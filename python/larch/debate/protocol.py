"""Pure debate protocol: wire constants, ledger parsing, and state machine.

Side-effect free: no filesystem, environment, clock, subprocess, or network
access. Imports only the standard library plus ``larch.design.plan_grammar``.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import InitVar, dataclass, replace
from enum import IntEnum, StrEnum
from types import MappingProxyType
from typing import Final, cast

from larch.design import plan_grammar

# ---------------------------------------------------------------------------
# Wire constants
# ---------------------------------------------------------------------------

PROTOCOL_VERSION: Final[str] = "1"
FINGERPRINT_ALGORITHM_VERSION: Final[str] = "1"
FINGERPRINT_HEX_LENGTH: Final[int] = 16
ROUND_LIMIT: Final[int] = 2
POINT_ID_MIN: Final[int] = 1
POINT_ID_MAX: Final[int] = 9999

# Membership owner is larch.core.external_defaults.VALID_TOOLS; this module's
# purity constraint forbids importing larch.core, and the ordered triple has no
# existing owner. Update this tuple when that vendor set changes.
SLOT_ORDER: Final[tuple[str, ...]] = ("cursor", "codex", "claude")
SLOT_SET: Final[frozenset[str]] = frozenset(SLOT_ORDER)
# Live-panel floor is independent of SLOT_ORDER length (the maximum).
LIVE_PANEL_MINIMUM: Final[int] = 2
LIVE_PANEL_MAXIMUM: Final[int] = len(SLOT_ORDER)

LEDGER_POINT_TOKEN: Final[str] = "POINT"
POINT_ID_PREFIX: Final[str] = "POINT_"
ACTION_AGREE: Final[str] = "AGREE"
ACTION_CONCEDE: Final[str] = "CONCEDE"
ACTION_HOLD: Final[str] = "HOLD"
ACTION_TOKENS: Final[frozenset[str]] = frozenset(
    {ACTION_AGREE, ACTION_CONCEDE, ACTION_HOLD}
)

ARTIFACT_CITATION_PREFIX: Final[str] = "[[artifact:"
ARTIFACT_CITATION_SUFFIX: Final[str] = "]]"

# Every pattern below is built from the wire constants above so each literal
# has exactly one owner. Editing a constant moves its parser with it.
_LEDGER_ROW_RE: Final[re.Pattern[str]] = re.compile(
    rf"^{re.escape(LEDGER_POINT_TOKEN)} (\S+) (\S+) (.*)$"
)
# The digit bound is derived from POINT_ID_MAX so the accepted range has one
# owner. Matches are re-validated through is_valid_point_token, so a wider
# class stays safe while a narrower one would silently drop legal ids.
_POINT_CITATION_RE: Final[re.Pattern[str]] = re.compile(
    rf"(?<![A-Za-z0-9_]){re.escape(LEDGER_POINT_TOKEN)} "
    rf"({re.escape(POINT_ID_PREFIX)}[1-9][0-9]{{0,{len(str(POINT_ID_MAX)) - 1}}})"
    r"(?![0-9A-Za-z_])"
)
_ARTIFACT_CITATION_RE: Final[re.Pattern[str]] = re.compile(
    rf"{re.escape(ARTIFACT_CITATION_PREFIX)}([^\]]*)"
    rf"{re.escape(ARTIFACT_CITATION_SUFFIX)}"
)
_FINGERPRINT_RE: Final[re.Pattern[str]] = re.compile(
    rf"^[0-9a-f]{{{FINGERPRINT_HEX_LENGTH}}}$"
)
_CONTROL_OR_FORBIDDEN_RE: Final[re.Pattern[str]] = re.compile(
    r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\u2028\u2029\t\r]"
)
_RUN_LOCAL_PLACEHOLDER_PREFIX: Final[str] = "<run-local:"
_RUN_LOCAL_PLACEHOLDER_SUFFIX: Final[str] = ">"


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class Participant(StrEnum):
    """Fixed debate panel slots."""

    cursor = "cursor"
    codex = "codex"
    claude = "claude"


class Action(StrEnum):
    """Per-point ledger actions."""

    AGREE = "AGREE"
    CONCEDE = "CONCEDE"
    HOLD = "HOLD"


class ConcessionClassification(StrEnum):
    """Citation status for a ledger reason."""

    cited = "cited"
    fold = "fold"
    non_concession = "non-concession"


class ParseRejectionReason(StrEnum):
    """Stable fail-closed rejection tokens for protocol parsing and validation."""

    empty_submission = "empty-submission"
    blank_row = "blank-row"
    forbidden_character = "forbidden-character"
    leading_or_trailing_whitespace = "leading-or-trailing-whitespace"
    repeated_separator_spaces = "repeated-separator-spaces"
    malformed_row = "malformed-row"
    unknown_action = "unknown-action"
    empty_reason = "empty-reason"
    malformed_point_id = "malformed-point-id"
    point_id_out_of_range = "point-id-out-of-range"
    duplicate_point_id = "duplicate-point-id"
    forbidden_plan_content = "forbidden-plan-content"
    invalid_slot = "invalid-slot"
    invalid_artifact_path = "invalid-artifact-path"
    invalid_protocol_version = "invalid-protocol-version"
    invalid_fingerprint_version = "invalid-fingerprint-version"
    invalid_fingerprint = "invalid-fingerprint"
    empty_replacement_needle = "empty-replacement-needle"
    invalid_round_number = "invalid-round-number"
    invalid_slot_ordering = "invalid-slot-ordering"
    below_live_panel_floor = "below-live-panel-floor"
    above_live_panel_ceiling = "above-live-panel-ceiling"
    point_universe_mismatch = "point-universe-mismatch"
    fingerprint_mismatch = "fingerprint-mismatch"
    malformed_adjudication = "malformed-adjudication"
    incomplete_adjudication_coverage = "incomplete-adjudication-coverage"
    illegal_transition = "illegal-transition"
    empty_point_universe = "empty-point-universe"
    nonadjacent_rounds = "nonadjacent-rounds"
    invalid_run_local_values = "invalid-run-local-values"
    invalid_proposal_state = "invalid-proposal-state"


class RoundNumber(IntEnum):
    """Negotiation round index; membership is pinned to :data:`ROUND_LIMIT`."""

    ROUND_1 = 1
    ROUND_2 = 2


class PointResolution(StrEnum):
    """Per-point resolution derived from the normative closure predicate."""

    AGREED = "AGREED"
    CONCEDED = "CONCEDED"
    HELD = "HELD"
    FOLDED = "FOLDED"


class NonterminalPhase(StrEnum):
    """Nonterminal proposal phases of the debate state machine."""

    BLIND_ROUND_1 = "BLIND_ROUND_1"
    ROUND_2 = "ROUND_2"
    AWAITING_ADJUDICATION = "AWAITING_ADJUDICATION"
    UNCONVERGED = "UNCONVERGED"


class TerminalOutcome(StrEnum):
    """Terminal proposal outcomes; never enter the transition table as sources."""

    CONVERGED = "CONVERGED"
    STALEMATE = "STALEMATE"
    BOTH_VIABLE = "BOTH_VIABLE"
    ABORTED = "ABORTED"


class AdjudicationDecision(StrEnum):
    """Adjudication record variant."""

    SELECTED = "SELECTED"
    SPLIT = "SPLIT"


class StalemateDetectionStatus(StrEnum):
    """Whether stalemate detection ran or was skipped for changed membership."""

    COMPLETED = "COMPLETED"
    MEMBERSHIP_CHANGED = "MEMBERSHIP_CHANGED"


class TransitionAction(StrEnum):
    """Explicit transition-table actions."""

    SUBMIT_ROUND = "SUBMIT_ROUND"
    DECLARE_STALEMATE = "DECLARE_STALEMATE"
    ADJUDICATE = "ADJUDICATE"
    ABORT = "ABORT"


def _pin_round_number_enum() -> None:
    actual = frozenset(int(member) for member in RoundNumber)
    expected = frozenset(range(1, ROUND_LIMIT + 1))
    if actual != expected:
        raise RuntimeError(
            "RoundNumber membership must equal range(1, ROUND_LIMIT + 1); "
            f"got {sorted(actual)}, expected {sorted(expected)}"
        )


_pin_round_number_enum()

_RESOLVED_POINT_RESOLUTIONS: Final[frozenset[PointResolution]] = frozenset(
    {PointResolution.AGREED, PointResolution.CONCEDED}
)

# Explicit edge table keyed by (nonterminal phase, action). Payload rules and
# ROUND_LIMIT checks run only after an edge is admitted.
_TRANSITION_TABLE: Final[frozenset[tuple[NonterminalPhase, TransitionAction]]] = (
    frozenset(
        {
            (NonterminalPhase.BLIND_ROUND_1, TransitionAction.SUBMIT_ROUND),
            (NonterminalPhase.BLIND_ROUND_1, TransitionAction.ABORT),
            (NonterminalPhase.ROUND_2, TransitionAction.SUBMIT_ROUND),
            (NonterminalPhase.ROUND_2, TransitionAction.ABORT),
            (NonterminalPhase.AWAITING_ADJUDICATION, TransitionAction.DECLARE_STALEMATE),
            (NonterminalPhase.AWAITING_ADJUDICATION, TransitionAction.ADJUDICATE),
            (NonterminalPhase.AWAITING_ADJUDICATION, TransitionAction.ABORT),
            (NonterminalPhase.UNCONVERGED, TransitionAction.ADJUDICATE),
            (NonterminalPhase.UNCONVERGED, TransitionAction.ABORT),
        }
    )
)


# ---------------------------------------------------------------------------
# Domain errors and frozen value objects
# ---------------------------------------------------------------------------


class ProtocolRejection(ValueError):
    """Fail-closed protocol rejection carrying a stable reason token."""

    def __init__(self, reason: ParseRejectionReason) -> None:
        self.reason = reason
        super().__init__(reason.value)


@dataclass(frozen=True)
class PointId:
    """Inclusive ``POINT_1`` … ``POINT_9999`` identity."""

    number: int

    def __post_init__(self) -> None:
        if type(self.number) is not int:  # pylint: disable=unidiomatic-typecheck  # exact runtime type rejects bool and subclasses
            raise ProtocolRejection(ParseRejectionReason.malformed_point_id)
        if self.number < POINT_ID_MIN or self.number > POINT_ID_MAX:
            raise ProtocolRejection(ParseRejectionReason.point_id_out_of_range)

    @property
    def token(self) -> str:
        return f"{POINT_ID_PREFIX}{self.number}"

    @classmethod
    def from_token(cls, token: str) -> PointId:
        if not token.startswith(POINT_ID_PREFIX) or len(token) <= len(POINT_ID_PREFIX):
            raise ProtocolRejection(ParseRejectionReason.malformed_point_id)
        rest = token[len(POINT_ID_PREFIX) :]
        if not rest.isdigit() or rest[0] == "0":
            raise ProtocolRejection(ParseRejectionReason.malformed_point_id)
        number = int(rest, 10)
        if number > POINT_ID_MAX:
            raise ProtocolRejection(ParseRejectionReason.point_id_out_of_range)
        return cls(number)


@dataclass(frozen=True)
class ReasonFingerprint:
    """Validated 16-character lowercase hex fingerprint prefix."""

    value: str

    def __post_init__(self) -> None:
        if not _FINGERPRINT_RE.fullmatch(self.value):
            raise ProtocolRejection(ParseRejectionReason.invalid_fingerprint)


@dataclass(frozen=True)
class LedgerRow:
    """One parsed ``POINT POINT_N <ACTION> <reason>`` row."""

    point_id: PointId
    action: Action
    reason: str
    concession: ConcessionClassification


@dataclass(frozen=True)
class ParsedSlotLedger:
    """Parsed rows for one slot submission."""

    rows: tuple[LedgerRow, ...]


# ---------------------------------------------------------------------------
# Lexical validators
# ---------------------------------------------------------------------------


def is_valid_slot(value: str) -> bool:
    """Return whether ``value`` is one of the fixed panel slots."""
    return value in SLOT_SET


def parse_slot(value: str) -> Participant:
    """Parse a slot name into :class:`Participant` or raise."""
    if not is_valid_slot(value):
        raise ProtocolRejection(ParseRejectionReason.invalid_slot)
    return Participant(value)


def is_valid_point_token(token: str) -> bool:
    """Return whether ``token`` is a canonical ``POINT_N`` in range."""
    try:
        _ = PointId.from_token(token)
    except ProtocolRejection:
        return False
    return True


def is_valid_artifact_path(path: str) -> bool:
    """Return whether ``path`` is a nonempty relative POSIX artifact path.

    Rejects absolute paths, empty or ``.`` / ``..`` segments, parent traversal,
    backslashes, controls, and malformed separators. Spaces inside otherwise
    valid segments are permitted.
    """
    if not path or path.startswith("/") or "\\" in path or path.endswith("/"):
        return False
    if _CONTROL_OR_FORBIDDEN_RE.search(path) is not None:
        return False
    if "//" in path:
        return False
    segments = path.split("/")
    return not any(segment == "" or segment in {".", ".."} for segment in segments)


def is_valid_protocol_version(value: str) -> bool:
    """Return whether ``value`` is the supported protocol version."""
    return value == PROTOCOL_VERSION


def is_valid_fingerprint_version(value: str) -> bool:
    """Return whether ``value`` is the supported fingerprint-algorithm version."""
    return value == FINGERPRINT_ALGORITHM_VERSION


def is_valid_fingerprint(value: str) -> bool:
    """Return whether ``value`` is exactly 16 lowercase hexadecimal characters."""
    return _FINGERPRINT_RE.fullmatch(value) is not None


def parse_protocol_version(value: str) -> str:
    """Accept the supported protocol version or raise."""
    if not is_valid_protocol_version(value):
        raise ProtocolRejection(ParseRejectionReason.invalid_protocol_version)
    return value


def parse_fingerprint_version(value: str) -> str:
    """Accept the supported fingerprint-algorithm version or raise."""
    if not is_valid_fingerprint_version(value):
        raise ProtocolRejection(ParseRejectionReason.invalid_fingerprint_version)
    return value


def parse_fingerprint(value: str) -> ReasonFingerprint:
    """Parse a fingerprint hex prefix into :class:`ReasonFingerprint`."""
    return ReasonFingerprint(value)


# ---------------------------------------------------------------------------
# Forbidden plan content
# ---------------------------------------------------------------------------


def reject_forbidden_plan_content(text: str) -> None:
    """Reject canonical plan headings and whole-line ``diff_lines:`` trailers.

    Uses ``plan_grammar`` iterators only; other trailer keys such as
    ``difficulty:`` and ``review_status:`` are not rejected as trailers.
    """
    if next(plan_grammar.iter_plan_headings(text), None) is not None:
        raise ProtocolRejection(ParseRejectionReason.forbidden_plan_content)
    if (
        next(plan_grammar.iter_trailer_lines(text, keys=("diff_lines",)), None)
        is not None
    ):
        raise ProtocolRejection(ParseRejectionReason.forbidden_plan_content)


# ---------------------------------------------------------------------------
# Ledger parsing
# ---------------------------------------------------------------------------


def _preflight_charset(submission: str) -> None:
    if _CONTROL_OR_FORBIDDEN_RE.search(submission) is not None:
        raise ProtocolRejection(ParseRejectionReason.forbidden_character)


def _match_ledger_row(row: str) -> re.Match[str]:
    if row.startswith(" "):
        raise ProtocolRejection(ParseRejectionReason.leading_or_trailing_whitespace)
    match = _LEDGER_ROW_RE.fullmatch(row)
    if match is None:
        if "  " in row:
            raise ProtocolRejection(ParseRejectionReason.repeated_separator_spaces)
        raise ProtocolRejection(ParseRejectionReason.malformed_row)
    # Structural separators are the single spaces before the reason. Reason-
    # internal spacing, including doubled spaces, is preserved byte for byte.
    if "  " in row[: match.start(3)]:
        raise ProtocolRejection(ParseRejectionReason.repeated_separator_spaces)
    return match


def _parse_point_id(token: str, *, seen: set[int]) -> PointId:
    try:
        point_id = PointId.from_token(token)
    except ProtocolRejection as exc:
        if exc.reason is ParseRejectionReason.point_id_out_of_range:
            raise
        raise ProtocolRejection(ParseRejectionReason.malformed_point_id) from exc
    if point_id.number in seen:
        raise ProtocolRejection(ParseRejectionReason.duplicate_point_id)
    seen.add(point_id.number)
    return point_id


def _parse_action(token: str) -> Action:
    if token not in ACTION_TOKENS:
        raise ProtocolRejection(ParseRejectionReason.unknown_action)
    return Action(token)


def _parse_ledger_row(row: str, *, seen: set[int]) -> LedgerRow:
    match = _match_ledger_row(row)
    reason = match.group(3)
    if reason == "":
        raise ProtocolRejection(ParseRejectionReason.empty_reason)
    if reason.endswith(" "):
        raise ProtocolRejection(ParseRejectionReason.leading_or_trailing_whitespace)

    point_id = _parse_point_id(match.group(1), seen=seen)
    action = _parse_action(match.group(2))
    reject_forbidden_plan_content(reason)
    return LedgerRow(
        point_id=point_id,
        action=action,
        reason=reason,
        concession=classify_concession(action, reason),
    )


def parse_slot_ledger(submission: str) -> ParsedSlotLedger:
    """Parse one slot submission with LF-only row separation.

    Splits only on literal LF. A trailing newline yields a final empty
    segment and is rejected as a blank row. Duplicate point tracking is local
    to this call.
    """
    if submission == "":
        raise ProtocolRejection(ParseRejectionReason.empty_submission)
    _preflight_charset(submission)

    segments = submission.split("\n")
    if any(segment == "" for segment in segments):
        raise ProtocolRejection(ParseRejectionReason.blank_row)

    seen: set[int] = set()
    rows = [_parse_ledger_row(segment, seen=seen) for segment in segments]
    return ParsedSlotLedger(rows=tuple(rows))


# ---------------------------------------------------------------------------
# Concession citation classification
# ---------------------------------------------------------------------------


def _has_valid_point_citation(reason: str) -> bool:
    for match in _POINT_CITATION_RE.finditer(reason):
        if is_valid_point_token(match.group(1)):
            return True
    return False


def _has_valid_artifact_citation(reason: str) -> bool:
    for match in _ARTIFACT_CITATION_RE.finditer(reason):
        if is_valid_artifact_path(match.group(1)):
            return True
    return False


def classify_concession(action: Action, reason: str) -> ConcessionClassification:
    """Classify a reason's concession citation status.

    ``CONCEDE`` reasons are ``cited`` when they contain at least one complete
    bounded ``POINT POINT_N`` citation or an exact
    ``[[artifact:RELATIVE_POSIX_PATH]]`` citation with a valid path. Otherwise
    they are ``fold``. Non-concession actions receive ``non_concession``.
    Malformed near-miss citations do not invalidate the reason; they simply
    leave a concession classified as a fold. The original reason is retained
    by the caller in either case.
    """
    if action is not Action.CONCEDE:
        return ConcessionClassification.non_concession
    if _has_valid_point_citation(reason) or _has_valid_artifact_citation(reason):
        return ConcessionClassification.cited
    return ConcessionClassification.fold


# ---------------------------------------------------------------------------
# Fingerprinting
# ---------------------------------------------------------------------------


def normalize_reason_for_fingerprint(
    reason: str,
    *,
    run_local_values: Iterable[str] | Mapping[str, str] = (),
) -> str:
    """NFKC-normalize ``reason`` and replace run-local values deterministically.

    Replacement needles are taken from ``run_local_values`` (iterable of values,
    or mapping values when a mapping is supplied). Empty needles are rejected.
    Needles are applied longest-first, then lexicographically, so overlapping
    values and caller container order cannot change the result.
    """
    if isinstance(run_local_values, Mapping):
        needles_raw: list[str] = list(
            cast("Mapping[str, str]", run_local_values).values()
        )
    else:
        needles_raw = list(run_local_values)

    for needle in needles_raw:
        if needle == "":
            raise ProtocolRejection(ParseRejectionReason.empty_replacement_needle)

    text = unicodedata.normalize("NFKC", reason)
    unique = sorted(set(needles_raw), key=lambda item: (-len(item), item))
    for index, needle in enumerate(unique):
        placeholder = (
            f"{_RUN_LOCAL_PLACEHOLDER_PREFIX}{index}{_RUN_LOCAL_PLACEHOLDER_SUFFIX}"
        )
        text = text.replace(needle, placeholder)
    return text


def fingerprint_reason(
    reason: str,
    *,
    run_local_values: Iterable[str] | Mapping[str, str] = (),
) -> ReasonFingerprint:
    """Return a versioned 16-character lowercase SHA-256 fingerprint prefix.

    Domain-separates the hash with :data:`FINGERPRINT_ALGORITHM_VERSION`. Does
    not read clocks, environment, filesystem, working directory, or other
    ambient metadata unless the caller supplies those values for placeholder
    replacement.
    """
    normalized = normalize_reason_for_fingerprint(
        reason, run_local_values=run_local_values
    )
    payload = f"{FINGERPRINT_ALGORITHM_VERSION}\0{normalized}".encode()
    digest = hashlib.sha256(payload).hexdigest()[:FINGERPRINT_HEX_LENGTH]
    return ReasonFingerprint(digest)


# ---------------------------------------------------------------------------
# Round assembly, resolution, stalemate, adjudication, transitions
# ---------------------------------------------------------------------------


def _slot_order_index(slot: Participant) -> int:
    try:
        return SLOT_ORDER.index(slot.value)
    except ValueError as exc:
        raise ProtocolRejection(ParseRejectionReason.invalid_slot) from exc


def _freeze_run_local_values(
    values: Mapping[str, str] | None,
) -> Mapping[str, str]:
    if values is None:
        return MappingProxyType({})
    if not isinstance(values, Mapping):
        raise ProtocolRejection(ParseRejectionReason.invalid_run_local_values)
    frozen: dict[str, str] = {}
    for key, value in values.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise ProtocolRejection(ParseRejectionReason.invalid_run_local_values)
        frozen[key] = value
    return MappingProxyType(frozen)


def _verify_binding_fingerprints(
    ledger: ParsedSlotLedger,
    fingerprints: tuple[ReasonFingerprint, ...],
    run_local_values: Mapping[str, str],
) -> None:
    if len(fingerprints) != len(ledger.rows):
        raise ProtocolRejection(ParseRejectionReason.fingerprint_mismatch)
    for row, expected in zip(ledger.rows, fingerprints, strict=True):
        actual = fingerprint_reason(row.reason, run_local_values=run_local_values)
        if actual != expected:
            raise ProtocolRejection(ParseRejectionReason.fingerprint_mismatch)


def _ledger_point_ids(ledger: ParsedSlotLedger) -> tuple[PointId, ...]:
    return tuple(row.point_id for row in ledger.rows)


def _validate_point_universe(
    point_universe: tuple[PointId, ...],
) -> tuple[PointId, ...]:
    if not point_universe:
        raise ProtocolRejection(ParseRejectionReason.empty_point_universe)
    seen: set[int] = set()
    for point_id in point_universe:
        if not isinstance(point_id, PointId):
            raise ProtocolRejection(ParseRejectionReason.malformed_point_id)
        if point_id.number in seen:
            raise ProtocolRejection(ParseRejectionReason.duplicate_point_id)
        seen.add(point_id.number)
    return point_universe


def _validate_adjudication_position(text: str) -> None:
    if text == "" or text != text.strip():
        raise ProtocolRejection(ParseRejectionReason.malformed_adjudication)
    if "\n" in text or "\r" in text:
        raise ProtocolRejection(ParseRejectionReason.malformed_adjudication)
    if _CONTROL_OR_FORBIDDEN_RE.search(text) is not None:
        raise ProtocolRejection(ParseRejectionReason.forbidden_character)
    reject_forbidden_plan_content(text)


def _require_ascending_slots(slots: Sequence[Participant]) -> None:
    previous_index = -1
    seen: set[Participant] = set()
    for slot in slots:
        if not isinstance(slot, Participant):
            raise ProtocolRejection(ParseRejectionReason.invalid_slot)
        if slot in seen:
            raise ProtocolRejection(ParseRejectionReason.invalid_slot_ordering)
        seen.add(slot)
        index = _slot_order_index(slot)
        if index <= previous_index:
            raise ProtocolRejection(ParseRejectionReason.invalid_slot_ordering)
        previous_index = index


def _validate_round_bindings(bindings: tuple[SlotLedgerBinding, ...]) -> None:
    if len(bindings) < LIVE_PANEL_MINIMUM:
        raise ProtocolRejection(ParseRejectionReason.below_live_panel_floor)
    if len(bindings) > LIVE_PANEL_MAXIMUM:
        raise ProtocolRejection(ParseRejectionReason.above_live_panel_ceiling)
    if not all(isinstance(binding, SlotLedgerBinding) for binding in bindings):
        raise ProtocolRejection(ParseRejectionReason.invalid_slot_ordering)
    _require_ascending_slots(tuple(binding.slot for binding in bindings))
    reference_points = _ledger_point_ids(bindings[0].ledger)
    for binding in bindings[1:]:
        if _ledger_point_ids(binding.ledger) != reference_points:
            raise ProtocolRejection(ParseRejectionReason.point_universe_mismatch)


@dataclass(frozen=True)
class SlotLedgerBinding:
    """One live slot bound to exactly one parsed ledger and row fingerprints."""

    slot: Participant
    ledger: ParsedSlotLedger
    fingerprints: tuple[ReasonFingerprint, ...]
    run_local_values: InitVar[Mapping[str, str] | None] = None

    def __post_init__(self, run_local_values: Mapping[str, str] | None) -> None:
        if not isinstance(self.slot, Participant):
            raise ProtocolRejection(ParseRejectionReason.invalid_slot)
        if not isinstance(self.ledger, ParsedSlotLedger):
            raise ProtocolRejection(ParseRejectionReason.malformed_row)
        if not isinstance(self.fingerprints, tuple):
            raise ProtocolRejection(ParseRejectionReason.fingerprint_mismatch)
        values = _freeze_run_local_values(run_local_values)
        _verify_binding_fingerprints(self.ledger, self.fingerprints, values)


@dataclass(frozen=True)
class RoundState:
    """Immutable assembly of one negotiation round's live slot bindings."""

    round_number: RoundNumber
    bindings: tuple[SlotLedgerBinding, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.round_number, RoundNumber):
            raise ProtocolRejection(ParseRejectionReason.invalid_round_number)
        if int(self.round_number) < 1 or int(self.round_number) > ROUND_LIMIT:
            raise ProtocolRejection(ParseRejectionReason.invalid_round_number)
        object.__setattr__(self, "bindings", tuple(self.bindings))
        _validate_round_bindings(self.bindings)

    @property
    def live_slots(self) -> tuple[Participant, ...]:
        return tuple(binding.slot for binding in self.bindings)

    @property
    def point_ids(self) -> tuple[PointId, ...]:
        return _ledger_point_ids(self.bindings[0].ledger)


