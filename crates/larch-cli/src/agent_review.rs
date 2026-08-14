//! Rust owner for the legacy `agent launch-review` command.
//!
//! Vendor process setup remains in `external_agent`, credentials stay in the
//! vendor adapters, and cross-owner timing/token writes use the bounded Python
//! verb bridge. This module owns only the review command composition.

use crate::{
    agent_commands::{AgentRawArguments, generated_paths},
    argparse_compat::split_inline_option,
    claude_commands::{panel_artifact_path, panel_slot_kind, parse_uint},
    dirty_tree_commands,
    external_agent::{ExternalAgentLaunch, ExternalAgentRouting, run_external_agent_launch},
    valid_meta_path,
};
use larch_adapters::{
    CodexHomeContext, ConfinedPath, CursorConfigContext, NoopProcessObserver, PathIntent,
    TemporaryRoot, TokioProcessRunner, atomic_write_utf8_in, ensure_directory_chain,
    read_optional_utf8_lossy, remove_optional_file, rename_same_directory,
    vendor_auth::{
        CursorPreflightConfig, CursorTokenPreread, VendorAuthContext, cursor_auth_preflight,
        cursor_preread_service_token,
    },
    vendor_diagnostics::{external_stream_reset, parse_codex_usage_file, write_failure_diag},
    vendor_lifecycle::{
        StartupLockConfig, StartupLockRelease, external_startup_lock_acquire,
        external_startup_lock_release_after,
    },
};
use larch_core::{
    AuthVerdict, CODEX_DESCRIPTOR, CURSOR_DEGRADED_RESPONSE, CURSOR_DESCRIPTOR, ChildEnvironment,
    CodexModelRole, CodexPromptSentinelRead, CodexPromptSidecarArgs, ENV_CURSOR_LAUNCH_JITTER_MS,
    ENV_CURSOR_RETRY_EMPTY_RESULT, ENV_TOKEN_BUDGET_CAP_REVIEW, ENV_TRANSIENT_RETRY_DELAY,
    ExternalProcessRunner as _, ExternalProgram, LaunchFailureInputs, LauncherArtifact,
    LauncherArtifactKind, LauncherArtifactPaths, ModelTool, ProcessRequest, PythonVerbProgram,
    REVIEW_MAX_TRANSIENT_RETRIES, ResearchOutputValidator, SpecialistRenderPort,
    VendorLaunchRequest, VendorProgram, classify_diff, codex_env_auth_from_key,
    cursor_child_environment, cursor_launch_jitter_ms, cursor_normalize_no_issues,
    effective_review_token_cap, emit_kv, external_auth_verdict, is_cursor_empty_result,
    is_quota_failure, is_transient_infra_failure, json_usage_number,
    plan_capture_cursor_dirty_baseline, plan_cursor_result_write, read_codex_prompt_sentinel,
    render_cap_hit_artifacts, render_codex_prompt_sidecar, render_preflight_bundle,
    render_unknown_dirty_tree, resolve_model_args, review_retry_delay_secs,
};
use std::{
    collections::BTreeMap,
    env,
    ffi::{OsStr, OsString},
    fmt::Write as _,
    fs,
    io::{Read as _, Seek as _, SeekFrom, Write as _},
    num::NonZeroUsize,
    path::{Path, PathBuf},
    process::ExitCode,
    sync::{
        Arc,
        atomic::{AtomicU64, Ordering},
    },
    thread,
    time::{Duration, SystemTime, UNIX_EPOCH},
};

#[cfg(unix)]
#[allow(deprecated)]
use nix::fcntl::{FlockArg, flock};
#[cfg(unix)]
use std::os::{
    fd::AsRawFd as _,
    unix::fs::{OpenOptionsExt as _, PermissionsExt as _},
};

use larch_adapters::runtime::{Cancellation, LarchRuntime};

const REVIEW_USAGE: &str = concat!(
    "usage: cli.py agent launch-review [-h] --tool {codex,cursor} --output OUTPUT --timeout TIMEOUT\n",
    "                                  (--prompt PROMPT | --prompt-file PROMPT_FILE | --agent-file AGENT_FILE)\n",
);
const CODEX_STRICT_PREAMBLE: &str = concat!(
    "STRICT CONSTRAINTS — your role is read-only review. Do not create, edit, ",
    "delete, or overwrite files, and do not run mutating shell or git commands. ",
    "The launcher enforces this with --sandbox read-only (CLI rejects writes).",
);
const CURSOR_STRICT_PREAMBLE: &str = concat!(
    "STRICT CONSTRAINTS — your role is read-only review. Do not create, edit, ",
    "delete, or overwrite files, and do not run mutating shell or git commands.\n",
    "The launcher passes --mode ask to the cursor CLI. Any post-run mutation will ",
    "be detected by the dirty-tree sidecar.",
);
const PYTHON_OUTPUT_LIMIT: usize = 256 * 1024;
const PYTHON_TIMEOUT: Duration = Duration::from_secs(120);
const PYTHON_SHUTDOWN_GRACE: Duration = Duration::from_secs(5);
const PANEL_FIELDS: &[&str] = &[
    "site",
    "phase",
    "round_num",
    "slot",
    "slot_kind",
    "tool",
    "output",
    "prompt_bytes",
    "prompt_tokens",
    "scaffold_bytes",
    "scaffold_tokens",
    "payload_bytes",
    "payload_tokens",
    "agent_file",
    "agent_bytes",
    "agent_tokens",
];
const PANEL_LEGACY_FIELDS: &[&str] = &[
    "site",
    "phase",
    "round_num",
    "slot",
    "slot_kind",
    "tool",
    "output",
    "prompt_bytes",
    "prompt_tokens",
    "agent_file",
    "agent_bytes",
    "agent_tokens",
];
const PANEL_LOCK_ATTEMPTS: usize = 200;
static PART_COUNTER: AtomicU64 = AtomicU64::new(0);

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum ReviewTool {
    Codex,
    Cursor,
}

impl ReviewTool {
    const fn vendor(self) -> VendorProgram {
        match self {
            Self::Codex => VendorProgram::Codex,
            Self::Cursor => VendorProgram::Cursor,
        }
    }

    const fn as_str(self) -> &'static str {
        match self {
            Self::Codex => "codex",
            Self::Cursor => "cursor",
        }
    }
}

#[derive(Clone, Debug, Default)]
struct ReviewArguments {
    tool: Option<ReviewTool>,
    output: String,
    timeout: String,
    prompt: Option<String>,
    prompt_file: String,
    agent_file: String,
    mode: String,
    description_text: String,
    scope_files: String,
    competition_notice: bool,
    competition_notice_file: String,
    diff_file: String,
    commit_count: String,
    plan_file: String,
    feature_file: String,
    session_env_path: String,
    timing_task_kind: String,
    token_budget_cap: String,
    risk: String,
    stderr_sink: String,
    site: String,
    model_role: String,
    default_model: String,
    cursor_model: Option<String>,
    difficulty: String,
}

impl ReviewArguments {
    fn selected_session_env_path(&self) -> String {
        if self.session_env_path.is_empty() {
            env::var("SESSION_ENV_PATH").unwrap_or_default()
        } else {
            self.session_env_path.clone()
        }
    }

    fn timing_kind(&self, tool: ReviewTool) -> String {
        if self.timing_task_kind.is_empty() || self.timing_task_kind.starts_with("--") {
            format!("{}-review", tool.as_str())
        } else {
            self.timing_task_kind.clone()
        }
    }
}

enum ReviewParse {
    Help,
    Error(String),
    Parsed(Box<ReviewArguments>),
}

/// Run `agent launch-review` with its legacy argument and artifact contract.
pub fn launch_review(raw: &AgentRawArguments) -> ExitCode {
    let args = match parse_arguments(&raw.arguments) {
        ReviewParse::Help => {
            eprint!("{REVIEW_USAGE}");
            return ExitCode::SUCCESS;
        }
        ReviewParse::Error(error) => {
            eprintln!("cli.py agent launch-review: error: {error}");
            return ExitCode::from(2);
        }
        ReviewParse::Parsed(args) => args,
    };
    let Some(tool) = args.tool else {
        eprintln!(
            "cli.py agent launch-review: error: the following arguments are required: --tool"
        );
        return ExitCode::from(2);
    };
    if let Err((code, message)) = validate_arguments(&args, tool) {
        eprintln!("{message}");
        return ExitCode::from(code);
    }
    let session = ReviewSession::resolve(&args);
    let artifacts = match ReviewArtifacts::create(&args.output, tool == ReviewTool::Cursor) {
        Ok(value) => value,
        Err(error) => {
            eprintln!("agent launch-review: {error}");
            return ExitCode::from(2);
        }
    };

    let cap = effective_review_token_cap(
        (!args.token_budget_cap.is_empty()).then_some(args.token_budget_cap.as_str()),
        env::var(ENV_TOKEN_BUDGET_CAP_REVIEW).ok().as_deref(),
    );
    if let Some(cap) = cap
        && let Some(stdout) = check_token_budget_cap(&session, cap, &args.timing_kind(tool))
    {
        write_cap_hit(&artifacts, cap, &stdout);
        return ExitCode::SUCCESS;
    }

    let (prompt, payload_bytes) = match resolve_prompt(&args, tool, &artifacts, &session) {
        Ok(value) => value,
        Err((code, message)) => {
            eprintln!("{message}");
            return ExitCode::from(code);
        }
    };
    append_panel_prompt_size(&args, &artifacts, &prompt, payload_bytes);
    let rc = match tool {
        ReviewTool::Codex => launch_codex(&args, &artifacts, &session, &prompt),
        ReviewTool::Cursor => launch_cursor(&args, &artifacts, &session, &prompt),
    };
    ExitCode::from(u8::try_from(rc).unwrap_or(1))
}

fn parse_arguments(arguments: &[OsString]) -> ReviewParse {
    let mut args = ReviewArguments {
        timing_task_kind: env::var("LARCH_TIMING_TASK_KIND").unwrap_or_default(),
        site: "review Step 2".to_owned(),
        model_role: "default".to_owned(),
        ..ReviewArguments::default()
    };
    let mut index = 0;
    while index < arguments.len() {
        let value = arguments[index].to_string_lossy();
        if value == "--help" || value == "-h" {
            return ReviewParse::Help;
        }
        if value == "--competition-notice" {
            args.competition_notice = true;
            index += 1;
            continue;
        }
        let (flag, inline) = split_inline_option(&value);
        let parameter = match review_option_value(arguments, &mut index, flag, inline, &value) {
            Ok(value) => value,
            Err(error) => return ReviewParse::Error(error),
        };
        if let Err(error) = set_review_option(&mut args, flag, parameter) {
            return ReviewParse::Error(error);
        }
        index += 1;
    }
    if args.output.is_empty() || args.timeout.is_empty() {
        return ReviewParse::Error(
            "the following arguments are required: --output, --timeout".to_owned(),
        );
    }
    let prompt_sources = usize::from(args.prompt.is_some())
        + usize::from(!args.prompt_file.is_empty())
        + usize::from(!args.agent_file.is_empty());
    if prompt_sources != 1 {
        return ReviewParse::Error(
            "one of the arguments --prompt --prompt-file --agent-file is required".to_owned(),
        );
    }
    ReviewParse::Parsed(Box::new(args))
}

fn review_option_value(
    arguments: &[OsString],
    index: &mut usize,
    flag: &str,
    inline: Option<&str>,
    original: &str,
) -> Result<String, String> {
    if !review_option_requires_value(flag) {
        return Err(format!("unrecognized arguments: {original}"));
    }
    if let Some(value) = inline {
        return Ok(value.to_owned());
    }
    let Some(next) = arguments.get(*index + 1) else {
        return Err(format!("argument {flag}: expected one argument"));
    };
    *index += 1;
    Ok(next.to_string_lossy().into_owned())
}

fn review_option_requires_value(flag: &str) -> bool {
    matches!(
        flag,
        "--tool"
            | "--output"
            | "--timeout"
            | "--prompt"
            | "--prompt-file"
            | "--agent-file"
            | "--mode"
            | "--description-text"
            | "--scope-files"
            | "--competition-notice-file"
            | "--diff-file"
            | "--commit-count"
            | "--plan-file"
            | "--feature-file"
            | "--session-env-path"
            | "--timing-task-kind"
            | "--token-budget-cap"
            | "--risk"
            | "--stderr-sink"
            | "--site"
            | "--model-role"
            | "--default-model"
            | "--cursor-model"
            | "--difficulty"
    )
}

fn set_review_option(args: &mut ReviewArguments, flag: &str, value: String) -> Result<(), String> {
    match flag {
        "--tool" => {
            args.tool = match value.as_str() {
                "codex" => Some(ReviewTool::Codex),
                "cursor" => Some(ReviewTool::Cursor),
                _ => {
                    return Err(format!(
                        "argument --tool: invalid choice: '{value}' (choose from 'codex', 'cursor')"
                    ));
                }
            };
        }
        "--output" => args.output = value,
        "--timeout" => args.timeout = value,
        "--prompt" => args.prompt = Some(value),
        "--prompt-file" => args.prompt_file = value,
        "--agent-file" => args.agent_file = value,
        "--mode" => args.mode = value,
        "--description-text" => args.description_text = value,
        "--scope-files" => args.scope_files = value,
        "--competition-notice-file" => args.competition_notice_file = value,
        "--diff-file" => args.diff_file = value,
        "--commit-count" => args.commit_count = value,
        "--plan-file" => args.plan_file = value,
        "--feature-file" => args.feature_file = value,
        "--session-env-path" => args.session_env_path = value,
        "--timing-task-kind" => args.timing_task_kind = value,
        "--token-budget-cap" => args.token_budget_cap = value,
        "--risk" => args.risk = value,
        "--stderr-sink" => args.stderr_sink = value,
        "--site" => args.site = value,
        "--model-role" => args.model_role = value,
        "--default-model" => args.default_model = value,
        "--cursor-model" => args.cursor_model = Some(value),
        "--difficulty" => args.difficulty = value,
        _ => unreachable!("option accepted by review_option_requires_value"),
    }
    Ok(())
}

