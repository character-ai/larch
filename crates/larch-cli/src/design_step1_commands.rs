//! Rust owner for the five `/design` step1 and step-log verbs (#8579).
//!
//! Owns `design driver`, `design step1d5`, `design step1d7`, `design
//! step1e-reentry`, and `plan step1-log`.
//!
//! The immediately-preceding sibling `design_step0_commands.rs` (#8578) already
//! ports the wrapper library these verbs need; this owner reuses its
//! `parse_wrapper_args`/`WrapperNs`, `load_wrapper_env`, `require_plugin_root`,
//! `require_design_tmpdir`, `check_pause_and_exit`, `derive_binary_found`,
//! `Env`/`env_get`/`utf8_arguments`/`entrypoint`/`exit_from_i32`, and the
//! `Step0Runner` child-seam pattern rather than duplicating them.

use std::{
    ffi::OsString,
    fs,
    io::Read,
    path::{Path, PathBuf},
    process::{Command, ExitCode, Stdio},
};

use larch_adapters::GixRepository;
use larch_core::RepositoryRead as _;
use larch_core::review::python_truthy_of_json;
use serde_json::Value;

use crate::design_step0_commands::{
    Env, LiveStep0Runner, Step0Runner, check_pause_and_exit, derive_binary_found, entrypoint,
    env_get, exit_from_i32, load_wrapper_env, parse_wrapper_args, require_design_tmpdir,
    require_plugin_root, utf8_arguments,
};

/// Resolved wrapper preamble shared by the design Step 1 entry points.
struct WrapperContext {
    env: Env,
    plugin_root: PathBuf,
    design_tmpdir: PathBuf,
    public_argv: Vec<String>,
}

/// Parse the wrapper argv, resolve the plugin root, optionally derive the
/// binary-found flag, then require the design tmpdir. One owner for the
/// parse-and-resolve preamble the Step 1 entry points otherwise repeat.
fn wrapper_context(
    arguments: &[OsString],
    derive_binary: bool,
) -> Result<WrapperContext, ExitCode> {
    let argv = utf8_arguments(arguments);
    let ns = parse_wrapper_args(&argv)?;
    let mut env = load_wrapper_env(&ns);
    let plugin_root_value = env_get(&env, "CLAUDE_PLUGIN_ROOT", &ns.plugin_root).to_owned();
    let plugin_root = require_plugin_root(&plugin_root_value)?;
    if derive_binary {
        derive_binary_found(&mut env);
    }
    let design_tmpdir = require_design_tmpdir(&env, None)?;
    Ok(WrapperContext {
        env,
        plugin_root,
        design_tmpdir,
        public_argv: ns.public_argv,
    })
}

/// Create the `.completed` directory under the design tmpdir and touch each
/// named checkpoint sentinel, swallowing best-effort I/O failures.
fn mark_completed(design_tmpdir: &Path, names: &[&str]) {
    let completed = design_tmpdir.join(".completed");
    let _ = fs::create_dir_all(&completed);
    for name in names {
        let _ = fs::write(completed.join(name), "");
    }
}

// ---------------------------------------------------------------------------
// Pure helpers ported branch-for-branch from design_core.py
// ---------------------------------------------------------------------------

/// Port of `_normalize_step`: lowercase, then map every character outside the
/// `[alnum._-]` set to `-`.
fn normalize_step(value: &str) -> String {
    value
        .to_lowercase()
        .chars()
        .map(|ch| {
            if ch.is_alphanumeric() || matches!(ch, '.' | '_' | '-') {
                ch
            } else {
                '-'
            }
        })
        .collect()
}

/// Port of `_extract_args`: the substring after the first ` ARGS=` marker.
fn extract_args(line: &str) -> String {
    line.split_once(" ARGS=")
        .map_or_else(String::new, |(_, rest)| rest.to_owned())
}

/// Port of `str.splitlines()` for the boundaries these verbs encounter
/// (`\n`, `\r\n`, `\r`). A trailing line terminator does not yield an empty
/// final element, matching Python's `str.splitlines`.
fn splitlines(text: &str) -> Vec<String> {
    let mut out = Vec::new();
    let mut current = String::new();
    let mut chars = text.chars().peekable();
    while let Some(character) = chars.next() {
        match character {
            '\n' => out.push(std::mem::take(&mut current)),
            '\r' => {
                if chars.peek() == Some(&'\n') {
                    let _ = chars.next();
                }
                out.push(std::mem::take(&mut current));
            }
            _ => current.push(character),
        }
    }
    if !current.is_empty() {
        out.push(current);
    }
    out
}

/// Minimal POSIX `shlex.split`. Returns `Err(())` for an unterminated quote or
/// a trailing escape, the two conditions where `shlex.split` raises
/// `ValueError` (the driver's `REASON=bad-args` path).
fn shlex_split(input: &str) -> Result<Vec<String>, ()> {
    #[derive(PartialEq, Eq)]
    enum Quote {
        None,
        Single,
        Double,
    }
    let mut tokens = Vec::new();
    let mut current = String::new();
    let mut has_token = false;
    let mut quote = Quote::None;
    let mut chars = input.chars().peekable();
    while let Some(character) = chars.next() {
        match quote {
            Quote::None => match character {
                '\\' => match chars.next() {
                    Some(next) => {
                        current.push(next);
                        has_token = true;
                    }
                    None => return Err(()),
                },
                '\'' => {
                    quote = Quote::Single;
                    has_token = true;
                }
                '"' => {
                    quote = Quote::Double;
                    has_token = true;
                }
                ' ' | '\t' | '\r' | '\n' => {
                    if has_token {
                        tokens.push(std::mem::take(&mut current));
                        has_token = false;
                    }
                }
                other => {
                    current.push(other);
                    has_token = true;
                }
            },
            Quote::Single => {
                if character == '\'' {
                    quote = Quote::None;
                } else {
                    current.push(character);
                }
            }
            Quote::Double => match character {
                '"' => quote = Quote::None,
                '\\' => match chars.peek() {
                    Some(&next) if matches!(next, '"' | '\\' | '$' | '`') => {
                        current.push(next);
                        let _ = chars.next();
                    }
                    Some(_) => current.push('\\'),
                    None => return Err(()),
                },
                other => current.push(other),
            },
        }
    }
    if quote != Quote::None {
        return Err(());
    }
    if has_token {
        tokens.push(current);
    }
    Ok(tokens)
}

/// Value of the first `KEY=` line (empty string when the value is empty),
/// mirroring `larch_io.kv_value`/`read_kv` first-match policy.
fn kv_first(text: &str, key: &str) -> Option<String> {
    let prefix = format!("{key}=");
    text.split('\n')
        .find_map(|line| line.strip_prefix(&prefix).map(str::to_owned))
}

// ---------------------------------------------------------------------------
// run-log append-failure and best-effort children through the Step 0 seam
// ---------------------------------------------------------------------------

