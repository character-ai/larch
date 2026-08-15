//! Rust owner for retrospective difficulty calibration.

use std::{collections::BTreeMap, env, ffi::OsString, fs, path::PathBuf, process::ExitCode};

use crate::{
    analysis_state,
    argparse_compat::{parse_required_with_help, write_stdout},
    run_log_commands,
    run_log_publication_commands::synchronized_corpus_root,
};

const PROGRAM: &str = "difficulty-calibration analyze";
const USAGE: &str = "usage: difficulty-calibration analyze [-h] [--log-root LOG_ROOT] [--out OUT]";
const HELP: &str = "\
usage: difficulty-calibration analyze [-h] [--log-root LOG_ROOT] [--out OUT]

options:
  -h, --help           show this help message and exit
  --log-root LOG_ROOT  offline fixture corpus override; default synchronizes
                       the current repository cache
  --out OUT";

/// Analyze predicted and realized difficulty over one run-log corpus.
pub fn analyze(arguments: &[OsString]) -> ExitCode {
    let parsed = match parse_required_with_help(
        arguments,
        PROGRAM,
        USAGE,
        HELP,
        &["--log-root", "--out"],
        &[],
        &[],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };

    let explicit_root = parsed
        .value("--log-root")
        .filter(|value| !value.is_empty())
        .map(PathBuf::from);
    let (log_root, state_root) = if let Some(root) = explicit_root {
        (root.clone(), root)
    } else {
        match synchronized_roots() {
            Ok(roots) => roots,
            Err(error) => {
                eprintln!("ERROR: {error}");
                return ExitCode::from(2);
            }
        }
    };
    if !log_root.is_dir() {
        eprintln!(
            "ERROR: --log-root is missing or not a directory: {}",
            log_root.display()
        );
        return ExitCode::from(2);
    }

    let environment: BTreeMap<String, String> = env::vars().collect();
    let report = larch_core::difficulty_calibration_report(&log_root, &state_root, &environment);
    let output = parsed
        .value("--out")
        .filter(|value| !value.is_empty())
        .map(PathBuf::from);
    let Some(output) = output else {
        return write_stdout(&report);
    };
    if let Some(parent) = output
        .parent()
        .filter(|parent| !parent.as_os_str().is_empty())
        && let Err(error) = fs::create_dir_all(parent)
    {
        eprintln!("{error}");
        return ExitCode::FAILURE;
    }
    if let Err(error) = fs::write(&output, report) {
        eprintln!("{error}");
        return ExitCode::FAILURE;
    }
    println!("REPORT_FILE={}", output.display());
    ExitCode::SUCCESS
}

fn synchronized_roots() -> Result<(PathBuf, PathBuf), String> {
    let (repo_root, _origin, _environment) =
        run_log_commands::resolve_repository_environment_path(None).map_err(|error| {
            let message = match error {
                run_log_commands::PreflightFailure::Configuration(error) => error.to_string(),
                run_log_commands::PreflightFailure::Provider(error) => error.to_string(),
            };
            if message.starts_with("could not discover a Git repository root") {
                "could not discover a Git repository root for run-log synchronization".to_owned()
            } else {
                message
            }
        })?;
    let repo_root = fs::canonicalize(repo_root).map_err(|_| {
        "could not discover a Git repository root for run-log synchronization".to_owned()
    })?;
    let storage =
        run_log_commands::resolve_enabled_storage_path(Some(&repo_root)).map_err(|error| {
            match error {
                run_log_commands::PreflightFailure::Configuration(error) => error.to_string(),
                run_log_commands::PreflightFailure::Provider(error) => error.to_string(),
            }
        })?;
    let log_root = synchronized_corpus_root(&repo_root)?;
    let state_root =
        analysis_state::storage_root(&storage.client_repo, &storage.storage_origin_id())?;
    Ok((log_root, state_root))
}