fn validate_arguments(args: &ReviewArguments, tool: ReviewTool) -> Result<(), (u8, String)> {
    if !valid_meta_path(OsStr::new(&args.output)) {
        return Err((
            1,
            "ERROR: --output contains unsupported characters".to_owned(),
        ));
    }
    if !args.stderr_sink.is_empty() && !valid_meta_path(OsStr::new(&args.stderr_sink)) {
        return Err((
            1,
            "ERROR: --stderr-sink contains unsupported characters".to_owned(),
        ));
    }
    if contains_control(&args.risk) {
        return Err((
            2,
            "agent launch-review: --risk must not contain control characters".to_owned(),
        ));
    }
    if contains_control(&args.timing_task_kind) {
        return Err((
            2,
            "agent launch-review: --timing-task-kind must not contain control characters"
                .to_owned(),
        ));
    }
    if parse_positive(&args.timeout).is_none() {
        let message = if tool == ReviewTool::Codex {
            format!(
                "agent launch-review: --timeout must be a positive integer (seconds), got '{}'",
                args.timeout
            )
        } else if args.timeout.bytes().all(|byte| byte.is_ascii_digit()) {
            "agent launch-review: --timeout must be >= 1".to_owned()
        } else {
            "agent launch-review: --timeout must be a positive integer".to_owned()
        };
        return Err((2, message));
    }
    if !args.timing_task_kind.is_empty()
        && (args.timing_task_kind.trim().is_empty() || args.timing_task_kind.starts_with("--"))
    {
        return Err((
            2,
            "agent launch-review: --timing-task-kind requires a non-empty, non-flag-like value"
                .to_owned(),
        ));
    }
    if !args.token_budget_cap.is_empty() && parse_positive(&args.token_budget_cap).is_none() {
        return Err((
            2,
            "agent launch-review: --token-budget-cap requires a positive integer".to_owned(),
        ));
    }
    if let Some(cursor_model) = &args.cursor_model {
        if tool != ReviewTool::Cursor {
            return Err((
                2,
                "agent launch-review: --cursor-model is only valid with --tool cursor".to_owned(),
            ));
        }
        if cursor_model.trim().is_empty() {
            return Err((
                2,
                "agent launch-review: --cursor-model requires a non-empty value".to_owned(),
            ));
        }
        if contains_control(cursor_model) {
            return Err((
                2,
                "agent launch-review: --cursor-model must not contain control characters"
                    .to_owned(),
            ));
        }
    }
    if args.site.trim().is_empty() || args.site.starts_with("--") {
        return Err((
            2,
            "agent launch-review: --site requires a non-empty, non-flag-like value".to_owned(),
        ));
    }
    if contains_control(&args.site) {
        return Err((
            2,
            "agent launch-review: --site must not contain control characters".to_owned(),
        ));
    }
    if !matches!(
        args.model_role.as_str(),
        "default" | "review" | "vote" | "fix"
    ) {
        return Err((
            2,
            format!(
                "argument --model-role: invalid choice: '{}' (choose from 'default', 'review', 'vote', 'fix')",
                args.model_role
            ),
        ));
    }
    Ok(())
}

fn contains_control(value: &str) -> bool {
    value.chars().any(char::is_control)
}

fn parse_positive(value: &str) -> Option<u64> {
    parse_uint(value).filter(|value| *value > 0)
}

struct ReviewArtifacts {
    root: TemporaryRoot,
    paths: LauncherArtifactPaths,
    output_raw: String,
}

impl ReviewArtifacts {
    fn create(output_raw: &str, create_parent: bool) -> Result<Self, String> {
        let cwd = env::current_dir().map_err(|error| error.to_string())?;
        let requested = PathBuf::from(output_raw);
        let output = if requested.is_absolute() {
            requested
        } else {
            cwd.join(requested)
        };
        let parent = output
            .parent()
            .ok_or_else(|| "--output has no parent directory".to_owned())?;
        if create_parent {
            ensure_directory_chain(parent).map_err(|error| error.to_string())?;
        } else if !parent.is_dir() {
            return Err(format!(
                "output parent directory does not exist: {}",
                parent.display()
            ));
        }
        let root = TemporaryRoot::resolve(Some(parent)).map_err(|error| error.to_string())?;
        let name = output
            .file_name()
            .ok_or_else(|| "--output must name a file".to_owned())?;
        let output = root
            .confine(root.path().join(name), PathIntent::Write)
            .map_err(|error| error.to_string())?
            .path()
            .to_path_buf();
        Ok(Self {
            root,
            paths: LauncherArtifactPaths::new(output),
            output_raw: output_raw.to_owned(),
        })
    }

    fn output(&self) -> &Path {
        self.paths.output()
    }

    fn path(&self, kind: LauncherArtifactKind) -> PathBuf {
        self.paths.path(kind)
    }

    fn write(&self, path: &Path, text: &str) {
        let _ignored = atomic_write_utf8_in(&self.root, path, text, true, 0o600);
    }

    fn write_bytes(&self, path: &Path, bytes: &[u8]) {
        let Ok(target) = self.root.confine(path, PathIntent::Write) else {
            return;
        };
        let _ignored = larch_adapters::atomic_write_bytes(&target, bytes, 0o600);
    }

    fn append(&self, path: &Path, text: &str) {
        let existing = self.read(path);
        self.write(path, &format!("{existing}{text}"));
    }

    fn read(&self, path: &Path) -> String {
        self.root
            .confine(path, PathIntent::Read)
            .ok()
            .and_then(|target| {
                target
                    .revalidate()
                    .ok()
                    .and_then(|()| read_optional_utf8_lossy(target.path()).ok())
            })
            .flatten()
            .unwrap_or_default()
    }

    fn read_bytes(&self, path: &Path) -> Option<Vec<u8>> {
        let target = self.root.confine(path, PathIntent::Read).ok()?;
        target.revalidate().ok()?;
        fs::read(target.path()).ok()
    }

    fn remove(&self, path: &Path) {
        let _ignored = self
            .root
            .confine(path, PathIntent::Cleanup)
            .ok()
            .and_then(|target| remove_optional_file(target.path()).ok());
    }

    fn promote_inner_done(&self) {
        let inner = self.path(LauncherArtifactKind::InnerDone);
        let done = self.path(LauncherArtifactKind::Done);
        let Ok(source) = self.root.confine(&inner, PathIntent::Write) else {
            return;
        };
        let Ok(destination) = self.root.confine(&done, PathIntent::Write) else {
            return;
        };
        let _ignored = rename_same_directory(&source, &destination);
    }
}

#[derive(Clone, Debug, Default)]
struct ReviewSession {
    token_session_id: String,
    claude_source_file: String,
    child_environment: Vec<(ChildEnvironment, OsString)>,
}

impl ReviewSession {
    fn resolve(args: &ReviewArguments) -> Self {
        let mut session = Self::default();
        for name in ["IMPLEMENT_TMPDIR", "DESIGN_TMPDIR"] {
            if let Some(candidate) = session_file_path(name, "session-id") {
                let token = fs::read(&candidate)
                    .map(|bytes| String::from_utf8_lossy(&bytes).into_owned())
                    .unwrap_or_default()
                    .replace(['\r', '\n'], "");
                if !token.is_empty() {
                    session.token_session_id = token;
                    break;
                }
            }
        }
        if let Some(source) = session_file_path("IMPLEMENT_TMPDIR", "claude-source.env") {
            session.claude_source_file = source.display().to_string();
        }
        let inherited = [
            (ChildEnvironment::ImplementTmpDir, "IMPLEMENT_TMPDIR"),
            (ChildEnvironment::DesignTmpDir, "DESIGN_TMPDIR"),
            (ChildEnvironment::SessionEnvPath, "SESSION_ENV_PATH"),
            (ChildEnvironment::LarchTokenLedger, "LARCH_TOKEN_LEDGER"),
            (ChildEnvironment::LarchTimingLedger, "LARCH_TIMING_LEDGER"),
            (ChildEnvironment::LarchTimingSkill, "LARCH_TIMING_SKILL"),
        ];
        for (key, name) in inherited {
            if let Some(value) = env::var_os(name).filter(|value| !value.is_empty()) {
                session.child_environment.push((key, value));
            }
        }
        let selected_session_env = args.selected_session_env_path();
        if !selected_session_env.is_empty() {
            session
                .child_environment
                .retain(|(key, _)| *key != ChildEnvironment::SessionEnvPath);
            session.child_environment.push((
                ChildEnvironment::SessionEnvPath,
                OsString::from(selected_session_env),
            ));
        }
        if !session.token_session_id.is_empty() {
            session.child_environment.push((
                ChildEnvironment::LarchTokenSessionId,
                OsString::from(&session.token_session_id),
            ));
        }
        if !session.claude_source_file.is_empty() {
            session.child_environment.push((
                ChildEnvironment::LarchClaudeSourceFile,
                OsString::from(&session.claude_source_file),
            ));
        }
        session
    }
}

/// Return a nonempty, regular session file only when it stays below a trusted
/// temporary root. These files bridge into the Python compatibility verbs, so
/// unlike arbitrary CLI inputs they must never follow a symlink.
fn session_file_path(root_name: &str, file_name: &str) -> Option<PathBuf> {
    let root_path = env::var_os(root_name).filter(|value| !value.is_empty())?;
    let root = TemporaryRoot::resolve(Some(Path::new(&root_path))).ok()?;
    let target = root
        .confine(root.path().join(file_name), PathIntent::Read)
        .ok()?;
    target.revalidate().ok()?;
    fs::metadata(target.path())
        .ok()
        .filter(|metadata| metadata.len() > 0)
        .map(|_| target.path().to_path_buf())
}

fn regular_nonempty(path: &Path) -> bool {
    fs::metadata(path).is_ok_and(|metadata| metadata.is_file() && metadata.len() > 0)
}

/// Validate an existing diagnostic carrier without following a parent or leaf
/// symlink. A caller sink can become part of a redacted failure report, so it
/// must not turn diagnostic publication into an arbitrary read.
fn safe_existing_diagnostic_path(path: &Path) -> Option<PathBuf> {
    let absolute = if path.is_absolute() {
        path.to_path_buf()
    } else {
        env::current_dir().ok()?.join(path)
    };
    let parent = absolute.parent()?;
    let root = TemporaryRoot::resolve(Some(parent)).ok()?;
    let name = absolute.file_name()?;
    let target = root
        .confine(root.path().join(name), PathIntent::Read)
        .ok()?;
    target.revalidate().ok()?;
    Some(target.path().to_path_buf())
}

fn read_safe_diagnostic(path: &Path) -> Option<String> {
    let path = safe_existing_diagnostic_path(path)?;
    let bytes = fs::read(path).ok()?;
    (!bytes.is_empty()).then(|| String::from_utf8_lossy(&bytes).into_owned())
}

fn check_token_budget_cap(session: &ReviewSession, cap: u64, step: &str) -> Option<String> {
    let Some(output) = run_python(
        session,
        [
            OsString::from("token"),
            OsString::from("check-budget"),
            OsString::from("--cap"),
            OsString::from(cap.to_string()),
            OsString::from("--step"),
            OsString::from(step),
        ],
    ) else {
        eprintln!("agent launch-review: token budget check could not run");
        return None;
    };
    let stdout = String::from_utf8_lossy(output.stdout()).into_owned();
    if !output.status().success() {
        let stderr = String::from_utf8_lossy(output.stderr()).trim().to_owned();
        eprintln!(
            "agent launch-review: token budget check failed{}",
            if stderr.is_empty() {
                String::new()
            } else {
                format!(": {stderr}")
            }
        );
        return None;
    }
    stdout
        .split_ascii_whitespace()
        .any(|field| field == "STATUS=cap_hit")
        .then_some(stdout)
}

fn write_cap_hit(artifacts: &ReviewArtifacts, cap: u64, stdout: &str) {
    let implement_tmpdir = env::var_os("IMPLEMENT_TMPDIR").map(PathBuf::from);
    let rendered = render_cap_hit_artifacts(cap, stdout, implement_tmpdir.as_deref());
    eprintln!("{}", rendered.warning);
    artifacts.write(artifacts.output(), &rendered.output);
    artifacts.write(
        &suffixed_path(artifacts.output(), ".cap-hit"),
        &rendered.cap_hit,
    );
    if let (Some(root_path), Some(text)) = (implement_tmpdir, rendered.step_budget_env)
        && let Ok(root) = TemporaryRoot::resolve(Some(&root_path))
    {
        let target = root.path().join("step-budget-cap-hit.env");
        let _ignored = atomic_write_utf8_in(&root, &target, &text, true, 0o600);
    }
    artifacts.write(&artifacts.path(LauncherArtifactKind::Done), &rendered.done);
}

