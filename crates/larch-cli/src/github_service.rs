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
use larch_core::GitHubTransportPolicy;
use std::env;

#[cfg(test)]
use std::{cell::RefCell, sync::Arc};

#[cfg(test)]
type TestServiceFactory = Arc<dyn Fn() -> OctocrabGitHubService + Send + Sync>;

#[cfg(test)]
std::thread_local! {
    /// Per-test substitute for the process-built GitHub service.
    ///
    /// Command-unit tests use a loopback-only typed client to exercise the
    /// same command path without making credential or network calls.  The
    /// value is thread-local because Rust runs independent unit tests in
    /// parallel.
    static TEST_SERVICE: RefCell<Option<TestServiceFactory>> = const { RefCell::new(None) };
}

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
    with_github_service_policy(GitHubTransportPolicy::github_com(), operation)
}

/// Run one operation against a hardened GitHub client using a reviewed
/// transport policy.
///
/// The migration audit is the only current caller that needs its separately
/// bounded exhaustive-history policy. Credential acquisition and client
/// construction remain centralized here and in the adapter.
pub fn with_github_service_policy<T>(
    policy: GitHubTransportPolicy,
    operation: impl AsyncFnOnce(&OctocrabGitHubService, &Cancellation) -> Result<T, String>,
) -> Result<T, ServiceFailure> {
    #[cfg(test)]
    if let Some(factory) = TEST_SERVICE.with(|slot| slot.borrow().clone()) {
        let runtime = LarchRuntime::new().map_err(|error| {
            ServiceFailure::Setup(format!("cannot initialize larch runtime: {error}"))
        })?;
        return runtime.block_on(async {
            let service = factory();
            let cancellation = Cancellation::new();
            operation(&service, &cancellation)
                .await
                .map_err(ServiceFailure::Operation)
        });
    }
    let working_directory = env::current_dir().map_err(|error| {
        ServiceFailure::Setup(format!("cannot resolve current directory: {error}"))
    })?;
    let runtime = LarchRuntime::new().map_err(|error| {
        ServiceFailure::Setup(format!("cannot initialize larch runtime: {error}"))
    })?;
    runtime.block_on(async {
        let runner = TokioProcessRunner::default();
        let cancellation = Cancellation::new();
        let service = OctocrabGitHubService::from_gh_with_policy(
            &runner,
            &working_directory,
            &cancellation,
            policy,
        )
        .await
        .map_err(|error| ServiceFailure::Setup(error.to_string()))?;
        operation(&service, &cancellation)
            .await
            .map_err(ServiceFailure::Operation)
    })
}

/// Run one command-unit-test action with a loopback-only GitHub service.
///
/// The substitute exists only in the test build; released command paths still
/// acquire their sole credential through `gh auth token --hostname github.com`.
#[cfg(test)]
pub fn with_test_github_service<T>(factory: TestServiceFactory, action: impl FnOnce() -> T) -> T {
    TEST_SERVICE.with(|slot| {
        assert!(
            slot.replace(Some(factory)).is_none(),
            "a command test cannot nest GitHub service substitutes"
        );
        let outcome = action();
        let _ = slot.replace(None);
        outcome
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
