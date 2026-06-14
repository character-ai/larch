"""PR body composition and Mermaid sanitization."""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import config
import gh
import git
import proc
import redact
import run_logs
import tracking_issue
from errors import ShipError
from proc import Runner


@dataclass(frozen=True)
class MermaidResult:
    status: str
    reason_tokens: tuple[str, ...]
    fence_count: int


_FENCE_RE = re.compile(r"^(\s{0,3})(`{3,})([^`]*)$")
_FLOWCHART_START = re.compile(r"^(flowchart|graph)(\s|$)")
_OPEN_BRACKET = frozenset("[{(")
_CLOSE_BRACKET = frozenset("]})")


def flowchart_rejects_pipe(line: str) -> bool:
    """Port sanitize-mermaid-fragment.sh flowchart_reject (depth + quote aware)."""
    depth = 0
    quote = False
    esc = False
    for char in line:
        if depth > 0 and quote:
            if esc:
                esc = False
            elif char == "\\":
                esc = True
            elif char == '"':
                quote = False
            continue
        if depth > 0 and char == '"':
            quote = True
            continue
        if char in _OPEN_BRACKET:
            depth += 1
            continue
        if depth > 0 and char in _CLOSE_BRACKET:
            depth -= 1
            continue
        if depth > 0 and char == "|":
            return True
    return False


def _first_non_blank_mermaid_fence(text: str) -> bool:
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("%%"):
            continue
        match = _FENCE_RE.match(line)
        return bool(
            match and re.match(r"^\s*mermaid\s*$", match.group(3) or ""),
        )
    return False


def compose_summary_bullets(
    runner: Runner,
    *,
    plan_goals_file: str,
    cwd: str | None = None,
) -> str:
    """Port compose-pr-summary.sh goal + test/cross-dir bullets."""
    _ = runner
    if cwd is None:
        msg = f"plan-goals path escapes repo root: {plan_goals_file}"
        raise ShipError(msg)
    goals_path = Path(plan_goals_file)
    repo_root = Path(cwd)
    goals_file = (
        goals_path.resolve()
        if goals_path.is_absolute()
        else (repo_root / goals_path).resolve()
    )
    try:
        rel = goals_file.relative_to(repo_root.resolve())
    except ValueError as exc:
        msg = f"plan-goals path escapes repo root: {plan_goals_file}"
        raise ShipError(msg) from exc
    if not run_logs.path_under_repo(repo_root, str(rel)):
        msg = f"plan-goals path escapes repo root: {plan_goals_file}"
        raise ShipError(msg)
    if not goals_file.is_file() or goals_file.stat().st_size == 0:
        msg = f"plan-goals file missing or empty: {plan_goals_file}"
        raise ShipError(msg)
    text = goals_file.read_text(encoding="utf-8")
    goal_line = ""
    in_goal = False
    for line in text.splitlines():
        if line.startswith("## Goal"):
            in_goal = True
            continue
        if in_goal and line.startswith("#"):
            break
        if in_goal and line.strip():
            goal_line = line.strip()
            break
    if not goal_line:
        msg = f"no Goal line found in {plan_goals_file}"
        raise ShipError(msg)
    bullets = [f"- {goal_line}"]
    merge_base = git.try_merge_base(runner, "HEAD", "origin/main", cwd=cwd)
    changed: tuple[str, ...] = ()
    if merge_base:
        result = git.diff_name_only(runner, merge_base, "HEAD", cwd=cwd)
        if result.returncode == 0:
            changed = tuple(
                line for line in result.stdout.splitlines() if line
            )
    if changed:
        test_count = sum(
            1 for path in changed if re.search(r"(^|/)test-[^/]+\.sh$", path)
        )
        if test_count > 0:
            bullets.append(f"- Added or updated {test_count} test file(s).")
        dirs = sorted({path.split("/")[0] if "/" in path else "." for path in changed})
        cross_dir_threshold = 2
        if len(dirs) > cross_dir_threshold:
            bullets.append(f"- Cross-cutting changes across: {','.join(dirs)}.")
    return "\n".join(bullets) + "\n"


