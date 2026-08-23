//! Closed typed push commands migrated from the Python runtime.

use std::{
    env, fs,
    io::{self, Write},
    path::Path,
    process::ExitCode,
    thread,
    time::Duration,
};

use larch_adapters::{
    BranchMutationRequest, FetchRequest, ForceWithLease, GitCli, GitCliError, GitCliPolicy, GitRef,
    GitRefspec, GitRemote, GixRepository, LsRemoteRequest, PushRequest, TokioProcessRunner,
    runtime::{Cancellation, LarchRuntime},
};
use larch_core::{Head, RefName, RepositoryRead, SafeText, emit_kv};

const REMOTE: &str = "origin";
const MAX_ATTEMPTS: u32 = 3;
const BRANCH_DETACHED: &str = "git-push.sh: not on a named branch";

pub fn branch(args: &[String]) -> ExitCode {
    if let Some(argument) = args.first() {
        let _ = writeln!(io::stderr(), "git-push.sh: unknown argument: {argument}");
        return ExitCode::from(1);
    }
    let Some(branch) = current_branch() else {
        let _ = writeln!(io::stderr(), "{BRANCH_DETACHED}");
        return ExitCode::from(1);
    };
    if original_branch_forbidden(&branch) {
        let _ = writeln!(
            io::stderr(),
            "refusing commit or push on forbidden original branch: {branch}"
        );
        return ExitCode::from(1);
    }
    if !clean_tree() {
        let _ = writeln!(
            io::stderr(),
            "uncommitted working-tree changes detected before push"
        );
        return ExitCode::from(1);
    }

    let request = match push_request(&branch, None, true) {
        Ok(request) => request,
        Err(error) => return input_failure(&error),
    };
    let mut diagnostics = Vec::new();
    let mut last_code = 1;
    for attempt in 1..=MAX_ATTEMPTS {
        if current_branch().as_deref() != Some(branch.as_str()) {
            let _ = writeln!(
                io::stderr(),
                "git-push.sh: not on a named branch before attempt {attempt}"
            );
            return ExitCode::from(1);
        }
        match run_push(request.clone()) {
            Ok(()) => {
                emit_kv("BRANCH", &branch);
                return ExitCode::SUCCESS;
            }
            Err(error) => {
                last_code = error.code;
                diagnostics.push(error.diagnostic);
            }
        }
        if attempt < MAX_ATTEMPTS {
            thread::sleep(Duration::from_secs(1_u64 << (attempt - 1)));
        }
    }
    emit_kv("BRANCH", &branch);
    write_deduplicated(&diagnostics);
    ExitCode::from(last_code)
}

pub fn force(expected_remote_oid: Option<&str>) -> ExitCode {
    let result = force_recovery(None, expected_remote_oid);
    if !result.branch.is_empty() {
        emit_kv("BRANCH", &result.branch);
    }
    if !result.detail.is_empty() {
        let _ = writeln!(
            io::stderr(),
            "{}",
            SafeText::from_untrusted(&result.detail).as_str()
        );
    }
    emit_kv("PUSHED", if result.pushed { "true" } else { "false" });
    emit_kv("STATUS", result.status);
    ExitCode::from(result.code)
}

/// Result from the shared clean-tree, exact-lease force-push recovery owner.
pub struct ForcePushOutcome {
    pub pushed: bool,
    pub status: &'static str,
    branch: String,
    code: u8,
    detail: String,
}

impl ForcePushOutcome {
    const fn success(status: &'static str, branch: String) -> Self {
        Self {
            pushed: true,
            status,
            branch,
            code: 0,
            detail: String::new(),
        }
    }

    const fn failure(status: &'static str, branch: String, code: u8, detail: String) -> Self {
        Self {
            pushed: false,
            status,
            branch,
            code,
            detail,
        }
    }
}

