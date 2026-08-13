//! Typed pull-request, review, and issue-graph operations.
//!
//! Each operation deserializes GitHub REST and fixed-document GraphQL responses
//! into the minimal typed DTOs current callers require. The DTOs expose no raw
//! URL or arbitrary GraphQL surface, GraphQL variables are typed, any GraphQL
//! `errors` member fails closed, ambiguous create outcomes reconcile before they
//! could duplicate a pull request, and issue-graph mutations stay behind the
//! live authorization gate with exact read-back.

use super::{
    GitHubCompletionError, LiveMutationDecision, LiveMutationRequest, OctocrabGitHubService,
    check_live_mutation_auth, collect_bounded_response, github_utc_timestamp, octocrab_status,
};
use chrono::{DateTime, Utc};
use http::header::LINK;
use http_body_util::{BodyExt, Limited};
use larch_core::{GitHubResponseLimits, ProcessCancellation, SafeText};
use regex::Regex;
use serde_json::{Map, Value, json};
use std::{
    collections::{BTreeMap, BTreeSet},
    error::Error,
    fmt,
    future::Future,
    sync::LazyLock,
};

const GITHUB_API_BASE: &str = "https://api.github.com/";
const DIAGNOSTIC_LIMIT: usize = 500;
const RELEASE_PAGE_SIZE: usize = 100;
// The run audit must inspect the repository's complete merged-PR history to
// preserve its merge-time ordering. Keep that read explicitly bounded while
// allowing the current larch history (more than the general 2,000-item
// operation limit) to be audited.
const AUDIT_HISTORY_PAGE_LIMIT: usize = 50;
const AUDIT_HISTORY_ITEM_LIMIT: usize = AUDIT_HISTORY_PAGE_LIMIT * RELEASE_PAGE_SIZE;

static SECURITY_CONTENT: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(
        r"\b(?:credentials?|secrets?|api[ -]?key|auth(?:entication|orization)? bypass|remote code execution|\brce\b|sql injection|command injection|vulnerabilit(?:y|ies)|private key|token exposure)\b",
    )
    .expect("security-content expression is valid")
});

/// Fixed GraphQL document for merge and review state REST does not expose.
const REVIEW_STATE_QUERY: &str = "query($owner:String!,$name:String!,$number:Int!){repository(owner:$owner,name:$name){pullRequest(number:$number){reviewDecision mergeStateStatus mergeable}}}";

/// Fixed GraphQL document for issue-to-pull-request closure references.
///
/// REST issue listings intentionally omit this relation. The backlog command
/// needs it to distinguish a completed issue from an explicitly not-planned
/// or combined-away issue, so it is a typed operation rather than an
/// arbitrary query exposed to a command caller.
const ISSUE_CLOSURE_REFERENCES_QUERY: &str = "query($owner:String!,$name:String!,$cursor:String){repository(owner:$owner,name:$name){issues(first:100,states:[OPEN,CLOSED],orderBy:{field:CREATED_AT,direction:DESC},after:$cursor){nodes{number closedByPullRequestsReferences(first:100){nodes{url}pageInfo{hasNextPage}}}pageInfo{hasNextPage endCursor}}}}";

/// Why a typed GitHub operation could not return a result.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum GitHubOperationError {
    /// The caller cancelled the operation before it completed.
    Cancelled,
    /// The operation exceeded the fixed overall deadline.
    DeadlineExceeded,
    /// GitHub rejected the request as unauthenticated or forbidden.
    Unauthorized,
    /// GitHub throttled the request.
    RateLimited,
    /// A mutation may have been accepted, but read reconciliation could not
    /// prove its postcondition. Callers must not retry it blindly.
    AmbiguousMutation,
    /// A transport or unexpected API failure, redacted and length-bounded.
    Transport(SafeText),
    /// A response did not match the typed contract at the named field.
    Malformed(&'static str),
    /// A GraphQL response carried an `errors` member, so it fails closed.
    GraphqlErrors,
    /// The repository does not expose the issue-dependency API.
    DependencyFeatureUnavailable,
    /// The repository does not expose the native sub-issue API.
    SubIssueFeatureUnavailable,
    /// GitHub rejected a sub-issue mutation because its relationship
    /// precondition did not hold. Callers must fail closed rather than replace
    /// a parent implicitly.
    SubIssuePreconditionFailed,
    /// The live-mutation authorization gate refused the request.
    MutationRefused(&'static str),
    /// A triage-controlled mutation's target no longer has its expected timestamp.
    StaleDependencyTarget,
    /// A triage-controlled mutation's target is not safe for a public mutation.
    ProtectedDependencyTarget,
    /// A triage-controlled mutation's target contains security-sensitive content.
    SecuritySensitiveDependencyTarget,
}

impl fmt::Display for GitHubOperationError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Cancelled => formatter.write_str("GitHub operation cancelled"),
            Self::DeadlineExceeded => formatter.write_str("GitHub operation deadline exceeded"),
            Self::Unauthorized => {
                formatter.write_str("GitHub rejected the request as unauthorized")
            }
            Self::RateLimited => formatter.write_str("GitHub rate limited the request"),
            Self::AmbiguousMutation => formatter.write_str(
                "GitHub mutation outcome is uncertain; reconciliation did not prove its postcondition",
            ),
            Self::Transport(detail) => write!(formatter, "GitHub transport failure: {detail}"),
            Self::Malformed(field) => {
                write!(
                    formatter,
                    "GitHub response did not match the typed contract: {field}"
                )
            }
            Self::GraphqlErrors => {
                formatter.write_str("GitHub GraphQL response contained an errors member")
            }
            Self::DependencyFeatureUnavailable => formatter
                .write_str("GitHub issue-dependency API is unavailable for this repository"),
            Self::SubIssueFeatureUnavailable => {
                formatter.write_str("GitHub sub-issue API is unavailable for this repository")
            }
            Self::SubIssuePreconditionFailed => {
                formatter.write_str("GitHub rejected the sub-issue relationship precondition")
            }
            Self::MutationRefused(reason) => {
                write!(formatter, "live GitHub mutation refused: {reason}")
            }
            Self::StaleDependencyTarget => {
                formatter.write_str("dependency target changed since the expected triage snapshot")
            }
            Self::ProtectedDependencyTarget => {
                formatter.write_str("dependency target has protected lifecycle state")
            }
            Self::SecuritySensitiveDependencyTarget => formatter
                .write_str("security-sensitive target cannot receive a public dependency mutation"),
        }
    }
}

impl Error for GitHubOperationError {}

/// Open or closed lifecycle state of a pull request.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum PullRequestState {
    Open,
    Closed,
}

/// GitHub review decision for a pull request.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ReviewDecision {
    Approved,
    ChangesRequested,
    ReviewRequired,
}

/// GitHub merge-state status for a pull request.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum MergeStateStatus {
    Behind,
    Blocked,
    Clean,
    Dirty,
    Draft,
    HasHooks,
    Unknown,
    Unstable,
}

/// Whether GitHub currently considers a pull request mergeable.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Mergeable {
    Mergeable,
    Conflicting,
    Unknown,
}

/// One of GitHub's supported pull-request merge methods.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum PullRequestMergeMethod {
    Merge,
    Squash,
    Rebase,
}

/// Typed result of a pull-request merge attempt.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum PullRequestMergeResult {
    /// The requested merge completed and GitHub returned its merge commit id.
    Merged { merge_commit_oid: String },
    /// The pull request had already merged at the caller's expected head.
    AlreadyMerged,
    /// The current or merged head differs from the caller's expected head.
    HeadChanged,
    /// GitHub refused the merge because the pull request is not mergeable.
    MergeConflict,
    /// GitHub refused the merge because repository policy blocked it.
    BranchProtection,
    /// GitHub refused the merge but did not provide a typed reason.
    MergeUnavailable,
    /// GitHub rejected the otherwise typed request as invalid or spammed.
    ValidationFailed,
    /// The pull request was closed without merging.
    Closed,
}

/// Minimal typed pull-request contract current callers require.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct PullRequest {
    number: u64,
    state: PullRequestState,
    title: String,
    head_ref: String,
    base_ref: String,
    draft: bool,
    merged: bool,
    merge_commit_oid: Option<String>,
}

/// Pull-request fields used to prepare release notes.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ReleasePullRequest {
    pub number: u64,
    pub title: String,
    pub labels: Vec<String>,
    pub author: String,
    pub url: String,
    pub head_ref: String,
}

/// Candidate lifecycle and commit identities used by release staging.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ReleaseCandidatePullRequest {
    pub state: ReleaseCandidatePullRequestState,
    pub head_oid: String,
    /// The commit GitHub created when the pull request merged.
    ///
    /// This is absent before merge. Release staging uses it instead of the
    /// branch head because a squash queue creates a distinct main commit.
    pub merge_commit_oid: Option<String>,
}

/// Bounded pull-request fields consumed by the run-audit reader.
///
/// This intentionally keeps the audit's read contract distinct from release
/// notes and mutation DTOs: it needs a body, the target base, and merge time,
/// but never exposes an arbitrary REST surface to a command caller.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct AuditPullRequest {
    pub number: u64,
    pub title: String,
    pub body: String,
    pub base_ref: String,
    pub merged_at: Option<String>,
}

/// Typed, injectable GitHub reads consumed by the run-audit command domain.
pub trait AuditRunsService: Sync {
    fn audit_pull_request<'a>(
        &'a self,
        cancellation: &'a dyn ProcessCancellation,
        owner: &'a str,
        repo: &'a str,
        number: u64,
    ) -> impl Future<Output = Result<AuditPullRequest, GitHubOperationError>> + Send + 'a;

    fn list_audit_merged_main_pull_requests<'a>(
        &'a self,
        cancellation: &'a dyn ProcessCancellation,
        owner: &'a str,
        repo: &'a str,
    ) -> impl Future<Output = Result<Vec<AuditPullRequest>, GitHubOperationError>> + Send + 'a;
}

impl AuditRunsService for OctocrabGitHubService {
    fn audit_pull_request<'a>(
        &'a self,
        cancellation: &'a dyn ProcessCancellation,
        owner: &'a str,
        repo: &'a str,
        number: u64,
    ) -> impl Future<Output = Result<AuditPullRequest, GitHubOperationError>> + Send + 'a {
        Self::audit_pull_request(self, cancellation, owner, repo, number)
    }

    fn list_audit_merged_main_pull_requests<'a>(
        &'a self,
        cancellation: &'a dyn ProcessCancellation,
        owner: &'a str,
        repo: &'a str,
    ) -> impl Future<Output = Result<Vec<AuditPullRequest>, GitHubOperationError>> + Send + 'a {
        Self::list_audit_merged_main_pull_requests(self, cancellation, owner, repo)
    }
}

/// Closed lifecycle states exposed by the release candidate check.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ReleaseCandidatePullRequestState {
    Open,
    Closed,
    Merged,
}

/// Typed, injectable GitHub reads used by release preparation.
pub trait ReleasePlanningService: Sync {
    fn latest_release_tag<'a>(
        &'a self,
        cancellation: &'a dyn ProcessCancellation,
        owner: &'a str,
        repo: &'a str,
    ) -> impl Future<Output = Result<Option<String>, GitHubOperationError>> + Send + 'a;

    fn list_open_pull_requests<'a>(
        &'a self,
        cancellation: &'a dyn ProcessCancellation,
        owner: &'a str,
        repo: &'a str,
    ) -> impl Future<Output = Result<Vec<ReleasePullRequest>, GitHubOperationError>> + Send + 'a;

    fn pull_request<'a>(
        &'a self,
        cancellation: &'a dyn ProcessCancellation,
        owner: &'a str,
        repo: &'a str,
        number: u64,
    ) -> impl Future<Output = Result<ReleasePullRequest, GitHubOperationError>> + Send + 'a;

    fn commit_pull_requests<'a>(
        &'a self,
        cancellation: &'a dyn ProcessCancellation,
        owner: &'a str,
        repo: &'a str,
        commit: &'a str,
    ) -> impl Future<Output = Result<Vec<ReleasePullRequest>, GitHubOperationError>> + Send + 'a;

    fn issue_title<'a>(
        &'a self,
        cancellation: &'a dyn ProcessCancellation,
        owner: &'a str,
        repo: &'a str,
        number: u64,
    ) -> impl Future<Output = Result<String, GitHubOperationError>> + Send + 'a;
}

impl ReleasePlanningService for OctocrabGitHubService {
    fn latest_release_tag<'a>(
        &'a self,
        cancellation: &'a dyn ProcessCancellation,
        owner: &'a str,
        repo: &'a str,
    ) -> impl Future<Output = Result<Option<String>, GitHubOperationError>> + Send + 'a {
        Self::latest_release_tag(self, cancellation, owner, repo)
    }

    fn list_open_pull_requests<'a>(
        &'a self,
        cancellation: &'a dyn ProcessCancellation,
        owner: &'a str,
        repo: &'a str,
    ) -> impl Future<Output = Result<Vec<ReleasePullRequest>, GitHubOperationError>> + Send + 'a
    {
        self.list_release_open_pull_requests(cancellation, owner, repo)
    }

    fn pull_request<'a>(
        &'a self,
        cancellation: &'a dyn ProcessCancellation,
        owner: &'a str,
        repo: &'a str,
        number: u64,
    ) -> impl Future<Output = Result<ReleasePullRequest, GitHubOperationError>> + Send + 'a {
        self.release_pull_request(cancellation, owner, repo, number)
    }

    fn commit_pull_requests<'a>(
        &'a self,
        cancellation: &'a dyn ProcessCancellation,
        owner: &'a str,
        repo: &'a str,
        commit: &'a str,
    ) -> impl Future<Output = Result<Vec<ReleasePullRequest>, GitHubOperationError>> + Send + 'a
    {
        Self::commit_pull_requests(self, cancellation, owner, repo, commit)
    }

    fn issue_title<'a>(
        &'a self,
        cancellation: &'a dyn ProcessCancellation,
        owner: &'a str,
        repo: &'a str,
        number: u64,
    ) -> impl Future<Output = Result<String, GitHubOperationError>> + Send + 'a {
        Self::issue_title(self, cancellation, owner, repo, number)
    }
}

impl PullRequest {
    #[must_use]
    pub const fn number(&self) -> u64 {
        self.number
    }

    #[must_use]
    pub const fn state(&self) -> PullRequestState {
        self.state
    }

    #[must_use]
    pub fn title(&self) -> &str {
        &self.title
    }

    #[must_use]
    pub fn head_ref(&self) -> &str {
        &self.head_ref
    }

    #[must_use]
    pub fn base_ref(&self) -> &str {
        &self.base_ref
    }

    #[must_use]
    pub const fn draft(&self) -> bool {
        self.draft
    }

    #[must_use]
    pub const fn merged(&self) -> bool {
        self.merged
    }

    /// Return the immutable merge commit GitHub recorded for a merged pull request.
    #[must_use]
    pub fn merge_commit_oid(&self) -> Option<&str> {
        self.merge_commit_oid.as_deref()
    }
}

/// Merge and review state assembled from the fixed GraphQL document.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct PullRequestReviewState {
    review_decision: Option<ReviewDecision>,
    merge_state_status: MergeStateStatus,
    mergeable: Mergeable,
}

impl PullRequestReviewState {
    #[must_use]
    pub const fn review_decision(&self) -> Option<ReviewDecision> {
        self.review_decision
    }

    #[must_use]
    pub const fn merge_state_status(&self) -> MergeStateStatus {
        self.merge_state_status
    }

    #[must_use]
    pub const fn mergeable(&self) -> Mergeable {
        self.mergeable
    }
}

/// Result of a reconciled pull-request creation.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct CreatedPullRequest {
    pull_request: PullRequest,
    created: bool,
}

impl CreatedPullRequest {
    #[must_use]
    pub const fn pull_request(&self) -> &PullRequest {
        &self.pull_request
    }

    /// Whether this call created the pull request, as opposed to adopting an
    /// existing one for the same head branch.
    #[must_use]
    pub const fn created(&self) -> bool {
        self.created
    }
}

/// One issue reference returned by a GitHub issue-graph endpoint.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct DependencyRef {
    issue_number: u64,
    issue_id: u64,
    open: bool,
}

impl DependencyRef {
    #[must_use]
    pub const fn issue_number(&self) -> u64 {
        self.issue_number
    }

    #[must_use]
    pub const fn issue_id(&self) -> u64 {
        self.issue_id
    }

    /// Whether the referenced issue is open.
    ///
    /// A response that omits `state`, or spells it as anything other than
    /// `open`, reads as closed. Blocker discovery must not treat an
    /// unrecognized lifecycle state as an active blocker.
    #[must_use]
    pub const fn is_open(&self) -> bool {
        self.open
    }
}

/// One sub-issue reference as read back from GitHub.
pub type SubIssueRef = DependencyRef;

/// Outcome of an idempotent issue-graph relation add or remove.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DependencyMutation {
    /// The edge was applied and confirmed by exact read-back.
    Applied,
    /// The edge already matched the desired state; no mutation was needed.
    AlreadyInDesiredState,
}

/// Outcome of an idempotent sub-issue add or remove.
pub type SubIssueMutation = DependencyMutation;

/// Receipt for a dependency mutation and its optional triage freshness proof.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct DependencyMutationReceipt {
    outcome: DependencyMutation,
    updated_at: Option<String>,
}

impl DependencyMutationReceipt {
    #[must_use]
    pub const fn outcome(&self) -> DependencyMutation {
        self.outcome
    }

    /// Fresh target timestamp returned only for triage-controlled mutations.
    #[must_use]
    pub fn updated_at(&self) -> Option<&str> {
        self.updated_at.as_deref()
    }
}

/// Receipt for a sub-issue mutation proven by a fresh relation read-back.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct SubIssueMutationReceipt {
    outcome: SubIssueMutation,
}

impl SubIssueMutationReceipt {
    #[must_use]
    pub const fn outcome(&self) -> SubIssueMutation {
        self.outcome
    }
}

/// Immutable inputs for a reconciled pull-request creation.
pub struct PullRequestSpec<'a> {
    pub owner: &'a str,
    pub repo: &'a str,
    pub head: &'a str,
    pub base: &'a str,
    pub title: &'a str,
    pub body: &'a str,
    pub draft: bool,
}

/// Immutable inputs for a pull-request edit; unset fields are left unchanged.
pub struct PullRequestEdit<'a> {
    pub owner: &'a str,
    pub repo: &'a str,
    pub number: u64,
    pub title: Option<&'a str>,
    pub body: Option<&'a str>,
    pub state: Option<PullRequestState>,
    pub base: Option<&'a str>,
}

/// Immutable, checked inputs for one pull-request merge mutation.
pub struct PullRequestMerge<'a> {
    pub owner: &'a str,
    pub repo: &'a str,
    pub number: u64,
    pub expected_head_oid: &'a str,
    pub method: PullRequestMergeMethod,
    pub commit_title: Option<&'a str>,
    pub commit_message: Option<&'a str>,
}

/// One issue-dependency edge to add or remove.
#[derive(Clone, Copy)]
pub struct DependencyEdge<'a> {
    pub owner: &'a str,
    pub repo: &'a str,
    pub client_issue: u64,
    pub blocker_id: u64,
    /// Exact target timestamp required for a triage-controlled mutation.
    pub expected_updated_at: Option<&'a str>,
}

/// One native parent-to-sub-issue edge to add or remove.
#[derive(Clone, Copy)]
pub struct SubIssueEdge<'a> {
    pub owner: &'a str,
    pub repo: &'a str,
    pub parent_issue: u64,
    /// GitHub's immutable numeric database id for the sub-issue.
    pub sub_issue_id: u64,
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct DependencyTarget {
    updated_at: String,
    state: String,
    title: String,
    body: String,
    labels: Vec<String>,
}

enum CreatePlan {
    ReturnExisting(u64),
    Create,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum DependencyWrite {
    Accepted,
    Duplicate,
    FeatureUnavailable,
    Unauthorized,
    Failed,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum SubIssueWrite {
    Accepted,
    PreconditionFailed,
    FeatureUnavailable,
    Unauthorized,
    RateLimited,
    Failed,
}

#[derive(Clone, Copy)]
enum IssueGraphFeature {
    Dependency,
    SubIssue,
}

impl IssueGraphFeature {
    const fn unavailable_error(self) -> GitHubOperationError {
        match self {
            Self::Dependency => GitHubOperationError::DependencyFeatureUnavailable,
            Self::SubIssue => GitHubOperationError::SubIssueFeatureUnavailable,
        }
    }

    const fn name(self) -> &'static str {
        match self {
            Self::Dependency => "dependency",
            Self::SubIssue => "sub-issue",
        }
    }

    const fn body_error_context(self) -> &'static str {
        match self {
            Self::Dependency => "dependency response exceeds body bound",
            Self::SubIssue => "sub-issue response exceeds body bound",
        }
    }