fn resolve_prompt(
    args: &ReviewArguments,
    tool: ReviewTool,
    artifacts: &ReviewArtifacts,
    session: &ReviewSession,
) -> Result<(String, u64), (u8, String)> {
    if let Some(prompt) = &args.prompt {
        return Ok((prompt.clone(), 0));
    }
    if !args.prompt_file.is_empty() {
        let raw = fs::read(&args.prompt_file).map_err(|_| {
            (
                1,
                format!(
                    "agent launch-review: failed to read --prompt-file {}",
                    args.prompt_file
                ),
            )
        })?;
        let text = String::from_utf8_lossy(&raw).into_owned();
        let payload_bytes = panel_payload_bytes();
        if tool == ReviewTool::Codex {
            let renderer = PythonSpecialistRenderer { session };
            match read_codex_prompt_sentinel(&text, &renderer) {
                CodexPromptSentinelRead::Ok { prompt } => return Ok((prompt, payload_bytes)),
                CodexPromptSentinelRead::Failed { message } => return Err((1, message)),
                CodexPromptSentinelRead::NotSentinel => {}
            }
        }
        return Ok((text, payload_bytes));
    }
    render_specialist_prompt(args, artifacts, session)
}

fn render_specialist_prompt(
    args: &ReviewArguments,
    artifacts: &ReviewArtifacts,
    session: &ReviewSession,
) -> Result<(String, u64), (u8, String)> {
    let unique = PART_COUNTER.fetch_add(1, Ordering::Relaxed);
    let payload = artifacts.root.path().join(format!(
        ".larch-render-payload.{}.{}",
        std::process::id(),
        unique
    ));
    let mut render_arguments = vec![OsString::from("render"), OsString::from("specialist")];
    let mut normal_arguments = normal_specialist_render_args(args, artifacts);
    if let Some(diff_mode) = specialist_diff_mode(&args.mode, &args.diff_file).map_err(|()| {
        (
            1,
            "render-specialist-prompt.sh: diff classification failed".to_owned(),
        )
    })? {
        normal_arguments.extend(["--diff-mode".to_owned(), diff_mode]);
    }
    render_arguments.extend(normal_arguments.into_iter().map(OsString::from));
    render_arguments.extend([
        OsString::from("--payload-bytes-output"),
        payload.as_os_str().to_owned(),
    ]);
    let result = run_python(session, render_arguments).ok_or_else(|| {
        (
            1,
            "agent launch-review: render specialist failed".to_owned(),
        )
    })?;
    let payload_bytes = artifacts
        .read(&payload)
        .trim()
        .parse::<u64>()
        .ok()
        .unwrap_or(0);
    artifacts.remove(&payload);
    let stdout = String::from_utf8_lossy(result.stdout()).into_owned();
    if !result.status().success() {
        let stderr = String::from_utf8_lossy(result.stderr()).trim().to_owned();
        return Err((
            u8::try_from(result.status().code().unwrap_or(1)).unwrap_or(1),
            if !stderr.is_empty() {
                stderr
            } else if !stdout.is_empty() {
                stdout
            } else {
                "agent launch-review: render specialist failed".to_owned()
            },
        ));
    }
    Ok((stdout, payload_bytes))
}

fn normal_specialist_render_args(
    args: &ReviewArguments,
    artifacts: &ReviewArtifacts,
) -> Vec<String> {
    let mut render = vec![
        "--agent-file".to_owned(),
        args.agent_file.clone(),
        "--mode".to_owned(),
        args.mode.clone(),
    ];
    for (value, flag) in [
        (&args.description_text, "--description-text"),
        (&args.scope_files, "--scope-files"),
        (&args.competition_notice_file, "--competition-notice-file"),
        (&args.diff_file, "--diff-file"),
        (&args.commit_count, "--commit-count"),
        (&args.plan_file, "--plan-file"),
        (&args.feature_file, "--feature-file"),
        (&args.difficulty, "--difficulty"),
    ] {
        if !value.is_empty() {
            render.extend([flag.to_owned(), value.clone()]);
        }
    }
    if args.competition_notice {
        render.push("--competition-notice".to_owned());
    }
    let session_env = args.selected_session_env_path();
    let ledger = findings_ledger_path(
        artifacts
            .output()
            .parent()
            .unwrap_or_else(|| Path::new(".")),
        &session_env,
    );
    render.extend([
        "--findings-ledger-file".to_owned(),
        ledger.display().to_string(),
    ]);
    if !session_env.is_empty() {
        render.extend(["--session-env-path".to_owned(), session_env]);
    }
    render
}

struct PythonSpecialistRenderer<'a> {
    session: &'a ReviewSession,
}

impl SpecialistRenderPort for PythonSpecialistRenderer<'_> {
    fn render_specialist(&self, sentinel: &BTreeMap<String, String>) -> (i32, String) {
        let mut render_arguments = vec![OsString::from("render"), OsString::from("specialist")];
        render_arguments.extend(
            sentinel_specialist_render_args(sentinel)
                .into_iter()
                .map(OsString::from),
        );
        match specialist_diff_mode(
            sentinel.get("MODE").map_or("", String::as_str),
            sentinel.get("DIFF_FILE").map_or("", String::as_str),
        ) {
            Ok(Some(diff_mode)) => {
                render_arguments.extend([OsString::from("--diff-mode"), diff_mode.into()]);
            }
            Ok(None) => {}
            Err(()) => {
                return (
                    1,
                    "render-specialist-prompt.sh: diff classification failed".to_owned(),
                );
            }
        }
        let Some(result) = run_python(self.session, render_arguments) else {
            return (
                1,
                "agent launch-review: render specialist failed".to_owned(),
            );
        };
        let rc = result.status().code().unwrap_or(1);
        if rc == 0 {
            return (0, String::from_utf8_lossy(result.stdout()).into_owned());
        }
        let stderr = String::from_utf8_lossy(result.stderr()).trim().to_owned();
        let stdout = String::from_utf8_lossy(result.stdout()).into_owned();
        (rc, if stderr.is_empty() { stdout } else { stderr })
    }
}

fn specialist_diff_mode(mode: &str, diff_file: &str) -> Result<Option<String>, ()> {
    if mode != "diff" || diff_file.is_empty() {
        return Ok(None);
    }
    let generated = generated_paths().map_err(|_| ())?;
    let diff = read_optional_utf8_lossy(Path::new(diff_file))
        .map_err(|_| ())?
        .ok_or(())?;
    Ok(Some(classify_diff(&diff, &generated).as_str().to_owned()))
}

fn sentinel_specialist_render_args(sentinel: &BTreeMap<String, String>) -> Vec<String> {
    let mut render = vec![
        "--agent-file".to_owned(),
        sentinel.get("AGENT_FILE").cloned().unwrap_or_default(),
        "--mode".to_owned(),
        sentinel.get("MODE").cloned().unwrap_or_default(),
    ];
    for (key, flag) in [
        ("SCOPE_FILES", "--scope-files"),
        ("COMPETITION_NOTICE_FILE", "--competition-notice-file"),
        ("DIFF_FILE", "--diff-file"),
        ("COMMIT_COUNT", "--commit-count"),
        ("PLAN_FILE", "--plan-file"),
        ("FEATURE_FILE", "--feature-file"),
        ("FINDINGS_LEDGER_FILE", "--findings-ledger-file"),
        ("SESSION_ENV_PATH", "--session-env-path"),
        ("DIFFICULTY", "--difficulty"),
    ] {
        if let Some(value) = sentinel.get(key).filter(|value| !value.is_empty()) {
            render.extend([flag.to_owned(), value.clone()]);
        }
    }
    if sentinel
        .get("COMPETITION_NOTICE")
        .is_some_and(|value| value == "true")
    {
        render.push("--competition-notice".to_owned());
    }
    render
}

/// Resolve the cross-round findings ledger one review session writes.
///
/// A `round-N` tmpdir nested directly below its session root shares that
/// root's ledger; every other review root owns its own.
pub fn findings_ledger_path(review_root: &Path, session_env_path: &str) -> PathBuf {
    let review_real = fs::canonicalize(review_root).unwrap_or_else(|_| review_root.to_path_buf());
    let parent = review_real.parent().unwrap_or(&review_real);
    let nested = review_real
        .file_name()
        .and_then(OsStr::to_str)
        .is_some_and(|name| {
            name.strip_prefix("round-").is_some_and(|number| {
                !number.is_empty() && number.bytes().all(|byte| byte.is_ascii_digit())
            })
        });
    let matching_parent = |raw: Option<OsString>| {
        raw.map(PathBuf::from)
            .and_then(|path| fs::canonicalize(path).ok())
            .is_some_and(|path| path == parent)
    };
    let session_parent = (!session_env_path.is_empty())
        .then(|| {
            PathBuf::from(session_env_path)
                .parent()
                .map(Path::to_path_buf)
        })
        .flatten()
        .and_then(|path| fs::canonicalize(path).ok())
        .is_some_and(|path| path == parent);
    let root = if nested && (matching_parent(env::var_os("IMPLEMENT_TMPDIR")) || session_parent) {
        parent.to_path_buf()
    } else {
        review_real
    };
    root.join("findings-ledger.tsv")
}

#[allow(clippy::too_many_lines)] // Preflight and terminal artifacts are one ordered launch lifecycle.
fn launch_codex(
    args: &ReviewArguments,
    artifacts: &ReviewArtifacts,
    session: &ReviewSession,
    prompt: &str,
) -> i32 {
    if CODEX_STRICT_PREAMBLE.contains("'''") {
        eprintln!(
            "agent launch-review: hardening preamble contains TOML triple-single-quote delimiter"
        );
        return 2;
    }
    let timing_kind = args.timing_kind(ReviewTool::Codex);
    let prompt_sidecar = artifacts.path(LauncherArtifactKind::Prompt);
    let session_env = args.selected_session_env_path();
    let sidecar_body = render_codex_prompt_sidecar(
        prompt,
        &CodexPromptSidecarArgs {
            agent_file: &args.agent_file,
            description_text: &args.description_text,
            mode: &args.mode,
            scope_files: &args.scope_files,
            competition_notice: args.competition_notice,
            competition_notice_file: &args.competition_notice_file,
            diff_file: &args.diff_file,
            commit_count: &args.commit_count,
            plan_file: &args.plan_file,
            feature_file: &args.feature_file,
            session_env_path: &session_env,
            findings_ledger_file: &findings_ledger_path(
                artifacts
                    .output()
                    .parent()
                    .unwrap_or_else(|| Path::new(".")),
                &session_env,
            )
            .display()
            .to_string(),
            difficulty: &args.difficulty,
        },
    );
    artifacts.write(&prompt_sidecar, &sidecar_body);
    let start = epoch_seconds();
    let model_args = match resolve_model_args(
        ModelTool::Codex,
        true,
        &args.default_model,
        CodexModelRole::parse(&args.model_role).unwrap_or(CodexModelRole::Default),
        &env::vars().collect(),
    ) {
        Ok(resolved) => {
            if !resolved.warning().is_empty() {
                eprintln!("agent model-args: {}", resolved.warning());
            }
            resolved.argv().to_vec()
        }
        Err(error) => {
            record_timing(
                session,
                VendorProgram::Codex,
                &timing_kind,
                start,
                artifacts.output(),
                1,
            );
            preflight_failure(
                args,
                artifacts,
                ReviewTool::Codex,
                &format!("agent model-args failed (exit 1): {error}"),
                1,
                false,
                Some(&render_unknown_dirty_tree(
                    false,
                    "model-args-preflight-no-agent-ran",
                )),
            );
            return 1;
        }
    };
    let Some(temporary_root) = system_temporary_root() else {
        preflight_failure(
            args,
            artifacts,
            ReviewTool::Codex,
            "codex auth setup failed: could not resolve temporary root",
            1,
            false,
            None,
        );
        return 0;
    };
    let instructions_dir = match larch_adapters::SecureTempDir::create(
        &temporary_root,
        "larch-codex-review-instructions-",
    ) {
        Ok(value) => value,
        Err(error) => {
            preflight_failure(
                args,
                artifacts,
                ReviewTool::Codex,
                &format!("codex auth setup failed: {error}"),
                1,
                false,
                None,
            );
            return 0;
        }
    };
    let instructions = instructions_dir.path().join("trusted-instructions.txt");
    if fs::write(&instructions, CODEX_STRICT_PREAMBLE).is_err() {
        preflight_failure(
            args,
            artifacts,
            ReviewTool::Codex,
            "codex auth setup failed: could not write trusted instructions",
            1,
            false,
            None,
        );
        return 0;
    }
    let home = env::var_os("HOME").map_or_else(env::temp_dir, PathBuf::from);
    let auth = codex_env_auth_from_key(env::var("OPENAI_API_KEY").ok().as_deref());
    let context = match CodexHomeContext::create(&temporary_root, &home, Some(&instructions), auth)
    {
        Ok(value) => value,
        Err(error) => {
            preflight_failure(
                args,
                artifacts,
                ReviewTool::Codex,
                &error.to_string(),
                error.exit_code(),
                false,
                None,
            );
            return 0;
        }
    };
    if context.path().starts_with(artifacts.root.path()) {
        eprintln!(
            "agent launch-review: CODEX_HOME inside output tree: {}",
            context.path().display()
        );
        return 2;
    }
    let workdir = review_workdir();
    let mut request = VendorLaunchRequest::new(
        workdir.display().to_string(),
        artifacts.output().display().to_string(),
        prompt,
    );
    request.timing_task_kind.clone_from(&timing_kind);
    request.model_args = model_args;
    request.add_dirs = vec![artifacts.root.path().display().to_string()];
    request.codex_env_auth = auth;
    let command = match CODEX_DESCRIPTOR.build_argv("read-only", &request) {
        Ok(arguments) => arguments.full_argv(),
        Err(error) => {
            record_timing(
                session,
                VendorProgram::Codex,
                &timing_kind,
                start,
                artifacts.output(),
                1,
            );
            preflight_failure(
                args,
                artifacts,
                ReviewTool::Codex,
                &format!("agent model-args failed (exit 1): {error}"),
                1,
                false,
                Some(&render_unknown_dirty_tree(
                    false,
                    "model-args-preflight-no-agent-ran",
                )),
            );
            return 1;
        }
    };
    let mut child_env = session.child_environment.clone();
    child_env.push(context.child_environment());
    let routed_streams = ExternalAgentRouting::Streams {
        stdout: Some(artifacts.path(LauncherArtifactKind::Events)),
        stderr: Some(artifacts.path(LauncherArtifactKind::Sidecar)),
    };
    let retry = run_review_retries(&ReviewRetryRequest {
        tool: ReviewTool::Codex,
        artifacts,
        args,
        command: &command,
        environment: &child_env,
        working_directory: &workdir,
        capture_stdout_only: false,
        routed_streams: Some(&routed_streams),
    });
    let events = artifacts.path(LauncherArtifactKind::Events);
    if !regular_nonempty(&events) {
        artifacts.write(&events, "{}\n");
    }
    let sidecar = artifacts.path(LauncherArtifactKind::Sidecar);
    if retry.exit_code != 0 {
        append_launch_failure(args, artifacts, session, ReviewTool::Codex, retry);
    } else if sidecar.is_file() {
        artifacts.append(
            &sidecar,
            "codex-status: ok (no stderr emitted during agent run)\n",
        );
    }
    append_outer_meta(args, artifacts, &timing_kind, None);
    record_timing(
        session,
        VendorProgram::Codex,
        &timing_kind,
        start,
        artifacts.output(),
        retry.exit_code,
    );
    record_codex_usage(artifacts, session, extracted_model(&request.model_args));
    artifacts.write(
        &artifacts.path(LauncherArtifactKind::DirtyTree),
        &larch_core::render_clean_readonly_dirty_tree(),
    );
    artifacts.promote_inner_done();
    emit_launcher_result(
        artifacts,
        ReviewTool::Codex,
        retry.exit_code,
        &args.stderr_sink,
    );
    retry.exit_code
}

