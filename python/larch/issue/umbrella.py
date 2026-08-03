"""Fail-closed state helpers for the public ``/umbrella`` orchestrator.

The skill owns decomposition and child-skill invocation.  This module owns the
durable issue record and every machine-consumed comparison so a resumed run
cannot select an unrelated issue or silently recreate an in-flight leaf.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, replace
from graphlib import CycleError, TopologicalSorter
from pathlib import Path
from typing import Final, cast

from larch import io as larch_io
from larch.core import config, logging_util, proc
from larch.errors import ShipError
from larch.git import gh
from larch.issue import issue_create, issue_mutation

PROPOSAL_MARKER: Final = "larch:umbrella-proposal"
UMBRELLA_PREFIX: Final = "[UMBRELLA]"
LEAF_OPENING_TEMPLATE: Final = "This is a leaf of umbrella #{umbrella}. Read the umbrella in full before acting."
MAX_LEAVES: Final = 30
MIN_PREPARED_LEAVES: Final = 2
MAX_PREPARED_INPUT_BYTES: Final = 262_144
MAX_PREPARED_DEPS_BYTES: Final = 16_384
PREPARED_DEP_FIELD_COUNT: Final = 2
COMPLETION_SENTINEL_VERSION: Final = "2"
SHA256_HEX_LENGTH: Final = 64
MANAGED_PARTITION_PREFIXES: Final = (
    config.TRACKING_ISSUE_PREFIX_BY_STATE["designing"],
    config.TRACKING_ISSUE_PREFIX_BY_STATE["implementing"],
)


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
    prepared_input_sha256: str = ""
    prepared_deps_sha256: str = ""
    version: int = 1


def leaf_opening(*, umbrella: str) -> str:
    return LEAF_OPENING_TEMPLATE.format(umbrella=umbrella)


def leaf_identity(*, title: str, body: str) -> str:
    """Return a stable identity that excludes run-local paths and timestamps."""
    content = f"{title.strip()}\n{body}".encode()
    return hashlib.sha256(content).hexdigest()


def _text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _valid_sha256(value: str) -> bool:
    return len(value) == SHA256_HEX_LENGTH and value.isascii() and all(char in "0123456789abcdef" for char in value)


def _require_positive(value: str, name: str) -> None:
    if not value.isdecimal() or value == "0":
        raise UmbrellaError(f"invalid-{name}")


def _managed_partition_title(title: str) -> bool:
    return title.startswith(MANAGED_PARTITION_PREFIXES)


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
    if not isinstance(leaves_value, list) or not 0 < len(cast("list[object]", leaves_value)) <= MAX_LEAVES:
        raise UmbrellaError("invalid-proposal-record")
    leaves = tuple(_expected_leaf(item) for item in cast("list[object]", leaves_value))
    if len({leaf.identity for leaf in leaves}) != len(leaves):
        raise UmbrellaError("invalid-proposal-record")
    leaf_identities = {leaf.identity for leaf in leaves}
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
        if blocker == blocked or blocker not in leaf_identities or blocked not in leaf_identities:
            raise UmbrellaError("invalid-proposal-record")
        edges.append(ExpectedDependencyEdge(blocker, blocked))
    _validate_dependency_graph(leaves=leaves, edges=tuple(edges), reason="invalid-proposal-record")
    prepared_input_sha256 = _string(row.get("prepared_input_sha256", ""), "invalid-proposal-record")
    prepared_deps_sha256 = _string(row.get("prepared_deps_sha256", ""), "invalid-proposal-record")
    if bool(prepared_input_sha256) != bool(prepared_deps_sha256) or (
        prepared_input_sha256
        and (not _valid_sha256(prepared_input_sha256) or not _valid_sha256(prepared_deps_sha256))
    ):
        raise UmbrellaError("invalid-proposal-record")
    _require_positive(umbrella, "umbrella")
    if not gh.validate_repo_slug(repository):
        raise UmbrellaError("invalid-proposal-record")
    return ProposalRecord(
        umbrella,
        repository,
        updated,
        context,
        leaves,
        tuple(edges),
        prepared_input_sha256,
        prepared_deps_sha256,
    )


def _validate_dependency_graph(*, leaves: tuple[ExpectedLeaf, ...], edges: tuple[ExpectedDependencyEdge, ...], reason: str) -> None:
    identities = {leaf.identity for leaf in leaves}
    if len(set(edges)) != len(edges) or any(edge.blocker not in identities or edge.blocked not in identities or edge.blocker == edge.blocked for edge in edges):
        raise UmbrellaError(reason)
    predecessors: dict[str, set[str]] = {identity: set() for identity in identities}
    for edge in edges:
        predecessors[edge.blocked].add(edge.blocker)
    try:
        _ = tuple(TopologicalSorter(predecessors).static_order())
    except CycleError as exc:
        raise UmbrellaError(reason) from exc


def _proposal_text(proposal: ProposalRecord) -> str:
    return json.dumps(asdict(proposal), sort_keys=True, separators=(",", ":")) + "\n"


def _prepared_graph_sha256(proposal: ProposalRecord) -> str:
    shape = {
        "leaves": [
            {"identity": leaf.identity, "title": leaf.title, "body": leaf.body}
            for leaf in proposal.leaves
        ],
        "dependency_edges": [asdict(edge) for edge in proposal.dependency_edges],
    }
    return _text_sha256(json.dumps(shape, sort_keys=True, separators=(",", ":")))


def _immutable_proposal_shape(proposal: ProposalRecord) -> tuple[tuple[tuple[str, str, str], ...], tuple[ExpectedDependencyEdge, ...]]:
    leaves = tuple((leaf.identity, leaf.title, leaf.body) for leaf in proposal.leaves)
    return leaves, proposal.dependency_edges


def persist_proposal(*, path: Path, proposal: ProposalRecord) -> None:
    """Atomically persist a bounded proposal before any leaf filing begins."""
    if len(proposal.leaves) > MAX_LEAVES:
        raise UmbrellaError("leaf-cap-exceeded")
    larch_io.atomic_write(path=path, text=_proposal_text(proposal), prefix=f".{path.name}.", nofollow=True, mode=0o600)


def _prepared_edges(*, deps_text: str, leaves: tuple[ExpectedLeaf, ...]) -> tuple[ExpectedDependencyEdge, ...]:
    if "\r" in deps_text:
        raise UmbrellaError("invalid-prepared-dependencies")
    edges: list[ExpectedDependencyEdge] = []
    seen: set[tuple[int, int]] = set()
    for raw_line in deps_text.splitlines():
        if not raw_line:
            raise UmbrellaError("invalid-prepared-dependencies")
        parts = raw_line.split("\t")
        if len(parts) != PREPARED_DEP_FIELD_COUNT or not all(part.isascii() and part.isdecimal() for part in parts):
            raise UmbrellaError("invalid-prepared-dependencies")
        blocker_index, blocked_index = (int(part) for part in parts)
        if blocker_index < 1 or blocked_index < 1 or blocker_index > len(leaves) or blocked_index > len(leaves) or blocker_index == blocked_index:
            raise UmbrellaError("invalid-prepared-dependencies")
        index_edge = (blocker_index, blocked_index)
        if index_edge in seen:
            raise UmbrellaError("invalid-prepared-dependencies")
        seen.add(index_edge)
        edges.append(ExpectedDependencyEdge(blocker=leaves[blocker_index - 1].identity, blocked=leaves[blocked_index - 1].identity))
    result = tuple(edges)
    _validate_dependency_graph(leaves=leaves, edges=result, reason="prepared-dependency-cycle")
    return result


def prepare_proposal_from_batch(*, snapshot: UmbrellaSnapshot, input_text: str, deps_text: str) -> tuple[ProposalRecord, str]:
    """Convert a validated parent partition into exact umbrella leaf records."""
    if len(input_text.encode()) > MAX_PREPARED_INPUT_BYTES or len(deps_text.encode()) > MAX_PREPARED_DEPS_BYTES:
        raise UmbrellaError("prepared-partition-too-large")
    items, mode = issue_create.parse_issue_input(input_text)
    if mode != "generic" or not MIN_PREPARED_LEAVES <= len(items) <= MAX_LEAVES or any(item.malformed or not item.title.strip() or not item.body.strip() or item.title.lstrip().casefold().startswith("[leaf of ") for item in items):
        raise UmbrellaError("invalid-prepared-partition")
    leaves: list[ExpectedLeaf] = []
    batch_parts: list[str] = []
    opening = leaf_opening(umbrella=snapshot.number)
    for item in items:
        base_title = item.title.strip()
        leaf_title = f"[LEAF OF {snapshot.number}] {base_title}"
        leaf_body = f"{opening}\n\n{item.body.strip()}"
        leaves.append(ExpectedLeaf(identity=leaf_identity(title=leaf_title, body=leaf_body), title=leaf_title, body=leaf_body))
        batch_parts.append(f"### {base_title}\n\n{leaf_body}")
    frozen_leaves = tuple(leaves)
    if len({leaf.identity for leaf in frozen_leaves}) != len(frozen_leaves):
        raise UmbrellaError("invalid-prepared-partition")
    proposal = ProposalRecord(
        umbrella=snapshot.number,
        repository=snapshot.repository,
        expected_updated_at=snapshot.updated_at,
        common_context=snapshot.body,
        leaves=frozen_leaves,
        dependency_edges=_prepared_edges(deps_text=deps_text, leaves=frozen_leaves),
        prepared_input_sha256=_text_sha256(input_text),
        prepared_deps_sha256=_text_sha256(deps_text),
    )
    issue_input = "\n".join(batch_parts) + "\n"
    round_trip_items, round_trip_mode = issue_create.parse_issue_input(issue_input)
    if round_trip_mode != "generic" or len(round_trip_items) != len(frozen_leaves) or any(
        item.title.strip() != leaf.title.removeprefix(f"[LEAF OF {snapshot.number}] ") or item.body != leaf.body
        for item, leaf in zip(round_trip_items, frozen_leaves, strict=True)
    ):
        raise UmbrellaError("invalid-prepared-partition")
    return proposal, issue_input


def persist_prepared_proposal(  # noqa: PLR0913 - prepared handoff keeps both trusted roots and every input/output path explicit.
    *, snapshot_path: Path, prepared_root: Path, input_path: Path, deps_path: Path, completion_sentinel_path: Path, output_root: Path, proposal_path: Path, issue_input_path: Path, deps_output_path: Path
) -> ProposalRecord:
    try:
        all_paths = (
            snapshot_path,
            prepared_root,
            input_path,
            deps_path,
            completion_sentinel_path,
            output_root,
            proposal_path,
            issue_input_path,
            deps_output_path,
        )
        if not all(path.is_absolute() for path in all_paths):
            raise UmbrellaError("invalid-prepared-path")
        _ = larch_io.validate_trusted_directory(completion_sentinel_path.parent, root=prepared_root)
        if larch_io.trusted_file_present(completion_sentinel_path, root=prepared_root):
            raise UmbrellaError("stale-completion-sentinel")
        snapshot_value = json.loads(larch_io.read_trusted_text(snapshot_path, root=output_root))
        if not isinstance(snapshot_value, dict):
            raise TypeError("snapshot is not an object")
        row = cast("dict[str, object]", snapshot_value)
        snapshot = UmbrellaSnapshot(
            repository=_string(row.get("repository"), "invalid-snapshot"),
            number=_string(row.get("number"), "invalid-snapshot"),
            title=_string(row.get("title"), "invalid-snapshot"),
            body=_string(row.get("body"), "invalid-snapshot"),
            state=_string(row.get("state"), "invalid-snapshot"),
            updated_at=_string(row.get("updated_at"), "invalid-snapshot"),
        )
        _require_positive(snapshot.number, "umbrella")
        if not gh.validate_repo_slug(snapshot.repository) or snapshot.state.upper() != "OPEN" or not snapshot.updated_at or not _managed_partition_title(snapshot.title):
            raise UmbrellaError("invalid-snapshot")
        input_text = larch_io.read_trusted_text(input_path, root=prepared_root)
        deps_text = larch_io.read_trusted_text(deps_path, root=prepared_root)
        proposal, issue_input = prepare_proposal_from_batch(snapshot=snapshot, input_text=input_text, deps_text=deps_text)
        larch_io.trusted_atomic_write(proposal_path, _proposal_text(proposal), root=output_root)
        larch_io.trusted_atomic_write(issue_input_path, issue_input, root=output_root)
        larch_io.trusted_atomic_write(deps_output_path, deps_text, root=output_root)
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise UmbrellaError("invalid-prepared-partition") from exc
    return proposal


def prepare_snapshot(*, repository: str, issue: str, managed_partition: bool = False) -> UmbrellaSnapshot:
    snapshot = issue_mutation.read_snapshot(proc, repository=repository, issue=issue)
    if snapshot.state.upper() != "OPEN":
        raise UmbrellaError("closed-input")
    managed_title = _managed_partition_title(snapshot.title)
    compatible_umbrella = snapshot.title.startswith(UMBRELLA_PREFIX) and PROPOSAL_MARKER in snapshot.body
    if managed_partition and not managed_title and not compatible_umbrella:
        raise UmbrellaError("incompatible-managed-partition")
    if snapshot.title.startswith("[PR]") or ("<!-- larch:plan" in snapshot.body and not managed_partition and not compatible_umbrella):
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


def finalize(*, repository: str, issue: str, title: str, body: str, managed_partition: bool = False) -> None:
    if not title.startswith(UMBRELLA_PREFIX) or PROPOSAL_MARKER not in body:
        raise UmbrellaError("invalid-final-umbrella")
    if managed_partition:
        _ = issue_mutation.convert_managed_issue_to_umbrella(proc, repository=repository, issue=issue, title=title, body=body)
        return
    snapshot = issue_mutation.read_snapshot(proc, repository=repository, issue=issue)
    _ = issue_mutation.apply(
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
    values = _parse_values(argv, {"--repo", "--issue", "--output", "--managed-partition"})
    if values is None or not {"--repo", "--issue", "--output"} <= values.keys():
        return _emit_error("usage")
    managed_partition = values.get("--managed-partition", "false")
    if managed_partition not in {"true", "false"}:
        return _emit_error("usage")
    try:
        snapshot = prepare_snapshot(repository=values["--repo"], issue=values["--issue"], managed_partition=managed_partition == "true")
        larch_io.atomic_write(path=Path(values["--output"]), text=json.dumps(asdict(snapshot), sort_keys=True) + "\n", prefix=".umbrella-snapshot.", nofollow=True, mode=0o600)
    except (UmbrellaError, ShipError) as exc:
        return _emit_error(getattr(exc, "reason", "snapshot-failed"))
    logging_util.emit_kv(key="UMBRELLA_READY", value="true")
    logging_util.emit_kv(key="UPDATED_AT", value=snapshot.updated_at)
    return 0


def persist_proposal_main(argv: list[str]) -> int:
    values = _parse_values(argv, {"--proposal", "--snapshot", "--prepared-root", "--prepared-input", "--prepared-deps", "--completion-sentinel", "--output-root", "--output", "--issue-input-output", "--deps-output"})
    if values is None:
        return _emit_error("usage")
    prepared_mode = "--proposal" not in values
    try:
        if "--proposal" in values:
            if set(values) != {"--proposal", "--output"}:
                return _emit_error("usage")
            proposal = load_proposal(Path(values["--proposal"]))
            persist_proposal(path=Path(values["--output"]), proposal=proposal)
        else:
            required = {"--snapshot", "--prepared-root", "--prepared-input", "--prepared-deps", "--completion-sentinel", "--output-root", "--output", "--issue-input-output", "--deps-output"}
            if set(values) != required:
                return _emit_error("usage")
            proposal = persist_prepared_proposal(
                snapshot_path=Path(values["--snapshot"]),
                prepared_root=Path(values["--prepared-root"]),
                input_path=Path(values["--prepared-input"]),
                deps_path=Path(values["--prepared-deps"]),
                completion_sentinel_path=Path(values["--completion-sentinel"]),
                output_root=Path(values["--output-root"]),
                proposal_path=Path(values["--output"]),
                issue_input_path=Path(values["--issue-input-output"]),
                deps_output_path=Path(values["--deps-output"]),
            )
    except (OSError, UmbrellaError) as exc:
        return _emit_error(getattr(exc, "reason", "proposal-write-failed"))
    logging_util.emit_kv(key="PROPOSAL_PERSISTED", value="true")
    if prepared_mode:
        logging_util.emit_kv(key="LEAF_COUNT", value=len(proposal.leaves))
    return 0


def mark_in_flight_main(argv: list[str]) -> int:
    values = _parse_values(argv, {"--proposal", "--identity"})
    if values is None or not {"--proposal", "--identity"} <= values.keys():
        return _emit_error("usage")
    try:
        _ = mark_in_flight(proposal_path=Path(values["--proposal"]), identity=values["--identity"])
    except UmbrellaError as exc:
        return _emit_error(exc.reason)
    logging_util.emit_kv(key="IN_FLIGHT_PERSISTED", value="true")
    return 0


def record_resolved_main(argv: list[str]) -> int:
    values = _parse_values(argv, {"--proposal", "--identity", "--number", "--url", "--issue-id"})
    if values is None or not {"--proposal", "--identity", "--number", "--url"} <= values.keys():
        return _emit_error("usage")
    try:
        _ = record_resolved(proposal_path=Path(values["--proposal"]), identity=values["--identity"], number=values["--number"], url=values["--url"], issue_id=values.get("--issue-id", ""))
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
        if not isinstance(candidate_value, list) or not all(isinstance(item, dict) for item in cast("list[object]", candidate_value)):
            raise UmbrellaError("ambiguous-in-flight-recovery")
        result = reconcile_in_flight(proposal=load_proposal(Path(values["--proposal"])), identity=values["--identity"], candidates=cast("list[dict[str, object]]", candidate_value))
        _ = record_resolved(proposal_path=Path(values["--proposal"]), identity=result.identity, number=result.number, url=result.url, issue_id=result.issue_id)
    except UmbrellaError as exc:
        return _emit_error(exc.reason)
    logging_util.emit_kv(key="RECONCILED", value="true")
    logging_util.emit_kv(key="ISSUE_NUMBER", value=result.number)
    logging_util.emit_kv(key="ISSUE_URL", value=result.url)
    return 0


def mutate_main(argv: list[str]) -> int:
    values = _parse_values(argv, {"--repo", "--issue", "--title", "--body-file", "--managed-partition"})
    if values is None or not {"--repo", "--issue", "--title", "--body-file"} <= values.keys():
        return _emit_error("usage")
    managed_partition = values.get("--managed-partition", "false")
    if managed_partition not in {"true", "false"}:
        return _emit_error("usage")
    try:
        finalize(
            repository=values["--repo"],
            issue=values["--issue"],
            title=values["--title"],
            body=Path(values["--body-file"]).read_text(encoding="utf-8"),
            managed_partition=managed_partition == "true",
        )
    except (OSError, UmbrellaError, ShipError) as exc:
        return _emit_error(getattr(exc, "reason", "mutation-failed"))
    logging_util.emit_kv(key="UMBRELLA_MUTATED", value="true")
    return 0


def _write_completion_sentinel(
    *, proposal: ProposalRecord, sentinel_file: str, sentinel_root: str, prepared_input: str, prepared_deps: str
) -> None:
    live_input = larch_io.read_trusted_text(prepared_input, root=sentinel_root)
    live_deps = larch_io.read_trusted_text(prepared_deps, root=sentinel_root)
    live_input_sha256 = _text_sha256(live_input)
    live_deps_sha256 = _text_sha256(live_deps)
    expected_proposal, _issue_input = prepare_proposal_from_batch(
        snapshot=UmbrellaSnapshot(
            repository=proposal.repository,
            number=proposal.umbrella,
            title="",
            body=proposal.common_context,
            state="OPEN",
            updated_at=proposal.expected_updated_at,
        ),
        input_text=live_input,
        deps_text=live_deps,
    )
    if (
        not proposal.prepared_input_sha256
        or live_input_sha256 != proposal.prepared_input_sha256
        or live_deps_sha256 != proposal.prepared_deps_sha256
        or _immutable_proposal_shape(proposal) != _immutable_proposal_shape(expected_proposal)
    ):
        raise UmbrellaError("stale-prepared-partition")
    graph_sha256 = _prepared_graph_sha256(expected_proposal)
    larch_io.trusted_atomic_write(
        sentinel_file,
        f"UMBRELLA_SENTINEL_VERSION={COMPLETION_SENTINEL_VERSION}\n"
        f"REPOSITORY={proposal.repository}\n"
        f"UMBRELLA_NUMBER={proposal.umbrella}\n"
        f"PREPARED_INPUT_SHA256={proposal.prepared_input_sha256}\n"
        f"PREPARED_DEPS_SHA256={proposal.prepared_deps_sha256}\n"
        f"PREPARED_GRAPH_SHA256={graph_sha256}\n"
        "GRAPH_VERIFIED=true\n",
        root=sentinel_root,
    )


def _completion_paths(values: dict[str, str]) -> tuple[str, str, str, str] | None:
    flags = ("--sentinel-file", "--sentinel-root", "--prepared-input", "--prepared-deps")
    if not any(flag in values for flag in flags):
        return "", "", "", ""
    if not all(flag in values and values[flag] for flag in flags):
        return None
    return values[flags[0]], values[flags[1]], values[flags[2]], values[flags[3]]


def verify_main(argv: list[str]) -> int:
    values = _parse_values(
        argv,
        {"--proposal", "--leaves", "--sentinel-file", "--sentinel-root", "--prepared-input", "--prepared-deps"},
    )
    if values is None or not {"--proposal", "--leaves"} <= values.keys():
        return _emit_error("usage")
    completion_paths = _completion_paths(values)
    if completion_paths is None:
        return _emit_error("usage")
    sentinel_file, sentinel_root, prepared_input, prepared_deps = completion_paths
    try:
        proposal = load_proposal(Path(values["--proposal"]))
        rows_value = _load_json(Path(values["--leaves"]))
        if not isinstance(rows_value, list) or not all(isinstance(item, dict) for item in cast("list[object]", rows_value)):
            raise UmbrellaError("incomplete-graph-state")
        actual = cast("list[dict[str, object]]", rows_value)
        for leaf in proposal.leaves:
            if leaf.state != "resolved" or not _leaf_contract(leaf=leaf, umbrella=proposal.umbrella):
                raise UmbrellaError("incomplete-graph-state")
            matching = [row for row in actual if str(row.get("number") or "") == leaf.number]
            if len(matching) != 1 or matching[0].get("title") != leaf.title or matching[0].get("body") != leaf.body:
                raise UmbrellaError("incomplete-graph-state")
        if sentinel_file:
            _write_completion_sentinel(
                proposal=proposal,
                sentinel_file=sentinel_file,
                sentinel_root=sentinel_root,
                prepared_input=prepared_input,
                prepared_deps=prepared_deps,
            )
    except OSError:
        return _emit_error("sentinel-write-failed")
    except UmbrellaError as exc:
        return _emit_error(exc.reason)
    logging_util.emit_kv(key="GRAPH_VERIFIED", value="true")
    return 0


def verify_completion_main(argv: list[str]) -> int:
    values = _parse_values(
        argv,
        {"--sentinel-file", "--sentinel-root", "--prepared-input", "--prepared-deps", "--repo", "--issue"},
    )
    required = {"--sentinel-file", "--sentinel-root", "--prepared-input", "--prepared-deps", "--repo", "--issue"}
    if values is None or set(values) != required:
        return _emit_error("usage")
    try:
        _require_positive(values["--issue"], "umbrella")
        if not gh.validate_repo_slug(values["--repo"]):
            raise UmbrellaError("invalid-repository")
        sentinel_text = larch_io.read_trusted_text(values["--sentinel-file"], root=values["--sentinel-root"], reject_cr=True)
        rows: dict[str, str] = {}
        for line in sentinel_text.splitlines():
            key, separator, value = line.partition("=")
            if not separator or not key or key in rows or "\n" in value:
                raise UmbrellaError("invalid-completion-sentinel")
            rows[key] = value
        if set(rows) != {
            "UMBRELLA_SENTINEL_VERSION",
            "REPOSITORY",
            "UMBRELLA_NUMBER",
            "PREPARED_INPUT_SHA256",
            "PREPARED_DEPS_SHA256",
            "PREPARED_GRAPH_SHA256",
            "GRAPH_VERIFIED",
        }:
            raise UmbrellaError("invalid-completion-sentinel")
        live_input = larch_io.read_trusted_text(values["--prepared-input"], root=values["--sentinel-root"])
        live_deps = larch_io.read_trusted_text(values["--prepared-deps"], root=values["--sentinel-root"])
        live_input_sha256 = _text_sha256(live_input)
        live_deps_sha256 = _text_sha256(live_deps)
        expected_proposal, _issue_input = prepare_proposal_from_batch(
            snapshot=UmbrellaSnapshot(
                repository=values["--repo"],
                number=values["--issue"],
                title="",
                body="",
                state="OPEN",
                updated_at="",
            ),
            input_text=live_input,
            deps_text=live_deps,
        )
        if (
            rows["UMBRELLA_SENTINEL_VERSION"] != COMPLETION_SENTINEL_VERSION
            or rows["REPOSITORY"] != values["--repo"]
            or rows["UMBRELLA_NUMBER"] != values["--issue"]
            or rows["GRAPH_VERIFIED"] != "true"
            or not _valid_sha256(rows["PREPARED_INPUT_SHA256"])
            or not _valid_sha256(rows["PREPARED_DEPS_SHA256"])
            or not _valid_sha256(rows["PREPARED_GRAPH_SHA256"])
            or rows["PREPARED_INPUT_SHA256"] != live_input_sha256
            or rows["PREPARED_DEPS_SHA256"] != live_deps_sha256
            or rows["PREPARED_GRAPH_SHA256"] != _prepared_graph_sha256(expected_proposal)
        ):
            raise UmbrellaError("stale-completion-sentinel")
    except (OSError, ValueError, UmbrellaError) as exc:
        return _emit_error(getattr(exc, "reason", "invalid-completion-sentinel"))
    logging_util.emit_kv(key="UMBRELLA_COMPLETION_VERIFIED", value="true")
    logging_util.emit_kv(key="UMBRELLA_NUMBER", value=values["--issue"])
    return 0


def _parse_values(argv: list[str], permitted: set[str]) -> dict[str, str] | None:
    values: dict[str, str] = {}
    index = 0
    while index < len(argv):
        if argv[index] not in permitted or argv[index] in values or index + 1 >= len(argv):
            return None
        values[argv[index]] = argv[index + 1]
        index += 2
    return values
