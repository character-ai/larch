//! Filesystem, Git, and bgjob effects for Rust-owned stall-recovery commands.
use crate::{
    FileIoErrorKind, GixRepository, PathIntent, SystemProcessIdentityHost, TemporaryRoot,
    atomic_write_bytes_in, atomic_write_utf8_in, ensure_directory_chain, open_confined_read,
    resolve_allow_missing,
};
use chrono::{SecondsFormat, Utc};
use larch_core::{
    Classification, ClassifyTextInput, CommentPolicy, CrStrip, DuplicatePolicy, FileFailureReport,
    IssueNormalization, KvDocument, NormalizeOutcomeInput, ParseOptions, RepositoryRead,
    artifact_prefix_valid, classification_signature, classify_text, daemon_liveness,
    failure_detail_sidecar_name, first_nonempty, is_terminal_merge_result, kv_text,
    normalize_file_failure_report, normalize_issue_output, normalize_outcome_values,
    public_text_is_sensitive, read_for, resume_hint_for, safe_bail_value, safe_dispatcher_value,
    safe_pattern_value, safe_phase, safe_phase_value, safe_step, safe_step_value, select_kv_bytes,
    state_value, terminal_state_valid, token_valid, truthy, unlink_entry,
    validate_process_identity,
};
#[cfg(unix)]
use nix::fcntl::{Flock, FlockArg};
use regex::Regex;
use sha2::{Digest as _, Sha256};
#[cfg(unix)]
use std::os::unix::{fs::OpenOptionsExt as _, fs::PermissionsExt as _};
use std::{
    collections::BTreeMap,
    env,
    fs::{self, File, OpenOptions},
    io::{ErrorKind, Read, Seek, SeekFrom, Write},
    path::{Path, PathBuf},
    sync::LazyLock,
};
const STATE_LAYERS: &[&str] = &["ship-pr-state.sh", "finalize-state.sh", "session-env.sh"];
const CHECKS_BGJOB_STEPS: &[(&str, &str)] = &[
    ("implement-step3-checks", "3"),
    ("implement-checks-step5-self-review", "5"),
    ("implement-step5-self-review", "5"),
];
const CLEAR_UPDATES: &[(&str, &str)] = &[
    ("STALL_TRACKING", "false"),
    ("STALL_STEP", ""),
    ("BAIL_REASON", ""),
    ("IMPLEMENT_BAIL_REASON", ""),
    ("EXIT_CODE", "unknown"),
];
/// Fixed evidence artifacts that contribute sensitive tokens to a stall report.
pub const STALL_RECOVERY_EVIDENCE_NAMES: &[&str] = &[
    "ship-pr-state.sh",
    "finalize-state.sh",
    "session-env.sh",
    "source-env.sh",
    "execution-issues.md",
    "run-log-pointer.txt",
    "plan.txt",
    "feature-description.txt",
    "issue-body.txt",
    "composed-plan.md",
    "final-summary.md",
    "validate-plan-commands.log",
    "design-log-publish.failure.log",
    "design-plan-write.failure.log",
    "design-publish-tail.failure.log",
    "design-publish-tail.stdout.log",
    "design-publish-tail.stderr.log",
    "design-publish-rename.stderr.log",
    "design-publish-log.stderr.log",
];
const MAX_PUBLIC_FILE_BYTES: u64 = 256_000;
/// Maximum byte length accepted for an optional failure-detail artifact.
pub const MAX_DETAIL_FILE_BYTES: u64 = 65_536;
const MAX_DETAIL_FILE_BYTES_USIZE: usize = 65_536;
static URL_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"https?://[^\s`)\]]+").expect("fixed regex"));
static GIT_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"git@github\.com:[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+").expect("fixed regex")
});
static GITHUB_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+").expect("fixed regex")
});
static HOST_PATH_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?:^|[\s`(])/(?:Users|home|private|tmp|var|Volumes)/[^\s`)]+")
        .expect("fixed regex")
});
/// Stable command exit classes for state mutation failures.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum StateMutationError {
    /// Existing state is malformed or unsafe and must not be replaced.
    Unsafe,
    /// A validated state mutation or readback failed.
    Failed,
}

/// Stable adapter errors mapped to command exit classes.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum StallRecoveryError {
    Usage,
    Unsafe,
    UnsafeDiagnostic(&'static str),
    Failed,
    Diagnostic(&'static str),
}

/// Inputs for one classification operation.
#[derive(Clone, Debug, Default)]
#[rustfmt::skip]
pub struct ClassificationRequest {
    pub tmpdir: PathBuf, pub primary_state_file: PathBuf, pub finalize_state_file: PathBuf,
    pub session_env_file: PathBuf, pub failure_detail_log: PathBuf, pub attempts_file: PathBuf,
    pub bail_reason: String, pub memory_stall: String, pub artifact_prefix: String, pub profile: String,
    pub stall_step: String, pub phase: String, pub exit_code: String, pub dispatcher: String,
}

/// Ordered classification values and their persisted artifact.
#[derive(Clone, Debug, Eq, PartialEq)]
#[rustfmt::skip]
pub struct ClassificationOutput {
    pub values: Vec<(String, String)>, pub file: PathBuf, pub warning: Option<&'static str>,
}

/// Inputs for one escalation ledger append.
#[derive(Clone, Debug)]
#[rustfmt::skip]
pub struct EscalationRequest {
    pub tmpdir: PathBuf, pub site: String, pub trigger: String, pub step: String, pub phase: String,
    pub dispatcher: String, pub exit_code: String, pub failure_detail_log: PathBuf,
    pub artifact_prefix: String, pub generic: bool,
}

/// Whether escalation reached its canonical or fallback ledger.
#[derive(Clone, Debug, Eq, PartialEq)]
#[rustfmt::skip]
pub enum EscalationOutput {
    Canonical(PathBuf), Fallback,
}

/// Stable record-escalation failure classes.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum EscalationError {
    Usage(&'static str),
    Failure(String),
}

#[doc = "Classify and publish local stall state.\n\n# Errors\nReturns a stable unsafe or I/O error class."]
#[rustfmt::skip]
pub fn classify(request: &ClassificationRequest) -> Result<ClassificationOutput, StallRecoveryError> {
    if !artifact_prefix_valid(&request.artifact_prefix) { return Err(StallRecoveryError::Usage); }
    let tmpdir = absolute_path(&request.tmpdir).map_err(|()| StallRecoveryError::Unsafe)?; if request.profile == "generic" { if !tmpdir.is_dir() { return Err(StallRecoveryError::Failed); } } else { ensure_directory_chain(&tmpdir).map_err(|_| StallRecoveryError::Failed)?; }
    let root = TemporaryRoot::resolve(Some(&tmpdir)).map_err(|_| StallRecoveryError::Unsafe)?;
    if request.profile == "generic" { return classify_generic(&root, request); }
    let primary = request_path(root.path(), &request.primary_state_file, "ship-pr-state.sh");
    if fs::symlink_metadata(&primary).is_ok_and(|metadata| metadata.file_type().is_symlink()) {
        return Err(StallRecoveryError::UnsafeDiagnostic("symlinked ship-pr-state.sh"));
    }
    if primary.is_file() {
        let text = read_lossy(&primary).map_err(|()| StallRecoveryError::Failed)?;
        if !assignment_lines_ok(&text) { return Err(StallRecoveryError::UnsafeDiagnostic("malformed ship-pr-state.sh")); }
    }
    let finalize = request_path(root.path(), &request.finalize_state_file, "finalize-state.sh");
    let session = request_path(root.path(), &request.session_env_file, "session-env.sh");
    let primary_values = read_state_map(&primary); let finalize_values = read_state_map(&finalize); let session_values = read_state_map(&session);
    let mut state = primary_values.clone(); state.extend(finalize_values.clone()); state.extend(session_values.clone());
    let mut step = first_nonempty(&[&request.stall_step, state_value(&state, "STALL_STEP")]).to_owned();
    let phase = first_nonempty(&[&request.phase, state_value(&state, "PHASE")]).to_owned();
    let bail = first_nonempty(&[&request.bail_reason, state_value(&state, "BAIL_REASON"), state_value(&state, "IMPLEMENT_BAIL_REASON")]).to_owned();
    let (detail, detail_valid, detail_value, warning) = read_detail_with_fallback(&root, &request.failure_detail_log, &request.artifact_prefix);
    let mut any_stall = [request.memory_stall.as_str(), state_value(&primary_values, "STALL_TRACKING"), state_value(&finalize_values, "STALL_TRACKING"), state_value(&session_values, "STALL_TRACKING")].into_iter().any(truthy);
    let abandoned = if any_stall { None } else { abandoned_checks_stall_step(root.path()) };
    if let Some(abandoned_step) = abandoned {
        any_stall = true; if step.is_empty() { abandoned_step.clone_into(&mut step); }
    }
    let mut evidence = detail;
    if !detail_valid {
        for name in STATE_LAYERS { evidence.push('\n'); evidence.push_str(&read_optional_evidence(&root.path().join(name))); }
    }
    let state_exit = state.get("EXIT_CODE").map_or("unknown", String::as_str);
    let raw_exit = first_nonempty(&[&request.exit_code, state_exit]);
    let lower = format!("{bail}\n{evidence}").to_ascii_lowercase();
    let terminal_merge = is_terminal_merge_result(state_value(&state, "MERGE_RESULT"));
    let postmerge = any_stall && phase == "postmerge" && step == "postmerge-flush" && terminal_merge;
    let postmerge_failure = postmerge && "redaction-failed post-merge-refresh-failed manifest-recovery-failed commit-failed".split_ascii_whitespace().any(|marker| lower.contains(marker));
    let expected_postmerge = postmerge && lower.contains("preterminal-outcome") && !postmerge_failure;
    let result = if abandoned.is_some() {
        classified("transient-infra", "checks-commit-route-retry", "checks-leg-abandoned")
    } else if !any_stall {
        classified("unrecoverable", "none", "no-stall")
    } else if postmerge_failure {
        classified("unrecoverable", "none", "postmerge-flush-failure")
    } else if expected_postmerge {
        classified("operator-action", "none", "postmerge-flush-expected")
    } else {
        classify_text(ClassifyTextInput { text: &evidence, bail: &bail, step: &step, detail_log_valid: detail_valid, exit_code: raw_exit, implement: true })
    };
    let hint = if postmerge_failure || expected_postmerge { result.resume_hint } else { resume_hint_for(result.failure_class, &step, &phase, result.pattern) };
    let dispatcher = first_nonempty(&[&request.dispatcher, state_value(&state, "DISPATCHER"), state_value(&state, "CODER_TOOL")]);
    let finish = FinishClassification { result, hint, step: &step, phase: &phase, stalled: any_stall, bail: &bail, detail: &detail_value, exit_code: raw_exit, dispatcher, evidence: &evidence, skill: None, repeat_exempt: expected_postmerge };
    finish_classification(&root, request, finish, Vec::new(), warning)
}

#[rustfmt::skip]
fn classify_generic(root: &TemporaryRoot, request: &ClassificationRequest) -> Result<ClassificationOutput, StallRecoveryError> {
    let state_file = if request.primary_state_file.as_os_str().is_empty() {
        stall_recovery_artifact_path(root.path(), "stall-recovery-terminal-state.env", &request.artifact_prefix)
    } else { request.primary_state_file.clone() };
    if !terminal_state_is_valid(root.path(), &state_file, true) { return Err(StallRecoveryError::Failed); }
    let found = read_terminal_state_map(&state_file);
    let step = state_value(&found, "STALL_STEP"); let phase = state_value(&found, "PHASE");
    let bail = state_value(&found, "BAIL_REASON"); let exit_code = state_value(&found, "EXIT_CODE");
    let source = state_value(&found, "SOURCE_SCRIPT");
    let detail_path = PathBuf::from(state_value(&found, "FAILURE_DETAIL_LOG"));
    let (evidence, detail_valid, detail_value, warning) = read_detail_with_fallback(root, &detail_path, &request.artifact_prefix);
    let evidence = if detail_valid { evidence } else { read_optional_evidence(&state_file) };
    let current_publish = state_value(&found, "TRIGGER") == "publish-tail-failed" && exit_code == "5"
        && !state_value(&found, "PUBLISH_ATTEMPT_ID").is_empty()
        && matches!(state_value(&found, "PUBLISH_RC_SOURCE"), "returned" | "exception");
    let result = if current_publish && state_value(&found, "PLAN_WRITE_OK") == "true" {
        classified("recoverable", "resume-post-plan-publish", "design-publish-tail-current-attempt")
    } else {
        let match_result = classify_text(ClassifyTextInput { text: &evidence, bail, step, detail_log_valid: detail_valid, exit_code, implement: false });
        classified(match_result.failure_class, "none", match_result.pattern)
    };
    let skill = if request.artifact_prefix == "design-failure" {
        "/design".to_owned()
    } else if request.artifact_prefix.is_empty() {
        "/implement".to_owned()
    } else {
        format!("/{}", request.artifact_prefix.split_once('-').map_or(request.artifact_prefix.as_str(), |(head, _)| head))
    };
    let mut extra = Vec::new();
    if current_publish {
        for key in ["LATEST_PHASE", "PUBLISH_RC_SOURCE", "PLAN_WRITE_OK", "PUBLISH_OK", "RENAMED", "LOG_PUBLISH_ATTEMPTED", "LOG_PUBLISH_COMPLETED", "PR_URL", "RECOVERY_BRANCH"] {
            let value = state_value(&found, key);
            if !value.is_empty() { extra.push((key.to_owned(), value.to_owned())); }
        }
    }
    let finish = FinishClassification { result, hint: result.resume_hint, step, phase, stalled: true, bail, detail: &detail_value, exit_code, dispatcher: source, evidence: &evidence, skill: Some(&skill), repeat_exempt: false };
    finish_classification(root, request, finish, extra, warning)
}

#[derive(Clone, Copy)]
#[rustfmt::skip]
struct FinishClassification<'a> {
    result: Classification, hint: &'a str, step: &'a str, phase: &'a str, stalled: bool,
    bail: &'a str, detail: &'a str, exit_code: &'a str, dispatcher: &'a str,
    evidence: &'a str, skill: Option<&'a str>, repeat_exempt: bool,
}