#[allow(clippy::too_many_lines)] // Preflight and terminal artifacts are one ordered launch lifecycle.
fn launch_cursor(
    args: &ReviewArguments,
    artifacts: &ReviewArtifacts,
    session: &ReviewSession,
    original_prompt: &str,
) -> i32 {
    let timing_kind = args.timing_kind(ReviewTool::Cursor);
    let start = epoch_seconds();
    let prompt_sidecar = artifacts.path(LauncherArtifactKind::Prompt);
    artifacts.write(&prompt_sidecar, original_prompt);
    let model_args = match crate::launcher_support::cursor_model_argv(args.cursor_model.as_deref())
    {
        Ok(resolved_model_argv) => resolved_model_argv,
        Err(error) => {
            record_timing(
                session,
                VendorProgram::Cursor,
                &timing_kind,
                start,
                artifacts.output(),
                1,
            );
            preflight_failure(
                args,
                artifacts,
                ReviewTool::Cursor,
                &format!("cursor_launcher_load_model_args failed (exit 1): {error}"),
                1,
                true,
                Some(&render_unknown_dirty_tree(
                    false,
                    "model-args-preflight-no-agent-ran",
                )),
            );
            return 1;
        }
    };
    let baseline_plan = plan_capture_cursor_dirty_baseline(&artifacts.paths);
    for path in baseline_plan.unlink {
        artifacts.remove(&path);
    }
    let workdir = review_workdir();
    let _captured = dirty_tree_commands::capture_untracked_baseline_for_review(
        &artifacts.root,
        &baseline_plan.baseline,
        &workdir,
    );
    artifacts.write(&artifacts.path(LauncherArtifactKind::Sidecar), "");
    let Some(temporary_root) = system_temporary_root() else {
        preflight_failure(
            args,
            artifacts,
            ReviewTool::Cursor,
            "cursor auth setup failed: could not resolve temporary root",
            1,
            true,
            None,
        );
        return 1;
    };
    let Some(lock_root) = shared_startup_lock_root() else {
        preflight_failure(
            args,
            artifacts,
            ReviewTool::Cursor,
            "cursor auth setup failed: could not resolve shared startup lock",
            1,
            true,
            None,
        );
        return 1;
    };
    let Some(startup_lock) = startup_lock_config(VendorProgram::Cursor) else {
        preflight_failure(
            args,
            artifacts,
            ReviewTool::Cursor,
            "cursor auth setup failed: USER is unusable as a startup-lock path component",
            1,
            true,
            None,
        );
        return 1;
    };
    let config = CursorPreflightConfig::from_values(
        platform_name(),
        env::var("CURSOR_API_KEY").ok().as_deref(),
        "agent launch-review",
    );
    let runner = TokioProcessRunner::new(Arc::new(NoopProcessObserver));
    let cancellation = Cancellation::new();
    let Ok(runtime) = LarchRuntime::current_thread() else {
        preflight_failure(
            args,
            artifacts,
            ReviewTool::Cursor,
            "cursor auth setup failed: could not start local runtime",
            1,
            true,
            None,
        );
        return 1;
    };
    let context = VendorAuthContext {
        temporary_root: &lock_root,
        startup_lock: &startup_lock,
        working_directory: &workdir,
    };
    let verdict = runtime.block_on(cursor_auth_preflight(
        &runner,
        &config,
        context,
        &cancellation,
    ));
    if !verdict.ok {
        eprintln!("{}", verdict.message);
        preflight_failure(
            args,
            artifacts,
            ReviewTool::Cursor,
            "cursor-auth-preflight: CURSOR_API_KEY unset/empty and cursor-user keychain entry missing on Darwin; see docs/installation-and-setup.md (Cursor section)",
            verdict.rc,
            true,
            Some(&render_unknown_dirty_tree(
                baseline_plan.baseline.is_file(),
                "preflight-short-circuit-no-agent-ran",
            )),
        );
        return verdict.rc;
    }
    let preread = runtime.block_on(cursor_preread_service_token(
        &runner,
        &config,
        context,
        &cancellation,
    ));
    let credential = match preread {
        CursorTokenPreread::Proceed(credential) => credential,
        CursorTokenPreread::Unreadable => {
            eprintln!("{}", larch_core::CURSOR_PREREAD_FAIL_MSG);
            preflight_failure(
                args,
                artifacts,
                ReviewTool::Cursor,
                "cursor-preread-service-token: keychain -w read returned no token on Darwin; see docs/installation-and-setup.md (Cursor section)",
                larch_core::CURSOR_PREREAD_FAIL_RC,
                true,
                Some(&render_unknown_dirty_tree(
                    baseline_plan.baseline.is_file(),
                    "preflight-short-circuit-no-agent-ran",
                )),
            );
            return larch_core::CURSOR_PREREAD_FAIL_RC;
        }
    };
    let home = env::var_os("HOME").map_or_else(env::temp_dir, PathBuf::from);
    let cursor_config = match CursorConfigContext::create(&temporary_root, &home) {
        Ok(value) => value,
        Err(error) => {
            preflight_failure(
                args,
                artifacts,
                ReviewTool::Cursor,
                &format!("cursor auth setup failed: {error}"),
                1,
                true,
                None,
            );
            return 1;
        }
    };
    let roll = randomish_u64();
    let jitter = cursor_launch_jitter_ms(
        env::var(ENV_CURSOR_LAUNCH_JITTER_MS).ok().as_deref(),
        env::var_os("PYTEST_CURRENT_TEST").is_some(),
        roll,
    );
    if jitter != 0 {
        thread::sleep(Duration::from_millis(jitter));
    }
    let wrapped = format!(" /max-mode on. Prompt: {CURSOR_STRICT_PREAMBLE}\n\n{original_prompt}");
    let mut request = VendorLaunchRequest::new(
        workdir.display().to_string(),
        artifacts.output().display().to_string(),
        wrapped,
    );
    request.timing_task_kind.clone_from(&timing_kind);
    request.model_args = model_args;
    let command = match CURSOR_DESCRIPTOR.build_argv("review-ask", &request) {
        Ok(arguments) => arguments.full_argv(),
        Err(error) => {
            preflight_failure(
                args,
                artifacts,
                ReviewTool::Cursor,
                &format!("cursor_launcher_load_model_args failed (exit 1): {error}"),
                1,
                true,
                Some(&render_unknown_dirty_tree(
                    baseline_plan.baseline.is_file(),
                    "model-args-preflight-no-agent-ran",
                )),
            );
            return 1;
        }
    };
    let mut child_env = session.child_environment.clone();
    child_env.extend(cursor_child_environment(credential.as_ref()));
    child_env.push(cursor_config.child_environment());
    let retry = run_review_retries(&ReviewRetryRequest {
        tool: ReviewTool::Cursor,
        artifacts,
        args,
        command: &command,
        environment: &child_env,
        working_directory: &workdir,
        capture_stdout_only: true,
        routed_streams: None,
    });
    let sidecar = artifacts.path(LauncherArtifactKind::Sidecar);
    if retry.exit_code != 0 {
        if brainstorm_failure_uses_sink(&timing_kind, &args.stderr_sink) {
            write_failure_sink(artifacts, &args.stderr_sink, retry.exit_code);
        } else {
            append_launch_failure(args, artifacts, session, ReviewTool::Cursor, retry);
        }
    } else {
        artifacts.append(
            &sidecar,
            "cursor-status: ok (no stderr emitted during agent run)\n",
        );
    }
    append_outer_meta(args, artifacts, &timing_kind, args.cursor_model.as_deref());
    if retry.exit_code == 0 {
        postprocess_cursor(
            artifacts,
            session,
            retry.transient_attempt,
            extracted_model(&request.model_args),
        );
    }
    let dirty_sidecar = artifacts.path(LauncherArtifactKind::DirtyTree);
    let fallback = dirty_tree_commands::baseline_sidecar_lines_for_review(
        &artifacts.root,
        &baseline_plan.baseline,
        &dirty_sidecar,
        &workdir,
    );
    artifacts.write(&dirty_sidecar, &format!("{}\n", fallback.join("\n")));
    record_timing(
        session,
        VendorProgram::Cursor,
        &timing_kind,
        start,
        artifacts.output(),
        retry.exit_code,
    );
    artifacts.promote_inner_done();
    emit_launcher_result(
        artifacts,
        ReviewTool::Cursor,
        retry.exit_code,
        &args.stderr_sink,
    );
    retry.exit_code
}

#[derive(Clone, Copy)]
struct RetryOutcome {
    exit_code: i32,
    auth_attempt: u32,
    transient_attempt: u32,
}

struct ReviewRetryRequest<'a> {
    tool: ReviewTool,
    artifacts: &'a ReviewArtifacts,
    args: &'a ReviewArguments,
    command: &'a [String],
    environment: &'a [(ChildEnvironment, OsString)],
    working_directory: &'a Path,
    capture_stdout_only: bool,
    routed_streams: Option<&'a ExternalAgentRouting>,
}

#[allow(clippy::too_many_lines)] // Retry branches must stay ordered with their artifact resets.
fn run_review_retries(request: &ReviewRetryRequest<'_>) -> RetryOutcome {
    let ReviewRetryRequest {
        tool,
        artifacts,
        args,
        command,
        environment,
        working_directory,
        capture_stdout_only,
        routed_streams,
    } = *request;
    let max_auth = env::var("LARCH_EXTERNAL_AUTH_RETRIES")
        .ok()
        .and_then(|value| parse_positive(&value))
        .and_then(|value| u32::try_from(value).ok())
        .unwrap_or(5);
    let mut auth_attempt = 1_u32;
    let mut transient_attempt = 1_u32;
    let mut unclassified_empty_retried = false;
    let stderr_sink = (!args.stderr_sink.is_empty())
        .then(|| PathBuf::from(&args.stderr_sink))
        .and_then(|path| safe_existing_diagnostic_path(&path));
    loop {
        let _release = acquire_startup_lock(tool.vendor());
        let routing = routed_streams.cloned().unwrap_or({
            if capture_stdout_only {
                ExternalAgentRouting::CaptureStdoutOnly
            } else {
                ExternalAgentRouting::Streams {
                    stdout: None,
                    stderr: None,
                }
            }
        });
        let exit_code = match run_external_agent_launch(&ExternalAgentLaunch {
            tool: tool.as_str().to_owned(),
            output: artifacts.output_raw.clone(),
            timeout_seconds: parse_positive(&args.timeout).unwrap_or(1),
            poll_interval: external_agent_poll_interval(),
            stderr_sink: stderr_sink.clone(),
            command: command.to_owned(),
            program: tool.vendor(),
            sentinel_suffix: ".inner.done",
            routing,
            environment: environment.to_owned(),
            working_directory: Some(working_directory.to_path_buf()),
            stdin: None,
            stall_watch: None,
        }) {
            Ok(outcome) => outcome.exit_code,
            Err(error) => {
                eprintln!("agent launch-review: {error}");
                1
            }
        };
        if tool == ReviewTool::Codex {
            mirror_codex_quota(artifacts);
        }
        let sidecar = artifacts.path(LauncherArtifactKind::Sidecar);
        let diag = artifacts.path(LauncherArtifactKind::Diag);
        let events = artifacts.path(LauncherArtifactKind::Events);
        let output = artifacts.output();
        let auth_paths = if tool == ReviewTool::Codex {
            vec![artifacts.read(&sidecar)]
        } else {
            vec![
                artifacts.read(&sidecar),
                artifacts.read(&diag),
                artifacts.read(output),
            ]
        };
        let verdict = external_auth_verdict(tool.as_str(), auth_paths.iter().map(String::as_str));
        let quota_paths = if tool == ReviewTool::Codex {
            vec![
                artifact_from_path(artifacts, &sidecar),
                artifact_from_path(artifacts, &diag),
                artifact_from_path(artifacts, &events),
                artifact_from_path(artifacts, output),
            ]
        } else {
            vec![
                artifact_from_path(artifacts, &sidecar),
                artifact_from_path(artifacts, &diag),
                artifact_from_path(artifacts, output),
            ]
        };
        let auth_failure = verdict == larch_core::ExternalAuthVerdict::Auth;
        let quota_failure = quota_paths
            .iter()
            .any(|artifact| is_quota_failure(Some(artifact)));
        let output_artifact = artifact_from_path(artifacts, output);
        let transient_failure =
            is_transient_infra_failure(tool.vendor(), exit_code, Some(&output_artifact));
        let empty_cursor = tool == ReviewTool::Cursor
            && exit_code == 0
            && is_cursor_empty_result(
                &artifacts.read(output),
                env::var(ENV_CURSOR_RETRY_EMPTY_RESULT).map_or(true, |value| value != "0"),
            );
        let policy_rejection = artifacts.read(&diag).contains("POLICY_REJECTION=true");
        let retryable = ((exit_code != 0 && transient_failure) || empty_cursor)
            && !auth_failure
            && !quota_failure
            && !policy_rejection;
        if retryable && transient_attempt <= REVIEW_MAX_TRANSIENT_RETRIES {
            transient_attempt += 1;
            sleep_before_retry(transient_attempt);
            reset_retry_artifacts(tool, artifacts, "attempt");
            continue;
        }
        if exit_code != 0
            && !unclassified_empty_retried
            && exit_code == 1
            && verdict == larch_core::ExternalAuthVerdict::Unclassified
            && !auth_failure
            && !quota_failure
            && !policy_rejection
        {
            unclassified_empty_retried = true;
            reset_retry_artifacts(
                tool,
                artifacts,
                if tool == ReviewTool::Cursor {
                    "cursor auth attempt"
                } else {
                    "attempt"
                },
            );
            continue;
        }
        if exit_code != 0 && auth_failure && auth_attempt < max_auth {
            auth_attempt += 1;
            reset_retry_artifacts(
                tool,
                artifacts,
                if tool == ReviewTool::Cursor {
                    "cursor auth attempt"
                } else {
                    "attempt"
                },
            );
            continue;
        }
        return RetryOutcome {
            exit_code,
            auth_attempt,
            transient_attempt,
        };
    }
}

