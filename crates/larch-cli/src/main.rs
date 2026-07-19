use std::{
    collections::{BTreeMap, BTreeSet},
    env,
    ffi::{OsStr, OsString},
    fmt::Write as _,
    fs,
    io::ErrorKind,
    io::Write as _,
    path::{Path, PathBuf},
    process::ExitCode,
    thread,
    time::Duration,
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
}

#[derive(Subcommand)]
enum GitCommand {
    /// Classify repository changes against an untracked-path baseline.
    CheckPhantomDirty(CheckPhantomDirtyArguments),
    /// Print the files and index stages that are currently conflicted.
    ConflictFiles,
    /// Report whether the worktree is clean using machine-readable key/value rows.
    CleanTree(CleanTreeArguments),
    /// Atomically write the sorted untracked-path baseline to an output file.
    SnapshotUntracked(SnapshotUntrackedArguments),
    /// Classify phantom paths and append advisory warnings to the run ledger.
    PhantomProbe(PhantomProbeArguments),
}

#[derive(Args)]
#[command(trailing_var_arg = true, disable_help_flag = true)]
struct CheckPhantomDirtyArguments {
    /// Raw compatibility arguments; parse errors are advisory command results.
    #[arg(allow_hyphen_values = true)]
    arguments: Vec<OsString>,
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

#[derive(Args)]
struct PhantomProbeArguments {
    /// Stable token identifying the checkpoint that invoked the probe.
    #[arg(long)]
    step: String,
    /// Override the session's untracked-path baseline.
    #[arg(long)]
    baseline_file: Option<PathBuf>,
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

fn run(cli: Cli, metadata: larch_core::BuildMetadata) -> Result<ExitCode, String> {
    match cli.domain {
        Domain::Bootstrap(BootstrapCommand::SelfCheck) => {
            println!("{}", larch_core::bootstrap_self_check(metadata));
            Ok(ExitCode::SUCCESS)
        }
        Domain::Example(ExampleCommand::Echo(arguments)) => {
            println!("{}", larch_core::example::echo(&arguments.message));
            Ok(ExitCode::SUCCESS)
        }
        Domain::Git(command) => run_git(command),
        Domain::Release(ReleaseCommand::PluginRuntime(arguments)) => {
            release_plugin_runtime::run(arguments.check).map(|()| ExitCode::SUCCESS)
        }
        Domain::Gh(GhCommand::WorkflowPath) => {
            print!("{}", larch_core::workflow_path());
            Ok(ExitCode::SUCCESS)
        }
        Domain::Gh(GhCommand::RunLogs(arguments)) => Ok(run_logs(&arguments)),
    }
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
        GitCommand::CheckPhantomDirty(arguments) => {
            check_phantom_dirty_command(&arguments);
            Ok(ExitCode::SUCCESS)
        }
        GitCommand::ConflictFiles => {
            conflict_files()?;
            Ok(ExitCode::SUCCESS)
        }
        GitCommand::CleanTree(arguments) => clean_tree(arguments),
        GitCommand::SnapshotUntracked(arguments) => {
            snapshot_untracked(arguments);
            Ok(ExitCode::SUCCESS)
        }
        GitCommand::PhantomProbe(arguments) => {
            phantom_probe(&arguments);
            Ok(ExitCode::SUCCESS)
        }
    }
}

#[derive(Debug, Eq, PartialEq)]
struct PhantomDirtyResult {
    status: &'static str,
    reason: Option<&'static str>,
    count: usize,
    paths_file: Option<PathBuf>,
}

impl PhantomDirtyResult {
    const fn status(status: &'static str) -> Self {
        Self {
            status,
            reason: None,
            count: 0,
            paths_file: None,
        }
    }