#[rustfmt::skip]
fn finish_classification(root: &TemporaryRoot, request: &ClassificationRequest, mut fields: FinishClassification<'_>, mut extra: Vec<(String, String)>, warning: Option<&'static str>) -> Result<ClassificationOutput, StallRecoveryError> {
    let signature = classification_signature(fields.skill, fields.result.failure_class, fields.hint, fields.step, fields.phase, fields.bail, fields.evidence);
    let repeated = !fields.repeat_exempt && same_cause_repeat(root, &request.attempts_file, fields.result.failure_class, &signature)?;
    if repeated {
        fields.result.failure_class = "same-cause-repeat"; fields.result.pattern = "same-cause-repeat";
        if fields.skill.is_none() { fields.hint = "none"; }
    }
    let exit_code = safe_exit_code(fields.exit_code);
    #[rustfmt::skip]
    let rows = [
        ("FAILURE_CLASS", fields.result.failure_class),
        ("FAILURE_SIGNATURE", signature.as_str()), ("RESUME_HINT", fields.hint),
        ("STALL_STEP", safe_step_value(fields.step)), ("PHASE", safe_phase_value(fields.phase)),
        ("STALL_TRACKING", if fields.stalled { "true" } else { "false" }),
        ("BAIL_REASON", safe_bail_value(fields.bail, fields.skill.is_some())),
        ("BAIL_REASON_RAW", if fields.skill.is_some() { fields.bail } else { fields.bail.split(['\n', '\r', '\u{b}', '\u{c}', '\u{1c}', '\u{1d}', '\u{1e}', '\u{85}', '\u{2028}', '\u{2029}']).next().unwrap_or("") }), ("FAILURE_DETAIL_LOG", fields.detail),
        ("EXIT_CODE", exit_code), ("MATCHED_CLASSIFIER_PATTERN", safe_pattern_value(fields.result.pattern)),
        ("DISPATCHER", safe_dispatcher_value(fields.dispatcher, fields.skill.is_some())),
    ];
    let mut values = rows.into_iter().map(|(key, value)| (key.to_owned(), value.to_owned())).collect::<Vec<_>>();
    values.append(&mut extra);
    let file = stall_recovery_artifact_path(root.path(), "stall-recovery-classification.env", &request.artifact_prefix);
    write_rows(root, &file, values.iter().map(|(key, value)| (key.as_str(), value.as_str())))?;
    Ok(ClassificationOutput { values, file, warning })
}

#[rustfmt::skip]
const fn classified(failure_class: &'static str, resume_hint: &'static str, pattern: &'static str) -> Classification {
    Classification { failure_class, resume_hint, pattern }
}

#[rustfmt::skip]
fn safe_exit_code(value: &str) -> &str { if value == "unknown" || (!value.is_empty() && value.bytes().all(|byte| byte.is_ascii_digit())) { value } else { "unknown" } }

/// One attempt-ledger append request.
#[derive(Clone, Debug)]
#[rustfmt::skip]
pub struct AttemptRecord {
    pub tmpdir: PathBuf, pub attempts_file: PathBuf, pub failure_class: String,
    pub signature: String, pub resume_hint: String, pub outcome: String,
}

#[doc = "Initialize the attempt ledger.\n\n# Errors\nReturns an unsafe-path or I/O error."]
#[rustfmt::skip]
pub fn init_attempts(tmpdir: &Path, requested: &Path) -> Result<(PathBuf, String), StallRecoveryError> {
    let (root, path) = attempts_path(tmpdir, requested)?;
    if !path.exists() {
        let now = utc_now();
        write_rows(&root, &path, [("version", "1"), ("created_utc", &now), ("attempt_count", "0")])?;
    }
    let count = read_state_map(&path).get("attempt_count").cloned().unwrap_or_else(|| "0".to_owned());
    Ok((path, count))
}

#[doc = "Append one attempt atomically.\n\n# Errors\nReturns an unsafe-path, malformed-state, or I/O error."]
#[rustfmt::skip]
pub fn record_attempt(request: &AttemptRecord) -> Result<String, StallRecoveryError> {
    if [&request.failure_class, &request.signature, &request.resume_hint, &request.outcome].into_iter().any(|value| value.contains(['\n', '\r'])) { return Err(StallRecoveryError::Diagnostic("attempt value contains newline")); }
    let (root, path) = attempts_path(&request.tmpdir, &request.attempts_file)?;
    let now = utc_now();
    let mut lines = if path.exists() {
        read_lossy(&path).map_err(|()| StallRecoveryError::Failed)?.lines().map(str::to_owned).collect::<Vec<_>>()
    } else {
        vec!["version=1".to_owned(), format!("created_utc={now}"), "attempt_count=1".to_owned()]
    };
    let count = if path.exists() {
        let raw = if lines.iter().any(|line| line.starts_with("attempt_count=")) { read_last_value(&lines.join("\n"), "attempt_count") } else { "0".to_owned() };
        let count = increment_decimal(&raw).ok_or(StallRecoveryError::Diagnostic("attempt_count is malformed"))?;
        let mut replaced = false;
        for line in &mut lines {
            if line.starts_with("attempt_count=") { *line = format!("attempt_count={count}"); replaced = true; }
        }
        if !replaced { lines.push(format!("attempt_count={count}")); }
        count
    } else { "1".to_owned() };
    lines.extend([
        format!("attempt.{count}.class={}", request.failure_class), format!("attempt.{count}.signature={}", request.signature),
        format!("attempt.{count}.resume_hint={}", request.resume_hint), format!("attempt.{count}.outcome={}", request.outcome),
        format!("attempt.{count}.utc={now}"), format!("last_class={}", request.failure_class),
        format!("last_signature={}", request.signature), format!("last_resume_hint={}", request.resume_hint), format!("last_outcome={}", request.outcome),
    ]);
    atomic_write_utf8_in(&root, &path, &(lines.join("\n") + "\n"), true, 0o600).map_err(|_| StallRecoveryError::Failed)?;
    Ok(count)
}

