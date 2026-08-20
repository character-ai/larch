"""Lint-fix dispatch loop and repair-loop CLI (ship-pr Phase 4, lint-fix half).

Contains the lint-fix agent dispatch pipeline, the check-fix loop, escalation,
and the repair-loop CLI. See checks_run_relevant.py for the run-relevant-checks
runner and contains-pins checker.
"""

from __future__ import annotations

import argparse
import contextlib
import os
import re
import sys
import threading
import time
from collections.abc import Callable, Generator
from dataclasses import dataclass
from pathlib import Path
from typing import Final, NoReturn

from larch import io as larch_io
from larch.core import config
from larch.core import external_defaults
from larch.core import proc
from larch.core import redact
from larch.core.repo_roots import larch_entrypoint, plugin_root
from larch.outcomes import Outcome, StepResult
from larch.core.proc import Runner

from larch.implement.checks_run_relevant import (
    ChecksResult,
    FixOutcome,
    LoopResult,
    validate_tmpdir,
    resolve_checks_log_path,
    read_log_file_text,
    normalize_max_iter,
    run_relevant_checks,
    default_repo_root,
)
from larch.implement.dispatch_helpers import ResultEnvCaptureRows, result_env_capture_rows

from larch.implement.self_edit_log import record_self_edits

_SITE_LABELS: Final[dict[str, str]] = {
    "step3": "Step 3",
    "step5": "Step 5",
    "step5-self-review": "Step 5",
    "step5-mav": "Step 5",
    "step6": "Step 6",
    "ship-pr-ci-initial": "ship-pr CI initial",
    "ship-pr-ci-merge": "ship-pr CI merge",
    "ship-pr-ci-per-job": "ship-pr CI per-job",
}
_PRE_SHIP_SITES: Final[frozenset[str]] = frozenset({
    "step3",
    "step5",
    "step5-self-review",
    "step5-mav",
    "step6",
})
_PRE_SHIP_ALL_TIERS_NO_DELTA_REASON: Final = "lint-fix-all-tiers-no-useful-delta"
_PRE_SHIP_NON_STRUCTURAL_REASONS: Final[frozenset[str]] = frozenset({
    "lint-fix-no-selectable-tier",
    _PRE_SHIP_ALL_TIERS_NO_DELTA_REASON,
    "lint-fix-budget-exhausted",
})
_PRE_SHIP_STALL_REASONS: Final[frozenset[str]] = (
    _PRE_SHIP_NON_STRUCTURAL_REASONS - {_PRE_SHIP_ALL_TIERS_NO_DELTA_REASON}
)
_EMPTY_FAILURE_CAP: Final = 2
_REPAIR_LOOP_HEARTBEAT_INTERVAL_S: Final = 30.0
_REPAIR_LOOP_HEARTBEAT_JOIN_TIMEOUT_S: Final = 2.0
# Module-scoped sink for optional bgjob merge-result-env capture (child mode).
_result_rows: ResultEnvCaptureRows | None = None


def _ledger_site_for_lint_site(site: str) -> str:
    if site.startswith("ship-pr-ci-"):
        return "ship-pr-internal"
    return site


def _ledger_trigger_for_lint_site(site: str) -> str:
    if site.startswith("ship-pr-ci-"):
        return config.NEEDS_USER_SHIP_PR_INTERNAL_LINT_FIX
    return "main-agent-required"


def _ledger_step_for_site(site: str) -> str:
    if site.startswith("step5"):
        return "5"
    if site == "step6":
        return "6"
    if site == "step3":
        return "3"
    return "8"


def _ledger_phase_for_site(site: str) -> str:
    if site.startswith("step5"):
        return "review"
    if site in {"step3", "step6"}:
        return "checks"
    if site == "ship-pr-ci-initial":
        return "ci-initial"
    if site in {"ship-pr-ci-merge", "ship-pr-ci-per-job"}:
        return "ci-merge"
    return "ci-merge"


def _emit_repair_kv(*, key: str, value: str) -> None:
    rows = _result_rows
    if rows is not None and "\n" not in value and "\r" not in value and re.fullmatch(r"[A-Z0-9_]+", key):
        rows.append((key, value))
    print(f"{key}={value}")


