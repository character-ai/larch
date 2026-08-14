//! Token scan and usage extraction over committed run logs.
//!
//! Library parity for Python `larch.report.report_tokens_scan`,
//! `larch.report.report_tokens_models`, and the extraction half of
//! `larch.report.tokens`. The Rust report analyzer and token measurement
//! commands share this extraction owner.
//!
//! # Memory bound
//!
//! [`TokenCorpusScan`] streams one run at a time from [`RunLogCorpus`], and
//! every ledger and transcript file is read line by line. Peak resident memory
//! is therefore bounded by the largest single run in the corpus, not by the
//! corpus size: for one run it is the retained usage rows (about 200 bytes per
//! ledger or transcript record) plus that run's decoded token report. Emitted
//! records are handed to the caller one at a time and are never accumulated by
//! this layer.
//!
//! # Deliberate difference
//!
//! Python's `_epoch` resolves a timestamp without a UTC designator through
//! `datetime.fromisoformat(...).timestamp()`, which reads it in the process's
//! local zone. This port reads such a timestamp as UTC so extraction is
//! deterministic across machines. Every timestamp larch writes carries an
//! explicit `Z`, so no recorded run changes.

use crate::report::run_log_corpus::{
    RunLogCorpus, RunLogCorpusEvent, RunLogCorpusIter, RunLogRun, RunLogSelection,
};
use crate::text::python_str as truthy_text;
use crate::vendor_model::{
    CLAUDE_FABLE_5_MODEL, CLAUDE_HAIKU_4_5_MODEL, CLAUDE_OPUS_4_8_MODEL, CLAUDE_SONNET_4_6_MODEL,
    CODEX_DEFAULT_MODEL, CODEX_FIX_MODEL_DEFAULT, CODEX_REVIEW_MODEL_DEFAULT,
    CODEX_VOTE_MODEL_DEFAULT, CURSOR_DEFAULT_MODEL, CURSOR_GROK_4_6_HIGH_MODEL,
    claude_sub_default_model, normalize_claude_ledger_model,
};
use crate::vendor_usage::json_usage_number;
use chrono::{DateTime, NaiveDateTime, Utc};
use serde_json::{Map, Value};
use sha2::{Digest as _, Sha256};
use std::{
    collections::HashMap,
    error::Error,
    fmt, fs,
    io::{BufRead, BufReader},
    path::{Path, PathBuf},
};

/// Step label the implement dispatcher records for external implementers.
pub const IMPLEMENT_STEP2_LABEL: &str = "Step 2 \u{2014} implementation";
/// Prefix shared by every implement Step 2 mark.
pub const IMPLEMENT_STEP2_PREFIX: &str = "Step 2 ";
/// `raw` label a Codex implement row carries.
pub const CODEX_IMPLEMENT_RAW_LABEL: &str = "codex_implement";
/// `raw` label a Cursor implement row carries.
pub const CURSOR_IMPLEMENT_RAW_LABEL: &str = "cursor_implement";

const OBSERVATION_LIMIT: usize = 256;
const CLAUDE_COMPONENTS: [&str; 6] = [
    "input",
    "cache_read",
    "cache_create",
    "cache_create_5m",
    "cache_create_1h",
    "output",
];
const CODEX_COMPONENTS: [&str; 3] = ["input", "cached_input", "output"];
const CURSOR_COMPONENTS: [&str; 3] = ["input", "cache_read", "output"];
const KNOWN_USAGE_FIELDS: [&str; 6] = [
    "input_tokens",
    "output_tokens",
    "cache_read_input_tokens",
    "cache_creation_input_tokens",
    "cache_creation",
    "service_tier",
];
const KNOWN_CACHE_CREATION_FIELDS: [&str; 3] = [
    "ephemeral_5m_input_tokens",
    "ephemeral_1h_input_tokens",
    "5m",
];
const PINNED_MODELS: [&str; 10] = [
    CODEX_DEFAULT_MODEL,
    CODEX_REVIEW_MODEL_DEFAULT,
    CODEX_VOTE_MODEL_DEFAULT,
    CODEX_FIX_MODEL_DEFAULT,
    CURSOR_DEFAULT_MODEL,
    CURSOR_GROK_4_6_HIGH_MODEL,
    CLAUDE_OPUS_4_8_MODEL,
    CLAUDE_SONNET_4_6_MODEL,
    CLAUDE_HAIKU_4_5_MODEL,
    CLAUDE_FABLE_5_MODEL,
];

/// One priced vendor lane in a token report.
#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub enum TokenVendor {
    /// Main-agent Claude, derived from the session transcript.
    Claude,
    /// Codex CLI subprocesses.
    Codex,
    /// Cursor agent subprocesses.
    Cursor,
    /// Spawned-process Claude, priced at Claude rates under a distinct key.
    ClaudeSub,
}

/// Every vendor lane in report order.
pub const TOKEN_VENDORS: [TokenVendor; 4] = [
    TokenVendor::Claude,
    TokenVendor::Codex,
    TokenVendor::Cursor,
    TokenVendor::ClaudeSub,
];

impl TokenVendor {
    /// Return the report key for this lane.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Claude => "claude",
            Self::Codex => "codex",
            Self::Cursor => "cursor",
            Self::ClaudeSub => "claude_sub",
        }
    }

    /// Return the bucket components that belong to this lane.
    #[must_use]
    pub const fn components(self) -> &'static [&'static str] {
        match self {
            Self::Claude | Self::ClaudeSub => &CLAUDE_COMPONENTS,
            Self::Codex => &CODEX_COMPONENTS,
            Self::Cursor => &CURSOR_COMPONENTS,
        }
    }
}

/// Which token report basename a skill commits.
#[must_use]
pub fn token_report_basename(skill: &str) -> &'static str {
    if skill == "design" {
        "token-report-final.json"
    } else {
        "token-report.json"
    }
}

/// Parse an integer the way Python `report_tokens_models.safe_int` does.
///
/// Booleans yield the default, floats truncate toward zero, and a string may
/// carry thousands separators or a float spelling.
#[must_use]
pub fn safe_int(value: Option<&Value>, default: i64) -> i64 {
    match value {
        None | Some(Value::Null | Value::Bool(_) | Value::Array(_) | Value::Object(_)) => default,
        Some(Value::Number(number)) => number
            .as_i64()
            .or_else(|| number.as_f64().and_then(truncate_float))
            .unwrap_or(default),
        Some(Value::String(text)) => {
            let stripped = text.trim().replace(',', "");
            stripped
                .parse::<i64>()
                .ok()
                .or_else(|| stripped.parse::<f64>().ok().and_then(truncate_float))
                .unwrap_or(default)
        }
    }
}

#[allow(
    clippy::cast_possible_truncation,
    reason = "the range check proves the truncated value fits i64"
)]
fn truncate_float(value: f64) -> Option<i64> {
    let truncated = value.trunc();
    (-9_223_372_036_854_775_808.0..9_223_372_036_854_775_808.0)
        .contains(&truncated)
        .then_some(truncated as i64)
}

