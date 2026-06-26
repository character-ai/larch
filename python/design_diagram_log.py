"""Bounded diagram failure logging helpers."""

from __future__ import annotations

import re
from pathlib import Path

from larch.core import redact

_DETAIL_LIMIT = 240
_SECTION_RE = re.compile(r"^##[ \t]+(Architecture Diagram|Code Flow Diagram)[ \t]*$", re.IGNORECASE)
_HEADING_RE = re.compile(r"^#{1,2}(\s|$)")
_FENCE_OPEN_RE = re.compile(r"^ {0,3}`{3,}\s*\S*")
_FENCE_CLOSE_RE = re.compile(r"^ {0,3}`{3,}\s*$")
_MERMAID_LINE_RE = re.compile(
    r"^\s*(graph|flowchart|sequenceDiagram|classDiagram|stateDiagram|erDiagram|gantt|pie|journey)\b",
    re.IGNORECASE,
)
_MERMAID_KEYWORD_LINE_RE = re.compile(
    r"^\s*(participant|actor|subgraph|classDef|style)\b",
    re.IGNORECASE,
)
_SEQUENCE_ARROW_RE = re.compile(r"^\s*\S+\s*->>\s*\S+")
_EDGE_LINE_RE = re.compile(r"^\s*[\w\[\]()\"'-]+\s*(-->|---|\-\.-|==>|\.+)\s*[\w\[\]()\"'-]+")
_MERMAID_REMAINS_RE = re.compile(
    r"(```|"
    r"\b(?:graph|flowchart|sequenceDiagram|classDiagram|stateDiagram|erDiagram|gantt|pie|journey)\b|"
    r"\b(?:participant|actor|subgraph|classDef|style)\b|"
    r"->>|-->|\-\.-|==>)",
    re.IGNORECASE,
)
_REDACTED_TOKEN = "diagram-content-redacted"
_SAFE_TOKEN_RE = re.compile(r"[^A-Za-z0-9._-]+")


def _line_is_mermaid_syntax(line: str) -> bool:
    if _MERMAID_LINE_RE.match(line):
        return True
    if _MERMAID_KEYWORD_LINE_RE.match(line):
        return True
    if _SEQUENCE_ARROW_RE.match(line):
        return True
    return bool(_EDGE_LINE_RE.match(line))


def strip_diagram_sections(text: str) -> str:
    """Remove diagram sections, fenced blocks, and unfenced graph syntax from captured text."""
    kept: list[str] = []
    in_diagram_section = False
    in_fence = False
    fence_len = 3
    for line in text.splitlines():
        if in_fence:
            close = _FENCE_CLOSE_RE.match(line)
            if close and len(close.group(0).lstrip()) >= fence_len:
                in_fence = False
            continue
        if in_diagram_section:
            if _SECTION_RE.match(line):
                continue
            if _HEADING_RE.match(line):
                in_diagram_section = False
            else:
                continue
        if _SECTION_RE.match(line):
            in_diagram_section = True
            continue
        if _line_is_mermaid_syntax(line):
            continue
        open_match = _FENCE_OPEN_RE.match(line)
        if open_match:
            stripped_open = open_match.group(0).lstrip()
            fence_len = len(stripped_open) - len(stripped_open.lstrip("`"))
            in_fence = True
            continue
        kept.append(line)
    out = "\n".join(kept).strip()
    return out + ("\n" if out else "")


def sanitize_diagram_capture(text: str) -> str:
    """Strip diagram/Mermaid content from an untrusted capture; fail closed on remainder."""
    stripped = strip_diagram_sections(text)
    stripped = re.sub(r"```+", "", stripped)
    stripped = re.sub(r"(?i)mermaid", "", stripped).strip()
    if not stripped or _MERMAID_REMAINS_RE.search(stripped):
        return _REDACTED_TOKEN
    return stripped + ("\n" if stripped.endswith("\n") else "")


def _sanitize_bounded_text(raw: str) -> str:
    stripped = strip_diagram_sections(raw)
    stripped = re.sub(r"```+", "", stripped)
    stripped = re.sub(r"(?i)mermaid", "", stripped)
    try:
        stripped = redact.redact(stripped)
    except Exception:
        stripped = "redaction-failed"
    detail = re.sub(r"\s+", " ", stripped).strip() or "unknown"
    if _MERMAID_REMAINS_RE.search(detail):
        detail = _REDACTED_TOKEN
    if len(detail) > _DETAIL_LIMIT:
        detail = "..." + detail[-(_DETAIL_LIMIT - 3):]
    return detail


def _bounded_detail(raw_capture_path: Path | None) -> str:
    if raw_capture_path is None or not raw_capture_path.is_file() or raw_capture_path.is_symlink():
        return ""
    try:
        text = raw_capture_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    return _sanitize_bounded_text(text)


def bounded_diagram_warning_body(*, reason: str, exit_code: int | str) -> str:
    """Compose a Mermaid-free warning bullet for execution-issues.md."""
    safe_reason = re.sub(r"\s+", " ", strip_diagram_sections(str(reason))).strip() or "unknown"
    safe_reason = re.sub(r"(?i)mermaid", "", safe_reason.replace("```", ""))
    return f"- **Diagram failure**: reason={safe_reason}; exit-code={exit_code}"


def write_bounded_diagram_failure_log(
    tmpdir: str | Path,
    *,
    site: str,
    reason: str,
    exit_code: int | str,
    raw_capture_path: str | Path | None = None,
) -> Path:
    """Write a bounded sidecar with KVs only and return its path."""
    tmp = Path(tmpdir)
    tmp.mkdir(parents=True, exist_ok=True)
    raw_path: Path | None = Path(raw_capture_path) if raw_capture_path else None
    slug = _SAFE_TOKEN_RE.sub("-", site.strip().lower()).strip("-") or "diagram"
    path = tmp / f"{slug}-diagram-failure.bounded.log"
    safe_reason = _sanitize_bounded_text(str(reason))
    lines: list[str] = [
        f"site={site}",
        f"reason={safe_reason}",
        f"exit-code={exit_code}",
    ]
    detail = _bounded_detail(raw_path)
    if detail:
        lines.append(f"detail={detail}")
    text = "\n".join(lines) + "\n"
    text = re.sub(r"(?i)mermaid", "", strip_diagram_sections(text).replace("```", ""))
    _ = path.write_text(text, encoding="utf-8")
    return path
