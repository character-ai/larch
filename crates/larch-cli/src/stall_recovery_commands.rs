//! Thin compatibility boundary for Rust-owned stall-recovery commands.
use crate::stall_recovery_reporting;
use larch_adapters::stall_recovery::{
    AttemptRecord, ClassificationRequest, EscalationError, EscalationOutput, EscalationRequest,
    StallRecoveryError, StateMutationError, classify, clear_stall, init_attempts,
    is_larch_dev_clone, normalize_file_failure_report_env, normalize_issue_env, normalize_outcome,
    record_attempt, record_escalation, seed_terminal_state, terminal_state_is_valid,
    tier_b_public_file_is_valid,
};
use larch_core::{IssueNormalization, artifact_prefix_valid, retry_policy, token_valid};
use std::{collections::BTreeMap, env, ffi::OsString, path::PathBuf, process::ExitCode};
const GLOBAL_FLAGS: &[&str] = &[
    "--profile",
    "--artifact-prefix",
    "--implement-tmpdir",
    "--primary-state-file",
    "--finalize-state-file",
    "--session-env-file",
];

type Globals = BTreeMap<String, String>;
macro_rules! command_options {
    ($arguments:expr, $verb:literal, $known:expr) => {
        match parse_options($arguments, $known) {
            OptionParse::Help => return help($verb),
            OptionParse::Error(message) => return usage_error(&message),
            OptionParse::Values(options) => options,
        }
    };
}
fn tmpdir(globals: &Globals) -> String {
    globals
        .get("--implement-tmpdir")
        .cloned()
        .unwrap_or_else(|| env::var("IMPLEMENT_TMPDIR").unwrap_or_else(|_| ".".to_owned()))
}

pub fn run(arguments: &[OsString]) -> ExitCode {
    let Ok(strings) = arguments
        .iter()
        .map(|value| value.clone().into_string())
        .collect::<Result<Vec<_>, _>>()
    else {
        eprintln!("stall-recovery: arguments must be UTF-8");
        return ExitCode::from(2);
    };
    let (globals, rest) = match parse_globals(&strings) {
        Ok(parsed) => parsed,
        Err(message) => return usage_error(&message),
    };
    let Some((verb, command_arguments)) = rest.split_first() else {
        return usage_error("missing subcommand");
    };
    match verb.as_str() {
        "classify" => classify_command(&globals, command_arguments),
        "clear-stall" => clear(&globals, command_arguments),
        "init-attempts" => init_attempts_command(&globals, command_arguments),
        "normalize-file-failure-report-env" => normalize_file_report(&globals, command_arguments),
        "normalize-issue-env" => normalize_issue(&globals, command_arguments),
        "normalize-outcome" => normalize_outcome_command(&globals, command_arguments),
        "record-attempt" => record_attempt_command(&globals, command_arguments),
        "record-escalation" => record_escalation_command(&globals, command_arguments),
        "retry-policy" => retry_policy_command(command_arguments),
        "seed-terminal-state" => seed(&globals, command_arguments),
        "validate-token" => validate_token(&globals, command_arguments),
        "validate-terminal-state" => validate_terminal(&globals, command_arguments),
        "validate-tier-b-public-file" => validate_public(&globals, command_arguments),
        "is-larch-dev-clone" => detect_dev_clone(&globals, command_arguments),
        "compose-report" => compose_report(&globals, command_arguments, false),
        "chat-print" => compose_report(&globals, command_arguments, true),
        "dedup-tier-a-report" => dedup_tier_a_report(&globals, command_arguments),
        "populate-sensitive-corpus" => populate_sensitive_corpus(&globals, command_arguments),
        other => usage_error(&format!("unknown subcommand: {other}")),
    }
}

const COMPOSE_REPORT_FLAGS: &[&str] = &[
    "--implement-tmpdir",
    "--report-kind",
    "--surface",
    "--attempts-file",
    "--classification-file",
    "--escalation-ledger-file",
    "--escalation-fallback-file",
    "--record-failure-marker",
    "--root-cause-file",
    "--bounded-root-cause-file",
    "--title-file",
    "--sensitive-corpus-file",
    "--output-file",
    "--profile",
    "--artifact-prefix",
    "--primary-state-file",
    "--finalize-state-file",
    "--session-env-file",
];

