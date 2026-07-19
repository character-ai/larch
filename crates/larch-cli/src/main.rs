use std::{
    collections::BTreeMap, ffi::OsString, fmt::Write as _, fs, io::ErrorKind, io::Write as _,
    path::Path, process::ExitCode,
};

use clap::{Args, CommandFactory, FromArgMatches, Parser, Subcommand};
use larch_core::{ChangeKind, RepositoryStatus, StatusOptions};

mod release_plugin_runtime;

#[derive(Parser)]
#[command(
    name = "larch",
    about = "Larch workflow automation",
    arg_required_else_help = true,
    subcommand_required = true
)]
struct Cli {
    #[command(subcommand)]
    domain: Domain,
}

#[derive(Subcommand)]
enum Domain {
    /// Internal bootstrap commands used before installation completes.
    #[command(subcommand, hide = true)]
    Bootstrap(BootstrapCommand),
    /// Non-production commands that exercise dispatcher wiring.
    #[command(subcommand)]
    Example(ExampleCommand),
    /// Local repository status and snapshot operations.
    #[command(subcommand)]
    Git(GitCommand),
    /// Release-maintenance commands.
    #[command(subcommand)]
    Release(ReleaseCommand),
    /// GitHub workflow helper commands.
    #[command(subcommand)]
    Gh(GhCommand),
    /// Upgrade the installed larch plugin and executable.
    #[command(subcommand)]
    UpgradeLarch(UpgradeLarchCommand),
}

#[derive(Subcommand)]
enum GitCommand {
    /// Print the files and index stages that are currently conflicted.
    ConflictFiles,
    /// Report whether the worktree is clean using machine-readable key/value rows.
    CleanTree(CleanTreeArguments),
    /// Atomically write the sorted untracked-path baseline to an output file.
    SnapshotUntracked(SnapshotUntrackedArguments),
}

#[derive(Args, Clone, Copy)]
struct CleanTreeArguments {
    /// Treat a repository probe failure as an error instead of a clean tree.
    #[arg(long)]
    fail_closed: bool,
}

#[derive(Args)]
struct SnapshotUntrackedArguments {
    /// File that receives the sorted untracked-path baseline.
    #[arg(long)]
    output: Option<std::path::PathBuf>,
    /// Separate output paths with NUL bytes rather than line feeds.
    #[arg(long)]
    nul: bool,
}

#[derive(Subcommand)]
enum BootstrapCommand {
    /// Print the compiled version and target as machine-readable JSON.
    SelfCheck,
}

#[derive(Subcommand)]
enum ExampleCommand {
    /// Print a message through the core library.
    Echo(EchoArguments),
}

#[derive(Subcommand)]
enum ReleaseCommand {
    /// Generate or validate the runtime-only plugin projection.
    PluginRuntime(PluginRuntimeArguments),
}

#[derive(Subcommand)]
enum UpgradeLarchCommand {
    /// Resolve the cache root used by release Step 7.
    ReleaseStep7Root(ReleaseStep7Arguments),
    /// Upgrade to the latest verified stable release.
    Run,
    /// Print the legacy sparse-checkout allowlist.
    SparseDirs,
}

#[derive(Args)]
struct ReleaseStep7Arguments {
    /// Current version used only to disambiguate one cache directory.
    #[arg(long, conflicts_with = "positional_current_version")]
    current_version: Option<String>,
    /// Backward-compatible positional spelling of the current version.
    #[arg(conflicts_with = "current_version")]
    positional_current_version: Option<String>,
}

#[derive(Args)]
struct PluginRuntimeArguments {
    /// Validate projection drift without changing the worktree.
    #[arg(long)]
    check: bool,
}

#[derive(Subcommand)]
enum GhCommand {
    /// Print the complete log archive for a workflow run.
    RunLogs(RunLogsArguments),
    /// Print the retained workflow-path placeholder.
    WorkflowPath,
}

#[derive(Args)]
struct RunLogsArguments {
    /// Numeric GitHub Actions workflow run identifier.
    #[arg(long)]
    run_id: u64,
    /// GitHub repository in OWNER/REPO form.
    #[arg(long = "repo", value_parser = parse_repository)]
    repository: larch_core::GitHubRepositoryRef,
}

#[derive(Args)]
struct EchoArguments {
    /// Message to print.
    message: String,
}

