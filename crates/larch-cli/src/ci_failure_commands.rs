//! Rust owner for the CI failure collection and repair-input commands.
//!
//! `failed-jobs`, `distill-log`, `rerun-failed`, and `main-health` read and
//! mutate GitHub only through the typed Octocrab service whose sole credential
//! is `gh auth token` (issue #7672); no `gh api` or `gh run` subprocess remains.
//! `behind-count` reads history through `gix` and shells out only for the Git
//! fetch exception (issue #7671).

use crate::{
    argparse_compat::{
        ParsedCommandLine, ascii_digits, missing, option_text as text, parse_python_int,
        parse_with_flags,
    },
    github_repository_resolution::{commits_behind_base, repository_ref, valid_git_label},
    github_service::with_github_service,
    implement_commands::write_atomic,
};
use clap::Args;
use larch_adapters::{
    FetchRequest, GitCli, GitCliPolicy, GitRefspec, GitRemote, TokioProcessRunner,
    github::OctocrabGitHubService,
    runtime::{Cancellation, LarchRuntime},
};
use larch_core::{
    CI_FIXER_STATUS_HEALTH_BAIL, GitHubActionsError, GitHubActionsErrorKind, GitHubActionsService,
    GitHubMutationOutcome, GitHubRepositoryRef, MAIN_HEALTH_DEFAULT_WORKFLOW,
    MAIN_HEALTH_RUN_LIST_LIMIT, MAIN_HEALTH_WAIT_POLL_INTERVAL_SECONDS,
    MAIN_HEALTH_WAIT_TIMEOUT_SECONDS, MainHealthStatus, MainHealthWaitStep, ProcessCancellation,
    WorkflowRun, WorkflowRunFilters, bounded_detail, classify_failed_jobs, classify_main_health,
    distill_digest, main_health_flap_status, main_health_wait_step, private_atomic_write,
    render_failed_job_log, sanitize_diagnostic_line, sanitize_job_list,
};
use std::{
    env,
    ffi::OsString,
    fmt::Write as _,
    fs,
    path::{Path, PathBuf},
    process::ExitCode,
    time::{Duration, Instant},
};

const STATUS_QUERY_TIMEOUT_SECONDS: u64 = 120;
const INVALID_REPOSITORY: &str = "--repo must be owner/name";

/// One retired `argparse` surface, frozen down to its help and exit codes.
struct Surface {
    verb: &'static str,
    usage: &'static str,
    help: &'static str,
    options: &'static [&'static str],
    flags: &'static [&'static str],
    required: &'static [&'static str],
    integers: &'static [&'static str],
    usage_exit: u8,
    /// The retired owners disagreed on `--help`, so each surface pins its own.
    help_exit: u8,
}

#[rustfmt::skip]
const FAILED_JOBS: Surface = Surface {
    verb: "failed-jobs",
    usage: concat!(
        "usage: cli.py ci failed-jobs [-h] --run-id RUN_ID --repo REPO\n",
        "                             [--output-tsv OUTPUT_TSV]",
    ),
    help: "options:\n  -h, --help            show this help message and exit\n  --run-id RUN_ID\n  --repo REPO\n  --output-tsv OUTPUT_TSV",
    options: &["--run-id", "--repo", "--output-tsv"],
    flags: &[],
    required: &["--run-id", "--repo"],
    integers: &[],
    usage_exit: 2,
    help_exit: 2,
};

#[rustfmt::skip]
const DISTILL_LOG: Surface = Surface {
    verb: "distill-log",
    usage: "usage: cli.py ci distill-log [-h] --run-id RUN_ID --repo REPO --output OUTPUT",
    help: "options:\n  -h, --help       show this help message and exit\n  --run-id RUN_ID\n  --repo REPO\n  --output OUTPUT",
    options: &["--run-id", "--repo", "--output"],
    flags: &[],
    required: &["--run-id", "--repo", "--output"],
    integers: &[],
    usage_exit: 2,
    help_exit: 0,
};

#[rustfmt::skip]
const RERUN_FAILED: Surface = Surface {
    verb: "rerun-failed",
    usage: "usage: cli.py ci rerun-failed [-h] --run-id RUN_ID --repo REPO",
    help: "options:\n  -h, --help       show this help message and exit\n  --run-id RUN_ID\n  --repo REPO",
    options: &["--run-id", "--repo"],
    flags: &[],
    required: &["--run-id", "--repo"],
    integers: &[],
    usage_exit: 1,
    help_exit: 1,
};

