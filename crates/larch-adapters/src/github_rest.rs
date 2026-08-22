//! Bounded repository, issue, comment, label, and search operations.

use crate::github::{
    GitHubCompletionError, OctocrabGitHubService, github_utc_timestamp, octocrab_is_unreachable,
    octocrab_status,
};
use larch_core::{
    GitHubCloseReason, GitHubComment, GitHubFuture, GitHubIssue, GitHubIssueBodyMode,
    GitHubIssueCreate, GitHubIssueEdit, GitHubIssueList, GitHubIssueListMode,
    GitHubIssueListResult, GitHubIssueListTimeoutScope, GitHubIssueScan, GitHubIssueSearch,
    GitHubIssueState, GitHubLabel, GitHubLabelCreate, GitHubListOutcome, GitHubListStop,
    GitHubOperationError, GitHubOperationErrorKind, GitHubRepository, GitHubRepositoryRef,
    GitHubService, GitHubTransportPolicy, GitHubUser, ProcessCancellation, resolve_issue_list,
};
use octocrab::{Page, models, params};
use serde::Serialize;
use serde_json::Value;
use std::{
    future::Future,
    time::{Duration, SystemTime, UNIX_EPOCH},
};

const PAGE_SIZE: u8 = 100;
const READ_ATTEMPTS: usize = 3;

#[derive(Clone, Copy)]
enum RateBucket {
    Core,
    Search,
}

/// List behavior the shared page collector applies after the first request.
#[derive(Clone, Copy)]
struct IssueListCollectionOptions {
    limit: usize,
    mode: GitHubIssueListMode,
    body_mode: GitHubIssueBodyMode,
}

#[allow(
    clippy::large_futures,
    reason = "Octocrab semantic builders are boxed at the object-safe GitHub service boundary"
)]
impl GitHubService for OctocrabGitHubService {
    fn transport_policy(&self) -> GitHubTransportPolicy {
        self.policy
    }

