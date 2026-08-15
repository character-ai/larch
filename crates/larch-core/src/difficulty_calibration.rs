//! Retrospective difficulty calibration over a synchronized run-log corpus.

use crate::{
    RunLogSlug,
    difficulty::{HARD, MODERATE, TIERS, TRIVIAL, normalize_tier, tier_max, tier_rank},
    report::{
        RunLogCorpus, RunLogCorpusEvent, RunLogCorpusWarningKind, RunLogRoundSort, RunLogSelection,
        TOKEN_VENDORS, TokenObservations, TokenRates, TokenVendor, claude_effective_cache_create,
        display_rates, effective_vendor_total, python_round, round_number_from_path, safe_int,
        vendor_totals_from_report,
    },
    review::code_review_classification_required_fields,
    run_log::python_string,
};
use chrono::{DateTime, Datelike as _, NaiveDate, NaiveDateTime, Utc};
use serde_json::{Map, Value};
use std::{
    collections::{BTreeMap, BTreeSet},
    fmt::Write as _,
    fs,
    path::{Path, PathBuf},
};

const SKILLS: [&str; 3] = ["design", "implement", "review"];
const UNKNOWN: &str = "unknown";
const ACCEPTED_HARD_THRESHOLD: usize = 3;
const SIDECAR_PATH: &str = "rejected-analysis/verdicts.tsv";
const LEGACY_SIDECAR_PATH: &str = "rejected-analysis-verdicts.tsv";
const DIFFICULTY_RECORD: &str = "difficulty-rating.json";

type TextRow = BTreeMap<String, String>;

#[derive(Clone)]
struct FindingIdentity {
    key: String,
    round: i64,
    finding_id: String,
}

#[derive(Default)]
struct Classification {
    accepted_count: Option<usize>,
    accepted: Vec<FindingIdentity>,
}

#[derive(Default)]
struct Metrics {
    tokens: Option<i128>,
    cost: Option<f64>,
    latency: Option<i128>,
}

struct RunRecord {
    skill: &'static str,
    run_id: String,
    rel_link: String,
    manifest: Map<String, Value>,
    rating: Option<Map<String, Value>>,
    classification: Classification,
    realized_tier: String,
    metrics: Metrics,
    sidecar_rows: Vec<TextRow>,
    sidecar_present: bool,
}

impl RunRecord {
    fn rating_tier(&self, key: &str) -> String {
        self.rating.as_ref().map_or_else(String::new, |rating| {
            normalize_tier(&legacy_text(rating.get(key)), "")
        })
    }

    fn applied_tier(&self) -> String {
        self.rating_tier("applied_tier")
    }

    fn predicted_tier(&self) -> String {
        self.rating_tier("predicted_tier")
    }

    fn rater_key(&self) -> String {
        self.rating.as_ref().map_or_else(
            || UNKNOWN.to_owned(),
            |rating| {
                ["rater", "rater_tool", "rater_model"]
                    .map(|key| unknown_if_empty(rating.get(key)))
                    .join("/")
            },
        )
    }

    fn panel_skipped(&self) -> String {
        self.rating.as_ref().map_or_else(String::new, |rating| {
            legacy_text(rating.get("panel_skipped"))
        })
    }

    fn issue_number(&self) -> String {
        let number = safe_int(self.manifest.get("issue_number"), 0);
        if number > 0 {
            number.to_string()
        } else {
            "n/a".to_owned()
        }
    }

    fn started_month(&self) -> Option<String> {
        started_month(self.manifest.get("started_at"))
    }

    fn audit_upgraded(&self) -> bool {
        self.rating
            .as_ref()
            .is_some_and(|rating| truthy(rating.get("audit_upgrade")))
    }

    fn pre_audit_tier(&self) -> Option<String> {
        let rating = self.rating.as_ref()?;
        let mut tiers: Vec<String> = ["design_tier", "implement_tier", "predicted_tier"]
            .into_iter()
            .map(|key| normalize_tier(&legacy_text(rating.get(key)), ""))
            .filter(|tier| !tier.is_empty())
            .collect();
        if let Some(floors) = rating.get("floors_applied").and_then(Value::as_array) {
            tiers.extend(floors.iter().filter_map(|floor| {
                let tier = normalize_tier(
                    &legacy_text(floor.as_object().and_then(|row| row.get("floor"))),
                    "",
                );
                (!tier.is_empty()).then_some(tier)
            }));
        }
        (!tiers.is_empty()).then(|| tier_max(tiers.iter().map(String::as_str)))
    }
}

#[derive(Default)]
struct State {
    counters: BTreeMap<&'static str, usize>,
}

impl State {
    fn bump(&mut self, key: &'static str, amount: usize) {
        if amount == 0 {
            return;
        }
        *self.counters.entry(key).or_default() += amount;
    }
}

#[derive(Default)]
struct SidecarIndex {
    by_run: BTreeMap<(String, String), Vec<TextRow>>,
    present: bool,
}

fn regular_file(path: &Path) -> bool {
    fs::symlink_metadata(path)
        .is_ok_and(|metadata| !metadata.file_type().is_symlink() && metadata.is_file())
}