fn compose_report(globals: &Globals, arguments: &[String], force_chat_print: bool) -> ExitCode {
    let options = match parse_options(arguments, COMPOSE_REPORT_FLAGS) {
        OptionParse::Help => {
            return help(if force_chat_print {
                "chat-print"
            } else {
                "compose-report"
            });
        }
        OptionParse::Error(message) => return usage_error(&message),
        OptionParse::Values(options) => options,
    };
    stall_recovery_reporting::compose(globals, &options, force_chat_print)
}

fn dedup_tier_a_report(globals: &Globals, arguments: &[String]) -> ExitCode {
    let options = match parse_options(
        arguments,
        &[
            "--implement-tmpdir",
            "--body-file",
            "--attempts-file",
            "--escalation-ledger-file",
            "--root-cause-file",
            "--context-file",
            "--artifact-prefix",
        ],
    ) {
        OptionParse::Help => return help("dedup-tier-a-report"),
        OptionParse::Error(message) => return usage_error(&message),
        OptionParse::Values(options) => options,
    };
    stall_recovery_reporting::dedup_tier_a_report(globals, &options)
}

fn populate_sensitive_corpus(globals: &Globals, arguments: &[String]) -> ExitCode {
    let options = match parse_options(
        arguments,
        &[
            "--implement-tmpdir",
            "--sensitive-corpus-file",
            "--classification-file",
            "--attempts-file",
            "--escalation-ledger-file",
            "--escalation-fallback-file",
            "--record-failure-marker",
            "--artifact-prefix",
        ],
    ) {
        OptionParse::Help => return help("populate-sensitive-corpus"),
        OptionParse::Error(message) => return usage_error(&message),
        OptionParse::Values(options) => options,
    };
    stall_recovery_reporting::populate_sensitive_corpus(globals, &options)
}

#[rustfmt::skip]
fn classify_command(globals: &Globals, arguments: &[String]) -> ExitCode {
    let known = ["--implement-tmpdir", "--failure-detail-log", "--attempts-file", "--bail-reason", "--in-memory-stall-tracking", "--primary-state-file", "--finalize-state-file", "--session-env-file", "--artifact-prefix", "--profile", "--stall-step", "--phase", "--exit-code", "--dispatcher"];
    let options = command_options!(arguments, "classify", &known);
    let profile = option_or_global(&options, globals, "--profile", "implement").to_owned();
    #[rustfmt::skip]
    let request = ClassificationRequest {
        tmpdir: PathBuf::from(option_or_tmpdir(&options, globals)),
        primary_state_file: PathBuf::from(option_or_global(&options, globals, "--primary-state-file", "")),
        finalize_state_file: PathBuf::from(option_or_global(&options, globals, "--finalize-state-file", "")),
        session_env_file: PathBuf::from(option_or_global(&options, globals, "--session-env-file", "")),
        failure_detail_log: PathBuf::from(value(&options, "--failure-detail-log")), attempts_file: PathBuf::from(value(&options, "--attempts-file")),
        bail_reason: value(&options, "--bail-reason").to_owned(), memory_stall: value(&options, "--in-memory-stall-tracking").to_owned(),
        artifact_prefix: option_or_global(&options, globals, "--artifact-prefix", "").to_owned(), profile: profile.clone(),
        stall_step: value(&options, "--stall-step").to_owned(), phase: value(&options, "--phase").to_owned(),
        exit_code: value(&options, "--exit-code").to_owned(), dispatcher: value(&options, "--dispatcher").to_owned(),
    };
    match classify(&request) {
        Ok(output) => {
            if let Some(warning) = output.warning { eprintln!("stall-recovery: {warning}"); }
            emit_rows(output.values); println!("CLASSIFICATION_FILE={}", output.file.display());
            ExitCode::SUCCESS
        }
        Err(error) => adapter_error(error, profile == "generic"),
    }
}

#[rustfmt::skip]
fn init_attempts_command(globals: &Globals, arguments: &[String]) -> ExitCode {
    let options = command_options!(arguments, "init-attempts", &["--implement-tmpdir", "--attempts-file"]);
    match init_attempts(&PathBuf::from(option_or_tmpdir(&options, globals)), &PathBuf::from(value(&options, "--attempts-file"))) {
        Ok((path, count)) => {
            println!("ATTEMPTS_FILE={}", path.display()); println!("ATTEMPT_COUNT={count}");
            ExitCode::SUCCESS
        }
        Err(error) => adapter_error(error, false),
    }
}

