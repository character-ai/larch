# pyright: reportUnusedFunction=false, reportUnusedCallResult=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportPrivateUsage=false
"""Step 18: resolve stalls, prepare the terminal snapshot, and publish it."""

from __future__ import annotations

import argparse
import contextlib
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from larch import io as larch_io
from larch.core import config
from larch.core import proc
from larch.core.repo_roots import larch_entrypoint
from larch.errors import ShipError
from larch.implement.dispatch_helpers import (
    _emit_kv,
    _invoke_cli,
    _invoke_larch,
    _parse_kv,
    _read_kv_file,
    _read_session_key_default,
    _rehydrate_larch_triplet,
    _rehydrate_plugin_root,
)
from larch.implement.dispatch_leg import _run_cli_capture, _run_larch_capture
from larch.issue import execution_issues
from larch.report import run_log_batch
from larch.state import finalize
from larch.state._tokens import _abandoned_checks_bgjob_stall_step


_TERMINAL_SHIPPING_REFUSAL_REASON = "step18-terminal-shipping-without-pr"
_TERMINAL_SHIPPING_REFUSAL_ENTRY = (
    "- **Step 18 terminal gate**: refused terminal `shipping` without PR evidence; "
    "preserved the session for stall recovery."
)
_LIFECYCLE_VERB_BY_ACTION = {
    "cancel": "lifecycle-cancel",
    "failure": "lifecycle-failure",
    "finalize": "lifecycle-finalize",
}


def _stall_layer_active(value: str) -> bool:
    return bool(value) and value != "false"


def _resolve_stall_memory_layer(*, stall_tracking_memory_arg: str, env_stall_tracking: str) -> str:
    if stall_tracking_memory_arg in {"true", "false"}:
        return stall_tracking_memory_arg
    if stall_tracking_memory_arg == "":
        return env_stall_tracking or "false"
    return stall_tracking_memory_arg


def _read_stall_layer_from_file(*, path: Path, key: str, default: str = "false") -> str:
    if not path.is_file():
        return default
    return _read_kv_file(path=path, key=key, default=default)


@dataclass(frozen=True)
class StallLayers:
    memory: str
    disk: str
    finalize: str
    session: str
    abandoned_checks_bgjob: str

    def any_active(self) -> bool:
        return any(
            _stall_layer_active(value)
            for value in (self.memory, self.disk, self.finalize, self.session, self.abandoned_checks_bgjob)
        )


def _resolve_stall_layers(implement_tmpdir: Path, *, stall_tracking_memory_arg: str) -> StallLayers:
    return StallLayers(
        memory=_resolve_stall_memory_layer(
            stall_tracking_memory_arg=stall_tracking_memory_arg,
            env_stall_tracking=os.environ.get("STALL_TRACKING", "false"),
        ),
        disk=_read_stall_layer_from_file(path=implement_tmpdir / "ship-pr-state.sh", key="STALL_TRACKING"),
        finalize=_read_stall_layer_from_file(path=implement_tmpdir / "finalize-state.sh", key="STALL_TRACKING"),
        session=_read_stall_layer_from_file(path=implement_tmpdir / "session-env.sh", key="STALL_TRACKING"),
        abandoned_checks_bgjob="true" if _abandoned_checks_bgjob_stall_step(implement_tmpdir) else "false",
    )


def _emit_stall_layers(layers: StallLayers) -> None:
    _emit_kv(key="STALL_TRACKING_MEMORY", value=layers.memory)
    _emit_kv(key="STALL_TRACKING_DISK", value=layers.disk)
    _emit_kv(key="STALL_TRACKING_FINALIZE", value=layers.finalize)
    _emit_kv(key="STALL_TRACKING_SESSION", value=layers.session)
    _emit_kv(key="STALL_TRACKING_ABANDONED_MARKER", value=layers.abandoned_checks_bgjob)


