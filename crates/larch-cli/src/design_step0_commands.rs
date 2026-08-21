//! Rust owner for the nine `/design` Step 0 wrapper verbs (#8578).
//!
//! Atomically replaces the Python registrations for `design step0-parse`,
//! `design step0-session`, `design step0-route`, `design step0-init`,
//! `design step0-clarify-hard-halt`, `design step0-abort-cleanup`,
//! `design step0-ap-continue`, `design step0c`, and `design settle-next-action`.
//! The frozen Python reference lives under
//! `fixtures/rust-parity/design_step0_frozen/`.
//!
//! The router-owning sibling `design_commands.rs` (#8577) is the exact style
//! template: each public verb takes `&[OsString]`, returns [`ExitCode`], and
//! defers subprocess work behind an injectable-effects seam. This owner reuses
//! that module's `quote_single`, `parse_stdout_kv`, `kv_last`, `kv_all`,
//! `write_kv_file`, and `PAUSE_LOAD_TIMEOUT` rather than duplicating them.

use std::{
    collections::BTreeMap,
    ffi::OsString,
    fs,
    path::{Path, PathBuf},
    process::{Command, ExitCode},
};

use larch_core::{CommentPolicy, KvDocument, ParseOptions};

use crate::{
    blocker_commands::resolve_repo_for,
    design_commands::{
        PAUSE_LOAD_TIMEOUT, kv_all, kv_last, parse_stdout_kv, quote_single, write_kv_file,
    },
    github_service::with_github_service,
    python_verb::run_python_verb,
    voter_calibration_commands::resolve_like_python,
};

// ---------------------------------------------------------------------------
// Constants ported from design_step0_env.py / session_env.py
// ---------------------------------------------------------------------------

const TEMPLATE_PLUGIN_ROOT: &str = "${CLAUDE_PLUGIN_ROOT}";
const PARSE_VALIDATION_RC: i32 = 3;
const CONFIGURATION_ERROR_RC: u8 = 2;
/// `config.EXIT_INTERNAL_ERROR` is 1 in the frozen reference.
const EXIT_INTERNAL_ERROR: u8 = 1;

const PARSED_ENV_KEYS: [&str; 10] = [
    "partition_requested",
    "brainstorm_requested",
    "approve_requested",
    "skip_approve_requested",
    "no_dedup_requested",
    "lifecycle_parent_context",
    "run_id",
    "difficulty",
    "POSITIONAL_KIND",
    "POSITIONAL_VALUE",
];

const SOURCE_ENV_ALLOW: [&str; 10] = [
    "DESIGN_TMPDIR",
    "SESSION_TMPDIR",
    "SESSION_ID",
    "ISSUE_NUMBER",
    "ISSUE_TITLE",
    "HAS_CLARIFY_LABEL",
    "REPO",
    "CODEX_BINARY_FOUND",
    "CURSOR_BINARY_FOUND",
    "CLAUDE_PLUGIN_ROOT",
];

const ROUTE_STATE_KEYS: [&str; 7] = [
    "ROUTE",
    "RESUME_STEP",
    "HAS_CLARIFY_LABEL",
    "ISSUE_NUMBER",
    "ISSUE_TITLE",
    "REPO",
    "brainstorm_requested",
];

const ROUTE_RESULT_KEYS: [&str; 12] = [
    "ROUTE",
    "BRAINSTORM_PREFIX",
    "TITLE_FILTER_REASON",
    "TITLE_FILTER_MARKER",
    "MARKER_AGE",
    "MARKER_TTL",
    "DESIGN_REENTRY_MARKER_PATH",
    "RESUME_STEP",
    "SESSION_ID",
    "RUN_ID",
    "BRAINSTORM_DONE",
    "MARKER_CLEARED",
];

const INIT_RESULT_KEYS: [&str; 3] = ["INIT_STATUS", "RENAMED", "RUN_PARAMS_PATH"];

const ROUTE_STATE_PATH: &str = ".design-step0-route-state.env";

/// `COMMON_ENV_DEFAULTS`: base process-env read set with defaults.
const COMMON_ENV_DEFAULTS: [(&str, &str); 24] = [
    // COMMON_DESIGN_ENV_DEFAULTS
    ("DESIGN_TMPDIR", ""),
    ("SESSION_TMPDIR", ""),
    ("SESSION_ID", ""),
    ("ISSUE_NUMBER", ""),
    ("ISSUE_TITLE", ""),
    ("HAS_CLARIFY_LABEL", "false"),
    ("REPO", ""),
    ("REPO_ROOT", ""),
    ("CLAUDE_BINARY_FOUND", ""),
    ("CODEX_BINARY_FOUND", ""),
    ("CURSOR_BINARY_FOUND", ""),
    ("IMPLEMENT_TMPDIR", ""),
    // DESIGN_REQUEST_ENV_DEFAULTS
    ("POSITIONAL_KIND", ""),
    ("POSITIONAL_VALUE", ""),
    ("partition_requested", "false"),
    ("brainstorm_requested", "false"),
    ("approve_requested", "false"),
    ("skip_approve_requested", "false"),
    ("no_dedup_requested", "false"),
    ("run_id", ""),
    // Step 0 wrapper extras
    ("difficulty", ""),
    ("SUMMARY_OUTCOME", ""),
    ("CLARIFY_FAILURE_LOG", ""),
    ("CLARIFY_HARD_HALT_RC", "1"),
];

pub type Env = BTreeMap<String, String>;

pub fn utf8_arguments(arguments: &[OsString]) -> Vec<String> {
    arguments
        .iter()
        .map(|argument| argument.to_string_lossy().into_owned())
        .collect()
}

pub fn env_get<'a>(env: &'a Env, key: &str, default: &'a str) -> &'a str {
    env.get(key).map_or(default, String::as_str)
}

// ---------------------------------------------------------------------------
// Child-verb seam (I-Runtime-1)
// ---------------------------------------------------------------------------

/// One child process' captured streams and exit status.
pub struct ChildOutcome {
    pub code: i32,
    pub stdout: String,
    pub stderr: String,
}

/// The subprocess/GitHub seam every Step 0 verb composes through. Production
/// spawns the verified larch entrypoint; unit tests inject a recorded runner.
pub trait Step0Runner {
    /// Run one larch child. When `merge_stderr` is set the child's stderr is
    /// folded into `stdout`, mirroring Python `stderr=subprocess.STDOUT`.
    fn run(
        &self,
        plugin_root: &Path,
        args: &[String],
        env: &[(String, String)],
        merge_stderr: bool,
    ) -> ChildOutcome;

    /// Typed GitHub issue read: `(title, body, has_clarify)`.
    ///
    /// The typed GitHub read lands with #7672. Until then the live impl returns
    /// `Err(())`; every parity golden leaves `ISSUE_NUMBER` empty so the read
    /// branch is not reached.
    fn read_issue(&self, _issue: &str, _repo: &str) -> Result<(String, String, String), ()> {
        Err(())
    }

    /// `gh.resolve_repo`; empty when no repository resolves. Wired with #7672.
    fn resolve_repo(&self) -> String {
        String::new()
    }
}

pub struct LiveStep0Runner;

/// The larch entrypoint, preferring `LARCH_BINARY` like the frozen router.
pub fn entrypoint(plugin_root: &Path) -> PathBuf {
    match std::env::var_os("LARCH_BINARY") {
        Some(value) if !value.is_empty() => PathBuf::from(value),
        _ => plugin_root.join("scripts").join("larch.sh"),
    }
}

impl Step0Runner for LiveStep0Runner {
    fn run(
        &self,
        plugin_root: &Path,
        args: &[String],
        env: &[(String, String)],
        merge_stderr: bool,
    ) -> ChildOutcome {
        let mut command = Command::new(entrypoint(plugin_root)); // lint-subprocess-via-runner: ok LiveStep0Runner is the design Step 0 subprocess seam that spawns the larch.sh/python entrypoint
        command.args(args);
        command.env("CLAUDE_PLUGIN_ROOT", plugin_root);
        for (key, value) in env {
            command.env(key, value);
        }
        match command.output() {
            Ok(output) => {
                let mut stdout = String::from_utf8_lossy(&output.stdout).into_owned();
                let stderr = String::from_utf8_lossy(&output.stderr).into_owned();
                let code = output.status.code().unwrap_or(1);
                if merge_stderr {
                    stdout.push_str(&stderr);
                    ChildOutcome {
                        code,
                        stdout,
                        stderr: String::new(),
                    }
                } else {
                    ChildOutcome {
                        code,
                        stdout,
                        stderr,
                    }
                }
            }
            Err(_error) => ChildOutcome {
                code: 127,
                stdout: String::new(),
                stderr: String::new(),
            },
        }
    }

    /// Typed issue read through the hardened Octocrab `GitHubService` (#7672),
    /// replacing the frozen Python `gh issue view --json body,labels,title`.
    /// Returns `(title, body, has_clarify)` where `has_clarify` is the string
    /// `"true"` when the `needs-design-clarification` label is present.
    fn read_issue(&self, issue: &str, repo: &str) -> Result<(String, String, String), ()> {
        let slug = resolve_repo_for(if repo.is_empty() { None } else { Some(repo) }).ok_or(())?;
        let (owner, name) = slug.split_once('/').ok_or(())?;
        let number: u64 = issue.parse().map_err(|_error| ())?;
        let companion = with_github_service(async |service, cancellation| {
            service
                .issue_read(cancellation, owner, name, number)
                .await
                .map_err(|error| error.to_string())
        })
        .map_err(|_error| ())?;
        let has_clarify = companion
            .labels
            .iter()
            .any(|label| label == "needs-design-clarification");
        Ok((
            companion.title,
            companion.body,
            if has_clarify { "true" } else { "false" }.to_owned(),
        ))
    }

    /// Resolve the ambient repository slug through the shared `gh`/`gix` owner.
    fn resolve_repo(&self) -> String {
        resolve_repo_for(None).unwrap_or_default()
    }
}

// ---------------------------------------------------------------------------
// Wrapper argument parsing (design_step0_env.py `_parse_wrapper_args`)
// ---------------------------------------------------------------------------

pub struct WrapperNs {
    pub session_env_path: String,
    pub claude_pid: String,
    pub plugin_root: String,
    pub outcome: String,
    pub issue_number: String,
    pub exit_code: String,
    pub failure_detail_log: String,
    pub reason: String,
    pub tool: String,
    pub public_argv: Vec<String>,
}

fn env_or(key: &str, default: &str) -> String {
    std::env::var(key).unwrap_or_else(|_| default.to_owned())
}

pub fn parse_wrapper_args(argv: &[String]) -> Result<WrapperNs, ExitCode> {
    let mut ns = WrapperNs {
        session_env_path: String::new(),
        claude_pid: String::new(),
        plugin_root: env_or("CLAUDE_PLUGIN_ROOT", ""),
        outcome: env_or("SUMMARY_OUTCOME", ""),
        issue_number: String::new(),
        exit_code: {
            let raw = env_or("CLARIFY_HARD_HALT_RC", "1");
            if raw.is_empty() { "1".to_owned() } else { raw }
        },
        failure_detail_log: env_or("CLARIFY_FAILURE_LOG", ""),
        reason: "external tool unhealthy; re-run once it recovers.".to_owned(),
        tool: "degraded-tools-gate".to_owned(),
        public_argv: Vec::new(),
    };
    // Value flags accepted; --site/--step3-review-loop-status/--loop-status are
    // consumed but unused by these verbs.
    let mut index = 0;
    while index < argv.len() {
        let token = argv[index].as_str();
        if token == "--" {
            ns.public_argv = argv[index + 1..].to_vec();
            return Ok(ns);
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
        );
        // `--mode`/`--site`/`--step3-review-loop-status`/`--loop-status` are
        // accepted and consumed but unused by these verbs.
        let ignored = matches!(
            token,
            "--mode" | "--site" | "--step3-review-loop-status" | "--loop-status"
        );
        if bound || ignored {
            let Some(value) = argv.get(index + 1) else {
                eprintln!("design wrapper: {token} requires a value");
                return Err(ExitCode::from(2));
            };
            match token {
                "--session-env-path" => ns.session_env_path.clone_from(value),
                "--claude-pid" => ns.claude_pid.clone_from(value),
                "--plugin-root" => ns.plugin_root.clone_from(value),
                "--outcome" => ns.outcome.clone_from(value),
                "--issue-number" => ns.issue_number.clone_from(value),
                "--exit-code" => ns.exit_code.clone_from(value),
                "--failure-detail-log" => ns.failure_detail_log.clone_from(value),
                "--reason" => ns.reason.clone_from(value),
                "--tool" => ns.tool.clone_from(value),
                _ => {}
            }
            index += 2;
            continue;
        }
        eprintln!("design wrapper: unknown argument: {token}");
        return Err(ExitCode::from(2));
    }
    Ok(ns)
}

/// `require_plugin_root`: reject empty/template roots. Never mutates process env
/// (the frozen `os.environ` write is replaced by explicit child-env passing).
pub fn require_plugin_root(value: &str) -> Result<PathBuf, ExitCode> {
    if value.is_empty() {
        eprintln!("/design wrapper: CLAUDE_PLUGIN_ROOT is empty; abort");
        return Err(ExitCode::from(1));
    }
    if value == TEMPLATE_PLUGIN_ROOT {
        eprintln!(
            "/design wrapper: CLAUDE_PLUGIN_ROOT is the unexpanded template literal {TEMPLATE_PLUGIN_ROOT}; abort"
        );
        return Err(ExitCode::from(1));
    }
    Ok(PathBuf::from(value))
}

// ---------------------------------------------------------------------------
// Bash %q codec (design_step0_env.py)
// ---------------------------------------------------------------------------

/// Encode `value` with `printf %q` via bash. On non-zero bash exit, empty
/// values yield `''` and everything else falls back to single-quote wrapping.
fn bash_percent_q(value: &str) -> String {
    let output = Command::new("bash") // lint-subprocess-via-runner: ok the bash %q codec must invoke bash directly to mirror the frozen design_step0_env.py encoder
        .args(["-c", "printf \"%q\" \"$1\"", "_", value])
        .output();
    match output {
        Ok(result) if result.status.success() => {
            String::from_utf8_lossy(&result.stdout).into_owned()
        }
        _ => {
            if value.is_empty() {
                "''".to_owned()
            } else {
                quote_single(value)
            }
        }
    }
}

