//! Behavior every larch vendor launcher shares, owned once.
//!
//! The review, drafter, Claude subprocess, CI, and implement launchers all
//! resolve the same execution-issues log, publish the same vendor
//! failure-diagnostic parts, discover the same work tree, emit the same
//! launcher failure envelope, publish the same artifact family, and record
//! Claude usage against the same ledger row. Each of those lives here so a
//! launcher never re-derives one.

use std::{
    env,
    ffi::OsString,
    path::{Path, PathBuf},
    sync::{Arc, Mutex, PoisonError},
    time::{Duration, SystemTime, UNIX_EPOCH},
};

use larch_adapters::{
    CursorConfigContext, NoopProcessObserver, PathIntent, TemporaryRoot, TokioProcessRunner,
    atomic_write_utf8_in, ensure_directory_chain, read_optional_utf8_lossy,
    runtime::{Cancellation, LarchRuntime},
    vendor_auth::{
        CursorPreflightConfig, CursorTokenPreread, VendorAuthContext, cursor_auth_preflight,
        cursor_preread_service_token,
    },
    vendor_diagnostics::write_failure_diag,
    vendor_lifecycle::StartupLockConfig,
};
use larch_core::{
    AuthVerdict, ChildEnvironment, ClaudeUsageTotals, ExternalAuthVerdict, LaunchFailureInputs,
    LauncherArtifact, LauncherArtifactKind, LauncherArtifactPaths, RepositoryRead as _, SafeText,
    VendorProgram, classify_launch_failure, emit_kv, external_auth_verdict, parse_claude_envelope,
    parse_claude_usage,
};

use crate::external_agent::{
    BareVendorOutput, BareVendorRun, ExternalAgentLaunch, ExternalAgentRouting,
    ExternalAgentStallWatch, platform_name, run_bare_vendor, shared_startup_lock_root,
};
use crate::python_verb::run_python_verb_best_effort;
use crate::run_log_entry_commands::{FailureRecordRequest, record_execution_failure};
use crate::timing_commands::record_vendor_timing;

/// Default cap on one vendor failure-diagnostic part, in bytes.
const DEFAULT_VENDOR_FAILURE_DIAG_BYTES: usize = 20_000;
/// Claude model for the conflict-resolution and lint-fix roles.
pub const CLAUDE_OPUS_MODEL: &str = "claude-opus-4-8";
/// Claude model for the CI-recovery and review-fix roles.
pub const CLAUDE_SONNET_1M_MODEL: &str = "claude-sonnet-4-6[1m]";
/// Ledger name the 1M Sonnet alias records under.
pub const CLAUDE_SONNET_BASE: &str = "claude-sonnet-4-6";

/// Resolve the execution-issues log this session writes launcher failures to.
///
/// `session_env` is the caller's `--session-env-path`, which wins over the
/// session tmpdir variables but not over an explicit log override.
pub fn execution_issues_log(session_env: &str) -> Option<PathBuf> {
    env::var_os("LARCH_EXECUTION_ISSUES_LOG")
        .filter(|value| !value.is_empty())
        .map(PathBuf::from)
        .or_else(|| {
            (!session_env.is_empty())
                .then(|| PathBuf::from(session_env))
                .and_then(|path| {
                    path.parent()
                        .map(|parent| parent.join("execution-issues.md"))
                })
        })
        .or_else(|| {
            ["IMPLEMENT_TMPDIR", "DESIGN_TMPDIR", "REVIEW_TMPDIR"]
                .into_iter()
                .find_map(|name| {
                    env::var_os(name)
                        .filter(|value| !value.is_empty())
                        .map(PathBuf::from)
                })
                .map(|path| path.join("execution-issues.md"))
        })
}

/// Append one redacted vendor failure-diagnostic part under `IMPLEMENT_TMPDIR`.
///
/// `label` is the full `===== … =====` heading, so the caller decides how its
/// site and tool read. Every step is best effort: a missing tmpdir, an
/// unresolvable root, or a failed write leaves the run untouched.
pub fn append_vendor_failure_diagnostic(source: &Path, label: &str, exit_code: i32) {
    let Some(root_path) = env::var_os("IMPLEMENT_TMPDIR")
        .filter(|value| !value.is_empty())
        .map(PathBuf::from)
    else {
        return;
    };
    let Ok(root) = TemporaryRoot::resolve(Some(&root_path)) else {
        return;
    };
    let parts = root.path().join("vendor-failure-diagnostics.parts");
    if ensure_directory_chain(&parts).is_err() {
        return;
    }
    let Ok(parts_root) = TemporaryRoot::resolve(Some(&parts)) else {
        return;
    };
    let body = read_optional_utf8_lossy(source)
        .unwrap_or_default()
        .unwrap_or_default();
    let body = if body.is_empty() {
        format!("no diagnostics captured (exit {exit_code})\n")
    } else {
        body
    };
    let text = format!(
        "===== {label} =====\nexit-code: {exit_code}\n{}\n",
        body.trim_end()
    );
    let redacted = SafeText::from_untrusted(&text).as_str().to_owned();
    let capped = larch_core::truncate_utf8_bytes(&redacted, vendor_failure_diagnostic_cap());
    let stamp = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_nanos();
    let _written = atomic_write_utf8_in(
        &parts_root,
        &parts.join(format!("part.{stamp:032x}")),
        capped,
        true,
        0o600,
    );
}

fn vendor_failure_diagnostic_cap() -> usize {
    env::var("LARCH_VENDOR_FAILURE_DIAG_BYTES")
        .ok()
        .and_then(|raw| raw.parse::<usize>().ok())
        .filter(|value| *value > 0)
        .unwrap_or(DEFAULT_VENDOR_FAILURE_DIAG_BYTES)
}

