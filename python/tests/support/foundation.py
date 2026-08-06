"""Shared pytest helpers for Python ship-pr modules."""

from __future__ import annotations

import os
import shlex
import stat
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final, Self, TypeVar, cast

if TYPE_CHECKING:
    import pytest

from larch.agents import collect_results
from larch.core.proc import CommandResult
from larch.core.run_context import RunContext
from larch.implement import scope_disposition

from tests.support.repo_contract import ROOT, repo_root
from tests.support.review_wire import plan_review_slot_line, slot_manifest_ndjson

CLI = ROOT / "python" / "cli.py"
T = TypeVar("T")

# Session/tmpdir builders depend on the root contract above; re-export after it.
from tests.support.session import (  # noqa: E402  # pylint: disable=wrong-import-position
    DESIGN_BASELINE_KEYS,
    IMPLEMENT_BASELINE_KEYS,
    make_design_tmpdir,
    make_implement_tmpdir,
    run_params_text,
    seed_feature_description,
    seed_plan,
    seed_run_params,
    write_design_source_env,
    write_session_env,
)


__all__ = [
    "CLI",
    "CODEX_USAGE_COMMAND",
    "DESIGN_BASELINE_KEYS",
    "IMPLEMENT_BASELINE_KEYS",
    "PR_VIEW_BEHIND_JSON",
    "PR_VIEW_OPEN_JSON",
    "ROOT",
    "RecordingRunner",
    "RunCall",
    "assert_larch_bgjob_adapter_request",
    "capture_start",
    "codex_usage_stdout",
    "completed",
    "gh_pr_view",
    "gh_result",
    "install_larch_bgjob_adapter_capture",
    "is_codex_usage_command",
    "make_adverse_push_repo",
    "make_checks_session",
    "make_committed_repo",
    "make_design_tmpdir",
    "make_implement_tmpdir",
    "make_keepalive_consumer_fixture",
    "make_run_context",
    "make_zero_findings_plan_review_fake_cli",
    "merge_admin_responses",
    "ok",
    "operator_repo_with_remote",
    "repo_root",
    "run_cli",
    "run_larch",
    "run_params_text",
    "seed_feature_description",
    "seed_plan",
    "seed_run_params",
    "write_design_source_env",
    "write_gh_pr_stub",
    "write_required_plan_coverage",
    "write_session_env",
]

def _empty_calls() -> list[list[str]]:
    return []


def make_keepalive_consumer_fixture(
    tmp_path: Path, *, session_text: str = "# no anchors\n"
) -> tuple[Path, Path, Path, Path]:
    """Create consumer, plugin, implementation, and keepalive review fixtures."""
    consumer = tmp_path / "consumer"
    (consumer / "larch-logs").mkdir(parents=True)
    plugin = tmp_path / "plugin"
    (plugin / "larch-logs").mkdir(parents=True)
    implement = tmp_path / "implement"
    implement.mkdir()
    review = implement / "round-1"
    review.mkdir()
    _ = (implement / "session-env.sh").write_text(session_text, encoding="utf-8")
    _ = (review / ".larch-keepalive").write_text(
        f"CLONE_PATH={consumer}\n", encoding="utf-8"
    )
    return consumer, plugin, implement, review


def _empty_results() -> list[CommandResult]:
    return []


def _empty_matchers() -> list[ArgvMatcher]:
    return []


def _empty_records() -> list[RunCall]:
    return []


def capture_start(captured: list[T]) -> Callable[..., int]:
    """Return a successful starter fake that records its specification."""
    def fake_start(spec: T, *, options: object | None = None) -> int:
        del options
        captured.append(spec)
        return 0

    return fake_start


def assert_larch_bgjob_adapter_request(
    command: Sequence[str],
    *,
    step: str,
    initial_merge_rows: Sequence[tuple[str, str]],
) -> None:
    """Assert the shared Rust adapter request fields at a Python caller seam."""
    assert command[command.index("--step") + 1] == step
    assert [
        command[index + 1]
        for index, value in enumerate(command)
        if value == "--initial-merge-row"
    ] == [f"{key}={value}" for key, value in initial_merge_rows]


