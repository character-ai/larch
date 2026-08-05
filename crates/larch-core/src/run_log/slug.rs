//! Run-log path slug validation matching Python `validate_run_id_slug`.

use std::{error::Error, fmt};

/// A path-safe skill or run-id slug for run-log directories.
///
/// Matches Python `larch.report.run_log_batch.validate_run_id_slug` byte for byte.
/// This is intentionally distinct from progress [`crate::RunId`], which also
/// reserves `current` / `.` and enforces a 128-byte bound.
#[derive(Clone, Debug, Eq, Hash, Ord, PartialEq, PartialOrd)]
pub struct RunLogSlug(Box<str>);

impl RunLogSlug {
    /// Parse a run-log skill or run-id slug.
    ///
    /// # Errors
    ///
    /// Returns [`RunLogSlugError`] when the value is empty, contains a path
    /// separator or `..`, or includes a byte outside the ASCII allowlist.
    pub fn parse(value: impl Into<String>) -> Result<Self, RunLogSlugError> {
        let value = value.into();
        if !validate_run_log_slug(&value) {
            return Err(RunLogSlugError {
                kind: classify_slug_failure(&value),
            });
        }
        Ok(Self(value.into_boxed_str()))
    }

    /// Return whether `value` is a valid run-log slug without allocating.
    #[must_use]
    pub fn is_valid(value: &str) -> bool {
        validate_run_log_slug(value)
    }

    /// Return the validated slug.
    #[must_use]
    pub fn as_str(&self) -> &str {
        &self.0
    }
}

impl fmt::Display for RunLogSlug {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(self.as_str())
    }
}

impl TryFrom<String> for RunLogSlug {
    type Error = RunLogSlugError;

    fn try_from(value: String) -> Result<Self, Self::Error> {
        Self::parse(value)
    }
}

impl TryFrom<&str> for RunLogSlug {
    type Error = RunLogSlugError;

    fn try_from(value: &str) -> Result<Self, Self::Error> {
        Self::parse(value)
    }
}

/// Why a run-log slug was rejected.
#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub enum RunLogSlugErrorKind {
    /// The slug was empty.
    Empty,
    /// The slug contained `..`.
    DotDot,
    /// The slug contained `/` or `\`.
    PathSeparator,
    /// The slug contained a byte outside the ASCII allowlist.
    InvalidCharacter,
}

/// A typed run-log slug validation failure.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RunLogSlugError {
    kind: RunLogSlugErrorKind,
}

impl RunLogSlugError {
    /// Return the validation failure kind.
    #[must_use]
    pub const fn kind(&self) -> RunLogSlugErrorKind {
        self.kind
    }
}

impl fmt::Display for RunLogSlugError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(match self.kind {
            RunLogSlugErrorKind::Empty => "run-log slug must be non-empty",
            RunLogSlugErrorKind::DotDot => "run-log slug must not contain '..'",
            RunLogSlugErrorKind::PathSeparator => "run-log slug must not contain path separators",
            RunLogSlugErrorKind::InvalidCharacter => {
                "run-log slug must contain only ASCII letters, digits, dot, underscore, or dash"
            }
        })
    }
}

impl Error for RunLogSlugError {}

/// Match Python `validate_run_id_slug` exactly.
#[must_use]
pub fn validate_run_log_slug(run_id: &str) -> bool {
    if run_id.is_empty() || run_id.contains("..") || run_id.contains('/') || run_id.contains('\\') {
        return false;
    }
    run_id
        .bytes()
        .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'.' | b'_' | b'-'))
}

fn classify_slug_failure(value: &str) -> RunLogSlugErrorKind {
    if value.is_empty() {
        RunLogSlugErrorKind::Empty
    } else if value.contains("..") {
        RunLogSlugErrorKind::DotDot
    } else if value.contains('/') || value.contains('\\') {
        RunLogSlugErrorKind::PathSeparator
    } else {
        RunLogSlugErrorKind::InvalidCharacter
    }
}

#[cfg(test)]
mod tests {
    use super::{RunLogSlug, RunLogSlugErrorKind, validate_run_log_slug};

    #[test]
    fn accepts_python_slug_contract() {
        for value in ["run-1", "-abc123", "abc.DEF_123", "current", ".", "A"] {
            assert!(validate_run_log_slug(value), "{value}");
            assert_eq!(RunLogSlug::parse(value).unwrap().as_str(), value);
        }
    }

    #[test]
    fn rejects_python_slug_refusals() {
        let cases = [
            ("", RunLogSlugErrorKind::Empty),
            ("../evil", RunLogSlugErrorKind::DotDot),
            ("a..b", RunLogSlugErrorKind::DotDot),
            ("bad/slash", RunLogSlugErrorKind::PathSeparator),
            (r"bad\slash", RunLogSlugErrorKind::PathSeparator),
            ("bad space", RunLogSlugErrorKind::InvalidCharacter),
            ("bad*char", RunLogSlugErrorKind::InvalidCharacter),
        ];
        for (value, kind) in cases {
            assert!(!validate_run_log_slug(value), "{value}");
            assert_eq!(RunLogSlug::parse(value).unwrap_err().kind(), kind);
        }
    }
}