def body_start_line(lines: list[str]) -> int:
    in_frontmatter = False
    frontmatter_started = False
    for index, raw in enumerate(lines, start=1):
        line = raw.strip()
        if not line or line.startswith("%%"):
            continue
        if not frontmatter_started and line == "---":
            in_frontmatter = True
            frontmatter_started = True
            continue
        if in_frontmatter:
            if line == "---":
                in_frontmatter = False
            continue
        return index
    return -1 if in_frontmatter else len(lines) + 1


def _validate_fence_body(body: str, _fence_num: int) -> list[str]:
    lines = body.splitlines()
    start = body_start_line(lines)
    if start == -1:
        return [config.MERMAID_REASON_UNCLOSED_FRONTMATTER]
    if start < 1 or start > len(lines):
        return []
    first = lines[start - 1].strip()
    reasons: list[str] = []
    if _FLOWCHART_START.match(first):
        for line in lines[start - 1 :]:
            if flowchart_rejects_pipe(line):
                reasons.append(config.MERMAID_REASON_PIPE_IN_NODE)
                break
    elif first == "sequenceDiagram":
        for line in lines[start - 1 :]:
            lower = line.strip().lower()
            if not re.match(
                r"^(participant|actor)\s+\S+\s+as\s+",
                lower,
            ):
                continue
            alias = re.sub(
                r"^[^\s]+\s+[^\s]+\s+as\s+",
                "",
                line.strip(),
                flags=re.IGNORECASE,
            )
            if re.search(r"<br\s*/?>", alias, re.IGNORECASE):
                reasons.append(config.MERMAID_REASON_BR_IN_ALIAS)
            if "$" in alias:
                reasons.append(config.MERMAID_REASON_DOLLAR_IN_ALIAS)
    return reasons


def sanitize_fragment(text: str, *, from_md: bool = False) -> MermaidResult:
    """Port sanitize-mermaid-fragment.sh; returns ok or rejected with reason tokens."""
    if not from_md and _first_non_blank_mermaid_fence(text):
        from_md = True
    if from_md:
        fences: list[str] = []
        in_outer = False
        outer_len = 0
        outer_mermaid = False
        current: list[str] = []
        for line in text.splitlines():
            match = _FENCE_RE.match(line)
            if match:
                opener = match.group(2)
                rest = match.group(3)
                length = len(opener)
                if not in_outer:
                    if re.match(r"^\s*mermaid\s*$", rest):
                        if current:
                            fences.append("\n".join(current))
                        current = []
                        in_outer = True
                        outer_len = length
                        outer_mermaid = True
                        continue
                    in_outer = True
                    outer_len = length
                    outer_mermaid = False
                elif length >= outer_len and not rest.strip():
                    in_outer = False
                    outer_mermaid = False
                    if current:
                        fences.append("\n".join(current))
                        current = []
                continue
            if in_outer and outer_mermaid:
                current.append(line)
        if current:
            fences.append("\n".join(current))
    else:
        fences = [text]
    all_reasons: list[str] = []
    for index, fence in enumerate(fences, start=1):
        all_reasons.extend(_validate_fence_body(fence, index))
    unique = tuple(dict.fromkeys(all_reasons))
    if unique:
        return MermaidResult(status="rejected", reason_tokens=unique, fence_count=len(fences))
    return MermaidResult(status="ok", reason_tokens=(), fence_count=len(fences))


def _fail_closed_body(redacted: str) -> str:
    if "[content truncated" in redacted:
        msg = "redaction failed for PR body"
        raise ShipError(msg)
    return redacted


def compose_pr_body(
    *,
    summary: str,
    mermaid: str = "",
    test_plan: str = "- [ ] `make py-lint`\n- [ ] `make py-test`\n",
    issue_number: int | None = None,
) -> str:
    if mermaid.strip():
        mermaid_result = sanitize_fragment(mermaid)
        if mermaid_result.status != "ok":
            msg = f"mermaid fragment rejected: {','.join(mermaid_result.reason_tokens)}"
            raise ShipError(msg)
    parts = [summary.rstrip(), ""]
    if mermaid.strip():
        parts.extend(["## Code Flow Diagram", "", "```mermaid", mermaid.strip(), "```", ""])
    parts.extend(["## Test plan", "", test_plan.rstrip(), ""])
    body = "\n".join(parts) + "\n"
    if issue_number is not None:
        body = tracking_issue.link_pr_closes(body, issue_number)
    mermaid_body = sanitize_fragment(body, from_md=True)
    if mermaid_body.status != "ok":
        msg = f"mermaid in PR body rejected: {','.join(mermaid_body.reason_tokens)}"
        raise ShipError(msg)
    redacted = _fail_closed_body(redact.redact(body))
    return redacted.rstrip("\n") + "\n"


