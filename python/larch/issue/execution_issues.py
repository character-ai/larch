"""Execution-issues ledger helpers for /implement."""

# pyright: reportUnusedCallResult=false

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from contextlib import suppress
from pathlib import Path
from typing import cast
from larch import io as larch_io
from larch.core import config
from larch.core import logging_util
from larch.report import exec_issue_detail
from larch.report.run_log_batch import (
    _EXECUTION_ISSUE_CATEGORIES,  # pyright: ignore[reportPrivateUsage]  # shared writer uses the canonical category set.
    _normalize_body_for_hash,  # pyright: ignore[reportPrivateUsage]  # shared writer preserves the established hash grammar.
    _redact_batch_payload,  # pyright: ignore[reportPrivateUsage]  # shared writer uses the existing fail-closed redaction path.
    execution_issue_identity,
)

VALIDATION_FAILED_RC = 2
_WARNINGS_CATEGORY = "Warnings"
_RESOLUTION_EVENT = "resolved"


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def normalize_body_for_hash(text: str) -> str:
    return _normalize_body_for_hash(text)


def execution_issue_id(*, category: str, body: str) -> str:
    """Return the stable identity used by append and resolution ledger records."""
    return execution_issue_identity(category=category, body=body)


def execution_issue_resolution_record(*, category: str, entry: str, resolution: str) -> str:
    """Serialize an append-only resolution event for an execution-issue record."""
    return json.dumps({
        "event": _RESOLUTION_EVENT,
        "issue_ids": [execution_issue_id(category=category, body=entry)],
        "resolution": resolution,
    }, separators=(",", ":"), sort_keys=True)


def execution_issue_batch_has_resolution(*, batch_text: str, category: str, entry: str) -> bool:
    """Whether the ledger already records this entry as resolved."""
    issue_id = execution_issue_id(category=category, body=entry)
    for raw in batch_text.splitlines():
        try:
            row: object = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, dict):
            continue
        row_dict = cast("dict[str, object]", row)
        if row_dict.get("event") != _RESOLUTION_EVENT:
            continue
        issue_ids = row_dict.get("issue_ids")
        if isinstance(issue_ids, list) and issue_id in issue_ids:
            return True
    return False


def _is_fence(line: str) -> bool:
    candidate = line.lstrip()
    if candidate.startswith("- "):
        candidate = candidate[2:].lstrip()
    return candidate.startswith("```")


def execution_issue_sections(text: str) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = []
    current: str | None = None
    body: list[str] = []
    in_fence = False

    def append_current() -> None:
        nonlocal body
        if current is not None and any(line.strip() for line in body):
            sections.append((current, "\n".join(body) + "\n"))
        body = []

    for line in text.splitlines():
        if not in_fence and line.strip() == "---":
            continue
        if not in_fence and line.startswith(("### ", "## ")):
            heading = line.split(" ", 1)[1].strip()
            if heading in _EXECUTION_ISSUE_CATEGORIES:
                append_current()
                current = heading
                continue
            append_current()
            current = _WARNINGS_CATEGORY
            continue
        if not in_fence and line.startswith("# ") and line[2:].strip() == "Execution Issues":
            continue
        if current is None and line.strip():
            current = _WARNINGS_CATEGORY
        body.append(line)
        if _is_fence(line):
            in_fence = not in_fence
    append_current()
    return sections


def _execution_issue_chunks(body: str) -> list[str]:
    chunks: list[str] = []
    current: list[str] = []
    in_fence = False
    pending_break = False
    for line in body.splitlines():
        if not in_fence and not line.strip():
            pending_break = bool(current)
            continue
        is_fence = _is_fence(line)
        if not in_fence and line.startswith("- ") and current and not is_fence:
            chunks.append("\n".join(current).strip() + "\n")
            current = []
            pending_break = False
        if pending_break and current:
            chunks.append("\n".join(current).strip() + "\n")
            current = []
        pending_break = False
        current.append(line)
        if is_fence:
            in_fence = not in_fence
    if current:
        chunks.append("\n".join(current).strip() + "\n")
    return chunks


def _execution_issue_body_keys(*, category: str, body: str) -> set[str]:
    return {
        f"{category}\0{key}"
        for key in exec_issue_detail.structured_body_dedupe_keys(body, category)
    }