fn write_bash_quoted_env(path: &Path, data: &Env) {
    if let Some(parent) = path.parent() {
        let _ = fs::create_dir_all(parent);
    }
    let mut text = String::new();
    for key in PARSED_ENV_KEYS {
        let value = data.get(key).map_or("", String::as_str);
        text.push_str(key);
        text.push('=');
        text.push_str(&bash_percent_q(value));
        text.push('\n');
    }
    let _ = fs::write(path, text);
}

const fn is_hex(character: char) -> bool {
    character.is_ascii_hexdigit()
}

/// Port of `_decode_ansi_c_quoted`.
#[allow(clippy::too_many_lines)] // One escape-decode state machine ported branch for branch.
fn decode_ansi_c_quoted(inner: &str) -> String {
    let chars: Vec<char> = inner.chars().collect();
    let mut out = String::new();
    let mut index = 0;
    while index < chars.len() {
        let character = chars[index];
        if character != '\\' || index + 1 >= chars.len() {
            out.push(character);
            index += 1;
            continue;
        }
        let next = chars[index + 1];
        let simple = match next {
            'n' => Some('\n'),
            't' => Some('\t'),
            'r' => Some('\r'),
            'a' => Some('\u{7}'),
            'b' => Some('\u{8}'),
            'f' => Some('\u{c}'),
            'v' => Some('\u{b}'),
            '\\' => Some('\\'),
            '\'' => Some('\''),
            '"' => Some('"'),
            _ => None,
        };
        if let Some(replacement) = simple {
            out.push(replacement);
            index += 2;
            continue;
        }
        if ('0'..='7').contains(&next) {
            let mut end = index + 1;
            let mut digits = String::new();
            while end < chars.len() && digits.len() < 3 && ('0'..='7').contains(&chars[end]) {
                digits.push(chars[end]);
                end += 1;
            }
            if let Ok(code) = u32::from_str_radix(&digits, 8) {
                out.push(char::from_u32(code).unwrap_or('\u{fffd}'));
            }
            index = end;
            continue;
        }
        if next == 'x' {
            let mut end = index + 2;
            let mut digits = String::new();
            while end < chars.len() && digits.len() < 2 && is_hex(chars[end]) {
                digits.push(chars[end]);
                end += 1;
            }
            if !digits.is_empty() {
                if let Ok(code) = u32::from_str_radix(&digits, 16) {
                    out.push(char::from_u32(code).unwrap_or('\u{fffd}'));
                }
                index = end;
                continue;
            }
        }
        if next == 'u' && index + 6 <= chars.len() {
            let digits: String = chars[index + 2..index + 6].iter().collect();
            if digits.len() == 4 && digits.chars().all(is_hex) {
                if let Ok(code) = u32::from_str_radix(&digits, 16) {
                    out.push(char::from_u32(code).unwrap_or('\u{fffd}'));
                }
                index += 6;
                continue;
            }
        }
        if next == 'U' && index + 10 <= chars.len() {
            let digits: String = chars[index + 2..index + 10].iter().collect();
            if digits.len() == 8 && digits.chars().all(is_hex) {
                if let Ok(code) = u32::from_str_radix(&digits, 16) {
                    out.push(char::from_u32(code).unwrap_or('\u{fffd}'));
                }
                index += 10;
                continue;
            }
        }
        out.push(next);
        index += 2;
    }
    out
}

/// Port of `_decode_utf8_byte_escapes`: re-interpret latin-1 code points as
/// UTF-8 bytes, returning the original string when either step cannot apply.
fn decode_utf8_byte_escapes(value: &str) -> String {
    let mut bytes = Vec::with_capacity(value.len());
    for character in value.chars() {
        match u8::try_from(character as u32) {
            Ok(byte) => bytes.push(byte),
            Err(_error) => return value.to_owned(),
        }
    }
    match String::from_utf8(bytes) {
        Ok(decoded) => decoded,
        Err(_error) => value.to_owned(),
    }
}

/// Port of `_decode_bash_percent_q`.
fn decode_bash_percent_q(value: &str) -> String {
    if value == "''" || value.is_empty() {
        return String::new();
    }
    if let Some(inner) = value
        .strip_prefix("$'")
        .and_then(|rest| rest.strip_suffix('\''))
    {
        return decode_utf8_byte_escapes(&decode_ansi_c_quoted(inner));
    }
    let bytes: Vec<char> = value.chars().collect();
    if bytes[0] == '\'' {
        let mut out = String::new();
        let mut index = 1;
        while index < bytes.len() {
            if bytes[index] != '\'' {
                out.push(bytes[index]);
                index += 1;
                continue;
            }
            // The `'"'"'` single-quote splice re-opens the quote with one quote.
            if bytes[index..].starts_with(&['\'', '"', '\'', '"', '\'']) {
                out.push('\'');
                index += 5;
                continue;
            }
            break;
        }
        return out;
    }
    let mut out = String::new();
    let mut index = 0;
    while index < bytes.len() {
        if bytes[index] == '\\' && index + 1 < bytes.len() {
            out.push(bytes[index + 1]);
            index += 2;
        } else {
            out.push(bytes[index]);
            index += 1;
        }
    }
    out
}

fn decode_shell_assignment_value(value: &str) -> String {
    if value.is_empty() {
        String::new()
    } else {
        decode_bash_percent_q(value)
    }
}

// ---------------------------------------------------------------------------
// Env loaders (design_step0_env.py)
// ---------------------------------------------------------------------------

fn normalize_splitlines(text: &str) -> String {
    text.replace("\r\n", "\n").replace('\r', "\n")
}

/// Parse allowlisted `KEY=value` rows, last-wins, then decode each value.
fn parse_allowed_last(text: &str, allowed: &[&str], skip_comments: bool) -> Env {
    let mut options = ParseOptions::legacy();
    if skip_comments {
        options.comments = CommentPolicy::Skip;
    }
    let document = KvDocument::parse(text, options).expect("legacy parser is non-rejecting");
    let mut map: Env = BTreeMap::new();
    for row in document.rows() {
        if allowed.contains(&row.key()) {
            let _ = map.insert(
                row.key().to_owned(),
                decode_shell_assignment_value(row.value()),
            );
        }
    }
    map
}

fn load_bash_quoted_env(path: &Path, allowed: &[&str]) -> Env {
    if path.is_symlink() || !path.is_file() {
        return BTreeMap::new();
    }
    let raw = match fs::read(path) {
        Ok(bytes) => String::from_utf8_lossy(&bytes).into_owned(),
        Err(_error) => return BTreeMap::new(),
    };
    parse_allowed_last(&normalize_splitlines(&raw), allowed, true)
}

pub fn load_source_env(path: &str, claude_pid: &str) -> Env {
    if path.is_empty() {
        return BTreeMap::new();
    }
    let source = Path::new(path);
    let read_path: PathBuf = if source.is_symlink() {
        if claude_pid.is_empty() {
            return BTreeMap::new();
        }
        match resolve_trusted_design_session_env_source(source, claude_pid) {
            Some(resolved) => resolved,
            None => return BTreeMap::new(),
        }
    } else if source.is_file() {
        source.to_path_buf()
    } else {
        return BTreeMap::new();
    };
    let raw = match fs::read(&read_path) {
        Ok(bytes) => String::from_utf8_lossy(&bytes).into_owned(),
        Err(_error) => return BTreeMap::new(),
    };
    let mut normalized = String::new();
    for line in normalize_splitlines(&raw).split('\n') {
        let trimmed = line.trim();
        if trimmed.is_empty() || trimmed.starts_with('#') {
            continue;
        }
        let stripped = trimmed.strip_prefix("export ").unwrap_or(trimmed);
        normalized.push_str(stripped);
        normalized.push('\n');
    }
    parse_allowed_last(&normalized, &SOURCE_ENV_ALLOW, false)
}

fn base_env() -> Env {
    let mut env = BTreeMap::new();
    for (key, default) in COMMON_ENV_DEFAULTS {
        let _ = env.insert(key.to_owned(), env_or(key, default));
    }
    env
}

pub fn load_wrapper_env(ns: &WrapperNs) -> Env {
    let mut env = base_env();
    for (key, value) in load_source_env(&ns.session_env_path, &ns.claude_pid) {
        let _ = env.insert(key, value);
    }
    if !ns.plugin_root.is_empty() {
        let _ = env.insert("CLAUDE_PLUGIN_ROOT".to_owned(), ns.plugin_root.clone());
    }
    if !ns.outcome.is_empty() {
        let _ = env.insert("SUMMARY_OUTCOME".to_owned(), ns.outcome.clone());
    }
    env
}

// ---------------------------------------------------------------------------
// Sessions cache + PID residual reaping (session_env.py, fs effects local)
// ---------------------------------------------------------------------------

fn sessions_dir() -> PathBuf {
    let home = env_or("HOME", "");
    PathBuf::from(home)
        .join(".cache")
        .join("larch")
        .join("sessions")
}

fn step0_parsed_env_path(pid: &str) -> PathBuf {
    sessions_dir().join(format!("step0-parsed-{pid}.env"))
}

fn design_symlink_path(pid: &str) -> PathBuf {
    let name = if pid.is_empty() {
        "current-design-env.sh".to_owned()
    } else {
        format!("current-design-env-{pid}.sh")
    };
    sessions_dir().join(name)
}

fn design_run_path(pid: &str) -> PathBuf {
    sessions_dir().join(format!("design-run-{pid}.sh"))
}

fn validate_claude_pid(pid: &str) -> Result<(), String> {
    let bytes = pid.as_bytes();
    let valid = !pid.is_empty()
        && pid.len() <= 7
        && matches!(bytes[0], b'1'..=b'9')
        && bytes.iter().all(u8::is_ascii_digit);
    if valid {
        Ok(())
    } else {
        Err(
            "Invalid --claude-pid: must be a positive integer of at most 7 decimal digits"
                .to_owned(),
        )
    }
}

/// True when `path` or any ancestor is a symlink (refused).
fn any_ancestor_symlink(path: &Path) -> bool {
    let mut cursor = Some(path);
    while let Some(current) = cursor {
        if fs::symlink_metadata(current).is_ok_and(|meta| meta.file_type().is_symlink()) {
            return true;
        }
        cursor = current.parent();
    }
    false
}

fn validate_design_current_env_link(symlink_path: &Path, pid: &str) -> Result<(), String> {
    if symlink_path != design_symlink_path(pid) {
        return Err(format!(
            "design current-env symlink path mismatch: {}",
            symlink_path.display()
        ));
    }
    let mut ancestor = symlink_path.parent();
    while let Some(current) = ancestor {
        if fs::symlink_metadata(current).is_ok_and(|meta| meta.file_type().is_symlink()) {
            return Err(format!(
                "refusing symlinked ancestor for design current-env link: {}",
                current.display()
            ));
        }
        let parent = current.parent();
        if parent == Some(current) || parent.is_none() {
            break;
        }
        ancestor = parent;
    }
    Ok(())
}

fn resolve_trusted_design_session_env_source(path: &Path, claude_pid: &str) -> Option<PathBuf> {
    if claude_pid.is_empty() || !path.is_symlink() {
        return None;
    }
    validate_design_current_env_link(path, claude_pid).ok()?;
    let resolved = fs::canonicalize(path).ok()?;
    if resolved.is_file() {
        Some(resolved)
    } else {
        None
    }
}

fn reap_pid_residuals(claude_pid: &str) -> Result<(), String> {
    validate_claude_pid(claude_pid)?;
    let symlink_path = design_symlink_path(claude_pid);
    validate_design_current_env_link(&symlink_path, claude_pid)?;
    let _ = fs::remove_file(&symlink_path);
    for target in [
        design_run_path(claude_pid),
        step0_parsed_env_path(claude_pid),
    ] {
        if any_ancestor_symlink(&target) {
            return Err(format!("refusing symlink in path: {}", target.display()));
        }
        let _ = fs::remove_file(&target);
    }
    Ok(())
}

// ---------------------------------------------------------------------------
// Shared verb helpers (design_step0.py)
// ---------------------------------------------------------------------------

pub fn require_design_tmpdir(env: &Env, design_tmpdir: Option<&str>) -> Result<PathBuf, ExitCode> {
    let raw = design_tmpdir.filter(|value| !value.is_empty()).map_or_else(
        || env_get(env, "DESIGN_TMPDIR", "").to_owned(),
        str::to_owned,
    );
    if raw.is_empty() {
        eprintln!("/design wrapper: DESIGN_TMPDIR required");
        return Err(ExitCode::from(1));
    }
    let path = PathBuf::from(&raw);
    if !path.is_absolute() {
        eprintln!("/design wrapper: DESIGN_TMPDIR must be an absolute path");
        return Err(ExitCode::from(1));
    }
    if !path.is_dir() {
        eprintln!(
            "/design wrapper: DESIGN_TMPDIR is not an existing directory: {}",
            path.display()
        );
        return Err(ExitCode::from(1));
    }
    Ok(resolve_like_python(&path))
}

/// Build the still-Python `design pause-save` argv shared by every bridge site.
pub fn pause_save_arguments(design_tmpdir: &Path, issue: &str, repo: &str) -> Vec<OsString> {
    let mut arguments: Vec<OsString> = vec![
        "design".into(),
        "pause-save".into(),
        "--design-tmpdir".into(),
        design_tmpdir.as_os_str().to_owned(),
        "--issue".into(),
        issue.into(),
    ];
    if !repo.is_empty() {
        arguments.push("--repo".into());
        arguments.push(repo.into());
    }
    arguments
}

/// Bridge to the still-Python `design pause-save`; returns its exit code.
pub fn pause_save_bridge(design_tmpdir: &Path, issue: &str, repo: &str) -> i32 {
    match run_python_verb(
        pause_save_arguments(design_tmpdir, issue, repo),
        PAUSE_LOAD_TIMEOUT,
    ) {
        Ok(output) => output.status().code().unwrap_or(1),
        Err(_error) => 1,
    }
}