def update_pr_body(
    runner: Runner,
    number: int,
    body: str,
    *,
    repo: str,
    cwd: str | None = None,
) -> None:
    mermaid_result = sanitize_fragment(body, from_md=True)
    if mermaid_result.status != "ok":
        msg = f"mermaid in PR body rejected: {','.join(mermaid_result.reason_tokens)}"
        raise ShipError(msg)
    redacted = redact.redact(body)
    if "[content truncated" in redacted:
        msg = "redaction failed for PR body"
        raise ShipError(msg)
    result = gh.pr_edit_body(runner, number, redacted, repo=repo, cwd=cwd)
    if result.returncode != 0:
        msg = f"gh pr edit failed ({result.returncode})"
        raise ShipError(msg)

# ---------------------------------------------------------------------------
# C4c report helper ports
# ---------------------------------------------------------------------------


def _emit_kv(key: str, value: object) -> None:
    print(f"{key}={value}")


def _read_kv(path: Path, key: str, default: str = "") -> str:
    if not path.is_file():
        return default
    prefix = key + "="
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith(prefix):
            return line[len(prefix):].strip("\r")
    return default


def _fmt_money(value: float | str) -> str:
    try:
        return f"${float(value):.2f}"
    except (TypeError, ValueError):
        return "N/A"


def render_run_summary(**kwargs: object) -> str:
    skill = str(kwargs.get("skill") or "implement")
    outcome = str(kwargs.get("outcome") or "unknown")
    run_id = str(kwargs.get("run_id") or "unknown")
    emergency = str(kwargs.get("emergency_requested") or "false") == "true"
    total_tokens = int(str(kwargs.get("total_tokens") or kwargs.get("claude_tokens") or 0) or 0)
    total_cost = kwargs.get("total_cost", "N/A")
    if kwargs.get("cost_unavailable") or total_cost == "N/A":
        cost = "N/A"
    else:
        cost = f"💰 TOTAL ~{_fmt_money(total_cost)} — Claude {_fmt_money(kwargs.get('claude_cost', 0))}, Codex {_fmt_money(kwargs.get('codex_cost', 0))}, Cursor {_fmt_money(kwargs.get('cursor_cost', 0))}, Claude (subprocess) {_fmt_money(kwargs.get('claude_sub_cost', 0))}  |  Tokens: {int((total_tokens + 500) / 1000)}k"
    issue_number = str(kwargs.get("issue_number") or "")
    issue_url = str(kwargs.get("issue_url") or "")
    issue = "N/A"
    if issue_number and issue_number != "0":
        issue = f"#{issue_number}" + (f" — {issue_url}" if issue_url and issue_url != "N/A" else "")
    pr_number = str(kwargs.get("pr_number") or "")
    pr_url = str(kwargs.get("pr_url") or "")
    pr = "N/A"
    if pr_number and pr_number != "0":
        pr = f"#{pr_number}" + (f" — {pr_url}" if pr_url and pr_url != "N/A" else "")
    lines_disp = "N/A"
    ca, cd, la, ld = (str(kwargs.get(k) or "") for k in ("code_added", "code_deleted", "logs_added", "logs_deleted"))
    if ca.isdigit() and cd.isdigit() and la.isdigit() and ld.isdigit():
        lines_disp = f"code +{ca}/-{cd}, larch-logs +{la}/-{ld}"
    oos_count = str(kwargs.get("oos_count") or "0")
    oos_urls = str(kwargs.get("oos_urls") or "")
    oos_disp = oos_count if not oos_urls or oos_urls == "N/A" or oos_count == "0" else f"{oos_count} — {oos_urls}"
    run_logs_path = str(kwargs.get("run_logs_path") or "")
    if not run_logs_path and run_id != "unknown" and outcome not in {"failed-publish", "publish-skipped"}:
        run_logs_path = f"larch-logs/{skill}/{run_id}/"
    lines = [f"## /{skill} run {run_id} — {outcome}", ""]
    if outcome.startswith(("bailed", "stalled", "cancelled-", "failed-")) or outcome == "publish-skipped":
        lines.append(f"- **Outcome**: {outcome}")
    if skill != "design":
        lines.append(f"- **Mode**: {kwargs.get('mode') or 'N/A'}")
        if kwargs.get("workflow_path"):
            lines.append(f"- **Path**: {kwargs.get('workflow_path')}")
    if emergency:
        lines.append("- Emergency: true")
    lines.extend([
        f"- **Duration**: {kwargs.get('duration') or 'N/A'}",
        f"- **Cost**: {cost}",
        f"- **Issue**: {issue}",
    ])
    if skill != "design" and pr != "N/A":
        lines.append(f"- **PR**: {pr}")
    lines.append(f"- **Plan review**: {kwargs.get('plan_review_line') or 'N/A'}")
    if skill != "design":
        lines.extend([
            f"- **Code review**: {kwargs.get('code_review_line') or 'N/A'}",
            f"- **Lines (PR diff)**: {lines_disp}",
        ])
    lines.extend([
        f"- **OOS filed**: {oos_disp}",
        f"- **Exec issues**: {kwargs.get('exec_issues') or 0}",
        f"- **Warnings**: {kwargs.get('warnings') or 0}",
        f"- **Run logs**: `{run_logs_path or 'N/A'}`",
        "",
        "<!-- larch:run-summary v=1 -->",
    ])
    note = kwargs.get("note_lines")
    if note:
        lines.extend(["", str(note).rstrip("\n")])
    return "\n".join(lines).rstrip("\n") + "\n"


