//! Debate-domain pure logic owned by the #8555 Rust migration.
//!
//! Leaf #8597 ports the protocol vocabulary, ledger grammar, concession
//! classification, and fingerprints. Leaf #8598 adds round assembly,
//! resolution, stalemate detection, adjudication records, and the proposal
//! transition machine. Command registration stays with later leaves.

mod protocol;
pub mod state;

pub use state::{
    ABSENT_FINGERPRINT, ActiveRound, DropRecord, EXIT_CORRUPT_STATE, EXIT_PERSISTENCE_FAILURE,
    EXIT_STALE_FINGERPRINT, EXIT_VALIDATION, InitializationContext, MailboxEntry, ParticipantSlot,
    RestoreMetadata, STATE_FILENAME, STATE_LOCK_FILENAME, STATE_SCHEMA_VERSION,
    SUPPORTED_STATE_SCHEMA_VERSIONS, StateError, StateErrorClass, StoredState, decode_state,
    encode_state, require_fingerprint, state_with_fingerprint,
};

pub use protocol::{
    ACTION_AGREE, ACTION_CONCEDE, ACTION_HOLD, ACTION_TOKENS, ARTIFACT_CITATION_PREFIX,
    ARTIFACT_CITATION_SUFFIX, Action, AdjudicationDecision, AdjudicationRecord,
    ConcessionClassification, Dispute, FINGERPRINT_ALGORITHM_VERSION, FINGERPRINT_HEX_LENGTH,
    LEDGER_POINT_TOKEN, LIVE_PANEL_MAXIMUM, LIVE_PANEL_MINIMUM, LedgerRow, NonterminalPhase,
    POINT_ID_MAX, POINT_ID_MIN, POINT_ID_PREFIX, PROTOCOL_VERSION, ParseRejectionReason,
    ParsedSlotLedger, Participant, PointId, PointResolution, ProposalState, ROUND_LIMIT,
    ReasonFingerprint, RoundNumber, RoundState, SLOT_ORDER, SelectedAdjudication,
    SlotLedgerBinding, SplitAdjudication, StalemateDetection, StalemateDetectionStatus,
    TerminalOutcome, TransitionAction, classify_concession, detect_stalemate_disputes,
    fingerprint_reason, is_valid_artifact_path, is_valid_fingerprint, is_valid_fingerprint_version,
    is_valid_point_token, is_valid_protocol_version, is_valid_slot, new_proposal,
    normalize_reason_for_fingerprint, parse_fingerprint, parse_fingerprint_version,
    parse_protocol_version, parse_slot, parse_slot_ledger, reject_forbidden_plan_content,
    resolve_point, resolve_round_points, round_is_fully_resolved, slot_closes_point, transition,
    unresolved_points, validate_adjudication_set,
};
