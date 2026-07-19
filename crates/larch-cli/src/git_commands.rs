//! Shared Git branch and ref-read commands migrated from Python.

use std::{
    env,
    ffi::OsString,
    fs,
    io::{self, Write},
    path::{Path, PathBuf},
    process::ExitCode,
    sync::Arc,
    thread,
    time::Duration,
};

use larch_adapters::{
    AddRequest, BranchMutationRequest, CommitMessage, CommitRequest, ExactDiffRequest, GitCli,
    GitCliError, GitCliPolicy, GitCliResult, GitFilePath, GitPath, GitRef, GitRemote,
    GixRepository, InterpretTrailersRequest, LsRemoteRequest, NoopProcessObserver,
    OpenFileHolderStatus, ResetMode, ResetRequest, TokioProcessRunner, probe_open_file_holder,
    runtime::Cancellation, runtime::LarchRuntime,
};
use larch_core::{
    GIT_COMMIT_CO_AUTHORED_BY_TRAILER, Head, ObjectId, ProcessErrorKind, RefName, RepositoryRead,
    Revision, SafeText, StatusOptions, emit_kv,
};

const CURRENT_BRANCH_DETACHED: &str =
    "git-current-branch.sh: not on a named branch (detached HEAD or not a git repo)";
const COUNT_MISSING_MAIN: &str = "WARN: lib-count-commits.sh: neither local 'main' nor 'origin/main' exists; cannot determine commit base. Returning 0.";
const TRANSIENT_ATTEMPTS: u32 = 3;
const TRANSIENT_BACKOFF_SECS: [u64; 2] = [2, 4];
const FLUSH_COMMIT_SUBJECT_PREFIX: &[u8] = b"chore(larch-logs): flush ";

#[derive(Debug)]
pub enum GitCommand {
    AmendAdd {
        paths: Vec<PathBuf>,
    },
    BranchInfo {
        args: Vec<String>,
    },
    CheckMainSync {
        args: Vec<String>,
    },
    CheckRemoteBranch {
        args: Vec<String>,
    },
    CountCommits {
        args: Vec<String>,
    },
    CurrentBranch {
        args: Vec<String>,
    },
    Commit {
        message: String,
        no_trailer: bool,
        only: bool,
        pathspec_from_file: Option<PathBuf>,
        pathspec_file_nul: bool,
        paths: Vec<PathBuf>,
    },
    ShowStage {
        args: Vec<String>,
    },
    Stage {
        paths: Vec<PathBuf>,
    },
    SyncLocalMain {
        args: Vec<String>,
    },
}

pub fn run(command: GitCommand) -> ExitCode {
    let code = match command {
        GitCommand::AmendAdd { paths } => amend_add(&paths),
        GitCommand::BranchInfo { args } => branch_info(&args),
        GitCommand::CheckRemoteBranch { args } => check_remote_branch(&args),
        GitCommand::CountCommits { args } => count_commits(&args),
        GitCommand::CurrentBranch { args } => current_branch(&args),
        GitCommand::CheckMainSync { args } => check_main_sync(&args),
        GitCommand::Commit {
            message,
            no_trailer,
            only,
            pathspec_from_file,
            pathspec_file_nul,
            paths,
        } => commit(
            &message,
            no_trailer,
            only,
            pathspec_from_file.as_deref(),
            pathspec_file_nul,
            &paths,
        ),
        GitCommand::ShowStage { args } => show_stage(&args),
        GitCommand::Stage { paths } => stage(&paths),
        GitCommand::SyncLocalMain { args } => sync_local_main(&args),
    };
    ExitCode::from(code)
}

fn check_main_sync(args: &[String]) -> u8 {
    if let Some(arg) = args.first() {
        let _ = writeln!(io::stderr(), "check-main-sync.sh: unknown flag: {arg}");
        return 2;
    }
    let Some(repo) = open_cwd_repository() else {
        emit_main_sync(
            "probe-error",
            None,
            Some("git rev-list failed or produced empty output (exit 128)"),
        );
        return 2;
    };
    let Ok(head) = repo.head() else {
        emit_main_sync(
            "probe-error",
            None,
            Some("git rev-list failed or produced empty output (exit 128)"),
        );
        return 2;
    };
    let Head::Symbolic { name, .. } = head else {
        emit_main_sync("not-main", None, None);
        return 0;
    };
    if short_branch_name(&name).as_deref() != Some("main") {
        emit_main_sync("not-main", None, None);
        return 0;
    }
    let Some(origin_main) = resolve_optional(&repo, "origin/main") else {
        emit_main_sync(
            "probe-error",
            None,
            Some("git rev-list failed or produced empty output (exit 128)"),
        );
        return 2;
    };
    let Some(current) = resolve_optional(&repo, "HEAD") else {
        emit_main_sync(
            "probe-error",
            None,
            Some("git rev-list failed or produced empty output (exit 128)"),
        );
        return 2;
    };
    let Ok(ahead) = repo.commit_count_range(&origin_main, &current) else {
        emit_main_sync(
            "probe-error",
            None,
            Some("git rev-list failed or produced empty output (exit 128)"),
        );
        return 2;
    };
    if ahead == 0 {
        emit_main_sync("ok", Some(ahead), None);
        return 0;
    }
    check_main_sync_ahead(&repo, &origin_main, &current, ahead)
}

