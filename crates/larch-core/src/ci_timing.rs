//! CI timing collection over the typed GitHub Actions service.

use crate::{
    GitHubActionsError, GitHubActionsErrorKind, GitHubActionsService, GitHubRepositoryRef,
    ProcessCancellation, WorkflowLogArchive, WorkflowRunFilters,
    github_actions::bounded_workflow_log_archive,
};
use regex::Regex;
use serde::Serialize;
use std::{
    collections::{HashMap, HashSet, hash_map::Entry},
    io::Read,
    sync::LazyLock,
};

const SCHEMA_VERSION: u8 = 2;
const MAX_ARCHIVE_ENTRY_NAME_BYTES: usize = 4_096;
const MAX_TIMING_LABEL_BYTES: usize = 16_384;
const MAX_TIMING_REPORT_LABEL_BYTES: usize = 32 * 1024 * 1024;
const MAX_TIMING_REPORT_ROWS: usize = 100_000;
const HARNESS_KIND: &str = "harness";
const PYTEST_KIND: &str = "pytest";
const JOBS_KIND: &str = "jobs";
const HARNESS_SENTINEL: &str = "LARCH_HARNESS_TIMING\t";
const HARNESS_BOOTSTRAP_SENTINEL: &str = "LARCH_HARNESS_BOOTSTRAP\t";

static HARNESS_JOB_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"test-harnesses \((\d+)\)").expect("valid harness job regex"));
static SECONDS_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^(\d+(?:\.\d+)?)s$").expect("valid seconds regex"));
static PYTEST_JOB_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"\bpython-tests\b").expect("valid pytest job regex"));
static PYTEST_JOB_SHARD_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"python-tests\s*\([^)]*,\s*(\d+)\)").expect("valid pytest shard regex")
});
static PYTEST_STEP_SHARD_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?i-u:shard)\s+(\d+)\s+(?i-u:of)\s+(\d+)").expect("valid pytest step shard regex")
});
static PYTEST_DURATION_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^(\d+(?:\.\d+)?)s\s+(call|setup|teardown)\s+(.+)$")
        .expect("valid pytest duration regex")
});
static PYTEST_BANNER_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?i-u:slowest)\s+(?:\d+\s+)?(?i-u:durations)").expect("valid pytest banner regex")
});
static PYTEST_ENV_SHARD_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^\s*PYTEST_SHARD_ID:\s*(\d+)\s*$").expect("valid pytest env shard regex")
});
static PYTEST_ENV_TOTAL_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^\s*PYTEST_SHARD_COUNT:\s*(\d+)\s*$").expect("valid pytest env total regex")
});
static TIMESTAMP_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^\d{4}-\d{2}-\d{2}T\S+Z\s+").expect("valid timestamp regex"));

/// Maximum workflow runs accepted by one CI timing operation.
pub const MAX_CI_TIMING_RUNS: usize = 20;
/// Maximum required harness targets accepted by one CI timing operation.
pub const MAX_CI_TIMING_REQUIRED_TARGETS: usize = 4_096;

/// Run selection shared by the harness and pytest collectors.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum CiTimingRunSelection {
    /// Fetch recent successful runs with the legacy branch and workflow filters.
    Recent {
        branch: String,
        workflow: String,
        limit: usize,
    },
    /// Fetch logs for the exact completed run identifiers supplied by the caller.
    Explicit(Vec<u64>),
}

/// One legacy `LARCH_HARNESS_TIMING` row.
#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct HarnessTimingRow {
    pub run_id: u64,
    pub shard: u32,
    pub target: String,
    pub seconds: f64,
}

/// One timer-bootstrap diagnostic paired with a harness target execution.
#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct HarnessBootstrapRow {
    pub run_id: u64,
    pub shard: u32,
    pub target: String,
    pub bootstrap_kind: String,
    pub seconds: f64,
}

/// One legacy pytest `--durations=0` call row.
#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct PytestTimingRow {
    pub run_id: u64,
    pub shard: u32,
    pub nodeid: String,
    pub seconds: f64,
    pub attempt: u32,
    pub shard_total: Option<u32>,
}

/// One real GitHub Actions harness-job wall-clock row.
#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct JobTimingRow {
    pub run_id: u64,
    pub shard: u32,
    pub seconds: f64,
}

/// A harness target median, preserving first-seen ordering.
#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct TargetTiming {
    pub target: String,
    pub seconds: f64,
}

/// A pytest nodeid median, preserving first-seen ordering.
#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct NodeidTiming {
    pub nodeid: String,
    pub seconds: f64,
}

/// A per-shard median.
#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct ShardTiming {
    pub shard: u32,
    pub seconds: f64,
}

/// Stable machine output for `larch ci-timing harness`.
#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct HarnessTimingReport {
    schema_version: u8,
    kind: &'static str,
    pub sampled_run_ids: Vec<u64>,
    pub rows: Vec<HarnessTimingRow>,
    pub bootstrap_rows: Vec<HarnessBootstrapRow>,
    pub target_medians: Vec<TargetTiming>,
    pub shard_medians: Vec<ShardTiming>,
    pub untimed_targets: Vec<String>,
    pub skipped_run_ids: Vec<u64>,
}