/// Canonical `run-log append-failure` argv, shared with the design terminal owner.
pub fn append_failure_args(
    log_path: String,
    site: &str,
    tool: &str,
    exit_code: &str,
    category: &str,
    output_file: &Path,
) -> Vec<String> {
    vec![
        "run-log".to_owned(),
        "append-failure".to_owned(),
        "--log".to_owned(),
        log_path,
        "--site".to_owned(),
        site.to_owned(),
        "--tool".to_owned(),
        tool.to_owned(),
        "--exit-code".to_owned(),
        exit_code.to_owned(),
        "--category".to_owned(),
        category.to_owned(),
        "--output-file".to_owned(),
        output_file.display().to_string(),
        "--redact".to_owned(),
    ]
}

/// Port of `_append_failure`: the canonical `run-log append-failure` child.
#[allow(clippy::too_many_arguments)] // Mirrors the frozen `append_failure` request fields verbatim.
fn append_failure(
    runner: &dyn Step0Runner,
    plugin_root: &Path,
    design_tmpdir: &Path,
    site: &str,
    tool: &str,
    exit_code: &str,
    category: &str,
    output_file: &Path,
) -> bool {
    let args = append_failure_args(
        design_tmpdir
            .join("execution-issues.md")
            .display()
            .to_string(),
        site,
        tool,
        exit_code,
        category,
        output_file,
    );
    runner.run(plugin_root, &args, &[], false).code == 0
}

// ---------------------------------------------------------------------------
// step1e-reentry
// ---------------------------------------------------------------------------

const STEP1E_REENTRY_SENTINELS: [&str; 10] = [
    "step-1e",
    "step-2a",
    "step-2a.5",
    "step-2b",
    "step-2b.5",
    "step-3",
    "step-3.5",
    "step-3b",
    "step-4",
    "step-4b",
];

/// The `step1e-reentry` entry point.
pub fn step1e_reentry(arguments: &[OsString]) -> ExitCode {
    let WrapperContext {
        env, design_tmpdir, ..
    } = match wrapper_context(arguments, false) {
        Ok(context) => context,
        Err(code) => return code,
    };
    let completed = design_tmpdir.join(".completed");
    for name in STEP1E_REENTRY_SENTINELS {
        let _ = fs::remove_file(completed.join(name));
    }
    if let Ok(entries) = fs::read_dir(&design_tmpdir) {
        for entry in entries.flatten() {
            if entry
                .file_name()
                .to_string_lossy()
                .starts_with(".gate-b-postapply-ready-")
            {
                let _ = fs::remove_file(entry.path());
            }
        }
    }
    if let Some(code) = check_pause_and_exit(&env, &design_tmpdir) {
        return code;
    }
    ExitCode::SUCCESS
}

// ---------------------------------------------------------------------------
// run-params.json readers
// ---------------------------------------------------------------------------

/// Port of `_step1d5_brainstorm_requested`.
fn step1d5_brainstorm_requested(design_tmpdir: &Path) -> bool {
    let run_params = design_tmpdir.join("run-params.json");
    let Ok(meta) = fs::symlink_metadata(&run_params) else {
        return false;
    };
    if meta.file_type().is_symlink() || !meta.is_file() {
        return false;
    }
    let Ok(text) = fs::read_to_string(&run_params) else {
        return false;
    };
    match serde_json::from_str::<Value>(&text) {
        Ok(value) => value.get("brainstorm_requested") == Some(&Value::Bool(true)),
        Err(_error) => {
            eprintln!(
                "**⚠ Step 1d.5: run-params.json is malformed; defaulting brainstorm_requested=false**"
            );
            false
        }
    }
}

/// Port of step1d7's `skip_approve_requested` read (truthy, no symlink guard).
fn read_skip_approve_requested(design_tmpdir: &Path) -> bool {
    let Ok(text) = fs::read_to_string(design_tmpdir.join("run-params.json")) else {
        return false;
    };
    serde_json::from_str::<Value>(&text)
        .ok()
        .and_then(|value| {
            value
                .get("skip_approve_requested")
                .map(python_truthy_of_json)
        })
        .unwrap_or(false)
}

// ---------------------------------------------------------------------------
// step1d7
// ---------------------------------------------------------------------------

/// The `step1d7` entry point.
pub fn step1d7(arguments: &[OsString]) -> ExitCode {
    let WrapperContext {
        env, design_tmpdir, ..
    } = match wrapper_context(arguments, true) {
        Ok(context) => context,
        Err(code) => return code,
    };
    if !step1d5_brainstorm_requested(&design_tmpdir) {
        mark_completed(&design_tmpdir, &["step-1c", "step-1d", "step-1d.5"]);
    }
    if let Some(code) = check_pause_and_exit(&env, &design_tmpdir) {
        return code;
    }
    let skip = read_skip_approve_requested(&design_tmpdir);
    println!(
        "SKIP_APPROVE_REQUESTED={}",
        if skip { "true" } else { "false" }
    );
    ExitCode::SUCCESS
}

// ---------------------------------------------------------------------------
// step1d5 (entry / collect / complete)
// ---------------------------------------------------------------------------

/// Extract `--mode`'s value from the wrapper argv, mirroring the Python parser
/// (`parse_wrapper_args` accepts but discards `--mode`).
fn extract_mode(argv: &[String]) -> String {
    let mut mode = String::new();
    let mut index = 0;
    while index < argv.len() {
        let token = argv[index].as_str();
        if token == "--" {
            break;
        }
        if token == "--skip-validate" || token == "--snapshot-original" {
            index += 1;
            continue;
        }
        let bound = matches!(
            token,
            "--session-env-path"
                | "--claude-pid"
                | "--plugin-root"
                | "--outcome"
                | "--issue-number"
                | "--exit-code"
                | "--failure-detail-log"
                | "--reason"
                | "--tool"
                | "--mode"
                | "--site"
                | "--step3-review-loop-status"
                | "--loop-status"
        );
        if bound {
            if token == "--mode"
                && let Some(value) = argv.get(index + 1)
            {
                mode.clone_from(value);
            }
            index += 2;
            continue;
        }
        index += 1;
    }
    mode
}

/// The `step1d5` entry point.
pub fn step1d5(arguments: &[OsString]) -> ExitCode {
    step1d5_with(arguments, &LiveStep0Runner)
}

fn step1d5_with(arguments: &[OsString], runner: &dyn Step0Runner) -> ExitCode {
    let WrapperContext {
        env,
        plugin_root,
        design_tmpdir,
        public_argv,
    } = match wrapper_context(arguments, false) {
        Ok(context) => context,
        Err(code) => return code,
    };
    let argv = utf8_arguments(arguments);
    match extract_mode(&argv).as_str() {
        "entry" => step1d5_entry(runner, &plugin_root, &design_tmpdir, &env),
        "collect" => step1d5_collect(runner, &plugin_root, &design_tmpdir, &env, &public_argv),
        "complete" => {
            mark_completed(&design_tmpdir, &["step-1d.5"]);
            if let Some(code) = check_pause_and_exit(&env, &design_tmpdir) {
                return code;
            }
            ExitCode::SUCCESS
        }
        _ => {
            eprintln!("design-step1d5.sh: --mode required");
            ExitCode::from(2)
        }
    }
}