fn run(
    cli: Cli,
    metadata: larch_core::BuildMetadata,
) -> Result<ExitCode, larch_adapters::upgrade_larch::Failure> {
    match cli.domain {
        Domain::Bootstrap(BootstrapCommand::SelfCheck) => {
            println!("{}", larch_core::bootstrap_self_check(metadata));
            Ok(ExitCode::SUCCESS)
        }
        Domain::Example(ExampleCommand::Echo(arguments)) => {
            println!("{}", larch_core::example::echo(&arguments.message));
            Ok(ExitCode::SUCCESS)
        }
        Domain::Git(command) => run_git(command).map_err(command_failure),
        Domain::Release(ReleaseCommand::PluginRuntime(arguments)) => {
            release_plugin_runtime::run(arguments.check)
                .map(|()| ExitCode::SUCCESS)
                .map_err(command_failure)
        }
        Domain::Gh(GhCommand::WorkflowPath) => {
            print!("{}", larch_core::workflow_path());
            Ok(ExitCode::SUCCESS)
        }
        Domain::Gh(GhCommand::RunLogs(arguments)) => Ok(run_logs(&arguments)),
        Domain::UpgradeLarch(command) => match command {
            UpgradeLarchCommand::ReleaseStep7Root(arguments) => {
                let version = arguments
                    .current_version
                    .as_deref()
                    .or(arguments.positional_current_version.as_deref());
                larch_adapters::upgrade_larch::release_step7_root(version)
                    .map(|()| ExitCode::SUCCESS)
            }
            UpgradeLarchCommand::Run => {
                larch_adapters::upgrade_larch::run().map(|()| ExitCode::SUCCESS)
            }
            UpgradeLarchCommand::SparseDirs => {
                larch_adapters::upgrade_larch::sparse_dirs();
                Ok(ExitCode::SUCCESS)
            }
        },
    }
}

const fn command_failure(message: String) -> larch_adapters::upgrade_larch::Failure {
    larch_adapters::upgrade_larch::Failure { code: 1, message }
}

fn run_logs(arguments: &RunLogsArguments) -> ExitCode {
    let output = match larch_adapters::runtime::LarchRuntime::new() {
        Ok(runtime) => runtime.block_on(async {
            let service = match larch_adapters::github::OctocrabGitHubService::from_environment() {
                Ok(service) => service,
                Err(error) => {
                    return larch_core::run_logs_setup_failure(
                        &arguments.repository,
                        arguments.run_id,
                        &error,
                    );
                }
            };
            let cancellation = larch_adapters::runtime::Cancellation::new();
            larch_core::run_logs(
                &service,
                &arguments.repository,
                arguments.run_id,
                &cancellation,
            )
            .await
        }),
        Err(error) => larch_core::run_logs_setup_failure(
            &arguments.repository,
            arguments.run_id,
            format!("cannot initialize larch runtime: {error}"),
        ),
    };
    std::io::stdout()
        .write_all(output.stdout())
        .expect("write command output");
    ExitCode::from(output.exit_code())
}

fn parse_repository(value: &str) -> Result<larch_core::GitHubRepositoryRef, String> {
    let Some((owner, name)) = value.split_once('/') else {
        return Err(String::from("repository must use OWNER/REPO form"));
    };
    if name.contains('/') {
        return Err(String::from("repository must use OWNER/REPO form"));
    }
    larch_core::GitHubRepositoryRef::new(owner, name).map_err(|error| error.to_string())
}

fn run_git(command: GitCommand) -> Result<ExitCode, String> {
    match command {
        GitCommand::ConflictFiles => {
            conflict_files()?;
            Ok(ExitCode::SUCCESS)
        }
        GitCommand::CleanTree(arguments) => clean_tree(arguments),
        GitCommand::SnapshotUntracked(arguments) => {
            snapshot_untracked(arguments);
            Ok(ExitCode::SUCCESS)
        }
    }
}

fn repository_status() -> Result<RepositoryStatus, larch_core::RepositoryError> {
    larch_adapters::git::GixRepository::discover(".")?.local_status(&StatusOptions::default())
}

fn conflict_files() -> Result<(), String> {
    let status = repository_status().map_err(|error| error.to_string())?;
    for entry in status.unmerged {
        println!("FILE={}", display_path(entry.path.as_bytes()));
        for stage in 1..=3 {
            println!(
                "STAGE_{stage}={}",
                entry.stages.iter().any(|item| item.stage == stage)
            );
        }
        println!();
    }
    Ok(())
}