/// Read one integer token field the way Python `tokens._int_field` does.
fn int_field(fields: &Map<String, Value>, key: &str) -> i64 {
    json_usage_number(fields.get(key)).unwrap_or(0)
}

fn object_field<'a>(fields: &'a Map<String, Value>, key: &str) -> Option<&'a Map<String, Value>> {
    fields.get(key).and_then(Value::as_object)
}

/// Aggregated token counts for one vendor lane.
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub struct VendorTotals {
    /// Uncached input tokens.
    pub input: i64,
    /// Cache-read input tokens.
    pub cache_read: i64,
    /// Legacy undivided cache-creation tokens.
    pub cache_create: i64,
    /// Cache-creation tokens at the five-minute tier.
    pub cache_create_5m: i64,
    /// Cache-creation tokens at the one-hour tier.
    pub cache_create_1h: i64,
    /// Codex-shaped cached input tokens.
    pub cached_input: i64,
    /// Output tokens.
    pub output: i64,
    /// Explicit recorded total.
    pub total: i64,
}

/// Build [`VendorTotals`] for one lane from a raw token report.
///
/// A present `<vendor>.totals.<key>` wins; a missing or null field falls back
/// to `BUCKETS_<vendor>.<key>`, because the legacy report builder only emitted
/// `{input, output, total}` for external vendor lanes.
#[must_use]
pub fn vendor_totals_from_report(report: &Map<String, Value>, vendor: TokenVendor) -> VendorTotals {
    let totals =
        object_field(report, vendor.as_str()).and_then(|lane| object_field(lane, "totals"));
    let buckets = object_field(report, &format!("BUCKETS_{}", vendor.as_str()));
    let field = |key: &str| -> i64 {
        match totals.and_then(|totals| totals.get(key)) {
            Some(Value::Null) | None => buckets.map_or(0, |buckets| safe_int(buckets.get(key), 0)),
            Some(value) => safe_int(Some(value), 0),
        }
    };
    VendorTotals {
        input: field("input"),
        cache_read: field("cache_read"),
        cache_create: field("cache_create"),
        cache_create_5m: field("cache_create_5m"),
        cache_create_1h: field("cache_create_1h"),
        cached_input: field("cached_input"),
        output: field("output"),
        total: field("total"),
    }
}

/// Return the `(5m, 1h)` cache-creation split for a Claude-shaped lane.
///
/// Legacy undivided cache creation folds into the five-minute tier, which is
/// the tier it was priced at.
#[must_use]
pub const fn claude_effective_cache_create(totals: &VendorTotals) -> (i64, i64) {
    if totals.cache_create_5m != 0 || totals.cache_create_1h != 0 {
        (totals.cache_create_5m, totals.cache_create_1h)
    } else {
        (totals.cache_create, 0)
    }
}

/// Return the canonical token total for one lane.
///
/// The nonzero component sum wins; the explicit recorded total is used only
/// when every component is zero.
#[must_use]
pub const fn effective_vendor_total(totals: &VendorTotals, vendor: TokenVendor) -> i64 {
    let component = match vendor {
        TokenVendor::Claude | TokenVendor::ClaudeSub => {
            let (five_minute, one_hour) = claude_effective_cache_create(totals);
            totals.input + totals.cache_read + five_minute + one_hour + totals.output
        }
        TokenVendor::Codex => totals.input + totals.cached_input + totals.output,
        TokenVendor::Cursor => totals.input + totals.cache_read + totals.output,
    };
    if component > 0 {
        component
    } else {
        totals.total
    }
}

/// Return whether a report carries any numeric token count worth pricing.
#[must_use]
pub fn report_has_numeric_tokens(report: &Map<String, Value>) -> bool {
    TOKEN_VENDORS.into_iter().any(|vendor| {
        let bucket = object_field(report, &format!("BUCKETS_{}", vendor.as_str()));
        let bucketed = bucket.is_some_and(|bucket| {
            vendor
                .components()
                .iter()
                .any(|key| safe_int(bucket.get(*key), 0) > 0)
        });
        bucketed || effective_vendor_total(&vendor_totals_from_report(report, vendor), vendor) > 0
    })
}

/// One per-step row of a vendor lane inside a token report.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct TokenPhaseRow {
    /// Lane this row belongs to.
    pub vendor: TokenVendor,
    /// Step label, or `unknown` when the report omitted one.
    pub step: String,
    /// Uncached input tokens.
    pub input: i64,
    /// Cache-read input tokens.
    pub cache_read: i64,
    /// Cache-creation tokens.
    pub cache_create: i64,
    /// Output tokens.
    pub output: i64,
    /// Recorded total.
    pub total: i64,
}

/// Read every per-step row from a raw token report, in lane order.
#[must_use]
pub fn token_phase_rows(report: &Map<String, Value>) -> Vec<TokenPhaseRow> {
    let mut rows = Vec::new();
    for vendor in TOKEN_VENDORS {
        let Some(per_step) = object_field(report, vendor.as_str())
            .and_then(|lane| lane.get("per_step"))
            .and_then(Value::as_array)
        else {
            continue;
        };
        for item in per_step {
            let item = item.as_object().cloned().unwrap_or_default();
            let totals = object_field(&item, "totals").cloned().unwrap_or_default();
            let step = truthy_text(item.get("step"));
            rows.push(TokenPhaseRow {
                vendor,
                step: if step.is_empty() {
                    "unknown".to_owned()
                } else {
                    step
                },
                input: safe_int(totals.get("input"), 0),
                cache_read: safe_int(totals.get("cache_read"), 0),
                cache_create: safe_int(totals.get("cache_create"), 0),
                output: safe_int(totals.get("output"), 0),
                total: safe_int(totals.get("total"), 0),
            });
        }
    }
    rows
}

/// Why extraction refused to build a report.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum TokenReportError {
    /// The ledger carried no step mark, so per-step slicing has no origin.
    NoStepMarks,
    /// A supplied transcript path was not a readable regular file.
    TranscriptNotFound(PathBuf),
}

impl fmt::Display for TokenReportError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::NoStepMarks => formatter.write_str("no step marks in ledger"),
            Self::TranscriptNotFound(_path) => formatter.write_str("transcript not found"),
        }
    }
}

impl Error for TokenReportError {}

/// A non-extraction event worth surfacing instead of dropping silently.
#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub enum TokenObservationKind {
    /// A usage object carried a field this extractor does not consume.
    UnknownUsageField,
    /// A vendor row recorded no model, so the lane default was substituted.
    DefaultedModel,
    /// A recorded model id was folded onto its base id for accounting.
    NormalizedModel,
    /// A recorded model id is not one of larch's pinned vendor models.
    UnpinnedModel,
    /// A recorded model id was priced by another model's rate row.
    UnpricedModel,
}

/// One structured extraction observation.
#[derive(Clone, Debug, Eq, Hash, PartialEq)]
pub struct TokenObservation {
    kind: TokenObservationKind,
    vendor: String,
    detail: String,
}