    const fn json_error_context(self) -> &'static str {
        match self {
            Self::Dependency => "dependency JSON response",
            Self::SubIssue => "sub-issue JSON response",
        }
    }

    const fn list_bound_error_context(self) -> &'static str {
        match self {
            Self::Dependency => "dependency list exceeds item bound",
            Self::SubIssue => "sub-issue list exceeds item bound",
        }
    }

    const fn pagination_bound_error_context(self) -> &'static str {
        match self {
            Self::Dependency => "dependency pagination exceeds page bound",
            Self::SubIssue => "sub-issue pagination exceeds page bound",
        }
    }

    const fn pagination_link_error_context(self) -> &'static str {
        match self {
            Self::Dependency => "dependency pagination link",
            Self::SubIssue => "sub-issue pagination link",
        }
    }
}

enum MergeExchangeError {
    Transport(octocrab::Error),
    BodyLimit,
}

impl OctocrabGitHubService {
    /// Read one pull request for the run-audit mapping and resolution commands.
    ///
    /// # Errors
    /// Returns a typed input, transport, cancellation, or response-contract
    /// failure. The returned text has passed the transport's response bounds.
    pub async fn audit_pull_request(
        &self,
        cancellation: &dyn ProcessCancellation,
        owner: &str,
        repo: &str,
        number: u64,
    ) -> Result<AuditPullRequest, GitHubOperationError> {
        validate_repo(owner, repo)?;
        let route = format!("/repos/{owner}/{repo}/pulls/{number}");
        let value = self
            .fetch_json(cancellation, self.client.get(route.as_str(), None::<&()>))
            .await?;
        parse_audit_pull_request(&value, self.policy.limits())
    }

    /// List merged pull requests targeting `main` through bounded pagination.
    ///
    /// The audit's chronology is defined by GitHub's `merged_at`, not by PR
    /// number or close time, so malformed rows are rejected instead of being
    /// silently re-ordered.
    ///
    /// # Errors
    /// Returns a typed input, transport, cancellation, response-contract, or
    /// bounded-pagination failure.
    pub async fn list_audit_merged_main_pull_requests(
        &self,
        cancellation: &dyn ProcessCancellation,
        owner: &str,
        repo: &str,
    ) -> Result<Vec<AuditPullRequest>, GitHubOperationError> {
        validate_repo(owner, repo)?;
        let route = format!("/repos/{owner}/{repo}/pulls");
        let limits = self.policy.limits();
        let mut output = Vec::new();
        for page in 1..=AUDIT_HISTORY_PAGE_LIMIT {
            let page_text = page.to_string();
            let parameters = [
                ("state", "closed"),
                ("base", "main"),
                ("per_page", "100"),
                ("page", page_text.as_str()),
            ];
            let value = self
                .fetch_json(
                    cancellation,
                    self.client.get(route.as_str(), Some(&parameters)),
                )
                .await?;
            let rows = parse_audit_pull_requests(&value, limits)?;
            let count = rows.len();
            if output.len().saturating_add(count) > AUDIT_HISTORY_ITEM_LIMIT {
                return Err(GitHubOperationError::Malformed(
                    "audit pull request list exceeds history bound",
                ));
            }
            output.extend(rows.into_iter().filter(|pull_request| {
                pull_request.base_ref == "main" && pull_request.merged_at.is_some()
            }));
            if count < RELEASE_PAGE_SIZE {
                output.sort_by(|left, right| left.merged_at.cmp(&right.merged_at));
                return Ok(output);
            }
        }
        Err(GitHubOperationError::Malformed(
            "audit pull request pagination exceeds page bound",
        ))
    }

    /// Read the lifecycle state and exact head object id of a release PR.
    ///
    /// # Errors
    /// Returns a typed error when the request fails or the response does not
    /// contain a full lowercase Git object id.
    pub async fn release_candidate_pull_request(
        &self,
        cancellation: &dyn ProcessCancellation,
        owner: &str,
        repo: &str,
        number: u64,
    ) -> Result<ReleaseCandidatePullRequest, GitHubOperationError> {
        validate_repo(owner, repo)?;
        let route = format!("/repos/{owner}/{repo}/pulls/{number}");
        let value = self
            .fetch_json(cancellation, self.client.get(route.as_str(), None::<&()>))
            .await?;
        parse_release_candidate_pull_request(&value)
    }

    /// Read the unique GitHub Latest release tag.
    ///
    /// # Errors
    /// Returns a typed input, transport, cancellation, or response-contract failure.
    pub async fn latest_release_tag(
        &self,
        cancellation: &dyn ProcessCancellation,
        owner: &str,
        repo: &str,
    ) -> Result<Option<String>, GitHubOperationError> {
        validate_repo(owner, repo)?;
        let route = format!("/repos/{owner}/{repo}/releases/latest");
        let operation = self.client.get(route.as_str(), None::<&()>);
        let value = match self.guard_operation(cancellation, operation).await {
            Ok(Ok(value)) => value,
            Ok(Err(error)) if octocrab_status(&error) == Some(404) => return Ok(None),
            Ok(Err(error)) => return Err(self.transport_error(&error)),
            Err(completion) => return Err(completion_error(completion)),
        };
        let object = as_object(&value)?;
        required_str(object, "tag_name", self.policy.limits(), "release tag").map(Some)
    }

    /// List every open pull request through bounded pagination.
    ///
    /// # Errors
    /// Returns a typed input, transport, cancellation, limit, or response-contract failure.
    pub async fn list_release_open_pull_requests(
        &self,
        cancellation: &dyn ProcessCancellation,
        owner: &str,
        repo: &str,
    ) -> Result<Vec<ReleasePullRequest>, GitHubOperationError> {
        validate_repo(owner, repo)?;
        let route = format!("/repos/{owner}/{repo}/pulls");
        self.release_pull_request_pages(cancellation, &route, Some("open"))
            .await
    }

    /// Read release-note metadata for one pull request.
    ///
    /// # Errors
    /// Returns a typed input, transport, cancellation, or response-contract failure.
    pub async fn release_pull_request(
        &self,
        cancellation: &dyn ProcessCancellation,
        owner: &str,
        repo: &str,
        number: u64,
    ) -> Result<ReleasePullRequest, GitHubOperationError> {
        validate_repo(owner, repo)?;
        let route = format!("/repos/{owner}/{repo}/pulls/{number}");
        let value = self
            .fetch_json(cancellation, self.client.get(route.as_str(), None::<&()>))
            .await?;
        parse_release_pull_request(&value, self.policy.limits())
            .map(|pull_request| self.redact_release_pull_request(pull_request))
    }

    /// List pull requests associated with one commit through bounded pagination.
    ///
    /// # Errors
    /// Returns a typed input, transport, cancellation, limit, or response-contract failure.
    pub async fn commit_pull_requests(
        &self,
        cancellation: &dyn ProcessCancellation,
        owner: &str,
        repo: &str,
        commit: &str,
    ) -> Result<Vec<ReleasePullRequest>, GitHubOperationError> {
        validate_repo(owner, repo)?;
        if commit.is_empty() || !commit.bytes().all(|byte| byte.is_ascii_hexdigit()) {
            return Err(GitHubOperationError::Malformed("commit object id"));
        }
        let route = format!("/repos/{owner}/{repo}/commits/{commit}/pulls");
        self.release_pull_request_pages(cancellation, &route, None)
            .await
    }

    /// Read one companion issue title.
    ///
    /// # Errors
    /// Returns a typed input, transport, cancellation, or response-contract failure.
    pub async fn issue_title(
        &self,
        cancellation: &dyn ProcessCancellation,
        owner: &str,
        repo: &str,
        number: u64,
    ) -> Result<String, GitHubOperationError> {
        validate_repo(owner, repo)?;
        let route = format!("/repos/{owner}/{repo}/issues/{number}");
        let value = self
            .fetch_json(cancellation, self.client.get(route.as_str(), None::<&()>))
            .await?;
        let object = as_object(&value)?;
        required_str(object, "title", self.policy.limits(), "issue title")
            .map(|title| self.redactor.safe_text(title).to_string())
    }

    async fn release_pull_request_pages(
        &self,
        cancellation: &dyn ProcessCancellation,
        route: &str,
        state: Option<&str>,
    ) -> Result<Vec<ReleasePullRequest>, GitHubOperationError> {
        let limits = self.policy.limits();
        let mut output = Vec::new();
        for page in 1..=limits.pages() {
            let page_text = page.to_string();
            let mut parameters = vec![("per_page", "100"), ("page", page_text.as_str())];
            if let Some(state) = state {
                parameters.push(("state", state));
            }
            let value = self
                .fetch_json(cancellation, self.client.get(route, Some(&parameters)))
                .await?;
            let page_items = parse_release_pull_requests(&value, limits)?;
            let count = page_items.len();
            if output.len().saturating_add(count) > limits.items() {
                return Err(GitHubOperationError::Malformed(
                    "pull request list exceeds item bound",
                ));
            }
            output.extend(
                page_items
                    .into_iter()
                    .map(|pull_request| self.redact_release_pull_request(pull_request)),
            );
            if count < RELEASE_PAGE_SIZE {
                return Ok(output);
            }
        }
        Err(GitHubOperationError::Malformed(
            "pull request pagination exceeds page bound",
        ))
    }

    fn redact_release_pull_request(
        &self,
        mut pull_request: ReleasePullRequest,
    ) -> ReleasePullRequest {
        pull_request.title = self.redactor.safe_text(pull_request.title).to_string();
        pull_request.author = self.redactor.safe_text(pull_request.author).to_string();
        pull_request.url = self.redactor.safe_text(pull_request.url).to_string();
        pull_request.head_ref = self.redactor.safe_text(pull_request.head_ref).to_string();
        pull_request.labels = pull_request
            .labels
            .into_iter()
            .map(|label| self.redactor.safe_text(label).to_string())
            .collect();
        pull_request
    }

    /// Fetch one pull request by number.
    ///
    /// # Errors
    /// Returns a typed error on cancellation, deadline, authorization, transport
    /// failure, or a response that does not match the pull-request contract.
    pub async fn get_pull_request(
        &self,
        cancellation: &dyn ProcessCancellation,
        owner: &str,
        repo: &str,
        number: u64,
    ) -> Result<PullRequest, GitHubOperationError> {
        validate_repo(owner, repo)?;
        let route = format!("/repos/{owner}/{repo}/pulls/{number}");
        let value = self
            .fetch_json(cancellation, self.client.get(route.as_str(), None::<&()>))
            .await?;
        parse_pull_request(&value, self.policy.limits())
    }

    /// List the open pull requests for one head branch on the approved origin.
    ///
    /// # Errors
    /// Returns a typed error on cancellation, deadline, authorization, transport
    /// failure, or a response that does not match the pull-request contract.
    pub async fn list_open_pull_requests(
        &self,
        cancellation: &dyn ProcessCancellation,
        owner: &str,
        repo: &str,
        head_branch: &str,
    ) -> Result<Vec<PullRequest>, GitHubOperationError> {
        validate_repo(owner, repo)?;
        let route = format!("/repos/{owner}/{repo}/pulls");
        let head = format!("{owner}:{head_branch}");
        let parameters = [("state", "open"), ("head", head.as_str())];
        let value = self
            .fetch_json(
                cancellation,
                self.client.get(route.as_str(), Some(&parameters)),
            )
            .await?;
        parse_pull_requests(&value, self.policy.limits())
    }

    /// Create a pull request, reconciling any existing head-branch pull request
    /// so an ambiguous outcome never silently creates a duplicate.
    ///
    /// # Errors
    /// Returns a typed error on cancellation, deadline, authorization, transport
    /// failure, or a response that does not match the pull-request contract.
    pub async fn create_pull_request(
        &self,
        cancellation: &dyn ProcessCancellation,
        spec: &PullRequestSpec<'_>,
    ) -> Result<CreatedPullRequest, GitHubOperationError> {
        validate_repo(spec.owner, spec.repo)?;
        if let Some(existing) = self.existing_head_pull_request(cancellation, spec).await? {
            return Ok(CreatedPullRequest {
                pull_request: existing,
                created: false,
            });
        }
        let route = format!("/repos/{}/{}/pulls", spec.owner, spec.repo);
        let body = json!({
            "title": spec.title,
            "head": spec.head,
            "base": spec.base,
            "body": spec.body,
            "draft": spec.draft,
        });
        match self
            .fetch_json(cancellation, self.client.post(route, Some(&body)))
            .await
        {
            Ok(value) => {
                let pull_request = parse_pull_request(&value, self.policy.limits())?;
                Ok(CreatedPullRequest {
                    pull_request,
                    created: true,
                })
            }
            Err(error) => {
                self.reconcile_after_create_failure(cancellation, spec, error)
                    .await
            }
        }
    }

    /// Edit an existing pull request; unset fields are left unchanged.
    ///
    /// # Errors
    /// Returns a typed error on cancellation, deadline, authorization, transport
    /// failure, or a response that does not match the pull-request contract.
    pub async fn edit_pull_request(
        &self,
        cancellation: &dyn ProcessCancellation,
        edit: &PullRequestEdit<'_>,
    ) -> Result<PullRequest, GitHubOperationError> {
        validate_repo(edit.owner, edit.repo)?;
        let route = format!("/repos/{}/{}/pulls/{}", edit.owner, edit.repo, edit.number);
        let value = self
            .fetch_json(
                cancellation,
                self.client.patch(route.as_str(), Some(&edit_body(edit))),
            )
            .await?;
        parse_pull_request(&value, self.policy.limits())
    }

    /// Merge one pull request exactly once behind the live-mutation gate.
    ///
    /// The expected head object id is checked before the write and sent to
    /// GitHub as the merge precondition. Transport, timeout, and malformed
    /// success outcomes are reconciled with a bounded read; no path resubmits
    /// the mutation.
    ///
    /// # Errors
    /// Returns `MutationRefused` before any read or write when live-mutation
    /// authorization fails. Other failures distinguish authorization, rate
    /// limiting, cancellation, malformed responses, and uncertain mutations.
    pub async fn merge_pull_request(
        &self,
        cancellation: &dyn ProcessCancellation,
        authorization: &LiveMutationRequest<'_>,
        request: &PullRequestMerge<'_>,
    ) -> Result<PullRequestMergeResult, GitHubOperationError> {
        authorize_mutation(authorization)?;
        validate_repo(request.owner, request.repo)?;
        if !is_git_object_id(request.expected_head_oid) {
            return Err(GitHubOperationError::Malformed(
                "expected pull request head oid",
            ));
        }
        for text in [request.commit_title, request.commit_message]
            .into_iter()
            .flatten()
        {
            if text.len() > self.policy.limits().string_bytes() {
                return Err(GitHubOperationError::Malformed("pull request merge text"));
            }
        }

        let _mutation = self.mutation_lock.lock().await;
        if let Some(result) = self.merge_precondition(cancellation, request).await? {
            return Ok(result);
        }

        let outcome = self.send_pull_request_merge(cancellation, request).await;
        match outcome {
            Ok(result) => Ok(result),
            Err(error) if requires_merge_reconciliation(&error) => {
                self.reconcile_after_merge_uncertainty(cancellation, request, error)
                    .await
            }
            Err(error) => Err(error),
        }
    }

    /// Read merge and review state through the fixed GraphQL document.
    ///
    /// # Errors
    /// Returns a typed error on cancellation, deadline, authorization, transport
    /// failure, a response outside the typed contract, or any GraphQL `errors`
    /// member, including partial-data responses.
    pub async fn pull_request_review_state(
        &self,
        cancellation: &dyn ProcessCancellation,
        owner: &str,
        repo: &str,
        number: u64,
    ) -> Result<PullRequestReviewState, GitHubOperationError> {
        validate_repo(owner, repo)?;
        let payload = json!({
            "query": REVIEW_STATE_QUERY,
            "variables": { "owner": owner, "name": repo, "number": number },
        });
        let value = self
            .fetch_json(cancellation, self.client.post("/graphql", Some(&payload)))
            .await?;
        parse_review_state(&value)
    }

    /// Read closure references for a bounded set of issues through one fixed
    /// paginated GraphQL document.
    ///
    /// # Errors
    ///
    /// Returns a typed error when the repository or response is invalid, the
    /// connection exceeds the transport page bound, or GitHub reports any
    /// GraphQL error. A returned map contains every requested issue observed
    /// in the connection, including entries whose closure list is empty.
    pub async fn issue_closure_references(
        &self,
        cancellation: &dyn ProcessCancellation,
        owner: &str,
        repo: &str,
        wanted: &BTreeSet<u64>,
    ) -> Result<BTreeMap<u64, Vec<String>>, GitHubOperationError> {
        validate_repo(owner, repo)?;
        if wanted.is_empty() {
            return Ok(BTreeMap::new());
        }
        if wanted.len() > self.policy.limits().items() {
            return Err(GitHubOperationError::Malformed(
                "issue closure-reference request exceeds item bound",
            ));
        }
        let mut cursor: Option<String> = None;
        let mut found = BTreeMap::new();
        for page_index in 0..self.policy.limits().pages() {
            let payload = json!({
                "query": ISSUE_CLOSURE_REFERENCES_QUERY,
                "variables": { "owner": owner, "name": repo, "cursor": cursor },
            });
            let value = self
                .fetch_json(cancellation, self.client.post("/graphql", Some(&payload)))
                .await?;
            let page = parse_issue_closure_references(&value, wanted, self.policy.limits())?;
            found.extend(page.entries);
            if found.len() == wanted.len() || !page.has_next_page {
                return Ok(found);
            }
            if page_index + 1 == self.policy.limits().pages() {
                return Err(GitHubOperationError::Malformed(
                    "issue closure-reference pagination limit",
                ));
            }
            cursor = page.end_cursor;
            if cursor.is_none() {
                return Err(GitHubOperationError::Malformed(
                    "issue closure-reference pagination cursor",
                ));
            }
        }
        unreachable!("bounded GraphQL pagination always returns")
    }

    /// List the issues that block one issue.
    ///
    /// # Errors
    /// Returns a typed error on cancellation, deadline, authorization, transport
    /// failure, or a response that does not match the dependency contract.
    pub async fn list_blocked_by(
        &self,
        cancellation: &dyn ProcessCancellation,
        owner: &str,
        repo: &str,
        issue: u64,
    ) -> Result<Vec<DependencyRef>, GitHubOperationError> {
        validate_repo(owner, repo)?;
        let route = format!("/repos/{owner}/{repo}/issues/{issue}/dependencies/blocked_by");
        self.dependency_pages(cancellation, &route).await
    }

    /// List the issues that one issue blocks.
    ///
    /// This is the mirror of [`Self::list_blocked_by`]. `/deps` reads both
    /// directions for every open issue so its snapshot of the dependency graph
    /// still contains an edge whose other endpoint has since been closed.
    ///
    /// # Errors
    /// Returns a typed error on cancellation, deadline, authorization, transport
    /// failure, or a response that does not match the dependency contract.
    pub async fn list_blocking(
        &self,
        cancellation: &dyn ProcessCancellation,
        owner: &str,
        repo: &str,
        issue: u64,
    ) -> Result<Vec<DependencyRef>, GitHubOperationError> {
        validate_repo(owner, repo)?;
        let route = format!("/repos/{owner}/{repo}/issues/{issue}/dependencies/blocking");
        self.dependency_pages(cancellation, &route).await
    }

    /// List the direct native sub-issues of one parent issue.
    ///
    /// The response follows only bounded, same-origin pagination links.
    ///
    /// # Errors
    /// Returns a typed error on cancellation, deadline, authorization,
    /// transport failure, unavailable sub-issue support, or a response outside
    /// the sub-issue contract.
    pub async fn list_sub_issues(
        &self,
        cancellation: &dyn ProcessCancellation,
        owner: &str,
        repo: &str,
        parent_issue: u64,
    ) -> Result<Vec<SubIssueRef>, GitHubOperationError> {
        validate_repo(owner, repo)?;
        validate_issue_number(parent_issue, "sub-issue parent number")?;
        let route = format!("/repos/{owner}/{repo}/issues/{parent_issue}/sub_issues");
        self.sub_issue_pages(cancellation, &route).await
    }