def _capture_larch_bgjob_adapter(
    captured: list[tuple[str, ...]],
    original_run: Callable[..., CommandResult],
) -> Callable[..., CommandResult]:
    """Capture Rust bgjob-adapter launches while preserving unrelated commands."""

    def fake_run(argv: Sequence[str], **kwargs: object) -> CommandResult:
        command = tuple(argv)
        if command[1:3] == ("bgjob", "adapt"):
            captured.append(command)
            return CommandResult(command, 0, "", "", 0.0)
        return original_run(argv, **kwargs)

    return fake_run


def install_larch_bgjob_adapter_capture(
    monkeypatch: pytest.MonkeyPatch,
    runner_module: Any,
) -> list[tuple[str, ...]]:
    """Install a Rust-adapter runner fake and return its captured commands."""
    captured: list[tuple[str, ...]] = []
    monkeypatch.setattr(
        runner_module,
        "run",
        _capture_larch_bgjob_adapter(captured, runner_module.run),
    )
    return captured


@dataclass(frozen=True)
class RunCall:
    """One recorded ``RecordingRunner.run`` invocation with its call options."""

    argv: tuple[str, ...]
    timeout: float | None = None
    cwd: str | None = None
    env: Mapping[str, str] | None = None
    check: bool = False
    stdout: int | None = None
    stderr: int | None = None


# An expected-argv matcher is either the exact argv sequence or a predicate over it.
ArgvMatcher = Sequence[str] | Callable[[Sequence[str]], bool]


def _argv_matches(matcher: ArgvMatcher, argv: tuple[str, ...]) -> bool:
    if callable(matcher):
        return matcher(argv)
    return list(matcher) == list(argv)


def _matcher_repr(matcher: ArgvMatcher) -> str:
    if callable(matcher):
        return f"predicate {getattr(matcher, '__name__', repr(matcher))}"
    return f"argv {list(matcher)}"


@dataclass
class RecordingRunner:
    """Indexed response-queue runner for unit tests.

    Records each call's argv in ``calls`` and its full options in ``records``.
    Returns queued ``responses`` in order, then a ``default`` result, or, in
    ``strict`` mode, raises once the queue is exhausted. Optional per-call
    ``matchers`` assert the positional argv (exact sequence or predicate) and
    raise a precise diagnostic on mismatch, ``on_call`` observes each call's
    options, and ``route_fds`` writes a queued result's captured output to the
    explicit stdout/stderr file descriptors the caller passed.
    """

    calls: list[list[str]] = field(default_factory=_empty_calls)
    responses: list[CommandResult] = field(default_factory=_empty_results)
    strict: bool = False
    default: CommandResult | None = None
    matchers: list[ArgvMatcher] = field(default_factory=_empty_matchers)
    on_call: Callable[[RunCall], None] | None = None
    route_fds: bool = False
    records: list[RunCall] = field(default_factory=_empty_records)
    _index: int = 0

    @classmethod
    def strict_queue(cls, *responses: CommandResult) -> Self:
        """Create a runner that requires one response per call."""
        return cls(responses=list(responses), strict=True)

    @classmethod
    def default_queue(cls, default: CommandResult | None = None) -> Self:
        """Create a runner that returns a default response after its queue."""
        return cls(responses=[], default=default)

    def run(  # noqa: PLR0913 - runner call options mirror subprocess.run.
        self,
        argv: Sequence[str],
        *,
        timeout: float | None = None,
        cwd: str | None = None,
        env: Mapping[str, str] | None = None,
        check: bool = False,
        stdout: int | None = None,
        stderr: int | None = None,
    ) -> CommandResult:
        call = RunCall(tuple(argv), timeout, cwd, env, check, stdout, stderr)
        self.calls.append(list(call.argv))
        self.records.append(call)
        self._assert_matcher(call)
        if self.on_call is not None:
            self.on_call(call)
        result = self._next_result(call.argv)
        if self.route_fds:
            return self._route_fds(result, call)
        return result

    def _assert_matcher(self, call: RunCall) -> None:
        index = len(self.records) - 1
        if index >= len(self.matchers):
            return
        matcher = self.matchers[index]
        if _argv_matches(matcher, call.argv):
            return
        remaining = len(self.responses) - self._index
        msg = (
            f"call {index}: argv {list(call.argv)} does not match expected "
            f"{_matcher_repr(matcher)} ({remaining} queued response(s) remaining)"
        )
        raise AssertionError(msg)

    def _next_result(self, argv: tuple[str, ...]) -> CommandResult:
        if self._index >= len(self.responses):
            if self.strict:
                msg = f"no response for call {argv}"
                raise AssertionError(msg)
            return self.default or ok(argv)
        result = self.responses[self._index]
        self._index += 1
        return result

    def _route_fds(self, result: CommandResult, call: RunCall) -> CommandResult:
        payload = (result.stdout + result.stderr).encode()
        if call.stdout is not None:
            _ = os.write(call.stdout, payload)
        elif call.stderr is not None:
            _ = os.write(call.stderr, payload)
        return CommandResult(
            argv=call.argv,
            returncode=result.returncode,
            stdout=result.stdout if call.stdout is None else "",
            stderr=result.stderr if call.stderr is None else "",
            duration=result.duration,
        )