def _normalize_outcome_for_step18(implement_tmpdir: Path, *, memory_layer: str, env: dict[str, str]) -> dict[str, str]:
    result = proc.run(
        [
            str(larch_entrypoint(Path(__file__).resolve().parents[3])),
            "stall-recovery",
            "normalize-outcome",
            "--implement-tmpdir",
            str(implement_tmpdir),
            "--in-memory-stall-tracking",
            memory_layer,
        ],
        env=env,
    )
    if result.stderr:
        sys.stderr.write(result.stderr)
        sys.stderr.flush()
    if result.stdout:
        sys.stdout.write(result.stdout)
        sys.stdout.flush()
    return _parse_kv(result.stdout if result.returncode == 0 else "")


def _is_terminal_shipping_without_pr(normalized: dict[str, str]) -> bool:
    return (
        normalized.get("IMPLEMENT_NORMALIZED_OUTCOME") == "shipping"
        and not normalized.get("IMPLEMENT_PR_NUMBER", "").strip()
    )


def _record_terminal_shipping_refusal(*, implement_tmpdir: Path) -> bool:
    """Persist the terminal-gate refusal before returning a hard failure.

    ``shipping`` is only valid for a committed, pre-PR snapshot.  Once Step 18
    starts terminal finalization, retaining that label would otherwise permit a
    teardown that loses the session needed to recover the failed ship attempt.
    """
    state_path = implement_tmpdir / "finalize-state.sh"
    if state_path.is_symlink():
        return False
    try:
        state: dict[str, str] = finalize.read_finalize_state(state_path)
        state.update(
            {
                "BAIL_REASON": _TERMINAL_SHIPPING_REFUSAL_REASON,
                "EXIT_CODE": str(config.EXIT_INTERNAL_ERROR),
                "PHASE": "stalled",
                "STALL_STEP": "8",
                "STALL_TRACKING": "true",
                "STEP18_GATE_REFUSAL": _TERMINAL_SHIPPING_REFUSAL_REASON,
            }
        )
        finalize.write_finalize_state_merged(path=state_path, data=state)
        persisted: dict[str, str] = finalize.read_finalize_state(state_path)
        expected = {
            "BAIL_REASON": _TERMINAL_SHIPPING_REFUSAL_REASON,
            "EXIT_CODE": str(config.EXIT_INTERNAL_ERROR),
            "PHASE": "stalled",
            "STALL_STEP": "8",
            "STALL_TRACKING": "true",
            "STEP18_GATE_REFUSAL": _TERMINAL_SHIPPING_REFUSAL_REASON,
        }
        if any(persisted.get(key) != value for key, value in expected.items()):
            return False
        issue_log = implement_tmpdir / "execution-issues.md"
        execution_issues.append_execution_issue(
            issue_log,
            category="Tool Failures",
            entry=_TERMINAL_SHIPPING_REFUSAL_ENTRY,
        )
        return _TERMINAL_SHIPPING_REFUSAL_ENTRY in issue_log.read_text(encoding="utf-8")
    except (OSError, ShipError):
        return False


def _append_failure_best_effort(*, implement_tmpdir: Path, site: str, tool: str, rc: int, log: Path) -> None:
    if not log.is_file():
        try:
            log.write_text("", encoding="utf-8")
        except OSError:
            return
    _ = _invoke_larch([
        "run-log", "append-failure",
        "--log", str(implement_tmpdir / "execution-issues.md"),
        "--site", site,
        "--tool", tool,
        "--exit-code", str(rc),
        "--category", "Tool Failures",
        "--output-file", str(log),
        "--redact",
    ])


def _print_summary_markers(implement_tmpdir: Path) -> int:
    summary_path = implement_tmpdir / "summary-final.md"
    print("---LARCH-SUMMARY-FINAL-BEGIN---")
    try:
        body = summary_path.read_text(encoding="utf-8")
    except OSError:
        return 1
    sys.stdout.write(body)
    if body and not body.endswith("\n"):
        sys.stdout.write("\n")
    print("---LARCH-SUMMARY-FINAL-END---")
    (implement_tmpdir / ".step17-emitted").touch()
    return 0


def _terminal_publication_suppressed(implement_tmpdir: Path) -> bool:
    for name in ("finalize-state.sh", "run-flags.sh", "session-env.sh"):
        if _read_kv_file(path=implement_tmpdir / name, key="NO_LOGS_COMMIT", default="false") == "true":
            return True
    return False