/// Resolve the work-tree root that owns one directory.
pub fn git_workdir(path: &Path) -> Option<PathBuf> {
    let repository = larch_adapters::GixRepository::discover(path).ok()?;
    let work_dir = repository.location().work_dir?;
    Some(PathBuf::from(
        String::from_utf8_lossy(work_dir.as_bytes()).into_owned(),
    ))
}

/// One launcher's terminal failure classification inputs.
pub struct LauncherFailureEnvelope<'a> {
    /// Launcher exit code.
    pub launcher_exit: i32,
    /// Vendor whose failure vocabulary applies.
    pub tool: VendorProgram,
    /// Authentication verdict already computed by the caller.
    pub auth_verdict: AuthVerdict,
    /// Whether the vendor executable was present.
    pub binary_present: bool,
    /// Diagnostic carrier text.
    pub sidecar: String,
    /// Published launcher output text.
    pub output: String,
    /// Reason used when the classifier has none.
    pub fallback_reason: &'a str,
    /// Output path exactly as the caller supplied it.
    pub output_label: &'a str,
}

/// Emit `LAUNCHER_FAILURE_CLASS`, `LAUNCHER_FAILURE_REASON`, and `OUTPUT`.
///
/// `LAUNCHER_EXIT` stays with the caller: some launchers emit it before the
/// artifacts that this classification reads exist.
pub fn emit_launcher_failure_envelope(envelope: &LauncherFailureEnvelope<'_>) {
    let sidecar = LauncherArtifact::present(envelope.sidecar.clone());
    let output = LauncherArtifact::present(envelope.output.clone());
    let failure = classify_launch_failure(&LaunchFailureInputs {
        launcher_exit: envelope.launcher_exit,
        tool: envelope.tool,
        auth_verdict: envelope.auth_verdict,
        binary_present: envelope.binary_present,
        sidecar: Some(&sidecar),
        output: Some(&output),
    });
    emit_kv("LAUNCHER_FAILURE_CLASS", failure.class().as_str());
    let reason = failure.reason().as_str();
    emit_kv(
        "LAUNCHER_FAILURE_REASON",
        if reason.is_empty() {
            envelope.fallback_reason
        } else {
            reason
        },
    );
    emit_kv("OUTPUT", envelope.output_label);
}

/// Resolve Cursor's model argv tokens, or an explicit single-model override.
pub fn cursor_model_argv(override_model: Option<&str>) -> Result<Vec<String>, String> {
    if let Some(model) = override_model.filter(|value| !value.is_empty()) {
        return Ok(vec!["--model".to_owned(), model.to_owned()]);
    }
    larch_core::resolve_model_args(
        larch_core::ModelTool::Cursor,
        true,
        "",
        larch_core::CodexModelRole::Default,
        &env::vars().collect(),
    )
    .map(|resolved| resolved.argv().to_vec())
    .map_err(|error| error.to_string())
}

/// Record one Claude subprocess's usage against the shared `claude_sub` row.
pub fn record_claude_sub_usage(usage: ClaudeUsageTotals, raw: &str, ledger_model: &str) {
    run_python_verb_best_effort([
        OsString::from("token"),
        OsString::from("record-vendor"),
        OsString::from("claude_sub"),
        OsString::from(format!("input={}", usage.input_tokens())),
        OsString::from(format!("output={}", usage.output_tokens())),
        OsString::from(format!("cache_read={}", usage.cache_read_tokens())),
        OsString::from(format!("cache_create={}", usage.cache_create_tokens())),
        OsString::from(format!("total={}", usage.total_tokens())),
        OsString::from(format!("raw={raw}")),
        OsString::from(format!("model={ledger_model}")),
    ]);
}

// ---------------------------------------------------------------------------
// Shared launcher artifact family
// ---------------------------------------------------------------------------

/// The confined artifact family published beside one launcher output.
pub struct LauncherArtifacts {
    /// Confinement root: the canonical parent of the launcher output.
    pub root: TemporaryRoot,
    /// Every artifact path derived from the resolved output path.
    pub paths: LauncherArtifactPaths,
    /// Output path exactly as the caller supplied it.
    pub raw_output: String,
}

impl LauncherArtifacts {
    /// Create the output's parent chain and confine the family below it.
    ///
    /// # Errors
    ///
    /// Returns a caller-facing message when the output names no file, its
    /// parent chain cannot be created, or the parent cannot be confined.
    pub fn create(output: &str) -> Result<Self, String> {
        let path = PathBuf::from(output);
        let (root, resolved) = confined_target(&path)
            .ok_or_else(|| format!("--output is not a confinable file: {output}"))?;
        Ok(Self {
            root,
            paths: LauncherArtifactPaths::new(resolved),
            raw_output: output.to_owned(),
        })
    }

    /// Atomically replace one artifact below the confinement root.
    pub fn write(&self, path: &Path, text: &str) {
        let _written = atomic_write_utf8_in(&self.root, path, text, true, 0o600);
    }

    /// Append to one artifact by republishing it.
    pub fn append(&self, path: &Path, text: &str) {
        let existing = read_text(path);
        self.write(path, &format!("{existing}{text}"));
    }

    /// Promote an inner completion sentinel to the published one.
    pub fn promote_inner_done(&self) {
        let inner = self.paths.path(LauncherArtifactKind::InnerDone);
        if inner.is_file() {
            let _renamed = std::fs::rename(&inner, self.paths.path(LauncherArtifactKind::Done));
        }
    }

    /// Path of one derived artifact.
    #[must_use]
    pub fn path(&self, kind: LauncherArtifactKind) -> PathBuf {
        self.paths.path(kind)
    }

    /// The resolved launcher output path.
    #[must_use]
    pub fn output(&self) -> &Path {
        self.paths.output()
    }
}

