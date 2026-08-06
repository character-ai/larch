//! Vendor-agent commands composed over typed core and adapter boundaries.

use std::{
    collections::BTreeMap,
    env,
    ffi::{OsStr, OsString},
    fmt::Write as _,
    fs,
    io::{Read as _, Seek as _, SeekFrom},
    num::NonZeroUsize,
    path::{Path, PathBuf},
    process::ExitCode,
    sync::Arc,
    thread,
    time::{Duration, Instant},
};

use clap::{Args, Subcommand};
use larch_adapters::{
    ConfinedPath, ExactDiffRequest, GitCli, GitCliError, GitCliPolicy, GitPath as GitCliPath,
    GitRef, GixRepository, NoopProcessObserver, PathIntent, PluginRoot, ProcessFileRouting,
    ProcessStdinRouting, TemporaryRoot, TokioProcessRunner, atomic_write_bytes,
    atomic_write_utf8_in, check_reviewers, ensure_directory_chain, read_optional_utf8_lossy,
    read_utf8, remove_optional_file, run_cursor_model_list,
    runtime::{Cancellation, LarchRuntime},
    vendor_auth::{CursorPreflightConfig, ProbeCache, VendorAuthContext, cursor_auth_preflight},
    vendor_diagnostics::{
        parse_codex_usage_file, select_failed_agent_stderr_source, write_collector_failure_log,
        write_failed_agent_stderr_tail, write_failure_diag,
    },
    vendor_lifecycle::StartupLockConfig,
    vendor_reviewers::CheckReviewersContext,
};
use larch_core::{
    CODEX_REVIEW_MODEL_DEFAULT, CheckReviewersConfig, ChildEnvironment, CodexGateMessage,
    CodexModelRole, Commit, CursorCredential, DegradedToolsResult, ExternalProgram,
    LauncherArtifactKind, LauncherArtifactPaths, ModelTool, ProbeTtl, ProcessError,
    ProcessErrorKind, RepositoryRead, ReviewerWaitConfig, ReviewerWaitHost, ReviewerWaitRow,
    Revision, StderrCaptureMode, VendorProgram, WAIT_DEFAULT_POLL_INTERVAL_SECONDS,
    WAIT_DEFAULT_TIMEOUT_SECONDS, classify_diff, claude_model_from_transcript,
    codex_env_auth_from_key, codex_policy_rejection_excerpt, codex_probe_identity,
    cursor_child_environment, emit_kv, env as env_names, extract_model_from_argv,
    model_list_timeout_seconds, norm_bool, norm_tristate, parse_generated_paths,
    resolve_model_args, resolve_model_pins, sanitize_tool_label, tool_state,
    transcript_path_from_claude_source, validate_emitted_token, wait_for_reviewers,
};

const WAIT_USAGE: &str =
    "Usage: wait-for-reviewers.sh [--timeout SECONDS] <sentinel.done> [sentinel2.done ...]";
const GATHER_USAGE: &str = "Usage: gather-branch-context.sh --output-dir <path>";
const COLLECTOR_USAGE: &str = "Usage: compose-collector-failure-log.sh --structured-record <record> --output <path> [--reviewer-file <path>]";
const RUN_EXTERNAL_AGENT_USAGE: &str = "Usage: cli.py agent run-external-agent --tool NAME --output FILE --timeout SECS [--capture-stdout|--capture-stdout-only] [--stderr-sink PATH] -- CMD...";
const POLL_INTERVAL_ENV: &str = "WAIT_FOR_REVIEWERS_POLL_INTERVAL";
const RUN_EXTERNAL_AGENT_POLL_INTERVAL_ENV: &str = "RUN_EXTERNAL_AGENT_POLL_INTERVAL";
const RUN_EXTERNAL_AGENT_INNER_SENTINEL_SUFFIX_ENV: &str =
    "RUN_EXTERNAL_AGENT_INNER_SENTINEL_SUFFIX";
const RUN_EXTERNAL_AGENT_OUTPUT_LIMIT: usize = 64 * 1024;
const RUN_EXTERNAL_AGENT_SHUTDOWN_GRACE: Duration = Duration::from_secs(5);
const GENERATORS_TSV: &str = "scripts/generators.tsv";
/// Startup-lock carrier shared with every remaining Python vendor caller.
const SHARED_STARTUP_LOCK_ROOT: &str = "/tmp";