def _terminal_publication_repo_root(implement_tmpdir: Path) -> Path | None:
    for name in ("session-env.sh", "ship-pr-state.sh", "finalize-state.sh"):
        raw: str = _read_kv_file(path=implement_tmpdir / name, key="REPO_ROOT", default="").strip()
        if not raw:
            continue
        root: Path = Path(raw)
        if not root.is_absolute():
            continue
        try:
            return larch_io.validate_trusted_directory(root)
        except OSError:
            continue
    return None


def _terminal_lifecycle_action(*, implement_tmpdir: Path, wfr_rc: str) -> str:
    if wfr_rc != "0":
        return "failure"
    summary = implement_tmpdir / "summary-final.md"
    if not summary.is_file():
        return "failure"
    try:
        summary_text = summary.read_text(encoding="utf-8", errors="replace")
    except OSError:
        summary_text = ""
    label = run_log_batch.parse_preterminal_outcome_label(summary_text)
    if label is None:
        return "failure"
    if "cancel" in label:
        return "cancel"
    if any(token in label for token in ("bail", "fail", "stall")):
        return "failure"
    return "finalize"


def _write_terminalization_record(*, implement_tmpdir: Path, publication: str) -> bool:
    try:
        larch_io.atomic_write(
            path=implement_tmpdir / ".run-log-terminalized",
            text=(f"RUN_LOG_TERMINALIZED=true\nRUN_LOG_PUBLICATION={publication}\nLIFECYCLE_TERMINALIZED=true\n"),
            nofollow=True,
            mode=0o600,
        )
    except OSError:
        return False
    return True


def _publish_terminal_archive(*, implement_tmpdir: Path, run_id: str, lifecycle_action: str) -> int:
    repo_root: Path | None = _terminal_publication_repo_root(implement_tmpdir)
    if repo_root is None:
        print("Step 18: run-log publication failed: persisted REPO_ROOT is unavailable", file=sys.stderr)
        _emit_kv(key="RUN_LOG_PUBLISH_OK", value="false")
        return config.EXIT_INTERNAL_ERROR
    publish = _run_larch_capture(
        [
            "run-log",
            _LIFECYCLE_VERB_BY_ACTION[lifecycle_action],
            "--repo-root",
            str(repo_root),
            "--skill",
            "implement",
            "--run-id",
            run_id,
        ],
        cwd=repo_root,
    )
    if publish.stderr:
        sys.stderr.write(publish.stderr)
        sys.stderr.flush()
    publication_values: dict[str, str] = _parse_kv(publish.stdout or "")
    cache_dir_raw: str = publication_values.get("CACHE_DIR", "")
    cache_dir: Path | None = Path(cache_dir_raw) if cache_dir_raw else None
    published: bool = (
        publication_values.get("RUN_LOG_PUBLICATION") == "published"
        and publication_values.get("LIFECYCLE_FLUSHED") == "true"
        and bool(publication_values.get("REMOTE_KEY"))
        and cache_dir is not None
        and cache_dir.is_dir()
    )
    skipped_disabled: bool = (
        publication_values.get("RUN_LOG_PUBLICATION") == "skipped-disabled"
        and publication_values.get("LIFECYCLE_FLUSHED") == "false"
        and not publication_values.get("REMOTE_KEY")
        and cache_dir is None
    )
    postcondition_ok: bool = (
        publish.returncode == 0
        and publication_values.get("LIFECYCLE_TERMINALIZED") == "true"
        and (published or skipped_disabled)
    )
    if not postcondition_ok:
        print(
            f"Step 18: run-log publication failed (rc={publish.returncode}); "
            "durable pending state and the session staging tree were retained for retry.",
            file=sys.stderr,
        )
        _emit_kv(key="RUN_LOG_PUBLISH_OK", value="false")
        return publish.returncode or config.EXIT_INTERNAL_ERROR
    publication = publication_values.get("RUN_LOG_PUBLICATION", "")
    if not _write_terminalization_record(implement_tmpdir=implement_tmpdir, publication=publication):
        print(
            "Step 18: run-log publication succeeded, but terminalization could not be recorded for cleanup.",
            file=sys.stderr,
        )
        _emit_kv(key="RUN_LOG_PUBLISH_OK", value="false")
        return config.EXIT_INTERNAL_ERROR
    if publish.stdout:
        sys.stdout.write(publish.stdout)
        if not publish.stdout.endswith("\n"):
            sys.stdout.write("\n")
        sys.stdout.flush()
    _emit_kv(key="RUN_LOG_PUBLISH_OK", value="true")
    return 0


