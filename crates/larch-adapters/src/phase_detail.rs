//! Review-phase detail rendering and per-round metadata publication.
//!
//! This adapter owns the on-disk review artifacts consumed by the final report.
//! The inputs are deliberately historical and partially populated: every reader
//! is best effort, while the two metadata writers publish their complete JSON
//! object atomically or report a command failure.

use crate::{TemporaryRoot, atomic_write_utf8_in, read_kv_raw, read_optional_utf8_lossy};
use chrono::{DateTime, Utc};
use indexmap::IndexMap;
use larch_core::{KvDocument, ParseOptions, claude_sub_default_model, ensure_ascii_json};
use regex::Regex;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::{
    collections::{BTreeMap, BTreeSet},
    env,
    fmt::Write as _,
    fs,
    path::{Path, PathBuf},
    sync::OnceLock,
};

/// The maximum number of lanes the historical progress Gantt displays.
pub const PROGRESS_GANTT_ROW_CAP: usize = 25;

const ROUND_PREFIX: &str = "round-";
const ROUND_TIMING_MIN_COLUMNS: usize = 8;
const VENDOR_TIMING_MIN_COLUMNS: usize = 13;
const ROUND_ATTEMPT_COLUMN: usize = 12;
// `Path.write_text` created these report artifacts at the process-default
// public mode. Keep the retired writer's observable mode while retaining the
// Rust writer's atomic, confined publication.
const LEGACY_REPORT_FILE_MODE: u32 = 0o644;

/// Which review workflow produced a phase-detail request.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum PhaseSkill {
    /// `/design` plan-review artifacts.
    Design,
    /// `/implement` code-review artifacts.
    Implement,
}

impl PhaseSkill {
    /// Parse the legacy CLI spelling.
    #[must_use]
    pub fn parse(value: &str) -> Option<Self> {
        match value {
            "design" => Some(Self::Design),
            "implement" => Some(Self::Implement),
            _other => None,
        }
    }

    const fn as_str(self) -> &'static str {
        match self {
            Self::Design => "design",
            Self::Implement => "implement",
        }
    }
}

/// Explicit inputs for one pure-ish renderer invocation.
#[derive(Clone, Debug)]
pub struct RenderRequest<'a> {
    /// Directory holding `round-N/round-meta.json` artifacts.
    pub rounds_root: &'a Path,
    /// Workflow that owns the timing table's duration window.
    pub skill: PhaseSkill,
    /// Optional `v1` timing ledger.
    pub timing_ledger: Option<&'a Path>,
    /// Optional JSONL vendor-token ledger.
    pub token_ledger: Option<&'a Path>,
    /// Optional legacy aggregated accepted-findings JSONL.
    pub findings_file: Option<&'a Path>,
    /// Maximum number of whole-run reviewer rows.
    pub top_n: usize,
    /// Whether reviewer timing Gantts should be included.
    pub gantt_enabled: bool,
}

#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
struct Counts {
    accepted: i64,
    rejected: i64,
    neutral: i64,
    exonerated: i64,
    oos_proposed: i64,
    oos_rejected: i64,
    oos_fileable: i64,
}

impl Counts {
    const fn all_zero(self) -> bool {
        self.accepted == 0
            && self.rejected == 0
            && self.neutral == 0
            && self.exonerated == 0
            && self.oos_proposed == 0
            && self.oos_rejected == 0
    }
}

#[derive(Clone, Debug)]
struct PhaseRound {
    number: u64,
    suggestions: i64,
    accepted: i64,
    oos_proposed: i64,
    oos_fileable: i64,
    reviewers: i64,
    seconds: Option<i64>,
    cost: String,
    gantt_window: Option<(i64, i64)>,
    canonical: Option<(i64, i64)>,
    nit_pruned: i64,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum CountSource {
    Markdown,
    Classification,
}

#[derive(Clone, Debug)]
struct ClassificationRow {
    columns: BTreeMap<String, String>,
    header: Vec<String>,
}

impl ClassificationRow {
    fn value(&self, key: &str) -> &str {
        self.columns.get(key).map_or("", String::as_str)
    }

    fn finding_id(&self) -> &str {
        self.value("finding_id")
    }

    fn result(&self) -> &str {
        self.value("voting_result")
    }

    fn in_scope(&self) -> bool {
        if self.header.iter().any(|column| column == "scope") {
            self.value("scope").trim() == "in_scope"
        } else {
            !self.finding_id().trim().starts_with("OOS_")
        }
    }
}

/// Render the historical review-phase detail Markdown.
///
/// Missing, unreadable, or partial report inputs intentionally render a stable
/// empty/no-rounds result instead of failing a final-report caller.
#[must_use]
pub fn render_phase_detail(request: &RenderRequest<'_>) -> String {
    if !readable_directory(request.rounds_root) {
        return String::new();
    }
    let top_n = if request.top_n > 0 { request.top_n } else { 7 };
    let round_dirs = completed_round_dirs(request.rounds_root);
    if round_dirs.is_empty() {
        return "## Review Phase Detail\n\nNo review rounds completed.\n".to_owned();
    }
    let label_map = progress_label_map(&round_dirs);
    let timing = request.timing_ledger.filter(|path| regular_file(path));
    let tokens = request.token_ledger.filter(|path| regular_file(path));
    let rounds: Vec<PhaseRound> = round_dirs
        .iter()
        .map(|directory| phase_round(directory, request.skill, timing, tokens))
        .collect();

    let top_reviewers = if classification_available(&round_dirs) {
        top_reviewers_from_classification(&round_dirs, top_n, &label_map)
    } else {
        top_reviewers_from_findings(request.findings_file, top_n, &label_map)
    };
    let top_reviewers = apply_fallback_remap(top_reviewers, &round_dirs);
    let (failure_total, failures) = failed_reviewers(&round_dirs, &label_map);
    let total_time: i64 = rounds.iter().filter_map(|round| round.seconds).sum();
    let any_time = rounds.iter().any(|round| round.seconds.is_some());
    let costs: Vec<f64> = rounds
        .iter()
        .filter_map(|round| round.cost.strip_prefix('$'))
        .filter_map(|value| value.parse::<f64>().ok())
        .collect();
    let total_cost = if costs.is_empty() {
        "N/A".to_owned()
    } else {
        format!("${:.2}", costs.iter().sum::<f64>())
    };

    let mut output = String::from(
        "## Review Phase Detail\n\n| Round | Suggestions | Accepted | OOS proposed | OOS fileable | Time | Cost | Reviewers |\n|--:|--:|--:|--:|--:|:--|--:|--:|\n",
    );
    for round in &rounds {
        let _ = writeln!(
            output,
            "| {} | {} | {} | {} | {} | {} | {} | {} |",
            round.number,
            round.suggestions,
            round.accepted,
            round.oos_proposed,
            round.oos_fileable,
            format_hms(round.seconds),
            round.cost,
            round.reviewers,
        );
    }
    let _ = writeln!(
        output,
        "| **Total (round-sum)** | **{}** | **{}** | **{}** | **{}** | **{}** | **{}** | **{}** |",
        rounds.iter().map(|round| round.suggestions).sum::<i64>(),
        rounds.iter().map(|round| round.accepted).sum::<i64>(),
        rounds.iter().map(|round| round.oos_proposed).sum::<i64>(),
        rounds.iter().map(|round| round.oos_fileable).sum::<i64>(),
        format_hms(any_time.then_some(total_time)),
        total_cost,
        rounds.iter().map(|round| round.reviewers).sum::<i64>(),
    );
    output.push('\n');
    output.push_str(
        "_The Total (round-sum) row adds up the per-round Suggestions and Accepted: when the review loop re-raises the same finding across rounds, that finding is counted once per round, so the round-sum can exceed the number of distinct findings. Top reviewers counts per-round accepted-point scores the same way._\n\n",
    );
    append_decomposition(&mut output, &rounds);
    if request.gantt_enabled {
        output.push_str(&render_gantts(&round_dirs, timing, &rounds, &label_map));
    }
    output.push_str("**Top reviewers** (by per-round accepted-point score, whole run):\n");
    if top_reviewers.is_empty() {
        output.push_str("- (no accepted-point score attributed to a reviewer slot)\n");
    } else {
        for (index, (label, score)) in top_reviewers.iter().enumerate() {
            let _ = writeln!(output, "{}. {}: {}", index + 1, label, format_score(*score));
        }
    }
    let _ = writeln!(output, "\n**Reviewer slot failures**: {failure_total}");
    for (label, count) in failures {
        let _ = writeln!(output, "- {label}: {count}");
    }
    output
}

/// Write design round metadata, returning `Ok(false)` for a missing round.
///
/// A real publication error is returned so the CLI preserves the retired
/// writer's nonzero exit contract.
///
/// # Errors
///
/// Returns an error when an input artifact cannot be safely published as
/// `round-meta.json`.
pub fn write_design_round_meta(round_dir: &Path) -> Result<bool, String> {
    let source_round_dir = round_dir;
    let round_dir = absolute_path(round_dir)?;
    if !round_dir.is_dir() {
        return Ok(false);
    }
    let (counts, source) = round_counts(&round_dir);
    let counts = source.map_or(counts, |source| {
        adjust_design_security_oos(&round_dir, counts, source)
    });
    let artifact = artifact_oos_split(&round_dir, counts, source);
    let mut metadata_counts = counts;
    metadata_counts.oos_proposed = artifact.proposed;
    metadata_counts.oos_fileable = artifact.fileable;
    metadata_counts.oos_rejected = artifact.rejected;
    let panel_count = materialize_design_panel_manifest(&round_dir)?;
    let summary = simple_env(&round_dir.join("round-summary.env"));
    let failure_count = as_i64(summary.get("COLLECT_FAILURE_COUNT").map(String::as_str));
    let collector = design_collector(&round_dir, failure_count);
    let revise = simple_env(&round_dir.join("revise/revise.env"));
    write_metadata(
        &round_dir,
        &RoundMetadataInput {
            counts: metadata_counts,
            panel_count,
            collector,
            canonical: None,
            nit_pruned: 0,
            revise: Some(Revise {
                status: nonempty(revise.get("REVISE_STATUS")),
                tier: nonempty(revise.get("REVISE_TIER")),
            }),
            difficulty: round_difficulty(&round_dir, source_round_dir),
        },
    )?;
    Ok(true)
}

/// Write implement round metadata, returning `Ok(false)` for a missing round.
///
/// # Errors
///
/// Returns an error when an input artifact cannot be safely published as
/// `round-meta.json`.
pub fn write_implement_round_meta(round_dir: &Path) -> Result<bool, String> {
    let source_round_dir = round_dir;
    let round_dir = absolute_path(round_dir)?;
    if !round_dir.is_dir() {
        return Ok(false);
    }
    let (counts, source) = round_counts(&round_dir);
    let artifact = artifact_oos_split(&round_dir, counts, source);
    let mut metadata_counts = counts;
    metadata_counts.oos_proposed = artifact.proposed;
    metadata_counts.oos_fileable = artifact.fileable;
    metadata_counts.oos_rejected = artifact.rejected;
    let panel_count = count_panel_manifest(&round_dir.join("panel-manifest.ndjson"));
    let (mut canonical, nit_pruned) = canonical_decomposition(&round_dir);
    if let Some(mut values) = canonical {
        let split = classification_oos_split(&round_dir);
        if split.seen {
            values.oos_proposed = split.proposed;
            values.oos_rejected = split.rejected;
            values.oos_fileable = review_tally_fileable(&round_dir).unwrap_or(split.fileable);
        }
        canonical = Some(values);
    }
    write_metadata(
        &round_dir,
        &RoundMetadataInput {
            counts: metadata_counts,
            panel_count,
            collector: String::new(),
            canonical,
            nit_pruned,
            revise: None,
            difficulty: round_difficulty(&round_dir, source_round_dir),
        },
    )?;
    Ok(true)
}

/// Atomically write a caller-selected rendered report without following an
/// existing output symlink.
///
/// # Errors
///
/// Returns an error when the output parent is unsafe or the report cannot be
/// written atomically.
pub fn write_render_output(path: &Path, text: &str) -> Result<(), String> {
    let absolute = if path.is_absolute() {
        path.to_path_buf()
    } else {
        env::current_dir()
            .map_err(|error| format!("resolve render output directory: {error}"))?
            .join(path)
    };
    let parent = absolute
        .parent()
        .ok_or_else(|| format!("render output has no parent: {}", path.display()))?;
    let filename = absolute
        .file_name()
        .ok_or_else(|| format!("render output has no filename: {}", path.display()))?;
    let root = TemporaryRoot::resolve(Some(parent))
        .map_err(|error| format!("unsafe render output parent: {error}"))?;
    atomic_write_utf8_in(
        &root,
        Path::new(filename),
        text,
        false,
        LEGACY_REPORT_FILE_MODE,
    )
    .map_err(|error| format!("write rendered phase detail: {error}"))
}

fn absolute_path(path: &Path) -> Result<PathBuf, String> {
    if path.is_absolute() {
        Ok(path.to_path_buf())
    } else {
        env::current_dir()
            .map(|directory| directory.join(path))
            .map_err(|error| format!("resolve current directory: {error}"))
    }
}

fn readable_directory(path: &Path) -> bool {
    fs::read_dir(path).is_ok()
}

fn regular_file(path: &Path) -> bool {
    fs::metadata(path).is_ok_and(|metadata| metadata.is_file())
}

fn round_number(path: &Path) -> Option<u64> {
    let name = path.file_name()?.to_str()?;
    let number = name.strip_prefix(ROUND_PREFIX)?;
    let mut characters = number.bytes();
    matches!(characters.next(), Some(b'1'..=b'9'))
        .then_some(())
        .filter(|()| characters.all(|character| character.is_ascii_digit()))
        .and_then(|()| number.parse::<u64>().ok())
}

fn completed_round_dirs(root: &Path) -> Vec<PathBuf> {
    let Ok(entries) = fs::read_dir(root) else {
        return Vec::new();
    };
    let mut entries: Vec<(u64, PathBuf)> = entries
        .flatten()
        .map(|entry| entry.path())
        .filter(|path| path.is_dir() && regular_file(&path.join("round-meta.json")))
        .filter_map(|path| round_number(&path).map(|number| (number, path)))
        .collect();
    entries.sort_by_key(|(number, _path)| *number);
    entries.into_iter().map(|(_number, path)| path).collect()
}

fn read_text(path: &Path) -> String {
    read_optional_utf8_lossy(path)
        .ok()
        .flatten()
        .unwrap_or_default()
}

fn read_lines(path: Option<&Path>) -> Vec<String> {
    path.map_or_else(Vec::new, |candidate| {
        read_text(candidate)
            .lines()
            .map(ToOwned::to_owned)
            .collect()
    })
}

fn read_json_object(path: &Path) -> serde_json::Map<String, Value> {
    serde_json::from_str::<Value>(&read_text(path))
        .ok()
        .and_then(|value| value.as_object().cloned())
        .unwrap_or_default()
}

fn ordered_array_field(path: &Path, key: &str) -> OrderedJson {
    serde_json::from_str::<IndexMap<String, OrderedJson>>(&read_text(path))
        .ok()
        .and_then(|object| object.get(key).cloned())
        .filter(|value| matches!(value, OrderedJson::Array(_)))
        .unwrap_or_else(OrderedJson::empty_array)
}

fn object_value<'a>(
    object: &'a serde_json::Map<String, Value>,
    key: &str,
) -> &'a serde_json::Map<String, Value> {
    object
        .get(key)
        .and_then(Value::as_object)
        .unwrap_or_else(|| -> &'a serde_json::Map<String, Value> { empty_object() })
}

