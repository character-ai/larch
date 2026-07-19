//! Domain types, use cases, and effect-free service ports for larch.

mod config;
mod context;
mod env_file;
mod error;
mod git;
mod github;
mod outcome;
mod process;
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
pub use git::{
    Change, ChangeKind, ChangeSet, Commit, ConfigKey, ConfigScope, ConfigValue, ConflictKind,
    ConflictStage, GitMode, GitPath, Head, IgnoreKind, IgnoredEntry, IndexFlags, Object,
    ObjectHash, ObjectId, ObjectKind, RefFormat, RefName, Reference, ReferenceKind,
    ReferenceTarget, Remote, RepositoryError, RepositoryErrorKind, RepositoryLocation,
    RepositoryRead, RepositoryStatus, Revision, StatusOptions, TrackedEntry, UnmergedEntry,
    Upstream, Worktree,
};
pub use github::{
    CheckBucket, CheckRun, GitHubActionsError, GitHubActionsErrorKind, GitHubActionsFuture,
    GitHubActionsService, GitHubCloseReason, GitHubComment, GitHubFailureInput, GitHubFuture,
    GitHubIssue, GitHubIssueCreate, GitHubIssueEdit, GitHubIssueList, GitHubIssueSearch,
    GitHubIssueState, GitHubLabel, GitHubLabelCreate, GitHubMutationOutcome, GitHubOperationError,
    GitHubOperationErrorKind, GitHubRateLimitInputs, GitHubRepository, GitHubRepositoryRef,
    GitHubRequestKind, GitHubResponseLimits, GitHubRetryAction, GitHubService,
    GitHubTransportPolicy, WorkflowDispatchRequest, WorkflowJob, WorkflowLogArchive, WorkflowRun,
    WorkflowRunFilters, classify_github_retry,
};
pub use outcome::{ExitCode, WorkflowOutcome};
pub use process::{
    ChildEnvironment, ExternalProcessRunner, ExternalProgram, GitCliOperation, ProcessCancellation,
    ProcessError, ProcessErrorKind, ProcessEvent, ProcessEventKind, ProcessFuture, ProcessObserver,
    ProcessOutput, ProcessRequest, ProcessRequestError, ProcessRequestErrorKind, ProcessStatus,
    VendorProgram,
};
pub use redaction::{RedactionResult, RuntimeRedactor, SafeText, redact, redact_sensitive_paths};
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
    target: &'static str,
}

impl BuildMetadata {
    /// Create metadata for a compile-time version.
    #[must_use]
    pub const fn new(version: &'static str, target: &'static str) -> Self {
        Self { version, target }
    }

    /// Return the build version.
    #[must_use]
    pub const fn version(self) -> &'static str {
        self.version
    }

    /// Return the compilation target triple.
    #[must_use]
    pub const fn target(self) -> &'static str {
        self.target
    }
}

/// Render the machine-readable identity checked by the installation shim.
#[must_use]
pub fn bootstrap_self_check(metadata: BuildMetadata) -> String {
    format!(
        "{{\"schema_version\":1,\"version\":\"{}\",\"target\":\"{}\"}}",
        metadata.version(),
        metadata.target()
    )
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
    use super::{BuildMetadata, bootstrap_self_check, example};

    #[test]
    fn build_metadata_preserves_the_version() {
        let metadata = BuildMetadata::new("1.2.3", "aarch64-apple-darwin");

        assert_eq!(metadata.version(), "1.2.3");
        assert_eq!(metadata.target(), "aarch64-apple-darwin");
    }

    #[test]
    fn bootstrap_self_check_is_compact_machine_readable_json() {
        let metadata = BuildMetadata::new("1.2.3", "x86_64-unknown-linux-gnu");

        assert_eq!(
            bootstrap_self_check(metadata),
            r#"{"schema_version":1,"version":"1.2.3","target":"x86_64-unknown-linux-gnu"}"#
        );
    }

    #[test]
    fn example_echo_preserves_the_message() {
        assert_eq!(example::echo("library wiring"), "library wiring");
    }
}