#[derive(Subcommand)]
pub enum AgentCommand {
    /// Prove Cursor can authenticate before a Cursor lane launches.
    CursorAuthPreflight,
    /// Probe Codex and Cursor binary presence and runtime health.
    #[command(name = "check-reviewers")]
    CheckReviewers(CheckReviewersArguments),
    /// Classify degraded external-tool availability for one skill Step 0 gate.
    #[command(name = "degraded-tools-gate")]
    DegradedToolsGate(DegradedToolsGateArguments),
    /// Resolve config-pinned vendor model ids against live vendor lists.
    #[command(name = "resolve-model-pins")]
    ResolveModelPins(ResolveModelPinsArguments),
    /// Wrap a Cursor prompt with the pinned max-mode preamble.
    #[command(name = "cursor-wrap-prompt", disable_help_flag = true)]
    CursorWrapPrompt(AgentRawArguments),
    /// Emit the external-tool and implementer-coder taxonomy.
    #[command(name = "external-tool-registry")]
    ExternalToolRegistry(ExternalToolRegistryArguments),
    /// Resolve Cursor or Codex model argv tokens.
    #[command(name = "model-args")]
    ModelArgs(ModelArgsArguments),
    /// Sum Codex token usage from a `--json` events stream.
    ParseCodexUsage(ParseCodexUsageArguments),
    /// Read the active Claude session model id.
    #[command(name = "read-claude-model")]
    ReadClaudeModel,
    /// Run one approved vendor executable and write the launch artifact family.
    #[command(disable_help_flag = true)]
    RunExternalAgent(AgentRawArguments),
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
pub struct CheckReviewersArguments {
    /// Skip the Codex health probe (binary discovery still runs).
    #[arg(long, action = clap::ArgAction::SetTrue)]
    skip_codex_probe: bool,
    /// Skip the Cursor health probe (binary discovery still runs).
    #[arg(long, action = clap::ArgAction::SetTrue)]
    skip_cursor_probe: bool,
}

#[derive(Args)]
pub struct DegradedToolsGateArguments {
    /// Codex binary-found tri-state (`true` / `false` / other → `unknown`).
    #[arg(long)]
    codex_binary_found: Option<String>,
    /// Codex presence from the durable session-env (`true` / `false`).
    #[arg(long)]
    codex_present: Option<String>,
    /// Cursor binary-found tri-state (`true` / `false` / other → `unknown`).
    #[arg(long)]
    cursor_binary_found: Option<String>,
    /// Cursor presence from the durable session-env (`true` / `false`).
    #[arg(long)]
    cursor_present: Option<String>,
    /// Skill name rendered into the operator explanation.
    #[arg(long, default_value = "this")]
    skill: String,
}

#[derive(Args)]
pub struct ResolveModelPinsArguments {
    /// Codex vendor state from the degraded-tools gate (`ok`, `binary-missing`, …).
    #[arg(long, required = true)]
    codex_state: String,
    /// Cursor vendor state from the degraded-tools gate (`ok`, `binary-missing`, …).
    #[arg(long, required = true)]
    cursor_state: String,
}

#[derive(Args)]
pub struct ParseCodexUsageArguments {
    /// Codex events JSONL file written by the launcher.
    events_jsonl: PathBuf,
}

#[derive(Args)]
pub struct ModelArgsArguments {
    #[arg(long)]
    tool: String,
    #[arg(long = "with-effort")]
    with_effort: bool,
    #[arg(long = "default-model", default_value = "")]
    default_model: String,
    #[arg(long = "codex-role", default_value = "default")]
    codex_role: String,
}

#[derive(Args)]
pub struct ExternalToolRegistryArguments {
    #[arg(long, default_value = "kv")]
    kind: String,
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
        AgentCommand::CursorAuthPreflight => cursor_auth_preflight_command(),
        AgentCommand::CheckReviewers(arguments) => check_reviewers_command(&arguments),
        AgentCommand::DegradedToolsGate(arguments) => degraded_tools_gate_command(&arguments),
        AgentCommand::ResolveModelPins(arguments) => resolve_model_pins_command(&arguments),
        AgentCommand::CursorWrapPrompt(arguments) => cursor_wrap_prompt(&arguments),
        AgentCommand::ExternalToolRegistry(arguments) => external_tool_registry(&arguments),
        AgentCommand::ModelArgs(arguments) => model_args(&arguments),
        AgentCommand::ParseCodexUsage(arguments) => parse_codex_usage(&arguments),
        AgentCommand::ReadClaudeModel => read_claude_model(),
        AgentCommand::RunExternalAgent(arguments) => run_external_agent(&arguments),
        AgentCommand::WaitReviewers(arguments) => wait_reviewers(&arguments),
        AgentCommand::ClassifyDiff(arguments) => classify_diff_command(&arguments),
        AgentCommand::GatherBranchContext(arguments) => gather_branch_context(&arguments),
        AgentCommand::ComposeCollectorFailureLog(arguments) => {
            compose_collector_failure_log(&arguments)
        }
    }
}

fn model_args(arguments: &ModelArgsArguments) -> ExitCode {
    let tool = match ModelTool::parse(&arguments.tool) {
        Ok(tool) => tool,
        Err(error) => {
            eprintln!("agent model-args: {error}");
            return ExitCode::from(1);
        }
    };
    let codex_role = match CodexModelRole::parse(&arguments.codex_role) {
        Ok(role) => role,
        Err(error) => {
            eprintln!("agent model-args: {error}");
            return ExitCode::from(1);
        }
    };
    let env_map = env::vars().collect();
    let result = match resolve_model_args(
        tool,
        arguments.with_effort,
        &arguments.default_model,
        codex_role,
        &env_map,
    ) {
        Ok(result) => result,
        Err(error) => {
            eprintln!("agent model-args: {error}");
            return ExitCode::from(1);
        }
    };
    if !result.warning().is_empty() {
        eprintln!("agent model-args: {}", result.warning());
    }
    for token in result.argv() {
        if token.is_empty() {
            continue;
        }
        if let Err(error) = validate_emitted_token(token) {
            eprintln!("agent model-args: {error}");
            return ExitCode::from(1);
        }
        println!("{token}");
    }
    ExitCode::SUCCESS
}

fn read_claude_model() -> ExitCode {
    let model = resolve_claude_model_from_environment();
    emit_kv("CLAUDE_MODEL", &model);
    ExitCode::SUCCESS
}

pub fn resolve_claude_model_from_environment() -> String {
    if let Some(model) = model_from_claude_source_file() {
        return model;
    }
    let Ok(home) = env::var("HOME") else {
        return "unknown".to_owned();
    };
    let Ok(repo_root) = discover_repo_root() else {
        return "unknown".to_owned();
    };
    let encoded = repo_root.replace('/', "-");
    let project_dir = PathBuf::from(home)
        .join(".claude")
        .join("projects")
        .join(encoded);
    let Ok(entries) = fs::read_dir(&project_dir) else {
        return "unknown".to_owned();
    };
    if let Some(model) = model_from_requested_session(&project_dir) {
        return model;
    }
    let mut latest: Option<(std::time::SystemTime, PathBuf)> = None;
    for entry in entries.flatten() {
        let path = entry.path();
        if path.extension().and_then(|ext| ext.to_str()) != Some("jsonl") {
            continue;
        }
        let modified = entry
            .metadata()
            .and_then(|meta| meta.modified())
            .unwrap_or(std::time::SystemTime::UNIX_EPOCH);
        match &latest {
            Some((stamp, _)) if modified <= *stamp => {}
            _ => latest = Some((modified, path)),
        }
    }
    let Some((_, path)) = latest else {
        return "unknown".to_owned();
    };
    fs::read_to_string(path).map_or_else(
        |_| "unknown".to_owned(),
        |body| claude_model_from_transcript(&body),
    )
}

