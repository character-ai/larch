"""Fail-closed state helpers for the public ``/umbrella`` orchestrator.

The skill owns decomposition and child-skill invocation.  This module owns the
durable issue record and every machine-consumed comparison so a resumed run
cannot select an unrelated issue or silently recreate an in-flight leaf.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Final, cast

from larch import io as larch_io
from larch.core import logging_util, proc
from larch.errors import ShipError
from larch.git import gh
from larch.issue import issue_mutation

PROPOSAL_MARKER: Final = "larch:umbrella-proposal"
UMBRELLA_PREFIX: Final = "[UMBRELLA]"
LEAF_OPENING_TEMPLATE: Final = "This is a leaf of umbrella #{umbrella}. Read the umbrella in full before acting."
MAX_LEAVES: Final = 30


class UmbrellaError(ShipError):
    """A stable, safe reason token for a refused umbrella operation."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class UmbrellaSnapshot:
    repository: str
    number: str
    title: str
    body: str
    state: str
    updated_at: str


@dataclass(frozen=True)
class ExpectedDependencyEdge:
    blocker: str
    blocked: str


@dataclass(frozen=True)
class ExpectedLeaf:
    identity: str
    title: str
    body: str
    state: str = "pending"
    number: str = ""
    url: str = ""
    issue_id: str = ""


@dataclass(frozen=True)
class InFlightLeaf:
    identity: str
    title: str
    body: str


@dataclass(frozen=True)
class ResolvedLeaf:
    identity: str
    number: str
    url: str
    issue_id: str = ""


@dataclass(frozen=True)
class ProposalRecord:
    umbrella: str
    repository: str
    expected_updated_at: str
    common_context: str
    leaves: tuple[ExpectedLeaf, ...]
    dependency_edges: tuple[ExpectedDependencyEdge, ...] = ()
    version: int = 1


def leaf_opening(*, umbrella: str) -> str:
    return LEAF_OPENING_TEMPLATE.format(umbrella=umbrella)


def leaf_identity(*, title: str, body: str) -> str:
    """Return a stable identity that excludes run-local paths and timestamps."""
    content = f"{title.strip()}\n{body}".encode()
    return hashlib.sha256(content).hexdigest()


def _require_positive(value: str, name: str) -> None:
    if not value.isdecimal() or value == "0":
        raise UmbrellaError(f"invalid-{name}")


def _load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise UmbrellaError("invalid-proposal-record") from exc


def _string(value: object, reason: str) -> str:
    if not isinstance(value, str):
        raise UmbrellaError(reason)
    return value


def _expected_leaf(value: object) -> ExpectedLeaf:
    if not isinstance(value, dict):
        raise UmbrellaError("invalid-proposal-record")
    row = cast("dict[str, object]", value)
    identity = _string(row.get("identity"), "invalid-proposal-record")
    title = _string(row.get("title"), "invalid-proposal-record")
    body = _string(row.get("body"), "invalid-proposal-record")
    state = _string(row.get("state", "pending"), "invalid-proposal-record")
    number = _string(row.get("number", ""), "invalid-proposal-record")
    url = _string(row.get("url", ""), "invalid-proposal-record")
    issue_id = _string(row.get("issue_id", ""), "invalid-proposal-record")
    if state not in {"pending", "in-flight", "resolved"} or leaf_identity(title=title, body=body) != identity:
        raise UmbrellaError("invalid-proposal-record")
    if state == "resolved" and (not number.isdecimal() or not url):
        raise UmbrellaError("invalid-proposal-record")
    return ExpectedLeaf(identity, title, body, state, number, url, issue_id)


