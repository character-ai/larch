//! Debate-domain pure logic owned by the #8555 Rust migration.
//!
//! Leaf #8597 ports the protocol vocabulary, ledger grammar, concession
//! classification, and fingerprints. Round assembly, resolution, stalemate
//! detection, adjudication records, the transition table, and command
//! registration stay with later leaves.

mod protocol;

pub use protocol::{
    ACTION_AGREE, ACTION_CONCEDE, ACTION_HOLD, ACTION_TOKENS, ARTIFACT_CITATION_PREFIX,
    ARTIFACT_CITATION_SUFFIX, Action, AdjudicationDecision, ConcessionClassification,
    FINGERPRINT_ALGORITHM_VERSION, FINGERPRINT_HEX_LENGTH, LEDGER_POINT_TOKEN, LIVE_PANEL_MAXIMUM,
    LIVE_PANEL_MINIMUM, LedgerRow, NonterminalPhase, POINT_ID_MAX, POINT_ID_MIN, POINT_ID_PREFIX,
    PROTOCOL_VERSION, ParseRejectionReason, ParsedSlotLedger, Participant, PointId,
    PointResolution, ROUND_LIMIT, ReasonFingerprint, RoundNumber, SLOT_ORDER,
    StalemateDetectionStatus, TerminalOutcome, TransitionAction, classify_concession,
    fingerprint_reason, is_valid_artifact_path, is_valid_fingerprint, is_valid_fingerprint_version,
    is_valid_point_token, is_valid_protocol_version, is_valid_slot,
    normalize_reason_for_fingerprint, parse_fingerprint, parse_fingerprint_version,
    parse_protocol_version, parse_slot, parse_slot_ledger, reject_forbidden_plan_content,
};
