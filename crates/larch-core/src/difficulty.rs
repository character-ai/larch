//! Difficulty rating, floors, records, and plan-trailer lookup.
//!
//! Ports the command-owned surface of `larch.calibration.difficulty` used by
//! `validate-rating`, `extract-plan-metadata`, `write-record`, `render-rubric`,
//! `render-line`, `resolve-panel`, and `sync-labels`.

use crate::{ensure_ascii_json, glob_matches, private_atomic_write};
use regex::Regex;
use serde_json::{Map, Value};
use std::{fs, path::Path, sync::LazyLock};

/// Canonical difficulty tiers, lowest to highest.
pub const TIERS: [&str; 3] = ["TRIVIAL", "MODERATE", "HARD"];
/// Lowest tier.
pub const TRIVIAL: &str = "TRIVIAL";
/// Default / middle tier.
pub const MODERATE: &str = "MODERATE";
/// Highest tier.
pub const HARD: &str = "HARD";
/// Allowed confidence tokens.
pub const CONFIDENCES: [&str; 3] = ["low", "medium", "high"];
/// Record schema version written by every producer.
pub const SCHEMA_VERSION: u64 = 1;
/// Rationale cap after sanitization.
pub const RATIONALE_MAX_CHARS: usize = 500;
/// Audit sampling denominator (`1:N`).
pub const AUDIT_DENOMINATOR: i64 = 30;
/// Round cap shared by every tier.
pub const TIER_CEILING: i64 = 2;
/// Codex model role shared by every tier.
pub const CODEX_MODEL_ROLE: &str = "review";
/// Basename of the raw design difficulty-rating sidecar.
pub const DESIGN_RAW_RATING_BASENAME: &str = "design-difficulty-rating.raw.json";
/// Basename of the merged difficulty record run logs consume.
pub const DIFFICULTY_RECORD_BASENAME: &str = "difficulty-rating.json";
/// Plugin-relative floor table.
pub const FLOOR_MANIFEST_RELPATH: &str = "docs/difficulty-floor-globs.tsv";
/// Fallback rationale used when synthesizing a panel record.
pub const FALLBACK_PANEL_RATIONALE: &str = "fallback rating synthesized for panel resolution";
/// Rubric printed by `difficulty render-rubric`.
pub const RUBRIC: &str = "\
Difficulty rating rubric (model judgment, not a computed complexity score):
- TRIVIAL: localized, low-risk edits with obvious tests or documentation-only wording updates.
- MODERATE: multi-file or workflow-affecting changes where integration, state, or reviewer interpretation can fail.
- HARD: cross-cutting lifecycle, security-sensitive, concurrency, CI/merge, or prompt-contract changes with high blast radius.
Confidence: use high when evidence is direct, medium when ordinary uncertainty remains, and low when scope or risk is unclear. Low confidence bumps the recorded tier by one level, capped at HARD.
Floors: hooks, redaction/secret handling, ship/merge drivers, session-env writers, and CI workflows force at least MODERATE. Floors raise only.
Seeded examples:
TRIVIAL: run-2026-06-27-doc-typo corrected a doc-only stale phrase; run-2026-06-29-test-pin refreshed a single harness literal; run-2026-07-01-small-cli added one bounded flag parser test.
MODERATE: run-2026-06-28-review-prune touched review loop metadata; run-2026-06-30-design-trailer changed plan trailer validation; run-2026-07-01-run-log-batch added a persisted run-log batch.
HARD: run-2026-06-26-ship-merge changed merge routing; run-2026-06-30-redaction updated secret handling; run-2026-07-02-session-bootstrap altered session-env materialization.
";

static TRAILER_LINE_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(
        r"^(review_status|rounds_completed|difficulty|diff_added|diff_deleted|mechanical_churn|oversize_override|diff_lines): ([^\r\n]+)$",
    )
    .expect("static trailer regex")
});
static LEGACY_CONFIDENCE_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^confidence: .+$").expect("static confidence regex"));
static SIZE_INTEGER_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"(?:0[0-7]*|[1-9][0-9]*)").expect("static size integer regex"));
static DIGITS_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"[0-9]+").expect("static digits regex"));

/// Validated model rating after sanitization and the low-confidence bump.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct DifficultyRating {
    /// Model-predicted tier.
    pub predicted_tier: String,
    /// low / medium / high.
    pub confidence: String,
    /// Sanitized rationale.
    pub rationale: String,
    /// Predicted tier after the low-confidence bump.
    pub adjusted_tier: String,
}

/// One floor glob row.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct DifficultyFloor {
    /// Path glob.
    pub glob: String,
    /// Minimum tier.
    pub floor: String,
    /// Human reason.
    pub reason: String,
}

/// One matched floor.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct FloorMatch {
    /// Changed path that matched.
    pub path: String,
    /// Matching glob.
    pub glob: String,
    /// Floor tier.
    pub floor: String,
    /// Row reason.
    pub reason: String,
}

/// Highest matching floor plus every hit.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct FloorResult {
    /// Raised tier, or TRIVIAL when nothing matched.
    pub tier: String,
    /// Every glob hit.
    pub matches: Vec<FloorMatch>,
}

/// Persisted panel-resolution fields.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct TierResolution {
    /// Effective panel tier.
    pub panel_tier: String,
    /// Clamped round cap.
    pub round_cap: i64,
    /// Codex model role.
    pub codex_model_role: String,
    /// Whether the 1:N audit ran.
    pub audit_evaluated: bool,
    /// Whether the audit upgraded to HARD.
    pub audit_upgrade: bool,
    /// `operator`, `floor`, or `none`.
    pub override_source: String,
    /// Whether this round was escalated.
    pub escalated_round: bool,
}

/// Return whether `value` is a canonical tier.
#[must_use]
pub fn tier_valid(value: &str) -> bool {
    TIERS.contains(&value)
}

/// Uppercase and accept only a canonical tier.
#[must_use]
pub fn normalize_tier(value: &str, default: &str) -> String {
    let tier = value.trim().to_ascii_uppercase();
    if tier_valid(&tier) {
        tier
    } else {
        default.to_owned()
    }
}

/// Rank a canonical tier. Invalid input is an error.
///
/// # Errors
/// Returns when `tier` is not canonical.
pub fn tier_rank(tier: &str) -> Result<usize, String> {
    let normalized = normalize_tier(tier, "");
    TIERS
        .iter()
        .position(|candidate| *candidate == normalized)
        .ok_or_else(|| format!("invalid difficulty tier: {tier}"))
}

/// Next higher tier, capped at HARD. Invalid input becomes MODERATE.
#[must_use]
pub fn next_tier(tier: &str) -> String {
    let normalized = normalize_tier(tier, MODERATE);
    if normalized == HARD {
        HARD.to_owned()
    } else {
        TIERS[tier_rank(&normalized).unwrap_or(1) + 1].to_owned()
    }
}

/// Round cap for a tier.
#[must_use]
pub fn tier_ceiling(tier: &str) -> i64 {
    let _normalized = normalize_tier(tier, MODERATE);
    TIER_CEILING
}

/// Codex review role for a tier.
#[must_use]
pub fn codex_review_model_role(tier: &str) -> String {
    let _normalized = normalize_tier(tier, MODERATE);
    CODEX_MODEL_ROLE.to_owned()
}

/// Panel shape token for a tier.
#[must_use]
pub fn panel_shape_for_tier(tier: &str) -> &'static str {
    if normalize_tier(tier, MODERATE) == TRIVIAL {
        "singles"
    } else {
        "pairs"
    }
}

/// Threshold-panel token for a tier.
#[must_use]
pub fn threshold_panel_for_tier(tier: &str) -> &'static str {
    if normalize_tier(tier, MODERATE) == TRIVIAL {
        "simple"
    } else {
        "hard"
    }
}

