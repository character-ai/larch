//! Rust owner for `ci decide`, `ci status`, and the CI polling loop.

use crate::{
    argparse_compat::{
        ParsedCommandLine, missing, option_text as text, parse_python_int, parse_with_flags,
    },
    github_repository_resolution::{commits_behind_base, repository_ref, valid_git_label},
};
use clap::Args;
use larch_adapters::{
    FetchRequest, GitCli, GitCliError, GitCliPolicy, GitRefspec, GitRemote, TokioProcessRunner,
    classify_process_error,
    github::OctocrabGitHubService,
    runtime::{Cancellation, LarchRuntime, ShutdownSignal, wait_for_shutdown_signal},
};
use larch_core::{
    CI_POLL_INTERVAL_SECONDS, CheckRun, CiCounters, CiDecision, CiStatus, CiStatusKind,
    ExternalProcessRunner, GitHubActionsError, GitHubActionsErrorKind, GitHubActionsService,
    GitHubRepositoryRef, ProcessCancellation, ProcessErrorKind, PullRequestCiState,
    PullRequestMergeState, StatusFailureState, ci_decide, ci_merge_state_conflicted,
    classify_checks, private_atomic_write,
};
use std::{
    ffi::OsString,
    fs,
    path::{Path, PathBuf},
    process::ExitCode,
    time::{Duration, Instant},
};

#[rustfmt::skip]
const STATUS_OPTIONS: &[&str] = &["--pr", "--repo", "--base-remote", "--base-ref", "--empty-checks-grace"];
#[rustfmt::skip]
const WAIT_OPTIONS: &[&str] = &["--pr", "--repo", "--base-remote", "--base-ref", "--empty-checks-grace", "--empty-checks-startup-deadline", "--iteration", "--rebase-count", "--fix-attempts", "--timeout", "--output-file"];
#[rustfmt::skip]
const DECIDE_OPTIONS: &[&str] = &["--ci-status", "--status", "--behind-count", "--behind", "--failed-run-id", "--conflicted", "--iteration", "--rebase-count", "--fix-attempts"];
const STATUS_QUERY_TIMEOUT_SECONDS: u64 = 120;
const STATUS_USAGE: &str = concat!(
    "usage: cli.py ci status [-h] --pr PR --repo REPO [--base-remote BASE_REMOTE]\n",
    "                        [--base-ref BASE_REF]\n",
    "                        [--empty-checks-grace EMPTY_CHECKS_GRACE]",
);
const WAIT_USAGE: &str = concat!(
    "usage: cli.py ci wait [-h] --pr PR --repo REPO [--base-remote BASE_REMOTE]\n",
    "                      [--base-ref BASE_REF]\n",
    "                      [--empty-checks-grace EMPTY_CHECKS_GRACE]\n",
    "                      [--iteration ITERATION] [--rebase-count REBASE_COUNT]\n",
    "                      [--fix-attempts FIX_ATTEMPTS] [--timeout TIMEOUT]\n",
    "                      [--output-file OUTPUT_FILE]",
);
const DECIDE_USAGE: &str = concat!(
    "usage: cli.py ci decide [-h] --ci-status CI_STATUS --behind-count BEHIND_COUNT\n",
    "                        [--failed-run-id FAILED_RUN_ID]\n",
    "                        [--conflicted CONFLICTED] [--iteration ITERATION]\n",
    "                        [--rebase-count REBASE_COUNT]\n",
    "                        [--fix-attempts FIX_ATTEMPTS]",
);
const STATUS_HELP_OPTIONS: &str = "options:\n  -h, --help            show this help message and exit\n  --pr PR\n  --repo REPO\n  --base-remote BASE_REMOTE\n  --base-ref BASE_REF\n  --empty-checks-grace EMPTY_CHECKS_GRACE";
const WAIT_HELP_OPTIONS: &str = "options:\n  -h, --help            show this help message and exit\n  --pr PR\n  --repo REPO\n  --base-remote BASE_REMOTE\n  --base-ref BASE_REF\n  --empty-checks-grace EMPTY_CHECKS_GRACE\n  --iteration ITERATION\n  --rebase-count REBASE_COUNT\n  --fix-attempts FIX_ATTEMPTS\n  --timeout TIMEOUT\n  --output-file OUTPUT_FILE";
const DECIDE_HELP_OPTIONS: &str = "options:\n  -h, --help            show this help message and exit\n  --ci-status CI_STATUS, --status CI_STATUS\n  --behind-count BEHIND_COUNT, --behind BEHIND_COUNT\n  --failed-run-id FAILED_RUN_ID\n  --conflicted CONFLICTED\n  --iteration ITERATION\n  --rebase-count REBASE_COUNT\n  --fix-attempts FIX_ATTEMPTS";

#[derive(Args)]
#[command(trailing_var_arg = true)]
pub struct Arguments {
    #[arg(allow_hyphen_values = true)]
    arguments: Vec<OsString>,
}

#[derive(Clone, Debug)]
struct StatusArguments {
    pr: i64,
    repository: GitHubRepositoryRef,
    base_remote: String,
    base_ref: String,
    empty_checks_grace: u64,
}

#[derive(Clone, Debug)]
struct WaitArguments {
    status: StatusArguments,
    counters: CiCounters,
    timeout: u64,
    startup_deadline: u64,
    output_file: Option<PathBuf>,
}

