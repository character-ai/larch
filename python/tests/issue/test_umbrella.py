"""Focused contract tests for durable /umbrella proposal state."""

from __future__ import annotations

import json
from dataclasses import asdict, replace
from pathlib import Path

import pytest

from larch.issue import issue_mutation, umbrella


def _proposal() -> umbrella.ProposalRecord:
    body = umbrella.leaf_opening(umbrella="12") + "\n\nImplement the leaf."
    leaf = umbrella.ExpectedLeaf(
        identity=umbrella.leaf_identity(title="[LEAF OF 12] One", body=body),
        title="[LEAF OF 12] One",
        body=body,
    )
    return umbrella.ProposalRecord("12", "owner/repo", "2026-07-26T00:00:00Z", "context", (leaf,))


def _snapshot() -> umbrella.UmbrellaSnapshot:
    return umbrella.UmbrellaSnapshot(
        repository="owner/repo",
        number="12",
        title="[DESIGNING] Split this work",
        body="Shared context.",
        state="OPEN",
        updated_at="2026-08-03T00:00:00Z",
    )


def test_managed_prepare_allows_plan_only_on_internal_partition_path(monkeypatch: pytest.MonkeyPatch) -> None:
    snapshot = issue_mutation.IssueSnapshot(
        repository="owner/repo",
        issue="12",
        title="[IMPLEMENTING] Split this work",
        body="<!-- larch:plan:start -->\nplan\n<!-- larch:plan:end -->\n",
        labels=frozenset(),
        state="OPEN",
        updated_at="2026-08-03T00:00:00Z",
    )
    active_snapshot = snapshot

    def fake_read_snapshot(_runner: object, *, repository: str, issue: str, cwd: str | None = None) -> issue_mutation.IssueSnapshot:
        _ = (repository, issue, cwd)
        return active_snapshot

    monkeypatch.setattr(umbrella.issue_mutation, "read_snapshot", fake_read_snapshot)
    with pytest.raises(umbrella.UmbrellaError, match="incompatible-input"):
        _ = umbrella.prepare_snapshot(repository="owner/repo", issue="12")
    assert umbrella.prepare_snapshot(repository="owner/repo", issue="12", managed_partition=True).title == snapshot.title

    resumed = replace(snapshot, title="[UMBRELLA] Split this work", body=snapshot.body + "\n<!-- larch:umbrella-proposal -->\n")
    active_snapshot = resumed
    assert umbrella.prepare_snapshot(repository="owner/repo", issue="12").title == resumed.title
    assert umbrella.prepare_snapshot(repository="owner/repo", issue="12", managed_partition=True).title == resumed.title


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
        _ = umbrella.reconcile_in_flight(
            proposal=in_flight,
            identity=leaf.identity,
            candidates=[{"number": 34, "url": "u", "title": leaf.title, "body": leaf.body}] * 2,
        )


def test_invalid_proposal_refuses_tampered_leaf_identity(tmp_path: Path) -> None:
    path = tmp_path / "proposal.json"
    payload = json.loads(json.dumps(umbrella.asdict(_proposal())))
    payload["leaves"][0]["identity"] = "tampered"
    _ = path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(umbrella.UmbrellaError, match="invalid-proposal-record"):
        _ = umbrella.load_proposal(path)


def test_prepared_batch_becomes_exact_umbrella_proposal() -> None:
    proposal, issue_input = umbrella.prepare_proposal_from_batch(
        snapshot=_snapshot(),
        input_text="### [BUG] split-12-1 First\n\nFirst body.\n\n### [BUG] split-12-2 Second\n\nSecond body.\n",
        deps_text="1\t2\n",
    )
    assert proposal.common_context == "Shared context."
    assert [leaf.title for leaf in proposal.leaves] == [
        "[LEAF OF 12] [BUG] split-12-1 First",
        "[LEAF OF 12] [BUG] split-12-2 Second",
    ]
    assert all(leaf.body.startswith("This is a leaf of umbrella #12. Read the umbrella in full before acting.") for leaf in proposal.leaves)
    assert proposal.dependency_edges == (
        umbrella.ExpectedDependencyEdge(blocker=proposal.leaves[0].identity, blocked=proposal.leaves[1].identity),
    )
    assert proposal.prepared_input_sha256
    assert proposal.prepared_deps_sha256
    assert "### [BUG] split-12-1 First" in issue_input
    assert "[LEAF OF 12]" not in issue_input.splitlines()[0]
    round_trip, mode = umbrella.issue_create.parse_issue_input(issue_input)
    assert mode == "generic"
    assert [item.body for item in round_trip] == [leaf.body for leaf in proposal.leaves]