fn model_from_claude_source_file() -> Option<String> {
    let source_file = env::var("LARCH_CLAUDE_SOURCE_FILE").ok()?;
    let text = fs::read_to_string(source_file).ok()?;
    let path = transcript_path_from_claude_source(&text)?;
    let body = fs::read_to_string(path).ok()?;
    Some(claude_model_from_transcript(&body))
}

fn model_from_requested_session(project_dir: &Path) -> Option<String> {
    let session_id = env::var("LARCH_CLAUDE_SESSION_ID")
        .or_else(|_| env::var("CLAUDE_CODE_SESSION_ID"))
        .ok()?;
    if session_id.is_empty() {
        return None;
    }
    let candidate = project_dir.join(format!("{session_id}.jsonl"));
    if !candidate.is_file() {
        return Some("unknown".to_owned());
    }
    let body = fs::read_to_string(candidate).ok()?;
    Some(claude_model_from_transcript(&body))
}

fn discover_repo_root() -> Result<String, ()> {
    let cwd = env::current_dir().map_err(|_| ())?;
    let repository = GixRepository::discover(&cwd).map_err(|_| ())?;
    let work_dir = repository.location().work_dir.ok_or(())?;
    let path = PathBuf::from(String::from_utf8_lossy(work_dir.as_bytes()).into_owned());
    let canonical = fs::canonicalize(path).map_err(|_| ())?;
    Ok(canonical.to_string_lossy().into_owned())
}

fn cursor_wrap_prompt(arguments: &AgentRawArguments) -> ExitCode {
    let Some(prompt) = arguments.arguments.first() else {
        eprintln!("agent cursor-wrap-prompt: a single prompt argument is required");
        return ExitCode::from(1);
    };
    let prompt = prompt.to_string_lossy();
    print!(" /max-mode on. Prompt: {prompt}");
    let _ = std::io::Write::flush(&mut std::io::stdout());
    ExitCode::SUCCESS
}

fn external_tool_registry(arguments: &ExternalToolRegistryArguments) -> ExitCode {
    match arguments.kind.as_str() {
        "external-tools" => {
            println!("codex");
            println!("cursor");
        }
        "implementer-coders" => {
            println!("claude");
            println!("codex");
            println!("cursor");
        }
        "kv" => {
            emit_kv("EXTERNAL_TOOLS", "codex,cursor");
            emit_kv("IMPLEMENTER_CODERS", "claude,codex,cursor");
        }
        other => {
            eprintln!("agent external-tool-registry: unsupported --kind {other}");
            return ExitCode::from(1);
        }
    }
    ExitCode::SUCCESS
}

/// Report the operating system under the name the vendor gates already use.
fn platform_name() -> &'static str {
    match env::consts::OS {
        "macos" => "Darwin",
        "linux" => "Linux",
        other => other,
    }
}

/// Resolve the startup-lock carrier, following the macOS `/tmp` symlink.
fn shared_startup_lock_root() -> Option<TemporaryRoot> {
    let canonical = fs::canonicalize(SHARED_STARTUP_LOCK_ROOT).ok()?;
    TemporaryRoot::resolve(Some(&canonical)).ok()
}

fn cursor_auth_preflight_command() -> ExitCode {
    let caller = "agent cursor-auth-preflight";
    let Ok(runtime) = LarchRuntime::current_thread() else {
        eprintln!("{caller}: could not start the local runtime");
        return ExitCode::from(1);
    };
    let Ok(working_directory) = env::current_dir() else {
        eprintln!("{caller}: could not resolve the working directory");
        return ExitCode::from(1);
    };
    let config = CursorPreflightConfig::from_values(
        platform_name(),
        env::var(env_names::CURSOR_API_KEY).ok().as_deref(),
        caller,
    );
    let Some(lock_root) = shared_startup_lock_root() else {
        eprintln!("{caller}: could not resolve the shared vendor startup-lock directory");
        return ExitCode::from(1);
    };
    // Release delay `0`: the preflight holds the shared vendor startup lock only
    // for its own keychain read and must not add latency to a concurrent launch.
    let Ok(startup_lock) = StartupLockConfig::from_values(
        VendorProgram::Cursor,
        platform_name(),
        env::var(env_names::USER).ok().as_deref(),
        None,
        None,
        Some("0"),
    ) else {
        eprintln!("{caller}: USER is unusable as a startup-lock path component");
        return ExitCode::from(1);
    };
    let runner = TokioProcessRunner::new(Arc::new(NoopProcessObserver));
    let verdict = runtime.block_on(cursor_auth_preflight(
        &runner,
        &config,
        VendorAuthContext {
            temporary_root: &lock_root,
            startup_lock: &startup_lock,
            working_directory: &working_directory,
        },
        &Cancellation::new(),
    ));
    if verdict.ok {
        return ExitCode::SUCCESS;
    }
    eprintln!("{}", verdict.message);
    ExitCode::from(u8::try_from(verdict.rc).unwrap_or(1))
}

