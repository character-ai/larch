//! Narrow GitHub service port and shared hostile-transport policy.

use crate::{ProcessCancellation, RetryClass, SafeText, StopReason};
use std::{error::Error, fmt, future::Future, pin::Pin, sync::LazyLock, time::Duration};

use regex::Regex;

/// The only content type accepted for a binary release-asset download.
pub const ASSET_MEDIA_TYPE: &str = "application/octet-stream";
const UPLOADED_ASSET_STATE: &str = "uploaded";
const MAX_ASSET_NAME_BYTES: usize = 255;

static DIGEST_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^sha256:[0-9a-f]{64}$").expect("static digest regex must compile")
});
static OBJECT_ID_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$").expect("static object-id regex must compile")
});

/// Injectable GitHub boundary used by domain code.
///
/// Operation leaves extend this boundary with typed DTOs. The foundation does
/// not expose raw URLs, arbitrary GraphQL documents, or a concrete HTTP client.
pub trait GitHubService: Send + Sync {
    /// Return the immutable transport policy enforced by this service.
    fn transport_policy(&self) -> GitHubTransportPolicy;

    /// Return the login whose credential authenticated this service.
    fn authenticated_user<'a>(
        &'a self,
        cancellation: &'a dyn ProcessCancellation,
    ) -> GitHubFuture<'a, GitHubUser>;

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
    ) -> GitHubFuture<'a, GitHubIssueListResult>;

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
    /// The request never reached GitHub: DNS failure, connect timeout, or a
    /// refused or reset connection. Distinct from `Transport`, which also
    /// covers HTTP 5xx and other post-connection transport faults, so an
    /// offline-aware caller can retry this class while leaving HTTP-level
    /// failures fail-closed.
    Unreachable,
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

    /// Return whether the request never reached GitHub (DNS failure, connect
    /// timeout, or a refused or reset connection). Offline-aware callers retry
    /// this class within a bounded connectivity window; every other kind,
    /// including HTTP 4xx and 5xx, stays fail-closed.
    #[must_use]
    pub const fn is_unreachable(&self) -> bool {
        matches!(self.kind, GitHubOperationErrorKind::Unreachable)
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
    /// The immediate parent when this repository is a fork.
    pub parent: Option<GitHubRepositoryRef>,
}

/// One authenticated GitHub identity.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct GitHubUser {
    /// GitHub login suitable for typed assignee requests.
    pub login: String,
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
    /// GitHub's optional close reason, empty when absent or not applicable.
    pub state_reason: String,
    pub url: String,
    pub author: String,
    /// GitHub logins currently assigned to the issue.
    pub assignees: Vec<String>,
    pub labels: Vec<GitHubLabel>,
    pub comments: u32,
    pub created_at: String,
    /// RFC 3339 close timestamp, empty while the issue is open.
    pub closed_at: String,
    pub updated_at: String,
    pub is_pull_request: bool,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct GitHubComment {
    pub id: u64,
    pub body: String,
    /// Web URL of the comment, the anchor a caller republishes.
    pub url: String,
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

/// Whether a list caller demands the complete matching set or accepts a
/// visible partial snapshot when the reviewed transport bound is reached.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum GitHubIssueListMode {
    /// Refuse with [`GitHubOperationErrorKind::LimitExceeded`] when a
    /// continuation remains at the transport page or item bound. Fail-closed
    /// consumers that must reason over every matching issue use this.
    Exhaustive,
    /// Return the admitted rows with `truncated = true` when the transport
    /// bound cut the scan short. Callers whose contract already permits a
    /// visible partial snapshot use this.
    BoundedPartial,
}

/// Whether an issue-list consumer needs issue-body content.
///
/// GitHub's REST list endpoint includes bodies even when a consumer only needs
/// metadata. [`GitHubIssueBodyMode::Omit`] keeps those unused fields out of the
/// returned domain value and out of per-string validation, while retaining the
/// response-wide transport bounds.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum GitHubIssueBodyMode {
    /// Preserve and validate issue-body fields for a consumer that reads them.
    Include,
    /// Discard issue-body fields before conversion because the consumer needs metadata only.
    Omit,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct GitHubIssueList {
    pub repo: GitHubRepositoryRef,
    pub state: GitHubIssueState,
    pub labels: Vec<String>,
    pub limit: usize,
    pub mode: GitHubIssueListMode,
    pub body_mode: GitHubIssueBodyMode,
}

/// The typed outcome of a bounded issue list.
///
/// `issues` excludes pull requests and foreign-repository rows, while
/// `raw_rows_scanned` counts every untrusted REST row those filters dropped, so
/// a caller can tell filtered output length from raw pagination. `truncated`
/// reports whether the transport bound (or, for a bounded-partial caller, the
/// requested count) left a continuation unread.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct GitHubIssueListResult {
    pub issues: Vec<GitHubIssue>,
    pub raw_rows_scanned: usize,
    pub truncated: bool,
}

/// Why a bounded issue scan stopped before its feed ended.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum GitHubListStop {
    /// The caller's own requested issue count was satisfied.
    RequestedLimit,
    /// The reviewed transport item bound was reached.
    TransportItems,
    /// The reviewed transport page bound was reached with a continuation.
    PageLimit,
    /// The feed ended within every bound.
    Exhausted,
}

/// The typed result of resolving a stopped scan against its caller mode.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum GitHubListOutcome {
    /// A usable snapshot, truncated or complete.
    Complete(GitHubIssueListResult),
    /// An exhaustive caller reached a transport bound with a continuation.
    Refused,
}