fn read_text(path: &Path, state: &mut State, counter: &'static str) -> Option<String> {
    if !regular_file(path) {
        state.bump(counter, 1);
        return None;
    }
    fs::read(path).map_or_else(
        |_| {
            state.bump(counter, 1);
            None
        },
        |bytes| Some(String::from_utf8_lossy(&bytes).into_owned()),
    )
}

fn read_json(path: &Path, state: &mut State, counter: &'static str) -> Option<Value> {
    let text = read_text(path, state, counter)?;
    serde_json::from_str(&text).ok().or_else(|| {
        state.bump(counter, 1);
        None
    })
}

fn unknown_if_empty(value: Option<&Value>) -> String {
    let value = legacy_text(value).trim().to_owned();
    if value.is_empty() {
        UNKNOWN.to_owned()
    } else {
        value
    }
}

fn truthy(value: Option<&Value>) -> bool {
    value == Some(&Value::Bool(true))
        || matches!(
            legacy_text(value).trim().to_ascii_lowercase().as_str(),
            "1" | "true" | "yes" | "y"
        )
}

fn legacy_text(value: Option<&Value>) -> String {
    value
        .filter(|value| match value {
            Value::Null | Value::Bool(false) => false,
            Value::String(text) => !text.is_empty(),
            Value::Number(number) => number.as_f64() != Some(0.0),
            Value::Array(items) => !items.is_empty(),
            Value::Object(items) => !items.is_empty(),
            Value::Bool(true) => true,
        })
        .map_or_else(String::new, python_string)
}

fn manifest(run_dir: &Path, state: &mut State) -> Map<String, Value> {
    let path = run_dir.join("manifest.json");
    if !regular_file(&path) {
        state.bump("missing_manifests", 1);
        return Map::new();
    }
    if let Some(Value::Object(value)) = read_json(&path, state, "malformed_manifests") {
        value
    } else {
        state.bump("malformed_manifests", 1);
        Map::new()
    }
}

fn rating(run_dir: &Path, state: &mut State) -> Option<Map<String, Value>> {
    let path = run_dir.join(DIFFICULTY_RECORD);
    if !regular_file(&path) {
        state.bump("unratable_missing_rating", 1);
        return None;
    }
    let text = read_text(&path, state, "unratable_malformed_rating")?;
    let Ok(parsed) = serde_json::from_str::<Value>(&text) else {
        state.bump("unratable_malformed_rating", 1);
        return None;
    };
    let Value::Object(value) = parsed else {
        state.bump("unratable_malformed_rating", 1);
        return None;
    };
    if normalize_tier(&legacy_text(value.get("applied_tier")), "").is_empty() {
        state.bump("unratable_malformed_rating", 1);
        return None;
    }
    Some(value)
}

fn safe_run_dirs(log_root: &Path, skill: &str, state: &mut State) -> Vec<PathBuf> {
    let slug = RunLogSlug::parse(skill).expect("fixed skill slug");
    for event in RunLogCorpus::new(log_root).select(RunLogSelection::for_skill(slug)) {
        let RunLogCorpusEvent::Warning(warning) = event else {
            continue;
        };
        match warning.kind() {
            RunLogCorpusWarningKind::RootMissing => state.bump("missing_skill_roots", 1),
            RunLogCorpusWarningKind::RootUnreadable => state.bump("unreadable_skill_roots", 1),
            RunLogCorpusWarningKind::ChildSymlink
            | RunLogCorpusWarningKind::ChildUnresolvable
            | RunLogCorpusWarningKind::ChildEscapes => state.bump("unsafe_run_dirs", 1),
            _ => {}
        }
    }
    RunLogCorpus::new(log_root.join(skill)).safe_child_run_directories()
}

fn classification_paths(
    skill: &str,
    run_dir: &Path,
    tsv_by_run: &BTreeMap<PathBuf, Vec<PathBuf>>,
) -> Vec<PathBuf> {
    let canonical = fs::canonicalize(run_dir).unwrap_or_else(|_| run_dir.to_owned());
    let tsvs = tsv_by_run.get(&canonical).cloned().unwrap_or_default();
    if !tsvs.is_empty() {
        return tsvs;
    }
    let candidates: &[&str] = match skill {
        "implement" => &["review-findings-full.jsonl"],
        "review" => &["review-findings.ndjson", "review-findings-full.jsonl"],
        _ => &[],
    };
    candidates
        .iter()
        .map(|name| run_dir.join(name))
        .find(|path| path.is_file())
        .into_iter()
        .collect()
}

