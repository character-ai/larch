//! Bootstrap routing compatibility commands.
//!
//! `parse-routing` and `resolve-non-interactive` are self-contained state
//! adapters. `invoke` owns all of Step 0; its continuation phase lives in the
//! private implementation module so one public command owns the complete
//! session, tracking, plan, coder-selection, and routing contract.

use crate::{
    agent_commands,
    bootstrap_support::{valid_run_id, write_session_text},
    child_process::run_host_utility,
    progress_commands,
    runtime_entrypoint::{plugin_root, run_verified_larch},
    session_env_commands,
};
use larch_adapters::{TemporaryRoot, atomic_write_utf8_in};
use larch_core::{
    CrStrip, DuplicatePolicy, GateDecision, HostUtilityProgram, KvDocument, ParseOptions,
    entry_gate, shell_quote, validate_progress_run_id, validate_repo_root_value,
};
use std::{
    collections::BTreeMap,
    env,
    ffi::OsString,
    fs,
    path::{Path, PathBuf},
    process::ExitCode,
    time::Duration,
};

pub const ROUTING_KEYS: &[&str] = &[
    "IMPLEMENT_TMPDIR",
    "IMPLEMENT_BAIL_REASON",
    "STALL_TRACKING",
    "PLAN_FILE",
    "coder",
    "coder_fallback",
    "REPO_UNAVAILABLE",
    "DEFERRED",
    "ISSUE_NUMBER",
    "REPO",
    "REPO_ROOT",
    "CODEX_BINARY_FOUND",
    "CURSOR_BINARY_FOUND",
    "codex_available",
    "cursor_available",
    "RUN_ID",
    "BRANCH_NAME",
    "BRANCH_ACTION",
    "SELF_REVIEW_REQUESTED",
    "SELF_IMPLEMENT_REQUESTED",
    "DESIGN_DIFFICULTY",
    "DEGRADED",
    "BOTH_DOWN",
    "CODEX_STATE",
    "CURSOR_STATE",
    "DEGRADED_PROMPT_REQUIRED",
    "DEGRADED_HARD_FAIL",
    "BOOTSTRAP_NEXT",
    "ROUTE",
    "CHECKPOINT_NEXT",
    "REBASE_RC",
    "REBASE_OUTCOME",
    "CONFLICT_FILES",
    "REBASE_ERROR",
    "SKIPPED_ALREADY_PUSHED",
    "SKIPPED_ALREADY_FRESH",
];

/// Parse a bootstrap stdout envelope and render safe shell assignments.
pub fn parse_routing(arguments: &[OsString]) -> ExitCode {
    if is_help(arguments) {
        print_parse_routing_usage();
        return ExitCode::SUCCESS;
    }
    let options = match parse_routing_arguments(arguments) {
        Ok(options) => options,
        Err(message) => {
            eprintln!("bootstrap parse-routing: {message}");
            return ExitCode::from(1);
        }
    };
    let stdout = match read_text_lossy(&options.stdout_file) {
        Ok(text) => text,
        Err(error) => {
            eprintln!("bootstrap parse-routing: {error}");
            return ExitCode::from(1);
        }
    };
    let stdout_data = parse_routing_envelope(&stdout);
    let tmpdir = if options.tmpdir.is_empty() {
        stdout_data
            .get("IMPLEMENT_TMPDIR")
            .cloned()
            .unwrap_or_default()
    } else {
        options.tmpdir.clone()
    };
    let mut merged = BTreeMap::new();
    if !tmpdir.is_empty() {
        let routing = Path::new(&tmpdir).join("bootstrap-routing.env");
        if fs::symlink_metadata(&routing)
            .is_ok_and(|metadata| metadata.is_file() && !metadata.file_type().is_symlink())
            && let Ok(text) = read_text_lossy(&routing)
        {
            merged.extend(parse_routing_envelope(&text));
        }
    }
    for (key, value) in stdout_data {
        if merged.get(&key).is_none_or(String::is_empty) {
            merged.insert(key, value);
        }
    }
    if options.resume {
        merged.remove("coder");
        merged.remove("coder_fallback");
    }
    let rendered = shell_assignments(&merged, options.resume);
    if let Some(output) = options.output {
        if let Err(error) = atomic_write_output(&output, &rendered) {
            eprintln!("bootstrap parse-routing: {error}");
            return ExitCode::from(1);
        }
    } else {
        print!("{rendered}");
    }
    ExitCode::SUCCESS
}

/// Resolve whether the caller is non-interactive, preserving the old order.
pub fn resolve_non_interactive(arguments: &[OsString]) -> ExitCode {
    if is_help(arguments) {
        print_resolve_non_interactive_usage();
        return ExitCode::SUCCESS;
    }
    let explicit = match parse_explicit(arguments) {
        Ok(value) => value,
        Err(message) => {
            eprintln!("bootstrap resolve-non-interactive: {message}");
            return ExitCode::from(2);
        }
    };
    println!(
        "{}",
        if non_interactive(&explicit) {
            "true"
        } else {
            "false"
        }
    );
    ExitCode::SUCCESS
}

/// Create or restore the Step 0 session, then complete its Rust-owned
/// tracking, plan, coder-selection, and routing phases.
pub fn invoke(arguments: &[OsString]) -> ExitCode {
    if is_help(arguments) {
        print_invoke_usage();
        return ExitCode::SUCCESS;
    }
    let mut options = match BootstrapOptions::parse(arguments) {
        Ok(options) => options,
        Err(message) => {
            eprintln!("bootstrap invoke: {message}");
            return ExitCode::from(1);
        }
    };
    if options.resume()
        && env::var_os("IMPLEMENT_TMPDIR").is_none_or(|value| value.is_empty())
        && resolve_resume_tmpdir().is_none()
    {
        eprintln!("bootstrap invoke: --mode resume requires exported IMPLEMENT_TMPDIR");
        return ExitCode::from(1);
    }
    let state = match run_infrastructure(&options) {
        Ok(state) => state,
        Err(failure) => return emit_infrastructure_failure(&failure),
    };
    options.resolve_continuation_defaults(&state.implement_tmpdir);
    crate::implement_bootstrap_continuation::run(state, &options)
}

const BOOL_VALUES: &[&str] = &["", "true", "false"];
const CODER_VALUES: &[&str] = &["", "claude", "codex", "cursor"];
const DIFFICULTY_VALUES: &[&str] = &["", "TRIVIAL", "MODERATE", "HARD"];