/// Bridge to `design pause-save`, returning its exit code and captured streams.
pub fn pause_save_captured(design_tmpdir: &Path, issue: &str, repo: &str) -> (i32, String, String) {
    run_python_verb(
        pause_save_arguments(design_tmpdir, issue, repo),
        PAUSE_LOAD_TIMEOUT,
    )
    .map_or((1, String::new(), String::new()), |output| {
        output.decoded_streams()
    })
}

/// Refuse a symlink target, then atomically publish `contents`. Returns `false`
/// on any trust-boundary miss or I/O failure.
pub fn atomic_write_string(path: &Path, contents: &str) -> bool {
    if path.is_symlink() {
        return false;
    }
    if let Some(parent) = path.parent() {
        let _ = fs::create_dir_all(parent);
    }
    let name = path.file_name().map_or_else(
        || ".result.env".to_owned(),
        |value| value.to_string_lossy().into_owned(),
    );
    let temporary = path.with_file_name(format!(".{name}.{}.tmp", std::process::id()));
    fs::write(&temporary, contents)
        .and_then(|()| fs::rename(&temporary, path))
        .inspect_err(|_error| {
            let _ = fs::remove_file(&temporary);
        })
        .is_ok()
}

/// If a pause is requested, run pause-save and yield its exit code.
pub fn check_pause_and_exit(env: &Env, design_tmpdir: &Path) -> Option<ExitCode> {
    if design_tmpdir.join(".pause-requested").is_file() {
        let code = pause_save_bridge(
            design_tmpdir,
            env_get(env, "ISSUE_NUMBER", ""),
            env_get(env, "REPO", ""),
        );
        return Some(exit_from_i32(code));
    }
    None
}

pub fn exit_from_i32(code: i32) -> ExitCode {
    ExitCode::from(u8::try_from(code).unwrap_or(1))
}

/// Port of `larch_io._valid_var_name`: a non-empty name whose first character is
/// a non-digit `[A-Za-z0-9_]` and whose remainder stays within that set.
pub fn valid_var_name(value: &str) -> bool {
    let mut chars = value.chars();
    match chars.next() {
        None => false,
        Some(first) if first.is_ascii_digit() => false,
        Some(first) if !(first.is_alphanumeric() || first == '_') => false,
        Some(_) => chars.all(|ch| ch.is_alphanumeric() || ch == '_'),
    }
}

/// Port of `phase_driver_read_result_env`: CR-free, allowlisted, order-preserving.
pub fn phase_driver_read_result_env(
    path: &Path,
    allowed: &[&str],
) -> Result<Vec<(String, String)>, ()> {
    if path.is_symlink() || !path.is_file() {
        return Err(());
    }
    let raw = match fs::read(path) {
        Ok(bytes) => String::from_utf8_lossy(&bytes).into_owned(),
        Err(_error) => return Err(()),
    };
    let cleaned: Vec<&str> = raw
        .split('\n')
        .filter(|line| !line.contains('\r'))
        .collect();
    let text = cleaned.join("\n");
    let document =
        KvDocument::parse(&text, ParseOptions::legacy()).expect("legacy parser is non-rejecting");
    Ok(document
        .rows()
        .iter()
        .filter(|row| allowed.contains(&row.key()))
        .map(|row| (row.key().to_owned(), row.value().to_owned()))
        .collect())
}

/// Port of `_read_result_pairs`: primary then optional regular-file fallback.
fn read_result_pairs(primary: &Path, fallback: Option<&Path>, allowed: &[&str]) -> Env {
    let mut pairs = phase_driver_read_result_env(primary, allowed).unwrap_or_default();
    let want_fallback = pairs.is_empty();
    if let Some(path) =
        fallback.filter(|path| want_fallback && path.is_file() && !path.is_symlink())
    {
        pairs = phase_driver_read_result_env(path, allowed).unwrap_or_default();
    }
    let mut map: Env = BTreeMap::new();
    for (key, value) in pairs {
        let _ = map.insert(key, value);
    }
    map
}

// ---------------------------------------------------------------------------
// `settle-next-action` (design_session.py, pure)
// ---------------------------------------------------------------------------

fn settle_next_action_for(site: &str, postplan_rc: i32) -> Option<(&'static str, &'static str)> {
    let action = match (site, postplan_rc) {
        ("gate-b", 0) => ("gate-b-continue", "ok"),
        ("gate-a" | "discussion-round2", 0) => ("gate-a-return", "ok"),
        ("gate-b", 10) => ("gate-b-validator-fail", "validate-failed"),
        ("gate-a" | "discussion-round2", 10) => ("gate-a-validator-fail", "validate-failed"),
        ("gate-b" | "gate-a" | "discussion-round2" | "gate-c", 11) => ("pause", "pause-save"),
        ("gate-b", 12) => ("gate-b-hard-size", "plan-size-trigger"),
        ("gate-a" | "discussion-round2", 12) => ("gate-a-hard-size", "plan-size-trigger"),
        ("gate-b", 13) => ("gate-b-split", "partition-requested"),
        ("gate-a" | "discussion-round2", 13) => ("gate-a-split", "partition-requested"),
        ("gate-c", 0) => ("gate-c-return", "ok"),
        ("gate-c", 10) => ("gate-c-validator-fail", "validate-failed"),
        ("gate-c", 12) => ("gate-c-hard-size", "plan-size-trigger"),
        ("gate-c", 13) => ("gate-c-split", "partition-requested"),
        _ => return None,
    };
    Some(action)
}

/// The `settle-next-action` entry point.
pub fn settle_next_action(arguments: &[OsString]) -> ExitCode {
    let argv = utf8_arguments(arguments);
    let mut site = String::new();
    let mut postplan_rc_raw = String::new();
    let mut status = String::new();
    let mut usage_requested = false;
    let mut index = 0;
    while index < argv.len() {
        let token = argv[index].as_str();
        if token == "--site" {
            let Some(value) = argv.get(index + 1) else {
                "missing-site".clone_into(&mut status);
                break;
            };
            site.clone_from(value);
            index += 2;
            continue;
        }
        if token == "--postplan-rc" {
            let Some(value) = argv.get(index + 1) else {
                "missing-postplan-rc".clone_into(&mut status);
                break;
            };
            postplan_rc_raw.clone_from(value);
            index += 2;
            continue;
        }
        if token == "-h" || token == "--help" {
            usage_requested = true;
            break;
        }
        status = format!("unknown-option:{token}");
        break;
    }
    if usage_requested {
        eprintln!("Usage: cli.py design settle-next-action --site SITE --postplan-rc RC");
        return ExitCode::SUCCESS;
    }
    let mut action = String::new();
    let mut exit_rc = 2;
    if status.is_empty() {
        if !matches!(
            site.as_str(),
            "gate-b" | "gate-a" | "discussion-round2" | "gate-c"
        ) {
            "invalid-site".clone_into(&mut status);
        } else if let Ok(postplan_rc) = postplan_rc_raw.trim().parse::<i32>() {
            if let Some((next_action, next_status)) = settle_next_action_for(&site, postplan_rc) {
                next_action.clone_into(&mut action);
                exit_rc = postplan_rc;
                next_status.clone_into(&mut status);
            } else {
                "unknown-dispatch".clone_into(&mut status);
            }
        } else {
            "invalid-postplan-rc".clone_into(&mut status);
        }
    }
    println!("SETTLE_STATUS={status}");
    if action.is_empty() {
        ExitCode::from(2)
    } else {
        println!("SETTLE_NEXT_ACTION={action}");
        println!("SETTLE_EXIT_RC={exit_rc}");
        ExitCode::SUCCESS
    }
}

// ---------------------------------------------------------------------------
// `step0-parse` (design_step0_env.py)
// ---------------------------------------------------------------------------

fn run_parse_argv(
    runner: &dyn Step0Runner,
    public_argv: &[String],
    plugin_root: &Path,
    claude_pid: &str,
) -> (i32, Env, String) {
    let scratch_dir = step0_parsed_env_path(claude_pid);
    let scratch_dir = scratch_dir
        .parent()
        .map_or_else(|| PathBuf::from("."), std::path::Path::to_path_buf);
    let _ = fs::create_dir_all(&scratch_dir);
    let out_path = scratch_dir.join(format!("larch-argv.{}.{}", std::process::id(), claude_pid));
    let mut args = vec![
        "design".to_owned(),
        "parse-flags".to_owned(),
        "--output".to_owned(),
        out_path.to_string_lossy().into_owned(),
    ];
    args.extend(public_argv.iter().cloned());
    let outcome = runner.run(plugin_root, &args, &[], false);
    let mut allowed: Vec<&str> = PARSED_ENV_KEYS.to_vec();
    allowed.push("VALIDATION_ERROR");
    allowed.push("ERROR_MESSAGE");
    let data = load_bash_quoted_env(&out_path, &allowed);
    let _ = fs::remove_file(&out_path);
    (outcome.code, data, outcome.stderr)
}

fn validate_parse_result(rc: i32, data: &Env, stderr_text: &str) -> Result<(), ExitCode> {
    let positional = env_get(data, "POSITIONAL_VALUE", "");
    if stderr_text.contains("PUBLIC_ARGV_WORDS")
        || positional == "${PUBLIC_ARGV_WORDS}"
        || positional == "$PUBLIC_ARGV_WORDS"
    {
        eprintln!(
            "**⚠ /design: skill loader did not expand public argv words; aborting before session setup.**"
        );
        return Err(ExitCode::from(1));
    }
    let validation_error = env_get(data, "VALIDATION_ERROR", "");
    let error_message = env_get(data, "ERROR_MESSAGE", "");
    if rc == PARSE_VALIDATION_RC {
        if !error_message.is_empty() {
            eprintln!("{error_message}");
        } else if !validation_error.is_empty() {
            eprintln!(
                "**⚠ /design: unrecognized or disallowed public flag: aborting before session setup.** {validation_error}"
            );
        } else {
            eprintln!(
                "**⚠ /design: unrecognized or disallowed public flag: aborting before session setup.**"
            );
        }
        return Err(ExitCode::from(1));
    }
    if rc == 0 {
        if !validation_error.is_empty() {
            eprintln!(
                "**⚠ /design: design parse-flags reported VALIDATION_ERROR but exited {rc}; aborting before session setup.**"
            );
            return Err(ExitCode::from(1));
        }
    } else {
        eprintln!(
            "**⚠ /design: design parse-flags failed (exit {rc}); aborting before session setup.**"
        );
        return Err(ExitCode::from(1));
    }
    if !matches!(
        env_get(data, "POSITIONAL_KIND", ""),
        "issue" | "verbal" | "none"
    ) {
        eprintln!(
            "**⚠ /design: design parse-flags emitted invalid POSITIONAL_KIND; aborting before session setup.**"
        );
        return Err(ExitCode::from(1));
    }
    Ok(())
}

fn parse_and_persist(
    runner: &dyn Step0Runner,
    ns: &WrapperNs,
    plugin_root: &Path,
) -> Result<(PathBuf, Env), ExitCode> {
    let (rc, mut data, stderr_text) =
        run_parse_argv(runner, &ns.public_argv, plugin_root, &ns.claude_pid);
    validate_parse_result(rc, &data, &stderr_text)?;
    for key in PARSED_ENV_KEYS {
        if !data.contains_key(key) {
            let default = if key.ends_with("_requested") {
                "false"
            } else {
                ""
            };
            let _ = data.insert(key.to_owned(), default.to_owned());
        }
    }
    if env_get(&data, "POSITIONAL_KIND", "").is_empty() {
        let _ = data.insert("POSITIONAL_KIND".to_owned(), "none".to_owned());
    }
    let cache = step0_parsed_env_path(&ns.claude_pid);
    write_bash_quoted_env(&cache, &data);
    Ok((cache, data))
}

fn emit_parse_kvs(cache: &Path, data: &Env) {
    println!("STEP0_PARSED_ENV_PATH={}", cache.display());
    println!(
        "PARTITION_REQUESTED={}",
        env_get(data, "partition_requested", "false")
    );
    println!(
        "BRAINSTORM_REQUESTED={}",
        env_get(data, "brainstorm_requested", "false")
    );
    println!(
        "APPROVE_REQUESTED={}",
        env_get(data, "approve_requested", "false")
    );
    println!(
        "SKIP_APPROVE_REQUESTED={}",
        env_get(data, "skip_approve_requested", "false")
    );
    println!(
        "NO_DEDUP_REQUESTED={}",
        env_get(data, "no_dedup_requested", "false")
    );
    println!("RUN_ID={}", env_get(data, "run_id", ""));
    println!("POSITIONAL_KIND={}", env_get(data, "POSITIONAL_KIND", ""));
    println!("POSITIONAL_VALUE={}", env_get(data, "POSITIONAL_VALUE", ""));
}

/// The `step0-parse` entry point.
pub fn step0_parse(arguments: &[OsString]) -> ExitCode {
    step0_parse_with(arguments, &LiveStep0Runner)
}

fn step0_parse_with(arguments: &[OsString], runner: &dyn Step0Runner) -> ExitCode {
    let argv = utf8_arguments(arguments);
    let ns = match parse_wrapper_args(&argv) {
        Ok(ns) => ns,
        Err(code) => return code,
    };
    let plugin_root = match require_plugin_root(&ns.plugin_root) {
        Ok(root) => root,
        Err(code) => return code,
    };
    let (cache, data) = match parse_and_persist(runner, &ns, &plugin_root) {
        Ok(result) => result,
        Err(code) => return code,
    };
    emit_parse_kvs(&cache, &data);
    ExitCode::SUCCESS
}

// ---------------------------------------------------------------------------
// `step0-ap-continue` and `step0c` (sentinel writers)
// ---------------------------------------------------------------------------

/// The `step0-ap-continue` entry point.
pub fn step0_ap_continue(arguments: &[OsString]) -> ExitCode {
    let argv = utf8_arguments(arguments);
    let ns = match parse_wrapper_args(&argv) {
        Ok(ns) => ns,
        Err(code) => return code,
    };
    let env = load_wrapper_env(&ns);
    let plugin_root_value = env_get(&env, "CLAUDE_PLUGIN_ROOT", &ns.plugin_root).to_owned();
    if let Err(code) = require_plugin_root(&plugin_root_value) {
        return code;
    }
    let design_tmpdir = match require_design_tmpdir(&env, None) {
        Ok(path) => path,
        Err(code) => return code,
    };
    let completed = design_tmpdir.join(".completed");
    let _ = fs::create_dir_all(&completed);
    for name in ["step-1c", "step-1d", "step-1d.5"] {
        let _ = fs::write(completed.join(name), "");
    }
    if let Some(code) = check_pause_and_exit(&env, &design_tmpdir) {
        return code;
    }
    ExitCode::SUCCESS
}

