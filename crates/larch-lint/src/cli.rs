use std::{
    env,
    io::{self, Write},
    path::{Path, PathBuf},
};

use clap::{Args, Subcommand, ValueEnum};

use crate::{
    GitCli, LintError, Repository, registered_rule_registry,
    runner::{ExitCode, render_error, render_findings, render_rule_list, render_warnings, run},
};

/// Arguments for the `larch lint` command domain.
#[derive(Debug, Args)]
pub struct LintArguments {
    /// Resolve the repository from this directory instead of the current directory.
    #[arg(long, value_name = "PATH")]
    root: Option<PathBuf>,

    #[command(subcommand)]
    command: Command,
}

impl LintArguments {
    /// Split out a Gitleaks request without losing other lint invocations.
    #[must_use]
    pub fn into_dispatch(self) -> LintDispatch {
        match self {
            Self {
                command: Command::Gitleaks(arguments),
                ..
            } => LintDispatch::Gitleaks(arguments),
            arguments => LintDispatch::Native(arguments),
        }
    }
}

/// A lint command split between the Rust-native scanner and rule engine.
#[derive(Debug)]
pub enum LintDispatch {
    /// Invoke the Gitleaks scanner owned by the CLI binary.
    Gitleaks(GitleaksArguments),
    /// Invoke a regular repository lint rule.
    Native(LintArguments),
}

/// Arguments for the checksum-pinned Gitleaks scanner.
#[derive(Clone, Debug, Args)]
pub struct GitleaksArguments {
    /// Select a preparation-only, working-tree, or commit-history scan.
    #[arg(long, value_enum)]
    mode: GitleaksMode,
    /// Bounded Git revision range required for a history scan.
    #[arg(long)]
    log_opts: Option<String>,
    /// Resolve the repository and `.gitleaks.toml` from this directory.
    #[arg(long, value_name = "PATH")]
    repo_root: Option<PathBuf>,
    /// Store the verified release binary under this directory.
    #[arg(long, value_name = "PATH")]
    cache_dir: Option<PathBuf>,
}

impl GitleaksArguments {
    /// Build a scanner request for an embedding caller or focused test.
    #[must_use]
    pub const fn new(
        mode: GitleaksMode,
        log_opts: Option<String>,
        repo_root: Option<PathBuf>,
        cache_dir: Option<PathBuf>,
    ) -> Self {
        Self {
            mode,
            log_opts,
            repo_root,
            cache_dir,
        }
    }

    /// Return the requested scanner mode.
    #[must_use]
    pub const fn mode(&self) -> GitleaksMode {
        self.mode
    }

    /// Return the optional history range.
    #[must_use]
    pub fn log_opts(&self) -> Option<&str> {
        self.log_opts.as_deref()
    }

    /// Return the optional repository-root override.
    #[must_use]
    pub fn repo_root(&self) -> Option<&Path> {
        self.repo_root.as_deref()
    }

    /// Return the optional cache-directory override.
    #[must_use]
    pub fn cache_dir(&self) -> Option<&Path> {
        self.cache_dir.as_deref()
    }
}

/// Scan mode for the checksum-pinned Gitleaks command.
#[derive(Clone, Copy, Debug, Eq, PartialEq, ValueEnum)]
pub enum GitleaksMode {
    /// Verify the release artifact and report its exact version.
    Verify,
    /// Scan the uncommitted working tree with `--no-git`.
    WorkingTree,
    /// Scan a bounded Git revision range.
    History,
}

#[derive(Debug, Subcommand)]
enum Command {
    /// Verify or run the checksum-pinned Gitleaks scanner.
    Gitleaks(GitleaksArguments),
    /// Run every registered rule.
    All {
        /// Write deterministic per-rule timing evidence to this TSV file.
        #[arg(long, value_name = "PATH")]
        timing_file: Option<PathBuf>,
    },
    /// Run one registered rule.
    Rule {
        /// Registered rule name.
        name: String,
    },
    /// List registered rules in name order.
    Rules,
    /// Maintain or report the Python-to-Rust command ownership ledger.
    #[command(name = "command-registry", subcommand)]
    Registry(CommandRegistryCommand),
}

