//! Shared report Markdown block and executive issue-detail helpers.
//!
//! Library parity for Python `larch.report.markdown_block` and
//! `larch.report.exec_issue_detail`. No command changes owner in this leaf;
//! Python remains the production owner until consumer cutover leaves move.

mod exec_issue_detail;
mod markdown_block;

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
