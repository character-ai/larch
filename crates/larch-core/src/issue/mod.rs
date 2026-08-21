//! Shared Rust issue-domain models.
//!
//! Ports Python `larch.issue.issue_blocks`, the wire subset of
//! `larch.issue.issue_wire`, `larch.issue.title_match`, and the row model in
//! `larch.issue.open_rows`. `crate::report::markdown_block` stays the Markdown
//! block owner; the larch named block is a distinct fail-closed grammar layered
//! above the same shared line primitive.
//!
//! Also provides library parity for Python `larch.issue._ground_truth` and
//! `larch.issue._report`, plus the `larch.issue._util` predicates they share.
//! No command changes owner here: Python keeps the wire commands until their
//! command leaves migrate them, while the backlog analysis, bug-sweep, and
//! learn-from-bugs command leaves consume the analysis core. Rejected-finding
//! and merged-change analyses stay with the research umbrella.

mod body;
mod candidates;
mod deps_audit;
mod ground_truth;
mod input;
mod lease;
mod oos_batch;
mod oos_conflict;
mod oos_disposition;
mod oos_filing;
mod oos_priority;
mod oos_record;
mod report_core;
mod rows;
mod title;
mod triage;
mod umbrella;
mod untrusted;

pub use body::{
    ALLOWED_NAMED_BLOCK_MARKERS, DESIGN_PAUSE_MARKER, MISSING_PLAN_BLOCK, MULTIPLE_PLAN_BLOCKS,
    NamedBlockDefect, NamedBlockError, NamedBlockSpan, NamedBlockWrite, NamedBlockWriteMode,
    PLAN_MARKER, classify_named_block, compose_named_block, is_valid_named_block_marker,
    issue_plan_marker_defect, named_block_marker_allowed, neutralize_named_block_markers,
    parse_named_block, plan_named_block_write, strip_named_block,
};
pub use candidates::{
    CANDIDATE_CAP, CandidateAllocation, CandidateRowDefect, CandidateRowDrop, allocate_candidates,
};
pub use deps_audit::{
    DEPS_GROUPS, DepsEdge, DepsFetchArtifacts, DepsFetchedIssue, DepsIssueMap, DepsLiveIssue,
    DepsMutation, DepsPartialAudit, DepsPlanInputs, GH_ERROR_CHARS, MUTATION_ERROR_CHARS,
    deps_compact_json, deps_edge_would_cycle, deps_explicit_refs, deps_failed_fetch,
    deps_fetch_artifacts, deps_flat_error, deps_group_for_title, deps_is_mutable_regular,
    deps_issue_map, deps_issue_title, deps_normal_edge, deps_partial_audit, deps_plan,
    deps_plan_writes_allowed, deps_pretty_json, deps_proposal_edges, deps_proposal_mutations,
    deps_revalidate_edge, deps_sanitize_outbound_body, deps_snapshot_numbers,
    deps_validate_snapshot_membership, deps_warning, json_positive_integer, parse_prose_blocks,
};
pub use ground_truth::{
    ClassificationSource, CorpusFilter, CorpusScanStats, EvidenceIndex, EvidenceOrdering,
    EvidenceSource, GateFailure, GroundTruthAnalysis, GroundTruthCorpusScan, GroundTruthEvidence,
    GroundTruthMode, GroundTruthOutcome, GroundTruthRow, GroundTruthStats, GroundTruthVoter,
    IncentiveEra, LARGE_CORPUS_ROW_LIMIT, MatchProfile, NotLaterReason, OutcomeBucket,
    OutcomeDirection, PanelKind, PanelVerdict, VerdictGateInputs, VoterBallot, VoterMetric,
    VoterSeverityMetric, accepted_finding_evidence, analyze_ground_truth, apply_verdict_gate,
    candidate_evidence, classify_in_scope, diagnostic_paths, distinctive_tokens, evidence_ordering,
    issue_evidence, normalize_diagnostic_path, realized_alignment_rate, run_dir_key,
    scan_ground_truth_corpus, strong_match, version_components, version_meets_floor,
};
pub use input::{InputMode, ParsedInput, ParsedItem, parse_issue_input};
pub use lease::{
    IMPLEMENTATION_LEASE_STALE_AFTER_HOURS, ImplementationLease, LeaseDefect,
    implementation_lease_age_hours, implementation_lease_is_expired, parse_implementation_lease,
    render_implementation_lease, upsert_implementation_lease,
};
pub use oos_batch::{
    IssueCapError, ManifestObservation, apply_issue_cap, description_lines, existing_oos_titles,
    next_oos_number, normalize_title, observation_is_security, sanitize_public_text,
    validate_issue_cap_input,
};
pub use oos_conflict::{
    ConflictPlan, FILE_CONFLICT_DEFAULT_CLUSTER_CAP, FILE_CONFLICT_DEFAULT_GLOBAL_CAP,
    FileConflictEdge, FileConflictError, FileConflictRecord, item_file_records, parse_conflict_cap,
    parse_intra_batch_deps, plan_file_conflict_deps, render_deps_tsv, topological_create_order,
};
pub use oos_disposition::{
    ACCEPTED_OOS_FILENAMES, DispositionCounters, DispositionState, INLINE_TRIAGE_MARKER,
    INLINE_TRIAGE_SOURCES, OosDispositionCounts, analyze_run_dir, count_filed_urls_strict_files,
    count_filed_urls_union_files, count_inline_triage_hits, count_inline_triage_occurrences,
    count_non_security_oos_blocks, count_rejected_oos_markers_from_ndjson, issue_url_pattern,
    read_universal_newlines,
};
pub use oos_filing::combined_oos_blocks;
pub use oos_filing::{
    AcceptedBlock, AcceptedSource, FiledIssue, LEGACY_PRIMARY_OOS_SOURCE, bare_oos_item_suffix,
    combined_block_count, dedupe_filed, is_capped_rollup_body, issue_covers_stable_id,
    ndjson_filed_evidence, normalized_title, priority_by_combined_item, priority_urls,
    render_blocks, render_oos_ndjson, render_recovery_evidence, render_sentinel, sentinel_urls,
    split_persisted_matches, split_to_github_limit, stable_identifier, stable_ids_by_combined_item,
    summarize_to_github_limit, working_batch, wrap_oos_body,
};
pub use oos_priority::{
    HIGH_RISK_FOCUS_VALUES, OOS_CORRECTNESS_LABEL, OOS_CORRECTNESS_LABEL_COLOR,
    OOS_CORRECTNESS_LABEL_DESCRIPTION, is_high_risk_oos_block, issue_number_from_url,
    label_create_argv,
};
pub use oos_record::{
    BlockBoundary, CanonicalHeading, OosBlock, OosItemKind, SerializedOos,
    count_non_security_blocks, is_canonical_heading, is_oos_eligible_block, is_security_block_text,
    normalize_oos_block_header, parse_canonical_heading, parse_oos_blocks, serialize_accepted_oos,
};
pub use report_core::{
    BODY_CAP, CategoryCount, CategoryIndex, CategoryLabel, CategoryMode, CoverageStats,
    IssueCategory, IssueLifecycle, IssueSummary, STRIPPED_TITLE_PREFIXES, categorize,
    category_breakdown, category_pattern, coverage_stats, parse_timestamp, percentile,
    strip_prefixes, title_tokens,
};
pub use rows::{OpenIssueRow, open_issue_rows, parse_open_issue_row};
pub use title::{
    ARCHIVAL_JQ_FILTER, BUG_PREFIX, BUG_TITLE_LIFECYCLE_PREFIXES, DONE_PREFIX, IMPLEMENTING_PREFIX,
    LIFECYCLE_PREFIXES, STALLED_PREFIX, UMBRELLA_PREFIX, bug_title_match, detect_lifecycle_prefix,
    insert_signal_marker, insert_tag_after_bug_prefix, leading_square_bracket_prefix,
    normalize_title_prefix, strip_lifecycle_prefix, title_has_archival_report_prefix,
    title_is_archival, title_lifecycle_reject_marker, title_starts_with_brainstorm,
};
pub use triage::{
    MAX_TRIAGE_EVIDENCE_BYTES, MAX_TRIAGE_PROBE_BYTES, TRIAGE_MARKER_END, TRIAGE_MARKER_START,
    TRIAGE_PROBE_TIMEOUT_SECONDS, TRIAGE_TMP_PREFIX, TRIAGE_VERDICT_COMMENT_PREFIX, TRIAGED_TAG,
    TriageBlockDefect, TriageProbe, TriageProbeError, TriageSanitizeError,
    body_has_foreign_larch_marker, replace_triage_block, sanitize_triage_outbound,
    strip_triage_lifecycle_prefixes, triage_label_is_security, triage_probe_command,
    triage_text_is_security_sensitive, triage_title_has_lifecycle_prefix, triaged_title,
    validate_triage_evidence_path,
};
pub use umbrella::{
    ADOPTED_UMBRELLA_SOURCE, AMBIGUOUS_IN_FLIGHT_RECOVERY, CLOSED_INPUT,
    COMPLETION_SENTINEL_VERSION, CandidateIssue, CompletionSentinel, DependencyEdge, ExpectedLeaf,
    INCOMPATIBLE_INPUT, INCOMPATIBLE_MANAGED_PARTITION, INCOMPATIBLE_UMBRELLA,
    INCOMPLETE_GRAPH_STATE, INVALID_COMPLETION_SENTINEL, INVALID_FINAL_UMBRELLA,
    INVALID_LEAF_NUMBER, INVALID_PREPARED_DEPENDENCIES, INVALID_PREPARED_PARTITION,
    INVALID_PROPOSAL_RECORD, INVALID_RESOLVED_LEAF, INVALID_UMBRELLA_NUMBER, LEAF_ALREADY_RESOLVED,
    LEAF_CAP_EXCEEDED, LeafState, MANAGED_PARTITION_PREFIXES, MAX_PREPARED_DEPS_BYTES,
    MAX_PREPARED_INPUT_BYTES, MAX_UMBRELLA_LEAVES, MIN_PREPARED_LEAVES, PREPARED_DEPENDENCY_CYCLE,
    PREPARED_PARTITION_TOO_LARGE, ProposalRecord, RemoteLeaf, ResolvedLeaf,
    STALE_COMPLETION_SENTINEL, STALE_PREPARED_PARTITION, UMBRELLA_PROPOSAL_TOKEN,
    UNKNOWN_LEAF_IDENTITY, UmbrellaRefusal, UmbrellaSnapshot, UmbrellaSourceKind, check_leaf_cap,
    classify_umbrella_source, completion_sentinel_for_record, expected_completion_sentinel,
    is_controlling_umbrella_title, is_managed_partition_title, is_umbrella_leaf_title,
    is_umbrella_title, leaf_identity, mark_leaf_in_flight, parse_proposal,
    prepare_proposal_from_batch, reconcile_in_flight, record_leaf_resolved, render_proposal,
    render_snapshot, umbrella_leaf_opening_text, validate_final_umbrella, verify_graph_state,
};
pub use untrusted::{redact_untrusted_stream, untrusted_content_block, xml_escape_attr};
