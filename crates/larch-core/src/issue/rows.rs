//! The normalized open-issue row model.
//!
//! Ports the row half of Python `larch.issue.open_rows`. The live `gh issue
//! list` read stays in Python until the issue-query and adapter leaves move it;
//! only the tolerant normalization every consumer shares lives here.

use serde_json::Value;

use crate::text::{positive_integer, python_str};

/// One open GitHub issue, normalized for the combine and deps consumers.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct OpenIssueRow {
    number: u64,
    title: String,
    labels: Vec<String>,
    body: String,
}

impl OpenIssueRow {
    /// Return the issue number.
    #[must_use]
    pub const fn number(&self) -> u64 {
        self.number
    }

    /// Return the issue title, or `""` when the read omitted it.
    #[must_use]
    pub fn title(&self) -> &str {
        &self.title
    }

    /// Return the normalized state.
    ///
    /// Every row that survives [`parse_open_issue_row`] is open, so the state is
    /// the constant Python normalized it to.
    #[must_use]
    pub const fn state(&self) -> &'static str {
        "open"
    }

    /// Return the label names, in read order.
    #[must_use]
    pub fn labels(&self) -> &[String] {
        &self.labels
    }

    /// Return the issue body, or `""` when the read omitted it.
    #[must_use]
    pub fn body(&self) -> &str {
        &self.body
    }
}

/// Return a normalized open row, or `None` for malformed or non-open input.
///
/// The skip policy never fails: a non-object row, a row without a positive
/// integer `number`, and a row whose `state` is not `open` are all dropped, so
/// one bad record cannot fail a whole read. Missing `title`, `labels`, and
/// `body` normalize to empty, and labels reduce to their names.
#[must_use]
pub fn parse_open_issue_row(row: &Value) -> Option<OpenIssueRow> {
    let object = row.as_object()?;
    let number = object.get("number").and_then(json_positive_integer)?;
    if !python_str(object.get("state")).eq_ignore_ascii_case("open") {
        return None;
    }
    Some(OpenIssueRow {
        number,
        title: python_str(object.get("title")),
        labels: label_names(object.get("labels")),
        body: python_str(object.get("body")),
    })
}

/// Return every open row in `rows`, sorted by issue number.
#[must_use]
pub fn open_issue_rows(rows: &[Value]) -> Vec<OpenIssueRow> {
    let mut parsed: Vec<OpenIssueRow> = rows.iter().filter_map(parse_open_issue_row).collect();
    parsed.sort_by_key(OpenIssueRow::number);
    parsed
}

/// Accept a positive integer number or its all-digit string spelling.
///
/// A JSON boolean is a distinct value here, matching Python's explicit `bool`
/// rejection, and a fractional number never parses.
fn json_positive_integer(value: &Value) -> Option<u64> {
    match value {
        Value::String(text) => positive_integer(text),
        other => other.as_u64().filter(|number| *number > 0),
    }
}

fn label_names(value: Option<&Value>) -> Vec<String> {
    value
        .and_then(Value::as_array)
        .map(|items| {
            items
                .iter()
                .map(|item| match item {
                    Value::Object(object) => python_str(object.get("name")),
                    other => python_str(Some(other)),
                })
                .filter(|name| !name.is_empty())
                .collect()
        })
        .unwrap_or_default()
}