#[doc = "Normalize local outcome state.\n\n# Errors\nReturns an error when the temporary root is unsafe."]
#[rustfmt::skip]
pub fn normalize_outcome(tmpdir: &Path, memory_stall: &str) -> Result<Vec<(String, String)>, StallRecoveryError> {
    let tmpdir = absolute_path(tmpdir).map_err(|()| StallRecoveryError::Unsafe)?; if !tmpdir.is_dir() { let empty = BTreeMap::new(); return Ok(normalize_outcome_values(NormalizeOutcomeInput { ship: &empty, finalize: &empty, session: &empty, seed: &empty, classification: &empty, memory_stall, panel_failed: false })); }
    let root = TemporaryRoot::resolve(Some(&tmpdir)).map_err(|_| StallRecoveryError::Unsafe)?;
    let ship = read_state_map(&root.path().join("ship-pr-state.sh"));
    let finalize = read_state_map(&root.path().join("finalize-state.sh"));
    let session = read_state_map(&root.path().join("session-env.sh"));
    let seed = read_state_map(&root.path().join("ship-seed-input.env"));
    let classification = read_state_map(&root.path().join("stall-recovery-classification.env"));
    let issues = root.path().join("execution-issues.md"); let panel_failed = regular_nonsymlink(&issues, None) && read_lossy(&issues).unwrap_or_default().to_ascii_lowercase().contains("panel-failed");
    let input = NormalizeOutcomeInput { ship: &ship, finalize: &finalize, session: &session, seed: &seed, classification: &classification, memory_stall, panel_failed };
    Ok(normalize_outcome_values(input))
}

#[doc = "Normalize issue-helper stdout.\n\n# Errors\nReturns an error for unconfined input or failed I/O."]
#[rustfmt::skip]
pub fn normalize_issue_env(tmpdir: &Path, stdout_file: &Path, exit_code: Option<&str>) -> Result<IssueNormalization, StallRecoveryError> {
    let tmpdir = absolute_path(tmpdir).map_err(|()| StallRecoveryError::Unsafe)?;
    let invalid = StallRecoveryError::Diagnostic("--issue-stdout-file outside implement tmpdir");
    if !tmpdir.is_dir() { return Err(invalid); } let root = TemporaryRoot::resolve(Some(&tmpdir)).map_err(|_| invalid)?;
    let stdout_file = validate_local_path(&root, stdout_file, false).map_err(|_| invalid)?;
    if !stdout_file.is_file() {
        return Err(invalid);
    }
    let result = normalize_issue_output(&read_lossy(&stdout_file).map_err(|()| StallRecoveryError::Failed)?, exit_code);
    let env = root.path().join("stall-recovery-issue.env");
    match &result {
        IssueNormalization::Success { number, url } => write_rows(&root, &env, [("ISSUE_NUMBER", number.as_str()), ("ISSUE_URL", url.as_str())])?,
        IssueNormalization::Failure(_) => { let _ = fs::remove_file(env); }
    }
    Ok(result)
}

#[doc = "Normalize one file-failure helper environment.\n\n# Errors\nReturns an error for unconfined or invalid input."]
#[rustfmt::skip]
pub fn normalize_file_failure_report_env(tmpdir: &Path, env_file: &Path) -> Result<FileFailureReport, StallRecoveryError> {
    let tmpdir = absolute_path(tmpdir).map_err(|()| StallRecoveryError::Unsafe)?;
    if !tmpdir.is_dir() { return Err(StallRecoveryError::Diagnostic("--implement-tmpdir must exist")); }
    let root = TemporaryRoot::resolve(Some(&tmpdir)).map_err(|_| StallRecoveryError::Unsafe)?;
    let invalid = StallRecoveryError::Diagnostic("--file-failure-report-env invalid");
    let env_file = validate_local_path(&root, env_file, false).map_err(|_| invalid)?;
    if !env_file.is_file() { return Err(invalid); }
    Ok(normalize_file_failure_report(&read_state_map(&env_file)))
}

#[doc = "Append a sanitized, locked row.\n\n# Errors\nReturns an error when neither ledger can be written."]
#[rustfmt::skip]
pub fn record_escalation(request: &EscalationRequest) -> Result<EscalationOutput, EscalationError> {
    if !request.tmpdir.is_absolute() {
        return Err(EscalationError::Usage("record-escalation --implement-tmpdir is empty or not absolute"));
    }
    if !artifact_prefix_valid(&request.artifact_prefix) {
        return Err(EscalationError::Usage("--artifact-prefix must be a simple dash token"));
    }
    if !request.tmpdir.is_dir() { return Err(EscalationError::Failure("ledger path invalid".to_owned())); }
    let root = TemporaryRoot::resolve(Some(&request.tmpdir)).map_err(|_| EscalationError::Failure("fallback write failed".to_owned()))?;
    for (kind, value) in [("site", request.site.as_str()), ("trigger", request.trigger.as_str()), ("step", request.step.as_str()), ("phase", request.phase.as_str())] {
        if !token_valid(value, kind, request.generic) {
            let reason = format!("token-validation-failed kind={kind} value={}", diagnostic_token(value));
            return escalation_failure(&root, &reason, reason.clone());
        }
    }
    let (detail, skipped) = resolve_escalation_detail(&root, &request.failure_detail_log);
    let exit_code = safe_exit_code(&request.exit_code);
    let skipped = if skipped.is_empty() { String::new() } else { format!("\tdetail_log_skipped={skipped}") };
    let row = format!(
        "utc={}\tsite={}\ttrigger={}\tstep={}\tphase={}\tdispatcher={}\texit_code={}\tfailure_detail_log={}{}\n",
        utc_now(), request.site, request.trigger, request.step, request.phase,
        safe_dispatcher_value(&request.dispatcher, request.generic), exit_code, detail, skipped,
    );
    let ledger = stall_recovery_artifact_path(root.path(), "stall-recovery-escalation-ledger.tsv", &request.artifact_prefix);
    if validate_local_path(&root, &ledger, true).is_err() {
        return escalation_failure(&root, "ledger-path-invalid", "ledger path invalid".to_owned());
    }
    if append_locked(&root, &ledger, &row).is_ok() { return Ok(EscalationOutput::Canonical(ledger)); }
    let marker = stall_recovery_artifact_path(root.path(), "stall-recovery-escalation-record-failure.env", &request.artifact_prefix);
    let fallback = stall_recovery_artifact_path(root.path(), "stall-recovery-escalation-fallback.tsv", &request.artifact_prefix);
    if validate_local_path(&root, &marker, true).is_err()
        || validate_local_path(&root, &fallback, true).is_err()
    {
        return escalation_failure(&root, "fallback-path-invalid", "fallback path invalid".to_owned());
    }
    if atomic_write_utf8_in(&root, &marker, "RECORD_ESCALATION_FAILED=true\nREASON=canonical-ledger-not-writable\n", true, 0o600).is_err()
        || atomic_write_utf8_in(&root, &fallback, &row, true, 0o600).is_err()
    {
        return escalation_failure(&root, "recording-failed", "fallback write failed".to_owned());
    }
    Ok(EscalationOutput::Fallback)
}

#[rustfmt::skip]
fn escalation_failure(root: &TemporaryRoot, reason: &str, message: String) -> Result<EscalationOutput, EscalationError> {
    append_escalation_tool_failure(root, reason); Err(EscalationError::Failure(message))
}

#[rustfmt::skip]
fn append_locked(root: &TemporaryRoot, path: &Path, row: &str) -> Result<(), ()> {
    let confined = root.confine(path, PathIntent::Write).map_err(|_| ())?; confined.revalidate().map_err(|_| ())?; let path = confined.path();
    if fs::symlink_metadata(path).is_ok_and(|metadata| metadata.file_type().is_symlink() || !metadata.is_file() || permissions_readonly(&metadata)) { return Err(()); }
    #[cfg(unix)]
    {
        let file = OpenOptions::new().create(true).read(true).append(true).mode(0o600).custom_flags(nix::libc::O_NOFOLLOW).open(path).map_err(|_| ())?;
        let mut locked = Flock::lock(file, FlockArg::LockExclusive).map_err(|_| ())?;
        append_row(&mut locked, row)?; Ok(())
    }
    #[cfg(not(unix))]
    {
        let mut file = OpenOptions::new().create(true).read(true).append(true).open(path).map_err(|_| ())?;
        append_row(&mut file, row)
    }
}

#[rustfmt::skip]
fn append_row(file: &mut fs::File, row: &str) -> Result<(), ()> {
    let len = file.metadata().map_err(|_| ())?.len();
    if len > 0 {
        file.seek(SeekFrom::End(-1)).map_err(|_| ())?;
        let mut last = [0]; file.read_exact(&mut last).map_err(|_| ())?;
        if last[0] != b'\n' { file.write_all(b"\n").map_err(|_| ())?; }
    }
    file.write_all(row.as_bytes()).map_err(|_| ())?; file.flush().map_err(|_| ())
}

#[cfg(unix)]
#[rustfmt::skip]
fn permissions_readonly(metadata: &fs::Metadata) -> bool { metadata.permissions().mode() & 0o222 == 0 }

#[cfg(not(unix))]
#[rustfmt::skip]
fn permissions_readonly(metadata: &fs::Metadata) -> bool { metadata.permissions().readonly() }

fn append_escalation_tool_failure(root: &TemporaryRoot, reason: &str) {
    let path = root.path().join("execution-issues.md");
    if validate_local_path(root, &path, true).is_err() {
        return;
    }
    let entry = format!(
        "\n## Tool Failure: record-escalation\n\n- utc: `{}`\n- helper: `scripts/larch.sh stall-recovery record-escalation`\n- reason: `{reason}`\n",
        Utc::now().format("%Y-%m-%dT%H:%M:%SZ")
    );
    let _ = append_execution_issue(root, &path, &entry);
}

#[rustfmt::skip]
fn append_execution_issue(root: &TemporaryRoot, path: &Path, entry: &str) -> Result<(), ()> {
    let lock = path.with_file_name(format!("{}.lock.d", path.file_name().ok_or(())?.to_string_lossy()));
    root.confine(&lock, PathIntent::Write).map_err(|_| ())?;
    let acquired = (0..100).find_map(|attempt| match fs::create_dir(&lock) { Ok(()) => Some(true), Err(error) if error.kind() == ErrorKind::AlreadyExists && attempt < 99 => { std::thread::sleep(std::time::Duration::from_millis(50)); None }, Err(_) => Some(false) }).unwrap_or(false);
    if !acquired { return Err(()); }
    let result = (|| {
        let text = if path.exists() { let mut file = open_regular_nofollow(path).ok_or(())?; let mut bytes = Vec::new(); file.read_to_end(&mut bytes).map_err(|_| ())?; String::from_utf8_lossy(&bytes).into_owned() } else { String::new() };
        let rendered = render_execution_issue(&text, "Tool Failures", entry); atomic_write_utf8_in(root, path, &rendered, true, 0o600).map_err(|_| ())
    })();
    let _ = fs::remove_dir(lock); result
}