/// Stable machine output for `larch ci-timing pytest`.
#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct PytestTimingReport {
    schema_version: u8,
    kind: &'static str,
    pub sampled_run_ids: Vec<u64>,
    pub rows: Vec<PytestTimingRow>,
    pub nodeid_medians: Vec<NodeidTiming>,
    pub shard_medians: Vec<ShardTiming>,
    pub observed_shard_count: Option<u32>,
    pub skipped_run_ids: Vec<u64>,
}

/// Stable machine output for `larch ci-timing jobs`.
#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct JobTimingReport {
    schema_version: u8,
    kind: &'static str,
    pub sampled_run_ids: Vec<u64>,
    pub rows: Vec<JobTimingRow>,
    pub shard_medians: Vec<ShardTiming>,
    pub skipped_run_ids: Vec<u64>,
}

/// Fetch, parse, and aggregate harness timing rows.
///
/// # Errors
///
/// Returns a typed GitHub Actions error when recent-run discovery is unavailable
/// or the operation is cancelled. Individual unreadable run archives are
/// reported in `skipped_run_ids`.
pub async fn collect_harness_timing(
    service: &dyn GitHubActionsService,
    repository: &GitHubRepositoryRef,
    selection: &CiTimingRunSelection,
    required_targets: &[String],
    cancellation: &dyn ProcessCancellation,
) -> Result<HarnessTimingReport, GitHubActionsError> {
    validate_required_targets(required_targets)?;
    let sampled_run_ids = select_run_ids(service, repository, selection, cancellation).await?;
    let mut rows = Vec::new();
    let mut bootstrap_rows = Vec::new();
    let mut retained_label_bytes = 0;
    let mut skipped_run_ids = Vec::new();
    for run_id in &sampled_run_ids {
        let archive = match service
            .download_workflow_logs(repository, *run_id, cancellation)
            .await
        {
            Ok(archive) => archive,
            Err(error) if error.kind() == GitHubActionsErrorKind::Cancelled => return Err(error),
            Err(_) => {
                skipped_run_ids.push(*run_id);
                continue;
            }
        };
        match parse_harness_archive(&archive, *run_id) {
            Ok(mut parsed) => match timing_rows_fit(
                rows.len().saturating_add(bootstrap_rows.len()),
                retained_label_bytes,
                parsed
                    .rows
                    .len()
                    .saturating_add(parsed.bootstrap_rows.len()),
                parsed
                    .rows
                    .iter()
                    .map(|row| row.target.as_str())
                    .chain(parsed.bootstrap_rows.iter().map(|row| row.target.as_str())),
            ) {
                Some(next_label_bytes) => {
                    retained_label_bytes = next_label_bytes;
                    rows.append(&mut parsed.rows);
                    bootstrap_rows.append(&mut parsed.bootstrap_rows);
                }
                None => skipped_run_ids.push(*run_id),
            },
            Err(()) => skipped_run_ids.push(*run_id),
        }
    }
    Ok(harness_report(
        sampled_run_ids,
        rows,
        bootstrap_rows,
        required_targets,
        skipped_run_ids,
    ))
}

/// Fetch, parse, and aggregate pytest timing rows.
///
/// # Errors
///
/// Returns a typed GitHub Actions error when recent-run discovery is unavailable
/// or the operation is cancelled. Individual unreadable run archives are
/// reported in `skipped_run_ids`.
pub async fn collect_pytest_timing(
    service: &dyn GitHubActionsService,
    repository: &GitHubRepositoryRef,
    selection: &CiTimingRunSelection,
    cancellation: &dyn ProcessCancellation,
) -> Result<PytestTimingReport, GitHubActionsError> {
    let sampled_run_ids = select_run_ids(service, repository, selection, cancellation).await?;
    let mut rows = Vec::new();
    let mut retained_label_bytes = 0;
    let mut skipped_run_ids = Vec::new();
    for run_id in &sampled_run_ids {
        let archive = match service
            .download_workflow_logs(repository, *run_id, cancellation)
            .await
        {
            Ok(archive) => archive,
            Err(error) if error.kind() == GitHubActionsErrorKind::Cancelled => return Err(error),
            Err(_) => {
                skipped_run_ids.push(*run_id);
                continue;
            }
        };
        match parse_pytest_archive(&archive, *run_id) {
            Ok(mut parsed) => match timing_rows_fit(
                rows.len(),
                retained_label_bytes,
                parsed.len(),
                parsed.iter().map(|row| row.nodeid.as_str()),
            ) {
                Some(next_label_bytes) => {
                    retained_label_bytes = next_label_bytes;
                    rows.append(&mut parsed);
                }
                None => skipped_run_ids.push(*run_id),
            },
            Err(()) => skipped_run_ids.push(*run_id),
        }
    }
    Ok(pytest_report(sampled_run_ids, rows, skipped_run_ids))
}