    fn authenticated_user<'a>(
        &'a self,
        cancellation: &'a dyn ProcessCancellation,
    ) -> GitHubFuture<'a, GitHubUser> {
        Box::pin(async move {
            self.guarded(cancellation, async {
                let value = self
                    .read_with_retry(cancellation, RateBucket::Core, || async {
                        self.client.current().user().await
                    })
                    .await?;
                validate_json(&value, self.policy)?;
                validate_string(&value.login, self.policy)?;
                if value.login.is_empty() {
                    return Err(malformed(
                        "GitHub authenticated-user response omitted login",
                    ));
                }
                Ok(GitHubUser { login: value.login })
            })
            .await
        })
    }

    fn repository<'a>(
        &'a self,
        repo: &'a GitHubRepositoryRef,
        cancellation: &'a dyn ProcessCancellation,
    ) -> GitHubFuture<'a, GitHubRepository> {
        Box::pin(async move {
            self.guarded(cancellation, async {
                validate_repo(repo)?;
                let value = self
                    .read_with_retry(cancellation, RateBucket::Core, || async {
                        self.client.repos(repo.owner(), repo.name()).get().await
                    })
                    .await?;
                repository_from_model(value, self.policy)
            })
            .await
        })
    }

    fn issue<'a>(
        &'a self,
        repo: &'a GitHubRepositoryRef,
        number: u64,
        cancellation: &'a dyn ProcessCancellation,
    ) -> GitHubFuture<'a, GitHubIssue> {
        Box::pin(async move {
            self.guarded(cancellation, self.get_issue(repo, number, cancellation))
                .await
        })
    }

    fn list_issues<'a>(
        &'a self,
        request: &'a GitHubIssueList,
        cancellation: &'a dyn ProcessCancellation,
    ) -> GitHubFuture<'a, GitHubIssueListResult> {
        Box::pin(async move {
            let operation = async {
                validate_repo(&request.repo)?;
                validate_limit(request.limit, self.policy)?;
                for label in &request.labels {
                    validate_string(label, self.policy)?;
                }
                let state = match request.state {
                    GitHubIssueState::Open => params::State::Open,
                    GitHubIssueState::Closed => params::State::Closed,
                    GitHubIssueState::All => params::State::All,
                };
                let first = self
                    .read_issue_page(cancellation, RateBucket::Core, || async {
                        self.client
                            .issues(request.repo.owner(), request.repo.name())
                            .list()
                            .state(state)
                            .labels(&request.labels)
                            .per_page(PAGE_SIZE)
                            .send()
                            .await
                    })
                    .await?;
                self.collect_issues(
                    &request.repo,
                    first,
                    IssueListCollectionOptions {
                        limit: request.limit,
                        mode: request.mode,
                        body_mode: request.body_mode,
                    },
                    RateBucket::Core,
                    cancellation,
                )
                .await
            };
            self.guard_issue_list(cancellation, operation).await
        })
    }

    fn search_issues<'a>(
        &'a self,
        request: &'a GitHubIssueSearch,
        cancellation: &'a dyn ProcessCancellation,
    ) -> GitHubFuture<'a, Vec<GitHubIssue>> {
        Box::pin(async move {
            self.guarded(cancellation, async {
                validate_repo(&request.repo)?;
                validate_limit(request.limit, self.policy)?;
                validate_string(&request.query, self.policy)?;
                let query = format!(
                    "{} repo:{}/{}",
                    request.query,
                    request.repo.owner(),
                    request.repo.name()
                );
                let first = self
                    .read_issue_page(cancellation, RateBucket::Search, || async {
                        self.client
                            .search()
                            .issues_and_pull_requests(&query)
                            .per_page(PAGE_SIZE)
                            .send()
                            .await
                    })
                    .await?;
                self.collect_issues(
                    &request.repo,
                    first,
                    IssueListCollectionOptions {
                        limit: request.limit,
                        mode: GitHubIssueListMode::Exhaustive,
                        body_mode: GitHubIssueBodyMode::Include,
                    },
                    RateBucket::Search,
                    cancellation,
                )
                .await
                .map(|result| result.issues)
            })
            .await
        })
    }

    fn create_issue<'a>(
        &'a self,
        request: &'a GitHubIssueCreate,
        cancellation: &'a dyn ProcessCancellation,
    ) -> GitHubFuture<'a, GitHubIssue> {
        Box::pin(async move {
            self.guarded(cancellation, async {
                validate_repo(&request.repo)?;
                validate_string(&request.title, self.policy)?;
                validate_string(&request.body, self.policy)?;
                for assignee in &request.assignees {
                    validate_string(assignee, self.policy)?;
                }
                for label in &request.labels {
                    validate_string(label, self.policy)?;
                }
                let issues = self
                    .client
                    .issues(request.repo.owner(), request.repo.name());
                let mut create = issues
                    .create(&request.title)
                    .body(&request.body)
                    .labels(request.labels.clone());
                if !request.assignees.is_empty() {
                    create = create.assignees(request.assignees.clone());
                }
                let result = create.send().await;
                match result {
                    Ok(value) => issue_from_model(value, self.policy),
                    Err(error) if transient_octocrab_error(&error) => Err(ambiguous(&error, self)),
                    Err(error) => Err(map_octocrab_error(&error, self)),
                }
            })
            .await
        })
    }

    fn edit_issue<'a>(
        &'a self,
        request: &'a GitHubIssueEdit,
        cancellation: &'a dyn ProcessCancellation,
    ) -> GitHubFuture<'a, GitHubIssue> {
        Box::pin(async move {
            self.guarded(cancellation, async {
                validate_repo(&request.repo)?;
                validate_number(request.number)?;
                if request.title.is_none()
                    && request.body.is_none()
                    && request.labels.is_none()
                    && request.assignees.is_none()
                {
                    return Err(operation_error(
                        GitHubOperationErrorKind::InvalidInput,
                        "GitHub issue edit must change at least one field",
                    ));
                }
                let handler = self
                    .client
                    .issues(request.repo.owner(), request.repo.name());
                let mut update = handler.update(request.number);
                if let Some(title) = &request.title {
                    validate_string(title, self.policy)?;
                    update = update.title(title);
                }
                if let Some(body) = &request.body {
                    validate_string(body, self.policy)?;
                    update = update.body(body);
                }
                if let Some(labels) = &request.labels {
                    for label in labels {
                        validate_string(label, self.policy)?;
                    }
                    update = update.labels(labels);
                }
                if let Some(assignees) = &request.assignees {
                    for assignee in assignees {
                        validate_string(assignee, self.policy)?;
                    }
                    update = update.assignees(assignees);
                }
                match update.send().await {
                    Ok(value) => issue_from_model(value, self.policy),
                    Err(error) if transient_octocrab_error(&error) => {
                        let current = self
                            .get_issue(&request.repo, request.number, cancellation)
                            .await?;
                        if issue_matches_edit(&current, request) {
                            Ok(current)
                        } else {
                            Err(ambiguous(&error, self))
                        }
                    }
                    Err(error) => Err(map_octocrab_error(&error, self)),
                }
            })
            .await
        })
    }

    fn close_issue<'a>(
        &'a self,
        repo: &'a GitHubRepositoryRef,
        number: u64,
        reason: GitHubCloseReason,
        cancellation: &'a dyn ProcessCancellation,
    ) -> GitHubFuture<'a, GitHubIssue> {
        Box::pin(async move {
            self.guarded(cancellation, async {
                validate_repo(repo)?;
                validate_number(number)?;
                let state_reason = match reason {
                    GitHubCloseReason::Completed => models::issues::IssueStateReason::Completed,
                    GitHubCloseReason::NotPlanned => models::issues::IssueStateReason::NotPlanned,
                };
                let result = self
                    .client
                    .issues(repo.owner(), repo.name())
                    .update(number)
                    .state(models::IssueState::Closed)
                    .state_reason(state_reason)
                    .send()
                    .await;
                match result {
                    Ok(value) => issue_from_model(value, self.policy),
                    Err(error) if transient_octocrab_error(&error) => {
                        let current = self.get_issue(repo, number, cancellation).await?;
                        if current.state == GitHubIssueState::Closed {
                            Ok(current)
                        } else {
                            Err(ambiguous(&error, self))
                        }
                    }
                    Err(error) => Err(map_octocrab_error(&error, self)),
                }
            })
            .await
        })
    }

    fn list_comments<'a>(
        &'a self,
        repo: &'a GitHubRepositoryRef,
        number: u64,
        cancellation: &'a dyn ProcessCancellation,
    ) -> GitHubFuture<'a, Vec<GitHubComment>> {
        Box::pin(async move {
            self.guarded(cancellation, async {
                validate_repo(repo)?;
                validate_number(number)?;
                let first = self
                    .read_with_retry(cancellation, RateBucket::Core, || async {
                        self.client
                            .issues(repo.owner(), repo.name())
                            .list_comments(number)
                            .per_page(PAGE_SIZE)
                            .send()
                            .await
                    })
                    .await?;
                self.collect_comments(first, cancellation).await
            })
            .await
        })
    }

    fn create_comment<'a>(
        &'a self,
        repo: &'a GitHubRepositoryRef,
        number: u64,
        body: &'a str,
        cancellation: &'a dyn ProcessCancellation,
    ) -> GitHubFuture<'a, GitHubComment> {
        Box::pin(async move {
            self.guarded(cancellation, async {
                validate_repo(repo)?;
                validate_number(number)?;
                validate_string(body, self.policy)?;
                match self
                    .client
                    .issues(repo.owner(), repo.name())
                    .create_comment(number, body)
                    .await
                {
                    Ok(value) => comment_from_model(value, self.policy),
                    Err(error) if transient_octocrab_error(&error) => Err(ambiguous(&error, self)),
                    Err(error) => Err(map_octocrab_error(&error, self)),
                }
            })
            .await
        })
    }

    fn edit_comment<'a>(
        &'a self,
        repo: &'a GitHubRepositoryRef,
        comment_id: u64,
        body: &'a str,
        cancellation: &'a dyn ProcessCancellation,
    ) -> GitHubFuture<'a, GitHubComment> {
        Box::pin(async move {
            self.guarded(cancellation, async {
                validate_repo(repo)?;
                validate_number(comment_id)?;
                validate_string(body, self.policy)?;
                let handler = self.client.issues(repo.owner(), repo.name());
                match handler.update_comment(comment_id.into(), body).await {
                    Ok(value) => comment_from_model(value, self.policy),
                    Err(error) if transient_octocrab_error(&error) => {
                        match handler.get_comment(comment_id.into()).await {
                            Ok(value) if value.body.as_deref() == Some(body) => {
                                comment_from_model(value, self.policy)
                            }
                            Ok(_) => Err(ambiguous(&error, self)),
                            Err(read_error) => Err(map_octocrab_error(&read_error, self)),
                        }
                    }
                    Err(error) => Err(map_octocrab_error(&error, self)),
                }
            })
            .await
        })
    }

    fn delete_comment<'a>(
        &'a self,
        repo: &'a GitHubRepositoryRef,
        comment_id: u64,
        cancellation: &'a dyn ProcessCancellation,
    ) -> GitHubFuture<'a, ()> {
        Box::pin(async move {
            self.guarded(cancellation, async {
                validate_repo(repo)?;
                validate_number(comment_id)?;
                let handler = self.client.issues(repo.owner(), repo.name());
                match handler.delete_comment(comment_id.into()).await {
                    Ok(()) => Ok(()),
                    Err(error) if transient_octocrab_error(&error) => {
                        match handler.get_comment(comment_id.into()).await {
                            Err(read_error) if octocrab_status(&read_error) == Some(404) => Ok(()),
                            Err(read_error) => Err(map_octocrab_error(&read_error, self)),
                            Ok(_) => Err(ambiguous(&error, self)),
                        }
                    }
                    Err(error) => Err(map_octocrab_error(&error, self)),
                }
            })
            .await
        })
    }

    fn list_labels<'a>(
        &'a self,
        repo: &'a GitHubRepositoryRef,
        cancellation: &'a dyn ProcessCancellation,
    ) -> GitHubFuture<'a, Vec<GitHubLabel>> {
        Box::pin(async move {
            self.guarded(cancellation, async {
                validate_repo(repo)?;
                let first = self
                    .read_with_retry(cancellation, RateBucket::Core, || async {
                        self.client
                            .issues(repo.owner(), repo.name())
                            .list_labels_for_repo()
                            .per_page(PAGE_SIZE)
                            .send()
                            .await
                    })
                    .await?;
                self.collect_labels(first, cancellation).await
            })
            .await
        })
    }

    fn create_label<'a>(
        &'a self,
        request: &'a GitHubLabelCreate,
        cancellation: &'a dyn ProcessCancellation,
    ) -> GitHubFuture<'a, GitHubLabel> {
        Box::pin(async move {
            self.guarded(cancellation, async {
                validate_repo(&request.repo)?;
                validate_string(&request.name, self.policy)?;
                validate_label_color(&request.color)?;
                validate_string(&request.description, self.policy)?;
                match self
                    .client
                    .issues(request.repo.owner(), request.repo.name())
                    .create_label(&request.name, &request.color, &request.description)
                    .await
                {
                    Ok(value) => label_from_model(value, self.policy),
                    Err(error) if transient_octocrab_error(&error) => {
                        match self
                            .client
                            .issues(request.repo.owner(), request.repo.name())
                            .get_label(&request.name)
                            .await
                        {
                            Ok(value) => {
                                let current = label_from_model(value, self.policy)?;
                                if current.color.eq_ignore_ascii_case(&request.color)
                                    && current.description == request.description
                                {
                                    Ok(current)
                                } else {
                                    Err(ambiguous(&error, self))
                                }
                            }
                            Err(_) => Err(ambiguous(&error, self)),
                        }
                    }
                    Err(error) => Err(map_octocrab_error(&error, self)),
                }
            })
            .await
        })
    }

    fn add_label<'a>(
        &'a self,
        repository: &'a GitHubRepositoryRef,
        issue_number: u64,
        label_name: &'a str,
        cancel: &'a dyn ProcessCancellation,
    ) -> GitHubFuture<'a, Vec<GitHubLabel>> {
        Box::pin(async move {
            self.guarded(
                cancel,
                self.change_label(repository, issue_number, label_name, true, cancel),
            )
            .await
        })
    }

    fn remove_label<'a>(
        &'a self,
        repository: &'a GitHubRepositoryRef,
        issue_number: u64,
        label_name: &'a str,
        cancel: &'a dyn ProcessCancellation,
    ) -> GitHubFuture<'a, Vec<GitHubLabel>> {
        Box::pin(async move {
            self.guarded(
                cancel,
                self.change_label(repository, issue_number, label_name, false, cancel),
            )
            .await
        })
    }
}

