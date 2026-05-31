"""Tests for checks.py (stub Runner only; no bash executed)."""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping, Sequence
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
        stdout: int | None = None,
        stderr: int | None = None,
    ) -> CommandResult:
        _ = timeout, env, check
        argv_tuple = tuple(argv)
        self.calls.append((argv_tuple, {"cwd": cwd}))
        if self.responses:
            result = self.responses.pop(0)
            payload = (result.stdout + result.stderr).encode()
            if stdout is not None:
                _ = os.write(stdout, payload)
            elif stderr is not None:
                _ = os.write(stderr, payload)
            return CommandResult(
                argv=argv_tuple,
                returncode=result.returncode,
                stdout=result.stdout if stdout is None else "",
                stderr=result.stderr if stderr is None else "",
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


def _lint_fix_dirs(tmp_path: Path) -> tuple[str, str]:
    allowed = str(tmp_path)
    run_parent = str(tmp_path / "lint-fix-loop")
    return allowed, run_parent


def _with_ledger_stubs(
    responses: list[CommandResult],
    *,
    site: str = "step6",
) -> list[CommandResult]:
    if site not in {"step3", "step6"}:
        return list(responses)
    scripts = Path(__file__).resolve().parents[1] / "scripts"
    leading: list[CommandResult] = []
    for name in ("token-ledger.sh", "timing-ledger.sh"):
        script = scripts / name
        if script.is_file() and os.access(script, os.X_OK):
            leading.append(_ok(""))
    return [*leading, *responses]


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
        allowed_tmpdir=str(tmp_path),
    )
    assert loop.status == "no-changes-stale"


def test_run_check_fix_loop_dispatch_first_multi_apply(tmp_path: Path) -> None:
    initial = tmp_path / "initial.redacted.log"
    _ = initial.write_text("error\n", encoding="utf-8")
    raw1 = tmp_path / "fail1.log"
    raw2 = tmp_path / "fail2.log"
    redacted1 = tmp_path / "fail1.redacted.log"
    redacted2 = tmp_path / "fail2.redacted.log"
    for path in (raw1, raw2, redacted1, redacted2):
        _ = path.write_text("error\n", encoding="utf-8")
    checks_sequence = [
        checks.ChecksResult(
            ok=False,
            exit_code=1,
            site="step6",
            redacted_log_path=str(redacted1),
            phase="pre-commit",
            coverage="changed-file-only",
            skipped=False,
            warn=None,
            raw_log_path=str(raw1),
        ),
        checks.ChecksResult(
            ok=False,
            exit_code=1,
            site="step6",
            redacted_log_path=str(redacted2),
            phase="agent-lint",
            coverage="changed-file-only",
            skipped=False,
            warn=None,
            raw_log_path=str(raw2),
        ),
        checks.ChecksResult(
            ok=True,
            exit_code=0,
            site="step6",
            redacted_log_path=None,
            phase="unknown",
            coverage="full",
            skipped=False,
            warn=None,
        ),
    ]
    fixes = [
        checks.FixOutcome(
            status="applied",
            delta_paths=("a.py",),
            failure_reason=None,
            commit_sha="abc",
            head_changed=False,
            coder_tool="codex",
        ),
        checks.FixOutcome(
            status="applied",
            delta_paths=("b.py",),
            failure_reason=None,
            commit_sha="def",
            head_changed=False,
            coder_tool="codex",
        ),
        checks.FixOutcome(
            status="applied",
            delta_paths=("c.py",),
            failure_reason=None,
            commit_sha="ghi",
            head_changed=False,
            coder_tool="codex",
        ),
    ]

    loop = checks.run_check_fix_loop(
        checks_runner=lambda: checks_sequence.pop(0),
        fixer=lambda _log: fixes.pop(0),
        dispatch_first=True,
        initial_redacted_log=str(initial),
        allowed_tmpdir=str(tmp_path),
    )
    assert loop.status == "ok"
    assert loop.delta_paths == ("a.py", "b.py", "c.py")


def test_run_check_fix_loop_dispatch_first_fallback_redacted_chmod(tmp_path: Path) -> None:
    initial = tmp_path / "initial.redacted.log"
    _ = initial.write_text("error\n", encoding="utf-8")
    raw = tmp_path / "fail.log"
    _ = raw.write_text("error\n", encoding="utf-8")
    checks_sequence = [
        checks.ChecksResult(
            ok=False,
            exit_code=1,
            site="step6",
            redacted_log_path=None,
            phase="pre-commit",
            coverage="changed-file-only",
            skipped=False,
            warn=None,
            raw_log_path=str(raw),
        ),
        checks.ChecksResult(
            ok=True,
            exit_code=0,
            site="step6",
            redacted_log_path=None,
            phase="unknown",
            coverage="full",
            skipped=False,
            warn=None,
        ),
    ]
    dispatched: list[str] = []

    def fixer(log: str) -> checks.FixOutcome:
        dispatched.append(log)
        return checks.FixOutcome(
            status="applied",
            delta_paths=("a.py",),
            failure_reason=None,
            commit_sha=None,
            head_changed=False,
            coder_tool="codex",
        )

    loop = checks.run_check_fix_loop(
        checks_runner=lambda: checks_sequence.pop(0),
        fixer=fixer,
        dispatch_first=True,
        initial_redacted_log=str(initial),
        allowed_tmpdir=str(tmp_path),
    )
    fallback = raw.with_name(f"{raw.stem}.redacted.log")
    assert loop.status == "ok"
    assert dispatched == [str(initial), str(fallback)]
    assert fallback.stat().st_mode & 0o777 == 0o600