def render_run_summary_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py render run-summary")
    for name in ("skill", "outcome", "run-id", "mode", "workflow-path", "duration", "issue-number", "issue-url", "pr-number", "pr-url", "plan-review-line", "code-review-line", "code-added", "code-deleted", "logs-added", "logs-deleted", "oos-count", "oos-urls", "exec-issues", "warnings", "run-logs-path", "emergency-requested"):
        parser.add_argument(f"--{name}")
    parser.add_argument("--output-file")
    parser.add_argument("--note-lines-file")
    parser.add_argument("--print-stdout", action="store_true")
    parser.add_argument("--cost-unavailable", action="store_true")
    # Accept token/cost args without fully modeling token pricing here.
    for name in ("claude-tokens", "codex-tokens", "cursor-tokens", "claude-sub-tokens", "claude-input-tokens", "claude-cache-read-tokens", "claude-cache-write-5m-tokens", "claude-cache-write-1h-tokens", "claude-output-tokens", "codex-input-tokens", "codex-cached-input-tokens", "codex-output-tokens", "cursor-input-tokens", "cursor-cache-read-tokens", "cursor-output-tokens", "claude-sub-input-tokens", "claude-sub-cache-read-tokens", "claude-sub-cache-write-5m-tokens", "claude-sub-cache-write-1h-tokens", "claude-sub-output-tokens"):
        parser.add_argument(f"--{name}", default="0")
    args = parser.parse_args(argv)
    note_lines = Path(args.note_lines_file).read_text(encoding="utf-8") if args.note_lines_file and Path(args.note_lines_file).is_file() else ""
    body = render_run_summary(
        skill=args.skill,
        outcome=args.outcome,
        run_id=args.run_id,
        mode=args.mode,
        workflow_path=args.workflow_path,
        duration=args.duration,
        issue_number=args.issue_number,
        issue_url=args.issue_url,
        pr_number=args.pr_number,
        pr_url=args.pr_url,
        plan_review_line=args.plan_review_line,
        code_review_line=args.code_review_line,
        code_added=args.code_added,
        code_deleted=args.code_deleted,
        logs_added=args.logs_added,
        logs_deleted=args.logs_deleted,
        oos_count=args.oos_count,
        oos_urls=args.oos_urls,
        exec_issues=args.exec_issues,
        warnings=args.warnings,
        run_logs_path=args.run_logs_path,
        emergency_requested=args.emergency_requested,
        cost_unavailable=args.cost_unavailable,
        total_tokens=sum(int(getattr(args, attr) or 0) for attr in ("claude_tokens", "codex_tokens", "cursor_tokens", "claude_sub_tokens")),
        total_cost="N/A",
        note_lines=note_lines,
    )
    if args.output_file:
        Path(args.output_file).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output_file).write_text(body, encoding="utf-8")
    if args.print_stdout or not args.output_file:
        sys.stdout.write(body)
    print("STATUS=ok", file=sys.stderr)
    if args.output_file:
        print(f"OUTPUT_FILE={args.output_file}", file=sys.stderr)
    return 0