/// Fetch and aggregate real harness-job wall-clock durations.
///
/// # Errors
///
/// Returns a typed GitHub Actions error when the operation is cancelled.
/// Individual unreadable or ambiguous jobs responses are reported in
/// `skipped_run_ids`.
pub async fn collect_job_timing(
    service: &dyn GitHubActionsService,
    repository: &GitHubRepositoryRef,
    run_ids: &[u64],
    cancellation: &dyn ProcessCancellation,
) -> Result<JobTimingReport, GitHubActionsError> {
    validate_run_ids(run_ids)?;
    let mut rows = Vec::new();
    let mut skipped_run_ids = Vec::new();
    for &run_id in run_ids {
        let jobs = match service
            .workflow_jobs(repository, run_id, cancellation)
            .await
        {
            Ok(jobs) => jobs,
            Err(error) if error.kind() == GitHubActionsErrorKind::Cancelled => return Err(error),
            Err(_) => {
                skipped_run_ids.push(run_id);
                continue;
            }
        };
        let mut run_rows = Vec::<JobTimingRow>::new();
        let mut seen_shards = HashSet::<u32>::new();
        let mut has_duplicate_shard = false;
        for job in jobs {
            let (Some(shard), Some(seconds)) = (
                job.harness_shard().filter(|shard| *shard > 0),
                job.wall_clock_seconds
                    .filter(|seconds| seconds.is_finite() && *seconds > 0.0),
            ) else {
                continue;
            };
            if !seen_shards.insert(shard) {
                has_duplicate_shard = true;
                break;
            }
            run_rows.push(JobTimingRow {
                run_id,
                shard,
                seconds,
            });
        }
        if has_duplicate_shard {
            skipped_run_ids.push(run_id);
            continue;
        }
        rows.extend(run_rows);
    }
    Ok(job_report(run_ids.to_vec(), rows, skipped_run_ids))
}

async fn select_run_ids(
    service: &dyn GitHubActionsService,
    repository: &GitHubRepositoryRef,
    selection: &CiTimingRunSelection,
    cancellation: &dyn ProcessCancellation,
) -> Result<Vec<u64>, GitHubActionsError> {
    match selection {
        CiTimingRunSelection::Explicit(run_ids) => {
            validate_run_ids(run_ids)?;
            Ok(run_ids.clone())
        }
        CiTimingRunSelection::Recent {
            branch,
            workflow,
            limit,
        } => {
            if !(1..=MAX_CI_TIMING_RUNS).contains(limit) {
                return Err(invalid_input(format!(
                    "CI timing run limit must be from 1 through {MAX_CI_TIMING_RUNS}"
                )));
            }
            let filters = WorkflowRunFilters {
                branch: Some(branch.clone()),
                workflow: Some(workflow.clone()),
                status: Some(String::from("success")),
                limit: *limit,
                ..WorkflowRunFilters::default()
            };
            let runs = service
                .list_workflow_runs(repository, &filters, cancellation)
                .await?;
            Ok(runs
                .into_iter()
                .filter(|run| {
                    run.status == "completed" && run.conclusion.as_deref() == Some("success")
                })
                .take(*limit)
                .map(|run| run.database_id)
                .collect())
        }
    }
}

fn validate_run_ids(run_ids: &[u64]) -> Result<(), GitHubActionsError> {
    if run_ids.len() > MAX_CI_TIMING_RUNS {
        return Err(invalid_input(format!(
            "at most {MAX_CI_TIMING_RUNS} workflow runs are allowed"
        )));
    }
    let mut seen = HashSet::new();
    if run_ids
        .iter()
        .any(|run_id| *run_id == 0 || !seen.insert(*run_id))
    {
        return Err(invalid_input(
            "workflow run identifiers must be positive and unique",
        ));
    }
    Ok(())
}

fn validate_required_targets(required_targets: &[String]) -> Result<(), GitHubActionsError> {
    if required_targets.len() > MAX_CI_TIMING_REQUIRED_TARGETS {
        return Err(invalid_input(format!(
            "at most {MAX_CI_TIMING_REQUIRED_TARGETS} required targets are allowed"
        )));
    }
    let mut total_bytes = 0_usize;
    for target in required_targets {
        if target.len() > MAX_TIMING_LABEL_BYTES {
            return Err(invalid_input("a required target exceeds the length limit"));
        }
        total_bytes = total_bytes
            .checked_add(target.len())
            .filter(|total| *total <= MAX_TIMING_REPORT_LABEL_BYTES)
            .ok_or_else(|| invalid_input("required targets exceed the total length limit"))?;
    }
    Ok(())
}

fn invalid_input(detail: impl AsRef<str>) -> GitHubActionsError {
    GitHubActionsError::new(GitHubActionsErrorKind::InvalidInput, detail)
}

