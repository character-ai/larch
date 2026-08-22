//! Rust owner for `implement cleanup` and the three `implement-finalize` phases.
//!
//! The command keeps the retired Python wire intact while routing repository
//! reads through gitoxide, mutations through the closed typed Git adapter,
//! GitHub work through the shared service owners, and process cleanup through
//! the reusable identity-validated kill-log owner.

use std::{
    collections::BTreeMap,
    env,
    ffi::{OsStr, OsString},
    fmt::Write as _,
    fs,
    io::Write as _,
    path::{Component, Path, PathBuf},
    process::ExitCode,
};

use chrono::{SecondsFormat, Utc};
use larch_adapters::{
    BranchMutationRequest, CheckoutRequest, FetchRequest, GitCliError, GitCliResult, GitRef,
    GitRefspec, GitRemote, GixRepository, LsRemoteRequest, PullRequest, RebaseRequest,
    StashRequest, SystemProcessIdentityHost,
    progress_state::{deactivate_run, progress_cache_home, progress_paths},
    remove_session_tmpdir, resolve_allow_missing, writer_target_allowed,
};
use larch_core::{
    DuplicateInputPolicy, DuplicatePolicy, GitHubIssueState, KeyPolicy, KvDocument, KvRow,
    ParseOptions, ProcessOutput, RepositoryRead as _, Revision, StatusOptions,
    allowed_session_roots, has_live_entry, kill_session_background_processes, private_atomic_write,
    validate_progress_run_id,
};

use crate::{
    argparse_compat::{missing, parse_required_with_help, parse_with_flags},
    git_command_runtime::GitCommandRuntime,
    git_commands::{is_transient_net, sleep_before_retry},
    implement_scope_disposition_commands::{
        has_persisted_coverage, persisted_repo_root, teardown_disposition,
    },
    issue_commands::read_issue_live,
    tracking_issue_commands::rename_finalize_live,
};

const CLEANUP_PROGRAM: &str = "cli.py implement cleanup";
const CLEANUP_USAGE: &str =
    "usage: cli.py implement cleanup [-h] --implement-tmpdir IMPLEMENT_TMPDIR";
const CLEANUP_HELP: &str = "usage: cli.py implement cleanup [-h] --implement-tmpdir IMPLEMENT_TMPDIR\n\noptions:\n  -h, --help            show this help message and exit\n  --implement-tmpdir IMPLEMENT_TMPDIR";
const POSTBUMP_HELP: &str = "usage: cli.py implement-finalize postbump [-h] --state-file STATE_FILE\n                                          --implement-tmpdir IMPLEMENT_TMPDIR\n                                          [--final-bail-reason-file FINAL_BAIL_REASON_FILE]\n\noptions:\n  -h, --help            show this help message and exit\n  --state-file STATE_FILE\n  --implement-tmpdir IMPLEMENT_TMPDIR\n  --final-bail-reason-file FINAL_BAIL_REASON_FILE";
const POSTMERGE_HELP: &str = "usage: cli.py implement-finalize postmerge [-h] --state-file STATE_FILE\n                                           [--implement-tmpdir IMPLEMENT_TMPDIR]\n                                           --final-bail-reason-file\n                                           FINAL_BAIL_REASON_FILE\n\noptions:\n  -h, --help            show this help message and exit\n  --state-file STATE_FILE\n  --implement-tmpdir IMPLEMENT_TMPDIR\n  --final-bail-reason-file FINAL_BAIL_REASON_FILE";
const TEARDOWN_HELP: &str = "usage: cli.py implement-finalize teardown [-h] --state-file STATE_FILE\n                                          --implement-tmpdir IMPLEMENT_TMPDIR\n                                          [--final-bail-reason-file FINAL_BAIL_REASON_FILE]\n\noptions:\n  -h, --help            show this help message and exit\n  --state-file STATE_FILE\n  --implement-tmpdir IMPLEMENT_TMPDIR\n  --final-bail-reason-file FINAL_BAIL_REASON_FILE";
const POSTBUMP_USAGE: &str = "usage: cli.py implement-finalize postbump [-h] --state-file STATE_FILE --implement-tmpdir IMPLEMENT_TMPDIR [--final-bail-reason-file FINAL_BAIL_REASON_FILE]";
const POSTMERGE_USAGE: &str = "usage: cli.py implement-finalize postmerge [-h] --state-file STATE_FILE [--implement-tmpdir IMPLEMENT_TMPDIR] --final-bail-reason-file FINAL_BAIL_REASON_FILE";
const TEARDOWN_USAGE: &str = "usage: cli.py implement-finalize teardown [-h] --state-file STATE_FILE --implement-tmpdir IMPLEMENT_TMPDIR [--final-bail-reason-file FINAL_BAIL_REASON_FILE]";
const PATH_ERROR: &str =
    "must be under /tmp/, /private/tmp/, /var/folders/, or the larch cache sessions root";
const CHECKPOINT_MAX_BYTES: u64 = 64;
#[rustfmt::skip]
const COMMON_REQUIRED: &[&str] = &["BRANCH_NAME", "PR_NUMBER", "PR_TITLE", "PR_URL", "ISSUE_NUMBER", "REPO", "DRAFT", "MERGE", "DEFERRED", "REPO_UNAVAILABLE", "PR_CLOSED", "DESIGN_ONLY_DONE", "BAIL_NEEDS_USER_INPUT", "STALL_TRACKING", "DONE_RENAME_APPLIED"];
#[rustfmt::skip]
const COMMON_BOOLS: &[&str] = &["DRAFT", "MERGE", "DEFERRED", "REPO_UNAVAILABLE", "PR_CLOSED", "DESIGN_ONLY_DONE", "BAIL_NEEDS_USER_INPUT", "STALL_TRACKING", "DONE_RENAME_APPLIED"];
#[rustfmt::skip]
const POSTBUMP_REQUIRED: &[&str] = &["BRANCH_NAME", "ISSUE_NUMBER", "PR_TITLE", "REPO", "REPO_UNAVAILABLE", "FORKED_TARGET", "BUMP_TYPE", "NEW_VERSION"];

