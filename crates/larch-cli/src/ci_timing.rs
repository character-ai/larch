//! larch ci-timing composition and stable JSON output.

use clap::{Args, Subcommand};
use larch_core::{
    CiTimingRunSelection, GitHubRepositoryRef, MAX_CI_TIMING_REQUIRED_TARGETS, MAX_CI_TIMING_RUNS,
    collect_harness_timing, collect_job_timing, collect_pytest_timing,
};
use serde::Serialize;
use std::{collections::HashSet, io::Write as _, path::Path, process::ExitCode};

#[derive(Subcommand)]
pub enum CiTimingCommand {
    /// Collect harness timing and bootstrap rows with their medians.
    Harness(HarnessArguments),
    /// Collect real harness-job wall-clock durations from the jobs API.
    Jobs(JobArguments),
    /// Collect pytest --durations=0 call rows and their medians.
    Pytest(PytestArguments),
}

#[derive(Args)]
pub struct HarnessArguments {
    #[command(flatten)]
    source: LogSourceArguments,
    /// Makefile target that must have at least one timing row.
    #[arg(long = "required-target")]
    required_targets: Vec<String>,
}

#[derive(Args)]
pub struct PytestArguments {
    #[command(flatten)]
    source: LogSourceArguments,
}

#[derive(Args)]
struct LogSourceArguments {
    /// GitHub repository in OWNER/REPO form.
    #[arg(long = "repo", value_parser = crate::parse_repository)]
    repository: GitHubRepositoryRef,
    /// Exact completed workflow run to read. Repeat for multiple runs.
    #[arg(long = "run-id", value_parser = parse_positive_u64)]
    run_ids: Vec<u64>,
    /// Successful workflow runs to sample when --run-id is absent.
    #[arg(long, default_value_t = 5, value_parser = parse_run_count)]
    n_runs: usize,
    /// Workflow file used when --run-id is absent.
    #[arg(long = "workflow", default_value = "ci.yaml")]
    workflow: String,
    /// Branch used when --run-id is absent.
    #[arg(long = "branch", default_value = "main")]
    branch: String,
}

#[derive(Args)]
pub struct JobArguments {
    /// GitHub repository in OWNER/REPO form.
    #[arg(long = "repo", value_parser = crate::parse_repository)]
    repository: GitHubRepositoryRef,
    /// Exact completed workflow run to read. Repeat for multiple runs.
    #[arg(long = "run-id", required = true, value_parser = parse_positive_u64)]
    run_ids: Vec<u64>,
}

pub fn run(command: CiTimingCommand) -> ExitCode {
    match run_inner(command) {
        Ok(bytes) => {
            if let Err(error) = std::io::stdout().lock().write_all(&bytes) {
                eprintln!("cannot write ci-timing output: {error}");
                return ExitCode::from(1);
            }
            ExitCode::SUCCESS
        }
        Err(error) => {
            eprintln!("{error}");
            ExitCode::from(1)
        }
    }
}

fn run_inner(command: CiTimingCommand) -> Result<Vec<u8>, String> {
    command.validate()?;
    let runtime = larch_adapters::runtime::LarchRuntime::new()
        .map_err(|error| format!("cannot initialize larch runtime: {error}"))?;
    let working_directory = std::env::current_dir()
        .map_err(|error| format!("cannot resolve current directory: {error}"))?;
    runtime.block_on(run_async(command, &working_directory))
}

impl CiTimingCommand {
    fn validate(&self) -> Result<(), String> {
        match self {
            Self::Harness(arguments) => {
                validate_run_ids(&arguments.source.run_ids)?;
                if arguments.required_targets.len() > MAX_CI_TIMING_REQUIRED_TARGETS {
                    return Err(format!(
                        "at most {MAX_CI_TIMING_REQUIRED_TARGETS} --required-target values are allowed"
                    ));
                }
                Ok(())
            }
            Self::Jobs(arguments) => validate_run_ids(&arguments.run_ids),
            Self::Pytest(arguments) => validate_run_ids(&arguments.source.run_ids),
        }
    }
}