#[rustfmt::skip]
fn render_execution_issue(text: &str, category: &str, entry: &str) -> String {
    let header = format!("### {category}");
    if !text.lines().any(|line| line == header) {
        let prefix = if text.is_empty() { "" } else { "\n" }; return format!("{}{prefix}{header}\n\n{}\n", text.trim_end_matches('\n'), entry.trim_end_matches('\n'));
    }
    let mut output = Vec::new(); let mut inserted = false; let mut in_target = false;
    for line in text.lines() { if line == header { in_target = true; output.push(line.to_owned()); continue; } else if in_target && line.starts_with("### ") { if !inserted { output.extend([String::new(), entry.trim_end_matches('\n').to_owned()]); inserted = true; } in_target = false; } output.push(line.to_owned()); }
    if in_target && !inserted { output.extend([String::new(), entry.trim_end_matches('\n').to_owned()]); } output.join("\n") + "\n"
}

#[rustfmt::skip]
fn diagnostic_token(value: &str) -> String {
    let safe = if !value.is_empty() && value.bytes().all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'.' | b'_' | b':' | b'-')) { value } else { "redacted" };
    safe.chars().take(64).collect()
}
/// Clear all stall fields and abandoned checks registry rows.
/// # Errors
/// Returns `Unsafe` for unsafe state and `Failed` when a validated mutation fails.
pub fn clear_stall(tmpdir: &Path) -> Result<(), StateMutationError> {
    let tmpdir = absolute_path(tmpdir).map_err(|()| StateMutationError::Unsafe)?;
    if !tmpdir.exists() {
        clear_abandoned_checks_registry(&tmpdir);
        return Ok(());
    }
    let root = TemporaryRoot::resolve(Some(&tmpdir)).map_err(|_| StateMutationError::Unsafe)?;
    let tmpdir = root.path().to_path_buf();
    for name in [
        "stall-recovery-classification.env",
        "stall-recovery-issue.env",
    ] {
        let _ = fs::remove_file(tmpdir.join(name));
    }
    let mut present = Vec::new();
    for name in STATE_LAYERS {
        let path = tmpdir.join(name);
        match inspect_state(&path) {
            Ok(Some(text)) if state_syntax_ok(&text) => present.push((path, text)),
            Ok(Some(_)) | Err(StateMutationError::Unsafe) => {
                return Err(StateMutationError::Unsafe);
            }
            Ok(None) => {}
            Err(StateMutationError::Failed) => return Err(StateMutationError::Failed),
        }
    }
    for (path, text) in present {
        rewrite_state(&root, &path, &text, CLEAR_UPDATES)?;
        let rewritten = read_lossy(&path).map_err(|()| StateMutationError::Failed)?;
        if read_last_value(&rewritten, "STALL_TRACKING") != "false"
            || !read_last_value(&rewritten, "STALL_STEP").is_empty()
        {
            return Err(StateMutationError::Failed);
        }
    }
    clear_abandoned_checks_registry(&tmpdir);
    Ok(())
}
/// Seed terminal state, returning the legacy `rewrite` or `seed` mode.
/// # Errors
/// Returns `Unsafe` for unsafe state and `Failed` when a validated mutation fails.
pub fn seed_terminal_state(
    tmpdir: &Path,
    stall_step: &str,
    phase: &str,
) -> Result<&'static str, StateMutationError> {
    let tmpdir = absolute_path(tmpdir).map_err(|()| StateMutationError::Unsafe)?;
    let raw_state = tmpdir.join("ship-pr-state.sh");
    let existing = match inspect_state(&raw_state) {
        Ok(Some(text)) if state_syntax_ok(&text) => Some(text),
        Ok(Some(_)) | Err(StateMutationError::Unsafe) => return Err(StateMutationError::Unsafe),
        Ok(None) => None,
        Err(StateMutationError::Failed) => return Err(StateMutationError::Failed),
    };
    let prior = existing.as_deref().unwrap_or("");
    let step = safe_state_value(stall_step, prior, "STALL_STEP", "8", safe_step);
    let phase = safe_state_value(phase, prior, "PHASE", "ci-initial", safe_phase);
    ensure_directory_chain(&tmpdir).map_err(|_| StateMutationError::Failed)?;
    let root = TemporaryRoot::resolve(Some(&tmpdir)).map_err(|_| StateMutationError::Unsafe)?;
    let state = root.path().join("ship-pr-state.sh");
    let rewrite = existing
        .as_ref()
        .is_some_and(|text| !text.is_empty() && text.lines().any(|line| line.contains('=')));
    if rewrite {
        rewrite_state(
            &root,
            &state,
            existing.as_deref().unwrap_or(""),
            &[
                ("STALL_TRACKING", "true"),
                ("STALL_STEP", &step),
                ("PHASE", &phase),
            ],
        )?;
    } else {
        let text = format!(
            "PHASE={phase}\nSTALL_TRACKING=true\nSTALL_STEP={step}\nBAIL_REASON=\nBAIL_FAILURE_DETAIL_LOG=\nEXIT_CODE=4\n"
        );
        atomic_write_utf8_in(&root, &state, &text, false, 0o600)
            .map_err(|_| StateMutationError::Failed)?;
    }
    let written = read_lossy(&state).map_err(|()| StateMutationError::Failed)?;
    if read_last_value(&written, "STALL_TRACKING") != "true" {
        return Err(StateMutationError::Failed);
    }
    Ok(if rewrite { "rewrite" } else { "seed" })
}
/// Validate one terminal-state file below its owning temporary directory.
#[must_use]
pub fn terminal_state_is_valid(tmpdir: &Path, state: &Path, generic: bool) -> bool {
    if !state.is_absolute() || !tmpdir.is_dir() {
        return false;
    }
    let Ok(root) = TemporaryRoot::resolve(Some(tmpdir)) else {
        return false;
    };
    let Some(state) = canonical_root_spelling(&root, tmpdir, state) else {
        return false;
    };
    let Ok(confined) = root.confine(&state, PathIntent::Read) else {
        return false;
    };
    let Ok(text) = read_lossy(confined.path()) else {
        return false;
    };
    let normalized = text
        .lines()
        .map(str::trim)
        .filter(|line| !line.is_empty() && !line.starts_with('#'))
        .collect::<Vec<_>>()
        .join("\n");
    let Ok(document) = KvDocument::parse(&normalized, ParseOptions::environment()) else {
        return false;
    };
    let rows = document
        .rows()
        .iter()
        .map(|row| (row.key().to_owned(), row.value().to_owned()))
        .collect::<Vec<_>>();
    terminal_state_valid(&rows, generic, |value| {
        canonical_root_spelling(&root, tmpdir, Path::new(value))
            .is_some_and(|path| safe_regular_file(&root, &path, None))
    })
}
/// Rebuild the effective sensitive corpus and validate a Tier B public file.
#[must_use]
pub fn tier_b_public_file_is_valid(
    tmpdir: &Path,
    public_file: &Path,
    sensitive_corpus: &Path,
    artifact_prefix: &str,
) -> bool {
    if !tmpdir.is_absolute()
        || !public_file.is_absolute()
        || !sensitive_corpus.is_absolute()
        || !artifact_prefix_valid(artifact_prefix)
        || !regular_nonsymlink(public_file, Some(MAX_PUBLIC_FILE_BYTES))
    {
        return false;
    }
    let Ok(root) = TemporaryRoot::resolve(Some(tmpdir)) else {
        return false;
    };
    let Some(sensitive_corpus) = canonical_root_spelling(&root, tmpdir, sensitive_corpus) else {
        return false;
    };
    if !safe_regular_file(&root, &sensitive_corpus, None) {
        return false;
    }
    let effective = root.path().join(format!(
        "{}-sensitive-corpus.public.effective",
        if artifact_prefix.is_empty() {
            "stall-recovery"
        } else {
            artifact_prefix
        }
    ));
    let corpus = build_sensitive_corpus(&root, &sensitive_corpus, artifact_prefix);
    if atomic_write_utf8_in(&root, &effective, &corpus, false, 0o600).is_err() {
        return false;
    }
    let sensitive = read_lossy(public_file)
        .ok()
        .is_none_or(|candidate| public_text_is_sensitive(&corpus, &candidate));
    if sensitive {
        return false;
    }
    let _ = fs::remove_file(effective);
    true
}

/// Detect whether the active repository is a non-forked larch development clone.
#[must_use]
pub fn is_larch_dev_clone(tmpdir: &Path, working_tree_root: Option<&Path>) -> bool {
    let forked = STATE_LAYERS.iter().any(|name| {
        let path = tmpdir.join(name);
        regular_nonsymlink(&path, None)
            .then(|| read_lossy(&path).ok())
            .flatten()
            .is_some_and(|text| {
                matches!(
                    read_last_value(&text, "FORKED_TARGET")
                        .trim()
                        .to_ascii_lowercase()
                        .as_str(),
                    "1" | "true" | "yes" | "on"
                )
            })
    });
    if forked {
        return false;
    }
    let root = working_tree_root.map(Path::to_path_buf).or_else(|| {
        GixRepository::discover(env::current_dir().ok()?)
            .ok()?
            .location()
            .work_dir
            .map(|path| PathBuf::from(String::from_utf8_lossy(path.as_bytes()).into_owned()))
    });
    root.is_some_and(|root| regular_nonsymlink(&root.join("skills/implement/SKILL.md"), None))
}

/// Stable validation failures for an optional failure-detail log.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum FailureDetailLogError {
    /// The caller supplied a relative path.
    NonAbsolute,
    /// The path or a confined component is a symlink.
    Symlink,
    /// The path is not below the validated temporary root.
    OutsideTmpdir,
    /// The file disappeared before it could be opened.
    Missing,
    /// The path is not a regular file.
    NotRegularFile,
    /// The file exceeds the 64 KiB optional-evidence limit.
    Oversize,
    /// The operating system refused a safe read.
    Unreadable,
}

impl FailureDetailLogError {
    /// Return the legacy stable suffix used in ledger diagnostics.
    #[must_use]
    pub const fn suffix(self) -> &'static str {
        match self {
            Self::NonAbsolute => "non-absolute",
            Self::Symlink => "symlink",
            Self::OutsideTmpdir => "outside-tmpdir",
            Self::Missing => "missing",
            Self::NotRegularFile => "not-regular-file",
            Self::Oversize => "oversize",
            Self::Unreadable => "unreadable",
        }
    }

    /// Render the legacy user-facing validation diagnostic for `flag`.
    #[must_use]
    pub fn message(self, flag: &str) -> String {
        match self {
            Self::NonAbsolute => format!("stall-recovery: {flag} must be absolute"),
            Self::Symlink => format!("stall-recovery: {flag} must not be a symlink"),
            Self::OutsideTmpdir | Self::Missing | Self::NotRegularFile => {
                format!("stall-recovery: {flag} outside implement tmpdir")
            }
            Self::Oversize => format!("stall-recovery: {flag} exceeds 64KiB"),
            Self::Unreadable => format!("stall-recovery: {flag} unreadable"),
        }
    }
}