def _existing_execution_issue_keys(batch_text: str) -> set[str]:
    keys: set[str] = set()
    for raw in batch_text.splitlines():
        try:
            row: object = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, dict):
            continue
        row_dict = cast("dict[str, object]", row)
        category = row_dict.get("category")
        body = row_dict.get("body")
        if isinstance(category, str) and isinstance(body, str):
            keys.update(_execution_issue_body_keys(category=category, body=body))
    return keys


def execution_issue_records(
    *,
    text: str,
    existing_batch: str,
    step_label: str,
    source_label: str,
    file_sha: str,
) -> list[str]:
    records: list[str] = []
    seen_keys = _existing_execution_issue_keys(existing_batch)
    for category, section in execution_issue_sections(text):
        for chunk in _execution_issue_chunks(section):
            body = _redact_batch_payload(chunk)
            body_keys = _execution_issue_body_keys(category=category, body=body)
            if body_keys <= seen_keys:
                continue
            norm_sha = hashlib.sha256(normalize_body_for_hash(body).encode()).hexdigest()
            records.append(json.dumps({
                "phase": "implement",
                "step": step_label,
                "category": category,
                "source": source_label,
                "source_sha256": norm_sha or file_sha,
                "body": body,
            }, separators=(",", ":"), sort_keys=True))
            seen_keys.update(body_keys)
    return records


def execution_issues_batch_contains_all_sections( *,input_file: str | Path, batch_path: str | Path) -> bool:
    batch = Path(batch_path)
    if not batch.is_file():
        return False
    text = Path(input_file).read_text(encoding="utf-8", errors="replace")
    batch_text = batch.read_text(encoding="utf-8", errors="replace")
    saw = False
    existing_keys = _existing_execution_issue_keys(batch_text)
    for category, section in execution_issue_sections(text):
        for body in _execution_issue_chunks(section):
            redacted_body = _redact_batch_payload(body)
            body_keys = _execution_issue_body_keys(category=category, body=redacted_body)
            norm_sha = hashlib.sha256(normalize_body_for_hash(redacted_body).encode()).hexdigest()
            if not body_keys <= existing_keys and f'"source_sha256":"{norm_sha}"' not in batch_text:
                return False
            saw = True
    return saw


def write_execution_issues_records( *,input_file: str | Path, record_file: str | Path, sha: str, batch_path: str | Path | None = None, step_label: str = "18", source_label: str = "execution-issues.md safety-net") -> int:
    source = Path(input_file)
    batch_text = Path(batch_path).read_text(encoding="utf-8", errors="replace") if batch_path and Path(batch_path).is_file() else ""
    records = execution_issue_records(
        text=source.read_text(encoding="utf-8", errors="replace"),
        existing_batch=batch_text,
        step_label=step_label,
        source_label=source_label,
        file_sha=sha,
    )
    Path(record_file).write_text("\n".join(records) + ("\n" if records else ""), encoding="utf-8")
    return len(records)


def _append_failure( *,issue_log: Path, site: str, message: str) -> None:
    with issue_log.open("a", encoding="utf-8") as handle:
        handle.write(f"\n### Tool Failures\n- **{site}**: {message}\n")


