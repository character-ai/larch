# pyright: reportUnusedCallResult=false, reportUnusedFunction=false
"""Tests for checks.py and the narrow executable CI workflow contracts."""

from __future__ import annotations

import io
import json
import os
import re
import shutil
import subprocess
import tarfile
import textwrap
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast

import pytest

from larch.implement import checks
from larch.implement import checks_run_relevant as _crr
from larch.core import repo_roots
from larch.implement import checks_lint_fix as _clf
from larch.core import config
from larch.core import external_defaults
from larch.core import proc
from larch.implement.dispatch_helpers import result_env_capture_rows
from larch.outcomes import Outcome
from larch.core.proc import CommandResult
from test_support import ok

CLI_PATH = Path(__file__).resolve().parents[2] / "cli.py"


def _empty_responses() -> list[CommandResult]:
    return []


def _empty_calls() -> list[tuple[tuple[str, ...], dict[str, object]]]:
    return []


def _successful_contains_pin_phase(**_kwargs: object) -> int:
    return 0


def _command_is_available(**_kwargs: object) -> bool:
    return True


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
        return ok(argv_tuple)


def _ok(stdout: str = "", *, rc: int = 0) -> CommandResult:
    if rc == 0:
        return ok((), stdout)
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



def test_write_failure_digest_appends_count_only_telemetry(tmp_path: Path) -> None:
    session = tmp_path / "claude-implement-test"
    log_dir = session / "relevant-checks"
    run_dir = session / "larch-logs" / "implement" / "run-abc"
    log_dir.mkdir(parents=True)
    run_dir.mkdir(parents=True)
    redacted = log_dir / "step6-1.redacted.log"
    raw_failure = "ERROR: raw failure text from pytest"
    redacted_text = f"=== Running pre-commit on 1 changed file(s) ===\n{raw_failure}\n"
    redacted.write_text(redacted_text, encoding="utf-8")

    digest_path = _crr._write_failure_digest_from_redacted(  # pyright: ignore[reportPrivateUsage]
        redacted_file=redacted,
        site="step6",
        attempt="1",
        log_dir=log_dir,
    )

    assert digest_path is not None
    digest = Path(digest_path).read_text(encoding="utf-8")
    assert raw_failure in digest
    telemetry = run_dir / "checks-digest-sizes.tsv"
    rows = telemetry.read_text(encoding="utf-8").splitlines()
    assert len(rows) == 2
    header = rows[0].split("\t")
    row = dict(zip(header, rows[1].split("\t"), strict=False))
    assert row["site"] == "step6"
    assert row["attempt"] == "1"
    assert row["redacted_bytes"] == str(len(redacted_text.encode("utf-8")))
    assert row["digest_bytes"] == str(len(digest.encode("utf-8")))
    assert row["saved_bytes"] == str(len(redacted_text.encode("utf-8")) - len(digest.encode("utf-8")))
    tsv_text = telemetry.read_text(encoding="utf-8")
    assert raw_failure not in tsv_text
    assert redacted_text not in tsv_text
    assert digest not in tsv_text
    assert str(tmp_path) not in tsv_text


def test_write_failure_digest_skips_telemetry_without_unique_run_dir(tmp_path: Path) -> None:
    session = tmp_path / "claude-implement-test"
    log_dir = session / "relevant-checks"
    log_dir.mkdir(parents=True)
    redacted = log_dir / "step6-1.redacted.log"
    redacted.write_text("ERROR: failed\n", encoding="utf-8")

    digest_path = _crr._write_failure_digest_from_redacted(  # pyright: ignore[reportPrivateUsage]
        redacted_file=redacted,
        site="step6",
        attempt="1",
        log_dir=log_dir,
    )

    assert digest_path is not None
    assert not list(session.glob("larch-logs/*/*/checks-digest-sizes.tsv"))

    (session / "larch-logs" / "implement" / "run-1").mkdir(parents=True)
    (session / "larch-logs" / "review" / "run-2").mkdir(parents=True)
    digest_path = _crr._write_failure_digest_from_redacted(  # pyright: ignore[reportPrivateUsage]
        redacted_file=redacted,
        site="step6",
        attempt="2",
        log_dir=log_dir,
    )

    assert digest_path is not None
    assert not list(session.glob("larch-logs/*/*/checks-digest-sizes.tsv"))


def test_checks_failure_digest_uses_only_redacted_source() -> None:
    secret = "ghp_" + "a" * 36
    text = f"ERROR: token {config.REDACTED_TOKEN}\n"

    digest = _crr._build_checks_failure_digest(redacted_log_text=text, site="unit")  # pyright: ignore[reportPrivateUsage]

    assert config.REDACTED_TOKEN in digest
    assert secret not in digest


def test_checks_fixer_evidence_materializes_bounded_redacted_digest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    session = _checks_session(tmp_path, monkeypatch)
    source = session / "step6.redacted.log"
    source.write_text(
        "=== Running direct relevant make target(s): py-lint ===\n"
        "ERROR: ghp_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n",
        encoding="utf-8",
    )

    rc = checks.checks_fixer_evidence_main([
        "--tmpdir",
        str(session),
        "--site",
        "step6",
        "--round",
        "1",
        "--checks-log",
        str(source),
    ])

    out = capsys.readouterr().out
    output = session / "checks-errors-step6-1.md"
    assert rc == 0
    assert "CHECKS_FIXER_EVIDENCE_STATUS=ok" in out
    assert f"CHECKS_FIXER_EVIDENCE_FILE={output}" in out
    assert output.stat().st_mode & 0o777 == 0o600
    digest = output.read_text(encoding="utf-8")
    assert "CHECKS_FAILURE_DIGEST v1" in digest
    assert "site=step6" in digest
    assert "ghp_" not in digest
    assert config.REDACTED_TOKEN in digest


@pytest.mark.parametrize(("site", "round_number"), [("../outside", "1"), ("step6", "11")])
def test_checks_fixer_evidence_rejects_unsafe_output_tokens(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    site: str,
    round_number: str,
) -> None:
    session = _checks_session(tmp_path, monkeypatch)
    source = session / "step6.redacted.log"
    source.write_text("ERROR: failed\n", encoding="utf-8")

    rc = checks.checks_fixer_evidence_main([
        "--tmpdir",
        str(session),
        "--site",
        site,
        "--round",
        round_number,
        "--checks-log",
        str(source),
    ])

    assert rc == 2
    assert "CHECKS_FIXER_EVIDENCE_STATUS=invalid-" in capsys.readouterr().out


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


