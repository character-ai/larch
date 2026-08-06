//! `/implement` admission, preflight, and fork-bootstrap verbs.
//!
//! `gate` decides whether an issue may enter a run, `preflight` enforces the
//! clean-main entry contract and syncs the working tree, and `fork-env`
//! publishes the fork metadata a `--forked` run needs before Step 0. All three
//! read ambient state here and delegate their decisions to the pure rules in
//! `larch-core` and to the shared Git, GitHub, and filesystem adapters.

use crate::{
    argparse_compat::{ParsedCommandLine, looks_like_option, parse, resolve_option, write_stdout},
    blocker_commands::{emit_blockers, open_blockers, resolve_repo_for},
    git_commands::{
        MainSync, TRANSIENT_ATTEMPTS, is_transient_net, main_sync, main_sync_blocked_message,
        sleep_before_retry,
    },
    github_repository_resolution::{
        RemoteRepoResult, repository_ref, repository_remote_fetch_url, resolve_remote_repo,
    },
};
use larch_adapters::{
    FetchRequest, GitCli, GitCliError, GitCliPolicy, GitRef, GitRefspec, GitRemote, GixRepository,
    NoopProcessObserver, PathIntent, RebaseRequest, TemporaryRoot, TokioProcessRunner,
    atomic_write_utf8,
    github::OctocrabGitHubService,
    read_kv_raw, remove_optional_file,
    runtime::{Cancellation, LarchRuntime},
};
use larch_core::{
    GitHubIssueState, GitHubService, Head, RefName, RepositoryRead, StatusOptions, emit_kv,
    has_designed_prefix, has_managed_prefix, has_report_prefix, normal_issue, single_line,
};
use std::{
    env,
    ffi::OsString,
    path::{Path, PathBuf},
    process::ExitCode,
    sync::Arc,
};

const GATE_USAGE: &str = "usage: admission gate [-h] --issue ISSUE [--repo REPO]\n";
const GATE_HELP: &str = concat!(
    "usage: admission gate [-h] --issue ISSUE [--repo REPO]\n",
    "\n",
    "options:\n",
    "  -h, --help     show this help message and exit\n",
    "  --issue ISSUE\n",
    "  --repo REPO\n",
);
const FORK_ENV_USAGE: &str = "usage: admission fork-env [-h] [--tmpdir TMPDIR]\n";
const FORK_ENV_HELP: &str = concat!(
    "usage: admission fork-env [-h] [--tmpdir TMPDIR]\n",
    "\n",
    "options:\n",
    "  -h, --help       show this help message and exit\n",
    "  --tmpdir TMPDIR\n",
);
const PREFLIGHT_USAGE: &str =
    "usage: admission preflight [--skip-branch-check] [--skip-clean-check]\n";
const PREFLIGHT_FLAGS: [&str; 2] = ["--skip-branch-check", "--skip-clean-check"];
const AUDIT_REPORT_LABEL: &str = "audit-report";
const STALLED_RUN_SENTINEL: &str = "larch-stalled-run.txt";
const CALLER_ENV_NAME: &str = "caller-env.sh";
const FORK_BOOTSTRAP_PREFIX: &str = "larch-fork-bootstrap.";
const TMP_FALLBACK: &str = "/tmp";

/// Decide whether one issue may enter a `/implement` run.
///
/// Exit codes carry the decision: `0` admits, `2` is an admission error, `4`
/// reports open blockers, `5` a lifecycle-prefix refusal, `6` an audit-report
/// label, and `7` a report-titled issue.
pub fn gate(arguments: &[OsString]) -> ExitCode {
    let parsed = parse(arguments, &["--issue", "--repo"], 0);
    if parsed.value_error().is_none() && wants_help(arguments) {
        return write_stdout(GATE_HELP);
    }
    let Some(issue) = gate_issue(&parsed) else {
        return admission_error("argument validation failed");
    };
    let Some(issue) = normal_issue(&issue) else {
        return admission_error("--issue must be a positive integer");
    };
    let explicit_repo = parsed
        .value("--repo")
        .map(|repo| repo.to_string_lossy().into_owned());
    let Some(repo) = resolve_repo_for(explicit_repo.as_deref()) else {
        return admission_error("could not resolve repo (gh repo view failed)");
    };
    let Some(subject) = read_issue(&repo, issue) else {
        // The legacy verb echoed the failed `gh` call's stdout, and a `--json`
        // read leaves stdout empty on every failure, so no detail follows.
        return admission_error("gh issue view failed");
    };
    if subject.closed {
        return admission_error(&format!("issue #{issue} is CLOSED"));
    }
    let blockers = || open_blockers(issue, &repo);
    let decision = if adopted_parent_session(issue) {
        resume_decision(&subject.title, blockers)
    } else {
        fresh_decision(&subject, blockers)
    };
    emit_decision(&decision)
}

/// One admission outcome, before it reaches the contract stream.
#[derive(Clone, Debug, Eq, PartialEq)]
enum Admission {
    /// The issue is admitted; `resume` marks an adopted parent session.
    Pass { resume: bool },
    /// Open blockers refuse the run.
    Blocked(Vec<u64>),
    /// A lifecycle prefix or label refuses the run.
    Refused {
        result: &'static str,
        title: Option<String>,
        code: u8,
    },
}

