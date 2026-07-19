//! Narrow GitHub service port and shared hostile-transport policy.

use crate::{ProcessCancellation, RetryClass, SafeText, StopReason};
use std::{error::Error, fmt, future::Future, pin::Pin, time::Duration};

/// Injectable GitHub boundary used by domain code.
///
/// Operation leaves extend this boundary with typed DTOs. The foundation does
/// not expose raw URLs, arbitrary GraphQL documents, or a concrete HTTP client.
pub trait GitHubService: Send + Sync {
    /// Return the immutable transport policy enforced by this service.
    fn transport_policy(&self) -> GitHubTransportPolicy;

    fn repository<'a>(
        &'a self,
        repo: &'a GitHubRepositoryRef,
        cancellation: &'a dyn ProcessCancellation,
    ) -> GitHubFuture<'a, GitHubRepository>;

    fn issue<'a>(
        &'a self,
        repo: &'a GitHubRepositoryRef,
        number: u64,
        cancellation: &'a dyn ProcessCancellation,
    ) -> GitHubFuture<'a, GitHubIssue>;

    fn list_issues<'a>(
        &'a self,
        request: &'a GitHubIssueList,
        cancellation: &'a dyn ProcessCancellation,
    ) -> GitHubFuture<'a, Vec<GitHubIssue>>;

    fn search_issues<'a>(
        &'a self,
        request: &'a GitHubIssueSearch,
        cancellation: &'a dyn ProcessCancellation,
    ) -> GitHubFuture<'a, Vec<GitHubIssue>>;

    fn create_issue<'a>(
        &'a self,
        request: &'a GitHubIssueCreate,
        cancellation: &'a dyn ProcessCancellation,
    ) -> GitHubFuture<'a, GitHubIssue>;

    fn edit_issue<'a>(
        &'a self,
        request: &'a GitHubIssueEdit,
        cancellation: &'a dyn ProcessCancellation,
    ) -> GitHubFuture<'a, GitHubIssue>;

    fn close_issue<'a>(
        &'a self,
        repo: &'a GitHubRepositoryRef,
        number: u64,
        reason: GitHubCloseReason,
        cancellation: &'a dyn ProcessCancellation,
    ) -> GitHubFuture<'a, GitHubIssue>;

    fn list_comments<'a>(
        &'a self,
        repo: &'a GitHubRepositoryRef,
        number: u64,
        cancellation: &'a dyn ProcessCancellation,
    ) -> GitHubFuture<'a, Vec<GitHubComment>>;

    fn create_comment<'a>(
        &'a self,
        repo: &'a GitHubRepositoryRef,
        number: u64,
        body: &'a str,
        cancellation: &'a dyn ProcessCancellation,
    ) -> GitHubFuture<'a, GitHubComment>;

    fn edit_comment<'a>(
        &'a self,
        repo: &'a GitHubRepositoryRef,
        comment_id: u64,
        body: &'a str,
        cancellation: &'a dyn ProcessCancellation,
    ) -> GitHubFuture<'a, GitHubComment>;

    fn delete_comment<'a>(
        &'a self,
        repo: &'a GitHubRepositoryRef,
        comment_id: u64,
        cancellation: &'a dyn ProcessCancellation,
    ) -> GitHubFuture<'a, ()>;

    fn list_labels<'a>(
        &'a self,
        repo: &'a GitHubRepositoryRef,
        cancellation: &'a dyn ProcessCancellation,
    ) -> GitHubFuture<'a, Vec<GitHubLabel>>;

    fn create_label<'a>(
        &'a self,
        request: &'a GitHubLabelCreate,
        cancellation: &'a dyn ProcessCancellation,
    ) -> GitHubFuture<'a, GitHubLabel>;

    fn add_label<'a>(
        &'a self,
        repo: &'a GitHubRepositoryRef,
        number: u64,
        label: &'a str,
        cancellation: &'a dyn ProcessCancellation,
    ) -> GitHubFuture<'a, Vec<GitHubLabel>>;

    fn remove_label<'a>(
        &'a self,
        repo: &'a GitHubRepositoryRef,
        number: u64,
        label: &'a str,
        cancellation: &'a dyn ProcessCancellation,
    ) -> GitHubFuture<'a, Vec<GitHubLabel>>;
}

pub type GitHubFuture<'a, T> =
    Pin<Box<dyn Future<Output = Result<T, GitHubOperationError>> + Send + 'a>>;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum GitHubOperationErrorKind {
    InvalidInput,
    Authentication,
    Permission,
    SsoRequired,
    NotFound,
    RateLimited,
    MalformedResponse,
    LimitExceeded,
    Transport,
    AmbiguousMutation,
    Cancelled,
    DeadlineExceeded,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct GitHubOperationError {
    kind: GitHubOperationErrorKind,
    status: Option<u16>,
    retry_after: Option<Duration>,
    detail: SafeText,
}