fn check_main_sync_ahead(
    repo: &GixRepository,
    origin_main: &ObjectId,
    current: &ObjectId,
    ahead: u64,
) -> u8 {
    let Ok(subjects) = repo.commit_subjects_range(origin_main, current) else {
        emit_main_sync(
            "probe-error",
            Some(ahead),
            Some("git log failed (exit 128)"),
        );
        return 2;
    };
    if subjects.len() as u64 != ahead {
        emit_main_sync(
            "probe-error",
            Some(ahead),
            Some(&format!(
                "git log subject line count ({}) does not match AHEAD ({ahead})",
                subjects.len()
            )),
        );
        return 2;
    }
    let Ok(paths) = exact_diff_paths("origin/main", "HEAD") else {
        emit_main_sync(
            "probe-error",
            Some(ahead),
            Some("git diff --name-only failed (exit 128)"),
        );
        return 2;
    };
    let all_flushes = subjects
        .iter()
        .all(|subject| subject.starts_with(FLUSH_COMMIT_SUBJECT_PREFIX));
    let logs_only = paths.is_empty() || paths.iter().all(|path| path.starts_with(b"larch-logs/"));
    if all_flushes && logs_only {
        if repo
            .local_status(&StatusOptions::default())
            .map_or(true, |status| status.is_dirty())
        {
            emit_main_sync(
                "probe-error",
                Some(ahead),
                Some(
                    "refusing reset: working tree is not clean (tracked or untracked changes present)",
                ),
            );
            return 2;
        }
        if reset_hard("origin/main").is_err() {
            emit_main_sync(
                "probe-error",
                Some(ahead),
                Some("git reset --hard origin/main failed (exit 128)"),
            );
            return 2;
        }
        emit_main_sync("reset", Some(ahead), None);
        return 0;
    }
    emit_main_sync(
        "blocked",
        Some(ahead),
        Some(&format!(
            "local main is {ahead} commit(s) ahead of origin/main with non-log changes; push or reconcile before re-running"
        )),
    );
    1
}

fn emit_main_sync(status: &str, ahead: Option<u64>, error: Option<&str>) {
    emit_kv("SYNC_STATUS", status);
    if let Some(ahead) = ahead {
        emit_kv("AHEAD_COUNT", &ahead.to_string());
    }
    if let Some(error) = error {
        emit_kv("ERROR", error);
    }
}

fn sync_local_main(args: &[String]) -> u8 {
    let (base_remote, base_ref) = match parse_sync_local_main_args(args) {
        Ok(values) => values,
        Err(message) => {
            let _ = writeln!(io::stderr(), "cli.py git sync-local-main: {message}");
            return 1;
        }
    };
    let Some(repo) = open_cwd_repository() else {
        emit_kv("RESULT", "absent");
        return 0;
    };
    if matches!(repo.head(), Ok(Head::Symbolic { name, .. }) if short_branch_name(&name).as_deref() == Some("main"))
    {
        let _ = writeln!(
            io::stderr(),
            "cli.py git sync-local-main: refusing to update local 'main' while checked out on main"
        );
        return 1;
    }
    let Some(local_main) = resolve_optional(&repo, "main") else {
        emit_kv("RESULT", "absent");
        return 0;
    };
    let target = format!("{base_remote}/{base_ref}");
    if resolve_optional(&repo, &target).is_some_and(|remote_main| remote_main == local_main) {
        emit_kv("RESULT", "already_current");
        return 0;
    }
    if force_branch_main(&target).is_err() {
        let _ = writeln!(io::stderr(), "cli.py git sync-local-main: failed");
        return 1;
    }
    emit_kv("RESULT", "updated");
    0
}

fn parse_sync_local_main_args(args: &[String]) -> Result<(String, String), &'static str> {
    let mut remote = "origin".to_owned();
    let mut reference = "main".to_owned();
    let mut index = 0;
    while index < args.len() {
        match args[index].as_str() {
            "--base-remote" => {
                remote = args
                    .get(index + 1)
                    .cloned()
                    .ok_or("--base-remote requires a value")?;
                index += 2;
            }
            "--base-ref" => {
                reference = args
                    .get(index + 1)
                    .cloned()
                    .ok_or("--base-ref requires a value")?;
                index += 2;
            }
            _ => return Err("unknown argument"),
        }
    }
    GitRemote::new(&remote).map_err(|_| "invalid --base-remote")?;
    GitRef::new(&reference).map_err(|_| "invalid --base-ref")?;
    Ok((remote, reference))
}

fn exact_diff_paths(base: &str, head: &str) -> Result<Vec<Vec<u8>>, ()> {
    let cwd = env::current_dir().map_err(|_| ())?;
    let policy = GitCliPolicy::new(cwd).map_err(|_| ())?;
    let runtime = LarchRuntime::current_thread().map_err(|_| ())?;
    let runner = TokioProcessRunner::new(Arc::new(NoopProcessObserver));
    let git = GitCli::new(&runner, policy);
    let request = ExactDiffRequest {
        cached: false,
        name_only: true,
        name_status: false,
        quiet: false,
        exit_code: false,
        base: Some(GitRef::new(base).map_err(|_| ())?),
        head: Some(GitRef::new(head).map_err(|_| ())?),
        paths: Vec::new(),
    };
    let output = runtime
        .block_on(git.exact_diff(request, &Cancellation::new()))
        .map_err(|_| ())?;
    Ok(output
        .output()
        .stdout()
        .split(|byte| *byte == b'\n')
        .filter(|path| !path.is_empty())
        .map(<[u8]>::to_vec)
        .collect())
}