fn parse_tsv(text: &str) -> Result<(Vec<String>, Vec<TextRow>), csv::Error> {
    let filtered = text
        .lines()
        .filter(|line| !line.trim().is_empty())
        .collect::<Vec<_>>()
        .join("\n");
    if filtered.is_empty() {
        return Ok((Vec::new(), Vec::new()));
    }
    let mut reader = csv::ReaderBuilder::new()
        .delimiter(b'\t')
        .flexible(true)
        .from_reader(filtered.as_bytes());
    let header: Vec<String> = reader.headers()?.iter().map(str::to_owned).collect();
    let rows = reader
        .records()
        .map(|record| {
            let record = record?;
            Ok(header
                .iter()
                .enumerate()
                .map(|(index, key)| (key.clone(), record.get(index).unwrap_or("").to_owned()))
                .collect())
        })
        .collect::<Result<_, csv::Error>>()?;
    Ok((header, rows))
}

fn schema_supported(skill: &str, header: &[String]) -> bool {
    let fields: BTreeSet<String> = header.iter().cloned().collect();
    if skill == "design" {
        return [
            "finding_id",
            "finding_reviewers",
            "voting_result",
            "v1_vote",
            "v2_vote",
            "v3_vote",
        ]
        .into_iter()
        .all(|field| fields.contains(field));
    }
    code_review_classification_required_fields(false, false).is_subset(&fields)
        || code_review_classification_required_fields(true, true).is_subset(&fields)
}

fn row_in_scope(row: &TextRow, finding_id: &str) -> bool {
    let scope = row
        .get("scope")
        .map_or("", String::as_str)
        .trim()
        .to_ascii_lowercase();
    if matches!(scope.as_str(), "oos" | "out_of_scope" | "out-of-scope")
        || finding_id.to_ascii_uppercase().starts_with("OOS_")
    {
        return false;
    }
    true
}

fn tsv_identity(skill: &str, round: i64, finding_id: &str) -> FindingIdentity {
    FindingIdentity {
        key: if skill == "design" {
            format!("design:{finding_id}")
        } else {
            format!("{round}:{finding_id}")
        },
        round,
        finding_id: finding_id.to_owned(),
    }
}

fn parse_tsv_source(
    path: &Path,
    skill: &str,
    state: &mut State,
) -> (Vec<(FindingIdentity, bool)>, bool) {
    let Some(text) = read_text(path, state, "unreadable_classification_sources") else {
        return (Vec::new(), false);
    };
    let Ok((header, rows)) = parse_tsv(&text) else {
        state.bump("unsupported_classification_sources", 1);
        return (Vec::new(), false);
    };
    if !schema_supported(skill, &header) {
        if !text.trim().is_empty() {
            state.bump("unsupported_classification_sources", 1);
        }
        return (Vec::new(), false);
    }
    let round = i64::from(round_number_from_path(path).unwrap_or(0));
    let mut parsed = Vec::new();
    let mut malformed = 0;
    for row in rows {
        let finding_id = row.get("finding_id").map_or("", String::as_str).trim();
        if finding_id.is_empty() {
            malformed += 1;
            continue;
        }
        let result = row
            .get("voting_result")
            .map_or("", String::as_str)
            .trim()
            .to_ascii_lowercase();
        let accepted = result == "accepted" && row_in_scope(&row, finding_id);
        if !matches!(result.as_str(), "accepted" | "rejected" | "neutral") {
            malformed += 1;
        }
        parsed.push((tsv_identity(skill, round, finding_id), accepted));
    }
    state.bump("malformed_classification_rows", malformed);
    (parsed, true)
}

fn first_value<'a>(record: &'a Map<String, Value>, keys: &[&str]) -> Option<&'a Value> {
    keys.iter().find_map(|key| {
        record.get(*key).filter(|value| match value {
            Value::Null | Value::Bool(false) => false,
            Value::String(text) => !text.is_empty(),
            Value::Number(number) => number.as_f64() != Some(0.0),
            Value::Array(items) => !items.is_empty(),
            Value::Object(items) => !items.is_empty(),
            Value::Bool(true) => true,
        })
    })
}

fn json_identity(
    skill: &str,
    record: &Map<String, Value>,
    round: i64,
    fallback: &str,
) -> FindingIdentity {
    let hash = legacy_text(record.get("finding_hash")).trim().to_owned();
    let id = legacy_text(record.get("id")).trim().to_owned();
    let key = if !hash.is_empty() {
        format!("hash:{hash}")
    } else if skill == "design" && !id.is_empty() {
        format!("id:{id}")
    } else {
        format!("{round}:{fallback}")
    };
    FindingIdentity {
        key,
        round,
        finding_id: fallback.to_owned(),
    }
}

