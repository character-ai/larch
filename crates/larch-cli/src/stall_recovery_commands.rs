//! Thin compatibility boundary for Rust-owned stall-recovery commands.
use larch_adapters::stall_recovery::{
    StateMutationError, clear_stall, is_larch_dev_clone, seed_terminal_state,
    terminal_state_is_valid, tier_b_public_file_is_valid,
};
use larch_core::{artifact_prefix_valid, token_valid};
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
        "clear-stall" => clear(&globals, command_arguments),
        "seed-terminal-state" => seed(&globals, command_arguments),
        "validate-token" => validate_token(&globals, command_arguments),
        "validate-terminal-state" => validate_terminal(&globals, command_arguments),
        "validate-tier-b-public-file" => validate_public(&globals, command_arguments),
        "is-larch-dev-clone" => detect_dev_clone(&globals, command_arguments),
        other => usage_error(&format!("unknown subcommand: {other}")),
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
            if value.starts_with('-') {
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

fn usage_error(message: &str) -> ExitCode {
    eprintln!("stall-recovery: {message}");
    ExitCode::from(2)
}

fn help(verb: &str) -> ExitCode {
    println!("Usage: larch stall-recovery {verb} [OPTIONS]");
    ExitCode::SUCCESS
}