#[derive(Clone, Copy, Eq, PartialEq)]
pub enum FinalizePhase {
    Postbump,
    Postmerge,
    Teardown,
}

impl FinalizePhase {
    const fn name(self) -> &'static str {
        match self {
            Self::Postbump => "postbump",
            Self::Postmerge => "postmerge",
            Self::Teardown => "teardown",
        }
    }

    const fn program(self) -> &'static str {
        match self {
            Self::Postbump => "cli.py implement-finalize postbump",
            Self::Postmerge => "cli.py implement-finalize postmerge",
            Self::Teardown => "cli.py implement-finalize teardown",
        }
    }

    const fn usage(self) -> &'static str {
        match self {
            Self::Postbump => POSTBUMP_USAGE,
            Self::Postmerge => POSTMERGE_USAGE,
            Self::Teardown => TEARDOWN_USAGE,
        }
    }

    const fn help(self) -> &'static str {
        match self {
            Self::Postbump => POSTBUMP_HELP,
            Self::Postmerge => POSTMERGE_HELP,
            Self::Teardown => TEARDOWN_HELP,
        }
    }
}

/// Captured command result used by the in-process ship and Step 19 callers.
pub struct CapturedFinalize {
    pub code: u8,
    pub stdout: String,
    pub stderr: String,
}

impl CapturedFinalize {
    fn error(code: u8, stderr: impl Into<String>) -> Self {
        Self {
            code,
            stdout: String::new(),
            stderr: stderr.into(),
        }
    }
}

#[derive(Default)]
struct FinalizeResult {
    outcome: &'static str,
    status: String,
    detail: String,
    local_cleanup_status: String,
    verify_main_status: String,
    rename_branch: String,
    rename_status: String,
    sentinel_written: bool,
    stash_ref: String,
    rebase_status: String,
    force_push_status: String,
    log_write_status: String,
    issue_url: String,
    conflict_files: String,
}

impl FinalizeResult {
    fn new(outcome: &'static str, status: &str) -> Self {
        Self {
            outcome,
            status: status.to_owned(),
            ..Self::default()
        }
    }

    fn render(&self, phase: FinalizePhase) -> String {
        let mut text = String::new();
        for (key, value) in [
            ("STATUS", self.status.as_str()),
            ("OUTCOME", self.outcome),
            ("FINALIZE_WARNINGS", self.detail.as_str()),
            ("LOG_WRITE_STATUS", self.log_write_status.as_str()),
            ("REBASE_STATUS", self.rebase_status.as_str()),
            ("CONFLICT_FILES", self.conflict_files.as_str()),
            ("FORCE_PUSH_STATUS", self.force_push_status.as_str()),
            ("LOCAL_CLEANUP_STATUS", self.local_cleanup_status.as_str()),
            ("VERIFY_MAIN_STATUS", self.verify_main_status.as_str()),
            ("RENAME_BRANCH", self.rename_branch.as_str()),
            ("RENAME_STATUS", self.rename_status.as_str()),
            ("ISSUE_URL", self.issue_url.as_str()),
            ("STASH_REF", self.stash_ref.as_str()),
            (
                "SENTINEL_WRITTEN",
                if self.sentinel_written {
                    "true"
                } else {
                    "false"
                },
            ),
            ("FINALIZE_SUBCOMMAND", phase.name()),
        ] {
            let _ = writeln!(text, "{key}={}", safe_line(value));
        }
        text
    }
}

#[derive(Default)]
// These booleans are independent fields in the persisted shell-state wire.
#[allow(clippy::struct_excessive_bools)]
struct Context {
    branch: String,
    issue: String,
    repo: String,
    run_id: String,
    tmpdir: PathBuf,
    manifest: Option<PathBuf>,
    pr_number: Option<u64>,
    pr_title: String,
    merge: bool,
    draft: bool,
    forked: bool,
    repo_unavailable: bool,
    design_only_done: bool,
    stall_tracking: bool,
    done_rename_applied: bool,
    stall_step: String,
    expected_session_id: String,
    expected_tmpdir_prefix: String,
    final_bail_reason: String,
}

impl Context {
    fn from_state(
        data: &BTreeMap<String, String>,
        tmpdir: PathBuf,
        bail_file: Option<&Path>,
    ) -> Self {
        let value = |key: &str| {
            data.get(key)
                .cloned()
                .or_else(|| env::var(key).ok())
                .unwrap_or_default()
        };
        let value_or = |primary: &str, fallback: &str| {
            let primary = value(primary);
            if primary.is_empty() {
                value(fallback)
            } else {
                primary
            }
        };
        let run_id = {
            let value = value("RUN_ID");
            if value.is_empty() {
                env::var("LARCH_RUN_ID").unwrap_or_default()
            } else {
                value
            }
        };
        let final_bail_reason = bail_file
            .and_then(|path| fs::read(path).ok())
            .map(|bytes| String::from_utf8_lossy(&bytes).trim().replace('\n', " "))
            .filter(|text| !text.is_empty())
            .unwrap_or_else(|| value("FINAL_BAIL_REASON"))
            .chars()
            .take(1024)
            .collect();
        Self {
            branch: value_or("BRANCH_NAME", "BRANCH"),
            issue: value_or("ISSUE_NUMBER", "ISSUE"),
            repo: value("REPO"),
            run_id,
            tmpdir,
            manifest: nonempty(value("MANIFEST_PATH")).map(PathBuf::from),
            pr_number: value("PR_NUMBER").trim().parse().ok(),
            pr_title: value("PR_TITLE"),
            merge: bool_value(&value("MERGE")),
            draft: bool_value(&value("DRAFT")),
            forked: bool_value(&value("FORKED_TARGET")) || bool_value(&value("FORKED")),
            repo_unavailable: bool_value(&value("REPO_UNAVAILABLE")),
            design_only_done: bool_value(&value("DESIGN_ONLY_DONE")),
            stall_tracking: bool_value(&value("STALL_TRACKING")),
            done_rename_applied: bool_value(&value("DONE_RENAME_APPLIED")),
            stall_step: value("STALL_STEP"),
            expected_session_id: value("EXPECTED_SESSION_ID"),
            expected_tmpdir_prefix: value("EXPECTED_TMPDIR_BASENAME_PREFIX"),
            final_bail_reason,
        }
    }
}

