# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnusedCallResult=false, reportUnnecessaryComparison=false
"""Durable, fail-closed orchestration for the two-round debate protocol.

The protocol module deliberately knows nothing about files or agents.  This
module is its sole stateful owner: it canonicalizes the persisted state,
serializes mutations with a per-debate lock, and turns untrusted vendor text
into protocol bindings only after the protocol parser accepts it.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Final, Protocol, Self, TextIO

from larch import io as larch_io
from larch.agents._types import VendorSessionHandle
from larch.core import config, external_defaults
from larch.debate import protocol

STATE_SCHEMA_VERSION: Final[int] = 1
UNAVAILABLE_VENDOR_LIMIT: Final[int] = 2

# ruff: noqa: PLR0913, FBT001, FBT003 - CLI wire and frozen state constructors mirror the explicit persisted schema.
_STATE_KEYS: Final[frozenset[str]] = frozenset(
    {"schema_version", "fingerprint", "initialization", "proposal", "active_round", "drops"}
)
_FINGERPRINT_HEX_LENGTH: Final[int] = 64


class DebateError(ValueError):
    """A stable, externally visible debate failure."""

    def __init__(self, error_class: str, message: str, exit_code: int = 2) -> None:
        self.error_class = error_class
        self.exit_code = exit_code
        super().__init__(message)


@dataclass(frozen=True)
class ParticipantSlot:
    """A persisted panel position sourced from the canonical role registry."""

    slot: str
    tool: str
    transport: str
    available: bool
    model: str = ""


@dataclass(frozen=True)
class RestoreMetadata:
    issue_number: str
    original_title: str
    restore_title: str


@dataclass(frozen=True)
class InitializationContext:
    point_universe: tuple[int, ...]
    run_local_values: Mapping[str, str]
    repo_workdir: str
    log_root: str
    run_id: str
    slots: tuple[ParticipantSlot, ...]
    restore: RestoreMetadata
    session_handles: Mapping[str, VendorSessionHandle] = field(default_factory=dict)
    warning: str = ""


@dataclass(frozen=True)
class ActiveRound:
    round_number: int
    prepared: bool
    mailboxes: Mapping[str, tuple[dict[str, object], ...]]
    live_slots: tuple[str, ...]
    pending_slots: tuple[str, ...]
    reserved_slot: str | None = None
    bindings: Mapping[str, protocol.SlotLedgerBinding] = field(default_factory=dict)


@dataclass(frozen=True)
class DropRecord:
    slot: str
    round_number: int
    reason: str
    event_id: str


@dataclass(frozen=True)
class ProposalState:
    """The persisted wrapper around the pure protocol proposal state."""

    initialization: InitializationContext
    proposal: protocol.ProposalState
    active_round: ActiveRound | None
    drops: tuple[DropRecord, ...] = ()
    fingerprint: str = ""


@dataclass(frozen=True)
class TurnRequest:
    slot: str
    round_number: int
    prompt: str
    mailbox: tuple[dict[str, object], ...]
    workdir: Path
    output: Path
    session_handle: VendorSessionHandle | None


@dataclass(frozen=True)
class TurnResult:
    ok: bool
    output: Path | None = None
    error_class: str = ""
    detail: str = ""


class TurnRunner(Protocol):
    def __call__(self, request: TurnRequest) -> TurnResult: ...


class SessionBootstrapper(Protocol):
    def __call__(self, slot: ParticipantSlot, context: InitializationContext) -> VendorSessionHandle: ...


def _canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"


def _strict_json(text: str) -> object:
    def reject_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise DebateError("corrupt_state", "duplicate JSON key", config.DEBATE_EXIT_CORRUPT_STATE)
            result[key] = value
        return result

    try:
        return json.loads(text, object_pairs_hook=reject_duplicates)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise DebateError("corrupt_state", "invalid state JSON", config.DEBATE_EXIT_CORRUPT_STATE) from exc


def _is_json_int(value: object) -> bool:
    """Reject JSON booleans and integer subclasses at the state boundary."""
    return type(value) is int  # pylint: disable=unidiomatic-typecheck  # exact JSON integer rejects bool and subclasses


def _is_exact_bool(value: object) -> bool:
    """Accept only a JSON boolean at the state boundary."""
    return type(value) is bool  # pylint: disable=unidiomatic-typecheck  # exact JSON boolean rejects integer subclasses


def _safe_line(value: str) -> bool:
    return bool(value) and "\n" not in value and "\r" not in value and "\x00" not in value


def _fingerprint_payload(payload: Mapping[str, object]) -> str:
    unsigned = dict(payload)
    unsigned.pop("fingerprint", None)
    return hashlib.sha256(_canonical_json(unsigned).encode("utf-8")).hexdigest()


def _point_values(raw: str) -> tuple[protocol.PointId, ...]:
    try:
        decoded: object = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise DebateError("validation", "point universe must be JSON", 2) from exc
    if not isinstance(decoded, list) or not decoded:
        raise DebateError("validation", "point universe must be a nonempty array", 2)
    points: list[protocol.PointId] = []
    seen: set[int] = set()
    for value in decoded:
        if not _is_json_int(value):  # pylint: disable=unidiomatic-typecheck  # JSON bool is not a point id
            raise DebateError("validation", "point universe values must be exact integers", 2)
        if value in seen:
            raise DebateError("validation", "point universe has duplicate values", 2)
        seen.add(value)
        try:
            points.append(protocol.PointId(value))
        except protocol.ProtocolRejection as exc:
            raise DebateError("validation", "point universe value is out of range", 2) from exc
    return tuple(points)


def _run_local_values(raw: str | None) -> dict[str, str]:
    if raw is None:
        return {}
    try:
        decoded: object = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise DebateError("validation", "run-local values must be JSON", 2) from exc
    if not isinstance(decoded, dict):  # pylint: disable=unidiomatic-typecheck  # exact JSON object required
        raise DebateError("validation", "run-local values must be an object", 2)
    result: dict[str, str] = {}
    for key, value in decoded.items():
        if not isinstance(key, str) or not isinstance(value, str):  # pylint: disable=unidiomatic-typecheck  # wire grammar is strings only
            raise DebateError("validation", "run-local values must contain strings", 2)
        if not _safe_line(key) or not _safe_line(value):
            raise DebateError("validation", "run-local values must be line-safe", 2)
        result[key] = value
    return dict(sorted(result.items()))


def _strict_bool(value: str) -> bool:
    if value not in {"true", "false"}:
        raise DebateError("validation", "presence flags must be true or false", 2)
    return value == "true"


def _trusted_root(path: str | Path, *, create: bool = False) -> Path:
    root = Path(path)
    # macOS exposes its system temporary directory through /tmp -> /private/tmp.
    # Treat that platform alias as the canonical temp root, while preserving the
    # no-symlink rule for caller-created debate roots.
    system_tmp = Path(tempfile.gettempdir())
    if root == system_tmp or system_tmp in root.parents:
        root = system_tmp / root.relative_to(system_tmp)
    try:
        return larch_io.ensure_trusted_directory(root) if create else larch_io.validate_trusted_directory(root)
    except OSError as exc:
        raise DebateError("persistence_failure", "unsafe debate directory", config.DEBATE_EXIT_PERSISTENCE_FAILURE) from exc


def _trusted_regular(path: Path, root: Path) -> None:
    try:
        if not larch_io.trusted_file_present(path, root=root):
            raise DebateError("corrupt_state", "state file missing", config.DEBATE_EXIT_CORRUPT_STATE)
    except OSError as exc:
        raise DebateError("corrupt_state", "unsafe state file", config.DEBATE_EXIT_CORRUPT_STATE) from exc


def _state_path(root: Path) -> Path:
    return root / config.DEBATE_STATE_FILENAME


def _encode_row(row: protocol.LedgerRow) -> dict[str, object]:
    return {"point": row.point_id.number, "action": row.action.value, "reason": row.reason}


def _encode_binding(binding: protocol.SlotLedgerBinding) -> dict[str, object]:
    return {
        "slot": binding.slot.value,
        "rows": [_encode_row(row) for row in binding.ledger.rows],
        "fingerprints": [fingerprint.value for fingerprint in binding.fingerprints],
    }


def _decode_binding(raw: object, run_local_values: Mapping[str, str]) -> protocol.SlotLedgerBinding:
    if not isinstance(raw, dict) or set(raw) != {"slot", "rows", "fingerprints"}:  # pylint: disable=unidiomatic-typecheck  # exact state shape
        raise DebateError("corrupt_state", "invalid binding", config.DEBATE_EXIT_CORRUPT_STATE)
    slot = raw["slot"]
    rows = raw["rows"]
    fingerprints = raw["fingerprints"]
    if not isinstance(slot, str) or not isinstance(rows, list) or not isinstance(fingerprints, list):  # pylint: disable=unidiomatic-typecheck  # decoded state boundary
        raise DebateError("corrupt_state", "invalid binding fields", config.DEBATE_EXIT_CORRUPT_STATE)
    lines: list[str] = []
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"point", "action", "reason"}:  # pylint: disable=unidiomatic-typecheck  # exact row schema
            raise DebateError("corrupt_state", "invalid ledger row", config.DEBATE_EXIT_CORRUPT_STATE)
        point, action, reason = row["point"], row["action"], row["reason"]
        if not _is_json_int(point) or not isinstance(action, str) or not isinstance(reason, str):  # pylint: disable=unidiomatic-typecheck  # decoded state boundary
            raise DebateError("corrupt_state", "invalid ledger row values", config.DEBATE_EXIT_CORRUPT_STATE)
        lines.append(f"POINT POINT_{point} {action} {reason}")
    try:
        ledger = protocol.parse_slot_ledger("\n".join(lines))
        parsed_fingerprints = tuple(protocol.ReasonFingerprint(value) for value in fingerprints if isinstance(value, str))
        if len(parsed_fingerprints) != len(fingerprints):
            raise protocol.ProtocolRejection(protocol.ParseRejectionReason.invalid_fingerprint)
        return protocol.SlotLedgerBinding(slot=protocol.parse_slot(slot), ledger=ledger, fingerprints=parsed_fingerprints, run_local_values=run_local_values)
    except (protocol.ProtocolRejection, ValueError) as exc:
        raise DebateError("corrupt_state", "invalid persisted binding", config.DEBATE_EXIT_CORRUPT_STATE) from exc


def _encode_proposal(proposal: protocol.ProposalState) -> dict[str, object]:
    return {
        "points": [point.number for point in proposal.point_universe],
        "phase": proposal.phase.value if proposal.phase is not None else None,
        "terminal": proposal.terminal_outcome.value if proposal.terminal_outcome is not None else None,
        "run_local_values": dict(sorted(proposal.run_local_values.items())),
        "rounds": [
            {"round": int(round_state.round_number), "bindings": [_encode_binding(binding) for binding in round_state.bindings]}
            for round_state in proposal.rounds
        ],
    }


def _decode_proposal(raw: object) -> protocol.ProposalState:
    if not isinstance(raw, dict) or set(raw) != {"points", "phase", "terminal", "run_local_values", "rounds"}:  # pylint: disable=unidiomatic-typecheck  # exact state shape
        raise DebateError("corrupt_state", "invalid proposal", config.DEBATE_EXIT_CORRUPT_STATE)
    points, phase, terminal, values, rounds = raw["points"], raw["phase"], raw["terminal"], raw["run_local_values"], raw["rounds"]
    if not isinstance(points, list) or not isinstance(values, dict) or not isinstance(rounds, list):  # pylint: disable=unidiomatic-typecheck  # decoded state boundary
        raise DebateError("corrupt_state", "invalid proposal fields", config.DEBATE_EXIT_CORRUPT_STATE)
    try:
        parsed_points = tuple(protocol.PointId(value) for value in points if _is_json_int(value))
        if len(parsed_points) != len(points):
            raise ValueError("point")
        parsed_values = {key: value for key, value in values.items() if isinstance(key, str) and isinstance(value, str)}
        if len(parsed_values) != len(values):
            raise ValueError("values")
        proposal = protocol.new_proposal(parsed_points, run_local_values=parsed_values)
        for item in rounds:
            if not isinstance(item, dict) or set(item) != {"round", "bindings"}:
                raise ValueError("round")
            number, bindings = item["round"], item["bindings"]
            if not _is_json_int(number) or not isinstance(bindings, list):
                raise ValueError("round")
            state = protocol.RoundState(protocol.RoundNumber(number), tuple(_decode_binding(binding, parsed_values) for binding in bindings))
            proposal = protocol.transition(proposal, protocol.TransitionAction.SUBMIT_ROUND, round_state=state)
        expected_phase = proposal.phase.value if proposal.phase is not None else None
        expected_terminal = proposal.terminal_outcome.value if proposal.terminal_outcome is not None else None
        if phase != expected_phase or terminal != expected_terminal:
            raise ValueError("proposal phase")
        return proposal
    except (ValueError, protocol.ProtocolRejection) as exc:
        raise DebateError("corrupt_state", "invalid proposal protocol state", config.DEBATE_EXIT_CORRUPT_STATE) from exc


def _encode_initialization(context: InitializationContext) -> dict[str, object]:
    return {
        "point_universe": list(context.point_universe), "run_local_values": dict(sorted(context.run_local_values.items())),
        "repo_workdir": context.repo_workdir, "log_root": context.log_root, "run_id": context.run_id,
        "slots": [asdict(slot) for slot in context.slots], "warning": context.warning,
        "restore": asdict(context.restore),
        "session_handles": {slot: {"vendor": handle.vendor, "session_id": handle.session_id} for slot, handle in sorted(context.session_handles.items())},
    }


def _decode_initialization(raw: object) -> InitializationContext:
    required = {"point_universe", "run_local_values", "repo_workdir", "log_root", "run_id", "slots", "warning", "restore", "session_handles"}
    if not isinstance(raw, dict) or set(raw) != required:  # pylint: disable=unidiomatic-typecheck  # exact schema
        raise DebateError("corrupt_state", "invalid initialization", config.DEBATE_EXIT_CORRUPT_STATE)
    try:
        points = raw["point_universe"]
        values = raw["run_local_values"]
        slots_raw = raw["slots"]
        restore_raw = raw["restore"]
        handles_raw = raw["session_handles"]
        if not isinstance(points, list) or not isinstance(values, dict) or not isinstance(slots_raw, list) or not isinstance(restore_raw, dict) or not isinstance(handles_raw, dict):  # pylint: disable=unidiomatic-typecheck  # decoded state boundary
            raise TypeError("shape")
        parsed_points = tuple(point for point in points if _is_json_int(point))
        parsed_values = {key: value for key, value in values.items() if isinstance(key, str) and isinstance(value, str)}
        if len(parsed_points) != len(points) or len(parsed_values) != len(values):
            raise ValueError("values")
        slots = tuple(ParticipantSlot(**item) for item in slots_raw if isinstance(item, dict))
        if len(slots) != len(slots_raw):
            raise ValueError("slots")
        restore = RestoreMetadata(**restore_raw)
        handles: dict[str, VendorSessionHandle] = {}
        for slot, item in handles_raw.items():
            if not isinstance(slot, str) or not isinstance(item, dict):
                raise TypeError("handle")
            handles[slot] = VendorSessionHandle.create(vendor=item["vendor"], session_id=item["session_id"])
        strings = (raw["repo_workdir"], raw["log_root"], raw["run_id"], raw["warning"])
        if any(not isinstance(value, str) for value in strings):
            raise ValueError("strings")
        return InitializationContext(parsed_points, parsed_values, *strings[:3], slots, restore, handles, strings[3])
    except (TypeError, ValueError, KeyError) as exc:
        raise DebateError("corrupt_state", "invalid initialization state", config.DEBATE_EXIT_CORRUPT_STATE) from exc


def _encode_active(active: ActiveRound | None) -> object:
    if active is None:
        return None
    return {"round": active.round_number, "prepared": active.prepared, "mailboxes": {slot: list(value) for slot, value in sorted(active.mailboxes.items())}, "live_slots": list(active.live_slots), "pending_slots": list(active.pending_slots), "reserved_slot": active.reserved_slot, "bindings": {slot: _encode_binding(binding) for slot, binding in sorted(active.bindings.items())}}


def _decode_active(raw: object, values: Mapping[str, str]) -> ActiveRound | None:
    if raw is None:
        return None
    required = {"round", "prepared", "mailboxes", "live_slots", "pending_slots", "reserved_slot", "bindings"}
    if not isinstance(raw, dict) or set(raw) != required:  # pylint: disable=unidiomatic-typecheck  # exact schema
        raise DebateError("corrupt_state", "invalid active round", config.DEBATE_EXIT_CORRUPT_STATE)
    try:
        number, prepared, mailboxes, live_slots, pending, reserved, bindings = (raw[key] for key in ("round", "prepared", "mailboxes", "live_slots", "pending_slots", "reserved_slot", "bindings"))
        invalid_shape = not all((isinstance(mailboxes, dict), isinstance(live_slots, list), isinstance(pending, list), isinstance(bindings, dict)))
        if not _is_json_int(number) or not _is_exact_bool(prepared) or invalid_shape or (reserved is not None and not isinstance(reserved, str)):
            raise ValueError("shape")
        if tuple(live_slots) != tuple(slot for slot in protocol.SLOT_ORDER if slot in live_slots) or any(not isinstance(slot, str) for slot in pending):
            raise ValueError("slot ordering")
        mailbox_data: dict[str, tuple[dict[str, object], ...]] = {}
        for slot, items in mailboxes.items():
            if not isinstance(slot, str) or not isinstance(items, list) or any(not isinstance(item, dict) for item in items):
                raise ValueError("mailbox")
            mailbox_data[slot] = tuple(items)
        parsed_bindings = {slot: _decode_binding(item, values) for slot, item in bindings.items() if isinstance(slot, str)}
        if len(parsed_bindings) != len(bindings) or set(parsed_bindings).difference(live_slots):
            raise ValueError("binding")
        return ActiveRound(number, prepared, mailbox_data, tuple(live_slots), tuple(pending), reserved, parsed_bindings)
    except (TypeError, ValueError) as exc:
        raise DebateError("corrupt_state", "invalid active round progress", config.DEBATE_EXIT_CORRUPT_STATE) from exc


def _encode_state(state: ProposalState) -> dict[str, object]:
    return {"schema_version": STATE_SCHEMA_VERSION, "fingerprint": state.fingerprint, "initialization": _encode_initialization(state.initialization), "proposal": _encode_proposal(state.proposal), "active_round": _encode_active(state.active_round), "drops": [asdict(drop) for drop in state.drops]}


def _state_with_fingerprint(state: ProposalState) -> ProposalState:
    payload = _encode_state(state)
    fingerprint = _fingerprint_payload(payload)
    return ProposalState(state.initialization, state.proposal, state.active_round, state.drops, fingerprint)


def load_state(root: str | Path) -> ProposalState:
    trusted_root = _trusted_root(root)
    path = _state_path(trusted_root)
    _trusted_regular(path, trusted_root)
    try:
        text = larch_io.read_trusted_text(path, root=trusted_root)
    except OSError as exc:
        raise DebateError("corrupt_state", "unable to read state", config.DEBATE_EXIT_CORRUPT_STATE) from exc
    raw = _strict_json(text)
    if not isinstance(raw, dict) or set(raw) != _STATE_KEYS:  # type: ignore[reportUnnecessaryComparison]  # runtime JSON keys are validated against the versioned schema  # pylint: disable=unidiomatic-typecheck  # exact versioned state schema
        raise DebateError("corrupt_state", "unknown state fields", config.DEBATE_EXIT_CORRUPT_STATE)
    if raw.get("schema_version") != STATE_SCHEMA_VERSION or not isinstance(raw.get("fingerprint"), str):  # pylint: disable=unidiomatic-typecheck  # schema field is exact string
        raise DebateError("corrupt_state", "unsupported state schema", config.DEBATE_EXIT_CORRUPT_STATE)
    if _canonical_json(raw) != text or _fingerprint_payload(raw) != raw["fingerprint"]:
        raise DebateError("corrupt_state", "noncanonical or stale state fingerprint", config.DEBATE_EXIT_CORRUPT_STATE)
    initialization = _decode_initialization(raw["initialization"])
    proposal = _decode_proposal(raw["proposal"])
    active = _decode_active(raw["active_round"], proposal.run_local_values)
    drops_raw = raw["drops"]
    if not isinstance(drops_raw, list):
        raise DebateError("corrupt_state", "invalid drops", config.DEBATE_EXIT_CORRUPT_STATE)
    try:
        drops = tuple(DropRecord(**item) for item in drops_raw if isinstance(item, dict))
    except TypeError as exc:
        raise DebateError("corrupt_state", "invalid drop", config.DEBATE_EXIT_CORRUPT_STATE) from exc
    if len(drops) != len(drops_raw):
        raise DebateError("corrupt_state", "invalid drop", config.DEBATE_EXIT_CORRUPT_STATE)
    return ProposalState(initialization, proposal, active, drops, raw["fingerprint"])


def write_state(root: str | Path, state: ProposalState) -> ProposalState:
    trusted_root = _trusted_root(root, create=True)
    finalized = _state_with_fingerprint(state)
    try:
        larch_io.trusted_atomic_write(_state_path(trusted_root), _canonical_json(_encode_state(finalized)), root=trusted_root)
    except OSError as exc:
        raise DebateError("persistence_failure", "unable to write state", config.DEBATE_EXIT_PERSISTENCE_FAILURE) from exc
    return finalized


class _StateLock:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.handle: TextIO | None = None

    def __enter__(self) -> Self:
        self.handle = (self.root / ".debate-state.lock").open("a+", encoding="utf-8")
        fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX)
        return self

    def __exit__(self, *_args: object) -> None:
        if self.handle is not None:
            fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
            self.handle.close()


def _require_fingerprint(state: ProposalState, expected: str) -> None:
    if expected != state.fingerprint:
        raise DebateError("stale_fingerprint", "expected fingerprint does not match state", config.DEBATE_EXIT_STALE_FINGERPRINT)


def _slots(cursor: bool, codex: bool, claude: bool) -> tuple[ParticipantSlot, ...]:
    availability = {"cursor": cursor, "codex": codex, "claude": claude}
    defaults = external_defaults.slot_defaults("debate.panel")
    slots = tuple(ParticipantSlot(item.slot, item.tool, item.transport, availability[item.tool], item.model) for item in defaults)
    if tuple(slot.slot for slot in slots) != protocol.SLOT_ORDER:
        raise DebateError("validation", "debate role seating does not match protocol order", 2)
    return slots


def initialize(
    *, root: str | Path, expected_fingerprint: str, repo_workdir: str, log_root: str, run_id: str,
    point_universe: Sequence[protocol.PointId], run_local_values: Mapping[str, str] | None,
    cursor_present: bool, codex_present: bool, claude_present: bool, restore_issue_number: str,
    restore_original_title: str, restore_title: str, bootstrapper: SessionBootstrapper | None = None,
) -> ProposalState:
    if expected_fingerprint != config.DEBATE_ABSENT_FINGERPRINT:
        raise DebateError("validation", "init requires ABSENT fingerprint", 2)
    if not all(_safe_line(value) for value in (repo_workdir, log_root, run_id, restore_issue_number, restore_original_title, restore_title)):
        raise DebateError("validation", "initialization strings must be line-safe", 2)
    debate_root = _trusted_root(root, create=True)
    try:
        workdir = larch_io.validate_trusted_directory(repo_workdir)
        trusted_log_root = _trusted_root(log_root, create=True)
    except OSError as exc:
        raise DebateError("validation", "unsafe initialization directory", 2) from exc
    with _StateLock(debate_root):
        if _state_path(debate_root).exists():
            raise DebateError("validation", "state already exists", 2)
        slots = _slots(cursor_present, codex_present, claude_present)
        missing = [slot for slot in slots if not slot.available]
        if len(missing) >= UNAVAILABLE_VENDOR_LIMIT:
            raise DebateError("validation", "two or more debate vendors unavailable", 2)
        warning = "" if not missing else f"unavailable vendor: {missing[0].slot}"
        values = dict(sorted((run_local_values or {}).items()))
        restore = RestoreMetadata(restore_issue_number, restore_original_title, restore_title)
        context = InitializationContext(tuple(point.number for point in point_universe), values, str(workdir), str(trusted_log_root), run_id, slots, restore, {}, warning)
        handles: dict[str, VendorSessionHandle] = {}
        if bootstrapper is not None:
            for slot in slots:
                if slot.available and slot.transport == "subprocess":
                    handles[slot.slot] = bootstrapper(slot, context)
            context = InitializationContext(
                context.point_universe,
                context.run_local_values,
                context.repo_workdir,
                context.log_root,
                context.run_id,
                context.slots,
                context.restore,
                handles,
                context.warning,
            )
        proposal = protocol.new_proposal(point_universe, run_local_values=values)
        return write_state(debate_root, ProposalState(context, proposal, None))


def _mailbox(binding: protocol.SlotLedgerBinding) -> dict[str, object]:
    return _encode_binding(binding)


def round_prep(*, root: str | Path, expected_fingerprint: str, round_number: int) -> ProposalState:
    debate_root = _trusted_root(root)
    with _StateLock(debate_root):
        state = load_state(debate_root)
        _require_fingerprint(state, expected_fingerprint)
        if state.active_round is not None:
            raise DebateError("validation", "an active round already exists", 2)
        if state.proposal.phase is None or round_number != len(state.proposal.rounds) + 1:
            raise DebateError("validation", "round is not admitted by proposal state", 2)
        live = tuple(slot.slot for slot in state.initialization.slots if slot.available)
        if len(live) < protocol.LIVE_PANEL_MINIMUM:
            raise DebateError("validation", "insufficient live panel", 2)
        mailboxes: dict[str, tuple[dict[str, object], ...]] = {}
        previous = state.proposal.rounds[-1] if state.proposal.rounds else None
        for slot in live:
            mailboxes[slot] = () if previous is None else tuple(_mailbox(binding) for binding in previous.bindings if binding.slot.value != slot)
        active = ActiveRound(round_number, True, mailboxes, live, live)
        return write_state(debate_root, ProposalState(state.initialization, state.proposal, active, state.drops))


def _default_runner(_request: TurnRequest) -> TurnResult:
    return TurnResult(False, error_class="unsupported_transport", detail="default runner is not configured")


def _drop(state: ProposalState, *, slot: str, round_number: int, reason: str) -> ProposalState:
    event = hashlib.sha256(f"{state.fingerprint}\0{slot}\0{round_number}\0{reason}".encode()).hexdigest()
    active = state.active_round
    if active is None:
        return state
    live = tuple(item for item in active.live_slots if item != slot)
    pending = tuple(item for item in active.pending_slots if item != slot)
    updated_active = ActiveRound(active.round_number, active.prepared, active.mailboxes, live, pending, None, active.bindings)
    drops = (*state.drops, DropRecord(slot, round_number, reason, event))
    proposal = state.proposal
    if len(live) < protocol.LIVE_PANEL_MINIMUM and proposal.phase is not None:
        proposal = protocol.transition(proposal, protocol.TransitionAction.ABORT)
    return ProposalState(state.initialization, proposal, updated_active, drops)


def record_turn(*, root: str | Path, expected_fingerprint: str, round_number: int, slot: str, runner: TurnRunner | None = None) -> tuple[ProposalState, str]:
    debate_root = _trusted_root(root)
    with _StateLock(debate_root):
        state = load_state(debate_root)
        _require_fingerprint(state, expected_fingerprint)
        active = state.active_round
        if active is None or not active.prepared or active.round_number != round_number or state.proposal.phase is None:
            raise DebateError("validation", "round has not been prepared", 2)
        if active.reserved_slot is not None or not active.pending_slots or active.pending_slots[0] != slot:
            raise DebateError("validation", "slot is not next pending slot", 2)
        if slot not in active.live_slots:
            raise DebateError("validation", "slot is not live", 2)
        handle = state.initialization.session_handles.get(slot)
        request = TurnRequest(slot, round_number, "", active.mailboxes[slot], Path(state.initialization.repo_workdir), debate_root / f"{slot}-round-{round_number}.out", handle)
        reserved = ActiveRound(active.round_number, active.prepared, active.mailboxes, active.live_slots, active.pending_slots, slot, active.bindings)
        state = write_state(debate_root, ProposalState(state.initialization, state.proposal, reserved, state.drops))
        result = (runner or _default_runner)(request)
        if not result.ok or result.output is None:
            dropped = _drop(state, slot=slot, round_number=round_number, reason=result.error_class or "runner_failure")
            return write_state(debate_root, dropped), result.error_class or "runner_failure"
        try:
            output = larch_io.read_trusted_text(result.output, root=debate_root)
            ledger = protocol.parse_slot_ledger(output)
            fingerprints = tuple(protocol.fingerprint_reason(row.reason, run_local_values=state.proposal.run_local_values) for row in ledger.rows)
            binding = protocol.SlotLedgerBinding(slot=protocol.parse_slot(slot), ledger=ledger, fingerprints=fingerprints, run_local_values=state.proposal.run_local_values)
        except (OSError, protocol.ProtocolRejection):
            dropped = _drop(state, slot=slot, round_number=round_number, reason="protocol_rejection")
            return write_state(debate_root, dropped), "protocol_rejection"
        completed = dict(reserved.bindings)
        completed[slot] = binding
        pending = tuple(item for item in reserved.pending_slots if item != slot)
        next_active = ActiveRound(round_number, True, reserved.mailboxes, reserved.live_slots, pending, None, completed)
        next_state = ProposalState(state.initialization, state.proposal, next_active, state.drops)
        if not pending:
            bindings = tuple(completed[item] for item in protocol.SLOT_ORDER if item in completed)
            try:
                proposal = protocol.transition(state.proposal, protocol.TransitionAction.SUBMIT_ROUND, round_state=protocol.RoundState(protocol.RoundNumber(round_number), bindings))
            except protocol.ProtocolRejection:
                dropped = _drop(state, slot=slot, round_number=round_number, reason="protocol_rejection")
                return write_state(debate_root, dropped), "protocol_rejection"
            next_state = ProposalState(state.initialization, proposal, None, state.drops)
        return write_state(debate_root, next_state), ""


def abort(*, root: str | Path, expected_fingerprint: str) -> ProposalState:
    debate_root = _trusted_root(root)
    with _StateLock(debate_root):
        state = load_state(debate_root)
        _require_fingerprint(state, expected_fingerprint)
        proposal = state.proposal
        if proposal.phase is not None:
            proposal = protocol.transition(proposal, protocol.TransitionAction.ABORT)
        updated = write_state(debate_root, ProposalState(state.initialization, proposal, state.active_round, state.drops))
        restore = updated.initialization.restore
        lines = (f"{config.DEBATE_RESTORE_ISSUE_NUMBER_KEY}={restore.issue_number}", f"{config.DEBATE_RESTORE_ORIGINAL_TITLE_KEY}={restore.original_title}", f"{config.DEBATE_RESTORE_TITLE_KEY}={restore.restore_title}", f"{config.DEBATE_SOURCE_FINGERPRINT_KEY}={updated.fingerprint}")
        payload = "\n".join(lines) + "\n"
        handoff = debate_root / config.DEBATE_ABORT_RESTORE_FILENAME
        if handoff.exists():
            try:
                if larch_io.read_trusted_text(handoff, root=debate_root) != payload:
                    raise DebateError("persistence_failure", "conflicting restore handoff", config.DEBATE_EXIT_PERSISTENCE_FAILURE)
            except OSError as exc:
                raise DebateError("persistence_failure", "unsafe restore handoff", config.DEBATE_EXIT_PERSISTENCE_FAILURE) from exc
        else:
            try:
                larch_io.trusted_atomic_write(handoff, payload, root=debate_root)
            except OSError as exc:
                raise DebateError("persistence_failure", "unable to write restore handoff", config.DEBATE_EXIT_PERSISTENCE_FAILURE) from exc
        return updated


def _envelope(*, ok: bool, operation: str, state: ProposalState | None, error_class: str = "", warning: str = "", slot_result: str = "") -> str:
    proposal = state.proposal if state is not None else None
    return json.dumps({"schema_version": 1, "ok": ok, "operation": operation, "fingerprint": state.fingerprint if state else None, "phase": proposal.phase.value if proposal and proposal.phase else None, "terminal_outcome": proposal.terminal_outcome.value if proposal and proposal.terminal_outcome else None, "warning": warning or (state.initialization.warning if state else ""), "slot_result": slot_result or None, "error_class": error_class or None}, sort_keys=True, separators=(",", ":"))


def _main(operation: str, argv: list[str] | None) -> int:
    parser = argparse.ArgumentParser(prog=f"cli.py debate {operation}")
    parser.add_argument("--debate-tmpdir", required=True)
    parser.add_argument("--expected-fingerprint", required=True)
    if operation == "init":
        for name in ("repo-workdir", "log-root", "run-id", "point-universe-json", "cursor-present", "codex-present", "claude-present", "restore-issue-number", "restore-original-title", "restore-title"):
            parser.add_argument(f"--{name}", required=True)
        parser.add_argument("--run-local-values-json")
    elif operation in {"round-prep", "record-turn"}:
        parser.add_argument("--round", required=True, type=int)
    if operation == "record-turn":
        parser.add_argument("--slot", required=True)
    try:
        args = parser.parse_args(argv)
        if operation == "init":
            state = initialize(root=args.debate_tmpdir, expected_fingerprint=args.expected_fingerprint, repo_workdir=args.repo_workdir, log_root=args.log_root, run_id=args.run_id, point_universe=_point_values(args.point_universe_json), run_local_values=_run_local_values(args.run_local_values_json), cursor_present=_strict_bool(args.cursor_present), codex_present=_strict_bool(args.codex_present), claude_present=_strict_bool(args.claude_present), restore_issue_number=args.restore_issue_number, restore_original_title=args.restore_original_title, restore_title=args.restore_title)
            print(_envelope(ok=True, operation=operation, state=state))
            return 0
        if operation == "round-prep":
            state = round_prep(root=args.debate_tmpdir, expected_fingerprint=args.expected_fingerprint, round_number=args.round)
            print(_envelope(ok=True, operation=operation, state=state))
            return 0
        if operation == "record-turn":
            state, result = record_turn(root=args.debate_tmpdir, expected_fingerprint=args.expected_fingerprint, round_number=args.round, slot=args.slot)
            code = config.DEBATE_EXIT_UNSUPPORTED_TRANSPORT if result == "unsupported_transport" else 0
            print(_envelope(ok=not result, operation=operation, state=state, error_class=result, slot_result=result))
            return code
        state = abort(root=args.debate_tmpdir, expected_fingerprint=args.expected_fingerprint)
        print(_envelope(ok=True, operation=operation, state=state))
        return 0
    except DebateError as exc:
        print(_envelope(ok=False, operation=operation, state=None, error_class=exc.error_class))
        return exc.exit_code
    except SystemExit:
        print(_envelope(ok=False, operation=operation, state=None, error_class="validation"))
        return 2


def init_main(argv: list[str] | None = None) -> int:
    return _main("init", argv)


def round_prep_main(argv: list[str] | None = None) -> int:
    return _main("round-prep", argv)


def record_turn_main(argv: list[str] | None = None) -> int:
    return _main("record-turn", argv)


def abort_main(argv: list[str] | None = None) -> int:
    return _main("abort", argv)