fn external_agent_poll_interval() -> Duration {
    env::var("RUN_EXTERNAL_AGENT_POLL_INTERVAL")
        .ok()
        .and_then(|value| value.parse::<f64>().ok())
        .filter(|value| value.is_finite() && *value > 0.0)
        .and_then(|value| Duration::try_from_secs_f64(value).ok())
        .unwrap_or(Duration::from_secs(10))
}

fn acquire_startup_lock(program: VendorProgram) -> Option<StartupLockRelease> {
    let root = shared_startup_lock_root()?;
    let config = startup_lock_config(program)?;
    external_startup_lock_acquire(&root, &config)
        .ok()
        .and_then(|state| external_startup_lock_release_after(state, &config).ok())
}

fn shared_startup_lock_root() -> Option<TemporaryRoot> {
    let root = fs::canonicalize("/tmp").ok()?;
    TemporaryRoot::resolve(Some(&root)).ok()
}

fn startup_lock_config(program: VendorProgram) -> Option<StartupLockConfig> {
    StartupLockConfig::from_values(
        program,
        platform_name(),
        env::var("USER").ok().as_deref(),
        env::var("LARCH_EXTERNAL_STARTUP_LOCK_TTL").ok().as_deref(),
        env::var("LARCH_EXTERNAL_STARTUP_LOCK_TRIES")
            .ok()
            .as_deref(),
        env::var("LARCH_EXTERNAL_STARTUP_LOCK_DELAY")
            .ok()
            .as_deref(),
    )
    .ok()
}

fn platform_name() -> &'static str {
    if env::consts::OS == "macos" {
        "Darwin"
    } else {
        "Linux"
    }
}

fn sleep_before_retry(attempt: u32) {
    let delay = review_retry_delay_secs(
        attempt,
        env::var(ENV_TRANSIENT_RETRY_DELAY).ok().as_deref(),
        env::var_os("PYTEST_CURRENT_TEST").is_some(),
        randomish_u64() & 1,
    );
    if delay != 0 {
        thread::sleep(Duration::from_secs(delay));
    }
}

fn reset_retry_artifacts(tool: ReviewTool, artifacts: &ReviewArtifacts, label: &str) {
    let history = artifacts.path(LauncherArtifactKind::SidecarHistory);
    let sidecar = artifacts.path(LauncherArtifactKind::Sidecar);
    let diag = artifacts.path(LauncherArtifactKind::Diag);
    let _ignored = external_stream_reset(&artifacts.root, &sidecar, Some(&history), label);
    let _ignored = external_stream_reset(
        &artifacts.root,
        &diag,
        Some(&history),
        &format!("{label} diag"),
    );
    if tool == ReviewTool::Codex {
        let events = artifacts.path(LauncherArtifactKind::Events);
        let _ignored = external_stream_reset(
            &artifacts.root,
            &events,
            Some(&history),
            &format!("{label} events.jsonl"),
        );
    }
}

fn mirror_codex_quota(artifacts: &ReviewArtifacts) {
    let events = artifacts.read(&artifacts.path(LauncherArtifactKind::Events));
    let quota = is_quota_failure(Some(&LauncherArtifact::present(events)));
    if quota {
        artifacts.append(
            &artifacts.path(LauncherArtifactKind::Sidecar),
            "codex-quota: usage limit / quota reported on the codex exec --json events stream\n",
        );
    }
}

fn artifact_from_path(artifacts: &ReviewArtifacts, path: &Path) -> LauncherArtifact {
    read_safe_diagnostic(path).map_or_else(
        || LauncherArtifact::present(artifacts.read(path)),
        LauncherArtifact::present,
    )
}

fn append_outer_meta(
    args: &ReviewArguments,
    artifacts: &ReviewArtifacts,
    timing_kind: &str,
    cursor_model: Option<&str>,
) {
    let cwd = env::current_dir().unwrap_or_default();
    let prompt_display = suffixed_path(Path::new(&args.output), ".prompt")
        .display()
        .to_string();
    let mut lines = vec![
        "OUTER_LAUNCHER=agent launch-review".to_owned(),
        format!("OUTER_LAUNCHER_PROMPT_FILE={prompt_display}"),
        format!("OUTER_LAUNCHER_WORKDIR={}", cwd.display()),
        format!("OUTER_LAUNCHER_SITE={}", args.site),
        format!(
            "OUTER_LAUNCHER_MODEL_ROLE={}",
            if args.model_role.is_empty() {
                "default"
            } else {
                &args.model_role
            }
        ),
    ];
    if !args.risk.is_empty() {
        lines.push(format!(
            "OUTER_LAUNCHER_RISK={}",
            if args.risk == "low" { "low" } else { "high" }
        ));
    }
    if !timing_kind.is_empty() {
        lines.push(format!("OUTER_LAUNCHER_TIMING_KIND={timing_kind}"));
    }
    if !args.stderr_sink.is_empty() {
        lines.push(format!("STDERR_SINK={}", args.stderr_sink));
    }
    if let Some(model) = cursor_model.filter(|model| !model.is_empty()) {
        lines.push(format!("OUTER_LAUNCHER_CURSOR_MODEL={model}"));
    }
    artifacts.append(
        &artifacts.path(LauncherArtifactKind::Meta),
        &format!("{}\n", lines.join("\n")),
    );
}

fn preflight_failure(
    args: &ReviewArguments,
    artifacts: &ReviewArtifacts,
    tool: ReviewTool,
    reason: &str,
    rc: i32,
    capture_stdout_only: bool,
    dirty_override: Option<&str>,
) {
    let bundle = render_preflight_bundle(
        tool.as_str(),
        &args.timeout,
        artifacts.output(),
        reason,
        capture_stdout_only,
        rc,
    );
    artifacts.write(artifacts.output(), &bundle.output);
    artifacts.write(&artifacts.path(LauncherArtifactKind::Diag), &bundle.diag);
    artifacts.write(
        &artifacts.path(LauncherArtifactKind::Sidecar),
        &bundle.sidecar,
    );
    artifacts.write(&artifacts.path(LauncherArtifactKind::Meta), &bundle.meta);
    artifacts.write(
        &artifacts.path(LauncherArtifactKind::DirtyTree),
        dirty_override.unwrap_or(&bundle.dirty_tree),
    );
    append_outer_meta(
        args,
        artifacts,
        &args.timing_kind(tool),
        args.cursor_model.as_deref(),
    );
    artifacts.write(&artifacts.path(LauncherArtifactKind::Done), &bundle.done);
    if brainstorm_failure_uses_sink(&args.timing_kind(tool), &args.stderr_sink) {
        write_failure_sink(artifacts, &args.stderr_sink, rc);
    }
    emit_launcher_result(artifacts, tool, rc, &args.stderr_sink);
}

fn brainstorm_failure_uses_sink(timing_kind: &str, sink: &str) -> bool {
    !sink.is_empty() && matches!(timing_kind, "codex-brainstorm" | "cursor-brainstorm")
}

fn write_failure_sink(artifacts: &ReviewArtifacts, sink: &str, exit_code: i32) {
    let diag = artifacts.read(&artifacts.path(LauncherArtifactKind::Diag));
    let mut body = if diag.is_empty() {
        format!("STATUS=FAILED\nLAUNCHER_EXIT={exit_code}\n")
    } else {
        diag
    };
    if !body.contains("LAUNCHER_EXIT=") {
        let _ignored = writeln!(body, "LAUNCHER_EXIT={exit_code}");
    }
    let requested = PathBuf::from(sink);
    let path = if requested.is_absolute() {
        requested
    } else {
        env::current_dir().unwrap_or_default().join(requested)
    };
    let Some(parent) = path.parent() else {
        return;
    };
    if ensure_directory_chain(parent).is_err() {
        return;
    }
    let Ok(root) = TemporaryRoot::resolve(Some(parent)) else {
        return;
    };
    let Some(name) = path.file_name() else {
        return;
    };
    let Ok(target) = root.confine(root.path().join(name), PathIntent::Write) else {
        return;
    };
    let _ignored = atomic_write_utf8_in(&root, target.path(), &body, true, 0o600);
}

fn append_launch_failure(
    args: &ReviewArguments,
    artifacts: &ReviewArtifacts,
    session: &ReviewSession,
    tool: ReviewTool,
    retry: RetryOutcome,
) {
    let sink = (!args.stderr_sink.is_empty())
        .then(|| Path::new(&args.stderr_sink))
        .and_then(safe_existing_diagnostic_path);
    let _ignored = write_failure_diag(
        &artifacts.root,
        &artifacts.paths,
        sink.as_deref(),
        Some(&artifacts.path(LauncherArtifactKind::SidecarHistory)),
        Some(&artifacts.path(LauncherArtifactKind::Events)),
    );
    let source = failure_source(artifacts, sink.as_deref());
    let (class, reason) = classify_failure(artifacts, tool, retry.exit_code, &source);
    if let Some(log) =
        crate::launcher_support::execution_issues_log(&args.selected_session_env_path())
    {
        let _ignored = run_python(
            session,
            [
                OsString::from("run-log"),
                OsString::from("append-failure"),
                OsString::from("--log"),
                log.into_os_string(),
                OsString::from("--site"),
                OsString::from(&args.site),
                OsString::from("--tool"),
                OsString::from(format!("{}-review", tool.as_str())),
                OsString::from("--exit-code"),
                OsString::from(retry.exit_code.to_string()),
                OsString::from("--category"),
                OsString::from("External Reviewer Issues"),
                OsString::from("--output-file"),
                source.as_os_str().to_owned(),
                OsString::from("--verdict"),
                OsString::from(if reason.is_empty() { class } else { reason }),
                OsString::from("--retry-count"),
                OsString::from(retry.auth_attempt.to_string()),
                OsString::from("--transient-retry-count"),
                OsString::from(retry.transient_attempt.to_string()),
                OsString::from("--redact"),
            ],
        );
    }
    crate::launcher_support::append_vendor_failure_diagnostic(
        &source,
        &format!("{} {}-review", args.site, tool.as_str()),
        retry.exit_code,
    );
}

fn failure_source(artifacts: &ReviewArtifacts, sink: Option<&Path>) -> PathBuf {
    let mut paths = vec![artifacts.path(LauncherArtifactKind::FailureDiag)];
    paths.extend(retry_failure_diagnostic_paths(artifacts.output()));
    if let Some(sink) = sink {
        paths.push(sink.to_path_buf());
    }
    paths.extend([
        artifacts.path(LauncherArtifactKind::SidecarHistory),
        artifacts.path(LauncherArtifactKind::Sidecar),
        artifacts.path(LauncherArtifactKind::Diag),
        artifacts.path(LauncherArtifactKind::Events),
        artifacts.output().to_path_buf(),
    ]);
    paths
        .into_iter()
        .find(|path| read_safe_diagnostic(path).is_some())
        .unwrap_or_else(|| artifacts.path(LauncherArtifactKind::Diag))
}

/// Preserve the legacy retry-carrier precedence used by review failure logs.
fn retry_failure_diagnostic_paths(output: &Path) -> [PathBuf; 2] {
    let rendered = output.to_string_lossy();
    let stem = rendered.strip_suffix(".txt").unwrap_or(&rendered);
    [
        PathBuf::from(format!("{stem}-retry.txt.failure-diag")),
        PathBuf::from(format!("{stem}-ns-retry.txt.failure-diag")),
    ]
}