fn emit_decision(decision: &Admission) -> ExitCode {
    match decision {
        Admission::Pass { resume } => {
            emit_kv("ADMISSION_RESULT", "pass");
            if *resume {
                emit_kv("RESUME", "true");
            }
            ExitCode::SUCCESS
        }
        Admission::Blocked(blockers) => {
            emit_kv("ADMISSION_RESULT", "has-blockers");
            emit_blockers(blockers);
            ExitCode::from(4)
        }
        Admission::Refused {
            result,
            title,
            code,
        } => {
            emit_kv("ADMISSION_RESULT", result);
            if let Some(title) = title {
                emit_kv("TITLE", &single_line(title));
            }
            ExitCode::from(*code)
        }
    }
}

/// Return the supplied `--issue` text, reporting `argparse`'s refusal otherwise.
///
/// `argparse` checks required arguments before surplus ones, so a line that is
/// both missing `--issue` and carries an unknown flag reports the missing
/// argument.
fn gate_issue(parsed: &ParsedCommandLine) -> Option<String> {
    if let Some(error) = parsed.value_error() {
        emit_gate_usage_error(error);
        return None;
    }
    let Some(issue) = parsed.value("--issue") else {
        emit_gate_usage_error("the following arguments are required: --issue");
        return None;
    };
    if let Some(error) = parsed.error() {
        emit_gate_usage_error(&error);
        return None;
    }
    Some(issue.to_string_lossy().into_owned())
}

fn emit_gate_usage_error(error: &str) {
    eprint!("{GATE_USAGE}");
    eprintln!("admission gate: error: {error}");
}

/// Decision for an issue this run already adopted through its parent sentinel.
///
/// An adopted issue already carries a lifecycle prefix from its own run, so the
/// managed-prefix and designed-prefix checks do not apply; blockers are read
/// first because a newly blocked target must stop even a resumed run.
fn resume_decision(title: &str, blockers: impl FnOnce() -> Vec<u64>) -> Admission {
    let blockers = blockers();
    if !blockers.is_empty() {
        return Admission::Blocked(blockers);
    }
    if has_report_prefix(title) {
        return refused("report-title", Some(title), 7);
    }
    Admission::Pass { resume: true }
}

/// Decision for an issue entering a run for the first time.
///
/// Title and label refusals precede the blocker read so a refusal that needs no
/// network never pays for one.
fn fresh_decision(subject: &IssueSubject, blockers: impl FnOnce() -> Vec<u64>) -> Admission {
    if has_managed_prefix(&subject.title) {
        return refused("managed-prefix", Some(&subject.title), 5);
    }
    if has_report_prefix(&subject.title) {
        return refused("report-title", Some(&subject.title), 7);
    }
    if subject.audit_report_label {
        return refused("audit-report-label", None, 6);
    }
    let blockers = blockers();
    if !blockers.is_empty() {
        return Admission::Blocked(blockers);
    }
    if has_designed_prefix(&subject.title) {
        Admission::Pass { resume: false }
    } else {
        refused("missing-designed-prefix", Some(&subject.title), 5)
    }
}

fn refused(result: &'static str, title: Option<&str>, code: u8) -> Admission {
    Admission::Refused {
        result,
        title: title.map(str::to_owned),
        code,
    }
}

fn admission_error(message: &str) -> ExitCode {
    emit_kv("ADMISSION_ERROR", &single_line(message));
    ExitCode::from(2)
}

/// The admission-relevant projection of one GitHub issue.
#[derive(Clone, Debug, Eq, PartialEq)]
struct IssueSubject {
    title: String,
    closed: bool,
    audit_report_label: bool,
}

fn read_issue(repo: &str, issue: u64) -> Option<IssueSubject> {
    let reference = repository_ref(repo).ok()?;
    let working_directory = env::current_dir().ok()?;
    let runtime = LarchRuntime::new().ok()?;
    runtime.block_on(async {
        let runner = TokioProcessRunner::new(Arc::new(NoopProcessObserver));
        let cancellation = Cancellation::new();
        let service = OctocrabGitHubService::from_gh(&runner, &working_directory, &cancellation)
            .await
            .ok()?;
        let subject = service.issue(&reference, issue, &cancellation).await.ok()?;
        Some(IssueSubject {
            closed: subject.state == GitHubIssueState::Closed,
            audit_report_label: subject
                .labels
                .iter()
                .any(|label| label.name == AUDIT_REPORT_LABEL),
            title: subject.title,
        })
    })
}

/// Report whether this run's parent sentinel already adopted `issue`.
///
/// Ambient state is read at the call site so the rule itself stays testable.
fn adopted_parent_session(issue: u64) -> bool {
    sentinel_adopts(
        issue,
        &env::var("IMPLEMENT_TMPDIR").unwrap_or_default(),
        &env::var("RUN_ID").unwrap_or_default(),
    )
}

/// Report whether the sentinel under `tmpdir` claims `issue` for `run_id`.
///
/// The sentinel matches only when it names the same issue and either carries no
/// run id or carries this run's id, so a crashed run resumes its own target and
/// never adopts another run's.
fn sentinel_adopts(issue: u64, tmpdir: &str, run_id: &str) -> bool {
    if tmpdir.is_empty() {
        return false;
    }
    let path = PathBuf::from(tmpdir).join("parent-issue.md");
    if !path.is_file() {
        return false;
    }
    let Ok(rows) = read_kv_raw(&path) else {
        return false;
    };
    let value = |key: &str| {
        rows.iter()
            .find(|(name, _value)| name == key)
            .map_or("", |(_name, value)| value.trim())
    };
    if normal_issue(value("ISSUE_NUMBER")) != Some(issue) {
        return false;
    }
    let sentinel_run_id = value("RUN_ID");
    sentinel_run_id.is_empty() || sentinel_run_id == run_id
}