/// Pure accountant for one bounded issue scan.
///
/// The adapter feeds it every raw REST row in page order, including pull
/// requests and foreign-repository rows, so the transport item bound counts the
/// same untrusted rows the API returned rather than the filtered issue rows.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct GitHubIssueScan {
    retained: usize,
    raw_scanned: usize,
    limit: usize,
    items_limit: usize,
    pages_limit: usize,
}

impl GitHubIssueScan {
    /// Start a scan bounded by the caller's requested issue count and the
    /// reviewed transport limits.
    #[must_use]
    pub const fn new(limit: usize, policy: GitHubTransportPolicy) -> Self {
        Self {
            retained: 0,
            raw_scanned: 0,
            limit,
            items_limit: policy.limits().items(),
            pages_limit: policy.limits().pages(),
        }
    }

    /// The reviewed transport page bound, the number of continuations the
    /// driver may follow.
    #[must_use]
    pub const fn pages_limit(&self) -> usize {
        self.pages_limit
    }

    /// Every raw REST row counted so far, pull requests included.
    #[must_use]
    pub const fn raw_scanned(&self) -> usize {
        self.raw_scanned
    }

    /// Count one raw REST row and report whether the driver should retain it.
    ///
    /// A row is retained only when it survives the caller's filter (`retain`)
    /// and the requested issue count is not yet met; every row, retained or
    /// not, counts against the transport item bound.
    pub const fn count_row(&mut self, retain: bool) -> bool {
        self.raw_scanned += 1;
        if retain && self.retained < self.limit {
            self.retained += 1;
            true
        } else {
            false
        }
    }

    /// The stop the running counts imply, if the scan must halt on this row.
    ///
    /// The transport item bound is reported before the requested count, so a
    /// caller whose requested count equals the transport bound stops as a
    /// transport refusal rather than a satisfied request.
    #[must_use]
    pub const fn stop(&self) -> Option<GitHubListStop> {
        if self.raw_scanned >= self.items_limit {
            Some(GitHubListStop::TransportItems)
        } else if self.retained >= self.limit {
            Some(GitHubListStop::RequestedLimit)
        } else {
            None
        }
    }
}

/// Resolve a stopped scan into a typed outcome for its caller mode.
///
/// `continuation` is whether more rows remained (on this page or a next page)
/// when the scan stopped. An exhaustive caller that reached a transport bound
/// with a continuation is refused; a bounded-partial caller receives the
/// admitted rows marked truncated. Reaching the caller's own requested count is
/// never a refusal and never truncation for an exhaustive caller.
#[must_use]
pub fn resolve_issue_list(
    issues: Vec<GitHubIssue>,
    raw_rows_scanned: usize,
    stop: GitHubListStop,
    continuation: bool,
    mode: GitHubIssueListMode,
) -> GitHubListOutcome {
    let transport_bound = matches!(
        stop,
        GitHubListStop::TransportItems | GitHubListStop::PageLimit
    );
    if continuation && transport_bound && matches!(mode, GitHubIssueListMode::Exhaustive) {
        return GitHubListOutcome::Refused;
    }
    let truncated =
        continuation && (transport_bound || matches!(mode, GitHubIssueListMode::BoundedPartial));
    GitHubListOutcome::Complete(GitHubIssueListResult {
        issues,
        raw_rows_scanned,
        truncated,
    })
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
    /// GitHub logins to assign atomically with creation.
    pub assignees: Vec<String>,
    pub labels: Vec<String>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct GitHubIssueEdit {
    pub repo: GitHubRepositoryRef,
    pub number: u64,
    pub title: Option<String>,
    pub body: Option<String>,
    pub labels: Option<Vec<String>>,
    /// Replace the issue or pull request assignee set when present.
    pub assignees: Option<Vec<String>>,
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
    fn pull_request_ci_state<'service>(
        &'service self,
        repository: &'service GitHubRepositoryRef,
        number: u64,
        cancellation: &'service dyn ProcessCancellation,
    ) -> GitHubActionsFuture<'service, PullRequestCiState>;

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
    /// The run's workflow display name, which callers filter on because the
    /// REST workflow selector accepts only a file name or numeric identifier.
    pub workflow_name: String,
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
    pub details_url: Option<String>,
    /// Human-facing status-context detail, when supplied by GitHub.
    pub description: Option<String>,
    /// Completed wall-clock duration, when GitHub supplied both timestamps.
    pub wall_clock_seconds: Option<u64>,
    pub bucket: CheckBucket,
}

/// Pull-request fields needed by the CI monitor's typed GitHub read.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct PullRequestCiState {
    pub merged: bool,
    pub merge_state: PullRequestMergeState,
}

/// Conservative merge-state vocabulary used by the CI decision boundary.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum PullRequestMergeState {
    Behind,
    Blocked,
    Clean,
    Dirty,
    HasHooks,
    Unknown,
    Unstable,
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
    /// Maximum file entries accepted from one workflow log archive.
    pub const MAX_ENTRIES: usize = 1_024;

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

/// Scope for the overall deadline of one paginated issue-list operation.
///
/// The exhaustive-history exception keeps each page read bounded while its
/// caller owns a separately bounded aggregate deadline.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum GitHubIssueListTimeoutScope {
    /// One overall deadline covers the complete paginated issue list.
    EntireList,
    /// Each page read receives the ordinary overall deadline independently.
    PerPage,
}

