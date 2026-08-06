//! Codex and cursor review-result adapter helpers.
//!
//! Adapter parity for the `agent launch-review` command cutover in issue #8115.
//! Auth, specialist render, research validation, and dirty-tree baseline I/O
//! arrive through injected ports; this module owns the review-side contracts.

use super::VendorLaunchRequest;
use crate::{
    DuplicatePolicy, KvDocument, LauncherArtifactKind, LauncherArtifactPaths, ParseOptions,
    VENDOR_FAILURE_DIAG_SECTION_LINES, json_usage_number, redaction::redact,
    stream_reset_history_entry,
};
use regex::Regex;
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::{
    collections::BTreeMap,
    fmt::Write as _,
    path::{Path, PathBuf},
    sync::LazyLock,
};

/// Collector strong-header prefix that may precede a compact Codex prompt sentinel.
pub const COLLECTOR_NS_STRONG_HEADER: &str = concat!(
    "IMPORTANT: Your previous response was not structured correctly. ",
    "You MUST output findings in the exact format your original prompt requires, ",
    "or the literal NO_ISSUES_FOUND if no issues exist. ",
    "Do NOT write narrative, process descriptions, or reading logs. ",
    "Begin your response directly with the format your prompt demands.\n\n",
);

/// Shared exit-code / empty-result transient retry budget for review launches.
pub const REVIEW_MAX_TRANSIENT_RETRIES: u32 = 4;

/// Cursor preread failure exit code (Darwin keychain read returned no token).
pub const CURSOR_PREREAD_FAIL_RC: i32 = 2;

/// Cursor preread failure message written to stderr and failure carriers.
pub const CURSOR_PREREAD_FAIL_MSG: &str = concat!(
    "cursor-preread-service-token: cursor-access-token keychain -w read returned no token; ",
    "CURSOR_API_KEY left unset (Cursor may fail auth in-process and return a degraded response).",
);

/// Input-work floor at/below which a bare no-issues sentinel is canned (#5518).
pub const CURSOR_NO_WORK_INPUT_TOKEN_FLOOR: i64 = 64;

/// Output-token floor that triggers research-output validation for short results.
pub const CURSOR_DEGRADED_OUTPUT_TOKEN_FLOOR: i64 = 1000;

/// Result-byte ceiling paired with [`CURSOR_DEGRADED_OUTPUT_TOKEN_FLOOR`].
pub const CURSOR_DEGRADED_RESULT_BYTES_CEILING: usize = 500;

/// Normalized cursor no-issues carrier.
pub const CURSOR_NO_ISSUES_JSON: &str = "{\"no_issues_found\": true}\n";

/// Cursor result written when the slot returned a canned or invalid response.
pub const CURSOR_DEGRADED_RESPONSE: &str = "CURSOR_DEGRADED_RESPONSE\n";

/// Cursor result written when `.result` stayed empty after retries.
pub const CURSOR_EMPTY_RESPONSE: &str = "CURSOR_EMPTY_RESPONSE\n";

/// Env key for the review-step default token budget cap.
pub const ENV_TOKEN_BUDGET_CAP_REVIEW: &str = "LARCH_TOKEN_BUDGET_CAP_REVIEW";

/// Env key for a fixed transient-retry delay in seconds.
pub const ENV_TRANSIENT_RETRY_DELAY: &str = "LARCH_TRANSIENT_RETRY_DELAY";

/// Env key for cursor launch jitter (milliseconds, inclusive max).
pub const ENV_CURSOR_LAUNCH_JITTER_MS: &str = "LARCH_CURSOR_LAUNCH_JITTER_MS";

/// Env key that disables empty-result retries when set to `0`.
pub const ENV_CURSOR_RETRY_EMPTY_RESULT: &str = "LARCH_CURSOR_RETRY_EMPTY_RESULT";

/// Default cursor launch jitter max when the env key is unset.
pub const DEFAULT_CURSOR_LAUNCH_JITTER_MS: u64 = 250;

/// Auth-setup outcome supplied by the caller-owned auth port.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ReviewAuthVerdict {
    /// Whether authentication setup succeeded.
    pub ok: bool,
    /// Exit code to publish on refusal.
    pub rc: i32,
    /// Human-readable failure message (empty on success).
    pub message: String,
}

impl ReviewAuthVerdict {
    /// Build a successful verdict.
    #[must_use]
    pub const fn ok() -> Self {
        Self {
            ok: true,
            rc: 0,
            message: String::new(),
        }
    }

    /// Build a refused verdict.
    #[must_use]
    pub fn refuse(rc: i32, message: impl Into<String>) -> Self {
        Self {
            ok: false,
            rc,
            message: message.into(),
        }
    }
}

/// Injected Codex home / auth preparation for review preflight.
pub trait CodexReviewAuthPort {
    /// Prepare a confined Codex home and return the auth verdict.
    fn prepare_home(&self, home: &Path, trusted_instructions: &Path) -> ReviewAuthVerdict;
}

