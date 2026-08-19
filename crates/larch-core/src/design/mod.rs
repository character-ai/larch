//! Design-domain pure logic owned by the #7680 Rust migration.
//!
//! Leaf #8575 ports the plan grammar and plan-quality analysis core. Command
//! registration stays with later leaves.

mod plan_grammar;
mod plan_quality;
mod plan_scout;

pub use plan_grammar::{
    CANONICAL_TRAILER_ORDER, FIRM_HEADING_KINDS, FORCE_PLAN_CONTRACT_ERROR, HEADING_KINDS,
    HeadingEvent, HeadingKind, HeadingMatch, M1_DEFECT_TOKENS, M2_DEFECT_TOKENS,
    OPTIONAL_SIZE_TRAILER_KEYS, PLAN_DEFECT_ORDER, PlanTrailers, PlanValidationResult,
    TRAILER_KEYS, TrailerKey, TrailerMatch, TrailerValue, compose_trailer_lines, grammar_prompt,
    is_fence_marker, iter_firm_headings, iter_heading_events, iter_plan_headings,
    iter_trailer_lines, match_heading, match_trailer_line, parse_final_trailers,
    terminal_diff_lines, validate_plan_contract, validate_plan_facets,
};
pub use plan_quality::{
    HEADER as PLAN_COMMAND_TSV_HEADER, OVERSIZE_OVERRIDE_OPERATOR, OptionalMetadata,
    PLAN_SIZE_MAX_DIFF_ADDED, PLAN_SIZE_MAX_DIFF_LINES, PLAN_SIZE_MAX_FIRM_HEADINGS,
    PLAN_SIZE_MAX_PLAN_BODY_LINES, PLAN_SIZE_MAX_SURFACES, PlanCommandRow, PlanSizeAssessment,
    ValidationSummary, assess_plan_size, compose_plan_goals_test, drift_exceeds, drift_ratio_token,
    firm_heading_count, firm_heading_paths, parse_optional_metadata, parse_plan_commands,
    plan_surfaces, render_plan_command_tsv, set_oversize_override_text,
    validate_difficulty_metadata,
};
pub use plan_scout::{
    DynamicArchetype, EMPTY_MANIFEST_TEXT, INVALID_ARCHETYPES_SHAPE, MAX_ARCHETYPE_WEIGHT,
    MAX_CONTEXT_BYTES, MAX_STAGED_BYTES, ManifestResult, PLAN_ONLY_RESERVED,
    REQUIRED_CLOSING_SENTENCE, REVIEW_RESERVED, SCOUT_RAW_RATING_BASENAME, ScoutDifficultySidecar,
    ensure_closing_sentence, extract_valid_fenced_json_text, render_difficulty_sidecar,
    render_manifest, reserved_for_mode, unsafe_plan_delimiter, unsafe_prompt_body,
    unsafe_rationale, unsafe_wrapper_tag, validate_dynamic_manifest,
};
