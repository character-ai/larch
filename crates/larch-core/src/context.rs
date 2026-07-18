//! Validated run identity and immutable runtime context.

use crate::BuildMetadata;
use std::{error::Error, fmt};

const RUN_ID_MAX_BYTES: usize = 128;

/// A path-safe identifier for one larch run.
#[derive(Clone, Debug, Eq, Hash, Ord, PartialEq, PartialOrd)]
pub struct RunId(Box<str>);

impl RunId {
    /// Parse a run identifier shared by progress, background-job, and run-log paths.
    ///
    /// # Errors
    ///
    /// Returns [`RunIdError`] when the value is empty, too long, reserved, or
    /// contains a byte outside the stable ASCII allowlist.
    pub fn parse(value: impl Into<String>) -> Result<Self, RunIdError> {
        let value = value.into();
        validate_run_id(&value)?;
        Ok(Self(value.into_boxed_str()))
    }

    /// Return the validated identifier.
    #[must_use]
    pub fn as_str(&self) -> &str {
        &self.0
    }
}

impl fmt::Display for RunId {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(self.as_str())
    }
}

impl TryFrom<String> for RunId {
    type Error = RunIdError;

    fn try_from(value: String) -> Result<Self, Self::Error> {
        Self::parse(value)
    }
}

impl TryFrom<&str> for RunId {
    type Error = RunIdError;

    fn try_from(value: &str) -> Result<Self, Self::Error> {
        Self::parse(value)
    }
}

/// The reason a run identifier was rejected.
#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub enum RunIdErrorKind {
    /// The identifier was empty.
    Empty,
    /// The identifier exceeded the shared size bound.
    TooLong,
    /// The identifier is reserved by the progress pointer contract.
    Reserved,
    /// The identifier contained bytes outside the stable ASCII allowlist.
    InvalidCharacter,
}

/// A typed run-identifier validation failure.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RunIdError {
    kind: RunIdErrorKind,
}

impl RunIdError {
    /// Return the validation failure kind.
    #[must_use]
    pub const fn kind(&self) -> RunIdErrorKind {
        self.kind
    }
}

impl fmt::Display for RunIdError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(match self.kind {
            RunIdErrorKind::Empty => "run ID must be non-empty",
            RunIdErrorKind::TooLong => "run ID must be at most 128 bytes",
            RunIdErrorKind::Reserved => "run ID is reserved",
            RunIdErrorKind::InvalidCharacter => {
                "run ID must contain only ASCII letters, digits, dot, underscore, or dash"
            }
        })
    }
}

impl Error for RunIdError {}

fn validate_run_id(value: &str) -> Result<(), RunIdError> {
    let kind = if value.is_empty() {
        Some(RunIdErrorKind::Empty)
    } else if value.len() > RUN_ID_MAX_BYTES {
        Some(RunIdErrorKind::TooLong)
    } else if matches!(value, "." | ".." | "current") || value.contains("..") {
        Some(RunIdErrorKind::Reserved)
    } else if !value
        .bytes()
        .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'.' | b'_' | b'-'))
    {
        Some(RunIdErrorKind::InvalidCharacter)
    } else {
        None
    };

    kind.map_or(Ok(()), |kind| Err(RunIdError { kind }))
}

/// Immutable metadata shared by one larch invocation.
///
/// Composition code constructs this value once after parsing untrusted input.
/// Domain code receives it by shared reference and cannot replace its identity.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RuntimeContext {
    build: BuildMetadata,
    run_id: RunId,
    session_id: Option<Box<str>>,
}

impl RuntimeContext {
    /// Create an invocation context from validated identity.
    #[must_use]
    pub fn new(build: BuildMetadata, run_id: RunId, session_id: Option<String>) -> Self {
        Self {
            build,
            run_id,
            session_id: session_id.map(String::into_boxed_str),
        }
    }

    /// Return metadata for the running build.
    #[must_use]
    pub const fn build(&self) -> BuildMetadata {
        self.build
    }

    /// Return the validated run identifier.
    #[must_use]
    pub const fn run_id(&self) -> &RunId {
        &self.run_id
    }

    /// Return the optional outer-session correlation identifier.
    #[must_use]
    pub fn session_id(&self) -> Option<&str> {
        self.session_id.as_deref()
    }
}

#[cfg(test)]
mod tests {
    use super::{RunId, RunIdErrorKind, RuntimeContext};
    use crate::BuildMetadata;

    #[test]
    fn run_id_accepts_live_ascii_contract() {
        for value in ["run-1", "-abc123", "abc.DEF_123", "A", &"a".repeat(128)] {
            let run_id = RunId::parse(value).expect("valid run ID should parse");
            assert_eq!(run_id.as_str(), value);
            assert_eq!(run_id.to_string(), value);
        }
    }

    #[test]
    fn run_id_rejects_unsafe_and_reserved_values() {
        let invalid = [
            ("", RunIdErrorKind::Empty),
            (&"a".repeat(129), RunIdErrorKind::TooLong),
            (".", RunIdErrorKind::Reserved),
            ("..", RunIdErrorKind::Reserved),
            ("current", RunIdErrorKind::Reserved),
            ("a..b", RunIdErrorKind::Reserved),
            ("../evil", RunIdErrorKind::Reserved),
            ("bad/slash", RunIdErrorKind::InvalidCharacter),
            (r"bad\slash", RunIdErrorKind::InvalidCharacter),
            ("bad space", RunIdErrorKind::InvalidCharacter),
            ("café", RunIdErrorKind::InvalidCharacter),
        ];

        for (value, expected) in invalid {
            let error = RunId::parse(value).expect_err("unsafe run ID should fail");
            assert_eq!(error.kind(), expected, "{value:?}");
        }
    }

    #[test]
    fn runtime_context_preserves_validated_immutable_identity() {
        let context = RuntimeContext::new(
            BuildMetadata::new("53.1.22"),
            RunId::parse("run-abc").expect("fixture run ID should parse"),
            Some("session-123".to_owned()),
        );
        let cloned = context.clone();

        assert_eq!(context.build().version(), "53.1.22");
        assert_eq!(context.run_id().as_str(), "run-abc");
        assert_eq!(context.session_id(), Some("session-123"));
        assert_eq!(cloned, context);
    }
}
