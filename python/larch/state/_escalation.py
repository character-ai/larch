"""Escalation artifact utilities and escalation recording for stall recovery."""

# pyright: reportUnusedCallResult=false
# pyright: reportPrivateUsage=false
# pyright: reportUnusedFunction=false

from __future__ import annotations

import argparse
import contextlib
import os
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

from larch.report import run_logs  # pylint: disable=cyclic-import
from larch.state._tokens import (
    _DEFAULT_ESCALATION_FALLBACK,
    _DEFAULT_RECORD_FAILURE_MARKER,
    _safe_dispatcher_value,
    _safe_token,
    _validate_tmpdir_write_path,
    emit,
)
from larch.state._detail_log import (
    _materialize_truncated_failure_detail_log,
    classify_failure_detail_log,
)


def _validate_artifact_prefix(prefix: str) -> bool:
    if not prefix:
        return True
    return bool(re.fullmatch(r"[A-Za-z0-9]+(-[A-Za-z0-9]+)*", prefix))


def _artifact_path(*, tmpdir: Path, default_name: str, prefix: str) -> Path:
    if not prefix or prefix == "stall-recovery":
        return tmpdir / default_name
    return tmpdir / (prefix + default_name.removeprefix("stall-recovery"))


def _append_ledger_row_atomic(*, ledger: Path, row: str) -> bool:
    ledger.parent.mkdir(parents=True, exist_ok=True)
    old = ledger.read_text(encoding="utf-8") if ledger.is_file() else ""
    if old and not old.endswith("\n"):
        old += "\n"
    content = old + row
    tmp = ledger.with_suffix(ledger.suffix + ".tmp")
    try:
        tmp.write_text(content, encoding="utf-8")
        tmp.replace(ledger)
        written = ledger.read_text(encoding="utf-8")
        return row.rstrip("\n") in written
    except OSError:
        with contextlib.suppress(OSError):
            tmp.unlink(missing_ok=True)
        return False


def _resolve_detail_log(*, tmpdir: Path, detail_log: str) -> tuple[str, str]:
    if not detail_log:
        return "", ""
    detail_path = Path(detail_log)
    suffix = classify_failure_detail_log(tmpdir=tmpdir, path=detail_path)
    if not suffix:
        try:
            rel = detail_path.resolve().relative_to(tmpdir.resolve())
            return str(rel), ""
        except ValueError:
            return "redacted", ""
    if suffix == "oversize":
        sidecar_log = _materialize_truncated_failure_detail_log(tmpdir=tmpdir, path=detail_path)
        if sidecar_log is not None:
            return sidecar_log, ""
        return "", "failure-detail-log-truncate-failed"
    return "", f"failure-detail-log-{suffix}"


def _record_escalation_tool_failure_present(tmpdir: Path) -> bool:
    execution = tmpdir / "execution-issues.md"
    if not execution.is_file() or execution.is_symlink():
        return False
    return bool(re.search(r"^#{2,3}\s+Tool Failure: record-escalation(\s|$)", execution.read_text(encoding="utf-8", errors="replace"), re.MULTILINE))


def _append_record_escalation_tool_failure(*, tmpdir: Path, reason: str) -> None:
    execution = tmpdir / "execution-issues.md"
    if not _validate_tmpdir_write_path(tmpdir=tmpdir, path=execution):
        return
    ts = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    entry = (
        f"\n## Tool Failure: record-escalation\n\n"
        f"- utc: `{ts}`\n"
        f"- helper: `python/cli.py stall-recovery record-escalation`\n"
        f"- reason: `{reason}`\n"
    )
    with contextlib.suppress(OSError):
        run_logs.append_execution_issue(log_file=execution, category="Tool Failures", entry=entry)


