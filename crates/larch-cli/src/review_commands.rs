//! Rust command boundary for review context gathering.

use std::{
    collections::BTreeMap,
    env,
    ffi::OsString,
    fmt::Write as _,
    fs,
    path::{Component, Path, PathBuf},
    process::ExitCode,
    time::Duration,
};

use clap::Subcommand;
use larch_adapters::{GixRepository, atomic_write_utf8_in, ensure_directory_chain};
use larch_core::{
    GitPath, RepositoryRead, StatusOptions, emit_kv,
    review::{
        CollectedFinding, GATHER_CONTEXT_USAGE, GatherContextArguments, GatherContextMode,
        GatherContextParse, PanelManifestSlot, ReviewerFailureThresholdInput, ReviewerOutput,
        description_path_matches, description_tokens, has_no_findings_sentinel,
        parse_gather_context_arguments, parse_markdown_findings, render_collection,
        reviewer_failure_threshold, valid_relative_review_path,
    },
};
use serde_json::Value;

use crate::{
    agent_commands::{AgentRawArguments, capture_reviewer_wait, parse_poll_interval},
    argparse_compat::absolute_path,
    claude_commands::parse_uint,
    collector_commands::{
        CollectorOptions, Publication, StructuredValidation, SubstantiveValidation, collect,
        render_records, structured_reviewer_rows,
    },
};

const COLLECT_FINDINGS_USAGE: &str = "Usage: review collect-findings --mode diff|description --findings-file FILE --oos-file FILE [--external-output-files FILE...] [--claude-output-files FILE...] [--timeout SECONDS]";
const REVIEWER_THRESHOLD_USAGE: &str = "Usage: review check-reviewer-failure-threshold --collector-results-file FILE --panel hard|simple [--intended-slots N] [--launched-slots N] [--dropped-slots-file FILE] [--panel-manifest FILE] [--reviewer-output-files FILE...] [--round-num N]";

/// Review-domain commands now owned by Rust.
#[derive(Subcommand)]
pub enum ReviewCommand {
    /// Gather branch or description context for one review round.
    #[command(name = "gather-context", disable_help_flag = true)]
    #[allow(clippy::struct_field_names)]
    // raw compatibility arguments name the legacy boundary.
    GatherContext(AgentRawArguments),
    /// Materialize and dispatch the reviewer panel.
    #[command(name = "dispatch-panel", disable_help_flag = true)]
    DispatchPanel(AgentRawArguments),
    #[command(name = "collect-findings", disable_help_flag = true)]
    CollectFindings(AgentRawArguments),
    #[command(name = "check-reviewer-failure-threshold", disable_help_flag = true)]
    CheckReviewerFailureThreshold(AgentRawArguments),
    #[command(name = "aggregate-findings", disable_help_flag = true)]
    AggregateFindings(AgentRawArguments),
    #[command(name = "prune-nit-findings", disable_help_flag = true)]
    PruneNitFindings(AgentRawArguments),
    #[command(name = "reviewer-prune", disable_help_flag = true)]
    ReviewerPrune(AgentRawArguments),
    #[command(name = "tally-code-votes", disable_help_flag = true)]
    TallyCodeVotes(AgentRawArguments),
    #[command(name = "emit-tally", disable_help_flag = true)]
    EmitTally(AgentRawArguments),
    #[command(name = "log-phase", disable_help_flag = true)]
    LogPhase(AgentRawArguments),
    /// Orchestrate one complete code-review panel round.
    #[command(name = "core", disable_help_flag = true)]
    Core(AgentRawArguments),
    /// Compose review artifacts into the public findings JSONL.
    #[command(name = "compose-findings", disable_help_flag = true)]
    ComposeFindings(AgentRawArguments),
}

