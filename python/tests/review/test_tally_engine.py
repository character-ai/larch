"""Unit coverage for the shared review tally adjudication engine."""

from __future__ import annotations

from pathlib import Path

import pytest

from larch.review import tally_engine


def _context(
    *, item_id: str = "FINDING_1", yes: int = 2, no: int = 0, is_oos: bool = False, severity: str = "major"
) -> tally_engine.ItemContext:
    votes = (("v1", "YES"), ("v2", "YES"), ("v3", ""))
    return tally_engine.ItemContext(
        item_id=item_id,
        block_path=Path(f"/{item_id}.md"),
        block_text=f"### {item_id}: example\n",
        artifact_text=f"### {item_id}: example\n",
        reviewer="reviewer-a",
        cells=(("YES", "true", severity, "good", "false", None), ("YES", "true", severity, "good", "false", None)),
        yes=yes,
        no=no,
        judge_error=0,
        is_oos=is_oos,
        eligible_voters=2,
        voter_votes=votes,
        voter_severities=(severity, severity, ""),
    )


def test_adjudicate_caches_accepted_finding_policy() -> None:
    result = tally_engine.adjudicate_item(_context())

    assert result.voting_result == "accepted"
    assert result.classification_scope == "in_scope"
    assert result.score_kind == "finding"
    assert result.accepted_weight == 2
    assert result.unique_finder_eligible is True
    assert result.ledger_outcome == "accepted"


def test_adjudicate_neutral_major_finding_reroutes_to_oos() -> None:
    result = tally_engine.adjudicate_item(_context(yes=1, no=1))

    assert result.voting_result == "neutral"
    assert result.neutral_rescued is True
    assert result.classification_scope == "oos"
    assert result.reroute_marker == "neutral-rescued"
    assert result.artifact_bucket == "oos"


def test_non_fileable_accepted_oos_scores_neutral() -> None:
    result = tally_engine.adjudicate_item(_context(item_id="OOS_1", is_oos=True, severity="minor"))

    assert result.voting_result == "accepted"
    assert result.fileable_oos is False
    assert result.score_result == "neutral"


def test_run_items_streams_security_before_publication_and_stops_on_failure() -> None:
    events: list[str] = []

    def contexts() -> object:
        yield _context(item_id="FINDING_1")
        yield _context(item_id="FINDING_2")
        raise AssertionError("later items must not be prepared")

    def serialize(result: tally_engine.ItemAdjudicationResult) -> None:
        events.append(f"serialize:{result.context.item_id}")

    def security(context: tally_engine.ItemContext) -> bool:
        events.append(f"security:{context.item_id}")
        if context.item_id == "FINDING_2":
            raise RuntimeError("security failed")
        return False

    def publish(result: tally_engine.ItemAdjudicationResult) -> None:
        events.append(f"publish:{result.context.item_id}")

    with pytest.raises(RuntimeError, match="security failed"):
        tally_engine.run_items(contexts(), serialize=serialize, security_hook=security, publish=publish)  # type: ignore[arg-type]

    assert events == [
        "serialize:FINDING_1",
        "security:FINDING_1",
        "publish:FINDING_1",
        "serialize:FINDING_2",
        "security:FINDING_2",
    ]