/// Run force-push recovery without emitting the public command envelope.
pub fn force_recovery(
    expected_branch: Option<&str>,
    expected_remote_oid: Option<&str>,
) -> ForcePushOutcome {
    let Some(branch) = current_branch() else {
        return ForcePushOutcome::failure(
            "detached_head",
            String::new(),
            2,
            "git-force-push.sh: not on a named branch".to_owned(),
        );
    };
    if expected_branch.is_none() && original_branch_forbidden(&branch)
        || expected_branch.is_some_and(|expected| expected != branch)
    {
        return ForcePushOutcome::failure("branch_mismatch", branch, 2, String::new());
    }
    if !clean_tree() {
        return ForcePushOutcome::failure("dirty_worktree", branch, 1, String::new());
    }
    let expected = match expected_remote_oid.map(GitRef::new).transpose() {
        Ok(expected) => expected,
        Err(error) => {
            return ForcePushOutcome::failure(
                "invalid_expected_remote_oid",
                branch,
                2,
                error.to_string(),
            );
        }
    };
    let request = match push_request(&branch, expected, false) {
        Ok(request) => request,
        Err(error) => return ForcePushOutcome::failure("invalid_input", branch, 2, error),
    };
    let _ = fetch_branch(&branch);
    let first = match run_push(request.clone()) {
        Ok(()) => return ForcePushOutcome::success("pushed", branch),
        Err(error) => error,
    };
    // A failed network write has an ambiguous outcome. Read the remote before
    // deciding whether a retry could overwrite a later tip.
    if remote_matches_head(&branch) {
        return ForcePushOutcome::success("noop_same_ref", branch);
    }
    let _ = fetch_branch(&branch);
    thread::sleep(Duration::from_secs(5));
    match run_push(request) {
        Ok(()) => ForcePushOutcome::success("pushed", branch),
        Err(second) => ForcePushOutcome::failure(
            "diverged_retry_failed",
            branch,
            1,
            format!("{}\n{}", first.diagnostic, second.diagnostic),
        ),
    }
}

/// Push the current branch for `pr create`, optionally applying the legacy
/// force-with-lease recovery used when an open PR already exists.
pub fn push_for_pr(branch: &str, recover_existing: bool) -> bool {
    if current_branch().as_deref() != Some(branch) || !clean_tree() {
        return false;
    }
    let Ok(request) = push_request(branch, None, true) else {
        return false;
    };
    if run_push(request).is_ok() {
        return true;
    }
    if !recover_existing {
        return false;
    }
    let _ignored = fetch_branch(branch);
    let _ignored = set_upstream(branch);
    let Ok(force_request) = push_request(branch, None, false) else {
        return false;
    };
    if run_push(force_request.clone()).is_ok() {
        return true;
    }
    let _ignored = fetch_branch(branch);
    if remote_matches_head(branch) {
        return true;
    }
    thread::sleep(Duration::from_secs(5));
    run_push(force_request).is_ok()
}

fn push_request(
    branch: &str,
    expected_remote_oid: Option<GitRef>,
    set_upstream: bool,
) -> Result<PushRequest, String> {
    let remote = GitRemote::new(REMOTE).map_err(|error| error.to_string())?;
    let destination = format!("refs/heads/{branch}");
    let refspec =
        GitRefspec::new(format!("HEAD:{destination}")).map_err(|error| error.to_string())?;
    let force_with_lease = match expected_remote_oid {
        Some(oid) => Some(ForceWithLease::Expecting {
            reference: GitRef::new(destination).map_err(|error| error.to_string())?,
            oid,
        }),
        None if !set_upstream => Some(ForceWithLease::Enabled),
        None => None,
    };
    Ok(PushRequest {
        remote: larch_adapters::GitPushTarget::Configured(remote),
        refspecs: vec![refspec],
        force_with_lease,
        set_upstream,
        prune: false,
    })
}

struct PushFailure {
    code: u8,
    diagnostic: String,
}

fn run_push(request: PushRequest) -> Result<(), PushFailure> {
    let cwd = env::current_dir().map_err(|error| PushFailure {
        code: 1,
        diagnostic: SafeText::from_untrusted(error.to_string())
            .as_str()
            .to_owned(),
    })?;
    let policy = GitCliPolicy::new(cwd).map_err(|error| git_failure(&error))?;
    let runtime = LarchRuntime::new().map_err(|error| PushFailure {
        code: 1,
        diagnostic: SafeText::from_untrusted(error.to_string())
            .as_str()
            .to_owned(),
    })?;
    let runner = TokioProcessRunner::default();
    let cancellation = Cancellation::new();
    runtime
        .block_on(GitCli::new(&runner, policy).push(request, &cancellation))
        .map(|_| ())
        .map_err(|error| git_failure(&error))
}