@pytest.mark.parametrize(
    ("deps_text", "reason"),
    [("1\t3\n", "invalid-prepared-dependencies"), ("1\t2\n2\t1\n", "prepared-dependency-cycle")],
)
def test_prepared_batch_rejects_invalid_dependency_graph(deps_text: str, reason: str) -> None:
    with pytest.raises(umbrella.UmbrellaError, match=reason):
        _ = umbrella.prepare_proposal_from_batch(
            snapshot=_snapshot(),
            input_text="### One\n\nFirst.\n\n### Two\n\nSecond.\n",
            deps_text=deps_text,
        )


def test_prepared_batch_rejects_non_strict_dependency_rows_and_duplicate_leaves() -> None:
    snapshot = _snapshot()
    valid_input = "### One\n\nFirst.\n\n### Two\n\nSecond.\n"
    for deps_text in (" 1\t2\n", "1\t2\r\n", "1\t2\n\n2\t1\n", "\u0661\t\u0662\n"):
        with pytest.raises(umbrella.UmbrellaError, match="invalid-prepared-dependencies"):
            _ = umbrella.prepare_proposal_from_batch(snapshot=snapshot, input_text=valid_input, deps_text=deps_text)
    with pytest.raises(umbrella.UmbrellaError, match="invalid-prepared-partition"):
        _ = umbrella.prepare_proposal_from_batch(
            snapshot=snapshot,
            input_text="### Same\n\nBody.\n\n### Same\n\nBody.\n",
            deps_text="",
        )