    /// Read the direct parent of one native sub-issue, if GitHub reports one.
    ///
    /// # Errors
    /// Returns a typed error on cancellation, deadline, authorization,
    /// transport failure, unavailable sub-issue support, or a malformed parent
    /// response. The endpoint's `404` outcome is represented as no parent.
    pub async fn parent_issue(
        &self,
        cancellation: &dyn ProcessCancellation,
        owner: &str,
        repo: &str,
        sub_issue: u64,
    ) -> Result<Option<SubIssueRef>, GitHubOperationError> {
        validate_repo(owner, repo)?;
        validate_issue_number(sub_issue, "sub-issue number")?;
        let route = format!("/repos/{owner}/{repo}/issues/{sub_issue}/parent");
        let result = self
            .guard_operation(cancellation, self.client._get(route.as_str()))
            .await;
        let response = match result {
            Ok(Ok(response)) => response,
            Ok(Err(error)) => return Err(self.transport_error(&error)),
            Err(completion) => return Err(completion_error(completion)),
        };
        match response.status().as_u16() {
            200 => {
                let body = collect_bounded_response(response, self.policy.limits().body_bytes())
                    .await
                    .map_err(|()| {
                        GitHubOperationError::Malformed(
                            "sub-issue parent response exceeds body bound",
                        )
                    })?;
                let value = serde_json::from_slice(&body).map_err(|_| {
                    GitHubOperationError::Malformed("sub-issue parent JSON response")
                })?;
                parse_sub_issue_ref(&value, self.policy.limits()).map(Some)
            }
            404 => Ok(None),
            401 | 403 => Err(GitHubOperationError::Unauthorized),
            410 => Err(GitHubOperationError::SubIssueFeatureUnavailable),
            429 => Err(GitHubOperationError::RateLimited),
            status => Err(GitHubOperationError::Transport(
                self.redactor
                    .safe_text(format!("sub-issue parent read returned status {status}")),
            )),
        }
    }

    /// Add one native sub-issue behind the live-mutation gate.
    ///
    /// A pre-read makes an existing edge a no-op. Every accepted or
    /// precondition-conflicted mutation proves the final relation by a fresh
    /// list read-back; it never asks GitHub to replace an existing parent.
    ///
    /// # Errors
    /// Returns `MutationRefused` before any read or write when authorization
    /// fails. Other failures remain typed and an unproven write returns
    /// `AmbiguousMutation` rather than being retried blindly.
    pub async fn add_sub_issue(
        &self,
        cancellation: &dyn ProcessCancellation,
        authorization: &LiveMutationRequest<'_>,
        edge: SubIssueEdge<'_>,
    ) -> Result<SubIssueMutationReceipt, GitHubOperationError> {
        self.mutate_sub_issue(cancellation, authorization, edge, true)
            .await
    }

    /// Remove one native sub-issue behind the live-mutation gate.
    ///
    /// A pre-read makes an absent edge a no-op. Every accepted or
    /// precondition-conflicted mutation proves the final relation by a fresh
    /// list read-back.
    ///
    /// # Errors
    /// Returns `MutationRefused` before any read or write when authorization
    /// fails. Other failures remain typed and an unproven write returns
    /// `AmbiguousMutation` rather than being retried blindly.
    pub async fn remove_sub_issue(
        &self,
        cancellation: &dyn ProcessCancellation,
        authorization: &LiveMutationRequest<'_>,
        edge: SubIssueEdge<'_>,
    ) -> Result<SubIssueMutationReceipt, GitHubOperationError> {
        self.mutate_sub_issue(cancellation, authorization, edge, false)
            .await
    }

    /// Add one blocked-by dependency edge behind the live-mutation gate, with a
    /// pre-read freshness and idempotency check and exact read-back.
    ///
    /// # Errors
    /// Returns `MutationRefused` when authorization fails, and a typed error on
    /// cancellation, deadline, authorization, an unavailable dependency API,
    /// transport failure, or a read-back that does not reflect the edge.
    pub async fn add_blocked_by(
        &self,
        cancellation: &dyn ProcessCancellation,
        authorization: &LiveMutationRequest<'_>,
        edge: DependencyEdge<'_>,
    ) -> Result<DependencyMutationReceipt, GitHubOperationError> {
        authorize_mutation(authorization)?;
        validate_repo(edge.owner, edge.repo)?;
        self.dependency_target_precondition(cancellation, edge)
            .await?;
        let before = self
            .list_blocked_by(cancellation, edge.owner, edge.repo, edge.client_issue)
            .await?;
        if dependency_present(&before, edge.blocker_id) {
            let current_target = self
                .dependency_target_precondition(cancellation, edge)
                .await?;
            return Ok(DependencyMutationReceipt {
                outcome: DependencyMutation::AlreadyInDesiredState,
                updated_at: current_target.map(|target| target.updated_at),
            });
        }
        let before_target = self
            .dependency_target_precondition(cancellation, edge)
            .await?;
        let uri = format!(
            "/repos/{}/{}/issues/{}/dependencies/blocked_by",
            edge.owner, edge.repo, edge.client_issue,
        );
        let body = json!({ "issue_id": edge.blocker_id });
        let status = self
            .send_status(cancellation, false, &uri, Some(&body))
            .await?;
        self.settle_dependency(cancellation, edge, status, true, before_target)
            .await
    }

    /// Remove one blocked-by dependency edge behind the live-mutation gate, with
    /// a pre-read freshness and idempotency check and exact read-back.
    ///
    /// # Errors
    /// Returns `MutationRefused` when authorization fails, and a typed error on
    /// cancellation, deadline, authorization, an unavailable dependency API,
    /// transport failure, or a read-back that still reflects the edge.
    pub async fn remove_blocked_by(
        &self,
        cancellation: &dyn ProcessCancellation,
        authorization: &LiveMutationRequest<'_>,
        edge: DependencyEdge<'_>,
    ) -> Result<DependencyMutationReceipt, GitHubOperationError> {
        authorize_mutation(authorization)?;
        validate_repo(edge.owner, edge.repo)?;
        self.dependency_target_precondition(cancellation, edge)
            .await?;
        let before = self
            .list_blocked_by(cancellation, edge.owner, edge.repo, edge.client_issue)
            .await?;
        if !dependency_present(&before, edge.blocker_id) {
            let current_target = self
                .dependency_target_precondition(cancellation, edge)
                .await?;
            return Ok(DependencyMutationReceipt {
                outcome: DependencyMutation::AlreadyInDesiredState,
                updated_at: current_target.map(|target| target.updated_at),
            });
        }
        let before_target = self
            .dependency_target_precondition(cancellation, edge)
            .await?;
        let uri = format!(
            "/repos/{}/{}/issues/{}/dependencies/blocked_by/{}",
            edge.owner, edge.repo, edge.client_issue, edge.blocker_id,
        );
        let status = self.send_status(cancellation, true, &uri, None).await?;
        self.settle_dependency(cancellation, edge, status, false, before_target)
            .await
    }

    async fn existing_head_pull_request(
        &self,
        cancellation: &dyn ProcessCancellation,
        spec: &PullRequestSpec<'_>,
    ) -> Result<Option<PullRequest>, GitHubOperationError> {
        let existing = self
            .list_open_pull_requests(cancellation, spec.owner, spec.repo, spec.head)
            .await?;
        match reconcile_create(&existing, spec.head) {
            CreatePlan::ReturnExisting(number) => Ok(Some(
                self.get_pull_request(cancellation, spec.owner, spec.repo, number)
                    .await?,
            )),
            CreatePlan::Create => Ok(None),
        }
    }

    async fn merge_precondition(
        &self,
        cancellation: &dyn ProcessCancellation,
        request: &PullRequestMerge<'_>,
    ) -> Result<Option<PullRequestMergeResult>, GitHubOperationError> {
        let current = self
            .release_candidate_pull_request(
                cancellation,
                request.owner,
                request.repo,
                request.number,
            )
            .await?;
        if current.head_oid != request.expected_head_oid {
            return Ok(Some(PullRequestMergeResult::HeadChanged));
        }
        Ok(Some(match current.state {
            ReleaseCandidatePullRequestState::Merged => PullRequestMergeResult::AlreadyMerged,
            ReleaseCandidatePullRequestState::Closed => PullRequestMergeResult::Closed,
            ReleaseCandidatePullRequestState::Open => match self
                .pull_request_review_state(
                    cancellation,
                    request.owner,
                    request.repo,
                    request.number,
                )
                .await?
            {
                PullRequestReviewState {
                    merge_state_status: MergeStateStatus::Blocked,
                    ..
                } => PullRequestMergeResult::BranchProtection,
                PullRequestReviewState {
                    mergeable: Mergeable::Conflicting,
                    ..
                } => PullRequestMergeResult::MergeConflict,
                _ => return Ok(None),
            },
        }))
    }

    async fn send_pull_request_merge(
        &self,
        cancellation: &dyn ProcessCancellation,
        request: &PullRequestMerge<'_>,
    ) -> Result<PullRequestMergeResult, GitHubOperationError> {
        let route = format!(
            "/repos/{}/{}/pulls/{}/merge",
            request.owner, request.repo, request.number
        );
        let body = merge_body(request);
        let limit = self.policy.limits().body_bytes();
        let exchange = async {
            let response = self
                .client
                ._put(route.as_str(), Some(&body))
                .await
                .map_err(MergeExchangeError::Transport)?;
            let status = response.status().as_u16();
            let body = Limited::new(response.into_body(), limit)
                .collect()
                .await
                .map_err(|_| MergeExchangeError::BodyLimit)?
                .to_bytes()
                .to_vec();
            Ok::<_, MergeExchangeError>((status, body))
        };
        let (status, body) = match self.guard_operation(cancellation, exchange).await {
            Ok(Ok(value)) => value,
            Ok(Err(MergeExchangeError::Transport(error))) => {
                return Err(self.transport_error(&error));
            }
            Ok(Err(MergeExchangeError::BodyLimit)) => {
                return Err(GitHubOperationError::Malformed(
                    "pull request merge response body",
                ));
            }
            Err(completion) => return Err(completion_error(completion)),
        };
        classify_merge_response(status, &body, self.policy.limits())
    }

    async fn reconcile_after_merge_uncertainty(
        &self,
        cancellation: &dyn ProcessCancellation,
        request: &PullRequestMerge<'_>,
        _original: GitHubOperationError,
    ) -> Result<PullRequestMergeResult, GitHubOperationError> {
        match self.merge_precondition(cancellation, request).await {
            Ok(Some(PullRequestMergeResult::AlreadyMerged)) => {
                Ok(PullRequestMergeResult::AlreadyMerged)
            }
            Ok(Some(PullRequestMergeResult::HeadChanged)) => {
                Ok(PullRequestMergeResult::HeadChanged)
            }
            Ok(_) | Err(_) => Err(GitHubOperationError::AmbiguousMutation),
        }
    }

    async fn reconcile_after_create_failure(
        &self,
        cancellation: &dyn ProcessCancellation,
        spec: &PullRequestSpec<'_>,
        error: GitHubOperationError,
    ) -> Result<CreatedPullRequest, GitHubOperationError> {
        match self.existing_head_pull_request(cancellation, spec).await {
            Ok(Some(existing)) => Ok(CreatedPullRequest {
                pull_request: existing,
                created: false,
            }),
            Ok(None) | Err(_) => Err(error),
        }
    }

    async fn mutate_sub_issue(
        &self,
        cancellation: &dyn ProcessCancellation,
        authorization: &LiveMutationRequest<'_>,
        edge: SubIssueEdge<'_>,
        adding: bool,
    ) -> Result<SubIssueMutationReceipt, GitHubOperationError> {
        authorize_mutation(authorization)?;
        validate_repo(edge.owner, edge.repo)?;
        validate_issue_number(edge.parent_issue, "sub-issue parent number")?;
        if edge.sub_issue_id == 0 {
            return Err(GitHubOperationError::Malformed("sub-issue id"));
        }

        let _mutation = self.mutation_lock.lock().await;
        let before = self
            .list_sub_issues(cancellation, edge.owner, edge.repo, edge.parent_issue)
            .await?;
        if sub_issue_present(&before, edge.sub_issue_id) == adding {
            return Ok(SubIssueMutationReceipt {
                outcome: SubIssueMutation::AlreadyInDesiredState,
            });
        }

        let (route, delete) = if adding {
            (
                format!(
                    "/repos/{}/{}/issues/{}/sub_issues",
                    edge.owner, edge.repo, edge.parent_issue
                ),
                false,
            )
        } else {
            (
                format!(
                    "/repos/{}/{}/issues/{}/sub_issue",
                    edge.owner, edge.repo, edge.parent_issue
                ),
                true,
            )
        };
        let body = json!({ "sub_issue_id": edge.sub_issue_id });
        match self
            .send_status(cancellation, delete, route.as_str(), Some(&body))
            .await
        {
            Ok(status) => {
                self.settle_sub_issue(cancellation, edge, adding, status)
                    .await
            }
            Err(error) if requires_sub_issue_reconciliation(&error) => {
                self.reconcile_sub_issue_mutation(cancellation, edge, adding)
                    .await
            }
            Err(error) => Err(error),
        }
    }

    async fn settle_sub_issue(
        &self,
        cancellation: &dyn ProcessCancellation,
        edge: SubIssueEdge<'_>,
        adding: bool,
        status: u16,
    ) -> Result<SubIssueMutationReceipt, GitHubOperationError> {
        match classify_sub_issue_write(adding, status) {
            SubIssueWrite::Accepted => {
                self.confirm_sub_issue_mutation(
                    cancellation,
                    edge,
                    adding,
                    GitHubOperationError::Malformed(
                        "sub-issue mutation not reflected in read-back",
                    ),
                )
                .await
            }
            SubIssueWrite::PreconditionFailed => {
                self.confirm_sub_issue_mutation(
                    cancellation,
                    edge,
                    adding,
                    GitHubOperationError::SubIssuePreconditionFailed,
                )
                .await
            }
            SubIssueWrite::FeatureUnavailable => {
                Err(GitHubOperationError::SubIssueFeatureUnavailable)
            }
            SubIssueWrite::Unauthorized => Err(GitHubOperationError::Unauthorized),
            SubIssueWrite::RateLimited => Err(GitHubOperationError::RateLimited),
            SubIssueWrite::Failed => {
                self.reconcile_sub_issue_mutation(cancellation, edge, adding)
                    .await
            }
        }
    }

    async fn reconcile_sub_issue_mutation(
        &self,
        cancellation: &dyn ProcessCancellation,
        edge: SubIssueEdge<'_>,
        adding: bool,
    ) -> Result<SubIssueMutationReceipt, GitHubOperationError> {
        self.confirm_sub_issue_mutation(
            cancellation,
            edge,
            adding,
            GitHubOperationError::AmbiguousMutation,
        )
        .await
    }

    async fn confirm_sub_issue_mutation(
        &self,
        cancellation: &dyn ProcessCancellation,
        edge: SubIssueEdge<'_>,
        adding: bool,
        mismatch: GitHubOperationError,
    ) -> Result<SubIssueMutationReceipt, GitHubOperationError> {
        match self
            .list_sub_issues(cancellation, edge.owner, edge.repo, edge.parent_issue)
            .await
        {
            Ok(after) if sub_issue_present(&after, edge.sub_issue_id) == adding => {
                Ok(SubIssueMutationReceipt {
                    outcome: SubIssueMutation::Applied,
                })
            }
            Ok(_) => Err(mismatch),
            Err(_) => Err(GitHubOperationError::AmbiguousMutation),
        }
    }

    async fn settle_dependency(
        &self,
        cancellation: &dyn ProcessCancellation,
        edge: DependencyEdge<'_>,
        status: u16,
        adding: bool,
        before_target: Option<DependencyTarget>,
    ) -> Result<DependencyMutationReceipt, GitHubOperationError> {
        match classify_dependency_write(status) {
            DependencyWrite::FeatureUnavailable => {
                return Err(GitHubOperationError::DependencyFeatureUnavailable);
            }
            DependencyWrite::Unauthorized => return Err(GitHubOperationError::Unauthorized),
            DependencyWrite::Failed => {
                return Err(GitHubOperationError::Transport(self.redactor.safe_text(
                    format!("dependency mutation returned status {status}"),
                )));
            }
            DependencyWrite::Accepted | DependencyWrite::Duplicate => {}
        }
        let after = self
            .list_blocked_by(cancellation, edge.owner, edge.repo, edge.client_issue)
            .await?;
        if dependency_present(&after, edge.blocker_id) == adding {
            let updated_at = match before_target {
                Some(target) => {
                    let current = self.dependency_target(cancellation, edge).await?;
                    if current.updated_at == target.updated_at {
                        return Err(GitHubOperationError::Malformed(
                            "dependency mutation did not advance target updated_at",
                        ));
                    }
                    Some(current.updated_at)
                }
                None => None,
            };
            Ok(DependencyMutationReceipt {
                outcome: DependencyMutation::Applied,
                updated_at,
            })
        } else {
            Err(GitHubOperationError::Malformed(
                "dependency mutation not reflected in read-back",
            ))
        }
    }

    async fn dependency_target_precondition(
        &self,
        cancellation: &dyn ProcessCancellation,
        edge: DependencyEdge<'_>,
    ) -> Result<Option<DependencyTarget>, GitHubOperationError> {
        let Some(expected_updated_at) = edge.expected_updated_at else {
            return Ok(None);
        };
        let expected_updated_at = normalize_utc_rfc3339_timestamp(expected_updated_at).ok_or(
            GitHubOperationError::Malformed("expected dependency updated_at"),
        )?;
        let target = self.dependency_target(cancellation, edge).await?;
        if target.updated_at != expected_updated_at {
            return Err(GitHubOperationError::StaleDependencyTarget);
        }
        if target_has_protected_lifecycle_state(&target) {
            return Err(GitHubOperationError::ProtectedDependencyTarget);
        }
        let comments = self.dependency_comments(cancellation, edge).await?;
        if target_has_security_content(&target, &comments) {
            return Err(GitHubOperationError::SecuritySensitiveDependencyTarget);
        }
        Ok(Some(target))
    }

    async fn dependency_target(
        &self,
        cancellation: &dyn ProcessCancellation,
        edge: DependencyEdge<'_>,
    ) -> Result<DependencyTarget, GitHubOperationError> {
        let route = format!(
            "/repos/{}/{}/issues/{}",
            edge.owner, edge.repo, edge.client_issue
        );
        let value = self.dependency_json(cancellation, &route).await?;
        parse_dependency_target(&value, self.policy.limits())
    }

    async fn dependency_pages(
        &self,
        cancellation: &dyn ProcessCancellation,
        initial_route: &str,
    ) -> Result<Vec<DependencyRef>, GitHubOperationError> {
        self.issue_ref_pages(
            cancellation,
            initial_route,
            IssueGraphFeature::Dependency,
            parse_dependency_refs,
        )
        .await
    }

    async fn sub_issue_pages(
        &self,
        cancellation: &dyn ProcessCancellation,
        initial_route: &str,
    ) -> Result<Vec<SubIssueRef>, GitHubOperationError> {
        self.issue_ref_pages(
            cancellation,
            initial_route,
            IssueGraphFeature::SubIssue,
            parse_sub_issue_refs,
        )
        .await
    }

    async fn issue_ref_pages(
        &self,
        cancellation: &dyn ProcessCancellation,
        initial_route: &str,
        feature: IssueGraphFeature,
        parse_page: fn(
            &Value,
            GitHubResponseLimits,
        ) -> Result<Vec<DependencyRef>, GitHubOperationError>,
    ) -> Result<Vec<DependencyRef>, GitHubOperationError> {
        let limits = self.policy.limits();
        let mut route = initial_route.to_owned();
        let mut issue_refs = Vec::new();
        for _ in 0..limits.pages() {
            let (value, next) = self
                .issue_graph_json_page(cancellation, &route, feature)
                .await?;
            let page = parse_page(&value, limits)?;
            if issue_refs.len().saturating_add(page.len()) > limits.items() {
                return Err(GitHubOperationError::Malformed(
                    feature.list_bound_error_context(),
                ));
            }
            issue_refs.extend(page);
            let Some(next) = next else {
                return Ok(issue_refs);
            };
            #[cfg(any(test, feature = "test-support"))]
            {
                route = self.issue_graph_continuation(&next, feature)?;
            }
            #[cfg(not(any(test, feature = "test-support")))]
            {
                route = Self::issue_graph_continuation(&next, feature)?;
            }
        }
        Err(GitHubOperationError::Malformed(
            feature.pagination_bound_error_context(),
        ))
    }