impl GitHubOperationError {
    #[must_use]
    pub fn new(
        kind: GitHubOperationErrorKind,
        status: Option<u16>,
        retry_after: Option<Duration>,
        detail: impl AsRef<str>,
    ) -> Self {
        Self {
            kind,
            status,
            retry_after,
            detail: SafeText::from_untrusted(detail),
        }
    }

    #[must_use]
    pub const fn kind(&self) -> GitHubOperationErrorKind {
        self.kind
    }

    #[must_use]
    pub const fn status(&self) -> Option<u16> {
        self.status
    }

    #[must_use]
    pub const fn retry_after(&self) -> Option<Duration> {
        self.retry_after
    }
}

impl fmt::Display for GitHubOperationError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        self.detail.fmt(formatter)
    }
}

impl Error for GitHubOperationError {}

#[derive(Clone, Debug, Eq, Hash, PartialEq)]
pub struct GitHubRepositoryRef {
    owner: String,
    name: String,
}

impl GitHubRepositoryRef {
    /// Build a repository reference from path-safe GitHub slug components.
    ///
    /// # Errors
    /// Rejects empty, dot-segment, non-ASCII, and path-delimiter input.
    pub fn new(
        owner: impl Into<String>,
        name: impl Into<String>,
    ) -> Result<Self, GitHubOperationError> {
        let value = Self {
            owner: owner.into(),
            name: name.into(),
        };
        if valid_repository_part(&value.owner) && valid_repository_part(&value.name) {
            Ok(value)
        } else {
            Err(GitHubOperationError::new(
                GitHubOperationErrorKind::InvalidInput,
                None,
                None,
                "GitHub repository owner or name is invalid",
            ))
        }
    }

    #[must_use]
    pub fn owner(&self) -> &str {
        &self.owner
    }

    #[must_use]
    pub fn name(&self) -> &str {
        &self.name
    }
}