/// Immutable policy shared by every GitHub operation adapter.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct GitHubTransportPolicy {
    connect_timeout: Duration,
    read_timeout: Duration,
    write_timeout: Duration,
    overall_timeout: Duration,
    issue_list_timeout_scope: GitHubIssueListTimeoutScope,
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
            issue_list_timeout_scope: GitHubIssueListTimeoutScope::EntireList,
            limits: GitHubResponseLimits {
                body_bytes: 2 * 1024 * 1024,
                pages: 20,
                items: 2_000,
                string_bytes: 64 * 1024,
                nesting_depth: 64,
            },
        }
    }

    /// Reviewed exhaustive-history policy for the daily migration audit.
    ///
    /// The aggregate must account for historical managed leaves, so its issue
    /// corpus is larger than ordinary interactive command snapshots. This is
    /// still a fixed, fail-closed transport boundary: it admits at most 100
    /// pages and 10,000 raw REST rows. Historical issue plans can legitimately
    /// exceed an interactive issue body's 64 KiB cap, so it raises that one
    /// field cap to 256 KiB. A full repository corpus can require more than
    /// the standard interactive aggregate deadline, so callers pair this
    /// policy with [`Self::migration_audit_aggregate_timeout`] while preserving
    /// the standard per-request, response-byte, nesting, and retry limits.
    #[must_use]
    pub const fn migration_audit() -> Self {
        Self {
            connect_timeout: Duration::from_secs(10),
            read_timeout: Duration::from_secs(30),
            write_timeout: Duration::from_secs(30),
            overall_timeout: Duration::from_secs(60),
            issue_list_timeout_scope: GitHubIssueListTimeoutScope::PerPage,
            limits: GitHubResponseLimits {
                body_bytes: 2 * 1024 * 1024,
                pages: 100,
                items: 10_000,
                string_bytes: 256 * 1024,
                nesting_depth: 64,
            },
        }
    }

    /// Fixed deadline for one complete migration-audit snapshot.
    ///
    /// This is intentionally separate from the client's per-operation timeout:
    /// a slow individual request keeps the ordinary 60-second bound, while the
    /// complete exhaustive-history read may consume up to three minutes.
    #[must_use]
    pub const fn migration_audit_aggregate_timeout() -> Duration {
        Duration::from_secs(180)
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

    /// Return whether one issue-list deadline covers the full list or each page.
    #[must_use]
    pub const fn issue_list_timeout_scope(self) -> GitHubIssueListTimeoutScope {
        self.issue_list_timeout_scope
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

/// Why a release or asset value violated its fail-closed contract.
///
/// Every variant renders a fixed, secret-free message. Untrusted API values
/// such as asset names, tags, or object ids never enter a diagnostic.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ReleaseDataErrorKind {
    /// An asset database id was absent or zero.
    InvalidAssetId,
    /// An asset name was empty, oversized, or carried path or control bytes.
    InvalidAssetName,
    /// An asset byte size was absent, zero, or not a positive integer.
    InvalidAssetSize,
    /// An asset digest was not a lowercase `sha256:<64 hex>` value.
    InvalidAssetDigest,
    /// An asset was present but not in the uploaded state.
    AssetNotUploaded,
    /// A tag reference resolved to a value that was not a Git object id.
    InvalidObjectId,
    /// A release state carried an invalid database id, tag, or mutability flag.
    InvalidReleaseState,
    /// More than one release claimed the same tag.
    DuplicateReleaseTag,
    /// A streamed asset exceeded the reviewed per-asset byte cap.
    AssetTooLarge,
    /// A download response advertised a content type other than octet-stream.
    UnexpectedContentType,
    /// A streamed asset ended before its declared length.
    TruncatedAsset,
}

/// A release or asset contract violation that never retains API text.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct ReleaseDataError {
    kind: ReleaseDataErrorKind,
}

impl ReleaseDataError {
    const fn new(kind: ReleaseDataErrorKind) -> Self {
        Self { kind }
    }

    /// Return the stable failure class.
    #[must_use]
    pub const fn kind(self) -> ReleaseDataErrorKind {
        self.kind
    }
}

impl fmt::Display for ReleaseDataError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(match self.kind {
            ReleaseDataErrorKind::InvalidAssetId => "release asset database id is invalid",
            ReleaseDataErrorKind::InvalidAssetName => "release asset name is invalid",
            ReleaseDataErrorKind::InvalidAssetSize => {
                "release asset size is not a positive integer"
            }
            ReleaseDataErrorKind::InvalidAssetDigest => {
                "release asset digest is not a lowercase sha256 digest"
            }
            ReleaseDataErrorKind::AssetNotUploaded => "release asset is not in the uploaded state",
            ReleaseDataErrorKind::InvalidObjectId => "tag reference is not a Git object id",
            ReleaseDataErrorKind::InvalidReleaseState => "release state fields are invalid",
            ReleaseDataErrorKind::DuplicateReleaseTag => "more than one release claims the tag",
            ReleaseDataErrorKind::AssetTooLarge => "release asset exceeds the byte cap",
            ReleaseDataErrorKind::UnexpectedContentType => {
                "release asset download has an unexpected content type"
            }
            ReleaseDataErrorKind::TruncatedAsset => {
                "release asset ended before its declared length"
            }
        })
    }
}

impl Error for ReleaseDataError {}

/// A lowercase `sha256:<64 hex>` release-asset digest.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct AssetDigest(String);

impl AssetDigest {
    /// Parse and validate a release-asset digest.
    ///
    /// # Errors
    /// Rejects any value that is not a lowercase `sha256:<64 hex>` digest.
    pub fn parse(value: &str) -> Result<Self, ReleaseDataError> {
        if DIGEST_RE.is_match(value) {
            Ok(Self(value.to_owned()))
        } else {
            Err(ReleaseDataError::new(
                ReleaseDataErrorKind::InvalidAssetDigest,
            ))
        }
    }

    /// Borrow the canonical digest text.
    #[must_use]
    pub fn as_str(&self) -> &str {
        &self.0
    }
}

/// A validated Git object id that a tag reference resolved to.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct TagObjectId(String);