#[derive(Clone, Debug, Subcommand)]
enum CommandRegistryCommand {
    /// Refresh Python command metadata and production caller inventory.
    Sync {
        /// Roadmap planning issue assigned only to newly discovered commands.
        #[arg(long, value_name = "NUMBER", value_parser = clap::value_parser!(u64).range(1..))]
        planning_issue: u64,
    },
    /// Render migration progress for the Chief migration issue.
    Report,
    /// Compare issue command evidence with registry migration ownership.
    Audit {
        /// JSON input produced from canonical issue owner and plan parsers.
        #[arg(long, value_name = "PATH")]
        input: PathBuf,
    },
}

/// Run `larch lint` with the process working directory and standard streams.
#[must_use]
pub fn run_cli(arguments: LintArguments) -> ExitCode {
    let mut stdout = io::stdout().lock();
    let mut stderr = io::stderr().lock();
    run_cli_with_io(arguments, None, &mut stdout, &mut stderr)
}

/// Run the lint domain with explicit process boundaries.
///
/// This is public so integration tests can preserve per-command working
/// directories without changing global process state.
#[doc(hidden)]
#[must_use]
pub fn run_cli_with_io(
    arguments: LintArguments,
    current_dir: Option<&Path>,
    stdout: &mut impl Write,
    stderr: &mut impl Write,
) -> ExitCode {
    match arguments.command {
        Command::Gitleaks(_) => render_error(
            &LintError::new("Gitleaks must run through the larch executable"),
            stderr,
        ),
        Command::Rules => match registered_rule_registry() {
            Ok(registry) => match render_rule_list(&registry, stdout) {
                Ok(()) => ExitCode::Clean,
                Err(error) => render_error(&error, stderr),
            },
            Err(error) => render_error(&error, stderr),
        },
        Command::All { timing_file } => execute_all(
            arguments.root.as_deref(),
            current_dir,
            timing_file.as_deref(),
            stdout,
            stderr,
        ),
        Command::Rule { name } => execute_named(
            &name,
            arguments.root.as_deref(),
            current_dir,
            stdout,
            stderr,
        ),
        Command::Registry(command) => execute_command_registry(
            command,
            arguments.root.as_deref(),
            current_dir,
            stdout,
            stderr,
        ),
    }
}

fn execute_command_registry(
    command: CommandRegistryCommand,
    root: Option<&Path>,
    current_dir: Option<&Path>,
    stdout: &mut impl Write,
    stderr: &mut impl Write,
) -> ExitCode {
    let repository = match discover_repository(root, current_dir, stderr) {
        Ok(repository) => repository,
        Err(exit) => return exit,
    };
    let result = match command {
        CommandRegistryCommand::Sync { planning_issue } => {
            crate::sync_command_registry(&repository, planning_issue)
                .and_then(|summary| write_command_output(stdout, &summary))
        }
        CommandRegistryCommand::Report => crate::render_command_progress(&repository)
            .and_then(|report| write_command_output(stdout, &report)),
        CommandRegistryCommand::Audit { input } => {
            match crate::audit_migration_issue_commands(&repository, &input) {
                Ok(output) => {
                    if let Err(error) = render_findings(output.findings(), stdout) {
                        return render_error(&error, stderr);
                    }
                    return crate::finding_exit_code(output.findings());
                }
                Err(error) => Err(error),
            }
        }
    };
    match result {
        Ok(()) => ExitCode::Clean,
        Err(error) => render_error(&error, stderr),
    }
}

fn write_command_output(output: &mut impl Write, value: &str) -> Result<(), LintError> {
    output
        .write_all(value.as_bytes())
        .map_err(|error| LintError::new(format!("cannot write command output: {error}")))
}