impl TokenObservation {
    /// Return the observation kind.
    #[must_use]
    pub const fn kind(&self) -> TokenObservationKind {
        self.kind
    }

    /// Return the lane key, or an empty string for lane-independent findings.
    #[must_use]
    pub fn vendor(&self) -> &str {
        &self.vendor
    }

    /// Return the observed field name or model id.
    #[must_use]
    pub fn detail(&self) -> &str {
        &self.detail
    }
}

/// A bounded, de-duplicated observation sink.
#[derive(Clone, Debug, Default)]
pub struct TokenObservations {
    entries: Vec<TokenObservation>,
    truncated: bool,
}

impl TokenObservations {
    /// Record one observation, ignoring repeats and stopping at the cap.
    pub fn record(&mut self, kind: TokenObservationKind, vendor: &str, detail: &str) {
        let candidate = TokenObservation {
            kind,
            vendor: vendor.to_owned(),
            detail: detail.to_owned(),
        };
        if self.entries.contains(&candidate) {
            return;
        }
        if self.entries.len() >= OBSERVATION_LIMIT {
            self.truncated = true;
            return;
        }
        self.entries.push(candidate);
    }

    /// Return the recorded observations in first-seen order.
    #[must_use]
    pub fn entries(&self) -> &[TokenObservation] {
        &self.entries
    }

    /// Return whether the cap dropped further distinct observations.
    #[must_use]
    pub const fn truncated(&self) -> bool {
        self.truncated
    }

    fn note_model(&mut self, vendor: &str, model: &str) {
        if !model.is_empty() && !PINNED_MODELS.contains(&model) {
            self.record(TokenObservationKind::UnpinnedModel, vendor, model);
        }
    }
}

/// One step mark read from a token ledger.
#[derive(Clone, Debug, PartialEq)]
pub struct TokenStepMark {
    /// Step label.
    pub step: String,
    /// Epoch seconds.
    pub ts: f64,
}

/// One usage-bearing row from a ledger or a session transcript.
#[derive(Clone, Debug, Default, PartialEq)]
pub struct TokenUsageRow {
    /// Epoch seconds, absent when no timestamp could be resolved.
    pub ts: Option<f64>,
    /// Lane key for a ledger row; empty for a transcript row.
    pub vendor: String,
    /// Recorded model id, empty when the row carried none.
    pub model: String,
    /// Recorded `raw` role label, empty when the row carried none.
    pub raw: String,
    /// Attributed or inferred step for a transcript row.
    pub skill: String,
    /// Uncached input tokens.
    pub input: i64,
    /// Output tokens.
    pub output: i64,
    /// Cache-read input tokens.
    pub cache_read: i64,
    /// Cache-creation tokens.
    pub cache_create: i64,
    /// Cache-creation tokens at the five-minute tier.
    pub cache_create_5m: i64,
    /// Cache-creation tokens at the one-hour tier.
    pub cache_create_1h: i64,
    /// Codex-shaped cached input tokens.
    pub cached_input: i64,
    /// Recorded or derived total.
    pub total: i64,
}

impl TokenUsageRow {
    const fn effective_total(&self) -> i64 {
        if self.total == 0 {
            self.input + self.output + self.cache_read + self.cache_create
        } else {
            self.total
        }
    }
}

#[derive(Clone, Copy, Debug, Default)]
struct UsageTally {
    input: i64,
    output: i64,
    cache_read: i64,
    cache_create: i64,
    cache_create_5m: i64,
    cache_create_1h: i64,
    cached_input: i64,
    total: i64,
}

impl UsageTally {
    const fn add(&mut self, row: &TokenUsageRow) {
        self.input += row.input;
        self.output += row.output;
        self.cache_read += row.cache_read;
        self.cache_create += row.cache_create;
        self.cache_create_5m += row.cache_create_5m;
        self.cache_create_1h += row.cache_create_1h;
        self.cached_input += row.cached_input;
        self.total += row.effective_total();
    }

    fn of<'a>(rows: impl IntoIterator<Item = &'a TokenUsageRow>) -> Self {
        let mut tally = Self::default();
        for row in rows {
            tally.add(row);
        }
        tally
    }

    fn to_value(self) -> Value {
        let mut fields = Map::new();
        for (key, value) in [
            ("input", self.input),
            ("output", self.output),
            ("cache_read", self.cache_read),
            ("cache_create", self.cache_create),
            ("total", self.total),
            ("cache_create_5m", self.cache_create_5m),
            ("cache_create_1h", self.cache_create_1h),
            ("cached_input", self.cached_input),
        ] {
            let _prior = fields.insert(key.to_owned(), Value::from(value));
        }
        Value::Object(fields)
    }
}

/// Resolve one recorded timestamp to epoch seconds.
#[must_use]
pub fn parse_epoch(value: Option<&Value>) -> Option<f64> {
    match value? {
        Value::Bool(flag) => Some(f64::from(u8::from(*flag))),
        Value::Number(number) => number.as_f64(),
        Value::String(text) => parse_epoch_text(text.trim()),
        Value::Null | Value::Array(_) | Value::Object(_) => None,
    }
}

fn parse_epoch_text(text: &str) -> Option<f64> {
    if text.is_empty() {
        return None;
    }
    if let Ok(seconds) = text.parse::<f64>() {
        return Some(seconds);
    }
    let normalized = text.replace('Z', "+00:00");
    DateTime::parse_from_rfc3339(&normalized)
        .map(|value| value.with_timezone(&Utc))
        .ok()
        .or_else(|| {
            NaiveDateTime::parse_from_str(&normalized, "%Y-%m-%dT%H:%M:%S%.f")
                .map(|value| value.and_utc())
                .ok()
        })
        .map(|value| {
            let nanos = f64::from(value.timestamp_subsec_nanos());
            let seconds = i64_to_f64(value.timestamp());
            seconds + nanos / 1_000_000_000.0
        })
}

#[allow(
    clippy::cast_precision_loss,
    reason = "epoch seconds stay well inside the exactly representable range"
)]
const fn i64_to_f64(value: i64) -> f64 {
    value as f64
}

fn read_json_lines(path: &Path) -> std::io::Result<Vec<Map<String, Value>>> {
    let reader = BufReader::new(fs::File::open(path)?);
    let mut rows = Vec::new();
    for line in reader.split(b'\n') {
        let line = line?;
        if let Ok(Value::Object(fields)) = serde_json::from_slice(&line) {
            rows.push(fields);
        }
    }
    Ok(rows)
}

fn is_regular_file(path: &Path) -> bool {
    fs::symlink_metadata(path)
        .is_ok_and(|metadata| !metadata.file_type().is_symlink() && metadata.is_file())
}

/// Read one token ledger, skipping absent files and malformed lines.
#[must_use]
pub fn read_ledger(path: &Path) -> Vec<Map<String, Value>> {
    if !path.is_file() {
        return Vec::new();
    }
    read_json_lines(path).unwrap_or_default()
}