fn timing_rows_fit<'a>(
    retained_rows: usize,
    retained_label_bytes: usize,
    added_rows: usize,
    labels: impl Iterator<Item = &'a str>,
) -> Option<usize> {
    if retained_rows.checked_add(added_rows)? > MAX_TIMING_REPORT_ROWS {
        return None;
    }
    let mut total_bytes = retained_label_bytes;
    for label in labels {
        if label.len() > MAX_TIMING_LABEL_BYTES {
            return None;
        }
        total_bytes = total_bytes.checked_add(label.len())?;
        if total_bytes > MAX_TIMING_REPORT_LABEL_BYTES {
            return None;
        }
    }
    Some(total_bytes)
}

#[derive(Debug)]
struct ArchiveLogEntry {
    job_name: String,
    step_name: String,
    contents: String,
}

struct ParsedHarnessArchive {
    rows: Vec<HarnessTimingRow>,
    bootstrap_rows: Vec<HarnessBootstrapRow>,
}

fn archive_log_entries(archive: &WorkflowLogArchive) -> Result<Vec<ArchiveLogEntry>, ()> {
    let mut zip = bounded_workflow_log_archive(archive)?;
    let mut total_bytes = 0_usize;
    let mut entries = Vec::new();
    for index in 0..zip.len() {
        let entry = zip.by_index(index).map_err(|_| ())?;
        if entry.is_dir() {
            continue;
        }
        let name = entry.name().to_owned();
        if name.len() > MAX_ARCHIVE_ENTRY_NAME_BYTES {
            return Err(());
        }
        let remaining = WorkflowLogArchive::MAX_BYTES.saturating_sub(total_bytes);
        let remaining_u64 = u64::try_from(remaining).unwrap_or(u64::MAX);
        if entry.size() > remaining_u64 {
            return Err(());
        }
        let mut contents = Vec::new();
        entry
            .take(remaining_u64.saturating_add(1))
            .read_to_end(&mut contents)
            .map_err(|_| ())?;
        if contents.len() > remaining {
            return Err(());
        }
        total_bytes += contents.len();
        let (job_name, step_name) = if let Some((job_name, step_path)) = name.split_once('/') {
            (job_name.to_owned(), normalize_step_name(step_path))
        } else if let Some(job_name) = flat_job_name(&name) {
            (job_name.to_owned(), String::new())
        } else {
            continue;
        };
        entries.push(ArchiveLogEntry {
            job_name,
            step_name,
            contents: String::from_utf8_lossy(&contents).into_owned(),
        });
    }
    let flat_jobs = entries
        .iter()
        .filter(|entry| entry.step_name.is_empty())
        .map(|entry| entry.job_name.clone())
        .collect::<HashSet<_>>();
    if !flat_jobs.is_empty() {
        entries.retain(|entry| entry.step_name.is_empty() || !flat_jobs.contains(&entry.job_name));
    }
    Ok(entries)
}

fn flat_job_name(path: &str) -> Option<&str> {
    let stem = path.strip_suffix(".txt")?;
    let (prefix, job_name) = stem.split_once('_')?;
    (!job_name.is_empty() && prefix.bytes().all(|byte| byte.is_ascii_digit())).then_some(job_name)
}

fn normalize_step_name(path: &str) -> String {
    let file_name = path.rsplit('/').next().unwrap_or(path);
    let stem = file_name.strip_suffix(".txt").unwrap_or(file_name);
    stem.split_once('_')
        .map_or(stem, |(prefix, remainder)| {
            if !prefix.is_empty() && prefix.bytes().all(|byte| byte.is_ascii_digit()) {
                remainder
            } else {
                stem
            }
        })
        .to_owned()
}

fn parse_harness_archive(
    archive: &WorkflowLogArchive,
    run_id: u64,
) -> Result<ParsedHarnessArchive, ()> {
    let mut rows = Vec::new();
    let mut bootstrap_rows = Vec::new();
    for entry in archive_log_entries(archive)? {
        let Some(shard) = capture_u32(&HARNESS_JOB_RE, &entry.job_name, 1) else {
            continue;
        };
        for line in entry.contents.lines() {
            let Some(index) = line.find(HARNESS_SENTINEL) else {
                continue;
            };
            let rest = &line[index + HARNESS_SENTINEL.len()..];
            let Some((target, seconds_text)) = rest.split_once('\t') else {
                continue;
            };
            let Some(seconds) = parse_seconds(seconds_text.trim()) else {
                continue;
            };
            rows.push(HarnessTimingRow {
                run_id,
                shard,
                target: target.trim().to_owned(),
                seconds,
            });
        }
        for line in entry.contents.lines() {
            let Some(index) = line.find(HARNESS_BOOTSTRAP_SENTINEL) else {
                continue;
            };
            let rest = &line[index + HARNESS_BOOTSTRAP_SENTINEL.len()..];
            let mut fields = rest.split('\t');
            let (Some(target), Some(bootstrap_kind), Some(seconds_text), None) =
                (fields.next(), fields.next(), fields.next(), fields.next())
            else {
                continue;
            };
            if !matches!(bootstrap_kind.trim(), "cold" | "warm" | "unknown") {
                continue;
            }
            let Some(seconds) = parse_seconds(seconds_text.trim()) else {
                continue;
            };
            bootstrap_rows.push(HarnessBootstrapRow {
                run_id,
                shard,
                target: target.trim().to_owned(),
                bootstrap_kind: bootstrap_kind.trim().to_owned(),
                seconds,
            });
        }
    }
    Ok(ParsedHarnessArchive {
        rows,
        bootstrap_rows,
    })
}