fn check_reviewers_command(arguments: &CheckReviewersArguments) -> ExitCode {
    let caller = "agent check-reviewers";
    let Ok(runtime) = LarchRuntime::current_thread() else {
        eprintln!("{caller}: could not start the local runtime");
        return ExitCode::from(1);
    };
    let Ok(working_directory) = env::current_dir() else {
        eprintln!("{caller}: could not resolve the working directory");
        return ExitCode::from(1);
    };
    let Some(temporary_root) = probe_temporary_root() else {
        eprintln!("{caller}: could not resolve the temporary root");
        return ExitCode::from(1);
    };
    let Some(home) = env::var_os(env_names::HOME).map(PathBuf::from) else {
        eprintln!("{caller}: HOME is unset");
        return ExitCode::from(1);
    };
    let path_env = env::var(env_names::PATH).ok();
    let user = env::var(env_names::USER).ok();
    let openai_api_key = env::var(env_names::OPENAI_API_KEY).ok();
    let cursor_api_key = env::var(env_names::CURSOR_API_KEY).ok();
    let env_map: BTreeMap<String, String> = env::vars().collect();
    let config = CheckReviewersConfig::from_env_values(
        env::var(env_names::LARCH_PROBE_TTL_SECONDS).ok().as_deref(),
        env::var(env_names::LARCH_PROBE_NEGATIVE_TTL_SECONDS)
            .ok()
            .as_deref(),
        env::var(env_names::LARCH_PROBE_TIMEOUT_SECONDS)
            .ok()
            .as_deref(),
        env::var(env_names::LARCH_EXTERNAL_AUTH_RETRIES)
            .ok()
            .as_deref(),
        env::var(env_names::LARCH_PROBE_RETRIES).ok().as_deref(),
        env::var(env_names::LARCH_PROBE_TIMEOUT_RETRIES)
            .ok()
            .as_deref(),
        arguments.skip_codex_probe,
        arguments.skip_cursor_probe,
        None,
    );
    let context = CheckReviewersContext {
        temporary_root: &temporary_root,
        home: &home,
        working_directory: &working_directory,
        path_env: path_env.as_deref(),
        user: user.as_deref(),
        openai_api_key: openai_api_key.as_deref(),
        cursor_api_key: cursor_api_key.as_deref(),
        platform: platform_name(),
        env_map: &env_map,
    };
    let runner = TokioProcessRunner::new(Arc::new(NoopProcessObserver));
    let result = runtime.block_on(check_reviewers(
        &runner,
        &config,
        context,
        &Cancellation::new(),
    ));
    for line in result.kv_lines() {
        println!("{line}");
    }
    ExitCode::SUCCESS
}

fn degraded_tools_gate_command(arguments: &DegradedToolsGateArguments) -> ExitCode {
    let codex_binary_found = flag_or_env(
        arguments.codex_binary_found.as_deref(),
        "CODEX_BINARY_FOUND",
        "unknown",
    );
    let codex_present = flag_or_env(arguments.codex_present.as_deref(), "CODEX_PRESENT", "");
    let cursor_binary_found = flag_or_env(
        arguments.cursor_binary_found.as_deref(),
        "CURSOR_BINARY_FOUND",
        "unknown",
    );
    let cursor_present = flag_or_env(arguments.cursor_present.as_deref(), "CURSOR_PRESENT", "");
    if codex_present.is_empty() {
        eprintln!(
            "agent degraded-tools-gate: ERROR: --codex-present resolved empty (caller rehydration bug: read presence keys from the durable session-env file, not ambient shell state); treating as down (fail-safe)"
        );
    }
    if cursor_present.is_empty() {
        eprintln!(
            "agent degraded-tools-gate: ERROR: --cursor-present resolved empty (caller rehydration bug: read presence keys from the durable session-env file, not ambient shell state); treating as down (fail-safe)"
        );
    }
    let codex_gate_message =
        codex_gate_message_for_probe_failed(&codex_binary_found, &codex_present);
    let result = DegradedToolsResult::classify(
        &codex_binary_found,
        &codex_present,
        &cursor_binary_found,
        &cursor_present,
        &arguments.skill,
        codex_gate_message.as_ref(),
    );
    for line in result.kv_lines() {
        println!("{line}");
    }
    if result.degraded() {
        println!("DEGRADED_EXPLANATION_BEGIN");
        for line in result.explanation() {
            println!("{line}");
        }
        println!("DEGRADED_EXPLANATION_END");
    }
    ExitCode::SUCCESS
}

fn resolve_model_pins_command(arguments: &ResolveModelPinsArguments) -> ExitCode {
    let caller = "agent resolve-model-pins";
    let cursor_list = if arguments.cursor_state == "ok" {
        let Ok(runtime) = LarchRuntime::current_thread() else {
            eprintln!("{caller}: could not start the local runtime");
            return ExitCode::from(1);
        };
        let Ok(working_directory) = env::current_dir() else {
            eprintln!("{caller}: could not resolve the working directory");
            return ExitCode::from(1);
        };
        let timeout = Duration::from_secs(model_list_timeout_seconds(
            env::var(env_names::LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT)
                .ok()
                .as_deref(),
        ));
        let runner = TokioProcessRunner::new(Arc::new(NoopProcessObserver));
        Some(runtime.block_on(run_cursor_model_list(
            &runner,
            &working_directory,
            timeout,
            &Cancellation::new(),
        )))
    } else {
        None
    };
    let report = resolve_model_pins(&arguments.codex_state, &arguments.cursor_state, cursor_list);
    emit_kv("CURSOR_MODEL_PINS", report.cursor.status());
    if !report.cursor.detail().is_empty() {
        emit_kv("CURSOR_MODEL_PIN_DETAIL", report.cursor.detail());
    }
    emit_kv("CODEX_MODEL_PINS", report.codex.status());
    if !report.codex.detail().is_empty() {
        emit_kv("CODEX_MODEL_PIN_DETAIL", report.codex.detail());
    }
    ExitCode::SUCCESS
}

/// Resolve the probe/cache temporary root from `TMPDIR` or `/tmp`.
fn probe_temporary_root() -> Option<TemporaryRoot> {
    let raw = env::var_os(env_names::TMPDIR).map_or_else(|| PathBuf::from("/tmp"), PathBuf::from);
    let canonical = fs::canonicalize(&raw).ok()?;
    TemporaryRoot::resolve(Some(&canonical)).ok()
}

/// Resolve a CLI flag, falling back to an environment variable, then a default.
fn flag_or_env(cli: Option<&str>, env_name: &str, default: &str) -> String {
    if let Some(value) = cli {
        return value.to_owned();
    }
    env::var(env_name).unwrap_or_else(|_| default.to_owned())
}