/// Read one artifact, treating an unreadable path as empty.
#[must_use]
pub fn read_text(path: &Path) -> String {
    read_optional_utf8_lossy(path)
        .unwrap_or_default()
        .unwrap_or_default()
}

/// Return whether a path is a regular file with content.
#[must_use]
pub fn is_non_empty_file(path: &Path) -> bool {
    std::fs::metadata(path).is_ok_and(|metadata| metadata.is_file() && metadata.len() > 0)
}

/// Return whether a vendor executable is reachable on `PATH`.
#[must_use]
pub fn vendor_on_path(program: VendorProgram) -> bool {
    let Ok(path) = env::var("PATH") else {
        return false;
    };
    env::split_paths(&path).any(|directory| directory.join(program.executable()).is_file())
}

/// Return whether a launcher argument is a positive decimal integer.
#[must_use]
pub fn is_positive_int(value: &str) -> bool {
    crate::claude_commands::parse_uint(value).is_some_and(|parsed| parsed > 0)
}

/// Return whether a `--model` argument is a single non-empty token.
#[must_use]
pub fn valid_model_token(value: &str) -> bool {
    !value.is_empty()
        && !value.chars().any(char::is_whitespace)
        && !value.chars().any(is_control_character)
}

/// Reject a dispatch `--site` label that cannot name a workflow surface.
///
/// Every panel dispatcher forwards this label into artifact rows and prompt
/// text, so a blank, flag-shaped, or control-bearing value is refused once.
///
/// # Errors
/// Returns the caller-prefixed refusal the retired dispatchers printed.
pub fn validate_site(prog: &str, site: &str) -> Result<(), String> {
    if site.trim().is_empty() || site.starts_with("--") {
        return Err(format!(
            "{prog}: --site requires a non-empty, non-flag-like value"
        ));
    }
    if site.chars().any(is_control_character) {
        return Err(format!(
            "{prog}: --site must not contain control characters"
        ));
    }
    Ok(())
}

/// Decode one `true`/`false` vendor-presence flag.
///
/// # Errors
/// Returns the caller-prefixed refusal for any other spelling.
pub fn parse_presence(prog: &str, flag: &str, raw: &str) -> Result<bool, String> {
    match raw {
        "true" => Ok(true),
        "false" => Ok(false),
        _ => Err(format!("{prog}: {flag} must be true or false")),
    }
}

/// Return whether a character is an ASCII control character.
#[must_use]
pub const fn is_control_character(character: char) -> bool {
    (character as u32) < 0x20 || character as u32 == 0x7f
}

/// Current wall-clock seconds since the epoch.
#[must_use]
pub fn unix_seconds() -> i64 {
    i64::try_from(
        SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs(),
    )
    .unwrap_or(0)
}

/// Stamp a launch's start time from inside the execute hook.
pub fn set_started(cell: &Mutex<i64>) {
    *cell.lock().unwrap_or_else(PoisonError::into_inner) = unix_seconds();
}

/// Read back the stamped start time.
#[must_use]
pub fn started_at(cell: &Mutex<i64>) -> i64 {
    *cell.lock().unwrap_or_else(PoisonError::into_inner)
}

/// Publish the preflight refusal bundle for a launch that ran no vendor.
pub fn write_preflight_bundle(
    artifacts: &LauncherArtifacts,
    tool: VendorProgram,
    timeout: &str,
    launcher_exit: i32,
    reason: PreflightRefusal<'_>,
) {
    artifacts.write(artifacts.output(), "");
    artifacts.write(
        &artifacts.path(LauncherArtifactKind::Diag),
        &format!("STATUS=FAILED\nFAILURE_REASON={}\n", reason.failure_reason),
    );
    artifacts.write(
        &artifacts.path(LauncherArtifactKind::Meta),
        &format!(
            "TOOL={}\nTIMEOUT={timeout}\nCAPTURE_STDOUT=false\nOUTPUT_FILE={}\nCMD_JSON=[]\n",
            tool.executable(),
            artifacts.raw_output,
        ),
    );
    artifacts.write(
        &artifacts.path(LauncherArtifactKind::Done),
        &format!("{launcher_exit}\n"),
    );
    emit_kv("LAUNCHER_EXIT", &launcher_exit.to_string());
    emit_launcher_failure_envelope(&LauncherFailureEnvelope {
        launcher_exit,
        tool,
        auth_verdict: AuthVerdict::Unclassified,
        binary_present: reason.binary_present,
        sidecar: format!("STATUS=FAILED\nFAILURE_REASON={}\n", reason.failure_reason),
        output: String::new(),
        fallback_reason: reason.failure_reason,
        output_label: &artifacts.raw_output,
    });
}

/// The refusal a preflight bundle records.
#[derive(Clone, Copy, Debug)]
pub struct PreflightRefusal<'a> {
    /// Operator-facing reason written to `.diag` and the envelope.
    pub failure_reason: &'a str,
    /// Whether the vendor executable was present when the launch was refused.
    pub binary_present: bool,
}

/// Choose the diagnostic carrier that describes one launcher failure.
#[must_use]
pub fn failure_source(artifacts: &LauncherArtifacts) -> PathBuf {
    [
        LauncherArtifactKind::FailureDiag,
        LauncherArtifactKind::Sidecar,
        LauncherArtifactKind::Diag,
    ]
    .into_iter()
    .map(|kind| artifacts.path(kind))
    .find(|path| is_non_empty_file(path))
    .unwrap_or_else(|| artifacts.path(LauncherArtifactKind::Diag))
}