    async fn dependency_comments(
        &self,
        cancellation: &dyn ProcessCancellation,
        edge: DependencyEdge<'_>,
    ) -> Result<Vec<String>, GitHubOperationError> {
        let limits = self.policy.limits();
        let mut route = format!(
            "/repos/{}/{}/issues/{}/comments?per_page=100",
            edge.owner, edge.repo, edge.client_issue
        );
        let mut comments = Vec::new();
        for _ in 0..limits.pages() {
            let (value, next) = self.dependency_json_page(cancellation, &route).await?;
            let page = parse_dependency_comments(&value, limits)?;
            if comments.len().saturating_add(page.len()) > limits.items() {
                return Err(GitHubOperationError::Malformed(
                    "dependency comments exceed item bound",
                ));
            }
            comments.extend(page);
            let Some(next) = next else {
                return Ok(comments);
            };
            #[cfg(any(test, feature = "test-support"))]
            {
                route = self.issue_graph_continuation(&next, IssueGraphFeature::Dependency)?;
            }
            #[cfg(not(any(test, feature = "test-support")))]
            {
                route = Self::issue_graph_continuation(&next, IssueGraphFeature::Dependency)?;
            }
        }
        Err(GitHubOperationError::Malformed(
            "dependency comment pagination exceeds page bound",
        ))
    }

    async fn dependency_json(
        &self,
        cancellation: &dyn ProcessCancellation,
        route: &str,
    ) -> Result<Value, GitHubOperationError> {
        self.dependency_json_page(cancellation, route)
            .await
            .map(|(value, _)| value)
    }

    async fn dependency_json_page(
        &self,
        cancellation: &dyn ProcessCancellation,
        route: &str,
    ) -> Result<(Value, Option<String>), GitHubOperationError> {
        self.issue_graph_json_page(cancellation, route, IssueGraphFeature::Dependency)
            .await
    }

    async fn issue_graph_json_page(
        &self,
        cancellation: &dyn ProcessCancellation,
        route: &str,
        feature: IssueGraphFeature,
    ) -> Result<(Value, Option<String>), GitHubOperationError> {
        let result = self
            .guard_operation(cancellation, self.client._get(route))
            .await;
        let response = match result {
            Ok(Ok(response)) => response,
            Ok(Err(error)) => return Err(self.transport_error(&error)),
            Err(completion) => return Err(completion_error(completion)),
        };
        match response.status().as_u16() {
            200 => {}
            401 | 403 => return Err(GitHubOperationError::Unauthorized),
            404 => return Err(feature.unavailable_error()),
            410 if matches!(feature, IssueGraphFeature::SubIssue) => {
                return Err(GitHubOperationError::SubIssueFeatureUnavailable);
            }
            429 if matches!(feature, IssueGraphFeature::SubIssue) => {
                return Err(GitHubOperationError::RateLimited);
            }
            status => {
                return Err(GitHubOperationError::Transport(self.redactor.safe_text(
                    format!("{} read returned status {status}", feature.name()),
                )));
            }
        }
        let next = issue_graph_next_link(response.headers(), feature)?;
        let body = collect_bounded_response(response, self.policy.limits().body_bytes())
            .await
            .map_err(|()| GitHubOperationError::Malformed(feature.body_error_context()))?;
        let value = serde_json::from_slice(&body)
            .map_err(|_| GitHubOperationError::Malformed(feature.json_error_context()))?;
        Ok((value, next))
    }

    #[cfg(any(test, feature = "test-support"))]
    fn issue_graph_continuation(
        &self,
        continuation: &str,
        feature: IssueGraphFeature,
    ) -> Result<String, GitHubOperationError> {
        if let Some(base) = &self.test_continuation_base {
            let next = base.join(continuation).map_err(|_| {
                GitHubOperationError::Malformed(feature.pagination_link_error_context())
            })?;
            if next.origin() != base.origin() {
                return Err(GitHubOperationError::Malformed(
                    feature.pagination_link_error_context(),
                ));
            }
            return Ok(next.to_string());
        }
        Self::continuation_url(GITHUB_API_BASE, continuation)
            .map(|url| url.to_string())
            .map_err(|_| GitHubOperationError::Malformed(feature.pagination_link_error_context()))
    }

    #[cfg(not(any(test, feature = "test-support")))]
    fn issue_graph_continuation(
        continuation: &str,
        feature: IssueGraphFeature,
    ) -> Result<String, GitHubOperationError> {
        Self::continuation_url(GITHUB_API_BASE, continuation)
            .map(|url| url.to_string())
            .map_err(|_| GitHubOperationError::Malformed(feature.pagination_link_error_context()))
    }

    async fn fetch_json(
        &self,
        cancellation: &dyn ProcessCancellation,
        operation: impl Future<Output = octocrab::Result<Value>> + Send,
    ) -> Result<Value, GitHubOperationError> {
        match self.guard_operation(cancellation, operation).await {
            Ok(Ok(value)) => Ok(value),
            Ok(Err(error)) => Err(self.transport_error(&error)),
            Err(completion) => Err(completion_error(completion)),
        }
    }

    async fn send_status(
        &self,
        cancellation: &dyn ProcessCancellation,
        delete: bool,
        uri: &str,
        body: Option<&Value>,
    ) -> Result<u16, GitHubOperationError> {
        let result = if delete {
            self.guard_operation(cancellation, self.client._delete(uri, body))
                .await
        } else {
            self.guard_operation(cancellation, self.client._post(uri, body))
                .await
        };
        match result {
            Ok(Ok(response)) => Ok(response.status().as_u16()),
            Ok(Err(error)) => Err(self.transport_error(&error)),
            Err(completion) => Err(completion_error(completion)),
        }
    }

    fn transport_error(&self, error: &octocrab::Error) -> GitHubOperationError {
        if matches!(octocrab_status(error), Some(401 | 403)) {
            return GitHubOperationError::Unauthorized;
        }
        let bounded: String = error.to_string().chars().take(DIAGNOSTIC_LIMIT).collect();
        GitHubOperationError::Transport(self.redactor.safe_text(bounded))
    }
}

const fn completion_error(error: GitHubCompletionError) -> GitHubOperationError {
    match error {
        GitHubCompletionError::Cancelled => GitHubOperationError::Cancelled,
        GitHubCompletionError::DeadlineExceeded => GitHubOperationError::DeadlineExceeded,
    }
}

fn authorize_mutation(authorization: &LiveMutationRequest<'_>) -> Result<(), GitHubOperationError> {
    match check_live_mutation_auth(authorization) {
        LiveMutationDecision::Authorized(_) => Ok(()),
        LiveMutationDecision::Refused(reason) => Err(GitHubOperationError::MutationRefused(reason)),
    }
}

fn validate_repo(owner: &str, repo: &str) -> Result<(), GitHubOperationError> {
    if is_safe_segment(owner) && is_safe_segment(repo) {
        Ok(())
    } else {
        Err(GitHubOperationError::Malformed("repository owner or name"))
    }
}

const fn validate_issue_number(
    value: u64,
    context: &'static str,
) -> Result<(), GitHubOperationError> {
    if value == 0 {
        Err(GitHubOperationError::Malformed(context))
    } else {
        Ok(())
    }
}

fn is_safe_segment(segment: &str) -> bool {
    !segment.is_empty()
        && segment.len() <= 128
        && segment
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || b"-._".contains(&byte))
}

fn edit_body(edit: &PullRequestEdit<'_>) -> Value {
    let mut body = Map::new();
    if let Some(title) = edit.title {
        body.insert("title".to_owned(), Value::from(title));
    }
    if let Some(text) = edit.body {
        body.insert("body".to_owned(), Value::from(text));
    }
    if let Some(state) = edit.state {
        let rendered = match state {
            PullRequestState::Open => "open",
            PullRequestState::Closed => "closed",
        };
        body.insert("state".to_owned(), Value::from(rendered));
    }
    if let Some(base) = edit.base {
        body.insert("base".to_owned(), Value::from(base));
    }
    Value::Object(body)
}

fn merge_body(request: &PullRequestMerge<'_>) -> Value {
    let mut body = Map::new();
    body.insert("sha".to_owned(), Value::from(request.expected_head_oid));
    body.insert(
        "merge_method".to_owned(),
        Value::from(match request.method {
            PullRequestMergeMethod::Merge => "merge",
            PullRequestMergeMethod::Squash => "squash",
            PullRequestMergeMethod::Rebase => "rebase",
        }),
    );
    if let Some(title) = request.commit_title {
        body.insert("commit_title".to_owned(), Value::from(title));
    }
    if let Some(message) = request.commit_message {
        body.insert("commit_message".to_owned(), Value::from(message));
    }
    Value::Object(body)
}

fn classify_merge_response(
    status: u16,
    body: &[u8],
    limits: GitHubResponseLimits,
) -> Result<PullRequestMergeResult, GitHubOperationError> {
    match status {
        200 => parse_merge_success(body, limits),
        403 if merge_response_is_rate_limited(body) => Err(GitHubOperationError::RateLimited),
        401 | 403 => Err(GitHubOperationError::Unauthorized),
        405 => Ok(PullRequestMergeResult::MergeUnavailable),
        409 => Ok(PullRequestMergeResult::HeadChanged),
        422 => Ok(PullRequestMergeResult::ValidationFailed),
        429 => Err(GitHubOperationError::RateLimited),
        500..=599 => Err(GitHubOperationError::AmbiguousMutation),
        _ => Err(GitHubOperationError::Transport(
            larch_core::RuntimeRedactor::default()
                .safe_text(format!("pull request merge returned status {status}")),
        )),
    }
}

fn parse_merge_success(
    body: &[u8],
    limits: GitHubResponseLimits,
) -> Result<PullRequestMergeResult, GitHubOperationError> {
    let value: Value = serde_json::from_slice(body)
        .map_err(|_| GitHubOperationError::Malformed("pull request merge response"))?;
    let object = as_object(&value)?;
    match object.get("merged").and_then(Value::as_bool) {
        Some(true) => {
            let oid = required_str(object, "sha", limits, "pull request merge commit oid")?;
            if !is_git_object_id(&oid) {
                return Err(GitHubOperationError::Malformed(
                    "pull request merge commit oid",
                ));
            }
            Ok(PullRequestMergeResult::Merged {
                merge_commit_oid: oid,
            })
        }
        Some(false) => classify_merge_rejection(object, limits),
        None => Err(GitHubOperationError::Malformed("pull request merge result")),
    }
}

fn classify_merge_rejection(
    object: &Map<String, Value>,
    limits: GitHubResponseLimits,
) -> Result<PullRequestMergeResult, GitHubOperationError> {
    let message = required_str(object, "message", limits, "pull request merge message")?;
    match message.as_str() {
        "Pull Request is not mergeable" => Ok(PullRequestMergeResult::MergeConflict),
        "Pull Request merge is blocked by branch protection" => {
            Ok(PullRequestMergeResult::BranchProtection)
        }
        _ => Err(GitHubOperationError::Malformed(
            "pull request merge rejection",
        )),
    }
}

fn merge_response_is_rate_limited(body: &[u8]) -> bool {
    serde_json::from_slice::<Value>(body)
        .ok()
        .and_then(|value| value.get("message")?.as_str().map(str::to_owned))
        .is_some_and(|message| {
            message
                .to_ascii_lowercase()
                .starts_with("api rate limit exceeded")
        })
}

const fn requires_merge_reconciliation(error: &GitHubOperationError) -> bool {
    matches!(
        error,
        GitHubOperationError::Transport(_)
            | GitHubOperationError::AmbiguousMutation
            | GitHubOperationError::DeadlineExceeded
            | GitHubOperationError::Malformed(_)
    )
}

fn is_git_object_id(oid: &str) -> bool {
    matches!(oid.len(), 40 | 64)
        && oid
            .bytes()
            .all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte))
}

fn reconcile_create(existing: &[PullRequest], head_ref: &str) -> CreatePlan {
    existing
        .iter()
        .find(|pull_request| {
            pull_request.state == PullRequestState::Open && pull_request.head_ref == head_ref
        })
        .map_or(CreatePlan::Create, |pull_request| {
            CreatePlan::ReturnExisting(pull_request.number)
        })
}

const fn classify_dependency_write(status: u16) -> DependencyWrite {
    match status {
        200 | 201 | 204 => DependencyWrite::Accepted,
        401 | 403 => DependencyWrite::Unauthorized,
        404 => DependencyWrite::FeatureUnavailable,
        422 => DependencyWrite::Duplicate,
        _ => DependencyWrite::Failed,
    }
}

const fn classify_sub_issue_write(adding: bool, status: u16) -> SubIssueWrite {
    match status {
        401 | 403 => SubIssueWrite::Unauthorized,
        429 => SubIssueWrite::RateLimited,
        201 if adding => SubIssueWrite::Accepted,
        200 if !adding => SubIssueWrite::Accepted,
        400 | 422 => SubIssueWrite::PreconditionFailed,
        404 if !adding => SubIssueWrite::PreconditionFailed,
        404 | 410 => SubIssueWrite::FeatureUnavailable,
        _ => SubIssueWrite::Failed,
    }
}

fn dependency_present(edges: &[DependencyRef], blocker_id: u64) -> bool {
    edges.iter().any(|edge| edge.issue_id == blocker_id)
}

fn sub_issue_present(edges: &[SubIssueRef], sub_issue_id: u64) -> bool {
    edges.iter().any(|edge| edge.issue_id == sub_issue_id)
}

const fn requires_sub_issue_reconciliation(error: &GitHubOperationError) -> bool {
    matches!(
        error,
        GitHubOperationError::Transport(_)
            | GitHubOperationError::AmbiguousMutation
            | GitHubOperationError::DeadlineExceeded
            | GitHubOperationError::Malformed(_)
    )
}

fn issue_graph_next_link(
    headers: &http::HeaderMap,
    feature: IssueGraphFeature,
) -> Result<Option<String>, GitHubOperationError> {
    let mut next = None;
    for raw in headers.get_all(LINK) {
        let raw = raw.to_str().map_err(|_| {
            GitHubOperationError::Malformed(feature.pagination_link_error_context())
        })?;
        for entry in raw.split(',') {
            let mut parts = entry.trim().split(';');
            let target = parts.next().unwrap_or_default().trim();
            let is_next = parts.any(|parameter| {
                let parameter = parameter.trim();
                parameter.strip_prefix("rel=").is_some_and(|value| {
                    value
                        .trim_matches('"')
                        .split_ascii_whitespace()
                        .any(|rel| rel.eq_ignore_ascii_case("next"))
                })
            });
            if !is_next {
                continue;
            }
            let target = target
                .strip_prefix('<')
                .and_then(|value| value.strip_suffix('>'))
                .filter(|value| !value.is_empty())
                .ok_or_else(|| {
                    GitHubOperationError::Malformed(feature.pagination_link_error_context())
                })?;
            if next.replace(target.to_owned()).is_some() {
                return Err(GitHubOperationError::Malformed(
                    feature.pagination_link_error_context(),
                ));
            }
        }
    }
    Ok(next)
}

fn parse_dependency_target(
    value: &Value,
    limits: GitHubResponseLimits,
) -> Result<DependencyTarget, GitHubOperationError> {
    let object = as_object(value)?;
    let updated_at = required_str(object, "updated_at", limits, "dependency target updated_at")?;
    // Normalize both REST timestamps and typed issue snapshots to GitHub's
    // canonical UTC spelling before the freshness comparison.
    let updated_at = normalize_utc_rfc3339_timestamp(&updated_at).ok_or(
        GitHubOperationError::Malformed("dependency target updated_at"),
    )?;
    let state = required_str(object, "state", limits, "dependency target state")?;
    let title = required_str(object, "title", limits, "dependency target title")?;
    let body = object
        .get("body")
        .and_then(Value::as_str)
        .map(|body| bounded_string(body, limits, "dependency target body"))
        .transpose()?
        .unwrap_or_default();
    let labels = object
        .get("labels")
        .and_then(Value::as_array)
        .ok_or(GitHubOperationError::Malformed("dependency target labels"))?;
    if labels.len() > limits.items() {
        return Err(GitHubOperationError::Malformed(
            "dependency target labels exceed item bound",
        ));
    }
    let labels = labels
        .iter()
        .map(|label| {
            let label = as_object(label)?;
            required_str(label, "name", limits, "dependency target label")
        })
        .collect::<Result<Vec<_>, _>>()?;
    Ok(DependencyTarget {
        updated_at,
        state,
        title,
        body,
        labels,
    })
}

fn target_has_protected_lifecycle_state(target: &DependencyTarget) -> bool {
    if !target.state.eq_ignore_ascii_case("open")
        || target
            .labels
            .iter()
            .any(|label| label.to_ascii_lowercase().contains("clarif"))
        || protected_lifecycle_title(&target.title)
    {
        return true;
    }
    let body = without_triage_block(&target.body);
    body.as_deref()
        .is_none_or(|body| body.to_ascii_lowercase().contains("<!-- larch:"))
}

fn parse_dependency_comments(
    value: &Value,
    limits: GitHubResponseLimits,
) -> Result<Vec<String>, GitHubOperationError> {
    let comments = value
        .as_array()
        .ok_or(GitHubOperationError::Malformed("dependency comments"))?;
    if comments.len() > limits.items() {
        return Err(GitHubOperationError::Malformed(
            "dependency comments exceed item bound",
        ));
    }
    comments
        .iter()
        .map(|comment| {
            let object = as_object(comment)?;
            match object.get("body") {
                None | Some(Value::Null) => Ok(String::new()),
                Some(Value::String(body)) => {
                    bounded_string(body, limits, "dependency comment body")
                }
                Some(_) => Err(GitHubOperationError::Malformed("dependency comment body")),
            }
        })
        .collect()
}

fn target_has_security_content(target: &DependencyTarget, comments: &[String]) -> bool {
    target
        .labels
        .iter()
        .any(|label| matches!(label.to_lowercase().as_str(), "security" | "vulnerability"))
        || contains_security_term(&target.title)
        || contains_security_term(&target.body)
        || comments
            .iter()
            .any(|comment| contains_security_term(comment))
}

fn contains_security_term(text: &str) -> bool {
    SECURITY_CONTENT.is_match(&text.to_lowercase())
}

fn protected_lifecycle_title(title: &str) -> bool {
    let Some((prefix, remainder)) = title
        .strip_prefix('[')
        .and_then(|text| text.split_once("] "))
    else {
        return false;
    };
    !remainder.is_empty()
        && matches!(
            prefix.to_ascii_uppercase().as_str(),
            "IMPLEMENTING"
                | "DONE"
                | "DESIGNING"
                | "DESIGNED"
                | "STALLED"
                | "IN PROGRESS"
                | "PLANNED"
        )
}

fn without_triage_block(body: &str) -> Option<String> {
    const START: &str = "<!-- larch:triage:start -->";
    const END: &str = "<!-- larch:triage:end -->";
    let starts = body.match_indices(START).collect::<Vec<_>>();
    let ends = body.match_indices(END).collect::<Vec<_>>();
    match (starts.as_slice(), ends.as_slice()) {
        ([], []) => Some(body.to_owned()),
        ([(start, _)], [(end, _)]) if start < end => {
            Some(format!("{}{}", &body[..*start], &body[end + END.len()..]))
        }
        _ => None,
    }
}

fn normalize_utc_rfc3339_timestamp(value: &str) -> Option<String> {
    if value.is_empty() {
        return None;
    }
    let timestamp = DateTime::parse_from_rfc3339(value).ok()?;
    if timestamp.offset().local_minus_utc() != 0 {
        return None;
    }
    Some(github_utc_timestamp(&timestamp.with_timezone(&Utc)))
}

