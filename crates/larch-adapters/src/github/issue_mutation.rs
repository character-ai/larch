//! The sole Rust owner for freshness-checked GitHub issue field mutations.
//!
//! This adapter uses the GitHub runtime's shared mutation lock, checks the
//! existing live-mutation authorization gate before any GitHub read, and
//! delegates request shape, redaction, protected-body checks, and read-back
//! proof to `larch_core::issue_mutation`.

use larch_core::{
    CreatedIssue, GitHubCloseReason, GitHubComment, GitHubIssue, GitHubIssueCreate,
    GitHubIssueEdit, GitHubIssueState, GitHubOperationError, GitHubRepositoryRef, GitHubService,
    IssueCreateRequest, IssueMutationError, IssueMutationField, IssueMutationRequest,
    IssueMutationSnapshot, ProcessCancellation, VerifiedIssueMutation, mutation_postcondition,
    mutation_would_change, redact_issue_create_request, redact_issue_mutation_request,
    redact_issue_text_outbound, same_mutation_identity, snapshot_is_strictly_newer,
    validate_issue_mutation_request, verify_authorized_body_change, verify_created_issue,
};

use super::{
    LiveMutationDecision, LiveMutationRequest, OctocrabGitHubService, check_live_mutation_auth,
};

/// Authenticated owner for every Rust title, body, and label issue mutation.
pub struct IssueMutationOwner<'service> {
    service: &'service OctocrabGitHubService,
}

/// Why one issue creation failed, and whether it left an issue behind.
///
/// `orphan` is set only when GitHub created an issue whose echo the owner
/// could not accept. The caller closes it and says so, rather than leaving a
/// half-filed issue no counter accounts for.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct IssueCreateFailure {
    pub error: IssueMutationError,
    pub orphan: Option<u64>,
    pub detail: String,
}

impl IssueCreateFailure {
    const fn without_orphan(error: IssueMutationError) -> Self {
        Self {
            error,
            orphan: None,
            detail: String::new(),
        }
    }

    fn with_detail(mut self, detail: String) -> Self {
        self.detail = detail;
        self
    }

    /// Render the failure as the one diagnostic line a caller publishes.
    #[must_use]
    pub fn message(&self) -> String {
        if self.detail.is_empty() {
            self.error.reason().to_owned()
        } else {
            format!("{}: {}", self.error.reason(), self.detail)
        }
    }
}

impl<'service> IssueMutationOwner<'service> {
    /// Bind the owner to the shared GitHub runtime for one execution context.
    #[must_use]
    pub const fn new(service: &'service OctocrabGitHubService) -> Self {
        Self { service }
    }

    /// Read one canonical issue snapshot for a later freshness-checked request.
    ///
    /// # Errors
    ///
    /// Returns `read-failed` or `invalid-read-back` when GitHub cannot provide
    /// the exact requested issue with a usable timestamp and lifecycle state.
    pub async fn read_snapshot(
        &self,
        repository: &GitHubRepositoryRef,
        issue: u64,
        cancellation: &dyn ProcessCancellation,
    ) -> Result<IssueMutationSnapshot, IssueMutationError> {
        if issue == 0 {
            return Err(IssueMutationError::new("invalid-identity"));
        }
        let response = self
            .service
            .issue(repository, issue, cancellation)
            .await
            .map_err(|error| mutation_error_for("read-failed", &error))?;
        snapshot_from_issue(repository, issue, response)
    }

    /// Create one issue, redacting every outbound string before the request
    /// and assigning it to the authenticated GitHub user when requested.
    ///
    /// Authorization is checked before GitHub is contacted at all, so an
    /// unauthorized caller never reaches the network. A usable response
    /// identity is followed by an exact issue GET; a create whose response or
    /// read-back cannot be proven leaves an orphan the caller is told to close.
    ///
    /// # Errors
    ///
    /// Returns `unauthorized-mutation`, `redaction-failed`,
    /// `assignee-read-failed`, `create-failed`, or `invalid-read-back` inside
    /// an [`IssueCreateFailure`] that names the orphan issue when one exists.
    pub async fn create(
        &self,
        cancellation: &dyn ProcessCancellation,
        authorization: &LiveMutationRequest<'_>,
        request: &IssueCreateRequest,
    ) -> Result<CreatedIssue, IssueCreateFailure> {
        authorize(authorization).map_err(IssueCreateFailure::without_orphan)?;
        let redacted =
            redact_issue_create_request(request).map_err(IssueCreateFailure::without_orphan)?;
        let assignees = if redacted.assign_authenticated_user {
            let authenticated_user = self
                .service
                .authenticated_user(cancellation)
                .await
                .map_err(|error| {
                    IssueCreateFailure::without_orphan(IssueMutationError::new(
                        "assignee-read-failed",
                    ))
                    .with_detail(error.to_string())
                })?;
            vec![authenticated_user.login]
        } else {
            Vec::new()
        };
        let create = GitHubIssueCreate {
            repo: redacted.repository,
            title: redacted.title,
            body: redacted.body,
            assignees,
            labels: redacted.labels,
        };
        let _mutation = self.service.mutation_lock.lock().await;
        let created = self
            .service
            .create_issue(&create, cancellation)
            .await
            .map_err(|error| {
                IssueCreateFailure::without_orphan(IssueMutationError::new("create-failed"))
                    .with_detail(error.to_string())
            })?;
        let echoed = verify_created_issue(&created).map_err(|error| IssueCreateFailure {
            error,
            orphan: (created.number != 0).then_some(created.number),
            detail: String::new(),
        })?;
        if !issue_url_matches(&echoed.url, &create.repo, echoed.number) {
            return Err(IssueCreateFailure {
                error: IssueMutationError::new("invalid-read-back"),
                orphan: Some(echoed.number),
                detail: String::new(),
            });
        }
        let read_back = self
            .service
            .issue(&create.repo, echoed.number, cancellation)
            .await
            .map_err(|_| IssueCreateFailure {
                error: IssueMutationError::new("invalid-read-back"),
                orphan: Some(echoed.number),
                detail: String::new(),
            })?;
        verify_created_read_back(&create, &echoed, &read_back).map_err(|error| IssueCreateFailure {
            error,
            orphan: Some(echoed.number),
            detail: String::new(),
        })
    }

    /// Publish one comment and prove the exact redacted body by a list read-back.
    ///
    /// # Errors
    ///
    /// Returns a stable mutation reason when authorization, identity,
    /// redaction, publication, or the response and list identities cannot be proven.
    pub async fn create_comment(
        &self,
        cancellation: &dyn ProcessCancellation,
        authorization: &LiveMutationRequest<'_>,
        repository: &GitHubRepositoryRef,
        issue: u64,
        body: &str,
    ) -> Result<GitHubComment, IssueMutationError> {
        authorize(authorization)?;
        if issue == 0 {
            return Err(IssueMutationError::new("invalid-identity"));
        }
        let redacted = redact_issue_text_outbound(body)?;
        let _mutation = self.service.mutation_lock.lock().await;
        let written = self
            .service
            .create_comment(repository, issue, &redacted, cancellation)
            .await
            .map_err(|_| IssueMutationError::new("comment-write-failed"))?;
        let echoed = verify_comment_read_back(written, &redacted, repository, issue, None)?;
        self.read_comment_back(cancellation, repository, issue, echoed.id, &redacted)
            .await
    }

