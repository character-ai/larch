//! Typed pull-request, review, and issue-dependency operations.
//!
//! Each operation deserializes GitHub REST and fixed-document GraphQL responses
//! into the minimal typed DTOs current callers require. The DTOs expose no raw
//! URL or arbitrary GraphQL surface, GraphQL variables are typed, any GraphQL
//! `errors` member fails closed, ambiguous create outcomes reconcile before they
//! could duplicate a pull request, and dependency mutations stay behind the live
//! authorization gate with exact read-back.

use super::{
    GitHubCompletionError, LiveMutationDecision, LiveMutationRequest, OctocrabGitHubService,
    check_live_mutation_auth, octocrab_status,
};
use larch_core::{GitHubResponseLimits, ProcessCancellation, SafeText};
use serde_json::{Map, Value, json};
use std::{error::Error, fmt, future::Future};

const GITHUB_API_BASE: &str = "https://api.github.com/";
const DIAGNOSTIC_LIMIT: usize = 500;
const RELEASE_PAGE_SIZE: usize = 100;

/// Fixed GraphQL document for merge and review state REST does not expose.
const REVIEW_STATE_QUERY: &str = "query($owner:String!,$name:String!,$number:Int!){repository(owner:$owner,name:$name){pullRequest(number:$number){reviewDecision mergeStateStatus mergeable}}}";

/// Why a typed GitHub operation could not return a result.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum GitHubOperationError {
    /// The caller cancelled the operation before it completed.
    Cancelled,
    /// The operation exceeded the fixed overall deadline.
    DeadlineExceeded,
    /// GitHub rejected the request as unauthenticated or forbidden.
    Unauthorized,
    /// A transport or unexpected API failure, redacted and length-bounded.
    Transport(SafeText),
    /// A response did not match the typed contract at the named field.
    Malformed(&'static str),
    /// A GraphQL response carried an `errors` member, so it fails closed.
    GraphqlErrors,
    /// The repository does not expose the issue-dependency API.
    DependencyFeatureUnavailable,
    /// The live-mutation authorization gate refused the request.
    MutationRefused(&'static str),
}

impl fmt::Display for GitHubOperationError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Cancelled => formatter.write_str("GitHub operation cancelled"),
            Self::DeadlineExceeded => formatter.write_str("GitHub operation deadline exceeded"),
            Self::Unauthorized => {
                formatter.write_str("GitHub rejected the request as unauthorized")
            }
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
            Self::MutationRefused(reason) => {
                write!(formatter, "live GitHub mutation refused: {reason}")
            }
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

/// Candidate state and exact head object id used by release staging.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ReleaseCandidatePullRequest {
    pub state: ReleaseCandidatePullRequestState,
    pub head_oid: String,
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

/// One issue-dependency edge as read back from GitHub.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct DependencyRef {
    issue_number: u64,
    issue_id: u64,
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
}

/// Outcome of an idempotent dependency add or remove.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DependencyMutation {
    /// The edge was applied and confirmed by exact read-back.
    Applied,
    /// The edge already matched the desired state; no mutation was needed.
    AlreadyInDesiredState,
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

/// One issue-dependency edge to add or remove.
#[derive(Clone, Copy)]
pub struct DependencyEdge<'a> {
    pub owner: &'a str,
    pub repo: &'a str,
    pub client_issue: u64,
    pub blocker_id: u64,
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