/// Classify a failure-detail path without reading its content.
///
/// The path must be absolute, regular, non-symlinked, below `root`, and at
/// most [`MAX_DETAIL_FILE_BYTES`] long.
///
/// # Errors
///
/// Returns the stable validation reason when the file is unsafe, too large, or
/// unreadable.
pub fn classify_failure_detail_log(
    root: &TemporaryRoot,
    path: &Path,
) -> Result<(), FailureDetailLogError> {
    open_failure_detail_log(root, path, Some(MAX_DETAIL_FILE_BYTES)).map(|_| ())
}

/// Read a validated failure-detail log as lossy UTF-8.
///
/// # Errors
///
/// Returns the stable validation reason when the file is unsafe, too large, or
/// unreadable.
pub fn read_validated_failure_detail_log(
    root: &TemporaryRoot,
    path: &Path,
) -> Result<String, FailureDetailLogError> {
    let (mut file, _size) = open_failure_detail_log(root, path, Some(MAX_DETAIL_FILE_BYTES))?;
    let mut bytes = Vec::new();
    file.read_to_end(&mut bytes)
        .map_err(|_| FailureDetailLogError::Unreadable)?;
    if bytes.len() > MAX_DETAIL_FILE_BYTES_USIZE {
        return Err(FailureDetailLogError::Oversize);
    }
    Ok(String::from_utf8_lossy(&bytes).into_owned())
}

/// Read optional failure evidence, returning an empty string for unsafe input.
#[must_use]
pub fn read_optional_failure_detail_evidence(root: &TemporaryRoot, path: &Path) -> String {
    read_validated_failure_detail_log(root, path).unwrap_or_default()
}

/// Materialize a bounded, private sidecar from an oversized detail log.
///
/// The returned path is absolute and confined below `root`. The sidecar name
/// uses the legacy SHA-256 seed so ledger references remain stable.
#[must_use]
pub fn materialize_truncated_failure_detail_log(
    root: &TemporaryRoot,
    path: &Path,
) -> Option<PathBuf> {
    let (mut source, size) = open_failure_detail_log(root, path, None).ok()?;
    let mut prefix = Vec::with_capacity(MAX_DETAIL_FILE_BYTES_USIZE);
    Read::by_ref(&mut source)
        .take(MAX_DETAIL_FILE_BYTES)
        .read_to_end(&mut prefix)
        .ok()?;
    let canonical = fs::canonicalize(path).ok()?;
    if !canonical.starts_with(root.path()) {
        return None;
    }
    let mut digest = Sha256::new();
    digest.update(canonical.to_string_lossy().as_bytes());
    digest.update([0]);
    digest.update(size.to_string().as_bytes());
    digest.update([0]);
    digest.update(&prefix);
    let fingerprint = format!("{:x}", digest.finalize());
    let name = format!(
        "stall-recovery-failure-detail-log-{}.truncated.log",
        &fingerprint[..16]
    );
    let sidecar = root.path().join(&name);
    atomic_write_bytes_in(root, &sidecar, &prefix, false, 0o600).ok()?;
    classify_failure_detail_log(root, &sidecar)
        .is_ok()
        .then_some(sidecar)
}

/// Find the newest valid failure-detail sidecar named by escalation evidence.
#[must_use]
pub fn latest_failure_detail_log_sidecar(
    root: &TemporaryRoot,
    ledger: &Path,
    fallback: &Path,
) -> Option<PathBuf> {
    detail_log_ledger_fields(root, ledger, fallback)
        .into_iter()
        .filter_map(|(utc, sequence, value)| {
            if value.contains('\0') || Path::new(&value).is_absolute() {
                None
            } else {
                let path = root.path().join(value);
                classify_failure_detail_log(root, &path)
                    .is_ok()
                    .then_some((utc, sequence, path))
            }
        })
        .max_by(|left, right| left.0.cmp(&right.0).then(left.1.cmp(&right.1)))
        .map(|(_, _, path)| path)
}

/// Read the primary detail log, or the newest valid ledger sidecar when allowed.
///
/// The returned path is the validated source used for the content. Invalid
/// primary input is intentionally ignored before considering a sidecar, which
/// preserves the former reporting fallback contract.
#[must_use]
pub fn read_failure_detail_log_with_sidecar_fallback(
    root: &TemporaryRoot,
    primary: &str,
    ledger: &Path,
    fallback: &Path,
    allow_without_primary: bool,
) -> Option<(String, PathBuf)> {
    if !primary.is_empty() {
        let path = PathBuf::from(primary);
        if let Ok(detail) = read_validated_failure_detail_log(root, &path) {
            return Some((detail, path));
        }
    } else if !allow_without_primary {
        return None;
    }
    let sidecar = latest_failure_detail_log_sidecar(root, ledger, fallback)?;
    read_validated_failure_detail_log(root, &sidecar)
        .ok()
        .map(|detail| (detail, sidecar))
}

fn detail_log_ledger_fields(
    root: &TemporaryRoot,
    ledger: &Path,
    fallback: &Path,
) -> Vec<(String, usize, String)> {
    let mut found = Vec::new();
    let mut sequence = 0;
    for path in [ledger, fallback] {
        if !safe_regular_file(root, path, None) {
            continue;
        }
        let Ok(text) = read_lossy(path) else {
            continue;
        };
        for row in text.lines() {
            sequence += 1;
            let mut utc = "";
            let mut detail = "";
            let Ok(document) = KvDocument::parse(&row.replace('\t', "\n"), ParseOptions::legacy())
            else {
                continue;
            };
            for field in document.rows() {
                if field.key() == "utc" {
                    utc = field.value();
                } else if field.key() == "failure_detail_log" {
                    detail = field.value();
                }
            }
            if !detail.is_empty() {
                found.push((utc.to_owned(), sequence, detail.to_owned()));
            }
        }
    }
    found
}

fn open_failure_detail_log(
    root: &TemporaryRoot,
    path: &Path,
    max_size: Option<u64>,
) -> Result<(File, u64), FailureDetailLogError> {
    if !path.is_absolute() {
        return Err(FailureDetailLogError::NonAbsolute);
    }
    if !path.starts_with(root.path()) {
        return Err(FailureDetailLogError::OutsideTmpdir);
    }
    let metadata = match fs::symlink_metadata(path) {
        Ok(metadata) if metadata.file_type().is_symlink() => {
            return Err(FailureDetailLogError::Symlink);
        }
        Ok(metadata) => metadata,
        Err(error) if error.kind() == ErrorKind::NotFound => {
            return Err(FailureDetailLogError::Missing);
        }
        Err(_) => return Err(FailureDetailLogError::Unreadable),
    };
    if !metadata.is_file() {
        return Err(FailureDetailLogError::NotRegularFile);
    }
    if max_size.is_some_and(|limit| metadata.len() > limit) {
        return Err(FailureDetailLogError::Oversize);
    }
    let confined = root
        .confine(path, PathIntent::Read)
        .map_err(|_| FailureDetailLogError::OutsideTmpdir)?;
    let file = open_confined_read(&confined).map_err(|error| match error.kind() {
        FileIoErrorKind::Symlink => FailureDetailLogError::Symlink,
        FileIoErrorKind::WrongFileType => FailureDetailLogError::NotRegularFile,
        _ => FailureDetailLogError::Unreadable,
    })?;
    let opened = file
        .metadata()
        .map_err(|_| FailureDetailLogError::Unreadable)?;
    if !opened.is_file() {
        return Err(FailureDetailLogError::NotRegularFile);
    }
    if max_size.is_some_and(|limit| opened.len() > limit) {
        return Err(FailureDetailLogError::Oversize);
    }
    Ok((file, opened.len()))
}

fn inspect_state(path: &Path) -> Result<Option<String>, StateMutationError> {
    let metadata = match fs::symlink_metadata(path) {
        Ok(metadata) => metadata,
        Err(error) if error.kind() == ErrorKind::NotFound => return Ok(None),
        Err(_) => return Err(StateMutationError::Failed),
    };
    if metadata.file_type().is_symlink() || !metadata.is_file() {
        return Err(StateMutationError::Unsafe);
    }
    if OpenOptions::new()
        .read(true)
        .write(true)
        .open(path)
        .is_err()
    {
        return Err(StateMutationError::Unsafe);
    }
    read_lossy(path)
        .map(Some)
        .map_err(|()| StateMutationError::Failed)
}

fn state_syntax_ok(text: &str) -> bool {
    text.lines()
        .all(|line| line.is_empty() || line.starts_with('#') || line.contains('='))
        && render_state(text, &[]).is_ok()
}

fn assignment_lines_ok(text: &str) -> bool {
    text.lines()
        .all(|line| line.is_empty() || line.starts_with('#') || line.contains('='))
}

fn rewrite_state(
    root: &TemporaryRoot,
    path: &Path,
    text: &str,
    updates: &[(&str, &str)],
) -> Result<(), StateMutationError> {
    let rendered = render_state(text, updates)?;
    atomic_write_utf8_in(root, path, &rendered, false, 0o600)
        .map_err(|_| StateMutationError::Failed)
}

fn render_state(text: &str, updates: &[(&str, &str)]) -> Result<String, StateMutationError> {
    let mut options = ParseOptions::legacy();
    options.comments = CommentPolicy::Skip;
    options.cr_strip = CrStrip::Suffix;
    let document = KvDocument::parse(text, options).map_err(|_| StateMutationError::Failed)?;
    let mut rows: Vec<(String, String)> = Vec::new();
    for row in document.rows() {
        if let Some((_, current)) = rows.iter_mut().find(|(current, _)| current == row.key()) {
            row.value().clone_into(current);
        } else {
            rows.push((row.key().to_owned(), row.value().to_owned()));
        }
    }
    for (key, value) in updates {
        if let Some((_, current)) = rows.iter_mut().find(|(current, _)| current == key) {
            (*value).clone_into(current);
        } else {
            rows.push(((*key).to_owned(), (*value).to_owned()));
        }
    }
    let refs = rows
        .iter()
        .map(|(key, value)| (key.as_str(), value.as_str()))
        .collect::<Vec<_>>();
    kv_text(&refs).map_err(|_| StateMutationError::Failed)
}