struct FinalizeArguments {
    state_file: PathBuf,
    implement_tmpdir: Option<PathBuf>,
    bail_file: Option<PathBuf>,
}

/// Run one public finalize phase and emit its captured streams.
pub fn command(phase: FinalizePhase, arguments: &[OsString]) -> ExitCode {
    emit_capture(&execute(phase, arguments))
}

/// Run one finalize phase without re-entering the executable.
pub fn execute(phase: FinalizePhase, arguments: &[OsString]) -> CapturedFinalize {
    let parsed = match parse_finalize_arguments(phase, arguments) {
        Ok(value) => value,
        Err(capture) => return capture,
    };
    let state = match load_state_checked(&parsed.state_file) {
        Ok(value) => value,
        Err(message) => return validation_error(&message),
    };
    if let Err(message) = validate_state(phase, &state, &parsed) {
        return validation_error(&message);
    }
    let tmpdir = parsed
        .implement_tmpdir
        .clone()
        .filter(|path| !path.as_os_str().is_empty())
        .or_else(|| {
            nonempty(state.get("IMPLEMENT_TMPDIR").cloned().unwrap_or_default()).map(PathBuf::from)
        })
        .unwrap_or_else(|| {
            parsed
                .state_file
                .parent()
                .unwrap_or_else(|| Path::new(""))
                .to_path_buf()
        });
    let context = Context::from_state(&state, tmpdir, parsed.bail_file.as_deref());
    let mut stderr = String::new();
    let result = match phase {
        FinalizePhase::Postbump => Ok(postbump(&context)),
        FinalizePhase::Postmerge => Ok(postmerge(&context, &mut stderr)),
        FinalizePhase::Teardown => teardown(&context, &mut stderr),
    };
    match result {
        Ok(result) => CapturedFinalize {
            code: 0,
            stdout: result.render(phase),
            stderr,
        },
        Err(message) => CapturedFinalize {
            code: 1,
            stdout: String::new(),
            stderr: format!("implement-finalize: {}\n", safe_line(&message)),
        },
    }
}