fn parse_jsonl_source(
    path: &Path,
    skill: &str,
    state: &mut State,
) -> (Vec<(FindingIdentity, bool)>, bool) {
    let Some(text) = read_text(path, state, "unreadable_classification_sources") else {
        return (Vec::new(), false);
    };
    let mut parsed = Vec::new();
    let mut malformed_json = 0;
    let mut malformed_rows = 0;
    let mut unsupported = 0;
    for line in text.lines().filter(|line| !line.trim().is_empty()) {
        let Ok(Value::Object(record)) = serde_json::from_str::<Value>(line) else {
            malformed_json += 1;
            continue;
        };
        let phase = legacy_text(record.get("phase")).trim().to_ascii_lowercase();
        if !matches!(phase.as_str(), "code-review" | "code_review") {
            unsupported += 1;
            continue;
        }
        let round = safe_int(record.get("round_num"), 0).max(0);
        let finding_id = legacy_text(first_value(&record, &["finding_id", "id", "finding_hash"]))
            .trim()
            .to_owned();
        if finding_id.is_empty() {
            malformed_rows += 1;
            continue;
        }
        let scope = legacy_text(record.get("scope")).trim().to_ascii_lowercase();
        if finding_id.to_ascii_uppercase().starts_with("OOS_")
            || matches!(scope.as_str(), "oos" | "out_of_scope" | "out-of-scope")
        {
            continue;
        }
        let outcome = legacy_text(first_value(&record, &["outcome", "voting_result"]))
            .trim()
            .to_ascii_lowercase();
        if !matches!(outcome.as_str(), "" | "accepted" | "rejected" | "neutral") {
            malformed_rows += 1;
        }
        parsed.push((
            json_identity(skill, &record, round, &finding_id),
            outcome == "accepted",
        ));
    }
    state.bump(
        "malformed_classification_rows",
        malformed_json + malformed_rows,
    );
    state.bump("unsupported_classification_rows", unsupported);
    let parseable = !parsed.is_empty() || malformed_json + malformed_rows + unsupported == 0;
    (parsed, parseable)
}

fn classification(skill: &str, sources: &[PathBuf], state: &mut State) -> Classification {
    if sources.is_empty() {
        state.bump("missing_classification_sources", 1);
        return Classification::default();
    }
    let mut rows: BTreeMap<String, (FindingIdentity, bool)> = BTreeMap::new();
    let mut parseable = false;
    for source in sources {
        let (source_rows, source_parseable) = if matches!(
            source.extension().and_then(|value| value.to_str()),
            Some("jsonl" | "ndjson")
        ) {
            parse_jsonl_source(source, skill, state)
        } else {
            parse_tsv_source(source, skill, state)
        };
        parseable |= source_parseable;
        for (identity, accepted) in source_rows {
            if rows
                .get(&identity.key)
                .is_none_or(|(current, _)| identity.round >= current.round)
            {
                rows.insert(identity.key.clone(), (identity, accepted));
            }
        }
    }
    if !parseable {
        state.bump("unknown_realized_no_parseable_source", 1);
        return Classification::default();
    }
    let mut accepted: Vec<_> = rows
        .into_values()
        .filter_map(|(identity, accepted)| accepted.then_some(identity))
        .collect();
    accepted.sort_by(|left, right| {
        (left.round, &left.finding_id, &left.key).cmp(&(right.round, &right.finding_id, &right.key))
    });
    Classification {
        accepted_count: Some(accepted.len()),
        accepted,
    }
}

fn realized_tier(
    rating: Option<&Map<String, Value>>,
    classification: &Classification,
    state: &mut State,
) -> String {
    if rating
        .and_then(|value| value.get("escalations"))
        .and_then(Value::as_array)
        .is_some_and(|rows| !rows.is_empty())
    {
        return HARD.to_owned();
    }
    match classification.accepted_count {
        None => {
            state.bump("unknown_realized_tiers", 1);
            UNKNOWN.to_owned()
        }
        Some(0) => TRIVIAL.to_owned(),
        Some(count) if count >= ACCEPTED_HARD_THRESHOLD => HARD.to_owned(),
        Some(_) => MODERATE.to_owned(),
    }
}

#[allow(
    clippy::cast_precision_loss,
    clippy::similar_names,
    clippy::suboptimal_flops
)] // Preserve the retired Python owner's arithmetic order for byte-level report parity.
fn vendor_cost(
    vendor: TokenVendor,
    totals: &crate::report::VendorTotals,
    rates: &TokenRates,
) -> f64 {
    let value = match vendor {
        TokenVendor::Codex => {
            totals.input as f64 * rates.codex_input
                + totals.cached_input as f64 * rates.codex_cached_input
                + totals.output as f64 * rates.codex_output
        }
        TokenVendor::Cursor => {
            totals.input as f64 * rates.cursor_input
                + totals.cache_read as f64 * rates.cursor_cache_read
                + totals.output as f64 * rates.cursor_output
        }
        TokenVendor::Claude | TokenVendor::ClaudeSub => {
            let (create_5m, create_1h) = claude_effective_cache_create(totals);
            totals.input as f64 * rates.claude_input
                + totals.cache_read as f64 * rates.claude_cache_read
                + create_5m as f64 * rates.claude_cache_create_5m
                + create_1h as f64 * rates.claude_cache_create_1h
                + totals.output as f64 * rates.claude_output
        }
    };
    value / 1_000_000.0
}

