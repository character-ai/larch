# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false, reportOptionalSubscript=false, reportOptionalMemberAccess=false, reportPossiblyUnboundVariable=false, reportUnnecessaryComparison=false, reportUnknownLambdaType=false, reportArgumentType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnusedImport=false, reportUnusedFunction=false, reportPrivateUsage=false, reportUnusedVariable=false
# pylint: skip-file
"""Shared OOS disposition counters for audit scan parity."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class OosDispositionCounts:
    non_security_oos_blocks: int
    issue_urls: int
    inline_triage_hits: int
    rejected_oos_markers: int
    ndjson_parse_error: bool = False


def _issue_url_re() -> re.Pattern[str]:
    host = os.environ.get("GH_HOST", "")
    if host and host != "github.com":
        host_re = f"(?:{re.escape(host)}|github\\.com)"
    else:
        host_re = r"github\.com"
    return re.compile(rf"https://{host_re}/[^\s/]+/[^\s/]+/issues/[0-9]+")


def count_filed_urls_union_files(paths: list[Path]) -> int:
    rx = _issue_url_re()
    urls: set[str] = set()
    for path in paths:
        if not path.is_file():
            continue
        urls.update(rx.findall(path.read_text(encoding="utf-8", errors="replace")))
    return len(urls)


def _is_security_header(line: str) -> bool:
    lower = line.lower()
    return bool(re.match(r"^###[ \t]+(oos_[0-9]+:|finding_[0-9]+:)[ \t]*(\[(out_of_scope|oos)\][ \t]*)?`?(\[security\]|<security>)`?([ \t]|$|[:-])", lower))


def count_non_security_oos_blocks(path: Path) -> int:
    if not path.is_file():
        return 0
    count = 0
    in_block = False
    security = False
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.rstrip("\r")
        starts = bool(re.match(r"^###[ \t]+OOS_", line)) or (re.match(r"^###[ \t]+FINDING_[0-9]+:", line) and re.search(r"\[(OUT_OF_SCOPE|OOS)\]", line))
        if starts:
            if in_block and not security:
                count += 1
            in_block = True
            security = _is_security_header(line)
            continue
        if in_block:
            lower = line.lower().replace("`", "").replace("*", "")
            if re.match(r"^[ \t-]*focus[- \t]*area[ \t]*[:=][ \t]*security([- \t:A-Za-z0-9_]*)([ \t]|$|\(|#|\.|,)", lower):
                security = True
    if in_block and not security:
        count += 1
    return count


def count_rejected_oos_markers_from_ndjson(path: Path) -> tuple[int, bool]:
    if not path.is_file() or path.stat().st_size == 0:
        return 0, False
    tags: set[str] = set()
    parse_error = False
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            data: object = json.loads(line)
        except json.JSONDecodeError:
            parse_error = True
            continue
        if not isinstance(data, dict):
            parse_error = True
            continue
        body = str(data.get("body") or "")
        if "Rejected / Out-of-Scope" not in body and "## Rejected" not in body:
            continue
        in_rej = False
        tail: list[str] = []
        for bline in body.splitlines():
            low = bline.lower()
            rej_heading = low.startswith("## rejected") or "rejected / out-of-scope" in low
            if rej_heading:
                in_rej = True
                continue
            if in_rej and re.match(r"^##[ \t]+", bline) and not rej_heading:
                break
            if in_rej:
                tail.append(bline)
        for item in re.findall(r"OOS_[0-9]+", "\n".join(tail)):
            tags.add(item)
    return len(tags), parse_error


def count_inline_triage_hits(run_dir: Path) -> int:
    lines: set[str] = set()
    found = False
    for name in ("codex-commit-message.txt", "session-transcript.jsonl"):
        path = run_dir / name
        if not path.is_file():
            continue
        found = True
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if "Inline-triage rule" in line:
                lines.add(line)
    return len(lines) if found else 0


def analyze_run_dir(run_dir: Path) -> OosDispositionCounts:
    accepted = sum(count_non_security_oos_blocks(run_dir / name) for name in (
        "oos-accepted-main-agent.md",
        "oos-accepted-design.md",
        "oos-accepted-review.md",
    ))
    ndjson = run_dir / "oos-issues.ndjson"
    rejected, parse_error = count_rejected_oos_markers_from_ndjson(ndjson)
    url_files = [p for p in (ndjson, run_dir / "oos-issues-created.md") if p.is_file()]
    return OosDispositionCounts(
        non_security_oos_blocks=accepted,
        issue_urls=count_filed_urls_union_files(url_files),
        inline_triage_hits=count_inline_triage_hits(run_dir),
        rejected_oos_markers=rejected,
        ndjson_parse_error=parse_error,
    )