def _complete_terminal_run_log(*, implement_tmpdir: Path, run_id: str, emit_body: str, wfr_rc: str) -> int:
    suppressed = _terminal_publication_suppressed(implement_tmpdir)
    repo_root = _terminal_publication_repo_root(implement_tmpdir)
    prepare_rc = _prepare_terminal_snapshot(
        implement_tmpdir=implement_tmpdir, run_id=run_id, suppressed=suppressed, repo_root=repo_root
    )
    if prepare_rc != 0:
        return prepare_rc
    if suppressed:
        publish_rc = _record_suppressed_terminalization(implement_tmpdir=implement_tmpdir)
    else:
        publish_rc = _publish_terminal_archive(
            implement_tmpdir=implement_tmpdir,
            run_id=run_id,
            lifecycle_action=_terminal_lifecycle_action(implement_tmpdir=implement_tmpdir, wfr_rc=wfr_rc),
        )
    if publish_rc != 0:
        return publish_rc
    summary = implement_tmpdir / "summary-final.md"
    if emit_body == "true" and wfr_rc == "0" and summary.is_file() and summary.stat().st_size > 0:
        _ = _print_summary_markers(implement_tmpdir)
    return 0


def _prepare_terminal_snapshot(*, implement_tmpdir: Path, run_id: str, suppressed: bool, repo_root: Path | None) -> int:
    if not run_id:
        print("Step 18: run-log publication failed: LARCH_RUN_ID is unavailable", file=sys.stderr)
        _emit_kv(key="RUN_LOG_FINAL_FLUSH_OK", value="false")
        _emit_kv(key="RUN_LOG_PUBLISH_OK", value="false")
        return config.EXIT_INTERNAL_ERROR
    prepare_args = [
        "run-log",
        "prepare-terminal-snapshot",
        "--implement-tmpdir",
        str(implement_tmpdir),
        "--run-id",
        run_id,
        "--no-logs-commit",
        str(suppressed).lower(),
    ]
    if repo_root is not None:
        prepare_args.extend(["--repo-root", str(repo_root)])
    prepare = _run_cli_capture(prepare_args, cwd=repo_root)
    if prepare.stderr:
        sys.stderr.write(prepare.stderr)
        sys.stderr.flush()
    prepare_values = _parse_kv(prepare.stdout or "")
    for line in (prepare.stdout or "").splitlines():
        if line.startswith(("SESSION_TRANSCRIPT_STATUS=", "TERMINAL_SNAPSHOT_")):
            print(line)
    prepared = prepare.returncode == 0 and prepare_values.get("TERMINAL_SNAPSHOT_STATUS") == "prepared"
    if not prepared:
        print(
            f"Step 18: terminal snapshot preparation failed (rc={prepare.returncode}); "
            "the session staging tree was retained for retry.",
            file=sys.stderr,
        )
        _emit_kv(key="RUN_LOG_FINAL_FLUSH_OK", value="false")
        _emit_kv(key="RUN_LOG_PUBLISH_OK", value="false")
        return prepare.returncode or config.EXIT_INTERNAL_ERROR
    _emit_kv(key="RUN_LOG_FINAL_FLUSH_OK", value="true")
    return 0


def _record_suppressed_terminalization(*, implement_tmpdir: Path) -> int:
    _emit_kv(key="RUN_LOG_PUBLISH_SKIPPED", value="no-logs-commit")
    _emit_kv(key="RUN_LOG_PUBLICATION", value="skipped-suppressed")
    _emit_kv(key="LIFECYCLE_FLUSHED", value="false")
    _emit_kv(key="LIFECYCLE_TERMINALIZED", value="true")
    if not _write_terminalization_record(implement_tmpdir=implement_tmpdir, publication="skipped-suppressed"):
        print("Step 18: suppressed terminalization could not be recorded for cleanup.", file=sys.stderr)
        _emit_kv(key="RUN_LOG_PUBLISH_OK", value="false")
        return config.EXIT_INTERNAL_ERROR
    _emit_kv(key="RUN_LOG_PUBLISH_OK", value="true")
    return 0


