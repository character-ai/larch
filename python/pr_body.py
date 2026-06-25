"""PR body composition and Mermaid sanitization."""

# pyright: reportUnusedCallResult=false, reportUnusedFunction=false

from __future__ import annotations

import argparse
import contextlib
import importlib
import json
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import larch_io
import config
import design_diagram_log
import gh
import git
import proc
import redact
import report_tokens_cost
import tokens
import tracking_issue
from errors import ShipError
from proc import CommandResult, Runner


@dataclass(frozen=True)
class MermaidResult:
    status: str
    reason_tokens: tuple[str, ...]
    fence_count: int


_FENCE_RE = re.compile(r"^(\s{0,3})(`{3,})([^`]*)$")
_FLOWCHART_START = re.compile(r"^(flowchart|graph)(\s|$)")
_OPEN_BRACKET = frozenset("[{(")
_CLOSE_BRACKET = frozenset("]})")
_ISSUE_SECTION_NONE = 0
_ISSUE_SECTION_EXEC = 1
_ISSUE_SECTION_WARN = 2
_EXEC_ISSUE_HEADINGS = frozenset({"### Tool Failures", "### External Reviewer Issues"})
_OOS_FILED_URL_LINE_RE = re.compile(r"^[ \t]*-[ \t]+\*\*Filed[ \t]URL\*\*[ \t]*:[ \t]+(https://[^\s]+/issues/\d+)", re.MULTILINE)
_DIAGRAM_FAILURE_TAIL_LIMIT = 200


def _path_under_repo(*, repo_root: Path, rel_path: str) -> bool:
    if "\x00" in rel_path or rel_path.startswith("/") or ".." in rel_path.split("/"):
        return False
    try:
        resolved = (repo_root / rel_path).resolve()
        _ = resolved.relative_to(repo_root.resolve())
    except ValueError:
        return False
    return True


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
    """Render PR summary goal + test/cross-dir bullets."""
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
    if not _path_under_repo(repo_root=repo_root, rel_path=str(rel)):
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


def _validate_fence_body(*, body: str, _fence_num: int) -> list[str]:
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
        all_reasons.extend(_validate_fence_body(body=fence, _fence_num=index))
    unique: tuple[str, ...] = tuple(dict.fromkeys(all_reasons))
    if unique:
        return MermaidResult(status="rejected", reason_tokens=unique, fence_count=len(fences))
    return MermaidResult(status="ok", reason_tokens=(), fence_count=len(fences))


def _fail_closed_body(redacted: str) -> str:
    if "[content truncated" in redacted:
        msg = "redaction failed for PR body"
        raise ShipError(msg)
    return redacted


def redact_pr_body(body: str) -> str:
    """Redact a PR body fail-closed: tmpdir paths then secrets.

    Single source of truth for outbound PR-body redaction, shared by
    ``compose_pr_body`` (the live ship path) and ``pr.create_pr_parity``
    (``cli.py pr create``). It pipes the body through ``redact tmpdir-paths``
    then ``redact secrets`` and fails closed. Raises :class:`ShipError` when
    redaction truncates the body.
    """
    return _fail_closed_body(redact.redact(body))


def architectural_guidelines_section(body: str) -> str:
    """Return normalized architectural-guidelines section body, or empty when absent."""
    heading = "## Architectural guidelines"
    idx = body.find(heading)
    if idx < 0:
        return ""
    rest = body[idx + len(heading) :].lstrip("\n")
    next_heading = rest.find("\n## ")
    section = rest[:next_heading] if next_heading >= 0 else rest
    return section.strip()


