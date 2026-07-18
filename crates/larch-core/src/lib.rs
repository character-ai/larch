//! Domain types, use cases, and effect-free service ports for larch.

mod config;
mod context;
mod env_file;
mod error;
mod outcome;
mod redaction;
mod retry;
mod telemetry;
mod time;

pub use config::env;
pub use context::{RunId, RunIdError, RunIdErrorKind, RuntimeContext};
pub use env_file::{
    CommentPolicy, CrStrip, DuplicateInputPolicy, DuplicatePolicy, EmptyKeyPolicy, EnvFile,
    KeyPolicy, KvDocument, KvError, KvErrorKind, KvRow, MalformedLinePolicy, ParseOptions,
    RenderOptions, WhitespacePolicy,
};
pub use error::{
    EnvironmentalFailure, ErrorCategory, FailureKind, InternalDefect, LarchError, OperatorError,
};
pub use outcome::{ExitCode, WorkflowOutcome};
pub use redaction::{RedactionResult, SafeText, redact, redact_sensitive_paths};
pub use retry::{
    AttemptOutcome, DeterministicJitter, Jitter, RetryClass, RetryDecision, RetryObservation,
    RetryPolicy, RetryPolicyError, StopReason,
};
pub use telemetry::{Breadcrumb, JournalRecord, RecordError, RecordErrorKind};
pub use time::{AsyncClock, BusinessClock, Deadline, MonotonicClock, MonotonicTime, Sleep};

/// Immutable metadata about the running larch build.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct BuildMetadata {
    version: &'static str,
}

impl BuildMetadata {
    /// Create metadata for a compile-time version.
    #[must_use]
    pub const fn new(version: &'static str) -> Self {
        Self { version }
    }

    /// Return the build version.
    #[must_use]
    pub const fn version(self) -> &'static str {
        self.version
    }
}

/// Non-production use cases that prove command dispatch and library wiring.
pub mod example {
    /// Return a caller-owned message unchanged.
    #[must_use]
    pub const fn echo(message: &str) -> &str {
        message
    }
}

#[cfg(test)]
mod tests {
    use super::{BuildMetadata, example};

    #[test]
    fn build_metadata_preserves_the_version() {
        let metadata = BuildMetadata::new("1.2.3");

        assert_eq!(metadata.version(), "1.2.3");
    }

    #[test]
    fn example_echo_preserves_the_message() {
        assert_eq!(example::echo("library wiring"), "library wiring");
    }
}