impl OctocrabGitHubService {
    async fn guarded<T, F>(
        &self,
        cancellation: &dyn ProcessCancellation,
        operation: F,
    ) -> Result<T, GitHubOperationError>
    where
        F: Future<Output = Result<T, GitHubOperationError>> + Send,
        T: Send,
    {
        match self.guard_operation(cancellation, operation).await {
            Ok(result) => result,
            Err(GitHubCompletionError::Cancelled) => Err(operation_error(
                GitHubOperationErrorKind::Cancelled,
                "GitHub operation cancelled",
            )),
            Err(GitHubCompletionError::DeadlineExceeded) => Err(operation_error(
                GitHubOperationErrorKind::DeadlineExceeded,
                "GitHub operation deadline exceeded",
            )),
        }
    }

    /// Apply the policy-selected deadline around an issue-list scan.
    ///
    /// Ordinary lists share one 60-second operation deadline. The migration
    /// audit is the documented exhaustive-history exception: each page read is
    /// individually guarded below, while its CLI owner enforces the bounded
    /// three-minute aggregate snapshot deadline.
    async fn guard_issue_list<T, F>(
        &self,
        cancellation: &dyn ProcessCancellation,
        operation: F,
    ) -> Result<T, GitHubOperationError>
    where
        F: Future<Output = Result<T, GitHubOperationError>> + Send,
        T: Send,
    {
        match self.policy.issue_list_timeout_scope() {
            GitHubIssueListTimeoutScope::EntireList => self.guarded(cancellation, operation).await,
            GitHubIssueListTimeoutScope::PerPage => operation.await,
        }
    }

    /// Fetch one issue-list page with its retries inside the ordinary deadline.
    async fn read_issue_page<T, F, Fut>(
        &self,
        cancellation: &dyn ProcessCancellation,
        rate_bucket: RateBucket,
        operation: F,
    ) -> Result<T, GitHubOperationError>
    where
        F: FnMut() -> Fut + Send,
        Fut: Future<Output = octocrab::Result<T>> + Send,
        T: Send,
    {
        self.guarded(
            cancellation,
            self.read_with_retry(cancellation, rate_bucket, operation),
        )
        .await
    }

    async fn read_with_retry<T, F, Fut>(
        &self,
        cancellation: &dyn ProcessCancellation,
        rate_bucket: RateBucket,
        mut operation: F,
    ) -> Result<T, GitHubOperationError>
    where
        F: FnMut() -> Fut + Send,
        Fut: Future<Output = octocrab::Result<T>> + Send,
        T: Send,
    {
        for attempt in 0..READ_ATTEMPTS {
            if cancellation.is_cancelled() {
                return Err(operation_error(
                    GitHubOperationErrorKind::Cancelled,
                    "GitHub operation cancelled",
                ));
            }
            match operation().await {
                Ok(value) => return Ok(value),
                Err(error) if transient_octocrab_error(&error) && attempt + 1 < READ_ATTEMPTS => {
                    let delay = self.retry_delay(&error, rate_bucket, attempt).await;
                    if delay >= self.policy.overall_timeout() {
                        return Err(map_octocrab_error(&error, self));
                    }
                    tokio::time::sleep(delay).await;
                }
                Err(error) => return Err(map_octocrab_error(&error, self)),
            }
        }
        unreachable!("bounded retry loop always returns")
    }

    async fn retry_delay(
        &self,
        error: &octocrab::Error,
        rate_bucket: RateBucket,
        attempt: usize,
    ) -> Duration {
        if let Some(delay) = retry_after_from_error(error) {
            return delay;
        }
        if matches!(octocrab_status(error), Some(403 | 429))
            && let Ok(limits) = self.client.ratelimit().get().await
        {
            let now = SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .unwrap_or_default()
                .as_secs();
            if let Some(delay) = rate_limit_delay(&limits, rate_bucket, now) {
                return delay;
            }
        }
        Duration::from_millis(100 * (attempt as u64 + 1))
    }

