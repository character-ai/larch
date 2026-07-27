"""Focused contract tests for durable /umbrella proposal state."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from larch.issue import umbrella


def _proposal() -> umbrella.ProposalRecord:
    body = umbrella.leaf_opening(umbrella="12") + "\n\nImplement the leaf."
    leaf = umbrella.ExpectedLeaf(
        identity=umbrella.leaf_identity(title="[LEAF OF 12] One", body=body),
        title="[LEAF OF 12] One",
        body=body,
    )
    return umbrella.ProposalRecord("12", "owner/repo", "2026-07-26T00:00:00Z", "context", (leaf,))


def test_proposal_round_trip_marks_in_flight_before_resolution(tmp_path: Path) -> None:
    path = tmp_path / "proposal.json"
    umbrella.persist_proposal(path=path, proposal=_proposal())
    marked = umbrella.mark_in_flight(proposal_path=path, identity=_proposal().leaves[0].identity)
    assert marked.leaves[0].state == "in-flight"
    resolved = umbrella.record_resolved(
        proposal_path=path,
        identity=marked.leaves[0].identity,
        number="34",
        url="https://example.test/issues/34",
        issue_id="99",
    )
    assert resolved.leaves[0].state == "resolved"
    assert umbrella.load_proposal(path).leaves[0].number == "34"


def test_in_flight_recovery_requires_exact_unique_leaf_contract() -> None:
    proposal = _proposal()
    in_flight = umbrella.ProposalRecord(
        proposal.umbrella,
        proposal.repository,
        proposal.expected_updated_at,
        proposal.common_context,
        (umbrella.ExpectedLeaf(**{**proposal.leaves[0].__dict__, "state": "in-flight"}),),
    )
    leaf = in_flight.leaves[0]
    result = umbrella.reconcile_in_flight(
        proposal=in_flight,
        identity=leaf.identity,
        candidates=[{"number": 34, "url": "https://example.test/issues/34", "id": 99, "title": leaf.title, "body": leaf.body}],
    )
    assert result.number == "34"
    with pytest.raises(umbrella.UmbrellaError, match="ambiguous-in-flight-recovery"):
        umbrella.reconcile_in_flight(
            proposal=in_flight,
            identity=leaf.identity,
            candidates=[{"number": 34, "url": "u", "title": leaf.title, "body": leaf.body}] * 2,
        )


def test_invalid_proposal_refuses_tampered_leaf_identity(tmp_path: Path) -> None:
    path = tmp_path / "proposal.json"
    payload = json.loads(json.dumps(umbrella.asdict(_proposal())))
    payload["leaves"][0]["identity"] = "tampered"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(umbrella.UmbrellaError, match="invalid-proposal-record"):
        umbrella.load_proposal(path)