/// Injected Cursor auth and keychain preread for review preflight.
pub trait CursorReviewAuthPort {
    /// Run Cursor authentication preflight.
    fn auth_preflight(&self) -> ReviewAuthVerdict;
    /// Preread the Darwin service token into the process environment.
    fn preread_service_token(&self) -> bool;
}

/// Injected specialist prompt reconstruction used by compact Codex sentinels.
pub trait SpecialistRenderPort {
    /// Render a specialist prompt from sentinel KEY=value fields.
    ///
    /// Returns `(exit_code, stdout)`. Non-zero exit code is failure.
    fn render_specialist(&self, sentinel: &BTreeMap<String, String>) -> (i32, String);
}

/// Injected research-output validator used by degraded Cursor result detection.
pub trait ResearchOutputValidator {
    /// Return true when the candidate research text is well-formed.
    fn validate(&self, result_text: &str) -> bool;
}

/// Injected dirty-tree baseline comparison writer.
pub trait DirtyTreeBaselinePort {
    /// Compare the live tree to `baseline` and write the sidecar when possible.
    ///
    /// Returns fallback lines used only when the sidecar file is still missing.
    fn write_from_baseline(&self, baseline: &Path, sidecar: &Path, cwd: &Path) -> Vec<String>;
}

/// Inputs that decide whether a Codex review prompt sidecar is compact.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct CodexPromptSidecarArgs<'a> {
    /// Specialist agent file path; empty disables the compact form.
    pub agent_file: &'a str,
    /// Description text; non-empty disables the compact form.
    pub description_text: &'a str,
    /// Review mode label.
    pub mode: &'a str,
    /// Optional scope-files path list.
    pub scope_files: &'a str,
    /// Whether competition notice was requested.
    pub competition_notice: bool,
    /// Optional competition-notice file path.
    pub competition_notice_file: &'a str,
    /// Optional diff file path.
    pub diff_file: &'a str,
    /// Optional commit-count string (digits only are recorded).
    pub commit_count: &'a str,
    /// Optional plan file path.
    pub plan_file: &'a str,
    /// Optional feature file path.
    pub feature_file: &'a str,
    /// Optional session-env path.
    pub session_env_path: &'a str,
    /// Optional findings-ledger file path.
    pub findings_ledger_file: &'a str,
    /// Optional difficulty label.
    pub difficulty: &'a str,
}

/// Outcome of reading a Codex prompt file that may carry a compact sentinel.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum CodexPromptSentinelRead {
    /// The file is not a compact sentinel; callers should read the raw prompt.
    NotSentinel,
    /// Sentinel reconstructed successfully.
    Ok {
        /// Reconstructed prompt, including any collector strong-header prefix.
        prompt: String,
    },
    /// Sentinel was present but malformed, hash-mismatched, or render failed.
    Failed {
        /// Failure message for stderr.
        message: String,
    },
}

/// Compact Cursor preflight refusal before artifact materialization.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct CursorPreflightFailure {
    /// Launcher exit code to publish.
    pub rc: i32,
    /// Failure reason recorded in diag / sidecar.
    pub failure_reason: &'static str,
}

impl CursorPreflightFailure {
    /// Expand into the full preflight artifact bundle for `output`.
    #[must_use]
    pub fn into_refusal(self, timeout: &str, output: &Path) -> ReviewPreflightRefusal {
        render_preflight_bundle(
            "cursor",
            timeout,
            output,
            self.failure_reason,
            true,
            self.rc,
        )
    }
}

/// Planned Cursor review preflight refusal artifacts.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ReviewPreflightRefusal {
    /// Launcher exit code to publish.
    pub rc: i32,
    /// Failure reason recorded in diag / sidecar.
    pub failure_reason: String,
    /// Dirty-tree sidecar body.
    pub dirty_tree: String,
    /// Empty output body.
    pub output: String,
    /// Diag body.
    pub diag: String,
    /// Sidecar body.
    pub sidecar: String,
    /// Meta body (without outer-launcher append).
    pub meta: String,
    /// Done-sentinel body.
    pub done: String,
}

/// Cursor result persistence decision after normalization and token checks.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum CursorResultWrite {
    /// Persist the (possibly normalized) result text.
    Keep(String),
    /// Persist the degraded sentinel, optionally with a diag body.
    Degraded {
        /// Optional redacted diag text.
        diag: Option<String>,
    },
}

/// Planned stream reset for one retry attempt artifact.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct StreamResetPlan {
    /// Redacted history entry to append, when the stream carried content.
    pub history_append: Option<String>,
    /// Whether the caller should unlink the live stream path.
    pub unlink: bool,
}

/// Planned retry-artifact reset covering sidecar, diag, and (for Codex) events.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RetryArtifactResetPlan {
    /// Ordered history entries to append before unlinks.
    pub history_entries: Vec<String>,
    /// Live stream kinds to unlink after history append.
    pub unlink_kinds: Vec<LauncherArtifactKind>,
}

