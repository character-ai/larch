//! Command boundary for the Rust-owned rejected-analysis verbs.
//!
//! The domain scanner, work-directory wire models, and verdict ingestion live
//! in `larch_core::rejected_analysis`. This module only parses compatibility
//! arguments, composes typed Git/GitHub adapters, and emits command KVs.

#![allow(
    clippy::too_many_lines,
    reason = "The two compatibility command boundaries keep their historical argument diagnostics together."
)]

use std::{
    env,
    ffi::OsString,
    fs,
    path::{Path, PathBuf},
    process::ExitCode,
};

use chrono::{DateTime, Utc};
use larch_adapters::GixRepository;
use larch_core::{
    GitHubIssueBodyMode, GitHubIssueList, GitHubIssueState, GitHubService as _, GitPath, Head,
    ISSUE_DEDUP_LIMIT, RepositoryRead, emit_kv,
    rejected_analysis::{
        self, INGEST_STATUS_FILE, LEDGER_RELATIVE, OpenIssue, PrepareResult,
        VERDICT_SIDECAR_RELATIVE,
    },
};
use uuid::Uuid;

use crate::{
    analysis_state,
    argparse_compat::{ParsedCommandLine, absolute_path, missing, parse_with_flags, usage_error},
    github_repository_resolution::{ambient_repo, repository_ref},
    github_service::with_github_service,
    run_log_commands,
    run_log_publication_commands::synchronized_corpus_root,
};

const DEFAULT_VERIFY_CAP: usize = 100;
const MAX_HISTORY_COMMITS: usize = 100_000;
const PREPARE_USAGE: &str = "usage: rejected-analysis prepare [-h] --days DAYS [--log-root LOG_ROOT]\n                                 [--work-dir WORK_DIR]\n                                 [--verify-cap VERIFY_CAP]";
const PREPARE_HELP: &str = "usage: rejected-analysis prepare [-h] --days DAYS [--log-root LOG_ROOT]\n                                 [--work-dir WORK_DIR]\n                                 [--verify-cap VERIFY_CAP]\n\noptions:\n  -h, --help            show this help message and exit\n  --days DAYS, --n DAYS\n  --log-root LOG_ROOT   offline fixture corpus override; default synchronizes\n                        the current repository cache\n  --work-dir WORK_DIR\n  --verify-cap VERIFY_CAP\n";
const INGEST_USAGE: &str = "usage: rejected-analysis ingest-verdict [-h] --work-dir WORK_DIR\n                                        --candidate-id CANDIDATE_ID --output\n                                        OUTPUT --launcher-exit LAUNCHER_EXIT\n                                        [--dirty-sidecar DIRTY_SIDECAR]";
const INGEST_HELP: &str = "usage: rejected-analysis ingest-verdict [-h] --work-dir WORK_DIR\n                                        --candidate-id CANDIDATE_ID --output\n                                        OUTPUT --launcher-exit LAUNCHER_EXIT\n                                        [--dirty-sidecar DIRTY_SIDECAR]\n\noptions:\n  -h, --help            show this help message and exit\n  --work-dir WORK_DIR\n  --candidate-id CANDIDATE_ID\n  --output OUTPUT\n  --launcher-exit LAUNCHER_EXIT\n  --dirty-sidecar DIRTY_SIDECAR\n";
const FINALIZE_USAGE: &str = "usage: rejected-analysis finalize [-h] --work-dir WORK_DIR";
const FINALIZE_HELP: &str = "usage: rejected-analysis finalize [-h] --work-dir WORK_DIR\n\noptions:\n  -h, --help           show this help message and exit\n  --work-dir WORK_DIR\n";
const RECORD_USAGE: &str = "usage: rejected-analysis record [-h] --work-dir WORK_DIR\n                                [--issue-output ISSUE_OUTPUT]\n                                [--issue-verified {true,false}]\n                                [--issues-failed ISSUES_FAILED]\n                                [--launch-failures LAUNCH_FAILURES]\n                                [--repo-root REPO_ROOT]";
const RECORD_HELP: &str = "usage: rejected-analysis record [-h] --work-dir WORK_DIR\n                                [--issue-output ISSUE_OUTPUT]\n                                [--issue-verified {true,false}]\n                                [--issues-failed ISSUES_FAILED]\n                                [--launch-failures LAUNCH_FAILURES]\n                                [--repo-root REPO_ROOT]\n\noptions:\n  -h, --help            show this help message and exit\n  --work-dir WORK_DIR\n  --issue-output ISSUE_OUTPUT\n  --issue-verified {true,false}\n  --issues-failed ISSUES_FAILED\n  --launch-failures LAUNCH_FAILURES\n  --repo-root REPO_ROOT\n";

