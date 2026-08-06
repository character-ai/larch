# pyright: reportUnusedCallResult=false, reportUnusedFunction=false, reportUnusedImport=false, reportPrivateUsage=false
# ruff: noqa: SLF001 - residual facade delegates to private owner helpers.
"""larch-log: slim residual façade and remaining CLI entrypoints.

The bulk of the original run_logs.py has been split into four sibling modules.
This file keeps only the implementations that did not move:
  - larch_log_init_main, larch_log_write_main, larch_log_append_main,
    larch_log_exists_main
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
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from larch.core import logging_util
from larch.core import redact
from larch.report import design_diagram_log
from larch.report import run_log_batch, run_log_manifest



def _parse_common(*, parser: argparse.ArgumentParser, argv: list[str]) -> argparse.Namespace | None:
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return None
    try:
        run_log_batch._validate_slug(label="skill", value=args.skill)
        run_log_batch._validate_slug(label="run-id", value=args.run_id)
        args.log_root_path = run_log_batch._resolve_log_root(getattr(args, "log_root", ""))
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


@dataclass(frozen=True)
class LogInitResult:
    """Result of :func:`log_init`: manifest path and idempotent write state."""

    path: Path
    written: bool
    unchanged: bool


@dataclass(frozen=True)
class RunParent:
    """Optional parent identity for a nested run-log invocation."""

    skill: str
    run_id: str


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
    parent: RunParent | None = None,
    issue: str = "",
) -> LogInitResult:
    """Idempotently synthesize a v2 manifest for ``skill``/``run_id``.

    Raises ``ValueError`` for an invalid ``parent_skill`` slug or non-numeric
    ``issue``. Returns an unchanged result when the manifest already exists.
    """
    if parent is not None:
        run_log_batch._validate_slug(label="parent-skill", value=parent.skill)
        run_log_batch._validate_slug(label="parent-run-id", value=parent.run_id)
    if issue and not str(issue).isdigit():
        raise ValueError(f"invalid issue: {issue}")
    path = run_log_manifest._manifest_cli_path(log_root=log_root, skill=skill, run_id=run_id)
    if path.is_file():
        return LogInitResult(path=path, written=False, unchanged=True)
    extra: dict[str, Any] = {
        "parent_skill": parent.skill if parent is not None else None,
        "parent_run_id": parent.run_id if parent is not None else None,
        "issue_number": int(issue) if issue else None,
    }
    manifest = run_log_manifest.Manifest.synthesize_v2(skill=skill, run_id=run_id, extra=extra)
    run_log_manifest._write_manifest_v2(path=path, data=manifest.to_json(existing=None))
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
    path, written, unchanged = run_log_batch._write_batch(
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
    path, written, unchanged = run_log_batch._append_batch(
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
    if batch not in run_log_batch._LARCH_LOG_BATCHES:
        raise ValueError(f"unknown batch: {batch}")
    path = run_log_batch._batch_path(log_root=log_root, skill=skill, run_id=run_id, batch=batch)
    return LogExistsResult(path=path, exists=path.exists())


def larch_log_init_main(argv: list[str]) -> int:
    parser = _common_parser("cli.py run-log init")
    parser.add_argument("--parent-skill", default="")
    parser.add_argument("--parent-run-id", default="")
    parser.add_argument("--issue", default="")
    args = _parse_common(parser=parser, argv=argv)
    if args is None:
        return run_log_batch._larch_log_fail(code=1, message="invalid init arguments")
    if bool(args.parent_skill) != bool(args.parent_run_id):
        return run_log_batch._larch_log_fail(
            code=1, message="parent-skill and parent-run-id must be provided together"
        )
    try:
        result = log_init(
            log_root=args.log_root_path,
            skill=args.skill,
            run_id=args.run_id,
            parent=(
                RunParent(skill=args.parent_skill, run_id=args.parent_run_id)
                if args.parent_skill and args.parent_run_id
                else None
            ),
            issue=args.issue,
        )
    except ValueError as exc:
        return run_log_batch._larch_log_fail(code=1, message=str(exc))
    run_log_batch._emit_larch_log_envelope(path=result.path, written=result.written, unchanged=result.unchanged)
    return 0


def larch_log_write_main(argv: list[str]) -> int:
    parser = _common_parser("cli.py run-log write")
    parser.add_argument("--batch", required=True)
    parser.add_argument("--input-file", required=True)
    parser.add_argument("--commit", action="store_true")
    args = _parse_common(parser=parser, argv=argv)
    if args is None:
        return run_log_batch._larch_log_fail(code=1, message="invalid write arguments")
    try:
        result = log_write(
            log_root=args.log_root_path,
            skill=args.skill,
            run_id=args.run_id,
            batch=args.batch,
            input_file=args.input_file,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return run_log_batch._larch_log_fail(code=1 if isinstance(exc, ValueError) else 2, message=str(exc))
    run_log_batch._emit_larch_log_envelope(path=result.path, written=result.written, unchanged=result.unchanged)
    return 0


def larch_log_append_main(argv: list[str]) -> int:
    parser = _common_parser("cli.py run-log append")
    parser.add_argument("--batch", required=True)
    parser.add_argument("--record-file", required=True)
    args = _parse_common(parser=parser, argv=argv)
    if args is None:
        return run_log_batch._larch_log_fail(code=1, message="invalid append arguments")
    try:
        result = log_append(
            log_root=args.log_root_path,
            skill=args.skill,
            run_id=args.run_id,
            batch=args.batch,
            record_file=args.record_file,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return run_log_batch._larch_log_fail(code=1 if isinstance(exc, ValueError) else 2, message=str(exc))
    run_log_batch._emit_larch_log_envelope(path=result.path, written=result.written, unchanged=result.unchanged)
    return 0


def larch_log_exists_main(argv: list[str]) -> int:
    parser = _common_parser("cli.py run-log exists")
    parser.add_argument("--batch", required=True)
    args = _parse_common(parser=parser, argv=argv)
    if args is None:
        return run_log_batch._larch_log_fail(code=1, message="invalid exists arguments")
    try:
        result = log_exists(
            log_root=args.log_root_path,
            skill=args.skill,
            run_id=args.run_id,
            batch=args.batch,
        )
    except ValueError as exc:
        return run_log_batch._larch_log_fail(code=1, message=str(exc))
    run_log_batch._emit_larch_log_envelope(path=result.path, written=False, unchanged=result.exists)
    return 0


def log_manifest_update(
    *, log_root: Path, skill: str, run_id: str, updates: dict[str, Any]
) -> Path:
    """Apply mutable manifest fields and return the updated manifest path."""
    path = run_log_manifest._manifest_cli_path(log_root=log_root, skill=skill, run_id=run_id)
    if not path.is_file():
        raise ValueError(f"manifest not found: {path}")
    run_log_manifest._update_manifest_v2(path=path, updates=updates)
    return path


def _resolve_required_files_manifest(raw: str) -> Path:
    if not raw:
        return run_log_batch._REQUIRED_FILES_TSV
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = (run_log_batch._REPO_ROOT / raw.removeprefix("./")).resolve()
    if not str(candidate).startswith(str(run_log_batch._REPO_ROOT.resolve())):
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
        manifest_data = run_log_manifest._read_manifest_v2(manifest_path)
        manifest = run_log_manifest.Manifest.from_json(manifest_data)
    except (OSError, json.JSONDecodeError, TypeError):
        print("MISSING=manifest")
        return 1
    manifest_status = run_log_manifest._manifest_field(manifest=manifest, key="status")
    manifest_pr_number = run_log_manifest._manifest_field(manifest=manifest, key="pr_number")
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
        if not run_log_manifest._verify_condition_reached(
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
        elif not run_log_manifest._verify_has_file(run_dir=run_dir, relative_path=relative_path):
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
    if args.category not in run_log_batch._EXECUTION_ISSUE_CATEGORIES:
        logging_util.emit_kv(key="FAILED", value="true")
        logging_util.emit_kv(key="ERROR", value=f"unsupported category: {args.category}")
        return 1
    try:
        entry = Path(args.entry_file).read_text(encoding="utf-8") if args.entry_file else args.entry
        run_log_batch._append_execution_issue(log_file=Path(args.log), category=args.category, entry=entry)
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
    run_log_batch._append_execution_issue(log_file=log, category=category, entry=entry)
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
        return run_log_batch._larch_log_fail(code=1, message="invalid write-round arguments")
    if not str(args.round).isdigit() or int(args.round) <= 0:
        return run_log_batch._larch_log_fail(code=1, message="--round must be a positive integer")
    source = Path(args.source_dir)
    if not source.is_dir() or source.is_symlink():
        return run_log_batch._larch_log_fail(code=1, message=f"source directory not found: {source}")
    dynamic_dir = source / "dynamic-archetypes"
    if dynamic_dir.is_symlink():
        return run_log_batch._larch_log_fail(code=2, message=f"dynamic-archetypes must not be a symlink: {dynamic_dir}")
    dest = run_log_batch._run_dir(log_root=args.log_root_path, skill=args.skill, run_id=args.run_id) / f"round-{args.round}"
    prev_round_dir = run_log_batch._run_dir(log_root=args.log_root_path, skill=args.skill, run_id=args.run_id) / f"round-{int(args.round) - 1}"
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
            if run_log_batch._is_round_sidecar_file(name):
                continue
            if name.startswith("reviewer-dyn-") and name.endswith(".md"):
                redacted = run_log_batch._normalize_run_log_text(redact.redact(item.read_text(encoding="utf-8", errors="replace")))
                digest = hashlib.sha256(redacted.encode("utf-8")).hexdigest()[:12]
                pool = dest / "archetypes"
                pool.mkdir(parents=True, exist_ok=True)
                pool_path = pool / f"{digest}.md"
                if not pool_path.is_file():
                    run_log_batch._atomic_write(path=pool_path, content=redacted)
                slot = "dyn-" + name.removeprefix("reviewer-dyn-").removesuffix(".md")
                archetype_refs[slot] = f"archetypes/{digest}.md"
                written = True
                continue
            if not run_log_batch._round_artifact_included(name):
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
                return run_log_batch._larch_log_fail(
                    code=2,
                    message=f"duplicate round artifact basename '{name}' from {item} and {seen[name]}",
                )
            seen[name] = item
            content = run_log_batch._stage_round_artifact(src=item, name=name)
            out = dest / name
            if not out.exists() or out.read_text(encoding="utf-8", errors="replace") != content:
                run_log_batch._atomic_write(path=out, content=content)
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
            run_log_batch._atomic_write(path=panel_manifest, content="\n".join(lines) + "\n")
            written = True
    run_log_batch._emit_larch_log_envelope(path=dest, written=written, unchanged=not written)
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