/// Cap-hit artifact bodies written when the review token budget is exceeded.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct CapHitArtifacts {
    /// Warning line for stderr.
    pub warning: String,
    /// Primary output body (`STATUS=cap_hit`).
    pub output: String,
    /// Cap-hit sidecar body.
    pub cap_hit: String,
    /// Optional implement-tmpdir step-budget carrier.
    pub step_budget_env: Option<String>,
    /// Done sentinel body (`0`).
    pub done: String,
}

/// Paths cleared and the baseline path created by cursor dirty-tree capture.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct DirtyBaselineCapturePlan {
    /// Stale artifact paths to unlink before snapshotting.
    pub unlink: Vec<PathBuf>,
    /// Baseline path the snapshot writer should populate.
    pub baseline: PathBuf,
}

static SCHEMA_VERSION_LINE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"(?m)^\s*schema_version").expect("schema_version regex"));
static EMBEDDED_NO_ISSUES: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r#"\{[^{}]*"no_issues_found"[^{}]*\}"#).expect("embedded no_issues regex")
});

/// Return the byte offset of a compact Codex prompt sentinel, if present.
#[must_use]
pub fn codex_compact_sentinel_offset(text: &str) -> Option<usize> {
    if text.starts_with("LARCH_PROMPT_SENTINEL=1\n") {
        return Some(0);
    }
    let header = COLLECTOR_NS_STRONG_HEADER;
    if text.starts_with(header) && text[header.len()..].starts_with("LARCH_PROMPT_SENTINEL=1\n") {
        return Some(header.len());
    }
    None
}

/// Render the Codex review prompt sidecar (compact sentinel or full prompt).
#[must_use]
pub fn render_codex_prompt_sidecar(prompt: &str, args: &CodexPromptSidecarArgs<'_>) -> String {
    if args.agent_file.is_empty() || !args.description_text.is_empty() {
        return prompt.to_owned();
    }
    let digest = sha256_hex(prompt.as_bytes());
    let mut lines = vec![
        "LARCH_PROMPT_SENTINEL=1".to_owned(),
        "KIND=specialist".to_owned(),
        format!("HASH={digest}"),
        format!("AGENT_FILE={}", args.agent_file),
        format!("MODE={}", args.mode),
    ];
    if !args.scope_files.is_empty() {
        lines.push(format!("SCOPE_FILES={}", args.scope_files));
    }
    if args.competition_notice {
        lines.push("COMPETITION_NOTICE=true".to_owned());
    }
    if !args.competition_notice_file.is_empty() && !args.competition_notice_file.contains('\n') {
        lines.push(format!(
            "COMPETITION_NOTICE_FILE={}",
            args.competition_notice_file
        ));
    }
    if !args.diff_file.is_empty() {
        lines.push(format!("DIFF_FILE={}", args.diff_file));
    }
    if !args.commit_count.is_empty() && args.commit_count.bytes().all(|b| b.is_ascii_digit()) {
        lines.push(format!("COMMIT_COUNT={}", args.commit_count));
    }
    if !args.plan_file.is_empty() && !args.plan_file.contains('\n') {
        lines.push(format!("PLAN_FILE={}", args.plan_file));
    }
    if !args.feature_file.is_empty() && !args.feature_file.contains('\n') {
        lines.push(format!("FEATURE_FILE={}", args.feature_file));
    }
    if !args.findings_ledger_file.is_empty() && !args.findings_ledger_file.contains('\n') {
        lines.push(format!(
            "FINDINGS_LEDGER_FILE={}",
            args.findings_ledger_file
        ));
    }
    if !args.session_env_path.is_empty() && !args.session_env_path.contains('\n') {
        lines.push(format!("SESSION_ENV_PATH={}", args.session_env_path));
    }
    if !args.difficulty.is_empty()
        && !args.difficulty.contains('\n')
        && !args.difficulty.contains('\r')
    {
        lines.push(format!("DIFFICULTY={}", args.difficulty));
    }
    format!("{}\n", lines.join("\n"))
}

/// Reconstruct a compact Codex prompt sentinel through the render port.
#[must_use]
pub fn read_codex_prompt_sentinel(
    text: &str,
    render: &impl SpecialistRenderPort,
) -> CodexPromptSentinelRead {
    let Some(sentinel_idx) = codex_compact_sentinel_offset(text) else {
        return CodexPromptSentinelRead::NotSentinel;
    };
    let prefix = &text[..sentinel_idx];
    let lines: Vec<&str> = text[sentinel_idx..].lines().collect();
    if lines.first().copied() != Some("LARCH_PROMPT_SENTINEL=1") {
        return CodexPromptSentinelRead::NotSentinel;
    }
    let values = parse_sentinel_kv(&lines[1..].join("\n"));
    if values.get("KIND").map(String::as_str) != Some("specialist")
        || values.get("AGENT_FILE").is_none_or(String::is_empty)
        || values.get("MODE").is_none_or(String::is_empty)
        || values.get("HASH").is_none_or(String::is_empty)
    {
        return CodexPromptSentinelRead::Failed {
            message: "agent launch-review: malformed prompt sentinel (missing or empty KIND/AGENT_FILE/MODE/HASH)"
                .to_owned(),
        };
    }
    let (rc, prompt) = render.render_specialist(&values);
    if rc != 0 {
        return CodexPromptSentinelRead::Failed {
            message: if prompt.is_empty() {
                "agent launch-review: render specialist failed".to_owned()
            } else {
                prompt
            },
        };
    }
    let digest = sha256_hex(prompt.as_bytes());
    let expected = values.get("HASH").map_or("", String::as_str);
    if digest != expected {
        return CodexPromptSentinelRead::Failed {
            message: format!(
                "agent launch-review: prompt reconstruction hash mismatch (sentinel={expected} reconstructed={digest})"
            ),
        };
    }
    let prompt = if prefix.is_empty() {
        prompt
    } else {
        format!("{prefix}{prompt}")
    };
    CodexPromptSentinelRead::Ok { prompt }
}

