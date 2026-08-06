//! Step 8 ship-outcome sidecar validation for the two assessment kinds.
//!
//! Ported from `larch.core.architectural_guidelines._validate_ship_outcome_record`
//! with the kind-specific policy from `larch.core.assessment_kind`.

use serde_json::Value;

const REASON_DETERMINISTIC_CLEAN: &str = "deterministic-clean";
const REASON_UNAVAILABLE: &str = "unavailable";
const ASSESSMENT_OUTCOME_CLEAN: &str = "clean";

const COMMON_REASONS: &[&str] = &[
    "clean-note",
    "note-read-failed",
    "note-redaction-failed",
    "compose-materialization-failed",
    REASON_DETERMINISTIC_CLEAN,
    REASON_UNAVAILABLE,
    "unknown",
];

const STATUS_VALUES: &[&str] = &["present", "absent", "invalid"];

const DROPPED_REASONS: &[&str] = &[
    "note-read-failed",
    "note-redaction-failed",
    "compose-materialization-failed",
    REASON_UNAVAILABLE,
    "unknown",
];

/// Which assessment lifecycle a ship-outcome sidecar belongs to.
#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub enum AssessmentKind {
    /// `ARCHITECTURAL_GUIDELINES.md` deviations.
    Guidelines,
    /// `ARCHITECTURAL_INVARIANTS.md` violations.
    Invariants,
}

impl AssessmentKind {
    const fn is_invariant(self) -> bool {
        matches!(self, Self::Invariants)
    }

    const fn key(self) -> &'static str {
        match self {
            Self::Guidelines => "guidelines",
            Self::Invariants => "invariants",
        }
    }

    const fn singular(self) -> &'static str {
        match self {
            Self::Guidelines => "guideline",
            Self::Invariants => "invariant",
        }
    }

    const fn status_field(self) -> &'static str {
        match self {
            Self::Guidelines => "guidelines_status",
            Self::Invariants => "invariants_status",
        }
    }

    const fn ship_outcomes(self) -> &'static [&'static str] {
        match self {
            Self::Guidelines => &["pinned", "clean", "dropped"],
            Self::Invariants => &["clean", "violation", "dropped"],
        }
    }

    const fn non_clean_ship_outcome(self) -> &'static str {
        match self {
            Self::Guidelines => "pinned",
            Self::Invariants => "violation",
        }
    }

    const fn non_clean_authored_outcome(self) -> &'static str {
        match self {
            Self::Guidelines => "deviation",
            Self::Invariants => "violation",
        }
    }

    const fn non_clean_note_reason(self) -> &'static str {
        match self {
            Self::Guidelines => "note-pinned",
            Self::Invariants => "violation-note",
        }
    }

    const fn absent_reason(self) -> &'static str {
        match self {
            Self::Guidelines => "guidelines-absent",
            Self::Invariants => "invariants-absent",
        }
    }

    const fn invalid_reason(self) -> &'static str {
        match self {
            Self::Guidelines => "guidelines-invalid",
            Self::Invariants => "invariants-invalid",
        }
    }

    /// Extra clean reason accepted only by the invariant lifecycle.
    const fn empty_reason(self) -> Option<&'static str> {
        match self {
            Self::Guidelines => None,
            Self::Invariants => Some("invariants-empty"),
        }
    }

    fn ship_reason_tokens(self) -> Vec<&'static str> {
        let mut tokens = COMMON_REASONS.to_vec();
        tokens.push(self.non_clean_note_reason());
        tokens.push(self.absent_reason());
        tokens.push(self.invalid_reason());
        if let Some(empty) = self.empty_reason() {
            tokens.push(empty);
        }
        tokens
    }
}

fn string_field(record: &serde_json::Map<String, Value>, key: &str) -> String {
    // Python coerces through `str(d.get(key) or "")`, so falsy values render empty.
    match record.get(key) {
        Some(Value::String(text)) => text.clone(),
        Some(Value::Number(number)) => {
            if number.as_f64() == Some(0.0) {
                String::new()
            } else {
                number.to_string()
            }
        }
        Some(Value::Bool(true)) => "True".to_owned(),
        _ => String::new(),
    }
}

