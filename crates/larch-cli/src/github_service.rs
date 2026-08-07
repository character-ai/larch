//! One owner for running a command's GitHub work on the hardened service.
//!
//! Every GitHub-backed verb builds its client the same way: resolve the working
//! directory, enter the larch Tokio runtime, and construct the single Octocrab
//! client from the `gh` credential. Only the operation differs, so it is the
//! only thing a caller supplies.

use larch_adapters::{
    TokioProcessRunner,
    github::OctocrabGitHubService,
    runtime::{Cancellation, LarchRuntime},
};
use std::env;

/// Why a GitHub operation did not produce a result.
///
/// Callers that report a setup failure differently from a service refusal —
/// repository resolution, for one — branch on this; the rest read the detail.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum ServiceFailure {
    /// The runtime, working directory, or client could not be built.
    Setup(String),
    /// The client was built and the operation itself failed.
    Operation(String),
}

impl ServiceFailure {
    /// Return the failure detail without its cause classification.
    #[must_use]
    pub fn into_detail(self) -> String {
        match self {
            Self::Setup(detail) | Self::Operation(detail) => detail,
        }
    }
}

/// Run one operation against a freshly built, hardened GitHub service.
///
/// # Errors
///
/// Returns [`ServiceFailure::Setup`] when the client cannot be built and
/// [`ServiceFailure::Operation`] with the operation's own detail otherwise.
pub fn with_github_service<T>(
    operation: impl AsyncFnOnce(&OctocrabGitHubService, &Cancellation) -> Result<T, String>,
) -> Result<T, ServiceFailure> {
    let working_directory = env::current_dir().map_err(|error| {
        ServiceFailure::Setup(format!("cannot resolve current directory: {error}"))
    })?;
    let runtime = LarchRuntime::new().map_err(|error| {
        ServiceFailure::Setup(format!("cannot initialize larch runtime: {error}"))
    })?;
    runtime.block_on(async {
        let runner = TokioProcessRunner::default();
        let cancellation = Cancellation::new();
        let service = OctocrabGitHubService::from_gh(&runner, &working_directory, &cancellation)
            .await
            .map_err(|error| ServiceFailure::Setup(error.to_string()))?;
        operation(&service, &cancellation)
            .await
            .map_err(ServiceFailure::Operation)
    })
}

#[cfg(test)]
mod tests {
    use super::ServiceFailure;

    #[test]
    fn a_failure_yields_its_detail_whatever_its_cause() {
        assert_eq!(
            ServiceFailure::Setup("no runtime".to_owned()).into_detail(),
            "no runtime"
        );
        assert_eq!(
            ServiceFailure::Operation("not found".to_owned()).into_detail(),
            "not found"
        );
    }
}