fn empty_object() -> &'static serde_json::Map<String, Value> {
    static EMPTY: OnceLock<serde_json::Map<String, Value>> = OnceLock::new();
    EMPTY.get_or_init(serde_json::Map::new)
}

fn as_i64(value: Option<&str>) -> i64 {
    value
        .and_then(|value| value.trim().parse::<f64>().ok())
        .map_or(0, legacy_float_to_i64)
}

fn value_i64(value: Option<&Value>) -> i64 {
    match value {
        Some(Value::Bool(value)) => i64::from(*value),
        Some(Value::Number(value)) => value
            .as_i64()
            .or_else(|| value.as_f64().map(legacy_float_to_i64))
            .unwrap_or(0),
        Some(Value::String(value)) => as_i64(Some(value)),
        _other => 0,
    }
}

#[allow(clippy::cast_possible_truncation)] // Mirrors the retired Python `int(float)` coercion.
const fn legacy_float_to_i64(value: f64) -> i64 {
    value as i64
}

fn nonempty(value: Option<&String>) -> Option<String> {
    value.filter(|value| !value.is_empty()).cloned()
}

fn simple_env(path: &Path) -> BTreeMap<String, String> {
    read_kv_raw(path).unwrap_or_default().into_iter().collect()
}

fn parse_classification(path: &Path) -> Vec<ClassificationRow> {
    let lines = read_lines(Some(path));
    let Some(header_line) = lines.first() else {
        return Vec::new();
    };
    let header: Vec<String> = header_line
        .split('\t')
        .map(|value| value.trim().to_owned())
        .collect();
    lines
        .iter()
        .skip(1)
        .filter_map(|line| {
            let values: Vec<&str> = line.split('\t').map(str::trim).collect();
            (values.len() >= 3).then(|| ClassificationRow {
                columns: header
                    .iter()
                    .enumerate()
                    .map(|(index, key)| {
                        (
                            key.clone(),
                            values.get(index).copied().unwrap_or_default().to_owned(),
                        )
                    })
                    .collect(),
                header: header.clone(),
            })
        })
        .collect()
}

fn parse_tally(path: &Path) -> Counts {
    let mut counts = Counts::default();
    let mut in_findings = false;
    for line in read_lines(Some(path)) {
        if line.starts_with("## Findings") {
            in_findings = true;
            continue;
        }
        if in_findings && line.starts_with("## ") {
            in_findings = false;
        }
        if !in_findings || !line.contains('|') {
            continue;
        }
        let pieces: Vec<&str> = line.split('|').map(str::trim).collect();
        if pieces.len() < 4 {
            continue;
        }
        let item = pieces.get(1).copied().unwrap_or_default();
        let mut result = pieces
            .get(pieces.len().saturating_sub(2))
            .copied()
            .unwrap_or_default();
        if result.is_empty() // lint-status-routing: ok result is a parsed Markdown cell, not a routed enum.
            || result.chars().all(|character| character == '-')
        {
            result = pieces
                .get(pieces.len().saturating_sub(3))
                .copied()
                .unwrap_or_default();
        }
        if item.is_empty()
            || item == "Item"
            || item.chars().all(|character| character == '-')
            || result.is_empty() // lint-status-routing: ok result is a parsed Markdown cell, not a routed enum.
            || result == "Result"
            || result.chars().all(|character| character == '-')
        {
            continue;
        }
        if finding_id(item) {
            increment_count(&mut counts, item, result, true);
        } else if oos_id(item) {
            increment_count(&mut counts, item, result, false);
        }
    }
    counts.oos_fileable = counts.oos_proposed;
    counts
}

fn parse_classification_counts(path: &Path) -> Counts {
    let mut counts = Counts::default();
    for row in parse_classification(path) {
        let item = row.finding_id();
        let result = row.result();
        if row.in_scope() && finding_id(item) {
            increment_count(&mut counts, item, result, true);
        } else if !result.is_empty() {
            increment_count(&mut counts, item, result, false);
        }
    }
    counts.oos_fileable = counts.oos_proposed;
    counts
}

fn finding_id(value: &str) -> bool {
    item_id(value, "FINDING_")
}

fn oos_id(value: &str) -> bool {
    item_id(value, "OOS_")
}

fn item_id(value: &str, prefix: &str) -> bool {
    value.strip_prefix(prefix).is_some_and(|suffix| {
        !suffix.is_empty()
            && suffix
                .bytes()
                .all(|byte| byte.is_ascii_alphanumeric() || byte == b'_')
    })
}

fn increment_count(counts: &mut Counts, _item: &str, result: &str, in_scope: bool) {
    if in_scope {
        match result {
            "accepted" => counts.accepted += 1,
            "rejected" => counts.rejected += 1,
            "neutral" => counts.neutral += 1,
            "exonerated" => counts.exonerated += 1,
            _other => {}
        }
    } else if result == "accepted" {
        counts.oos_proposed += 1;
    } else {
        counts.oos_rejected += 1;
    }
}

fn classification_has_data(path: &Path) -> bool {
    read_lines(Some(path))
        .iter()
        .skip(1)
        .any(|line| !line.trim().is_empty())
}

fn round_counts(round_dir: &Path) -> (Counts, Option<CountSource>) {
    let tally = round_dir.join("voting-tally.md");
    let classification = round_dir.join("findings-classification.tsv");
    let mut counts = None;
    let mut source = None;
    let markdown = if regular_file(&tally) {
        parse_tally(&tally)
    } else {
        Counts::default()
    };
    if regular_file(&tally) {
        counts = Some(markdown);
        source = Some(CountSource::Markdown);
    }
    if regular_file(&classification) {
        let tsv = parse_classification_counts(&classification);
        if counts.is_none() || (markdown.all_zero() && classification_has_data(&classification)) {
            counts = Some(tsv);
            source = Some(CountSource::Classification);
        }
    }
    (counts.unwrap_or_default(), source)
}

#[derive(Clone, Copy, Debug, Default)]
struct OosSplit {
    proposed: i64,
    rejected: i64,
    fileable: i64,
    seen: bool,
}

fn classification_oos_split(round_dir: &Path) -> OosSplit {
    let mut split = OosSplit::default();
    for row in parse_classification(&round_dir.join("findings-classification.tsv")) {
        if row.result().is_empty() || row.in_scope() {
            continue;
        }
        split.seen = true;
        if security_oos_block(round_dir, row.finding_id()) {
            continue;
        }
        if row.result() == "accepted" {
            split.proposed += 1;
            if oos_fileable(&row) {
                split.fileable += 1;
            }
        } else {
            split.rejected += 1;
        }
    }
    split
}

fn oos_fileable(row: &ClassificationRow) -> bool {
    if row.result() != "accepted" {
        return false;
    }
    let vote_indices: Vec<String> = row
        .header
        .iter()
        .filter_map(|key| vote_column_index(key).map(ToOwned::to_owned))
        .collect();
    let mut yes_count = 0;
    let mut major_yes = 0;
    for index in vote_indices {
        if row
            .value(&format!("v{index}_vote"))
            .eq_ignore_ascii_case("YES")
        {
            yes_count += 1;
            if row
                .value(&format!("v{index}_severity"))
                .eq_ignore_ascii_case("major")
            {
                major_yes += 1;
            }
        }
    }
    yes_count > 0 && major_yes * 2 > yes_count
}

fn vote_column_index(value: &str) -> Option<&str> {
    let suffix = value.strip_prefix('v')?.strip_suffix("_vote")?;
    (!suffix.is_empty() && suffix.bytes().all(|byte| byte.is_ascii_digit())).then_some(suffix)
}

fn security_oos_block(round_dir: &Path, id: &str) -> bool {
    oos_block(round_dir, id).is_some_and(|block| is_security_block(&block))
}

fn is_security_block(text: &str) -> bool {
    static HEADER: OnceLock<Regex> = OnceLock::new();
    static FIELD: OnceLock<Regex> = OnceLock::new();
    let header = HEADER.get_or_init(|| {
        Regex::new(
            r"(?i)^###[ \t]+(?:OOS|FINDING)_\d+:\s*(?:\[(?:OUT_OF_SCOPE|OOS)\]\s*)?`?(?:\[security\]|<security>)`?(?:\s|$|[:-])",
        )
        .expect("security header regex is valid")
    });
    let field = FIELD.get_or_init(|| {
        Regex::new(
            r"(?i)^[ \t-]*focus[- ]area[ \t]*[:=][ \t]*security(?:[-a-z0-9 _]*)(?:[ \t]|$|\(|#|\.|,)",
        )
        .expect("security field regex is valid")
    });
    let visible = without_fenced_code(text);
    let mut lines = visible.lines();
    if lines.next().is_some_and(|line| header.is_match(line)) {
        return true;
    }
    visible.lines().any(|line| {
        let normalized = line.replace(['`', '*'], "");
        field.is_match(normalized.trim())
    })
}