impl TagObjectId {
    /// Validate a resolved tag object id.
    ///
    /// # Errors
    /// Rejects any value that is not a 40- or 64-character lowercase hex id.
    pub fn parse(value: &str) -> Result<Self, ReleaseDataError> {
        if OBJECT_ID_RE.is_match(value) {
            Ok(Self(value.to_owned()))
        } else {
            Err(ReleaseDataError::new(ReleaseDataErrorKind::InvalidObjectId))
        }
    }

    /// Borrow the object id text.
    #[must_use]
    pub fn as_str(&self) -> &str {
        &self.0
    }
}

/// Resolve the object id a tag points at, preferring the peeled target.
///
/// This mirrors `git ls-remote origin refs/tags/<tag> refs/tags/<tag>^{}`:
/// an annotated tag's peeled commit wins over the tag object itself, and an
/// absent tag yields `None`.
///
/// # Errors
/// Rejects a resolved value that is not a Git object id.
pub fn resolve_tag_object_id(
    direct: Option<&str>,
    peeled: Option<&str>,
) -> Result<Option<TagObjectId>, ReleaseDataError> {
    peeled
        .or(direct)
        .map_or(Ok(None), |value| TagObjectId::parse(value).map(Some))
}

/// Validated metadata for one uploaded release asset.
///
/// Fields mirror the machine-readable shape current release callers consume:
/// a name, a positive byte size, and a `sha256:` digest for an uploaded asset.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RemoteAsset {
    database_id: u64,
    name: String,
    size: u64,
    digest: AssetDigest,
}

impl RemoteAsset {
    /// Validate one asset metadata record.
    ///
    /// # Errors
    /// Rejects an invalid id or name, a non-positive size, a malformed digest,
    /// or an asset whose state is anything other than uploaded.
    pub fn new(
        database_id: u64,
        name: &str,
        size: u64,
        digest: &str,
        state: &str,
    ) -> Result<Self, ReleaseDataError> {
        if database_id == 0 {
            return Err(ReleaseDataError::new(ReleaseDataErrorKind::InvalidAssetId));
        }
        if !is_valid_asset_name(name) {
            return Err(ReleaseDataError::new(
                ReleaseDataErrorKind::InvalidAssetName,
            ));
        }
        if size == 0 {
            return Err(ReleaseDataError::new(
                ReleaseDataErrorKind::InvalidAssetSize,
            ));
        }
        if state != UPLOADED_ASSET_STATE {
            return Err(ReleaseDataError::new(
                ReleaseDataErrorKind::AssetNotUploaded,
            ));
        }
        Ok(Self {
            database_id,
            name: name.to_owned(),
            size,
            digest: AssetDigest::parse(digest)?,
        })
    }

    /// Return the release asset database id used by the bounded download API.
    #[must_use]
    pub const fn database_id(&self) -> u64 {
        self.database_id
    }

    /// Borrow the asset name.
    #[must_use]
    pub fn name(&self) -> &str {
        &self.name
    }

    /// Return the asset byte size.
    #[must_use]
    pub const fn size(&self) -> u64 {
        self.size
    }

    /// Borrow the asset digest.
    #[must_use]
    pub const fn digest(&self) -> &AssetDigest {
        &self.digest
    }
}

fn is_valid_asset_name(name: &str) -> bool {
    !name.is_empty()
        && name.len() <= MAX_ASSET_NAME_BYTES
        && !name.contains(['/', '\\'])
        && !name.chars().any(char::is_control)
}

/// Validated state of one release selected by tag.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ReleaseState {
    database_id: u64,
    tag: String,
    name: Option<String>,
    target_commitish: Option<String>,
    draft: bool,
    immutable: bool,
    prerelease: bool,
    published_at: Option<String>,
    assets: Vec<RemoteAsset>,
}

impl ReleaseState {
    /// Validate one release state record for the requested tag.
    ///
    /// # Errors
    /// Rejects a zero database id or a tag that does not match the request.
    pub fn new(
        database_id: u64,
        tag: &str,
        draft: bool,
        immutable: bool,
        assets: Vec<RemoteAsset>,
    ) -> Result<Self, ReleaseDataError> {
        if database_id == 0 || tag.is_empty() {
            return Err(ReleaseDataError::new(
                ReleaseDataErrorKind::InvalidReleaseState,
            ));
        }
        Ok(Self {
            database_id,
            tag: tag.to_owned(),
            name: None,
            target_commitish: None,
            draft,
            immutable,
            prerelease: false,
            published_at: None,
            assets,
        })
    }

    /// Attach the publication fields returned by GitHub's release API.
    #[must_use]
    pub fn with_publication(mut self, prerelease: bool, published_at: Option<String>) -> Self {
        self.prerelease = prerelease;
        self.published_at = published_at;
        self
    }

    /// Attach the GitHub staging identity used to recover a mutable draft.
    #[must_use]
    pub fn with_staging_identity(mut self, name: Option<String>, target_commitish: String) -> Self {
        self.name = name.filter(|value| !value.is_empty());
        self.target_commitish = (!target_commitish.is_empty()).then_some(target_commitish);
        self
    }

    /// Return the release database id.
    #[must_use]
    pub const fn database_id(&self) -> u64 {
        self.database_id
    }

    /// Borrow the release tag.
    #[must_use]
    pub fn tag(&self) -> &str {
        &self.tag
    }

    /// Borrow the optional release title returned by GitHub.
    #[must_use]
    pub fn name(&self) -> Option<&str> {
        self.name.as_deref()
    }

    /// Borrow the optional target commitish returned by GitHub.
    #[must_use]
    pub fn target_commitish(&self) -> Option<&str> {
        self.target_commitish.as_deref()
    }