fn parse_pull_request(
    value: &Value,
    limits: GitHubResponseLimits,
) -> Result<PullRequest, GitHubOperationError> {
    let object = as_object(value)?;
    let merge_commit_oid = optional_str(
        object,
        "merge_commit_sha",
        limits,
        "pull request merge commit oid",
    )?;
    if merge_commit_oid
        .as_deref()
        .is_some_and(|oid| !is_git_object_id(oid))
    {
        return Err(GitHubOperationError::Malformed(
            "pull request merge commit oid",
        ));
    }
    Ok(PullRequest {
        number: required_u64(object, "number", "pull request number")?,
        state: parse_state(required_str(object, "state", limits, "pull request state")?.as_str())?,
        title: optional_str(object, "title", limits, "pull request title")?.unwrap_or_default(),
        head_ref: required_ref(object, "head", limits, "pull request head ref")?,
        base_ref: required_ref(object, "base", limits, "pull request base ref")?,
        draft: optional_bool(object, "draft", "pull request draft")?.unwrap_or(false),
        merged: optional_bool(object, "merged", "pull request merged")?.unwrap_or(false),
        merge_commit_oid,
    })
}

fn parse_pull_requests(
    value: &Value,
    limits: GitHubResponseLimits,
) -> Result<Vec<PullRequest>, GitHubOperationError> {
    let array = value
        .as_array()
        .ok_or(GitHubOperationError::Malformed("pull request list"))?;
    if array.len() > limits.items() {
        return Err(GitHubOperationError::Malformed(
            "pull request list exceeds item bound",
        ));
    }
    array
        .iter()
        .map(|element| parse_pull_request(element, limits))
        .collect()
}

fn parse_audit_pull_request(
    value: &Value,
    limits: GitHubResponseLimits,
) -> Result<AuditPullRequest, GitHubOperationError> {
    let object = as_object(value)?;
    let merged_at = optional_str(object, "merged_at", limits, "audit pull request merged_at")?;
    if merged_at
        .as_deref()
        .is_some_and(|timestamp| DateTime::parse_from_rfc3339(timestamp).is_err())
    {
        return Err(GitHubOperationError::Malformed(
            "audit pull request merged_at",
        ));
    }
    Ok(AuditPullRequest {
        number: required_u64(object, "number", "audit pull request number")?,
        title: optional_str(object, "title", limits, "audit pull request title")?
            .unwrap_or_default(),
        body: optional_str(object, "body", limits, "audit pull request body")?.unwrap_or_default(),
        base_ref: required_ref(object, "base", limits, "audit pull request base ref")?,
        merged_at,
    })
}

fn parse_audit_pull_requests(
    value: &Value,
    limits: GitHubResponseLimits,
) -> Result<Vec<AuditPullRequest>, GitHubOperationError> {
    let array = value
        .as_array()
        .ok_or(GitHubOperationError::Malformed("audit pull request list"))?;
    if array.len() > RELEASE_PAGE_SIZE {
        return Err(GitHubOperationError::Malformed(
            "audit pull request page exceeds item bound",
        ));
    }
    array
        .iter()
        .map(|element| parse_audit_pull_request(element, limits))
        .collect()
}

fn parse_release_pull_request(
    value: &Value,
    limits: GitHubResponseLimits,
) -> Result<ReleasePullRequest, GitHubOperationError> {
    let object = as_object(value)?;
    let labels = object
        .get("labels")
        .and_then(Value::as_array)
        .ok_or(GitHubOperationError::Malformed("pull request labels"))?;
    if labels.len() > limits.items() {
        return Err(GitHubOperationError::Malformed("pull request labels"));
    }
    let labels = labels
        .iter()
        .map(|label| {
            let label = as_object(label)?;
            required_str(label, "name", limits, "pull request label")
        })
        .collect::<Result<Vec<_>, _>>()?;
    let author = object
        .get("user")
        .and_then(Value::as_object)
        .and_then(|user| user.get("login"))
        .and_then(Value::as_str)
        .unwrap_or("unknown");
    if author.len() > limits.string_bytes() {
        return Err(GitHubOperationError::Malformed("pull request author"));
    }
    Ok(ReleasePullRequest {
        number: required_u64(object, "number", "pull request number")?,
        title: required_str(object, "title", limits, "pull request title")?,
        labels,
        author: author.to_owned(),
        url: required_str(object, "html_url", limits, "pull request url")?,
        head_ref: required_ref(object, "head", limits, "pull request head ref")?,
    })
}

fn parse_release_candidate_pull_request(
    value: &Value,
) -> Result<ReleaseCandidatePullRequest, GitHubOperationError> {
    let object = as_object(value)?;
    let state = match (
        object.get("state").and_then(Value::as_str),
        object.get("merged").and_then(Value::as_bool),
    ) {
        (_, Some(true)) => ReleaseCandidatePullRequestState::Merged,
        (Some("open"), _) => ReleaseCandidatePullRequestState::Open,
        (Some("closed"), _) => ReleaseCandidatePullRequestState::Closed,
        _ => {
            return Err(GitHubOperationError::Malformed(
                "release pull request state",
            ));
        }
    };
    let head_oid = object
        .get("head")
        .and_then(Value::as_object)
        .and_then(|head| head.get("sha"))
        .and_then(Value::as_str)
        .filter(|oid| {
            matches!(oid.len(), 40 | 64)
                && oid
                    .bytes()
                    .all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte))
        })
        .ok_or(GitHubOperationError::Malformed(
            "release pull request head oid",
        ))?;
    let merge_commit_oid = match object.get("merge_commit_sha") {
        None | Some(Value::Null) => None,
        Some(Value::String(oid)) if is_git_object_id(oid) => Some(oid.to_owned()),
        _ => {
            return Err(GitHubOperationError::Malformed(
                "release pull request merge commit oid",
            ));
        }
    };
    Ok(ReleaseCandidatePullRequest {
        state,
        head_oid: head_oid.to_owned(),
        merge_commit_oid,
    })
}

fn parse_release_pull_requests(
    value: &Value,
    limits: GitHubResponseLimits,
) -> Result<Vec<ReleasePullRequest>, GitHubOperationError> {
    let array = value
        .as_array()
        .ok_or(GitHubOperationError::Malformed("pull request list"))?;
    if array.len() > RELEASE_PAGE_SIZE {
        return Err(GitHubOperationError::Malformed(
            "pull request page exceeds item bound",
        ));
    }
    array
        .iter()
        .map(|element| parse_release_pull_request(element, limits))
        .collect()
}

#[derive(Debug)]
struct IssueClosureReferencePage {
    entries: BTreeMap<u64, Vec<String>>,
    has_next_page: bool,
    end_cursor: Option<String>,
}

fn parse_issue_closure_references(
    value: &Value,
    wanted: &BTreeSet<u64>,
    limits: GitHubResponseLimits,
) -> Result<IssueClosureReferencePage, GitHubOperationError> {
    let object = as_object(value)?;
    if graphql_has_errors(object) {
        return Err(GitHubOperationError::GraphqlErrors);
    }
    let connection = value
        .pointer("/data/repository/issues")
        .and_then(Value::as_object)
        .ok_or(GitHubOperationError::Malformed("graphql issue connection"))?;
    let nodes = connection
        .get("nodes")
        .and_then(Value::as_array)
        .ok_or(GitHubOperationError::Malformed("graphql issue nodes"))?;
    if nodes.len() > 100 {
        return Err(GitHubOperationError::Malformed("graphql issue page size"));
    }
    let mut entries = BTreeMap::new();
    for node in nodes {
        let node = as_object(node)?;
        let number = required_u64(node, "number", "graphql issue number")?;
        if !wanted.contains(&number) {
            continue;
        }
        let reference_connection = node
            .get("closedByPullRequestsReferences")
            .and_then(Value::as_object)
            .ok_or(GitHubOperationError::Malformed(
                "graphql issue closure references",
            ))?;
        let references = reference_connection
            .get("nodes")
            .and_then(Value::as_array)
            .ok_or(GitHubOperationError::Malformed(
                "graphql issue closure references",
            ))?;
        if references.len() > 100
            || reference_connection
                .get("pageInfo")
                .and_then(Value::as_object)
                .and_then(|page_info| page_info.get("hasNextPage"))
                .and_then(Value::as_bool)
                .ok_or(GitHubOperationError::Malformed(
                    "graphql issue closure-reference pageInfo",
                ))?
        {
            return Err(GitHubOperationError::Malformed(
                "graphql issue closure-reference pagination",
            ));
        }
        let references = references
            .iter()
            .map(|reference| {
                let reference = as_object(reference)?;
                required_str(
                    reference,
                    "url",
                    limits,
                    "graphql issue closure-reference URL",
                )
            })
            .collect::<Result<Vec<_>, _>>()?;
        entries.insert(number, references);
    }
    let page_info = connection
        .get("pageInfo")
        .and_then(Value::as_object)
        .ok_or(GitHubOperationError::Malformed("graphql issue pageInfo"))?;
    let has_next_page = page_info
        .get("hasNextPage")
        .and_then(Value::as_bool)
        .ok_or(GitHubOperationError::Malformed(
            "graphql issue pageInfo.hasNextPage",
        ))?;
    let end_cursor = match page_info.get("endCursor") {
        None | Some(Value::Null) => None,
        Some(Value::String(cursor)) if cursor.len() <= limits.string_bytes() => {
            Some(cursor.clone())
        }
        Some(_) => {
            return Err(GitHubOperationError::Malformed(
                "graphql issue pageInfo.endCursor",
            ));
        }
    };
    Ok(IssueClosureReferencePage {
        entries,
        has_next_page,
        end_cursor,
    })
}

fn parse_review_state(value: &Value) -> Result<PullRequestReviewState, GitHubOperationError> {
    let object = as_object(value)?;
    if graphql_has_errors(object) {
        return Err(GitHubOperationError::GraphqlErrors);
    }
    let pull_request = value
        .pointer("/data/repository/pullRequest")
        .and_then(Value::as_object)
        .ok_or(GitHubOperationError::Malformed("graphql pullRequest"))?;
    Ok(PullRequestReviewState {
        review_decision: parse_optional_review_decision(pull_request)?,
        merge_state_status: parse_merge_state_status(pull_request)?,
        mergeable: parse_mergeable(pull_request)?,
    })
}

fn graphql_has_errors(object: &Map<String, Value>) -> bool {
    match object.get("errors") {
        None | Some(Value::Null) => false,
        Some(Value::Array(entries)) => !entries.is_empty(),
        Some(_) => true,
    }
}

fn parse_optional_review_decision(
    object: &Map<String, Value>,
) -> Result<Option<ReviewDecision>, GitHubOperationError> {
    match object.get("reviewDecision") {
        None | Some(Value::Null) => Ok(None),
        Some(Value::String(raw)) => match raw.as_str() {
            "APPROVED" => Ok(Some(ReviewDecision::Approved)),
            "CHANGES_REQUESTED" => Ok(Some(ReviewDecision::ChangesRequested)),
            "REVIEW_REQUIRED" => Ok(Some(ReviewDecision::ReviewRequired)),
            _ => Err(GitHubOperationError::Malformed("reviewDecision")),
        },
        Some(_) => Err(GitHubOperationError::Malformed("reviewDecision")),
    }
}

fn parse_merge_state_status(
    object: &Map<String, Value>,
) -> Result<MergeStateStatus, GitHubOperationError> {
    match object.get("mergeStateStatus").and_then(Value::as_str) {
        Some("BEHIND") => Ok(MergeStateStatus::Behind),
        Some("BLOCKED") => Ok(MergeStateStatus::Blocked),
        Some("CLEAN") => Ok(MergeStateStatus::Clean),
        Some("DIRTY") => Ok(MergeStateStatus::Dirty),
        Some("DRAFT") => Ok(MergeStateStatus::Draft),
        Some("HAS_HOOKS") => Ok(MergeStateStatus::HasHooks),
        Some("UNKNOWN") => Ok(MergeStateStatus::Unknown),
        Some("UNSTABLE") => Ok(MergeStateStatus::Unstable),
        _ => Err(GitHubOperationError::Malformed("mergeStateStatus")),
    }
}

fn parse_mergeable(object: &Map<String, Value>) -> Result<Mergeable, GitHubOperationError> {
    match object.get("mergeable").and_then(Value::as_str) {
        Some("MERGEABLE") => Ok(Mergeable::Mergeable),
        Some("CONFLICTING") => Ok(Mergeable::Conflicting),
        Some("UNKNOWN") => Ok(Mergeable::Unknown),
        _ => Err(GitHubOperationError::Malformed("mergeable")),
    }
}

fn parse_dependency_refs(
    value: &Value,
    limits: GitHubResponseLimits,
) -> Result<Vec<DependencyRef>, GitHubOperationError> {
    let array = value
        .as_array()
        .ok_or(GitHubOperationError::Malformed("dependency list"))?;
    if array.len() > limits.items() {
        return Err(GitHubOperationError::Malformed(
            "dependency list exceeds item bound",
        ));
    }
    array
        .iter()
        .map(|element| {
            let object = as_object(element)?;
            parse_issue_ref(
                object,
                limits,
                "dependency issue number",
                "dependency issue id",
                "dependency issue state",
            )
        })
        .collect()
}

fn parse_sub_issue_refs(
    value: &Value,
    limits: GitHubResponseLimits,
) -> Result<Vec<SubIssueRef>, GitHubOperationError> {
    let array = value
        .as_array()
        .ok_or(GitHubOperationError::Malformed("sub-issue list"))?;
    if array.len() > limits.items() {
        return Err(GitHubOperationError::Malformed(
            "sub-issue list exceeds item bound",
        ));
    }
    array
        .iter()
        .map(|element| parse_sub_issue_ref(element, limits))
        .collect()
}

fn parse_sub_issue_ref(
    value: &Value,
    limits: GitHubResponseLimits,
) -> Result<SubIssueRef, GitHubOperationError> {
    parse_issue_ref(
        as_object(value)?,
        limits,
        "sub-issue number",
        "sub-issue id",
        "sub-issue state",
    )
}

fn parse_issue_ref(
    object: &Map<String, Value>,
    limits: GitHubResponseLimits,
    number_context: &'static str,
    id_context: &'static str,
    state_context: &'static str,
) -> Result<DependencyRef, GitHubOperationError> {
    Ok(DependencyRef {
        issue_number: required_u64(object, "number", number_context)?,
        issue_id: required_u64(object, "id", id_context)?,
        open: optional_str(object, "state", limits, state_context)?
            .is_some_and(|state| state.eq_ignore_ascii_case("open")),
    })
}

fn parse_state(raw: &str) -> Result<PullRequestState, GitHubOperationError> {
    match raw {
        "open" => Ok(PullRequestState::Open),
        "closed" => Ok(PullRequestState::Closed),
        _ => Err(GitHubOperationError::Malformed("pull request state")),
    }
}

fn as_object(value: &Value) -> Result<&Map<String, Value>, GitHubOperationError> {
    value
        .as_object()
        .ok_or(GitHubOperationError::Malformed("expected a JSON object"))
}

fn required_u64(
    object: &Map<String, Value>,
    key: &str,
    context: &'static str,
) -> Result<u64, GitHubOperationError> {
    object
        .get(key)
        .and_then(Value::as_u64)
        .ok_or(GitHubOperationError::Malformed(context))
}

fn required_str(
    object: &Map<String, Value>,
    key: &str,
    limits: GitHubResponseLimits,
    context: &'static str,
) -> Result<String, GitHubOperationError> {
    let text = object
        .get(key)
        .and_then(Value::as_str)
        .ok_or(GitHubOperationError::Malformed(context))?;
    bounded_string(text, limits, context)
}

fn required_ref(
    object: &Map<String, Value>,
    key: &str,
    limits: GitHubResponseLimits,
    context: &'static str,
) -> Result<String, GitHubOperationError> {
    let nested = object
        .get(key)
        .and_then(Value::as_object)
        .ok_or(GitHubOperationError::Malformed(context))?;
    required_str(nested, "ref", limits, context)
}

fn optional_str(
    object: &Map<String, Value>,
    key: &str,
    limits: GitHubResponseLimits,
    context: &'static str,
) -> Result<Option<String>, GitHubOperationError> {
    match object.get(key) {
        None | Some(Value::Null) => Ok(None),
        Some(Value::String(text)) => bounded_string(text, limits, context).map(Some),
        Some(_) => Err(GitHubOperationError::Malformed(context)),
    }
}

fn optional_bool(
    object: &Map<String, Value>,
    key: &str,
    context: &'static str,
) -> Result<Option<bool>, GitHubOperationError> {
    match object.get(key) {
        None | Some(Value::Null) => Ok(None),
        Some(Value::Bool(flag)) => Ok(Some(*flag)),
        Some(_) => Err(GitHubOperationError::Malformed(context)),
    }
}

fn bounded_string(
    text: &str,
    limits: GitHubResponseLimits,
    context: &'static str,
) -> Result<String, GitHubOperationError> {
    if text.len() > limits.string_bytes() {
        return Err(GitHubOperationError::Malformed(context));
    }
    Ok(text.to_owned())
}

#[cfg(test)]
mod tests {
    use super::{
        CreatePlan, DependencyRef, DependencyTarget, GitHubOperationError, MergeStateStatus,
        Mergeable, PullRequestMerge, PullRequestMergeMethod, PullRequestState, ReviewDecision,
        classify_dependency_write, classify_sub_issue_write, dependency_present, edit_body,
        is_safe_segment, issue_graph_next_link, merge_body, parse_dependency_comments,
        parse_dependency_refs, parse_dependency_target, parse_issue_closure_references,
        parse_pull_request, parse_pull_requests, parse_release_candidate_pull_request,
        parse_review_state, parse_sub_issue_ref, parse_sub_issue_refs, reconcile_create,
        sub_issue_present, target_has_protected_lifecycle_state, target_has_security_content,
        validate_issue_number, validate_repo,
    };
    use super::{DependencyWrite, IssueGraphFeature, PullRequestEdit, SubIssueWrite};
    use larch_core::GitHubTransportPolicy;
    use serde_json::{Value, json};
    use std::collections::BTreeSet;

    fn limits() -> larch_core::GitHubResponseLimits {
        GitHubTransportPolicy::github_com().limits()
    }

    fn pull_request_value(number: u64, state: &str, head: &str) -> serde_json::Value {
        json!({
            "number": number,
            "state": state,
            "title": "Add typed operations",
            "head": { "ref": head },
            "base": { "ref": "main" },
            "draft": false,
            "merged": false,
        })
    }

    #[test]
    fn pull_request_parses_the_minimal_typed_contract() {
        let parsed = parse_pull_request(&pull_request_value(7, "open", "feature"), limits())
            .expect("valid pull request");
        assert_eq!(parsed.number(), 7);
        assert_eq!(parsed.state(), PullRequestState::Open);
        assert_eq!(parsed.title(), "Add typed operations");
        assert_eq!(parsed.head_ref(), "feature");
        assert_eq!(parsed.base_ref(), "main");
        assert!(!parsed.draft());
        assert!(!parsed.merged());
        assert_eq!(parsed.merge_commit_oid(), None);
    }

    #[test]
    fn pull_request_exposes_only_a_valid_merge_commit_oid() {
        let mut value = pull_request_value(7, "closed", "feature");
        value["merged"] = json!(true);
        value["merge_commit_sha"] = json!("1111111111111111111111111111111111111111");
        let parsed = parse_pull_request(&value, limits()).expect("valid merged pull request");
        assert_eq!(
            parsed.merge_commit_oid(),
            Some("1111111111111111111111111111111111111111")
        );

        value["merge_commit_sha"] = json!("not-an-oid");
        assert_eq!(
            parse_pull_request(&value, limits()),
            Err(GitHubOperationError::Malformed(
                "pull request merge commit oid"
            ))
        );
    }

    #[test]
    fn release_candidate_requires_exact_identities_and_tracks_merge_state() {
        let value = json!({
            "state": "closed",
            "merged": true,
            "head": {"sha": "1111111111111111111111111111111111111111"},
            "merge_commit_sha": "2222222222222222222222222222222222222222"
        });
        let parsed = parse_release_candidate_pull_request(&value).expect("candidate");
        assert_eq!(
            parsed.state,
            super::ReleaseCandidatePullRequestState::Merged
        );
        assert_eq!(parsed.head_oid.len(), 40);
        assert_eq!(
            parsed.merge_commit_oid.as_deref(),
            Some("2222222222222222222222222222222222222222")
        );
        assert_eq!(
            parse_release_candidate_pull_request(&json!({
                "state": "open", "head": {"sha": "short"}
            })),
            Err(GitHubOperationError::Malformed(
                "release pull request head oid"
            ))
        );
        assert_eq!(
            parse_release_candidate_pull_request(&json!({
                "state": "closed",
                "merged": true,
                "head": {"sha": "1111111111111111111111111111111111111111"},
                "merge_commit_sha": "not-an-oid"
            })),
            Err(GitHubOperationError::Malformed(
                "release pull request merge commit oid"
            ))
        );
    }