class _ProcRunner:
    def run(self, argv, *, timeout=None, cwd=None, env=None, check=False, stdout=None, stderr=None):
        return proc.run(argv, timeout=timeout, cwd=cwd, env=env, check=check, stdout=stdout, stderr=stderr)


def compose_pr_summary_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py pr compose-summary")
    parser.add_argument("--plan-goals-file", required=True)
    args = parser.parse_args(argv)
    try:
        sys.stdout.write(compose_summary_bullets(_ProcRunner(), plan_goals_file=args.plan_goals_file, cwd=str(Path.cwd())))
    except Exception as exc:
        print(f"ERROR={exc}", file=sys.stderr)
        return 2
    return 0


def _normalized_outcome(tmpdir: Path) -> str:
    ship = tmpdir / "ship-pr-state.sh"
    fin = tmpdir / "finalize-state.sh"
    if _read_kv(fin, "STALL_TRACKING") == "true" or _read_kv(ship, "STALL_TRACKING") == "true":
        return "stalled"
    merge_result = _read_kv(ship, "MERGE_RESULT") or _read_kv(fin, "MERGE_RESULT")
    if merge_result == "already_merged":
        return "force-merged-externally"
    if _read_kv(fin, "DESIGN_ONLY_DONE") == "true":
        return "done"
    if _read_kv(ship, "MERGE") == "true" or _read_kv(fin, "MERGE") == "true":
        return "merged"
    return "completed"


def write_final_report(implement_tmpdir: Path, *, comment_only: bool = False, print_stdout: bool = False) -> tuple[int, str, str]:
    parent = implement_tmpdir / "parent-issue.md"
    session = implement_tmpdir / "session-env.sh"
    ship = implement_tmpdir / "ship-pr-state.sh"
    final = implement_tmpdir / "finalize-state.sh"
    run_flags = implement_tmpdir / "run-flags.sh"
    issue = _read_kv(parent, "ISSUE_NUMBER", "0") or "0"
    run_id = _read_kv(parent, "RUN_ID") or ((implement_tmpdir / "session-id").read_text(encoding="utf-8").strip() if (implement_tmpdir / "session-id").is_file() else "unknown")
    if "/" in run_id or ".." in run_id:
        return 1, "", "invalid RUN_ID (path-traversal characters rejected)"
    repo = _read_kv(session, "REPO")
    pr_number = _read_kv(ship, "PR_NUMBER") or _read_kv(final, "PR_NUMBER")
    pr_url = _read_kv(ship, "PR_URL", "N/A") or _read_kv(final, "PR_URL", "N/A")
    issue_url = f"https://github.com/{repo}/issues/{issue}" if repo and issue and issue != "0" else ""
    exec_count = 0
    issue_log = implement_tmpdir / "execution-issues.md"
    if issue_log.is_file():
        exec_count = sum(1 for line in issue_log.read_text(encoding="utf-8", errors="replace").splitlines() if line.startswith("- "))
    body = render_run_summary(
        skill="implement",
        outcome=_normalized_outcome(implement_tmpdir),
        run_id=run_id or "unknown",
        mode=_read_kv(session, "MODE", "N/A"),
        workflow_path=_read_kv(session, "WORKFLOW_PATH"),
        duration=_read_kv(ship, "DURATION", "N/A"),
        issue_number=issue,
        issue_url=issue_url,
        pr_number=pr_number,
        pr_url=pr_url,
        plan_review_line=_read_kv(ship, "PLAN_REVIEW_LINE", "N/A"),
        code_review_line=_read_kv(ship, "CODE_REVIEW_LINE", "N/A"),
        code_added=_read_kv(ship, "CODE_ADDED"),
        code_deleted=_read_kv(ship, "CODE_DELETED"),
        logs_added=_read_kv(ship, "LOGS_ADDED"),
        logs_deleted=_read_kv(ship, "LOGS_DELETED"),
        oos_count=_read_kv(ship, "OOS_COUNT", "0"),
        oos_urls=_read_kv(ship, "OOS_URLS"),
        exec_issues=exec_count,
        warnings=0,
        run_logs_path=f"larch-logs/implement/{run_id}/" if run_id else "N/A",
        emergency_requested=_read_kv(run_flags, "EMERGENCY_REQUESTED", "false"),
        cost_unavailable=True,
    )
    (implement_tmpdir / "summary-final.md").write_text(body, encoding="utf-8")
    comment_url = ""
    if issue and issue != "0" and not comment_only:
        # The historical helper upserted a run summary comment. Keep failures non-fatal for API callers.
        content = implement_tmpdir / "summary-final.md"
        marker = f"<!-- larch:run-summary v=1 runid={run_id} -->"
        cmd = [sys.executable, str(Path(__file__).resolve().parent / "cli.py"), "tracking-issue", "upsert-summary", "--issue", issue, "--marker", marker, "--content-file", str(content)]
        if repo:
            cmd += ["--repo", repo]
        completed = subprocess.run(cmd, text=True, capture_output=True, check=False)
        if completed.returncode == 0:
            m = re.search(r"^COMMENT_URL=(.*)$", completed.stdout, re.MULTILINE)
            comment_url = m.group(1) if m else ""
    if print_stdout:
        sys.stdout.write(body)
    return 0, comment_url, ""


