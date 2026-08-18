//! Rust owner for retrospective difficulty calibration.

use std::{collections::BTreeMap, env, ffi::OsString, path::PathBuf, process::ExitCode};

use crate::{
    analysis_state,
    argparse_compat::{optional_out_path, parse_required_with_help, write_report_file, write_stdout},
    run_log_commands,
    run_log_publication_commands::{
        preflight_error, synchronized_corpus_root, synchronized_repository_root,
    },
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
    let Some(output) = optional_out_path(&parsed) else {
        return write_stdout(&report);
    };
    write_report_file(&output, &report)
}

fn synchronized_roots() -> Result<(PathBuf, PathBuf), String> {
    let repo_root = synchronized_repository_root()?;
    let storage = run_log_commands::resolve_enabled_storage_path(Some(&repo_root))
        .map_err(|error| preflight_error(&error))?;
    let log_root = synchronized_corpus_root(&repo_root)?;
    let state_root =
        analysis_state::storage_root(&storage.client_repo, &storage.storage_origin_id())?;
    Ok((log_root, state_root))
}