def test_prepared_persist_and_verify_write_completion_sentinel(tmp_path: Path) -> None:
    parent = tmp_path / "parent"
    child = tmp_path / "child"
    parent.mkdir()
    child.mkdir()
    snapshot_path = child / "snapshot.json"
    input_path = parent / "partition-input.txt"
    deps_path = parent / "partition-deps.tsv"
    proposal_path = child / "proposal.json"
    issue_input_path = child / "issue-input.txt"
    deps_output_path = child / "prepared-deps.tsv"
    sentinel_path = parent / "umbrella-complete.sentinel"
    _ = snapshot_path.write_text(json.dumps(asdict(_snapshot())) + "\n", encoding="utf-8")
    _ = input_path.write_text("### One\n\nFirst.\n\n### Two\n\nSecond.\n", encoding="utf-8")
    _ = deps_path.write_text("", encoding="utf-8")
    proposal = umbrella.persist_prepared_proposal(
        snapshot_path=snapshot_path,
        prepared_root=parent,
        input_path=input_path,
        deps_path=deps_path,
        completion_sentinel_path=sentinel_path,
        output_root=child,
        proposal_path=proposal_path,
        issue_input_path=issue_input_path,
        deps_output_path=deps_output_path,
    )
    assert deps_output_path.read_text(encoding="utf-8") == deps_path.read_text(encoding="utf-8")
    resolved_leaves = tuple(
        replace(leaf, state="resolved", number=str(index), url=f"https://github.com/owner/repo/issues/{index}")
        for index, leaf in enumerate(proposal.leaves, start=21)
    )
    umbrella.persist_proposal(path=proposal_path, proposal=replace(proposal, leaves=resolved_leaves))
    leaves_path = child / "leaves.json"
    _ = leaves_path.write_text(
        json.dumps([{"number": int(leaf.number), "title": leaf.title, "body": leaf.body} for leaf in resolved_leaves]) + "\n",
        encoding="utf-8",
    )
    assert umbrella.verify_main(
        [
            "--proposal",
            str(proposal_path),
            "--leaves",
            str(leaves_path),
            "--sentinel-file",
            str(sentinel_path),
            "--sentinel-root",
            str(parent),
            "--prepared-input",
            str(input_path),
            "--prepared-deps",
            str(deps_path),
        ]
    ) == 0
    sentinel_rows = dict(
        line.split("=", 1)
        for line in sentinel_path.read_text(encoding="utf-8").splitlines()
    )
    assert sentinel_rows == {
        "UMBRELLA_SENTINEL_VERSION": "2",
        "REPOSITORY": "owner/repo",
        "UMBRELLA_NUMBER": "12",
        "PREPARED_INPUT_SHA256": proposal.prepared_input_sha256,
        "PREPARED_DEPS_SHA256": proposal.prepared_deps_sha256,
        "PREPARED_GRAPH_SHA256": sentinel_rows["PREPARED_GRAPH_SHA256"],
        "GRAPH_VERIFIED": "true",
    }
    assert len(sentinel_rows["PREPARED_GRAPH_SHA256"]) == 64
    _ = int(sentinel_rows["PREPARED_GRAPH_SHA256"], 16)
    with pytest.raises(umbrella.UmbrellaError, match="stale-completion-sentinel"):
        _ = umbrella.persist_prepared_proposal(
            snapshot_path=snapshot_path,
            prepared_root=parent,
            input_path=input_path,
            deps_path=deps_path,
            completion_sentinel_path=sentinel_path,
            output_root=child,
            proposal_path=proposal_path,
            issue_input_path=issue_input_path,
            deps_output_path=deps_output_path,
        )
    completion_args = [
        "--sentinel-file",
        str(sentinel_path),
        "--sentinel-root",
        str(parent),
        "--prepared-input",
        str(input_path),
        "--prepared-deps",
        str(deps_path),
        "--repo",
        "owner/repo",
        "--issue",
        "12",
    ]
    assert umbrella.verify_completion_main(completion_args) == 0
    _ = input_path.write_text("### Changed\n\nFirst.\n\n### Two\n\nSecond.\n", encoding="utf-8")
    assert umbrella.verify_completion_main(completion_args) == 2
    _ = input_path.write_text("### One\n\nFirst.\n\n### Two\n\nSecond.\n", encoding="utf-8")

    sentinel_path.unlink()
    _ = deps_path.write_text("1\t2\n", encoding="utf-8")
    assert umbrella.verify_main(
        [
            "--proposal",
            str(proposal_path),
            "--leaves",
            str(leaves_path),
            "--sentinel-file",
            str(sentinel_path),
            "--sentinel-root",
            str(parent),
            "--prepared-input",
            str(input_path),
            "--prepared-deps",
            str(deps_path),
        ]
    ) == 2
    assert not sentinel_path.exists()
    _ = deps_path.write_text("", encoding="utf-8")
    _ = leaves_path.write_text(json.dumps([{"number": 21, "title": "tampered", "body": resolved_leaves[0].body}]) + "\n", encoding="utf-8")
    assert umbrella.verify_main(
        [
            "--proposal",
            str(proposal_path),
            "--leaves",
            str(leaves_path),
            "--sentinel-file",
            str(sentinel_path),
            "--sentinel-root",
            str(parent),
            "--prepared-input",
            str(input_path),
            "--prepared-deps",
            str(deps_path),
        ]
    ) == 2
    assert not sentinel_path.exists()


def test_prepared_persist_rejects_unmanaged_snapshot(tmp_path: Path) -> None:
    parent = tmp_path / "parent"
    child = tmp_path / "child"
    parent.mkdir()
    child.mkdir()
    snapshot_path = child / "snapshot.json"
    _ = snapshot_path.write_text(json.dumps(asdict(replace(_snapshot(), title="Regular issue"))) + "\n", encoding="utf-8")
    input_path = parent / "partition-input.txt"
    deps_path = parent / "partition-deps.tsv"
    _ = input_path.write_text("### One\n\nFirst.\n\n### Two\n\nSecond.\n", encoding="utf-8")
    _ = deps_path.write_text("", encoding="utf-8")
    with pytest.raises(umbrella.UmbrellaError, match="invalid-snapshot"):
        _ = umbrella.persist_prepared_proposal(
            snapshot_path=snapshot_path,
            prepared_root=parent,
            input_path=input_path,
            deps_path=deps_path,
            completion_sentinel_path=parent / "umbrella-complete.sentinel",
            output_root=child,
            proposal_path=child / "proposal.json",
            issue_input_path=child / "issue-input.txt",
            deps_output_path=child / "prepared-deps.tsv",
        )


def test_persist_proposal_cli_rejects_duplicate_flags(tmp_path: Path) -> None:
    assert umbrella.persist_proposal_main(
        [
            "--proposal",
            str(tmp_path / "first.json"),
            "--proposal",
            str(tmp_path / "second.json"),
            "--output",
            str(tmp_path / "output.json"),
        ]
    ) == 2