@dataclass(frozen=True)
class Dispute:
    """Stalemate dispute for one point with at least two unchanged HOLD slots."""

    point_id: PointId
    holding_slots: tuple[Participant, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.point_id, PointId):
            raise ProtocolRejection(ParseRejectionReason.malformed_point_id)
        if len(self.holding_slots) < LIVE_PANEL_MINIMUM:
            raise ProtocolRejection(ParseRejectionReason.below_live_panel_floor)
        _require_ascending_slots(self.holding_slots)


@dataclass(frozen=True)
class SelectedAdjudication:
    """Selected-position adjudication for one unresolved point."""

    point_id: PointId
    selected_position: str

    def __post_init__(self) -> None:
        if not isinstance(self.point_id, PointId):
            raise ProtocolRejection(ParseRejectionReason.malformed_point_id)
        if not isinstance(self.selected_position, str):
            raise ProtocolRejection(ParseRejectionReason.malformed_adjudication)
        _validate_adjudication_position(self.selected_position)

    @property
    def decision(self) -> AdjudicationDecision:
        return AdjudicationDecision.SELECTED


@dataclass(frozen=True)
class SplitAdjudication:
    """Split-position adjudication for one unresolved point."""

    point_id: PointId
    position_a: str
    position_b: str

    def __post_init__(self) -> None:
        if not isinstance(self.point_id, PointId):
            raise ProtocolRejection(ParseRejectionReason.malformed_point_id)
        if not isinstance(self.position_a, str) or not isinstance(self.position_b, str):
            raise ProtocolRejection(ParseRejectionReason.malformed_adjudication)
        _validate_adjudication_position(self.position_a)
        _validate_adjudication_position(self.position_b)
        if self.position_a == self.position_b:
            raise ProtocolRejection(ParseRejectionReason.malformed_adjudication)

    @property
    def decision(self) -> AdjudicationDecision:
        return AdjudicationDecision.SPLIT