fn which(program: &str) -> bool {
    let Some(paths) = std::env::var_os("PATH") else {
        return false;
    };
    std::env::split_paths(&paths)
        .any(|directory| fs::metadata(directory.join(program)).is_ok_and(|meta| meta.is_file()))
}

pub fn derive_binary_found(env: &mut Env) {
    if env_get(env, "CODEX_BINARY_FOUND", "").is_empty() {
        let _ = env.insert(
            "CODEX_BINARY_FOUND".to_owned(),
            if which("codex") { "true" } else { "false" }.to_owned(),
        );
    }
    if env_get(env, "CURSOR_BINARY_FOUND", "").is_empty() {
        let _ = env.insert(
            "CURSOR_BINARY_FOUND".to_owned(),
            if which("cursor") { "true" } else { "false" }.to_owned(),
        );
    }
}

/// The `step0c` entry point.
pub fn step0c(arguments: &[OsString]) -> ExitCode {
    step0c_with(arguments, &LiveStep0Runner)
}

fn step0c_with(arguments: &[OsString], runner: &dyn Step0Runner) -> ExitCode {
    let argv = utf8_arguments(arguments);
    let ns = match parse_wrapper_args(&argv) {
        Ok(ns) => ns,
        Err(code) => return code,
    };
    let mut env = load_wrapper_env(&ns);
    let plugin_root_value = env_get(&env, "CLAUDE_PLUGIN_ROOT", &ns.plugin_root).to_owned();
    let plugin_root = match require_plugin_root(&plugin_root_value) {
        Ok(root) => root,
        Err(code) => return code,
    };
    derive_binary_found(&mut env);
    let design_tmpdir = match require_design_tmpdir(&env, None) {
        Ok(path) => path,
        Err(code) => return code,
    };
    if let Some(code) = check_pause_and_exit(&env, &design_tmpdir) {
        return code;
    }
    let completed = design_tmpdir.join(".completed");
    let _ = fs::create_dir_all(&completed);
    let _ = fs::write(completed.join("step-0c"), "");
    let _ = runner.run(
        &plugin_root,
        &[
            "timing".to_owned(),
            "mark".to_owned(),
            "design folded discussion block".to_owned(),
        ],
        &[("LARCH_TIMING_SKILL".to_owned(), "design".to_owned())],
        false,
    );
    ExitCode::SUCCESS
}

// ---------------------------------------------------------------------------
// `step0-clarify-hard-halt`
// ---------------------------------------------------------------------------

/// Bridge to the Rust-owned `design stage-terminal-state`, capturing streams to
/// the two log paths and returning its exit code. #8580 flipped the verb from
/// Python to Rust and removed its Python registration, so this resolves the
/// larch entrypoint (preferring `LARCH_BINARY`) instead of `run_python_verb`.
pub fn stage_terminal_state_bridge(
    plugin_root: &Path,
    stdout_log: &Path,
    stderr_log: &Path,
    args: &[String],
) -> i32 {
    let mut command = Command::new(entrypoint(plugin_root)); // lint-subprocess-via-runner: ok resolves the larch entrypoint to the Rust-owned design stage-terminal-state verb
    command.env("CLAUDE_PLUGIN_ROOT", plugin_root);
    command.arg("design").arg("stage-terminal-state");
    command.args(args);
    match command.output() {
        Ok(output) => {
            let _ = fs::write(stdout_log, &output.stdout);
            let _ = fs::write(stderr_log, &output.stderr);
            output.status.code().unwrap_or(1)
        }
        Err(_error) => {
            let _ = fs::write(stdout_log, b"");
            let _ = fs::write(stderr_log, b"");
            1
        }
    }
}

pub fn clarify_failure_stage_args(
    design_tmpdir: &Path,
    exit_code: &str,
    detail_log: &Path,
) -> Vec<String> {
    vec![
        "--design-tmpdir".to_owned(),
        design_tmpdir.display().to_string(),
        "--outcome".to_owned(),
        "failed-clarify".to_owned(),
        "--step".to_owned(),
        "clarify".to_owned(),
        "--phase".to_owned(),
        "clarify-loop".to_owned(),
        "--site".to_owned(),
        "clarify-loop".to_owned(),
        "--trigger".to_owned(),
        "failed".to_owned(),
        "--bail-reason".to_owned(),
        "clarify-hard-halt".to_owned(),
        "--exit-code".to_owned(),
        exit_code.to_owned(),
        "--source-script".to_owned(),
        "clarify-loop".to_owned(),
        "--summary-outcome".to_owned(),
        "failed-clarify".to_owned(),
        "--failure-detail-log".to_owned(),
        detail_log.display().to_string(),
    ]
}

/// The `step0-clarify-hard-halt` entry point.
pub fn step0_clarify_hard_halt(arguments: &[OsString]) -> ExitCode {
    let argv = utf8_arguments(arguments);
    let ns = match parse_wrapper_args(&argv) {
        Ok(ns) => ns,
        Err(code) => return code,
    };
    let env = load_wrapper_env(&ns);
    let plugin_root_value = env_get(&env, "CLAUDE_PLUGIN_ROOT", &ns.plugin_root).to_owned();
    if let Err(code) = require_plugin_root(&plugin_root_value) {
        return code;
    }
    if env_get(&env, "DESIGN_TMPDIR", "").is_empty() {
        eprintln!("/design Step 0b clarify hard halt: DESIGN_TMPDIR required");
        return ExitCode::from(1);
    }
    let design_tmpdir = resolve_like_python(Path::new(env_get(&env, "DESIGN_TMPDIR", "")));
    if let Some(code) = check_pause_and_exit(&env, &design_tmpdir) {
        return code;
    }
    let mut detail = if ns.failure_detail_log.is_empty() {
        let configured = env_get(&env, "CLARIFY_FAILURE_LOG", "");
        if configured.is_empty() {
            design_tmpdir.join("clarify-loop.failure.log")
        } else {
            PathBuf::from(configured)
        }
    } else {
        PathBuf::from(&ns.failure_detail_log)
    };
    let resolved_detail = resolve_like_python(&detail);
    if !resolved_detail.starts_with(&design_tmpdir) {
        detail = design_tmpdir.join("clarify-loop.failure.log");
    }
    if !detail.is_file() {
        let _ = fs::write(&detail, "clarify loop hard halt\n");
    }
    let stdout_log = design_tmpdir.join("design-stage-terminal-state.stdout.log");
    let stderr_log = design_tmpdir.join("design-stage-terminal-state.stderr.log");
    let exit_code = if ns.exit_code.is_empty() {
        "1"
    } else {
        &ns.exit_code
    };
    let _stage_rc = stage_terminal_state_bridge(
        Path::new(&plugin_root_value),
        &stdout_log,
        &stderr_log,
        &clarify_failure_stage_args(&design_tmpdir, exit_code, &detail),
    );
    // The append-failure branches (STAGED=false / non-zero rc) mirror the
    // frozen reference's best-effort failure log; the golden asserts detail-log
    // containment and the unconditional rc 0 below.
    ExitCode::SUCCESS
}

// ---------------------------------------------------------------------------
// `step0-abort-cleanup`
// ---------------------------------------------------------------------------

/// The `step0-abort-cleanup` entry point.
/// Port of `progress_file.validate_run_id`: a non-reserved run identifier of
/// 1..=128 letters, digits, dot, underscore, or dash.
fn is_valid_owned_run_id(value: &str) -> bool {
    !value.is_empty()
        && value.len() <= 128
        && value != "."
        && value != ".."
        && value != "current"
        && value
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'.' | b'_' | b'-'))
}

/// Port of `progress_file.resolve_owned_run_id` for the abort path: process
/// `LARCH_RUN_ID`, then persisted `session-env.sh`/`source-env.sh` values,
/// returning the first candidate that validates.
pub fn resolve_owned_run_id(design_tmpdir: &Path) -> Option<String> {
    let mut candidates: Vec<String> = Vec::new();
    if let Ok(value) = std::env::var("LARCH_RUN_ID")
        && !value.is_empty()
    {
        candidates.push(value);
    }
    for name in ["session-env.sh", "source-env.sh"] {
        let Ok(text) = fs::read_to_string(design_tmpdir.join(name)) else {
            continue;
        };
        for line in text.lines() {
            for prefix in ["LARCH_RUN_ID=", "export LARCH_RUN_ID="] {
                if let Some(rest) = line.strip_prefix(prefix) {
                    candidates.push(
                        rest.trim()
                            .trim_matches(|c: char| c == '\'' || c == '"')
                            .to_owned(),
                    );
                }
            }
        }
    }
    candidates
        .into_iter()
        .find(|value| is_valid_owned_run_id(value))
}

/// Port of `progress_file.resolve_persisted_repo_root`: the first absolute,
/// existing `REPO_ROOT` persisted in `source-env.sh`/`session-env.sh`.
fn resolve_persisted_repo_root(design_tmpdir: &Path) -> Option<PathBuf> {
    for name in ["source-env.sh", "session-env.sh"] {
        let Ok(text) = fs::read_to_string(design_tmpdir.join(name)) else {
            continue;
        };
        for line in text.lines() {
            for prefix in ["REPO_ROOT=", "export REPO_ROOT="] {
                if let Some(rest) = line.strip_prefix(prefix) {
                    let candidate =
                        PathBuf::from(rest.trim().trim_matches(|c: char| c == '\'' || c == '"'));
                    if candidate.is_absolute()
                        && candidate.is_dir()
                        && let Ok(resolved) = candidate.canonicalize()
                    {
                        return Some(resolved);
                    }
                }
            }
        }
    }
    None
}

pub fn step0_abort_cleanup(arguments: &[OsString]) -> ExitCode {
    step0_abort_cleanup_with(arguments, &LiveStep0Runner)
}

fn step0_abort_cleanup_with(arguments: &[OsString], runner: &dyn Step0Runner) -> ExitCode {
    let argv = utf8_arguments(arguments);
    let ns = match parse_wrapper_args(&argv) {
        Ok(ns) => ns,
        Err(code) => return code,
    };
    let env = load_wrapper_env(&ns);
    let plugin_root_value = env_get(&env, "CLAUDE_PLUGIN_ROOT", &ns.plugin_root).to_owned();
    let plugin_root = match require_plugin_root(&plugin_root_value) {
        Ok(root) => root,
        Err(code) => return code,
    };
    if env_get(&env, "DESIGN_TMPDIR", "").is_empty() {
        eprintln!("/design Step 0 abort-cleanup: DESIGN_TMPDIR required");
        return ExitCode::from(1);
    }
    if let Err(message) = validate_claude_pid(&ns.claude_pid) {
        eprintln!("design-step0-abort-cleanup.sh: {message}");
        return ExitCode::from(CONFIGURATION_ERROR_RC);
    }
    let design_tmpdir = PathBuf::from(env_get(&env, "DESIGN_TMPDIR", ""));
    println!("**⚠ /design: aborted by operator: {}**", ns.reason);
    // Best-effort failure-log breadcrumb (larch run-log append-failure child).
    let _ = runner.run(
        &plugin_root,
        &[
            "run-log".to_owned(),
            "append-failure".to_owned(),
            "--log".to_owned(),
            design_tmpdir
                .join("execution-issues.md")
                .display()
                .to_string(),
            "--site".to_owned(),
            "design Step 0".to_owned(),
            "--tool".to_owned(),
            ns.tool.clone(),
            "--exit-code".to_owned(),
            "0".to_owned(),
            "--category".to_owned(),
            "Warnings".to_owned(),
            "--output-file".to_owned(),
            design_tmpdir
                .join("execution-issues.md")
                .display()
                .to_string(),
            "--redact".to_owned(),
        ],
        &[],
        false,
    );
    // Best-effort progress deactivation before cleanup, matching frozen
    // `step0_abort_cleanup_main`: clear the owned run pointer so an aborted
    // /design stops showing as active once its tmpdir is gone.
    if let (Some(run_id), Some(repo_root)) = (
        resolve_owned_run_id(&design_tmpdir),
        resolve_persisted_repo_root(&design_tmpdir),
    ) {
        let _ = runner.run(
            &plugin_root,
            &[
                "progress".to_owned(),
                "deactivate".to_owned(),
                "--repo-root".to_owned(),
                repo_root.display().to_string(),
                "--run-id".to_owned(),
                run_id,
            ],
            &[],
            false,
        );
    }
    let cleanup = runner.run(
        &plugin_root,
        &[
            "session".to_owned(),
            "cleanup-tmpdir".to_owned(),
            "--dir".to_owned(),
            design_tmpdir.display().to_string(),
        ],
        &[],
        false,
    );
    if cleanup.code != 0 {
        return exit_from_i32(cleanup.code);
    }
    if let Err(message) = reap_pid_residuals(&ns.claude_pid) {
        eprintln!("design-step0-abort-cleanup.sh: {message}");
        return ExitCode::from(1);
    }
    ExitCode::SUCCESS
}

// ---------------------------------------------------------------------------
// route/init helpers shared by `step0-route` and `step0-init`
// ---------------------------------------------------------------------------

fn is_all_digits(value: &str) -> bool {
    !value.is_empty() && value.bytes().all(|byte| byte.is_ascii_digit())
}

fn recover_route_state_values(env: &Env, design_tmpdir: &Path) -> Env {
    let mut merged: Env = BTreeMap::new();
    for key in ROUTE_STATE_KEYS {
        let value = env_get(env, key, "");
        if !value.is_empty() {
            let _ = merged.insert(key.to_owned(), value.to_owned());
        }
    }
    let Ok(route_state) =
        phase_driver_read_result_env(&design_tmpdir.join(ROUTE_STATE_PATH), &ROUTE_STATE_KEYS)
    else {
        return merged;
    };
    // `dict(...)` keeps the last value per key.
    let mut last: Env = BTreeMap::new();
    for (key, value) in route_state {
        let _ = last.insert(key, value);
    }
    for (key, value) in last {
        if !value.is_empty() && merged.get(&key).is_none_or(String::is_empty) {
            let _ = merged.insert(key, value);
        }
    }
    merged
}