fn fetch_branch(branch: &str) -> Result<(), PushFailure> {
    let remote = GitRemote::new(REMOTE).map_err(|error| input_failure_result(&error))?;
    let refspec = GitRefspec::new(format!(
        "refs/heads/{branch}:refs/remotes/{REMOTE}/{branch}"
    ))
    .map_err(|error| input_failure_result(&error))?;
    let cwd = env::current_dir().map_err(|error| PushFailure {
        code: 1,
        diagnostic: SafeText::from_untrusted(error.to_string())
            .as_str()
            .to_owned(),
    })?;
    let policy = GitCliPolicy::new(cwd).map_err(|error| git_failure(&error))?;
    let runtime = LarchRuntime::new().map_err(|error| PushFailure {
        code: 1,
        diagnostic: SafeText::from_untrusted(error.to_string())
            .as_str()
            .to_owned(),
    })?;
    let runner = TokioProcessRunner::default();
    let cancellation = Cancellation::new();
    runtime
        .block_on(GitCli::new(&runner, policy).fetch(
            FetchRequest {
                remote,
                refspec: Some(refspec),
                quiet: true,
                no_tags: false,
                mode: larch_adapters::FetchMode::Standard,
            },
            &cancellation,
        ))
        .map(|_| ())
        .map_err(|error| git_failure(&error))
}

fn set_upstream(branch: &str) -> Result<(), PushFailure> {
    let name = GitRef::new(branch).map_err(|error| input_failure_result(&error))?;
    let upstream =
        GitRef::new(format!("{REMOTE}/{branch}")).map_err(|error| input_failure_result(&error))?;
    let cwd = env::current_dir().map_err(|error| PushFailure {
        code: 1,
        diagnostic: SafeText::from_untrusted(error.to_string())
            .as_str()
            .to_owned(),
    })?;
    let policy = GitCliPolicy::new(cwd).map_err(|error| git_failure(&error))?;
    let runtime = LarchRuntime::new().map_err(|error| PushFailure {
        code: 1,
        diagnostic: SafeText::from_untrusted(error.to_string())
            .as_str()
            .to_owned(),
    })?;
    let runner = TokioProcessRunner::default();
    let cancellation = Cancellation::new();
    runtime
        .block_on(GitCli::new(&runner, policy).branch_mutation(
            BranchMutationRequest::SetUpstream { name, upstream },
            &cancellation,
        ))
        .map(|_| ())
        .map_err(|error| git_failure(&error))
}

fn remote_matches_head(branch: &str) -> bool {
    let Some(local) = local_head() else {
        return false;
    };
    let Ok(remote) = GitRemote::new(REMOTE) else {
        return false;
    };
    let Ok(pattern) = GitRef::new(format!("refs/heads/{branch}")) else {
        return false;
    };
    let Ok(cwd) = env::current_dir() else {
        return false;
    };
    let Ok(policy) = GitCliPolicy::new(cwd) else {
        return false;
    };
    let Ok(runtime) = LarchRuntime::new() else {
        return false;
    };
    let runner = TokioProcessRunner::default();
    let cancellation = Cancellation::new();
    let result = runtime.block_on(GitCli::new(&runner, policy).ls_remote(
        LsRemoteRequest {
            remote: larch_adapters::GitLsRemoteTarget::Configured(remote),
            patterns: vec![pattern],
            heads: true,
            exit_code: true,
        },
        &cancellation,
    ));
    let Ok(result) = result else {
        return false;
    };
    let remote = String::from_utf8_lossy(result.output().stdout())
        .split_whitespace()
        .next()
        .unwrap_or_default()
        .to_owned();
    remote == local
}

pub fn current_branch() -> Option<String> {
    let cwd = env::current_dir().ok()?;
    current_branch_from(&cwd)
}

/// Read the named branch for a caller-supplied repository root.
///
/// Callers with durable run state should use this instead of deriving a root
/// from their ambient working directory.
pub fn current_branch_from(root: &Path) -> Option<String> {
    let repo = GixRepository::discover(root).ok()?;
    match repo.head().ok()? {
        Head::Symbolic { name, .. } | Head::Unborn { name } => short_branch_name(&name),
        Head::Detached { .. } => None,
    }
}