    /// Return whether the release is still a draft.
    #[must_use]
    pub const fn is_draft(&self) -> bool {
        self.draft
    }

    /// Return whether the release is immutable.
    #[must_use]
    pub const fn is_immutable(&self) -> bool {
        self.immutable
    }

    /// Return whether GitHub marks the release as a prerelease.
    #[must_use]
    pub const fn is_prerelease(&self) -> bool {
        self.prerelease
    }

    /// Borrow the publication timestamp used to order non-draft releases.
    #[must_use]
    pub fn published_at(&self) -> Option<&str> {
        self.published_at.as_deref()
    }

    /// Borrow the uploaded assets.
    #[must_use]
    pub fn assets(&self) -> &[RemoteAsset] {
        &self.assets
    }

    /// Return whether the release is a mutable draft safe to edit.
    #[must_use]
    pub const fn is_mutable_draft(&self) -> bool {
        self.draft && !self.immutable
    }
}

/// Select the single release that claims `tag`, rejecting duplicates.
///
/// This mirrors the bounded-page selection current callers use: exactly one
/// match returns it, no match returns `None`, and more than one match is a
/// fail-closed duplicate error rather than an arbitrary pick.
///
/// # Errors
/// Returns [`ReleaseDataErrorKind::DuplicateReleaseTag`] when two or more
/// releases share the tag.
pub fn select_release_for_tag(
    tag: &str,
    releases: impl IntoIterator<Item = ReleaseState>,
) -> Result<Option<ReleaseState>, ReleaseDataError> {
    let mut selected: Option<ReleaseState> = None;
    for release in releases {
        if release.tag() != tag {
            continue;
        }
        if selected.is_some() {
            return Err(ReleaseDataError::new(
                ReleaseDataErrorKind::DuplicateReleaseTag,
            ));
        }
        selected = Some(release);
    }
    Ok(selected)
}

/// Select one exact-tag release or its mutable GitHub placeholder draft.
///
/// GitHub may temporarily assign an `untagged-*` tag to a draft created just
/// after its Git ref is pushed. The release name and exact target commit bind
/// that placeholder to the requested staging transaction without accepting an
/// unrelated draft.
///
/// # Errors
/// Returns [`ReleaseDataErrorKind::DuplicateReleaseTag`] when more than one
/// release claims the exact or placeholder staging identity.
pub fn select_release_for_staging(
    tag: &str,
    target_commitish: &str,
    releases: impl IntoIterator<Item = ReleaseState>,
) -> Result<Option<ReleaseState>, ReleaseDataError> {
    let mut selected: Option<ReleaseState> = None;
    for release in releases {
        let exact = release.tag() == tag;
        let placeholder = release.is_mutable_draft()
            && release.tag().starts_with("untagged-")
            && release.name() == Some(tag)
            && release.target_commitish() == Some(target_commitish);
        if !exact && !placeholder {
            continue;
        }
        if selected.is_some() {
            return Err(ReleaseDataError::new(
                ReleaseDataErrorKind::DuplicateReleaseTag,
            ));
        }
        selected = Some(release);
    }
    Ok(selected)
}

/// Reject any download content type other than binary octet-stream.
///
/// The media type is compared case-insensitively and tolerates trailing
/// parameters such as `; charset=...`.
///
/// # Errors
/// Returns [`ReleaseDataErrorKind::UnexpectedContentType`] for any other type.
pub fn require_asset_content_type(content_type: &str) -> Result<(), ReleaseDataError> {
    let media_type = content_type
        .split(';')
        .next()
        .unwrap_or("")
        .trim()
        .to_ascii_lowercase();
    if media_type == ASSET_MEDIA_TYPE {
        Ok(())
    } else {
        Err(ReleaseDataError::new(
            ReleaseDataErrorKind::UnexpectedContentType,
        ))
    }
}

/// Enforces the per-asset byte cap and declared-length completeness while a
/// download streams, without buffering the whole asset.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct AssetStreamGuard {
    received: u64,
    max_bytes: u64,
    declared_length: Option<u64>,
}

impl AssetStreamGuard {
    /// Start a guard bounded by `max_bytes` and an optional declared length.
    ///
    /// A declared length greater than the cap is clamped so an oversized
    /// advertisement cannot raise the effective ceiling.
    #[must_use]
    pub const fn new(max_bytes: u64, declared_length: Option<u64>) -> Self {
        Self {
            received: 0,
            max_bytes,
            declared_length,
        }
    }

    /// Account for one received chunk, rejecting an over-cap total.
    ///
    /// # Errors
    /// Returns [`ReleaseDataErrorKind::AssetTooLarge`] when the running total
    /// would exceed the byte cap or the declared length.
    pub fn accept(&mut self, chunk_len: usize) -> Result<(), ReleaseDataError> {
        let next = self
            .received
            .checked_add(chunk_len as u64)
            .ok_or_else(|| ReleaseDataError::new(ReleaseDataErrorKind::AssetTooLarge))?;
        let ceiling = match self.declared_length {
            Some(length) => length.min(self.max_bytes),
            None => self.max_bytes,
        };
        if next > ceiling {
            return Err(ReleaseDataError::new(ReleaseDataErrorKind::AssetTooLarge));
        }
        self.received = next;
        Ok(())
    }

    /// Finish the stream, rejecting a body shorter than its declared length.
    ///
    /// # Errors
    /// Returns [`ReleaseDataErrorKind::TruncatedAsset`] when fewer than the
    /// declared bytes arrived.
    pub const fn finish(self) -> Result<u64, ReleaseDataError> {
        if let Some(length) = self.declared_length
            && self.received < length
        {
            return Err(ReleaseDataError::new(ReleaseDataErrorKind::TruncatedAsset));
        }
        Ok(self.received)
    }