/// Classify one launcher failure from its published artifacts.
#[must_use]
pub fn classify_launcher_failure(
    artifacts: &LauncherArtifacts,
    tool: VendorProgram,
    launcher_exit: i32,
    source: &Path,
    binary_present: bool,
) -> (String, String) {
    let texts = [
        read_text(source),
        read_text(&artifacts.path(LauncherArtifactKind::Sidecar)),
        read_text(&artifacts.path(LauncherArtifactKind::Diag)),
        read_text(&artifacts.path(LauncherArtifactKind::Stderr)),
        read_text(artifacts.output()),
    ];
    let verdict = external_auth_verdict(tool.executable(), texts.iter().map(String::as_str));
    let sidecar = LauncherArtifact::present(read_text(source));
    let output = LauncherArtifact::present(read_text(artifacts.output()));
    let failure = classify_launch_failure(&LaunchFailureInputs {
        launcher_exit,
        tool,
        auth_verdict: if verdict == ExternalAuthVerdict::Auth {
            AuthVerdict::Auth
        } else {
            AuthVerdict::Unclassified
        },
        binary_present,
        sidecar: Some(&sidecar),
        output: Some(&output),
    });
    (
        failure.class().as_str().to_owned(),
        failure.reason().as_str().to_owned(),
    )
}

/// Emit the launcher-result envelope every CI and fix caller parses.
pub fn emit_launcher_result(
    artifacts: &LauncherArtifacts,
    tool: VendorProgram,
    launcher_exit: i32,
    binary_present: bool,
) {
    let source = failure_source(artifacts);
    let (class, reason) =
        classify_launcher_failure(artifacts, tool, launcher_exit, &source, binary_present);
    emit_kv("LAUNCHER_EXIT", &launcher_exit.to_string());
    emit_kv("LAUNCHER_FAILURE_CLASS", &class);
    emit_kv("LAUNCHER_FAILURE_REASON", &reason);
    emit_kv("OUTPUT", &artifacts.raw_output);
}

/// Record one nonzero CI-family launch in the execution-issues log.
///
/// `site` names the lane — `ci fixer`, `lint fixer`, or `review fixer` — while
/// the tool label and category stay the shared CI vocabulary the run-log
/// consumers already parse.
pub fn append_ci_failure(
    artifacts: &LauncherArtifacts,
    tool: VendorProgram,
    launcher_exit: i32,
    site: &str,
    binary_present: bool,
) {
    if launcher_exit == 0 {
        return;
    }
    let source = failure_source(artifacts);
    let (class, reason) =
        classify_launcher_failure(artifacts, tool, launcher_exit, &source, binary_present);
    if let Some(log) = execution_issues_log(&env::var("SESSION_ENV_PATH").unwrap_or_default()) {
        let _recorded = record_execution_failure(&FailureRecordRequest {
            log: &log,
            site,
            tool: &format!("{}-ci", tool.executable()),
            exit_code: &launcher_exit.to_string(),
            category: "CI Issues",
            output_file: &source.display().to_string(),
            verdict: if reason.is_empty() { &class } else { &reason },
            retry_count: "",
            transient_retry_count: "",
            status_label: "",
            redact: true,
        });
    }
    append_vendor_failure_diagnostic(
        &source,
        &format!("{site} {}-ci", tool.executable()),
        launcher_exit,
    );
}

// ---------------------------------------------------------------------------
// Shared Claude fix lane
// ---------------------------------------------------------------------------

/// One Claude write-capable fix launch: CI recovery, lint repair, or review fix.
pub struct ClaudeFixLane<'a> {
    /// Artifact family this launch publishes into.
    pub artifacts: &'a LauncherArtifacts,
    /// Resolved Claude model id.
    pub model: &'a str,
    /// Deadline in seconds.
    pub timeout_seconds: u64,
    /// Timing ledger task kind.
    pub timing_task_kind: &'a str,
    /// Output sentinel prefix, for example `CLAUDE_LINT_FIX`.
    pub sentinel_prefix: &'a str,
    /// Heading written above a malformed envelope in the diagnostic.
    pub malformed_label: &'a str,
    /// Token ledger `raw` label.
    pub usage_raw: &'a str,
    /// Whether a non-JSON stdout is published as the result rather than refused.
    pub publish_non_json_stdout: bool,
}

/// Run one Claude fix launch and publish everything but the completion sentinel.
///
/// The caller writes the prompt artifact first: this lane transports it on the
/// child's standard input. Returns the launcher exit code, which the caller
/// still writes to `.done` and reports in the launcher envelope.
#[must_use]
pub fn run_claude_fix_lane(lane: &ClaudeFixLane<'_>) -> i32 {
    let artifacts = lane.artifacts;
    let workdir = env::current_dir().unwrap_or_else(|_error| PathBuf::from("."));
    let command: Vec<String> = [
        "claude",
        "-p",
        "--output-format",
        "json",
        "--model",
        lane.model,
        "--add-dir",
        &workdir.display().to_string(),
        "--allowedTools",
        "Read,Edit,Write",
    ]
    .map(str::to_owned)
    .to_vec();
    let prompt_path = artifacts.path(LauncherArtifactKind::Prompt);
    let stdout_path = artifacts.path(LauncherArtifactKind::Events);
    let stderr_path = artifacts.path(LauncherArtifactKind::Stderr);
    let start = unix_seconds();
    let mut exit_code = run_claude(
        artifacts,
        &command,
        lane.timeout_seconds,
        &workdir,
        &ClaudeStreams {
            stdin: &prompt_path,
            stdout: &stdout_path,
            stderr: &stderr_path,
        },
    );
    let end = unix_seconds();
    let outcome = publish_claude_result(
        lane,
        read_text(&stdout_path),
        read_text(&stderr_path),
        exit_code,
    );
    exit_code = outcome.exit_code;
    if !outcome.diagnostics.is_empty() {
        artifacts.write(
            &artifacts.path(LauncherArtifactKind::Diag),
            SafeText::from_untrusted(outcome.diagnostics.join("\n")).as_str(),
        );
    }
    if exit_code != 0 {
        let _written = write_failure_diag(&artifacts.root, &artifacts.paths, None, None, None);
    }
    record_vendor_timing(
        "claude",
        lane.timing_task_kind,
        start,
        end,
        artifacts.output(),
        exit_code,
        if exit_code == 0 { "complete" } else { "signal" },
    );
    if let Some(raw) = outcome.envelope_raw {
        record_claude_fix_usage(artifacts, &raw, lane.model, lane.usage_raw);
    }
    exit_code
}