    async fn get_issue(
        &self,
        repo: &GitHubRepositoryRef,
        number: u64,
        cancellation: &dyn ProcessCancellation,
    ) -> Result<GitHubIssue, GitHubOperationError> {
        validate_repo(repo)?;
        validate_number(number)?;
        let value = self
            .read_with_retry(cancellation, RateBucket::Core, || async {
                self.client
                    .issues(repo.owner(), repo.name())
                    .get(number)
                    .await
            })
            .await?;
        issue_from_model(value, self.policy)
    }

    async fn collect_issues(
        &self,
        repository: &GitHubRepositoryRef,
        mut page: Page<models::issues::Issue>,
        options: IssueListCollectionOptions,
        rate_bucket: RateBucket,
        cancellation: &dyn ProcessCancellation,
    ) -> Result<GitHubIssueListResult, GitHubOperationError> {
        let mut output = Vec::new();
        let mut scan = GitHubIssueScan::new(options.limit, self.policy);
        let expected_repository_url = format!(
            "https://api.github.com/repos/{}/{}",
            repository.owner(),
            repository.name()
        );
        for page_index in 0..scan.pages_limit() {
            validate_json(&page, self.policy)?;
            let items = page.take_items();
            let count = items.len();
            for (index, value) in items.into_iter().enumerate() {
                // Every raw REST row, pull requests and foreign-repository rows
                // included, counts against the transport item bound; only
                // matching issue rows reach the caller.
                let retain = value.pull_request.is_none()
                    && value.repository_url.as_str() == expected_repository_url;
                if scan.count_row(retain) {
                    output.push(issue_from_list_model(
                        value,
                        self.policy,
                        options.body_mode,
                    )?);
                }
                if let Some(stop) = scan.stop() {
                    let continuation = index + 1 < count || page.next.is_some();
                    return finish_list(
                        output,
                        scan.raw_scanned(),
                        stop,
                        continuation,
                        options.mode,
                    );
                }
            }
            let Some(next) = page.next.clone() else {
                return finish_list(
                    output,
                    scan.raw_scanned(),
                    GitHubListStop::Exhausted,
                    false,
                    options.mode,
                );
            };
            if page_index + 1 == scan.pages_limit() {
                return finish_list(
                    output,
                    scan.raw_scanned(),
                    GitHubListStop::PageLimit,
                    true,
                    options.mode,
                );
            }
            validate_next(&next.to_string())?;
            page = self
                .read_issue_page(cancellation, rate_bucket, || {
                    self.client.get(next.to_string(), None::<&()>)
                })
                .await?;
        }
        finish_list(
            output,
            scan.raw_scanned(),
            GitHubListStop::Exhausted,
            false,
            options.mode,
        )
    }

    async fn collect_comments(
        &self,
        mut page: Page<models::issues::Comment>,
        cancellation: &dyn ProcessCancellation,
    ) -> Result<Vec<GitHubComment>, GitHubOperationError> {
        let mut output = Vec::new();
        for page_index in 0..self.policy.limits().pages() {
            validate_json(&page, self.policy)?;
            for value in page.take_items() {
                if output.len() >= self.policy.limits().items() {
                    return Err(limit_error("GitHub comment item limit exceeded"));
                }
                output.push(comment_from_model(value, self.policy)?);
            }
            let Some(next) = page.next.clone() else {
                return Ok(output);
            };
            if page_index + 1 == self.policy.limits().pages() {
                return Err(limit_error("GitHub pagination page limit exceeded"));
            }
            validate_next(&next.to_string())?;
            page = self
                .read_with_retry(cancellation, RateBucket::Core, || {
                    self.client.get(next.to_string(), None::<&()>)
                })
                .await?;
        }
        Ok(output)
    }

    async fn collect_labels(
        &self,
        mut page: Page<models::Label>,
        cancellation: &dyn ProcessCancellation,
    ) -> Result<Vec<GitHubLabel>, GitHubOperationError> {
        let mut output = Vec::new();
        for page_index in 0..self.policy.limits().pages() {
            validate_json(&page, self.policy)?;
            for value in page.take_items() {
                if output.len() >= self.policy.limits().items() {
                    return Err(limit_error("GitHub label item limit exceeded"));
                }
                output.push(label_from_model(value, self.policy)?);
            }
            let Some(next) = page.next.clone() else {
                return Ok(output);
            };
            if page_index + 1 == self.policy.limits().pages() {
                return Err(limit_error("GitHub pagination page limit exceeded"));
            }
            validate_next(&next.to_string())?;
            page = self
                .read_with_retry(cancellation, RateBucket::Core, || {
                    self.client.get(next.to_string(), None::<&()>)
                })
                .await?;
        }
        Ok(output)
    }

    async fn change_label(
        &self,
        repo: &GitHubRepositoryRef,
        number: u64,
        label: &str,
        add: bool,
        cancellation: &dyn ProcessCancellation,
    ) -> Result<Vec<GitHubLabel>, GitHubOperationError> {
        validate_repo(repo)?;
        validate_number(number)?;
        validate_string(label, self.policy)?;
        let handler = self.client.issues(repo.owner(), repo.name());
        let result = if add {
            handler.add_labels(number, &[label.to_owned()]).await
        } else {
            handler.remove_label(number, label).await
        };
        match result {
            Ok(values) => values
                .into_iter()
                .map(|value| label_from_model(value, self.policy))
                .collect(),
            Err(error) if transient_octocrab_error(&error) => {
                let current = self.get_issue(repo, number, cancellation).await?;
                let present = current.labels.iter().any(|item| item.name == label);
                if present == add {
                    Ok(current.labels)
                } else {
                    Err(ambiguous(&error, self))
                }
            }
            Err(error) => Err(map_octocrab_error(&error, self)),
        }
    }
}

fn validate_repo(repo: &GitHubRepositoryRef) -> Result<(), GitHubOperationError> {
    validate_string(repo.owner(), GitHubTransportPolicy::github_com())?;
    validate_string(repo.name(), GitHubTransportPolicy::github_com())
}

fn validate_number(number: u64) -> Result<(), GitHubOperationError> {
    if number == 0 {
        Err(operation_error(
            GitHubOperationErrorKind::InvalidInput,
            "GitHub numeric identifier must be positive",
        ))
    } else {
        Ok(())
    }
}

fn validate_limit(limit: usize, policy: GitHubTransportPolicy) -> Result<(), GitHubOperationError> {
    if limit == 0 || limit > policy.limits().items() {
        Err(limit_error("GitHub requested item limit is outside policy"))
    } else {
        Ok(())
    }
}

fn validate_string(value: &str, policy: GitHubTransportPolicy) -> Result<(), GitHubOperationError> {
    if value.len() > policy.limits().string_bytes() {
        Err(limit_error("GitHub string limit exceeded"))
    } else {
        Ok(())
    }
}

fn validate_label_color(color: &str) -> Result<(), GitHubOperationError> {
    if color.len() == 6 && color.bytes().all(|byte| byte.is_ascii_hexdigit()) {
        Ok(())
    } else {
        Err(operation_error(
            GitHubOperationErrorKind::InvalidInput,
            "GitHub label color must contain six hexadecimal digits",
        ))
    }
}