fn gap_fill_route_state_values(env: &mut Env, design_tmpdir: &Path) {
    for (key, value) in recover_route_state_values(env, design_tmpdir) {
        if !value.is_empty() && env_get(env, &key, "").is_empty() {
            let _ = env.insert(key, value);
        }
    }
}

fn bind_step0_route_issue_env(
    env: &mut Env,
    design_tmpdir: &Path,
    issue_number_arg: &str,
) -> Result<(), ExitCode> {
    if !issue_number_arg.is_empty() {
        if is_all_digits(issue_number_arg) {
            let _ = env.insert("ISSUE_NUMBER".to_owned(), issue_number_arg.to_owned());
        } else {
            eprintln!("**⚠ Step 0b: --issue-number requires numeric value; aborting /design**");
            return Err(ExitCode::from(1));
        }
    }
    let kind = {
        let value = env_get(env, "POSITIONAL_KIND", "none");
        if value.is_empty() { "none" } else { value }.to_owned()
    };
    if kind == "issue" {
        let positional = env_get(env, "POSITIONAL_VALUE", "").to_owned();
        if is_all_digits(&positional) {
            let _ = env.insert("ISSUE_NUMBER".to_owned(), positional);
        } else {
            eprintln!(
                "**⚠ Step 0b: POSITIONAL_KIND=issue requires numeric POSITIONAL_VALUE; aborting /design**"
            );
            return Err(ExitCode::from(1));
        }
    }
    if kind == "verbal" && env_get(env, "ISSUE_NUMBER", "").is_empty() {
        eprintln!(
            "**⚠ Step 0b: POSITIONAL_KIND=verbal requires ISSUE_NUMBER from /larch:issue before routing; aborting /design**"
        );
        return Err(ExitCode::from(1));
    }
    if env_get(env, "ISSUE_NUMBER", "").is_empty() {
        gap_fill_route_state_values(env, design_tmpdir);
    }
    if !matches!(kind.as_str(), "issue" | "none" | "verbal") {
        let shown = if kind.is_empty() { "<empty>" } else { &kind };
        eprintln!("**⚠ Step 0b: invalid POSITIONAL_KIND={shown}; aborting /design**");
        return Err(ExitCode::from(1));
    }
    Ok(())
}

fn materialize_step0_feature_description(design_tmpdir: &Path, env: &Env, init_route: &str) {
    if init_route != "proceed" && init_route != "already-planned" {
        return;
    }
    let issue_body = design_tmpdir.join("issue-body.txt");
    if issue_body.is_file() {
        let title = env_get(env, "ISSUE_TITLE", "");
        let prefix = if title.is_empty() {
            String::new()
        } else {
            format!("# {title}\n\n")
        };
        let body = fs::read(&issue_body)
            .map(|bytes| String::from_utf8_lossy(&bytes).into_owned())
            .unwrap_or_default();
        let _ = fs::write(
            design_tmpdir.join("feature-description.txt"),
            format!("{prefix}{body}"),
        );
    } else if env_get(env, "POSITIONAL_KIND", "") == "verbal" {
        let value = env_get(env, "POSITIONAL_VALUE", "");
        if !value.is_empty() {
            let _ = fs::write(
                design_tmpdir.join("feature-description.txt"),
                format!("{value}\n"),
            );
        }
    }
}

fn init_driver_args(design_tmpdir: &Path, env: &Env, claude_pid: &str) -> Vec<String> {
    let mut args = vec![
        "design".to_owned(),
        "init-runparams".to_owned(),
        "--design-tmpdir".to_owned(),
        design_tmpdir.display().to_string(),
        "--issue".to_owned(),
        env_get(env, "ISSUE_NUMBER", "").to_owned(),
        "--session-id".to_owned(),
        env_get(env, "SESSION_ID", "").to_owned(),
        "--claude-pid".to_owned(),
        claude_pid.to_owned(),
        "--partition-requested".to_owned(),
        env_get(env, "partition_requested", "false").to_owned(),
        "--brainstorm-requested".to_owned(),
        env_get(env, "brainstorm_requested", "false").to_owned(),
        "--approve-requested".to_owned(),
        env_get(env, "approve_requested", "false").to_owned(),
        "--skip-approve-requested".to_owned(),
        env_get(env, "skip_approve_requested", "false").to_owned(),
        "--difficulty".to_owned(),
        env_get(env, "difficulty", "").to_owned(),
    ];
    let repo = env_get(env, "REPO", "");
    if !repo.is_empty() {
        args.push("--repo".to_owned());
        args.push(repo.to_owned());
    }
    args
}

/// Port of `_run_step0_init_driver`. Returns `(rc, result_rows)`.
fn run_step0_init_driver(
    runner: &dyn Step0Runner,
    plugin_root: &Path,
    design_tmpdir: &Path,
    env: &Env,
    claude_pid: &str,
    emit_stdout: bool,
) -> (i32, Env) {
    let capture_path = design_tmpdir.join(format!(
        ".larch-init-stdout.{}.{claude_pid}",
        std::process::id()
    ));
    let outcome = runner.run(
        plugin_root,
        &init_driver_args(design_tmpdir, env, claude_pid),
        &[],
        false,
    );
    let _ = fs::write(&capture_path, &outcome.stdout);
    if outcome.code == i32::from(CONFIGURATION_ERROR_RC) {
        if !outcome.stderr.is_empty() {
            eprint_line(&outcome.stderr);
        }
        eprintln!(
            "**⚠ Step 0b: design-init-runparams.sh configuration error (exit 2); aborting /design**"
        );
        let _ = fs::remove_file(&capture_path);
        return (1, BTreeMap::new());
    }
    if outcome.code != 0 && outcome.code != 1 {
        if !outcome.stderr.is_empty() {
            eprint_line(&outcome.stderr);
        }
        eprintln!(
            "**⚠ Step 0b: design-init-runparams.sh failed (exit {}); aborting /design**",
            outcome.code
        );
        let _ = fs::remove_file(&capture_path);
        return (1, BTreeMap::new());
    }
    let result = read_result_pairs(
        &design_tmpdir.join(".design-init-runparams-result.env"),
        Some(&capture_path),
        &INIT_RESULT_KEYS,
    );
    let _ = fs::remove_file(&capture_path);
    if result.is_empty() {
        eprintln!(
            "**⚠ Step 0b: read-result-env.sh failed for design-init-runparams result (exit 1); aborting /design**"
        );
        return (1, BTreeMap::new());
    }
    let init_status = env_get(&result, "INIT_STATUS", "");
    if outcome.code == 0
        && (init_status != "ok" || !design_tmpdir.join("run-params.json").is_file())
    {
        eprintln!(
            "**⚠ Step 0b: design-init-runparams.sh exited 0 without INIT_STATUS=ok and run-params.json; aborting /design**"
        );
        return (1, BTreeMap::new());
    }
    if outcome.code == 1 {
        if !outcome.stderr.is_empty() {
            eprint_line(&outcome.stderr);
        }
        let shown = match init_status {
            "" => "unknown",
            other => other,
        };
        eprintln!(
            "**⚠ Step 0b: design-init-runparams.sh failed (INIT_STATUS={shown}); aborting /design**"
        );
        return (1, BTreeMap::new());
    }
    if emit_stdout {
        emit_step0_init_rows(&result);
    }
    (0, result)
}

fn eprint_line(text: &str) {
    if text.ends_with('\n') {
        eprint!("{text}");
    } else {
        eprintln!("{text}");
    }
}

fn print_line(text: &str) {
    if text.ends_with('\n') {
        print!("{text}");
    } else {
        println!("{text}");
    }
}

fn emit_step0_init_rows(result: &Env) {
    for key in ["INIT_STATUS", "RENAMED", "RUN_PARAMS_PATH"] {
        println!("{key}={}", env_get(result, key, ""));
    }
}

fn emit_step0_route_rows(route: &str, resume_step: &str, route_env: &Env, env: &Env) {
    let marker_cleared = env_get(route_env, "MARKER_CLEARED", "");
    if !resume_step.is_empty() {
        if !marker_cleared.is_empty() {
            println!("MARKER_CLEARED={marker_cleared}");
        }
        println!("🔓 resumed from STEP={resume_step}");
    }
    println!("ROUTE={route}");
    if !resume_step.is_empty() {
        println!("RESUME_STEP={resume_step}");
    }
    if !marker_cleared.is_empty() {
        println!("MARKER_CLEARED={marker_cleared}");
    }
    for key in [
        "TITLE_FILTER_REASON",
        "TITLE_FILTER_MARKER",
        "DESIGN_REENTRY_MARKER_PATH",
    ] {
        let value = env_get(route_env, key, "");
        if !value.is_empty() {
            println!("{key}={value}");
        }
    }
    println!(
        "HAS_CLARIFY_LABEL={}",
        env_get(env, "HAS_CLARIFY_LABEL", "false")
    );
    println!("ISSUE_NUMBER={}", env_get(env, "ISSUE_NUMBER", ""));
    println!("ISSUE_TITLE={}", env_get(env, "ISSUE_TITLE", ""));
    let repo = env_get(env, "REPO", "");
    if !repo.is_empty() {
        println!("REPO={repo}");
    }
}

fn refresh_route_source_env(
    runner: &dyn Step0Runner,
    plugin_root: &Path,
    design_tmpdir: &Path,
    env: &Env,
    claude_pid: &str,
) -> i32 {
    let recovered = recover_route_state_values(env, design_tmpdir);
    let session_id = env_get(env, "SESSION_ID", "");
    let issue_number = env_get(&recovered, "ISSUE_NUMBER", "");
    if session_id.is_empty() {
        eprintln!("**⚠ Step 0b: route missing SESSION_ID; aborting /design**");
        return 1;
    }
    if issue_number.is_empty() || !is_all_digits(issue_number) {
        eprintln!("**⚠ Step 0b: route could not recover numeric ISSUE_NUMBER; aborting /design**");
        return 1;
    }
    let run_id = {
        let value = env_get(env, "LARCH_RUN_ID", "");
        if value.is_empty() { session_id } else { value }
    };
    let mut args = vec![
        "session".to_owned(),
        "write-design-env".to_owned(),
        "--output".to_owned(),
        design_tmpdir.join("source-env.sh").display().to_string(),
        "--design-tmpdir".to_owned(),
        design_tmpdir.display().to_string(),
        "--session-id".to_owned(),
        session_id.to_owned(),
        "--run-id".to_owned(),
        run_id.to_owned(),
        "--issue-number".to_owned(),
        issue_number.to_owned(),
        "--claude-pid".to_owned(),
        claude_pid.to_owned(),
    ];
    let repo = env_get(&recovered, "REPO", "");
    if !repo.is_empty() {
        args.push("--repo".to_owned());
        args.push(repo.to_owned());
    }
    let outcome = runner.run(plugin_root, &args, &[], false);
    if outcome.code == 0 {
        return 0;
    }
    if !outcome.stderr.is_empty() {
        eprint_line(&outcome.stderr);
    }
    eprintln!(
        "**⚠ Step 0b: session write-design-env failed during route refresh (exit {}); aborting /design**",
        outcome.code
    );
    1
}

const TERMINAL_CANCEL_ROUTES: [&str; 2] = ["cancel-title-filter", "cancel-reentry-guard"];

/// Bundled route-finish inputs mirroring `Step0RouteFinishContext`.
struct RouteFinish<'a> {
    runner: &'a dyn Step0Runner,
    plugin_root: &'a Path,
    design_tmpdir: &'a Path,
    route: &'a str,
    resume_step: &'a str,
    route_env: &'a Env,
    env: &'a Env,
    claude_pid: &'a str,
}

fn finish_step0_route(ctx: &RouteFinish<'_>) -> ExitCode {
    let mut rows: Vec<(String, String)> = vec![("ROUTE".to_owned(), ctx.route.to_owned())];
    if !ctx.resume_step.is_empty() {
        rows.push(("RESUME_STEP".to_owned(), ctx.resume_step.to_owned()));
    }
    rows.push((
        "HAS_CLARIFY_LABEL".to_owned(),
        env_get(ctx.env, "HAS_CLARIFY_LABEL", "false").to_owned(),
    ));
    rows.push((
        "ISSUE_NUMBER".to_owned(),
        env_get(ctx.env, "ISSUE_NUMBER", "").to_owned(),
    ));
    rows.push((
        "ISSUE_TITLE".to_owned(),
        env_get(ctx.env, "ISSUE_TITLE", "").to_owned(),
    ));
    let repo = env_get(ctx.env, "REPO", "");
    if !repo.is_empty() {
        rows.push(("REPO".to_owned(), repo.to_owned()));
    }
    let brainstorm = env_get(ctx.env, "brainstorm_requested", "");
    if !brainstorm.is_empty() {
        rows.push(("brainstorm_requested".to_owned(), brainstorm.to_owned()));
    }
    write_kv_file(&ctx.design_tmpdir.join(ROUTE_STATE_PATH), &rows);

    if ctx.route == "proceed" {
        if let Some(code) = check_pause_and_exit(ctx.env, ctx.design_tmpdir) {
            return code;
        }
        materialize_step0_feature_description(ctx.design_tmpdir, ctx.env, "proceed");
        let (init_rc, init_result) = run_step0_init_driver(
            ctx.runner,
            ctx.plugin_root,
            ctx.design_tmpdir,
            ctx.env,
            ctx.claude_pid,
            false,
        );
        if init_rc != 0 {
            return exit_from_i32(init_rc);
        }
        emit_step0_route_rows(ctx.route, ctx.resume_step, ctx.route_env, ctx.env);
        emit_step0_init_rows(&init_result);
        return ExitCode::SUCCESS;
    }
    if ctx.route.starts_with("resume@") || TERMINAL_CANCEL_ROUTES.contains(&ctx.route) {
        let refresh_rc = refresh_route_source_env(
            ctx.runner,
            ctx.plugin_root,
            ctx.design_tmpdir,
            ctx.env,
            ctx.claude_pid,
        );
        if refresh_rc != 0 {
            return exit_from_i32(refresh_rc);
        }
    }
    emit_step0_route_rows(ctx.route, ctx.resume_step, ctx.route_env, ctx.env);
    ExitCode::SUCCESS
}