fn reset_hard(target: &str) -> Result<(), ()> {
    let cwd = env::current_dir().map_err(|_| ())?;
    let policy = GitCliPolicy::new(cwd).map_err(|_| ())?;
    let runtime = LarchRuntime::current_thread().map_err(|_| ())?;
    let runner = TokioProcessRunner::new(Arc::new(NoopProcessObserver));
    let git = GitCli::new(&runner, policy);
    runtime
        .block_on(git.reset(
            ResetRequest {
                mode: ResetMode::Hard,
                target: GitRef::new(target).map_err(|_| ())?,
                paths: Vec::new(),
            },
            &Cancellation::new(),
        ))
        .map_err(|_| ())?;
    Ok(())
}

fn force_branch_main(target: &str) -> Result<(), ()> {
    let cwd = env::current_dir().map_err(|_| ())?;
    let policy = GitCliPolicy::new(cwd).map_err(|_| ())?;
    let runtime = LarchRuntime::current_thread().map_err(|_| ())?;
    let runner = TokioProcessRunner::new(Arc::new(NoopProcessObserver));
    let git = GitCli::new(&runner, policy);
    runtime
        .block_on(git.branch_mutation(
            BranchMutationRequest::Create {
                force: true,
                name: GitRef::new("main").map_err(|_| ())?,
                start_point: Some(GitRef::new(target).map_err(|_| ())?),
            },
            &Cancellation::new(),
        ))
        .map_err(|_| ())?;
    Ok(())
}

fn stage(paths: &[PathBuf]) -> u8 {
    if paths.is_empty() {
        let _ = writeln!(
            io::stderr(),
            "git-stage.sh: at least one file argument is required"
        );
        let _ = writeln!(io::stderr(), "usage: git-stage.sh <file> [<file> ...]");
        return 1;
    }
    let Some(context) = MutationContext::new() else {
        return 128;
    };
    if !branch_write_allowed(&context.cwd) {
        return 1;
    }
    let Ok(paths) = typed_paths(paths) else {
        return 1;
    };
    let request = AddRequest {
        all: false,
        force: false,
        pathspec_from_file: None,
        pathspec_file_nul: false,
        paths,
    };
    let git = context.git();
    let (result, note) = context.runtime.block_on(run_add_with_retry(
        &git,
        request,
        &context.runner,
        &context.cancellation,
    ));
    render_git_result(result, note.as_deref())
}

fn amend_add(paths: &[PathBuf]) -> u8 {
    if paths.is_empty() {
        let _ = writeln!(
            io::stderr(),
            "git-amend-add.sh: at least one file argument is required"
        );
        let _ = writeln!(io::stderr(), "usage: git-amend-add.sh <file> [<file> ...]");
        return 1;
    }
    let Some(context) = MutationContext::new() else {
        return 128;
    };
    if !branch_write_allowed(&context.cwd) {
        return 1;
    }
    let Ok(paths) = typed_paths(paths) else {
        return 1;
    };
    let add_request = AddRequest {
        all: false,
        force: false,
        pathspec_from_file: None,
        pathspec_file_nul: false,
        paths,
    };
    let git = context.git();
    let (staged, note) = context.runtime.block_on(run_add_with_retry(
        &git,
        add_request,
        &context.runner,
        &context.cancellation,
    ));
    if staged.is_err() {
        return render_git_result(staged, note.as_deref());
    }
    let request = CommitRequest {
        message: None,
        amend: true,
        no_edit: true,
        allow_empty: false,
        only: false,
        pathspec_from_file: None,
        pathspec_file_nul: false,
        paths: Vec::new(),
    };
    let result = context
        .runtime
        .block_on(git.commit(request, &context.cancellation));
    render_git_result(result, None)
}

fn commit(
    message: &str,
    no_trailer: bool,
    only: bool,
    pathspec_from_file: Option<&Path>,
    pathspec_file_nul: bool,
    paths: &[PathBuf],
) -> u8 {
    if message.trim().is_empty() {
        let _ = writeln!(
            io::stderr(),
            "git-commit.sh: commit message must be non-empty"
        );
        return 1;
    }
    let Some(context) = MutationContext::new() else {
        return 128;
    };
    if !branch_write_allowed(&context.cwd) {
        return 1;
    }
    if let LockRemoval::Removed(diagnostic) = context.runtime.block_on(try_remove_stale_index_lock(
        &context.runner,
        &context.cancellation,
        &context.cwd,
    )) {
        let _ = writeln!(io::stderr(), "{diagnostic}");
    }
    let Ok((pathspec, typed)) = commit_paths(pathspec_from_file, paths) else {
        return 1;
    };
    let pathspec_file_nul = pathspec.is_some() && pathspec_file_nul;
    if let Err(code) =
        stage_commit_paths(&context, pathspec.clone(), pathspec_file_nul, typed.clone())
    {
        return code;
    }
    let message_file = match prepare_commit_message(&context, message, no_trailer) {
        Ok(file) => file,
        Err(code) => return code,
    };
    let message_path = match GitFilePath::new(message_file.path().as_os_str().to_owned()) {
        Ok(path) => path,
        Err(error) => {
            let _ = writeln!(io::stderr(), "{error}");
            return 1;
        }
    };
    let request = CommitRequest {
        message: Some(CommitMessage::File(message_path)),
        amend: false,
        no_edit: false,
        allow_empty: false,
        only,
        pathspec_from_file: pathspec,
        pathspec_file_nul,
        paths: typed,
    };
    let git = context.git();
    let (result, note) = context.runtime.block_on(run_commit_with_retry(
        &git,
        request,
        &context.runner,
        &context.cancellation,
    ));
    render_git_result(result, note.as_deref())
}