/// Apply resolved Codex model argv tokens onto a launch request.
#[must_use]
pub fn resolve_codex_review_model(
    mut request: VendorLaunchRequest,
    model_args: Vec<String>,
) -> VendorLaunchRequest {
    request.model_args = model_args;
    request
}

/// Run Codex review auth preflight through the injected port.
///
/// # Errors
///
/// Returns the auth port verdict when preparation refuses the launch.
pub fn run_codex_review_preflight(
    auth: &impl CodexReviewAuthPort,
    home: &Path,
    trusted_instructions: &Path,
) -> Result<(), ReviewAuthVerdict> {
    let verdict = auth.prepare_home(home, trusted_instructions);
    if verdict.ok { Ok(()) } else { Err(verdict) }
}

/// Run Cursor review auth preflight through the injected port.
///
/// # Errors
///
/// Returns a compact failure when auth or token preread refuses the launch.
pub fn run_cursor_review_preflight(
    auth: &impl CursorReviewAuthPort,
) -> Result<(), CursorPreflightFailure> {
    let verdict = auth.auth_preflight();
    if !verdict.ok {
        return Err(CursorPreflightFailure {
            rc: verdict.rc,
            failure_reason: "cursor-auth-preflight: CURSOR_API_KEY unset/empty and cursor-user keychain entry missing on Darwin; see docs/installation-and-setup.md (Cursor section)",
        });
    }
    if !auth.preread_service_token() {
        return Err(CursorPreflightFailure {
            rc: CURSOR_PREREAD_FAIL_RC,
            failure_reason: "cursor-preread-service-token: keychain -w read returned no token on Darwin; see docs/installation-and-setup.md (Cursor section)",
        });
    }
    Ok(())
}

/// Render a Codex/cursor review preflight refusal artifact bundle.
#[must_use]
pub fn render_preflight_bundle(
    tool: &str,
    timeout: &str,
    output: &Path,
    failure_reason: &str,
    capture_stdout_only: bool,
    launcher_exit: i32,
) -> ReviewPreflightRefusal {
    let dirty_tree = if tool == "codex" {
        render_clean_readonly_dirty_tree()
    } else {
        render_unknown_dirty_tree(false, "preflight-short-circuit-no-agent-ran")
    };
    ReviewPreflightRefusal {
        rc: launcher_exit,
        failure_reason: failure_reason.to_owned(),
        dirty_tree,
        output: String::new(),
        diag: format!("STATUS=FAILED\nFAILURE_REASON={failure_reason}\n"),
        sidecar: format!("{failure_reason}\n"),
        meta: format!(
            "TOOL={tool}\nTIMEOUT={timeout}\nCAPTURE_STDOUT=false\nCAPTURE_STDOUT_ONLY={}\nOUTPUT_FILE={}\nCMD_JSON=[]\n",
            if capture_stdout_only { "true" } else { "false" },
            output.display()
        ),
        done: format!("{launcher_exit}\n"),
    }
}

/// Compute cursor launch jitter milliseconds from configured max and a roll.
#[must_use]
pub fn cursor_launch_jitter_ms(configured_max: Option<&str>, under_test: bool, roll: u64) -> u64 {
    if under_test {
        return 0;
    }
    let max_ms = configured_max
        .filter(|raw| !raw.is_empty() && raw.bytes().all(|b| b.is_ascii_digit()))
        .and_then(|raw| raw.parse::<u64>().ok())
        .unwrap_or(DEFAULT_CURSOR_LAUNCH_JITTER_MS);
    if max_ms == 0 {
        return 0;
    }
    roll % (max_ms + 1)
}

/// Plan the unlink set and baseline path for cursor dirty-tree capture.
#[must_use]
pub fn plan_capture_cursor_dirty_baseline(
    paths: &LauncherArtifactPaths,
) -> DirtyBaselineCapturePlan {
    DirtyBaselineCapturePlan {
        unlink: vec![
            paths.path(LauncherArtifactKind::UntrackedBaseline),
            paths.path(LauncherArtifactKind::DirtyTree),
            paths.path(LauncherArtifactKind::DirtyTreeTrackedPaths),
            paths.path(LauncherArtifactKind::DirtyTreeNewUntrackedPaths),
        ],
        baseline: paths.path(LauncherArtifactKind::UntrackedBaseline),
    }
}

