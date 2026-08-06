//! Run-log batch registry and payload sanitizers.
//!
//! The registry is the single source of truth for every batch basename, its
//! extension, whether it is replace- or append-mode, and which sanitizer
//! validates its payload before persistence.

use std::fmt;

use serde_json::Value;

use super::plan_goals::validate_plan_goals_payload;
use super::ship_outcome::{AssessmentKind, validate_ship_outcome_record};

/// Guideline ship-outcome batch name shared with the assessment lifecycle.
pub const BATCH_GUIDELINE_SHIP_OUTCOME: &str = "architectural-guideline-outcome";
/// Invariant ship-outcome batch name shared with the assessment lifecycle.
pub const BATCH_INVARIANT_SHIP_OUTCOME: &str = "architectural-invariant-outcome";

const CODEX_TRANSCRIPT_CAP_BYTES: usize = 8192;

/// Whether a batch replaces its file or appends one record per call.
#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub enum BatchMode {
    /// The payload replaces the whole batch file.
    Replace,
    /// The payload is appended to the batch file.
    Append,
}

/// Which validation a batch payload must pass before persistence.
#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub enum Sanitizer {
    /// No structural validation.
    Passthrough,
    /// The payload must decode as a single JSON object.
    JsonObject,
    /// Every non-blank line must decode as JSON.
    JsonLines,
    /// The payload must carry a non-placeholder Implementation Plan body.
    PlanGoals,
}

/// One registry row.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct BatchInfo {
    name: &'static str,
    extension: &'static str,
    mode: BatchMode,
    sanitizer: Sanitizer,
    reject_session_tmpdir: bool,
    cap_bytes: Option<usize>,
}

impl BatchInfo {
    /// Return the registry batch name.
    #[must_use]
    pub const fn name(&self) -> &'static str {
        self.name
    }

    /// Return the file extension, including the leading dot.
    #[must_use]
    pub const fn extension(&self) -> &'static str {
        self.extension
    }

    /// Return the write mode.
    #[must_use]
    pub const fn mode(&self) -> BatchMode {
        self.mode
    }

    /// Return whether this batch refuses recognized session-tmpdir pointers.
    #[must_use]
    pub const fn rejects_session_tmpdir(&self) -> bool {
        self.reject_session_tmpdir
    }

    /// Return the redacted-payload byte cap, when this batch has one.
    #[must_use]
    pub const fn cap_bytes(&self) -> Option<usize> {
        self.cap_bytes
    }

    /// Return the sanitizer that validates this batch's payload.
    #[must_use]
    pub const fn sanitizer(&self) -> Sanitizer {
        self.sanitizer
    }
}

const fn row(
    name: &'static str,
    extension: &'static str,
    mode: BatchMode,
    sanitizer: Sanitizer,
) -> BatchInfo {
    BatchInfo {
        name,
        extension,
        mode,
        sanitizer,
        reject_session_tmpdir: false,
        cap_bytes: None,
    }
}

const fn debate_row(
    name: &'static str,
    extension: &'static str,
    mode: BatchMode,
    sanitizer: Sanitizer,
) -> BatchInfo {
    BatchInfo {
        reject_session_tmpdir: true,
        ..row(name, extension, mode, sanitizer)
    }
}

const fn capped_row(
    name: &'static str,
    extension: &'static str,
    mode: BatchMode,
    sanitizer: Sanitizer,
    cap_bytes: usize,
) -> BatchInfo {
    BatchInfo {
        cap_bytes: Some(cap_bytes),
        ..row(name, extension, mode, sanitizer)
    }
}

