//! Issue-body wire, block, and identity model.
//!
//! Ports Python `larch.issue.issue_blocks`, the wire subset of
//! `larch.issue.issue_wire`, `larch.issue.title_match`, and the row model in
//! `larch.issue.open_rows`. `crate::report::markdown_block` stays the Markdown
//! block owner; the larch named block is a distinct fail-closed grammar layered
//! above the same shared line primitive. No command changes owner here: Python
//! keeps every `plan-block`, `named-block`, `untrusted`, and `issue title-*`
//! command until its command leaf migrates it.

mod body;
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
pub use rows::{OpenIssueRow, open_issue_rows, parse_open_issue_row};
pub use title::{
    ARCHIVAL_JQ_FILTER, BUG_PREFIX, BUG_TITLE_LIFECYCLE_PREFIXES, LIFECYCLE_PREFIXES,
    bug_title_match, detect_lifecycle_prefix, insert_signal_marker, insert_tag_after_bug_prefix,
    leading_square_bracket_prefix, strip_lifecycle_prefix, title_has_archival_report_prefix,
    title_lifecycle_reject_marker, title_starts_with_brainstorm,
};
pub use untrusted::{redact_untrusted_stream, untrusted_content_block, xml_escape_attr};
