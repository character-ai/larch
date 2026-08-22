//! Rust owner for PR composition and lifecycle commands (#8789, #8790).

use crate::{
    argparse_compat::{ParsedCommandLine, parse_required_with_help, usage_error},
    git_command_runtime::{GitCommandRuntime, exact_name_only_request},
    github_repository_resolution::{
        ambient_repo, remote_slug, repository_ref, valid_git_label, validate_repo_slug,
    },
    github_service::{ServiceFailure, with_github_service},
    implement_scope_disposition_commands::{PrMutationScopeGate, validate_pr_mutation_scope},
};
use larch_adapters::github::{IssueMutationOwner, LiveMutationRequest};
use larch_adapters::{
    CheckoutRequest, FetchMode, FetchRequest, GitRef, GitRefspec, GitRemote, GixRepository,
    path_under, resolve_allow_missing,
};
use larch_core::{
    CheckBucket, ConfigKey, ConfigScope, GitHubActionsService, GitHubService, RepositoryRead,
    Revision, SafeText, StatusOptions, compose_pr_summary, emit_kv, redact_issue_text_outbound,
    redact_pr_body,
};
use regex::Regex;
use std::{
    env,
    ffi::{OsStr, OsString},
    fs,
    path::Path,
    process::ExitCode,
    sync::LazyLock,
    thread,
    time::Duration,
};

struct LegacyParserSpec {
    program: &'static str,
    usage: &'static str,
    help: &'static str,
    values: &'static [&'static str],
    flags: &'static [&'static str],
    required: &'static [&'static str],
}

const SUMMARY_PROGRAM: &str = "cli.py pr compose-summary";
const SUMMARY_USAGE: &str =
    "usage: cli.py pr compose-summary [-h] --plan-goals-file PLAN_GOALS_FILE";
const SUMMARY_HELP: &str = "usage: cli.py pr compose-summary [-h] --plan-goals-file PLAN_GOALS_FILE\n\noptions:\n  -h, --help            show this help message and exit\n  --plan-goals-file PLAN_GOALS_FILE\n";
const BRANCH_PROGRAM: &str = "cli.py pr create-branch";
const BRANCH_USAGE: &str = "usage: cli.py pr create-branch [-h] [--branch BRANCH] [--check]\n                               [--base-remote BASE_REMOTE]\n                               [--base-ref BASE_REF]";
const BRANCH_HELP: &str = "usage: cli.py pr create-branch [-h] [--branch BRANCH] [--check]\n                               [--base-remote BASE_REMOTE]\n                               [--base-ref BASE_REF]\n\noptions:\n  -h, --help            show this help message and exit\n  --branch BRANCH\n  --check\n  --base-remote BASE_REMOTE\n  --base-ref BASE_REF\n";
const CREATE_PROGRAM: &str = "cli.py pr create";
const CREATE_USAGE: &str = "usage: cli.py pr create [-h] [--repo REPO] [--branch BRANCH] --title TITLE\n                        --body-file BODY_FILE [--base BASE] [--draft]";
const CREATE_HELP: &str = "usage: cli.py pr create [-h] [--repo REPO] [--branch BRANCH] --title TITLE\n                        --body-file BODY_FILE [--base BASE] [--draft]\n\noptions:\n  -h, --help            show this help message and exit\n  --repo REPO\n  --branch BRANCH\n  --title TITLE\n  --body-file BODY_FILE\n  --base BASE\n  --draft\n";
const UPDATE_PROGRAM: &str = "cli.py pr body-update";
const UPDATE_USAGE: &str =
    "usage: cli.py pr body-update [-h] --pr PR [--repo REPO] --body-file BODY_FILE";
const UPDATE_HELP: &str = "usage: cli.py pr body-update [-h] --pr PR [--repo REPO] --body-file BODY_FILE\n\noptions:\n  -h, --help            show this help message and exit\n  --pr PR\n  --repo REPO\n  --body-file BODY_FILE\n";
const CHECKS_PROGRAM: &str = "cli.py pr checks";
const CHECKS_USAGE: &str = "usage: cli.py pr checks [-h] --pr PR --repo REPO";
const CHECKS_HELP: &str = "usage: cli.py pr checks [-h] --pr PR --repo REPO\n\noptions:\n  -h, --help   show this help message and exit\n  --pr PR\n  --repo REPO\n";
const CLOSES_PROGRAM: &str = "cli.py pr closes-issue";
const CLOSES_USAGE: &str =
    "usage: cli.py pr closes-issue [-h] [--body-file BODY_FILE] [--repo REPO]";
const CLOSES_HELP: &str = "usage: cli.py pr closes-issue [-h] [--body-file BODY_FILE] [--repo REPO]\n\noptions:\n  -h, --help            show this help message and exit\n  --body-file BODY_FILE\n  --repo REPO\n";
const NEEDS_USER_EXIT: u8 = 3;
static CLOSES_ISSUE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"Closes #([0-9]+)").expect("static closes expression"));