fn validate_next(next: &str) -> Result<(), GitHubOperationError> {
    OctocrabGitHubService::continuation_url("https://api.github.com/", next)
        .map(drop)
        .map_err(|error| {
            operation_error(
                GitHubOperationErrorKind::MalformedResponse,
                error.to_string(),
            )
        })
}

fn repository_from_model(
    value: models::Repository,
    policy: GitHubTransportPolicy,
) -> Result<GitHubRepository, GitHubOperationError> {
    validate_json(&value, policy)?;
    let name_with_owner = value
        .full_name
        .ok_or_else(|| malformed("GitHub repository response omitted full_name"))?;
    let url = value
        .html_url
        .ok_or_else(|| malformed("GitHub repository response omitted html_url"))?
        .to_string();
    let default_branch = value
        .default_branch
        .ok_or_else(|| malformed("GitHub repository response omitted default_branch"))?;
    for text in [&name_with_owner, &url, &default_branch] {
        validate_string(text, policy)?;
    }
    Ok(GitHubRepository {
        id: value.id.into_inner(),
        name_with_owner,
        url,
        default_branch,
        private: value.private.unwrap_or(false),
    })
}

fn issue_from_model(
    value: models::issues::Issue,
    policy: GitHubTransportPolicy,
) -> Result<GitHubIssue, GitHubOperationError> {
    issue_from_list_model(value, policy, GitHubIssueBodyMode::Include)
}

/// Convert one REST list row while retaining only the fields its caller needs.
fn issue_from_list_model(
    mut value: models::issues::Issue,
    policy: GitHubTransportPolicy,
    body_mode: GitHubIssueBodyMode,
) -> Result<GitHubIssue, GitHubOperationError> {
    if matches!(body_mode, GitHubIssueBodyMode::Omit) {
        // REST list responses include all three body representations even for
        // metadata-only snapshots. They are untrusted and unused on this path,
        // so discard them before the per-string transport validation below.
        value.body = None;
        value.body_text = None;
        value.body_html = None;
    }
    validate_json(&value, policy)?;
    let body = value.body.unwrap_or_default();
    let state = match value.state {
        models::IssueState::Open => GitHubIssueState::Open,
        models::IssueState::Closed => GitHubIssueState::Closed,
        _ => {
            return Err(malformed(
                "GitHub issue response contained an unknown state",
            ));
        }
    };
    let state_reason = match value.state_reason {
        Some(models::issues::IssueStateReason::Completed) => "COMPLETED",
        Some(models::issues::IssueStateReason::NotPlanned) => "NOT_PLANNED",
        Some(models::issues::IssueStateReason::Reopened) => "REOPENED",
        Some(models::issues::IssueStateReason::Duplicate) => "DUPLICATE",
        Some(_) | None => "",
    }
    .to_owned();
    let labels: Vec<GitHubLabel> = value
        .labels
        .into_iter()
        .map(|label| label_from_model(label, policy))
        .collect::<Result<_, _>>()?;
    let assignees: Vec<String> = value
        .assignees
        .into_iter()
        .map(|assignee| {
            validate_string(&assignee.login, policy)?;
            Ok(assignee.login)
        })
        .collect::<Result<_, GitHubOperationError>>()?;
    let url = value.html_url.to_string();
    for text in [&value.title, &body, &url, &value.user.login] {
        validate_string(text, policy)?;
    }
    Ok(GitHubIssue {
        id: value.id.into_inner(),
        number: value.number,
        title: value.title,
        body,
        state,
        state_reason,
        url,
        author: value.user.login,
        assignees,
        labels,
        comments: value.comments,
        created_at: github_utc_timestamp(&value.created_at),
        closed_at: value
            .closed_at
            .as_ref()
            .map(github_utc_timestamp)
            .unwrap_or_default(),
        updated_at: github_utc_timestamp(&value.updated_at),
        is_pull_request: value.pull_request.is_some(),
    })
}

fn comment_from_model(
    value: models::issues::Comment,
    policy: GitHubTransportPolicy,
) -> Result<GitHubComment, GitHubOperationError> {
    validate_json(&value, policy)?;
    let body = value.body.unwrap_or_default();
    validate_string(&body, policy)?;
    validate_string(&value.user.login, policy)?;
    let url = value.html_url.to_string();
    validate_string(&url, policy)?;
    Ok(GitHubComment {
        id: value.id.into_inner(),
        body,
        url,
        author: value.user.login,
        created_at: github_utc_timestamp(&value.created_at),
        updated_at: github_utc_timestamp(value.updated_at.as_ref().unwrap_or(&value.created_at)),
    })
}

fn label_from_model(
    value: models::Label,
    policy: GitHubTransportPolicy,
) -> Result<GitHubLabel, GitHubOperationError> {
    validate_json(&value, policy)?;
    let description = value.description.unwrap_or_default();
    for text in [&value.name, &value.color, &description] {
        validate_string(text, policy)?;
    }
    Ok(GitHubLabel {
        id: value.id.into_inner(),
        name: value.name,
        color: value.color,
        description,
    })
}

fn issue_matches_edit(issue: &GitHubIssue, request: &GitHubIssueEdit) -> bool {
    request
        .title
        .as_ref()
        .is_none_or(|value| issue.title == *value)
        && request
            .body
            .as_ref()
            .is_none_or(|value| issue.body == *value)
        && request.labels.as_ref().is_none_or(|values| {
            values.len() == issue.labels.len()
                && values
                    .iter()
                    .all(|value| issue.labels.iter().any(|label| label.name == *value))
        })
        && request.assignees.as_ref().is_none_or(|values| {
            values.len() == issue.assignees.len()
                && values.iter().all(|value| issue.assignees.contains(value))
        })
}

fn transient_octocrab_error(error: &octocrab::Error) -> bool {
    matches!(
        octocrab_status(error),
        Some(408 | 429 | 500 | 502 | 503 | 504)
    ) || octocrab_status(error) == Some(403)
        && error
            .to_string()
            .to_ascii_lowercase()
            .contains("rate limit")
        || matches!(
            error,
            octocrab::Error::Service { .. } | octocrab::Error::Hyper { .. }
        )
}

fn map_octocrab_error(
    error: &octocrab::Error,
    service: &OctocrabGitHubService,
) -> GitHubOperationError {
    let status = octocrab_status(error);
    let detail = service.redact_diagnostic(error.to_string());
    let kind = classify_octocrab_kind(octocrab_is_unreachable(error), status, detail.as_str());
    GitHubOperationError::new(kind, status, retry_after_from_error(error), detail.as_str())
}

/// Choose the operation-error kind for one octocrab failure.
///
/// A connection-level failure never carried an HTTP status, so it classifies as
/// `Unreachable` before the status table maps its `None` status to the broader
/// `Transport` class. HTTP 5xx keeps its `Some(5xx)` status and stays
/// `Transport`, so an offline-aware caller retries only the former.
fn classify_octocrab_kind(
    unreachable: bool,
    status: Option<u16>,
    detail: &str,
) -> GitHubOperationErrorKind {
    if unreachable {
        GitHubOperationErrorKind::Unreachable
    } else {
        classify_status(status, detail)
    }
}

