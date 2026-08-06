//! `external-defaults` commands composed over the shared role table.

use std::{collections::BTreeMap, env, process::ExitCode};

use clap::{Args, Subcommand};
use larch_core::{doc_rows, parse_bool_flag, resolve_vendor, role_default};

#[derive(Subcommand)]
pub enum ExternalDefaultsCommand {
    /// Emit documentation rows for every role with a doc phase.
    Docs(DocsArguments),
    /// Resolve the first available vendor for a `first_available` role.
    #[command(name = "resolve-vendor")]
    ResolveVendor(ResolveVendorArguments),
    /// Emit one role's machine-readable summary.
    Role(RoleArguments),
}

#[derive(Args)]
pub struct DocsArguments {
    #[arg(trailing_var_arg = true, allow_hyphen_values = true)]
    extra: Vec<String>,
}

#[derive(Args)]
pub struct ResolveVendorArguments {
    #[arg(long)]
    role: String,
    #[arg(long = "codex-present", default_value = "false")]
    codex_present: String,
    #[arg(long = "cursor-present", default_value = "false")]
    cursor_present: String,
}

#[derive(Args)]
pub struct RoleArguments {
    #[arg(long)]
    role: String,
}

/// Run one external-defaults command.
pub fn run(command: ExternalDefaultsCommand) -> ExitCode {
    match command {
        ExternalDefaultsCommand::Docs(arguments) => docs(&arguments),
        ExternalDefaultsCommand::ResolveVendor(arguments) => resolve_vendor_command(&arguments),
        ExternalDefaultsCommand::Role(arguments) => role_command(&arguments),
    }
}

fn docs(arguments: &DocsArguments) -> ExitCode {
    if !arguments.extra.is_empty() {
        eprintln!("external-defaults docs: no arguments expected");
        return ExitCode::from(2);
    }
    let rows = doc_rows();
    println!("DOC_ROW_COUNT={}", rows.len());
    for role in rows {
        println!(
            "DOC_ROW={}\t{}\t{}\t{}\t{}",
            role.role_id, role.doc_phase, role.doc_role, role.doc_skills, role.doc_fallback
        );
    }
    ExitCode::SUCCESS
}

fn role_command(arguments: &RoleArguments) -> ExitCode {
    let role = match role_default(&arguments.role) {
        Ok(role) => role,
        Err(error) => {
            eprintln!("ERROR={error}");
            return ExitCode::from(2);
        }
    };
    println!("ROLE={}", role.role_id);
    println!("KIND={}", role.kind.as_str());
    if !role.order.is_empty() {
        println!("ORDER={}", role.order.join(","));
    }
    if !role.env_override.is_empty() {
        println!("ENV_OVERRIDE={}", role.env_override);
    }
    if role.slot_count > 0 {
        println!("SLOT_COUNT={}", role.slot_count);
    }
    if role.voter_count > 0 {
        println!("VOTER_COUNT={}", role.voter_count);
    }
    ExitCode::SUCCESS
}

fn resolve_vendor_command(arguments: &ResolveVendorArguments) -> ExitCode {
    let codex_present = match parse_bool_flag(&arguments.codex_present, "--codex-present") {
        Ok(value) => value,
        Err(error) => {
            eprintln!("ERROR={error}");
            return ExitCode::from(2);
        }
    };
    let cursor_present = match parse_bool_flag(&arguments.cursor_present, "--cursor-present") {
        Ok(value) => value,
        Err(error) => {
            eprintln!("ERROR={error}");
            return ExitCode::from(2);
        }
    };
    let env_map = env::vars().collect::<BTreeMap<_, _>>();
    let result = match resolve_vendor(&arguments.role, &env_map, codex_present, cursor_present) {
        Ok(result) => result,
        Err(error) => {
            eprintln!("ERROR={error}");
            return ExitCode::from(2);
        }
    };
    println!("ROLE={}", arguments.role);
    println!("VENDOR={}", result.vendor);
    if !result.skip_reason.is_empty() {
        println!("SKIP_REASON={}", result.skip_reason);
    }
    ExitCode::SUCCESS
}
