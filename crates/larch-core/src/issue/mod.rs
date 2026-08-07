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
mod ground_truth;
mod report_core;
mod rows;
mod title;
mod untrusted;

pub use body::{
    ALLOWED_NAMED_BLOCK_MARKERS, DESIGN_PAUSE_MARKER, MISSING_PLAN_BLOCK, MULTIPLE_PLAN_BLOCKS,
    NamedBlockDefect, NamedBlockError, NamedBlockSpan, NamedBlockWrite, NamedBlockWriteMode,
    PLAN_MARKER, classify_named_block, compose_named_block, is_valid_named_block_marker,
    issue_plan_marker_defect, named_block_marker_allowed, neutralize_named_block_markers,
    parse_named_block, plan_named_block_write, strip_named_block,
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
pub use report_core::{
    BODY_CAP, CategoryCount, CategoryIndex, CategoryLabel, CategoryMode, CoverageStats,
    IssueCategory, IssueLifecycle, IssueSummary, STRIPPED_TITLE_PREFIXES, categorize,
    category_breakdown, category_pattern, coverage_stats, parse_timestamp, percentile,
    strip_prefixes, title_tokens,
};
pub use rows::{OpenIssueRow, open_issue_rows, parse_open_issue_row};
pub use title::{
    ARCHIVAL_JQ_FILTER, BUG_PREFIX, BUG_TITLE_LIFECYCLE_PREFIXES, LIFECYCLE_PREFIXES,
    bug_title_match, detect_lifecycle_prefix, insert_signal_marker, insert_tag_after_bug_prefix,
    leading_square_bracket_prefix, strip_lifecycle_prefix, title_has_archival_report_prefix,
    title_lifecycle_reject_marker, title_starts_with_brainstorm,
};
pub use untrusted::{redact_untrusted_stream, untrusted_content_block, xml_escape_attr};