/// Render the Codex read-only clean dirty-tree sidecar.
#[must_use]
pub fn render_clean_readonly_dirty_tree() -> String {
    "STATUS=clean\nMODE=baseline\nREASON=codex-sandbox-read-only\n".to_owned()
}

/// Render an unknown dirty-tree sidecar for a short-circuited launch.
#[must_use]
pub fn render_unknown_dirty_tree(baseline_present: bool, reason: &str) -> String {
    let state = if baseline_present {
        "present"
    } else {
        "missing"
    };
    format!("STATUS=unknown\nMODE=baseline\nUNTRACKED_BASELINE={state}\nREASON={reason}\n")
}

/// Write the cursor dirty-tree sidecar through the baseline port, with fallback.
pub fn write_cursor_dirty_tree_from_baseline(
    port: &impl DirtyTreeBaselinePort,
    baseline: &Path,
    sidecar: &Path,
    cwd: &Path,
    sidecar_exists_after: impl FnOnce() -> bool,
) -> Option<String> {
    let lines = port.write_from_baseline(baseline, sidecar, cwd);
    if sidecar_exists_after() {
        None
    } else {
        Some(format!("{}\n", lines.join("\n")))
    }
}

/// True when a stripped line is a JSON object with `no_issues_found: true`.
#[must_use]
pub fn cursor_line_no_issues(line: &str) -> bool {
    let stripped = line.trim();
    if !stripped.starts_with('{') {
        return false;
    }
    let Ok(obj) = serde_json::from_str::<Value>(stripped) else {
        return false;
    };
    obj.as_object()
        .is_some_and(|map| map.get("no_issues_found") == Some(&Value::Bool(true)))
}

/// True when any JSON line carries a `schema_version` key.
#[must_use]
pub fn cursor_has_structured_findings(text: &str) -> bool {
    for line in text.lines() {
        let stripped = line.trim();
        if !stripped.starts_with('{') {
            continue;
        }
        let Ok(obj) = serde_json::from_str::<Value>(stripped) else {
            continue;
        };
        if obj
            .as_object()
            .is_some_and(|map| map.contains_key("schema_version"))
        {
            return true;
        }
    }
    false
}

/// Collapse eligible cursor prose/sentinel mixtures to the bare no-issues JSON.
#[must_use]
pub fn cursor_normalize_no_issues(text: &str) -> String {
    if text.trim().is_empty() {
        return text.to_owned();
    }
    if cursor_has_structured_findings(text) {
        return text.to_owned();
    }
    let first = text
        .lines()
        .map(str::trim)
        .find(|line| !line.is_empty())
        .unwrap_or("");
    if SCHEMA_VERSION_LINE.is_match(text) {
        return text.to_owned();
    }
    if !first.is_empty()
        && !first.starts_with('{')
        && let Some(matched) = EMBEDDED_NO_ISSUES.find(first)
        && let Ok(obj) = serde_json::from_str::<Value>(matched.as_str())
        && obj
            .as_object()
            .is_some_and(|map| map.get("no_issues_found") == Some(&Value::Bool(true)))
    {
        return CURSOR_NO_ISSUES_JSON.to_owned();
    }
    let sentinel_count = text
        .lines()
        .filter(|line| {
            let stripped = line.trim();
            stripped == "NO_ISSUES_FOUND" || cursor_line_no_issues(stripped)
        })
        .count();
    if sentinel_count == 1 {
        return CURSOR_NO_ISSUES_JSON.to_owned();
    }
    text.to_owned()
}

/// True when normalized cursor text is exactly one no-issues sentinel line.
#[must_use]
pub fn cursor_result_is_no_issues(text: &str) -> bool {
    if cursor_has_structured_findings(text) {
        return false;
    }
    let non_empty: Vec<&str> = text
        .lines()
        .map(str::trim)
        .filter(|line| !line.is_empty())
        .collect();
    if non_empty.len() != 1 {
        return false;
    }
    non_empty[0] == "NO_ISSUES_FOUND" || cursor_line_no_issues(non_empty[0])
}

/// Sum `inputTokens + cacheReadTokens` from a Cursor envelope; missing → 0.
#[must_use]
pub fn cursor_input_work_tokens(obj: &Value) -> i64 {
    let Some(usage) = obj.get("usage").and_then(Value::as_object) else {
        return 0;
    };
    let mut total = 0_i64;
    for key in ["inputTokens", "cacheReadTokens"] {
        if let Ok(n) = json_usage_number(usage.get(key)) {
            total += n;
        }
    }
    total
}

/// Read `outputTokens` from a Cursor envelope; missing/non-numeric → 0.
#[must_use]
pub fn cursor_output_tokens(obj: &Value) -> i64 {
    let Some(usage) = obj.get("usage").and_then(Value::as_object) else {
        return 0;
    };
    json_usage_number(usage.get("outputTokens")).unwrap_or(0)
}