/// Dispatch one Rust-owned review command.
pub fn run(command: ReviewCommand) -> ExitCode {
    match command {
        ReviewCommand::GatherContext(arguments) => gather_context(&arguments.arguments),
        ReviewCommand::DispatchPanel(arguments) => {
            crate::review_dispatch_panel::run(&arguments.arguments)
        }
        ReviewCommand::CollectFindings(arguments) => collect_findings(&arguments.arguments),
        ReviewCommand::CheckReviewerFailureThreshold(arguments) => {
            check_reviewer_failure_threshold(&arguments.arguments)
        }
        ReviewCommand::AggregateFindings(arguments) => {
            crate::review_findings_commands::run_aggregate_findings(&arguments.arguments)
        }
        ReviewCommand::PruneNitFindings(arguments) => {
            crate::review_findings_commands::run_prune_nit_findings(&arguments.arguments)
        }
        ReviewCommand::ReviewerPrune(arguments) => {
            crate::review_findings_commands::run_reviewer_prune(&arguments.arguments)
        }
        ReviewCommand::TallyCodeVotes(arguments) => {
            crate::review_tally_commands::tally_code_votes(&arguments.arguments)
        }
        ReviewCommand::EmitTally(arguments) => {
            crate::review_tally_commands::emit_tally(&arguments.arguments)
        }
        ReviewCommand::LogPhase(arguments) => {
            crate::review_tally_commands::log_phase(&arguments.arguments)
        }
        ReviewCommand::Core(arguments) => crate::review_core_commands::core(&arguments.arguments),
        ReviewCommand::ComposeFindings(arguments) => {
            crate::review_compose_commands::compose_findings(&arguments.arguments)
        }
    }
}

fn gather_context(arguments: &[OsString]) -> ExitCode {
    let arguments = arguments
        .iter()
        .map(|argument| argument.to_string_lossy().into_owned())
        .collect::<Vec<_>>();
    match parse_gather_context_arguments(&arguments) {
        Ok(GatherContextParse::Help) => {
            eprintln!("{GATHER_CONTEXT_USAGE}");
            ExitCode::SUCCESS
        }
        Ok(GatherContextParse::Arguments(arguments)) => run_gather_context(&arguments),
        Err(error) => {
            eprint!("{}", error.prefix());
            if error.includes_usage() {
                eprintln!("{GATHER_CONTEXT_USAGE}");
            } else {
                eprintln!();
            }
            ExitCode::from(2)
        }
    }
}

fn run_gather_context(arguments: &GatherContextArguments) -> ExitCode {
    if let Err(error) = validate_output_arguments(arguments) {
        eprintln!("review gather-context: {error}");
        return ExitCode::from(1);
    }
    let output_dir = output_directory(&arguments.output_dir);
    let absolute_output = match absolute_path(&output_dir) {
        Ok(path) => path,
        Err(error) => {
            eprintln!("review gather-context: cannot resolve output directory: {error}");
            return ExitCode::from(1);
        }
    };
    if let Err(error) = ensure_directory_chain(&absolute_output) {
        eprintln!("review gather-context: cannot create output directory: {error}");
        return ExitCode::from(1);
    }
    match arguments.mode {
        GatherContextMode::Diff => gather_diff_context(&output_dir),
        GatherContextMode::Description => gather_description_context(arguments, &output_dir),
    }
}

fn validate_output_arguments(arguments: &GatherContextArguments) -> Result<(), String> {
    for (name, value) in [
        ("--output-dir", arguments.output_dir.as_str()),
        ("--scope-files", arguments.scope_files.as_str()),
    ] {
        if value.contains(['\n', '\r']) {
            return Err(format!(
                "{name} must not contain a newline or carriage return"
            ));
        }
    }
    Ok(())
}

fn output_directory(value: &str) -> PathBuf {
    if value.is_empty() {
        PathBuf::from(".")
    } else {
        PathBuf::from(value)
    }
}

fn gather_diff_context(output_dir: &Path) -> ExitCode {
    let result = crate::agent_commands::gather_branch_context_for_review(output_dir);
    let rows = result
        .as_ref()
        .map_or_else(|_| Vec::new(), crate::agent_commands::branch_context_rows);
    if let Err(error) = write_rows(output_dir, &rows) {
        eprintln!("review gather-context: cannot write branch context: {error}");
        return ExitCode::from(1);
    }
    let exit_code = match &result {
        Ok(_) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("gather-branch-context.sh: {error}");
            ExitCode::from(1)
        }
    };
    for (key, value) in rows {
        emit_kv(&key, &value);
    }
    emit_kv("SCOPE_FILES_COUNT", "0");
    emit_kv("MODE", "diff");
    exit_code
}

