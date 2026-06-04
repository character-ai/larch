"""Create the GitHub issue for /report-tokens analysis."""

from __future__ import annotations

import sys

import config
import gh
import redact
from errors import ShipError
from proc import CommandResult, Runner
from report_tokens_models import ReportSection, SectionPriority

_TRUNCATION_PREFIX = (
    "## ⚠ Report body trimmed to fit GitHub's size limit\n\n"
    "This report is incomplete because low-priority sections were omitted before posting. "
    "Run `/report-tokens --no-issue` locally for the full output.\n\n"
)

_TITLE_BY_SECTION = {
    "summary": "Report Tokens Analysis",
    "aggregate": "Aggregate cost by workflow",
    "vendor": "Vendor breakdown",
    "top": "Top runs by estimated cost",
    "trends": "Per-day cost trends",
    "suggestions": "Cost-reduction suggestions",
    "rates": "Rates used for display/fallback",
}


def _bytes(text: str) -> int:
    return len(text.encode("utf-8"))


def _assemble(sections: list[ReportSection]) -> str:
    return "\n\n".join(section.body.strip() for section in sections if section.body.strip()) + "\n"


def _posting_body(text: str) -> str:
    return redact.redact(redact.redact(text))


def _section_label(section: ReportSection) -> str:
    return _TITLE_BY_SECTION.get(section.title, section.title)


def _trim_sections(sections: list[ReportSection], *, limit: int) -> tuple[str, list[str]]:
    kept = list(sections)
    omitted: list[str] = []
    redacted = _posting_body(_assemble(kept))
    if _bytes(redacted) <= limit:
        return redacted, omitted
    candidates = sorted(
        [section for section in kept if section.priority != SectionPriority.BANNER],
        key=lambda section: int(section.priority),
        reverse=True,
    )
    for candidate in candidates:
        kept.remove(candidate)
        omitted.append(_section_label(candidate))
        notice = _TRUNCATION_PREFIX + f"Omitted sections: {', '.join(omitted)}.\n\n"
        redacted = _posting_body(notice + _assemble(kept))
        if _bytes(redacted) <= limit:
            return redacted, omitted
    notice = _TRUNCATION_PREFIX + f"Omitted sections: {', '.join(omitted)}.\n\n"
    return _posting_body(notice + _assemble(kept)), omitted


def assemble_issue_body(sections: list[ReportSection]) -> str:
    body, _ = _trim_sections(sections, limit=config.GITHUB_ISSUE_BODY_MAX_BYTES)
    return body


def post_issue(
    runner: Runner,
    *,
    repo: str | None,
    title: str,
    sections: list[ReportSection],
) -> None:
    body, _omitted = _trim_sections(sections, limit=config.GITHUB_ISSUE_BODY_MAX_BYTES)
    if _bytes(body) > config.GITHUB_ISSUE_BODY_MAX_BYTES:
        msg = "ERROR: report issue body remains over GitHub's 65536-byte limit after trimming"
        print(msg, file=sys.stderr)
        raise ShipError(msg)
    try:
        result: CommandResult = gh.issue_create(runner, repo=repo, title=title, body=body)
    except ShipError as exc:
        print(f"ERROR: gh issue create failed: {exc}", file=sys.stderr)
        raise
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        msg = f"ERROR: gh issue create failed ({result.returncode})"
        if detail:
            msg = f"{msg}: {detail}"
        print(msg, file=sys.stderr)
        raise ShipError(msg)