/// Render a redacted Cursor degraded-response diagnostic.
#[must_use]
pub fn render_cursor_degraded_diag(obj: &Value, reason: &str) -> String {
    let mut reason = reason.to_owned();
    if let Some(usage) = obj.get("usage").and_then(Value::as_object) {
        for key in ["inputTokens", "cacheReadTokens", "outputTokens"] {
            if let Some(value) = usage.get(key) {
                let _ = write!(reason, " usage.{key}={}", json_diag_value(value));
            }
        }
    }
    let raw = format!("TOOL=cursor\nFAILURE_REASON={reason}\n");
    redact(&raw).text().to_owned()
}

/// Render the canned no-work no-issues diagnostic (#5518).
#[must_use]
pub fn render_cursor_no_work_diag(obj: &Value) -> String {
    render_cursor_degraded_diag(
        obj,
        &format!(
            "cursor-no-work-no-issues: exit 0, bare no_issues_found sentinel with input work \
             <= {CURSOR_NO_WORK_INPUT_TOKEN_FLOOR} tokens (slot did not ingest the review; \
             likely in-process auth/backend failure)"
        ),
    )
}

/// Decide what to persist for a Cursor review result after normalization.
#[must_use]
pub fn plan_cursor_result_write(
    result: &str,
    obj: &Value,
    validator: Option<&dyn ResearchOutputValidator>,
) -> CursorResultWrite {
    let result_bytes = result.len();
    if cursor_result_is_no_issues(result)
        && cursor_input_work_tokens(obj) <= CURSOR_NO_WORK_INPUT_TOKEN_FLOOR
    {
        return CursorResultWrite::Degraded {
            diag: Some(render_cursor_no_work_diag(obj)),
        };
    }
    if cursor_output_tokens(obj) > CURSOR_DEGRADED_OUTPUT_TOKEN_FLOOR
        && result_bytes < CURSOR_DEGRADED_RESULT_BYTES_CEILING
    {
        let ok = validator.is_none_or(|port| port.validate(result));
        return if ok {
            CursorResultWrite::Keep(result.to_owned())
        } else {
            CursorResultWrite::Degraded { diag: None }
        };
    }
    CursorResultWrite::Keep(result.to_owned())
}

/// Render the empty-result Cursor output and redacted diagnostic.
#[must_use]
pub fn render_cursor_empty_response(obj: &Value, transient_attempt: u32) -> (String, String) {
    let retries = transient_attempt.saturating_sub(1);
    let mut reason = format!(
        "cursor-empty-result: exit 0, .result empty/null after {retries} transient retries (shared exit-code and empty-result budget)"
    );
    for key in [
        "type",
        "subtype",
        "is_error",
        "duration",
        "request_id",
        "requestId",
    ] {
        if let Some(value) = obj.get(key) {
            let rendered = json_diag_value(value).replace('\n', " ");
            let clipped: String = rendered.chars().take(200).collect();
            let _ = write!(reason, " {key}={clipped}");
        }
    }
    if let Some(usage) = obj.get("usage").and_then(Value::as_object) {
        for key in ["inputTokens", "outputTokens"] {
            if let Some(value) = usage.get(key) {
                let _ = write!(reason, " usage.{key}={}", json_diag_value(value));
            }
        }
    }
    let diag = redact(&format!("TOOL=cursor\nFAILURE_REASON={reason}\n"))
        .text()
        .to_owned();
    (CURSOR_EMPTY_RESPONSE.to_owned(), diag)
}

/// Compute the transient-retry sleep delay in seconds.
#[must_use]
pub fn review_retry_delay_secs(
    attempt: u32,
    configured: Option<&str>,
    under_test: bool,
    jitter_bit: u64,
) -> u64 {
    if let Some(raw) = configured.filter(|raw| raw.bytes().all(|b| b.is_ascii_digit())) {
        let delay = raw.parse::<u64>().unwrap_or(0);
        return if delay > 0 { delay } else { 0 };
    }
    let base = 1_u64.checked_shl(attempt).unwrap_or(u64::MAX).max(10);
    let delay = base.saturating_add(jitter_bit.min(1));
    if under_test { 0 } else { delay }
}

/// Plan one stream reset: archive content into history, then unlink.
#[must_use]
pub fn plan_stream_reset(label: &str, existing: Option<&str>) -> StreamResetPlan {
    let history_append = existing.filter(|text| !text.is_empty()).and_then(|text| {
        stream_reset_history_entry(label, text, VENDOR_FAILURE_DIAG_SECTION_LINES)
    });
    StreamResetPlan {
        history_append,
        unlink: true,
    }
}

/// Plan retry-artifact reset so a prior attempt leaves no stale live stream.
#[must_use]
pub fn plan_retry_artifact_reset(
    tool: &str,
    label: &str,
    sidecar: Option<&str>,
    diag: Option<&str>,
    events: Option<&str>,
) -> RetryArtifactResetPlan {
    let mut history_entries = Vec::new();
    let mut unlink_kinds = vec![LauncherArtifactKind::Sidecar, LauncherArtifactKind::Diag];
    if let Some(entry) = plan_stream_reset(label, sidecar).history_append {
        history_entries.push(entry);
    }
    if let Some(entry) = plan_stream_reset(&format!("{label} diag"), diag).history_append {
        history_entries.push(entry);
    }
    if tool == "codex" {
        unlink_kinds.push(LauncherArtifactKind::Events);
        if let Some(entry) =
            plan_stream_reset(&format!("{label} events.jsonl"), events).history_append
        {
            history_entries.push(entry);
        }
    }
    RetryArtifactResetPlan {
        history_entries,
        unlink_kinds,
    }
}

