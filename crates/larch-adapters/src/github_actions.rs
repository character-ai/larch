//! Typed GitHub Actions operations over the shared authenticated transport.

use crate::github::{GitHubCompletionError, OctocrabGitHubService};
use bytes::Buf;
use chrono::{DateTime, Utc};
use http::{Response, StatusCode, header};
use http_body::Body;
use http_body_util::BodyExt;
use larch_core::{
    CheckBucket, CheckRun, GitHubActionsError, GitHubActionsErrorKind, GitHubActionsFuture,
    GitHubActionsService, GitHubMutationOutcome, GitHubRepositoryRef, GitHubService,
    ProcessCancellation, WorkflowDispatchRequest, WorkflowJob, WorkflowLogArchive, WorkflowRun,
    WorkflowRunFilters,
};
use serde::Deserialize;
use serde::de::DeserializeOwned;
use std::collections::BTreeSet;
use std::future::Future;
use std::time::{Duration, SystemTime, UNIX_EPOCH};
use url::{Url, form_urlencoded};

const PAGE_SIZE: usize = 100;
const LOG_BYTES: usize = 64 * 1024 * 1024;
const LOG_TIMEOUT: Duration = Duration::from_secs(60);
const LOG_REDIRECTS: usize = 3;
const READ_ATTEMPTS: u32 = 3;

#[derive(Deserialize)]
struct RunsResponse {
    workflow_runs: Vec<RunDto>,
}

#[derive(Clone, Deserialize)]
struct RunDto {
    id: u64,
    status: String,
    conclusion: Option<String>,
    #[serde(default)]
    head_sha: String,
    #[serde(default)]
    event: String,
    #[serde(default = "default_attempt")]
    run_attempt: u32,
}

const fn default_attempt() -> u32 {
    1
}

impl RunDto {
    fn into_core(self) -> WorkflowRun {
        WorkflowRun {
            database_id: self.id,
            status: self.status,
            conclusion: self.conclusion,
            head_sha: self.head_sha,
            event: self.event,
            attempt: self.run_attempt,
        }
    }
}

#[derive(Deserialize)]
struct JobsResponse {
    jobs: Vec<JobDto>,
}

#[derive(Deserialize)]
struct JobDto {
    name: String,
    status: String,
    conclusion: Option<String>,
    started_at: Option<DateTime<Utc>>,
    completed_at: Option<DateTime<Utc>>,
}

impl JobDto {
    fn into_core(self) -> WorkflowJob {
        let wall_clock_seconds =
            self.started_at
                .zip(self.completed_at)
                .and_then(|(started, completed)| {
                    (completed - started)
                        .to_std()
                        .ok()
                        .filter(|duration| !duration.is_zero())
                        .map(|duration| duration.as_secs_f64())
                });
        WorkflowJob {
            name: self.name,
            status: self.status,
            conclusion: self.conclusion,
            wall_clock_seconds,
        }
    }
}

#[derive(Deserialize)]
struct ChecksResponse {
    check_runs: Vec<CheckDto>,
}

#[derive(Deserialize)]
struct CheckDto {
    name: String,
    status: String,
    conclusion: Option<String>,
}

impl CheckDto {
    fn into_core(self) -> CheckRun {
        let bucket = check_bucket(&self.status, self.conclusion.as_deref());
        CheckRun {
            name: self.name,
            status: self.status,
            conclusion: self.conclusion,
            bucket,
        }
    }
}

fn check_bucket(status: &str, conclusion: Option<&str>) -> CheckBucket {
    if status != "completed" {
        return CheckBucket::Pending;
    }
    match conclusion {
        Some("success") => CheckBucket::Pass,
        Some("cancelled") => CheckBucket::Cancel,
        Some("failure" | "timed_out" | "action_required" | "startup_failure") => CheckBucket::Fail,
        Some("skipped" | "neutral") => CheckBucket::Skipping,
        _ => CheckBucket::Pending,
    }
}