fn without_fenced_code(text: &str) -> String {
    let mut output = String::new();
    let mut fence: Option<(char, usize)> = None;
    let mut pending = String::new();
    for raw_line in text.split_inclusive('\n') {
        let line = raw_line.trim_end_matches(['\r', '\n']);
        if let Some((marker, minimum)) = fence {
            pending.push_str(raw_line);
            if exact_fence_closes(line, marker, minimum) {
                fence = None;
                pending.clear();
            }
            continue;
        }
        if let Some(marker) = fence_marker(line) {
            fence = Some(marker);
            pending.push_str(raw_line);
            continue;
        }
        output.push_str(raw_line);
    }
    // The Python regex removes only complete fences. An unclosed marker is
    // ordinary visible text, including any security field that follows it.
    output.push_str(&pending);
    output
}

fn fence_closes(line: &str, marker: char, minimum: usize) -> bool {
    let Some(line) = markdown_fence_tail(line) else {
        return false;
    };
    let count = line.chars().take_while(|value| *value == marker).count();
    count >= minimum && line.chars().skip(count).all(char::is_whitespace)
}

fn exact_fence_closes(line: &str, marker: char, length: usize) -> bool {
    let Some(line) = markdown_fence_tail(line) else {
        return false;
    };
    let count = line.chars().take_while(|value| *value == marker).count();
    count == length && line.chars().skip(count).all(char::is_whitespace)
}

fn fence_marker(line: &str) -> Option<(char, usize)> {
    let line = markdown_fence_tail(line)?;
    let marker = line.chars().next()?;
    if !matches!(marker, '`' | '~') {
        return None;
    }
    let count = line.chars().take_while(|value| *value == marker).count();
    (count >= 3).then_some((marker, count))
}

fn markdown_fence_tail(line: &str) -> Option<&str> {
    let indentation = line
        .chars()
        .take_while(|character| matches!(character, ' ' | '\t'))
        .count();
    (indentation <= 3).then(|| {
        &line[line
            .char_indices()
            .nth(indentation)
            .map_or(line.len(), |(index, _character)| index)..]
    })
}

fn oos_block(round_dir: &Path, id: &str) -> Option<String> {
    for name in [
        "findings-oos.md",
        "findings.md",
        "oos.md",
        "findings-in-scope.md",
    ] {
        let text = read_text(&round_dir.join(name));
        if text.is_empty() {
            continue;
        }
        if let Some(block) = canonical_item_block(&text, id) {
            return Some(block);
        }
    }
    None
}

fn canonical_item_block(text: &str, sought_id: &str) -> Option<String> {
    let mut start = None;
    let mut offset = 0;
    let mut fence = None;
    for raw_line in text.split_inclusive('\n') {
        let line = raw_line.trim_end_matches(['\r', '\n']);
        if let Some((marker, minimum)) = fence {
            if fence_closes(line, marker, minimum) {
                fence = None;
            }
            offset += raw_line.len();
            continue;
        }
        if let Some(marker) = fence_marker(line) {
            fence = Some(marker);
            offset += raw_line.len();
            continue;
        }
        if let Some(start) = start {
            if level_three_heading(line) {
                return Some(text[start..offset].to_owned());
            }
        } else if canonical_item_id(line).is_some_and(|id| id == sought_id) {
            start = Some(offset);
        }
        offset += raw_line.len();
    }
    start.map(|start| text[start..].to_owned())
}

fn canonical_item_id(line: &str) -> Option<&str> {
    let remainder = line.strip_prefix("###")?;
    if !remainder.starts_with([' ', '\t']) {
        return None;
    }
    let remainder = remainder.trim_start_matches([' ', '\t']);
    let (id, _title) = remainder.split_once(':')?;
    let (kind, number) = id.split_once('_')?;
    (matches!(kind, "OOS" | "FINDING")
        && !number.is_empty()
        && number.bytes().all(|value| value.is_ascii_digit()))
    .then_some(id)
}

fn level_three_heading(line: &str) -> bool {
    line.strip_prefix("###")
        .is_some_and(|remainder| remainder.is_empty() || remainder.starts_with([' ', '\t']))
}

fn oos_rows(round_dir: &Path, source: CountSource) -> Vec<(String, String)> {
    match source {
        CountSource::Classification => {
            parse_classification(&round_dir.join("findings-classification.tsv"))
                .into_iter()
                .filter(|row| oos_id(row.finding_id()) && !row.result().is_empty())
                .map(|row| (row.finding_id().to_owned(), row.result().to_owned()))
                .collect()
        }
        CountSource::Markdown => {
            let mut rows = Vec::new();
            let mut in_findings = false;
            for line in read_lines(Some(&round_dir.join("voting-tally.md"))) {
                if line.starts_with("## Findings") {
                    in_findings = true;
                    continue;
                }
                if in_findings && line.starts_with("## ") {
                    in_findings = false;
                }
                if !in_findings || !line.contains('|') {
                    continue;
                }
                let pieces: Vec<&str> = line.split('|').map(str::trim).collect();
                if pieces.len() < 4 {
                    continue;
                }
                let item = pieces[1];
                let result = pieces[pieces.len() - 2];
                let result =
                    if result.is_empty() || result.chars().all(|character| character == '-') {
                        pieces[pieces.len() - 3]
                    } else {
                        result
                    };
                if oos_id(item) && !result.is_empty() {
                    rows.push((item.to_owned(), result.to_owned()));
                }
            }
            rows
        }
    }
}

fn adjust_design_security_oos(round_dir: &Path, mut counts: Counts, source: CountSource) -> Counts {
    for (id, result) in oos_rows(round_dir, source) {
        if !security_oos_block(round_dir, &id) {
            continue;
        }
        if result == "accepted" {
            counts.oos_proposed = counts.oos_proposed.saturating_sub(1).max(0);
        } else {
            counts.oos_rejected = counts.oos_rejected.saturating_sub(1).max(0);
        }
    }
    counts.oos_fileable = counts.oos_proposed;
    counts
}

fn review_tally_fileable(round_dir: &Path) -> Option<i64> {
    simple_env(&round_dir.join("review-tally.env"))
        .get("OOS_ACCEPTED_COUNT")
        .map(|value| as_i64(Some(value)))
}

#[derive(Clone, Copy, Debug, Default)]
struct ArtifactOosSplit {
    proposed: i64,
    rejected: i64,
    fileable: i64,
    present: bool,
}

fn artifact_oos_split(
    round_dir: &Path,
    counts: Counts,
    source: Option<CountSource>,
) -> ArtifactOosSplit {
    let classification = classification_oos_split(round_dir);
    let env_fileable = review_tally_fileable(round_dir);
    if classification.seen {
        return ArtifactOosSplit {
            proposed: classification.proposed,
            rejected: classification.rejected,
            fileable: env_fileable.unwrap_or(classification.fileable),
            present: true,
        };
    }
    let Some(source) = source else {
        return ArtifactOosSplit::default();
    };
    let adjusted = { adjust_design_security_oos(round_dir, counts, source) };
    ArtifactOosSplit {
        proposed: adjusted.oos_proposed,
        rejected: adjusted.oos_rejected,
        fileable: env_fileable.unwrap_or(0),
        present: true,
    }
}

fn canonical_decomposition(round_dir: &Path) -> (Option<Counts>, i64) {
    let path = round_dir.join("findings-classification.tsv");
    if !regular_file(&path) || !classification_has_data(&path) {
        return (None, 0);
    }
    let counts = parse_classification_counts(&path);
    let pruned = simple_env(&round_dir.join("prune-nit.env"))
        .get("PRUNED_COUNT")
        .filter(|value| value.bytes().all(|byte| byte.is_ascii_digit()))
        .map_or(0, |value| as_i64(Some(value)));
    (Some(counts), pruned)
}

#[derive(Serialize)]
struct TallyWire {
    #[serde(rename = "ACCEPTED_COUNT")]
    accepted: String,
    #[serde(rename = "REJECTED_COUNT")]
    rejected: String,
    #[serde(rename = "EXONERATED_COUNT")]
    exonerated: String,
    #[serde(rename = "NEUTRAL_COUNT")]
    neutral: String,
    #[serde(rename = "OOS_PROPOSED_COUNT")]
    oos_proposed: String,
    #[serde(rename = "OOS_ACCEPTED_COUNT")]
    oos_fileable: String,
    #[serde(rename = "OOS_REJECTED_COUNT")]
    oos_rejected: String,
}

impl From<Counts> for TallyWire {
    fn from(counts: Counts) -> Self {
        Self {
            accepted: counts.accepted.to_string(),
            rejected: counts.rejected.to_string(),
            exonerated: counts.exonerated.to_string(),
            neutral: counts.neutral.to_string(),
            oos_proposed: counts.oos_proposed.to_string(),
            oos_fileable: counts.oos_fileable.to_string(),
            oos_rejected: counts.oos_rejected.to_string(),
        }
    }
}

#[derive(Serialize)]
struct PanelWire {
    total_slot_count: i64,
}

#[derive(Serialize)]
struct SummaryWire {
    panel: PanelWire,
}

#[derive(Clone, Serialize)]
struct Revise {
    status: Option<String>,
    tier: Option<String>,
}

#[derive(Serialize)]
#[serde(untagged)]
enum ScoutWire {
    Absent {
        status: &'static str,
    },
    Ok {
        status: &'static str,
        predicted_tier: String,
        confidence: String,
        source: String,
    },
}

#[derive(Serialize)]
struct DifficultyBaseWire {
    tier_in_effect: Value,
    ceiling_in_effect: Value,
    escalations: OrderedJson,
    scout: ScoutWire,
}

#[derive(Serialize)]
struct DifficultyRecordWire {
    tier_in_effect: Value,
    ceiling_in_effect: Value,
    escalations: OrderedJson,
    scout: ScoutWire,
    applied_tier: String,
    panel_tier: String,
    round_cap: Value,
    codex_model_role: String,
    override_source: String,
    audit_evaluated: Value,
    audit_upgrade: Option<String>,
    escalated_round: Value,
}

#[derive(Serialize)]
#[serde(untagged)]
enum DifficultyWire {
    Base(Box<DifficultyBaseWire>),
    Record(Box<DifficultyRecordWire>),
}

/// JSON values whose object keys retain the source artifact's insertion order.
///
/// Python's `json.loads` and `json.dumps` preserve nested key order, so the
/// parity writer needs this only for copied opaque `escalations` payloads.
#[derive(Clone, Deserialize, Serialize)]
#[serde(untagged)]
enum OrderedJson {
    Null,
    Bool(bool),
    Number(serde_json::Number),
    String(String),
    Array(Vec<Self>),
    Object(Box<IndexMap<String, Self>>),
}

impl OrderedJson {
    const fn empty_array() -> Self {
        Self::Array(Vec::new())
    }
}

#[derive(Serialize)]
struct RoundMetaWire {
    tally: TallyWire,
    summary: SummaryWire,
    collector: String,
    difficulty: DifficultyWire,
    #[serde(skip_serializing_if = "Option::is_none")]
    tally_canonical: Option<TallyWire>,
    #[serde(skip_serializing_if = "Option::is_none")]
    nit_pruned_count: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    revise: Option<Revise>,
}

struct RoundMetadataInput {
    counts: Counts,
    panel_count: i64,
    collector: String,
    canonical: Option<Counts>,
    nit_pruned: i64,
    revise: Option<Revise>,
    difficulty: DifficultyWire,
}