fn classify_failure(
    artifacts: &ReviewArtifacts,
    tool: ReviewTool,
    exit_code: i32,
    source: &Path,
) -> (&'static str, &'static str) {
    let auth_paths = [
        artifacts.read(source),
        artifacts.read(&artifacts.path(LauncherArtifactKind::FailureDiag)),
        artifacts.read(&artifacts.path(LauncherArtifactKind::Diag)),
        artifacts.read(&artifacts.path(LauncherArtifactKind::Sidecar)),
        artifacts.read(&artifacts.path(LauncherArtifactKind::Events)),
        artifacts.read(artifacts.output()),
    ];
    let verdict = external_auth_verdict(tool.as_str(), auth_paths.iter().map(String::as_str));
    let sidecar = artifact_from_path(artifacts, source);
    let output = artifact_from_path(artifacts, artifacts.output());
    let failure = larch_core::classify_launch_failure(&LaunchFailureInputs {
        launcher_exit: exit_code,
        tool: tool.vendor(),
        auth_verdict: if verdict == larch_core::ExternalAuthVerdict::Auth {
            AuthVerdict::Auth
        } else {
            AuthVerdict::Unclassified
        },
        binary_present: vendor_on_path(tool.vendor()),
        sidecar: Some(&sidecar),
        output: Some(&output),
    });
    (failure.class().as_str(), failure.reason().as_str())
}

fn emit_launcher_result(artifacts: &ReviewArtifacts, tool: ReviewTool, exit_code: i32, sink: &str) {
    let sink = (!sink.is_empty())
        .then(|| Path::new(sink))
        .and_then(safe_existing_diagnostic_path);
    if exit_code != 0 {
        let _ignored = write_failure_diag(
            &artifacts.root,
            &artifacts.paths,
            sink.as_deref(),
            Some(&artifacts.path(LauncherArtifactKind::SidecarHistory)),
            Some(&artifacts.path(LauncherArtifactKind::Events)),
        );
    }
    let source = failure_source(artifacts, sink.as_deref());
    let (class, reason) = classify_failure(artifacts, tool, exit_code, &source);
    emit_kv("LAUNCHER_EXIT", &exit_code.to_string());
    emit_kv("LAUNCHER_FAILURE_CLASS", class);
    emit_kv("LAUNCHER_FAILURE_REASON", reason);
    emit_kv("OUTPUT", &artifacts.output_raw);
}

fn record_codex_usage(artifacts: &ReviewArtifacts, _session: &ReviewSession, model: &str) {
    let events = artifacts.path(LauncherArtifactKind::Events);
    let sidecar = artifacts.path(LauncherArtifactKind::Sidecar);
    let totals = match parse_codex_usage_file(&events) {
        Ok(value) => value,
        Err(error) => {
            artifacts.append(&sidecar, &format!("agent parse-codex-usage: {error}\n"));
            return;
        }
    };
    let token_record = if model.is_empty() {
        format!(
            "TOOL=codex\nINPUT={}\nOUTPUT={}\nCACHE_READ={}\nTOTAL={}\nRAW=codex_review\n",
            totals.uncached_input_tokens(),
            totals.output_tokens(),
            totals.cached_input_tokens(),
            totals.total_tokens(),
        )
    } else {
        format!(
            "TOOL=codex\nMODEL={model}\nINPUT={}\nOUTPUT={}\nCACHE_READ={}\nTOTAL={}\nRAW=codex_review\n",
            totals.uncached_input_tokens(),
            totals.output_tokens(),
            totals.cached_input_tokens(),
            totals.total_tokens(),
        )
    };
    let path = artifacts.path(LauncherArtifactKind::TokenRecord);
    artifacts.write(&path, &token_record);
    crate::token_commands::record_vendor_sidecar_best_effort([
        OsString::from("--input"),
        path.as_os_str().to_owned(),
    ]);
}

fn postprocess_cursor(
    artifacts: &ReviewArtifacts,
    session: &ReviewSession,
    transient_attempt: u32,
    model: &str,
) {
    let raw = match artifacts.read_bytes(artifacts.output()) {
        Some(raw) if !raw.is_empty() => raw,
        _ => return,
    };
    let json_sidecar = suffixed_path(artifacts.output(), ".json");
    artifacts.write_bytes(&json_sidecar, &raw);
    let Ok(value) = serde_json::from_slice::<serde_json::Value>(&raw) else {
        return;
    };
    let Some(object) = value.as_object() else {
        return;
    };
    let result = object
        .get("result")
        .and_then(serde_json::Value::as_str)
        .unwrap_or_default();
    if !result.is_empty() {
        let normalized = cursor_normalize_no_issues(result);
        let validator = RustResearchValidator;
        match plan_cursor_result_write(&normalized, &value, Some(&validator)) {
            larch_core::CursorResultWrite::Keep(result) => {
                artifacts.write(artifacts.output(), &result);
            }
            larch_core::CursorResultWrite::Degraded { diag } => {
                artifacts.write(artifacts.output(), CURSOR_DEGRADED_RESPONSE);
                if let Some(diag) = diag {
                    artifacts.write(&artifacts.path(LauncherArtifactKind::Diag), &diag);
                }
            }
        }
    }
    record_cursor_usage(artifacts, session, &value, model);
    if result.is_empty() {
        let (output, diag) = larch_core::render_cursor_empty_response(&value, transient_attempt);
        artifacts.write(artifacts.output(), &output);
        artifacts.write(&artifacts.path(LauncherArtifactKind::Diag), &diag);
    }
}

struct RustResearchValidator;

impl ResearchOutputValidator for RustResearchValidator {
    fn validate(&self, result_text: &str) -> bool {
        let Some(root) = system_temporary_root() else {
            return false;
        };
        let Ok(directory) =
            larch_adapters::SecureTempDir::create(&root, "larch-review-validation-")
        else {
            return false;
        };
        let path = directory.path().join("result.txt");
        if fs::write(&path, result_text).is_err() {
            return false;
        }
        crate::eval_commands::validate_captured(&[
            OsString::from("--validation-mode"),
            path.as_os_str().to_owned(),
        ])
        .code
            == 0
    }
}

fn record_cursor_usage(
    artifacts: &ReviewArtifacts,
    _session: &ReviewSession,
    value: &serde_json::Value,
    model: &str,
) {
    let Some(usage) = value.get("usage").and_then(serde_json::Value::as_object) else {
        return;
    };
    let parse = |names: &[&str]| -> Result<i64, ()> {
        names
            .iter()
            .find_map(|name| usage.get(*name))
            .map_or(Ok(0), |value| {
                json_usage_number(Some(value)).map_err(|_| ())
            })
    };
    let (Ok(input), Ok(output), Ok(cache_read), Ok(cache_create)) = (
        parse(&["inputTokens", "input_tokens"]),
        parse(&["outputTokens", "output_tokens"]),
        parse(&["cacheReadTokens", "cache_read_input_tokens"]),
        parse(&["cacheWriteTokens", "cache_creation_input_tokens"]),
    ) else {
        artifacts.append(
            &artifacts.path(LauncherArtifactKind::Sidecar),
            "agent parse-cursor-usage: usage token value is not numeric\n",
        );
        return;
    };
    let total = input
        .saturating_add(output)
        .saturating_add(cache_read)
        .saturating_add(cache_create);
    let mut text = format!(
        "TOOL=cursor\nINPUT={input}\nOUTPUT={output}\nCACHE_READ={cache_read}\nCACHE_CREATE={cache_create}\nTOTAL={total}\nRAW=cursor_review\n"
    );
    if !model.is_empty() {
        let _ignored = writeln!(text, "MODEL={model}");
    }
    let record = artifacts.path(LauncherArtifactKind::TokenRecord);
    artifacts.write(&record, &text);
    crate::token_commands::record_vendor_sidecar_best_effort([
        OsString::from("--input"),
        record.as_os_str().to_owned(),
    ]);
}

fn extracted_model(args: &[String]) -> &str {
    args.windows(2)
        .find(|pair| pair[0] == "--model" || pair[0] == "-m")
        .map_or("", |pair| pair[1].as_str())
}

fn record_timing(
    session: &ReviewSession,
    vendor: VendorProgram,
    task_kind: &str,
    start: i64,
    output: &Path,
    exit_code: i32,
) {
    let overrides: Vec<(&str, OsString)> = session
        .child_environment
        .iter()
        .map(|(key, value)| (key.name(), value.clone()))
        .collect();
    let _ignored = crate::timing_commands::record_vendor_task_with_environment(
        &crate::timing_commands::vendor_timing_arguments(
            vendor.executable(),
            task_kind,
            start,
            epoch_seconds(),
            output,
            exit_code,
            if exit_code == 0 { "complete" } else { "signal" },
        ),
        &overrides,
    );
}

fn append_panel_prompt_size(
    args: &ReviewArguments,
    artifacts: &ReviewArtifacts,
    prompt: &str,
    payload_bytes: u64,
) {
    let Some(kind) = panel_slot_kind() else {
        return;
    };
    let artifact = panel_artifact_path(artifacts.output());
    let prompt_bytes = prompt.len();
    let payload_bytes = usize::try_from(payload_bytes).unwrap_or(usize::MAX);
    let scaffold_bytes = prompt_bytes.saturating_sub(payload_bytes);
    let source_agent = if args.agent_file.is_empty() {
        env::var("LARCH_PANEL_SOURCE_AGENT_FILE").unwrap_or_default()
    } else {
        args.agent_file.clone()
    };
    let (agent_file, agent_bytes) = panel_agent_file(&source_agent);
    let round_num = env::var("LARCH_PANEL_ROUND_NUM")
        .ok()
        .filter(|value| !value.is_empty() && value.bytes().all(|byte| byte.is_ascii_digit()))
        .unwrap_or_default();
    let fields = [
        args.site.clone(),
        env::var("LARCH_PANEL_PHASE").unwrap_or_default(),
        round_num,
        env::var("LARCH_PANEL_SLOT").unwrap_or_default(),
        kind.to_owned(),
        args.tool
            .map(ReviewTool::as_str)
            .unwrap_or_default()
            .to_owned(),
        artifacts
            .output()
            .file_name()
            .map_or_else(String::new, |name| name.to_string_lossy().into_owned()),
        prompt_bytes.to_string(),
        estimated_tokens(prompt_bytes).to_string(),
        scaffold_bytes.to_string(),
        estimated_tokens(scaffold_bytes).to_string(),
        payload_bytes.to_string(),
        estimated_tokens(payload_bytes).to_string(),
        agent_file,
        agent_bytes.to_string(),
        estimated_tokens(agent_bytes).to_string(),
    ];
    append_panel_tsv_row(&artifact, &fields);
}

fn append_panel_tsv_row(artifact: &Path, fields: &[String]) {
    if fields.len() != PANEL_FIELDS.len() {
        return;
    }
    let Some(parent) = artifact.parent() else {
        return;
    };
    if ensure_directory_chain(parent).is_err() {
        return;
    }
    let Ok(root) = TemporaryRoot::resolve(Some(parent)) else {
        return;
    };
    let Some(name) = artifact.file_name() else {
        return;
    };
    let Ok(path) = root.confine(root.path().join(name), PathIntent::Write) else {
        return;
    };
    let header = PANEL_FIELDS.join("\t");
    let row = tsv_row(fields);
    #[cfg(unix)]
    append_locked_panel_tsv_row(&path, &header, &row);
    #[cfg(not(unix))]
    append_unlocked_panel_tsv_row(&path, &header, &row);
}

#[cfg(unix)]
fn append_locked_panel_tsv_row(path: &ConfinedPath, header: &str, row: &str) {
    if path.revalidate().is_err() {
        return;
    }
    let raw_path = path.path();
    let Ok(mut file) = fs::OpenOptions::new()
        .read(true)
        .write(true)
        .create(true)
        .truncate(false)
        .mode(0o600)
        .custom_flags(nix::libc::O_NOFOLLOW)
        .open(raw_path)
    else {
        return;
    };
    let mut locked = false;
    for attempt in 0..PANEL_LOCK_ATTEMPTS {
        #[allow(deprecated)]
        if flock(file.as_raw_fd(), FlockArg::LockExclusiveNonblock).is_ok() {
            locked = true;
            break;
        }
        if attempt + 1 < PANEL_LOCK_ATTEMPTS {
            thread::sleep(Duration::from_millis(50));
        }
    }
    if !locked {
        return;
    }
    append_unlocked_panel_tsv_row_to_file(&mut file, header, row);
    #[allow(deprecated)]
    let _ignored = flock(file.as_raw_fd(), FlockArg::Unlock);
    let _ignored = fs::set_permissions(raw_path, fs::Permissions::from_mode(0o600));
}

#[cfg(not(unix))]
fn append_unlocked_panel_tsv_row(path: &ConfinedPath, header: &str, row: &str) {
    if path.revalidate().is_err() {
        return;
    }
    let Ok(mut file) = fs::OpenOptions::new()
        .read(true)
        .write(true)
        .create(true)
        .truncate(false)
        .open(path.path())
    else {
        return;
    };
    append_unlocked_panel_tsv_row_to_file(&mut file, header, row);
}

fn append_unlocked_panel_tsv_row_to_file(file: &mut fs::File, header: &str, row: &str) {
    let _ignored = file.seek(SeekFrom::Start(0));
    let mut existing = String::new();
    if file.read_to_string(&mut existing).is_err() {
        return;
    }
    if let Some(migrated) = migrate_panel_legacy_header(&existing) {
        if file.set_len(0).is_err()
            || file.seek(SeekFrom::Start(0)).is_err()
            || file.write_all(migrated.as_bytes()).is_err()
        {
            return;
        }
        existing = migrated;
    }
    if file.seek(SeekFrom::End(0)).is_err() {
        return;
    }
    if existing.is_empty() && file.write_all(format!("{header}\n").as_bytes()).is_err() {
        return;
    }
    if file.write_all(format!("{row}\n").as_bytes()).is_err() {
        return;
    }
    let _ignored = file.flush();
}