def record_escalation(args: argparse.Namespace) -> int:
    tmpdir = Path(args.implement_tmpdir)
    prefix = getattr(args, "artifact_prefix", "") or ""
    profile = getattr(args, "profile", "implement") or "implement"
    generic = profile == "generic"
    if prefix and not _validate_artifact_prefix(prefix):
        print("stall-recovery: --artifact-prefix must be a simple dash token", file=sys.stderr)
        return 2

    def hard_fail(reason: str) -> int:
        _append_record_escalation_tool_failure(tmpdir=tmpdir, reason=reason)
        return 1

    site = args.site
    trigger = args.trigger
    step = args.step
    phase = args.phase
    dispatcher = args.dispatcher
    exit_code = args.exit_code
    if not _safe_token(kind="site", value=site, generic=generic) or not _safe_token(kind="trigger", value=trigger, generic=generic):
        print("stall-recovery: record-escalation token validation failed", file=sys.stderr)
        return hard_fail("token-validation-failed")
    if not _safe_token(kind="step", value=step, generic=generic) or not _safe_token(kind="phase", value=phase, generic=generic):
        print("stall-recovery: record-escalation token validation failed", file=sys.stderr)
        return hard_fail("token-validation-failed")
    detail_log = getattr(args, "failure_detail_log", "") or ""
    rel_log, detail_log_skipped = _resolve_detail_log(tmpdir=tmpdir, detail_log=detail_log)
    ledger = _artifact_path(tmpdir=tmpdir, default_name="stall-recovery-escalation-ledger.tsv", prefix=prefix)
    fallback = _artifact_path(tmpdir=tmpdir, default_name=_DEFAULT_ESCALATION_FALLBACK, prefix=prefix)
    marker = _artifact_path(tmpdir=tmpdir, default_name=_DEFAULT_RECORD_FAILURE_MARKER, prefix=prefix)
    if not _validate_tmpdir_write_path(tmpdir=tmpdir, path=ledger):
        print("stall-recovery: record-escalation ledger path invalid", file=sys.stderr)
        return hard_fail("ledger-path-invalid")
    safe_dispatcher = _safe_dispatcher_value(dispatcher, generic=generic)
    raw_exit_code = str(exit_code or "")
    safe_exit_code = raw_exit_code if re.fullmatch(r"[0-9]+|unknown", raw_exit_code) else "unknown"
    skip_field = f"\tdetail_log_skipped={detail_log_skipped}" if detail_log_skipped else ""
    row = (
        f"utc={datetime.now(UTC).isoformat()}\tsite={site}\ttrigger={trigger}\tstep={step}\tphase={phase}"
        f"\tdispatcher={safe_dispatcher}\texit_code={safe_exit_code}\tfailure_detail_log={rel_log}{skip_field}\n"
    )
    try:
        if ledger.is_file() and not os.access(ledger, os.W_OK):
            raise OSError("canonical-ledger-not-writable")
        if _append_ledger_row_atomic(ledger=ledger, row=row):
            emit(key="ESCALATION_RECORDED", value="true")
            emit(key="ESCALATION_LEDGER_FILE", value=ledger)
        else:
            raise OSError("canonical-ledger-write-failed")
    except OSError:
        marker = _artifact_path(tmpdir=tmpdir, default_name=_DEFAULT_RECORD_FAILURE_MARKER, prefix=prefix)
        fallback = _artifact_path(tmpdir=tmpdir, default_name=_DEFAULT_ESCALATION_FALLBACK, prefix=prefix)
        if not _validate_tmpdir_write_path(tmpdir=tmpdir, path=fallback) or not _validate_tmpdir_write_path(tmpdir=tmpdir, path=marker):
            print("stall-recovery: record-escalation fallback path invalid", file=sys.stderr)
            return hard_fail("fallback-path-invalid")
        try:
            marker.write_text("RECORD_ESCALATION_FAILED=true\nREASON=canonical-ledger-not-writable\n", encoding="utf-8")
            fallback.write_text(row, encoding="utf-8")
        except OSError:
            print("stall-recovery: record-escalation fallback write failed", file=sys.stderr)
            return hard_fail("recording-failed")
        emit(key="ESCALATION_RECORDED", value="false")
        emit(key="ESCALATION_FALLBACK_WRITTEN", value="true")
    return 0