/// Read a cached Codex gate-detail message when Codex would classify as probe-failed.
fn codex_gate_message_for_probe_failed(
    codex_binary_found: &str,
    codex_present: &str,
) -> Option<CodexGateMessage> {
    let binary = norm_tristate(codex_binary_found);
    let present = norm_bool(codex_present);
    if tool_state(binary, present) != "probe-failed" {
        return None;
    }
    let temporary_root = probe_temporary_root()?;
    let ttl_seconds = env::var(env_names::LARCH_PROBE_TTL_SECONDS)
        .ok()
        .and_then(|raw| raw.trim().parse::<u64>().ok())
        .unwrap_or(60);
    let negative_ttl_seconds = env::var(env_names::LARCH_PROBE_NEGATIVE_TTL_SECONDS)
        .ok()
        .and_then(|raw| raw.trim().parse::<u64>().ok())
        .unwrap_or(0);
    let ttl = ProbeTtl::from_seconds(ttl_seconds, negative_ttl_seconds);
    let cache = ProbeCache::new(
        temporary_root,
        env::var(env_names::USER).ok().as_deref(),
        ttl,
    );
    let env_map: BTreeMap<String, String> = env::vars().collect();
    let resolved_model =
        match resolve_model_args(ModelTool::Codex, true, "", CodexModelRole::Review, &env_map) {
            Ok(result) => {
                let model = extract_model_from_argv(result.argv());
                if model.is_empty() {
                    CODEX_REVIEW_MODEL_DEFAULT.to_owned()
                } else {
                    model
                }
            }
            Err(_) => return None,
        };
    let auth = codex_env_auth_from_key(env::var(env_names::OPENAI_API_KEY).ok().as_deref());
    let identity = codex_probe_identity(auth, &resolved_model);
    cache
        .read_gate_detail(&identity, ttl.standalone_gate_max_age())
        .map(|detail| CodexGateMessage::new(detail.message().to_owned()))
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

struct RunExternalAgentArguments {
    tool: String,
    output: String,
    timeout_seconds: u64,
    poll_interval: Duration,
    capture_stdout: bool,
    capture_stdout_only: bool,
    stderr_sink: Option<PathBuf>,
    command: Vec<String>,
    program: VendorProgram,
    sentinel_suffix: &'static str,
}

enum RunExternalAgentParse {
    Help,
    Error(String),
    Parsed(RunExternalAgentArguments),
}

struct RunExternalAgentOptions {
    tool: String,
    output: String,
    timeout_raw: String,
    stderr_sink: String,
    capture_stdout: bool,
    capture_stdout_only: bool,
    command: Vec<String>,
}

enum RunExternalAgentOptionsParse {
    Help,
    Error(String),
    Parsed(RunExternalAgentOptions),
}

struct PreparedExternalAgentFiles {
    root: TemporaryRoot,
    paths: LauncherArtifactPaths,
    output_file: ConfinedPath,
    diag_file: ConfinedPath,
    diag: PathBuf,
    done: PathBuf,
}

fn run_external_agent(arguments: &AgentRawArguments) -> ExitCode {
    let parsed = match parse_run_external_agent_arguments(&arguments.arguments) {
        RunExternalAgentParse::Help => {
            eprintln!("{RUN_EXTERNAL_AGENT_USAGE}");
            return ExitCode::SUCCESS;
        }
        RunExternalAgentParse::Error(message) => {
            eprintln!("{message}");
            return ExitCode::from(1);
        }
        RunExternalAgentParse::Parsed(value) => value,
    };
    let prepared = match prepare_run_external_agent_files(&parsed) {
        Ok(value) => value,
        Err(error) => {
            eprintln!("agent run-external-agent: {error}");
            return ExitCode::from(1);
        }
    };
    let exit_code = run_prepared_external_agent(&parsed, &prepared);
    let done_write = atomic_write_utf8_in(
        &prepared.root,
        &prepared.done,
        &format!("{exit_code}\n"),
        true,
        0o600,
    );
    if let Err(error) = done_write {
        eprintln!("agent run-external-agent: could not write completion sentinel: {error}");
        return ExitCode::from(1);
    }
    ExitCode::from(u8::try_from(exit_code).unwrap_or(1))
}

fn parse_run_external_agent_arguments(arguments: &[OsString]) -> RunExternalAgentParse {
    match parse_run_external_agent_options(arguments) {
        RunExternalAgentOptionsParse::Help => RunExternalAgentParse::Help,
        RunExternalAgentOptionsParse::Error(message) => RunExternalAgentParse::Error(message),
        RunExternalAgentOptionsParse::Parsed(options) => {
            build_run_external_agent_arguments(options)
        }
    }
}

fn parse_run_external_agent_options(arguments: &[OsString]) -> RunExternalAgentOptionsParse {
    let mut tool = String::new();
    let mut output = String::new();
    let mut timeout_raw = String::new();
    let mut stderr_sink = String::new();
    let mut capture_stdout = false;
    let mut capture_stdout_only = false;
    let mut index = 0_usize;
    while index < arguments.len() {
        let argument = arguments[index].to_string_lossy();
        if argument == "--" {
            index += 1;
            break;
        }
        match argument.as_ref() {
            "--tool" if index + 1 < arguments.len() => {
                tool = arguments[index + 1].to_string_lossy().into_owned();
                index += 2;
            }
            "--output" if index + 1 < arguments.len() => {
                output = arguments[index + 1].to_string_lossy().into_owned();
                index += 2;
            }
            "--timeout" if index + 1 < arguments.len() => {
                timeout_raw = arguments[index + 1].to_string_lossy().into_owned();
                index += 2;
            }
            "--stderr-sink" if index + 1 < arguments.len() => {
                stderr_sink = arguments[index + 1].to_string_lossy().into_owned();
                index += 2;
            }
            "--capture-stdout" => {
                capture_stdout = true;
                index += 1;
            }
            "--capture-stdout-only" => {
                capture_stdout_only = true;
                index += 1;
            }
            "--help" => return RunExternalAgentOptionsParse::Help,
            _ => return RunExternalAgentOptionsParse::Error(format!("Unknown option: {argument}")),
        }
    }
    let command: Vec<String> = arguments[index..]
        .iter()
        .map(|argument| argument.to_string_lossy().into_owned())
        .collect();
    if tool.is_empty() || output.is_empty() || timeout_raw.is_empty() {
        return RunExternalAgentOptionsParse::Error(
            "ERROR: --tool, --output, and --timeout are required".to_owned(),
        );
    }
    if capture_stdout && capture_stdout_only {
        return RunExternalAgentOptionsParse::Error(
            "ERROR: --capture-stdout and --capture-stdout-only are mutually exclusive".to_owned(),
        );
    }
    RunExternalAgentOptionsParse::Parsed(RunExternalAgentOptions {
        tool,
        output,
        timeout_raw,
        stderr_sink,
        capture_stdout,
        capture_stdout_only,
        command,
    })
}

fn build_run_external_agent_arguments(options: RunExternalAgentOptions) -> RunExternalAgentParse {
    if !crate::valid_meta_path(OsStr::new(&options.output)) {
        return RunExternalAgentParse::Error(
            "ERROR: --output contains unsupported characters".to_owned(),
        );
    }
    if !options.stderr_sink.is_empty() && !crate::valid_meta_path(OsStr::new(&options.stderr_sink))
    {
        return RunExternalAgentParse::Error(
            "ERROR: --stderr-sink contains unsupported characters".to_owned(),
        );
    }
    let Some(timeout_seconds) = larch_core::positive_integer(&options.timeout_raw) else {
        return RunExternalAgentParse::Error(format!(
            "ERROR: --timeout must be a positive integer, got '{}'",
            options.timeout_raw
        ));
    };
    let sentinel_suffix = match run_external_agent_sentinel_suffix() {
        Ok(value) => value,
        Err(message) => return RunExternalAgentParse::Error(message),
    };
    let poll_interval = match run_external_agent_poll_interval() {
        Ok(value) => value,
        Err(message) => return RunExternalAgentParse::Error(message),
    };
    if options.command.is_empty() {
        return RunExternalAgentParse::Error("ERROR: no command specified after --".to_owned());
    }
    let program = match options.command[0].as_str() {
        "claude" => VendorProgram::Claude,
        "codex" => VendorProgram::Codex,
        "cursor" => VendorProgram::Cursor,
        _ => {
            return RunExternalAgentParse::Error(
                "ERROR: command must begin with an approved vendor executable".to_owned(),
            );
        }
    };
    RunExternalAgentParse::Parsed(RunExternalAgentArguments {
        tool: options.tool,
        output: options.output,
        timeout_seconds,
        poll_interval,
        capture_stdout: options.capture_stdout,
        capture_stdout_only: options.capture_stdout_only,
        stderr_sink: (!options.stderr_sink.is_empty()).then(|| PathBuf::from(options.stderr_sink)),
        command: options.command,
        program,
        sentinel_suffix,
    })
}

fn run_external_agent_sentinel_suffix() -> Result<&'static str, String> {
    match env::var(RUN_EXTERNAL_AGENT_INNER_SENTINEL_SUFFIX_ENV) {
        Ok(value) if value.is_empty() => Ok(".done"),
        Ok(value) if value == ".inner.done" => Ok(".inner.done"),
        Ok(value) => Err(format!(
            "ERROR: invalid {RUN_EXTERNAL_AGENT_INNER_SENTINEL_SUFFIX_ENV} value '{value}'; expected '.inner.done'"
        )),
        Err(_error) => Ok(".done"),
    }
}

