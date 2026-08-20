//! Pure Step 2 dispatch manifest validation and sanitization (#8623).
//!
//! Everything here works on already-decoded values so the `step2-dispatch`
//! orchestrator keeps its I/O and process work in the CLI layer.

use serde_json::{Map, Value};

use crate::difficulty::validate_rating_object;
use crate::implement::manifest::path_under_submodule;
use crate::redaction::redact_secrets_only;

/// Maximum `summary_bullets` a complete manifest may declare.
pub const SUMMARY_BULLETS_MAX: usize = 5;
/// Minimum whitespace-separated fields in a `git submodule status` row.
pub const PORCELAIN_MIN_PARTS: usize = 2;
/// Exit code the external launcher wrapper uses for its own validation failure.
pub const WRAPPER_VALIDATION_RC: i32 = 2;
/// Maximum needs-QA resume rounds before the loop is refused.
pub const RESUME_CAP: u32 = 5;
/// Coder tokens `--coder` accepts.
pub const SAFE_CODERS: [&str; 3] = ["claude", "codex", "cursor"];
/// Manifest statuses the dispatcher routes on.
pub const MANIFEST_STATUSES: [&str; 3] = ["complete", "needs_qa", "bailed"];
/// Cap on a sanitized `architectural_acknowledgment`.
const ACKNOWLEDGMENT_MAX_CHARS: usize = 500;
/// Cap on a sanitized manifest bail reason.
const BAIL_REASON_MAX_CHARS: usize = 200;

/// Submodule roots declared by `git submodule status --recursive` output.
#[must_use]
pub fn submodule_roots(status_stdout: &str) -> Vec<String> {
    status_stdout
        .lines()
        .filter_map(|line| {
            let parts: Vec<&str> = line.split_whitespace().collect();
            (parts.len() >= PORCELAIN_MIN_PARTS).then(|| parts[1].trim_end_matches('/').to_owned())
        })
        .collect()
}

/// True when a `git submodule status` line reports a dirty or conflicted entry.
#[must_use]
pub fn submodule_status_dirty(status_stdout: &str) -> bool {
    status_stdout
        .lines()
        .any(|line| line.starts_with(['+', '-', 'U']))
}

/// True for a manifest that is schema-1 and self-declares completion.
///
/// A non-zero launcher exit is salvageable only for such a manifest, because
/// the implementation work was already atomically published.
#[must_use]
pub fn manifest_complete_salvageable(obj: Option<&Value>) -> bool {
    let Some(map) = obj.and_then(Value::as_object) else {
        return false;
    };
    json_scalar_string(map.get("schema_version")) == "1"
        && map.get("status").and_then(Value::as_str) == Some("complete")
}

/// Render a manifest scalar the way Python `str(value)` did for comparison.
#[must_use]
pub fn json_scalar_string(value: Option<&Value>) -> String {
    match value {
        None | Some(Value::Null) => String::new(),
        Some(other) => json_scalar_text(other).unwrap_or_else(|| other.to_string()),
    }
}

/// The text of a JSON scalar, or `None` for null and container values.
///
/// Shared by every reader that has to accept the loosely typed scalars a
/// Python writer produced, where a number or bool may stand in for a string.
#[must_use]
pub fn json_scalar_text(value: &Value) -> Option<String> {
    match value {
        Value::String(text) => Some(text.clone()),
        Value::Number(number) => Some(number.to_string()),
        Value::Bool(flag) => Some(flag.to_string()),
        Value::Null | Value::Array(_) | Value::Object(_) => None,
    }
}

/// The declared `status`, or empty when it is absent or not a string.
#[must_use]
pub fn manifest_status(obj: Option<&Value>) -> String {
    obj.and_then(Value::as_object)
        .and_then(|map| map.get("status"))
        .and_then(Value::as_str)
        .unwrap_or_default()
        .to_owned()
}