/// Highest canonical tier among `tiers`, or TRIVIAL when none are valid.
#[must_use]
pub fn tier_max<'a>(tiers: impl IntoIterator<Item = &'a str>) -> String {
    let mut best = None::<usize>;
    let mut best_tier = TRIVIAL;
    for tier in tiers {
        if let Ok(rank) = tier_rank(tier)
            && best.is_none_or(|current| rank > current)
        {
            best = Some(rank);
            best_tier = TIERS[rank];
        }
    }
    best_tier.to_owned()
}

/// Bump one tier when confidence is low.
#[must_use]
pub fn bump_for_confidence(tier: &str, confidence: &str) -> String {
    if confidence != "low" || tier == HARD {
        tier.to_owned()
    } else {
        next_tier(tier)
    }
}

/// Strip controls, collapse whitespace, and cap rationale length.
#[must_use]
pub fn sanitize_rationale(value: &str, max_chars: usize) -> String {
    let mut cleaned = String::new();
    for character in value.chars() {
        if character == '\r' || character == '\n' || is_stripped_control(character) {
            cleaned.push(' ');
        } else {
            cleaned.push(character);
        }
    }
    let cleaned = cleaned.split_whitespace().collect::<Vec<_>>().join(" ");
    if cleaned.chars().count() > max_chars {
        let mut truncated: String = cleaned.chars().take(max_chars.saturating_sub(1)).collect();
        truncated = truncated.trim_end().to_owned();
        truncated.push('…');
        truncated
    } else {
        cleaned
    }
}

const fn is_stripped_control(character: char) -> bool {
    matches!(character as u32, 0x00..=0x08 | 0x0b | 0x0c | 0x0e..=0x1f | 0x7f)
}

/// Validate a raw rating object.
///
/// # Errors
/// Returns when the object is missing required fields or uses illegal tokens.
pub fn validate_rating_object(obj: &Value) -> Result<DifficultyRating, String> {
    let Value::Object(data) = obj else {
        return Err("rating must be a JSON object".to_owned());
    };
    let predicted = json_string(data.get("predicted_tier")).to_ascii_uppercase();
    let confidence = json_string(data.get("confidence")).to_ascii_lowercase();
    if !tier_valid(&predicted) {
        return Err("predicted_tier must be TRIVIAL, MODERATE, or HARD".to_owned());
    }
    if !CONFIDENCES.contains(&confidence.as_str()) {
        return Err("confidence must be low, medium, or high".to_owned());
    }
    let rationale = sanitize_rationale(&json_string(data.get("rationale")), RATIONALE_MAX_CHARS);
    if rationale.is_empty() {
        return Err("rationale must be non-empty after sanitization".to_owned());
    }
    Ok(DifficultyRating {
        predicted_tier: predicted.clone(),
        confidence: confidence.clone(),
        rationale,
        adjusted_tier: bump_for_confidence(&predicted, &confidence),
    })
}

/// Read a rating file, returning `None` for missing, symlink, or invalid input.
#[must_use]
pub fn read_rating_file(path: &Path) -> Option<DifficultyRating> {
    if !is_regular_file(path) {
        return None;
    }
    let text = fs::read_to_string(path).ok().unwrap_or_else(|| {
        String::from_utf8_lossy(&fs::read(path).unwrap_or_default()).into_owned()
    });
    let data: Value = serde_json::from_str(&text).ok()?;
    validate_rating_object(&data).ok()
}

/// Load the TSV floor manifest.
///
/// # Errors
/// Returns when the file cannot be read or a row is malformed.
pub fn load_floor_manifest(path: &Path) -> Result<Vec<DifficultyFloor>, String> {
    let text = fs::read_to_string(path)
        .map_err(|_| format!("difficulty floor manifest not readable: {}", path.display()))?;
    let mut rows = Vec::new();
    for (line_no, raw) in text.lines().enumerate() {
        let line_no = line_no + 1;
        if raw.trim().is_empty() || raw.starts_with('#') {
            continue;
        }
        let parts: Vec<&str> = raw.split('\t').collect();
        if parts.len() >= 3 && parts[0] == "glob" && parts[1] == "floor" && parts[2] == "reason" {
            continue;
        }
        if parts.len() < 3 {
            return Err(format!(
                "difficulty floor manifest row {line_no} must have glob, floor, reason"
            ));
        }
        let glob = parts[0].trim();
        let floor = parts[1].trim().to_ascii_uppercase();
        let reason = parts[2].trim();
        if glob.is_empty() || !tier_valid(&floor) || reason.is_empty() {
            return Err(format!(
                "difficulty floor manifest row {line_no} is invalid"
            ));
        }
        rows.push(DifficultyFloor {
            glob: glob.to_owned(),
            floor,
            reason: reason.to_owned(),
        });
    }
    Ok(rows)
}

/// Read changed-path lists, supporting NUL- or newline-separated files.
#[must_use]
pub fn read_changed_paths(path: Option<&Path>) -> Vec<String> {
    let Some(path) = path else {
        return Vec::new();
    };
    if !is_regular_file(path) {
        return Vec::new();
    }
    let Ok(raw) = fs::read(path) else {
        return Vec::new();
    };
    let values = if raw.contains(&0) {
        raw.split(|byte| *byte == 0)
            .map(|part| String::from_utf8_lossy(part).into_owned())
            .collect::<Vec<_>>()
    } else {
        String::from_utf8_lossy(&raw)
            .lines()
            .map(str::to_owned)
            .collect()
    };
    values
        .into_iter()
        .map(|value| value.trim().to_owned())
        .filter(|value| !value.is_empty())
        .collect()
}

/// Match changed paths against floor globs.
#[must_use]
pub fn match_floors(paths: &[String], floors: &[DifficultyFloor]) -> FloorResult {
    let mut matches = Vec::new();
    for changed in paths {
        for row in floors {
            if glob_matches(changed, &row.glob) {
                matches.push(FloorMatch {
                    path: changed.clone(),
                    glob: row.glob.clone(),
                    floor: row.floor.clone(),
                    reason: row.reason.clone(),
                });
            }
        }
    }
    if matches.is_empty() {
        FloorResult {
            tier: TRIVIAL.to_owned(),
            matches,
        }
    } else {
        let tier = tier_max(matches.iter().map(|row| row.floor.as_str()));
        FloorResult { tier, matches }
    }
}

/// Inputs for composing one difficulty record.
#[derive(Clone, Copy)]
pub struct BuildRecord<'a> {
    /// Rater identity.
    pub rater: &'a str,
    /// Rater tool.
    pub rater_tool: &'a str,
    /// Rater model.
    pub rater_model: &'a str,
    /// Optional design rating.
    pub design_rating: Option<&'a DifficultyRating>,
    /// Optional implement rating.
    pub implement_rating: Option<&'a DifficultyRating>,
    /// Optional fallback rating.
    pub fallback_rating: Option<&'a DifficultyRating>,
    /// Changed paths used for floors.
    pub changed_paths: &'a [String],
    /// Floor rows.
    pub floors: &'a [DifficultyFloor],
    /// Optional panel-skip reason.
    pub panel_skipped: &'a str,
    /// Optional audit-upgrade token.
    pub audit_upgrade: &'a str,
    /// Escalation entries.
    pub escalations: &'a [Value],
    /// Explicit override source.
    pub override_source: &'a str,
    /// Explicit override tier.
    pub override_tier: &'a str,
    /// Explicit panel tier.
    pub panel_tier: &'a str,
    /// Optional round cap.
    pub round_cap: Option<i64>,
    /// Optional Codex role.
    pub codex_model_role: &'a str,
    /// Optional audit-evaluated flag.
    pub audit_evaluated: Option<bool>,
    /// Optional escalated-round flag.
    pub escalated_round: Option<bool>,
}