def run_cli(
    *args: str,
    env: dict[str, str] | None = None,
    quiet_disable: bool = False,
) -> subprocess.CompletedProcess[str]:
    """Run python/cli.py in a subprocess with CLAUDE_PLUGIN_ROOT set to the repo root."""
    merged = os.environ.copy()
    merged["CLAUDE_PLUGIN_ROOT"] = str(ROOT)
    if quiet_disable:
        merged["LARCH_QUIET_DISABLE"] = "1"
    if env:
        merged.update(env)
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=ROOT,
        env=merged,
        text=True,
        capture_output=True,
        check=False,
    )


def run_larch(
    *args: str,
    env: dict[str, str] | None = None,
    quiet_disable: bool = False,
) -> subprocess.CompletedProcess[str]:
    """Run one Rust-owned command through the verified bootstrap script.

    `LARCH_BINARY` comes from the session-wide test double unless the caller
    supplies its own, so a Python-only test run needs no Rust build.
    """
    merged = os.environ.copy()
    merged["CLAUDE_PLUGIN_ROOT"] = str(ROOT)
    if quiet_disable:
        merged["LARCH_QUIET_DISABLE"] = "1"
    if env:
        merged.update(env)
    return subprocess.run(
        [str(ROOT / "scripts" / "larch.sh"), *args],
        cwd=ROOT,
        env=merged,
        text=True,
        capture_output=True,
        check=False,
    )