fn write_metadata(round_dir: &Path, input: &RoundMetadataInput) -> Result<(), String> {
    let wire = RoundMetaWire {
        tally: input.counts.into(),
        summary: SummaryWire {
            panel: PanelWire {
                total_slot_count: input.panel_count,
            },
        },
        collector: input.collector.clone(),
        difficulty: clone_difficulty(&input.difficulty),
        tally_canonical: input.canonical.map(Into::into),
        nit_pruned_count: input.canonical.map(|_counts| input.nit_pruned.to_string()),
        revise: input.revise.clone(),
    };
    let text = serde_json::to_string_pretty(&wire)
        .map(|text| format!("{}\n", ensure_ascii_json(&text)))
        .map_err(|error| format!("encode round metadata: {error}"))?;
    let root = TemporaryRoot::resolve(Some(round_dir))
        .map_err(|error| format!("unsafe round metadata directory: {error}"))?;
    atomic_write_utf8_in(
        &root,
        Path::new("round-meta.json"),
        &text,
        false,
        LEGACY_REPORT_FILE_MODE,
    )
    .map_err(|error| format!("write round metadata: {error}"))
}

fn clone_difficulty(value: &DifficultyWire) -> DifficultyWire {
    match value {
        DifficultyWire::Base(value) => DifficultyWire::Base(Box::new(DifficultyBaseWire {
            tier_in_effect: value.tier_in_effect.clone(),
            ceiling_in_effect: value.ceiling_in_effect.clone(),
            escalations: value.escalations.clone(),
            scout: clone_scout(&value.scout),
        })),
        DifficultyWire::Record(value) => DifficultyWire::Record(Box::new(DifficultyRecordWire {
            tier_in_effect: value.tier_in_effect.clone(),
            ceiling_in_effect: value.ceiling_in_effect.clone(),
            escalations: value.escalations.clone(),
            scout: clone_scout(&value.scout),
            applied_tier: value.applied_tier.clone(),
            panel_tier: value.panel_tier.clone(),
            round_cap: value.round_cap.clone(),
            codex_model_role: value.codex_model_role.clone(),
            override_source: value.override_source.clone(),
            audit_evaluated: value.audit_evaluated.clone(),
            audit_upgrade: value.audit_upgrade.clone(),
            escalated_round: value.escalated_round.clone(),
        })),
    }
}

fn clone_scout(value: &ScoutWire) -> ScoutWire {
    match value {
        ScoutWire::Absent { .. } => ScoutWire::Absent { status: "absent" },
        ScoutWire::Ok {
            predicted_tier,
            confidence,
            source,
            ..
        } => ScoutWire::Ok {
            status: "ok",
            predicted_tier: predicted_tier.clone(),
            confidence: confidence.clone(),
            source: source.clone(),
        },
    }
}

fn round_difficulty(round_dir: &Path, source_round_dir: &Path) -> DifficultyWire {
    let raw_path = round_dir.join("scout-difficulty-rating.raw.json");
    let raw = if regular_non_symlink_file(&raw_path) {
        read_json_object(&raw_path)
    } else {
        serde_json::Map::new()
    };
    let rating = valid_rating(&raw).map(|(predicted, confidence)| {
        let adjusted = if confidence == "low" && predicted != "HARD" {
            next_tier(&predicted)
        } else {
            predicted.clone()
        };
        (
            adjusted,
            ScoutWire::Ok {
                status: "ok",
                predicted_tier: predicted,
                confidence,
                source: source_round_dir
                    .join("scout-difficulty-rating.raw.json")
                    .display()
                    .to_string(),
            },
        )
    });
    let record = read_json_object(&round_dir.join("difficulty-rating.json"));
    let (mut tier, scout) = rating.map_or_else(
        || (Value::Null, ScoutWire::Absent { status: "absent" }),
        |(tier, scout)| (Value::String(tier), scout),
    );
    let mut ceiling = tier.clone();
    if record.is_empty() {
        return DifficultyWire::Base(Box::new(DifficultyBaseWire {
            tier_in_effect: tier,
            ceiling_in_effect: ceiling,
            escalations: OrderedJson::empty_array(),
            scout,
        }));
    }
    let panel_tier = first_nonempty([
        object_string(&record, "panel_tier"),
        object_string(&record, "applied_tier"),
        tier.as_str().unwrap_or_default().to_owned(),
    ]);
    let mut round_cap = record.get("round_cap").and_then(Value::as_i64);
    if round_cap.is_none() && !panel_tier.is_empty() {
        round_cap = Some(tier_ceiling(&panel_tier));
    } else if round_cap.is_some() && !panel_tier.is_empty() {
        round_cap = round_cap.map(|value| value.min(tier_ceiling(&panel_tier)));
    }
    if !panel_tier.is_empty() {
        tier = Value::String(panel_tier);
    }
    if let Some(value) = round_cap {
        ceiling = Value::Number(value.into());
    }
    DifficultyWire::Record(Box::new(DifficultyRecordWire {
        tier_in_effect: tier,
        ceiling_in_effect: ceiling,
        escalations: ordered_array_field(&round_dir.join("difficulty-rating.json"), "escalations"),
        scout,
        applied_tier: object_string(&record, "applied_tier"),
        panel_tier: object_string(&record, "panel_tier"),
        round_cap: round_cap.map_or(Value::Null, |value| Value::Number(value.into())),
        codex_model_role: object_string(&record, "codex_model_role"),
        override_source: object_string(&record, "override_source"),
        audit_evaluated: record
            .get("audit_evaluated")
            .cloned()
            .unwrap_or(Value::Null),
        audit_upgrade: nonempty_string(object_string(&record, "audit_upgrade")),
        escalated_round: record
            .get("escalated_round")
            .cloned()
            .unwrap_or(Value::Null),
    }))
}

fn valid_rating(object: &serde_json::Map<String, Value>) -> Option<(String, String)> {
    let predicted = object_string(object, "predicted_tier").to_ascii_uppercase();
    let confidence = object_string(object, "confidence").to_ascii_lowercase();
    let rationale = object
        .get("rationale")
        .and_then(Value::as_str)
        .map(sanitize_rationale)
        .unwrap_or_default();
    (["TRIVIAL", "MODERATE", "HARD"].contains(&predicted.as_str())
        && ["low", "medium", "high"].contains(&confidence.as_str())
        && !rationale.trim().is_empty())
    .then_some((predicted, confidence))
}

fn regular_non_symlink_file(path: &Path) -> bool {
    fs::symlink_metadata(path)
        .is_ok_and(|metadata| !metadata.file_type().is_symlink() && metadata.file_type().is_file())
}

fn sanitize_rationale(value: &str) -> String {
    let mut text = String::with_capacity(value.len());
    let mut whitespace = false;
    let mut character_count = 0;
    for character in value.chars() {
        let control =
            matches!(character, '\0'..='\u{8}' | '\u{b}' | '\u{c}' | '\u{e}'..='\u{1f}' | '\u{7f}');
        if control {
            whitespace = true;
            continue;
        }
        if character.is_whitespace() {
            whitespace = true;
            continue;
        }
        if whitespace && !text.is_empty() {
            text.push(' ');
        }
        whitespace = false;
        text.push(character);
        character_count += 1;
        if character_count > 500 {
            let retained: String = text.chars().take(499).collect();
            return format!("{retained}…");
        }
    }
    text
}

fn object_string(object: &serde_json::Map<String, Value>, key: &str) -> String {
    object
        .get(key)
        .map_or_else(String::new, |value| match value {
            Value::String(value) => value.clone(),
            Value::Null => String::new(),
            _other => value.to_string(),
        })
}

fn first_nonempty(values: impl IntoIterator<Item = String>) -> String {
    values
        .into_iter()
        .find(|value| !value.is_empty())
        .unwrap_or_default()
}

fn nonempty_string(value: String) -> Option<String> {
    (!value.is_empty()).then_some(value)
}

const fn tier_ceiling(_tier: &str) -> i64 {
    2
}

fn next_tier(tier: &str) -> String {
    match tier {
        "TRIVIAL" => "MODERATE".to_owned(),
        "MODERATE" => "HARD".to_owned(),
        _other => "HARD".to_owned(),
    }
}

fn materialize_design_panel_manifest(round_dir: &Path) -> Result<i64, String> {
    let local = round_dir.join("plan-review-slots.ndjson");
    let source = if regular_file(&local) {
        local
    } else {
        round_dir
            .parent()
            .and_then(Path::parent)
            .map(|path| path.join("plan-review-slots.ndjson"))
            .unwrap_or_default()
    };
    let mut output = String::new();
    let mut count = 0;
    for row in jsonl_objects(&source) {
        let slot = value_string(row.get("slot"));
        let tool = value_string(row.get("tool"));
        let artifact = value_string(row.get("output"));
        if slot.is_empty() && tool.is_empty() && artifact.is_empty() {
            continue;
        }
        output.push('{');
        append_json_field(&mut output, "slot", &slot, false);
        append_json_field(&mut output, "tool", &tool, true);
        append_json_field(&mut output, "output", &artifact, true);
        for key in ["vendor", "resolved_model", "model_role", "focus_area"] {
            let value = value_string(row.get(key));
            if !value.is_empty() {
                append_json_field(&mut output, key, &value, true);
            }
        }
        output.push_str("}\n");
        count += 1;
    }
    let root = TemporaryRoot::resolve(Some(round_dir))
        .map_err(|error| format!("unsafe design round directory: {error}"))?;
    atomic_write_utf8_in(
        &root,
        Path::new("panel-manifest.ndjson"),
        &output,
        false,
        LEGACY_REPORT_FILE_MODE,
    )
    .map_err(|error| format!("write design panel manifest: {error}"))?;
    Ok(count)
}

fn append_json_field(output: &mut String, key: &str, value: &str, comma: bool) {
    if comma {
        output.push(',');
    }
    let key = json_string(key);
    let value = json_string(value);
    let _ = write!(output, "{key}:{value}");
}

fn json_string(value: &str) -> String {
    serde_json::to_string(value)
        .map(|value| ensure_ascii_json(&value))
        .unwrap_or_default()
}

fn count_panel_manifest(path: &Path) -> i64 {
    let count = jsonl_objects(path)
        .into_iter()
        .filter(|row| {
            ["slot", "tool", "output"]
                .iter()
                .any(|key| !value_string(row.get(*key)).is_empty())
        })
        .count();
    i64::try_from(count).unwrap_or(i64::MAX)
}

fn jsonl_objects(path: &Path) -> Vec<serde_json::Map<String, Value>> {
    read_lines(Some(path))
        .into_iter()
        .filter_map(|line| serde_json::from_str::<Value>(&line).ok())
        .filter_map(|value| value.as_object().cloned())
        .collect()
}

fn value_string(value: Option<&Value>) -> String {
    value.map_or_else(String::new, |value| match value {
        Value::String(value) => value.clone(),
        Value::Null => String::new(),
        _other => value.to_string(),
    })
}

fn design_collector(round_dir: &Path, failure_count: i64) -> String {
    if failure_count <= 0 {
        return String::new();
    }
    let local = round_dir.join("collector-results.env");
    let source = if regular_file(&local) {
        local
    } else {
        round_dir
            .parent()
            .and_then(Path::parent)
            .map(|path| path.join("collector-results.env"))
            .unwrap_or_default()
    };
    let records: Vec<String> = collector_records(&read_text(&source))
        .into_iter()
        .filter(|record| !record.status.is_empty() && record.status != "OK")
        .map(|record| {
            format!(
                "TOOL={}\nSTATUS={}\nREVIEWER_FILE={}",
                record.tool,
                record.status,
                basename(&record.reviewer_file)
            )
        })
        .collect();
    if !records.is_empty() {
        return records.join("\n\n");
    }
    (1..=failure_count)
        .map(|index| {
            format!("TOOL=unknown\nSTATUS=FAILED\nREVIEWER_FILE=collector-failure-{index}.txt")
        })
        .collect::<Vec<_>>()
        .join("\n\n")
}