fn local_head() -> Option<String> {
    let cwd = env::current_dir().ok()?;
    let repo = GixRepository::discover(cwd).ok()?;
    let head = repo.head().ok()?;
    match head {
        Head::Symbolic { target, .. } | Head::Detached { target } => Some(target.to_hex()),
        Head::Unborn { .. } => None,
    }
}

fn short_branch_name(name: &RefName) -> Option<String> {
    std::str::from_utf8(
        name.as_bytes()
            .strip_prefix(b"refs/heads/")
            .unwrap_or(name.as_bytes()),
    )
    .ok()
    .filter(|branch| !branch.is_empty())
    .map(ToOwned::to_owned)
}

fn clean_tree() -> bool {
    GixRepository::discover(".")
        .and_then(|repo| repo.local_status(&larch_core::StatusOptions::default()))
        .is_ok_and(|status| !status.is_dirty())
}

fn original_branch_forbidden(branch: &str) -> bool {
    let path = env::var_os("SHIP_PR_STATE_FILE")
        .map(std::path::PathBuf::from)
        .or_else(|| {
            env::var_os("IMPLEMENT_TMPDIR").map(|root| Path::new(&root).join("ship-pr-state.sh"))
        });
    let Some(path) = path else {
        return false;
    };
    if fs::symlink_metadata(&path)
        .ok()
        .is_none_or(|metadata| !metadata.is_file() || metadata.file_type().is_symlink())
    {
        return false;
    }
    let Ok(contents) = fs::read_to_string(path) else {
        return false;
    };
    let mut forbidden = false;
    let mut saved_branch = "";
    for line in contents.lines() {
        if let Some(value) = line.strip_prefix("ORIGINAL_BRANCH_FORBIDDEN=") {
            forbidden = value.trim().eq_ignore_ascii_case("true");
        } else if let Some(value) = line.strip_prefix("BRANCH_NAME=") {
            saved_branch = value;
        }
    }
    forbidden && saved_branch == branch
}

fn git_failure(error: &GitCliError) -> PushFailure {
    PushFailure {
        code: exit_code(error),
        diagnostic: diagnostic(error),
    }
}

fn input_failure_result(error: &larch_adapters::GitCliInputError) -> PushFailure {
    PushFailure {
        code: 1,
        diagnostic: SafeText::from_untrusted(error.to_string())
            .as_str()
            .to_owned(),
    }
}

fn diagnostic(error: &GitCliError) -> String {
    match error {
        GitCliError::Failed(result) => result.safe_stderr().as_str().to_owned(),
        GitCliError::Process(error) => error.output().map_or_else(
            || {
                SafeText::from_untrusted(error.to_string())
                    .as_str()
                    .to_owned()
            },
            |output| output.safe_stderr().as_str().to_owned(),
        ),
        _ => SafeText::from_untrusted(error.to_string())
            .as_str()
            .to_owned(),
    }
}

fn exit_code(error: &GitCliError) -> u8 {
    match error {
        GitCliError::Failed(result) => result
            .output()
            .status()
            .code()
            .and_then(|code| u8::try_from(code).ok())
            .unwrap_or(1),
        _ => 1,
    }
}

fn input_failure(error: &str) -> ExitCode {
    let _ = writeln!(io::stderr(), "{}", SafeText::from_untrusted(error).as_str());
    ExitCode::from(1)
}

fn write_deduplicated(blocks: &[String]) {
    let mut prior = None;
    let mut repeats = 0;
    for block in blocks {
        if prior.as_ref() == Some(block) {
            repeats += 1;
            continue;
        }
        if let Some(previous) = prior.replace(block.clone()) {
            let _ = write!(io::stderr(), "{previous}");
            if repeats != 0 {
                let _ = writeln!(io::stderr(), "(repeated {} times)", repeats + 1);
            }
        }
        repeats = 0;
    }
    if let Some(previous) = prior {
        let _ = write!(io::stderr(), "{previous}");
    }
    if repeats != 0 {
        let _ = writeln!(io::stderr(), "(repeated {} times)", repeats + 1);
    }
}