#[derive(Clone, Debug)]
pub struct BootstrapOptions {
    pub(crate) mode: InvokeMode,
    pub(crate) issue_number: String,
    pub(crate) forked_target: String,
    pub(crate) merge_requested: String,
    pub(crate) draft_requested: String,
    pub(crate) no_admin_fallback: String,
    pub(crate) no_logs_commit: String,
    pub(crate) force_requested: String,
    pub(crate) difficulty_override: String,
    pub(crate) upstream_repo: String,
    pub(crate) run_id: String,
    pub(crate) preflight_tmpdir: String,
    pub(crate) caller_env: String,
    pub(crate) coder_opt: String,
    pub(crate) non_interactive: String,
    pub(crate) self_review_requested: String,
    pub(crate) self_implement_requested: String,
    pub(crate) skip_codex_probe: bool,
    pub(crate) skip_cursor_probe: bool,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum InvokeMode {
    Initial,
    Resume,
}

impl BootstrapOptions {
    #[allow(clippy::too_many_lines)] // Parsing preserves the public bootstrap argv contract.
    fn parse(arguments: &[OsString]) -> Result<Self, String> {
        let mut values = BTreeMap::new();
        let known = [
            "--mode",
            "--issue-number",
            "--forked-target",
            "--merge-requested",
            "--draft-requested",
            "--no-admin-fallback",
            "--no-logs-commit",
            "--upstream-repo",
            "--run-id",
            "--coder",
            "--preflight-tmpdir",
            "--caller-env",
            "--force-requested",
            "--self-review-requested",
            "--self-implement-requested",
            "--non-interactive",
            "--difficulty",
        ];
        let mut index = 0;
        while index < arguments.len() {
            let flag = arguments[index].to_string_lossy().into_owned();
            if !known.contains(&flag.as_str()) {
                return Err(format!("unrecognized arguments: {flag}"));
            }
            index += 1;
            let Some(value) = arguments.get(index) else {
                return Err(format!("argument {flag}: expected one argument"));
            };
            values.insert(flag, value.to_string_lossy().into_owned());
            index += 1;
        }
        let mode = match value(&values, "--mode", "").as_str() {
            "initial" => InvokeMode::Initial,
            "resume" => InvokeMode::Resume,
            _ => return Err("the following arguments are required: --mode".to_owned()),
        };
        for flag in [
            "--forked-target",
            "--merge-requested",
            "--draft-requested",
            "--no-admin-fallback",
            "--no-logs-commit",
            "--force-requested",
            "--self-review-requested",
            "--self-implement-requested",
            "--non-interactive",
        ] {
            let supplied = value(&values, flag, "");
            if !BOOL_VALUES.contains(&supplied.as_str()) {
                return Err(format!("argument {flag}: invalid choice"));
            }
        }
        if !CODER_VALUES.contains(&value(&values, "--coder", "").as_str()) {
            return Err("argument --coder: invalid choice".to_owned());
        }
        if !DIFFICULTY_VALUES.contains(&value(&values, "--difficulty", "").as_str()) {
            return Err("argument --difficulty: invalid choice".to_owned());
        }
        let environment = |key: &str| env::var(key).unwrap_or_default();
        let forked_target = bool_or_default(&first_nonempty(&[
            value(&values, "--forked-target", ""),
            environment("forked_target"),
            environment("FORKED_TARGET"),
        ]));
        let self_review_requested = bool_or_default(&first_nonempty(&[
            value(&values, "--self-review-requested", ""),
            bool_environment("self_review"),
        ]));
        let self_implement_requested = bool_or_default(&first_nonempty(&[
            value(&values, "--self-implement-requested", ""),
            bool_environment("self_implement"),
        ]));
        Ok(Self {
            mode,
            issue_number: first_nonempty(&[
                value(&values, "--issue-number", ""),
                environment("TARGET_ISSUE_NUMBER"),
                environment("ISSUE_NUMBER"),
            ]),
            forked_target,
            merge_requested: first_nonempty(&[
                value(&values, "--merge-requested", ""),
                bool_environment("merge"),
                bool_environment("MERGE"),
            ]),
            draft_requested: first_nonempty(&[
                value(&values, "--draft-requested", ""),
                bool_environment("draft"),
                bool_environment("DRAFT"),
            ]),
            no_admin_fallback: first_nonempty(&[
                value(&values, "--no-admin-fallback", ""),
                bool_environment("no_admin_fallback"),
                bool_environment("NO_ADMIN_FALLBACK"),
            ]),
            no_logs_commit: first_nonempty(&[
                value(&values, "--no-logs-commit", ""),
                bool_environment("no_logs_commit"),
                bool_environment("NO_LOGS_COMMIT"),
            ]),
            force_requested: bool_or_default(&first_nonempty(&[
                value(&values, "--force-requested", ""),
                bool_environment("force_requested"),
            ])),
            difficulty_override: first_nonempty(&[
                value(&values, "--difficulty", ""),
                environment("difficulty"),
                environment("DIFFICULTY_OVERRIDE"),
            ]),
            upstream_repo: first_nonempty(&[
                value(&values, "--upstream-repo", ""),
                environment("UPSTREAM_REPO"),
            ]),
            run_id: first_nonempty(&[value(&values, "--run-id", ""), environment("RUN_ID")]),
            preflight_tmpdir: first_nonempty(&[
                value(&values, "--preflight-tmpdir", ""),
                environment("PREFLIGHT_TMPDIR"),
            ]),
            caller_env: first_nonempty(&[
                value(&values, "--caller-env", ""),
                environment("CALLER_ENV_PATH"),
                environment("SESSION_ENV_PATH"),
            ]),
            coder_opt: if mode == InvokeMode::Resume {
                String::new()
            } else {
                first_nonempty(&[value(&values, "--coder", ""), environment("coder")])
            },
            non_interactive: first_nonempty(&[
                value(&values, "--non-interactive", ""),
                bool_environment("non_interactive"),
            ]),
            self_review_requested,
            self_implement_requested,
            skip_codex_probe: false,
            skip_cursor_probe: false,
        })
    }

    pub(crate) fn resume(&self) -> bool {
        self.mode == InvokeMode::Resume
    }

    pub(crate) fn self_subagents_only(&self) -> bool {
        self.self_review_requested == "true" && self.self_implement_requested == "true"
    }