def compose_pr_body(
    *,
    summary: str,
    mermaid: str = "",
    test_plan: str = "- [ ] `make py-lint`\n- [ ] `make py-test`\n",
    issue_number: int | None = None,
    architectural_guidelines_note: str = "",
) -> str:
    if mermaid.strip():
        mermaid_result = sanitize_fragment(mermaid)
        if mermaid_result.status != "ok":
            msg = f"mermaid fragment rejected: {','.join(mermaid_result.reason_tokens)}"
            raise ShipError(msg)
    parts = [summary.rstrip(), ""]
    if architectural_guidelines_note.strip():
        parts.extend(["## Architectural guidelines", "", architectural_guidelines_note.strip(), ""])
    if mermaid.strip():
        parts.extend(["## Code Flow Diagram", "", "```mermaid", mermaid.strip(), "```", ""])
    parts.extend(["## Test plan", "", test_plan.rstrip(), ""])
    body = "\n".join(parts) + "\n"
    if issue_number is not None:
        body = tracking_issue.link_pr_closes(body=body, issue_number=issue_number)
    mermaid_body = sanitize_fragment(body, from_md=True)
    if mermaid_body.status != "ok":
        msg = f"mermaid in PR body rejected: {','.join(mermaid_body.reason_tokens)}"
        raise ShipError(msg)
    redacted = redact_pr_body(body)
    return redacted.rstrip("\n") + "\n"