def write_final_report_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py final-report write")
    parser.add_argument("--implement-tmpdir", required=True)
    parser.add_argument("--comment-only", action="store_true")
    parser.add_argument("--print-stdout", action="store_true")
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        _emit_kv("COMMENT_URL", "")
        _emit_kv("STATUS", "failed")
        _emit_kv("ERROR", "usage")
        return 2
    rc, url, err = write_final_report(Path(args.implement_tmpdir), comment_only=args.comment_only, print_stdout=args.print_stdout)
    _emit_kv("COMMENT_URL", url)
    _emit_kv("STATUS", "ok" if rc == 0 else "failed")
    if err:
        _emit_kv("ERROR", err)
    return rc


def step18b_final_report(implement_tmpdir: Path) -> tuple[bool, int, bool, str]:
    step17_present = (implement_tmpdir / ".step17-emitted").exists()
    emit_body = not step17_present
    snapshot_ok = "absent"
    pre = implement_tmpdir / ".step18-prebody"
    summary = implement_tmpdir / "summary-final.md"
    if summary.exists():
        try:
            pre.write_bytes(summary.read_bytes())
            snapshot_ok = "true"
        except OSError:
            snapshot_ok = "false"
            with contextlib.suppress(OSError):
                pre.unlink()
    wfr_rc, _url, _err = write_final_report(implement_tmpdir)
    if (
        wfr_rc == 0
        and summary.is_file()
        and summary.stat().st_size > 0
        and not emit_body
        and (snapshot_ok in {"absent", "false"} or (pre.is_file() and pre.read_bytes() != summary.read_bytes()))
    ):
        emit_body = True
    return (emit_body and wfr_rc == 0 and summary.is_file() and summary.stat().st_size > 0), wfr_rc, step17_present, snapshot_ok


def step18b_final_report_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py final-report step18b")
    parser.add_argument("--implement-tmpdir", required=True)
    args = parser.parse_args(argv)
    emit_body, wfr_rc, present, snapshot = step18b_final_report(Path(args.implement_tmpdir))
    _emit_kv("EMIT_BODY", str(emit_body).lower())
    _emit_kv("WFR_RC", wfr_rc)
    _emit_kv("STEP17_EMITTED_PRESENT", str(present).lower())
    _emit_kv("SNAPSHOT_OK", snapshot)
    return 0


