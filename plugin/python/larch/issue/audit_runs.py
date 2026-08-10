# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false, reportOptionalSubscript=false, reportOptionalMemberAccess=false, reportPossiblyUnboundVariable=false, reportUnnecessaryComparison=false, reportUnknownLambdaType=false, reportArgumentType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnusedImport=false, reportUnusedFunction=false, reportPrivateUsage=false, reportUnusedVariable=false
# ruff: noqa: E701, E702, PERF401, SIM115
# pylint: skip-file
"""Python-owned audit report title and mutation helpers.

The scan, mapping, counter, preflight, resolver, and Pacific-clock verbs are
Rust-owned. This module retains only the report title and operator-authorized
backlog/close helpers that still have Python callers.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from larch.core import config
from larch.state import session_env as _session_env_audit
from larch.core import proc
from larch.core.repo_roots import larch_entrypoint
from larch.errors import ShipError
from larch.git import gh
from larch.issue.title_match import BUG_PREFIX, bug_title_match

_DESIGN_RUN_TITLE_RE = re.compile(r"^chore\(larch-logs\): design run [0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12}(?: \(issue #[0-9]+\))?$")


def _validate_skill( *,skill: str, prog: str) -> bool:
    if skill in {"design", "implement"}:
        return True
    msg = f"{prog}: --skill is required (allowed: design, implement)" if not skill else f"{prog}: --skill must be design or implement (got: {skill})"
    print(msg, file=sys.stderr)
    return False


def match_audit_report_title( *,skill: str, title: str) -> bool:
    if skill == "implement":
        return bool(re.match(r"^\[(Run Logs Audit |Implement Run Logs Audit ).* Report\]", title))
    if skill == "design":
        return bool(re.match(r"^\[Design Run Logs Audit .* Report\]", title))
    return False


def match_design_run_log_pr_title(title: str) -> bool:
    return bool(_DESIGN_RUN_TITLE_RE.match(title or ""))


def title_match_main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="cli.py audit-runs title-match")
    p.add_argument("--skill", required=True)
    p.add_argument("--title", required=True)
    args = p.parse_args(argv)
    if not _validate_skill(skill=args.skill, prog="audit-title-matcher.sh"):
        return 1
    return 0 if match_audit_report_title(skill=args.skill, title=args.title) else 1


def title_main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="cli.py audit-runs title")
    p.add_argument("--skill", required=True)
    p.add_argument("--pr-list", required=True)
    p.add_argument("--timestamp", required=True)
    args = p.parse_args(argv)
    if not _validate_skill(skill=args.skill, prog="audit-title.sh"):
        return 1
    nums = sorted({int(tok.strip()) for tok in args.pr_list.split(",") if tok.strip().isdigit()})
    if not nums:
        print("audit-title.sh: --pr-list contains no valid PR numbers", file=sys.stderr)
        return 1
    prefix = "Implement Run Logs Audit" if args.skill == "implement" else "Design Run Logs Audit"
    if len(nums) == 1:
        prs = f"#{nums[0]}"
    elif nums[-1] - nums[0] + 1 == len(nums):
        prs = f"#{nums[0]}-#{nums[-1]}"
    else:
        prs = f"#{nums[0]}-#{nums[-1]} ({len(nums)} total)"
    print(f"TITLE=[{prefix} {args.timestamp} Report] PRs {prs}")
    return 0


def _parse_utc_instant(raw: str) -> datetime | None:
    text = (raw or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _iso_z(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _valid_repo(value: str) -> bool:
    return re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", value or "") is not None


def _bugs_backlog_nudge_issue_rows(*, repo: str, boundary: str) -> list[dict[str, object]] | None:
    try:
        parsed = gh.issue_list_read(
            proc,
            repo=repo,
            state="closed",
            fields=("number", "title", "closedAt"),
            search=f"{BUG_PREFIX} in:title closed:>{boundary}",
            limit=100000,
        )
    except ShipError as exc:
        reason = str(exc).strip() or "gh issue list failed"
        if "JSON parse failed" in reason:
            print(
                f"audit-runs bugs-backlog-nudge: gh issue list returned invalid JSON: {reason}",
                file=sys.stderr,
            )
        else:
            print(f"audit-runs bugs-backlog-nudge: gh issue list failed: {reason}", file=sys.stderr)
        return None
    rows: list[dict[str, object]] = []
    for row in parsed:
        if isinstance(row, dict):
            rows.append(dict(row))
    return rows


def _bugs_backlog_nudge_count(*, repo: str, boundary: datetime) -> int | None:
    rows = _bugs_backlog_nudge_issue_rows(repo=repo, boundary=_iso_z(boundary))
    if rows is None:
        return None
    count = 0
    for row in rows:
        if not bug_title_match(str(row.get("title") or "")):
            continue
        closed_at = _parse_utc_instant(str(row.get("closedAt") or ""))
        if closed_at is not None and closed_at > boundary:
            count += 1
    return count


def _learn_from_bugs_scan_boundary(root: Path) -> tuple[str, str] | None:
    """Read the Rust-owned durable marker through its public wire contract."""
    result = proc.run(
        [
            str(larch_entrypoint(Path(__file__).resolve().parents[3])),
            "learn-from-bugs",
            "read-state",
            "--root",
            str(root),
        ]
    )
    if result.returncode != 0:
        return None
    required = ("LEARN_FROM_BUGS_STATE_FOUND", "REPO", "RUN_DATE")
    rows: dict[str, str] = {}
    counts = dict.fromkeys(required, 0)
    for line in result.stdout.splitlines():
        for key in (*required, "SCAN_STARTED_AT"):
            prefix = f"{key}="
            if line.startswith(prefix):
                rows[key] = line.removeprefix(prefix)
                if key in counts:
                    counts[key] += 1
    if rows.get("LEARN_FROM_BUGS_STATE_FOUND") != "true":
        return None
    if any(counts[key] != 1 for key in required):
        return None
    boundary = rows.get("SCAN_STARTED_AT") or rows["RUN_DATE"]
    return rows["REPO"], boundary


def bugs_backlog_nudge_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py audit-runs bugs-backlog-nudge", allow_abbrev=False)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--root", required=True)
    args = parser.parse_args(argv)
    repo = str(args.repo)
    if not _valid_repo(repo):
        print("audit-runs bugs-backlog-nudge: --repo must be OWNER/REPO", file=sys.stderr)
        return 2
    scan = _learn_from_bugs_scan_boundary(Path(args.root))
    if scan is not None and scan[0].lower() != repo.lower():
        scan = None
    boundary_raw = "" if scan is None else scan[1]
    boundary = _parse_utc_instant(boundary_raw)
    if scan is None or boundary is None:
        print("Advisory: /learn-from-bugs has never run for this repo; consider running /learn-from-bugs.")
        return 0
    count = _bugs_backlog_nudge_count(repo=repo, boundary=boundary)
    if count is None:
        return 1
    if count > config.LEARN_FROM_BUGS_NUDGE_THRESHOLD:
        print(
            f"Advisory: {count} closed [BUG] issues accumulated since the last /learn-from-bugs scan; "
            "consider running /learn-from-bugs."
        )
    return 0


def _issue_state_closed(*, num: str, repo: str) -> bool:
    """Re-read issue state after a close so a silently-open prior is not reported closed (G-Py-8)."""
    view = gh.issue_view_field_read(proc, num, "state", repo=repo)
    if view.returncode != 0:
        return False
    try:
        data: object = json.loads(view.stdout or "{}")
    except json.JSONDecodeError:
        return False
    return isinstance(data, dict) and str(data.get("state") or "").lower() == "closed"


def _close_prior_issue(*, num: str, repo: str) -> str | None:
    """Close one prior and confirm the close landed; return a CLOSE_FAILED reason or None on a verified close."""
    if gh.issue_close(proc, num, repo=repo).returncode != 0:
        return "gh issue close failed"
    if not _issue_state_closed(num=num, repo=repo):
        return config.CLOSE_POSTCONDITION_UNVERIFIED
    return None


def close_priors_main(argv: list[str] | None = None) -> int:
    p=argparse.ArgumentParser(prog="cli.py audit-runs close-priors"); p.add_argument("--skill",required=True); p.add_argument("--new-issue-number",required=True); p.add_argument("--repo",default="character-ai/larch"); p.add_argument("--operator-invoked",action="store_true"); args=p.parse_args(argv)
    if not _validate_skill(skill=args.skill,prog="audit-close-priors.sh"): return 1
    _authorized, _auth_reason = _session_env_audit.check_live_mutation_auth(context_file=None, operator_mode=bool(getattr(args, "operator_invoked", False)))
    if not _authorized:
        print(f"CLOSE_PRIORS_REFUSED=true\nREASON={config.LIVE_MUTATION_REFUSAL_REASON}:{_auth_reason}")
        return config.EXIT_MUTATION_REFUSED
    try:
        arr = gh.issue_list_read(
            proc,
            repo=args.repo,
            state="open",
            fields=("number", "title"),
            labels=("audit-report",),
            limit=100000,
        )
    except ShipError as exc:
        reason = str(exc)
        if "JSON parse failed" in reason:
            print("ISSUE_LIST_FAILED=true\nREASON=gh issue list returned invalid JSON")
        else:
            print("ISSUE_LIST_FAILED=true\nREASON=gh issue list failed")
        return 1
    body: Path | None = None
    try:
        handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False)
        try:
            handle.write(f"Superseded by #{args.new_issue_number}")
            body = Path(handle.name)
        finally:
            handle.close()
    except OSError:
        print("BODY_FILE_FAILED=true\nREASON=mktemp failed")
        return 1
    try:
        for issue in arr:
            if not isinstance(issue,dict): continue
            num=str(issue.get("number") or "")
            if num==args.new_issue_number or not match_audit_report_title(skill=args.skill,title=str(issue.get("title") or "")): continue
            if gh.command(proc, ["issue","comment",num,"--repo",args.repo,"--body-file",str(body)]).returncode!=0: print(f"CLOSE_FAILED={num}\tREASON=gh issue comment failed"); continue
            reason = _close_prior_issue(num=num, repo=args.repo)
            if reason is not None: print(f"CLOSE_FAILED={num}\tREASON={reason}"); continue
            print(f"CLOSED_NUMBER={num}")
    finally:
        if body is not None:
            body.unlink(missing_ok=True)
    return 0
# pyright: reportReturnType=false