/// Validate one ship-outcome sidecar record, returning the failure reason.
///
/// Returns `None` when the record is consistent for its assessment kind.
#[must_use]
#[allow(clippy::too_many_lines)] // Parity validator preserves every distinct Python diagnostic.
pub fn validate_ship_outcome_record(data: &Value, kind: AssessmentKind) -> Option<String> {
    let label = kind.singular();
    let Value::Object(record) = data else {
        return Some(format!("{label} outcome artifact must be a JSON object"));
    };
    if string_field(record, "schema_version") != "1" {
        return Some(format!("{label} outcome schema_version must be 1"));
    }
    let phase = string_field(record, "phase");
    let step = string_field(record, "step");
    let base_ref = string_field(record, "base_ref");
    let head_sha = string_field(record, "head_sha");
    let outcome = string_field(record, "outcome");
    let reason = string_field(record, "reason");
    let status = string_field(record, kind.status_field());
    let assessment_kind = string_field(record, "assessment_kind");

    let operator_waived = match record.get("operator_waived") {
        None | Some(Value::Bool(false)) => false,
        Some(Value::Bool(true)) => true,
        Some(_) => return Some(format!("{label} outcome operator_waived must be boolean")),
    };
    if operator_waived && (outcome != "dropped" || reason != REASON_UNAVAILABLE) {
        return Some(format!(
            "{label} outcome operator_waived requires unavailable dropped outcome"
        ));
    }
    if phase != "implement" {
        return Some(format!("{label} outcome phase must be implement"));
    }
    if step != "8" {
        return Some(format!("{label} outcome step must be 8"));
    }
    if base_ref.is_empty() {
        return Some(format!("{label} outcome base_ref is empty"));
    }
    if head_sha.trim().is_empty() {
        return Some(format!("{label} outcome head_sha is empty"));
    }
    if !kind.ship_outcomes().contains(&outcome.as_str()) {
        return Some(format!("{label} outcome token is unknown"));
    }
    if !STATUS_VALUES.contains(&status.as_str()) {
        return Some(format!(
            "{label} outcome {} is unknown",
            kind.status_field()
        ));
    }
    if !kind.ship_reason_tokens().contains(&reason.as_str()) {
        return Some(format!("{label} outcome reason token is unknown"));
    }
    let allowed_assessment_kinds = [
        "",
        ASSESSMENT_OUTCOME_CLEAN,
        kind.non_clean_authored_outcome(),
    ];
    if !allowed_assessment_kinds.contains(&assessment_kind.as_str()) {
        return Some(format!("{label} outcome assessment_kind is unknown"));
    }

    if status == "absent" || status == "invalid" {
        let expected_reason = if status == "absent" {
            kind.absent_reason()
        } else {
            kind.invalid_reason()
        };
        if outcome != "clean" || reason != expected_reason || !assessment_kind.is_empty() {
            return Some(format!(
                "{label} outcome fields are inconsistent for {status} {}",
                kind.key()
            ));
        }
        return None;
    }
    if outcome == "clean" {
        let mut clean_reasons = vec!["clean-note", REASON_DETERMINISTIC_CLEAN];
        if let Some(empty) = kind.empty_reason() {
            clean_reasons.push(empty);
        }
        if !clean_reasons.contains(&reason.as_str()) || assessment_kind != "clean" {
            return Some(format!(
                "{label} outcome fields are inconsistent for clean {}",
                kind.key()
            ));
        }
        return None;
    }
    if outcome == kind.non_clean_ship_outcome() {
        if reason != kind.non_clean_note_reason()
            || assessment_kind != kind.non_clean_authored_outcome()
        {
            return Some(if kind.is_invariant() {
                "invariant outcome fields are inconsistent for invariant violations".to_owned()
            } else {
                "guideline outcome fields are inconsistent for pinned guidelines".to_owned()
            });
        }
        return None;
    }
    if outcome == "dropped" {
        if !assessment_kind.is_empty()
            || (!kind.is_invariant() && status != "present")
            || !DROPPED_REASONS.contains(&reason.as_str())
        {
            return Some(format!(
                "{label} outcome fields are inconsistent for dropped {}",
                kind.key()
            ));
        }
        return None;
    }
    Some(format!("{label} outcome fields are inconsistent"))
}

