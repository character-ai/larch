//! `token` measurement command composition.

use std::{
    env,
    ffi::OsString,
    path::{Path, PathBuf},
    process::ExitCode,
};

use chrono::Local;
use larch_adapters::GixRepository;
use larch_core::report::{
    checks_digest_savings, markdown_cost, ngram_duplication, panel_cost, realized_cost,
    reference_heatmap, token_cache_efficiency_with_diagnostics,
};

use crate::{
    analysis_state,
    run_log_commands::{PreflightFailure, resolve_repository_environment_path},
    run_log_publication_commands::synchronized_corpus_root,
};

const EXIT_BAIL: u8 = 4;

#[derive(Clone, Copy)]
enum Measurement {
    Markdown,
    Cache,
    ChecksDigest,
    Ngram,
    Panel,
    Realized,
    References,
}

impl Measurement {
    const fn owner(self) -> &'static str {
        match self {
            Self::Markdown => "measure-md-cost",
            Self::Cache => "measure-cache-efficiency",
            Self::ChecksDigest => "measure-checks-digest-savings",
            Self::Ngram => "measure-ngram-duplication",
            Self::Panel => "measure-panel-cost",
            Self::Realized => "measure-realized-cost",
            Self::References => "measure-references-heatmap",
        }
    }

    const fn suffix(self) -> &'static str {
        if matches!(self, Self::Ngram) {
            "txt"
        } else {
            "tsv"
        }
    }

    const fn needs_corpus(self) -> bool {
        !matches!(self, Self::Markdown | Self::Ngram)
    }

    const fn error_prefix(self) -> &'static str {
        if matches!(self, Self::Cache) {
            ""
        } else {
            "ERROR: "
        }
    }
}

/// Measure tracked Markdown cost.
pub fn measure_md_cost(arguments: &[OsString]) -> ExitCode {
    run(Measurement::Markdown, arguments)
}

/// Measure Claude cache efficiency.
pub fn measure_cache_efficiency(arguments: &[OsString]) -> ExitCode {
    run(Measurement::Cache, arguments)
}

/// Measure checks-digest savings.
pub fn measure_checks_digest_savings(arguments: &[OsString]) -> ExitCode {
    run(Measurement::ChecksDigest, arguments)
}

/// Measure repeated prompt shingles.
pub fn measure_ngram_duplication(arguments: &[OsString]) -> ExitCode {
    run(Measurement::Ngram, arguments)
}

/// Measure panel prompt cost.
pub fn measure_panel_cost(arguments: &[OsString]) -> ExitCode {
    run(Measurement::Panel, arguments)
}

/// Measure realized skill and reference cost.
pub fn measure_realized_cost(arguments: &[OsString]) -> ExitCode {
    run(Measurement::Realized, arguments)
}

/// Measure reference-read frequency.
pub fn measure_references_heatmap(arguments: &[OsString]) -> ExitCode {
    run(Measurement::References, arguments)
}

fn run(measurement: Measurement, _arguments: &[OsString]) -> ExitCode {
    match execute(measurement) {
        Ok(path) => {
            let displayed = if matches!(measurement, Measurement::Panel) {
                repository_relative(&path).unwrap_or_else(|| path.display().to_string())
            } else {
                path.display().to_string()
            };
            println!("WROTE\t{displayed}");
            ExitCode::SUCCESS
        }
        Err(error) => {
            eprintln!("{}{error}", measurement.error_prefix());
            ExitCode::from(EXIT_BAIL)
        }
    }
}

fn execute(measurement: Measurement) -> Result<PathBuf, String> {
    let repo_root = repository_root()?;
    let stamp = env::var("LARCH_MEASURE_DATE")
        .unwrap_or_else(|_| Local::now().format("%Y-%m-%d").to_string());
    validate_file_component(&format!("{stamp}.{}", measurement.suffix()))?;
    let relative = format!("{}/{stamp}.{}", measurement.owner(), measurement.suffix());
    let output = analysis_state::marker_path(&repo_root, &relative)?;
    let corpus = measurement
        .needs_corpus()
        .then(|| synchronized_corpus_root(&repo_root))
        .transpose()?;
    let tracked = if measurement.needs_corpus() {
        Vec::new()
    } else {
        let repository = GixRepository::discover(&repo_root)
            .map_err(|_| "could not read repository index".to_owned())?;
        repository
            .tracked_paths()
            .map_err(|_| "could not read repository index".to_owned())?
            .into_iter()
            .map(|path| path.as_bytes().to_vec())
            .collect()
    };
    let text = render(measurement, &repo_root, corpus.as_deref(), &tracked)?;
    analysis_state::write_marker(&output, &text)?;
    Ok(output)
}

fn render(
    measurement: Measurement,
    repo_root: &Path,
    corpus_root: Option<&Path>,
    tracked: &[Vec<u8>],
) -> Result<String, String> {
    let corpus = || corpus_root.ok_or_else(|| "run-log corpus was not synchronized".to_owned());
    match measurement {
        Measurement::Markdown => markdown_cost(repo_root, tracked),
        Measurement::Cache => Ok(token_cache_efficiency_with_diagnostics(corpus()?, |line| {
            eprintln!("{line}");
        })),
        Measurement::ChecksDigest => Ok(checks_digest_savings(corpus()?)),
        Measurement::Ngram => ngram_duplication(
            repo_root,
            tracked,
            numeric_env("LARCH_MEASURE_NGRAM_SIZE", 6)?,
            numeric_env("LARCH_MEASURE_NGRAM_MIN_FILES", 3)?,
            numeric_env("LARCH_MEASURE_NGRAM_LIMIT", 50)?,
        ),
        Measurement::Panel => Ok(panel_cost(corpus()?)),
        Measurement::Realized => Ok(realized_cost(repo_root, corpus()?)),
        Measurement::References => Ok(reference_heatmap(repo_root, corpus()?)),
    }
}

fn numeric_env(name: &str, default: usize) -> Result<usize, String> {
    let Some(value) = env::var_os(name) else {
        return Ok(default);
    };
    value
        .to_string_lossy()
        .parse()
        .map_err(|_| format!("{name} must be a non-negative integer"))
}

fn validate_file_component(value: &str) -> Result<(), String> {
    let invalid = value.is_empty()
        || matches!(value, "." | "..")
        || value.contains(['/', '\\'])
        || value.chars().any(char::is_control);
    if invalid {
        Err(format!("invalid state file: {value:?}"))
    } else {
        Ok(())
    }
}

fn repository_root() -> Result<PathBuf, String> {
    resolve_repository_environment_path(None)
        .map(|(root, _origin, _environment)| root)
        .map_err(|error| match error {
            PreflightFailure::Configuration(error) => error.to_string(),
            PreflightFailure::Provider(error) => error.to_string(),
        })
}

fn repository_relative(path: &Path) -> Option<String> {
    let cwd = env::current_dir().ok()?;
    path.strip_prefix(cwd)
        .ok()
        .map(|relative| relative.display().to_string())
}
