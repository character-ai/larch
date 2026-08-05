//! Execution-issue entry readers for markdown and ndjson historical shapes.

use std::{
    error::Error,
    fmt,
    path::Path,
};

use serde_json::Value;

/// One committed execution-issue ledger entry.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ExecutionIssueEntry {
    category: String,
    body: String,
}

impl ExecutionIssueEntry {
    /// Create an entry from validated category and body strings.
    #[must_use]
    pub fn new(category: impl Into<String>, body: impl Into<String>) -> Self {
        Self {
            category: category.into(),
            body: body.into(),
        }
    }

    /// Return the category heading.
    #[must_use]
    pub fn category(&self) -> &str {
        &self.category
    }

    /// Return the issue body.
    #[must_use]
    pub fn body(&self) -> &str {
        &self.body
    }
}

/// Detected execution-issue file format.
#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub enum ExecutionIssueFormat {
    /// Historical markdown `### Category` sections.
    Markdown,
    /// Current ndjson `{category, body}` lines.
    Ndjson,
}

impl ExecutionIssueFormat {
    /// Stable machine token for the detected format.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Markdown => "markdown",
            Self::Ndjson => "ndjson",
        }
    }
}

/// Why an execution-issue read failed.
#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub enum ExecutionIssueReadErrorKind {
    /// File bytes could not be read.
    Io,
    /// An ndjson line was truncated or not JSON.
    InvalidJson,
    /// An ndjson line was not an object with string category/body.
    InvalidShape,
    /// The path suffix did not identify a supported format.
    UnknownFormat,
}

/// Loud execution-issue reader failure with a stable reason.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ExecutionIssueReadError {
    kind: ExecutionIssueReadErrorKind,
    detail: Box<str>,
}

impl ExecutionIssueReadError {
    fn new(kind: ExecutionIssueReadErrorKind, detail: impl Into<String>) -> Self {
        Self {
            kind,
            detail: detail.into().into_boxed_str(),
        }
    }

    /// Return the failure kind.
    #[must_use]
    pub const fn kind(&self) -> ExecutionIssueReadErrorKind {
        self.kind
    }

    /// Return the stable machine reason.
    #[must_use]
    pub const fn reason(&self) -> &'static str {
        match self.kind {
            ExecutionIssueReadErrorKind::Io => "io-error",
            ExecutionIssueReadErrorKind::InvalidJson => "invalid-json",
            ExecutionIssueReadErrorKind::InvalidShape => "invalid-shape",
            ExecutionIssueReadErrorKind::UnknownFormat => "unknown-format",
        }
    }

    /// Return the detail string.
    #[must_use]
    pub fn detail(&self) -> &str {
        &self.detail
    }
}

impl fmt::Display for ExecutionIssueReadError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(formatter, "{}: {}", self.reason(), self.detail)
    }
}

impl Error for ExecutionIssueReadError {}

/// Parsed execution-issue ledger with an explicit detected format.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ExecutionIssueLedger {
    detected_format: ExecutionIssueFormat,
    entries: Vec<ExecutionIssueEntry>,
}

impl ExecutionIssueLedger {
    /// Return the detected format.
    #[must_use]
    pub const fn detected_format(&self) -> ExecutionIssueFormat {
        self.detected_format
    }

    /// Return parsed entries in document order.
    #[must_use]
    pub fn entries(&self) -> &[ExecutionIssueEntry] {
        &self.entries
    }

    /// Parse markdown execution-issue text.
    #[must_use]
    pub fn parse_markdown(text: &str) -> Self {
        let mut entries = Vec::new();
        let mut category = String::new();
        let mut body_lines: Vec<String> = Vec::new();
        for line in text.lines() {
            if let Some(next) = line.strip_prefix("### ") {
                flush_markdown_entry(&mut entries, &category, &body_lines);
                category.clear();
                category.push_str(next.trim());
                body_lines.clear();
                continue;
            }
            body_lines.push(line.to_owned());
        }
        flush_markdown_entry(&mut entries, &category, &body_lines);
        Self {
            detected_format: ExecutionIssueFormat::Markdown,
            entries,
        }
    }