#[derive(Clone, Debug)]
struct PrepareRequest {
    days: i64,
    log_root: Option<PathBuf>,
    work_dir: Option<PathBuf>,
    verify_cap: i128,
}

#[derive(Clone, Debug)]
struct RecordRequest {
    work_dir: PathBuf,
    issue_output: Option<PathBuf>,
    issue_verified: Option<bool>,
    issues_failed: i64,
    launch_failures: i64,
    repo_root: Option<PathBuf>,
}

/// Execute `rejected-analysis prepare`.
#[must_use]
pub fn prepare(arguments: &[OsString]) -> ExitCode {
    if help_requested(arguments) {
        print!("{PREPARE_HELP}");
        return ExitCode::SUCCESS;
    }
    let request = match parse_prepare(arguments) {
        Ok(request) => request,
        Err(code) => return code,
    };
    match prepare_live(&request) {
        Ok(result) => {
            emit_prepare(&result);
            ExitCode::SUCCESS
        }
        Err(error) => {
            eprintln!("rejected-analysis prepare: {error}");
            ExitCode::from(2)
        }
    }
}

/// Execute `rejected-analysis ingest-verdict`.
#[must_use]
pub fn ingest_verdict(arguments: &[OsString]) -> ExitCode {
    if help_requested(arguments) {
        print!("{INGEST_HELP}");
        return ExitCode::SUCCESS;
    }
    let parsed = parse_with_flags(
        arguments,
        &[
            "--work-dir",
            "--candidate-id",
            "--output",
            "--launcher-exit",
            "--dirty-sidecar",
        ],
        &[],
        0,
    );
    if let Some(error) = parsed.value_error() {
        return usage_error(INGEST_USAGE, "rejected-analysis ingest-verdict", error, 2);
    }
    if let Some(error) = parsed.error() {
        return usage_error(INGEST_USAGE, "rejected-analysis ingest-verdict", &error, 2);
    }
    let Some(work_dir) = option_path(&parsed, "--work-dir") else {
        return ingest_missing(&parsed);
    };
    let Some(candidate_id) = option_text(&parsed, "--candidate-id") else {
        return ingest_missing(&parsed);
    };
    let Some(output) = option_path(&parsed, "--output") else {
        return ingest_missing(&parsed);
    };
    let Some(launcher_exit) = option_text(&parsed, "--launcher-exit") else {
        return ingest_missing(&parsed);
    };
    let Ok(launcher_exit) = launcher_exit.parse::<i64>() else {
        return usage_error(
            INGEST_USAGE,
            "rejected-analysis ingest-verdict",
            &format!("argument --launcher-exit: invalid int value: '{launcher_exit}'"),
            2,
        );
    };
    let dirty_sidecar = option_path(&parsed, "--dirty-sidecar");
    match rejected_analysis::ingest_artifact(
        &work_dir,
        &candidate_id,
        &output,
        launcher_exit,
        dirty_sidecar.as_deref(),
    ) {
        Ok((status, disposition)) => {
            emit_kv("INGEST_STATUS", &status);
            if !disposition.is_empty() {
                emit_kv("INGEST_DISPOSITION", &disposition);
            }
            ExitCode::SUCCESS
        }
        Err(error) => {
            eprintln!("rejected-analysis ingest-verdict: {error}");
            ExitCode::from(2)
        }
    }
}