fn gather_description_context(arguments: &GatherContextArguments, output_dir: &Path) -> ExitCode {
    let file_list = if arguments.scope_files.is_empty() {
        output_dir.join("scope-files.txt")
    } else {
        PathBuf::from(&arguments.scope_files)
    };
    let matches = description_scope_matches(&arguments.description_text).unwrap_or_default();
    let mut content = String::new();
    for path in &matches {
        writeln!(&mut content, "{path}").expect("writing to String cannot fail");
    }
    if let Err(error) = write_scope_file(&file_list, &content) {
        eprintln!("review gather-context: cannot write scope files: {error}");
        return ExitCode::from(1);
    }
    emit_kv("DIFF_FILE", "");
    emit_kv("FILE_LIST_FILE", &file_list.display().to_string());
    emit_kv("COMMIT_LOG_FILE", "");
    emit_kv("COMMIT_COUNT", "0");
    emit_kv("SCOPE_FILES_COUNT", &matches.len().to_string());
    emit_kv("MODE", "description");
    ExitCode::SUCCESS
}

fn description_scope_matches(description: &str) -> Result<Vec<String>, String> {
    let cwd = env::current_dir().map_err(|error| error.to_string())?;
    let repository = GixRepository::discover(cwd.as_path()).map_err(|error| error.to_string())?;
    let repository_root = repository
        .location()
        .work_dir
        .map(|path| PathBuf::from(String::from_utf8_lossy(path.as_bytes()).into_owned()))
        .ok_or_else(|| "repository has no working directory".to_owned())?;
    let tracked = repository
        .tracked_paths()
        .map_err(|error| error.to_string())?;
    let mut tracked_paths = paths_from_current_directory(&repository_root, &cwd, tracked);
    tracked_paths.sort();
    tracked_paths.dedup();
    let mut content_paths = tracked_paths.clone();
    if let Ok(status) = repository.local_status(&StatusOptions::default()) {
        content_paths.extend(paths_from_current_directory(
            &repository_root,
            &cwd,
            status.untracked,
        ));
    }
    content_paths.sort();
    content_paths.dedup();
    let tokens = description_tokens(description);
    let eligible = |path: &str| eligible_review_file(&cwd, path);
    let mut matches =
        description_path_matches(&tokens, tracked_paths.iter().map(String::as_str), eligible);
    // Preserve the legacy availability gate without adding an untyped `rg`
    // process path beside the in-process repository owner.
    if matches.is_empty() && !description.is_empty() && ripgrep_available() {
        let lowercase_description = description.to_lowercase();
        for path in &content_paths {
            if !eligible_review_file(&cwd, path) {
                continue;
            }
            let Ok(contents) = fs::read(cwd.join(path)) else {
                continue;
            };
            let text = String::from_utf8_lossy(&contents);
            if text.to_lowercase().contains(&lowercase_description) {
                matches.insert(path.clone());
            }
        }
    }
    Ok(matches.into_iter().collect())
}

fn ripgrep_available() -> bool {
    let executable = if cfg!(windows) { "rg.exe" } else { "rg" };
    env::var_os("PATH").is_some_and(|path| {
        env::split_paths(&path).any(|directory| {
            let candidate = directory.join(executable);
            candidate.is_file() && executable_file(&candidate)
        })
    })
}

#[cfg(unix)]
fn executable_file(path: &Path) -> bool {
    use std::os::unix::fs::PermissionsExt as _;

    fs::metadata(path).is_ok_and(|metadata| metadata.permissions().mode() & 0o111 != 0)
}

#[cfg(not(unix))]
fn executable_file(_path: &Path) -> bool {
    true
}

fn paths_from_current_directory(
    repository_root: &Path,
    cwd: &Path,
    paths: impl IntoIterator<Item = GitPath>,
) -> Vec<String> {
    paths
        .into_iter()
        .filter_map(|path| {
            let path = PathBuf::from(String::from_utf8_lossy(path.as_bytes()).into_owned());
            repository_root
                .join(path)
                .strip_prefix(cwd)
                .ok()
                .and_then(git_wire_path)
        })
        .collect()
}