impl GitHubActionsService for OctocrabGitHubService {
    fn list_workflow_runs<'service>(
        &'service self,
        repository: &'service GitHubRepositoryRef,
        filters: &'service WorkflowRunFilters,
        cancellation: &'service dyn ProcessCancellation,
    ) -> GitHubActionsFuture<'service, Vec<WorkflowRun>> {
        Box::pin(async move {
            self.with_cancellation(cancellation, self.list_runs(repository, filters))
                .await
        })
    }

    fn workflow_run<'service>(
        &'service self,
        repository: &'service GitHubRepositoryRef,
        run_id: u64,
        cancellation: &'service dyn ProcessCancellation,
    ) -> GitHubActionsFuture<'service, WorkflowRun> {
        Box::pin(self.with_cancellation(cancellation, async move {
            require_positive_id(run_id)?;
            let route = format!("{}/actions/runs/{run_id}", repository_route(repository));
            let run: RunDto = self.read_json(&route).await?;
            validate_run(self, &run)?;
            Ok(run.into_core())
        }))
    }

    fn workflow_jobs<'service>(
        &'service self,
        repository: &'service GitHubRepositoryRef,
        run_id: u64,
        cancellation: &'service dyn ProcessCancellation,
    ) -> GitHubActionsFuture<'service, Vec<WorkflowJob>> {
        Box::pin(async move {
            self.with_cancellation(cancellation, self.list_jobs(repository, run_id))
                .await
        })
    }

    fn check_runs<'service>(
        &'service self,
        repository: &'service GitHubRepositoryRef,
        git_reference: &'service str,
        cancellation: &'service dyn ProcessCancellation,
    ) -> GitHubActionsFuture<'service, Vec<CheckRun>> {
        Box::pin(async move {
            self.with_cancellation(cancellation, self.list_checks(repository, git_reference))
                .await
        })
    }

    fn rerun_workflow<'service>(
        &'service self,
        repository: &'service GitHubRepositoryRef,
        run_id: u64,
        failed_only: bool,
        cancellation: &'service dyn ProcessCancellation,
    ) -> GitHubActionsFuture<'service, GitHubMutationOutcome> {
        Box::pin(self.with_cancellation(cancellation, async move {
            require_positive_id(run_id)?;
            let _guard = self.mutation_lock.lock().await;
            let before =
                GitHubActionsService::workflow_run(self, repository, run_id, cancellation).await?;
            let suffix = if failed_only {
                "rerun-failed-jobs"
            } else {
                "rerun"
            };
            let route = format!(
                "{}/actions/runs/{run_id}/{suffix}",
                repository_route(repository)
            );
            match self.post_mutation(&route, StatusCode::CREATED).await? {
                MutationAttempt::Accepted => Ok(GitHubMutationOutcome::Accepted),
                MutationAttempt::Uncertain(delay) => {
                    wait_for_rate_limit(delay).await;
                    let after =
                        GitHubActionsService::workflow_run(self, repository, run_id, cancellation)
                            .await?;
                    Ok(if after.attempt > before.attempt {
                        GitHubMutationOutcome::Reconciled
                    } else {
                        GitHubMutationOutcome::Ambiguous
                    })
                }
            }
        }))
    }

    fn dispatch_workflow<'service>(
        &'service self,
        request: &'service WorkflowDispatchRequest,
        cancellation: &'service dyn ProcessCancellation,
    ) -> GitHubActionsFuture<'service, GitHubMutationOutcome> {
        Box::pin(self.with_cancellation(cancellation, async move {
            let repository = &request.repository;
            let workflow = &request.workflow;
            let git_reference = &request.git_reference;
            validate_selector(workflow, "workflow")?;
            validate_selector(git_reference, "Git reference")?;
            let _guard = self.mutation_lock.lock().await;
            let filters = WorkflowRunFilters {
                branch: Some(git_reference.to_owned()),
                workflow: Some(workflow.to_owned()),
                event: Some(String::from("workflow_dispatch")),
                limit: 1,
                ..WorkflowRunFilters::default()
            };
            let before = self.list_runs(repository, &filters).await?;
            let route = format!(
                "{}/actions/workflows/{}/dispatches",
                repository_route(repository),
                encode_path_segment(workflow)
            );
            let body = serde_json::json!({"ref": git_reference});
            match self
                .post_json_mutation(&route, &body, StatusCode::NO_CONTENT)
                .await?
            {
                MutationAttempt::Accepted => Ok(GitHubMutationOutcome::Accepted),
                MutationAttempt::Uncertain(delay) => {
                    wait_for_rate_limit(delay).await;
                    let after = self.list_runs(repository, &filters).await?;
                    Ok(if latest_run_id(&after) == latest_run_id(&before) {
                        GitHubMutationOutcome::Ambiguous
                    } else {
                        GitHubMutationOutcome::Reconciled
                    })
                }
            }
        }))
    }

    fn download_workflow_logs<'service>(
        &'service self,
        repository: &'service GitHubRepositoryRef,
        run_id: u64,
        cancellation: &'service dyn ProcessCancellation,
    ) -> GitHubActionsFuture<'service, WorkflowLogArchive> {
        Box::pin(self.with_cancellation(cancellation, async move {
            require_positive_id(run_id)?;
            tokio::time::timeout(LOG_TIMEOUT, self.download_logs(repository, run_id))
                .await
                .map_err(|_| {
                    self.error(
                        GitHubActionsErrorKind::DeadlineExceeded,
                        "GitHub workflow log download exceeded its time limit",
                    )
                })?
        }))
    }
}

impl OctocrabGitHubService {
    async fn with_cancellation<T, F>(
        &self,
        cancellation: &dyn ProcessCancellation,
        operation: F,
    ) -> Result<T, GitHubActionsError>
    where
        F: Future<Output = Result<T, GitHubActionsError>> + Send,
        T: Send,
    {
        match self.guard_operation(cancellation, operation).await {
            Ok(result) => result,
            Err(GitHubCompletionError::Cancelled) => Err(self.error(
                GitHubActionsErrorKind::Cancelled,
                "GitHub Actions operation cancelled",
            )),
            Err(GitHubCompletionError::DeadlineExceeded) => Err(self.error(
                GitHubActionsErrorKind::DeadlineExceeded,
                "GitHub Actions operation exceeded its time limit",
            )),
        }
    }