def _print_loop_ledger(loop: LoopResult) -> None:
    if not loop.ledger_ready:
        return
    _emit_repair_kv(key="LINT_FIX_LEDGER_READY", value="true")
    _emit_repair_kv(key="LINT_FIX_LEDGER_SITE", value=loop.ledger_site)
    _emit_repair_kv(key="LINT_FIX_LEDGER_TRIGGER", value=loop.ledger_trigger)
    _emit_repair_kv(key="LINT_FIX_LEDGER_STEP", value=loop.ledger_step)
    _emit_repair_kv(key="LINT_FIX_LEDGER_PHASE", value=loop.ledger_phase)
    _emit_repair_kv(key="LINT_FIX_LEDGER_DISPATCHER", value=loop.ledger_dispatcher)
    if loop.ledger_exit_code is not None:
        _emit_repair_kv(key="LINT_FIX_LEDGER_EXIT_CODE", value=str(loop.ledger_exit_code))
    if loop.ledger_failure_detail_log:
        _emit_repair_kv(
            key="LINT_FIX_LEDGER_FAILURE_DETAIL_LOG",
            value=loop.ledger_failure_detail_log,
        )


def _repair_loop_action(
    loop: LoopResult,
    *,
    lint_site: str,
    checks_log: str,
    allowed_tmpdir: Path,
) -> str:
    if loop.status == "ok":
        return "continue"
    if loop.status == "main-agent-required":
        return "main-agent-edit"
    if _is_pre_ship_site(lint_site) and loop.status in {
        "head-changed",
        "dispatch-failed",
    }:
        return "main-agent-edit"
    if (
        _is_pre_ship_site(lint_site)
        and loop.failure_reason in _PRE_SHIP_STALL_REASONS
    ):
        return "stall"
    # Exhaustion after every delegated tier made no useful delta, like
    # iteration-count exhaustion, needs a recorded main-agent escalation.
    if loop.status in {"exhausted", "no-changes-stale"} and _is_pre_ship_site(lint_site):
        # Use the initial checks_log for no-changes-stale, final iteration log for exhausted.
        log_candidate = (
            checks_log if loop.status == "no-changes-stale" else loop.final_redacted_checks_log
        )
        log_path = resolve_checks_log_path(
            candidate=log_candidate,
            allowed_root=allowed_tmpdir,
        )
        if log_path is not None:
            loop.ledger_ready = True
            loop.ledger_site = _ledger_site_for_lint_site(lint_site)
            loop.ledger_trigger = _ledger_trigger_for_lint_site(lint_site)
            loop.ledger_step = _ledger_step_for_site(lint_site)
            loop.ledger_phase = _ledger_phase_for_site(lint_site)
            loop.ledger_dispatcher = "lint-fix-loop"
            loop.ledger_exit_code = 1
            loop.ledger_failure_detail_log = str(log_path)
            return "main-agent-edit"
    return "stall"


def _valid_checks_site(site: str) -> bool:
    return bool(
        site
        and re.fullmatch(r"[A-Za-z0-9._-]+", site)
        and not site.startswith(".")
        and ".." not in site
    )


class _RepairLoopArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        print("NEXT_ACTION=stall")
        print("LOOP_STATUS=argument-error")
        super().error(message)


@dataclass(frozen=True)
class RepairLoopBgjobLaunch:
    tmpdir: Path
    site: str
    checks_site: str
    checks_log: str
    repo_root: str


def _repair_loop_step_slug(site: str) -> str:
    return f"implement-{site}-repair"


@contextlib.contextmanager
def _result_env_capture(path: Path | None) -> Generator[None, None, None]:
    global _result_rows  # noqa: PLW0603 - scoped sink for bgjob merge-result-env capture
    prior = _result_rows
    try:
        with result_env_capture_rows(path) as rows:
            _result_rows = rows
            yield
    finally:
        _result_rows = prior


