# pyright: reportUnusedCallResult=false, reportUnusedFunction=false, reportUnusedImport=false, reportPrivateUsage=false
# pylint: disable=unused-import  # re-export facade: all imports intentionally available via run_logs.*
"""larch-log: slim residual façade and remaining CLI entrypoints.

The bulk of the original run_logs.py has been split into four sibling modules.
This file re-exports all their public symbols and keeps the implementations
that did not move:
  - larch_log_init_main, larch_log_write_main, larch_log_append_main,
    larch_log_exists_main, larch_log_manifest_main,
    larch_log_validate_run_id_main
  - verify_completeness_main and its helpers
  - append_entry_main, append_failure_main
  - larch_log_write_round_main
  - path_under_repo
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import shutil

from larch import io as larch_io

from larch.core import config
from larch.core import logging_util
from larch.core import proc  # re-exported: step_7a.py accesses run_logs.proc
from larch.core import redact
from larch.report import design_diagram_log
from larch.report import tokens
from larch.errors import ShipError
from larch.report.run_log_batch import (
    BatchInfo,
    _APPEND_LOCK_ATTEMPTS,
    _EXECUTION_ISSUE_CATEGORIES,
    _LARCH_LOG_BATCHES,
    _PLACEHOLDER_RUN_ID_RE,
    _QUIET_LOG_RE,
    _REPO_ROOT,
    _REQUIRED_FILES_TSV,
    _ROUND_ARTIFACT_ALLOW,
    _ROUND_ARTIFACT_ALLOW_GLOBS,
    _ROUND_ARTIFACT_DEBUG_GLOBS,
    _ROUND_ARTIFACT_DENY_GLOBS,
    _ROUND_SIDECAR_FILES,
    _SLUG_RE,
    _VOTE_OUTPUT_TRUNCATE_BYTES,
    _append_batch,
    _append_execution_issue,
    _atomic_write,
    _batch_extension,
    _batch_list,
    _batch_mode,
    _batch_path,
    _batch_sanitizer,
    _batch_validate_payload,
    _emit_larch_log_envelope,
    _is_round_sidecar_file,
    _larch_log_fail,
    _normalize_body_for_hash,
    _normalize_run_log_text,
    _read_kv_file,
    _read_state_kv,
    _redact_batch_payload,
    _redact_to_temp,
    _repo_run_dir,
    _resolve_log_root,
    _round_artifact_included,
    _round_name_matches,
    _run_dir,
    _sha256_file,
    _stage_round_artifact,
    _validate_plan_goals_payload,
    _validate_slug,
    _warn_placeholder_run_id,
    _write_batch,
    append_execution_issue,
    is_placeholder_run_id,
    validate_run_id_slug,
)

from larch.report.run_log_manifest import (
    RECOVERY_REASON_MANIFEST_LOST,
    REFRESH_SKIP_RECOVERY_FAILED,
    DurableFlags,
    Manifest,
    ManifestRecovery,
    RefreshSkip,
    ResumeCounters,
    _MANIFEST_IMMUTABLE,
    _MANIFEST_SCHEMA_VERSION,
    _V2_EMIT_EXTRA_EXCLUDED_KEYS,
    _V2_RESERVED_KEYS,
    _issue_number_from_context,
    _manifest_cli_path,
    _manifest_path,
    _manifest_field,
    _manifest_step9a1_explicitly_ran,
    _manifest_step9a1_explicitly_skipped,
    _manifest_steps_ran_nonempty_without_step9a1,
    _verify_condition_reached,
    _verify_has_file,
    _now_utc,
    _parse_manifest_scalar,
    _parse_nonnegative_int,
    _plugin_version,
    _pre_push_probe,
    _read_manifest_v2,
    _read_session_env_key,
    _recover_manifest_from_run_dir,
    _resolve_consumer_repo_root,
    _resolve_main_model,
    _run_log_dir,
    _update_manifest_v2,
    _write_manifest,
    _write_manifest_v2,
    effective_run_id,
    init_run,
    load_or_recover_manifest,
    load_or_recover_manifest_checked,
    manifest_status,
    parse_pr_number,
    read_durable_flags,
    read_resume_counters,
    read_state_kv,
    update_manifest,
)

from larch.report.run_log_commit import (
    _VOLATILE_REFRESH_BASENAMES,
    _breadcrumb_source_confined,
    _cleanup_volatile_run_tree,
    _commit_run,
    _copy_tree_to_repo,
    _default_branches,
    _git_stdout,
    _larch_log_commit,
    _publish_breadcrumbs_with_warning,
    _publish_run_tree_to_repo,
    _replace_tree_with_backup,
    _run_git_cleanup,
    _safe_copy_run_tree,
    _scrub_run_tree,
    _status_line_path,
    _update_commit_manifest_with_warning,
    _volatile_file_paths,
    _volatile_only_under_run_tree,
    _warn_secret_scrub,
    commit_larch_logs,
    larch_log_commit_main,
    publish_breadcrumbs_main,
)

from larch.report.run_log_flush import (
    _capture_transcript_append_warning,
    _capture_transcript_emit,
    _capture_transcript_redact_stderr,
    _check_preterminal_outcome_label,
    _load_refresh_session_env,
    _parse_preterminal_outcome_label,
    _parse_preterminal_outcome_label_from_run_dir,
    _preterminal_outcome_commit_blocked,
    _preterminal_outcome_refresh_skip,
    _read_finalize_kv,
    _read_run_flags_kv,
    _reconcile_terminal_manifest_from_ctx,
    _refresh_context,
    _render_execution_issues_batch,
    _render_ledger_reports,
    _render_token_timing_batches,
    _report_subprocess_env,
    _should_flush_execution_issues,
    _stage_pre_commit,
    _stage_ship_route_handoff,
    _stage_vendor_failure_diagnostics,
    _step9a1_heuristic,
    _timing_sidecar_paths,
    _token_sidecar_paths,
    _write_final_report,
    _write_report_json,
    capture_session_transcript,
    capture_transcript_main,
    finalize_postmerge_logs,
    flush_logs_post,
    flush_logs_pre,
    larch_log_flush_main,
    refresh_run_logs_main,
    render_execution_issues_batch,
    write_final_report_comment,
)



def _parse_common(*, parser: argparse.ArgumentParser, argv: list[str]) -> argparse.Namespace | None:
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return None
    try:
        _validate_slug(label="skill", value=args.skill)
        _validate_slug(label="run-id", value=args.run_id)
        args.log_root_path = _resolve_log_root(getattr(args, "log_root", ""))
    except (ValueError, AttributeError) as exc:
        print(str(exc), file=sys.stderr)
        return None
    return args


def _common_parser(prog: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=prog, add_help=False)
    parser.add_argument("--log-root", default="")
    parser.add_argument("--skill", required=True)
    parser.add_argument("--run-id", required=True)
    return parser


def larch_log_validate_run_id_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py run-log validate-run-id", add_help=False)
    parser.add_argument("--run-id", required=True)
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 2
    print(f"VALID={'true' if validate_run_id_slug(args.run_id) else 'false'}")
    return 0


@dataclass(frozen=True)
class LogInitResult:
    """Result of :func:`log_init`: manifest path and idempotent write state."""

    path: Path
    written: bool
    unchanged: bool


@dataclass(frozen=True)
class LogWriteResult:
    """Result of :func:`log_write`: batch path and idempotent write state."""

    path: Path
    written: bool
    unchanged: bool


@dataclass(frozen=True)
class LogAppendResult:
    """Result of :func:`log_append`: batch path and append state."""

    path: Path
    written: bool
    unchanged: bool


@dataclass(frozen=True)
class LogAppendFailureResult:
    """Result of :func:`log_append_failure`: execution-issue log path and append flag."""

    log: Path
    appended: bool


@dataclass(frozen=True)
class LogExistsResult:
    """Result of :func:`log_exists`: batch path and existence flag."""

    path: Path
    exists: bool


def log_init(
    *,
    log_root: Path,
    skill: str,
    run_id: str,
    parent_skill: str = "",
    issue: str = "",
) -> LogInitResult:
    """Idempotently synthesize a v2 manifest for ``skill``/``run_id``.

    Raises ``ValueError`` for an invalid ``parent_skill`` slug or non-numeric
    ``issue``. Returns an unchanged result when the manifest already exists.
    """
    if parent_skill:
        _validate_slug(label="parent-skill", value=parent_skill)
    if issue and not str(issue).isdigit():
        raise ValueError(f"invalid issue: {issue}")
    path = _manifest_cli_path(log_root=log_root, skill=skill, run_id=run_id)
    if path.is_file():
        return LogInitResult(path=path, written=False, unchanged=True)
    extra: dict[str, Any] = {
        "parent_skill": parent_skill or None,
        "issue_number": int(issue) if issue else None,
    }
    manifest = Manifest.synthesize_v2(skill=skill, run_id=run_id, extra=extra)
    _write_manifest_v2(path=path, data=manifest.to_json(existing=None))
    return LogInitResult(path=path, written=True, unchanged=False)


def log_write(
    *,
    log_root: Path,
    skill: str,
    run_id: str,
    batch: str,
    input_file: str,
) -> LogWriteResult:
    """Write a batch payload, returning its path and idempotent write state."""
    path, written, unchanged = _write_batch(
        log_root=log_root, skill=skill, run_id=run_id, batch=batch, input_file=input_file
    )
    return LogWriteResult(path=path, written=written, unchanged=unchanged)


def log_append(
    *,
    log_root: Path,
    skill: str,
    run_id: str,
    batch: str,
    record_file: str,
) -> LogAppendResult:
    """Append a record to a batch, returning its path and append state."""
    path, written, unchanged = _append_batch(
        log_root=log_root, skill=skill, run_id=run_id, batch=batch, record_file=record_file
    )
    return LogAppendResult(path=path, written=written, unchanged=unchanged)


def log_exists(
    *,
    log_root: Path,
    skill: str,
    run_id: str,
    batch: str,
) -> LogExistsResult:
    """Report whether a known batch file exists. Raises ``ValueError`` for an unknown batch."""
    if batch not in _LARCH_LOG_BATCHES:
        raise ValueError(f"unknown batch: {batch}")
    path = _batch_path(log_root=log_root, skill=skill, run_id=run_id, batch=batch)
    return LogExistsResult(path=path, exists=path.exists())


def larch_log_init_main(argv: list[str]) -> int:
    parser = _common_parser("cli.py run-log init")
    parser.add_argument("--parent-skill", default="")
    parser.add_argument("--issue", default="")
    args = _parse_common(parser=parser, argv=argv)
    if args is None:
        return _larch_log_fail(code=1, message="invalid init arguments")
    try:
        result = log_init(
            log_root=args.log_root_path,
            skill=args.skill,
            run_id=args.run_id,
            parent_skill=args.parent_skill,
            issue=args.issue,
        )
    except ValueError as exc:
        return _larch_log_fail(code=1, message=str(exc))
    _emit_larch_log_envelope(path=result.path, written=result.written, unchanged=result.unchanged)
    return 0


def larch_log_write_main(argv: list[str]) -> int:
    parser = _common_parser("cli.py run-log write")
    parser.add_argument("--batch", required=True)
    parser.add_argument("--input-file", required=True)
    parser.add_argument("--commit", action="store_true")
    args = _parse_common(parser=parser, argv=argv)
    if args is None:
        return _larch_log_fail(code=1, message="invalid write arguments")
    try:
        result = log_write(
            log_root=args.log_root_path,
            skill=args.skill,
            run_id=args.run_id,
            batch=args.batch,
            input_file=args.input_file,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return _larch_log_fail(code=1 if isinstance(exc, ValueError) else 2, message=str(exc))
    _emit_larch_log_envelope(path=result.path, written=result.written, unchanged=result.unchanged)
    return 0


def larch_log_append_main(argv: list[str]) -> int:
    parser = _common_parser("cli.py run-log append")
    parser.add_argument("--batch", required=True)
    parser.add_argument("--record-file", required=True)
    args = _parse_common(parser=parser, argv=argv)
    if args is None:
        return _larch_log_fail(code=1, message="invalid append arguments")
    try:
        result = log_append(
            log_root=args.log_root_path,
            skill=args.skill,
            run_id=args.run_id,
            batch=args.batch,
            record_file=args.record_file,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return _larch_log_fail(code=1 if isinstance(exc, ValueError) else 2, message=str(exc))
    _emit_larch_log_envelope(path=result.path, written=result.written, unchanged=result.unchanged)
    return 0


def larch_log_exists_main(argv: list[str]) -> int:
    parser = _common_parser("cli.py run-log exists")
    parser.add_argument("--batch", required=True)
    args = _parse_common(parser=parser, argv=argv)
    if args is None:
        return _larch_log_fail(code=1, message="invalid exists arguments")
    try:
        result = log_exists(
            log_root=args.log_root_path,
            skill=args.skill,
            run_id=args.run_id,
            batch=args.batch,
        )
    except ValueError as exc:
        return _larch_log_fail(code=1, message=str(exc))
    _emit_larch_log_envelope(path=result.path, written=False, unchanged=result.exists)
    return 0


def larch_log_manifest_main(argv: list[str]) -> int:
    parser = _common_parser("cli.py run-log manifest")
    parser.add_argument("--field", action="append", default=[])
    args = _parse_common(parser=parser, argv=argv)
    if args is None:
        return _larch_log_fail(code=1, message="invalid manifest arguments")
    updates: dict[str, Any] = {}
    for assignment in args.field:
        if "=" not in assignment:
            return _larch_log_fail(code=1, message=f"invalid field assignment: {assignment}")
        key, _, raw = assignment.partition("=")
        updates[key] = _parse_manifest_scalar(raw)
    try:
        result = log_manifest_update(
            log_root=args.log_root_path, skill=args.skill, run_id=args.run_id, updates=updates
        )
    except ValueError as exc:
        return _larch_log_fail(code=1, message=str(exc))
    _emit_larch_log_envelope(path=result, written=True, unchanged=False)
    return 0


def log_manifest_update(
    *, log_root: Path, skill: str, run_id: str, updates: dict[str, Any]
) -> Path:
    """Apply mutable manifest fields and return the updated manifest path."""
    path = _manifest_cli_path(log_root=log_root, skill=skill, run_id=run_id)
    if not path.is_file():
        raise ValueError(f"manifest not found: {path}")
    _update_manifest_v2(path=path, updates=updates)
    return path


def _resolve_required_files_manifest(raw: str) -> Path:
    if not raw:
        return _REQUIRED_FILES_TSV
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = (_REPO_ROOT / raw.removeprefix("./")).resolve()
    if not str(candidate).startswith(str(_REPO_ROOT.resolve())):
        msg = "LARCH_VERIFY_MANIFEST resolves outside repository root"
        raise ValueError(msg)
    return candidate


def verify_completeness_main(argv: list[str]) -> int:
    if not argv:
        print("MISSING=manifest", file=sys.stderr)
        return 1
    run_dir = Path(argv[0])
    if not run_dir.is_dir():
        print(f"verify-completeness: run dir not found: {run_dir}", file=sys.stderr)
        return 1
    try:
        manifest_tsv = _resolve_required_files_manifest(os.environ.get("LARCH_VERIFY_MANIFEST", ""))
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if not manifest_tsv.is_file():
        print(f"verify-completeness: manifest not found: {manifest_tsv}", file=sys.stderr)
        return 1
    manifest_path = run_dir / "manifest.json"
    if not manifest_path.is_file():
        print("MISSING=manifest")
        return 1
    try:
        manifest_data = _read_manifest_v2(manifest_path)
        manifest = Manifest.from_json(manifest_data)
    except (OSError, json.JSONDecodeError, TypeError):
        print("MISSING=manifest")
        return 1
    manifest_status = _manifest_field(manifest=manifest, key="status")
    manifest_pr_number = _manifest_field(manifest=manifest, key="pr_number")
    missing: list[str] = []
    for line in manifest_tsv.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split("\t")
        if not parts or parts[0] == "relative_path":
            continue
        relative_path, condition = parts[0], parts[1] if len(parts) > 1 else "always"
        if ".." in relative_path.split("/"):
            print(f"verify-completeness: invalid relative_path (..): {relative_path}", file=sys.stderr)
            return 1
        if not re.fullmatch(r"[A-Za-z0-9_./*-]+", relative_path):
            print(f"verify-completeness: invalid characters in relative_path: {relative_path}", file=sys.stderr)
            return 1
        if not _verify_condition_reached(
            condition=condition,
            run_dir=run_dir,
            manifest_data=manifest,
            manifest_status=manifest_status,
            manifest_pr_number=manifest_pr_number,
        ):
            continue
        if "*" in relative_path:
            if relative_path.count("*") > 1:
                print(
                    f"verify-completeness: relative_path must contain at most one * wildcard: {relative_path}",
                    file=sys.stderr,
                )
                return 1
            glob_hits = list(run_dir.glob(relative_path))
            if not any(hit.is_file() for hit in glob_hits):
                missing.append(relative_path)
        elif not _verify_has_file(run_dir=run_dir, relative_path=relative_path):
            missing.append(relative_path)
    if missing:
        print("MISSING=" + ",".join(missing))
        return 1
    print("OK")
    return 0


def append_entry_main(argv: list[str]) -> int:
    logging_util.quiet_init(argv0="append-execution-issue.sh")
    parser = argparse.ArgumentParser(prog="append-execution-issue.sh", add_help=False)
    parser.add_argument("--log", required=True)
    parser.add_argument("--category", required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--entry")
    group.add_argument("--entry-file")
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        logging_util.emit_kv(key="FAILED", value="true")
        logging_util.emit_kv(key="USAGE", value="append-execution-issue.sh --log FILE --category CAT (--entry STR | --entry-file FILE)")
        return 1
    if args.category not in _EXECUTION_ISSUE_CATEGORIES:
        logging_util.emit_kv(key="FAILED", value="true")
        logging_util.emit_kv(key="ERROR", value=f"unsupported category: {args.category}")
        return 1
    try:
        entry = Path(args.entry_file).read_text(encoding="utf-8") if args.entry_file else args.entry
        _append_execution_issue(log_file=Path(args.log), category=args.category, entry=entry)
    except OSError as exc:
        logging_util.emit_kv(key="FAILED", value="true")
        logging_util.emit_kv(key="ERROR", value=str(exc))
        return 2
    logging_util.emit_kv(key="APPENDED", value="true")
    logging_util.emit_kv(key="LOG", value=args.log)
    return 0


def _failure_retry_suffix(retry_count: str, transient_retry_count: str) -> str:
    if retry_count and transient_retry_count:
        auth_retries = int(retry_count) - 1
        transient_retries = int(transient_retry_count) - 1
        retry_parts: list[str] = []
        if auth_retries > 0:
            retry_parts.append(f"auth-retries={auth_retries}")
        if transient_retries > 0:
            retry_parts.append(f"transient-retries={transient_retries}")
        if retry_parts:
            return ", " + ", ".join(retry_parts)
        return ""
    if retry_count:
        return f", retries={retry_count}"
    return ""


def log_append_failure(
    *,
    log: Path,
    site: str,
    tool: str,
    exit_code: str,
    category: str,
    output_file: Path,
    verdict: str = "",
    retry_count: str = "",
    transient_retry_count: str = "",
    redact_body: bool = False,
    status_label: str = "failed",
) -> LogAppendFailureResult:
    """Format and append a failure entry to an execution-issue log.

    Raises ``ValueError`` for an unsupported category or malformed integer
    fields; ``OSError`` propagates from the underlying append.
    """
    if category not in {"Tool Failures", "External Reviewer Issues", "CI Issues", "Warnings"}:
        raise ValueError(f"unsupported category: {category}")
    for flag, value in (
        ("exit-code", exit_code),
        ("retry-count", retry_count),
        ("transient-retry-count", transient_retry_count),
    ):
        if value and not re.fullmatch(r"[0-9]+", value):
            raise ValueError(f"--{flag} must be a non-negative integer")
    if output_file.is_file() and output_file.stat().st_size:
        body = output_file.read_text(encoding="utf-8", errors="replace")
    else:
        body = f"no diagnostics captured (exit {exit_code})\n"
    if redact_body:
        body = redact.redact_secrets_only(redact.redact_tmpdir_paths(body))
    if category == "Warnings" and "diagram" in f"{site} {output_file}".lower():
        body = design_diagram_log.sanitize_diagram_capture(body)
    suffix = ""
    if verdict:
        suffix += f", {verdict}"
    suffix += _failure_retry_suffix(retry_count, transient_retry_count)
    entry = (
        f"- **Step {site}: {tool} {status_label} "
        f"(exit {exit_code}{suffix})**:\n"
        "  ```\n"
        f"{body.rstrip()}\n"
        "  ```\n"
    )
    _append_execution_issue(log_file=log, category=category, entry=entry)
    return LogAppendFailureResult(log=log, appended=True)


def append_failure_main(argv: list[str]) -> int:
    logging_util.quiet_init(argv0="python3 python/cli.py run-log append-failure")
    parser = argparse.ArgumentParser(prog="python3 python/cli.py run-log append-failure", add_help=False)
    parser.add_argument("--log", required=True)
    parser.add_argument("--site", required=True)
    parser.add_argument("--tool", required=True)
    parser.add_argument("--exit-code", required=True)
    parser.add_argument("--category", required=True)
    parser.add_argument("--output-file", required=True)
    parser.add_argument("--verdict", default="")
    parser.add_argument("--retry-count", default="")
    parser.add_argument("--transient-retry-count", default="")
    parser.add_argument("--redact", action="store_true")
    parser.add_argument("--status-label", default="failed")
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        logging_util.emit_kv(key="FAILED", value="true")
        return 1
    try:
        log_append_failure(
            log=Path(args.log),
            site=args.site,
            tool=args.tool,
            exit_code=args.exit_code,
            category=args.category,
            output_file=Path(args.output_file),
            verdict=args.verdict,
            retry_count=args.retry_count,
            transient_retry_count=args.transient_retry_count,
            redact_body=args.redact,
            status_label=args.status_label,
        )
    except ValueError as exc:
        logging_util.emit_kv(key="FAILED", value="true")
        logging_util.emit_kv(key="ERROR", value=str(exc))
        return 1
    except OSError as exc:
        logging_util.emit_kv(key="FAILED", value="true")
        logging_util.emit_kv(key="ERROR", value=str(exc))
        return 2
    logging_util.emit_kv(key="APPENDED", value="true")
    logging_util.emit_kv(key="LOG", value=args.log)
    return 0


def larch_log_write_round_main(argv: list[str]) -> int:
    parser = _common_parser("cli.py run-log write-round")
    parser.add_argument("--round", required=True)
    parser.add_argument("--source-dir", required=True)
    args = _parse_common(parser=parser, argv=argv)
    if args is None:
        return _larch_log_fail(code=1, message="invalid write-round arguments")
    if not str(args.round).isdigit() or int(args.round) <= 0:
        return _larch_log_fail(code=1, message="--round must be a positive integer")
    source = Path(args.source_dir)
    if not source.is_dir() or source.is_symlink():
        return _larch_log_fail(code=1, message=f"source directory not found: {source}")
    dynamic_dir = source / "dynamic-archetypes"
    if dynamic_dir.is_symlink():
        return _larch_log_fail(code=2, message=f"dynamic-archetypes must not be a symlink: {dynamic_dir}")
    dest = _run_dir(log_root=args.log_root_path, skill=args.skill, run_id=args.run_id) / f"round-{args.round}"
    prev_round_dir = _run_dir(log_root=args.log_root_path, skill=args.skill, run_id=args.run_id) / f"round-{int(args.round) - 1}"
    dest.mkdir(parents=True, exist_ok=True)
    written = False
    archetype_refs: dict[str, str] = {}
    seen: dict[str, Path] = {}
    scan_dirs = [source]
    if dynamic_dir.is_dir():
        scan_dirs.append(dynamic_dir)
    for scan_dir in scan_dirs:
        for item in sorted(scan_dir.iterdir()):
            if not item.is_file() or item.is_symlink():
                continue
            name = item.name
            if _is_round_sidecar_file(name):
                continue
            if name.startswith("reviewer-dyn-") and name.endswith(".md"):
                redacted = _normalize_run_log_text(redact.redact(item.read_text(encoding="utf-8", errors="replace")))
                digest = hashlib.sha256(redacted.encode("utf-8")).hexdigest()[:12]
                shared = args.log_root_path / "shared" / "archetypes"
                shared.mkdir(parents=True, exist_ok=True)
                pool_path = shared / f"{digest}.md"
                if not pool_path.is_file():
                    _atomic_write(path=pool_path, content=redacted)
                slot = "dyn-" + name.removeprefix("reviewer-dyn-").removesuffix(".md")
                archetype_refs[slot] = digest
                written = True
                continue
            if not _round_artifact_included(name):
                continue
            if name == "aggregator-output.txt":
                agg_findings = item.parent / "findings.md"
                if agg_findings.is_file() and agg_findings.read_bytes() == item.read_bytes():
                    continue
            if name.startswith("scout-round") and name.endswith("-manifest.json"):
                prev_manifest = prev_round_dir / name
                if prev_manifest.is_file() and prev_manifest.read_bytes() == item.read_bytes():
                    continue
            if name in seen:
                return _larch_log_fail(
                    code=2,
                    message=f"duplicate round artifact basename '{name}' from {item} and {seen[name]}",
                )
            seen[name] = item
            content = _stage_round_artifact(src=item, name=name)
            out = dest / name
            if not out.exists() or out.read_text(encoding="utf-8", errors="replace") != content:
                _atomic_write(path=out, content=content)
                written = True
    panel_manifest = dest / "panel-manifest.ndjson"
    if archetype_refs and panel_manifest.is_file():
        lines: list[str] = []
        changed = False
        for line in panel_manifest.read_text(encoding="utf-8", errors="replace").splitlines():
            stripped = line.strip()
            if not stripped:
                lines.append(line)
                continue
            try:
                row = json.loads(stripped)
            except json.JSONDecodeError:
                lines.append(line)
                continue
            if not isinstance(row, dict):
                lines.append(line)
                continue
            row_dict = cast("dict[str, Any]", row)
            slot = str(row_dict.get("slot", ""))
            if slot in archetype_refs and "archetype_ref" not in row:
                row["archetype_ref"] = archetype_refs[slot]
                changed = True
            lines.append(json.dumps(row, ensure_ascii=False))
        if changed:
            _atomic_write(path=panel_manifest, content="\n".join(lines) + "\n")
            written = True
    _emit_larch_log_envelope(path=dest, written=written, unchanged=not written)
    return 0


def path_under_repo(*, repo_root: Path, rel_path: str) -> bool:
    if "\x00" in rel_path or rel_path.startswith("/") or ".." in rel_path.split("/"):
        return False
    try:
        resolved = (repo_root / rel_path).resolve()
        _ = resolved.relative_to(repo_root.resolve())
    except ValueError:
        return False
    return True