fn commit_paths(
    pathspec_from_file: Option<&Path>,
    paths: &[PathBuf],
) -> Result<(Option<GitFilePath>, Vec<GitPath>), ()> {
    let pathspec = pathspec_from_file
        .map(|path| GitFilePath::new(path.as_os_str().to_owned()))
        .transpose()
        .map_err(|error| {
            let _ = writeln!(io::stderr(), "{error}");
        })?;
    let paths = if pathspec.is_some() {
        Vec::new()
    } else {
        typed_paths(paths)?
    };
    Ok((pathspec, paths))
}

fn stage_commit_paths(
    context: &MutationContext,
    pathspec: Option<GitFilePath>,
    pathspec_file_nul: bool,
    paths: Vec<GitPath>,
) -> Result<(), u8> {
    if pathspec.is_none() && paths.is_empty() {
        return Ok(());
    }
    let request = AddRequest {
        all: false,
        force: false,
        pathspec_from_file: pathspec,
        pathspec_file_nul,
        paths,
    };
    let git = context.git();
    let (result, note) = context.runtime.block_on(run_add_with_retry(
        &git,
        request,
        &context.runner,
        &context.cancellation,
    ));
    if result.is_err() {
        return Err(render_git_result(result, note.as_deref()));
    }
    Ok(())
}

fn prepare_commit_message(
    context: &MutationContext,
    message: &str,
    no_trailer: bool,
) -> Result<tempfile::NamedTempFile, u8> {
    let mut file = tempfile::Builder::new()
        .prefix("larch-commit-")
        .suffix(".txt")
        .tempfile()
        .map_err(|error| {
            let _ = writeln!(
                io::stderr(),
                "git-commit.sh: temporary message file failed: {error}"
            );
            1
        })?;
    writeln!(file, "{message}").map_err(|error| {
        let _ = writeln!(
            io::stderr(),
            "git-commit.sh: temporary message write failed: {error}"
        );
        1
    })?;
    if no_trailer {
        return Ok(file);
    }
    let path = GitFilePath::new(file.path().as_os_str().to_owned()).map_err(|error| {
        let _ = writeln!(io::stderr(), "{error}");
        1
    })?;
    let request = InterpretTrailersRequest {
        trailers: vec![OsString::from(GIT_COMMIT_CO_AUTHORED_BY_TRAILER)],
        in_place: Some(path),
        add_if_different: true,
        add_if_missing: true,
        stdin: Vec::new(),
    };
    let git = context.git();
    let result = context
        .runtime
        .block_on(git.interpret_trailers(request, &context.cancellation));
    if result.is_err() {
        return Err(render_git_result(result, None));
    }
    Ok(file)
}

struct MutationContext {
    runtime: LarchRuntime,
    runner: TokioProcessRunner,
    cancellation: Cancellation,
    cwd: PathBuf,
}

impl MutationContext {
    fn new() -> Option<Self> {
        let cwd = env::current_dir().ok()?;
        let _ = GitCliPolicy::new(cwd.clone()).ok()?;
        let runtime = LarchRuntime::current_thread().ok()?;
        let context = Self {
            runtime,
            runner: TokioProcessRunner::new(Arc::new(NoopProcessObserver)),
            cancellation: Cancellation::new(),
            cwd,
        };
        let cancellation = context.cancellation.clone();
        context.runtime.block_on(async move {
            let signal_task = tokio::spawn(async move {
                let _result =
                    larch_adapters::runtime::cancel_on_shutdown_signal(&cancellation).await;
            });
            drop(signal_task);
        });
        Some(context)
    }

    fn git(&self) -> GitCli<'_, TokioProcessRunner> {
        GitCli::new(
            &self.runner,
            GitCliPolicy::new(self.cwd.clone()).expect("absolute current directory"),
        )
    }
}

fn typed_paths(paths: &[PathBuf]) -> Result<Vec<GitPath>, ()> {
    paths
        .iter()
        .map(|path| {
            GitPath::new(path.as_os_str().to_owned()).map_err(|error| {
                let _ = writeln!(io::stderr(), "{error}");
            })
        })
        .collect()
}

async fn run_add_with_retry(
    git: &GitCli<'_, TokioProcessRunner>,
    request: AddRequest,
    runner: &TokioProcessRunner,
    cancellation: &Cancellation,
) -> (Result<GitCliResult, GitCliError>, Option<String>) {
    let first = git.add(request.clone(), cancellation).await;
    if !retryable_index_lock_failure(&first, git) {
        return (first, None);
    }
    match try_remove_stale_index_lock(runner, cancellation, git.working_directory()).await {
        LockRemoval::Removed(diagnostic) => (
            git.add(request, cancellation).await,
            Some(format!("{diagnostic}; retrying git command once")),
        ),
        LockRemoval::NotRemoved(diagnostic) => (first, Some(diagnostic)),
    }
}

