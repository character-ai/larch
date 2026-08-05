//! Shared run-log layout, identity, and tolerant readers.

mod entry;
mod layout;
mod manifest;
mod round;
mod slug;
mod tolerance;

pub use entry::{
    ExecutionIssueEntry, ExecutionIssueFormat, ExecutionIssueLedger, ExecutionIssueReadError,
    ExecutionIssueReadErrorKind,
};
pub use layout::{BatchName, RunLogLayout};
pub use manifest::{
    ManifestFormatVersion, ManifestReadError, ManifestReadErrorKind, ManifestRecord,
};
pub use round::{RoundNumber, RoundNumberError};
pub use slug::{RunLogSlug, RunLogSlugError, RunLogSlugErrorKind, validate_run_log_slug};
pub use tolerance::{
    final_summary_terminal_heading, first_nonempty_line, manifest_pr_evidence_matches,
    stale_bail_heading_with_pr_evidence, terminal_bail_skip_signal,
};