#[rustfmt::skip]
const BEHIND_COUNT: Surface = Surface {
    verb: "behind-count",
    usage: concat!(
        "usage: cli.py ci behind-count [-h] [--base-remote BASE_REMOTE]\n",
        "                              [--base-ref BASE_REF] [--no-fetch]",
    ),
    help: "options:\n  -h, --help            show this help message and exit\n  --base-remote BASE_REMOTE\n  --base-ref BASE_REF\n  --no-fetch",
    options: &["--base-remote", "--base-ref"],
    flags: &["--no-fetch"],
    required: &[],
    integers: &[],
    usage_exit: 2,
    help_exit: 2,
};

#[rustfmt::skip]
const MAIN_HEALTH: Surface = Surface {
    verb: "main-health",
    usage: concat!(
        "usage: cli.py ci main-health [-h] --repo REPO [--base-ref BASE_REF]\n",
        "                             [--workflow WORKFLOW] [--limit LIMIT]\n",
        "                             [--timeout TIMEOUT] [--interval INTERVAL]\n",
        "                             [--wait] [--commit COMMIT]\n",
        "                             [--upstream-repo UPSTREAM_REPO]\n",
        "                             [--skip-flap-check]",
    ),
    help: "options:\n  -h, --help            show this help message and exit\n  --repo REPO\n  --base-ref BASE_REF\n  --workflow WORKFLOW\n  --limit LIMIT\n  --timeout TIMEOUT\n  --interval INTERVAL\n  --wait\n  --commit COMMIT\n  --upstream-repo UPSTREAM_REPO\n  --skip-flap-check",
    options: &["--repo", "--base-ref", "--workflow", "--limit", "--timeout", "--interval", "--commit", "--upstream-repo"],
    flags: &["--wait", "--skip-flap-check"],
    required: &["--repo"],
    integers: &["--limit", "--timeout", "--interval"],
    usage_exit: 2,
    help_exit: 2,
};

#[derive(Args)]
#[command(trailing_var_arg = true)]
pub struct Arguments {
    #[arg(allow_hyphen_values = true)]
    arguments: Vec<OsString>,
}

/// One default-branch health question, already validated.
#[derive(Clone, Debug)]
struct MainHealthQuery {
    repository: GitHubRepositoryRef,
    base_branch: String,
    workflow: String,
    limit: usize,
    head_sha: String,
    skip_flap_check: bool,
}

/// A GitHub read failure routed into the distill exit and bail vocabulary.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum ReadFailure {
    /// GitHub itself is unusable: credentials, quota, or a missing binary.
    HealthBail,
    /// GitHub answered, but the read did not produce usable evidence.
    Unusable,
}

impl ReadFailure {
    const fn distill_exit(self) -> u8 {
        match self {
            Self::HealthBail => 5,
            Self::Unusable => 1,
        }
    }

    const fn bail_class(self) -> &'static str {
        match self {
            Self::HealthBail => CI_FIXER_STATUS_HEALTH_BAIL,
            Self::Unusable => "github-log-failure",
        }
    }
}

const fn classify_read_failure(error: &GitHubActionsError) -> ReadFailure {
    match error.kind() {
        GitHubActionsErrorKind::Authorization | GitHubActionsErrorKind::RateLimited => {
            ReadFailure::HealthBail
        }
        _ => ReadFailure::Unusable,
    }
}

