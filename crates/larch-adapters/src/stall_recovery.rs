//! Filesystem, Git, and bgjob effects for Rust-owned stall-recovery commands.
use crate::bgjob_recovery::{BgjobRecoveryOutcome, recover_abandoned_entry};
use crate::{
    FileIoErrorKind, GixRepository, PathIntent, SystemProcessIdentityHost, TemporaryRoot,
    atomic_write_bytes_in, atomic_write_utf8_in, ensure_directory_chain, lock_private_file,
    open_confined_read, resolve_allow_missing,
};
use chrono::{SecondsFormat, Utc};
use larch_core::{
    Classification, ClassifyTextInput, CommentPolicy, CrStrip, DuplicatePolicy, FileFailureReport,
    IssueNormalization, KvDocument, NormalizeOutcomeInput, ParseOptions, RegistryEntry,
    RepositoryRead, artifact_prefix_valid, classification_signature, classify_text,
    daemon_liveness, failure_detail_sidecar_name, first_nonempty, is_terminal_merge_result,
    kv_text, normalize_file_failure_report, normalize_issue_output, normalize_outcome_values,
    public_text_is_sensitive, read_for, redact, resume_hint_for, safe_bail_value,
    safe_dispatcher_value, safe_pattern_value, safe_phase, safe_phase_value, safe_step,
    safe_step_value, select_kv_bytes, state_value, terminal_state_valid, token_valid, truthy,
    validate_process_identity,
};
#[cfg(unix)]
use nix::fcntl::{Flock, FlockArg};
use regex::Regex;
use sha2::{Digest as _, Sha256};
#[cfg(unix)]
use std::os::unix::fs::{MetadataExt as _, OpenOptionsExt as _, PermissionsExt as _};
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
const CLEAR_TRANSACTION_FILE: &str = "stall-recovery-clear.transaction.env";
const CLEAR_TRANSACTION_VERSION: &str = "1";
const CLEAR_TRANSACTION_STATE: &str = "pending";
const ATTEMPT_LEDGER_LOCK_FILE: &str = ".stall-recovery-attempts.lock";
#[derive(Clone, Copy)]
struct ClearEntry {
    name: &'static str,
    marker_key: &'static str,
    state_layer: bool,
}
const CLEAR_ENTRIES: [ClearEntry; 5] = [
    ClearEntry {
        name: "ship-pr-state.sh",
        marker_key: "CLEAR_STALL_SHIP_PR_STATE",
        state_layer: true,
    },
    ClearEntry {
        name: "finalize-state.sh",
        marker_key: "CLEAR_STALL_FINALIZE_STATE",
        state_layer: true,
    },
    ClearEntry {
        name: "session-env.sh",
        marker_key: "CLEAR_STALL_SESSION_ENV",
        state_layer: true,
    },
    ClearEntry {
        name: "stall-recovery-classification.env",
        marker_key: "CLEAR_STALL_CLASSIFICATION",
        state_layer: false,
    },
    ClearEntry {
        name: "stall-recovery-issue.env",
        marker_key: "CLEAR_STALL_ISSUE",
        state_layer: false,
    },
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
static COMMENT_URL_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(
        r"^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/issues/[0-9]+#issuecomment-[0-9]+$",
    )
    .expect("fixed regex")
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

/// Durable clear-stall intent. A pending marker keeps partial atomic updates
/// distinguishable from a completed clear until the final commit removes it.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct ClearTransaction {
    present: [bool; CLEAR_ENTRIES.len()],
}

struct ClearPlan {
    transaction: ClearTransaction,
    newly_started: bool,
}

struct AttemptLedgerLock {
    _lock: crate::PrivateFileLock,
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

/// Complete outer decision branches for `/implement` stall classification.
///
/// The text classifier has its own data table in `larch_core`; this table keeps
/// the state-derived branches visible beside the adapter that owns them.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum ImplementClassificationBranch {
    AbandonedChecks,
    NoStall,
    PostmergeFailure,
    ExpectedPostmerge,
    Text,
}