/// True when a Cursor output file is a successful empty-result retry candidate.
#[must_use]
pub fn is_cursor_empty_result(raw: &str, retry_empty_enabled: bool) -> bool {
    if !retry_empty_enabled || raw.is_empty() {
        return false;
    }
    let Ok(obj) = serde_json::from_str::<Value>(raw) else {
        return false;
    };
    let Some(map) = obj.as_object() else {
        return false;
    };
    match map.get("result") {
        None | Some(Value::Null) => true,
        Some(Value::String(text)) => text.is_empty(),
        Some(_) => false,
    }
}

/// Resolve the effective review token-budget cap from CLI then env.
#[must_use]
pub fn effective_review_token_cap(cli_cap: Option<&str>, env_cap: Option<&str>) -> Option<u64> {
    if let Some(raw) = cli_cap.filter(|raw| is_positive_int(raw)) {
        return raw.parse().ok();
    }
    env_cap
        .filter(|raw| is_positive_int(raw))
        .and_then(|raw| raw.parse().ok())
}

/// Render cap-hit artifact bodies for a review launch short-circuit.
#[must_use]
pub fn render_cap_hit_artifacts(
    cap: u64,
    check_stdout: &str,
    implement_tmpdir: Option<&Path>,
) -> CapHitArtifacts {
    let total = parse_total_token(check_stdout).unwrap_or_default();
    let warning = format!(
        "⚠ agent launch-review: step token budget cap of {cap} tokens exceeded ({total} combined vendor tokens); external reviewer fan-out skipped"
    );
    let body = format!("STATUS=cap_hit\n{}", check_stdout.trim_end());
    let step_budget_env = implement_tmpdir.map(|_| format!("{body}\n"));
    CapHitArtifacts {
        warning,
        output: "STATUS=cap_hit\n".to_owned(),
        cap_hit: format!("{body}\n"),
        step_budget_env,
        done: "0\n".to_owned(),
    }
}

fn parse_sentinel_kv(text: &str) -> BTreeMap<String, String> {
    KvDocument::parse(text, ParseOptions::legacy())
        .map(|document| document.select(DuplicatePolicy::Last))
        .unwrap_or_default()
}

fn sha256_hex(bytes: &[u8]) -> String {
    let digest = Sha256::digest(bytes);
    let mut hex = String::with_capacity(digest.len() * 2);
    for byte in digest {
        let _ = write!(&mut hex, "{byte:02x}");
    }
    hex
}

fn json_diag_value(value: &Value) -> String {
    match value {
        Value::Null => "None".to_owned(),
        Value::Bool(true) => "True".to_owned(),
        Value::Bool(false) => "False".to_owned(),
        Value::Number(number) => number.to_string(),
        Value::String(text) => text.clone(),
        other => other.to_string(),
    }
}

fn is_positive_int(value: &str) -> bool {
    !value.is_empty()
        && value.bytes().all(|b| b.is_ascii_digit())
        && value != "0"
        && value.parse::<u64>().is_ok_and(|n| n > 0)
}