AdjudicationRecord = SelectedAdjudication | SplitAdjudication


def slot_closes_point(row: LedgerRow) -> bool:
    """Return whether a slot's row closes a point under the normative predicate."""
    if row.action is Action.AGREE:
        return True
    return (
        row.action is Action.CONCEDE
        and row.concession is ConcessionClassification.cited
    )


def resolve_point(rows: Sequence[LedgerRow]) -> PointResolution:
    """Resolve one point from every live slot's row for that point.

    A point resolves only when every live slot closes it. Closing actions are
    ``AGREE`` and cited ``CONCEDE``. Folded concessions and ``HOLD`` never close.
    """
    if not rows:
        raise ProtocolRejection(ParseRejectionReason.below_live_panel_floor)
    if all(slot_closes_point(row) for row in rows):
        if all(row.action is Action.AGREE for row in rows):
            return PointResolution.AGREED
        return PointResolution.CONCEDED
    if any(row.action is Action.HOLD for row in rows):
        return PointResolution.HELD
    return PointResolution.FOLDED


def _row_for_point(binding: SlotLedgerBinding, point_id: PointId) -> LedgerRow:
    matches = [row for row in binding.ledger.rows if row.point_id == point_id]
    if len(matches) != 1:
        raise ProtocolRejection(ParseRejectionReason.point_universe_mismatch)
    return matches[0]