/// Execute `rejected-analysis finalize`.
#[must_use]
pub fn finalize(arguments: &[OsString]) -> ExitCode {
    if help_requested(arguments) {
        print!("{FINALIZE_HELP}");
        return ExitCode::SUCCESS;
    }
    let work_dir = match parse_finalize(arguments) {
        Ok(work_dir) => work_dir,
        Err(code) => return code,
    };
    match rejected_analysis::finalize_artifacts(&work_dir, Utc::now()) {
        Ok(result) => {
            emit_kv("CONFIRMED_COUNT", &result.confirmed_count.to_string());
            emit_kv(
                "ISSUE_BATCH_FILE",
                &result.issue_batch_file.display().to_string(),
            );
            emit_kv(
                "ISSUE_CLUSTER_MAP_FILE",
                &result.issue_cluster_map_file.display().to_string(),
            );
            emit_kv(
                "ISSUE_SENTINEL",
                &result.issue_sentinel.display().to_string(),
            );
            emit_kv(
                "LEDGER_PENDING_FILE",
                &result.ledger_pending_file.display().to_string(),
            );
            emit_kv(
                "INGEST_STATUS_FILE",
                &result.ingest_status_file.display().to_string(),
            );
            emit_kv(
                "ISSUE_OUTPUT_STUB",
                &result.issue_output_stub.display().to_string(),
            );
            emit_kv("LAUNCH_FAILURES", &result.launch_failures.to_string());
            ExitCode::SUCCESS
        }
        Err(error) => {
            eprintln!("rejected-analysis finalize: {error}");
            ExitCode::from(2)
        }
    }
}

/// Execute `rejected-analysis record`.
#[must_use]
pub fn record(arguments: &[OsString]) -> ExitCode {
    if help_requested(arguments) {
        print!("{RECORD_HELP}");
        return ExitCode::SUCCESS;
    }
    let request = match parse_record(arguments) {
        Ok(request) => request,
        Err(code) => return code,
    };
    match record_live(&request) {
        Ok(result) => {
            emit_kv("LEDGER_APPENDED", &result.ledger_appended.to_string());
            emit_kv("ISSUES_CREATED", &result.issues_created.to_string());
            emit_kv(
                "ISSUES_DEDUPLICATED",
                &result.issues_deduplicated.to_string(),
            );
            emit_kv("DISMISSED_COUNT", &result.dismissed_count.to_string());
            emit_kv(
                "UNMAPPED_CONFIRMED",
                if result.unmapped_confirmed {
                    "true"
                } else {
                    "false"
                },
            );
            emit_kv("RECORD_EXIT_RC", &result.exit_code.to_string());
            ExitCode::from(u8::try_from(result.exit_code).unwrap_or(2))
        }
        Err(error) => {
            eprintln!("rejected-analysis record: {error}");
            ExitCode::from(2)
        }
    }
}

fn parse_finalize(arguments: &[OsString]) -> Result<PathBuf, ExitCode> {
    let parsed = parse_with_flags(arguments, &["--work-dir"], &[], 0);
    if let Some(error) = parsed.value_error() {
        return Err(usage_error(
            FINALIZE_USAGE,
            "rejected-analysis finalize",
            error,
            2,
        ));
    }
    if let Some(error) = parsed.error() {
        return Err(usage_error(
            FINALIZE_USAGE,
            "rejected-analysis finalize",
            &error,
            2,
        ));
    }
    option_path(&parsed, "--work-dir").ok_or_else(|| {
        usage_error(
            FINALIZE_USAGE,
            "rejected-analysis finalize",
            &missing(&[("--work-dir", false)]),
            2,
        )
    })
}

fn parse_record(arguments: &[OsString]) -> Result<RecordRequest, ExitCode> {
    let parsed = parse_with_flags(
        arguments,
        &[
            "--work-dir",
            "--issue-output",
            "--issue-verified",
            "--issues-failed",
            "--launch-failures",
            "--repo-root",
        ],
        &[],
        0,
    );
    if let Some(error) = parsed.value_error() {
        return Err(usage_error(
            RECORD_USAGE,
            "rejected-analysis record",
            error,
            2,
        ));
    }
    if let Some(error) = parsed.error() {
        return Err(usage_error(
            RECORD_USAGE,
            "rejected-analysis record",
            &error,
            2,
        ));
    }
    let work_dir = option_path(&parsed, "--work-dir").ok_or_else(|| {
        usage_error(
            RECORD_USAGE,
            "rejected-analysis record",
            &missing(&[("--work-dir", false)]),
            2,
        )
    })?;
    let issue_verified = match option_text(&parsed, "--issue-verified").as_deref() {
        None | Some("") => None,
        Some("true") => Some(true),
        Some("false") => Some(false),
        Some(value) => {
            return Err(usage_error(
                RECORD_USAGE,
                "rejected-analysis record",
                &format!(
                    "argument --issue-verified: invalid choice: '{value}' (choose from 'true', 'false')"
                ),
                2,
            ));
        }
    };
    let issues_failed = parse_i64_option(&parsed, "--issues-failed", 0)?;
    let launch_failures = parse_i64_option(&parsed, "--launch-failures", 0)?;
    Ok(RecordRequest {
        work_dir,
        issue_output: option_path(&parsed, "--issue-output")
            .filter(|path| !path.as_os_str().is_empty()),
        issue_verified,
        issues_failed,
        launch_failures,
        repo_root: option_path(&parsed, "--repo-root").filter(|path| !path.as_os_str().is_empty()),
    })
}