def _step18_gate(*, implement_tmpdir: Path, stall_tracking_memory: str) -> int:
    layers = _resolve_stall_layers(implement_tmpdir, stall_tracking_memory_arg=stall_tracking_memory)
    _emit_kv(key="STALL_TRACKING_MEMORY", value=layers.memory)
    _emit_kv(key="STALL_TRACKING_DISK", value=layers.disk)
    _emit_kv(key="STALL_TRACKING_FINALIZE", value=layers.finalize)
    _emit_kv(key="STALL_TRACKING_SESSION", value=layers.session)
    if any(_stall_layer_active(value) for value in (layers.memory, layers.disk, layers.finalize, layers.session)):
        _emit_kv(key="STALL_RECOVERY_REQUIRED", value="true")
        return 0
    _emit_kv(key="STALL_RECOVERY_REQUIRED", value="false")
    print("⏩ 18a: stall recovery; no stall detected")
    return 0


def _step18_logs_flush(*, implement_tmpdir: Path, step17_emitted: str) -> int:
    if step17_emitted == "true":
        (implement_tmpdir / ".step17-emitted").touch()

    step18b_out = implement_tmpdir / "step18b-final-report.stdout"
    step18b_err = implement_tmpdir / "step18b-final-report.stderr"
    with contextlib.suppress(OSError):
        step18b_err.write_text("", encoding="utf-8")
    result = _run_cli_capture([
        "final-report", "step18b",
        "--implement-tmpdir", str(implement_tmpdir),
        "--step17-emitted", step17_emitted,
    ])
    try:
        step18b_out.write_text(result.stdout or "", encoding="utf-8")
        if result.stderr:
            step18b_err.write_text(result.stderr, encoding="utf-8")
    except OSError:
        pass
    values = _parse_kv(result.stdout or "")
    emit_body = values.get("EMIT_BODY", "false") or "false"
    wfr_rc = values.get("WFR_RC", "") or str(result.returncode)
    step17_present = values.get("STEP17_EMITTED_PRESENT", "false") or "false"
    snapshot_ok = values.get("SNAPSHOT_OK", "absent") or "absent"
    wfr_error = values.get("ERROR", "")
    if result.returncode != 0:
        _append_failure_best_effort(
            implement_tmpdir=implement_tmpdir,
            site="Step 18b — final-report",
            tool="python/cli.py final-report step18b",
            rc=result.returncode,
            log=step18b_err,
        )
    _emit_kv(key="EMIT_BODY", value=emit_body)
    _emit_kv(key="WFR_RC", value=wfr_rc)
    _emit_kv(key="STEP17_EMITTED_PRESENT", value=step17_present)
    _emit_kv(key="SNAPSHOT_OK", value=snapshot_ok)
    _emit_kv(key="ERROR", value=wfr_error)
    if wfr_rc != "0":
        reason = wfr_error or "render failed (no reason surfaced)"
        print(f"**⚠ Step 18: final report render failed (WFR_RC={wfr_rc}): {reason}.**", file=sys.stderr)
    _ = _invoke_cli(["token", "report", "--since-last-mark", "--terse"])
    timing_env = {**os.environ, "DESIGN_TMPDIR": "", "LARCH_TIMING_SKILL": "implement"}
    _ = _run_cli_capture(["timing", "report", "--since-last-mark", "--terse"], env=timing_env)
    _ = _invoke_cli(["token", "mark", "Step 18 — logs flush"])
    _ = _run_cli_capture(["timing", "mark", "Step 18 — logs flush"], env=timing_env)

    run_id = os.environ.get("RUN_ID") or _read_session_key_default(implement_tmpdir=implement_tmpdir, key="LARCH_RUN_ID", default="")
    run_log_rc = _complete_terminal_run_log(
        implement_tmpdir=implement_tmpdir,
        run_id=run_id,
        emit_body=emit_body,
        wfr_rc=wfr_rc,
    )
    if run_log_rc != 0:
        return run_log_rc
    return 0