def resolve_round_points(
    round_state: RoundState,
) -> dict[PointId, PointResolution]:
    """Apply the normative predicate to every point in ``round_state``."""
    return {
        point_id: resolve_point(
            tuple(_row_for_point(binding, point_id) for binding in round_state.bindings)
        )
        for point_id in round_state.point_ids
    }


def unresolved_points(round_state: RoundState) -> tuple[PointId, ...]:
    """Return ordered unresolved point IDs from the normative predicate."""
    resolutions = resolve_round_points(round_state)
    return tuple(
        point_id
        for point_id in round_state.point_ids
        if resolutions[point_id] not in _RESOLVED_POINT_RESOLUTIONS
    )


def round_is_fully_resolved(round_state: RoundState) -> bool:
    """Return whether every point in the round is AGREED or CONCEDED."""
    return not unresolved_points(round_state)


def _revalidate_round_against_proposal(
    proposal: ProposalState,
    round_state: RoundState,
) -> None:
    if round_state.point_ids != proposal.point_universe:
        raise ProtocolRejection(ParseRejectionReason.point_universe_mismatch)
    for binding in round_state.bindings:
        _verify_binding_fingerprints(
            binding.ledger,
            binding.fingerprints,
            proposal.run_local_values,
        )


@dataclass(frozen=True)
class StalemateDetection:
    """Stalemate-detection result separating empty success from a skipped run."""

    status: StalemateDetectionStatus
    disputes: tuple[Dispute, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "disputes", tuple(self.disputes))
        if self.status is StalemateDetectionStatus.MEMBERSHIP_CHANGED and self.disputes:
            raise ProtocolRejection(ParseRejectionReason.invalid_proposal_state)


