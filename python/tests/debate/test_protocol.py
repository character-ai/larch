"""Offline table-driven coverage for the pure debate protocol.

Apart from the doc-parity lane's single read of the committed
``docs/debate-protocol.md``, this module uses fixed literals and pure
constructors only: no subprocess, clock, environment, or network access.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

import larch.debate as debate_facade
from larch.core import external_defaults
from larch.debate import protocol
from larch.debate.protocol import (
    ACTION_AGREE,
    ACTION_CONCEDE,
    ACTION_HOLD,
    ACTION_TOKENS,
    ARTIFACT_CITATION_PREFIX,
    ARTIFACT_CITATION_SUFFIX,
    FINGERPRINT_ALGORITHM_VERSION,
    FINGERPRINT_HEX_LENGTH,
    LEDGER_POINT_TOKEN,
    LIVE_PANEL_MAXIMUM,
    LIVE_PANEL_MINIMUM,
    POINT_ID_MAX,
    POINT_ID_MIN,
    POINT_ID_PREFIX,
    PROTOCOL_VERSION,
    ROUND_LIMIT,
    SLOT_ORDER,
    SLOT_SET,
    Action,
    AdjudicationDecision,
    ConcessionClassification,
    Dispute,
    LedgerRow,
    NonterminalPhase,
    ParseRejectionReason,
    ParsedSlotLedger,
    Participant,
    PointId,
    PointResolution,
    ProposalState,
    ProtocolRejection,
    ReasonFingerprint,
    RoundNumber,
    RoundState,
    SelectedAdjudication,
    SlotLedgerBinding,
    SplitAdjudication,
    StalemateDetection,
    StalemateDetectionStatus,
    TerminalOutcome,
    TransitionAction,
    classify_concession,
    detect_stalemate_disputes,
    fingerprint_reason,
    is_valid_artifact_path,
    is_valid_fingerprint,
    is_valid_fingerprint_version,
    is_valid_point_token,
    is_valid_protocol_version,
    is_valid_slot,
    new_proposal,
    normalize_reason_for_fingerprint,
    parse_fingerprint,
    parse_fingerprint_version,
    parse_protocol_version,
    parse_slot,
    parse_slot_ledger,
    reject_forbidden_plan_content,
    resolve_point,
    resolve_round_points,
    round_is_fully_resolved,
    slot_closes_point,
    transition,
    unresolved_points,
    validate_adjudication_set,
)

# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[3]
_PROTOCOL_DOC = _REPO_ROOT / "docs" / "debate-protocol.md"

_LEGAL_EDGES: frozenset[tuple[NonterminalPhase, TransitionAction]] = frozenset(
    {
        (NonterminalPhase.BLIND_ROUND_1, TransitionAction.SUBMIT_ROUND),
        (NonterminalPhase.BLIND_ROUND_1, TransitionAction.ABORT),
        (NonterminalPhase.ROUND_2, TransitionAction.SUBMIT_ROUND),
        (NonterminalPhase.ROUND_2, TransitionAction.ABORT),
        (
            NonterminalPhase.AWAITING_ADJUDICATION,
            TransitionAction.DECLARE_STALEMATE,
        ),
        (NonterminalPhase.AWAITING_ADJUDICATION, TransitionAction.ADJUDICATE),
        (NonterminalPhase.AWAITING_ADJUDICATION, TransitionAction.ABORT),
        (NonterminalPhase.UNCONVERGED, TransitionAction.ADJUDICATE),
        (NonterminalPhase.UNCONVERGED, TransitionAction.ABORT),
    }
)


def _expect_reject(reason: ParseRejectionReason, call: object) -> None:
    with pytest.raises(ProtocolRejection) as exc_info:
        call()  # type: ignore[operator]
    assert exc_info.value.reason is reason


def _ledger_from_specs(
    specs: list[tuple[int, Action, str]],
) -> ParsedSlotLedger:
    lines = [
        f"{LEDGER_POINT_TOKEN} {POINT_ID_PREFIX}{number} {action.value} {reason}"
        for number, action, reason in specs
    ]
    return parse_slot_ledger("\n".join(lines))


def _binding(
    slot: Participant,
    ledger: ParsedSlotLedger,
    *,
    run_local_values: dict[str, str] | None = None,
    fingerprints: tuple[ReasonFingerprint, ...] | None = None,
) -> SlotLedgerBinding:
    values = run_local_values or {}
    fps = fingerprints
    if fps is None:
        fps = tuple(
            fingerprint_reason(row.reason, run_local_values=values)
            for row in ledger.rows
        )
    return SlotLedgerBinding(
        slot=slot,
        ledger=ledger,
        fingerprints=fps,
        run_local_values=run_local_values,
    )


def _round(
    number: RoundNumber,
    bindings: list[SlotLedgerBinding],
) -> RoundState:
    return RoundState(round_number=number, bindings=tuple(bindings))


def _agree_ledger(*point_numbers: int) -> ParsedSlotLedger:
    return _ledger_from_specs(
        [(n, Action.AGREE, f"agree {n}") for n in point_numbers]
    )


def _hold_ledger(reason: str, *point_numbers: int) -> ParsedSlotLedger:
    return _ledger_from_specs(
        [(n, Action.HOLD, reason) for n in point_numbers]
    )


def _mixed_hold_agree(hold_reason: str) -> ParsedSlotLedger:
    return _ledger_from_specs(
        [
            (1, Action.HOLD, hold_reason),
            (2, Action.AGREE, "agreed second"),
        ]
    )


def _two_slot_round(
    number: RoundNumber,
    ledger: ParsedSlotLedger,
    *,
    run_local_values: dict[str, str] | None = None,
) -> RoundState:
    return _round(
        number,
        [
            _binding(Participant.cursor, ledger, run_local_values=run_local_values),
            _binding(Participant.codex, ledger, run_local_values=run_local_values),
        ],
    )


def _proposal_after_round1_holds(
    hold_reason: str = "stable hold reason",
) -> ProposalState:
    points = (PointId(1), PointId(2))
    proposal = new_proposal(points)
    ledger = _mixed_hold_agree(hold_reason)
    round1 = _two_slot_round(RoundNumber.ROUND_1, ledger)
    return transition(proposal, TransitionAction.SUBMIT_ROUND, round_state=round1)


def _proposal_awaiting_adjudication(
    hold_reason: str = "stable hold reason",
) -> ProposalState:
    after_r1 = _proposal_after_round1_holds(hold_reason)
    ledger = _mixed_hold_agree(hold_reason)
    round2 = _two_slot_round(RoundNumber.ROUND_2, ledger)
    return transition(after_r1, TransitionAction.SUBMIT_ROUND, round_state=round2)


def _proposal_unconverged() -> ProposalState:
    """Round 2 incomplete with no qualifying two-slot HOLD dispute."""
    points = (PointId(1), PointId(2))
    proposal = new_proposal(points)
    r1_ledger = _ledger_from_specs(
        [
            (1, Action.HOLD, "round1 hold"),
            (2, Action.AGREE, "ok"),
        ]
    )
    after_r1 = transition(
        proposal,
        TransitionAction.SUBMIT_ROUND,
        round_state=_two_slot_round(RoundNumber.ROUND_1, r1_ledger),
    )
    # Round 2: only one slot still HOLDs with the same fingerprint.
    cursor_ledger = _ledger_from_specs(
        [
            (1, Action.HOLD, "round1 hold"),
            (2, Action.AGREE, "ok"),
        ]
    )
    codex_ledger = _ledger_from_specs(
        [
            (1, Action.CONCEDE, "uncited fold"),
            (2, Action.AGREE, "ok"),
        ]
    )
    round2 = _round(
        RoundNumber.ROUND_2,
        [
            _binding(Participant.cursor, cursor_ledger),
            _binding(Participant.codex, codex_ledger),
        ],
    )
    return transition(after_r1, TransitionAction.SUBMIT_ROUND, round_state=round2)


# ---------------------------------------------------------------------------
# Constants, enums, facade, slot parity
# ---------------------------------------------------------------------------


def test_exported_constants() -> None:
    assert PROTOCOL_VERSION == "1"
    assert FINGERPRINT_ALGORITHM_VERSION == "1"
    assert FINGERPRINT_HEX_LENGTH == 16
    assert ROUND_LIMIT == 2
    assert POINT_ID_MIN == 1
    assert POINT_ID_MAX == 9999
    assert SLOT_ORDER == ("cursor", "codex", "claude")
    assert SLOT_SET == frozenset(SLOT_ORDER)
    assert LIVE_PANEL_MINIMUM == 2
    assert LIVE_PANEL_MAXIMUM == len(SLOT_ORDER)
    assert LEDGER_POINT_TOKEN == "POINT"
    assert POINT_ID_PREFIX == "POINT_"
    assert ACTION_AGREE == "AGREE"
    assert ACTION_CONCEDE == "CONCEDE"
    assert ACTION_HOLD == "HOLD"
    assert ACTION_TOKENS == frozenset({ACTION_AGREE, ACTION_CONCEDE, ACTION_HOLD})
    assert ARTIFACT_CITATION_PREFIX == "[[artifact:"
    assert ARTIFACT_CITATION_SUFFIX == "]]"


def test_enum_membership_and_values() -> None:
    assert {member.value for member in Participant} == set(SLOT_ORDER)
    assert {member.value for member in Action} == set(ACTION_TOKENS)
    assert set(ConcessionClassification) == {
        ConcessionClassification.cited,
        ConcessionClassification.fold,
        ConcessionClassification.non_concession,
    }
    assert ConcessionClassification.cited.value == "cited"
    assert ConcessionClassification.fold.value == "fold"
    assert ConcessionClassification.non_concession.value == "non-concession"
    assert list(RoundNumber) == [RoundNumber.ROUND_1, RoundNumber.ROUND_2]
    assert int(RoundNumber.ROUND_1) == 1
    assert int(RoundNumber.ROUND_2) == 2
    assert frozenset(int(member) for member in RoundNumber) == frozenset(
        range(1, ROUND_LIMIT + 1)
    )
    assert set(PointResolution) == {
        PointResolution.AGREED,
        PointResolution.CONCEDED,
        PointResolution.HELD,
        PointResolution.FOLDED,
    }
    assert set(NonterminalPhase) == {
        NonterminalPhase.BLIND_ROUND_1,
        NonterminalPhase.ROUND_2,
        NonterminalPhase.AWAITING_ADJUDICATION,
        NonterminalPhase.UNCONVERGED,
    }
    assert set(TerminalOutcome) == {
        TerminalOutcome.CONVERGED,
        TerminalOutcome.STALEMATE,
        TerminalOutcome.BOTH_VIABLE,
        TerminalOutcome.ABORTED,
    }
    assert set(AdjudicationDecision) == {
        AdjudicationDecision.SELECTED,
        AdjudicationDecision.SPLIT,
    }
    assert set(StalemateDetectionStatus) == {
        StalemateDetectionStatus.COMPLETED,
        StalemateDetectionStatus.MEMBERSHIP_CHANGED,
    }
    assert set(TransitionAction) == {
        TransitionAction.SUBMIT_ROUND,
        TransitionAction.DECLARE_STALEMATE,
        TransitionAction.ADJUDICATE,
        TransitionAction.ABORT,
    }


def test_version_and_fingerprint_parsers() -> None:
    assert parse_protocol_version("1") == "1"
    assert parse_fingerprint_version("1") == "1"
    assert is_valid_protocol_version("1") is True
    assert is_valid_fingerprint_version("1") is True
    assert is_valid_protocol_version("2") is False
    assert is_valid_fingerprint_version("0") is False
    _expect_reject(
        ParseRejectionReason.invalid_protocol_version,
        lambda: parse_protocol_version("2"),
    )
    _expect_reject(
        ParseRejectionReason.invalid_fingerprint_version,
        lambda: parse_fingerprint_version("0"),
    )
    assert is_valid_fingerprint("a" * FINGERPRINT_HEX_LENGTH) is True
    assert is_valid_fingerprint("A" * FINGERPRINT_HEX_LENGTH) is False
    assert is_valid_fingerprint("a" * (FINGERPRINT_HEX_LENGTH - 1)) is False
    assert parse_fingerprint("0123456789abcdef").value == "0123456789abcdef"
    _expect_reject(
        ParseRejectionReason.invalid_fingerprint,
        lambda: parse_fingerprint("not-hex-fingerprint"),
    )


def test_dataclass_immutability_and_tuple_coercion() -> None:
    point = PointId(1)
    with pytest.raises(FrozenInstanceError):
        point.number = 2  # type: ignore[misc]
    ledger = _agree_ledger(1)
    binding = _binding(Participant.cursor, ledger)
    with pytest.raises(FrozenInstanceError):
        binding.slot = Participant.codex  # type: ignore[misc]
    # RoundState coerces a list of bindings to a tuple.
    coerced = RoundState(
        round_number=RoundNumber.ROUND_1,
        bindings=[  # type: ignore[arg-type]
            _binding(Participant.cursor, ledger),
            _binding(Participant.codex, ledger),
        ],
    )
    assert isinstance(coerced.bindings, tuple)
    assert len(coerced.bindings) == 2


def test_facade_all_matches_piece1_exports() -> None:
    expected = [
        "ACTION_AGREE",
        "ACTION_CONCEDE",
        "ACTION_HOLD",
        "ACTION_TOKENS",
        "ARTIFACT_CITATION_PREFIX",
        "ARTIFACT_CITATION_SUFFIX",
        "FINGERPRINT_ALGORITHM_VERSION",
        "FINGERPRINT_HEX_LENGTH",
        "LEDGER_POINT_TOKEN",
        "POINT_ID_MAX",
        "POINT_ID_MIN",
        "POINT_ID_PREFIX",
        "PROTOCOL_VERSION",
        "ROUND_LIMIT",
        "SLOT_ORDER",
        "SLOT_SET",
        "Action",
        "ConcessionClassification",
        "LedgerRow",
        "ParseRejectionReason",
        "ParsedSlotLedger",
        "Participant",
        "PointId",
        "ProtocolRejection",
        "ReasonFingerprint",
        "classify_concession",
        "fingerprint_reason",
        "is_valid_artifact_path",
        "is_valid_fingerprint",
        "is_valid_fingerprint_version",
        "is_valid_point_token",
        "is_valid_protocol_version",
        "is_valid_slot",
        "normalize_reason_for_fingerprint",
        "parse_fingerprint",
        "parse_fingerprint_version",
        "parse_protocol_version",
        "parse_slot",
        "parse_slot_ledger",
        "reject_forbidden_plan_content",
    ]
    assert list(debate_facade.__all__) == expected
    for name in expected:
        assert getattr(debate_facade, name) is getattr(protocol, name)
    # Piece 2 symbols stay off the facade; import them from protocol directly.
    assert not hasattr(debate_facade, "transition")
    assert not hasattr(debate_facade, "new_proposal")
    assert not hasattr(debate_facade, "RoundState")
    assert protocol.transition is transition
    assert protocol.new_proposal is new_proposal


def test_debate_panel_slot_parity_with_external_defaults() -> None:
    panel = external_defaults.slot_defaults("debate.panel")
    ordered = tuple(slot.slot for slot in panel)
    assert ordered == SLOT_ORDER
    assert frozenset(ordered) == SLOT_SET


# ---------------------------------------------------------------------------
# Lexical validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "ok"),
    [
        ("cursor", True),
        ("codex", True),
        ("claude", True),
        ("Cursor", False),
        ("gpt", False),
        ("", False),
    ],
    ids=[
        "slot-cursor",
        "slot-codex",
        "slot-claude",
        "slot-case",
        "slot-unknown",
        "slot-empty",
    ],
)
def test_slot_validation(value: str, ok: bool) -> None:
    assert is_valid_slot(value) is ok
    if ok:
        assert parse_slot(value).value == value
    else:
        _expect_reject(ParseRejectionReason.invalid_slot, lambda: parse_slot(value))


@pytest.mark.parametrize(
    ("token", "ok"),
    [
        ("POINT_1", True),
        ("POINT_9999", True),
        ("POINT_0", False),
        ("POINT_01", False),
        ("POINT_10000", False),
        ("POINT_", False),
        ("POINT_1a", False),
        ("point_1", False),
        ("P1", False),
    ],
    ids=[
        "point-min",
        "point-max",
        "point-zero",
        "point-leading-zero",
        "point-over-max",
        "point-bare-prefix",
        "point-alpha-suffix",
        "point-lowercase",
        "point-short",
    ],
)
def test_point_token_validation(token: str, ok: bool) -> None:
    assert is_valid_point_token(token) is ok


@pytest.mark.parametrize(
    ("path", "ok"),
    [
        ("docs/x.md", True),
        ("a b/c.md", True),
        ("file.md", True),
        ("", False),
        ("/abs.md", False),
        ("a\\b.md", False),
        ("a/../b.md", False),
        ("./x.md", False),
        ("a//b.md", False),
        ("a/", False),
        ("a/\tb.md", False),
    ],
    ids=[
        "path-nested",
        "path-space-segment",
        "path-simple",
        "path-empty",
        "path-absolute",
        "path-backslash",
        "path-parent",
        "path-dot",
        "path-double-slash",
        "path-trailing-slash",
        "path-tab",
    ],
)
def test_artifact_path_validation(path: str, ok: bool) -> None:
    assert is_valid_artifact_path(path) is ok


@pytest.mark.parametrize(
    ("text", "reason"),
    [
        ("### NEW: x.py", ParseRejectionReason.forbidden_plan_content),
        ("### UPDATED: x.py", ParseRejectionReason.forbidden_plan_content),
        ("### REWRITTEN: x.py", ParseRejectionReason.forbidden_plan_content),
        ("### MAY_UPDATE: x.py", ParseRejectionReason.forbidden_plan_content),
        ("diff_lines: 12", ParseRejectionReason.forbidden_plan_content),
    ],
    ids=[
        "forbid-new",
        "forbid-updated",
        "forbid-rewritten",
        "forbid-may-update",
        "forbid-diff-lines",
    ],
)
def test_forbidden_plan_content(text: str, reason: ParseRejectionReason) -> None:
    _expect_reject(reason, lambda: reject_forbidden_plan_content(text))


def test_non_forbidden_trailers_are_allowed() -> None:
    reject_forbidden_plan_content("difficulty: HARD")
    reject_forbidden_plan_content("review_status: complete")
    reject_forbidden_plan_content("ordinary prose about NEW files")


def test_point_id_bounds() -> None:
    assert PointId(POINT_ID_MIN).token == "POINT_1"
    assert PointId(POINT_ID_MAX).token == "POINT_9999"
    _expect_reject(
        ParseRejectionReason.point_id_out_of_range,
        lambda: PointId(0),
    )
    _expect_reject(
        ParseRejectionReason.point_id_out_of_range,
        lambda: PointId(POINT_ID_MAX + 1),
    )
    _expect_reject(
        ParseRejectionReason.malformed_point_id,
        lambda: PointId(True),  # type: ignore[arg-type]  # bool must reject
    )
    _expect_reject(
        ParseRejectionReason.malformed_point_id,
        lambda: PointId.from_token("POINT_01"),
    )
    _expect_reject(
        ParseRejectionReason.point_id_out_of_range,
        lambda: PointId.from_token("POINT_10000"),
    )


# ---------------------------------------------------------------------------
# Ledger parsing
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("submission", "expected"),
    [
        (
            "POINT POINT_1 AGREE looks good",
            [
                (1, Action.AGREE, "looks good", ConcessionClassification.non_concession),
            ],
        ),
        (
            "POINT POINT_1 CONCEDE see POINT POINT_2\nPOINT POINT_2 HOLD keep this",
            [
                (1, Action.CONCEDE, "see POINT POINT_2", ConcessionClassification.cited),
                (2, Action.HOLD, "keep this", ConcessionClassification.non_concession),
            ],
        ),
        (
            "POINT POINT_3 CONCEDE no citation here",
            [
                (3, Action.CONCEDE, "no citation here", ConcessionClassification.fold),
            ],
        ),
        (
            "POINT POINT_1 AGREE reason  with  spaces",
            [
                (
                    1,
                    Action.AGREE,
                    "reason  with  spaces",
                    ConcessionClassification.non_concession,
                ),
            ],
        ),
    ],
    ids=[
        "ledger-single-agree",
        "ledger-cited-and-hold",
        "ledger-fold-concede",
        "ledger-reason-internal-spaces",
    ],
)
def test_ledger_accepted_rows(
    submission: str,
    expected: list[tuple[int, Action, str, ConcessionClassification]],
) -> None:
    parsed = parse_slot_ledger(submission)
    assert len(parsed.rows) == len(expected)
    for row, (number, action, reason, concession) in zip(
        parsed.rows, expected, strict=True
    ):
        assert row.point_id.number == number
        assert row.action is action
        assert row.reason == reason
        assert row.concession is concession


@pytest.mark.parametrize(
    ("submission", "reason"),
    [
        ("", ParseRejectionReason.empty_submission),
        ("POINT POINT_1 AGREE ok\n", ParseRejectionReason.blank_row),
        ("\nPOINT POINT_1 AGREE ok", ParseRejectionReason.blank_row),
        ("POINT POINT_1 AGREE ok\n\nPOINT POINT_2 AGREE ok", ParseRejectionReason.blank_row),
        ("POINT POINT_1 AGREE ok\r", ParseRejectionReason.forbidden_character),
        ("POINT POINT_1 AGREE\tok", ParseRejectionReason.forbidden_character),
        ("POINT POINT_1 AGREE ok\x00", ParseRejectionReason.forbidden_character),
        (" POINT POINT_1 AGREE ok", ParseRejectionReason.leading_or_trailing_whitespace),
        ("POINT POINT_1 AGREE ok ", ParseRejectionReason.leading_or_trailing_whitespace),
        ("POINT  POINT_1 AGREE ok", ParseRejectionReason.repeated_separator_spaces),
        ("POINT POINT_1  AGREE ok", ParseRejectionReason.repeated_separator_spaces),
        ("NOT A ROW", ParseRejectionReason.malformed_row),
        ("POINT POINT_1 ok", ParseRejectionReason.malformed_row),
        ("POINT POINT_1 YES no", ParseRejectionReason.unknown_action),
        ("POINT POINT_1 AGREE", ParseRejectionReason.malformed_row),
        ("POINT POINT_1 AGREE ", ParseRejectionReason.empty_reason),
        ("POINT POINT_X AGREE ok", ParseRejectionReason.malformed_point_id),
        ("POINT POINT_0 AGREE ok", ParseRejectionReason.malformed_point_id),
        ("POINT POINT_10000 AGREE ok", ParseRejectionReason.point_id_out_of_range),
        (
            "POINT POINT_1 AGREE a\nPOINT POINT_1 HOLD b",
            ParseRejectionReason.duplicate_point_id,
        ),
        (
            "POINT POINT_1 AGREE ### NEW: x.py",
            ParseRejectionReason.forbidden_plan_content,
        ),
        (
            "POINT POINT_1 HOLD diff_lines: 9",
            ParseRejectionReason.forbidden_plan_content,
        ),
    ],
    ids=[
        "reject-empty",
        "reject-trailing-blank",
        "reject-leading-blank",
        "reject-middle-blank",
        "reject-cr",
        "reject-tab",
        "reject-nul",
        "reject-leading-ws",
        "reject-trailing-ws",
        "reject-double-space-point",
        "reject-double-space-action",
        "reject-malformed",
        "reject-missing-reason-token",
        "reject-unknown-action",
        "reject-no-reason-field",
        "reject-empty-reason",
        "reject-bad-point",
        "reject-point-zero",
        "reject-point-over",
        "reject-duplicate-point",
        "reject-plan-heading",
        "reject-diff-lines",
    ],
)
def test_ledger_rejection_classes(
    submission: str, reason: ParseRejectionReason
) -> None:
    _expect_reject(reason, lambda: parse_slot_ledger(submission))


# ---------------------------------------------------------------------------
# Citations and concessions
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("action", "reason", "expected"),
    [
        (Action.AGREE, "POINT POINT_1", ConcessionClassification.non_concession),
        (Action.HOLD, "[[artifact:docs/x.md]]", ConcessionClassification.non_concession),
        (Action.CONCEDE, "see POINT POINT_1 please", ConcessionClassification.cited),
        (Action.CONCEDE, "see POINT POINT_9999", ConcessionClassification.cited),
        (
            Action.CONCEDE,
            f"see {ARTIFACT_CITATION_PREFIX}docs/x.md{ARTIFACT_CITATION_SUFFIX}",
            ConcessionClassification.cited,
        ),
        (Action.CONCEDE, "no citation", ConcessionClassification.fold),
        (Action.CONCEDE, "POINT POINT_0 bad", ConcessionClassification.fold),
        (Action.CONCEDE, "POINTPOINT_1 glued", ConcessionClassification.fold),
        (Action.CONCEDE, "xPOINT POINT_1", ConcessionClassification.fold),
        (Action.CONCEDE, "POINT POINT_1x", ConcessionClassification.fold),
        (Action.CONCEDE, "[[artifact:/abs.md]]", ConcessionClassification.fold),
        (Action.CONCEDE, "[[artifact:../x.md]]", ConcessionClassification.fold),
        (Action.CONCEDE, "[[artifact:]]", ConcessionClassification.fold),
        (Action.CONCEDE, "[artifact:docs/x.md]", ConcessionClassification.fold),
        (Action.CONCEDE, "POINT POINT_1 and more", ConcessionClassification.cited),
    ],
    ids=[
        "agree-ignores-cite",
        "hold-ignores-artifact",
        "concede-point-cited",
        "concede-point-max",
        "concede-artifact-cited",
        "concede-uncited-fold",
        "concede-point-zero-fold",
        "concede-glued-fold",
        "concede-prefix-alnum-fold",
        "concede-suffix-alnum-fold",
        "concede-abs-artifact-fold",
        "concede-parent-artifact-fold",
        "concede-empty-artifact-fold",
        "concede-near-miss-bracket-fold",
        "concede-point-cited-trailing",
    ],
)
def test_concession_matrix(
    action: Action, reason: str, expected: ConcessionClassification
) -> None:
    assert classify_concession(action, reason) is expected


def test_uncited_concession_retains_original_reason() -> None:
    parsed = parse_slot_ledger("POINT POINT_1 CONCEDE original fold reason")
    row = parsed.rows[0]
    assert row.concession is ConcessionClassification.fold
    assert row.reason == "original fold reason"


# ---------------------------------------------------------------------------
# Fingerprints
# ---------------------------------------------------------------------------


def test_fingerprint_nfkc_and_shape() -> None:
    # U+FB01 LATIN SMALL LIGATURE FI normalizes to "fi" under NFKC.
    ligature = fingerprint_reason("ﬁ")
    plain = fingerprint_reason("fi")
    assert ligature == plain
    assert len(ligature.value) == FINGERPRINT_HEX_LENGTH
    assert ligature.value == ligature.value.lower()
    assert all(ch in "0123456789abcdef" for ch in ligature.value)


def test_fingerprint_replacement_order_independence() -> None:
    reason = "prefix-ab-suffix"
    left = fingerprint_reason(reason, run_local_values=["a", "ab"])
    right = fingerprint_reason(reason, run_local_values=["ab", "a"])
    assert left == right
    mapped_a = fingerprint_reason(
        reason, run_local_values={"z": "a", "y": "ab"}
    )
    mapped_b = fingerprint_reason(
        reason, run_local_values={"y": "ab", "z": "a"}
    )
    assert mapped_a == mapped_b == left


def test_fingerprint_overlapping_and_duplicate_needles() -> None:
    reason = "aaaa"
    with_dupes = fingerprint_reason(reason, run_local_values=["aa", "aa", "a"])
    without = fingerprint_reason(reason, run_local_values=["aa", "a"])
    assert with_dupes == without


def test_fingerprint_excludes_ambient_unless_supplied() -> None:
    base = fingerprint_reason("stable text")
    # Supplying path/run tokens changes the digest only when they appear.
    altered = fingerprint_reason(
        "stable text with /tmp/run and run-9",
        run_local_values={"/tmp/run": "/tmp/run", "run-9": "run-9"},
    )
    assert base != altered
    # Same reason without those substrings ignores unused needles.
    unused = fingerprint_reason(
        "stable text",
        run_local_values={"/tmp/run": "/tmp/run", "run-9": "run-9"},
    )
    assert unused == base


def test_fingerprint_empty_needle_rejected() -> None:
    _expect_reject(
        ParseRejectionReason.empty_replacement_needle,
        lambda: normalize_reason_for_fingerprint("x", run_local_values=[""]),
    )
    _expect_reject(
        ParseRejectionReason.empty_replacement_needle,
        lambda: fingerprint_reason("x", run_local_values={"": ""}),
    )


def test_forged_binding_fingerprint_rejected() -> None:
    ledger = _agree_ledger(1)
    forged = (ReasonFingerprint("0" * FINGERPRINT_HEX_LENGTH),)
    _expect_reject(
        ParseRejectionReason.fingerprint_mismatch,
        lambda: _binding(Participant.cursor, ledger, fingerprints=forged),
    )


# ---------------------------------------------------------------------------
# Round assembly and resolution
# ---------------------------------------------------------------------------


def test_round_construction_happy_path_and_ceiling() -> None:
    ledger = _agree_ledger(1, 2)
    bindings = [
        _binding(Participant.cursor, ledger),
        _binding(Participant.codex, ledger),
        _binding(Participant.claude, ledger),
    ]
    round_state = _round(RoundNumber.ROUND_1, bindings)
    assert round_state.live_slots == SLOT_ORDER
    assert round_state.point_ids == (PointId(1), PointId(2))


def test_one_slot_below_live_panel_floor() -> None:
    ledger = _agree_ledger(1)
    _expect_reject(
        ParseRejectionReason.below_live_panel_floor,
        lambda: _round(
            RoundNumber.ROUND_1,
            [_binding(Participant.cursor, ledger)],
        ),
    )


def test_above_live_panel_ceiling() -> None:
    ledger = _agree_ledger(1)
    # Four bindings exceed LIVE_PANEL_MAXIMUM (3); duplicate-slot ordering
    # also fails, so build four distinct by repeating a legal slot illegally.
    bindings = [
        _binding(Participant.cursor, ledger),
        _binding(Participant.codex, ledger),
        _binding(Participant.claude, ledger),
        _binding(Participant.cursor, ledger),
    ]
    _expect_reject(
        ParseRejectionReason.above_live_panel_ceiling,
        lambda: _round(RoundNumber.ROUND_1, bindings),
    )


def test_point_universe_mismatch_and_empty() -> None:
    left = _agree_ledger(1, 2)
    right = _agree_ledger(1, 3)
    _expect_reject(
        ParseRejectionReason.point_universe_mismatch,
        lambda: _round(
            RoundNumber.ROUND_1,
            [
                _binding(Participant.cursor, left),
                _binding(Participant.codex, right),
            ],
        ),
    )
    # Empty universe via new_proposal.
    _expect_reject(
        ParseRejectionReason.empty_point_universe,
        lambda: new_proposal(()),
    )


def test_duplicate_points_in_universe_rejected() -> None:
    _expect_reject(
        ParseRejectionReason.duplicate_point_id,
        lambda: new_proposal((PointId(1), PointId(1))),
    )


def test_invalid_slot_ordering_rejected() -> None:
    ledger = _agree_ledger(1)
    _expect_reject(
        ParseRejectionReason.invalid_slot_ordering,
        lambda: _round(
            RoundNumber.ROUND_1,
            [
                _binding(Participant.codex, ledger),
                _binding(Participant.cursor, ledger),
            ],
        ),
    )


@pytest.mark.parametrize(
    ("rows", "expected"),
    [
        (
            [
                LedgerRow(
                    PointId(1),
                    Action.AGREE,
                    "a",
                    ConcessionClassification.non_concession,
                ),
                LedgerRow(
                    PointId(1),
                    Action.AGREE,
                    "b",
                    ConcessionClassification.non_concession,
                ),
            ],
            PointResolution.AGREED,
        ),
        (
            [
                LedgerRow(
                    PointId(1),
                    Action.AGREE,
                    "a",
                    ConcessionClassification.non_concession,
                ),
                LedgerRow(
                    PointId(1),
                    Action.CONCEDE,
                    "see POINT POINT_1",
                    ConcessionClassification.cited,
                ),
            ],
            PointResolution.CONCEDED,
        ),
        (
            [
                LedgerRow(
                    PointId(1),
                    Action.CONCEDE,
                    "fold",
                    ConcessionClassification.fold,
                ),
                LedgerRow(
                    PointId(1),
                    Action.AGREE,
                    "a",
                    ConcessionClassification.non_concession,
                ),
            ],
            PointResolution.FOLDED,
        ),
        (
            [
                LedgerRow(
                    PointId(1),
                    Action.HOLD,
                    "h",
                    ConcessionClassification.non_concession,
                ),
                LedgerRow(
                    PointId(1),
                    Action.AGREE,
                    "a",
                    ConcessionClassification.non_concession,
                ),
            ],
            PointResolution.HELD,
        ),
    ],
    ids=["resolve-agreed", "resolve-conceded", "resolve-folded", "resolve-held"],
)
def test_resolution_matrix(
    rows: list[LedgerRow], expected: PointResolution
) -> None:
    assert resolve_point(rows) is expected
    assert slot_closes_point(rows[0]) is (
        rows[0].action is Action.AGREE
        or (
            rows[0].action is Action.CONCEDE
            and rows[0].concession is ConcessionClassification.cited
        )
    )


def test_point_universe_order_continues_across_bindings_and_rounds() -> None:
    points = (PointId(2), PointId(1))
    proposal = new_proposal(points)
    assert proposal.point_universe == points
    ledger = _ledger_from_specs(
        [
            (2, Action.AGREE, "second first"),
            (1, Action.AGREE, "first second"),
        ]
    )
    round1 = _two_slot_round(RoundNumber.ROUND_1, ledger)
    assert round1.point_ids == points
    converged = transition(
        proposal, TransitionAction.SUBMIT_ROUND, round_state=round1
    )
    assert converged.terminal_outcome is TerminalOutcome.CONVERGED
    assert converged.point_universe == points
    assert converged.rounds[0].point_ids == points


def test_resolve_round_points_and_unresolved() -> None:
    ledger = _mixed_hold_agree("hold")
    round_state = _two_slot_round(RoundNumber.ROUND_1, ledger)
    resolutions = resolve_round_points(round_state)
    assert resolutions[PointId(1)] is PointResolution.HELD
    assert resolutions[PointId(2)] is PointResolution.AGREED
    assert unresolved_points(round_state) == (PointId(1),)
    assert round_is_fully_resolved(round_state) is False


# ---------------------------------------------------------------------------
# Stalemate detection
# ---------------------------------------------------------------------------


def test_stalemate_two_and_three_matching_holds() -> None:
    hold = "unchanged hold text"
    proposal = new_proposal((PointId(1),))
    ledger = _hold_ledger(hold, 1)
    earlier = _two_slot_round(RoundNumber.ROUND_1, ledger)
    later = _two_slot_round(RoundNumber.ROUND_2, ledger)
    detection = detect_stalemate_disputes(proposal, earlier, later)
    assert detection.status is StalemateDetectionStatus.COMPLETED
    assert len(detection.disputes) == 1
    assert detection.disputes[0].holding_slots == (
        Participant.cursor,
        Participant.codex,
    )

    three = _round(
        RoundNumber.ROUND_1,
        [
            _binding(Participant.cursor, ledger),
            _binding(Participant.codex, ledger),
            _binding(Participant.claude, ledger),
        ],
    )
    three_later = _round(
        RoundNumber.ROUND_2,
        [
            _binding(Participant.cursor, ledger),
            _binding(Participant.codex, ledger),
            _binding(Participant.claude, ledger),
        ],
    )
    detection3 = detect_stalemate_disputes(proposal, three, three_later)
    assert detection3.disputes[0].holding_slots == SLOT_ORDER


def test_stalemate_one_matching_slot_is_empty_completed() -> None:
    proposal = new_proposal((PointId(1),))
    cursor_hold = _hold_ledger("same", 1)
    codex_hold = _hold_ledger("same", 1)
    earlier = _round(
        RoundNumber.ROUND_1,
        [
            _binding(Participant.cursor, cursor_hold),
            _binding(Participant.codex, codex_hold),
        ],
    )
    later_codex = _ledger_from_specs([(1, Action.AGREE, "changed mind")])
    later = _round(
        RoundNumber.ROUND_2,
        [
            _binding(Participant.cursor, cursor_hold),
            _binding(Participant.codex, later_codex),
        ],
    )
    detection = detect_stalemate_disputes(proposal, earlier, later)
    assert detection.status is StalemateDetectionStatus.COMPLETED
    assert detection.disputes == ()


def test_stalemate_changed_reason_or_action_skips_dispute() -> None:
    proposal = new_proposal((PointId(1),))
    earlier = _two_slot_round(RoundNumber.ROUND_1, _hold_ledger("v1", 1))
    later = _two_slot_round(RoundNumber.ROUND_2, _hold_ledger("v2", 1))
    detection = detect_stalemate_disputes(proposal, earlier, later)
    assert detection.status is StalemateDetectionStatus.COMPLETED
    assert detection.disputes == ()


def test_stalemate_membership_changed_distinct_from_empty() -> None:
    proposal = new_proposal((PointId(1),))
    ledger = _hold_ledger("same", 1)
    earlier = _two_slot_round(RoundNumber.ROUND_1, ledger)
    later = _round(
        RoundNumber.ROUND_2,
        [
            _binding(Participant.cursor, ledger),
            _binding(Participant.claude, ledger),
        ],
    )
    detection = detect_stalemate_disputes(proposal, earlier, later)
    assert detection.status is StalemateDetectionStatus.MEMBERSHIP_CHANGED
    assert detection.disputes == ()


def test_stalemate_nonadjacent_and_forged_fingerprints() -> None:
    proposal = new_proposal((PointId(1),))
    ledger = _hold_ledger("same", 1)
    r1 = _two_slot_round(RoundNumber.ROUND_1, ledger)
    # Non-adjacent: both ROUND_1.
    _expect_reject(
        ParseRejectionReason.nonadjacent_rounds,
        lambda: detect_stalemate_disputes(proposal, r1, r1),
    )
    forged_binding = SlotLedgerBinding(
        slot=Participant.cursor,
        ledger=ledger,
        fingerprints=(fingerprint_reason("same"),),
    )
    # Build a later round, then mutate proposal run-local so revalidation fails.
    later = _two_slot_round(RoundNumber.ROUND_2, ledger)
    mismatched = new_proposal(
        (PointId(1),),
        run_local_values={"needle": "same"},
    )
    _expect_reject(
        ParseRejectionReason.fingerprint_mismatch,
        lambda: detect_stalemate_disputes(mismatched, r1, later),
    )
    del forged_binding  # constructed only to prove binding API


def test_stalemate_partial_dispute_coverage() -> None:
    # Point 1 qualifies; point 2 does not. Detection still completes with one dispute.
    proposal = new_proposal((PointId(1), PointId(2)))
    earlier_ledger = _ledger_from_specs(
        [
            (1, Action.HOLD, "stable"),
            (2, Action.HOLD, "moves"),
        ]
    )
    later_ledger = _ledger_from_specs(
        [
            (1, Action.HOLD, "stable"),
            (2, Action.HOLD, "moved"),
        ]
    )
    earlier = _two_slot_round(RoundNumber.ROUND_1, earlier_ledger)
    later = _two_slot_round(RoundNumber.ROUND_2, later_ledger)
    detection = detect_stalemate_disputes(proposal, earlier, later)
    assert detection.status is StalemateDetectionStatus.COMPLETED
    assert [d.point_id for d in detection.disputes] == [PointId(1)]


def test_dispute_requires_two_holding_slots() -> None:
    _expect_reject(
        ParseRejectionReason.below_live_panel_floor,
        lambda: Dispute(point_id=PointId(1), holding_slots=(Participant.cursor,)),
    )


def test_membership_changed_cannot_carry_disputes() -> None:
    _expect_reject(
        ParseRejectionReason.invalid_proposal_state,
        lambda: StalemateDetection(
            status=StalemateDetectionStatus.MEMBERSHIP_CHANGED,
            disputes=(
                Dispute(
                    point_id=PointId(1),
                    holding_slots=(Participant.cursor, Participant.codex),
                ),
            ),
        ),
    )


# ---------------------------------------------------------------------------
# Adjudication
# ---------------------------------------------------------------------------


def test_selected_and_split_adjudication() -> None:
    selected = SelectedAdjudication(PointId(1), "take cursor position")
    assert selected.decision is AdjudicationDecision.SELECTED
    split = SplitAdjudication(PointId(1), "pos a", "pos b")
    assert split.decision is AdjudicationDecision.SPLIT
    _expect_reject(
        ParseRejectionReason.malformed_adjudication,
        lambda: SplitAdjudication(PointId(1), "same", "same"),
    )
    _expect_reject(
        ParseRejectionReason.malformed_adjudication,
        lambda: SelectedAdjudication(PointId(1), ""),
    )
    _expect_reject(
        ParseRejectionReason.malformed_adjudication,
        lambda: SelectedAdjudication(PointId(1), " leading"),
    )
    _expect_reject(
        ParseRejectionReason.malformed_adjudication,
        lambda: SelectedAdjudication(PointId(1), "has\nnewline"),
    )
    _expect_reject(
        ParseRejectionReason.forbidden_plan_content,
        lambda: SelectedAdjudication(PointId(1), "### NEW: x.py"),
    )


def test_adjudication_coverage_and_outcomes() -> None:
    unresolved = (PointId(1), PointId(2))
    selected_set = (
        SelectedAdjudication(PointId(1), "a"),
        SelectedAdjudication(PointId(2), "b"),
    )
    assert (
        validate_adjudication_set(unresolved, selected_set)
        is TerminalOutcome.CONVERGED
    )
    split_set = (
        SelectedAdjudication(PointId(1), "a"),
        SplitAdjudication(PointId(2), "b1", "b2"),
    )
    assert (
        validate_adjudication_set(unresolved, split_set)
        is TerminalOutcome.BOTH_VIABLE
    )
    _expect_reject(
        ParseRejectionReason.malformed_adjudication,
        lambda: validate_adjudication_set((), selected_set),
    )
    _expect_reject(
        ParseRejectionReason.incomplete_adjudication_coverage,
        lambda: validate_adjudication_set(
            unresolved, (SelectedAdjudication(PointId(1), "a"),)
        ),
    )
    _expect_reject(
        ParseRejectionReason.malformed_adjudication,
        lambda: validate_adjudication_set(
            unresolved,
            (
                SelectedAdjudication(PointId(1), "a"),
                SelectedAdjudication(PointId(3), "foreign"),
            ),
        ),
    )
    _expect_reject(
        ParseRejectionReason.malformed_adjudication,
        lambda: validate_adjudication_set(
            unresolved,
            (
                SelectedAdjudication(PointId(1), "a"),
                SelectedAdjudication(PointId(1), "dup"),
            ),
        ),
    )
    _expect_reject(
        ParseRejectionReason.duplicate_point_id,
        lambda: validate_adjudication_set(
            (PointId(1), PointId(1)),
            (
                SelectedAdjudication(PointId(1), "a"),
                SelectedAdjudication(PointId(1), "b"),
            ),
        ),
    )


# ---------------------------------------------------------------------------
# Transition matrix
# ---------------------------------------------------------------------------


def test_legal_edge_count_and_illegal_pairs() -> None:
    phases = list(NonterminalPhase)
    actions = list(TransitionAction)
    assert len(phases) * len(actions) == 16
    assert len(_LEGAL_EDGES) == 9
    illegal = {
        (phase, action)
        for phase in phases
        for action in actions
        if (phase, action) not in _LEGAL_EDGES
    }
    assert len(illegal) == 7


@pytest.mark.parametrize(
    ("phase", "action"),
    sorted(_LEGAL_EDGES, key=lambda item: (item[0].value, item[1].value)),
    ids=[
        f"{phase.value}+{action.value}"
        for phase, action in sorted(
            _LEGAL_EDGES, key=lambda item: (item[0].value, item[1].value)
        )
    ],
)
def test_each_legal_edge(
    phase: NonterminalPhase, action: TransitionAction
) -> None:
    if phase is NonterminalPhase.BLIND_ROUND_1 and action is TransitionAction.ABORT:
        proposal = new_proposal((PointId(1),))
        out = transition(proposal, TransitionAction.ABORT)
        assert out.terminal_outcome is TerminalOutcome.ABORTED
        assert out.phase is None
        return
    if phase is NonterminalPhase.BLIND_ROUND_1 and action is TransitionAction.SUBMIT_ROUND:
        proposal = new_proposal((PointId(1),))
        ledger = _agree_ledger(1)
        out = transition(
            proposal,
            TransitionAction.SUBMIT_ROUND,
            round_state=_two_slot_round(RoundNumber.ROUND_1, ledger),
        )
        assert out.terminal_outcome is TerminalOutcome.CONVERGED
        return
    if phase is NonterminalPhase.ROUND_2 and action is TransitionAction.ABORT:
        proposal = _proposal_after_round1_holds()
        assert proposal.phase is NonterminalPhase.ROUND_2
        out = transition(proposal, TransitionAction.ABORT)
        assert out.terminal_outcome is TerminalOutcome.ABORTED
        return
    if phase is NonterminalPhase.ROUND_2 and action is TransitionAction.SUBMIT_ROUND:
        proposal = _proposal_after_round1_holds()
        ledger = _mixed_hold_agree("stable hold reason")
        out = transition(
            proposal,
            TransitionAction.SUBMIT_ROUND,
            round_state=_two_slot_round(RoundNumber.ROUND_2, ledger),
        )
        assert out.phase is NonterminalPhase.AWAITING_ADJUDICATION
        assert out.disputes
        return
    if (
        phase is NonterminalPhase.AWAITING_ADJUDICATION
        and action is TransitionAction.DECLARE_STALEMATE
    ):
        proposal = _proposal_awaiting_adjudication()
        out = transition(proposal, TransitionAction.DECLARE_STALEMATE)
        assert out.terminal_outcome is TerminalOutcome.STALEMATE
        return
    if (
        phase is NonterminalPhase.AWAITING_ADJUDICATION
        and action is TransitionAction.ADJUDICATE
    ):
        proposal = _proposal_awaiting_adjudication()
        out = transition(
            proposal,
            TransitionAction.ADJUDICATE,
            adjudications=(SelectedAdjudication(PointId(1), "pick a"),),
        )
        assert out.terminal_outcome is TerminalOutcome.CONVERGED
        return
    if (
        phase is NonterminalPhase.AWAITING_ADJUDICATION
        and action is TransitionAction.ABORT
    ):
        proposal = _proposal_awaiting_adjudication()
        out = transition(proposal, TransitionAction.ABORT)
        assert out.terminal_outcome is TerminalOutcome.ABORTED
        assert out.disputes == ()
        return
    if phase is NonterminalPhase.UNCONVERGED and action is TransitionAction.ADJUDICATE:
        proposal = _proposal_unconverged()
        assert proposal.phase is NonterminalPhase.UNCONVERGED
        out = transition(
            proposal,
            TransitionAction.ADJUDICATE,
            adjudications=(
                SplitAdjudication(PointId(1), "left", "right"),
            ),
        )
        assert out.terminal_outcome is TerminalOutcome.BOTH_VIABLE
        return
    if phase is NonterminalPhase.UNCONVERGED and action is TransitionAction.ABORT:
        proposal = _proposal_unconverged()
        out = transition(proposal, TransitionAction.ABORT)
        assert out.terminal_outcome is TerminalOutcome.ABORTED
        return
    raise AssertionError(f"unhandled legal edge {phase!s}+{action!s}")


@pytest.mark.parametrize(
    ("phase", "action"),
    [
        (NonterminalPhase.BLIND_ROUND_1, TransitionAction.DECLARE_STALEMATE),
        (NonterminalPhase.BLIND_ROUND_1, TransitionAction.ADJUDICATE),
        (NonterminalPhase.ROUND_2, TransitionAction.DECLARE_STALEMATE),
        (NonterminalPhase.ROUND_2, TransitionAction.ADJUDICATE),
        (NonterminalPhase.AWAITING_ADJUDICATION, TransitionAction.SUBMIT_ROUND),
        (NonterminalPhase.UNCONVERGED, TransitionAction.SUBMIT_ROUND),
        (NonterminalPhase.UNCONVERGED, TransitionAction.DECLARE_STALEMATE),
    ],
    ids=[
        "illegal-blind+stalemate",
        "illegal-blind+adjudicate",
        "illegal-r2+stalemate",
        "illegal-r2+adjudicate",
        "illegal-await+submit",
        "illegal-unconv+submit",
        "illegal-unconv+stalemate",
    ],
)
def test_illegal_edges_reject_before_payload(
    phase: NonterminalPhase, action: TransitionAction
) -> None:
    if phase is NonterminalPhase.BLIND_ROUND_1:
        proposal = new_proposal((PointId(1),))
    elif phase is NonterminalPhase.ROUND_2:
        proposal = _proposal_after_round1_holds()
    elif phase is NonterminalPhase.AWAITING_ADJUDICATION:
        proposal = _proposal_awaiting_adjudication()
    else:
        proposal = _proposal_unconverged()
    assert proposal.phase is phase
    # Supply a plausible payload that would be valid on a legal edge; the
    # illegal edge must still reject as illegal_transition first.
    kwargs: dict[str, object] = {}
    if action is TransitionAction.SUBMIT_ROUND:
        kwargs["round_state"] = _two_slot_round(
            RoundNumber.ROUND_1, _agree_ledger(1)
        )
    if action is TransitionAction.ADJUDICATE:
        kwargs["adjudications"] = (SelectedAdjudication(PointId(1), "x"),)
    _expect_reject(
        ParseRejectionReason.illegal_transition,
        lambda: transition(proposal, action, **kwargs),  # type: ignore[arg-type]
    )


def test_terminal_immutability() -> None:
    proposal = new_proposal((PointId(1),))
    ledger = _agree_ledger(1)
    terminal = transition(
        proposal,
        TransitionAction.SUBMIT_ROUND,
        round_state=_two_slot_round(RoundNumber.ROUND_1, ledger),
    )
    assert terminal.terminal_outcome is TerminalOutcome.CONVERGED
    for action in TransitionAction:
        _expect_reject(
            ParseRejectionReason.illegal_transition,
            lambda action=action: transition(terminal, action),
        )


def test_submit_round_payload_misuse_and_wrong_round() -> None:
    proposal = new_proposal((PointId(1),))
    ledger = _agree_ledger(1)
    round1 = _two_slot_round(RoundNumber.ROUND_1, ledger)
    _expect_reject(
        ParseRejectionReason.illegal_transition,
        lambda: transition(
            proposal,
            TransitionAction.SUBMIT_ROUND,
            round_state=round1,
            adjudications=(SelectedAdjudication(PointId(1), "x"),),
        ),
    )
    _expect_reject(
        ParseRejectionReason.illegal_transition,
        lambda: transition(proposal, TransitionAction.SUBMIT_ROUND),
    )
    wrong = _two_slot_round(RoundNumber.ROUND_2, ledger)
    _expect_reject(
        ParseRejectionReason.invalid_round_number,
        lambda: transition(
            proposal, TransitionAction.SUBMIT_ROUND, round_state=wrong
        ),
    )


def test_abort_payload_must_be_empty() -> None:
    proposal = new_proposal((PointId(1),))
    _expect_reject(
        ParseRejectionReason.illegal_transition,
        lambda: transition(
            proposal,
            TransitionAction.ABORT,
            round_state=_two_slot_round(RoundNumber.ROUND_1, _agree_ledger(1)),
        ),
    )


def test_round2_convergence_without_disputes() -> None:
    points = (PointId(1),)
    proposal = new_proposal(points)
    hold = _hold_ledger("temp", 1)
    after_r1 = transition(
        proposal,
        TransitionAction.SUBMIT_ROUND,
        round_state=_two_slot_round(RoundNumber.ROUND_1, hold),
    )
    agree = _agree_ledger(1)
    converged = transition(
        after_r1,
        TransitionAction.SUBMIT_ROUND,
        round_state=_two_slot_round(RoundNumber.ROUND_2, agree),
    )
    assert converged.terminal_outcome is TerminalOutcome.CONVERGED
    assert converged.phase is None


# ---------------------------------------------------------------------------
# Doc parity (single intentional filesystem read)
# ---------------------------------------------------------------------------


_DOC_PINNED_NAMES: tuple[str, ...] = (
    "PROTOCOL_VERSION",
    "FINGERPRINT_ALGORITHM_VERSION",
    "FINGERPRINT_HEX_LENGTH",
    "ROUND_LIMIT",
    "POINT_ID_MIN",
    "POINT_ID_MAX",
    "SLOT_ORDER",
    "LIVE_PANEL_MINIMUM",
    "LIVE_PANEL_MAXIMUM",
    "ACTION_TOKENS",
    "ARTIFACT_CITATION_PREFIX",
    "ARTIFACT_CITATION_SUFFIX",
    "LEDGER_POINT_TOKEN",
    "POINT_ID_PREFIX",
    "NonterminalPhase",
    "TransitionAction",
)


@pytest.mark.parametrize("name", _DOC_PINNED_NAMES, ids=_DOC_PINNED_NAMES)
def test_doc_parity_constant_names(name: str) -> None:
    doc = _PROTOCOL_DOC.read_text(encoding="utf-8")
    assert name in doc


def test_doc_parity_cheap_values_and_token_sets() -> None:
    doc = _PROTOCOL_DOC.read_text(encoding="utf-8")
    assert f"`FINGERPRINT_HEX_LENGTH` (`{FINGERPRINT_HEX_LENGTH}`)" in doc
    assert f"`ROUND_LIMIT` (`{ROUND_LIMIT}`)" in doc
    assert f"`POINT_ID_MIN` (`{POINT_ID_MIN}`)" in doc
    assert f"`POINT_ID_MAX` (`{POINT_ID_MAX}`)" in doc
    assert f"`LIVE_PANEL_MINIMUM` (`{LIVE_PANEL_MINIMUM}`)" in doc
    assert f"`LIVE_PANEL_MAXIMUM` (`{LIVE_PANEL_MAXIMUM}`)" in doc
    for slot in SLOT_ORDER:
        assert f"`{slot}`" in doc
    for action in ACTION_TOKENS:
        assert f"`{action}`" in doc
    assert "python/larch/debate/protocol.py" in doc