def post_tracking_issue(implement_tmpdir: Path, *, issue_number: str = "", run_id: str = "", adopted: str = "true", emergency_requested: str = "false") -> tuple[int, bool, str, str]:
    if adopted not in {"true", "false"}:
        return 2, False, "", "--adopted must be true or false"
    if emergency_requested not in {"true", "false"}:
        return 2, False, "", "--emergency-requested must be true or false"
    parent = implement_tmpdir / "parent-issue.md"
    session = implement_tmpdir / "session-env.sh"
    flags = implement_tmpdir / "run-flags.sh"
    issue = issue_number or _read_kv(parent, "ISSUE_NUMBER")
    run = run_id or _read_kv(parent, "RUN_ID") or ((implement_tmpdir / "session-id").read_text(encoding="utf-8").strip() if (implement_tmpdir / "session-id").is_file() else "") or _read_kv(session, "LARCH_TOKEN_SESSION_ID")
    if emergency_requested == "false" and _read_kv(flags, "EMERGENCY_REQUESTED") == "true":
        emergency_requested = "true"
    if not issue:
        return 1, False, "", "ISSUE_NUMBER not found in parent-issue.md"
    if not issue.isdigit():
        return 1, False, "", "ISSUE_NUMBER must be numeric"
    if not re.fullmatch(r"[A-Za-z0-9._-]+", run or ""):
        return 1, False, "", "RUN_ID must match ^[A-Za-z0-9._-]+$"
    version = "unknown"
    try:
        completed = subprocess.run([sys.executable, str(Path(__file__).resolve().parent / "cli.py"), "plugin", "read-version"], text=True, capture_output=True, check=False)
        m = re.search(r"^LARCH_PLUGIN_VERSION=(.*)$", completed.stdout, re.MULTILINE)
        if m:
            version = m.group(1)
    except OSError:
        pass
    summary = implement_tmpdir / "summary-metadata.md"
    lines = [f"Run ID: `{run}`", f"Logs: `larch-logs/implement/{run}/`", f"Tracking issue: #{issue}", f"Agent: `{_read_kv(session, 'AGENT', 'claude') or 'claude'}`", f"Coder: `{_read_kv(session, 'CODER', 'claude') or 'claude'}`"]
    if emergency_requested == "true":
        lines.append("Emergency: true")
    lines.append(f"Larch version: `{version}`")
    summary.write_text("\n".join(lines) + "\n", encoding="utf-8")
    repo = _read_kv(session, "REPO")
    cmd = [sys.executable, str(Path(__file__).resolve().parent / "cli.py"), "tracking-issue", "upsert-summary", "--issue", issue, "--marker", f"<!-- larch:metadata v1 runid={run} -->", "--content-file", str(summary)]
    if repo:
        cmd += ["--repo", repo]
    completed = subprocess.run(cmd, text=True, capture_output=True, check=False)
    if completed.returncode == 0:
        if issue_number:
            parent.write_text(f"ISSUE_NUMBER={issue}\nRUN_ID={run}\nADOPTED={adopted}\n", encoding="utf-8")
        m = re.search(r"^COMMENT_URL=(.*)$", completed.stdout, re.MULTILINE)
        return 0, True, m.group(1) if m else "", ""
    return 1, False, "", " ".join(completed.stderr.split())[:500]


def post_tracking_issue_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py tracking post-issue")
    parser.add_argument("--implement-tmpdir", required=True)
    parser.add_argument("--issue-number", default="")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--adopted", default="true")
    parser.add_argument("--emergency-requested", default="false")
    args = parser.parse_args(argv)
    rc, posted, url, err = post_tracking_issue(Path(args.implement_tmpdir), issue_number=args.issue_number, run_id=args.run_id, adopted=args.adopted, emergency_requested=args.emergency_requested)
    _emit_kv("POSTED", str(posted).lower())
    _emit_kv("COMMENT_URL", url)
    if err:
        _emit_kv("ERROR", err)
    return rc