def detect_stalemate_disputes(
    proposal: ProposalState,
    earlier: RoundState,
    later: RoundState,
) -> StalemateDetection:
    """Detect qualifying HOLD stalemates across adjacent rounds.

    Requires adjacent round numbers. Forged or mismatched fingerprints raise. A
    dispute requires at least two matching slots that ``HOLD`` in both rounds
    with unchanged recomputed fingerprints under the proposal's frozen run-local
    snapshot. Changed live-slot membership skips detection and reports
    :attr:`StalemateDetectionStatus.MEMBERSHIP_CHANGED`, which is distinct from a
    completed run that found no qualifying dispute.
    """
    if int(later.round_number) != int(earlier.round_number) + 1:
        raise ProtocolRejection(ParseRejectionReason.nonadjacent_rounds)

    _revalidate_round_against_proposal(proposal, earlier)
    _revalidate_round_against_proposal(proposal, later)

    if earlier.live_slots != later.live_slots:
        return StalemateDetection(
            status=StalemateDetectionStatus.MEMBERSHIP_CHANGED, disputes=()
        )

    earlier_by_slot = {binding.slot: binding for binding in earlier.bindings}
    later_by_slot = {binding.slot: binding for binding in later.bindings}
    disputes: list[Dispute] = []
    for point_index, point_id in enumerate(proposal.point_universe):
        holding_slots: list[Participant] = []
        for slot in earlier.live_slots:
            earlier_binding = earlier_by_slot[slot]
            later_binding = later_by_slot[slot]
            earlier_row = earlier_binding.ledger.rows[point_index]
            later_row = later_binding.ledger.rows[point_index]
            if earlier_row.point_id != point_id or later_row.point_id != point_id:
                raise ProtocolRejection(ParseRejectionReason.point_universe_mismatch)
            if earlier_row.action is not Action.HOLD or later_row.action is not Action.HOLD:
                continue
            earlier_fp = fingerprint_reason(
                earlier_row.reason, run_local_values=proposal.run_local_values
            )
            later_fp = fingerprint_reason(
                later_row.reason, run_local_values=proposal.run_local_values
            )
            earlier_expected = earlier_binding.fingerprints[point_index]
            later_expected = later_binding.fingerprints[point_index]
            if earlier_fp != earlier_expected or later_fp != later_expected:
                raise ProtocolRejection(ParseRejectionReason.fingerprint_mismatch)
            if earlier_fp != later_fp:
                continue
            holding_slots.append(slot)
        if len(holding_slots) >= LIVE_PANEL_MINIMUM:
            disputes.append(
                Dispute(point_id=point_id, holding_slots=tuple(holding_slots))
            )
    return StalemateDetection(
        status=StalemateDetectionStatus.COMPLETED, disputes=tuple(disputes)
    )


