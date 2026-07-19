"""Descriptor for architectural guideline and invariant assessment lifecycles."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from functools import partial

from larch.core import config

EntryParser = Callable[[str], str]

_MARKDOWN_HEADING_RE = re.compile(r"^#{1,6}\s+\S")  # lint-markdown-heading-fence-state: ok fenced-line indices are precomputed via plan_grammar.balanced_fence_line_indices and skipped before this check
_WHY_RE = re.compile(r"^\s*-\s*Why:\s*(.+?)\s*$")
_DEVIATE_RE = re.compile(r"^\s*-\s*Deviate when:\s*(.+?)\s*$")
_MECHANIZED_RE = re.compile(r"^\s*-\s*Mechanized:\s*(.+?)\s*$")


def _guideline_body(body: list[str]) -> list[str]:
    details: list[str] = []
    mechanized = ""
    for line in body:
        for pattern, label in (
            (_MECHANIZED_RE, "Mechanized"), (_WHY_RE, "Why"), (_DEVIATE_RE, "Deviate when")
        ):
            if match := pattern.match(line):
                normalized = f"- {label}: {match.group(1).strip()}"
                if label == "Mechanized":
                    mechanized = normalized
                else:
                    details.append(normalized)
                break
    return [mechanized] if mechanized else details


def _parse_entries(  # noqa: C901 - per-line heading/fence classification plus entry-body assembly each need multiple branches
    raw_text: str, *, heading_re: re.Pattern[str], preserve_body: bool
) -> str:
    from larch.design import plan_grammar  # noqa: PLC0415 - deferred function-level import keeps larch.core import-time free of larch.design  # lint-layering: ok reuse the balanced fenced-code-block scanner (G-Md-3) instead of re-deriving fence state.

    entries: list[list[str]] = []
    heading: str | None = None
    body: list[str] = []

    def append_entry() -> None:
        nonlocal heading, body
        if heading is None:
            return
        if preserve_body:
            while body and not body[0].strip():
                _ = body.pop(0)
            while body and not body[-1].strip():
                _ = body.pop()
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
        match = heading_re.match(raw_line)
        if match:
            append_entry()
            heading = f"### {match.group(1)}: {match.group(2).strip()}"
            continue
        if _MARKDOWN_HEADING_RE.match(raw_line):
            append_entry()
            continue
        if heading is not None:
            body.append(raw_line)
    append_entry()
    return "\n\n".join("\n".join(entry) for entry in entries).strip()


_parse_guideline_entries = partial(
    _parse_entries,
    heading_re=re.compile(r"^###\s+(G-[A-Za-z0-9-]+-\d+):\s*(.+?)\s*$"),  # lint-shared-convention-regex: ok canonical definition; architectural_guidelines.GUIDELINE_HEADING_RE derives from this field
    preserve_body=False,
)
_parse_invariant_entries = partial(
    _parse_entries,
    heading_re=re.compile(r"^#{1,6}\s+(I-[A-Za-z0-9-]+-\d+):\s*(.+?)\s*$"),  # lint-shared-convention-regex: ok canonical definition; architectural_guidelines.INVARIANT_HEADING_RE derives from this field
    preserve_body=True,
)


@dataclass(frozen=True)
class AssessmentKind:
    """All kind-specific policy and wire names for one assessment lifecycle."""

    key: str
    singular: str
    filename: str
    env_prefix: str
    status_field: str
    status_env_key: str
    path_env_key: str
    clean_presentation_note: str
    assessment_required_line: str
    design_assessment: str
    staged_assessment: str
    staged_assessment_env: str
    materialized_diff: str
    durable_note: str
    durable_note_env: str
    dropped_note_artifact: str
    ship_outcome_sidecar: str
    materialize_env: str
    heading_re: re.Pattern[str]
    identifier_re: re.Pattern[str]
    parse_entries: EntryParser
    authored_outcomes: frozenset[str]
    non_clean_authored_outcome: str
    ship_outcomes: frozenset[str]
    non_clean_ship_outcome: str
    absent_reason: str
    invalid_reason: str
    empty_reason: str
    non_clean_note_reason: str
    ship_reason_tokens: frozenset[str]
    ship_present_empty: bool
    design_requires_nonempty: bool
    design_empty_removes: bool
    flush_outcome: bool

    @property
    def is_invariant(self) -> bool:
        return self.key == config.ASSESSMENT_KIND_INVARIANTS


_COMMON_REASONS = frozenset(
    {
        "clean-note",
        "note-read-failed",
        "note-redaction-failed",
        "compose-materialization-failed",
        config.REASON_DETERMINISTIC_CLEAN,
        config.REASON_UNAVAILABLE,
        "unknown",
    }
)

GUIDELINES = AssessmentKind(
    key=config.ASSESSMENT_KIND_GUIDELINES,
    singular="guideline",
    filename="ARCHITECTURAL_GUIDELINES.md",
    env_prefix="ARCHITECTURAL_GUIDELINES",
    status_field="guidelines_status",
    status_env_key="GUIDELINES_STATUS",
    path_env_key="GUIDELINES_PATH",
    clean_presentation_note="Consulted ARCHITECTURAL_GUIDELINES.md; no deviations identified.",
    assessment_required_line="GUIDELINES_DEVIATION_ASSESSMENT_REQUIRED=true",
    design_assessment="architectural-guideline-assessment.md",
    staged_assessment="architectural-guideline-staged-assessment.md",
    staged_assessment_env="architectural-guideline-staged-assessment.env",
    materialized_diff="architectural-guideline-materialized-diff.txt",
    durable_note="architectural-guideline-note.md",
    durable_note_env="architectural-guideline-note.meta.env",
    dropped_note_artifact="architectural-guideline-drop-notice.txt",
    ship_outcome_sidecar="architectural-guideline-outcome.json",
    materialize_env="architectural-guideline-materialize.env",
    heading_re=re.compile(r"^###\s+(G-[A-Za-z0-9-]+-\d+):\s*(.+?)\s*$", re.MULTILINE),  # lint-shared-convention-regex: ok canonical definition; architectural_guidelines.GUIDELINE_HEADING_RE derives from this field
    identifier_re=re.compile(r"G-[A-Za-z0-9-]+-\d+"),
    parse_entries=_parse_guideline_entries,
    authored_outcomes=config.GUIDELINE_ASSESSMENT_OUTCOMES,
    non_clean_authored_outcome=config.ASSESSMENT_OUTCOME_DEVIATION,
    ship_outcomes=frozenset({"pinned", "clean", "dropped"}),
    non_clean_ship_outcome="pinned",
    absent_reason="guidelines-absent",
    invalid_reason="guidelines-invalid",
    empty_reason="",
    non_clean_note_reason="note-pinned",
    ship_reason_tokens=_COMMON_REASONS | {"note-pinned", "guidelines-absent", "guidelines-invalid"},
    ship_present_empty=False,
    design_requires_nonempty=False,
    design_empty_removes=False,
    flush_outcome=True,
)

INVARIANTS = AssessmentKind(
    key=config.ASSESSMENT_KIND_INVARIANTS,
    singular="invariant",
    filename="ARCHITECTURAL_INVARIANTS.md",
    env_prefix="ARCHITECTURAL_INVARIANTS",
    status_field="invariants_status",
    status_env_key="INVARIANTS_STATUS",
    path_env_key="INVARIANTS_PATH",
    clean_presentation_note="Consulted ARCHITECTURAL_INVARIANTS.md; no violations identified.",
    assessment_required_line="INVARIANTS_VIOLATION_ASSESSMENT_REQUIRED=true",
    design_assessment="architectural-invariant-assessment.md",
    staged_assessment="architectural-invariant-staged-assessment.md",
    staged_assessment_env="architectural-invariant-staged-assessment.env",
    materialized_diff="architectural-invariant-materialized-diff.txt",
    durable_note="architectural-invariant-note.md",
    durable_note_env="architectural-invariant-note.meta.env",
    dropped_note_artifact="architectural-invariant-drop-notice.txt",
    ship_outcome_sidecar="architectural-invariant-outcome.json",
    materialize_env="architectural-invariant-materialize.env",
    heading_re=re.compile(r"^#{1,6}\s+(I-[A-Za-z0-9-]+-\d+):\s*(.+?)\s*$", re.MULTILINE),  # lint-shared-convention-regex: ok canonical definition; architectural_guidelines.INVARIANT_HEADING_RE derives from this field
    identifier_re=re.compile(r"I-[A-Za-z0-9-]+-\d+"),
    parse_entries=_parse_invariant_entries,
    authored_outcomes=config.INVARIANT_ASSESSMENT_OUTCOMES,
    non_clean_authored_outcome=config.ASSESSMENT_OUTCOME_VIOLATION,
    ship_outcomes=frozenset({"clean", "violation", "dropped"}),
    non_clean_ship_outcome="violation",
    absent_reason="invariants-absent",
    invalid_reason="invariants-invalid",
    empty_reason="invariants-empty",
    non_clean_note_reason="violation-note",
    ship_reason_tokens=_COMMON_REASONS
    | {"invariants-absent", "invariants-empty", "invariants-invalid", "violation-note"},
    ship_present_empty=True,
    design_requires_nonempty=True,
    design_empty_removes=True,
    flush_outcome=False,
)
