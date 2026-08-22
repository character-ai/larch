use crate::{
    argparse_compat::{
        choice_error, option_text, parse_python_int, parse_required_with_help, python_repr,
        usage_error,
    },
    release_common::{ProductionReleaseServices, plugin_version_at, repo_slug, semver},
};
use larch_adapters::github::{
    LiveMutationRequest, MergeStateStatus, PullRequestMerge, PullRequestMergeMethod,
    PullRequestMergeResult, PullRequestQueueResult, ReleaseCandidatePullRequestState, RepoSlug,
    ReviewDecision,
};
use larch_core::{
    CheckBucket, GitHubActionsService, GitHubRepositoryRef, RepositoryRead, Revision,
    RuntimeRedactor,
};
use std::{ffi::OsString, process::ExitCode, thread, time::Duration};
const PR_PROGRAM: &str = "cli.py merge pr";
const PR_USAGE: &str = "usage: cli.py merge pr [-h] --pr PR --repo REPO [--no-admin-fallback]\n                       [--method {squash,merge}]";
const PR_HELP: &str = "usage: cli.py merge pr [-h] --pr PR --repo REPO [--no-admin-fallback]\n                       [--method {squash,merge}]\n\noptions:\n  -h, --help            show this help message and exit\n  --pr PR\n  --repo REPO\n  --no-admin-fallback\n  --method {squash,merge}";
const WAIT_USAGE: &str = "usage: cli.py merge wait [-h] --pr PR --repo REPO";
const WAIT_HELP: &str = "usage: cli.py merge wait [-h] --pr PR --repo REPO\n\noptions:\n  -h, --help   show this help message and exit\n  --pr PR\n  --repo REPO";
const VERSION_WALK_LIMIT: usize = 10_000;
const UNKNOWN_RETRIES: usize = 4;
const WAIT_POLLS: usize = 2_880;
#[derive(Clone, Debug, Eq, PartialEq)]
struct Outcome {
    result: &'static str,
    error: String,
}
impl Outcome {
    fn new(result: &'static str, error: impl Into<String>) -> Self {
        let error = error.into();
        Self {
            result,
            error: diagnostic(&error),
        }
    }
    fn success(result: &'static str) -> Self {
        Self::new(result, "")
    }
}
#[derive(Clone, Debug, Eq, PartialEq)]
struct Candidate {
    state: ReleaseCandidatePullRequestState,
    head_oid: String,
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct ReviewState {
    merge_state: MergeStateStatus,
    decision: Option<ReviewDecision>,
}
#[derive(Clone, Debug, Eq, PartialEq)]
struct VersionBump {
    parent: String,
    version: String,
}
trait MergeServices {
    fn candidate(&mut self, repository: &str, number: u64) -> Result<Candidate, String>;
    fn review(&mut self, repository: &str, number: u64) -> Result<ReviewState, String>;
    fn checks_pass(&mut self, repository: &str, head: &str) -> Result<bool, String>;
    fn queue_enabled(&mut self, repository: &str, number: u64) -> Result<bool, String>;
    fn enqueue(
        &mut self,
        request: &MergeRequest,
        head: &str,
    ) -> Result<PullRequestQueueResult, String>;
    fn direct_merge(
        &mut self,
        request: &MergeRequest,
        head: &str,
        bypass: bool,
    ) -> Result<PullRequestMergeResult, String>;
    fn local_head(&mut self) -> Result<String, String>;
    fn fetch_main(&mut self) -> Result<(), String>;
    fn version_bump(&mut self) -> Result<Option<VersionBump>, String>;
    fn plugin_version(&mut self, revision: &str) -> Result<String, String>;
    fn sleep(&mut self, duration: Duration);
}
impl MergeServices for ProductionReleaseServices {
    fn candidate(&mut self, repository: &str, number: u64) -> Result<Candidate, String> {
        let pull = self.pull_request(&merge_repo(repository)?, number)?;
        Ok(Candidate {
            state: pull.state,
            head_oid: pull.head_oid,
        })
    }
    fn review(&mut self, repository: &str, number: u64) -> Result<ReviewState, String> {
        let slug = merge_repo(repository)?;
        let state = self
            .runtime
            .block_on(self.github.pull_request_review_state(
                &self.cancellation,
                slug.owner(),
                slug.repo(),
                number,
            ))
            .map_err(|error| error.to_string())?;
        Ok(ReviewState {
            merge_state: state.merge_state_status(),
            decision: state.review_decision(),
        })
    }
    fn checks_pass(&mut self, repository: &str, head: &str) -> Result<bool, String> {
        let slug = merge_repo(repository)?;
        let reference = GitHubRepositoryRef::new(slug.owner(), slug.repo())
            .map_err(|error| error.to_string())?;
        let checks = self
            .runtime
            .block_on(self.github.check_runs(&reference, head, &self.cancellation))
            .map_err(|error| error.to_string())?;
        Ok(!checks.is_empty()
            && checks
                .iter()
                .all(|check| !matches!(check.bucket, CheckBucket::Fail | CheckBucket::Pending)))
    }
    fn queue_enabled(&mut self, repository: &str, number: u64) -> Result<bool, String> {
        let slug = merge_repo(repository)?;
        self.runtime
            .block_on(self.github.pull_request_queue_state(
                &self.cancellation,
                slug.owner(),
                slug.repo(),
                number,
            ))
            .map(|state| state.enabled)
            .map_err(|error| error.to_string())
    }
    fn enqueue(
        &mut self,
        request: &MergeRequest,
        head: &str,
    ) -> Result<PullRequestQueueResult, String> {
        let slug = merge_repo(&request.repository)?;
        self.runtime
            .block_on(self.github.enqueue_pull_request(
                &self.cancellation,
                &mutation_authorization(),
                slug.owner(),
                slug.repo(),
                request.number,
                head,
            ))
            .map_err(|error| error.to_string())
    }
    fn direct_merge(
        &mut self,
        request: &MergeRequest,
        head: &str,
        bypass: bool,
    ) -> Result<PullRequestMergeResult, String> {
        let slug = merge_repo(&request.repository)?;
        self.runtime
            .block_on(self.github.merge_pull_request(
                &self.cancellation,
                &mutation_authorization(),
                &PullRequestMerge {
                    owner: slug.owner(),
                    repo: slug.repo(),
                    number: request.number,
                    expected_head_oid: head,
                    method: request.method,
                    bypass_branch_protection: bypass,
                    commit_title: None,
                    commit_message: None,
                },
            ))
            .map_err(|error| error.to_string())
    }
    fn local_head(&mut self) -> Result<String, String> {
        self.repository
            .resolve_revision(&Revision::new(b"HEAD"))
            .map(|oid| oid.to_hex())
            .map_err(|error| error.to_string())
    }
    fn fetch_main(&mut self) -> Result<(), String> {
        self.fetch_origin_main()
    }
    fn version_bump(&mut self) -> Result<Option<VersionBump>, String> {
        let main = self
            .repository
            .resolve_revision(&Revision::new(b"origin/main"))
            .map_err(|error| error.to_string())?;
        let head = self
            .repository
            .resolve_revision(&Revision::new(b"HEAD"))
            .map_err(|error| error.to_string())?;
        let commits = self
            .repository
            .walk_commits_range(&main, &head, VERSION_WALK_LIMIT + 1)
            .map_err(|error| error.to_string())?;
        if commits.len() > VERSION_WALK_LIMIT {
            return Err("version-race commit window exceeds its bound".to_owned());
        }
        for commit in commits {
            let subject = String::from_utf8_lossy(&commit.subject);
            let Some(version) = bump_version(&subject) else {
                continue;
            };
            let parent = commit
                .parents
                .first()
                .ok_or_else(|| "version bump commit has no parent".to_owned())?;
            return Ok(Some(VersionBump {
                parent: parent.to_hex(),
                version: version.to_owned(),
            }));
        }
        Ok(None)
    }
    fn plugin_version(&mut self, revision: &str) -> Result<String, String> {
        plugin_version_at(&self.repository, revision)
    }
    fn sleep(&mut self, duration: Duration) {
        thread::sleep(duration);
    }
}
pub fn pr(arguments: &[OsString]) -> ExitCode {
    let Some(request) = parse_pr(arguments) else {
        return ExitCode::from(1);
    };
    let outcome = match ProductionReleaseServices::new() {
        Ok(mut services) => merge(&mut services, &request),
        Err(error) => Outcome::new("error", error),
    };
    emit(&outcome);
    ExitCode::SUCCESS
}
pub fn wait(arguments: &[OsString]) -> ExitCode {
    let Some((number, repository)) = parse_wait(arguments) else {
        return ExitCode::from(1);
    };
    let outcome = match ProductionReleaseServices::new() {
        Ok(mut services) => wait_for_merge(&mut services, number, &repository),
        Err(error) => Err(error),
    };
    match outcome {
        Ok(()) => {
            emit(&Outcome::success("merged"));
            ExitCode::SUCCESS
        }
        Err(error) => {
            emit(&Outcome::new("error", error));
            ExitCode::from(1)
        }
    }
}
struct MergeRequest {
    number: u64,
    repository: String,
    no_admin_fallback: bool,
    method: PullRequestMergeMethod,
}
fn parse_pr(arguments: &[OsString]) -> Option<MergeRequest> {
    const OPTIONS: &[&str] = &["--pr", "--repo", "--no-admin-fallback", "--method"];
    if let Some(error) = choice_error(arguments, OPTIONS, &[("--method", &["squash", "merge"])]) {
        let _ = usage_error(PR_USAGE, PR_PROGRAM, &error, 1);
        return None;
    }
    let parsed = parse_required_with_help(
        arguments,
        PR_PROGRAM,
        PR_USAGE,
        PR_HELP,
        &["--pr", "--repo", "--method"],
        &["--no-admin-fallback"],
        &["--pr", "--repo"],
    )
    .ok()?;
    let raw = option_text(&parsed, "--pr", "");
    let number = parse_python_int(&raw).and_then(|value| u64::try_from(value).ok());
    let Some(number) = number.filter(|number| *number > 0) else {
        if parse_python_int(&raw).is_none() {
            let _ = usage_error(
                PR_USAGE,
                PR_PROGRAM,
                &format!("argument --pr: invalid int value: {}", python_repr(&raw)),
                1,
            );
            return None;
        }
        return Some(MergeRequest {
            number: 0,
            repository: option_text(&parsed, "--repo", ""),
            no_admin_fallback: parsed.flag("--no-admin-fallback"),
            method: PullRequestMergeMethod::Squash,
        });
    };
    Some(MergeRequest {
        number,
        repository: option_text(&parsed, "--repo", ""),
        no_admin_fallback: parsed.flag("--no-admin-fallback"),
        method: match option_text(&parsed, "--method", "squash").as_str() {
            "merge" => PullRequestMergeMethod::Merge,
            _ => PullRequestMergeMethod::Squash,
        },
    })
}
fn parse_wait(arguments: &[OsString]) -> Option<(u64, String)> {
    let parsed = parse_required_with_help(
        arguments,
        "cli.py merge wait",
        WAIT_USAGE,
        WAIT_HELP,
        &["--pr", "--repo"],
        &[],
        &["--pr", "--repo"],
    )
    .ok()?;
    let raw = option_text(&parsed, "--pr", "");
    let number = parse_python_int(&raw).and_then(|value| u64::try_from(value).ok());
    match number.filter(|number| *number > 0) {
        Some(number) => Some((number, option_text(&parsed, "--repo", ""))),
        None if parse_python_int(&raw).is_some() => Some((0, option_text(&parsed, "--repo", ""))),
        None => {
            let _ = usage_error(
                WAIT_USAGE,
                "cli.py merge wait",
                &format!("argument --pr: invalid int value: {}", python_repr(&raw)),
                1,
            );
            None
        }
    }
}
fn merge<S: MergeServices>(services: &mut S, request: &MergeRequest) -> Outcome {
    if request.number == 0 {
        return Outcome::new("error", "pull request number must be positive");
    }
    if repo_slug(&request.repository).is_none() {
        return Outcome::new("error", "invalid GitHub repository slug");
    }
    let candidate = match services.candidate(&request.repository, request.number) {
        Ok(candidate) => candidate,
        Err(error) => return Outcome::new("error", format!("pull request read failed: {error}")),
    };
    match candidate.state {
        ReleaseCandidatePullRequestState::Merged => return Outcome::success("merged"),
        ReleaseCandidatePullRequestState::Closed => {
            return Outcome::new(
                "error",
                "PR is closed but was not merged; refusing merge noop",
            );
        }
        ReleaseCandidatePullRequestState::Open => {}
    }
    let review = match stable_review(services, &request.repository, request.number) {
        Ok(review) => review,
        Err(error) => return Outcome::new("error", error),
    };
    match services.checks_pass(&request.repository, &candidate.head_oid) {
        Ok(true) => {}
        Ok(false) => return Outcome::new("ci_not_ready", "CI checks are not all passing"),
        Err(error) => {
            return Outcome::new(
                "ci_not_ready",
                format!("CI checks could not be read: {error}"),
            );
        }
    }
    if !matches!(
        review.merge_state,
        MergeStateStatus::Behind
            | MergeStateStatus::Blocked
            | MergeStateStatus::Clean
            | MergeStateStatus::HasHooks
            | MergeStateStatus::Unstable
    ) {
        return Outcome::new(
            "main_advanced",
            format!(
                "Branch mergeStateStatus is {}",
                merge_state_name(review.merge_state)
            ),
        );
    }
    let Ok(local_head) = services.local_head() else {
        return Outcome::new("error", "could not resolve local HEAD via git rev-parse");
    };
    if local_head != candidate.head_oid {
        return Outcome::new(
            "error",
            format!(
                "local HEAD ({local_head}) does not match PR head OID ({}); refusing to evaluate same-version gate",
                candidate.head_oid
            ),
        );
    }
    if let Some(outcome) = version_race(services) {
        return outcome;
    }
    attempt_merge(services, request, &candidate.head_oid)
}
fn stable_review<S: MergeServices>(
    services: &mut S,
    repository: &str,
    number: u64,
) -> Result<ReviewState, String> {
    let mut last = services.review(repository, number);
    for _ in 0..UNKNOWN_RETRIES {
        if matches!(&last, Ok(state) if state.merge_state != MergeStateStatus::Unknown) {
            return last;
        }
        services.sleep(Duration::from_secs(5));
        last = services.review(repository, number);
    }
    match last {
        Ok(state) if state.merge_state != MergeStateStatus::Unknown => Ok(state),
        _ => Err(format!(
            "could not read mergeStateStatus from gh pr view after {UNKNOWN_RETRIES} retries"
        )),
    }
}
fn version_race<S: MergeServices>(services: &mut S) -> Option<Outcome> {
    if services.fetch_main().is_err() {
        return Some(Outcome::new(
            "error",
            "git fetch origin main failed; cannot verify same-version race",
        ));
    }
    let bump = match services.version_bump() {
        Ok(Some(bump)) => bump,
        Ok(None) => return None,
        Err(error) => return Some(Outcome::new("error", error)),
    };
    let origin = services.plugin_version("origin/main").unwrap_or_default();
    if semver(&origin).is_none() {
        return Some(Outcome::new(
            "error",
            format!("could not parse origin/main published version (got: '{origin}')"),
        ));
    }
    if origin == bump.version {
        return Some(Outcome::new(
            "version_already_published",
            format!(
                "origin/main HEAD already bumped to {}; rebase and re-bump",
                bump.version
            ),
        ));
    }
    let current = services.plugin_version(&bump.parent).unwrap_or_default();
    if semver(&current).is_none() {
        return Some(Outcome::new(
            "error",
            format!("could not parse pre-bump plugin version (got: '{current}')"),
        ));
    }
    if origin != current {
        return Some(Outcome::new(
            "error",
            format!(
                "origin/main plugin version is {origin}, not pre-bump {current}; a competing release landed"
            ),
        ));
    }
    if services.fetch_main().is_err() {
        return Some(Outcome::new(
            "error",
            "git fetch origin main failed (pre-merge re-fetch)",
        ));
    }
    let refreshed = services.plugin_version("origin/main").unwrap_or_default();
    if semver(&refreshed).is_some() && refreshed == bump.version {
        return Some(Outcome::new(
            "version_already_published",
            format!(
                "origin/main HEAD already bumped to {} (pre-merge re-fetch); rebase and re-bump",
                bump.version
            ),
        ));
    }
    if semver(&refreshed).is_some() && refreshed != current {
        return Some(Outcome::new(
            "error",
            format!(
                "origin/main plugin version is {refreshed}, not pre-bump {current} (pre-merge re-fetch); a competing release landed"
            ),
        ));
    }
    None
}
fn attempt_merge<S: MergeServices>(
    services: &mut S,
    request: &MergeRequest,
    head: &str,
) -> Outcome {
    let queue_enabled = match services.queue_enabled(&request.repository, request.number) {
        Ok(enabled) => enabled,
        Err(error) => {
            return Outcome::new(
                "error",
                format!("could not determine default-branch merge queue policy: {error}"),
            );
        }
    };
    if queue_enabled {
        return enqueue(services, request, head);
    }
    if request.no_admin_fallback {
        return merge_without_admin(services, request, head);
    }
    merge_with_admin_fallback(services, request, head)
}
fn enqueue<S: MergeServices>(services: &mut S, request: &MergeRequest, head: &str) -> Outcome {
    match services.enqueue(request, head) {
        Ok(PullRequestQueueResult::Merged) => Outcome::success("merged"),
        Ok(PullRequestQueueResult::Queued) => Outcome::success("queued"),
        Ok(PullRequestQueueResult::HeadChanged) => Outcome::new(
            "main_advanced",
            "pull request head changed before queue submission",
        ),
        Ok(PullRequestQueueResult::Closed) => Outcome::new(
            "error",
            "PR closed before merge queue submission was confirmed",
        ),
        Err(error) => review_classification(
            services,
            request,
            Outcome::new(
                "policy_denied",
                format!("merge queue submission failed: {error}"),
            ),
        ),
    }
}
fn terminal_merge_result(
    result: &PullRequestMergeResult,
    success: &'static str,
) -> Option<Outcome> {
    match result {
        PullRequestMergeResult::Merged { .. } => Some(Outcome::success(success)),
        PullRequestMergeResult::AlreadyMerged => Some(Outcome::success("merged")),
        PullRequestMergeResult::HeadChanged | PullRequestMergeResult::MergeConflict => {
            Some(Outcome::new(
                "main_advanced",
                "pull request head changed or conflicts with main",
            ))
        }
        _ => None,
    }
}
fn merge_without_admin<S: MergeServices>(
    services: &mut S,
    request: &MergeRequest,
    head: &str,
) -> Outcome {
    match services.direct_merge(request, head, false) {
        Ok(result) => terminal_merge_result(&result, "merged").unwrap_or_else(|| {
            review_classification(
                services,
                request,
                Outcome::new(
                    "policy_denied",
                    format!("branch protection denied merge; --no-admin-fallback set: {result:?}"),
                ),
            )
        }),
        Err(error) => review_classification(
            services,
            request,
            Outcome::new(
                "policy_denied",
                format!("branch protection denied merge; --no-admin-fallback set: {error}"),
            ),
        ),
    }
}
fn merge_with_admin_fallback<S: MergeServices>(
    services: &mut S,
    request: &MergeRequest,
    head: &str,
) -> Outcome {
    let admin_result = match services.direct_merge(request, head, true) {
        Ok(result) => match terminal_merge_result(&result, "admin_merged") {
            Some(outcome) => return outcome,
            None => result,
        },
        Err(error) => {
            return review_classification(
                services,
                request,
                Outcome::new(
                    "admin_failed",
                    format!("Admin merge outcome was uncertain: {error}"),
                ),
            );
        }
    };
    match services.direct_merge(request, head, false) {
        Ok(result) => terminal_merge_result(&result, "merged").unwrap_or_else(|| {
            review_classification(
                services,
                request,
                Outcome::new(
                    "admin_failed",
                    format!(
                        "Admin merge failed: {admin_result:?}; fallback merge failed: {result:?}"
                    ),
                ),
            )
        }),
        Err(error) => review_classification(
            services,
            request,
            Outcome::new(
                "admin_failed",
                format!(
                    "Admin merge failed: {admin_result:?}; fallback merge outcome was uncertain: {error}"
                ),
            ),
        ),
    }
}
fn review_classification<S: MergeServices>(
    services: &mut S,
    request: &MergeRequest,
    outcome: Outcome,
) -> Outcome {
    let review_required = services
        .review(&request.repository, request.number)
        .is_ok_and(|state| state.decision == Some(ReviewDecision::ReviewRequired));
    if !review_required {
        return outcome;
    }
    if request.no_admin_fallback {
        Outcome::new(
            "review_required",
            "PR requires approving review; --no-admin-fallback is set",
        )
    } else {
        Outcome::new(
            "review_required",
            format!(
                "PR requires approving review; admin merge failed: {}",
                outcome.error
            ),
        )
    }
}
fn wait_for_merge<S: MergeServices>(
    services: &mut S,
    number: u64,
    repository: &str,
) -> Result<(), String> {
    if repo_slug(repository).is_none() {
        return Err("invalid GitHub repository slug".to_owned());
    }
    if number == 0 {
        return Err("pull request number must be positive".to_owned());
    }
    for poll in 0..WAIT_POLLS {
        match services.candidate(repository, number)?.state {
            ReleaseCandidatePullRequestState::Merged => return Ok(()),
            ReleaseCandidatePullRequestState::Closed => {
                return Err("queued PR entered state CLOSED without merging".to_owned());
            }
            ReleaseCandidatePullRequestState::Open if poll + 1 < WAIT_POLLS => {
                services.sleep(Duration::from_secs(30));
            }
            ReleaseCandidatePullRequestState::Open => {}
        }
    }
    Err("queued PR did not merge within the merge queue wait timeout".to_owned())
}
fn bump_version(subject: &str) -> Option<&str> {
    ["Release v", "Bump version to "]
        .into_iter()
        .find_map(|prefix| subject.strip_prefix(prefix))
        .filter(|version| semver(version).is_some())
}
fn merge_repo(repository: &str) -> Result<RepoSlug, String> {
    repo_slug(repository).ok_or_else(|| "invalid GitHub repository slug".to_owned())
}
const fn mutation_authorization() -> LiveMutationRequest<'static> {
    LiveMutationRequest {
        context_file: None,
        operator_mode: true,
        run_id: "",
        trusted_root: None,
        test_deny: false,
    }
}
const fn merge_state_name(state: MergeStateStatus) -> &'static str {
    match state {
        MergeStateStatus::Behind => "BEHIND",
        MergeStateStatus::Blocked => "BLOCKED",
        MergeStateStatus::Clean => "CLEAN",
        MergeStateStatus::Dirty => "DIRTY",
        MergeStateStatus::Draft => "DRAFT",
        MergeStateStatus::HasHooks => "HAS_HOOKS",
        MergeStateStatus::Unknown => "UNKNOWN",
        MergeStateStatus::Unstable => "UNSTABLE",
    }
}
fn diagnostic(value: &str) -> String {
    RuntimeRedactor::default()
        .safe_text(value.replace(['\n', '\r'], " "))
        .to_string()
        .chars()
        .take(500)
        .collect()
}
fn emit(outcome: &Outcome) {
    println!("MERGE_RESULT={}", outcome.result);
    println!("ERROR={}", outcome.error);
}
#[cfg(test)]
mod tests {
    use super::*;
    use MergeStateStatus as MS;
    use PullRequestMergeResult as MR;
    use PullRequestQueueResult as QR;
    use ReleaseCandidatePullRequestState as PS;
    use std::collections::VecDeque;
    #[derive(Default)]
    struct Fake {
        candidates: VecDeque<Result<Candidate, String>>,
        reviews: VecDeque<Result<ReviewState, String>>,
        checks: Option<Result<bool, String>>,
        queue: Option<Result<bool, String>>,
        enqueued: Option<Result<PullRequestQueueResult, String>>,
        merges: VecDeque<Result<PullRequestMergeResult, String>>,
        head: Option<Result<String, String>>,
        fetches: VecDeque<Result<(), String>>,
        bump: Option<Result<Option<VersionBump>, String>>,
        versions: VecDeque<Result<String, String>>,
        merge_calls: usize,
    }
    impl MergeServices for Fake {
        fn candidate(&mut self, _: &str, _: u64) -> Result<Candidate, String> {
            self.candidates
                .pop_front()
                .unwrap_or_else(|| Ok(candidate(PS::Open)))
        }
        fn review(&mut self, _: &str, _: u64) -> Result<ReviewState, String> {
            self.reviews
                .pop_front()
                .unwrap_or_else(|| Ok(review(MS::Clean)))
        }
        fn checks_pass(&mut self, _: &str, _: &str) -> Result<bool, String> {
            self.checks.clone().unwrap_or(Ok(true))
        }
        fn queue_enabled(&mut self, _: &str, _: u64) -> Result<bool, String> {
            self.queue.clone().unwrap_or(Ok(false))
        }
        fn enqueue(&mut self, _: &MergeRequest, _: &str) -> Result<QR, String> {
            self.enqueued.clone().unwrap_or(Ok(QR::Queued))
        }
        fn direct_merge(&mut self, _: &MergeRequest, _: &str, _: bool) -> Result<MR, String> {
            self.merge_calls += 1;
            self.merges
                .pop_front()
                .unwrap_or_else(|| Ok(merged_result()))
        }
        fn local_head(&mut self) -> Result<String, String> {
            self.head.clone().unwrap_or_else(|| Ok("1".repeat(40)))
        }
        fn fetch_main(&mut self) -> Result<(), String> {
            self.fetches.pop_front().unwrap_or(Ok(()))
        }
        fn version_bump(&mut self) -> Result<Option<VersionBump>, String> {
            self.bump.clone().unwrap_or(Ok(None))
        }
        fn plugin_version(&mut self, _: &str) -> Result<String, String> {
            self.versions.pop_front().unwrap_or(Ok(String::new()))
        }
        fn sleep(&mut self, _: Duration) {}
    }
    macro_rules! fake {
        ($($field:ident: $value:expr),* $(,)?) => {{
            let mut fake = Fake::default();
            $(fake.$field = $value;)*
            fake
        }};
    }
    fn candidate(state: PS) -> Candidate {
        Candidate {
            state,
            head_oid: "1".repeat(40),
        }
    }
    fn review(merge_state: MS) -> ReviewState {
        ReviewState {
            merge_state,
            decision: None,
        }
    }
    fn request() -> MergeRequest {
        MergeRequest {
            number: 7,
            repository: "o/r".to_owned(),
            no_admin_fallback: false,
            method: PullRequestMergeMethod::Squash,
        }
    }
    fn required_review() -> ReviewState {
        ReviewState {
            merge_state: MS::Clean,
            decision: Some(ReviewDecision::ReviewRequired),
        }
    }
    fn merged_result() -> MR {
        MR::Merged {
            merge_commit_oid: "2".repeat(40),
        }
    }
    fn racing(versions: &[&str]) -> Fake {
        fake!(
            bump: Some(Ok(Some(VersionBump { parent: "3".repeat(40), version: "1.2.3".to_owned() }))),
            versions: versions.iter().map(|value| Ok((*value).to_owned())).collect()
        )
    }
    fn merged(mut fake: Fake) -> &'static str {
        merge(&mut fake, &request()).result
    }
    fn assert_queue(enqueued: Result<QR, String>, expected: &str) {
        let mut fake = fake!(queue: Some(Ok(true)), enqueued: Some(enqueued));
        assert_eq!(
            attempt_merge(&mut fake, &request(), "head").result,
            expected
        );
    }
    fn assert_plain(result: Result<MR, String>, expected: &str) {
        let mut fake = fake!(merges: VecDeque::from([result]));
        let mut request = request();
        request.no_admin_fallback = true;
        assert_eq!(
            merge_without_admin(&mut fake, &request, "head").result,
            expected
        );
    }
    fn assert_admin<const N: usize>(
        results: [Result<MR, String>; N],
        expected: &str,
        calls: usize,
    ) {
        let mut fake = fake!(merges: results.into_iter().collect());
        assert_eq!(
            merge_with_admin_fallback(&mut fake, &request(), "head").result,
            expected
        );
        assert_eq!(fake.merge_calls, calls);
    }
    #[test]
    fn preconditions_and_reads_are_classified() {
        assert_eq!(merged(Fake::default()), "admin_merged");
        let mut invalid = request();
        invalid.number = 0;
        assert_eq!(merge(&mut Fake::default(), &invalid).result, "error");
        invalid.number = 7;
        invalid.repository = "invalid".to_owned();
        assert_eq!(merge(&mut Fake::default(), &invalid).result, "error");
        assert_eq!(
            merged(fake!(candidates: VecDeque::from([Ok(candidate(PS::Merged))]))),
            "merged"
        );
        for value in [Ok(candidate(PS::Closed)), Err("read".to_owned())] {
            assert_eq!(merged(fake!(candidates: VecDeque::from([value]))), "error");
        }
        assert_eq!(merged(fake!(checks: Some(Ok(false)))), "ci_not_ready");
        assert_eq!(
            merged(fake!(checks: Some(Err("read".to_owned())))),
            "ci_not_ready"
        );
        assert_eq!(
            merged(fake!(reviews: VecDeque::from([Ok(review(MS::Dirty))]))),
            "main_advanced"
        );
        assert_eq!(merged(fake!(head: Some(Ok("9".repeat(40))))), "error");
        assert_eq!(
            merged(fake!(head: Some(Err("missing".to_owned())))),
            "error"
        );
        let mut recovered = fake!(reviews: VecDeque::from([
            Ok(review(MS::Unknown)), Ok(review(MS::Clean)),
        ]));
        assert_eq!(
            stable_review(&mut recovered, "o/r", 7),
            Ok(review(MS::Clean))
        );
        for reviews in [
            (0..5).map(|_| Err("read".to_owned())).collect(),
            (0..5).map(|_| Ok(review(MS::Unknown))).collect(),
        ] {
            assert!(stable_review(&mut fake!(reviews: reviews), "o/r", 7).is_err());
        }
    }
    #[test]
    fn queue_outcomes_and_policy_reads_are_classified() {
        assert_queue(Ok(QR::Merged), "merged");
        assert_queue(Ok(QR::Queued), "queued");
        assert_queue(Ok(QR::HeadChanged), "main_advanced");
        assert_queue(Ok(QR::Closed), "error");
        assert_queue(Err("denied".to_owned()), "policy_denied");
        let mut unreadable = fake!(queue: Some(Err("read".to_owned())));
        assert_eq!(
            attempt_merge(&mut unreadable, &request(), "head").result,
            "error"
        );
        let mut required = fake!(
            queue: Some(Ok(true)), enqueued: Some(Err("denied".to_owned())),
            reviews: VecDeque::from([Ok(required_review())])
        );
        assert_eq!(
            attempt_merge(&mut required, &request(), "head").result,
            "review_required"
        );
    }
    #[test]
    fn direct_merge_paths_do_not_repeat_uncertain_mutations() {
        assert_plain(Ok(MR::HeadChanged), "main_advanced");
        assert_plain(Ok(MR::BranchProtection), "policy_denied");
        assert_plain(Err("uncertain".to_owned()), "policy_denied");
        assert_admin([Ok(MR::AlreadyMerged)], "merged", 1);
        assert_admin([Err("uncertain".to_owned())], "admin_failed", 1);
        assert_admin([Ok(MR::BranchProtection), Ok(merged_result())], "merged", 2);
        assert_admin(
            [Ok(MR::BranchProtection), Ok(MR::MergeUnavailable)],
            "admin_failed",
            2,
        );
        assert_admin(
            [Ok(MR::BranchProtection), Err("uncertain".to_owned())],
            "admin_failed",
            2,
        );
        let mut no_admin = request();
        no_admin.no_admin_fallback = true;
        let mut required = fake!(
            merges: VecDeque::from([Ok(MR::BranchProtection)]),
            reviews: VecDeque::from([Ok(required_review())])
        );
        assert_eq!(
            merge_without_admin(&mut required, &no_admin, "head").result,
            "review_required"
        );
    }
    #[test]
    fn version_race_covers_every_release_window() {
        let mut failed_fetch = fake!(fetches: VecDeque::from([Err("fetch".to_owned())]));
        assert_eq!(version_race(&mut failed_fetch).unwrap().result, "error");
        let mut failed_walk = fake!(bump: Some(Err("walk".to_owned())));
        assert_eq!(version_race(&mut failed_walk).unwrap().result, "error");
        assert_eq!(version_race(&mut Fake::default()), None);
        for (versions, expected) in [
            (&["invalid"][..], "error"),
            (&["1.2.3"][..], "version_already_published"),
            (&["1.0.0", "invalid"][..], "error"),
            (&["1.1.0", "1.0.0"][..], "error"),
            (
                &["1.0.0", "1.0.0", "1.2.3"][..],
                "version_already_published",
            ),
            (&["1.0.0", "1.0.0", "1.1.0"][..], "error"),
        ] {
            assert_eq!(
                version_race(&mut racing(versions)).unwrap().result,
                expected
            );
        }
        let mut second_fetch = racing(&["1.0.0", "1.0.0"]);
        second_fetch.fetches = VecDeque::from([Ok(()), Err("fetch".to_owned())]);
        assert_eq!(version_race(&mut second_fetch).unwrap().result, "error");
        assert_eq!(
            version_race(&mut racing(&["1.0.0", "1.0.0", "invalid"])),
            None
        );
    }
    #[test]
    fn wait_validates_and_requires_an_observed_merge() {
        assert!(wait_for_merge(&mut Fake::default(), 7, "invalid").is_err());
        assert!(wait_for_merge(&mut Fake::default(), 0, "o/r").is_err());
        let sequence = [PS::Open, PS::Merged].map(candidate).map(Ok).into();
        assert_eq!(
            wait_for_merge(&mut fake!(candidates: sequence), 7, "o/r"),
            Ok(())
        );
        let closed = VecDeque::from([Ok(candidate(PS::Closed))]);
        assert!(wait_for_merge(&mut fake!(candidates: closed), 7, "o/r").is_err());
        assert!(wait_for_merge(&mut Fake::default(), 7, "o/r").is_err());
    }
    #[test]
    fn small_helpers_are_exact() {
        assert_eq!(bump_version("Release v1.2.3"), Some("1.2.3"));
        assert_eq!(bump_version("Bump version to 2.0.0"), Some("2.0.0"));
        assert_eq!(bump_version("Release v1.2.3 extra"), None);
        assert!(merge_repo("o/r").is_ok());
        assert!(mutation_authorization().operator_mode);
    }
}