/// Remove one validated implementation session directory.
pub fn cleanup(arguments: &[OsString]) -> ExitCode {
    let parsed = match parse_required_with_help(
        arguments,
        CLEANUP_PROGRAM,
        CLEANUP_USAGE,
        CLEANUP_HELP,
        &["--implement-tmpdir"],
        &[],
        &["--implement-tmpdir"],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let raw = parsed.value("--implement-tmpdir").unwrap_or_default();
    let tmpdir = PathBuf::from(raw);
    let state = load_state_lenient(&tmpdir.join("finalize-state.sh"));
    let context = cleanup_context(&state, &tmpdir);
    if tmpdir.exists() && cleanup_target_ok(&context, &tmpdir) {
        if remove_session_tmpdir(&tmpdir).is_ok() && !tmpdir.exists() {
            println!("CLEANED=true");
            return ExitCode::SUCCESS;
        }
        println!("CLEANED=false\nERROR=cleanup-tmpdir failed");
        return ExitCode::FAILURE;
    }
    println!("CLEANED=false\nERROR=cleanup target rejected");
    ExitCode::from(2)
}

fn cleanup_context(state: &BTreeMap<String, String>, tmpdir: &Path) -> Context {
    let ambient = |key: &str| env::var(key).ok();
    let value = |key: &str| {
        ambient(key)
            .or_else(|| state.get(key).cloned())
            .unwrap_or_default()
    };
    Context {
        tmpdir: tmpdir.to_path_buf(),
        expected_session_id: value("EXPECTED_SESSION_ID"),
        expected_tmpdir_prefix: value("EXPECTED_TMPDIR_BASENAME_PREFIX"),
        ..Context::default()
    }
}

fn parse_finalize_arguments(
    phase: FinalizePhase,
    arguments: &[OsString],
) -> Result<FinalizeArguments, CapturedFinalize> {
    let options = [
        "--state-file",
        "--implement-tmpdir",
        "--final-bail-reason-file",
    ];
    let parsed = parse_with_flags(arguments, &options, &["-h", "--help"], 0);
    if parsed.flag("-h") || parsed.flag("--help") {
        return Err(CapturedFinalize {
            code: 2,
            stdout: format!("{}\n", phase.help()),
            stderr: String::new(),
        });
    }
    if let Some(error) = parsed
        .value_error()
        .map(ToOwned::to_owned)
        .or_else(|| parsed.error())
    {
        return Err(argparse_capture(phase, &error));
    }
    let required = match phase {
        FinalizePhase::Postmerge => ["--state-file", "--final-bail-reason-file"].as_slice(),
        FinalizePhase::Postbump | FinalizePhase::Teardown => {
            ["--state-file", "--implement-tmpdir"].as_slice()
        }
    };
    let states = required
        .iter()
        .map(|option| (*option, parsed.value(option).is_some()))
        .collect::<Vec<_>>();
    if states.iter().any(|(_, present)| !present) {
        return Err(argparse_capture(phase, &missing(&states)));
    }
    Ok(FinalizeArguments {
        state_file: PathBuf::from(parsed.value("--state-file").unwrap_or_default()),
        implement_tmpdir: parsed.value("--implement-tmpdir").map(PathBuf::from),
        bail_file: parsed.value("--final-bail-reason-file").map(PathBuf::from),
    })
}

fn argparse_capture(phase: FinalizePhase, error: &str) -> CapturedFinalize {
    CapturedFinalize::error(
        2,
        format!("{}\n{}: error: {error}\n", phase.usage(), phase.program()),
    )
}

fn validation_error(message: &str) -> CapturedFinalize {
    CapturedFinalize::error(2, format!("implement-finalize: {message}\n"))
}

fn emit_capture(capture: &CapturedFinalize) -> ExitCode {
    let _ = std::io::stdout().write_all(capture.stdout.as_bytes());
    let _ = std::io::stderr().write_all(capture.stderr.as_bytes());
    ExitCode::from(capture.code)
}

fn validate_state(
    phase: FinalizePhase,
    data: &BTreeMap<String, String>,
    arguments: &FinalizeArguments,
) -> Result<(), String> {
    if !allowed_finalize_path(&arguments.state_file) {
        return Err(format!("--state-file {PATH_ERROR}"));
    }
    if matches!(phase, FinalizePhase::Postbump | FinalizePhase::Teardown) {
        let tmpdir = arguments
            .implement_tmpdir
            .as_ref()
            .ok_or_else(|| "--implement-tmpdir is required".to_owned())?;
        if !allowed_finalize_path(tmpdir) {
            return Err(format!("--implement-tmpdir {PATH_ERROR}"));
        }
        let state = resolve_allow_missing(&arguments.state_file)
            .map_err(|_| "state-file or implement-tmpdir resolution failed".to_owned())?;
        let root = resolve_allow_missing(tmpdir)
            .map_err(|_| "state-file or implement-tmpdir resolution failed".to_owned())?;
        if !state.starts_with(&root) {
            return Err("--state-file must live under --implement-tmpdir for teardown".to_owned());
        }
    }
    if phase == FinalizePhase::Postmerge {
        let bail = arguments
            .bail_file
            .as_ref()
            .ok_or_else(|| "--final-bail-reason-file is required".to_owned())?;
        if !allowed_finalize_path(bail) {
            return Err(format!("--final-bail-reason-file {PATH_ERROR}"));
        }
    }
    if phase == FinalizePhase::Postbump {
        require_keys(data, POSTBUMP_REQUIRED)?;
        require_bools(data, &["FORKED_TARGET", "REPO_UNAVAILABLE"])?;
        let bump = data
            .get("BUMP_TYPE")
            .map(String::as_str)
            .unwrap_or_default();
        if !["MAJOR", "MINOR", "PATCH", "NONE"].contains(&bump) {
            return Err(
                "state-file key BUMP_TYPE must be one of MAJOR, MINOR, PATCH, NONE".to_owned(),
            );
        }
        let branch = data
            .get("BRANCH_NAME")
            .map(String::as_str)
            .unwrap_or_default();
        if branch.is_empty() {
            return Err("state-file key BRANCH_NAME must be non-empty for postbump".to_owned());
        }
        if ["main", "master"].contains(&branch)
            && data.get("FORKED_TARGET").map(String::as_str) != Some("true")
        {
            return Err("state-file key BRANCH_NAME must not be main or master".to_owned());
        }
        let version = data
            .get("NEW_VERSION")
            .map(String::as_str)
            .unwrap_or_default();
        if bump != "NONE" && version.is_empty() {
            return Err(
                "state-file key NEW_VERSION must be non-empty when BUMP_TYPE is not NONE"
                    .to_owned(),
            );
        }
        if bump != "NONE" && !semver_triplet(version) {
            return Err(
                "state-file key NEW_VERSION must be semver when BUMP_TYPE is not NONE".to_owned(),
            );
        }
    } else {
        require_keys(data, COMMON_REQUIRED)?;
        require_bools(data, COMMON_BOOLS)?;
    }
    Ok(())
}

fn load_state_checked(path: &Path) -> Result<BTreeMap<String, String>, String> {
    if !allowed_finalize_path(path) {
        return Err(format!("--state-file {PATH_ERROR}"));
    }
    if !path.is_file() {
        return Err("--state-file must exist and be readable".to_owned());
    }
    let bytes = fs::read(path).map_err(|_| "--state-file must exist and be readable".to_owned())?;
    let text = String::from_utf8_lossy(&bytes);
    let document = KvDocument::parse(
        &text,
        ParseOptions {
            duplicates: DuplicateInputPolicy::Allow,
            ..ParseOptions::environment()
        },
    )
    .map_err(|error| format!("malformed state-file line {}", error.line()))?;
    let mut data = BTreeMap::new();
    for row in document.rows() {
        if data
            .insert(row.key().to_owned(), row.value().to_owned())
            .is_some()
        {
            return Err(format!("duplicate state-file key: {}", row.key()));
        }
    }
    Ok(data)
}

fn load_state_lenient(path: &Path) -> BTreeMap<String, String> {
    let Ok(bytes) = fs::read(path) else {
        return BTreeMap::new();
    };
    let Ok(document) = KvDocument::parse(&String::from_utf8_lossy(&bytes), ParseOptions::legacy())
    else {
        return BTreeMap::new();
    };
    let rows = document
        .rows()
        .iter()
        .filter(|row| KvRow::new(row.key(), "", KeyPolicy::Environment).is_ok())
        .cloned()
        .collect();
    KvDocument::from_rows(rows).select(DuplicatePolicy::Last)
}

fn require_keys(data: &BTreeMap<String, String>, keys: &[&str]) -> Result<(), String> {
    for key in keys {
        if !data.contains_key(*key) {
            return Err(format!("state-file missing required key: {key}"));
        }
    }
    Ok(())
}

fn require_bools(data: &BTreeMap<String, String>, keys: &[&str]) -> Result<(), String> {
    for key in keys {
        if !matches!(data.get(*key).map(String::as_str), Some("true" | "false")) {
            return Err(format!("state-file key {key} must be true or false"));
        }
    }
    Ok(())
}

fn postbump(context: &Context) -> FinalizeResult {
    let Ok(root) = env::current_dir() else {
        return postbump_failure("postbump-cwd-not-repo", "cwd is not in a repo");
    };
    let Ok(repository) = GixRepository::discover(&root) else {
        return postbump_failure("postbump-cwd-not-repo", "cwd is not in a repo");
    };
    let branch = crate::push_network::current_branch_from(&root).unwrap_or_default();
    if branch.is_empty() || (!context.branch.is_empty() && branch != context.branch) {
        return postbump_failure("branch-mismatch", "wrong branch");
    }
    if ["main", "master"].contains(&branch.as_str()) && !context.forked {
        return postbump_failure("branch-mismatch", "protected branch");
    }
    if checkpoint_status(&context.tmpdir) != "ok" {
        return postbump_failure("postbump-state-corrupt", "postbump checkpoint corrupt");
    }
    let git = match Git::new(&root) {
        Ok(git) => git,
        Err(error) => return postbump_failure("rebase-failed", &error),
    };
    let base_remote = if context.forked { "upstream" } else { "origin" };
    let base = format!("{base_remote}/main");
    if !retry_git(|| git.fetch(base_remote, "main")).ok {
        return rebase_failure(&[]);
    }
    let fresh = crate::release_common::is_ancestor(&repository, &base, "HEAD").unwrap_or(false);
    let rebase_status = if fresh {
        "already-fresh"
    } else if git.rebase(&base).ok {
        "rebased"
    } else {
        let conflicts = repository
            .local_status(&StatusOptions::default())
            .map(|status| crate::push_rebase::sorted_lossy_unmerged_paths(&status))
            .unwrap_or_default();
        if crate::push_rebase::rebase_in_progress() {
            let _ = git.rebase_abort();
        }
        return rebase_failure(&conflicts);
    };
    if context.repo_unavailable {
        let mut result = FinalizeResult::new("OK", "ok");
        rebase_status.clone_into(&mut result.rebase_status);
        "skipped-repo-unavailable".clone_into(&mut result.force_push_status);
        "skipped".clone_into(&mut result.log_write_status);
        return result;
    }
    let remote = retry_git(|| git.ls_remote("origin", &branch, true));
    if remote.code == 2 {
        return postbump_success(rebase_status, "absent");
    }
    if !remote.ok {
        return postbump_remote_failure(rebase_status, "remote branch probe failed");
    }
    let mut remote_tip = remote
        .stdout
        .split_whitespace()
        .next()
        .unwrap_or_default()
        .to_owned();
    if remote_tip.is_empty() {
        remote_tip = repository
            .resolve_revision(&Revision::new(format!("origin/{branch}").as_bytes()))
            .ok()
            .map(|oid| oid.to_hex())
            .unwrap_or_default();
    }
    if remote_tip.is_empty() {
        return postbump_remote_failure(rebase_status, "remote branch OID unavailable");
    }
    let push = crate::push_network::force_recovery(Some(&branch), Some(&remote_tip));
    if push.pushed && ["pushed", "noop_same_ref"].contains(&push.status) {
        postbump_success(rebase_status, push.status)
    } else {
        let mut result = FinalizeResult::new("STALLED", "push-failed");
        push.status.clone_into(&mut result.detail);
        rebase_status.clone_into(&mut result.rebase_status);
        "failed".clone_into(&mut result.force_push_status);
        "skipped".clone_into(&mut result.log_write_status);
        result
    }
}

fn postmerge(context: &Context, stderr: &mut String) -> FinalizeResult {
    for (condition, status) in [
        (context.draft, "skipped-draft"),
        (!context.merge, "skipped-merge-false"),
        (!context.final_bail_reason.is_empty(), "skipped-bail"),
    ] {
        if condition {
            let mut result = FinalizeResult::new("OK", status);
            status.clone_into(&mut result.local_cleanup_status);
            "skipped".clone_into(&mut result.verify_main_status);
            return result;
        }
    }
    if context.branch.is_empty() || context.branch == "main" {
        let mut result = FinalizeResult::new("STALLED", "branch-invalid");
        "invalid branch".clone_into(&mut result.detail);
        return result;
    }
    let Ok(root) = env::current_dir() else {
        return local_cleanup_failure(context);
    };
    let Ok(git) = Git::new(&root) else {
        return local_cleanup_failure(context);
    };
    let checkout = git.checkout("main");
    if !checkout.ok {
        return local_cleanup_failure(context);
    }
    let _ = retry_git(|| git.fetch("origin", "main"));
    if !retry_git(|| git.pull_main()).ok {
        let ahead = crate::session_closeout_commands::ahead_of_origin(&root);
        if ahead > 0 {
            let _ = writeln!(
                stderr,
                "local cleanup: pull failed; local main is ahead of origin/main by {ahead} commit(s)"
            );
        }
        return local_cleanup_failure(context);
    }
    let branch_ref = GitRef::new(&context.branch);
    if branch_ref.is_err() {
        return local_cleanup_failure(context);
    }
    let reference = format!("refs/heads/{}", context.branch);
    let exists = GixRepository::discover(&root)
        .map_err(|error| error.to_string())
        .and_then(|repository| repository.references().map_err(|error| error.to_string()))
        .map(|rows| {
            rows.iter()
                .any(|row| row.name.as_bytes() == reference.as_bytes())
        });
    let Ok(exists) = exists else {
        return local_cleanup_failure(context);
    };
    let deleted = if exists {
        git.delete_branch(branch_ref.unwrap_or_else(|_| unreachable!()))
            .ok
    } else {
        false
    };
    if exists && !deleted {
        return local_cleanup_failure(context);
    }
    let actual = GixRepository::discover(&root)
        .ok()
        .and_then(|repository| {
            let head = repository.resolve_revision(&Revision::new(b"HEAD")).ok()?;
            Some(crate::ship_pr_commands::head_subject(&repository, &head))
        })
        .unwrap_or_default();
    let mut result = FinalizeResult::new("OK", "ok");
    "success".clone_into(&mut result.local_cleanup_status);
    if title_matches(&actual, &context.pr_title, context.pr_number) {
        "verified"
    } else {
        "unexpected"
    }
    .clone_into(&mut result.verify_main_status);
    result
}

fn teardown(context: &Context, stderr: &mut String) -> Result<FinalizeResult, String> {
    let repo_root = match persisted_repo_root(&context.tmpdir) {
        Some(root) => root,
        None if has_persisted_coverage(&context.tmpdir)? => {
            return Err(
                "persisted repository root is required for teardown coverage validation".to_owned(),
            );
        }
        None => env::current_dir()
            .ok()
            .and_then(|path| path.canonicalize().ok())
            .unwrap_or_else(|| PathBuf::from(".")),
    };
    let mut rename_branch = "C".to_owned();
    let mut rename_status = "skipped".to_owned();
    if context.stall_tracking {
        "A".clone_into(&mut rename_branch);
        rename_status = rename_issue(context, "stalled");
    } else if !context.done_rename_applied
        && (context.pr_number.is_some() || context.design_only_done)
    {
        let disposition = teardown_disposition(
            &context.tmpdir,
            &repo_root,
            context.manifest.as_deref(),
            context.tmpdir.join("post-merge-sentinel").is_file(),
        )?;
        if disposition.recovered_stale_live {
            let _ = writeln!(
                stderr,
                "teardown: live coverage no longer matches repository inputs; using validated persisted disposition"
            );
        }
        if !disposition.partial {
            "B".clone_into(&mut rename_branch);
            rename_status = rename_issue(context, "done");
        }
    }
    let sentinel_detail =
        private_atomic_write(&context.tmpdir.join(".run-cleaned-up"), "", &context.tmpdir)
            .err()
            .map(|error| format!("run-cleaned-up sentinel write failed: {error}"))
            .unwrap_or_default();
    if !sentinel_detail.is_empty() {
        let _ = writeln!(stderr, "teardown: {sentinel_detail}");
    }
    let host = SystemProcessIdentityHost::new();
    if !context.run_id.is_empty()
        && validate_progress_run_id(&context.run_id).is_some()
        && !has_live_entry(&host, &repo_root, &context.run_id)
    {
        let cache = progress_cache_home(
            env::var_os("LARCH_TEST_CACHE_HOME").as_deref(),
            env::var_os("XDG_CACHE_HOME").as_deref(),
            env::var_os("HOME").as_deref(),
        );
        let _ = deactivate_run(&progress_paths(&cache, &repo_root), &context.run_id);
    }
    let issue_url = issue_info(context).map_or_else(|_| String::new(), |issue| issue.url);
    if context.stall_tracking {
        let stash_ref = auto_stash(&repo_root, context);
        let sentinel_written = write_stalled_sentinel(&repo_root, context, &stash_ref)?;
        let mut result = FinalizeResult::new("OK", "stalled-preserved");
        result.detail = sentinel_detail;
        result.rename_branch = rename_branch;
        result.rename_status = rename_status;
        result.sentinel_written = sentinel_written;
        result.stash_ref = stash_ref;
        result.issue_url = issue_url;
        return Ok(result);
    }
    let removed = if context.tmpdir.exists() && cleanup_target_ok(context, &context.tmpdir) {
        let _ = kill_session_background_processes(&host, &context.tmpdir.to_string_lossy());
        let _ = remove_session_tmpdir(&context.tmpdir);
        !context.tmpdir.exists()
    } else {
        false
    };
    let mut result = FinalizeResult::new(
        "OK",
        if removed {
            "cleaned"
        } else {
            "cleanup-skipped"
        },
    );
    result.detail = sentinel_detail;
    result.rename_branch = rename_branch;
    result.rename_status = rename_status;
    result.issue_url = issue_url;
    Ok(result)
}

fn rename_issue(context: &Context, state: &str) -> String {
    if context.issue.is_empty() || context.repo_unavailable {
        return "skipped".to_owned();
    }
    if state == "stalled" {
        let Ok(issue) = issue_info(context) else {
            return "failed".to_owned();
        };
        if issue.state != GitHubIssueState::Open {
            return "skipped".to_owned();
        }
    }
    rename_finalize_live(
        &context.issue,
        state,
        nonempty_ref(&context.repo),
        &context.run_id,
    )
    .map_or_else(|_| "failed".to_owned(), |_| "ok".to_owned())
}

fn issue_info(context: &Context) -> Result<larch_core::GitHubIssue, String> {
    if context.issue.is_empty() || context.repo_unavailable {
        return Err("issue lookup skipped".to_owned());
    }
    read_issue_live(nonempty_ref(&context.repo), &context.issue)
}

fn auto_stash(repo_root: &Path, context: &Context) -> String {
    let Ok(repository) = GixRepository::discover(repo_root) else {
        return "git-status-failed".to_owned();
    };
    let Ok(status) = repository.local_status(&StatusOptions::default()) else {
        return "git-status-failed".to_owned();
    };
    if !status.is_dirty() {
        return String::new();
    }
    let label = format!(
        "larch-stalled-{}-{}-{}",
        if context.issue.is_empty() {
            "unknown"
        } else {
            &context.issue
        },
        if context.stall_step.is_empty() {
            "unknown"
        } else {
            &context.stall_step
        },
        Utc::now().format("%Y%m%dT%H%M%SZ")
    );
    let Ok(git) = Git::new(repo_root) else {
        return "git-stash-failed".to_owned();
    };
    if !git.stash_push(&label).ok {
        return "git-stash-failed".to_owned();
    }
    let listed = git.stash_list();
    if !listed.ok {
        return "git-stash-list-failed".to_owned();
    }
    listed
        .stdout
        .lines()
        .find(|line| line.contains(&label))
        .and_then(|line| line.split_whitespace().next())
        .unwrap_or_default()
        .to_owned()
}

fn write_stalled_sentinel(
    repo_root: &Path,
    context: &Context,
    stash_ref: &str,
) -> Result<bool, String> {
    let Ok(repository) = GixRepository::discover(repo_root) else {
        return Ok(false);
    };
    let location = repository.location();
    let mut git_dir =
        PathBuf::from(String::from_utf8_lossy(location.git_dir.as_bytes()).into_owned());
    if git_dir.is_relative() {
        git_dir = repo_root.join(git_dir);
    }
    let issue_url = if context.issue.is_empty() || context.repo.is_empty() {
        String::new()
    } else {
        format!(
            "https://github.com/{}/issues/{}",
            context.repo, context.issue
        )
    };
    for (key, value) in [
        ("ISSUE_NUMBER", context.issue.as_str()),
        ("ISSUE_URL", issue_url.as_str()),
        ("STALL_STEP", context.stall_step.as_str()),
        ("STASH_REF", stash_ref),
    ] {
        if value.contains(['\n', '\r']) {
            return Err(format!(
                "stalled sentinel value for {key} contains a newline"
            ));
        }
    }
    let contents = format!(
        "ISSUE_NUMBER={}\nISSUE_URL={}\nSTALL_STEP={}\nSTASH_REF={}\nTIMESTAMP={}\n",
        context.issue,
        issue_url,
        if context.stall_step.is_empty() {
            "unknown"
        } else {
            &context.stall_step
        },
        stash_ref,
        Utc::now().to_rfc3339_opts(SecondsFormat::AutoSi, false),
    );
    private_atomic_write(&git_dir.join("larch-stalled-run.txt"), &contents, &git_dir)
        .map(|()| true)
        .map_err(|error| error.to_string())
}

fn cleanup_target_ok(context: &Context, tmpdir: &Path) -> bool {
    if tmpdir.components().any(|part| part == Component::ParentDir) {
        return false;
    }
    let Ok(resolved) = resolve_allow_missing(tmpdir) else {
        return false;
    };
    if !writer_target_allowed(&resolved, &session_roots()) {
        return false;
    }
    let prefix = if context.expected_tmpdir_prefix.is_empty() {
        let repo = env::current_dir()
            .ok()
            .and_then(|path| path.canonicalize().ok())
            .and_then(|path| path.file_name().map(OsStr::to_os_string))
            .unwrap_or_else(|| OsString::from("_"));
        format!(
            "claude-implement-{}-",
            repo.to_string_lossy().chars().take(32).collect::<String>()
        )
    } else {
        context.expected_tmpdir_prefix.clone()
    };
    let prefix_matches = tmpdir
        .file_name()
        .is_some_and(|name| name.to_string_lossy().starts_with(&prefix));
    if !prefix_matches || !context.expected_session_id.is_empty() {
        if context.expected_session_id.is_empty() {
            return false;
        }
        let session = resolved.join("session-id");
        let Ok(metadata) = fs::symlink_metadata(&session) else {
            return false;
        };
        if !metadata.file_type().is_file() || metadata.file_type().is_symlink() {
            return false;
        }
        return fs::read_to_string(session)
            .is_ok_and(|value| value.trim() == context.expected_session_id);
    }
    true
}

fn allowed_finalize_path(path: &Path) -> bool {
    writer_target_allowed(path, &session_roots())
}

fn session_roots() -> Vec<PathBuf> {
    let xdg = env::var_os("XDG_CACHE_HOME").filter(|value| Path::new(value).is_absolute());
    allowed_session_roots(xdg.as_deref(), env::var_os("HOME").as_deref()).to_vec()
}

fn checkpoint_status(tmpdir: &Path) -> &'static str {
    let path = tmpdir.join(".postbump-phase");
    if !path.exists() {
        return "ok";
    }
    let Ok(metadata) = fs::symlink_metadata(&path) else {
        return "corrupt";
    };
    if metadata.file_type().is_symlink() || metadata.len() > CHECKPOINT_MAX_BYTES {
        return "corrupt";
    }
    let Ok(text) = fs::read_to_string(&path) else {
        return "corrupt";
    };
    let text = text.replace('\r', "");
    let text = text.trim();
    if text.is_empty()
        || !text.chars().next().is_some_and(char::is_lowercase)
        || !text
            .chars()
            .all(|character| character.is_lowercase() || character.is_numeric() || character == '-')
    {
        return "corrupt";
    }
    if fs::remove_file(path).is_ok() {
        "ok"
    } else {
        "corrupt"
    }
}

