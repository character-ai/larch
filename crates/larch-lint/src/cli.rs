use std::{
    env,
    path::{Path, PathBuf},
};

use clap::{Parser, Subcommand};

use crate::{
    GitCli, Repository, registered_rule_registry,
    runner::{ExitCode, render_error, render_findings, render_rule_list, render_warnings, run},
};

/// Check larch repository policy.
#[derive(Debug, Parser)]
#[command(name = "larch-lint", version)]
struct Cli {
    /// Resolve the repository from this directory instead of the current directory.
    #[arg(long, value_name = "PATH")]
    root: Option<PathBuf>,

    #[command(subcommand)]
    command: Command,
}

#[derive(Debug, Subcommand)]
enum Command {
    /// Run every registered rule.
    All,
    /// Run one registered rule.
    Rule {
        /// Registered rule name.
        name: String,
    },
    /// List registered rules in name order.
    Rules,
}

/// Run the production command-line interface.
#[must_use]
pub fn run_cli() -> i32 {
    let cli = Cli::parse();
    match cli.command {
        Command::Rules => match registered_rule_registry() {
            Ok(registry) => match render_rule_list(&registry, &mut std::io::stdout()) {
                Ok(()) => ExitCode::Clean.as_i32(),
                Err(error) => render_error(&error, &mut std::io::stderr()).as_i32(),
            },
            Err(error) => render_error(&error, &mut std::io::stderr()).as_i32(),
        },
        Command::All => execute_all(cli.root.as_deref()),
        Command::Rule { name } => execute_named(&name, cli.root.as_deref()),
    }
}

fn execute_all(root: Option<&Path>) -> i32 {
    let repository = match discover_repository(root) {
        Ok(repository) => repository,
        Err(exit) => return exit,
    };
    let registry = match registered_rule_registry() {
        Ok(registry) => registry,
        Err(error) => return render_error(&error, &mut std::io::stderr()).as_i32(),
    };
    if let Err(error) = crate::validate_migration_ledger(&repository, &registry) {
        return render_error(&error, &mut std::io::stderr()).as_i32();
    }
    execute(&repository, registry.iter(), false)
}

fn execute_named(name: &str, root: Option<&Path>) -> i32 {
    let registry = match registered_rule_registry() {
        Ok(registry) => registry,
        Err(error) => return render_error(&error, &mut std::io::stderr()).as_i32(),
    };
    let Some(rule) = registry.get(name) else {
        return render_error(
            &crate::runner::LintError::new(format!("unknown rule: {name}")),
            &mut std::io::stderr(),
        )
        .as_i32();
    };
    let repository = match discover_repository(root) {
        Ok(repository) => repository,
        Err(exit) => return exit,
    };
    if let Err(error) = crate::validate_migration_ledger(&repository, &registry) {
        return render_error(&error, &mut std::io::stderr()).as_i32();
    }
    execute(
        &repository,
        std::iter::once(rule),
        name == "retired-scripts",
    )
}

fn discover_repository(root: Option<&Path>) -> Result<Repository, i32> {
    let cwd = match root
        .map(Path::to_path_buf)
        .map_or_else(env::current_dir, Ok)
    {
        Ok(cwd) => cwd,
        Err(error) => {
            return Err(render_error(
                &crate::runner::LintError::new(format!("cannot read current directory: {error}")),
                &mut std::io::stderr(),
            )
            .as_i32());
        }
    };
    Repository::discover(&GitCli, &cwd)
        .map_err(|error| render_error(&error, &mut std::io::stderr()).as_i32())
}

fn execute<'rule>(
    repository: &Repository,
    rules: impl IntoIterator<Item = &'rule dyn crate::Rule>,
    render_contract: bool,
) -> i32 {
    let report = match run(repository, rules) {
        Ok(report) => report,
        Err(error) => return render_error(&error, &mut std::io::stderr()).as_i32(),
    };
    if let Err(error) = render_warnings(report.warnings(), &mut std::io::stderr()) {
        return render_error(&error, &mut std::io::stderr()).as_i32();
    }
    let exit = crate::runner::finding_exit_code(report.findings());
    if exit == ExitCode::Findings
        && let Err(error) = render_findings(report.findings(), &mut std::io::stdout())
    {
        return render_error(&error, &mut std::io::stderr()).as_i32();
    }
    if render_contract
        && let Err(error) =
            crate::render_contract_lines(report.contract_lines(), &mut std::io::stdout())
    {
        return render_error(&error, &mut std::io::stderr()).as_i32();
    }
    exit.as_i32()
}

#[cfg(test)]
mod tests {
    use clap::CommandFactory;

    use super::Cli;

    #[test]
    fn command_definition_is_valid() {
        Cli::command().debug_assert();
    }
}