fn step1d5_entry(
    runner: &dyn Step0Runner,
    plugin_root: &Path,
    design_tmpdir: &Path,
    env: &Env,
) -> ExitCode {
    let completed = design_tmpdir.join(".completed");
    let _ = fs::create_dir_all(&completed);
    for name in ["step-1c", "step-1d"] {
        let _ = fs::write(completed.join(name), "");
    }
    let brainstorm_requested = step1d5_brainstorm_requested(design_tmpdir);
    let (action, skip_kind) = if design_tmpdir.join(".brainstorm-done").is_file() {
        ("skip", "already-complete")
    } else if brainstorm_requested {
        ("run", "")
    } else {
        ("skip", "disabled")
    };
    if action == "skip" {
        let _ = fs::write(completed.join("step-1d.5"), "");
    }
    if let Some(code) = check_pause_and_exit(env, design_tmpdir) {
        return code;
    }
    println!("STEP1D5_ACTION={action}");
    if !skip_kind.is_empty() {
        println!("STEP1D5_SKIP_KIND={skip_kind}");
    }
    // Best-effort `timing mark`; failures are swallowed like `_run_best_effort`.
    let _ = runner.run(
        plugin_root,
        &[
            "timing".to_owned(),
            "mark".to_owned(),
            "design Step 1d.5 — brainstorm".to_owned(),
        ],
        &[("LARCH_TIMING_SKILL".to_owned(), "design".to_owned())],
        false,
    );
    ExitCode::SUCCESS
}

fn step1d5_collect(
    runner: &dyn Step0Runner,
    plugin_root: &Path,
    design_tmpdir: &Path,
    env: &Env,
    public_argv: &[String],
) -> ExitCode {
    if let Some(code) = check_pause_and_exit(env, design_tmpdir) {
        return code;
    }
    if public_argv.is_empty() {
        eprintln!("design-step1d5.sh: --mode collect requires at least one output path after --");
        return ExitCode::from(2);
    }
    let paths: Vec<PathBuf> = public_argv.iter().map(PathBuf::from).collect();
    let mut args = vec![
        "agent".to_owned(),
        "collect-results".to_owned(),
        "--timeout".to_owned(),
        "1260".to_owned(),
    ];
    args.extend(paths.iter().map(|path| path.display().to_string()));
    let collect = runner.run(plugin_root, &args, &[], false);
    let _ = fs::write(
        design_tmpdir.join("brainstorm-collect.stdout.log"),
        &collect.stdout,
    );
    let _ = fs::write(
        design_tmpdir.join("brainstorm-collect.stderr.log"),
        &collect.stderr,
    );
    if !collect.stdout.is_empty() {
        if collect.stdout.ends_with('\n') {
            print!("{}", collect.stdout);
        } else {
            println!("{}", collect.stdout);
        }
    }
    if collect.code != 0 {
        let failure = design_tmpdir.join("brainstorm-collect.failure.log");
        let _ = fs::write(&failure, format!("{}{}", collect.stdout, collect.stderr));
        let _ = append_failure(
            runner,
            plugin_root,
            design_tmpdir,
            "design Step 1d.5",
            "agent collect-results",
            &collect.code.to_string(),
            "External Reviewer Issues",
            &failure,
        );
    }
    for path in &paths {
        if let Some(sink) = brainstorm_stderr_sink_for_output(path, design_tmpdir) {
            brainstorm_collect_launch_failure_once(
                runner,
                plugin_root,
                design_tmpdir,
                &sink,
                &launch_tool_for_sink(&sink),
            );
        }
    }
    brainstorm_dirty_checkpoint(runner, plugin_root, design_tmpdir, &paths);
    ExitCode::SUCCESS
}

/// Port of `brainstorm_stderr_sink_for_output`.
fn brainstorm_stderr_sink_for_output(output_path: &Path, design_tmpdir: &Path) -> Option<PathBuf> {
    let file_name = output_path.file_name()?.to_string_lossy().into_owned();
    let meta = output_path.with_file_name(format!("{file_name}.meta"));
    if meta.is_file()
        && let Ok(raw) = fs::read_to_string(&meta)
    {
        let text = splitlines(&raw).join("\n");
        if let Some(sink) = kv_first(&text, "STDERR_SINK").filter(|value| !value.is_empty()) {
            return Some(PathBuf::from(sink));
        }
    }
    match file_name.as_str() {
        "cursor-brainstorm-output.txt" => {
            Some(design_tmpdir.join("cursor-brainstorm-launch.failure.log"))
        }
        "codex-brainstorm-output.txt" => {
            Some(design_tmpdir.join("codex-brainstorm-launch.failure.log"))
        }
        _ => None,
    }
}

/// Port of `_launch_tool_for_sink`.
fn launch_tool_for_sink(sink: &Path) -> String {
    let name = sink
        .file_name()
        .map_or_else(String::new, |value| value.to_string_lossy().into_owned());
    name.strip_suffix(".failure.log")
        .map_or_else(|| name.clone(), str::to_owned)
}

/// Port of `brainstorm_collect_launch_failure_once`.
fn brainstorm_collect_launch_failure_once(
    runner: &dyn Step0Runner,
    plugin_root: &Path,
    design_tmpdir: &Path,
    log_path: &Path,
    tool: &str,
) {
    let Ok(meta) = fs::metadata(log_path) else {
        return;
    };
    if !meta.is_file() || meta.len() == 0 {
        return;
    }
    let log_name = log_path
        .file_name()
        .map_or_else(String::new, |value| value.to_string_lossy().into_owned());
    let sentinel = design_tmpdir.join(format!(".brainstorm-{log_name}.runlog-appended"));
    if sentinel.exists() {
        return;
    }
    let mut exit_code = fs::read_to_string(log_path)
        .ok()
        .map(|raw| splitlines(&raw).join("\n"))
        .and_then(|text| kv_first(&text, "LAUNCHER_EXIT"))
        .filter(|value| !value.is_empty())
        .unwrap_or_else(|| "1".to_owned());
    if !exit_code
        .chars()
        .all(|character| character.is_ascii_digit())
    {
        exit_code = String::from("1");
    }
    if append_failure(
        runner,
        plugin_root,
        design_tmpdir,
        "design Step 1d.5",
        tool,
        &exit_code,
        "External Reviewer Issues",
        log_path,
    ) {
        let _ = fs::write(&sentinel, "");
    }
}