/// Read every `mark` row from decoded ledger rows, in ledger order.
#[must_use]
pub fn ledger_step_marks(rows: &[Map<String, Value>]) -> Vec<TokenStepMark> {
    rows.iter()
        .filter(|row| truthy_text(row.get("type")) == "mark")
        .filter_map(|row| {
            parse_epoch(row.get("ts")).map(|ts| TokenStepMark {
                step: truthy_text(row.get("step")),
                ts,
            })
        })
        .collect()
}

/// Read every `vendor` usage row from decoded ledger rows.
#[must_use]
pub fn ledger_vendor_rows(
    rows: &[Map<String, Value>],
    observations: &mut TokenObservations,
) -> Vec<TokenUsageRow> {
    let mut usage_rows = Vec::new();
    for row in rows {
        if truthy_text(row.get("type")) != "vendor" {
            continue;
        }
        let Some(ts) = parse_epoch(row.get("ts")) else {
            continue;
        };
        let vendor = truthy_text(row.get("vendor"));
        let mut usage = TokenUsageRow {
            ts: Some(ts),
            vendor: if vendor.is_empty() {
                "unknown".to_owned()
            } else {
                vendor
            },
            model: truthy_text(row.get("model")),
            raw: truthy_text(row.get("raw")),
            input: int_field(row, "input"),
            output: int_field(row, "output"),
            cache_read: int_field(row, "cache_read"),
            cache_create: int_field(row, "cache_create"),
            total: int_field(row, "total"),
            ..TokenUsageRow::default()
        };
        usage.total = usage.effective_total();
        observations.note_model(&usage.vendor, &usage.model);
        usage_rows.push(usage);
    }
    usage_rows
}

fn usage_object(row: &Map<String, Value>) -> Option<&Map<String, Value>> {
    object_field(row, "message")
        .and_then(|message| object_field(message, "usage"))
        .or_else(|| object_field(row, "usage"))
        .filter(|usage| !usage.is_empty())
}

fn cache_create_parts(
    usage: &Map<String, Value>,
    observations: &mut TokenObservations,
) -> (i64, i64) {
    for key in usage.keys() {
        if !KNOWN_USAGE_FIELDS.contains(&key.as_str()) {
            observations.record(TokenObservationKind::UnknownUsageField, "claude", key);
        }
    }
    let Some(cache_creation) = object_field(usage, "cache_creation") else {
        return (int_field(usage, "cache_creation_input_tokens"), 0);
    };
    for key in cache_creation.keys() {
        if !KNOWN_CACHE_CREATION_FIELDS.contains(&key.as_str()) {
            observations.record(
                TokenObservationKind::UnknownUsageField,
                "claude",
                &format!("cache_creation.{key}"),
            );
        }
    }
    (
        int_field(cache_creation, "ephemeral_5m_input_tokens") + int_field(cache_creation, "5m"),
        int_field(cache_creation, "ephemeral_1h_input_tokens"),
    )
}

fn enclosing_step(marks: &[TokenStepMark], ts: Option<f64>) -> Option<&str> {
    let ts = ts?;
    marks.iter().enumerate().find_map(|(index, mark)| {
        let end = marks.get(index + 1).map(|next| next.ts);
        (mark.ts <= ts && end.is_none_or(|end| ts < end)).then_some(mark.step.as_str())
    })
}

/// Extract deduplicated main-agent Claude usage rows from transcript rows.
#[must_use]
pub fn claude_usage_rows(
    transcript_rows: &[Map<String, Value>],
    marks: &[TokenStepMark],
    observations: &mut TokenObservations,
) -> Vec<TokenUsageRow> {
    let first_ts = marks.first().map(|mark| mark.ts);
    let mut order: Vec<TokenUsageRow> = Vec::new();
    let mut seen: HashMap<String, usize> = HashMap::new();
    for row in transcript_rows {
        let Some(usage) = usage_object(row) else {
            continue;
        };
        let ts = parse_epoch(row.get("timestamp"))
            .filter(|value| *value != 0.0)
            .or(first_ts);
        let (cache5, cache1) = cache_create_parts(usage, observations);
        let input = int_field(usage, "input_tokens");
        let cache_read = int_field(usage, "cache_read_input_tokens");
        let output = int_field(usage, "output_tokens");
        let attribution = truthy_text(row.get("attributionSkill"));
        let skill = if attribution.is_empty() {
            enclosing_step(marks, ts).map_or_else(
                || "unattributed".to_owned(),
                |step| format!("inferred:{step}"),
            )
        } else {
            attribution
        };
        let usage_row = TokenUsageRow {
            ts,
            skill,
            input,
            output,
            cache_read,
            cache_create: cache5 + cache1,
            cache_create_5m: cache5,
            cache_create_1h: cache1,
            total: input + cache_read + cache5 + cache1 + output,
            ..TokenUsageRow::default()
        };
        let request_id = truthy_text(row.get("requestId"));
        let message_id = object_field(row, "message")
            .map(|message| truthy_text(message.get("id")))
            .unwrap_or_default();
        let fingerprint = if request_id.is_empty() && message_id.is_empty() {
            format!("{input}/{cache_read}/{cache5}/{cache1}/{output}")
        } else {
            String::new()
        };
        let key = format!("{request_id}|{message_id}|{fingerprint}");
        if let Some(index) = seen.get(&key) {
            order[*index] = usage_row;
        } else {
            let _prior = seen.insert(key, order.len());
            order.push(usage_row);
        }
    }
    order
}

/// Return the transcript files one session contributes, in stable order.
///
/// # Errors
/// Returns [`TokenReportError::TranscriptNotFound`] when the primary transcript
/// is not a readable regular file.
pub fn transcript_sources(
    transcript_path: &Path,
    session_dir: Option<&Path>,
) -> Result<Vec<PathBuf>, TokenReportError> {
    if !transcript_path.is_file() {
        return Err(TokenReportError::TranscriptNotFound(
            transcript_path.to_owned(),
        ));
    }
    let mut paths = vec![transcript_path.to_owned()];
    let Some(subagents) = session_dir.map(|dir| dir.join("subagents")) else {
        return Ok(paths);
    };
    if !subagents.is_dir() {
        return Ok(paths);
    }
    let mut extra: Vec<PathBuf> = fs::read_dir(&subagents)
        .into_iter()
        .flatten()
        .flatten()
        .map(|entry| entry.path())
        .filter(|path| path.extension().is_some_and(|part| part == "jsonl"))
        .collect();
    extra.sort();
    paths.extend(extra);
    Ok(paths)
}

/// Marks and usage rows one report render consumes.
#[derive(Clone, Debug, Default)]
pub struct TokenReportInputs {
    /// Ordered step marks.
    pub marks: Vec<TokenStepMark>,
    /// Main-agent Claude usage rows.
    pub claude: Vec<TokenUsageRow>,
    /// Vendor usage rows.
    pub vendor: Vec<TokenUsageRow>,
    /// Extraction observations gathered while reading both sources.
    pub observations: TokenObservations,
}