/// Compose one record object.
///
/// # Errors
/// Returns when no rating source is present.
pub fn build_record(input: BuildRecord<'_>) -> Result<Map<String, Value>, String> {
    let source = input
        .implement_rating
        .or(input.design_rating)
        .or(input.fallback_rating)
        .ok_or_else(|| "at least one difficulty rating is required".to_owned())?;
    let mut model_tier = tier_max(
        [
            input
                .design_rating
                .map(|rating| rating.adjusted_tier.as_str()),
            input
                .implement_rating
                .map(|rating| rating.adjusted_tier.as_str()),
        ]
        .into_iter()
        .flatten(),
    );
    if model_tier == TRIVIAL
        && input.design_rating.is_none()
        && input.implement_rating.is_none()
        && let Some(fallback) = input.fallback_rating
    {
        model_tier.clone_from(&fallback.adjusted_tier);
    }
    let floors = match_floors(input.changed_paths, input.floors);
    let explicit_override = normalize_tier(input.override_tier, "");
    let mut applied = if explicit_override.is_empty() {
        tier_max([model_tier.as_str(), floors.tier.as_str()])
    } else {
        explicit_override.clone()
    };
    if input.audit_upgrade.eq_ignore_ascii_case("true") && applied != HARD {
        HARD.clone_into(&mut applied);
    }
    let derived_override = if !explicit_override.is_empty() {
        "operator"
    } else if !floors.matches.is_empty()
        && tier_rank(&floors.tier).unwrap_or(0) > tier_rank(&model_tier).unwrap_or(0)
    {
        "floor"
    } else {
        "none"
    };
    Ok(assembled_record(
        input,
        source,
        &applied,
        derived_override,
        &floors,
    ))
}

fn assembled_record(
    input: BuildRecord<'_>,
    source: &DifficultyRating,
    applied: &str,
    derived_override: &str,
    floors: &FloorResult,
) -> Map<String, Value> {
    let mut data = Map::new();
    insert_identity(&mut data, input, source);
    insert_resolution(&mut data, input, applied, derived_override, floors);
    data
}

fn insert_identity(
    data: &mut Map<String, Value>,
    input: BuildRecord<'_>,
    source: &DifficultyRating,
) {
    insert_value(data, "schema_version", Value::from(SCHEMA_VERSION));
    insert_value(data, "rater", Value::from(nonempty(input.rater, "unknown")));
    insert_value(
        data,
        "rater_tool",
        Value::from(nonempty(input.rater_tool, "unknown")),
    );
    insert_value(
        data,
        "rater_model",
        Value::from(nonempty(input.rater_model, "unknown")),
    );
    insert_value(
        data,
        "predicted_tier",
        Value::from(source.adjusted_tier.as_str()),
    );
    insert_value(data, "confidence", Value::from(source.confidence.as_str()));
    insert_value(data, "rationale", Value::from(source.rationale.as_str()));
    insert_value(
        data,
        "design_tier",
        option_str(
            input
                .design_rating
                .map(|rating| rating.adjusted_tier.as_str()),
        ),
    );
    insert_value(
        data,
        "implement_tier",
        option_str(
            input
                .implement_rating
                .map(|rating| rating.adjusted_tier.as_str()),
        ),
    );
}

fn insert_resolution(
    data: &mut Map<String, Value>,
    input: BuildRecord<'_>,
    applied: &str,
    derived_override: &str,
    floors: &FloorResult,
) {
    let effective_panel_tier = {
        let panel = normalize_tier(input.panel_tier, "");
        if panel.is_empty() {
            applied.to_owned()
        } else {
            panel
        }
    };
    let tier_cap = tier_ceiling(&effective_panel_tier);
    let effective_round_cap = input.round_cap.map_or(tier_cap, |cap| cap.min(tier_cap));
    let effective_codex_role = if input.codex_model_role.is_empty() {
        codex_review_model_role(&effective_panel_tier)
    } else {
        input.codex_model_role.to_owned()
    };
    insert_value(data, "applied_tier", Value::from(applied));
    insert_value(
        data,
        "override_source",
        Value::from(nonempty(input.override_source, derived_override)),
    );
    insert_value(
        data,
        "floors_applied",
        Value::Array(floors.matches.iter().map(floor_match_value).collect()),
    );
    insert_value(
        data,
        "audit_upgrade",
        if input.audit_upgrade.is_empty() {
            Value::Null
        } else {
            Value::from(input.audit_upgrade)
        },
    );
    insert_value(
        data,
        "escalations",
        Value::Array(input.escalations.to_vec()),
    );
    insert_value(
        data,
        "panel_skipped",
        if input.panel_skipped.is_empty() {
            Value::Null
        } else {
            Value::from(input.panel_skipped)
        },
    );
    insert_value(data, "panel_tier", Value::from(effective_panel_tier));
    insert_value(data, "round_cap", Value::from(effective_round_cap));
    insert_value(data, "codex_model_role", Value::from(effective_codex_role));
    insert_value(data, "audit_evaluated", option_bool(input.audit_evaluated));
    insert_value(data, "escalated_round", option_bool(input.escalated_round));
}

/// Merge persisted resolution fields into a newly built record.
#[must_use]
pub fn merge_existing_record_fields(
    mut record: Map<String, Value>,
    existing: &Map<String, Value>,
    explicit: &MergeExplicit<'_>,
) -> Map<String, Value> {
    if existing.is_empty() {
        return record;
    }
    let resolution_persisted = record_resolution_is_persisted(existing);
    let mut explicit_keys = Vec::new();
    if !explicit.override_source.is_empty() {
        explicit_keys.push("override_source");
    }
    if !explicit.audit_upgrade.is_empty() {
        explicit_keys.push("audit_upgrade");
    }
    if explicit.has_escalation {
        explicit_keys.push("escalations");
    }
    if !explicit.round_cap.is_empty() {
        explicit_keys.push("round_cap");
    }
    if !explicit.codex_model_role.is_empty() {
        explicit_keys.push("codex_model_role");
    }
    if !explicit.audit_evaluated.is_empty() {
        explicit_keys.push("audit_evaluated");
    }
    if !explicit.escalated_round.is_empty() {
        explicit_keys.push("escalated_round");
    }
    if !explicit.override_tier.is_empty() || !explicit.panel_tier.is_empty() {
        explicit_keys.extend(["applied_tier", "panel_tier"]);
    }
    for key in [
        "override_source",
        "audit_upgrade",
        "escalations",
        "applied_tier",
        "panel_tier",
        "round_cap",
        "codex_model_role",
        "audit_evaluated",
        "escalated_round",
    ] {
        if explicit_keys.contains(&key) {
            continue;
        }
        if matches!(
            key,
            "override_source"
                | "audit_upgrade"
                | "escalations"
                | "applied_tier"
                | "panel_tier"
                | "round_cap"
                | "codex_model_role"
                | "audit_evaluated"
                | "escalated_round"
        ) && !resolution_persisted
        {
            continue;
        }
        let Some(value) = existing.get(key) else {
            continue;
        };
        if is_empty_merge_value(value) {
            continue;
        }
        let _replaced = record.insert(key.to_owned(), value.clone());
    }
    if let Some(Value::Number(number)) = record.get("round_cap").cloned()
        && let Some(cap) = number.as_i64()
    {
        let cap_tier = {
            let panel = normalize_tier(&json_string(record.get("panel_tier")), "");
            if panel.is_empty() {
                normalize_tier(&json_string(record.get("applied_tier")), MODERATE)
            } else {
                panel
            }
        };
        let _replaced = record.insert(
            "round_cap".to_owned(),
            Value::from(cap.min(tier_ceiling(&cap_tier))),
        );
    }
    record
}

/// Explicit CLI overrides that must beat persisted resolution fields.
pub struct MergeExplicit<'a> {
    /// `--override-source`.
    pub override_source: &'a str,
    /// `--audit-upgrade`.
    pub audit_upgrade: &'a str,
    /// Whether `--escalation` was supplied.
    pub has_escalation: bool,
    /// `--round-cap`.
    pub round_cap: &'a str,
    /// `--codex-model-role`.
    pub codex_model_role: &'a str,
    /// `--audit-evaluated`.
    pub audit_evaluated: &'a str,
    /// `--escalated-round`.
    pub escalated_round: &'a str,
    /// `--override-tier`.
    pub override_tier: &'a str,
    /// `--panel-tier`.
    pub panel_tier: &'a str,
}