#[rustfmt::skip]
fn record_attempt_command(globals: &Globals, arguments: &[String]) -> ExitCode {
    let known = ["--implement-tmpdir", "--attempts-file", "--class", "--signature", "--resume-hint", "--outcome"];
    let options = command_options!(arguments, "record-attempt", &known);
    if let Some(message) = required_options(&options, &["--class", "--signature"]) { return usage_error(&message); }
    let request = AttemptRecord {
        tmpdir: PathBuf::from(option_or_tmpdir(&options, globals)), attempts_file: PathBuf::from(value(&options, "--attempts-file")),
        failure_class: value(&options, "--class").to_owned(), signature: value(&options, "--signature").to_owned(),
        resume_hint: option_or(&options, "--resume-hint", "none").to_owned(), outcome: option_or(&options, "--outcome", "failed").to_owned(),
    };
    match record_attempt(&request) {
        Ok(count) => { println!("ATTEMPT_COUNT={count}"); ExitCode::SUCCESS }
        Err(error) => adapter_error(error, false),
    }
}

#[rustfmt::skip]
fn retry_policy_command(arguments: &[String]) -> ExitCode {
    let options = command_options!(arguments, "retry-policy", &["--class"]);
    if let Some(message) = required_options(&options, &["--class"]) { return usage_error(&message); }
    let class = value(&options, "--class");
    let (attempts, delay) = retry_policy(class);
    println!("FAILURE_CLASS={class}"); println!("MAX_ATTEMPTS={attempts}"); println!("RETRY_DELAY={delay}");
    ExitCode::SUCCESS
}

#[rustfmt::skip]
fn normalize_outcome_command(globals: &Globals, arguments: &[String]) -> ExitCode {
    let options = command_options!(arguments, "normalize-outcome", &["--implement-tmpdir", "--in-memory-stall-tracking"]);
    match normalize_outcome(&PathBuf::from(option_or_tmpdir(&options, globals)), value(&options, "--in-memory-stall-tracking")) {
        Ok(values) => { emit_rows(values); ExitCode::SUCCESS }
        Err(error) => adapter_error(error, false),
    }
}

#[rustfmt::skip]
fn normalize_issue(globals: &Globals, arguments: &[String]) -> ExitCode {
    let options = command_options!(arguments, "normalize-issue-env", &["--implement-tmpdir", "--issue-stdout-file", "--issue-exit-code"]);
    if let Some(message) = required_options(&options, &["--issue-stdout-file"]) { return usage_error(&message); }
    let exit_code = options.get("--issue-exit-code").map(String::as_str);
    if exit_code.is_some_and(|value| !value.bytes().all(|byte| byte.is_ascii_digit())) {
        return usage_error("--issue-exit-code must be a non-negative integer");
    }
    match normalize_issue_env(&PathBuf::from(option_or_tmpdir(&options, globals)), &PathBuf::from(value(&options, "--issue-stdout-file")), exit_code) {
        Ok(IssueNormalization::Success { number, url }) => {
            println!("NORMALIZED=true"); println!("ISSUE_NUMBER={number}"); println!("ISSUE_URL={url}");
            ExitCode::SUCCESS
        }
        Ok(IssueNormalization::Failure(reason)) => {
            println!("NORMALIZED=false"); println!("REASON={reason}");
            ExitCode::SUCCESS
        }
        Err(error) => adapter_error(error, false),
    }
}

#[rustfmt::skip]
fn normalize_file_report(globals: &Globals, arguments: &[String]) -> ExitCode {
    let options = command_options!(arguments, "normalize-file-failure-report-env", &["--implement-tmpdir", "--file-failure-report-env"]);
    if let Some(message) = required_options(&options, &["--file-failure-report-env"]) { return usage_error(&message); }
    match normalize_file_failure_report_env(&PathBuf::from(option_or_tmpdir(&options, globals)), &PathBuf::from(value(&options, "--file-failure-report-env"))) {
        Ok(report) => {
            println!("STALL_RECOVERY_REPORT_STATUS={}", report.status);
            if !report.url.is_empty() {
                println!("STALL_RECOVERY_REPORT_URL={}", report.url);
                if let Some(number) = report.issue_number {
                    println!("STALL_RECOVERY_REPORT_ISSUE_URL={}", report.url); println!("STALL_RECOVERY_REPORT_ISSUE_NUMBER={number}");
                }
            }
            if !report.fallback_reason.is_empty() {
                println!("STALL_RECOVERY_REPORT_FALLBACK_REASON={}", report.fallback_reason);
            }
            ExitCode::SUCCESS
        }
        Err(error) => adapter_error(error, false),
    }
}

