//! `larch rebalance-tests` pure planning and verification command boundary.

use std::{
    fs,
    io::{Read, Write as _},
    path::{Path, PathBuf},
    process::ExitCode,
};

use clap::{Args, Subcommand};
use larch_core::{plan_json, verify_json};

const MAX_INPUT_BYTES: u64 = 64 * 1024 * 1024;

#[derive(Subcommand)]
pub enum RebalanceTestsCommand {
    /// Validate baseline timing evidence and produce a pure rebalance plan.
    Plan(JsonInputArguments),
    /// Validate post-run timing evidence against a pure rebalance plan context.
    Verify(JsonInputArguments),
}

#[derive(Args)]
pub struct JsonInputArguments {
    /// JSON request. Reads standard input when omitted.
    #[arg(long)]
    input: Option<PathBuf>,
}

pub fn run(command: &RebalanceTestsCommand) -> ExitCode {
    match run_inner(command) {
        Ok((output, status)) => {
            if let Err(error) = std::io::stdout().lock().write_all(&output) {
                eprintln!("rebalance-tests: cannot write output: {error}");
                return ExitCode::from(1);
            }
            status
        }
        Err(error) => {
            eprintln!("rebalance-tests: {error}");
            ExitCode::from(1)
        }
    }
}

fn run_inner(command: &RebalanceTestsCommand) -> Result<(Vec<u8>, ExitCode), String> {
    let input = match &command {
        RebalanceTestsCommand::Plan(arguments) | RebalanceTestsCommand::Verify(arguments) => {
            read_json_input(arguments.input.as_deref())?
        }
    };
    let source = std::str::from_utf8(&input)
        .map_err(|error| format!("JSON input must be UTF-8: {error}"))?;
    let result = match command {
        RebalanceTestsCommand::Plan(_) => plan_json(source)?,
        RebalanceTestsCommand::Verify(_) => verify_json(source)?,
    };
    let mut output = result.json.into_bytes();
    output.push(b'\n');
    let status = if result.success {
        ExitCode::SUCCESS
    } else {
        ExitCode::from(1)
    };
    Ok((output, status))
}

fn read_json_input(path: Option<&Path>) -> Result<Vec<u8>, String> {
    match path {
        Some(path) => {
            let file = fs::File::open(path)
                .map_err(|error| format!("cannot read JSON input {}: {error}", path.display()))?;
            bounded_read(file, &format!("JSON input {}", path.display()))
        }
        None => bounded_read(std::io::stdin().lock(), "JSON input"),
    }
}

fn bounded_read(mut reader: impl Read, label: &str) -> Result<Vec<u8>, String> {
    let mut input = Vec::new();
    reader
        .by_ref()
        .take(MAX_INPUT_BYTES + 1)
        .read_to_end(&mut input)
        .map_err(|error| format!("cannot read {label}: {error}"))?;
    if input.len() > usize::try_from(MAX_INPUT_BYTES).expect("input limit fits usize") {
        return Err(format!("{label} exceeds the {MAX_INPUT_BYTES} byte limit"));
    }
    Ok(input)
}