fn run_external_agent_poll_interval() -> Result<Duration, String> {
    let raw =
        env::var(RUN_EXTERNAL_AGENT_POLL_INTERVAL_ENV).unwrap_or_else(|_error| "10".to_owned());
    let Some(seconds) = raw
        .parse::<f64>()
        .ok()
        .filter(|value| value.is_finite() && *value > 0.0)
    else {
        return Err(format!(
            "ERROR: {RUN_EXTERNAL_AGENT_POLL_INTERVAL_ENV} must be a positive number, got '{raw}'"
        ));
    };
    Ok(Duration::from_secs_f64(seconds))
}

fn prepare_run_external_agent_files(
    arguments: &RunExternalAgentArguments,
) -> Result<PreparedExternalAgentFiles, String> {
    let working_directory = env::current_dir().map_err(|error| error.to_string())?;
    let requested_output = PathBuf::from(&arguments.output);
    let output = if requested_output.is_absolute() {
        requested_output
    } else {
        working_directory.join(requested_output)
    };
    let parent = output
        .parent()
        .ok_or_else(|| "--output has no parent directory".to_owned())?;
    let file_name = output
        .file_name()
        .ok_or_else(|| "--output must name a file".to_owned())?;
    ensure_directory_chain(parent).map_err(|error| error.to_string())?;
    let root = TemporaryRoot::resolve(Some(parent)).map_err(|error| error.to_string())?;
    let output = root
        .confine(root.path().join(file_name), PathIntent::Write)
        .map_err(|error| error.to_string())?
        .path()
        .to_path_buf();
    let paths = LauncherArtifactPaths::new(output);
    let diag = paths.path(LauncherArtifactKind::Diag);
    let done = suffixed_launcher_path(paths.output(), arguments.sentinel_suffix);
    let stale_paths = [
        paths.output().to_path_buf(),
        paths.path(LauncherArtifactKind::Done),
        paths.path(LauncherArtifactKind::InnerDone),
        paths.path(LauncherArtifactKind::Meta),
        diag.clone(),
        paths.path(LauncherArtifactKind::StderrTail),
        paths.path(LauncherArtifactKind::FailureDiag),
    ];
    for stale in stale_paths {
        remove_external_agent_stale(&root, &stale)?;
    }
    let command_json =
        serde_json::to_string(&arguments.command).map_err(|error| error.to_string())?;
    let mut meta = format!(
        "TOOL={}\nTIMEOUT={}\nCAPTURE_STDOUT={}\nCAPTURE_STDOUT_ONLY={}\nOUTPUT_FILE={}\n",
        sanitize_tool_label(&arguments.tool),
        arguments.timeout_seconds,
        arguments.capture_stdout,
        arguments.capture_stdout_only,
        arguments.output,
    );
    if let Some(stderr_sink) = &arguments.stderr_sink {
        writeln!(&mut meta, "STDERR_SINK={}", stderr_sink.display())
            .expect("formatting a String is infallible");
    }
    writeln!(&mut meta, "CMD_JSON={command_json}").expect("formatting a String is infallible");
    atomic_write_utf8_in(
        &root,
        &paths.path(LauncherArtifactKind::Meta),
        &meta,
        true,
        0o600,
    )
    .map_err(|error| error.to_string())?;
    let output_file = root
        .confine(paths.output(), PathIntent::Write)
        .map_err(|error| error.to_string())?;
    let diag_file = root
        .confine(&diag, PathIntent::Write)
        .map_err(|error| error.to_string())?;
    Ok(PreparedExternalAgentFiles {
        root,
        paths,
        output_file,
        diag_file,
        diag,
        done,
    })
}