fn read_last_value(text: &str, key: &str) -> String {
    String::from_utf8_lossy(&select_kv_bytes(
        text.as_bytes(),
        key.as_bytes(),
        b"",
        DuplicatePolicy::Last,
        CrStrip::Both,
    ))
    .into_owned()
}

fn safe_state_value(
    argument: &str,
    prior: &str,
    key: &str,
    fallback: &str,
    validator: fn(&str, bool) -> bool,
) -> String {
    let prior = read_last_value(prior, key);
    let value = if !argument.is_empty() {
        argument.to_owned()
    } else if prior.is_empty() {
        fallback.to_owned()
    } else {
        prior
    };
    if validator(&value, true) || value == "unknown" {
        value
    } else {
        "unknown".to_owned()
    }
}

fn clear_abandoned_checks_registry(tmpdir: &Path) {
    let host = SystemProcessIdentityHost::new();
    for (path, _) in abandoned_checks_registry_rows(tmpdir, &host) {
        unlink_entry(&path);
    }
}

/// Return the first abandoned checks step using the shared Rust bgjob registry.
#[must_use]
pub fn abandoned_checks_stall_step(tmpdir: &Path) -> Option<&'static str> {
    let host = SystemProcessIdentityHost::new();
    abandoned_checks_registry_rows(tmpdir, &host)
        .into_iter()
        .next()
        .map(|(_, step)| step)
}

fn abandoned_checks_registry_rows(
    tmpdir: &Path,
    host: &SystemProcessIdentityHost,
) -> Vec<(PathBuf, &'static str)> {
    let mut abandoned = Vec::new();
    for &(step, stall_step) in CHECKS_BGJOB_STEPS {
        let Ok((path, Some(entry))) = read_for(tmpdir, step, None) else {
            continue;
        };
        if regular_nonsymlink(&entry.result_env, None) {
            continue;
        }
        let owner_dead = entry
            .owner
            .as_ref()
            .is_some_and(|owner| !validate_process_identity(host, owner).ok);
        if !daemon_liveness(host, &entry).live || owner_dead {
            abandoned.push((path, stall_step));
        }
    }
    abandoned
}

fn build_sensitive_corpus(root: &TemporaryRoot, sensitive: &Path, prefix: &str) -> String {
    let mut sources = vec![
        sensitive.to_path_buf(),
        stall_recovery_artifact_path(root.path(), "stall-recovery-classification.env", prefix),
        stall_recovery_artifact_path(root.path(), "stall-recovery-attempts.env", prefix),
        stall_recovery_artifact_path(root.path(), "stall-recovery-escalation-ledger.tsv", prefix),
        stall_recovery_artifact_path(
            root.path(),
            "stall-recovery-escalation-fallback.tsv",
            prefix,
        ),
        stall_recovery_artifact_path(
            root.path(),
            "stall-recovery-escalation-record-failure.env",
            prefix,
        ),
    ];
    sources.extend(
        STALL_RECOVERY_EVIDENCE_NAMES
            .iter()
            .map(|name| root.path().join(name)),
    );
    let class_file =
        stall_recovery_artifact_path(root.path(), "stall-recovery-classification.env", prefix);
    if let Ok(text) = read_lossy(&class_file) {
        let detail = read_last_value(&text, "FAILURE_DETAIL_LOG");
        let detail_path = Path::new(&detail);
        if !detail.is_empty()
            && let Some(detail_path) = canonical_root_spelling(root, root.path(), detail_path)
            && safe_regular_file(root, &detail_path, Some(MAX_DETAIL_FILE_BYTES))
        {
            sources.push(detail_path);
        }
    }
    build_sensitive_corpus_from_evidence(root, sources)
}

/// Build the effective sensitive-token corpus from confined report evidence.
///
/// Every input path is revalidated below `root`; missing, symlinked, and
/// non-regular files contribute no data. Callers can therefore pass optional
/// report artifacts without widening the trusted filesystem boundary.
#[must_use]
pub fn build_sensitive_corpus_from_evidence(
    root: &TemporaryRoot,
    sources: impl IntoIterator<Item = PathBuf>,
) -> String {
    let mut lines = Vec::new();
    for source in sources {
        if !safe_regular_file(root, &source, None) {
            continue;
        }
        let Ok(text) = read_lossy(&source) else {
            continue;
        };
        lines.extend(text.lines().map(str::to_owned));
        for regex in [&*URL_RE, &*GIT_RE, &*GITHUB_RE, &*HOST_PATH_RE] {
            lines.extend(
                regex
                    .find_iter(&text)
                    .map(|found| found.as_str().trim().to_owned()),
            );
        }
    }
    lines
        .into_iter()
        .map(|line| line.trim().to_owned())
        .filter(|line| !line.is_empty())
        .collect::<Vec<_>>()
        .join("\n")
        + "\n"
}

#[rustfmt::skip]
fn request_path(root: &Path, requested: &Path, fallback: &str) -> PathBuf { if requested.as_os_str().is_empty() { root.join(fallback) } else { requested.to_path_buf() } }

#[rustfmt::skip]
fn attempts_path(tmpdir: &Path, requested: &Path) -> Result<(TemporaryRoot, PathBuf), StallRecoveryError> {
    if requested.as_os_str().is_empty() && !tmpdir.is_absolute() { return Err(StallRecoveryError::Diagnostic("--attempts-file must be absolute")); } let tmpdir = absolute_path(tmpdir).map_err(|()| StallRecoveryError::Unsafe)?;
    if !tmpdir.is_dir() { return Err(StallRecoveryError::Diagnostic("--attempts-file outside implement tmpdir")); }
    let root = TemporaryRoot::resolve(Some(&tmpdir)).map_err(|_| StallRecoveryError::Unsafe)?;
    let path = if requested.as_os_str().is_empty() { root.path().join("stall-recovery-attempts.env") } else { validate_attempts_path(&root, requested, true)? };
    Ok((root, path))
}

#[rustfmt::skip]
fn validate_attempts_path(root: &TemporaryRoot, path: &Path, write: bool) -> Result<PathBuf, StallRecoveryError> {
    if !path.is_absolute() {
        return Err(StallRecoveryError::Diagnostic("--attempts-file must be absolute"));
    }
    if fs::symlink_metadata(path).is_ok_and(|metadata| metadata.file_type().is_symlink()) {
        return Err(StallRecoveryError::Diagnostic("--attempts-file must not be a symlink"));
    }
    validate_local_path(root, path, write).map_err(|_| StallRecoveryError::Diagnostic("--attempts-file outside implement tmpdir"))
}

#[rustfmt::skip]
fn validate_local_path(root: &TemporaryRoot, path: &Path, write: bool) -> Result<PathBuf, StallRecoveryError> {
    if !path.is_absolute()
        || fs::symlink_metadata(path).is_ok_and(|metadata| metadata.file_type().is_symlink() || !metadata.is_file())
    {
        return Err(StallRecoveryError::Unsafe);
    }
    let normalized = resolve_allow_missing(path).map_err(|_| StallRecoveryError::Unsafe)?;
    let intent = if write { PathIntent::Write } else { PathIntent::Read };
    root.confine(&normalized, intent).map(|confined| confined.path().to_path_buf()).map_err(|_| StallRecoveryError::Unsafe)
}

#[rustfmt::skip]
fn read_state_map(path: &Path) -> BTreeMap<String, String> { if !path.is_file() { return BTreeMap::new(); } let Ok(text) = read_lossy(path) else { return BTreeMap::new(); }; let mut options = ParseOptions::legacy(); options.cr_strip = CrStrip::Both; KvDocument::parse(&text, options).map(|document| document.rows().iter().map(|row| (row.key().to_owned(), row.value().to_owned())).collect()).unwrap_or_default() }

#[rustfmt::skip]
fn read_terminal_state_map(path: &Path) -> BTreeMap<String, String> { let Ok(text) = read_lossy(path) else { return BTreeMap::new(); }; let normalized = text.lines().map(str::trim).filter(|line| !line.is_empty() && !line.starts_with('#')).collect::<Vec<_>>().join("\n"); KvDocument::parse(&normalized, ParseOptions::environment()).map(|document| document.rows().iter().map(|row| (row.key().to_owned(), row.value().to_owned())).collect()).unwrap_or_default() }

#[rustfmt::skip]
fn write_rows<'a>(root: &TemporaryRoot, path: &Path, rows: impl IntoIterator<Item = (&'a str, &'a str)>) -> Result<(), StallRecoveryError> {
    let refs: Vec<_> = rows.into_iter().collect();
    let text = kv_text(&refs).map_err(|_| StallRecoveryError::Failed)?;
    atomic_write_utf8_in(root, path, &text, true, 0o600).map_err(|_| StallRecoveryError::Failed)
}

#[rustfmt::skip]
fn latest_attempt_signature(path: &Path) -> String {
    let values = read_state_map(path);
    let count = state_value(&values, "attempt_count");
    if count == "0" || !count.bytes().all(|byte| byte.is_ascii_digit()) { String::new() }
    else { state_value(&values, &format!("attempt.{count}.signature")).to_owned() }
}

#[rustfmt::skip]
fn same_cause_repeat(root: &TemporaryRoot, requested: &Path, class: &str, signature: &str) -> Result<bool, StallRecoveryError> {
    if requested.as_os_str().is_empty() || matches!(class, "contract-failure" | "unrecoverable") {
        return Ok(false);
    }
    let attempts = validate_attempts_path(root, requested, true)?;
    Ok(attempts.is_file() && latest_attempt_signature(&attempts) == signature)
}

#[rustfmt::skip]
fn increment_decimal(value: &str) -> Option<String> {
    if value.is_empty() || !value.bytes().all(|byte| byte.is_ascii_digit()) {
        return None;
    }
    let mut digits = value.trim_start_matches('0').as_bytes().to_vec();
    if digits.is_empty() { digits.push(b'0'); }
    for digit in digits.iter_mut().rev() {
        if *digit < b'9' {
            *digit += 1; return String::from_utf8(digits).ok();
        }
        *digit = b'0';
    }
    digits.insert(0, b'1');
    String::from_utf8(digits).ok()
}

#[rustfmt::skip]
fn read_optional_evidence(path: &Path) -> String { regular_nonsymlink(path, Some(MAX_DETAIL_FILE_BYTES)).then(|| read_lossy(path).ok()).flatten().unwrap_or_default() }