fn parse_i64_option(
    parsed: &ParsedCommandLine,
    option: &str,
    default: i64,
) -> Result<i64, ExitCode> {
    let Some(value) = option_text(parsed, option) else {
        return Ok(default);
    };
    value.parse::<i64>().map_err(|_| {
        usage_error(
            RECORD_USAGE,
            "rejected-analysis record",
            &format!("argument {option}: invalid int value: '{value}'"),
            2,
        )
    })
}

fn record_live(request: &RecordRequest) -> Result<rejected_analysis::RecordResult, String> {
    let repo_root = request
        .repo_root
        .as_deref()
        .map(absolute_path)
        .transpose()
        .map_err(|error| error.to_string())?
        .or_else(|| read_work_root(&request.work_dir, "repo-root.txt"))
        .unwrap_or_else(|| absolute_path(Path::new(".")).unwrap_or_else(|_| PathBuf::from(".")));
    let state_root =
        read_work_root(&request.work_dir, "state-root.txt").unwrap_or_else(|| repo_root.clone());
    let ledger_path = state_root.join(LEDGER_RELATIVE);
    let sidecar_path = state_root.join(VERDICT_SIDECAR_RELATIVE);
    let plan = rejected_analysis::record_plan(
        &request.work_dir,
        request.issue_output.as_deref(),
        request.issue_verified,
        request.issues_failed,
        request.launch_failures,
        Utc::now(),
    )?;
    analysis_state::with_state_lock(&ledger_path, || {
        rejected_analysis::commit_record_ledger(&plan, &ledger_path)
    })?;
    analysis_state::with_state_lock(&sidecar_path, || {
        rejected_analysis::commit_record_sidecar(&plan, &sidecar_path, Utc::now())
    })?;
    Ok(plan.result().clone())
}

fn read_work_root(work_dir: &Path, marker: &str) -> Option<PathBuf> {
    let text = fs::read_to_string(work_dir.join(marker)).ok()?;
    let value = text.trim();
    if value.is_empty() {
        return None;
    }
    absolute_path(Path::new(value)).ok()
}

fn parse_prepare(arguments: &[OsString]) -> Result<PrepareRequest, ExitCode> {
    let parsed = parse_with_flags(
        arguments,
        &["--days", "--n", "--log-root", "--work-dir", "--verify-cap"],
        &[],
        0,
    );
    if let Some(error) = parsed.value_error() {
        return Err(usage_error(
            PREPARE_USAGE,
            "rejected-analysis prepare",
            prepare_value_error(error),
            2,
        ));
    }
    if let Some(error) = parsed.error() {
        return Err(usage_error(
            PREPARE_USAGE,
            "rejected-analysis prepare",
            &error,
            2,
        ));
    }
    let days = parsed
        .entries()
        .iter()
        .rev()
        .find(|(option, _)| *option == "--days" || *option == "--n")
        .and_then(|(_, value)| value.to_str())
        .ok_or_else(|| {
            usage_error(
                PREPARE_USAGE,
                "rejected-analysis prepare",
                &missing(&[("--days/--n", false)]),
                2,
            )
        })?;
    let days = days.parse::<i64>().map_err(|_| {
        usage_error(
            PREPARE_USAGE,
            "rejected-analysis prepare",
            &format!("argument --days/--n: invalid int value: '{days}'"),
            2,
        )
    })?;
    let verify_cap = parsed
        .value("--verify-cap")
        .and_then(|value| value.to_str())
        .map_or(Ok(DEFAULT_VERIFY_CAP as i128), |value| {
            value.parse::<i128>().map_err(|_| {
                usage_error(
                    PREPARE_USAGE,
                    "rejected-analysis prepare",
                    &format!("argument --verify-cap: invalid int value: '{value}'"),
                    2,
                )
            })
        })?;
    Ok(PrepareRequest {
        days,
        log_root: option_path(&parsed, "--log-root").filter(|path| !path.as_os_str().is_empty()),
        work_dir: option_path(&parsed, "--work-dir").filter(|path| !path.as_os_str().is_empty()),
        verify_cap,
    })
}