def flush_execution_issues(*, log_root: Path, run_id: str, issue_log: Path, batch: str = "execution-issues", step_label: str = "7a", source_label: str = "execution-issues.md pre-bump") -> tuple[int, str, int, str]:
    if not log_root.is_absolute():
        return 2, "failed", 0, "--log-root must be absolute"
    if not re.fullmatch(r"[A-Za-z0-9-]+", run_id or ""):
        return 2, "failed", 0, "--run-id must contain only letters, numbers, and hyphens"
    if batch != "execution-issues":
        return 2, "failed", 0, "--batch must be execution-issues"
    sentinel_dir = issue_log.parent
    if step_label == "7a":
        (sentinel_dir / ".execution-issues-step7a-reached").touch(exist_ok=True)
    if not issue_log.is_file() or issue_log.stat().st_size == 0:
        return 0, "skip", 0, ""
    sha = sha256_file(issue_log)
    sentinel = sentinel_dir / ".execution-issues-flushed.sha"
    batch_path = log_root / "implement" / run_id / "execution-issues.ndjson"
    sentinel_matches = sentinel.is_file() and sentinel.read_text(encoding="utf-8", errors="replace").strip() == sha
    batch_matches = False
    if batch_path.is_file():
        batch_text = batch_path.read_text(encoding="utf-8", errors="replace")
        batch_matches = f'"source_sha256":"{sha}"' in batch_text or execution_issues_batch_contains_all_sections(input_file=issue_log, batch_path=batch_path)
    if sentinel_matches:
        sentinel.write_text(sha + "\n", encoding="utf-8")
        issue_log.write_text("", encoding="utf-8")
        return 0, "already-flushed", 0, ""
    if batch_matches:
        sentinel.write_text(sha + "\n", encoding="utf-8")
        issue_log.write_text("", encoding="utf-8")
        return 0, "already-flushed", 0, ""
    with tempfile.NamedTemporaryFile("w", delete=False, dir=str(sentinel_dir if sentinel_dir.is_dir() else Path(tempfile.gettempdir())), encoding="utf-8") as record_tmp:
        record_path = Path(record_tmp.name)
    append_log = sentinel_dir / f"flush-execution-issues-append.{os.getpid()}.log"
    try:
        records = write_execution_issues_records(input_file=issue_log, record_file=record_path, sha=sha, batch_path=batch_path, step_label=step_label, source_label=source_label)
        if records == 0:
            sentinel.write_text(sha + "\n", encoding="utf-8")
            issue_log.write_text("", encoding="utf-8")
            return 0, "no-records", 0, str(append_log)
        plugin_root = Path(os.environ.get("CLAUDE_PLUGIN_ROOT", Path(__file__).resolve().parents[3]))
        cmd = [sys.executable, str(plugin_root / "python" / "cli.py"), "run-log", "append", "--log-root", str(log_root), "--skill", "implement", "--run-id", run_id, "--batch", "execution-issues", "--record-file", str(record_path)]
        proc = subprocess.run(cmd, text=True, capture_output=True, check=False)
        append_log.write_text(proc.stdout + proc.stderr, encoding="utf-8")
        if proc.returncode == 0:
            sentinel.write_text(sha + "\n", encoding="utf-8")
            issue_log.write_text("", encoding="utf-8")
            return 0, "ok", records, str(append_log)
        _append_failure(issue_log=issue_log, site="flush-execution-issues", message=f"run-log exited {proc.returncode}")
        return 1, "failed", 0, str(append_log)
    finally:
        with suppress(OSError):
            record_path.unlink()




def flush_execution_issues_safety_net(*, log_root: Path, run_id: str, issue_log: Path, batch: str = "execution-issues", step_label: str = "18", source_label: str = "execution-issues.md safety-net") -> tuple[int, str, int, str]:
    """Append pending execution issues to the run log without truncating the source log."""
    if not log_root.is_absolute():
        return 2, "failed", 0, "--log-root must be absolute"
    if not re.fullmatch(r"[A-Za-z0-9-]+", run_id or ""):
        return 2, "failed", 0, "--run-id must contain only letters, numbers, and hyphens"
    if batch != "execution-issues":
        return 2, "failed", 0, "--batch must be execution-issues"
    if not issue_log.is_file() or issue_log.stat().st_size == 0:
        return 0, "skip", 0, ""
    sentinel_dir = issue_log.parent
    sha = sha256_file(issue_log)
    batch_path = log_root / "implement" / run_id / "execution-issues.ndjson"
    with tempfile.NamedTemporaryFile("w", delete=False, dir=str(sentinel_dir if sentinel_dir.is_dir() else Path(tempfile.gettempdir())), encoding="utf-8") as record_tmp:
        record_path = Path(record_tmp.name)
    append_log = sentinel_dir / f"flush-execution-issues-safety-net-append.{os.getpid()}.log"
    try:
        records = write_execution_issues_records(input_file=issue_log, record_file=record_path, sha=sha, batch_path=batch_path, step_label=step_label, source_label=source_label)
        if records == 0:
            return 0, "no-records", 0, str(append_log)
        plugin_root = Path(os.environ.get("CLAUDE_PLUGIN_ROOT", Path(__file__).resolve().parents[3]))
        cmd = [sys.executable, str(plugin_root / "python" / "cli.py"), "run-log", "append", "--log-root", str(log_root), "--skill", "implement", "--run-id", run_id, "--batch", "execution-issues", "--record-file", str(record_path)]
        proc = subprocess.run(cmd, text=True, capture_output=True, check=False)
        append_log.write_text(proc.stdout + proc.stderr, encoding="utf-8")
        if proc.returncode == 0:
            return 0, "ok", records, str(append_log)
        _append_failure(issue_log=issue_log, site="flush-execution-issues-safety-net", message=f"run-log exited {proc.returncode}")
        return 1, "failed", 0, str(append_log)
    finally:
        with suppress(OSError):
            record_path.unlink()