/// Empty explicit-override set used when refreshing an existing record.
#[must_use]
pub const fn blank_merge_explicit<'a>() -> MergeExplicit<'a> {
    MergeExplicit {
        override_source: "",
        audit_upgrade: "",
        has_escalation: false,
        round_cap: "",
        codex_model_role: "",
        audit_evaluated: "",
        escalated_round: "",
        override_tier: "",
        panel_tier: "",
    }
}

/// Load a record object, or an empty map when missing or invalid.
#[must_use]
pub fn load_record_data(path: &Path) -> Map<String, Value> {
    if !is_regular_file(path) {
        return Map::new();
    }
    let Ok(bytes) = fs::read(path) else {
        return Map::new();
    };
    let text = String::from_utf8_lossy(&bytes);
    match serde_json::from_str::<Value>(&text) {
        Ok(Value::Object(data)) => data,
        _ => Map::new(),
    }
}

/// Atomically write one JSON record.
///
/// # Errors
/// Returns when the write cannot be confined or replaced.
pub fn write_record_map(path: &Path, data: &Map<String, Value>) -> Result<(), String> {
    let parent = path.parent().unwrap_or_else(|| Path::new("."));
    private_atomic_write(path, &dump_record(data), parent).map_err(|error| error.to_string())
}

/// Render a record the way Python `json.dumps(..., indent=2, sort_keys=True)` did.
#[must_use]
pub fn dump_record(data: &Map<String, Value>) -> String {
    let rendered = serde_json::to_string_pretty(&sort_json(Value::Object(data.clone())))
        .unwrap_or_else(|_| "{\n}".to_owned());
    ensure_ascii_json(&rendered) + "\n"
}

fn sort_json(value: Value) -> Value {
    match value {
        Value::Object(map) => {
            let mut keys: Vec<String> = map.keys().cloned().collect();
            keys.sort();
            let mut sorted = Map::new();
            for key in keys {
                if let Some(item) = map.get(&key) {
                    let _inserted = sorted.insert(key, sort_json(item.clone()));
                }
            }
            Value::Object(sorted)
        }
        Value::Array(items) => Value::Array(items.into_iter().map(sort_json).collect()),
        other => other,
    }
}

/// Resolve panel fields, persist them, and return the resolution.
///
/// # Errors
/// Returns when the record cannot be written.
pub fn resolve_panel_tier(
    record_path: &Path,
    override_tier: &str,
    roll: Option<i64>,
    audit_enabled: bool,
    round_num: Option<i64>,
) -> Result<TierResolution, String> {
    let mut data = load_record_data(record_path);
    let override_tier = normalize_tier(override_tier, "");
    if let Some(existing) = resolution_from_data(&data, round_num) {
        let resolved_once = data
            .get("audit_evaluated")
            .is_some_and(|value| !value.is_null())
            || data
                .get("audit_upgrade")
                .is_some_and(|value| !value.is_null())
            || !record_escalations_for_round(&data, None).is_empty();
        if resolved_once && override_tier.is_empty() {
            return Ok(existing);
        }
    }
    let override_source = if override_tier.is_empty() {
        nonempty(&json_string(data.get("override_source")), "none")
    } else {
        "operator".to_owned()
    };
    let starting = if override_tier.is_empty() {
        resolve_applied_tier(&data, MODERATE)
    } else {
        override_tier
    };
    let (audit_evaluated, audit_upgrade) =
        if !json_bool(data.get("audit_evaluated")) && audit_enabled {
            let decision_roll = if roll.is_some() {
                roll
            } else if data.is_empty() {
                Some(AUDIT_DENOMINATOR)
            } else {
                None
            };
            let decision = maybe_audit_upgrade(&starting, decision_roll);
            (decision.evaluated, decision.upgrade)
        } else {
            (
                json_bool(data.get("audit_evaluated")),
                json_truthy_upgrade(data.get("audit_upgrade")),
            )
        };
    let panel_tier = if audit_upgrade && starting != HARD {
        HARD.to_owned()
    } else {
        starting.clone()
    };
    let resolution = TierResolution {
        panel_tier: panel_tier.clone(),
        round_cap: tier_ceiling(&panel_tier),
        codex_model_role: codex_review_model_role(&panel_tier),
        audit_evaluated,
        audit_upgrade,
        override_source,
        escalated_round: json_bool(data.get("escalated_round")),
    };
    if data.is_empty() {
        data = fallback_record_object(&starting, FALLBACK_PANEL_RATIONALE);
    }
    let _replaced = data.insert("applied_tier".to_owned(), Value::from(panel_tier));
    let _replaced = data.insert(
        "panel_tier".to_owned(),
        Value::from(resolution.panel_tier.as_str()),
    );
    let _replaced = data.insert("round_cap".to_owned(), Value::from(resolution.round_cap));
    let _replaced = data.insert(
        "codex_model_role".to_owned(),
        Value::from(resolution.codex_model_role.as_str()),
    );
    let _replaced = data.insert(
        "audit_evaluated".to_owned(),
        Value::from(resolution.audit_evaluated),
    );
    let _replaced = data.insert(
        "audit_upgrade".to_owned(),
        if resolution.audit_upgrade {
            Value::from("true")
        } else {
            Value::Null
        },
    );
    let _replaced = data.insert(
        "override_source".to_owned(),
        Value::from(resolution.override_source.as_str()),
    );
    let _replaced = data.insert(
        "escalated_round".to_owned(),
        Value::from(resolution.escalated_round),
    );
    write_record_map(record_path, &data)?;
    Ok(resolution)
}

/// One audit decision.
pub struct AuditDecision {
    /// Whether a roll happened.
    pub evaluated: bool,
    /// Whether the roll upgraded.
    pub upgrade: bool,
}

/// Sample or apply a supplied audit roll.
#[must_use]
pub fn maybe_audit_upgrade(tier: &str, roll: Option<i64>) -> AuditDecision {
    let normalized = normalize_tier(tier, MODERATE);
    if normalized == HARD {
        return AuditDecision {
            evaluated: false,
            upgrade: false,
        };
    }
    let roll = roll.unwrap_or(AUDIT_DENOMINATOR);
    AuditDecision {
        evaluated: true,
        upgrade: roll == 1,
    }
}

/// Plan-trailer difficulty, including the adjacent-invalid-tier refusal.
#[must_use]
pub fn plan_difficulty(text: &str) -> String {
    let trailing = trailing_plan_difficulty(text);
    if !trailing.is_empty() {
        return trailing;
    }
    if adjacent_invalid_difficulty(text) {
        return String::new();
    }
    last_plan_difficulty_line(text)
}

/// Difficulty from the final contiguous trailer block only.
#[must_use]
pub fn trailing_plan_difficulty(text: &str) -> String {
    for line in trailing_plan_metadata_lines(text).into_iter().rev() {
        if let Some((key, value)) = match_trailer_line(line.trim())
            && key == "difficulty"
        {
            return value;
        }
    }
    String::new()
}

/// Trailing contiguous valid trailer lines.
#[must_use]
pub fn trailing_plan_metadata_lines(text: &str) -> Vec<String> {
    let lines: Vec<String> = text.lines().map(str::to_owned).collect();
    let Some((start, end)) = trailing_metadata_span(&lines) else {
        return Vec::new();
    };
    lines[start..end].to_vec()
}

/// `difficulty:<tier>` label.
///
/// # Errors
/// Returns when `tier` is not canonical.
pub fn label_for_tier(tier: &str) -> Result<String, String> {
    if !tier_valid(tier) {
        return Err(format!("invalid difficulty tier: {tier}"));
    }
    Ok(format!("difficulty:{}", tier.to_ascii_lowercase()))
}

/// Every known difficulty label.
#[must_use]
pub fn known_labels() -> Vec<String> {
    TIERS
        .iter()
        .map(|tier| format!("difficulty:{}", tier.to_ascii_lowercase()))
        .collect()
}