def _adjudication_coverage(
    unresolved: Sequence[PointId],
    records: Sequence[AdjudicationRecord],
) -> tuple[set[PointId], bool]:
    unresolved_tuple = tuple(unresolved)
    if not unresolved_tuple:
        raise ProtocolRejection(ParseRejectionReason.malformed_adjudication)
    unresolved_set = set(unresolved_tuple)
    if len(unresolved_set) != len(unresolved_tuple):
        raise ProtocolRejection(ParseRejectionReason.duplicate_point_id)
    if len(records) != len(unresolved_tuple):
        raise ProtocolRejection(
            ParseRejectionReason.incomplete_adjudication_coverage
        )

    seen: set[PointId] = set()
    has_split = False
    for record in records:
        if not isinstance(record, (SelectedAdjudication, SplitAdjudication)):
            raise ProtocolRejection(ParseRejectionReason.malformed_adjudication)
        if record.point_id in seen or record.point_id not in unresolved_set:
            raise ProtocolRejection(ParseRejectionReason.malformed_adjudication)
        seen.add(record.point_id)
        has_split = has_split or isinstance(record, SplitAdjudication)
    if seen != unresolved_set:
        raise ProtocolRejection(
            ParseRejectionReason.incomplete_adjudication_coverage
        )
    return seen, has_split