#[allow(clippy::cast_precision_loss)]
fn metrics(
    skill: &str,
    run_dir: &Path,
    environment: &BTreeMap<String, String>,
    state: &mut State,
) -> Metrics {
    let token_name = if skill == "design" {
        "token-report-final.json"
    } else {
        "token-report.json"
    };
    let timing_name = if skill == "design" {
        "timing-report-final.json"
    } else {
        "timing-report.json"
    };
    let mut result = Metrics::default();
    if let Some(Value::Object(report)) = read_json(
        &run_dir.join(token_name),
        state,
        "missing_or_malformed_token_reports",
    ) {
        let rates = display_rates(environment, "", &mut TokenObservations::default());
        let mut tokens = 0_i128;
        let mut cost = 0.0;
        for vendor in TOKEN_VENDORS {
            let totals = vendor_totals_from_report(&report, vendor);
            tokens = tokens.saturating_add(i128::from(effective_vendor_total(&totals, vendor)));
            cost += vendor_cost(vendor, &totals, &rates);
        }
        result.tokens = Some(tokens);
        result.cost = Some(cost);
    }
    if let Some(Value::Object(report)) = read_json(
        &run_dir.join(timing_name),
        state,
        "missing_or_malformed_timing_reports",
    ) {
        let mut seconds = i128::from(safe_int(report.get("total_seconds"), 0));
        if seconds <= 0
            && let Some(steps) = report.get("per_step").and_then(Value::as_array)
        {
            seconds = steps
                .iter()
                .filter_map(Value::as_object)
                .map(|step| safe_int(step.get("duration_seconds"), 0))
                .map(i128::from)
                .fold(0_i128, i128::saturating_add);
        }
        if seconds > 0 {
            result.latency = Some(seconds);
        }
    }
    result
}

fn sidecar(state_root: &Path, state: &mut State) -> SidecarIndex {
    let primary = state_root.join(SIDECAR_PATH);
    let path = if primary.is_file() {
        primary
    } else {
        state_root.join(LEGACY_SIDECAR_PATH)
    };
    if !regular_file(&path) {
        state.bump("missing_rejected_sidecar", 1);
        return SidecarIndex::default();
    }
    let Some(text) = read_text(&path, state, "malformed_rejected_sidecar") else {
        return SidecarIndex::default();
    };
    let Ok((_header, rows)) = parse_tsv(&text) else {
        state.bump("malformed_rejected_sidecar", 1);
        return SidecarIndex::default();
    };
    let mut deduped = BTreeMap::new();
    let mut hashes = BTreeSet::new();
    let mut unhashed = BTreeSet::new();
    let mut duplicates = 0;
    for row in rows {
        let get = |key: &str| row.get(key).map_or("", String::as_str);
        let hash = get("finding_hash").trim();
        let fields = [
            "source_skill",
            "run_id",
            "round_num",
            "finding_id",
            "verdict",
            "current_location",
            "evidence",
            "triaged_at",
        ];
        let plain_key = fields.map(get).join("\0");
        if (!hash.is_empty() && !hashes.insert(hash.to_owned()))
            || (hash.is_empty() && !unhashed.insert(plain_key.clone()))
        {
            duplicates += 1;
        }
        deduped.insert(
            format!(
                "{}\0{plain_key}",
                if hash.is_empty() { "row" } else { hash }
            ),
            row,
        );
    }
    state.bump("duplicate_sidecar_rows", duplicates);
    let mut by_run: BTreeMap<(String, String), Vec<TextRow>> = BTreeMap::new();
    for row in deduped.into_values() {
        let key = (
            row.get("source_skill").cloned().unwrap_or_default(),
            row.get("run_id").cloned().unwrap_or_default(),
        );
        by_run.entry(key).or_default().push(row);
    }
    SidecarIndex {
        by_run,
        present: true,
    }
}

fn started_month(value: Option<&Value>) -> Option<String> {
    let text = legacy_text(value).trim().replace('Z', "+00:00");
    let date = DateTime::parse_from_rfc3339(&text)
        .map(|value| value.with_timezone(&Utc).date_naive())
        .or_else(|_| {
            NaiveDateTime::parse_from_str(&text, "%Y-%m-%dT%H:%M:%S%.f").map(|value| value.date())
        })
        .or_else(|_| {
            NaiveDateTime::parse_from_str(&text, "%Y-%m-%d %H:%M:%S%.f").map(|value| value.date())
        })
        .or_else(|_| NaiveDate::parse_from_str(&text, "%Y-%m-%d"))
        .ok()?;
    Some(format!("{:04}-{:02}", date.year(), date.month()))
}