async fn run_commit_with_retry(
    git: &GitCli<'_, TokioProcessRunner>,
    request: CommitRequest,
    runner: &TokioProcessRunner,
    cancellation: &Cancellation,
) -> (Result<GitCliResult, GitCliError>, Option<String>) {
    let first = git.commit(request.clone(), cancellation).await;
    if !retryable_index_lock_failure(&first, git) {
        return (first, None);
    }
    match try_remove_stale_index_lock(runner, cancellation, git.working_directory()).await {
        LockRemoval::Removed(diagnostic) => (
            git.commit(request, cancellation).await,
            Some(format!("{diagnostic}; retrying git command once")),
        ),
        LockRemoval::NotRemoved(diagnostic) => (first, Some(diagnostic)),
    }
}

fn retryable_index_lock_failure(
    result: &Result<GitCliResult, GitCliError>,
    git: &GitCli<'_, TokioProcessRunner>,
) -> bool {
    let Err(GitCliError::Failed(failed)) = result else {
        return false;
    };
    output_mentions_index_lock(failed)
        || index_lock_path(git.working_directory()).is_some_and(|path| path.exists())
}

fn output_mentions_index_lock(result: &GitCliResult) -> bool {
    let mut content = String::from_utf8_lossy(result.output().stdout()).to_lowercase();
    content.push_str(&String::from_utf8_lossy(result.output().stderr()).to_lowercase());
    content.contains("index.lock")
        || (content.contains("unable to create") && content.contains("lock"))
}

fn render_git_result(result: Result<GitCliResult, GitCliError>, note: Option<&str>) -> u8 {
    match result {
        Ok(result) => {
            let _ = io::stdout().write_all(result.output().stdout());
            let _ = io::stderr().write_all(result.output().stderr());
            if let Some(note) = note {
                let _ = writeln!(io::stderr(), "{note}");
            }
            0
        }
        Err(GitCliError::Failed(result)) => {
            let _ = io::stdout().write_all(result.output().stdout());
            let _ = io::stderr().write_all(result.output().stderr());
            if let Some(note) = note {
                let _ = writeln!(io::stderr(), "{note}");
            }
            result
                .output()
                .status()
                .code()
                .and_then(|code| u8::try_from(code).ok())
                .unwrap_or(1)
        }
        Err(GitCliError::Process(error)) => {
            if let Some(output) = error.output() {
                let _ = io::stdout().write_all(output.stdout());
                let _ = io::stderr().write_all(output.stderr());
            }
            let _ = writeln!(io::stderr(), "fatal: {error}");
            if let Some(note) = note {
                let _ = writeln!(io::stderr(), "{note}");
            }
            match error.kind() {
                ProcessErrorKind::Spawn => 127,
                ProcessErrorKind::Cancelled => 130,
                ProcessErrorKind::TimedOut => 124,
                _ => 128,
            }
        }
        Err(error) => {
            let _ = writeln!(io::stderr(), "fatal: {error}");
            if let Some(note) = note {
                let _ = writeln!(io::stderr(), "{note}");
            }
            128
        }
    }
}

enum LockRemoval {
    Removed(String),
    NotRemoved(String),
}

async fn try_remove_stale_index_lock(
    runner: &TokioProcessRunner,
    cancellation: &Cancellation,
    cwd: &Path,
) -> LockRemoval {
    let Some(lock_path) = index_lock_path(cwd) else {
        return LockRemoval::NotRemoved(
            "larch: stale .git/index.lock not removed: git-dir probe failed".to_owned(),
        );
    };
    let label = format!("lock={}", lock_path.display());
    let metadata = match fs::symlink_metadata(&lock_path) {
        Ok(metadata) => metadata,
        Err(error) if error.kind() == io::ErrorKind::NotFound => {
            return LockRemoval::NotRemoved(format!(
                "larch: stale .git/index.lock not removed: lock absent; {label}"
            ));
        }
        Err(error) => {
            return LockRemoval::NotRemoved(format!(
                "larch: stale .git/index.lock not removed: stat failed: {error}; {label}"
            ));
        }
    };
    if !metadata.file_type().is_file() {
        return LockRemoval::NotRemoved(format!(
            "larch: stale .git/index.lock not removed: unsafe lock file type; {label}"
        ));
    }
    if metadata.len() != 0 {
        return LockRemoval::NotRemoved(format!(
            "larch: stale .git/index.lock not removed: non-empty lock; {label}"
        ));
    }
    match index_lock_holder_state(runner, cancellation, &lock_path, cwd).await {
        HolderState::Held => {
            return LockRemoval::NotRemoved(format!(
                "larch: stale .git/index.lock not removed: lock held by process; {label}"
            ));
        }
        HolderState::Unverifiable => {
            return LockRemoval::NotRemoved(format!(
                "larch: stale .git/index.lock not removed: holder probe failed; {label}"
            ));
        }
        HolderState::Absent => {}
    }
    if let Err(error) = fs::remove_file(&lock_path) {
        return LockRemoval::NotRemoved(format!(
            "larch: stale .git/index.lock not removed: unlink failed: {error}; {label}"
        ));
    }
    if lock_path.exists() {
        return LockRemoval::NotRemoved(format!(
            "larch: stale .git/index.lock not removed: unlink verification failed; {label}"
        ));
    }
    LockRemoval::Removed(format!("larch: removed stale .git/index.lock; {label}"))
}

