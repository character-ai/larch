//! Rust owner for the standalone `/complete-umbrella` leaf ship lifecycle.
//! Deterministic leaf ship driver for one umbrella leaf.
//!
//! The durable state is independent of `/implement`. A resumed run classifies
//! its persisted PR before any checkout or Git mutation, then re-enters the
//! bounded reconcile, CI, merge, and post-merge state machine.
//! Repository reads use gix; installed Git effects use closed `GitCli` requests.

// The frozen standalone transaction stays reviewable while honoring #8629's
// explicit compatibility-line budget.
#[rustfmt::skip]
mod implementation {

use std::{
    collections::{BTreeMap, BTreeSet},
    ffi::OsString,
    fmt::Write as _,
    fs,
    path::{Path, PathBuf},
    process::ExitCode,
    sync::LazyLock,
    thread,
    time::Duration,
};

use clap::Args;
use larch_adapters::{
    BranchMutationRequest, CheckoutRequest, ExactDiffRequest, FetchRequest, ForceWithLease, GitCliError, GitRef, GitRefspec, GitRemote, GixRepository, LsRemoteRequest,
    PushRequest, RebaseRequest,
    github::{IssueMutationOwner, MergeStateStatus, PullRequest, PullRequestSpec, PullRequestState, ReleaseCandidatePullRequestState},
};
use larch_core::{
    ChildEnvironment, DuplicatePolicy, GitHubIssueState, GitHubRepositoryRef, GitPath, Head, KvDocument, ParseOptions, RepositoryRead, Revision, StatusOptions,
    complete_umbrella_active_leaf_title, complete_umbrella_done_leaf_title, parse_complete_umbrella_numstat, redact_outbound, ship_pr_title,
};
use regex::Regex;

use crate::{
    argparse_compat::{ParsedCommandLine, choice_error, parse_python_int, parse_required_with_help, python_repr, usage_error},
    complete_umbrella_commands::{exact_title_request, operator_authorization},
    git_commands::{TRANSIENT_ATTEMPTS, is_transient_net, sleep_before_retry},
    git_command_runtime::GitCommandRuntime,
    github_repository_resolution::repository_ref,
    github_service::{ServiceFailure, with_github_service},
    implement_child_seam::{delegate_larch_with_options_in, delegate_merge_wait, verify_merge_wait},
    session_artifact_support::{canonical_directory, read_expected_file, temporary_root, write_private_file},
    ship_pr_commands::head_subject,
};

const STATE_BASENAME: &str = "complete-umbrella-ship.env";
const PROGRAM: &str = "cli.py complete-umbrella ship-leaf";
const USAGE: &str = concat!(
    "usage: cli.py complete-umbrella ship-leaf [-h] --mode\n",
    "                                          {prepare,ship,verify,line-budget}\n",
    "                                          --repository REPOSITORY --repo-root\n",
    "                                          REPO_ROOT --handoff-root\n",
    "                                          HANDOFF_ROOT --umbrella UMBRELLA\n",
    "                                          --leaf LEAF",
);
const HELP: &str = concat!(
    "usage: cli.py complete-umbrella ship-leaf [-h] --mode\n",
    "                                          {prepare,ship,verify,line-budget}\n",
    "                                          --repository REPOSITORY --repo-root\n",
    "                                          REPO_ROOT --handoff-root\n",
    "                                          HANDOFF_ROOT --umbrella UMBRELLA\n",
    "                                          --leaf LEAF\n\n",
    "options:\n",
    "  -h, --help            show this help message and exit\n",
    "  --mode {prepare,ship,verify,line-budget}\n",
    "  --repository REPOSITORY\n",
    "  --repo-root REPO_ROOT\n",
    "  --handoff-root HANDOFF_ROOT\n",
    "  --umbrella UMBRELLA\n",
    "  --leaf LEAF",
);
const OPTIONS: &[&str] = &["--mode", "--repository", "--repo-root", "--handoff-root", "--umbrella", "--leaf"];
const REQUIRED: &[&str] = OPTIONS;
const STATE_LIMIT: u64 = 64 * 1024;
const CI_POLL: Duration = Duration::from_secs(300);
const CI_POLLS: usize = 288;
const CI_LOG_ATTEMPTS: usize = 3;
const CI_FIX_CAP: u64 = 30;
const CONFLICT_FIX_CAP: u64 = 3;
const RECONCILE_CAP: u64 = 3;
const ISSUE_CLOSE_ATTEMPTS: usize = 12;
const ISSUE_CLOSE_POLL: Duration = Duration::from_secs(5);
const RUST_LINE_LIMIT: u64 = 1_500;
const MERGE_WAIT: Duration = Duration::from_secs(86_500);
const CHILD_TIMEOUT: Duration = Duration::from_secs(600);
const STATUSES: [&str; 8] = [
    "prepared",
    "monitoring",
    "ci_failed",
    "needs_conflict_fix",
    "queued",
    "merged",
    "finalizing",
    "complete",
];
const STATE_KEYS: [&str; 14] = [
    "SCHEMA",
    "REPOSITORY",
    "UMBRELLA",
    "LEAF",
    "BRANCH",
    "HEAD_SHA",
    "PR_NUMBER",
    "PR_URL",
    "STATUS",
    "CI_ERRORS_FILE",
    "CI_FIX_ATTEMPTS",
    "CONFLICT_FILES",
    "CONFLICT_FIX_ATTEMPTS",
    "MAIN_RECONCILE_ATTEMPTS",
];

static ISSUE_REFERENCE: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"#[1-9][0-9]*").expect("issue reference expression"));
static CHIEF_MARKER: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"(?i)\[CHIEF[ \t]+UMBRELLA\]").expect("chief umbrella expression"));

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum ShipMode {
    Prepare,
    Ship,
    Verify,
    LineBudget,
}

#[derive(Args)]
#[command(trailing_var_arg = true)]
pub struct ShipLeafArguments {
    #[arg(allow_hyphen_values = true)]
    arguments: Vec<OsString>,
}

struct ParsedArguments {
    mode: ShipMode,
    repository: String,
    repo_root: PathBuf,
    handoff_root: PathBuf,
    umbrella: i64,
    leaf: i64,
}

struct Request {
    repository: GitHubRepositoryRef,
    slug: String,
    repo_root: PathBuf,
    handoff_root: PathBuf,
    umbrella: u64,
    leaf: u64,
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct ShipState {
    repository: String,
    umbrella: u64,
    leaf: u64,
    branch: String,
    head_sha: String,
    pr_number: u64,
    pr_url: String,
    status: String,
    ci_errors_file: String,
    ci_fix_attempts: u64,
    conflict_files: String,
    conflict_fix_attempts: u64,
    main_reconcile_attempts: u64,
}

impl ShipState {
    fn prepared(request: &Request) -> Self {
        Self {
            repository: request.slug.clone(),
            umbrella: request.umbrella,
            leaf: request.leaf,
            branch: String::new(),
            head_sha: String::new(),
            pr_number: 0,
            pr_url: String::new(),
            status: "prepared".to_owned(),
            ci_errors_file: String::new(),
            ci_fix_attempts: 0,
            conflict_files: String::new(),
            conflict_fix_attempts: 0,
            main_reconcile_attempts: 0,
        }
    }

    fn parse(request: &Request, text: &str) -> Result<Self, String> {
        if text.contains('\r') {
            return Err("ship state contains a carriage return".to_owned());
        }
        if text.lines().any(|line| !line.is_empty() && !line.contains('=')) {
            return Err("ship state contains a malformed row".to_owned());
        }
        let values = KvDocument::parse(text, ParseOptions::environment())
            .map_err(|_| "ship state has missing, unknown, or duplicate keys".to_owned())?
            .select(DuplicatePolicy::Last);
        let observed = values.keys().map(String::as_str).collect::<BTreeSet<_>>();
        let expected = STATE_KEYS.into_iter().collect::<BTreeSet<_>>();
        if observed != expected {
            return Err("ship state has missing, unknown, or duplicate keys".to_owned());
        }
        let value = |key: &str| values.get(key).map(String::as_str).unwrap_or_default();
        if value("SCHEMA") != "1" {
            return Err("ship state schema is unsupported".to_owned());
        }
        let number = |key: &str, empty: bool| -> Result<u64, String> {
            let raw = value(key);
            if empty && raw.is_empty() {
                return Ok(0);
            }
            raw.parse().map_err(|_| "ship state contains a non-numeric identity".to_owned())
        };
        let state = Self {
            repository: value("REPOSITORY").to_owned(),
            umbrella: number("UMBRELLA", false)?,
            leaf: number("LEAF", false)?,
            branch: value("BRANCH").to_owned(),
            head_sha: value("HEAD_SHA").to_owned(),
            pr_number: number("PR_NUMBER", true)?,
            pr_url: value("PR_URL").to_owned(),
            status: value("STATUS").to_owned(),
            ci_errors_file: value("CI_ERRORS_FILE").to_owned(),
            ci_fix_attempts: number("CI_FIX_ATTEMPTS", false)?,
            conflict_files: value("CONFLICT_FILES").to_owned(),
            conflict_fix_attempts: number("CONFLICT_FIX_ATTEMPTS", false)?,
            main_reconcile_attempts: number("MAIN_RECONCILE_ATTEMPTS", false)?,
        };
        state.validate(request)?;
        Ok(state)
    }

    fn render(&self, request: &Request) -> Result<String, String> {
        self.validate(request)?;
        let pr_number = if self.pr_number == 0 { String::new() } else { self.pr_number.to_string() };
        let rows = [
            ("SCHEMA", "1".to_owned()),
            ("REPOSITORY", self.repository.clone()),
            ("UMBRELLA", self.umbrella.to_string()),
            ("LEAF", self.leaf.to_string()),
            ("BRANCH", self.branch.clone()),
            ("HEAD_SHA", self.head_sha.clone()),
            ("PR_NUMBER", pr_number),
            ("PR_URL", self.pr_url.clone()),
            ("STATUS", self.status.clone()),
            ("CI_ERRORS_FILE", self.ci_errors_file.clone()),
            ("CI_FIX_ATTEMPTS", self.ci_fix_attempts.to_string()),
            ("CONFLICT_FILES", self.conflict_files.clone()),
            ("CONFLICT_FIX_ATTEMPTS", self.conflict_fix_attempts.to_string()),
            ("MAIN_RECONCILE_ATTEMPTS", self.main_reconcile_attempts.to_string()),
        ];
        if rows.iter().any(|(_, value)| value.contains(['\r', '\n'])) {
            return Err("ship state contains a line break".to_owned());
        }
        let mut output = String::new();
        for (key, value) in rows {
            writeln!(output, "{key}={value}").expect("writing to String cannot fail");
        }
        Ok(output)
    }

    fn validate(&self, request: &Request) -> Result<(), String> {
        if !STATUSES.contains(&self.status.as_str()) {
            return Err(format!("invalid ship state status: {}", self.status));
        }
        if self.repository != request.slug {
            return Err("ship state identity does not match the live leaf".to_owned());
        }
        if self.umbrella != request.umbrella || self.leaf != request.leaf {
            return Err("ship state identity does not match the live leaf".to_owned());
        }
        if self.ci_fix_attempts > CI_FIX_CAP {
            return Err("ship state exceeds the CI fix attempt cap".to_owned());
        }
        if self.conflict_fix_attempts > CONFLICT_FIX_CAP {
            return Err("ship state exceeds the conflict fix attempt cap".to_owned());
        }
        if self.main_reconcile_attempts > RECONCILE_CAP {
            return Err("ship state exceeds the main-reconcile attempt cap".to_owned());
        }
        let branch = !self.branch.is_empty();
        let head = !self.head_sha.is_empty();
        let pr = self.pr_number != 0;
        let url = !self.pr_url.is_empty();
        if branch && (!valid_branch(&self.branch) || self.branch != expected_branch(self.leaf)) {
            return Err("ship state branch does not match the leaf identity".to_owned());
        }
        if head && !valid_oid(&self.head_sha) {
            return Err("ship state contains an invalid head SHA".to_owned());
        }
        if pr != url || (url && self.pr_url != expected_pr_url(request, self.pr_number)) {
            return Err("ship state contains an invalid PR URL".to_owned());
        }
        if self.status == "needs_conflict_fix" {
            if !branch || !head {
                return Err("conflict ship state lacks branch identity".to_owned());
            }
        } else if [branch, head, pr, url].iter().any(|value| *value) && ![branch, head, pr, url].iter().all(|value| *value) {
            return Err("ship state contains a partial PR identity".to_owned());
        } else if self.status != "prepared" && ![branch, head, pr, url].iter().all(|value| *value) {
            return Err("advanced ship state lacks a complete PR identity".to_owned());
        }
        if self.status == "ci_failed" {
            validate_ci_file(request, &self.ci_errors_file)?;
        } else if !self.ci_errors_file.is_empty() {
            return Err("non-failed ship state contains a CI errors file".to_owned());
        }
        if self.status == "needs_conflict_fix" {
            validate_conflicts(&self.conflict_files)?;
        } else if !self.conflict_files.is_empty() {
            return Err("non-conflict ship state contains conflict files".to_owned());
        }
        Ok(())
    }