/// Refuse a declared path that escapes the repository or enters a submodule.
///
/// Returns `protected-path-modified` for the first offending declared path.
#[must_use]
pub fn validate_manifest_paths(obj: &Map<String, Value>, roots: &[String]) -> &'static str {
    for path in declared_paths(obj) {
        if path.contains('\0')
            || path.starts_with('/')
            || path.contains("..")
            || path_under_submodule(&path, roots)
        {
            return "protected-path-modified";
        }
    }
    ""
}

/// Every path a complete manifest declares as touched or tested.
#[must_use]
pub fn declared_paths(obj: &Map<String, Value>) -> Vec<String> {
    let mut paths: Vec<String> = files_touched_paths(obj);
    paths.extend(string_list(obj.get("tests_added_or_modified")));
    paths
}

/// The `files_touched[].path` values a manifest declares.
#[must_use]
pub fn files_touched_paths(obj: &Map<String, Value>) -> Vec<String> {
    obj.get("files_touched")
        .and_then(Value::as_array)
        .map(|items| {
            items
                .iter()
                .filter_map(|item| item.as_object()?.get("path")?.as_str())
                .map(str::to_owned)
                .collect()
        })
        .unwrap_or_default()
}

fn string_list(value: Option<&Value>) -> Vec<String> {
    value
        .and_then(Value::as_array)
        .map(|items| {
            items
                .iter()
                .filter_map(Value::as_str)
                .map(str::to_owned)
                .collect()
        })
        .unwrap_or_default()
}

/// True when a complete manifest satisfies every required schema-1 field.
#[must_use]
pub fn complete_schema_valid(obj: &Map<String, Value>) -> bool {
    let files_touched_ok = obj
        .get("files_touched")
        .and_then(Value::as_array)
        .is_some_and(|items| {
            !items.is_empty()
                && items.iter().all(|item| {
                    item.as_object()
                        .is_some_and(|entry| entry.get("path").and_then(Value::as_str).is_some())
                })
        });
    let bullets_ok = obj
        .get("summary_bullets")
        .and_then(Value::as_array)
        .is_some_and(|items| !items.is_empty() && items.len() <= SUMMARY_BULLETS_MAX);
    files_touched_ok
        && bullets_ok
        && obj
            .get("commit_message")
            .and_then(Value::as_str)
            .is_some_and(|text| !text.is_empty())
        && obj
            .get("tests_added_or_modified")
            .is_some_and(Value::is_array)
        && obj.get("todos_left").is_some_and(Value::is_array)
        && obj.get("oos_observations").is_some_and(Value::is_array)
        && difficulty_schema_valid(obj)
}

fn difficulty_schema_valid(obj: &Map<String, Value>) -> bool {
    validate_rating_object(obj.get("difficulty").unwrap_or(&Value::Null)).is_ok()
}

/// Collapse an acknowledgment to one redacted, bounded, control-free line.
#[must_use]
pub fn sanitize_architectural_acknowledgment(value: Option<&Value>) -> String {
    let Some(Value::String(text)) = value else {
        return String::new();
    };
    let folded = fold_visible_whitespace(&text.replace(['\r', '\n'], " "));
    let redacted = redact_secrets_only(&folded);
    truncate_chars(redacted.trim(), ACKNOWLEDGMENT_MAX_CHARS)
}

/// True when a manifest carries a non-empty visible architecture acknowledgment.
#[must_use]
pub fn require_architectural_acknowledgment(obj: &Map<String, Value>) -> bool {
    !sanitize_architectural_acknowledgment(obj.get("architectural_acknowledgment")).is_empty()
}

/// Collapse a manifest bail reason to one bounded line, or fall back.
#[must_use]
pub fn sanitize_bail_reason(reason: &str, fallback: &str) -> String {
    // A control byte becomes a separator rather than vanishing, so two words it
    // sat between cannot silently merge into a token nobody wrote.
    let visible: String = reason
        .chars()
        .map(|character| {
            if character < ' ' || character == '\u{7f}' {
                ' '
            } else {
                character
            }
        })
        .collect();
    let bounded = truncate_chars(
        fold_visible_whitespace(&visible).trim(),
        BAIL_REASON_MAX_CHARS,
    );
    if bounded.is_empty() {
        fallback.to_owned()
    } else {
        bounded
    }
}