fn index_lock_path(cwd: &Path) -> Option<PathBuf> {
    let repo = GixRepository::discover(cwd).ok()?;
    let location = repo.location();
    let git_dir = native_path(location.git_dir.as_bytes());
    Some(git_dir.join("index.lock"))
}

#[cfg(unix)]
fn native_path(bytes: &[u8]) -> PathBuf {
    use std::os::unix::ffi::OsStringExt as _;
    PathBuf::from(OsString::from_vec(bytes.to_vec()))
}

#[cfg(not(unix))]
fn native_path(bytes: &[u8]) -> PathBuf {
    PathBuf::from(String::from_utf8_lossy(bytes).into_owned())
}

fn lock_held_by_procfs(lock_path: &Path) -> Option<bool> {
    let proc_root = Path::new("/proc");
    if !proc_root.is_dir() {
        return None;
    }
    let wanted = lock_path
        .canonicalize()
        .unwrap_or_else(|_| lock_path.to_path_buf());
    let current = std::process::id().to_string();
    let entries = fs::read_dir(proc_root).ok()?;
    let mut uncertain = false;
    for entry in entries {
        let Ok(entry) = entry else {
            uncertain = true;
            continue;
        };
        let name = entry.file_name();
        let name = name.to_string_lossy();
        if name == current || !name.chars().all(|value| value.is_ascii_digit()) {
            continue;
        }
        let descriptors = match fs::read_dir(entry.path().join("fd")) {
            Ok(descriptors) => descriptors,
            Err(error) if error.kind() == io::ErrorKind::NotFound => continue,
            Err(_) => {
                uncertain = true;
                continue;
            }
        };
        for descriptor in descriptors {
            let Ok(descriptor) = descriptor else {
                uncertain = true;
                continue;
            };
            match descriptor.path().canonicalize() {
                Ok(path) if path == wanted => return Some(true),
                Ok(_) => {}
                Err(error) if error.kind() == io::ErrorKind::NotFound => {}
                Err(_) => uncertain = true,
            }
        }
    }
    if uncertain { None } else { Some(false) }
}

enum HolderState {
    Held,
    Absent,
    Unverifiable,
}

async fn index_lock_holder_state(
    runner: &TokioProcessRunner,
    cancellation: &Cancellation,
    lock_path: &Path,
    cwd: &Path,
) -> HolderState {
    match lock_held_by_procfs(lock_path) {
        Some(true) => HolderState::Held,
        Some(false) => HolderState::Absent,
        None => match probe_open_file_holder(runner, lock_path, cwd, cancellation).await {
            OpenFileHolderStatus::Held => HolderState::Held,
            OpenFileHolderStatus::Absent => HolderState::Absent,
            OpenFileHolderStatus::Unverifiable => HolderState::Unverifiable,
        },
    }
}

fn branch_write_allowed(cwd: &Path) -> bool {
    let state_file = env::var_os("SHIP_PR_STATE_FILE")
        .filter(|value| !value.is_empty())
        .map(PathBuf::from)
        .or_else(|| {
            env::var_os("IMPLEMENT_TMPDIR")
                .filter(|value| !value.is_empty())
                .map(|value| PathBuf::from(value).join("ship-pr-state.sh"))
        });
    let Some(state_file) = state_file else {
        return true;
    };
    let Ok(metadata) = fs::symlink_metadata(&state_file) else {
        return true;
    };
    if metadata.file_type().is_symlink() || !metadata.is_file() {
        return true;
    }
    let Some(repo) = GixRepository::discover(cwd).ok() else {
        return true;
    };
    let Ok(Head::Symbolic { name, .. }) = repo.head() else {
        return true;
    };
    let Some(branch) = short_branch_name(&name) else {
        return true;
    };
    let Ok(content) = fs::read_to_string(state_file) else {
        return true;
    };
    let mut forbidden = false;
    let mut original = "";
    for line in content.lines() {
        if let Some(value) = line.strip_prefix("ORIGINAL_BRANCH_FORBIDDEN=") {
            forbidden = value.trim().eq_ignore_ascii_case("true");
        } else if let Some(value) = line.strip_prefix("BRANCH_NAME=") {
            original = value;
        }
    }
    if forbidden && original == branch {
        let _ = writeln!(
            io::stderr(),
            "refusing commit or push on forbidden original branch: {branch}"
        );
        return false;
    }
    true
}

fn current_branch(args: &[String]) -> u8 {
    if let Some(arg) = args.first() {
        let _ = writeln!(
            io::stderr(),
            "git-current-branch.sh: unknown argument: {arg}"
        );
        return 1;
    }
    let Some(repo) = open_cwd_repository() else {
        let _ = writeln!(io::stderr(), "{CURRENT_BRANCH_DETACHED}");
        return 1;
    };
    let Ok(head) = repo.head() else {
        let _ = writeln!(io::stderr(), "{CURRENT_BRANCH_DETACHED}");
        return 1;
    };
    let name = match head {
        Head::Symbolic { name, .. } | Head::Unborn { name } => name,
        Head::Detached { .. } => {
            let _ = writeln!(io::stderr(), "{CURRENT_BRANCH_DETACHED}");
            return 1;
        }
    };
    let Some(branch) = short_branch_name(&name) else {
        let _ = writeln!(io::stderr(), "{CURRENT_BRANCH_DETACHED}");
        return 1;
    };
    emit_kv("BRANCH", &branch);
    0
}