const BRANCH_PARSER: LegacyParserSpec = LegacyParserSpec {
    program: BRANCH_PROGRAM,
    usage: BRANCH_USAGE,
    help: BRANCH_HELP,
    values: &["--branch", "--base-remote", "--base-ref"],
    flags: &["--check"],
    required: &[],
};
const CREATE_PARSER: LegacyParserSpec = LegacyParserSpec {
    program: CREATE_PROGRAM,
    usage: CREATE_USAGE,
    help: CREATE_HELP,
    values: &["--repo", "--branch", "--title", "--body-file", "--base"],
    flags: &["--draft"],
    required: &["--title", "--body-file"],
};
const UPDATE_PARSER: LegacyParserSpec = LegacyParserSpec {
    program: UPDATE_PROGRAM,
    usage: UPDATE_USAGE,
    help: UPDATE_HELP,
    values: &["--pr", "--repo", "--body-file"],
    flags: &[],
    required: &["--pr", "--body-file"],
};
const CHECKS_PARSER: LegacyParserSpec = LegacyParserSpec {
    program: CHECKS_PROGRAM,
    usage: CHECKS_USAGE,
    help: CHECKS_HELP,
    values: &["--pr", "--repo"],
    flags: &[],
    required: &["--pr", "--repo"],
};
const CLOSES_PARSER: LegacyParserSpec = LegacyParserSpec {
    program: CLOSES_PROGRAM,
    usage: CLOSES_USAGE,
    help: CLOSES_HELP,
    values: &["--body-file", "--repo"],
    flags: &[],
    required: &[],
};