pub fn failed_jobs(arguments: &Arguments) -> ExitCode {
    let parsed = match parse(&arguments.arguments, &FAILED_JOBS) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let Some(run_id) = numeric_run_id(&parsed) else {
        return ExitCode::from(1);
    };
    let Ok(repository) = repository(&parsed) else {
        return ExitCode::from(1);
    };
    let jobs = match github(async |service, cancellation| {
        let run = service
            .workflow_run(&repository, run_id, cancellation)
            .await?;
        if run.status != "completed" {
            return Ok(None);
        }
        service
            .workflow_jobs(&repository, run_id, cancellation)
            .await
            .map(Some)
    }) {
        Ok(Some(jobs)) => jobs,
        Ok(None) => return ExitCode::from(3),
        Err((_failure, detail)) => {
            eprintln!("ERROR: {detail}");
            return ExitCode::from(1);
        }
    };
    let classified = classify_failed_jobs(&jobs);
    let mut rows = String::new();
    for job in &classified {
        let _written = writeln!(rows, "{}\t{}\t{}", job.name, job.shard, job.class());
    }
    match parsed.value("--output-tsv").map(PathBuf::from) {
        Some(path) if !path.as_os_str().is_empty() => {
            if let Err(error) = write_atomic(&path, &rows) {
                eprintln!("ERROR: {error}");
                return ExitCode::from(1);
            }
        }
        _ => print!("{rows}"),
    }
    let tokens = |fixable: bool| {
        sanitize_job_list(
            &classified
                .iter()
                .filter(|job| job.fixable == fixable)
                .map(|job| {
                    if fixable {
                        job.token()
                    } else {
                        format!("{}={}", job.token(), job.unfixable_reason())
                    }
                })
                .collect::<Vec<_>>()
                .join(","),
        )
    };
    println!("FAILED_JOBS_COUNT={}", classified.len());
    println!("FAILED_JOBS_FIXABLE={}", tokens(true));
    println!("FAILED_JOBS_UNFIXABLE={}", tokens(false));
    ExitCode::SUCCESS
}

pub fn rerun_failed(arguments: &Arguments) -> ExitCode {
    let parsed = match parse(&arguments.arguments, &RERUN_FAILED) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let Some(run_id) = numeric_run_id(&parsed) else {
        return ExitCode::from(1);
    };
    let (submitted, already_running, error) = match repository(&parsed) {
        Err(detail) => (false, false, detail),
        Ok(repository) => match github(async |service, cancellation| {
            service
                .rerun_workflow(&repository, run_id, true, cancellation)
                .await
        }) {
            Ok(GitHubMutationOutcome::Accepted | GitHubMutationOutcome::Reconciled) => {
                (true, false, String::new())
            }
            Ok(GitHubMutationOutcome::Ambiguous) => (
                false,
                false,
                "run rerun failed: GitHub did not confirm a new attempt".to_owned(),
            ),
            Err((_failure, detail)) if detail.to_lowercase().contains("already running") => {
                (true, true, String::new())
            }
            Err((_failure, detail)) => (false, false, format!("run rerun failed: {detail}")),
        },
    };
    println!("RERUN_SUBMITTED={submitted}");
    println!("ALREADY_RUNNING={already_running}");
    println!("ERROR={}", bounded_detail(&error));
    ExitCode::SUCCESS
}

pub fn behind_count(arguments: &Arguments) -> ExitCode {
    let parsed = match parse(&arguments.arguments, &BEHIND_COUNT) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let base_remote = text(&parsed, "--base-remote", "origin");
    let base_ref = text(&parsed, "--base-ref", "main");
    let count = if valid_git_label(&base_remote) && valid_git_label(&base_ref) {
        read_behind_count(&base_remote, &base_ref, !parsed.flag("--no-fetch")).unwrap_or(0)
    } else {
        0
    };
    println!("BEHIND_COUNT={count}");
    ExitCode::SUCCESS
}

pub fn distill_log(arguments: &Arguments) -> ExitCode {
    let parsed = match parse(&arguments.arguments, &DISTILL_LOG) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let raw_run_id = text(&parsed, "--run-id", "");
    let Some(run_id) = parse_run_id(raw_run_id.trim()) else {
        eprintln!("ERROR: --run-id must be numeric");
        return ExitCode::from(2);
    };
    let raw_repository = text(&parsed, "--repo", "");
    let raw_repository = raw_repository.trim();
    let Ok(repository) = repository_ref(raw_repository) else {
        eprintln!("ERROR: {INVALID_REPOSITORY}");
        return ExitCode::from(2);
    };
    let declared = env::var("IMPLEMENT_TMPDIR").unwrap_or_default();
    let Some((output, root)) = distill_output_path(&text(&parsed, "--output", ""), &declared)
    else {
        eprintln!("ERROR: --output must resolve under IMPLEMENT_TMPDIR");
        return ExitCode::from(2);
    };
    let outcome = distill(&repository, raw_repository, run_id, &output, &root);
    println!("STATUS={}", outcome.status);
    println!("OUTPUT={}", output.display());
    println!("FAILED_JOBS_COUNT={}", outcome.failed_jobs);
    println!("BAIL_CLASS={}", outcome.bail_class);
    ExitCode::from(outcome.exit_code)
}

