"""PR body composition and Mermaid sanitization."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import config
import gh
import git
import redact
from errors import ShipError
from proc import Runner


@dataclass(frozen=True)
class MermaidResult:
    status: str
    reason_tokens: tuple[str, ...]
    fence_count: int


@dataclass(frozen=True)
class PrBodyParts:
    summary: str
    mermaid_block: str
    test_plan: str
    closes_line: str


_FENCE_RE = re.compile(r"^(\s{0,3})(`{3,})([^`]*)$")
_FLOWCHART_START = re.compile(r"^(flowchart|graph)(\s|$)")
_PIPE_IN_BRACKETS = re.compile(r"[\[\{\(][^\]\}\)]*\|")


def compose_summary_bullets(
    runner: Runner,
    *,
    plan_goals_file: str,
    cwd: str | None = None,
) -> str:
    """Port compose-pr-summary.sh goal + test/cross-dir bullets."""
    _ = runner
    goals_path = Path(plan_goals_file)
    if not goals_path.is_file() or goals_path.stat().st_size == 0:
        msg = f"plan-goals file missing or empty: {plan_goals_file}"
        raise ShipError(msg)
    text = goals_path.read_text(encoding="utf-8")
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


def _body_start_line(lines: list[str]) -> int:
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
    start = _body_start_line(lines)
    if start == -1:
        return [config.MERMAID_REASON_UNCLOSED_FRONTMATTER]
    if start < 1 or start > len(lines):
        return []
    first = lines[start - 1].strip()
    reasons: list[str] = []
    if _FLOWCHART_START.match(first):
        for line in lines[start - 1 :]:
            if _PIPE_IN_BRACKETS.search(line):
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


def compose_pr_body(
    *,
    summary: str,
    mermaid: str = "",
    test_plan: str = "- [ ] `make py-lint`\n- [ ] `make py-test`\n",
    issue_number: int | None = None,
) -> str:
    parts = [summary.rstrip(), ""]
    if mermaid.strip():
        parts.extend(["## Code Flow Diagram", "", "```mermaid", mermaid.strip(), "```", ""])
    parts.extend(["## Test plan", "", test_plan.rstrip(), ""])
    if issue_number is not None:
        parts.extend(["", f"Closes #{issue_number}"])
    body = "\n".join(parts) + "\n"
    return redact.redact(body).rstrip("\n") + "\n"


def update_pr_body(
    runner: Runner,
    number: int,
    body: str,
    *,
    repo: str,
    cwd: str | None = None,
) -> None:
    redacted = redact.redact(body)
    if "[content truncated" in redacted:
        msg = "redaction failed for PR body"
        raise ShipError(msg)
    result = gh.pr_edit_body(runner, number, redacted, repo=repo, cwd=cwd)
    if result.returncode != 0:
        msg = f"gh pr edit failed ({result.returncode})"
        raise ShipError(msg)
