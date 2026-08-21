//! Pure candidate-shape and plan-reconciliation rules for the design dialectic.
//!
//! The candidate file grammar is shared by the four Rust-owned candidate
//! commands from #8584 and by the still-Python Gate C debate commands. The
//! command effects stay in `larch-cli`; this module owns only byte-independent
//! normalization, fingerprinting, and plan-choice checks.

use std::{collections::BTreeSet, error::Error, fmt};

use regex::RegexBuilder;
use serde::Serialize;
use serde_json::Value;
use sha2::{Digest as _, Sha256};

use crate::ensure_ascii_json;

/// Maximum number of drafter decisions retained from one candidate payload.
pub const MAX_DIALECTIC_DECISIONS: usize = 2;

/// One normalized dialectic decision.
#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct DialecticCandidate {
    pub id: String,
    pub title: String,
    pub option_a: String,
    pub option_b: String,
    pub tradeoff: String,
    pub drafter_pick: String,
    pub why_this_matters: String,
}

/// A normalized candidate payload bound to one plan fingerprint.
#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct DialecticCandidateSet {
    pub plan_fingerprint: String,
    pub decisions: Vec<DialecticCandidate>,
}

impl DialecticCandidateSet {
    /// Candidate ids in presentation order.
    #[must_use]
    pub fn ordered_ids(&self) -> Vec<&str> {
        self.decisions
            .iter()
            .map(|candidate| candidate.id.as_str())
            .collect()
    }
}

/// Stable candidate-shape refusal used by the command layer.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct DialecticShapeError(String);

impl DialecticShapeError {
    fn new(message: impl Into<String>) -> Self {
        Self(message.into())
    }
}

impl fmt::Display for DialecticShapeError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(&self.0)
    }
}

impl Error for DialecticShapeError {}

fn text_field(value: Option<&Value>, field: &str) -> Result<String, DialecticShapeError> {
    let text = match value {
        Some(Value::String(value)) => value.trim().to_owned(),
        Some(Value::Object(value)) => ["label", "summary", "description", "text"]
            .into_iter()
            .filter_map(|key| value.get(key).and_then(Value::as_str))
            .map(str::trim)
            .filter(|piece| !piece.is_empty())
            .collect::<Vec<_>>()
            .join(": "),
        _ => String::new(),
    };
    if text.is_empty() {
        return Err(DialecticShapeError::new(format!(
            "{field} must be non-empty text"
        )));
    }
    Ok(text)
}

/// Normalize an operator-visible decision label into the candidate-id grammar.
#[must_use]
pub fn dialectic_slugify(value: &str, fallback: &str) -> String {
    let mut slug = String::new();
    let mut separator_pending = false;
    for character in value.to_lowercase().chars() {
        if character.is_ascii_lowercase() || character.is_ascii_digit() {
            if separator_pending && !slug.is_empty() {
                slug.push('-');
            }
            separator_pending = false;
            slug.push(character);
        } else {
            separator_pending = true;
        }
    }
    let mut slug = slug.trim_matches('-').to_owned();
    slug.truncate(80);
    if slug.is_empty() {
        fallback.to_owned()
    } else {
        slug
    }
}

fn parse_candidate(value: &Value, index: usize) -> Result<DialecticCandidate, DialecticShapeError> {
    let Some(object) = value.as_object() else {
        return Err(DialecticShapeError::new("each decision must be an object"));
    };
    let title = text_field(object.get("title"), "title")?;
    let option_a = text_field(object.get("option_a"), "option_a")?;
    let option_b = text_field(object.get("option_b"), "option_b")?;
    if option_a == option_b {
        return Err(DialecticShapeError::new(
            "option_a and option_b must differ",
        ));
    }
    let tradeoff = text_field(object.get("tradeoff"), "tradeoff")?;
    let why_this_matters = text_field(object.get("why_this_matters"), "why_this_matters")?;
    let Some(drafter_pick @ ("option_a" | "option_b")) =
        object.get("drafter_pick").and_then(Value::as_str)
    else {
        return Err(DialecticShapeError::new(
            "drafter_pick must be option_a or option_b",
        ));
    };
    let fallback = format!("decision-{index}");
    let id = object
        .get("id")
        .and_then(Value::as_str)
        .filter(|value| !value.trim().is_empty())
        .map_or_else(
            || dialectic_slugify(&title, &fallback),
            |value| dialectic_slugify(value, &fallback),
        );
    Ok(DialecticCandidate {
        id,
        title,
        option_a,
        option_b,
        tradeoff,
        drafter_pick: drafter_pick.to_owned(),
        why_this_matters,
    })
}

