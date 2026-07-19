//! Shared Git branch and ref-read commands migrated from Python.

use std::{
    env, fs,
    io::{self, Write},
    process::ExitCode,
    sync::Arc,
    thread,
    time::Duration,
};

use larch_adapters::{
    GitCli, GitCliError, GitCliPolicy, GitCliResult, GitRef, GitRemote, GixRepository,
    LsRemoteRequest, NoopProcessObserver, TokioProcessRunner, runtime::Cancellation,
    runtime::LarchRuntime,
};
use larch_core::{Head, ObjectId, RefName, RepositoryRead, Revision, SafeText, emit_kv};

const CURRENT_BRANCH_DETACHED: &str =
    "git-current-branch.sh: not on a named branch (detached HEAD or not a git repo)";
const COUNT_MISSING_MAIN: &str = "WARN: lib-count-commits.sh: neither local 'main' nor 'origin/main' exists; cannot determine commit base. Returning 0.";
const TRANSIENT_ATTEMPTS: u32 = 3;
const TRANSIENT_BACKOFF_SECS: [u64; 2] = [2, 4];

#[derive(Debug)]
pub enum GitCommand {
    BranchInfo { args: Vec<String> },
    CheckRemoteBranch { args: Vec<String> },
    CountCommits { args: Vec<String> },
    CurrentBranch { args: Vec<String> },
    ShowStage { args: Vec<String> },
}

pub fn run(command: GitCommand) -> ExitCode {
    let code = match command {
        GitCommand::BranchInfo { args } => branch_info(&args),
        GitCommand::CheckRemoteBranch { args } => check_remote_branch(&args),
        GitCommand::CountCommits { args } => count_commits(&args),
        GitCommand::CurrentBranch { args } => current_branch(&args),
        GitCommand::ShowStage { args } => show_stage(&args),
    };
    ExitCode::from(code)
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
            emit_kv("ERROR", &message);
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