def test_run_check_fix_loop_dispatch_first_exhausted_carries_final_redacted_log(
    tmp_path: Path,
) -> None:
    initial = tmp_path / "initial.redacted.log"
    initial.write_text("initial failure\n", encoding="utf-8")
    failure_logs = [tmp_path / f"iteration-{iteration}.redacted.log" for iteration in range(1, 4)]
    for iteration, failure_log in enumerate(failure_logs, start=1):
        failure_log.write_text(f"failure {iteration}\n", encoding="utf-8")
    failures = [_repair_loop_failed_result(path) for path in failure_logs]

    loop = checks.run_check_fix_loop(
        checks_runner=lambda: failures.pop(0),
        fixer=lambda _log: checks.FixOutcome(
            status="applied",
            delta_paths=("fixed.py",),
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
    assert loop.final_redacted_checks_log == str(failure_logs[-1])


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


def test_run_relevant_checks_no_changed_files_is_a_fast_freshness_check(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _checks_session(tmp_path, monkeypatch)
    repo = _git_repo(tmp_path)
    result = checks.run_relevant_checks(proc, site="unit", tmpdir=str(session), repo_root=str(repo))
    assert result.ok is True
    assert result.raw_log_path is not None
    assert "No modified files detected — no scoped validation needed." in Path(result.raw_log_path).read_text(encoding="utf-8")


def test_run_relevant_checks_no_changed_files_does_not_require_agent_lint(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _checks_session(tmp_path, monkeypatch)
    repo = _git_repo(tmp_path)
    result = checks.run_relevant_checks(proc, site="unit", tmpdir=str(session), repo_root=str(repo))
    assert result.ok is True


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
    assert result.coverage == "changed-file-only"
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
        "contains_pin": 0,
    }

    def fake_run_logged(*, runner: object, argv: list[str], log_fd: int, **_kwargs: object) -> CommandResult:
        _ = runner
        calls["run_logged"] += 1
        assert argv[:3] == ["pre-commit", "run", "--files"]
        os.write(log_fd, b"precommit failed\n")
        return _ok("precommit failed\n", rc=1)

    def fake_contains_pin_phase(*_args: object, **_kwargs: object) -> int:
        calls["contains_pin"] += 1
        return 0

    monkeypatch.setattr(_crr, "_run_logged", fake_run_logged)  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(_crr, "_run_contains_pin_phase", fake_contains_pin_phase)  # pyright: ignore[reportPrivateUsage]

    result = checks.run_relevant_checks(proc, site="unit", tmpdir=str(session), repo_root=str(repo))

    assert result.ok is False
    assert result.phase == "pre-commit"
    assert calls == {
        "run_logged": 1,
        "contains_pin": 0,
    }
    log = Path(result.raw_log_path or "").read_text(encoding="utf-8")
    marker_index = log.index("=== Running pre-commit on 1 changed file(s) ===")
    assert "precommit failed" in log[marker_index:]
    assert "bounded Rust Clippy fallback" not in log[marker_index:]
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
    assert outcome.status == "failed"
    assert outcome.failure_reason == "lint-fix-no-selectable-tier"
    assert outcome.tier_ledger_path
    timing_calls = _timing_record_calls(runner, task_kind="claude-lint-fix")
    assert len(timing_calls) == 1
    call, _kw = timing_calls[0]
    assert "--output" in call
    assert call[call.index("--output") + 1] == str(tmp_path / "claude-lint-fix.txt")
    assert "--exit-code" in call
    assert call[call.index("--exit-code") + 1] == "1"
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



def _assert_structural_fast_fail(outcome: checks.FixOutcome, log: Path) -> None:
    assert outcome.status == "main-agent-required"
    assert outcome.failure_reason == "structural-ruff-failure"
    assert outcome.ledger_ready is True
    assert outcome.ledger_dispatcher == "lint-fix-loop"
    assert outcome.ledger_exit_code == 1
    assert outcome.ledger_failure_detail_log == str(log.resolve())


def _install_lint_fix_dispatch_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> list[str]:
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
    return dispatch_calls


@pytest.mark.parametrize("code", ["C901", "PLR0911", "PLR0912", "PLC0415"])
@pytest.mark.parametrize(
    "row",
    [
        "python/larch/implement/checks_lint_fix.py:12:5: {code} structural issue\n",
        "python/larch/implement/checks_lint_fix.py:12: {code} structural issue\n",
    ],
)
def test_run_lint_fix_structural_ruff_diagnostics_fast_fail(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    code: str,
    row: str,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    log = tmp_path / "checks.log"
    _ = log.write_text(row.format(code=code), encoding="utf-8")
    dispatch_calls = _install_lint_fix_dispatch_failures(monkeypatch)
    runner = StubRunner()

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

    _assert_structural_fast_fail(outcome, log)
    assert not dispatch_calls
    assert runner.calls == _timing_record_calls(runner, task_kind="claude-lint-fix")


@pytest.mark.parametrize(
    "log_text",
    [
        "C901 `transform_file` is too complex (11 > 10)\n"
        " --> python/larch/report/report_tokens_render.py:65:5\n",
    ],
)
def test_run_lint_fix_structural_ruff_human_block_fast_fail(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    log_text: str,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    log = tmp_path / "checks.log"
    _ = log.write_text(log_text, encoding="utf-8")
    dispatch_calls = _install_lint_fix_dispatch_failures(monkeypatch)
    runner = StubRunner()

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

    _assert_structural_fast_fail(outcome, log)
    assert not dispatch_calls
    assert runner.calls == _timing_record_calls(runner, task_kind="claude-lint-fix")



@pytest.mark.parametrize(
    "log_text",
    [
        "The operator mentioned C901 and PLR0912 in prose only.\n",
        "python/larch/implement/checks_lint_fix.py:12:5: E501 line too long\n",
    ],
)
def test_run_lint_fix_structural_false_positives_use_normal_fixer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    log_text: str,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    log = tmp_path / "checks.log"
    _ = log.write_text(log_text, encoding="utf-8")
    codex_calls: list[str] = []

    def fail_codex(*_args: object, **_kwargs: object) -> int:
        codex_calls.append("codex")
        return 1

    monkeypatch.setattr(_clf, "_run_codex", fail_codex)
    runner = StubRunner([
        _ok(""),  # baseline tracked diff
        _ok(""),  # baseline cached diff
        _ok(""),  # baseline untracked status
        _ok(""),  # baseline snapshot git diff --raw
        _ok(""),  # baseline snapshot git diff --cached --raw
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
    assert outcome.status == "failed"
    assert outcome.failure_reason == "lint-fix-all-tiers-no-useful-delta"



def test_run_lint_fix_structural_ruff_no_tools_fast_fail(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    log = tmp_path / "checks.log"
    _ = log.write_text(
        "python/larch/implement/checks_lint_fix.py:12:5: PLR0912 too many branches\n",
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

    _assert_structural_fast_fail(outcome, log)
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
    assert outcome.status == "failed"
    assert outcome.failure_reason == "lint-fix-all-tiers-no-useful-delta"


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
        _ok(""),  # baseline snapshot git diff --raw
        _ok(""),  # baseline snapshot git diff --cached --raw
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
        allowed_tmpdir=_lint_fix_dirs(tmp_path)[0],
        run_parent=_lint_fix_dirs(tmp_path)[1],
    )
    assert outcome.status == "failed"
    assert outcome.failure_reason == "lint-fix-all-tiers-no-useful-delta"
    flat = " ".join(arg for call, _kw in runner.calls for arg in call)
    assert "launch-codex-ci.sh" not in flat
    assert "launch-cursor-ci.sh" not in flat
    codex_call = next(
        call for call, _kw in runner.calls
        if "launch-codex-exec" in call
    )
    entrypoint = str(repo_roots.larch_entrypoint())
    idx = list(codex_call).index(entrypoint)
    argv = list(codex_call)[idx:]
    assert argv[:3] == [entrypoint, "agent", "launch-codex-exec"]
    assert str(agent_cli) not in argv
    assert "--timeout" in argv
    assert "1800" in argv
    assert "--workdir" in argv
    assert str(repo) in argv
    assert "--prompt-file" in argv
    assert "--usage-label" in argv
    assert "codex_lint_fix" in argv
    assert "run-external-agent" not in argv


def test_codex_descriptor_grants_only_run_dir_and_repo(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    run_dir = tmp_path / "implement" / "lint-fix-loop" / "step5.1"
    session_root = tmp_path / "implement"
    repo.mkdir()
    run_dir.mkdir(parents=True)
    request = _clf.VendorLaunchRequest(
        workdir=str(repo),
        output=str(run_dir / "codex.log"),
        prompt="fix lint",
        add_dirs=(str(run_dir), str(repo)),
    )
    argv = _clf.CODEX_DESCRIPTOR.build_argv("workspace-write", request)
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
        return ok(argv_tuple)


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
        assert append_argv[0].endswith("larch.sh") or "larch" in append_argv[0]
        assert append_argv[1:3] == ["token", "append-record"]
        assert append_argv[append_argv.index("--input") + 1] == str(token_record)
        assert append_argv[append_argv.index("--tmpdir") + 1] == str(implement_tmpdir)
        active_argv = list(active_calls[0][0])
        assert active_argv[1:3] == ["token", "record-vendor-sidecar"]
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
        _ok(""),  # baseline snapshot git diff --raw
        _ok(""),  # baseline snapshot git diff --cached --raw
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

    assert outcome.status == "failed"
    assert outcome.failure_reason == "lint-fix-all-tiers-no-useful-delta"
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
        _ok(""),  # baseline snapshot git diff --raw
        _ok(""),  # baseline snapshot git diff --cached --raw
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

    def fail_codex(*_args: object, **_kwargs: object) -> int:
        return 1

    def classify_must_not_run(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("dispatch failure classification must not select status")

    monkeypatch.setattr(_clf, "_run_codex", fail_codex)
    monkeypatch.setattr("larch.agents.agents.classify_launch_failure", classify_must_not_run)
    head = "abc123"
    runner = StubRunner([
        _ok(""),  # baseline tracked diff
        _ok(""),  # baseline cached diff
        _ok(""),  # baseline untracked status
        _ok(""),  # baseline snapshot git diff --raw
        _ok(""),  # baseline snapshot git diff --cached --raw
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
    assert outcome.status == "failed"
    assert outcome.failure_reason == "lint-fix-all-tiers-no-useful-delta"


def test_run_lint_fix_all_tools_timeout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Exit 124 from every selectable tier advances to named exhaustion."""

    def timeout_lane(*_args: object, **_kwargs: object) -> int:
        return config.PROC_TIMEOUT_EXIT_CODE

    monkeypatch.setattr(_clf, "_run_claude", timeout_lane)
    monkeypatch.setattr(_clf, "_run_codex", timeout_lane)
    repo = tmp_path / "repo"
    repo.mkdir()
    log = tmp_path / "checks.log"
    _ = log.write_text("lint error\n", encoding="utf-8")
    runner = StubRunner()
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
    assert outcome.status == "failed"
    assert outcome.failure_reason == "lint-fix-all-tiers-no-useful-delta"


def test_run_lint_fix_git_commit_applied_path(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    log = tmp_path / "checks.log"
    _ = log.write_text("lint error\n", encoding="utf-8")
    commit = "def456"
    head = "abc123"
    delta_raw = ":100644 100644 abc def M\tfixed.py\n"
    runner = StubRunner([
        # Baseline setup
        _ok(""),  # baseline tracked diff
        _ok(""),  # baseline cached diff
        _ok(""),  # baseline untracked status
        _ok(""),  # baseline snapshot git diff --raw
        _ok(""),  # baseline snapshot git diff --cached --raw
        _ok(head + "\n"),  # baseline HEAD
        _ok("main\n"),  # branch
        _ok(""),  # submodule foreach (prompt)
        _ok(""),  # submodule foreach (forbidden paths)
        # Per-attempt baseline (while-loop, before dispatch)
        _ok(""),  # attempt tracked diff
        _ok(""),  # attempt cached diff
        _ok(""),  # attempt untracked status
        _ok(""),  # attempt snapshot git diff --raw
        _ok(""),  # attempt snapshot git diff --cached --raw
        _ok(head + "\n"),  # attempt HEAD
        # Dispatch
        _ok(""),  # codex dispatch succeeds
        # Post-dispatch current snapshot (while-loop, after dispatch)
        _ok(""),  # current tracked diff
        _ok(""),  # current cached diff
        _ok(""),  # current untracked status
        _ok(delta_raw),  # current snapshot git diff --raw (useful delta)
        _ok(""),  # current snapshot git diff --cached --raw
        _ok(head + "\n"),  # current attempt HEAD
        # Post-loop: current HEAD (no change)
        _ok(head + "\n"),  # current HEAD after dispatch
        # _post_dispatch_forbidden_revert (head unchanged branch)
        _ok(""),  # forbidden-revert tracked diff
        _ok(""),  # forbidden-revert cached diff
        _ok(""),  # forbidden-revert untracked status
        # Final delta snapshot
        _ok("fixed.py\n"),  # current tracked diff
        _ok(""),  # current cached diff
        _ok(""),  # current untracked status
        _ok(delta_raw),  # final snapshot git diff --raw
        _ok(""),  # final snapshot git diff --cached --raw
        # Git operations
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
    assert "scripts/larch.sh git commit --no-trailer" in flat


def test_run_lint_fix_forbidden_reset_failure_is_structural(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    log = tmp_path / "checks.log"
    _ = log.write_text("lint error\n", encoding="utf-8")
    moved = "def456"
    head = "abc123"
    runner = StubRunner([
        # Baseline setup
        _ok(""),  # baseline tracked diff
        _ok(""),  # baseline cached diff
        _ok(""),  # baseline untracked status
        _ok(""),  # baseline snapshot git diff --raw
        _ok(""),  # baseline snapshot git diff --cached --raw
        _ok(head + "\n"),  # baseline HEAD
        _ok("main\n"),  # baseline branch
        _ok(""),  # submodule foreach (prompt)
        _ok(""),  # submodule foreach (forbidden paths)
        # Per-attempt baseline
        _ok(""),  # attempt tracked diff
        _ok(""),  # attempt cached diff
        _ok(""),  # attempt untracked status
        _ok(""),  # attempt snapshot git diff --raw
        _ok(""),  # attempt snapshot git diff --cached --raw
        _ok(head + "\n"),  # attempt HEAD
        # Dispatch
        _ok(""),  # codex dispatch succeeds
        # Post-dispatch current snapshot
        _ok(""),  # current tracked diff
        _ok(""),  # current cached diff
        _ok(""),  # current untracked status
        _ok(""),  # current snapshot git diff --raw
        _ok(""),  # current snapshot git diff --cached --raw
        _ok(moved + "\n"),  # current attempt HEAD (changed: useful delta)
        # Post-loop
        _ok(moved + "\n"),  # current HEAD after dispatch
        _ok("main\n"),  # current branch (for _head_change_invalid check)
        _ok(""),  # merge-base --is-ancestor
        _ok(head + "\n"),  # current parent
        _ok("", rc=1),  # no second parent
        _ok(".gitmodules\n"),  # committed forbidden path
        _ok("", rc=1),  # reset fails
        _ok(moved + "\n"),  # HEAD still moved (post-reset rev_parse)
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
    moved = "def456"
    head = "abc123"
    runner = StubRunner([
        # Baseline setup
        _ok(""),  # baseline tracked diff
        _ok(""),  # baseline cached diff
        _ok(""),  # baseline untracked status
        _ok(""),  # baseline snapshot git diff --raw
        _ok(""),  # baseline snapshot git diff --cached --raw
        _ok(head + "\n"),  # baseline HEAD
        _ok("main\n"),  # baseline branch
        _ok(""),  # submodule foreach (prompt)
        _ok(""),  # submodule foreach (forbidden paths)
        # Per-attempt baseline
        _ok(""),  # attempt tracked diff
        _ok(""),  # attempt cached diff
        _ok(""),  # attempt untracked status
        _ok(""),  # attempt snapshot git diff --raw
        _ok(""),  # attempt snapshot git diff --cached --raw
        _ok(head + "\n"),  # attempt HEAD
        # Dispatch
        _ok(""),  # codex dispatch succeeds
        # Post-dispatch current snapshot
        _ok(""),  # current tracked diff
        _ok(""),  # current cached diff
        _ok(""),  # current untracked status
        _ok(""),  # current snapshot git diff --raw
        _ok(""),  # current snapshot git diff --cached --raw
        _ok(moved + "\n"),  # current attempt HEAD (changed: useful delta)
        # Post-loop
        _ok(moved + "\n"),  # current HEAD after dispatch
        _ok("main\n"),  # current branch
        _ok(""),  # merge-base --is-ancestor
        _ok(head + "\n"),  # current parent
        _ok("", rc=1),  # no second parent
        _ok(".gitmodules\n"),  # committed forbidden path
        _ok(""),  # reset succeeds
        _ok(head + "\n"),  # HEAD reset (back to baseline)
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
    delta_raw = ":100644 100644 abc def M\t.gitmodules\n"
    runner = StubRunner([
        # Baseline setup
        _ok(""),  # baseline tracked diff
        _ok(""),  # baseline cached diff
        _ok(""),  # baseline untracked status
        _ok(""),  # baseline snapshot git diff --raw
        _ok(""),  # baseline snapshot git diff --cached --raw
        _ok(head + "\n"),  # baseline HEAD
        _ok("main\n"),  # branch
        _ok(""),  # submodule foreach (prompt)
        _ok(""),  # submodule foreach (forbidden paths)
        # Per-attempt baseline
        _ok(""),  # attempt tracked diff
        _ok(""),  # attempt cached diff
        _ok(""),  # attempt untracked status
        _ok(""),  # attempt snapshot git diff --raw
        _ok(""),  # attempt snapshot git diff --cached --raw
        _ok(head + "\n"),  # attempt HEAD
        # Dispatch
        _ok(""),  # codex dispatch succeeds
        # Post-dispatch current snapshot
        _ok(""),  # current tracked diff
        _ok(""),  # current cached diff
        _ok(""),  # current untracked status
        _ok(delta_raw),  # current snapshot git diff --raw (useful delta: .gitmodules)
        _ok(""),  # current snapshot git diff --cached --raw
        _ok(head + "\n"),  # current attempt HEAD (unchanged)
        # Post-loop: current HEAD (unchanged)
        _ok(head + "\n"),  # current HEAD after dispatch
        # _post_dispatch_forbidden_revert (head unchanged, else branch)
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

    def succeed_claude(*_args: object, **_kwargs: object) -> int:
        return 0

    monkeypatch.setattr(_clf, "_run_claude", succeed_claude)
    head = "abc123"
    plugin_raw = f":100644 100644 abc def M\t{config.PLUGIN_JSON_PATH}\n"
    runner = StubRunner([
        # Baseline setup
        _ok(""),  # baseline tracked diff
        _ok(""),  # baseline cached diff
        _ok(""),  # baseline untracked status
        _ok(""),  # baseline snapshot git diff --raw
        _ok(""),  # baseline snapshot git diff --cached --raw
        _ok(head + "\n"),  # baseline HEAD
        _ok("main\n"),  # branch
        _ok(""),  # submodule foreach (prompt)
        _ok(""),  # submodule foreach (forbidden paths)
        # Per-attempt baseline (claude is mocked, no dispatch stubs needed)
        _ok(""),  # attempt tracked diff
        _ok(""),  # attempt cached diff
        _ok(""),  # attempt untracked status
        _ok(""),  # attempt snapshot git diff --raw
        _ok(""),  # attempt snapshot git diff --cached --raw
        _ok(head + "\n"),  # attempt HEAD
        # Post-dispatch current snapshot (claude mocked, no dispatch stub)
        _ok(""),  # current tracked diff
        _ok(""),  # current cached diff
        _ok(""),  # current untracked status
        _ok(plugin_raw),  # current snapshot git diff --raw (useful delta: plugin.json)
        _ok(""),  # current snapshot git diff --cached --raw
        _ok(head + "\n"),  # current attempt HEAD (unchanged)
        # Post-loop: current HEAD (unchanged)
        _ok(head + "\n"),  # current HEAD after dispatch
        # _post_dispatch_forbidden_revert (head unchanged, else branch)
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
        # Baseline setup
        _ok(""),  # baseline tracked diff
        _ok(""),  # baseline cached diff
        _ok(""),  # baseline untracked status
        _ok(""),  # baseline snapshot git diff --raw
        _ok(""),  # baseline snapshot git diff --cached --raw
        _ok(head + "\n"),  # baseline HEAD
        _ok("main\n"),  # branch
        _ok(""),  # submodule foreach (prompt)
        _ok(""),  # submodule foreach (forbidden paths)
        # Per-attempt baseline (before cursor dispatch)
        _ok(""),  # attempt tracked diff
        _ok(""),  # attempt cached diff
        _ok(""),  # attempt untracked status
        _ok(""),  # attempt snapshot git diff --raw
        _ok(""),  # attempt snapshot git diff --cached --raw
        _ok(head + "\n"),  # attempt HEAD
        # Cursor dispatch (cursor-wrap-prompt.sh + cursor agent)
        _ok("wrapped promptX"),  # cursor-wrap-prompt.sh
        _ok("", rc=1),  # cursor dispatch fails
        # Post-dispatch current snapshot (no useful delta)
        _ok(""),  # current tracked diff
        _ok(""),  # current cached diff
        _ok(""),  # current untracked status
        _ok(""),  # current snapshot git diff --raw (empty = no useful delta)
        _ok(""),  # current snapshot git diff --cached --raw
        _ok(head + "\n"),  # current attempt HEAD (unchanged)
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
    assert outcome.status == "failed"
    assert outcome.failure_reason == "lint-fix-all-tiers-no-useful-delta"
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
    entrypoint = str(_clf.larch_entrypoint(_clf.plugin_root()))
    idx = list(cursor_call).index(entrypoint)
    argv = list(cursor_call)[idx:]
    assert argv[:4] == [entrypoint, "agent", "run-external-agent", "--tool"]
    assert argv[4] == "cursor"
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
    head = "abc123"
    delta_raw = ":100644 100644 abc def M\tfixed.py\n"
    runner = StubRunner([
        # Baseline setup
        _ok(""),  # baseline tracked diff
        _ok(""),  # baseline cached diff
        _ok(""),  # baseline untracked status
        _ok(""),  # baseline snapshot git diff --raw
        _ok(""),  # baseline snapshot git diff --cached --raw
        _ok(head + "\n"),  # rev-parse HEAD
        _ok("main\n"),  # symbolic-ref
        _ok(""),  # submodule foreach (prompt)
        _ok(""),  # submodule foreach (forbidden paths)
        # Per-attempt baseline (claude is first, mocked)
        _ok(""),  # attempt tracked diff
        _ok(""),  # attempt cached diff
        _ok(""),  # attempt untracked status
        _ok(""),  # attempt snapshot git diff --raw
        _ok(""),  # attempt snapshot git diff --cached --raw
        _ok(head + "\n"),  # attempt HEAD
        # Post-dispatch current snapshot (claude mocked, no dispatch stub)
        _ok(""),  # current tracked diff
        _ok(""),  # current cached diff
        _ok(""),  # current untracked status
        _ok(delta_raw),  # current snapshot git diff --raw (useful delta)
        _ok(""),  # current snapshot git diff --cached --raw
        _ok(head + "\n"),  # current attempt HEAD (unchanged)
        # Post-loop: current HEAD (unchanged)
        _ok(head + "\n"),  # current HEAD after dispatch
        # _post_dispatch_forbidden_revert (head unchanged, else branch)
        _ok(""),  # forbidden-revert tracked diff
        _ok(""),  # forbidden-revert cached diff
        _ok(""),  # forbidden-revert untracked status
        # Final delta snapshot
        _ok("fixed.py\n"),  # current tracked diff
        _ok(""),  # current cached diff
        _ok(""),  # current untracked status
        _ok(delta_raw),  # final snapshot git diff --raw
        _ok(""),  # final snapshot git diff --cached --raw
        # Git operations
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
    monkeypatch.delenv("CLAUDE_BINARY_FOUND", raising=False)
    head = "abc123"
    delta_raw = ":100644 100644 abc def M\tfixed.py\n"
    runner = StubRunner([
        # Baseline setup
        _ok(""),  # baseline tracked diff
        _ok(""),  # baseline cached diff
        _ok(""),  # baseline untracked status
        _ok(""),  # baseline snapshot git diff --raw
        _ok(""),  # baseline snapshot git diff --cached --raw
        _ok(head + "\n"),  # rev-parse HEAD
        _ok("main\n"),  # symbolic-ref
        _ok(""),  # submodule foreach (prompt)
        _ok(""),  # submodule foreach (forbidden paths)
        # Per-attempt: claude (fails, mocked)
        _ok(""),  # attempt tracked diff
        _ok(""),  # attempt cached diff
        _ok(""),  # attempt untracked status
        _ok(""),  # attempt snapshot git diff --raw
        _ok(""),  # attempt snapshot git diff --cached --raw
        _ok(head + "\n"),  # attempt HEAD
        # Post-dispatch: claude (no useful delta)
        _ok(""),  # current tracked diff
        _ok(""),  # current cached diff
        _ok(""),  # current untracked status
        _ok(""),  # current snapshot git diff --raw
        _ok(""),  # current snapshot git diff --cached --raw
        _ok(head + "\n"),  # current attempt HEAD
        # Per-attempt: codex (fails, mocked)
        _ok(""),  # attempt tracked diff
        _ok(""),  # attempt cached diff
        _ok(""),  # attempt untracked status
        _ok(""),  # attempt snapshot git diff --raw
        _ok(""),  # attempt snapshot git diff --cached --raw
        _ok(head + "\n"),  # attempt HEAD
        # Post-dispatch: codex (no useful delta)
        _ok(""),  # current tracked diff
        _ok(""),  # current cached diff
        _ok(""),  # current untracked status
        _ok(""),  # current snapshot git diff --raw
        _ok(""),  # current snapshot git diff --cached --raw
        _ok(head + "\n"),  # current attempt HEAD
        # Per-attempt: cursor (succeeds, mocked)
        _ok(""),  # attempt tracked diff
        _ok(""),  # attempt cached diff
        _ok(""),  # attempt untracked status
        _ok(""),  # attempt snapshot git diff --raw
        _ok(""),  # attempt snapshot git diff --cached --raw
        _ok(head + "\n"),  # attempt HEAD
        # Post-dispatch: cursor (useful delta!)
        _ok(""),  # current tracked diff
        _ok(""),  # current cached diff
        _ok(""),  # current untracked status
        _ok(delta_raw),  # current snapshot git diff --raw (useful delta)
        _ok(""),  # current snapshot git diff --cached --raw
        _ok(head + "\n"),  # current attempt HEAD (unchanged)
        # Post-loop: current HEAD (unchanged)
        _ok(head + "\n"),  # current HEAD after dispatch
        # _post_dispatch_forbidden_revert
        _ok(""),  # forbidden-revert tracked diff
        _ok(""),  # forbidden-revert cached diff
        _ok(""),  # forbidden-revert untracked status
        # Final delta snapshot
        _ok("fixed.py\n"),  # current tracked diff
        _ok(""),  # current cached diff
        _ok(""),  # current untracked status
        _ok(delta_raw),  # final snapshot git diff --raw
        _ok(""),  # final snapshot git diff --cached --raw
        # Git operations
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
    assert loop.status == "main-agent-required"
    assert checks.escalate(loop.status).outcome == Outcome.NEEDS_USER_INPUT


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
    assert outcome.status == "failed"
    assert outcome.failure_reason == "lint-fix-all-tiers-no-useful-delta"


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
        if any("cli.py" in name or "larch.sh" in name for name in call)
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
    assert outcome.status == "failed"
    assert outcome.failure_reason == "lint-fix-no-selectable-tier"
    assert outcome.tier_ledger_path
    assert outcome.ledger_ready is False
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
    assert outcome.status == "failed"
    assert outcome.failure_reason == "lint-fix-no-selectable-tier"
    assert outcome.tier_ledger_path
    assert outcome.ledger_ready is False
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

def _precommit_hook_rows(text: str) -> dict[str, dict[str, str]]:
    hooks: dict[str, dict[str, str]] = {}
    current: dict[str, str] | None = None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- id: "):
            hook_id = stripped.removeprefix("- id: ")
            current = {"id": hook_id}
            hooks[hook_id] = current
            continue
        if current is None or ": " not in stripped:
            continue
        key, value = stripped.split(": ", 1)
        if key in {"entry", "files", "pass_filenames", "always_run", "stages", "verbose"}:
            current[key] = value
    return hooks


def test_default_precommit_stage_is_bounded_and_ci_keeps_exhaustive_rust_checks() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    precommit = (repo_root / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    workflow = (repo_root / ".github" / "workflows" / "ci.yaml").read_text(encoding="utf-8")
    makefile = (repo_root / "Makefile").read_text(encoding="utf-8")
    hooks = _precommit_hook_rows(precommit)
    rust_lint = workflow.split("\n  rust-lint:", 1)[1].split("\n  rust-deny:", 1)[0]
    rust_deny = workflow.split("\n  rust-deny:", 1)[1].split("\n  rust-full:", 1)[0]
    rust_coverage = (
        repo_root / ".github" / "actions" / "rust-coverage" / "action.yaml"
    ).read_text(encoding="utf-8")
    lint = workflow.split("\n  lint:", 1)[1].split("\n  lint-local:", 1)[0]
    lint_local = workflow.split("\n  lint-local:", 1)[1].split("\n  shellcheck:", 1)[0]
    shellcheck = workflow.split("\n  shellcheck:", 1)[1].split("\n  test-harnesses:", 1)[0]
    lint_skip = lint.split("SKIP: ", 1)[1].split("\n", 1)[0].split(",")
    lint_local_skip = lint_local.split("SKIP: ", 1)[1].split("\n", 1)[0].split(",")

    assert "id: ruff" in precommit
    assert "ruff check --fix" in precommit
    assert "id: pyright" in precommit
    assert "pyright --project python/pyrightconfig.json" in precommit
    assert hooks["cargo-clippy"]["entry"] == "python3 python/cli.py checks rust-clippy --repo-root ."
    assert "\\.cargo/.*" in hooks["cargo-clippy"]["files"]
    assert hooks["cargo-clippy"]["pass_filenames"] == "true"
    assert hooks["cargo-clippy"]["verbose"] == "true"
    assert hooks["pyright"]["stages"] == "[manual]"
    assert hooks["agent-lint"]["stages"] == "[manual]"
    for manual_only in ("agent-lint", "agnix", "gitleaks", "larch-lint", "pyright"):
        assert hooks[manual_only]["stages"] == "[manual]"
    for hook in hooks.values():
        if hook.get("stages") == "[manual]":
            continue
        entry = hook.get("entry", "")
        assert not (hook.get("pass_filenames") == "false" and hook.get("always_run") == "true")
        for forbidden in ("cargo build", "cargo test", "cargo llvm-cov", "--all-targets", "--all-features", "--release"):
            assert forbidden not in entry
        assert "cargo run" not in entry
    assert "contains-pins:" in workflow
    assert "python3 python/cli.py checks contains-pins" in workflow
    assert "python-lint:" not in workflow
    assert "python-pyright:" in workflow
    assert "agent-lint:" in workflow
    assert "rust-lint:" in workflow
    assert "rust-deny:" in workflow
    assert "rust-build-test:" not in workflow
    assert "\n  rust-clippy:" not in workflow
    assert "rust-coverage-profile:" not in workflow
    assert "rust-coverage:" in workflow
    assert "rust-coverage-benchmark:" in workflow
    assert "rust-gate:" in workflow
    assert "needs: [rust-lint, rust-deny, rust-coverage]" in workflow
    assert "make rust-fmt" in rust_lint
    assert "make rust-clippy" in rust_lint
    assert "make rust-lint" not in rust_lint
    assert "cargo-deny-action" not in rust_lint
    assert '"$coverage_larch" lint all' in rust_coverage
    assert "make rust-lint" not in rust_coverage
    assert "make rust-build" not in workflow
    assert "make rust-test" not in workflow
    assert "cargo llvm-cov nextest --no-report" in rust_coverage
    assert "cargo test --doc" in rust_coverage
    assert "make rust-coverage" not in workflow
    assert "rust-coverage" not in makefile
    assert "crates/larch-harness-mark/src/residual_bash_main.rs" in shellcheck
    assert "rustc --edition=2024 --crate-name larch_residual_bash_paths" in shellcheck
    assert '"$residual_bash_reader" --root "$GITHUB_WORKSPACE"' in shellcheck
    assert "cargo build" not in shellcheck
    assert '"$GITHUB_WORKSPACE/scripts/larch.sh" residual-bash paths' not in shellcheck
    assert "EmbarkStudios/cargo-deny-action@b66acf5e9fe20f8aba065be86778a8a4c846f902" in rust_deny
    for hook in (
        "cargo-fmt",
        "cargo-clippy",
        "larch-lint",
        "check-topology-rule-paths",
        "lint-retired-scripts",
    ):
        assert hook in lint_skip
        assert hook in lint_local_skip
    assert "ruff" in lint_skip
    assert "ruff" not in lint_local_skip


def test_ci_branch_safety_merge_group_and_required_context_contract() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    workflow = (repo_root / ".github" / "workflows" / "ci.yaml").read_text(encoding="utf-8")
    publication = (
        repo_root / ".github" / "workflows" / "main-cache-publication.yaml"
    ).read_text(encoding="utf-8")
    linting = (repo_root / "docs" / "linting.md").read_text(encoding="utf-8")
    coverage_action = (
        repo_root / ".github" / "actions" / "rust-coverage" / "action.yaml"
    ).read_text(encoding="utf-8")
    required_contexts = (
        "lint",
        "lint-local",
        "shellcheck",
        "test-harnesses-gate",
        "agent-lint",
        "rust-coverage",
        "rust-gate",
        "contains-pins",
        "gitleaks",
        "agent-sync",
        "trufflehog",
        "python-pyright",
        "python-tests-gate",
    )
    workflow_trigger = workflow.split("\nconcurrency:", 1)[0]
    ruleset_section = linting.split("### CI and branch-safety ruleset", 1)[1].split(
        "### Changing the shard count", 1
    )[0]
    rust_selection = workflow.split("\n  rust-selection:", 1)[1].split(
        "\n  rust-lint:", 1
    )[0]
    rust_full = workflow.split("\n  rust-full:", 1)[1].split("\n  rust-partial:", 1)[0]
    rust_coverage = workflow.split("\n  rust-coverage:", 1)[1].split(
        "\n  rust-coverage-benchmark:", 1
    )[0]
    rust_gate = workflow.split("\n  rust-gate:", 1)[1].split("\n  contains-pins:", 1)[0]
    test_harnesses_gate = workflow.split("\n  test-harnesses-gate:", 1)[1].split(
        "\n  agent-lint:", 1
    )[0]
    python_tests_gate = workflow.split("\n  python-rust-integration:", 1)[1].split(
        "\n  gitleaks:", 1
    )[0]

    assert "merge_group:\n    types: [checks_requested]" in workflow_trigger
    assert "\n  push:" not in workflow_trigger
    assert "if: github.event_name == 'pull_request'" in rust_selection
    assert "github.event_name != 'pull_request'" in rust_full
    assert "if: always()" in test_harnesses_gate
    assert "if: always()" in rust_coverage
    assert "if: always()" in rust_gate
    assert "if: always()" in python_tests_gate
    assert "needs: [rust-lint, rust-deny, rust-coverage]" in rust_gate
    assert "needs: [rust-coverage, python-tests]" in python_tests_gate
    assert 'test "$FULL_RESULT" = success' in rust_coverage
    for result_name in ("lint_result", "deny_result", "coverage_result"):
        assert f'[ "${result_name}" = success ]' in rust_gate

    assert tuple(re.findall(r"^- `([^`]+)`$", ruleset_section, re.MULTILINE)) == required_contexts
    assert "source-bound to the GitHub Actions integration (`15368`)" in ruleset_section
    assert "strict_required_status_checks_policy" in ruleset_section
    assert "full, read-only validation lane before each merge" in ruleset_section
    assert "trusted cache-publication workflow" in ruleset_section
    assert "exact final main\nSHA" in ruleset_section
    assert "Do not require a matrix leg or a conditional implementation detail." in ruleset_section
    for merge_queue_parameter in (
        "`ALLGREEN`",
        "`max_entries_to_build=1`",
        "`max_entries_to_merge=1`",
        "`min_entries_to_merge=1`",
        "`min_entries_to_merge_wait_minutes=0`",
    ):
        assert merge_queue_parameter in ruleset_section
    for conditional_context in (
        "rust-selection",
        "rust-lint",
        "rust-deny",
        "rust-full",
        "rust-partial",
        "rust-skip",
    ):
        assert f"`{conditional_context}`" in ruleset_section

    required_job_anchors = {
        "lint": "\n  lint:",
        "lint-local": "\n  lint-local:",
        "shellcheck": "\n  shellcheck:",
        "test-harnesses-gate": "\n  test-harnesses-gate:\n    name: test-harnesses-gate",
        "agent-lint": "\n  agent-lint:",
        "rust-coverage": "\n  rust-coverage:\n    name: rust-coverage",
        "rust-gate": "\n  rust-gate:\n    name: rust-gate",
        "contains-pins": "\n  contains-pins:",
        "gitleaks": "\n  gitleaks:",
        "agent-sync": "\n  agent-sync:",
        "trufflehog": "\n  trufflehog:",
        "python-pyright": "\n  python-pyright:",
        "python-tests-gate": "\n  python-rust-integration:\n    name: python-tests-gate",
    }
    assert tuple(required_job_anchors) == required_contexts
    for context, anchor in required_job_anchors.items():
        assert anchor in workflow, context

    for unconditionally_reported_job in (
        "lint",
        "lint-local",
        "shellcheck",
        "agent-lint",
        "contains-pins",
        "gitleaks",
        "agent-sync",
        "trufflehog",
        "python-pyright",
    ):
        job = workflow.split(f"\n  {unconditionally_reported_job}:", 1)[1].split(
            "\n  ", 1
        )[0]
        assert re.search(r"^    if:", job, re.MULTILINE) is None, unconditionally_reported_job

    assert "actions/cache/save@" not in rust_full
    assert "github.event_name == 'push'" not in workflow
    assert "main-cache-candidate" in coverage_action
    assert "main-cache-publication" in publication
    assert "push:\n    branches:\n      - main" in publication
    assert "workflow_dispatch:" in publication
    assert "push:refs/heads/main|workflow_dispatch:refs/heads/main" in publication
    assert "group: main-cache-publication" in publication
    assert "cancel-in-progress: true" in publication


def test_main_cache_inventory_and_publication_contract() -> None:
    """Keep cache names, keys, validation, and trusted writers in lockstep."""
    repo_root = Path(__file__).resolve().parents[3]
    inventory_value: object = json.loads(
        (repo_root / ".github" / "main-cache-inventory.json").read_text(encoding="utf-8")
    )
    assert isinstance(inventory_value, dict)
    # json.loads returns an unparameterized dict; JSON object keys are strings.
    inventory = cast("dict[str, object]", inventory_value)
    key_action = (
        repo_root / ".github" / "actions" / "main-cache-keys" / "action.yaml"
    ).read_text(encoding="utf-8")
    validation = (repo_root / ".github" / "workflows" / "ci.yaml").read_text(
        encoding="utf-8"
    )
    coverage_action = (
        repo_root / ".github" / "actions" / "rust-coverage" / "action.yaml"
    ).read_text(encoding="utf-8")
    publication = (
        repo_root / ".github" / "workflows" / "main-cache-publication.yaml"
    ).read_text(encoding="utf-8")
    rust_probe = publication.split("\n  main-cache-probe:", 1)[1].split(
        "\n  main-cache-merge-group-source:", 1
    )[0]
    merge_group_source = publication.split(
        "\n  main-cache-merge-group-source:", 1
    )[1].split("\n  main-cache-rust-promotion:", 1)[0]
    rust_promotion_lookup = (
        publication.split("\n  main-cache-rust-promotion:", 1)[1]
        .split("\n      - name: Download Cargo inputs candidate", 1)[0]
    )
    rust_promotion = publication.split("\n  main-cache-rust-promotion:", 1)[1]
    gitleaks_publisher = publication.split("\n  main-cache-gitleaks:", 1)[1].split(
        "\n  main-cache-probe:", 1
    )[0]
    source_resolver = (
        repo_root / "crates" / "larch-core" / "src" / "main_cache.rs"
    ).read_text(encoding="utf-8")
    github_auth_config = (
        repo_root / ".github" / "actions" / "github-auth-config" / "action.yaml"
    ).read_text(encoding="utf-8")
    candidate_helper = (
        repo_root / "python" / "larch" / "implement" / "main_cache_candidate.py"
    ).read_text(encoding="utf-8")
    supply_chain = (
        repo_root / "docs" / "security" / "supply-chain-credentials-and-services.md"
    ).read_text(encoding="utf-8")
    shipped_supply_chain = (
        repo_root
        / "plugin"
        / "docs"
        / "security"
        / "supply-chain-credentials-and-services.md"
    ).read_text(encoding="utf-8")
    workflow_trust = (
        repo_root / "docs" / "security" / "workflow-trust-and-mutations.md"
    ).read_text(encoding="utf-8")
    shipped_workflow_trust = (
        repo_root
        / "plugin"
        / "docs"
        / "security"
        / "workflow-trust-and-mutations.md"
    ).read_text(encoding="utf-8")

    assert inventory["schema_version"] == 1
    classes_value = inventory["cache_classes"]
    assert isinstance(classes_value, list)
    classes = cast("list[object]", classes_value)
    assert len(classes) == 18
    cache_class_ids: list[str] = []
    for raw_entry in classes:
        assert isinstance(raw_entry, dict)
        # The JSON object is constrained by the assertions below.
        entry = cast("dict[str, object]", raw_entry)
        cache_class = entry["id"]
        key_output = entry["key_output"]
        producer = entry["producer"]
        key_inputs = entry["key_inputs"]
        validation_prerequisite = entry["validation"]
        publication_event = entry["publication_event"]
        assert isinstance(cache_class, str)
        assert isinstance(key_output, str)
        assert isinstance(producer, str)
        assert isinstance(key_inputs, list)
        assert isinstance(validation_prerequisite, str)
        assert publication_event == "trusted-main"
        assert key_inputs
        assert validation_prerequisite
        cache_class_ids.append(cache_class)
        assert f"  {key_output}:" in key_action
        assert f"  {producer}:" in publication
        canonical_key_reference = f"steps.main-cache-keys.outputs.{key_output}"
        assert canonical_key_reference in validation
        assert canonical_key_reference in publication
    assert len(set(cache_class_ids)) == len(classes)

    assert "actions/cache/save@" not in validation
    assert "cache: pip" not in validation
    assert "main-cache-merge-group-source" in publication
    assert "ci-timing merge-group-source" in publication
    assert 'source-sha "$GITHUB_SHA"' in publication
    assert "actions/cache/save@" not in merge_group_source
    assert "restore-keys:" not in merge_group_source
    assert "uses: ./.github/actions/main-cache-keys" in merge_group_source
    assert (
        merge_group_source.count(
            "actions/cache/restore@caa296126883cff596d87d8935842f9db880ef25"
        )
        == 2
    )
    for cache_path, cache_key in (
        (
            "path: |\n            ~/.cargo/registry\n            ~/.cargo/git",
            "key: ${{ steps.main-cache-keys.outputs.cargo-inputs }}",
        ),
        (
            "path: target/debug",
            "key: ${{ steps.main-cache-keys.outputs.rust-lint-deps }}",
        ),
    ):
        assert cache_path in merge_group_source
        assert cache_key in merge_group_source
    assert (
        merge_group_source.index(
            "Restore Cargo inputs for typed merge-group source resolution"
        )
        < merge_group_source.index("Resolve the exact successful merge-group producer run")
    )
    assert (
        merge_group_source.index(
            "Restore Rust lint dependencies for typed merge-group source resolution"
        )
        < merge_group_source.index("Resolve the exact successful merge-group producer run")
    )
    for profile_value in (
        'CARGO_INCREMENTAL: "0"',
        'CARGO_PROFILE_DEV_DEBUG: "0"',
        'CARGO_PROFILE_TEST_DEBUG: "0"',
    ):
        assert profile_value in merge_group_source
    assert "resolver_seconds" in merge_group_source
    assert "cargo_inputs_cache_hit" in merge_group_source
    assert "rust_lint_deps_cache_hit" in merge_group_source
    assert "cargo run --quiet --locked --package larch-cli" in merge_group_source
    assert "target/debug/larch" not in merge_group_source
    assert "uses: ./.github/actions/github-auth-config" in publication
    assert "GH_TOKEN:" not in publication
    assert "GH_CONFIG_DIR: ${{ steps.github-auth.outputs.config-dir }}" in publication
    assert "gh api" not in publication
    assert "resolve_main_cache_merge_group_source" in source_resolver
    assert "workflow: Some(CI_WORKFLOW.to_owned())" in source_resolver
    assert "event: Some(MERGE_GROUP.to_owned())" in source_resolver
    assert "status: Some(COMPLETED.to_owned())" in source_resolver
    assert "commit: Some(source_sha.to_owned())" in source_resolver
    assert "expected exactly one successful CI merge-group run" in source_resolver
    assert "successful merge-group producer is missing required Rust jobs" in source_resolver
    assert "gh auth login --hostname github.com --with-token" in github_auth_config
    assert "gh auth status --hostname github.com >/dev/null" in github_auth_config
    assert 'mktemp -d "$RUNNER_TEMP/larch-gh.XXXXXX"' in github_auth_config
    assert "unset GH_TOKEN GITHUB_TOKEN" in github_auth_config
    assert "config-dir=%s" in github_auth_config
    assert "actions/download-artifact@" in publication
    assert "run-id: ${{ needs.main-cache-merge-group-source.outputs.run-id }}" in publication
    assert "ci verify-main-cache-candidate" in publication
    canonical_rust_cache_paths = (
        "path: |\n            ~/.cargo/registry\n            ~/.cargo/git",
        "path: target/debug",
        "path: ~/.cargo/bin/cargo-nextest",
        "path: ~/.cargo/bin/cargo-llvm-cov",
        "path: target/llvm-cov-target",
        "path: ${{ runner.temp }}/trusted-main-rust-policy",
    )
    for lookup_job in (rust_probe, rust_promotion_lookup):
        for cache_path in canonical_rust_cache_paths:
            assert cache_path in lookup_job
    for cache_path in canonical_rust_cache_paths:
        assert rust_promotion.count(cache_path) == 2
    assert "path: ${{ runner.temp }}/main-cache-probe/" not in rust_probe
    assert "path: ${{ runner.temp }}/main-cache-promoted/" not in rust_promotion
    for canonical_materialization in (
        'mv -- "$RUNNER_TEMP/main-cache-promoted/cargo-inputs/registry" "$HOME/.cargo/registry"',
        'mv -- "$RUNNER_TEMP/main-cache-promoted/cargo-inputs/git" "$HOME/.cargo/git"',
        'mv -- "$RUNNER_TEMP/main-cache-promoted/rust-lint-deps/debug" "$GITHUB_WORKSPACE/target/debug"',
        'mv -- "$RUNNER_TEMP/main-cache-promoted/cargo-nextest/cargo-nextest" "$HOME/.cargo/bin/cargo-nextest"',
        'mv -- "$RUNNER_TEMP/main-cache-promoted/cargo-llvm-cov/cargo-llvm-cov" "$HOME/.cargo/bin/cargo-llvm-cov"',
        'mv -- "$RUNNER_TEMP/main-cache-promoted/coverage-target/llvm-cov-target" "$GITHUB_WORKSPACE/target/llvm-cov-target"',
        '--policy-dir "$RUNNER_TEMP/trusted-main-rust-policy"',
    ):
        assert canonical_materialization in rust_promotion
    assert (
        'if [ -e "$RUNNER_TEMP/main-cache-promoted/cargo-inputs/git" ]; then\n'
        '            test -d "$RUNNER_TEMP/main-cache-promoted/cargo-inputs/git"\n'
        '            mv -- "$RUNNER_TEMP/main-cache-promoted/cargo-inputs/git" "$HOME/.cargo/git"\n'
        '          else\n'
        '            mkdir -p "$HOME/.cargo/git"\n'
        '          fi'
    ) in rust_promotion
    assert "/*\n            !/larch-logs/" in gitleaks_publisher
    assert "/.github/actions/main-cache-keys/" not in gitleaks_publisher
    for validation_operation in (
        "pre-commit run",
        "pytest",
        "gitleaks detect",
        "cargo llvm-cov",
        "cargo nextest run",
        "make test-harnesses",
    ):
        assert validation_operation not in publication
    assert "candidate producer event is not merge_group" in candidate_helper
    assert "candidate producer ref is not a merge-queue ref" in candidate_helper
    assert "candidate payload members do not match its manifest" in candidate_helper
    assert "candidate tool versions do not match the publisher contract" in candidate_helper
    assert "_SCHEMA_VERSION: Final = 2" in candidate_helper
    assert '"mtime_ns": member.mtime_ns' in candidate_helper
    assert "os.utime(" in candidate_helper
    assert "_reject_tree_symlinks" in candidate_helper
    assert "default: v2" in key_action
    assert "cargo-inputs=cargo-inputs-v2-" in key_action
    assert "rust-lint-deps=rust-lint-deps-v2-" in key_action
    assert (
        '--tool-version "cargo-nextest=cargo-nextest ${CARGO_NEXTEST_VERSION}"'
        in coverage_action
    )
    assert (
        '--tool-version "cargo-llvm-cov=cargo-llvm-cov ${CARGO_LLVM_COV_VERSION}"'
        in coverage_action
    )
    assert "main-cache-merge-group-source" in supply_chain
    assert (
        "cache action evidence, those values support comparable exact-hit and\n"
        "Cargo-graph-miss samples"
    ) in supply_chain
    assert (
        "does not weaken\n"
        "final-SHA, event, workflow, producer, or ambiguity verification"
    ) in workflow_trust
    assert shipped_supply_chain == supply_chain
    assert shipped_workflow_trust == workflow_trust

    candidate_artifacts = {
        "cargo-inputs": "main-cache-cargo-inputs-candidate",
        "rust-lint-deps": "main-cache-rust-lint-deps-candidate",
        "cargo-nextest": "main-cache-cargo-nextest-candidate",
        "cargo-llvm-cov": "main-cache-cargo-llvm-cov-candidate",
        "coverage-target": "main-cache-coverage-target-candidate",
        "rust-policy": "main-cache-rust-policy-candidate",
    }
    for cache_class, artifact_name in candidate_artifacts.items():
        assert artifact_name in validation or artifact_name in coverage_action
        assert artifact_name in publication
        assert f"--cache-class {cache_class}" in publication
        assert f"--artifact-name {artifact_name}" in publication
    candidate_uploads = (
        (validation, "main-cache-cargo-inputs-candidate"),
        (validation, "main-cache-rust-lint-deps-candidate"),
        (coverage_action, "main-cache-cargo-nextest-candidate"),
        (coverage_action, "main-cache-cargo-llvm-cov-candidate"),
        (coverage_action, "main-cache-coverage-target-candidate"),
        (validation, "main-cache-rust-policy-candidate"),
    )
    assert {artifact_name for _, artifact_name in candidate_uploads} == set(
        candidate_artifacts.values()
    )
    for workflow_surface, artifact_name in candidate_uploads:
        upload_pattern = (
            rf"(?m)^\s*name: {re.escape(artifact_name)}\n"
            rf"\s*path: \$\{{\{{ runner\.temp \}}\}}/{re.escape(artifact_name)}\n"
            r"\s*include-hidden-files: true$"
        )
        assert re.search(upload_pattern, workflow_surface)
    assert "overwrite: false" in validation
    assert "overwrite: false" in coverage_action


def test_coverage_cache_diagnostics_preserve_a_prior_failure(tmp_path: Path) -> None:
    """Replay skipped cache steps after a prior failure without masking it."""
    repo_root = Path(__file__).resolve().parents[3]
    coverage_action = (
        repo_root / ".github" / "actions" / "rust-coverage" / "action.yaml"
    ).read_text(encoding="utf-8")

    def run_diagnostic(
        start: str, end: str, outcome: str, prior_failure_or_cancelled: str
    ) -> subprocess.CompletedProcess[str]:
        script = (
            coverage_action.split(start, 1)[1]
            .split(end, 1)[0]
            .split("run: |\n", 1)[1]
            .split("\n    - name:", 1)[0]
        )
        script = textwrap.dedent(script).replace(
            "${{ steps.coverage-target-cache.outcome }}", "$DIAGNOSTIC_OUTCOME"
        )
        script = script.replace(
            "${{ steps.coverage-target-cache-prune.outcome }}", "$DIAGNOSTIC_OUTCOME"
        )
        script = script.replace(
            "${{ steps.coverage-target-cache.outputs.cache-hit }}",
            "$DIAGNOSTIC_CACHE_HIT",
        )
        environment: dict[str, str] = os.environ.copy()
        environment.update(
            {
                "COVERAGE_TARGET_CACHE_ENABLED": "true",
                "COVERAGE_TARGET_CACHE_POST_PRUNE_BYTES": "unavailable",
                "COVERAGE_TARGET_CACHE_RESTORE_STARTED": "0",
                "COVERAGE_TARGET_CACHE_SAVE_REASON": "not-available",
                "COVERAGE_TIMING_FILE": str(tmp_path / "coverage-timing.tsv"),
                "COVERAGE_TARGET_CACHE_INVENTORY": str(
                    tmp_path / "coverage-inventory.tsv"
                ),
                "DIAGNOSTIC_CACHE_HIT": "",
                "COVERAGE_PRIOR_FAILURE_OR_CANCELLATION": prior_failure_or_cancelled,
                "DIAGNOSTIC_OUTCOME": outcome,
                "GITHUB_ENV": str(tmp_path / "github-env"),
            }
        )
        return subprocess.run(
            ["bash", "-c", script],
            check=False,
            capture_output=True,
            env=environment,
            text=True,
        )

    for start, end in (
        (
            "Record coverage dependency cache restore diagnostics",
            "Start Rust coverage tool setup timing",
        ),
        (
            "Record coverage dependency cache prune diagnostics",
            "Upload coverage target cache inventory",
        ),
    ):
        prior_failure = run_diagnostic(start, end, "skipped", "true")
        assert prior_failure.returncode == 0, prior_failure.stderr

        unexpected_skip = run_diagnostic(start, end, "skipped", "false")
        assert unexpected_skip.returncode != 0
        assert "unexpected coverage target" in unexpected_skip.stderr


def test_github_auth_config_keeps_action_token_out_of_typed_operation(tmp_path: Path) -> None:
    """Execute the credential bootstrap with a fake gh client and inspect its boundary."""
    repo_root = Path(__file__).resolve().parents[3]
    action = (
        repo_root / ".github" / "actions" / "github-auth-config" / "action.yaml"
    ).read_text(encoding="utf-8")
    script = textwrap.dedent(action.split("run: |\n", 1)[1])
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    gh = bin_dir / "gh"
    gh.write_text(
        "#!/bin/sh\n"
        'test -z "${GH_TOKEN:-}"\n'
        'test -z "${GITHUB_TOKEN:-}"\n'
        'test -n "${GH_CONFIG_DIR:-}"\n'
        'test -d "$GH_CONFIG_DIR"\n'
        'case "$1 $2" in\n'
        "  'auth login') IFS= read -r token; test \"$token\" = expected-action-token ;;\n"
        "  'auth status') ;;\n"
        "  *) exit 1 ;;\n"
        "esac\n",
        encoding="utf-8",
    )
    gh.chmod(0o755)
    github_output = tmp_path / "github-output"
    environment: dict[str, str] = os.environ.copy()
    environment.update(
        {
            "GH_TOKEN": "expected-action-token",
            "GITHUB_OUTPUT": str(github_output),
            "GITHUB_TOKEN": "must-not-reach-gh",
            "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
            "RUNNER_TEMP": str(tmp_path),
        }
    )

    result = subprocess.run(
        ["bash", "-c", script],
        check=False,
        capture_output=True,
        env=environment,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    config_dir = Path(github_output.read_text(encoding="utf-8").strip().removeprefix("config-dir="))
    assert config_dir.is_dir()
    assert config_dir.parent == tmp_path
    assert config_dir.stat().st_mode & 0o077 == 0


def test_rust_ci_cache_tool_and_gate_contract() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    workflow = (repo_root / ".github" / "workflows" / "ci.yaml").read_text(encoding="utf-8")
    rust_testing = (repo_root / "docs" / "rust-testing.md").read_text(encoding="utf-8")
    supply_chain = (
        repo_root / "docs" / "security" / "supply-chain-credentials-and-services.md"
    ).read_text(encoding="utf-8")
    supply_chain_text = " ".join(supply_chain.split())
    workflow_trust = (
        repo_root / "docs" / "security" / "workflow-trust-and-mutations.md"
    ).read_text(encoding="utf-8")
    rust_lint = workflow.split("\n  rust-lint:", 1)[1].split("\n  rust-deny:", 1)[0]
    rust_deny = workflow.split("\n  rust-deny:", 1)[1].split("\n  rust-full:", 1)[0]
    rust_full_job = workflow.split("\n  rust-full:", 1)[1].split(
        "\n  rust-partial:", 1
    )[0]
    policy_candidate_stage = rust_full_job.split(
        "Stage and verify Rust policy cache candidate", 1
    )[1].split("Upload Rust policy cache candidate", 1)[0]
    rust_coverage_job = workflow.split("\n  rust-coverage:", 1)[1].split(
        "\n  rust-coverage-benchmark:", 1
    )[0]
    rust_coverage_benchmark = workflow.split("\n  rust-coverage-benchmark:", 1)[1].split(
        "\n  rust-phase-overlap-benchmark:", 1
    )[0]
    rust_phase_overlap_benchmark = workflow.split(
        "\n  rust-phase-overlap-benchmark:", 1
    )[1].split(
        "\n  rust-coverage-target-cache-benchmark:", 1
    )[0]
    rust_target_cache_benchmark = workflow.split(
        "\n  rust-coverage-target-cache-benchmark:", 1
    )[1].split("\n  rust-gate:", 1)[0]
    rust_coverage = (
        repo_root / ".github" / "actions" / "rust-coverage" / "action.yaml"
    ).read_text(encoding="utf-8")
    python_pyproject = (repo_root / "python" / "pyproject.toml").read_text(encoding="utf-8")
    lifecycle_consumer = (
        repo_root / "python" / "tests" / "report" / "test_run_lifecycle_consumer.py"
    ).read_text(encoding="utf-8")
    rust_gate = workflow.split("\n  rust-gate:", 1)[1].split("\n  contains-pins:", 1)[0]
    python_tests = workflow.split("\n  python-tests:", 1)[1].split(
        "\n  python-rust-integration:", 1
    )[0]
    python_rust_integration = workflow.split("\n  python-rust-integration:", 1)[1].split(
        "\n  gitleaks:", 1
    )[0]
    cache_sha = "caa296126883cff596d87d8935842f9db880ef25"

    assert "concurrency:" in workflow
    assert "group: ${{ github.workflow }}-${{ github.event_name == 'pull_request'" in workflow
    assert "format('pr-{0}', github.event.pull_request.number)" in workflow
    assert "format('ref-{0}', github.ref)" in workflow
    assert "cancel-in-progress: ${{ github.event_name == 'pull_request' }}" in workflow

    for env_value in (
        'CARGO_INCREMENTAL: "0"',
        'CARGO_PROFILE_DEV_DEBUG: "0"',
        'CARGO_PROFILE_TEST_DEBUG: "0"',
    ):
        assert env_value in rust_lint
    assert "uses: ./.github/actions/main-cache-keys" in rust_lint
    assert "key: ${{ steps.main-cache-keys.outputs.cargo-inputs }}" in rust_lint
    assert "key: ${{ env.CARGO_INPUTS_CACHE_KEY }}" in rust_coverage

    lint_target_cache = rust_lint.split("Restore Rust lint dependencies", 1)[1].split(
        "Check Rust formatting", 1
    )[0]
    assert "path: target/debug" in lint_target_cache
    assert "restore-keys:" not in lint_target_cache
    assert "crates/**/*.rs" not in rust_lint
    assert "cargo clean --workspace" in rust_lint
    assert "actions/cache/restore@" + cache_sha in rust_lint
    assert "actions/cache/save@" + cache_sha not in rust_lint
    assert "Stage Rust lint dependency cache candidate" in rust_lint
    assert "main-cache-rust-lint-deps-candidate" in rust_lint

    lint_input_cache = rust_lint.split("Restore Cargo inputs", 1)[1].split(
        "Restore Rust lint dependencies", 1
    )[0]
    coverage_input_cache = rust_coverage.split("Restore Cargo inputs", 1)[1].split(
        "Restore coverage dependencies", 1
    )[0]
    coverage_target_restore = rust_coverage.split("Restore coverage dependencies", 1)[1].split(
        "Record Rust coverage cache restore timing", 1
    )[0]
    coverage_target_restore_diagnostics = rust_coverage.split(
        "Record coverage dependency cache restore diagnostics", 1
    )[1].split("Start Rust coverage tool setup timing", 1)[0]
    cache_restore_timing = rust_coverage.split(
        "Record Rust coverage cache restore timing", 1
    )[1].split("Record coverage dependency cache restore diagnostics", 1)[0]
    coverage_target_prune = rust_coverage.split(
        "Prune coverage workspace products before target cache save", 1
    )[1].split("Record coverage dependency cache prune diagnostics", 1)[0]
    coverage_target_prune_diagnostics = rust_coverage.split(
        "Record coverage dependency cache prune diagnostics", 1
    )[1].split("Upload coverage target cache inventory", 1)[0]
    coverage_target_save = rust_coverage.split("Save coverage dependencies", 1)[1].split(
        "Record coverage dependency cache save diagnostics", 1
    )[0]
    for input_cache in (
        lint_input_cache,
        coverage_input_cache,
    ):
        assert "path: target" not in input_cache
        assert "actions/cache/restore@" + cache_sha in input_cache
        assert "actions/cache@" + cache_sha not in input_cache

    assert (
        "COVERAGE_TARGET_CACHE_ENABLED: ${{ github.event_name == 'workflow_dispatch' && "
        "inputs.coverage_target_cache_benchmark && 'false' || 'true' }}"
        in rust_full_job
    )
    assert 'COVERAGE_TARGET_CACHE_ENABLED: "false"' not in rust_full_job
    named_full_steps = {
        match.group("name"): match.group("body")
        for match in re.finditer(
            r"(?ms)^      - name: (?P<name>[^\n]+)\n(?P<body>.*?)(?=^      - name:|\Z)",
            rust_full_job.split("\n    steps:\n", 1)[1],
        )
    }
    event_varying_steps = {
        name
        for name, body in named_full_steps.items()
        if "github.event_name" in body or "github.ref" in body
    }
    assert event_varying_steps == {
        "Look up trusted main Rust policy cache key",
        "Stage and verify Rust policy cache candidate",
        "Upload Rust policy cache candidate",
    }
    for step_name in event_varying_steps:
        assert "main-cache" in named_full_steps[step_name] or "actions/cache/" in named_full_steps[step_name]
    named_coverage_steps = {
        match.group("name"): match.group("body")
        for match in re.finditer(
            r"(?ms)^    - name: (?P<name>[^\n]+)\n(?P<body>.*?)(?=^    - name:|\Z)",
            rust_coverage,
        )
    }
    for coverage_step in named_coverage_steps.values():
        if "run: |" in coverage_step:
            assert "github.event_name == 'push'" not in coverage_step
    for coverage_job in (rust_full_job, rust_coverage_benchmark):
        assert 'COVERAGE_TARGET_CACHE_SCHEMA: "v2"' in coverage_job
        assert 'COVERAGE_TARGET_CACHE_KEY_PREFIX: "coverage-target-deps"' in coverage_job
        assert 'COVERAGE_TARGET_CACHE_PUBLICATION: "main-cache-candidate"' in coverage_job
        assert 'RUST_COVERAGE_TARGET_TRIPLE: "x86_64-unknown-linux-gnu"' in coverage_job
        assert 'RUST_COVERAGE_FEATURE_MODE: "all-features"' in coverage_job
        assert 'RUST_COVERAGE_LINKER: "runner-default"' in coverage_job
    assert 'COVERAGE_TARGET_CACHE_SCHEMA: "v1"' not in workflow
    assert 'COVERAGE_TARGET_CACHE_MAX_BYTES: "1400000000"' in rust_full_job
    assert 'COVERAGE_TARGET_CACHE_ENABLED: "false"' in rust_coverage_benchmark
    assert 'COVERAGE_TARGET_CACHE_MAX_BYTES: "0"' in rust_coverage_benchmark
    assert "path: target/llvm-cov-target" in coverage_target_restore
    assert "key: ${{ env.COVERAGE_TARGET_CACHE_KEY }}" in coverage_target_restore
    assert "actions/cache/restore@" + cache_sha in coverage_target_restore
    assert "restore-keys:" not in coverage_target_restore
    assert "~/.cargo" not in coverage_target_restore
    assert "cargo-nextest" not in coverage_target_restore
    assert "cargo-llvm-cov" not in coverage_target_restore
    assert "if: env.COVERAGE_TARGET_CACHE_ENABLED == 'true'" in coverage_target_restore
    cargo_inputs_candidate = rust_lint.split("Stage Cargo inputs cache candidate", 1)[1].split(
        "Upload Cargo inputs cache candidate", 1
    )[0]
    assert 'mkdir -p "$HOME/.cargo/git"' in cargo_inputs_candidate
    assert '--source "git=$HOME/.cargo/git"' in cargo_inputs_candidate
    assert 'cargo clean --workspace --target-dir "$coverage_target_dir"' in coverage_target_prune
    for run_specific_output in (
        "*.profraw",
        "*-profraw-list",
        "*.profdata",
        "*.lcov",
        "lcov.info",
        "rust-coverage-phases.tsv",
        "cargo metadata --no-deps --format-version 1",
        'index("custom-build")',
        "! -name '*.d'",
        "coverage target cache retained workspace product",
        "COVERAGE_TARGET_CACHE_MAX_BYTES",
        "COVERAGE_TARGET_CACHE_MAX_BYTES_CAP",
        "main-dispatch-benchmark",
        "unmeasured-size-bound",
        "COVERAGE_TARGET_CACHE_SAVE_ALLOWED",
    ):
        assert run_specific_output in coverage_target_prune
    assert "actions/cache/save@" + cache_sha in coverage_target_save
    assert "path: target/llvm-cov-target" in coverage_target_save
    assert "env.COVERAGE_TARGET_CACHE_PUBLICATION == 'main-dispatch-benchmark'" in coverage_target_save
    assert "github.event_name == 'workflow_dispatch' && github.ref == 'refs/heads/main'" in coverage_target_save
    assert "steps.coverage-target-cache.outputs.cache-hit != 'true'" in coverage_target_save
    assert "steps.coverage-target-cache-prune.outcome == 'success'" in coverage_target_save
    assert "env.COVERAGE_TARGET_CACHE_SAVE_ALLOWED == 'true'" in coverage_target_save
    assert "skipped)" in coverage_target_prune_diagnostics
    assert (
        'prior_failure_or_cancelled="${COVERAGE_PRIOR_FAILURE_OR_CANCELLATION:?}"'
        in coverage_target_prune_diagnostics
    )
    assert '"$prior_failure_or_cancelled" = true' in coverage_target_prune_diagnostics
    assert "if: failure() && !cancelled()" in rust_coverage
    assert "if: cancelled()" in rust_coverage
    assert "coverage-target-cache-restore" in rust_coverage
    assert "coverage-target-cache-prune" in rust_coverage
    assert "coverage-target-cache-save" in rust_coverage
    assert "Start Rust coverage job timing" in rust_full_job
    assert "Start Rust coverage job timing" in rust_coverage_benchmark
    assert "job-total-after-runner-setup" in rust_coverage
    assert (
        'coverage_target_dir="$GITHUB_WORKSPACE/target/llvm-cov-target"'
        in coverage_target_restore_diagnostics
    )
    assert "coverage target cache hit restored no directory" in coverage_target_restore_diagnostics
    assert 'du -sk "$coverage_target_dir"' in coverage_target_restore_diagnostics
    assert 'restored_bytes="$((restored_kib * 1024))"' in coverage_target_restore_diagnostics
    assert "restored_bytes=0" in coverage_target_restore_diagnostics
    assert "skipped)" in coverage_target_restore_diagnostics
    assert (
        'prior_failure_or_cancelled="${COVERAGE_PRIOR_FAILURE_OR_CANCELLATION:?}"'
        in coverage_target_restore_diagnostics
    )
    assert '"$prior_failure_or_cancelled" = true' in coverage_target_restore_diagnostics
    assert "*skipped*) outcome=skipped" in cache_restore_timing
    assert "rust-coverage-target-cache-inventory" in rust_coverage
    assert rust_coverage.index("Upload Rust coverage report") < rust_coverage.index(
        "Prune coverage workspace products before target cache save"
    )
    assert rust_coverage.index(
        "Upload coverage-built Rust executable for cross-language integration tests"
    ) < rust_coverage.index("Prune coverage workspace products before target cache save")
    assert rust_coverage.index("Run plugin validations with coverage executable") < rust_coverage.index(
        "Prune coverage workspace products before target cache save"
    )
    assert rust_coverage.index("Prune coverage workspace products before target cache save") < rust_coverage.index(
        "Save coverage dependencies"
    )

    assert "Stage Cargo inputs cache candidate" in rust_lint
    assert "main-cache-cargo-inputs-candidate" in rust_lint
    assert "Stage Cargo inputs cache candidate" not in rust_coverage
    for candidate_name in (
        "Stage cargo-nextest cache candidate",
        "Stage cargo-llvm-cov cache candidate",
        "Stage pruned coverage dependency cache candidate",
    ):
        assert candidate_name in rust_coverage

    assert "EmbarkStudios/cargo-deny-action@b66acf5e9fe20f8aba065be86778a8a4c846f902" in rust_deny
    assert "actions/checkout@8e8c483db84b4bee98b60c0593521ed34d9990e8 # v6.0.1" in rust_deny
    assert "arguments: --locked --all-features" in rust_deny
    assert "path: ~/.cargo/bin/cargo-nextest" in rust_coverage
    assert "path: ~/.cargo/bin/cargo-llvm-cov" in rust_coverage
    assert "key: ${{ env.CARGO_NEXTEST_CACHE_KEY }}" in rust_coverage
    assert "key: ${{ env.CARGO_LLVM_COV_CACHE_KEY }}" in rust_coverage
    for checksum in (
        "38fd6275e111b200bbbed1bd2ae91cbb0d7edd28504879875cff2b3d96f3f311",
        "9c05bd3c7c5da1286b193873f12b37db386485fa483d8fa0554e68a53d9df550",
        "9a75fe29538d3800b3da57f6f6efb64cba5c720a257bf0cb8b51f39d495a9168",
        "8bff2fb8e14655f92d50afe7873945c6e46981505f3f3469683bf11da1ff8042",
    ):
        assert checksum in rust_full_job
        assert checksum in rust_coverage_benchmark
    assert "--retry 5 --retry-max-time 120 --retry-all-errors --connect-timeout 10 --max-time 120" in rust_coverage
    assert 'test "$(tar -tzf "$nextest_archive")" = "cargo-nextest"' in rust_coverage
    assert 'test "$(tar -tzf "$llvm_cov_archive")" = "cargo-llvm-cov"' in rust_coverage
    assert "sha256sum --check --strict" in rust_coverage
    assert "cargo install" not in rust_coverage
    assert "cargo nextest --version" in rust_coverage
    assert "cargo llvm-cov --version" in rust_coverage
    assert "coverage_profile_benchmark:" in workflow
    assert "coverage_profile_runner:" in workflow
    assert "coverage_target_cache_benchmark:" in workflow
    assert "coverage_target_cache_benchmark_max_bytes:" in workflow
    assert "large_ubuntu_4cpu" in workflow
    assert "CARGO_PROFILE_TEST_OPT_LEVEL: ${{ matrix.test_opt_level }}" in rust_coverage_benchmark
    assert 'CARGO_PROFILE_TEST_OPT_LEVEL: "0"' in rust_full_job
    assert 'COVERAGE_LCOV_ARTIFACT_SUFFIX: ""' in rust_full_job
    assert 'COVERAGE_TIMING_ARTIFACT_SUFFIX: "-opt0-sample1"' in rust_full_job
    assert 'COVERAGE_PYTHON_ARTIFACT_NAME: "larch-linux-test-binary"' in rust_full_job
    assert rust_coverage_benchmark.count(
        "COVERAGE_LCOV_ARTIFACT_SUFFIX: ${{ format('-opt{0}-sample{1}', matrix.test_opt_level, matrix.sample) }}"
    ) == 1
    assert rust_coverage_benchmark.count(
        "COVERAGE_TIMING_ARTIFACT_SUFFIX: ${{ format('-opt{0}-sample{1}', matrix.test_opt_level, matrix.sample) }}"
    ) == 1
    assert 'NEXTEST_TEST_THREADS: "16"' in rust_full_job
    assert 'NEXTEST_TEST_THREADS: "16"' in rust_coverage_benchmark
    assert "RUST_COVERAGE_PHASE_MODE: sequential" in rust_full_job
    assert "RUST_COVERAGE_PHASE_MODE: sequential" in rust_coverage_benchmark
    assert "NEXTEST_TEST_THREADS=16" in rust_testing
    assert "Post-policy nextest-tail candidate evidence" in rust_testing
    assert "if: github.event_name == 'workflow_dispatch' && inputs.coverage_profile_benchmark" in rust_coverage_benchmark
    assert 'test_opt_level: ["0", "1"]' in rust_coverage_benchmark
    assert "sample: [1, 2, 3]" in rust_coverage_benchmark
    assert 'CARGO_INCREMENTAL: "0"' in rust_full_job
    assert 'CARGO_PROFILE_TEST_DEBUG: "0"' in rust_full_job
    assert "timeout-minutes: 15" in rust_full_job
    assert "timeout-minutes: 60" in rust_coverage_benchmark
    assert "strategy:" not in rust_full_job
    assert "needs: [rust-selection]" in rust_full_job
    assert "uses: ./.github/actions/rust-coverage" in rust_full_job
    assert "uses: ./.github/actions/rust-coverage" in rust_coverage_benchmark
    assert "Run plugin validations with coverage executable" in rust_coverage
    plugin_validation = rust_coverage.split("Run plugin validations with coverage executable", 1)[1].split(
        "Upload Rust coverage report", 1
    )[0]
    assert '"$GITHUB_WORKSPACE/scripts/larch.sh" "$@"' in plugin_validation
    assert "plugin_larch release plugin-runtime --check --check-worktree" in plugin_validation
    assert "rust_phase_overlap_benchmark:" in workflow
    assert "github.event_name == 'workflow_dispatch' && inputs.rust_phase_overlap_benchmark" in rust_phase_overlap_benchmark
    assert "runs-on: ubuntu-24.04" in rust_phase_overlap_benchmark
    assert "phase_mode: [sequential, parallel]" in rust_phase_overlap_benchmark
    assert "sample: [1, 2, 3]" in rust_phase_overlap_benchmark
    assert 'NEXTEST_TEST_THREADS: "16"' in rust_phase_overlap_benchmark
    assert "RUST_COVERAGE_PHASE_MODE: ${{ matrix.phase_mode }}" in rust_phase_overlap_benchmark
    assert 'COVERAGE_PROFILE_BENCHMARK: "false"' in rust_phase_overlap_benchmark
    assert 'COVERAGE_TARGET_CACHE_ENABLED: "true"' in rust_phase_overlap_benchmark
    assert 'COVERAGE_PRODUCES_PYTHON_ARTIFACT: "true"' in rust_phase_overlap_benchmark
    assert (
        "github.event_name == 'workflow_dispatch' && inputs.coverage_target_cache_benchmark"
        " && github.ref == 'refs/heads/main'"
    ) in rust_target_cache_benchmark
    assert "name: rust-coverage-target-cache-benchmark" in rust_target_cache_benchmark
    assert "runs-on: ubuntu-24.04" in rust_target_cache_benchmark
    assert 'COVERAGE_TARGET_CACHE_ENABLED: "true"' in rust_target_cache_benchmark
    assert 'COVERAGE_TARGET_CACHE_KEY_PREFIX: "coverage-target-deps-benchmark"' in rust_target_cache_benchmark
    assert 'COVERAGE_TARGET_CACHE_PUBLICATION: "main-dispatch-benchmark"' in rust_target_cache_benchmark
    assert "COVERAGE_TARGET_CACHE_MAX_BYTES: ${{ inputs.coverage_target_cache_benchmark_max_bytes }}" in rust_target_cache_benchmark
    assert 'COVERAGE_TARGET_CACHE_MAX_BYTES_CAP: "2147483648"' in rust_target_cache_benchmark
    assert "Validate coverage target cache benchmark bound" in rust_target_cache_benchmark
    assert "coverage target cache benchmark bound exceeds cap" in rust_target_cache_benchmark
    assert 'COVERAGE_LCOV_ARTIFACT_SUFFIX: "-target-cache-benchmark"' in rust_target_cache_benchmark
    assert 'COVERAGE_TIMING_ARTIFACT_SUFFIX: "-target-cache-benchmark"' in rust_target_cache_benchmark
    assert 'COVERAGE_PRODUCES_PYTHON_ARTIFACT: "true"' in rust_target_cache_benchmark
    assert 'COVERAGE_PYTHON_ARTIFACT_NAME: "larch-linux-test-binary-target-cache-benchmark"' in rust_target_cache_benchmark
    assert "uses: ./.github/actions/rust-coverage" in rust_target_cache_benchmark
    assert "git diff --exit-code -- plugin" not in rust_target_cache_benchmark
    assert "cargo llvm-cov show-env --sh" in rust_coverage
    assert "cargo nextest run --workspace --all-features --locked \\" in rust_coverage
    assert '--target-dir "$coverage_target_dir" --no-run' in rust_coverage
    coverage_compilation = rust_coverage.split("compile_coverage() (", 1)[1].split(
        "run_timed compilation compile_coverage", 1
    )[0]
    assert 'test -x "$coverage_target_dir/debug/larch"' in coverage_compilation
    assert "cargo build" not in coverage_compilation
    assert "cargo llvm-cov nextest --no-report \\" in rust_coverage
    assert 'thread_counts="4 6 8 10 12 14 16"' in rust_coverage
    assert "cargo llvm-cov clean --profraw-only" in rust_coverage
    assert "run_timed doctests run_doctests" in rust_coverage
    assert "cargo test --doc --workspace --all-features --locked \\" in rust_coverage
    assert '--target-dir "$coverage_target_dir"' in rust_coverage
    assert "--status-level slow --final-status-level slow" in rust_coverage
    assert '--fail-under-lines "${RUST_COVERAGE_MIN_LINES}"' in rust_coverage
    assert "rust-coverage-timings${{ env.COVERAGE_TIMING_ARTIFACT_SUFFIX }}" in rust_coverage
    assert "## Rust coverage phase timings" in rust_coverage
    assert "phase\\tseconds\\toutcome\\tdetail" in rust_coverage
    for timing_phase in (
        "cache-restore",
        "tool-setup",
        "profile-cleanup",
        "compilation",
        "test-execution",
        "doctests",
        "coverage-report",
        "end-to-end-total-",
        "repository-policy",
        "plugin-validation",
        "cache-save",
    ):
        assert timing_phase in rust_coverage
    assert "validation-read-only" in rust_coverage
    assert "workflow_dispatch-main-benchmark-hit" in rust_coverage
    assert 'case "${RUST_COVERAGE_PHASE_MODE:?}" in' in rust_coverage
    assert "require_process_scoped_profile()" in rust_coverage
    assert "*%p*" in rust_coverage
    assert "start_timed_background()" in rust_coverage
    assert "wait_for_timed_background()" in rust_coverage
    assert "record_timed_background()" in rust_coverage
    waited_background = rust_coverage.split("wait_for_timed_background() {", 1)[1].split(
        "record_timed_background()", 1
    )[0]
    assert "cat " not in waited_background
    assert "test -s" not in waited_background
    recorded_background = rust_coverage.split("record_timed_background() {", 1)[1].split(
        'profile_started="$(date +%s)"', 1
    )[0]
    assert "BACKGROUND_PHASE_COLLECTION_STATUS" in recorded_background
    assert "return 0" in recorded_background
    parallel_phases = rust_coverage.split("run_parallel_coverage_phases() {", 1)[1].split(
        'thread_counts="$NEXTEST_TEST_THREADS"', 1
    )[0]
    assert 'wait_for_timed_background "$nextest_pid"' in parallel_phases
    assert 'wait_for_timed_background "$policy_pid"' in parallel_phases
    assert 'record_timed_background "test-execution-${test_threads}"' in parallel_phases
    assert 'record_timed_background "repository-policy-${test_threads}"' in parallel_phases
    assert "parallel Rust coverage phase failed" in parallel_phases
    assert parallel_phases.index('wait_for_timed_background "$nextest_pid"') < parallel_phases.index(
        'wait_for_timed_background "$policy_pid"'
    )
    assert parallel_phases.index('wait_for_timed_background "$policy_pid"') < parallel_phases.index(
        'record_timed_background "test-execution-${test_threads}"'
    )
    assert parallel_phases.index('record_timed_background "repository-policy-${test_threads}"') < parallel_phases.index(
        "parallel Rust coverage phase failed"
    )
    assert "nextest-collection=%s policy-collection=%s" in parallel_phases
    phase_mode_switch = rust_coverage.split('case "$RUST_COVERAGE_PHASE_MODE" in', 1)[1].split(
        'if run_timed "coverage-report-${test_threads}"', 1
    )[0]
    assert 'run_parallel_coverage_phases "$test_threads"' in phase_mode_switch
    assert 'run_timed "coverage-report-${test_threads}"' not in phase_mode_switch
    coverage_binary = "target/llvm-cov-target/debug/larch"
    assert f'coverage_larch="$GITHUB_WORKSPACE/{coverage_binary}"' in rust_coverage
    assert 'test -x "$coverage_larch"' in rust_coverage
    assert "plugin_larch() {" in rust_coverage
    assert "plugin_larch --version" in rust_coverage
    assert '"$coverage_larch" lint all' in rust_coverage
    assert rust_coverage.count('"$coverage_larch" lint all') == 1
    assert "plugin_larch release plugin-runtime" in rust_coverage
    assert "plugin_larch release plugin-runtime --check" in rust_coverage
    for coverage_job in (
        rust_full_job,
        rust_coverage_benchmark,
        rust_phase_overlap_benchmark,
        rust_target_cache_benchmark,
    ):
        assert "uses: ./.github/actions/rust-coverage" in coverage_job
        assert "git diff --exit-code -- plugin" not in coverage_job
        assert "git ls-files --others --exclude-standard -- plugin" not in coverage_job
    repository_policy = rust_coverage.split("run_repository_policy() (", 1)[1].split(
        'thread_counts="$NEXTEST_TEST_THREADS"', 1
    )[0]
    assert 'CARGO_TARGET_DIR="$coverage_target_dir" cargo llvm-cov show-env --sh' in repository_policy
    assert '"$coverage_larch" lint all \\' in repository_policy
    assert "rust-repository-policy-rules-${test_threads}.tsv" in repository_policy
    plugin_validation = rust_coverage.split(
        "Run plugin validations with coverage executable", 1
    )[1].split("Upload Rust coverage report", 1)[0]
    validation_profile = (
        "LLVM_PROFILE_FILE: ${{ runner.temp }}/"
        "larch-coverage-validation-%p.profraw"
    )
    assert validation_profile in plugin_validation
    assert plugin_validation.index(validation_profile) < plugin_validation.index("run: |")
    coverage_binary_artifact = rust_coverage.split(
        "Upload coverage-built Rust executable for cross-language integration tests", 1
    )[1].split("Start Rust coverage cache save timing", 1)[0]
    assert "Prepare coverage-built Rust integration artifact" in rust_coverage
    assert "name: ${{ env.COVERAGE_PYTHON_ARTIFACT_NAME }}" in coverage_binary_artifact
    assert "path: ${{ runner.temp }}/larch-linux-test-binary" in coverage_binary_artifact
    assert "if-no-files-found: error" in coverage_binary_artifact
    assert "env.COVERAGE_PRODUCES_PYTHON_ARTIFACT == 'true'" in coverage_binary_artifact
    prepared_artifact = rust_coverage.split(
        "Prepare coverage-built Rust integration artifact", 1
    )[1].split("Upload coverage-built Rust executable for cross-language integration tests", 1)[0]
    assert "ci prepare-rust-integration-artifact" in prepared_artifact
    assert f'--coverage-larch "$GITHUB_WORKSPACE/{coverage_binary}"' in prepared_artifact
    assert '--artifact-dir "$RUNNER_TEMP/larch-linux-test-binary"' in prepared_artifact
    assert '--source-sha "$GITHUB_SHA"' in prepared_artifact
    assert '--rust-inputs-sha256 "$RUST_POLICY_INPUTS_SHA256"' in prepared_artifact
    assert "sha256sum larch > larch.sha256" not in prepared_artifact
    assert "github.event_name" not in prepared_artifact
    assert "github.ref" not in prepared_artifact
    assert "github.event_name == 'merge_group'" in policy_candidate_stage
    assert "github.ref" not in policy_candidate_stage
    assert policy_candidate_stage.count("$GITHUB_EVENT_NAME") == 2
    assert policy_candidate_stage.count("$GITHUB_REF") == 2
    assert 'mkdir -p "$RUNNER_TEMP/main-cache-rust-policy"' in policy_candidate_stage
    assert policy_candidate_stage.index(
        'mkdir -p "$RUNNER_TEMP/main-cache-rust-policy"'
    ) < policy_candidate_stage.index("ci stage-rust-policy-candidate")
    for candidate_argument in (
        "ci stage-rust-policy-candidate",
        '--artifact-dir "$RUNNER_TEMP/larch-linux-test-binary"',
        '--policy-dir "$RUNNER_TEMP/main-cache-rust-policy/policy"',
        '--event-name "$GITHUB_EVENT_NAME"',
        '--ref "$GITHUB_REF"',
        '--source-sha "$GITHUB_SHA"',
        '--rust-inputs-sha256 "$RUST_POLICY_INPUTS_SHA256"',
    ):
        assert candidate_argument in policy_candidate_stage
    assert "ci stage-main-cache-candidate" in policy_candidate_stage
    assert "--cache-class rust-policy" in policy_candidate_stage
    assert '--source "policy=$RUNNER_TEMP/main-cache-rust-policy/policy"' in policy_candidate_stage
    assert "target/llvm-cov-target" not in policy_candidate_stage
    assert rust_coverage.index('run_timed "repository-policy-${test_threads}"') < rust_coverage.index(
        "coverage-report-${test_threads}"
    )
    assert rust_coverage.index("coverage-report-${test_threads}") < rust_coverage.index(
        "Run plugin validations with coverage executable"
    )
    assert rust_coverage.index("Run plugin validations with coverage executable") < rust_coverage.index(
        "Upload Rust coverage report"
    )
    assert "Upload Rust repository policy rule timings" in rust_coverage
    assert "rust-repository-policy-rule-timings${{ env.COVERAGE_TIMING_ARTIFACT_SUFFIX }}" in rust_coverage
    assert "## Rust repository policy rule timings" in rust_coverage
    assert "rust-repository-policy-rule-timings-*" in rust_testing
    assert "repository-policy scan" in rust_testing
    assert "rust_phase_overlap_benchmark=true" in rust_testing
    assert "three `sequential` control samples" in rust_testing
    assert "three `parallel` candidate samples" in rust_testing
    assert "process placeholder" in rust_testing
    assert "before `cargo llvm-cov report`" in rust_testing
    for cache_contract in (
        "restore-only cache action",
        "validation-read-only",
        "cannot publish Cargo\ninputs",
    ):
        assert cache_contract in rust_testing
    assert "rust-build-test" not in rust_testing
    assert "coverage-target executable" in rust_testing
    assert "workflow_dispatch" in supply_chain
    assert "cannot publish" in supply_chain
    assert "coverage compiler-dependency cache" in supply_chain_text
    assert "same exact keys" in supply_chain_text
    assert "successful `CI` merge-group run" in supply_chain_text
    assert "restore-keys" in supply_chain
    assert "successful `rust-full` merge-group run stages" in supply_chain
    assert "same checksum" in supply_chain
    assert "fixed `merge-group` label" in supply_chain
    assert "primary-key miss" in supply_chain
    assert "2 GiB" in supply_chain
    assert "coverage-target-deps-benchmark" in supply_chain
    assert "main-ref coverage-target benchmark" in supply_chain
    assert "repository quota pressure" in supply_chain
    assert "CI cache trust" in workflow_trust
    assert "compiler-output cache" in workflow_trust
    assert "manual target-cache benchmark" in workflow_trust
    assert "actions/cache/restore@" + cache_sha in rust_coverage
    assert "actions/cache/save@" + cache_sha in rust_coverage
    assert "id: cargo-inputs-cache" in rust_coverage
    assert "rust-coverage-lcov${{ env.COVERAGE_LCOV_ARTIFACT_SUFFIX }}" in rust_coverage
    assert rust_coverage.index("Upload Rust coverage report") < rust_coverage.index(
        "Upload coverage-built Rust executable for cross-language integration tests"
    )
    assert rust_coverage.index("Upload coverage-built Rust executable for cross-language integration tests") < rust_coverage.index(
        "Stage cargo-nextest cache candidate"
    )

    assert "needs: [rust-selection, rust-full, rust-partial, rust-skip]" in rust_coverage_job
    assert "if: always()" in rust_coverage_job
    assert "Require the selected Rust execution path to pass" in rust_coverage_job
    for execution_result in ("FULL_RESULT", "PARTIAL_RESULT", "SELECTION_RESULT", "SKIP_RESULT"):
        assert execution_result in rust_coverage_job

    assert "needs: [rust-lint, rust-deny, rust-coverage]" in rust_gate
    for result_name in ("lint_result", "deny_result", "coverage_result"):
        assert result_name in rust_gate
    assert "build_test_result" not in rust_gate
    assert "if: always()" in rust_gate

    assert "needs:" not in python_tests
    assert "needs: [rust-build-test]" not in python_tests
    assert "LARCH_TEST_RUST_BINARY" not in python_tests
    assert "larch-linux-test-binary" not in python_tests
    assert "PYTEST_ADDOPTS: '-m \"not rust_integration\"'" in python_tests
    assert "shard: [1, 2, 3, 4]" in python_tests
    python_test_execution = python_tests.split(
        "Run Python tests (shard ${{ matrix.shard }} of 4)", 1
    )[1]
    assert 'PYTEST_SHARD_COUNT: "4"' in python_test_execution
    assert "LLVM_PROFILE_FILE" not in python_test_execution

    assert "name: python-tests-gate" in python_rust_integration
    assert "needs: [rust-coverage, python-tests]" in python_rust_integration
    assert "if: always()" in python_rust_integration
    assert "unit_result" in python_rust_integration
    assert "coverage_result" in python_rust_integration
    assert "LARCH_TEST_RUST_BINARY: ${{ github.workspace }}/.ci-bin/larch" in python_rust_integration
    assert "RUST_CI_MODE: ${{ needs.rust-coverage.outputs.mode }}" in python_rust_integration
    assert "RUST_POLICY_INPUTS_SHA256" in python_rust_integration
    assert "name: larch-linux-test-binary" in python_rust_integration
    assert "path: .ci-bin" in python_rust_integration
    assert "Verify selected Rust integration artifact" in python_rust_integration
    assert "sha256sum --check --strict larch.sha256" in python_rust_integration
    assert "producer-ref" in python_rust_integration
    assert "rust-inputs-sha256" in python_rust_integration
    assert 'test "$source_sha" = "$GITHUB_SHA"' in python_rust_integration
    assert 'test "$RUST_CI_MODE" = skip' in python_rust_integration
    assert 'test "$actual_version" = "$expected_version"' in python_rust_integration
    assert "LARCH_TEST_RUST_BINARY_SHA256" in python_rust_integration
    integration_execution = python_rust_integration.split(
        "Run Rust-backed Python integration tests", 1
    )[1]
    assert "python3 -m pytest --durations=0 -m rust_integration" in integration_execution
    assert (
        "tests/report/test_run_lifecycle_consumer.py::test_consumer_reaches_rust_through_its_bootstrap"
        in integration_execution
    )
    assert "LLVM_PROFILE_FILE: ${{ runner.temp }}/larch-python-%p.profraw" in integration_execution

    assert "rust_integration: requires the coverage-built Rust larch executable" in python_pyproject
    assert "@pytest.mark.rust_integration\ndef test_consumer_reaches_rust_through_its_bootstrap" in lifecycle_consumer
    marker_paths = sorted(
        path.relative_to(repo_root).as_posix()
        for path in (repo_root / "python" / "tests").rglob("test_*.py")
        if re.search(
            r"^\s*@pytest\.mark\.rust_integration\s*$",
            path.read_text(encoding="utf-8"),
            re.MULTILINE,
        )
    )
    assert marker_paths == ["python/tests/report/test_run_lifecycle_consumer.py"]


def test_gitleaks_ci_uses_a_verified_scanner_and_typed_history_resolver() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    workflow = (repo_root / ".github" / "workflows" / "ci.yaml").read_text(
        encoding="utf-8"
    )
    gitleaks = workflow.split("\n  gitleaks:", 1)[1].split("\n  agent-sync:", 1)[0]
    bootstrap = (
        repo_root / ".github" / "actions" / "gitleaks-bootstrap" / "action.yaml"
    ).read_text(encoding="utf-8")
    publication = (
        repo_root / ".github" / "workflows" / "main-cache-publication.yaml"
    ).read_text(encoding="utf-8")
    publisher = publication.split("\n  main-cache-gitleaks:", 1)[1].split(
        "\n  main-cache-probe:", 1
    )[0]
    supply_chain = (
        repo_root / "docs" / "security" / "supply-chain-credentials-and-services.md"
    ).read_text(encoding="utf-8")
    artifacts = (
        repo_root / "docs" / "security" / "artifacts-redaction-and-publication.md"
    ).read_text(encoding="utf-8")
    workflow_trust = (
        repo_root / "docs" / "security" / "workflow-trust-and-mutations.md"
    ).read_text(encoding="utf-8")
    shipped_supply_chain = (
        repo_root
        / "plugin"
        / "docs"
        / "security"
        / "supply-chain-credentials-and-services.md"
    ).read_text(encoding="utf-8")
    shipped_artifacts = (
        repo_root
        / "plugin"
        / "docs"
        / "security"
        / "artifacts-redaction-and-publication.md"
    ).read_text(encoding="utf-8")
    shipped_workflow_trust = (
        repo_root
        / "plugin"
        / "docs"
        / "security"
        / "workflow-trust-and-mutations.md"
    ).read_text(encoding="utf-8")
    cache_sha = "caa296126883cff596d87d8935842f9db880ef25"
    archive_sha = "ba6dbb656933921c775ee5a2d1c13a91046e7952e9d919f9bac4cec61d628e7d"
    binary_sha = "46a05260e7cce527f132cb618de59d22262b8b5eb47f66c288447b95c7a98b7e"

    assert "runs-on: ubuntu-24.04" in gitleaks
    assert "id: gitleaks-checkout-start" in gitleaks
    assert "id: gitleaks-checkout-timing" in gitleaks
    assert 'checkout_started="${{ steps.gitleaks-checkout-start.outputs.epoch_seconds }}"' in gitleaks
    assert 'checkout_seconds="$(( $(date +%s) - checkout_started ))"' in gitleaks
    assert 'test "$checkout_seconds" -ge 0' in gitleaks
    assert "fetch-depth: 0" in gitleaks
    assert 'GITLEAKS_VERSION: "8.18.4"' in gitleaks
    assert archive_sha in gitleaks
    assert binary_sha in gitleaks
    assert "Build typed gitleaks history resolver" in gitleaks
    assert "id: gitleaks-rust-bootstrap" in gitleaks
    assert "cargo build --locked --package larch-cli --bin larch" in gitleaks
    assert "target/debug/larch" in gitleaks
    assert "LARCH_BINARY" in gitleaks
    assert "scripts/larch.sh" in gitleaks

    assert "id: gitleaks-cache" in gitleaks
    assert "actions/cache/restore@" + cache_sha in gitleaks
    assert "actions/cache/save@" + cache_sha not in gitleaks
    assert "actions/cache@v5" not in gitleaks
    assert "path: ~/.cache/larch/tools/gitleaks" in gitleaks
    assert "key: ${{ steps.main-cache-keys.outputs.gitleaks }}" in gitleaks
    main_cache_keys = (
        repo_root / ".github" / "actions" / "main-cache-keys" / "action.yaml"
    ).read_text(encoding="utf-8")
    assert "printf 'gitleaks=gitleaks-release-v2-%s-%s-%s-%s\\n'" in main_cache_keys
    assert '"$RUNNER_OS" "$RUNNER_ARCH" "$GITLEAKS_VERSION" "$GITLEAKS_BINARY_SHA256"' in main_cache_keys
    assert "uses: ./.github/actions/gitleaks-bootstrap" in gitleaks
    assert "actions/cache/save@" + cache_sha in publisher
    assert "gitleaks detect" not in publisher

    assert "if ! gitleaks_is_verified; then" in bootstrap
    assert "gitleaks_is_verified || {" in bootstrap
    assert '[ ! -d "$directory" ] || [ -L "$directory" ]' in bootstrap
    assert '[ ! -f "$gitleaks_binary" ] || [ -L "$gitleaks_binary" ]' in bootstrap
    assert "gitleaks cache entry is not a regular file" in bootstrap
    assert "verified gitleaks release failed post-install validation" in bootstrap
    assert (gitleaks + bootstrap).count("env -i") == 3
    assert "GIT_TERMINAL_PROMPT=0" in bootstrap
    assert "--proto '=https' --proto-redir '=https'" in bootstrap
    assert (
        "--retry 5 --retry-max-time 120 --retry-all-errors --connect-timeout 10 --max-time 120"
        in bootstrap
    )
    assert "--max-filesize 16777216" in bootstrap
    assert (
        "https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}"
        in bootstrap
    )
    assert bootstrap.count("sha256sum --check --strict --status -") >= 2
    assert (
        "expected_gitleaks_members=\"$(printf '%s\\n' LICENSE README.md gitleaks)\""
        in bootstrap
    )
    assert (
        'actual_gitleaks_members="$(tar -tzf "$gitleaks_archive" | LC_ALL=C sort)"'
        in bootstrap
    )
    assert 'test "$actual_gitleaks_members" = "$expected_gitleaks_members"' in bootstrap
    assert 'tar -xzf "$gitleaks_archive" -C "$temporary" -- gitleaks' in bootstrap
    assert 'install -m 0755 "${temporary}/gitleaks" "$gitleaks_binary"' in bootstrap
    assert 'test "$(run_gitleaks version)" = "$GITLEAKS_VERSION"' in bootstrap

    working_tree = gitleaks.split("- name: Scan working tree", 1)[1].split(
        "- name: Scan git history", 1
    )[0]
    history = gitleaks.split("- name: Scan git history", 1)[1].split(
        "- name: Record gitleaks phase timing metadata", 1
    )[0]
    assert (
        'detect --source . --config "$GITHUB_WORKSPACE/.gitleaks.toml" --redact --no-banner --no-git'
        in working_tree
    )
    assert "ci gitleaks-base" in history
    assert "BASE=$(git " not in history
    assert "git merge-base" not in history
    assert "git rev-parse" not in history
    assert (
        'detect --source . --config "$GITHUB_WORKSPACE/.gitleaks.toml" --redact --no-banner --log-opts "${BASE}..HEAD"'
        in history
    )
    assert "Record gitleaks phase timing metadata" in gitleaks
    for phase in (
        "checkout_seconds",
        "rust_bootstrap_seconds: ${{ steps.gitleaks-rust-bootstrap.outputs.seconds }}",
        "rust_bootstrap: typed larch history resolver",
        "verified_tool_preparation_seconds",
        "working_tree_scan_seconds",
        "history_scan_seconds",
    ):
        assert phase in gitleaks

    assert "typed Rust history resolver" in supply_chain
    assert "16 MiB archive-size cap" in supply_chain
    assert (
        "pull-request-provided executable cannot cross into the\ntrusted-main cache"
        in supply_chain
    )
    assert "workflow-local installer" in artifacts
    assert "CI installer rechecks the cache before each scan" in " ".join(
        artifacts.split()
    )
    assert "#ci-tool-bootstrap-and-caches" in workflow_trust
    assert "#ci-rust-tool-bootstrap-and-caches" not in workflow_trust
    assert shipped_supply_chain == supply_chain
    assert shipped_artifacts == artifacts
    assert shipped_workflow_trust == workflow_trust


def test_ci_bootstrap_consumers_restore_exact_trusted_rust_dependency_caches() -> None:
    """Keep the three bootstrap consumers read-only and profile-compatible."""
    repo_root = Path(__file__).resolve().parents[3]
    workflow = (repo_root / ".github" / "workflows" / "ci.yaml").read_text(
        encoding="utf-8"
    )
    makefile = (repo_root / "Makefile").read_text(encoding="utf-8")
    focus_area_rule = (
        repo_root / "crates" / "larch-lint" / "src" / "rules" / "focus_area_enum.rs"
    ).read_text(encoding="utf-8")
    supply_chain = (
        repo_root / "docs" / "security" / "supply-chain-credentials-and-services.md"
    ).read_text(encoding="utf-8")
    shipped_supply_chain = (
        repo_root
        / "plugin"
        / "docs"
        / "security"
        / "supply-chain-credentials-and-services.md"
    ).read_text(encoding="utf-8")
    gitleaks = workflow.split("\n  gitleaks:", 1)[1].split("\n  agent-sync:", 1)[0]
    agent_sync = workflow.split("\n  agent-sync:", 1)[1].split("\n  trufflehog:", 1)[0]
    test_harnesses = workflow.split("\n  test-harnesses:", 1)[1].split(
        "\n  test-harnesses-gate:", 1
    )[0]
    cache_sha = "caa296126883cff596d87d8935842f9db880ef25"

    for consumer in (gitleaks, agent_sync, test_harnesses):
        assert "actions/cache/restore@" + cache_sha in consumer
        assert "actions/cache/save@" + cache_sha not in consumer
        assert "restore-keys:" not in consumer
        assert "key: ${{ steps.main-cache-keys.outputs.cargo-inputs }}" in consumer
        assert "key: ${{ steps.main-cache-keys.outputs.rust-lint-deps }}" in consumer

    for consumer in (gitleaks, agent_sync):
        for profile_value in (
            'CARGO_INCREMENTAL: "0"',
            'CARGO_PROFILE_DEV_DEBUG: "0"',
            'CARGO_PROFILE_TEST_DEBUG: "0"',
        ):
            assert profile_value in consumer
        assert "cargo_inputs_cache_hit" in consumer
        assert "rust_lint_deps_cache_hit" in consumer
        assert "rust_bootstrap_seconds" in consumer

    assert gitleaks.index("Restore Cargo inputs for typed gitleaks history resolver") < gitleaks.index(
        "Build typed gitleaks history resolver"
    )
    assert gitleaks.index("Restore Rust lint dependencies for typed gitleaks history resolver") < gitleaks.index(
        "Build typed gitleaks history resolver"
    )

    assert "runs-on: ubuntu-24.04" in agent_sync
    assert "actions/setup-python" not in agent_sync
    assert "pip install" not in agent_sync
    assert "make agent-sync" in agent_sync
    assert "generate check" in makefile
    assert "lint rule topology-rule-paths" in makefile
    assert "lint rule focus-area-enum" in makefile
    for path in (
        "skills/shared/reviewer-templates.md",
        "agents/code-reviewer.md",
        "agents/reviewer-structure.md",
        "agents/reviewer-correctness.md",
        "agents/reviewer-testing.md",
        "agents/reviewer-security.md",
        "agents/reviewer-edge-cases.md",
        "agents/reviewer-plan-fidelity.md",
        "agents/reviewer-code-robustness.md",
        "docs/review-agents.md",
        "skills/review/SKILL.md",
        "python/larch/rendering/rendering.py",
        "skills/design/SKILL.md",
    ):
        assert f'"{path}",' in focus_area_rule
    assert 'Regex::new(r"`code-quality`.*`risk-integration`.*`correctness`.*`architecture`")' in focus_area_rule
    assert '"code-quality / risk-integration / correctness / architecture"' in focus_area_rule
    assert 'line.contains("security")' in focus_area_rule
    assert "no {style} focus-area enumeration found" in focus_area_rule

    assert "shard: [1, 2]" in test_harnesses
    assert "Run Rust hook harness (shard 1 of 2)" in test_harnesses
    rust_hook = test_harnesses.split("Run Rust hook harness", 1)[1].split(
        "Run test harnesses (shards other than 1)", 1
    )[0]
    assert "if: matrix.shard == 1" in test_harnesses
    assert "Restore Cargo inputs for Rust hook harness" in test_harnesses
    assert "Restore Rust lint dependencies for Rust hook harness" in test_harnesses
    assert "if: matrix.shard == 1" in rust_hook
    for profile_value in (
        'CARGO_INCREMENTAL: "0"',
        'CARGO_PROFILE_DEV_DEBUG: "0"',
        'CARGO_PROFILE_TEST_DEBUG: "0"',
    ):
        assert profile_value in rust_hook
    assert 'LARCH_BINARY: ""' in rust_hook
    assert "Record Rust hook harness cache timing metadata" in test_harnesses
    assert "rust_bootstrap_seconds" in test_harnesses

    assert "restore the exact\nCargo-input and lint-dependency classes read-only" in supply_chain
    assert "no\nrestore-key fallback or cache save step" in supply_chain
    assert shipped_supply_chain == supply_chain


def _gitleaks_ci_preparation_script(repo_root: Path) -> str:
    bootstrap = (
        repo_root / ".github" / "actions" / "gitleaks-bootstrap" / "action.yaml"
    ).read_text(encoding="utf-8")
    preparation = bootstrap.split(
        "    - name: Prepare verified gitleaks release\n"
        "      id: prepare-gitleaks\n"
        "      shell: bash\n"
        "      run: |\n",
        1,
    )[1]
    return textwrap.dedent(preparation)


def _write_gitleaks_ci_mock(path: Path, body: str) -> None:
    path.write_text(f"#!/bin/bash\nset -euo pipefail\n{body}", encoding="utf-8")
    path.chmod(0o755)


def _write_gitleaks_ci_archive(path: Path, members: tuple[str, ...]) -> None:
    with tarfile.open(path, "w:gz") as archive:
        for name in members:
            if name == "gitleaks":
                contents = b"""#!/bin/bash
if [ -n "${GITHUB_TOKEN:-}" ]; then
  printf '%s\n' credential-leak >> "$HOME/gitleaks-invocations"
  exit 97
fi
printf '%s\n' "$*" >> "$HOME/gitleaks-invocations"
if [ "${1:-}" = version ]; then
  printf '%s\n' 8.18.4
fi
"""
                mode = 0o755
            else:
                contents = name.encode()
                mode = 0o644
            header = tarfile.TarInfo(name)
            header.size = len(contents)
            header.mode = mode
            archive.addfile(header, io.BytesIO(contents))


def _gitleaks_ci_mock_tools(mock_bin: Path) -> None:
    _write_gitleaks_ci_mock(
        mock_bin / "curl",
        """\
output=""
saw_max_filesize=false
while [ "$#" -gt 0 ]; do
  case "$1" in
    --max-filesize)
      test "${2:-}" = 16777216
      saw_max_filesize=true
      shift 2
      ;;
    --output)
      output="${2:?missing curl output path}"
      shift 2
      ;;
    *)
      shift
      ;;
  esac
done
test "$saw_max_filesize" = true
test -n "$output"
if [ "${TEST_CURL_FAILURE:-false}" = true ]; then
  exit 22
fi
cp "$TEST_ARCHIVE_SOURCE" "$output"
""",
    )
    _write_gitleaks_ci_mock(
        mock_bin / "sha256sum",
        """\
if [ "${1:-}" = --check ]; then
  check_count=0
  if [ -f "$TEST_SHA256_CHECK_COUNT" ]; then
    check_count="$(cat "$TEST_SHA256_CHECK_COUNT")"
  fi
  check_count="$((check_count + 1))"
  printf '%s\n' "$check_count" > "$TEST_SHA256_CHECK_COUNT"
  if [ "${TEST_SHA256_FAIL_AT:-0}" = "$check_count" ]; then
    exit 1
  fi
  exit 0
fi
path=""
for argument in "$@"; do
  path="$argument"
done
if [ "$(cat "$path")" = corrupt ]; then
  printf '%s  %s\n' unverified "$path"
else
  printf '%s  %s\n' "$GITLEAKS_BINARY_SHA256" "$path"
fi
""",
    )


def _run_gitleaks_ci_preparation(
    tmp_path: Path,
    *,
    archive_members: tuple[str, ...] = ("LICENSE", "README.md", "gitleaks"),
    checksum_failure_at: int | None = None,
    cache_kind: str = "cold",
) -> tuple[subprocess.CompletedProcess[str], Path, Path]:
    repo_root = Path(__file__).resolve().parents[3]
    tmp_path.mkdir(exist_ok=True)
    mock_bin = tmp_path / "mock-bin"
    mock_bin.mkdir()
    _gitleaks_ci_mock_tools(mock_bin)
    archive_source = tmp_path / "gitleaks.tar.gz"
    _write_gitleaks_ci_archive(archive_source, archive_members)
    home = tmp_path / "home"
    home.mkdir()
    temporary = tmp_path / "temporary"
    temporary.mkdir()
    cache_binary = (
        home
        / ".cache"
        / "larch"
        / "tools"
        / "gitleaks"
        / "8.18.4"
        / "linux-x64"
        / "gitleaks"
    )
    if cache_kind == "corrupt":
        cache_binary.parent.mkdir(parents=True)
        cache_binary.write_text("corrupt", encoding="utf-8")
    elif cache_kind == "symlink":
        cache_binary.parent.mkdir(parents=True)
        cache_target = tmp_path / "untrusted-gitleaks"
        cache_target.write_text("corrupt", encoding="utf-8")
        cache_binary.symlink_to(cache_target)
    elif cache_kind != "cold":
        raise AssertionError(f"unknown cache fixture kind: {cache_kind}")
    github_output = tmp_path / "github-output"
    check_count = tmp_path / "sha256-check-count"
    environment = os.environ.copy()
    environment.update(
        {
            "HOME": str(home),
            "TMPDIR": str(temporary),
            "PATH": f"{mock_bin}{os.pathsep}{environment['PATH']}",
            "LANG": "C.UTF-8",
            "GITHUB_OUTPUT": str(github_output),
            "GITHUB_TOKEN": "must-not-reach-gitleaks",
            "GITLEAKS_VERSION": "8.18.4",
            "GITLEAKS_ARCHIVE_SHA256": "archive-sha256",
            "GITLEAKS_BINARY_SHA256": "binary-sha256",
            "TEST_ARCHIVE_SOURCE": str(archive_source),
            "TEST_SHA256_CHECK_COUNT": str(check_count),
        }
    )
    if checksum_failure_at is not None:
        environment["TEST_SHA256_FAIL_AT"] = str(checksum_failure_at)
    result = subprocess.run(
        ["bash", "-c", _gitleaks_ci_preparation_script(repo_root)],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    return result, home, github_output


def test_gitleaks_ci_preparation_executes_a_hermetic_cold_miss_and_recovers_corrupt_cache(
    tmp_path: Path,
) -> None:
    for cache_kind in ("cold", "corrupt"):
        result, home, github_output = _run_gitleaks_ci_preparation(
            tmp_path / cache_kind,
            cache_kind=cache_kind,
        )
        assert result.returncode == 0, result.stderr
        binary = (
            home
            / ".cache"
            / "larch"
            / "tools"
            / "gitleaks"
            / "8.18.4"
            / "linux-x64"
            / "gitleaks"
        )
        assert binary.is_file()
        assert not binary.is_symlink()
        assert (
            home / "gitleaks-invocations"
        ).read_text(encoding="utf-8") == "version\n"
        assert "seconds=" in github_output.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("archive_members", "checksum_failure_at", "cache_kind"),
    [
        (("LICENSE", "README.md", "unexpected"), None, "cold"),
        (("LICENSE", "README.md", "gitleaks"), 1, "cold"),
        (("LICENSE", "README.md", "gitleaks"), 2, "cold"),
        (("LICENSE", "README.md", "gitleaks"), None, "symlink"),
    ],
)
def test_gitleaks_ci_preparation_rejects_invalid_material_before_execution(
    tmp_path: Path,
    archive_members: tuple[str, ...],
    checksum_failure_at: int | None,
    cache_kind: str,
) -> None:
    result, home, github_output = _run_gitleaks_ci_preparation(
        tmp_path,
        archive_members=archive_members,
        checksum_failure_at=checksum_failure_at,
        cache_kind=cache_kind,
    )
    assert result.returncode != 0
    assert not (home / "gitleaks-invocations").exists()
    assert not github_output.exists()


def test_rust_ci_documentation_matches_producer_topology() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    workflow = (repo_root / ".github" / "workflows" / "ci.yaml").read_text(encoding="utf-8")
    rust_testing = (repo_root / "docs" / "rust-testing.md").read_text(encoding="utf-8")
    shipped_rust_testing = (repo_root / "plugin" / "docs" / "rust-testing.md").read_text(
        encoding="utf-8"
    )
    coverage_and_ci = rust_testing.split("## Coverage and CI", 1)[1].split(
        "### Pull-request Rust selection", 1
    )[0]
    production_evidence = rust_testing.split("### Production main-run evidence", 1)[1].split(
        "### Post-policy nextest-tail candidate evidence", 1
    )[0]
    coverage_text = " ".join(coverage_and_ci.split())
    production_evidence_text = " ".join(production_evidence.split())
    rust_testing_text = " ".join(rust_testing.split())
    rust_full = workflow.split("\n  rust-full:", 1)[1].split("\n  rust-partial:", 1)[0]
    rust_partial = workflow.split("\n  rust-partial:", 1)[1].split("\n  rust-skip:", 1)[0]
    rust_skip = workflow.split("\n  rust-skip:", 1)[1].split("\n  rust-coverage:", 1)[0]
    rust_coverage = workflow.split("\n  rust-coverage:", 1)[1].split(
        "\n  rust-coverage-benchmark:", 1
    )[0]
    python_tests = workflow.split("\n  python-tests:", 1)[1].split(
        "\n  python-rust-integration:", 1
    )[0]
    python_rust_integration = workflow.split("\n  python-rust-integration:", 1)[1].split(
        "\n  gitleaks:", 1
    )[0]

    assert shipped_rust_testing == rust_testing
    assert (
        "`rust-full`, `rust-partial`, and `rust-skip` are mutually exclusive execution producers."
        in coverage_text
    )
    assert "`rust-coverage` is not an execution lane: it is the stable required aggregate." in coverage_text
    assert "it validates the selected mode and every producer result" in coverage_text
    assert (
        "Manual dispatches and merge-queue runs use `rust-full`; a normal `main` push runs only "
        "trusted cache publication."
        in coverage_text
    )
    assert "`rust-partial` and `rust-skip` may be the selected producer only for pull requests." in coverage_text
    assert "The 4-shard `python-tests` matrix is artifact-independent" in coverage_text
    assert "consumes the selected producer's verified `larch-linux-test-binary`" in coverage_text
    assert "selection cannot prove a narrower path" in coverage_text
    assert "An unavailable selector defaults to `full`" in rust_testing_text
    assert "cache miss or any validation failure selects `full`" in rust_testing_text
    assert "full-rust-ci" in rust_testing_text
    assert "that label can only narrow toward the safer `full` mode" in rust_testing_text
    assert "`rust-coverage` is the direct production coverage lane." not in rust_testing
    assert "three comparable warm full-path successful `push` runs on `refs/heads/main`" in production_evidence_text
    assert "`rust-full`, `rust-coverage`, `rust-gate`, and `python-tests-gate`" in production_evidence_text
    assert "coverage-timing TSV, LCOV artifact, and `larch-linux-test-binary` artifact" in production_evidence_text
    assert "A pull-request or manual run does not substitute for a production push." in production_evidence_text

    assert "github.event_name != 'pull_request'" in rust_full
    assert "needs.rust-selection.outputs.mode == 'full'" in rust_full
    assert "needs.rust-selection.outputs.mode == 'partial'" in rust_partial
    assert "needs.rust-selection.outputs.mode == 'skip'" in rust_skip
    assert "needs: [rust-selection, rust-full, rust-partial, rust-skip]" in rust_coverage
    assert "if: always()" in rust_coverage
    assert "Require the selected Rust execution path to pass" in rust_coverage
    assert "needs: [rust-coverage, python-tests]" in python_rust_integration
    assert "LARCH_TEST_RUST_BINARY" not in python_tests
    assert "larch-linux-test-binary" not in python_tests
    assert "Verify selected Rust integration artifact" in python_rust_integration


def test_rust_ci_change_selection_rollout_contract() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    workflow = (repo_root / ".github" / "workflows" / "ci.yaml").read_text(encoding="utf-8")
    rust_testing = (repo_root / "docs" / "rust-testing.md").read_text(encoding="utf-8")
    workflow_trust = (
        repo_root / "docs" / "security" / "workflow-trust-and-mutations.md"
    ).read_text(encoding="utf-8")
    supply_chain = (
        repo_root / "docs" / "security" / "supply-chain-credentials-and-services.md"
    ).read_text(encoding="utf-8")
    evidence = (repo_root / "docs" / "rust-ci-selection-observation.md").read_text(encoding="utf-8")
    selector_job = workflow.split("\n  rust-selection:", 1)[1].split("\n  rust-lint:", 1)[0]
    rust_lint = workflow.split("\n  rust-lint:", 1)[1].split("\n  rust-deny:", 1)[0]
    rust_deny = workflow.split("\n  rust-deny:", 1)[1].split("\n  rust-full:", 1)[0]
    rust_full = workflow.split("\n  rust-full:", 1)[1].split("\n  rust-partial:", 1)[0]
    rust_partial = workflow.split("\n  rust-partial:", 1)[1].split("\n  rust-skip:", 1)[0]
    rust_skip = workflow.split("\n  rust-skip:", 1)[1].split("\n  rust-coverage:", 1)[0]
    rust_coverage = workflow.split("\n  rust-coverage:", 1)[1].split("\n  rust-coverage-benchmark:", 1)[0]

    assert "if: github.event_name == 'pull_request'" in selector_job
    assert "permissions:" in selector_job
    assert "contents: read" in selector_job
    assert "runs-on: ubuntu-24.04" in selector_job
    assert "timeout-minutes: 10" in selector_job
    assert 'RUST_CI_PARTIAL_ENFORCEMENT: "false"' in workflow
    assert 'RUST_CI_SKIP_ENFORCEMENT: "true"' in workflow
    assert "actions/checkout@8e8c483db84b4bee98b60c0593521ed34d9990e8 # v6.0.1" in selector_job
    assert "fetch-depth: 0" in selector_job
    assert "ref: ${{ github.sha }}" in selector_job
    assert "Check out the trusted PR-base selector" in selector_job
    assert "path: .rust-ci-selector-base" in selector_job
    assert "continue-on-error: true" in selector_job
    assert "persist-credentials: false" in selector_job
    assert "selector-base-checkout-unavailable" in selector_job
    assert "trusted-main-policy-unavailable-or-invalid" in selector_job
    assert "selector_history_source=full-history-checkout" in selector_job
    assert "RUST_SELECTION_HISTORY_MILLISECONDS" in selector_job
    assert "RUST_SELECTION_COMMAND_MILLISECONDS" in selector_job
    assert "cargo build --locked --package larch-cli --bin larch" not in selector_job
    assert 'selector_binary="$RUNNER_TEMP/trusted-main-rust-policy/larch"' in selector_job
    assert '"$selector_root/scripts/larch.sh" ci rust-select' in selector_job
    assert '"$selector_root/scripts/larch.sh" ci rust-select-summary' in selector_job
    assert "PYTHONPATH" not in selector_job
    assert "python/cli.py" not in selector_job
    assert "git worktree" not in selector_job
    assert "git cat-file" not in selector_job
    assert "git merge-base" not in selector_job
    assert "git fetch" not in selector_job
    assert '--repo-root "$GITHUB_WORKSPACE"' in selector_job
    assert "uses: ./.github/actions/main-cache-keys" in selector_job
    assert "key: ${{ steps.main-cache-keys.outputs.rust-policy }}" in selector_job
    assert "'build.rs'" in selector_job
    assert "'crates/**/*.rs'" in selector_job
    assert "'**/*.rs'" not in selector_job
    assert "sha256sum --check --strict larch.sha256" in selector_job
    assert "TRUSTED_POLICY_VALID" in selector_job
    assert "if: steps.proposed-selection.outputs.mode == 'skip'" not in selector_job
    assert "if: steps.effective-mode.outputs.mode == 'skip'" in selector_job
    assert selector_job.index("Restore trusted main Rust policy binary") < selector_job.index(
        "Select Rust CI mode from the trusted base"
    )
    assert selector_job.index("Verify trusted main Rust policy binary") < selector_job.index(
        "Select Rust CI mode from the trusted base"
    )
    policy_restore = selector_job.split("Restore trusted main Rust policy binary", 1)[1].split(
        "Verify trusted main Rust policy binary", 1
    )[0]
    assert "continue-on-error: true" in policy_restore
    assert "RUST_CI_FORCE_FULL" in selector_job
    assert "full-rust-ci" in selector_job
    assert "RUST_CI_PARTIAL_ENFORCEMENT" in selector_job
    assert "RUST_CI_SKIP_ENFORCEMENT" in selector_job
    assert "partial-observation-window-open" in selector_job
    assert "skip-observation-window-open" in selector_job
    assert ".rollout_state = $rollout_state" in selector_job
    assert ".observation_only = $observation_only" in selector_job
    assert ".proposed_mode = .mode" in selector_job
    assert ".effective_mode = $effective_mode" in selector_job
    assert ".effective_mode_reason = $effective_reason" in selector_job
    assert "fallback_selection()" in selector_job
    assert "selector-workflow-failed" in selector_job
    assert "schema_version: 1" in selector_job
    assert "Rust selector result was malformed; using the full Rust CI fallback" in selector_job
    assert selector_job.count("|| return 1") >= 3
    assert "all($doctests[];" in selector_job
    assert "name: rust-ci-selection" in selector_job
    assert "name: trusted-main-rust-policy" in selector_job
    assert "rust-selection-observation" not in workflow

    for selected_lane in (rust_lint, rust_deny, rust_full):
        assert "needs: [rust-selection]" in selected_lane
    assert "RUST_CI_MODE" in rust_lint
    assert "Run selected Clippy with warnings denied" in rust_lint
    assert "if: env.RUST_CI_MODE == 'full'" in rust_deny
    assert "partial-closure-covers-entire-workspace" in (
        repo_root / "crates" / "larch-cli" / "src" / "ci_selection.rs"
    ).read_text(encoding="utf-8")
    assert "needs.rust-selection.outputs.mode == 'full'" in rust_full
    assert "needs.rust-selection.outputs.mode == 'partial'" in rust_partial
    assert 'CARGO_PROFILE_TEST_OPT_LEVEL: "0"' in rust_partial
    assert "cargo test --doc" in rust_partial
    assert "cargo build --package larch-cli --bin larch --all-features --locked" in rust_partial
    assert "needs.rust-selection.outputs.mode == 'skip'" in rust_skip
    assert "Download verified trusted main policy binary" in rust_skip
    assert 'chmod 755 "$policy_dir/larch"' in rust_skip
    for plugin_validation_job in (rust_partial, rust_skip):
        assert "release plugin-runtime --check --check-worktree" in plugin_validation_job
        assert "git ls-files --others --exclude-standard -- plugin" not in plugin_validation_job
    assert "refs/heads/main" in rust_skip
    assert "needs: [rust-selection, rust-full, rust-partial, rust-skip]" in rust_coverage
    assert "Require the selected Rust execution path to pass" in rust_coverage
    assert 'if [ "$EVENT_NAME" = pull_request ] && [ "$SELECTION_RESULT" = success ]; then' in rust_coverage
    assert "mode=full" in rust_coverage
    assert "requiring the full Rust path" in rust_coverage

    for required_detail in (
        "Pull-request Rust selection",
        "typed command",
        "normal, build, and dev reverse dependency edge",
        "strict subset of the workspace",
        "trusted-main-rust-policy",
        "full-workspace\n  coverage threshold",
        "non-ancestor base",
        "full history",
        "Rust core redaction boundary",
        "scrub failure emits a static",
        "full-rust-ci",
        "merge group is the per-merge full-run backstop",
        "observation-window-open",
        "Promotion is intentionally manual and class-specific",
    ):
        assert required_detail in rust_testing
    for required_detail in (
        "CI Rust selection trust",
        "read-only workflow permissions",
        "it is an artifact for audit",
        "strict Rust-source package closure",
        "Skip ownership is explicit",
        "residual-secret rescan",
        "redaction failure emits a static",
        "trusted-main-rust-policy",
        "full history",
        "`RUST_CI_PARTIAL_ENFORCEMENT` remains `false`",
        "`RUST_CI_SKIP_ENFORCEMENT` is `true`",
    ):
        assert required_detail in workflow_trust
    for required_detail in (
        "Only the trusted\npublisher may save it",
        "exact successful merge-group source",
        "exact key binds",
        "trusted pull-request-base wrapper",
        "without compiling or executing pull-request code",
        "The skip\nlane is the only consumer of an artifact handoff",
        "Skip enforcement is enabled only after",
    ):
        assert required_detail in supply_chain
    for evidence_detail in (
        "six independent pull requests",
        "three `partial` and three\n`skip`",
        "zero historical full-backstop failures",
        "not a claim that the final",
        "Completed skip observation window",
        "#8247",
        "#8252",
        "Partial promotion decision (2026-08-08)",
        "one eligible partial observation",
        "#8281",
        "Two more distinct, ordinary pull requests",
        "345 seconds, 352 seconds, and 346 seconds",
        "75%) shorter on that measured Rust PR critical path",
        "does not change the classifier or its trusted-input\ncontract",
        "Do not count a label-forced run",
        "Rust-selection critical-path measurement (2026-08-08)",
        "Depth-two candidate trial",
        "`bounded-depth-8`",
        "#8288, attempt 3",
        "Before median",
        "After depth 8 median",
        "27 to 12 seconds",
        "23 to 9 seconds",
        "424 to 410 seconds",
        "#8002",
        "#8039",
    ):
        assert evidence_detail in evidence


def test_existing_regular_files_includes_symlink_to_file(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    target = repo / "real.py"
    target.write_text("x\n", encoding="utf-8")
    link = repo / "link.py"
    link.symlink_to(target)
    assert _crr._existing_regular_files(repo=repo, paths=("link.py",)) == ("link.py",)  # pyright: ignore[reportPrivateUsage]


def test_run_relevant_checks_non_rust_deletion_runs_contains_pins_without_make(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _checks_session(tmp_path, monkeypatch)
    repo = _git_repo(tmp_path)
    contains_calls: list[tuple[str, ...]] = []

    def fake_changed_files(_runner: object, *, cwd: str) -> tuple[str, ...]:
        _ = cwd
        return ("scripts/read-result-env.sh",)

    def fake_contains_pin_phase(*_args: object, changed: tuple[str, ...], **_kwargs: object) -> int:
        contains_calls.append(changed)
        return 0

    monkeypatch.setattr(_crr, "_changed_files", fake_changed_files)  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(_crr, "_run_contains_pin_phase", fake_contains_pin_phase)  # pyright: ignore[reportPrivateUsage]
    result = checks.run_relevant_checks(proc, site="unit", tmpdir=str(session), repo_root=str(repo))
    assert result.ok is True
    assert contains_calls == [("scripts/read-result-env.sh",)]


def test_run_relevant_checks_regular_rust_hook_runs_once_without_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _checks_session(tmp_path, monkeypatch)
    repo = _git_repo(tmp_path)
    rust_path = repo / "crates" / "demo" / "src" / "lib.rs"
    rust_path.parent.mkdir(parents=True)
    rust_path.write_text("pub fn demo() {}\n", encoding="utf-8")
    calls: list[tuple[list[str], dict[str, str]]] = []

    def fake_changed_files(_runner: object, *, cwd: str) -> tuple[str, ...]:
        _ = cwd
        return ("crates/demo/src/lib.rs",)

    def fake_logged(*, runner: object, argv: list[str], log_fd: int, env: dict[str, str], **_kwargs: object) -> CommandResult:
        _ = runner
        calls.append((argv, env))
        os.write(log_fd, b"RUST_CLIPPY_HOOK_RAN=true\n")
        return _ok("")

    def fake_contains_pin_phase(*_args: object, **_kwargs: object) -> int:
        return 0

    monkeypatch.setattr(_crr, "_changed_files", fake_changed_files)  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(_crr, "_run_logged", fake_logged)  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(_crr, "_run_contains_pin_phase", fake_contains_pin_phase)  # pyright: ignore[reportPrivateUsage]

    def available(*, runner: object, name: str, **_kwargs: object) -> bool:
        _ = runner
        return name == "pre-commit"

    monkeypatch.setattr(_crr, "_command_available", available)  # pyright: ignore[reportPrivateUsage]
    result = checks.run_relevant_checks(proc, site="unit", tmpdir=str(session), repo_root=str(repo))
    assert result.ok is True
    assert len(calls) == 1
    assert calls[0][0][:3] == ["pre-commit", "run", "--files"]
    assert all(
        forbidden not in " ".join(calls[0][0])
        for forbidden in ("rust-check", "cargo check", "cargo build", "cargo test", "cargo llvm-cov")
    )
    for key in (
        config.ENV_CARGO_INCREMENTAL,
        config.ENV_CARGO_PROFILE_DEV_DEBUG,
        config.ENV_CARGO_PROFILE_TEST_DEBUG,
    ):
        assert calls[0][1][key] == "0"


def test_run_relevant_checks_deleted_rust_path_uses_bounded_fallback_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _checks_session(tmp_path, monkeypatch)
    repo = _git_repo(tmp_path)
    calls: list[tuple[list[str], dict[str, str]]] = []

    def fake_changed_files(_runner: object, *, cwd: str) -> tuple[str, ...]:
        _ = cwd
        return ("crates/demo/src/lib.rs",)

    def fake_logged(*, runner: object, argv: list[str], log_fd: int, env: dict[str, str], **_kwargs: object) -> CommandResult:
        _ = runner
        calls.append((argv, env))
        os.write(log_fd, b"RUST_CLIPPY_HOOK_RAN=true\n")
        return _ok("")

    def fake_contains_pin_phase(*_args: object, **_kwargs: object) -> int:
        return 0

    monkeypatch.setattr(_crr, "_changed_files", fake_changed_files)  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(_crr, "_run_logged", fake_logged)  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(_crr, "_run_contains_pin_phase", fake_contains_pin_phase)  # pyright: ignore[reportPrivateUsage]
    result = checks.run_relevant_checks(proc, site="unit", tmpdir=str(session), repo_root=str(repo))
    assert result.ok is True
    assert len(calls) == 1
    assert calls[0][0][2:4] == ["checks", "rust-clippy"]
    assert "make" not in calls[0][0]
    assert calls[0][1][config.ENV_CARGO_INCREMENTAL] == "0"


def test_run_relevant_checks_non_regular_rust_skips_hook_and_falls_back_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _checks_session(tmp_path, monkeypatch)
    repo = _git_repo(tmp_path)
    python_path = repo / "python" / "changed.py"
    python_path.parent.mkdir()
    python_path.write_text("print('ok')\n", encoding="utf-8")
    calls: list[tuple[list[str], dict[str, str]]] = []

    def fake_changed_files(_runner: object, *, cwd: str) -> tuple[str, ...]:
        _ = cwd
        return ("crates/demo/src/lib.rs", "python/changed.py")

    def fake_logged(*, runner: object, argv: list[str], log_fd: int, env: dict[str, str], **_kwargs: object) -> CommandResult:
        _ = runner
        calls.append((argv, env))
        if argv[0] != "pre-commit":
            os.write(log_fd, b"RUST_CLIPPY_HOOK_RAN=true\n")
        return _ok("")

    monkeypatch.setattr(_crr, "_changed_files", fake_changed_files)  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(_crr, "_run_logged", fake_logged)  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(_crr, "_run_contains_pin_phase", _successful_contains_pin_phase)  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(_crr, "_command_available", _command_is_available)  # pyright: ignore[reportPrivateUsage]

    result = checks.run_relevant_checks(proc, site="unit", tmpdir=str(session), repo_root=str(repo))

    assert result.ok is True
    assert len(calls) == 2
    assert calls[0][0][0] == "pre-commit"
    assert _crr._RUST_CLIPPY_HOOK_ID in calls[0][1][config.ENV_PRECOMMIT_SKIP]  # pyright: ignore[reportPrivateUsage]
    assert calls[1][0][2:4] == ["checks", "rust-clippy"]


def test_run_relevant_checks_rust_hook_without_marker_fails_without_second_configuration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _checks_session(tmp_path, monkeypatch)
    repo = _git_repo(tmp_path)
    rust_path = repo / "crates" / "demo" / "src" / "lib.rs"
    rust_path.parent.mkdir(parents=True)
    rust_path.write_text("pub fn demo() {}\n", encoding="utf-8")
    calls: list[list[str]] = []

    def fake_changed_files(_runner: object, *, cwd: str) -> tuple[str, ...]:
        _ = cwd
        return ("crates/demo/src/lib.rs",)

    def fake_logged(*, runner: object, argv: list[str], log_fd: int, **_kwargs: object) -> CommandResult:
        _ = runner, log_fd
        calls.append(argv)
        return _ok("")

    monkeypatch.setattr(_crr, "_changed_files", fake_changed_files)  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(_crr, "_run_logged", fake_logged)  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(_crr, "_run_contains_pin_phase", _successful_contains_pin_phase)  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(_crr, "_command_available", _command_is_available)  # pyright: ignore[reportPrivateUsage]

    result = checks.run_relevant_checks(proc, site="unit", tmpdir=str(session), repo_root=str(repo))

    assert result.ok is False
    assert len(calls) == 1
    assert calls[0][0] == "pre-commit"
    assert "make" not in calls[0]
    assert "refusing a second Rust configuration" in Path(result.raw_log_path or "").read_text(encoding="utf-8")


def test_run_relevant_checks_missing_rust_proof_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _checks_session(tmp_path, monkeypatch)
    repo = _git_repo(tmp_path)
    rust_path = repo / "crates" / "demo" / "src" / "lib.rs"
    rust_path.parent.mkdir(parents=True)
    rust_path.write_text("pub fn demo() {}\n", encoding="utf-8")
    calls: list[list[str]] = []

    def fake_changed_files(_runner: object, *, cwd: str) -> tuple[str, ...]:
        _ = cwd
        return ("crates/demo/src/lib.rs",)

    def fake_logged(*, runner: object, argv: list[str], **_kwargs: object) -> CommandResult:
        _ = runner
        calls.append(argv)
        return _ok("")

    monkeypatch.setattr(_crr, "_changed_files", fake_changed_files)  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(_crr, "_run_logged", fake_logged)  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(_crr, "_run_contains_pin_phase", _successful_contains_pin_phase)  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(_crr, "_command_available", _command_is_available)  # pyright: ignore[reportPrivateUsage]

    result = checks.run_relevant_checks(proc, site="unit", tmpdir=str(session), repo_root=str(repo))

    assert result.ok is False
    assert result.exit_code == 1
    assert len(calls) == 1
    assert "refusing a second Rust configuration" in Path(result.raw_log_path or "").read_text(encoding="utf-8")


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


def test_checks_repair_loop_bgjob_launch_starts_transport(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    session = _checks_session(tmp_path, monkeypatch)
    checks_log = session / "initial.redacted.log"
    checks_log.write_text("err\n", encoding="utf-8")
    calls: list[tuple[str, ...]] = []
    entrypoint = tmp_path / "scripts" / "larch.sh"

    def fake_larch_entrypoint(_root: Path) -> Path:
        return entrypoint

    def fake_proc_run(argv: Sequence[str], **_kwargs: object) -> CommandResult:
        argv_tuple = tuple(argv)
        calls.append(argv_tuple)
        return CommandResult(
            argv_tuple,
            0,
            "BGJOB_STATUS=STARTED STEP=implement-step3-repair PGID=123\n",
            "",
            0.0,
        )

    monkeypatch.setattr(_clf, "larch_entrypoint", fake_larch_entrypoint)
    monkeypatch.setattr(_clf.proc, "run", fake_proc_run)
    rc = checks.checks_repair_loop_main([
        "--tmpdir",
        str(session),
        "--site",
        "step3",
        "--checks-log",
        str(checks_log),
        "--repo-root",
        str(tmp_path),
        "--bgjob-launch",
        "true",
    ])
    assert rc == 0
    assert capsys.readouterr().out == (
        "BGJOB_STATUS=STARTED STEP=implement-step3-repair PGID=123\n"
    )
    start = calls[0]
    assert start[:3] == (str(entrypoint), "bgjob", "start")
    assert start[3:9] == (
        "--step",
        "implement-step3-repair",
        "--tmpdir",
        str(session),
        "--budget-s",
        str(
            external_defaults.fixer_lane_budget_sec("implement.lint_fix_coder")
            * config.RCC_MAX_ITER_DEFAULT
        ),
    )
    assert "--merge-result-env" in start
    assert str(session / "bgjob" / "implement-step3-repair.merge.env") in start
    terminal_marker = start.index("--terminal-stdout-key")
    assert start[terminal_marker:terminal_marker + 2] == ("--terminal-stdout-key", "NEXT_ACTION")
    assert "--bgjob-merge-result-env" in start
    assert "checks" in start
    assert "repair-loop" in start
    assert "--bgjob-launch" not in start


def test_checks_repair_loop_bgjob_launch_site_qualifies_step6_slug(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _checks_session(tmp_path, monkeypatch)
    checks_log = session / "initial.redacted.log"
    checks_log.write_text("err\n", encoding="utf-8")
    calls: list[tuple[str, ...]] = []

    def fake_proc_run(argv: Sequence[str], **_kwargs: object) -> CommandResult:
        argv_tuple = tuple(argv)
        calls.append(argv_tuple)
        return CommandResult(argv_tuple, 0, "BGJOB_STATUS=STARTED\n", "", 0.0)

    monkeypatch.setattr(_clf.proc, "run", fake_proc_run)
    rc = checks.checks_repair_loop_main([
        "--tmpdir",
        str(session),
        "--site",
        "step6",
        "--checks-log",
        str(checks_log),
        "--bgjob-launch",
        "true",
    ])
    assert rc == 0
    assert calls[0][4] == "implement-step6-repair"


def test_checks_repair_loop_bgjob_launch_propagates_transport_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    session = _checks_session(tmp_path, monkeypatch)
    checks_log = session / "initial.redacted.log"
    checks_log.write_text("err\n", encoding="utf-8")

    def fake_proc_run(argv: Sequence[str], **_kwargs: object) -> CommandResult:
        return CommandResult(tuple(argv), 23, "BGJOB_STATUS=FAILED\n", "launch failed\n", 0.0)

    monkeypatch.setattr(_clf.proc, "run", fake_proc_run)
    rc = checks.checks_repair_loop_main([
        "--tmpdir",
        str(session),
        "--site",
        "step3",
        "--checks-log",
        str(checks_log),
        "--bgjob-launch",
        "true",
    ])

    assert rc == 23
    captured = capsys.readouterr()
    assert captured.out == "BGJOB_STATUS=FAILED\n"
    assert captured.err == "launch failed\n"


def test_checks_repair_loop_merge_result_env_captures_terminal_kvs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    session = _checks_session(tmp_path, monkeypatch)
    checks_log = session / "initial.redacted.log"
    checks_log.write_text("err\n", encoding="utf-8")
    merge_env = session / "bgjob" / "implement-step3-repair.merge.env"

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
        "--bgjob-merge-result-env",
        str(merge_env),
    ])
    out = capsys.readouterr().out
    assert rc == 0
    assert "NEXT_ACTION=continue" in out
    text = merge_env.read_text(encoding="utf-8")
    assert "NEXT_ACTION=continue\n" in text
    assert "LOOP_STATUS=ok\n" in text
    assert "BGJOB_RC=" not in text


def test_checks_repair_loop_merge_rows_flush_immediately(tmp_path: Path) -> None:
    merge_env = tmp_path / "bgjob" / "repair.merge.env"

    with result_env_capture_rows(merge_env) as rows:
        assert rows is not None
        rows.append(("NEXT_ACTION", "main-agent-edit"))
        assert merge_env.read_text(encoding="utf-8") == "NEXT_ACTION=main-agent-edit\n"


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


def test_checks_repair_loop_main_step6_no_changes_stale_falls_back_to_main_agent(
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
    assert rc == 0
    assert "NEXT_ACTION=main-agent-edit" in out
    assert "LOOP_STATUS=no-changes-stale" in out
    assert "LINT_FIX_LEDGER_READY=true" in out
    assert "LINT_FIX_LEDGER_SITE=step6" in out
    assert "LINT_FIX_LEDGER_TRIGGER=main-agent-required" in out
    assert "LINT_FIX_LEDGER_STEP=6" in out
    assert "LINT_FIX_LEDGER_PHASE=checks" in out
    assert "LINT_FIX_LEDGER_DISPATCHER=lint-fix-loop" in out
    assert "LINT_FIX_LEDGER_EXIT_CODE=1" in out
    assert f"LINT_FIX_LEDGER_FAILURE_DETAIL_LOG={checks_log.resolve()}" in out


@pytest.mark.parametrize(("site", "step"), [("step3", "3"), ("step6", "6")])
def test_checks_repair_loop_main_exhausted_falls_back_to_main_agent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    site: str,
    step: str,
) -> None:
    session = _checks_session(tmp_path, monkeypatch)
    checks_log = session / "initial.redacted.log"
    checks_log.write_text("initial failure\n", encoding="utf-8")
    failure_logs = [session / f"iteration-{iteration}.redacted.log" for iteration in range(1, 4)]
    for iteration, failure_log in enumerate(failure_logs, start=1):
        failure_log.write_text(f"failure {iteration}\n", encoding="utf-8")

    def fake_run_lint_fix(_runner: object, **_kwargs: object) -> checks.FixOutcome:
        return checks.FixOutcome(
            status="applied",
            delta_paths=("fixed.py",),
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
        return _repair_loop_failed_result(failure_logs.pop(0), site=site)

    monkeypatch.setattr(_clf, "run_lint_fix", fake_run_lint_fix)
    monkeypatch.setattr(_clf, "run_relevant_checks", fake_run_relevant_checks)
    final_failure_log = session / "iteration-3.redacted.log"
    rc = checks.checks_repair_loop_main([
        "--tmpdir",
        str(session),
        "--site",
        site,
        "--checks-log",
        str(checks_log),
        "--repo-root",
        str(tmp_path),
    ])
    out = capsys.readouterr().out
    assert rc == 0
    assert "NEXT_ACTION=main-agent-edit" in out
    assert "LOOP_STATUS=exhausted" in out
    assert "LINT_FIX_LEDGER_READY=true" in out
    assert f"LINT_FIX_LEDGER_SITE={site}" in out
    assert "LINT_FIX_LEDGER_TRIGGER=main-agent-required" in out
    assert f"LINT_FIX_LEDGER_STEP={step}" in out
    assert "LINT_FIX_LEDGER_PHASE=checks" in out
    assert "LINT_FIX_LEDGER_DISPATCHER=lint-fix-loop" in out
    assert "LINT_FIX_LEDGER_EXIT_CODE=1" in out
    assert f"LINT_FIX_LEDGER_FAILURE_DETAIL_LOG={final_failure_log.resolve()}" in out
    assert str(checks_log.resolve()) not in out.split("LINT_FIX_LEDGER_FAILURE_DETAIL_LOG=", maxsplit=1)[1]


@pytest.mark.parametrize(
    ("site", "step", "phase"),
    [
        ("step3", "3", "checks"),
        ("step5", "5", "review"),
        ("step5-self-review", "5", "review"),
        ("step5-mav", "5", "review"),
        ("step6", "6", "checks"),
    ],
)
def test_checks_repair_loop_main_all_tiers_no_delta_escalates_to_main_agent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    site: str,
    step: str,
    phase: str,
) -> None:
    session = _checks_session(tmp_path, monkeypatch)
    checks_log = session / "initial.redacted.log"
    checks_log.write_text("initial failure\n", encoding="utf-8")

    def fake_run_lint_fix(_runner: object, **_kwargs: object) -> checks.FixOutcome:
        return checks.FixOutcome(
            status="failed",
            delta_paths=(),
            failure_reason="lint-fix-all-tiers-no-useful-delta",
            commit_sha=None,
            head_changed=False,
            coder_tool=None,
            tier_ledger_path=str(session / "lint-fix-tier-ledger.tsv"),
            ledger_failure_detail_log=str(checks_log),
        )

    monkeypatch.setattr(_clf, "run_lint_fix", fake_run_lint_fix)
    rc = checks.checks_repair_loop_main([
        "--tmpdir",
        str(session),
        "--site",
        site,
        "--checks-log",
        str(checks_log),
        "--repo-root",
        str(tmp_path),
    ])
    out = capsys.readouterr().out

    assert rc == 0
    assert "NEXT_ACTION=main-agent-edit" in out
    assert "LOOP_STATUS=exhausted" in out
    assert "FAILURE_REASON=lint-fix-all-tiers-no-useful-delta" in out
    assert "LINT_FIX_LEDGER_READY=true" in out
    assert f"LINT_FIX_LEDGER_SITE={site}" in out
    assert "LINT_FIX_LEDGER_TRIGGER=main-agent-required" in out
    assert f"LINT_FIX_LEDGER_STEP={step}" in out
    assert f"LINT_FIX_LEDGER_PHASE={phase}" in out
    assert "LINT_FIX_LEDGER_DISPATCHER=lint-fix-loop" in out
    assert "LINT_FIX_LEDGER_EXIT_CODE=1" in out
    assert f"LINT_FIX_LEDGER_FAILURE_DETAIL_LOG={checks_log.resolve()}" in out


@pytest.mark.parametrize("final_log", ["", "outside.redacted.log"])
def test_checks_repair_loop_main_exhausted_invalid_final_log_stalls(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    final_log: str,
) -> None:
    session = _checks_session(tmp_path, monkeypatch)
    checks_log = session / "initial.redacted.log"
    checks_log.write_text("initial failure\n", encoding="utf-8")
    carried_log = ""
    if final_log:
        outside_log = tmp_path / final_log
        outside_log.write_text("outside failure\n", encoding="utf-8")
        carried_log = str(outside_log)

    def fake_run_check_fix_loop(**_kwargs: object) -> checks.LoopResult:
        return checks.LoopResult(
            status="exhausted",
            final_redacted_checks_log=carried_log,
        )

    monkeypatch.setattr(_clf, "run_check_fix_loop", fake_run_check_fix_loop)
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
    assert "LOOP_STATUS=exhausted" in out
    assert "LINT_FIX_LEDGER_READY" not in out


def test_checks_repair_loop_main_ship_pr_exhausted_stalls(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    session = _checks_session(tmp_path, monkeypatch)
    checks_log = session / "initial.redacted.log"
    checks_log.write_text("initial failure\n", encoding="utf-8")
    final_log = session / "final.redacted.log"
    final_log.write_text("final failure\n", encoding="utf-8")
    def fake_run_check_fix_loop(**_kwargs: object) -> checks.LoopResult:
        return checks.LoopResult(
            status="exhausted",
            final_redacted_checks_log=str(final_log),
        )

    monkeypatch.setattr(_clf, "run_check_fix_loop", fake_run_check_fix_loop)
    rc = checks.checks_repair_loop_main([
        "--tmpdir",
        str(session),
        "--site",
        "ship-pr-ci-initial",
        "--checks-log",
        str(checks_log),
        "--repo-root",
        str(tmp_path),
    ])
    out = capsys.readouterr().out
    assert rc == 1
    assert "NEXT_ACTION=stall" in out
    assert "LOOP_STATUS=exhausted" in out
    assert "LINT_FIX_LEDGER_READY" not in out


def test_checks_repair_loop_main_ship_pr_no_changes_stale_stalls(
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
        "ship-pr-ci-initial",
        "--checks-log",
        str(checks_log),
        "--repo-root",
        str(tmp_path),
    ])
    out = capsys.readouterr().out
    assert rc == 1
    assert "NEXT_ACTION=stall" in out
    assert "LOOP_STATUS=no-changes-stale" in out
    assert "LINT_FIX_LEDGER_READY" not in out


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


def test_checks_repair_loop_main_empty_tmpdir_falls_back_to_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # A fresh Bash block expands an unset $IMPLEMENT_TMPDIR to an empty --tmpdir
    # argument. The stable launcher exports IMPLEMENT_TMPDIR to this process, so
    # the entrypoint must fall back to the env var instead of stalling at
    # LOOP_STATUS=tmpdir-validation. Progression to the next validation gate
    # (checks-site-validation) proves the env fallback resolved the tmpdir.
    session = _checks_session(tmp_path, monkeypatch)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(session))
    rc = checks.checks_repair_loop_main([
        "--tmpdir",
        "",
        "--site",
        "step6",
        "--checks-site",
        "../bad",
        "--checks-log",
        str(session / "initial.redacted.log"),
        "--repo-root",
        str(tmp_path),
    ])
    out = capsys.readouterr().out
    assert rc == 2
    assert "LOOP_STATUS=checks-site-validation" in out
    assert "LOOP_STATUS=tmpdir-validation" not in out


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
    dispatch_calls: list[str] = []

    def succeed_claude(*_args: object, **_kwargs: object) -> int:
        dispatch_calls.append("claude")
        return 0

    monkeypatch.setattr(_clf, "_run_claude", succeed_claude)
    def claude_on_path(name: str) -> str | None:
        return "/usr/bin/claude" if name == "claude" else None

    monkeypatch.setattr(shutil, "which", claude_on_path)
    monkeypatch.delenv("CLAUDE_BINARY_FOUND", raising=False)
    head = "abc123"
    delta_raw = ":100644 100644 abc def M\tfixed.py\n"
    runner = StubRunner([
        # Baseline setup
        _ok(""),  # baseline tracked diff
        _ok(""),  # baseline cached diff
        _ok(""),  # baseline untracked status
        _ok(""),  # baseline snapshot git diff --raw
        _ok(""),  # baseline snapshot git diff --cached --raw
        _ok(head + "\n"),  # rev-parse HEAD
        _ok("main\n"),  # symbolic-ref
        _ok(""),  # submodule foreach (prompt)
        _ok(""),  # submodule foreach (forbidden paths)
        # Per-attempt baseline (claude is mocked)
        _ok(""),  # attempt tracked diff
        _ok(""),  # attempt cached diff
        _ok(""),  # attempt untracked status
        _ok(""),  # attempt snapshot git diff --raw
        _ok(""),  # attempt snapshot git diff --cached --raw
        _ok(head + "\n"),  # attempt HEAD
        # Post-dispatch current snapshot (claude mocked, no dispatch stub)
        _ok(""),  # current tracked diff
        _ok(""),  # current cached diff
        _ok(""),  # current untracked status
        _ok(delta_raw),  # current snapshot git diff --raw (useful delta)
        _ok(""),  # current snapshot git diff --cached --raw
        _ok(head + "\n"),  # current attempt HEAD (unchanged)
        # Post-loop: current HEAD (unchanged)
        _ok(head + "\n"),  # current HEAD after dispatch
        # _post_dispatch_forbidden_revert
        _ok(""),  # forbidden-revert tracked diff
        _ok(""),  # forbidden-revert cached diff
        _ok(""),  # forbidden-revert untracked status
        # Final delta snapshot
        _ok("fixed.py\n"),  # current tracked diff
        _ok(""),  # current cached diff
        _ok(""),  # current untracked status
        _ok(delta_raw),  # final snapshot git diff --raw
        _ok(""),  # final snapshot git diff --cached --raw
        # Git operations
        _ok(""),  # git add
        _ok(""),  # cli.py git commit
        _ok("def456\n"),  # commit SHA
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


def test_run_lint_fix_all_three_tiers_report_exhaustion_for_repair_loop(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    log = tmp_path / "checks.log"
    _ = log.write_text("lint error\n", encoding="utf-8")
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
    monkeypatch.delenv("CLAUDE_BINARY_FOUND", raising=False)
    head = "abc123"
    runner = StubRunner([
        _ok(""),  # baseline tracked diff
        _ok(""),  # baseline cached diff
        _ok(""),  # baseline untracked status
        _ok(""),  # baseline snapshot git diff --raw
        _ok(""),  # baseline snapshot git diff --cached --raw
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
        cursor_present=True,
        allowed_tmpdir=_lint_fix_dirs(tmp_path)[0],
        run_parent=_lint_fix_dirs(tmp_path)[1],
    )
    assert dispatch_calls == ["claude", "codex", "cursor"]
    assert outcome.status == "failed"
    assert outcome.failure_reason == "lint-fix-all-tiers-no-useful-delta"
    assert outcome.tier_ledger_path
    assert outcome.ledger_ready is False


def test_handle_fix_outcome_preserves_named_exhaustion_evidence() -> None:
    loop = checks.LoopResult(status="exhausted")
    fix = checks.FixOutcome(
        status="failed",
        delta_paths=(),
        failure_reason="lint-fix-all-tiers-no-useful-delta",
        commit_sha=None,
        head_changed=False,
        coder_tool=None,
        tier_ledger_path="/tmp/lint-fix-tier-ledger.tsv",
    )

    should_continue = _clf._handle_fix_outcome(  # pyright: ignore[reportPrivateUsage]
        fix,
        delta_accum=[],
        loop=loop,
    )

    assert should_continue is False
    assert loop.status == "exhausted"
    assert loop.failure_reason == "lint-fix-all-tiers-no-useful-delta"
    assert loop.tier_ledger_path == "/tmp/lint-fix-tier-ledger.tsv"


def test_repair_loop_action_stalls_only_named_pre_ship_exhaustion(tmp_path: Path) -> None:
    named = checks.LoopResult(
        status="exhausted",
        failure_reason="lint-fix-budget-exhausted",
    )
    generic = checks.LoopResult(status="exhausted", failure_reason="dispatch-failed")
    structural = checks.LoopResult(
        status="main-agent-required",
        failure_reason="structural-ruff-failure",
    )

    assert _clf._repair_loop_action(  # pyright: ignore[reportPrivateUsage]
        named,
        lint_site="step6",
        checks_log="",
        allowed_tmpdir=tmp_path,
    ) == "stall"
    assert _clf._repair_loop_action(  # pyright: ignore[reportPrivateUsage]
        generic,
        lint_site="step6",
        checks_log="",
        allowed_tmpdir=tmp_path,
    ) == "stall"
    assert _clf._repair_loop_action(  # pyright: ignore[reportPrivateUsage]
        structural,
        lint_site="step6",
        checks_log="",
        allowed_tmpdir=tmp_path,
    ) == "main-agent-edit"


def _classify(tmp_path: Path, *, launcher_rc: int, useful_delta: bool, log: str = "", stderr_tail: str = "") -> str:
    (tmp_path / "claude.log").write_text(log, encoding="utf-8")
    (tmp_path / "claude.log.stderr-tail").write_text(stderr_tail, encoding="utf-8")
    return _clf._classify_attempt_issue(  # pyright: ignore[reportPrivateUsage]
        launcher_rc=launcher_rc, run_dir=tmp_path, log_name="claude.log", useful_delta=useful_delta,
    )


def test_classify_attempt_issue_green_fix_never_classified(tmp_path: Path) -> None:
    # #7074: a succeeded fix with a useful delta is not an execution issue, even
    # when its transcript names a repo file like preflight.py.
    assert _classify(
        tmp_path,
        launcher_rc=0,
        useful_delta=True,
        log="I did not touch the unrelated `preflight.py` working-tree change.\n",
        stderr_tail="",
    ) == ""


def test_classify_attempt_issue_ignores_transcript_prose(tmp_path: Path) -> None:
    # #7074: token matching is anchored to stderr-tail. preflight.py / "not found"
    # in the coder transcript (main log) must not brand a failed attempt.
    assert _classify(
        tmp_path,
        launcher_rc=1,
        useful_delta=False,
        log="touched preflight.py; metadata not found earlier in the run\n",
        stderr_tail="",
    ) == "launcher-failure"


def test_classify_attempt_issue_auth_on_stderr_still_flagged(tmp_path: Path) -> None:
    assert _classify(
        tmp_path,
        launcher_rc=1,
        useful_delta=False,
        stderr_tail="Error: not authenticated. login required.\n",
    ) == "authentication-preflight"


def test_classify_attempt_issue_bare_not_found_dropped(tmp_path: Path) -> None:
    # #7074: the bare "not found" token is dropped; "metadata not found" prose on
    # stderr must not misclassify as missing-binary.
    assert _classify(
        tmp_path,
        launcher_rc=1,
        useful_delta=False,
        stderr_tail="runtime model error gpt-5.6-sol metadata not found\n",
    ) == "launcher-failure"
    # A genuine missing binary still classifies.
    assert _classify(
        tmp_path,
        launcher_rc=1,
        useful_delta=False,
        stderr_tail="claude: command not found\n",
    ) == "missing-binary"


def test_append_attempt_execution_issue_is_single_line(tmp_path: Path) -> None:
    # #7074: a multi-line transcript tail must collapse to one bullet so its own
    # "- ..." lines do not inflate the summary's exec-issue count.
    attempt = tmp_path / "attempt.log"
    attempt.write_text(
        "Verification complete:\n- pyright: 0 errors\n- ruff: All checks passed!\nFIXED: foo.py\n",
        encoding="utf-8",
    )
    issue_log = tmp_path / "execution-issues.md"
    _clf._append_attempt_execution_issue(  # pyright: ignore[reportPrivateUsage]
        issue_log=issue_log, tier="claude", issue_kind="authentication-preflight", attempt_log=str(attempt),
    )
    bullets = [line for line in issue_log.read_text(encoding="utf-8").splitlines() if line.startswith("- ")]
    assert len(bullets) == 1
    assert bullets[0].startswith("- lint-fix tier=claude category=authentication-preflight;")