/// Read one ledger and its transcripts into report inputs.
///
/// # Errors
/// Returns [`TokenReportError::NoStepMarks`] when the ledger carries no mark.
pub fn read_report_inputs(
    ledger_path: &Path,
    transcript_paths: &[PathBuf],
) -> Result<TokenReportInputs, TokenReportError> {
    let ledger_rows = read_ledger(ledger_path);
    let marks = ledger_step_marks(&ledger_rows);
    if marks.is_empty() {
        return Err(TokenReportError::NoStepMarks);
    }
    let mut observations = TokenObservations::default();
    let mut transcript_rows = Vec::new();
    for path in transcript_paths {
        if path.is_file() {
            transcript_rows.extend(read_json_lines(path).unwrap_or_default());
        }
    }
    let claude = claude_usage_rows(&transcript_rows, &marks, &mut observations);
    let vendor = ledger_vendor_rows(&ledger_rows, &mut observations);
    Ok(TokenReportInputs {
        marks,
        claude,
        vendor,
        observations,
    })
}

fn slice_rows<'a>(
    rows: impl IntoIterator<Item = &'a TokenUsageRow>,
    start: f64,
    end: Option<f64>,
) -> Vec<&'a TokenUsageRow> {
    rows.into_iter()
        .filter(|row| {
            row.ts
                .is_some_and(|ts| ts >= start && end.is_none_or(|end| ts < end))
        })
        .collect()
}

fn vendor_lane_names(inputs: &TokenReportInputs) -> Vec<String> {
    let Some(first) = inputs.marks.first().map(|mark| mark.ts) else {
        return Vec::new();
    };
    let mut present: Vec<String> = Vec::new();
    for row in &inputs.vendor {
        if row.ts.is_some_and(|ts| ts >= first) && !present.contains(&row.vendor) {
            present.push(row.vendor.clone());
        }
    }
    present.sort();
    let mut ordered: Vec<String> = ["codex", "cursor", "claude_sub"]
        .into_iter()
        .filter(|name| present.iter().any(|entry| entry == name))
        .map(str::to_owned)
        .collect();
    ordered.extend(
        present
            .into_iter()
            .filter(|name| !matches!(name.as_str(), "codex" | "cursor" | "claude_sub")),
    );
    ordered
}

fn explicit_step_for_vendor_row(name: &str, row: &TokenUsageRow) -> bool {
    (name == "codex" && row.raw == CODEX_IMPLEMENT_RAW_LABEL)
        || (name == "cursor" && row.raw == CURSOR_IMPLEMENT_RAW_LABEL)
}

fn should_reroute_vendor_row(name: &str, marks: &[TokenStepMark], row: &TokenUsageRow) -> bool {
    if !explicit_step_for_vendor_row(name, row) {
        return false;
    }
    let Some(first) = marks.first().map(|mark| mark.ts) else {
        return false;
    };
    let Some(ts) = row.ts.filter(|ts| *ts >= first) else {
        return false;
    };
    !enclosing_step(marks, Some(ts))
        .unwrap_or_default()
        .starts_with(IMPLEMENT_STEP2_PREFIX)
}

fn add_totals(left: &Value, right: &Value) -> Value {
    let (Some(left), Some(right)) = (left.as_object(), right.as_object()) else {
        return right.clone();
    };
    let mut merged = left.clone();
    for (key, value) in right {
        let sum = safe_int(left.get(key), 0) + safe_int(Some(value), 0);
        let _prior = merged.insert(key.clone(), Value::from(sum));
    }
    Value::Object(merged)
}

fn per_step_json(name: &str, marks: &[TokenStepMark], rows: &[TokenUsageRow]) -> Value {
    let first = marks.first().map_or(0.0, |mark| mark.ts);
    let lane: Vec<&TokenUsageRow> = rows
        .iter()
        .filter(|row| name == "claude" || row.vendor == name)
        .collect();
    let (rerouted, retained): (Vec<&TokenUsageRow>, Vec<&TokenUsageRow>) = lane
        .iter()
        .copied()
        .partition(|row| name != "claude" && should_reroute_vendor_row(name, marks, row));
    let mut per_step: Vec<Map<String, Value>> = marks
        .iter()
        .enumerate()
        .map(|(index, mark)| {
            let end = marks.get(index + 1).map(|next| next.ts);
            let mut entry = Map::new();
            let _prior = entry.insert("step".to_owned(), Value::from(mark.step.clone()));
            let _prior = entry.insert(
                "totals".to_owned(),
                UsageTally::of(slice_rows(retained.iter().copied(), mark.ts, end)).to_value(),
            );
            entry
        })
        .collect();
    if !rerouted.is_empty() {
        let synthetic = UsageTally::of(rerouted.iter().copied()).to_value();
        merge_step2(&mut per_step, synthetic);
    }
    let mut lane_json = Map::new();
    let _prior = lane_json.insert(
        "per_step".to_owned(),
        Value::Array(per_step.into_iter().map(Value::Object).collect()),
    );
    let _prior = lane_json.insert(
        "totals".to_owned(),
        UsageTally::of(slice_rows(lane, first, None)).to_value(),
    );
    Value::Object(lane_json)
}

fn merge_step2(per_step: &mut Vec<Map<String, Value>>, synthetic: Value) {
    let index = per_step
        .iter()
        .position(|entry| truthy_text(entry.get("step")).starts_with(IMPLEMENT_STEP2_PREFIX));
    if let Some(index) = index {
        let existing = per_step[index]
            .get("totals")
            .cloned()
            .unwrap_or(Value::Null);
        let _prior = per_step[index].insert("totals".to_owned(), add_totals(&existing, &synthetic));
    } else {
        let mut entry = Map::new();
        let _prior = entry.insert("step".to_owned(), Value::from(IMPLEMENT_STEP2_LABEL));
        let _prior = entry.insert("totals".to_owned(), synthetic);
        per_step.push(entry);
    }
}

fn bucket_value(pairs: &[(&str, i64)]) -> Value {
    let mut fields = Map::new();
    for (key, value) in pairs {
        let _prior = fields.insert((*key).to_owned(), Value::from(*value));
    }
    Value::Object(fields)
}

/// Render one lane's bucket in that lane's exact key vocabulary.
///
/// The single owner of the per-lane bucket shape, shared by the aggregate
/// `BUCKETS_<lane>` and the per-model split so the two cannot drift.
fn lane_bucket_value(vendor: TokenVendor, tally: UsageTally) -> Value {
    match vendor {
        TokenVendor::Codex => bucket_value(&[
            ("input", tally.input),
            ("cached_input", tally.cache_read),
            ("output", tally.output),
            ("total", tally.total),
        ]),
        TokenVendor::Cursor => bucket_value(&[
            ("input", tally.input),
            ("cache_read", tally.cache_read),
            ("output", tally.output),
            ("total", tally.total),
        ]),
        TokenVendor::Claude | TokenVendor::ClaudeSub => bucket_value(&[
            ("input", tally.input),
            ("cache_read", tally.cache_read),
            ("cache_create_5m", tally.cache_create),
            ("cache_create_1h", 0),
            ("output", tally.output),
            ("total", tally.total),
        ]),
    }
}

