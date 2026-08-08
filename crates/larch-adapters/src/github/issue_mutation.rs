//! The sole Rust owner for freshness-checked GitHub issue field mutations.
//!
//! This adapter uses the GitHub runtime's shared mutation lock, checks the
//! existing live-mutation authorization gate before any GitHub read, and
//! delegates request shape, redaction, protected-body checks, and read-back
//! proof to `larch_core::issue_mutation`.

use larch_core::{
    CreatedIssue, GitHubCloseReason, GitHubIssue, GitHubIssueCreate, GitHubIssueEdit,
    GitHubIssueState, GitHubRepositoryRef, GitHubService, IssueCreateRequest, IssueMutationError,
    IssueMutationField, IssueMutationRequest, IssueMutationSnapshot, ProcessCancellation,
    VerifiedIssueMutation, mutation_postcondition, mutation_would_change,
    redact_issue_create_request, redact_issue_mutation_request, same_mutation_identity,
    snapshot_is_strictly_newer, validate_issue_mutation_request, verify_authorized_body_change,
    verify_created_issue,
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
            .map_err(|_| IssueMutationError::new("read-failed"))?;
        snapshot_from_issue(repository, issue, response)
    }

    /// Create one issue, redacting every outbound string before the request.
    ///
    /// Authorization is checked before GitHub is contacted at all, so an
    /// unauthorized caller never reaches the network. The response GitHub
    /// echoes is the read-back: a create that returns no usable number, node
    /// id, or URL leaves an orphan the caller is told to close.
    ///
    /// # Errors
    ///
    /// Returns `unauthorized-mutation`, `redaction-failed`, `create-failed`,
    /// or `invalid-read-back` inside an [`IssueCreateFailure`] that names the
    /// orphan issue when one exists.
    pub async fn create(
        &self,
        cancellation: &dyn ProcessCancellation,
        authorization: &LiveMutationRequest<'_>,
        request: &IssueCreateRequest,
    ) -> Result<CreatedIssue, IssueCreateFailure> {
        authorize(authorization).map_err(IssueCreateFailure::without_orphan)?;
        let redacted =
            redact_issue_create_request(request).map_err(IssueCreateFailure::without_orphan)?;
        let create = GitHubIssueCreate {
            repo: redacted.repository,
            title: redacted.title,
            body: redacted.body,
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
        verify_created_issue(&created).map_err(|error| IssueCreateFailure {
            error,
            orphan: (created.number != 0).then_some(created.number),
            detail: String::new(),
        })
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
            };
            self.service
                .edit_issue(&edit, cancellation)
                .await
                .map_err(|_| IssueMutationError::new("write-failed"))?;
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
            && mutation_postcondition(&after, request, body)
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
    if !mutation_postcondition(&after, request, body) {
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
        GitHubIssueState, GitHubRepositoryRef, IssueCreateRequest, IssueMutationError,
        IssueMutationField, IssueMutationRequest, IssueMutationSnapshot,
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
        let (service, server) = service(Vec::new());
        let owner = IssueMutationOwner::new(&service);
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
    async fn a_create_redacts_every_outbound_string_and_reads_back_its_identity() {
        let (service, server) = service(vec![issue_response(
            "Renamed",
            "Body",
            &["keep"],
            "2026-07-19T00:00:00Z",
        )]);
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
        let body: Value = serde_json::from_slice(&requests[0].body.bytes).expect("create JSON");

        assert_eq!((created.number, created.id), (7, 70));
        assert_eq!(created.url, "https://github.com/o/r/issues/2");
        assert_eq!(requests[0].method, "POST");
        assert_eq!(body["title"], "Renamed <REDACTED-TOKEN>");
        assert_eq!(body["body"], "Body <REDACTED-TOKEN>");
        assert_eq!(body["labels"], json!(["keep"]));
    }

    #[tokio::test]
    async fn an_unusable_create_echo_names_the_orphan_it_left_behind() {
        let mut echo: Value =
            serde_json::from_str(&issue_json("T", "B", &[], "2026-07-19T00:00:00Z"))
                .expect("issue JSON");
        echo["id"] = json!(0);
        let (service, server) = service(vec![response(201, echo.to_string())]);
        let owner = IssueMutationOwner::new(&service);

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
        assert_eq!(server.finish().expect("stub finished").len(), 1);
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

    fn create_request(title: &str, body: &str, labels: &[&str]) -> IssueCreateRequest {
        IssueCreateRequest {
            repository: repository(),
            title: title.to_owned(),
            body: body.to_owned(),
            labels: labels.iter().map(|label| (*label).to_owned()).collect(),
        }
    }
}