fn collect(
    log_root: &Path,
    state_root: &Path,
    environment: &BTreeMap<String, String>,
) -> (Vec<RunRecord>, BTreeMap<&'static str, usize>) {
    let mut state = State::default();
    let sidecar = sidecar(state_root, &mut state);
    let mut records = Vec::new();
    for skill in SKILLS {
        let skill_root = log_root.join(skill);
        let mut tsv_by_run: BTreeMap<PathBuf, Vec<PathBuf>> = BTreeMap::new();
        for (run, path) in RunLogCorpus::new(&skill_root)
            .classification_paths_without_manifest(skill, RunLogRoundSort::Numeric)
        {
            tsv_by_run.entry(run).or_default().push(path);
        }
        for run_dir in safe_run_dirs(log_root, skill, &mut state) {
            let has_rating = run_dir.join(DIFFICULTY_RECORD).is_file();
            let sources = classification_paths(skill, &run_dir, &tsv_by_run);
            if !has_rating && sources.is_empty() {
                continue;
            }
            let run_rating = if has_rating {
                rating(&run_dir, &mut state)
            } else {
                state.bump("unratable_missing_rating", 1);
                None
            };
            let classification = classification(skill, &sources, &mut state);
            let realized = realized_tier(run_rating.as_ref(), &classification, &mut state);
            let run_id = run_dir
                .file_name()
                .map_or_else(String::new, |name| name.to_string_lossy().into_owned());
            let relative = fs::canonicalize(&run_dir)
                .ok()
                .zip(fs::canonicalize(log_root).ok())
                .and_then(|(run, root)| run.strip_prefix(root).ok().map(Path::to_owned));
            let rel_link = relative.map_or_else(
                || run_dir.display().to_string(),
                |path| Path::new("larch-logs").join(path).display().to_string(),
            );
            records.push(RunRecord {
                skill,
                run_id: run_id.clone(),
                rel_link,
                manifest: manifest(&run_dir, &mut state),
                rating: run_rating,
                classification,
                realized_tier: realized,
                metrics: metrics(skill, &run_dir, environment, &mut state),
                sidecar_rows: sidecar
                    .by_run
                    .get(&(skill.to_owned(), run_id))
                    .cloned()
                    .unwrap_or_default(),
                sidecar_present: sidecar.present,
            });
        }
    }
    (records, state.counters)
}

fn ratable(record: &RunRecord) -> bool {
    record.rating.is_some()
        && TIERS.contains(&record.realized_tier.as_str())
        && TIERS.contains(&record.applied_tier().as_str())
}

fn render_matrix(output: &mut String, label: &str, records: &[&RunRecord]) {
    let mut matrix = [[0_usize; 3]; 3];
    for record in records.iter().filter(|record| ratable(record)) {
        let applied = tier_rank(&record.applied_tier()).expect("ratable applied tier");
        let realized = tier_rank(&record.realized_tier).expect("ratable realized tier");
        matrix[applied][realized] += 1;
    }
    let _ = writeln!(
        output,
        "### {label}\n\n| Applied \\ Realized | TRIVIAL | MODERATE | HARD |\n|---|---:|---:|---:|"
    );
    for (index, tier) in TIERS.iter().enumerate() {
        let _ = writeln!(
            output,
            "| {tier} | {} | {} | {} |",
            matrix[index][0], matrix[index][1], matrix[index][2]
        );
    }
    let denominator: usize = matrix.into_iter().flatten().sum();
    let _ = writeln!(output, "\nDenominator: {denominator}\n");
}

fn fmt_int<T: ToString>(value: Option<T>) -> String {
    value.map_or_else(|| "n/a".to_owned(), |value| value.to_string())
}

fn fmt_cost(value: Option<f64>) -> String {
    value.map_or_else(|| "n/a".to_owned(), |value| format!("${value:.2}"))
}

fn sidecar_identity_keys(row: &TextRow) -> Vec<String> {
    let mut keys = Vec::new();
    let hash = row.get("finding_hash").map_or("", String::as_str).trim();
    if !hash.is_empty() {
        keys.push(format!("hash:{hash}"));
    }
    let round = row.get("round_num").map_or("", String::as_str).trim();
    let finding = row.get("finding_id").map_or("", String::as_str).trim();
    if !round.is_empty() && !finding.is_empty() {
        keys.push(format!("{round}:{finding}"));
    }
    if row
        .get("source_skill")
        .is_some_and(|skill| skill.trim().eq_ignore_ascii_case("design"))
        && !finding.is_empty()
    {
        keys.push(format!("design:{finding}"));
    }
    keys.sort();
    keys.dedup();
    keys
}

fn sidecar_note(record: &RunRecord) -> String {
    if !record.sidecar_present {
        return "confirmed=n/a".to_owned();
    }
    let accepted: BTreeSet<&str> = record
        .classification
        .accepted
        .iter()
        .map(|row| row.key.as_str())
        .collect();
    if accepted.is_empty() {
        return "confirmed=0".to_owned();
    }
    let mut counts: BTreeMap<String, usize> = BTreeMap::new();
    for row in &record.sidecar_rows {
        if !sidecar_identity_keys(row)
            .iter()
            .any(|key| accepted.contains(key.as_str()))
        {
            continue;
        }
        let verdict = row
            .get("verdict")
            .map_or("", String::as_str)
            .trim()
            .to_ascii_lowercase()
            .replace('-', "_");
        if !verdict.is_empty() {
            *counts.entry(verdict).or_default() += 1;
        }
    }
    let mut parts = vec![format!(
        "confirmed={}",
        counts.get("confirmed").copied().unwrap_or(0)
    )];
    if let Some(count) = counts.get("stale").filter(|count| **count > 0) {
        parts.push(format!("stale={count}"));
    }
    if let Some(count) = counts.get("already_fixed").filter(|count| **count > 0) {
        parts.push(format!("already-fixed={count}"));
    }
    parts.join("; ")
}