/// Every known run-log batch, in the Python registry's declaration order.
static BATCHES: &[BatchInfo] = &[
    row(
        "parent-issue",
        ".md",
        BatchMode::Replace,
        Sanitizer::Passthrough,
    ),
    row(
        "pre-review-head",
        ".txt",
        BatchMode::Replace,
        Sanitizer::Passthrough,
    ),
    row(
        "pre-review-untracked",
        ".txt",
        BatchMode::Replace,
        Sanitizer::Passthrough,
    ),
    capped_row(
        "codex-impl-transcript",
        ".txt",
        BatchMode::Replace,
        Sanitizer::Passthrough,
        CODEX_TRANSCRIPT_CAP_BYTES,
    ),
    row(
        "codex-impl-transcript-meta",
        ".txt.meta",
        BatchMode::Replace,
        Sanitizer::Passthrough,
    ),
    row(
        "codex-impl-transcript-prompt",
        ".txt",
        BatchMode::Replace,
        Sanitizer::Passthrough,
    ),
    row(
        "codex-commit-message",
        ".txt",
        BatchMode::Replace,
        Sanitizer::Passthrough,
    ),
    row(
        "codex-impl-manifest-raw",
        ".json",
        BatchMode::Replace,
        Sanitizer::Passthrough,
    ),
    row(
        "plan-review-tally",
        ".json",
        BatchMode::Replace,
        Sanitizer::JsonObject,
    ),
    row(
        "code-review-tally",
        ".json",
        BatchMode::Replace,
        Sanitizer::JsonObject,
    ),
    row(
        "review-findings-full",
        ".jsonl",
        BatchMode::Replace,
        Sanitizer::Passthrough,
    ),
    row(
        "reviewer-prune-ledger",
        ".tsv",
        BatchMode::Replace,
        Sanitizer::Passthrough,
    ),
    row(
        "review-context",
        ".md",
        BatchMode::Replace,
        Sanitizer::Passthrough,
    ),
    row(
        "review-findings",
        ".ndjson",
        BatchMode::Append,
        Sanitizer::JsonLines,
    ),
    row(
        "review-panel-manifest",
        ".ndjson",
        BatchMode::Replace,
        Sanitizer::Passthrough,
    ),
    row(
        "panel-prompt-sizes",
        ".tsv",
        BatchMode::Replace,
        Sanitizer::Passthrough,
    ),
    row(
        "checks-digest-sizes",
        ".tsv",
        BatchMode::Append,
        Sanitizer::Passthrough,
    ),
    row(
        "review-round-summary",
        ".md",
        BatchMode::Replace,
        Sanitizer::Passthrough,
    ),
    row(
        "review-scout-manifest",
        ".json",
        BatchMode::Replace,
        Sanitizer::JsonObject,
    ),
    row(
        "difficulty-rating",
        ".json",
        BatchMode::Replace,
        Sanitizer::JsonObject,
    ),
    row(
        "review-tally",
        ".md",
        BatchMode::Replace,
        Sanitizer::Passthrough,
    ),
    row(
        "review-findings-classification-round-1",
        ".tsv",
        BatchMode::Replace,
        Sanitizer::Passthrough,
    ),
    row(
        "review-findings-classification-round-2",
        ".tsv",
        BatchMode::Replace,
        Sanitizer::Passthrough,
    ),
    row(
        "review-findings-classification-round-3",
        ".tsv",
        BatchMode::Replace,
        Sanitizer::Passthrough,
    ),
    row(
        "review-findings-classification-round-4",
        ".tsv",
        BatchMode::Replace,
        Sanitizer::Passthrough,
    ),
    row(
        "review-findings-classification-round-5",
        ".tsv",
        BatchMode::Replace,
        Sanitizer::Passthrough,
    ),
    row(
        "version-bump-reasoning",
        ".md",
        BatchMode::Replace,
        Sanitizer::Passthrough,
    ),
    row(
        "oos-issues",
        ".ndjson",
        BatchMode::Append,
        Sanitizer::JsonLines,
    ),
    row(
        "run-statistics",
        ".md",
        BatchMode::Replace,
        Sanitizer::Passthrough,
    ),
    row(
        "scope-disposition",
        ".json",
        BatchMode::Replace,
        Sanitizer::JsonObject,
    ),
    row(
        "token-report",
        ".json",
        BatchMode::Replace,
        Sanitizer::Passthrough,
    ),
    row(
        "timing-report",
        ".json",
        BatchMode::Replace,
        Sanitizer::Passthrough,
    ),
    row(
        "execution-issues",
        ".ndjson",
        BatchMode::Append,
        Sanitizer::JsonLines,
    ),
    row(
        "final-bail-reason",
        ".txt",
        BatchMode::Replace,
        Sanitizer::Passthrough,
    ),
    row(
        "include-probe-evidence",
        ".md",
        BatchMode::Replace,
        Sanitizer::Passthrough,
    ),
    row(
        "session-transcript",
        ".jsonl",
        BatchMode::Replace,
        Sanitizer::Passthrough,
    ),
    row(
        "vendor-failure-diagnostics",
        ".txt",
        BatchMode::Replace,
        Sanitizer::Passthrough,
    ),
    row(
        "plan-goals-test",
        ".md",
        BatchMode::Replace,
        Sanitizer::PlanGoals,
    ),
    row(
        BATCH_INVARIANT_SHIP_OUTCOME,
        ".json",
        BatchMode::Replace,
        Sanitizer::JsonObject,
    ),
    row(
        BATCH_GUIDELINE_SHIP_OUTCOME,
        ".json",
        BatchMode::Replace,
        Sanitizer::JsonObject,
    ),
    row(
        "ship-route-exit-handoff",
        ".env",
        BatchMode::Replace,
        Sanitizer::Passthrough,
    ),
    debate_row(
        "debate-round-ledger",
        ".ndjson",
        BatchMode::Append,
        Sanitizer::JsonLines,
    ),
    debate_row(
        "debate-proposal",
        ".md",
        BatchMode::Replace,
        Sanitizer::Passthrough,
    ),
    debate_row(
        "debate-stalemate-tally",
        ".json",
        BatchMode::Replace,
        Sanitizer::JsonObject,
    ),
    debate_row(
        "debate-participants",
        ".tsv",
        BatchMode::Replace,
        Sanitizer::Passthrough,
    ),
];

/// Look up a batch registry row by name.
#[must_use]
pub fn lookup_batch(name: &str) -> Option<&'static BatchInfo> {
    BATCHES.iter().find(|batch| batch.name == name)
}