fn by_model_value(
    rows: &[&TokenUsageRow],
    vendor: TokenVendor,
    observations: &mut TokenObservations,
) -> Value {
    let mut order: Vec<String> = Vec::new();
    let mut totals: HashMap<String, UsageTally> = HashMap::new();
    for row in rows {
        let model = resolve_row_model(row, vendor, observations);
        if !totals.contains_key(&model) {
            order.push(model.clone());
        }
        totals.entry(model).or_default().add(row);
    }
    let mut fields = Map::new();
    for model in order {
        let tally = totals.get(&model).copied().unwrap_or_default();
        let _prior = fields.insert(model, lane_bucket_value(vendor, tally));
    }
    Value::Object(fields)
}

fn resolve_row_model(
    row: &TokenUsageRow,
    vendor: TokenVendor,
    observations: &mut TokenObservations,
) -> String {
    let lane = vendor.as_str();
    if vendor == TokenVendor::ClaudeSub {
        if row.model.is_empty() {
            let default = claude_sub_default_model(&row.raw);
            observations.record(TokenObservationKind::DefaultedModel, lane, default);
            return default.to_owned();
        }
        let normalized = normalize_claude_ledger_model(&row.model);
        if normalized != row.model {
            observations.record(TokenObservationKind::NormalizedModel, lane, &row.model);
        }
        observations.note_model(lane, normalized);
        return normalized.to_owned();
    }
    if row.model.is_empty() {
        let default = if vendor == TokenVendor::Codex {
            CODEX_DEFAULT_MODEL
        } else {
            CURSOR_DEFAULT_MODEL
        };
        observations.record(TokenObservationKind::DefaultedModel, lane, default);
        return default.to_owned();
    }
    row.model.clone()
}

/// Render the canonical full token report from extracted inputs.
#[must_use]
pub fn full_report(inputs: &TokenReportInputs) -> Map<String, Value> {
    let mut observations = TokenObservations::default();
    full_report_with_observations(inputs, &mut observations)
}

/// Render the canonical full token report and collect model observations.
#[must_use]
pub fn full_report_with_observations(
    inputs: &TokenReportInputs,
    observations: &mut TokenObservations,
) -> Map<String, Value> {
    let names = vendor_lane_names(inputs);
    let mut data = Map::new();
    let vendors: Vec<Value> = std::iter::once(Value::from("claude"))
        .chain(names.iter().map(|name| Value::from(name.clone())))
        .collect();
    let _prior = data.insert("vendors".to_owned(), Value::Array(vendors));
    let _prior = data.insert(
        "claude".to_owned(),
        per_step_json("claude", &inputs.marks, &inputs.claude),
    );
    for name in &names {
        let _prior = data.insert(
            name.clone(),
            per_step_json(name, &inputs.marks, &inputs.vendor),
        );
    }
    let claude_totals = data
        .get("claude")
        .and_then(|lane| lane.get("totals"))
        .cloned()
        .unwrap_or(Value::Null);
    let claude_field = |key: &str| safe_int(claude_totals.get(key), 0);
    let _prior = data.insert(
        "BUCKETS_claude".to_owned(),
        bucket_value(&[
            ("input", claude_field("input")),
            ("cache_read", claude_field("cache_read")),
            ("cache_create_5m", claude_field("cache_create_5m")),
            ("cache_create_1h", claude_field("cache_create_1h")),
            ("output", claude_field("output")),
            ("total", claude_field("total")),
        ]),
    );
    let first = inputs.marks.first().map_or(0.0, |mark| mark.ts);
    let in_window = slice_rows(&inputs.vendor, first, None);
    for vendor in [
        TokenVendor::Codex,
        TokenVendor::Cursor,
        TokenVendor::ClaudeSub,
    ] {
        insert_vendor_buckets(&mut data, vendor, &in_window, observations);
    }
    data
}

fn insert_vendor_buckets(
    data: &mut Map<String, Value>,
    vendor: TokenVendor,
    in_window: &[&TokenUsageRow],
    observations: &mut TokenObservations,
) {
    let rows: Vec<&TokenUsageRow> = in_window
        .iter()
        .copied()
        .filter(|row| row.vendor == vendor.as_str())
        .collect();
    let tally = UsageTally::of(rows.iter().copied());
    let key = vendor.as_str();
    let _prior = data.insert(format!("BUCKETS_{key}"), lane_bucket_value(vendor, tally));
    let _prior = data.insert(
        format!("BUCKETS_{key}_by_model"),
        by_model_value(&rows, vendor, observations),
    );
}

/// Render the summary token report from extracted inputs.
#[must_use]
pub fn summary_report(inputs: &TokenReportInputs) -> Map<String, Value> {
    let first = inputs.marks.first().map_or(0.0, |mark| mark.ts);
    let claude = UsageTally::of(slice_rows(&inputs.claude, first, None));
    let in_window = slice_rows(&inputs.vendor, first, None);
    let lane =
        |name: &str| UsageTally::of(in_window.iter().copied().filter(|row| row.vendor == name));
    let codex = lane("codex");
    let cursor = lane("cursor");
    let claude_sub = lane("claude_sub");
    let vendor_total: i64 = in_window.iter().map(|row| row.effective_total()).sum();
    let mut data = Map::new();
    for (key, value) in [
        (
            "claude",
            bucket_value(&[
                ("input", claude.input),
                ("cache_read", claude.cache_read),
                ("cache_write_5m", claude.cache_create_5m),
                ("cache_write_1h", claude.cache_create_1h),
                ("output", claude.output),
            ]),
        ),
        (
            "codex",
            bucket_value(&[
                ("input", codex.input),
                ("cached_input", codex.cache_read),
                ("output", codex.output),
            ]),
        ),
        (
            "cursor",
            bucket_value(&[
                ("input", cursor.input),
                ("cache_read", cursor.cache_read),
                ("output", cursor.output),
            ]),
        ),
        (
            "claude_sub",
            bucket_value(&[
                ("input", claude_sub.input),
                ("cache_read", claude_sub.cache_read),
                ("cache_write_5m", claude_sub.cache_create),
                ("cache_write_1h", 0),
                ("output", claude_sub.output),
            ]),
        ),
        ("codex_ledger_total", Value::from(codex.total)),
        ("cursor_ledger_total", Value::from(cursor.total)),
        ("claude_sub_ledger_total", Value::from(claude_sub.total)),
        ("token_total", Value::from(claude.total + vendor_total)),
    ] {
        let _prior = data.insert(key.to_owned(), value);
    }
    data
}

/// Aggregate committed token ledgers into the canonical full-report shape.
///
/// The main-agent `claude` lane is intentionally absent: the session transcript
/// is not committed to the run-log tree, so it cannot be recovered afterwards.
///
/// # Errors
/// Returns [`TokenReportError::NoStepMarks`] when no ledger carries a mark.
pub fn build_report_from_ledgers(
    ledger_paths: &[PathBuf],
    observations: &mut TokenObservations,
) -> Result<Map<String, Value>, TokenReportError> {
    let mut ledger_rows = Vec::new();
    for path in ledger_paths {
        ledger_rows.extend(read_ledger(path));
    }
    let mut marks = ledger_step_marks(&ledger_rows);
    if marks.is_empty() {
        return Err(TokenReportError::NoStepMarks);
    }
    marks.sort_by(|left, right| left.ts.total_cmp(&right.ts));
    let inputs = TokenReportInputs {
        vendor: ledger_vendor_rows(&ledger_rows, observations),
        marks,
        claude: Vec::new(),
        observations: TokenObservations::default(),
    };
    Ok(full_report_with_observations(&inputs, observations))
}