pub fn main_health(arguments: &Arguments) -> ExitCode {
    let parsed = match parse(&arguments.arguments, &MAIN_HEALTH) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let mut bounds = Vec::new();
    for (option, default) in [
        ("--limit", MAIN_HEALTH_RUN_LIST_LIMIT),
        ("--timeout", MAIN_HEALTH_WAIT_TIMEOUT_SECONDS),
        ("--interval", MAIN_HEALTH_WAIT_POLL_INTERVAL_SECONDS),
    ] {
        let value = parsed
            .value(option)
            .and_then(|raw| parse_python_int(&raw.to_string_lossy()))
            .unwrap_or(default);
        if value < 0 {
            eprintln!("ERROR: {option} must be a non-negative integer, got: {value}");
            return ExitCode::from(2);
        }
        bounds.push(value.cast_unsigned());
    }
    let Ok(repository) = repository_ref(text(&parsed, "--upstream-repo", "").trim())
        .or_else(|()| repository_ref(text(&parsed, "--repo", "").trim()))
    else {
        emit_main_health(&MainHealthStatus::error("--repo must be owner/name"));
        return ExitCode::SUCCESS;
    };
    let query = MainHealthQuery {
        repository,
        base_branch: normalize_base_branch(&text(&parsed, "--base-ref", "main")),
        workflow: text(&parsed, "--workflow", MAIN_HEALTH_DEFAULT_WORKFLOW),
        limit: usize::try_from(bounds[0]).unwrap_or(usize::MAX),
        head_sha: text(&parsed, "--commit", "").trim().to_owned(),
        skip_flap_check: parsed.flag("--skip-flap-check"),
    };
    let status = if parsed.flag("--wait") {
        live_main_health(&query, Some((bounds[1], bounds[2])))
    } else {
        live_main_health(&query, None)
    };
    emit_main_health(&status);
    ExitCode::SUCCESS
}

/// Probe main's CI health in-process for the Preflight envelope.
pub fn preflight_main_health(repository: &str, base_ref: &str) -> Result<MainHealthStatus, String> {
    let repository = repository_ref(repository).map_err(|()| INVALID_REPOSITORY.to_owned())?;
    Ok(live_main_health(
        &MainHealthQuery {
            repository,
            base_branch: normalize_base_branch(base_ref),
            workflow: MAIN_HEALTH_DEFAULT_WORKFLOW.to_owned(),
            limit: usize::try_from(MAIN_HEALTH_RUN_LIST_LIMIT).unwrap_or(20),
            head_sha: String::new(),
            skip_flap_check: false,
        },
        None,
    ))
}

fn parse(arguments: &[OsString], surface: &Surface) -> Result<ParsedCommandLine, ExitCode> {
    let flags: Vec<&'static str> = surface
        .flags
        .iter()
        .copied()
        .chain(["-h", "--help"])
        .collect();
    let parsed = parse_with_flags(arguments, surface.options, &flags, 0);
    if parsed.flag("-h") || parsed.flag("--help") {
        println!("{}\n\n{}", surface.usage, surface.help);
        return Err(ExitCode::from(surface.help_exit));
    }
    let refuse = |error: &str| {
        eprintln!(
            "{}\ncli.py ci {}: error: {error}",
            surface.usage, surface.verb
        );
        ExitCode::from(surface.usage_exit)
    };
    if let Some(error) = parsed.value_error() {
        return Err(refuse(error));
    }
    let required: Vec<(&str, bool)> = surface
        .required
        .iter()
        .map(|option| (*option, parsed.value(option).is_some()))
        .collect();
    if required.iter().any(|(_option, present)| !present) {
        return Err(refuse(&missing(&required)));
    }
    if let Some(error) = parsed.error() {
        return Err(refuse(&error));
    }
    for (option, value) in parsed.entries() {
        if surface.integers.contains(option) && parse_python_int(&value.to_string_lossy()).is_none()
        {
            return Err(refuse(&format!(
                "argument {option}: invalid int value: '{}'",
                value.to_string_lossy()
            )));
        }
    }
    Ok(parsed)
}

fn numeric_run_id(parsed: &ParsedCommandLine) -> Option<u64> {
    let raw = text(parsed, "--run-id", "");
    let parsed = parse_run_id(raw.trim());
    if parsed.is_none() {
        eprintln!("ERROR: --run-id must be numeric");
    }
    parsed
}

fn parse_run_id(value: &str) -> Option<u64> {
    ascii_digits(value)
}