fn git_wire_path(path: &Path) -> Option<String> {
    let mut parts = Vec::new();
    for component in path.components() {
        match component {
            Component::Normal(part) => parts.push(part.to_str()?.to_owned()),
            Component::CurDir => {}
            Component::ParentDir | Component::RootDir | Component::Prefix(_) => return None,
        }
    }
    (!parts.is_empty()).then(|| parts.join("/"))
}

fn eligible_review_file(cwd: &Path, path: &str) -> bool {
    if !valid_relative_review_path(path) {
        return false;
    }
    fs::symlink_metadata(cwd.join(path))
        .is_ok_and(|metadata| metadata.file_type().is_file() && !metadata.file_type().is_symlink())
}

fn write_scope_file(path: &Path, content: &str) -> Result<(), String> {
    let absolute = absolute_path(path).map_err(|error| error.to_string())?;
    let (root, target) = crate::launcher_support::confined_target(&absolute)
        .ok_or_else(|| "scope-files path is not a confinable file".to_owned())?;
    atomic_write_utf8_in(&root, &target, content, true, 0o600).map_err(|error| error.to_string())
}

fn write_rows(output_dir: &Path, rows: &[(String, String)]) -> Result<(), String> {
    if rows
        .iter()
        .any(|(key, value)| key.contains(['\n', '\r']) || value.contains(['\n', '\r']))
    {
        return Err("branch context contains a newline or carriage return".to_owned());
    }
    let absolute_output = absolute_path(output_dir).map_err(|error| error.to_string())?;
    let path = absolute_output.join("gather-branch-context.env");
    let (root, target) = crate::launcher_support::confined_target(&path)
        .ok_or_else(|| "branch-context path is not confinable".to_owned())?;
    let mut content = String::new();
    for (key, value) in rows {
        writeln!(&mut content, "{key}={value}").expect("writing to String cannot fail");
    }
    atomic_write_utf8_in(&root, &target, &content, true, 0o600).map_err(|error| error.to_string())
}

enum LegacyReviewArguments {
    Help,
    Values(ReviewArgumentValues),
}

#[derive(Default)]
struct ReviewArgumentValues {
    values: BTreeMap<String, String>,
    lists: BTreeMap<String, Vec<String>>,
}

impl ReviewArgumentValues {
    fn value(&self, name: &str, default: &str) -> String {
        self.values
            .get(name)
            .cloned()
            .unwrap_or_else(|| default.to_owned())
    }

    fn list(&self, name: &str) -> Vec<String> {
        self.lists.get(name).cloned().unwrap_or_default()
    }
}

fn parse_legacy_review_arguments(
    arguments: &[String],
    usage: &str,
    options: &[&str],
    list_options: &[&str],
) -> Result<LegacyReviewArguments, String> {
    if arguments.iter().any(|argument| argument == "--help") {
        return Ok(LegacyReviewArguments::Help);
    }
    let mut parsed = ReviewArgumentValues::default();
    let mut index = 0_usize;
    while index < arguments.len() {
        let option = &arguments[index];
        if list_options.contains(&option.as_str()) {
            index += 1;
            let mut values = Vec::new();
            while let Some(value) = arguments.get(index) {
                if value.starts_with("--") {
                    break;
                }
                values.push(value.clone());
                index += 1;
            }
            parsed.lists.insert(option.clone(), values);
            continue;
        }
        if !options.contains(&option.as_str()) {
            return Err(format!("unknown option: {option}\n{usage}"));
        }
        let Some(value) = arguments.get(index + 1) else {
            return Err(format!("{option} requires a value\n{usage}"));
        };
        parsed.values.insert(option.clone(), value.clone());
        index += 2;
    }
    Ok(LegacyReviewArguments::Values(parsed))
}

fn raw_arguments(arguments: &[OsString]) -> Vec<String> {
    arguments
        .iter()
        .map(|argument| argument.to_string_lossy().into_owned())
        .collect()
}