/// Rating synthesized from a wire tier.
#[must_use]
pub fn rating_from_tier(tier: &str, rationale: &str) -> Option<DifficultyRating> {
    if !tier_valid(tier) {
        return None;
    }
    let rationale = sanitize_rationale(rationale, RATIONALE_MAX_CHARS);
    Some(DifficultyRating {
        predicted_tier: tier.to_owned(),
        confidence: "medium".to_owned(),
        rationale: if rationale.is_empty() {
            "wire metadata".to_owned()
        } else {
            rationale
        },
        adjusted_tier: tier.to_owned(),
    })
}

/// One-line human summary of a record.
#[must_use]
pub fn difficulty_line(data: &Map<String, Value>) -> String {
    let predicted = nonempty(&json_string(data.get("predicted_tier")), "unknown");
    let applied = nonempty(&json_string(data.get("applied_tier")), &predicted);
    let mut parts = vec![
        format!("predicted {predicted}"),
        format!("applied {applied}"),
    ];
    if let Some(Value::Array(floors)) = data.get("floors_applied")
        && !floors.is_empty()
    {
        parts.push(
            if applied == predicted {
                "floor checked"
            } else {
                "floor raised"
            }
            .to_owned(),
        );
    }
    let audit = json_string(data.get("audit_upgrade"));
    if !audit.is_empty() {
        parts.push(format!("audit {audit}"));
    }
    if json_string(data.get("override_source")) == "operator" {
        parts.push("override operator".to_owned());
    }
    if let Some(Value::Array(escalations)) = data.get("escalations")
        && !escalations.is_empty()
    {
        let rendered: Vec<String> = escalations
            .iter()
            .map(|item| match item {
                Value::Object(entry) => {
                    let round = nonempty(&json_string(entry.get("round")), "?");
                    let from = nonempty(&json_string(entry.get("from_tier")), "?");
                    let to = nonempty(&json_string(entry.get("to_tier")), "?");
                    let trigger = json_string(entry.get("trigger"));
                    let suffix = if trigger.is_empty() {
                        String::new()
                    } else {
                        format!(" {trigger}")
                    };
                    format!("r{round} {from}->{to}{suffix}")
                }
                other => other.to_string(),
            })
            .collect();
        parts.push(format!("escalated {}", rendered.join(", ")));
    }
    let skipped = json_string(data.get("panel_skipped"));
    if !skipped.is_empty() {
        parts.push(format!("panel skipped: {skipped}"));
    }
    parts.join("; ")
}

/// Refresh floors on an existing record without replacing resolution fields.
///
/// # Errors
/// Returns when the existing record is not a valid rating or cannot be written.
pub fn refresh_existing_record(
    path: &Path,
    changed_paths: &[String],
    floors: &[DifficultyFloor],
) -> Result<Map<String, Value>, String> {
    let existing = load_record_data(path);
    let rating = validate_rating_object(&Value::Object(existing.clone()))?;
    let rater = nonempty(&json_string(existing.get("rater")), "unknown");
    let rater_tool = nonempty(&json_string(existing.get("rater_tool")), "unknown");
    let rater_model = nonempty(&json_string(existing.get("rater_model")), "unknown");
    let escalations = match existing.get("escalations") {
        Some(Value::Array(items)) => items.clone(),
        _ => Vec::new(),
    };
    let panel_skipped = json_string(existing.get("panel_skipped"));
    let audit_upgrade = json_string(existing.get("audit_upgrade"));
    let mut input = BuildRecord {
        rater: &rater,
        rater_tool: &rater_tool,
        rater_model: &rater_model,
        design_rating: None,
        implement_rating: None,
        fallback_rating: None,
        changed_paths,
        floors,
        panel_skipped: &panel_skipped,
        audit_upgrade: &audit_upgrade,
        escalations: &escalations,
        override_source: "",
        override_tier: "",
        panel_tier: "",
        round_cap: None,
        codex_model_role: "",
        audit_evaluated: None,
        escalated_round: None,
    };
    if rater == "implement" {
        input.implement_rating = Some(&rating);
    } else if rater == "fallback" {
        input.fallback_rating = Some(&rating);
    } else {
        input.design_rating = Some(&rating);
    }
    let built = build_record(input)?;
    Ok(merge_existing_record_fields(
        built,
        &existing,
        &blank_merge_explicit(),
    ))
}

fn resolve_applied_tier(data: &Map<String, Value>, fallback: &str) -> String {
    for key in ["applied_tier", "adjusted_tier", "predicted_tier"] {
        let tier = normalize_tier(&json_string(data.get(key)), "");
        if !tier.is_empty() {
            return tier;
        }
    }
    normalize_tier(fallback, MODERATE)
}

fn resolution_from_data(
    data: &Map<String, Value>,
    round_num: Option<i64>,
) -> Option<TierResolution> {
    let panel_tier = normalize_tier(&json_string(data.get("panel_tier")), "");
    if panel_tier.is_empty() {
        return None;
    }
    let round_escalations = if round_num.is_some() {
        record_escalations_for_round(data, round_num)
    } else {
        Vec::new()
    };
    let tier_cap = tier_ceiling(&panel_tier);
    let round_cap = data
        .get("round_cap")
        .and_then(Value::as_i64)
        .map_or(tier_cap, |cap| cap.min(tier_cap));
    Some(TierResolution {
        panel_tier: panel_tier.clone(),
        round_cap,
        codex_model_role: {
            let role = json_string(data.get("codex_model_role"));
            if role.is_empty() {
                codex_review_model_role(&panel_tier)
            } else {
                role
            }
        },
        audit_evaluated: json_bool(data.get("audit_evaluated")),
        audit_upgrade: json_truthy_upgrade(data.get("audit_upgrade")),
        override_source: nonempty(&json_string(data.get("override_source")), "none"),
        escalated_round: if round_num.is_some() {
            !round_escalations.is_empty()
        } else {
            json_bool(data.get("escalated_round"))
        },
    })
}

fn record_resolution_is_persisted(data: &Map<String, Value>) -> bool {
    json_string(data.get("override_source")) == "operator"
        || data
            .get("audit_evaluated")
            .is_some_and(|value| !value.is_null())
        || data
            .get("audit_upgrade")
            .is_some_and(|value| !value.is_null())
        || !record_escalations_for_round(data, None).is_empty()
}

fn record_escalations_for_round(data: &Map<String, Value>, round_num: Option<i64>) -> Vec<Value> {
    let Some(Value::Array(items)) = data.get("escalations") else {
        return Vec::new();
    };
    let Some(round_num) = round_num else {
        return items.clone();
    };
    items
        .iter()
        .filter(|item| {
            item.as_object().is_some_and(|entry| {
                json_string(entry.get("round"))
                    .parse::<i64>()
                    .ok()
                    .is_some_and(|value| value == round_num)
            })
        })
        .cloned()
        .collect()
}

fn fallback_record_object(starting: &str, rationale: &str) -> Map<String, Value> {
    let mut data = Map::new();
    insert_value(&mut data, "schema_version", Value::from(SCHEMA_VERSION));
    insert_value(&mut data, "rater", Value::from("fallback"));
    insert_value(&mut data, "rater_tool", Value::from("unknown"));
    insert_value(&mut data, "rater_model", Value::from("unknown"));
    insert_value(&mut data, "predicted_tier", Value::from(starting));
    insert_value(&mut data, "confidence", Value::from("medium"));
    insert_value(&mut data, "rationale", Value::from(rationale));
    insert_value(&mut data, "design_tier", Value::Null);
    insert_value(&mut data, "implement_tier", Value::Null);
    insert_value(&mut data, "floors_applied", Value::Array(Vec::new()));
    insert_value(&mut data, "panel_skipped", Value::Null);
    insert_value(&mut data, "escalations", Value::Array(Vec::new()));
    data
}

fn trailing_metadata_span(lines: &[String]) -> Option<(usize, usize)> {
    let joined = lines.join("\n");
    let trailers = parse_final_trailers(&joined);
    if trailers.is_empty() {
        return None;
    }
    let mut end = lines.len();
    while end > 0 && lines[end - 1].trim().is_empty() {
        end -= 1;
    }
    Some((end.saturating_sub(trailers.len()), end))
}