def validate_adjudication_set(
    unresolved: Sequence[PointId],
    records: Sequence[AdjudicationRecord],
) -> TerminalOutcome:
    """Validate a complete adjudication set against unresolved points.

    Returns :attr:`TerminalOutcome.CONVERGED` when every record is selected, or
    :attr:`TerminalOutcome.BOTH_VIABLE` when any record is a split.
    """
    _seen, has_split = _adjudication_coverage(unresolved, records)
    if has_split:
        return TerminalOutcome.BOTH_VIABLE
    return TerminalOutcome.CONVERGED


def _validate_proposal_phase_fields(
    phase: NonterminalPhase | None,
    terminal_outcome: TerminalOutcome | None,
) -> None:
    phase_set = phase is not None
    terminal_set = terminal_outcome is not None
    if phase_set == terminal_set:
        raise ProtocolRejection(ParseRejectionReason.invalid_proposal_state)
    if phase is not None and not isinstance(phase, NonterminalPhase):
        raise ProtocolRejection(ParseRejectionReason.invalid_proposal_state)
    if terminal_outcome is not None and not isinstance(
        terminal_outcome, TerminalOutcome
    ):
        raise ProtocolRejection(ParseRejectionReason.invalid_proposal_state)


def _validate_proposal_rounds(
    point_universe: tuple[PointId, ...],
    rounds: tuple[RoundState, ...],
    run_local_values: Mapping[str, str],
) -> None:
    if len(rounds) > ROUND_LIMIT:
        raise ProtocolRejection(ParseRejectionReason.illegal_transition)
    for index, round_state in enumerate(rounds):
        if not isinstance(round_state, RoundState):
            raise ProtocolRejection(ParseRejectionReason.invalid_round_number)
        if int(round_state.round_number) != index + 1:
            raise ProtocolRejection(ParseRejectionReason.invalid_round_number)
        if round_state.point_ids != point_universe:
            raise ProtocolRejection(ParseRejectionReason.point_universe_mismatch)
        for binding in round_state.bindings:
            _verify_binding_fingerprints(
                binding.ledger,
                binding.fingerprints,
                run_local_values,
            )


def _validate_proposal_records(
    disputes: tuple[Dispute, ...],
    adjudications: tuple[AdjudicationRecord, ...],
) -> None:
    for dispute in disputes:
        if not isinstance(dispute, Dispute):
            raise ProtocolRejection(ParseRejectionReason.invalid_proposal_state)
    for record in adjudications:
        if not isinstance(record, (SelectedAdjudication, SplitAdjudication)):
            raise ProtocolRejection(ParseRejectionReason.malformed_adjudication)


def _validate_proposal_shape(
    phase: NonterminalPhase | None,
    terminal_outcome: TerminalOutcome | None,
    rounds: tuple[RoundState, ...],
    disputes: tuple[Dispute, ...],
    adjudications: tuple[AdjudicationRecord, ...],
) -> None:
    if phase is NonterminalPhase.BLIND_ROUND_1 and rounds:
        raise ProtocolRejection(ParseRejectionReason.invalid_proposal_state)
    if phase is NonterminalPhase.ROUND_2 and len(rounds) != 1:
        raise ProtocolRejection(ParseRejectionReason.invalid_proposal_state)
    if phase in {
        NonterminalPhase.AWAITING_ADJUDICATION,
        NonterminalPhase.UNCONVERGED,
    } and len(rounds) != ROUND_LIMIT:
        raise ProtocolRejection(ParseRejectionReason.invalid_proposal_state)
    if terminal_outcome is TerminalOutcome.STALEMATE and (
        adjudications or not disputes
    ):
        raise ProtocolRejection(ParseRejectionReason.invalid_proposal_state)
    if terminal_outcome is TerminalOutcome.BOTH_VIABLE and not adjudications:
        raise ProtocolRejection(ParseRejectionReason.invalid_proposal_state)
    if terminal_outcome is TerminalOutcome.ABORTED and (
        disputes or adjudications
    ):
        raise ProtocolRejection(ParseRejectionReason.invalid_proposal_state)
    if phase is NonterminalPhase.AWAITING_ADJUDICATION and not disputes:
        raise ProtocolRejection(ParseRejectionReason.invalid_proposal_state)
    if phase is not None and adjudications:
        raise ProtocolRejection(ParseRejectionReason.invalid_proposal_state)


@dataclass(frozen=True)
class ProposalState:
    """Immutable proposal protocol state, including the fixed point universe."""

    point_universe: tuple[PointId, ...]
    protocol_version: str
    fingerprint_algorithm_version: str
    run_local_values: Mapping[str, str]
    phase: NonterminalPhase | None
    terminal_outcome: TerminalOutcome | None
    rounds: tuple[RoundState, ...]
    disputes: tuple[Dispute, ...]
    adjudications: tuple[AdjudicationRecord, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "point_universe",
            _validate_point_universe(tuple(self.point_universe)),
        )
        parse_protocol_version(self.protocol_version)
        parse_fingerprint_version(self.fingerprint_algorithm_version)
        object.__setattr__(
            self,
            "run_local_values",
            _freeze_run_local_values(
                cast("Mapping[str, str] | None", self.run_local_values)
            ),
        )
        object.__setattr__(self, "rounds", tuple(self.rounds))
        object.__setattr__(self, "disputes", tuple(self.disputes))
        object.__setattr__(self, "adjudications", tuple(self.adjudications))
        _validate_proposal_phase_fields(self.phase, self.terminal_outcome)
        _validate_proposal_rounds(
            self.point_universe, self.rounds, self.run_local_values
        )
        _validate_proposal_records(self.disputes, self.adjudications)
        _validate_proposal_shape(
            self.phase,
            self.terminal_outcome,
            self.rounds,
            self.disputes,
            self.adjudications,
        )