fn phase_round(
    round_dir: &Path,
    skill: PhaseSkill,
    timing: Option<&Path>,
    token_ledger: Option<&Path>,
) -> PhaseRound {
    let meta = read_json_object(&round_dir.join("round-meta.json"));
    let tally = object_value(&meta, "tally");
    let summary = object_value(&meta, "summary");
    let finding_counts = object_value(summary, "finding_counts");
    let panel = object_value(summary, "panel");
    let accepted = tally_value(
        tally,
        "ACCEPTED_COUNT",
        finding_counts.get("total_accepted"),
    );
    let rejected = tally_value(
        tally,
        "REJECTED_COUNT",
        finding_counts.get("total_rejected"),
    );
    let neutral = tally_value(tally, "NEUTRAL_COUNT", finding_counts.get("total_neutral"));
    let exonerated = tally_value(
        tally,
        "EXONERATED_COUNT",
        finding_counts.get("total_exonerated"),
    );
    let (oos_proposed, oos_fileable) = meta_oos_counts(round_dir, tally);
    let reviewers = {
        let total = value_i64(panel.get("total_slot_count"));
        if total == 0 {
            value_i64(panel.get("static_slot_count")) + value_i64(panel.get("dynamic_slot_count"))
        } else {
            total
        }
    };
    let number = round_number(round_dir).unwrap_or(0);
    let table_window = timing.and_then(|path| timing_window(path, skill, number, true));
    let gantt_window = timing.and_then(|path| timing_window(path, skill, number, false));
    let seconds = table_window.and_then(|(start, end)| (end > start).then_some(end - start));
    let canonical = object_value(&meta, "tally_canonical");
    let canonical = (!canonical.is_empty()).then(|| {
        let in_scope = [
            "ACCEPTED_COUNT",
            "REJECTED_COUNT",
            "NEUTRAL_COUNT",
            "EXONERATED_COUNT",
        ]
        .iter()
        .map(|key| tally_value(canonical, key, None))
        .sum();
        let oos = tally_value(
            canonical,
            "OOS_PROPOSED_COUNT",
            canonical.get("OOS_ACCEPTED_COUNT"),
        ) + tally_value(canonical, "OOS_REJECTED_COUNT", None);
        (in_scope, oos)
    });
    PhaseRound {
        number,
        suggestions: accepted + rejected + neutral + exonerated,
        accepted,
        oos_proposed,
        oos_fileable,
        reviewers,
        seconds,
        cost: round_vendor_cost(token_ledger, table_window),
        gantt_window: gantt_window.filter(|(start, end)| end > start),
        canonical,
        nit_pruned: value_i64(meta.get("nit_pruned_count")),
    }
}

fn tally_value(tally: &serde_json::Map<String, Value>, key: &str, fallback: Option<&Value>) -> i64 {
    value_i64(tally.get(key).or(fallback))
}

fn meta_oos_counts(round_dir: &Path, tally: &serde_json::Map<String, Value>) -> (i64, i64) {
    let (counts, source) = round_counts(round_dir);
    let artifact = artifact_oos_split(round_dir, counts, source);
    let fileable = review_tally_fileable(round_dir);
    if tally.contains_key("OOS_PROPOSED_COUNT") {
        return (
            tally_value(tally, "OOS_PROPOSED_COUNT", None),
            fileable.unwrap_or_else(|| tally_value(tally, "OOS_ACCEPTED_COUNT", None)),
        );
    }
    if artifact.present {
        return (artifact.proposed, fileable.unwrap_or(artifact.fileable));
    }
    (
        tally_value(tally, "OOS_ACCEPTED_COUNT", None),
        fileable.unwrap_or(0),
    )
}

fn timing_window(
    path: &Path,
    skill: PhaseSkill,
    round: u64,
    filter_skill: bool,
) -> Option<(i64, i64)> {
    let mut starts = Vec::new();
    let mut ends = Vec::new();
    for line in read_lines(Some(path)) {
        let columns: Vec<&str> = line.split('\t').collect();
        if columns.len() < ROUND_TIMING_MIN_COLUMNS
            || columns.first() != Some(&"v1")
            || columns.get(1) != Some(&"round")
            || (filter_skill && columns.get(3) != Some(&skill.as_str()))
            || columns.get(5).and_then(|value| value.parse::<u64>().ok()) != Some(round)
        {
            continue;
        }
        let (Some(start), Some(end)) = (
            columns.get(6).and_then(|value| value.parse::<i64>().ok()),
            columns.get(7).and_then(|value| value.parse::<i64>().ok()),
        ) else {
            continue;
        };
        starts.push(start);
        ends.push(end);
    }
    Some((*starts.iter().min()?, *ends.iter().max()?))
}

fn timing_attempt_windows(path: &Path, round: u64) -> Vec<(i64, i64, i64)> {
    let mut windows: BTreeMap<i64, (i64, i64)> = BTreeMap::new();
    for line in read_lines(Some(path)) {
        let columns: Vec<&str> = line.split('\t').collect();
        if columns.len() < ROUND_TIMING_MIN_COLUMNS
            || columns.first() != Some(&"v1")
            || columns.get(1) != Some(&"round")
            || columns.get(5).and_then(|value| value.parse::<u64>().ok()) != Some(round)
        {
            continue;
        }
        let (Some(start), Some(end)) = (
            columns.get(6).and_then(|value| value.parse::<i64>().ok()),
            columns.get(7).and_then(|value| value.parse::<i64>().ok()),
        ) else {
            continue;
        };
        let attempt = columns
            .get(ROUND_ATTEMPT_COLUMN)
            .filter(|value| value.bytes().all(|byte| byte.is_ascii_digit()))
            .and_then(|value| value.parse::<i64>().ok())
            .unwrap_or(1);
        windows
            .entry(attempt)
            .and_modify(|(old_start, old_end)| {
                *old_start = (*old_start).min(start);
                *old_end = (*old_end).max(end);
            })
            .or_insert((start, end));
    }
    windows
        .into_iter()
        .map(|(attempt, (start, end))| (attempt, start, end))
        .collect()
}

#[derive(Clone, Copy, Debug, Default)]
struct TokenBucket {
    input: i64,
    cache_read: i64,
    cache_create: i64,
    output: i64,
}

impl TokenBucket {
    fn add_row(&mut self, row: &serde_json::Map<String, Value>) -> Result<(), ()> {
        self.input += token_count(row.get("input"))?;
        self.cache_read += token_count(row.get("cache_read"))?;
        // The retired renderer passed the legacy `cache_create` value through
        // the 5-minute cache-write pricing flag. Preserve that wire behavior.
        self.cache_create += token_count(row.get("cache_create"))?;
        self.output += token_count(row.get("output"))?;
        Ok(())
    }
}

#[derive(Clone, Copy)]
struct TokenRates {
    input: f64,
    cache_read: f64,
    cache_create: f64,
    output: f64,
}

const OPUS_RATES: TokenRates = TokenRates {
    input: 5.0,
    cache_read: 0.5,
    cache_create: 6.25,
    output: 25.0,
};
const SONNET_RATES: TokenRates = TokenRates {
    input: 3.0,
    cache_read: 0.3,
    cache_create: 3.75,
    output: 15.0,
};
const HAIKU_RATES: TokenRates = TokenRates {
    input: 1.0,
    cache_read: 0.1,
    cache_create: 1.25,
    output: 5.0,
};
const FABLE_RATES: TokenRates = TokenRates {
    input: 10.0,
    cache_read: 1.0,
    cache_create: 12.5,
    output: 50.0,
};

#[allow(clippy::too_many_lines)] // One ordered legacy schema-to-pricing mapping preserves cost parity.
fn round_vendor_cost(ledger: Option<&Path>, window: Option<(i64, i64)>) -> String {
    let (Some(ledger), Some((start, end))) = (ledger, window) else {
        return "N/A".to_owned();
    };
    let mut codex = TokenBucket::default();
    let mut codex_mini = TokenBucket::default();
    let mut cursor = TokenBucket::default();
    let mut cursor_grok = TokenBucket::default();
    let mut claude_sub_opus = TokenBucket::default();
    let mut claude_sub_sonnet = TokenBucket::default();
    let mut claude_sub_haiku = TokenBucket::default();
    let mut claude_sub_fable = TokenBucket::default();
    let mut saw_vendor = false;

    for row in jsonl_objects(ledger) {
        if value_string(row.get("type")) != "vendor" {
            continue;
        }
        let timestamp = value_string(row.get("ts"));
        let Some(timestamp) = parse_timestamp(&timestamp) else {
            continue;
        };
        if timestamp < start || timestamp > end {
            continue;
        }
        let vendor = value_string(row.get("vendor"));
        let model = value_string(row.get("model"));
        let raw = value_string(row.get("raw"));
        let bucket = match vendor.as_str() {
            // The Python owner groups all non-mini Codex rows into its default
            // bucket; a recorded Terra model does not receive Terra pricing.
            "codex" if matches!(model.as_str(), "gpt-5.4-mini" | "gpt-5.6-luna") => &mut codex_mini,
            "codex" => &mut codex,
            "cursor" if matches!(model.as_str(), "cursor-grok-4.5-high" | "grok-4.5") => {
                &mut cursor_grok
            }
            "cursor" => &mut cursor,
            "claude_sub" => match if model.is_empty() {
                claude_sub_default_model(&raw).to_owned()
            } else {
                model
            }
            .as_str()
            {
                "claude-sonnet-4-6" => &mut claude_sub_sonnet,
                "claude-haiku-4-5" => &mut claude_sub_haiku,
                "claude-fable-5" => &mut claude_sub_fable,
                // Model names outside the three explicit sub-agent buckets,
                // including the `[1m]` spelling, use the generic Opus lane.
                _other => &mut claude_sub_opus,
            },
            _other => continue,
        };
        saw_vendor = true;
        if bucket.add_row(&row).is_err() {
            return "N/A".to_owned();
        }
    }
    if !saw_vendor {
        return "$0.00".to_owned();
    }

    let codex_default_rates = TokenRates {
        input: env_rate_any(
            &["LARCH_CODEX_INPUT_RATE_PER_M", "LARCH_RATE_CODEX_INPUT"],
            5.0,
        ),
        cache_read: env_rate_any(
            &[
                "LARCH_CODEX_CACHED_INPUT_RATE_PER_M",
                "LARCH_RATE_CODEX_CACHE_READ",
                "LARCH_RATE_CODEX_CACHED_INPUT",
            ],
            0.5,
        ),
        cache_create: 0.0,
        output: env_rate_any(
            &["LARCH_CODEX_OUTPUT_RATE_PER_M", "LARCH_RATE_CODEX_OUTPUT"],
            30.0,
        ),
    };
    let codex_mini_rates = TokenRates {
        input: env_rate_any(
            &[
                "LARCH_CODEX_MINI_INPUT_RATE_PER_M",
                "LARCH_RATE_CODEX_MINI_INPUT",
            ],
            1.0,
        ),
        cache_read: env_rate_any(
            &[
                "LARCH_CODEX_MINI_CACHED_INPUT_RATE_PER_M",
                "LARCH_RATE_CODEX_MINI_CACHE_READ",
                "LARCH_RATE_CODEX_MINI_CACHED_INPUT",
            ],
            0.1,
        ),
        cache_create: 0.0,
        output: env_rate_any(
            &[
                "LARCH_CODEX_MINI_OUTPUT_RATE_PER_M",
                "LARCH_RATE_CODEX_MINI_OUTPUT",
            ],
            6.0,
        ),
    };
    let surcharge = env_rate_any(&["LARCH_CURSOR_TEAMS_SURCHARGE_PER_M"], 0.25);
    let cursor_rates = TokenRates {
        input: env_rate_any(
            &["LARCH_CURSOR_INPUT_RATE_PER_M", "LARCH_RATE_CURSOR_INPUT"],
            0.5 + surcharge,
        ),
        cache_read: env_rate_any(
            &[
                "LARCH_CURSOR_CACHE_READ_RATE_PER_M",
                "LARCH_RATE_CURSOR_CACHE_READ",
            ],
            0.2 + surcharge,
        ),
        cache_create: 0.0,
        output: env_rate_any(
            &["LARCH_CURSOR_OUTPUT_RATE_PER_M", "LARCH_RATE_CURSOR_OUTPUT"],
            2.5 + surcharge,
        ),
    };
    let cursor_grok_rates = TokenRates {
        input: env_rate_any(&["LARCH_CURSOR_GROK_INPUT_RATE_PER_M"], 2.0),
        cache_read: env_rate_any(&["LARCH_CURSOR_GROK_CACHE_READ_RATE_PER_M"], 0.5),
        cache_create: 0.0,
        output: env_rate_any(&["LARCH_CURSOR_GROK_OUTPUT_RATE_PER_M"], 6.0),
    };

    let codex_cost = round_money(bucket_cost(codex, codex_default_rates));
    let codex_mini_cost = round_money(bucket_cost(codex_mini, codex_mini_rates));
    let cursor_composer_cost = round_money(bucket_cost(cursor, cursor_rates));
    let cursor_grok_cost = round_money(bucket_cost(cursor_grok, cursor_grok_rates));
    let cursor_cost = round_money(cursor_composer_cost + cursor_grok_cost);
    let mut claude_sub_cost = round_money(bucket_cost(claude_sub_opus, OPUS_RATES));
    for (bucket, rates) in [
        (claude_sub_sonnet, SONNET_RATES),
        (claude_sub_haiku, HAIKU_RATES),
        (claude_sub_fable, FABLE_RATES),
    ] {
        claude_sub_cost = round_money(claude_sub_cost + round_money(bucket_cost(bucket, rates)));
    }
    format!(
        "${:.2}",
        round_money(codex_cost + codex_mini_cost + cursor_cost + claude_sub_cost)
    )
}