/// Redact the operator-visible strings a manifest carries before publication.
#[must_use]
pub fn sanitize_manifest_obj(obj: &Map<String, Value>) -> Map<String, Value> {
    let mut sanitized = obj.clone();
    if let Some(Value::String(message)) = sanitized.get("commit_message") {
        let redacted = redact_secrets_only(message);
        let _prior = sanitized.insert("commit_message".to_owned(), Value::from(redacted));
    }
    if sanitized.contains_key("architectural_acknowledgment") {
        let acknowledgment =
            sanitize_architectural_acknowledgment(sanitized.get("architectural_acknowledgment"));
        let _prior = sanitized.insert(
            "architectural_acknowledgment".to_owned(),
            Value::from(acknowledgment),
        );
    }
    for key in ["summary_bullets", "todos_left"] {
        if let Some(Value::Array(items)) = sanitized.get(key) {
            let redacted: Vec<Value> = items.iter().map(redact_string_value).collect();
            let _prior = sanitized.insert(key.to_owned(), Value::Array(redacted));
        }
    }
    if let Some(Value::Object(_)) = sanitized.get("difficulty")
        && let Ok(rating) = validate_rating_object(&sanitized["difficulty"])
    {
        let mut object = Map::new();
        let _prior = object.insert(
            "predicted_tier".to_owned(),
            Value::from(rating.predicted_tier),
        );
        let _prior = object.insert("confidence".to_owned(), Value::from(rating.confidence));
        let _prior = object.insert("rationale".to_owned(), Value::from(rating.rationale));
        let _prior = sanitized.insert("difficulty".to_owned(), Value::Object(object));
    }
    if let Some(Value::Array(items)) = sanitized.get("oos_observations") {
        let redacted: Vec<Value> = items.iter().map(redact_observation).collect();
        let _prior = sanitized.insert("oos_observations".to_owned(), Value::Array(redacted));
    }
    sanitized
}

fn redact_string_value(value: &Value) -> Value {
    match value {
        Value::String(text) => Value::from(redact_secrets_only(text)),
        other => other.clone(),
    }
}

fn redact_observation(item: &Value) -> Value {
    let Some(object) = item.as_object() else {
        return item.clone();
    };
    let mut updated = object.clone();
    for key in ["title", "description", "focus-area", "focus_area"] {
        if let Some(Value::String(text)) = updated.get(key) {
            let redacted = redact_secrets_only(text);
            let _prior = updated.insert(key.to_owned(), Value::from(redacted));
        }
    }
    Value::Object(updated)
}

/// Whether an OOS materialization outcome must fail the dispatch.
///
/// A failed count probe is always fatal. A failed materialization is fatal when
/// either the count probe or the manifest itself proves observations exist.
#[must_use]
pub const fn oos_materialize_should_bail(
    count_rc: i32,
    count: Option<u64>,
    oos_nonempty: bool,
    materialize_failed: bool,
) -> bool {
    if count_rc != 0 {
        return true;
    }
    if materialize_failed && matches!(count, Some(value) if value > 0) {
        return true;
    }
    materialize_failed && oos_nonempty
}

/// Rebuild `needs_qa` questions from a legacy `qa-pending.json` items array.
///
/// Returns `None` when no item carries renderable text, which the caller treats
/// as an unrepairable schema failure.
#[must_use]
pub fn repaired_qa_questions(qa_obj: Option<&Value>) -> Option<Value> {
    let items = qa_obj?.as_object()?.get("items")?.as_array()?;
    if items.is_empty() {
        return None;
    }
    let mut questions = Vec::new();
    for (index, item) in items.iter().enumerate() {
        let Some(entry) = item.as_object() else {
            continue;
        };
        let parts: Vec<String> = [
            ("area", "Area"),
            ("risk", "Risk"),
            ("suggested_check", "Suggested check"),
        ]
        .into_iter()
        .filter_map(|(key, label)| {
            let text = json_scalar_string(entry.get(key));
            (!text.is_empty()).then(|| format!("{label}: {text}"))
        })
        .collect();
        let mut question = Map::new();
        let _prior = question.insert("id".to_owned(), Value::from(format!("q{}", index + 1)));
        let _prior = question.insert("text".to_owned(), Value::from(parts.join(". ")));
        questions.push(Value::Object(question));
    }
    if questions.is_empty() {
        return None;
    }
    let mut wrapper = Map::new();
    let _prior = wrapper.insert("questions".to_owned(), Value::Array(questions));
    Some(Value::Object(wrapper))
}

