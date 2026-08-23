"""Frozen architectural-read and exception helpers for pre-cutover parity.

Production commands are Rust-owned. This fixture keeps only the retired pure
Python behavior still needed by frozen `/design` reference processes.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import partial
from pathlib import Path

from larch.core.repo_roots import consumer_repo_root
from larch.design import plan_grammar


@dataclass(frozen=True)
class ArchitecturalGuidelinesResult:
    status: str
    repo_root: Path | None
    path: Path | None
    content: str
    warning: str = ""


@dataclass(frozen=True)
class _Kind:
    filename: str
    heading_re: re.Pattern[str]
    preserve_body: bool


GUIDELINES = _Kind(
    "ARCHITECTURAL_GUIDELINES.md",
    re.compile(r"^###\s+(G-[A-Za-z0-9-]+-\d+):\s*(.+?)\s*$"),
    False,
)
INVARIANTS = _Kind(
    "ARCHITECTURAL_INVARIANTS.md",
    re.compile(r"^#{1,6}\s+(I-[A-Za-z0-9-]+-\d+):\s*(.+?)\s*$"),
    True,
)
_MARKDOWN_HEADING_RE = re.compile(r"^#{1,6}\s+\S")
_GUIDELINE_DETAIL_RE = re.compile(
    r"^\s*-\s*(Why|Deviate when|Mechanized):\s*(.+?)\s*$"
)


def _guideline_body(body: list[str]) -> list[str]:
    details: list[str] = []
    mechanized = ""
    for line in body:
        match = _GUIDELINE_DETAIL_RE.match(line)
        if match is None:
            continue
        normalized = f"- {match.group(1)}: {match.group(2).strip()}"
        if match.group(1) == "Mechanized":
            mechanized = normalized
        else:
            details.append(normalized)
    return [mechanized] if mechanized else details


def _parse_entries(raw_text: str, *, kind: _Kind) -> str:
    entries: list[list[str]] = []
    heading: str | None = None
    body: list[str] = []

    def append_entry() -> None:
        nonlocal heading, body
        if heading is None:
            return
        if kind.preserve_body:
            while body and not body[0].strip():
                body.pop(0)
            while body and not body[-1].strip():
                body.pop()
            entry_body = body
        else:
            entry_body = _guideline_body(body)
        entries.append([heading, *entry_body])
        heading = None
        body = []

    lines = raw_text.splitlines()
    fenced_lines = plan_grammar.balanced_fence_line_indices(lines)
    for index, raw_line in enumerate(lines):
        if index in fenced_lines or plan_grammar.is_fence_marker(raw_line):
            if heading is not None:
                body.append(raw_line)
            continue
        match = kind.heading_re.match(raw_line)
        if match:
            append_entry()
            heading = f"### {match.group(1)}: {match.group(2).strip()}"
        elif _MARKDOWN_HEADING_RE.match(raw_line):
            append_entry()
        elif heading is not None:
            body.append(raw_line)
    append_entry()
    return "\n\n".join("\n".join(entry) for entry in entries).strip()


def _resolve_repo_root(explicit_repo_root: str | Path | None) -> Path | None:
    if explicit_repo_root is not None:
        try:
            return Path(explicit_repo_root).resolve()
        except OSError:
            return None
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "").strip()
    if project_dir:
        root = consumer_repo_root(Path(project_dir))
        if root is not None:
            return root
    return consumer_repo_root(Path.cwd())


def _read(*, kind: _Kind, repo_root: str | Path | None = None) -> ArchitecturalGuidelinesResult:
    root = _resolve_repo_root(repo_root)
    if root is None:
        return ArchitecturalGuidelinesResult("absent", None, None, "")
    path = root / kind.filename
    if not path.exists() and not path.is_symlink():
        return ArchitecturalGuidelinesResult("absent", root, path, "")
    warning = ""
    if path.is_symlink():
        warning = f"{kind.filename} is invalid: symlinks are not read"
    else:
        try:
            path.resolve(strict=False).relative_to(root.resolve())
        except (OSError, ValueError):
            warning = f"{kind.filename} is invalid: path escapes repo root"
        if not warning and path.is_dir():
            warning = (
                f"{kind.filename} is invalid: expected a regular file, found a directory"
            )
        elif not warning and not path.is_file():
            warning = f"{kind.filename} is invalid: expected a regular file"
    if warning:
        return ArchitecturalGuidelinesResult("invalid", root, path, "", warning)
    try:
        raw_text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        return ArchitecturalGuidelinesResult(
            "invalid",
            root,
            path,
            "",
            f"{kind.filename} is invalid: unreadable file ({error})",
        )
    return ArchitecturalGuidelinesResult(
        "present",
        root,
        path.resolve(strict=False),
        _parse_entries(raw_text, kind=kind),
    )


read_guidelines = partial(_read, kind=GUIDELINES)
read_invariants = partial(_read, kind=INVARIANTS)


@dataclass(frozen=True)
class GuidelineException:
    rationale: str
    date: str
    line: str


_EXCEPTION_LEAD_RE = re.compile(r"^\s*Exception:")
_DESIGN_EXCEPTION_RE = re.compile(
    r"^\s*Exception:\s+(?P<rationale>\S[^\n]*?)\s+"
    r"\(author:\s*main-agent,\s+date:\s*"
    r"(?P<date>\d{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01]))\)\s*$"
)


def guideline_active_exception(note: str) -> GuidelineException | None:
    lines = note.splitlines()
    fenced = plan_grammar.balanced_fence_line_indices(lines)
    active = [
        line
        for index, line in enumerate(lines)
        if index not in fenced and _EXCEPTION_LEAD_RE.match(line) is not None
    ]
    if len(active) != 1 or (match := _DESIGN_EXCEPTION_RE.match(active[0])) is None:
        return None
    try:
        year, month, day = (int(value) for value in match.group("date").split("-"))
        datetime(year, month, day, tzinfo=UTC)
    except ValueError:
        return None
    rationale = match.group("rationale").strip()
    if not rationale:
        return None
    return GuidelineException(rationale, match.group("date"), active[0].strip())