fn repository(parsed: &ParsedCommandLine) -> Result<GitHubRepositoryRef, String> {
    let value = text(parsed, "--repo", "");
    let repository = repository_ref(value.trim()).map_err(|()| INVALID_REPOSITORY.to_owned());
    if repository.is_err() {
        eprintln!("ERROR: {INVALID_REPOSITORY}");
    }
    repository
}

fn normalize_base_branch(value: &str) -> String {
    let text = value.trim();
    let text = text.rsplit_once('/').map_or(text, |(_head, tail)| tail);
    if text.is_empty() {
        "main".to_owned()
    } else {
        text.to_owned()
    }
}

/// Run one bounded GitHub read or mutation on the shared authenticated service.
///
/// Bootstrap failures are health bails: a missing `gh`, a missing credential,
/// and a broken async runtime all mean GitHub is unusable rather than that the
/// run under inspection is unhealthy.
fn github<T>(
    work: impl AsyncFnOnce(
        &OctocrabGitHubService,
        &dyn ProcessCancellation,
    ) -> Result<T, GitHubActionsError>,
) -> Result<T, (ReadFailure, String)> {
    let outcome = with_github_service(async |service, cancellation| {
        Ok(work(service, cancellation)
            .await
            .map_err(|error| (classify_read_failure(&error), error.to_string())))
    });
    outcome.unwrap_or_else(|setup| Err((ReadFailure::HealthBail, setup.into_detail())))
}

fn read_behind_count(base_remote: &str, base_ref: &str, fetch: bool) -> Result<usize, String> {
    let cwd = env::current_dir().map_err(|error| error.to_string())?;
    if fetch {
        fetch_base(&cwd, base_remote, base_ref)?;
    }
    commits_behind_base(&cwd, base_remote, base_ref).map(|commits| commits.len())
}

/// Refresh the base remote before counting. Fetch is the reviewed Git CLI
/// exception; every read below it stays on the typed gix port.
fn fetch_base(cwd: &Path, base_remote: &str, base_ref: &str) -> Result<(), String> {
    let runtime = LarchRuntime::new().map_err(|error| error.to_string())?;
    runtime.block_on(async {
        let runner = TokioProcessRunner::default();
        let policy = GitCliPolicy::new(cwd.to_path_buf())
            .map_err(|error| error.to_string())?
            .with_timeout(Duration::from_secs(STATUS_QUERY_TIMEOUT_SECONDS));
        let request = FetchRequest {
            remote: GitRemote::new(base_remote.to_owned()).map_err(|error| error.to_string())?,
            refspec: Some(GitRefspec::new(base_ref.to_owned()).map_err(|error| error.to_string())?),
            quiet: true,
            no_tags: false,
        };
        GitCli::new(&runner, policy)
            .fetch(request, &Cancellation::new())
            .await
            .map(|_output| ())
            .map_err(|error| error.to_string())
    })
}

struct DistillOutcome {
    exit_code: u8,
    status: &'static str,
    failed_jobs: usize,
    bail_class: String,
}

fn distill(
    repository: &GitHubRepositoryRef,
    repository_slug: &str,
    run_id: u64,
    output: &Path,
    root: &Path,
) -> DistillOutcome {
    let refuse = |failure: ReadFailure| DistillOutcome {
        exit_code: failure.distill_exit(),
        status: "error",
        failed_jobs: 0,
        bail_class: failure.bail_class().to_owned(),
    };
    let evidence = github(async |service, cancellation| {
        let run = service
            .workflow_run(repository, run_id, cancellation)
            .await?;
        if run.status != "completed" {
            return Ok(None);
        }
        let archive = service
            .download_workflow_logs(repository, run_id, cancellation)
            .await?;
        let jobs = service
            .workflow_jobs(repository, run_id, cancellation)
            .await?;
        Ok(Some((archive, jobs)))
    });
    let (archive, jobs) = match evidence {
        Ok(Some(evidence)) => evidence,
        Ok(None) => {
            return DistillOutcome {
                exit_code: 3,
                status: "in_progress",
                failed_jobs: 0,
                bail_class: "in_progress".to_owned(),
            };
        }
        Err((failure, _detail)) => return refuse(failure),
    };
    let failed_jobs: Vec<String> = jobs
        .iter()
        .filter(|job| job.is_failed())
        .map(|job| sanitize_diagnostic_line(&job.name))
        .filter(|name| !name.is_empty())
        .collect();
    let Some(raw_log) = render_failed_job_log(&archive, &failed_jobs) else {
        return refuse(ReadFailure::Unusable);
    };
    let digest = distill_digest(&run_id.to_string(), repository_slug, &raw_log, &failed_jobs);
    if let Err(error) = private_atomic_write(output, &digest, root) {
        eprintln!("ERROR: failed to write digest: {error}");
        return DistillOutcome {
            exit_code: 1,
            status: "error",
            failed_jobs: failed_jobs.len(),
            bail_class: "write-failure".to_owned(),
        };
    }
    DistillOutcome {
        exit_code: 0,
        status: "ok",
        failed_jobs: failed_jobs.len(),
        bail_class: String::new(),
    }
}

