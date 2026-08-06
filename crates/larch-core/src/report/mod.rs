//! Shared report Markdown block, issue-detail, and run-log corpus helpers.
//!
//! Library parity for Python `larch.report.markdown_block` and
//! `larch.report.exec_issue_detail`, plus read-only parity for
//! `larch.report.run_log_batch` and `larch.report.run_log_corpus`. No command
//! changes owner in these leaves; Python remains the production owner until
//! consumer cutover leaves move.

mod exec_issue_detail;
mod markdown_block;
mod run_log_corpus;

pub use exec_issue_detail::{
    EMPTY_GROUPS, IssueDetail, IssueDetailGroups, IssueEvent, LoadResult, MAX_DEDUPE_KEY_LEN,
    MAX_DISPLAY_LEN, WARN_CATEGORY, build_issue_detail_section, count_issue_groups,
    count_load_result, execution_issue_identity, load_issue_detail_groups,
    parse_markdown_execution_issues, render_issue_detail_block, structured_body_dedupe_keys,
};
pub use markdown_block::{
    BlockMarkers, BlockMarkersError, BlockMarkersErrorKind, replace_markdown_block,
    replace_markdown_block_with_warn,
};
pub use run_log_corpus::{
    RunLogBatchArtifact, RunLogBatchMode, RunLogBatchSanitizer, RunLogBatchSpec, RunLogCorpus,
    RunLogCorpusEvent, RunLogCorpusIter, RunLogCorpusWarning, RunLogCorpusWarningKind,
    RunLogFileIter, RunLogManifest, RunLogRoundSort, RunLogRun, RunLogSelection, RunLogTimeWindow,
    RunLogTimeWindowError, parse_preterminal_outcome_label, round_number_from_path,
    run_log_batch_spec, run_log_batch_specs,
};