/// Compose the implementation goal and changed-scope bullets for a PR.
pub fn compose_summary(arguments: &[OsString]) -> ExitCode {
    let parsed = match parse_required_with_help(
        arguments,
        SUMMARY_PROGRAM,
        SUMMARY_USAGE,
        SUMMARY_HELP,
        &["--plan-goals-file"],
        &[],
        &["--plan-goals-file"],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let supplied = parsed
        .value("--plan-goals-file")
        .expect("required option was checked")
        .to_string_lossy()
        .into_owned();
    match compose_summary_in(&supplied) {
        Ok(summary) => print!("{summary}"),
        Err(error) => {
            eprintln!("ERROR={error}");
            return ExitCode::from(2);
        }
    }
    ExitCode::SUCCESS
}

fn compose_summary_in(supplied: &str) -> Result<String, String> {
    let root = env::current_dir()
        .and_then(fs::canonicalize)
        .map_err(|_| format!("plan-goals path escapes repo root: {supplied}"))?;
    compose_summary_at(&root, supplied)
}

fn compose_summary_at(root: &Path, supplied: &str) -> Result<String, String> {
    let unresolved = if Path::new(supplied).is_absolute() {
        Path::new(supplied).to_path_buf()
    } else {
        root.join(supplied)
    };
    let plan = resolve_allow_missing(&unresolved)
        .map_err(|_| format!("plan-goals path escapes repo root: {supplied}"))?;
    if !path_under(&plan, root) {
        return Err(format!("plan-goals path escapes repo root: {supplied}"));
    }
    let metadata = fs::metadata(&plan).ok();
    if !metadata.is_some_and(|value| value.is_file() && value.len() > 0) {
        return Err(format!("plan-goals file missing or empty: {supplied}"));
    }
    let text =
        fs::read_to_string(&plan).map_err(|error| format!("could not read {supplied}: {error}"))?;
    let changed = changed_paths(root);
    compose_pr_summary(&text, changed.iter().map(String::as_str))
        .map_err(|_| format!("no Goal line found in {supplied}"))
}

fn changed_paths(root: &Path) -> Vec<String> {
    let Some((merge_base, head)) = merge_base_and_head(root) else {
        return Vec::new();
    };
    let Ok(base) = GitRef::new(merge_base) else {
        return Vec::new();
    };
    let Ok(head) = GitRef::new(head) else {
        return Vec::new();
    };
    let Ok(runtime) = GitCommandRuntime::for_repository(root) else {
        return Vec::new();
    };
    let result = runtime.runtime.block_on(runtime.git_cli().exact_diff(
        exact_name_only_request(Some(base), Some(head)),
        &runtime.cancellation,
    ));
    match result {
        Ok(result) if !result.truncated() && result.output().status().success() => {
            String::from_utf8_lossy(result.output().stdout())
                .lines()
                .filter(|line| !line.is_empty())
                .map(ToOwned::to_owned)
                .collect()
        }
        _ => Vec::new(),
    }
}

fn merge_base_and_head(root: &Path) -> Option<(String, String)> {
    let repository = GixRepository::discover(root).ok()?;
    let head = repository.resolve_revision(&Revision::new("HEAD")).ok()?;
    let origin_main = repository
        .resolve_revision(&Revision::new("origin/main"))
        .ok()?;
    let merge_base = repository.merge_base(&head, &origin_main).ok()?;
    Some((merge_base.to_hex(), head.to_hex()))
}

/// Branch facts shared by `pr create-branch --check` and `/implement` Step 0.
#[derive(Debug)]
pub struct BranchState {
    pub current_branch: String,
    pub is_main: String,
    pub is_user_branch: String,
    pub user_prefix: String,
}

/// Read the current branch and canonical user prefix without invoking Git.
pub fn branch_state() -> BranchState {
    let current_branch = crate::push_network::current_branch().unwrap_or_default();
    let user_prefix = user_prefix(&configured_git_user_name());
    let is_main = (current_branch.is_empty() || current_branch == "main").to_string();
    let is_user_branch = (!current_branch.is_empty()
        && current_branch.starts_with(&format!("{user_prefix}/")))
    .to_string();
    BranchState {
        current_branch,
        is_main,
        is_user_branch,
        user_prefix,
    }
}

fn configured_git_user_name() -> String {
    let Ok(cwd) = env::current_dir() else {
        return String::new();
    };
    let Ok(repository) = GixRepository::discover(cwd) else {
        return String::new();
    };
    let Ok(key) = ConfigKey::new("user.name") else {
        return String::new();
    };
    let Ok(values) = repository.config_values(&key) else {
        return String::new();
    };
    values
        .iter()
        .rev()
        .find(|value| {
            matches!(
                value.scope,
                ConfigScope::Repository
                    | ConfigScope::Worktree
                    | ConfigScope::Environment
                    | ConfigScope::CommandLine
                    | ConfigScope::Api
            )
        })
        .or_else(|| values.last())
        .map(|value| String::from_utf8_lossy(&value.value).trim().to_owned())
        .unwrap_or_default()
}

fn user_prefix(user_name: &str) -> String {
    let prefix: String = user_name
        .to_ascii_lowercase()
        .replace(' ', "-")
        .chars()
        .filter(|value| value.is_ascii_lowercase() || value.is_ascii_digit() || *value == '-')
        .take(20)
        .collect();
    let prefix = prefix.trim_end_matches('-');
    if prefix.is_empty() {
        "dev".to_owned()
    } else {
        prefix.to_owned()
    }
}

/// Create an implementation branch, or report the current branch facts.
pub fn create_branch(arguments: &[OsString]) -> ExitCode {
    let parsed = match legacy_parse(arguments, &BRANCH_PARSER, 2) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    if parsed.flag("--check") {
        let state = branch_state();
        emit_kv("CURRENT_BRANCH", &state.current_branch);
        emit_kv("IS_MAIN", &state.is_main);
        emit_kv("IS_USER_BRANCH", &state.is_user_branch);
        emit_kv("USER_PREFIX", &state.user_prefix);
        return ExitCode::SUCCESS;
    }
    let branch = option(&parsed, "--branch");
    if branch.is_empty() {
        eprintln!("create-branch.sh: --branch is required");
        return ExitCode::from(2);
    }
    let remote = option_or(&parsed, "--base-remote", "origin");
    let base_ref = option_or(&parsed, "--base-ref", "main");
    let base = format!("{remote}/{base_ref}");
    let prefix = user_prefix(&configured_git_user_name());
    if !branch.starts_with(&format!("{prefix}/"))
        || !valid_git_label(&remote)
        || !valid_git_label(&base_ref)
    {
        eprintln!("create-branch.sh: invalid: {branch}");
        return ExitCode::from(2);
    }
    let Ok(root) = env::current_dir() else {
        return branch_failure("create_failed", &branch, 2);
    };
    if local_branch_exists(&root, &branch) {
        return branch_failure("exists", &branch, 1);
    }
    if !fetch_base(&root, &remote, &base_ref) {
        return branch_failure("fetch_failed", &branch, 2);
    }
    let Ok(runtime) = GitCommandRuntime::for_repository(&root) else {
        return branch_failure("create_failed", &branch, 2);
    };
    let Ok(name) = GitRef::new(&branch) else {
        return branch_failure("create_failed", &branch, 2);
    };
    let Ok(start_point) = GitRef::new(&base) else {
        return branch_failure("create_failed", &branch, 2);
    };
    if runtime
        .runtime
        .block_on(runtime.git_cli().checkout(
            CheckoutRequest::Branch {
                create: true,
                force: false,
                no_track: true,
                name,
                start_point: Some(start_point),
            },
            &runtime.cancellation,
        ))
        .is_err()
    {
        return branch_failure("create_failed", &branch, 2);
    }
    emit_kv("BRANCH_NAME", &branch);
    emit_kv("ACTION", "created");
    ExitCode::SUCCESS
}

fn local_branch_exists(root: &Path, branch: &str) -> bool {
    let expected = format!("refs/heads/{branch}");
    GixRepository::discover(root)
        .and_then(|repository| repository.references())
        .is_ok_and(|references| {
            references
                .iter()
                .any(|reference| reference.name.as_bytes() == expected.as_bytes())
        })
}

fn fetch_base(root: &Path, remote: &str, base_ref: &str) -> bool {
    let Ok(remote) = GitRemote::new(remote) else {
        return false;
    };
    let Ok(refspec) = GitRefspec::new(base_ref) else {
        return false;
    };
    let Ok(runtime) = GitCommandRuntime::for_repository(root) else {
        return false;
    };
    for attempt in 0..3 {
        let fetched = runtime.runtime.block_on(runtime.git_cli().fetch(
            FetchRequest {
                remote: remote.clone(),
                refspec: Some(refspec.clone()),
                quiet: true,
                no_tags: false,
                mode: FetchMode::Standard,
            },
            &runtime.cancellation,
        ));
        if fetched.is_ok() {
            return true;
        }
        if attempt < 2 {
            thread::sleep(Duration::from_secs(1 << attempt));
        }
    }
    false
}

fn branch_failure(status: &str, branch: &str, code: u8) -> ExitCode {
    eprintln!("create-branch.sh: {status}: {branch}");
    ExitCode::from(code)
}

/// Create or adopt a pull request for the current clean branch.
pub fn create(arguments: &[OsString]) -> ExitCode {
    let parsed = match legacy_parse(arguments, &CREATE_PARSER, 1) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let title = option(&parsed, "--title");
    let repo = match resolve_repository(&parsed, "create-pr.sh") {
        Ok(repo) => repo,
        Err(code) => return code,
    };
    let branch = option(&parsed, "--branch");
    let current = crate::push_network::current_branch().unwrap_or_default();
    let branch = if branch.is_empty() {
        current.clone()
    } else {
        branch
    };
    if branch.is_empty() {
        eprintln!("create-pr.sh: not on a branch (detached HEAD)");
        return ExitCode::from(2);
    }
    let body_file = option(&parsed, "--body-file");
    let body = match fs::read_to_string(&body_file) {
        Ok(body) => body,
        Err(error) => {
            eprintln!("create-pr.sh: cannot read body file: {error}");
            return ExitCode::from(2);
        }
    };
    match scope_gate() {
        Ok(PrMutationScopeGate::Allowed) => {}
        Ok(PrMutationScopeGate::NeedsUser) => {
            emit_pr_result(0, "", &title, "needs-user");
            emit_needs_scope();
            return ExitCode::from(NEEDS_USER_EXIT);
        }
        Err(error) => return emit_pr_error(&title, &error),
    }
    if branch != current {
        emit_pr_result(0, "", &title, "push_failed");
        return ExitCode::from(2);
    }
    if !clean_worktree() {
        emit_pr_result(0, "", &title, "push_failed");
        return ExitCode::from(1);
    }
    let head = github_head(&repo, &branch);
    let existing = match open_pull_request(&repo, &head) {
        Ok(existing) => existing,
        Err(error) => return emit_pr_error(&title, &error),
    };
    if let Some(existing) = existing {
        if !crate::push_network::push_for_pr(&branch, true) {
            emit_pr_result(0, "", &title, "push_failed");
            return ExitCode::from(1);
        }
        let url = pull_request_url(&repo, existing.number());
        emit_pr_result(existing.number(), &url, existing.title(), "existing");
        return ExitCode::SUCCESS;
    }
    if !crate::push_network::push_for_pr(&branch, false) {
        emit_pr_result(0, "", &title, "push_failed");
        return ExitCode::from(1);
    }
    let body = match redact_pr_body(&body) {
        Ok(body) => body,
        Err(error) => return emit_pr_error(&title, &error),
    };
    let title = match redact_issue_text_outbound(&title) {
        Ok(title) => title,
        Err(error) => return emit_pr_error(&title, &error.to_string()),
    };
    let base = option(&parsed, "--base");
    match create_pull_request(&repo, &head, &title, &body, &base, parsed.flag("--draft")) {
        Ok((pull_request, created)) => {
            let status = if created { "created" } else { "existing" };
            let url = pull_request_url(&repo, pull_request.number());
            emit_pr_result(pull_request.number(), &url, pull_request.title(), status);
            ExitCode::SUCCESS
        }
        Err(error) => emit_pr_error(&title, &error),
    }
}

fn clean_worktree() -> bool {
    GixRepository::discover(".")
        .and_then(|repository| repository.local_status(&StatusOptions::default()))
        .is_ok_and(|status| !status.is_dirty())
}

fn scope_gate() -> Result<PrMutationScopeGate, String> {
    let root = env::current_dir()
        .and_then(fs::canonicalize)
        .map_err(|error| error.to_string())?;
    validate_pr_mutation_scope(&root)
}

fn open_pull_request(
    slug: &str,
    branch: &str,
) -> Result<Option<larch_adapters::github::PullRequest>, String> {
    let reference = repository_ref(slug).map_err(|()| "invalid repository slug".to_owned())?;
    with_github_service(async |service, cancellation| {
        service
            .list_open_pull_requests(cancellation, reference.owner(), reference.name(), branch)
            .await
            .map(|pull_requests| pull_requests.into_iter().next())
            .map_err(|error| error.to_string())
    })
    .map_err(ServiceFailure::into_detail)
}

fn pull_request_for_head(
    slug: &str,
    head: &str,
) -> Result<Option<larch_adapters::github::PullRequest>, String> {
    let reference = repository_ref(slug).map_err(|()| "invalid repository slug".to_owned())?;
    with_github_service(async |service, cancellation| {
        service
            .list_pull_requests_for_head(cancellation, reference.owner(), reference.name(), head)
            .await
            .map(|pull_requests| pull_requests.into_iter().next())
            .map_err(|error| error.to_string())
    })
    .map_err(ServiceFailure::into_detail)
}

fn github_head(target_repo: &str, branch: &str) -> String {
    let origin = remote_slug("origin");
    qualify_github_head(target_repo, origin.as_deref(), branch)
}

fn qualify_github_head(target_repo: &str, origin_repo: Option<&str>, branch: &str) -> String {
    if branch.contains(':') {
        return branch.to_owned();
    }
    let Some(origin) = origin_repo else {
        return branch.to_owned();
    };
    if origin.eq_ignore_ascii_case(target_repo) {
        return branch.to_owned();
    }
    origin.split_once('/').map_or_else(
        || branch.to_owned(),
        |(owner, _repo)| format!("{owner}:{branch}"),
    )
}

fn create_pull_request(
    slug: &str,
    branch: &str,
    title: &str,
    body: &str,
    base: &str,
    draft: bool,
) -> Result<(larch_adapters::github::PullRequest, bool), String> {
    let reference = repository_ref(slug).map_err(|()| "invalid repository slug".to_owned())?;
    with_github_service(async |service, cancellation| {
        let resolved_base = if base.is_empty() {
            service
                .repository(&reference, cancellation)
                .await
                .map_err(|error| error.to_string())?
                .default_branch
        } else {
            base.to_owned()
        };
        let created = service
            .create_pull_request(
                cancellation,
                &larch_adapters::github::PullRequestSpec {
                    owner: reference.owner(),
                    repo: reference.name(),
                    head: branch,
                    base: &resolved_base,
                    title,
                    body,
                    draft,
                },
            )
            .await
            .map_err(|error| error.to_string())?;
        if created.created() {
            IssueMutationOwner::new(service)
                .assign_authenticated_user(
                    cancellation,
                    &LiveMutationRequest {
                        context_file: None,
                        operator_mode: true,
                        run_id: "",
                        trusted_root: None,
                        test_deny: false,
                    },
                    &reference,
                    created.pull_request().number(),
                )
                .await
                .map_err(|error| error.to_string())?;
        }
        Ok((created.pull_request().clone(), created.created()))
    })
    .map_err(ServiceFailure::into_detail)
}

fn emit_pr_result(number: u64, url: &str, title: &str, status: &str) {
    emit_kv("PR_NUMBER", &number.to_string());
    emit_kv("PR_URL", url);
    emit_kv("PR_TITLE", title);
    emit_kv("PR_STATUS", status);
}

fn emit_pr_error(title: &str, error: &str) -> ExitCode {
    emit_kv("PR_STATUS", "error");
    emit_kv("PR_NUMBER", "0");
    emit_kv("PR_URL", "");
    emit_kv("PR_TITLE", title);
    eprintln!("{error}");
    ExitCode::from(2)
}

fn emit_needs_scope() {
    emit_kv("needs_user_reason", "scope-disposition");
    emit_kv("NEXT_ACTION", "halt-scope-disposition");
}

fn pull_request_url(slug: &str, number: u64) -> String {
    format!("https://github.com/{slug}/pull/{number}")
}

/// Replace one PR body through the typed GitHub service.
pub fn body_update(arguments: &[OsString]) -> ExitCode {
    let parsed = match legacy_parse(arguments, &UPDATE_PARSER, 2) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let explicit_repo = option(&parsed, "--repo");
    if !explicit_repo.is_empty() && !validate_repo_slug(&explicit_repo) {
        eprintln!(
            "gh-pr-body-update.sh: --repo must be OWNER/REPO using GitHub owner/repo characters"
        );
        return ExitCode::from(2);
    }
    let body_file = option(&parsed, "--body-file");
    if !Path::new(&body_file).is_file() {
        emit_update(false, &format!("body file not found: {body_file}"));
        return ExitCode::from(2);
    }
    match scope_gate() {
        Ok(PrMutationScopeGate::Allowed) => {}
        Ok(PrMutationScopeGate::NeedsUser) => {
            emit_update(false, "scope-disposition required");
            emit_needs_scope();
            return ExitCode::from(NEEDS_USER_EXIT);
        }
        Err(error) => {
            emit_update(false, &one_line(&error));
            return ExitCode::from(2);
        }
    }
    let repo = if explicit_repo.is_empty() {
        ambient_repo().unwrap_or_default()
    } else {
        explicit_repo
    };
    let Some(number) = resolve_pr_selector(&repo, &option(&parsed, "--pr")) else {
        emit_update(
            false,
            "gh pr edit failed (exit 1): invalid pull request selector",
        );
        return ExitCode::from(2);
    };
    let body = match fs::read_to_string(&body_file)
        .and_then(|body| redact_pr_body(&body).map_err(std::io::Error::other))
    {
        Ok(body) => body,
        Err(error) => {
            emit_update(false, &format!("gh pr edit failed (exit 1): {error}"));
            return ExitCode::from(2);
        }
    };
    let result = update_pull_request_body(&repo, number, &body);
    match result {
        Ok(()) => {
            emit_update(true, "");
            ExitCode::SUCCESS
        }
        Err(error) => {
            emit_update(
                false,
                &format!("gh pr edit failed (exit 1): {}", one_line(&error)),
            );
            ExitCode::from(2)
        }
    }
}

fn update_pull_request_body(slug: &str, number: u64, body: &str) -> Result<(), String> {
    let reference = repository_ref(slug).map_err(|()| "repository not found".to_owned())?;
    with_github_service(async |service, cancellation| {
        let edited = service
            .edit_pull_request(
                cancellation,
                &larch_adapters::github::PullRequestEdit {
                    owner: reference.owner(),
                    repo: reference.name(),
                    number,
                    title: None,
                    body: Some(body),
                    state: None,
                    base: None,
                },
            )
            .await
            .map_err(|error| error.to_string())?;
        if edited.body().trim_end_matches('\n') != body.trim_end_matches('\n') {
            return Err("pull request body read-back did not match".to_owned());
        }
        Ok(())
    })
    .map_err(ServiceFailure::into_detail)
}

fn emit_update(updated: bool, error: &str) {
    emit_kv("UPDATED", &updated.to_string());
    emit_kv("ERROR", error);
}

/// Render the current PR checks in the legacy `gh pr checks` text shape.
pub fn checks(arguments: &[OsString]) -> ExitCode {
    let parsed = match legacy_parse(arguments, &CHECKS_PARSER, 1) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let raw_number = option(&parsed, "--pr");
    let number = match raw_number.parse::<u64>() {
        Ok(number) if number > 0 => number,
        _ => {
            let _ = usage_error(
                CHECKS_USAGE,
                CHECKS_PROGRAM,
                &format!("argument --pr: invalid int value: '{raw_number}'"),
                2,
            );
            return ExitCode::from(1);
        }
    };
    let repo = option(&parsed, "--repo");
    if !validate_repo_slug(&repo) {
        eprintln!("gh-pr-checks.sh: --repo must be OWNER/REPO using GitHub owner/repo characters");
        return ExitCode::from(2);
    }
    let Ok(reference) = repository_ref(&repo) else {
        return ExitCode::from(2);
    };
    let checks = with_github_service(async |service, cancellation| {
        service
            .check_runs(
                &reference,
                &format!("refs/pull/{number}/head"),
                cancellation,
            )
            .await
            .map_err(|error| error.to_string())
    });
    let checks = match checks {
        Ok(checks) => checks,
        Err(error) => {
            eprintln!("{}", error.into_detail());
            return ExitCode::from(1);
        }
    };
    let mut failed = false;
    let mut pending = false;
    for check in &checks {
        let (bucket, blocks_as_failure, blocks_as_pending) = check_output_state(check.bucket);
        failed |= blocks_as_failure;
        pending |= blocks_as_pending;
        let name = SafeText::diagnostic(&check.name);
        let details = SafeText::diagnostic(check.details_url.as_deref().unwrap_or_default());
        let description = SafeText::diagnostic(check.description.as_deref().unwrap_or_default());
        println!(
            "{}\t{}\t{}\t{}\t{}",
            name,
            bucket,
            format_duration(check.wall_clock_seconds),
            details,
            description
        );
    }
    if failed || checks.is_empty() {
        ExitCode::from(1)
    } else if pending {
        ExitCode::from(8)
    } else {
        ExitCode::SUCCESS
    }
}

const fn check_output_state(bucket: CheckBucket) -> (&'static str, bool, bool) {
    match bucket {
        CheckBucket::Pass => ("pass", false, false),
        CheckBucket::Fail => ("fail", true, false),
        CheckBucket::Pending => ("pending", false, true),
        CheckBucket::Skipping => ("skipping", false, false),
        // `gh pr checks` renders cancelled checks as `fail` in the non-TTY
        // grammar but does not make cancellation alone exit 1.
        CheckBucket::Cancel => ("fail", false, false),
    }
}

fn format_duration(seconds: Option<u64>) -> String {
    let Some(seconds) = seconds.filter(|seconds| *seconds > 0) else {
        return "0".to_owned();
    };
    let hours = seconds / 3600;
    let minutes = seconds % 3600 / 60;
    let seconds = seconds % 60;
    if hours > 0 {
        format!("{hours}h{minutes}m{seconds}s")
    } else if minutes > 0 {
        format!("{minutes}m{seconds}s")
    } else {
        format!("{seconds}s")
    }
}

/// Print the first `Closes #N` footer from a file or the current pull request.
pub fn closes_issue(arguments: &[OsString]) -> ExitCode {
    let parsed = match legacy_parse(arguments, &CLOSES_PARSER, 1) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let body_file = option(&parsed, "--body-file");
    if !body_file.is_empty() {
        println!(
            "{}",
            fs::read_to_string(body_file)
                .ok()
                .as_deref()
                .map(extract_closes_issue)
                .unwrap_or_default()
        );
        return ExitCode::SUCCESS;
    }
    let explicit_repo = option(&parsed, "--repo");
    if !explicit_repo.is_empty() && !validate_repo_slug(&explicit_repo) {
        eprintln!(
            "gh-pr-closes-issue.sh: --repo must be OWNER/REPO using GitHub owner/repo characters"
        );
        return ExitCode::from(2);
    }
    let repo = if explicit_repo.is_empty() {
        ambient_repo().unwrap_or_default()
    } else {
        explicit_repo
    };
    if repo.is_empty() {
        println!();
        return ExitCode::SUCCESS;
    }
    let branch = crate::push_network::current_branch().unwrap_or_default();
    let issue = if branch.is_empty() {
        String::new()
    } else {
        let head = github_head(&repo, &branch);
        pull_request_for_head(&repo, &head)
            .ok()
            .flatten()
            .map(|pull_request| extract_closes_issue(pull_request.body()))
            .unwrap_or_default()
    };
    println!("{issue}");
    ExitCode::SUCCESS
}

fn extract_closes_issue(body: &str) -> String {
    CLOSES_ISSUE
        .captures(body)
        .and_then(|captures| captures.get(1))
        .map_or_else(String::new, |number| number.as_str().to_owned())
}

fn resolve_repository(parsed: &ParsedCommandLine, script: &str) -> Result<String, ExitCode> {
    let explicit = option(parsed, "--repo");
    if !explicit.is_empty() && !validate_repo_slug(&explicit) {
        eprintln!("{script}: --repo must be OWNER/REPO using GitHub owner/repo characters");
        return Err(ExitCode::from(2));
    }
    Ok(if explicit.is_empty() {
        ambient_repo().unwrap_or_default()
    } else {
        explicit
    })
}

fn resolve_pr_selector(slug: &str, selector: &str) -> Option<u64> {
    selector
        .parse::<u64>()
        .ok()
        .filter(|number| *number > 0)
        .or_else(|| github_pr_url_number(slug, selector))
        .or_else(|| {
            valid_pr_branch_selector(selector)
                .then(|| github_head(slug, selector))
                .and_then(|head| open_pull_request(slug, &head).ok().flatten())
                .map(|pull_request| pull_request.number())
        })
}

fn valid_pr_branch_selector(selector: &str) -> bool {
    GitRef::new(selector).is_ok()
}

fn github_pr_url_number(slug: &str, selector: &str) -> Option<u64> {
    let path = selector
        .strip_prefix("https://github.com/")
        .or_else(|| selector.strip_prefix("http://github.com/"))?;
    let mut parts = path.trim_end_matches('/').split('/');
    let owner = parts.next()?;
    let repo = parts.next()?;
    if parts.next()? != "pull" {
        return None;
    }
    let number = parts
        .next()?
        .parse::<u64>()
        .ok()
        .filter(|number| *number > 0)?;
    if parts.next().is_some() {
        return None;
    }
    let expected = format!("{owner}/{repo}");
    expected.eq_ignore_ascii_case(slug).then_some(number)
}

fn legacy_parse(
    arguments: &[OsString],
    spec: &LegacyParserSpec,
    wrapper_exit: u8,
) -> Result<ParsedCommandLine, ExitCode> {
    parse_required_with_help(
        arguments,
        spec.program,
        spec.usage,
        spec.help,
        spec.values,
        spec.flags,
        spec.required,
    )
    .map_err(|_code| ExitCode::from(wrapper_exit))
}

fn option(parsed: &ParsedCommandLine, name: &str) -> String {
    parsed
        .value(name)
        .unwrap_or_else(|| OsStr::new(""))
        .to_string_lossy()
        .into_owned()
}

fn option_or(parsed: &ParsedCommandLine, name: &str, fallback: &str) -> String {
    let value = option(parsed, name);
    if value.is_empty() {
        fallback.to_owned()
    } else {
        value
    }
}

fn one_line(value: &str) -> String {
    value.split_whitespace().collect::<Vec<_>>().join(" ")
}

#[cfg(test)]
#[path = "pr_commands/tests.rs"]
mod coverage_tests;

#[cfg(test)]
mod tests {
    use super::{
        check_output_state, compose_summary_at, extract_closes_issue, format_duration,
        github_pr_url_number, qualify_github_head, user_prefix, valid_pr_branch_selector,
    };
    use larch_core::CheckBucket;
    use larch_test_support::{GitFixture, GitRepository};
    use std::fs;
    use tempfile::TempDir;

    #[test]
    fn composes_without_git_metadata() {
        let fixture = TempDir::new().expect("fixture");
        fs::write(fixture.path().join("plan.md"), "## Goal\nShip Rust.\n").expect("plan write");
        assert_eq!(
            compose_summary_at(fixture.path(), "plan.md"),
            Ok("- Ship Rust.\n".to_owned())
        );
    }

    #[test]
    fn refuses_escape_missing_empty_and_goalless_inputs() {
        let fixture = TempDir::new().expect("fixture");
        let outside = TempDir::new().expect("outside fixture");
        fs::write(fixture.path().join("empty.md"), "").expect("empty write");
        fs::write(fixture.path().join("scope.md"), "## Scope\nNo goal\n").expect("scope write");
        assert!(
            compose_summary_at(
                fixture.path(),
                outside.path().join("plan.md").to_string_lossy().as_ref()
            )
            .is_err_and(|error| error.contains("path escapes repo root"))
        );
        assert_eq!(
            compose_summary_at(fixture.path(), "missing.md"),
            Err("plan-goals file missing or empty: missing.md".to_owned())
        );
        assert_eq!(
            compose_summary_at(fixture.path(), "empty.md"),
            Err("plan-goals file missing or empty: empty.md".to_owned())
        );
        assert_eq!(
            compose_summary_at(fixture.path(), "scope.md"),
            Err("no Goal line found in scope.md".to_owned())
        );
    }

    #[test]
    fn reads_the_merge_base_diff_through_typed_git() {
        let fixture = GitRepository::builder(GitFixture::Unborn)
            .build()
            .expect("fixture");
        fs::write(fixture.root().join("plan.md"), "## Goal\nShip Rust.\n").expect("plan write");
        fs::write(fixture.root().join("base.txt"), "base\n").expect("base write");
        git(&fixture, &["add", "."]);
        git(&fixture, &["commit", "-q", "-m", "base"]);
        git(
            &fixture,
            &["update-ref", "refs/remotes/origin/main", "HEAD"],
        );
        for (path, contents) in [
            ("crates/owner.rs", "owner\n"),
            ("docs/contract.md", "contract\n"),
            ("scripts/test-owner.sh", "#!/bin/sh\n"),
        ] {
            let target = fixture.root().join(path);
            fs::create_dir_all(target.parent().expect("changed parent")).expect("parent create");
            fs::write(target, contents).expect("changed file write");
        }
        git(&fixture, &["add", "."]);
        git(&fixture, &["commit", "-q", "-m", "change"]);

        assert_eq!(
            compose_summary_at(fixture.root(), "plan.md"),
            Ok(concat!(
                "- Ship Rust.\n",
                "- Added or updated 1 test file(s).\n",
                "- Cross-cutting changes across: crates,docs,scripts.\n"
            )
            .to_owned())
        );
    }

    #[test]
    fn lifecycle_helpers_preserve_legacy_text_contracts() {
        assert_eq!(user_prefix("Ada Lovelace"), "ada-lovelace");
        assert_eq!(user_prefix("---"), "dev");
        assert_eq!(
            user_prefix("abcdefghijklmnopqrstuv"),
            "abcdefghijklmnopqrst"
        );
        assert_eq!(extract_closes_issue("Part of #2\nCloses #8790\n"), "8790");
        assert_eq!(extract_closes_issue("closes #8790"), "");
        assert_eq!(format_duration(None), "0");
        assert_eq!(format_duration(Some(26)), "26s");
        assert_eq!(format_duration(Some(191)), "3m11s");
        assert_eq!(format_duration(Some(3_723)), "1h2m3s");
        assert_eq!(
            check_output_state(CheckBucket::Cancel),
            ("fail", false, false)
        );
        assert_eq!(
            github_pr_url_number("owner/repo", "https://github.com/Owner/Repo/pull/8790/"),
            Some(8790)
        );
        assert_eq!(github_pr_url_number("owner/repo", "feature/8790"), None);
        assert!(valid_pr_branch_selector("feature/with+plus"));
        assert_eq!(
            github_pr_url_number("owner/repo", "https://github.com/other/repo/pull/8790"),
            None
        );
        assert_eq!(
            qualify_github_head("upstream/repo", Some("fork/repo"), "feature"),
            "fork:feature"
        );
        assert_eq!(
            qualify_github_head("owner/repo", Some("OWNER/REPO"), "feature"),
            "feature"
        );
        assert_eq!(
            qualify_github_head("upstream/repo", Some("fork/repo"), "fork:feature"),
            "fork:feature"
        );
    }

    fn git(repository: &GitRepository, arguments: &[&str]) {
        let output = repository.git(arguments).expect("git fixture command");
        assert!(
            output.success(),
            "git {arguments:?}: {}",
            String::from_utf8_lossy(&output.stderr)
        );
    }
}
