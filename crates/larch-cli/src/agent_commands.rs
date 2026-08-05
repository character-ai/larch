//! Vendor-agent commands composed over typed core and adapter boundaries.

use std::{
    env,
    ffi::OsString,
    path::{Path, PathBuf},
    process::ExitCode,
    thread,
    time::{Duration, Instant},
};

use clap::{Args, Subcommand};
use larch_adapters::{
    ExactDiffRequest, GitCli, GitCliError, GitCliPolicy, GitPath as GitCliPath, GitRef,
    GixRepository, PathIntent, PluginRoot, TemporaryRoot, TokioProcessRunner, atomic_write_bytes,
    read_optional_utf8_lossy, read_utf8,
    runtime::{Cancellation, LarchRuntime},
    vendor_diagnostics::{parse_codex_usage_file, write_collector_failure_log},
};
use larch_core::{
    Commit, RepositoryRead, ReviewerWaitConfig, ReviewerWaitHost, ReviewerWaitRow, Revision,
    WAIT_DEFAULT_POLL_INTERVAL_SECONDS, WAIT_DEFAULT_TIMEOUT_SECONDS, classify_diff, emit_kv,
    parse_generated_paths, wait_for_reviewers,
};

const WAIT_USAGE: &str =
    "Usage: wait-for-reviewers.sh [--timeout SECONDS] <sentinel.done> [sentinel2.done ...]";
const GATHER_USAGE: &str = "Usage: gather-branch-context.sh --output-dir <path>";
const COLLECTOR_USAGE: &str = "Usage: compose-collector-failure-log.sh --structured-record <record> --output <path> [--reviewer-file <path>]";
const POLL_INTERVAL_ENV: &str = "WAIT_FOR_REVIEWERS_POLL_INTERVAL";
const GENERATORS_TSV: &str = "scripts/generators.tsv";

#[derive(Subcommand)]
pub enum AgentCommand {
    /// Sum Codex token usage from a `--json` events stream.
    ParseCodexUsage(ParseCodexUsageArguments),
    /// Wait for reviewer completion sentinels with legacy-compatible diagnostics.
    #[command(disable_help_flag = true)]
    WaitReviewers(AgentRawArguments),
    /// Emit the routing mode for one review diff.
    #[command(disable_help_flag = true)]
    ClassifyDiff(AgentRawArguments),
    /// Write the diff, changed-file list, and commit summary for the current branch.
    #[command(disable_help_flag = true)]
    GatherBranchContext(AgentRawArguments),
    /// Atomically compose a redacted collector failure-log carrier.
    #[command(disable_help_flag = true)]
    ComposeCollectorFailureLog(AgentRawArguments),
}

#[derive(Args)]
pub struct ParseCodexUsageArguments {
    /// Codex events JSONL file written by the launcher.
    events_jsonl: PathBuf,
}

/// Raw legacy-compatible arguments handled by the command implementation.
#[derive(Args)]
#[command(trailing_var_arg = true)]
pub struct AgentRawArguments {
    #[arg(allow_hyphen_values = true)]
    arguments: Vec<OsString>,
}