def load_proposal(path: Path) -> ProposalRecord:
    value = _load_json(path)
    if not isinstance(value, dict):
        raise UmbrellaError("invalid-proposal-record")
    row = cast("dict[str, object]", value)
    umbrella = _string(row.get("umbrella"), "invalid-proposal-record")
    repository = _string(row.get("repository"), "invalid-proposal-record")
    updated = _string(row.get("expected_updated_at"), "invalid-proposal-record")
    context = _string(row.get("common_context"), "invalid-proposal-record")
    leaves_value = row.get("leaves")
    if not isinstance(leaves_value, list) or not 0 < len(leaves_value) <= MAX_LEAVES:
        raise UmbrellaError("invalid-proposal-record")
    leaves = tuple(_expected_leaf(item) for item in cast("list[object]", leaves_value))
    if len({leaf.identity for leaf in leaves}) != len(leaves):
        raise UmbrellaError("invalid-proposal-record")
    edges_value = row.get("dependency_edges", [])
    if not isinstance(edges_value, list):
        raise UmbrellaError("invalid-proposal-record")
    edges: list[ExpectedDependencyEdge] = []
    for item in cast("list[object]", edges_value):
        if not isinstance(item, dict):
            raise UmbrellaError("invalid-proposal-record")
        edge = cast("dict[str, object]", item)
        blocker = _string(edge.get("blocker"), "invalid-proposal-record")
        blocked = _string(edge.get("blocked"), "invalid-proposal-record")
        if blocker == blocked:
            raise UmbrellaError("invalid-proposal-record")
        edges.append(ExpectedDependencyEdge(blocker, blocked))
    _require_positive(umbrella, "umbrella")
    if not gh.validate_repo_slug(repository):
        raise UmbrellaError("invalid-proposal-record")
    return ProposalRecord(umbrella, repository, updated, context, leaves, tuple(edges))


def persist_proposal(*, path: Path, proposal: ProposalRecord) -> None:
    """Atomically persist a bounded proposal before any leaf filing begins."""
    if len(proposal.leaves) > MAX_LEAVES:
        raise UmbrellaError("leaf-cap-exceeded")
    serialized = json.dumps(asdict(proposal), sort_keys=True, separators=(",", ":")) + "\n"
    larch_io.atomic_write(path=path, text=serialized, prefix=f".{path.name}.", nofollow=True, mode=0o600)


def prepare_snapshot(*, repository: str, issue: str) -> UmbrellaSnapshot:
    snapshot = issue_mutation.read_snapshot(proc, repository=repository, issue=issue)
    if snapshot.state.upper() != "OPEN":
        raise UmbrellaError("closed-input")
    if snapshot.title.startswith("[PR]") or "<!-- larch:plan" in snapshot.body:
        raise UmbrellaError("incompatible-input")
    if snapshot.title.startswith(UMBRELLA_PREFIX) and PROPOSAL_MARKER not in snapshot.body:
        raise UmbrellaError("incompatible-umbrella")
    return UmbrellaSnapshot(repository, issue, snapshot.title, snapshot.body, snapshot.state, snapshot.updated_at)


def _leaf_contract(*, leaf: ExpectedLeaf, umbrella: str) -> bool:
    return leaf.title.startswith(f"[LEAF OF {umbrella}]") and leaf.body.startswith(leaf_opening(umbrella=umbrella))


def mark_in_flight(*, proposal_path: Path, identity: str) -> ProposalRecord:
    proposal = load_proposal(proposal_path)
    found = False
    leaves: list[ExpectedLeaf] = []
    for leaf in proposal.leaves:
        if leaf.identity == identity:
            if leaf.state == "resolved":
                raise UmbrellaError("leaf-already-resolved")
            leaves.append(replace(leaf, state="in-flight"))
            found = True
        else:
            leaves.append(leaf)
    if not found:
        raise UmbrellaError("unknown-leaf-identity")
    updated = replace(proposal, leaves=tuple(leaves))
    persist_proposal(path=proposal_path, proposal=updated)
    return updated


def record_resolved(*, proposal_path: Path, identity: str, number: str, url: str, issue_id: str = "") -> ProposalRecord:
    _require_positive(number, "leaf")
    if not url:
        raise UmbrellaError("invalid-resolved-leaf")
    proposal = load_proposal(proposal_path)
    leaves: list[ExpectedLeaf] = []
    found = False
    for leaf in proposal.leaves:
        if leaf.identity == identity:
            leaves.append(replace(leaf, state="resolved", number=number, url=url, issue_id=issue_id))
            found = True
        else:
            leaves.append(leaf)
    if not found:
        raise UmbrellaError("unknown-leaf-identity")
    updated = replace(proposal, leaves=tuple(leaves))
    persist_proposal(path=proposal_path, proposal=updated)
    return updated