/// Split `text` into lines while retaining each line's terminator.
fn split_keepends(text: &str) -> Vec<String> {
    let mut out: Vec<String> = Vec::new();
    let mut rest = text;
    while let Some(index) = rest.find('\n') {
        out.push(rest[..=index].to_owned());
        rest = &rest[index + 1..];
    }
    if !rest.is_empty() {
        out.push(rest.to_owned());
    }
    out
}

/// Rewrite (or insert) the plan's trailing `difficulty:` line to `tier`.
///
/// A verbatim port of the Python `rewrite_plan_difficulty`: the difficulty line
/// inside the final contiguous trailer block is replaced in place, or inserted
/// above any `diff_lines:` trailer when absent. Returns `text` unchanged when
/// `tier` is not canonical or the plan carries no trailer block.
#[must_use]
pub fn rewrite_plan_difficulty(text: &str, tier: &str) -> String {
    if !tier_valid(tier) {
        return text.to_owned();
    }
    let plain: Vec<String> = text.lines().map(str::to_owned).collect();
    let Some((start, end)) = trailing_metadata_span(&plain) else {
        return text.to_owned();
    };
    let mut lines = split_keepends(text);
    if end > lines.len() {
        return text.to_owned();
    }
    for line in lines.iter_mut().take(end).skip(start) {
        if line.starts_with("difficulty:") {
            let newline = if line.ends_with('\n') { "\n" } else { "" };
            *line = format!("difficulty: {tier}{newline}");
            return lines.concat();
        }
    }
    let mut insert_at = end;
    while insert_at > start && lines[insert_at - 1].starts_with("diff_lines:") {
        insert_at -= 1;
    }
    lines.insert(insert_at, format!("difficulty: {tier}\n"));
    lines.concat()
}

fn parse_final_trailers(text: &str) -> Vec<(String, String, String)> {
    let mut lines: Vec<&str> = text.lines().collect();
    while lines.last().is_some_and(|line| line.trim().is_empty()) {
        let _removed = lines.pop();
    }
    let mut trailers = Vec::new();
    for line in lines.iter().rev() {
        let Some(parsed) = match_trailer_line(line) else {
            break;
        };
        trailers.push((parsed.0.to_owned(), parsed.1, line.to_string()));
    }
    trailers.reverse();
    trailers
}

fn match_trailer_line(line: &str) -> Option<(&'static str, String)> {
    let captured = TRAILER_LINE_RE.captures(line.trim_end_matches(['\r', '\n']))?;
    let key = captured.get(1)?.as_str();
    let value = captured.get(2)?.as_str();
    parse_trailer_value(key, value)?;
    Some((
        match key {
            "review_status" => "review_status",
            "rounds_completed" => "rounds_completed",
            "difficulty" => "difficulty",
            "diff_added" => "diff_added",
            "diff_deleted" => "diff_deleted",
            "mechanical_churn" => "mechanical_churn",
            "oversize_override" => "oversize_override",
            "diff_lines" => "diff_lines",
            _ => return None,
        },
        value.to_owned(),
    ))
}

fn parse_trailer_value(key: &str, value: &str) -> Option<()> {
    match key {
        "rounds_completed" | "diff_lines" => DIGITS_RE
            .captures(value)
            .and_then(|captured| (captured.get(0)?.as_str() == value).then_some(())),
        "diff_added" | "diff_deleted" => SIZE_INTEGER_RE
            .captures(value)
            .and_then(|captured| (captured.get(0)?.as_str() == value).then_some(())),
        "difficulty" => ["TRIVIAL", "MODERATE", "HARD"]
            .contains(&value)
            .then_some(()),
        "mechanical_churn" => matches!(value, "true" | "false").then_some(()),
        "oversize_override" => (value == "operator").then_some(()),
        "review_status" => (!value.trim().is_empty()).then_some(()),
        _ => Some(()),
    }
}

fn last_plan_difficulty_line(text: &str) -> String {
    for line in text.lines().rev() {
        if let Some((key, value)) = match_trailer_line(line.trim())
            && key == "difficulty"
        {
            return value;
        }
    }
    String::new()
}

fn adjacent_invalid_difficulty(text: &str) -> bool {
    let lines: Vec<String> = text.lines().map(str::to_owned).collect();
    let mut idx = trailing_metadata_span(&lines).map_or(lines.len(), |(start, _end)| start);
    while idx > 0 {
        let line = lines[idx - 1].trim();
        if line.is_empty()
            || match_trailer_line(line).is_some()
            || LEGACY_CONFIDENCE_RE.captures(line).is_some()
        {
            idx -= 1;
            continue;
        }
        return line.starts_with("difficulty:")
            && match_trailer_line(line).is_none_or(|(key, _value)| key != "difficulty");
    }
    false
}

fn is_regular_file(path: &Path) -> bool {
    fs::symlink_metadata(path).is_ok_and(|metadata| metadata.is_file())
}

fn json_string(value: Option<&Value>) -> String {
    value.map_or(String::new(), |item| match item {
        Value::String(text) => text.clone(),
        Value::Number(number) => number.to_string(),
        Value::Bool(flag) => flag.to_string(),
        Value::Null => String::new(),
        other => other.to_string(),
    })
}

fn json_bool(value: Option<&Value>) -> bool {
    match value {
        Some(Value::Bool(flag)) => *flag,
        Some(Value::String(text)) => text.eq_ignore_ascii_case("true"),
        _ => false,
    }
}

fn json_truthy_upgrade(value: Option<&Value>) -> bool {
    match value {
        Some(Value::Bool(true)) => true,
        Some(Value::String(text)) => text.eq_ignore_ascii_case("true"),
        _ => false,
    }
}

fn option_str(value: Option<&str>) -> Value {
    value.map_or(Value::Null, Value::from)
}

fn option_bool(value: Option<bool>) -> Value {
    value.map_or(Value::Null, Value::from)
}

fn nonempty(value: &str, fallback: &str) -> String {
    if value.is_empty() {
        fallback.to_owned()
    } else {
        value.to_owned()
    }
}

fn insert_value(data: &mut Map<String, Value>, key: &str, value: Value) {
    let _replaced = data.insert(key.to_owned(), value);
}

fn floor_match_value(row: &FloorMatch) -> Value {
    let mut item = Map::new();
    insert_value(&mut item, "floor", Value::from(row.floor.as_str()));
    insert_value(&mut item, "glob", Value::from(row.glob.as_str()));
    insert_value(&mut item, "path", Value::from(row.path.as_str()));
    insert_value(&mut item, "reason", Value::from(row.reason.as_str()));
    Value::Object(item)
}

const fn is_empty_merge_value(value: &Value) -> bool {
    match value {
        Value::Null => true,
        Value::String(text) => text.is_empty(),
        Value::Array(items) => items.is_empty(),
        _ => false,
    }
}

#[cfg(test)]
mod tests {
    use super::{
        AUDIT_DENOMINATOR, BuildRecord, DifficultyFloor, HARD, MODERATE, RUBRIC, SCHEMA_VERSION,
        TRIVIAL, blank_merge_explicit, build_record, bump_for_confidence, codex_review_model_role,
        difficulty_line, dump_record, known_labels, label_for_tier, load_floor_manifest,
        load_record_data, match_floors, maybe_audit_upgrade, merge_existing_record_fields,
        next_tier, normalize_tier, panel_shape_for_tier, plan_difficulty, rating_from_tier,
        read_changed_paths, read_rating_file, refresh_existing_record, resolve_panel_tier,
        sanitize_rationale, threshold_panel_for_tier, tier_ceiling, tier_max, tier_rank,
        rewrite_plan_difficulty, tier_valid, trailing_plan_difficulty, trailing_plan_metadata_lines,
        validate_rating_object, write_record_map,
    };
    use serde_json::{Map, json};