struct GitOutcome {
    ok: bool,
    code: i32,
    stdout: String,
    stderr: String,
}

impl GitOutcome {
    fn error(message: impl Into<String>) -> Self {
        Self {
            ok: false,
            code: 1,
            stdout: String::new(),
            stderr: message.into(),
        }
    }
}

fn git_outcome(result: Result<GitCliResult, GitCliError>) -> GitOutcome {
    match result {
        Ok(value) => output_outcome(true, value.output()),
        Err(GitCliError::Failed(value)) => output_outcome(false, value.output()),
        Err(GitCliError::Process(error)) => error.output().map_or_else(
            || GitOutcome::error("Git process failed"),
            |output| output_outcome(false, output),
        ),
        Err(error) => GitOutcome::error(error.to_string()),
    }
}

fn output_outcome(ok: bool, output: &ProcessOutput) -> GitOutcome {
    let (code, stdout, stderr) = output.decoded_streams();
    GitOutcome {
        ok,
        code,
        stdout,
        stderr,
    }
}

struct Git {
    runtime: GitCommandRuntime,
}

macro_rules! git_input {
    ($value:expr) => {
        match $value {
            Ok(value) => value,
            Err(error) => return GitOutcome::error(error.to_string()),
        }
    };
}

macro_rules! git_call {
    ($owner:expr, $future:expr) => {
        git_outcome($owner.runtime.runtime.block_on($future))
    };
}