fn classify_status(status: Option<u16>, detail: &str) -> GitHubOperationErrorKind {
    let lower = detail.to_ascii_lowercase();
    match status {
        Some(401) => GitHubOperationErrorKind::Authentication,
        Some(403) if lower.contains("sso") || lower.contains("saml") => {
            GitHubOperationErrorKind::SsoRequired
        }
        Some(403) if lower.contains("rate limit") => GitHubOperationErrorKind::RateLimited,
        Some(403) => GitHubOperationErrorKind::Permission,
        Some(404) => GitHubOperationErrorKind::NotFound,
        Some(429) => GitHubOperationErrorKind::RateLimited,
        Some(400..=499) => GitHubOperationErrorKind::InvalidInput,
        Some(500..=599) | None => GitHubOperationErrorKind::Transport,
        Some(_) => GitHubOperationErrorKind::MalformedResponse,
    }
}

fn retry_after_from_error(error: &octocrab::Error) -> Option<Duration> {
    let octocrab::Error::GitHub { source, .. } = error else {
        return None;
    };
    source.errors.as_ref()?.iter().find_map(|value| {
        let object = value.as_object()?;
        let raw = object
            .get("retry_after")
            .or_else(|| object.get("retry_after_seconds"))?;
        let seconds = raw.as_u64().or_else(|| raw.as_str()?.parse().ok())?;
        Some(Duration::from_secs(seconds))
    })
}

fn rate_limit_delay(
    limits: &models::RateLimit,
    bucket: RateBucket,
    now_epoch_seconds: u64,
) -> Option<Duration> {
    let rate = match bucket {
        RateBucket::Core => &limits.resources.core,
        RateBucket::Search => &limits.resources.search,
    };
    (rate.limit > 0 && rate.remaining == 0)
        .then(|| Duration::from_secs(rate.reset.saturating_sub(now_epoch_seconds)))
}

fn ambiguous(error: &octocrab::Error, service: &OctocrabGitHubService) -> GitHubOperationError {
    let detail = service.redact_diagnostic(error.to_string());
    GitHubOperationError::new(
        GitHubOperationErrorKind::AmbiguousMutation,
        octocrab_status(error),
        None,
        format!("GitHub mutation outcome is ambiguous after reconciliation: {detail}"),
    )
}

fn operation_error(
    kind: GitHubOperationErrorKind,
    detail: impl AsRef<str>,
) -> GitHubOperationError {
    GitHubOperationError::new(kind, None, None, detail)
}

fn malformed(detail: impl AsRef<str>) -> GitHubOperationError {
    operation_error(GitHubOperationErrorKind::MalformedResponse, detail)
}
fn limit_error(detail: impl AsRef<str>) -> GitHubOperationError {
    operation_error(GitHubOperationErrorKind::LimitExceeded, detail)
}

/// Resolve a stopped scan, mapping an exhaustive refusal to the typed
/// page-limit error the exhaustive callers already branch on.
fn finish_list(
    issues: Vec<GitHubIssue>,
    raw_rows_scanned: usize,
    stop: GitHubListStop,
    continuation: bool,
    mode: GitHubIssueListMode,
) -> Result<GitHubIssueListResult, GitHubOperationError> {
    match resolve_issue_list(issues, raw_rows_scanned, stop, continuation, mode) {
        GitHubListOutcome::Complete(result) => Ok(result),
        GitHubListOutcome::Refused => Err(limit_error("GitHub pagination page limit exceeded")),
    }
}

fn validate_json<T: Serialize>(
    value: &T,
    policy: GitHubTransportPolicy,
) -> Result<(), GitHubOperationError> {
    let json = serde_json::to_value(value)
        .map_err(|_| malformed("GitHub response could not be normalized"))?;
    let bytes = serde_json::to_vec(&json)
        .map_err(|_| malformed("GitHub response could not be measured"))?;
    if bytes.len() > policy.limits().body_bytes() {
        return Err(limit_error("GitHub response body limit exceeded"));
    }
    if json_depth(&json) > policy.limits().nesting_depth() {
        return Err(limit_error("GitHub response nesting limit exceeded"));
    }
    Ok(())
}