/// What one Claude fix launch's captured streams resolved to.
struct ClaudeResultOutcome {
    exit_code: i32,
    diagnostics: Vec<String>,
    envelope_raw: Option<String>,
}

/// Publish the launcher output for one captured Claude envelope.
fn publish_claude_result(
    lane: &ClaudeFixLane<'_>,
    stdout: String,
    stderr: String,
    exit_code: i32,
) -> ClaudeResultOutcome {
    let artifacts = lane.artifacts;
    let mut outcome = ClaudeResultOutcome {
        exit_code,
        diagnostics: Vec::new(),
        envelope_raw: None,
    };
    let refuse = |outcome: &mut ClaudeResultOutcome, marker: &str, diagnostic: String| {
        outcome.exit_code = 1;
        artifacts.write(
            artifacts.output(),
            &format!("{}_{marker}\n", lane.sentinel_prefix),
        );
        outcome.diagnostics.push(diagnostic);
    };
    if !stdout.is_empty() && exit_code == 0 {
        let envelope = parse_claude_envelope(&stdout);
        match envelope.status {
            larch_core::ClaudeEnvelopeStatus::Ok => {
                artifacts.write(artifacts.output(), &envelope.text);
                outcome.envelope_raw = Some(stdout);
            }
            larch_core::ClaudeEnvelopeStatus::MalformedJson => refuse(
                &mut outcome,
                "MALFORMED_JSON",
                format!("{}:\n{stdout}", lane.malformed_label),
            ),
            larch_core::ClaudeEnvelopeStatus::IsError => {
                refuse(&mut outcome, "ERROR_RESPONSE", stdout);
            }
            larch_core::ClaudeEnvelopeStatus::NonObject
            | larch_core::ClaudeEnvelopeStatus::MissingResult
            | larch_core::ClaudeEnvelopeStatus::NonStringResult
            | larch_core::ClaudeEnvelopeStatus::EmptyResult => {
                refuse(&mut outcome, "EMPTY_RESULT", stdout);
            }
        }
    } else if !stdout.is_empty() && !lane.publish_non_json_stdout {
        refuse(&mut outcome, "NON_JSON_OUTPUT", stdout);
    } else {
        artifacts.write(artifacts.output(), &stdout);
    }
    if !stderr.is_empty() {
        outcome.diagnostics.push(stderr);
    }
    outcome
}

/// Where one Claude fix launch routes the child's three streams.
struct ClaudeStreams<'a> {
    stdin: &'a Path,
    stdout: &'a Path,
    stderr: &'a Path,
}

/// Run Claude with its prompt on standard input through the approved layer.
fn run_claude(
    artifacts: &LauncherArtifacts,
    command: &[String],
    timeout_seconds: u64,
    workdir: &Path,
    streams: &ClaudeStreams<'_>,
) -> i32 {
    let confine = |path: &Path, intent: PathIntent| {
        artifacts
            .root
            .confine(path, intent)
            .map_err(|error| error.to_string())
    };
    let files = confine(streams.stdin, PathIntent::Read).and_then(|stdin| {
        Ok((
            stdin,
            confine(streams.stdout, PathIntent::Write)?,
            confine(streams.stderr, PathIntent::Write)?,
        ))
    });
    let (stdin_file, stdout_file, stderr_file) = match files {
        Ok(files) => files,
        Err(error) => {
            artifacts.append(
                streams.stderr,
                &format!("Failed to launch child: {error}\n"),
            );
            return 127;
        }
    };
    match run_bare_vendor(&BareVendorRun {
        program: VendorProgram::Claude,
        argv: command,
        working_directory: workdir,
        environment: Vec::new(),
        stdin: Some(stdin_file),
        output: BareVendorOutput::Streams {
            stdout: Some(stdout_file),
            stderr: Some(stderr_file),
        },
        timeout_seconds,
    }) {
        Ok(exit_code) => exit_code,
        Err((exit_code, message)) => {
            artifacts.append(
                streams.stderr,
                &format!("Failed to launch child: {message}\n"),
            );
            exit_code
        }
    }
}

/// Publish one Claude fix launch's token record and ledger row.
fn record_claude_fix_usage(
    artifacts: &LauncherArtifacts,
    raw_envelope: &str,
    model: &str,
    usage_raw: &str,
) {
    let ledger_model = if model == CLAUDE_SONNET_1M_MODEL {
        CLAUDE_SONNET_BASE
    } else {
        model
    };
    let Some(usage) = serde_json::from_str::<serde_json::Value>(raw_envelope)
        .ok()
        .as_ref()
        .and_then(parse_claude_usage)
    else {
        return;
    };
    artifacts.write(
        &artifacts.path(LauncherArtifactKind::TokenRecord),
        &usage.token_record(ledger_model, usage_raw),
    );
    record_claude_sub_usage(usage, usage_raw, ledger_model);
}

// ---------------------------------------------------------------------------
// Shared vendor preflight
// ---------------------------------------------------------------------------

/// Resolve the repository a write-capable vendor lane edits.
#[must_use]
pub fn vendor_workdir() -> PathBuf {
    let current = env::current_dir().unwrap_or_else(|_error| PathBuf::from("."));
    if let Some(project) = env::var_os("CLAUDE_PROJECT_DIR").filter(|value| !value.is_empty())
        && let Some(toplevel) = git_workdir(Path::new(&project))
    {
        return toplevel;
    }
    git_workdir(&current).unwrap_or(current)
}

