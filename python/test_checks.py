"""Tests for checks.py (stub Runner only; no bash executed)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import pytest

import checks
import config
from outcomes import Outcome
from proc import CommandResult


def _empty_responses() -> list[CommandResult]:
    return []


def _empty_calls() -> list[tuple[tuple[str, ...], dict[str, object]]]:
    return []


@dataclass
class StubRunner:
    """Scripted subprocess responses for unit tests."""

    responses: list[CommandResult] = field(default_factory=_empty_responses)
    calls: list[tuple[tuple[str, ...], dict[str, object]]] = field(
        default_factory=_empty_calls,
    )

    def run(
        self,
        argv: Sequence[str],
        *,
        timeout: float | None = None,
        cwd: str | None = None,
        env: Mapping[str, str] | None = None,
        check: bool = False,
    ) -> CommandResult:
        _ = timeout, env, check
        argv_tuple = tuple(argv)
        self.calls.append((argv_tuple, {"cwd": cwd}))
        if self.responses:
            result = self.responses.pop(0)
            return CommandResult(
                argv=argv_tuple,
                returncode=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                duration=result.duration,
            )
        return CommandResult(
            argv=argv_tuple,
            returncode=0,
            stdout="",
            stderr="",
            duration=0.0,
        )


def _ok(stdout: str = "", *, rc: int = 0) -> CommandResult:
    return CommandResult(argv=(), returncode=rc, stdout=stdout, stderr="", duration=0.0)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (0, 3),
        (1, 1),
        (3, 3),
        (6, 6),
        (7, 6),
        (99, 6),
        ("", 3),
        ("x", 3),
        ("03", 3),
    ],
)
def test_normalize_max_iter(raw: str | int, expected: int) -> None:
    assert checks.normalize_max_iter(raw) == expected


def test_normalize_max_iter_default() -> None:
    assert checks.normalize_max_iter(None) == config.RCC_MAX_ITER_DEFAULT


def test_escalate_mapping() -> None:
    assert checks.escalate("ok").outcome == Outcome.OK
    assert checks.escalate("exhausted").outcome == Outcome.STALLED
    assert checks.escalate("no-changes-stale").outcome == Outcome.STALLED
    assert checks.escalate("main-agent-required").outcome == Outcome.NEEDS_USER_INPUT
    assert checks.escalate("dispatch-failed").outcome == Outcome.TRANSIENT
    assert checks.escalate("head-changed").outcome == Outcome.TRANSIENT


def test_run_check_fix_loop_clean_first() -> None:
    sequence = [checks.ChecksResult(
        ok=True,
        exit_code=0,
        site="step6",
        redacted_log_path=None,
        phase="unknown",
        coverage="full",
        skipped=False,
        warn=None,
    )]

    def checks_runner() -> checks.ChecksResult:
        return sequence.pop(0)

    def fixer(_log: str) -> checks.FixOutcome:
        raise AssertionError("fixer must not run")

    loop = checks.run_check_fix_loop(
        checks_runner=checks_runner,
        fixer=fixer,
        dispatch_first=False,
        max_iter=3,
    )
    assert loop.status == "ok"


def test_run_check_fix_loop_fail_applied_clean(tmp_path: Path) -> None:
    raw_log = tmp_path / "fail.log"
    _ = raw_log.write_text("error\n", encoding="utf-8")
    redacted = tmp_path / "fail.redacted.log"
    _ = redacted.write_text("error\n", encoding="utf-8")
    fail = checks.ChecksResult(
        ok=False,
        exit_code=1,
        site="step6",
        redacted_log_path=str(redacted),
        phase="pre-commit",
        coverage="changed-file-only",
        skipped=False,
        warn=None,
        raw_log_path=str(raw_log),
    )
    ok = checks.ChecksResult(
        ok=True,
        exit_code=0,
        site="step6",
        redacted_log_path=None,
        phase="unknown",
        coverage="full",
        skipped=False,
        warn=None,
    )
    sequence = [fail, ok]
    fix_calls: list[str] = []

    def checks_runner() -> checks.ChecksResult:
        return sequence.pop(0)

    def fixer(log: str) -> checks.FixOutcome:
        fix_calls.append(log)
        return checks.FixOutcome(
            status="applied",
            delta_paths=("a.py",),
            failure_reason=None,
            commit_sha="abc",
            head_changed=False,
            coder_tool="codex",
        )

    loop = checks.run_check_fix_loop(
        checks_runner=checks_runner,
        fixer=fixer,
        dispatch_first=False,
        max_iter=3,
    )
    assert loop.status == "ok"
    assert fix_calls == [str(redacted)]
    assert loop.delta_paths == ("a.py",)


def test_run_check_fix_loop_exhausted_applied_still_failing(tmp_path: Path) -> None:
    raw_log = tmp_path / "fail.log"
    _ = raw_log.write_text("error\n", encoding="utf-8")
    redacted = tmp_path / "fail.redacted.log"
    _ = redacted.write_text("error\n", encoding="utf-8")
    fail = checks.ChecksResult(
        ok=False,
        exit_code=1,
        site="step6",
        redacted_log_path=str(redacted),
        phase="agent-lint",
        coverage="changed-file-only",
        skipped=False,
        warn=None,
        raw_log_path=str(raw_log),
    )
    sequence = [fail, fail, fail]

    def checks_runner() -> checks.ChecksResult:
        return sequence.pop(0)

    def fixer(_log: str) -> checks.FixOutcome:
        return checks.FixOutcome(
            status="applied",
            delta_paths=("b.py",),
            failure_reason=None,
            commit_sha=None,
            head_changed=False,
            coder_tool="codex",
        )

    loop = checks.run_check_fix_loop(
        checks_runner=checks_runner,
        fixer=fixer,
        dispatch_first=False,
        max_iter=3,
    )
    assert loop.status == "exhausted"
    result = checks.escalate(loop.status, delta_paths=loop.delta_paths)
    assert result.outcome == Outcome.STALLED


def test_run_check_fix_loop_empty_failure_twice_exhausted(tmp_path: Path) -> None:
    empty_log = tmp_path / "empty.log"
    _ = empty_log.write_text("", encoding="utf-8")
    fail_empty = checks.ChecksResult(
        ok=False,
        exit_code=1,
        site="step6",
        redacted_log_path=None,
        phase="unknown",
        coverage="changed-file-only",
        skipped=False,
        warn=None,
        raw_log_path=str(empty_log),
    )
    sequence = [fail_empty, fail_empty]

    def checks_runner() -> checks.ChecksResult:
        return sequence.pop(0)

    def fixer(_log: str) -> checks.FixOutcome:
        raise AssertionError("fixer must not run on empty log")

    loop = checks.run_check_fix_loop(
        checks_runner=checks_runner,
        fixer=fixer,
        dispatch_first=False,
        max_iter=3,
    )
    assert loop.status == "exhausted"


def test_run_check_fix_loop_dispatch_first_no_changes_stale(tmp_path: Path) -> None:
    initial = tmp_path / "initial.redacted.log"
    _ = initial.write_text("error\n", encoding="utf-8")
    raw_log = tmp_path / "fail.log"
    _ = raw_log.write_text("error\n", encoding="utf-8")
    redacted = tmp_path / "fail.redacted.log"
    _ = redacted.write_text("error\n", encoding="utf-8")
    fail = checks.ChecksResult(
        ok=False,
        exit_code=1,
        site="step6",
        redacted_log_path=str(redacted),
        phase="pre-commit",
        coverage="changed-file-only",
        skipped=False,
        warn=None,
        raw_log_path=str(raw_log),
    )

    def checks_runner() -> checks.ChecksResult:
        return fail

    def fixer(_log: str) -> checks.FixOutcome:
        return checks.FixOutcome(
            status="no-changes",
            delta_paths=(),
            failure_reason=None,
            commit_sha=None,
            head_changed=False,
            coder_tool="codex",
        )

    loop = checks.run_check_fix_loop(
        checks_runner=checks_runner,
        fixer=fixer,
        dispatch_first=True,
        max_iter=3,
        initial_redacted_log=str(initial),
    )
    assert loop.status == "no-changes-stale"


def test_run_check_fix_loop_main_agent_required(tmp_path: Path) -> None:
    raw_log = tmp_path / "fail.log"
    _ = raw_log.write_text("error\n", encoding="utf-8")
    redacted = tmp_path / "fail.redacted.log"
    _ = redacted.write_text("error\n", encoding="utf-8")
    fail = checks.ChecksResult(
        ok=False,
        exit_code=1,
        site="step6",
        redacted_log_path=str(redacted),
        phase="pre-commit",
        coverage="changed-file-only",
        skipped=False,
        warn=None,
        raw_log_path=str(raw_log),
    )

    def checks_runner() -> checks.ChecksResult:
        return fail

    def fixer(_log: str) -> checks.FixOutcome:
        return checks.FixOutcome(
            status="main-agent-required",
            delta_paths=(),
            failure_reason=None,
            commit_sha=None,
            head_changed=False,
            coder_tool=None,
        )

    loop = checks.run_check_fix_loop(
        checks_runner=checks_runner,
        fixer=fixer,
        dispatch_first=False,
        max_iter=3,
    )
    assert loop.status == "main-agent-required"
    assert checks.escalate(loop.status).outcome == Outcome.NEEDS_USER_INPUT


def test_run_check_fix_loop_failed_head_changed(tmp_path: Path) -> None:
    raw_log = tmp_path / "fail.log"
    _ = raw_log.write_text("error\n", encoding="utf-8")
    redacted = tmp_path / "fail.redacted.log"
    _ = redacted.write_text("error\n", encoding="utf-8")
    fail = checks.ChecksResult(
        ok=False,
        exit_code=1,
        site="step6",
        redacted_log_path=str(redacted),
        phase="pre-commit",
        coverage="changed-file-only",
        skipped=False,
        warn=None,
        raw_log_path=str(raw_log),
    )

    def checks_runner() -> checks.ChecksResult:
        return fail

    def fixer(_log: str) -> checks.FixOutcome:
        return checks.FixOutcome(
            status="failed",
            delta_paths=(),
            failure_reason="head-changed-after-dispatch",
            commit_sha=None,
            head_changed=True,
            coder_tool="cursor",
        )

    loop = checks.run_check_fix_loop(
        checks_runner=checks_runner,
        fixer=fixer,
        dispatch_first=False,
        max_iter=3,
    )
    assert loop.status == "head-changed"
    assert checks.escalate(loop.status).outcome == Outcome.TRANSIENT


def test_run_relevant_checks_skipped_when_script_absent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cache = tmp_path / "cache"
    session = cache / "larch" / "sessions" / "claude-implement-test"
    session.mkdir(parents=True)
    monkeypatch.setenv("XDG_CACHE_HOME", str(cache))
    repo = tmp_path / "repo"
    repo.mkdir()
    runner = StubRunner()
    result = checks.run_relevant_checks(
        runner,
        site="step6",
        tmpdir=str(session),
        repo_root=str(repo),
    )
    assert result.skipped is True
    assert result.ok is True


def test_run_relevant_checks_parses_markers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cache = tmp_path / "cache"
    session = cache / "larch" / "sessions" / "claude-implement-test"
    session.mkdir(parents=True)
    monkeypatch.setenv("XDG_CACHE_HOME", str(cache))
    repo = tmp_path / "repo"
    scripts = repo / "scripts"
    scripts.mkdir(parents=True)
    check_script = scripts / "relevant-checks.sh"
    _ = check_script.write_text("#!/bin/sh\necho ok\n", encoding="utf-8")
    _ = check_script.chmod(0o755)
    log_body = (
        "=== Running pre-commit\n"
        "=== Running agent-lint ===\n"
    )
    runner = StubRunner([_ok(log_body)])
    result = checks.run_relevant_checks(
        runner,
        site="step6",
        tmpdir=str(session),
        repo_root=str(repo),
    )
    assert result.ok is True
    assert result.coverage == "full"
    assert result.warn is None


def test_run_relevant_checks_fail_produces_redacted_log(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cache = tmp_path / "cache"
    session = cache / "larch" / "sessions" / "claude-implement-test"
    session.mkdir(parents=True)
    monkeypatch.setenv("XDG_CACHE_HOME", str(cache))
    repo = tmp_path / "repo"
    scripts = repo / "scripts"
    scripts.mkdir(parents=True)
    check_script = scripts / "relevant-checks.sh"
    _ = check_script.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    _ = check_script.chmod(0o755)
    secret = "sk-ant-abcdefghijklmnopqrstuvwxyz0123456789ABCD"
    runner = StubRunner([_ok(f"=== Running pre-commit\n{secret}\n", rc=1)])
    result = checks.run_relevant_checks(
        runner,
        site="step6",
        tmpdir=str(session),
        repo_root=str(repo),
    )
    assert result.ok is False
    assert result.redacted_log_path is not None
    redacted = Path(result.redacted_log_path).read_text(encoding="utf-8")
    assert secret not in redacted
    assert config.REDACTED_TOKEN in redacted


def test_run_lint_fix_no_tools(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    scripts = repo / "scripts"
    scripts.mkdir(parents=True)
    run_external = scripts / "run-external-agent.sh"
    _ = run_external.write_text("#!/bin/sh\n", encoding="utf-8")
    _ = run_external.chmod(0o755)
    log = tmp_path / "checks.log"
    _ = log.write_text("lint error\n", encoding="utf-8")
    runner = StubRunner()
    outcome = checks.run_lint_fix(
        runner,
        site="step6",
        checks_log=str(log),
        repo_root=str(repo),
        codex_present=False,
        cursor_present=False,
        run_parent=str(tmp_path / "runs"),
    )
    assert outcome.status == "main-agent-required"


def test_run_lint_fix_empty_log(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    scripts = repo / "scripts"
    scripts.mkdir(parents=True)
    run_external = scripts / "run-external-agent.sh"
    _ = run_external.write_text("#!/bin/sh\n", encoding="utf-8")
    _ = run_external.chmod(0o755)
    log = tmp_path / "empty.log"
    _ = log.write_text("", encoding="utf-8")
    runner = StubRunner()
    outcome = checks.run_lint_fix(
        runner,
        site="step6",
        checks_log=str(log),
        repo_root=str(repo),
        codex_present=True,
        cursor_present=False,
        run_parent=str(tmp_path / "runs"),
    )
    assert outcome.status == "no-changes"


def test_run_lint_fix_missing_run_external_agent(tmp_path: Path) -> None:
    log = tmp_path / "log.txt"
    _ = log.write_text("failure\n", encoding="utf-8")
    repo = tmp_path / "repo"
    repo.mkdir()
    runner = StubRunner()
    outcome = checks.run_lint_fix(
        runner,
        site="step6",
        checks_log=str(log),
        repo_root=str(repo),
        codex_present=True,
        cursor_present=False,
        run_parent=str(tmp_path / "runs"),
    )
    assert outcome.status == "failed"
    assert outcome.failure_reason == "missing-run-external-agent"


def test_run_lint_fix_codex_argv_parity(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    scripts = repo / "scripts"
    scripts.mkdir(parents=True)
    run_external = scripts / "run-external-agent.sh"
    _ = run_external.write_text("#!/bin/sh\n", encoding="utf-8")
    _ = run_external.chmod(0o755)
    log = tmp_path / "checks.log"
    _ = log.write_text("lint error\n", encoding="utf-8")
    head = "abc123"
    runner = StubRunner([
        _ok(""),  # baseline tracked diff
        _ok(""),  # baseline untracked status
        _ok(head + "\n"),  # rev-parse HEAD
        _ok("main\n"),  # symbolic-ref
        _ok(""),  # submodule config
        _ok(""),  # submodule foreach
        _ok("", rc=1),  # codex dispatch fails
        _ok("", rc=1),  # cursor not tried when codex_present only
    ])
    outcome = checks.run_lint_fix(
        runner,
        site="step6",
        checks_log=str(log),
        repo_root=str(repo),
        codex_present=True,
        cursor_present=False,
        run_parent=str(tmp_path / "runs"),
    )
    assert outcome.status == "main-agent-required"
    assert outcome.failure_reason == "dispatch-failed"
    flat = " ".join(arg for call, _kw in runner.calls for arg in call)
    assert "launch-codex-ci.sh" not in flat
    assert "launch-cursor-ci.sh" not in flat
    codex_call = next(
        call for call, _kw in runner.calls
        if any("run-external-agent.sh" in part for part in call)
    )
    idx = list(codex_call).index(str(run_external))
    argv = list(codex_call)[idx:]
    assert argv[1:3] == ["--tool", "codex"]
    assert "--timeout" in argv
    assert "1800" in argv
    assert "--stderr-sink" in argv
    leaf = argv[argv.index("--") + 1 :]
    assert leaf[:3] == ["codex", "exec", "--full-auto"]
    assert "-C" in leaf
    assert str(repo) in leaf
    assert leaf[-1]


def test_compose_prompt_redacts_secrets(tmp_path: Path) -> None:
    log = tmp_path / "checks.log"
    secret = "ghp_" + "a" * 36
    _ = log.write_text(secret + "\n", encoding="utf-8")
    prompt = checks._compose_prompt(  # pyright: ignore[reportPrivateUsage]
        checks_log=log,
        site_label="Step 6",
        submodule_paths=(),
        target_cmd_display=None,
    )
    assert secret not in prompt
    assert config.REDACTED_TOKEN in prompt