fn prepare_value_error(error: &str) -> &str {
    match error {
        "argument --days: expected one argument" | "argument --n: expected one argument" => {
            "argument --days/--n: expected one argument"
        }
        _ => error,
    }
}

fn ingest_missing(parsed: &ParsedCommandLine) -> ExitCode {
    let required = [
        "--work-dir",
        "--candidate-id",
        "--output",
        "--launcher-exit",
    ];
    let absent: Vec<(&str, bool)> = required
        .iter()
        .map(|option| (*option, parsed.value(option).is_some()))
        .collect();
    usage_error(
        INGEST_USAGE,
        "rejected-analysis ingest-verdict",
        &missing(&absent),
        2,
    )
}

fn help_requested(arguments: &[OsString]) -> bool {
    arguments.iter().any(|argument| {
        let value = argument.to_string_lossy();
        value == "-h" || value == "--help"
    })
}

fn option_text(parsed: &ParsedCommandLine, option: &str) -> Option<String> {
    parsed
        .value(option)
        .map(|value| value.to_string_lossy().into_owned())
}

fn option_path(parsed: &ParsedCommandLine, option: &str) -> Option<PathBuf> {
    parsed.value(option).map(PathBuf::from)
}

fn prepare_live(request: &PrepareRequest) -> Result<PrepareResult, String> {
    let (repo_root, state_root) = resolve_prepare_context(request.log_root.is_some())?;
    let verify_cap = validate_prepare_bounds(request.days, request.verify_cap)?;
    let logs = resolve_prepare_logs(&repo_root, request.log_root.as_deref())?;
    let work_dir = create_work_dir(request.work_dir.as_deref())?;
    let issues = query_open_issues()?;
    rejected_analysis::prepare_artifacts(
        &repo_root,
        &logs,
        &state_root,
        &work_dir,
        request.days,
        verify_cap,
        &issues,
        Utc::now(),
        |file_path, started_at| file_touched_after(&repo_root, file_path, started_at),
    )
}

fn resolve_prepare_context(log_root_supplied: bool) -> Result<(PathBuf, PathBuf), String> {
    let (repo_root, _origin, _environment) =
        run_log_commands::resolve_repository_environment_path(None)
            .map_err(|_| "could not discover a Git repository root".to_owned())?;
    let repo_root = fs::canonicalize(&repo_root)
        .map_err(|_| "could not discover a Git repository root".to_owned())?;
    if !log_root_supplied {
        let storage =
            run_log_commands::resolve_enabled_storage_path(Some(&repo_root)).map_err(|error| {
                match error {
                    run_log_commands::PreflightFailure::Configuration(error) => error.to_string(),
                    run_log_commands::PreflightFailure::Provider(error) => error.to_string(),
                }
            })?;
        return Ok((
            repo_root,
            analysis_state::storage_root(&storage.client_repo, &storage.storage_origin_id())?,
        ));
    }
    Ok((repo_root.clone(), repo_root))
}

fn validate_prepare_bounds(days: i64, verify_cap: i128) -> Result<usize, String> {
    if days <= 0 {
        return Err("days must be positive".to_owned());
    }
    if verify_cap <= 0 {
        return Err("verify_cap must be positive".to_owned());
    }
    Ok(usize::try_from(verify_cap).unwrap_or(usize::MAX))
}

fn resolve_prepare_logs(
    repo_root: &std::path::Path,
    log_root: Option<&std::path::Path>,
) -> Result<PathBuf, String> {
    let Some(log_root) = log_root else {
        return synchronized_corpus_root(repo_root);
    };
    Ok(if log_root.is_absolute() {
        log_root.to_owned()
    } else {
        repo_root.join(log_root)
    })
}