// ---------------------------------------------------------------------------
// `step0-route`
// ---------------------------------------------------------------------------

/// The `step0-route` entry point.
pub fn step0_route(arguments: &[OsString]) -> ExitCode {
    step0_route_with(arguments, &LiveStep0Runner)
}

#[allow(clippy::too_many_lines)] // One verb, one Python main ported branch for branch.
fn step0_route_with(arguments: &[OsString], runner: &dyn Step0Runner) -> ExitCode {
    let argv = utf8_arguments(arguments);
    let ns = match parse_wrapper_args(&argv) {
        Ok(ns) => ns,
        Err(code) => return code,
    };
    let mut env = load_wrapper_env(&ns);
    let plugin_root_value = env_get(&env, "CLAUDE_PLUGIN_ROOT", &ns.plugin_root).to_owned();
    let plugin_root = match require_plugin_root(&plugin_root_value) {
        Ok(root) => root,
        Err(code) => return code,
    };
    let design_tmpdir = match require_design_tmpdir(&env, None) {
        Ok(path) => path,
        Err(code) => return code,
    };
    if let Some(code) = check_pause_and_exit(&env, &design_tmpdir) {
        return code;
    }
    for (key, value) in load_bash_quoted_env(
        &design_tmpdir.join(".design-step0-parsed.env"),
        &PARSED_ENV_KEYS,
    ) {
        let _ = env.insert(key, value);
    }
    if let Err(code) = bind_step0_route_issue_env(&mut env, &design_tmpdir, &ns.issue_number) {
        return code;
    }
    if !env_get(&env, "ISSUE_NUMBER", "").is_empty() {
        if env_get(&env, "REPO", "").is_empty() {
            let _ = env.insert("REPO".to_owned(), runner.resolve_repo());
        }
        let issue = env_get(&env, "ISSUE_NUMBER", "").to_owned();
        let repo = env_get(&env, "REPO", "").to_owned();
        if let Ok((title, body, has_clarify)) = runner.read_issue(&issue, &repo) {
            let _ = env.insert("ISSUE_TITLE".to_owned(), title);
            let _ = env.insert("HAS_CLARIFY_LABEL".to_owned(), has_clarify);
            let _ = fs::write(design_tmpdir.join("issue-body.txt"), body);
        } else {
            eprintln!("**⚠ Step 0b: gh issue view failed for issue {issue}; aborting /design**");
            return ExitCode::from(1);
        }
    }
    let capture_path = design_tmpdir.join(format!(".larch-route-stdout.{}", std::process::id()));
    let mut route_cmd = vec![
        "design".to_owned(),
        "route".to_owned(),
        "--design-tmpdir".to_owned(),
        design_tmpdir.display().to_string(),
        "--issue".to_owned(),
        env_get(&env, "ISSUE_NUMBER", "").to_owned(),
        "--issue-title".to_owned(),
        env_get(&env, "ISSUE_TITLE", "").to_owned(),
        "--issue-body-file".to_owned(),
        design_tmpdir.join("issue-body.txt").display().to_string(),
        "--has-clarify-label".to_owned(),
        env_get(&env, "HAS_CLARIFY_LABEL", "false").to_owned(),
        "--claude-pid".to_owned(),
        ns.claude_pid.clone(),
        "--session-id".to_owned(),
        env_get(&env, "SESSION_ID", "").to_owned(),
        "--partition-requested".to_owned(),
        env_get(&env, "partition_requested", "false").to_owned(),
        "--brainstorm-requested".to_owned(),
        env_get(&env, "brainstorm_requested", "false").to_owned(),
        "--approve-requested".to_owned(),
        env_get(&env, "approve_requested", "false").to_owned(),
        "--skip-approve-requested".to_owned(),
        env_get(&env, "skip_approve_requested", "false").to_owned(),
        "--difficulty".to_owned(),
        env_get(&env, "difficulty", "").to_owned(),
    ];
    let repo = env_get(&env, "REPO", "").to_owned();
    if !repo.is_empty() {
        route_cmd.push("--repo".to_owned());
        route_cmd.push(repo);
    }
    let outcome = runner.run(&plugin_root, &route_cmd, &[], false);
    let _ = fs::write(&capture_path, &outcome.stdout);
    if outcome.code == i32::from(CONFIGURATION_ERROR_RC) {
        if !outcome.stderr.is_empty() {
            eprint_line(&outcome.stderr);
        }
        eprintln!("**⚠ Step 0b: design-route.sh configuration error (exit 2); aborting /design**");
        let _ = fs::remove_file(&capture_path);
        return ExitCode::from(1);
    }
    if outcome.code != 0 {
        if !outcome.stderr.is_empty() {
            eprint_line(&outcome.stderr);
        }
        eprintln!(
            "**⚠ Step 0b: design-route.sh failed (exit {}); aborting /design**",
            outcome.code
        );
        let _ = fs::remove_file(&capture_path);
        return ExitCode::from(1);
    }
    let route_env = read_result_pairs(
        &design_tmpdir.join(".design-route-result.env"),
        Some(&capture_path),
        &ROUTE_RESULT_KEYS,
    );
    let _ = fs::remove_file(&capture_path);
    if route_env.is_empty() {
        eprintln!("**⚠ Step 0b: could not read design-route result env; aborting /design**");
        return ExitCode::from(1);
    }
    let route = env_get(&route_env, "ROUTE", "").to_owned();
    if env_get(&route_env, "BRAINSTORM_PREFIX", "") == "true" {
        let _ = env.insert("brainstorm_requested".to_owned(), "true".to_owned());
        println!(
            "**ℹ /design: detected Brainstorm title prefix: auto-enabling brainstorm mode (run-params `brainstorm_requested=true`) even though --brainstorm was not on argv.**"
        );
    }
    if route == "cancel-pause-load" {
        let result_env_path = design_tmpdir.join(".design-route-result.env");
        if result_env_path.is_file() {
            replay_warn_error(&result_env_path);
        }
        eprintln!(
            "**⚠ /design: pause resume state could not be loaded safely; aborting before fresh routing. Inspect pause-load ERROR breadcrumbs above, fix the pause block, then re-invoke /design.**"
        );
        return ExitCode::from(1);
    }
    let resume_step = route.strip_prefix("resume@").unwrap_or("").to_owned();
    let valid = matches!(
        route.as_str(),
        "proceed"
            | "clarify"
            | "already-planned"
            | "cancel-title-filter"
            | "cancel-reentry-guard"
            | "cancel-pause-load"
    ) || (route.starts_with("resume@") && !resume_step.is_empty());
    if !valid {
        eprintln!(
            "**⚠ Step 0b: missing or invalid ROUTE after design-route.sh; aborting /design**"
        );
        return ExitCode::from(1);
    }
    finish_step0_route(&RouteFinish {
        runner,
        plugin_root: &plugin_root,
        design_tmpdir: &design_tmpdir,
        route: &route,
        resume_step: &resume_step,
        route_env: &route_env,
        env: &env,
        claude_pid: &ns.claude_pid,
    })
}

/// Port of `_replay_warn_error`: emit WARN/ERROR rows to stderr.
fn replay_warn_error(path: &Path) {
    let Ok(bytes) = fs::read(path) else {
        return;
    };
    let text = String::from_utf8_lossy(&bytes).into_owned();
    let rows = parse_stdout_kv(&text);
    for value in kv_all(&rows, "WARN") {
        eprintln!("WARN={value}");
    }
    for value in kv_all(&rows, "ERROR") {
        eprintln!("ERROR={value}");
    }
}

// ---------------------------------------------------------------------------
// `step0-init`
// ---------------------------------------------------------------------------

fn load_route_result_route(design_tmpdir: &Path) -> String {
    let result = read_result_pairs(
        &design_tmpdir.join(".design-route-result.env"),
        None,
        &["ROUTE"],
    );
    env_get(&result, "ROUTE", "").to_owned()
}

/// The `step0-init` entry point.
pub fn step0_init(arguments: &[OsString]) -> ExitCode {
    step0_init_with(arguments, &LiveStep0Runner)
}

fn step0_init_with(arguments: &[OsString], runner: &dyn Step0Runner) -> ExitCode {
    let argv = utf8_arguments(arguments);
    let ns = match parse_wrapper_args(&argv) {
        Ok(ns) => ns,
        Err(code) => return code,
    };
    let mut env = load_wrapper_env(&ns);
    let plugin_root_value = env_get(&env, "CLAUDE_PLUGIN_ROOT", &ns.plugin_root).to_owned();
    let plugin_root = match require_plugin_root(&plugin_root_value) {
        Ok(root) => root,
        Err(code) => return code,
    };
    let design_tmpdir = match require_design_tmpdir(&env, None) {
        Ok(path) => path,
        Err(code) => return code,
    };
    if let Some(code) = check_pause_and_exit(&env, &design_tmpdir) {
        return code;
    }
    for (key, value) in load_bash_quoted_env(
        &design_tmpdir.join(".design-step0-parsed.env"),
        &PARSED_ENV_KEYS,
    ) {
        let _ = env.insert(key, value);
    }
    if let Ok(pairs) =
        phase_driver_read_result_env(&design_tmpdir.join(ROUTE_STATE_PATH), &ROUTE_STATE_KEYS)
    {
        for (key, value) in pairs {
            let _ = env.insert(key, value);
        }
    }
    let init_route = load_route_result_route(&design_tmpdir);
    materialize_step0_feature_description(&design_tmpdir, &env, &init_route);
    let (rc, _result) = run_step0_init_driver(
        runner,
        &plugin_root,
        &design_tmpdir,
        &env,
        &ns.claude_pid,
        false,
    );
    exit_from_i32(rc)
}

// ---------------------------------------------------------------------------
// `step0-session`
// ---------------------------------------------------------------------------

fn kv_line_value(line: &str, key: &str) -> String {
    line.strip_prefix(key)
        .and_then(|rest| rest.strip_prefix('='))
        .unwrap_or("")
        .to_owned()
}

struct DegradedGateState {
    degraded: String,
    both_down: String,
    step0_status: String,
}

/// Port of `relay_degraded_tools_gate_stdout`: relay recognized rows and derive
/// the terminal `STEP0_STATUS`. The `PRESENCE_INPUT_EMPTY` execution-issue append
/// is the frozen reference's best-effort breadcrumb and is not relayed here.
fn relay_degraded_tools_gate_stdout(stdout: &str, design_tmpdir: &Path) -> DegradedGateState {
    let mut degraded = "false".to_owned();
    let mut both_down = "false".to_owned();
    let mut both_down_seen = false;
    let mut in_explanation = false;
    for line in stdout.split('\n') {
        if line == "DEGRADED_EXPLANATION_BEGIN" {
            in_explanation = true;
            println!("{line}");
        } else if line == "DEGRADED_EXPLANATION_END" {
            in_explanation = false;
            println!("{line}");
        } else if line.starts_with("DEGRADED=") {
            degraded = kv_line_value(line, "DEGRADED");
            println!("{line}");
        } else if line.starts_with("BOTH_DOWN=") {
            both_down = kv_line_value(line, "BOTH_DOWN");
            both_down_seen = true;
            println!("{line}");
        } else if line.starts_with("DEGRADED_HARD_FAIL=")
            || line.starts_with("PRESENCE_INPUT_EMPTY=")
            || line.starts_with("CODEX_STATE=")
            || line.starts_with("CURSOR_STATE=")
            || in_explanation
        {
            println!("{line}");
        }
    }
    let mut step0_status = "ok".to_owned();
    if degraded == "true" {
        if both_down_seen && both_down == "true" {
            "degraded-both-down-hard-fail".clone_into(&mut step0_status);
        } else if both_down_seen
            && both_down == "false"
            && design_tmpdir
                .join(".degraded-tools-gate-prompted")
                .is_file()
        {
            "degraded-one-down".clone_into(&mut step0_status);
        } else {
            "needs-degraded-decision".clone_into(&mut step0_status);
        }
    }
    DegradedGateState {
        degraded,
        both_down,
        step0_status,
    }
}

/// The `step0-session` entry point (run-log storage preflight then session set-up).
pub fn step0_session(arguments: &[OsString]) -> ExitCode {
    step0_session_with(arguments, &LiveStep0Runner)
}

fn repo_root_string() -> String {
    std::env::current_dir()
        .map(|dir| resolve_like_python(&dir).display().to_string())
        .unwrap_or_default()
}

fn step0_session_with(arguments: &[OsString], runner: &dyn Step0Runner) -> ExitCode {
    let argv = utf8_arguments(arguments);
    let ns = match parse_wrapper_args(&argv) {
        Ok(ns) => ns,
        Err(code) => return code,
    };
    let plugin_root = match require_plugin_root(&ns.plugin_root) {
        Ok(root) => root,
        Err(code) => return code,
    };
    let repo_root = repo_root_string();
    let storage = runner.run(
        &plugin_root,
        &[
            "run-log".to_owned(),
            "storage-preflight".to_owned(),
            "--repo-root".to_owned(),
            repo_root.clone(),
        ],
        &[],
        false,
    );
    if storage.code != 0 {
        if !storage.stderr.is_empty() {
            eprint_line(&storage.stderr);
        }
        eprintln!("**⚠ /design: run-log storage preflight failed; aborting before session setup**");
        return exit_from_i32(storage.code);
    }
    let storage_kv = parse_stdout_kv(&storage.stdout);
    let storage_mode = kv_last(&storage_kv, "RUN_LOG_STORAGE", "");
    let storage_state = kv_last(&storage_kv, "STORAGE_PREFLIGHT", "");
    let valid_storage_state = (storage_mode == "enabled" && storage_state == "ok")
        || (storage_mode == "disabled" && storage_state == "skipped-disabled");
    if kv_last(&storage_kv, "PREFLIGHT_OK", "") != "true" || !valid_storage_state {
        eprintln!(
            "**⚠ /design: run-log storage preflight returned an invalid state; aborting before session setup**"
        );
        return ExitCode::from(EXIT_INTERNAL_ERROR);
    }
    step0_session_main(runner, &ns, &plugin_root, &repo_root)
}