fn dedupe_candidate_ids(decisions: &mut [DialecticCandidate]) {
    let mut seen = BTreeSet::new();
    for (offset, decision) in decisions.iter_mut().enumerate() {
        let original = decision.id.clone();
        let mut candidate = original.clone();
        if seen.contains(&candidate) {
            let mut suffix = offset + 1;
            candidate = format!("{original}-{suffix}");
            while seen.contains(&candidate) {
                suffix += 1;
                candidate = format!("{original}-{suffix}");
            }
            decision.id.clone_from(&candidate);
        }
        let _ = seen.insert(candidate);
    }
}

/// Normalize one parsed candidate payload with the retired Python semantics.
///
/// # Errors
/// Returns the exact shape message for a malformed payload or stale required
/// fingerprint.
pub fn normalize_dialectic_candidates(
    payload: &Value,
    fingerprint: Option<&str>,
    require_fingerprint: bool,
) -> Result<DialecticCandidateSet, DialecticShapeError> {
    let Some(object) = payload.as_object() else {
        return Err(DialecticShapeError::new(
            "candidate payload must be an object",
        ));
    };
    let payload_fingerprint = object.get("plan_fingerprint").and_then(Value::as_str);
    let normalized_fingerprint = if require_fingerprint {
        let Some(payload_fingerprint) =
            payload_fingerprint.filter(|value| !value.trim().is_empty())
        else {
            return Err(DialecticShapeError::new("plan_fingerprint is required"));
        };
        if fingerprint.is_some_and(|current| current != payload_fingerprint) {
            return Err(DialecticShapeError::new(
                "plan_fingerprint does not match current plan",
            ));
        }
        payload_fingerprint.to_owned()
    } else {
        fingerprint.map_or_else(
            || {
                payload_fingerprint
                    .filter(|value| !value.is_empty())
                    .unwrap_or_default()
                    .to_owned()
            },
            str::to_owned,
        )
    };
    let Some(raw_decisions) = object.get("decisions").and_then(Value::as_array) else {
        return Err(DialecticShapeError::new("decisions must be a list"));
    };
    let mut decisions = raw_decisions
        .iter()
        .take(MAX_DIALECTIC_DECISIONS)
        .enumerate()
        .map(|(index, value)| parse_candidate(value, index + 1))
        .collect::<Result<Vec<_>, _>>()?;
    if decisions.is_empty() {
        return Err(DialecticShapeError::new(
            "decisions must contain at least one decision",
        ));
    }
    dedupe_candidate_ids(&mut decisions);
    Ok(DialecticCandidateSet {
        plan_fingerprint: normalized_fingerprint,
        decisions,
    })
}

fn innermost_json_container_bytes(content: &[u8]) -> Option<u8> {
    let mut stack = Vec::new();
    let mut in_string = false;
    let mut escaped = false;
    for &byte in content {
        if in_string {
            if escaped {
                escaped = false;
            } else if byte == b'\\' {
                escaped = true;
            } else if byte == b'"' {
                in_string = false;
            }
            continue;
        }
        match byte {
            b'"' => in_string = true,
            b'{' | b'[' => stack.push(byte),
            b'}' if stack.last() == Some(&b'{') => {
                let _ = stack.pop();
            }
            b']' if stack.last() == Some(&b'[') => {
                let _ = stack.pop();
            }
            _ => {}
        }
    }
    stack.last().copied()
}