fn migrate_panel_legacy_header(existing: &str) -> Option<String> {
    let mut lines = existing.lines();
    let header = lines.next()?;
    if header.split('\t').collect::<Vec<_>>() != PANEL_LEGACY_FIELDS {
        return None;
    }
    let mut migrated = String::from(&PANEL_FIELDS.join("\t"));
    migrated.push('\n');
    for line in lines.filter(|line| !line.trim().is_empty()) {
        let mut cells = line.split('\t').map(str::to_owned).collect::<Vec<_>>();
        cells.resize(PANEL_LEGACY_FIELDS.len(), String::new());
        let fields = [
            cells[0].clone(),
            cells[1].clone(),
            cells[2].clone(),
            cells[3].clone(),
            cells[4].clone(),
            cells[5].clone(),
            cells[6].clone(),
            cells[7].clone(),
            cells[8].clone(),
            cells[7].clone(),
            cells[8].clone(),
            "0".to_owned(),
            "0".to_owned(),
            cells[9].clone(),
            cells[10].clone(),
            cells[11].clone(),
        ];
        migrated.push_str(&tsv_row(&fields));
        migrated.push('\n');
    }
    Some(migrated)
}

fn tsv_row(fields: &[String]) -> String {
    fields
        .iter()
        .map(|field| tsv_cell(field))
        .collect::<Vec<_>>()
        .join("\t")
}

fn tsv_cell(field: &str) -> String {
    if !field.contains(['\t', '\n', '\r', '"']) {
        return field.to_owned();
    }
    format!("\"{}\"", field.replace('"', "\"\""))
}

fn panel_agent_file(raw: &str) -> (String, usize) {
    if raw.is_empty() {
        return (String::new(), 0);
    }
    let Some(root) = plugin_root_directory() else {
        return (String::new(), 0);
    };
    let Ok(repo) = root.canonicalize() else {
        return (String::new(), 0);
    };
    let path = PathBuf::from(raw);
    let candidate = if path.is_absolute() {
        path
    } else {
        repo.join(path)
    };
    let Ok(metadata) = fs::symlink_metadata(&candidate) else {
        return (String::new(), 0);
    };
    if metadata.file_type().is_symlink() || !metadata.is_file() {
        return (String::new(), 0);
    }
    let Ok(resolved) = candidate.canonicalize() else {
        return (String::new(), 0);
    };
    let Ok(relative) = resolved.strip_prefix(&repo) else {
        return (String::new(), 0);
    };
    let bytes =
        fs::metadata(&resolved).map_or(0, |metadata| usize::try_from(metadata.len()).unwrap_or(0));
    (relative.to_string_lossy().replace('\\', "/"), bytes)
}

const fn estimated_tokens(bytes: usize) -> usize {
    bytes.saturating_add(3) / 4
}

fn panel_payload_bytes() -> u64 {
    env::var("LARCH_PANEL_PAYLOAD_BYTES")
        .ok()
        .and_then(|value| value.trim().parse::<u64>().ok())
        .unwrap_or(0)
}

fn run_python<I>(session: &ReviewSession, arguments: I) -> Option<larch_core::ProcessOutput>
where
    I: IntoIterator<Item = OsString>,
{
    let root = plugin_root_directory()?;
    let program = PythonVerbProgram::new(&root).ok()?;
    let cwd = env::current_dir().ok()?;
    let request = ProcessRequest::new(
        ExternalProgram::PythonVerb(program),
        arguments,
        cwd,
        PYTHON_TIMEOUT,
        PYTHON_SHUTDOWN_GRACE,
        NonZeroUsize::new(PYTHON_OUTPUT_LIMIT).unwrap_or(NonZeroUsize::MIN),
    )
    .ok()?;
    let request = session
        .child_environment
        .iter()
        .fold(request, |request, (key, value)| {
            request.with_environment(*key, value.clone())
        });
    let runtime = LarchRuntime::current_thread().ok()?;
    let runner = TokioProcessRunner::new(Arc::new(NoopProcessObserver));
    runtime
        .block_on(runner.run(request, &Cancellation::new()))
        .ok()
}

fn plugin_root_directory() -> Option<PathBuf> {
    let declared = env::var_os("CLAUDE_PLUGIN_ROOT").map(PathBuf::from);
    if let Some(root) = declared.filter(|root| {
        root.is_absolute()
            && !root.components().any(|part| {
                matches!(
                    part,
                    std::path::Component::CurDir | std::path::Component::ParentDir
                )
            })
    }) {
        return Some(root);
    }
    let cwd = env::current_dir().ok()?;
    if cwd.join("python/cli.py").is_file() {
        return Some(cwd);
    }
    env::current_exe()
        .ok()?
        .parent()?
        .parent()
        .map(Path::to_path_buf)
}

fn review_workdir() -> PathBuf {
    let cwd = env::current_dir().unwrap_or_else(|_| PathBuf::from("/"));
    for candidate in [
        env::var_os("CLAUDE_PROJECT_DIR").map(PathBuf::from),
        Some(cwd.clone()),
    ]
    .into_iter()
    .flatten()
    {
        if let Some(root) = crate::launcher_support::git_workdir(&candidate) {
            return root;
        }
    }
    session_clone_path()
        .or_else(|| clone_path_from_parent_walk(&cwd))
        .and_then(|path| crate::launcher_support::git_workdir(&path))
        .unwrap_or(cwd)
}

fn session_clone_path() -> Option<PathBuf> {
    ["IMPLEMENT_TMPDIR", "DESIGN_TMPDIR", "SESSION_TMPDIR"]
        .into_iter()
        .filter_map(env::var_os)
        .map(PathBuf::from)
        .find_map(|root| keepalive_clone_path(&root.join(".larch-keepalive")))
}

fn clone_path_from_parent_walk(start: &Path) -> Option<PathBuf> {
    start
        .ancestors()
        .find_map(|directory| keepalive_clone_path(&directory.join(".larch-keepalive")))
}

fn keepalive_clone_path(path: &Path) -> Option<PathBuf> {
    let metadata = fs::symlink_metadata(path).ok()?;
    if !metadata.is_file() || metadata.file_type().is_symlink() {
        return None;
    }
    fs::read_to_string(path)
        .ok()?
        .lines()
        .find_map(|line| line.strip_prefix("CLONE_PATH="))
        .map(str::trim)
        .filter(|value| !value.is_empty())
        .map(PathBuf::from)
}

fn vendor_on_path(program: VendorProgram) -> bool {
    let executable = program.executable();
    env::var_os("PATH").is_some_and(|path| {
        env::split_paths(&path).any(|directory| directory.join(executable).is_file())
    })
}

fn system_temporary_root() -> Option<TemporaryRoot> {
    let root = env::temp_dir();
    TemporaryRoot::resolve(Some(&root)).ok()
}

fn suffixed_path(path: &Path, suffix: &str) -> PathBuf {
    let mut rendered = path.as_os_str().to_owned();
    rendered.push(suffix);
    PathBuf::from(rendered)
}

fn epoch_seconds() -> i64 {
    i64::try_from(
        SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs(),
    )
    .unwrap_or(i64::MAX)
}

fn epoch_nanos() -> u128 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_nanos()
}