/// One launcher's Cursor authentication preflight.
pub struct CursorPreflightRequest<'a> {
    /// Prefix on infrastructure-failure diagnostics, for example `agent launch-ci`.
    pub diagnostic_prefix: &'a str,
    /// Caller identity the vendor preflight records, for example `agent launch-cursor-ci`.
    pub caller: &'a str,
    /// Repository the preflight probe runs in.
    pub workdir: &'a Path,
}

/// Prove Cursor can authenticate, returning the pre-read service credential.
///
/// # Errors
///
/// Returns the launcher exit code and message for a refused preflight or an
/// unreadable service token.
pub fn cursor_launch_credential(
    request: &CursorPreflightRequest<'_>,
) -> Result<Option<larch_core::CursorCredential>, (i32, String)> {
    let prefix = request.diagnostic_prefix;
    let runtime = LarchRuntime::current_thread()
        .map_err(|_error| (1, format!("{prefix}: could not start the local runtime")))?;
    let lock_root = shared_startup_lock_root().ok_or_else(|| {
        (
            1,
            format!("{prefix}: could not resolve the shared vendor startup-lock directory"),
        )
    })?;
    let startup_lock = StartupLockConfig::from_values(
        VendorProgram::Cursor,
        platform_name(),
        env::var(larch_core::env::USER).ok().as_deref(),
        None,
        None,
        None,
    )
    .map_err(|_error| {
        (
            1,
            format!("{prefix}: USER is unusable as a startup-lock path component"),
        )
    })?;
    let config = CursorPreflightConfig::from_values(
        platform_name(),
        env::var(larch_core::env::CURSOR_API_KEY).ok().as_deref(),
        request.caller,
    );
    let runner = TokioProcessRunner::new(Arc::new(NoopProcessObserver));
    let cancellation = Cancellation::new();
    let context = VendorAuthContext {
        temporary_root: &lock_root,
        startup_lock: &startup_lock,
        working_directory: request.workdir,
    };
    let verdict = runtime.block_on(cursor_auth_preflight(
        &runner,
        &config,
        context,
        &cancellation,
    ));
    if !verdict.ok {
        return Err((verdict.rc, verdict.message));
    }
    match runtime.block_on(cursor_preread_service_token(
        &runner,
        &config,
        context,
        &cancellation,
    )) {
        CursorTokenPreread::Proceed(credential) => Ok(credential),
        CursorTokenPreread::Unreadable => Err((
            larch_core::CURSOR_PREREAD_FAIL_RC,
            larch_core::CURSOR_PREREAD_FAIL_MSG.to_owned(),
        )),
    }
}

// ---------------------------------------------------------------------------
// Shared launcher argument scanning
// ---------------------------------------------------------------------------

/// Why the shared launcher flag scanner stopped.
pub enum FlagScanError {
    /// `-h` or `--help` appeared, so the caller prints its usage line.
    Help,
    /// An option outside the launcher's grammar.
    Unrecognized(String),
    /// A trailing option with no value.
    MissingValue(String),
}

/// Scan `--flag value` and `--flag=value` pairs for one launcher grammar.
///
/// Every legacy launcher parser accepted the same two spellings and reported
/// the same two argparse refusals, so the scan lives here once and each
/// launcher supplies only its own option table.
///
/// # Errors
///
/// Returns the first help request, unrecognized option, or missing value.
pub fn scan_flag_arguments(
    arguments: &[OsString],
    requires_value: &dyn Fn(&str) -> bool,
    apply: &mut dyn FnMut(&str, String),
) -> Result<(), FlagScanError> {
    let mut index = 0;
    while index < arguments.len() {
        let value = arguments[index].to_string_lossy();
        if value == "--help" || value == "-h" {
            return Err(FlagScanError::Help);
        }
        let (flag, inline) = crate::argparse_compat::split_inline_option(&value);
        if !requires_value(flag) {
            return Err(FlagScanError::Unrecognized(value.into_owned()));
        }
        let parameter = if let Some(inline) = inline {
            inline.to_owned()
        } else {
            let Some(next) = arguments.get(index + 1) else {
                return Err(FlagScanError::MissingValue(flag.to_owned()));
            };
            index += 1;
            next.to_string_lossy().into_owned()
        };
        apply(flag, parameter);
        index += 1;
    }
    Ok(())
}

// ---------------------------------------------------------------------------
// Shared vendor launch assembly
// ---------------------------------------------------------------------------

/// Everything one launcher fixes before its argv is known.
pub struct VendorLaunchPlan<'a> {
    /// Vendor this launch drives.
    pub program: VendorProgram,
    /// Artifact family the launch publishes into.
    pub artifacts: &'a LauncherArtifacts,
    /// Deadline in seconds.
    pub timeout_seconds: u64,
    /// Stream routing for the vendor's output.
    pub routing: ExternalAgentRouting,
    /// Repository the vendor runs in.
    pub working_directory: PathBuf,
    /// Typed child-environment overrides layered on the vendor defaults.
    pub environment: Vec<(ChildEnvironment, OsString)>,
    /// Progress channel watched for a stall, when the launcher enforces one.
    pub stall_watch: Option<ExternalAgentStallWatch>,
}

impl VendorLaunchPlan<'_> {
    /// Bind one built argv to this plan.
    #[must_use]
    pub fn launch(&self, argv: &[String]) -> ExternalAgentLaunch {
        ExternalAgentLaunch {
            tool: self.program.executable().to_owned(),
            output: self.artifacts.raw_output.clone(),
            timeout_seconds: self.timeout_seconds,
            command: argv.to_vec(),
            program: self.program,
            routing: self.routing.clone(),
            stderr_sink: None,
            working_directory: Some(self.working_directory.clone()),
            environment: self.environment.clone(),
            sentinel_suffix: LauncherArtifactKind::InnerDone.suffix(),
            poll_interval: LAUNCH_POLL_INTERVAL,
            stdin: None,
            stall_watch: self.stall_watch.clone(),
        }
    }
}