    /// Replace one comment and prove its identity and exact redacted body from
    /// the mutation response and a subsequent list read-back.
    ///
    /// # Errors
    ///
    /// Returns a stable mutation reason when authorization, identity,
    /// redaction, publication, or the response and list identities cannot be proven.
    pub async fn edit_comment(
        &self,
        cancellation: &dyn ProcessCancellation,
        authorization: &LiveMutationRequest<'_>,
        repository: &GitHubRepositoryRef,
        issue: u64,
        comment_id: u64,
        body: &str,
    ) -> Result<GitHubComment, IssueMutationError> {
        authorize(authorization)?;
        if issue == 0 || comment_id == 0 {
            return Err(IssueMutationError::new("invalid-identity"));
        }
        let redacted = redact_issue_text_outbound(body)?;
        let _mutation = self.service.mutation_lock.lock().await;
        let written = self
            .service
            .edit_comment(repository, comment_id, &redacted, cancellation)
            .await
            .map_err(|_| IssueMutationError::new("comment-write-failed"))?;
        let _echoed =
            verify_comment_read_back(written, &redacted, repository, issue, Some(comment_id))?;
        self.read_comment_back(cancellation, repository, issue, comment_id, &redacted)
            .await
    }

    /// Delete one comment and prove it is absent from the issue comment list.
    ///
    /// # Errors
    ///
    /// Returns a stable mutation reason when authorization, identity, deletion,
    /// or the absence read-back cannot be proven.
    pub async fn delete_comment(
        &self,
        cancellation: &dyn ProcessCancellation,
        authorization: &LiveMutationRequest<'_>,
        repository: &GitHubRepositoryRef,
        issue: u64,
        comment_id: u64,
    ) -> Result<(), IssueMutationError> {
        authorize(authorization)?;
        if issue == 0 || comment_id == 0 {
            return Err(IssueMutationError::new("invalid-identity"));
        }
        let _mutation = self.service.mutation_lock.lock().await;
        self.service
            .delete_comment(repository, comment_id, cancellation)
            .await
            .map_err(|_| IssueMutationError::new("comment-delete-failed"))?;
        let comments = self
            .service
            .list_comments(repository, issue, cancellation)
            .await
            .map_err(|_| IssueMutationError::new("comment-read-back-failed"))?;
        if comments.iter().any(|comment| comment.id == comment_id) {
            Err(IssueMutationError::new("comment-read-back-failed"))
        } else {
            Ok(())
        }
    }

    async fn read_comment_back(
        &self,
        cancellation: &dyn ProcessCancellation,
        repository: &GitHubRepositoryRef,
        issue: u64,
        comment_id: u64,
        expected_body: &str,
    ) -> Result<GitHubComment, IssueMutationError> {
        let comments = self
            .service
            .list_comments(repository, issue, cancellation)
            .await
            .map_err(|_| IssueMutationError::new("comment-read-back-failed"))?;
        let mut matching = comments
            .into_iter()
            .filter(|comment| comment.id == comment_id);
        let comment = matching
            .next()
            .ok_or_else(|| IssueMutationError::new("comment-read-back-failed"))?;
        if matching.next().is_some() {
            return Err(IssueMutationError::new("comment-read-back-failed"));
        }
        verify_comment_read_back(comment, expected_body, repository, issue, Some(comment_id))
    }

    /// Close one issue as not planned, proving the close by its read-back.
    ///
    /// This carries no live-mutation gate. It is the best-effort orphan
    /// cleanup `/issue` runs after a partially created batch, and its Python
    /// predecessor took no authorization either: the caller has already
    /// created the issue it is now retracting.
    ///
    /// # Errors
    ///
    /// Returns the transport detail when the close fails and
    /// `close-read-back-failed` when GitHub reports the issue still open.
    pub async fn close_not_planned(
        &self,
        cancellation: &dyn ProcessCancellation,
        repository: &GitHubRepositoryRef,
        issue: u64,
    ) -> Result<(), String> {
        let _mutation = self.service.mutation_lock.lock().await;
        let closed = self
            .service
            .close_issue(
                repository,
                issue,
                GitHubCloseReason::NotPlanned,
                cancellation,
            )
            .await
            .map_err(|error| error.to_string())?;
        if closed.state == GitHubIssueState::Closed {
            Ok(())
        } else {
            Err(String::from("close-read-back-failed"))
        }
    }

    /// Publish an optional close note and close one open issue under the shared
    /// live-mutation gate.
    ///
    /// Unlike [`Self::close_not_planned`], this is a user-visible mutation and
    /// therefore checks authorization before it reaches GitHub.  The comment is
    /// written first while holding the runtime mutation lock: a failed comment
    /// leaves the issue open, and a failed close leaves the durable note in
    /// place for an operator to inspect rather than claiming that the close
    /// happened.  GitHub's close response is the required read-back proof.
    ///
    /// # Errors
    ///
    /// Returns a stable mutation reason when authorization, identity,
    /// redaction, the open-state precondition, comment publication, close, or
    /// close read-back cannot be proven.
    pub async fn close_with_comment(
        &self,
        cancellation: &dyn ProcessCancellation,
        authorization: &LiveMutationRequest<'_>,
        repository: &GitHubRepositoryRef,
        issue: u64,
        reason: GitHubCloseReason,
        comment: Option<&str>,
    ) -> Result<GitHubIssue, IssueMutationError> {
        authorize(authorization)?;
        if issue == 0 {
            return Err(IssueMutationError::new("invalid-identity"));
        }
        let redacted_comment = comment.map(redact_issue_text_outbound).transpose()?;
        let _mutation = self.service.mutation_lock.lock().await;
        let before = self.read_snapshot(repository, issue, cancellation).await?;
        if before.state != GitHubIssueState::Open {
            return Err(IssueMutationError::new("close-precondition-failed"));
        }
        if let Some(body) = redacted_comment.as_deref() {
            let written = self
                .service
                .create_comment(repository, issue, body, cancellation)
                .await
                .map_err(|_| IssueMutationError::new("comment-write-failed"))?;
            if written.body != body {
                return Err(IssueMutationError::new("comment-read-back-failed"));
            }
        }
        let closed = self
            .service
            .close_issue(repository, issue, reason, cancellation)
            .await
            .map_err(|_| IssueMutationError::new("close-failed"))?;
        if closed.number != issue || closed.state != GitHubIssueState::Closed {
            return Err(IssueMutationError::new("close-read-back-failed"));
        }
        Ok(closed)
    }

    /// Apply the exact requested fields and prove their postcondition by read-back.
    ///
    /// # Errors
    ///
    /// Refuses before contacting GitHub when live authorization is missing, then
    /// returns a stable protected-mutation reason for stale, invalid, ambiguous,
    /// unredactable, or unverifiable requests.
    pub async fn apply(
        &self,
        cancellation: &dyn ProcessCancellation,
        authorization: &LiveMutationRequest<'_>,
        request: &IssueMutationRequest,
    ) -> Result<VerifiedIssueMutation, IssueMutationError> {
        authorize(authorization)?;
        validate_issue_mutation_request(request)?;
        let _mutation = self.service.mutation_lock.lock().await;
        let before = self
            .read_snapshot(&request.repository, request.issue, cancellation)
            .await?;
        if !same_mutation_identity(&before, request) {
            return Err(IssueMutationError::new("stale-identity"));
        }
        let redacted = redact_issue_mutation_request(request)?;
        let body = verify_authorized_body_change(request, &redacted, &before)?;
        if !mutation_would_change(&before, &redacted, body.as_deref()) {
            return Ok(VerifiedIssueMutation {
                before: before.clone(),
                after: before,
                fields: redacted.fields.clone(),
            });
        }
        if self
            .perform_write(cancellation, &redacted, &before, body.as_deref())
            .await
            .is_err()
        {
            return self
                .reconcile_write(cancellation, &redacted, before, body.as_deref())
                .await;
        }
        let after = self
            .read_snapshot(&redacted.repository, redacted.issue, cancellation)
            .await?;
        verify_read_back(before, after, &redacted, body.as_deref())
    }