fn branch_info(args: &[String]) -> u8 {
    if let Some(arg) = args.first() {
        let _ = writeln!(io::stderr(), "git-branch-info.sh: unknown argument: {arg}");
        return 1;
    }
    let Some(repo) = open_cwd_repository() else {
        return 1;
    };
    let Ok(head) = repo.head() else {
        return 1;
    };
    let (head_sha, current) = match head {
        Head::Symbolic { name, target } => (
            short_hex(&target),
            short_branch_name(&name).unwrap_or_default(),
        ),
        Head::Detached { target } => (short_hex(&target), String::new()),
        Head::Unborn { .. } => return 1,
    };
    emit_kv("HEAD_SHA", &head_sha);
    emit_kv("CURRENT_BRANCH", &current);
    0
}

fn count_commits(args: &[String]) -> u8 {
    if let Some(arg) = args.first() {
        let _ = writeln!(io::stderr(), "git count-commits: unknown argument: {arg}");
        return 1;
    }
    let (count, status) =
        open_cwd_repository().map_or((0, "git_error"), |repo| count_commits_in(&repo));
    if let Ok(path) = env::var("COUNT_COMMITS_STATUS_FILE")
        && !path.is_empty()
    {
        let _ = fs::write(path, format!("{status}\n"));
    }
    if status == "missing_main_ref" {
        let _ = writeln!(io::stderr(), "{COUNT_MISSING_MAIN}");
    }
    println!("{count}");
    0
}

fn count_commits_in(repo: &GixRepository) -> (u64, &'static str) {
    let Some(base) =
        resolve_optional(repo, "origin/main").or_else(|| resolve_optional(repo, "main"))
    else {
        return (0, "missing_main_ref");
    };
    let Some(head) = resolve_optional(repo, "HEAD") else {
        return (0, "git_error");
    };
    repo.commit_count_range(&base, &head)
        .map_or((0, "git_error"), |count| (count, "ok"))
}

fn show_stage(args: &[String]) -> u8 {
    let mut stage = String::new();
    let mut file = String::new();
    let mut index = 0;
    while index < args.len() {
        let arg = &args[index];
        if arg == "--stage" {
            let Some(value) = args.get(index + 1) else {
                let _ = writeln!(io::stderr(), "git-show-stage.sh: --stage requires a value");
                return 1;
            };
            stage.clone_from(value);
            index += 2;
            continue;
        }
        if arg == "--file" {
            let Some(value) = args.get(index + 1) else {
                let _ = writeln!(io::stderr(), "git-show-stage.sh: --file requires a value");
                return 1;
            };
            file.clone_from(value);
            index += 2;
            continue;
        }
        let _ = writeln!(io::stderr(), "git-show-stage.sh: unknown argument: {arg}");
        return 1;
    }
    if stage.is_empty() || file.is_empty() {
        let _ = writeln!(
            io::stderr(),
            "git-show-stage.sh: --stage and --file are required"
        );
        return 1;
    }
    if !matches!(stage.as_str(), "1" | "2" | "3") {
        let _ = writeln!(
            io::stderr(),
            "git-show-stage.sh: --stage must be 1, 2, or 3 (got: {stage})"
        );
        return 1;
    }
    let stage_num: u8 = stage.parse().unwrap_or(0);
    let Some(repo) = open_cwd_repository() else {
        return 128;
    };
    match repo.stage_blob(file.as_bytes(), stage_num) {
        Ok(bytes) => {
            let _ = io::stdout().write_all(&bytes);
            0
        }
        Err(error) => {
            let _ = writeln!(io::stderr(), "fatal: {error}");
            128
        }
    }
}

fn check_remote_branch(args: &[String]) -> u8 {
    let parsed = parse_check_remote_args(args);
    let (branch, remote) = match parsed {
        Ok(pair) => pair,
        Err(message) => {
            emit_kv("STATE", "error");
            emit_kv("RC", "1");
            // Sanitize argv-derived text before ERROR= (G-IO-2); match network path.
            emit_kv("ERROR", &one_line_summary(&message));
            return 0;
        }
    };
    match probe_remote_branch(&branch, &remote) {
        RemoteProbe::Present => {
            emit_kv("STATE", "present");
            emit_kv("RC", "0");
        }
        RemoteProbe::Absent => {
            emit_kv("STATE", "absent");
            emit_kv("RC", "2");
        }
        RemoteProbe::Error { rc, error } => {
            emit_kv("STATE", "error");
            emit_kv("RC", &rc.to_string());
            emit_kv("ERROR", &one_line_summary(&error));
        }
    }
    0
}

fn parse_check_remote_args(args: &[String]) -> Result<(String, String), String> {
    let mut branch = String::new();
    let mut remote = "origin".to_owned();
    let mut index = 0;
    while index < args.len() {
        let arg = &args[index];
        if arg == "--branch" {
            branch = args.get(index + 1).cloned().unwrap_or_default();
            index += 2;
            continue;
        }
        if arg == "--remote" {
            remote = args.get(index + 1).cloned().unwrap_or_default();
            index += 2;
            continue;
        }
        return Err(format!("unknown flag: {arg}"));
    }
    if branch.is_empty() {
        return Err("--branch is required".to_owned());
    }
    Ok((branch, remote))
}

