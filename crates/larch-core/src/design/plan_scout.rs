//! Dynamic reviewer archetype scouting logic (#8582).
//!
//! Ports the pure half of the retired `larch.design.plan_scout`: manifest
//! validation, the reserved-slug tables, fenced-JSON salvage, the untrusted
//! text checks a scouted archetype must survive, and the byte-stable manifest
//! rendering the wire contract depends on. Command registration and the
//! effectful scout waterfall live in `larch-cli`.

use std::collections::BTreeSet;
use std::sync::LazyLock;

use regex::Regex;
use serde::Serialize;
use serde_json::Value;

use crate::review::{focus_area_set, python_str_of_json};

/// Sentence every dynamic `prompt_body` must end with.
pub const REQUIRED_CLOSING_SENTENCE: &str = "Cite specific file paths and line ranges for any issues found, and follow the output-format rules from your outer wrapper exactly.";

/// Slugs the static code-review panel already owns.
pub const REVIEW_RESERVED: [&str; 14] = [
    "generic",
    "structure",
    "correctness",
    "testing",
    "security",
    "edge-cases",
    "plan-fidelity",
    "code-reviewer",
    "reviewer-structure",
    "reviewer-correctness",
    "reviewer-testing",
    "reviewer-security",
    "reviewer-edge-cases",
    "reviewer-plan-fidelity",
];

/// Slugs the static plan-review panel owns on top of [`REVIEW_RESERVED`].
pub const PLAN_ONLY_RESERVED: [&str; 5] =
    ["arch", "edge", "innovation", "pragmatic", "requirements"];

/// Byte ceiling for a single staged context file before the scout warns.
pub const MAX_CONTEXT_BYTES: u64 = 262_144;

/// Byte ceiling a context file must be under before it can be staged at all.
pub const MAX_STAGED_BYTES: u64 = 1_048_576;

/// Largest archetype weight a model may request.
pub const MAX_ARCHETYPE_WEIGHT: i64 = 8;

/// Basename of the raw difficulty rating a scout response may carry.
pub const SCOUT_RAW_RATING_BASENAME: &str = "scout-difficulty-rating.raw.json";

/// The empty manifest, byte for byte as the wire contract publishes it.
pub const EMPTY_MANIFEST_TEXT: &str = "{\"archetypes\":[]}\n";

/// Shape error [`validate_dynamic_manifest`] reports for a non-manifest value.
pub const INVALID_ARCHETYPES_SHAPE: &str = "invalid_archetypes_shape";