def write_gh_pr_stub(
    path: Path, *, pr_create_rc: int, capture_path: Path | None = None
) -> None:
    """Write a ``gh`` stub for PR-create and PR-merge fixture flows."""
    path.parent.mkdir(parents=True, exist_ok=True)
    capture_path_arg = shlex.quote(str(capture_path) if capture_path else "")
    _ = path.write_text(
        "#!/usr/bin/env bash\n"
        f"CAPTURE_PATH={capture_path_arg}\n"
        'STATE_FILE="${0}.branch"\n'
        'REPO_FILE="${0}.repo"\n'
        'if [ "$1" = "pr" ] && [ "$2" = "create" ]; then\n'
        '  if [ -n "$CAPTURE_PATH" ]; then\n'
        '    (\n'
        "      printf '%s\\n' '__ARGV__'\n"
        "      for arg in \"$@\"; do printf '%s\\n' \"$arg\"; done\n"
        "      printf '%s\\n' '__BODY__'\n"
        '      body_file=""\n'
        '      while [ "$#" -gt 0 ]; do\n'
        '        if [ "$1" = "--body-file" ]; then\n'
        '          shift\n'
        '          body_file="${1-}"\n'
        '          break\n'
        '        fi\n'
        '        shift\n'
        '      done\n'
        '      if [ -n "$body_file" ]; then cat "$body_file"; fi\n'
        '    ) > "$CAPTURE_PATH"\n'
        '  fi\n'
        '  head_ref=""\n'
        '  repo=""\n'
        '  while [ "$#" -gt 0 ]; do\n'
        '    if [ "$1" = "--head" ]; then shift; head_ref="${1-}"; fi\n'
        '    if [ "$1" = "--repo" ]; then shift; repo="${1-}"; fi\n'
        '    shift\n'
        '  done\n'
        '  printf "%s\\n" "$head_ref" > "$STATE_FILE"\n'
        '  printf "%s\\n" "${repo:-o/r}" > "$REPO_FILE"\n'
        f"  if [ {pr_create_rc} -ne 0 ]; then echo 'gh: pr create failed' >&2; exit {pr_create_rc}; fi\n"
        '  repo="$(cat "$REPO_FILE")"\n'
        '  printf "https://github.com/%s/pull/77\\n" "$repo"\n'
        "  exit 0\n"
        "fi\n"
        'if [ "$1" = "pr" ] && [ "$2" = "list" ]; then echo "[]"; exit 0; fi\n'
        'if [ "$1" = "pr" ] && [ "$2" = "view" ]; then\n'
        '  head_ref="$(cat "$STATE_FILE")"\n'
        '  repo="$(cat "$REPO_FILE")"\n'
        '  printf \'{"number":77,"url":"https://github.com/%s/pull/77","state":"OPEN","headRefName":"%s"}\\n\' "$repo" "$head_ref"\n'
        "  exit 0\n"
        "fi\n"
        'if [ "$1" = "pr" ] && [ "$2" = "merge" ]; then exit 0; fi\n'
        "exit 0\n",
        encoding="utf-8",
    )
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def operator_repo_with_remote(
    tmp_path: Path,
    *,
    files: Mapping[str, str] | None = None,
    commit_message: str = "seed",
) -> Path:
    """Create a committed ``main`` fixture repository with a bare ``origin`` remote."""
    repo = make_committed_repo(
        tmp_path,
        files=files if files is not None else {"README.md": "seed\n"},
        commit_message=commit_message,
        branch="main",
    )
    origin = tmp_path / "origin.git"
    _ = subprocess.run(
        ["git", "init", "-q", "--bare", str(origin)],  # noqa: S607 - required test fixture dependency
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    for args in (("remote", "add", "origin", str(origin)), ("push", "-q", "-u", "origin", "main")):
        _ = subprocess.run(
            ["git", *args],  # noqa: S607 - required test fixture dependency
            cwd=repo,
            check=True,
            capture_output=True,
        )
    return repo


def make_committed_repo(
    tmp_path: Path,
    *,
    path: Path | None = None,
    files: Mapping[str, str] | None = None,
    commit_message: str = "base",
    branch: str | None = None,
) -> Path:
    """Create a committed git fixture, optionally at ``path`` with named files."""
    repo = path or tmp_path / "repo"
    repo.parent.mkdir(parents=True, exist_ok=True)
    repo.mkdir(exist_ok=True)
    _ = subprocess.run(
        ["git", "init", "-q"],  # noqa: S607 - required test fixture dependency
        cwd=repo,
        check=True,
        capture_output=True,
    )
    if branch is not None:
        _ = subprocess.run(
            ["git", "checkout", "-q", "-b", branch],  # noqa: S607 - required fixture dependency
            cwd=repo,
            check=True,
            capture_output=True,
        )
    for args in (("config", "user.email", "test@example.com"), ("config", "user.name", "Test")):
        _ = subprocess.run(
            ["git", *args],  # noqa: S607 - required test fixture dependency
            cwd=repo,
            check=True,
            capture_output=True,
        )
    fixture_files = files if files is not None else {"tracked": "base\n"}
    for relpath, content in fixture_files.items():
        target = repo / relpath
        target.parent.mkdir(parents=True, exist_ok=True)
        _ = target.write_text(content, encoding="utf-8")
    _ = subprocess.run(
        ["git", "add", "-A"],  # noqa: S607 - required test fixture dependency
        cwd=repo,
        check=True,
        capture_output=True,
    )
    _ = subprocess.run(
        ["git", "commit", "-q", "-m", commit_message, "--allow-empty"],  # noqa: S607 - required fixture dependency
        cwd=repo,
        check=True,
        capture_output=True,
    )
    return repo.resolve()


def make_checks_session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, bgjob_model: Any
) -> tuple[Path, Path]:
    """Create the standard implementation-checks session fixture."""
    repo = make_committed_repo(tmp_path)
    impl = tmp_path / "impl"
    impl.mkdir()
    _ = (impl / "session-env.sh").write_text(f"REPO_ROOT={repo.resolve()}\n", encoding="utf-8")
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(impl))
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(ROOT))
    monkeypatch.setenv("LARCH_CLAUDE_PID", str(os.getpid()))

    def fake_owner_identity(_pid: str | None) -> object:
        return bgjob_model.OwnerIdentity(recorded=None)

    monkeypatch.setattr(
        bgjob_model, "owner_identity_from_env", fake_owner_identity
    )
    return impl, repo