fn randomish_u64() -> u64 {
    u64::try_from(epoch_nanos()).unwrap_or(u64::MAX) ^ PART_COUNTER.fetch_add(1, Ordering::Relaxed)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::{
        ffi::OsString,
        fs::{self, OpenOptions},
    };
    use tempfile::TempDir;

    fn is_round_dir(name: &str) -> bool {
        name.strip_prefix("round-").is_some_and(|number| {
            !number.is_empty() && number.bytes().all(|byte| byte.is_ascii_digit())
        })
    }

    fn review_args() -> ReviewArguments {
        ReviewArguments {
            tool: Some(ReviewTool::Codex),
            output: "out.txt".to_owned(),
            timeout: "5".to_owned(),
            prompt: Some("review this".to_owned()),
            site: "review Step 2".to_owned(),
            model_role: "default".to_owned(),
            ..ReviewArguments::default()
        }
    }

    fn parse(values: &[&str]) -> ReviewParse {
        parse_arguments(&values.iter().map(OsString::from).collect::<Vec<_>>())
    }

    fn parsed(values: &[&str]) -> ReviewArguments {
        match parse(values) {
            ReviewParse::Parsed(args) => *args,
            ReviewParse::Help | ReviewParse::Error(_) => panic!("expected parsed arguments"),
        }
    }

    fn parse_error(values: &[&str]) -> String {
        match parse(values) {
            ReviewParse::Error(error) => error,
            ReviewParse::Help | ReviewParse::Parsed(_) => panic!("expected parser error"),
        }
    }

    fn artifacts(fixture: &TempDir) -> ReviewArtifacts {
        let output = fixture.path().join("review.txt");
        ReviewArtifacts::create(&output.display().to_string(), false).expect("artifacts")
    }

    #[test]
    fn parser_accepts_the_full_legacy_value_contract() {
        let args = parsed(&[
            "--tool",
            "cursor",
            "--output=out.txt",
            "--timeout=5",
            "--prompt=review this",
            "--mode",
            "review",
            "--description-text",
            "description",
            "--scope-files",
            "src/lib.rs",
            "--competition-notice",
            "--competition-notice-file",
            "notice.md",
            "--diff-file",
            "change.diff",
            "--commit-count",
            "2",
            "--plan-file",
            "plan.md",
            "--feature-file",
            "feature.md",
            "--session-env-path",
            "session.env",
            "--timing-task-kind",
            "cursor-review",
            "--token-budget-cap",
            "11",
            "--risk",
            "low",
            "--stderr-sink",
            "stderr.log",
            "--site",
            "review Step 2",
            "--model-role",
            "review",
            "--default-model",
            "gpt-test",
            "--cursor-model",
            "cursor-test",
            "--difficulty",
            "high",
        ]);
        assert_eq!(args.tool, Some(ReviewTool::Cursor));
        assert_eq!(args.output, "out.txt");
        assert_eq!(args.timeout, "5");
        assert_eq!(args.prompt.as_deref(), Some("review this"));
        assert!(args.competition_notice);
        assert_eq!(args.cursor_model.as_deref(), Some("cursor-test"));
        assert_eq!(args.difficulty, "high");
        assert!(validate_arguments(&args, ReviewTool::Cursor).is_ok());
        let mut direct = ReviewArguments::default();
        set_review_option(&mut direct, "--agent-file", "agents/reviewer.md".to_owned())
            .expect("agent file option");
        assert_eq!(direct.agent_file, "agents/reviewer.md");
    }

    #[test]
    fn parser_rejects_missing_unknown_and_conflicting_arguments() {
        assert!(matches!(parse(&["--help"]), ReviewParse::Help));
        assert_eq!(
            parse_error(&["--unknown"]),
            "unrecognized arguments: --unknown"
        );
        assert_eq!(
            parse_error(&["--output"]),
            "argument --output: expected one argument"
        );
        assert_eq!(
            parse_error(&["--tool", "codex", "--output", "out", "--timeout", "1"]),
            "one of the arguments --prompt --prompt-file --agent-file is required"
        );
        assert_eq!(
            parse_error(&[
                "--tool",
                "codex",
                "--output",
                "out",
                "--timeout",
                "1",
                "--prompt",
                "one",
                "--prompt-file",
                "two",
            ]),
            "one of the arguments --prompt --prompt-file --agent-file is required"
        );
        assert!(
            parse_error(&[
                "--tool",
                "claude",
                "--output",
                "out",
                "--timeout",
                "1",
                "--prompt",
                "one",
            ])
            .contains("invalid choice")
        );
        assert_eq!(
            parse_error(&[
                "--tool",
                "codex",
                "--output",
                "out",
                "--timeout",
                "1",
                "--prompt",
                "one",
                "--competition-notice=value",
            ]),
            "unrecognized arguments: --competition-notice=value"
        );
    }

    #[test]
    fn validation_rejects_each_public_unsafe_or_invalid_value() {
        type ValidationCase = (ReviewTool, fn(&mut ReviewArguments), &'static str);

        let valid = review_args();
        assert!(validate_arguments(&valid, ReviewTool::Codex).is_ok());
        let cases: &[ValidationCase] = &[
            (
                ReviewTool::Codex,
                |args| args.output = "bad\noutput".to_owned(),
                "unsupported",
            ),
            (
                ReviewTool::Codex,
                |args| args.stderr_sink = "bad\nsink".to_owned(),
                "unsupported",
            ),
            (
                ReviewTool::Codex,
                |args| args.risk = "low\nhigh".to_owned(),
                "risk",
            ),
            (
                ReviewTool::Codex,
                |args| args.timing_task_kind = "review\nforged".to_owned(),
                "timing-task-kind",
            ),
            (
                ReviewTool::Codex,
                |args| args.timeout = "abc".to_owned(),
                "got 'abc'",
            ),
            (
                ReviewTool::Cursor,
                |args| args.timeout = "0".to_owned(),
                ">= 1",
            ),
            (
                ReviewTool::Codex,
                |args| args.timing_task_kind = "--invalid".to_owned(),
                "non-empty",
            ),
            (
                ReviewTool::Codex,
                |args| args.token_budget_cap = "0".to_owned(),
                "token-budget-cap",
            ),
            (
                ReviewTool::Codex,
                |args| args.cursor_model = Some("model".to_owned()),
                "only valid",
            ),
            (
                ReviewTool::Cursor,
                |args| args.cursor_model = Some(" ".to_owned()),
                "non-empty",
            ),
            (
                ReviewTool::Cursor,
                |args| args.cursor_model = Some("bad\nmodel".to_owned()),
                "control",
            ),
            (
                ReviewTool::Codex,
                |args| args.site = "--site".to_owned(),
                "non-empty",
            ),
            (
                ReviewTool::Codex,
                |args| args.site = "site\nforged".to_owned(),
                "control",
            ),
            (
                ReviewTool::Codex,
                |args| args.model_role = "other".to_owned(),
                "invalid choice",
            ),
        ];
        for &(tool, update, expected) in cases {
            let mut value = valid.clone();
            update(&mut value);
            assert!(
                validate_arguments(&value, tool)
                    .expect_err("invalid value")
                    .1
                    .contains(expected),
                "expected validation error to contain {expected}"
            );
        }
    }

    #[test]
    fn artifact_and_diagnostic_helpers_stay_confined_and_ordered() {
        let fixture = TempDir::new().expect("fixture");
        let artifacts = artifacts(&fixture);
        artifacts.write(artifacts.output(), "first");
        artifacts.append(artifacts.output(), " second");
        assert_eq!(artifacts.read(artifacts.output()), "first second");

        let token_record = artifacts.path(LauncherArtifactKind::TokenRecord);
        artifacts.write_bytes(&token_record, b"bytes");
        assert_eq!(artifacts.read_bytes(&token_record), Some(b"bytes".to_vec()));
        artifacts.remove(&token_record);
        assert_eq!(artifacts.read_bytes(&token_record), None);

        let inner_done = artifacts.path(LauncherArtifactKind::InnerDone);
        artifacts.write(&inner_done, "0\n");
        artifacts.promote_inner_done();
        assert_eq!(
            artifacts.read(&artifacts.path(LauncherArtifactKind::Done)),
            "0\n"
        );
        assert!(!inner_done.exists());
        assert!(regular_nonempty(artifacts.output()));
        assert!(!regular_nonempty(&fixture.path().join("missing")));

        let diagnostic = fixture.path().join("diagnostic.log");
        fs::write(&diagnostic, "diagnostic body").expect("diagnostic");
        assert_eq!(
            read_safe_diagnostic(&diagnostic).as_deref(),
            Some("diagnostic body")
        );
        assert!(safe_existing_diagnostic_path(&fixture.path().join("missing")).is_none());

        let [retry, namespaced] = retry_failure_diagnostic_paths(artifacts.output());
        artifacts.write(&namespaced, "namespaced retry");
        assert_eq!(failure_source(&artifacts, None), namespaced);
        artifacts.write(&retry, "retry");
        assert_eq!(failure_source(&artifacts, None), retry);
        assert!(
            ReviewArtifacts::create(
                &fixture
                    .path()
                    .join("missing-parent/out.txt")
                    .display()
                    .to_string(),
                false,
            )
            .is_err()
        );
    }

    #[test]
    fn prompt_and_specialist_argument_helpers_preserve_all_inputs() {
        let fixture = TempDir::new().expect("fixture");
        let artifacts = artifacts(&fixture);
        let session = ReviewSession::default();
        let args = review_args();
        assert_eq!(
            resolve_prompt(&args, ReviewTool::Codex, &artifacts, &session).expect("raw prompt"),
            ("review this".to_owned(), 0)
        );

        let prompt_file = fixture.path().join("prompt.txt");
        fs::write(&prompt_file, "from file").expect("prompt");
        let mut from_file = args.clone();
        from_file.prompt = None;
        from_file.prompt_file = prompt_file.display().to_string();
        assert_eq!(
            resolve_prompt(&from_file, ReviewTool::Cursor, &artifacts, &session)
                .expect("file prompt"),
            ("from file".to_owned(), 0)
        );
        from_file.prompt_file = fixture.path().join("missing.txt").display().to_string();
        assert!(
            resolve_prompt(&from_file, ReviewTool::Cursor, &artifacts, &session)
                .expect_err("missing prompt")
                .1
                .contains("failed to read")
        );

        let mut render_args = args;
        render_args.agent_file = "agents/reviewer.md".to_owned();
        render_args.mode = "review".to_owned();
        render_args.description_text = "description".to_owned();
        render_args.scope_files = "src/lib.rs".to_owned();
        render_args.competition_notice = true;
        render_args.competition_notice_file = "notice.md".to_owned();
        render_args.diff_file = "diff.txt".to_owned();
        render_args.commit_count = "3".to_owned();
        render_args.plan_file = "plan.md".to_owned();
        render_args.feature_file = "feature.md".to_owned();
        render_args.session_env_path = fixture.path().join("session.env").display().to_string();
        render_args.difficulty = "high".to_owned();
        let rendered = normal_specialist_render_args(&render_args, &artifacts);
        for expected in [
            "--description-text",
            "--scope-files",
            "--competition-notice",
            "--diff-file",
            "--feature-file",
            "--findings-ledger-file",
            "--session-env-path",
            "--difficulty",
        ] {
            assert!(
                rendered.contains(&expected.to_owned()),
                "missing {expected}"
            );
        }

        let mut sentinel = BTreeMap::new();
        for (key, value) in [
            ("AGENT_FILE", "agents/reviewer.md"),
            ("MODE", "review"),
            ("SCOPE_FILES", "src/lib.rs"),
            ("COMPETITION_NOTICE_FILE", "notice.md"),
            ("DIFF_FILE", "diff.txt"),
            ("COMMIT_COUNT", "3"),
            ("PLAN_FILE", "plan.md"),
            ("FEATURE_FILE", "feature.md"),
            ("FINDINGS_LEDGER_FILE", "findings.tsv"),
            ("SESSION_ENV_PATH", "session.env"),
            ("DIFFICULTY", "high"),
            ("COMPETITION_NOTICE", "true"),
        ] {
            sentinel.insert(key.to_owned(), value.to_owned());
        }
        let replay = sentinel_specialist_render_args(&sentinel);
        assert!(replay.contains(&"--competition-notice".to_owned()));
        assert!(replay.contains(&"--findings-ledger-file".to_owned()));
        assert!(findings_ledger_path(fixture.path(), "").ends_with("findings-ledger.tsv"));
    }

    #[test]
    fn metadata_preflight_and_retry_helpers_preserve_failure_context() {
        let fixture = TempDir::new().expect("fixture");
        let artifacts = artifacts(&fixture);
        let mut args = review_args();
        args.output = artifacts.output().display().to_string();
        args.risk = "medium".to_owned();
        args.stderr_sink = fixture.path().join("sink.log").display().to_string();
        args.timing_task_kind = "cursor-brainstorm".to_owned();
        append_outer_meta(
            &args,
            &artifacts,
            &args.timing_task_kind,
            Some("cursor-model"),
        );
        let meta = artifacts.read(&artifacts.path(LauncherArtifactKind::Meta));
        assert!(meta.contains("OUTER_LAUNCHER_RISK=high"));
        assert!(meta.contains("OUTER_LAUNCHER_CURSOR_MODEL=cursor-model"));

        preflight_failure(
            &args,
            &artifacts,
            ReviewTool::Cursor,
            "preflight reason",
            7,
            true,
            Some("STATUS=unknown\n"),
        );
        assert_eq!(
            artifacts.read(&artifacts.path(LauncherArtifactKind::Done)),
            "7\n"
        );
        assert!(
            artifacts
                .read(&artifacts.path(LauncherArtifactKind::Diag))
                .contains("preflight reason")
        );
        assert!(
            fs::read_to_string(&args.stderr_sink)
                .expect("failure sink")
                .contains("LAUNCHER_EXIT=7")
        );

        artifacts.write(
            &artifacts.path(LauncherArtifactKind::Events),
            "usage limit reached",
        );
        mirror_codex_quota(&artifacts);
        assert!(
            artifacts
                .read(&artifacts.path(LauncherArtifactKind::Sidecar))
                .contains("codex-quota")
        );

        artifacts.write(&artifacts.path(LauncherArtifactKind::Sidecar), "sidecar");
        artifacts.write(&artifacts.path(LauncherArtifactKind::Diag), "diag");
        reset_retry_artifacts(ReviewTool::Codex, &artifacts, "attempt");
        assert!(
            artifacts
                .read(&artifacts.path(LauncherArtifactKind::SidecarHistory))
                .contains("attempt")
        );
        assert!(brainstorm_failure_uses_sink("codex-brainstorm", "sink"));
        assert!(!brainstorm_failure_uses_sink("codex-review", "sink"));
    }

    #[test]
    fn cursor_postprocess_and_usage_handle_empty_invalid_and_valid_payloads() {
        let fixture = TempDir::new().expect("fixture");
        let artifacts = artifacts(&fixture);
        let session = ReviewSession::default();
        artifacts.write_bytes(
            artifacts.output(),
            br#"{"result":"","usage":{"inputTokens":4,"outputTokens":2,"cacheReadTokens":1,"cacheWriteTokens":0}}"#,
        );
        postprocess_cursor(&artifacts, &session, 2, "cursor-model");
        assert!(suffixed_path(artifacts.output(), ".json").is_file());
        assert!(artifacts.read(artifacts.output()).contains("CURSOR"));
        assert!(
            artifacts
                .read(&artifacts.path(LauncherArtifactKind::TokenRecord))
                .contains("MODEL=cursor-model")
        );

        record_cursor_usage(
            &artifacts,
            &session,
            &serde_json::json!({"usage": {"inputTokens": "invalid"}}),
            "",
        );
        assert!(
            artifacts
                .read(&artifacts.path(LauncherArtifactKind::Sidecar))
                .contains("not numeric")
        );

        artifacts.write(
            &artifacts.path(LauncherArtifactKind::Events),
            "{\"type\":\"message\",\"usage\":{\"input_tokens\":4,\"cached_input_tokens\":1,\"output_tokens\":2}}\n",
        );
        record_codex_usage(&artifacts, &session, "codex-model");
        assert!(
            artifacts
                .read(&artifacts.path(LauncherArtifactKind::TokenRecord))
                .contains("MODEL=codex-model")
        );
        artifacts.write(&artifacts.path(LauncherArtifactKind::Events), "not json");
        record_codex_usage(&artifacts, &session, "");
        assert!(
            artifacts
                .read(&artifacts.path(LauncherArtifactKind::Sidecar))
                .contains("parse-codex-usage")
        );
        assert_eq!(
            extracted_model(&["--model".to_owned(), "model".to_owned()]),
            "model"
        );
        assert_eq!(extracted_model(&["--other".to_owned()]), "");
    }

    #[test]
    fn panel_and_path_helpers_escape_migrate_and_resolve_safely() {
        let legacy_row = [
            "site",
            "phase",
            "1",
            "slot",
            "specialist",
            "cursor",
            "out",
            "12",
            "3",
            "agent",
            "4",
            "1",
        ]
        .join("\t");
        let legacy = format!("{}\n{legacy_row}\n", PANEL_LEGACY_FIELDS.join("\t"));
        let migrated = migrate_panel_legacy_header(&legacy).expect("legacy migration");
        assert_eq!(
            migrated.lines().next(),
            Some(PANEL_FIELDS.join("\t").as_str())
        );
        assert_eq!(
            migrated.lines().nth(1).expect("row").split('\t').count(),
            16
        );
        assert!(migrate_panel_legacy_header("not legacy\n").is_none());
        assert_eq!(tsv_cell("plain"), "plain");
        assert_eq!(tsv_cell("tab\tquote\""), "\"tab\tquote\"\"\"");
        assert!(tsv_row(&["one".to_owned(), "two\nthree".to_owned()]).contains('"'));
        assert!(is_round_dir("round-12"));
        assert!(!is_round_dir("round-x"));
        assert_eq!(estimated_tokens(5), 2);

        let fixture = TempDir::new().expect("fixture");
        let panel = fixture.path().join("panel.tsv");
        let mut file = OpenOptions::new()
            .create(true)
            .truncate(false)
            .read(true)
            .write(true)
            .open(&panel)
            .expect("panel file");
        append_unlocked_panel_tsv_row_to_file(&mut file, &PANEL_FIELDS.join("\t"), "row");
        drop(file);
        assert!(fs::read_to_string(&panel).expect("panel").contains("row"));

        let fields = PANEL_FIELDS
            .iter()
            .map(|field| (*field).to_owned())
            .collect::<Vec<_>>();
        append_panel_tsv_row(&fixture.path().join("round-3/panel.tsv"), &fields);
        assert!(fixture.path().join("round-3/panel.tsv").is_file());
        assert!(
            panel_artifact_path(&fixture.path().join("round-3/out.txt"))
                .ends_with("round-3/panel-prompt-sizes.tsv")
        );
        assert_eq!(
            suffixed_path(Path::new("out.txt"), ".done"),
            PathBuf::from("out.txt.done")
        );
        assert!(epoch_seconds() > 0);
        assert!(epoch_nanos() > 0);
        let _first = randomish_u64();
        let _second = randomish_u64();
    }

    #[test]
    fn keepalive_and_temporary_root_helpers_reject_unsafe_carriers() {
        let fixture = TempDir::new().expect("fixture");
        let keepalive = fixture.path().join(".larch-keepalive");
        fs::write(&keepalive, "OTHER=value\nCLONE_PATH=/tmp/clone\n").expect("keepalive");
        assert_eq!(
            keepalive_clone_path(&keepalive),
            Some(PathBuf::from("/tmp/clone"))
        );
        assert_eq!(
            clone_path_from_parent_walk(fixture.path()),
            Some(PathBuf::from("/tmp/clone"))
        );
        assert!(system_temporary_root().is_some());
        let _vendor_present = vendor_on_path(VendorProgram::Codex);
    }
}