#[rustfmt::skip]
fn record_escalation_command(globals: &Globals, arguments: &[String]) -> ExitCode {
    let known = ["--implement-tmpdir", "--site", "--trigger", "--step", "--phase", "--dispatcher", "--exit-code", "--failure-detail-log", "--artifact-prefix", "--profile"];
    let options = command_options!(arguments, "record-escalation", &known);
    if let Some(message) = required_options(&options, &["--site", "--trigger", "--step", "--phase", "--dispatcher"]) { return usage_error(&message); }
    let request = EscalationRequest {
        tmpdir: PathBuf::from(option_or_tmpdir(&options, globals)), site: value(&options, "--site").to_owned(),
        trigger: value(&options, "--trigger").to_owned(), step: value(&options, "--step").to_owned(), phase: value(&options, "--phase").to_owned(),
        dispatcher: value(&options, "--dispatcher").to_owned(), exit_code: option_or(&options, "--exit-code", "unknown").to_owned(),
        failure_detail_log: PathBuf::from(value(&options, "--failure-detail-log")),
        artifact_prefix: option_or_global(&options, globals, "--artifact-prefix", "").to_owned(), generic: option_or_global(&options, globals, "--profile", "implement") == "generic",
    };
    match record_escalation(&request) {
        Ok(EscalationOutput::Canonical(path)) => {
            println!("ESCALATION_RECORDED=true"); println!("ESCALATION_LEDGER_FILE={}", path.display());
            ExitCode::SUCCESS
        }
        Ok(EscalationOutput::Fallback) => {
            println!("ESCALATION_RECORDED=false"); println!("ESCALATION_FALLBACK_WRITTEN=true");
            ExitCode::SUCCESS
        }
        Err(EscalationError::Usage(message)) => usage_error(message),
        Err(EscalationError::Failure(message)) => command_error(&format!("record-escalation {message}")),
    }
}

fn clear(globals: &Globals, arguments: &[String]) -> ExitCode {
    let options = match parse_options(arguments, &["--implement-tmpdir"]) {
        OptionParse::Help => return help("clear-stall"),
        OptionParse::Error(message) => return usage_error(&message),
        OptionParse::Values(options) => options,
    };
    let tmpdir = options
        .get("--implement-tmpdir")
        .cloned()
        .unwrap_or_else(|| tmpdir(globals));
    match clear_stall(&PathBuf::from(tmpdir)) {
        Ok(()) => emit_result("CLEARED", true, 0),
        Err(StateMutationError::Unsafe) => emit_result("CLEARED", false, 3),
        Err(StateMutationError::Failed) => emit_result("CLEARED", false, 1),
    }
}

fn seed(globals: &Globals, arguments: &[String]) -> ExitCode {
    let options = match parse_options(
        arguments,
        &["--implement-tmpdir", "--stall-step", "--phase"],
    ) {
        OptionParse::Help => return help("seed-terminal-state"),
        OptionParse::Error(message) => return usage_error(&message),
        OptionParse::Values(options) => options,
    };
    let tmpdir = options
        .get("--implement-tmpdir")
        .cloned()
        .unwrap_or_else(|| tmpdir(globals));
    match seed_terminal_state(
        &PathBuf::from(tmpdir),
        value(&options, "--stall-step"),
        value(&options, "--phase"),
    ) {
        Ok(mode) => {
            println!("SEEDED=true");
            println!("SEED_MODE={mode}");
            ExitCode::SUCCESS
        }
        Err(StateMutationError::Unsafe) => emit_result("SEEDED", false, 3),
        Err(StateMutationError::Failed) => emit_result("SEEDED", false, 1),
    }
}