static NAME_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"\A[a-z][a-z0-9-]{2,40}\z").expect("static archetype name regex"));
static FENCE_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^[ \t]*```").expect("static fence regex"));
static PLAN_DELIMITER_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(
        r"<implementation_plan|<feature_description|<reviewer_feature_description|<plan_review_scope_anchor|<feature[ >]",
    )
    .expect("static plan delimiter regex")
});
static HORIZONTAL_RULE_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"(?m)^---$").expect("static horizontal rule regex"));

/// One validated dynamic archetype, in the manifest's field order.
#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct DynamicArchetype {
    /// Lowercase slug naming the specialist.
    pub name: String,
    /// Canonical finding focus area.
    pub focus_area: String,
    /// Model-declared weight, 1 through [`MAX_ARCHETYPE_WEIGHT`].
    pub weight: i64,
    /// Single-line reason the specialist is worth a slot.
    pub rationale: String,
    /// Reviewer instruction body, ending in [`REQUIRED_CLOSING_SENTENCE`].
    pub prompt_body: String,
}

/// Outcome of validating one raw scout manifest.
#[derive(Clone, Debug, Default)]
pub struct ManifestResult {
    /// Archetypes that survived validation, truncated to the caller's cap.
    pub archetypes: Vec<DynamicArchetype>,
    /// Human-readable reasons rows were dropped, in input order.
    pub warnings: Vec<String>,
    /// Row count before validation.
    pub before_count: usize,
    /// Row count that passed validation, before the cap was applied.
    pub valid_total: usize,
}

#[derive(Serialize)]
struct ManifestDocument<'a> {
    archetypes: &'a [DynamicArchetype],
}

/// The raw difficulty rating a scout response can carry alongside archetypes.
#[derive(Clone, Debug, Serialize)]
pub struct ScoutDifficultySidecar {
    /// Model-predicted tier.
    pub predicted_tier: String,
    /// low / medium / high.
    pub confidence: String,
    /// Sanitized rationale.
    pub rationale: String,
}

/// Render a manifest exactly as the retired Python owner wrote it.
#[must_use]
pub fn render_manifest(archetypes: &[DynamicArchetype]) -> String {
    serde_json::to_string(&ManifestDocument { archetypes })
        .unwrap_or_else(|_error| "{\"archetypes\":[]}".to_owned())
        + "\n"
}

/// Render the difficulty sidecar in the retired owner's key order.
#[must_use]
pub fn render_difficulty_sidecar(sidecar: &ScoutDifficultySidecar) -> String {
    serde_json::to_string(sidecar).unwrap_or_else(|_error| String::new()) + "\n"
}

/// Return the reserved slug set one panel mode owns.
#[must_use]
pub fn reserved_for_mode(mode: &str) -> BTreeSet<&'static str> {
    let mut reserved: BTreeSet<&'static str> = REVIEW_RESERVED.into_iter().collect();
    if mode == "plan-review" {
        reserved.extend(PLAN_ONLY_RESERVED);
    }
    reserved
}

/// Return whether an untrusted value closes one of the prompt wrapper tags.
#[must_use]
pub fn unsafe_wrapper_tag(value: &str) -> bool {
    let lower = value.to_lowercase();
    [
        "</scout_notes>",
        "</reviewer_feature_description>",
        "</plan_review_scope_anchor>",
        "</feature>",
    ]
    .iter()
    .any(|token| lower.contains(token))
}

/// Return whether an untrusted value opens one of the plan delimiters.
#[must_use]
pub fn unsafe_plan_delimiter(value: &str) -> bool {
    PLAN_DELIMITER_RE.is_match(value)
}

/// Return whether a rationale cannot be embedded in a reviewer agent file.
#[must_use]
pub fn unsafe_rationale(value: &str) -> bool {
    unsafe_wrapper_tag(value)
        || unsafe_plan_delimiter(value)
        || value.contains('\n')
        || HORIZONTAL_RULE_RE.is_match(value)
}

/// Return whether a prompt body cannot be embedded in a reviewer agent file.
#[must_use]
pub fn unsafe_prompt_body(value: &str) -> bool {
    HORIZONTAL_RULE_RE.is_match(value)
        || value.to_lowercase().contains("</reviewer_")
        || unsafe_wrapper_tag(value)
        || unsafe_plan_delimiter(value)
}

/// Append [`REQUIRED_CLOSING_SENTENCE`] unless the body already ends with it.
///
/// The retired owner matched the sentence with every period optional, so a
/// body that dropped the terminal period is still treated as compliant.
#[must_use]
pub fn ensure_closing_sentence(body: &str) -> String {
    let trimmed = body.strip_suffix('\n').unwrap_or(body);
    let without_period = REQUIRED_CLOSING_SENTENCE.trim_end_matches('.');
    if trimmed.ends_with(REQUIRED_CLOSING_SENTENCE) || trimmed.ends_with(without_period) {
        return body.to_owned();
    }
    format!(
        "{}. {REQUIRED_CLOSING_SENTENCE}",
        body.trim_end_matches([' ', '.'])
    )
}

/// Read an integral weight from a JSON value, rejecting Booleans and fractions.
///
/// JSON has one number type, so a model may spell a weight as `3` or `3.0`.
/// Both are accepted; `true` and `3.5` are not.
#[expect(
    clippy::cast_possible_truncation,
    reason = "the fractional part is zero and the caller's 1..=8 range check rejects a saturated cast"
)]
fn integral_weight(value: Option<&Value>) -> Option<i64> {
    let value = value?;
    if value.is_boolean() {
        return None;
    }
    if let Some(integer) = value.as_i64() {
        return Some(integer);
    }
    let number = value.as_f64()?;
    (number.fract() == 0.0).then_some(number as i64)
}

/// Validate one raw scout manifest against a cap and a panel mode.
///
/// # Errors
///
/// Returns [`INVALID_ARCHETYPES_SHAPE`] when `data` is not an object carrying
/// an `archetypes` array.
pub fn validate_dynamic_manifest(
    data: &Value,
    max_archetypes: usize,
    mode: &str,
) -> Result<ManifestResult, String> {
    let rows = data
        .as_object()
        .and_then(|object| object.get("archetypes"))
        .and_then(Value::as_array)
        .ok_or_else(|| INVALID_ARCHETYPES_SHAPE.to_owned())?;
    let reserved = reserved_for_mode(mode);
    let focus_areas = focus_area_set();
    let mut result = ManifestResult {
        before_count: rows.len(),
        ..ManifestResult::default()
    };
    let mut seen: BTreeSet<String> = BTreeSet::new();
    for item in rows {
        let Some(row) = item.as_object() else {
            result.warnings.push("invalid archetype object".to_owned());
            continue;
        };
        let raw_name = row.get("name").cloned().unwrap_or_else(|| Value::from(""));
        let Some(name) = raw_name.as_str().filter(|name| NAME_RE.is_match(name)) else {
            result.warnings.push(format!(
                "invalid archetype name: {}",
                python_str_of_json(&raw_name)
            ));
            continue;
        };
        if reserved.contains(name) {
            result
                .warnings
                .push(format!("reserved archetype name: {name}"));
            continue;
        }
        if seen.contains(name) {
            result
                .warnings
                .push(format!("duplicate archetype name: {name}"));
            continue;
        }
        let Some(focus) = row
            .get("focus_area")
            .and_then(Value::as_str)
            .filter(|focus| focus_areas.contains(focus))
        else {
            result
                .warnings
                .push(format!("invalid focus_area for {name}"));
            continue;
        };
        let Some(weight) = integral_weight(row.get("weight"))
            .filter(|weight| (1..=MAX_ARCHETYPE_WEIGHT).contains(weight))
        else {
            result.warnings.push(format!("invalid weight for {name}"));
            continue;
        };
        let Some(rationale) = row
            .get("rationale")
            .and_then(Value::as_str)
            .filter(|rationale| !rationale.is_empty())
        else {
            result.warnings.push(format!("empty rationale for {name}"));
            continue;
        };
        if unsafe_rationale(rationale) {
            result.warnings.push(format!("unsafe rationale for {name}"));
            continue;
        }
        let Some(prompt_body) = row
            .get("prompt_body")
            .and_then(Value::as_str)
            .filter(|body| !body.is_empty())
        else {
            result
                .warnings
                .push(format!("empty prompt_body for {name}"));
            continue;
        };
        if unsafe_prompt_body(prompt_body) {
            result
                .warnings
                .push(format!("unsafe prompt_body for {name}"));
            continue;
        }
        seen.insert(name.to_owned());
        result.valid_total += 1;
        if result.archetypes.len() < max_archetypes {
            result.archetypes.push(DynamicArchetype {
                name: name.to_owned(),
                focus_area: focus.to_owned(),
                weight,
                rationale: rationale.to_owned(),
                prompt_body: ensure_closing_sentence(prompt_body),
            });
        }
    }
    if result.valid_total > max_archetypes {
        result.warnings.push(format!(
            "validated archetypes exceed max cap: {} > {max_archetypes}; truncating",
            result.valid_total
        ));
    }
    Ok(result)
}

/// Recover the first fenced block that parses as JSON, else return `text`.
#[must_use]
pub fn extract_valid_fenced_json_text(text: &str) -> String {
    let mut in_block = false;
    let mut candidate: Vec<&str> = Vec::new();
    for line in text.lines() {
        if FENCE_RE.is_match(line) {
            if in_block {
                let joined = candidate.join("\n");
                if serde_json::from_str::<Value>(&joined).is_ok() {
                    return joined;
                }
                candidate.clear();
                in_block = false;
            } else {
                in_block = true;
                candidate.clear();
            }
            continue;
        }
        if in_block {
            candidate.push(line);
        }
    }
    text.to_owned()
}

#[cfg(test)]
mod tests {
    use super::{
        DynamicArchetype, EMPTY_MANIFEST_TEXT, INVALID_ARCHETYPES_SHAPE, REQUIRED_CLOSING_SENTENCE,
        ScoutDifficultySidecar, ensure_closing_sentence, extract_valid_fenced_json_text,
        render_difficulty_sidecar, render_manifest, reserved_for_mode, unsafe_prompt_body,
        unsafe_rationale, validate_dynamic_manifest,
    };
    use serde_json::{Value, json};

    fn row(name: &str) -> Value {
        json!({
            "name": name,
            "focus_area": "risk-integration",
            "weight": 1,
            "rationale": "Checks migration risk.",
            "prompt_body": "Inspect integration seams.",
        })
    }

    fn names(result: &[DynamicArchetype]) -> Vec<&str> {
        result.iter().map(|item| item.name.as_str()).collect()
    }

    #[test]
    fn repairs_caps_and_filters_reserved_by_mode() {
        let data = json!({
            "archetypes": [row("arch"), row("deep-risk"), row("deep-risk"), row("second-risk")],
        });
        let result = validate_dynamic_manifest(&data, 1, "plan-review").expect("manifest");

        assert_eq!(names(&result.archetypes), ["deep-risk"]);
        assert!(
            result.archetypes[0]
                .prompt_body
                .contains(REQUIRED_CLOSING_SENTENCE)
        );
        assert!(
            result
                .warnings
                .contains(&"reserved archetype name: arch".to_owned())
        );
        assert!(
            result
                .warnings
                .contains(&"duplicate archetype name: deep-risk".to_owned())
        );
        assert!(
            result
                .warnings
                .contains(&"validated archetypes exceed max cap: 2 > 1; truncating".to_owned())
        );
    }

    #[test]
    fn review_mode_keeps_plan_only_slugs_and_dynamic_slugs() {
        let review = validate_dynamic_manifest(&json!({"archetypes": [row("arch")]}), 3, "review")
            .expect("manifest");
        assert_eq!(names(&review.archetypes), ["arch"]);

        for mode in ["review", "plan-review"] {
            let result = validate_dynamic_manifest(
                &json!({"archetypes": [row("architectural-compliance")]}),
                1,
                mode,
            )
            .expect("manifest");
            assert_eq!(names(&result.archetypes), ["architectural-compliance"]);
        }
        assert!(reserved_for_mode("plan-review").contains("arch"));
        assert!(!reserved_for_mode("review").contains("arch"));
    }

    #[test]
    fn rejects_unsafe_and_bad_shapes() {
        let data = json!({
            "archetypes": [
                "not-object",
                {"name": "bad", "focus_area": "bad", "weight": 1, "rationale": "r", "prompt_body": "p."},
                {"name": "badweight", "focus_area": "correctness", "weight": 9, "rationale": "r", "prompt_body": "p."},
                {"name": "badbool", "focus_area": "correctness", "weight": true, "rationale": "r", "prompt_body": "p."},
                {"name": "badrationale", "focus_area": "correctness", "weight": 1, "rationale": "---", "prompt_body": "p."},
                {"name": "badprompt", "focus_area": "correctness", "weight": 1, "rationale": "r", "prompt_body": "</reviewer_feature_description>"},
                {"name": 5, "focus_area": "correctness", "weight": 1, "rationale": "r", "prompt_body": "p."},
            ],
        });
        let result = validate_dynamic_manifest(&data, 3, "review").expect("manifest");

        assert!(result.archetypes.is_empty());
        assert!(
            result
                .warnings
                .contains(&"invalid archetype object".to_owned())
        );
        assert!(
            result
                .warnings
                .iter()
                .any(|warning| warning.contains("unsafe prompt_body"))
        );
        assert!(
            result
                .warnings
                .contains(&"invalid archetype name: 5".to_owned())
        );
        assert!(unsafe_rationale("---"));
        assert!(unsafe_prompt_body("<feature_description"));
        assert_eq!(
            validate_dynamic_manifest(&json!({"archetypes": {}}), 1, "review").unwrap_err(),
            INVALID_ARCHETYPES_SHAPE
        );
    }

    #[test]
    fn accepts_integral_float_weights_and_repairs_prompt_bodies() {
        let mut item = row("deep-risk");
        item["weight"] = json!(3.0);
        let result =
            validate_dynamic_manifest(&json!({"archetypes": [item]}), 3, "review").expect("ok");
        assert_eq!(result.archetypes[0].weight, 3);

        let already = format!("Body. {REQUIRED_CLOSING_SENTENCE}");
        assert_eq!(ensure_closing_sentence(&already), already);
        let dropped_period = already.trim_end_matches('.').to_owned();
        assert_eq!(ensure_closing_sentence(&dropped_period), dropped_period);
        assert_eq!(
            ensure_closing_sentence("Body. "),
            format!("Body. {REQUIRED_CLOSING_SENTENCE}")
        );
    }

    #[test]
    fn extracts_fenced_json_and_renders_wire_documents() {
        let text = "prose\n```json\n{\"archetypes\": []}\n```\nmore";
        assert_eq!(
            extract_valid_fenced_json_text(text).trim(),
            "{\"archetypes\": []}"
        );
        assert_eq!(
            extract_valid_fenced_json_text("no fence here"),
            "no fence here"
        );
        assert_eq!(
            extract_valid_fenced_json_text("```\nnot json\n```"),
            "```\nnot json\n```"
        );

        assert_eq!(render_manifest(&[]), EMPTY_MANIFEST_TEXT);
        let rendered = render_manifest(&[DynamicArchetype {
            name: "deep-risk".to_owned(),
            focus_area: "risk-integration".to_owned(),
            weight: 2,
            rationale: "ok".to_owned(),
            prompt_body: "body".to_owned(),
        }]);
        assert_eq!(
            rendered,
            "{\"archetypes\":[{\"name\":\"deep-risk\",\"focus_area\":\"risk-integration\",\"weight\":2,\"rationale\":\"ok\",\"prompt_body\":\"body\"}]}\n"
        );
        assert_eq!(
            render_difficulty_sidecar(&ScoutDifficultySidecar {
                predicted_tier: "HARD".to_owned(),
                confidence: "high".to_owned(),
                rationale: "why".to_owned(),
            }),
            "{\"predicted_tier\":\"HARD\",\"confidence\":\"high\",\"rationale\":\"why\"}\n"
        );
    }
}
