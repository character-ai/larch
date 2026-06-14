"""Python Step 7a orchestration for /implement."""

# pyright: reportUnusedCallResult=false

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

import execution_issues
import pr_body


def emit(key: str, value: object) -> None:
    print(f"{key}={value}")


def _read_kv(path: Path, key: str, default: str = "") -> str:
    if not path.is_file():
        return default
    prefix = key + "="
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith(prefix):
            return line[len(prefix):].strip("\r")
    return default


def run_step7a(implement_tmpdir: Path, *, base_remote: str = "origin", base_ref: str = "main") -> int:
    implement_tmpdir.mkdir(parents=True, exist_ok=True)
    diagram_rc, diagram_status, diagram_path, _reason = pr_body.generate_code_flow_diagram(implement_tmpdir, base_remote=base_remote, base_ref=base_ref)
    comment_url = ""
    if diagram_status == "ok" and diagram_path:
        upsert = subprocess.run([sys.executable, str(Path(__file__).resolve().parent / "cli.py"), "diagrams", "upsert", "--diagram-file", diagram_path], text=True, capture_output=True, check=False)
        m = None
        if upsert.returncode == 0:
            m = re.search(r"^COMMENT_URL=(.*)$", upsert.stdout, re.MULTILINE)
        comment_url = m.group(1) if m else ""
    run_id = _read_kv(implement_tmpdir / "ship-pr-state.sh", "RUN_ID") or ((implement_tmpdir / "session-id").read_text(encoding="utf-8").strip() if (implement_tmpdir / "session-id").is_file() else "")
    log_flush_status = "skip"
    if run_id:
        log_root = implement_tmpdir / "larch-logs"
        rc, log_flush_status, _records, _append_log = execution_issues.flush_execution_issues(log_root=log_root, run_id=run_id, issue_log=implement_tmpdir / "execution-issues.md")
        if rc not in {0, 1, 2}:
            log_flush_status = "failed"
    rebase_outcome = "skipped"
    relay = implement_tmpdir / "7a.r"
    if relay.is_file():
        rebase_outcome = relay.read_text(encoding="utf-8", errors="replace").strip() or "requested"
    bail = "" if diagram_rc == 0 else "diagram-failed"
    emit("DIAGRAM_STATUS", diagram_status)
    emit("DIAGRAM_PATH", diagram_path)
    emit("COMMENT_URL", comment_url)
    emit("LOG_FLUSH_STATUS", log_flush_status)
    emit("STEP_7A_BAIL_REASON", bail)
    emit("REBASE_OUTCOME", rebase_outcome)
    return 0 if not bail else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py implement step-7a")
    parser.add_argument("--implement-tmpdir", default=os.environ.get("IMPLEMENT_TMPDIR", ""))
    parser.add_argument("--base-remote", default="origin")
    parser.add_argument("--base-ref", default="main")
    args, _unknown = parser.parse_known_args(argv)
    if not args.implement_tmpdir:
        emit("DIAGRAM_STATUS", "failed")
        emit("DIAGRAM_PATH", "")
        emit("COMMENT_URL", "")
        emit("LOG_FLUSH_STATUS", "skip")
        emit("STEP_7A_BAIL_REASON", "missing-implement-tmpdir")
        emit("REBASE_OUTCOME", "skipped")
        return 2
    return run_step7a(Path(args.implement_tmpdir), base_remote=args.base_remote, base_ref=args.base_ref)
