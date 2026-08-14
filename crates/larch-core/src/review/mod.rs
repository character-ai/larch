//! Typed review-domain contracts shared by Rust command owners.
//!
//! Pure review models live here so each command cutover can reuse one tested
//! owner while leaving side effects at its CLI boundary.

mod dispatch;
mod findings_ledger;
mod pipeline;
mod tally_engine;
mod types;
mod voting;

pub use dispatch::{
    DispatchError, VOTER_SLOT_COUNT, VoterOutputBinding, VoterPathsFilePolicy, VoterRowLayout,
    VoterSlotPolicy, VoterSlotState, optional_positive_float, parse_rate_status, path_for_wire,
    resolved_manifest_model, voter_states_from_bindings, voter_status_rows,
    with_manifest_attribution,
};
pub use findings_ledger::{
    LEDGER_BASENAME, LEDGER_COLUMNS, LedgerError, LedgerRow, ledger_path, ledger_root,
    parse as parse_ledger, prompt_section, read as read_ledger, render as render_ledger,
    replace_round, write_round,
};
pub use pipeline::{
    GATHER_CONTEXT_USAGE, GatherContextArgumentError, GatherContextArguments, GatherContextMode,
    GatherContextParse, description_path_matches, description_tokens, normalize_output_base,
    parse_collector_records, parse_gather_context_arguments, positive_integer,
    valid_relative_review_path,
};
pub use tally_engine::{ItemAdjudicationResult, ItemContext, VoteCell, adjudicate_item, run_items};
pub use types::{
    BoundaryMode, CanonicalHeading, CompatibilityBoundary, FINDING_SCOPE_VALUES, FOCUS_AREA_VALUES,
    Finding, FindingScope, FocusArea, ItemKind, JudgeSeverity, ParsedBlock, ReviewCoreStatus,
    ReviewOrdinal, ReviewVote, code_review_classification_header,
    code_review_classification_required_fields, count_non_security_blocks, finding_dedup_key,
    finding_scope_set, focus_area_set, is_canonical_heading, is_oos_eligible_block,
    is_security_block_text, parse_blocks, parse_canonical_heading, parse_findings,
    parse_findings_text, read_finding_text, render_wire_values,
};
pub use voting::{
    FINDINGS_CLASSIFICATION_HEADER, ParsedJudgeVote, accept_finding,
    accepted_finding_points_from_severities, alias_ballot_id, ballot_blocks, ballot_parse_text,
    classify_oos_result, classify_result, classify_unbounded_result, false_positive_match,
    neutral_high_severity_rescue_to_oos, oos_fileable_from_votes, panel_tier,
    parse_judge_vote_text, reviewer_for_block_text, vote_for_id_text,
};
