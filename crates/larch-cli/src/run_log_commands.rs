//! `run-log` command boundary.

use larch_core::validate_run_log_slug;
use std::{
    ffi::OsString,
    io::Write as _,
    process::ExitCode,
};

/// Run the Rust-owned `run-log validate-run-id` command.
pub fn validate_run_id(arguments: &[OsString]) -> ExitCode {
    match parse_validate_run_id(arguments) {
        ParseOutcome::Help => {
            println!("Usage: run-log validate-run-id --run-id RUN_ID");
            ExitCode::SUCCESS
        }
        ParseOutcome::Error(message) => {
            eprintln!("{message}");
            // Match Python argparse missing-required exit code.
            ExitCode::from(2)
        }
        ParseOutcome::Ok(run_id) => {
            let valid = validate_run_log_slug(&run_id);
            if writeln!(
                std::io::stdout(),
                "VALID={}",
                if valid { "true" } else { "false" }
            )
            .is_err()
            {
                return ExitCode::FAILURE;
            }
            ExitCode::SUCCESS
        }
    }
}

enum ParseOutcome {
    Help,
    Error(String),
    Ok(String),
}

fn parse_validate_run_id(arguments: &[OsString]) -> ParseOutcome {
    let mut run_id: Option<String> = None;
    let mut index = 0;
    while index < arguments.len() {
        let Some(arg) = arguments[index].to_str() else {
            return ParseOutcome::Error(format!(
                "unknown argument: {}",
                arguments[index].to_string_lossy()
            ));
        };
        if arg == "-h" || arg == "--help" {
            return ParseOutcome::Help;
        }
        if let Some(value) = arg.strip_prefix("--run-id=") {
            if run_id.replace(value.to_owned()).is_some() {
                return ParseOutcome::Error("argument --run-id: conflicting values".to_owned());
            }
            index += 1;
            continue;
        }
        if arg == "--run-id" {
            index += 1;
            let Some(value) = arguments.get(index).and_then(|item| item.to_str()) else {
                return ParseOutcome::Error("argument --run-id: expected one argument".to_owned());
            };
            if run_id.replace(value.to_owned()).is_some() {
                return ParseOutcome::Error("argument --run-id: conflicting values".to_owned());
            }
            index += 1;
            continue;
        }
        return ParseOutcome::Error(format!("unrecognized arguments: {arg}"));
    }
    run_id.map_or_else(
        || ParseOutcome::Error("the following arguments are required: --run-id".to_owned()),
        ParseOutcome::Ok,
    )
}

#[cfg(test)]
mod tests {
    use super::{ParseOutcome, parse_validate_run_id};
    use std::ffi::OsString;

    fn args(values: &[&str]) -> Vec<OsString> {
        values.iter().map(OsString::from).collect()
    }

    #[test]
    fn parses_inline_and_split_run_id() {
        match parse_validate_run_id(&args(&["--run-id=-abc123"])) {
            ParseOutcome::Ok(value) => assert_eq!(value, "-abc123"),
            ParseOutcome::Help | ParseOutcome::Error(_) => panic!("expected ok"),
        }
        match parse_validate_run_id(&args(&["--run-id", "run-1"])) {
            ParseOutcome::Ok(value) => assert_eq!(value, "run-1"),
            ParseOutcome::Help | ParseOutcome::Error(_) => panic!("expected ok"),
        }
    }
}