    const fn unknown(reason: &'static str) -> Self {
        Self {
            status: "unknown",
            reason: Some(reason),
            count: 0,
            paths_file: None,
        }
    }
}

fn check_phantom_dirty_command(arguments: &CheckPhantomDirtyArguments) {
    let parsed = parse_check_phantom_arguments(&arguments.arguments);
    let result = match parsed {
        Ok((baseline, step, paths_dir)) => check_phantom_dirty(&baseline, &step, &paths_dir),
        Err(reason) => PhantomDirtyResult::unknown(reason),
    };
    emit_phantom_dirty(&result, "");
}

fn parse_check_phantom_arguments(
    arguments: &[OsString],
) -> Result<(PathBuf, String, PathBuf), &'static str> {
    let mut baseline = None;
    let mut step = None;
    let mut paths_dir = None;
    let mut index = 0;
    while index < arguments.len() {
        let argument = arguments[index].as_os_str();
        let (target, missing_reason) = if argument == "--baseline" {
            (&mut baseline, "baseline-missing-value")
        } else if argument == "--step" {
            if index + 1 >= arguments.len() {
                return Err("step-missing-value");
            }
            step = arguments[index + 1].to_str().map(str::to_owned);
            if step.is_none() {
                return Err("bad-step");
            }
            index += 2;
            continue;
        } else if argument == "--phantom-paths-dir" {
            (&mut paths_dir, "phantom-paths-dir-missing-value")
        } else {
            return Err("unknown-flag");
        };
        if index + 1 >= arguments.len() {
            return Err(missing_reason);
        }
        *target = Some(PathBuf::from(&arguments[index + 1]));
        index += 2;
    }
    let baseline = baseline
        .filter(|value| !value.as_os_str().is_empty())
        .ok_or("baseline-required")?;
    let step = step
        .filter(|value| !value.is_empty())
        .ok_or("step-required")?;
    let paths_dir = paths_dir
        .filter(|value| !value.as_os_str().is_empty())
        .ok_or("phantom-paths-dir-required")?;
    Ok((baseline, step, paths_dir))
}

fn check_phantom_dirty(baseline: &Path, step: &str, paths_dir: &Path) -> PhantomDirtyResult {
    if !valid_step(step) {
        return PhantomDirtyResult::unknown("bad-step");
    }
    if !valid_meta_path(baseline.as_os_str()) {
        return PhantomDirtyResult::unknown("bad-baseline-path");
    }
    let Ok(status) = repository_status() else {
        return PhantomDirtyResult::unknown("git-status-failed");
    };
    let current_untracked = untracked_paths(&status);
    let baseline_paths = if baseline.is_file() {
        match fs::read(baseline) {
            Ok(data) => split_nul(&data),
            Err(_) => return PhantomDirtyResult::unknown("baseline-sort-failed"),
        }
    } else if current_untracked.is_empty() {
        BTreeSet::new()
    } else {
        return PhantomDirtyResult::unknown("baseline-missing-untracked-ambiguous");
    };
    let new_untracked = current_untracked
        .difference(&baseline_paths)
        .cloned()
        .collect::<Vec<_>>();
    if new_untracked.is_empty() {
        return if status.tree_to_index.entries().is_empty()
            && status.index_to_worktree.entries().is_empty()
            && status.unmerged.is_empty()
        {
            PhantomDirtyResult::status("clean")
        } else {
            PhantomDirtyResult::status("tracked-only")
        };
    }
    if fs::create_dir_all(paths_dir).is_err() {
        return PhantomDirtyResult::unknown("phantom-paths-dir-create-failed");
    }
    let paths_file = paths_dir.join(format!("phantom-paths-{step}.z"));
    let mut data = Vec::new();
    for path in &new_untracked {
        data.extend(path);
        data.push(0);
    }
    if fs::write(&paths_file, data).is_err() {
        return PhantomDirtyResult::unknown("phantom-paths-write-failed");
    }
    let count = match fs::read(&paths_file) {
        Ok(data) => data
            .iter()
            .fold(0, |count, byte| count + usize::from(*byte == 0)),
        Err(_) => return PhantomDirtyResult::unknown("phantom-count-failed"),
    };
    PhantomDirtyResult {
        status: "phantom",
        reason: None,
        count,
        paths_file: Some(paths_file),
    }
}

