//! Shared run-log layout, identity, records, and tolerant readers.

mod batch;
mod completeness;
mod diagram_capture;
mod entry;
mod execution_issue_append;
mod layout;
mod lifecycle;
mod manifest;
mod plan_goals;
mod round;
mod round_artifacts;
mod ship_outcome;
mod slug;
mod tolerance;

pub use batch::{
    BATCH_GUIDELINE_SHIP_OUTCOME, BATCH_INVARIANT_SHIP_OUTCOME, BatchInfo, BatchMode,
    BatchPayloadError, Sanitizer, lookup_batch, normalize_run_log_text, validate_batch_payload,
};
pub use completeness::{
    CompletenessOutcome, ReachabilityContext, condition_reached, scan_required_files,
};
pub use diagram_capture::{sanitize_diagram_capture, strip_diagram_sections};
pub use entry::{
    ExecutionIssueEntry, ExecutionIssueFormat, ExecutionIssueLedger, ExecutionIssueReadError,
    ExecutionIssueReadErrorKind,
};
pub use execution_issue_append::{
    EXECUTION_ISSUE_CATEGORIES, FAILURE_CATEGORIES, FailureEntry, compose_execution_issue,
    compose_failure_entry, failure_retry_suffix, validate_failure_counts,
};
pub use layout::{BatchName, RunLogLayout};
pub use lifecycle::{
    LIFECYCLE_CONTEXT_BASENAME, LIFECYCLE_CONTEXT_SCHEMA_VERSION, LIFECYCLE_SCHEMA_VERSION,
    LifecycleContext, LifecycleError, LifecycleOutcome, UNIVERSAL_EXECUTION_ISSUES,
    UNIVERSAL_FINAL_REPORT, UNIVERSAL_SESSION_TRANSCRIPT,
};
pub use manifest::{
    ManifestDocument, ManifestFormatVersion, ManifestReadError, ManifestReadErrorKind,
    ManifestRecord, ManifestUpdate, ManifestV2Seed, ManifestWriteError,
};
pub use plan_goals::implementation_plan_body;
pub use round::{RoundNumber, RoundNumberError};
pub use round_artifacts::{
    ResidualSecretError, glob_matches, is_round_sidecar_file, round_artifact_included,
    stage_round_artifact,
};
pub use ship_outcome::{AssessmentKind, validate_ship_outcome_record};
pub use slug::{RunLogSlug, RunLogSlugError, RunLogSlugErrorKind, validate_run_log_slug};
pub use tolerance::{
    final_summary_terminal_heading, first_nonempty_line, manifest_pr_evidence_matches,
    stale_bail_heading_with_pr_evidence, terminal_bail_skip_signal,
};