#[allow(clippy::too_many_lines)] // Ordered collector artifacts and failure logs share one compatibility transaction.
fn collect_findings(arguments: &[OsString]) -> ExitCode {
    let arguments = raw_arguments(arguments);
    let parsed = match parse_legacy_review_arguments(
        &arguments,
        COLLECT_FINDINGS_USAGE,
        [
            "--mode",
            "--timeout",
            "--session-env-path",
            "--findings-file",
            "--oos-file",
        ]
        .as_slice(),
        ["--external-output-files", "--claude-output-files"].as_slice(),
    ) {
        Ok(LegacyReviewArguments::Help) => {
            eprintln!("{COLLECT_FINDINGS_USAGE}");
            return ExitCode::SUCCESS;
        }
        Ok(LegacyReviewArguments::Values(parsed)) => parsed,
        Err(message) => {
            eprintln!("{message}");
            return ExitCode::from(2);
        }
    };
    let mode = parsed.value("--mode", "");
    if !matches!(mode.as_str(), "diff" | "description") {
        eprintln!("review collect-findings: --mode must be diff or description");
        return ExitCode::from(2);
    }
    let findings_file = PathBuf::from(parsed.value("--findings-file", ""));
    let oos_file = PathBuf::from(parsed.value("--oos-file", ""));
    let timeout = parsed.value("--timeout", "1860");
    let external_files = parsed
        .list("--external-output-files")
        .into_iter()
        .map(PathBuf::from)
        .collect::<Vec<_>>();
    let claude_files = parsed
        .list("--claude-output-files")
        .into_iter()
        .map(PathBuf::from)
        .collect::<Vec<_>>();
    let review_tmpdir = env::var_os("REVIEW_TMPDIR")
        .filter(|value| !value.is_empty())
        .map_or_else(
            || {
                findings_file
                    .parent()
                    .map_or_else(|| PathBuf::from("."), Path::to_path_buf)
            },
            PathBuf::from,
        );
    if let Err(error) = ensure_review_parent(&findings_file)
        .and_then(|()| ensure_review_parent(&oos_file))
        .and_then(|()| ensure_review_directory(&review_tmpdir))
    {
        eprintln!("review collect-findings: cannot prepare output paths: {error}");
        return ExitCode::from(1);
    }
    let collector_results = review_tmpdir.join("collector-results.env");
    let mut collector_text = String::new();
    if !external_files.is_empty() {
        let Some(timeout_seconds) = parse_uint(&timeout).filter(|seconds| *seconds > 0) else {
            eprintln!("Error: --timeout value must be a positive integer, got '{timeout}'");
            return ExitCode::from(1);
        };
        let options = CollectorOptions {
            timeout: timeout_seconds,
            output_files: external_files
                .iter()
                .map(|path| path.display().to_string())
                .collect(),
            substantive: SubstantiveValidation::ShortReviewer,
            structured: StructuredValidation::Off,
            publication: Publication::Full,
        };
        let outcome = collect(&options);
        collector_text = render_records(&outcome.records, Publication::Full);
        for diagnostic in outcome.diagnostics {
            eprintln!("{diagnostic}");
        }
    }
    if let Err(error) = write_review_file(&collector_results, &collector_text) {
        eprintln!("review collect-findings: cannot write collector results: {error}");
        return ExitCode::from(1);
    }
    if !claude_files.is_empty() {
        let Some(timeout_seconds) = parse_uint(&timeout).filter(|seconds| *seconds > 0) else {
            let text =
                format!("Error: --timeout value must be a positive integer, got '{timeout}'\n");
            let _ignored =
                write_review_file(&review_tmpdir.join("wait-for-claude-reviewers.log"), &text);
            return ExitCode::from(1);
        };
        let poll_interval = match reviewer_poll_interval() {
            Ok(interval) => interval,
            Err(message) => {
                let _ignored = write_review_file(
                    &review_tmpdir.join("wait-for-claude-reviewers.log"),
                    &format!("{message}\n"),
                );
                return ExitCode::from(1);
            }
        };
        let sentinels = claude_files
            .iter()
            .map(|path| PathBuf::from(format!("{}.done", path.display())))
            .collect::<Vec<_>>();
        let (wait_log_content, timed_out) =
            capture_reviewer_wait(&sentinels, timeout_seconds, poll_interval);
        let wait_log = review_tmpdir.join("wait-for-claude-reviewers.log");
        if let Err(error) = write_review_file(&wait_log, &wait_log_content) {
            eprintln!("review collect-findings: cannot write reviewer wait log: {error}");
            return ExitCode::from(1);
        }
        if timed_out {
            return ExitCode::from(1);
        }
    }
    let dirty_detected = [external_files.as_slice(), claude_files.as_slice()]
        .into_iter()
        .flatten()
        .any(|path| dirty_tree_sidecar(path));
    let mut rows = Vec::new();
    for path in &external_files {
        if !collector_ok(&collector_text, path) {
            continue;
        }
        let label = output_label(path);
        let structured = structured_reviewer_rows(path, &review_tmpdir)
            .into_iter()
            .map(|row| structured_finding(&row, &label))
            .collect::<Vec<_>>();
        if structured.is_empty() {
            rows.extend(parse_markdown_findings(&read_file_lossy(path), &label));
        } else {
            rows.extend(structured);
        }
    }
    for path in &claude_files {
        let label = output_label(path);
        let mut reviewer_rows = parse_markdown_findings(&read_file_lossy(path), &label);
        if reviewer_rows.is_empty() {
            reviewer_rows = structured_reviewer_rows(path, &review_tmpdir)
                .into_iter()
                .map(|row| structured_finding(&row, &label))
                .collect();
        }
        let output = read_file_lossy(path);
        if !reviewer_rows.is_empty() || has_no_findings_sentinel(&output) {
            let _ignored = write!(
                collector_text,
                "REVIEWER_FILE={}\nTOOL=claude\nSTATUS=OK\nEXIT_CODE=0\n\n",
                path.display()
            );
        } else if is_non_empty_regular_file(path) {
            let _ignored = write!(
                collector_text,
                "REVIEWER_FILE={}\nTOOL=claude\nSTATUS=NOT_SUBSTANTIVE\nEXIT_CODE=0\n\n",
                path.display()
            );
            eprintln!(
                "**⚠ Reviewer {}: non-substantive output produced no prose or TSV findings**",
                output_label(path)
            );
        }
        rows.extend(reviewer_rows);
    }
    if let Err(error) = write_review_file(&collector_results, &collector_text) {
        eprintln!("review collect-findings: cannot write collector results: {error}");
        return ExitCode::from(1);
    }
    let rendered = render_collection(rows);
    if let Err(error) = write_review_file(&findings_file, &rendered.findings)
        .and_then(|()| write_review_file(&oos_file, &rendered.oos))
    {
        eprintln!("review collect-findings: cannot write finding artifacts: {error}");
        return ExitCode::from(1);
    }
    emit_kv("FINDINGS_COUNT", &rendered.findings_count.to_string());
    emit_kv("OOS_COUNT", &rendered.oos_count.to_string());
    emit_kv(
        "DIRTY_DETECTED",
        if dirty_detected { "true" } else { "false" },
    );
    emit_kv("COLLECT_OK", "true");
    emit_kv(
        "COLLECTOR_OUTPUT_FILE",
        &collector_results.display().to_string(),
    );
    ExitCode::SUCCESS
}