/// True when `qa-pending.json` carries a usable non-empty `questions` array.
#[must_use]
pub fn qa_pending_valid(qa_obj: Option<&Value>) -> bool {
    qa_obj
        .and_then(Value::as_object)
        .and_then(|map| map.get("questions"))
        .and_then(Value::as_array)
        .is_some_and(|items| !items.is_empty())
}

/// True when a `needs_qa` manifest already declares its own questions.
#[must_use]
pub fn needs_qa_questions_present(obj: &Map<String, Value>) -> bool {
    obj.get("needs_qa")
        .and_then(Value::as_object)
        .and_then(|map| map.get("questions"))
        .and_then(Value::as_array)
        .is_some_and(|items| !items.is_empty())
}

/// True when the child's stdout is a complete Claude-fallback envelope.
#[must_use]
pub fn child_stdout_is_claude_fallback(stdout: &str) -> bool {
    let mut status = false;
    let mut authority = false;
    for line in stdout.lines() {
        if line == "STATUS=claude_fallback" {
            status = true;
        } else if line == "ORCHESTRATOR_EDIT_AUTHORITY=allowed" {
            authority = true;
        }
    }
    status && authority
}

/// True when Step 2 should mark its token/timing budget for an in-agent run.
#[must_use]
pub fn step2_token_mark_eligible(
    coder: &str,
    codex_binary_found: &str,
    cursor_binary_found: &str,
) -> bool {
    coder == "claude"
        || (coder == "codex" && codex_binary_found != "true")
        || (coder == "cursor" && cursor_binary_found != "true")
}

/// Reject a rater model token that is empty or carries control bytes.
#[must_use]
pub fn model_value_safe(value: &str) -> String {
    let text = value.trim();
    if text.is_empty()
        || text
            .chars()
            .any(|character| character <= '\u{1f}' || character == '\u{7f}')
    {
        return "unknown".to_owned();
    }
    text.to_owned()
}

/// Normalize a plain warning to the bullet form the final summary counts.
#[must_use]
pub fn warning_bullet(text: &str) -> String {
    if text.starts_with("- ") {
        text.to_owned()
    } else {
        format!("- {text}")
    }
}

/// Validated bounded Step 2 completion-retry state.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct CompletionRetryState {
    /// Retries already spent, always within the configured cap.
    pub count: u32,
    /// Coverage fingerprint the retry was recorded against.
    pub fingerprint: String,
}

/// A completion-retry record that exists but cannot be trusted.
///
/// The caller fails closed on this: a retry it cannot count is a retry it
/// cannot bound, so the dispatch bails rather than re-running the implementer.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct CompletionRetryInvalid;

/// Parse the bounded completion-retry wire record.
///
/// `Ok(None)` means no retry is in flight.
///
/// # Errors
///
/// Returns [`CompletionRetryInvalid`] for a non-numeric count, an out-of-range
/// count, or a fingerprint that is not 64 lowercase hex characters.
pub fn parse_completion_retry_state(
    text: &str,
    cap: u32,
) -> Result<Option<CompletionRetryState>, CompletionRetryInvalid> {
    let mut count_text = "";
    let mut fingerprint = "";
    for line in text.lines() {
        let trimmed = line.trim_end_matches('\r');
        if trimmed.starts_with('#') {
            continue;
        }
        if let Some(rest) = trimmed.strip_prefix("COMPLETION_RETRY_COUNT=")
            && count_text.is_empty()
        {
            count_text = rest;
        } else if let Some(rest) = trimmed.strip_prefix("PLAN_COVERAGE_FINGERPRINT=")
            && fingerprint.is_empty()
        {
            fingerprint = rest;
        }
    }
    if !is_coverage_fingerprint(fingerprint) {
        return Err(CompletionRetryInvalid);
    }
    let Ok(count) = count_text.parse::<u32>() else {
        return Err(CompletionRetryInvalid);
    };
    if count == 0 || count > cap {
        return Err(CompletionRetryInvalid);
    }
    Ok(Some(CompletionRetryState {
        count,
        fingerprint: fingerprint.to_owned(),
    }))
}