/// Why a batch payload was refused.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct BatchPayloadError(String);

impl BatchPayloadError {
    fn new(message: impl Into<String>) -> Self {
        Self(message.into())
    }

    /// Return the operator-facing message.
    #[must_use]
    pub fn message(&self) -> &str {
        &self.0
    }
}

impl fmt::Display for BatchPayloadError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(&self.0)
    }
}

impl std::error::Error for BatchPayloadError {}

/// Normalize a run-log payload to exactly one trailing newline.
#[must_use]
pub fn normalize_run_log_text(content: &str) -> String {
    if content.is_empty() {
        return String::new();
    }
    let mut text = content.trim_end_matches('\n').to_owned();
    text.push('\n');
    text
}

/// Validate a redacted payload against its batch sanitizer.
///
/// # Errors
///
/// Returns [`BatchPayloadError`] when the payload violates the sanitizer
/// contract for `batch`.
pub fn validate_batch_payload(batch: &BatchInfo, text: &str) -> Result<(), BatchPayloadError> {
    match batch.sanitizer {
        Sanitizer::Passthrough => Ok(()),
        Sanitizer::JsonObject => validate_json_object(batch, text),
        Sanitizer::JsonLines => validate_json_lines(text),
        Sanitizer::PlanGoals => validate_plan_goals_payload(text).map_err(BatchPayloadError::new),
    }
}

fn validate_json_object(batch: &BatchInfo, text: &str) -> Result<(), BatchPayloadError> {
    let value: Value =
        serde_json::from_str(text).map_err(|error| BatchPayloadError::new(error.to_string()))?;
    if !value.is_object() {
        return Err(BatchPayloadError::new(format!(
            "batch {} requires a JSON object",
            batch.name
        )));
    }
    let kind = match batch.name {
        BATCH_GUIDELINE_SHIP_OUTCOME => Some(AssessmentKind::Guidelines),
        BATCH_INVARIANT_SHIP_OUTCOME => Some(AssessmentKind::Invariants),
        _ => None,
    };
    if let Some(kind) = kind
        && let Some(reason) = validate_ship_outcome_record(&value, kind)
    {
        return Err(BatchPayloadError::new(format!(
            "batch {} validation failed: {reason}",
            batch.name
        )));
    }
    Ok(())
}

fn validate_json_lines(text: &str) -> Result<(), BatchPayloadError> {
    for line in text.lines() {
        if line.trim().is_empty() {
            continue;
        }
        serde_json::from_str::<Value>(line)
            .map_err(|error| BatchPayloadError::new(error.to_string()))?;
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::{
        BATCH_GUIDELINE_SHIP_OUTCOME, BatchMode, lookup_batch, normalize_run_log_text,
        validate_batch_payload,
    };

    #[test]
    fn registry_reports_mode_extension_and_cap() {
        let transcript = lookup_batch("codex-impl-transcript").expect("registry row");
        assert_eq!(transcript.extension(), ".txt");
        assert_eq!(transcript.mode(), BatchMode::Replace);
        assert_eq!(transcript.cap_bytes(), Some(8192));
        let findings = lookup_batch("review-findings").expect("registry row");
        assert_eq!(findings.mode(), BatchMode::Append);
        assert_eq!(findings.cap_bytes(), None);
        assert!(lookup_batch("not-a-batch").is_none());
    }

    #[test]
    fn debate_batches_reject_session_tmpdir_pointers() {
        assert!(
            lookup_batch("debate-proposal")
                .expect("registry row")
                .rejects_session_tmpdir()
        );
        assert!(
            !lookup_batch("review-context")
                .expect("registry row")
                .rejects_session_tmpdir()
        );
    }

    #[test]
    fn normalizes_trailing_newlines() {
        assert_eq!(normalize_run_log_text(""), "");
        assert_eq!(normalize_run_log_text("a"), "a\n");
        assert_eq!(normalize_run_log_text("a\n\n\n"), "a\n");
    }

    #[test]
    fn json_object_sanitizer_rejects_arrays_and_bad_records() {
        let tally = lookup_batch("code-review-tally").expect("registry row");
        assert!(validate_batch_payload(tally, "{\"a\": 1}").is_ok());
        let error = validate_batch_payload(tally, "[]").expect_err("array should fail");
        assert_eq!(
            error.message(),
            "batch code-review-tally requires a JSON object"
        );

        let outcome = lookup_batch(BATCH_GUIDELINE_SHIP_OUTCOME).expect("registry row");
        let error = validate_batch_payload(outcome, "{\"schema_version\": \"2\"}")
            .expect_err("schema version should fail");
        assert!(error.message().contains("schema_version must be 1"));
    }

    #[test]
    fn json_lines_sanitizer_skips_blank_rows() {
        let findings = lookup_batch("review-findings").expect("registry row");
        assert!(validate_batch_payload(findings, "{\"a\":1}\n\n{\"b\":2}\n").is_ok());
        assert!(validate_batch_payload(findings, "{\"a\":1}\nnot-json\n").is_err());
    }
}