    #[test]
    fn rewrite_plan_difficulty_replaces_in_place() {
        let plan = "## Plan\n\nDo it.\n\ndifficulty: MODERATE\n";
        assert_eq!(
            rewrite_plan_difficulty(plan, HARD),
            "## Plan\n\nDo it.\n\ndifficulty: HARD\n",
        );
    }

    #[test]
    fn rewrite_plan_difficulty_inserts_above_diff_lines() {
        let plan = "## Plan\n\nDo it.\n\ndiff_lines: 12\n";
        assert_eq!(
            rewrite_plan_difficulty(plan, MODERATE),
            "## Plan\n\nDo it.\n\ndifficulty: MODERATE\ndiff_lines: 12\n",
        );
    }

    #[test]
    fn rewrite_plan_difficulty_no_trailing_newline_is_stable() {
        let plan = "## Plan\n\nDo it.\n\ndifficulty: MODERATE";
        assert_eq!(
            rewrite_plan_difficulty(plan, HARD),
            "## Plan\n\nDo it.\n\ndifficulty: HARD",
        );
    }

    #[test]
    fn rewrite_plan_difficulty_ignores_invalid_tier_and_missing_trailers() {
        let plan = "## Plan\n\ndifficulty: MODERATE\n";
        assert_eq!(rewrite_plan_difficulty(plan, "BOGUS"), plan);
        assert_eq!(rewrite_plan_difficulty("just prose\n", HARD), "just prose\n");
    }
    use std::path::Path;
    use tempfile::TempDir;

    fn rating(tier: &str, confidence: &str, rationale: &str) -> super::DifficultyRating {
        validate_rating_object(&json!({
            "predicted_tier": tier,
            "confidence": confidence,
            "rationale": rationale,
        }))
        .expect("rating")
    }

