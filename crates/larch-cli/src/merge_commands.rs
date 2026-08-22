use std::{ffi::OsString, process::ExitCode, thread, time::Duration};

use larch_adapters::{
    GixRepository,
    github::{
        LiveMutationRequest, MergeStateStatus, PullRequestMerge, PullRequestMergeMethod,
        PullRequestMergeResult, PullRequestQueueResult, ReleaseCandidatePullRequestState,
        ReviewDecision,
    },
};
use larch_core::{
    CheckBucket, GitHubActionsService, GitHubRepositoryRef, RepositoryRead, Revision,
    RuntimeRedactor,
};

use crate::{
    argparse_compat::{
        choice_error, option_text, parse_python_int, parse_required_with_help, python_repr,
        usage_error,
    },
    release_common::{ProductionReleaseServices, plugin_version_at, repo_slug, semver},
};

const PR_PROGRAM: &str = "cli.py merge pr";
const PR_USAGE: &str = "usage: cli.py merge pr [-h] --pr PR --repo REPO [--no-admin-fallback]\n                       [--method {squash,merge}]";
const PR_HELP: &str = "usage: cli.py merge pr [-h] --pr PR --repo REPO [--no-admin-fallback]\n                       [--method {squash,merge}]\n\noptions:\n  -h, --help            show this help message and exit\n  --pr PR\n  --repo REPO\n  --no-admin-fallback\n  --method {squash,merge}";
const WAIT_PROGRAM: &str = "cli.py merge wait";
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
    const fn success(result: &'static str) -> Self {
        Self {
            result,
            error: String::new(),
        }
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
        repository: &str,
        number: u64,
        head: &str,
    ) -> Result<PullRequestQueueResult, String>;
    fn direct_merge(
        &mut self,
        repository: &str,
        number: u64,
        head: &str,
        method: PullRequestMergeMethod,
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
        let slug =
            repo_slug(repository).ok_or_else(|| "invalid GitHub repository slug".to_owned())?;
        let pull = self
            .runtime
            .block_on(self.github.release_candidate_pull_request(
                &self.cancellation,
                slug.owner(),
                slug.repo(),
                number,
            ))
            .map_err(|error| error.to_string())?;
        Ok(Candidate {
            state: pull.state,
            head_oid: pull.head_oid,
        })
    }
    fn review(&mut self, repository: &str, number: u64) -> Result<ReviewState, String> {
        let slug =
            repo_slug(repository).ok_or_else(|| "invalid GitHub repository slug".to_owned())?;
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
        let slug =
            repo_slug(repository).ok_or_else(|| "invalid GitHub repository slug".to_owned())?;
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
        let slug =
            repo_slug(repository).ok_or_else(|| "invalid GitHub repository slug".to_owned())?;
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
        repository: &str,
        number: u64,
        head: &str,
    ) -> Result<PullRequestQueueResult, String> {
        let slug =
            repo_slug(repository).ok_or_else(|| "invalid GitHub repository slug".to_owned())?;
        self.runtime
            .block_on(self.github.enqueue_pull_request(
                &self.cancellation,
                &mutation_authorization(),
                slug.owner(),
                slug.repo(),
                number,
                head,
            ))
            .map_err(|error| error.to_string())
    }
    fn direct_merge(
        &mut self,
        repository: &str,
        number: u64,
        head: &str,
        method: PullRequestMergeMethod,
        bypass: bool,
    ) -> Result<PullRequestMergeResult, String> {
        let slug =
            repo_slug(repository).ok_or_else(|| "invalid GitHub repository slug".to_owned())?;
        self.runtime
            .block_on(self.github.merge_pull_request(
                &self.cancellation,
                &mutation_authorization(),
                &PullRequestMerge {
                    owner: slug.owner(),
                    repo: slug.repo(),
                    number,
                    expected_head_oid: head,
                    method,
                    bypass_branch_protection: bypass,
                    commit_title: None,
                    commit_message: None,
                },
            ))
            .map_err(|error| error.to_string())
    }
    fn local_head(&mut self) -> Result<String, String> {
        resolve(&self.repository, "HEAD")
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
#[derive(Clone, Debug)]
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
        WAIT_PROGRAM,
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
                WAIT_PROGRAM,
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
    match services.enqueue(&request.repository, request.number, head) {
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
fn merge_without_admin<S: MergeServices>(
    services: &mut S,
    request: &MergeRequest,
    head: &str,
) -> Outcome {
    match services.direct_merge(
        &request.repository,
        request.number,
        head,
        request.method,
        false,
    ) {
        Ok(PullRequestMergeResult::Merged { .. } | PullRequestMergeResult::AlreadyMerged) => {
            Outcome::success("merged")
        }
        Ok(PullRequestMergeResult::HeadChanged | PullRequestMergeResult::MergeConflict) => {
            Outcome::new(
                "main_advanced",
                "pull request head changed or conflicts with main",
            )
        }
        Ok(result) => review_classification(
            services,
            request,
            Outcome::new(
                "policy_denied",
                format!("branch protection denied merge; --no-admin-fallback set: {result:?}"),
            ),
        ),
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
    let admin = services.direct_merge(
        &request.repository,
        request.number,
        head,
        request.method,
        true,
    );
    match admin {
        Ok(PullRequestMergeResult::Merged { .. } | PullRequestMergeResult::AlreadyMerged) => {
            Outcome::success("admin_merged")
        }
        Ok(PullRequestMergeResult::HeadChanged | PullRequestMergeResult::MergeConflict) => {
            Outcome::new(
                "main_advanced",
                "pull request head changed or conflicts with main",
            )
        }
        Err(error) => review_classification(
            services,
            request,
            Outcome::new(
                "admin_failed",
                format!("Admin merge outcome was uncertain: {error}"),
            ),
        ),
        Ok(admin_result) => {
            let plain = services.direct_merge(
                &request.repository,
                request.number,
                head,
                request.method,
                false,
            );
            match plain {
                Ok(
                    PullRequestMergeResult::Merged { .. } | PullRequestMergeResult::AlreadyMerged,
                ) => Outcome::success("merged"),
                Ok(PullRequestMergeResult::HeadChanged | PullRequestMergeResult::MergeConflict) => {
                    Outcome::new(
                        "main_advanced",
                        "pull request head changed or conflicts with main",
                    )
                }
                Ok(result) => review_classification(
                    services,
                    request,
                    Outcome::new(
                        "admin_failed",
                        format!(
                            "Admin merge failed: {admin_result:?}; fallback merge failed: {result:?}"
                        ),
                    ),
                ),
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
fn resolve(repository: &GixRepository, revision: &str) -> Result<String, String> {
    repository
        .resolve_revision(&Revision::new(revision.as_bytes()))
        .map(|oid| oid.to_hex())
        .map_err(|error| error.to_string())
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
    use std::collections::VecDeque;

    struct Fake {
        candidates: VecDeque<Result<Candidate, String>>,
        reviews: VecDeque<Result<ReviewState, String>>,
        checks: bool,
        queue: bool,
        enqueued: Result<PullRequestQueueResult, String>,
        merges: VecDeque<Result<PullRequestMergeResult, String>>,
        head: String,
        bump: Option<VersionBump>,
        versions: VecDeque<String>,
        merge_calls: usize,
    }

    impl Default for Fake {
        fn default() -> Self {
            Self {
                candidates: VecDeque::from([Ok(candidate(ReleaseCandidatePullRequestState::Open))]),
                reviews: VecDeque::from([Ok(review(MergeStateStatus::Clean))]),
                checks: true,
                queue: false,
                enqueued: Ok(PullRequestQueueResult::Queued),
                merges: VecDeque::from([Ok(PullRequestMergeResult::Merged {
                    merge_commit_oid: "2".repeat(40),
                })]),
                head: "1".repeat(40),
                bump: None,
                versions: VecDeque::new(),
                merge_calls: 0,
            }
        }
    }

    impl MergeServices for Fake {
        fn candidate(&mut self, _: &str, _: u64) -> Result<Candidate, String> {
            self.candidates
                .pop_front()
                .unwrap_or_else(|| Ok(candidate(ReleaseCandidatePullRequestState::Open)))
        }
        fn review(&mut self, _: &str, _: u64) -> Result<ReviewState, String> {
            self.reviews
                .pop_front()
                .unwrap_or_else(|| Ok(review(MergeStateStatus::Clean)))
        }
        fn checks_pass(&mut self, _: &str, _: &str) -> Result<bool, String> {
            Ok(self.checks)
        }
        fn queue_enabled(&mut self, _: &str, _: u64) -> Result<bool, String> {
            Ok(self.queue)
        }
        fn enqueue(&mut self, _: &str, _: u64, _: &str) -> Result<PullRequestQueueResult, String> {
            self.enqueued.clone()
        }
        fn direct_merge(
            &mut self,
            _: &str,
            _: u64,
            _: &str,
            _: PullRequestMergeMethod,
            _: bool,
        ) -> Result<PullRequestMergeResult, String> {
            self.merge_calls += 1;
            self.merges
                .pop_front()
                .unwrap_or(Ok(PullRequestMergeResult::MergeUnavailable))
        }
        fn local_head(&mut self) -> Result<String, String> {
            Ok(self.head.clone())
        }
        fn fetch_main(&mut self) -> Result<(), String> {
            Ok(())
        }
        fn version_bump(&mut self) -> Result<Option<VersionBump>, String> {
            Ok(self.bump.clone())
        }
        fn plugin_version(&mut self, _: &str) -> Result<String, String> {
            Ok(self.versions.pop_front().unwrap_or_default())
        }
        fn sleep(&mut self, _: Duration) {}
    }
    fn candidate(state: ReleaseCandidatePullRequestState) -> Candidate {
        Candidate {
            state,
            head_oid: "1".repeat(40),
        }
    }
    fn review(merge_state: MergeStateStatus) -> ReviewState {
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

    #[test]
    fn terminal_and_precondition_outcomes_are_stable() {
        let mut merged = Fake {
            candidates: VecDeque::from([Ok(candidate(ReleaseCandidatePullRequestState::Merged))]),
            ..Fake::default()
        };
        assert_eq!(merge(&mut merged, &request()), Outcome::success("merged"));
        let mut ci = Fake {
            checks: false,
            ..Fake::default()
        };
        assert_eq!(merge(&mut ci, &request()).result, "ci_not_ready");
        let mut mismatch = Fake {
            head: "9".repeat(40),
            ..Fake::default()
        };
        assert!(
            merge(&mut mismatch, &request())
                .error
                .contains("does not match PR head")
        );
    }

    #[test]
    fn queue_and_admin_fallback_preserve_result_literals() {
        let mut queued = Fake {
            queue: true,
            ..Fake::default()
        };
        assert_eq!(merge(&mut queued, &request()), Outcome::success("queued"));
        let mut changed = Fake {
            queue: true,
            enqueued: Ok(PullRequestQueueResult::HeadChanged),
            ..Fake::default()
        };
        assert_eq!(merge(&mut changed, &request()).result, "main_advanced");
        let mut fallback = Fake {
            merges: VecDeque::from([
                Ok(PullRequestMergeResult::BranchProtection),
                Ok(PullRequestMergeResult::Merged {
                    merge_commit_oid: "2".repeat(40),
                }),
            ]),
            ..Fake::default()
        };
        assert_eq!(merge(&mut fallback, &request()), Outcome::success("merged"));
        assert_eq!(fallback.merge_calls, 2);
    }

    #[test]
    fn uncertain_admin_outcome_never_submits_a_second_mutation() {
        let mut fake = Fake {
            merges: VecDeque::from([Err("uncertain".to_owned())]),
            ..Fake::default()
        };
        assert_eq!(merge(&mut fake, &request()).result, "admin_failed");
        assert_eq!(fake.merge_calls, 1);
    }

    #[test]
    fn version_race_detects_a_published_same_version() {
        let mut fake = Fake {
            bump: Some(VersionBump {
                parent: "3".repeat(40),
                version: "1.2.3".to_owned(),
            }),
            versions: VecDeque::from(["1.2.3".to_owned()]),
            ..Fake::default()
        };
        assert_eq!(
            merge(&mut fake, &request()).result,
            "version_already_published"
        );
    }

    #[test]
    fn wait_requires_an_observed_merge_and_rejects_closed() {
        let mut merged = Fake {
            candidates: VecDeque::from([
                Ok(candidate(ReleaseCandidatePullRequestState::Open)),
                Ok(candidate(ReleaseCandidatePullRequestState::Merged)),
            ]),
            ..Fake::default()
        };
        assert_eq!(wait_for_merge(&mut merged, 7, "o/r"), Ok(()));
        let mut closed = Fake {
            candidates: VecDeque::from([Ok(candidate(ReleaseCandidatePullRequestState::Closed))]),
            ..Fake::default()
        };
        assert!(
            wait_for_merge(&mut closed, 7, "o/r")
                .unwrap_err()
                .contains("CLOSED")
        );
    }

    #[test]
    fn bump_subjects_are_exact() {
        assert_eq!(bump_version("Release v1.2.3"), Some("1.2.3"));
        assert_eq!(bump_version("Bump version to 2.0.0"), Some("2.0.0"));
        assert_eq!(bump_version("Release v1.2.3 extra"), None);
    }
}