/// Port of `_brainstorm_dirty_checkpoint`.
fn brainstorm_dirty_checkpoint(
    runner: &dyn Step0Runner,
    plugin_root: &Path,
    design_tmpdir: &Path,
    paths: &[PathBuf],
) {
    let mut recovery = false;
    let mut reason = String::new();
    for path in paths {
        let file_name = path
            .file_name()
            .map_or_else(String::new, |value| value.to_string_lossy().into_owned());
        let sidecar = path.with_file_name(format!("{file_name}.dirty-tree"));
        if sidecar.is_file()
            && let Ok(text) = fs::read_to_string(&sidecar)
        {
            let status = kv_last_status(&text);
            if status == "dirty" || status == "unknown" {
                recovery = true;
                reason = status;
            }
        }
    }
    let stdout_path = design_tmpdir.join("brainstorm-dirty-tree.checkpoint.out");
    let stderr_path = design_tmpdir.join("brainstorm-dirty-tree.checkpoint.err");
    let checkpoint = runner.run(
        plugin_root,
        &["dirty-tree".to_owned(), "checkpoint".to_owned()],
        &[],
        false,
    );
    let _ = fs::write(&stdout_path, &checkpoint.stdout);
    let _ = fs::write(&stderr_path, &checkpoint.stderr);
    let raw_status = kv_last(&checkpoint.stdout, "STATUS");
    let status = if checkpoint.code != 0 && raw_status.is_empty() {
        String::from("unknown")
    } else {
        raw_status
    };
    if status == "dirty" || status == "unknown" {
        recovery = true;
        if reason.is_empty() {
            reason = status;
        }
    }
    let detected = design_tmpdir.join("dirty-tree-detected.env");
    if recovery {
        let label = if reason.is_empty() {
            "unknown"
        } else {
            &reason
        };
        let mut text = format!(
            "STAGE=brainstorm-collection\nRECOVERY_REQUIRED=true\nDIRTY_TREE_STATUS={label}\n"
        );
        if fs::metadata(&stdout_path).is_ok_and(|meta| meta.len() > 0)
            && let Ok(extra) = fs::read_to_string(&stdout_path)
        {
            text.push_str(&extra);
        }
        let _ = fs::write(&detected, text);
        println!("WARN=brainstorm-collection dirty-tree recovery required (status={label})");
    } else {
        let _ = fs::write(
            &detected,
            "STAGE=brainstorm-collection\nRECOVERY_REQUIRED=false\n",
        );
    }
}

/// Last `STATUS=` value, defaulting to `unknown` for the sidecar reader (which
/// substitutes `unknown` for a missing/empty value).
fn kv_last_status(text: &str) -> String {
    let value = kv_last(text, "STATUS");
    if value.is_empty() {
        "unknown".to_owned()
    } else {
        value
    }
}

/// Last `KEY=` value across `\n`-split lines (empty when absent).
fn kv_last(text: &str, key: &str) -> String {
    let prefix = format!("{key}=");
    text.split('\n')
        .filter_map(|line| line.strip_prefix(&prefix))
        .next_back()
        .unwrap_or("")
        .to_owned()
}

// ---------------------------------------------------------------------------
// driver
// ---------------------------------------------------------------------------

const DRIVER_DISPATCH_ACTIONS: [&str; 4] =
    ["EMIT_PLAN", "TALLY", "FINALIZE", "VALIDATE_PLAN_COMMANDS"];

/// The consumer repository's git toplevel, or `None` outside a work tree.
pub fn consumer_repo_root() -> Option<PathBuf> {
    let work_dir = GixRepository::discover(std::env::current_dir().ok()?)
        .ok()?
        .location()
        .work_dir?;
    Some(PathBuf::from(
        String::from_utf8_lossy(work_dir.as_bytes()).into_owned(),
    ))
}

struct DriverArgs {
    design_tmpdir: String,
    action_file: String,
    resume_from: String,
}

/// Parse the driver argv (`argparse` with `--design-tmpdir`, `--action-file`,
/// `--resume-from`). Any extra token or a missing `--design-tmpdir` is exit 2.
fn parse_driver_args(argv: &[String]) -> Result<DriverArgs, ExitCode> {
    let mut parsed = DriverArgs {
        design_tmpdir: String::new(),
        action_file: String::new(),
        resume_from: String::new(),
    };
    let mut extra = false;
    let mut index = 0;
    while index < argv.len() {
        if let token @ ("--design-tmpdir" | "--action-file" | "--resume-from") =
            argv[index].as_str()
        {
            let Some(value) = argv.get(index + 1) else {
                return Err(ExitCode::from(2));
            };
            match token {
                "--design-tmpdir" => parsed.design_tmpdir.clone_from(value),
                "--action-file" => parsed.action_file.clone_from(value),
                _ => parsed.resume_from.clone_from(value),
            }
            index += 2;
        } else {
            extra = true;
            index += 1;
        }
    }
    if extra || parsed.design_tmpdir.is_empty() {
        return Err(ExitCode::from(2));
    }
    Ok(parsed)
}

/// The `driver` entry point.
pub fn driver(arguments: &[OsString]) -> ExitCode {
    driver_with(arguments, &LiveStep0Runner)
}

fn driver_with(arguments: &[OsString], runner: &dyn Step0Runner) -> ExitCode {
    let argv = utf8_arguments(arguments);
    let parsed = match parse_driver_args(&argv) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let design_tmpdir = fs::canonicalize(&parsed.design_tmpdir)
        .unwrap_or_else(|_error| PathBuf::from(&parsed.design_tmpdir));
    let completed = design_tmpdir.join(".completed");
    let _ = fs::create_dir_all(&completed);
    let plugin_root = PathBuf::from(env_or("CLAUDE_PLUGIN_ROOT", ""));

    let action_lines = if parsed.action_file.is_empty() {
        let mut buffer = String::new();
        let _ = std::io::stdin().read_to_string(&mut buffer);
        splitlines(&buffer)
    } else {
        match fs::read(&parsed.action_file) {
            Ok(bytes) => splitlines(&String::from_utf8_lossy(&bytes)),
            Err(_error) => Vec::new(),
        }
    };

    let mut state = DriverState {
        resume_seen: parsed.resume_from.is_empty(),
        resume_norm: normalize_step(&parsed.resume_from),
        consumer_root: None,
    };
    for line in action_lines {
        match dispatch_action_line(
            runner,
            &plugin_root,
            &design_tmpdir,
            &parsed,
            &mut state,
            &line,
        ) {
            LineOutcome::Continue => {}
            LineOutcome::Exit(code) => return code,
        }
    }
    ExitCode::SUCCESS
}

struct DriverState {
    resume_seen: bool,
    resume_norm: String,
    consumer_root: Option<PathBuf>,
}

enum LineOutcome {
    Continue,
    Exit(ExitCode),
}

fn env_or(key: &str, default: &str) -> String {
    std::env::var(key).unwrap_or_else(|_error| default.to_owned())
}