/// Resolve the digest path, refusing anything outside the declared session root.
fn distill_output_path(raw: &str, declared: &str) -> Option<(PathBuf, PathBuf)> {
    let declared = declared.trim();
    if declared.is_empty() {
        return None;
    }
    let root = fs::canonicalize(declared).ok()?;
    let output = PathBuf::from(raw);
    let name = output.file_name()?;
    let parent = fs::canonicalize(if output.parent()?.as_os_str().is_empty() {
        Path::new(".")
    } else {
        output.parent()?
    })
    .ok()?;
    let _relative = parent.strip_prefix(&root).ok()?;
    let resolved = parent.join(name);
    match fs::symlink_metadata(&resolved) {
        Ok(metadata) if metadata.file_type().is_symlink() || !metadata.is_file() => None,
        _ => Some((resolved, root)),
    }
}

fn live_main_health(query: &MainHealthQuery, wait: Option<(u64, u64)>) -> MainHealthStatus {
    github(async |service, cancellation| {
        let Some((timeout, interval)) = wait else {
            return Ok(read_main_health(service, cancellation, query).await);
        };
        let started = Instant::now();
        loop {
            let last = read_main_health(service, cancellation, query).await;
            let elapsed = started.elapsed().as_secs();
            match main_health_wait_step(&last, &query.head_sha, elapsed, timeout, interval) {
                MainHealthWaitStep::Ready(status) => return Ok(status),
                MainHealthWaitStep::Sleep(seconds) => {
                    tokio::time::sleep(Duration::from_secs(seconds)).await;
                }
            }
        }
    })
    .unwrap_or_else(|(_failure, detail)| MainHealthStatus::error(&detail))
}

async fn read_main_health(
    service: &OctocrabGitHubService,
    cancellation: &dyn ProcessCancellation,
    query: &MainHealthQuery,
) -> MainHealthStatus {
    let filters = WorkflowRunFilters {
        branch: Some(query.base_branch.clone()),
        workflow: None,
        event: Some("push".to_owned()),
        status: None,
        commit: (!query.head_sha.is_empty()).then(|| query.head_sha.clone()),
        limit: query.limit,
    };
    let runs = match service
        .list_workflow_runs(&query.repository, &filters, cancellation)
        .await
    {
        Ok(runs) => runs,
        Err(error) => return MainHealthStatus::error(&error.to_string()),
    };
    let runs: Vec<WorkflowRun> = runs
        .into_iter()
        .filter(|run| query.workflow.is_empty() || run.workflow_name == query.workflow)
        .collect();
    let verdict = classify_main_health(&runs, &query.head_sha);
    if query.skip_flap_check || verdict.status.status != "pass" {
        return verdict.status;
    }
    for candidate in &verdict.flap_candidates {
        let named_failure = service
            .workflow_jobs(&query.repository, candidate.database_id, cancellation)
            .await
            .is_ok_and(|jobs| {
                jobs.iter()
                    .any(|job| job.is_failed() && !job.name.trim().is_empty())
            });
        if named_failure {
            return main_health_flap_status(candidate, &verdict.status.head_sha);
        }
    }
    verdict.status
}

fn emit_main_health(status: &MainHealthStatus) {
    println!("MAIN_CI_STATUS={}", status.status);
    println!("MAIN_FAILED_RUN_ID={}", status.failed_run_id);
    println!("MAIN_HEALTH_HEAD_SHA={}", status.head_sha);
    println!("MAIN_HEALTH_DETAIL={}", status.detail);
}

#[cfg(test)]
mod tests {
    use super::*;
    use larch_core::{JobClass, WorkflowJob, sanitize_job_list};

