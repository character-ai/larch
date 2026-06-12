# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false, reportOptionalSubscript=false, reportOptionalMemberAccess=false, reportPossiblyUnboundVariable=false, reportUnnecessaryComparison=false, reportUnknownLambdaType=false, reportArgumentType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnusedImport=false, reportUnusedFunction=false, reportPrivateUsage=false, reportUnusedVariable=false
# ruff: noqa: SIM115
# pylint: skip-file
"""Combine-issues helper CLI verbs."""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
import time
from pathlib import Path

import proc
import redact

_BUSY_RE = re.compile(r"^\[(DESIGNING|IMPLEMENTING|STALLED|DONE|PLANNED|IN PROGRESS|LOCKED)\]\s")
_OOS_RE = re.compile(r"^\[OOS\]\s")


def _repo() -> str | None:
    res = proc.run(["gh", "repo", "view", "--json", "nameWithOwner"])
    if res.returncode != 0:
        return None
    try:
        data = json.loads(res.stdout)
    except json.JSONDecodeError:
        return None
    val = data.get("nameWithOwner") if isinstance(data, dict) else None
    return str(val) if val else None


def fetch_main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="cli.py combine-issues fetch")
    p.add_argument("--repo", default="")
    p.add_argument("--oos", action="store_true")
    args = p.parse_args(argv)
    repo = args.repo or _repo()
    if not repo:
        print("ERROR=Could not determine repository", file=sys.stderr)
        return 1
    res = proc.run(["gh", "issue", "list", "--repo", repo, "--state", "open", "--limit", "200", "--json", "number,title,body,labels"])
    if res.returncode != 0:
        print(f"ERROR=Failed to fetch issues from {repo}", file=sys.stderr)
        return 1
    try:
        raw = json.loads(res.stdout or "[]")
    except json.JSONDecodeError:
        print(f"ERROR=Failed to fetch issues from {repo}", file=sys.stderr)
        return 1
    if not isinstance(raw, list):
        print(f"ERROR=Failed to fetch issues from {repo}", file=sys.stderr)
        return 1
    out = []
    for issue in raw:
        if not isinstance(issue, dict):
            continue
        title = str(issue.get("title") or "")
        if args.oos:
            if _OOS_RE.match(title):
                out.append(issue)
        elif not _BUSY_RE.match(title):
            out.append(issue)
    handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", prefix="combine-issues-", dir="/tmp", delete=False)
    Path(handle.name).chmod(0o600)
    json.dump(out, handle)
    handle.write("\n")
    handle.close()
    print(f"ISSUES_FILE={handle.name}")
    print(f"COUNT={len(out)}")
    return 0


def _parse_issue_number(text: str) -> str:
    nums = re.findall(r"/issues/([0-9]+)", text)
    return nums[-1] if nums else ""


def _close_issue_with_retry(issue: str, repo: str, combined: str, *, attempts: int = 3) -> proc.CommandResult:
    result: proc.CommandResult | None = None
    for attempt in range(attempts):
        result = proc.run(["gh", "issue", "close", issue, "--repo", repo, "--comment", f"Combined into #{combined}"])
        if result.returncode == 0:
            return result
        if attempt + 1 < attempts:
            time.sleep(1)
    assert result is not None
    return result


def apply_main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="cli.py combine-issues apply")
    p.add_argument("--title", required=True)
    p.add_argument("--body-file", required=True)
    p.add_argument("--source-issues", required=True)
    p.add_argument("--repo", default="")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)
    body = Path(args.body_file)
    if not body.is_file():
        print(f"ERROR=Missing or unreadable --body-file: {args.body_file}", file=sys.stderr)
        return 1
    repo = args.repo or _repo()
    if not repo:
        print("ERROR=Could not determine repository", file=sys.stderr)
        return 1
    issues = [x.strip() for x in args.source_issues.split(",") if x.strip()]
    if not issues:
        print("ERROR=No source issues provided", file=sys.stderr)
        return 1
    if args.dry_run:
        print("DRY_RUN=true")
        print(f"WOULD_CREATE={args.title}")
        print(f"WOULD_CLOSE={len(issues)} issues: {args.source_issues}")
        return 0
    red_title = redact.redact(args.title).rstrip("\n")
    red_body = tempfile.NamedTemporaryFile("w", encoding="utf-8", prefix="combine-redacted-", dir="/tmp", delete=False)
    red_body.write(redact.redact(body.read_text(encoding="utf-8")))
    red_body.close()
    try:
        create = proc.run(["gh", "issue", "create", "--repo", repo, "--title", red_title, "--body-file", red_body.name])
        if create.returncode != 0:
            print(f"ERROR=Failed to create combined issue: {create.stderr or create.stdout}", file=sys.stderr)
            return 1
        combined = _parse_issue_number(create.stdout + create.stderr)
        if not combined:
            print(f"ERROR=Could not parse issue number from gh output: {create.stdout + create.stderr}", file=sys.stderr)
            return 1
        closed = 0
        warnings = []
        for issue in issues:
            res = _close_issue_with_retry(issue, repo, combined)
            if res.returncode == 0:
                closed += 1
            else:
                warnings.append(f"Failed to close #{issue}: {redact.redact((res.stderr or res.stdout)[:500]).strip()}")
        if warnings:
            print(f"WARNING={'; '.join(warnings)}", file=sys.stderr)
        print("DRY_RUN=false")
        print(f"COMBINED_ISSUE={combined}")
        print(f"CLOSED_ISSUES={closed}")
        return 0
    finally:
        Path(red_body.name).unlink(missing_ok=True)