fn clean_tree(arguments: CleanTreeArguments) -> Result<ExitCode, String> {
    match repository_status() {
        Ok(status) => {
            if status.is_dirty() {
                println!("CLEAN=false");
                println!("DIRTY_OUT={}", one_line(&porcelain(&status)));
            } else {
                println!("CLEAN=true");
            }
            Ok(ExitCode::SUCCESS)
        }
        Err(_error) if !arguments.fail_closed => {
            println!("CLEAN=true");
            Ok(ExitCode::SUCCESS)
        }
        Err(error) => {
            println!("CLEAN=unknown");
            println!(
                "PROBE_ERROR=git exited 1 ({})",
                one_line(&error.to_string())
            );
            Err(String::new())
        }
    }
}

fn snapshot_untracked(arguments: SnapshotUntrackedArguments) {
    let Some(output) = arguments.output else {
        eprintln!("snapshot-untracked.sh: --output is required");
        return;
    };
    let mut temporary_name = output
        .file_name()
        .map_or_else(OsString::new, OsString::from);
    temporary_name.push(".tmp");
    let temporary = output.with_file_name(temporary_name);
    let result = repository_status();
    let cleanup = || {
        remove_if_present(&output);
        remove_if_present(&temporary);
    };
    let Ok(status) = result else {
        cleanup();
        return;
    };
    let mut paths = status
        .untracked
        .into_iter()
        .map(|path| path.as_bytes().to_vec())
        .collect::<Vec<_>>();
    paths.sort();
    paths.dedup();
    let separator = if arguments.nul { 0 } else { b'\n' };
    let mut data = Vec::new();
    for path in paths {
        data.extend(path);
        data.push(separator);
    }
    if fs::write(&temporary, data).is_err() || fs::rename(&temporary, &output).is_err() {
        cleanup();
    }
}

fn remove_if_present(path: &Path) {
    let _ = fs::remove_file(path).or_else(|error| {
        if error.kind() == ErrorKind::NotFound {
            Ok(())
        } else {
            Err(error)
        }
    });
}

fn display_path(path: &[u8]) -> String {
    String::from_utf8_lossy(path).into_owned()
}

fn one_line(value: &str) -> String {
    value
        .replace(['\n', '\r', '\t'], " ")
        .chars()
        .take(256)
        .collect()
}

fn porcelain(status: &RepositoryStatus) -> String {
    let mut rows = BTreeMap::<Vec<u8>, [char; 2]>::new();
    for change in status.tree_to_index.entries() {
        rows.entry(change.path.as_bytes().to_vec())
            .or_insert([' ', ' '])[0] = status_code(change.kind);
    }
    for change in status.index_to_worktree.entries() {
        rows.entry(change.path.as_bytes().to_vec())
            .or_insert([' ', ' '])[1] = status_code(change.kind);
    }
    for entry in &status.unmerged {
        rows.insert(
            entry.path.as_bytes().to_vec(),
            conflict_code(entry.kind)
                .chars()
                .collect::<Vec<_>>()
                .try_into()
                .expect("two-byte conflict code"),
        );
    }
    for path in &status.untracked {
        rows.insert(path.as_bytes().to_vec(), ['?', '?']);
    }
    let mut output = String::new();
    for (path, code) in rows {
        let _ = writeln!(output, "{}{} {}", code[0], code[1], display_path(&path));
    }
    output
}

const fn status_code(kind: ChangeKind) -> char {
    match kind {
        ChangeKind::Added => 'A',
        ChangeKind::Deleted => 'D',
        ChangeKind::Modified | ChangeKind::SubmoduleModified => 'M',
        ChangeKind::TypeChanged => 'T',
        ChangeKind::Renamed => 'R',
        ChangeKind::Copied => 'C',
    }
}

const fn conflict_code(kind: larch_core::ConflictKind) -> &'static str {
    match kind {
        larch_core::ConflictKind::BothDeleted => "DD",
        larch_core::ConflictKind::AddedByUs => "AU",
        larch_core::ConflictKind::DeletedByThem => "UD",
        larch_core::ConflictKind::AddedByThem => "UA",
        larch_core::ConflictKind::DeletedByUs => "DU",
        larch_core::ConflictKind::BothAdded => "AA",
        larch_core::ConflictKind::BothModified => "UU",
    }
}

fn main() -> ExitCode {
    let metadata = larch_adapters::build_metadata();
    let matches = Cli::command().version(metadata.version()).get_matches();
    let cli = Cli::from_arg_matches(&matches)
        .expect("arguments already validated by the generated Clap command");
    match run(cli, metadata) {
        Ok(exit_code) => exit_code,
        Err(error) => {
            if !error.message.is_empty() {
                eprintln!("{}", error.message);
            }
            ExitCode::from(error.code)
        }
    }
}