fn phantom_probe(arguments: &PhantomProbeArguments) {
    eprintln!("→ phantom-probe: {}", arguments.step);
    let Some(implement_tmpdir) = env::var_os("IMPLEMENT_TMPDIR").filter(|value| !value.is_empty())
    else {
        emit_phantom_dirty(
            &PhantomDirtyResult::unknown("IMPLEMENT_TMPDIR-unset"),
            "PHANTOM_",
        );
        return;
    };
    let implement_tmpdir = PathBuf::from(implement_tmpdir);
    let baseline = arguments
        .baseline_file
        .clone()
        .unwrap_or_else(|| implement_tmpdir.join("untracked-baseline.z"));
    let result = check_phantom_dirty(&baseline, &arguments.step, &implement_tmpdir);
    let append_error = append_phantom_warning(&implement_tmpdir, &arguments.step, &result);
    emit_phantom_dirty(&result, "PHANTOM_");
    if let Some(error) = append_error {
        println!("PHANTOM_APPEND_WARN_ERROR={}", fold_whitespace(&error));
    }
}

fn append_phantom_warning(
    implement_tmpdir: &Path,
    step: &str,
    result: &PhantomDirtyResult,
) -> Option<String> {
    let entry = match result.status {
        "phantom" => format!(
            "- **Step {step} — phantom untracked files:** {} file(s) appeared since session baseline (inspect {}/phantom-paths-{step}.z locally)",
            result.count,
            implement_tmpdir.display()
        ),
        "unknown" => format!(
            "- **Step {step} — phantom detection inconclusive:** STATUS=unknown REASON={}",
            result.reason.unwrap_or("unknown")
        ),
        _ => return None,
    };
    let log = implement_tmpdir.join("execution-issues.md");
    match write_execution_warning(&log, &entry) {
        Ok(()) => None,
        Err(error) => {
            let folded = fold_whitespace(&error);
            let fallback = format!("- **Step {step} — phantom warning append failed: {folded}**");
            let _ = write_execution_warning(&log, &fallback);
            Some(folded)
        }
    }
}

fn write_execution_warning(log: &Path, entry: &str) -> Result<(), String> {
    reject_symlink_path_or_ancestors(log)?;
    let parent = log
        .parent()
        .ok_or_else(|| String::from("log path has no parent"))?;
    fs::create_dir_all(parent).map_err(|error| python_io_error(&error, parent))?;
    reject_symlink_path_or_ancestors(log)?;
    let lock = log.with_file_name(format!(
        "{}.lock.d",
        log.file_name().unwrap_or_default().to_string_lossy()
    ));
    let mut acquired = false;
    for attempt in 0..100 {
        match fs::create_dir(&lock) {
            Ok(()) => {
                acquired = true;
                break;
            }
            Err(error) if error.kind() == ErrorKind::AlreadyExists && attempt < 99 => {
                thread::sleep(Duration::from_millis(50));
            }
            Err(error) if error.kind() == ErrorKind::AlreadyExists => {
                return Err(format!("could not acquire lock: {}", lock.display()));
            }
            Err(error) => return Err(python_io_error(&error, &lock)),
        }
    }
    if !acquired {
        return Err(format!("could not acquire lock: {}", lock.display()));
    }
    let result = (|| {
        let bytes = match fs::read(log) {
            Ok(bytes) => bytes,
            Err(error) if error.kind() == ErrorKind::NotFound => Vec::new(),
            Err(error) => return Err(python_io_error(&error, log)),
        };
        let text = String::from_utf8_lossy(&bytes).into_owned();
        let new_text = insert_warning_entry(&text, entry);
        reject_symlink_path_or_ancestors(log)?;
        let (temporary, mut file) = create_phantom_temp(log)?;
        let replace_result = (|| {
            file.write_all(new_text.as_bytes())
                .map_err(|error| python_io_error(&error, &temporary))?;
            drop(file);
            reject_symlink_path_or_ancestors(log)?;
            fs::rename(&temporary, log).map_err(|error| python_io_error(&error, log))
        })();
        if replace_result.is_err() {
            let _ = fs::remove_file(&temporary);
        }
        replace_result
    })();
    let _ = fs::remove_dir(&lock);
    result
}

