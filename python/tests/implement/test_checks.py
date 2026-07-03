# pyright: reportUnusedCallResult=false, reportUnusedFunction=false
"""Tests for checks.py (stub Runner only; no bash executed)."""

from __future__ import annotations

import os
import shutil
import subprocess
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from larch.implement import checks
from larch.implement import checks_run_relevant as _crr
from larch.implement import checks_lint_fix as _clf
from larch.core import config
from larch.core import proc
from larch.outcomes import Outcome
from larch.core.proc import CommandResult

CLI_PATH = Path(__file__).resolve().parents[2] / "cli.py"


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
        _ = timeout, check
        argv_tuple = tuple(argv)
        self.calls.append((argv_tuple, {"cwd": cwd, "env": env}))
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
    # _mark_step_ledger always makes 2 runner.run calls: token mark + timing mark
    return [_ok(""), _ok(""), *responses]


def _timing_record_calls(
    runner: StubRunner,
    *,
    task_kind: str | None = None,
) -> list[tuple[tuple[str, ...], dict[str, object]]]:
    calls = [
        (call, kw)
        for call, kw in runner.calls
        if "timing" in call and "record-vendor-task" in call
    ]
    if task_kind is None:
        return calls
    return [
        (call, kw)
        for call, kw in calls
        if "--task-kind" in call and call[call.index("--task-kind") + 1] == task_kind
    ]


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


def test_checks_failure_digest_precommit_hook_record() -> None:
    text = (
        "=== Running pre-commit on 1 changed file(s) ===\n"
        "ruff.....................................................................Failed\n"
        "python/app.py:12:5: F401 imported but unused\n"
        "ERROR: command failed"
    )

    digest = _crr._build_checks_failure_digest(redacted_log_text=text, site="unit")  # pyright: ignore[reportPrivateUsage]

    assert "CHECKS_FAILURE_DIGEST v1" in digest
    assert "site=unit" in digest
    assert "digest_truncated=false" in digest
    assert "check=ruff" in digest
    assert "failure_count=2" in digest
    assert "first_location=python/app.py:12" in digest
    assert "first_error=python/app.py:12:5: F401 imported but unused" in digest


def test_checks_failure_digest_multiple_precommit_hooks_under_cap() -> None:
    text = (
        "=== Running pre-commit on 2 changed file(s) ===\n"
        "ruff.....................................................................Failed\n"
        "python/app.py:12: F401\n"
        "markdownlint.............................................................Failed\n"
        "docs/readme.md:7 MD013"
    )

    digest = _crr._build_checks_failure_digest(redacted_log_text=text, site="unit")  # pyright: ignore[reportPrivateUsage]

    assert digest.count("check=") == 2
    assert "check=ruff" in digest
    assert "check=markdownlint" in digest
    assert "digest_truncated=false" in digest


def test_checks_failure_digest_truncates_on_record_boundary(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_crr, "CHECKS_FAILURE_DIGEST_MAX_BYTES", 220)
    text = (
        "=== Running pre-commit on 2 changed file(s) ===\n"
        "ruff.....................................................................Failed\n"
        "python/app.py:12: F401\n"
        "markdownlint.............................................................Failed\n"
        "docs/readme.md:7 MD013"
    )

    digest = _crr._build_checks_failure_digest(redacted_log_text=text, site="unit")  # pyright: ignore[reportPrivateUsage]

    assert len(digest.encode("utf-8")) <= 220
    assert digest.encode("utf-8").decode("utf-8") == digest
    assert "digest_truncated=true" in digest
    assert "check=ruff" in digest
    assert "check=markdownlint" not in digest


def test_checks_failure_digest_direct_make_fallback() -> None:
    text = (
        "=== Running direct relevant make target(s): test-example ===\n"
        "ERROR: test-example failed\n"
        "tests/example.py:44: assertion failed"
    )

    digest = _crr._build_checks_failure_digest(redacted_log_text=text, site="unit")  # pyright: ignore[reportPrivateUsage]

    assert "check=test-example" in digest
    assert "first_location=tests/example.py:44" in digest
    assert "first_error=ERROR: test-example failed" in digest


def test_checks_failure_digest_direct_py_lint_markerless_failure() -> None:
    text = (
        "=== Running direct relevant make target(s): py-lint ===\n"
        "python/larch/foo.py:10:5: F401 'os' imported but unused\n"
        "make: *** [Makefile:42: py-lint] Error 1"
    )

    digest = _crr._build_checks_failure_digest(redacted_log_text=text, site="unit")  # pyright: ignore[reportPrivateUsage]

    assert "check=py-lint" in digest
    assert "failure_count=1" in digest
    assert "first_location=python/larch/foo.py:10" in digest
    assert "first_error=python/larch/foo.py:10:5: F401 'os' imported but unused" in digest
    assert "first_location=unknown" not in digest
    assert "first_error=unknown" not in digest


def test_checks_failure_digest_direct_make_error_tail() -> None:
    text = (
        "=== Running direct relevant make target(s): py-lint ===\n"
        "make: *** [Makefile:42: py-lint] Error 1"
    )

    digest = _crr._build_checks_failure_digest(redacted_log_text=text, site="unit")  # pyright: ignore[reportPrivateUsage]

    assert "check=py-lint" in digest
    assert "failure_count=1" in digest
    assert "first_error=make: *** [Makefile:42: py-lint] Error 1" in digest


def test_checks_failure_digest_defect_lines_use_contains_pins() -> None:
    text = (
        "=== Running direct relevant make target(s): test-docs ===\n"
        "target succeeded\n"
        "DEFECT: skills/implement/SKILL.md:132 literal drift"
    )

    digest = _crr._build_checks_failure_digest(redacted_log_text=text, site="unit")  # pyright: ignore[reportPrivateUsage]

    assert "check=contains-pins" in digest
    assert "first_location=skills/implement/SKILL.md:132" in digest
    assert "check=test-docs" not in digest


def test_checks_failure_digest_cap_preserves_utf8(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_crr, "CHECKS_FAILURE_DIGEST_MAX_BYTES", 150)
    text = "ERROR: " + ("é" * 400)

    digest = _crr._build_checks_failure_digest(redacted_log_text=text, site="unit")  # pyright: ignore[reportPrivateUsage]

    assert len(digest.encode("utf-8")) <= 150
    assert digest.encode("utf-8").decode("utf-8") == digest


def test_checks_failure_digest_uses_only_redacted_source() -> None:
    secret = "ghp_" + "a" * 36
    text = f"ERROR: token {config.REDACTED_TOKEN}\n"

    digest = _crr._build_checks_failure_digest(redacted_log_text=text, site="unit")  # pyright: ignore[reportPrivateUsage]

    assert config.REDACTED_TOKEN in digest
    assert secret not in digest


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


def test_run_check_fix_loop_dispatch_first_no_changes_continues_after_failed_recheck(
    tmp_path: Path,
) -> None:
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
    checks_sequence = [fail, ok]
    fixes = [
        checks.FixOutcome(
            status="no-changes",
            delta_paths=(),
            failure_reason=None,
            commit_sha=None,
            head_changed=False,
            coder_tool="codex",
        ),
        checks.FixOutcome(
            status="applied",
            delta_paths=("fixed.py",),
            failure_reason=None,
            commit_sha="abc",
            head_changed=False,
            coder_tool="codex",
        ),
    ]
    fix_logs: list[str] = []

    def checks_runner() -> checks.ChecksResult:
        return checks_sequence.pop(0)

    def fixer(log: str) -> checks.FixOutcome:
        fix_logs.append(log)
        return fixes.pop(0)

    loop = checks.run_check_fix_loop(
        checks_runner=checks_runner,
        fixer=fixer,
        dispatch_first=True,
        max_iter=3,
        initial_redacted_log=str(initial),
        allowed_tmpdir=str(tmp_path),
    )
    assert loop.status == "ok"
    assert fix_logs == [str(initial), str(redacted)]
    assert loop.delta_paths == ("fixed.py",)


def test_run_check_fix_loop_dispatch_first_no_changes_stale_on_exhaustion(
    tmp_path: Path,
) -> None:
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
    fix_count = 0

    def checks_runner() -> checks.ChecksResult:
        return fail

    def fixer(_log: str) -> checks.FixOutcome:
        nonlocal fix_count
        fix_count += 1
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
    assert fix_count == 3


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



def _checks_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    cache = tmp_path / "cache"
    session = cache / "larch" / "sessions" / "claude-implement-test"
    session.mkdir(parents=True)
    monkeypatch.setenv("XDG_CACHE_HOME", str(cache))
    return session


def _git_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return repo


def _stub_tool(bin_dir: Path, name: str, body: str) -> None:
    path = bin_dir / name
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)


def _checks_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *, precommit: str, agent_lint: str | None = None, make: str | None = None) -> Path:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _stub_tool(bin_dir, "pre-commit", precommit)
    if agent_lint is not None:
        _stub_tool(bin_dir, "agent-lint", agent_lint)
    if make is not None:
        _stub_tool(bin_dir, "make", make)
    monkeypatch.setenv("PATH", f"{bin_dir}:{os.environ['PATH']}")
    return bin_dir


