"""Pure debate protocol: wire constants, ledger parsing, and fingerprints.

Side-effect free: no filesystem, environment, clock, subprocess, or network
access. Imports only the standard library plus ``larch.design.plan_grammar``.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Final

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
        PointId.from_token(token)
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
        needles_raw: list[str] = list(run_local_values.values())
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