fn run_prepared_external_agent(
    arguments: &RunExternalAgentArguments,
    prepared: &PreparedExternalAgentFiles,
) -> i32 {
    let Ok(runtime) = LarchRuntime::current_thread() else {
        let _ignored = append_launcher_text(
            &prepared.root,
            &prepared.diag,
            "Failed to launch child: could not start the local runtime\n",
        );
        return 127;
    };
    let Ok(working_directory) = env::current_dir() else {
        let _ignored = append_launcher_text(
            &prepared.root,
            &prepared.diag,
            "Failed to launch child: could not resolve the working directory\n",
        );
        return 127;
    };
    let request = match external_agent_request(arguments, working_directory) {
        Ok(value) => value,
        Err(error) => {
            let _ignored = append_launcher_text(
                &prepared.root,
                &prepared.diag,
                &format!("Failed to launch child: {error}\n"),
            );
            return 127;
        }
    };
    let (routing, policy_watch) = external_agent_file_routing(arguments, prepared);
    let cancellation = Cancellation::new();
    let runner = TokioProcessRunner::new(Arc::new(NoopProcessObserver));
    let (result, policy_excerpt) = runtime.block_on(run_file_routed_external_agent(
        &runner,
        request,
        &cancellation,
        routing,
        policy_watch.as_ref(),
        arguments.poll_interval,
    ));
    let exit_code = external_agent_exit_code(arguments, prepared, result, policy_excerpt.is_some());
    if let Some(excerpt) = policy_excerpt {
        append_external_agent_policy_failure(prepared, &excerpt);
    }
    finish_external_agent_launch(arguments, prepared, exit_code);
    exit_code
}

fn external_agent_request(
    arguments: &RunExternalAgentArguments,
    working_directory: PathBuf,
) -> Result<larch_core::ProcessRequest, String> {
    let output_limit =
        NonZeroUsize::new(RUN_EXTERNAL_AGENT_OUTPUT_LIMIT).unwrap_or(NonZeroUsize::MIN);
    larch_core::ProcessRequest::new(
        ExternalProgram::Vendor(arguments.program),
        arguments.command.iter().skip(1).cloned(),
        working_directory,
        Duration::from_secs(arguments.timeout_seconds),
        RUN_EXTERNAL_AGENT_SHUTDOWN_GRACE,
        output_limit,
    )
    .map(|request| request.with_environment_for_vendor(arguments.program))
    .map_err(|error| error.to_string())
}

fn external_agent_file_routing(
    arguments: &RunExternalAgentArguments,
    prepared: &PreparedExternalAgentFiles,
) -> (ProcessFileRouting, Option<ConfinedPath>) {
    let routing = if arguments.capture_stdout {
        ProcessFileRouting::combined(prepared.output_file.clone())
    } else if arguments.capture_stdout_only {
        ProcessFileRouting::separate(prepared.output_file.clone(), prepared.diag_file.clone())
    } else {
        ProcessFileRouting::inherit_output()
    }
    .with_stdin(if arguments.tool == "codex" {
        ProcessStdinRouting::Null
    } else {
        ProcessStdinRouting::Inherit
    });
    let policy_watch = (arguments.tool == "codex"
        && (arguments.capture_stdout || arguments.capture_stdout_only))
        .then(|| prepared.output_file.clone());
    (routing, policy_watch)
}

fn external_agent_exit_code(
    arguments: &RunExternalAgentArguments,
    prepared: &PreparedExternalAgentFiles,
    result: Result<larch_core::ProcessOutput, ProcessError>,
    policy_rejected: bool,
) -> i32 {
    if policy_rejected {
        return 1;
    }
    match result {
        Ok(output) => output.status().code().unwrap_or(1),
        Err(error) if error.kind() == ProcessErrorKind::TimedOut => {
            let size = output_size(prepared.paths.output());
            let _ignored = append_launcher_text(
                &prepared.root,
                &prepared.diag,
                &format!(
                    "Timed out after {}s (limit: {}s). Process was killed after exceeding the timeout. Output size: {size} bytes.\n",
                    arguments.timeout_seconds, arguments.timeout_seconds
                ),
            );
            124
        }
        Err(error) => {
            let code = spawn_error_exit_code(&error);
            if error.kind() == ProcessErrorKind::Spawn {
                let _ignored =
                    atomic_write_utf8_in(&prepared.root, prepared.paths.output(), "", true, 0o600);
            }
            let _ignored = append_launcher_text(
                &prepared.root,
                &prepared.diag,
                &format!("Failed to launch child: {}\n", error.message()),
            );
            code
        }
    }
}

fn append_external_agent_policy_failure(prepared: &PreparedExternalAgentFiles, excerpt: &str) {
    let _ignored = append_launcher_text(
        &prepared.root,
        &prepared.diag,
        &format!(
            "FAILURE_CLASS=policy-rejection\nPOLICY_REJECTION=true\nCodex exec_command policy rejection detected in events stream.\nMatched excerpt:\n{}\n",
            excerpt.trim_end()
        ),
    );
}

trait VendorRequestEnvironment {
    fn with_environment_for_vendor(self, program: VendorProgram) -> Self;
}

impl VendorRequestEnvironment for larch_core::ProcessRequest {
    fn with_environment_for_vendor(mut self, program: VendorProgram) -> Self {
        match program {
            VendorProgram::Claude | VendorProgram::Codex => {
                let key = if program == VendorProgram::Claude {
                    ChildEnvironment::AnthropicApiKey
                } else {
                    ChildEnvironment::OpenAiApiKey
                };
                if let Some(value) = env::var_os(key.name()) {
                    self = self.with_environment(key, value);
                }
            }
            VendorProgram::Cursor => {
                let credential = env::var(env_names::CURSOR_API_KEY)
                    .ok()
                    .and_then(|value| CursorCredential::parse(&value));
                for (key, value) in cursor_child_environment(credential.as_ref()) {
                    self = self.with_environment(key, value);
                }
            }
        }
        self
    }
}

