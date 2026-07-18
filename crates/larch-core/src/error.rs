//! Categorized failures for domain and composition layers.

use crate::ExitCode;
use std::{error::Error, fmt};

/// The actor or system responsible for resolving a failure.
#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub enum ErrorCategory {
    /// The operator must correct input, grant authority, or make a decision.
    Operator,
    /// An external dependency or runtime precondition failed.
    Environment,
    /// Larch violated one of its own contracts.
    Internal,
}

/// Operator-resolvable failures.
#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub enum OperatorError {
    /// Command arguments or trusted configuration are invalid.
    Usage,
    /// The workflow needs a decision or manual action.
    NeedsUserInput,
    /// A live mutation was not authorized.
    MutationRefused,
    /// An authored artifact must be revised.
    ReauthorRequired,
}

/// Failures caused by external systems or runtime preconditions.
#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub enum EnvironmentalFailure {
    /// A required external precondition is not currently satisfied.
    Stalled,
    /// A retryable infrastructure or service failure occurred.
    Transient,
    /// An external operation exceeded its deadline.
    Timeout,
}

/// Defects caused by larch itself.
#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub enum InternalDefect {
    /// Larch reached a state forbidden by its own contracts.
    ContractViolation,
}

/// A typed failure kind with an unambiguous responsibility category.
#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub enum FailureKind {
    /// An operator-resolvable failure.
    Operator(OperatorError),
    /// An environmental failure.
    Environment(EnvironmentalFailure),
    /// An internal larch defect.
    Internal(InternalDefect),
}

impl FailureKind {
    /// Return the responsible category.
    #[must_use]
    pub const fn category(self) -> ErrorCategory {
        match self {
            Self::Operator(_) => ErrorCategory::Operator,
            Self::Environment(_) => ErrorCategory::Environment,
            Self::Internal(_) => ErrorCategory::Internal,
        }
    }

    /// Return the stable process exit code.
    #[must_use]
    pub const fn exit_code(self) -> ExitCode {
        match self {
            Self::Operator(OperatorError::Usage) => ExitCode::Usage,
            Self::Operator(OperatorError::NeedsUserInput) => ExitCode::NeedsUserInput,
            Self::Operator(OperatorError::MutationRefused) => ExitCode::MutationRefused,
            Self::Operator(OperatorError::ReauthorRequired) => ExitCode::ReauthorRequired,
            Self::Environment(EnvironmentalFailure::Stalled) => ExitCode::Stalled,
            Self::Environment(EnvironmentalFailure::Transient) => ExitCode::Transient,
            Self::Environment(EnvironmentalFailure::Timeout) => ExitCode::Timeout,
            Self::Internal(InternalDefect::ContractViolation) => ExitCode::InternalError,
        }
    }
}

/// A categorized larch failure with diagnostic context.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct LarchError {
    kind: FailureKind,
    message: String,
}

impl LarchError {
    /// Create a categorized failure.
    #[must_use]
    pub fn new(kind: FailureKind, message: impl Into<String>) -> Self {
        Self {
            kind,
            message: message.into(),
        }
    }

    /// Return the typed failure kind.
    #[must_use]
    pub const fn kind(&self) -> FailureKind {
        self.kind
    }

    /// Return the responsible category.
    #[must_use]
    pub const fn category(&self) -> ErrorCategory {
        self.kind.category()
    }

    /// Return the stable process exit code.
    #[must_use]
    pub const fn exit_code(&self) -> ExitCode {
        self.kind.exit_code()
    }

    /// Return the diagnostic without adding presentation text.
    #[must_use]
    pub fn message(&self) -> &str {
        &self.message
    }
}

impl fmt::Display for LarchError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(&self.message)
    }
}

impl Error for LarchError {}

#[cfg(test)]
mod tests {
    use super::{
        EnvironmentalFailure, ErrorCategory, FailureKind, InternalDefect, LarchError, OperatorError,
    };
    use crate::ExitCode;

    #[test]
    fn every_failure_kind_maps_to_one_category_and_stable_exit() {
        let expected = [
            (
                FailureKind::Operator(OperatorError::Usage),
                ErrorCategory::Operator,
                ExitCode::Usage,
            ),
            (
                FailureKind::Operator(OperatorError::NeedsUserInput),
                ErrorCategory::Operator,
                ExitCode::NeedsUserInput,
            ),
            (
                FailureKind::Operator(OperatorError::MutationRefused),
                ErrorCategory::Operator,
                ExitCode::MutationRefused,
            ),
            (
                FailureKind::Operator(OperatorError::ReauthorRequired),
                ErrorCategory::Operator,
                ExitCode::ReauthorRequired,
            ),
            (
                FailureKind::Environment(EnvironmentalFailure::Stalled),
                ErrorCategory::Environment,
                ExitCode::Stalled,
            ),
            (
                FailureKind::Environment(EnvironmentalFailure::Transient),
                ErrorCategory::Environment,
                ExitCode::Transient,
            ),
            (
                FailureKind::Environment(EnvironmentalFailure::Timeout),
                ErrorCategory::Environment,
                ExitCode::Timeout,
            ),
            (
                FailureKind::Internal(InternalDefect::ContractViolation),
                ErrorCategory::Internal,
                ExitCode::InternalError,
            ),
        ];

        for (kind, category, exit) in expected {
            assert_eq!(kind.category(), category);
            assert_eq!(kind.exit_code(), exit);
        }
    }

    #[test]
    fn larch_error_preserves_typed_and_display_contracts() {
        let error = LarchError::new(
            FailureKind::Environment(EnvironmentalFailure::Transient),
            "GitHub request failed",
        );

        assert_eq!(
            error.kind(),
            FailureKind::Environment(EnvironmentalFailure::Transient)
        );
        assert_eq!(error.category(), ErrorCategory::Environment);
        assert_eq!(error.exit_code(), ExitCode::Transient);
        assert_eq!(error.message(), "GitHub request failed");
        assert_eq!(error.to_string(), "GitHub request failed");
    }
}