def test_run_relevant_checks_no_changed_files_runs_agent_lint(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _checks_session(tmp_path, monkeypatch)
    repo = _git_repo(tmp_path)
    _checks_path(
        monkeypatch,
        tmp_path,
        precommit="#!/usr/bin/env bash\nexit 0\n",
        agent_lint="#!/usr/bin/env bash\necho agent ok\n",
    )
    result = checks.run_relevant_checks(proc, site="unit", tmpdir=str(session), repo_root=str(repo))
    assert result.ok is True
    assert result.coverage == "post-check-only"


def test_run_relevant_checks_no_phase_fails_when_agent_lint_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _checks_session(tmp_path, monkeypatch)
    repo = _git_repo(tmp_path)
    bin_dir = _checks_path(monkeypatch, tmp_path, precommit="#!/usr/bin/env bash\nexit 0\n")
    monkeypatch.setenv("PATH", f"{bin_dir}:/usr/bin:/bin")
    result = checks.run_relevant_checks(proc, site="unit", tmpdir=str(session), repo_root=str(repo))
    assert result.ok is False
    assert result.redacted_log_path is not None


def test_run_relevant_checks_precommit_missing_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _checks_session(tmp_path, monkeypatch)
    repo = _git_repo(tmp_path)
    (repo / "file.py").write_text("print('ok')\n", encoding="utf-8")

    def available(*, runner: object, name: str, **_kwargs: object) -> bool:
        _ = runner
        return name != "pre-commit"

    monkeypatch.setattr(_crr, "_command_available", available)  # pyright: ignore[reportPrivateUsage]
    result = checks.run_relevant_checks(proc, site="unit", tmpdir=str(session), repo_root=str(repo))
    assert result.ok is False
    assert result.exit_code == 1
    assert result.redacted_log_path is not None


def test_run_relevant_checks_changed_file_precommit_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _checks_session(tmp_path, monkeypatch)
    repo = _git_repo(tmp_path)
    (repo / "file.py").write_text("print('ok')\n", encoding="utf-8")
    _checks_path(
        monkeypatch,
        tmp_path,
        precommit='#!/usr/bin/env bash\necho precommit "$@"\nexit 0\n',
        agent_lint="#!/usr/bin/env bash\necho agent ok\n",
    )
    result = checks.run_relevant_checks(proc, site="unit", tmpdir=str(session), repo_root=str(repo))
    assert result.ok is True
    assert result.coverage == "full"
    assert "=== Running pre-commit on 1 changed file(s) ===" in Path(result.raw_log_path or "").read_text(encoding="utf-8")


def test_run_relevant_checks_fail_produces_redacted_log(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _checks_session(tmp_path, monkeypatch)
    repo = _git_repo(tmp_path)
    (repo / "file.py").write_text("print('bad')\n", encoding="utf-8")
    secret = "sk-ant-abcdefghijklmnopqrstuvwxyz0123456789ABCD"
    _checks_path(
        monkeypatch,
        tmp_path,
        precommit=f"#!/usr/bin/env bash\necho '=== Running pre-commit'\necho 'ERROR: {secret}'\nexit 1\n",
    )
    result = checks.run_relevant_checks(proc, site="unit", tmpdir=str(session), repo_root=str(repo))
    assert result.ok is False
    assert result.redacted_log_path is not None
    redacted = Path(result.redacted_log_path).read_text(encoding="utf-8")
    assert secret not in redacted
    assert config.REDACTED_TOKEN in redacted
    assert Path(result.redacted_log_path).stat().st_mode & 0o777 == 0o600
    assert result.digest_file_path is not None
    digest_path = Path(result.digest_file_path)
    assert digest_path.stat().st_mode & 0o777 == 0o600
    digest = digest_path.read_text(encoding="utf-8")
    assert secret not in digest
    assert config.REDACTED_TOKEN in digest
    assert result.phase == "pre-commit"


def test_run_relevant_checks_precommit_failure_skips_later_phases(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _checks_session(tmp_path, monkeypatch)
    repo = _git_repo(tmp_path)
    changed = repo / "python" / "foo.py"
    changed.parent.mkdir()
    changed.write_text("print('bad')\n", encoding="utf-8")
    _checks_path(
        monkeypatch,
        tmp_path,
        precommit="#!/usr/bin/env bash\necho precommit failed\nexit 1\n",
    )
    calls = {
        "run_logged": 0,
        "direct_targets": 0,
        "contains_pin": 0,
        "agent_lint": 0,
    }

    def fake_run_logged(*, runner: object, argv: list[str], log_fd: int, **_kwargs: object) -> CommandResult:
        _ = runner
        calls["run_logged"] += 1
        assert argv[:3] == ["pre-commit", "run", "--files"]
        os.write(log_fd, b"precommit failed\n")
        return _ok("precommit failed\n", rc=1)

    def fake_direct_targets(*_args: object, **_kwargs: object) -> tuple[str, ...]:
        calls["direct_targets"] += 1
        return ()

    def fake_contains_pin_phase(*_args: object, **_kwargs: object) -> int:
        calls["contains_pin"] += 1
        return 0

    def fake_agent_lint(*_args: object, **_kwargs: object) -> int | None:
        calls["agent_lint"] += 1

    monkeypatch.setattr(_crr, "_run_logged", fake_run_logged)  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(_crr, "_direct_targets", fake_direct_targets)  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(_crr, "_run_contains_pin_phase", fake_contains_pin_phase)  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(_crr, "_run_agent_lint", fake_agent_lint)  # pyright: ignore[reportPrivateUsage]

    result = checks.run_relevant_checks(proc, site="unit", tmpdir=str(session), repo_root=str(repo))

    assert result.ok is False
    assert result.phase == "pre-commit"
    assert calls == {
        "run_logged": 1,
        "direct_targets": 0,
        "contains_pin": 0,
        "agent_lint": 0,
    }
    log = Path(result.raw_log_path or "").read_text(encoding="utf-8")
    marker_index = log.index("=== Running pre-commit on 1 changed file(s) ===")
    assert "precommit failed" in log[marker_index:]
    assert "=== Running direct relevant make target(s):" not in log[marker_index:]
    assert "=== Running agent-lint ===" not in log[marker_index:]
    assert "contains-pin" not in log[marker_index:]


def test_run_relevant_checks_python_change_skips_direct_make_fanout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _checks_session(tmp_path, monkeypatch)
    repo = _git_repo(tmp_path)
    changed = repo / "python" / "larch" / "review" / "review_and_fix.py"
    changed.parent.mkdir(parents=True)
    changed.write_text("print('ok')\n", encoding="utf-8")
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", "/plugin-cache")
    monkeypatch.setenv("LARCH_QUIET_ACTIVE", "1")
    _checks_path(
        monkeypatch,
        tmp_path,
        precommit="#!/usr/bin/env bash\nexit 0\n",
        agent_lint="#!/usr/bin/env bash\nexit 0\n",
        make="#!/usr/bin/env bash\necho 'make should not run' >&2\nexit 99\n",
    )
    result = checks.run_relevant_checks(proc, site="unit", tmpdir=str(session), repo_root=str(repo))
    assert result.ok is True
    assert result.raw_log_path is not None
    log = Path(result.raw_log_path).read_text(encoding="utf-8")
    assert "=== Running direct relevant make target(s):" not in log


def test_run_relevant_checks_rejects_dotdot_site(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _checks_session(tmp_path, monkeypatch)
    repo = _git_repo(tmp_path)
    result = checks.run_relevant_checks(StubRunner(), site="evil..step6", tmpdir=str(session), repo_root=str(repo))
    assert result.ok is False
    assert result.exit_code == 2
    assert result.failure_reason == "site-validation"


def test_run_relevant_checks_rejects_non_git_repo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _checks_session(tmp_path, monkeypatch)
    repo = tmp_path / "repo"
    repo.mkdir()
    result = checks.run_relevant_checks(proc, site="unit", tmpdir=str(session), repo_root=str(repo))
    assert result.ok is False
    assert result.failure_reason == "repo-root-unresolved"


def test_run_relevant_checks_records_vendor_task_with_runner(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _checks_session(tmp_path, monkeypatch)
    repo = tmp_path / "repo"
    repo.mkdir()
    runner = StubRunner(_with_ledger_stubs([_ok(f"{repo}\n")]))

    result = checks.run_relevant_checks(
        runner,
        site="step6",
        tmpdir=str(session),
        repo_root=str(repo),
    )

    assert result.ok is True
    timing_calls = _timing_record_calls(runner, task_kind="claude-relevant-checks")
    assert len(timing_calls) == 1
    call, kw = timing_calls[0]
    assert "--vendor" in call
    assert call[call.index("--vendor") + 1] == "claude"
    assert "--output" in call
    assert call[call.index("--output") + 1] == str(session / "claude-relevant-checks.txt")
    assert "--status" in call
    assert call[call.index("--status") + 1] == "complete"
    env = kw["env"]
    assert isinstance(env, Mapping)
    assert env["IMPLEMENT_TMPDIR"] == str(session)
    assert env["DESIGN_TMPDIR"] == ""
    assert runner.calls[-1][0] == call


def test_run_relevant_checks_records_exception_timing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _checks_session(tmp_path, monkeypatch)
    runner = StubRunner()

    def fail_impl(*_args: object, **_kwargs: object) -> checks.ChecksResult:
        raise RuntimeError("boom")

    monkeypatch.setattr(_crr, "_run_relevant_checks_impl", fail_impl)

    with pytest.raises(RuntimeError, match="boom"):
        checks.run_relevant_checks(
            runner,
            site="step6",
            tmpdir=str(session),
            repo_root=str(tmp_path / "repo"),
        )

    timing_calls = _timing_record_calls(runner, task_kind="claude-relevant-checks")
    assert len(timing_calls) == 1
    call, _kw = timing_calls[0]
    assert "--exit-code" in call
    assert call[call.index("--exit-code") + 1] == "1"
    assert "--status" in call
    assert call[call.index("--status") + 1] == "complete"


def test_run_relevant_checks_timing_failure_is_non_fatal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _checks_session(tmp_path, monkeypatch)

    class TimingFailRunner(StubRunner):
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
            if "timing" in argv and "record-vendor-task" in argv:
                raise RuntimeError("timing failed")
            return super().run(
                argv,
                timeout=timeout,
                cwd=cwd,
                env=env,
                check=check,
                stdout=stdout,
                stderr=stderr,
            )

    def ok_impl(*_args: object, **_kwargs: object) -> checks.ChecksResult:
        return checks.ChecksResult(
            ok=True,
            exit_code=0,
            site="step6",
            redacted_log_path=None,
            phase="unknown",
            coverage="post-check-only",
            skipped=False,
            warn=None,
        )

    monkeypatch.setattr(_crr, "_run_relevant_checks_impl", ok_impl)
    result = checks.run_relevant_checks(
        TimingFailRunner(),
        site="step6",
        tmpdir=str(session),
        repo_root=str(tmp_path / "repo"),
    )
    assert result.ok is True


def test_check_contains_pins_main_success_failure_and_scope(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    target = repo / "skills" / "demo" / "SKILL.md"
    target.parent.mkdir(parents=True)
    target.write_text("expected literal\n", encoding="utf-8")
    script = repo / "skills" / "demo" / "scripts" / "test-demo.sh"
    script.parent.mkdir(parents=True)
    script.write_text(
        'TARGET="$SCRIPT_DIR/../SKILL.md"\ncontains "$TARGET" "expected literal" "ok"\n',
        encoding="utf-8",
    )
    assert checks.check_contains_pins_main(["--repo-root", str(repo)]) == 0
    target.write_text("drift\n", encoding="utf-8")
    assert checks.check_contains_pins_main(["--repo-root", str(repo)]) == 1
    changed = tmp_path / "changed.txt"
    changed.write_text("README.md\n", encoding="utf-8")
    assert checks.check_contains_pins_main(["--repo-root", str(repo), "--changed-files", str(changed)]) == 0

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
        claude_present=False,
        allowed_tmpdir=_lint_fix_dirs(tmp_path)[0],
        run_parent=_lint_fix_dirs(tmp_path)[1],
    )
    assert outcome.status == "main-agent-required"
    assert outcome.ledger_failure_detail_log == str(log.resolve())
    timing_calls = _timing_record_calls(runner, task_kind="claude-lint-fix")
    assert len(timing_calls) == 1
    call, _kw = timing_calls[0]
    assert "--output" in call
    assert call[call.index("--output") + 1] == str(tmp_path / "claude-lint-fix.txt")
    assert "--exit-code" in call
    assert call[call.index("--exit-code") + 1] == "0"
    assert "--status" in call
    assert call[call.index("--status") + 1] == "complete"


def test_run_lint_fix_skips_outer_timing_for_claude_outcome(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = StubRunner()

    def claude_impl(*_args: object, **_kwargs: object) -> checks.FixOutcome:
        return checks.FixOutcome(
            status="applied",
            delta_paths=("fixed.py",),
            failure_reason=None,
            commit_sha="abc123",
            head_changed=True,
            coder_tool="claude",
        )

    monkeypatch.setattr(_clf, "_run_lint_fix_impl", claude_impl)

    outcome = checks.run_lint_fix(
        runner,
        site="step6",
        checks_log=str(tmp_path / "checks.log"),
        repo_root=str(tmp_path / "repo"),
        codex_present=False,
        cursor_present=False,
        allowed_tmpdir=str(tmp_path),
        run_parent=str(tmp_path / "lint-fix-loop"),
    )

    assert outcome.coder_tool == "claude"
    assert not _timing_record_calls(runner, task_kind="claude-lint-fix")


def test_run_lint_fix_records_exception_timing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = StubRunner()

    def fail_impl(*_args: object, **_kwargs: object) -> checks.FixOutcome:
        raise RuntimeError("boom")

    monkeypatch.setattr(_clf, "_run_lint_fix_impl", fail_impl)

    with pytest.raises(RuntimeError, match="boom"):
        checks.run_lint_fix(
            runner,
            site="step6",
            checks_log=str(tmp_path / "checks.log"),
            repo_root=str(tmp_path / "repo"),
            codex_present=False,
            cursor_present=False,
            allowed_tmpdir=str(tmp_path),
            run_parent=str(tmp_path / "lint-fix-loop"),
        )

    timing_calls = _timing_record_calls(runner, task_kind="claude-lint-fix")
    assert len(timing_calls) == 1
    call, _kw = timing_calls[0]
    assert "--exit-code" in call
    assert call[call.index("--exit-code") + 1] == "1"
    assert "--status" in call
    assert call[call.index("--status") + 1] == "complete"


def _assert_complexity_fast_fail(outcome: checks.FixOutcome, log: Path) -> None:
    assert outcome.status == "main-agent-required"
    assert outcome.failure_reason == "complexity-baseline-regression"
    assert outcome.ledger_ready is True
    assert outcome.ledger_dispatcher == "lint-fix-loop"
    assert outcome.ledger_exit_code == 1
    assert outcome.ledger_failure_detail_log == str(log.resolve())


def test_run_lint_fix_complexity_baseline_metric_growth_fast_fail(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    log = tmp_path / "checks.log"
    _ = log.write_text(
        "python3 python/cli.py lint complexity-baseline\n"
        "larch/core/proc.py:ProcRunner.run PLR0913 metric 8 > baseline 7\n",
        encoding="utf-8",
    )
    dispatch_calls: list[str] = []

    def fail_claude(*_args: object, **_kwargs: object) -> int:
        dispatch_calls.append("claude")
        raise AssertionError("claude must not run")

    def fail_codex(*_args: object, **_kwargs: object) -> int:
        dispatch_calls.append("codex")
        raise AssertionError("codex must not run")

    def fail_cursor(*_args: object, **_kwargs: object) -> int:
        dispatch_calls.append("cursor")
        raise AssertionError("cursor must not run")

    monkeypatch.setattr(_clf, "_run_claude", fail_claude)
    monkeypatch.setattr(_clf, "_run_codex", fail_codex)
    monkeypatch.setattr(_clf, "_run_cursor", fail_cursor)
    runner = StubRunner()

    outcome = checks.run_lint_fix(
        runner,
        site="step6",
        checks_log=str(log),
        repo_root=str(repo),
        claude_present=False,
        codex_present=True,
        cursor_present=False,
        allowed_tmpdir=_lint_fix_dirs(tmp_path)[0],
        run_parent=_lint_fix_dirs(tmp_path)[1],
    )

    _assert_complexity_fast_fail(outcome, log)
    assert not dispatch_calls
    assert runner.calls == _timing_record_calls(runner, task_kind="claude-lint-fix")


def test_run_lint_fix_complexity_baseline_new_identity_fast_fail(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    log = tmp_path / "checks.log"
    _ = log.write_text(
        "python3 python/cli.py lint complexity-baseline\n"
        "proc.py:run PLR0912 (new)\n",
        encoding="utf-8",
    )
    dispatch_calls: list[str] = []

    def fail_claude(*_args: object, **_kwargs: object) -> int:
        dispatch_calls.append("claude")
        raise AssertionError("claude must not run")

    def fail_codex(*_args: object, **_kwargs: object) -> int:
        dispatch_calls.append("codex")
        raise AssertionError("codex must not run")

    def fail_cursor(*_args: object, **_kwargs: object) -> int:
        dispatch_calls.append("cursor")
        raise AssertionError("cursor must not run")

    monkeypatch.setattr(_clf, "_run_claude", fail_claude)
    monkeypatch.setattr(_clf, "_run_codex", fail_codex)
    monkeypatch.setattr(_clf, "_run_cursor", fail_cursor)
    runner = StubRunner()

    outcome = checks.run_lint_fix(
        runner,
        site="step6",
        checks_log=str(log),
        repo_root=str(repo),
        claude_present=False,
        codex_present=True,
        cursor_present=False,
        allowed_tmpdir=_lint_fix_dirs(tmp_path)[0],
        run_parent=_lint_fix_dirs(tmp_path)[1],
    )

    _assert_complexity_fast_fail(outcome, log)
    assert not dispatch_calls
    assert runner.calls == _timing_record_calls(runner, task_kind="claude-lint-fix")


def test_run_lint_fix_complexity_baseline_plr0911_new_uses_normal_fixer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    log = tmp_path / "checks.log"
    _ = log.write_text(
        "python3 python/cli.py lint complexity-baseline\n"
        "larch/git/gh.py:pr_checks_not_ready_detail PLR0911 (new)\n",
        encoding="utf-8",
    )
    codex_calls: list[str] = []

    def fail_codex(*_args: object, **_kwargs: object) -> int:
        codex_calls.append("codex")
        return 1

    monkeypatch.setattr(_clf, "_run_codex", fail_codex)
    runner = StubRunner([
        _ok(""),  # baseline tracked diff
        _ok(""),  # baseline cached diff
        _ok(""),  # baseline untracked status
        _ok("abc123\n"),  # rev-parse HEAD
        _ok("main\n"),  # symbolic-ref
        _ok(""),  # submodule foreach (prompt)
        _ok(""),  # submodule foreach (forbidden paths)
    ])

    outcome = checks.run_lint_fix(
        runner,
        site="step6",
        checks_log=str(log),
        repo_root=str(repo),
        claude_present=False,
        codex_present=True,
        cursor_present=False,
        allowed_tmpdir=_lint_fix_dirs(tmp_path)[0],
        run_parent=_lint_fix_dirs(tmp_path)[1],
    )

    assert codex_calls == ["codex"]
    assert outcome.status == "main-agent-required"
    assert outcome.failure_reason == "dispatch-failed"
    assert outcome.failure_reason != "complexity-baseline-regression"


def test_run_lint_fix_complexity_baseline_plr0911_new_with_metric_fast_fail(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    log = tmp_path / "checks.log"
    _ = log.write_text(
        "python3 python/cli.py lint complexity-baseline\n"
        "larch/git/gh.py:pr_checks_not_ready_detail PLR0911 (new)\n"
        "larch/core/proc.py:ProcRunner.run PLR0913 metric 8 > baseline 7\n",
        encoding="utf-8",
    )
    dispatch_calls: list[str] = []

    def fail_claude(*_args: object, **_kwargs: object) -> int:
        dispatch_calls.append("claude")
        raise AssertionError("claude must not run")

    def fail_codex(*_args: object, **_kwargs: object) -> int:
        dispatch_calls.append("codex")
        raise AssertionError("codex must not run")

    def fail_cursor(*_args: object, **_kwargs: object) -> int:
        dispatch_calls.append("cursor")
        raise AssertionError("cursor must not run")

    monkeypatch.setattr(_clf, "_run_claude", fail_claude)
    monkeypatch.setattr(_clf, "_run_codex", fail_codex)
    monkeypatch.setattr(_clf, "_run_cursor", fail_cursor)
    runner = StubRunner()

    outcome = checks.run_lint_fix(
        runner,
        site="step6",
        checks_log=str(log),
        repo_root=str(repo),
        claude_present=False,
        codex_present=True,
        cursor_present=False,
        allowed_tmpdir=_lint_fix_dirs(tmp_path)[0],
        run_parent=_lint_fix_dirs(tmp_path)[1],
    )

    _assert_complexity_fast_fail(outcome, log)
    assert not dispatch_calls
    assert runner.calls == _timing_record_calls(runner, task_kind="claude-lint-fix")


def test_run_lint_fix_complexity_baseline_tool_error_uses_normal_fixer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    log = tmp_path / "checks.log"
    _ = log.write_text(
        "python3 python/cli.py lint complexity-baseline\n"
        "lint-complexity-baseline: ruff exited 2: boom\n",
        encoding="utf-8",
    )
    codex_calls: list[str] = []

    def fail_codex(*_args: object, **_kwargs: object) -> int:
        codex_calls.append("codex")
        return 1

    monkeypatch.setattr(_clf, "_run_codex", fail_codex)
    runner = StubRunner([
        _ok(""),  # baseline tracked diff
        _ok(""),  # baseline cached diff
        _ok(""),  # baseline untracked status
        _ok("abc123\n"),  # rev-parse HEAD
        _ok("main\n"),  # symbolic-ref
        _ok(""),  # submodule foreach (prompt)
        _ok(""),  # submodule foreach (forbidden paths)
    ])

    outcome = checks.run_lint_fix(
        runner,
        site="step6",
        checks_log=str(log),
        repo_root=str(repo),
        claude_present=False,
        codex_present=True,
        cursor_present=False,
        allowed_tmpdir=_lint_fix_dirs(tmp_path)[0],
        run_parent=_lint_fix_dirs(tmp_path)[1],
    )

    assert codex_calls == ["codex"]
    assert outcome.status == "main-agent-required"
    assert outcome.failure_reason == "dispatch-failed"
    assert outcome.failure_reason != "complexity-baseline-regression"


def test_run_lint_fix_complexity_baseline_no_tools_fast_fail(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    log = tmp_path / "checks.log"
    _ = log.write_text(
        "python3 python/cli.py lint complexity-baseline\n"
        "larch/core/proc.py:ProcRunner.run PLR0913 metric 8 > baseline 7\n",
        encoding="utf-8",
    )
    runner = StubRunner()

    outcome = checks.run_lint_fix(
        runner,
        site="step6",
        checks_log=str(log),
        repo_root=str(repo),
        claude_present=False,
        codex_present=False,
        cursor_present=False,
        allowed_tmpdir=_lint_fix_dirs(tmp_path)[0],
        run_parent=_lint_fix_dirs(tmp_path)[1],
    )

    _assert_complexity_fast_fail(outcome, log)
    assert outcome.failure_reason is not None
    assert outcome.ledger_exit_code == 1
    assert runner.calls == _timing_record_calls(runner, task_kind="claude-lint-fix")


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


def test_run_lint_fix_missing_scripts_dir_no_longer_checks_deleted_launcher(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    log = tmp_path / "log.txt"
    _ = log.write_text("failure\n", encoding="utf-8")
    repo = tmp_path / "repo"
    repo.mkdir()

    def missing_scripts_dir() -> Path:
        return repo / "scripts"

    monkeypatch.setattr(_crr, "plugin_scripts_dir", missing_scripts_dir)
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
    assert outcome.failure_reason is None


def test_run_lint_fix_codex_argv_parity(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    agent_cli = _clf._agent_cli()  # pyright: ignore[reportPrivateUsage]
    log = tmp_path / "checks.log"
    _ = log.write_text("lint error\n", encoding="utf-8")
    head = "abc123"
    runner = StubRunner([
        _ok(""),  # baseline tracked diff
        _ok(""),  # baseline cached diff
        _ok(""),  # baseline untracked status
        _ok(head + "\n"),  # rev-parse HEAD
        _ok("main\n"),  # symbolic-ref
        _ok(""),  # submodule foreach (prompt)
        _ok(""),  # submodule foreach (forbidden paths)
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
        if "launch-codex-exec" in call
    )
    idx = list(codex_call).index(str(agent_cli))
    argv = list(codex_call)[idx:]
    assert argv[:3] == [str(agent_cli), "agent", "launch-codex-exec"]
    assert "--timeout" in argv
    assert "300" in argv
    assert "--workdir" in argv
    assert str(repo) in argv
    assert "--prompt-file" in argv
    assert "--usage-label" in argv
    assert "codex_lint_fix" in argv
    assert "run-external-agent" not in argv


def test_build_codex_argv_grants_only_run_dir_and_repo(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    run_dir = tmp_path / "implement" / "lint-fix-loop" / "step5.1"
    session_root = tmp_path / "implement"
    repo.mkdir()
    run_dir.mkdir(parents=True)
    prompt_file = run_dir / "prompt.md"

    argv = _clf._build_codex_argv(  # pyright: ignore[reportPrivateUsage]
        agent_cli=_clf._agent_cli(),  # pyright: ignore[reportPrivateUsage]
        run_dir=run_dir,
        repo_root=str(repo),
        prompt_file=prompt_file,
    )

    add_dirs = [
        argv[index + 1]
        for index, value in enumerate(argv)
        if value == "--add-dir"
    ]
    assert add_dirs == [str(run_dir), str(repo)]
    assert str(session_root) not in add_dirs


@dataclass
class TokenWritingRunner(StubRunner):
    launcher_exit: int = 0
    append_rc: int = 0
    append_stderr: str = ""
    active_rc: int = 0
    active_stderr: str = ""

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
        _ = timeout, check, stdout, stderr
        argv_tuple = tuple(argv)
        self.calls.append((argv_tuple, {"cwd": cwd, "env": env}))
        if "launch-codex-exec" in argv_tuple:
            output = Path(argv_tuple[argv_tuple.index("--output") + 1])
            _ = output.with_suffix(output.suffix + ".token-record").write_text(
                "TOOL=codex\nINPUT=1\nOUTPUT=2\nTOTAL=3\nRAW=codex_lint_fix\n",
                encoding="utf-8",
            )
            return CommandResult(argv=argv_tuple, returncode=self.launcher_exit, stdout=f"LAUNCHER_EXIT={self.launcher_exit}\n", stderr="", duration=0.0)
        if "append-record" in argv_tuple:
            return CommandResult(argv=argv_tuple, returncode=self.append_rc, stdout="", stderr=self.append_stderr, duration=0.0)
        if "record-vendor-sidecar" in argv_tuple:
            return CommandResult(argv=argv_tuple, returncode=self.active_rc, stdout="", stderr=self.active_stderr, duration=0.0)
        return CommandResult(argv=argv_tuple, returncode=0, stdout="", stderr="", duration=0.0)


def _token_calls(runner: StubRunner, token_command: str) -> list[tuple[tuple[str, ...], dict[str, object]]]:
    return [(call, kw) for call, kw in runner.calls if token_command in call]


def test_run_codex_ingests_token_record_on_success_and_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    implement_tmpdir = tmp_path / "implement"
    run_dir = implement_tmpdir / "lint-fix-loop" / "step6.1"
    run_dir.mkdir(parents=True)
    monkeypatch.setenv("LARCH_TOKEN_LEDGER", str(tmp_path / "stale.jsonl"))
    monkeypatch.setenv("LARCH_TOKEN_SESSION_ID", "stale-session")
    monkeypatch.setenv("DESIGN_TMPDIR", str(tmp_path / "design"))
    monkeypatch.setenv("RESEARCH_TMPDIR", str(tmp_path / "research"))
    monkeypatch.setenv("SESSION_ENV_PATH", str(tmp_path / "session-env.sh"))

    for launcher_exit in (0, 7):
        runner = TokenWritingRunner(launcher_exit=launcher_exit)
        rc = _clf._run_codex(  # pyright: ignore[reportPrivateUsage]
            runner,
            agent_cli=_clf._agent_cli(),  # pyright: ignore[reportPrivateUsage]
            run_dir=run_dir,
            implement_tmpdir=implement_tmpdir,
            repo_root=str(repo),
            prompt_body="fix lint",
            site="step6",
        )

        assert rc == launcher_exit
        append_calls = _token_calls(runner, "append-record")
        active_calls = _token_calls(runner, "record-vendor-sidecar")
        assert len(append_calls) == 1
        assert len(active_calls) == 1
        append_argv = list(append_calls[0][0])
        token_record = run_dir / "codex.log.token-record"
        assert append_argv[:3] == ["python3", str(_clf._agent_cli()), "token"]  # pyright: ignore[reportPrivateUsage]
        assert append_argv[1] != "python/cli.py"
        assert append_argv[append_argv.index("--input") + 1] == str(token_record)
        assert append_argv[append_argv.index("--tmpdir") + 1] == str(implement_tmpdir)
        active_argv = list(active_calls[0][0])
        assert active_argv[:3] == ["python3", str(_clf._agent_cli()), "token"]  # pyright: ignore[reportPrivateUsage]
        assert active_argv[active_argv.index("--input") + 1] == str(token_record)
        active_env = active_calls[0][1]["env"]
        assert isinstance(active_env, Mapping)
        assert active_env["IMPLEMENT_TMPDIR"] == str(implement_tmpdir)
        for key in ("LARCH_TOKEN_LEDGER", "LARCH_TOKEN_SESSION_ID", "DESIGN_TMPDIR", "RESEARCH_TMPDIR", "SESSION_ENV_PATH"):
            assert key not in active_env


def test_run_codex_warns_on_append_failure_and_still_records_active_ledger(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    implement_tmpdir = tmp_path / "implement"
    run_dir = implement_tmpdir / "lint-fix-loop" / "step6.1"
    run_dir.mkdir(parents=True)
    runner = TokenWritingRunner(append_rc=13, append_stderr="append exploded")

    rc = _clf._run_codex(  # pyright: ignore[reportPrivateUsage]
        runner,
        agent_cli=_clf._agent_cli(),  # pyright: ignore[reportPrivateUsage]
        run_dir=run_dir,
        implement_tmpdir=implement_tmpdir,
        repo_root=str(repo),
        prompt_body="fix lint",
        site="step6",
    )

    assert rc == 0
    err = capsys.readouterr().err
    assert "WARNING: token append-record failed with exit 13" in err
    assert "append exploded" in err
    assert len(_token_calls(runner, "append-record")) == 1
    assert len(_token_calls(runner, "record-vendor-sidecar")) == 1


def test_run_codex_warns_on_active_ledger_failure(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    implement_tmpdir = tmp_path / "implement"
    run_dir = implement_tmpdir / "lint-fix-loop" / "step6.1"
    run_dir.mkdir(parents=True)
    runner = TokenWritingRunner(active_rc=9, active_stderr="ledger denied")

    rc = _clf._run_codex(  # pyright: ignore[reportPrivateUsage]
        runner,
        agent_cli=_clf._agent_cli(),  # pyright: ignore[reportPrivateUsage]
        run_dir=run_dir,
        implement_tmpdir=implement_tmpdir,
        repo_root=str(repo),
        prompt_body="fix lint",
        site="step6",
    )

    assert rc == 0
    err = capsys.readouterr().err
    assert "WARNING: token record-vendor-sidecar failed with exit 9" in err
    assert "ledger denied" in err


def test_run_codex_preserves_active_ledger_stderr_warning(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    implement_tmpdir = tmp_path / "implement"
    run_dir = implement_tmpdir / "lint-fix-loop" / "step6.1"
    run_dir.mkdir(parents=True)
    runner = TokenWritingRunner(active_stderr="unsupported TOOL=unknown")

    _ = _clf._run_codex(  # pyright: ignore[reportPrivateUsage]
        runner,
        agent_cli=_clf._agent_cli(),  # pyright: ignore[reportPrivateUsage]
        run_dir=run_dir,
        implement_tmpdir=implement_tmpdir,
        repo_root=str(repo),
        prompt_body="fix lint",
        site="step6",
    )

    assert "token record-vendor-sidecar: unsupported TOOL=unknown" in capsys.readouterr().err


def test_codex_lint_fix_prompt_appendix_binds_site_and_verification() -> None:
    appendix = _clf._codex_lint_fix_prompt_appendix("step5")  # pyright: ignore[reportPrivateUsage]

    assert "machine site `step5`" in appendix
    assert "checks run-relevant --site step5" in appendix
    assert "parent orchestrator owns verification after Codex exits" in appendix
    assert "Make repository file edits only." in appendix
    assert "`exec_command`" in appendix
    assert "shell" in appendix
    assert "`checks run-relevant` inside the Codex sandbox" in appendix
    assert "Do not create ad-hoc temporary verification roots" in appendix
    assert "mkdir -p /tmp" not in appendix


def test_run_codex_writes_shared_prompt_plus_codex_appendix(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    implement_tmpdir = tmp_path / "implement"
    run_dir = implement_tmpdir / "lint-fix-loop" / "step5.1"
    run_dir.mkdir(parents=True)
    runner = TokenWritingRunner()

    rc = _clf._run_codex(  # pyright: ignore[reportPrivateUsage]
        runner,
        agent_cli=_clf._agent_cli(),  # pyright: ignore[reportPrivateUsage]
        run_dir=run_dir,
        implement_tmpdir=implement_tmpdir,
        repo_root=str(repo),
        prompt_body="shared prompt\n",
        site="step5",
    )

    assert rc == 0
    prompt = (run_dir / "prompt.md").read_text(encoding="utf-8")
    assert prompt == "shared prompt\n" + _clf._codex_lint_fix_prompt_appendix("step5")  # pyright: ignore[reportPrivateUsage]


def test_run_lint_fix_threads_session_root_as_codex_implement_tmpdir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    implement_tmpdir = tmp_path / "implement"
    run_parent = implement_tmpdir / "lint-fix-loop"
    run_parent.mkdir(parents=True)
    log = implement_tmpdir / "checks.log"
    _ = log.write_text("lint error\n", encoding="utf-8")
    captured: dict[str, Path] = {}

    def fail_codex(*_args: object, **kwargs: object) -> int:
        captured["implement_tmpdir"] = kwargs["implement_tmpdir"]  # type: ignore[assignment]
        captured["run_dir"] = kwargs["run_dir"]  # type: ignore[assignment]
        return 1

    monkeypatch.setattr(_clf, "_run_codex", fail_codex)
    runner = StubRunner([
        _ok(""),  # baseline tracked diff
        _ok(""),  # baseline cached diff
        _ok(""),  # baseline untracked status
        _ok("abc123\n"),  # rev-parse HEAD
        _ok("main\n"),  # symbolic-ref
        _ok(""),  # submodule foreach (prompt)
        _ok(""),  # submodule foreach (forbidden paths)
    ])

    outcome = checks.run_lint_fix(
        runner,
        site="step6",
        checks_log=str(log),
        repo_root=str(repo),
        codex_present=True,
        cursor_present=False,
        claude_present=False,
        allowed_tmpdir=str(implement_tmpdir),
        run_parent=str(run_parent),
    )

    assert outcome.status == "main-agent-required"
    assert captured["implement_tmpdir"] == implement_tmpdir.resolve()
    assert captured["implement_tmpdir"] != run_parent
    assert captured["implement_tmpdir"] != captured["run_dir"]


def test_run_lint_fix_derives_implement_tmpdir_from_run_parent_without_allowed_tmpdir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    implement_tmpdir = tmp_path / "implement"
    run_parent = implement_tmpdir / "lint-fix-loop"
    run_parent.mkdir(parents=True)
    log = implement_tmpdir / "checks.log"
    _ = log.write_text("lint error\n", encoding="utf-8")
    captured: dict[str, Path] = {}

    def fail_codex(*_args: object, **kwargs: object) -> int:
        captured["implement_tmpdir"] = kwargs["implement_tmpdir"]  # type: ignore[assignment]
        return 1

    monkeypatch.setattr(_clf, "_run_codex", fail_codex)
    runner = StubRunner([
        _ok(""),  # baseline tracked diff
        _ok(""),  # baseline cached diff
        _ok(""),  # baseline untracked status
        _ok("abc123\n"),  # rev-parse HEAD
        _ok("main\n"),  # symbolic-ref
        _ok(""),  # submodule foreach (prompt)
        _ok(""),  # submodule foreach (forbidden paths)
    ])

    _ = checks.run_lint_fix(
        runner,
        site="step6",
        checks_log=str(log),
        repo_root=str(repo),
        codex_present=True,
        cursor_present=False,
        claude_present=False,
        allowed_tmpdir=None,
        run_parent=str(run_parent),
    )

    assert captured["implement_tmpdir"] == implement_tmpdir.resolve()


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

    monkeypatch.setattr(_clf, "_run_codex", fail_codex)
    monkeypatch.setattr("larch.agents.agents.classify_launch_failure", classify_must_not_run)
    runner = StubRunner([
        _ok(""),  # baseline tracked diff
        _ok(""),  # baseline cached diff
        _ok(""),  # baseline untracked status
        _ok(head + "\n"),  # rev-parse HEAD
        _ok("main\n"),  # symbolic-ref
        _ok(""),  # submodule foreach (prompt)
        _ok(""),  # submodule foreach (forbidden paths)
    ])
    outcome = checks.run_lint_fix(
        runner,
        site="step6",
        checks_log=str(log),
        repo_root=str(repo),
        codex_present=True,
        cursor_present=False,
        claude_present=False,
        allowed_tmpdir=_lint_fix_dirs(tmp_path)[0],
        run_parent=_lint_fix_dirs(tmp_path)[1],
    )
    assert outcome.status == "main-agent-required"
    assert outcome.failure_reason == "dispatch-failed"


def test_run_lint_fix_all_tools_timeout(tmp_path: Path) -> None:
    """Exit 124 (timeout) from every tier routes to main-agent-required, not failed."""
    repo = tmp_path / "repo"
    repo.mkdir()
    log = tmp_path / "checks.log"
    _ = log.write_text("lint error\n", encoding="utf-8")
    head = "abc123"
    runner = StubRunner([
        _ok(""),          # baseline tracked diff
        _ok(""),          # baseline cached diff
        _ok(""),          # baseline untracked status
        _ok(head + "\n"), # rev-parse HEAD
        _ok("main\n"),    # symbolic-ref
        _ok(""),          # submodule foreach (prompt)
        _ok(""),          # submodule foreach (forbidden paths)
        _ok("", rc=124),  # claude dispatch: timeout
        _ok("", rc=124),  # codex dispatch: timeout
    ])
    outcome = checks.run_lint_fix(
        runner,
        site="step6",
        checks_log=str(log),
        repo_root=str(repo),
        claude_present=True,
        codex_present=True,
        cursor_present=False,
        allowed_tmpdir=_lint_fix_dirs(tmp_path)[0],
        run_parent=_lint_fix_dirs(tmp_path)[1],
    )
    assert outcome.status == "main-agent-required"
    assert outcome.failure_reason in {"dispatch-failed", "lint-fix-budget-exceeded"}


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
        _ok(""),  # submodule foreach (prompt)
        _ok(""),  # submodule foreach (forbidden paths)
        _ok(""),  # codex dispatch succeeds
        _ok(head + "\n"),  # current HEAD after dispatch
        _ok("fixed.py\n"),  # forbidden-revert tracked diff
        _ok(""),  # forbidden-revert cached diff
        _ok(""),  # forbidden-revert untracked status
        _ok("fixed.py\n"),  # current tracked diff
        _ok(""),  # current cached diff
        _ok(""),  # current untracked status
        _ok(""),  # git add
        _ok(""),  # cli.py git commit
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
    assert "git commit --file" in flat


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
        _ok(""),  # submodule foreach (prompt)
        _ok(""),  # submodule foreach (forbidden paths)
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
        _ok(""),  # submodule foreach (prompt)
        _ok(""),  # submodule foreach (forbidden paths)
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
        _ok(""),  # submodule foreach (prompt)
        _ok(""),  # submodule foreach (forbidden paths)
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


def test_run_lint_fix_plugin_json_touch_is_reverted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    log = tmp_path / "checks.log"
    _ = log.write_text("lint error\n", encoding="utf-8")
    head = "abc123"

    def succeed_claude(*_args: object, **_kwargs: object) -> int:
        return 0

    monkeypatch.setattr(_clf, "_run_claude", succeed_claude)
    runner = StubRunner([
        _ok(""),  # baseline tracked diff
        _ok(""),  # baseline cached diff
        _ok(""),  # baseline untracked status
        _ok(head + "\n"),  # baseline HEAD
        _ok("main\n"),  # branch
        _ok(""),  # submodule foreach (prompt)
        _ok(""),  # submodule foreach (forbidden paths)
        _ok(head + "\n"),  # current HEAD after dispatch
        _ok(f"{config.PLUGIN_JSON_PATH}\n"),  # forbidden-revert tracked diff
        _ok(""),  # forbidden-revert cached diff
        _ok(""),  # forbidden-revert untracked status
        _ok(""),  # git checkout -- plugin.json
    ])
    outcome = checks.run_lint_fix(
        runner,
        site="step6",
        checks_log=str(log),
        repo_root=str(repo),
        claude_present=True,
        codex_present=False,
        cursor_present=False,
        allowed_tmpdir=_lint_fix_dirs(tmp_path)[0],
        run_parent=_lint_fix_dirs(tmp_path)[1],
    )
    assert outcome.status == "failed"
    assert outcome.failure_reason == "forbidden-path-violation"
    assert any(
        call[:4] == ("git", "checkout", "--", config.PLUGIN_JSON_PATH)
        for call, _kw in runner.calls
    )


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
        _ok(""),  # submodule foreach (prompt)
        _ok(""),  # submodule foreach (forbidden paths)
        _ok("wrapped promptX"),  # cursor-wrap-prompt.sh
        _ok("", rc=1),  # cursor dispatch fails
    ])
    outcome = checks.run_lint_fix(
        runner,
        site="step6",
        checks_log=str(log),
        repo_root=str(repo),
        codex_present=False,
        cursor_present=True,
        claude_present=False,
        allowed_tmpdir=_lint_fix_dirs(tmp_path)[0],
        run_parent=_lint_fix_dirs(tmp_path)[1],
    )
    assert outcome.status == "main-agent-required"
    flat = " ".join(arg for call, _kw in runner.calls for arg in call)
    assert "lib-external-launcher-common.sh" not in flat
    assert "--tool" in flat
    assert "cursor" in flat
    wrap_call, wrap_kwargs = next(
        (call, kw) for call, kw in runner.calls if any("cursor-wrap-prompt" in part for part in call)
    )
    assert any("agent" in part for part in wrap_call)
    assert any("cursor-wrap-prompt" in part for part in wrap_call)
    assert wrap_kwargs["cwd"] == str(repo)
    cursor_call = next(
        call for call, _kw in runner.calls
        if "cursor" in call and "agent" in call
    )
    idx = list(cursor_call).index(str(_clf._agent_cli()))  # pyright: ignore[reportPrivateUsage]
    argv = list(cursor_call)[idx:]
    assert argv[:4] == [str(_clf._agent_cli()), "agent", "run-external-agent", "--tool"]  # pyright: ignore[reportPrivateUsage]
    assert argv[4] == "cursor"
    assert "--timeout" in argv
    assert "300" in argv
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
            ledger_ready=True,
            ledger_site="ship-pr-internal",
            ledger_trigger=config.NEEDS_USER_SHIP_PR_INTERNAL_LINT_FIX,
            ledger_step="8",
            ledger_phase="ci-initial",
            ledger_dispatcher="lint-fix-loop",
            ledger_exit_code=1,
            ledger_failure_detail_log=str(log),
        )

    monkeypatch.setattr(_clf, "run_relevant_checks", fake_checks)
    monkeypatch.setattr(_clf, "run_lint_fix", fake_fix)
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
    assert result.detail == config.NEEDS_USER_SHIP_PR_INTERNAL_LINT_FIX
    assert result.ledger_ready is True
    assert result.ledger_site == "ship-pr-internal"
    assert result.ledger_trigger == "ship-pr-internal-lint-fix"
    assert result.ledger_phase == "ci-initial"
    assert result.ledger_failure_detail_log == str(log)
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

    log = session / "checks.redacted.log"
    log.write_text("=== Running pre-commit\n", encoding="utf-8")

    def fake_checks(*_args: object, **kwargs: object) -> checks.ChecksResult:
        return checks.ChecksResult(
            ok=False,
            exit_code=1,
            site=str(kwargs.get("site", "ship-pr-ci-per-job")),
            redacted_log_path=str(log),
            phase="pre-commit",
            coverage="changed-file-only",
            skipped=False,
            warn=None,
            raw_log_path=str(log),
        )

    monkeypatch.setattr(_clf, "run_relevant_checks", fake_checks)
    monkeypatch.setattr(_clf, "run_lint_fix", fake_run_lint_fix)
    result = checks.run_checks_phase(
        StubRunner(),
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
    assert outcome.ledger_failure_detail_log == ""


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


def test_run_lint_fix_dispatches_claude_before_codex(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    log = tmp_path / "checks.log"
    _ = log.write_text("lint error\n", encoding="utf-8")
    head = "abc123"
    dispatch_calls: list[str] = []

    def succeed_claude(*_args: object, **_kwargs: object) -> int:
        dispatch_calls.append("claude")
        return 0

    def fail_codex(*_args: object, **_kwargs: object) -> int:
        dispatch_calls.append("codex")
        return 1

    def fail_cursor(*_args: object, **_kwargs: object) -> int:
        dispatch_calls.append("cursor")
        return 1

    monkeypatch.setattr(_clf, "_run_claude", succeed_claude)
    monkeypatch.setattr(_clf, "_run_codex", fail_codex)
    monkeypatch.setattr(_clf, "_run_cursor", fail_cursor)
    runner = StubRunner([
        _ok(""),  # baseline tracked diff
        _ok(""),  # baseline cached diff
        _ok(""),  # baseline untracked status
        _ok(head + "\n"),  # rev-parse HEAD
        _ok("main\n"),  # symbolic-ref
        _ok(""),  # submodule foreach (prompt)
        _ok(""),  # submodule foreach (forbidden paths)
        _ok(head + "\n"),  # current HEAD after dispatch
        _ok("fixed.py\n"),  # forbidden-revert tracked diff
        _ok(""),  # forbidden-revert cached diff
        _ok(""),  # forbidden-revert untracked status
        _ok("fixed.py\n"),  # current tracked diff
        _ok(""),  # current cached diff
        _ok(""),  # untracked status
        _ok(""),  # git add
        _ok(""),  # cli.py git commit
        _ok("def456\n"),  # commit SHA
    ])
    outcome = checks.run_lint_fix(
        runner,
        site="step6",
        checks_log=str(log),
        repo_root=str(repo),
        claude_present=True,
        codex_present=True,
        cursor_present=True,
        allowed_tmpdir=_lint_fix_dirs(tmp_path)[0],
        run_parent=_lint_fix_dirs(tmp_path)[1],
    )
    assert dispatch_calls == ["claude"]
    assert outcome.status == "applied"
    assert outcome.coder_tool == "claude"


def test_run_lint_fix_codex_fail_cursor_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    log = tmp_path / "checks.log"
    _ = log.write_text("lint error\n", encoding="utf-8")
    head = "abc123"
    dispatch_calls: list[str] = []

    def fail_claude(*_args: object, **_kwargs: object) -> int:
        dispatch_calls.append("claude")
        return 1

    def fail_codex(*_args: object, **_kwargs: object) -> int:
        dispatch_calls.append("codex")
        return 1

    def succeed_cursor(*_args: object, **_kwargs: object) -> int:
        dispatch_calls.append("cursor")
        return 0

    monkeypatch.setattr(_clf, "_run_claude", fail_claude)
    monkeypatch.setattr(_clf, "_run_codex", fail_codex)
    monkeypatch.setattr(_clf, "_run_cursor", succeed_cursor)
    def claude_on_path(name: str) -> str | None:
        return "/usr/bin/claude" if name == "claude" else None

    monkeypatch.setattr(shutil, "which", claude_on_path)
    runner = StubRunner([
        _ok(""),  # baseline tracked diff
        _ok(""),  # baseline cached diff
        _ok(""),  # baseline untracked status
        _ok(head + "\n"),  # rev-parse HEAD
        _ok("main\n"),  # symbolic-ref
        _ok(""),  # submodule foreach (prompt)
        _ok(""),  # submodule foreach (forbidden paths)
        _ok(head + "\n"),  # current HEAD after dispatch
        _ok("fixed.py\n"),  # forbidden-revert tracked diff
        _ok(""),  # forbidden-revert cached diff
        _ok(""),  # forbidden-revert untracked status
        _ok("fixed.py\n"),  # current tracked diff
        _ok(""),  # current cached diff
        _ok(""),  # untracked status
        _ok(""),  # git add
        _ok(""),  # cli.py git commit
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
    assert dispatch_calls == ["claude", "codex", "cursor"]
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


def test_run_checks_phase_stalls_when_repo_unresolved(
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
    assert result.outcome == Outcome.STALLED


def test_run_lint_fix_non_executable_deleted_launcher_is_ignored(
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
    monkeypatch.setattr(_crr, "plugin_scripts_dir", lambda: scripts)
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
    assert outcome.status == "no-changes"
    assert outcome.failure_reason is None


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
    prompt = _clf._compose_prompt(  # pyright: ignore[reportPrivateUsage]
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
    prompt = _clf._compose_prompt(  # pyright: ignore[reportPrivateUsage]
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
    prompt = _clf._compose_prompt(  # pyright: ignore[reportPrivateUsage]
        checks_log=log,
        site_label="Step 6",
        submodule_paths=("vendor/lib",),
        target_cmd_display=None,
    )
    assert "## PROHIBITION: Submodules" in prompt
    assert "- vendor/lib" in prompt
    assert "Do NOT touch `.git/`, `.gitmodules`, or any path under a submodule." in prompt


def test_compose_prompt_includes_pyright_type_ignore_guidance(tmp_path: Path) -> None:
    log = tmp_path / "checks.log"
    _ = log.write_text(
        "python/test_collect_results.py:42:9 - error: ... (reportPrivateUsage)\n",
        encoding="utf-8",
    )
    prompt = _clf._compose_prompt(  # pyright: ignore[reportPrivateUsage]
        checks_log=log,
        site_label="Step 6",
        submodule_paths=(),
        target_cmd_display=None,
    )
    assert "## Pyright type errors" in prompt
    assert "# type: ignore[reportPrivateUsage]" in prompt
    assert "# type: ignore[reportUnknownArgumentType, reportUnknownLambdaType]" in prompt
    for code in (
        "reportPrivateUsage",
        "reportCallIssue",
        "reportArgumentType",
        "reportUnknownArgumentType",
        "reportUnknownLambdaType",
    ):
        assert code in prompt
    assert (
        "Do not rename private helpers or broaden APIs just to silence `reportPrivateUsage`."
        in prompt
    )


def test_compose_prompt_includes_plr0911_consolidation_guidance(tmp_path: Path) -> None:
    log = tmp_path / "checks.log"
    _ = log.write_text("larch/git/gh.py:42:5: PLR0911 Too many return statements\n", encoding="utf-8")
    prompt = _clf._compose_prompt(  # pyright: ignore[reportPrivateUsage]
        checks_log=log,
        site_label="Step 6",
        submodule_paths=(),
        target_cmd_display=None,
    )
    assert "## Ruff PLR0911 too many returns" in prompt
    assert "Ruff has no safe auto-fix for PLR0911." in prompt
    assert "Do not add `# noqa` or suppression comments for this case." in prompt


def test_compose_prompt_omits_codex_only_exec_prohibitions(tmp_path: Path) -> None:
    log = tmp_path / "checks.log"
    _ = log.write_text("failure\n", encoding="utf-8")
    prompt = _clf._compose_prompt(  # pyright: ignore[reportPrivateUsage]
        checks_log=log,
        site_label="Step 6",
        submodule_paths=(),
        target_cmd_display=None,
    )
    assert "Codex lint-fix task split" not in prompt
    assert "`exec_command`" not in prompt
    assert "inside the Codex sandbox" not in prompt


def test_read_log_tail_truncation_uses_constant(tmp_path: Path) -> None:
    log = tmp_path / "large.log"
    _ = log.write_bytes(b"a" * (_clf._PROMPT_TAIL_BYTES + 1))  # pyright: ignore[reportPrivateUsage]
    text = _clf._read_log_tail(path=log, max_bytes=_clf._PROMPT_TAIL_BYTES)  # pyright: ignore[reportPrivateUsage]
    assert text.startswith(f"[truncated to last {_clf._PROMPT_TAIL_BYTES} bytes]\n")  # pyright: ignore[reportPrivateUsage]


def test_read_log_text_bounded_uses_seek_not_full_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    log = tmp_path / "large.log"
    _ = log.write_bytes(b"x" * (_clf._PROMPT_TAIL_BYTES + 5000))  # pyright: ignore[reportPrivateUsage]

    def fail_read_bytes(_self: object, *_args: object, **_kwargs: object) -> bytes:
        raise AssertionError("read_bytes must not load entire log for tail reads")

    monkeypatch.setattr(Path, "read_bytes", fail_read_bytes)
    text = _clf._read_log_text_bounded(path=log, max_bytes=100)  # pyright: ignore[reportPrivateUsage]
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



def test_run_relevant_checks_redaction_failure_removes_partial_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _checks_session(tmp_path, monkeypatch)
    repo = _git_repo(tmp_path)
    (repo / "file.py").write_text("print('bad')\n", encoding="utf-8")
    _checks_path(
        monkeypatch,
        tmp_path,
        precommit="#!/usr/bin/env bash\necho '=== Running pre-commit'\necho fail\nexit 1\n",
    )
    original_chmod = Path.chmod

    def chmod_fail(self: Path, mode: int, *args: object, **kwargs: object) -> None:
        if self.name.endswith(".redacted.log"):
            raise OSError("chmod failed")
        original_chmod(self, mode, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "chmod", chmod_fail)
    result = checks.run_relevant_checks(proc, site="unit", tmpdir=str(session), repo_root=str(repo))
    assert result.redacted_log_path is None
    assert result.warn == "redaction-failed"
    assert result.raw_log_path is None
    assert not (session / "relevant-checks" / "unit-1.redacted.log").exists()

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

    monkeypatch.setattr(_clf, "run_relevant_checks", fake_checks)
    monkeypatch.setattr(_clf, "run_lint_fix", fake_fix)
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



def test_run_relevant_checks_marks_step6_ledger(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _checks_session(tmp_path, monkeypatch)
    repo = tmp_path / "repo"
    repo.mkdir()
    runner = StubRunner([_ok(""), _ok(""), _ok(f"{repo}\n")])
    _ = checks.run_relevant_checks(
        runner,
        site="step6",
        tmpdir=str(session),
        repo_root=str(repo),
    )
    ledger_calls = [
        call for call, _kw in runner.calls
        if any("cli.py" in name for name in call)
        and "record-vendor-task" not in call
    ]
    assert len(ledger_calls) == 2
    assert all("Step 6 — checks second pass" in " ".join(call) for call in ledger_calls)
    assert len(_timing_record_calls(runner, task_kind="claude-relevant-checks")) == 1

def test_lint_fix_main_agent_required_carries_ledger_tokens(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    runner = StubRunner()
    checks_log = tmp_path / "checks.log"
    _ = checks_log.write_text("lint failed\n", encoding="utf-8")
    run_parent = tmp_path / "lint-fix-loop"
    outcome = checks.run_lint_fix(
        runner,
        site="step5-self-review",
        checks_log=str(checks_log),
        repo_root=str(repo),
        codex_present=False,
        cursor_present=False,
        claude_present=False,
        run_parent=str(run_parent),
        allowed_tmpdir=str(tmp_path),
    )
    assert outcome.status == "main-agent-required"
    assert outcome.ledger_ready is True
    assert outcome.ledger_site == "step5-self-review"
    assert outcome.ledger_trigger == "main-agent-required"
    assert outcome.ledger_step == "5"
    assert outcome.ledger_phase == "review"
    assert outcome.ledger_dispatcher == "lint-fix-loop"
    assert outcome.ledger_failure_detail_log == str(checks_log.resolve())


def test_lint_fix_ship_pr_initial_carries_ci_initial_ledger_phase(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    checks_log = tmp_path / "checks.log"
    _ = checks_log.write_text("lint failed\n", encoding="utf-8")
    outcome = checks.run_lint_fix(
        StubRunner(),
        site="ship-pr-ci-initial",
        checks_log=str(checks_log),
        repo_root=str(repo),
        codex_present=False,
        cursor_present=False,
        claude_present=False,
        run_parent=str(tmp_path / "lint-fix-loop"),
        allowed_tmpdir=str(tmp_path),
    )
    assert outcome.status == "main-agent-required"
    assert outcome.ledger_ready is True
    assert outcome.ledger_site == "ship-pr-internal"
    assert outcome.ledger_trigger == "ship-pr-internal-lint-fix"
    assert outcome.ledger_step == "8"
    assert outcome.ledger_phase == "ci-initial"


def test_lint_fix_ship_pr_merge_handoffs_use_internal_ledger_tokens(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    checks_log = tmp_path / "checks.log"
    _ = checks_log.write_text("lint failed\n", encoding="utf-8")
    for site in ("ship-pr-ci-merge", "ship-pr-ci-per-job"):
        run_parent = tmp_path / "lint-fix-loop"
        outcome = checks.run_lint_fix(
            StubRunner(),
            site=site,
            checks_log=str(checks_log),
            repo_root=str(repo),
            codex_present=False,
            cursor_present=False,
            claude_present=False,
            run_parent=str(run_parent),
            allowed_tmpdir=str(tmp_path),
            target_cmd_display="make check-job" if site == "ship-pr-ci-per-job" else None,
        )
        assert outcome.status == "main-agent-required"
        assert outcome.ledger_ready is True
        assert outcome.ledger_site == "ship-pr-internal"
        assert outcome.ledger_trigger == "ship-pr-internal-lint-fix"
        assert outcome.ledger_step == "8"
        assert outcome.ledger_phase == "ci-merge"


def test_presence_flag_reads_session_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    session = _checks_session(tmp_path, monkeypatch)
    (session / "session-env.sh").write_text("CODEX_BINARY_FOUND=true\nCURSOR_BINARY_FOUND=false\n", encoding="utf-8")
    monkeypatch.delenv("CODEX_BINARY_FOUND", raising=False)
    monkeypatch.delenv("CURSOR_BINARY_FOUND", raising=False)
    assert _clf._binary_flag(name="CODEX_BINARY_FOUND", implement_tmpdir=session, binary="codex") is True  # pyright: ignore[reportPrivateUsage]
    assert _clf._binary_flag(name="CURSOR_BINARY_FOUND", implement_tmpdir=session, binary="cursor") is False  # pyright: ignore[reportPrivateUsage]


def test_checks_lint_fix_main_reads_presence_from_session_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _checks_session(tmp_path, monkeypatch)
    (session / "session-env.sh").write_text("CODEX_BINARY_FOUND=true\nCURSOR_BINARY_FOUND=false\n", encoding="utf-8")
    checks_log = session / "fail.redacted.log"
    checks_log.write_text("error\n", encoding="utf-8")
    captured: dict[str, object] = {}

    def fake_run_lint_fix(*_args: object, **kwargs: object) -> checks.FixOutcome:
        captured.update(kwargs)
        return checks.FixOutcome(
            status="no-changes",
            delta_paths=(),
            failure_reason=None,
            commit_sha=None,
            head_changed=False,
            coder_tool=None,
        )

    monkeypatch.setattr(_clf, "run_lint_fix", fake_run_lint_fix)
    monkeypatch.delenv("CODEX_BINARY_FOUND", raising=False)
    monkeypatch.delenv("CURSOR_BINARY_FOUND", raising=False)
    rc = checks.checks_lint_fix_main([
        "--tmpdir",
        str(session),
        "--site",
        "step3",
        "--checks-log",
        str(checks_log),
    ])
    assert rc == 0
    assert captured["codex_present"] is True
    assert captured["cursor_present"] is False




def _direct_targets_for(paths: tuple[str, ...], tmp_path: Path) -> tuple[str, ...]:
    return _crr._direct_targets(runner=StubRunner(), changed=paths, cwd=str(tmp_path), env=dict(os.environ), log_fd=2)  # pyright: ignore[reportPrivateUsage]


def test_direct_targets_are_ci_first_no_local_make_fanout(tmp_path: Path) -> None:
    assert _direct_targets_for(("skills/implement/SKILL.md",), tmp_path) == ()
    assert _direct_targets_for(("python/larch/review/review_and_fix.py",), tmp_path) == ()
    assert _direct_targets_for(("python/test_plan_review.py",), tmp_path) == ()


def test_local_relevant_checks_ci_superset_guard() -> None:
    precommit = Path(".pre-commit-config.yaml").read_text(encoding="utf-8")
    workflow = Path(".github/workflows/ci.yaml").read_text(encoding="utf-8")

    assert "id: ruff" in precommit
    assert "ruff check --fix" in precommit
    assert "id: pyright" in precommit
    assert "pyright --project python/pyrightconfig.json" in precommit
    assert "contains-pins:" in workflow
    assert "python3 python/cli.py checks contains-pins" in workflow
    assert "python-lint:" in workflow
    assert "python-pyright:" in workflow
    assert "agent-lint:" in workflow

def test_existing_regular_files_includes_symlink_to_file(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    target = repo / "real.py"
    target.write_text("x\n", encoding="utf-8")
    link = repo / "link.py"
    link.symlink_to(target)
    assert _crr._existing_regular_files(repo=repo, paths=("link.py",)) == ("link.py",)  # pyright: ignore[reportPrivateUsage]


def test_run_relevant_checks_deletion_only_runs_direct_targets(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _checks_session(tmp_path, monkeypatch)
    repo = _git_repo(tmp_path)
    make_calls: list[list[str]] = []
    direct_changed: list[tuple[str, ...]] = []

    def fake_changed_files(_runner: object, *, cwd: str) -> tuple[str, ...]:
        _ = cwd
        return ("scripts/read-result-env.sh",)

    def fake_direct(*, runner: object, changed: tuple[str, ...], **_kwargs: object) -> tuple[str, ...]:
        _ = runner
        direct_changed.append(changed)
        return ("test-read-result-env",)

    def fake_logged(*, runner: object, argv: list[str], **_kwargs: object) -> CommandResult:
        _ = runner
        if argv and argv[0] == "make":
            make_calls.append(list(argv))
        return _ok("")

    def fake_contains_pin_phase(*_args: object, **_kwargs: object) -> int:
        return 0

    def fake_agent_lint(*_args: object, **_kwargs: object) -> None:
        return None

    monkeypatch.setattr(_crr, "_changed_files", fake_changed_files)  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(_crr, "_direct_targets", fake_direct)  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(_crr, "_run_logged", fake_logged)  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(_crr, "_run_contains_pin_phase", fake_contains_pin_phase)  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(_crr, "_run_agent_lint", fake_agent_lint)  # pyright: ignore[reportPrivateUsage]

    def available(*, runner: object, name: str, **_kwargs: object) -> bool:
        _ = runner
        return name != "pre-commit"

    monkeypatch.setattr(_crr, "_command_available", available)  # pyright: ignore[reportPrivateUsage]
    result = checks.run_relevant_checks(proc, site="unit", tmpdir=str(session), repo_root=str(repo))
    assert result.ok is True
    assert direct_changed == [("scripts/read-result-env.sh",)]
    assert make_calls == [["make", "test-read-result-env"]]


def test_run_relevant_checks_skips_undefined_direct_make_targets(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _checks_session(tmp_path, monkeypatch)
    repo = _git_repo(tmp_path)
    (repo / "Makefile").write_text("test-read-result-env:\n\t@true\n", encoding="utf-8")
    make_calls: list[list[str]] = []

    def fake_changed_files(_runner: object, *, cwd: str) -> tuple[str, ...]:
        _ = cwd
        return ("scripts/unwired-direct-target.sh", "scripts/read-result-env.sh")

    def fake_direct(*, runner: object, changed: tuple[str, ...], **_kwargs: object) -> tuple[str, ...]:
        _ = (runner, changed)
        return ("test-unwired-direct-target", "test-read-result-env")

    def fake_logged(*, runner: object, argv: list[str], **_kwargs: object) -> CommandResult:
        _ = runner
        if argv and argv[0] == "make":
            make_calls.append(list(argv))
        return _ok("")

    def fake_contains_pin_phase(*_args: object, **_kwargs: object) -> int:
        return 0

    def fake_agent_lint(*_args: object, **_kwargs: object) -> None:
        return None

    monkeypatch.setattr(_crr, "_changed_files", fake_changed_files)  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(_crr, "_direct_targets", fake_direct)  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(_crr, "_run_logged", fake_logged)  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(_crr, "_run_contains_pin_phase", fake_contains_pin_phase)  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(_crr, "_run_agent_lint", fake_agent_lint)  # pyright: ignore[reportPrivateUsage]

    def available(*, runner: object, name: str, **_kwargs: object) -> bool:
        _ = runner
        return name != "pre-commit"

    monkeypatch.setattr(_crr, "_command_available", available)  # pyright: ignore[reportPrivateUsage]
    result = checks.run_relevant_checks(proc, site="unit", tmpdir=str(session), repo_root=str(repo))
    assert result.ok is True
    assert make_calls == [["make", "test-read-result-env"]]
    assert result.raw_log_path is not None
    log = Path(result.raw_log_path).read_text(encoding="utf-8")
    assert "skipping undefined direct make target(s): test-unwired-direct-target" in log


def test_run_relevant_checks_deletion_only_counts_contains_pins_phase(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _checks_session(tmp_path, monkeypatch)
    repo = _git_repo(tmp_path)

    def fake_changed_files(_runner: object, *, cwd: str) -> tuple[str, ...]:
        _ = cwd
        return ("scripts/unrouted-deleted.sh",)

    def fake_direct(*, runner: object, changed: tuple[str, ...], **_kwargs: object) -> tuple[str, ...]:
        _ = (runner, changed)
        return ()

    def fake_contains_pin_phase(*_args: object, **_kwargs: object) -> int:
        return 0

    def fake_agent_lint(*_args: object, **_kwargs: object) -> None:
        return None

    monkeypatch.setattr(_crr, "_changed_files", fake_changed_files)  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(_crr, "_direct_targets", fake_direct)  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(_crr, "_run_contains_pin_phase", fake_contains_pin_phase)  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(_crr, "_run_agent_lint", fake_agent_lint)  # pyright: ignore[reportPrivateUsage]

    def available(*, runner: object, name: str, **_kwargs: object) -> bool:
        _ = runner
        return name != "pre-commit"

    monkeypatch.setattr(_crr, "_command_available", available)  # pyright: ignore[reportPrivateUsage]
    result = checks.run_relevant_checks(proc, site="unit", tmpdir=str(session), repo_root=str(repo))
    assert result.ok is True
    assert result.exit_code == 0
    assert result.failure_reason is None


def test_run_relevant_checks_no_changes_skips_precommit_requirement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _checks_session(tmp_path, monkeypatch)
    repo = _git_repo(tmp_path)
    _checks_path(
        monkeypatch,
        tmp_path,
        precommit="#!/usr/bin/env bash\nexit 1\n",
        agent_lint="#!/usr/bin/env bash\necho agent ok\n",
    )

    def available(*, runner: object, name: str, **_kwargs: object) -> bool:
        _ = runner
        return name != "pre-commit"

    monkeypatch.setattr(_crr, "_command_available", available)  # pyright: ignore[reportPrivateUsage]
    result = checks.run_relevant_checks(proc, site="unit", tmpdir=str(session), repo_root=str(repo))
    assert result.ok is True


def test_checks_run_relevant_main_success_envelope(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    session = _checks_session(tmp_path, monkeypatch)

    def fake_checks(*_args: object, **kwargs: object) -> checks.ChecksResult:
        return checks.ChecksResult(
            ok=True,
            exit_code=0,
            site=str(kwargs["site"]),
            redacted_log_path=None,
            phase="pre-commit",
            coverage="changed-file-only",
            skipped=False,
            warn=None,
        )

    monkeypatch.setattr(_crr, "run_relevant_checks", fake_checks)
    rc = checks.checks_run_relevant_main(["--site", "step3", "--tmpdir", str(session)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "RELEVANT_CHECKS_OK=true" in out
    assert "SITE=step3" in out


def test_checks_run_relevant_main_fail_envelope(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    session = _checks_session(tmp_path, monkeypatch)
    log = session / "fail.redacted.log"
    log.write_text("err\n", encoding="utf-8")
    digest = session / "fail.digest.txt"
    digest.write_text("CHECKS_FAILURE_DIGEST v1\n", encoding="utf-8")

    def fake_checks(*_args: object, **_kwargs: object) -> checks.ChecksResult:
        return checks.ChecksResult(
            ok=False,
            exit_code=1,
            site="step3",
            redacted_log_path=str(log),
            phase="pre-commit",
            coverage="changed-file-only",
            skipped=False,
            warn=None,
            failure_reason="checks-failed",
            digest_file_path=str(digest),
        )

    monkeypatch.setattr(_crr, "run_relevant_checks", fake_checks)
    rc = checks.checks_run_relevant_main(["--site", "step3", "--tmpdir", str(session)])
    out = capsys.readouterr().out
    assert rc == 1
    assert "STATUS=fail" in out
    assert "DIGEST_FILE=" in out
    assert "REDACTED_LOG_FILE=" in out
    assert out.index("DIGEST_FILE=") < out.index("REDACTED_LOG_FILE=")


def test_checks_run_relevant_main_no_validation_envelope_includes_digest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    session = _checks_session(tmp_path, monkeypatch)
    log = session / "fail.redacted.log"
    log.write_text("err\n", encoding="utf-8")
    digest = session / "fail.digest.txt"
    digest.write_text("CHECKS_FAILURE_DIGEST v1\n", encoding="utf-8")

    def fake_checks(*_args: object, **_kwargs: object) -> checks.ChecksResult:
        return checks.ChecksResult(
            ok=False,
            exit_code=2,
            site="step3",
            redacted_log_path=str(log),
            phase="none",
            coverage="none",
            skipped=False,
            warn=None,
            failure_reason="no-validation-phases",
            digest_file_path=str(digest),
        )

    monkeypatch.setattr(_crr, "run_relevant_checks", fake_checks)
    rc = checks.checks_run_relevant_main(["--site", "step3", "--tmpdir", str(session)])
    out = capsys.readouterr().out
    assert rc == 2
    assert "FAILURE_REASON=no-validation-phases" in out
    assert out.index("DIGEST_FILE=") < out.index("REDACTED_LOG_FILE=")


def test_checks_run_relevant_main_allow_skip_envelope(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    session = _checks_session(tmp_path, monkeypatch)

    def fake_checks(*_args: object, **kwargs: object) -> checks.ChecksResult:
        return checks.ChecksResult(
            ok=False,
            exit_code=0,
            site=str(kwargs["site"]),
            redacted_log_path=None,
            phase="none",
            coverage="none",
            skipped=True,
            warn=None,
        )

    monkeypatch.setattr(_crr, "run_relevant_checks", fake_checks)
    rc = checks.checks_run_relevant_main(["--site", "step3", "--tmpdir", str(session), "--allow-skip"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "RELEVANT_CHECKS_SKIPPED=true" in out


def test_checks_run_relevant_main_without_allow_skip_never_emits_skipped(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    session = _checks_session(tmp_path, monkeypatch)

    def fake_checks(*_args: object, **_kwargs: object) -> checks.ChecksResult:
        return checks.ChecksResult(
            ok=False,
            exit_code=2,
            site="step3",
            redacted_log_path=None,
            phase="none",
            coverage="none",
            skipped=True,
            warn=None,
            failure_reason="checks-failed",
        )

    monkeypatch.setattr(_crr, "run_relevant_checks", fake_checks)
    rc = checks.checks_run_relevant_main(["--site", "step3", "--tmpdir", str(session)])
    out = capsys.readouterr().out
    assert rc == 2
    assert "RELEVANT_CHECKS_SKIPPED" not in out
    assert "STATUS=fail" in out


def test_checks_lint_fix_main_main_agent_required_envelope(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    session = _checks_session(tmp_path, monkeypatch)
    checks_log = session / "fail.redacted.log"
    checks_log.write_text("err\n", encoding="utf-8")

    def fake_run_lint_fix(*_args: object, **_kwargs: object) -> checks.FixOutcome:
        return checks.FixOutcome(
            status="main-agent-required",
            delta_paths=(),
            failure_reason="dispatch-failed",
            commit_sha=None,
            head_changed=False,
            coder_tool=None,
            ledger_ready=True,
            ledger_site="step3",
            ledger_trigger="main-agent-required",
            ledger_step="3",
            ledger_phase="checks",
            ledger_dispatcher="lint-fix-loop",
            ledger_exit_code=1,
            ledger_failure_detail_log=str(checks_log),
            stderr_tail_path=str(session / "lint-fix-loop" / "step3.x" / "codex.log"),
        )

    monkeypatch.setattr(_clf, "run_lint_fix", fake_run_lint_fix)
    rc = checks.checks_lint_fix_main([
        "--tmpdir",
        str(session),
        "--site",
        "step3",
        "--checks-log",
        str(checks_log),
    ])
    out = capsys.readouterr().out
    assert rc == 0
    assert "LINT_FIX_STATUS=main-agent-required" in out
    assert "FAILURE_REASON=dispatch-failed" in out
    assert "LINT_FIX_LEDGER_READY=true" in out
    assert "LINT_FIX_LEDGER_SITE=step3" in out
    assert "STDERR_TAIL_PATH=" in out
    assert "LINT_FIX_LEDGER_FAILURE_DETAIL_LOG=" in out


def test_checks_lint_fix_main_failed_envelope(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    session = _checks_session(tmp_path, monkeypatch)
    checks_log = session / "fail.redacted.log"
    checks_log.write_text("err\n", encoding="utf-8")

    def fake_run_lint_fix(*_args: object, **_kwargs: object) -> checks.FixOutcome:
        return checks.FixOutcome(
            status="failed",
            delta_paths=(),
            failure_reason="checks-log-invalid",
            commit_sha=None,
            head_changed=False,
            coder_tool=None,
        )

    monkeypatch.setattr(_clf, "run_lint_fix", fake_run_lint_fix)
    rc = checks.checks_lint_fix_main([
        "--tmpdir",
        str(session),
        "--site",
        "step3",
        "--checks-log",
        str(checks_log),
    ])
    out = capsys.readouterr().out
    assert rc == 1
    assert "LINT_FIX_STATUS=failed" in out
    assert "FAILURE_REASON=checks-log-invalid" in out
    assert "LINT_FIX_LEDGER_READY" not in out



def _repair_loop_failed_result(log: Path, *, site: str = "step6") -> checks.ChecksResult:
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


def _repair_loop_ok_result(*, site: str = "step6") -> checks.ChecksResult:
    return checks.ChecksResult(
        ok=True,
        exit_code=0,
        site=site,
        redacted_log_path=None,
        phase="unknown",
        coverage="full",
        skipped=False,
        warn=None,
    )


def test_checks_repair_loop_main_continue_after_applied_and_clean_recheck(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    session = _checks_session(tmp_path, monkeypatch)
    checks_log = session / "initial.redacted.log"
    checks_log.write_text("err\n", encoding="utf-8")
    calls: list[str] = []

    def fake_run_lint_fix(_runner: object, **kwargs: object) -> checks.FixOutcome:
        calls.append(f"fix:{kwargs['site']}:{kwargs['checks_log']}")
        return checks.FixOutcome(
            status="applied",
            delta_paths=("fixed.py",),
            failure_reason=None,
            commit_sha="abc",
            head_changed=False,
            coder_tool="codex",
        )

    def fake_run_relevant_checks(
        _runner: object,
        *,
        site: str,
        tmpdir: str,
        repo_root: str,
    ) -> checks.ChecksResult:
        calls.append(f"checks:{site}:{tmpdir}:{repo_root}")
        return _repair_loop_ok_result(site=site)

    monkeypatch.setattr(_clf, "run_lint_fix", fake_run_lint_fix)
    monkeypatch.setattr(_clf, "run_relevant_checks", fake_run_relevant_checks)
    rc = checks.checks_repair_loop_main([
        "--tmpdir",
        str(session),
        "--site",
        "step3",
        "--checks-log",
        str(checks_log),
        "--repo-root",
        str(tmp_path),
    ])
    out = capsys.readouterr().out
    assert rc == 0
    assert "NEXT_ACTION=continue" in out
    assert "LOOP_STATUS=ok" in out
    assert calls == [
        f"fix:step3:{checks_log}",
        f"checks:step3:{session}:{tmp_path}",
    ]


def test_checks_repair_loop_main_main_agent_edit_envelope(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    session = _checks_session(tmp_path, monkeypatch)
    checks_log = session / "initial.redacted.log"
    checks_log.write_text("err\n", encoding="utf-8")
    stderr_tail = session / "lint-fix-loop" / "step3.1" / "codex.log.tail"
    coder_log = session / "lint-fix-loop" / "step3.1" / "codex.log"

    def fake_run_lint_fix(_runner: object, **_kwargs: object) -> checks.FixOutcome:
        return checks.FixOutcome(
            status="main-agent-required",
            delta_paths=(),
            failure_reason="dispatch-failed",
            commit_sha=None,
            head_changed=False,
            coder_tool="codex",
            ledger_ready=True,
            ledger_site="step3",
            ledger_trigger="main-agent-required",
            ledger_step="3",
            ledger_phase="checks",
            ledger_dispatcher="lint-fix-loop",
            ledger_exit_code=7,
            ledger_failure_detail_log=str(checks_log),
            stderr_tail_path=str(stderr_tail),
            coder_log_path=str(coder_log),
        )

    def fail_if_checks_run(*_args: object, **_kwargs: object) -> checks.ChecksResult:
        raise AssertionError("main-agent-required returns before re-check")

    monkeypatch.setattr(_clf, "run_lint_fix", fake_run_lint_fix)
    monkeypatch.setattr(_clf, "run_relevant_checks", fail_if_checks_run)
    rc = checks.checks_repair_loop_main([
        "--tmpdir",
        str(session),
        "--site",
        "step3",
        "--checks-log",
        str(checks_log),
        "--repo-root",
        str(tmp_path),
    ])
    out = capsys.readouterr().out
    assert rc == 0
    assert "NEXT_ACTION=main-agent-edit" in out
    assert "LOOP_STATUS=main-agent-required" in out
    assert f"STDERR_TAIL_PATH={stderr_tail}" in out
    assert f"CODER_LOG_FILE={coder_log}" in out
    assert "LINT_FIX_LEDGER_READY=true" in out
    assert "LINT_FIX_LEDGER_SITE=step3" in out
    assert "LINT_FIX_LEDGER_TRIGGER=main-agent-required" in out
    assert "LINT_FIX_LEDGER_STEP=3" in out
    assert "LINT_FIX_LEDGER_PHASE=checks" in out
    assert "LINT_FIX_LEDGER_DISPATCHER=lint-fix-loop" in out
    assert "LINT_FIX_LEDGER_EXIT_CODE=7" in out
    assert f"LINT_FIX_LEDGER_FAILURE_DETAIL_LOG={checks_log}" in out


def test_checks_repair_loop_main_wires_lint_and_capture_sites(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    session = _checks_session(tmp_path, monkeypatch)
    checks_log = session / "initial.redacted.log"
    checks_log.write_text("err\n", encoding="utf-8")
    seen: dict[str, str] = {}

    def fake_run_lint_fix(_runner: object, **kwargs: object) -> checks.FixOutcome:
        seen["lint_site"] = str(kwargs["site"])
        return checks.FixOutcome(
            status="applied",
            delta_paths=("fixed.py",),
            failure_reason=None,
            commit_sha="abc",
            head_changed=False,
            coder_tool="codex",
        )

    def fake_run_relevant_checks(
        _runner: object,
        *,
        site: str,
        tmpdir: str,
        repo_root: str,
    ) -> checks.ChecksResult:
        _ = tmpdir, repo_root
        seen["capture_site"] = site
        return _repair_loop_ok_result(site=site)

    monkeypatch.setattr(_clf, "run_lint_fix", fake_run_lint_fix)
    monkeypatch.setattr(_clf, "run_relevant_checks", fake_run_relevant_checks)
    rc = checks.checks_repair_loop_main([
        "--tmpdir",
        str(session),
        "--site",
        "step5-mav",
        "--checks-site",
        "step5-review-fixes",
        "--checks-log",
        str(checks_log),
        "--repo-root",
        str(tmp_path),
    ])
    out = capsys.readouterr().out
    assert rc == 0
    assert "NEXT_ACTION=continue" in out
    assert seen == {
        "lint_site": "step5-mav",
        "capture_site": "step5-review-fixes",
    }


def test_checks_repair_loop_main_stall_exit_is_parseable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    session = _checks_session(tmp_path, monkeypatch)
    checks_log = session / "initial.redacted.log"
    checks_log.write_text("err\n", encoding="utf-8")
    fail_log = session / "fail.redacted.log"
    fail_log.write_text("still bad\n", encoding="utf-8")

    def fake_run_lint_fix(_runner: object, **_kwargs: object) -> checks.FixOutcome:
        return checks.FixOutcome(
            status="no-changes",
            delta_paths=(),
            failure_reason=None,
            commit_sha=None,
            head_changed=False,
            coder_tool="codex",
        )

    def fake_run_relevant_checks(
        _runner: object,
        *,
        site: str,
        tmpdir: str,
        repo_root: str,
    ) -> checks.ChecksResult:
        _ = tmpdir, repo_root
        return _repair_loop_failed_result(fail_log, site=site)

    monkeypatch.setattr(_clf, "run_lint_fix", fake_run_lint_fix)
    monkeypatch.setattr(_clf, "run_relevant_checks", fake_run_relevant_checks)
    rc = checks.checks_repair_loop_main([
        "--tmpdir",
        str(session),
        "--site",
        "step6",
        "--checks-log",
        str(checks_log),
        "--repo-root",
        str(tmp_path),
    ])
    out = capsys.readouterr().out
    assert rc == 1
    assert "NEXT_ACTION=stall" in out
    assert "LOOP_STATUS=no-changes-stale" in out


def test_checks_repair_loop_main_validation_failure_emits_stall(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    missing_session = tmp_path / "missing"
    rc = checks.checks_repair_loop_main([
        "--tmpdir",
        str(missing_session),
        "--site",
        "step6",
        "--checks-log",
        str(missing_session / "fail.redacted.log"),
        "--repo-root",
        str(tmp_path),
    ])
    out = capsys.readouterr().out
    assert rc == 2
    assert "NEXT_ACTION=stall" in out
    assert "LOOP_STATUS=tmpdir-validation" in out


def test_checks_repair_loop_main_rejects_invalid_checks_site(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    session = _checks_session(tmp_path, monkeypatch)
    checks_log = session / "initial.redacted.log"
    checks_log.write_text("err\n", encoding="utf-8")
    rc = checks.checks_repair_loop_main([
        "--tmpdir",
        str(session),
        "--site",
        "step6",
        "--checks-site",
        "../bad",
        "--checks-log",
        str(checks_log),
        "--repo-root",
        str(tmp_path),
    ])
    out = capsys.readouterr().out
    assert rc == 2
    assert "NEXT_ACTION=stall" in out
    assert "LOOP_STATUS=checks-site-validation" in out


def test_checks_repair_loop_main_reentry_keeps_checks_site_pair(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    session = _checks_session(tmp_path, monkeypatch)
    checks_log = session / "post-edit.redacted.log"
    checks_log.write_text("err\n", encoding="utf-8")
    capture_sites: list[str] = []

    def fake_run_lint_fix(_runner: object, **_kwargs: object) -> checks.FixOutcome:
        return checks.FixOutcome(
            status="applied",
            delta_paths=("fixed.py",),
            failure_reason=None,
            commit_sha="abc",
            head_changed=False,
            coder_tool="codex",
        )

    def fake_run_relevant_checks(
        _runner: object,
        *,
        site: str,
        tmpdir: str,
        repo_root: str,
    ) -> checks.ChecksResult:
        _ = tmpdir, repo_root
        capture_sites.append(site)
        return _repair_loop_ok_result(site=site)

    monkeypatch.setattr(_clf, "run_lint_fix", fake_run_lint_fix)
    monkeypatch.setattr(_clf, "run_relevant_checks", fake_run_relevant_checks)
    argv = [
        "--tmpdir",
        str(session),
        "--site",
        "step5-mav",
        "--checks-site",
        "step5-review-fixes",
        "--checks-log",
        str(checks_log),
        "--repo-root",
        str(tmp_path),
    ]
    # Reference-facing contract: post-main-agent re-entry must repeat the same
    # --site / --checks-site pair rather than passing only an updated log.
    assert checks.checks_repair_loop_main(argv) == 0
    assert checks.checks_repair_loop_main(argv) == 0
    _ = capsys.readouterr()
    assert capture_sites == ["step5-review-fixes", "step5-review-fixes"]


def test_checks_repair_loop_main_emits_dispatching_breadcrumb_to_stdout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    session = _checks_session(tmp_path, monkeypatch)
    checks_log = session / "initial.redacted.log"
    checks_log.write_text("err\n", encoding="utf-8")

    def fake_run_lint_fix(_runner: object, **_kwargs: object) -> checks.FixOutcome:
        return checks.FixOutcome(
            status="applied",
            delta_paths=("fixed.py",),
            failure_reason=None,
            commit_sha="abc",
            head_changed=False,
            coder_tool="codex",
        )

    def fake_run_relevant_checks(
        _runner: object,
        *,
        site: str,
        tmpdir: str,
        repo_root: str,
    ) -> checks.ChecksResult:
        _ = tmpdir, repo_root
        return _repair_loop_ok_result(site=site)

    monkeypatch.setattr(_clf, "run_lint_fix", fake_run_lint_fix)
    monkeypatch.setattr(_clf, "run_relevant_checks", fake_run_relevant_checks)
    rc = checks.checks_repair_loop_main([
        "--tmpdir",
        str(session),
        "--site",
        "step3",
        "--checks-log",
        str(checks_log),
        "--repo-root",
        str(tmp_path),
    ])
    captured = capsys.readouterr()
    assert rc == 0
    # Immediate liveness breadcrumb lands on stdout as orchestrator-ignorable
    # PROGRESS= (issue #5286); terminal NEXT_ACTION/LOOP_STATUS still parse.
    assert "PROGRESS=dispatching-lint-fix site=step3" in captured.out
    assert "PROGRESS=dispatching-lint-fix" not in captured.err
    assert "NEXT_ACTION=continue" in captured.out
    assert "LOOP_STATUS=ok" in captured.out


def test_emit_repair_loop_heartbeat_writes_periodic_lines_to_stdout(
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Drive the helper with a fake stop event so the periodic emission is
    # deterministic (no threads, no sleeps). Thread wiring on the real path is
    # exercised by the dispatching-breadcrumb test above (issue #5286).
    class _CountingStop:
        def __init__(self, false_count: int) -> None:
            self._remaining = false_count

        def wait(self, _timeout: float) -> bool:
            if self._remaining > 0:
                self._remaining -= 1
                return False
            return True

    _clf._emit_repair_loop_heartbeat(stop=_CountingStop(3), site="step3")  # pyright: ignore[reportPrivateUsage, reportArgumentType]
    captured = capsys.readouterr()
    assert captured.out.count("PROGRESS=lint-fix-running site=step3 elapsed=") == 3
    assert captured.err == ""


def test_repair_loop_heartbeat_fires_during_blocking_lint_fix(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Heartbeat fires while run_lint_fix blocks; stop event is set on completion.

    Uses shared state (threading.Event) to verify lifecycle because pytest's
    capsys fixture does not reliably capture output from daemon threads.
    """
    session = _checks_session(tmp_path, monkeypatch)
    checks_log = session / "initial.redacted.log"
    checks_log.write_text("err\n", encoding="utf-8")

    # Very short interval so the heartbeat fires quickly during the blocking fixer.
    monkeypatch.setattr(_clf, "_REPAIR_LOOP_HEARTBEAT_INTERVAL_S", 0.005)  # type: ignore[attr-defined]

    stop_captured: list[threading.Event] = []
    heartbeat_fired = threading.Event()
    fixer_active = threading.Event()
    fixer_active.set()
    heartbeat_emissions = [0]

    def tracking_heartbeat(*, stop: threading.Event, site: str) -> None:
        stop_captured.append(stop)
        start = time.monotonic()
        while not stop.wait(0.005):
            elapsed = int(time.monotonic() - start)
            print(f"PROGRESS=lint-fix-running site={site} elapsed={elapsed}s", flush=True)
            heartbeat_emissions[0] += 1
            if fixer_active.is_set():
                heartbeat_fired.set()

    monkeypatch.setattr(_clf, "_emit_repair_loop_heartbeat", tracking_heartbeat)

    def fake_run_lint_fix(_runner: object, **_kwargs: object) -> checks.FixOutcome:
        # Block until at least one heartbeat has fired, then complete.
        assert heartbeat_fired.wait(timeout=5.0), (
            "heartbeat never fired during blocking lint-fix"
        )
        fixer_active.clear()
        return checks.FixOutcome(
            status="applied",
            delta_paths=("fixed.py",),
            failure_reason=None,
            commit_sha="abc",
            head_changed=False,
            coder_tool="codex",
        )

    def fake_run_relevant_checks(
        _runner: object,
        *,
        site: str,
        tmpdir: str,
        repo_root: str,
    ) -> checks.ChecksResult:
        _ = tmpdir, repo_root
        return _repair_loop_ok_result(site=site)

    monkeypatch.setattr(_clf, "run_lint_fix", fake_run_lint_fix)
    monkeypatch.setattr(_clf, "run_relevant_checks", fake_run_relevant_checks)

    rc = checks.checks_repair_loop_main([
        "--tmpdir", str(session),
        "--site", "step3",
        "--checks-log", str(checks_log),
        "--repo-root", str(tmp_path),
    ])

    captured = capsys.readouterr()
    assert rc == 0
    # Heartbeat was started and fired at least once while the fixer was blocking.
    assert heartbeat_fired.is_set(), "heartbeat never fired during blocking lint-fix"
    assert len(stop_captured) == 1
    # Stop event is set in the finally block after the fixer completed.
    assert stop_captured[0].is_set(), "heartbeat stop event was not set after fixer completed"
    # No further heartbeat emissions after the repair loop completed.
    emissions_at_end = heartbeat_emissions[0]
    time.sleep(0.05)
    assert heartbeat_emissions[0] == emissions_at_end, (
        "heartbeat emitted after repair loop completed"
    )
    # Terminal envelope is intact and precedes any stray heartbeat lines.
    assert "NEXT_ACTION=continue" in captured.out
    assert "LOOP_STATUS=ok" in captured.out
    next_action_idx = captured.out.find("NEXT_ACTION=continue")
    if next_action_idx >= 0:
        assert "PROGRESS=lint-fix-running" not in captured.out[next_action_idx:], (
            "heartbeat line appeared after terminal envelope"
        )


def test_repair_loop_oserror_stops_heartbeat_and_emits_stall(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """OSError from the fixer callback emits stall output and stops the heartbeat cleanly."""
    session = _checks_session(tmp_path, monkeypatch)
    checks_log = session / "initial.redacted.log"
    checks_log.write_text("err\n", encoding="utf-8")

    stop_events: list[threading.Event] = []

    def recording_heartbeat(*, stop: threading.Event, site: str) -> None:
        # Record the stop event and wait on it — mirrors real lifecycle without timing.
        _ = site
        stop_events.append(stop)
        stop.wait()

    monkeypatch.setattr(_clf, "_emit_repair_loop_heartbeat", recording_heartbeat)

    def oserror_lint_fix(_runner: object, **_kwargs: object) -> checks.FixOutcome:
        raise OSError("simulated disk error")

    monkeypatch.setattr(_clf, "run_lint_fix", oserror_lint_fix)

    rc = checks.checks_repair_loop_main([
        "--tmpdir", str(session),
        "--site", "step3",
        "--checks-log", str(checks_log),
        "--repo-root", str(tmp_path),
    ])

    captured = capsys.readouterr()
    assert rc == 1
    assert "NEXT_ACTION=stall" in captured.out
    assert "LOOP_STATUS=callback-oserror" in captured.out
    # Verify the finally block ran: the heartbeat was started and its stop event is set.
    assert len(stop_events) == 1
    assert stop_events[0].is_set()


def test_run_lint_fix_claude_only_host_dispatches_claude(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    log = tmp_path / "checks.log"
    _ = log.write_text("lint error\n", encoding="utf-8")
    head = "abc123"
    dispatch_calls: list[str] = []

    def succeed_claude(*_args: object, **_kwargs: object) -> int:
        dispatch_calls.append("claude")
        return 0

    monkeypatch.setattr(_clf, "_run_claude", succeed_claude)
    def claude_on_path(name: str) -> str | None:
        return "/usr/bin/claude" if name == "claude" else None

    monkeypatch.setattr(shutil, "which", claude_on_path)
    runner = StubRunner([
        _ok(""),
        _ok(""),
        _ok(""),
        _ok(head + "\n"),
        _ok("main\n"),
        _ok(""),
        _ok(""),
        _ok(head + "\n"),
        _ok("fixed.py\n"),
        _ok(""),
        _ok(""),
        _ok("fixed.py\n"),
        _ok(""),
        _ok(""),
        _ok(""),
        _ok(""),
        _ok("def456\n"),
    ])
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
    assert dispatch_calls == ["claude"]
    assert outcome.status == "applied"
    assert outcome.coder_tool == "claude"


def test_run_lint_fix_all_three_tiers_fail_main_agent_required(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    log = tmp_path / "checks.log"
    _ = log.write_text("lint error\n", encoding="utf-8")
    head = "abc123"
    dispatch_calls: list[str] = []

    def fail_claude(*_args: object, **_kwargs: object) -> int:
        dispatch_calls.append("claude")
        return 1

    def fail_codex(*_args: object, **_kwargs: object) -> int:
        dispatch_calls.append("codex")
        return 1

    def fail_cursor(*_args: object, **_kwargs: object) -> int:
        dispatch_calls.append("cursor")
        return 1

    monkeypatch.setattr(_clf, "_run_claude", fail_claude)
    monkeypatch.setattr(_clf, "_run_codex", fail_codex)
    monkeypatch.setattr(_clf, "_run_cursor", fail_cursor)
    def all_tools_on_path(name: str) -> str:
        return f"/usr/bin/{name}"

    monkeypatch.setattr(shutil, "which", all_tools_on_path)
    runner = StubRunner([
        _ok(""),
        _ok(""),
        _ok(""),
        _ok(head + "\n"),
        _ok("main\n"),
        _ok(""),
        _ok(""),
        _ok(head + "\n"),
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
    assert dispatch_calls == ["claude", "codex", "cursor"]
    assert outcome.status == "main-agent-required"
    assert outcome.ledger_ready is True