def _launch_repair_loop_bgjob(spec: RepairLoopBgjobLaunch) -> int:
    step = _repair_loop_step_slug(spec.site)
    merge_result_env = spec.tmpdir / "bgjob" / f"{step}.merge.env"
    merge_result_env.parent.mkdir(parents=True, exist_ok=True)
    larch_io.atomic_write(path=merge_result_env, text="", nofollow=True, mode=0o600)
    budget_s = str(
        external_defaults.fixer_lane_budget_sec("implement.lint_fix_coder")
        * config.RCC_MAX_ITER_DEFAULT
    )
    command: list[str] = [
        str(larch_entrypoint(Path(__file__).resolve().parents[3])),
        "bgjob",
        "start",
        "--step",
        step,
        "--tmpdir",
        str(spec.tmpdir),
        "--budget-s",
        budget_s,
        "--merge-result-env",
        str(merge_result_env),
        "--terminal-stdout-key",
        "NEXT_ACTION",
        "--",
        sys.executable,
        str(plugin_root(Path(__file__).resolve().parents[3]) / "python" / "cli.py"),
        "checks",
        "repair-loop",
        "--tmpdir",
        str(spec.tmpdir),
        "--site",
        spec.site,
    ]
    if spec.checks_site:
        command.extend(("--checks-site", spec.checks_site))
    command.extend(("--checks-log", spec.checks_log))
    if spec.repo_root:
        command.extend(("--repo-root", spec.repo_root))
    command.extend(("--bgjob-merge-result-env", str(merge_result_env)))
    result = proc.run(command)
    if result.stdout:
        _ = sys.stdout.write(result.stdout)
    if result.stderr:
        _ = sys.stderr.write(result.stderr)
    return int(result.returncode)


def _emit_repair_loop_heartbeat(*, stop: threading.Event, site: str) -> None:
    start: float = time.monotonic()
    while not stop.wait(_REPAIR_LOOP_HEARTBEAT_INTERVAL_S):
        elapsed: int = int(time.monotonic() - start)
        print(f"PROGRESS=lint-fix-running site={site} elapsed={elapsed}s", flush=True)


def _emit_repair_loop_outcome(*, action: str, loop: LoopResult) -> None:
    _emit_repair_kv(key="NEXT_ACTION", value=action)
    _emit_repair_kv(key="LOOP_STATUS", value=loop.status)
    if loop.stderr_tail_path:
        _emit_repair_kv(key="STDERR_TAIL_PATH", value=loop.stderr_tail_path)
    if loop.coder_log_path:
        _emit_repair_kv(key="CODER_LOG_FILE", value=loop.coder_log_path)
    if loop.failure_reason:
        _emit_repair_kv(key="FAILURE_REASON", value=loop.failure_reason)
    if loop.tier_ledger_path:
        _emit_repair_kv(key="LINT_FIX_TIER_LEDGER_PATH", value=loop.tier_ledger_path)
    if action == "main-agent-edit":
        _print_loop_ledger(loop)


def checks_repair_loop_main(argv: list[str] | None = None) -> int:
    parser = _RepairLoopArgumentParser(prog="cli.py checks repair-loop")
    _ = parser.add_argument("--tmpdir", required=True)
    _ = parser.add_argument("--site", required=True)
    _ = parser.add_argument("--checks-site", default="")
    _ = parser.add_argument("--checks-log", required=True)
    _ = parser.add_argument("--repo-root", default="")
    _ = parser.add_argument("--bgjob-launch", choices=("true", "false"), default="false")
    _ = parser.add_argument("--bgjob-merge-result-env", default="")
    args = parser.parse_args(argv)
    canonical_tmp = validate_tmpdir(args.tmpdir or os.environ.get(config.ENV_IMPLEMENT_TMPDIR, ""))
    if canonical_tmp is None:
        print("NEXT_ACTION=stall")
        print("LOOP_STATUS=tmpdir-validation")
        return 2
    lint_site = args.site
    capture_site = args.checks_site or lint_site
    if not _is_known_site(lint_site):
        print("NEXT_ACTION=stall")
        print("LOOP_STATUS=site-validation")
        return 2
    if not _valid_checks_site(capture_site):
        print("NEXT_ACTION=stall")
        print("LOOP_STATUS=checks-site-validation")
        return 2

    if args.bgjob_launch == "true":
        return _launch_repair_loop_bgjob(
            RepairLoopBgjobLaunch(
                tmpdir=canonical_tmp,
                site=lint_site,
                checks_site=args.checks_site,
                checks_log=args.checks_log,
                repo_root=args.repo_root,
            )
        )

    merge_result_env = Path(args.bgjob_merge_result_env) if args.bgjob_merge_result_env else None
    with _result_env_capture(merge_result_env):
        return _run_repair_loop_foreground(
            canonical_tmp=canonical_tmp,
            lint_site=lint_site,
            capture_site=capture_site,
            checks_log=args.checks_log,
            repo_root=args.repo_root or default_repo_root(),
        )