/// Interval between in-flight policy and stall samples while a vendor runs.
pub const LAUNCH_POLL_INTERVAL: Duration = Duration::from_secs(10);

/// Run one vendor through the approved layer, reporting a launcher failure.
#[must_use]
pub fn run_vendor_attempt(prog: &str, launch: &ExternalAgentLaunch) -> i32 {
    match crate::external_agent::run_external_agent_with_auth_retries(launch) {
        Ok(outcome) => outcome.exit_code,
        Err(error) => {
            eprintln!("{prog}: {error}");
            1
        }
    }
}

/// Run one ready vendor launch and resolve its launcher exit code.
#[must_use]
pub fn run_ready_launch_exit(
    descriptor: &'static larch_core::VendorDescriptor,
    profile: &str,
    request: &larch_core::VendorLaunchRequest,
    hooks: &larch_core::SyncLauncherHooks<'_>,
    prog: &str,
) -> i32 {
    match larch_core::run_ready_launch(descriptor, profile, request, hooks) {
        Ok(outcome) => larch_core::outcome_exit_code(&outcome, 1),
        Err(error) => {
            eprintln!("{prog}: {error}");
            1
        }
    }
}

/// Resolve the private Cursor configuration directory for one launch.
///
/// # Errors
///
/// Returns the operator-facing refusal each launcher publishes verbatim.
pub fn cursor_configuration_context() -> Result<CursorConfigContext, String> {
    let home = env::var_os("HOME").map_or_else(env::temp_dir, PathBuf::from);
    let temporary_root = TemporaryRoot::resolve(Some(&env::temp_dir())).map_err(|_error| {
        "cursor auth setup failed: could not resolve temporary root".to_owned()
    })?;
    CursorConfigContext::create(&temporary_root, &home)
        .map_err(|error| format!("cursor auth setup failed: {error}"))
}

// ---------------------------------------------------------------------------
// Shared usage recording
// ---------------------------------------------------------------------------

/// Record one Codex launch's per-bucket usage against the shared ledger.
pub fn record_codex_vendor_usage(totals: &larch_core::UsageTotals, label: &str, model: &str) {
    let mut arguments = vec![
        OsString::from("token"),
        OsString::from("record-vendor"),
        OsString::from("codex"),
        OsString::from(format!("input={}", totals.uncached_input_tokens())),
        OsString::from(format!("cache_read={}", totals.cached_input_tokens())),
        OsString::from(format!("output={}", totals.output_tokens())),
        OsString::from(format!("total={}", totals.total_tokens())),
        OsString::from(format!("raw={label}")),
    ];
    if !model.is_empty() {
        arguments.push(OsString::from(format!("model={model}")));
    }
    run_python_verb_best_effort(arguments);
}

/// One Cursor result envelope's four usage buckets.
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub struct CursorUsageBuckets {
    /// Uncached input tokens.
    pub input: i64,
    /// Output tokens.
    pub output: i64,
    /// Cache-read tokens.
    pub cache_read: i64,
    /// Cache-write tokens.
    pub cache_create: i64,
}

impl CursorUsageBuckets {
    /// Sum of every bucket.
    #[must_use]
    pub const fn total(self) -> i64 {
        self.input + self.output + self.cache_read + self.cache_create
    }
}

/// Parse the four usage buckets from one Cursor result envelope.
///
/// Returns `None` when the envelope carries no usage object at all, and the
/// parse error when a present bucket is unreadable. A bucket the vendor omitted
/// counts as zero, matching the retired parser.
///
/// # Errors
///
/// Returns the first unreadable bucket's parse error.
pub fn parse_cursor_usage_buckets(
    envelope: &str,
) -> Option<Result<CursorUsageBuckets, larch_core::UsageParseError>> {
    let value = serde_json::from_str::<serde_json::Value>(envelope).ok()?;
    let usage = value.get("usage")?.clone();
    let zero = serde_json::Value::from(0);
    let read = |primary: &str, alternate: &str| -> Result<i64, larch_core::UsageParseError> {
        larch_core::json_usage_number(Some(
            usage
                .get(primary)
                .or_else(|| usage.get(alternate))
                .unwrap_or(&zero),
        ))
    };
    let buckets = (|| {
        Ok(CursorUsageBuckets {
            input: read("inputTokens", "input_tokens")?,
            output: read("outputTokens", "output_tokens")?,
            cache_read: read("cacheReadTokens", "cache_read_input_tokens")?,
            cache_create: read("cacheWriteTokens", "cache_creation_input_tokens")?,
        })
    })();
    Some(buckets)
}

// ---------------------------------------------------------------------------
// Confined writes outside one artifact family
// ---------------------------------------------------------------------------

/// Atomically publish one file, confined to the directory that owns it.
///
/// Launchers write logs and session records that do not belong to their output
/// family — an implement sidecar log, a cap-hit record under the session root —
/// so each write resolves its own confinement root.
pub fn write_confined(path: &Path, text: &str) {
    let Some((root, target)) = confined_target(path) else {
        return;
    };
    let _written = atomic_write_utf8_in(&root, &target, text, true, 0o600);
}

/// Append to one file outside an artifact family by republishing it.
pub fn append_confined(path: &Path, text: &str) {
    let existing = read_text(path);
    write_confined(path, &format!("{existing}{text}"));
}