fn parse_pytest_archive(
    archive: &WorkflowLogArchive,
    run_id: u64,
) -> Result<Vec<PytestTimingRow>, ()> {
    let mut rows = Vec::new();
    let mut attempts = HashMap::<(String, String), u32>::new();
    for entry in archive_log_entries(archive)? {
        if !PYTEST_JOB_RE.is_match(&entry.job_name) {
            continue;
        }
        let Some((shard, shard_total)) =
            pytest_shard(&entry.job_name, &entry.step_name, &entry.contents)
        else {
            continue;
        };
        let key = (entry.job_name, entry.step_name);
        for line in entry.contents.lines() {
            let content = TIMESTAMP_RE.replace(line.trim(), "");
            if PYTEST_BANNER_RE.is_match(&content) {
                let attempt = attempts.entry(key.clone()).or_default();
                *attempt = attempt.saturating_add(1);
                continue;
            }
            let Some(captures) = PYTEST_DURATION_RE.captures(&content) else {
                continue;
            };
            if captures.get(2).map(|value| value.as_str()) != Some("call") {
                continue;
            }
            let attempt = attempts.get(&key).copied().unwrap_or_default();
            if attempt == 0 {
                continue;
            }
            let Some(seconds) = captures
                .get(1)
                .and_then(|value| value.as_str().parse::<f64>().ok())
                .filter(|value| value.is_finite())
            else {
                continue;
            };
            let Some(nodeid) = captures.get(3).map(|value| value.as_str().trim()) else {
                continue;
            };
            rows.push(PytestTimingRow {
                run_id,
                shard,
                nodeid: nodeid.to_owned(),
                seconds,
                attempt,
                shard_total,
            });
        }
    }
    Ok(rows)
}

fn pytest_shard(job_name: &str, step_name: &str, contents: &str) -> Option<(u32, Option<u32>)> {
    if let Some(captures) = PYTEST_STEP_SHARD_RE.captures(step_name) {
        return Some((
            captures.get(1)?.as_str().parse().ok()?,
            Some(captures.get(2)?.as_str().parse().ok()?),
        ));
    }
    let shard = capture_u32(&PYTEST_JOB_SHARD_RE, job_name, 1)?;
    let mut logged_shards = HashSet::new();
    let mut logged_totals = HashSet::new();
    for line in contents.lines() {
        let content = TIMESTAMP_RE.replace(line.trim(), "");
        if let Some(value) = capture_u32(&PYTEST_ENV_SHARD_RE, &content, 1) {
            logged_shards.insert(value);
        }
        if let Some(value) = capture_u32(&PYTEST_ENV_TOTAL_RE, &content, 1) {
            logged_totals.insert(value);
        }
    }
    let shard_total =
        (logged_shards.len() == 1 && logged_shards.contains(&shard) && logged_totals.len() == 1)
            .then(|| logged_totals.into_iter().next())
            .flatten();
    Some((shard, shard_total))
}

fn capture_u32(regex: &Regex, text: &str, group: usize) -> Option<u32> {
    regex
        .captures(text)?
        .get(group)?
        .as_str()
        .parse()
        .ok()
        .filter(|value| *value > 0)
}

fn parse_seconds(value: &str) -> Option<f64> {
    SECONDS_RE
        .captures(value)?
        .get(1)?
        .as_str()
        .parse::<f64>()
        .ok()
        .filter(|seconds| seconds.is_finite())
}

fn harness_report(
    sampled_run_ids: Vec<u64>,
    rows: Vec<HarnessTimingRow>,
    bootstrap_rows: Vec<HarnessBootstrapRow>,
    required_targets: &[String],
    skipped_run_ids: Vec<u64>,
) -> HarnessTimingReport {
    let target_medians = harness_target_medians(&rows);
    let shard_medians = harness_shard_medians(&rows);
    let timed = target_medians
        .iter()
        .map(|row| row.target.as_str())
        .collect::<HashSet<_>>();
    let mut seen = HashSet::<&str>::new();
    let untimed_targets = required_targets
        .iter()
        .filter(|target| !timed.contains(target.as_str()) && seen.insert(target.as_str()))
        .cloned()
        .collect();
    HarnessTimingReport {
        schema_version: SCHEMA_VERSION,
        kind: HARNESS_KIND,
        sampled_run_ids,
        rows,
        bootstrap_rows,
        target_medians,
        shard_medians,
        untimed_targets,
        skipped_run_ids,
    }
}