fn innermost_json_container(content: &str) -> Option<u8> {
    innermost_json_container_bytes(content.as_bytes())
}

fn json_error_offset(content: &str, error: &serde_json::Error) -> usize {
    let mut offset = 0;
    for (index, line) in content.split_inclusive('\n').enumerate() {
        if index + 1 == error.line() {
            offset += error.column().saturating_sub(1).min(line.len());
            return offset;
        }
        offset += line.len();
    }
    content.len()
}

fn json_container_at_error(content: &str, error: &serde_json::Error) -> Option<u8> {
    innermost_json_container_bytes(&content.as_bytes()[..json_error_offset(content, error)])
}

fn invalid_unicode_escape(content: &str, error: &serde_json::Error) -> bool {
    let bytes = content.as_bytes();
    let end = (json_error_offset(content, error) + 1).min(bytes.len());
    bytes[..end]
        .iter()
        .rposition(|byte| *byte == b'\\')
        .is_some_and(|offset| bytes.get(offset + 1) == Some(&b'u'))
}

fn final_string_is_object_key(content: &str) -> bool {
    let content = content.trim_end().as_bytes();
    if content.last() != Some(&b'"') {
        return false;
    }
    let mut in_string = false;
    let mut escaped = false;
    let mut previous_significant = None;
    let mut string_context = None;
    let mut final_context = None;
    for &byte in content {
        if in_string {
            if escaped {
                escaped = false;
            } else if byte == b'\\' {
                escaped = true;
            } else if byte == b'"' {
                in_string = false;
                final_context = string_context;
                previous_significant = Some(b'"');
            }
        } else if byte == b'"' {
            in_string = true;
            string_context = previous_significant;
        } else if !byte.is_ascii_whitespace() {
            previous_significant = Some(byte);
        }
    }
    matches!(final_context, Some(b'{' | b','))
}

fn python_json_error_message(content: &str, error: &serde_json::Error) -> &'static str {
    let message = error.to_string();
    let trimmed = content.trim_end();
    if content.trim().is_empty() {
        "Expecting value"
    } else if message.starts_with("EOF while parsing a string") {
        "Unterminated string starting at"
    } else if message.starts_with("key must be a string")
        || (message.starts_with("EOF while parsing an object")
            && (trimmed.ends_with('{') || trimmed.ends_with(',')))
        || (message.starts_with("EOF while parsing a value")
            && trimmed.ends_with(',')
            && innermost_json_container(content) == Some(b'{'))
        || (message.starts_with("trailing comma")
            && json_container_at_error(content, error) == Some(b'{'))
    {
        "Expecting property name enclosed in double quotes"
    } else if message.starts_with("EOF while parsing an object")
        && final_string_is_object_key(content)
    {
        "Expecting ':' delimiter"
    } else if message.starts_with("trailing characters") {
        "Extra data"
    } else if message.starts_with("expected `:`") {
        "Expecting ':' delimiter"
    } else if message.starts_with("EOF while parsing a value")
        || (message.starts_with("EOF while parsing a list") && trimmed.ends_with('['))
        || message.starts_with("expected value")
        || message.starts_with("expected ident")
        || message.starts_with("trailing comma")
    {
        "Expecting value"
    } else if message.starts_with("expected `,`")
        || message.starts_with("EOF while parsing an object")
        || message.starts_with("EOF while parsing a list")
    {
        "Expecting ',' delimiter"
    } else if message.starts_with("invalid escape") && invalid_unicode_escape(content, error) {
        "Invalid \\uXXXX escape"
    } else if message.starts_with("invalid escape") {
        "Invalid \\escape"
    } else if message.starts_with("control character") {
        "Invalid control character at"
    } else {
        "Expecting value"
    }
}

