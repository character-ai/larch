//! Rust command owners for ship state and result-env persistence.

use std::{env, ffi::OsString, path::PathBuf, process::ExitCode};

use larch_core::{
    InitialShipState, ShipResult, allowed_session_roots, tmpdir_under_allowed_root,
    validate_ship_result_env, write_initial_state,
};

use crate::argparse_compat::{ParsedCommandLine, parse_required_with_help, read_stdin};

const PROGRAM: &str = "cli.py";
const USAGE: &str = concat!(
    "usage: cli.py [-h] --tmpdir TMPDIR [--state-file STATE_FILE] --branch BRANCH\n              --issue ISSUE --repo REPO --run-id RUN_ID\n",
    "              [--manifest-path MANIFEST_PATH] [--tool-label TOOL_LABEL]\n              [--merge MERGE] [--draft DRAFT] [--forked FORKED]\n",
    "              [--repo-unavailable REPO_UNAVAILABLE] [--deferred DEFERRED]\n              [--no-admin-fallback NO_ADMIN_FALLBACK]\n",
    "              [--no-logs-commit NO_LOGS_COMMIT]\n              [--expected-session-id EXPECTED_SESSION_ID]\n",
    "              [--expected-tmpdir-basename-prefix EXPECTED_TMPDIR_BASENAME_PREFIX]\n              [--stall-tracking STALL_TRACKING] [--stall-step STALL_STEP]\n",
    "              [--bail-reason BAIL_REASON]\n              [--bail-failure-detail-log BAIL_FAILURE_DETAIL_LOG]",
);
const HELP: &str = concat!(
    "usage: cli.py [-h] --tmpdir TMPDIR [--state-file STATE_FILE] --branch BRANCH\n              --issue ISSUE --repo REPO --run-id RUN_ID\n",
    "              [--manifest-path MANIFEST_PATH] [--tool-label TOOL_LABEL]\n              [--merge MERGE] [--draft DRAFT] [--forked FORKED]\n",
    "              [--repo-unavailable REPO_UNAVAILABLE] [--deferred DEFERRED]\n              [--no-admin-fallback NO_ADMIN_FALLBACK]\n",
    "              [--no-logs-commit NO_LOGS_COMMIT]\n              [--expected-session-id EXPECTED_SESSION_ID]\n",
    "              [--expected-tmpdir-basename-prefix EXPECTED_TMPDIR_BASENAME_PREFIX]\n              [--stall-tracking STALL_TRACKING] [--stall-step STALL_STEP]\n",
    "              [--bail-reason BAIL_REASON]\n              [--bail-failure-detail-log BAIL_FAILURE_DETAIL_LOG]\n",
    "\nSeed initial ship-pr state\n\noptions:\n  -h, --help            show this help message and exit\n",
    "  --tmpdir TMPDIR\n  --state-file STATE_FILE\n  --branch BRANCH\n",
    "  --issue ISSUE\n  --repo REPO\n  --run-id RUN_ID\n",
    "  --manifest-path MANIFEST_PATH\n  --tool-label TOOL_LABEL\n  --merge MERGE\n",
    "  --draft DRAFT\n  --forked FORKED\n  --repo-unavailable REPO_UNAVAILABLE\n",
    "  --deferred DEFERRED\n  --no-admin-fallback NO_ADMIN_FALLBACK\n  --no-logs-commit NO_LOGS_COMMIT\n",
    "  --expected-session-id EXPECTED_SESSION_ID\n  --expected-tmpdir-basename-prefix EXPECTED_TMPDIR_BASENAME_PREFIX\n",
    "  --stall-tracking STALL_TRACKING\n  --stall-step STALL_STEP\n  --bail-reason BAIL_REASON\n",
    "  --bail-failure-detail-log BAIL_FAILURE_DETAIL_LOG",
);
#[rustfmt::skip]
const OPTIONS: &[&str] = &[
    "--tmpdir", "--state-file", "--branch", "--issue", "--repo", "--run-id",
    "--manifest-path", "--tool-label", "--merge", "--draft", "--forked",
    "--repo-unavailable", "--deferred", "--no-admin-fallback", "--no-logs-commit",
    "--expected-session-id", "--expected-tmpdir-basename-prefix", "--stall-tracking",
    "--stall-step", "--bail-reason", "--bail-failure-detail-log",
];
const REQUIRED: &[&str] = &["--tmpdir", "--branch", "--issue", "--repo", "--run-id"];
const RESULT_PROGRAM: &str = "cli.py ship write-result-env";
const RESULT_USAGE: &str =
    "usage: cli.py ship write-result-env [-h] --tmpdir TMPDIR --path PATH [--validate-only]";
