//! `session` entry-gate and live-mutation authorization verbs.
//!
//! Both verbs are read-only decisions taken before a run mutates anything: the
//! entry gate resolves the clean-main contract from branch facts, and the
//! authorization check answers whether a session may perform a live GitHub
//! issue mutation. Ambient state is read here and passed to the pure rules and
//! the adapter gate explicitly.

use crate::argparse_compat::{parse, write_stdout};
use larch_adapters::github::{LiveMutationRequest, check_live_mutation_auth};
use larch_core::{GateDecision, entry_gate as resolve_entry_gate};
use std::{env, ffi::OsString, path::Path, process::ExitCode};

/// `argparse` renders this usage block at its 80-column fallback width.
const ENTRY_GATE_USAGE: &str = concat!(
    "usage: session entry-gate [--mode MODE] [--current-branch CURRENT_BRANCH]\n",
    "                          [--is-main IS_MAIN]\n",
    "                          [--is-user-branch IS_USER_BRANCH]\n",
    "                          [--user-prefix USER_PREFIX]\n",
    "                          [--branch-info-supplied BRANCH_INFO_SUPPLIED]\n",
);
const MUTATION_AUTH_USAGE: &str = concat!(
    "usage: session check-live-mutation-auth --context-file CONTEXT_FILE --run-id\n",
    "                                        RUN_ID --trusted-root TRUSTED_ROOT\n",
);
const MUTATION_AUTH_OPTIONS: [&str; 3] = ["--context-file", "--run-id", "--trusted-root"];
const MUTATION_TEST_DENY_KEY: &str = "LARCH_ISSUE_MUTATION_DENY";
const EXIT_MUTATION_REFUSED: u8 = 5;
const GATE_ERROR_EXIT: u8 = 4;

/// Flags the gate requires as literal tokens, in the order it reports them.
///
/// The legacy verb tested `argv` membership rather than parsed presence, so an
/// abbreviated or `--flag=value` spelling parses but still reports as missing.
/// Callers pass the separated spelling; preserving the check keeps a partially
/// spelled command line failing loudly instead of resolving a gate from
/// defaults.
const REQUIRED_GATE_FLAGS: [&str; 5] = [
    "--mode",
    "--current-branch",
    "--user-prefix",
    "--is-main",
    "--is-user-branch",
];

/// Resolve the `/implement` or `/design` entry gate from supplied branch facts.
pub fn entry_gate(arguments: &[OsString]) -> ExitCode {
    let options = [
        "--mode",
        "--current-branch",
        "--is-main",
        "--is-user-branch",
        "--user-prefix",
        "--branch-info-supplied",
    ];
    let parsed = parse(arguments, &options, 0);
    if let Some(error) = parsed.value_error() {
        eprint!("{ENTRY_GATE_USAGE}");
        eprintln!("session entry-gate: error: {error}");
        return ExitCode::from(GATE_ERROR_EXIT);
    }
    if let Some(unrecognized) = parsed.error() {
        // `parse_known_args` returned the surplus token instead of exiting.
        let first = unrecognized
            .strip_prefix("unrecognized arguments: ")
            .and_then(|rest| rest.split(' ').next())
            .unwrap_or_default();
        return gate_error(&format!("unknown argument: {first}"));
    }
    for flag in REQUIRED_GATE_FLAGS {
        if !arguments.iter().any(|argument| argument == flag) {
            return gate_error(&format!("missing required flag {flag}"));
        }
    }
    let branch_info = parsed
        .value("--branch-info-supplied")
        .map(|value| value.to_string_lossy().into_owned());
    let decision = resolve_entry_gate(
        &text(&parsed, "--mode"),
        &text(&parsed, "--is-main"),
        &text(&parsed, "--is-user-branch"),
        &text(&parsed, "--user-prefix"),
        branch_info.as_deref(),
    );
    match decision {
        Ok(GateDecision {
            entry_gate,
            skip_branch_check,
        }) => write_stdout(&format!(
            "ENTRY_GATE={entry_gate}\nSKIP_BRANCH_CHECK={skip_branch_check}\n"
        )),
        Err(message) => gate_error(&message),
    }
}

/// Authorize one live GitHub issue mutation for a session-backed caller.
pub fn check_live_mutation_auth_command(arguments: &[OsString]) -> ExitCode {
    let parsed = parse(arguments, &MUTATION_AUTH_OPTIONS, 0);
    if let Some(error) = parsed.value_error() {
        return mutation_auth_usage_error(error);
    }
    let missing: Vec<&str> = MUTATION_AUTH_OPTIONS
        .into_iter()
        .filter(|option| parsed.value(option).is_none())
        .collect();
    if !missing.is_empty() {
        return mutation_auth_usage_error(&format!(
            "the following arguments are required: {}",
            missing.join(", ")
        ));
    }
    if let Some(unrecognized) = parsed.error() {
        return mutation_auth_usage_error(&unrecognized);
    }
    let context_file = Path::new(parsed.value("--context-file").unwrap_or_default());
    let trusted_root = Path::new(parsed.value("--trusted-root").unwrap_or_default());
    let run_id = text(&parsed, "--run-id");
    let decision = check_live_mutation_auth(&LiveMutationRequest {
        context_file: Some(context_file),
        operator_mode: false,
        run_id: &run_id,
        trusted_root: Some(trusted_root),
        test_deny: env::var(MUTATION_TEST_DENY_KEY).as_deref() == Ok("true"),
    });
    if decision.is_authorized() {
        ExitCode::SUCCESS
    } else {
        ExitCode::from(EXIT_MUTATION_REFUSED)
    }
}

fn mutation_auth_usage_error(error: &str) -> ExitCode {
    eprint!("{MUTATION_AUTH_USAGE}");
    eprintln!("session check-live-mutation-auth: error: {error}");
    ExitCode::FAILURE
}

fn gate_error(message: &str) -> ExitCode {
    eprintln!("GATE_ERROR={message}");
    ExitCode::from(GATE_ERROR_EXIT)
}

fn text(parsed: &crate::argparse_compat::ParsedCommandLine, option: &str) -> String {
    parsed
        .value(option)
        .unwrap_or_default()
        .to_string_lossy()
        .into_owned()
}
