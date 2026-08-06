//! Shared run-log layout, identity, and tolerant readers.

mod entry;
mod layout;
mod lifecycle;
mod manifest;
mod round;
mod slug;
mod tolerance;

pub use entry::{
    ExecutionIssueEntry, ExecutionIssueFormat, ExecutionIssueLedger, ExecutionIssueReadError,
    ExecutionIssueReadErrorKind,
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
pub use round::{RoundNumber, RoundNumberError};
pub use slug::{RunLogSlug, RunLogSlugError, RunLogSlugErrorKind, validate_run_log_slug};
pub use tolerance::{
    final_summary_terminal_heading, first_nonempty_line, manifest_pr_evidence_matches,
    stale_bail_heading_with_pr_evidence, terminal_bail_skip_signal,
};