fn valid_repository_part(value: &str) -> bool {
    !value.is_empty()
        && value.len() <= 100
        && value != "."
        && value != ".."
        && value
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'.' | b'_' | b'-'))
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct GitHubRepository {
    pub id: u64,
    pub name_with_owner: String,
    pub url: String,
    pub default_branch: String,
    pub private: bool,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum GitHubIssueState {
    Open,
    Closed,
    All,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum GitHubCloseReason {
    Completed,
    NotPlanned,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct GitHubIssue {
    pub id: u64,
    pub number: u64,
    pub title: String,
    pub body: String,
    pub state: GitHubIssueState,
    pub url: String,
    pub author: String,
    pub labels: Vec<GitHubLabel>,
    pub comments: u32,
    pub created_at: String,
    pub updated_at: String,
    pub is_pull_request: bool,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct GitHubComment {
    pub id: u64,
    pub body: String,
    pub author: String,
    pub created_at: String,
    pub updated_at: String,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct GitHubLabel {
    pub id: u64,
    pub name: String,
    pub color: String,
    pub description: String,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct GitHubIssueList {
    pub repo: GitHubRepositoryRef,
    pub state: GitHubIssueState,
    pub labels: Vec<String>,
    pub limit: usize,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct GitHubIssueSearch {
    pub repo: GitHubRepositoryRef,
    pub query: String,
    pub limit: usize,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct GitHubIssueCreate {
    pub repo: GitHubRepositoryRef,
    pub title: String,
    pub body: String,
    pub labels: Vec<String>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct GitHubIssueEdit {
    pub repo: GitHubRepositoryRef,
    pub number: u64,
    pub title: Option<String>,
    pub body: Option<String>,
    pub labels: Option<Vec<String>>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct GitHubLabelCreate {
    pub repo: GitHubRepositoryRef,
    pub name: String,
    pub color: String,
    pub description: String,
}

/// Owned future returned by the object-safe GitHub Actions port.
pub type GitHubActionsFuture<'service, T> =
    Pin<Box<dyn Future<Output = Result<T, GitHubActionsError>> + Send + 'service>>;

/// Typed workflow, job, check, control, and log operations.
pub trait GitHubActionsService: GitHubService {
    fn list_workflow_runs<'service>(
        &'service self,
        repository: &'service GitHubRepositoryRef,
        filters: &'service WorkflowRunFilters,
        cancellation: &'service dyn ProcessCancellation,
    ) -> GitHubActionsFuture<'service, Vec<WorkflowRun>>;

    fn workflow_run<'service>(
        &'service self,
        repository: &'service GitHubRepositoryRef,
        run_id: u64,
        cancellation: &'service dyn ProcessCancellation,
    ) -> GitHubActionsFuture<'service, WorkflowRun>;

    fn workflow_jobs<'service>(
        &'service self,
        repository: &'service GitHubRepositoryRef,
        run_id: u64,
        cancellation: &'service dyn ProcessCancellation,
    ) -> GitHubActionsFuture<'service, Vec<WorkflowJob>>;

    fn check_runs<'service>(
        &'service self,
        repository: &'service GitHubRepositoryRef,
        git_reference: &'service str,
        cancellation: &'service dyn ProcessCancellation,
    ) -> GitHubActionsFuture<'service, Vec<CheckRun>>;

    fn rerun_workflow<'service>(
        &'service self,
        repository: &'service GitHubRepositoryRef,
        run_id: u64,
        failed_only: bool,
        cancellation: &'service dyn ProcessCancellation,
    ) -> GitHubActionsFuture<'service, GitHubMutationOutcome>;

    fn dispatch_workflow<'service>(
        &'service self,
        request: &'service WorkflowDispatchRequest,
        cancellation: &'service dyn ProcessCancellation,
    ) -> GitHubActionsFuture<'service, GitHubMutationOutcome>;

    fn download_workflow_logs<'service>(
        &'service self,
        repository: &'service GitHubRepositoryRef,
        run_id: u64,
        cancellation: &'service dyn ProcessCancellation,
    ) -> GitHubActionsFuture<'service, WorkflowLogArchive>;
}

/// Additive filters for listing workflow runs.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct WorkflowRunFilters {
    pub branch: Option<String>,
    pub workflow: Option<String>,
    pub event: Option<String>,
    pub status: Option<String>,
    pub commit: Option<String>,
    pub limit: usize,
}

impl WorkflowRunFilters {
    #[must_use]
    pub const fn effective_limit(&self) -> usize {
        if self.limit == 0 { 5 } else { self.limit }
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct WorkflowRun {
    pub database_id: u64,
    pub status: String,
    pub conclusion: Option<String>,
    pub head_sha: String,
    pub event: String,
    pub attempt: u32,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct WorkflowDispatchRequest {
    pub repository: GitHubRepositoryRef,
    pub workflow: String,
    pub git_reference: String,
}

#[derive(Clone, Debug, PartialEq)]
pub struct WorkflowJob {
    pub name: String,
    pub status: String,
    pub conclusion: Option<String>,
    pub wall_clock_seconds: Option<f64>,
}

impl WorkflowJob {
    #[must_use]
    pub fn is_failed(&self) -> bool {
        self.conclusion.as_deref() == Some("failure")
    }

    #[must_use]
    pub fn harness_shard(&self) -> Option<u32> {
        let shard = self
            .name
            .strip_prefix("test-harnesses (")?
            .strip_suffix(')')?;
        shard.parse().ok()
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum CheckBucket {
    Pass,
    Fail,
    Pending,
    Skipping,
    Cancel,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct CheckRun {
    pub name: String,
    pub status: String,
    pub conclusion: Option<String>,
    pub bucket: CheckBucket,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum GitHubMutationOutcome {
    Accepted,
    Reconciled,
    Ambiguous,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct WorkflowLogArchive {
    bytes: Vec<u8>,
}

impl WorkflowLogArchive {
    /// Maximum bytes accepted from a workflow log download and rendered from
    /// its archive entries.
    pub const MAX_BYTES: usize = 64 * 1024 * 1024;

    #[must_use]
    pub const fn new(bytes: Vec<u8>) -> Self {
        Self { bytes }
    }

    #[must_use]
    pub fn as_bytes(&self) -> &[u8] {
        &self.bytes
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum GitHubActionsErrorKind {
    InvalidInput,
    Authorization,
    RateLimited,
    Transport,
    Response,
    Redirect,
    LogLimit,
    Cancelled,
    DeadlineExceeded,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct GitHubActionsError {
    kind: GitHubActionsErrorKind,
    detail: SafeText,
}

impl GitHubActionsError {
    #[must_use]
    pub fn new(kind: GitHubActionsErrorKind, detail: impl AsRef<str>) -> Self {
        Self {
            kind,
            detail: SafeText::from_untrusted(detail),
        }
    }

    #[must_use]
    pub const fn kind(&self) -> GitHubActionsErrorKind {
        self.kind
    }
}

impl std::fmt::Display for GitHubActionsError {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        self.detail.fmt(formatter)
    }
}

impl std::error::Error for GitHubActionsError {}

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

    #[test]
    fn actions_errors_render_their_safe_detail() {
        let error = GitHubActionsError::new(GitHubActionsErrorKind::Transport, "request failed");
        assert_eq!(error.to_string(), "request failed");
    }
}