    #[rustfmt::skip]
    fn raw(values: &[&str]) -> Arguments { Arguments { arguments: values.iter().map(OsString::from).collect() } }

    #[test]
    #[rustfmt::skip]
    fn argument_helpers_preserve_the_frozen_spellings() {
        assert_eq!(normalize_base_branch(" origin/release-1 "), "release-1");
        assert_eq!(normalize_base_branch("origin/"), "main");
        assert_eq!(normalize_base_branch(""), "main");
        assert_eq!(parse_run_id("42"), Some(42));
        assert!(parse_run_id("").is_none() && parse_run_id("4x").is_none() && parse_run_id("-4").is_none());
        assert!(repository_ref("o/r").is_ok() && repository_ref("o").is_err() && repository_ref("o/r/x").is_err());
        assert!(valid_git_label("origin") && !valid_git_label("") && !valid_git_label("bad ref"));
    }

    #[test]
    #[rustfmt::skip]
    fn every_surface_keeps_its_required_argument_and_help_exit_contract() {
        for surface in [&FAILED_JOBS, &DISTILL_LOG, &RERUN_FAILED, &BEHIND_COUNT, &MAIN_HEALTH] {
            assert_eq!(parse(&raw(&["--help"]).arguments, surface).unwrap_err(), ExitCode::from(surface.help_exit));
            if surface.required.is_empty() { assert!(parse(&raw(&[]).arguments, surface).is_ok()); }
            else { assert!(parse(&raw(&[]).arguments, surface).is_err()); }
        }
        assert!(parse(&raw(&["--repo", "o/r", "--limit", "x"]).arguments, &MAIN_HEALTH).is_err());
        assert!(parse(&raw(&["--repo", "o/r", "--wait", "--skip-flap-check"]).arguments, &MAIN_HEALTH).is_ok());
    }

    #[test]
    #[rustfmt::skip]
    fn failure_routing_separates_a_health_bail_from_an_unusable_read() {
        assert_eq!(classify_read_failure(&GitHubActionsError::new(GitHubActionsErrorKind::Authorization, "bad credentials")), ReadFailure::HealthBail);
        assert_eq!(classify_read_failure(&GitHubActionsError::new(GitHubActionsErrorKind::Transport, "offline")), ReadFailure::Unusable);
        assert_eq!(ReadFailure::HealthBail.distill_exit(), 5);
        assert_eq!(ReadFailure::HealthBail.bail_class(), CI_FIXER_STATUS_HEALTH_BAIL);
        assert_eq!(ReadFailure::Unusable.distill_exit(), 1);
        assert_eq!(ReadFailure::Unusable.bail_class(), "github-log-failure");
    }

    #[test]
    #[rustfmt::skip]
    fn the_output_path_must_resolve_under_the_declared_session_tmpdir() {
        let root = tempfile::tempdir().expect("tmpdir");
        let declared = root.path().to_string_lossy().into_owned();
        let outside = tempfile::tempdir().expect("outside");
        let digest = root.path().join("digest.md").to_string_lossy().into_owned();
        assert!(distill_output_path(&digest, &declared).is_some());
        assert!(distill_output_path(&outside.path().join("digest.md").to_string_lossy(), &declared).is_none());
        fs::create_dir(root.path().join("blocked")).expect("blocking directory");
        assert!(distill_output_path(&root.path().join("blocked").to_string_lossy(), &declared).is_none());
        assert!(distill_output_path(&digest, "").is_none());
        assert!(distill_output_path(&digest, &outside.path().join("missing").to_string_lossy()).is_none());
    }

    #[test]
    #[rustfmt::skip]
    fn the_emitted_job_lists_carry_their_tokens_and_reasons() {
        let jobs = [
            WorkflowJob { name: "lint".to_owned(), status: "completed".to_owned(), conclusion: Some("failure".to_owned()), wall_clock_seconds: None },
            WorkflowJob { name: "gitleaks".to_owned(), status: "completed".to_owned(), conclusion: Some("failure".to_owned()), wall_clock_seconds: None },
        ];
        let classified = classify_failed_jobs(&jobs);
        assert_eq!(sanitize_job_list(&classified.iter().filter(|job| job.fixable).map(JobClass::token).collect::<Vec<_>>().join(",")), "lint");
        assert_eq!(classified[1].unfixable_reason(), "history-scan");
    }
}