fn validate_token(globals: &Globals, arguments: &[String]) -> ExitCode {
    let options = match parse_options(
        arguments,
        &[
            "--implement-tmpdir",
            "--token",
            "--value",
            "--token-kind",
            "--profile",
            "--artifact-prefix",
        ],
    ) {
        OptionParse::Help => return help("validate-token"),
        OptionParse::Error(message) => return usage_error(&message),
        OptionParse::Values(options) => options,
    };
    let token = match value(&options, "--token") {
        "" => value(&options, "--value"),
        token => token,
    };
    let profile = option_or_global(&options, globals, "--profile", "implement");
    emit_result(
        "TOKEN_VALID",
        token_valid(token, value(&options, "--token-kind"), profile == "generic"),
        1,
    )
}

fn validate_terminal(globals: &Globals, arguments: &[String]) -> ExitCode {
    let options = match parse_options(
        arguments,
        &[
            "--implement-tmpdir",
            "--primary-state-file",
            "--profile",
            "--artifact-prefix",
        ],
    ) {
        OptionParse::Help => return help("validate-terminal-state"),
        OptionParse::Error(message) => return usage_error(&message),
        OptionParse::Values(options) => options,
    };
    let tmpdir = PathBuf::from(
        options
            .get("--implement-tmpdir")
            .cloned()
            .unwrap_or_else(|| tmpdir(globals)),
    );
    let primary = option_or_global(&options, globals, "--primary-state-file", "");
    let state = if primary.is_empty() {
        tmpdir.join("design-failure-terminal-state.env")
    } else {
        PathBuf::from(primary)
    };
    let profile = option_or_global(&options, globals, "--profile", "implement");
    emit_result(
        "VALID",
        terminal_state_is_valid(&tmpdir, &state, profile == "generic"),
        1,
    )
}

fn validate_public(globals: &Globals, arguments: &[String]) -> ExitCode {
    let options = match parse_options(
        arguments,
        &[
            "--implement-tmpdir",
            "--public-file",
            "--tmpdir",
            "--sensitive-corpus-file",
            "--profile",
            "--artifact-prefix",
        ],
    ) {
        OptionParse::Help => return help("validate-tier-b-public-file"),
        OptionParse::Error(message) => return usage_error(&message),
        OptionParse::Values(options) => options,
    };
    if !options.contains_key("--public-file") {
        return usage_error("validate-tier-b-public-file: --public-file is required");
    }
    let inherited_tmpdir = options
        .get("--implement-tmpdir")
        .cloned()
        .unwrap_or_else(|| tmpdir(globals));
    let tmpdir = match value(&options, "--tmpdir") {
        "" => inherited_tmpdir,
        explicit => explicit.to_owned(),
    };
    let prefix = option_or_global(&options, globals, "--artifact-prefix", "");
    if !artifact_prefix_valid(prefix) {
        return usage_error("--artifact-prefix must be a simple dash token");
    }
    let valid = !value(&options, "--sensitive-corpus-file").is_empty()
        && tier_b_public_file_is_valid(
            &PathBuf::from(tmpdir),
            &PathBuf::from(value(&options, "--public-file")),
            &PathBuf::from(value(&options, "--sensitive-corpus-file")),
            prefix,
        );
    emit_result("PUBLIC_FILE_VALID", valid, 1)
}

fn detect_dev_clone(globals: &Globals, arguments: &[String]) -> ExitCode {
    let options = match parse_options(arguments, &["--implement-tmpdir", "--working-tree-root"]) {
        OptionParse::Help => return help("is-larch-dev-clone"),
        OptionParse::Error(message) => return usage_error(&message),
        OptionParse::Values(options) => options,
    };
    let tmpdir = options
        .get("--implement-tmpdir")
        .cloned()
        .unwrap_or_else(|| tmpdir(globals));
    let root = (!value(&options, "--working-tree-root").is_empty())
        .then(|| PathBuf::from(value(&options, "--working-tree-root")));
    emit_result(
        "LARCH_DEV_CLONE",
        is_larch_dev_clone(&PathBuf::from(tmpdir), root.as_deref()),
        0,
    )
}