def test_run_check_fix_loop_dispatch_first_exhausted_missing_post_fix_raw_log(
    tmp_path: Path,
) -> None:
    initial = tmp_path / "initial.redacted.log"
    _ = initial.write_text("error\n", encoding="utf-8")
    fail_no_raw = checks.ChecksResult(
        ok=False,
        exit_code=1,
        site="step6",
        redacted_log_path=None,
        phase="pre-commit",
        coverage="changed-file-only",
        skipped=False,
        warn=None,
        raw_log_path=None,
    )

    loop = checks.run_check_fix_loop(
        checks_runner=lambda: fail_no_raw,
        fixer=lambda _log: checks.FixOutcome(
            status="applied",
            delta_paths=("a.py",),
            failure_reason=None,
            commit_sha=None,
            head_changed=False,
            coder_tool="codex",
        ),
        dispatch_first=True,
        initial_redacted_log=str(initial),
        allowed_tmpdir=str(tmp_path),
    )
    assert loop.status == "exhausted"
    assert checks.escalate(loop.status).outcome == Outcome.STALLED


def test_run_check_fix_loop_check_first_fallback_redacted_chmod(tmp_path: Path) -> None:
    raw = tmp_path / "fail.log"
    secret = "ghp_" + "a" * 36
    _ = raw.write_text(f"{secret}\n", encoding="utf-8")
    checks_sequence = [
        checks.ChecksResult(
            ok=False,
            exit_code=1,
            site="step6",
            redacted_log_path=None,
            phase="pre-commit",
            coverage="changed-file-only",
            skipped=False,
            warn=None,
            raw_log_path=str(raw),
        ),
        checks.ChecksResult(
            ok=True,
            exit_code=0,
            site="step6",
            redacted_log_path=None,
            phase="unknown",
            coverage="full",
            skipped=False,
            warn=None,
        ),
    ]
    dispatched: list[str] = []

    def fixer(log: str) -> checks.FixOutcome:
        dispatched.append(log)
        return checks.FixOutcome(
            status="applied",
            delta_paths=("a.py",),
            failure_reason=None,
            commit_sha=None,
            head_changed=False,
            coder_tool="codex",
        )

    loop = checks.run_check_fix_loop(
        checks_runner=lambda: checks_sequence.pop(0),
        fixer=fixer,
        dispatch_first=False,
    )
    fallback = raw.with_name(f"{raw.stem}.redacted.log")
    assert loop.status == "ok"
    assert dispatched == [str(fallback)]
    assert fallback.stat().st_mode & 0o777 == 0o600
    assert secret not in fallback.read_text(encoding="utf-8")


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

    captured: list[checks.FixOutcome] = []

    def fixer(_log: str) -> checks.FixOutcome:
        outcome = checks.FixOutcome(
            status="main-agent-required",
            delta_paths=(),
            failure_reason="dispatch-failed",
            commit_sha=None,
            head_changed=False,
            coder_tool=None,
        )
        captured.append(outcome)
        return outcome

    loop = checks.run_check_fix_loop(
        checks_runner=checks_runner,
        fixer=fixer,
        dispatch_first=False,
        max_iter=3,
    )
    assert loop.status == "main-agent-required"
    assert captured[0].failure_reason == "dispatch-failed"
    assert checks.escalate(loop.status).outcome == Outcome.NEEDS_USER_INPUT


def test_run_check_fix_loop_check_first_no_changes_stale(tmp_path: Path) -> None:
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

    loop = checks.run_check_fix_loop(
        checks_runner=checks_runner,
        fixer=lambda _log: checks.FixOutcome(
            status="no-changes",
            delta_paths=(),
            failure_reason=None,
            commit_sha=None,
            head_changed=False,
            coder_tool="codex",
        ),
        dispatch_first=False,
        max_iter=3,
    )
    assert loop.status == "no-changes-stale"
    assert checks.escalate(loop.status).outcome == Outcome.STALLED


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