    fn resolve_continuation_defaults(&mut self, tmpdir: &str) {
        let seed = Path::new(tmpdir).join("ship-seed-input.env");
        let resume = self.resume();
        let seed_value = |key: &str| {
            if resume {
                read_env_file(&seed, key)
            } else {
                String::new()
            }
        };
        self.merge_requested = bool_or_default(&first_nonempty(&[
            self.merge_requested.clone(),
            seed_value("MERGE"),
        ]));
        self.draft_requested = bool_or_default(&first_nonempty(&[
            self.draft_requested.clone(),
            seed_value("DRAFT"),
        ]));
        self.no_admin_fallback = bool_or_default(&first_nonempty(&[
            self.no_admin_fallback.clone(),
            seed_value("NO_ADMIN_FALLBACK"),
        ]));
        self.no_logs_commit = bool_or_default(&first_nonempty(&[
            self.no_logs_commit.clone(),
            seed_value("NO_LOGS_COMMIT"),
        ]));
        if !DIFFICULTY_VALUES.contains(&self.difficulty_override.as_str()) {
            self.difficulty_override.clear();
        }
        if !CODER_VALUES.contains(&self.coder_opt.as_str()) {
            self.coder_opt.clear();
        }
        self.non_interactive = if BOOL_VALUES.contains(&self.non_interactive.as_str()) {
            self.non_interactive.clone()
        } else {
            String::new()
        };
    }
}

#[derive(Clone, Debug, Default)]
pub struct BootstrapState {
    pub(crate) current_branch: String,
    pub(crate) is_main: String,
    pub(crate) is_user_branch: String,
    pub(crate) user_prefix: String,
    pub(crate) entry_gate: String,
    pub(crate) skip_branch_check: String,
    pub(crate) implement_tmpdir: String,
    pub(crate) session_id: String,
    pub(crate) repo: String,
    pub(crate) repo_unavailable: String,
    pub(crate) codex_present: String,
    pub(crate) cursor_present: String,
    pub(crate) claude_binary_found: String,
    pub(crate) codex_binary_found: String,
    pub(crate) cursor_binary_found: String,
    pub(crate) codex_available: String,
    pub(crate) cursor_available: String,
    pub(crate) run_id: String,
    pub(crate) issue_number_resolved: String,
    pub(crate) branch_selected: String,
    pub(crate) deferred: String,
    pub(crate) stall_tracking: String,
    pub(crate) branch_name: String,
    pub(crate) branch_action: String,
    pub(crate) plan_file: String,
    pub(crate) coder: String,
    pub(crate) coder_fallback: String,
    pub(crate) implement_bail_reason: String,
}

#[derive(Clone, Debug)]
struct InfrastructureFailure {
    step: &'static str,
    implement_tmpdir: String,
    message: String,
}

impl InfrastructureFailure {
    fn new(step: &'static str, implement_tmpdir: &str, message: impl Into<String>) -> Self {
        Self {
            step,
            implement_tmpdir: implement_tmpdir.to_owned(),
            message: message.into(),
        }
    }
}

fn run_infrastructure(options: &BootstrapOptions) -> Result<BootstrapState, InfrastructureFailure> {
    let _ignored = progress_commands::clear(&[]);
    let branch = crate::pr_commands::branch_state();
    let GateDecision {
        entry_gate,
        skip_branch_check,
    } = entry_gate(
        "implement",
        &branch.is_main,
        &branch.is_user_branch,
        &branch.user_prefix,
        None,
    )
    .map_err(|message| InfrastructureFailure::new("session-entry-gate", "", message))?;
    let mut state = BootstrapState {
        current_branch: branch.current_branch,
        is_main: branch.is_main,
        is_user_branch: branch.is_user_branch,
        user_prefix: branch.user_prefix,
        entry_gate: entry_gate.to_owned(),
        skip_branch_check: skip_branch_check.to_owned(),
        ..BootstrapState::default()
    };

    let ambient_tmpdir = if options.resume() {
        resolve_resume_tmpdir().unwrap_or_default()
    } else {
        String::new()
    };
    if options.resume() && !ambient_tmpdir.is_empty() && trusted_session_env(&ambient_tmpdir) {
        restore_session_state(&mut state, options, &ambient_tmpdir);
        restore_resume_progress(&state);
        ensure_plugin_root_env(&state).map_err(|message| {
            InfrastructureFailure::new("write-session-env", &state.implement_tmpdir, message)
        })?;
    } else {
        setup_new_session(&mut state, options)?;
        materialize_preflight_sidecars(&state, options);
        state.run_id = resolved_run_id(options, &state);
        activate_progress(&state);
        write_claude_source_snapshot(&state);
        write_base_session_env(&state, options).map_err(|message| {
            InfrastructureFailure::new("write-session-env", &state.implement_tmpdir, message)
        })?;
        let _ignored = crate::timing_commands::telemetry_mark(&[
            OsString::from("--implement-tmpdir"),
            OsString::from(&state.implement_tmpdir),
            OsString::from("--label"),
            OsString::from("Step 0 — preflight"),
        ]);
        refresh_reviewer_state(&mut state, options).map_err(|message| {
            InfrastructureFailure::new("reviewer-refresh", &state.implement_tmpdir, message)
        })?;
    }
    let root = plugin_root().map_err(|message| {
        InfrastructureFailure::new("write-session-env", &state.implement_tmpdir, message)
    })?;
    let cwd = env::current_dir().map_err(|error| {
        InfrastructureFailure::new("statusline", &state.implement_tmpdir, error.to_string())
    })?;
    let _ignored = run_verified_larch(&[
        OsString::from("progress"),
        OsString::from("install-statusline"),
        OsString::from("--plugin-root"),
        root.into_os_string(),
        OsString::from("--repo-root"),
        cwd.into_os_string(),
        OsString::from("--notice"),
    ]);
    write_larch_run_sh(&state.implement_tmpdir).map_err(|message| {
        InfrastructureFailure::new("larch-run", &state.implement_tmpdir, message)
    })?;
    write_implement_pointer(&state).map_err(|message| {
        InfrastructureFailure::new("write-implement-env", &state.implement_tmpdir, message)
    })?;
    state.codex_available = bool_from_binary(&state.codex_binary_found);
    state.cursor_available = bool_from_binary(&state.cursor_binary_found);
    eprintln!(
        "→ step0: infra ready (tmpdir={} session={})",
        state.implement_tmpdir, state.session_id
    );
    Ok(state)
}

trait EmptyFallback {
    fn if_empty(self, fallback: &str) -> String;
}

impl EmptyFallback for String {
    fn if_empty(self, fallback: &str) -> String {
        if self.is_empty() {
            fallback.to_owned()
        } else {
            self
        }
    }
}

fn setup_new_session(
    state: &mut BootstrapState,
    options: &BootstrapOptions,
) -> Result<(), InfrastructureFailure> {
    let mut arguments = vec![
        OsString::from("session"),
        OsString::from("setup"),
        OsString::from("--prefix"),
        OsString::from("claude-implement"),
    ];
    if state.skip_branch_check == "true" {
        arguments.push(OsString::from("--skip-branch-check"));
    }
    if options.skip_codex_probe || options.self_subagents_only() {
        arguments.push(OsString::from("--skip-codex-probe"));
    }
    if options.skip_cursor_probe || options.self_subagents_only() {
        arguments.push(OsString::from("--skip-cursor-probe"));
    }
    if !options.caller_env.is_empty() {
        arguments.extend([
            OsString::from("--caller-env"),
            OsString::from(&options.caller_env),
        ]);
    }
    let output = run_verified_larch(&arguments)
        .map_err(|message| InfrastructureFailure::new("session-setup", "", message))?;
    if !output.status().success() {
        return Err(InfrastructureFailure::new(
            "session-setup",
            "",
            String::from_utf8_lossy(output.stderr()).trim().to_owned(),
        ));
    }
    let fields = parse_kv(&String::from_utf8_lossy(output.stdout()));
    state.implement_tmpdir = value(&fields, "SESSION_TMPDIR", "");
    state.session_id = value(&fields, "SESSION_ID", "");
    if state.implement_tmpdir.is_empty()
        || state.session_id.is_empty()
        || !trusted_session_directory(&state.implement_tmpdir)
    {
        return Err(InfrastructureFailure::new(
            "session-setup",
            &state.implement_tmpdir,
            "session setup did not publish a usable session directory",
        ));
    }
    state.repo = value(&fields, "REPO", "");
    state.repo_unavailable = value(&fields, "REPO_UNAVAILABLE", "false");
    state.codex_present = value(&fields, "CODEX_PRESENT", "");
    state.cursor_present = value(&fields, "CURSOR_PRESENT", "");
    state.claude_binary_found = value(&fields, "CLAUDE_BINARY_FOUND", "");
    state.codex_binary_found = value(&fields, "CODEX_BINARY_FOUND", "");
    state.cursor_binary_found = value(&fields, "CURSOR_BINARY_FOUND", "");
    Ok(())
}

fn restore_session_state(state: &mut BootstrapState, options: &BootstrapOptions, tmpdir: &str) {
    tmpdir.clone_into(&mut state.implement_tmpdir);
    read_session_value(tmpdir, "session-id")
        .trim()
        .clone_into(&mut state.session_id);
    state.repo = read_session_env(tmpdir, "REPO");
    state.repo_unavailable = read_session_env(tmpdir, "REPO_UNAVAILABLE").if_empty("false");
    state.codex_present = read_session_env(tmpdir, "CODEX_PRESENT");
    state.cursor_present = read_session_env(tmpdir, "CURSOR_PRESENT");
    state.claude_binary_found = read_session_env(tmpdir, "CLAUDE_BINARY_FOUND");
    state.codex_binary_found = read_session_env(tmpdir, "CODEX_BINARY_FOUND");
    state.cursor_binary_found = read_session_env(tmpdir, "CURSOR_BINARY_FOUND");
    state.run_id = first_nonempty(&[
        read_session_env(tmpdir, "LARCH_RUN_ID"),
        resolved_run_id(options, state),
    ]);
}

fn resolved_run_id(options: &BootstrapOptions, state: &BootstrapState) -> String {
    for candidate in [&options.run_id, &state.run_id, &state.session_id] {
        if valid_run_id(candidate) {
            return candidate.to_owned();
        }
    }
    let session_id = read_session_value(&state.implement_tmpdir, "session-id");
    if valid_run_id(&session_id) {
        session_id
    } else {
        String::new()
    }
}

fn activatable_run_id(value: &str) -> bool {
    validate_progress_run_id(value).is_some()
}

fn activate_progress(state: &BootstrapState) {
    if !activatable_run_id(&state.run_id) {
        return;
    }
    let Ok(cwd) = env::current_dir() else {
        return;
    };
    let _ignored = progress_commands::activate(&[
        OsString::from("--repo-root"),
        cwd.into_os_string(),
        OsString::from("--run-id"),
        OsString::from(&state.run_id),
    ]);
}

fn restore_resume_progress(state: &BootstrapState) {
    activate_progress(state);
}

fn materialize_preflight_sidecars(state: &BootstrapState, options: &BootstrapOptions) {
    if options.preflight_tmpdir.is_empty() || state.implement_tmpdir.is_empty() {
        return;
    }
    let _ignored = write_session_text(
        &state.implement_tmpdir,
        "preflight-tmpdir.env",
        &format!("PREFLIGHT_TMPDIR={}\n", options.preflight_tmpdir),
        0o600,
    );
    let source = Path::new(&options.preflight_tmpdir).join("main-health.env");
    let Ok(metadata) = fs::symlink_metadata(&source) else {
        return;
    };
    if metadata.file_type().is_symlink() || !metadata.is_file() {
        return;
    }
    let Ok(text) = read_text_lossy(&source) else {
        return;
    };
    let _ignored = write_session_text(&state.implement_tmpdir, "main-health.env", &text, 0o600);
}

fn write_claude_source_snapshot(state: &BootstrapState) {
    let target = Path::new(&state.implement_tmpdir).join("claude-source.env");
    if fs::symlink_metadata(&target).is_ok_and(|metadata| {
        metadata.is_file() && !metadata.file_type().is_symlink() && metadata.len() > 0
    }) {
        return;
    }
    let Ok(source) = crate::token_commands::resolve_claude_source(None) else {
        return;
    };
    let text = format!(
        "TRANSCRIPT_PATH={}\nSESSION_DIR={}\nSESSION_UUID={}\n",
        source.transcript.display(),
        source
            .session_dir
            .as_deref()
            .map(|dir| dir.display().to_string())
            .unwrap_or_default(),
        source.session_uuid,
    );
    let _ignored = write_session_text(&state.implement_tmpdir, "claude-source.env", &text, 0o600);
}

pub fn write_base_session_env(
    state: &BootstrapState,
    options: &BootstrapOptions,
) -> Result<(), String> {
    let root = plugin_root()?;
    let tmpdir = Path::new(&state.implement_tmpdir);
    let session_env = tmpdir.join("session-env.sh");
    let prior_repo_root = read_session_env(&state.implement_tmpdir, "REPO_ROOT");
    let repo_root = if !prior_repo_root.is_empty()
        && validate_repo_root_value(&prior_repo_root, "REPO_ROOT").is_ok()
    {
        prior_repo_root
    } else {
        resolve_repo_root()
    };
    let prior_claude_source = read_session_env(&state.implement_tmpdir, "LARCH_CLAUDE_SOURCE_FILE");
    let claude_source = if prior_claude_source.is_empty() {
        let source = tmpdir.join("claude-source.env");
        if source.is_file() && !source.is_symlink() {
            source.display().to_string()
        } else {
            String::new()
        }
    } else {
        prior_claude_source
    };
    let mut arguments = vec![
        OsString::from("--output"),
        session_env.into_os_string(),
        OsString::from("--repo"),
        OsString::from(&state.repo),
        OsString::from("--repo-root"),
        OsString::from(repo_root),
        OsString::from("--repo-unavailable"),
        OsString::from(if state.repo_unavailable.is_empty() {
            "false"
        } else {
            &state.repo_unavailable
        }),
        OsString::from("--codex-present"),
        OsString::from(&state.codex_present),
        OsString::from("--cursor-present"),
        OsString::from(&state.cursor_present),
        OsString::from("--claude-binary-found"),
        OsString::from(&state.claude_binary_found),
        OsString::from("--codex-binary-found"),
        OsString::from(&state.codex_binary_found),
        OsString::from("--cursor-binary-found"),
        OsString::from(&state.cursor_binary_found),
        OsString::from("--timing-ledger"),
        tmpdir.join("timing-ledger.tsv").into_os_string(),
        OsString::from("--token-session-id"),
        OsString::from(&state.session_id),
        OsString::from("--claude-source-file"),
        OsString::from(claude_source),
        OsString::from("--prev-implement-tmpdir"),
        OsString::from(&state.implement_tmpdir),
        OsString::from("--auto-mode"),
        OsString::from(read_session_env(&state.implement_tmpdir, "LARCH_AUTO_MODE")),
        OsString::from("--dynamic-archetypes"),
        OsString::from(valid_dynamic_archetypes(&read_session_env(
            &state.implement_tmpdir,
            "LARCH_DYNAMIC_ARCHETYPES_MAX",
        ))),
        OsString::from("--run-id"),
        OsString::from(if valid_run_id(&state.run_id) {
            &state.run_id
        } else {
            ""
        }),
        OsString::from("--forked-target"),
        OsString::from(&options.forked_target),
        OsString::from("--live-mutation-ok"),
        OsString::from("true"),
    ];
    session_env_commands::write_env_for_setup(&arguments)?;
    arguments.clear();
    arguments.extend([
        OsString::from("--output"),
        tmpdir.join("plugin-root.env").into_os_string(),
        OsString::from("--plugin-root-only"),
        OsString::from("--value"),
        root.into_os_string(),
    ]);
    session_env_commands::write_env_for_setup(&arguments)
}

fn ensure_plugin_root_env(state: &BootstrapState) -> Result<(), String> {
    let path = Path::new(&state.implement_tmpdir).join("plugin-root.env");
    if path.is_file() && !path.is_symlink() {
        return Ok(());
    }
    let root = plugin_root()?;
    session_env_commands::write_env_for_setup(&[
        OsString::from("--output"),
        path.into_os_string(),
        OsString::from("--plugin-root-only"),
        OsString::from("--value"),
        root.into_os_string(),
    ])
}

fn refresh_reviewer_state(
    state: &mut BootstrapState,
    options: &BootstrapOptions,
) -> Result<(), String> {
    if options.self_subagents_only() {
        return Ok(());
    }
    let result = agent_commands::check_reviewers_with_environment(
        options.skip_codex_probe,
        options.skip_cursor_probe,
        &BTreeMap::new(),
    )?;
    let values = parse_kv(&result.kv_lines().join("\n"));
    state.codex_present = value(&values, "CODEX_PRESENT", &state.codex_present);
    state.cursor_present = value(&values, "CURSOR_PRESENT", &state.cursor_present);
    state.codex_binary_found = value(&values, "CODEX_BINARY_FOUND", &state.codex_binary_found);
    state.cursor_binary_found = value(&values, "CURSOR_BINARY_FOUND", &state.cursor_binary_found);
    write_base_session_env(state, options)
}

fn write_larch_run_sh(tmpdir: &str) -> Result<(), String> {
    let script = r#"#!/usr/bin/env bash
set -uo pipefail

IMPLEMENT_TMPDIR="${IMPLEMENT_TMPDIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)}"
export IMPLEMENT_TMPDIR

[ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -f "$IMPLEMENT_TMPDIR/plugin-root.env" ] && . "$IMPLEMENT_TMPDIR/plugin-root.env"
[ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ] && CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
export CLAUDE_PLUGIN_ROOT

[ -n "${CLAUDE_PLUGIN_ROOT:-}" ] || { printf '%s\n' 'larch-run.sh: CLAUDE_PLUGIN_ROOT could not be resolved' >&2; exit 2; }
[ "${1:-}" = "--print-plugin-root" ] && { printf '%s\n' "$CLAUDE_PLUGIN_ROOT"; exit 0; }
[ "$#" -ge 1 ] || { printf '%s\n' 'larch-run.sh: missing relative script path' >&2; exit 2; }

script=$1
shift
case "$script" in
  /*|*..*) printf '%s\n' "larch-run.sh: invalid relative script path: $script" >&2; exit 2 ;;
esac

_larch_cleanup_active_leg() {
  "$CLAUDE_PLUGIN_ROOT/scripts/larch.sh" implement kill-active-leg --owner-token "$_larch_active_leg_owner_token" --implement-tmpdir "$IMPLEMENT_TMPDIR" || true
}

case "$script" in
  *.py)
    _larch_active_leg_owner_token="$(python3 -c 'import uuid; print(uuid.uuid4().hex)' 2>/dev/null || printf '%s.%s.%s\n' "$$" "$(date +%s)" "${RANDOM:-0}")"
    export LARCH_ACTIVE_LEG_OWNER_TOKEN="$_larch_active_leg_owner_token"
    trap _larch_cleanup_active_leg EXIT INT TERM
    python3 "$CLAUDE_PLUGIN_ROOT/$script" "$@"
    rc=$?
    _larch_cleanup_active_leg
    trap - EXIT INT TERM
    exit "$rc"
    ;;
  *.sh) exec "$CLAUDE_PLUGIN_ROOT/$script" "$@" ;;
  *) printf '%s\n' "larch-run.sh: unsupported script target: $script" >&2; exit 2 ;;
esac
"#;
    write_session_text(tmpdir, "larch-run.sh", script, 0o755)
}

fn write_implement_pointer(state: &BootstrapState) -> Result<(), String> {
    let pid = env::var("LARCH_CLAUDE_PID").unwrap_or_default();
    if pid.is_empty() {
        return Err("LARCH_CLAUDE_PID is required".to_owned());
    }
    let cwd = env::current_dir().map_err(|error| error.to_string())?;
    let exit = session_env_commands::write_implement_env(&[
        OsString::from("--claude-pid"),
        OsString::from(pid),
        OsString::from("--implement-tmpdir"),
        OsString::from(&state.implement_tmpdir),
        OsString::from("--cwd"),
        cwd.into_os_string(),
    ]);
    if exit == ExitCode::SUCCESS {
        Ok(())
    } else {
        Err("could not write implement session pointer".to_owned())
    }
}

fn trusted_session_env(tmpdir: &str) -> bool {
    if !trusted_session_directory(tmpdir) {
        return false;
    }
    let path = Path::new(tmpdir).join("session-env.sh");
    fs::symlink_metadata(path)
        .is_ok_and(|metadata| metadata.is_file() && !metadata.file_type().is_symlink())
}

fn trusted_session_directory(tmpdir: &str) -> bool {
    let path = Path::new(tmpdir);
    path.is_absolute()
        && fs::symlink_metadata(path)
            .is_ok_and(|metadata| metadata.is_dir() && !metadata.file_type().is_symlink())
}

fn resolve_resume_tmpdir() -> Option<String> {
    let direct = env::var("IMPLEMENT_TMPDIR").unwrap_or_default();
    if !direct.is_empty() {
        return Some(direct);
    }
    let pid = env::var("LARCH_CLAUDE_PID").unwrap_or_default();
    if !valid_claude_pid(&pid) {
        return None;
    }
    let home = env::var_os("HOME")?;
    let pointer = PathBuf::from(home)
        .join(".cache/larch/sessions")
        .join(format!("current-implement-env-{pid}.sh"));
    let value = read_env_file(&pointer, "IMPLEMENT_TMPDIR");
    (!value.is_empty()).then_some(value)
}

fn valid_claude_pid(value: &str) -> bool {
    !value.is_empty()
        && value.len() <= 7
        && value
            .bytes()
            .enumerate()
            .all(|(index, byte)| byte.is_ascii_digit() && (index != 0 || byte != b'0'))
}

fn read_session_env(tmpdir: &str, key: &str) -> String {
    read_env_file(&Path::new(tmpdir).join("session-env.sh"), key)
}

fn read_session_value(tmpdir: &str, name: &str) -> String {
    let path = Path::new(tmpdir).join(name);
    fs::symlink_metadata(&path)
        .ok()
        .filter(|metadata| metadata.is_file() && !metadata.file_type().is_symlink())
        .and_then(|_| read_text_lossy(&path).ok())
        .unwrap_or_default()
}

fn read_env_file(path: &Path, key: &str) -> String {
    fs::symlink_metadata(path)
        .ok()
        .filter(|metadata| metadata.is_file() && !metadata.file_type().is_symlink())
        .and_then(|_| read_text_lossy(path).ok())
        // The retired `_read_key` used the first matching row.  Keep that
        // precedence for trusted session state and PID-keyed resume pointers.
        .map(|text| first_kv_value(&text, key))
        .unwrap_or_default()
}

fn first_kv_value(text: &str, expected: &str) -> String {
    let Ok(document) = KvDocument::parse(text, bootstrap_kv_options()) else {
        return String::new();
    };
    document
        .rows()
        .iter()
        .find(|row| row.key() == expected)
        .map(|row| row.value().to_owned())
        .unwrap_or_default()
}

fn read_text_lossy(path: &Path) -> Result<String, std::io::Error> {
    fs::read(path).map(|bytes| String::from_utf8_lossy(&bytes).into_owned())
}

fn parse_kv(text: &str) -> BTreeMap<String, String> {
    KvDocument::parse(text, bootstrap_kv_options()).map_or_else(
        |_| BTreeMap::new(),
        |document| {
            document
                .select(DuplicatePolicy::Last)
                .into_iter()
                .filter(|(key, _)| valid_key(key))
                .collect()
        },
    )
}

const fn bootstrap_kv_options() -> ParseOptions {
    let mut options = ParseOptions::legacy();
    options.cr_strip = CrStrip::Suffix;
    options
}

fn first_nonempty(values: &[String]) -> String {
    values
        .iter()
        .find(|value| !value.is_empty())
        .cloned()
        .unwrap_or_default()
}

fn value(values: &BTreeMap<String, String>, key: &str, fallback: &str) -> String {
    values
        .get(key)
        .cloned()
        .unwrap_or_else(|| fallback.to_owned())
}

fn bool_environment(key: &str) -> String {
    let value = env::var(key).unwrap_or_default();
    if BOOL_VALUES.contains(&value.as_str()) {
        value
    } else {
        String::new()
    }
}

fn bool_or_default(value: &str) -> String {
    if value == "true" {
        "true".to_owned()
    } else {
        "false".to_owned()
    }
}

fn bool_from_binary(value: &str) -> String {
    if value == "true" {
        "true".to_owned()
    } else {
        "false".to_owned()
    }
}

fn valid_dynamic_archetypes(value: &str) -> String {
    if matches!(value, "0" | "1") {
        value.to_owned()
    } else {
        String::new()
    }
}

fn resolve_repo_root() -> String {
    first_nonempty(&[
        env::var("CLAUDE_PROJECT_DIR").unwrap_or_default(),
        env::var("REPO_ROOT").unwrap_or_default(),
        env::current_dir()
            .map(|path| path.display().to_string())
            .unwrap_or_default(),
    ])
}

fn emit_infrastructure_failure(failure: &InfrastructureFailure) -> ExitCode {
    if !failure.implement_tmpdir.is_empty() {
        println!("IMPLEMENT_TMPDIR={}", failure.implement_tmpdir);
    }
    println!("STEP_FAILED={}", failure.step);
    if !failure.message.trim().is_empty() {
        eprintln!("bootstrap invoke: {}", failure.message.trim());
    }
    ExitCode::from(2)
}

#[derive(Debug)]
struct ParseRoutingOptions {
    stdout_file: PathBuf,
    tmpdir: String,
    resume: bool,
    output: Option<PathBuf>,
}

fn parse_routing_arguments(arguments: &[OsString]) -> Result<ParseRoutingOptions, String> {
    let mut stdout_file = None;
    let mut tmpdir = String::new();
    let mut resume = false;
    let mut output = None;
    let mut index = 0;
    while index < arguments.len() {
        let token = arguments[index].to_string_lossy();
        let value = |index: &mut usize| -> Result<String, String> {
            *index += 1;
            arguments
                .get(*index)
                .map(|value| value.to_string_lossy().into_owned())
                .ok_or_else(|| format!("argument {token}: expected one argument"))
        };
        match token.as_ref() {
            "--stdout-file" => stdout_file = Some(PathBuf::from(value(&mut index)?)),
            "--tmpdir" => tmpdir = value(&mut index)?,
            "--resume" => match value(&mut index)?.as_str() {
                "true" => resume = true,
                "false" => {}
                _ => return Err("argument --resume: invalid choice".to_owned()),
            },
            "--output" => output = Some(PathBuf::from(value(&mut index)?)),
            _ => return Err(format!("unrecognized arguments: {token}")),
        }
        index += 1;
    }
    Ok(ParseRoutingOptions {
        stdout_file: stdout_file
            .ok_or_else(|| "the following arguments are required: --stdout-file".to_owned())?,
        tmpdir,
        resume,
        output,
    })
}

fn parse_routing_envelope(text: &str) -> BTreeMap<String, String> {
    KvDocument::parse(text, bootstrap_kv_options()).map_or_else(
        |_| BTreeMap::new(),
        |document| {
            document
                .select(DuplicatePolicy::Last)
                .into_iter()
                .filter(|(key, _)| ROUTING_KEYS.contains(&key.as_str()) && valid_key(key))
                .collect()
        },
    )
}

fn valid_key(key: &str) -> bool {
    !key.is_empty()
        && key
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || byte == b'_')
}

fn shell_assignments(data: &BTreeMap<String, String>, preserve_coder: bool) -> String {
    let mut text = String::new();
    for key in ROUTING_KEYS {
        if preserve_coder && matches!(*key, "coder" | "coder_fallback") {
            continue;
        }
        if let Some(value) = data.get(*key).filter(|value| !value.is_empty()) {
            text.push_str(key);
            text.push('=');
            text.push_str(&shell_quote(value));
            text.push('\n');
            text.push_str("export ");
        } else {
            text.push_str("unset ");
        }
        text.push_str(key);
        text.push('\n');
    }
    text
}

fn atomic_write_output(output: &Path, text: &str) -> Result<(), String> {
    let target = if output.is_absolute() {
        output.to_path_buf()
    } else {
        env::current_dir()
            .map_err(|error| error.to_string())?
            .join(output)
    };
    let parent = target
        .parent()
        .ok_or_else(|| "--output has no parent directory".to_owned())?;
    let parent = fs::canonicalize(parent).map_err(|error| error.to_string())?;
    let root = TemporaryRoot::resolve(Some(&parent)).map_err(|error| error.to_string())?;
    let name = target
        .file_name()
        .ok_or_else(|| "--output has no filename".to_owned())?;
    let target = root.path().join(name);
    atomic_write_utf8_in(&root, &target, text, false, 0o600).map_err(|error| error.to_string())
}

fn parse_explicit(arguments: &[OsString]) -> Result<String, String> {
    if arguments.is_empty() {
        return Ok(String::new());
    }
    if arguments.len() != 2 || arguments.first().is_none_or(|value| value != "--explicit") {
        return Err("unrecognized arguments".to_owned());
    }
    let value = arguments[1].to_string_lossy().into_owned();
    if matches!(value.as_str(), "" | "true" | "false") {
        Ok(value)
    } else {
        Err("argument --explicit: invalid choice".to_owned())
    }
}

fn is_help(arguments: &[OsString]) -> bool {
    arguments
        .iter()
        .any(|argument| argument == "-h" || argument == "--help")
}

fn print_invoke_usage() {
    print!(
        "{}",
        concat!(
            "usage: bootstrap invoke [-h] --mode {initial,resume}\n",
            "                        [--issue-number ISSUE_NUMBER]\n",
            "                        [--forked-target {,true,false}]\n",
            "                        [--merge-requested {,true,false}]\n",
            "                        [--draft-requested {,true,false}]\n",
            "                        [--no-admin-fallback {,true,false}]\n",
            "                        [--no-logs-commit {,true,false}]\n",
            "                        [--upstream-repo UPSTREAM_REPO] [--run-id RUN_ID]\n",
            "                        [--coder {,claude,codex,cursor}]\n",
            "                        [--preflight-tmpdir PREFLIGHT_TMPDIR]\n",
            "                        [--caller-env CALLER_ENV]\n",
            "                        [--force-requested {,true,false}]\n",
            "                        [--self-review-requested {,true,false}]\n",
            "                        [--self-implement-requested {,true,false}]\n",
            "                        [--non-interactive {,true,false}]\n",
            "                        [--difficulty {,TRIVIAL,MODERATE,HARD}]\n\n",
            "options:\n",
            "  -h, --help            show this help message and exit\n",
            "  --mode {initial,resume}\n",
            "  --issue-number ISSUE_NUMBER\n",
            "  --forked-target {,true,false}\n",
            "  --merge-requested {,true,false}\n",
            "  --draft-requested {,true,false}\n",
            "  --no-admin-fallback {,true,false}\n",
            "  --no-logs-commit {,true,false}\n",
            "  --upstream-repo UPSTREAM_REPO\n",
            "  --run-id RUN_ID\n",
            "  --coder {,claude,codex,cursor}\n",
            "  --preflight-tmpdir PREFLIGHT_TMPDIR\n",
            "  --caller-env CALLER_ENV\n",
            "  --force-requested {,true,false}\n",
            "  --self-review-requested {,true,false}\n",
            "  --self-implement-requested {,true,false}\n",
            "  --non-interactive {,true,false}\n",
            "  --difficulty {,TRIVIAL,MODERATE,HARD}\n",
        )
    );
}

fn print_parse_routing_usage() {
    print!(
        "{}",
        concat!(
            "usage: bootstrap parse-routing [-h] --stdout-file STDOUT_FILE\n",
            "                               [--tmpdir TMPDIR] [--resume {true,false}]\n",
            "                               [--output OUTPUT]\n\n",
            "options:\n",
            "  -h, --help            show this help message and exit\n",
            "  --stdout-file STDOUT_FILE\n",
            "  --tmpdir TMPDIR\n",
            "  --resume {true,false}\n",
            "  --output OUTPUT\n",
        )
    );
}

fn print_resolve_non_interactive_usage() {
    print!(
        "{}",
        concat!(
            "usage: bootstrap resolve-non-interactive [-h] [--explicit {,true,false}]\n\n",
            "options:\n",
            "  -h, --help            show this help message and exit\n",
            "  --explicit {,true,false}\n",
        )
    );
}

fn non_interactive(explicit: &str) -> bool {
    if explicit == "true" {
        return true;
    }
    if explicit == "false" {
        return false;
    }
    for key in [
        "LARCH_SKILL_NON_INTERACTIVE",
        "LARCH_AUTONOMOUS_LOOP",
        "LARCH_EVAL_RUN",
        "LARCH_CRON",
    ] {
        if env::var(key).as_deref() == Ok("true") {
            return true;
        }
    }
    if matches!(
        env::var("CLAUDE_CODE_SUBAGENT").as_deref(),
        Ok("1" | "true" | "yes")
    ) {
        return true;
    }
    parent_invocation_non_interactive()
}

fn parent_invocation_non_interactive() -> bool {
    let process_field = |pid: u32, field: &str| {
        run_host_utility(
            HostUtilityProgram::Ps,
            [
                OsString::from("-o"),
                OsString::from(field),
                OsString::from("-p"),
                OsString::from(pid.to_string()),
            ],
            Duration::from_secs(3),
        )
        .ok()
        .filter(|output| output.status().success())
        .map(|output| String::from_utf8_lossy(output.stdout()).trim().to_owned())
    };
    // Python's `os.getppid()` starts inspection at the invoking process, not
    // at the command itself. Preserve the full eight-parent inspection depth.
    let Some(mut pid) =
        process_field(std::process::id(), "ppid=").and_then(|value| value.parse().ok())
    else {
        return false;
    };
    let mut visited = std::collections::BTreeSet::new();
    for _ in 0..8 {
        if pid <= 1 || !visited.insert(pid) {
            break;
        }
        if process_field(pid, "comm=")
            .is_some_and(|command| command.to_ascii_lowercase().contains("cron"))
        {
            return true;
        }
        if process_field(pid, "args=").is_some_and(|arguments| {
            let lower = arguments.to_ascii_lowercase();
            lower.contains("<<autonomous-loop")
                || (lower.split_whitespace().any(|word| word == "claude")
                    && (lower.split_whitespace().any(|word| word == "-p")
                        || lower.contains("--print")))
        }) {
            return true;
        }
        let Some(parent) = process_field(pid, "ppid=").and_then(|value| value.parse().ok()) else {
            break;
        };
        pid = parent;
    }
    false
}

#[cfg(test)]
mod tests {
    use super::{
        BootstrapOptions, activatable_run_id, first_kv_value, is_help, parse_routing,
        parse_routing_envelope, shell_assignments, valid_claude_pid, write_larch_run_sh,
    };
    #[cfg(unix)]
    use std::os::unix::fs::PermissionsExt;
    #[cfg(unix)]
    use std::process::Command;
    use std::{ffi::OsString, fs, process::ExitCode};

    #[test]
    fn routing_parser_drops_unknown_keys_and_shell_quotes_values() {
        let parsed =
            parse_routing_envelope("IMPLEMENT_TMPDIR=/tmp/a b\nUNKNOWN=no\ncoder=claude\n");
        let output = shell_assignments(&parsed, false);
        assert!(output.contains("IMPLEMENT_TMPDIR='/tmp/a b'"));
        assert!(output.contains("coder=claude"));
        assert!(!output.contains("UNKNOWN"));
    }

    #[test]
    fn routing_file_precedes_stdout_and_resume_omits_coder_exports() {
        let temporary = tempfile::tempdir().expect("temporary routing directory");
        let session = temporary.path().join("session");
        fs::create_dir(&session).expect("session directory");
        fs::write(
            session.join("bootstrap-routing.env"),
            "IMPLEMENT_TMPDIR=/saved\nBRANCH_NAME=saved-branch\ncoder=codex\n",
        )
        .expect("saved routing");
        let stdout = temporary.path().join("stdout.txt");
        fs::write(
            &stdout,
            format!(
                "IMPLEMENT_TMPDIR={}\nBRANCH_NAME=stdout-branch\nRUN_ID=R1\ncoder=cursor\n",
                session.display()
            ),
        )
        .expect("bootstrap stdout");
        let output = temporary.path().join("routing.env");
        let arguments = [
            "--stdout-file",
            stdout.to_str().expect("utf8 stdout path"),
            "--tmpdir",
            session.to_str().expect("utf8 session path"),
            "--resume",
            "true",
            "--output",
            output.to_str().expect("utf8 output path"),
        ]
        .into_iter()
        .map(OsString::from)
        .collect::<Vec<_>>();

        assert_eq!(parse_routing(&arguments), ExitCode::SUCCESS);
        let rendered = fs::read_to_string(output).expect("rendered routing");
        assert!(rendered.contains("IMPLEMENT_TMPDIR=/saved"));
        assert!(rendered.contains("BRANCH_NAME=saved-branch"));
        assert!(rendered.contains("RUN_ID=R1"));
        assert!(!rendered.contains("coder="));
        assert!(!rendered.contains("unset coder"));
    }

    #[test]
    fn bootstrap_options_preserve_cli_validation_and_progress_reservations() {
        let invalid = ["--mode", "initial", "--forked-target", "tru"]
            .into_iter()
            .map(OsString::from)
            .collect::<Vec<_>>();
        assert!(BootstrapOptions::parse(&invalid).is_err());
        assert!(activatable_run_id("run-1"));
        assert!(!activatable_run_id("current"));
        assert!(!activatable_run_id(".."));
        assert!(valid_claude_pid("1234567"));
        assert!(!valid_claude_pid("0123"));
        assert!(!valid_claude_pid("12345678"));
        assert_eq!(
            first_kv_value(
                "IMPLEMENT_TMPDIR=/first\nIMPLEMENT_TMPDIR=/second\n",
                "IMPLEMENT_TMPDIR"
            ),
            "/first"
        );
        assert!(is_help(&[
            OsString::from("--help"),
            OsString::from("ignored")
        ]));
    }

    #[test]
    fn session_launcher_keeps_active_leg_cleanup_contract() {
        let temporary = tempfile::tempdir().expect("temporary session directory");
        write_larch_run_sh(temporary.path().to_str().expect("utf8 session path"))
            .expect("write launcher");
        let rendered =
            fs::read_to_string(temporary.path().join("larch-run.sh")).expect("read launcher");
        assert!(rendered.contains("trap _larch_cleanup_active_leg EXIT INT TERM"));
        assert!(rendered.contains("LARCH_ACTIVE_LEG_OWNER_TOKEN"));
        assert!(rendered.contains("scripts/larch.sh\" implement kill-active-leg --owner-token"));
    }

    #[cfg(unix)]
    #[test]
    fn session_launcher_executes_only_supported_relative_targets() {
        let temporary = tempfile::tempdir().expect("temporary plugin fixture");
        let session = temporary.path().join("session");
        let plugin = temporary.path().join("plugin");
        fs::create_dir_all(plugin.join("scripts")).expect("plugin scripts");
        fs::create_dir_all(plugin.join("python")).expect("plugin python");
        fs::create_dir(&session).expect("session directory");
        fs::write(
            session.join("plugin-root.env"),
            format!("CLAUDE_PLUGIN_ROOT={}\n", plugin.display()),
        )
        .expect("plugin root sidecar");
        let shell_target = plugin.join("scripts/echo-argv.sh");
        fs::write(
            &shell_target,
            "#!/usr/bin/env bash\nprintf 'SH_ARGV=%s|%s\\n' \"$1\" \"$2\"\n",
        )
        .expect("shell target");
        let mut permissions = fs::metadata(&shell_target)
            .expect("shell target metadata")
            .permissions();
        permissions.set_mode(0o755);
        fs::set_permissions(&shell_target, permissions).expect("shell target executable");
        fs::write(
            plugin.join("python/echo_argv.py"),
            "import sys\nprint('PY_ARGV=' + '|'.join(sys.argv[1:]))\n",
        )
        .expect("python target");
        write_larch_run_sh(session.to_str().expect("utf8 session path")).expect("write launcher");
        let launcher = session.join("larch-run.sh");
        let run = |arguments: &[&str]| {
            Command::new("bash") // lint-subprocess-via-runner: ok test-only launcher fixture exercises the generated shell contract.
                .arg(&launcher)
                .args(arguments)
                .env_remove("IMPLEMENT_TMPDIR")
                .output()
                .expect("run launcher")
        };

        let shell = run(&["scripts/echo-argv.sh", "one", "two words"]);
        assert!(shell.status.success(), "{shell:?}");
        assert_eq!(
            String::from_utf8_lossy(&shell.stdout),
            "SH_ARGV=one|two words\n"
        );
        let python = run(&["python/echo_argv.py", "alpha", "beta gamma"]);
        assert!(python.status.success(), "{python:?}");
        assert!(
            String::from_utf8_lossy(&python.stdout).contains("PY_ARGV=alpha|beta gamma"),
            "{python:?}"
        );
        assert_eq!(
            run(&["/tmp/not-allowed.sh"]).status.code(),
            Some(2),
            "absolute target must be rejected"
        );
        assert_eq!(
            run(&["../not-allowed.sh"]).status.code(),
            Some(2),
            "traversal target must be rejected"
        );
        assert_eq!(
            run(&["scripts/not-supported.txt"]).status.code(),
            Some(2),
            "unsupported target must be rejected"
        );

        let session_fallback = temporary.path().join("session-fallback");
        fs::create_dir(&session_fallback).expect("fallback session");
        fs::write(
            session_fallback.join("session-env.sh"),
            format!("LARCH_CLAUDE_PLUGIN_ROOT={}\n", plugin.display()),
        )
        .expect("fallback session env");
        write_larch_run_sh(
            session_fallback
                .to_str()
                .expect("utf8 fallback session path"),
        )
        .expect("write fallback launcher");
        let root = Command::new("bash") // lint-subprocess-via-runner: ok test-only launcher fixture verifies the generated fallback resolver.
            .arg(session_fallback.join("larch-run.sh"))
            .arg("--print-plugin-root")
            .env_remove("IMPLEMENT_TMPDIR")
            .output()
            .expect("resolve fallback root");
        assert!(root.status.success(), "{root:?}");
        assert_eq!(
            String::from_utf8_lossy(&root.stdout).trim(),
            plugin.display().to_string()
        );
    }
}