impl Git {
    fn new(root: &Path) -> Result<Self, String> {
        GitCommandRuntime::for_repository(root).map(|runtime| Self { runtime })
    }

    fn fetch(&self, remote: &str, reference: &str) -> GitOutcome {
        let request = FetchRequest {
            remote: git_input!(GitRemote::new(remote)),
            refspec: Some(git_input!(GitRefspec::new(reference))),
            quiet: true,
            no_tags: false,
        };
        git_call!(
            self,
            self.runtime
                .git_cli()
                .fetch(request, &self.runtime.cancellation)
        )
    }

    fn rebase(&self, upstream: &str) -> GitOutcome {
        let request = RebaseRequest::Start {
            onto: None,
            upstream: git_input!(GitRef::new(upstream)),
            branch: None,
        };
        git_call!(
            self,
            self.runtime
                .git_cli()
                .rebase(request, &self.runtime.cancellation)
        )
    }

    fn rebase_abort(&self) -> GitOutcome {
        git_call!(
            self,
            self.runtime
                .git_cli()
                .rebase(RebaseRequest::Abort, &self.runtime.cancellation)
        )
    }

    fn checkout(&self, branch: &str) -> GitOutcome {
        let request = CheckoutRequest::Branch {
            create: false,
            force: false,
            no_track: false,
            name: git_input!(GitRef::new(branch)),
            start_point: None,
        };
        git_call!(
            self,
            self.runtime
                .git_cli()
                .checkout(request, &self.runtime.cancellation)
        )
    }