#[allow(clippy::too_many_lines)] // One `driver_main` per-line dispatch state machine, ported branch for branch.
fn dispatch_action_line(
    runner: &dyn Step0Runner,
    plugin_root: &Path,
    design_tmpdir: &Path,
    args: &DriverArgs,
    state: &mut DriverState,
    line: &str,
) -> LineOutcome {
    if line.is_empty() {
        return LineOutcome::Continue;
    }
    let Some(rest) = line.strip_prefix("ACTION=") else {
        println!("ACTION_PASSTHROUGH={line}");
        return LineOutcome::Continue;
    };
    let action = rest.split(' ').next().unwrap_or("");
    if action == "CLASSIFY" {
        println!("STEP_FAILED=CLASSIFY REASON=deprecated-action");
        return LineOutcome::Exit(ExitCode::from(2));
    }
    if !DRIVER_DISPATCH_ACTIONS.contains(&action) {
        println!("ACTION_PASSTHROUGH={line}");
        return LineOutcome::Continue;
    }
    let sentinel = design_tmpdir
        .join(".completed")
        .join(normalize_step(action));
    let no_sentinel = action == "EMIT_PLAN" || action == "VALIDATE_PLAN_COMMANDS";
    if state.resume_seen {
        if sentinel.exists() && !no_sentinel {
            println!("STEP_SKIPPED={action} REASON=already-completed");
            return LineOutcome::Continue;
        }
    } else if action == args.resume_from || normalize_step(action) == state.resume_norm {
        state.resume_seen = true;
    } else if sentinel.exists() && !no_sentinel {
        println!("STEP_SKIPPED={action} REASON=completed-before-resume");
        return LineOutcome::Continue;
    } else {
        println!("STEP_SKIPPED={action} REASON=before-resume");
        return LineOutcome::Continue;
    }
    let args_text = extract_args(line);
    let action_args = if args_text.is_empty() {
        Vec::new()
    } else if let Ok(parsed) = shlex_split(&args_text) {
        parsed
    } else {
        println!("STEP_FAILED={action} REASON=bad-args");
        return LineOutcome::Exit(ExitCode::from(2));
    };
    println!("STEP_STARTED={action}");
    let (child_args, child_env) = driver_child_command(action, design_tmpdir, &action_args, state);
    let outcome = runner.run(plugin_root, &child_args, &child_env, false);
    if !outcome.stdout.is_empty() {
        print!("{}", outcome.stdout);
    }
    if outcome.code != 0 {
        println!("STEP_FAILED={action} REASON=exit-{}", outcome.code);
        return LineOutcome::Exit(exit_from_i32(outcome.code));
    }
    if !no_sentinel {
        let _ = fs::write(&sentinel, "");
    }
    println!("STEP_COMPLETED={action}");
    LineOutcome::Continue
}

fn driver_child_command(
    action: &str,
    design_tmpdir: &Path,
    action_args: &[String],
    state: &mut DriverState,
) -> (Vec<String>, Vec<(String, String)>) {
    let design = design_tmpdir.display().to_string();
    match action {
        "EMIT_PLAN" | "TALLY" | "FINALIZE" => {
            let verb = match action {
                "EMIT_PLAN" => "emit",
                "TALLY" => "tally",
                _ => "finalize",
            };
            let mut args = vec![
                "plan-review".to_owned(),
                verb.to_owned(),
                "--design-tmpdir".to_owned(),
                design,
            ];
            args.extend(action_args.iter().cloned());
            (args, Vec::new())
        }
        _ => {
            let consumer_root = state
                .consumer_root
                .get_or_insert_with(|| consumer_repo_root().unwrap_or_else(design_tmpdir_root))
                .display()
                .to_string();
            let mut args = vec![
                "plan".to_owned(),
                "validate".to_owned(),
                "--design-tmpdir".to_owned(),
                design.clone(),
                "--repo-root".to_owned(),
                consumer_root,
            ];
            args.extend(action_args.iter().cloned());
            (args, vec![("DESIGN_TMPDIR".to_owned(), design)])
        }
    }
}

/// The `driver`'s Python fallback root: `Path(__file__).resolve().parents[3]`,
/// which resolves to the repository/plugin root the entrypoint already names.
fn design_tmpdir_root() -> PathBuf {
    PathBuf::from(env_or("CLAUDE_PLUGIN_ROOT", "."))
}

// ---------------------------------------------------------------------------
// plan step1-log
// ---------------------------------------------------------------------------

fn step1_log_fail(message: &str) -> ExitCode {
    eprintln!("run-step1-plan-log.sh: {message}");
    ExitCode::from(2)
}

const STEP1_LOG_USAGE: &str =
    "Usage: run-step1-plan-log.sh --implement-tmpdir PATH --goal-text TEXT";

struct Step1LogArgs {
    implement_tmpdir: String,
    goal_text: String,
}

fn parse_step1_log_args(argv: &[String]) -> Result<Option<Step1LogArgs>, ExitCode> {
    let mut implement_tmpdir = String::new();
    let mut goal_text = String::new();
    let mut goal_text_set = false;
    let mut index = 0;
    while index < argv.len() {
        match argv[index].as_str() {
            "--implement-tmpdir" => {
                let Some(value) = argv.get(index + 1) else {
                    return Err(step1_log_fail("--implement-tmpdir requires a value"));
                };
                implement_tmpdir.clone_from(value);
                index += 2;
            }
            "--goal-text" => {
                let Some(value) = argv.get(index + 1) else {
                    return Err(step1_log_fail("--goal-text requires a value"));
                };
                goal_text.clone_from(value);
                goal_text_set = true;
                index += 2;
            }
            "-h" | "--help" => {
                eprintln!("{STEP1_LOG_USAGE}");
                return Ok(None);
            }
            other => {
                eprintln!("{STEP1_LOG_USAGE}");
                return Err(step1_log_fail(&format!("unknown option: {other}")));
            }
        }
    }
    if implement_tmpdir.is_empty() {
        eprintln!("{STEP1_LOG_USAGE}");
        return Err(step1_log_fail("--implement-tmpdir is required"));
    }
    if !goal_text_set {
        eprintln!("{STEP1_LOG_USAGE}");
        return Err(step1_log_fail("--goal-text is required"));
    }
    Ok(Some(Step1LogArgs {
        implement_tmpdir,
        goal_text,
    }))
}

/// Port of `_resolve_run_id`.
fn resolve_run_id(session_env_path: &Path, implement_tmpdir: &Path) -> String {
    let mut run_id = session_read(session_env_path, "RUN_ID");
    if run_id.is_empty() {
        run_id = session_read(&implement_tmpdir.join("parent-issue.md"), "RUN_ID");
    }
    if run_id.is_empty() {
        let manifests: Vec<PathBuf> =
            fs::read_dir(implement_tmpdir.join("larch-logs").join("implement"))
                .into_iter()
                .flatten()
                .flatten()
                .map(|entry| entry.path().join("manifest.json"))
                .filter(|path| path.is_file())
                .collect();
        if manifests.len() == 1
            && let Some(parent) = manifests[0].parent()
            && let Some(name) = parent.file_name()
        {
            run_id = name.to_string_lossy().into_owned();
        }
    }
    if run_id.is_empty() {
        let session_id = implement_tmpdir.join("session-id");
        if session_id.is_file()
            && let Ok(text) = fs::read_to_string(&session_id)
        {
            text.trim().clone_into(&mut run_id);
        }
    }
    run_id
}