async fn run_file_routed_external_agent(
    runner: &TokioProcessRunner,
    request: larch_core::ProcessRequest,
    cancellation: &Cancellation,
    routing: ProcessFileRouting,
    policy_watch: Option<&ConfinedPath>,
    poll_interval: Duration,
) -> (
    Result<larch_core::ProcessOutput, ProcessError>,
    Option<String>,
) {
    let mut launch = Box::pin(runner.run_with_files(request, cancellation, routing));
    let mut ticker = tokio::time::interval(poll_interval);
    let mut policy_excerpt = None;
    loop {
        tokio::select! {
            result = &mut launch => {
                if policy_excerpt.is_none()
                    && let Some(path) = policy_watch
                    && let Some(excerpt) = codex_policy_excerpt_from_file(path)
                {
                    policy_excerpt = Some(excerpt);
                }
                return (result, policy_excerpt);
            }
            _ = ticker.tick(), if policy_watch.is_some() && policy_excerpt.is_none() => {
                if let Some(path) = policy_watch
                    && let Some(excerpt) = codex_policy_excerpt_from_file(path)
                {
                    eprintln!("❌ codex agent: exec_command policy rejection detected, killing");
                    cancellation.cancel();
                    policy_excerpt = Some(excerpt);
                }
            }
        }
    }
}

fn codex_policy_excerpt_from_file(path: &ConfinedPath) -> Option<String> {
    path.revalidate().ok()?;
    let mut file = fs::File::open(path.path()).ok()?;
    let length = file.metadata().ok()?.len();
    let cap = u64::try_from(larch_core::CODEX_POLICY_REJECTION_TAIL_BYTES + 1).ok()?;
    if length > cap {
        file.seek(SeekFrom::Start(length - cap)).ok()?;
    }
    let mut bytes = Vec::with_capacity(usize::try_from(length.min(cap)).ok()?);
    file.read_to_end(&mut bytes).ok()?;
    let excerpt = codex_policy_rejection_excerpt(&String::from_utf8_lossy(&bytes));
    (!excerpt.is_empty()).then_some(excerpt)
}

fn finish_external_agent_launch(
    arguments: &RunExternalAgentArguments,
    prepared: &PreparedExternalAgentFiles,
    exit_code: i32,
) {
    let size = output_size(prepared.paths.output());
    if exit_code != 0 {
        eprintln!(
            "❌ {} agent: FAILED (exit code {exit_code}, output {size} bytes)",
            arguments.tool
        );
        let _ignored = append_launcher_text(
            &prepared.root,
            &prepared.diag,
            &format!("Failed with exit code {exit_code}. Output size: {size} bytes.\n"),
        );
        let mode = if arguments.capture_stdout {
            StderrCaptureMode::Combined
        } else if arguments.capture_stdout_only {
            StderrCaptureMode::StdoutOnly
        } else {
            StderrCaptureMode::Separate
        };
        if let Ok(Some(source)) = select_failed_agent_stderr_source(
            &prepared.paths,
            mode,
            arguments.stderr_sink.as_deref(),
        ) {
            let _ignored = write_failed_agent_stderr_tail(
                &prepared.root,
                &source,
                &prepared.paths,
                None,
                None,
            );
        }
        let _ignored = write_failure_diag(
            &prepared.root,
            &prepared.paths,
            arguments.stderr_sink.as_deref(),
            None,
            None,
        );
    } else if size == 0 {
        eprintln!(
            "⚠ {} agent: completed but OUTPUT IS EMPTY (exit code 0)",
            arguments.tool
        );
        let _ignored = append_launcher_text(
            &prepared.root,
            &prepared.diag,
            "Process exited successfully (code 0) but produced no output.\n",
        );
        let _ignored = remove_external_agent_stale(
            &prepared.root,
            &prepared.paths.path(LauncherArtifactKind::FailureDiag),
        );
    } else {
        eprintln!(
            "✓ {} agent: completed (exit code 0, output {size} bytes)",
            arguments.tool
        );
        let _ignored = remove_external_agent_stale(
            &prepared.root,
            &prepared.paths.path(LauncherArtifactKind::FailureDiag),
        );
    }
}

fn append_launcher_text(root: &TemporaryRoot, path: &Path, text: &str) -> Result<(), String> {
    let existing = read_external_agent_text(root, path)?;
    atomic_write_utf8_in(root, path, &format!("{existing}{text}"), true, 0o600)
        .map_err(|error| error.to_string())
}

fn remove_external_agent_stale(root: &TemporaryRoot, path: &Path) -> Result<(), String> {
    match fs::symlink_metadata(path) {
        Ok(_metadata) => {
            let confined = root
                .confine(path, PathIntent::Cleanup)
                .map_err(|error| error.to_string())?;
            remove_optional_file(confined.path()).map_err(|error| error.to_string())
        }
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => Ok(()),
        Err(error) => Err(error.to_string()),
    }
}

fn read_external_agent_text(root: &TemporaryRoot, path: &Path) -> Result<String, String> {
    match fs::symlink_metadata(path) {
        Ok(_metadata) => {
            let confined = root
                .confine(path, PathIntent::Read)
                .map_err(|error| error.to_string())?;
            fs::read(confined.path())
                .map(|bytes| String::from_utf8_lossy(&bytes).into_owned())
                .map_err(|error| error.to_string())
        }
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => Ok(String::new()),
        Err(error) => Err(error.to_string()),
    }
}

fn output_size(path: &Path) -> u64 {
    fs::metadata(path).map_or(0, |metadata| metadata.len())
}

fn spawn_error_exit_code(error: &ProcessError) -> i32 {
    if error.kind() == ProcessErrorKind::Spawn && error.message().contains("Permission denied") {
        126
    } else if error.kind() == ProcessErrorKind::Spawn {
        127
    } else {
        1
    }
}

fn suffixed_launcher_path(output: &Path, suffix: &str) -> PathBuf {
    let mut rendered = output.as_os_str().to_owned();
    rendered.push(suffix);
    PathBuf::from(rendered)
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