#[derive(Clone, Copy)]
struct ImplementClassificationRule {
    branch: ImplementClassificationBranch,
    result: Option<Classification>,
    final_hint: bool,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct ImplementClassificationDecision {
    abandoned: bool,
    stalled: bool,
    postmerge: PostmergeClassification,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum PostmergeClassification {
    None,
    Failure,
    Expected,
}

const IMPLEMENT_CLASSIFICATION_TABLE: &[ImplementClassificationRule] = &[
    ImplementClassificationRule {
        branch: ImplementClassificationBranch::AbandonedChecks,
        result: Some(Classification {
            failure_class: "transient-infra",
            resume_hint: "checks-commit-route-retry",
            pattern: "checks-leg-abandoned",
        }),
        final_hint: false,
    },
    ImplementClassificationRule {
        branch: ImplementClassificationBranch::NoStall,
        result: Some(Classification {
            failure_class: "unrecoverable",
            resume_hint: "none",
            pattern: "no-stall",
        }),
        final_hint: false,
    },
    ImplementClassificationRule {
        branch: ImplementClassificationBranch::PostmergeFailure,
        result: Some(Classification {
            failure_class: "unrecoverable",
            resume_hint: "none",
            pattern: "postmerge-flush-failure",
        }),
        final_hint: true,
    },
    ImplementClassificationRule {
        branch: ImplementClassificationBranch::ExpectedPostmerge,
        result: Some(Classification {
            failure_class: "operator-action",
            resume_hint: "none",
            pattern: "postmerge-flush-expected",
        }),
        final_hint: true,
    },
    ImplementClassificationRule {
        branch: ImplementClassificationBranch::Text,
        result: None,
        final_hint: false,
    },
];

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum GenericClassificationBranch {
    CurrentPublish,
    Text,
}

#[derive(Clone, Copy)]
struct GenericClassificationRule {
    branch: GenericClassificationBranch,
    result: Option<Classification>,
}

const GENERIC_CLASSIFICATION_TABLE: &[GenericClassificationRule] = &[
    GenericClassificationRule {
        branch: GenericClassificationBranch::CurrentPublish,
        result: Some(Classification {
            failure_class: "recoverable",
            resume_hint: "resume-post-plan-publish",
            pattern: "design-publish-tail-current-attempt",
        }),
    },
    GenericClassificationRule {
        branch: GenericClassificationBranch::Text,
        result: None,
    },
];

const fn implement_classification_branch(
    decision: ImplementClassificationDecision,
) -> ImplementClassificationBranch {
    if decision.abandoned {
        ImplementClassificationBranch::AbandonedChecks
    } else if !decision.stalled {
        ImplementClassificationBranch::NoStall
    } else {
        match decision.postmerge {
            PostmergeClassification::Failure => ImplementClassificationBranch::PostmergeFailure,
            PostmergeClassification::Expected => ImplementClassificationBranch::ExpectedPostmerge,
            PostmergeClassification::None => ImplementClassificationBranch::Text,
        }
    }
}

fn implement_classification_rule(
    branch: ImplementClassificationBranch,
) -> ImplementClassificationRule {
    IMPLEMENT_CLASSIFICATION_TABLE
        .iter()
        .copied()
        .find(|rule| rule.branch == branch)
        .expect("outer implement classification table is exhaustive")
}

const fn generic_classification_branch(current_publish: bool) -> GenericClassificationBranch {
    if current_publish {
        GenericClassificationBranch::CurrentPublish
    } else {
        GenericClassificationBranch::Text
    }
}

fn generic_classification_rule(branch: GenericClassificationBranch) -> GenericClassificationRule {
    GENERIC_CLASSIFICATION_TABLE
        .iter()
        .copied()
        .find(|rule| rule.branch == branch)
        .expect("outer generic classification table is exhaustive")
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
    match clear_transaction_pending(&root) {
        Ok(true) => return Err(StallRecoveryError::UnsafeDiagnostic("stall clear transaction pending")),
        Ok(false) => {}
        Err(StateMutationError::Unsafe) => return Err(StallRecoveryError::Unsafe),
        Err(StateMutationError::Failed) => return Err(StallRecoveryError::Failed),
    }
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
    let postmerge = if postmerge_failure {
        PostmergeClassification::Failure
    } else if expected_postmerge {
        PostmergeClassification::Expected
    } else {
        PostmergeClassification::None
    };
    let branch = implement_classification_branch(ImplementClassificationDecision {
        abandoned: abandoned.is_some(),
        stalled: any_stall,
        postmerge,
    });
    let rule = implement_classification_rule(branch);
    let result = rule.result.unwrap_or_else(|| {
        classify_text(ClassifyTextInput {
            text: &evidence,
            bail: &bail,
            step: &step,
            detail_log_valid: detail_valid,
            exit_code: raw_exit,
            implement: true,
        })
    });
    let hint = if rule.final_hint {
        result.resume_hint
    } else {
        resume_hint_for(result.failure_class, &step, &phase, result.pattern)
    };
    let dispatcher = first_nonempty(&[&request.dispatcher, state_value(&state, "DISPATCHER"), state_value(&state, "CODER_TOOL")]);
    let finish = FinishClassification { result, hint, step: &step, phase: &phase, stalled: any_stall, bail: &bail, detail: &detail_value, exit_code: raw_exit, dispatcher, evidence: &evidence, skill: None, repeat_exempt: branch == ImplementClassificationBranch::ExpectedPostmerge };
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
    let branch = generic_classification_branch(
        current_publish && state_value(&found, "PLAN_WRITE_OK") == "true",
    );
    let rule = generic_classification_rule(branch);
    let result = rule.result.unwrap_or_else(|| {
        let match_result = classify_text(ClassifyTextInput {
            text: &evidence,
            bail,
            step,
            detail_log_valid: detail_valid,
            exit_code,
            implement: false,
        });
        classified(match_result.failure_class, "none", match_result.pattern)
    });
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
    let _lock = lock_attempt_ledger(&root, &path)?;
    if !path.exists() {
        let now = utc_now();
        write_rows(&root, &path, [("version", "1"), ("created_utc", &now), ("attempt_count", "0")])?;
    } else if !attempt_ledger_syntax_ok(&path)? {
        return Err(StallRecoveryError::Diagnostic("attempt ledger is malformed"));
    }
    let count = read_state_map(&path).get("attempt_count").cloned().unwrap_or_else(|| "0".to_owned());
    Ok((path, count))
}

#[doc = "Append one attempt atomically.\n\n# Errors\nReturns an unsafe-path, malformed-state, or I/O error."]
#[rustfmt::skip]
pub fn record_attempt(request: &AttemptRecord) -> Result<String, StallRecoveryError> {
    if [&request.failure_class, &request.signature, &request.resume_hint, &request.outcome].into_iter().any(|value| value.contains(['\n', '\r'])) { return Err(StallRecoveryError::Diagnostic("attempt value contains newline")); }
    let (root, path) = attempts_path(&request.tmpdir, &request.attempts_file)?;
    let _lock = lock_attempt_ledger(&root, &path)?;
    let now = utc_now();
    let mut lines = if path.exists() {
        let text = read_lossy(&path).map_err(|()| StallRecoveryError::Failed)?;
        if !state_syntax_ok(&text) {
            return Err(StallRecoveryError::Diagnostic("attempt ledger is malformed"));
        }
        text.lines().map(str::to_owned).collect::<Vec<_>>()
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
    if !attempt_record_is_visible(&path, &count, request) {
        return Err(StallRecoveryError::Failed);
    }
    Ok(count)
}

#[doc = "Normalize local outcome state.\n\n# Errors\nReturns an error when the temporary root is unsafe."]
#[rustfmt::skip]
pub fn normalize_outcome(tmpdir: &Path, memory_stall: &str) -> Result<Vec<(String, String)>, StallRecoveryError> {
    let tmpdir = absolute_path(tmpdir).map_err(|()| StallRecoveryError::Unsafe)?; if !tmpdir.is_dir() { let empty = BTreeMap::new(); return Ok(normalize_outcome_values(NormalizeOutcomeInput { ship: &empty, finalize: &empty, session: &empty, seed: &empty, classification: &empty, memory_stall, panel_failed: false })); }
    let root = TemporaryRoot::resolve(Some(&tmpdir)).map_err(|_| StallRecoveryError::Unsafe)?;
    match clear_transaction_pending(&root) {
        Ok(true) | Err(StateMutationError::Unsafe) => return Err(StallRecoveryError::Unsafe),
        Ok(false) => {}
        Err(StateMutationError::Failed) => return Err(StallRecoveryError::Failed),
    }
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
    match clear_transaction_pending(&root) {
        Ok(true) | Err(StateMutationError::Unsafe) => return Err(StallRecoveryError::Unsafe),
        Ok(false) => {}
        Err(StateMutationError::Failed) => return Err(StallRecoveryError::Failed),
    }
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

/// Read and validate the URL returned by a cross-repository comment mutation.
///
/// # Errors
/// Returns an error for an unconfined or unreadable response file.
pub fn file_failure_comment_url(
    tmpdir: &Path,
    response_file: &Path,
) -> Result<String, StallRecoveryError> {
    let text = read_file_failure_helper_file(tmpdir, response_file, "--response-file invalid")?;
    let url = serde_json::from_str::<serde_json::Value>(&text)
        .ok()
        .and_then(|value| {
            value
                .get("html_url")
                .and_then(serde_json::Value::as_str)
                .map(str::to_owned)
        })
        .filter(|url| COMMENT_URL_RE.is_match(url))
        .unwrap_or_default();
    Ok(url)
}

/// Find the first open issue whose body contains the exact stall signature.
///
/// # Errors
/// Returns an error for an unconfined or unreadable issue snapshot.
pub fn find_open_stall_issue(
    tmpdir: &Path,
    issues_file: &Path,
    marker: &str,
) -> Result<Option<String>, StallRecoveryError> {
    let text = read_file_failure_helper_file(tmpdir, issues_file, "--issues-file invalid")?;
    let marker = format!("<!-- larch-stall:signature={marker} -->");
    for line in text.lines().map(str::trim).filter(|line| !line.is_empty()) {
        let Ok(value) = serde_json::from_str::<serde_json::Value>(line) else {
            return Ok(None);
        };
        if value
            .get("pull_request")
            .is_some_and(|pull_request| !pull_request.is_null())
        {
            continue;
        }
        if !value
            .get("body")
            .and_then(serde_json::Value::as_str)
            .is_some_and(|body| body.contains(&marker))
        {
            continue;
        }
        let number = value.get("number").and_then(|number| {
            number
                .as_u64()
                .and_then(|number| (number != 0).then(|| number.to_string()))
                .or_else(|| {
                    number
                        .as_str()
                        .filter(|number| !number.is_empty())
                        .map(str::to_owned)
                })
        });
        return Ok(Some(number.unwrap_or_default()));
    }
    Ok(None)
}

fn read_file_failure_helper_file(
    tmpdir: &Path,
    path: &Path,
    diagnostic: &'static str,
) -> Result<String, StallRecoveryError> {
    let tmpdir = absolute_path(tmpdir).map_err(|()| StallRecoveryError::Unsafe)?;
    if !tmpdir.is_dir() {
        return Err(StallRecoveryError::Diagnostic(
            "--implement-tmpdir must exist",
        ));
    }
    let root = TemporaryRoot::resolve(Some(&tmpdir)).map_err(|_| StallRecoveryError::Unsafe)?;
    let path = validate_local_path(&root, path, false)
        .map_err(|_| StallRecoveryError::Diagnostic(diagnostic))?;
    if !path.is_file() {
        return Err(StallRecoveryError::Diagnostic(diagnostic));
    }
    read_lossy(&path).map_err(|()| StallRecoveryError::Failed)
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
    clear_stall_inner(tmpdir, None)
}

fn clear_stall_inner(
    tmpdir: &Path,
    fault_after_phase: Option<usize>,
) -> Result<(), StateMutationError> {
    let tmpdir = absolute_path(tmpdir).map_err(|()| StateMutationError::Unsafe)?;
    if !tmpdir.exists() {
        clear_abandoned_checks_registry(&tmpdir)?;
        return Ok(());
    }
    let root = TemporaryRoot::resolve(Some(&tmpdir)).map_err(|_| StateMutationError::Unsafe)?;
    let tmpdir = root.path().to_path_buf();
    let transaction = read_clear_transaction(&root)?;
    let plan = preflight_clear(&root, transaction)?;
    // Reconcile checks jobs before clearing any state that names their owner.
    // A failed proof deliberately leaves both the row and stall state intact
    // for the next caller instead of losing the last safe identity.
    clear_abandoned_checks_registry(&tmpdir)?;
    if plan.newly_started && !plan.transaction.present.into_iter().any(|present| present) {
        return Ok(());
    }
    if plan.newly_started {
        write_clear_transaction(&root, plan.transaction)?;
    }
    let mut phase = 0;
    if plan.newly_started {
        after_clear_phase(&mut phase, fault_after_phase)?;
    }
    for (index, entry) in CLEAR_ENTRIES.iter().enumerate() {
        if !plan.transaction.present[index] {
            continue;
        }
        let path = root.path().join(entry.name);
        if entry.state_layer {
            rewrite_clear_state(&root, &path)?;
        } else if inspect_clear_file(&root, &path)?.is_some() {
            remove_clear_artifact(&root, &path)?;
        }
        after_clear_phase(&mut phase, fault_after_phase)?;
    }
    verify_clear_plan(&root, plan.transaction)?;
    remove_clear_transaction(&root)?;
    Ok(())
}

fn after_clear_phase(
    phase: &mut usize,
    fault_after_phase: Option<usize>,
) -> Result<(), StateMutationError> {
    *phase += 1;
    if fault_after_phase == Some(*phase) {
        Err(StateMutationError::Failed)
    } else {
        Ok(())
    }
}

fn preflight_clear(
    root: &TemporaryRoot,
    existing: Option<ClearTransaction>,
) -> Result<ClearPlan, StateMutationError> {
    let mut present = [false; CLEAR_ENTRIES.len()];
    for (index, entry) in CLEAR_ENTRIES.iter().enumerate() {
        let path = root.path().join(entry.name);
        let content = inspect_clear_file(root, &path)?;
        if content.as_ref().is_some_and(|text| !state_syntax_ok(text)) {
            return Err(StateMutationError::Unsafe);
        }
        present[index] = content.is_some();
        if let Some(transaction) = existing {
            if !transaction.present[index] && present[index] {
                return Err(StateMutationError::Failed);
            }
            if transaction.present[index] && entry.state_layer && !present[index] {
                return Err(StateMutationError::Failed);
            }
        }
    }
    let transaction = existing.unwrap_or(ClearTransaction { present });
    Ok(ClearPlan {
        transaction,
        newly_started: existing.is_none(),
    })
}

fn write_clear_transaction(
    root: &TemporaryRoot,
    transaction: ClearTransaction,
) -> Result<(), StateMutationError> {
    let path = root.path().join(CLEAR_TRANSACTION_FILE);
    let mut rows = vec![
        ("CLEAR_STALL_TRANSACTION_VERSION", CLEAR_TRANSACTION_VERSION),
        ("CLEAR_STALL_TRANSACTION_STATE", CLEAR_TRANSACTION_STATE),
    ];
    for (index, entry) in CLEAR_ENTRIES.iter().enumerate() {
        rows.push((
            entry.marker_key,
            if transaction.present[index] {
                "present"
            } else {
                "absent"
            },
        ));
    }
    let text = kv_text(&rows).map_err(|_| StateMutationError::Failed)?;
    atomic_write_utf8_in(root, &path, &text, false, 0o600).map_err(|_| StateMutationError::Failed)
}

fn read_clear_transaction(
    root: &TemporaryRoot,
) -> Result<Option<ClearTransaction>, StateMutationError> {
    let path = root.path().join(CLEAR_TRANSACTION_FILE);
    let Some(text) = inspect_clear_file(root, &path)? else {
        return Ok(None);
    };
    if text.is_empty() || text.lines().any(|line| !line.contains('=')) {
        return Err(StateMutationError::Unsafe);
    }
    let document =
        KvDocument::parse(&text, ParseOptions::legacy()).map_err(|_| StateMutationError::Unsafe)?;
    let mut values = BTreeMap::new();
    for row in document.rows() {
        if values
            .insert(row.key().to_owned(), row.value().to_owned())
            .is_some()
        {
            return Err(StateMutationError::Unsafe);
        }
    }
    if values.len() != CLEAR_ENTRIES.len() + 2
        || values
            .get("CLEAR_STALL_TRANSACTION_VERSION")
            .map(String::as_str)
            != Some(CLEAR_TRANSACTION_VERSION)
        || values
            .get("CLEAR_STALL_TRANSACTION_STATE")
            .map(String::as_str)
            != Some(CLEAR_TRANSACTION_STATE)
    {
        return Err(StateMutationError::Unsafe);
    }
    let mut present = [false; CLEAR_ENTRIES.len()];
    for (index, entry) in CLEAR_ENTRIES.iter().enumerate() {
        match values.get(entry.marker_key).map(String::as_str) {
            Some("present") => present[index] = true,
            Some("absent") => {}
            _ => return Err(StateMutationError::Unsafe),
        }
    }
    Ok(Some(ClearTransaction { present }))
}

fn clear_transaction_pending(root: &TemporaryRoot) -> Result<bool, StateMutationError> {
    Ok(read_clear_transaction(root)?.is_some())
}

fn rewrite_clear_state(root: &TemporaryRoot, path: &Path) -> Result<(), StateMutationError> {
    let Some(text) = inspect_clear_file(root, path)? else {
        return Err(StateMutationError::Failed);
    };
    if !state_syntax_ok(&text) {
        return Err(StateMutationError::Unsafe);
    }
    rewrite_state(root, path, &text, CLEAR_UPDATES)?;
    let rewritten = read_lossy(path).map_err(|()| StateMutationError::Failed)?;
    if !clear_state_is_complete(&rewritten) {
        return Err(StateMutationError::Failed);
    }
    Ok(())
}

fn remove_clear_artifact(root: &TemporaryRoot, path: &Path) -> Result<(), StateMutationError> {
    let Some(text) = inspect_clear_file(root, path)? else {
        return Err(StateMutationError::Failed);
    };
    if !state_syntax_ok(&text) {
        return Err(StateMutationError::Unsafe);
    }
    let confined = root
        .confine(path, PathIntent::Write)
        .map_err(|_| StateMutationError::Unsafe)?;
    confined
        .revalidate()
        .map_err(|_| StateMutationError::Unsafe)?;
    fs::remove_file(confined.path()).map_err(|_| StateMutationError::Failed)?;
    sync_clear_parent(confined.path())
}

fn verify_clear_plan(
    root: &TemporaryRoot,
    transaction: ClearTransaction,
) -> Result<(), StateMutationError> {
    for (index, entry) in CLEAR_ENTRIES.iter().enumerate() {
        let path = root.path().join(entry.name);
        let content = inspect_clear_file(root, &path)?;
        if !transaction.present[index] {
            if content.is_some() {
                return Err(StateMutationError::Failed);
            }
            continue;
        }
        if entry.state_layer {
            let Some(text) = content else {
                return Err(StateMutationError::Failed);
            };
            if !clear_state_is_complete(&text) {
                return Err(StateMutationError::Failed);
            }
        } else if content.is_some() {
            return Err(StateMutationError::Failed);
        }
    }
    Ok(())
}

fn remove_clear_transaction(root: &TemporaryRoot) -> Result<(), StateMutationError> {
    if read_clear_transaction(root)?.is_none() {
        return Err(StateMutationError::Failed);
    }
    let path = root.path().join(CLEAR_TRANSACTION_FILE);
    let confined = root
        .confine(&path, PathIntent::Write)
        .map_err(|_| StateMutationError::Unsafe)?;
    confined
        .revalidate()
        .map_err(|_| StateMutationError::Unsafe)?;
    fs::remove_file(confined.path()).map_err(|_| StateMutationError::Failed)?;
    sync_clear_parent(confined.path())
}

fn clear_state_is_complete(text: &str) -> bool {
    state_syntax_ok(text)
        && read_last_value(text, "STALL_TRACKING") == "false"
        && read_last_value(text, "STALL_STEP").is_empty()
        && read_last_value(text, "BAIL_REASON").is_empty()
        && read_last_value(text, "IMPLEMENT_BAIL_REASON").is_empty()
        && read_last_value(text, "EXIT_CODE") == "unknown"
}

fn sync_clear_parent(path: &Path) -> Result<(), StateMutationError> {
    let parent = path.parent().ok_or(StateMutationError::Failed)?;
    File::open(parent)
        .and_then(|directory| directory.sync_all())
        .map_err(|_| StateMutationError::Failed)
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
    if tmpdir.is_dir() {
        let root = TemporaryRoot::resolve(Some(&tmpdir)).map_err(|_| StateMutationError::Unsafe)?;
        if clear_transaction_pending(&root)? {
            return Err(StateMutationError::Unsafe);
        }
    }
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
    if !tmpdir.is_absolute() || !public_file.is_absolute() || !sensitive_corpus.is_absolute() {
        return false;
    }
    let Ok(root) = TemporaryRoot::resolve(Some(tmpdir)) else {
        return false;
    };
    let Some(public_file) = canonical_root_spelling(&root, tmpdir, public_file) else {
        return false;
    };
    tier_b_public_file_snapshot(&root, &public_file, sensitive_corpus, artifact_prefix).is_some()
}

/// Read one stable public-file snapshot into owned memory.
///
/// Passing a sensitive corpus applies the Tier B policy. Omitting it applies
/// the Tier A redaction policy. The returned bytes have already passed the
/// same bounded, no-follow, identity-checked read used by the descriptor
/// transport boundary.
#[must_use]
pub fn snapshot_public_file_contents(
    source_tmpdir: &Path,
    public_file: &Path,
    sensitive_corpus: Option<&Path>,
    artifact_prefix: &str,
) -> Option<String> {
    approved_public_file_payload(
        source_tmpdir,
        public_file,
        sensitive_corpus,
        artifact_prefix,
    )
    .map(|(payload, _corpus)| payload)
}

/// Validate an in-memory public payload through the shared publication policy.
///
/// File-report assembly uses this after its source slices have already become
/// stable owned snapshots. This keeps Tier B corpus rebuilding and public-text
/// checks identical to `validate-tier-b-public-file --snapshot-fd` without
/// reopening a caller-controlled pathname.
#[must_use]
pub fn validate_public_snapshot_contents(
    source_tmpdir: &Path,
    payload: &str,
    sensitive_corpus: Option<&Path>,
    artifact_prefix: &str,
) -> Option<String> {
    if !source_tmpdir.is_absolute()
        || !artifact_prefix_valid(artifact_prefix)
        || u64::try_from(payload.len()).map_or(true, |length| length > MAX_PUBLIC_FILE_BYTES)
    {
        return None;
    }
    let root = TemporaryRoot::resolve(Some(source_tmpdir)).ok()?;
    match sensitive_corpus {
        None => public_snapshot_is_safe(payload, None).then(|| payload.to_owned()),
        Some(sensitive_corpus) => {
            if !sensitive_corpus.is_absolute() {
                return None;
            }
            let sensitive_corpus = canonical_root_spelling(&root, source_tmpdir, sensitive_corpus)?;
            if !safe_regular_file(&root, &sensitive_corpus, None) {
                return None;
            }
            let corpus =
                build_effective_sensitive_corpus(&root, &sensitive_corpus, artifact_prefix)?;
            let approved = public_snapshot_is_safe(payload, Some(&corpus));
            let _ = fs::remove_file(effective_public_corpus_path(&root, artifact_prefix));
            approved.then(|| payload.to_owned())
        }
    }
}

/// Snapshot one approved public artifact into a caller-owned unlinked Unix file.
///
/// The caller keeps the descriptor open across its transport command. That
/// binds the outbound read to this exact validated inode without reopening a
/// mutable pathname after validation.
#[cfg(unix)]
#[must_use]
pub fn snapshot_public_file_to_fd(
    source_tmpdir: &Path,
    public_file: &Path,
    sensitive_corpus: Option<&Path>,
    artifact_prefix: &str,
    snapshot_fd: i32,
) -> bool {
    let Some((payload, corpus)) = approved_public_file_payload(
        source_tmpdir,
        public_file,
        sensitive_corpus,
        artifact_prefix,
    ) else {
        return false;
    };
    write_public_snapshot_fd(snapshot_fd, &payload, corpus.as_deref())
}

/// Revalidate a caller-owned unlinked public descriptor and stage it into a
/// second inherited descriptor for transport.
///
/// This supports a Tier A body snapshot feeding Tier B corpus validation while
/// keeping marker and title parsing bound to the original immutable descriptor.
#[cfg(unix)]
#[must_use]
pub fn snapshot_public_fd_to_fd(
    source_tmpdir: &Path,
    public_fd: i32,
    sensitive_corpus: Option<&Path>,
    artifact_prefix: &str,
    snapshot_fd: i32,
) -> bool {
    if public_fd == snapshot_fd {
        return false;
    }
    let Some((payload, corpus)) =
        approved_public_fd_payload(source_tmpdir, public_fd, sensitive_corpus, artifact_prefix)
    else {
        return false;
    };
    write_public_snapshot_fd(snapshot_fd, &payload, corpus.as_deref())
}

/// Rewind a caller-owned unlinked public descriptor after a shell reader.
#[cfg(unix)]
#[must_use]
pub fn rewind_public_snapshot_fd(public_fd: i32) -> bool {
    let Some(mut file) = open_public_snapshot_fd(public_fd) else {
        return false;
    };
    file.metadata()
        .is_ok_and(|metadata| metadata.is_file() && metadata.nlink() == 0)
        && file.seek(SeekFrom::Start(0)).is_ok()
}

/// Wrap an approved comment descriptor in the GitHub request JSON envelope.
#[cfg(unix)]
#[must_use]
pub fn compose_public_comment_request_fd(public_fd: i32, snapshot_fd: i32) -> bool {
    if public_fd == snapshot_fd {
        return false;
    }
    let Some(payload) = read_public_snapshot_fd(public_fd) else {
        return false;
    };
    let request = python_json_comment_request(&payload);
    write_verified_unlinked_fd(snapshot_fd, &request, |_| true)
}

fn python_json_comment_request(body: &str) -> String {
    let mut request = String::with_capacity(body.len().saturating_mul(6).saturating_add(12));
    request.push_str("{\"body\": ");
    push_python_json_string(&mut request, body);
    request.push('}');
    request
}

fn push_python_json_string(output: &mut String, value: &str) {
    output.push('"');
    for character in value.chars() {
        match character {
            '"' => output.push_str("\\\""),
            '\\' => output.push_str("\\\\"),
            '\u{0008}' => output.push_str("\\b"),
            '\u{000c}' => output.push_str("\\f"),
            '\n' => output.push_str("\\n"),
            '\r' => output.push_str("\\r"),
            '\t' => output.push_str("\\t"),
            character if character <= '\u{001f}' => {
                push_json_hex_escape(output, character as u16);
            }
            character if character.is_ascii() => output.push(character),
            character => {
                let mut code_units = [0; 2];
                for code_unit in character.encode_utf16(&mut code_units) {
                    push_json_hex_escape(output, *code_unit);
                }
            }
        }
    }
    output.push('"');
}

fn push_json_hex_escape(output: &mut String, value: u16) {
    const HEX: &[u8; 16] = b"0123456789abcdef";
    output.push_str("\\u");
    for shift in [12, 8, 4, 0] {
        output.push(char::from(HEX[usize::from((value >> shift) & 0x000f)]));
    }
}

/// Non-Unix callers cannot safely hand an inherited unlinked descriptor to the
/// shell transport helper.
#[cfg(not(unix))]
#[must_use]
pub fn snapshot_public_file_to_fd(
    _source_tmpdir: &Path,
    _public_file: &Path,
    _sensitive_corpus: Option<&Path>,
    _artifact_prefix: &str,
    _snapshot_fd: i32,
) -> bool {
    false
}

/// Non-Unix callers cannot safely hand an inherited unlinked descriptor to the
/// shell transport helper.
#[cfg(not(unix))]
#[must_use]
pub fn snapshot_public_fd_to_fd(
    _source_tmpdir: &Path,
    _public_fd: i32,
    _sensitive_corpus: Option<&Path>,
    _artifact_prefix: &str,
    _snapshot_fd: i32,
) -> bool {
    false
}

/// Non-Unix callers cannot safely seek an inherited unlinked descriptor.
#[cfg(not(unix))]
#[must_use]
pub fn rewind_public_snapshot_fd(_public_fd: i32) -> bool {
    false
}

/// Non-Unix callers cannot safely compose into an inherited descriptor.
#[cfg(not(unix))]
#[must_use]
pub fn compose_public_comment_request_fd(_public_fd: i32, _snapshot_fd: i32) -> bool {
    false
}

fn approved_public_file_payload(
    source_tmpdir: &Path,
    public_file: &Path,
    sensitive_corpus: Option<&Path>,
    artifact_prefix: &str,
) -> Option<(String, Option<String>)> {
    if !source_tmpdir.is_absolute()
        || !public_file.is_absolute()
        || !artifact_prefix_valid(artifact_prefix)
    {
        return None;
    }
    let source_root = TemporaryRoot::resolve(Some(source_tmpdir)).ok()?;
    let public_file = canonical_root_spelling(&source_root, source_tmpdir, public_file)?;
    sensitive_corpus.map_or_else(
        || tier_a_public_file_snapshot(&source_root, &public_file).map(|payload| (payload, None)),
        |corpus| {
            tier_b_public_file_snapshot(&source_root, &public_file, corpus, artifact_prefix)
                .map(|(payload, corpus)| (payload, Some(corpus)))
        },
    )
}

#[cfg(unix)]
fn approved_public_fd_payload(
    source_tmpdir: &Path,
    public_fd: i32,
    sensitive_corpus: Option<&Path>,
    artifact_prefix: &str,
) -> Option<(String, Option<String>)> {
    if !source_tmpdir.is_absolute() || !artifact_prefix_valid(artifact_prefix) {
        return None;
    }
    let source_root = TemporaryRoot::resolve(Some(source_tmpdir)).ok()?;
    let payload = read_public_snapshot_fd(public_fd)?;
    match sensitive_corpus {
        None => public_snapshot_is_safe(&payload, None).then_some((payload, None)),
        Some(sensitive_corpus) => tier_b_public_fd_snapshot(
            &source_root,
            source_tmpdir,
            &payload,
            sensitive_corpus,
            artifact_prefix,
        )
        .map(|corpus| (payload, Some(corpus))),
    }
}

#[cfg(unix)]
fn write_public_snapshot_fd(snapshot_fd: i32, payload: &str, corpus: Option<&str>) -> bool {
    if u64::try_from(payload.len()).map_or(true, |length| length > MAX_PUBLIC_FILE_BYTES) {
        return false;
    }
    write_verified_unlinked_fd(snapshot_fd, payload, |written| {
        public_snapshot_is_safe(written, corpus)
    })
}

#[cfg(unix)]
fn write_verified_unlinked_fd(
    snapshot_fd: i32,
    payload: &str,
    approve: impl FnOnce(&str) -> bool,
) -> bool {
    let Some(mut file) = open_public_snapshot_fd(snapshot_fd) else {
        return false;
    };
    let Ok(expected_len) = u64::try_from(payload.len()) else {
        return false;
    };
    let Ok(metadata) = file.metadata() else {
        return false;
    };
    if !metadata.is_file() || metadata.nlink() != 0 {
        return false;
    }
    if file
        .set_permissions(fs::Permissions::from_mode(0o600))
        .is_err()
        || file.set_len(0).is_err()
        || file.seek(SeekFrom::Start(0)).is_err()
        || file.write_all(payload.as_bytes()).is_err()
        || file.flush().is_err()
        || file.sync_all().is_err()
        || file.seek(SeekFrom::Start(0)).is_err()
    {
        return false;
    }
    let Ok(before_read) = file.metadata() else {
        return false;
    };
    if !before_read.is_file()
        || before_read.nlink() != 0
        || before_read.len() != u64::try_from(payload.len()).unwrap_or(u64::MAX)
    {
        return false;
    }
    let mut bytes = Vec::with_capacity(payload.len());
    if Read::by_ref(&mut file)
        .take(expected_len.saturating_add(1))
        .read_to_end(&mut bytes)
        .is_err()
    {
        return false;
    }
    let Ok(after_read) = file.metadata() else {
        return false;
    };
    if !same_public_file_snapshot(&before_read, &after_read) || after_read.nlink() != 0 {
        return false;
    }
    let approved =
        String::from_utf8(bytes).is_ok_and(|written| written == payload && approve(&written));
    let _ = file.seek(SeekFrom::Start(0));
    approved
}

#[cfg(unix)]
fn tier_b_public_fd_snapshot(
    root: &TemporaryRoot,
    tmpdir: &Path,
    payload: &str,
    sensitive_corpus: &Path,
    artifact_prefix: &str,
) -> Option<String> {
    if !sensitive_corpus.is_absolute() {
        return None;
    }
    let sensitive_corpus = canonical_root_spelling(root, tmpdir, sensitive_corpus)?;
    if !safe_regular_file(root, &sensitive_corpus, None) {
        return None;
    }
    let corpus = build_effective_sensitive_corpus(root, &sensitive_corpus, artifact_prefix)?;
    if !public_snapshot_is_safe(payload, Some(&corpus)) {
        return None;
    }
    let effective = effective_public_corpus_path(root, artifact_prefix);
    let _ = fs::remove_file(effective);
    Some(corpus)
}

#[cfg(unix)]
fn read_public_snapshot_fd(snapshot_fd: i32) -> Option<String> {
    let mut file = open_public_snapshot_fd(snapshot_fd)?;
    let before = file.metadata().ok()?;
    if !before.is_file() || before.nlink() != 0 || before.len() > MAX_PUBLIC_FILE_BYTES {
        return None;
    }
    file.seek(SeekFrom::Start(0)).ok()?;
    let mut bytes = Vec::with_capacity(usize::try_from(before.len()).ok()?);
    Read::by_ref(&mut file)
        .take(MAX_PUBLIC_FILE_BYTES + 1)
        .read_to_end(&mut bytes)
        .ok()?;
    let after = file.metadata().ok()?;
    if !same_public_file_snapshot(&before, &after)
        || after.nlink() != 0
        || u64::try_from(bytes.len()).ok() != Some(before.len())
    {
        return None;
    }
    file.seek(SeekFrom::Start(0)).ok()?;
    String::from_utf8(bytes).ok()
}

#[cfg(unix)]
fn open_public_snapshot_fd(snapshot_fd: i32) -> Option<File> {
    (snapshot_fd >= 3)
        .then(|| PathBuf::from(format!("/dev/fd/{snapshot_fd}")))
        .and_then(|path| OpenOptions::new().read(true).write(true).open(path).ok())
}

fn tier_a_public_file_snapshot(root: &TemporaryRoot, public_file: &Path) -> Option<String> {
    let payload = bounded_public_file_snapshot(root, public_file)?;
    public_snapshot_is_safe(&payload, None).then_some(payload)
}

fn tier_b_public_file_snapshot(
    root: &TemporaryRoot,
    public_file: &Path,
    sensitive_corpus: &Path,
    artifact_prefix: &str,
) -> Option<(String, String)> {
    if !public_file.is_absolute()
        || !sensitive_corpus.is_absolute()
        || !artifact_prefix_valid(artifact_prefix)
    {
        return None;
    }
    let sensitive_corpus = canonical_root_spelling(root, root.path(), sensitive_corpus)?;
    if !safe_regular_file(root, &sensitive_corpus, None) {
        return None;
    }
    let corpus = build_effective_sensitive_corpus(root, &sensitive_corpus, artifact_prefix)?;
    let payload = bounded_public_file_snapshot(root, public_file)?;
    if !public_snapshot_is_safe(&payload, Some(&corpus)) {
        return None;
    }
    let effective = effective_public_corpus_path(root, artifact_prefix);
    let _ = fs::remove_file(effective);
    Some((payload, corpus))
}

fn build_effective_sensitive_corpus(
    root: &TemporaryRoot,
    sensitive_corpus: &Path,
    artifact_prefix: &str,
) -> Option<String> {
    let effective = effective_public_corpus_path(root, artifact_prefix);
    let corpus = build_sensitive_corpus(root, sensitive_corpus, artifact_prefix);
    atomic_write_utf8_in(root, &effective, &corpus, false, 0o600).ok()?;
    Some(corpus)
}

fn effective_public_corpus_path(root: &TemporaryRoot, artifact_prefix: &str) -> PathBuf {
    root.path().join(format!(
        "{}-sensitive-corpus.public.effective",
        if artifact_prefix.is_empty() {
            "stall-recovery"
        } else {
            artifact_prefix
        }
    ))
}

fn public_snapshot_is_safe(payload: &str, corpus: Option<&str>) -> bool {
    redact(payload).findings().is_empty()
        && corpus.is_none_or(|corpus| !public_text_is_sensitive(corpus, payload))
}

fn bounded_public_file_snapshot(root: &TemporaryRoot, path: &Path) -> Option<String> {
    bounded_public_file_snapshot_after_open(root, path, |_| {})
}

fn bounded_public_file_snapshot_after_open(
    root: &TemporaryRoot,
    path: &Path,
    after_open: impl FnOnce(&Path),
) -> Option<String> {
    let confined = root.confine(path, PathIntent::Read).ok()?;
    confined.revalidate().ok()?;
    let before = fs::symlink_metadata(confined.path()).ok()?;
    if before.file_type().is_symlink() || !before.is_file() || before.len() > MAX_PUBLIC_FILE_BYTES
    {
        return None;
    }
    let mut options = OpenOptions::new();
    options.read(true);
    #[cfg(unix)]
    options.custom_flags(nix::libc::O_NOFOLLOW);
    let mut file = options.open(confined.path()).ok()?;
    let opened = file.metadata().ok()?;
    if confined.revalidate().is_err() || !same_public_file_snapshot(&before, &opened) {
        return None;
    }
    after_open(confined.path());
    let capacity = usize::try_from(before.len()).ok()?;
    let mut bytes = Vec::with_capacity(capacity);
    Read::by_ref(&mut file)
        .take(MAX_PUBLIC_FILE_BYTES + 1)
        .read_to_end(&mut bytes)
        .ok()?;
    let opened_after = file.metadata().ok()?;
    let visible_after = fs::symlink_metadata(confined.path()).ok()?;
    if confined.revalidate().is_err()
        || !same_public_file_snapshot(&before, &opened_after)
        || !same_public_file_snapshot(&before, &visible_after)
        || u64::try_from(bytes.len()).ok() != Some(before.len())
    {
        return None;
    }
    String::from_utf8(bytes).ok()
}

#[cfg(unix)]
fn same_public_file_snapshot(before: &fs::Metadata, after: &fs::Metadata) -> bool {
    before.dev() == after.dev()
        && before.ino() == after.ino()
        && before.len() == after.len()
        && before.mtime() == after.mtime()
        && before.mtime_nsec() == after.mtime_nsec()
        && before.ctime() == after.ctime()
        && before.ctime_nsec() == after.ctime_nsec()
}

#[cfg(not(unix))]
fn same_public_file_snapshot(before: &fs::Metadata, after: &fs::Metadata) -> bool {
    before.len() == after.len() && before.modified().ok() == after.modified().ok()
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

/// Preflight one fixed clear target through the temporary-root write boundary.
///
/// A clear will later replace or remove the target, so read-only inspection is
/// not sufficient: reject a hard-linked, symlinked, or otherwise unsafe leaf
/// before the transaction marker makes any destructive phase reachable.
fn inspect_clear_file(
    root: &TemporaryRoot,
    path: &Path,
) -> Result<Option<String>, StateMutationError> {
    root.confine(path, PathIntent::Write)
        .map_err(|_| StateMutationError::Unsafe)?;
    inspect_state(path)
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

fn clear_abandoned_checks_registry(tmpdir: &Path) -> Result<(), StateMutationError> {
    let host = SystemProcessIdentityHost::new();
    for (path, entry, _) in abandoned_checks_registry_rows(tmpdir, &host) {
        match recover_abandoned_entry(&host, &path, &entry, "stall-clear", "clear-stall") {
            BgjobRecoveryOutcome::Recovered | BgjobRecoveryOutcome::Gone => {}
            // A live daemon, concurrent claimant, or failed verification is
            // not permission to erase a row or clear the state that points to
            // it. The next clear-stall invocation can retry the same claim.
            BgjobRecoveryOutcome::Busy | BgjobRecoveryOutcome::Failed(_) => {
                return Err(StateMutationError::Failed);
            }
        }
    }
    Ok(())
}

/// Return the first abandoned checks step using the shared Rust bgjob registry.
#[must_use]
pub fn abandoned_checks_stall_step(tmpdir: &Path) -> Option<&'static str> {
    let host = SystemProcessIdentityHost::new();
    abandoned_checks_registry_rows(tmpdir, &host)
        .into_iter()
        .next()
        .map(|(_, _, step)| step)
}

fn abandoned_checks_registry_rows(
    tmpdir: &Path,
    host: &SystemProcessIdentityHost,
) -> Vec<(PathBuf, RegistryEntry, &'static str)> {
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
            abandoned.push((path, entry, stall_step));
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

fn attempt_lock_path(path: &Path) -> Result<PathBuf, StallRecoveryError> {
    let Some(parent) = path.parent() else {
        return Err(StallRecoveryError::Diagnostic(
            "--attempts-file outside implement tmpdir",
        ));
    };
    Ok(parent.join(ATTEMPT_LEDGER_LOCK_FILE))
}

/// Serialize read-modify-replace against a stable companion inode.
///
/// Locking the ledger itself would not cover a subsequent atomic replacement,
/// because waiting callers could retain the old inode. The companion remains a
/// private non-wire file until session cleanup so every caller locks one inode.
fn lock_attempt_ledger(
    root: &TemporaryRoot,
    attempts: &Path,
) -> Result<AttemptLedgerLock, StallRecoveryError> {
    let lock_path = attempt_lock_path(attempts)?;
    let parent = lock_path.parent().ok_or(StallRecoveryError::Diagnostic(
        "--attempts-file outside implement tmpdir",
    ))?;
    root.ensure_directory(parent)
        .map_err(|_| StallRecoveryError::Unsafe)?;
    let lock = lock_private_file(root, &lock_path).map_err(|error| {
        if error.is_lock_failure() {
            StallRecoveryError::Failed
        } else {
            StallRecoveryError::Unsafe
        }
    })?;
    Ok(AttemptLedgerLock { _lock: lock })
}

fn attempt_ledger_syntax_ok(path: &Path) -> Result<bool, StallRecoveryError> {
    let text = read_lossy(path).map_err(|()| StallRecoveryError::Failed)?;
    Ok(state_syntax_ok(&text))
}

fn attempt_record_is_visible(path: &Path, count: &str, request: &AttemptRecord) -> bool {
    let Ok(text) = read_lossy(path) else {
        return false;
    };
    state_syntax_ok(&text)
        && read_last_value(&text, "attempt_count") == count
        && read_last_value(&text, &format!("attempt.{count}.class")) == request.failure_class
        && read_last_value(&text, &format!("attempt.{count}.signature")) == request.signature
        && read_last_value(&text, &format!("attempt.{count}.resume_hint")) == request.resume_hint
        && read_last_value(&text, &format!("attempt.{count}.outcome")) == request.outcome
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
    #[cfg(unix)]
    use super::MAX_PUBLIC_FILE_BYTES;
    use super::{
        AttemptRecord, ClassificationRequest, EscalationError, EscalationOutput, EscalationRequest,
        FailureDetailLogError, MAX_DETAIL_FILE_BYTES, MAX_DETAIL_FILE_BYTES_USIZE,
        StallRecoveryError, StateMutationError, classify, classify_failure_detail_log, clear_stall,
        clear_stall_inner, compose_public_comment_request_fd, file_failure_comment_url,
        find_open_stall_issue, init_attempts, is_larch_dev_clone,
        latest_failure_detail_log_sidecar, materialize_truncated_failure_detail_log,
        normalize_outcome, python_json_comment_request,
        read_failure_detail_log_with_sidecar_fallback, read_validated_failure_detail_log,
        record_attempt, record_escalation, rewind_public_snapshot_fd, seed_terminal_state,
        snapshot_public_fd_to_fd, snapshot_public_file_to_fd, terminal_state_is_valid,
    };
    use crate::TemporaryRoot;
    #[cfg(unix)]
    use std::os::fd::AsRawFd as _;
    use std::{
        fs,
        io::{Read as _, Seek as _, SeekFrom, Write as _},
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

    fn clear_fixture(tmpdir: &Path) {
        for (index, name) in ["ship-pr-state.sh", "finalize-state.sh", "session-env.sh"]
            .into_iter()
            .enumerate()
        {
            fs::write(
                tmpdir.join(name),
                format!(
                    "KEEP_{index}=yes\nSTALL_TRACKING=true\nSTALL_STEP=8\nBAIL_REASON=review-required\nIMPLEMENT_BAIL_REASON=review-required\nEXIT_CODE=4\n"
                ),
            )
            .expect("state fixture");
        }
        fs::write(
            tmpdir.join("stall-recovery-classification.env"),
            "FAILURE_CLASS=test-failure\nRESUME_HINT=step2-impl\n",
        )
        .expect("classification fixture");
        fs::write(
            tmpdir.join("stall-recovery-issue.env"),
            "ISSUE_NUMBER=42\nISSUE_URL=https://github.com/o/r/issues/42\n",
        )
        .expect("issue fixture");
    }

    fn classification_request(tmpdir: &Path) -> ClassificationRequest {
        ClassificationRequest {
            tmpdir: tmpdir.to_path_buf(),
            ..ClassificationRequest::default()
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
        let classification = temp.path().join("stall-recovery-classification.env");
        let issue = temp.path().join("stall-recovery-issue.env");
        fs::write(&classification, "FAILURE_CLASS=test-failure\n").expect("classification");
        fs::write(&issue, "ISSUE_NUMBER=42\n").expect("issue");
        assert_eq!(clear_stall(temp.path()), Err(StateMutationError::Unsafe));
        assert_eq!(
            fs::read_to_string(state).expect("unchanged"),
            "STALL_TRACKING=true\npartial\n"
        );
        assert_eq!(
            fs::read_to_string(classification).expect("classification unchanged"),
            "FAILURE_CLASS=test-failure\n"
        );
        assert_eq!(
            fs::read_to_string(issue).expect("issue unchanged"),
            "ISSUE_NUMBER=42\n"
        );
        assert!(
            !temp.path().join(super::CLEAR_TRANSACTION_FILE).exists(),
            "preflight must not publish a transaction marker"
        );
    }

    #[test]
    fn malformed_derived_artifact_fails_before_any_clear_mutation() {
        let temp = tempfile::tempdir().expect("tempdir");
        clear_fixture(temp.path());
        let classification = temp.path().join("stall-recovery-classification.env");
        fs::write(&classification, "FAILURE_CLASS=test-failure\npartial\n")
            .expect("malformed classification");
        let before = [
            "ship-pr-state.sh",
            "finalize-state.sh",
            "session-env.sh",
            "stall-recovery-classification.env",
            "stall-recovery-issue.env",
        ]
        .into_iter()
        .map(|name| {
            (
                name,
                fs::read_to_string(temp.path().join(name)).expect("before"),
            )
        })
        .collect::<Vec<_>>();

        assert_eq!(clear_stall(temp.path()), Err(StateMutationError::Unsafe));

        for (name, contents) in before {
            assert_eq!(
                fs::read_to_string(temp.path().join(name)).expect("unchanged artifact"),
                contents,
                "preflight mutated {name}"
            );
        }
        assert!(!temp.path().join(super::CLEAR_TRANSACTION_FILE).exists());
    }

    #[cfg(unix)]
    #[test]
    fn hardlinked_clear_artifact_fails_during_preflight() {
        let temp = tempfile::tempdir().expect("tempdir");
        clear_fixture(temp.path());
        let classification = temp.path().join("stall-recovery-classification.env");
        let alias = temp.path().join("classification-alias.env");
        fs::hard_link(&classification, &alias).expect("hard link fixture");
        let state = fs::read_to_string(temp.path().join("ship-pr-state.sh")).expect("state");

        assert_eq!(clear_stall(temp.path()), Err(StateMutationError::Unsafe));

        assert_eq!(
            fs::read_to_string(temp.path().join("ship-pr-state.sh")).expect("state unchanged"),
            state
        );
        assert!(classification.exists());
        assert_eq!(
            fs::read_to_string(&alias).expect("hard-link target unchanged"),
            "FAILURE_CLASS=test-failure\nRESUME_HINT=step2-impl\n"
        );
        assert!(!temp.path().join(super::CLEAR_TRANSACTION_FILE).exists());
    }

    #[test]
    fn interrupted_clear_phases_stay_pending_then_retry_to_one_completed_state() {
        const PHASES: usize = super::CLEAR_ENTRIES.len() + 1;

        for phase in 1..=PHASES {
            let temp = tempfile::tempdir().expect("tempdir");
            clear_fixture(temp.path());

            assert_eq!(
                clear_stall_inner(temp.path(), Some(phase)),
                Err(StateMutationError::Failed),
                "injected phase {phase}"
            );
            assert!(
                temp.path().join(super::CLEAR_TRANSACTION_FILE).is_file(),
                "phase {phase} did not leave a recognizable transaction"
            );
            assert_eq!(
                normalize_outcome(temp.path(), "false"),
                Err(StallRecoveryError::Unsafe),
                "phase {phase} normalized a partial clear as completed"
            );
            assert_eq!(
                classify(&classification_request(temp.path())),
                Err(StallRecoveryError::UnsafeDiagnostic(
                    "stall clear transaction pending"
                )),
                "phase {phase} classified a partial clear as completed"
            );
            let mut generic = classification_request(temp.path());
            generic.profile = "generic".to_owned();
            assert_eq!(
                classify(&generic),
                Err(StallRecoveryError::UnsafeDiagnostic(
                    "stall clear transaction pending"
                )),
                "phase {phase} let generic classification bypass its pending marker"
            );
            assert_eq!(
                seed_terminal_state(temp.path(), "8", "ci-initial"),
                Err(StateMutationError::Unsafe),
                "phase {phase} allowed a state writer through its pending marker"
            );

            clear_stall(temp.path()).expect("retry clear");
            assert!(
                !temp.path().join(super::CLEAR_TRANSACTION_FILE).exists(),
                "successful retry retained its transaction marker"
            );
            for (index, name) in ["ship-pr-state.sh", "finalize-state.sh", "session-env.sh"]
                .into_iter()
                .enumerate()
            {
                let state = fs::read_to_string(temp.path().join(name)).expect("cleared state");
                assert!(state.contains(&format!("KEEP_{index}=yes\n")));
                assert_eq!(super::read_last_value(&state, "STALL_TRACKING"), "false");
                assert!(super::read_last_value(&state, "STALL_STEP").is_empty());
                assert!(super::read_last_value(&state, "BAIL_REASON").is_empty());
                assert!(super::read_last_value(&state, "IMPLEMENT_BAIL_REASON").is_empty());
                assert_eq!(super::read_last_value(&state, "EXIT_CODE"), "unknown");
            }
            assert!(
                !temp
                    .path()
                    .join("stall-recovery-classification.env")
                    .exists()
            );
            assert!(!temp.path().join("stall-recovery-issue.env").exists());
        }
    }

    #[test]
    fn concurrent_attempt_records_receive_contiguous_distinct_numbers() {
        let temp = tempfile::tempdir().expect("tempdir");
        let root = temp.path().to_path_buf();
        let attempts = root.join("stall-recovery-attempts.env");
        let handles: [_; 32] = std::array::from_fn(|index| {
            let tmpdir = root.clone();
            let attempts_file = attempts.clone();
            thread::spawn(move || {
                record_attempt(&AttemptRecord {
                    tmpdir,
                    attempts_file,
                    failure_class: "test-failure".to_owned(),
                    signature: format!("signature-{index}"),
                    resume_hint: "step2-impl".to_owned(),
                    outcome: "failed".to_owned(),
                })
            })
        });
        let mut counts = handles
            .into_iter()
            .map(|handle| {
                handle
                    .join()
                    .expect("writer thread")
                    .expect("serialized append")
                    .parse::<usize>()
                    .expect("numeric attempt count")
            })
            .collect::<Vec<_>>();
        counts.sort_unstable();
        assert_eq!(counts, (1..=32).collect::<Vec<_>>());

        let text = fs::read_to_string(&attempts).expect("attempt ledger");
        assert!(
            super::state_syntax_ok(&text),
            "ledger must remain parseable"
        );
        assert_eq!(super::read_last_value(&text, "attempt_count"), "32");
        for number in 1..=32 {
            assert!(
                !super::read_last_value(&text, &format!("attempt.{number}.signature")).is_empty(),
                "missing recorded attempt {number}"
            );
        }
        assert_eq!(
            init_attempts(temp.path(), &attempts)
                .expect("readback after concurrent writes")
                .1,
            "32"
        );
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt as _;

            assert_eq!(
                fs::metadata(&attempts)
                    .expect("ledger mode")
                    .permissions()
                    .mode()
                    & 0o077,
                0
            );
            assert_eq!(
                fs::metadata(temp.path().join(super::ATTEMPT_LEDGER_LOCK_FILE))
                    .expect("stable lock mode")
                    .permissions()
                    .mode()
                    & 0o077,
                0
            );
        }
    }

    #[test]
    fn outer_classifier_tables_list_every_branch_once() {
        let implement = super::IMPLEMENT_CLASSIFICATION_TABLE
            .iter()
            .map(|rule| rule.branch)
            .collect::<Vec<_>>();
        assert_eq!(
            implement,
            vec![
                super::ImplementClassificationBranch::AbandonedChecks,
                super::ImplementClassificationBranch::NoStall,
                super::ImplementClassificationBranch::PostmergeFailure,
                super::ImplementClassificationBranch::ExpectedPostmerge,
                super::ImplementClassificationBranch::Text,
            ]
        );
        assert_eq!(
            super::implement_classification_branch(super::ImplementClassificationDecision {
                abandoned: true,
                stalled: false,
                postmerge: super::PostmergeClassification::None,
            }),
            super::ImplementClassificationBranch::AbandonedChecks
        );
        assert_eq!(
            super::implement_classification_branch(super::ImplementClassificationDecision {
                abandoned: false,
                stalled: false,
                postmerge: super::PostmergeClassification::None,
            }),
            super::ImplementClassificationBranch::NoStall
        );
        assert_eq!(
            super::implement_classification_branch(super::ImplementClassificationDecision {
                abandoned: false,
                stalled: true,
                postmerge: super::PostmergeClassification::Failure,
            }),
            super::ImplementClassificationBranch::PostmergeFailure
        );
        assert_eq!(
            super::implement_classification_branch(super::ImplementClassificationDecision {
                abandoned: false,
                stalled: true,
                postmerge: super::PostmergeClassification::Expected,
            }),
            super::ImplementClassificationBranch::ExpectedPostmerge
        );
        assert_eq!(
            super::implement_classification_branch(super::ImplementClassificationDecision {
                abandoned: false,
                stalled: true,
                postmerge: super::PostmergeClassification::None,
            }),
            super::ImplementClassificationBranch::Text
        );

        let generic = super::GENERIC_CLASSIFICATION_TABLE
            .iter()
            .map(|rule| rule.branch)
            .collect::<Vec<_>>();
        assert_eq!(
            generic,
            vec![
                super::GenericClassificationBranch::CurrentPublish,
                super::GenericClassificationBranch::Text,
            ]
        );
        assert_eq!(
            super::generic_classification_branch(true),
            super::GenericClassificationBranch::CurrentPublish
        );
        assert_eq!(
            super::generic_classification_branch(false),
            super::GenericClassificationBranch::Text
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

    #[cfg(unix)]
    #[test]
    fn public_snapshot_keeps_the_approved_tier_b_bytes_after_source_mutation() {
        let source = tempfile::tempdir().expect("source tempdir");
        let transport = tempfile::NamedTempFile::new_in(source.path()).expect("transport file");
        let public = source.path().join("public.md");
        let corpus = source.path().join("stall-recovery-sensitive-corpus.env");
        fs::write(&public, "approved report\n").expect("public fixture");
        fs::write(&corpus, "late-public-secret\n").expect("corpus fixture");
        fs::remove_file(transport.path()).expect("unlink transport file");

        assert!(snapshot_public_file_to_fd(
            source.path(),
            &public,
            Some(&corpus),
            "",
            transport.as_raw_fd(),
        ));
        fs::write(&public, "late-public-secret\n").expect("mutated source");

        let mut captured = transport
            .as_file()
            .try_clone()
            .expect("transport duplicate");
        captured.seek(SeekFrom::Start(0)).expect("rewind transport");
        let mut captured_text = String::new();
        captured
            .read_to_string(&mut captured_text)
            .expect("read transport");
        assert_eq!(captured_text, "approved report\n");
    }

    #[cfg(unix)]
    #[test]
    fn public_snapshot_transport_fd_keeps_the_approved_tier_b_bytes() {
        let source = tempfile::tempdir().expect("source tempdir");
        let stage = tempfile::NamedTempFile::new_in(source.path()).expect("stage file");
        let transport = tempfile::NamedTempFile::new_in(source.path()).expect("transport file");
        let public = source.path().join("public.md");
        let corpus = source.path().join("stall-recovery-sensitive-corpus.env");
        fs::write(&public, "approved report\n").expect("public fixture");
        fs::write(&corpus, "late-public-secret\n").expect("corpus fixture");
        fs::remove_file(stage.path()).expect("unlink stage file");
        fs::remove_file(transport.path()).expect("unlink transport file");

        assert!(snapshot_public_file_to_fd(
            source.path(),
            &public,
            None,
            "",
            stage.as_raw_fd(),
        ));
        assert!(!snapshot_public_fd_to_fd(
            source.path(),
            stage.as_raw_fd(),
            None,
            "",
            stage.as_raw_fd(),
        ));
        assert!(snapshot_public_fd_to_fd(
            source.path(),
            stage.as_raw_fd(),
            Some(&corpus),
            "",
            transport.as_raw_fd(),
        ));
        fs::write(&public, "late-public-secret\n").expect("mutated source");

        let mut captured = transport
            .as_file()
            .try_clone()
            .expect("transport duplicate");
        captured.seek(SeekFrom::Start(0)).expect("rewind transport");
        let mut captured_text = String::new();
        captured
            .read_to_string(&mut captured_text)
            .expect("read transport");
        assert_eq!(captured_text, "approved report\n");
    }

    #[cfg(unix)]
    #[test]
    fn public_comment_request_rewinds_and_wraps_approved_bytes() {
        let temporary = tempfile::tempdir().expect("tempdir");
        let mut public = tempfile::NamedTempFile::new_in(temporary.path()).expect("public file");
        let request = tempfile::NamedTempFile::new_in(temporary.path()).expect("request file");
        let payload = "approved \"comment\" \\ ☃ 😀\t\n";
        public
            .write_all(payload.as_bytes())
            .expect("write public comment");
        assert!(!rewind_public_snapshot_fd(public.as_raw_fd()));
        assert!(!compose_public_comment_request_fd(
            public.as_raw_fd(),
            request.as_raw_fd(),
        ));
        fs::remove_file(public.path()).expect("unlink public file");
        fs::remove_file(request.path()).expect("unlink request file");
        public
            .seek(SeekFrom::End(0))
            .expect("position public descriptor at end");

        assert!(rewind_public_snapshot_fd(public.as_raw_fd()));
        assert!(compose_public_comment_request_fd(
            public.as_raw_fd(),
            request.as_raw_fd(),
        ));
        assert!(!compose_public_comment_request_fd(
            public.as_raw_fd(),
            public.as_raw_fd(),
        ));

        let mut captured = request.as_file().try_clone().expect("request duplicate");
        captured.seek(SeekFrom::Start(0)).expect("rewind request");
        let mut request_text = String::new();
        captured
            .read_to_string(&mut request_text)
            .expect("read request");
        assert_eq!(
            request_text,
            r#"{"body": "approved \"comment\" \\ \u2603 \ud83d\ude00\t\n"}"#
        );
    }

    #[test]
    fn comment_request_matches_legacy_python_json_dump_wire() {
        assert_eq!(
            python_json_comment_request("\u{0000}\u{0001}\u{0008}\u{000c}\n\r\t\"\\é"),
            r#"{"body": "\u0000\u0001\b\f\n\r\t\"\\\u00e9"}"#
        );
    }

    #[cfg(unix)]
    #[test]
    fn comment_request_preserves_legacy_escape_expansion_above_public_input_limit() {
        let temporary = tempfile::tempdir().expect("tempdir");
        let mut public = tempfile::NamedTempFile::new_in(temporary.path()).expect("public file");
        let request = tempfile::NamedTempFile::new_in(temporary.path()).expect("request file");
        let payload = "é"
            .repeat(usize::try_from(MAX_PUBLIC_FILE_BYTES / 2).expect("fixture length fits usize"));
        public
            .write_all(payload.as_bytes())
            .expect("write public comment");
        fs::remove_file(public.path()).expect("unlink public file");
        fs::remove_file(request.path()).expect("unlink request file");

        assert!(compose_public_comment_request_fd(
            public.as_raw_fd(),
            request.as_raw_fd(),
        ));
        assert!(
            request
                .as_file()
                .metadata()
                .expect("request metadata")
                .len()
                > MAX_PUBLIC_FILE_BYTES
        );
    }

    #[test]
    fn file_failure_helpers_validate_comment_urls_and_find_issue_markers() {
        let temporary = tempfile::tempdir().expect("tempdir");
        let response = temporary.path().join("response.json");
        let issues = temporary.path().join("issues.jsonl");
        let marker = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";
        fs::write(
            &response,
            r#"{"html_url":"https://github.com/owner/repo/issues/7#issuecomment-99"}"#,
        )
        .expect("comment response");
        fs::write(
            &issues,
            format!(
                concat!(
                    "{{\"number\":3,\"body\":\"<!-- larch-stall:signature={marker} -->\",\"pull_request\":{{}}}}\n",
                    "{{\"number\":7,\"body\":\"contains <!-- larch-stall:signature={marker} -->\",\"pull_request\":null}}\n"
                ),
                marker = marker,
            ),
        )
        .expect("issue response");

        assert_eq!(
            file_failure_comment_url(temporary.path(), &response),
            Ok("https://github.com/owner/repo/issues/7#issuecomment-99".to_owned())
        );
        assert_eq!(
            find_open_stall_issue(temporary.path(), &issues, marker),
            Ok(Some("7".to_owned()))
        );

        fs::write(
            &issues,
            format!("{{\"number\":null,\"body\":\"<!-- larch-stall:signature={marker} -->\"}}\n"),
        )
        .expect("empty issue number response");
        assert_eq!(
            find_open_stall_issue(temporary.path(), &issues, marker),
            Ok(Some(String::new()))
        );

        fs::write(
            &response,
            r#"{"html_url":"https://example.test/not-github"}"#,
        )
        .expect("invalid comment response");
        fs::write(&issues, "not json\n").expect("invalid issue response");
        assert_eq!(
            file_failure_comment_url(temporary.path(), &response),
            Ok(String::new())
        );
        assert_eq!(
            find_open_stall_issue(temporary.path(), &issues, marker),
            Ok(None)
        );
    }

    #[cfg(unix)]
    #[test]
    fn public_snapshot_refuses_a_source_symlink() {
        let temporary = tempfile::tempdir().expect("tempdir");
        let target = temporary.path().join("target.md");
        let public = temporary.path().join("public.md");
        let transport = tempfile::NamedTempFile::new_in(temporary.path()).expect("transport file");
        fs::write(&target, "approved report\n").expect("target fixture");
        std::os::unix::fs::symlink(&target, &public).expect("source symlink");
        fs::remove_file(transport.path()).expect("unlink transport file");

        assert!(!snapshot_public_file_to_fd(
            temporary.path(),
            &public,
            None,
            "",
            transport.as_raw_fd(),
        ));
    }

    #[cfg(unix)]
    #[test]
    fn public_snapshot_refuses_an_oversized_source() {
        let temporary = tempfile::tempdir().expect("tempdir");
        let public = temporary.path().join("public.md");
        let transport = tempfile::NamedTempFile::new_in(temporary.path()).expect("transport file");
        let oversized_len =
            usize::try_from(MAX_PUBLIC_FILE_BYTES + 1).expect("fixture length fits usize");
        fs::write(&public, vec![b'x'; oversized_len]).expect("oversized public fixture");
        fs::remove_file(transport.path()).expect("unlink transport file");

        assert!(!snapshot_public_file_to_fd(
            temporary.path(),
            &public,
            None,
            "",
            transport.as_raw_fd(),
        ));
    }

    #[test]
    fn public_snapshot_refuses_growth_after_open() {
        let temporary = tempfile::tempdir().expect("tempdir");
        let root = TemporaryRoot::resolve(Some(temporary.path())).expect("snapshot root");
        let public = root.path().join("public.md");
        fs::write(&public, "approved report\n").expect("public fixture");

        assert!(
            super::bounded_public_file_snapshot_after_open(&root, &public, |path| {
                fs::OpenOptions::new()
                    .append(true)
                    .open(path)
                    .expect("append source")
                    .write_all(b"late-public-secret\n")
                    .expect("grow source");
            })
            .is_none()
        );
    }

    #[test]
    fn public_snapshot_refuses_truncation_after_open() {
        let temporary = tempfile::tempdir().expect("tempdir");
        let root = TemporaryRoot::resolve(Some(temporary.path())).expect("snapshot root");
        let public = root.path().join("public.md");
        fs::write(&public, "approved report\n").expect("public fixture");

        assert!(
            super::bounded_public_file_snapshot_after_open(&root, &public, |path| {
                fs::OpenOptions::new()
                    .write(true)
                    .open(path)
                    .expect("open source")
                    .set_len(0)
                    .expect("truncate source");
            })
            .is_none()
        );
    }

    #[test]
    fn public_snapshot_refuses_removal_after_open() {
        let temporary = tempfile::tempdir().expect("tempdir");
        let root = TemporaryRoot::resolve(Some(temporary.path())).expect("snapshot root");
        let public = root.path().join("public.md");
        fs::write(&public, "approved report\n").expect("public fixture");

        assert!(
            super::bounded_public_file_snapshot_after_open(&root, &public, |path| {
                fs::remove_file(path).expect("remove source");
            })
            .is_none()
        );
    }

    #[cfg(unix)]
    #[test]
    fn public_snapshot_refuses_pathname_replacement_after_open() {
        let temporary = tempfile::tempdir().expect("tempdir");
        let root = TemporaryRoot::resolve(Some(temporary.path())).expect("snapshot root");
        let public = root.path().join("public.md");
        let replacement = root.path().join("replacement.md");
        fs::write(&public, "approved report\n").expect("public fixture");
        fs::write(&replacement, "late-public-secret\n").expect("replacement fixture");

        assert!(
            super::bounded_public_file_snapshot_after_open(&root, &public, |path| {
                fs::rename(&replacement, path).expect("replace source");
            })
            .is_none()
        );
    }

    #[cfg(unix)]
    #[test]
    fn public_snapshot_refuses_symlink_substitution_after_open() {
        let temporary = tempfile::tempdir().expect("tempdir");
        let root = TemporaryRoot::resolve(Some(temporary.path())).expect("snapshot root");
        let public = root.path().join("public.md");
        let original = root.path().join("public.original");
        let replacement = root.path().join("replacement.md");
        fs::write(&public, "approved report\n").expect("public fixture");
        fs::write(&replacement, "late-public-secret\n").expect("replacement fixture");

        assert!(
            super::bounded_public_file_snapshot_after_open(&root, &public, |path| {
                fs::rename(path, &original).expect("move source");
                std::os::unix::fs::symlink(&replacement, path).expect("replace with symlink");
            })
            .is_none()
        );
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