/// Parse and normalize candidate JSON.
///
/// # Errors
/// Returns a stable Python-compatible JSON or candidate-shape message.
pub fn parse_dialectic_candidates(
    content: &str,
    fingerprint: Option<&str>,
    require_fingerprint: bool,
) -> Result<DialecticCandidateSet, DialecticShapeError> {
    let payload: Value = serde_json::from_str(content).map_err(|error| {
        DialecticShapeError::new(format!(
            "invalid JSON: {}",
            python_json_error_message(content, &error)
        ))
    })?;
    normalize_dialectic_candidates(&payload, fingerprint, require_fingerprint)
}

/// Render the compact `json.dumps(..., separators=(",", ":"))` stdout row.
///
/// # Errors
/// Returns serialization failures from `serde_json`.
pub fn render_dialectic_candidates_compact(
    candidates: &DialecticCandidateSet,
) -> Result<String, serde_json::Error> {
    serde_json::to_string(candidates).map(|text| ensure_ascii_json(&text))
}

/// Render the sorted, two-space candidate wire file plus its terminal newline.
///
/// # Errors
/// Returns serialization failures from `serde_json`.
pub fn render_dialectic_candidates_pretty(
    candidates: &DialecticCandidateSet,
) -> Result<String, serde_json::Error> {
    let value = serde_json::to_value(candidates)?;
    serde_json::to_string_pretty(&value).map(|text| format!("{}\n", ensure_ascii_json(&text)))
}

/// SHA-256 identity of exact `plan.txt` bytes.
#[must_use]
pub fn dialectic_plan_fingerprint(plan: &[u8]) -> String {
    format!("{:x}", Sha256::digest(plan))
}

fn is_python_word(character: char) -> bool {
    character == '_' || character.is_alphanumeric()
}

/// Whether `option` occurs with Python `(?<!\w)...(?!\w)` boundaries.
#[must_use]
pub fn dialectic_option_in_plan(plan: &str, option: &str) -> bool {
    let option = option.trim();
    if option.is_empty() {
        return false;
    }
    let Ok(pattern) = RegexBuilder::new(&regex::escape(option))
        .case_insensitive(true)
        .build()
    else {
        return false;
    };
    pattern.find_iter(plan).any(|matched| {
        let before = plan[..matched.start()].chars().next_back();
        let after = plan[matched.end()..].chars().next();
        before.is_none_or(|character| !is_python_word(character))
            && after.is_none_or(|character| !is_python_word(character))
    })
}

/// Infer the candidate side uniquely named by the final plan.
///
/// # Errors
/// Returns the stable ambiguity message when both options or neither option
/// appears with a valid boundary.
pub fn infer_dialectic_plan_choice(
    plan: &str,
    option_a: &str,
    option_b: &str,
) -> Result<&'static str, DialecticShapeError> {
    match (
        dialectic_option_in_plan(plan, option_a),
        dialectic_option_in_plan(plan, option_b),
    ) {
        (true, false) => Ok("option_a"),
        (false, true) => Ok("option_b"),
        _ => Err(DialecticShapeError::new(
            "Cannot reconcile drafter_pick against final plan.txt (both options or neither appear uniquely)",
        )),
    }
}