const RESULT_HELP: &str = concat!(
    "usage: cli.py ship write-result-env [-h] --tmpdir TMPDIR --path PATH [--validate-only]\n",
    "\noptions:\n",
    "  -h, --help       show this help message and exit\n  --tmpdir TMPDIR\n  --path PATH\n  --validate-only",
);

/// Parse, validate, and create the canonical first ship state.
pub fn seed_initial_state(arguments: &[OsString]) -> ExitCode {
    let parsed =
        match parse_required_with_help(arguments, PROGRAM, USAGE, HELP, OPTIONS, &[], REQUIRED) {
            Ok(parsed) => parsed,
            Err(code) => {
                return if arguments.iter().any(|arg| arg == "-h" || arg == "--help") {
                    ExitCode::from(1)
                } else {
                    code
                };
            }
        };
    match seed(&parsed) {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("ship seed-initial-state: {error}");
            ExitCode::from(2)
        }
    }
}

/// Validate or publish the typed ship-result env from JSON on stdin.
pub fn write_result_env(arguments: &[OsString]) -> ExitCode {
    let parsed = match parse_required_with_help(
        arguments,
        RESULT_PROGRAM,
        RESULT_USAGE,
        RESULT_HELP,
        &["--tmpdir", "--path"],
        &["--validate-only"],
        &["--tmpdir", "--path"],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let tmpdir = PathBuf::from(parsed.value("--tmpdir").unwrap_or_default());
    let path = PathBuf::from(parsed.value("--path").unwrap_or_default());
    let result = validate_tmpdir(&tmpdir).and_then(|()| {
        validate_ship_result_env(&path, &tmpdir).map_err(|error| error.to_string())?;
        if parsed.flag("--validate-only") {
            return Ok(());
        }
        ShipResult::from_json(&read_stdin())
            .and_then(|ship_result| ship_result.write_result_env(&path, &tmpdir))
            .map_err(|error| error.to_string())
    });
    match result {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("ship write-result-env: {error}");
            ExitCode::from(2)
        }
    }
}

fn seed(parsed: &ParsedCommandLine) -> Result<(), String> {
    let text = |name: &str| {
        parsed
            .value(name)
            .map(|value| value.to_string_lossy().into_owned())
            .unwrap_or_default()
    };
    let tmpdir = PathBuf::from(text("--tmpdir"));
    validate_tmpdir(&tmpdir)?;
    let state_text = text("--state-file");
    let state_file = if state_text.is_empty() {
        tmpdir.join("ship-pr-state.sh")
    } else {
        PathBuf::from(state_text)
    };
    let input = InitialShipState {
        tmpdir: tmpdir.display().to_string(),
        branch: text("--branch"),
        issue: text("--issue"),
        repo: text("--repo"),
        run_id: text("--run-id"),
        manifest_path: text("--manifest-path"),
        tool_label: text("--tool-label"),
        merge: bool_arg(&text("--merge")),
        draft: bool_arg(&text("--draft")),
        forked: bool_arg(&text("--forked")),
        repo_unavailable: bool_arg(&text("--repo-unavailable")),
        deferred: bool_arg(&text("--deferred")),
        no_admin_fallback: bool_arg(&text("--no-admin-fallback")),
        no_logs_commit: bool_arg(&text("--no-logs-commit")),
        expected_session_id: text("--expected-session-id"),
        expected_tmpdir_basename_prefix: text("--expected-tmpdir-basename-prefix"),
        stall_tracking: bool_arg(&text("--stall-tracking")),
        stall_step: text("--stall-step"),
        bail_reason: text("--bail-reason"),
        bail_failure_detail_log: text("--bail-failure-detail-log"),
    };
    write_initial_state(&tmpdir, &state_file, &input).map_err(|error| error.to_string())
}

pub fn validate_tmpdir(tmpdir: &std::path::Path) -> Result<(), String> {
    let xdg = env::var_os("XDG_CACHE_HOME").filter(|value| PathBuf::from(value).is_absolute());
    let home = env::var_os("HOME");
    let roots = allowed_session_roots(xdg.as_deref(), home.as_deref());
    if tmpdir_under_allowed_root(tmpdir, &roots) {
        Ok(())
    } else {
        Err("--tmpdir is not an allowed implement tmpdir".to_owned())
    }
}

fn bool_arg(value: &str) -> bool {
    matches!(
        value.trim().to_ascii_lowercase().as_str(),
        "1" | "true" | "yes" | "on"
    )
}