def reconcile_in_flight(*, proposal: ProposalRecord, identity: str, candidates: list[dict[str, object]]) -> ResolvedLeaf:
    """Resolve exactly one remote issue matching the immutable in-flight contract."""
    leaf = next((item for item in proposal.leaves if item.identity == identity), None)
    if leaf is None or leaf.state != "in-flight" or not _leaf_contract(leaf=leaf, umbrella=proposal.umbrella):
        raise UmbrellaError("ambiguous-in-flight-recovery")
    matches: list[ResolvedLeaf] = []
    for row in candidates:
        title = row.get("title")
        body = row.get("body")
        number = row.get("number")
        url = row.get("url")
        issue_id = row.get("id", "")
        if title == leaf.title and body == leaf.body and isinstance(number, int) and isinstance(url, str) and url:
            matches.append(ResolvedLeaf(identity, str(number), url, str(issue_id)))
    if len(matches) != 1:
        raise UmbrellaError("ambiguous-in-flight-recovery")
    return matches[0]


def finalize(*, repository: str, issue: str, title: str, body: str) -> None:
    if not title.startswith(UMBRELLA_PREFIX) or PROPOSAL_MARKER not in body:
        raise UmbrellaError("invalid-final-umbrella")
    snapshot = issue_mutation.read_snapshot(proc, repository=repository, issue=issue)
    issue_mutation.apply(
        proc,
        issue_mutation.request_for_snapshot(
            snapshot,
            fields=frozenset({issue_mutation.MutationField.TITLE, issue_mutation.MutationField.BODY}),
            title=title,
            body=body,
        ),
    )


def _emit_error(reason: str) -> int:
    logging_util.emit_kv(key="UMBRELLA_FAILED", value="true")
    logging_util.emit_kv(key="REASON", value=reason)
    return 2


def prepare_main(argv: list[str]) -> int:
    values = _parse_values(argv, {"--repo", "--issue", "--output"})
    if values is None or not {"--repo", "--issue", "--output"} <= values.keys():
        return _emit_error("usage")
    try:
        snapshot = prepare_snapshot(repository=values["--repo"], issue=values["--issue"])
        larch_io.atomic_write(path=Path(values["--output"]), text=json.dumps(asdict(snapshot), sort_keys=True) + "\n", prefix=".umbrella-snapshot.", nofollow=True, mode=0o600)
    except (UmbrellaError, ShipError) as exc:
        return _emit_error(getattr(exc, "reason", "snapshot-failed"))
    logging_util.emit_kv(key="UMBRELLA_READY", value="true")
    logging_util.emit_kv(key="UPDATED_AT", value=snapshot.updated_at)
    return 0


def persist_proposal_main(argv: list[str]) -> int:
    values = _parse_values(argv, {"--proposal", "--output"})
    if values is None or not {"--proposal", "--output"} <= values.keys():
        return _emit_error("usage")
    try:
        persist_proposal(path=Path(values["--output"]), proposal=load_proposal(Path(values["--proposal"])))
    except UmbrellaError as exc:
        return _emit_error(exc.reason)
    logging_util.emit_kv(key="PROPOSAL_PERSISTED", value="true")
    return 0


def mark_in_flight_main(argv: list[str]) -> int:
    values = _parse_values(argv, {"--proposal", "--identity"})
    if values is None or not {"--proposal", "--identity"} <= values.keys():
        return _emit_error("usage")
    try:
        mark_in_flight(proposal_path=Path(values["--proposal"]), identity=values["--identity"])
    except UmbrellaError as exc:
        return _emit_error(exc.reason)
    logging_util.emit_kv(key="IN_FLIGHT_PERSISTED", value="true")
    return 0