fn create_phantom_temp(log: &Path) -> Result<(PathBuf, fs::File), String> {
    for nonce in 0..100 {
        let temporary = log.with_file_name(format!(".phantom-{}-{nonce}.tmp", std::process::id()));
        let mut options = fs::OpenOptions::new();
        options.write(true).create_new(true);
        #[cfg(unix)]
        {
            use std::os::unix::fs::OpenOptionsExt as _;
            options.mode(0o600);
        }
        match options.open(&temporary) {
            Ok(file) => return Ok((temporary, file)),
            Err(error) if error.kind() == ErrorKind::AlreadyExists => {}
            Err(error) => return Err(python_io_error(&error, &temporary)),
        }
    }
    Err(String::from("could not create warning-ledger temp file"))
}

fn insert_warning_entry(text: &str, entry: &str) -> String {
    const HEADER: &str = "### Warnings";
    if !text.lines().any(|line| line == HEADER) {
        let prefix = if text.is_empty() { "" } else { "\n" };
        return format!(
            "{}{prefix}{HEADER}\n\n{}\n",
            text.trim_end_matches('\n'),
            entry.trim_end_matches('\n')
        );
    }
    let lines = text.lines().collect::<Vec<_>>();
    let mut output = Vec::new();
    let mut inserted = false;
    let mut in_target = false;
    for line in lines {
        if line == HEADER {
            in_target = true;
            output.push(line);
            continue;
        }
        if in_target && line.starts_with("### ") {
            if !inserted {
                output.extend(["", entry.trim_end_matches('\n')]);
                inserted = true;
            }
            in_target = false;
        }
        output.push(line);
    }
    if in_target && !inserted {
        output.extend(["", entry.trim_end_matches('\n')]);
    }
    output.join("\n") + "\n"
}

fn emit_phantom_dirty(result: &PhantomDirtyResult, prefix: &str) {
    println!("{prefix}STATUS={}", result.status);
    if let Some(reason) = result.reason {
        println!("{prefix}REASON={reason}");
    }
    if result.status == "phantom" {
        println!("PHANTOM_COUNT={}", result.count);
        if let Some(paths_file) = &result.paths_file {
            println!("PHANTOM_PATHS_FILE={}", paths_file.display());
        }
    }
}

fn split_nul(data: &[u8]) -> BTreeSet<Vec<u8>> {
    data.split(|byte| *byte == 0)
        .filter(|path| !path.is_empty())
        .map(<[u8]>::to_vec)
        .collect()
}

fn untracked_paths(status: &RepositoryStatus) -> BTreeSet<Vec<u8>> {
    status
        .untracked
        .iter()
        .map(|path| path.as_bytes().to_vec())
        .collect()
}

fn fold_whitespace(value: &str) -> String {
    value.split_whitespace().collect::<Vec<_>>().join(" ")
}

fn python_io_error(error: &std::io::Error, path: &Path) -> String {
    let Some(code) = error.raw_os_error() else {
        return error.to_string();
    };
    let rendered = error.to_string();
    let detail = rendered.split(" (os error ").next().unwrap_or("I/O error");
    format!("[Errno {code}] {detail}: '{}'", path.display())
}

fn reject_symlink_path_or_ancestors(path: &Path) -> Result<(), String> {
    let mut current = Some(path);
    while let Some(candidate) = current {
        match fs::symlink_metadata(candidate) {
            Ok(metadata) if metadata.file_type().is_symlink() => {
                return Err(format!(
                    "refusing symlinked path or ancestor: {}",
                    candidate.display()
                ));
            }
            Ok(_) => {}
            Err(error) if error.kind() == ErrorKind::NotFound => {}
            Err(error) => return Err(python_io_error(&error, candidate)),
        }
        current = candidate.parent();
    }
    Ok(())
}

fn valid_step(step: &str) -> bool {
    !step.is_empty()
        && step
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'_' | b'.' | b'-'))
}

fn valid_meta_path(path: &OsStr) -> bool {
    let bytes = path.as_encoded_bytes();
    !bytes.is_empty()
        && bytes
            .iter()
            .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'.' | b'/' | b'_' | b'-'))
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
    let paths = untracked_paths(&status);
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
            if !error.is_empty() {
                eprintln!("{error}");
            }
            ExitCode::from(1)
        }
    }
}