/// Port of `_session_read`: first-match `KEY=` value from a file, empty when
/// absent or unreadable.
fn session_read(path: &Path, key: &str) -> String {
    if !path.is_file() {
        return String::new();
    }
    fs::read_to_string(path)
        .ok()
        .and_then(|text| kv_first(&text, key))
        .unwrap_or_default()
}

/// Locate `python3` on `PATH` for the default compose command.
fn python3_executable() -> PathBuf {
    if let Some(paths) = std::env::var_os("PATH") {
        for candidate in std::env::split_paths(&paths).map(|dir| dir.join("python3")) {
            if candidate.is_file() {
                return candidate;
            }
        }
    }
    PathBuf::from("python3")
}

fn apply_child_env(command: &mut Command, plugin_root: &Path, implement_tmpdir: &Path) {
    command.env("CLAUDE_PLUGIN_ROOT", plugin_root);
    command.env("IMPLEMENT_TMPDIR", implement_tmpdir);
}

/// The `step1-log` entry point.
pub fn step1_log(arguments: &[OsString]) -> ExitCode {
    let argv = utf8_arguments(arguments);
    let parsed = match parse_step1_log_args(&argv) {
        Ok(Some(parsed)) => parsed,
        Ok(None) => return ExitCode::SUCCESS,
        Err(code) => return code,
    };
    let implement_tmpdir_arg = PathBuf::from(&parsed.implement_tmpdir);
    if !implement_tmpdir_arg.is_dir() {
        return step1_log_fail(&format!(
            "--implement-tmpdir not a directory: {}",
            parsed.implement_tmpdir
        ));
    }
    let implement_tmpdir = fs::canonicalize(&implement_tmpdir_arg).unwrap_or(implement_tmpdir_arg);
    let session_env_path = implement_tmpdir.join("session-env.sh");
    if !session_env_path.is_file() {
        return step1_log_fail(&format!(
            "session-env not readable: {}",
            session_env_path.display()
        ));
    }
    let run_id = resolve_run_id(&session_env_path, &implement_tmpdir);
    if run_id.is_empty() {
        return step1_log_fail(
            "RUN_ID unresolved from session-env, parent-issue, manifest, or session-id",
        );
    }
    let plan_file = implement_tmpdir.join("plan.txt");
    if !plan_file.is_file() {
        return step1_log_fail(&format!(
            "plan file not found at conventional path: {}",
            plan_file.display()
        ));
    }
    let plugin_root_value = {
        let from_env = env_or("CLAUDE_PLUGIN_ROOT", "");
        if from_env.is_empty() {
            session_read(&session_env_path, "LARCH_CLAUDE_PLUGIN_ROOT")
        } else {
            from_env
        }
    };
    let plugin_root = PathBuf::from(&plugin_root_value);
    if !plugin_root.is_dir() {
        return step1_log_fail(&format!(
            "plugin root not a directory: {}",
            plugin_root.display()
        ));
    }
    match run_step1_log(
        &plugin_root,
        &implement_tmpdir,
        &plan_file,
        &parsed.goal_text,
        &run_id,
    ) {
        Ok(code) | Err(code) => code,
    }
}

fn run_step1_log(
    plugin_root: &Path,
    implement_tmpdir: &Path,
    plan_file: &Path,
    goal_text: &str,
    run_id: &str,
) -> Result<ExitCode, ExitCode> {
    let compose_cmd = compose_command(plugin_root);
    let larch_log_cmd = larch_log_command(plugin_root)?;
    let output_file = implement_tmpdir.join("plan-goals-test.md");
    if let Some(code) = compose_to_output(
        &compose_cmd,
        plugin_root,
        implement_tmpdir,
        plan_file,
        goal_text,
        &output_file,
    )? {
        return Ok(code);
    }
    // run-log write for the composed plan-goals-test document.
    let write_result = run_larch_log_write(
        &larch_log_cmd,
        plugin_root,
        implement_tmpdir,
        run_id,
        "plan-goals-test",
        &output_file,
    );
    if let Some(stdout) = &write_result.0 {
        print!("{stdout}");
    }
    if let Some(stderr) = &write_result.1 {
        eprint!("{stderr}");
    }
    if write_result.2 != 0 {
        return Ok(exit_from_i32(write_result.2));
    }
    log_parent_issue(&larch_log_cmd, plugin_root, implement_tmpdir, run_id);
    Ok(ExitCode::SUCCESS)
}

fn compose_command(plugin_root: &Path) -> Vec<String> {
    let override_value = env_or("RUN_STEP1_COMPOSE_CMD", "");
    let trimmed = override_value.trim();
    if trimmed.is_empty() {
        vec![
            python3_executable().display().to_string(),
            plugin_root
                .join("python")
                .join("cli.py")
                .display()
                .to_string(),
            "plan".to_owned(),
            "compose-goals-test".to_owned(),
        ]
    } else {
        shlex_split(trimmed).unwrap_or_default()
    }
}

fn larch_log_command(plugin_root: &Path) -> Result<Vec<String>, ExitCode> {
    let override_value = env_or("RUN_STEP1_LARCH_LOG_SH", "");
    let trimmed = override_value.trim();
    if trimmed.is_empty() {
        let entry = entrypoint(plugin_root);
        if !entry.is_file() {
            return Err(step1_log_fail(&format!(
                "larch bootstrap missing: {}",
                entry.display()
            )));
        }
        Ok(vec![entry.display().to_string()])
    } else if is_executable(Path::new(trimmed)) {
        Ok(vec![trimmed.to_owned()])
    } else {
        Err(step1_log_fail(&format!(
            "run-log override not executable: {trimmed}"
        )))
    }
}

#[cfg(unix)]
fn is_executable(path: &Path) -> bool {
    use std::os::unix::fs::PermissionsExt as _;
    fs::metadata(path).is_ok_and(|meta| meta.is_file() && meta.permissions().mode() & 0o111 != 0)
}

#[cfg(not(unix))]
fn is_executable(path: &Path) -> bool {
    path.is_file()
}