    #[test]
    fn pull_request_rejects_missing_and_malformed_fields() {
        assert_eq!(
            parse_pull_request(&json!({ "state": "open" }), limits())
                .expect_err("missing number must fail"),
            GitHubOperationError::Malformed("pull request number")
        );
        assert_eq!(
            parse_pull_request(&pull_request_value(1, "merging", "x"), limits())
                .expect_err("unknown state must fail"),
            GitHubOperationError::Malformed("pull request state")
        );
        assert_eq!(
            parse_pull_request(&json!([]), limits()).expect_err("non-object must fail"),
            GitHubOperationError::Malformed("expected a JSON object")
        );
    }

    #[test]
    fn pull_request_list_is_bounded_and_typed() {
        let value = json!([
            pull_request_value(1, "open", "a"),
            pull_request_value(2, "open", "b"),
        ]);
        let parsed = parse_pull_requests(&value, limits()).expect("valid list");
        assert_eq!(parsed.len(), 2);
        assert_eq!(
            parse_pull_requests(&json!({}), limits()).expect_err("non-array must fail"),
            GitHubOperationError::Malformed("pull request list")
        );
    }

    #[test]
    fn create_reconciliation_adopts_an_open_head_branch_pull_request() {
        let existing = vec![
            parse_pull_request(&pull_request_value(3, "closed", "feature"), limits()).unwrap(),
            parse_pull_request(&pull_request_value(9, "open", "feature"), limits()).unwrap(),
        ];
        assert!(matches!(
            reconcile_create(&existing, "feature"),
            CreatePlan::ReturnExisting(9)
        ));
        assert!(matches!(
            reconcile_create(&existing, "other"),
            CreatePlan::Create
        ));
        assert!(matches!(
            reconcile_create(&[], "feature"),
            CreatePlan::Create
        ));
    }

    #[test]
    fn review_state_parses_all_merge_and_review_fields() {
        let value = json!({
            "data": { "repository": { "pullRequest": {
                "reviewDecision": "APPROVED",
                "mergeStateStatus": "CLEAN",
                "mergeable": "MERGEABLE",
            }}}
        });
        let parsed = parse_review_state(&value).expect("valid review state");
        assert_eq!(parsed.review_decision(), Some(ReviewDecision::Approved));
        assert_eq!(parsed.merge_state_status(), MergeStateStatus::Clean);
        assert_eq!(parsed.mergeable(), Mergeable::Mergeable);
    }

    #[test]
    fn review_state_allows_null_review_decision() {
        let value = json!({
            "data": { "repository": { "pullRequest": {
                "reviewDecision": null,
                "mergeStateStatus": "BEHIND",
                "mergeable": "UNKNOWN",
            }}}
        });
        let parsed = parse_review_state(&value).expect("null review decision is valid");
        assert_eq!(parsed.review_decision(), None);
        assert_eq!(parsed.merge_state_status(), MergeStateStatus::Behind);
        assert_eq!(parsed.mergeable(), Mergeable::Unknown);
    }

    #[test]
    fn review_state_fails_closed_on_errors_including_partial_data() {
        let errors_only = json!({ "errors": [{ "message": "denied" }] });
        assert_eq!(
            parse_review_state(&errors_only).expect_err("errors must fail closed"),
            GitHubOperationError::GraphqlErrors
        );
        let partial = json!({
            "data": { "repository": { "pullRequest": {
                "reviewDecision": "APPROVED",
                "mergeStateStatus": "CLEAN",
                "mergeable": "MERGEABLE",
            }}},
            "errors": [{ "message": "partial" }],
        });
        assert_eq!(
            parse_review_state(&partial).expect_err("partial data must fail closed"),
            GitHubOperationError::GraphqlErrors
        );
    }

    #[test]
    fn review_state_rejects_missing_node_and_unknown_enum() {
        assert_eq!(
            parse_review_state(&json!({ "data": { "repository": { "pullRequest": null } } }))
                .expect_err("missing node must fail"),
            GitHubOperationError::Malformed("graphql pullRequest")
        );
        let unknown = json!({
            "data": { "repository": { "pullRequest": {
                "mergeStateStatus": "FUTURE",
                "mergeable": "MERGEABLE",
            }}}
        });
        assert_eq!(
            parse_review_state(&unknown).expect_err("unknown enum must fail"),
            GitHubOperationError::Malformed("mergeStateStatus")
        );
    }

    #[test]
    fn issue_closure_references_keep_requested_rows_and_fail_closed() {
        let wanted = BTreeSet::from([7, 99]);
        let value = json!({
            "data": { "repository": { "issues": {
                "nodes": [
                    {"number": 7, "closedByPullRequestsReferences": {"nodes": [{"url": "https://github.com/o/r/pull/8"}], "pageInfo": {"hasNextPage": false}}},
                    {"number": 8, "closedByPullRequestsReferences": {"nodes": [], "pageInfo": {"hasNextPage": false}}},
                ],
                "pageInfo": {"hasNextPage": false, "endCursor": null},
            }}}
        });
        let parsed =
            parse_issue_closure_references(&value, &wanted, limits()).expect("closure references");
        assert_eq!(
            parsed.entries.get(&7),
            Some(&vec!["https://github.com/o/r/pull/8".to_owned()])
        );
        assert!(!parsed.entries.contains_key(&8));
        assert!(!parsed.has_next_page);
        assert_eq!(
            parse_issue_closure_references(
                &json!({"errors": [{"message": "denied"}]}),
                &wanted,
                limits()
            )
            .expect_err("GraphQL errors must fail closed"),
            GitHubOperationError::GraphqlErrors
        );
        assert!(
            parse_issue_closure_references(
                &json!({
                    "data": {"repository": {"issues": {
                        "nodes": [{
                            "number": 7,
                            "closedByPullRequestsReferences": {
                                "nodes": [], "pageInfo": {"hasNextPage": true}
                            }
                        }],
                        "pageInfo": {"hasNextPage": false, "endCursor": null}
                    }}}
                }),
                &wanted,
                limits()
            )
            .is_err()
        );
    }

    #[test]
    fn dependency_refs_parse_and_read_back_exactly() {
        let value = json!([
            { "number": 10, "id": 111, "state": "OPEN" },
            { "number": 12, "id": 222, "state": "closed" },
            { "number": 14, "id": 333 },
        ]);
        let refs = parse_dependency_refs(&value, limits()).expect("valid dependency list");
        assert_eq!(refs.len(), 3);
        assert_eq!(
            refs[0],
            DependencyRef {
                issue_number: 10,
                issue_id: 111,
                open: true
            }
        );
        assert!(!refs[1].is_open());
        assert!(!refs[2].is_open(), "a missing state must not read as open");
        assert!(dependency_present(&refs, 222));
        assert!(!dependency_present(&refs, 999));
        assert_eq!(
            parse_dependency_refs(&json!({}), limits()).expect_err("non-array must fail"),
            GitHubOperationError::Malformed("dependency list")
        );
    }

    #[test]
    fn sub_issue_refs_are_bounded_and_fail_closed() {
        let refs = parse_sub_issue_refs(
            &json!([
                { "number": 10, "id": 111, "state": "open" },
                { "number": 12, "id": 222, "state": "closed" },
            ]),
            limits(),
        )
        .expect("valid sub-issue list");
        assert_eq!(refs.len(), 2);
        assert_eq!(refs[0].issue_number(), 10);
        assert_eq!(refs[0].issue_id(), 111);
        assert!(refs[0].is_open());
        assert!(!refs[1].is_open());
        assert!(sub_issue_present(&refs, 222));
        assert_eq!(
            parse_sub_issue_refs(&json!({}), limits()).expect_err("non-array must fail"),
            GitHubOperationError::Malformed("sub-issue list")
        );
        assert_eq!(
            parse_sub_issue_ref(&json!({ "number": 10 }), limits())
                .expect_err("unexpected parent node must fail"),
            GitHubOperationError::Malformed("sub-issue id")
        );
        let too_many = Value::Array(
            (0..=limits().items())
                .map(|number| json!({ "number": number + 1, "id": number + 1 }))
                .collect(),
        );
        assert_eq!(
            parse_sub_issue_refs(&too_many, limits()).expect_err("item bound must fail"),
            GitHubOperationError::Malformed("sub-issue list exceeds item bound")
        );
        assert_eq!(
            validate_issue_number(0, "sub-issue parent number")
                .expect_err("zero issue number must fail"),
            GitHubOperationError::Malformed("sub-issue parent number")
        );
        assert_eq!(classify_sub_issue_write(true, 201), SubIssueWrite::Accepted);
        assert_eq!(
            classify_sub_issue_write(false, 404),
            SubIssueWrite::PreconditionFailed
        );
        assert_eq!(
            classify_sub_issue_write(true, 422),
            SubIssueWrite::PreconditionFailed
        );
        assert_eq!(
            classify_sub_issue_write(true, 429),
            SubIssueWrite::RateLimited
        );
    }

    #[test]
    fn dependency_target_and_pagination_inputs_fail_closed() {
        let target = json!({
            "updated_at": "2026-07-12T10:00:00Z",
            "state": "open",
            "title": "Regular issue",
            "body": "body",
            "labels": [{"name": "bug"}],
        });
        let parsed = parse_dependency_target(&target, limits()).expect("valid target");
        assert_eq!(parsed.updated_at, "2026-07-12T10:00:00Z");
        let offset_target = json!({
            "updated_at": "2026-07-12T10:00:00+00:00",
            "state": "open",
            "title": "Regular issue",
            "body": "body",
            "labels": [{"name": "bug"}],
        });
        let offset = parse_dependency_target(&offset_target, limits()).expect("valid UTC target");
        assert_eq!(offset.updated_at, parsed.updated_at);
        assert!(!target_has_protected_lifecycle_state(&parsed));
        assert!(target_has_protected_lifecycle_state(&DependencyTarget {
            updated_at: String::from("2026-07-12T10:00:00Z"),
            state: String::from("open"),
            title: String::from("[IMPLEMENTING] issue"),
            body: String::new(),
            labels: Vec::new(),
        }));
        assert_eq!(
            parse_dependency_target(&json!({"updated_at": "nope"}), limits())
                .expect_err("malformed target fails closed"),
            GitHubOperationError::Malformed("dependency target updated_at")
        );
        assert_eq!(
            parse_dependency_target(
                &json!({
                    "updated_at": "2026-07-12T11:00:00+01:00",
                    "state": "open",
                    "title": "target",
                }),
                limits(),
            )
            .expect_err("non-UTC target timestamp fails closed"),
            GitHubOperationError::Malformed("dependency target updated_at")
        );

        let mut headers = http::HeaderMap::new();
        headers.insert(
            http::header::LINK,
            http::HeaderValue::from_str(
                "</repos/o/r/issues/5/dependencies/blocked_by?page=2>; rel=\"next\"",
            )
            .expect("valid header"),
        );
        assert_eq!(
            issue_graph_next_link(&headers, IssueGraphFeature::Dependency).expect("next link"),
            Some(String::from(
                "/repos/o/r/issues/5/dependencies/blocked_by?page=2"
            ))
        );
        headers.insert(
            http::header::LINK,
            http::HeaderValue::from_static("bad; rel=next"),
        );
        assert!(issue_graph_next_link(&headers, IssueGraphFeature::Dependency).is_err());
    }

    #[test]
    fn dependency_security_content_matches_python_triage_contract() {
        let mut target = DependencyTarget {
            updated_at: String::from("2026-07-12T10:00:00Z"),
            state: String::from("open"),
            title: String::from("Regular issue"),
            body: String::new(),
            labels: Vec::new(),
        };
        assert!(!target_has_security_content(&target, &[]));
        assert!(target_has_security_content(
            &target,
            &[String::from("Possible authentication bypass")]
        ));
        target.title = String::from("Credential exposure");
        assert!(target_has_security_content(&target, &[]));
        target.title = String::from("Regular issue");
        target.body = String::from("Possible remote code execution");
        assert!(target_has_security_content(&target, &[]));
        target.body.clear();
        target.labels.push(String::from("VULNERABILITY"));
        assert!(target_has_security_content(&target, &[]));
        assert_eq!(
            parse_dependency_comments(&json!([{"body": null}, {"body": "safe"}]), limits())
                .expect("valid comments"),
            [String::new(), String::from("safe")]
        );
        assert_eq!(
            parse_dependency_comments(&json!([{"body": 7}]), limits())
                .expect_err("malformed body fails closed"),
            GitHubOperationError::Malformed("dependency comment body")
        );
        let too_many = Value::Array(
            (0..=limits().items())
                .map(|_| json!({"body": "safe"}))
                .collect(),
        );
        assert_eq!(
            parse_dependency_comments(&too_many, limits())
                .expect_err("aggregate item limit fails closed"),
            GitHubOperationError::Malformed("dependency comments exceed item bound")
        );
    }

    #[test]
    fn dependency_write_classification_covers_the_status_contract() {
        assert_eq!(classify_dependency_write(201), DependencyWrite::Accepted);
        assert_eq!(classify_dependency_write(204), DependencyWrite::Accepted);
        assert_eq!(
            classify_dependency_write(404),
            DependencyWrite::FeatureUnavailable
        );
        assert_eq!(classify_dependency_write(422), DependencyWrite::Duplicate);
        assert_eq!(
            classify_dependency_write(403),
            DependencyWrite::Unauthorized
        );
        assert_eq!(classify_dependency_write(500), DependencyWrite::Failed);
    }

    #[test]
    fn repository_segments_reject_traversal_and_injection() {
        validate_repo("character-ai", "larch").expect("safe segments pass");
        assert!(is_safe_segment("owner_1.name-2"));
        for bad in ["", "../etc", "a/b", "a b", "spÃ©cial"] {
            assert!(!is_safe_segment(bad), "segment {bad} must be rejected");
        }
        assert_eq!(
            validate_repo("ok", "../escape").expect_err("traversal must fail"),
            GitHubOperationError::Malformed("repository owner or name")
        );
    }

    #[test]
    fn edit_body_only_includes_set_fields() {
        let edit = PullRequestEdit {
            owner: "character-ai",
            repo: "larch",
            number: 5,
            title: Some("New title"),
            body: None,
            state: Some(PullRequestState::Closed),
            base: None,
        };
        assert_eq!(
            edit_body(&edit),
            json!({ "title": "New title", "state": "closed" })
        );
    }

    #[test]
    fn merge_body_has_only_typed_supported_fields() {
        let request = PullRequestMerge {
            owner: "character-ai",
            repo: "larch",
            number: 5,
            expected_head_oid: "1111111111111111111111111111111111111111",
            method: PullRequestMergeMethod::Squash,
            commit_title: Some("Merge title"),
            commit_message: None,
        };
        assert_eq!(
            merge_body(&request),
            json!({
                "sha": "1111111111111111111111111111111111111111",
                "merge_method": "squash",
                "commit_title": "Merge title",
            })
        );
    }
}

#[cfg(test)]
mod service_tests {
    use super::{
        AuditRunsService, DependencyEdge, DependencyMutation, DependencyMutationReceipt,
        DependencyRef, GitHubOperationError, LiveMutationRequest, MergeStateStatus, Mergeable,
        OctocrabGitHubService, PullRequestEdit, PullRequestMerge, PullRequestMergeMethod,
        PullRequestMergeResult, PullRequestSpec, PullRequestState, ReleasePlanningService,
        ReviewDecision, SubIssueEdge, SubIssueMutation, SubIssueMutationReceipt,
    };
    use crate::runtime::Cancellation;
    use larch_test_support::{HttpResponseBuilder, IssueServiceExchange, IssueServiceStub};
    use serde_json::json;
    use std::collections::BTreeSet;

    fn stub_service(responses: Vec<(u16, String)>) -> (OctocrabGitHubService, IssueServiceStub) {
        let exchanges = responses.into_iter().map(|(status, body)| {
            IssueServiceExchange::any_json(status, body).expect("valid stub response")
        });
        service_with_stub(IssueServiceStub::start(exchanges).expect("start stub"))
    }

    fn stub_service_with_links(
        responses: Vec<(u16, String, Option<String>)>,
    ) -> (OctocrabGitHubService, IssueServiceStub) {
        let exchanges = responses.into_iter().map(|(status, body, link)| {
            let response = HttpResponseBuilder::new(status)
                .header("content-type", "application/json")
                .expect("content type");
            let response = match link {
                Some(link) => response.header("link", &link).expect("link header"),
                None => response,
            }
            .body(body)
            .build()
            .expect("valid stub response");
            IssueServiceExchange::any(response)
        });
        service_with_stub(IssueServiceStub::start(exchanges).expect("start stub"))
    }

    fn service_with_stub(server: IssueServiceStub) -> (OctocrabGitHubService, IssueServiceStub) {
        let base = server.base_url().to_owned();
        let client = octocrab::Octocrab::builder()
            .personal_token(String::from("test-token"))
            .base_uri(&base)
            .expect("base URI")
            .upload_uri(&base)
            .expect("upload URI")
            .build()
            .expect("stub client");
        (
            OctocrabGitHubService::with_test_client(client).with_test_continuation_base(&base),
            server,
        )
    }