#[derive(Clone, Debug)]
#[rustfmt::skip]
enum DetailStatus {
    Valid(PathBuf), Oversize(PathBuf, u64), Invalid(&'static str),
}

#[rustfmt::skip]
fn detail_status(root: &TemporaryRoot, path: &Path) -> DetailStatus {
    if !path.is_absolute() { return DetailStatus::Invalid("non-absolute"); }
    if fs::symlink_metadata(path).is_ok_and(|metadata| metadata.file_type().is_symlink()) { return DetailStatus::Invalid("symlink"); }
    let Ok(path) = resolve_allow_missing(path) else {
        return DetailStatus::Invalid("outside-tmpdir");
    };
    if !path.starts_with(root.path()) { return DetailStatus::Invalid("outside-tmpdir"); }
    let metadata = match fs::metadata(&path) {
        Ok(metadata) => metadata,
        Err(error) if error.kind() == ErrorKind::NotFound => return DetailStatus::Invalid("missing"),
        Err(_) => return DetailStatus::Invalid("unreadable"),
    };
    if !metadata.is_file() { return DetailStatus::Invalid("not-regular-file"); }
    if metadata.len() > MAX_DETAIL_FILE_BYTES { return DetailStatus::Oversize(path, metadata.len()); }
    DetailStatus::Valid(path)
}

#[rustfmt::skip]
fn read_detail(root: &TemporaryRoot, path: &Path) -> Option<String> {
    let DetailStatus::Valid(path) = detail_status(root, path) else { return None; };
    let mut source = open_regular_nofollow(&path)?;
    if source.metadata().ok()?.len() > MAX_DETAIL_FILE_BYTES { return None; }
    let mut bytes = Vec::new();
    source.read_to_end(&mut bytes).ok()?; Some(String::from_utf8_lossy(&bytes).into_owned())
}

#[rustfmt::skip]
fn read_detail_with_fallback(root: &TemporaryRoot, primary: &Path, prefix: &str) -> (String, bool, String, Option<&'static str>) {
    if primary.as_os_str().is_empty() {
        return (String::new(), false, String::new(), None);
    }
    if let Some(detail) = read_detail(root, primary) {
        return (detail, true, primary.to_string_lossy().into_owned(), None);
    }
    let warning = match detail_status(root, primary) {
        DetailStatus::Invalid(suffix) => Some(detail_warning(suffix)),
        DetailStatus::Oversize(_, _) => Some(detail_warning("oversize")), DetailStatus::Valid(_) => Some(detail_warning("unreadable")),
    };
    let ledger = stall_recovery_artifact_path(root.path(), "stall-recovery-escalation-ledger.tsv", prefix);
    let fallback = stall_recovery_artifact_path(root.path(), "stall-recovery-escalation-fallback.tsv", prefix);
    let Some(sidecar) = latest_detail_sidecar(root, &ledger, &fallback) else {
        return (String::new(), false, String::new(), warning);
    };
    read_detail(root, &sidecar).map_or_else(|| (String::new(), false, String::new(), warning), |detail| {
        (detail, true, fs::canonicalize(sidecar).unwrap_or_default().to_string_lossy().into_owned(), warning)
    })
}

#[rustfmt::skip]
fn detail_warning(suffix: &str) -> &'static str {
    match suffix {
        "non-absolute" => "--failure-detail-log must be absolute", "symlink" => "--failure-detail-log must not be a symlink",
        "oversize" => "--failure-detail-log exceeds 64KiB", "unreadable" => "--failure-detail-log unreadable",
        "outside-tmpdir" | "missing" | "not-regular-file" => "--failure-detail-log outside implement tmpdir",
        _ => "--failure-detail-log invalid",
    }
}

#[rustfmt::skip]
fn latest_detail_sidecar(root: &TemporaryRoot, ledger: &Path, fallback: &Path) -> Option<PathBuf> {
    let mut candidates: Vec<(String, usize, PathBuf)> = Vec::new();
    let mut sequence = 0;
    for path in [ledger, fallback] {
        if !regular_nonsymlink(path, None) { continue; }
        let Ok(text) = read_lossy(path) else { continue; };
        for row in text.lines() {
            sequence += 1;
            let value = tab_value(row, "failure_detail_log");
            if value.is_empty() || Path::new(&value).is_absolute() || value.contains('\0') { continue; }
            let candidate = root.path().join(value);
            if matches!(detail_status(root, &candidate), DetailStatus::Valid(_)) { candidates.push((tab_value(row, "utc"), sequence, candidate)); }
        }
    }
    candidates.into_iter().max().map(|(_, _, path)| path)
}

#[rustfmt::skip]
fn tab_value(row: &str, key: &str) -> String { KvDocument::parse(&row.replace('\t', "\n"), ParseOptions::legacy()).ok().and_then(|document| document.rows().iter().find(|field| field.key() == key).map(|field| field.value().to_owned())).unwrap_or_default() }

#[rustfmt::skip]
fn resolve_escalation_detail(root: &TemporaryRoot, requested: &Path) -> (String, String) {
    if requested.as_os_str().is_empty() { return (String::new(), String::new()); }
    match detail_status(root, requested) {
        DetailStatus::Valid(path) => { let value = path.strip_prefix(root.path()).unwrap_or(&path).to_string_lossy().into_owned(); if value.contains(['\t', '\n', '\r']) { (String::new(), "failure-detail-log-unsafe-name".to_owned()) } else { (value, String::new()) } },
        DetailStatus::Oversize(path, size) => materialize_detail_sidecar(root, &path, size).map_or_else(
            || (String::new(), "failure-detail-log-truncate-failed".to_owned()), |relative| (relative, String::new())),
        DetailStatus::Invalid(suffix) => (String::new(), format!("failure-detail-log-{suffix}")),
    }
}

#[rustfmt::skip]
fn materialize_detail_sidecar(root: &TemporaryRoot, path: &Path, size: u64) -> Option<String> {
    let mut source = open_regular_nofollow(path)?;
    let mut prefix = Vec::new();
    Read::by_ref(&mut source).take(MAX_DETAIL_FILE_BYTES).read_to_end(&mut prefix).ok()?;
    let resolved = fs::canonicalize(path).ok()?;
    let name = failure_detail_sidecar_name(&resolved.to_string_lossy(), size, &prefix);
    let sidecar = root.path().join(&name);
    atomic_write_bytes_in(root, &sidecar, &prefix, false, 0o600).ok()?;
    matches!(detail_status(root, &sidecar), DetailStatus::Valid(_)).then_some(name)
}

#[rustfmt::skip]
fn open_regular_nofollow(path: &Path) -> Option<fs::File> {
    let mut options = OpenOptions::new();
    options.read(true);
    #[cfg(unix)]
    options.custom_flags(nix::libc::O_NOFOLLOW);
    let file = options.open(path).ok()?;
    file.metadata().ok()?.is_file().then_some(file)
}

#[rustfmt::skip]
fn utc_now() -> String { Utc::now().to_rfc3339_opts(SecondsFormat::Micros, false) }

/// Build the default artifact path beneath a caller-validated temporary root.
#[must_use]
pub fn stall_recovery_artifact_path(tmpdir: &Path, default_name: &str, prefix: &str) -> PathBuf {
    if prefix.is_empty() || prefix == "stall-recovery" {
        tmpdir.join(default_name)
    } else {
        tmpdir.join(format!(
            "{prefix}{}",
            default_name
                .strip_prefix("stall-recovery")
                .unwrap_or(default_name)
        ))
    }
}

fn safe_regular_file(root: &TemporaryRoot, path: &Path, max_size: Option<u64>) -> bool {
    path.is_absolute()
        && root.confine(path, PathIntent::Read).is_ok()
        && regular_nonsymlink(path, max_size)
}

fn canonical_root_spelling(
    root: &TemporaryRoot,
    input_root: &Path,
    path: &Path,
) -> Option<PathBuf> {
    if !path.is_absolute()
        || fs::symlink_metadata(path).is_ok_and(|metadata| metadata.file_type().is_symlink())
    {
        return None;
    }
    if let Ok(relative) = path.strip_prefix(input_root) {
        return Some(root.path().join(relative));
    }
    let canonical = fs::canonicalize(path).ok()?;
    canonical.starts_with(root.path()).then_some(canonical)
}

fn regular_nonsymlink(path: &Path, max_size: Option<u64>) -> bool {
    fs::symlink_metadata(path).is_ok_and(|metadata| {
        metadata.is_file()
            && !metadata.file_type().is_symlink()
            && max_size.is_none_or(|limit| metadata.len() <= limit)
    })
}

fn absolute_path(path: &Path) -> Result<PathBuf, ()> {
    if path.is_absolute() {
        Ok(path.to_path_buf())
    } else {
        env::current_dir().map(|cwd| cwd.join(path)).map_err(|_| ())
    }
}

fn read_lossy(path: &Path) -> Result<String, ()> {
    fs::read(path)
        .map(|bytes| String::from_utf8_lossy(&bytes).into_owned())
        .map_err(|_| ())
}

#[cfg(test)]
mod tests {
    use super::{
        ClassificationRequest, EscalationError, EscalationOutput, EscalationRequest,
        FailureDetailLogError, MAX_DETAIL_FILE_BYTES, MAX_DETAIL_FILE_BYTES_USIZE,
        StateMutationError, classify, classify_failure_detail_log, clear_stall, is_larch_dev_clone,
        latest_failure_detail_log_sidecar, materialize_truncated_failure_detail_log,
        read_failure_detail_log_with_sidecar_fallback, read_validated_failure_detail_log,
        record_escalation, seed_terminal_state, terminal_state_is_valid,
    };
    use crate::TemporaryRoot;
    use std::{
        fs,
        path::{Path, PathBuf},
        thread,
    };

    #[rustfmt::skip]
    fn escalation(tmpdir: &Path) -> EscalationRequest {
        EscalationRequest {
            tmpdir: tmpdir.to_path_buf(),
            site: "step2".to_owned(),
            trigger: "step2-impl".to_owned(),
            step: "2".to_owned(),
            phase: "implementation".to_owned(),
            dispatcher: "codex".to_owned(),
            exit_code: "1".to_owned(),
            failure_detail_log: PathBuf::new(),
            artifact_prefix: String::new(),
            generic: false,
        }
    }