    fn pull_main(&self) -> GitOutcome {
        git_call!(
            self,
            self.runtime.git_cli().pull(
                PullRequest {
                    remote: git_input!(GitRemote::new("origin")),
                    refspec: Some(git_input!(GitRefspec::new("main"))),
                    fast_forward_only: true,
                },
                &self.runtime.cancellation,
            )
        )
    }

    fn delete_branch(&self, name: GitRef) -> GitOutcome {
        git_call!(
            self,
            self.runtime.git_cli().branch_mutation(
                BranchMutationRequest::Delete { force: true, name },
                &self.runtime.cancellation,
            )
        )
    }

    fn ls_remote(&self, remote: &str, branch: &str, exit_code: bool) -> GitOutcome {
        let request = LsRemoteRequest {
            remote: git_input!(GitRemote::new(remote)),
            patterns: vec![git_input!(GitRef::new(branch))],
            heads: true,
            exit_code,
        };
        git_call!(
            self,
            self.runtime
                .git_cli()
                .ls_remote(request, &self.runtime.cancellation)
        )
    }

    fn stash_push(&self, message: &str) -> GitOutcome {
        git_call!(
            self,
            self.runtime.git_cli().stash(
                StashRequest::Push {
                    message: Some(message.into()),
                    include_untracked: true,
                },
                &self.runtime.cancellation,
            )
        )
    }