fn parse_total_token(stdout: &str) -> Option<String> {
    let mut total = None;
    for token in stdout.split_whitespace() {
        if let Some(value) = token.strip_prefix("TOTAL=") {
            total = Some(value.to_owned());
        }
    }
    total
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;
    use std::sync::Mutex;

    struct FixedRender {
        prompt: String,
        rc: i32,
    }

    impl SpecialistRenderPort for FixedRender {
        fn render_specialist(&self, _sentinel: &BTreeMap<String, String>) -> (i32, String) {
            (self.rc, self.prompt.clone())
        }
    }

    struct RejectValidator;

    impl ResearchOutputValidator for RejectValidator {
        fn validate(&self, _result_text: &str) -> bool {
            false
        }
    }

    struct RecordingBaseline {
        lines: Vec<String>,
        wrote: Mutex<bool>,
    }

    impl DirtyTreeBaselinePort for RecordingBaseline {
        fn write_from_baseline(
            &self,
            _baseline: &Path,
            _sidecar: &Path,
            _cwd: &Path,
        ) -> Vec<String> {
            *self.wrote.lock().expect("lock") = true;
            self.lines.clone()
        }
    }

    #[test]
    fn compact_sentinel_offset_accepts_bare_and_header_prefix() {
        assert_eq!(
            codex_compact_sentinel_offset("LARCH_PROMPT_SENTINEL=1\nKIND=specialist\n"),
            Some(0)
        );
        let prefixed = format!("{COLLECTOR_NS_STRONG_HEADER}LARCH_PROMPT_SENTINEL=1\n");
        assert_eq!(
            codex_compact_sentinel_offset(&prefixed),
            Some(COLLECTOR_NS_STRONG_HEADER.len())
        );
        assert_eq!(codex_compact_sentinel_offset("plain prompt"), None);
    }

    #[test]
    fn sentinel_round_trip_checks_hash() {
        let prompt = "rendered specialist";
        let body = render_codex_prompt_sidecar(
            prompt,
            &CodexPromptSidecarArgs {
                agent_file: "agents/code-reviewer.md",
                mode: "review",
                difficulty: "TRIVIAL",
                ..CodexPromptSidecarArgs::default()
            },
        );
        let read = read_codex_prompt_sentinel(
            &body,
            &FixedRender {
                prompt: prompt.to_owned(),
                rc: 0,
            },
        );
        assert_eq!(
            read,
            CodexPromptSentinelRead::Ok {
                prompt: prompt.to_owned()
            }
        );
        let mismatch = read_codex_prompt_sentinel(
            &body,
            &FixedRender {
                prompt: "different".to_owned(),
                rc: 0,
            },
        );
        assert!(matches!(mismatch, CodexPromptSentinelRead::Failed { .. }));
    }

    #[test]
    fn dirty_tree_writers_match_python_shapes() {
        assert_eq!(
            render_clean_readonly_dirty_tree(),
            "STATUS=clean\nMODE=baseline\nREASON=codex-sandbox-read-only\n"
        );
        assert!(render_unknown_dirty_tree(true, "reason").contains("UNTRACKED_BASELINE=present"));
        let paths = LauncherArtifactPaths::new("/tmp/out.txt");
        let plan = plan_capture_cursor_dirty_baseline(&paths);
        assert_eq!(plan.unlink.len(), 4);
        assert!(plan.baseline.ends_with("out.txt.untracked-baseline"));
        let port = RecordingBaseline {
            lines: vec!["STATUS=clean".to_owned()],
            wrote: Mutex::new(false),
        };
        let fallback = write_cursor_dirty_tree_from_baseline(
            &port,
            Path::new("/b"),
            Path::new("/s"),
            Path::new("/cwd"),
            || false,
        );
        assert_eq!(fallback.as_deref(), Some("STATUS=clean\n"));
    }

    #[test]
    fn retry_reset_clears_stale_streams() {
        let plan = plan_retry_artifact_reset(
            "codex",
            "attempt",
            Some("old sidecar"),
            Some("old diag"),
            Some("{\"event\":1}\n"),
        );
        assert_eq!(plan.history_entries.len(), 3);
        assert!(plan.unlink_kinds.contains(&LauncherArtifactKind::Events));
        assert!(
            plan.history_entries
                .iter()
                .all(|entry| entry.contains("====="))
        );
        let cursor = plan_retry_artifact_reset("cursor", "attempt", Some("x"), None, Some("keep"));
        assert!(!cursor.unlink_kinds.contains(&LauncherArtifactKind::Events));
        assert_eq!(cursor.history_entries.len(), 1);
    }

    #[test]
    fn cap_hit_and_token_cap_resolution() {
        assert_eq!(effective_review_token_cap(Some("10"), Some("99")), Some(10));
        assert_eq!(effective_review_token_cap(None, Some("10")), Some(10));
        assert_eq!(effective_review_token_cap(Some("0"), Some("x")), None);
        let artifacts =
            render_cap_hit_artifacts(10, "STATUS=cap_hit TOTAL=42\n", Some(Path::new("/t")));
        assert_eq!(artifacts.output, "STATUS=cap_hit\n");
        assert_eq!(artifacts.done, "0\n");
        assert!(artifacts.warning.contains("10 tokens exceeded (42"));
        assert!(artifacts.step_budget_env.is_some());
    }

    #[test]
    fn cursor_token_shapes_and_result_writes() {
        let canned = json!({"result":"{\"no_issues_found\": true}","usage":{"inputTokens":0,"outputTokens":8,"cacheReadTokens":0}});
        assert_eq!(cursor_input_work_tokens(&canned), 0);
        assert_eq!(
            plan_cursor_result_write("{\"no_issues_found\": true}\n", &canned, None),
            CursorResultWrite::Degraded {
                diag: Some(render_cursor_no_work_diag(&canned))
            }
        );
        let real = json!({"usage":{"inputTokens":5000,"cacheReadTokens":1200,"outputTokens":8}});
        assert_eq!(cursor_input_work_tokens(&real), 6200);
        assert_eq!(
            plan_cursor_result_write("{\"no_issues_found\": true}\n", &real, None),
            CursorResultWrite::Keep("{\"no_issues_found\": true}\n".to_owned())
        );
        let short = json!({"usage":{"outputTokens":1001}});
        assert_eq!(
            plan_cursor_result_write("short", &short, Some(&RejectValidator)),
            CursorResultWrite::Degraded { diag: None }
        );
        assert!(is_cursor_empty_result(r#"{"result":""}"#, true));
        assert!(!is_cursor_empty_result(r#"{"result":""}"#, false));
        assert!(!is_cursor_empty_result(r#"{"result":"x"}"#, true));
    }
}