fn parse_timestamp(value: &str) -> Option<i64> {
    DateTime::parse_from_rfc3339(value)
        .ok()
        .map(|value| value.with_timezone(&Utc).timestamp())
}

fn token_count(value: Option<&Value>) -> Result<i64, ()> {
    let value = match value {
        Some(Value::Bool(_)) | None => 0,
        Some(Value::Number(value)) => value
            .as_i64()
            .or_else(|| value.as_f64().map(legacy_float_to_i64))
            .unwrap_or(0),
        Some(Value::String(value)) => value
            .trim()
            .replace(',', "")
            .parse::<f64>()
            .map(legacy_float_to_i64)
            .unwrap_or(0),
        _other => 0,
    };
    (value >= 0).then_some(value).ok_or(())
}

fn bucket_cost(bucket: TokenBucket, rates: TokenRates) -> f64 {
    round_token_component(bucket.input, rates.input)
        + round_token_component(bucket.cache_read, rates.cache_read)
        + round_token_component(bucket.cache_create, rates.cache_create)
        + round_token_component(bucket.output, rates.output)
}

fn round_token_component(tokens: i64, rate: f64) -> f64 {
    if tokens <= 0 {
        0.0
    } else {
        round_to_places(legacy_i64_to_f64(tokens) * rate / 1_000_000.0, 6)
    }
}

#[allow(clippy::cast_precision_loss)] // Legacy Python pricing intentionally uses binary floating-point token math.
const fn legacy_i64_to_f64(value: i64) -> f64 {
    value as f64
}

fn round_money(value: f64) -> f64 {
    round_to_places(value, 2)
}

fn round_to_places(value: f64, places: i32) -> f64 {
    let multiplier = 10_f64.powi(places);
    (value * multiplier).round() / multiplier
}

fn env_rate_any(names: &[&str], default: f64) -> f64 {
    names
        .iter()
        .find_map(|name| {
            env::var(name)
                .ok()
                .and_then(|value| value.trim().parse::<f64>().ok())
                .filter(|value| *value > 0.0 && value.is_finite())
        })
        .unwrap_or(default)
}

fn format_hms(seconds: Option<i64>) -> String {
    let Some(seconds) = seconds.filter(|value| *value > 0) else {
        return "N/A".to_owned();
    };
    let hours = seconds / 3600;
    let minutes = seconds % 3600 / 60;
    let seconds = seconds % 60;
    if hours > 0 {
        format!("{hours}h {minutes:02}m {seconds:02}s")
    } else if minutes > 0 {
        format!("{minutes}m {seconds:02}s")
    } else {
        format!("{seconds}s")
    }
}

fn append_decomposition(output: &mut String, rounds: &[PhaseRound]) {
    let segments: Vec<String> = rounds
        .iter()
        .filter_map(|round| {
            round.canonical.map(|(in_scope, oos)| {
                let mut segment = format!(
                    "round {}: {} finding(s) = {in_scope} in-scope (voted; matches the headline X/Y accepted) + {oos} out-of-scope",
                    round.number,
                    in_scope + oos
                );
                if round.oos_proposed != 0 || round.oos_fileable != 0 {
                    let _ = write!(segment, " ({} OOS proposed, {} OOS fileable)", round.oos_proposed, round.oos_fileable);
                }
                if round.nit_pruned != 0 {
                    let _ = write!(segment, " (incl. {} nit-pruned)", round.nit_pruned);
                }
                segment
            })
        })
        .collect();
    if segments.is_empty() {
        return;
    }
    let _ = writeln!(
        output,
        "_Finding decomposition (canonical, scope-aware): {}. The Suggestions and OOS columns above count findings by finding id (raw per-finding) and can disagree with this scope-aware split when findings are reclassified out-of-scope after voting; round-meta.json records both raw (`tally`) and canonical (`tally_canonical`) counts so downstream joins do not contradict._\n",
        segments.join("; ")
    );
}

fn progress_label_map(round_dirs: &[PathBuf]) -> BTreeMap<String, String> {
    let mut labels = BTreeMap::new();
    for directory in round_dirs {
        for row in jsonl_objects(&directory.join("panel-manifest.ndjson")) {
            let output = value_string(row.get("output"));
            let tool = value_string(row.get("tool"));
            let slot = value_string(row.get("slot"));
            if !output.is_empty() && !tool.is_empty() && !slot.is_empty() {
                labels.insert(basename(&output), format!("{tool}/{slot}"));
            }
        }
    }
    labels
}

fn basename(value: &str) -> String {
    Path::new(value).file_name().map_or_else(
        || value.to_owned(),
        |value| value.to_string_lossy().into_owned(),
    )
}

fn normalized_basename(value: &str) -> String {
    let base = basename(value);
    let (mut stem, extension) = base
        .strip_suffix(".txt")
        .map_or((base.as_str(), ""), |value| (value, ".txt"));
    loop {
        let next = ["-phase2", "-phase3", "-retry"]
            .iter()
            .find_map(|suffix| stem.strip_suffix(suffix));
        let Some(next) = next else {
            break;
        };
        stem = next;
    }
    format!("{stem}{extension}")
}

fn derived_label(output: &str) -> String {
    let base = basename(output);
    let mut core = base
        .strip_suffix(".txt")
        .unwrap_or(&base)
        .to_ascii_lowercase();
    for suffix in ["-output-ns-retry", "-output", "-ns-retry"] {
        if let Some(trimmed) = core.strip_suffix(suffix) {
            let next = trimmed.to_owned();
            core = next;
            break;
        }
    }
    if core == "aggregator" {
        return "aggregator".to_owned();
    }
    if core == "scout-plan-manifest" || core.starts_with("scout-plan-manifest.") {
        return "scout".to_owned();
    }
    if ["codex", "cursor", "claude", "claude_sub"].contains(&core.as_str()) {
        return core;
    }
    for vendor in ["cursor", "codex", "claude_sub", "claude"] {
        if let Some(slot) = core.strip_prefix(&format!("{vendor}-specialist-")) {
            return format!("{vendor}/{slot}");
        }
        if core == format!("{vendor}-generalist") {
            return format!("{vendor}/generalist");
        }
        if let Some(slot) = core.strip_prefix(&format!("{vendor}-")) {
            return format!("{vendor}/{}", if slot.is_empty() { "panel" } else { slot });
        }
    }
    if let Some(slot) = core.strip_prefix("dyn-") {
        return format!("dynamic/{slot}");
    }
    if core.is_empty() || core == "panel" {
        "panel/panel".to_owned()
    } else {
        format!("unknown/{core}")
    }
}

fn is_vendor_fallback_output(output: &str) -> bool {
    let base = basename(output);
    base.strip_suffix(".txt")
        .is_some_and(|value| value.ends_with("-phase2") || value.ends_with("-phase3"))
}

fn derive_label(
    output: &str,
    vendor: &str,
    kind: &str,
    labels: &BTreeMap<String, String>,
) -> String {
    let kind_label = match kind {
        "codex-review-fix" | "codex-plan-autofix" => Some("codex/apply"),
        "cursor-review-fix" | "cursor-plan-autofix" => Some("cursor/apply"),
        "claude-review-fix" => Some("claude/apply"),
        "gate-b-apply" => Some("gate-b/apply"),
        "voter-dispatch-prep" => Some("voter-dispatch-prep"),
        "reviewer-collect" => Some("reviewer-collect"),
        _other => None,
    };
    if let Some(label) = kind_label {
        return label.to_owned();
    }
    let raw = if output == "-" {
        String::new()
    } else {
        basename(output)
    };
    if let Some(label) = labels.get(&raw) {
        return label.clone();
    }
    let fallback = is_vendor_fallback_output(&raw);
    let normalized = normalized_basename(&raw);
    let mut label = labels.get(&normalized).cloned().unwrap_or_else(|| {
        let source = if fallback && !normalized.is_empty() {
            &normalized
        } else {
            &raw
        };
        if source.is_empty() {
            String::new()
        } else {
            derived_label(source)
        }
    });
    if fallback && !label.is_empty() && label != "unknown/-" {
        let (nominal, slot) = label.split_once('/').unwrap_or((&label, ""));
        if !slot.is_empty()
            && ["codex", "cursor", "claude", "claude_sub"].contains(&nominal)
            && nominal != vendor.to_ascii_lowercase()
            && ["codex", "cursor", "claude", "claude_sub"]
                .contains(&vendor.to_ascii_lowercase().as_str())
        {
            label = human_slot_label(slot, vendor);
        }
        return format!("{label} (via fallback)");
    }
    if ["codex", "cursor", "claude", "claude_sub"].contains(&label.as_str())
        && !kind.is_empty()
        && kind != "-"
    {
        label = format!("{label}/{kind}");
    }
    if !label.is_empty() && label != "unknown/-" {
        label
    } else if !vendor.is_empty() && !kind.is_empty() {
        format!("{vendor}/{kind}")
    } else if !vendor.is_empty() {
        vendor.to_owned()
    } else if !kind.is_empty() {
        kind.to_owned()
    } else {
        "unknown".to_owned()
    }
}

fn human_slot_label(slot: &str, tool: &str) -> String {
    let prefixes = [
        ("dyn-cursor-plan-", "Cursor-dyn-"),
        ("dyn-codex-plan-", "Codex-dyn-"),
        ("cursor-plan-", "Cursor-"),
        ("codex-plan-", "Codex-"),
        ("codex-primary-plan-", "Codex-"),
    ];
    for (prefix, label) in prefixes {
        if let Some(tail) = slot.strip_prefix(prefix) {
            return format!("{label}{}", title_words(tail));
        }
    }
    if tool.is_empty() {
        slot.to_owned()
    } else {
        format!("{tool}/{slot}")
    }
}

fn title_words(value: &str) -> String {
    value
        .split('-')
        .map(|word| {
            let mut characters = word.chars();
            characters.next().map_or_else(String::new, |first| {
                first.to_uppercase().collect::<String>() + characters.as_str()
            })
        })
        .collect::<Vec<_>>()
        .join(" ")
}

fn classification_available(round_dirs: &[PathBuf]) -> bool {
    round_dirs
        .iter()
        .any(|directory| classification_has_data(&directory.join("findings-classification.tsv")))
}

fn top_reviewers_from_findings(
    findings: Option<&Path>,
    top_n: usize,
    labels: &BTreeMap<String, String>,
) -> Vec<(String, f64)> {
    let mut scores: BTreeMap<String, f64> = BTreeMap::new();
    if let Some(path) = findings {
        for row in jsonl_objects(path) {
            if value_string(row.get("outcome")) != "accepted" {
                continue;
            }
            let reviewers = row
                .get("reviewer_slots")
                .and_then(Value::as_array)
                .map_or_else(
                    || vec![value_string(row.get("reviewer"))],
                    |values| {
                        values
                            .iter()
                            .map(|value| value_string(Some(value)))
                            .collect()
                    },
                );
            for reviewer in reviewers.into_iter().filter(|value| !value.is_empty()) {
                let base = basename(&reviewer);
                let label = labels
                    .get(&base)
                    .cloned()
                    .unwrap_or_else(|| derived_label(&base));
                *scores.entry(label).or_default() += 1.0;
            }
        }
    }
    sorted_scores(scores, top_n)
}

