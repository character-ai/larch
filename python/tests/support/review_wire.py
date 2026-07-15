"""Canonical wire-format builders for review and plan-review tests.

The builders deliberately serialize only valid, ordinary fixture shapes. Tests
that exercise malformed or legacy wire data should keep their literals inline.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import TypeAlias

WireValue: TypeAlias = str | int | float | bool | None | Path
WireRow: TypeAlias = Mapping[str, WireValue]


def make_finding_block(  # noqa: PLR0913 - canonical Markdown fields map directly to the wire format.
    item_id: str,
    title: str,
    *,
    reviewer: str | Sequence[str] | None = None,
    location: str | None = None,
    severity: str | None = None,
    concern: str | None = None,
    suggested_revision: str | None = None,
) -> str:
    """Build one ordinary finding or OOS Markdown block with terminal spacing."""
    lines: list[str] = [f"### {item_id}: {title}"]
    if reviewer is not None:
        reviewers: str = ", ".join(reviewer) if not isinstance(reviewer, str) else reviewer
        label: str = "Reviewer" if isinstance(reviewer, str) else "Reviewer(s)"
        lines.append(f"- **{label}**: {reviewers}")
    if location is not None:
        lines.append(f"- **Location**: {location}")
    if severity is not None:
        lines.append(f"- **Severity**: {severity}")
    if concern is not None:
        lines.append(f"- **Concern**: {concern}")
    if suggested_revision is not None:
        lines.append(f"- **Suggested revision**: {suggested_revision}")
    return "\n".join(lines) + "\n\n"


def make_rejected_block(  # noqa: PLR0913 - rejected tally fields map directly to the wire format.
    item_id: str,
    title: str,
    *,
    location: str,
    concern: str,
    severity: str = "major",
    plan_review: bool = True,
) -> str:
    """Build a rejected-finding block in the plan-review tally's normal shape."""
    prefix: str = f"### [Plan Review] {item_id}\n\n" if plan_review else ""
    return (
        prefix
        + f"### {item_id}: {title}\n"
        + f"- **Location**: {location}\n"
        + f"- **Concern**: {concern}\n"
        + f"- **Severity**: {severity}\n\n"
    )


def vote_lines(votes: Mapping[str, str]) -> str:
    """Serialize canonical per-item judge vote lines in caller-supplied order."""
    return "".join(f"{item_id}: {vote}\n" for item_id, vote in votes.items())


def ballot_snippet(*blocks: str) -> str:
    """Compose complete Markdown blocks with exactly one blank line between them."""
    if not blocks:
        return ""
    return "\n\n".join(block.rstrip("\n") for block in blocks) + "\n"


def plan_review_slot_line(  # noqa: PLR0913 - manifest fields are intentionally named at fixture call sites.
    slot: str,
    tool: str,
    output: str | Path,
    *,
    prompt_file: str | Path | None = None,
    vendor: str | None = None,
    resolved_model: str | None = None,
    **optional_fields: WireValue,
) -> dict[str, WireValue]:
    """Build one valid plan-review slot-manifest row without reordering fields."""
    row: dict[str, WireValue] = {"slot": slot, "tool": tool, "output": output}
    if prompt_file is not None:
        row["prompt_file"] = prompt_file
    if vendor is not None:
        row["vendor"] = vendor
    if resolved_model is not None:
        row["resolved_model"] = resolved_model
    row.update(optional_fields)
    return row


def panel_manifest_row(
    slot: str,
    tool: str,
    output: str | Path,
    **optional_fields: WireValue,
) -> dict[str, WireValue]:
    """Build one valid shared panel-manifest row."""
    row: dict[str, WireValue] = {"slot": slot, "tool": tool, "output": output}
    row.update(optional_fields)
    return row


def slot_manifest_ndjson(rows: Sequence[WireRow]) -> str:
    """Serialize rows as compact NDJSON, preserving order and ending in one newline."""
    if not rows:
        return ""
    return "".join(json.dumps(dict(row), default=str, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows)


def panel_manifest_ndjson(rows: Sequence[WireRow]) -> str:
    """Serialize shared panel-manifest rows using the canonical NDJSON contract."""
    return slot_manifest_ndjson(rows)


def code_review_classification_row(  # noqa: PLR0913 - columns are a wire-format fixture.
    finding_id: str,
    result: str,
    *,
    reviewer: str = "reviewer",
    vote1: str = "YES",
    severity1: str = "major",
    vote2: str = "NO",
    scope: str = "",
) -> str:
    """Build one ordinary code-review findings-classification TSV row."""
    return (
        f"{finding_id}\t{reviewer}\t{result}\t{vote1}\ttrue\t{severity1}\tgood\tfalse\t"
        f"cursor-validity\t{vote2}\ttrue\tminor\tgood\tfalse\tcodex-plan-fidelity\t"
        f"NO\ttrue\tminor\tgood\tfalse\tcodex-pragmatism\t{scope}"
    )