fn execute_all(
    root: Option<&Path>,
    current_dir: Option<&Path>,
    timing_file: Option<&Path>,
    stdout: &mut impl Write,
    stderr: &mut impl Write,
) -> ExitCode {
    let repository = match discover_repository(root, current_dir, stderr) {
        Ok(repository) => repository,
        Err(exit) => return exit,
    };
    let registry = match registered_rule_registry() {
        Ok(registry) => registry,
        Err(error) => return render_error(&error, stderr),
    };
    if let Err(error) = crate::validate_migration_ledger(&repository, &registry) {
        return render_error(&error, stderr);
    }
    execute(
        &repository,
        registry.iter(),
        false,
        timing_file,
        stdout,
        stderr,
    )
}

fn execute_named(
    name: &str,
    root: Option<&Path>,
    current_dir: Option<&Path>,
    stdout: &mut impl Write,
    stderr: &mut impl Write,
) -> ExitCode {
    let registry = match registered_rule_registry() {
        Ok(registry) => registry,
        Err(error) => return render_error(&error, stderr),
    };
    let Some(rule) = registry.get(name) else {
        return render_error(&LintError::new(format!("unknown rule: {name}")), stderr);
    };
    let repository = match discover_repository(root, current_dir, stderr) {
        Ok(repository) => repository,
        Err(exit) => return exit,
    };
    if let Err(error) = crate::validate_migration_ledger(&repository, &registry) {
        return render_error(&error, stderr);
    }
    execute(
        &repository,
        std::iter::once(rule),
        name == "retired-scripts",
        None,
        stdout,
        stderr,
    )
}

fn discover_repository(
    root: Option<&Path>,
    current_dir: Option<&Path>,
    stderr: &mut impl Write,
) -> Result<Repository, ExitCode> {
    let start = match (root, current_dir) {
        (Some(root), _) if root.is_absolute() => root.to_path_buf(),
        (Some(root), Some(current_dir)) => current_dir.join(root),
        (None, Some(current_dir)) => current_dir.to_path_buf(),
        (root, None) => {
            let current_dir = env::current_dir().map_err(|error| {
                render_error(
                    &LintError::new(format!("cannot read current directory: {error}")),
                    stderr,
                )
            })?;
            root.map_or_else(|| current_dir.clone(), |root| current_dir.join(root))
        }
    };
    Repository::discover(&GitCli, &start).map_err(|error| render_error(&error, stderr))
}

fn execute<'rule>(
    repository: &Repository,
    rules: impl IntoIterator<Item = &'rule dyn crate::Rule>,
    render_contract: bool,
    timing_file: Option<&Path>,
    stdout: &mut impl Write,
    stderr: &mut impl Write,
) -> ExitCode {
    let report = match run(repository, rules) {
        Ok(report) => report,
        Err(error) => return render_error(&error, stderr),
    };
    if let Some(timing_file) = timing_file
        && let Err(error) = write_rule_timings(&report, timing_file)
    {
        return render_error(&error, stderr);
    }
    if let Err(error) = render_warnings(report.warnings(), stderr) {
        return render_error(&error, stderr);
    }
    let exit = crate::finding_exit_code(report.findings());
    if exit == ExitCode::Findings
        && let Err(error) = render_findings(report.findings(), stdout)
    {
        return render_error(&error, stderr);
    }
    if render_contract
        && let Err(error) = crate::render_contract_lines(report.contract_lines(), stdout)
    {
        return render_error(&error, stderr);
    }
    exit
}

fn write_rule_timings(report: &crate::LintReport, path: &Path) -> Result<(), LintError> {
    let mut output = String::from("rule\tmilliseconds\n");
    for timing in report.rule_timings() {
        use std::fmt::Write as _;

        writeln!(output, "{}\t{}", timing.name(), timing.milliseconds())
            .map_err(|error| LintError::new(format!("cannot render rule timings: {error}")))?;
    }
    std::fs::write(path, output).map_err(|error| {
        LintError::new(format!(
            "cannot write rule timings {}: {error}",
            path.display()
        ))
    })
}