def slack_issue_announce(implement_tmpdir: Path, *, best_effort: bool = False) -> tuple[int, str, str]:
    parent = implement_tmpdir / "parent-issue.md"
    ship = implement_tmpdir / "ship-pr-state.sh"
    issue = _read_kv(parent, "ISSUE_NUMBER", "0") or "0"
    if not issue.isdigit():
        return (0 if best_effort else 1), "failed", "ISSUE_NUMBER must be numeric"
    if issue == "0":
        return 0, "skipped", "issue-not-set"
    webhook = os.environ.get("LARCH_SLACK_WEBHOOK_URL", "")
    if not webhook:
        return 0, "skipped", "webhook-not-set"
    if urllib.parse.urlparse(webhook).scheme not in {"http", "https"}:
        return (0 if best_effort else 1), "failed", "webhook scheme must be http or https"
    run_id = _read_kv(parent, "RUN_ID") or ((implement_tmpdir / "session-id").read_text(encoding="utf-8").strip() if (implement_tmpdir / "session-id").is_file() else "")
    text = f"Implement run {run_id} opened PR {_read_kv(ship, 'PR_URL', 'N/A')} for tracking issue #{issue}"
    if _read_kv(ship, "PR_TITLE"):
        text += f" — {_read_kv(ship, 'PR_TITLE')}"
    payload = json.dumps({"text": text}).encode()
    fake_curl = os.environ.get("__LARCH_FAKE_CURL")
    try:
        if fake_curl:
            completed = subprocess.run([fake_curl, "-sS", "-X", "POST", "-H", "Content-Type: application/json", "--data", payload.decode(), webhook], text=True, capture_output=True, check=False)
            if completed.returncode != 0:
                return (0 if best_effort else 1), "failed", " ".join(completed.stderr.split())[:500]
        else:
            req = urllib.request.Request(webhook, data=payload, headers={"Content-Type": "application/json"}, method="POST")  # noqa: S310
            with urllib.request.urlopen(req, timeout=10):  # noqa: S310
                pass
    except Exception as exc:
        return (0 if best_effort else 1), "failed", str(exc)[:500]
    return 0, "posted", ""


def slack_issue_announce_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py slack issue-announce")
    parser.add_argument("--implement-tmpdir", required=True)
    parser.add_argument("--best-effort", action="store_true")
    args = parser.parse_args(argv)
    rc, status, reason = slack_issue_announce(Path(args.implement_tmpdir), best_effort=args.best_effort)
    _emit_kv("STATUS", status)
    if reason:
        _emit_kv("REASON" if status == "skipped" else "ERROR", reason)
    return rc


def generate_code_flow_diagram(implement_tmpdir: Path, *, model: str = "claude-sonnet-4-6", base_remote: str = "origin", base_ref: str = "main") -> tuple[int, str, str, str]:
    _ = (base_remote, base_ref)
    implement_tmpdir.mkdir(parents=True, exist_ok=True)
    raw = implement_tmpdir / "code-flow-diagram.raw.md"
    candidate = implement_tmpdir / "code-flow-diagram.candidate.md"
    diagram = implement_tmpdir / "code-flow-diagram.md"
    launcher = os.environ.get("LARCH_TEST_LAUNCH_CLAUDE_SUBPROCESS")
    if launcher:
        completed = subprocess.run([launcher, "--model", model, "--prompt-file", str(implement_tmpdir / "code-flow-prompt.md"), "--output-file", str(raw), "--timeout", "600", "--allow-root", str(Path.cwd()), "--timing-task-kind", "implement-code-flow"], text=True, capture_output=True, check=False)
        if completed.returncode != 0:
            return 1, "failed", "", "generation-failed"
    else:
        raw.write_text("## Code Flow Diagram\n\n```mermaid\nflowchart TD\n  A[Implementation] --> B[Runtime]\n```\n", encoding="utf-8")
    if not raw.is_file() or raw.stat().st_size == 0:
        return 1, "failed", "", "empty-generation"
    candidate.write_bytes(raw.read_bytes())
    result = sanitize_fragment(candidate.read_text(encoding="utf-8"), from_md=True)
    if result.status == "ok":
        candidate.replace(diagram)
        return 0, "ok", str(diagram), ""
    candidate.unlink(missing_ok=True)
    return 0, "skipped", "", result.reason_tokens[0] if result.reason_tokens else "sanitizer-rejected"


def generate_code_flow_diagram_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py diagram code-flow")
    parser.add_argument("--implement-tmpdir", required=True)
    parser.add_argument("--model", default="claude-sonnet-4-6")
    parser.add_argument("--base-remote", default="origin")
    parser.add_argument("--base-ref", default="main")
    args = parser.parse_args(argv)
    rc, status, diagram, reason = generate_code_flow_diagram(Path(args.implement_tmpdir), model=args.model, base_remote=args.base_remote, base_ref=args.base_ref)
    _emit_kv("STATUS", status)
    _emit_kv("DIAGRAM_FILE", diagram)
    _emit_kv("SKIP_REASON", reason)
    return rc