    fn record_input<'a>(
        rater: &'a str,
        design: Option<&'a super::DifficultyRating>,
        implement: Option<&'a super::DifficultyRating>,
        fallback: Option<&'a super::DifficultyRating>,
        paths: &'a [String],
        floors: &'a [DifficultyFloor],
        override_tier: &'a str,
    ) -> BuildRecord<'a> {
        BuildRecord {
            rater,
            rater_tool: "claude",
            rater_model: "sonnet",
            design_rating: design,
            implement_rating: implement,
            fallback_rating: fallback,
            changed_paths: paths,
            floors,
            panel_skipped: "",
            audit_upgrade: "",
            escalations: &[],
            override_source: "",
            override_tier,
            panel_tier: "",
            round_cap: None,
            codex_model_role: "",
            audit_evaluated: None,
            escalated_round: None,
        }
    }

    #[test]
    fn low_confidence_bumps_and_sanitizes() {
        let rating = validate_rating_object(&json!({
            "predicted_tier": "trivial",
            "confidence": "low",
            "rationale": "line\nwith\tcontrols",
        }))
        .expect("rating");
        assert_eq!(rating.predicted_tier, TRIVIAL);
        assert_eq!(rating.adjusted_tier, MODERATE);
        assert_eq!(rating.rationale, "line with controls");
        assert_eq!(bump_for_confidence(HARD, "low"), HARD);
        assert!(sanitize_rationale("x".repeat(600).as_str(), 500).ends_with('…'));
    }

    #[test]
    fn floors_raise_only() {
        let floors = [DifficultyFloor {
            glob: "hooks/**".to_owned(),
            floor: MODERATE.to_owned(),
            reason: "hook".to_owned(),
        }];
        let result = match_floors(&["hooks/pre-tool-use.sh".to_owned()], &floors);
        assert_eq!(result.tier, MODERATE);
        assert_eq!(tier_max(["TRIVIAL", "HARD"]), HARD);
        assert_eq!(normalize_tier(" moderate ", ""), MODERATE);
        assert_eq!(label_for_tier(HARD).expect("label"), "difficulty:hard");
        assert!(!maybe_audit_upgrade(HARD, Some(1)).evaluated);
        assert!(maybe_audit_upgrade(MODERATE, Some(1)).upgrade);
        assert!(!maybe_audit_upgrade(MODERATE, Some(AUDIT_DENOMINATOR)).upgrade);
    }

    #[test]
    fn plan_difficulty_prefers_trailing_tier() {
        let text = "body\ndifficulty: TRIVIAL\n\nreview_status: complete\ndifficulty: HARD\ndiff_lines: 9\n";
        assert_eq!(plan_difficulty(text), HARD);
        assert_eq!(
            trailing_plan_difficulty(
                "difficulty: MODERATE\nbody\n\nreview_status: complete\ndiff_lines: 9\n"
            ),
            ""
        );
        assert_eq!(
            plan_difficulty("difficulty: MODERATE\nbody\n\ndifficulty: EASY\ndiff_lines: 9\n"),
            ""
        );
        assert_eq!(
            plan_difficulty("difficulty: HARD\nbody\n\ndifficulty: MODERATE\nconfidence: high\n"),
            MODERATE
        );
    }

    #[test]
    fn difficulty_line_renders_escalations() {
        let mut data = serde_json::Map::new();
        let _ = data.insert("predicted_tier".to_owned(), json!("MODERATE"));
        let _ = data.insert("applied_tier".to_owned(), json!("HARD"));
        let _ = data.insert(
            "escalations".to_owned(),
            json!([{"round": 2, "from_tier": "MODERATE", "to_tier": "HARD", "trigger": "high-severity"}]),
        );
        assert!(difficulty_line(&data).contains("MODERATE->HARD"));
        assert!(RUBRIC.contains("TRIVIAL:"));
    }

    #[test]
    fn floor_manifest_parses_checked_in_table() {
        let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
        let rows =
            load_floor_manifest(&root.join("docs/difficulty-floor-globs.tsv")).expect("manifest");
        assert!(rows.iter().any(|row| row.glob == "hooks/**"));
        let dir = TempDir::new().expect("temp");
        assert!(load_floor_manifest(&dir.path().join("missing.tsv")).is_err());
    }

    #[test]
    fn validate_rating_rejects_invalid_tiers() {
        for tier in ["", "EASY", "harder"] {
            assert!(
                validate_rating_object(&json!({
                    "predicted_tier": tier,
                    "confidence": "medium",
                    "rationale": "x",
                }))
                .is_err(),
                "{tier}"
            );
        }
        assert!(!tier_valid("EASY"));
        assert!(read_rating_file(Path::new("/no/such/rating.json")).is_none());
        assert!(rating_from_tier("EASY", "x").is_none());
        assert_eq!(
            rating_from_tier(HARD, "wire")
                .expect("rating")
                .predicted_tier,
            HARD
        );
    }

    #[test]
    fn build_record_applies_floors_and_ignores_weaker_fallback() {
        let floors = [DifficultyFloor {
            glob: "hooks/**".to_owned(),
            floor: MODERATE.to_owned(),
            reason: "hook".to_owned(),
        }];
        let implement = rating("TRIVIAL", "high", "small hook edit");
        let paths = ["hooks/pre-tool-use.sh".to_owned()];
        let raised = build_record(record_input(
            "implement",
            None,
            Some(&implement),
            None,
            &paths,
            &floors,
            "",
        ))
        .expect("record");
        assert_eq!(raised["predicted_tier"], json!(TRIVIAL));
        assert_eq!(raised["applied_tier"], json!(MODERATE));
        assert_eq!(raised["override_source"], json!("floor"));
        assert_eq!(raised["schema_version"], json!(SCHEMA_VERSION));

        let design = rating("TRIVIAL", "high", "small doc edit");
        let fallback = rating("MODERATE", "medium", "recovery fallback");
        let kept = build_record(record_input(
            "fallback",
            Some(&design),
            None,
            Some(&fallback),
            &[],
            &[],
            "",
        ))
        .expect("record");
        assert_eq!(kept["predicted_tier"], json!(TRIVIAL));
        assert_eq!(kept["applied_tier"], json!(TRIVIAL));
        assert_eq!(kept["override_source"], json!("none"));
        assert!(build_record(record_input("design", None, None, None, &[], &[], "")).is_err());
    }

    #[test]
    fn write_and_refresh_records_round_trip() {
        let dir = TempDir::new().expect("temp");
        let path = dir.path().join("difficulty-rating.json");
        let design = rating("MODERATE", "medium", "plan changes workflow");
        let record = build_record(record_input(
            "design",
            Some(&design),
            None,
            None,
            &[],
            &[],
            "",
        ))
        .expect("record");
        write_record_map(&path, &record).expect("write");
        let data = load_record_data(&path);
        assert_eq!(data["design_tier"], json!(MODERATE));
        assert_eq!(data["applied_tier"], json!(MODERATE));
        assert!(dump_record(&data).contains("MODERATE"));

        let floors = [DifficultyFloor {
            glob: "hooks/**".to_owned(),
            floor: MODERATE.to_owned(),
            reason: "hook".to_owned(),
        }];
        let implement = rating("TRIVIAL", "high", "small");
        write_record_map(
            &path,
            &build_record(record_input(
                "implement",
                None,
                Some(&implement),
                None,
                &[],
                &[],
                "",
            ))
            .expect("seed"),
        )
        .expect("seed");
        let refreshed =
            refresh_existing_record(&path, &["hooks/pre-tool-use.sh".to_owned()], &floors)
                .expect("refresh");
        assert_eq!(refreshed["override_source"], json!("floor"));
        assert!(load_record_data(&dir.path().join("missing.json")).is_empty());
        assert!(read_changed_paths(None).is_empty());
        let list = dir.path().join("paths.txt");
        std::fs::write(&list, "hooks/a.sh\n\nskills/x.md\n").expect("paths");
        assert_eq!(
            read_changed_paths(Some(&list)),
            vec!["hooks/a.sh".to_owned(), "skills/x.md".to_owned()]
        );
        let nul = dir.path().join("nul.txt");
        std::fs::write(&nul, b"hooks/a.sh\0skills/x.md\0").expect("nul");
        assert_eq!(
            read_changed_paths(Some(&nul)),
            vec!["hooks/a.sh".to_owned(), "skills/x.md".to_owned()]
        );
        let rating_path = dir.path().join("rating.json");
        std::fs::write(
            &rating_path,
            json!({
                "predicted_tier": "HARD",
                "confidence": "high",
                "rationale": "wide"
            })
            .to_string(),
        )
        .expect("rating file");
        assert_eq!(
            read_rating_file(&rating_path)
                .expect("rating")
                .predicted_tier,
            HARD
        );
        let bad_floors = dir.path().join("floors.tsv");
        std::fs::write(&bad_floors, "glob\tfloor\treason\nhooks/**\tEASY\thook\n")
            .expect("bad floors");
        assert!(load_floor_manifest(&bad_floors).is_err());
        std::fs::write(&bad_floors, "only-one-column\n").expect("short floors");
        assert!(load_floor_manifest(&bad_floors).is_err());
    }

    #[test]
    fn operator_override_and_panel_resolution_upgrade() {
        let dir = TempDir::new().expect("temp");
        let path = dir.path().join("difficulty-rating.json");
        let implement = rating("TRIVIAL", "high", "small");
        let record = build_record(record_input(
            "implement",
            None,
            Some(&implement),
            None,
            &["hooks/pre-tool-use.sh".to_owned()],
            &[DifficultyFloor {
                glob: "hooks/**".to_owned(),
                floor: MODERATE.to_owned(),
                reason: "hook".to_owned(),
            }],
            "TRIVIAL",
        ))
        .expect("record");
        write_record_map(&path, &record).expect("write");
        let resolved = resolve_panel_tier(&path, "TRIVIAL", Some(1), true, None).expect("resolve");
        let data = load_record_data(&path);
        assert_eq!(resolved.panel_tier, HARD);
        assert!(resolved.audit_upgrade);
        assert_eq!(data["override_source"], json!("operator"));
        assert_eq!(data["audit_upgrade"], json!("true"));

        let recomputed = resolve_panel_tier(&path, "HARD", Some(1), true, None).expect("recompute");
        assert_eq!(recomputed.panel_tier, HARD);
        assert_eq!(recomputed.codex_model_role, codex_review_model_role(HARD));
    }

    #[test]
    fn merge_preserves_resolution_and_clamps_helpers() {
        assert_eq!(tier_ceiling(TRIVIAL), 2);
        assert_eq!(tier_ceiling(HARD), 2);
        assert_eq!(panel_shape_for_tier(TRIVIAL), "singles");
        assert_eq!(threshold_panel_for_tier(MODERATE), "hard");
        assert_eq!(next_tier(TRIVIAL), MODERATE);
        assert_eq!(next_tier(HARD), HARD);
        assert_eq!(tier_rank(MODERATE).expect("rank"), 1);
        assert!(known_labels().contains(&"difficulty:hard".to_owned()));
        assert_eq!(codex_review_model_role(HARD), "review");

        let fallback = rating("MODERATE", "medium", "new");
        let built = build_record(record_input(
            "implement",
            None,
            None,
            Some(&fallback),
            &[],
            &[],
            "",
        ))
        .expect("built");
        let mut existing = Map::new();
        let _ = existing.insert("override_source".to_owned(), json!("operator"));
        let _ = existing.insert("audit_upgrade".to_owned(), json!("true"));
        let _ = existing.insert("panel_tier".to_owned(), json!("HARD"));
        let _ = existing.insert("round_cap".to_owned(), json!(3));
        let _ = existing.insert(
            "escalations".to_owned(),
            json!([{"round": 2, "from_tier": "MODERATE", "to_tier": "HARD", "trigger": "bulk-skip"}]),
        );
        let merged = merge_existing_record_fields(built, &existing, &blank_merge_explicit());
        assert_eq!(merged["override_source"], json!("operator"));
        assert_eq!(merged["audit_upgrade"], json!("true"));
        assert_eq!(merged["panel_tier"], json!("HARD"));
        assert_eq!(merged["round_cap"], json!(2));
    }

    #[test]
    fn trailer_metadata_and_difficulty_line_extras() {
        let contiguous = "body\ndiff_added: 8\nnot trailer\ndifficulty: MODERATE\ndiff_lines: 9\n";
        assert_eq!(
            trailing_plan_metadata_lines(contiguous),
            vec![
                "difficulty: MODERATE".to_owned(),
                "diff_lines: 9".to_owned()
            ]
        );
        let full = "body\nreview_status: complete\nrounds_completed: 2\ndifficulty: MODERATE\noversize_override: operator\ndiff_lines: 9\n";
        let lines = trailing_plan_metadata_lines(full);
        assert!(lines.iter().any(|line| line.starts_with("review_status:")));
        assert!(
            lines
                .iter()
                .any(|line| line.starts_with("oversize_override:"))
        );
        assert_eq!(
            plan_difficulty(
                "## Plan\nbody\ndifficulty: MODERATE\n\n## Acceptance\nok\n\ndiff_lines: 9\n"
            ),
            MODERATE
        );
        assert_eq!(
            plan_difficulty(
                "difficulty: TRIVIAL\nbody\ndifficulty: HARD\n\n## Acceptance\nok\n\ndiff_lines: 9\n"
            ),
            HARD
        );
        assert_eq!(
            plan_difficulty(
                "difficulty: MODERATE\nbody\n\ndifficulty: EASY\nconfidence: high\ndiff_lines: 9\n"
            ),
            ""
        );

        let mut data = serde_json::Map::new();
        let _ = data.insert("predicted_tier".to_owned(), json!("TRIVIAL"));
        let _ = data.insert("floors_applied".to_owned(), json!([{"glob": "hooks/**"}]));
        let _ = data.insert("override_source".to_owned(), json!("operator"));
        let _ = data.insert("panel_skipped".to_owned(), json!("no-panel"));
        let _ = data.insert("audit_upgrade".to_owned(), json!("true"));
        let line = difficulty_line(&data);
        assert!(line.contains("floor checked"));
        assert!(line.contains("override operator"));
        assert!(line.contains("panel skipped: no-panel"));
        assert!(line.contains("audit true"));
    }
}