fn ensure_review_directory(path: &Path) -> Result<(), String> {
    let absolute = absolute_path(path).map_err(|error| error.to_string())?;
    ensure_directory_chain(&absolute).map_err(|error| error.to_string())
}

fn ensure_review_parent(path: &Path) -> Result<(), String> {
    ensure_review_directory(path.parent().unwrap_or_else(|| Path::new(".")))
}

fn write_review_file(path: &Path, content: &str) -> Result<(), String> {
    let absolute = absolute_path(path).map_err(|error| error.to_string())?;
    let (root, target) = crate::launcher_support::confined_target(&absolute)
        .ok_or_else(|| "review output path is not a confinable file".to_owned())?;
    atomic_write_utf8_in(&root, &target, content, true, 0o600).map_err(|error| error.to_string())
}

fn output_label(path: &Path) -> String {
    path.file_name()
        .map_or_else(String::new, |name| name.to_string_lossy().into_owned())
}

fn read_file_lossy(path: &Path) -> String {
    fs::read(path)
        .map(|bytes| String::from_utf8_lossy(&bytes).into_owned())
        .unwrap_or_default()
}

fn is_non_empty_regular_file(path: &Path) -> bool {
    fs::metadata(path).is_ok_and(|metadata| metadata.is_file() && metadata.len() > 0)
}