    fn set_status(&mut self, status: &str) {
        status.clone_into(&mut self.status);
    }
}

struct ShipOutcome {
    status: String,
    pr_number: u64,
    pr_url: String,
    ci_errors_file: String,
    conflict_files: String,
    detail: String,
}

impl ShipOutcome {
    fn from_state(state: &ShipState, status: &str) -> Self {
        Self {
            status: status.to_owned(),
            pr_number: state.pr_number,
            pr_url: state.pr_url.clone(),
            ci_errors_file: state.ci_errors_file.clone(),
            conflict_files: state.conflict_files.clone(),
            detail: String::new(),
        }
    }

    fn error(detail: String) -> Self {
        Self {
            status: "error".to_owned(),
            pr_number: 0,
            pr_url: String::new(),
            ci_errors_file: String::new(),
            conflict_files: String::new(),
            detail,
        }
    }
}

struct RustBudget {
    status: &'static str,
    base_sha: String,
    head_sha: String,
    added_lines: Option<u64>,
}

enum Reconcile {
    Clean { rebased: bool },
    Conflict { files: String, original_head: String },
}

enum MergeResult {
    Merged,
    Queued,
    Reconcile,
    RetryCi,
}

#[must_use]
pub fn run(arguments: &ShipLeafArguments) -> ExitCode {
    let parsed = match parse_arguments(&arguments.arguments) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let result = Request::load(&parsed).and_then(|request| match parsed.mode {
        ShipMode::Prepare => prepare(&request).map(CommandOutcome::Ship),
        ShipMode::Ship => ship(&request).map(CommandOutcome::Ship),
        ShipMode::Verify => verify(&request).map(CommandOutcome::Ship),
        ShipMode::LineBudget => rust_budget(&request).map(CommandOutcome::Budget),
    });
    match result {
        Ok(CommandOutcome::Ship(outcome)) => {
            emit_ship(&outcome);
            ExitCode::SUCCESS
        }
        Ok(CommandOutcome::Budget(outcome)) => {
            emit_budget(&outcome);
            ExitCode::SUCCESS
        }
        Err(error) => {
            emit_ship(&ShipOutcome::error(error));
            ExitCode::FAILURE
        }
    }
}

enum CommandOutcome {
    Ship(ShipOutcome),
    Budget(RustBudget),
}

impl Request {
    fn load(arguments: &ParsedArguments) -> Result<Self, String> {
        let repository = repository_ref(&arguments.repository).map_err(|()| "repository must use OWNER/REPO syntax".to_owned())?;
        if arguments.umbrella == 0 || arguments.leaf == 0 {
            return Err("umbrella and leaf must be positive integers".to_owned());
        }
        let (Ok(umbrella), Ok(leaf)) = (u64::try_from(arguments.umbrella), u64::try_from(arguments.leaf)) else {
            return Err("umbrella and leaf must be positive integers".to_owned());
        };
        let repo_root = canonical_directory(&arguments.repo_root, "--repo-root")?;
        let handoff = temporary_root(&arguments.handoff_root, "--handoff-root")?;
        Ok(Self {
            repository,
            slug: arguments.repository.clone(),
            repo_root,
            handoff_root: handoff.path().to_path_buf(),
            umbrella,
            leaf,
        })
    }
}

fn parse_arguments(arguments: &[OsString]) -> Result<ParsedArguments, ExitCode> {
    if let Some(error) = choice_error(arguments, OPTIONS, &[("--mode", &["prepare", "ship", "verify", "line-budget"])]) {
        return Err(usage_error(USAGE, PROGRAM, &error, 2));
    }
    let parsed = parse_required_with_help(arguments, PROGRAM, USAGE, HELP, OPTIONS, &[], REQUIRED)?;
    let text = |option: &str| parsed.value(option).map(|value| value.to_string_lossy().into_owned()).unwrap_or_default();
    let mode = match text("--mode").as_str() {
        "prepare" => ShipMode::Prepare,
        "ship" => ShipMode::Ship,
        "verify" => ShipMode::Verify,
        "line-budget" => ShipMode::LineBudget,
        _ => unreachable!("choice validation admits only fixed modes"),
    };
    Ok(ParsedArguments {
        mode,
        repository: text("--repository"),
        repo_root: text("--repo-root").into(),
        handoff_root: text("--handoff-root").into(),
        umbrella: integer_argument(&parsed, "--umbrella")?,
        leaf: integer_argument(&parsed, "--leaf")?,
    })
}

fn integer_argument(parsed: &ParsedCommandLine, option: &str) -> Result<i64, ExitCode> {
    let raw = parsed.value(option).map(|value| value.to_string_lossy()).unwrap_or_default();
    parse_python_int(&raw).ok_or_else(|| {
        usage_error(USAGE, PROGRAM, &format!("argument {option}: invalid int value: {}", python_repr(&raw)), 2)
    })
}

fn prepare(request: &Request) -> Result<ShipOutcome, String> {
    mutate_leaf_title(request, false)?;
    let state = if let Some(existing) = read_state(request)?
        && existing.pr_number != 0
    {
        existing
    } else {
        ShipState::prepared(request)
    };
    write_state(request, &state)?;
    Ok(ShipOutcome::from_state(&state, "prepared"))
}

fn ship(request: &Request) -> Result<ShipOutcome, String> {
    let mut state = read_state(request)?.ok_or_else(|| "leaf prepare phase has not initialized ship state".to_owned())?;
    if state.status == "complete" {
        verify_complete(request, &state)?;
        return Ok(ShipOutcome::from_state(&state, "complete"));
    }

    if state.pr_number != 0 {
        let (pull, candidate) = read_pull(request, state.pr_number)?;
        require_pull_identity(request, &state, &pull, &candidate.head_oid)?;
        if pull.merged() && candidate.state == ReleaseCandidatePullRequestState::Merged {
            state.set_status("merged");
            state.pr_url = expected_pr_url(request, state.pr_number);
            state.ci_errors_file.clear();
            state.conflict_files.clear();
            write_state(request, &state)?;
        } else if pull.merged() || candidate.state == ReleaseCandidatePullRequestState::Merged || matches!(state.status.as_str(), "merged" | "finalizing") {
            return Err("persisted postmerge state contradicts the live PR".to_owned());
        } else if pull.state() == PullRequestState::Closed || candidate.state == ReleaseCandidatePullRequestState::Closed {
            return Err("implementation PR is closed without a merge".to_owned());
        }
    }

    if state.status == "queued" {
        wait_queued(request, &mut state)?;
    } else if state.status != "merged"
        && let Some(outcome) = run_premerge(request, &mut state)?
    {
        return Ok(outcome);
    }

    mutate_leaf_title(request, true)?;
    sync_main_and_delete(request, &state.branch)?;
    state.set_status("finalizing");
    state.ci_errors_file.clear();
    state.conflict_files.clear();
    write_state(request, &state)?;
    verify_complete(request, &state)?;
    state.set_status("complete");
    write_state(request, &state)?;
    if read_state(request)?.as_ref() != Some(&state) {
        return Err("complete ship marker read-back failed".to_owned());
    }
    Ok(ShipOutcome::from_state(&state, "complete"))
}

fn verify(request: &Request) -> Result<ShipOutcome, String> {
    let state = read_state(request)?
        .filter(|state| state.status == "complete")
        .ok_or_else(|| "leaf ship state is not complete".to_owned())?;
    verify_complete(request, &state)?;
    Ok(ShipOutcome::from_state(&state, "complete"))
}

#[allow(clippy::too_many_lines)] // One bounded pre-merge state-machine transaction.
fn run_premerge(request: &Request, state: &mut ShipState) -> Result<Option<ShipOutcome>, String> {
    let mut force = false;
    if state.status == "ci_failed" {
        require_changed_head(request, &state.head_sha, "CI failed but no fixer commit changed the branch head")?;
        if state.ci_fix_attempts >= CI_FIX_CAP {
            return Err("complete-umbrella CI fix attempt cap reached".to_owned());
        }
        state.ci_fix_attempts += 1;
        state.conflict_files.clear();
        force = true;
    } else if state.status == "needs_conflict_fix" {
        if rebase_in_progress(request)? {
            return Err("conflict fix left a rebase in progress".to_owned());
        }
        require_changed_head(request, &state.head_sha, "conflict fix did not change the branch head")?;
        if state.conflict_fix_attempts >= CONFLICT_FIX_CAP {
            return Err("complete-umbrella conflict fix attempt cap reached".to_owned());
        }
        state.conflict_fix_attempts += 1;
        state.conflict_files.clear();
        state.ci_errors_file.clear();
        force = true;
    }

    for _ in 0..=RECONCILE_CAP {
        match reconcile_main(request)? {
            Reconcile::Conflict { files, original_head } => {
                return conflict_handoff(request, state, files, original_head).map(Some);
            }
            Reconcile::Clean { rebased: true } => {
                if state.main_reconcile_attempts >= RECONCILE_CAP {
                    return Err("complete-umbrella main-reconcile attempt cap reached".to_owned());
                }
                state.main_reconcile_attempts += 1;
                force = true;
            }
            Reconcile::Clean { rebased: false } => {}
        }

        let (branch, head) = push_branch(request, force)?;
        force = false;
        if !state.branch.is_empty() && state.branch != branch {
            return Err("implementation branch changed after leaf preparation".to_owned());
        }
        let pull = ensure_pull(request, state, &branch)?;
        state.branch.clone_from(&branch);
        state.head_sha.clone_from(&head);
        state.pr_number = pull.number();
        state.pr_url = expected_pr_url(request, pull.number());
        state.set_status("monitoring");
        state.ci_errors_file.clear();
        state.conflict_files.clear();
        write_state(request, state)?;

        let (ci, failed_run) = wait_ci(request, pull.number())?;
        if ci == "merged" {
            confirm_merged(request, state)?;
            state.set_status("merged");
            write_state(request, state)?;
            return Ok(None);
        }
        if ci == "fail" {
            state.set_status("ci_failed");
            state.ci_errors_file = distill_failure(request, &failed_run)?.display().to_string();
            write_state(request, state)?;
            if state.ci_fix_attempts >= CI_FIX_CAP {
                return Err("complete-umbrella CI fix attempt cap reached after failed CI".to_owned());
            }
            return Ok(Some(ShipOutcome::from_state(state, "ci_failed")));
        }

        let merge_state = pull_review_state(request, pull.number(), &head)?;
        if merge_state == MergeStateStatus::Dirty {
            match reconcile_main(request)? {
                Reconcile::Conflict { files, original_head } => {
                    return conflict_handoff(request, state, files, original_head).map(Some);
                }
                Reconcile::Clean { rebased: true } => {
                    if state.main_reconcile_attempts >= RECONCILE_CAP {
                        return Err("complete-umbrella main-reconcile attempt cap reached".to_owned());
                    }
                    state.main_reconcile_attempts += 1;
                    let (_, new_head) = push_branch(request, true)?;
                    state.head_sha = new_head;
                    state.set_status("monitoring");
                    write_state(request, state)?;
                    force = false;
                    continue;
                }
                Reconcile::Clean { rebased: false } => {
                    return Err("PR is DIRTY but reconcile did not produce a rebased head".to_owned());
                }
            }
        }

        match submit_merge(request, state)? {
            MergeResult::Merged => {
                state.set_status("merged");
                write_state(request, state)?;
                return Ok(None);
            }
            MergeResult::Queued => {
                state.set_status("queued");
                write_state(request, state)?;
                wait_queued(request, state)?;
                return Ok(None);
            }
            MergeResult::Reconcile => force = true,
            MergeResult::RetryCi => {}
        }
    }
    Err("complete-umbrella main-reconcile attempt cap reached".to_owned())
}

fn conflict_handoff(request: &Request, state: &mut ShipState, files: String, original_head: String) -> Result<ShipOutcome, String> {
    if state.conflict_fix_attempts >= CONFLICT_FIX_CAP {
        abort_rebase(request)?;
        return Err("complete-umbrella conflict fix attempt cap reached".to_owned());
    }
    state.branch = expected_branch(request.leaf);
    state.head_sha = original_head;
    state.set_status("needs_conflict_fix");
    state.ci_errors_file.clear();
    state.conflict_files = files;
    write_state(request, state)?;
    let mut outcome = ShipOutcome::from_state(state, "needs_conflict_fix");
    "leaf branch conflicts with origin/main; resolve via MODE=conflict".clone_into(&mut outcome.detail);
    Ok(outcome)
}

fn read_state(request: &Request) -> Result<Option<ShipState>, String> {
    let path = request.handoff_root.join(STATE_BASENAME);
    match fs::symlink_metadata(&path) {
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => Ok(None),
        Err(error) => Err(format!("ship state read failed: {error}")),
        Ok(_) => read_expected_file(
            &path,
            &request.handoff_root,
            &temporary_root(&request.handoff_root, "--handoff-root")?,
            "ship state",
            STATE_LIMIT,
        )
        .and_then(|text| ShipState::parse(request, &text))
        .map(Some),
    }
}

fn write_state(request: &Request, state: &ShipState) -> Result<(), String> {
    write_private_file(
        &request.handoff_root.join(STATE_BASENAME),
        &state.render(request)?,
        &request.handoff_root,
        &temporary_root(&request.handoff_root, "--handoff-root")?,
    )
}

fn mutate_leaf_title(request: &Request, done: bool) -> Result<(), String> {
    with_github_service(async |service, cancellation| {
        let owner = IssueMutationOwner::new(service);
        let mut snapshot = owner
            .read_snapshot(&request.repository, request.leaf, cancellation)
            .await
            .map_err(|error| error.to_string())?;
        if !done && snapshot.state != GitHubIssueState::Open {
            return Err("leaf must be open before implementation starts".to_owned());
        }
        let title = if done {
            complete_umbrella_done_leaf_title(&snapshot.title, request.umbrella)
        } else {
            complete_umbrella_active_leaf_title(&snapshot.title, request.umbrella)
        }
        .map_err(str::to_owned)?;
        if title != snapshot.title {
            let mutation = exact_title_request(&snapshot, title.clone())?;
            snapshot = owner
                .apply(cancellation, &operator_authorization(), &mutation)
                .await
                .map_err(|error| error.to_string())?
                .after;
        }
        if !done {
            return (snapshot.state == GitHubIssueState::Open && snapshot.title == title)
                .then_some(())
                .ok_or_else(|| "active leaf title read-back failed".to_owned());
        }
        for attempt in 0..ISSUE_CLOSE_ATTEMPTS {
            if snapshot.state == GitHubIssueState::Closed && snapshot.title == title {
                return Ok(());
            }
            if attempt + 1 < ISSUE_CLOSE_ATTEMPTS {
                thread::sleep(ISSUE_CLOSE_POLL);
                snapshot = owner
                    .read_snapshot(&request.repository, request.leaf, cancellation)
                    .await
                    .map_err(|error| error.to_string())?;
            }
        }
        Err("leaf issue did not auto-close after the PR merge".to_owned())
    })
    .map_err(ServiceFailure::into_detail)
}

fn reconcile_main(request: &Request) -> Result<Reconcile, String> {
    ensure_clean(request)?;
    if rebase_in_progress(request)? {
        return Err("cannot reconcile while a rebase is already in progress".to_owned());
    }
    let (_, original_head) = expected_branch_head(request)?;
    fetch_main(request)?;
    let repo = repository(request)?;
    let head = repo.resolve_revision(&Revision::new(b"HEAD")).map_err(|error| error.to_string())?;
    let base = repo
        .resolve_revision(&Revision::new(b"origin/main"))
        .map_err(|_| "could not resolve origin/main before leaf reconcile".to_owned())?;
    if repo.is_ancestor(&base, &head).map_err(|error| error.to_string())? {
        return Ok(Reconcile::Clean { rebased: false });
    }
    let runtime = git_runtime(request)?;
    let rebased = runtime.runtime.block_on(runtime.git_cli().rebase(
        RebaseRequest::Start {
            onto: None,
            upstream: GitRef::new("origin/main").map_err(|error| error.to_string())?,
            branch: None,
        },
        &runtime.cancellation,
    ));
    if rebased.is_ok() {
        return Ok(Reconcile::Clean { rebased: true });
    }
    let status = repository(request)?
        .local_status(&StatusOptions::default())
        .map_err(|error| error.to_string())?;
    let mut files = status
        .unmerged
        .iter()
        .map(|entry| String::from_utf8_lossy(entry.path.as_bytes()).into_owned())
        .collect::<Vec<_>>();
    files.sort();
    files.dedup();
    let joined = files.join(",");
    if joined.is_empty() {
        abort_rebase(request)?;
        Err("could not reconcile the leaf branch onto origin/main".to_owned())
    } else {
        validate_conflicts(&joined)?;
        Ok(Reconcile::Conflict { files: joined, original_head })
    }
}

fn push_branch(request: &Request, force: bool) -> Result<(String, String), String> {
    ensure_clean(request)?;
    let (branch, head) = expected_branch_head(request)?;
    let remote = GitRemote::new("origin").map_err(|error| error.to_string())?;
    let destination = format!("refs/heads/{branch}");
    let reference = GitRef::new(&destination).map_err(|error| error.to_string())?;
    let force_with_lease = if force {
        match remote_oid(request, &branch)? {
            Some(oid) => Some(ForceWithLease::Expecting {
                reference,
                oid: GitRef::new(oid).map_err(|error| error.to_string())?,
            }),
            None => Some(ForceWithLease::ExpectingAbsent { reference }),
        }
    } else {
        None
    };
    let runtime = git_runtime(request)?;
    let push = PushRequest {
        remote,
        refspec: GitRefspec::new(format!("HEAD:{destination}")).map_err(|error| error.to_string())?,
        force_with_lease,
        set_upstream: true,
    };
    transient_git(|| runtime.runtime.block_on(runtime.git_cli().push(push.clone(), &runtime.cancellation)))
        .map_err(|_| "feature branch push failed".to_owned())?;
    Ok((branch, head))
}

fn fetch_main(request: &Request) -> Result<(), String> {
    let runtime = git_runtime(request)?;
    let fetch = FetchRequest {
        remote: GitRemote::new("origin").map_err(|error| error.to_string())?,
        refspec: Some(GitRefspec::new("main").map_err(|error| error.to_string())?),
        quiet: false,
        no_tags: false,
    };
    transient_git(|| runtime.runtime.block_on(runtime.git_cli().fetch(fetch.clone(), &runtime.cancellation)))
        .map(|_| ())
        .map_err(|_| "could not fetch origin/main".to_owned())
}

fn ensure_pull(request: &Request, state: &ShipState, branch: &str) -> Result<PullRequest, String> {
    let title = pr_title(request)?;
    let body = format!(
        "## Summary\n\n- Implement leaf #{} of umbrella #{}.\n\nCloses #{}\n",
        request.leaf, request.umbrella, request.leaf
    );
    let pull = with_github_service(async |service, cancellation| {
        let existing = if state.pr_number != 0 {
            Some(
                service
                    .get_pull_request(cancellation, request.repository.owner(), request.repository.name(), state.pr_number)
                    .await
                    .map_err(|error| error.to_string())?,
            )
        } else {
            let listed = service
                .list_open_pull_requests(cancellation, request.repository.owner(), request.repository.name(), branch)
                .await
                .map_err(|error| error.to_string())?;
            if listed.len() > 1 {
                return Err("multiple pull requests belong to the implementation branch".to_owned());
            }
            listed.into_iter().next()
        };
        if let Some(existing) = existing {
            return Ok(existing);
        }
        let created = service
            .create_pull_request(
                cancellation,
                &PullRequestSpec {
                    owner: request.repository.owner(),
                    repo: request.repository.name(),
                    head: branch,
                    base: "main",
                    title: &title,
                    body: &body,
                    draft: false,
                },
            )
            .await
            .map_err(|error| error.to_string())?;
        service
            .get_pull_request(
                cancellation,
                request.repository.owner(),
                request.repository.name(),
                created.pull_request().number(),
            )
            .await
            .map_err(|error| error.to_string())
    })
    .map_err(ServiceFailure::into_detail)?;
    if pull.state() == PullRequestState::Closed && !pull.merged() {
        return Err("implementation PR is closed without a merge".to_owned());
    }
    if pull.head_ref() != branch || pull.base_ref() != "main" {
        return Err("implementation PR branch or base read-back failed".to_owned());
    }
    let closing = format!("Closes #{}", request.leaf);
    if pull.body().lines().rfind(|line| !line.trim().is_empty()).map(str::trim) != Some(closing.as_str()) {
        return Err("existing PR body lacks the required leaf closing link".to_owned());
    }
    Ok(pull)
}

fn read_pull(request: &Request, number: u64) -> Result<(PullRequest, larch_adapters::github::ReleaseCandidatePullRequest), String> {
    with_github_service(async |service, cancellation| {
        let pull = service
            .get_pull_request(cancellation, request.repository.owner(), request.repository.name(), number)
            .await
            .map_err(|error| error.to_string())?;
        let candidate = service
            .release_candidate_pull_request(cancellation, request.repository.owner(), request.repository.name(), number)
            .await
            .map_err(|error| error.to_string())?;
        Ok((pull, candidate))
    })
    .map_err(ServiceFailure::into_detail)
}

fn require_pull_identity(request: &Request, state: &ShipState, pull: &PullRequest, head_oid: &str) -> Result<(), String> {
    if pull.number() != state.pr_number || pull.head_ref() != state.branch {
        return Err("persisted PR branch identity changed".to_owned());
    }
    if pull.base_ref() != "main" {
        return Err("implementation PR does not target main".to_owned());
    }
    if head_oid != state.head_sha {
        return Err("PR head changed after the verified push".to_owned());
    }
    if state.pr_url != expected_pr_url(request, state.pr_number) {
        return Err("persisted pull request URL does not match repository identity".to_owned());
    }
    Ok(())
}

fn pull_review_state(request: &Request, number: u64, expected_head: &str) -> Result<MergeStateStatus, String> {
    with_github_service(async |service, cancellation| {
        let candidate = service
            .release_candidate_pull_request(cancellation, request.repository.owner(), request.repository.name(), number)
            .await
            .map_err(|error| error.to_string())?;
        if candidate.head_oid != expected_head {
            return Err("PR head changed after the verified push".to_owned());
        }
        service
            .pull_request_review_state(cancellation, request.repository.owner(), request.repository.name(), number)
            .await
            .map(|state| state.merge_state_status())
            .map_err(|error| error.to_string())
    })
    .map_err(ServiceFailure::into_detail)
}

fn wait_ci(request: &Request, pr: u64) -> Result<(String, String), String> {
    for poll in 0..CI_POLLS {
        let fields = ci_status(request, pr)?;
        let status = fields.get("CI_STATUS").map(String::as_str).unwrap_or_default();
        match status {
            "pass" | "merged" => return Ok((status.to_owned(), String::new())),
            "fail" => {
                return Ok(("fail".to_owned(), fields.get("FAILED_RUN_ID").cloned().unwrap_or_default()));
            }
            "pending" | "NO_CHECKS" | "" if poll + 1 < CI_POLLS => thread::sleep(CI_POLL),
            "pending" | "NO_CHECKS" | "" => break,
            other => return Err(format!("CI returned an unsupported status: {other}")),
        }
    }
    Err("CI did not complete within the leaf ship timeout".to_owned())
}

fn ci_status(request: &Request, pr: u64) -> Result<BTreeMap<String, String>, String> {
    let output = delegate_larch_with_options_in(
        &[
            "ci".into(),
            "status".into(),
            "--pr".into(),
            pr.to_string().into(),
            "--repo".into(),
            request.slug.clone().into(),
            "--empty-checks-grace".into(),
            "0".into(),
        ],
        &[],
        &request.repo_root,
        CHILD_TIMEOUT,
    )?;
    if !output.status().success() || output.stdout_truncated() {
        return Err("CI status command failed".to_owned());
    }
    output_fields(output.stdout())
}

fn distill_failure(request: &Request, run_id: &str) -> Result<PathBuf, String> {
    if run_id.is_empty() || !run_id.bytes().all(|byte| byte.is_ascii_digit()) {
        return Err("failed CI did not expose a numeric Actions run id".to_owned());
    }
    let output_path = request.handoff_root.join(format!("ci-errors-{run_id}.md"));
    for attempt in 0..CI_LOG_ATTEMPTS {
        let output = delegate_larch_with_options_in(
            &[
                "ci".into(),
                "distill-log".into(),
                "--run-id".into(),
                run_id.into(),
                "--repo".into(),
                request.slug.clone().into(),
                "--output".into(),
                output_path.as_os_str().to_owned(),
            ],
            &[(ChildEnvironment::ImplementTmpdir, request.handoff_root.as_os_str().to_owned())],
            &request.repo_root,
            CHILD_TIMEOUT,
        )?;
        if output.stdout_truncated() {
            return Err("CI log distill output was truncated".to_owned());
        }
        let fields = output_fields(output.stdout())?;
        match fields.get("STATUS").map(String::as_str) {
            Some("ok") => {
                validate_ci_file(request, &output_path.display().to_string())?;
                return Ok(output_path);
            }
            Some("in_progress") if attempt + 1 < CI_LOG_ATTEMPTS => thread::sleep(CI_POLL),
            Some("in_progress") => break,
            _ => {
                let detail = fields.get("BAIL_CLASS").cloned().unwrap_or_default();
                return Err(format!("CI log distill failed: {detail}"));
            }
        }
    }
    Err("failed CI logs did not become ready".to_owned())
}

fn submit_merge(request: &Request, state: &ShipState) -> Result<MergeResult, String> {
    let merge_state = pull_review_state(request, state.pr_number, &state.head_sha)?;
    if !matches!(
        merge_state,
        MergeStateStatus::Clean | MergeStateStatus::Unstable | MergeStateStatus::HasHooks | MergeStateStatus::Blocked | MergeStateStatus::Behind
    ) {
        return Err(format!("PR is not admin-merge eligible: {merge_state:?}"));
    }
    if ci_status(request, state.pr_number)?.get("CI_STATUS").map(String::as_str) != Some("pass") {
        return Err("CI changed after the green pre-merge check".to_owned());
    }
    let budget = rust_budget_for_head(request, &state.head_sha)?;
    if budget.status == "over-limit" {
        eprintln!(
            "WARNING: managed Chief leaf #{}, PR #{}, exceeds the Rust line budget ({} added non-generated Rust lines; limit {RUST_LINE_LIMIT}); continuing with warning.",
            request.leaf,
            state.pr_number,
            budget.added_lines.unwrap_or_default()
        );
    }
    let output = delegate_larch_with_options_in(
        &[
            "merge".into(),
            "pr".into(),
            "--pr".into(),
            state.pr_number.to_string().into(),
            "--repo".into(),
            request.slug.clone().into(),
        ],
        &[],
        &request.repo_root,
        CHILD_TIMEOUT,
    )?;
    if output.stdout_truncated() {
        return Err("merge result output was truncated".to_owned());
    }
    let fields = output_fields(output.stdout())?;
    let result = fields.get("MERGE_RESULT").map(String::as_str).unwrap_or_default();
    match result {
        "merged" | "admin_merged" | "already_merged" => {
            confirm_merged(request, state)?;
            Ok(MergeResult::Merged)
        }
        "queued" => Ok(MergeResult::Queued),
        "main_advanced" => Ok(MergeResult::Reconcile),
        "ci_not_ready" => Ok(MergeResult::RetryCi),
        "review_required" => Err("PR requires approving review".to_owned()),
        other => Err(fields
            .get("ERROR")
            .filter(|detail| !detail.is_empty())
            .cloned()
            .unwrap_or_else(|| format!("merge did not complete: {other}"))),
    }
}

fn wait_queued(request: &Request, state: &mut ShipState) -> Result<(), String> {
    let output = delegate_merge_wait(state.pr_number, &request.slug, MERGE_WAIT)?;
    verify_merge_wait(&output)?;
    confirm_merged(request, state)?;
    state.set_status("merged");
    state.ci_errors_file.clear();
    write_state(request, state)
}

fn confirm_merged(request: &Request, state: &ShipState) -> Result<(), String> {
    let (pull, candidate) = read_pull(request, state.pr_number)?;
    require_pull_identity(request, state, &pull, &candidate.head_oid)?;
    if !pull.merged() || candidate.state != ReleaseCandidatePullRequestState::Merged {
        return Err("merged PR read-back failed".to_owned());
    }
    Ok(())
}

fn rust_budget(request: &Request) -> Result<RustBudget, String> {
    let head = repository(request)?
        .resolve_revision(&Revision::new(b"HEAD"))
        .map_err(|error| error.to_string())?
        .to_hex();
    rust_budget_for_head(request, &head)
}

fn rust_budget_for_head(request: &Request, head_sha: &str) -> Result<RustBudget, String> {
    let managed = with_github_service(async |service, cancellation| {
        service
            .issue_read(cancellation, request.repository.owner(), request.repository.name(), request.umbrella)
            .await
            .map(|issue| chief_umbrella_reference(&issue.body))
            .map_err(|error| error.to_string())
    })
    .map_err(ServiceFailure::into_detail)?;
    if !managed {
        return Ok(RustBudget {
            status: "not-managed",
            base_sha: String::new(),
            head_sha: String::new(),
            added_lines: None,
        });
    }
    let repository = repository(request)?;
    let head = repository
        .resolve_revision(&Revision::new(head_sha.as_bytes()))
        .map_err(|_| "Rust line budget head SHA is invalid".to_owned())?;
    let main = repository
        .resolve_revision(&Revision::new(b"origin/main"))
        .map_err(|_| "Rust line budget base is unavailable".to_owned())?;
    let base = repository.merge_base(&main, &head).map_err(|error| error.to_string())?;
    let runtime = git_runtime(request)?;
    let diff = runtime
        .runtime
        .block_on(runtime.git_cli().exact_diff(
            ExactDiffRequest {
                cached: false,
                binary: false,
                no_ext_diff: true,
                numstat_z_rename_50: true,
                unified_context: None,
                name_only: false,
                name_status: false,
                quiet: false,
                exit_code: false,
                base: Some(GitRef::new(base.to_hex()).map_err(|error| error.to_string())?),
                head: Some(GitRef::new(head.to_hex()).map_err(|error| error.to_string())?),
                paths: Vec::new(),
            },
            &runtime.cancellation,
        ))
        .map_err(|_| "Rust line budget diff failed".to_owned())?;
    if diff.truncated() {
        return Err("Rust line budget diff exceeded its output limit".to_owned());
    }
    let mut added = 0_u64;
    for row in parse_complete_umbrella_numstat(diff.output().stdout()).map_err(str::to_owned)? {
        if Path::new(&row.new_path).extension() != Some(std::ffi::OsStr::new("rs")) || row.added == Some(0) {
            continue;
        }
        let count = row.added.ok_or_else(|| "Rust line budget cannot measure a binary Rust diff".to_owned())?;
        let blob = repository
            .blob_at_commit(&head, &GitPath::new(row.new_path.as_bytes()))
            .map_err(|_| "Rust line budget could not read the changed source".to_owned())?
            .ok_or_else(|| "Rust line budget could not read the changed source".to_owned())?;
        let generated = String::from_utf8_lossy(&blob)
            .lines()
            .take(40)
            .any(|line| ["@generated", "Code generated by", "AUTOGENERATED"].iter().any(|marker| line.contains(marker)));
        if !generated {
            added = added.saturating_add(count);
        }
    }
    Ok(RustBudget {
        status: if added <= RUST_LINE_LIMIT { "within-limit" } else { "over-limit" },
        base_sha: base.to_hex(),
        head_sha: head.to_hex(),
        added_lines: Some(added),
    })
}

fn chief_umbrella_reference(body: &str) -> bool {
    body.lines().any(|line| {
        ISSUE_REFERENCE.find_iter(line).any(|issue| {
            let tail = &line[issue.end()..];
            CHIEF_MARKER.find(tail).is_some_and(|marker| tail[..marker.start()].chars().count() <= 160)
        })
    })
}

fn sync_main_and_delete(request: &Request, branch: &str) -> Result<(), String> {
    if !valid_branch(branch) {
        return Err("cannot clean up an invalid implementation branch".to_owned());
    }
    ensure_clean(request)?;
    if current_branch(request)? != "main" {
        let runtime = git_runtime(request)?;
        runtime
            .runtime
            .block_on(runtime.git_cli().checkout(
                CheckoutRequest::Branch {
                    create: false,
                    force: false,
                    no_track: false,
                    name: GitRef::new("main").map_err(|error| error.to_string())?,
                    start_point: None,
                },
                &runtime.cancellation,
            ))
            .map_err(|_| "could not switch to main after merge".to_owned())?;
    }
    fetch_main(request)?;
    let runtime = git_runtime(request)?;
    if runtime
        .runtime
        .block_on(runtime.git_cli().rebase(
            RebaseRequest::Start {
                onto: None,
                upstream: GitRef::new("origin/main").map_err(|error| error.to_string())?,
                branch: None,
            },
            &runtime.cancellation,
        ))
        .is_err()
    {
        abort_rebase(request)?;
        return Err("could not rebase local main onto origin/main".to_owned());
    }
    ensure_clean(request)?;
    require_main_equal(request)?;
    if local_branch_exists(request, branch)? {
        let runtime = git_runtime(request)?;
        runtime
            .runtime
            .block_on(runtime.git_cli().branch_mutation(
                BranchMutationRequest::Delete {
                    force: true,
                    name: GitRef::new(branch).map_err(|error| error.to_string())?,
                },
                &runtime.cancellation,
            ))
            .map_err(|_| "could not delete the local implementation branch".to_owned())?;
    }
    if remote_oid(request, branch)?.is_some() {
        let runtime = git_runtime(request)?;
        let delete = PushRequest {
            remote: GitRemote::new("origin").map_err(|error| error.to_string())?,
            refspec: GitRefspec::deletion(&GitRef::new(format!("refs/heads/{branch}")).map_err(|error| error.to_string())?),
            force_with_lease: None,
            set_upstream: false,
        };
        transient_git(|| runtime.runtime.block_on(runtime.git_cli().push(delete.clone(), &runtime.cancellation)))
            .map_err(|_| "could not delete the remote implementation branch".to_owned())?;
    }
    if local_branch_exists(request, branch)? || remote_oid(request, branch)?.is_some() {
        return Err("implementation branch deletion did not verify".to_owned());
    }
    Ok(())
}

fn verify_complete(request: &Request, state: &ShipState) -> Result<(), String> {
    if state.pr_number == 0 || !valid_branch(&state.branch) {
        return Err("complete ship state lacks PR or branch identity".to_owned());
    }
    confirm_merged(request, state)?;
    let issue = with_github_service(async |service, cancellation| {
        IssueMutationOwner::new(service)
            .read_snapshot(&request.repository, request.leaf, cancellation)
            .await
            .map_err(|error| error.to_string())
    })
    .map_err(ServiceFailure::into_detail)?;
    let expected = complete_umbrella_done_leaf_title(&issue.title, request.umbrella).map_err(str::to_owned)?;
    if issue.state != GitHubIssueState::Closed || issue.title != expected {
        return Err("leaf issue is not closed with the exact done title".to_owned());
    }
    if current_branch(request)? != "main" {
        return Err("repository is not on main after leaf shipping".to_owned());
    }
    ensure_clean(request)?;
    require_main_equal(request)?;
    if local_branch_exists(request, &state.branch)? || remote_oid(request, &state.branch)?.is_some() {
        return Err("implementation branch still exists".to_owned());
    }
    Ok(())
}

fn repository(request: &Request) -> Result<GixRepository, String> {
    GixRepository::open(&request.repo_root).map_err(|error| error.to_string())
}

fn git_runtime(request: &Request) -> Result<GitCommandRuntime, String> {
    GitCommandRuntime::for_repository(&request.repo_root)
}

fn transient_git<T>(mut operation: impl FnMut() -> Result<T, GitCliError>) -> Result<T, GitCliError> {
    for attempt in 1..=TRANSIENT_ATTEMPTS {
        match operation() {
            Err(error) if transient_git_error(&error) && sleep_before_retry(attempt) => {}
            result => return result,
        }
    }
    unreachable!("the shared retry schedule stops its final attempt")
}

fn transient_git_error(error: &GitCliError) -> bool {
    match error {
        GitCliError::Failed(result) => is_transient_net(&format!("{}{}", result.safe_stdout().as_str(), result.safe_stderr().as_str())),
        other => is_transient_net(&other.to_string()),
    }
}

fn ensure_clean(request: &Request) -> Result<(), String> {
    if repository(request)?
        .local_status(&StatusOptions::default())
        .map_err(|error| error.to_string())?
        .is_dirty()
    {
        Err("leaf ship requires a clean worktree".to_owned())
    } else {
        Ok(())
    }
}

fn current_branch(request: &Request) -> Result<String, String> {
    match repository(request)?.head().map_err(|error| error.to_string())? {
        Head::Symbolic { name, .. } => String::from_utf8(name.as_bytes().to_vec())
            .map_err(|_| "current branch is not UTF-8".to_owned())?
            .strip_prefix("refs/heads/")
            .map(str::to_owned)
            .ok_or_else(|| "detached HEAD or no current branch".to_owned()),
        Head::Detached { .. } | Head::Unborn { .. } => Err("detached HEAD or no current branch".to_owned()),
    }
}

fn expected_branch_head(request: &Request) -> Result<(String, String), String> {
    let branch = current_branch(request)?;
    if branch != expected_branch(request.leaf) {
        return Err("leaf implementation is not on its exact managed branch".to_owned());
    }
    let head = repository(request)?
        .resolve_revision(&Revision::new(b"HEAD"))
        .map_err(|error| error.to_string())?
        .to_hex();
    Ok((branch, head))
}

fn require_changed_head(request: &Request, old: &str, message: &str) -> Result<(), String> {
    let (_, head) = expected_branch_head(request)?;
    if head == old { Err(message.to_owned()) } else { Ok(()) }
}

fn rebase_in_progress(request: &Request) -> Result<bool, String> {
    let location = repository(request)?.location();
    let git_dir = PathBuf::from(String::from_utf8_lossy(location.git_dir.as_bytes()).into_owned());
    let git_dir = if git_dir.is_absolute() { git_dir } else { request.repo_root.join(git_dir) };
    Ok(git_dir.join("rebase-merge").is_dir() || git_dir.join("rebase-apply").is_dir())
}

fn abort_rebase(request: &Request) -> Result<(), String> {
    if !rebase_in_progress(request)? {
        return Ok(());
    }
    let runtime = git_runtime(request)?;
    let aborted = runtime
        .runtime
        .block_on(runtime.git_cli().rebase(RebaseRequest::Abort, &runtime.cancellation))
        .map(|_| ());
    if aborted.is_err() && rebase_in_progress(request)? {
        Err("could not abort an in-progress rebase".to_owned())
    } else {
        Ok(())
    }
}

fn remote_oid(request: &Request, branch: &str) -> Result<Option<String>, String> {
    let reference = format!("refs/heads/{branch}");
    let runtime = git_runtime(request)?;
    let probe = LsRemoteRequest {
        remote: GitRemote::new("origin").map_err(|error| error.to_string())?,
        patterns: vec![GitRef::new(&reference).map_err(|error| error.to_string())?],
        heads: true,
        exit_code: false,
    };
    let output = transient_git(|| runtime.runtime.block_on(runtime.git_cli().ls_remote(probe.clone(), &runtime.cancellation)))
        .map_err(|_| "remote branch probe failed".to_owned())?;
    let text = String::from_utf8_lossy(output.output().stdout());
    let fields = text.split_whitespace().collect::<Vec<_>>();
    match fields.as_slice() {
        [] => Ok(None),
        [oid, observed] if valid_oid(oid) && *observed == reference => Ok(Some((*oid).to_owned())),
        _ => Err("remote branch probe returned an invalid ref".to_owned()),
    }
}

fn local_branch_exists(request: &Request, branch: &str) -> Result<bool, String> {
    let reference = format!("refs/heads/{branch}");
    repository(request)?
        .references()
        .map(|references| references.iter().any(|candidate| candidate.name.as_bytes() == reference.as_bytes()))
        .map_err(|error| error.to_string())
}

fn require_main_equal(request: &Request) -> Result<(), String> {
    let repository = repository(request)?;
    let head = repository.resolve_revision(&Revision::new(b"HEAD")).map_err(|error| error.to_string())?;
    let main = repository.resolve_revision(&Revision::new(b"origin/main")).map_err(|error| error.to_string())?;
    if head == main {
        Ok(())
    } else {
        Err("local main does not match origin/main after rebase".to_owned())
    }
}

fn pr_title(request: &Request) -> Result<String, String> {
    let repository = repository(request)?;
    let head = repository.resolve_revision(&Revision::new(b"HEAD")).map_err(|error| error.to_string())?;
    let subject = head_subject(&repository, &head);
    let summary = if subject.is_empty() { format!("Implement umbrella leaf #{}", request.leaf) } else { subject };
    let prefix = format!("Fixes #{}: ", request.leaf);
    let title = if summary.starts_with(&prefix) { summary } else { format!("{prefix}{summary}") };
    Ok(ship_pr_title(request.leaf, &title.chars().take(250).collect::<String>(), ""))
}

fn output_fields(bytes: &[u8]) -> Result<BTreeMap<String, String>, String> {
    KvDocument::parse(&String::from_utf8_lossy(bytes), ParseOptions::legacy())
        .map(|document| document.select(DuplicatePolicy::Last))
        .map_err(|error| error.to_string())
}

fn validate_ci_file(request: &Request, value: &str) -> Result<(), String> {
    let path = Path::new(value);
    let valid_name = path.file_name().and_then(|name| name.to_str()).is_some_and(|name| {
        name.strip_prefix("ci-errors-")
            .and_then(|tail| tail.strip_suffix(".md"))
            .is_some_and(|id| !id.is_empty() && id.bytes().all(|byte| byte.is_ascii_digit()))
    });
    if !path.is_absolute() || !valid_name || !path.starts_with(&request.handoff_root) {
        return Err("ship state contains an invalid CI errors file".to_owned());
    }
    read_expected_file(
        path,
        &request.handoff_root,
        &temporary_root(&request.handoff_root, "--handoff-root")?,
        "CI errors file",
        1024 * 1024,
    )
    .map(|_| ())
    .map_err(|_| "ship state CI errors file is missing".to_owned())
}

fn validate_conflicts(value: &str) -> Result<(), String> {
    if value.is_empty() {
        return Ok(());
    }
    let paths = value.split(',').collect::<Vec<_>>();
    let valid = |path: &str| {
        !path.is_empty()
            && path
                .bytes()
                .enumerate()
                .all(|(index, byte)| byte.is_ascii_alphanumeric() || b"._".contains(&byte) || b"/-".contains(&byte) && index > 0)
    };
    if paths.iter().any(|path| !valid(path)) || paths.iter().collect::<BTreeSet<_>>().len() != paths.len() {
        Err("ship state contains invalid conflict files".to_owned())
    } else {
        Ok(())
    }
}

fn valid_branch(branch: &str) -> bool {
    !branch.is_empty()
        && branch != "main"
        && branch
            .bytes()
            .enumerate()
            .all(|(index, byte)| byte.is_ascii_alphanumeric() || b"._/-".contains(&byte) && index > 0)
        && !branch.contains("..")
        && !branch.contains("//")
        && !branch.contains("@{")
        && !branch.ends_with(['/', '.'])
}

fn valid_oid(value: &str) -> bool {
    (40..=64).contains(&value.len()) && value.bytes().all(|byte| byte.is_ascii_hexdigit() && !byte.is_ascii_uppercase())
}

fn expected_branch(leaf: u64) -> String {
    format!("complete-umbrella/leaf-{leaf}")
}

fn expected_pr_url(request: &Request, number: u64) -> String {
    format!("https://github.com/{}/pull/{number}", request.slug)
}

fn emit_ship(outcome: &ShipOutcome) {
    println!("SHIP_STATUS={}", outcome.status);
    println!(
        "PR_NUMBER={}",
        if outcome.pr_number == 0 {
            String::new()
        } else {
            outcome.pr_number.to_string()
        }
    );
    println!("PR_URL={}", outcome.pr_url);
    println!("CI_ERRORS_FILE={}", outcome.ci_errors_file);
    println!("CONFLICT_FILES={}", outcome.conflict_files);
    let detail = redact_outbound(&outcome.detail).replace(['\r', '\n'], " ");
    println!("DETAIL={}", detail.trim().chars().take(500).collect::<String>());
}

fn emit_budget(outcome: &RustBudget) {
    println!("RUST_LINE_BUDGET_STATUS={}", outcome.status);
    println!("RUST_LINE_BUDGET_LIMIT={RUST_LINE_LIMIT}");
    println!(
        "RUST_LINE_BUDGET_ADDED_LINES={}",
        outcome.added_lines.map(|value| value.to_string()).unwrap_or_default()
    );
    println!("RUST_LINE_BUDGET_BASE_SHA={}", outcome.base_sha);
    println!("RUST_LINE_BUDGET_HEAD_SHA={}", outcome.head_sha);
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{
        github_service::with_test_github_service,
        implement_child_seam::{clear_hooks, install_larch},
    };
    use larch_adapters::github::OctocrabGitHubService;
    use larch_core::{ProcessOutput, ProcessStatus};
    use larch_test_support::{GitFixture, GitRepository, GitRepositoryBuilder, IssueServiceExchange, IssueServiceStub};
    use serde_json::{Value, json};
    use std::sync::Arc;

    fn request(root: &Path) -> Request {
        Request {
            repository: repository_ref("owner/repo").expect("repository"),
            slug: "owner/repo".to_owned(),
            repo_root: root.to_path_buf(),
            handoff_root: root.to_path_buf(),
            umbrella: 40,
            leaf: 42,
        }
    }

    fn request_with(repo_root: &Path, handoff_root: &Path) -> Request {
        Request {
            repository: repository_ref("owner/repo").expect("repository"),
            slug: "owner/repo".to_owned(),
            repo_root: repo_root.to_path_buf(),
            handoff_root: handoff_root.to_path_buf(),
            umbrella: 40,
            leaf: 42,
        }
    }

    fn output(code: i32, stdout: &str) -> ProcessOutput {
        ProcessOutput::new(
            ProcessStatus::new(code == 0, Some(code)),
            stdout.as_bytes().to_vec(),
            Vec::new(),
            false,
            false,
        )
    }

    fn service(
        bodies: impl IntoIterator<Item = String>,
    ) -> (Arc<dyn Fn() -> OctocrabGitHubService + Send + Sync>, IssueServiceStub) {
        let exchanges = bodies
            .into_iter()
            .map(|body| IssueServiceExchange::any_json(200, body.into_bytes()).expect("response"))
            .collect::<Vec<_>>();
        let server = IssueServiceStub::start(exchanges).expect("stub");
        let base = server.base_url().to_owned();
        (Arc::new(move || OctocrabGitHubService::with_test_base(&base)), server)
    }

    fn pull(number: u64, state: &str, merged: bool, head: &str) -> String {
        json!({
            "number": number,
            "state": state,
            "title": "Ship",
            "body": "Summary\n\nCloses #42",
            "head": {"ref": expected_branch(42), "label": "owner:complete-umbrella/leaf-42", "sha": head},
            "base": {"ref": "main"},
            "draft": false,
            "merged": merged,
            "merge_commit_sha": merged.then_some("2222222222222222222222222222222222222222"),
        })
        .to_string()
    }

    fn candidate(state: &str, merged: bool, head: &str) -> String {
        json!({"state": state, "merged": merged, "head": {"sha": head}}).to_string()
    }

    fn clean_review() -> String {
        json!({"data": {"repository": {"pullRequest": {
            "reviewDecision": null,
            "mergeStateStatus": "CLEAN",
            "mergeable": "MERGEABLE",
        }}}})
        .to_string()
    }

    fn companion_issue(body: &str) -> String {
        json!({"title": "Umbrella", "body": body, "labels": []}).to_string()
    }

    fn issue_at(title: &str, state: &str, updated_at: &str) -> String {
        let mut value: Value = serde_json::from_str(include_str!("../../larch-adapters/fixtures/github_issue.json"))
            .expect("issue fixture");
        value["id"] = json!(420);
        value["number"] = json!(42);
        value["title"] = json!(title);
        value["body"] = json!("Body");
        value["state"] = json!(state);
        value["updated_at"] = json!(updated_at);
        value["labels"] = json!([]);
        value.to_string()
    }

    fn issue(title: &str, state: &str) -> String {
        issue_at(title, state, "2026-08-21T00:00:00Z")
    }

    fn identity_state(request: &Request, status: &str) -> ShipState {
        let mut state = ShipState::prepared(request);
        state.set_status(status);
        state.branch = expected_branch(request.leaf);
        state.head_sha = "a".repeat(40);
        state.pr_number = 7;
        state.pr_url = expected_pr_url(request, 7);
        state
    }

    fn command_arguments(mode: &str, repo_root: &Path, handoff_root: &Path) -> Vec<OsString> {
        [
            "--mode".into(), mode.into(),
            "--repository".into(), "owner/repo".into(),
            "--repo-root".into(), repo_root.as_os_str().to_owned(),
            "--handoff-root".into(), handoff_root.as_os_str().to_owned(),
            "--umbrella".into(), "40".into(),
            "--leaf".into(), "42".into(),
        ]
        .into()
    }

    fn git_fixture() -> GitRepository {
        let fixture = GitRepositoryBuilder::new(GitFixture::Refs).build().expect("git fixture");
        let remote = fixture.workspace_root().join("remote.git");
        assert!(fixture.git(["init", "--quiet", "--bare", remote.to_str().expect("remote")]).expect("init remote").success());
        assert!(fixture.git(["remote", "add", "origin", remote.to_str().expect("remote")]).expect("add remote").success());
        assert!(fixture.git(["config", "user.name", "Larch Fixture"]).expect("configure user name").success());
        assert!(fixture.git(["config", "user.email", "fixture@example.invalid"]).expect("configure user email").success());
        assert!(fixture.git(["push", "--quiet", "-u", "origin", "main"]).expect("push main").success());
        assert!(fixture.git(["checkout", "--quiet", "-b", &expected_branch(42)]).expect("leaf branch").success());
        fixture.write("leaf.txt", b"leaf\n").expect("leaf file");
        assert!(fixture.git(["add", "--", "leaf.txt"]).expect("add leaf").success());
        assert!(fixture.git(["commit", "--quiet", "-m", "Implement leaf"]).expect("commit leaf").success());
        fixture
    }

    fn closed_pull_service() -> (Arc<dyn Fn() -> OctocrabGitHubService + Send + Sync>, IssueServiceStub) {
        let pull = json!({
            "number": 7, "state": "closed", "title": "Ship", "body": "Closes #42",
            "head": {"ref": "complete-umbrella/leaf-42", "label": "owner:complete-umbrella/leaf-42", "sha": "1".repeat(40)},
            "base": {"ref": "main"}, "draft": false, "merged": false, "merge_commit_sha": null,
        })
        .to_string();
        let exchanges: Vec<_> = [pull.clone(), pull]
            .into_iter()
            .map(|body| IssueServiceExchange::any_json(200, body.into_bytes()).expect("response"))
            .collect();
        let server = IssueServiceStub::start(exchanges).expect("stub");
        let base = server.base_url().to_owned();
        (Arc::new(move || OctocrabGitHubService::with_test_base(&base)), server)
    }

    #[test]
    fn state_rejects_duplicates_and_stale_identity() {
        let temporary = tempfile::tempdir().expect("temporary");
        let request = request(temporary.path());
        let state = ShipState::prepared(&request);
        let text = state.render(&request).expect("state");
        assert_eq!(ShipState::parse(&request, &text), Ok(state));
        assert!(ShipState::parse(&request, &format!("{text}STATUS=prepared\n")).is_err());
        assert!(ShipState::parse(&request, &format!("{text}# comment\n")).is_err());
        assert!(ShipState::parse(&request, &text.replace("LEAF=42", "LEAF=41")).is_err());
    }

    #[test]
    fn state_binds_advanced_progress_to_the_exact_branch_and_pr() {
        let temporary = tempfile::tempdir().expect("temporary");
        let request = request(temporary.path());
        let mut state = ShipState::prepared(&request);
        state.set_status("monitoring");
        state.branch = expected_branch(request.leaf);
        state.head_sha = "a".repeat(40);
        state.pr_number = 7;
        state.pr_url = expected_pr_url(&request, 7);
        assert!(state.validate(&request).is_ok());
        "other".clone_into(&mut state.branch);
        assert!(state.validate(&request).is_err());
    }

    #[test]
    fn closed_pr_reentry_stops_before_every_git_mutation() {
        let temporary = tempfile::tempdir().expect("temporary");
        let request = request(temporary.path());
        let mut state = ShipState::prepared(&request);
        state.set_status("monitoring");
        state.branch = expected_branch(request.leaf);
        state.head_sha = "1".repeat(40);
        state.pr_number = 7;
        state.pr_url = expected_pr_url(&request, 7);
        write_state(&request, &state).expect("state");
        let (factory, server) = closed_pull_service();
        let Err(error) = with_test_github_service(factory, || ship(&request)) else {
            panic!("closed PR must stop");
        };
        assert_eq!(error, "implementation PR is closed without a merge");
        server.join().expect("stub completed");
    }

    #[test]
    fn fixed_poll_interval_is_exactly_five_minutes() {
        assert_eq!(CI_POLL, Duration::from_secs(300));
        assert_eq!(u64::try_from(CI_POLLS).expect("CI poll count fits u64") * CI_POLL.as_secs(), 86_400);
        assert!(MERGE_WAIT > Duration::from_secs(86_400));
    }

    #[test]
    fn chief_marker_requires_a_complete_nearby_issue_reference() {
        assert!(chief_umbrella_reference("#7687 owns [CHIEF UMBRELLA] work"));
        assert!(!chief_umbrella_reference(&format!("#7687{}[CHIEF UMBRELLA]", "x".repeat(161))));
        assert!(!chief_umbrella_reference("[CHIEF UMBRELLA] without issue"));
    }

    #[test]
    fn state_validation_covers_caps_partial_identity_and_scoped_artifacts() {
        let temporary = tempfile::tempdir().expect("temporary");
        let request = request(temporary.path());
        let mut state = identity_state(&request, "monitoring");

        let mut invalid = state.clone();
        invalid.status = "unknown".to_owned();
        assert_eq!(invalid.validate(&request).unwrap_err(), "invalid ship state status: unknown");
        invalid = state.clone();
        invalid.repository = "other/repo".to_owned();
        assert!(invalid.validate(&request).unwrap_err().contains("identity"));
        invalid = state.clone();
        invalid.umbrella = 41;
        assert!(invalid.validate(&request).unwrap_err().contains("identity"));
        invalid = state.clone();
        invalid.ci_fix_attempts = CI_FIX_CAP + 1;
        assert!(invalid.validate(&request).unwrap_err().contains("CI fix"));
        invalid = state.clone();
        invalid.conflict_fix_attempts = CONFLICT_FIX_CAP + 1;
        assert!(invalid.validate(&request).unwrap_err().contains("conflict fix"));
        invalid = state.clone();
        invalid.main_reconcile_attempts = RECONCILE_CAP + 1;
        assert!(invalid.validate(&request).unwrap_err().contains("main-reconcile"));
        invalid = state.clone();
        invalid.branch = "main".to_owned();
        assert!(invalid.validate(&request).unwrap_err().contains("branch"));
        invalid = state.clone();
        invalid.head_sha = "A".repeat(40);
        assert!(invalid.validate(&request).unwrap_err().contains("head SHA"));
        invalid = state.clone();
        invalid.pr_url.clear();
        assert!(invalid.validate(&request).unwrap_err().contains("PR URL"));
        invalid = state.clone();
        invalid.pr_url = expected_pr_url(&request, 8);
        assert!(invalid.validate(&request).unwrap_err().contains("PR URL"));

        let mut partial = ShipState::prepared(&request);
        partial.branch = expected_branch(request.leaf);
        assert!(partial.validate(&request).unwrap_err().contains("partial PR identity"));
        partial.branch.clear();
        partial.set_status("monitoring");
        assert!(partial.validate(&request).unwrap_err().contains("advanced ship state"));

        let ci_file = request.handoff_root.join("ci-errors-123.md");
        fs::write(&ci_file, "failure\n").expect("CI file");
        state.set_status("ci_failed");
        state.ci_errors_file = ci_file.display().to_string();
        assert!(state.validate(&request).is_ok());
        invalid = state.clone();
        invalid.ci_errors_file = request.handoff_root.join("other.md").display().to_string();
        assert!(invalid.validate(&request).unwrap_err().contains("invalid CI errors"));
        state.set_status("monitoring");
        assert!(state.validate(&request).unwrap_err().contains("non-failed"));

        state = identity_state(&request, "needs_conflict_fix");
        state.pr_number = 0;
        state.pr_url.clear();
        state.conflict_files = "src/a.rs,docs/b.md".to_owned();
        assert!(state.validate(&request).is_ok());
        invalid = state.clone();
        invalid.head_sha.clear();
        assert!(invalid.validate(&request).unwrap_err().contains("lacks branch identity"));
        invalid = state.clone();
        invalid.conflict_files = "src/a.rs,src/a.rs".to_owned();
        assert!(invalid.validate(&request).unwrap_err().contains("invalid conflict"));
        state.pr_number = 7;
        state.pr_url = expected_pr_url(&request, 7);
        state.set_status("monitoring");
        assert!(state.validate(&request).unwrap_err().contains("non-conflict"));

        let prepared = ShipState::prepared(&request).render(&request).expect("prepared");
        assert!(ShipState::parse(&request, &prepared.replace("SCHEMA=1", "SCHEMA=2")).unwrap_err().contains("schema"));
        assert!(ShipState::parse(&request, &prepared.replace("UMBRELLA=40", "UMBRELLA=no")).unwrap_err().contains("non-numeric"));
        assert!(ShipState::parse(&request, &prepared.replace("STATUS=prepared", "STATUS=prepared\r")).unwrap_err().contains("carriage"));
        assert!(ShipState::parse(&request, &prepared.replace("STATUS=prepared\n", "BROKEN\n")).unwrap_err().contains("malformed"));
    }

    #[test]
    fn argument_request_wire_and_value_helpers_fail_closed() {
        let repo = tempfile::tempdir().expect("repo");
        let handoff = tempfile::tempdir().expect("handoff");
        for (mode, expected) in [
            ("prepare", ShipMode::Prepare),
            ("ship", ShipMode::Ship),
            ("verify", ShipMode::Verify),
            ("line-budget", ShipMode::LineBudget),
        ] {
            let parsed = parse_arguments(&command_arguments(mode, repo.path(), handoff.path())).expect("arguments");
            assert_eq!(parsed.mode, expected);
            assert_eq!(Request::load(&parsed).expect("request").leaf, 42);
        }
        let mut bad = command_arguments("other", repo.path(), handoff.path());
        assert!(parse_arguments(&bad).is_err());
        bad = command_arguments("ship", repo.path(), handoff.path());
        let leaf = bad.iter().position(|value| value == "--leaf").expect("leaf") + 1;
        bad[leaf] = "not-a-number".into();
        assert!(parse_arguments(&bad).is_err());

        let parsed = |repository: &str, umbrella: i64, leaf: i64| ParsedArguments {
            mode: ShipMode::Ship,
            repository: repository.to_owned(),
            repo_root: repo.path().to_path_buf(),
            handoff_root: handoff.path().to_path_buf(),
            umbrella,
            leaf,
        };
        assert!(Request::load(&parsed("bad", 40, 42)).err().expect("bad repository").contains("OWNER/REPO"));
        assert!(Request::load(&parsed("owner/repo", 0, 42)).err().expect("zero umbrella").contains("positive"));
        assert!(Request::load(&parsed("owner/repo", -1, 42)).err().expect("negative umbrella").contains("positive"));

        let fields = output_fields(b"A=first\nA=last\n").expect("fields");
        assert_eq!(fields.get("A").map(String::as_str), Some("last"));
        assert!(output_fields(b"broken\n").expect("legacy fields").is_empty());
        assert!(validate_conflicts("").is_ok());
        assert!(validate_conflicts("src/a.rs,docs/b.md").is_ok());
        assert!(validate_conflicts("/absolute").is_err());
        assert!(validate_conflicts("same,same").is_err());
        for branch in ["", "main", "/bad", "bad..name", "bad//name", "bad@{name", "bad/", "bad."] {
            assert!(!valid_branch(branch), "{branch}");
        }
        assert!(valid_branch("complete-umbrella/leaf-42"));
        assert!(valid_oid(&"a".repeat(40)) && valid_oid(&"b".repeat(64)));
        assert!(!valid_oid(&"a".repeat(39)) && !valid_oid(&"A".repeat(40)));

        let state = identity_state(&request(handoff.path()), "monitoring");
        let outcome = ShipOutcome::from_state(&state, "monitoring");
        assert_eq!(outcome.status, "monitoring");
        emit_ship(&outcome);
        emit_ship(&ShipOutcome::error("line\nbreak".to_owned()));
        emit_budget(&RustBudget { status: "within-limit", base_sha: "a".repeat(40), head_sha: "b".repeat(40), added_lines: Some(2) });
        emit_budget(&RustBudget { status: "not-managed", base_sha: String::new(), head_sha: String::new(), added_lines: None });
    }

    #[test]
    fn prepare_mutates_exact_titles_and_missing_state_modes_refuse() {
        let repo = tempfile::tempdir().expect("repo");
        let handoff = tempfile::tempdir().expect("handoff");
        let request = request_with(repo.path(), handoff.path());
        assert_eq!(ship(&request).err().expect("missing state"), "leaf prepare phase has not initialized ship state");
        assert_eq!(verify(&request).err().expect("incomplete state"), "leaf ship state is not complete");
        assert!(read_state(&request).expect("missing state").is_none());

        let initial = issue_at("[LEAF OF 40] Ship", "open", "2026-08-21T00:00:00Z");
        let active = issue_at("[IMPLEMENTING] [LEAF OF 40] Ship", "open", "2026-08-21T00:00:01Z");
        let (factory, server) = service([initial.clone(), initial, active.clone(), active]);
        let outcome = with_test_github_service(factory, || prepare(&request)).expect("prepare");
        assert_eq!(outcome.status, "prepared");
        assert_eq!(read_state(&request).expect("state").expect("prepared").status, "prepared");
        server.join().expect("stub completed");

        let before = issue_at("[IMPLEMENTING] [LEAF OF 40] Ship", "closed", "2026-08-21T00:00:02Z");
        let done = issue_at("[DONE] [LEAF OF 40] Ship", "closed", "2026-08-21T00:00:03Z");
        let (factory, server) = service([before.clone(), before, done.clone(), done]);
        with_test_github_service(factory, || mutate_leaf_title(&request, true)).expect("done title");
        server.join().expect("stub completed");

        let code = run(&ShipLeafArguments { arguments: command_arguments("verify", repo.path(), handoff.path()) });
        assert_eq!(code, ExitCode::FAILURE);
    }

    #[test]
    fn ci_status_wait_and_distillation_preserve_child_envelopes() {
        let repo = tempfile::tempdir().expect("repo");
        let handoff = tempfile::tempdir().expect("handoff");
        let request = request_with(repo.path(), handoff.path());
        install_larch(|_arguments, _environment| Ok(output(0, "CI_STATUS=pass\nFAILED_RUN_ID=\n")));
        assert_eq!(wait_ci(&request, 7).expect("pass").0, "pass");
        install_larch(|_arguments, _environment| Ok(output(0, "CI_STATUS=fail\nFAILED_RUN_ID=123\n")));
        assert_eq!(wait_ci(&request, 7).expect("fail"), ("fail".to_owned(), "123".to_owned()));
        install_larch(|_arguments, _environment| Ok(output(0, "CI_STATUS=surprise\n")));
        assert!(wait_ci(&request, 7).unwrap_err().contains("unsupported"));

        install_larch(|arguments, _environment| {
            let index = arguments.iter().position(|value| value == "--output").expect("output option");
            fs::write(PathBuf::from(&arguments[index + 1]), "# CI failure\n").expect("distilled file");
            Ok(output(0, "STATUS=ok\n"))
        });
        assert_eq!(distill_failure(&request, "123").expect("distill"), handoff.path().join("ci-errors-123.md"));
        assert!(distill_failure(&request, "not-numeric").unwrap_err().contains("numeric"));

        install_larch(|_arguments, _environment| {
            Ok(ProcessOutput::new(ProcessStatus::new(true, Some(0)), b"CI_STATUS=pass\n".to_vec(), Vec::new(), true, false))
        });
        assert_eq!(ci_status(&request, 7).unwrap_err(), "CI status command failed");
        clear_hooks();
    }

    #[test]
    fn managed_budget_counts_only_non_generated_rust_lines() {
        let fixture = GitRepositoryBuilder::new(GitFixture::Refs).build().expect("git fixture");
        fixture.write("live.rs", b"fn live() {}\nfn more() {}\n").expect("live Rust");
        fixture.write("generated.rs", b"// @generated\nfn generated() {}\n").expect("generated Rust");
        fixture.write("notes.txt", b"not Rust\n").expect("notes");
        assert!(fixture.git(["add", "--", "live.rs", "generated.rs", "notes.txt"]).expect("add").success());
        assert!(fixture.git(["commit", "--quiet", "-m", "Rust changes"]).expect("commit").success());
        let handoff = tempfile::tempdir().expect("handoff");
        let request = request_with(fixture.root(), handoff.path());
        let head = repository(&request).expect("repository").resolve_revision(&Revision::new(b"HEAD")).expect("head").to_hex();
        let managed = companion_issue("#7687 owns [CHIEF UMBRELLA] work");
        let (factory, server) = service([managed.clone(), managed.clone(), managed]);
        let budget = with_test_github_service(factory, || rust_budget_for_head(&request, &head)).expect("budget");
        assert_eq!(budget.status, "within-limit");
        assert_eq!(budget.added_lines, Some(2));
        assert_eq!(with_test_github_service(
            Arc::new({
                let base = server.base_url().to_owned();
                move || OctocrabGitHubService::with_test_base(&base)
            }),
            || rust_budget(&request),
        ).expect("head budget").added_lines, Some(2));
        assert!(with_test_github_service(
            Arc::new({
                let base = server.base_url().to_owned();
                move || OctocrabGitHubService::with_test_base(&base)
            }),
            || rust_budget_for_head(&request, "invalid"),
        ).err().expect("invalid head").contains("head SHA"));
        server.join().expect("stub completed");
    }

    #[test]
    fn pull_creation_and_merge_result_classification_are_bounded() {
        let fixture = git_fixture();
        let handoff = tempfile::tempdir().expect("handoff");
        let request = request_with(fixture.root(), handoff.path());
        let state = ShipState::prepared(&request);
        let head = repository(&request).expect("repository").resolve_revision(&Revision::new(b"HEAD")).expect("head").to_hex();
        let open = pull(7, "open", false, &head);
        let (factory, server) = service(["[]".to_owned(), "[]".to_owned(), open.clone(), open.clone()]);
        let created = with_test_github_service(factory, || ensure_pull(&request, &state, &expected_branch(42))).expect("created pull");
        assert_eq!(created.number(), 7);
        server.join().expect("stub completed");

        let (factory, server) = service([format!("[{open},{open}]")]);
        assert!(with_test_github_service(factory, || ensure_pull(&request, &state, &expected_branch(42))).unwrap_err().contains("multiple"));
        server.join().expect("stub completed");

        let merge_state = identity_state(&request, "monitoring");
        for (wire, expected) in [
            ("MERGE_RESULT=queued\n", "queued"),
            ("MERGE_RESULT=main_advanced\n", "reconcile"),
            ("MERGE_RESULT=ci_not_ready\n", "retry-ci"),
            ("MERGE_RESULT=review_required\n", "requires approving review"),
            ("MERGE_RESULT=other\nERROR=custom failure\n", "custom failure"),
        ] {
            let (factory, server) = service([
                candidate("open", false, &merge_state.head_sha),
                clean_review(),
                companion_issue("ordinary umbrella"),
            ]);
            let selected = wire.to_owned();
            install_larch(move |arguments, _environment| {
                match arguments.iter().filter_map(|value| value.to_str()).take(2).collect::<Vec<_>>().as_slice() {
                    ["ci", "status"] => Ok(output(0, "CI_STATUS=pass\n")),
                    ["merge", "pr"] => Ok(output(0, &selected)),
                    other => panic!("unexpected larch child: {other:?}"),
                }
            });
            let result = with_test_github_service(factory, || submit_merge(&request, &merge_state));
            match expected {
                "queued" => assert!(matches!(result, Ok(MergeResult::Queued))),
                "reconcile" => assert!(matches!(result, Ok(MergeResult::Reconcile))),
                "retry-ci" => assert!(matches!(result, Ok(MergeResult::RetryCi))),
                detail => assert!(result.err().expect("merge refusal").contains(detail)),
            }
            server.join().expect("stub completed");
        }
        clear_hooks();
    }

    #[test]
    fn pull_identity_review_and_closing_link_validation_fail_closed() {
        let fixture = git_fixture();
        let handoff = tempfile::tempdir().expect("handoff");
        let request = request_with(fixture.root(), handoff.path());
        let head = repository(&request).expect("repository").resolve_revision(&Revision::new(b"HEAD")).expect("head").to_hex();
        let mut state = identity_state(&request, "monitoring");
        state.head_sha.clone_from(&head);
        let valid = pull(7, "open", false, &head);
        let (factory, server) = service([valid.clone()]);
        let valid_pull = with_test_github_service(factory, || ensure_pull(&request, &state, &expected_branch(42))).expect("valid pull");
        server.join().expect("stub completed");

        assert!(require_pull_identity(&request, &state, &valid_pull, &head).is_ok());
        let mut changed = state.clone();
        changed.pr_number = 8;
        assert!(require_pull_identity(&request, &changed, &valid_pull, &head).unwrap_err().contains("branch identity"));
        changed = state.clone();
        changed.branch = "other".to_owned();
        assert!(require_pull_identity(&request, &changed, &valid_pull, &head).unwrap_err().contains("branch identity"));
        assert!(require_pull_identity(&request, &state, &valid_pull, &"b".repeat(40)).unwrap_err().contains("head changed"));
        changed = state.clone();
        changed.pr_url = "https://example.invalid/pull/7".to_owned();
        assert!(require_pull_identity(&request, &changed, &valid_pull, &head).unwrap_err().contains("URL"));

        let mut wrong_branch: Value = serde_json::from_str(&valid).expect("pull JSON");
        wrong_branch["head"]["ref"] = json!("other");
        let mut wrong_base: Value = serde_json::from_str(&valid).expect("pull JSON");
        wrong_base["base"]["ref"] = json!("release");
        let mut wrong_body: Value = serde_json::from_str(&valid).expect("pull JSON");
        wrong_body["body"] = json!("Closes #42\n\nTrailing prose");
        for (body, detail) in [
            (pull(7, "closed", false, &head), "closed without a merge"),
            (wrong_branch.to_string(), "branch or base"),
            (wrong_base.to_string(), "branch or base"),
            (wrong_body.to_string(), "closing link"),
        ] {
            let (factory, server) = service([body]);
            let error = with_test_github_service(factory, || ensure_pull(&request, &state, &expected_branch(42)))
                .expect_err("invalid pull");
            assert!(error.contains(detail), "{error}");
            server.join().expect("stub completed");
        }

        let (factory, server) = service([candidate("open", false, &"c".repeat(40))]);
        assert!(with_test_github_service(factory, || pull_review_state(&request, 7, &head)).unwrap_err().contains("head changed"));
        server.join().expect("stub completed");

        let dirty = json!({"data": {"repository": {"pullRequest": {
            "reviewDecision": null, "mergeStateStatus": "DIRTY", "mergeable": "CONFLICTING",
        }}}})
        .to_string();
        let mut merge_state = identity_state(&request, "monitoring");
        merge_state.head_sha.clone_from(&head);
        let (factory, server) = service([candidate("open", false, &head), dirty]);
        assert!(with_test_github_service(factory, || submit_merge(&request, &merge_state))
            .err()
            .expect("ineligible merge")
            .contains("not admin-merge eligible"));
        server.join().expect("stub completed");

        let (factory, server) = service([candidate("open", false, &head), clean_review()]);
        install_larch(|_arguments, _environment| Ok(output(0, "CI_STATUS=fail\n")));
        assert!(with_test_github_service(factory, || submit_merge(&request, &merge_state))
            .err()
            .expect("changed CI")
            .contains("CI changed"));
        server.join().expect("stub completed");
        clear_hooks();
    }

    #[test]
    #[allow(clippy::cognitive_complexity)] // One real Git history keeps the clean and conflicting rebase phases causally linked.
    fn git_reconcile_and_branch_helpers_cover_rebase_and_conflict() {
        let fixture = git_fixture();
        let handoff = tempfile::tempdir().expect("handoff");
        let request = request_with(fixture.root(), handoff.path());
        let branch = expected_branch(42);
        let (_, original_head) = expected_branch_head(&request).expect("managed branch");
        assert_eq!(current_branch(&request).expect("branch"), branch);
        assert!(require_changed_head(&request, &original_head, "unchanged").unwrap_err().contains("unchanged"));
        assert!(require_changed_head(&request, &"0".repeat(40), "changed").is_ok());
        assert!(matches!(reconcile_main(&request), Ok(Reconcile::Clean { rebased: false })));

        assert!(fixture.git(["checkout", "--quiet", "main"]).expect("checkout main").success());
        fixture.write("upstream.txt", b"upstream\n").expect("upstream file");
        assert!(fixture.git(["add", "--", "upstream.txt"]).expect("add upstream").success());
        assert!(fixture.git(["commit", "--quiet", "-m", "Advance main"]).expect("commit upstream").success());
        assert!(fixture.git(["push", "--quiet", "origin", "main"]).expect("push main").success());
        assert!(fixture.git(["checkout", "--quiet", branch.as_str()]).expect("checkout leaf").success());
        assert!(matches!(reconcile_main(&request), Ok(Reconcile::Clean { rebased: true })));

        assert!(fixture.git(["checkout", "--quiet", "main"]).expect("checkout main").success());
        fixture.write("conflict.txt", b"base\n").expect("base conflict file");
        assert!(fixture.git(["add", "--", "conflict.txt"]).expect("add conflict base").success());
        assert!(fixture.git(["commit", "--quiet", "-m", "Add conflict base"]).expect("commit conflict base").success());
        assert!(fixture.git(["push", "--quiet", "origin", "main"]).expect("push conflict base").success());
        assert!(fixture.git(["checkout", "--quiet", branch.as_str()]).expect("checkout leaf").success());
        assert!(matches!(reconcile_main(&request), Ok(Reconcile::Clean { rebased: true })));
        fixture.write("conflict.txt", b"leaf\n").expect("leaf conflict");
        assert!(fixture.git(["add", "--", "conflict.txt"]).expect("add leaf conflict").success());
        assert!(fixture.git(["commit", "--quiet", "-m", "Change conflict on leaf"]).expect("commit leaf conflict").success());

        assert!(fixture.git(["checkout", "--quiet", "main"]).expect("checkout main").success());
        fixture.write("conflict.txt", b"main\n").expect("main conflict");
        assert!(fixture.git(["add", "--", "conflict.txt"]).expect("add main conflict").success());
        assert!(fixture.git(["commit", "--quiet", "-m", "Change conflict on main"]).expect("commit main conflict").success());
        assert!(fixture.git(["push", "--quiet", "origin", "main"]).expect("push main conflict").success());
        assert!(fixture.git(["checkout", "--quiet", branch.as_str()]).expect("checkout leaf").success());
        let Reconcile::Conflict { files, original_head: conflict_head } = reconcile_main(&request).expect("conflict") else {
            panic!("expected conflict");
        };
        assert_eq!(files, "conflict.txt");
        assert!(valid_oid(&conflict_head));
        assert!(rebase_in_progress(&request).expect("rebase state"));
        abort_rebase(&request).expect("abort conflict");
        assert!(!rebase_in_progress(&request).expect("cleared rebase"));
        abort_rebase(&request).expect("idempotent abort");

        assert!(local_branch_exists(&request, &branch).expect("local branch"));
        assert!(fixture.git(["push", "--quiet", "-u", "origin", branch.as_str()]).expect("push leaf").success());
        assert!(remote_oid(&request, &branch).expect("remote branch").is_some());
        assert!(pr_title(&request).expect("PR title").starts_with("Fixes #42: "));
        assert!(require_main_equal(&request).unwrap_err().contains("does not match"));

        assert!(fixture.git(["checkout", "--quiet", "main"]).expect("checkout main").success());
        assert!(require_main_equal(&request).is_ok());
        assert!(expected_branch_head(&request).unwrap_err().contains("exact managed branch"));
        fixture.write("dirty.txt", b"dirty\n").expect("dirty file");
        assert!(ensure_clean(&request).unwrap_err().contains("clean worktree"));
    }

    #[test]
    fn premerge_reentry_and_conflict_handoff_caps_are_bounded() {
        let fixture = git_fixture();
        let handoff = tempfile::tempdir().expect("handoff");
        let request = request_with(fixture.root(), handoff.path());
        let (_, head) = expected_branch_head(&request).expect("managed head");

        let mut state = identity_state(&request, "ci_failed");
        state.head_sha.clone_from(&head);
        assert!(run_premerge(&request, &mut state).err().expect("unchanged fixer").contains("no fixer commit"));
        state.head_sha = "0".repeat(40);
        state.ci_fix_attempts = CI_FIX_CAP;
        assert!(run_premerge(&request, &mut state).err().expect("CI cap").contains("CI fix attempt cap"));

        state = identity_state(&request, "needs_conflict_fix");
        state.head_sha = "0".repeat(40);
        state.conflict_fix_attempts = CONFLICT_FIX_CAP;
        assert!(run_premerge(&request, &mut state).err().expect("conflict cap").contains("conflict fix attempt cap"));

        state = ShipState::prepared(&request);
        let outcome = conflict_handoff(&request, &mut state, "src/a.rs".to_owned(), head.clone()).expect("handoff");
        assert_eq!(outcome.status, "needs_conflict_fix");
        assert_eq!(read_state(&request).expect("state").expect("handoff state").conflict_files, "src/a.rs");
        state.conflict_fix_attempts = CONFLICT_FIX_CAP;
        assert!(conflict_handoff(&request, &mut state, "src/a.rs".to_owned(), head)
            .err()
            .expect("handoff cap")
            .contains("conflict fix attempt cap"));
    }

    #[test]
    fn ship_reentry_rejects_contradictory_live_pull_states() {
        let handoff = tempfile::tempdir().expect("handoff");
        let request = request(handoff.path());
        for (status, live_pull, live_candidate, detail) in [
            ("monitoring", pull(7, "closed", true, &"a".repeat(40)), candidate("open", false, &"a".repeat(40)), "contradicts"),
            ("monitoring", pull(7, "open", false, &"a".repeat(40)), candidate("closed", true, &"a".repeat(40)), "contradicts"),
            ("merged", pull(7, "open", false, &"a".repeat(40)), candidate("open", false, &"a".repeat(40)), "contradicts"),
            ("monitoring", pull(7, "closed", false, &"a".repeat(40)), candidate("open", false, &"a".repeat(40)), "closed without a merge"),
        ] {
            let state = identity_state(&request, status);
            write_state(&request, &state).expect("state");
            let (factory, server) = service([live_pull, live_candidate]);
            let error = with_test_github_service(factory, || ship(&request)).err().expect("reentry refusal");
            assert!(error.contains(detail), "{error}");
            server.join().expect("stub completed");
        }
    }

    #[test]
    fn ship_completes_the_green_direct_merge_and_postmerge_cleanup() {
        let fixture = git_fixture();
        let handoff = tempfile::tempdir().expect("handoff");
        let request = request_with(fixture.root(), handoff.path());
        write_state(&request, &ShipState::prepared(&request)).expect("prepared state");
        let head = repository(&request)
            .expect("repository")
            .resolve_revision(&Revision::new(b"HEAD"))
            .expect("head")
            .to_hex();
        let open = pull(7, "open", false, &head);
        let merged = pull(7, "closed", true, &head);
        let done = issue("[DONE] [LEAF OF 40] Ship", "closed");
        let (factory, server) = service([
            format!("[{open}]"),
            candidate("open", false, &head),
            clean_review(),
            candidate("open", false, &head),
            clean_review(),
            companion_issue("ordinary umbrella"),
            merged.clone(),
            candidate("closed", true, &head),
            done.clone(),
            merged,
            candidate("closed", true, &head),
            done,
        ]);
        install_larch(|arguments, _environment| {
            match arguments.iter().filter_map(|value| value.to_str()).take(2).collect::<Vec<_>>().as_slice() {
                ["ci", "status"] => Ok(output(0, "CI_STATUS=pass\nFAILED_RUN_ID=\n")),
                ["merge", "pr"] => Ok(output(0, "MERGE_RESULT=merged\n")),
                other => panic!("unexpected larch child: {other:?}"),
            }
        });

        let outcome = with_test_github_service(factory, || ship(&request)).expect("ship completes");

        assert_eq!(outcome.status, "complete");
        assert_eq!(outcome.pr_number, 7);
        assert_eq!(current_branch(&request).as_deref(), Ok("main"));
        assert!(!local_branch_exists(&request, &expected_branch(42)).expect("local branch"));
        assert!(remote_oid(&request, &expected_branch(42)).expect("remote branch").is_none());
        assert_eq!(read_state(&request).expect("read state").expect("state").status, "complete");
        server.join().expect("stub completed");
        clear_hooks();
    }
}

}

pub use implementation::{ShipLeafArguments, run};