fn json_depth(value: &Value) -> usize {
    match value {
        Value::Array(values) => 1 + values.iter().map(json_depth).max().unwrap_or(0),
        Value::Object(values) => 1 + values.values().map(json_depth).max().unwrap_or(0),
        _ => 1,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::runtime::Cancellation;
    use http_body_util::Full;
    use serde_json::json;
    use std::{
        convert::Infallible,
        io::{Read as _, Write as _},
        net::TcpListener,
        thread,
    };
    use tower::service_fn;

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

    fn service_with_policy(policy: GitHubTransportPolicy) -> OctocrabGitHubService {
        let client = octocrab::OctocrabBuilder::new_empty()
            .with_service(service_fn(|_request: http::Request<octocrab::OctoBody>| {
                std::future::ready(Ok::<_, Infallible>(
                    http::Response::builder()
                        .status(500)
                        .body(Full::new(bytes::Bytes::new()))
                        .expect("unreachable test response"),
                ))
            }))
            .with_auth(octocrab::AuthState::None)
            .build()
            .expect("test client");
        let mut service = OctocrabGitHubService::with_test_client(client);
        service.policy = policy;
        service
    }

    fn comment_json() -> Value {
        let issue = serde_json::to_value(issue_model()).expect("serialize issue fixture");
        json!({
            "id": 11, "node_id": "C_11",
            "url": "https://api.github.com/repos/o/r/issues/comments/11",
            "html_url": "https://github.com/o/r/issues/2#issuecomment-11",
            "body": "comment", "user": issue["user"],
            "created_at": "2026-07-18T00:00:00Z",
            "updated_at": "2026-07-18T01:00:00Z"
        })
    }

    fn response_script(name: &str) -> Vec<(u16, String)> {
        let scripts: Value =
            serde_json::from_str(include_str!("../fixtures/github_response_scripts.json"))
                .expect("valid response scripts");
        let issue = serde_json::to_value(issue_model()).expect("serialize issue fixture");
        let comment = comment_json();
        scripts[name].as_array().expect("named script").iter().map(|row| {
            let status = u16::try_from(row[0].as_u64().expect("status")).expect("u16 status");
            let body = match row[1].as_str().expect("response fixture") {
                "repository" => json!({"id": 1, "name": "r", "full_name": "o/r", "private": true, "html_url": "https://github.com/o/r", "url": "https://api.github.com/repos/o/r", "default_branch": "main"}),
                "issue" => issue.clone(),
                "issues" => json!([issue.clone()]),
                "search" => json!({"total_count": 1, "incomplete_results": false, "items": [issue.clone()]}),
                "comment" => comment.clone(),
                "comments" => json!([comment.clone()]),
                "label" => issue["labels"][0].clone(),
                "labels" => json!([issue["labels"][0].clone()]),
                "failure" => json!({"message": "temporary failure"}),
                "forbidden" => json!({"message": "forbidden"}),
                "empty_array" => json!([]),
                "empty" => return (status, String::new()),
                _ => unreachable!("fixture keys are reviewed"),
            };
            (status, body.to_string())
        }).collect()
    }

    fn issue_model() -> models::issues::Issue {
        serde_json::from_str(include_str!("../fixtures/github_issue.json"))
            .expect("valid parity fixture")
    }

    fn error_kind<T>(result: Result<T, GitHubOperationError>) -> GitHubOperationErrorKind {
        result.err().expect("operation must fail").kind()
    }

    macro_rules! succeeds {
        ($future:expr) => {
            assert!($future.await.is_ok());
        };
    }

    macro_rules! fails {
        ($future:expr, $kind:expr) => {
            assert_eq!(error_kind($future.await), $kind);
        };
    }

    #[test]
    fn conversion_validation_mapping_and_reconciliation_are_typed() {
        use GitHubOperationErrorKind::{
            LimitExceeded, MalformedResponse, NotFound, Permission, RateLimited, SsoRequired,
            Transport, Unreachable,
        };
        assert_eq!(classify_status(Some(403), "SAML SSO"), SsoRequired);
        assert_eq!(classify_status(Some(403), "forbidden"), Permission);
        assert_eq!(classify_status(Some(429), "slow down"), RateLimited);
        assert_eq!(classify_status(Some(200), "invalid"), MalformedResponse);
        // A connection-level failure classifies as Unreachable, while HTTP 5xx,
        // 4xx, and status-less non-connection faults keep their existing kinds
        // so an offline-aware caller retries only the unreachable class.
        assert_eq!(
            classify_octocrab_kind(true, None, "Service Error: connection refused"),
            Unreachable
        );
        assert_eq!(
            classify_octocrab_kind(false, Some(500), "server error"),
            Transport
        );
        assert_eq!(
            classify_octocrab_kind(false, None, "invalid response body"),
            Transport
        );
        assert_eq!(
            classify_octocrab_kind(false, Some(404), "missing"),
            NotFound
        );
        let mut limits = models::RateLimit::default();
        limits.resources.core.limit = 5_000;
        limits.resources.core.remaining = 0;
        limits.resources.core.reset = 110;
        assert_eq!(
            rate_limit_delay(&limits, RateBucket::Core, 100),
            Some(Duration::from_secs(10))
        );
        let policy = GitHubTransportPolicy::github_com();
        assert!(GitHubRepositoryRef::new("../owner", "repo").is_err());
        assert!(GitHubRepositoryRef::new("o".repeat(101), "repo").is_err());
        assert_eq!(
            error_kind(validate_limit(policy.limits().items() + 1, policy)),
            LimitExceeded
        );
        assert_eq!(
            error_kind(validate_string(
                &"x".repeat(policy.limits().string_bytes() + 1),
                policy
            )),
            LimitExceeded
        );
        assert!(validate_next("https://evil.example/issues?page=2").is_err());
        let mut nested = Value::Null;
        for _ in 0..=policy.limits().nesting_depth() {
            nested = Value::Array(vec![nested]);
        }
        assert_eq!(error_kind(validate_json(&nested, policy)), LimitExceeded);
        let mut issue = issue_from_model(issue_model(), policy).expect("fixture converts");
        issue.assignees = vec!["fixture".to_owned()];
        let edit = GitHubIssueEdit {
            repo: GitHubRepositoryRef::new("o", "r").expect("valid repo"),
            number: 2,
            title: Some(issue.title.clone()),
            body: None,
            labels: None,
            assignees: Some(vec!["fixture".to_owned()]),
        };
        assert!(issue_matches_edit(&issue, &edit));
        let different_assignee = GitHubIssueEdit {
            assignees: Some(vec!["other".to_owned()]),
            ..edit
        };
        assert!(!issue_matches_edit(&issue, &different_assignee));
        assert_eq!(issue.number, 2);
        assert_eq!(issue.author, "octocat");
        assert_eq!(issue.labels[0].name, "bug");
        assert_eq!(issue.comments, 3);
        assert!(!issue.is_pull_request);
    }

    #[test]
    fn rest_issue_and_comment_timestamps_use_github_utc_spelling() {
        let policy = GitHubTransportPolicy::github_com();
        let mut closed_issue =
            serde_json::to_value(issue_model()).expect("serialize issue fixture");
        closed_issue["state"] = json!("closed");
        closed_issue["closed_at"] = json!("2026-07-18T02:00:00Z");
        let closed_issue = serde_json::from_value(closed_issue).expect("closed issue fixture");
        let issue = issue_from_model(closed_issue, policy).expect("fixture converts");
        let comment = serde_json::from_value(comment_json()).expect("comment fixture");
        let comment = comment_from_model(comment, policy).expect("fixture converts");

        assert_eq!(issue.created_at, "2026-07-18T00:00:00Z");
        assert_eq!(issue.updated_at, "2026-07-18T01:00:00Z");
        assert_eq!(issue.closed_at, "2026-07-18T02:00:00Z");
        assert_eq!(comment.created_at, "2026-07-18T00:00:00Z");
        assert_eq!(comment.updated_at, "2026-07-18T01:00:00Z");
    }

    #[tokio::test]
    async fn semantic_operations_cover_repository_issue_comment_and_label_parity() {
        let (service, server) = stub_service(response_script("success"));
        let repo = GitHubRepositoryRef::new("o", "r").expect("valid repo");
        let cancellation = Cancellation::new();
        let list = GitHubIssueList {
            repo: repo.clone(),
            state: GitHubIssueState::All,
            labels: vec![String::from("bug")],
            limit: 1,
            mode: GitHubIssueListMode::Exhaustive,
            body_mode: GitHubIssueBodyMode::Include,
        };
        let search = GitHubIssueSearch {
            repo: repo.clone(),
            query: String::from("parity"),
            limit: 1,
        };
        let create = GitHubIssueCreate {
            repo: repo.clone(),
            title: String::from("Parity title"),
            body: String::from("Parity body"),
            assignees: vec![String::from("fixture")],
            labels: vec![String::from("bug")],
        };
        let edit = GitHubIssueEdit {
            repo: repo.clone(),
            number: 2,
            title: Some(String::from("Parity title")),
            body: None,
            labels: None,
            assignees: None,
        };
        let label = GitHubLabelCreate {
            repo: repo.clone(),
            name: String::from("bug"),
            color: String::from("d73a4a"),
            description: String::from("Defect"),
        };
        succeeds!(service.repository(&repo, &cancellation));
        succeeds!(service.issue(&repo, 2, &cancellation));
        succeeds!(service.list_issues(&list, &cancellation));
        succeeds!(service.search_issues(&search, &cancellation));
        succeeds!(service.create_issue(&create, &cancellation));
        succeeds!(service.edit_issue(&edit, &cancellation));
        succeeds!(service.close_issue(&repo, 2, GitHubCloseReason::Completed, &cancellation));
        succeeds!(service.list_comments(&repo, 2, &cancellation));
        succeeds!(service.create_comment(&repo, 2, "comment", &cancellation));
        succeeds!(service.edit_comment(&repo, 11, "comment", &cancellation));
        succeeds!(service.delete_comment(&repo, 11, &cancellation));
        succeeds!(service.list_labels(&repo, &cancellation));
        succeeds!(service.create_label(&label, &cancellation));
        succeeds!(service.add_label(&repo, 2, "bug", &cancellation));
        succeeds!(service.remove_label(&repo, 2, "bug", &cancellation));
        server.join().expect("stub completed");
    }

    #[tokio::test]
    async fn failures_retry_reconcile_and_validate_without_blind_mutation_retries() {
        let (service, server) = stub_service(response_script("failures"));
        let repo = GitHubRepositoryRef::new("o", "r").expect("valid repo");
        let cancellation = Cancellation::new();

        succeeds!(service.issue(&repo, 2, &cancellation));
        let edit = GitHubIssueEdit {
            repo: repo.clone(),
            number: 2,
            title: Some(String::from("Parity title")),
            body: None,
            labels: None,
            assignees: None,
        };
        succeeds!(service.edit_issue(&edit, &cancellation));
        let create = GitHubIssueCreate {
            repo: repo.clone(),
            title: String::from("new"),
            body: String::new(),
            assignees: Vec::new(),
            labels: Vec::new(),
        };
        fails!(
            service.create_issue(&create, &cancellation),
            GitHubOperationErrorKind::AmbiguousMutation
        );
        fails!(
            service.issue(&repo, 2, &cancellation),
            GitHubOperationErrorKind::Permission
        );
        for state in [GitHubIssueState::Open, GitHubIssueState::Closed] {
            let list = GitHubIssueList {
                repo: repo.clone(),
                state,
                labels: Vec::new(),
                limit: 1,
                mode: GitHubIssueListMode::BoundedPartial,
                body_mode: GitHubIssueBodyMode::Include,
            };
            succeeds!(service.list_issues(&list, &cancellation));
        }
        succeeds!(service.close_issue(&repo, 2, GitHubCloseReason::NotPlanned, &cancellation));

        let empty_edit = GitHubIssueEdit {
            repo: repo.clone(),
            number: 2,
            title: None,
            body: None,
            labels: None,
            assignees: None,
        };
        fails!(
            service.edit_issue(&empty_edit, &cancellation),
            GitHubOperationErrorKind::InvalidInput
        );
        let bad_label = GitHubLabelCreate {
            repo: repo.clone(),
            name: String::from("bad"),
            color: String::from("xyz"),
            description: String::new(),
        };
        fails!(
            service.create_label(&bad_label, &cancellation),
            GitHubOperationErrorKind::InvalidInput
        );
        fails!(
            service.issue(&repo, 0, &cancellation),
            GitHubOperationErrorKind::InvalidInput
        );
        let cancelled = Cancellation::new();
        cancelled.cancel();
        fails!(
            service.repository(&repo, &cancelled),
            GitHubOperationErrorKind::Cancelled
        );
        server.join().expect("stub completed");
    }

    #[tokio::test]
    async fn list_issues_returns_a_typed_bounded_result_that_counts_filtered_rows() {
        // One issue row and one pull-request row on a single terminal page: the
        // pull request counts against the raw scan but never reaches the caller,
        // and a feed that ends within every bound is not truncated.
        let issue: Value =
            serde_json::from_str(include_str!("../fixtures/github_issue.json")).expect("fixture");
        let mut pull_request = issue.clone();
        pull_request["pull_request"] = json!({
            "url": "https://api.github.com/repos/o/r/pulls/2",
            "html_url": "https://github.com/o/r/pull/2",
            "diff_url": "https://github.com/o/r/pull/2.diff",
            "patch_url": "https://github.com/o/r/pull/2.patch",
        });
        let body = json!([issue, pull_request]).to_string();
        let (service, server) = stub_service(vec![(200, body)]);
        let repo = GitHubRepositoryRef::new("o", "r").expect("valid repo");
        let cancellation = Cancellation::new();
        let request = GitHubIssueList {
            repo,
            state: GitHubIssueState::All,
            labels: Vec::new(),
            limit: 50,
            mode: GitHubIssueListMode::BoundedPartial,
            body_mode: GitHubIssueBodyMode::Include,
        };
        let result = service
            .list_issues(&request, &cancellation)
            .await
            .expect("list succeeds");
        assert_eq!(result.issues.len(), 1);
        assert_eq!(result.raw_rows_scanned, 2);
        assert!(!result.truncated);
        server.join().expect("stub completed");
    }

    #[tokio::test(start_paused = true)]
    async fn migration_audit_issue_list_allows_per_page_timeouts_within_aggregate_deadline() {
        let service = service_with_policy(GitHubTransportPolicy::migration_audit());
        let cancellation = Cancellation::new();
        let started = tokio::time::Instant::now();

        let result = tokio::time::timeout(
            Duration::from_secs(180),
            Box::pin(service.guard_issue_list(&cancellation, async {
                for _ in 0..2 {
                    service
                        .read_issue_page(&cancellation, RateBucket::Core, || async {
                            tokio::time::sleep(Duration::from_secs(31)).await;
                            Ok::<(), octocrab::Error>(())
                        })
                        .await?;
                }
                Ok::<(), GitHubOperationError>(())
            })),
        )
        .await;

        assert_eq!(result, Ok(Ok(())));
        assert_eq!(
            tokio::time::Instant::now().duration_since(started),
            Duration::from_secs(62)
        );
    }

    #[tokio::test(start_paused = true)]
    async fn migration_audit_issue_page_keeps_the_ordinary_deadline() {
        let service = service_with_policy(GitHubTransportPolicy::migration_audit());
        let cancellation = Cancellation::new();

        let error = Box::pin(service.guard_issue_list(&cancellation, async {
            service
                .read_issue_page(&cancellation, RateBucket::Core, || async {
                    tokio::time::sleep(Duration::from_secs(61)).await;
                    Ok::<(), octocrab::Error>(())
                })
                .await
        }))
        .await
        .expect_err("one slow page must fail before the aggregate deadline");

        assert_eq!(error.kind(), GitHubOperationErrorKind::DeadlineExceeded);
    }

    #[tokio::test(start_paused = true)]
    async fn ordinary_issue_list_keeps_one_overall_deadline() {
        let service = service_with_policy(GitHubTransportPolicy::github_com());
        let cancellation = Cancellation::new();

        let error = Box::pin(service.guard_issue_list(&cancellation, async {
            tokio::time::sleep(Duration::from_secs(61)).await;
            Ok::<(), GitHubOperationError>(())
        }))
        .await
        .expect_err("ordinary issue list must retain its overall deadline");

        assert_eq!(error.kind(), GitHubOperationErrorKind::DeadlineExceeded);
    }
}
