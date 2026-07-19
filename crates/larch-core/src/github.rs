//! Narrow GitHub service port and shared hostile-transport policy.

use crate::{RetryClass, StopReason};
use std::time::Duration;

/// Injectable GitHub boundary used by domain code.
///
/// Operation leaves extend this boundary with typed DTOs. The foundation does
/// not expose raw URLs, arbitrary GraphQL documents, or a concrete HTTP client.
pub trait GitHubService: Send + Sync {
    /// Return the immutable transport policy enforced by this service.
    fn transport_policy(&self) -> GitHubTransportPolicy;
}

/// Fixed per-response and continuation bounds.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct GitHubResponseLimits {
    body_bytes: usize,
    pages: usize,
    items: usize,
    string_bytes: usize,
    nesting_depth: usize,
}

impl GitHubResponseLimits {
    /// Maximum bytes accepted for one non-streaming response body.
    #[must_use]
    pub const fn body_bytes(self) -> usize {
        self.body_bytes
    }

    /// Maximum pagination continuations followed for one operation.
    #[must_use]
    pub const fn pages(self) -> usize {
        self.pages
    }

    /// Maximum aggregate items accepted for one operation.
    #[must_use]
    pub const fn items(self) -> usize {
        self.items
    }

    /// Maximum bytes accepted for one untrusted API string.
    #[must_use]
    pub const fn string_bytes(self) -> usize {
        self.string_bytes
    }

    /// Maximum accepted JSON nesting depth.
    #[must_use]
    pub const fn nesting_depth(self) -> usize {
        self.nesting_depth
    }
}

/// Immutable policy shared by every GitHub operation adapter.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct GitHubTransportPolicy {
    connect_timeout: Duration,
    read_timeout: Duration,
    write_timeout: Duration,
    overall_timeout: Duration,
    limits: GitHubResponseLimits,
}

impl GitHubTransportPolicy {
    /// Reviewed policy for the public GitHub API.
    #[must_use]
    pub const fn github_com() -> Self {
        Self {
            connect_timeout: Duration::from_secs(10),
            read_timeout: Duration::from_secs(30),
            write_timeout: Duration::from_secs(30),
            overall_timeout: Duration::from_secs(60),
            limits: GitHubResponseLimits {
                body_bytes: 2 * 1024 * 1024,
                pages: 20,
                items: 2_000,
                string_bytes: 64 * 1024,
                nesting_depth: 64,
            },
        }
    }

    #[must_use]
    pub const fn connect_timeout(self) -> Duration {
        self.connect_timeout
    }

    #[must_use]
    pub const fn read_timeout(self) -> Duration {
        self.read_timeout
    }

    #[must_use]
    pub const fn write_timeout(self) -> Duration {
        self.write_timeout
    }

    #[must_use]
    pub const fn overall_timeout(self) -> Duration {
        self.overall_timeout
    }

    #[must_use]
    pub const fn limits(self) -> GitHubResponseLimits {
        self.limits
    }
}

/// Whether an operation is safe to repeat without reconciliation.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum GitHubRequestKind {
    IdempotentRead,
    Mutation,
}

/// Closed transport input used to classify retries without logging payloads.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum GitHubFailureInput {
    Transport,
    HttpStatus(u16),
}

/// Transport action selected before the shared retry executor runs.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum GitHubRetryAction {
    Retry(RetryClass),
    Stop(StopReason),
    /// A mutation may have committed; its typed operation must read back state.
    ReconcileMutation,
}

/// Inputs parsed from rate-limit headers without retaining response text.
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub struct GitHubRateLimitInputs {
    retry_after: Option<Duration>,
    reset_epoch_seconds: Option<u64>,
    remaining: Option<u64>,
}

impl GitHubRateLimitInputs {
    /// No rate-limit headers were present or valid.
    pub const NONE: Self = Self::new(None, None, None);

    #[must_use]
    pub const fn new(
        retry_after: Option<Duration>,
        reset_epoch_seconds: Option<u64>,
        remaining: Option<u64>,
    ) -> Self {
        Self {
            retry_after,
            reset_epoch_seconds,
            remaining,
        }
    }

    #[must_use]
    pub const fn retry_after(self) -> Option<Duration> {
        self.retry_after
    }

    #[must_use]
    pub const fn reset_epoch_seconds(self) -> Option<u64> {
        self.reset_epoch_seconds
    }

    #[must_use]
    pub const fn remaining(self) -> Option<u64> {
        self.remaining
    }

    /// Return whether parsed headers prove GitHub is throttling this request.
    #[must_use]
    pub const fn is_limited(self) -> bool {
        self.retry_after.is_some() || matches!(self.remaining, Some(0))
    }
}