    fn sub_issue_edge() -> SubIssueEdge<'static> {
        SubIssueEdge {
            owner: "o",
            repo: "r",
            parent_issue: 5,
            sub_issue_id: 222,
        }
    }

    fn sub_issue_json(number: u64, id: u64) -> String {
        json!({ "number": number, "id": id, "state": "open" }).to_string()
    }

    fn pull_request_json(number: u64, state: &str, head: &str) -> String {
        json!({
            "number": number,
            "state": state,
            "title": "Typed operations",
            "head": { "ref": head },
            "base": { "ref": "main" },
            "draft": false,
            "merged": false,
        })
        .to_string()
    }

    const HEAD: &str = "1111111111111111111111111111111111111111";
    const OTHER_HEAD: &str = "2222222222222222222222222222222222222222";
    const MERGE_COMMIT: &str = "3333333333333333333333333333333333333333";

    fn merge_candidate_json(state: &str, merged: bool, head: &str) -> String {
        json!({
            "state": state,
            "merged": merged,
            "head": { "sha": head },
        })
        .to_string()
    }

    fn merge_review_state_json(status: &str, mergeable: &str) -> String {
        json!({
            "data": { "repository": { "pullRequest": {
                "reviewDecision": null,
                "mergeStateStatus": status,
                "mergeable": mergeable,
            }}}
        })
        .to_string()
    }

    fn merge_request() -> PullRequestMerge<'static> {
        PullRequestMerge {
            owner: "o",
            repo: "r",
            number: 7,
            expected_head_oid: HEAD,
            method: PullRequestMergeMethod::Squash,
            commit_title: Some("Merge typed operation"),
            commit_message: None,
        }
    }

    fn release_pull_request_value(number: u64, title: &str) -> serde_json::Value {
        json!({
            "number": number,
            "title": title,
            "labels": [{ "name": "release-note" }],
            "user": { "login": "author" },
            "html_url": format!("https://github.com/o/r/pull/{number}"),
            "head": { "ref": format!("feature-{number}") },
        })
    }

    fn audit_pull_request_value(
        number: u64,
        title: &str,
        body: &str,
        base: &str,
        merged_at: Option<&str>,
    ) -> serde_json::Value {
        json!({
            "number": number,
            "title": title,
            "body": body,
            "base": { "ref": base },
            "merged_at": merged_at,
        })
    }

    fn spec(head: &str) -> PullRequestSpec<'_> {
        PullRequestSpec {
            owner: "character-ai",
            repo: "larch",
            head,
            base: "main",
            title: "Typed operations",
            body: "Body",
            draft: false,
        }
    }

    fn operator_request() -> LiveMutationRequest<'static> {
        LiveMutationRequest {
            context_file: None,
            operator_mode: true,
            run_id: "",
            trusted_root: None,
            test_deny: false,
        }
    }

    fn denied_request() -> LiveMutationRequest<'static> {
        LiveMutationRequest {
            context_file: None,
            operator_mode: false,
            run_id: "",
            trusted_root: None,
            test_deny: false,
        }
    }

    #[tokio::test]
    async fn get_pull_request_reads_the_typed_contract() {
        let (service, server) = stub_service(vec![(200, pull_request_json(7, "open", "feature"))]);
        let cancellation = Cancellation::new();
        let pull_request = service
            .get_pull_request(&cancellation, "character-ai", "larch", 7)
            .await
            .expect("valid pull request");
        assert_eq!(pull_request.number(), 7);
        assert_eq!(pull_request.state(), PullRequestState::Open);
        assert_eq!(pull_request.head_ref(), "feature");
        assert_eq!(pull_request.base_ref(), "main");
        assert!(!pull_request.draft());
        assert!(!pull_request.merged());
        server.join().expect("stub completed");
    }

    #[tokio::test]
    async fn read_maps_unauthorized_transport_and_cancellation() {
        let cancellation = Cancellation::new();
        let (unauthorized, server) =
            stub_service(vec![(401, json!({ "message": "no" }).to_string())]);
        assert_eq!(
            unauthorized
                .get_pull_request(&cancellation, "o", "r", 1)
                .await
                .expect_err("401 maps to Unauthorized"),
            GitHubOperationError::Unauthorized
        );
        server.join().expect("stub completed");

        let (transport, server) =
            stub_service(vec![(500, json!({ "message": "boom" }).to_string())]);
        assert!(matches!(
            transport
                .get_pull_request(&cancellation, "o", "r", 1)
                .await
                .expect_err("500 maps to Transport"),
            GitHubOperationError::Transport(_)
        ));
        server.join().expect("stub completed");

        let (idle, server) = stub_service(vec![]);
        let cancelled = Cancellation::new();
        cancelled.cancel();
        assert_eq!(
            idle.get_pull_request(&cancelled, "o", "r", 1)
                .await
                .expect_err("cancellation short-circuits"),
            GitHubOperationError::Cancelled
        );
        server.join().expect("stub completed");
    }

    #[tokio::test]
    async fn list_open_pull_requests_reads_a_bounded_array() {
        let first = pull_request_json(1, "open", "a");
        let second = pull_request_json(2, "open", "b");
        let (service, server) = stub_service(vec![(200, format!("[{first},{second}]"))]);
        let cancellation = Cancellation::new();
        let list = service
            .list_open_pull_requests(&cancellation, "o", "r", "a")
            .await
            .expect("valid list");
        assert_eq!(list.len(), 2);
        server.join().expect("stub completed");
    }

    #[tokio::test]
    async fn audit_runs_service_reads_and_filters_typed_pull_requests() {
        let direct = audit_pull_request_value(
            7,
            "chore(larch-logs): design run ABCDEF01-2345-6789-ABCD-EF0123456789",
            "Fixes #42",
            "main",
            Some("2026-08-09T12:00:00Z"),
        );
        let (service, server) = stub_service(vec![(200, direct.to_string())]);
        let cancellation = Cancellation::new();
        let pull = AuditRunsService::audit_pull_request(&service, &cancellation, "o", "r", 7)
            .await
            .expect("typed audit pull request");
        assert_eq!(pull.number, 7);
        assert_eq!(pull.body, "Fixes #42");
        server.join().expect("stub completed");

        let listed = json!([
            audit_pull_request_value(3, "newer", "", "main", Some("2026-08-09T13:00:00Z")),
            audit_pull_request_value(2, "other base", "", "release", Some("2026-08-09T11:00:00Z")),
            audit_pull_request_value(1, "older", "", "main", Some("2026-08-09T10:00:00Z")),
            audit_pull_request_value(4, "unmerged", "", "main", None),
        ]);
        let (service, server) = stub_service(vec![(200, listed.to_string())]);
        let pulls = AuditRunsService::list_audit_merged_main_pull_requests(
            &service,
            &Cancellation::new(),
            "o",
            "r",
        )
        .await
        .expect("filtered audit pulls");
        assert_eq!(
            pulls.iter().map(|pull| pull.number).collect::<Vec<_>>(),
            [1, 3]
        );
        let requests = server.requests().expect("request log");
        assert_eq!(requests.len(), 1);
        let query = requests[0]
            .path
            .split_once('?')
            .expect("audit list query")
            .1;
        for parameter in ["state=closed", "base=main", "per_page=100", "page=1"] {
            assert!(
                query.split('&').any(|entry| entry == parameter),
                "audit list must constrain {parameter}: {query}"
            );
        }
        server.join().expect("stub completed");
    }

    #[tokio::test]
    async fn release_pull_requests_paginate_and_redact_note_fields() {
        let first_page = (1..=100)
            .map(|number| release_pull_request_value(number, "Feature"))
            .collect::<Vec<_>>();
        let secret = ["ghp", "_123456789012345678901234567890"].concat();
        let second_page = vec![json!({
            "number": 101,
            "title": &secret,
            "labels": [{ "name": &secret }],
            "user": { "login": &secret },
            "html_url": &secret,
            "head": { "ref": &secret },
        })];
        let (service, server) = stub_service(vec![
            (200, serde_json::to_string(&first_page).unwrap()),
            (200, serde_json::to_string(&second_page).unwrap()),
        ]);

        let pull_requests = service
            .list_release_open_pull_requests(&Cancellation::new(), "o", "r")
            .await
            .expect("paginated pull requests");

        assert_eq!(pull_requests.len(), 101);
        let redacted = &pull_requests[100];
        assert_eq!(redacted.title, "<REDACTED-TOKEN>");
        assert_eq!(redacted.labels, ["<REDACTED-TOKEN>"]);
        assert_eq!(redacted.author, "<REDACTED-TOKEN>");
        assert_eq!(redacted.url, "<REDACTED-TOKEN>");
        assert_eq!(redacted.head_ref, "<REDACTED-TOKEN>");
        server.join().expect("stub completed");
    }

    #[tokio::test]
    async fn release_planning_port_exercises_every_typed_read() {
        let pull = release_pull_request_value(42, "Fixes #7: feature");
        let (service, server) = stub_service(vec![
            (200, json!({ "tag_name": "v1.2.3" }).to_string()),
            (200, json!([pull.clone()]).to_string()),
            (200, pull.to_string()),
            (200, json!([pull]).to_string()),
            (200, json!({ "title": "Companion title" }).to_string()),
        ]);
        let cancellation = Cancellation::new();

        assert_eq!(
            ReleasePlanningService::latest_release_tag(&service, &cancellation, "o", "r")
                .await
                .expect("latest release")
                .as_deref(),
            Some("v1.2.3")
        );
        assert_eq!(
            ReleasePlanningService::list_open_pull_requests(&service, &cancellation, "o", "r",)
                .await
                .expect("open pull requests")
                .len(),
            1
        );
        assert_eq!(
            ReleasePlanningService::pull_request(&service, &cancellation, "o", "r", 42)
                .await
                .expect("pull request")
                .number,
            42
        );
        assert_eq!(
            ReleasePlanningService::commit_pull_requests(
                &service,
                &cancellation,
                "o",
                "r",
                "0123456789abcdef0123456789abcdef01234567",
            )
            .await
            .expect("commit pull requests")
            .len(),
            1
        );
        assert_eq!(
            ReleasePlanningService::issue_title(&service, &cancellation, "o", "r", 7)
                .await
                .expect("issue title"),
            "Companion title"
        );
        server.join().expect("stub completed");
    }

    #[tokio::test]
    async fn create_pull_request_creates_when_no_head_branch_exists() {
        let (service, server) = stub_service(vec![
            (200, String::from("[]")),
            (201, pull_request_json(12, "open", "feature")),
        ]);
        let cancellation = Cancellation::new();
        let spec = spec("feature");
        let created = service
            .create_pull_request(&cancellation, &spec)
            .await
            .expect("created pull request");
        assert!(created.created());
        assert_eq!(created.pull_request().number(), 12);
        server.join().expect("stub completed");
    }

    #[tokio::test]
    async fn create_pull_request_adopts_an_open_head_branch() {
        let existing = pull_request_json(9, "open", "feature");
        let (service, server) = stub_service(vec![
            (200, format!("[{existing}]")),
            (200, pull_request_json(9, "open", "feature")),
        ]);
        let cancellation = Cancellation::new();
        let spec = spec("feature");
        let created = service
            .create_pull_request(&cancellation, &spec)
            .await
            .expect("adopted existing pull request");
        assert!(!created.created());
        assert_eq!(created.pull_request().number(), 9);
        server.join().expect("stub completed");
    }

    #[tokio::test]
    async fn create_pull_request_reconciles_after_a_create_failure() {
        let cancellation = Cancellation::new();
        let spec = spec("feature");
        let existing = pull_request_json(9, "open", "feature");
        let (adopts, server) = stub_service(vec![
            (200, String::from("[]")),
            (422, json!({ "message": "exists" }).to_string()),
            (200, format!("[{existing}]")),
            (200, pull_request_json(9, "open", "feature")),
        ]);
        let created = adopts
            .create_pull_request(&cancellation, &spec)
            .await
            .expect("adopted after create failure");
        assert!(!created.created());
        assert_eq!(created.pull_request().number(), 9);
        server.join().expect("stub completed");

        let (fails, server) = stub_service(vec![
            (200, String::from("[]")),
            (422, json!({ "message": "exists" }).to_string()),
            (200, String::from("[]")),
        ]);
        assert!(matches!(
            fails
                .create_pull_request(&cancellation, &spec)
                .await
                .expect_err("original failure surfaces"),
            GitHubOperationError::Transport(_)
        ));
        server.join().expect("stub completed");
    }

    #[tokio::test]
    async fn edit_pull_request_patches_and_parses() {
        let (service, server) =
            stub_service(vec![(200, pull_request_json(5, "closed", "feature"))]);
        let cancellation = Cancellation::new();
        let edit = PullRequestEdit {
            owner: "character-ai",
            repo: "larch",
            number: 5,
            title: Some("New title"),
            body: None,
            state: Some(PullRequestState::Closed),
            base: None,
        };
        let pull_request = service
            .edit_pull_request(&cancellation, &edit)
            .await
            .expect("edited pull request");
        assert_eq!(pull_request.number(), 5);
        assert_eq!(pull_request.state(), PullRequestState::Closed);
        server.join().expect("stub completed");
    }

    #[tokio::test]
    async fn merge_pull_request_covers_success_stale_and_ambiguous_success() {
        let cancellation = Cancellation::new();
        let authorized = operator_request();

        let (service, server) = stub_service(vec![
            (200, merge_candidate_json("open", false, HEAD)),
            (200, merge_review_state_json("CLEAN", "MERGEABLE")),
            (
                200,
                json!({ "merged": true, "sha": MERGE_COMMIT }).to_string(),
            ),
        ]);
        assert_eq!(
            service
                .merge_pull_request(&cancellation, &authorized, &merge_request())
                .await
                .expect("successful merge"),
            PullRequestMergeResult::Merged {
                merge_commit_oid: MERGE_COMMIT.to_owned(),
            }
        );
        server.join().expect("stub completed");

        let (service, server) =
            stub_service(vec![(200, merge_candidate_json("open", false, OTHER_HEAD))]);
        assert_eq!(
            service
                .merge_pull_request(&cancellation, &authorized, &merge_request())
                .await
                .expect("stale expected head is a typed result"),
            PullRequestMergeResult::HeadChanged
        );
        server.join().expect("stub completed");

        let (service, server) = stub_service(vec![
            (200, merge_candidate_json("open", false, HEAD)),
            (200, merge_review_state_json("CLEAN", "MERGEABLE")),
            (500, json!({ "message": "upstream failure" }).to_string()),
            (200, merge_candidate_json("closed", true, HEAD)),
        ]);
        assert_eq!(
            service
                .merge_pull_request(&cancellation, &authorized, &merge_request())
                .await
                .expect("ambiguous write read-back proves merged state"),
            PullRequestMergeResult::AlreadyMerged
        );
        server.join().expect("stub completed");
    }

    #[tokio::test]
    async fn merge_pull_request_covers_refusal_permission_and_retry_refusal() {
        let cancellation = Cancellation::new();
        let authorized = operator_request();

        let (service, server) = stub_service(vec![
            (200, merge_candidate_json("open", false, HEAD)),
            (200, merge_review_state_json("CLEAN", "MERGEABLE")),
            (422, json!({ "message": "policy" }).to_string()),
        ]);
        assert_eq!(
            service
                .merge_pull_request(&cancellation, &authorized, &merge_request())
                .await
                .expect("validation failure result"),
            PullRequestMergeResult::ValidationFailed
        );
        server.join().expect("stub completed");

        let (service, server) = stub_service(vec![
            (200, merge_candidate_json("open", false, HEAD)),
            (200, merge_review_state_json("CLEAN", "MERGEABLE")),
            (401, json!({ "message": "denied" }).to_string()),
        ]);
        assert_eq!(
            service
                .merge_pull_request(&cancellation, &authorized, &merge_request())
                .await
                .expect_err("permission failure remains distinct"),
            GitHubOperationError::Unauthorized
        );
        server.join().expect("stub completed");

        let (service, server) = stub_service(vec![
            (200, merge_candidate_json("open", false, HEAD)),
            (200, merge_review_state_json("CLEAN", "MERGEABLE")),
            (500, json!({ "message": "uncertain" }).to_string()),
            (200, merge_candidate_json("open", false, HEAD)),
            (200, merge_review_state_json("CLEAN", "MERGEABLE")),
        ]);
        assert_eq!(
            service
                .merge_pull_request(&cancellation, &authorized, &merge_request())
                .await
                .expect_err("reconciliation refuses a second merge submission"),
            GitHubOperationError::AmbiguousMutation
        );
        server.join().expect("stub completed");
    }

    #[tokio::test]
    async fn merge_pull_request_handles_terminal_and_unavailable_states() {
        let cancellation = Cancellation::new();
        let authorized = operator_request();

        let (service, server) =
            stub_service(vec![(200, merge_candidate_json("closed", true, HEAD))]);
        assert_eq!(
            service
                .merge_pull_request(&cancellation, &authorized, &merge_request())
                .await
                .expect("already merged is idempotent"),
            PullRequestMergeResult::AlreadyMerged
        );
        server.join().expect("stub completed");

        let (service, server) =
            stub_service(vec![(200, merge_candidate_json("closed", false, HEAD))]);
        assert_eq!(
            service
                .merge_pull_request(&cancellation, &authorized, &merge_request())
                .await
                .expect("closed pull request is a typed result"),
            PullRequestMergeResult::Closed
        );
        server.join().expect("stub completed");

        let (service, server) = stub_service(vec![
            (200, merge_candidate_json("open", false, HEAD)),
            (200, merge_review_state_json("CLEAN", "MERGEABLE")),
            (405, json!({ "message": "cannot merge" }).to_string()),
        ]);
        assert_eq!(
            service
                .merge_pull_request(&cancellation, &authorized, &merge_request())
                .await
                .expect("unavailable merge reason is typed"),
            PullRequestMergeResult::MergeUnavailable
        );
        server.join().expect("stub completed");
    }

    #[tokio::test]
    async fn merge_pull_request_distinguishes_conflict_policy_and_rate_limit() {
        let cancellation = Cancellation::new();
        let authorized = operator_request();

        let (service, server) = stub_service(vec![
            (200, merge_candidate_json("open", false, HEAD)),
            (200, merge_review_state_json("CLEAN", "CONFLICTING")),
        ]);
        assert_eq!(
            service
                .merge_pull_request(&cancellation, &authorized, &merge_request())
                .await
                .expect("conflict is a typed result"),
            PullRequestMergeResult::MergeConflict
        );
        server.join().expect("stub completed");

        let (service, server) = stub_service(vec![
            (200, merge_candidate_json("open", false, HEAD)),
            (200, merge_review_state_json("BLOCKED", "MERGEABLE")),
        ]);
        assert_eq!(
            service
                .merge_pull_request(&cancellation, &authorized, &merge_request())
                .await
                .expect("branch policy is a typed result"),
            PullRequestMergeResult::BranchProtection
        );
        server.join().expect("stub completed");

        let (service, server) = stub_service(vec![
            (200, merge_candidate_json("open", false, HEAD)),
            (200, merge_review_state_json("CLEAN", "MERGEABLE")),
            (429, json!({ "message": "slow down" }).to_string()),
        ]);
        assert_eq!(
            service
                .merge_pull_request(&cancellation, &authorized, &merge_request())
                .await
                .expect_err("rate limit remains distinct"),
            GitHubOperationError::RateLimited
        );
        server.join().expect("stub completed");
    }

    #[tokio::test]
    async fn merge_pull_request_honors_live_gate_cancellation_and_input_validation() {
        let request = merge_request();
        let (service, server) = stub_service(vec![]);
        assert_eq!(
            service
                .merge_pull_request(&Cancellation::new(), &denied_request(), &request)
                .await
                .expect_err("mutation gate runs before a network read"),
            GitHubOperationError::MutationRefused("unauthorized-mutation")
        );
        server.join().expect("stub completed");

        let (service, server) = stub_service(vec![]);
        let cancelled = Cancellation::new();
        cancelled.cancel();
        assert_eq!(
            service
                .merge_pull_request(&cancelled, &operator_request(), &request)
                .await
                .expect_err("cancellation is typed"),
            GitHubOperationError::Cancelled
        );
        server.join().expect("stub completed");

        let malformed = PullRequestMerge {
            expected_head_oid: "not-an-object-id",
            ..request
        };
        let (service, server) = stub_service(vec![]);
        assert_eq!(
            service
                .merge_pull_request(&Cancellation::new(), &operator_request(), &malformed)
                .await
                .expect_err("malformed expected head is rejected before a network read"),
            GitHubOperationError::Malformed("expected pull request head oid")
        );
        server.join().expect("stub completed");
    }

    #[tokio::test]
    async fn pull_request_review_state_reads_graphql_and_fails_closed() {
        let cancellation = Cancellation::new();
        let ok = json!({
            "data": { "repository": { "pullRequest": {
                "reviewDecision": "APPROVED",
                "mergeStateStatus": "CLEAN",
                "mergeable": "MERGEABLE",
            }}}
        })
        .to_string();
        let (service, server) = stub_service(vec![(200, ok)]);
        let state = service
            .pull_request_review_state(&cancellation, "o", "r", 3)
            .await
            .expect("valid review state");
        assert_eq!(state.review_decision(), Some(ReviewDecision::Approved));
        assert_eq!(state.merge_state_status(), MergeStateStatus::Clean);
        assert_eq!(state.mergeable(), Mergeable::Mergeable);
        server.join().expect("stub completed");

        let errors = json!({ "errors": [{ "message": "denied" }] }).to_string();
        let (failing, server) = stub_service(vec![(200, errors)]);
        assert_eq!(
            failing
                .pull_request_review_state(&cancellation, "o", "r", 3)
                .await
                .expect_err("graphql errors fail closed"),
            GitHubOperationError::GraphqlErrors
        );
        server.join().expect("stub completed");
    }

    #[tokio::test]
    async fn issue_closure_references_rejects_an_unbounded_request_before_network() {
        let (service, server) = stub_service(vec![]);
        let max = u64::try_from(service.policy.limits().items()).expect("item bound fits u64");
        let wanted: BTreeSet<u64> = (1..=max + 1).collect();

        assert_eq!(
            service
                .issue_closure_references(&Cancellation::new(), "o", "r", &wanted)
                .await
                .expect_err("unbounded request must fail before network I/O"),
            GitHubOperationError::Malformed("issue closure-reference request exceeds item bound")
        );
        server.join().expect("stub completed");
    }

    #[tokio::test]
    async fn list_blocked_by_reads_dependency_refs() {
        let body = json!([{ "number": 10, "id": 111 }, { "number": 12, "id": 222 }]).to_string();
        let (service, server) = stub_service(vec![(200, body)]);
        let cancellation = Cancellation::new();
        let refs = service
            .list_blocked_by(&cancellation, "o", "r", 5)
            .await
            .expect("dependency list");
        assert_eq!(refs.len(), 2);
        assert_eq!(refs[0].issue_number(), 10);
        assert_eq!(refs[0].issue_id(), 111);
        server.join().expect("stub completed");
    }

    #[tokio::test]
    async fn list_blocked_by_follows_a_bounded_same_origin_next_link() {
        let (service, server) = stub_service_with_links(vec![
            (
                200,
                json!([{ "number": 10, "id": 111 }]).to_string(),
                Some(String::from(
                    "</repos/o/r/issues/5/dependencies/blocked_by?page=2>; rel=\"next\"",
                )),
            ),
            (200, json!([{ "number": 12, "id": 222 }]).to_string(), None),
        ]);
        let refs = service
            .list_blocked_by(&Cancellation::new(), "o", "r", 5)
            .await
            .expect("later page is included");
        assert_eq!(
            refs.iter().map(DependencyRef::issue_id).collect::<Vec<_>>(),
            [111, 222]
        );
        server.join().expect("stub completed");
    }

    #[tokio::test]
    async fn list_sub_issues_follows_a_bounded_same_origin_next_link() {
        let exchanges = [
            IssueServiceExchange::pagination(
                "GET",
                "/repos/o/r/issues/5/sub_issues",
                200,
                format!("[{}]", sub_issue_json(10, 111)),
                "/repos/o/r/issues/5/sub_issues?page=2",
            )
            .expect("valid first page"),
            IssueServiceExchange::json(
                "GET",
                "/repos/o/r/issues/5/sub_issues?page=2",
                200,
                format!("[{}]", sub_issue_json(12, 222)),
            )
            .expect("valid second page"),
        ];
        let server = IssueServiceStub::start(exchanges).expect("start stub");
        let (service, server) = service_with_stub(server);

        let refs = service
            .list_sub_issues(&Cancellation::new(), "o", "r", 5)
            .await
            .expect("sub-issues include each page");
        assert_eq!(
            refs.iter().map(DependencyRef::issue_id).collect::<Vec<_>>(),
            [111, 222]
        );
        server.join().expect("stub completed");

        let cross_origin = IssueServiceStub::start([IssueServiceExchange::pagination(
            "GET",
            "/repos/o/r/issues/5/sub_issues",
            200,
            format!("[{}]", sub_issue_json(10, 111)),
            "https://example.invalid/repos/o/r/issues/5/sub_issues?page=2",
        )
        .expect("valid hostile link response")])
        .expect("start stub");
        let (service, server) = service_with_stub(cross_origin);
        assert!(matches!(
            service
                .list_sub_issues(&Cancellation::new(), "o", "r", 5)
                .await
                .expect_err("cross-origin continuation must fail closed"),
            GitHubOperationError::Malformed(_)
        ));
        server.join().expect("stub completed");
    }

    #[tokio::test]
    async fn sub_issue_parent_reads_a_typed_parent_or_absence() {
        let server = IssueServiceStub::start([IssueServiceExchange::json(
            "GET",
            "/repos/o/r/issues/12/parent",
            200,
            sub_issue_json(5, 111),
        )
        .expect("valid parent response")])
        .expect("start stub");
        let (service, server) = service_with_stub(server);
        let parent = service
            .parent_issue(&Cancellation::new(), "o", "r", 12)
            .await
            .expect("typed parent");
        assert_eq!(parent.expect("parent is present").issue_number(), 5);
        server.join().expect("stub completed");

        let server = IssueServiceStub::start([IssueServiceExchange::json(
            "GET",
            "/repos/o/r/issues/12/parent",
            404,
            "{}",
        )
        .expect("valid no-parent response")])
        .expect("start stub");
        let (service, server) = service_with_stub(server);
        assert_eq!(
            service
                .parent_issue(&Cancellation::new(), "o", "r", 12)
                .await
                .expect("404 is an absent parent"),
            None
        );
        server.join().expect("stub completed");
    }

    #[tokio::test]
    async fn sub_issue_add_and_remove_are_verified_by_exact_read_back() {
        let add_exchanges = [
            IssueServiceExchange::json("GET", "/repos/o/r/issues/5/sub_issues", 200, "[]")
                .expect("valid pre-read"),
            IssueServiceExchange::json("POST", "/repos/o/r/issues/5/sub_issues", 201, "{}")
                .expect("valid add"),
            IssueServiceExchange::json(
                "GET",
                "/repos/o/r/issues/5/sub_issues",
                200,
                format!("[{}]", sub_issue_json(12, 222)),
            )
            .expect("valid add read-back"),
        ];
        let server = IssueServiceStub::start(add_exchanges).expect("start stub");
        let (service, server) = service_with_stub(server);
        assert_eq!(
            service
                .add_sub_issue(&Cancellation::new(), &operator_request(), sub_issue_edge())
                .await
                .expect("verified add"),
            SubIssueMutationReceipt {
                outcome: SubIssueMutation::Applied,
            }
        );
        let requests = server.finish().expect("stub completed");
        assert_eq!(requests[1].method, "POST");
        assert_eq!(requests[1].path, "/repos/o/r/issues/5/sub_issues");
        assert_eq!(requests[1].body.bytes, br#"{"sub_issue_id":222}"#);

        let remove_exchanges = [
            IssueServiceExchange::json(
                "GET",
                "/repos/o/r/issues/5/sub_issues",
                200,
                format!("[{}]", sub_issue_json(12, 222)),
            )
            .expect("valid remove pre-read"),
            IssueServiceExchange::json("DELETE", "/repos/o/r/issues/5/sub_issue", 200, "{}")
                .expect("valid remove"),
            IssueServiceExchange::json("GET", "/repos/o/r/issues/5/sub_issues", 200, "[]")
                .expect("valid remove read-back"),
        ];
        let server = IssueServiceStub::start(remove_exchanges).expect("start stub");
        let (service, server) = service_with_stub(server);
        assert_eq!(
            service
                .remove_sub_issue(&Cancellation::new(), &operator_request(), sub_issue_edge())
                .await
                .expect("verified removal"),
            SubIssueMutationReceipt {
                outcome: SubIssueMutation::Applied,
            }
        );
        let requests = server.finish().expect("stub completed");
        assert_eq!(requests[1].method, "DELETE");
        assert_eq!(requests[1].path, "/repos/o/r/issues/5/sub_issue");
        assert_eq!(requests[1].body.bytes, br#"{"sub_issue_id":222}"#);
    }

    #[tokio::test]
    async fn sub_issue_mutations_are_idempotent_and_authorization_gated() {
        let present = IssueServiceStub::start([IssueServiceExchange::json(
            "GET",
            "/repos/o/r/issues/5/sub_issues",
            200,
            format!("[{}]", sub_issue_json(12, 222)),
        )
        .expect("valid present relation")])
        .expect("start stub");
        let (service, server) = service_with_stub(present);
        assert_eq!(
            service
                .add_sub_issue(&Cancellation::new(), &operator_request(), sub_issue_edge())
                .await
                .expect("present add is a no-op"),
            SubIssueMutationReceipt {
                outcome: SubIssueMutation::AlreadyInDesiredState,
            }
        );
        server.join().expect("stub completed");

        let absent = IssueServiceStub::start([IssueServiceExchange::json(
            "GET",
            "/repos/o/r/issues/5/sub_issues",
            200,
            "[]",
        )
        .expect("valid absent relation")])
        .expect("start stub");
        let (service, server) = service_with_stub(absent);
        assert_eq!(
            service
                .remove_sub_issue(&Cancellation::new(), &operator_request(), sub_issue_edge())
                .await
                .expect("absent removal is a no-op"),
            SubIssueMutationReceipt {
                outcome: SubIssueMutation::AlreadyInDesiredState,
            }
        );
        server.join().expect("stub completed");

        let denied = IssueServiceStub::start([]).expect("start stub");
        let (service, server) = service_with_stub(denied);
        assert_eq!(
            service
                .add_sub_issue(&Cancellation::new(), &denied_request(), sub_issue_edge())
                .await
                .expect_err("live mutation gate runs before a read"),
            GitHubOperationError::MutationRefused("unauthorized-mutation")
        );
        server.join().expect("stub completed");
    }

    #[tokio::test]
    async fn sub_issue_conflicts_and_uncertain_writes_fail_closed_after_read_back() {
        let conflict_exchanges = [
            IssueServiceExchange::json("GET", "/repos/o/r/issues/5/sub_issues", 200, "[]")
                .expect("valid pre-read"),
            IssueServiceExchange::json("POST", "/repos/o/r/issues/5/sub_issues", 422, "{}")
                .expect("valid conflict"),
            IssueServiceExchange::json("GET", "/repos/o/r/issues/5/sub_issues", 200, "[]")
                .expect("valid conflict read-back"),
        ];
        let server = IssueServiceStub::start(conflict_exchanges).expect("start stub");
        let (service, server) = service_with_stub(server);
        assert_eq!(
            service
                .add_sub_issue(&Cancellation::new(), &operator_request(), sub_issue_edge())
                .await
                .expect_err("unrelated parent conflict must fail closed"),
            GitHubOperationError::SubIssuePreconditionFailed
        );
        server.join().expect("stub completed");

        let reconcile_exchanges = [
            IssueServiceExchange::json("GET", "/repos/o/r/issues/5/sub_issues", 200, "[]")
                .expect("valid pre-read"),
            IssueServiceExchange::disconnect("POST", "/repos/o/r/issues/5/sub_issues"),
            IssueServiceExchange::json(
                "GET",
                "/repos/o/r/issues/5/sub_issues",
                200,
                format!("[{}]", sub_issue_json(12, 222)),
            )
            .expect("valid reconciliation read-back"),
        ];
        let server = IssueServiceStub::start(reconcile_exchanges).expect("start stub");
        let (service, server) = service_with_stub(server);
        assert_eq!(
            service
                .add_sub_issue(&Cancellation::new(), &operator_request(), sub_issue_edge())
                .await
                .expect("read-back proves the disconnected mutation"),
            SubIssueMutationReceipt {
                outcome: SubIssueMutation::Applied,
            }
        );
        server.join().expect("stub completed");
    }

    #[tokio::test]
    async fn sub_issue_reads_keep_cancellation_authorization_and_transport_typed() {
        let unauthorized = IssueServiceStub::start([IssueServiceExchange::json(
            "GET",
            "/repos/o/r/issues/5/sub_issues",
            401,
            "{}",
        )
        .expect("valid unauthorized response")])
        .expect("start stub");
        let (service, server) = service_with_stub(unauthorized);
        assert_eq!(
            service
                .list_sub_issues(&Cancellation::new(), "o", "r", 5)
                .await
                .expect_err("unauthorized read stays typed"),
            GitHubOperationError::Unauthorized
        );
        server.join().expect("stub completed");

        let transport = IssueServiceStub::start([IssueServiceExchange::json(
            "GET",
            "/repos/o/r/issues/5/sub_issues",
            500,
            "{}",
        )
        .expect("valid transport response")])
        .expect("start stub");
        let (service, server) = service_with_stub(transport);
        assert!(matches!(
            service
                .list_sub_issues(&Cancellation::new(), "o", "r", 5)
                .await
                .expect_err("transport failure stays typed"),
            GitHubOperationError::Transport(_)
        ));
        server.join().expect("stub completed");

        let cancelled = Cancellation::new();
        cancelled.cancel();
        let idle = IssueServiceStub::start([]).expect("start stub");
        let (service, server) = service_with_stub(idle);
        assert_eq!(
            service
                .list_sub_issues(&cancelled, "o", "r", 5)
                .await
                .expect_err("cancelled read stays typed"),
            GitHubOperationError::Cancelled
        );
        server.join().expect("stub completed");
    }

    #[tokio::test]
    async fn add_blocked_by_is_idempotent_and_gated() {
        let cancellation = Cancellation::new();
        let edge = DependencyEdge {
            owner: "o",
            repo: "r",
            client_issue: 5,
            blocker_id: 222,
            expected_updated_at: None,
        };

        let (present, server) = stub_service(vec![(
            200,
            json!([{ "number": 12, "id": 222 }]).to_string(),
        )]);
        let authorized = operator_request();
        assert_eq!(
            present
                .add_blocked_by(&cancellation, &authorized, edge)
                .await
                .expect("idempotent add reconciles without mutating"),
            DependencyMutationReceipt {
                outcome: DependencyMutation::AlreadyInDesiredState,
                updated_at: None,
            }
        );
        server.join().expect("stub completed");

        let (refused, server) = stub_service(vec![]);
        let denied = denied_request();
        assert_eq!(
            refused
                .add_blocked_by(&cancellation, &denied, edge)
                .await
                .expect_err("unauthorized request is refused before any read"),
            GitHubOperationError::MutationRefused("unauthorized-mutation")
        );
        server.join().expect("stub completed");
    }

    #[tokio::test]
    async fn triage_controlled_add_rechecks_and_returns_fresh_timestamp() {
        let target = |updated_at: &str| {
            json!({
                "updated_at": updated_at,
                "state": "open",
                "title": "Regular issue",
                "body": "",
                "labels": [],
            })
            .to_string()
        };
        let (service, server) = stub_service(vec![
            (200, target("2026-07-12T10:00:00Z")),
            (200, String::from("[]")),
            (200, String::from("[]")),
            (200, target("2026-07-12T10:00:00Z")),
            (200, String::from("[]")),
            (201, String::from("{}")),
            (200, json!([{ "number": 12, "id": 222 }]).to_string()),
            (200, target("2026-07-12T10:00:01Z")),
        ]);
        let edge = DependencyEdge {
            owner: "o",
            repo: "r",
            client_issue: 5,
            blocker_id: 222,
            expected_updated_at: Some("2026-07-12T10:00:00Z"),
        };
        let receipt = service
            .add_blocked_by(&Cancellation::new(), &operator_request(), edge)
            .await
            .expect("verified triage mutation");
        assert_eq!(receipt.outcome(), DependencyMutation::Applied);
        assert_eq!(receipt.updated_at(), Some("2026-07-12T10:00:01Z"));
        server.join().expect("stub completed");
    }

    #[tokio::test]
    async fn triage_controlled_add_scans_every_comment_page_for_security_content() {
        let target = json!({
            "updated_at": "2026-07-12T10:00:00Z", "state": "open", "title": "Regular",
            "body": "", "labels": [],
        })
        .to_string();
        let (service, server) = stub_service_with_links(vec![
            (200, target, None),
            (
                200,
                json!([{"body": "ordinary discussion"}]).to_string(),
                Some(String::from(
                    "</repos/o/r/issues/5/comments?per_page=100&page=2>; rel=\"next\"",
                )),
            ),
            (
                200,
                json!([{"body": "This exposes an API key"}]).to_string(),
                None,
            ),
        ]);
        let edge = DependencyEdge {
            owner: "o",
            repo: "r",
            client_issue: 5,
            blocker_id: 222,
            expected_updated_at: Some("2026-07-12T10:00:00Z"),
        };
        assert_eq!(
            service
                .add_blocked_by(&Cancellation::new(), &operator_request(), edge)
                .await
                .expect_err("security-sensitive comment prevents write"),
            GitHubOperationError::SecuritySensitiveDependencyTarget
        );
        server.join().expect("stub completed");
    }

    #[tokio::test]
    async fn triage_dependency_mutations_fail_closed_on_untrusted_comment_evidence() {
        let target = json!({
            "updated_at": "2026-07-12T10:00:00Z", "state": "open", "title": "Regular",
            "body": "", "labels": [],
        })
        .to_string();
        let edge = DependencyEdge {
            owner: "o",
            repo: "r",
            client_issue: 5,
            blocker_id: 222,
            expected_updated_at: Some("2026-07-12T10:00:00Z"),
        };

        let (malformed, server) =
            stub_service(vec![(200, target.clone()), (200, String::from("{}"))]);
        assert_eq!(
            malformed
                .add_blocked_by(&Cancellation::new(), &operator_request(), edge)
                .await
                .expect_err("malformed comments prevent mutation"),
            GitHubOperationError::Malformed("dependency comments")
        );
        server.join().expect("stub completed");

        let (unavailable, server) = stub_service(vec![
            (200, target.clone()),
            (404, json!({"message": "missing"}).to_string()),
        ]);
        assert_eq!(
            unavailable
                .add_blocked_by(&Cancellation::new(), &operator_request(), edge)
                .await
                .expect_err("unavailable comments prevent mutation"),
            GitHubOperationError::DependencyFeatureUnavailable
        );
        server.join().expect("stub completed");

        let (cross_origin, server) = stub_service_with_links(vec![
            (200, target, None),
            (
                200,
                json!([{"body": "safe"}]).to_string(),
                Some(String::from(
                    "<https://example.invalid/comments?page=2>; rel=\"next\"",
                )),
            ),
        ]);
        assert_eq!(
            cross_origin
                .add_blocked_by(&Cancellation::new(), &operator_request(), edge)
                .await
                .expect_err("cross-origin comments prevent mutation"),
            GitHubOperationError::Malformed("dependency pagination link")
        );
        server.join().expect("stub completed");
    }

    #[tokio::test]
    async fn triage_controlled_remove_rejects_security_label_before_mutation() {
        let target = json!({
            "updated_at": "2026-07-12T10:00:00Z", "state": "open", "title": "Regular",
            "body": "", "labels": [{"name": "Security"}],
        })
        .to_string();
        let (service, server) = stub_service(vec![(200, target), (200, String::from("[]"))]);
        let edge = DependencyEdge {
            owner: "o",
            repo: "r",
            client_issue: 5,
            blocker_id: 222,
            expected_updated_at: Some("2026-07-12T10:00:00Z"),
        };
        assert_eq!(
            service
                .remove_blocked_by(&Cancellation::new(), &operator_request(), edge)
                .await
                .expect_err("security label prevents remove"),
            GitHubOperationError::SecuritySensitiveDependencyTarget
        );
        server.join().expect("stub completed");
    }

    #[tokio::test]
    async fn triage_controlled_add_refuses_stale_or_protected_target_before_write() {
        let stale = json!({
            "updated_at": "2026-07-12T10:00:01Z", "state": "open", "title": "Regular",
            "body": "", "labels": [],
        })
        .to_string();
        let (service, server) = stub_service(vec![(200, stale)]);
        let edge = DependencyEdge {
            owner: "o",
            repo: "r",
            client_issue: 5,
            blocker_id: 222,
            expected_updated_at: Some("2026-07-12T10:00:00Z"),
        };
        assert_eq!(
            service
                .add_blocked_by(&Cancellation::new(), &operator_request(), edge)
                .await
                .expect_err("stale target prevents write"),
            GitHubOperationError::StaleDependencyTarget
        );
        server.join().expect("stub completed");

        let protected = json!({
            "updated_at": "2026-07-12T10:00:00Z", "state": "open", "title": "[DONE] Regular",
            "body": "", "labels": [],
        })
        .to_string();
        let (service, server) = stub_service(vec![(200, protected)]);
        assert_eq!(
            service
                .add_blocked_by(&Cancellation::new(), &operator_request(), edge)
                .await
                .expect_err("protected target prevents write"),
            GitHubOperationError::ProtectedDependencyTarget
        );
        server.join().expect("stub completed");
    }

    #[tokio::test]
    async fn remove_blocked_by_is_idempotent_when_absent() {
        let cancellation = Cancellation::new();
        let edge = DependencyEdge {
            owner: "o",
            repo: "r",
            client_issue: 5,
            blocker_id: 222,
            expected_updated_at: None,
        };
        let (service, server) = stub_service(vec![(200, String::from("[]"))]);
        let authorized = operator_request();
        assert_eq!(
            service
                .remove_blocked_by(&cancellation, &authorized, edge)
                .await
                .expect("idempotent remove reconciles without mutating"),
            DependencyMutationReceipt {
                outcome: DependencyMutation::AlreadyInDesiredState,
                updated_at: None,
            }
        );
        server.join().expect("stub completed");
    }

    #[test]
    fn operation_error_display_covers_every_variant() {
        let detail = larch_core::RuntimeRedactor::default().safe_text("io failure");
        let variants = [
            GitHubOperationError::Cancelled,
            GitHubOperationError::DeadlineExceeded,
            GitHubOperationError::Unauthorized,
            GitHubOperationError::RateLimited,
            GitHubOperationError::AmbiguousMutation,
            GitHubOperationError::Transport(detail),
            GitHubOperationError::Malformed("pull request state"),
            GitHubOperationError::GraphqlErrors,
            GitHubOperationError::DependencyFeatureUnavailable,
            GitHubOperationError::SubIssueFeatureUnavailable,
            GitHubOperationError::SubIssuePreconditionFailed,
            GitHubOperationError::MutationRefused("unauthorized-mutation"),
            GitHubOperationError::StaleDependencyTarget,
            GitHubOperationError::ProtectedDependencyTarget,
            GitHubOperationError::SecuritySensitiveDependencyTarget,
        ];
        for variant in &variants {
            assert!(!variant.to_string().is_empty());
        }
        assert_eq!(
            GitHubOperationError::Cancelled.to_string(),
            "GitHub operation cancelled"
        );
        assert!(
            GitHubOperationError::Malformed("head ref")
                .to_string()
                .contains("head ref")
        );
        assert!(
            GitHubOperationError::MutationRefused("reason-y")
                .to_string()
                .contains("reason-y")
        );
    }
}