#[allow(clippy::too_many_lines)] // One verb, one Python main ported branch for branch.
fn step0_session_main(
    runner: &dyn Step0Runner,
    ns: &WrapperNs,
    plugin_root: &Path,
    repo_root: &str,
) -> ExitCode {
    let (cache, parsed) = match parse_and_persist(runner, ns, plugin_root) {
        Ok(result) => result,
        Err(code) => return code,
    };
    emit_parse_kvs(&cache, &parsed);
    // Best-effort statusline + progress clear.
    let _ = runner.run(
        plugin_root,
        &[
            "progress".to_owned(),
            "install-statusline".to_owned(),
            "--plugin-root".to_owned(),
            plugin_root.display().to_string(),
            "--repo-root".to_owned(),
            repo_root.to_owned(),
            "--notice".to_owned(),
        ],
        &[],
        false,
    );
    let _ = runner.run(
        plugin_root,
        &[
            "progress".to_owned(),
            "clear".to_owned(),
            "--repo-root".to_owned(),
            repo_root.to_owned(),
        ],
        &[],
        false,
    );
    let setup = runner.run(
        plugin_root,
        &[
            "session".to_owned(),
            "setup".to_owned(),
            "--prefix".to_owned(),
            "claude-design".to_owned(),
            "--skip-repo-check".to_owned(),
            "--check-reviewers".to_owned(),
        ],
        &[],
        true,
    );
    if !setup.stdout.is_empty() {
        print_line(&setup.stdout);
    }
    if setup.code != 0 {
        return exit_from_i32(setup.code);
    }
    let setup_kv = parse_stdout_kv(&setup.stdout);
    let design_tmpdir = kv_last(&setup_kv, "SESSION_TMPDIR", "").to_owned();
    let session_id = kv_last(&setup_kv, "SESSION_ID", "").to_owned();
    if design_tmpdir.is_empty() || session_id.is_empty() {
        eprintln!("**⚠ /design: session setup output missing SESSION_TMPDIR or SESSION_ID**");
        return ExitCode::from(1);
    }
    let design_path = PathBuf::from(&design_tmpdir);
    if let Ok(bytes) = fs::read(&cache) {
        let _ = fs::write(design_path.join(".design-step0-parsed.env"), bytes);
    }
    let _ = runner.run(
        plugin_root,
        &[
            "token".to_owned(),
            "mark".to_owned(),
            "design Step 0: session setup".to_owned(),
        ],
        &[("DESIGN_TMPDIR".to_owned(), design_tmpdir.clone())],
        false,
    );
    let codex_binary = kv_last(&setup_kv, "CODEX_BINARY_FOUND", "").to_owned();
    let cursor_binary = kv_last(&setup_kv, "CURSOR_BINARY_FOUND", "").to_owned();
    let active_run_id = {
        let run_id = env_get(&parsed, "run_id", "");
        if run_id.is_empty() {
            &session_id
        } else {
            run_id
        }
        .to_owned()
    };
    // Lifecycle start.
    let lifecycle = runner.run(
        plugin_root,
        &[
            "run-log".to_owned(),
            "lifecycle-start".to_owned(),
            "--repo-root".to_owned(),
            repo_root.to_owned(),
            "--skill".to_owned(),
            "design".to_owned(),
            "--run-id".to_owned(),
            active_run_id.clone(),
            "--log-root".to_owned(),
            design_path.join("larch-logs").display().to_string(),
            "--adopt-existing".to_owned(),
        ],
        &[],
        false,
    );
    if !lifecycle.stdout.is_empty() {
        print_line(&lifecycle.stdout);
    }
    let lifecycle_kv = parse_stdout_kv(&lifecycle.stdout);
    if lifecycle.code != 0 || kv_last(&lifecycle_kv, "LIFECYCLE_STARTED", "") != "true" {
        if !lifecycle.stderr.is_empty() {
            eprint_line(&lifecycle.stderr);
        }
        eprintln!("**⚠ /design: lifecycle start failed; preserving the session**");
        return exit_from_i32(if lifecycle.code == 0 {
            i32::from(EXIT_INTERNAL_ERROR)
        } else {
            lifecycle.code
        });
    }
    let reviewer = runner.run(
        plugin_root,
        &["agent".to_owned(), "check-reviewers".to_owned()],
        &[],
        false,
    );
    if !reviewer.stdout.is_empty() {
        print_line(&reviewer.stdout);
    }
    let reviewer_kv = if reviewer.code == 0 {
        parse_stdout_kv(&reviewer.stdout)
    } else {
        Vec::new()
    };
    let pick = |key: &str, fallback: &str| -> String {
        let from_reviewer = kv_last(&reviewer_kv, key, "");
        if !from_reviewer.is_empty() || reviewer_kv.iter().any(|(row, _)| row == key) {
            return from_reviewer.to_owned();
        }
        let from_setup = kv_last(&setup_kv, key, "");
        if from_setup.is_empty() && !setup_kv.iter().any(|(row, _)| row == key) {
            fallback.to_owned()
        } else {
            from_setup.to_owned()
        }
    };
    let mut wdce = vec![
        "session".to_owned(),
        "write-design-env".to_owned(),
        "--output".to_owned(),
        design_path.join("source-env.sh").display().to_string(),
        "--design-tmpdir".to_owned(),
        design_tmpdir,
        "--session-id".to_owned(),
        session_id,
        "--run-id".to_owned(),
        active_run_id.clone(),
        "--claude-pid".to_owned(),
        ns.claude_pid.clone(),
        "--repo-root".to_owned(),
        repo_root.to_owned(),
        "--live-mutation-ok".to_owned(),
        "true".to_owned(),
    ];
    for (flag, value) in [
        ("--codex-present", pick("CODEX_PRESENT", "")),
        ("--cursor-present", pick("CURSOR_PRESENT", "")),
        ("--codex-binary-found", {
            let value = kv_last(&reviewer_kv, "CODEX_BINARY_FOUND", "");
            if value.is_empty()
                && !reviewer_kv
                    .iter()
                    .any(|(row, _)| row == "CODEX_BINARY_FOUND")
            {
                codex_binary.clone()
            } else {
                value.to_owned()
            }
        }),
        ("--cursor-binary-found", {
            let value = kv_last(&reviewer_kv, "CURSOR_BINARY_FOUND", "");
            if value.is_empty()
                && !reviewer_kv
                    .iter()
                    .any(|(row, _)| row == "CURSOR_BINARY_FOUND")
            {
                cursor_binary.clone()
            } else {
                value.to_owned()
            }
        }),
    ] {
        if !value.is_empty() {
            wdce.push(flag.to_owned());
            wdce.push(value);
        }
    }
    let wdce_outcome = runner.run(plugin_root, &wdce, &[], false);
    if wdce_outcome.code != 0 {
        return exit_from_i32(wdce_outcome.code);
    }
    let _ = runner.run(
        plugin_root,
        &[
            "progress".to_owned(),
            "activate".to_owned(),
            "--repo-root".to_owned(),
            repo_root.to_owned(),
            "--run-id".to_owned(),
            active_run_id,
        ],
        &[],
        false,
    );
    let _ = runner.run(
        plugin_root,
        &[
            "timing".to_owned(),
            "mark".to_owned(),
            "design Step 0: session setup".to_owned(),
        ],
        &[("LARCH_TIMING_SKILL".to_owned(), "design".to_owned())],
        false,
    );
    let gate = runner.run(
        plugin_root,
        &[
            "agent".to_owned(),
            "degraded-tools-gate".to_owned(),
            "--skill".to_owned(),
            "design".to_owned(),
            "--codex-present".to_owned(),
            {
                let value = pick("CODEX_PRESENT", "false");
                if value.is_empty() {
                    "false".to_owned()
                } else {
                    value
                }
            },
            "--cursor-present".to_owned(),
            {
                let value = pick("CURSOR_PRESENT", "false");
                if value.is_empty() {
                    "false".to_owned()
                } else {
                    value
                }
            },
            "--codex-binary-found".to_owned(),
            if codex_binary.is_empty() {
                "false".to_owned()
            } else {
                codex_binary
            },
            "--cursor-binary-found".to_owned(),
            if cursor_binary.is_empty() {
                "false".to_owned()
            } else {
                cursor_binary
            },
        ],
        &[],
        false,
    );
    let has_degraded = gate
        .stdout
        .split('\n')
        .any(|line| line.starts_with("DEGRADED="));
    if gate.code != 0 || !has_degraded {
        eprintln!("**⚠ /design: degraded-tools gate failed; aborting Step 0**");
        return exit_from_i32(if gate.code != 0 { gate.code } else { 1 });
    }
    let state = relay_degraded_tools_gate_stdout(&gate.stdout, &design_path);
    println!("STEP0_STATUS={}", state.step0_status);
    println!("DEGRADED={}", state.degraded);
    println!("BOTH_DOWN={}", state.both_down);
    if state.step0_status == "degraded-both-down-hard-fail" {
        println!("DEGRADED_HARD_FAIL=true");
    }
    if state.step0_status == "needs-degraded-decision" {
        println!("DEGRADED_PROMPT_REQUIRED=true");
    }
    ExitCode::SUCCESS
}

#[cfg(test)]
mod tests {
    use std::{cell::RefCell, ffi::OsString, fs, path::Path, process::ExitCode};

    use larch_test_support::{DesignFixture, DesignSession};

    use super::{
        ChildOutcome, Step0Runner, bash_percent_q, decode_bash_percent_q,
        decode_shell_assignment_value, require_plugin_root, settle_next_action,
        step0_abort_cleanup_with, step0_ap_continue, step0_clarify_hard_halt, step0_parse_with,
        step0_route_with, step0_session_with, step0c_with, validate_claude_pid,
    };

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
            // Emulate the Rust-owned `design parse-flags` child: write a valid
            // bash-quoted document to its `--output` path so the persist step
            // re-reads a well-formed default request.
            let is_parse_flags = args.first().map(String::as_str) == Some("design")
                && args.get(1).map(String::as_str) == Some("parse-flags");
            let output = args
                .iter()
                .position(|arg| arg == "--output")
                .and_then(|index| args.get(index + 1));
            if let (true, Some(output)) = (is_parse_flags, output) {
                let mut data = super::Env::new();
                for key in super::PARSED_ENV_KEYS {
                    let _ = data.insert(
                        key.to_owned(),
                        if key.ends_with("_requested") {
                            "false"
                        } else {
                            ""
                        }
                        .to_owned(),
                    );
                }
                let _ = data.insert("POSITIONAL_KIND".to_owned(), "none".to_owned());
                super::write_bash_quoted_env(Path::new(output), &data);
            }
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

    fn source_env(path: &Path, plugin_root: &Path, design_tmpdir: &Path) {
        fs::write(
            path,
            format!(
                "CLAUDE_PLUGIN_ROOT={}\nDESIGN_TMPDIR={}\n",
                super::bash_percent_q(&plugin_root.to_string_lossy()),
                super::bash_percent_q(&design_tmpdir.to_string_lossy()),
            ),
        )
        .expect("write source env");
    }

    #[test]
    fn wrapper_rejects_missing_value_and_unknown_argument() {
        assert_eq!(
            step0_parse_with(
                &arguments(&["--claude-pid"]),
                &RecordingRunner::new(Vec::new())
            ),
            ExitCode::from(2)
        );
        assert_eq!(
            step0_parse_with(&arguments(&["--nope"]), &RecordingRunner::new(Vec::new())),
            ExitCode::from(2)
        );
    }

    #[test]
    fn require_plugin_root_guards_empty_and_template() {
        assert_eq!(require_plugin_root("").unwrap_err(), ExitCode::from(1));
        assert_eq!(
            require_plugin_root("${CLAUDE_PLUGIN_ROOT}").unwrap_err(),
            ExitCode::from(1)
        );
        assert!(require_plugin_root("/opt/plugin").is_ok());
    }

    #[test]
    fn bash_percent_q_round_trips_ascii_and_quotes() {
        // ASCII inputs encode identically in every locale; the Unicode octal
        // form is asserted separately so the test does not depend on the
        // ambient locale bash uses to render high bytes.
        for original in ["it's a test", "plain", "a\tb", "two words", ""] {
            let encoded = bash_percent_q(original);
            assert_eq!(
                decode_shell_assignment_value(&encoded),
                original,
                "round trip {original:?} via {encoded:?}"
            );
        }
    }

    #[test]
    fn decode_handles_octal_escaped_utf8_and_single_quote_splice() {
        // The `$'...'` octal byte escapes bash emits in a UTF-8 locale.
        assert_eq!(decode_bash_percent_q("$'\\360\\237\\230\\200'"), "😀");
        assert_eq!(decode_bash_percent_q("$'caf\\303\\251'"), "café");
        assert_eq!(decode_bash_percent_q("$'\\303\\277'"), "ÿ");
        assert_eq!(decode_bash_percent_q("''"), "");
        assert_eq!(decode_bash_percent_q("'it'\"'\"'s'"), "it's");
    }

    #[test]
    fn validate_claude_pid_matches_regex() {
        assert!(validate_claude_pid("1").is_ok());
        assert!(validate_claude_pid("1234567").is_ok());
        assert!(validate_claude_pid("12345678").is_err());
        assert!(validate_claude_pid("0").is_err());
        assert!(validate_claude_pid("").is_err());
        assert!(validate_claude_pid("12a").is_err());
    }

    #[test]
    fn settle_matrix_covers_dispatch_and_errors() {
        let capture = |args: &[&str]| settle_next_action(&arguments(args));
        assert_eq!(
            capture(&["--site", "gate-b", "--postplan-rc", "0"]),
            ExitCode::SUCCESS
        );
        assert_eq!(
            capture(&["--site", "gate-c", "--postplan-rc", "11"]),
            ExitCode::SUCCESS
        );
        assert_eq!(
            capture(&["--site", "gate-a", "--postplan-rc", "99"]),
            ExitCode::from(2)
        );
        assert_eq!(
            capture(&["--site", "bogus", "--postplan-rc", "0"]),
            ExitCode::from(2)
        );
        assert_eq!(
            capture(&["--site", "gate-b", "--postplan-rc", "xx"]),
            ExitCode::from(2)
        );
        assert_eq!(capture(&["--postplan-rc", "0"]), ExitCode::from(2));
        assert_eq!(capture(&["-h"]), ExitCode::SUCCESS);
    }

