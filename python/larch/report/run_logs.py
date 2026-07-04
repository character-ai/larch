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
from larch.report.run_log_tolerance import terminal_bail_skip_signal

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
    _manifest_step9a1_explicitly_ran,
    _manifest_step9a1_explicitly_skipped,
    _manifest_steps_ran_nonempty_without_step9a1,
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
    _execution_issue_record,
    _load_refresh_session_env,
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

_TERMINAL_OUTCOME_SUFFIX = re.compile(
    r"(bailed(-needs-user-input)?|stalled|design-only|forked-dry-run|pr-created(-draft)?|shipping)$",
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


def larch_log_init_main(argv: list[str]) -> int:
    parser = _common_parser("cli.py run-log init")
    parser.add_argument("--parent-skill", default="")
    parser.add_argument("--issue", default="")
    args = _parse_common(parser=parser, argv=argv)
    if args is None:
        return _larch_log_fail(code=1, message="invalid init arguments")
    if args.parent_skill:
        try:
            _validate_slug(label="parent-skill", value=args.parent_skill)
        except ValueError as exc:
            return _larch_log_fail(code=1, message=str(exc))
    if args.issue and not str(args.issue).isdigit():
        return _larch_log_fail(code=1, message=f"invalid issue: {args.issue}")
    path = _manifest_cli_path(log_root=args.log_root_path, skill=args.skill, run_id=args.run_id)
    if path.is_file():
        _emit_larch_log_envelope(path=path, written=False, unchanged=True)
        return 0
    extra: dict[str, Any] = {
        "parent_skill": args.parent_skill or None,
        "issue_number": int(args.issue) if args.issue else None,
    }
    manifest = Manifest.synthesize_v2(skill=args.skill, run_id=args.run_id, extra=extra)
    _write_manifest_v2(path=path, data=manifest.to_json(existing=None))
    _emit_larch_log_envelope(path=path, written=True, unchanged=False)
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
        path, written, unchanged = _write_batch(log_root=args.log_root_path, skill=args.skill, run_id=args.run_id, batch=args.batch, input_file=args.input_file)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return _larch_log_fail(code=1 if isinstance(exc, ValueError) else 2, message=str(exc))
    _emit_larch_log_envelope(path=path, written=written, unchanged=unchanged)
    return 0


def larch_log_append_main(argv: list[str]) -> int:
    parser = _common_parser("cli.py run-log append")
    parser.add_argument("--batch", required=True)
    parser.add_argument("--record-file", required=True)
    args = _parse_common(parser=parser, argv=argv)
    if args is None:
        return _larch_log_fail(code=1, message="invalid append arguments")
    try:
        path, written, unchanged = _append_batch(log_root=args.log_root_path, skill=args.skill, run_id=args.run_id, batch=args.batch, record_file=args.record_file)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return _larch_log_fail(code=1 if isinstance(exc, ValueError) else 2, message=str(exc))
    _emit_larch_log_envelope(path=path, written=written, unchanged=unchanged)
    return 0


def larch_log_exists_main(argv: list[str]) -> int:
    parser = _common_parser("cli.py run-log exists")
    parser.add_argument("--batch", required=True)
    args = _parse_common(parser=parser, argv=argv)
    if args is None:
        return _larch_log_fail(code=1, message="invalid exists arguments")
    if args.batch not in _LARCH_LOG_BATCHES:
        return _larch_log_fail(code=1, message=f"unknown batch: {args.batch}")
    path = _batch_path(log_root=args.log_root_path, skill=args.skill, run_id=args.run_id, batch=args.batch)
    _emit_larch_log_envelope(path=path, written=False, unchanged=path.exists())
    return 0


def larch_log_manifest_main(argv: list[str]) -> int:
    parser = _common_parser("cli.py run-log manifest")
    parser.add_argument("--field", action="append", default=[])
    args = _parse_common(parser=parser, argv=argv)
    if args is None:
        return _larch_log_fail(code=1, message="invalid manifest arguments")
    path = _manifest_cli_path(log_root=args.log_root_path, skill=args.skill, run_id=args.run_id)
    if not path.is_file():
        return _larch_log_fail(code=1, message=f"manifest not found: {path}")
    updates: dict[str, Any] = {}
    for assignment in args.field:
        if "=" not in assignment:
            return _larch_log_fail(code=1, message=f"invalid field assignment: {assignment}")
        key, _, raw = assignment.partition("=")
        updates[key] = _parse_manifest_scalar(raw)
    try:
        _update_manifest_v2(path=path, updates=updates)
    except ValueError as exc:
        return _larch_log_fail(code=1, message=str(exc))
    _emit_larch_log_envelope(path=path, written=True, unchanged=False)
    return 0


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


def _manifest_field(*, manifest: Manifest, key: str) -> str:
    value = manifest.reserved.get(key) if key in _V2_RESERVED_KEYS else None
    if value is None and manifest.extra:
        value = manifest.extra.get(key)
    if key == "pr_number":
        if isinstance(value, bool):
            return ""
        if isinstance(value, int):
            return str(value)
        if isinstance(value, str) and value.strip():
            return value.strip()
        return ""
    if key == "status":
        return manifest.status
    return ""


def _manifest_steps_ran_empty(manifest: Manifest) -> bool:
    return len(manifest.steps_ran) == 0


def _final_summary_heading_bail_signal(run_dir: Path) -> bool:
    summary = run_dir / "final-summary.md"
    if not summary.is_file():
        return False
    for line in summary.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.strip():
            return bool(_TERMINAL_OUTCOME_SUFFIX.search(line.rstrip("\r\n")))
    return False


def _final_summary_bail_signal_without_pr_evidence(
    *, run_dir: Path,
    manifest_pr_number: str,
    manifest_data: Manifest | None = None,
) -> bool:
    manifest_obj: object | None = manifest_data.to_json(existing=None) if manifest_data is not None else None
    if manifest_obj is None and manifest_pr_number.strip().isdigit():
        manifest_obj = {"pr_number": int(manifest_pr_number)}
    pr = int(manifest_pr_number) if manifest_pr_number.strip().isdigit() else 0
    return terminal_bail_skip_signal(run_dir=run_dir, manifest=manifest_obj, pr=pr)


def _verify_has_file(*, run_dir: Path, relative_path: str) -> bool:
    return (run_dir / relative_path).is_file()


def _verify_condition_reached(
    *, condition: str,
    run_dir: Path,
    manifest_data: Manifest,
    manifest_status: str,
    manifest_pr_number: str,
    chain: bool = False,
) -> bool:
    if condition == "always":
        return True
    if condition == "step5":
        return (
            _verify_has_file(run_dir=run_dir, relative_path="code-review-tally.json")
            or _verify_has_file(run_dir=run_dir, relative_path="review-findings-full.jsonl")
            or _verify_condition_reached(
                condition="step7a",
                run_dir=run_dir,
                manifest_data=manifest_data,
                manifest_status=manifest_status,
                manifest_pr_number=manifest_pr_number,
            )
        )
    if condition == "step7a":
        if (
            _manifest_steps_ran_empty(manifest_data)
            and _final_summary_bail_signal_without_pr_evidence(
                run_dir=run_dir,
                manifest_pr_number=manifest_pr_number,
                manifest_data=manifest_data,
            )
            and not (
                _verify_has_file(run_dir=run_dir, relative_path="token-report.json")
                or _verify_has_file(run_dir=run_dir, relative_path="timing-report.json")
                or _verify_has_file(run_dir=run_dir, relative_path="execution-issues.ndjson")
                or _verify_has_file(run_dir=run_dir, relative_path="session-transcript.jsonl")
            )
        ):
            return False
        return (
            _verify_has_file(run_dir=run_dir, relative_path="token-report.json")
            or _verify_has_file(run_dir=run_dir, relative_path="timing-report.json")
            or _verify_has_file(run_dir=run_dir, relative_path="execution-issues.ndjson")
            or _verify_has_file(run_dir=run_dir, relative_path="session-transcript.jsonl")
            or _verify_condition_reached(
                condition="step8",
                run_dir=run_dir,
                manifest_data=manifest_data,
                manifest_status=manifest_status,
                manifest_pr_number=manifest_pr_number,
            )
        )
    if condition == "step8":
        if (
            _manifest_steps_ran_empty(manifest_data)
            and _final_summary_bail_signal_without_pr_evidence(
                run_dir=run_dir,
                manifest_pr_number=manifest_pr_number,
                manifest_data=manifest_data,
            )
            and not _verify_has_file(run_dir=run_dir, relative_path="version-bump-reasoning.md")
        ):
            return False
        return (
            _verify_has_file(run_dir=run_dir, relative_path="version-bump-reasoning.md")
            or _verify_has_file(run_dir=run_dir, relative_path="final-summary.md")
            or _verify_condition_reached(
                condition="step9a1",
                run_dir=run_dir,
                manifest_data=manifest_data,
                manifest_status=manifest_status,
                manifest_pr_number=manifest_pr_number,
                chain=True,
            )
        )
    if condition == "step9a1":
        # Intentional divergence from the retired bash verify-completeness, which
        # OR-ed run-statistics.md / oos-issues.ndjson / PR-number / status=done /
        # final-summary.md. Step 9a.1 completion is authoritative ONLY via
        # run-statistics.md plus explicit steps_ran.step9a1 markers (#4427): an
        # oos-issues.ndjson alone is provisional disposition evidence and must
        # NOT count, and a steps_ran.step9a1=true without run-statistics.md is a
        # stale or corrupt marker that must fail the scan. See the "bail-time
        # steps_ran invariant" in skills/implement/SKILL.md and the asserting
        # tests test_verify_completeness_stale_step9a1_true_without_stats_fails
        # and test_flush_logs_pre_downgrades_stale_step9a1_true_with_ndjson_only.
        if _manifest_step9a1_explicitly_skipped(manifest_data):
            return False
        if _manifest_step9a1_explicitly_ran(manifest_data):
            return True
        if (
            _manifest_steps_ran_empty(manifest_data)
            and _final_summary_bail_signal_without_pr_evidence(
                run_dir=run_dir,
                manifest_pr_number=manifest_pr_number,
                manifest_data=manifest_data,
            )
            and not _verify_has_file(run_dir=run_dir, relative_path="run-statistics.md")
        ):
            return False
        if (
            _final_summary_bail_signal_without_pr_evidence(
                run_dir=run_dir,
                manifest_pr_number=manifest_pr_number,
                manifest_data=manifest_data,
            )
            and not _verify_has_file(run_dir=run_dir, relative_path="run-statistics.md")
            and _manifest_steps_ran_nonempty_without_step9a1(manifest_data)
        ):
            return False
        return _verify_has_file(run_dir=run_dir, relative_path="run-statistics.md") if chain else True
    if condition == "exn-agg-validate-fail":
        path = run_dir / "execution-issues.ndjson"
        return path.is_file() and "merged output failed validation" in path.read_text(encoding="utf-8", errors="replace")
    if condition == "exn-agg-dispatch-fail":
        path = run_dir / "execution-issues.ndjson"
        if not path.is_file():
            return False
        text = path.read_text(encoding="utf-8", errors="replace")
        return (
            "dispatch-with-waterfall exited non-zero" in text
            or "agent dispatch-waterfall exited non-zero" in text
            or "DISPATCH_OK=false" in text
        )
    msg = f"unsupported manifest condition: {condition}"
    raise ValueError(msg)


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
    if args.category not in {"Tool Failures", "External Reviewer Issues", "CI Issues", "Warnings"}:
        logging_util.emit_kv(key="FAILED", value="true")
        logging_util.emit_kv(key="ERROR", value=f"unsupported category: {args.category}")
        return 1
    for attr in ("exit_code", "retry_count", "transient_retry_count"):
        value = getattr(args, attr)
        if value and not re.fullmatch(r"[0-9]+", value):
            logging_util.emit_kv(key="FAILED", value="true")
            logging_util.emit_kv(key="ERROR", value=f"--{attr.replace('_', '-')} must be a non-negative integer")
            return 1
    output = Path(args.output_file)
    if output.is_file() and output.stat().st_size:
        body = output.read_text(encoding="utf-8", errors="replace")
    else:
        body = f"no diagnostics captured (exit {args.exit_code})\n"
    if args.redact:
        body = redact.redact_secrets_only(redact.redact_tmpdir_paths(body))
    if args.category == "Warnings" and "diagram" in f"{args.site} {args.output_file}".lower():
        body = design_diagram_log.sanitize_diagram_capture(body)
    suffix = ""
    if args.verdict:
        suffix += f", {args.verdict}"
    if args.retry_count and args.transient_retry_count:
        suffix += f", auth-retries={args.retry_count}, transient-retries={args.transient_retry_count}"
    elif args.retry_count:
        suffix += f", retries={args.retry_count}"
    entry = (
        f"- **Step {args.site}: {args.tool} {args.status_label} "
        f"(exit {args.exit_code}{suffix})**:\n"
        "  ```\n"
        f"{body.rstrip()}\n"
        "  ```\n"
    )
    try:
        _append_execution_issue(log_file=Path(args.log), category=args.category, entry=entry)
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
                redacted = redact.redact(item.read_text(encoding="utf-8", errors="replace"))
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