def _run_repair_loop_foreground(
    *,
    canonical_tmp: Path,
    lint_site: str,
    capture_site: str,
    checks_log: str,
    repo_root: str,
) -> int:
    runner = proc
    run_parent = str(canonical_tmp / "lint-fix-loop")

    def checks_runner() -> ChecksResult:
        return run_relevant_checks(
            runner,
            site=capture_site,
            tmpdir=str(canonical_tmp),
            repo_root=repo_root,
        )

    def fixer(log_path: str) -> FixOutcome:
        return run_lint_fix(
            runner,
            site=lint_site,
            checks_log=log_path,
            repo_root=repo_root,
            run_parent=run_parent,
            allowed_tmpdir=str(canonical_tmp),
        )

    print(f"PROGRESS=dispatching-lint-fix site={lint_site}", flush=True)
    stop_heartbeat = threading.Event()
    heartbeat = threading.Thread(
        target=_emit_repair_loop_heartbeat,
        kwargs={"stop": stop_heartbeat, "site": lint_site},
        daemon=True,
    )
    heartbeat.start()
    try:
        loop = run_check_fix_loop(
            checks_runner=checks_runner,
            fixer=fixer,
            dispatch_first=True,
            initial_redacted_log=checks_log,
            allowed_tmpdir=str(canonical_tmp),
        )
    except OSError:
        _emit_repair_kv(key="NEXT_ACTION", value="stall")
        _emit_repair_kv(key="LOOP_STATUS", value="callback-oserror")
        return 1
    finally:
        stop_heartbeat.set()
        heartbeat.join(timeout=_REPAIR_LOOP_HEARTBEAT_JOIN_TIMEOUT_S)
    _ = record_self_edits(
        tmpdir=canonical_tmp,
        source=f"lint-fix:{lint_site}",
        paths=loop.delta_paths,
        repo_root=repo_root,
    )
    action = _repair_loop_action(
        loop=loop,
        lint_site=lint_site,
        checks_log=checks_log,
        allowed_tmpdir=canonical_tmp,
    )
    _emit_repair_loop_outcome(action=action, loop=loop)
    return 0 if action in {"continue", "main-agent-edit"} else 1


def _is_known_site(site: str) -> bool:
    return site in _SITE_LABELS


def _is_pre_ship_site(site: str) -> bool:
    return site in _PRE_SHIP_SITES


def run_lint_fix(  # noqa: PLR0913 - dispatch verb preserves the loop fixer's explicit paths
    runner: Runner,
    *,
    site: str,
    checks_log: str,
    repo_root: str,
    run_parent: str,
    allowed_tmpdir: str | None = None,
) -> FixOutcome:
    """Dispatch the Rust-owned ``checks lint-fix`` verb and rebuild its outcome.

    The lint-fix engine (delegated coder waterfall, snapshots, tier ledger, and
    commit) is owned by Rust (#8625). The still-Python repair loop is a Rust
    consumer here: it runs the verb through ``scripts/larch.sh`` and rebuilds the
    ``FixOutcome`` it branches on from the verb's ``KEY=value`` stdout. The Rust
    verb re-probes tool presence and owns lane timing.
    """
    argv = [
        str(larch_entrypoint(plugin_root())),
        "checks",
        "lint-fix",
        "--tmpdir",
        allowed_tmpdir or "",
        "--site",
        site,
        "--checks-log",
        checks_log,
        "--repo-root",
        repo_root,
        "--run-parent",
        run_parent,
    ]
    result = runner.run(argv, cwd=repo_root)
    return _fix_outcome_from_stdout(result.stdout)