/// Resolve the canonical root and rebuilt path for one confined write.
///
/// The root is canonical, so the target is rebuilt under it: a path through a
/// symlinked parent — `/var/folders/…` on macOS — would otherwise read as an
/// escape from its own directory.
pub fn confined_target(path: &Path) -> Option<(TemporaryRoot, PathBuf)> {
    let parent = path.parent()?;
    let file_name = path.file_name()?;
    ensure_directory_chain(parent).ok()?;
    let root = TemporaryRoot::resolve(Some(parent)).ok()?;
    let target = root.path().join(file_name);
    Some((root, target))
}

// ---------------------------------------------------------------------------
// One shared vendor-launch execution
// ---------------------------------------------------------------------------

/// One vendor launch's descriptor, request, effects, and reporting identity.
pub struct VendorLaunchExecution<'a> {
    /// Frozen vendor descriptor that builds the argv.
    pub descriptor: &'static larch_core::VendorDescriptor,
    /// Descriptor argv profile.
    pub profile: &'a str,
    /// Ready launch request.
    pub request: &'a larch_core::VendorLaunchRequest,
    /// Process-layer plan the built argv is bound to.
    pub plan: VendorLaunchPlan<'a>,
    /// Diagnostic prefix for a launcher-level failure.
    pub prog: &'a str,
    /// Timing ledger task kind.
    pub timing_kind: &'a str,
    /// Effect run inside the execute hook, before the vendor starts.
    pub before_execute: Option<&'a (dyn Fn() + Sync)>,
    /// Effect run after execution to mirror vendor quota diagnostics.
    pub mirror_quota: Option<&'a (dyn Fn() + Sync)>,
    /// Effect run after execution with the resolved model id.
    pub record_usage: Option<&'a (dyn Fn(&str) + Sync)>,
}

/// Run one vendor launch through the shared lifecycle and return its exit code.
///
/// Every launcher stamps its start time inside the execute hook, runs the
/// vendor through the approved process layer, and records timing against the
/// same ledger, so that sequence lives here once.
#[must_use]
pub fn run_vendor_launch_execution(execution: &VendorLaunchExecution<'_>) -> i32 {
    let started = Mutex::new(unix_seconds());
    let execute = |argv: &[String]| -> larch_core::VendorProcessResult {
        set_started(&started);
        if let Some(effect) = execution.before_execute {
            effect();
        }
        larch_core::VendorProcessResult::new(run_vendor_attempt(
            execution.prog,
            &execution.plan.launch(argv),
        ))
    };
    let quota = |_result: &larch_core::VendorProcessResult| {
        if let Some(effect) = execution.mirror_quota {
            effect();
        }
    };
    let timing = |result: &larch_core::VendorProcessResult| {
        record_vendor_timing(
            execution.plan.program.executable(),
            execution.timing_kind,
            started_at(&started),
            unix_seconds(),
            execution.plan.artifacts.output(),
            result.exit_code,
            if result.exit_code == 0 {
                "complete"
            } else {
                "signal"
            },
        );
    };
    let usage = |model: &str| {
        if let Some(effect) = execution.record_usage {
            effect(model);
        }
    };
    let mut hooks = larch_core::SyncLauncherHooks::new(&execute);
    hooks.mirror_quota = Some(&quota);
    hooks.record_timing = Some(&timing);
    hooks.record_usage = Some(&usage);
    run_ready_launch_exit(
        execution.descriptor,
        execution.profile,
        execution.request,
        &hooks,
        execution.prog,
    )
}

/// Read one Cursor result envelope's usage buckets, noting a parse failure.
#[must_use]
pub fn cursor_usage_buckets(
    artifacts: &LauncherArtifacts,
    sidecar: &Path,
) -> Option<CursorUsageBuckets> {
    match parse_cursor_usage_buckets(&read_text(artifacts.output()))? {
        Ok(buckets) => Some(buckets),
        Err(error) => {
            artifacts.append(sidecar, &format!("agent parse-cursor-usage: {error}\n"));
            None
        }
    }
}

// ---------------------------------------------------------------------------
// One shared Claude fix launcher
// ---------------------------------------------------------------------------

/// One Claude write-capable fix launch, from preflight to launcher envelope.
pub struct ClaudeFixLaunch<'a> {
    /// Prompt already composed by the caller.
    pub prompt: &'a str,
    /// `--timeout` exactly as the caller supplied it.
    pub timeout: &'a str,
    /// Execution-issues site label, for example `lint fixer`.
    pub site: &'a str,
    /// The envelope lane the launch drives, which names its artifact family.
    pub lane: ClaudeFixLane<'a>,
}

/// Publish one Claude fix launch: prompt, preflight, lane, and envelope.
///
/// The CI, lint, and review fix launchers differ only in their prompt, model,
/// and ledger labels, so the ordered artifact publication lives here once.
#[must_use]
pub fn launch_claude_fix(launch: &ClaudeFixLaunch<'_>) -> i32 {
    let artifacts = launch.lane.artifacts;
    artifacts.write(&artifacts.path(LauncherArtifactKind::Prompt), launch.prompt);
    if !vendor_on_path(VendorProgram::Claude) {
        write_preflight_bundle(
            artifacts,
            VendorProgram::Claude,
            launch.timeout,
            127,
            PreflightRefusal {
                failure_reason: "claude binary missing",
                binary_present: false,
            },
        );
        append_ci_failure(artifacts, VendorProgram::Claude, 127, launch.site, false);
        return 0;
    }
    let exit_code = run_claude_fix_lane(&launch.lane);
    artifacts.write(
        &artifacts.path(LauncherArtifactKind::Done),
        &format!("{exit_code}\n"),
    );
    append_ci_failure(
        artifacts,
        VendorProgram::Claude,
        exit_code,
        launch.site,
        true,
    );
    emit_launcher_result(artifacts, VendorProgram::Claude, exit_code, true);
    0
}