fn is_coverage_fingerprint(value: &str) -> bool {
    crate::is_sha256_hex(value)
}

/// Collapse runs of Python-recognized whitespace to single spaces.
fn fold_visible_whitespace(value: &str) -> String {
    value.split_whitespace().collect::<Vec<_>>().join(" ")
}

fn truncate_chars(value: &str, limit: usize) -> String {
    value.chars().take(limit).collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn complete() -> Map<String, Value> {
        json!({
            "schema_version": 1,
            "status": "complete",
            "files_touched": [{"path": "a.rs"}],
            "commit_message": "msg",
            "summary_bullets": ["one"],
            "tests_added_or_modified": [],
            "todos_left": [],
            "oos_observations": [],
            "difficulty": {
                "predicted_tier": "MODERATE",
                "confidence": "high",
                "rationale": "because",
            },
        })
        .as_object()
        .cloned()
        .expect("object")
    }

    #[test]
    fn submodule_rows_yield_trimmed_roots_and_dirty_flags() {
        let status = " abc123 vendor/foo (v1)\n+def456 vendor/bar/ (v2)\n";
        assert_eq!(submodule_roots(status), ["vendor/foo", "vendor/bar"]);
        assert!(submodule_status_dirty(status));
        assert!(!submodule_status_dirty(" abc vendor/foo (v1)\n"));
        assert!(submodule_roots("oneword\n").is_empty());
    }

    #[test]
    fn salvageable_requires_schema_one_and_complete() {
        assert!(manifest_complete_salvageable(Some(&json!({
            "schema_version": "1",
            "status": "complete"
        }))));
        assert!(manifest_complete_salvageable(Some(&json!({
            "schema_version": 1,
            "status": "complete"
        }))));
        assert!(!manifest_complete_salvageable(Some(&json!({
            "schema_version": 2,
            "status": "complete"
        }))));
        assert!(!manifest_complete_salvageable(Some(&json!({
            "schema_version": 1,
            "status": "bailed"
        }))));
        assert!(!manifest_complete_salvageable(None));
    }

    #[test]
    fn declared_paths_are_refused_when_they_escape_or_enter_submodules() {
        let roots = vec!["vendor".to_owned()];
        let mut obj = complete();
        assert_eq!(validate_manifest_paths(&obj, &roots), "");
        let _prior = obj.insert("files_touched".to_owned(), json!([{"path": "/etc/passwd"}]));
        assert_eq!(
            validate_manifest_paths(&obj, &roots),
            "protected-path-modified"
        );
        let _prior = obj.insert("files_touched".to_owned(), json!([{"path": "../up"}]));
        assert_eq!(
            validate_manifest_paths(&obj, &roots),
            "protected-path-modified"
        );
        let _prior = obj.insert("files_touched".to_owned(), json!([{"path": "vendor/x"}]));
        assert_eq!(
            validate_manifest_paths(&obj, &roots),
            "protected-path-modified"
        );
        let _prior = obj.insert("files_touched".to_owned(), json!([{"path": "ok.rs"}]));
        let _prior = obj.insert("tests_added_or_modified".to_owned(), json!(["vendor"]));
        assert_eq!(
            validate_manifest_paths(&obj, &roots),
            "protected-path-modified"
        );
    }

    #[test]
    fn complete_schema_checks_every_required_field() {
        assert!(complete_schema_valid(&complete()));
        for (key, value) in [
            ("files_touched", json!([])),
            ("files_touched", json!([{"no_path": 1}])),
            ("commit_message", json!("")),
            ("summary_bullets", json!([])),
            ("summary_bullets", json!(["a", "b", "c", "d", "e", "f"])),
            ("tests_added_or_modified", json!("not-a-list")),
            ("todos_left", json!(0)),
            ("oos_observations", json!(null)),
            ("difficulty", json!({"predicted_tier": "NOPE"})),
        ] {
            let mut obj = complete();
            let _prior = obj.insert(key.to_owned(), value);
            assert!(!complete_schema_valid(&obj), "{key} must be required");
        }
    }

    #[test]
    fn acknowledgment_sanitization_folds_newlines_and_bounds_length() {
        assert_eq!(
            sanitize_architectural_acknowledgment(Some(&json!("honoring\nI-Sec-1\t and  G-Py-4"))),
            "honoring I-Sec-1 and G-Py-4"
        );
        assert!(sanitize_architectural_acknowledgment(Some(&json!("   "))).is_empty());
        assert!(sanitize_architectural_acknowledgment(Some(&json!(7))).is_empty());
        assert!(sanitize_architectural_acknowledgment(None).is_empty());
        let long = "x".repeat(600);
        assert_eq!(
            sanitize_architectural_acknowledgment(Some(&json!(long)))
                .chars()
                .count(),
            ACKNOWLEDGMENT_MAX_CHARS
        );
        let mut obj = complete();
        assert!(!require_architectural_acknowledgment(&obj));
        let _prior = obj.insert(
            "architectural_acknowledgment".to_owned(),
            json!("honoring I-Sec-1"),
        );
        assert!(require_architectural_acknowledgment(&obj));
    }

    #[test]
    fn bail_reason_drops_control_bytes_and_falls_back_when_empty() {
        assert_eq!(
            sanitize_bail_reason("bad\u{7f}\nreason  here", "fallback"),
            "bad reason here"
        );
        assert_eq!(sanitize_bail_reason("\u{1}\u{2}", "fallback"), "fallback");
        assert_eq!(sanitize_bail_reason("", "fallback"), "fallback");
        assert_eq!(
            sanitize_bail_reason(&"y".repeat(400), "fallback")
                .chars()
                .count(),
            BAIL_REASON_MAX_CHARS
        );
    }

    #[test]
    fn sanitizing_a_manifest_normalizes_difficulty_and_leaves_other_keys() {
        let mut obj = complete();
        let _prior = obj.insert("summary_bullets".to_owned(), json!(["keep", 7]));
        let _prior = obj.insert(
            "oos_observations".to_owned(),
            json!([{"title": "t", "focus-area": "f"}, "scalar"]),
        );
        let sanitized = sanitize_manifest_obj(&obj);
        // The retired owner ran every bullet through the line-oriented secret
        // redactor, which terminates its output with a newline.
        assert_eq!(sanitized["summary_bullets"], json!(["keep\n", 7]));
        assert_eq!(
            sanitized["difficulty"],
            json!({"predicted_tier": "MODERATE", "confidence": "high", "rationale": "because"})
        );
        assert_eq!(sanitized["oos_observations"][1], json!("scalar"));
        assert_eq!(sanitized["status"], json!("complete"));
    }

    #[test]
    fn oos_bail_policy_covers_count_and_materialize_failures() {
        assert!(oos_materialize_should_bail(1, None, false, false));
        assert!(oos_materialize_should_bail(0, Some(2), false, true));
        assert!(oos_materialize_should_bail(0, None, true, true));
        assert!(!oos_materialize_should_bail(0, Some(0), false, true));
        assert!(!oos_materialize_should_bail(0, Some(3), true, false));
    }

    #[test]
    fn qa_repair_builds_ids_and_refuses_empty_input() {
        let repaired = repaired_qa_questions(Some(&json!({
            "items": [{"area": "a", "risk": "r"}, {"suggested_check": "c"}]
        })))
        .expect("repaired");
        assert_eq!(repaired["questions"][0]["id"], json!("q1"));
        assert_eq!(repaired["questions"][0]["text"], json!("Area: a. Risk: r"));
        assert_eq!(
            repaired["questions"][1]["text"],
            json!("Suggested check: c")
        );
        assert!(repaired_qa_questions(Some(&json!({"items": []}))).is_none());
        assert!(repaired_qa_questions(Some(&json!({"items": ["scalar"]}))).is_none());
        assert!(repaired_qa_questions(None).is_none());
        assert!(qa_pending_valid(Some(&repaired)));
        assert!(!qa_pending_valid(Some(&json!({"questions": []}))));
    }

    #[test]
    fn claude_fallback_needs_both_envelope_rows() {
        assert!(child_stdout_is_claude_fallback(
            "STATUS=claude_fallback\nORCHESTRATOR_EDIT_AUTHORITY=allowed\n"
        ));
        assert!(!child_stdout_is_claude_fallback("STATUS=claude_fallback\n"));
        assert!(!child_stdout_is_claude_fallback(
            "ORCHESTRATOR_EDIT_AUTHORITY=allowed\n"
        ));
    }

    #[test]
    fn token_mark_eligibility_tracks_the_in_agent_lane() {
        assert!(step2_token_mark_eligible("claude", "true", "true"));
        assert!(step2_token_mark_eligible("codex", "false", "true"));
        assert!(!step2_token_mark_eligible("codex", "true", "true"));
        assert!(step2_token_mark_eligible("cursor", "true", "false"));
        assert!(!step2_token_mark_eligible("cursor", "true", "true"));
    }

    #[test]
    fn model_tokens_and_warning_bullets_normalize() {
        assert_eq!(model_value_safe("  gpt-x  "), "gpt-x");
        assert_eq!(model_value_safe(""), "unknown");
        assert_eq!(model_value_safe("bad\u{7f}"), "unknown");
        assert_eq!(warning_bullet("plain"), "- plain");
        assert_eq!(warning_bullet("- already"), "- already");
    }

    #[test]
    fn completion_retry_state_parses_only_a_bounded_valid_record() {
        let fingerprint = "a".repeat(64);
        let text = format!("COMPLETION_RETRY_COUNT=2\nPLAN_COVERAGE_FINGERPRINT={fingerprint}\n");
        assert_eq!(
            parse_completion_retry_state(&text, 3),
            Ok(Some(CompletionRetryState {
                count: 2,
                fingerprint: fingerprint.clone(),
            }))
        );
        assert_eq!(
            parse_completion_retry_state(&text, 1),
            Err(CompletionRetryInvalid)
        );
        assert_eq!(
            parse_completion_retry_state(
                &format!("COMPLETION_RETRY_COUNT=0\nPLAN_COVERAGE_FINGERPRINT={fingerprint}\n"),
                3
            ),
            Err(CompletionRetryInvalid)
        );
        assert_eq!(
            parse_completion_retry_state(
                &format!("COMPLETION_RETRY_COUNT=x\nPLAN_COVERAGE_FINGERPRINT={fingerprint}\n"),
                3
            ),
            Err(CompletionRetryInvalid)
        );
        assert_eq!(
            parse_completion_retry_state(
                "COMPLETION_RETRY_COUNT=1\nPLAN_COVERAGE_FINGERPRINT=zz\n",
                3
            ),
            Err(CompletionRetryInvalid)
        );
    }

    #[test]
    fn manifest_status_and_needs_qa_questions_read_defensively() {
        assert_eq!(
            manifest_status(Some(&json!({"status": "bailed"}))),
            "bailed"
        );
        assert!(manifest_status(Some(&json!({"status": 1}))).is_empty());
        assert!(manifest_status(None).is_empty());
        let obj = json!({"needs_qa": {"questions": [{"id": "q1"}]}})
            .as_object()
            .cloned()
            .expect("object");
        assert!(needs_qa_questions_present(&obj));
        let empty = json!({"needs_qa": {"questions": []}})
            .as_object()
            .cloned()
            .expect("object");
        assert!(!needs_qa_questions_present(&empty));
    }
}