    async fn list_runs(
        &self,
        repository: &GitHubRepositoryRef,
        filters: &WorkflowRunFilters,
    ) -> Result<Vec<WorkflowRun>, GitHubActionsError> {
        validate_filters(filters)?;
        let requested = filters
            .effective_limit()
            .min(self.transport_policy().limits().items());
        let mut runs = Vec::with_capacity(requested.min(PAGE_SIZE));
        for page in 1..=self.transport_policy().limits().pages() {
            let route = runs_route(repository, filters, page, requested - runs.len());
            let response: RunsResponse = self.read_json(&route).await?;
            let count = response.workflow_runs.len();
            for run in response.workflow_runs {
                validate_run(self, &run)?;
                runs.push(run.into_core());
                if runs.len() == requested {
                    return Ok(runs);
                }
            }
            if count < PAGE_SIZE {
                return Ok(runs);
            }
        }
        if runs.len() < requested {
            return Err(self.error(
                GitHubActionsErrorKind::Response,
                "GitHub workflow run pagination exceeded its page limit",
            ));
        }
        Ok(runs)
    }

    async fn list_jobs(
        &self,
        repository: &GitHubRepositoryRef,
        run_id: u64,
    ) -> Result<Vec<WorkflowJob>, GitHubActionsError> {
        require_positive_id(run_id)?;
        let mut jobs = Vec::new();
        for page in 1..=self.transport_policy().limits().pages() {
            let route = format!(
                "{}/actions/runs/{run_id}/jobs?filter=latest&per_page={PAGE_SIZE}&page={page}",
                repository_route(repository)
            );
            let response: JobsResponse = self.read_json(&route).await?;
            let count = response.jobs.len();
            for job in response.jobs {
                validate_string(self, &job.name, "workflow job name")?;
                validate_string(self, &job.status, "workflow job status")?;
                validate_optional_string(
                    self,
                    job.conclusion.as_deref(),
                    "workflow job conclusion",
                )?;
                jobs.push(job.into_core());
                if jobs.len() == self.transport_policy().limits().items() {
                    return Ok(jobs);
                }
            }
            if count < PAGE_SIZE {
                return Ok(jobs);
            }
        }
        Err(self.error(
            GitHubActionsErrorKind::Response,
            "GitHub workflow job pagination exceeded its page limit",
        ))
    }

    async fn list_checks(
        &self,
        repository: &GitHubRepositoryRef,
        git_reference: &str,
    ) -> Result<Vec<CheckRun>, GitHubActionsError> {
        validate_selector(git_reference, "Git reference")?;
        let mut checks = Vec::new();
        for page in 1..=self.transport_policy().limits().pages() {
            let route = format!(
                "{}/commits/{}/check-runs?filter=latest&per_page={PAGE_SIZE}&page={page}",
                repository_route(repository),
                encode_path_segment(git_reference)
            );
            let response: ChecksResponse = self.read_json(&route).await?;
            let count = response.check_runs.len();
            for check in response.check_runs {
                validate_string(self, &check.name, "check run name")?;
                validate_string(self, &check.status, "check run status")?;
                validate_optional_string(
                    self,
                    check.conclusion.as_deref(),
                    "check run conclusion",
                )?;
                checks.push(check.into_core());
                if checks.len() == self.transport_policy().limits().items() {
                    return Ok(checks);
                }
            }
            if count < PAGE_SIZE {
                return Ok(checks);
            }
        }
        Err(self.error(
            GitHubActionsErrorKind::Response,
            "GitHub check run pagination exceeded its page limit",
        ))
    }

    async fn read_json<T: DeserializeOwned>(&self, route: &str) -> Result<T, GitHubActionsError> {
        for attempt in 1..=READ_ATTEMPTS {
            let response = match self.client()._get(route).await {
                Ok(response) => response,
                Err(error) if attempt == READ_ATTEMPTS => {
                    return Err(self.error(GitHubActionsErrorKind::Transport, error.to_string()));
                }
                Err(_) => {
                    tokio::time::sleep(read_backoff(attempt, None)).await;
                    continue;
                }
            };
            let status = response.status();
            if transient_read_status(status, response.headers()) && attempt < READ_ATTEMPTS {
                let delay = retry_delay(response.headers());
                drop(response);
                tokio::time::sleep(read_backoff(attempt, delay)).await;
                continue;
            }
            if !status.is_success() {
                return Err(self.status_error(status, response.headers()));
            }
            require_content_type(self, response.headers(), &["application/json"])?;
            let bytes = collect_bounded(
                response.into_body(),
                self.transport_policy().limits().body_bytes(),
                GitHubActionsErrorKind::Response,
            )
            .await?;
            if !json_depth_within(&bytes, self.transport_policy().limits().nesting_depth()) {
                return Err(self.error(
                    GitHubActionsErrorKind::Response,
                    "GitHub JSON response exceeds its nesting limit",
                ));
            }
            return serde_json::from_slice(&bytes)
                .map_err(|error| self.error(GitHubActionsErrorKind::Response, error.to_string()));
        }
        unreachable!("bounded read retry loop returns on every terminal state")
    }

    async fn post_mutation(
        &self,
        route: &str,
        expected: StatusCode,
    ) -> Result<MutationAttempt, GitHubActionsError> {
        let Ok(response) = self.client()._post(route, None::<&()>).await else {
            return Ok(MutationAttempt::Uncertain(None));
        };
        mutation_response(self, &response, expected)
    }