    #[test]
    fn seed_and_clear_preserve_unrelated_state() {
        let temp = tempfile::tempdir().expect("tempdir");
        let state = temp.path().join("ship-pr-state.sh");
        fs::write(&state, "KEEP=yes\nSTALL_STEP=9\nPHASE=merge\n").expect("seed fixture");
        assert_eq!(
            seed_terminal_state(temp.path(), "8a", "ci-initial"),
            Ok("rewrite")
        );
        let seeded = fs::read_to_string(&state).expect("seeded state");
        assert!(seeded.contains("KEEP=yes\n"));
        assert!(seeded.contains("STALL_TRACKING=true\n"));
        clear_stall(temp.path()).expect("clear state");
        let cleared = fs::read_to_string(&state).expect("cleared state");
        assert!(cleared.contains("KEEP=yes\n"));
        assert!(cleared.contains("STALL_TRACKING=false\n"));
    }

    #[test]
    fn malformed_state_fails_before_mutation() {
        let temp = tempfile::tempdir().expect("tempdir");
        let state = temp.path().join("ship-pr-state.sh");
        fs::write(&state, "STALL_TRACKING=true\npartial\n").expect("fixture");
        assert_eq!(clear_stall(temp.path()), Err(StateMutationError::Unsafe));
        assert_eq!(
            fs::read_to_string(state).expect("unchanged"),
            "STALL_TRACKING=true\npartial\n"
        );
    }

    #[test]
    fn terminal_validation_rejects_partial_files() {
        let temp = tempfile::tempdir().expect("tempdir");
        let state = temp.path().join("terminal.env");
        fs::write(
            &state,
            "DESIGN_FAILURE_VERSION=1\nDESIGN_FAILURE_KIND=terminal\n",
        )
        .expect("fixture");
        assert!(!terminal_state_is_valid(temp.path(), &state, true));
    }

    #[test]
    fn larch_dev_clone_rejects_a_fork_marker_in_every_state_layer() {
        let temporary = tempfile::tempdir().expect("tempdir");
        let state = temporary.path().join("state");
        let project = temporary.path().join("project");
        fs::create_dir_all(state.as_path()).expect("state fixture");
        fs::create_dir_all(project.join("skills/implement")).expect("project fixture");
        fs::write(project.join("skills/implement/SKILL.md"), "fixture\n").expect("project marker");
        fs::write(state.join("ship-pr-state.sh"), "FORKED_TARGET=false\n").expect("ship state");
        fs::write(state.join("finalize-state.sh"), "FORKED_TARGET=true\n").expect("finalize state");

        assert!(!is_larch_dev_clone(&state, Some(&project)));
    }

    #[test]
    fn failure_detail_log_reads_only_small_confined_regular_files() {
        let temp = tempfile::tempdir().expect("tempdir");
        let root = TemporaryRoot::resolve(Some(temp.path())).expect("temporary root");
        let detail = root.path().join("detail.log");
        fs::write(&detail, "bounded detail\n").expect("detail fixture");

        assert_eq!(classify_failure_detail_log(&root, &detail), Ok(()));
        assert_eq!(
            read_validated_failure_detail_log(&root, &detail),
            Ok("bounded detail\n".to_owned())
        );
        assert_eq!(
            classify_failure_detail_log(&root, &root.path().join("missing.log")),
            Err(FailureDetailLogError::Missing)
        );
        assert_eq!(
            FailureDetailLogError::Oversize.message("--failure-detail-log"),
            "stall-recovery: --failure-detail-log exceeds 64KiB"
        );
    }

    #[test]
    fn failure_detail_log_materializes_and_reads_the_newest_ledger_sidecar() {
        let temp = tempfile::tempdir().expect("tempdir");
        let root = TemporaryRoot::resolve(Some(temp.path())).expect("temporary root");
        let detail = root.path().join("large-detail.log");
        fs::write(&detail, vec![b'x'; MAX_DETAIL_FILE_BYTES_USIZE + 1])
            .expect("oversized detail fixture");
        assert_eq!(
            classify_failure_detail_log(&root, &detail),
            Err(FailureDetailLogError::Oversize)
        );

        let sidecar = materialize_truncated_failure_detail_log(&root, &detail)
            .expect("materialized detail sidecar");
        let fingerprint = sidecar
            .file_name()
            .and_then(|name| name.to_str())
            .and_then(|name| name.strip_prefix("stall-recovery-failure-detail-log-"))
            .and_then(|name| name.strip_suffix(".truncated.log"))
            .expect("legacy sidecar name");
        assert_eq!(fingerprint.len(), 16);
        assert!(fingerprint.bytes().all(|byte| byte.is_ascii_hexdigit()));
        assert_eq!(
            fs::metadata(&sidecar).expect("sidecar metadata").len(),
            MAX_DETAIL_FILE_BYTES
        );
        let relative = sidecar
            .strip_prefix(root.path())
            .expect("confined sidecar")
            .display()
            .to_string();
        let ledger = root.path().join("ledger.tsv");
        fs::write(
            &ledger,
            format!("utc=2026-01-01T00:00:00Z\tfailure_detail_log={relative}\n"),
        )
        .expect("ledger fixture");
        let fallback = root.path().join("fallback.tsv");

        assert_eq!(
            latest_failure_detail_log_sidecar(&root, &ledger, &fallback),
            Some(sidecar.clone())
        );
        let (detail, selected) =
            read_failure_detail_log_with_sidecar_fallback(&root, "", &ledger, &fallback, true)
                .expect("sidecar fallback");
        assert_eq!(selected, sidecar);
        assert_eq!(detail.len(), MAX_DETAIL_FILE_BYTES_USIZE);
    }

    #[test]
    #[rustfmt::skip]
    fn generic_classification_consumes_the_validated_trimmed_state() {
        let temp = tempfile::tempdir().expect("tempdir"); let state = temp.path().join("terminal.env"); fs::write(&state, "  DESIGN_FAILURE_VERSION=1  \n  DESIGN_FAILURE_KIND=terminal  \n  FAILURE_OUTCOME=approved  \n  STALL_STEP=8a  \n  PHASE=ship-pr  \n  SITE=ship-pr  \n  TRIGGER=main-agent-required  \n  BAIL_REASON=review-required  \n  EXIT_CODE=4  \n  FAILURE_DETAIL_LOG=  \n  SOURCE_SCRIPT=ship-pr  \n").expect("fixture");
        let request = ClassificationRequest { tmpdir: temp.path().to_path_buf(), primary_state_file: state, profile: "generic".to_owned(), artifact_prefix: "design-failure".to_owned(), ..ClassificationRequest::default() }; let output = classify(&request).expect("classify");
        let value = |key: &str| output.values.iter().find(|(found, _)| found == key).map(|(_, value)| value.as_str());
        assert_eq!(value("STALL_STEP"), Some("8a")); assert_eq!(value("PHASE"), Some("ship-pr")); assert_eq!(value("DISPATCHER"), Some("ship-pr"));
    }

    #[test]
    fn concurrent_escalation_rows_never_interleave() {
        let temp = tempfile::tempdir().expect("tempdir");
        let root = temp.path().to_path_buf();
        fs::write(
            root.join("stall-recovery-escalation-ledger.tsv"),
            "existing=row",
        )
        .expect("ledger fixture");
        let handles = (0..32)
            .map(|index| {
                let tmpdir = root.clone();
                thread::spawn(move || {
                    let mut request = escalation(&tmpdir);
                    request.exit_code = index.to_string();
                    record_escalation(&request)
                })
            })
            .collect::<Vec<_>>();
        for handle in handles {
            assert!(matches!(
                handle.join().expect("writer thread"),
                Ok(EscalationOutput::Canonical(_))
            ));
        }
        let ledger =
            fs::read_to_string(root.join("stall-recovery-escalation-ledger.tsv")).expect("ledger");
        let lines = ledger.lines().collect::<Vec<_>>();
        assert_eq!(lines.len(), 33);
        assert_eq!(lines[0], "existing=row");
        assert!(lines[1..].iter().all(|line| {
            line.matches("utc=").count() == 1
                && line.contains("\tsite=step2\ttrigger=step2-impl\t")
                && line.ends_with("\tfailure_detail_log=")
        }));
    }

    #[test]
    fn escalation_bounds_oversize_detail_in_a_deterministic_sidecar() {
        let temp = tempfile::tempdir().expect("tempdir");
        let detail = temp.path().join("detail.log");
        fs::write(&detail, vec![b'x'; 70_000]).expect("detail");
        let mut request = escalation(temp.path());
        request.failure_detail_log = detail;
        let output = record_escalation(&request).expect("record");
        assert!(matches!(output, EscalationOutput::Canonical(_)));
        let sidecars = fs::read_dir(temp.path())
            .expect("read dir")
            .filter_map(Result::ok)
            .filter(|entry| {
                entry
                    .file_name()
                    .to_string_lossy()
                    .ends_with(".truncated.log")
            })
            .collect::<Vec<_>>();
        assert_eq!(sidecars.len(), 1);
        assert_eq!(sidecars[0].metadata().expect("metadata").len(), 65_536);
    }

    #[cfg(unix)]
    #[test]
    fn failure_detail_log_rejects_a_symlink() {
        let temp = tempfile::tempdir().expect("tempdir");
        let root = TemporaryRoot::resolve(Some(temp.path())).expect("temporary root");
        let target = root.path().join("target.log");
        let link = root.path().join("detail.log");
        fs::write(&target, "bounded detail\n").expect("detail fixture");
        std::os::unix::fs::symlink(&target, &link).expect("detail symlink");

        assert_eq!(
            classify_failure_detail_log(&root, &link),
            Err(FailureDetailLogError::Symlink)
        );
    }

    #[cfg(unix)]
    #[test]
    #[rustfmt::skip]
    fn unsafe_canonical_ledger_fails_closed_and_records_the_reason() {
        use std::os::unix::fs::symlink;
        let temp = tempfile::tempdir().expect("tempdir");
        let target = temp.path().join("target");
        fs::write(&target, "unchanged").expect("target");
        fs::write(temp.path().join("execution-issues.md"), "### Tool Failures\n- existing\n\n### Warnings\n- warning\n").expect("issue fixture");
        symlink(&target, temp.path().join("stall-recovery-escalation-ledger.tsv")).expect("link");
        assert_eq!(record_escalation(&escalation(temp.path())), Err(EscalationError::Failure("ledger path invalid".to_owned())));
        assert_eq!(fs::read_to_string(target).expect("target"), "unchanged");
        let issue = fs::read_to_string(temp.path().join("execution-issues.md")).expect("issue");
        assert_eq!(issue.matches("### Tool Failures").count(), 1);
        assert!(issue.contains("reason: `ledger-path-invalid`"));
        assert!(issue.find("Tool Failure: record-escalation").unwrap() < issue.find("### Warnings").unwrap());
    }
}
