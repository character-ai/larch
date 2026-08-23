"""PR body composition and Mermaid sanitization."""

# pyright: reportUnusedCallResult=false, reportUnusedFunction=false

from __future__ import annotations

import re
from dataclasses import dataclass

from larch.core import config


@dataclass(frozen=True)
class MermaidResult:
    status: str
    reason_tokens: tuple[str, ...]
    fence_count: int


@dataclass(frozen=True)
class FinalReportResult:
    exit_code: int
    comment_url: str
    error: str

_FENCE_RE = re.compile(r"^(\s{0,3})(`{3,})([^`]*)$")
_FLOWCHART_START = re.compile(r"^(flowchart|graph)(\s|$)")
_OPEN_BRACKET = frozenset("[{(")
_CLOSE_BRACKET = frozenset("]})")
_ISSUE_SECTION_NONE = 0
_ISSUE_SECTION_EXEC = 1
_ISSUE_SECTION_WARN = 2
_EXEC_ISSUE_HEADINGS = frozenset({"### Tool Failures", "### External Reviewer Issues"})
_OOS_FILED_URL_LINE_RE = re.compile(r"^[ \t]*-[ \t]+\*\*Filed[ \t]URL\*\*[ \t]*:[ \t]+(https://[^\s]+/issues/\d+)", re.MULTILINE)


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