/// Resolve the committed token ledger for one run-log directory.
#[must_use]
pub fn run_log_ledger_path(run_dir: &Path) -> Option<PathBuf> {
    let session_id_path = run_dir.join("session-id");
    if is_regular_file(&session_id_path)
        && let Ok(bytes) = fs::read(&session_id_path)
    {
        let session_id = String::from_utf8_lossy(&bytes).trim().to_owned();
        if !session_id.is_empty() {
            let digest = format!("{:x}", Sha256::digest(session_id.as_bytes()));
            let ledger = run_dir.join(format!("larch-tokens-{digest}.jsonl"));
            if is_regular_file(&ledger) {
                return Some(ledger);
            }
        }
    }
    let mut ledgers: Vec<PathBuf> = fs::read_dir(run_dir)
        .into_iter()
        .flatten()
        .flatten()
        .map(|entry| entry.path())
        .filter(|path| is_ledger_name(path) && is_regular_file(path))
        .collect();
    ledgers.sort();
    (ledgers.len() == 1).then(|| ledgers.remove(0))
}

pub(super) fn is_ledger_name(path: &Path) -> bool {
    path.file_name()
        .and_then(|name| name.to_str())
        .is_some_and(|name| name.starts_with("larch-tokens-"))
        && path.extension().is_some_and(|part| part == "jsonl")
}

fn enrich_by_model(
    report: &mut Map<String, Value>,
    run_dir: &Path,
    key: &str,
    observations: &mut TokenObservations,
) -> bool {
    if object_field(report, key).is_some_and(|bucket| !bucket.is_empty()) {
        return false;
    }
    let Some(ledger) = run_log_ledger_path(run_dir) else {
        return false;
    };
    let Ok(ledger_report) = build_report_from_ledgers(&[ledger], observations) else {
        return false;
    };
    let Some(by_model) = object_field(&ledger_report, key).filter(|bucket| !bucket.is_empty())
    else {
        return false;
    };
    let _prior = report.insert(key.to_owned(), Value::Object(by_model.clone()));
    true
}

/// Why a run was skipped or how its report was recovered.
#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub enum TokenScanWarningKind {
    /// The canonical token report was a symlink.
    ReportSymlink,
    /// The canonical token report could not be read or parsed.
    ReportUnreadable,
    /// The canonical token report's JSON root was not an object.
    ReportNotObject,
    /// The canonical token report was an empty object.
    ReportEmpty,
    /// The canonical token report carried no numeric token counts.
    ReportWithoutTokens,
    /// The run had no canonical token report.
    ReportMissing,
    /// The committed ledger could not be read.
    LedgerUnreadable,
    /// The report was recovered from the committed ledger.
    LedgerRecovered,
    /// Per-model Codex buckets were merged in from the committed ledger.
    CodexModelBucketsMerged,
    /// Per-model spawned-Claude buckets were merged in from the ledger.
    ClaudeSubModelBucketsMerged,
    /// The corpus reader skipped an artifact.
    Corpus,
}

/// A non-fatal, structured scan warning.
pub type TokenScanWarning = super::PathWarning<TokenScanWarningKind>;

/// One priced run selected from a run-log corpus.
#[derive(Clone, Debug)]
pub struct TokenRunRecord {
    /// Issue number from the run manifest.
    pub number: i64,
    /// Issue title, or a synthesized `Issue #N`.
    pub title: String,
    /// Issue URL, empty when no repository slug was supplied.
    pub url: String,
    /// Manifest `started_at`.
    pub started_at: String,
    /// Manifest `updated_at`, falling back to `started_at`.
    pub closed_at: String,
    /// Per-lane totals.
    pub claude: VendorTotals,
    /// Per-lane totals.
    pub codex: VendorTotals,
    /// Per-lane totals.
    pub cursor: VendorTotals,
    /// Per-lane totals.
    pub claude_sub: VendorTotals,
    /// Per-step rows across every lane.
    pub phase_rows: Vec<TokenPhaseRow>,
    /// The resolved raw token report.
    pub raw_report: Map<String, Value>,
    /// Main-agent model recorded in the manifest roster.
    pub main_model: String,
}

/// One streamed scan result.
#[derive(Clone, Debug)]
pub enum TokenScanEvent {
    /// A priced run.
    Record(Box<TokenRunRecord>),
    /// A skipped or recovered artifact.
    Warning(TokenScanWarning),
    /// A model or usage-field finding worth surfacing.
    Observation(TokenObservation),
}

/// Load one run's token report, recovering from the committed ledger.
///
/// Returns `None` when the run has no priceable report; every refusal and every
/// recovery is appended to `warnings`.
#[must_use]
pub fn resolve_run_report(
    run_dir: &Path,
    skill: &str,
    warnings: &mut Vec<TokenScanWarning>,
    observations: &mut TokenObservations,
) -> Option<Map<String, Value>> {
    let basename = token_report_basename(skill);
    let token_path = run_dir.join(basename);
    if fs::symlink_metadata(&token_path).is_ok_and(|meta| meta.file_type().is_symlink()) {
        warnings.push(TokenScanWarning::new(
            TokenScanWarningKind::ReportSymlink,
            token_path.clone(),
            format!("{} is a symlink; skipping", token_path.display()),
        ));
        return None;
    }
    let present = token_path.is_file();
    let canonical = present
        .then(|| load_canonical_report(&token_path, warnings))
        .flatten();
    if let Some(report) = canonical.clone().filter(report_has_numeric_tokens) {
        return Some(enrich_model_buckets(
            report,
            run_dir,
            warnings,
            observations,
        ));
    }
    if let Some(report) =
        ledger_fallback_report(run_dir, warnings, observations).filter(report_has_numeric_tokens)
    {
        warnings.push(TokenScanWarning::new(
            TokenScanWarningKind::LedgerRecovered,
            run_dir.to_owned(),
            format!(
                "recovering token report from committed ledger for {}",
                run_dir.display()
            ),
        ));
        return Some(report);
    }
    if present {
        if canonical.is_some() {
            warnings.push(TokenScanWarning::new(
                TokenScanWarningKind::ReportWithoutTokens,
                token_path.clone(),
                format!(
                    "{} lacks vendor totals/BUCKETS with numeric token counts; skipping",
                    token_path.display()
                ),
            ));
        }
    } else {
        warnings.push(TokenScanWarning::new(
            TokenScanWarningKind::ReportMissing,
            run_dir.to_owned(),
            format!("{} has no {basename}; skipping", run_dir.display()),
        ));
    }
    None
}