    async fn perform_write(
        &self,
        cancellation: &dyn ProcessCancellation,
        request: &IssueMutationRequest,
        before: &IssueMutationSnapshot,
        body: Option<&str>,
    ) -> Result<(), IssueMutationError> {
        let title = request
            .fields
            .contains(&IssueMutationField::Title)
            .then(|| request.title.clone())
            .flatten();
        if title.is_some() || body.is_some() {
            let edit = GitHubIssueEdit {
                repo: request.repository.clone(),
                number: request.issue,
                title,
                body: body.map(str::to_owned),
                labels: None,
                assignees: None,
            };
            self.service
                .edit_issue(&edit, cancellation)
                .await
                .map_err(|error| mutation_error_for("write-failed", &error))?;
        }
        self.update_labels(cancellation, request, before).await
    }

    async fn update_labels(
        &self,
        cancellation: &dyn ProcessCancellation,
        request: &IssueMutationRequest,
        before: &IssueMutationSnapshot,
    ) -> Result<(), IssueMutationError> {
        if !request.fields.contains(&IssueMutationField::Labels) {
            return Ok(());
        }
        let Some(labels) = request.labels.as_ref() else {
            return Err(IssueMutationError::new("invalid-label-request"));
        };
        for label in before.labels.difference(labels) {
            self.service
                .remove_label(&request.repository, request.issue, label, cancellation)
                .await
                .map_err(|_| IssueMutationError::new("write-failed"))?;
        }
        for label in labels.difference(&before.labels) {
            self.service
                .add_label(&request.repository, request.issue, label, cancellation)
                .await
                .map_err(|_| IssueMutationError::new("write-failed"))?;
        }
        Ok(())
    }

    async fn reconcile_write(
        &self,
        cancellation: &dyn ProcessCancellation,
        request: &IssueMutationRequest,
        before: IssueMutationSnapshot,
        body: Option<&str>,
    ) -> Result<VerifiedIssueMutation, IssueMutationError> {
        let after = self
            .read_snapshot(&request.repository, request.issue, cancellation)
            .await?;
        if snapshot_is_strictly_newer(&before, &after)
            && mutation_postcondition(&before, &after, request, body)
        {
            return Ok(VerifiedIssueMutation {
                before,
                after,
                fields: request.fields.clone(),
            });
        }
        Err(IssueMutationError::new("write-failed"))
    }
}

fn authorize(authorization: &LiveMutationRequest<'_>) -> Result<(), IssueMutationError> {
    match check_live_mutation_auth(authorization) {
        LiveMutationDecision::Authorized(_) => Ok(()),
        LiveMutationDecision::Refused(reason) => Err(IssueMutationError::new(reason)),
    }
}

/// Build a mutation refusal that preserves its stable reason token while
/// carrying whether the underlying GitHub failure never reached the server, so
/// an offline-aware caller can retry the network-unreachable class.
const fn mutation_error_for(
    reason: &'static str,
    error: &GitHubOperationError,
) -> IssueMutationError {
    if error.is_unreachable() {
        IssueMutationError::unreachable(reason)
    } else {
        IssueMutationError::new(reason)
    }
}

fn verify_comment_read_back(
    comment: GitHubComment,
    expected_body: &str,
    repository: &GitHubRepositoryRef,
    issue: u64,
    expected_id: Option<u64>,
) -> Result<GitHubComment, IssueMutationError> {
    let identity_ok = comment.id != 0
        && expected_id.is_none_or(|comment_id| comment.id == comment_id)
        && comment_url_matches(&comment.url, repository, issue, comment.id);
    if identity_ok && comment.body == expected_body {
        Ok(comment)
    } else {
        Err(IssueMutationError::new("comment-read-back-failed"))
    }
}

fn verify_created_read_back(
    request: &GitHubIssueCreate,
    echoed: &CreatedIssue,
    issue: &GitHubIssue,
) -> Result<CreatedIssue, IssueMutationError> {
    let verified = verify_created_issue(issue)?;
    let expected_labels = request
        .labels
        .iter()
        .collect::<std::collections::BTreeSet<_>>();
    let actual_labels = issue
        .labels
        .iter()
        .map(|label| &label.name)
        .collect::<std::collections::BTreeSet<_>>();
    let expected_assignees = request
        .assignees
        .iter()
        .collect::<std::collections::BTreeSet<_>>();
    let actual_assignees = issue
        .assignees
        .iter()
        .collect::<std::collections::BTreeSet<_>>();
    if &verified != echoed
        || !issue_url_matches(&verified.url, &request.repo, verified.number)
        || issue.title != request.title
        || issue.body != request.body
        || actual_assignees != expected_assignees
        || actual_labels != expected_labels
        || issue.is_pull_request
    {
        return Err(IssueMutationError::new("invalid-read-back"));
    }
    Ok(verified)
}

fn issue_url_matches(value: &str, repository: &GitHubRepositoryRef, issue: u64) -> bool {
    let Ok(url) = url::Url::parse(value) else {
        return false;
    };
    let Some(segments) = url.path_segments() else {
        return false;
    };
    let segments: Vec<&str> = segments.collect();
    url.scheme() == "https"
        && url.host_str() == Some("github.com")
        && url.port().is_none()
        && url.username().is_empty()
        && url.password().is_none()
        && url.query().is_none()
        && url.fragment().is_none()
        && segments.len() == 4
        && segments[0].eq_ignore_ascii_case(repository.owner())
        && segments[1].eq_ignore_ascii_case(repository.name())
        && segments[2] == "issues"
        && segments[3] == issue.to_string()
}

fn comment_url_matches(
    value: &str,
    repository: &GitHubRepositoryRef,
    issue: u64,
    comment: u64,
) -> bool {
    let Ok(url) = url::Url::parse(value) else {
        return false;
    };
    let Some(segments) = url.path_segments() else {
        return false;
    };
    let segments: Vec<&str> = segments.collect();
    url.scheme() == "https"
        && url.host_str() == Some("github.com")
        && url.port().is_none()
        && url.username().is_empty()
        && url.password().is_none()
        && url.query().is_none()
        && segments.len() == 4
        && segments[0].eq_ignore_ascii_case(repository.owner())
        && segments[1].eq_ignore_ascii_case(repository.name())
        && segments[2] == "issues"
        && segments[3] == issue.to_string()
        && url.fragment() == Some(format!("issuecomment-{comment}").as_str())
}