/// Enforce the clean-main entry contract and sync the tree with `origin/main`.
///
/// Exit codes carry the refusal: `1` is a branch refusal, `2` a dirty-tree or
/// stash refusal, and `3` an argument, fetch, sync, or rebase failure.
pub fn preflight(arguments: &[OsString]) -> ExitCode {
    let (skip_branch_check, skip_clean_check) = match preflight_flags(arguments) {
        Ok(flags) => flags,
        Err(unknown) => {
            eprint!("{PREFLIGHT_USAGE}");
            eprintln!("Unknown option: {unknown}");
            return ExitCode::from(3);
        }
    };
    // One repository read serves the branch, cleanliness, and sentinel rules.
    let repository = open_cwd_repository();
    if !skip_branch_check {
        let current = current_branch_name(repository.as_ref());
        if current != "main" {
            return preflight_failure(
                &format!(
                    "Not on main branch (on '{current}'). Switch to main first, or pass --skip-branch-check."
                ),
                1,
            );
        }
    }
    if !skip_clean_check && let Some(refusal) = clean_tree_refusal(repository.as_ref()) {
        return refusal;
    }
    // The Git mutations run in the same clone the rules just read.
    let working_directory = env::current_dir().unwrap_or_default();
    if !fetch_origin_main(&working_directory) {
        return preflight_failure("git fetch origin main failed.", 3);
    }
    if !skip_branch_check && let MainSync::Blocked { ahead } = main_sync() {
        return preflight_failure(&main_sync_blocked_message(ahead), 3);
    }
    if !skip_branch_check && !skip_clean_check && !rebase_onto_origin_main(&working_directory) {
        return preflight_failure("git rebase origin/main failed.", 3);
    }
    clear_stalled_sentinel(repository.as_ref(), skip_clean_check);
    emit_kv("PREFLIGHT", "ok");
    ExitCode::SUCCESS
}

/// Resolve the two boolean flags, naming the first token that is neither.
///
/// `argparse` accepted unambiguous abbreviations, so `--skip-b` still resolves.
fn preflight_flags(arguments: &[OsString]) -> Result<(bool, bool), String> {
    let mut skip_branch_check = false;
    let mut skip_clean_check = false;
    for argument in arguments {
        let text = argument.to_string_lossy().into_owned();
        let resolved = looks_like_option(argument)
            .then(|| resolve_option(&text, &PREFLIGHT_FLAGS))
            .flatten();
        match resolved {
            Some("--skip-branch-check") => skip_branch_check = true,
            Some("--skip-clean-check") => skip_clean_check = true,
            _ => return Err(text),
        }
    }
    Ok((skip_branch_check, skip_clean_check))
}

fn preflight_failure(message: &str, code: u8) -> ExitCode {
    emit_kv("PREFLIGHT", "fail");
    emit_kv("PREFLIGHT_ERROR", &single_line(message));
    ExitCode::from(code)
}

/// Name the checked-out branch, or the empty string when there is none.
fn current_branch_name(repository: Option<&GixRepository>) -> String {
    let Some(repository) = repository else {
        return String::new();
    };
    match repository.head() {
        Ok(Head::Symbolic { name, .. }) => short_branch_name(&name),
        _ => String::new(),
    }
}

fn short_branch_name(name: &RefName) -> String {
    let raw = name.as_bytes();
    let stripped = raw.strip_prefix(b"refs/heads/").unwrap_or(raw);
    String::from_utf8_lossy(stripped).into_owned()
}

/// Refuse a working tree that is dirty, unreadable, or carries stashed work.
fn clean_tree_refusal(repository: Option<&GixRepository>) -> Option<ExitCode> {
    let unreadable = || {
        Some(preflight_failure(
            "Could not determine working-tree cleanliness (helper produced no CLEAN= line).",
            2,
        ))
    };
    let Some(repository) = repository else {
        return unreadable();
    };
    match repository.local_status(&StatusOptions::default()) {
        Ok(status) if status.is_dirty() => Some(preflight_failure(
            "Working tree is not clean. Commit or stash changes first.",
            2,
        )),
        Ok(_clean) => stash_refusal(repository),
        Err(_error) => unreadable(),
    }
}

/// Refuse when `refs/stash` exists, the reference `git stash list` reports on.
fn stash_refusal(repository: &GixRepository) -> Option<ExitCode> {
    let Ok(references) = repository.references() else {
        return Some(preflight_failure(
            "Could not determine git stash cleanliness. Inspect git stash list and re-run.",
            2,
        ));
    };
    references
        .iter()
        .any(|reference| reference.name.as_bytes() == b"refs/stash")
        .then(|| {
            preflight_failure(
                "Git stash is not empty. Apply or drop stashed changes first, for example with git stash pop or git stash drop.",
                2,
            )
        })
}