def test_run_relevant_checks_broken_symlink_fails_closed(
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
    (scripts / "relevant-checks.sh").symlink_to(repo / "missing.sh")
    result = checks.run_relevant_checks(
        StubRunner(),
        site="step6",
        tmpdir=str(session),
        repo_root=str(repo),
    )
    assert result.ok is False
    assert result.exit_code == 1


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
    runner = StubRunner(_with_ledger_stubs([_ok(log_body)]))
    result = checks.run_relevant_checks(
        runner,
        site="step6",
        tmpdir=str(session),
        repo_root=str(repo),
    )
    assert result.ok is True
    assert result.coverage == "full"
    assert result.warn is None


def test_run_relevant_checks_agent_lint_missing_warn(
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
    runner = StubRunner(_with_ledger_stubs([_ok("WARNING: agent-lint not found on PATH\n")]))
    result = checks.run_relevant_checks(
        runner,
        site="step6",
        tmpdir=str(session),
        repo_root=str(repo),
    )
    assert result.ok is True
    assert result.warn == "agent-lint-missing"


def test_run_relevant_checks_post_check_only_coverage(
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
    runner = StubRunner(_with_ledger_stubs([_ok("=== Running agent-lint ===\n")]))
    result = checks.run_relevant_checks(
        runner,
        site="step6",
        tmpdir=str(session),
        repo_root=str(repo),
    )
    assert result.ok is True
    assert result.coverage == "post-check-only"


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
    runner = StubRunner(_with_ledger_stubs([_ok(f"=== Running pre-commit\n{secret}\n", rc=1)]))
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
    assert Path(result.redacted_log_path).stat().st_mode & 0o777 == 0o600
    assert result.phase == "pre-commit"
    assert result.coverage == "changed-file-only"


def test_run_relevant_checks_rejects_dotdot_site(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cache = tmp_path / "cache"
    session = cache / "larch" / "sessions" / "claude-implement-test"
    session.mkdir(parents=True)
    monkeypatch.setenv("XDG_CACHE_HOME", str(cache))
    repo = tmp_path / "repo"
    repo.mkdir()
    result = checks.run_relevant_checks(
        StubRunner(),
        site="evil..step6",
        tmpdir=str(session),
        repo_root=str(repo),
    )
    assert result.ok is False
    assert result.exit_code == 2


def test_run_relevant_checks_non_executable_fails_closed(
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
    _ = check_script.write_text("#!/bin/sh\n", encoding="utf-8")
    _ = check_script.chmod(0o644)
    result = checks.run_relevant_checks(
        StubRunner(),
        site="step6",
        tmpdir=str(session),
        repo_root=str(repo),
    )
    assert result.ok is False
    assert result.exit_code == 126


def test_run_check_fix_loop_skipped_does_not_dispatch() -> None:
    def checks_runner() -> checks.ChecksResult:
        return checks.ChecksResult(
            ok=True,
            exit_code=0,
            site="step6",
            redacted_log_path=None,
            phase="unknown",
            coverage="changed-file-only",
            skipped=True,
            warn=None,
        )

    def fixer(_log: str) -> checks.FixOutcome:
        raise AssertionError("fixer must not run for skipped checks")

    loop = checks.run_check_fix_loop(
        checks_runner=checks_runner,
        fixer=fixer,
        dispatch_first=False,
    )
    assert loop.status == "ok"


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
        allowed_tmpdir=_lint_fix_dirs(tmp_path)[0],
        run_parent=_lint_fix_dirs(tmp_path)[1],
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
        allowed_tmpdir=_lint_fix_dirs(tmp_path)[0],
        run_parent=_lint_fix_dirs(tmp_path)[1],
    )
    assert outcome.status == "no-changes"


def test_run_lint_fix_missing_run_external_agent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    log = tmp_path / "log.txt"
    _ = log.write_text("failure\n", encoding="utf-8")
    repo = tmp_path / "repo"
    repo.mkdir()

    def missing_scripts_dir() -> Path:
        return repo / "scripts"

    monkeypatch.setattr(checks, "_plugin_scripts_dir", missing_scripts_dir)
    runner = StubRunner()
    outcome = checks.run_lint_fix(
        runner,
        site="step6",
        checks_log=str(log),
        repo_root=str(repo),
        codex_present=True,
        cursor_present=False,
        allowed_tmpdir=_lint_fix_dirs(tmp_path)[0],
        run_parent=_lint_fix_dirs(tmp_path)[1],
    )
    assert outcome.status == "failed"
    assert outcome.failure_reason == "missing-run-external-agent"


def test_run_lint_fix_codex_argv_parity(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    run_external = checks._run_external_agent_sh()  # pyright: ignore[reportPrivateUsage]
    log = tmp_path / "checks.log"
    _ = log.write_text("lint error\n", encoding="utf-8")
    head = "abc123"
    runner = StubRunner([
        _ok(""),  # baseline tracked diff
        _ok(""),  # baseline cached diff
        _ok(""),  # baseline untracked status
        _ok(head + "\n"),  # rev-parse HEAD
        _ok("main\n"),  # symbolic-ref
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
        allowed_tmpdir=_lint_fix_dirs(tmp_path)[0],
        run_parent=_lint_fix_dirs(tmp_path)[1],
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
    assert "lib-external-launcher-common.sh" in flat
    assert "--tool" in flat
    assert "codex" in flat


def test_run_lint_fix_dispatch_failure_ignores_health_classification(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    log = tmp_path / "checks.log"
    _ = log.write_text("lint error\n", encoding="utf-8")
    head = "abc123"

    def fail_codex(*_args: object, **_kwargs: object) -> int:
        return 1

    def classify_must_not_run(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("dispatch failure classification must not select status")

    monkeypatch.setattr(checks, "_run_codex", fail_codex)
    monkeypatch.setattr("agents.classify_launch_failure", classify_must_not_run)
    runner = StubRunner([
        _ok(""),  # baseline tracked diff
        _ok(""),  # baseline cached diff
        _ok(""),  # baseline untracked status
        _ok(head + "\n"),  # rev-parse HEAD
        _ok("main\n"),  # symbolic-ref
        _ok(""),  # submodule foreach
    ])
    outcome = checks.run_lint_fix(
        runner,
        site="step6",
        checks_log=str(log),
        repo_root=str(repo),
        codex_present=True,
        cursor_present=False,
        allowed_tmpdir=_lint_fix_dirs(tmp_path)[0],
        run_parent=_lint_fix_dirs(tmp_path)[1],
    )
    assert outcome.status == "main-agent-required"
    assert outcome.failure_reason == "dispatch-failed"


def test_run_lint_fix_git_commit_applied_path(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    log = tmp_path / "checks.log"
    _ = log.write_text("lint error\n", encoding="utf-8")
    head = "abc123"
    commit = "def456"
    runner = StubRunner([
        _ok(""),  # baseline tracked diff
        _ok(""),  # baseline cached diff
        _ok(""),  # baseline untracked status
        _ok(head + "\n"),  # baseline HEAD
        _ok("main\n"),  # branch
        _ok(""),  # submodule foreach
        _ok(""),  # codex dispatch succeeds
        _ok(head + "\n"),  # current HEAD after dispatch
        _ok("fixed.py\n"),  # forbidden-revert tracked diff
        _ok(""),  # forbidden-revert cached diff
        _ok(""),  # forbidden-revert untracked status
        _ok("fixed.py\n"),  # current tracked diff
        _ok(""),  # current cached diff
        _ok(""),  # current untracked status
        _ok(""),  # git add
        _ok(""),  # git-commit.sh
        _ok(commit + "\n"),  # commit SHA
    ])
    outcome = checks.run_lint_fix(
        runner,
        site="step6",
        checks_log=str(log),
        repo_root=str(repo),
        codex_present=True,
        cursor_present=False,
        allowed_tmpdir=_lint_fix_dirs(tmp_path)[0],
        run_parent=_lint_fix_dirs(tmp_path)[1],
    )
    assert outcome.status == "applied"
    assert outcome.delta_paths == ("fixed.py",)
    assert outcome.commit_sha == commit
    flat = " ".join(arg for call, _kw in runner.calls for arg in call)
    assert "git-commit.sh" in flat


def test_run_lint_fix_forbidden_reset_failure_is_structural(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    log = tmp_path / "checks.log"
    _ = log.write_text("lint error\n", encoding="utf-8")
    head = "abc123"
    moved = "def456"
    runner = StubRunner([
        _ok(""),  # baseline tracked diff
        _ok(""),  # baseline cached diff
        _ok(""),  # baseline untracked status
        _ok(head + "\n"),  # baseline HEAD
        _ok("main\n"),  # baseline branch
        _ok(""),  # submodule foreach
        _ok(""),  # codex dispatch succeeds
        _ok(moved + "\n"),  # current HEAD after dispatch
        _ok("main\n"),  # current branch
        _ok(""),  # merge-base --is-ancestor
        _ok(head + "\n"),  # current parent
        _ok("", rc=1),  # no second parent
        _ok(".gitmodules\n"),  # committed forbidden path
        _ok("", rc=1),  # reset fails
        _ok(moved + "\n"),  # HEAD still moved
    ])
    outcome = checks.run_lint_fix(
        runner,
        site="step6",
        checks_log=str(log),
        repo_root=str(repo),
        codex_present=True,
        cursor_present=False,
        allowed_tmpdir=_lint_fix_dirs(tmp_path)[0],
        run_parent=_lint_fix_dirs(tmp_path)[1],
    )
    assert outcome.status == "failed"
    assert outcome.failure_reason == "forbidden-path-reset-failed"


def test_run_lint_fix_committed_forbidden_delta_reset_success_is_violation(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    log = tmp_path / "checks.log"
    _ = log.write_text("lint error\n", encoding="utf-8")
    head = "abc123"
    moved = "def456"
    runner = StubRunner([
        _ok(""),  # baseline tracked diff
        _ok(""),  # baseline cached diff
        _ok(""),  # baseline untracked status
        _ok(head + "\n"),  # baseline HEAD
        _ok("main\n"),  # baseline branch
        _ok(""),  # submodule foreach
        _ok(""),  # codex dispatch succeeds
        _ok(moved + "\n"),  # current HEAD after dispatch
        _ok("main\n"),  # current branch
        _ok(""),  # merge-base --is-ancestor
        _ok(head + "\n"),  # current parent
        _ok("", rc=1),  # no second parent
        _ok(".gitmodules\n"),  # committed forbidden path
        _ok(""),  # reset succeeds
        _ok(head + "\n"),  # HEAD reset
    ])
    outcome = checks.run_lint_fix(
        runner,
        site="step6",
        checks_log=str(log),
        repo_root=str(repo),
        codex_present=True,
        cursor_present=False,
        allowed_tmpdir=_lint_fix_dirs(tmp_path)[0],
        run_parent=_lint_fix_dirs(tmp_path)[1],
    )
    assert outcome.status == "failed"
    assert outcome.failure_reason == "forbidden-path-violation"


def test_run_lint_fix_forbidden_worktree_delta_is_reverted(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    log = tmp_path / "checks.log"
    _ = log.write_text("lint error\n", encoding="utf-8")
    head = "abc123"
    runner = StubRunner([
        _ok(""),  # baseline tracked diff
        _ok(""),  # baseline cached diff
        _ok(""),  # baseline untracked status
        _ok(head + "\n"),  # baseline HEAD
        _ok("main\n"),  # branch
        _ok(""),  # submodule foreach
        _ok(""),  # codex dispatch succeeds
        _ok(head + "\n"),  # current HEAD after dispatch
        _ok(".gitmodules\n"),  # forbidden-revert tracked diff
        _ok(""),  # forbidden-revert cached diff
        _ok(""),  # forbidden-revert untracked status
        _ok(""),  # git checkout -- .gitmodules
    ])
    outcome = checks.run_lint_fix(
        runner,
        site="step6",
        checks_log=str(log),
        repo_root=str(repo),
        codex_present=True,
        cursor_present=False,
        allowed_tmpdir=_lint_fix_dirs(tmp_path)[0],
        run_parent=_lint_fix_dirs(tmp_path)[1],
    )
    assert outcome.status == "failed"
    assert outcome.failure_reason == "forbidden-path-violation"
    assert any(call[:3] == ("git", "checkout", "--") for call, _kw in runner.calls)


def test_run_lint_fix_cursor_argv_and_wrap_cwd(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    log = tmp_path / "checks.log"
    _ = log.write_text("lint error\n", encoding="utf-8")
    head = "abc123"
    runner = StubRunner([
        _ok(""),  # baseline tracked diff
        _ok(""),  # baseline cached diff
        _ok(""),  # baseline untracked status
        _ok(head + "\n"),  # baseline HEAD
        _ok("main\n"),  # branch
        _ok(""),  # submodule foreach
        _ok("\0__DELIM__\0"),  # cursor model/auth argv loader
        _ok("wrapped promptX"),  # cursor-wrap-prompt.sh
        _ok("", rc=1),  # cursor dispatch fails
        _ok(""),  # stderr-tail helper
    ])
    outcome = checks.run_lint_fix(
        runner,
        site="step6",
        checks_log=str(log),
        repo_root=str(repo),
        codex_present=False,
        cursor_present=True,
        allowed_tmpdir=_lint_fix_dirs(tmp_path)[0],
        run_parent=_lint_fix_dirs(tmp_path)[1],
    )
    assert outcome.status == "main-agent-required"
    flat = " ".join(arg for call, _kw in runner.calls for arg in call)
    assert "lib-external-launcher-common.sh" in flat
    assert "--tool" in flat
    assert "cursor" in flat
    wrap_call, wrap_kwargs = next(
        (call, kw) for call, kw in runner.calls if "cursor-wrap-prompt.sh" in " ".join(call)
    )
    assert "cursor-wrap-prompt.sh" in " ".join(wrap_call)
    assert wrap_kwargs["cwd"] == str(repo)
    cursor_call = next(
        call for call, _kw in runner.calls
        if "cursor" in call and "agent" in call
    )
    idx = list(cursor_call).index(str(checks._run_external_agent_sh()))  # pyright: ignore[reportPrivateUsage]
    argv = list(cursor_call)[idx:]
    assert argv[1:3] == ["--tool", "cursor"]
    assert "--timeout" in argv
    assert "1800" in argv
    assert "--capture-stdout" in argv
    assert "launch-cursor-ci.sh" not in " ".join(argv)
    leaf = argv[argv.index("--") + 1 :]
    assert leaf[:4] == ["cursor", "agent", "-p", "--trust"]
    assert "--workspace" in cursor_call
    assert str(repo) in cursor_call


def test_run_lint_fix_rejects_unknown_site(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    log = tmp_path / "checks.log"
    _ = log.write_text("lint error\n", encoding="utf-8")
    outcome = checks.run_lint_fix(
        StubRunner(),
        site="typo",
        checks_log=str(log),
        repo_root=str(repo),
        codex_present=True,
        cursor_present=False,
        allowed_tmpdir=_lint_fix_dirs(tmp_path)[0],
        run_parent=_lint_fix_dirs(tmp_path)[1],
    )
    assert outcome.status == "failed"
    assert outcome.failure_reason == "unknown-site"


def test_run_checks_phase_rejects_invalid_tmpdir_before_dispatch(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    result = checks.run_checks_phase(
        StubRunner(),
        tmpdir=str(tmp_path / "not-created"),
        repo_root=str(repo),
        codex_present=True,
        cursor_present=True,
        dispatch_first=True,
        initial_redacted_log=str(tmp_path / "initial.redacted.log"),
    )
    assert result.outcome == Outcome.TRANSIENT
    assert result.detail == "invalid-tmpdir"


def test_run_checks_phase_checks_site_and_fix_site_split(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cache = tmp_path / "cache"
    session = cache / "larch" / "sessions" / "claude-implement-test"
    session.mkdir(parents=True)
    monkeypatch.setenv("XDG_CACHE_HOME", str(cache))
    repo = tmp_path / "repo"
    repo.mkdir()
    log = session / "fail.redacted.log"
    _ = log.write_text("error\n", encoding="utf-8")
    captured: dict[str, str] = {}

    def fake_checks(runner: StubRunner, *, site: str, **kwargs: object) -> checks.ChecksResult:
        _ = runner, kwargs
        captured["checks_site"] = site
        return checks.ChecksResult(
            ok=False,
            exit_code=1,
            site=site,
            redacted_log_path=str(log),
            phase="pre-commit",
            coverage="changed-file-only",
            skipped=False,
            warn=None,
            raw_log_path=str(log),
        )

    def fake_fix(runner: StubRunner, *, site: str, **kwargs: object) -> checks.FixOutcome:
        _ = runner, kwargs
        captured["fix_site"] = site
        return checks.FixOutcome(
            status="main-agent-required",
            delta_paths=(),
            failure_reason=None,
            commit_sha=None,
            head_changed=False,
            coder_tool=None,
        )

    monkeypatch.setattr(checks, "run_relevant_checks", fake_checks)
    monkeypatch.setattr(checks, "run_lint_fix", fake_fix)
    result = checks.run_checks_phase(
        StubRunner(),
        tmpdir=str(session),
        repo_root=str(repo),
        codex_present=False,
        cursor_present=False,
        site="step6",
        checks_site="step6",
        fix_site="ship-pr-ci-initial",
    )
    assert result.outcome == Outcome.NEEDS_USER_INPUT
    assert captured == {"checks_site": "step6", "fix_site": "ship-pr-ci-initial"}


def test_run_checks_phase_threads_target_cmd_display(
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
    captured: list[str | None] = []

    def fake_fix(**kwargs: object) -> checks.FixOutcome:
        captured.append(kwargs["target_cmd_display"])  # type: ignore[index]
        return checks.FixOutcome(
            status="main-agent-required",
            delta_paths=(),
            failure_reason=None,
            commit_sha=None,
            head_changed=False,
            coder_tool=None,
        )

    def fake_run_lint_fix(*_args: object, **kwargs: object) -> checks.FixOutcome:
        return fake_fix(**kwargs)

    monkeypatch.setattr(checks, "run_lint_fix", fake_run_lint_fix)
    result = checks.run_checks_phase(
        StubRunner([_ok("=== Running pre-commit\n", rc=1)]),
        tmpdir=str(session),
        repo_root=str(repo),
        codex_present=False,
        cursor_present=False,
        site="ship-pr-ci-per-job",
        target_cmd_display="make py-test",
    )
    assert result.outcome == Outcome.NEEDS_USER_INPUT
    assert captured == ["make py-test"]


def test_run_checks_phase_rejects_target_cmd_display_for_non_per_job(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cache = tmp_path / "cache"
    session = cache / "larch" / "sessions" / "claude-implement-test"
    session.mkdir(parents=True)
    monkeypatch.setenv("XDG_CACHE_HOME", str(cache))
    repo = tmp_path / "repo"
    repo.mkdir()
    result = checks.run_checks_phase(
        StubRunner(),
        tmpdir=str(session),
        repo_root=str(repo),
        codex_present=False,
        cursor_present=False,
        site="step6",
        target_cmd_display="make py-test",
    )
    assert result.outcome == Outcome.TRANSIENT
    assert result.detail == "target-cmd-display-invalid"


def test_run_checks_phase_requires_target_cmd_display_for_per_job(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cache = tmp_path / "cache"
    session = cache / "larch" / "sessions" / "claude-implement-test"
    session.mkdir(parents=True)
    monkeypatch.setenv("XDG_CACHE_HOME", str(cache))
    repo = tmp_path / "repo"
    repo.mkdir()
    result = checks.run_checks_phase(
        StubRunner(),
        tmpdir=str(session),
        repo_root=str(repo),
        codex_present=False,
        cursor_present=False,
        site="ship-pr-ci-per-job",
    )
    assert result.outcome == Outcome.TRANSIENT
    assert result.detail == "target-cmd-display-invalid"


def test_run_lint_fix_rejects_checks_log_outside_run_parent_root(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    log = outside / "checks.log"
    _ = log.write_text("lint error\n", encoding="utf-8")
    session = tmp_path / "session"
    session.mkdir()
    outcome = checks.run_lint_fix(
        StubRunner(),
        site="step6",
        checks_log=str(log),
        repo_root=str(repo),
        codex_present=True,
        cursor_present=False,
        allowed_tmpdir=str(session),
        run_parent=str(session / "lint-fix-loop"),
    )
    assert outcome.status == "failed"
    assert outcome.failure_reason == "checks-log-invalid"


def test_run_check_fix_loop_rejects_initial_log_outside_allowed_tmpdir(tmp_path: Path) -> None:
    session = tmp_path / "session"
    session.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    initial = outside / "initial.redacted.log"
    _ = initial.write_text("error\n", encoding="utf-8")

    def checks_runner() -> checks.ChecksResult:
        raise AssertionError("checks must not run before confined initial log")

    def fixer(_log: str) -> checks.FixOutcome:
        raise AssertionError("fixer must not receive an unconfined log")

    loop = checks.run_check_fix_loop(
        checks_runner=checks_runner,
        fixer=fixer,
        dispatch_first=True,
        initial_redacted_log=str(initial),
        allowed_tmpdir=str(session),
    )
    assert loop.status == "dispatch-failed"


def test_run_lint_fix_codex_fail_cursor_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    log = tmp_path / "checks.log"
    _ = log.write_text("lint error\n", encoding="utf-8")
    head = "abc123"
    dispatch_calls: list[str] = []

    def fail_codex(*_args: object, **_kwargs: object) -> int:
        dispatch_calls.append("codex")
        return 1

    def succeed_cursor(*_args: object, **_kwargs: object) -> int:
        dispatch_calls.append("cursor")
        return 0

    monkeypatch.setattr(checks, "_run_codex", fail_codex)
    monkeypatch.setattr(checks, "_run_cursor", succeed_cursor)
    runner = StubRunner([
        _ok(""),  # baseline tracked diff
        _ok(""),  # baseline cached diff
        _ok(""),  # baseline untracked status
        _ok(head + "\n"),  # rev-parse HEAD
        _ok("main\n"),  # symbolic-ref
        _ok(""),  # submodule foreach
        _ok(head + "\n"),  # current HEAD after dispatch
        _ok("fixed.py\n"),  # forbidden-revert tracked diff
        _ok(""),  # forbidden-revert cached diff
        _ok(""),  # forbidden-revert untracked status
        _ok("fixed.py\n"),  # current tracked diff
        _ok(""),  # current cached diff
        _ok(""),  # untracked status
        _ok(""),  # git add
        _ok(""),  # git-commit.sh
        _ok("def456\n"),  # commit SHA
    ])
    outcome = checks.run_lint_fix(
        runner,
        site="step6",
        checks_log=str(log),
        repo_root=str(repo),
        codex_present=True,
        cursor_present=True,
        allowed_tmpdir=_lint_fix_dirs(tmp_path)[0],
        run_parent=_lint_fix_dirs(tmp_path)[1],
    )
    assert dispatch_calls == ["codex", "cursor"]
    assert outcome.status == "applied"
    assert outcome.coder_tool == "cursor"


def test_run_lint_fix_generic_failed_maps_dispatch_failed(tmp_path: Path) -> None:
    session = tmp_path / "session"
    session.mkdir()
    initial = session / "initial.redacted.log"
    _ = initial.write_text("error\n", encoding="utf-8")
    fail = checks.ChecksResult(
        ok=False,
        exit_code=1,
        site="step6",
        redacted_log_path=str(initial),
        phase="pre-commit",
        coverage="changed-file-only",
        skipped=False,
        warn=None,
        raw_log_path=str(initial),
    )

    loop = checks.run_check_fix_loop(
        checks_runner=lambda: fail,
        fixer=lambda _log: checks.FixOutcome(
            status="failed",
            delta_paths=(),
            failure_reason="forbidden-path-violation",
            commit_sha=None,
            head_changed=False,
            coder_tool="codex",
        ),
        dispatch_first=True,
        initial_redacted_log=str(initial),
        allowed_tmpdir=str(session),
    )
    assert loop.status == "dispatch-failed"
    assert checks.escalate(loop.status).outcome == Outcome.TRANSIENT


def test_run_check_fix_loop_max_iter_six_exhausted(tmp_path: Path) -> None:
    raw_log = tmp_path / "fail.log"
    redacted = tmp_path / "fail.redacted.log"
    _ = raw_log.write_text("error\n", encoding="utf-8")
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

    loop = checks.run_check_fix_loop(
        checks_runner=lambda: fail,
        fixer=lambda _log: checks.FixOutcome(
            status="applied",
            delta_paths=("a.py",),
            failure_reason=None,
            commit_sha=None,
            head_changed=False,
            coder_tool="codex",
        ),
        dispatch_first=False,
        max_iter=6,
    )
    assert loop.status == "exhausted"


def test_run_checks_phase_ok_when_checks_skipped(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cache = tmp_path / "cache"
    session = cache / "larch" / "sessions" / "claude-implement-test"
    session.mkdir(parents=True)
    monkeypatch.setenv("XDG_CACHE_HOME", str(cache))
    repo = tmp_path / "repo"
    repo.mkdir()
    result = checks.run_checks_phase(
        StubRunner(),
        tmpdir=str(session),
        repo_root=str(repo),
        codex_present=True,
        cursor_present=True,
    )
    assert result.outcome == Outcome.OK


def test_run_lint_fix_non_executable_run_external_agent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    scripts = repo / "scripts"
    scripts.mkdir(parents=True)
    run_external = scripts / "run-external-agent.sh"
    _ = run_external.write_text("#!/bin/sh\n", encoding="utf-8")
    _ = run_external.chmod(0o644)
    log = tmp_path / "checks.log"
    _ = log.write_text("failure\n", encoding="utf-8")
    monkeypatch.setattr(checks, "_plugin_scripts_dir", lambda: scripts)
    outcome = checks.run_lint_fix(
        StubRunner(),
        site="step6",
        checks_log=str(log),
        repo_root=str(repo),
        codex_present=True,
        cursor_present=False,
        allowed_tmpdir=_lint_fix_dirs(tmp_path)[0],
        run_parent=_lint_fix_dirs(tmp_path)[1],
    )
    assert outcome.status == "failed"
    assert outcome.failure_reason == "missing-run-external-agent"


def test_run_check_fix_loop_requires_allowed_tmpdir_for_dispatch_first(
    tmp_path: Path,
) -> None:
    initial = tmp_path / "initial.redacted.log"
    _ = initial.write_text("error\n", encoding="utf-8")
    loop = checks.run_check_fix_loop(
        checks_runner=lambda: checks.ChecksResult(
            ok=True,
            exit_code=0,
            site="step6",
            redacted_log_path=None,
            phase="unknown",
            coverage="full",
            skipped=False,
            warn=None,
        ),
        fixer=lambda _log: checks.FixOutcome(
            status="applied",
            delta_paths=(),
            failure_reason=None,
            commit_sha=None,
            head_changed=False,
            coder_tool="codex",
        ),
        dispatch_first=True,
        initial_redacted_log=str(initial),
    )
    assert loop.status == "dispatch-failed"


def test_compose_prompt_redacts_checks_log_path(tmp_path: Path) -> None:
    cache = tmp_path / "cache" / "larch" / "sessions" / "claude-implement-secret"
    cache.mkdir(parents=True)
    log = cache / "checks.log"
    _ = log.write_text("failure\n", encoding="utf-8")
    prompt = checks._compose_prompt(  # pyright: ignore[reportPrivateUsage]
        checks_log=log,
        site_label="Step 6",
        submodule_paths=(),
        target_cmd_display=None,
    )
    assert str(log) not in prompt
    assert "claude-implement-secret" not in prompt


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


def test_compose_prompt_includes_submodule_prohibition(tmp_path: Path) -> None:
    log = tmp_path / "checks.log"
    _ = log.write_text("failure\n", encoding="utf-8")
    prompt = checks._compose_prompt(  # pyright: ignore[reportPrivateUsage]
        checks_log=log,
        site_label="Step 6",
        submodule_paths=("vendor/lib",),
        target_cmd_display=None,
    )
    assert "## PROHIBITION: Submodules" in prompt
    assert "- vendor/lib" in prompt
    assert "Do NOT touch `.git/`, `.gitmodules`, or any path under a submodule." in prompt


def test_read_log_tail_truncation_uses_constant(tmp_path: Path) -> None:
    log = tmp_path / "large.log"
    _ = log.write_bytes(b"a" * (checks._PROMPT_TAIL_BYTES + 1))  # pyright: ignore[reportPrivateUsage]
    text = checks._read_log_tail(log, checks._PROMPT_TAIL_BYTES)  # pyright: ignore[reportPrivateUsage]
    assert text.startswith(f"[truncated to last {checks._PROMPT_TAIL_BYTES} bytes]\n")  # pyright: ignore[reportPrivateUsage]


def test_read_log_text_bounded_uses_seek_not_full_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    log = tmp_path / "large.log"
    _ = log.write_bytes(b"x" * (checks._PROMPT_TAIL_BYTES + 5000))  # pyright: ignore[reportPrivateUsage]

    def fail_read_bytes(_self: object, *_args: object, **_kwargs: object) -> bytes:
        raise AssertionError("read_bytes must not load entire log for tail reads")

    monkeypatch.setattr(Path, "read_bytes", fail_read_bytes)
    text = checks._read_log_text_bounded(log, 100)  # pyright: ignore[reportPrivateUsage]
    assert text is not None
    assert text.startswith("[truncated to last 100 bytes]\n")


def test_run_relevant_checks_rejects_invalid_tmpdir() -> None:
    result = checks.run_relevant_checks(
        StubRunner(),
        site="step6",
        tmpdir="/not-a-session",
        repo_root="/tmp",
    )
    assert result.ok is False
    assert result.exit_code == 2


def _session_path_under_tmp(name: str) -> Path:
    return Path("/tmp") / f"claude-implement-{name}"


def _session_path_under_private_tmp(name: str) -> Path:
    return Path("/private/tmp") / f"claude-implement-{name}"


@pytest.mark.parametrize(
    "session_path",
    [
        pytest.param(_session_path_under_tmp, id="tmp"),
        pytest.param(
            _session_path_under_private_tmp,
            id="private_tmp",
            marks=pytest.mark.skipif(
                not Path("/private/tmp").is_dir(),
                reason="/private/tmp not present",
            ),
        ),
    ],
)
def test_validate_tmpdir_accepts_tmp_roots(
    tmp_path: Path,
    session_path: Callable[[str], Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = session_path(tmp_path.name)
    session.mkdir(parents=True, exist_ok=True)
    monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
    assert checks.validate_tmpdir(str(session)) == session.resolve()


def test_run_relevant_checks_parses_header_markers_in_large_log(
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
    log_body = (
        "=== Running pre-commit\n"
        "=== Running agent-lint ===\n"
        + ("padding\n" * 50000)
    )
    runner = StubRunner(_with_ledger_stubs([_ok(log_body, rc=1)]))
    result = checks.run_relevant_checks(
        runner,
        site="step6",
        tmpdir=str(session),
        repo_root=str(repo),
    )
    assert result.ok is False
    assert result.phase == "agent-lint"
    assert result.coverage == "changed-file-only"


def test_run_relevant_checks_redaction_failure_removes_partial_file(
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
    runner = StubRunner(_with_ledger_stubs([_ok("=== Running pre-commit\nfail\n", rc=1)]))

    original_chmod = Path.chmod

    def chmod_fail(self: Path, mode: int, *args: object, **kwargs: object) -> None:
        if self.name.endswith(".redacted.log"):
            raise OSError("chmod failed")
        original_chmod(self, mode, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "chmod", chmod_fail)
    result = checks.run_relevant_checks(
        runner,
        site="step6",
        tmpdir=str(session),
        repo_root=str(repo),
    )
    assert result.redacted_log_path is None
    assert result.warn == "redaction-failed"
    assert result.raw_log_path is None
    redacted = session / "relevant-checks" / "step6-1.redacted.log"
    assert not redacted.exists()


def test_validate_tmpdir_rejects_empty_xdg_cache_home(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = tmp_path / "claude-implement-empty-xdg"
    session.mkdir()
    monkeypatch.setenv("XDG_CACHE_HOME", "")
    monkeypatch.chdir(tmp_path)
    assert checks.validate_tmpdir(str(session)) is None


def test_run_check_fix_loop_redaction_failed_dispatch_failed() -> None:
    fail = checks.ChecksResult(
        ok=False,
        exit_code=1,
        site="step6",
        redacted_log_path=None,
        phase="pre-commit",
        coverage="changed-file-only",
        skipped=False,
        warn="redaction-failed",
        raw_log_path=None,
    )

    def fixer_must_not_run(_log: str) -> checks.FixOutcome:
        raise AssertionError("fixer must not run")

    loop = checks.run_check_fix_loop(
        checks_runner=lambda: fail,
        fixer=fixer_must_not_run,
        dispatch_first=False,
        max_iter=3,
    )
    assert loop.status == "dispatch-failed"


def test_run_checks_phase_dispatch_first_wiring(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cache = tmp_path / "cache"
    session = cache / "larch" / "sessions" / "claude-implement-dispatch-first"
    session.mkdir(parents=True)
    monkeypatch.setenv("XDG_CACHE_HOME", str(cache))
    repo = tmp_path / "repo"
    repo.mkdir()
    initial = session / "initial.redacted.log"
    _ = initial.write_text("error\n", encoding="utf-8")
    after = session / "after.redacted.log"
    _ = after.write_text("error\n", encoding="utf-8")
    checks_sequence = [
        checks.ChecksResult(
            ok=False,
            exit_code=1,
            site="step6",
            redacted_log_path=str(after),
            phase="pre-commit",
            coverage="changed-file-only",
            skipped=False,
            warn=None,
            raw_log_path=str(after),
        ),
        checks.ChecksResult(
            ok=True,
            exit_code=0,
            site="step6",
            redacted_log_path=None,
            phase="unknown",
            coverage="full",
            skipped=False,
            warn=None,
        ),
    ]

    def fake_checks(runner: StubRunner, **kwargs: object) -> checks.ChecksResult:
        _ = runner, kwargs
        return checks_sequence.pop(0)

    def fake_fix(runner: StubRunner, **kwargs: object) -> checks.FixOutcome:
        _ = runner, kwargs
        return checks.FixOutcome(
            status="applied",
            delta_paths=("fixed.py",),
            failure_reason=None,
            commit_sha=None,
            head_changed=False,
            coder_tool="codex",
        )

    monkeypatch.setattr(checks, "run_relevant_checks", fake_checks)
    monkeypatch.setattr(checks, "run_lint_fix", fake_fix)
    result = checks.run_checks_phase(
        StubRunner(),
        tmpdir=str(session),
        repo_root=str(repo),
        codex_present=True,
        cursor_present=False,
        dispatch_first=True,
        initial_redacted_log=str(initial),
    )
    assert result.outcome == Outcome.OK
    assert result.payload == ("fixed.py",)


@pytest.mark.skipif(
    not (Path(__file__).resolve().parents[1] / "scripts" / "token-ledger.sh").is_file(),
    reason="token-ledger.sh missing",
)
def test_run_relevant_checks_marks_step6_ledger(
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
    runner = StubRunner(_with_ledger_stubs([_ok("")]))
    _ = checks.run_relevant_checks(
        runner,
        site="step6",
        tmpdir=str(session),
        repo_root=str(repo),
    )
    ledger_calls = [
        call for call, _kw in runner.calls
        if any(name.endswith(("token-ledger.sh", "timing-ledger.sh")) for name in call)
    ]
    assert len(ledger_calls) == 2
    assert all("Step 6 — checks second pass" in " ".join(call) for call in ledger_calls)
