"""Create the GitHub issue for /report-tokens analysis."""

from __future__ import annotations

import sys

from larch.core import config
import gh
from larch.core import redact
from larch.errors import ShipError
from larch.core.proc import CommandResult, Runner
from report_tokens_models import ReportSection, SectionPriority, Skill

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
    "phase": "Phase breakdown",
    "trends": "Per-day cost trends",
    "suggestions": "Cost-reduction suggestions",
    "rates": "Rates used for display/fallback",
}


def _bytes(text: str) -> int:
    return len(text.encode("utf-8"))


def _assemble(sections: list[ReportSection]) -> str:
    return "\n\n".join(section.body.strip() for section in sections if section.body.strip()) + "\n"


def _posting_body(text: str) -> str:
    redacted = redact.redact(text)
    if "[content truncated" in redacted:
        msg = "ERROR: report issue body redaction failed"
        print(msg, file=sys.stderr)
        raise ShipError(msg)
    return redacted


def _section_label(*, section: ReportSection, skill: Skill) -> str:
    if section.title == "aggregate" and skill == "implement":
        return "Aggregate cost"
    return _TITLE_BY_SECTION.get(section.title, section.title)


def _trim_sections(sections: list[ReportSection], *, limit: int, skill: Skill) -> tuple[str, list[str]]:
    kept: list[ReportSection] = list(sections)
    omitted: list[str] = []
    redacted = _posting_body(_assemble(kept))
    if _bytes(redacted) <= limit:
        return redacted, omitted
    candidates: list[ReportSection] = sorted(
        [section for section in kept if section.priority != SectionPriority.BANNER],
        key=lambda section: int(section.priority),
        reverse=True,
    )
    for candidate in candidates:
        kept.remove(candidate)
        omitted.append(_section_label(section=candidate, skill=skill))
        notice = _TRUNCATION_PREFIX + f"Omitted sections: {', '.join(omitted)}.\n\n"
        redacted = _posting_body(notice + _assemble(kept))
        if _bytes(redacted) <= limit:
            return redacted, omitted
    notice = _TRUNCATION_PREFIX + f"Omitted sections: {', '.join(omitted)}.\n\n"
    return _posting_body(notice + _assemble(kept)), omitted


def assemble_issue_body(sections: list[ReportSection], *, skill: Skill) -> str:
    body, _ = _trim_sections(sections, limit=config.GITHUB_ISSUE_BODY_MAX_BYTES, skill=skill)
    return body


def post_issue(
    runner: Runner,
    *,
    repo: str | None,
    title: str,
    sections: list[ReportSection],
    skill: Skill,
) -> None:
    body, _omitted = _trim_sections(sections, limit=config.GITHUB_ISSUE_BODY_MAX_BYTES, skill=skill)
    if _bytes(body) > config.GITHUB_ISSUE_BODY_MAX_BYTES:
        msg = "ERROR: report issue body remains over GitHub's 65536-byte limit after trimming"
        print(msg, file=sys.stderr)
        raise ShipError(msg)
    try:
        result: CommandResult = gh.issue_create(runner, repo=repo, title=title, body=body, redact_body=False)
    except ShipError as exc:
        print(f"ERROR: gh issue create failed: {exc}", file=sys.stderr)
        raise
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        msg = f"ERROR: gh issue create failed ({result.returncode})"
        if detail:
            msg = f"{msg}: {redact.redact(detail)}"
        print(msg, file=sys.stderr)
        raise ShipError(msg)
    output = result.stdout.strip()
    if output:
        print(redact.redact(output).rstrip())
    else:
        print(f"Created GitHub issue: {title}")