def _fixture_git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],  # noqa: S607 - fixed executable in a disposable Git fixture
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def make_adverse_push_repo(tmp_path: Path) -> tuple[Path, Path, str, str]:
    """Create a feature branch whose tracking ref is deliberately adversarial."""
    origin = tmp_path / "origin.git"
    source = tmp_path / "source"
    repo = tmp_path / "repo"
    _ = subprocess.run(
        ["git", "init", "--bare", "-q", str(origin)],  # noqa: S607 - fixed executable in a disposable Git fixture
        check=True,
    )
    _ = subprocess.run(
        ["git", "init", "-q", "-b", "main", str(source)],  # noqa: S607 - fixed executable in a disposable Git fixture
        check=True,
    )
    _ = _fixture_git(source, "config", "user.email", "test@example.com")
    _ = _fixture_git(source, "config", "user.name", "Test")
    _ = (source / "README.md").write_text("base\n", encoding="utf-8")
    for args in (("add", "README.md"), ("commit", "-q", "-m", "base"), ("remote", "add", "origin", str(origin)), ("push", "-q", "-u", "origin", "main")):
        _ = _fixture_git(source, *args)
    _ = _fixture_git(origin, "symbolic-ref", "HEAD", "refs/heads/main")
    _ = subprocess.run(
        ["git", "clone", "-q", str(origin), str(repo)],  # noqa: S607 - fixed executable in a disposable Git fixture
        check=True,
    )
    _ = _fixture_git(repo, "config", "user.email", "test@example.com")
    _ = _fixture_git(repo, "config", "user.name", "Test")
    for args in (("checkout", "-q", "-b", "feature-x", "origin/main"), ("push", "-q", "-u", "origin", "feature-x"), ("branch", "--set-upstream-to=origin/main", "feature-x"), ("config", "push.default", "upstream")):
        _ = _fixture_git(repo, *args)
    _ = (repo / "feature.txt").write_text("feature\n", encoding="utf-8")
    _ = _fixture_git(repo, "add", "feature.txt")
    _ = _fixture_git(repo, "commit", "-q", "-m", "feature")
    return repo, origin, _fixture_git(repo, "rev-parse", "origin/feature-x"), _fixture_git(origin, "rev-parse", "refs/heads/main")


def write_required_plan_coverage(
    tmp_path: Path,
    *,
    fingerprint: str,
) -> None:
    """Write the high-coverage disposition fixture used by PR tests."""
    coverage = scope_disposition.PlanCoverage(
        total=1, touched=0, untouched=1, untouched_percent=100, band="high",
        plan_paths=("a.py",), touched_paths=(), untouched_paths=("a.py",),
        todos_left_count=0, todos_left=(), fingerprint=fingerprint,
        disposition_required=True, plan_fidelity_forced=True,
        coverage_file=str(tmp_path / "plan-coverage.json"),
        untouched_file=str(tmp_path / "untouched.txt"), todos_file=str(tmp_path / "todos.txt"),
    )
    scope_disposition.write_coverage(coverage, tmpdir=tmp_path)


# Shared RunContext defaults for ship-pr unit tests; override fields via
# make_run_context(). The frozen dataclass is safe to share as a singleton.
_DEFAULT_RUN_CONTEXT = RunContext(
    branch="feat",
    issue="1",
    repo="o/r",
    run_id="run-1",
    tmpdir="/tmp/impl",  # noqa: S108 - fixed fixture value, not a real temporary directory.
    merge=True,
    draft=False,
    forked=False,
    manifest_path="/tmp/impl/manifest.json",  # noqa: S108 - fixed fixture value, not a real temporary directory.
    tool_label="cursor",
    no_admin_fallback=False,
    repo_unavailable=False,
)


def make_run_context(**overrides: object) -> RunContext:
    """Build a RunContext from shared test defaults, applying field overrides."""
    return _DEFAULT_RUN_CONTEXT.with_(**overrides)


# Common `gh pr view 1` JSON payloads for merge/ship unit tests.
PR_VIEW_OPEN_JSON = '{"number":1,"url":"u","state":"OPEN","headRefName":"feat"}'
PR_VIEW_BEHIND_JSON = '{"mergeStateStatus":"BEHIND","headRefOid":"abc"}'


def gh_result(argv: tuple[str, ...], stdout: str = "") -> CommandResult:
    """Stubbed gh CommandResult: exit 0, empty stderr, 0.01s duration."""
    return CommandResult(argv, 0, stdout, "", 0.01)


def ok(argv: Sequence[str], stdout: str = "") -> CommandResult:
    """Build a successful CommandResult for a command argument sequence."""
    return CommandResult(tuple(argv), 0, stdout, "", 0.01)