    async fn post_json_mutation<T: serde::Serialize + Sync + ?Sized>(
        &self,
        route: &str,
        body: &T,
        expected: StatusCode,
    ) -> Result<MutationAttempt, GitHubActionsError> {
        let Ok(response) = self.client()._post(route, Some(body)).await else {
            return Ok(MutationAttempt::Uncertain(None));
        };
        mutation_response(self, &response, expected)
    }

    async fn download_logs(
        &self,
        repository: &GitHubRepositoryRef,
        run_id: u64,
    ) -> Result<WorkflowLogArchive, GitHubActionsError> {
        let route = format!(
            "{}/actions/runs/{run_id}/logs",
            repository_route(repository)
        );
        let mut response =
            self.client()._get(&route).await.map_err(|error| {
                self.error(GitHubActionsErrorKind::Transport, error.to_string())
            })?;
        let mut current = Url::parse(&format!("https://api.github.com{route}"))
            .expect("repository route is a valid fixed API URL");
        let mut visited = BTreeSet::from([current.as_str().to_owned()]);
        for redirects in 0..=LOG_REDIRECTS {
            if !response.status().is_redirection() {
                if !response.status().is_success() {
                    return Err(self.status_error(response.status(), response.headers()));
                }
                require_content_type(
                    self,
                    response.headers(),
                    &["application/zip", "application/octet-stream"],
                )?;
                let expected_length = content_length(response.headers())?;
                if expected_length.is_some_and(|length| length > LOG_BYTES) {
                    return Err(self.error(
                        GitHubActionsErrorKind::LogLimit,
                        "GitHub workflow log archive exceeds its byte limit",
                    ));
                }
                let bytes = collect_bounded(
                    response.into_body(),
                    LOG_BYTES,
                    GitHubActionsErrorKind::LogLimit,
                )
                .await?;
                if expected_length.is_some_and(|length| length != bytes.len()) {
                    return Err(self.error(
                        GitHubActionsErrorKind::LogLimit,
                        "GitHub workflow log archive ended before its declared length",
                    ));
                }
                return Ok(WorkflowLogArchive::new(bytes));
            }
            if redirects == LOG_REDIRECTS {
                return Err(self.error(
                    GitHubActionsErrorKind::Redirect,
                    "GitHub workflow log redirect limit exceeded",
                ));
            }
            let location = response
                .headers()
                .get(header::LOCATION)
                .ok_or_else(|| {
                    self.error(
                        GitHubActionsErrorKind::Redirect,
                        "GitHub workflow log redirect omitted Location",
                    )
                })?
                .to_str()
                .map_err(|_| {
                    self.error(
                        GitHubActionsErrorKind::Redirect,
                        "GitHub workflow log redirect Location is invalid",
                    )
                })?;
            let next = validate_log_redirect(&current, location, &visited)?;
            visited.insert(next.as_str().to_owned());
            current = next;
            response = self
                .client()
                ._get(current.as_str())
                .await
                .map_err(|error| {
                    self.error(GitHubActionsErrorKind::Transport, error.to_string())
                })?;
        }
        unreachable!("bounded redirect loop returns on every terminal state")
    }

    fn status_error(&self, status: StatusCode, headers: &http::HeaderMap) -> GitHubActionsError {
        let kind = match status {
            StatusCode::UNAUTHORIZED | StatusCode::FORBIDDEN if !rate_limited(status, headers) => {
                GitHubActionsErrorKind::Authorization
            }
            StatusCode::TOO_MANY_REQUESTS | StatusCode::FORBIDDEN => {
                GitHubActionsErrorKind::RateLimited
            }
            _ => GitHubActionsErrorKind::Response,
        };
        let retry_after = retry_delay(headers)
            .map_or_else(|| String::from("none"), |delay| delay.as_secs().to_string());
        self.error(
            kind,
            format!("GitHub returned HTTP {status}; retry-after={retry_after}"),
        )
    }