/// Fetch `origin main`, retrying across the shared transient backoff schedule.
fn fetch_origin_main(working_directory: &Path) -> bool {
    for attempt in 1..=TRANSIENT_ATTEMPTS {
        match run_git(working_directory, &PreflightGit::FetchOriginMain) {
            GitOutcome::Succeeded => return true,
            GitOutcome::Failed { transient } => {
                if !transient || !sleep_before_retry(attempt) {
                    return false;
                }
            }
        }
    }
    false
}

/// Replay the current branch onto `origin/main`, aborting a failed rebase.
fn rebase_onto_origin_main(working_directory: &Path) -> bool {
    if matches!(
        run_git(working_directory, &PreflightGit::RebaseOntoOriginMain),
        GitOutcome::Succeeded
    ) {
        return true;
    }
    let _aborted = run_git(working_directory, &PreflightGit::AbortRebase);
    false
}

/// The Git mutations preflight performs, each a fixed argv with no free input.
enum PreflightGit {
    FetchOriginMain,
    RebaseOntoOriginMain,
    AbortRebase,
}

/// Whether one Git call succeeded, and whether a failure looked transient.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum GitOutcome {
    Succeeded,
    Failed { transient: bool },
}

/// Run one preflight Git mutation through the shared CLI compatibility owner.
fn run_git(working_directory: &Path, operation: &PreflightGit) -> GitOutcome {
    let opaque = GitOutcome::Failed { transient: false };
    let Ok(policy) = GitCliPolicy::new(working_directory) else {
        return opaque;
    };
    let Ok(runtime) = LarchRuntime::current_thread() else {
        return opaque;
    };
    let runner = TokioProcessRunner::new(Arc::new(NoopProcessObserver));
    let git = GitCli::new(&runner, policy);
    let cancellation = Cancellation::new();
    let result = runtime.block_on(async {
        match operation {
            PreflightGit::FetchOriginMain => {
                let (Ok(remote), Ok(refspec)) = (GitRemote::new("origin"), GitRefspec::new("main"))
                else {
                    return None;
                };
                Some(
                    git.fetch(
                        FetchRequest {
                            remote,
                            refspec: Some(refspec),
                            quiet: true,
                        },
                        &cancellation,
                    )
                    .await,
                )
            }
            PreflightGit::RebaseOntoOriginMain => {
                let Ok(upstream) = GitRef::new("origin/main") else {
                    return None;
                };
                Some(
                    git.rebase(
                        RebaseRequest::Start {
                            onto: None,
                            upstream,
                            branch: None,
                        },
                        &cancellation,
                    )
                    .await,
                )
            }
            PreflightGit::AbortRebase => {
                Some(git.rebase(RebaseRequest::Abort, &cancellation).await)
            }
        }
    });
    match result {
        Some(Ok(_result)) => GitOutcome::Succeeded,
        Some(Err(GitCliError::Failed(result))) => GitOutcome::Failed {
            transient: is_transient_net(&format!(
                "{}{}",
                result.safe_stdout().as_str(),
                result.safe_stderr().as_str()
            )),
        },
        Some(Err(error)) => GitOutcome::Failed {
            transient: is_transient_net(&error.to_string()),
        },
        None => opaque,
    }
}

/// Remove the stalled-run sentinel this entry supersedes.
///
/// The legacy verb kept the sentinel only when a clean-check-skipping run
/// entered with a dirty tree, so a resumed run still sees its own stall marker.
fn clear_stalled_sentinel(repository: Option<&GixRepository>, skip_clean_check: bool) {
    let Some(repository) = repository else {
        return;
    };
    if skip_clean_check
        && repository
            .local_status(&StatusOptions::default())
            .is_ok_and(|status| status.is_dirty())
    {
        return;
    }
    let git_dir = PathBuf::from(
        String::from_utf8_lossy(repository.location().git_dir.as_bytes()).into_owned(),
    );
    let _removed = remove_optional_file(&git_dir.join(STALLED_RUN_SENTINEL));
}

/// Publish the fork metadata a `--forked` run consumes before Step 0.
pub fn fork_env(arguments: &[OsString]) -> ExitCode {
    let parsed = parse(arguments, &["--tmpdir"], 0);
    if let Some(error) = parsed.value_error() {
        return fork_env_usage_error(error);
    }
    if wants_help(arguments) {
        return write_stdout(FORK_ENV_HELP);
    }
    if let Some(error) = parsed.error() {
        return fork_env_usage_error(&error);
    }
    let explicit = parsed
        .value("--tmpdir")
        .map(PathBuf::from)
        .filter(|tmpdir| !tmpdir.as_os_str().is_empty());
    publish_fork_env(open_cwd_repository().as_ref(), explicit)
}

