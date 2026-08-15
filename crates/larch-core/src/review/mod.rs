//! Typed review-domain contracts shared by Rust command owners.
//!
//! Pure review models live here so each command cutover can reuse one tested
//! owner while leaving side effects at its CLI boundary.

mod collection;
mod dispatch;
mod findings_ledger;
mod pipeline;
mod plan_review;
mod repair;
mod tally_engine;
mod types;
mod voting;

pub use collection::{
    CollectedFinding, CollectionRender, CollectorResultRecord, PanelManifestSlot,
    ReviewerFailureThreshold, ReviewerFailureThresholdInput, ReviewerOutput,
    has_no_findings_sentinel, parse_markdown_findings, parse_threshold_collector_records,
    render_collection, reviewer_failure_threshold,
};
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
    parse_collector_records, parse_gather_context_arguments, parse_legacy_collector_blocks,
    positive_integer, valid_relative_review_path,
};
pub use plan_review::{
    MERGE_KEYS, NON_NIT_CONTINUE_THRESHOLD, PER_REVIEWER_OOS_PROPOSAL_CAP,
    PlanReviewAcceptedFinding, PlanReviewAggregationOutcome, PlanReviewBallotOutcome,
    PlanReviewCollectionOutcome, PlanReviewCollectorRecord, PlanReviewFindingOutput,
    PlanReviewGateBDisplayRow, PlanReviewGateBSeveritySummary, PlanReviewManifestSlot,
    PlanReviewPanelOutcome, PlanReviewReviewerStatus, PlanReviewRoundArtifacts,
    PlanReviewRoundInput, PlanReviewRoundState, PlanReviewRoundSummary,
    PlanReviewStructuredFinding, PlanReviewTallyOutcome, PlanReviewVoterOutcome, ROUND_CAP,
    ROUND_THREE_AUTHORIZATION_CAP, STEP3_NORMALIZE_ALLOW_KEYS, STEP3_ROUND_CARRY_KEYS,
    STRUCTURAL_DIFF_LINE_THRESHOLD, STRUCTURAL_MIN_REVIEW_ROUNDS, STRUCTURAL_PLAN_LINE_THRESHOLD,
    aggregation_ok_for_voting, aggregator_status, all_applied_finding_keys,
    applied_finding_keys_before, classify_plan_review_gate_b, classify_round_loop_status,
    filter_plan_review_gate_b_skipped, merge_already_addressed_finding_keys,
    merge_step3_round_carry_warnings, normalize_collected_findings,
    parse_plan_review_accepted_findings, plan_review_gate_b_display_rows,
    reconciled_reviewer_label, render_reviewer_status_table, render_reviewer_status_tsv,
    replace_applied_finding_keys, reviewer_status_rows, run_plan_review_round, slot_human_label,
    step3_loop_status_to_loop_status, step3_next_action, step3_round_carry_values,
    step3_status_from_loop_status, strip_crlf,
};
pub use repair::{
    RejectedFindingsRound, RepairBatchReport, RepairClassifier, RepairCleanupAction,
    RepairCoderAttempt, RepairCoderInput, RepairCoderResult, RepairCommitOutcome,
    RepairComposition, RepairConvergenceEvidence, RepairCounts, RepairRoundArtifacts,
    RepairRoundInput, RepairRoundState, RepairSnapshotError, RepairSnapshotLayout,
    RepairSnapshotMode, RepairTrackedPath, SnapshotArtifactIdentity, cleanup_plan,
    collect_repair_stage_paths, count_code_review_findings, render_rejected_findings_aggregate,
    render_repair_tally_body, render_scout_manifest_payload, resolve_coder_result,
    resolve_repair_round, safe_patch_name, snapshot_identity_matches, tally_flush_sidecar,
    tracked_delta_paths, untracked_delta_paths, validate_repair_snapshot,
};
pub use tally_engine::{ItemAdjudicationResult, ItemContext, VoteCell, adjudicate_item, run_items};
pub use types::{
    BoundaryMode, CanonicalHeading, CompatibilityBoundary, FINDING_SCOPE_VALUES, FOCUS_AREA_VALUES,
    Finding, FindingScope, FocusArea, ItemKind, JudgeSeverity, ParsedBlock, ReviewCoreStatus,
    ReviewOrdinal, ReviewVote, code_review_classification_header,
    code_review_classification_required_fields, count_non_security_blocks, finding_dedup_key,
    finding_scope_set, focus_area_set, is_canonical_heading, is_oos_eligible_block,
    is_security_block_text, parse_blocks, parse_canonical_heading, parse_findings,
    parse_findings_text, python_str_of_json, read_finding_text, render_wire_values,
};
pub use voting::{
    FINDINGS_CLASSIFICATION_HEADER, ParsedJudgeVote, TallyRecordFields, accept_finding,
    accepted_finding_points_from_classification_fields, accepted_finding_points_from_severities,
    alias_ballot_id, ballot_blocks, ballot_parse_text, classify_oos_result, classify_result,
    classify_unbounded_result, compose_self_review_findings_from_tally_json,
    compose_self_review_findings_jsonl, compose_tally_record_json, false_positive_match,
    grow_reviewer_labels, neutral_high_severity_rescue_to_oos, oos_fileable_from_votes, panel_tier,
    parse_judge_vote_text, proposer_map_item_mismatch, raw_sole_finder_attribution,
    reviewer_for_block_text, scoreboard_scores_from_tsv, split_classification_attribution,
    vote_for_id_text,
};