/// Refuse a candidate set whose recorded picks no longer match `plan.txt`.
///
/// # Errors
/// Returns the stable ambiguity or mismatch message for the first bad decision.
pub fn reconcile_dialectic_candidates(
    candidates: &DialecticCandidateSet,
    plan: &str,
) -> Result<(), DialecticShapeError> {
    for decision in &candidates.decisions {
        let inferred = infer_dialectic_plan_choice(plan, &decision.option_a, &decision.option_b)?;
        if inferred != decision.drafter_pick {
            return Err(DialecticShapeError::new(format!(
                "drafter_pick {} no longer matches final plan ({inferred})",
                decision.drafter_pick
            )));
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use serde_json::json;

    use super::*;

    fn decision(id: &str, title: &Value) -> Value {
        json!({
            "id": id,
            "title": title,
            "option_a": "Use SQLite",
            "option_b": "Use JSON files",
            "tradeoff": "query power",
            "drafter_pick": "option_a",
            "why_this_matters": "runtime dependencies"
        })
    }

    #[test]
    fn normalization_coerces_text_dedupes_ids_and_caps_decisions() {
        let payload = json!({
            "plan_fingerprint": "fp",
            "decisions": [
                decision("same", &json!({"label": " Storage ", "summary": "choice"})),
                decision("same", &json!("Second")),
                false
            ]
        });
        let normalized = normalize_dialectic_candidates(&payload, Some("fp"), true).unwrap();
        assert_eq!(normalized.decisions.len(), 2);
        assert_eq!(normalized.decisions[0].title, "Storage: choice");
        assert_eq!(normalized.ordered_ids(), vec!["same", "same-2"]);
    }

    #[test]
    fn required_fingerprint_rejects_stale_payload() {
        let payload =
            json!({"plan_fingerprint": "old", "decisions": [decision("one", &json!("One"))]});
        assert_eq!(
            normalize_dialectic_candidates(&payload, Some("new"), true)
                .unwrap_err()
                .to_string(),
            "plan_fingerprint does not match current plan"
        );
    }

    #[test]
    fn renderers_preserve_python_order_spacing_and_ascii_escaping() {
        let candidates = DialecticCandidateSet {
            plan_fingerprint: "café".to_owned(),
            decisions: vec![DialecticCandidate {
                id: "one".to_owned(),
                title: "One".to_owned(),
                option_a: "A".to_owned(),
                option_b: "B".to_owned(),
                tradeoff: "T".to_owned(),
                drafter_pick: "option_a".to_owned(),
                why_this_matters: "W".to_owned(),
            }],
        };
        let compact = render_dialectic_candidates_compact(&candidates).unwrap();
        assert!(compact.starts_with("{\"plan_fingerprint\":\"caf\\u00e9\",\"decisions\":"));
        let pretty = render_dialectic_candidates_pretty(&candidates).unwrap();
        assert!(pretty.starts_with("{\n  \"decisions\": ["));
        assert!(pretty.ends_with('\n'));
    }

    #[test]
    fn plan_choice_uses_word_boundaries_and_refuses_mismatch() {
        assert!(!dialectic_option_in_plan("SQLiteLite", "SQLite"));
        assert!(dialectic_option_in_plan("Use SQLite here.", "SQLite"));
        let candidates = normalize_dialectic_candidates(
            &json!({"decisions": [decision("one", &json!("One"))]}),
            Some("fp"),
            false,
        )
        .unwrap();
        assert!(reconcile_dialectic_candidates(&candidates, "Use SQLite here.").is_ok());
        assert_eq!(
            reconcile_dialectic_candidates(&candidates, "Use JSON files here.")
                .unwrap_err()
                .to_string(),
            "drafter_pick option_a no longer matches final plan (option_b)"
        );
    }

    #[test]
    fn invalid_json_uses_python_reason_tokens() {
        for (content, expected) in [
            ("not json", "Expecting value"),
            ("[", "Expecting value"),
            ("{\"a\"", "Expecting ':' delimiter"),
            ("{\"a\":true", "Expecting ',' delimiter"),
            (
                "{\"a\":true,",
                "Expecting property name enclosed in double quotes",
            ),
            ("{\"a\":\"x", "Unterminated string starting at"),
            ("{\"a\":\"\\uZZZZ\"}", "Invalid \\uXXXX escape"),
            ("{\"a\":\"\\u1234\",\"b\":\"\\q\"}", "Invalid \\escape"),
            ("{\"a\":\"\n\"}", "Invalid control character at"),
            ("{\"a\":[1,]}", "Expecting value"),
        ] {
            assert_eq!(
                parse_dialectic_candidates(content, None, false)
                    .unwrap_err()
                    .to_string(),
                format!("invalid JSON: {expected}"),
                "content: {content:?}"
            );
        }
    }
}
