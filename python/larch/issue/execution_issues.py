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
from larch import io as larch_io
from larch.core import config

VALIDATION_FAILED_RC = 2


def emit_kv( *,key: str, value: object) -> None:
    print(f"{key}={value}")


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def normalize_body_for_hash(text: str) -> str:
    lines = text.splitlines()
    if lines and lines[0].startswith("### "):
        lines = lines[1:]
    start = 0
    while start < len(lines) and not lines[start].strip():
        start += 1
    end = len(lines)
    while end > start and not lines[end - 1].strip():
        end -= 1
    return "\n".join(lines[start:end]) + ("\n" if end > start else "")


def _sections(text: str) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = []
    current = "Tool Failures"
    body: list[str] = []
    for line in text.splitlines():
        if line.startswith("### "):
            if body:
                sections.append((current, "\n".join(body) + "\n"))
            current = line[4:].strip() or "Tool Failures"
            body = []
        else:
            body.append(line)
    if body:
        sections.append((current, "\n".join(body) + "\n"))
    return [(cat, body) for cat, body in sections if body.strip()]


def execution_issues_batch_contains_all_sections( *,input_file: str | Path, batch_path: str | Path) -> bool:
    batch = Path(batch_path)
    if not batch.is_file():
        return False
    text = Path(input_file).read_text(encoding="utf-8", errors="replace")
    batch_text = batch.read_text(encoding="utf-8", errors="replace")
    saw = False
    for _cat, body in _sections(text):
        norm_sha = hashlib.sha256(normalize_body_for_hash(body).encode()).hexdigest()
        if f'"source_sha256":"{norm_sha}"' not in batch_text:
            return False
        saw = True
    return saw


def write_execution_issues_records( *,input_file: str | Path, record_file: str | Path, sha: str, batch_path: str | Path | None = None, step_label: str = "18", source_label: str = "execution-issues.md safety-net") -> int:
    source = Path(input_file)
    batch_text = Path(batch_path).read_text(encoding="utf-8", errors="replace") if batch_path and Path(batch_path).is_file() else ""
    records: list[str] = []
    for category, body in _sections(source.read_text(encoding="utf-8", errors="replace")):
        norm = normalize_body_for_hash(body)
        norm_sha = hashlib.sha256(norm.encode()).hexdigest() if norm else sha
        if norm_sha and f'"source_sha256":"{norm_sha}"' in batch_text:
            continue
        records.append(json.dumps({
            "phase": "implement",
            "step": step_label,
            "category": category,
            "source": source_label,
            "source_sha256": norm_sha or sha,
            "body": body,
        }, separators=(",", ":")))
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
        emit_kv(key="FLUSH_STATUS", value="failed")
        emit_kv(key="RECORDS", value=0)
        emit_kv(key="ERROR", value="usage")
        return VALIDATION_FAILED_RC
    issue_log = Path(args.issue_log) if args.issue_log else Path(os.environ.get("IMPLEMENT_TMPDIR", ".")) / "execution-issues.md"
    rc, status, records, append_log = flush_execution_issues_safety_net(log_root=Path(args.log_root), run_id=args.run_id, issue_log=issue_log, batch=args.batch, step_label=args.step_label, source_label=args.source_label)
    emit_kv(key="FLUSH_STATUS", value=status)
    emit_kv(key="RECORDS", value=records)
    if append_log:
        emit_kv(key="APPEND_LOG_FILE", value=append_log)
    if rc == VALIDATION_FAILED_RC:
        emit_kv(key="ERROR", value=append_log or "validation failed")
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
        emit_kv(key="FLUSH_STATUS", value="failed")
        emit_kv(key="RECORDS", value=0)
        emit_kv(key="ERROR", value="usage")
        return VALIDATION_FAILED_RC
    issue_log = Path(args.issue_log) if args.issue_log else Path(os.environ.get("IMPLEMENT_TMPDIR", ".")) / "execution-issues.md"
    rc, status, records, append_log = flush_execution_issues(log_root=Path(args.log_root), run_id=args.run_id, issue_log=issue_log, batch=args.batch, step_label=args.step_label, source_label=args.source_label)
    emit_kv(key="FLUSH_STATUS", value=status)
    emit_kv(key="RECORDS", value=records)
    if append_log:
        emit_kv(key="APPEND_LOG_FILE", value=append_log)
    if rc == VALIDATION_FAILED_RC:
        emit_kv(key="ERROR", value=append_log or "validation failed")
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
        emit_kv(key="REFRESHED", value="false")
        emit_kv(key="ERROR", value="usage")
        return VALIDATION_FAILED_RC
    raw_tmpdir = args.implement_tmpdir or os.environ.get(config.ENV_IMPLEMENT_TMPDIR, "")
    if not raw_tmpdir:
        emit_kv(key="REFRESHED", value="false")
        emit_kv(key="ERROR", value="--implement-tmpdir is required or IMPLEMENT_TMPDIR must be set")
        return VALIDATION_FAILED_RC
    rc, refreshed, reason = refresh_execution_issues(Path(raw_tmpdir), best_effort=args.best_effort)
    emit_kv(key="REFRESHED", value=str(refreshed).lower())
    if reason:
        emit_kv(key="REASON" if refreshed else "ERROR", value=reason)
    return rc