#[allow(clippy::cast_precision_loss, clippy::cast_possible_truncation)]
fn rounded_mean(values: &[i128]) -> Option<i128> {
    (!values.is_empty()).then(|| {
        let total = values.iter().copied().fold(0_i128, i128::saturating_add);
        python_round(total as f64 / values.len() as f64, 0) as i128
    })
}

#[allow(clippy::cast_precision_loss, clippy::too_many_lines)] // Exact table order stays contiguous for parity review.
fn render(records: &[RunRecord], counters: &BTreeMap<&'static str, usize>) -> String {
    let mut output = String::new();
    output.push_str("# Difficulty Calibration\n\n## Corpus Summary\n\n| Skill | Runs | Ratable | Known realized | Unratable | Unknown realized |\n|---|---:|---:|---:|---:|---:|\n");
    for skill in SKILLS {
        let rows: Vec<_> = records
            .iter()
            .filter(|record| record.skill == skill)
            .collect();
        let rated = rows.iter().filter(|record| record.rating.is_some()).count();
        let known = rows
            .iter()
            .filter(|record| TIERS.contains(&record.realized_tier.as_str()))
            .count();
        let unknown = rows
            .iter()
            .filter(|record| record.realized_tier == UNKNOWN)
            .count();
        let _ = writeln!(
            output,
            "| {skill} | {} | {rated} | {known} | {} | {unknown} |",
            rows.len(),
            rows.len() - rated
        );
    }
    output.push_str("\n## Degraded Inputs\n\n| Counter | Count |\n|---|---:|\n");
    if counters.is_empty() {
        output.push_str("| none | 0 |\n");
    } else {
        for (key, count) in counters {
            let _ = writeln!(output, "| {key} | {count} |");
        }
    }
    output.push_str("\n## Confusion Matrix by Skill\n\n");
    for skill in SKILLS {
        let rows: Vec<_> = records
            .iter()
            .filter(|record| record.skill == skill)
            .collect();
        render_matrix(&mut output, skill, &rows);
    }
    output.push_str("## Confusion Matrix by Rater\n\n");
    let mut by_rater: BTreeMap<String, Vec<&RunRecord>> = BTreeMap::new();
    for record in records.iter().filter(|record| record.rating.is_some()) {
        by_rater.entry(record.rater_key()).or_default().push(record);
    }
    if by_rater.is_empty() {
        output.push_str("No ratable runs.\n\n");
    } else {
        for (label, rows) in by_rater {
            render_matrix(&mut output, &label, &rows);
        }
    }
    output.push_str("## Under-rating Misses\n\n| Skill | Run | Issue | Applied | Predicted | Realized | Accepted | Panel skipped | False-negative burden | Link |\n|---|---|---:|---|---|---|---:|---|---|---|\n");
    let mut misses: Vec<_> = records
        .iter()
        .filter(|record| {
            ratable(record)
                && tier_rank(&record.realized_tier).unwrap_or(0)
                    > tier_rank(&record.applied_tier()).unwrap_or(0)
        })
        .collect();
    misses.sort_by(|left, right| (left.skill, &left.run_id).cmp(&(right.skill, &right.run_id)));
    if misses.is_empty() {
        output.push_str("| n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |\n");
    }
    for record in misses {
        let predicted = record.predicted_tier();
        let skipped = record.panel_skipped();
        let accepted = record
            .classification
            .accepted_count
            .and_then(|value| i64::try_from(value).ok());
        let _ = writeln!(
            output,
            "| {} | {} | {} | {} | {} | {} | {} | {} | {} | {} |",
            record.skill,
            record.run_id,
            record.issue_number(),
            record.applied_tier(),
            if predicted.is_empty() {
                "n/a"
            } else {
                &predicted
            },
            record.realized_tier,
            fmt_int(accepted),
            if skipped.is_empty() { "n/a" } else { &skipped },
            sidecar_note(record),
            record.rel_link,
        );
    }
    output.push_str("\n## Per-tier Tokens, Cost, and Latency\n\n| Applied tier | Runs | Tokens total | USD | Avg latency seconds |\n|---|---:|---:|---:|---:|\n");
    for tier in TIERS {
        let rows: Vec<_> = records
            .iter()
            .filter(|record| record.applied_tier() == tier)
            .collect();
        let tokens: Vec<_> = rows
            .iter()
            .filter_map(|record| record.metrics.tokens)
            .collect();
        let costs: Vec<_> = rows
            .iter()
            .filter_map(|record| record.metrics.cost)
            .collect();
        let latencies: Vec<_> = rows
            .iter()
            .filter_map(|record| record.metrics.latency)
            .collect();
        let _ = writeln!(
            output,
            "| {tier} | {} | {} | {} | {} |",
            rows.len(),
            fmt_int(
                (!tokens.is_empty())
                    .then(|| { tokens.iter().copied().fold(0_i128, i128::saturating_add) })
            ),
            fmt_cost((!costs.is_empty()).then(|| costs.iter().sum())),
            fmt_int(rounded_mean(&latencies)),
        );
    }
    output.push_str("\n## Audit-run Deltas\n\n| Skill | Run | Month | Pre-audit tier | Peer count | Token delta | Latency delta seconds |\n|---|---|---|---|---:|---:|---:|\n");
    let mut upgraded: Vec<_> = records
        .iter()
        .filter(|record| record.audit_upgraded())
        .collect();
    upgraded.sort_by(|left, right| (left.skill, &left.run_id).cmp(&(right.skill, &right.run_id)));
    if upgraded.is_empty() {
        output.push_str("| n/a | n/a | n/a | n/a | 0 | n/a | n/a |\n");
    }
    for record in upgraded {
        let month = record.started_month();
        let pre_tier = record.pre_audit_tier();
        let (Some(month), Some(pre_tier)) = (month, pre_tier) else {
            let _ = writeln!(
                output,
                "| {} | {} | {} | {} | 0 | n/a | n/a |",
                record.skill,
                record.run_id,
                record.started_month().unwrap_or_else(|| "n/a".to_owned()),
                record.pre_audit_tier().unwrap_or_else(|| "n/a".to_owned())
            );
            continue;
        };
        let peers: Vec<_> = records
            .iter()
            .filter(|peer| {
                !peer.audit_upgraded()
                    && peer.skill == record.skill
                    && peer.started_month().as_deref() == Some(month.as_str())
                    && peer.pre_audit_tier().as_deref() == Some(pre_tier.as_str())
            })
            .collect();
        let token_peers: Vec<_> = peers
            .iter()
            .filter_map(|peer| peer.metrics.tokens)
            .collect();
        let latency_peers: Vec<_> = peers
            .iter()
            .filter_map(|peer| peer.metrics.latency)
            .collect();
        let token_delta = record
            .metrics
            .tokens
            .zip(rounded_mean(&token_peers))
            .map(|(value, mean)| value.saturating_sub(mean));
        let latency_delta = record
            .metrics
            .latency
            .zip(rounded_mean(&latency_peers))
            .map(|(value, mean)| value.saturating_sub(mean));
        let _ = writeln!(
            output,
            "| {} | {} | {month} | {pre_tier} | {} | {} | {} |",
            record.skill,
            record.run_id,
            peers.len(),
            fmt_int(token_delta),
            fmt_int(latency_delta)
        );
    }
    output.push_str("\n## Escalation Statistics\n\n| Skill | Ratable runs | Escalated runs | Rate |\n|---|---:|---:|---:|\n");
    for skill in SKILLS {
        let rows: Vec<_> = records
            .iter()
            .filter(|record| record.skill == skill && record.rating.is_some())
            .collect();
        let escalated = rows
            .iter()
            .filter(|record| {
                record
                    .rating
                    .as_ref()
                    .and_then(|rating| rating.get("escalations"))
                    .and_then(Value::as_array)
                    .is_some_and(|items| !items.is_empty())
            })
            .count();
        let rate = if rows.is_empty() {
            0.0
        } else {
            escalated as f64 / rows.len() as f64
        };
        let _ = writeln!(
            output,
            "| {skill} | {} | {escalated} | {rate:.2} |",
            rows.len()
        );
    }
    output.push_str("\n## Tier-distribution Drift\n\n### By Month\n\n| Month | TRIVIAL | MODERATE | HARD |\n|---|---:|---:|---:|\n");
    let mut by_month: BTreeMap<String, [usize; 3]> = BTreeMap::new();
    let mut by_model: BTreeMap<String, [usize; 3]> = BTreeMap::new();
    for record in records.iter().filter(|record| record.rating.is_some()) {
        let tier = tier_rank(&record.applied_tier()).unwrap_or(0);
        if let Some(month) = record.started_month() {
            by_month.entry(month).or_default()[tier] += 1;
        }
        let model = unknown_if_empty(
            record
                .rating
                .as_ref()
                .and_then(|rating| rating.get("rater_model")),
        );
        by_model.entry(model).or_default()[tier] += 1;
    }
    if by_month.is_empty() {
        output.push_str("| n/a | 0 | 0 | 0 |\n");
    }
    for (month, counts) in by_month {
        let _ = writeln!(
            output,
            "| {month} | {} | {} | {} |",
            counts[0], counts[1], counts[2]
        );
    }
    output.push_str("\n### By Rater Model\n\n| Rater model | TRIVIAL | MODERATE | HARD |\n|---|---:|---:|---:|\n");
    if by_model.is_empty() {
        output.push_str("| n/a | 0 | 0 | 0 |\n");
    }
    for (model, counts) in by_model {
        let _ = writeln!(
            output,
            "| {model} | {} | {} | {} |",
            counts[0], counts[1], counts[2]
        );
    }
    output
}

/// Analyze one already synchronized or explicitly supplied run-log corpus.
#[must_use]
pub fn difficulty_calibration_report(
    log_root: &Path,
    state_root: &Path,
    environment: &BTreeMap<String, String>,
) -> String {
    let (records, counters) = collect(log_root, state_root, environment);
    render(&records, &counters)
}