fn collector_ok(collector_text: &str, reviewer_file: &Path) -> bool {
    larch_core::review::parse_threshold_collector_records(collector_text)
        .into_iter()
        .any(|record| {
            record.reviewer_file == reviewer_file.display().to_string()
                && matches!(record.status.as_str(), "OK" | "cap_hit")
        })
}

fn structured_finding(
    row: &crate::collector_commands::StructuredReviewerRow,
    label: &str,
) -> CollectedFinding {
    let prefix = if row.scope == "out_of_scope" {
        "[OUT_OF_SCOPE] "
    } else {
        ""
    };
    CollectedFinding {
        title: format!("{prefix}{}: {}", row.focus_area, row.location),
        label: label.to_owned(),
        body: format!(
            "[{}] {} {} {}",
            row.severity, row.what, row.scenario, row.suggested_fix
        ),
    }
}

fn dirty_tree_sidecar(path: &Path) -> bool {
    let sidecar = PathBuf::from(format!("{}.dirty-tree", path.display()));
    fs::read_to_string(sidecar)
        .ok()
        .and_then(|text| {
            text.lines()
                .find_map(|line| line.strip_prefix("STATUS=").map(str::to_owned))
        })
        .is_some_and(|status| status == "dirty")
}

fn reviewer_poll_interval() -> Result<Duration, String> {
    let raw = env::var("WAIT_FOR_REVIEWERS_POLL_INTERVAL").unwrap_or_else(|_| "1".to_owned());
    parse_poll_interval(&raw).ok_or_else(|| {
        format!("Error: WAIT_FOR_REVIEWERS_POLL_INTERVAL must be a positive number, got '{raw}'")
    })
}