def completed(argv: Sequence[str], stdout: str = "") -> subprocess.CompletedProcess[str]:
    """Build a successful text CompletedProcess for the supplied arguments."""
    return subprocess.CompletedProcess(argv, 0, stdout, "")


CODEX_USAGE_COMMAND: Final[tuple[str, str]] = ("agent", "parse-codex-usage")


def is_codex_usage_command(argv: object) -> bool:
    """Report whether argv invokes the Rust-owned `agent parse-codex-usage`."""
    if not isinstance(argv, (list, tuple)):
        return False
    items: list[str] = [str(item) for item in cast("Sequence[object]", argv)]
    return tuple(items[1:3]) == CODEX_USAGE_COMMAND


def codex_usage_stdout(*, uncached_input: int = 7, cached_input: int = 3, output: int = 4) -> str:
    """Render the `KEY=value` stdout that `agent parse-codex-usage` emits."""
    total: int = uncached_input + cached_input + output
    return f"INPUT={uncached_input}\nCACHED_INPUT={cached_input}\nOUTPUT={output}\nTOTAL={total}\n"


def gh_pr_view(stdout: str) -> CommandResult:
    """Stubbed `gh pr view 1` CommandResult carrying the given JSON stdout."""
    return gh_result(("gh", "pr", "view", "1"), stdout)


def merge_admin_responses(*, double_open_view: bool = False) -> list[CommandResult]:
    """Build the gh response queue for a BEHIND PR that merge_pr() admin-merges.

    With double_open_view, two OPEN `gh pr view` results precede the BEHIND
    view, matching tests that re-view the PR before merging.
    """
    opens = [gh_pr_view(PR_VIEW_OPEN_JSON) for _ in range(2 if double_open_view else 1)]
    return [*opens, gh_pr_view(PR_VIEW_BEHIND_JSON), gh_result(("gh", "pr", "merge"))]


def make_zero_findings_plan_review_fake_cli(
    design: Path, reviewer_file: Path
) -> Callable[..., subprocess.CompletedProcess[str]]:
    """Build the shared ``_run_cli`` fake for the #5032 zero-findings degraded-panel path.

    ``test_plan_review`` and ``test_plan_review_round`` both stub the same
    panel-dispatch / collect-results / aggregate / voter-dispatch / tally sequence
    for a single OK Cursor reviewer that parses to zero findings. Extracting the
    identical block here keeps it from tripping the R0801 duplicate-code gate.
    """

    def fake_run_cli(argv: list[str], *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        del env
        if argv[:2] == ["plan-review", "panel-dispatch"]:
            paths_file = design / "plan-review-panel-paths.txt"
            _ = (design / "plan-review-slots.ndjson").write_text(
                slot_manifest_ndjson(
                    [
                        plan_review_slot_line(
                            "cursor-plan-arch",
                            "cursor",
                            reviewer_file,
                            prompt_file=design / "cursor-plan-arch.prompt",
                        )
                    ]
                ),
                encoding="utf-8",
            )
            _ = paths_file.write_text(str(reviewer_file) + "\n", encoding="utf-8")
            return subprocess.CompletedProcess(argv, 0, f"PANEL_PRUNED_EMPTY=false\nPANEL_PATHS_FILE={paths_file}\n", "")
        if argv[:2] == ["agent", "collect-results"]:
            record = collect_results.CollectorRecord(
                reviewer_file=str(reviewer_file),
                tool="cursor",
                status="OK",
                exit_code="0",
            )
            blocks = ["\n".join(record.fields())]
            return subprocess.CompletedProcess(argv, 0, "\n\n".join(blocks) + "\n", "")
        if argv[:2] == ["review", "aggregate-findings"]:
            return subprocess.CompletedProcess(argv, 0, "REASON=insufficient-input\nAGGREGATED=false\n", "")
        if argv[:2] == ["plan-review", "voter-dispatch"]:
            return subprocess.CompletedProcess(argv, 0, "DISPATCH_OK=false\nDEGRADED_PANEL=1\n", "")
        if argv[:2] == ["plan-review", "tally"]:
            return subprocess.CompletedProcess(argv, 0, "TALLY_PLAN_REVIEW_STATUS=ok\n", "")
        return subprocess.CompletedProcess(argv, 0, "", "")

    return fake_run_cli