    fn stash_list(&self) -> GitOutcome {
        git_call!(
            self,
            self.runtime
                .git_cli()
                .stash(StashRequest::List, &self.runtime.cancellation)
        )
    }
}

fn retry_git(mut operation: impl FnMut() -> GitOutcome) -> GitOutcome {
    let mut result = operation();
    let mut attempt = 1_u32;
    while !result.ok
        && is_transient_net(&format!("{}{}", result.stdout, result.stderr))
        && sleep_before_retry(attempt)
    {
        result = operation();
        attempt += 1;
    }
    result
}

fn title_matches(actual: &str, expected: &str, pr_number: Option<u64>) -> bool {
    let normalized = strip_pr_suffix(expected);
    if normalized.is_empty() {
        return false;
    }
    let suffix_number = pr_number.map(|value| value.to_string()).unwrap_or_default();
    let numbered = if suffix_number.is_empty() {
        normalized.to_owned()
    } else {
        format!("{normalized} (#{suffix_number})")
    };
    actual == expected
        || actual == numbered
        || actual.starts_with(&numbered)
        || (!suffix_number.is_empty() && actual.contains(&format!("(#{suffix_number})")))
}

fn strip_pr_suffix(value: &str) -> &str {
    let Some(open) = value.rfind("(#") else {
        return value;
    };
    if open == 0
        || !value[..open]
            .chars()
            .last()
            .is_some_and(char::is_whitespace)
    {
        return value;
    }
    let Some(number) = value.get(open + 2..value.len().saturating_sub(1)) else {
        return value;
    };
    if value.ends_with(')')
        && !number.is_empty()
        && number.bytes().all(|byte| byte.is_ascii_digit())
    {
        value[..open].trim_end()
    } else {
        value
    }
}

fn postbump_failure(status: &str, detail: &str) -> FinalizeResult {
    postbump_result("STALLED", status, detail, "skipped-resume", "absent")
}

fn rebase_failure(conflicts: &[String]) -> FinalizeResult {
    let mut result = FinalizeResult::new("STALLED", "rebase-failed");
    result.detail = if conflicts.is_empty() {
        "rebase failed".to_owned()
    } else {
        format!("rebase failed; conflicts in: {}", conflicts.join(", "))
    };
    "failed".clone_into(&mut result.rebase_status);
    "absent".clone_into(&mut result.force_push_status);
    "skipped".clone_into(&mut result.log_write_status);
    result.conflict_files = conflicts.join(",");
    result
}

fn postbump_remote_failure(rebase: &str, detail: &str) -> FinalizeResult {
    postbump_result("STALLED", "remote-check-failed", detail, rebase, "failed")
}

fn postbump_success(rebase: &str, push: &str) -> FinalizeResult {
    postbump_result("OK", "ok", "", rebase, push)
}

fn postbump_result(
    outcome: &'static str,
    status: &str,
    detail: &str,
    rebase: &str,
    push: &str,
) -> FinalizeResult {
    let mut result = FinalizeResult::new(outcome, status);
    detail.clone_into(&mut result.detail);
    rebase.clone_into(&mut result.rebase_status);
    push.clone_into(&mut result.force_push_status);
    "skipped".clone_into(&mut result.log_write_status);
    result
}

fn local_cleanup_failure(context: &Context) -> FinalizeResult {
    let mut result = FinalizeResult::new("STALLED", "local-cleanup-failed");
    result.detail = format!("failed to delete local branch {}", context.branch);
    "partial".clone_into(&mut result.local_cleanup_status);
    result
}

fn semver_triplet(value: &str) -> bool {
    let parts = value.split('.').collect::<Vec<_>>();
    parts.len() == 3
        && parts
            .iter()
            .all(|part| !part.is_empty() && part.bytes().all(|byte| byte.is_ascii_digit()))
}

fn bool_value(value: &str) -> bool {
    matches!(
        value.trim().to_ascii_lowercase().as_str(),
        "1" | "true" | "yes" | "on"
    )
}

fn nonempty(value: String) -> Option<String> {
    (!value.is_empty()).then_some(value)
}

fn nonempty_ref(value: &str) -> Option<&str> {
    (!value.is_empty()).then_some(value)
}

fn safe_line(value: &str) -> String {
    value.replace(['\n', '\r'], " ")
}