async fn run_async(command: CiTimingCommand, working_directory: &Path) -> Result<Vec<u8>, String> {
    let cancellation = larch_adapters::runtime::Cancellation::new();
    let runner = larch_adapters::TokioProcessRunner::default();
    let service = larch_adapters::github::OctocrabGitHubService::from_gh(
        &runner,
        working_directory,
        &cancellation,
    )
    .await
    .map_err(|error| error.to_string())?;
    match command {
        CiTimingCommand::Harness(arguments) => {
            let selection = arguments.source.selection();
            let report = collect_harness_timing(
                &service,
                &arguments.source.repository,
                &selection,
                &arguments.required_targets,
                &cancellation,
            )
            .await
            .map_err(|error| error.to_string())?;
            warn_skipped("harness", &report.skipped_run_ids);
            serialize_report(&report)
        }
        CiTimingCommand::Jobs(arguments) => {
            let report = collect_job_timing(
                &service,
                &arguments.repository,
                &arguments.run_ids,
                &cancellation,
            )
            .await
            .map_err(|error| error.to_string())?;
            warn_skipped("jobs", &report.skipped_run_ids);
            serialize_report(&report)
        }
        CiTimingCommand::Pytest(arguments) => {
            let selection = arguments.source.selection();
            let report = collect_pytest_timing(
                &service,
                &arguments.source.repository,
                &selection,
                &cancellation,
            )
            .await
            .map_err(|error| error.to_string())?;
            warn_skipped("pytest", &report.skipped_run_ids);
            serialize_report(&report)
        }
    }
}

impl LogSourceArguments {
    fn selection(&self) -> CiTimingRunSelection {
        if self.run_ids.is_empty() {
            CiTimingRunSelection::Recent {
                branch: self.branch.clone(),
                workflow: self.workflow.clone(),
                limit: self.n_runs,
            }
        } else {
            CiTimingRunSelection::Explicit(self.run_ids.clone())
        }
    }
}

fn serialize_report(report: &impl Serialize) -> Result<Vec<u8>, String> {
    let mut bytes = serde_json::to_vec(report)
        .map_err(|error| format!("cannot serialize ci-timing output: {error}"))?;
    bytes.push(b'\n');
    Ok(bytes)
}

fn warn_skipped(kind: &str, run_ids: &[u64]) {
    for run_id in run_ids {
        eprintln!("warning: ci-timing {kind} skipped unreadable workflow run {run_id}");
    }
}

fn parse_positive_u64(value: &str) -> Result<u64, String> {
    value
        .parse::<u64>()
        .ok()
        .filter(|parsed| *parsed > 0)
        .ok_or_else(|| format!("expected a positive integer, got {value:?}"))
}

fn parse_run_count(value: &str) -> Result<usize, String> {
    let parsed = value
        .parse::<usize>()
        .ok()
        .filter(|parsed| (1..=MAX_CI_TIMING_RUNS).contains(parsed))
        .ok_or_else(|| {
            format!("expected an integer from 1 through {MAX_CI_TIMING_RUNS}, got {value:?}")
        })?;
    Ok(parsed)
}

fn validate_run_ids(run_ids: &[u64]) -> Result<(), String> {
    if run_ids.len() > MAX_CI_TIMING_RUNS {
        return Err(format!(
            "at most {MAX_CI_TIMING_RUNS} --run-id values are allowed"
        ));
    }
    let mut seen = HashSet::new();
    if let Some(duplicate) = run_ids.iter().find(|run_id| !seen.insert(**run_id)) {
        return Err(format!("duplicate --run-id value {duplicate}"));
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn source_selection_prefers_explicit_run_ids() {
        let source = LogSourceArguments {
            repository: GitHubRepositoryRef::new("owner", "repo").expect("repository"),
            run_ids: vec![3, 4],
            n_runs: 5,
            workflow: String::from("ci.yaml"),
            branch: String::from("main"),
        };

        assert_eq!(
            source.selection(),
            CiTimingRunSelection::Explicit(vec![3, 4])
        );
    }

    #[test]
    fn positive_integer_parser_rejects_zero_and_non_numbers() {
        assert_eq!(parse_positive_u64("3"), Ok(3));
        assert!(parse_positive_u64("0").is_err());
        assert_eq!(parse_run_count("20"), Ok(20));
        assert!(parse_run_count("21").is_err());
        assert!(parse_run_count("x").is_err());
        assert!(validate_run_ids(&[1, 1]).is_err());
    }
}
