//! Design-domain pure logic owned by the #7680 Rust migration.
//!
//! Leaf #8575 ports the plan grammar and plan-quality analysis core. Command
//! registration stays with later leaves.

mod plan_grammar;
mod plan_quality;

pub use plan_grammar::{
    CANONICAL_TRAILER_ORDER, FORCE_PLAN_CONTRACT_ERROR, FIRM_HEADING_KINDS, HEADING_KINDS,
    M1_DEFECT_TOKENS, M2_DEFECT_TOKENS, OPTIONAL_SIZE_TRAILER_KEYS, PLAN_DEFECT_ORDER, TRAILER_KEYS,
    HeadingEvent, HeadingKind, HeadingMatch, PlanTrailers, PlanValidationResult, TrailerKey,
    TrailerMatch, TrailerValue, compose_trailer_lines, grammar_prompt, is_fence_marker,
    iter_firm_headings, iter_heading_events, iter_plan_headings, iter_trailer_lines, match_heading,
    match_trailer_line, parse_final_trailers, terminal_diff_lines, validate_plan_contract,
    validate_plan_facets,
};
pub use plan_quality::{
    HEADER as PLAN_COMMAND_TSV_HEADER, OVERSIZE_OVERRIDE_OPERATOR, PLAN_SIZE_MAX_DIFF_ADDED,
    PLAN_SIZE_MAX_DIFF_LINES, PLAN_SIZE_MAX_FIRM_HEADINGS, PLAN_SIZE_MAX_PLAN_BODY_LINES,
    PLAN_SIZE_MAX_SURFACES, OptionalMetadata, PlanCommandRow, PlanSizeAssessment,
    assess_plan_size, firm_heading_count, firm_heading_paths, parse_optional_metadata,
    parse_plan_commands, plan_surfaces, render_plan_command_tsv, validate_difficulty_metadata,
};