#[cfg(test)]
mod tests {
    use super::{AssessmentKind, validate_ship_outcome_record};
    use serde_json::json;

    fn clean_guideline() -> serde_json::Value {
        json!({
            "schema_version": "1",
            "phase": "implement",
            "step": "8",
            "base_ref": "origin/main",
            "head_sha": "abc123",
            "outcome": "clean",
            "reason": "clean-note",
            "guidelines_status": "present",
            "assessment_kind": "clean",
        })
    }

    #[test]
    fn accepts_a_consistent_clean_record() {
        assert_eq!(
            validate_ship_outcome_record(&clean_guideline(), AssessmentKind::Guidelines),
            None
        );
    }

    #[test]
    fn rejects_non_object_and_bad_schema_version() {
        assert_eq!(
            validate_ship_outcome_record(&json!([]), AssessmentKind::Invariants),
            Some("invariant outcome artifact must be a JSON object".to_owned())
        );
        let mut record = clean_guideline();
        record["schema_version"] = json!(2);
        assert_eq!(
            validate_ship_outcome_record(&record, AssessmentKind::Guidelines),
            Some("guideline outcome schema_version must be 1".to_owned())
        );
    }

    #[test]
    fn operator_waived_requires_unavailable_dropped() {
        let mut record = clean_guideline();
        record["operator_waived"] = json!(true);
        assert_eq!(
            validate_ship_outcome_record(&record, AssessmentKind::Guidelines),
            Some(
                "guideline outcome operator_waived requires unavailable dropped outcome".to_owned()
            )
        );
        record["operator_waived"] = json!("yes");
        assert_eq!(
            validate_ship_outcome_record(&record, AssessmentKind::Guidelines),
            Some("guideline outcome operator_waived must be boolean".to_owned())
        );
    }

    #[test]
    fn invariant_kind_accepts_its_own_tokens_only() {
        let mut record = clean_guideline();
        record["invariants_status"] = json!("present");
        record["reason"] = json!("invariants-empty");
        assert_eq!(
            validate_ship_outcome_record(&record, AssessmentKind::Invariants),
            None
        );
        // The same empty reason is unknown for guidelines.
        assert_eq!(
            validate_ship_outcome_record(&record, AssessmentKind::Guidelines),
            Some("guideline outcome reason token is unknown".to_owned())
        );
    }

    #[test]
    fn non_clean_outcomes_require_matching_reason_and_kind() {
        let mut record = clean_guideline();
        record["outcome"] = json!("pinned");
        record["reason"] = json!("note-pinned");
        record["assessment_kind"] = json!("deviation");
        assert_eq!(
            validate_ship_outcome_record(&record, AssessmentKind::Guidelines),
            None
        );
        record["reason"] = json!("clean-note");
        assert_eq!(
            validate_ship_outcome_record(&record, AssessmentKind::Guidelines),
            Some("guideline outcome fields are inconsistent for pinned guidelines".to_owned())
        );
    }

    #[test]
    fn dropped_guideline_requires_present_status() {
        let mut record = clean_guideline();
        record["outcome"] = json!("dropped");
        record["reason"] = json!("unavailable");
        record["assessment_kind"] = json!("");
        assert_eq!(
            validate_ship_outcome_record(&record, AssessmentKind::Guidelines),
            None
        );
        record["guidelines_status"] = json!("absent");
        assert_eq!(
            validate_ship_outcome_record(&record, AssessmentKind::Guidelines),
            Some("guideline outcome fields are inconsistent for absent guidelines".to_owned())
        );
    }
}
