//! Stable process exits and workflow outcomes.

use std::fmt;

/// Stable process exit codes shared by larch commands.
///
/// These values preserve the live Python command contract. Domain-specific
/// helper exits stay with their owning command instead of expanding this type.
#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
#[repr(i32)]
pub enum ExitCode {
    /// The command completed successfully.
    Success = 0,
    /// Larch encountered an internal defect.
    InternalError = 1,
    /// The operator supplied invalid arguments or configuration.
    Usage = 2,
    /// Larch needs an operator decision before it can continue.
    NeedsUserInput = 3,
    /// An external precondition prevented the workflow from continuing.
    Stalled = 4,
    /// A requested live mutation lacked operator authorization.
    MutationRefused = 5,
    /// A retryable environmental failure interrupted the workflow.
    Transient = 6,
    /// An authored artifact must be revised before it can be accepted.
    ReauthorRequired = 7,
    /// An external operation exceeded its deadline.
    Timeout = 124,
}

impl ExitCode {
    /// Every shared exit code, used by composition layers and exhaustive tests.
    pub const ALL: [Self; 9] = [
        Self::Success,
        Self::InternalError,
        Self::Usage,
        Self::NeedsUserInput,
        Self::Stalled,
        Self::MutationRefused,
        Self::Transient,
        Self::ReauthorRequired,
        Self::Timeout,
    ];

    /// Return the process exit status.
    #[must_use]
    pub const fn value(self) -> i32 {
        match self {
            Self::Success => 0,
            Self::InternalError => 1,
            Self::Usage => 2,
            Self::NeedsUserInput => 3,
            Self::Stalled => 4,
            Self::MutationRefused => 5,
            Self::Transient => 6,
            Self::ReauthorRequired => 7,
            Self::Timeout => 124,
        }
    }

    /// Parse a process status when it is part of the shared contract.
    #[must_use]
    pub const fn from_value(value: i32) -> Option<Self> {
        match value {
            0 => Some(Self::Success),
            1 => Some(Self::InternalError),
            2 => Some(Self::Usage),
            3 => Some(Self::NeedsUserInput),
            4 => Some(Self::Stalled),
            5 => Some(Self::MutationRefused),
            6 => Some(Self::Transient),
            7 => Some(Self::ReauthorRequired),
            124 => Some(Self::Timeout),
            _ => None,
        }
    }
}

/// Terminal outcomes shared by workflow state machines.
#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub enum WorkflowOutcome {
    /// The workflow completed successfully.
    Ok,
    /// The workflow needs an operator decision.
    NeedsUserInput,
    /// The workflow stopped on an unmet external precondition.
    Stalled,
    /// The workflow stopped on a retryable environmental failure.
    Transient,
    /// The workflow stopped because larch violated an internal contract.
    InternalError,
}

impl WorkflowOutcome {
    /// Every shared workflow outcome.
    pub const ALL: [Self; 5] = [
        Self::Ok,
        Self::NeedsUserInput,
        Self::Stalled,
        Self::Transient,
        Self::InternalError,
    ];

    /// Return the stable machine-readable outcome string.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Ok => "OK",
            Self::NeedsUserInput => "NEEDS_USER_INPUT",
            Self::Stalled => "STALLED",
            Self::Transient => "TRANSIENT",
            Self::InternalError => "INTERNAL_ERROR",
        }
    }

    /// Return the stable process exit code for this outcome.
    #[must_use]
    pub const fn exit_code(self) -> ExitCode {
        match self {
            Self::Ok => ExitCode::Success,
            Self::NeedsUserInput => ExitCode::NeedsUserInput,
            Self::Stalled => ExitCode::Stalled,
            Self::Transient => ExitCode::Transient,
            Self::InternalError => ExitCode::InternalError,
        }
    }
}

impl fmt::Display for WorkflowOutcome {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(self.as_str())
    }
}

#[cfg(test)]
mod tests {
    use super::{ExitCode, WorkflowOutcome};
    use std::collections::BTreeSet;

    #[test]
    fn shared_exit_codes_preserve_the_live_contract() {
        let expected = [
            (ExitCode::Success, 0),
            (ExitCode::InternalError, 1),
            (ExitCode::Usage, 2),
            (ExitCode::NeedsUserInput, 3),
            (ExitCode::Stalled, 4),
            (ExitCode::MutationRefused, 5),
            (ExitCode::Transient, 6),
            (ExitCode::ReauthorRequired, 7),
            (ExitCode::Timeout, 124),
        ];

        assert_eq!(ExitCode::ALL.len(), expected.len());
        for (exit, value) in expected {
            assert_eq!(exit.value(), value);
            assert_eq!(ExitCode::from_value(value), Some(exit));
        }
    }

    #[test]
    fn shared_exit_codes_are_unique_and_unknown_values_stay_domain_owned() {
        let values = ExitCode::ALL.map(ExitCode::value);
        assert_eq!(
            values.into_iter().collect::<BTreeSet<_>>().len(),
            values.len()
        );
        assert_eq!(ExitCode::from_value(-1), None);
        assert_eq!(ExitCode::from_value(8), None);
        assert_eq!(ExitCode::from_value(125), None);
    }

    #[test]
    fn every_workflow_outcome_has_its_stable_string_and_exit() {
        let expected = [
            (WorkflowOutcome::Ok, "OK", ExitCode::Success),
            (
                WorkflowOutcome::NeedsUserInput,
                "NEEDS_USER_INPUT",
                ExitCode::NeedsUserInput,
            ),
            (WorkflowOutcome::Stalled, "STALLED", ExitCode::Stalled),
            (WorkflowOutcome::Transient, "TRANSIENT", ExitCode::Transient),
            (
                WorkflowOutcome::InternalError,
                "INTERNAL_ERROR",
                ExitCode::InternalError,
            ),
        ];

        assert_eq!(WorkflowOutcome::ALL.len(), expected.len());
        for (outcome, text, exit) in expected {
            assert_eq!(outcome.as_str(), text);
            assert_eq!(outcome.to_string(), text);
            assert_eq!(outcome.exit_code(), exit);
        }
    }
}
