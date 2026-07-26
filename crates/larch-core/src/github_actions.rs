//! Domain use cases for the narrow GitHub Actions command surface.

use crate::{GitHubActionsService, GitHubRepositoryRef, ProcessCancellation, WorkflowLogArchive};
use std::io::{Cursor, Read};

const MAX_LOG_ENTRIES: usize = 1_024;

/// Stable outcome for `larch gh run-logs`.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RunLogsOutput {
    stdout: Vec<u8>,
    exit_code: u8,
}

impl RunLogsOutput {
    #[must_use]
    pub fn stdout(&self) -> &[u8] {
        &self.stdout
    }

    #[must_use]
    pub const fn exit_code(&self) -> u8 {
        self.exit_code
    }
}

/// Download and render the logs for one completed GitHub workflow run.
///
/// The returned bytes intentionally remain unredacted. The command preserves
/// the legacy redaction boundary: callers that pass logs to an agent must
/// redact them before doing so.
pub async fn run_logs(
    service: &dyn GitHubActionsService,
    repository: &GitHubRepositoryRef,
    run_id: u64,
    cancellation: &dyn ProcessCancellation,
) -> RunLogsOutput {
    let pointer = run_logs_pointer(repository, run_id);
    let run = match service.workflow_run(repository, run_id, cancellation).await {
        Ok(run) => run,
        Err(error) => return failure(&pointer, error),
    };
    if run.status != "completed" {
        return RunLogsOutput {
            stdout: format!(
                "{pointer}\nrun is still in progress; logs will be available when it is complete\n"
            )
            .into_bytes(),
            exit_code: 3,
        };
    }
    let archive = match service
        .download_workflow_logs(repository, run_id, cancellation)
        .await
    {
        Ok(archive) => archive,
        Err(error) => return failure(&pointer, error),
    };
    let jobs = match service
        .workflow_jobs(repository, run_id, cancellation)
        .await
    {
        Ok(jobs) => jobs,
        Err(error) => return failure(&pointer, error),
    };
    let failed_jobs: Vec<&str> = jobs
        .iter()
        .filter(|job| job.is_failed())
        .map(|job| job.name.as_str())
        .collect();
    match render_archive(&archive, &failed_jobs) {
        Ok(logs) => {
            let mut stdout = pointer.into_bytes();
            stdout.push(b'\n');
            stdout.extend_from_slice(&logs);
            if !logs.is_empty() && !logs.ends_with(b"\n") {
                stdout.push(b'\n');
            }
            RunLogsOutput {
                stdout,
                exit_code: 0,
            }
        }
        Err(()) => RunLogsOutput {
            stdout: format!(
                "{pointer}\nGitHub workflow log archive is invalid or exceeds its limit\n"
            )
            .into_bytes(),
            exit_code: 1,
        },
    }
}

/// Render the legacy placeholder returned by `larch gh workflow-path`.
#[must_use]
pub const fn workflow_path() -> &'static str {
    "unknown\n"
}

/// Render a setup failure using the same pointer contract as a service error.
#[must_use]
pub fn run_logs_setup_failure(
    repository: &GitHubRepositoryRef,
    run_id: u64,
    detail: impl std::fmt::Display,
) -> RunLogsOutput {
    failure(&run_logs_pointer(repository, run_id), detail)
}

fn run_logs_pointer(repository: &GitHubRepositoryRef, run_id: u64) -> String {
    format!(
        "--- CI log (run {run_id}, repo {}/{}): failed-job log shown. Full log: https://github.com/{}/{}/actions/runs/{run_id} ---",
        repository.owner(),
        repository.name(),
        repository.owner(),
        repository.name(),
    )
}

fn failure(pointer: &str, error: impl std::fmt::Display) -> RunLogsOutput {
    RunLogsOutput {
        stdout: format!("{pointer}\n{error}\n").into_bytes(),
        exit_code: 1,
    }
}

fn render_archive(archive: &WorkflowLogArchive, failed_jobs: &[&str]) -> Result<Vec<u8>, ()> {
    let mut zip = zip::ZipArchive::new(Cursor::new(archive.as_bytes())).map_err(|_| ())?;
    if zip.len() > MAX_LOG_ENTRIES {
        return Err(());
    }
    let mut output = Vec::new();
    for index in 0..zip.len() {
        let mut entry = zip.by_index(index).map_err(|_| ())?;
        if entry.is_dir() {
            continue;
        }
        if entry.size() > WorkflowLogArchive::MAX_BYTES as u64 {
            return Err(());
        }
        let job = entry.name().split('/').next().unwrap_or_default();
        if !failed_jobs.contains(&job) {
            continue;
        }
        read_entry(&mut entry, &mut output)?;
    }
    Ok(output)
}

fn read_entry(
    entry: &mut zip::read::ZipFile<'_, Cursor<&[u8]>>,
    output: &mut Vec<u8>,
) -> Result<(), ()> {
    let mut buffer = [0_u8; 8_192];
    loop {
        let read = entry.read(&mut buffer).map_err(|_| ())?;
        if read == 0 {
            return Ok(());
        }
        if read > WorkflowLogArchive::MAX_BYTES.saturating_sub(output.len()) {
            return Err(());
        }
        output.extend_from_slice(&buffer[..read]);
    }
}