    /// Parse ndjson execution-issue text, failing loudly on truncated lines.
    ///
    /// # Errors
    ///
    /// Returns [`ExecutionIssueReadError`] for invalid JSON or non-object rows.
    pub fn parse_ndjson(text: &str) -> Result<Self, ExecutionIssueReadError> {
        let mut entries = Vec::new();
        for (index, raw) in text.lines().enumerate() {
            if raw.trim().is_empty() {
                continue;
            }
            let value: Value = serde_json::from_str(raw).map_err(|error| {
                ExecutionIssueReadError::new(
                    ExecutionIssueReadErrorKind::InvalidJson,
                    format!("line {}: {error}", index + 1),
                )
            })?;
            let Value::Object(map) = value else {
                return Err(ExecutionIssueReadError::new(
                    ExecutionIssueReadErrorKind::InvalidShape,
                    format!("line {}: entry must be a JSON object", index + 1),
                ));
            };
            let category = match map.get("category") {
                Some(Value::String(text)) => text.clone(),
                _ => {
                    return Err(ExecutionIssueReadError::new(
                        ExecutionIssueReadErrorKind::InvalidShape,
                        format!("line {}: category must be a string", index + 1),
                    ));
                }
            };
            let body = match map.get("body") {
                Some(Value::String(text)) => text.clone(),
                _ => {
                    return Err(ExecutionIssueReadError::new(
                        ExecutionIssueReadErrorKind::InvalidShape,
                        format!("line {}: body must be a string", index + 1),
                    ));
                }
            };
            entries.push(ExecutionIssueEntry::new(category, body));
        }
        Ok(Self {
            detected_format: ExecutionIssueFormat::Ndjson,
            entries,
        })
    }

    /// Read an execution-issue file, detecting markdown vs ndjson by suffix.
    ///
    /// # Errors
    ///
    /// Returns [`ExecutionIssueReadError`] for I/O, unknown suffixes, or truncated
    /// ndjson rows.
    pub fn read_path(path: &Path) -> Result<Self, ExecutionIssueReadError> {
        let text = std::fs::read_to_string(path).map_err(|error| {
            ExecutionIssueReadError::new(
                ExecutionIssueReadErrorKind::Io,
                format!("{}: {error}", path.display()),
            )
        })?;
        match path.extension().and_then(|ext| ext.to_str()) {
            Some("md") => Ok(Self::parse_markdown(&text)),
            Some("ndjson") => Self::parse_ndjson(&text),
            _ => Err(ExecutionIssueReadError::new(
                ExecutionIssueReadErrorKind::UnknownFormat,
                format!(
                    "unsupported execution-issue suffix for {}",
                    path.display()
                ),
            )),
        }
    }
}

fn flush_markdown_entry(
    entries: &mut Vec<ExecutionIssueEntry>,
    category: &str,
    body_lines: &[String],
) {
    let body = body_lines
        .join("\n")
        .trim()
        .to_owned();
    if !category.is_empty() && !body.is_empty() {
        entries.push(ExecutionIssueEntry::new(category, body));
    }
}

#[cfg(test)]
mod tests {
    use super::{ExecutionIssueFormat, ExecutionIssueLedger, ExecutionIssueReadErrorKind};

    #[test]
    fn parses_markdown_and_ndjson_shapes() {
        let markdown = ExecutionIssueLedger::parse_markdown(
            "### Warnings\n\nbody one\n\n### CI Issues\n\nbody two\n",
        );
        assert_eq!(markdown.detected_format(), ExecutionIssueFormat::Markdown);
        assert_eq!(markdown.entries().len(), 2);
        assert_eq!(markdown.entries()[0].category(), "Warnings");
        assert_eq!(markdown.entries()[1].body(), "body two");

        let ndjson = ExecutionIssueLedger::parse_ndjson(
            "{\"category\":\"Warnings\",\"body\":\"a\"}\n{\"category\":\"CI Issues\",\"body\":\"b\"}\n",
        )
        .unwrap();
        assert_eq!(ndjson.detected_format(), ExecutionIssueFormat::Ndjson);
        assert_eq!(ndjson.entries().len(), 2);
    }

    #[test]
    fn truncated_ndjson_fails_loudly() {
        let error = ExecutionIssueLedger::parse_ndjson("{\"category\":\"Warnings\",\"body\":")
            .unwrap_err();
        assert_eq!(error.kind(), ExecutionIssueReadErrorKind::InvalidJson);
        assert_eq!(error.reason(), "invalid-json");
    }
}
