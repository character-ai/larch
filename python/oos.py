"""Out-of-scope disposition gate (parity with oos-disposition-gate.sh)."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import config
from proc import Runner


@dataclass(frozen=True)
class DispositionResult:
    ok: bool
    skipped: bool
    non_security_count: int = 0
    filed_urls: int = 0
    inline_triage: int = 0
    rejected_markers: int = 0


_INLINE_TRIAGE_RE = re.compile(re.escape(config.INLINE_TRIAGE_MARKER))
_OOS_TAG_RE = re.compile(r"OOS_\d+")
_FILED_URL_LINE = re.compile(
    r"^\s*-\s+\*\*Filed URL\*\*:\s+https://",
    re.MULTILINE,
)
_OOS_HEADER_RE = re.compile(r"^###\s+OOS_", re.MULTILINE)
_SECURITY_FOCUS_RE = re.compile(
    r"^\s*-\s*\*\*focus-area\*\*\s*:\s*"
    r"security([-a-zA-Z0-9 _]*)(\s|$|\(|#|\.|,)",
    re.IGNORECASE | re.MULTILINE,
)
_REJECTED_SECTION_RE = re.compile(
    r"(?:Rejected / Out-of-Scope|## Rejected)",
    re.IGNORECASE,
)
_SECTION_HEADING_RE = re.compile(r"^##\s+")


def _github_issue_url_pattern() -> re.Pattern[str]:
    gh_host = os.environ.get("GH_HOST", "github.com")
    if gh_host and gh_host != "github.com":
        esc = re.escape(gh_host)
        host = f"(?:{esc}|github\\.com)"
    else:
        host = r"github\.com"
    return re.compile(
        rf"https://{host}/[^/\s]+/[^/\s]+/issues/\d+",
    )


def _count_non_security_markdown(text: str) -> int:
    """Port oos-non-security-block-count.awk block counting."""
    count = 0
    in_block = False
    security = False
    for line in text.splitlines():
        if _OOS_HEADER_RE.match(line):
            if in_block and not security:
                count += 1
            in_block = True
            security = False
            continue
        if in_block and _SECURITY_FOCUS_RE.match(line):
            security = True
    if in_block and not security:
        count += 1
    return count


def _count_non_security(accepted_paths: tuple[str, ...]) -> int:
    total = 0
    for path in accepted_paths:
        file_path = Path(path)
        if not file_path.is_file():
            continue
        text = file_path.read_text(encoding="utf-8")
        if _OOS_HEADER_RE.search(text):
            total += _count_non_security_markdown(text)
    return total


def count_non_security(accepted_paths: tuple[str, ...]) -> int:
    """Count non-security accepted OOS blocks in markdown files."""
    return _count_non_security(accepted_paths)


def _count_filed_urls_loose(paths: tuple[str, ...]) -> int:
    url_re = _github_issue_url_pattern()
    urls: set[str] = set()
    for path in paths:
        if not Path(path).is_file():
            continue
        text = Path(path).read_text(encoding="utf-8")
        urls.update(url_re.findall(text))
    return len(urls)


def _count_filed_url_field_lines(paths: tuple[str, ...]) -> int:
    url_re = _github_issue_url_pattern()
    urls: set[str] = set()
    for path in paths:
        if not Path(path).is_file():
            continue
        text = Path(path).read_text(encoding="utf-8")
        for line in text.splitlines():
            if _FILED_URL_LINE.match(line):
                urls.update(url_re.findall(line))
    return len(urls)


def _is_rejected_heading(line: str) -> bool:
    lowered = line.lower()
    return bool(
        re.match(r"^##\s*rejected", lowered)
        or re.search(r"rejected\s*/\s*out-of-scope", lowered)
    )


def _rejected_section(body: str) -> str:
    """Slice rejected markers like count_rejected_oos_markers_from_ndjson awk."""
    if not _REJECTED_SECTION_RE.search(body):
        return ""
    tail_lines: list[str] = []
    injecting = False
    for line in body.splitlines():
        if _is_rejected_heading(line):
            injecting = True
            continue
        if injecting and _SECTION_HEADING_RE.match(line) and not _is_rejected_heading(line):
            break
        if injecting:
            tail_lines.append(line)
    return "\n".join(tail_lines)


def _count_rejected_markers(ndjson_path: str | None) -> int:
    if not ndjson_path or not Path(ndjson_path).is_file():
        return 0
    tags: set[str] = set()
    for line in Path(ndjson_path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, dict):
            continue
        row_map = cast("dict[str, object]", row)
        body_obj = row_map.get("body")
        body = body_obj if isinstance(body_obj, str) else str(body_obj or "")
        section = _rejected_section(body)
        if not section:
            continue
        tags.update(_OOS_TAG_RE.findall(section))
    return len(tags)


def _count_inline_triage(commit_messages: str) -> int:
    return len(_INLINE_TRIAGE_RE.findall(commit_messages))


def disposition_ok(
    _runner: Runner,
    *,
    accepted_files: tuple[str, ...],
    filed_urls_files: tuple[str, ...] = (),
    filed_urls_strict_files: tuple[str, ...] = (),
    oos_issues_ndjson: str | None = None,
    commit_range_messages: str = "",
    forked: bool = False,
    repo_unavailable: bool = False,
) -> DispositionResult:
    """Return whether non-security OOS entries are disposition-covered."""
    if forked or repo_unavailable:
        return DispositionResult(ok=True, skipped=True)
    non_sec = _count_non_security(accepted_files)
    if non_sec == 0:
        return DispositionResult(ok=True, skipped=False, non_security_count=0)
    ndjson_paths = (oos_issues_ndjson,) if oos_issues_ndjson else ()
    loose_paths = (*filed_urls_files, *ndjson_paths)
    filed = _count_filed_urls_loose(loose_paths) + _count_filed_url_field_lines(
        filed_urls_strict_files,
    )
    inline = _count_inline_triage(commit_range_messages)
    rejected = _count_rejected_markers(oos_issues_ndjson)
    ok = filed > 0 or inline >= non_sec or rejected >= non_sec
    return DispositionResult(
        ok=ok,
        skipped=False,
        non_security_count=non_sec,
        filed_urls=filed,
        inline_triage=inline,
        rejected_markers=rejected,
    )