    /// Return the bytes accepted so far.
    #[must_use]
    pub const fn received(&self) -> u64 {
        self.received
    }
}

/// Outcome of reconciling an ambiguous mutation before any retry.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ReconciledMutation {
    /// A read-back proved the mutation already committed; do not repeat it.
    AlreadyApplied,
    /// The mutation is safe to run again within the shared retry policy.
    SafeToRetry(RetryClass),
    /// The failure is permanent or an authorization stop; abort the operation.
    Abort(StopReason),
}

/// Reconcile a classified transport action against an observed post-state.
///
/// A mutation whose transport outcome is ambiguous ([`GitHubRetryAction::ReconcileMutation`])
/// is never blindly repeated: when the read-back shows the effect already
/// landed, the caller stops; otherwise it retries the idempotent operation.
#[must_use]
pub const fn reconcile_mutation(
    action: GitHubRetryAction,
    already_applied: bool,
) -> ReconciledMutation {
    match action {
        GitHubRetryAction::Retry(class) => ReconciledMutation::SafeToRetry(class),
        GitHubRetryAction::Stop(reason) => ReconciledMutation::Abort(reason),
        GitHubRetryAction::ReconcileMutation => {
            if already_applied {
                ReconciledMutation::AlreadyApplied
            } else {
                ReconciledMutation::SafeToRetry(RetryClass::Transient)
            }
        }
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
    fn migration_audit_policy_is_a_bounded_history_expansion() {
        let standard = GitHubTransportPolicy::github_com();
        let audit = GitHubTransportPolicy::migration_audit();
        assert_eq!(audit.connect_timeout(), standard.connect_timeout());
        assert_eq!(audit.read_timeout(), standard.read_timeout());
        assert_eq!(audit.write_timeout(), standard.write_timeout());
        assert_eq!(audit.overall_timeout(), standard.overall_timeout());
        assert_eq!(
            standard.issue_list_timeout_scope(),
            GitHubIssueListTimeoutScope::EntireList
        );
        assert_eq!(
            audit.issue_list_timeout_scope(),
            GitHubIssueListTimeoutScope::PerPage
        );
        assert_eq!(
            GitHubTransportPolicy::migration_audit_aggregate_timeout(),
            Duration::from_secs(180)
        );
        assert_eq!(audit.limits().body_bytes(), standard.limits().body_bytes());
        assert_eq!(audit.limits().string_bytes(), 256 * 1024);
        assert_eq!(
            audit.limits().nesting_depth(),
            standard.limits().nesting_depth()
        );
        assert_eq!(audit.limits().pages(), 100);
        assert_eq!(audit.limits().items(), 10_000);
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

    /// One synthetic REST page: whether each raw row survives the pull-request
    /// and repository filter, and whether a continuation link follows.
    type ScanPage = (Vec<bool>, bool);

    fn placeholder_issue() -> GitHubIssue {
        GitHubIssue {
            id: 1,
            number: 1,
            title: String::new(),
            body: String::new(),
            state: GitHubIssueState::Open,
            state_reason: String::new(),
            url: String::new(),
            author: String::new(),
            assignees: Vec::new(),
            labels: Vec::new(),
            comments: 0,
            created_at: String::new(),
            closed_at: String::new(),
            updated_at: String::new(),
            is_pull_request: false,
        }
    }

    /// Drive the pure bounded-list primitives over synthetic pages, mirroring
    /// the adapter's page walk without any HTTP so the transport-bound math is
    /// covered at the observed live scale.
    fn walk(pages: &[ScanPage], limit: usize, mode: GitHubIssueListMode) -> GitHubListOutcome {
        let policy = GitHubTransportPolicy::github_com();
        let mut scan = GitHubIssueScan::new(limit, policy);
        let mut kept: Vec<GitHubIssue> = Vec::new();
        for (page_index, (rows, has_next)) in pages.iter().enumerate() {
            let count = rows.len();
            for (index, &retain) in rows.iter().enumerate() {
                if scan.count_row(retain) {
                    kept.push(placeholder_issue());
                }
                if let Some(stop) = scan.stop() {
                    let continuation = index + 1 < count || *has_next;
                    return resolve_issue_list(kept, scan.raw_scanned(), stop, continuation, mode);
                }
            }
            if !has_next {
                return resolve_issue_list(
                    kept,
                    scan.raw_scanned(),
                    GitHubListStop::Exhausted,
                    false,
                    mode,
                );
            }
            if page_index + 1 == scan.pages_limit() {
                return resolve_issue_list(
                    kept,
                    scan.raw_scanned(),
                    GitHubListStop::PageLimit,
                    true,
                    mode,
                );
            }
        }
        resolve_issue_list(
            kept,
            scan.raw_scanned(),
            GitHubListStop::Exhausted,
            false,
            mode,
        )
    }

    /// Build the observed live fixture: 20 full pages of 100 raw rows each, of
    /// which 889 are issues and 1,111 are pull requests, with a continuation.
    fn live_scale_pages(final_page_has_next: bool) -> Vec<ScanPage> {
        let mut issues_left = 889_usize;
        let mut pages = Vec::with_capacity(20);
        for page in 0..20 {
            let mut rows = Vec::with_capacity(100);
            for _ in 0..100 {
                // Front-load the issue rows so the retained count is exact.
                let retain = issues_left > 0;
                if retain {
                    issues_left -= 1;
                }
                rows.push(retain);
            }
            let has_next = if page == 19 {
                final_page_has_next
            } else {
                true
            };
            pages.push((rows, has_next));
        }
        pages
    }

    #[test]
    fn bounded_partial_admits_the_live_scale_snapshot_with_truncation() {
        let pages = live_scale_pages(true);
        let GitHubListOutcome::Complete(result) =
            walk(&pages, 2_000, GitHubIssueListMode::BoundedPartial)
        else {
            panic!("bounded-partial must admit the snapshot");
        };
        assert_eq!(result.issues.len(), 889);
        assert_eq!(result.raw_rows_scanned, 2_000);
        assert!(result.truncated);
    }

    #[test]
    fn exhaustive_refuses_the_live_scale_snapshot() {
        let pages = live_scale_pages(true);
        assert_eq!(
            walk(&pages, 2_000, GitHubIssueListMode::Exhaustive),
            GitHubListOutcome::Refused
        );
    }

    #[test]
    fn exactly_twenty_pages_without_a_continuation_is_not_truncated() {
        let pages = live_scale_pages(false);
        for mode in [
            GitHubIssueListMode::Exhaustive,
            GitHubIssueListMode::BoundedPartial,
        ] {
            let GitHubListOutcome::Complete(result) = walk(&pages, 2_000, mode) else {
                panic!("a terminal twentieth page is a complete snapshot");
            };
            assert_eq!(result.issues.len(), 889);
            assert!(!result.truncated);
        }
    }

    #[test]
    fn reaching_the_requested_count_early_never_refuses_an_exhaustive_caller() {
        // Five retainable rows on a page that still has more work: an
        // exhaustive caller (search) gets its five with no refusal and no
        // truncation, while a bounded-partial caller learns older rows remain.
        let pages: Vec<ScanPage> = vec![(vec![true; 100], true)];
        let GitHubListOutcome::Complete(exhaustive) =
            walk(&pages, 5, GitHubIssueListMode::Exhaustive)
        else {
            panic!("reaching the requested count is not a refusal");
        };
        assert_eq!(exhaustive.issues.len(), 5);
        assert!(!exhaustive.truncated);

        let GitHubListOutcome::Complete(bounded) =
            walk(&pages, 5, GitHubIssueListMode::BoundedPartial)
        else {
            panic!("bounded-partial admits the partial set");
        };
        assert_eq!(bounded.issues.len(), 5);
        assert!(bounded.truncated);
    }

    #[test]
    fn a_short_feed_within_every_bound_is_complete_and_untruncated() {
        let pages: Vec<ScanPage> = vec![(vec![true, false, true], false)];
        let GitHubListOutcome::Complete(result) =
            walk(&pages, 2_000, GitHubIssueListMode::Exhaustive)
        else {
            panic!("a feed that ends within bounds is complete");
        };
        assert_eq!(result.issues.len(), 2);
        assert_eq!(result.raw_rows_scanned, 3);
        assert!(!result.truncated);
    }
}

#[cfg(test)]
mod release_tests {
    use super::*;

    const DIGEST: &str = "sha256:1111111111111111111111111111111111111111111111111111111111111111";

    fn asset(name: &str) -> RemoteAsset {
        RemoteAsset::new(7, name, 10, DIGEST, "uploaded").expect("valid asset")
    }

    fn release(tag: &str, draft: bool, immutable: bool) -> ReleaseState {
        ReleaseState::new(42, tag, draft, immutable, vec![asset("larch")]).expect("valid release")
    }

    #[test]
    fn asset_metadata_validates_name_size_digest_and_state() {
        let parsed = asset("larch-v1.2.3-x86_64-unknown-linux-gnu.tar.gz");
        assert_eq!(parsed.database_id(), 7);
        assert_eq!(parsed.size(), 10);
        assert_eq!(parsed.digest().as_str(), DIGEST);
        assert_eq!(
            RemoteAsset::new(0, "larch", 10, DIGEST, "uploaded")
                .expect_err("zero id should fail")
                .kind(),
            ReleaseDataErrorKind::InvalidAssetId
        );

        for (name, size, digest, state, kind) in [
            (
                "",
                10,
                DIGEST,
                "uploaded",
                ReleaseDataErrorKind::InvalidAssetName,
            ),
            (
                "../escape",
                10,
                DIGEST,
                "uploaded",
                ReleaseDataErrorKind::InvalidAssetName,
            ),
            (
                "larch",
                0,
                DIGEST,
                "uploaded",
                ReleaseDataErrorKind::InvalidAssetSize,
            ),
            (
                "larch",
                10,
                "sha1:dead",
                "uploaded",
                ReleaseDataErrorKind::InvalidAssetDigest,
            ),
            (
                "larch",
                10,
                DIGEST,
                "starter",
                ReleaseDataErrorKind::AssetNotUploaded,
            ),
        ] {
            assert_eq!(
                RemoteAsset::new(7, name, size, digest, state)
                    .expect_err("invalid asset should fail")
                    .kind(),
                kind
            );
        }
    }

    #[test]
    fn digest_and_object_id_reject_uppercase_and_wrong_length() {
        assert!(AssetDigest::parse(&DIGEST.to_uppercase()).is_err());
        assert!(TagObjectId::parse("0123456789abcdef0123456789abcdef01234567").is_ok());
        assert_eq!(
            TagObjectId::parse("XYZ")
                .expect_err("non-hex id should fail")
                .kind(),
            ReleaseDataErrorKind::InvalidObjectId
        );
    }

    #[test]
    fn tag_resolution_prefers_peeled_target_and_tolerates_absence() {
        let oid = "0123456789abcdef0123456789abcdef01234567";
        let peeled = "89abcdef0123456789abcdef0123456789abcdef";
        assert_eq!(
            resolve_tag_object_id(Some(oid), Some(peeled))
                .expect("valid")
                .expect("present")
                .as_str(),
            peeled
        );
        assert_eq!(
            resolve_tag_object_id(Some(oid), None)
                .expect("valid")
                .expect("present")
                .as_str(),
            oid
        );
        assert!(resolve_tag_object_id(None, None).expect("valid").is_none());
    }

    #[test]
    fn release_selection_rejects_duplicate_tags_and_reports_absence() {
        let releases = [release("v1", true, false), release("v2", false, true)];
        let selected = select_release_for_tag("v2", releases.iter().cloned())
            .expect("selection")
            .expect("present");
        assert!(selected.is_immutable());
        assert!(!selected.is_mutable_draft());

        assert!(
            select_release_for_tag("absent", releases.iter().cloned())
                .expect("selection")
                .is_none()
        );
        assert_eq!(
            select_release_for_tag(
                "dup",
                [release("dup", true, false), release("dup", true, false)]
            )
            .expect_err("duplicate tag should fail")
            .kind(),
            ReleaseDataErrorKind::DuplicateReleaseTag
        );
    }

    #[test]
    fn staging_selection_adopts_only_the_exact_mutable_placeholder() {
        let placeholder = release("untagged-abc", true, false)
            .with_staging_identity(Some("v2".to_owned()), "commit-2".to_owned());
        let unrelated = release("untagged-def", true, false)
            .with_staging_identity(Some("v2".to_owned()), "other".to_owned());
        let selected =
            select_release_for_staging("v2", "commit-2", [unrelated, placeholder.clone()])
                .expect("selection")
                .expect("placeholder");
        assert_eq!(selected.database_id(), placeholder.database_id());

        assert!(
            select_release_for_staging(
                "v2",
                "commit-2",
                [release("untagged-abc", false, false)
                    .with_staging_identity(Some("v2".to_owned()), "commit-2".to_owned(),)],
            )
            .expect("selection")
            .is_none()
        );
        assert_eq!(
            select_release_for_staging(
                "v2",
                "commit-2",
                [release("v2", true, false), placeholder],
            )
            .expect_err("duplicate staging identity should fail")
            .kind(),
            ReleaseDataErrorKind::DuplicateReleaseTag
        );
    }

    #[test]
    fn mutable_draft_requires_draft_and_not_immutable() {
        assert!(release("v1", true, false).is_mutable_draft());
        assert!(!release("v1", true, true).is_mutable_draft());
        assert!(!release("v1", false, false).is_mutable_draft());
    }

    #[test]
    fn content_type_accepts_only_octet_stream() {
        require_asset_content_type("application/octet-stream").expect("binary type");
        require_asset_content_type("Application/Octet-Stream; charset=binary").expect("params ok");
        assert_eq!(
            require_asset_content_type("text/html")
                .expect_err("html should fail")
                .kind(),
            ReleaseDataErrorKind::UnexpectedContentType
        );
    }

    #[test]
    fn stream_guard_rejects_oversize_and_truncation_but_accepts_exact() {
        let mut guard = AssetStreamGuard::new(1024, Some(6));
        guard.accept(3).expect("first chunk");
        guard.accept(3).expect("second chunk");
        assert_eq!(guard.finish().expect("complete"), 6);

        let mut capped = AssetStreamGuard::new(4, None);
        assert_eq!(
            capped.accept(5).expect_err("over cap should fail").kind(),
            ReleaseDataErrorKind::AssetTooLarge
        );

        let mut declared = AssetStreamGuard::new(1024, Some(10));
        declared.accept(4).expect("partial chunk");
        assert_eq!(
            declared
                .finish()
                .expect_err("short body should fail")
                .kind(),
            ReleaseDataErrorKind::TruncatedAsset
        );
    }

    #[test]
    fn stream_guard_clamps_declared_length_to_the_byte_cap() {
        let mut guard = AssetStreamGuard::new(4, Some(1_000_000));
        assert_eq!(
            guard
                .accept(5)
                .expect_err("declared length cannot raise the cap")
                .kind(),
            ReleaseDataErrorKind::AssetTooLarge
        );
    }

    #[test]
    fn reconciliation_never_repeats_a_committed_mutation() {
        assert_eq!(
            reconcile_mutation(GitHubRetryAction::ReconcileMutation, true),
            ReconciledMutation::AlreadyApplied
        );
        assert_eq!(
            reconcile_mutation(GitHubRetryAction::ReconcileMutation, false),
            ReconciledMutation::SafeToRetry(RetryClass::Transient)
        );
        assert_eq!(
            reconcile_mutation(GitHubRetryAction::Retry(RetryClass::Throttled), true),
            ReconciledMutation::SafeToRetry(RetryClass::Throttled)
        );
        assert_eq!(
            reconcile_mutation(GitHubRetryAction::Stop(StopReason::Authorization), false),
            ReconciledMutation::Abort(StopReason::Authorization)
        );
    }

    #[test]
    fn release_data_errors_render_without_untrusted_text() {
        let rendered = [
            ReleaseDataErrorKind::InvalidAssetName,
            ReleaseDataErrorKind::InvalidAssetSize,
            ReleaseDataErrorKind::InvalidAssetDigest,
            ReleaseDataErrorKind::AssetNotUploaded,
            ReleaseDataErrorKind::InvalidObjectId,
            ReleaseDataErrorKind::InvalidReleaseState,
            ReleaseDataErrorKind::DuplicateReleaseTag,
            ReleaseDataErrorKind::AssetTooLarge,
            ReleaseDataErrorKind::UnexpectedContentType,
            ReleaseDataErrorKind::TruncatedAsset,
        ]
        .map(|kind| ReleaseDataError::new(kind).to_string());
        for message in rendered {
            assert!(!message.is_empty());
            assert!(!message.contains("sha256:"));
        }
    }
}