    #[test]
    fn route_proceed_folds_init_success_end_to_end() {
        // Contract success-path assertion (#8578 parity plan §5): a `proceed`
        // route must fold `INIT_STATUS=ok` with a non-empty `RUN_PARAMS_PATH=`
        // and return success. The offline parity golden cannot record a live
        // `design route`/`init-runparams` success, so the injected seam proves it
        // here. `finish_step0_route` only returns `SUCCESS` when the folded init
        // reported `INIT_STATUS=ok` and `run-params.json` exists.
        let session = DesignSession::builder(DesignFixture::Absent)
            .build()
            .expect("build design session");
        let design_tmpdir = session.root().join("design-tmpdir");
        fs::create_dir_all(&design_tmpdir).expect("create design tmpdir");
        let plugin_root = session.root().join("plugin");
        fs::create_dir_all(&plugin_root).expect("create plugin root");
        let source = session.root().join("source-env.sh");
        source_env(&source, &plugin_root, &design_tmpdir);
        // The folded-init success guard requires a materialized run-params.json.
        let run_params = design_tmpdir.join("run-params.json");
        fs::write(&run_params, "{}").expect("seed run-params");
        let answers = vec![
            // design route -> proceed
            ok("ROUTE=proceed\n"),
            // design init-runparams -> success rows with a non-empty path
            ok(&format!(
                "INIT_STATUS=ok\nRENAMED=false\nRUN_PARAMS_PATH={}\n",
                run_params.display()
            )),
        ];
        let runner = RecordingRunner::new(answers);
        let code = step0_route_with(
            &arguments(&[
                "--plugin-root",
                plugin_root.to_str().expect("utf8"),
                "--session-env-path",
                source.to_str().expect("utf8"),
                "--claude-pid",
                "4242",
            ]),
            &runner,
        );
        assert_eq!(code, ExitCode::SUCCESS);
        // The route-state wire file records the proceed route before folded init.
        let route_state = fs::read_to_string(design_tmpdir.join(".design-step0-route-state.env"))
            .expect("route state env");
        assert!(
            route_state.contains("ROUTE=proceed"),
            "route state env: {route_state}"
        );
        // The proceed path folds route then init-runparams end to end.
        let calls = runner.calls.borrow();
        assert_eq!(calls.len(), 2);
        assert_eq!(calls[0][1], "route");
        assert_eq!(calls[1][1], "init-runparams");
    }

    #[test]
    fn live_runner_reads_issue_labels_through_github_service() {
        // Regression guard: the live `step0-route` GitHub read must go through
        // the typed `GitHubService::issue_read` (#7672), not an always-`Err`
        // stub. A stubbed loopback issue with the clarify label must surface
        // `has_clarify == "true"` and the bounded title/body.
        use std::sync::Arc;

        use larch_adapters::github::OctocrabGitHubService;
        use larch_test_support::{IssueServiceExchange, IssueServiceStub};

        use crate::github_service::with_test_github_service;

        let body = br#"{"title":"Fix the widget","body":"widget body","labels":[{"name":"needs-design-clarification"}]}"#;
        let stub = IssueServiceStub::start([
            IssueServiceExchange::any_json(200, body.to_vec()).expect("issue json response")
        ])
        .expect("start issue service stub");
        let base_url = stub.base_url().to_owned();
        let factory: Arc<dyn Fn() -> OctocrabGitHubService + Send + Sync> =
            Arc::new(move || OctocrabGitHubService::with_test_base(&base_url));
        let read = with_test_github_service(factory, || {
            super::LiveStep0Runner.read_issue("123", "owner/repo")
        });
        assert_eq!(
            read,
            Ok((
                "Fix the widget".to_owned(),
                "widget body".to_owned(),
                "true".to_owned(),
            ))
        );
    }

    #[test]
    fn ap_continue_writes_completion_sentinels() {
        let session = DesignSession::builder(DesignFixture::Absent)
            .build()
            .expect("build design session");
        let design_tmpdir = session.root().join("design-tmpdir");
        fs::create_dir_all(&design_tmpdir).expect("create design tmpdir");
        let plugin_root = session.root().join("plugin");
        fs::create_dir_all(&plugin_root).expect("create plugin root");
        let source = session.root().join("source-env.sh");
        source_env(&source, &plugin_root, &design_tmpdir);
        let code = step0_ap_continue(&arguments(&[
            "--plugin-root",
            plugin_root.to_str().expect("utf8"),
            "--session-env-path",
            source.to_str().expect("utf8"),
        ]));
        assert_eq!(code, ExitCode::SUCCESS);
        for name in ["step-1c", "step-1d", "step-1d.5"] {
            assert!(design_tmpdir.join(".completed").join(name).is_file());
        }
    }

    #[test]
    fn step0c_writes_sentinel_and_marks_timing() {
        let session = DesignSession::builder(DesignFixture::Absent)
            .build()
            .expect("build design session");
        let design_tmpdir = session.root().join("design-tmpdir");
        fs::create_dir_all(&design_tmpdir).expect("create design tmpdir");
        let plugin_root = session.root().join("plugin");
        fs::create_dir_all(&plugin_root).expect("create plugin root");
        let source = session.root().join("source-env.sh");
        source_env(&source, &plugin_root, &design_tmpdir);
        let runner = RecordingRunner::new(Vec::new());
        let code = step0c_with(
            &arguments(&[
                "--plugin-root",
                plugin_root.to_str().expect("utf8"),
                "--session-env-path",
                source.to_str().expect("utf8"),
            ]),
            &runner,
        );
        assert_eq!(code, ExitCode::SUCCESS);
        assert!(design_tmpdir.join(".completed").join("step-0c").is_file());
        let calls = runner.calls.borrow();
        assert_eq!(calls.len(), 1);
        assert_eq!(calls[0][0], "timing");
        assert_eq!(calls[0][1], "mark");
    }

    #[test]
    fn clarify_hard_halt_contains_detail_and_returns_zero() {
        let session = DesignSession::builder(DesignFixture::Absent)
            .build()
            .expect("build design session");
        let design_tmpdir = session.root().join("design-tmpdir");
        fs::create_dir_all(&design_tmpdir).expect("create design tmpdir");
        let plugin_root = session.root().join("plugin");
        fs::create_dir_all(&plugin_root).expect("create plugin root");
        let source = session.root().join("source-env.sh");
        source_env(&source, &plugin_root, &design_tmpdir);
        // An out-of-tree detail log is reset to the in-tree default.
        let outside = session.root().join("outside.log");
        let code = step0_clarify_hard_halt(&arguments(&[
            "--plugin-root",
            plugin_root.to_str().expect("utf8"),
            "--session-env-path",
            source.to_str().expect("utf8"),
            "--failure-detail-log",
            outside.to_str().expect("utf8"),
        ]));
        assert_eq!(code, ExitCode::SUCCESS);
        let resolved = fs::canonicalize(&design_tmpdir).expect("canonical tmpdir");
        assert!(resolved.join("clarify-loop.failure.log").is_file());
        assert!(!outside.is_file());
    }

    #[test]
    fn abort_cleanup_rejects_bad_pid_with_exit_two() {
        let session = DesignSession::builder(DesignFixture::Absent)
            .build()
            .expect("build design session");
        let design_tmpdir = session.root().join("design-tmpdir");
        fs::create_dir_all(&design_tmpdir).expect("create design tmpdir");
        let plugin_root = session.root().join("plugin");
        fs::create_dir_all(&plugin_root).expect("create plugin root");
        let source = session.root().join("source-env.sh");
        source_env(&source, &plugin_root, &design_tmpdir);
        let runner = RecordingRunner::new(Vec::new());
        let code = step0_abort_cleanup_with(
            &arguments(&[
                "--plugin-root",
                plugin_root.to_str().expect("utf8"),
                "--session-env-path",
                source.to_str().expect("utf8"),
                "--claude-pid",
                "not-a-pid",
            ]),
            &runner,
        );
        assert_eq!(code, ExitCode::from(2));
        // Rejection happens before any child call.
        assert!(runner.calls.borrow().is_empty());
    }

    #[test]
    fn abort_cleanup_deactivates_progress_before_cleanup() {
        let session = DesignSession::builder(DesignFixture::Absent)
            .build()
            .expect("build design session");
        let design_tmpdir = session.root().join("design-tmpdir");
        fs::create_dir_all(&design_tmpdir).expect("create design tmpdir");
        let plugin_root = session.root().join("plugin");
        fs::create_dir_all(&plugin_root).expect("create plugin root");
        let source = session.root().join("source-env.sh");
        source_env(&source, &plugin_root, &design_tmpdir);
        // The persisted run/repo the abort path resolves for deactivation.
        let repo_root = session.root().join("repo");
        fs::create_dir_all(&repo_root).expect("create repo root");
        fs::write(
            design_tmpdir.join("source-env.sh"),
            format!("LARCH_RUN_ID=run-123\nREPO_ROOT={}\n", repo_root.display()),
        )
        .expect("write persisted env");
        let runner = RecordingRunner::new(Vec::new());
        let code = step0_abort_cleanup_with(
            &arguments(&[
                "--plugin-root",
                plugin_root.to_str().expect("utf8"),
                "--session-env-path",
                source.to_str().expect("utf8"),
                "--claude-pid",
                "4242",
            ]),
            &runner,
        );
        assert_eq!(code, ExitCode::SUCCESS);
        let calls = runner.calls.borrow();
        let find = |verb: &str, sub: &str| {
            calls.iter().position(|call| {
                call.first().map(String::as_str) == Some(verb)
                    && call.get(1).map(String::as_str) == Some(sub)
            })
        };
        let deactivate = find("progress", "deactivate").expect("progress deactivate call");
        let cleanup = find("session", "cleanup-tmpdir").expect("cleanup-tmpdir call");
        assert!(deactivate < cleanup, "deactivation must precede cleanup");
        let canonical = repo_root.canonicalize().expect("canonical repo root");
        assert!(calls[deactivate].contains(&"run-123".to_owned()));
        assert!(
            calls[deactivate]
                .iter()
                .any(|arg| arg == &canonical.display().to_string()),
            "deactivate call must carry the resolved repo root: {:?}",
            calls[deactivate]
        );
    }

    #[test]
    fn session_storage_preflight_failure_aborts() {
        let session = DesignSession::builder(DesignFixture::Absent)
            .build()
            .expect("build design session");
        let plugin_root = session.root().join("plugin");
        fs::create_dir_all(&plugin_root).expect("create plugin root");
        let runner = RecordingRunner::new(vec![ChildOutcome {
            code: 3,
            stdout: String::new(),
            stderr: "boom\n".to_owned(),
        }]);
        let code = step0_session_with(
            &arguments(&["--plugin-root", plugin_root.to_str().expect("utf8")]),
            &runner,
        );
        assert_eq!(code, ExitCode::from(3));
        let calls = runner.calls.borrow();
        assert_eq!(calls[0][0], "run-log");
        assert_eq!(calls[0][1], "storage-preflight");
    }

    #[test]
    fn session_happy_path_runs_expected_child_sequence() {
        let session = DesignSession::builder(DesignFixture::Absent)
            .build()
            .expect("build design session");
        let plugin_root = session.root().join("plugin");
        fs::create_dir_all(&plugin_root).expect("create plugin root");
        let design_tmpdir = session.root().join("session-tmpdir");
        fs::create_dir_all(&design_tmpdir).expect("create session tmpdir");
        let claude_pid = "4242";
        let answers = vec![
            // run-log storage-preflight
            ok("PREFLIGHT_OK=true\nRUN_LOG_STORAGE=disabled\nSTORAGE_PREFLIGHT=skipped-disabled\n"),
            // design parse-flags (RecordingRunner writes its --output document)
            ok(""),
            // progress install-statusline
            ok(""),
            // progress clear
            ok(""),
            // session setup
            ok(&format!(
                "SESSION_TMPDIR={}\nSESSION_ID=sid\nCODEX_BINARY_FOUND=true\nCURSOR_BINARY_FOUND=false\n",
                design_tmpdir.display()
            )),
            // token mark
            ok(""),
            // run-log lifecycle-start
            ok("LIFECYCLE_STARTED=true\n"),
            // agent check-reviewers
            ok("CODEX_PRESENT=true\nCURSOR_PRESENT=false\n"),
            // session write-design-env
            ok(""),
            // progress activate
            ok(""),
            // timing mark
            ok(""),
            // agent degraded-tools-gate
            ok("DEGRADED=false\nBOTH_DOWN=false\n"),
        ];
        let runner = RecordingRunner::new(answers);
        let code = step0_session_with(
            &arguments(&[
                "--plugin-root",
                plugin_root.to_str().expect("utf8"),
                "--claude-pid",
                claude_pid,
            ]),
            &runner,
        );
        assert_eq!(code, ExitCode::SUCCESS);
        let calls = runner.calls.borrow();
        let sequence: Vec<(String, String)> = calls
            .iter()
            .map(|call| {
                (
                    call.first().cloned().unwrap_or_default(),
                    call.get(1).cloned().unwrap_or_default(),
                )
            })
            .collect();
        assert_eq!(
            sequence,
            vec![
                ("run-log".to_owned(), "storage-preflight".to_owned()),
                ("design".to_owned(), "parse-flags".to_owned()),
                ("progress".to_owned(), "install-statusline".to_owned()),
                ("progress".to_owned(), "clear".to_owned()),
                ("session".to_owned(), "setup".to_owned()),
                ("token".to_owned(), "mark".to_owned()),
                ("run-log".to_owned(), "lifecycle-start".to_owned()),
                ("agent".to_owned(), "check-reviewers".to_owned()),
                ("session".to_owned(), "write-design-env".to_owned()),
                ("progress".to_owned(), "activate".to_owned()),
                ("timing".to_owned(), "mark".to_owned()),
                ("agent".to_owned(), "degraded-tools-gate".to_owned()),
            ]
        );
    }
}