def _fix_outcome_from_stdout(stdout: str) -> FixOutcome:
    """Rebuild the ``FixOutcome`` the repair loop branches on from verb stdout."""
    text = "\n".join(stdout.splitlines())

    def value(key: str) -> str:
        return larch_io.kv_value(text=text, key=key, duplicate_policy="first").strip()

    status = value("LINT_FIX_STATUS") or "failed"
    delta_count_raw = value("LINT_FIX_DELTA_COUNT")
    delta_count = int(delta_count_raw) if delta_count_raw.isdigit() else 0
    delta_paths = tuple(
        path for i in range(delta_count) if (path := value(f"LINT_FIX_DELTA_PATH_{i}"))
    )
    exit_raw = value("LINT_FIX_LEDGER_EXIT_CODE")
    return FixOutcome(
        status=status,
        delta_paths=delta_paths,
        failure_reason=value("FAILURE_REASON") or None,
        commit_sha=None,
        head_changed=False,
        coder_tool=None,
        ledger_ready=value("LINT_FIX_LEDGER_READY") == "true",
        ledger_site=value("LINT_FIX_LEDGER_SITE"),
        ledger_trigger=value("LINT_FIX_LEDGER_TRIGGER"),
        ledger_step=value("LINT_FIX_LEDGER_STEP"),
        ledger_phase=value("LINT_FIX_LEDGER_PHASE"),
        ledger_dispatcher=value("LINT_FIX_LEDGER_DISPATCHER"),
        ledger_exit_code=int(exit_raw) if exit_raw.lstrip("-").isdigit() else None,
        ledger_failure_detail_log=value("LINT_FIX_LEDGER_FAILURE_DETAIL_LOG"),
        coder_log_path=value("CODER_LOG_FILE"),
        stderr_tail_path=value("STDERR_TAIL_PATH"),
        tier_ledger_path=value("LINT_FIX_TIER_LEDGER_PATH"),
    )


def _handle_fix_outcome(
    fix: FixOutcome,
    *,
    delta_accum: list[str],
    loop: LoopResult,
) -> bool:
    """Return True when the outer loop should continue."""
    loop.last_fix_status = fix.status
    loop.failure_reason = fix.failure_reason or ""
    loop.tier_ledger_path = fix.tier_ledger_path
    if fix.ledger_ready:
        loop.ledger_ready = True
        loop.ledger_site = fix.ledger_site
        loop.ledger_trigger = fix.ledger_trigger
        loop.ledger_step = fix.ledger_step
        loop.ledger_phase = fix.ledger_phase
        loop.ledger_dispatcher = fix.ledger_dispatcher
        loop.ledger_exit_code = fix.ledger_exit_code
        loop.ledger_failure_detail_log = fix.ledger_failure_detail_log
    if fix.status in {"applied", "no-changes"}:
        if fix.status == "applied":
            for path in fix.delta_paths:
                if path not in delta_accum:
                    delta_accum.append(path)
        return True
    if fix.status == "main-agent-required":
        loop.status = "main-agent-required"
        loop.stderr_tail_path = fix.stderr_tail_path
        loop.coder_log_path = fix.coder_log_path
        return False
    if fix.status == "failed":
        # A delegated waterfall can fail before re-running checks, so there is
        # no later capture to populate final_redacted_checks_log. Keep its
        # redacted input as the candidate; _repair_loop_action validates it
        # against the session root before using it for an escalation.
        loop.final_redacted_checks_log = fix.ledger_failure_detail_log
        if fix.failure_reason in _PRE_SHIP_NON_STRUCTURAL_REASONS:
            loop.status = "exhausted"
        elif fix.failure_reason == "head-changed-after-dispatch":
            loop.status = "head-changed"
            loop.stderr_tail_path = fix.stderr_tail_path
            loop.coder_log_path = fix.coder_log_path
        else:
            loop.status = "main-agent-required"
            loop.stderr_tail_path = fix.stderr_tail_path
            loop.coder_log_path = fix.coder_log_path
        return False
    loop.status = "dispatch-failed"
    loop.stderr_tail_path = fix.stderr_tail_path
    loop.coder_log_path = fix.coder_log_path
    return False


def _fallback_redacted_path(raw: Path) -> Path:
    """On-demand redacted log path (capture uses ``<site>-<n>.redacted.log``)."""
    if raw.name.endswith(".log"):
        return raw.with_name(f"{raw.name[:-4]}.redacted.log")
    return raw.with_suffix(raw.suffix + ".redacted")


