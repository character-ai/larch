//! Vendor-agent commands composed over the core diagnostic use cases.

use std::{path::PathBuf, process::ExitCode};

use clap::{Args, Subcommand};
use larch_adapters::vendor_diagnostics::parse_codex_usage_file;
use larch_core::emit_kv;

#[derive(Subcommand)]
pub enum AgentCommand {
    /// Sum Codex token usage from a `--json` events stream.
    ParseCodexUsage(ParseCodexUsageArguments),
}

#[derive(Args)]
pub struct ParseCodexUsageArguments {
    /// Codex events JSONL file written by the launcher.
    events_jsonl: PathBuf,
}

/// Run one agent command and return its process exit status.
pub fn run(command: AgentCommand) -> ExitCode {
    match command {
        AgentCommand::ParseCodexUsage(arguments) => parse_codex_usage(&arguments),
    }
}

fn parse_codex_usage(arguments: &ParseCodexUsageArguments) -> ExitCode {
    let totals = match parse_codex_usage_file(&arguments.events_jsonl) {
        Ok(totals) => totals,
        Err(error) => {
            eprintln!("agent parse-codex-usage: {error}");
            return ExitCode::from(1);
        }
    };
    emit_kv("INPUT", &totals.uncached_input_tokens().to_string());
    emit_kv("CACHED_INPUT", &totals.cached_input_tokens().to_string());
    emit_kv("OUTPUT", &totals.output_tokens().to_string());
    emit_kv("TOTAL", &totals.total_tokens().to_string());
    ExitCode::SUCCESS
}