def step_18_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py implement step-18")
    parser.add_argument("--phase", choices=("gate", "logs-flush"), default="gate")
    parser.add_argument("--stall-tracking-memory", default="")
    parser.add_argument("--step17-emitted", choices=("true", "false"), default="false")
    args = parser.parse_args(argv)
    implement_tmpdir_raw = os.environ.get(config.ENV_IMPLEMENT_TMPDIR, "")
    if not implement_tmpdir_raw:
        print("implement step-18: IMPLEMENT_TMPDIR is required", file=sys.stderr)
        return 2
    implement_tmpdir = Path(implement_tmpdir_raw)
    plugin_root = _rehydrate_plugin_root(implement_tmpdir)
    if not plugin_root.is_dir():
        print(f"step-18: CLAUDE_PLUGIN_ROOT not found: {plugin_root}", file=sys.stderr)
        return 2
    _rehydrate_larch_triplet(implement_tmpdir)
    run_id = os.environ.get("RUN_ID") or _read_session_key_default(implement_tmpdir=implement_tmpdir, key="LARCH_RUN_ID", default="")
    if run_id:
        os.environ["RUN_ID"] = run_id
    if args.phase == "gate":
        return _step18_gate(implement_tmpdir=implement_tmpdir, stall_tracking_memory=args.stall_tracking_memory)
    return _step18_logs_flush(implement_tmpdir=implement_tmpdir, step17_emitted=args.step17_emitted)


def step_18_gate_logs_flush_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py implement step-18-gate-logs-flush")
    parser.add_argument("--implement-tmpdir", default="")
    parser.add_argument("--stall-tracking-memory", default="")
    parser.add_argument("--step17-emitted", choices=("true", "false"), default="false")
    args = parser.parse_args(argv)
    raw_tmpdir = args.implement_tmpdir or os.environ.get(config.ENV_IMPLEMENT_TMPDIR, "")
    if not raw_tmpdir:
        print(
            "implement step-18-gate-logs-flush: --implement-tmpdir is required or IMPLEMENT_TMPDIR must be set",
            file=sys.stderr,
        )
        return 2
    implement_tmpdir = Path(raw_tmpdir)
    os.environ[config.ENV_IMPLEMENT_TMPDIR] = str(implement_tmpdir)
    plugin_root = _rehydrate_plugin_root(implement_tmpdir)
    _rehydrate_larch_triplet(implement_tmpdir)
    env = dict(os.environ)
    env[config.ENV_IMPLEMENT_TMPDIR] = str(implement_tmpdir)
    env["CLAUDE_PLUGIN_ROOT"] = str(plugin_root)

    layers = _resolve_stall_layers(implement_tmpdir, stall_tracking_memory_arg=args.stall_tracking_memory)
    _emit_stall_layers(layers)
    if layers.any_active():
        _emit_kv(key="STALL_RECOVERY_REQUIRED", value="true")
        _emit_kv(key="NEXT_ACTION", value="stall-recovery")
        return 0

    print("⏩ 18a: stall recovery; no stall detected")
    normalized = _normalize_outcome_for_step18(implement_tmpdir, memory_layer=layers.memory, env=env)
    if _is_terminal_shipping_without_pr(normalized):
        persisted = _record_terminal_shipping_refusal(implement_tmpdir=implement_tmpdir)
        _emit_kv(key="STALL_RECOVERY_REQUIRED", value="true" if persisted else "unknown")
        _emit_kv(key="TERMINAL_FINALIZE_REFUSED", value="true")
        _emit_kv(key="STATUS", value="blocked")
        _emit_kv(key="OUTCOME", value="stalled")
        _emit_kv(key="NEXT_ACTION", value="tool-failure")
        if not persisted:
            print("implement step-18-gate-logs-flush: cannot persist terminal shipping refusal", file=sys.stderr)
        return config.EXIT_INTERNAL_ERROR

    _emit_kv(key="STALL_RECOVERY_REQUIRED", value="false")
    logs_flush_rc = _step18_logs_flush(implement_tmpdir=implement_tmpdir, step17_emitted=args.step17_emitted)
    _emit_kv(key="NEXT_ACTION", value="logs-flush-done" if logs_flush_rc == 0 else "logs-flush-failed")
    return logs_flush_rc