def record_resolved_main(argv: list[str]) -> int:
    values = _parse_values(argv, {"--proposal", "--identity", "--number", "--url", "--issue-id"})
    if values is None or not {"--proposal", "--identity", "--number", "--url"} <= values.keys():
        return _emit_error("usage")
    try:
        record_resolved(proposal_path=Path(values["--proposal"]), identity=values["--identity"], number=values["--number"], url=values["--url"], issue_id=values.get("--issue-id", ""))
    except UmbrellaError as exc:
        return _emit_error(exc.reason)
    logging_util.emit_kv(key="RESOLVED_PERSISTED", value="true")
    return 0


def reconcile_in_flight_main(argv: list[str]) -> int:
    values = _parse_values(argv, {"--proposal", "--identity", "--candidates"})
    if values is None or not {"--proposal", "--identity", "--candidates"} <= values.keys():
        return _emit_error("usage")
    try:
        candidate_value = _load_json(Path(values["--candidates"]))
        if not isinstance(candidate_value, list) or not all(isinstance(item, dict) for item in candidate_value):
            raise UmbrellaError("ambiguous-in-flight-recovery")
        result = reconcile_in_flight(proposal=load_proposal(Path(values["--proposal"])), identity=values["--identity"], candidates=cast("list[dict[str, object]]", candidate_value))
        record_resolved(proposal_path=Path(values["--proposal"]), identity=result.identity, number=result.number, url=result.url, issue_id=result.issue_id)
    except UmbrellaError as exc:
        return _emit_error(exc.reason)
    logging_util.emit_kv(key="RECONCILED", value="true")
    logging_util.emit_kv(key="ISSUE_NUMBER", value=result.number)
    logging_util.emit_kv(key="ISSUE_URL", value=result.url)
    return 0


def mutate_main(argv: list[str]) -> int:
    values = _parse_values(argv, {"--repo", "--issue", "--title", "--body-file"})
    if values is None or not {"--repo", "--issue", "--title", "--body-file"} <= values.keys():
        return _emit_error("usage")
    try:
        finalize(
            repository=values["--repo"],
            issue=values["--issue"],
            title=values["--title"],
            body=Path(values["--body-file"]).read_text(encoding="utf-8"),
        )
    except (OSError, UmbrellaError, ShipError) as exc:
        return _emit_error(getattr(exc, "reason", "mutation-failed"))
    logging_util.emit_kv(key="UMBRELLA_MUTATED", value="true")
    return 0


def verify_main(argv: list[str]) -> int:
    values = _parse_values(argv, {"--proposal", "--leaves"})
    if values is None or not {"--proposal", "--leaves"} <= values.keys():
        return _emit_error("usage")
    try:
        proposal = load_proposal(Path(values["--proposal"]))
        rows_value = _load_json(Path(values["--leaves"]))
        if not isinstance(rows_value, list) or not all(isinstance(item, dict) for item in rows_value):
            raise UmbrellaError("incomplete-graph-state")
        actual = cast("list[dict[str, object]]", rows_value)
        for leaf in proposal.leaves:
            if leaf.state != "resolved" or not _leaf_contract(leaf=leaf, umbrella=proposal.umbrella):
                raise UmbrellaError("incomplete-graph-state")
            matching = [row for row in actual if str(row.get("number") or "") == leaf.number]
            if len(matching) != 1 or matching[0].get("title") != leaf.title or matching[0].get("body") != leaf.body:
                raise UmbrellaError("incomplete-graph-state")
    except UmbrellaError as exc:
        return _emit_error(exc.reason)
    logging_util.emit_kv(key="GRAPH_VERIFIED", value="true")
    return 0


def _parse_values(argv: list[str], permitted: set[str]) -> dict[str, str] | None:
    values: dict[str, str] = {}
    index = 0
    while index < len(argv):
        if argv[index] not in permitted or index + 1 >= len(argv):
            return None
        values[argv[index]] = argv[index + 1]
        index += 2
    return values
