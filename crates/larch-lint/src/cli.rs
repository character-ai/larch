use std::{
    env,
    path::{Path, PathBuf},
};

use clap::{Parser, Subcommand};

use crate::{
    GitCli, Repository,
    runner::{ExitCode, RuleRegistry, render_error, render_findings, render_rule_list, run},
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
    let rules: [&dyn crate::Rule; 0] = [];
    let registry = match RuleRegistry::new(&rules) {
        Ok(registry) => registry,
        Err(error) => return render_error(&error, &mut std::io::stderr()).as_i32(),
    };
    match cli.command {
        Command::Rules => match render_rule_list(&registry, &mut std::io::stdout()) {
            Ok(()) => ExitCode::Clean.as_i32(),
            Err(error) => render_error(&error, &mut std::io::stderr()).as_i32(),
        },
        Command::All => execute(registry.iter(), cli.root.as_deref()),
        Command::Rule { name } => registry.get(&name).map_or_else(
            || {
                render_error(
                    &crate::runner::LintError::new(format!("unknown rule: {name}")),
                    &mut std::io::stderr(),
                )
                .as_i32()
            },
            |rule| execute(std::iter::once(rule), cli.root.as_deref()),
        ),
    }
}

fn execute<'rule>(
    rules: impl IntoIterator<Item = &'rule dyn crate::Rule>,
    root: Option<&Path>,
) -> i32 {
    let cwd = match root
        .map(Path::to_path_buf)
        .map_or_else(env::current_dir, Ok)
    {
        Ok(cwd) => cwd,
        Err(error) => {
            return render_error(
                &crate::runner::LintError::new(format!("cannot read current directory: {error}")),
                &mut std::io::stderr(),
            )
            .as_i32();
        }
    };
    let repository = match Repository::discover(&GitCli, &cwd) {
        Ok(repository) => repository,
        Err(error) => return render_error(&error, &mut std::io::stderr()).as_i32(),
    };
    let findings = match run(&repository, rules) {
        Ok(findings) => findings,
        Err(error) => return render_error(&error, &mut std::io::stderr()).as_i32(),
    };
    let exit = crate::runner::finding_exit_code(&findings);
    if exit == ExitCode::Clean {
        exit.as_i32()
    } else if let Err(error) = render_findings(&findings, &mut std::io::stdout()) {
        render_error(&error, &mut std::io::stderr()).as_i32()
    } else {
        exit.as_i32()
    }
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