/// Publish the fork metadata for `repository`, or report why it cannot.
fn publish_fork_env(repository: Option<&GixRepository>, explicit: Option<PathBuf>) -> ExitCode {
    if repository
        .and_then(|repository| repository_remote_fetch_url(repository, "upstream"))
        .is_none()
    {
        eprintln!("--forked requires the clone to be configured for the fork-PR workflow:");
        eprintln!("  origin -> your fork; upstream -> the upstream repo.");
        eprintln!("See docs/forked.md for the full remote-add walkthrough;");
        eprintln!("the minimum is:");
        eprintln!("  git remote add upstream <https-or-ssh-url-of-upstream-repo>");
        return ExitCode::FAILURE;
    }
    // Resolve one remote at a time: the legacy verb returned on the first
    // failure, so a broken `origin` must not also report `upstream`.
    let Some(fork_repo) = remote_repo(repository, "origin") else {
        return ExitCode::from(2);
    };
    let Some(upstream_repo) = remote_repo(repository, "upstream") else {
        return ExitCode::from(2);
    };
    let bootstrap_tmpdir = match bootstrap_tmpdir(explicit) {
        Ok(tmpdir) => tmpdir,
        Err(message) => {
            eprintln!("admission fork-env: could not create bootstrap tmpdir: {message}");
            return ExitCode::from(2);
        }
    };
    if let Err(message) = write_caller_env(&bootstrap_tmpdir, &fork_repo) {
        eprintln!("admission fork-env: could not write caller-env.sh: {message}");
        return ExitCode::from(2);
    }
    let fork_owner = fork_repo.split_once('/').map_or("", |(owner, _name)| owner);
    emit_kv("BOOTSTRAP_TMPDIR", &bootstrap_tmpdir.to_string_lossy());
    emit_kv(
        "CALLER_ENV_PATH",
        &bootstrap_tmpdir.join(CALLER_ENV_NAME).to_string_lossy(),
    );
    emit_kv("FORK_REPO", &fork_repo);
    emit_kv("UPSTREAM_REPO", &upstream_repo);
    emit_kv("FORK_OWNER", fork_owner);
    emit_kv("FORKED_TARGET", "true");
    ExitCode::SUCCESS
}

fn remote_repo(repository: Option<&GixRepository>, remote: &str) -> Option<String> {
    match resolve_remote_repo(remote, repository) {
        RemoteRepoResult::Ok { repo } => Some(repo),
        RemoteRepoResult::Usage | RemoteRepoResult::ParseFailure => {
            eprintln!("github-remote-repo.sh: cannot parse remote");
            None
        }
    }
}

/// Create or adopt the bootstrap tmpdir that carries `caller-env.sh`.
///
/// The directory outlives this process: Step 0 reads `CALLER_ENV_PATH` from it.
/// A minted directory is private (`0700`) like `mkdtemp`; `tempfile` alone
/// leaves it at the umask default, which would publish the fork bootstrap's
/// listing to every local user. An explicitly named directory keeps the
/// caller's own mode, as the legacy `mkdir(parents=True)` did.
fn bootstrap_tmpdir(explicit: Option<PathBuf>) -> Result<PathBuf, String> {
    if let Some(explicit) = explicit {
        std::fs::create_dir_all(&explicit).map_err(|error| error.to_string())?;
        return Ok(explicit);
    }
    let base = env::var_os("TMPDIR")
        .filter(|value| !value.is_empty())
        .map_or_else(|| PathBuf::from(TMP_FALLBACK), PathBuf::from);
    tempfile::Builder::new()
        .prefix(FORK_BOOTSTRAP_PREFIX)
        .tempdir_in(&base)
        .and_then(|directory| {
            let path = directory.keep();
            make_private(&path)?;
            Ok(path)
        })
        .map_err(|error| error.to_string())
}

/// Restrict a freshly minted directory to its owner.
#[cfg(unix)]
fn make_private(path: &Path) -> std::io::Result<()> {
    use std::os::unix::fs::PermissionsExt as _;

    std::fs::set_permissions(path, std::fs::Permissions::from_mode(0o700))
}

#[cfg(not(unix))]
fn make_private(_path: &Path) -> std::io::Result<()> {
    Ok(())
}

/// Publish `caller-env.sh` atomically below the bootstrap directory.
///
/// The name is confined relative to the canonical root so a symlinked ancestor
/// such as macOS `/var` cannot make containment fail.
fn write_caller_env(bootstrap_tmpdir: &Path, fork_repo: &str) -> Result<(), String> {
    let root = TemporaryRoot::resolve(Some(bootstrap_tmpdir)).map_err(|error| error.to_string())?;
    let confined = root
        .confine(CALLER_ENV_NAME, PathIntent::Write)
        .map_err(|error| error.to_string())?;
    atomic_write_utf8(&confined, &format!("REPO={fork_repo}\n"), 0o600)
        .map_err(|error| error.to_string())
}

fn fork_env_usage_error(error: &str) -> ExitCode {
    eprint!("{FORK_ENV_USAGE}");
    eprintln!("admission fork-env: error: {error}");
    ExitCode::from(2)
}

/// Report whether a help action fires for this line.
///
/// `argparse` runs the `-h` action while consuming arguments, so a help token
/// that a preceding option swallows as its value never triggers help. Callers
/// check for a mid-parse value error first.
fn wants_help(arguments: &[OsString]) -> bool {
    arguments
        .iter()
        .any(|argument| argument == "--help" || argument == "-h")
}

fn open_cwd_repository() -> Option<GixRepository> {
    GixRepository::discover(env::current_dir().ok()?).ok()
}

