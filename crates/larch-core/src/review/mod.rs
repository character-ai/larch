//! Dormant parity library for Python-owned review commands.
//!
//! This module deliberately registers no CLI command or runtime caller.  It
//! exists so later atomic cutover leaves can consume one tested Rust owner.

mod findings_ledger;
mod tally_engine;
mod types;
mod voting;

pub use findings_ledger::{
    LEDGER_BASENAME, LEDGER_COLUMNS, LedgerError, LedgerRow, ledger_path, ledger_root,
    parse as parse_ledger, prompt_section, read as read_ledger, render as render_ledger,
    replace_round, write_round,
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
    accepted_finding_points_from_severities, classify_oos_result, classify_result,
    neutral_high_severity_rescue_to_oos, oos_fileable_from_votes,
};
