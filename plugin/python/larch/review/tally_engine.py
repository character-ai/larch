"""Shared, ordered per-item adjudication for review tally families."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, replace
from pathlib import Path

from larch.review import voting

VoteCell = tuple[str, str, str, str, str, str | None]


@dataclass(frozen=True)
class ItemContext:
    """Family-prepared inputs for one ballot item.

    Families own parsing and attribution restoration.  The engine owns only the
    policy decisions that must remain identical as tally implementations converge.
    """

    item_id: str
    block_path: Path
    block_text: str
    artifact_text: str
    reviewer: str
    cells: tuple[VoteCell, ...]
    yes: int
    no: int
    judge_error: int
    is_oos: bool
    eligible_voters: int
    voter_votes: tuple[tuple[str, str], ...]
    voter_severities: tuple[str, ...]


@dataclass(frozen=True)
class ItemAdjudicationResult:
    """Cached policy outcome, before and after the family security hook."""

    context: ItemContext
    voting_result: str
    classification_scope: str
    neutral_rescued: bool
    fileable_oos: bool
    score_kind: str
    score_result: str
    accepted_weight: int
    unique_finder_eligible: bool
    ledger_outcome: str
    reroute_marker: str
    artifact_bucket: str
    security: bool | None = None


def _finding_oos_reroute_marker(*, block_text: str, neutral_rescued: bool) -> str:
    """Return the engine-owned marker for a neutral finding rerouted to OOS."""
    _ = block_text
    return "neutral-rescued" if neutral_rescued else ""


def adjudicate_item(context: ItemContext) -> ItemAdjudicationResult:
    """Evaluate the shared policy for a fully prepared item exactly once."""
    vote_values = tuple(vote for _label, vote in context.voter_votes)
    if context.is_oos:
        voting_result = voting.classify_oos_result(
            yes=context.yes,
            no=context.no,
            exonerate=0,
            eligible=context.eligible_voters,
        )
    else:
        voting_result = voting.classify_result(
            yes=context.yes,
            no=context.no,
            exonerate=0,
            eligible=context.eligible_voters,
        )
    fileable_oos = voting.oos_fileable_from_votes(
        voting_result,
        yes_votes=vote_values,
        severities=context.voter_severities,
    )
    neutral_rescued = voting.neutral_high_severity_rescue_to_oos(
        voting_result,
        yes_votes=vote_values,
        severities=context.voter_severities,
    )
    score_kind = "oos" if context.is_oos or neutral_rescued else "finding"
    score_result = "neutral" if context.is_oos and voting_result == "accepted" and not fileable_oos else voting_result
    accepted_weight = (
        voting.accepted_finding_points_from_severities(context.voter_severities, votes=vote_values)
        if score_kind == "finding" and score_result == "accepted"
        else 0
    )
    classification_scope = "oos" if context.is_oos or neutral_rescued else "in_scope"
    ledger_outcome = "oos" if classification_scope == "oos" else voting_result
    if context.is_oos or neutral_rescued:
        artifact_bucket = "oos"
    elif voting_result == "accepted":
        artifact_bucket = "accepted"
    else:
        artifact_bucket = "rejected"
    return ItemAdjudicationResult(
        context=context,
        voting_result=voting_result,
        classification_scope=classification_scope,
        neutral_rescued=neutral_rescued,
        fileable_oos=fileable_oos,
        score_kind=score_kind,
        score_result=score_result,
        accepted_weight=accepted_weight,
        unique_finder_eligible=score_kind == "finding" and score_result == "accepted",
        ledger_outcome=ledger_outcome,
        reroute_marker=_finding_oos_reroute_marker(block_text=context.block_text, neutral_rescued=neutral_rescued),
        artifact_bucket=artifact_bucket,
    )


def run_items(
    contexts: Iterable[ItemContext],
    *,
    serialize: Callable[[ItemAdjudicationResult], None],
    security_hook: Callable[[ItemContext], bool],
    publish: Callable[[ItemAdjudicationResult], None],
) -> list[ItemAdjudicationResult]:
    """Run the required prepare → serialize → security → publish lifecycle.

    Iterating lazily is deliberate: failures leave prior output intact and do not
    prepare, serialize, or publish later ballot items.
    """
    completed: list[ItemAdjudicationResult] = []
    for context in contexts:
        result = adjudicate_item(context)
        serialize(result)
        completed_result = replace(result, security=security_hook(context))
        publish(completed_result)
        completed.append(completed_result)
    return completed