fn top_reviewers_from_classification(
    round_dirs: &[PathBuf],
    top_n: usize,
    labels: &BTreeMap<String, String>,
) -> Vec<(String, f64)> {
    let mut scores: BTreeMap<String, f64> = BTreeMap::new();
    let corpus = attribution_labels(round_dirs);
    let bonus = env::var("LARCH_UNIQUE_FINDER_BONUS")
        .ok()
        .and_then(|value| value.parse::<f64>().ok())
        .filter(|value| value.is_finite() && *value > 0.0)
        .unwrap_or(0.0);
    for directory in round_dirs {
        for row in parse_classification(&directory.join("findings-classification.tsv")) {
            if row.result() != "accepted" || !row.in_scope() {
                continue;
            }
            let Some(column) = classification_reviewer_column(&row) else {
                continue;
            };
            let cell = row.value(column);
            let raw_sole_finder = raw_sole_finder_attribution(cell, column, &corpus);
            let mut reviewers = split_classification_attribution(cell, column, &corpus);
            if reviewers.is_empty() && column == "finding_reviewers" {
                reviewers = cell
                    .trim()
                    .split(',')
                    .map(str::trim)
                    .filter(|value| !value.is_empty())
                    .map(ToOwned::to_owned)
                    .collect();
            }
            if reviewers.is_empty() {
                continue;
            }
            let mut points = legacy_i64_to_f64(accepted_points(&row));
            if bonus > 0.0 && raw_sole_finder.len() == 1 {
                points += bonus;
            }
            for reviewer in reviewers {
                let label = if column == "reviewer_slots" {
                    labels
                        .get(&reviewer)
                        .cloned()
                        .unwrap_or_else(|| derived_label(&reviewer))
                } else {
                    reviewer
                };
                *scores.entry(label).or_default() += points;
            }
        }
    }
    sorted_scores(scores, top_n)
}

fn attribution_labels(round_dirs: &[PathBuf]) -> BTreeSet<String> {
    let mut labels = BTreeSet::new();
    for directory in round_dirs {
        for map in [
            directory.join("plan-review-prune-label-map.tsv"),
            directory
                .parent()
                .and_then(Path::parent)
                .map(|path| path.join("plan-review-prune-label-map.tsv"))
                .unwrap_or_default(),
        ] {
            for line in read_lines(Some(&map)) {
                if let Some((_slot, label)) = line.split_once('\t')
                    && !label.trim().is_empty()
                {
                    labels.insert(label.trim().to_owned());
                }
            }
        }
        for manifest in [
            directory.join("panel-manifest.ndjson"),
            directory.join("plan-review-slots.ndjson"),
        ] {
            for row in jsonl_objects(&manifest) {
                let slot = value_string(row.get("slot"));
                if !slot.is_empty() {
                    labels.insert(human_slot_label(&slot, ""));
                }
            }
        }
        for row in parse_classification(&directory.join("findings-classification.tsv")) {
            for segment in row.value("finding_reviewers").split(',').map(str::trim) {
                if !segment.is_empty() && !segment.contains(' ') {
                    labels.insert(segment.to_owned());
                }
            }
        }
    }
    labels
}

fn classification_reviewer_column(row: &ClassificationRow) -> Option<&'static str> {
    ["finding_reviewers", "reviewer_slots"]
        .into_iter()
        .find(|column| row.header.iter().any(|header| header == column))
}

fn split_classification_attribution(
    cell: &str,
    column: &str,
    labels: &BTreeSet<String>,
) -> Vec<String> {
    let cell = cell.trim();
    if cell.is_empty() {
        return Vec::new();
    }
    match column {
        "finding_reviewers" => tokenize_finding_reviewers(cell, labels),
        "reviewer_slots" => cell
            .split('|')
            .map(str::trim)
            .filter(|value| !value.is_empty())
            .map(ToOwned::to_owned)
            .collect(),
        _other => vec![cell.to_owned()],
    }
}

fn raw_sole_finder_attribution(cell: &str, column: &str, labels: &BTreeSet<String>) -> Vec<String> {
    let cell = cell.trim();
    if cell.is_empty() {
        return Vec::new();
    }
    if column != "finding_reviewers" {
        return split_classification_attribution(cell, column, labels);
    }
    let parts: Vec<&str> = cell
        .split(',')
        .map(str::trim)
        .filter(|part| !part.is_empty())
        .collect();
    if parts.len() != 1 {
        return Vec::new();
    }
    let tokens = tokenize_finding_reviewers(parts[0], labels);
    if tokens.is_empty() {
        return parts.into_iter().map(ToOwned::to_owned).collect();
    }
    if finding_reviewer_segment_is_fully_tokenized(parts[0], labels) {
        tokens
    } else {
        Vec::new()
    }
}

fn tokenize_finding_reviewers(cell: &str, labels: &BTreeSet<String>) -> Vec<String> {
    let candidates = reviewer_label_candidates(labels);
    let mut tokens = Vec::new();
    let mut seen = BTreeSet::new();
    for segment in cell
        .split(',')
        .map(str::trim)
        .filter(|segment| !segment.is_empty())
    {
        if labels.contains(segment) {
            if seen.insert(segment.to_owned()) {
                tokens.push(segment.to_owned());
            }
            continue;
        }
        let mut position = 0;
        while position < segment.len() {
            let tail = &segment[position..];
            if tail.starts_with(char::is_whitespace) {
                position += tail.chars().next().map_or(0, char::len_utf8);
                continue;
            }
            let Some(label) = candidates.iter().find(|label| label_matches(tail, label)) else {
                break;
            };
            if seen.insert((*label).to_owned()) {
                tokens.push((*label).to_owned());
            }
            position += label.len();
        }
    }
    tokens
}

fn finding_reviewer_segment_is_fully_tokenized(segment: &str, labels: &BTreeSet<String>) -> bool {
    let candidates = reviewer_label_candidates(labels);
    if candidates.is_empty() {
        return false;
    }
    let mut position = 0;
    while position < segment.len() {
        let tail = &segment[position..];
        if tail.starts_with(char::is_whitespace) {
            position += tail.chars().next().map_or(0, char::len_utf8);
            continue;
        }
        let Some(label) = candidates.iter().find(|label| label_matches(tail, label)) else {
            return false;
        };
        position += label.len();
    }
    true
}

fn reviewer_label_candidates(labels: &BTreeSet<String>) -> Vec<&str> {
    let mut candidates: Vec<&str> = labels.iter().map(String::as_str).collect();
    candidates.sort_by(|left, right| {
        right
            .chars()
            .count()
            .cmp(&left.chars().count())
            .then_with(|| left.cmp(right))
    });
    candidates
}

fn label_matches(tail: &str, label: &str) -> bool {
    tail.strip_prefix(label)
        .is_some_and(|remainder| remainder.chars().next().is_none_or(char::is_whitespace))
}

fn accepted_points(row: &ClassificationRow) -> i64 {
    if !row.header.iter().any(|column| column == "scope") || row.value("scope") == "oos" {
        return 1;
    }
    let mut yes = 0;
    let mut major_yes = 0;
    for index in 1..=3 {
        if row
            .value(&format!("v{index}_vote"))
            .eq_ignore_ascii_case("YES")
        {
            yes += 1;
            if row
                .value(&format!("v{index}_severity"))
                .eq_ignore_ascii_case("major")
            {
                major_yes += 1;
            }
        }
    }
    if yes > 0 && major_yes * 2 > yes { 2 } else { 1 }
}

fn sorted_scores(scores: BTreeMap<String, f64>, top_n: usize) -> Vec<(String, f64)> {
    let mut rows: Vec<_> = scores.into_iter().collect();
    rows.sort_by(|(left_label, left_score), (right_label, right_score)| {
        right_score
            .total_cmp(left_score)
            .then_with(|| left_label.cmp(right_label))
    });
    rows.truncate(top_n);
    rows
}

fn format_score(value: f64) -> String {
    if value.fract() == 0.0 {
        format!("{value:.0}")
    } else {
        value.to_string()
    }
}

#[derive(Clone, Debug, Default)]
struct CollectorRecord {
    reviewer_file: String,
    tool: String,
    status: String,
}

fn collector_records(text: &str) -> Vec<CollectorRecord> {
    let mut records = Vec::new();
    let mut current = CollectorRecord::default();
    for line in text.lines().chain(std::iter::once("")) {
        let parsed = KvDocument::parse(line, ParseOptions::legacy())
            .ok()
            .and_then(|document| {
                document
                    .rows()
                    .first()
                    .map(|row| (row.key().to_owned(), row.value().to_owned()))
            });
        let Some((key, value)) = parsed else {
            if line.trim().is_empty()
                && (!current.reviewer_file.is_empty()
                    || !current.tool.is_empty()
                    || !current.status.is_empty())
            {
                records.push(current);
                current = CollectorRecord::default();
            }
            continue;
        };
        match key.as_str() {
            "REVIEWER_FILE" => {
                if !current.reviewer_file.is_empty() {
                    records.push(current);
                    current = CollectorRecord::default();
                }
                value.clone_into(&mut current.reviewer_file);
            }
            "TOOL" => {
                value.clone_into(&mut current.tool);
            }
            "STATUS" => {
                value.clone_into(&mut current.status);
            }
            _other => {}
        }
    }
    records
}

fn collector_paths(round_dir: &Path) -> Vec<PathBuf> {
    let mut paths = vec![round_dir.join("collector-results.env")];
    if let Some(parent) = round_dir.parent() {
        paths.push(parent.join("collector-results.env"));
        if round_dir
            .components()
            .any(|component| component.as_os_str() == "plan-review")
            && let Some(root) = parent.parent()
        {
            paths.push(root.join("collector-results.env"));
        }
    }
    paths
}

fn first_collector_text(round_dir: &Path) -> String {
    collector_paths(round_dir)
        .into_iter()
        .find(|path| regular_file(path) && !read_text(path).is_empty())
        .map_or_else(String::new, |path| read_text(&path))
}

fn fallback_remap(round_dirs: &[PathBuf]) -> BTreeMap<String, String> {
    let mut remap = BTreeMap::new();
    for directory in round_dirs {
        let tools: BTreeMap<String, String> = collector_records(&first_collector_text(directory))
            .into_iter()
            .filter(|record| {
                !record.reviewer_file.is_empty()
                    && !record.tool.is_empty()
                    && record.tool != "unknown"
            })
            .map(|record| (normalized_basename(&record.reviewer_file), record.tool))
            .collect();
        if tools.is_empty() {
            continue;
        }
        for manifest in [directory.join("panel-manifest.ndjson")] {
            for row in jsonl_objects(&manifest) {
                let slot = value_string(row.get("slot"));
                let nominal = value_string(row.get("tool"));
                let output = value_string(row.get("output"));
                let Some(tool) = tools.get(&normalized_basename(&output)) else {
                    continue;
                };
                if !slot.is_empty() && !nominal.is_empty() && nominal != *tool {
                    let base = human_slot_label(&slot, &nominal);
                    remap.insert(base.clone(), format!("{base} (via {})", title_words(tool)));
                }
            }
        }
    }
    remap
}

fn apply_fallback_remap(rows: Vec<(String, f64)>, round_dirs: &[PathBuf]) -> Vec<(String, f64)> {
    let remap = fallback_remap(round_dirs);
    rows.into_iter()
        .map(|(label, score)| (remap.get(&label).cloned().unwrap_or(label), score))
        .collect()
}