def _status_for_missing_redacted_log(  # noqa: PLR0911,RUF100
    checks: ChecksResult,
    *,
    allowed_tmpdir: Path | None,
    dispatch_first_post_apply: bool,
) -> str:
    """Map a failed redacted-log resolution to loop.status (bash parity)."""
    if checks.warn == "redaction-failed":
        return "dispatch-failed"
    if checks.redacted_log_path:
        redacted = Path(checks.redacted_log_path)
        if allowed_tmpdir is not None and resolve_checks_log_path(candidate=str(redacted), allowed_root=allowed_tmpdir) is None:
            return "dispatch-failed"
        if redacted.is_file() and not redacted.is_symlink():
            return "dispatch-failed"
    raw_path = checks.raw_log_path
    if not raw_path:
        return "exhausted" if dispatch_first_post_apply else "dispatch-failed"
    raw = Path(raw_path)
    if allowed_tmpdir is not None and resolve_checks_log_path(candidate=str(raw), allowed_root=allowed_tmpdir) is None:
        return "dispatch-failed"
    try:
        if not raw.is_file() or raw.is_symlink() or raw.stat().st_size == 0:
            return "exhausted" if dispatch_first_post_apply else "dispatch-failed"
    except OSError:
        return "exhausted" if dispatch_first_post_apply else "dispatch-failed"
    return "dispatch-failed"


def _redacted_log_for_dispatch(  # noqa: C901,PLR0911,PLR0912,RUF100
    checks: ChecksResult,
    *,
    allowed_tmpdir: Path | None,
) -> str | None:
    if checks.warn == "redaction-failed":
        return None
    if checks.redacted_log_path:
        redacted = Path(checks.redacted_log_path)
        if allowed_tmpdir is not None and resolve_checks_log_path(candidate=str(redacted), allowed_root=allowed_tmpdir) is None:
            return None
        if redacted.is_file() and not redacted.is_symlink():
            return str(redacted)
        return None
    raw_path = checks.raw_log_path
    if not raw_path:
        return None
    raw = Path(raw_path)
    if allowed_tmpdir is not None and resolve_checks_log_path(candidate=str(raw), allowed_root=allowed_tmpdir) is None:
        return None
    try:
        if not raw.is_file() or raw.is_symlink() or raw.stat().st_size == 0:
            return None
    except OSError:
        return None
    log_text = read_log_file_text(raw)
    if log_text is None:
        return None
    redacted = _fallback_redacted_path(raw)
    try:
        _ = redacted.write_text(redact.redact(log_text), encoding="utf-8")
        redacted.chmod(0o600)
    except OSError:
        with contextlib.suppress(OSError):
            redacted.unlink(missing_ok=True)
        return None
    if allowed_tmpdir is not None and resolve_checks_log_path(candidate=str(redacted), allowed_root=allowed_tmpdir) is None:
        return None
    return str(redacted)


