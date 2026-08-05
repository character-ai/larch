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
    let mut pending = arguments.iter();
    while let Some(raw) = pending.next() {
        let Some(flag) = raw.to_str() else {
            return ParseOutcome::Error(format!(
                "unknown argument: {}",
                raw.to_string_lossy()
            ));
        };
        if matches!(flag, "-h" | "--help") {
            return ParseOutcome::Help;
        }
        let value = if let Some(inline) = flag.strip_prefix("--run-id=") {
            inline
        } else if flag == "--run-id" {
            let Some(next) = pending.next() else {
                return ParseOutcome::Error("argument --run-id: expected one argument".to_owned());
            };
            let Some(text) = next.to_str() else {
                return ParseOutcome::Error(format!(
                    "argument --run-id: expected one argument, got {}",
                    next.to_string_lossy()
                ));
            };
            text
        } else {
            return ParseOutcome::Error(format!("unrecognized arguments: {flag}"));
        };
        if run_id.replace(value.to_owned()).is_some() {
            return ParseOutcome::Error("argument --run-id: conflicting values".to_owned());
        }
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