#[cfg(test)]
mod tests {
    use super::{
        Admission, CALLER_ENV_NAME, GATE_HELP, GATE_USAGE, GitOutcome, GixRepository, IssueSubject,
        Path, PathBuf, PreflightGit, STALLED_RUN_SENTINEL, bootstrap_tmpdir, clean_tree_refusal,
        clear_stalled_sentinel, current_branch_name, emit_decision, fetch_origin_main,
        fresh_decision, gate_issue, preflight_flags, publish_fork_env, rebase_onto_origin_main,
        resume_decision, run_git, sentinel_adopts, short_branch_name, write_caller_env,
    };
    use crate::argparse_compat::parse;
    use larch_core::{DESIGNED_PREFIX, MANAGED_PREFIXES, RefName, RepositoryRead};
    use larch_test_support::{
        GitFixture, GitFixtureError, GitRepository as GitRepositoryFixture, GitRepositoryBuilder,
        TestWorkspace,
    };
    use std::{ffi::OsString, process::ExitCode};

    /// Compose a title from a shared prefix constant, never an inline literal.
    fn titled(prefix: &str) -> String {
        format!("{prefix}Do the thing")
    }

    fn arguments(values: &[&str]) -> Vec<OsString> {
        values.iter().map(OsString::from).collect()
    }

    fn subject(title: &str) -> IssueSubject {
        IssueSubject {
            title: title.to_owned(),
            closed: false,
            audit_report_label: false,
        }
    }

    fn refused(result: &'static str, title: &str, code: u8) -> Admission {
        Admission::Refused {
            result,
            title: Some(title.to_owned()),
            code,
        }
    }

    /// A blocker read that fails the test if the ladder reaches it.
    fn unreachable_blockers() -> Vec<u64> {
        panic!("the decision must refuse before reading blockers");
    }

    #[test]
    fn a_sentinel_adopts_only_its_own_issue_and_run() {
        let workspace = TestWorkspace::new().expect("workspace");
        let session = workspace.create_dir("session").expect("session dir");
        let tmpdir = session.to_string_lossy().into_owned();
        let write = |contents: &str| {
            workspace
                .write("session/parent-issue.md", contents)
                .expect("sentinel");
        };

        // No tmpdir, and a tmpdir with no sentinel, both decline adoption.
        assert!(!sentinel_adopts(8059, "", "run-1"));
        assert!(!sentinel_adopts(8059, &tmpdir, "run-1"));

        write("ISSUE_NUMBER=8059\nRUN_ID=run-1\n");
        assert!(sentinel_adopts(8059, &tmpdir, "run-1"));
        assert!(
            !sentinel_adopts(8059, &tmpdir, "run-2"),
            "another run's sentinel must not adopt this run's target"
        );
        assert!(!sentinel_adopts(9999, &tmpdir, "run-1"));

        // A sentinel with no run id belongs to whichever run finds it.
        write("ISSUE_NUMBER=8059\n");
        assert!(sentinel_adopts(8059, &tmpdir, "run-1"));
        assert!(sentinel_adopts(8059, &tmpdir, "run-2"));

        // Surrounding whitespace and a malformed issue number both fail closed.
        write("ISSUE_NUMBER= 8059 \nRUN_ID= run-1 \n");
        assert!(sentinel_adopts(8059, &tmpdir, "run-1"));
        write("ISSUE_NUMBER=not-a-number\n");
        assert!(!sentinel_adopts(8059, &tmpdir, "run-1"));
    }

    #[test]
    fn the_fork_bootstrap_directory_is_private_and_carries_the_fork_repo() {
        let workspace = TestWorkspace::new().expect("workspace");
        let explicit = workspace.path("bootstrap").expect("bootstrap path");

        let created = bootstrap_tmpdir(Some(explicit.clone())).expect("explicit tmpdir");
        assert_eq!(created, explicit);
        write_caller_env(&created, "zhupanov/larch").expect("caller env");

        let caller_env = created.join(CALLER_ENV_NAME);
        assert_eq!(
            std::fs::read_to_string(&caller_env).expect("caller env text"),
            "REPO=zhupanov/larch\n"
        );
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt as _;

            let mode = |path: &std::path::Path| {
                std::fs::metadata(path)
                    .expect("metadata")
                    .permissions()
                    .mode()
                    & 0o777
            };
            // The legacy verb left an explicitly named directory at the caller's
            // own mode and wrote the file itself private.
            assert_eq!(mode(&caller_env), 0o600);
        }