fn failed_reviewers(
    round_dirs: &[PathBuf],
    labels: &BTreeMap<String, String>,
) -> (i64, Vec<(String, i64)>) {
    let mut failures: BTreeMap<String, i64> = BTreeMap::new();
    let mut total = 0;
    for directory in round_dirs {
        let text = first_collector_text(directory);
        let mut seen: BTreeSet<String> = collector_records(&text)
            .iter()
            .map(|record| normalized_basename(&record.reviewer_file))
            .filter(|value| !value.is_empty())
            .collect();
        let mut records = collector_records(&text);
        if records.is_empty() {
            records = collector_records(&value_string(
                read_json_object(&directory.join("round-meta.json")).get("collector"),
            ));
        }
        for record in records {
            if record.status.is_empty() || ["OK", "cap_hit"].contains(&record.status.as_str()) {
                continue;
            }
            let normal = normalized_basename(&record.reviewer_file);
            seen.insert(normal.clone());
            let mut label = labels
                .get(&normal)
                .or_else(|| labels.get(&basename(&record.reviewer_file)))
                .cloned()
                .unwrap_or_else(|| derived_label(&normal));
            if !record.tool.is_empty() && label.contains('/') {
                label = format!("{}{}", record.tool, &label[label.find('/').unwrap_or(0)..]);
            }
            *failures.entry(label).or_default() += 1;
            total += 1;
        }
        for path in dropped_slot_files(directory) {
            for line in read_lines(Some(&path)) {
                let values: Vec<&str> = line.split('\t').collect();
                let (Some(slot), Some(tool), Some(reason)) =
                    (values.first(), values.get(1), values.get(2))
                else {
                    continue;
                };
                if !["codex", "cursor"].contains(tool)
                    || (*reason == "straggler-dropped" && !slot.starts_with("dyn-"))
                {
                    continue;
                }
                let normal = dropped_basename(directory, slot, tool);
                if seen.contains(&normal) {
                    continue;
                }
                let label = labels.get(&normal).cloned().unwrap_or_else(|| {
                    if slot.starts_with("dyn-") {
                        format!("{tool}/{slot}")
                    } else {
                        derived_label(&normal)
                    }
                });
                *failures.entry(label).or_default() += 1;
                total += 1;
            }
        }
    }
    let mut rows: Vec<_> = failures.into_iter().collect();
    rows.sort_by(|(left_label, left_count), (right_label, right_count)| {
        right_count
            .cmp(left_count)
            .then_with(|| left_label.cmp(right_label))
    });
    (total, rows)
}

fn dropped_slot_files(round_dir: &Path) -> Vec<PathBuf> {
    let Ok(entries) = fs::read_dir(round_dir) else {
        return Vec::new();
    };
    let mut files: Vec<PathBuf> = entries
        .flatten()
        .map(|entry| entry.path())
        .filter(|path| {
            path.file_name()
                .is_some_and(|name| name.to_string_lossy().ends_with(".dropped-slots"))
        })
        .collect();
    files.sort_by_key(|path| {
        (
            !path.file_name().is_some_and(|name| {
                name.to_string_lossy()
                    .ends_with(".output-files.dropped-slots")
            }),
            path.clone(),
        )
    });
    files
}

fn dropped_basename(round_dir: &Path, slot: &str, tool: &str) -> String {
    let mapped = jsonl_objects(&round_dir.join("panel-manifest.ndjson"))
        .into_iter()
        .find(|row| value_string(row.get("slot")) == slot && value_string(row.get("tool")) == tool)
        .map(|row| normalized_basename(&value_string(row.get("output"))));
    mapped.unwrap_or_else(|| {
        if slot.starts_with("dyn-") {
            let archetype = slot
                .trim_start_matches("dyn-")
                .strip_suffix("-codex")
                .filter(|_value| tool == "codex")
                .unwrap_or_else(|| slot.trim_start_matches("dyn-"));
            format!(
                "dyn-{}{}-output.txt",
                archetype,
                if tool == "codex" { "-codex" } else { "" }
            )
        } else if slot == "generalist" && tool == "codex" {
            "codex-generalist-output.txt".to_owned()
        } else {
            format!("{tool}-specialist-{slot}-output.txt")
        }
    })
}

#[derive(Clone, Debug)]
struct GanttRow {
    label: String,
    start: i64,
    end: i64,
}

fn render_gantts(
    round_dirs: &[PathBuf],
    timing: Option<&Path>,
    rounds: &[PhaseRound],
    labels: &BTreeMap<String, String>,
) -> String {
    let Some(timing) = timing else {
        return String::new();
    };
    let by_number: BTreeMap<u64, &PhaseRound> =
        rounds.iter().map(|round| (round.number, round)).collect();
    let mut sections = Vec::new();
    for directory in round_dirs {
        let number = round_number(directory).unwrap_or(0);
        let Some(round) = by_number.get(&number) else {
            continue;
        };
        let Some((fallback_start, fallback_end)) = round.gantt_window else {
            continue;
        };
        let mut attempts = timing_attempt_windows(timing, number);
        if attempts.is_empty() {
            attempts.push((1, fallback_start, fallback_end));
        }
        let multiple = attempts.len() > 1;
        for (attempt, start, end) in attempts {
            let suffix = if multiple {
                format!(" (attempt {attempt})")
            } else {
                String::new()
            };
            let rows = vendor_rows(timing, start, end, labels, true, false);
            let mut section = format!("### Round {number} reviewer timing{suffix}\n\n");
            if let Some(chart) = render_gantt(start, end, &rows) {
                let span = end - start;
                let _ = write!(
                    section,
                    "```\nRound {number} reviewer timing{suffix}  ·  window 0:00-{} ({span}s)\n{chart}\n```\n",
                    format_mss(span)
                );
            } else {
                section.push_str("No reviewer timing tasks overlapped this round.\n");
            }
            sections.push(section);
        }
    }
    if sections.is_empty() {
        String::new()
    } else {
        format!("{}\n\n", sections.join("\n").trim_end_matches('\n'))
    }
}

fn vendor_rows(
    ledger: &Path,
    window_start: i64,
    window_end: i64,
    labels: &BTreeMap<String, String>,
    skip_ci: bool,
    require_complete: bool,
) -> Vec<GanttRow> {
    if window_end <= window_start {
        return Vec::new();
    }
    let mut rows = Vec::new();
    for line in read_lines(Some(ledger)) {
        let columns: Vec<&str> = line.split('\t').collect();
        if columns.len() < VENDOR_TIMING_MIN_COLUMNS
            || columns.first() != Some(&"v1")
            || columns.get(1) != Some(&"vendor")
        {
            continue;
        }
        let status = columns.get(12).copied().unwrap_or_default();
        if require_complete && !["complete", "OK"].contains(&status) {
            continue;
        }
        let (Some(start), Some(end)) = (
            columns.get(7).and_then(|value| value.parse::<i64>().ok()),
            columns.get(8).and_then(|value| value.parse::<i64>().ok()),
        ) else {
            continue;
        };
        if end <= window_start || start >= window_end {
            continue;
        }
        let output = columns.get(10).copied().unwrap_or_default();
        let kind = columns.get(6).copied().unwrap_or_default();
        if skip_ci && ci_row(kind, output) {
            continue;
        }
        let clamped_start = start.max(window_start);
        let clamped_end = end.min(window_end);
        if clamped_end <= clamped_start {
            continue;
        }
        rows.push(GanttRow {
            label: derive_label(
                output,
                columns.get(5).copied().unwrap_or_default(),
                kind,
                labels,
            ),
            start: clamped_start,
            end: clamped_end,
        });
    }
    rows.sort_by(|left, right| {
        (left.start, left.end, left.label.as_str()).cmp(&(
            right.start,
            right.end,
            right.label.as_str(),
        ))
    });
    rows
}

fn ci_row(kind: &str, output: &str) -> bool {
    let kind = kind.to_ascii_lowercase();
    let output = basename(output).to_ascii_lowercase();
    [
        "codex-ci",
        "cursor-ci",
        "claude-ci",
        "codex-ci-fix",
        "cursor-ci-fix",
        "claude-ci-fix",
    ]
    .contains(&kind.as_str())
        || kind.ends_with("-ci")
        || kind.ends_with("-ci-fix")
        || kind.ends_with("-ci-test")
        || output == "ci.out"
        || output.ends_with("-ci.out")
        || (output.starts_with("ci-fix-")
            && Path::new(&output)
                .extension()
                .is_some_and(|extension| extension == "out"))
        || ["claude.out", "codex.out", "cursor.out"].contains(&output.as_str())
}

fn render_gantt(window_start: i64, window_end: i64, rows: &[GanttRow]) -> Option<String> {
    let span = (window_end - window_start).max(1);
    let filtered: Vec<(&GanttRow, i64, i64, i64)> = rows
        .iter()
        .filter_map(|row| {
            let start = row.start.max(window_start);
            let end = row.end.min(window_end);
            (end > start).then_some((row, start, end, end - start))
        })
        .collect();
    if filtered.is_empty() {
        return None;
    }
    let label_width = filtered
        .iter()
        .map(|(row, _, _, _)| char_len(&row.label))
        .max()
        .unwrap_or(0);
    let duration_width = filtered
        .iter()
        .map(|(_, _, _, duration)| format!("{duration}s").len())
        .max()
        .unwrap_or(0);
    let width = 56.min(
        90usize
            .saturating_sub(label_width)
            .saturating_sub(duration_width)
            .saturating_sub(4)
            .max(10),
    );
    let prefix = " ".repeat(label_width + 1);
    let mut lines = vec![gantt_axis(label_width, width, &format_mss(span))];
    lines.push(format!("{prefix}┌{}┐", "─".repeat(width)));
    for (row, start, end, duration) in filtered {
        let label = pad_right(&row.label, label_width);
        let duration = format!("{duration}s");
        lines.push(format!(
            "{label} │{}│ {}",
            gantt_bar(start, end, window_start, span, width),
            pad_left(&duration, duration_width)
        ));
    }
    lines.push(format!("{prefix}└{}┘", "─".repeat(width)));
    Some(lines.join("\n"))
}

fn gantt_axis(label_width: usize, width: usize, span: &str) -> String {
    let start = label_width + 2;
    let end = start + width - 1;
    let mut characters = vec![' '; end + 1];
    for (index, character) in "0:00".chars().enumerate() {
        if start + index < characters.len() {
            characters[start + index] = character;
        }
    }
    let right = start.max(end.saturating_sub(char_len(span)).saturating_add(1));
    for (index, character) in span.chars().enumerate() {
        if right + index < characters.len() {
            characters[right + index] = character;
        }
    }
    characters
        .into_iter()
        .collect::<String>()
        .trim_end()
        .to_owned()
}

fn gantt_bar(start: i64, end: i64, window_start: i64, span: i64, width: usize) -> String {
    let rounded_start = legacy_gantt_position((start - window_start).max(0), span, width);
    let rounded_end = legacy_gantt_position((end - window_start).max(0), span, width);
    let start = rounded_start.min(width.saturating_sub(1));
    let end = rounded_end.max(start + 1).min(width);
    format!(
        "{}{}{}",
        " ".repeat(start),
        "█".repeat(end - start),
        " ".repeat(width - end)
    )
}

#[allow(
    clippy::cast_precision_loss,
    clippy::cast_possible_truncation,
    clippy::cast_sign_loss,
    clippy::cast_possible_wrap
)] // The retired Python Gantt uses this IEEE-754 formula and clamps its integer result.
fn legacy_gantt_position(value: i64, span: i64, width: usize) -> usize {
    round_half_up(value as f64 * width as f64 / span as f64).clamp(0, width as i64) as usize
}

#[allow(clippy::cast_possible_truncation)] // Mirrors the retired Python `int(value + 0.5)` rounding.
fn round_half_up(value: f64) -> i64 {
    (value + 0.5) as i64
}

fn format_mss(seconds: i64) -> String {
    let seconds = seconds.max(0);
    format!("{}:{:02}", seconds / 60, seconds % 60)
}

fn char_len(value: &str) -> usize {
    value.chars().count()
}

fn pad_right(value: &str, width: usize) -> String {
    format!(
        "{value}{}",
        " ".repeat(width.saturating_sub(char_len(value)))
    )
}

fn pad_left(value: &str, width: usize) -> String {
    format!(
        "{}{value}",
        " ".repeat(width.saturating_sub(char_len(value)))
    )
}