def run_check_fix_loop(  # noqa: PLR0911,PLR0912,PLR0913,PLR0915,RUF100
    *,
    checks_runner: Callable[[], ChecksResult],
    fixer: Callable[[str], FixOutcome],
    dispatch_first: bool = False,
    max_iter: int | None = None,
    initial_redacted_log: str | None = None,
    allowed_tmpdir: str | None = None,
) -> LoopResult:
    """Port of run_captured_cmd_then_fix_loop."""
    cap = normalize_max_iter(max_iter)
    loop = LoopResult(status="exhausted")
    delta_accum: list[str] = []
    empty_failures = 0
    canonical_tmp = Path(allowed_tmpdir) if allowed_tmpdir else None
    if (dispatch_first or initial_redacted_log) and canonical_tmp is None:
        return LoopResult(status="dispatch-failed")
    redacted_log_for_dispatch = initial_redacted_log or ""
    if redacted_log_for_dispatch and canonical_tmp is not None:
        resolved = resolve_checks_log_path(candidate=redacted_log_for_dispatch, allowed_root=canonical_tmp)
        redacted_log_for_dispatch = str(resolved) if resolved is not None else ""

    for _ in range(1, cap + 1):
        if dispatch_first:
            if not redacted_log_for_dispatch or not Path(redacted_log_for_dispatch).is_file():
                loop.status = "dispatch-failed"
                loop.delta_paths = tuple(delta_accum)
                return loop
            fix = fixer(redacted_log_for_dispatch)
            if not _handle_fix_outcome(fix, delta_accum=delta_accum, loop=loop):
                loop.delta_paths = tuple(delta_accum)
                return loop
            checks = checks_runner()
            if checks.ok or checks.skipped:
                loop.status = "ok"
                loop.delta_paths = tuple(delta_accum)
                return loop
            loop.final_redacted_checks_log = ""
            redacted_path = _redacted_log_for_dispatch(
                checks,
                allowed_tmpdir=canonical_tmp,
            )
            if redacted_path is None:
                loop.status = _status_for_missing_redacted_log(
                    checks,
                    allowed_tmpdir=canonical_tmp,
                    dispatch_first_post_apply=True,
                )
                loop.delta_paths = tuple(delta_accum)
                return loop
            loop.final_redacted_checks_log = redacted_path
            redacted_log_for_dispatch = redacted_path
        else:
            checks = checks_runner()
            if checks.ok or checks.skipped:
                loop.status = "ok"
                loop.delta_paths = tuple(delta_accum)
                return loop
            if checks.warn == "redaction-failed":
                loop.status = "dispatch-failed"
                loop.delta_paths = tuple(delta_accum)
                return loop
            raw_path = checks.raw_log_path
            if not raw_path or not Path(raw_path).is_file() or Path(raw_path).stat().st_size == 0:
                empty_failures += 1
                if empty_failures >= _EMPTY_FAILURE_CAP:
                    loop.status = "exhausted"
                    loop.delta_paths = tuple(delta_accum)
                    return loop
                continue
            empty_failures = 0
            redacted_path = _redacted_log_for_dispatch(
                checks,
                allowed_tmpdir=canonical_tmp,
            )
            if redacted_path is None:
                loop.status = _status_for_missing_redacted_log(
                    checks,
                    allowed_tmpdir=canonical_tmp,
                    dispatch_first_post_apply=False,
                )
                loop.delta_paths = tuple(delta_accum)
                return loop
            fix = fixer(redacted_path)
            if not _handle_fix_outcome(fix, delta_accum=delta_accum, loop=loop):
                loop.delta_paths = tuple(delta_accum)
                return loop
            if loop.last_fix_status == "no-changes":
                recheck = checks_runner()
                if recheck.ok or recheck.skipped:
                    loop.status = "ok"
                    loop.delta_paths = tuple(delta_accum)
                    return loop
                loop.status = "no-changes-stale"
                loop.delta_paths = tuple(delta_accum)
                return loop
    loop.status = "no-changes-stale" if loop.last_fix_status == "no-changes" else "exhausted"
    loop.delta_paths = tuple(delta_accum)
    return loop


def escalate(status: str, *, delta_paths: tuple[str, ...] = (), loop: LoopResult | None = None) -> StepResult:
    """Map loop terminal status to StepResult."""
    def make_step(*, outcome: Outcome, detail: str = "") -> StepResult:
        if loop is None or not loop.ledger_ready:
            return StepResult(outcome, detail, payload=delta_paths)
        return StepResult(
            outcome,
            detail,
            payload=delta_paths,
            ledger_ready=loop.ledger_ready,
            ledger_site=loop.ledger_site,
            ledger_trigger=loop.ledger_trigger,
            ledger_step=loop.ledger_step,
            ledger_phase=loop.ledger_phase,
            ledger_dispatcher=loop.ledger_dispatcher,
            ledger_exit_code=loop.ledger_exit_code,
            ledger_failure_detail_log=loop.ledger_failure_detail_log,
        )

    if status == "ok":
        return make_step(outcome=Outcome.OK)
    if status in {"exhausted", "no-changes-stale"}:
        return make_step(outcome=Outcome.STALLED, detail=status)
    if status == "main-agent-required":
        detail = (
            config.NEEDS_USER_SHIP_PR_INTERNAL_LINT_FIX
            if loop and loop.ledger_trigger == config.NEEDS_USER_SHIP_PR_INTERNAL_LINT_FIX
            else status
        )
        return make_step(outcome=Outcome.NEEDS_USER_INPUT, detail=detail)
    return make_step(outcome=Outcome.TRANSIENT, detail=status)