        // A second publish overwrites in place rather than failing.
        write_caller_env(&created, "other/fork").expect("republish");
        assert_eq!(
            std::fs::read_to_string(&caller_env).expect("caller env text"),
            "REPO=other/fork\n"
        );
    }

    #[cfg(unix)]
    #[test]
    fn a_minted_fork_bootstrap_directory_is_owner_only() {
        use std::os::unix::fs::PermissionsExt as _;

        let workspace = TestWorkspace::new().expect("workspace");
        let base = workspace.create_dir("tmp").expect("temp base");
        let minted: std::path::PathBuf = tempfile::Builder::new()
            .prefix(super::FORK_BOOTSTRAP_PREFIX)
            .tempdir_in(&base)
            .expect("minted tmpdir")
            .keep();
        super::make_private(&minted).expect("private mode");

        let mode = std::fs::metadata(&minted)
            .expect("metadata")
            .permissions()
            .mode()
            & 0o777;
        assert_eq!(mode, 0o700, "mkdtemp published a private directory");
    }

    /// A seeded repository on `main`, or `None` when installed Git is absent.
    ///
    /// The fixture reports its own skip reason; these cases then pass vacuously
    /// rather than failing an environment that cannot host a real repository.
    fn repository() -> Option<(GitRepositoryFixture, GixRepository)> {
        let fixture = match GitRepositoryBuilder::new(GitFixture::Refs).build() {
            Ok(fixture) => fixture,
            Err(GitFixtureError::Skip(_reason)) => return None,
            Err(error) => panic!("git fixture failed: {error}"),
        };
        let opened = GixRepository::discover(fixture.root()).expect("open fixture");
        Some((fixture, opened))
    }

    #[test]
    fn preflight_rules_read_one_repository() {
        let Some((fixture, opened)) = repository() else {
            return;
        };
        assert_eq!(current_branch_name(Some(&opened)), "main");
        assert_eq!(
            current_branch_name(None),
            "",
            "an unreadable repository reports no branch, which refuses"
        );

        // A clean tree with no stash admits; a new untracked file refuses.
        assert!(clean_tree_refusal(Some(&opened)).is_none());
        assert_eq!(
            clean_tree_refusal(None),
            Some(ExitCode::from(2)),
            "an unreadable repository is a cleanliness refusal, not a pass"
        );
        fixture.write("stray.txt", b"stray\n").expect("stray file");
        assert_eq!(clean_tree_refusal(Some(&opened)), Some(ExitCode::from(2)));

        // Stashed work refuses even once the tree itself reads clean again.
        fixture.git(["stash", "push", "-u"]).expect("stash");
        assert_eq!(clean_tree_refusal(Some(&opened)), Some(ExitCode::from(2)));
    }

    #[test]
    fn the_stalled_sentinel_survives_only_a_dirty_skip_clean_entry() {
        let Some((fixture, opened)) = repository() else {
            return;
        };
        let sentinel = PathBuf::from(
            String::from_utf8_lossy(opened.location().git_dir.as_bytes()).into_owned(),
        )
        .join(STALLED_RUN_SENTINEL);
        let plant = || std::fs::write(&sentinel, "stalled\n").expect("plant sentinel");

        plant();
        clear_stalled_sentinel(Some(&opened), false);
        assert!(
            !sentinel.exists(),
            "a clean-checked entry clears the marker"
        );

        plant();
        clear_stalled_sentinel(None, false);
        assert!(sentinel.exists(), "no repository means no removal");

        // A clean tree clears the marker even when the caller skipped the check.
        clear_stalled_sentinel(Some(&opened), true);
        assert!(!sentinel.exists());

        // A dirty tree under --skip-clean-check keeps the resuming run's marker.
        fixture.write("stray.txt", b"stray\n").expect("stray file");
        plant();
        clear_stalled_sentinel(Some(&opened), true);
        assert!(sentinel.exists());
    }

    #[test]
    fn fork_env_publishes_only_from_a_fork_configured_clone() {
        let Some((fixture, opened)) = repository() else {
            return;
        };
        let bootstrap = fixture.workspace_root().join("bootstrap");

        // No `upstream` remote: the clone is not configured for fork PRs.
        assert_eq!(
            publish_fork_env(Some(&opened), Some(bootstrap.clone())),
            ExitCode::FAILURE
        );
        assert_eq!(
            publish_fork_env(None, Some(bootstrap.clone())),
            ExitCode::FAILURE,
            "no repository reads the same as no fork configuration"
        );

        // An upstream that is not a GitHub remote cannot yield a slug.
        fixture
            .git(["remote", "add", "upstream", "/not/a/github/url"])
            .expect("add upstream");
        assert_eq!(
            publish_fork_env(Some(&opened), Some(bootstrap.clone())),
            ExitCode::from(2)
        );

        // With both remotes resolvable the metadata publishes.
        fixture
            .git([
                "remote",
                "set-url",
                "upstream",
                "https://github.com/character-ai/larch.git",
            ])
            .expect("set upstream url");
        fixture
            .git([
                "remote",
                "add",
                "origin",
                "git@github.com:zhupanov/larch.git",
            ])
            .expect("add origin");
        assert_eq!(
            publish_fork_env(Some(&opened), Some(bootstrap.clone())),
            ExitCode::SUCCESS
        );
        assert_eq!(
            std::fs::read_to_string(bootstrap.join(CALLER_ENV_NAME)).expect("caller env"),
            "REPO=zhupanov/larch\n"
        );
    }

    #[test]
    fn preflight_git_mutations_report_a_non_transient_local_failure() {
        let Some((fixture, _opened)) = repository() else {
            return;
        };
        let root = fixture.root();

        // The fixture configures no `origin` remote, so the fetch fails at once:
        // a missing remote is not a transient network condition, so the retry
        // loop gives up on the first attempt rather than sleeping.
        assert!(!fetch_origin_main(root));

        // It does carry `refs/remotes/origin/main`, so the rebase is a no-op
        // that succeeds without the abort path running.
        assert!(rebase_onto_origin_main(root));

        // Aborting with no rebase in progress is a nonzero Git exit, which the
        // runner reports as a failure rather than panicking.
        assert_eq!(
            run_git(root, &PreflightGit::AbortRebase),
            GitOutcome::Failed { transient: false }
        );

        // A relative working directory never reaches Git: the policy rejects it.
        assert_eq!(
            run_git(Path::new("relative/path"), &PreflightGit::AbortRebase),
            GitOutcome::Failed { transient: false }
        );
    }

    #[test]
    fn every_decision_emits_its_own_exit_code() {
        assert_eq!(
            emit_decision(&Admission::Pass { resume: false }),
            ExitCode::SUCCESS
        );
        assert_eq!(
            emit_decision(&Admission::Pass { resume: true }),
            ExitCode::SUCCESS
        );
        assert_eq!(
            emit_decision(&Admission::Blocked(vec![7, 9])),
            ExitCode::from(4)
        );
        assert_eq!(
            emit_decision(&refused("managed-prefix", &titled(MANAGED_PREFIXES[2]), 5)),
            ExitCode::from(5)
        );
        assert_eq!(
            emit_decision(&Admission::Refused {
                result: "audit-report-label",
                title: None,
                code: 6,
            }),
            ExitCode::from(6)
        );
    }

    #[test]
    fn the_gate_reports_argparse_refusals_before_reading_the_issue() {
        let options = ["--issue", "--repo"];
        assert_eq!(
            gate_issue(&parse(&arguments(&["--issue", "8059"]), &options, 0)),
            Some("8059".to_owned())
        );
        // Missing required, mid-parse value error, and surplus token each refuse.
        assert_eq!(gate_issue(&parse(&arguments(&[]), &options, 0)), None);
        assert_eq!(
            gate_issue(&parse(&arguments(&["--issue"]), &options, 0)),
            None
        );
        assert_eq!(
            gate_issue(&parse(
                &arguments(&["--issue", "8059", "extra"]),
                &options,
                0
            )),
            None
        );
    }

    #[test]
    fn every_lifecycle_prefix_refuses_a_fresh_run_with_its_own_code() {
        for prefix in MANAGED_PREFIXES {
            let title = titled(prefix);
            assert_eq!(
                fresh_decision(&subject(&title), unreachable_blockers),
                refused("managed-prefix", &title, 5),
                "{prefix}"
            );
        }
        assert_eq!(
            fresh_decision(
                &subject("[BUG REPORT] Something broke"),
                unreachable_blockers
            ),
            refused("report-title", "[BUG REPORT] Something broke", 7)
        );
        assert_eq!(
            fresh_decision(&subject("Plain title"), Vec::new),
            refused("missing-designed-prefix", "Plain title", 5)
        );
    }

    #[test]
    fn only_the_designed_prefix_admits_a_fresh_run() {
        let designed = titled(DESIGNED_PREFIX);
        assert_eq!(
            fresh_decision(&subject(&designed), Vec::new),
            Admission::Pass { resume: false }
        );
        // A near miss on either side of the exact prefix still refuses.
        let unspaced = DESIGNED_PREFIX.trim_end().to_owned() + "No space";
        assert_eq!(
            fresh_decision(&subject(&unspaced), Vec::new),
            refused("missing-designed-prefix", &unspaced, 5)
        );
        let embedded = format!("Re: {DESIGNED_PREFIX}elsewhere");
        assert_eq!(
            fresh_decision(&subject(&embedded), Vec::new),
            refused("missing-designed-prefix", &embedded, 5)
        );
    }

    #[test]
    fn an_audit_report_label_refuses_after_the_title_checks() {
        let labeled = IssueSubject {
            audit_report_label: true,
            ..subject(&titled(DESIGNED_PREFIX))
        };
        assert_eq!(
            fresh_decision(&labeled, unreachable_blockers),
            Admission::Refused {
                result: "audit-report-label",
                title: None,
                code: 6,
            }
        );
    }

    #[test]
    fn open_blockers_outrank_the_designed_prefix_check() {
        assert_eq!(
            fresh_decision(&subject(&titled(DESIGNED_PREFIX)), || vec![7, 9]),
            Admission::Blocked(vec![7, 9])
        );
        assert_eq!(
            fresh_decision(&subject("Plain title"), || vec![7]),
            Admission::Blocked(vec![7])
        );
    }

    #[test]
    fn a_resumed_run_reads_blockers_first_and_ignores_its_own_prefix() {
        let implementing = titled(MANAGED_PREFIXES[1]);
        assert_eq!(
            resume_decision(&implementing, Vec::new),
            Admission::Pass { resume: true }
        );
        assert_eq!(
            resume_decision(&implementing, || vec![4]),
            Admission::Blocked(vec![4])
        );
        assert_eq!(
            resume_decision("[weekly report] Numbers", Vec::new),
            refused("report-title", "[weekly report] Numbers", 7)
        );
    }

    #[test]
    fn the_help_block_opens_with_the_usage_line() {
        assert!(GATE_HELP.starts_with(GATE_USAGE));
    }

    #[test]
    fn branch_names_drop_only_the_heads_prefix() {
        assert_eq!(
            short_branch_name(&RefName::new(b"refs/heads/main".to_vec())),
            "main"
        );
        assert_eq!(short_branch_name(&RefName::new(b"main".to_vec())), "main");
    }

    #[test]
    fn preflight_accepts_abbreviations_and_names_the_first_stray_token() {
        assert_eq!(
            preflight_flags(&arguments(&["--skip-b", "--skip-clean-check"])),
            Ok((true, true))
        );
        assert_eq!(preflight_flags(&arguments(&[])), Ok((false, false)));
        assert_eq!(
            preflight_flags(&arguments(&["--skip-branch-check", "extra"])),
            Err("extra".to_owned())
        );
        assert_eq!(
            preflight_flags(&arguments(&["--bogus"])),
            Err("--bogus".to_owned())
        );
    }
}