fn snapshot_from_issue(
    repository: &GitHubRepositoryRef,
    requested_issue: u64,
    issue: GitHubIssue,
) -> Result<IssueMutationSnapshot, IssueMutationError> {
    if issue.number != requested_issue
        || !matches!(
            issue.state,
            GitHubIssueState::Open | GitHubIssueState::Closed
        )
        || chrono::DateTime::parse_from_rfc3339(&issue.updated_at).is_err()
    {
        return Err(IssueMutationError::new("invalid-read-back"));
    }
    Ok(IssueMutationSnapshot {
        repository: repository.clone(),
        issue: requested_issue,
        title: issue.title,
        body: issue.body,
        labels: issue.labels.into_iter().map(|label| label.name).collect(),
        state: issue.state,
        updated_at: issue.updated_at,
    })
}

fn verify_read_back(
    before: IssueMutationSnapshot,
    after: IssueMutationSnapshot,
    request: &IssueMutationRequest,
    body: Option<&str>,
) -> Result<VerifiedIssueMutation, IssueMutationError> {
    if !snapshot_is_strictly_newer(&before, &after) {
        return Err(IssueMutationError::new("non-fresh-read-back"));
    }
    if !mutation_postcondition(&before, &after, request, body) {
        return Err(IssueMutationError::new("postcondition-failed"));
    }
    Ok(VerifiedIssueMutation {
        before,
        after,
        fields: request.fields.clone(),
    })
}

#[cfg(test)]
mod tests {
    use super::IssueMutationOwner;
    use crate::{
        github::{LiveMutationRequest, OctocrabGitHubService},
        runtime::Cancellation,
    };
    use larch_core::{
        GitHubCloseReason, GitHubIssueState, GitHubRepositoryRef, IMPLEMENTING_PREFIX,
        IssueCreateRequest, IssueMutationError, IssueMutationField, IssueMutationLease,
        IssueMutationRequest, IssueMutationSnapshot,
    };
    use larch_test_support::{IssueServiceExchange, IssueServiceStub};
    use serde_json::{Value, json};
    use std::collections::BTreeSet;

    fn service(exchanges: Vec<IssueServiceExchange>) -> (OctocrabGitHubService, IssueServiceStub) {
        let server = IssueServiceStub::start(exchanges).expect("start issue service stub");
        let client = octocrab::Octocrab::builder()
            .personal_token(String::from("test-token"))
            .base_uri(server.base_url())
            .expect("stub base URI")
            .upload_uri(server.base_url())
            .expect("stub upload URI")
            .build()
            .expect("stub client");
        (OctocrabGitHubService::with_test_client(client), server)
    }

    fn response(status: u16, body: impl Into<Vec<u8>>) -> IssueServiceExchange {
        IssueServiceExchange::any_json(status, body).expect("valid issue service response")
    }

    fn issue_response(
        title: &str,
        body: &str,
        labels: &[&str],
        updated_at: &str,
    ) -> IssueServiceExchange {
        response(200, issue_json(title, body, labels, updated_at))
    }

    fn issue_json(title: &str, body: &str, labels: &[&str], updated_at: &str) -> String {
        let mut issue: Value =
            serde_json::from_str(include_str!("../../fixtures/github_issue.json"))
                .expect("valid issue fixture");
        issue["id"] = json!(70);
        issue["number"] = json!(7);
        issue["url"] = json!("https://api.github.com/repos/owner/repo/issues/7");
        issue["html_url"] = json!("https://github.com/owner/repo/issues/7");
        issue["title"] = json!(title);
        issue["body"] = json!(body);
        issue["updated_at"] = json!(updated_at);
        let template = issue["labels"]
            .as_array()
            .and_then(|labels| labels.first())
            .cloned()
            .expect("label fixture");
        issue["labels"] = Value::Array(
            labels
                .iter()
                .enumerate()
                .map(|(index, name)| {
                    let mut label = template.clone();
                    label["id"] = json!(index + 1);
                    label["name"] = json!(name);
                    label["url"] = json!(format!(
                        "https://api.github.com/repos/owner/repo/labels/{name}"
                    ));
                    label
                })
                .collect(),
        );
        issue.to_string()
    }

    fn authenticated_user_json() -> String {
        serde_json::from_str::<Value>(&issue_json("T", "B", &[], "2026-07-19T00:00:00Z"))
            .expect("issue fixture")["user"]
            .to_string()
    }

    fn assigned_issue_json(title: &str, body: &str, labels: &[&str]) -> String {
        let mut issue: Value =
            serde_json::from_str(&issue_json(title, body, labels, "2026-07-19T00:00:00Z"))
                .expect("issue fixture");
        let assignee = issue["user"].clone();
        issue["assignee"] = assignee.clone();
        issue["assignees"] = json!([assignee]);
        issue.to_string()
    }

    fn authenticated_user_response() -> IssueServiceExchange {
        IssueServiceExchange::json("GET", "/user", 200, authenticated_user_json())
            .expect("authenticated-user response")
    }

    fn comment_json(id: u64, body: &str) -> String {
        let user =
            serde_json::from_str::<Value>(&issue_json("T", "B", &[], "2026-07-19T00:00:00Z"))
                .expect("issue fixture")["user"]
                .clone();
        json!({
            "id": id,
            "node_id": format!("C_{id}"),
            "url": format!("https://api.github.com/repos/owner/repo/issues/comments/{id}"),
            "html_url": format!("https://github.com/owner/repo/issues/7#issuecomment-{id}"),
            "body": body,
            "user": user,
            "created_at": "2026-07-19T00:00:00Z",
            "updated_at": "2026-07-19T00:00:00Z",
        })
        .to_string()
    }

    fn repository() -> GitHubRepositoryRef {
        GitHubRepositoryRef::new("owner", "repo").expect("valid repository")
    }