#[allow(clippy::too_many_lines)] // Frozen option parsing and stdout form one compatibility boundary.
fn check_reviewer_failure_threshold(arguments: &[OsString]) -> ExitCode {
    let arguments = raw_arguments(arguments);
    let parsed = match parse_legacy_review_arguments(
        &arguments,
        REVIEWER_THRESHOLD_USAGE,
        [
            "--collector-results-file",
            "--panel",
            "--intended-slots",
            "--launched-slots",
            "--dropped-slots-file",
            "--panel-manifest",
            "--round-num",
        ]
        .as_slice(),
        ["--reviewer-output-files"].as_slice(),
    ) {
        Ok(LegacyReviewArguments::Help) => {
            eprintln!("{REVIEWER_THRESHOLD_USAGE}");
            return ExitCode::SUCCESS;
        }
        Ok(LegacyReviewArguments::Values(parsed)) => parsed,
        Err(message) => {
            eprintln!("{message}");
            return ExitCode::from(2);
        }
    };
    let panel = parsed.value("--panel", "");
    if !matches!(panel.as_str(), "hard" | "simple") {
        eprintln!("review check-reviewer-failure-threshold: --panel must be hard or simple");
        return ExitCode::from(2);
    }
    let intended_raw = parsed.value("--intended-slots", "3");
    let round_raw = parsed.value("--round-num", "1");
    let Some(intended_slots) = nonnegative_usize(&intended_raw) else {
        eprintln!("review check-reviewer-failure-threshold: slot counts must be integers");
        return ExitCode::from(2);
    };
    if nonnegative_usize(&round_raw)
        .filter(|round| *round > 0)
        .is_none()
    {
        eprintln!("review check-reviewer-failure-threshold: slot counts must be integers");
        return ExitCode::from(2);
    }
    let launched_slots = match parsed
        .values
        .get("--launched-slots")
        .filter(|value| !value.is_empty())
    {
        Some(value) => {
            if let Some(value) = nonnegative_usize(value) {
                Some(value)
            } else {
                eprintln!(
                    "review check-reviewer-failure-threshold: --launched-slots must be a non-negative integer"
                );
                return ExitCode::from(2);
            }
        }
        None => None,
    };
    let collector_file = PathBuf::from(parsed.value("--collector-results-file", ""));
    let collector_results = read_file_lossy(&collector_file);
    let dropped_slots = match parsed
        .values
        .get("--dropped-slots-file")
        .filter(|value| !value.is_empty())
    {
        Some(value) => {
            let path = PathBuf::from(value);
            if !path.is_file() {
                eprintln!(
                    "review check-reviewer-failure-threshold: --dropped-slots-file must name a file"
                );
                return ExitCode::from(2);
            }
            Some(read_file_lossy(&path))
        }
        None => None,
    };
    let panel_manifest = match parsed
        .values
        .get("--panel-manifest")
        .filter(|value| !value.is_empty())
    {
        Some(value) => {
            let path = PathBuf::from(value);
            let text = if path.is_symlink() || !path.is_file() {
                Err(())
            } else {
                fs::read(&path)
                    .map(|bytes| String::from_utf8_lossy(&bytes).into_owned())
                    .map_err(|_| ())
            };
            if let Ok(slots) = text.and_then(|text| panel_manifest_slots(&text)) {
                slots
            } else {
                eprintln!(
                    "review check-reviewer-failure-threshold: --panel-manifest is unreadable or contains invalid JSON"
                );
                return ExitCode::from(1);
            }
        }
        None => Vec::new(),
    };
    let reviewer_outputs = parsed
        .list("--reviewer-output-files")
        .into_iter()
        .map(|path| {
            let path = PathBuf::from(path);
            ReviewerOutput {
                path: path.display().to_string(),
                content: is_non_empty_regular_file(&path).then(|| read_file_lossy(&path)),
            }
        })
        .collect();
    let result = reviewer_failure_threshold(&ReviewerFailureThresholdInput {
        collector_results,
        reviewer_outputs,
        dropped_slots,
        panel_manifest,
        intended_slots,
        launched_slots,
    });
    emit_kv("INTENDED_SLOTS", &result.intended_slots.to_string());
    emit_kv("SUCCEEDED_SLOTS", &result.succeeded_slots.to_string());
    emit_kv("FAILED_SLOTS", &result.failed_slots.to_string());
    emit_kv("COUNTED_SLOTS", &result.counted_slots.to_string());
    emit_kv(
        "NOT_SUBSTANTIVE_SLOTS",
        &result.not_substantive_slots.to_string(),
    );
    emit_kv("DROPPED_SLOTS", &result.dropped_slots.to_string());
    emit_kv(
        "DROPPED_STATIC_SLOTS",
        &result.dropped_static_slots.to_string(),
    );
    emit_kv(
        "DYNAMIC_FAILED_SLOTS",
        &result.dynamic_failed_slots.to_string(),
    );
    emit_kv(
        "DYNAMIC_DROPPED_SLOTS",
        &result.dynamic_dropped_slots.to_string(),
    );
    emit_kv(
        "THRESHOLD_OK",
        if result.threshold_ok { "true" } else { "false" },
    );
    emit_kv("THRESHOLD_REASON", &result.threshold_reason);
    ExitCode::SUCCESS
}

fn nonnegative_usize(value: &str) -> Option<usize> {
    (!value.is_empty() && value.bytes().all(|byte| byte.is_ascii_digit()))
        .then(|| value.parse::<usize>().ok())
        .flatten()
}

fn panel_manifest_slots(text: &str) -> Result<Vec<PanelManifestSlot>, ()> {
    text.lines()
        .filter(|line| !line.trim().is_empty())
        .map(|value| {
            let value = serde_json::from_str::<Value>(value).map_err(|_| ())?;
            let Some(object) = value.as_object() else {
                return Ok(None);
            };
            let (Some(slot), Some(tool), Some(output)) = (
                object.get("slot").and_then(Value::as_str),
                object.get("tool").and_then(Value::as_str),
                object.get("output").and_then(Value::as_str),
            ) else {
                return Ok(None);
            };
            Ok(
                (!slot.is_empty() && !tool.is_empty() && !output.is_empty()).then(|| {
                    PanelManifestSlot {
                        slot: slot.to_owned(),
                        tool: tool.to_owned(),
                        output: output.to_owned(),
                    }
                }),
            )
        })
        .collect::<Result<Vec<_>, _>>()
        .map(|slots| slots.into_iter().flatten().collect())
}