/// Run one agent command and return its process exit status.
pub fn run(command: AgentCommand) -> ExitCode {
    match command {
        AgentCommand::ParseCodexUsage(arguments) => parse_codex_usage(&arguments),
        AgentCommand::WaitReviewers(arguments) => wait_reviewers(&arguments),
        AgentCommand::ClassifyDiff(arguments) => classify_diff_command(&arguments),
        AgentCommand::GatherBranchContext(arguments) => gather_branch_context(&arguments),
        AgentCommand::ComposeCollectorFailureLog(arguments) => {
            compose_collector_failure_log(&arguments)
        }
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

struct WaitArguments {
    timeout_seconds: u64,
    sentinels: Vec<PathBuf>,
}

enum WaitParse {
    Help,
    Error(String),
    Parsed(WaitArguments),
}

fn wait_reviewers(arguments: &AgentRawArguments) -> ExitCode {
    let parsed = match parse_wait_arguments(&arguments.arguments) {
        WaitParse::Help => {
            eprintln!("{WAIT_USAGE}");
            return ExitCode::SUCCESS;
        }
        WaitParse::Error(message) => {
            eprintln!("{message}");
            return ExitCode::from(1);
        }
        WaitParse::Parsed(value) => value,
    };
    let raw_poll = env::var(POLL_INTERVAL_ENV)
        .unwrap_or_else(|_| WAIT_DEFAULT_POLL_INTERVAL_SECONDS.to_string());
    let Some(poll_interval) = parse_poll_interval(&raw_poll) else {
        eprintln!("Error: {POLL_INTERVAL_ENV} must be a positive number, got '{raw_poll}'");
        return ExitCode::from(1);
    };
    let mut host = SystemWaitHost::new();
    let result = wait_for_reviewers(
        &mut host,
        &parsed.sentinels,
        ReviewerWaitConfig::new(parsed.timeout_seconds, poll_interval),
    );
    for row in result.rows() {
        match row {
            ReviewerWaitRow::Done {
                index,
                name,
                exit_code,
            } => println!("DONE {index} {name}: exit={exit_code}"),
            ReviewerWaitRow::Timeout { index, name } => println!("TIMEOUT {index} {name}"),
        }
    }
    ExitCode::SUCCESS
}

fn parse_wait_arguments(arguments: &[OsString]) -> WaitParse {
    let mut timeout = WAIT_DEFAULT_TIMEOUT_SECONDS.to_string();
    let mut sentinels = Vec::new();
    let mut index = 0_usize;
    while index < arguments.len() {
        let argument = arguments[index].to_string_lossy();
        if argument == "--timeout" {
            let Some(value) = arguments.get(index + 1) else {
                return WaitParse::Error("--timeout requires a value".to_owned());
            };
            timeout = value.to_string_lossy().into_owned();
            index += 2;
        } else if argument == "--help" {
            return WaitParse::Help;
        } else if argument.starts_with('-') {
            return WaitParse::Error(format!("Unknown option: {argument}\n{WAIT_USAGE}"));
        } else {
            sentinels.extend(arguments[index..].iter().map(PathBuf::from));
            break;
        }
    }
    let timeout_seconds = match parse_positive_integer(&timeout, "--timeout") {
        Ok(value) => value,
        Err(message) => return WaitParse::Error(message),
    };
    if sentinels.is_empty() {
        return WaitParse::Error(format!(
            "ERROR: at least one sentinel file path is required\n{WAIT_USAGE}"
        ));
    }
    WaitParse::Parsed(WaitArguments {
        timeout_seconds,
        sentinels,
    })
}

fn parse_positive_integer(raw: &str, flag: &str) -> Result<u64, String> {
    if raw.is_empty() || !raw.bytes().all(|byte| byte.is_ascii_digit()) {
        return Err(format!(
            "Error: {flag} value must be a positive integer, got '{raw}'"
        ));
    }
    let value = raw
        .parse::<u64>()
        .map_err(|_| format!("Error: {flag} value must be a positive integer, got '{raw}'"))?;
    if value == 0 {
        return Err(format!(
            "Error: {flag} value must be a positive integer, got '{raw}'"
        ));
    }
    Ok(value)
}

fn parse_poll_interval(raw: &str) -> Option<Duration> {
    if raw.is_empty() || raw == "." || raw.matches('.').count() > 1 {
        return None;
    }
    if !raw
        .bytes()
        .all(|byte| byte.is_ascii_digit() || byte == b'.')
    {
        return None;
    }
    if !raw.contains('.') && raw.parse::<u64>().ok()? < 1 {
        return None;
    }
    let seconds = raw.parse::<f64>().ok()?;
    (seconds.is_finite() && seconds > 0.0)
        .then(|| Duration::try_from_secs_f64(seconds).ok())
        .flatten()
}

struct SystemWaitHost {
    started: Instant,
}

impl SystemWaitHost {
    fn new() -> Self {
        Self {
            started: Instant::now(),
        }
    }
}

impl ReviewerWaitHost for SystemWaitHost {
    fn now(&mut self) -> Duration {
        self.started.elapsed()
    }

    fn sleep(&mut self, duration: Duration) {
        thread::sleep(duration);
    }

    fn read_sentinel(&mut self, path: &Path) -> Option<String> {
        read_optional_utf8_lossy(path).unwrap_or_else(|_| Some(String::new()))
    }

    fn diagnostic(&mut self, text: &str) {
        eprint!("{text}");
    }
}

fn classify_diff_command(arguments: &AgentRawArguments) -> ExitCode {
    if arguments.arguments.len() == 1 && arguments.arguments[0] == "--help" {
        eprintln!("Usage: classify-diff-mode.sh <diff-file>");
        return ExitCode::SUCCESS;
    }
    if arguments.arguments.len() != 1 {
        eprintln!("classify-diff-mode.sh: expected exactly one diff file path");
        return ExitCode::from(2);
    }
    let diff_file = PathBuf::from(&arguments.arguments[0]);
    if !diff_file.is_file() {
        eprintln!(
            "classify-diff-mode.sh: diff file not found: {}",
            diff_file.display()
        );
        return ExitCode::from(2);
    }
    let generated_paths = match generated_paths() {
        Ok(paths) => paths,
        Err(error) => {
            eprintln!("classify-diff-mode.sh: {error}");
            return ExitCode::from(1);
        }
    };
    let diff = match read_optional_utf8_lossy(&diff_file) {
        Ok(Some(diff)) => diff,
        Ok(None) => {
            eprintln!(
                "classify-diff-mode.sh: diff file not found: {}",
                diff_file.display()
            );
            return ExitCode::from(2);
        }
        Err(error) => {
            eprintln!("classify-diff-mode.sh: {error}");
            return ExitCode::from(1);
        }
    };
    emit_kv("DIFF_MODE", classify_diff(&diff, &generated_paths).as_str());
    ExitCode::SUCCESS
}

fn generated_paths() -> Result<std::collections::BTreeSet<String>, String> {
    let root = env::var_os(larch_core::env::CLAUDE_PLUGIN_ROOT)
        .map(PathBuf::from)
        .ok_or_else(|| {
            "CLAUDE_PLUGIN_ROOT is required to read scripts/generators.tsv".to_owned()
        })?;
    let root = PluginRoot::resolve(Some(&root))
        .map_err(|_| "scripts/generators.tsv is missing or unsafe".to_owned())?;
    let manifest = root
        .confine(GENERATORS_TSV, PathIntent::Read)
        .map_err(|_| "scripts/generators.tsv is missing or unsafe".to_owned())?;
    let text = read_utf8(&manifest)
        .map_err(|_| "scripts/generators.tsv is unreadable or malformed".to_owned())?;
    parse_generated_paths(&text).map_err(|error| error.to_string())
}

struct BranchContext {
    diff_file: PathBuf,
    file_list_file: PathBuf,
    commit_log_file: PathBuf,
    commit_count: usize,
}

fn gather_branch_context(arguments: &AgentRawArguments) -> ExitCode {
    let output_dir = match parse_output_dir(&arguments.arguments) {
        Ok(Some(path)) => path,
        Ok(None) => {
            eprintln!("{GATHER_USAGE}");
            return ExitCode::SUCCESS;
        }
        Err(error) => {
            eprintln!("{error}");
            return ExitCode::from(1);
        }
    };
    if !output_dir.is_dir() {
        eprintln!(
            "ERROR: output directory does not exist: {}",
            output_dir.display()
        );
        return ExitCode::from(1);
    }
    let context = match gather_context(&output_dir) {
        Ok(context) => context,
        Err(error) => {
            eprintln!("gather-branch-context.sh: {error}");
            return ExitCode::from(1);
        }
    };
    emit_kv("DIFF_FILE", &context.diff_file.display().to_string());
    emit_kv(
        "FILE_LIST_FILE",
        &context.file_list_file.display().to_string(),
    );
    emit_kv(
        "COMMIT_LOG_FILE",
        &context.commit_log_file.display().to_string(),
    );
    emit_kv("COMMIT_COUNT", &context.commit_count.to_string());
    ExitCode::SUCCESS
}

fn parse_output_dir(arguments: &[OsString]) -> Result<Option<PathBuf>, String> {
    let mut output_dir = None;
    let mut index = 0_usize;
    while index < arguments.len() {
        let argument = arguments[index].to_string_lossy();
        if argument == "--output-dir" {
            let Some(value) = arguments.get(index + 1) else {
                return Err("--output-dir requires a value".to_owned());
            };
            output_dir = Some(PathBuf::from(value));
            index += 2;
        } else if argument == "--help" {
            return Ok(None);
        } else {
            return Err(format!("Unknown option: {argument}\n{GATHER_USAGE}"));
        }
    }
    output_dir
        .ok_or_else(|| format!("ERROR: --output-dir is required\n{GATHER_USAGE}"))
        .map(Some)
}

fn gather_context(output_dir: &Path) -> Result<BranchContext, String> {
    let cwd = env::current_dir().map_err(|error| format!("cannot resolve cwd: {error}"))?;
    let repository =
        GixRepository::discover(&cwd).map_err(|_| "cannot open repository".to_owned())?;
    let head = repository
        .resolve_revision(&Revision::new("HEAD"))
        .map_err(|_| "cannot resolve HEAD".to_owned())?;
    let base = repository
        .resolve_revision(&Revision::new("origin/main"))
        .or_else(|_| repository.resolve_revision(&Revision::new("main")))
        .map_err(|_| "cannot resolve origin/main or main".to_owned())?;
    let merge_base = repository
        .merge_base(&head, &base)
        .map_err(|_| "git merge-base failed".to_owned())?;
    let merge_ref = GitRef::new(merge_base.to_hex()).map_err(|error| error.to_string())?;
    let head_ref = GitRef::new("HEAD").map_err(|error| error.to_string())?;
    let paths = review_paths()?;
    let output_absolute = if output_dir.is_absolute() {
        output_dir.to_path_buf()
    } else {
        cwd.join(output_dir)
    };
    let output_root = TemporaryRoot::resolve(Some(&output_absolute))
        .map_err(|_| "output directory is unsafe".to_owned())?;
    let runtime = LarchRuntime::new().map_err(|error| error.to_string())?;
    let runner = TokioProcessRunner::default();
    let policy = GitCliPolicy::new(cwd).map_err(|error| error.to_string())?;
    let git = GitCli::new(&runner, policy);
    let cancellation = Cancellation::new();
    let diff = runtime
        .block_on(git.exact_diff(
            ExactDiffRequest {
                cached: false,
                unified_context: Some(20),
                name_only: false,
                name_status: false,
                quiet: false,
                exit_code: false,
                base: Some(merge_ref.clone()),
                head: Some(head_ref.clone()),
                paths: paths.clone(),
            },
            &cancellation,
        ))
        .map_err(render_git_error)?;
    let file_list = runtime
        .block_on(git.exact_diff(
            ExactDiffRequest {
                cached: false,
                unified_context: None,
                name_only: true,
                name_status: false,
                quiet: false,
                exit_code: false,
                base: Some(merge_ref),
                head: Some(head_ref),
                paths,
            },
            &cancellation,
        ))
        .map_err(render_git_error)?;
    if diff.truncated() || file_list.truncated() {
        return Err("git diff output exceeded the reviewed capture limit".to_owned());
    }
    let commit_log = review_commit_log(&repository, &merge_base, &head)?;
    let diff_target = output_root
        .confine("diff.txt", PathIntent::Write)
        .map_err(|error| error.to_string())?;
    let file_list_target = output_root
        .confine("file-list.txt", PathIntent::Write)
        .map_err(|error| error.to_string())?;
    let commit_log_target = output_root
        .confine("commit-log.txt", PathIntent::Write)
        .map_err(|error| error.to_string())?;
    atomic_write_bytes(&diff_target, diff.output().stdout(), 0o600)
        .map_err(|error| error.to_string())?;
    atomic_write_bytes(&file_list_target, file_list.output().stdout(), 0o600)
        .map_err(|error| error.to_string())?;
    atomic_write_bytes(&commit_log_target, &commit_log, 0o600)
        .map_err(|error| error.to_string())?;
    Ok(BranchContext {
        diff_file: output_dir.join("diff.txt"),
        file_list_file: output_dir.join("file-list.txt"),
        commit_log_file: output_dir.join("commit-log.txt"),
        commit_count: String::from_utf8_lossy(&commit_log).lines().count(),
    })
}

fn review_paths() -> Result<Vec<GitCliPath>, String> {
    [".", ":(exclude)larch-logs/**"]
        .into_iter()
        .map(|path| GitCliPath::new(path).map_err(|error| error.to_string()))
        .collect()
}

fn review_commit_log(
    repository: &GixRepository,
    merge_base: &larch_core::ObjectId,
    head: &larch_core::ObjectId,
) -> Result<Vec<u8>, String> {
    let commits = repository
        .walk_commits_range(merge_base, head, usize::MAX)
        .map_err(|_| "cannot walk branch commits".to_owned())?;
    let mut output = Vec::new();
    for commit in commits {
        if !commit_touches_review_path(repository, &commit)? {
            continue;
        }
        output.extend_from_slice(commit.id.to_hex().as_bytes().get(..7).unwrap_or_default());
        output.push(b' ');
        output.extend_from_slice(String::from_utf8_lossy(&commit.subject).as_bytes());
        output.push(b'\n');
    }
    Ok(output)
}

fn commit_touches_review_path(repository: &GixRepository, commit: &Commit) -> Result<bool, String> {
    for parent in &commit.parents {
        let parent_commit = repository
            .walk_commits(parent, 1)
            .map_err(|_| "cannot inspect branch commit paths".to_owned())?
            .into_iter()
            .next()
            .ok_or_else(|| "cannot inspect branch commit paths".to_owned())?;
        let changes = repository
            .tree_changes(&parent_commit.tree, &commit.tree)
            .map_err(|_| "cannot inspect branch commit paths".to_owned())?;
        if changes.entries().iter().any(change_is_reviewable) {
            return Ok(true);
        }
    }
    Ok(false)
}

fn change_is_reviewable(change: &larch_core::Change) -> bool {
    !is_larch_log_path(change.path.as_bytes())
        || change
            .source_path
            .as_ref()
            .is_some_and(|path| !is_larch_log_path(path.as_bytes()))
}

fn is_larch_log_path(path: &[u8]) -> bool {
    path == b"larch-logs" || path.starts_with(b"larch-logs/")
}

fn render_git_error(error: GitCliError) -> String {
    match error {
        GitCliError::Failed(result) => {
            let stderr = result.safe_stderr();
            let stdout = result.safe_stdout();
            let detail = if stderr.as_str().trim().is_empty() {
                stdout.as_str().trim()
            } else {
                stderr.as_str().trim()
            };
            if detail.is_empty() {
                "git command failed".to_owned()
            } else {
                detail.to_owned()
            }
        }
        other => other.to_string(),
    }
}

struct CollectorArguments {
    reviewer_file: Option<PathBuf>,
    structured_record: String,
    output: PathBuf,
}

fn compose_collector_failure_log(arguments: &AgentRawArguments) -> ExitCode {
    if arguments.arguments.len() == 1 && arguments.arguments[0] == "--help" {
        eprintln!("{COLLECTOR_USAGE}");
        return ExitCode::SUCCESS;
    }
    let parsed = match parse_collector_arguments(&arguments.arguments) {
        Ok(arguments) => arguments,
        Err(error) => {
            eprintln!("{error}");
            return ExitCode::from(2);
        }
    };
    let cwd = match env::current_dir() {
        Ok(path) => path,
        Err(error) => {
            eprintln!("compose-collector-failure-log.sh: cannot resolve cwd: {error}");
            return ExitCode::from(1);
        }
    };
    let output = if parsed.output.is_absolute() {
        parsed.output.clone()
    } else {
        cwd.join(&parsed.output)
    };
    let Some(parent) = output.parent() else {
        eprintln!(
            "--output parent directory missing: {}",
            parsed.output.display()
        );
        return ExitCode::from(2);
    };
    if !parent.is_dir() {
        eprintln!("--output parent directory missing: {}", parent.display());
        return ExitCode::from(2);
    }
    let root = match TemporaryRoot::resolve(Some(parent)) {
        Ok(root) => root,
        Err(error) => {
            eprintln!("compose-collector-failure-log.sh: {error}");
            return ExitCode::from(1);
        }
    };
    let Some(output_name) = output.file_name() else {
        eprintln!("--output must name a file: {}", parsed.output.display());
        return ExitCode::from(2);
    };
    let output = match root.confine(output_name, PathIntent::Write) {
        Ok(output) => output,
        Err(error) => {
            eprintln!("compose-collector-failure-log.sh: {error}");
            return ExitCode::from(1);
        }
    };
    match write_collector_failure_log(
        parsed.reviewer_file.as_deref(),
        &parsed.structured_record,
        &output,
    ) {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("compose-collector-failure-log.sh: {error}");
            ExitCode::from(1)
        }
    }
}

fn parse_collector_arguments(arguments: &[OsString]) -> Result<CollectorArguments, String> {
    let mut reviewer_file = None;
    let mut structured_record = String::new();
    let mut output = None;
    let mut index = 0_usize;
    while index < arguments.len() {
        let argument = arguments[index].to_string_lossy();
        let Some(value) = arguments.get(index + 1) else {
            return Err(match argument.as_ref() {
                "--reviewer-file" => "--reviewer-file requires a value".to_owned(),
                "--structured-record" => "--structured-record requires a value".to_owned(),
                "--output" => "--output requires a value".to_owned(),
                _ => format!("compose-collector-failure-log.sh: unknown flag: {argument}"),
            });
        };
        match argument.as_ref() {
            "--reviewer-file" => reviewer_file = Some(PathBuf::from(value)),
            "--structured-record" => structured_record = value.to_string_lossy().into_owned(),
            "--output" => output = Some(PathBuf::from(value)),
            _ => {
                return Err(format!(
                    "compose-collector-failure-log.sh: unknown flag: {argument}"
                ));
            }
        }
        index += 2;
    }
    if structured_record.is_empty() {
        return Err("--structured-record is required and non-empty".to_owned());
    }
    let output = output
        .filter(|path| !path.as_os_str().is_empty())
        .ok_or_else(|| "--output is required".to_owned())?;
    Ok(CollectorArguments {
        reviewer_file: reviewer_file.filter(|path| !path.as_os_str().is_empty()),
        structured_record,
        output,
    })
}