/// Compose the plan-goals-test document into a temp file, then atomically
/// rename it into place. Returns `Ok(Some(code))` when compose exits non-zero.
fn compose_to_output(
    compose_cmd: &[String],
    plugin_root: &Path,
    implement_tmpdir: &Path,
    plan_file: &Path,
    goal_text: &str,
    output_file: &Path,
) -> Result<Option<ExitCode>, ExitCode> {
    let Some((program, program_args)) = compose_cmd.split_first() else {
        return Err(step1_log_fail("compose command is empty"));
    };
    let temp = implement_tmpdir.join(format!("plan-goals-test.md.tmp.{}", std::process::id()));
    let file = match fs::File::create(&temp) {
        Ok(file) => file,
        Err(error) => {
            return Err(step1_log_fail(&format!(
                "compose temp create failed: {error}"
            )));
        }
    };
    let mut command = Command::new(program); // lint-subprocess-via-runner: ok leaf seam that runs the composed plan-goals drafter command, mirroring the frozen design_step_log.py subprocess call
    command.args(program_args);
    command.args(["--plan-file", &plan_file.display().to_string()]);
    command.args(["--goal-text", goal_text]);
    apply_child_env(&mut command, plugin_root, implement_tmpdir);
    command.stdout(Stdio::from(file));
    let status = command.status();
    let code = match status {
        Ok(status) => status.code().unwrap_or(1),
        Err(_error) => {
            let _ = fs::remove_file(&temp);
            return Err(step1_log_fail("compose command failed to launch"));
        }
    };
    if code != 0 {
        let _ = fs::remove_file(&temp);
        return Ok(Some(exit_from_i32(code)));
    }
    if let Err(error) = fs::rename(&temp, output_file) {
        let _ = fs::remove_file(&temp);
        return Err(step1_log_fail(&format!("compose rename failed: {error}")));
    }
    Ok(None)
}

fn run_larch_log_write(
    larch_log_cmd: &[String],
    plugin_root: &Path,
    implement_tmpdir: &Path,
    run_id: &str,
    batch: &str,
    input_file: &Path,
) -> (Option<String>, Option<String>, i32) {
    let Some((program, program_args)) = larch_log_cmd.split_first() else {
        return (None, None, 1);
    };
    let mut command = Command::new(program); // lint-subprocess-via-runner: ok leaf seam that runs the larch `run-log write` entrypoint, mirroring the frozen design_step_log.py subprocess call
    command.args(program_args);
    command.args([
        "run-log",
        "write",
        "--log-root",
        &implement_tmpdir.join("larch-logs").display().to_string(),
        "--skill",
        "implement",
        "--run-id",
        run_id,
        "--batch",
        batch,
        "--input-file",
        &input_file.display().to_string(),
    ]);
    apply_child_env(&mut command, plugin_root, implement_tmpdir);
    match command.output() {
        Ok(output) => (
            Some(String::from_utf8_lossy(&output.stdout).into_owned()),
            Some(String::from_utf8_lossy(&output.stderr).into_owned()),
            output.status.code().unwrap_or(1),
        ),
        Err(_error) => (None, None, 1),
    }
}

/// Best-effort `run-log write` for `parent-issue.md`, mirroring the frozen
/// module's failure-log breadcrumb.
fn log_parent_issue(
    larch_log_cmd: &[String],
    plugin_root: &Path,
    implement_tmpdir: &Path,
    run_id: &str,
) {
    let parent_issue = implement_tmpdir.join("parent-issue.md");
    if !parent_issue.is_file() {
        return;
    }
    let (stdout, stderr, code) = run_larch_log_write(
        larch_log_cmd,
        plugin_root,
        implement_tmpdir,
        run_id,
        "parent-issue",
        &parent_issue,
    );
    if code != 0 {
        let fail_log = implement_tmpdir.join("parent-issue-write.failure.log");
        let _ = fs::write(
            &fail_log,
            format!(
                "{}{}",
                stdout.unwrap_or_default(),
                stderr.unwrap_or_default()
            ),
        );
        append_log_write_failure(plugin_root, implement_tmpdir, &fail_log);
    }
}

fn append_log_write_failure(plugin_root: &Path, implement_tmpdir: &Path, output_file: &Path) {
    let helper = entrypoint(plugin_root);
    if !helper.is_file() {
        eprintln!(
            "run-step1-plan-log.sh: best-effort log write failed for scripts/larch.sh run-log write parent-issue (see {})",
            output_file.display()
        );
        return;
    }
    let mut command = Command::new(&helper); // lint-subprocess-via-runner: ok leaf seam that runs the larch `run-log append-failure` entrypoint, mirroring the frozen design_step_log.py subprocess call
    command.args([
        "run-log",
        "append-failure",
        "--log",
        &implement_tmpdir
            .join("execution-issues.md")
            .display()
            .to_string(),
        "--site",
        "1",
        "--tool",
        "scripts/larch.sh run-log write parent-issue",
        "--exit-code",
        "1",
        "--category",
        "Warnings",
        "--output-file",
        &output_file.display().to_string(),
        "--redact",
    ]);
    apply_child_env(&mut command, plugin_root, implement_tmpdir);
    command.stdout(Stdio::null());
    command.stderr(Stdio::null());
    let _ = command.status();
}

#[cfg(test)]
mod tests {
    use std::{cell::RefCell, ffi::OsString, fs, path::Path, process::ExitCode};

    use larch_test_support::{DesignFixture, DesignSession};

    use crate::design_step0_commands::{ChildOutcome, Step0Runner};

    use super::{driver_with, step1d5_with, step1d7, step1e_reentry};

    fn arguments(values: &[&str]) -> Vec<OsString> {
        values.iter().map(OsString::from).collect()
    }

    struct RecordingRunner {
        calls: RefCell<Vec<Vec<String>>>,
        answers: RefCell<Vec<ChildOutcome>>,
    }

    impl RecordingRunner {
        fn new(answers: Vec<ChildOutcome>) -> Self {
            Self {
                calls: RefCell::new(Vec::new()),
                answers: RefCell::new(answers),
            }
        }
    }

    impl Step0Runner for RecordingRunner {
        fn run(
            &self,
            _plugin_root: &Path,
            args: &[String],
            _env: &[(String, String)],
            _merge_stderr: bool,
        ) -> ChildOutcome {
            self.calls.borrow_mut().push(args.to_vec());
            let mut answers = self.answers.borrow_mut();
            if answers.is_empty() {
                ChildOutcome {
                    code: 0,
                    stdout: String::new(),
                    stderr: String::new(),
                }
            } else {
                answers.remove(0)
            }
        }
    }

    fn ok(stdout: &str) -> ChildOutcome {
        ChildOutcome {
            code: 0,
            stdout: stdout.to_owned(),
            stderr: String::new(),
        }
    }

    /// Write a plain `KEY=value` source env the wrapper loader reads for
    /// `CLAUDE_PLUGIN_ROOT`/`DESIGN_TMPDIR` (no special characters to quote).
    fn source_env(path: &Path, plugin_root: &Path, design_tmpdir: &Path) {
        fs::write(
            path,
            format!(
                "CLAUDE_PLUGIN_ROOT={}\nDESIGN_TMPDIR={}\n",
                plugin_root.to_string_lossy(),
                design_tmpdir.to_string_lossy(),
            ),
        )
        .expect("write source env");
    }