fn pytest_report(
    sampled_run_ids: Vec<u64>,
    rows: Vec<PytestTimingRow>,
    skipped_run_ids: Vec<u64>,
) -> PytestTimingReport {
    let groups = pytest_groups(&rows);
    let latest_rows = groups
        .iter()
        .flat_map(|group| latest_pytest_attempt(group))
        .collect::<Vec<_>>();
    let nodeid_medians = named_medians(
        latest_rows
            .iter()
            .map(|row| (row.nodeid.as_str(), row.seconds)),
    )
    .into_iter()
    .map(|(nodeid, seconds)| NodeidTiming { nodeid, seconds })
    .collect::<Vec<_>>();
    let shard_medians = pytest_shard_medians(&groups);
    let observed_shard_count = observed_shard_count(&rows);
    PytestTimingReport {
        schema_version: SCHEMA_VERSION,
        kind: PYTEST_KIND,
        sampled_run_ids,
        rows,
        nodeid_medians,
        shard_medians,
        observed_shard_count,
        skipped_run_ids,
    }
}

fn job_report(
    sampled_run_ids: Vec<u64>,
    rows: Vec<JobTimingRow>,
    skipped_run_ids: Vec<u64>,
) -> JobTimingReport {
    let shard_medians = shard_medians(rows.iter().map(|row| (row.shard, row.seconds)));
    JobTimingReport {
        schema_version: SCHEMA_VERSION,
        kind: JOBS_KIND,
        sampled_run_ids,
        rows,
        shard_medians,
        skipped_run_ids,
    }
}

fn named_medians<'a>(values: impl Iterator<Item = (&'a str, f64)>) -> Vec<(String, f64)> {
    let mut groups = Vec::<(String, Vec<f64>)>::new();
    let mut indexes = HashMap::<String, usize>::new();
    for (name, seconds) in values {
        let index = match indexes.entry(name.to_owned()) {
            Entry::Occupied(entry) => *entry.get(),
            Entry::Vacant(entry) => {
                let index = groups.len();
                groups.push((entry.key().clone(), Vec::new()));
                entry.insert(index);
                index
            }
        };
        groups[index].1.push(seconds);
    }
    groups
        .into_iter()
        .map(|(name, values)| (name, median(values)))
        .collect()
}

fn shard_medians(values: impl Iterator<Item = (u32, f64)>) -> Vec<ShardTiming> {
    let mut groups = Vec::<(u32, Vec<f64>)>::new();
    let mut indexes = HashMap::<u32, usize>::new();
    for (shard, seconds) in values {
        let index = match indexes.entry(shard) {
            Entry::Occupied(entry) => *entry.get(),
            Entry::Vacant(entry) => {
                let index = groups.len();
                groups.push((shard, Vec::new()));
                entry.insert(index);
                index
            }
        };
        groups[index].1.push(seconds);
    }
    groups
        .into_iter()
        .map(|(shard, values)| ShardTiming {
            shard,
            seconds: median(values),
        })
        .collect()
}

fn median(mut values: Vec<f64>) -> f64 {
    values.sort_by(f64::total_cmp);
    let midpoint = values.len() / 2;
    if values.len().is_multiple_of(2) {
        values[midpoint - 1] / 2.0 + values[midpoint] / 2.0
    } else {
        values[midpoint]
    }
}

fn harness_groups(rows: &[HarnessTimingRow]) -> Vec<Vec<&HarnessTimingRow>> {
    let mut groups = Vec::<Vec<&HarnessTimingRow>>::new();
    let mut indexes = HashMap::<(u64, u32), usize>::new();
    for row in rows {
        let key = (row.run_id, row.shard);
        let index = match indexes.entry(key) {
            Entry::Occupied(entry) => *entry.get(),
            Entry::Vacant(entry) => {
                let index = groups.len();
                groups.push(Vec::new());
                entry.insert(index);
                index
            }
        };
        groups[index].push(row);
    }
    groups
}

fn harness_shard_medians(rows: &[HarnessTimingRow]) -> Vec<ShardTiming> {
    shard_medians(harness_groups(rows).into_iter().map(|group| {
        let shard = group[0].shard;
        (shard, group.iter().map(|row| row.seconds).sum())
    }))
}

fn harness_target_medians(rows: &[HarnessTimingRow]) -> Vec<TargetTiming> {
    let mut target_totals = Vec::<(String, f64)>::new();
    for shard_rows in harness_groups(rows) {
        let mut totals = Vec::<(String, f64)>::new();
        let mut indexes = HashMap::<String, usize>::new();
        for row in shard_rows {
            let index = match indexes.entry(row.target.clone()) {
                Entry::Occupied(entry) => *entry.get(),
                Entry::Vacant(entry) => {
                    let index = totals.len();
                    totals.push((entry.key().clone(), 0.0));
                    entry.insert(index);
                    index
                }
            };
            totals[index].1 += row.seconds;
        }
        target_totals.extend(totals);
    }
    named_medians(
        target_totals
            .iter()
            .map(|(target, seconds)| (target.as_str(), *seconds)),
    )
    .into_iter()
    .map(|(target, seconds)| TargetTiming { target, seconds })
    .collect()
}