def update_pr_body(
    *,
    runner: Runner,
    number: int,
    body: str,
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


def _emit_kv(*, key: str, value: object) -> None:
    print(f"{key}={value}")


def _read_kv(*, path: Path, key: str, default: str = "") -> str:
    return larch_io.read_kv(path, key, default=default, first_match=True, cr_strip="strip", on_error_default=False)


def _fmt_money(value: float | str) -> str:
    try:
        return f"${float(value):.2f}"
    except (TypeError, ValueError):
        return "N/A"


def _money_value(value: object) -> float | str:
    return value if isinstance(value, (float, int, str)) else "N/A"


def _identity_from_manifest(manifest_path: str) -> dict[str, str]:
    try:
        parsed: Any = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return {}
    if not isinstance(parsed, dict):
        return {}
    data = cast("Mapping[str, object]", parsed)
    roster = data.get("model_roster")
    model = cast("Mapping[str, object]", roster).get("main", "") if isinstance(roster, dict) else ""
    return {
        "larch_version": str(data.get("larch_version") or ""),
        "main_model": str(model or ""),
        "effort": str(data.get("effort") or ""),
    }


def _plugin_version_local() -> str:
    try:
        parsed: Any = json.loads((Path(__file__).resolve().parents[1] / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return ""
    if not isinstance(parsed, dict):
        return ""
    return str(cast("Mapping[str, object]", parsed).get("version") or "")


def _resolve_run_identity(kwargs: Mapping[str, object]) -> tuple[str, str, str]:
    """Resolve (larch_version, main_agent_model, effort) for the run summary.

    The committed run manifest (captured at run-log init) is the single source.
    Explicit kwargs win for tests; live fallbacks keep the summary populated when
    a manifest field is missing.
    """
    def clean(value: object) -> str:
        text = str(value or "").strip()
        return "" if text in ("", "unknown", "None") else text

    ident: dict[str, str] = {}
    manifest_path = kwargs.get("manifest_path")
    if manifest_path:
        ident = _identity_from_manifest(str(manifest_path))
    version = clean(kwargs.get("larch_version")) or clean(ident.get("larch_version")) or _plugin_version_local() or "unknown"
    model = clean(kwargs.get("main_model")) or clean(ident.get("main_model"))
    if not model:
        try:
            model = tokens.read_main_model()
        except Exception:
            model = ""
        model = model or "unknown"
    effort = (
        clean(kwargs.get("effort"))
        or clean(ident.get("effort"))
        or clean(os.environ.get("CLAUDE_CODE_EFFORT_LEVEL"))
        or clean(os.environ.get("CLAUDE_EFFORT"))
        or "unknown"
    )
    return version, model, effort


def _identity_lines(kwargs: Mapping[str, object]) -> list[str]:
    version, model, effort = _resolve_run_identity(kwargs)
    return [
        f"- **Main agent model**: {model}",
        f"- **Effort**: {effort}",
        f"- **Larch version**: {version}",
    ]


def render_run_summary(**kwargs: object) -> str:
    skill = str(kwargs.get("skill") or "implement")
    outcome = str(kwargs.get("outcome") or "unknown")
    run_id = str(kwargs.get("run_id") or "unknown")
    force = str(kwargs.get("force_requested") or "false") == "true"
    total_tokens = int(str(kwargs.get("total_tokens") or kwargs.get("claude_tokens") or 0) or 0)
    total_cost = kwargs.get("total_cost", "N/A")
    if kwargs.get("cost_unavailable") or total_cost == "N/A":
        cost = "N/A"
    else:
        cost = f"💰 TOTAL ~{_fmt_money(_money_value(total_cost))} — Claude {_fmt_money(_money_value(kwargs.get('claude_cost', 0)))}, Codex {_fmt_money(_money_value(kwargs.get('codex_cost', 0)))}, Cursor {_fmt_money(_money_value(kwargs.get('cursor_cost', 0)))}, Claude (subprocess) {_fmt_money(_money_value(kwargs.get('claude_sub_cost', 0)))}  |  Tokens: {int((total_tokens + 500) / 1000)}k"
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
    if force:
        lines.append("- Force: true")
    lines.extend([
        f"- **Duration**: {kwargs.get('duration') or 'N/A'}",
        f"- **Cost**: {cost}",
        f"- **Issue**: {issue}",
    ])
    if skill != "design" and pr != "N/A":
        lines.append(f"- **PR**: {pr}")
    if skill != "design" and str(kwargs.get("merge_downgraded") or "false") == "true":
        lines.append(
            "- **⚠ Merge downgraded**: requested `--merge`, but panel-failed "
            "recovery shipped a PR without merging. Manual review and merge required."
        )
    lines.append(f"- **Plan review**: {kwargs.get('plan_review_line') or 'N/A'}")
    dynamic_line = str(kwargs.get("dynamic_archetypes_line") or "")
    if dynamic_line:
        lines.append(f"- **Dynamic archetypes**: {dynamic_line}")
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
        *_identity_lines(kwargs),
        "",
        "<!-- larch:run-summary v=1 -->",
    ])
    note = kwargs.get("note_lines")
    if note:
        lines.extend(["", str(note).rstrip("\n")])
    return "\n".join(lines).rstrip("\n") + "\n"


def render_run_summary_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py render run-summary")
    parser.add_argument("--skill", required=True, choices=("implement", "design"))
    parser.add_argument("--outcome", required=True)
    parser.add_argument("--run-id", required=True)
    for name in ("mode", "workflow-path", "duration", "issue-number", "issue-url", "pr-number", "pr-url", "plan-review-line", "dynamic-archetypes-line", "code-review-line", "code-added", "code-deleted", "logs-added", "logs-deleted", "oos-count", "oos-urls", "exec-issues", "warnings", "run-logs-path", "merge-downgraded", "manifest-path", "larch-version", "main-model", "effort"):
        parser.add_argument(f"--{name}")
    parser.add_argument("--force-requested", choices=("true", "false"))
    parser.add_argument("--output-file")
    parser.add_argument("--note-lines-file")
    parser.add_argument("--print-stdout", action="store_true")
    parser.add_argument("--cost-unavailable", action="store_true")
    _TOKEN_COST_ARGS = ("claude-tokens", "codex-tokens", "cursor-tokens", "claude-sub-tokens", "claude-input-tokens", "claude-cache-read-tokens", "claude-cache-write-5m-tokens", "claude-cache-write-1h-tokens", "claude-output-tokens", "codex-input-tokens", "codex-cached-input-tokens", "codex-output-tokens", "cursor-input-tokens", "cursor-cache-read-tokens", "cursor-output-tokens", "claude-sub-input-tokens", "claude-sub-cache-read-tokens", "claude-sub-cache-write-5m-tokens", "claude-sub-cache-write-1h-tokens", "claude-sub-output-tokens")
    for name in _TOKEN_COST_ARGS:
        parser.add_argument(f"--{name}", default="0")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 2

    cost_unavailable = args.cost_unavailable
    total_cost = "N/A"
    claude_cost: object = "N/A"
    codex_cost: object = "N/A"
    cursor_cost: object = "N/A"
    claude_sub_cost: object = "N/A"
    total_tokens = sum(int(getattr(args, a.replace("-", "_")) or 0) for a in ("claude-tokens", "codex-tokens", "cursor-tokens", "claude-sub-tokens"))
    if not cost_unavailable:
        try:
            token_argv: list[str] = []
            for name in _TOKEN_COST_ARGS:
                val = getattr(args, name.replace("-", "_"), "0") or "0"
                if val != "0":
                    token_argv += [f"--{name}", val]
            cost_kv = report_tokens_cost.token_cost_from_args(token_argv)
            total_cost = larch_io.kv_value(cost_kv, "TOTAL_COST", default="N/A")
            claude_cost = larch_io.kv_value(cost_kv, "CLAUDE_COST", default="N/A")
            codex_cost = larch_io.kv_value(cost_kv, "CODEX_COST", default="N/A")
            cursor_cost = larch_io.kv_value(cost_kv, "CURSOR_COST", default="N/A")
            claude_sub_cost = larch_io.kv_value(cost_kv, "CLAUDE_SUB_COST", default="N/A")
            total_tokens = int(larch_io.kv_value(cost_kv, "TOTAL_TOKENS", default="N/A") or total_tokens)
        except Exception:
            cost_unavailable = True

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
        dynamic_archetypes_line=args.dynamic_archetypes_line,
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
        force_requested=args.force_requested,
        merge_downgraded=args.merge_downgraded,
        cost_unavailable=cost_unavailable,
        total_tokens=total_tokens,
        total_cost=total_cost,
        claude_cost=claude_cost,
        codex_cost=codex_cost,
        cursor_cost=cursor_cost,
        claude_sub_cost=claude_sub_cost,
        note_lines=note_lines,
        manifest_path=args.manifest_path,
        larch_version=args.larch_version,
        main_model=args.main_model,
        effort=args.effort,
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
    def run(
        self,
        argv: Sequence[str],
        *,
        timeout: float | None = None,
        cwd: str | None = None,
        env: Mapping[str, str] | None = None,
        check: bool = False,
        stdout: int | None = None,
        stderr: int | None = None,
    ) -> CommandResult:
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


# ---------------------------------------------------------------------------
# Final report compatibility wrappers
# ---------------------------------------------------------------------------


def _final_report_module() -> object:
    return importlib.import_module("final_report")


def _final_report_token_fields(*, implement_tmpdir: Path, run_id: str) -> dict[str, object]:
    name = "_final_report_token_fields"
    return getattr(_final_report_module(), name)(implement_tmpdir, run_id)


def _refresh_issue_counts(*, implement_tmpdir: Path, run_id: str) -> tuple[int, int]:
    name = "_refresh_issue_counts"
    return getattr(_final_report_module(), name)(implement_tmpdir, run_id)


def write_final_report(
    implement_tmpdir: Path,
    *,
    comment_only: bool = False,
    print_stdout: bool = False,
    skip_tracking_upsert: bool = False,
) -> tuple[int, str, str]:
    return _final_report_module().write_final_report(  # type: ignore[attr-defined]
        implement_tmpdir,
        comment_only=comment_only,
        print_stdout=print_stdout,
        skip_tracking_upsert=skip_tracking_upsert,
    )


def write_final_report_main(argv: list[str] | None = None) -> int:
    return _final_report_module().write_final_report_main(argv)  # type: ignore[attr-defined]


def step18b_final_report(implement_tmpdir: Path) -> tuple[bool, int, bool, str]:
    return _final_report_module().step18b_final_report(implement_tmpdir)  # type: ignore[attr-defined]


def step18b_final_report_main(argv: list[str] | None = None) -> int:
    return _final_report_module().step18b_final_report_main(argv)  # type: ignore[attr-defined]

def post_tracking_issue(implement_tmpdir: Path, *, issue_number: str = "", run_id: str = "", adopted: str = "true", force_requested: str = "false") -> tuple[int, bool, str, str]:
    if adopted not in {"true", "false"}:
        return 2, False, "", "--adopted must be true or false"
    if force_requested not in {"true", "false"}:
        return 2, False, "", "--force-requested must be true or false"
    parent = implement_tmpdir / "parent-issue.md"
    session = implement_tmpdir / "session-env.sh"
    flags = implement_tmpdir / "run-flags.sh"
    issue = issue_number or _read_kv(path=parent, key="ISSUE_NUMBER")
    run = run_id or _read_kv(path=parent, key="RUN_ID") or ((implement_tmpdir / "session-id").read_text(encoding="utf-8").strip() if (implement_tmpdir / "session-id").is_file() else "") or _read_kv(path=session, key="LARCH_TOKEN_SESSION_ID")
    if force_requested == "false" and _read_kv(path=flags, key="FORCE_REQUESTED") == "true":
        force_requested = "true"
    if not issue:
        return 1, False, "", "ISSUE_NUMBER not found in parent-issue.md"
    if not issue.isdigit():
        return 1, False, "", "ISSUE_NUMBER must be numeric"
    if not re.fullmatch(r"[A-Za-z0-9._-]+", run or ""):
        return 1, False, "", "RUN_ID must match ^[A-Za-z0-9._-]+$"
    version = "unknown"
    try:
        completed = subprocess.run([sys.executable, str(Path(__file__).resolve().parent / "cli.py"), "plugin", "read-version"], text=True, capture_output=True, check=False)
        m: re.Match[str] | None = re.search(r"^LARCH_PLUGIN_VERSION=(.*)$", completed.stdout, re.MULTILINE)
        if m:
            version = m.group(1)
    except OSError:
        pass
    summary = implement_tmpdir / "summary-metadata.md"
    lines = [f"Run ID: `{run}`", f"Logs: `larch-logs/implement/{run}/`", f"Tracking issue: #{issue}", f"Agent: `{_read_kv(path=session, key='AGENT', default='claude') or 'claude'}`", f"Coder: `{_read_kv(path=session, key='CODER', default='claude') or 'claude'}`"]
    if force_requested == "true":
        lines.append("Force: true")
    lines.append(f"Larch version: `{version}`")
    summary.write_text("\n".join(lines) + "\n", encoding="utf-8")
    repo = _read_kv(path=session, key="REPO")
    cmd = [sys.executable, str(Path(__file__).resolve().parent / "cli.py"), "tracking-issue", "upsert-summary", "--issue", issue, "--marker", f"<!-- larch:metadata v1 runid={run} -->", "--content-file", str(summary)]
    if repo:
        cmd += ["--repo", repo]
    completed = subprocess.run(cmd, text=True, capture_output=True, check=False)
    if completed.returncode == 0:
        if issue_number:
            parent.write_text(f"ISSUE_NUMBER={issue}\nRUN_ID={run}\nADOPTED={adopted}\n", encoding="utf-8")
        m: re.Match[str] | None = re.search(r"^COMMENT_URL=(.*)$", completed.stdout, re.MULTILINE)
        return 0, True, m.group(1) if m else "", ""
    return 1, False, "", " ".join(completed.stderr.split())[:500]


def post_tracking_issue_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py tracking post-issue")
    parser.add_argument("--implement-tmpdir", required=True)
    parser.add_argument("--issue-number", default="")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--adopted", default="true")
    parser.add_argument("--force-requested", default="false")
    args = parser.parse_args(argv)
    rc, posted, url, err = post_tracking_issue(Path(args.implement_tmpdir), issue_number=args.issue_number, run_id=args.run_id, adopted=args.adopted, force_requested=args.force_requested)
    _emit_kv(key="POSTED", value=str(posted).lower())
    _emit_kv(key="COMMENT_URL", value=url)
    if err:
        _emit_kv(key="ERROR", value=err)
    return rc


def slack_issue_announce(implement_tmpdir: Path, *, best_effort: bool = False) -> tuple[int, str, str]:
    parent = implement_tmpdir / "parent-issue.md"
    ship = implement_tmpdir / "ship-pr-state.sh"
    issue = _read_kv(path=parent, key="ISSUE_NUMBER", default="0") or "0"
    if not issue.isdigit():
        return (0 if best_effort else 1), "failed", "ISSUE_NUMBER must be numeric"
    if issue == "0":
        return 0, "skipped", "issue-not-set"
    webhook = os.environ.get("LARCH_SLACK_WEBHOOK_URL", "")
    if not webhook:
        return 0, "skipped", "webhook-not-set"
    if urllib.parse.urlparse(webhook).scheme not in {"http", "https"}:
        return (0 if best_effort else 1), "failed", "webhook scheme must be http or https"
    run_id = _read_kv(path=parent, key="RUN_ID") or ((implement_tmpdir / "session-id").read_text(encoding="utf-8").strip() if (implement_tmpdir / "session-id").is_file() else "")
    text = f"Implement run {run_id} opened PR {_read_kv(path=ship, key='PR_URL', default='N/A')} for tracking issue #{issue}"
    if _read_kv(path=ship, key="PR_TITLE"):
        text += f" — {_read_kv(path=ship, key='PR_TITLE')}"
    payload = json.dumps({"text": text}).encode()
    try:
        req = urllib.request.Request(webhook, data=payload, headers={"Content-Type": "application/json"}, method="POST")  # noqa: S310
        with urllib.request.urlopen(req, timeout=10):  # noqa: S310
            pass
    except Exception as exc:
        return (0 if best_effort else 1), "failed", " ".join(str(exc).split())[:500]
    return 0, "posted", ""


def slack_issue_announce_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py slack issue-announce")
    parser.add_argument("--implement-tmpdir", default=None)
    parser.add_argument("--best-effort", action="store_true")
    args = parser.parse_args(argv)
    if not args.implement_tmpdir:
        _emit_kv(key="STATUS", value="failed")
        _emit_kv(key="ERROR", value="--implement-tmpdir is required")
        return 2
    if not Path(args.implement_tmpdir).is_dir():
        _emit_kv(key="STATUS", value="failed")
        _emit_kv(key="ERROR", value="--implement-tmpdir not found")
        return 2
    rc, status, reason = slack_issue_announce(Path(args.implement_tmpdir), best_effort=args.best_effort)
    _emit_kv(key="STATUS", value=status)
    if reason:
        _emit_kv(key="REASON" if status == "skipped" else "ERROR", value=reason)
    return rc


def _diagram_failure_capture(*, returncode: int, stderr: str) -> tuple[str, str]:
    tail_source = f"stderr:\n{stderr or ''}\n"
    try:
        capture = redact.redact(design_diagram_log.strip_diagram_sections(tail_source))
    except Exception:
        return f"returncode: {returncode}\nredaction-failed\n", "redaction-failed"
    sanitized = design_diagram_log.sanitize_diagram_capture(capture)
    collapsed = re.sub(r"\s+", " ", sanitized).strip() or "no-output"
    if len(collapsed) > _DIAGRAM_FAILURE_TAIL_LIMIT:
        collapsed = "..." + collapsed[-(_DIAGRAM_FAILURE_TAIL_LIMIT - 3):]
    return f"returncode: {returncode}\n{sanitized}", collapsed


def generate_code_flow_diagram(implement_tmpdir: Path, *, model: str = "claude-sonnet-4-6", base_remote: str = "origin", base_ref: str = "main") -> tuple[int, str, str, str]:
    implement_tmpdir.mkdir(parents=True, exist_ok=True)
    raw = implement_tmpdir / "code-flow-diagram.raw.md"
    candidate = implement_tmpdir / "code-flow-diagram.candidate.md"
    diagram = implement_tmpdir / "code-flow-diagram.md"
    prompt_path = implement_tmpdir / "code-flow-prompt.md"
    failure_log = implement_tmpdir / "code-flow-diagram.failure.log"
    base_target = f"{base_remote}/{base_ref}"
    merge_base = subprocess.run(["git", "merge-base", "HEAD", base_target], text=True, capture_output=True, check=False)  # noqa: S607
    if merge_base.returncode != 0 or not merge_base.stdout.strip():
        fallback = subprocess.run(["git", "rev-parse", "HEAD~1"], text=True, capture_output=True, check=False)  # noqa: S607
        merge_ref = fallback.stdout.strip() if fallback.returncode == 0 and fallback.stdout.strip() else "HEAD"
    else:
        merge_ref = merge_base.stdout.strip()
    changed = subprocess.run(["git", "diff", "--name-only", f"{merge_ref}..HEAD"], text=True, capture_output=True, check=False)  # noqa: S607
    changed_lines: list[str] = changed.stdout.strip().splitlines() if changed.returncode == 0 else []
    prompt_lines = [
        "Generate a concise Mermaid code-flow diagram for the committed implementation diff.",
        "Return markdown containing exactly one `## Code Flow Diagram` heading and one mermaid fence.",
        "Focus on runtime calls, data flow, and control flow. Avoid structural architecture duplication.",
        "",
        "Changed files:",
        *changed_lines,
        "",
    ]
    prompt_path.write_text("\n".join(prompt_lines), encoding="utf-8")
    plugin_root = Path(__file__).resolve().parent
    launcher = os.environ.get("LARCH_TEST_LAUNCH_CLAUDE_SUBPROCESS")
    if launcher:
        launch_cmd = [launcher]
    else:
        launch_cmd = [sys.executable, str(plugin_root / "cli.py"), "agent", "launch-claude-subprocess"]
    with contextlib.suppress(OSError):
        failure_log.unlink()
    completed = subprocess.run(
        [
            *launch_cmd,
            "--model", model,
            "--prompt-file", str(prompt_path),
            "--output-file", str(raw),
            "--timeout", "600",
            "--allow-root", str(Path.cwd()),
            "--timing-task-kind", "implement-code-flow",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raw_capture: Path | None = implement_tmpdir / "code-flow-diagram.raw-failure.log"
        try:
            raw_capture.write_text(
                f"stderr:\n{completed.stderr or ''}\nstdout:\n{completed.stdout or ''}\n",
                encoding="utf-8",
            )
        except OSError:
            raw_capture = None
        diagnostic, tail = _diagram_failure_capture(returncode=completed.returncode, stderr=completed.stderr)
        reason = f"generation-failed rc={completed.returncode} tail={tail}"
        try:
            if raw_capture is not None:
                bounded = design_diagram_log.write_bounded_diagram_failure_log(
                    implement_tmpdir,
                    site="implement Step 7a",
                    reason=reason,
                    exit_code=completed.returncode,
                    raw_capture_path=raw_capture,
                )
                if bounded != failure_log:
                    failure_log.write_text(bounded.read_text(encoding="utf-8"), encoding="utf-8")
                with contextlib.suppress(OSError):
                    raw_capture.unlink()
            else:
                failure_log.write_text(diagnostic, encoding="utf-8")
        except OSError:
            reason = f"{reason} log-write-failed"
        return 1, "failed", "", reason
    if not raw.is_file() or raw.stat().st_size == 0:
        return 1, "failed", "", "empty-generation"
    candidate.write_bytes(raw.read_bytes())
    result = sanitize_fragment(candidate.read_text(encoding="utf-8"), from_md=True)
    if result.status == "ok":
        candidate.replace(diagram)
        with contextlib.suppress(OSError):
            failure_log.unlink()
            _ = (implement_tmpdir / "code-flow-diagram.raw-failure.log").unlink(missing_ok=True)
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
    _emit_kv(key="STATUS", value=status)
    _emit_kv(key="DIAGRAM_FILE", value=diagram)
    _emit_kv(key="SKIP_REASON", value=reason)
    return rc