fn load_canonical_report(
    token_path: &Path,
    warnings: &mut Vec<TokenScanWarning>,
) -> Option<Map<String, Value>> {
    let display = token_path.display();
    let name = token_path
        .file_name()
        .and_then(|name| name.to_str())
        .unwrap_or_default();
    let parsed: Value = match fs::read(token_path)
        .map_err(|error| error.to_string())
        .and_then(|bytes| serde_json::from_slice(&bytes).map_err(|error| error.to_string()))
    {
        Ok(parsed) => parsed,
        Err(detail) => {
            warnings.push(TokenScanWarning::new(
                TokenScanWarningKind::ReportUnreadable,
                token_path.to_owned(),
                format!("invalid {name} at {display}: {detail}; skipping"),
            ));
            return None;
        }
    };
    let Value::Object(report) = parsed else {
        warnings.push(TokenScanWarning::new(
            TokenScanWarningKind::ReportNotObject,
            token_path.to_owned(),
            format!("{display} is not a JSON object; skipping"),
        ));
        return None;
    };
    if report.is_empty() {
        warnings.push(TokenScanWarning::new(
            TokenScanWarningKind::ReportEmpty,
            token_path.to_owned(),
            format!("{display} is empty; skipping"),
        ));
        return None;
    }
    Some(report)
}

fn ledger_fallback_report(
    run_dir: &Path,
    warnings: &mut Vec<TokenScanWarning>,
    observations: &mut TokenObservations,
) -> Option<Map<String, Value>> {
    let ledger = run_log_ledger_path(run_dir)?;
    if let Err(error) = fs::File::open(&ledger) {
        warnings.push(TokenScanWarning::new(
            TokenScanWarningKind::LedgerUnreadable,
            ledger,
            format!(
                "could not read token ledger for {}: {error}",
                run_dir.display()
            ),
        ));
        return None;
    }
    build_report_from_ledgers(&[ledger], observations).ok()
}

fn enrich_model_buckets(
    report: Map<String, Value>,
    run_dir: &Path,
    warnings: &mut Vec<TokenScanWarning>,
    observations: &mut TokenObservations,
) -> Map<String, Value> {
    let mut enriched = report;
    for (key, kind, label) in [
        (
            "BUCKETS_codex_by_model",
            TokenScanWarningKind::CodexModelBucketsMerged,
            "Codex",
        ),
        (
            "BUCKETS_claude_sub_by_model",
            TokenScanWarningKind::ClaudeSubModelBucketsMerged,
            "Claude subprocess",
        ),
    ] {
        if enrich_by_model(&mut enriched, run_dir, key, observations) {
            warnings.push(TokenScanWarning::new(
                kind,
                run_dir.to_owned(),
                format!(
                    "merging per-model {label} buckets from committed ledger for {}",
                    run_dir.display()
                ),
            ));
        }
    }
    enriched
}

/// Build one priced record from a corpus-accepted run.
#[must_use]
pub fn run_record(
    run: &RunLogRun,
    repo_slug: Option<&str>,
    warnings: &mut Vec<TokenScanWarning>,
    observations: &mut TokenObservations,
) -> Option<TokenRunRecord> {
    let skill = run.layout().skill().as_str().to_owned();
    let report = resolve_run_report(run.directory(), &skill, warnings, observations)?;
    let number = safe_int(run.manifest().field("issue_number"), 0);
    let title = truthy_text(run.manifest().field("title"));
    let started_at = truthy_text(run.manifest().field("started_at"));
    let updated_at = truthy_text(run.manifest().field("updated_at"));
    let main_model = run
        .manifest()
        .field("model_roster")
        .and_then(Value::as_object)
        .map(|roster| truthy_text(roster.get("main")))
        .unwrap_or_default();
    Some(TokenRunRecord {
        number,
        title: if title.is_empty() {
            format!("Issue #{number}")
        } else {
            title
        },
        url: repo_slug.map_or_else(String::new, |slug| {
            format!("https://github.com/{slug}/issues/{number}")
        }),
        closed_at: if updated_at.is_empty() {
            started_at.clone()
        } else {
            updated_at
        },
        started_at,
        claude: vendor_totals_from_report(&report, TokenVendor::Claude),
        codex: vendor_totals_from_report(&report, TokenVendor::Codex),
        cursor: vendor_totals_from_report(&report, TokenVendor::Cursor),
        claude_sub: vendor_totals_from_report(&report, TokenVendor::ClaudeSub),
        phase_rows: token_phase_rows(&report),
        raw_report: report,
        main_model,
    })
}

/// Streaming scan of one skill's runs inside a synchronized corpus root.
#[derive(Debug)]
pub struct TokenCorpusScan {
    runs: RunLogCorpusIter,
    repo_slug: Option<String>,
    limit: Option<usize>,
    seen: usize,
    pending: Vec<TokenScanEvent>,
    finished: bool,
}

impl TokenCorpusScan {
    /// Stream priced records for one skill from a corpus root.
    ///
    /// `limit` bounds how many manifest-accepted runs are inspected, matching
    /// the Python scanner's run-directory budget rather than a record budget.
    #[must_use]
    pub fn new(
        corpus_root: impl Into<PathBuf>,
        selection: RunLogSelection,
        repo_slug: Option<&str>,
        limit: Option<usize>,
    ) -> Self {
        Self {
            runs: RunLogCorpus::new(corpus_root).select(selection),
            repo_slug: repo_slug.map(str::to_owned),
            limit: limit.filter(|value| *value > 0),
            seen: 0,
            pending: Vec::new(),
            finished: false,
        }
    }

    fn expand(&mut self, run: &RunLogRun) {
        let mut warnings = Vec::new();
        let mut observations = TokenObservations::default();
        let record = run_record(
            run,
            self.repo_slug.as_deref(),
            &mut warnings,
            &mut observations,
        );
        self.pending
            .extend(warnings.into_iter().map(TokenScanEvent::Warning));
        self.pending.extend(
            observations
                .entries()
                .iter()
                .cloned()
                .map(TokenScanEvent::Observation),
        );
        if let Some(record) = record {
            self.pending.push(TokenScanEvent::Record(Box::new(record)));
        }
    }
}

impl Iterator for TokenCorpusScan {
    type Item = TokenScanEvent;

    fn next(&mut self) -> Option<Self::Item> {
        loop {
            if !self.pending.is_empty() {
                return Some(self.pending.remove(0));
            }
            if self.finished {
                return None;
            }
            match self.runs.next() {
                None => return None,
                Some(RunLogCorpusEvent::Warning(warning)) => {
                    return Some(TokenScanEvent::Warning(TokenScanWarning::new(
                        TokenScanWarningKind::Corpus,
                        warning.path().to_owned(),
                        warning.message(),
                    )));
                }
                Some(RunLogCorpusEvent::Run(run)) => {
                    self.expand(&run);
                    self.seen += 1;
                    if self.limit.is_some_and(|limit| self.seen >= limit) {
                        self.finished = true;
                    }
                }
            }
        }
    }
}