trait CiStatusService: Sync {
    async fn read_pull_state(
        &self,
        repository: &GitHubRepositoryRef,
        number: u64,
        cancellation: &dyn ProcessCancellation,
    ) -> Result<PullRequestCiState, GitHubActionsError>;
    async fn read_checks(
        &self,
        repository: &GitHubRepositoryRef,
        git_reference: &str,
        cancellation: &dyn ProcessCancellation,
    ) -> Result<Vec<CheckRun>, GitHubActionsError>;
}

impl CiStatusService for OctocrabGitHubService {
    async fn read_pull_state(
        &self,
        repository: &GitHubRepositoryRef,
        number: u64,
        cancellation: &dyn ProcessCancellation,
    ) -> Result<PullRequestCiState, GitHubActionsError> {
        self.pull_request_ci_state(repository, number, cancellation)
            .await
    }

    async fn read_checks(
        &self,
        repository: &GitHubRepositoryRef,
        git_reference: &str,
        cancellation: &dyn ProcessCancellation,
    ) -> Result<Vec<CheckRun>, GitHubActionsError> {
        self.check_runs(repository, git_reference, cancellation)
            .await
    }
}

#[derive(Clone, Debug)]
struct WaitResult {
    status: CiStatus,
    decision: CiDecision,
    elapsed: u64,
}

enum WaitCompletion {
    Complete(WaitResult),
    Signaled(ShutdownSignal, u64),
}