def flush_execution_issues_safety_net_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py execution-issues flush-safety-net")
    parser.add_argument("--log-root", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--issue-log")
    parser.add_argument("--batch", default="execution-issues")
    parser.add_argument("--step-label", default="18")
    parser.add_argument("--source-label", default="execution-issues.md safety-net")
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        logging_util.emit_kv(key="FLUSH_STATUS", value="failed")
        logging_util.emit_kv(key="RECORDS", value=0)
        logging_util.emit_kv(key="ERROR", value="usage")
        return VALIDATION_FAILED_RC
    issue_log = Path(args.issue_log) if args.issue_log else Path(os.environ.get("IMPLEMENT_TMPDIR", ".")) / "execution-issues.md"
    rc, status, records, append_log = flush_execution_issues_safety_net(log_root=Path(args.log_root), run_id=args.run_id, issue_log=issue_log, batch=args.batch, step_label=args.step_label, source_label=args.source_label)
    logging_util.emit_kv(key="FLUSH_STATUS", value=status)
    logging_util.emit_kv(key="RECORDS", value=records)
    if append_log:
        logging_util.emit_kv(key="APPEND_LOG_FILE", value=append_log)
    if rc == VALIDATION_FAILED_RC:
        logging_util.emit_kv(key="ERROR", value=append_log or "validation failed")
    return rc


def flush_execution_issues_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py execution-issues flush")
    parser.add_argument("--log-root", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--issue-log")
    parser.add_argument("--batch", default="execution-issues")
    parser.add_argument("--step-label", default="7a")
    parser.add_argument("--source-label", default="execution-issues.md pre-bump")
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        logging_util.emit_kv(key="FLUSH_STATUS", value="failed")
        logging_util.emit_kv(key="RECORDS", value=0)
        logging_util.emit_kv(key="ERROR", value="usage")
        return VALIDATION_FAILED_RC
    issue_log = Path(args.issue_log) if args.issue_log else Path(os.environ.get("IMPLEMENT_TMPDIR", ".")) / "execution-issues.md"
    rc, status, records, append_log = flush_execution_issues(log_root=Path(args.log_root), run_id=args.run_id, issue_log=issue_log, batch=args.batch, step_label=args.step_label, source_label=args.source_label)
    logging_util.emit_kv(key="FLUSH_STATUS", value=status)
    logging_util.emit_kv(key="RECORDS", value=records)
    if append_log:
        logging_util.emit_kv(key="APPEND_LOG_FILE", value=append_log)
    if rc == VALIDATION_FAILED_RC:
        logging_util.emit_kv(key="ERROR", value=append_log or "validation failed")
    return rc


def append_execution_issue(log: Path, *, category: str, entry: str) -> None:
    if log.is_symlink() or (log.exists() and not log.is_file()):
        raise OSError(f"refusing to append through non-regular log file: {log}")
    text = log.read_text(encoding="utf-8") if log.exists() else ""
    if entry in text:
        return
    heading = f"### {category}"
    lines = text.splitlines()
    section_idx = next((idx for idx, line in enumerate(lines) if line == heading), -1)
    if section_idx < 0:
        text = text.rstrip() + ("\n\n" if text.strip() else "") + f"{heading}\n{entry}\n"
    else:
        insert_idx = len(lines)
        for idx in range(section_idx + 1, len(lines)):
            if lines[idx].startswith("### "):
                insert_idx = idx
                break
        while insert_idx > section_idx + 1 and lines[insert_idx - 1] == "":
            insert_idx -= 1
        lines.insert(insert_idx, entry)
        text = "\n".join(lines).rstrip() + "\n"
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(text, encoding="utf-8")


def resolve_execution_issue(log: Path, *, entry: str) -> bool:
    """Remove an open entry from the mutable log after its durable resolution.

    Committed batches remain append-only: callers first append
    :func:`execution_issue_resolution_record`, then use this helper to prevent a
    still-live copy from being merged back into the final report.
    """
    if log.is_symlink() or (log.exists() and not log.is_file()):
        raise OSError(f"refusing to resolve through non-regular log file: {log}")
    if not log.is_file():
        return False
    lines = log.read_text(encoding="utf-8").splitlines()
    try:
        lines.remove(entry)
    except ValueError:
        return False
    text = "\n".join(lines).rstrip() + "\n"
    log.write_text(text, encoding="utf-8")
    return True


def append_execution_issue_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py execution-issues append")
    parser.add_argument("--log", required=True)
    parser.add_argument("--category", default="Tool Failures")
    parser.add_argument("--entry", required=True)
    args = parser.parse_args(argv)
    append_execution_issue(Path(args.log), category=args.category, entry=args.entry)
    return 0


def _read_kv( *,path: Path, key: str) -> str:
    return larch_io.read_kv(path=path, key=key, default="", first_match=True, cr_strip="strip", on_error_default=False)


def refresh_execution_issues(implement_tmpdir: Path, *, best_effort: bool = False) -> tuple[int, bool, str]:
    if not implement_tmpdir.is_dir():
        return 0 if best_effort else 2, False, "--implement-tmpdir not found"
    issue = _read_kv(path=implement_tmpdir / "parent-issue.md", key="ISSUE_NUMBER")
    run_id = _read_kv(path=implement_tmpdir / "parent-issue.md", key="RUN_ID") or ((implement_tmpdir / "session-id").read_text(encoding="utf-8").strip() if (implement_tmpdir / "session-id").is_file() else "")
    repo = _read_kv(path=implement_tmpdir / "session-env.sh", key="REPO")
    if not issue or issue == "0":
        return 0, True, "issue-not-set"
    if not issue.isdigit():
        return 0 if best_effort else 1, False, "ISSUE_NUMBER must be numeric"
    issue_log = implement_tmpdir / "execution-issues.md"
    count = 0
    if issue_log.is_file() and issue_log.stat().st_size:
        count = sum(1 for line in issue_log.read_text(encoding="utf-8", errors="replace").splitlines() if line.startswith("- "))
    summary = implement_tmpdir / "summary-metadata.md"
    existing = summary.read_text(encoding="utf-8") if summary.is_file() else ""
    kept = [line for line in existing.splitlines() if not re.match(r"Execution issues pending flush: `[^`]*`$", line)] if existing else [f"Run ID: `{run_id}`", f"Logs: `larch-logs/implement/{run_id}/`", f"Tracking issue: #{issue}"]
    kept.append(f"Execution issues pending flush: `{count}`")
    summary.write_text("\n".join(kept) + "\n", encoding="utf-8")
    plugin_root = Path(os.environ.get("CLAUDE_PLUGIN_ROOT", Path(__file__).resolve().parents[3]))
    cmd = [sys.executable, str(plugin_root / "python" / "cli.py"), "tracking-issue", "upsert-summary", "--issue", issue, "--marker", f"<!-- larch:metadata v1 runid={run_id} -->", "--content-file", str(summary)]
    if repo:
        cmd += ["--repo", repo]
    proc = subprocess.run(cmd, text=True, capture_output=True, check=False)
    (implement_tmpdir / "refresh-execution-issues.out").write_text(proc.stdout, encoding="utf-8")
    (implement_tmpdir / "refresh-execution-issues.err").write_text(proc.stderr, encoding="utf-8")
    if proc.returncode == 0:
        return 0, True, ""
    return 0 if best_effort else 1, False, " ".join(proc.stderr.split())[:500]


def refresh_execution_issues_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py execution-issues refresh")
    parser.add_argument("--implement-tmpdir", default="")
    parser.add_argument("--best-effort", action="store_true")
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        logging_util.emit_kv(key="REFRESHED", value="false")
        logging_util.emit_kv(key="ERROR", value="usage")
        return VALIDATION_FAILED_RC
    raw_tmpdir = args.implement_tmpdir or os.environ.get(config.ENV_IMPLEMENT_TMPDIR, "")
    if not raw_tmpdir:
        logging_util.emit_kv(key="REFRESHED", value="false")
        logging_util.emit_kv(key="ERROR", value="--implement-tmpdir is required or IMPLEMENT_TMPDIR must be set")
        return VALIDATION_FAILED_RC
    rc, refreshed, reason = refresh_execution_issues(Path(raw_tmpdir), best_effort=args.best_effort)
    logging_util.emit_kv(key="REFRESHED", value=refreshed)
    if reason:
        logging_util.emit_kv(key="REASON" if refreshed else "ERROR", value=reason)
    return rc