    fn operator_authorization() -> LiveMutationRequest<'static> {
        LiveMutationRequest {
            context_file: None,
            operator_mode: true,
            run_id: "",
            trusted_root: None,
            test_deny: true,
        }
    }

    fn denied_authorization() -> LiveMutationRequest<'static> {
        LiveMutationRequest {
            context_file: None,
            operator_mode: false,
            run_id: "",
            trusted_root: None,
            test_deny: false,
        }
    }

    fn mutation_request(
        snapshot: &IssueMutationSnapshot,
        fields: BTreeSet<IssueMutationField>,
        title: Option<&str>,
        body: Option<&str>,
        labels: Option<BTreeSet<String>>,
    ) -> IssueMutationRequest {
        IssueMutationRequest {
            repository: snapshot.repository.clone(),
            issue: snapshot.issue,
            expected_updated_at: snapshot.updated_at.clone(),
            expected_state: snapshot.state,
            fields,
            title: title.map(str::to_owned),
            body: body.map(str::to_owned),
            labels,
            marker: None,
            lease: None,
        }
    }

    async fn snapshot(
        owner: &IssueMutationOwner<'_>,
        cancellation: &Cancellation,
    ) -> IssueMutationSnapshot {
        owner
            .read_snapshot(&repository(), 7, cancellation)
            .await
            .expect("read snapshot")
    }

    fn reason(error: IssueMutationError) -> &'static str {
        error.reason()
    }

    #[tokio::test]
    async fn authorization_refuses_before_the_first_github_read() {
        let (github, server) = service(Vec::new());
        let owner = IssueMutationOwner::new(&github);
        let cancellation = Cancellation::new();
        let request = IssueMutationRequest {
            repository: repository(),
            issue: 7,
            expected_updated_at: String::from("2026-07-19T00:00:00Z"),
            expected_state: GitHubIssueState::Open,
            fields: BTreeSet::from([IssueMutationField::Title]),
            title: Some(String::from("Renamed")),
            body: None,
            labels: None,
            marker: None,
            lease: None,
        };

        let error = owner
            .apply(&cancellation, &denied_authorization(), &request)
            .await
            .expect_err("unauthorized mutation must fail");

        assert_eq!(reason(error), "unauthorized-mutation");
        assert!(server.finish().expect("stub finished").is_empty());
    }

    #[tokio::test]
    async fn field_scoped_title_and_label_write_reads_back_the_full_postcondition() {
        let (github, server) = service(vec![
            issue_response("Regular", "Body", &["old"], "2026-07-19T00:00:00Z"),
            issue_response("Regular", "Body", &["old"], "2026-07-19T00:00:00Z"),
            issue_response(
                "Renamed <REDACTED-TOKEN>",
                "Body",
                &["old"],
                "2026-07-19T00:00:01Z",
            ),
            response(200, "[]"),
            response(200, "[]"),
            issue_response(
                "Renamed <REDACTED-TOKEN>",
                "Body",
                &["new"],
                "2026-07-19T00:00:03Z",
            ),
        ]);
        let owner = IssueMutationOwner::new(&github);
        let cancellation = Cancellation::new();
        let before = snapshot(&owner, &cancellation).await;
        let request = mutation_request(
            &before,
            BTreeSet::from([IssueMutationField::Title, IssueMutationField::Labels]),
            Some("Renamed ghp_abcdefghijklmnopqrst"),
            None,
            Some(BTreeSet::from([String::from("new")])),
        );

        let result = owner
            .apply(&cancellation, &operator_authorization(), &request)
            .await
            .expect("mutation succeeds");
        let requests = server.finish().expect("stub finished");
        let edit: Value = serde_json::from_slice(&requests[2].body.bytes).expect("edit JSON");

        assert_eq!(result.after.title, "Renamed <REDACTED-TOKEN>");
        assert_eq!(result.after.labels, BTreeSet::from([String::from("new")]));
        assert_eq!(requests[2].method, "PATCH");
        assert_eq!(edit["title"], "Renamed <REDACTED-TOKEN>");
        assert!(edit.get("body").is_none());
        assert!(edit.get("labels").is_none());
        assert_eq!(requests[3].method, "DELETE");
        assert_eq!(requests[4].method, "POST");
    }

    #[tokio::test]
    async fn stale_or_nonfresh_snapshots_fail_closed() {
        let (github, server) = service(vec![
            issue_response("Regular", "Body", &[], "2026-07-19T00:00:00Z"),
            issue_response("Concurrent", "Body", &[], "2026-07-19T00:00:01Z"),
        ]);
        let owner = IssueMutationOwner::new(&github);
        let cancellation = Cancellation::new();
        let before = snapshot(&owner, &cancellation).await;
        let request = mutation_request(
            &before,
            BTreeSet::from([IssueMutationField::Title]),
            Some("Renamed"),
            None,
            None,
        );
        let error = owner
            .apply(&cancellation, &operator_authorization(), &request)
            .await
            .expect_err("stale identity must fail");
        assert_eq!(reason(error), "stale-identity");
        assert_eq!(server.finish().expect("stub finished").len(), 2);

        let (service, server) = service(vec![
            issue_response("Regular", "Body", &[], "2026-07-19T00:00:00Z"),
            issue_response("Regular", "Body", &[], "2026-07-19T00:00:00Z"),
            issue_response("Renamed", "Body", &[], "2026-07-19T00:00:00Z"),
            issue_response("Renamed", "Body", &[], "2026-07-19T00:00:00Z"),
        ]);
        let owner = IssueMutationOwner::new(&service);
        let before = snapshot(&owner, &cancellation).await;
        let request = mutation_request(
            &before,
            BTreeSet::from([IssueMutationField::Title]),
            Some("Renamed"),
            None,
            None,
        );
        let error = owner
            .apply(&cancellation, &operator_authorization(), &request)
            .await
            .expect_err("unchanged timestamp must fail");
        assert_eq!(reason(error), "non-fresh-read-back");
        assert_eq!(server.finish().expect("stub finished").len(), 4);
    }

    #[tokio::test]
    async fn outbound_redaction_and_uncertain_write_reconciliation_are_safe() {
        let (service, server) = service(vec![
            issue_response("Regular", "Body", &[], "2026-07-19T00:00:00Z"),
            issue_response("Regular", "Body", &[], "2026-07-19T00:00:00Z"),
            response(500, r#"{"message":"temporary failure"}"#),
            issue_response("Regular", "Body", &[], "2026-07-19T00:00:00Z"),
            issue_response(
                "Regular",
                "Body <REDACTED-TOKEN>",
                &[],
                "2026-07-19T00:00:01Z",
            ),
        ]);
        let owner = IssueMutationOwner::new(&service);
        let cancellation = Cancellation::new();
        let before = snapshot(&owner, &cancellation).await;
        let request = mutation_request(
            &before,
            BTreeSet::from([IssueMutationField::Body]),
            None,
            Some("Body ghp_abcdefghijklmnopqrst"),
            None,
        );

        let result = owner
            .apply(&cancellation, &operator_authorization(), &request)
            .await
            .expect("landed write reconciles after transport failure");
        let requests = server.finish().expect("stub finished");
        let edit: Value = serde_json::from_slice(&requests[2].body.bytes).expect("edit JSON");

        assert_eq!(result.after.body, "Body <REDACTED-TOKEN>");
        assert_eq!(edit["body"], "Body <REDACTED-TOKEN>");
        assert_eq!(
            requests
                .iter()
                .filter(|request| request.method == "PATCH")
                .count(),
            1
        );
    }

    #[tokio::test]
    async fn managed_to_umbrella_conversion_is_atomic_and_field_scoped() {
        let original = "Original body\n";
        let converted = "Original body\n<!-- larch:umbrella-proposal -->\n";
        let (service, server) = service(vec![
            issue_response("[DESIGNING] Split", original, &[], "2026-07-19T00:00:00Z"),
            issue_response("[DESIGNING] Split", original, &[], "2026-07-19T00:00:00Z"),
            issue_response("[UMBRELLA] Split", converted, &[], "2026-07-19T00:00:01Z"),
            issue_response("[UMBRELLA] Split", converted, &[], "2026-07-19T00:00:01Z"),
        ]);
        let owner = IssueMutationOwner::new(&service);
        let cancellation = Cancellation::new();
        let before = snapshot(&owner, &cancellation).await;
        let request = mutation_request(
            &before,
            BTreeSet::from([
                IssueMutationField::Title,
                IssueMutationField::Body,
                IssueMutationField::UmbrellaConversion,
            ]),
            Some("[UMBRELLA] Split"),
            Some(converted),
            None,
        );

        let result = owner
            .apply(&cancellation, &operator_authorization(), &request)
            .await
            .expect("conversion succeeds");
        let mut invalid = request.clone();
        invalid.title = Some(String::from("[UMBRELLA] Rewritten"));
        assert_eq!(
            larch_core::verify_authorized_body_change(&invalid, &invalid, &before)
                .expect_err("conversion must preserve its source title")
                .reason(),
            "invalid-umbrella-conversion"
        );
        let requests = server.finish().expect("stub finished");
        let edit: Value = serde_json::from_slice(&requests[2].body.bytes).expect("edit JSON");

        assert_eq!(result.after.title, "[UMBRELLA] Split");
        assert_eq!(edit["title"], "[UMBRELLA] Split");
        assert_eq!(edit["body"], converted);
        assert_eq!(
            requests
                .iter()
                .filter(|request| request.method == "PATCH")
                .count(),
            1
        );
    }

    #[tokio::test]
    async fn recordless_umbrella_adoption_is_atomic_and_keeps_the_external_title() {
        let original = "External context\n";
        let adopted = "External context\n<!-- larch:umbrella-proposal -->\n";
        let title = "[UMBRELLA] External split";
        let (service, server) = service(vec![
            issue_response(title, original, &[], "2026-07-19T00:00:00Z"),
            issue_response(title, original, &[], "2026-07-19T00:00:00Z"),
            issue_response(title, adopted, &[], "2026-07-19T00:00:01Z"),
            issue_response(title, adopted, &[], "2026-07-19T00:00:01Z"),
        ]);
        let owner = IssueMutationOwner::new(&service);
        let cancellation = Cancellation::new();
        let before = snapshot(&owner, &cancellation).await;
        let request = mutation_request(
            &before,
            BTreeSet::from([
                IssueMutationField::Title,
                IssueMutationField::Body,
                IssueMutationField::UmbrellaAdoption,
            ]),
            Some(title),
            Some(adopted),
            None,
        );

        let result = owner
            .apply(&cancellation, &operator_authorization(), &request)
            .await
            .expect("adoption succeeds");
        let requests = server.finish().expect("stub finished");
        let edit: Value = serde_json::from_slice(&requests[2].body.bytes).expect("edit JSON");

        assert_eq!(result.after.title, title);
        assert_eq!(result.after.body, adopted);
        assert_eq!(edit["title"], title);
        assert_eq!(edit["body"], adopted);
        assert_eq!(
            requests
                .iter()
                .filter(|request| request.method == "PATCH")
                .count(),
            1
        );
    }

    #[tokio::test]
    async fn initial_lease_and_implementing_title_land_in_one_verified_patch() {
        let original = format!(
            "<!-- larch:plan-receipt v1 plan_sha256={} base_sha={} blockers_sha256={} owners_sha256={} -->\n",
            "b".repeat(64),
            "a".repeat(40),
            "c".repeat(64),
            "d".repeat(64),
        );
        let lease = format!(
            "<!-- larch:implementation-lease v1 run_id=run-7 branch=feature/work base={} plan={} updated_at=2026-08-10T00:00:00Z -->",
            "a".repeat(40),
            "b".repeat(64),
        );
        let updated = format!("{original}\n{lease}\n");
        let (service, server) = service(vec![
            issue_response("[DESIGNED] Work", &original, &[], "2026-08-10T00:00:00Z"),
            issue_response("[DESIGNED] Work", &original, &[], "2026-08-10T00:00:00Z"),
            issue_response("[IMPLEMENTING] Work", &updated, &[], "2026-08-10T00:00:01Z"),
            issue_response("[IMPLEMENTING] Work", &updated, &[], "2026-08-10T00:00:01Z"),
        ]);
        let owner = IssueMutationOwner::new(&service);
        let cancellation = Cancellation::new();
        let before = snapshot(&owner, &cancellation).await;
        let mut request = mutation_request(
            &before,
            BTreeSet::from([
                IssueMutationField::Title,
                IssueMutationField::ImplementationLease,
            ]),
            Some("[IMPLEMENTING] Work"),
            Some(&updated),
            None,
        );
        request.marker = Some(String::from("implementation-lease"));
        request.lease = Some(IssueMutationLease {
            run_id: String::from("run-7"),
            marker: String::from("implementation-lease"),
        });

        let result = owner
            .apply(&cancellation, &operator_authorization(), &request)
            .await
            .expect("atomic activation succeeds");
        let requests = server.finish().expect("stub finished");
        let edit: Value = serde_json::from_slice(&requests[2].body.bytes).expect("edit JSON");

        assert_eq!(result.after.title, format!("{IMPLEMENTING_PREFIX}Work"));
        assert_eq!(result.after.body, updated);
        assert_eq!(edit["title"], format!("{IMPLEMENTING_PREFIX}Work"));
        assert_eq!(edit["body"], updated);
        assert_eq!(
            requests
                .iter()
                .filter(|request| request.method == "PATCH")
                .count(),
            1
        );
    }
    #[tokio::test]
    async fn a_create_refuses_before_the_first_github_request() {
        let (service, server) = service(Vec::new());
        let owner = IssueMutationOwner::new(&service);

        let failure = owner
            .create(
                &Cancellation::new(),
                &denied_authorization(),
                &create_request("Title", "Body", &[]),
            )
            .await
            .expect_err("unauthorized create must fail");

        assert_eq!(failure.error.reason(), "unauthorized-mutation");
        assert_eq!(failure.orphan, None);
        assert!(server.finish().expect("stub finished").is_empty());
    }

    #[tokio::test]
    async fn a_create_refuses_when_the_authenticated_assignee_cannot_be_resolved() {
        let (service, server) = service(vec![
            IssueServiceExchange::json("GET", "/user", 403, r#"{"message":"forbidden"}"#)
                .expect("authenticated-user refusal"),
        ]);

        let failure = IssueMutationOwner::new(&service)
            .create(
                &Cancellation::new(),
                &operator_authorization(),
                &create_request("Title", "Body", &[]),
            )
            .await
            .expect_err("an unresolved assignee must fail before create");

        assert_eq!(failure.error.reason(), "assignee-read-failed");
        assert_eq!(failure.orphan, None);
        assert_eq!(server.finish().expect("stub finished").len(), 1);
    }

    #[tokio::test]
    async fn a_create_without_assignment_request_keeps_the_existing_payload() {
        let unassigned = issue_json("T", "B", &[], "2026-07-19T00:00:00Z");
        let (service, server) = service(vec![
            IssueServiceExchange::json("POST", "/repos/owner/repo/issues", 201, unassigned.clone())
                .expect("create response"),
            IssueServiceExchange::json("GET", "/repos/owner/repo/issues/7", 200, unassigned)
                .expect("create read-back"),
        ]);
        let mut request = create_request("T", "B", &[]);
        request.assign_authenticated_user = false;

        let created = IssueMutationOwner::new(&service)
            .create(&Cancellation::new(), &operator_authorization(), &request)
            .await
            .expect("unassigned create succeeds");
        let requests = server.finish().expect("stub finished");
        let body: Value = serde_json::from_slice(&requests[0].body.bytes).expect("create JSON");

        assert_eq!(created.number, 7);
        assert_eq!(requests.len(), 2);
        assert_eq!(requests[0].method, "POST");
        assert!(body.get("assignees").is_none());
    }

    #[tokio::test]
    async fn a_create_redacts_every_outbound_string_and_reads_back_its_identity() {
        let redacted = assigned_issue_json(
            "Renamed <REDACTED-TOKEN>",
            "Body <REDACTED-TOKEN>",
            &["keep"],
        );
        let (service, server) = service(vec![
            authenticated_user_response(),
            IssueServiceExchange::json("POST", "/repos/owner/repo/issues", 201, redacted.clone())
                .expect("create response"),
            IssueServiceExchange::json("GET", "/repos/owner/repo/issues/7", 200, redacted)
                .expect("create read-back"),
        ]);
        let owner = IssueMutationOwner::new(&service);

        let created = owner
            .create(
                &Cancellation::new(),
                &operator_authorization(),
                &create_request(
                    "Renamed ghp_abcdefghijklmnopqrst",
                    "Body ghp_abcdefghijklmnopqrst",
                    &["keep"],
                ),
            )
            .await
            .expect("create succeeds");
        let requests = server.finish().expect("stub finished");
        let body: Value = serde_json::from_slice(&requests[1].body.bytes).expect("create JSON");

        assert_eq!((created.number, created.id), (7, 70));
        assert_eq!(created.url, "https://github.com/owner/repo/issues/7");
        assert_eq!(requests[0].method, "GET");
        assert_eq!(requests[0].path, "/user");
        assert_eq!(requests[1].method, "POST");
        assert_eq!(requests[2].method, "GET");
        assert_eq!(body["title"], "Renamed <REDACTED-TOKEN>");
        assert_eq!(body["body"], "Body <REDACTED-TOKEN>");
        assert_eq!(body["assignees"], json!(["octocat"]));
        assert_eq!(body["labels"], json!(["keep"]));
    }

    #[tokio::test]
    async fn a_create_refuses_an_assignee_github_did_not_persist() {
        let assigned = assigned_issue_json("T", "B", &[]);
        let unassigned = issue_json("T", "B", &[], "2026-07-19T00:00:00Z");
        let (service, server) = service(vec![
            authenticated_user_response(),
            IssueServiceExchange::json("POST", "/repos/owner/repo/issues", 201, assigned)
                .expect("create response"),
            IssueServiceExchange::json("GET", "/repos/owner/repo/issues/7", 200, unassigned)
                .expect("create read-back"),
        ]);

        let failure = IssueMutationOwner::new(&service)
            .create(
                &Cancellation::new(),
                &operator_authorization(),
                &create_request("T", "B", &[]),
            )
            .await
            .expect_err("a dropped assignee must fail");

        assert_eq!(failure.error.reason(), "invalid-read-back");
        assert_eq!(failure.orphan, Some(7));
        assert_eq!(server.finish().expect("stub finished").len(), 3);
    }

    #[tokio::test]
    async fn comment_mutations_are_authorized_redacted_and_read_back() {
        let (service, server) = service(vec![
            IssueServiceExchange::json(
                "POST",
                "/repos/owner/repo/issues/7/comments",
                201,
                comment_json(11, "note <REDACTED-TOKEN>"),
            )
            .expect("comment response"),
            IssueServiceExchange::json(
                "GET",
                "/repos/owner/repo/issues/7/comments?per_page=100",
                200,
                format!("[{}]", comment_json(11, "note <REDACTED-TOKEN>")),
            )
            .expect("comment read-back"),
            IssueServiceExchange::any_json(200, comment_json(11, "updated"))
                .expect("comment response"),
            IssueServiceExchange::json(
                "GET",
                "/repos/owner/repo/issues/7/comments?per_page=100",
                200,
                format!("[{}]", comment_json(11, "updated")),
            )
            .expect("comment read-back"),
        ]);
        let owner = IssueMutationOwner::new(&service);
        let cancellation = Cancellation::new();

        let created = owner
            .create_comment(
                &cancellation,
                &operator_authorization(),
                &repository(),
                7,
                "note ghp_abcdefghijklmnopqrst",
            )
            .await
            .expect("create comment");
        let edited = owner
            .edit_comment(
                &cancellation,
                &operator_authorization(),
                &repository(),
                7,
                11,
                "updated",
            )
            .await
            .expect("edit comment");
        let requests = server.finish().expect("stub finished");
        let create: Value = serde_json::from_slice(&requests[0].body.bytes).expect("create JSON");

        assert_eq!((created.id, edited.id), (11, 11));
        assert_eq!(create["body"], "note <REDACTED-TOKEN>");
        assert_eq!(requests[2].method, "POST");
    }

    #[tokio::test]
    async fn comment_mutations_refuse_before_github_and_reject_bad_echoes() {
        let (github, server) = service(Vec::new());
        let owner = IssueMutationOwner::new(&github);
        let cancellation = Cancellation::new();
        let error = owner
            .create_comment(
                &cancellation,
                &denied_authorization(),
                &repository(),
                7,
                "note",
            )
            .await
            .expect_err("authorization must fail");
        assert_eq!(error.reason(), "unauthorized-mutation");
        assert!(server.finish().expect("stub finished").is_empty());

        let (bad_echo_service, server) = service(vec![
            IssueServiceExchange::any_json(200, comment_json(12, "wrong"))
                .expect("comment response"),
        ]);
        let error = IssueMutationOwner::new(&bad_echo_service)
            .edit_comment(
                &cancellation,
                &operator_authorization(),
                &repository(),
                7,
                11,
                "expected",
            )
            .await
            .expect_err("mismatched response must fail");
        assert_eq!(error.reason(), "comment-read-back-failed");
        assert_eq!(server.finish().expect("stub finished").len(), 1);

        let (bad_read_back_service, server) = service(vec![
            IssueServiceExchange::any_json(200, comment_json(11, "expected"))
                .expect("comment response"),
            IssueServiceExchange::json(
                "GET",
                "/repos/owner/repo/issues/7/comments?per_page=100",
                200,
                format!("[{}]", comment_json(11, "wrong")),
            )
            .expect("comment read-back"),
        ]);
        let error = IssueMutationOwner::new(&bad_read_back_service)
            .edit_comment(
                &cancellation,
                &operator_authorization(),
                &repository(),
                7,
                11,
                "expected",
            )
            .await
            .expect_err("a mismatched GET read-back must fail");
        assert_eq!(error.reason(), "comment-read-back-failed");
        assert_eq!(server.finish().expect("stub finished").len(), 2);

        let mut foreign_url: Value =
            serde_json::from_str(&comment_json(11, "expected")).expect("comment fixture");
        foreign_url["html_url"] =
            json!("https://attacker.test/owner/repo/issues/7#issuecomment-11");
        let (foreign_service, server) = service(vec![
            IssueServiceExchange::any_json(200, foreign_url.to_string()).expect("comment response"),
        ]);
        let error = IssueMutationOwner::new(&foreign_service)
            .edit_comment(
                &cancellation,
                &operator_authorization(),
                &repository(),
                7,
                11,
                "expected",
            )
            .await
            .expect_err("a foreign comment URL must fail");
        assert_eq!(error.reason(), "comment-read-back-failed");
        assert_eq!(server.finish().expect("stub finished").len(), 1);
    }

    #[tokio::test]
    async fn comment_delete_requires_an_absence_read_back() {
        let (service, server) = service(vec![
            IssueServiceExchange::json("DELETE", "/repos/owner/repo/issues/comments/11", 204, "")
                .expect("delete response"),
            IssueServiceExchange::json(
                "GET",
                "/repos/owner/repo/issues/7/comments?per_page=100",
                200,
                "[]",
            )
            .expect("comment list"),
        ]);

        IssueMutationOwner::new(&service)
            .delete_comment(
                &Cancellation::new(),
                &operator_authorization(),
                &repository(),
                7,
                11,
            )
            .await
            .expect("absence proves deletion");
        assert_eq!(server.finish().expect("stub finished").len(), 2);
    }

    #[tokio::test]
    async fn an_unusable_create_echo_names_the_orphan_it_left_behind() {
        let mut echo: Value =
            serde_json::from_str(&issue_json("T", "B", &[], "2026-07-19T00:00:00Z"))
                .expect("issue JSON");
        echo["id"] = json!(0);
        let (invalid_service, server) = service(vec![
            authenticated_user_response(),
            response(201, echo.to_string()),
        ]);
        let owner = IssueMutationOwner::new(&invalid_service);

        let failure = owner
            .create(
                &Cancellation::new(),
                &operator_authorization(),
                &create_request("T", "B", &[]),
            )
            .await
            .expect_err("a zero node id must fail");

        assert_eq!(failure.error.reason(), "invalid-read-back");
        assert_eq!(failure.orphan, Some(7));
        assert_eq!(server.finish().expect("stub finished").len(), 2);

        let echo = issue_json("T", "B", &[], "2026-07-19T00:00:00Z");
        let mut hostile_read_back: Value =
            serde_json::from_str(&echo).expect("issue read-back fixture");
        hostile_read_back["html_url"] = json!("https://attacker.test/owner/repo/issues/7");
        let (service, server) = service(vec![
            authenticated_user_response(),
            response(201, echo),
            response(200, hostile_read_back.to_string()),
        ]);
        let failure = IssueMutationOwner::new(&service)
            .create(
                &Cancellation::new(),
                &operator_authorization(),
                &create_request("T", "B", &[]),
            )
            .await
            .expect_err("a foreign GET read-back URL must fail");
        assert_eq!(failure.error.reason(), "invalid-read-back");
        assert_eq!(failure.orphan, Some(7));
        assert_eq!(server.finish().expect("stub finished").len(), 3);
    }

    #[tokio::test]
    async fn a_close_is_proved_by_its_read_back_and_never_guessed() {
        let mut closed: Value =
            serde_json::from_str(&issue_json("T", "B", &[], "2026-07-19T00:00:00Z"))
                .expect("issue JSON");
        closed["state"] = json!("closed");
        let (service, server) = service(vec![
            response(200, closed.to_string()),
            issue_response("T", "B", &[], "2026-07-19T00:00:00Z"),
        ]);
        let owner = IssueMutationOwner::new(&service);
        let cancellation = Cancellation::new();

        owner
            .close_not_planned(&cancellation, &repository(), 7)
            .await
            .expect("a closed read-back proves the close");
        let error = owner
            .close_not_planned(&cancellation, &repository(), 7)
            .await
            .expect_err("an issue that stayed open must fail");

        assert_eq!(error, "close-read-back-failed");
        assert_eq!(server.finish().expect("stub finished").len(), 2);
    }

    #[tokio::test]
    async fn a_commented_close_redacts_then_confirms_the_closed_issue() {
        let mut closed: Value =
            serde_json::from_str(&issue_json("T", "B", &[], "2026-07-19T00:00:00Z"))
                .expect("issue fixture");
        closed["state"] = json!("closed");
        let mut comment = json!({
            "id": 11, "node_id": "C_11",
            "url": "https://api.github.com/repos/owner/repo/issues/comments/11",
            "html_url": "https://github.com/owner/repo/issues/7#issuecomment-11",
            "body": "note <REDACTED-TOKEN>",
            "created_at": "2026-07-19T00:00:00Z",
            "updated_at": "2026-07-19T00:00:00Z",
        });
        comment["user"] =
            serde_json::from_str::<Value>(&issue_json("T", "B", &[], "2026-07-19T00:00:00Z"))
                .expect("issue fixture")["user"]
                .clone();
        let (service, server) = service(vec![
            IssueServiceExchange::json(
                "GET",
                "/repos/owner/repo/issues/7",
                200,
                issue_json("T", "B", &[], "2026-07-19T00:00:00Z"),
            )
            .expect("snapshot response"),
            IssueServiceExchange::json(
                "POST",
                "/repos/owner/repo/issues/7/comments",
                201,
                comment.to_string(),
            )
            .expect("comment response"),
            IssueServiceExchange::json(
                "PATCH",
                "/repos/owner/repo/issues/7",
                200,
                closed.to_string(),
            )
            .expect("close response"),
        ]);
        let owner = IssueMutationOwner::new(&service);

        let result = owner
            .close_with_comment(
                &Cancellation::new(),
                &operator_authorization(),
                &repository(),
                7,
                GitHubCloseReason::Completed,
                Some("note ghp_abcdefghijklmnopqrst"),
            )
            .await;
        let requests = server.finish().expect("stub finished");
        let closed = result.expect("close succeeds");
        let note: Value = serde_json::from_slice(&requests[1].body.bytes).expect("comment JSON");

        assert_eq!(closed.state, GitHubIssueState::Closed);
        assert_eq!(note["body"], "note <REDACTED-TOKEN>");
        assert_eq!(requests[2].method, "PATCH");
    }

    #[tokio::test]
    async fn a_commented_close_refuses_a_comment_echo_that_lost_its_marker() {
        let mut comment = json!({
            "id": 11, "node_id": "C_11",
            "url": "https://api.github.com/repos/owner/repo/issues/comments/11",
            "html_url": "https://github.com/owner/repo/issues/7#issuecomment-11",
            "body": "wrong note",
            "created_at": "2026-07-19T00:00:00Z",
            "updated_at": "2026-07-19T00:00:00Z",
        });
        comment["user"] =
            serde_json::from_str::<Value>(&issue_json("T", "B", &[], "2026-07-19T00:00:00Z"))
                .expect("issue fixture")["user"]
                .clone();
        let (service, server) = service(vec![
            IssueServiceExchange::json(
                "GET",
                "/repos/owner/repo/issues/7",
                200,
                issue_json("T", "B", &[], "2026-07-19T00:00:00Z"),
            )
            .expect("snapshot response"),
            IssueServiceExchange::json(
                "POST",
                "/repos/owner/repo/issues/7/comments",
                201,
                comment.to_string(),
            )
            .expect("comment response"),
        ]);
        let owner = IssueMutationOwner::new(&service);

        let error = owner
            .close_with_comment(
                &Cancellation::new(),
                &operator_authorization(),
                &repository(),
                7,
                GitHubCloseReason::Completed,
                Some("expected note"),
            )
            .await
            .expect_err("a mismatched comment must stop the close");

        assert_eq!(error.reason(), "comment-read-back-failed");
        assert_eq!(server.finish().expect("stub finished").len(), 2);
    }

    #[tokio::test]
    async fn a_commented_close_refuses_before_any_github_request() {
        let (service, server) = service(Vec::new());
        let owner = IssueMutationOwner::new(&service);

        let error = owner
            .close_with_comment(
                &Cancellation::new(),
                &denied_authorization(),
                &repository(),
                7,
                GitHubCloseReason::Completed,
                Some("note"),
            )
            .await
            .expect_err("unauthorized close must fail");

        assert_eq!(error.reason(), "unauthorized-mutation");
        assert!(server.finish().expect("stub finished").is_empty());
    }

    fn create_request(title: &str, body: &str, labels: &[&str]) -> IssueCreateRequest {
        IssueCreateRequest {
            repository: repository(),
            title: title.to_owned(),
            body: body.to_owned(),
            assign_authenticated_user: true,
            labels: labels.iter().map(|label| (*label).to_owned()).collect(),
        }
    }
}