pub fn decide(arguments: &Arguments) -> ExitCode {
    let parsed = match parse(
        arguments.arguments.as_slice(),
        DECIDE_OPTIONS,
        DECIDE_USAGE,
        "decide",
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let status_text = alias_value(&parsed, "--ci-status", "--status").unwrap_or_default();
    let Some(kind) = CiStatusKind::parse(&status_text) else {
        eprintln!("ERROR: --status must be pass|fail|pending|merged|error, got: {status_text}");
        return ExitCode::from(1);
    };
    if kind == CiStatusKind::NoChecks {
        eprintln!("ERROR: --status must be pass|fail|pending|merged|error, got: {status_text}");
        return ExitCode::from(1);
    }
    let behind = match alias_integer(&parsed, "--behind-count", "--behind") {
        Ok(value) => value,
        Err(code) => return code,
    };
    let iteration = match integer(&parsed, "--iteration", 0, DECIDE_USAGE, "decide") {
        Ok(value) => value,
        Err(code) => return code,
    };
    let rebase_count = match integer(&parsed, "--rebase-count", 0, DECIDE_USAGE, "decide") {
        Ok(value) => value,
        Err(code) => return code,
    };
    let fix_attempts = match integer(&parsed, "--fix-attempts", 0, DECIDE_USAGE, "decide") {
        Ok(value) => value,
        Err(code) => return code,
    };
    for (name, value) in [
        ("behind_count", behind),
        ("iteration", iteration),
        ("rebase_count", rebase_count),
        ("fix_attempts", fix_attempts),
    ] {
        if value < 0 {
            eprintln!("ERROR: {name} must be a non-negative integer, got: {value}");
            return ExitCode::from(1);
        }
    }
    let conflicted_text = text(&parsed, "--conflicted", "false");
    if !matches!(
        conflicted_text.to_ascii_lowercase().as_str(),
        "true" | "false"
    ) {
        eprintln!("ERROR: --conflicted must be true or false, got: {conflicted_text}");
        return ExitCode::from(1);
    }
    let decision = ci_decide(
        &CiStatus {
            kind,
            behind_count: usize::try_from(behind).unwrap_or(usize::MAX),
            failed_run_id: optional_text(&parsed, "--failed-run-id"),
            conflicted: conflicted_text.eq_ignore_ascii_case("true"),
            checks_empty: false,
            checks_observed: true,
        },
        CiCounters {
            iteration: iteration.cast_unsigned(),
            rebase_count: rebase_count.cast_unsigned(),
            fix_attempts: fix_attempts.cast_unsigned(),
        },
    );
    emit_decision(decision);
    ExitCode::SUCCESS
}

pub fn status(arguments: &Arguments) -> ExitCode {
    let parsed = match parse(
        arguments.arguments.as_slice(),
        STATUS_OPTIONS,
        STATUS_USAGE,
        "status",
    ) {
        Ok(parsed) => parsed,
        Err(_code) => {
            emit_status(&CiStatus::error());
            return ExitCode::SUCCESS;
        }
    };
    let query = match status_arguments(&parsed, STATUS_USAGE, "status") {
        Ok(query) => query,
        Err(_code) => {
            emit_status(&CiStatus::error());
            return ExitCode::SUCCESS;
        }
    };
    let status = live_status(&query).unwrap_or_else(|_| CiStatus::error());
    emit_status(&status);
    ExitCode::SUCCESS
}

pub fn wait(arguments: &Arguments) -> ExitCode {
    let parsed = match parse(
        arguments.arguments.as_slice(),
        WAIT_OPTIONS,
        WAIT_USAGE,
        "wait",
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let query = match wait_arguments(&parsed) {
        Ok(query) => query,
        Err(code) => return code,
    };
    if let Some(path) = &query.output_file
        && let Err(error) = clean_wait_files(path)
    {
        eprintln!("{error}");
        return ExitCode::from(1);
    }
    let completion = match live_wait(&query) {
        Ok(completion) => completion,
        Err(error) => {
            if let Some(path) = &query.output_file {
                let fallback = unexpected_wait_result(0);
                if publish_wait_files(path, &wait_output(&fallback, query.counters.iteration), 1)
                    .is_err()
                {
                    return ExitCode::from(1);
                }
                return ExitCode::SUCCESS;
            }
            eprintln!("{error}");
            return ExitCode::from(1);
        }
    };
    let result = match completion {
        WaitCompletion::Complete(result) => result,
        WaitCompletion::Signaled(signal, elapsed) => {
            let result = unexpected_wait_result(elapsed);
            let code = signal_exit_code(signal);
            if let Some(path) = &query.output_file
                && publish_wait_files(path, &wait_output(&result, query.counters.iteration), code)
                    .is_err()
            {
                return ExitCode::from(1);
            }
            return ExitCode::from(code);
        }
    };
    if let Some(path) = &query.output_file {
        let text = wait_output(&result, query.counters.iteration);
        if publish_wait_files(path, &text, 0).is_err() {
            return ExitCode::from(1);
        }
    } else {
        print!("{}", wait_output(&result, query.counters.iteration));
    }
    ExitCode::SUCCESS
}

fn parse(
    arguments: &[OsString],
    options: &[&'static str],
    usage: &str,
    command: &str,
) -> Result<ParsedCommandLine, ExitCode> {
    let parsed = parse_with_flags(arguments, options, &["-h", "--help"], 0);
    if parsed.flag("-h") || parsed.flag("--help") {
        let options = match command {
            "decide" => DECIDE_HELP_OPTIONS,
            "status" => STATUS_HELP_OPTIONS,
            _ => WAIT_HELP_OPTIONS,
        };
        println!("{usage}\n\n{options}");
        return Err(ExitCode::from(1));
    }
    if let Some(error) = parsed.value_error() {
        eprintln!("{usage}\ncli.py ci {command}: error: {error}");
        return Err(ExitCode::from(1));
    }
    let required_state = if command == "decide" {
        vec![
            (
                "--ci-status/--status",
                alias_value(&parsed, "--ci-status", "--status").is_some(),
            ),
            (
                "--behind-count/--behind",
                alias_value(&parsed, "--behind-count", "--behind").is_some(),
            ),
        ]
    } else {
        vec![
            ("--pr", parsed.value("--pr").is_some()),
            ("--repo", parsed.value("--repo").is_some()),
        ]
    };
    if required_state.iter().any(|(_, present)| !present) {
        let error = missing(&required_state);
        eprintln!("{usage}\ncli.py ci {command}: error: {error}");
        return Err(ExitCode::from(1));
    }
    if let Some(error) = parsed.error() {
        eprintln!("{usage}\ncli.py ci {command}: error: {error}");
        return Err(ExitCode::from(1));
    }
    for (option, value) in parsed.entries() {
        if integer_option(option) && parse_python_int(&value.to_string_lossy()).is_none() {
            let diagnostic_option = match *option {
                "--behind-count" | "--behind" => "--behind-count/--behind",
                _ => *option,
            };
            eprintln!(
                "{usage}\ncli.py ci {command}: error: argument {diagnostic_option}: invalid int value: '{}'",
                value.to_string_lossy()
            );
            return Err(ExitCode::from(1));
        }
    }
    Ok(parsed)
}

fn integer_option(option: &str) -> bool {
    matches!(
        option,
        "--pr"
            | "--behind-count"
            | "--behind"
            | "--empty-checks-grace"
            | "--empty-checks-startup-deadline"
            | "--iteration"
            | "--rebase-count"
            | "--fix-attempts"
            | "--timeout"
    )
}

fn status_arguments(
    parsed: &ParsedCommandLine,
    usage: &str,
    command: &str,
) -> Result<StatusArguments, ExitCode> {
    let empty_checks_grace = integer(parsed, "--empty-checks-grace", 120, usage, command)?;
    if empty_checks_grace < 0 {
        eprintln!(
            "ERROR: --empty-checks-grace must be a non-negative integer, got: {empty_checks_grace}"
        );
        return Err(ExitCode::from(1));
    }
    let base_remote = text(parsed, "--base-remote", "origin");
    let base_ref = text(parsed, "--base-ref", "main");
    if !valid_git_label(&base_remote) || !valid_git_label(&base_ref) {
        eprintln!("ERROR: --base-remote/--base-ref contain unsupported characters");
        return Err(ExitCode::from(1));
    }
    let repository_text = text(parsed, "--repo", "");
    let repository = parse_repository(&repository_text).map_err(|error| {
        eprintln!("{error}");
        ExitCode::from(1)
    })?;
    Ok(StatusArguments {
        pr: integer(parsed, "--pr", 0, usage, command)?,
        repository,
        base_remote,
        base_ref,
        empty_checks_grace: empty_checks_grace.cast_unsigned(),
    })
}

fn wait_arguments(parsed: &ParsedCommandLine) -> Result<WaitArguments, ExitCode> {
    let status = status_arguments(parsed, WAIT_USAGE, "wait")?;
    let iteration = integer(parsed, "--iteration", 0, WAIT_USAGE, "wait")?;
    let rebase_count = integer(parsed, "--rebase-count", 0, WAIT_USAGE, "wait")?;
    let fix_attempts = integer(parsed, "--fix-attempts", 0, WAIT_USAGE, "wait")?;
    let timeout = integer(parsed, "--timeout", 1800, WAIT_USAGE, "wait")?;
    let startup_deadline = integer(
        parsed,
        "--empty-checks-startup-deadline",
        0,
        WAIT_USAGE,
        "wait",
    )?;
    for (name, value) in [
        ("rebase-count", rebase_count),
        ("fix-attempts", fix_attempts),
        ("iteration", iteration),
        ("timeout", timeout),
        ("empty-checks-startup-deadline", startup_deadline),
    ] {
        if value < 0 {
            eprintln!("ERROR: --{name} must be a non-negative integer, got: {value}");
            return Err(ExitCode::from(1));
        }
    }
    Ok(WaitArguments {
        status,
        counters: CiCounters {
            iteration: iteration.cast_unsigned(),
            rebase_count: rebase_count.cast_unsigned(),
            fix_attempts: fix_attempts.cast_unsigned(),
        },
        timeout: timeout.cast_unsigned(),
        startup_deadline: startup_deadline.cast_unsigned(),
        output_file: optional_text(parsed, "--output-file").map(PathBuf::from),
    })
}

fn integer(
    parsed: &ParsedCommandLine,
    option: &str,
    default: i64,
    usage: &str,
    command: &str,
) -> Result<i64, ExitCode> {
    let Some(value) = parsed.value(option) else {
        return Ok(default);
    };
    parse_python_int(&value.to_string_lossy()).ok_or_else(|| {
        eprintln!(
            "{usage}\ncli.py ci {command}: error: argument {option}: invalid int value: '{}'",
            value.to_string_lossy()
        );
        ExitCode::from(1)
    })
}

fn alias_integer(parsed: &ParsedCommandLine, left: &str, right: &str) -> Result<i64, ExitCode> {
    let value = alias_value(parsed, left, right).unwrap_or_default();
    parse_python_int(&value).ok_or_else(|| ExitCode::from(1))
}

fn alias_value(parsed: &ParsedCommandLine, left: &str, right: &str) -> Option<String> {
    parsed
        .entries()
        .iter()
        .rev()
        .find(|(name, _)| *name == left || *name == right)
        .map(|(_, value)| value.to_string_lossy().into_owned())
}

fn optional_text(parsed: &ParsedCommandLine, option: &str) -> Option<String> {
    let value = text(parsed, option, "");
    (!value.is_empty()).then_some(value)
}

fn parse_repository(value: &str) -> Result<GitHubRepositoryRef, String> {
    repository_ref(value).map_err(|()| "repository must use OWNER/REPO form".to_owned())
}

fn live_status(arguments: &StatusArguments) -> Result<CiStatus, String> {
    let runtime = LarchRuntime::new().map_err(|error| error.to_string())?;
    let cwd = std::env::current_dir().map_err(|error| error.to_string())?;
    runtime.block_on(async {
        let runner = TokioProcessRunner::default();
        let cancellation = Cancellation::new();
        let service = OctocrabGitHubService::from_gh(&runner, &cwd, &cancellation)
            .await
            .map_err(|error| error.to_string())?;
        gather_status(&service, &runner, &cancellation, &cwd, arguments).await
    })
}

fn live_wait(arguments: &WaitArguments) -> Result<WaitCompletion, String> {
    let runtime = LarchRuntime::new().map_err(|error| error.to_string())?;
    let cwd = std::env::current_dir().map_err(|error| error.to_string())?;
    runtime.block_on(async {
        let runner = TokioProcessRunner::default();
        let cancellation = Cancellation::new();
        let work = async {
            let service = OctocrabGitHubService::from_gh(&runner, &cwd, &cancellation)
                .await
                .map_err(|error| error.to_string())?;
            poll_ci(&service, &runner, &cancellation, &cwd, arguments)
                .await
                .map(WaitCompletion::Complete)
        };
        if arguments.output_file.is_some() {
            let started = Instant::now();
            tokio::select! {
                result = work => result,
                signal = wait_for_shutdown_signal() => {
                    cancellation.cancel();
                    signal.map_or_else(
                        |error| Err(error.to_string()),
                        |signal| Ok(WaitCompletion::Signaled(signal, started.elapsed().as_secs())),
                    )
                }
            }
        } else {
            work.await
        }
    })
}

async fn gather_status<R: ExternalProcessRunner, S: CiStatusService + ?Sized>(
    service: &S,
    runner: &R,
    cancellation: &dyn ProcessCancellation,
    cwd: &Path,
    arguments: &StatusArguments,
) -> Result<CiStatus, String> {
    let number = u64::try_from(arguments.pr).map_err(|_| "pull request number is invalid")?;
    let pull = service
        .read_pull_state(&arguments.repository, number, cancellation)
        .await;
    if pull
        .as_ref()
        .is_err_and(|error| error.kind() == GitHubActionsErrorKind::DeadlineExceeded)
    {
        eprintln!(
            "gather_status: gh pr view timed out after {STATUS_QUERY_TIMEOUT_SECONDS}s; treating as CI status failure"
        );
        return Err("pull request state query timed out".to_owned());
    }
    if pull.as_ref().is_ok_and(|state| state.merged) {
        return Ok(CiStatus {
            kind: CiStatusKind::Merged,
            behind_count: 0,
            failed_run_id: None,
            conflicted: false,
            checks_empty: false,
            checks_observed: false,
        });
    }
    let head_reference = format!("pull/{number}/head");
    let merge_state = pull.map_or(PullRequestMergeState::Unknown, |state| state.merge_state);
    let conflicted = ci_merge_state_conflicted(merge_state);
    let policy = GitCliPolicy::new(cwd.to_path_buf())
        .map_err(|error| error.to_string())?
        .with_timeout(Duration::from_secs(STATUS_QUERY_TIMEOUT_SECONDS));
    let git = GitCli::new(runner, policy);
    let fetched = git
        .fetch(
            FetchRequest {
                remote: GitRemote::new(arguments.base_remote.clone())
                    .map_err(|error| error.to_string())?,
                refspec: Some(
                    GitRefspec::new(arguments.base_ref.clone())
                        .map_err(|error| error.to_string())?,
                ),
                quiet: true,
                no_tags: false,
            },
            cancellation,
        )
        .await;
    match fetched {
        Ok(_) => {}
        Err(GitCliError::Process(error))
            if classify_process_error(&error) == ProcessErrorKind::TimedOut =>
        {
            eprintln!(
                "gather_status: git fetch timed out after {STATUS_QUERY_TIMEOUT_SECONDS}s; treating as CI status failure"
            );
            return Err(error.to_string());
        }
        Err(_) => {
            let mut pending = CiStatus::pending();
            pending.conflicted = conflicted;
            return Ok(pending);
        }
    }
    let mut checks = check_runs(service, arguments, &head_reference, cancellation).await?;
    if checks.is_empty() && arguments.empty_checks_grace > 0 {
        tokio::time::sleep(Duration::from_secs(arguments.empty_checks_grace)).await;
        checks = check_runs(service, arguments, &head_reference, cancellation).await?;
    }
    let observation = classify_checks(&checks, arguments.empty_checks_grace);
    let (behind_count, squash_merged) = behind_state(cwd, arguments).unwrap_or((0, false));
    Ok(CiStatus {
        kind: if squash_merged {
            CiStatusKind::Merged
        } else {
            observation.kind
        },
        behind_count: if squash_merged { 0 } else { behind_count },
        failed_run_id: if squash_merged {
            None
        } else {
            observation.failed_run_id
        },
        conflicted: if squash_merged { false } else { conflicted },
        checks_empty: observation.empty,
        checks_observed: true,
    })
}

async fn check_runs(
    service: &(impl CiStatusService + ?Sized),
    arguments: &StatusArguments,
    head_reference: &str,
    cancellation: &dyn ProcessCancellation,
) -> Result<Vec<CheckRun>, String> {
    service
        .read_checks(&arguments.repository, head_reference, cancellation)
        .await
        .map_err(|error| {
            if error.kind() == GitHubActionsErrorKind::DeadlineExceeded {
                eprintln!(
                    "gather_status: gh pr checks timed out after {STATUS_QUERY_TIMEOUT_SECONDS}s; treating as CI status failure"
                );
            }
            error.to_string()
        })
}

fn behind_state(cwd: &Path, arguments: &StatusArguments) -> Result<(usize, bool), String> {
    let commits = commits_behind_base(cwd, &arguments.base_remote, &arguments.base_ref)?;
    let needle = format!("(#{})", arguments.pr).into_bytes();
    let merged = !commits.is_empty()
        && commits
            .iter()
            .any(|commit| contains_bytes(&commit.subject, &needle));
    Ok((commits.len(), merged))
}

fn contains_bytes(haystack: &[u8], needle: &[u8]) -> bool {
    !needle.is_empty()
        && haystack
            .windows(needle.len())
            .any(|window| window == needle)
}

async fn poll_ci<R: ExternalProcessRunner, S: CiStatusService + ?Sized>(
    service: &S,
    runner: &R,
    cancellation: &dyn ProcessCancellation,
    cwd: &Path,
    arguments: &WaitArguments,
) -> Result<WaitResult, String> {
    let max_polls = arguments.timeout.div_ceil(CI_POLL_INTERVAL_SECONDS).max(1);
    let started = Instant::now();
    let mut polls = 0_u64;
    let mut failures = StatusFailureState::default();
    let mut last_status = CiStatus::pending();
    let mut startup_empty_since = None;
    let mut startup_active = arguments.startup_deadline > 0;
    loop {
        if polls >= max_polls {
            return Ok(terminal(
                last_status,
                CiDecision::bail("poll-budget-exhausted"),
                started,
            ));
        }
        eprintln!(
            "ci_monitor: CI status query #{} in progress after {}s",
            polls + 1,
            started.elapsed().as_secs()
        );
        let raw = gather_status(service, runner, cancellation, cwd, &arguments.status)
            .await
            .unwrap_or_else(|_| CiStatus::error());
        let status = match failures.observe(raw) {
            Ok(status) => status,
            Err(decision) => return Ok(terminal(CiStatus::error(), decision, started)),
        };
        last_status = status.clone();
        if status.kind == CiStatusKind::NoChecks {
            return Ok(terminal(
                status,
                CiDecision::bail("no-ci-checks-observed"),
                started,
            ));
        }
        let decision = ci_decide(&status, arguments.counters);
        if decision.action != "wait" {
            return Ok(terminal(status, decision, started));
        }
        if startup_active && status.checks_observed {
            if status.checks_empty {
                let empty_since = startup_empty_since.get_or_insert_with(Instant::now);
                if empty_since.elapsed().as_secs() >= arguments.startup_deadline {
                    let mut no_checks = status;
                    no_checks.kind = CiStatusKind::NoChecks;
                    return Ok(terminal(
                        no_checks,
                        CiDecision::bail("no-ci-checks-observed"),
                        started,
                    ));
                }
            } else {
                startup_active = false;
                startup_empty_since = None;
            }
        }
        polls += 1;
        eprintln!(
            "ci_monitor: poll {polls}/{max_polls} pending after {}s; sleeping {}s",
            started.elapsed().as_secs(),
            CI_POLL_INTERVAL_SECONDS
        );
        let sleep_started = Instant::now();
        tokio::time::sleep(Duration::from_secs(CI_POLL_INTERVAL_SECONDS)).await;
        if sleep_started.elapsed() > Duration::from_secs(60) {
            eprintln!(
                "ci_monitor: detected {}s real-time gap during poll {polls} (threshold 60s); probable host suspend, not counting this poll",
                sleep_started.elapsed().as_secs()
            );
            polls = polls.saturating_sub(1);
        }
    }
}

fn terminal(status: CiStatus, decision: CiDecision, started: Instant) -> WaitResult {
    let suffix = decision
        .bail_reason
        .map_or_else(String::new, |reason| format!(" ({reason})"));
    eprintln!(
        "ci_monitor: CI {} after {}s -> {}{}",
        status.kind.as_str(),
        started.elapsed().as_secs(),
        decision.action,
        suffix
    );
    WaitResult {
        status,
        decision,
        elapsed: started.elapsed().as_secs(),
    }
}

const fn unexpected_wait_result(elapsed: u64) -> WaitResult {
    WaitResult {
        status: CiStatus::pending(),
        decision: CiDecision::bail("ci-wait-unexpected-exit"),
        elapsed,
    }
}

const fn signal_exit_code(signal: ShutdownSignal) -> u8 {
    match signal {
        ShutdownSignal::Hangup => 129,
        ShutdownSignal::Interrupt => 130,
        ShutdownSignal::Terminate => 143,
    }
}

fn emit_status(status: &CiStatus) {
    println!("CI_STATUS={}", status.kind.as_str());
    println!("BEHIND_COUNT={}", status.behind_count);
    println!(
        "FAILED_RUN_ID={}",
        status.failed_run_id.as_deref().unwrap_or_default()
    );
    println!("CONFLICTED={}", status.conflicted);
}

fn emit_decision(decision: CiDecision) {
    println!("ACTION={}", decision.action);
    println!("BAIL_REASON={}", decision.bail_reason.unwrap_or_default());
}

fn wait_output(result: &WaitResult, iteration: u64) -> String {
    format!(
        "ACTION={}\nCI_STATUS={}\nBEHIND_COUNT={}\nCONFLICTED={}\nFAILED_RUN_ID={}\nBAIL_REASON={}\nITERATION={}\nELAPSED={}\n",
        result.decision.action,
        result.status.kind.as_str(),
        result.status.behind_count,
        result.status.conflicted,
        result.status.failed_run_id.as_deref().unwrap_or_default(),
        result.decision.bail_reason.unwrap_or_default(),
        iteration,
        result.elapsed,
    )
}

fn clean_wait_files(path: &Path) -> Result<(), String> {
    for candidate in [
        path.to_path_buf(),
        appended(path, ".done"),
        appended(path, ".tmp"),
    ] {
        if let Err(error) = fs::remove_file(&candidate)
            && error.kind() != std::io::ErrorKind::NotFound
        {
            return Err(error.to_string());
        }
    }
    Ok(())
}

fn publish_wait_files(path: &Path, text: &str, code: u8) -> Result<(), String> {
    atomic_output_write(path, text)?;
    atomic_output_write(&appended(path, ".done"), &format!("{code}\n"))
}

fn atomic_output_write(path: &Path, text: &str) -> Result<(), String> {
    let absolute = if path.is_absolute() {
        path.to_path_buf()
    } else {
        std::env::current_dir()
            .map_err(|error| error.to_string())?
            .join(path)
    };
    let parent = absolute
        .parent()
        .ok_or_else(|| "CI wait output path has no parent".to_owned())?;
    private_atomic_write(&absolute, text, parent).map_err(|error| error.to_string())
}

fn appended(path: &Path, suffix: &str) -> PathBuf {
    let mut value = path.as_os_str().to_os_string();
    value.push(suffix);
    PathBuf::from(value)
}

#[cfg(test)]
mod tests {
    use super::*;
    use larch_core::{CheckBucket, GitHubActionsError, ProcessError};
    use larch_test_support::{
        FakeProcessRunner, GitFixture, GitRepository, NeverCancelled, ProcessOutputBuilder,
    };
    use std::{collections::VecDeque, sync::Mutex};

    #[rustfmt::skip]
    struct FakeCiService {
        pulls: Mutex<VecDeque<Result<PullRequestCiState, GitHubActionsError>>>,
        checks: Mutex<VecDeque<Result<Vec<CheckRun>, GitHubActionsError>>>,
    }

    #[rustfmt::skip]
    impl FakeCiService {
        fn new(pulls: impl IntoIterator<Item = Result<PullRequestCiState, GitHubActionsError>>, checks: impl IntoIterator<Item = Result<Vec<CheckRun>, GitHubActionsError>>) -> Self {
            Self { pulls: Mutex::new(pulls.into_iter().collect()), checks: Mutex::new(checks.into_iter().collect()) }
        }
    }

    #[rustfmt::skip]
    impl CiStatusService for FakeCiService {
        async fn read_pull_state(&self, _repository: &GitHubRepositoryRef, _number: u64, _cancellation: &dyn ProcessCancellation) -> Result<PullRequestCiState, GitHubActionsError> {
            self.pulls.lock().unwrap().pop_front().unwrap()
        }
        async fn read_checks(&self, _repository: &GitHubRepositoryRef, _git_reference: &str, _cancellation: &dyn ProcessCancellation) -> Result<Vec<CheckRun>, GitHubActionsError> {
            self.checks.lock().unwrap().pop_front().unwrap()
        }
    }

    #[rustfmt::skip]
    fn raw(values: &[&str]) -> Arguments { Arguments { arguments: values.iter().map(OsString::from).collect() } }

    #[rustfmt::skip]
    fn query() -> StatusArguments {
        StatusArguments { pr: 7, repository: GitHubRepositoryRef::new("o", "r").unwrap(), base_remote: "origin".to_owned(), base_ref: "main".to_owned(), empty_checks_grace: 0 }
    }

    #[rustfmt::skip]
    fn pull(merged: bool, merge_state: PullRequestMergeState) -> PullRequestCiState { PullRequestCiState { merged, merge_state } }

    #[rustfmt::skip]
    fn pass_check() -> CheckRun {
        CheckRun { name: "ci".to_owned(), status: "completed".to_owned(), conclusion: Some("success".to_owned()), details_url: None, description: None, wall_clock_seconds: None, bucket: CheckBucket::Pass }
    }

    #[rustfmt::skip]
    fn pending_check() -> CheckRun { CheckRun { status: "in_progress".to_owned(), bucket: CheckBucket::Pending, ..pass_check() } }

    #[rustfmt::skip]
    fn wait_query(timeout: u64, startup_deadline: u64, empty_checks_grace: u64) -> WaitArguments {
        let mut status=query(); status.empty_checks_grace=empty_checks_grace;
        WaitArguments { status, counters: CiCounters { iteration: 0, rebase_count: 0, fix_attempts: 0 }, timeout, startup_deadline, output_file: None }
    }

    #[rustfmt::skip]
    async fn run_poll(pulls: impl IntoIterator<Item = Result<PullRequestCiState, GitHubActionsError>>, checks: impl IntoIterator<Item = Result<Vec<CheckRun>, GitHubActionsError>>, processes: impl IntoIterator<Item = Result<larch_core::ProcessOutput, ProcessError>>, arguments: &WaitArguments) -> WaitResult {
        let service=FakeCiService::new(pulls,checks); let runner=FakeProcessRunner::new(processes); let root=tempfile::tempdir().unwrap();
        poll_ci(&service,&runner,&NeverCancelled,root.path(),arguments).await.unwrap()
    }

    #[rustfmt::skip]
    fn gather_once(pull: Result<PullRequestCiState, GitHubActionsError>, checks: impl IntoIterator<Item = Result<Vec<CheckRun>, GitHubActionsError>>, processes: impl IntoIterator<Item = Result<larch_core::ProcessOutput, ProcessError>>) -> Result<CiStatus, String> {
        let service=FakeCiService::new([pull],checks); let runner=FakeProcessRunner::new(processes); let root=tempfile::tempdir().unwrap();
        LarchRuntime::new().unwrap().block_on(gather_status(&service,&runner,&NeverCancelled,root.path(),&query()))
    }

    #[test]
    #[rustfmt::skip]
    fn wait_parser_preserves_defaults_and_additive_startup_deadline() {
        let parsed=parse(&raw(&["--pr","7","--repo","o/r"]).arguments,WAIT_OPTIONS,WAIT_USAGE,"wait").unwrap(); let query=wait_arguments(&parsed).unwrap();
        assert_eq!((query.status.empty_checks_grace,query.timeout,query.startup_deadline),(120,1800,0));
    }

    #[test]
    #[rustfmt::skip]
    fn output_file_contract_keeps_order_and_done_marker() {
        let root=tempfile::tempdir().unwrap(); let path=root.path().join("wait.env"); let result=WaitResult { status: CiStatus::pending(), decision: CiDecision::bail("poll-budget-exhausted"), elapsed: 12 };
        publish_wait_files(&path,&wait_output(&result,3),0).unwrap();
        assert_eq!(fs::read_to_string(path).unwrap(),"ACTION=bail\nCI_STATUS=pending\nBEHIND_COUNT=0\nCONFLICTED=false\nFAILED_RUN_ID=\nBAIL_REASON=poll-budget-exhausted\nITERATION=3\nELAPSED=12\n"); assert_eq!(fs::read_to_string(root.path().join("wait.env.done")).unwrap(),"0\n");
    }

    #[test]
    #[rustfmt::skip]
    fn squash_race_search_is_byte_preserving() { assert!(contains_bytes(b"Port the monitor (#8619)",b"(#8619)")); assert!(!contains_bytes(b"Port the monitor (#8620)",b"(#8619)")); }

    #[test]
    #[rustfmt::skip]
    fn status_gathering_preserves_failure_and_fallback_boundaries() {
        assert_eq!(gather_once(Ok(pull(true,PullRequestMergeState::Unknown)),[],[]).unwrap().kind,CiStatusKind::Merged);
        assert!(gather_once(Err(GitHubActionsError::new(GitHubActionsErrorKind::DeadlineExceeded,"late")),[],[]).is_err());
        let failed_fetch=gather_once(Err(GitHubActionsError::new(GitHubActionsErrorKind::Transport,"offline")),[],[Ok(ProcessOutputBuilder::failure(1).build())]).unwrap();
        assert_eq!(failed_fetch.kind,CiStatusKind::Pending); assert!(failed_fetch.conflicted);
        assert!(gather_once(Ok(pull(false,PullRequestMergeState::Clean)),[],[Err(ProcessError::new(ProcessErrorKind::TimedOut,"late",None))]).is_err());
        let passing=gather_once(Ok(pull(false,PullRequestMergeState::Dirty)),[Ok(vec![pass_check()])],[Ok(ProcessOutputBuilder::success().build())]).unwrap();
        assert_eq!(passing.kind,CiStatusKind::Pass); assert!(passing.conflicted&&passing.checks_observed);
        assert!(gather_once(Ok(pull(false,PullRequestMergeState::Clean)),[Err(GitHubActionsError::new(GitHubActionsErrorKind::DeadlineExceeded,"late"))],[Ok(ProcessOutputBuilder::success().build())]).is_err());
    }

    #[test]
    #[rustfmt::skip]
    fn immediate_passing_poll_reaches_the_terminal_merge_decision() {
        let result=LarchRuntime::new().unwrap().block_on(run_poll([Ok(pull(false,PullRequestMergeState::Clean))],[Ok(vec![pass_check()])],[Ok(ProcessOutputBuilder::success().build())],&wait_query(1,0,0)));
        assert_eq!(result.decision.action,"merge");
    }

    #[tokio::test(start_paused = true)]
    #[rustfmt::skip]
    async fn paused_poll_covers_budgets_failures_and_empty_check_deadlines() {
        let clean=||Ok(pull(false,PullRequestMergeState::Clean)); let fetch=||Ok(ProcessOutputBuilder::success().build());
        let budget=run_poll([clean(),clean()],[Ok(vec![pending_check()]),Ok(vec![pending_check()])],[fetch(),fetch()],&wait_query(11,0,0)).await;
        assert_eq!(budget.decision.bail_reason,Some("poll-budget-exhausted"));
        let deadline=||Err(GitHubActionsError::new(GitHubActionsErrorKind::DeadlineExceeded,"late"));
        let stale=run_poll([deadline(),deadline(),deadline()],[],[],&wait_query(30,0,0)).await;
        assert_eq!(stale.decision.bail_reason,Some("ci-status-stale"));
        let no_checks=run_poll([clean()],[Ok(vec![]),Ok(vec![])],[fetch()],&wait_query(10,0,1)).await;
        assert_eq!(no_checks.decision.bail_reason,Some("no-ci-checks-observed"));
    }

    #[test]
    #[rustfmt::skip]
    fn parser_and_output_helpers_cover_rejection_and_cleanup_edges() {
        assert!(valid_git_label("origin/release-1")&&!valid_git_label("")&&!valid_git_label("origin main"));
        assert!(parse_repository("owner/repo").is_ok()&&parse_repository("owner").is_err()&&parse_repository("owner/repo/extra").is_err());
        for values in [&["--pr","7","--repo","o/r","--empty-checks-grace","-1"][..],&["--pr","7","--repo","o/r","--base-ref","bad ref"][..]] { let parsed=parse(&raw(values).arguments,STATUS_OPTIONS,STATUS_USAGE,"status").unwrap(); assert!(status_arguments(&parsed,STATUS_USAGE,"status").is_err()); }
        assert_eq!((signal_exit_code(ShutdownSignal::Hangup),signal_exit_code(ShutdownSignal::Interrupt),signal_exit_code(ShutdownSignal::Terminate)),(129,130,143));
        let root=tempfile::tempdir().unwrap(); let path=root.path().join("wait.env");
        for candidate in [&path,&appended(&path,".done"),&appended(&path,".tmp")] { fs::write(candidate,"stale").unwrap(); }
        clean_wait_files(&path).unwrap(); assert!(!path.exists()&&!appended(&path,".done").exists()); assert_eq!(unexpected_wait_result(4).elapsed,4);
    }

    #[test]
    #[rustfmt::skip]
    fn behind_state_detects_the_squash_merge_subject() {
        let repository=GitRepository::builder(GitFixture::Refs).build().unwrap(); repository.write("next.txt",b"next\n").unwrap();
        for args in [&["add","next.txt"][..],&["commit","--quiet","-m","Port monitor (#7)"][..],&["update-ref","refs/remotes/origin/main","HEAD"][..],&["reset","--hard","HEAD^"][..]] { assert!(repository.git(args).unwrap().success()); }
        assert_eq!(behind_state(repository.root(),&query()).unwrap(),(1,true));
    }
}