def new_proposal(
    point_universe: Sequence[PointId],
    *,
    protocol_version: str = PROTOCOL_VERSION,
    fingerprint_algorithm_version: str = FINGERPRINT_ALGORITHM_VERSION,
    run_local_values: Mapping[str, str] | None = None,
) -> ProposalState:
    """Construct a proposal in blind round 1 with no prior rounds."""
    return ProposalState(
        point_universe=tuple(point_universe),
        protocol_version=protocol_version,
        fingerprint_algorithm_version=fingerprint_algorithm_version,
        run_local_values=_freeze_run_local_values(run_local_values),
        phase=NonterminalPhase.BLIND_ROUND_1,
        terminal_outcome=None,
        rounds=(),
        disputes=(),
        adjudications=(),
    )


def _require_nonterminal(proposal: ProposalState) -> NonterminalPhase:
    if proposal.phase is None or proposal.terminal_outcome is not None:
        raise ProtocolRejection(ParseRejectionReason.illegal_transition)
    return proposal.phase


def _admit_transition(
    phase: NonterminalPhase, action: TransitionAction
) -> None:
    if (phase, action) not in _TRANSITION_TABLE:
        raise ProtocolRejection(ParseRejectionReason.illegal_transition)


def _expected_submit_round_number(proposal: ProposalState) -> RoundNumber:
    next_index = len(proposal.rounds) + 1
    if next_index > ROUND_LIMIT:
        raise ProtocolRejection(ParseRejectionReason.illegal_transition)
    try:
        return RoundNumber(next_index)
    except ValueError as exc:
        raise ProtocolRejection(ParseRejectionReason.invalid_round_number) from exc


def _submit_round(
    proposal: ProposalState, round_state: RoundState
) -> ProposalState:
    expected = _expected_submit_round_number(proposal)
    if round_state.round_number is not expected:
        raise ProtocolRejection(ParseRejectionReason.invalid_round_number)
    _revalidate_round_against_proposal(proposal, round_state)

    new_rounds = (*proposal.rounds, round_state)
    if round_is_fully_resolved(round_state):
        return replace(
            proposal,
            phase=None,
            terminal_outcome=TerminalOutcome.CONVERGED,
            rounds=new_rounds,
            disputes=(),
            adjudications=(),
        )

    if expected is RoundNumber.ROUND_1:
        return replace(
            proposal,
            phase=NonterminalPhase.ROUND_2,
            terminal_outcome=None,
            rounds=new_rounds,
            disputes=(),
            adjudications=(),
        )

    # Round 2 incomplete: classify by qualifying disputes covering all unresolved.
    earlier = proposal.rounds[0]
    detection = detect_stalemate_disputes(proposal, earlier, round_state)
    unresolved = unresolved_points(round_state)
    disputes: tuple[Dispute, ...] = ()
    if detection.status is StalemateDetectionStatus.MEMBERSHIP_CHANGED:
        # Detection was skipped, not empty: surviving-slot holds stay unclassified.
        next_phase = NonterminalPhase.UNCONVERGED
    elif unresolved and {
        dispute.point_id for dispute in detection.disputes
    } == set(unresolved):
        next_phase = NonterminalPhase.AWAITING_ADJUDICATION
        disputes = detection.disputes
    else:
        next_phase = NonterminalPhase.UNCONVERGED
    return replace(
        proposal,
        phase=next_phase,
        terminal_outcome=None,
        rounds=new_rounds,
        disputes=disputes,
        adjudications=(),
    )


def _declare_stalemate(proposal: ProposalState) -> ProposalState:
    if not proposal.disputes:
        raise ProtocolRejection(ParseRejectionReason.illegal_transition)
    return replace(
        proposal,
        phase=None,
        terminal_outcome=TerminalOutcome.STALEMATE,
        adjudications=(),
    )


def _adjudicate(
    proposal: ProposalState, records: Sequence[AdjudicationRecord]
) -> ProposalState:
    if len(proposal.rounds) != ROUND_LIMIT:
        raise ProtocolRejection(ParseRejectionReason.illegal_transition)
    latest = proposal.rounds[-1]
    unresolved = unresolved_points(latest)
    # Reject adjudicating already-resolved points via validate_adjudication_set.
    outcome = validate_adjudication_set(unresolved, records)
    return replace(
        proposal,
        phase=None,
        terminal_outcome=outcome,
        adjudications=tuple(records),
    )


def _abort(proposal: ProposalState) -> ProposalState:
    return replace(
        proposal,
        phase=None,
        terminal_outcome=TerminalOutcome.ABORTED,
        disputes=(),
        adjudications=(),
    )


def transition(
    proposal: ProposalState,
    action: TransitionAction,
    *,
    round_state: RoundState | None = None,
    adjudications: Sequence[AdjudicationRecord] | None = None,
) -> ProposalState:
    """Apply one explicit transition-table edge with payload-gated validation.

    The edge table is checked before payload-specific validation so illegal
    edges cannot bypass the two-round cap or terminal immutability.
    """
    phase = _require_nonterminal(proposal)
    _admit_transition(phase, action)

    if action is TransitionAction.SUBMIT_ROUND:
        if round_state is None or adjudications is not None:
            raise ProtocolRejection(ParseRejectionReason.illegal_transition)
        return _submit_round(proposal, round_state)
    if action is TransitionAction.DECLARE_STALEMATE:
        if round_state is not None or adjudications is not None:
            raise ProtocolRejection(ParseRejectionReason.illegal_transition)
        return _declare_stalemate(proposal)
    if action is TransitionAction.ADJUDICATE:
        if round_state is not None or adjudications is None:
            raise ProtocolRejection(ParseRejectionReason.illegal_transition)
        return _adjudicate(proposal, adjudications)
    if action is TransitionAction.ABORT:
        if round_state is not None or adjudications is not None:
            raise ProtocolRejection(ParseRejectionReason.illegal_transition)
        return _abort(proposal)
    raise ProtocolRejection(ParseRejectionReason.illegal_transition)