fn create_work_dir(requested: Option<&std::path::Path>) -> Result<PathBuf, String> {
    let path = if let Some(path) = requested {
        path.to_owned()
    } else {
        let path = env::temp_dir().join(format!("rejected-analysis-{}", Uuid::new_v4().simple()));
        fs::create_dir(&path).map_err(|error| error.to_string())?;
        path
    };
    if !path.exists() {
        fs::create_dir_all(&path).map_err(|error| error.to_string())?;
    }
    let metadata = fs::symlink_metadata(&path).map_err(|error| error.to_string())?;
    if metadata.file_type().is_symlink() || !metadata.is_dir() {
        return Err(format!("work directory is unsafe: {}", path.display()));
    }
    let _canonical = fs::canonicalize(&path).map_err(|error| error.to_string())?;
    Ok(path)
}

fn query_open_issues() -> Result<Vec<OpenIssue>, String> {
    let repository = ambient_repo()
        .ok_or_else(|| "open issue snapshot failed: cannot resolve repository".to_owned())?;
    let reference = repository_ref(&repository)
        .map_err(|()| "open issue snapshot failed: cannot resolve repository".to_owned())?;
    let result = with_github_service(async |service, cancellation| {
        let request = GitHubIssueList::for_dedup(
            reference.clone(),
            GitHubIssueState::Open,
            GitHubIssueBodyMode::Include,
            service.transport_policy(),
        );
        let listed = service
            .list_issues(&request, cancellation)
            .await
            .map_err(|_| "open issue snapshot failed".to_owned())?;
        if listed.truncated {
            eprintln!(
                "WARN: rejected-analysis overlap snapshot was capped at the {ISSUE_DEDUP_LIMIT} most recent open issues; older open issues were omitted"
            );
        }
        Ok::<_, String>(
            listed
                .issues
                .into_iter()
                .filter(|issue| !issue.is_pull_request && issue.state == GitHubIssueState::Open)
                .map(|issue| OpenIssue {
                    title: issue.title,
                    body: issue.body,
                })
                .collect(),
        )
    });
    result.map_err(|_| "open issue snapshot failed".to_owned())
}

fn file_touched_after(repo_root: &std::path::Path, file_path: &str, started_at: &str) -> bool {
    if file_path.is_empty() || started_at.is_empty() {
        return false;
    }
    let Some(since) = parse_timestamp(started_at).map(|time| time.timestamp()) else {
        return false;
    };
    let Some(repository) = GixRepository::discover(repo_root).ok() else {
        return true;
    };
    let Some(head) = repository.head().ok().and_then(|head| match head {
        Head::Symbolic { target, .. } | Head::Detached { target } => Some(target),
        Head::Unborn { .. } => None,
    }) else {
        return true;
    };
    let Ok(commits) = repository.walk_commits(&head, MAX_HISTORY_COMMITS) else {
        return true;
    };
    if commits.len() == MAX_HISTORY_COMMITS {
        return true;
    }
    let path = GitPath::new(file_path.as_bytes().to_vec());
    for commit in commits {
        let Some(commit_time) = repository
            .object(&commit.id)
            .ok()
            .flatten()
            .and_then(|object| commit_time(&object.data))
        else {
            return true;
        };
        if commit_time < since {
            continue;
        }
        let Ok(current) = repository.blob_at_commit(&commit.id, &path) else {
            return true;
        };
        if commit.parents.is_empty() {
            if current.is_some() {
                return true;
            }
            continue;
        }
        for parent in &commit.parents {
            let Ok(previous) = repository.blob_at_commit(parent, &path) else {
                return true;
            };
            if current != previous {
                return true;
            }
        }
    }
    false
}

fn parse_timestamp(value: &str) -> Option<DateTime<Utc>> {
    DateTime::parse_from_rfc3339(value.trim())
        .ok()
        .map(|value| value.with_timezone(&Utc))
}

fn commit_time(data: &[u8]) -> Option<i64> {
    data.split(|byte| *byte == b'\n').find_map(|line| {
        let text = std::str::from_utf8(line).ok()?;
        let remainder = text.strip_prefix("committer ")?;
        let fields: Vec<&str> = remainder.split_whitespace().collect();
        fields
            .get(fields.len().checked_sub(2)?)?
            .parse::<i64>()
            .ok()
    })
}