    fn error(&self, kind: GitHubActionsErrorKind, detail: impl AsRef<str>) -> GitHubActionsError {
        let safe = self.redact_diagnostic(detail);
        GitHubActionsError::new(kind, safe.as_str())
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum MutationAttempt {
    Accepted,
    Uncertain(Option<Duration>),
}

fn mutation_response<B>(
    service: &OctocrabGitHubService,
    response: &Response<B>,
    expected: StatusCode,
) -> Result<MutationAttempt, GitHubActionsError> {
    if response.status() == expected {
        return Ok(MutationAttempt::Accepted);
    }
    if matches!(
        response.status(),
        StatusCode::REQUEST_TIMEOUT
            | StatusCode::TOO_MANY_REQUESTS
            | StatusCode::INTERNAL_SERVER_ERROR
            | StatusCode::BAD_GATEWAY
            | StatusCode::SERVICE_UNAVAILABLE
            | StatusCode::GATEWAY_TIMEOUT
    ) || rate_limited(response.status(), response.headers())
    {
        return Ok(MutationAttempt::Uncertain(retry_delay(response.headers())));
    }
    Err(service.status_error(response.status(), response.headers()))
}

fn rate_limited(status: StatusCode, headers: &http::HeaderMap) -> bool {
    status == StatusCode::TOO_MANY_REQUESTS
        || headers.contains_key(header::RETRY_AFTER)
        || headers
            .get("x-ratelimit-remaining")
            .is_some_and(|value| value == "0")
}

fn transient_read_status(status: StatusCode, headers: &http::HeaderMap) -> bool {
    matches!(
        status,
        StatusCode::REQUEST_TIMEOUT
            | StatusCode::TOO_MANY_REQUESTS
            | StatusCode::INTERNAL_SERVER_ERROR
            | StatusCode::BAD_GATEWAY
            | StatusCode::SERVICE_UNAVAILABLE
            | StatusCode::GATEWAY_TIMEOUT
    ) || rate_limited(status, headers)
}

fn retry_delay(headers: &http::HeaderMap) -> Option<Duration> {
    let retry_after = headers
        .get(header::RETRY_AFTER)
        .and_then(|value| value.to_str().ok())
        .and_then(|value| value.parse::<u64>().ok())
        .map(Duration::from_secs);
    if retry_after.is_some() {
        return retry_after;
    }
    let reset = headers
        .get("x-ratelimit-reset")?
        .to_str()
        .ok()?
        .parse::<u64>()
        .ok()?;
    let now = SystemTime::now().duration_since(UNIX_EPOCH).ok()?.as_secs();
    Some(Duration::from_secs(reset.saturating_sub(now)))
}

fn read_backoff(attempt: u32, requested: Option<Duration>) -> Duration {
    requested
        .unwrap_or_else(|| Duration::from_millis(u64::from(attempt) * 100))
        .min(LOG_TIMEOUT)
}

async fn wait_for_rate_limit(delay: Option<Duration>) {
    if let Some(delay) = delay {
        tokio::time::sleep(delay.min(LOG_TIMEOUT)).await;
    }
}

async fn collect_bounded<B>(
    mut body: B,
    limit: usize,
    kind: GitHubActionsErrorKind,
) -> Result<Vec<u8>, GitHubActionsError>
where
    B: Body + Unpin,
    B::Data: Buf,
{
    let mut output = Vec::new();
    while let Some(frame) = body.frame().await {
        let frame = frame
            .map_err(|_| GitHubActionsError::new(kind, "GitHub response body stream failed"))?;
        let Ok(mut data) = frame.into_data() else {
            continue;
        };
        if data.remaining() > limit.saturating_sub(output.len()) {
            return Err(GitHubActionsError::new(
                kind,
                "GitHub response exceeded its byte limit",
            ));
        }
        let length = data.remaining();
        output.extend_from_slice(&data.copy_to_bytes(length));
    }
    Ok(output)
}

fn json_depth_within(bytes: &[u8], limit: usize) -> bool {
    let mut depth = 0_usize;
    let mut in_string = false;
    let mut escaped = false;
    for byte in bytes {
        if in_string {
            if escaped {
                escaped = false;
            } else if *byte == b'\\' {
                escaped = true;
            } else if *byte == b'"' {
                in_string = false;
            }
            continue;
        }
        match byte {
            b'"' => in_string = true,
            b'{' | b'[' => {
                depth += 1;
                if depth > limit {
                    return false;
                }
            }
            b'}' | b']' => depth = depth.saturating_sub(1),
            _ => {}
        }
    }
    true
}

fn runs_route(
    repository: &GitHubRepositoryRef,
    filters: &WorkflowRunFilters,
    page: usize,
    remaining: usize,
) -> String {
    let workflow = filters
        .workflow
        .as_ref()
        .map(|value| format!("/workflows/{}", encode_path_segment(value)))
        .unwrap_or_default();
    let mut query = form_urlencoded::Serializer::new(String::new());
    query.append_pair("per_page", &remaining.min(PAGE_SIZE).to_string());
    query.append_pair("page", &page.to_string());
    for (name, value) in [
        ("branch", filters.branch.as_deref()),
        ("event", filters.event.as_deref()),
        ("status", filters.status.as_deref()),
        ("head_sha", filters.commit.as_deref()),
    ] {
        if let Some(value) = value {
            query.append_pair(name, value);
        }
    }
    format!(
        "{}/actions{workflow}/runs?{}",
        repository_route(repository),
        query.finish()
    )
}

fn repository_route(repository: &GitHubRepositoryRef) -> String {
    format!("/repos/{}/{}", repository.owner(), repository.name())
}

fn encode_path_segment(value: &str) -> String {
    form_urlencoded::byte_serialize(value.as_bytes()).collect()
}

fn validate_selector(value: &str, label: &str) -> Result<(), GitHubActionsError> {
    if value.is_empty() || value.len() > 255 || value.bytes().any(|byte| byte.is_ascii_control()) {
        return Err(GitHubActionsError::new(
            GitHubActionsErrorKind::InvalidInput,
            format!("GitHub {label} is invalid"),
        ));
    }
    Ok(())
}

fn require_positive_id(value: u64) -> Result<(), GitHubActionsError> {
    if value == 0 {
        Err(GitHubActionsError::new(
            GitHubActionsErrorKind::InvalidInput,
            "GitHub numeric identifier must be positive",
        ))
    } else {
        Ok(())
    }
}

fn validate_run(service: &OctocrabGitHubService, run: &RunDto) -> Result<(), GitHubActionsError> {
    validate_string(service, &run.status, "workflow run status")?;
    validate_optional_string(
        service,
        run.conclusion.as_deref(),
        "workflow run conclusion",
    )?;
    validate_string(service, &run.head_sha, "workflow run head SHA")?;
    validate_string(service, &run.event, "workflow run event")
}

fn validate_optional_string(
    service: &OctocrabGitHubService,
    value: Option<&str>,
    label: &str,
) -> Result<(), GitHubActionsError> {
    value.map_or(Ok(()), |value| validate_string(service, value, label))
}

fn validate_filters(filters: &WorkflowRunFilters) -> Result<(), GitHubActionsError> {
    for (label, value) in [
        ("branch", filters.branch.as_deref()),
        ("workflow", filters.workflow.as_deref()),
        ("event", filters.event.as_deref()),
        ("status", filters.status.as_deref()),
        ("commit", filters.commit.as_deref()),
    ] {
        if let Some(value) = value {
            validate_selector(value, label)?;
        }
    }
    Ok(())
}

fn validate_string(
    service: &OctocrabGitHubService,
    value: &str,
    label: &str,
) -> Result<(), GitHubActionsError> {
    if value.len() > service.transport_policy().limits().string_bytes() {
        return Err(service.error(
            GitHubActionsErrorKind::Response,
            format!("GitHub {label} exceeds its byte limit"),
        ));
    }
    Ok(())
}

fn latest_run_id(runs: &[WorkflowRun]) -> Option<u64> {
    runs.first().map(|run| run.database_id)
}

fn require_content_type(
    service: &OctocrabGitHubService,
    headers: &http::HeaderMap,
    allowed: &[&str],
) -> Result<(), GitHubActionsError> {
    let content_type = headers
        .get(header::CONTENT_TYPE)
        .and_then(|value| value.to_str().ok())
        .and_then(|value| value.split(';').next())
        .map(str::trim);
    if content_type.is_some_and(|value| allowed.contains(&value)) {
        Ok(())
    } else {
        Err(service.error(
            GitHubActionsErrorKind::Response,
            "GitHub response content type is not allowed for this operation",
        ))
    }
}

fn content_length(headers: &http::HeaderMap) -> Result<Option<usize>, GitHubActionsError> {
    headers
        .get(header::CONTENT_LENGTH)
        .map(|value| {
            value
                .to_str()
                .ok()
                .and_then(|value| value.parse().ok())
                .ok_or_else(|| {
                    GitHubActionsError::new(
                        GitHubActionsErrorKind::Response,
                        "GitHub workflow log Content-Length is invalid",
                    )
                })
        })
        .transpose()
}

fn validate_log_redirect(
    current: &Url,
    location: &str,
    visited: &BTreeSet<String>,
) -> Result<Url, GitHubActionsError> {
    let next = current.join(location).map_err(|_| {
        GitHubActionsError::new(
            GitHubActionsErrorKind::Redirect,
            "GitHub workflow log redirect URL is invalid",
        )
    })?;
    let host = next.host_str().unwrap_or_default();
    let approved = next.scheme() == "https"
        && next.port_or_known_default() == Some(443)
        && next.username().is_empty()
        && next.password().is_none()
        && next.fragment().is_none()
        && approved_log_host(host);
    if !approved {
        return Err(GitHubActionsError::new(
            GitHubActionsErrorKind::Redirect,
            "GitHub workflow log redirect origin is not approved",
        ));
    }
    if visited.contains(next.as_str()) {
        return Err(GitHubActionsError::new(
            GitHubActionsErrorKind::Redirect,
            "GitHub workflow log redirect loop detected",
        ));
    }
    Ok(next)
}

fn approved_log_host(host: &str) -> bool {
    if host
        .strip_suffix(".actions.githubusercontent.com")
        .is_some_and(|prefix| !prefix.is_empty())
    {
        return true;
    }
    host.strip_suffix(".blob.core.windows.net")
        .and_then(|prefix| prefix.strip_prefix("productionresultssa"))
        .is_some_and(|suffix| {
            !suffix.is_empty() && suffix.bytes().all(|byte| byte.is_ascii_digit())
        })
}

#[cfg(test)]
mod tests {
    use super::*;
    use http_body_util::Full;
    use std::collections::VecDeque;
    use std::convert::Infallible;
    use std::sync::{Arc, Mutex as StdMutex};
    use tower::service_fn;

    fn repository() -> GitHubRepositoryRef {
        GitHubRepositoryRef::new("octo-org", "octo-repo").expect("repository")
    }

    fn queued_service(responses: Vec<Response<Full<bytes::Bytes>>>) -> OctocrabGitHubService {
        let responses = Arc::new(StdMutex::new(VecDeque::from(responses)));
        let client = octocrab::OctocrabBuilder::new_empty()
            .with_service(service_fn(
                move |_request: http::Request<octocrab::OctoBody>| {
                    let response = responses.lock().expect("response queue").pop_front();
                    std::future::ready(Ok::<_, Infallible>(response.expect("queued response")))
                },
            ))
            .with_auth(octocrab::AuthState::None)
            .build()
            .expect("test client");
        OctocrabGitHubService::with_test_client(client)
    }

    fn response(
        status: u16,
        content_type: &str,
        body: &'static str,
    ) -> Response<Full<bytes::Bytes>> {
        Response::builder()
            .status(status)
            .header(header::CONTENT_TYPE, content_type)
            .body(Full::new(bytes::Bytes::from_static(body.as_bytes())))
            .expect("response")
    }

    #[test]
    fn actions_port_exercises_successful_offline_operations() {
        const RUN: &str = r#"{"id":1,"status":"completed","conclusion":"success","head_sha":"abc","event":"push","run_attempt":1}"#;
        const RUNS: &str = r#"{"workflow_runs":[{"id":1,"status":"completed","conclusion":"success","head_sha":"abc","event":"push","run_attempt":1}]}"#;
        let json = "application/json";
        let responses = vec![
            response(200, json, RUNS),
            response(200, json, RUN),
            response(
                200,
                json,
                r#"{"jobs":[{"name":"job","status":"completed","conclusion":"success","started_at":null,"completed_at":null}]}"#,
            ),
            response(
                200,
                json,
                r#"{"check_runs":[{"name":"check","status":"completed","conclusion":"success"}]}"#,
            ),
            response(200, json, RUN),
            response(201, json, ""),
            response(200, json, RUNS),
            response(204, json, ""),
            response(200, "application/zip", "ZIP"),
        ];
        let runtime = crate::runtime::LarchRuntime::new().expect("runtime");
        runtime.block_on(async move {
            let s = queued_service(responses);
            let r = repository();
            let c = crate::runtime::Cancellation::new();
            let f = WorkflowRunFilters::default();
            assert_eq!(
                s.list_workflow_runs(&r, &f, &c).await.expect("runs").len(),
                1
            );
            assert_eq!(s.workflow_run(&r, 1, &c).await.expect("run").database_id, 1);
            assert_eq!(s.workflow_jobs(&r, 1, &c).await.expect("jobs").len(), 1);
            assert_eq!(s.check_runs(&r, "abc", &c).await.expect("checks").len(), 1);
            assert_eq!(
                s.rerun_workflow(&r, 1, false, &c).await.expect("rerun"),
                GitHubMutationOutcome::Accepted
            );
            let dispatch = WorkflowDispatchRequest {
                repository: r.clone(),
                workflow: String::from("ci.yml"),
                git_reference: String::from("main"),
            };
            assert_eq!(
                s.dispatch_workflow(&dispatch, &c).await.expect("dispatch"),
                GitHubMutationOutcome::Accepted
            );
            assert_eq!(
                s.download_workflow_logs(&r, 1, &c)
                    .await
                    .expect("logs")
                    .as_bytes(),
                b"ZIP"
            );
        });
    }

    #[test]
    fn run_filters_preserve_every_current_filter_and_bound_page_size() {
        let route = runs_route(
            &repository(),
            &WorkflowRunFilters {
                branch: Some(String::from("topic/name")),
                workflow: Some(String::from("ci check.yml")),
                event: Some(String::from("pull_request")),
                status: Some(String::from("in_progress")),
                commit: Some(String::from("abc123")),
                limit: 500,
            },
            2,
            400,
        );
        assert_eq!(
            route,
            "/repos/octo-org/octo-repo/actions/workflows/ci+check.yml/runs?per_page=100&page=2&branch=topic%2Fname&event=pull_request&status=in_progress&head_sha=abc123"
        );
        assert!(validate_selector("", "workflow").is_err());
        assert!(require_positive_id(0).is_err());
    }

    #[test]
    fn check_classification_retains_blocking_and_nonblocking_buckets() {
        assert_eq!(check_bucket("queued", None), CheckBucket::Pending);
        assert_eq!(
            check_bucket("completed", Some("failure")),
            CheckBucket::Fail
        );
        assert_eq!(
            check_bucket("completed", Some("timed_out")),
            CheckBucket::Fail
        );
        assert_eq!(
            check_bucket("completed", Some("skipped")),
            CheckBucket::Skipping
        );
        assert_eq!(
            check_bucket("completed", Some("success")),
            CheckBucket::Pass
        );
        assert_eq!(
            check_bucket("completed", Some("cancelled")),
            CheckBucket::Cancel
        );
        assert_eq!(
            check_bucket("completed", Some("stale")),
            CheckBucket::Pending
        );
    }

    #[test]
    fn jobs_preserve_failure_and_positive_wall_clock_classification() {
        let failed: JobDto = serde_json::from_str(
            r#"{"name":"test-harnesses (3)","status":"completed","conclusion":"failure","started_at":"2026-07-18T01:00:00Z","completed_at":"2026-07-18T01:00:02.500Z"}"#,
        )
        .expect("job");
        let job = failed.into_core();
        assert!(job.is_failed());
        assert_eq!(job.harness_shard(), Some(3));
        assert_eq!(job.wall_clock_seconds, Some(2.5));

        let zero: JobDto = serde_json::from_str(
            r#"{"name":"test-harnesses (4)","status":"completed","conclusion":"success","started_at":"2026-07-18T01:00:02Z","completed_at":"2026-07-18T01:00:02Z"}"#,
        )
        .expect("job");
        assert_eq!(zero.into_core().wall_clock_seconds, None);
    }

    #[test]
    fn log_redirect_policy_rejects_downgrade_credentials_loops_and_broad_blob_hosts() {
        let start =
            Url::parse("https://api.github.com/repos/o/r/actions/runs/1/logs").expect("URL");
        let approved = validate_log_redirect(
            &start,
            "https://productionresultssa12.blob.core.windows.net/actions-results/log.zip",
            &BTreeSet::new(),
        )
        .expect("approved GitHub Actions storage host");
        assert_eq!(approved.scheme(), "https");

        for location in [
            "http://productionresultssa12.blob.core.windows.net/log.zip",
            "https://user@productionresultssa12.blob.core.windows.net/log.zip",
            "https://attacker.blob.core.windows.net/log.zip",
            "https://results-receiver.actions.githubusercontent.com.evil.example/log.zip",
        ] {
            assert!(
                validate_log_redirect(&start, location, &BTreeSet::new()).is_err(),
                "redirect {location}"
            );
        }
        let loop_url = "https://results-receiver.actions.githubusercontent.com/log.zip";
        assert!(
            validate_log_redirect(&start, loop_url, &BTreeSet::from([loop_url.to_owned()]))
                .is_err()
        );
    }

    #[tokio::test]
    async fn bounded_stream_fails_instead_of_returning_truncated_bytes() {
        let body = Full::new(bytes::Bytes::from_static(b"12345"));
        let error = collect_bounded(body, 4, GitHubActionsErrorKind::LogLimit)
            .await
            .expect_err("oversize body");
        assert_eq!(error.kind(), GitHubActionsErrorKind::LogLimit);

        let body = Full::new(bytes::Bytes::from_static(b"12345"));
        assert_eq!(
            collect_bounded(body, 5, GitHubActionsErrorKind::LogLimit)
                .await
                .expect("at limit"),
            b"12345"
        );

        let headers = Response::builder()
            .header(header::CONTENT_LENGTH, "invalid")
            .body(())
            .expect("response");
        assert_eq!(
            content_length(headers.headers())
                .expect_err("malformed content length")
                .kind(),
            GitHubActionsErrorKind::Response
        );
    }

    #[test]
    fn actions_port_maps_cooperative_cancellation_to_its_closed_error() {
        let runtime = crate::runtime::LarchRuntime::paused_current_thread().expect("runtime");
        let service = runtime.block_on(async {
            super::OctocrabGitHubService::from_test_token("test-token-for-cancellation")
        });
        let cancellation = crate::runtime::Cancellation::new();
        cancellation.cancel();
        let result = runtime.block_on(service.with_cancellation(
            &cancellation,
            std::future::pending::<Result<(), GitHubActionsError>>(),
        ));
        assert_eq!(
            result.expect_err("cancelled operation").kind(),
            GitHubActionsErrorKind::Cancelled
        );
    }

    #[test]
    fn mutation_statuses_distinguish_acceptance_uncertainty_and_denial() {
        let runtime = crate::runtime::LarchRuntime::new().expect("runtime");
        let service = runtime.block_on(async {
            super::OctocrabGitHubService::from_test_token("test-token-for-status")
        });
        let accepted = Response::builder().status(201).body(()).expect("response");
        assert_eq!(
            mutation_response(&service, &accepted, StatusCode::CREATED).expect("accepted"),
            MutationAttempt::Accepted
        );
        let uncertain = Response::builder().status(503).body(()).expect("response");
        assert_eq!(
            mutation_response(&service, &uncertain, StatusCode::CREATED).expect("uncertain"),
            MutationAttempt::Uncertain(None)
        );
        let denied = Response::builder().status(401).body(()).expect("response");
        assert_eq!(
            mutation_response(&service, &denied, StatusCode::CREATED)
                .expect_err("authorization")
                .kind(),
            GitHubActionsErrorKind::Authorization
        );
    }

    #[test]
    fn response_nesting_counts_structures_but_not_string_punctuation() {
        assert!(json_depth_within(br#"{"value":"[[[","rows":[{}]}"#, 3));
        assert!(!json_depth_within(br#"{"rows":[[{"deep":true}]]}"#, 3));
    }

    #[test]
    fn retry_after_is_bounded_and_attached_to_uncertain_mutations() {
        let runtime = crate::runtime::LarchRuntime::new().expect("runtime");
        let service = runtime.block_on(async {
            super::OctocrabGitHubService::from_test_token("test-token-for-rate-limit")
        });
        let response = Response::builder()
            .status(429)
            .header(header::RETRY_AFTER, "120")
            .body(())
            .expect("response");
        assert_eq!(
            mutation_response(&service, &response, StatusCode::CREATED)
                .expect("uncertain mutation"),
            MutationAttempt::Uncertain(Some(Duration::from_secs(120)))
        );
        assert_eq!(
            read_backoff(1, retry_delay(response.headers())),
            LOG_TIMEOUT
        );
    }
}