fn parse_globals(arguments: &[String]) -> Result<(Globals, &[String]), String> {
    let mut globals = Globals::default();
    let mut index = 0;
    while arguments
        .get(index)
        .is_some_and(|argument| GLOBAL_FLAGS.contains(&argument.as_str()))
    {
        let flag = &arguments[index];
        let Some(value) = arguments.get(index + 1) else {
            return Err(format!("{flag} requires a value"));
        };
        globals.insert(flag.clone(), value.clone());
        index += 2;
    }
    let prefix = globals.get("--artifact-prefix").map_or("", String::as_str);
    if !prefix.is_empty() && !artifact_prefix_valid(prefix) {
        return Err("--artifact-prefix must be a simple dash token".to_owned());
    }
    Ok((globals, &arguments[index..]))
}

enum OptionParse {
    Help,
    Error(String),
    Values(BTreeMap<String, String>),
}

fn parse_options(arguments: &[String], known: &[&str]) -> OptionParse {
    let mut values = BTreeMap::new();
    let mut index = 0;
    while index < arguments.len() {
        let option = &arguments[index];
        if matches!(option.as_str(), "-h" | "--help") {
            return OptionParse::Help;
        }
        if let Some((flag, value)) = option.split_once('=') {
            if known.contains(&flag) {
                values.insert(flag.to_owned(), value.to_owned());
            }
            index += 1;
            continue;
        }
        if known.contains(&option.as_str()) {
            let Some(value) = arguments.get(index + 1) else {
                return OptionParse::Error(format!("{option} requires a value"));
            };
            if value.starts_with('-')
                && !value.strip_prefix('-').is_some_and(|digits| {
                    !digits.is_empty() && digits.bytes().all(|byte| byte.is_ascii_digit())
                })
            {
                return OptionParse::Error(format!("{option} requires a value"));
            }
            values.insert(option.clone(), value.clone());
            index += 2;
        } else {
            index += 1;
        }
    }
    OptionParse::Values(values)
}

fn option_or_global<'a>(
    options: &'a BTreeMap<String, String>,
    globals: &'a Globals,
    flag: &str,
    fallback: &'a str,
) -> &'a str {
    options
        .get(flag)
        .map(String::as_str)
        .or_else(|| globals.get(flag).map(String::as_str))
        .unwrap_or(fallback)
}

fn option_or_tmpdir(options: &BTreeMap<String, String>, globals: &Globals) -> String {
    options
        .get("--implement-tmpdir")
        .cloned()
        .unwrap_or_else(|| tmpdir(globals))
}

fn option_or<'a>(options: &'a BTreeMap<String, String>, flag: &str, fallback: &'a str) -> &'a str {
    options.get(flag).map_or(fallback, String::as_str)
}

fn required_options(options: &BTreeMap<String, String>, flags: &[&str]) -> Option<String> {
    flags
        .iter()
        .find(|flag| !options.contains_key(**flag))
        .map(|flag| format!("{flag} is required"))
}

fn value<'a>(options: &'a BTreeMap<String, String>, flag: &str) -> &'a str {
    options.get(flag).map_or("", String::as_str)
}

fn emit_result(key: &str, valid: bool, invalid_code: u8) -> ExitCode {
    println!("{key}={}", if valid { "true" } else { "false" });
    if valid {
        ExitCode::SUCCESS
    } else {
        ExitCode::from(invalid_code)
    }
}

fn emit_rows(rows: Vec<(String, String)>) {
    for (key, value) in rows {
        println!("{key}={value}");
    }
}

#[rustfmt::skip]
fn adapter_error(error: StallRecoveryError, generic: bool) -> ExitCode {
    match error {
        StallRecoveryError::Usage => usage_error("--artifact-prefix must be a simple dash token"),
        StallRecoveryError::Unsafe => ExitCode::from(3),
        StallRecoveryError::UnsafeDiagnostic(message) => { eprintln!("stall-recovery: {message}"); ExitCode::from(3) },
        StallRecoveryError::Failed if generic => emit_result("VALID", false, 1),
        StallRecoveryError::Failed => ExitCode::from(1),
        StallRecoveryError::Diagnostic(message) => command_error(message),
    }
}

fn usage_error(message: &str) -> ExitCode {
    eprintln!("stall-recovery: {message}");
    ExitCode::from(2)
}

fn command_error(message: &str) -> ExitCode {
    eprintln!("stall-recovery: {message}");
    ExitCode::from(1)
}

fn help(verb: &str) -> ExitCode {
    println!("Usage: larch stall-recovery {verb} [OPTIONS]");
    ExitCode::SUCCESS
}