fn emit_prepare(result: &PrepareResult) {
    emit_kv("WORK_DIR", &result.work_dir.display().to_string());
    emit_kv("VERIFY_COUNT", &result.candidates.len().to_string());
    emit_kv(
        "VERDICTS_FILE",
        &result.work_dir.join("verdicts.jsonl").display().to_string(),
    );
    emit_kv(
        "INGEST_STATUS_FILE",
        &result
            .work_dir
            .join(INGEST_STATUS_FILE)
            .display()
            .to_string(),
    );
    emit_kv(
        "LEDGER_PENDING_FILE",
        &result
            .work_dir
            .join("ledger-pending.tsv")
            .display()
            .to_string(),
    );
    emit_kv(
        "ISSUE_SENTINEL",
        &result
            .work_dir
            .join("issue-completed.sentinel")
            .display()
            .to_string(),
    );
    emit_kv("REPO_ROOT", &result.repo_root.display().to_string());
    for candidate in &result.candidates {
        emit_kv(
            &format!("VERIFY_PROMPT_{}", candidate.candidate_id),
            &candidate.prompt_path.display().to_string(),
        );
    }
}

#[cfg(test)]
mod tests {
    use super::{
        commit_time, create_work_dir, emit_prepare, file_touched_after, help_requested,
        ingest_verdict, option_path, option_text, parse_prepare, parse_timestamp,
        prepare_value_error, resolve_prepare_logs, validate_prepare_bounds,
    };
    use larch_core::rejected_analysis::{Candidate, Finding, PrepareResult, VoteSplit};
    use larch_test_support::{GitFixture, GitRepository};
    use std::{collections::BTreeMap, ffi::OsString, fs, path::Path, process::ExitCode};
    use tempfile::tempdir;

    fn arguments(values: &[&str]) -> Vec<OsString> {
        values.iter().map(OsString::from).collect()
    }

    fn finding() -> Finding {
        Finding {
            finding_hash: "finding-hash".to_owned(),
            concern_hash: "concern-hash".to_owned(),
            source_skill: "implement".to_owned(),
            run_id: "RUN-1".to_owned(),
            round_num: "1".to_owned(),
            canonical_finding_id: "FINDING_1".to_owned(),
            synthetic_id: "REJ_CR1_1".to_owned(),
            reviewer_slots: vec!["cursor".to_owned()],
            dissenting_slots: Vec::new(),
            file_path: "python/example.py".to_owned(),
            line_hint: "12".to_owned(),
            concern: "Missing validation".to_owned(),
            prose_body: "untrusted finding".to_owned(),
            classification_row: BTreeMap::new(),
            vote_split: VoteSplit {
                yes_votes: 1,
                no_votes: 2,
                yes_slots: vec!["cursor".to_owned()],
                no_slots: vec!["codex".to_owned(), "claude".to_owned()],
                high_severity: false,
            },
            started_at: "2026-08-14T12:00:00Z".to_owned(),
            demoted_later_touched: false,
        }
    }

    #[test]
    fn prepare_parser_preserves_aliases_defaults_and_diagnostics() {
        let parsed = parse_prepare(&arguments(&[
            "--n",
            "7",
            "--log-root",
            "logs",
            "--work-dir",
            "work",
            "--verify-cap",
            "42",
        ]))
        .expect("parse compatible prepare arguments");

        assert_eq!(parsed.days, 7);
        assert_eq!(parsed.log_root.as_deref(), Some(Path::new("logs")));
        assert_eq!(parsed.work_dir.as_deref(), Some(Path::new("work")));
        assert_eq!(parsed.verify_cap, 42);
        assert_eq!(
            prepare_value_error("argument --n: expected one argument"),
            "argument --days/--n: expected one argument"
        );
        assert!(parse_prepare(&arguments(&["--days", "nope"])).is_err());
        assert!(parse_prepare(&arguments(&["--days", "7", "--verify-cap", "nope"])).is_err());
        assert!(parse_prepare(&arguments(&["--days"])).is_err());
    }