/// Classify only reviewed transient inputs. Mutations are never blindly retried.
#[must_use]
pub const fn classify_github_retry(
    request: GitHubRequestKind,
    failure: GitHubFailureInput,
    rate_limit: GitHubRateLimitInputs,
) -> GitHubRetryAction {
    let retry_class = match failure {
        GitHubFailureInput::Transport | GitHubFailureInput::HttpStatus(408) => {
            Some(RetryClass::Transient)
        }
        GitHubFailureInput::HttpStatus(429) => Some(RetryClass::Throttled),
        GitHubFailureInput::HttpStatus(500 | 502 | 503 | 504) => Some(RetryClass::Transient),
        GitHubFailureInput::HttpStatus(403) if rate_limit.is_limited() => {
            Some(RetryClass::Throttled)
        }
        GitHubFailureInput::HttpStatus(401 | 403) => {
            return GitHubRetryAction::Stop(StopReason::Authorization);
        }
        GitHubFailureInput::HttpStatus(_) => None,
    };
    match (request, retry_class) {
        (GitHubRequestKind::IdempotentRead, Some(class)) => GitHubRetryAction::Retry(class),
        (GitHubRequestKind::Mutation, Some(_)) => GitHubRetryAction::ReconcileMutation,
        (_, None) => GitHubRetryAction::Stop(StopReason::Permanent),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn reviewed_policy_has_nonzero_deadlines_and_limits() {
        let policy = GitHubTransportPolicy::github_com();
        assert!(policy.connect_timeout() < policy.overall_timeout());
        assert!(policy.read_timeout() < policy.overall_timeout());
        assert!(policy.write_timeout() < policy.overall_timeout());
        assert!(policy.limits().body_bytes() > 0);
        assert!(policy.limits().pages() > 0);
        assert!(policy.limits().items() > 0);
        assert!(policy.limits().string_bytes() > 0);
        assert!(policy.limits().nesting_depth() > 0);
    }

    #[test]
    fn retries_only_bounded_idempotent_read_inputs() {
        assert_eq!(
            classify_github_retry(
                GitHubRequestKind::IdempotentRead,
                GitHubFailureInput::HttpStatus(503),
                GitHubRateLimitInputs::NONE,
            ),
            GitHubRetryAction::Retry(RetryClass::Transient)
        );
        assert_eq!(
            classify_github_retry(
                GitHubRequestKind::IdempotentRead,
                GitHubFailureInput::HttpStatus(429),
                GitHubRateLimitInputs::NONE,
            ),
            GitHubRetryAction::Retry(RetryClass::Throttled)
        );
        assert_eq!(
            classify_github_retry(
                GitHubRequestKind::IdempotentRead,
                GitHubFailureInput::HttpStatus(401),
                GitHubRateLimitInputs::NONE,
            ),
            GitHubRetryAction::Stop(StopReason::Authorization)
        );
    }

    #[test]
    fn uncertain_mutations_require_reconciliation() {
        for failure in [
            GitHubFailureInput::Transport,
            GitHubFailureInput::HttpStatus(408),
            GitHubFailureInput::HttpStatus(429),
            GitHubFailureInput::HttpStatus(500),
        ] {
            assert_eq!(
                classify_github_retry(
                    GitHubRequestKind::Mutation,
                    failure,
                    GitHubRateLimitInputs::NONE,
                ),
                GitHubRetryAction::ReconcileMutation
            );
        }
    }

    #[test]
    fn rate_limit_inputs_are_typed_and_payload_free() {
        let inputs = GitHubRateLimitInputs::new(Some(Duration::from_secs(3)), Some(99), Some(0));
        assert_eq!(inputs.retry_after(), Some(Duration::from_secs(3)));
        assert_eq!(inputs.reset_epoch_seconds(), Some(99));
        assert_eq!(inputs.remaining(), Some(0));
        assert!(inputs.is_limited());
        assert!(!GitHubRateLimitInputs::NONE.is_limited());
    }

    #[test]
    fn rate_limited_forbidden_reads_are_throttled_not_authorization_failures() {
        let limited = GitHubRateLimitInputs::new(Some(Duration::from_secs(3)), None, Some(0));
        assert_eq!(
            classify_github_retry(
                GitHubRequestKind::IdempotentRead,
                GitHubFailureInput::HttpStatus(403),
                limited,
            ),
            GitHubRetryAction::Retry(RetryClass::Throttled)
        );
        assert_eq!(
            classify_github_retry(
                GitHubRequestKind::IdempotentRead,
                GitHubFailureInput::HttpStatus(403),
                GitHubRateLimitInputs::NONE,
            ),
            GitHubRetryAction::Stop(StopReason::Authorization)
        );
    }
}