fn pytest_groups(rows: &[PytestTimingRow]) -> Vec<Vec<&PytestTimingRow>> {
    let mut groups = Vec::<Vec<&PytestTimingRow>>::new();
    let mut indexes = HashMap::<(u64, u32), usize>::new();
    for row in rows {
        let key = (row.run_id, row.shard);
        let index = match indexes.entry(key) {
            Entry::Occupied(entry) => *entry.get(),
            Entry::Vacant(entry) => {
                let index = groups.len();
                groups.push(Vec::new());
                entry.insert(index);
                index
            }
        };
        groups[index].push(row);
    }
    groups
}

fn latest_pytest_attempt<'a>(rows: &'a [&'a PytestTimingRow]) -> &'a [&'a PytestTimingRow] {
    let Some(last) = rows.last() else {
        return rows;
    };
    let attempt = last.attempt;
    let start = rows
        .iter()
        .rposition(|row| row.attempt != attempt)
        .map_or(0, |index| index + 1);
    &rows[start..]
}

fn pytest_shard_medians(groups: &[Vec<&PytestTimingRow>]) -> Vec<ShardTiming> {
    shard_medians(groups.iter().filter_map(|group| {
        let latest = latest_pytest_attempt(group);
        let first = latest.first()?;
        Some((first.shard, latest.iter().map(|row| row.seconds).sum()))
    }))
}

fn observed_shard_count(rows: &[PytestTimingRow]) -> Option<u32> {
    let totals = rows
        .iter()
        .filter_map(|row| row.shard_total)
        .collect::<HashSet<_>>();
    if totals.len() == 1 {
        return totals.into_iter().next();
    }
    if !totals.is_empty() || rows.is_empty() {
        return None;
    }
    rows.iter().map(|row| row.shard).max()
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::{Cursor, Write as _};

    fn archive(entries: &[(&str, &str)]) -> WorkflowLogArchive {
        let mut writer = zip::ZipWriter::new(Cursor::new(Vec::new()));
        for (name, contents) in entries {
            writer
                .start_file(name, zip::write::SimpleFileOptions::default())
                .expect("start fixture entry");
            writer
                .write_all(contents.as_bytes())
                .expect("write fixture entry");
        }
        WorkflowLogArchive::new(writer.finish().expect("finish fixture").into_inner())
    }

    #[test]
    fn recorded_harness_fixture_preserves_aggregate_rows_medians_and_wire_order() {
        let fixture = archive(&[
            (
                "23_test-harnesses (1).txt",
                "2026-01-01T00:00:00Z LARCH_HARNESS_TIMING\ttest-a\t10.00s\n\
                 LARCH_HARNESS_TIMING\ttest-b\t5s\n\
                 LARCH_HARNESS_TIMING\ttest-a\t12.00s\n\
                 LARCH_HARNESS_TIMING\ttest-b\t8.00s\n\
                 LARCH_HARNESS_BOOTSTRAP\ttest-a\tcold\t1.00s\n\
                 LARCH_HARNESS_BOOTSTRAP\ttest-b\twarm\t0.01s\n",
            ),
            (
                "26_test-harnesses (2).txt",
                "LARCH_HARNESS_TIMING\ttest-c\t3.00s\n",
            ),
            (
                "test-harnesses (1)/10_duplicate-step.txt",
                "LARCH_HARNESS_TIMING\ttest-a\t100.00s\n",
            ),
        ]);
        let parsed = parse_harness_archive(&fixture, 42).expect("parse fixture");
        let report = harness_report(
            vec![42],
            parsed.rows,
            parsed.bootstrap_rows,
            &[String::from("test-a"), String::from("test-missing")],
            Vec::new(),
        );

        assert_eq!(report.rows.len(), 5);
        assert_eq!(report.bootstrap_rows.len(), 2);
        assert_eq!(report.untimed_targets, ["test-missing"]);
        assert_eq!(
            serde_json::to_string(&report).expect("serialize report"),
            r#"{"schema_version":2,"kind":"harness","sampled_run_ids":[42],"rows":[{"run_id":42,"shard":1,"target":"test-a","seconds":10.0},{"run_id":42,"shard":1,"target":"test-b","seconds":5.0},{"run_id":42,"shard":1,"target":"test-a","seconds":12.0},{"run_id":42,"shard":1,"target":"test-b","seconds":8.0},{"run_id":42,"shard":2,"target":"test-c","seconds":3.0}],"bootstrap_rows":[{"run_id":42,"shard":1,"target":"test-a","bootstrap_kind":"cold","seconds":1.0},{"run_id":42,"shard":1,"target":"test-b","bootstrap_kind":"warm","seconds":0.01}],"target_medians":[{"target":"test-a","seconds":22.0},{"target":"test-b","seconds":13.0},{"target":"test-c","seconds":3.0}],"shard_medians":[{"shard":1,"seconds":35.0},{"shard":2,"seconds":3.0}],"untimed_targets":["test-missing"],"skipped_run_ids":[]}"#
        );
    }

    #[test]
    fn recorded_pytest_fixture_preserves_attempts_nodeids_totals_and_wire_order() {
        let fixture = archive(&[(
            "4_python-tests (3.11, 2).txt",
            "PYTEST_SHARD_ID: 2\n\
             PYTEST_SHARD_COUNT: 4\n\
             1.00s call stale.py::ignored\n\
             ================= slowest durations =================\n\
             2026-01-01T00:00:00Z 10.00s call test_a.py::old[param]\n\
             0.50s setup test_a.py::old[param]\n\
             slowest 2 durations\n\
             2s call test_b.py::new[param]\n",
        )]);
        let rows = parse_pytest_archive(&fixture, 7).expect("parse fixture");
        let report = pytest_report(vec![7], rows, Vec::new());

        assert_eq!(report.rows.len(), 2);
        assert_eq!(report.nodeid_medians[0].nodeid, "test_b.py::new[param]");
        assert_eq!(report.observed_shard_count, Some(4));
        assert_eq!(
            serde_json::to_string(&report).expect("serialize report"),
            r#"{"schema_version":2,"kind":"pytest","sampled_run_ids":[7],"rows":[{"run_id":7,"shard":2,"nodeid":"test_a.py::old[param]","seconds":10.0,"attempt":1,"shard_total":4},{"run_id":7,"shard":2,"nodeid":"test_b.py::new[param]","seconds":2.0,"attempt":2,"shard_total":4}],"nodeid_medians":[{"nodeid":"test_b.py::new[param]","seconds":2.0}],"shard_medians":[{"shard":2,"seconds":2.0}],"observed_shard_count":4,"skipped_run_ids":[]}"#
        );
    }

    #[test]
    fn single_target_harness_marks_are_aggregated_as_one_target_cost() {
        let rows = vec![
            HarnessTimingRow {
                run_id: 1,
                shard: 1,
                target: String::from("test-solo"),
                seconds: 10.0,
            },
            HarnessTimingRow {
                run_id: 1,
                shard: 1,
                target: String::from("test-solo"),
                seconds: 12.0,
            },
        ];

        assert!((harness_shard_medians(&rows)[0].seconds - 22.0).abs() < f64::EPSILON);
        assert_eq!(
            harness_target_medians(&rows),
            [TargetTiming {
                target: String::from("test-solo"),
                seconds: 22.0,
            }]
        );
    }

    #[test]
    fn conflicting_pytest_totals_are_not_coerced_to_a_count() {
        let rows = vec![
            PytestTimingRow {
                run_id: 1,
                shard: 1,
                nodeid: String::from("a"),
                seconds: 1.0,
                attempt: 1,
                shard_total: Some(4),
            },
            PytestTimingRow {
                run_id: 1,
                shard: 2,
                nodeid: String::from("b"),
                seconds: 1.0,
                attempt: 1,
                shard_total: Some(5),
            },
        ];

        assert_eq!(observed_shard_count(&rows), None);
    }

    #[test]
    fn malformed_or_entry_flood_archives_fail_closed() {
        assert!(parse_harness_archive(&WorkflowLogArchive::new(b"not zip".to_vec()), 1).is_err());
        let mut writer = zip::ZipWriter::new(Cursor::new(Vec::new()));
        for index in 0..=WorkflowLogArchive::MAX_ENTRIES {
            writer
                .start_file(
                    format!("job/{index}.txt"),
                    zip::write::SimpleFileOptions::default(),
                )
                .expect("start flood entry");
        }
        let flood = WorkflowLogArchive::new(writer.finish().expect("finish flood").into_inner());
        assert!(parse_pytest_archive(&flood, 1).is_err());
    }

    #[test]
    fn domain_limits_reject_oversized_or_ambiguous_inputs() {
        assert!(validate_run_ids(&[1; MAX_CI_TIMING_RUNS + 1]).is_err());
        assert!(validate_run_ids(&[1, 1]).is_err());
        assert!(validate_run_ids(&[0]).is_err());
        assert_eq!(capture_u32(&HARNESS_JOB_RE, "test-harnesses (0)", 1), None);
        assert!(validate_required_targets(&["x".repeat(MAX_TIMING_LABEL_BYTES + 1)]).is_err());
        assert_eq!(timing_rows_fit(1, 2, 1, ["abc"].into_iter()), Some(5));
        assert!(
            timing_rows_fit(MAX_TIMING_REPORT_ROWS, 0, 1, std::iter::empty::<&str>()).is_none()
        );
    }
}