enum RemoteProbe {
    Present,
    Absent,
    Error { rc: i32, error: String },
}

fn probe_remote_branch(branch: &str, remote: &str) -> RemoteProbe {
    let Ok(cwd) = env::current_dir() else {
        return RemoteProbe::Error {
            rc: 128,
            error: "cannot resolve working directory".to_owned(),
        };
    };
    let Ok(policy) = GitCliPolicy::new(cwd) else {
        return RemoteProbe::Error {
            rc: 128,
            error: "Git working directory must be absolute".to_owned(),
        };
    };
    let Ok(remote_name) = GitRemote::new(remote) else {
        return RemoteProbe::Error {
            rc: 1,
            error: "invalid remote name".to_owned(),
        };
    };
    let Ok(branch_ref) = GitRef::new(branch) else {
        return RemoteProbe::Error {
            rc: 1,
            error: "invalid branch name".to_owned(),
        };
    };
    let Ok(runtime) = LarchRuntime::current_thread() else {
        return RemoteProbe::Error {
            rc: 128,
            error: "runtime initialization failed".to_owned(),
        };
    };
    let runner = TokioProcessRunner::new(Arc::new(NoopProcessObserver));
    let git = GitCli::new(&runner, policy);
    let request = LsRemoteRequest {
        remote: remote_name,
        patterns: vec![branch_ref],
        heads: true,
        exit_code: true,
    };
    let mut last = RemoteProbe::Error {
        rc: 128,
        error: "git ls-remote failed".to_owned(),
    };
    for attempt in 1..=TRANSIENT_ATTEMPTS {
        let cancellation = Cancellation::new();
        let outcome = runtime.block_on(git.ls_remote(request.clone(), &cancellation));
        match classify_ls_remote(outcome) {
            LsRemoteClass::Present => return RemoteProbe::Present,
            LsRemoteClass::Absent => return RemoteProbe::Absent,
            LsRemoteClass::Error {
                rc,
                error,
                transient,
            } => {
                last = RemoteProbe::Error { rc, error };
                if !transient || attempt == TRANSIENT_ATTEMPTS {
                    break;
                }
                let backoff = TRANSIENT_BACKOFF_SECS
                    [(attempt as usize - 1).min(TRANSIENT_BACKOFF_SECS.len() - 1)];
                thread::sleep(Duration::from_secs(backoff));
            }
        }
    }
    last
}

enum LsRemoteClass {
    Present,
    Absent,
    Error {
        rc: i32,
        error: String,
        transient: bool,
    },
}

fn classify_ls_remote(outcome: Result<GitCliResult, GitCliError>) -> LsRemoteClass {
    match outcome {
        Ok(_) => LsRemoteClass::Present,
        Err(GitCliError::Failed(result)) => {
            let code = result.output().status().code().unwrap_or(1);
            if code == 2 {
                return LsRemoteClass::Absent;
            }
            // Match Python remote_branch_state: redact before ERROR= emission.
            let combined = format!(
                "{}{}",
                result.safe_stdout().as_str(),
                result.safe_stderr().as_str()
            );
            let summary = if combined.trim().is_empty() {
                format!("git ls-remote failed (exit {code})")
            } else {
                combined
            };
            LsRemoteClass::Error {
                rc: code,
                transient: is_transient_net(&summary),
                error: summary,
            }
        }
        Err(error) => {
            let summary = SafeText::from_untrusted(error.to_string())
                .as_str()
                .to_owned();
            LsRemoteClass::Error {
                rc: 128,
                transient: is_transient_net(&summary),
                error: summary,
            }
        }
    }
}

fn open_cwd_repository() -> Option<GixRepository> {
    let cwd = env::current_dir().ok()?;
    GixRepository::discover(cwd).ok()
}

fn resolve_optional(repo: &GixRepository, revision: &str) -> Option<ObjectId> {
    repo.resolve_revision(&Revision::new(revision.as_bytes()))
        .ok()
}

fn short_branch_name(name: &RefName) -> Option<String> {
    let raw = name.as_bytes();
    let stripped = raw.strip_prefix(b"refs/heads/").unwrap_or(raw);
    let text = std::str::from_utf8(stripped).ok()?;
    if text.is_empty() {
        None
    } else {
        Some(text.to_owned())
    }
}

fn short_hex(id: &ObjectId) -> String {
    let mut hex = String::with_capacity(id.digest().len() * 2);
    for byte in id.digest() {
        use std::fmt::Write as _;
        let _ = write!(hex, "{byte:02x}");
    }
    hex.chars().take(7).collect()
}

fn one_line_summary(text: &str) -> String {
    text.replace(['\n', '\r', '\t'], " ")
        .chars()
        .take(256)
        .collect()
}

fn is_transient_net(content: &str) -> bool {
    let lower = content.to_ascii_lowercase();
    // Keep the Python is_transient_net_signature exclusions for permanent DNS misses.
    if lower.contains("no such hosted") || lower.contains("no such hostname") {
        return false;
    }
    [
        "could not resolve",
        "temporary failure",
        "unable to access",
        "connection refused",
        "connection timed out",
        "timed out",
        "connection reset",
        "network is unreachable",
        "network/auth issue",
        "tls handshake",
        "ssl",
        "tls",
        "http 5",
        "502",
        "503",
        "504",
        "context deadline exceeded",
        "no such host",
    ]
    .iter()
    .any(|needle| lower.contains(needle))
}