impl OctocrabGitHubService {
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
        let value = self
            .fetch_json(cancellation, self.client.get(route.as_str(), None::<&()>))
            .await?;
        parse_dependency_refs(&value, self.policy.limits())
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
    ) -> Result<DependencyMutation, GitHubOperationError> {
        authorize_mutation(authorization)?;
        validate_repo(edge.owner, edge.repo)?;
        let before = self
            .list_blocked_by(cancellation, edge.owner, edge.repo, edge.client_issue)
            .await?;
        if dependency_present(&before, edge.blocker_id) {
            return Ok(DependencyMutation::AlreadyInDesiredState);
        }
        let uri = format!(
            "{GITHUB_API_BASE}repos/{}/{}/issues/{}/dependencies/blocked_by",
            edge.owner, edge.repo, edge.client_issue,
        );
        let body = json!({ "issue_id": edge.blocker_id });
        let status = self
            .send_status(cancellation, false, &uri, Some(&body))
            .await?;
        self.settle_dependency(cancellation, edge, status, true)
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
    ) -> Result<DependencyMutation, GitHubOperationError> {
        authorize_mutation(authorization)?;
        validate_repo(edge.owner, edge.repo)?;
        let before = self
            .list_blocked_by(cancellation, edge.owner, edge.repo, edge.client_issue)
            .await?;
        if !dependency_present(&before, edge.blocker_id) {
            return Ok(DependencyMutation::AlreadyInDesiredState);
        }
        let uri = format!(
            "{GITHUB_API_BASE}repos/{}/{}/issues/{}/dependencies/blocked_by/{}",
            edge.owner, edge.repo, edge.client_issue, edge.blocker_id,
        );
        let status = self.send_status(cancellation, true, &uri, None).await?;
        self.settle_dependency(cancellation, edge, status, false)
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

    async fn settle_dependency(
        &self,
        cancellation: &dyn ProcessCancellation,
        edge: DependencyEdge<'_>,
        status: u16,
        adding: bool,
    ) -> Result<DependencyMutation, GitHubOperationError> {
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
            Ok(DependencyMutation::Applied)
        } else {
            Err(GitHubOperationError::Malformed(
                "dependency mutation not reflected in read-back",
            ))
        }
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

fn dependency_present(edges: &[DependencyRef], blocker_id: u64) -> bool {
    edges.iter().any(|edge| edge.issue_id == blocker_id)
}

fn parse_pull_request(
    value: &Value,
    limits: GitHubResponseLimits,
) -> Result<PullRequest, GitHubOperationError> {
    let object = as_object(value)?;
    Ok(PullRequest {
        number: required_u64(object, "number", "pull request number")?,
        state: parse_state(required_str(object, "state", limits, "pull request state")?.as_str())?,
        title: optional_str(object, "title", limits, "pull request title")?.unwrap_or_default(),
        head_ref: required_ref(object, "head", limits, "pull request head ref")?,
        base_ref: required_ref(object, "base", limits, "pull request base ref")?,
        draft: optional_bool(object, "draft", "pull request draft")?.unwrap_or(false),
        merged: optional_bool(object, "merged", "pull request merged")?.unwrap_or(false),
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
    Ok(ReleaseCandidatePullRequest {
        state,
        head_oid: head_oid.to_owned(),
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
            Ok(DependencyRef {
                issue_number: required_u64(object, "number", "dependency issue number")?,
                issue_id: required_u64(object, "id", "dependency issue id")?,
            })
        })
        .collect()
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
        CreatePlan, DependencyRef, GitHubOperationError, MergeStateStatus, Mergeable,
        PullRequestState, ReviewDecision, classify_dependency_write, dependency_present, edit_body,
        is_safe_segment, parse_dependency_refs, parse_pull_request, parse_pull_requests,
        parse_release_candidate_pull_request, parse_review_state, reconcile_create, validate_repo,
    };
    use super::{DependencyWrite, PullRequestEdit};
    use larch_core::GitHubTransportPolicy;
    use serde_json::json;

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
    }

    #[test]
    fn release_candidate_requires_exact_head_identity_and_tracks_merge_state() {
        let value = json!({
            "state": "closed",
            "merged": true,
            "head": {"sha": "1111111111111111111111111111111111111111"}
        });
        let parsed = parse_release_candidate_pull_request(&value).expect("candidate");
        assert_eq!(
            parsed.state,
            super::ReleaseCandidatePullRequestState::Merged
        );
        assert_eq!(parsed.head_oid.len(), 40);
        assert_eq!(
            parse_release_candidate_pull_request(&json!({
                "state": "open", "head": {"sha": "short"}
            })),
            Err(GitHubOperationError::Malformed(
                "release pull request head oid"
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
    fn dependency_refs_parse_and_read_back_exactly() {
        let value = json!([
            { "number": 10, "id": 111 },
            { "number": 12, "id": 222 },
        ]);
        let refs = parse_dependency_refs(&value, limits()).expect("valid dependency list");
        assert_eq!(refs.len(), 2);
        assert_eq!(
            refs[0],
            DependencyRef {
                issue_number: 10,
                issue_id: 111
            }
        );
        assert!(dependency_present(&refs, 222));
        assert!(!dependency_present(&refs, 999));
        assert_eq!(
            parse_dependency_refs(&json!({}), limits()).expect_err("non-array must fail"),
            GitHubOperationError::Malformed("dependency list")
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
}

#[cfg(test)]
mod service_tests {
    use super::{
        DependencyEdge, DependencyMutation, GitHubOperationError, LiveMutationRequest,
        MergeStateStatus, Mergeable, OctocrabGitHubService, PullRequestEdit, PullRequestSpec,
        PullRequestState, ReleasePlanningService, ReviewDecision,
    };
    use crate::runtime::Cancellation;
    use serde_json::json;
    use std::{
        io::{Read as _, Write as _},
        net::TcpListener,
        thread,
    };

    fn stub_service(
        responses: Vec<(u16, String)>,
    ) -> (OctocrabGitHubService, thread::JoinHandle<()>) {
        let listener = TcpListener::bind("127.0.0.1:0").expect("bind stub");
        let base = format!("http://{}/", listener.local_addr().expect("stub address"));
        let server = thread::spawn(move || {
            for (status, body) in responses {
                let (mut socket, _) = listener.accept().expect("accept request");
                let mut request = [0_u8; 16_384];
                let bytes_read = socket.read(&mut request).expect("read request");
                assert!(bytes_read > 0, "request must not be empty");
                write!(
                    socket,
                    "HTTP/1.1 {status} Stub\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{body}",
                    body.len()
                )
                .expect("write response");
            }
        });
        let client = octocrab::Octocrab::builder()
            .personal_token(String::from("test-token"))
            .base_uri(&base)
            .expect("base URI")
            .upload_uri(&base)
            .expect("upload URI")
            .build()
            .expect("stub client");
        (OctocrabGitHubService::with_test_client(client), server)
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
    async fn add_blocked_by_is_idempotent_and_gated() {
        let cancellation = Cancellation::new();
        let edge = DependencyEdge {
            owner: "o",
            repo: "r",
            client_issue: 5,
            blocker_id: 222,
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
            DependencyMutation::AlreadyInDesiredState
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
    async fn remove_blocked_by_is_idempotent_when_absent() {
        let cancellation = Cancellation::new();
        let edge = DependencyEdge {
            owner: "o",
            repo: "r",
            client_issue: 5,
            blocker_id: 222,
        };
        let (service, server) = stub_service(vec![(200, String::from("[]"))]);
        let authorized = operator_request();
        assert_eq!(
            service
                .remove_blocked_by(&cancellation, &authorized, edge)
                .await
                .expect("idempotent remove reconciles without mutating"),
            DependencyMutation::AlreadyInDesiredState
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
            GitHubOperationError::Transport(detail),
            GitHubOperationError::Malformed("pull request state"),
            GitHubOperationError::GraphqlErrors,
            GitHubOperationError::DependencyFeatureUnavailable,
            GitHubOperationError::MutationRefused("unauthorized-mutation"),
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