    #[test]
    fn command_helpers_guard_paths_bounds_and_usage() {
        let fixture = tempdir().expect("fixture directory");
        let root = fixture.path().join("repository");
        fs::create_dir(&root).expect("repository directory");

        assert!(help_requested(&arguments(&["-h"])));
        assert!(help_requested(&arguments(&["--help"])));
        assert!(!help_requested(&arguments(&["--days", "7"])));
        assert_eq!(validate_prepare_bounds(7, 3), Ok(3));
        assert_eq!(
            validate_prepare_bounds(0, 3),
            Err("days must be positive".to_owned())
        );
        assert_eq!(
            validate_prepare_bounds(7, 0),
            Err("verify_cap must be positive".to_owned())
        );
        assert_eq!(
            resolve_prepare_logs(&root, Some(Path::new("logs"))).expect("relative logs"),
            root.join("logs")
        );
        let absolute_logs = fixture.path().join("absolute-logs");
        assert_eq!(
            resolve_prepare_logs(&root, Some(&absolute_logs)).expect("absolute logs"),
            absolute_logs
        );

        let requested = fixture.path().join("work");
        assert_eq!(
            create_work_dir(Some(&requested)).expect("create requested work directory"),
            requested
        );
        let regular_file = fixture.path().join("regular-file");
        fs::write(&regular_file, "not a directory").expect("regular file");
        assert!(create_work_dir(Some(&regular_file)).is_err());

        let parsed = super::parse_with_flags(
            &arguments(&["--output", "result.json"]),
            &["--output"],
            &[],
            0,
        );
        assert_eq!(
            option_text(&parsed, "--output").as_deref(),
            Some("result.json")
        );
        assert_eq!(
            option_path(&parsed, "--output").as_deref(),
            Some(Path::new("result.json"))
        );
    }

    #[test]
    fn history_probe_tracks_recent_file_changes_without_false_positives() {
        let fixture = GitRepository::builder(GitFixture::Refs)
            .build()
            .expect("fixture repository");
        let repository = fixture.root();

        assert!(file_touched_after(
            repository,
            "tracked.txt",
            "2000-01-01T00:00:00Z"
        ));
        assert!(!file_touched_after(
            repository,
            "tracked.txt",
            "2002-01-01T00:00:00Z"
        ));
        assert!(!file_touched_after(
            repository,
            "missing.txt",
            "2000-01-01T00:00:00Z"
        ));
        let not_repository = fixture.workspace_root().join("not-a-repository");
        fs::create_dir(&not_repository).expect("non-repository directory");
        assert!(file_touched_after(
            &not_repository,
            "tracked.txt",
            "2000-01-01T00:00:00Z"
        ));
        assert!(!file_touched_after(repository, "", "2000-01-01T00:00:00Z"));
        assert!(!file_touched_after(
            repository,
            "tracked.txt",
            "not a timestamp"
        ));
        assert_eq!(
            parse_timestamp(" 2024-01-01T00:00:00Z ").map(|time| time.timestamp()),
            Some(1_704_067_200)
        );
        assert_eq!(
            commit_time(b"tree deadbeef\ncommitter Larch <larch@example.test> 1704067200 +0000\n"),
            Some(1_704_067_200)
        );
        assert_eq!(commit_time(b"committer malformed\n"), None);
    }

    #[test]
    fn command_boundaries_preserve_help_and_ingest_diagnostics() {
        let fixture = tempdir().expect("fixture directory");
        assert_eq!(ingest_verdict(&arguments(&["--help"])), ExitCode::SUCCESS);
        assert_eq!(ingest_verdict(&arguments(&[])), ExitCode::from(2));
        assert_eq!(
            ingest_verdict(&arguments(&[
                "--work-dir",
                &fixture.path().display().to_string(),
                "--candidate-id",
                "C1",
                "--output",
                "result.json",
                "--launcher-exit",
                "not-an-integer",
            ])),
            ExitCode::from(2)
        );
        assert_eq!(
            ingest_verdict(&arguments(&[
                "--work-dir",
                &fixture.path().display().to_string(),
                "--candidate-id",
                "C1",
                "--output",
                "result.json",
                "--launcher-exit",
                "0",
            ])),
            ExitCode::from(2)
        );
    }

    #[test]
    fn preparation_output_lists_every_published_wire_path() {
        let fixture = tempdir().expect("fixture directory");
        emit_prepare(&PrepareResult {
            work_dir: fixture.path().join("work"),
            repo_root: fixture.path().join("repository"),
            candidates: vec![Candidate {
                candidate_id: "C1".to_owned(),
                finding: finding(),
                prompt_path: fixture.path().join("work/verify-C1.md"),
            }],
        });
    }
}