    struct Fixture {
        _session: DesignSession,
        design_tmpdir: std::path::PathBuf,
        plugin_root: std::path::PathBuf,
        source: std::path::PathBuf,
    }

    fn fixture() -> Fixture {
        let session = DesignSession::builder(DesignFixture::Absent)
            .build()
            .expect("build design session");
        let design_tmpdir = session.root().join("design-tmpdir");
        fs::create_dir_all(&design_tmpdir).expect("create design tmpdir");
        let plugin_root = session.root().join("plugin");
        fs::create_dir_all(&plugin_root).expect("create plugin root");
        let source = session.root().join("source-env.sh");
        source_env(&source, &plugin_root, &design_tmpdir);
        Fixture {
            _session: session,
            design_tmpdir,
            plugin_root,
            source,
        }
    }

    fn wrapper_args<'a>(fixture: &'a Fixture, tail: &[&'a str]) -> Vec<OsString> {
        let mut values = vec![
            "--plugin-root",
            fixture.plugin_root.to_str().expect("utf8"),
            "--session-env-path",
            fixture.source.to_str().expect("utf8"),
        ];
        values.extend_from_slice(tail);
        arguments(&values)
    }

    #[test]
    fn step1e_reentry_unlinks_only_the_reentry_sentinels() {
        let fixture = fixture();
        let completed = fixture.design_tmpdir.join(".completed");
        fs::create_dir_all(&completed).expect("completed dir");
        for name in ["step-1c", "step-1e", "step-2a", "step-4b"] {
            fs::write(completed.join(name), "").expect("seed sentinel");
        }
        let gate = fixture.design_tmpdir.join(".gate-b-postapply-ready-abc");
        fs::write(&gate, "").expect("seed gate marker");

        let code = step1e_reentry(&wrapper_args(&fixture, &[]));

        assert_eq!(code, ExitCode::SUCCESS);
        assert!(completed.join("step-1c").is_file());
        for name in ["step-1e", "step-2a", "step-4b"] {
            assert!(!completed.join(name).exists());
        }
        assert!(!gate.exists());
    }

    #[test]
    fn step1d7_brainstorm_off_writes_prerequisite_sentinels() {
        let fixture = fixture();
        let code = step1d7(&wrapper_args(&fixture, &[]));
        assert_eq!(code, ExitCode::SUCCESS);
        let completed = fixture.design_tmpdir.join(".completed");
        for name in ["step-1c", "step-1d", "step-1d.5"] {
            assert!(completed.join(name).is_file());
        }
    }

    #[test]
    fn step1d5_entry_disabled_writes_completion_and_marks_timing() {
        let fixture = fixture();
        let runner = RecordingRunner::new(Vec::new());
        let code = step1d5_with(&wrapper_args(&fixture, &["--mode", "entry"]), &runner);
        assert_eq!(code, ExitCode::SUCCESS);
        let completed = fixture.design_tmpdir.join(".completed");
        for name in ["step-1c", "step-1d", "step-1d.5"] {
            assert!(completed.join(name).is_file());
        }
        let calls = runner.calls.borrow();
        assert_eq!(calls.len(), 1);
        assert_eq!(calls[0][0], "timing");
        assert_eq!(calls[0][1], "mark");
    }

    #[test]
    fn step1d5_collect_spawns_agent_and_dirty_checkpoint() {
        let fixture = fixture();
        let output = fixture.design_tmpdir.join("cursor-brainstorm-output.txt");
        let runner = RecordingRunner::new(vec![ok("SLOT=cursor\n"), ok("STATUS=clean\n")]);
        let code = step1d5_with(
            &wrapper_args(
                &fixture,
                &["--mode", "collect", "--", output.to_str().expect("utf8")],
            ),
            &runner,
        );
        assert_eq!(code, ExitCode::SUCCESS);
        let calls = runner.calls.borrow();
        assert_eq!(calls[0][0], "agent");
        assert_eq!(calls[0][1], "collect-results");
        assert_eq!(calls[0][2], "--timeout");
        assert_eq!(calls[0][3], "1260");
        assert_eq!(calls.last().expect("checkpoint call")[0], "dirty-tree");
        assert!(
            fixture
                .design_tmpdir
                .join("brainstorm-collect.stdout.log")
                .is_file()
        );
        assert!(
            fixture
                .design_tmpdir
                .join("dirty-tree-detected.env")
                .is_file()
        );
    }

    #[test]
    fn step1d5_collect_rejects_missing_output_paths() {
        let fixture = fixture();
        let runner = RecordingRunner::new(Vec::new());
        let code = step1d5_with(&wrapper_args(&fixture, &["--mode", "collect"]), &runner);
        assert_eq!(code, ExitCode::from(2));
        assert!(runner.calls.borrow().is_empty());
    }

    fn driver_args(design_tmpdir: &Path, action_file: &Path) -> Vec<OsString> {
        arguments(&[
            "--design-tmpdir",
            design_tmpdir.to_str().expect("utf8"),
            "--action-file",
            action_file.to_str().expect("utf8"),
        ])
    }

    #[test]
    fn driver_dispatches_emit_plan_child() {
        let fixture = fixture();
        let action_file = fixture.design_tmpdir.join("actions.txt");
        fs::write(&action_file, "ACTION=EMIT_PLAN\n").expect("seed actions");
        let runner = RecordingRunner::new(vec![ok("EMIT_PLAN_STATUS=ok\n")]);
        let code = driver_with(&driver_args(&fixture.design_tmpdir, &action_file), &runner);
        assert_eq!(code, ExitCode::SUCCESS);
        let calls = runner.calls.borrow();
        assert_eq!(calls.len(), 1);
        assert_eq!(calls[0][0], "plan-review");
        assert_eq!(calls[0][1], "emit");
        assert_eq!(calls[0][2], "--design-tmpdir");
    }

    #[test]
    fn driver_classify_action_fails_without_dispatch() {
        let fixture = fixture();
        let action_file = fixture.design_tmpdir.join("actions.txt");
        fs::write(&action_file, "ACTION=CLASSIFY\n").expect("seed actions");
        let runner = RecordingRunner::new(Vec::new());
        let code = driver_with(&driver_args(&fixture.design_tmpdir, &action_file), &runner);
        assert_eq!(code, ExitCode::from(2));
        assert!(runner.calls.borrow().is_empty());
    }

    #[test]
    fn driver_bad_args_fails_without_dispatch() {
        let fixture = fixture();
        let action_file = fixture.design_tmpdir.join("actions.txt");
        fs::write(&action_file, "ACTION=EMIT_PLAN ARGS=\"unterminated\n").expect("seed actions");
        let runner = RecordingRunner::new(Vec::new());
        let code = driver_with(&driver_args(&fixture.design_tmpdir, &action_file), &runner);
        assert_eq!(code, ExitCode::from(2));
        assert!(runner.calls.borrow().is_empty());
    }
}
