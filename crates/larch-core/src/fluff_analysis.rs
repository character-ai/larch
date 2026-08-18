//! Rust owner for the `/fluff-analysis` report.
//!
//! Bug-for-bug port of `skills/fluff-analysis/scripts/fluff-analysis.py`
//! (frozen as `fixtures/rust-parity/fluff_analysis_reference.py`): extraction,
//! the multi-label semantic classifier, acceptance aggregation, assessment and
//! ship-outcome coverage, false-negative diagnostics, and markdown rendering.
//! Corpus walks route through `report::run_log_corpus`; the in-progress
//! session scan is a session-cache surface and reads its directory directly.

use std::collections::{BTreeMap, BTreeSet, HashMap};
use std::fs;
use std::path::{Path, PathBuf};
use std::sync::LazyLock;

use chrono::{Duration as ChronoDuration, NaiveDate, NaiveDateTime, TimeZone};
use regex::Regex;
use serde_json::{Map, Value};

use crate::report::{
    RunLogCorpus, RunLogRoundSort, manifest_only_larch_version, manifest_only_started_at_text,
    round_number_from_path,
};
use crate::review::{compose_self_review_findings_from_tally_json, parse_canonical_heading};
use crate::run_log::{
    AssessmentKind, ReachabilityContext, SHIP_OUTCOME_CUTOVER_VERSION, condition_reached,
    validate_ship_outcome_record,
};

// --------------------------------------------------------------------------
// Python-compatible timestamps
// --------------------------------------------------------------------------

/// A timestamp parsed with Python `datetime.fromisoformat` semantics.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct PyTimestamp {
    naive: NaiveDateTime,
    offset_seconds: Option<i32>,
}

impl PyTimestamp {
    const fn is_aware(self) -> bool {
        self.offset_seconds.is_some()
    }

    const fn promoted_to_utc(mut self) -> Self {
        self.offset_seconds = Some(0);
        self
    }

    fn from_epoch_utc(seconds: f64) -> Option<Self> {
        // Mirrors `datetime.fromtimestamp(mtime, tz=timezone.utc)`.
        #[allow(clippy::cast_possible_truncation)] // Bounded by the chrono range check below.
        let micros = (seconds * 1_000_000.0).round() as i64;
        let naive = chrono::DateTime::from_timestamp_micros(micros)?.naive_utc();
        Some(Self {
            naive,
            offset_seconds: Some(0),
        })
    }

    fn utc_key(self) -> NaiveDateTime {
        self.offset_seconds.map_or(self.naive, |offset| {
            self.naive - ChronoDuration::seconds(i64::from(offset))
        })
    }

    /// Return the Python `datetime.timestamp()` value in float seconds.
    ///
    /// A naive timestamp is interpreted in the local timezone, matching the
    /// analyzer's `--inprogress-since` contract.
    #[must_use]
    pub fn epoch_seconds(self) -> f64 {
        let utc_naive = self.offset_seconds.map_or_else(
            || {
                chrono::Local
                    .from_local_datetime(&self.naive)
                    .earliest()
                    .map_or(self.naive, |local| local.naive_utc())
            },
            |offset| self.naive - ChronoDuration::seconds(i64::from(offset)),
        );
        #[allow(clippy::cast_precision_loss)] // Sub-second precision matches Python floats.
        {
            utc_naive.and_utc().timestamp() as f64
                + f64::from(utc_naive.and_utc().timestamp_subsec_micros()) / 1_000_000.0
        }
    }
}

/// Parse a timestamp with Python 3.11 `datetime.fromisoformat` semantics.
///
/// Covers the spellings this corpus carries: `YYYY-MM-DD`, an optional
/// one-character separator plus `HH:MM[:SS[.frac]]`, and an optional
/// `Z`/`±HH[:MM[:SS]]` offset.
#[must_use]
pub fn parse_python_isoformat(text: &str) -> Option<PyTimestamp> {
    if text.len() < 10 || !text.is_ascii() {
        return None;
    }
    let (date_text, rest) = text.split_at(10);
    let date = parse_iso_date(date_text)?;
    if rest.is_empty() {
        return Some(PyTimestamp {
            naive: date.and_hms_opt(0, 0, 0)?,
            offset_seconds: None,
        });
    }
    // Python 3.11 accepts any single character as the date/time separator.
    let time_text = rest.get(1..)?;
    let (time_of_day, offset_seconds) = parse_iso_time(time_text)?;
    Some(PyTimestamp {
        naive: date.and_time(time_of_day),
        offset_seconds,
    })
}

fn parse_iso_date(text: &str) -> Option<NaiveDate> {
    let bytes = text.as_bytes();
    if bytes.len() != 10 || bytes[4] != b'-' || bytes[7] != b'-' {
        return None;
    }
    let year: i32 = parse_ascii_digits(&text[..4])?;
    let month: u32 = parse_ascii_digits(&text[5..7])?;
    let day: u32 = parse_ascii_digits(&text[8..10])?;
    NaiveDate::from_ymd_opt(year, month, day)
}

fn parse_iso_time(text: &str) -> Option<(chrono::NaiveTime, Option<i32>)> {
    let (clock_text, offset) = split_iso_offset(text)?;
    let mut parts = clock_text.splitn(3, ':');
    let hour: u32 = parse_ascii_digits(parts.next()?)?;
    let minute: u32 = parts.next().map_or(Some(0), parse_ascii_digits)?;
    let (second, micro) = parts.next().map_or(Some((0, 0)), parse_iso_seconds)?;
    let time = chrono::NaiveTime::from_hms_micro_opt(hour, minute, second, micro)?;
    Some((time, offset))
}

fn parse_iso_seconds(text: &str) -> Option<(u32, u32)> {
    let (whole, fraction) = text
        .split_once('.')
        .map_or((text, None), |(whole, fraction)| (whole, Some(fraction)));
    let second: u32 = parse_ascii_digits(whole)?;
    let Some(fraction) = fraction else {
        return Some((second, 0));
    };
    if fraction.is_empty() || !fraction.bytes().all(|byte| byte.is_ascii_digit()) {
        return None;
    }
    // Python truncates fractional digits beyond microseconds.
    let mut padded: String = fraction.chars().take(6).collect();
    while padded.len() < 6 {
        padded.push('0');
    }
    Some((second, parse_ascii_digits(&padded)?))
}

fn split_iso_offset(text: &str) -> Option<(&str, Option<i32>)> {
    if let Some(clock) = text.strip_suffix(['Z', 'z']) {
        return Some((clock, Some(0)));
    }
    let Some(position) = text.rfind(['+', '-']) else {
        return Some((text, None));
    };
    if position == 0 {
        return None;
    }
    let (clock, sign_and_offset) = text.split_at(position);
    let offset_text = &sign_and_offset[1..];
    let sign = if sign_and_offset.starts_with('-') {
        -1
    } else {
        1
    };
    let seconds = parse_offset_magnitude(offset_text)?;
    Some((clock, Some(sign * seconds)))
}

fn parse_offset_magnitude(text: &str) -> Option<i32> {
    let (hours, minutes, seconds) = if text.contains(':') {
        let mut parts = text.splitn(3, ':');
        (
            parse_ascii_digits::<i32>(parts.next()?)?,
            parts.next().map_or(Some(0), parse_ascii_digits)?,
            parts.next().map_or(Some(0), parse_ascii_digits)?,
        )
    } else {
        match text.len() {
            2 => (parse_ascii_digits(text)?, 0, 0),
            4 => (
                parse_ascii_digits(&text[..2])?,
                parse_ascii_digits(&text[2..])?,
                0,
            ),
            _ => return None,
        }
    };
    if hours >= 24 || minutes >= 60 || seconds >= 60 {
        return None;
    }
    Some(hours * 3600 + minutes * 60 + seconds)
}

fn parse_ascii_digits<T: std::str::FromStr>(text: &str) -> Option<T> {
    if text.is_empty() || !text.bytes().all(|byte| byte.is_ascii_digit()) {
        return None;
    }
    text.parse().ok()
}

/// Parse a `--cutoff`-style value: every `Z` becomes `+00:00`, then the text
/// goes through the Python `fromisoformat` parser.
#[must_use]
pub fn parse_cutoff_text(raw: &str) -> Option<PyTimestamp> {
    parse_python_isoformat(&raw.replace('Z', "+00:00"))
}

/// Parse a strict `X.Y.Z` larch version, as the analyzer's version filters do.
#[must_use]
pub fn parse_larch_version_tuple(raw: &str) -> Option<(u64, u64, u64)> {
    static VERSION_RE: LazyLock<Regex> = LazyLock::new(|| {
        Regex::new(r"^(\d+)\.(\d+)\.(\d+)$").expect("static version regex must compile")
    });
    let captures = VERSION_RE.captures(raw.trim())?;
    Some((
        captures[1].parse().ok()?,
        captures[2].parse().ok()?,
        captures[3].parse().ok()?,
    ))
}

// --------------------------------------------------------------------------
// small Python-shaped helpers
// --------------------------------------------------------------------------

fn py_truthy(value: &Value) -> bool {
    match value {
        Value::Null | Value::Bool(false) => false,
        Value::Bool(true) => true,
        Value::Number(number) => number.as_f64().is_some_and(|value| value != 0.0),
        Value::String(text) => !text.is_empty(),
        Value::Array(items) => !items.is_empty(),
        Value::Object(fields) => !fields.is_empty(),
    }
}

fn py_str(value: &Value) -> String {
    crate::review::python_str_of_json(value)
}

/// `str(record.get(key, "") or "")`: the Python truthy-or-empty coercion.
fn str_if_truthy(record: &Map<String, Value>, key: &str) -> String {
    record
        .get(key)
        .filter(|value| py_truthy(value))
        .map(py_str)
        .unwrap_or_default()
}

fn read_text(path: &Path) -> String {
    fs::read(path).map_or_else(
        |_| String::new(),
        |bytes| String::from_utf8_lossy(&bytes).into_owned(),
    )
}

fn pct(numerator: usize, denominator: usize) -> f64 {
    if denominator == 0 {
        0.0
    } else {
        ratio(numerator, denominator) * 100.0
    }
}

#[allow(clippy::cast_precision_loss)] // Counts are small; Python float division is the contract.
fn ratio(numerator: usize, denominator: usize) -> f64 {
    numerator as f64 / denominator as f64
}

fn manifest_started(run_dir: &Path) -> String {
    let text = manifest_only_started_at_text(run_dir);
    if text.is_empty() || parse_python_isoformat(&text).is_none() {
        String::new()
    } else {
        text
    }
}

fn is_dynamic(label: &str) -> bool {
    label.to_lowercase().contains("dyn-")
}

fn normalize_severity(raw: &str) -> &'static str {
    match raw.trim().to_lowercase().as_str() {
        "blocker" | "critical" | "major" | "important" => "important",
        "minor" | "latent" => "latent",
        "nit" | "trivial" => "nit",
        _ => "(none)",
    }
}

fn normalize_design_severity(raw: &str) -> &'static str {
    match raw.trim().to_lowercase().as_str() {
        "major" | "important" => "important",
        "minor" | "latent" => "latent",
        "nit" => "nit",
        _ => "(none)",
    }
}

fn find_severity(text: &str) -> &'static str {
    static SEVERITY_FIELD_RE: LazyLock<Regex> = LazyLock::new(|| {
        Regex::new(r"\*\*Severity\*\*:\s*([a-zA-Z-]+)").expect("static severity regex")
    });
    static SEVERITY_TOKEN_RE: LazyLock<Regex> = LazyLock::new(|| {
        Regex::new(r"\[(blocker|critical|major|important|minor|latent|nit|trivial)\]")
            .expect("static severity token regex")
    });
    if let Some(captures) = SEVERITY_FIELD_RE.captures(text) {
        return normalize_severity(&captures[1]);
    }
    SEVERITY_TOKEN_RE
        .captures(&text.to_lowercase())
        .map_or("(none)", |captures| normalize_severity(&captures[1]))
}

/// First-inserted value wins count ties, matching `Counter.most_common(1)`.
fn modal(values: &[String]) -> String {
    let mut order: Vec<&str> = Vec::new();
    let mut counts: HashMap<&str, usize> = HashMap::new();
    for value in values.iter().filter(|value| !value.is_empty()) {
        let entry = counts.entry(value.as_str()).or_insert(0);
        if *entry == 0 {
            order.push(value.as_str());
        }
        *entry += 1;
    }
    let Some(top) = order.iter().map(|value| counts[value]).max() else {
        return String::new();
    };
    order
        .iter()
        .find(|value| counts[*value] == top)
        .map_or_else(String::new, |value| (*value).to_owned())
}

fn period_of(cutoff: Option<PyTimestamp>, started_at: &str, mtime: Option<f64>) -> &'static str {
    let Some(cutoff) = cutoff else {
        return "all";
    };
    let when = if started_at.is_empty() {
        mtime
            .filter(|value| *value != 0.0)
            .and_then(PyTimestamp::from_epoch_utc)
    } else {
        parse_cutoff_text(started_at)
    };
    let Some(mut when) = when else {
        return "unknown";
    };
    if cutoff.is_aware() && !when.is_aware() {
        when = when.promoted_to_utc();
    }
    if when.utc_key() >= cutoff.utc_key() {
        "post"
    } else {
        "pre"
    }
}

fn period_of_version(since_version: (u64, u64, u64), larch_version: &str) -> &'static str {
    parse_larch_version_tuple(larch_version).map_or("unknown", |parsed| {
        if parsed >= since_version {
            "post"
        } else {
            "pre"
        }
    })
}

fn run_period(
    cutoff: Option<PyTimestamp>,
    since_version: Option<(u64, u64, u64)>,
    started_at: &str,
    larch_version: &str,
) -> &'static str {
    since_version.map_or_else(
        || period_of(cutoff, started_at, None),
        |since| period_of_version(since, larch_version),
    )
}

// --------------------------------------------------------------------------
// insertion-ordered map (Python dict iteration parity)
// --------------------------------------------------------------------------

struct OrderedMap<V>(Vec<(String, V)>);

impl<V> OrderedMap<V> {
    const fn new() -> Self {
        Self(Vec::new())
    }

    fn get(&self, key: &str) -> Option<&V> {
        self.0
            .iter()
            .find(|(existing, _)| existing == key)
            .map(|(_, value)| value)
    }

    fn insert(&mut self, key: &str, value: V) {
        if let Some(slot) = self
            .0
            .iter_mut()
            .find(|(existing, _)| existing == key)
            .map(|(_, existing)| existing)
        {
            *slot = value;
        } else {
            self.0.push((key.to_owned(), value));
        }
    }

    fn iter(&self) -> impl Iterator<Item = &(String, V)> {
        self.0.iter()
    }

    const fn is_empty(&self) -> bool {
        self.0.is_empty()
    }
}

// --------------------------------------------------------------------------
// finding-id join helpers
// --------------------------------------------------------------------------

fn first_canonical_heading_id(text: &str) -> String {
    text.lines()
        .find_map(|line| parse_canonical_heading(line).map(|heading| heading.item_id))
        .unwrap_or_default()
}

fn finding_tokens(value: &str, prose_body: &str) -> BTreeSet<String> {
    static REJ_RE: LazyLock<Regex> =
        LazyLock::new(|| Regex::new(r"^REJ_CR\d+_(\d+)$").expect("static REJ id regex"));
    static FINDING_RE: LazyLock<Regex> =
        LazyLock::new(|| Regex::new(r"^FINDING_(\d+)$").expect("static FINDING id regex"));
    let heading_id = first_canonical_heading_id(prose_body);
    let mut tokens = BTreeSet::new();
    for raw in [value, heading_id.as_str()] {
        let text = raw.trim().to_uppercase();
        if text.is_empty() {
            continue;
        }
        if let Some(captures) = REJ_RE.captures(&text) {
            let _ = tokens.insert(format!("FINDING_{}", &captures[1]));
        }
        if let Some(captures) = FINDING_RE.captures(&text) {
            let _ = tokens.insert(format!("REJ_CR1_{}", &captures[1]));
        }
        let _ = tokens.insert(text);
    }
    tokens
}

type TokenIndex<'r> = HashMap<(String, String), &'r Map<String, Value>>;

fn records_by_round_and_token(records: &[Map<String, Value>]) -> TokenIndex<'_> {
    let mut out = HashMap::new();
    for record in records {
        let prose = ["prose_body", "body", "text"]
            .iter()
            .find_map(|key| {
                record
                    .get(*key)
                    .filter(|value| py_truthy(value))
                    .map(py_str)
            })
            .unwrap_or_default();
        let round_num = str_if_truthy(record, "round_num");
        for token in finding_tokens(&str_if_truthy(record, "id"), &prose) {
            let _ = out.insert((round_num.clone(), token), record);
        }
    }
    out
}

enum JsonlLookup<'r> {
    Missing,
    One(&'r Map<String, Value>),
    Ambiguous,
}

fn lookup_jsonl_record<'r>(
    by_token: &TokenIndex<'r>,
    round_num: &str,
    row_id: &str,
    allow_unscoped: bool,
) -> JsonlLookup<'r> {
    let mut unique: Vec<&'r Map<String, Value>> = Vec::new();
    for token in finding_tokens(row_id, "") {
        let matched = by_token
            .get(&(round_num.to_owned(), token.clone()))
            .copied()
            .or_else(|| {
                if allow_unscoped {
                    by_token.get(&(String::new(), token)).copied()
                } else {
                    None
                }
            });
        if let Some(record) = matched
            && !unique
                .iter()
                .any(|existing| std::ptr::eq(*existing, record))
        {
            unique.push(record);
        }
    }
    match unique.len() {
        0 => JsonlLookup::Missing,
        1 => JsonlLookup::One(unique[0]),
        _ => JsonlLookup::Ambiguous,
    }
}

// --------------------------------------------------------------------------
// semantic-group classifier — a finding may carry many tags (multi-label)
// --------------------------------------------------------------------------

const TAG_PATTERNS: [(&str, &str); 24] = [
    // Out-of-Scope ("fluff") signals named by skills/shared/review-acceptance-rubric.md
    (
        "rub:cleaner/clarity",
        r"\bcleaner\b|more readable|for clarity|readability|easier to read",
    ),
    (
        "rub:more-robust",
        r"more robust|be more robust|increase robustness",
    ),
    (
        "rub:idiomatic/bestprac",
        r"idiomatic|best practice|conventional|more consistent|consistency|uniform",
    ),
    (
        "rub:flexible/futureproof",
        r"more flexible|future[- ]proof|extensib|generaliz",
    ),
    (
        "rub:while-were-here",
        r"while (we|you)('| a)re here|since (we|you)('| a)re|opportunistic|as a bonus|also worth",
    ),
    (
        "rub:defensive/incase",
        r"defensive|in case|just in case|guard against|cannot (occur|happen)|can'?t (occur|happen)|should never|belt and suspenders",
    ),
    (
        "rub:configurability",
        r"configurab|make .* configurable|add (a |an )?(flag|option|env var|knob)|parameteriz",
    ),
    (
        "rub:rename",
        r"\brename\b|renaming|better name|clearer name",
    ),
    (
        "rub:nice-to-have",
        r"nice to have|would be nice|consider (adding|using|whether)|might want to|could also|optional(ly)?",
    ),
    // broad themes
    (
        "theme:testing",
        r"\btest\b|\btests\b|harness|assertion|\bassert\b|coverage|fixture|\bTDD\b|red[- ]green|test case",
    ),
    (
        "theme:docs/comments",
        r"\bdoc\b|\bdocs\b|documentation|readme|changelog|\bcomment\b|docstring|prose|wording|\btypo\b|\.md\b|spelling",
    ),
    (
        "theme:naming",
        r"\brename\b|naming|variable name|function name|identifier name|misnomer",
    ),
    (
        "theme:style/lint",
        r"\bstyle\b|formatting|whitespace|\blint\b|casing|indent|trailing|quote style",
    ),
    (
        "theme:refactor/dry",
        r"refactor|deduplicat|\bDRY\b|extract (a )?(helper|function|method)|consolidat|simplif|collaps|factor out|reduce duplication",
    ),
    (
        "theme:perf",
        r"performance|efficien|optimiz|\bslow\b|latency|\bO\(|caching|redundant (work|call|read)",
    ),
    (
        "theme:error-handling",
        r"error handling|error message|\bexception\b|failure mode|\bretry\b|fallback|graceful|swallow",
    ),
    (
        "theme:robustness",
        r"robust|race condition|concurren|idempoten|atomic|resource leak|cleanup|partial failure|signal handling",
    ),
    (
        "theme:edge-case",
        r"edge case|boundary|corner case|off[- ]by[- ]one|empty (input|list|string)|\bnull\b|\bnil\b|unset|zero[- ]length",
    ),
    (
        "theme:validation",
        r"validate|validation|sanitiz|input check|bounds check|malformed|untrusted|guardrail",
    ),
    (
        "theme:security",
        r"secret|injection|\bssrf\b|traversal|redact|\bleak\b|\bauth\b|permission|sandbox|\bvuln|crypto|credential|token leak|password",
    ),
    (
        "theme:completeness",
        r"missing|omit|incomplete|not (updated|covered|handled|wired|listed)|left out|forgot|fails to (update|cover|include)|absent from",
    ),
    (
        "theme:correctness",
        r"incorrect|\bwrong\b|\bbug\b|logic error|inverted|mismatch|broken|does not (match|work)|doesn'?t (match|work)|stale",
    ),
    (
        "theme:backward-compat",
        r"backward|back[- ]compat|breaking change|migration|deprecat|existing caller|wire (format|surface)",
    ),
    (
        "theme:portability",
        r"portab|bash 3\.2|macos|posix|gnu vs bsd|platform[- ]specific|cross[- ]shell|awk implementation",
    ),
];

static TAGS: LazyLock<Vec<(&'static str, Regex)>> = LazyLock::new(|| {
    TAG_PATTERNS
        .iter()
        .map(|(name, pattern)| {
            let compiled =
                Regex::new(&format!("(?i){pattern}")).expect("static tag regex must compile");
            (*name, compiled)
        })
        .collect()
});

const SEV_BODY: [&str; 8] = [
    "blocker",
    "critical",
    "major",
    "important",
    "minor",
    "latent",
    "nit",
    "trivial",
];

fn tags_of(text: &str) -> Vec<&'static str> {
    TAGS.iter()
        .filter(|(_name, pattern)| pattern.is_match(text))
        .map(|(name, _pattern)| *name)
        .collect()
}

// --------------------------------------------------------------------------
// parsers (defensive against format drift across the log corpus)
// --------------------------------------------------------------------------

static HEAD_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?m)^#{2,4}\s+((?:FINDING|OOS|REJ)[_A-Z0-9]*\d)\b[:\s]?(.*)$")
        .expect("static block-heading regex")
});
static FIELD_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?m)^\s*-\s+\*\*(.+?)\*\*:\s*(.*)$").expect("static block-field regex")
});
static ID_PREFIX_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^(FINDING|OOS|REJ)").expect("static id-prefix regex"));
static ROUND_IN_TEXT_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"round-(\d+)").expect("static round regex"));

#[derive(Clone, Default)]
struct MdBlock {
    title: String,
    fields: HashMap<String, String>,
    raw: String,
}

/// Parse `### FINDING_N:` style blocks into `{id: {title, fields, raw}}`.
fn parse_md_blocks(text: &str) -> HashMap<String, MdBlock> {
    let mut out: HashMap<String, MdBlock> = HashMap::new();
    let matches: Vec<regex::Captures<'_>> = HEAD_RE.captures_iter(text).collect();
    for (index, captures) in matches.iter().enumerate() {
        let fid = captures.get(1).map_or("", |group| group.as_str());
        let title = captures
            .get(2)
            .map_or("", |group| group.as_str())
            .trim()
            .to_owned();
        let start = captures.get(0).map_or(0, |group| group.end());
        let end = matches
            .get(index + 1)
            .and_then(|next| next.get(0))
            .map_or(text.len(), |group| group.start());
        let body = &text[start..end];
        let mut fields: HashMap<String, String> = HashMap::new();
        for field in FIELD_RE.captures_iter(body) {
            let key = field[1].trim().to_lowercase();
            let _ = fields
                .entry(key)
                .or_insert_with(|| field[2].trim().to_owned());
        }
        let raw = format!("{title}\n{body}");
        let replace = out
            .get(fid)
            .is_none_or(|existing| fields.len() > existing.fields.len());
        if replace {
            let _ = out.insert(fid.to_owned(), MdBlock { title, fields, raw });
        }
    }
    out
}

fn parse_voting_tally(text: &str) -> OrderedMap<String> {
    static TALLY_ROW_RE: LazyLock<Regex> = LazyLock::new(|| {
        Regex::new(r"^\s*\|\s*((?:FINDING|OOS|REJ)[_A-Z0-9]*\d)\s*\|(.+)\|\s*$")
            .expect("static tally-row regex")
    });
    let mut out = OrderedMap::new();
    for line in text.lines() {
        let Some(captures) = TALLY_ROW_RE.captures(line) else {
            continue;
        };
        let cells: Vec<&str> = captures[2].split('|').map(str::trim).collect();
        let result = cells
            .last()
            .map_or_else(String::new, |cell| cell.to_lowercase());
        out.insert(&captures[1], result);
    }
    out
}

/// One `csv.DictReader`-shaped row: header names mapped to present cells.
fn tsv_dict_rows<'t>(lines: &[&'t str]) -> Vec<HashMap<&'t str, &'t str>> {
    let Some((header_line, rows)) = lines.split_first() else {
        return Vec::new();
    };
    let header: Vec<&str> = header_line.split('\t').collect();
    rows.iter()
        .filter(|line| !line.is_empty())
        .map(|line| {
            let cells: Vec<&str> = line.split('\t').collect();
            let mut row = HashMap::new();
            for (index, name) in header.iter().enumerate() {
                if let Some(cell) = cells.get(index) {
                    let _ = row.insert(*name, *cell);
                }
            }
            row
        })
        .collect()
}

#[derive(Clone, Default)]
struct DesignRow {
    result: String,
    reviewers: String,
    severities: Vec<String>,
    body_severity: String,
    scope: String,
}

/// Parse design `findings-classification.tsv` header supersets.
fn parse_design_tsv(text: &str) -> OrderedMap<DesignRow> {
    let mut out = OrderedMap::new();
    let lines: Vec<&str> = text.lines().collect();
    if lines.is_empty() {
        return out;
    }
    for row in tsv_dict_rows(&lines) {
        let fid = row.get("finding_id").copied().unwrap_or("").trim();
        if !ID_PREFIX_RE.is_match(fid) {
            continue;
        }
        let severities = (1..=3)
            .filter_map(|index| {
                let key = format!("v{index}_severity");
                row.get(key.as_str())
                    .copied()
                    .filter(|cell| !cell.is_empty())
                    .map(|cell| normalize_design_severity(cell).to_owned())
            })
            .collect();
        out.insert(
            fid,
            DesignRow {
                result: row
                    .get("voting_result")
                    .copied()
                    .unwrap_or("")
                    .trim()
                    .to_lowercase(),
                reviewers: row
                    .get("finding_reviewers")
                    .copied()
                    .unwrap_or("")
                    .trim()
                    .to_owned(),
                severities,
                body_severity: row
                    .get("body_severity")
                    .copied()
                    .unwrap_or("")
                    .trim()
                    .to_owned(),
                scope: row.get("scope").copied().unwrap_or("").trim().to_owned(),
            },
        );
    }
    out
}

#[derive(Clone, Default)]
struct ImplRow {
    voting_result: String,
    body_severity: String,
    scope: String,
    severities: Vec<String>,
}

/// Parse implement/code-review TSV ratings from compact and named schemas.
fn parse_impl_tsv(text: &str) -> OrderedMap<ImplRow> {
    let mut out = OrderedMap::new();
    let lines: Vec<&str> = text.lines().collect();
    let Some(header_line) = lines.first() else {
        return out;
    };
    let header: Vec<&str> = header_line.split('\t').collect();
    let has_named_ratings =
        (1..=3).all(|index| header.contains(&format!("v{index}_severity").as_str()));
    if has_named_ratings {
        for row in tsv_dict_rows(&lines) {
            let fid = row.get("finding_id").copied().unwrap_or("").trim();
            if !ID_PREFIX_RE.is_match(fid) {
                continue;
            }
            let severities = (1..=3)
                .filter_map(|index| {
                    let key = format!("v{index}_severity");
                    row.get(key.as_str())
                        .copied()
                        .filter(|cell| !cell.is_empty())
                        .map(str::to_lowercase)
                })
                .collect();
            out.insert(
                fid,
                ImplRow {
                    voting_result: row
                        .get("voting_result")
                        .copied()
                        .unwrap_or("")
                        .trim()
                        .to_lowercase(),
                    body_severity: row
                        .get("body_severity")
                        .copied()
                        .unwrap_or("")
                        .trim()
                        .to_owned(),
                    scope: row.get("scope").copied().unwrap_or("").trim().to_owned(),
                    severities,
                },
            );
        }
        return out;
    }
    for line in lines.iter().skip(1) {
        let cells: Vec<&str> = line.split('\t').collect();
        if cells.len() != 18 || !ID_PREFIX_RE.is_match(cells[0]) {
            continue;
        }
        let get = |index: usize| cells.get(index).map_or("", |cell| cell.trim());
        let severities = [get(5), get(10), get(15)]
            .iter()
            .filter(|cell| !cell.is_empty())
            .map(|cell| cell.to_lowercase())
            .collect();
        out.insert(
            cells[0],
            ImplRow {
                voting_result: get(2).to_lowercase(),
                body_severity: String::new(),
                scope: String::new(),
                severities,
            },
        );
    }
    out
}

fn scope_is_oos(scope: &str, finding_id: &str) -> bool {
    let value = scope.trim().to_lowercase();
    matches!(value.as_str(), "oos" | "out_of_scope" | "out-of-scope")
        || finding_id.to_uppercase().starts_with("OOS_")
}

fn reviewer_claimed_tier(body_severity: &str, corpus: &str) -> &'static str {
    let raw = body_severity.trim().to_lowercase();
    if raw.is_empty() {
        return "(none)";
    }
    if matches!(raw.as_str(), "blocker" | "critical" | "blocking") {
        return "important";
    }
    if corpus == "design" {
        normalize_design_severity(&raw)
    } else {
        normalize_severity(&raw)
    }
}

fn round_from_path(path: &Path) -> String {
    round_number_from_path(path).map_or_else(String::new, |round| round.to_string())
}

fn round_from_text(text: &str) -> String {
    ROUND_IN_TEXT_RE
        .captures(text)
        .map_or_else(String::new, |captures| captures[1].to_owned())
}

fn round_dir_names(run_dir: &Path) -> Vec<PathBuf> {
    let Ok(entries) = fs::read_dir(run_dir) else {
        return Vec::new();
    };
    let mut paths: Vec<PathBuf> = entries
        .filter_map(Result::ok)
        .map(|entry| entry.path())
        .filter(|path| {
            path.file_name()
                .and_then(|name| name.to_str())
                .is_some_and(|name| name.starts_with("round-"))
        })
        .collect();
    paths.sort();
    paths
}

fn run_has_multiple_rounds(run_dir: &Path) -> bool {
    round_dir_names(run_dir)
        .iter()
        .filter(|path| path.is_dir())
        .count()
        > 1
}

fn round_local_jsonl_paths(run_dir: &Path) -> Vec<PathBuf> {
    round_dir_names(run_dir)
        .into_iter()
        .filter(|path| path.is_dir())
        .map(|path| path.join("review-findings-full.jsonl"))
        .filter(|path| fs::symlink_metadata(path).is_ok())
        .collect()
}

fn load_jsonl(path: &Path) -> Vec<Map<String, Value>> {
    read_text(path)
        .lines()
        .filter_map(|line| {
            let line = line.trim();
            if line.is_empty() {
                return None;
            }
            match serde_json::from_str::<Value>(line) {
                Ok(Value::Object(record)) => Some(record),
                _ => None,
            }
        })
        .collect()
}

fn impl_jsonl_records_by_round(run_dir: &Path) -> Vec<(String, Vec<Map<String, Value>>)> {
    let mut by_round: Vec<(String, Vec<Map<String, Value>>)> = Vec::new();
    let mut push = |round: String, record: Map<String, Value>| {
        if let Some((_, records)) = by_round.iter_mut().find(|(key, _)| *key == round) {
            records.push(record);
        } else {
            by_round.push((round, vec![record]));
        }
    };
    let round_local = round_local_jsonl_paths(run_dir);
    if round_local.is_empty() {
        for record in load_jsonl(&run_dir.join("review-findings-full.jsonl")) {
            let round = str_if_truthy(&record, "round_num");
            push(round, record);
        }
        return by_round;
    }
    for path in round_local {
        let path_round = round_from_path(&path);
        for mut record in load_jsonl(&path) {
            if !record.get("round_num").is_some_and(py_truthy) {
                let _ = record.insert("round_num".to_owned(), Value::String(path_round.clone()));
            }
            let round = {
                let text = str_if_truthy(&record, "round_num");
                if text.is_empty() {
                    path_round.clone()
                } else {
                    text
                }
            };
            push(round, record);
        }
    }
    by_round
}

// --------------------------------------------------------------------------
// extraction
// --------------------------------------------------------------------------

#[derive(Clone)]
struct Record {
    skill: &'static str,
    source: &'static str,
    run_id: String,
    finding_id: String,
    phase: String,
    outcome: String,
    is_oos_id: bool,
    severity: String,
    body_severity: String,
    scope: String,
    is_dynamic: bool,
    v_severities: Vec<String>,
    period: &'static str,
    text: String,
    tags: Vec<&'static str>,
}

fn cap_chars(text: &str, limit: usize) -> String {
    text.chars().take(limit).collect()
}

struct RunContext {
    run_id: String,
    period: &'static str,
}

fn run_context(
    run_dir: &Path,
    cutoff: Option<PyTimestamp>,
    since_version: Option<(u64, u64, u64)>,
) -> RunContext {
    let started = manifest_started(run_dir);
    let larch_version = manifest_only_larch_version(run_dir);
    let period = run_period(cutoff, since_version, &started, &larch_version);
    RunContext {
        run_id: run_dir
            .file_name()
            .map_or_else(String::new, |name| name.to_string_lossy().into_owned()),
        period,
    }
}

fn implement_round_tsvs(corpus: &RunLogCorpus) -> HashMap<PathBuf, Vec<PathBuf>> {
    let mut by_run: HashMap<PathBuf, Vec<PathBuf>> = HashMap::new();
    for (canonical_run, path) in
        corpus.classification_paths_without_manifest("implement", RunLogRoundSort::Lexical)
    {
        by_run.entry(canonical_run).or_default().push(path);
    }
    by_run
}

fn canonical_run_key(run_dir: &Path) -> Option<PathBuf> {
    fs::canonicalize(run_dir).ok()
}

#[allow(clippy::too_many_lines)] // Parity extraction preserves the Python record shape verbatim.
fn extract_one_implement_run(
    run_dir: &Path,
    tsv_paths: &[PathBuf],
    cutoff: Option<PyTimestamp>,
    since_version: Option<(u64, u64, u64)>,
) -> Vec<Record> {
    static TITLE_HEADING_RE: LazyLock<Regex> = LazyLock::new(|| {
        Regex::new(r"(?m)^#{2,4}\s+(?:(?:FINDING|OOS|REJ)[_A-Z0-9]*\d[:\s]+)?(.*)$")
            .expect("static title-heading regex")
    });
    let context = run_context(run_dir, cutoff, since_version);
    let jsonl_path = run_dir.join("review-findings-full.jsonl");
    let mut round_tsv: OrderedMap<OrderedMap<ImplRow>> = OrderedMap::new();
    for tsv in tsv_paths {
        let round = round_from_text(&tsv.to_string_lossy());
        round_tsv.insert(&round, parse_impl_tsv(&read_text(tsv)));
    }
    if fs::metadata(&jsonl_path).is_err() {
        return self_review_tally_records(run_dir, &context);
    }
    let mut malformed_jsonl = false;
    let mut records = Vec::new();
    for line in read_text(&jsonl_path).lines() {
        let line = line.trim();
        if line.is_empty() {
            continue;
        }
        let Ok(data) = serde_json::from_str::<Value>(line) else {
            malformed_jsonl = true;
            continue;
        };
        let Value::Object(data) = data else {
            continue;
        };
        let is_retroactive =
            data.get("phase") == Some(&Value::String("retroactive-backfill".to_owned()));
        let outcome = str_if_truthy(&data, "outcome");
        if is_retroactive || outcome.is_empty() {
            continue;
        }
        let phase = {
            let text = str_if_truthy(&data, "phase");
            if text.is_empty() {
                "code-review".to_owned()
            } else {
                text
            }
        };
        let fid = str_if_truthy(&data, "id");
        let rnum = str_if_truthy(&data, "round_num");
        let slots: Vec<String> = data.get("reviewer_slots").map_or_else(
            || {
                data.get("reviewer")
                    .and_then(Value::as_str)
                    .map(|reviewer| vec![reviewer.to_owned()])
                    .unwrap_or_default()
            },
            |value| match value {
                Value::Array(items) => items
                    .iter()
                    .filter_map(Value::as_str)
                    .map(str::to_owned)
                    .collect(),
                _ => data
                    .get("reviewer")
                    .and_then(Value::as_str)
                    .map(|reviewer| vec![reviewer.to_owned()])
                    .unwrap_or_default(),
            },
        );
        let rev_str = slots.join(", ");
        let cat = str_if_truthy(&data, "category");
        let prose = str_if_truthy(&data, "prose_body");
        let body_severity = str_if_truthy(&data, "body_severity");
        let severity = if body_severity.is_empty() {
            find_severity(&prose)
        } else {
            normalize_severity(&body_severity)
        };
        let title = if cat.is_empty() {
            let heading = TITLE_HEADING_RE
                .captures(&prose)
                .map_or_else(String::new, |captures| captures[1].trim().to_owned());
            cap_chars(&heading, 200)
        } else {
            cat
        };
        let ratings = round_tsv
            .get(&rnum)
            .and_then(|rows| rows.get(&fid))
            .cloned()
            .unwrap_or_default();
        let text = cap_chars(&format!("{title}\n{prose}"), 2000);
        records.push(Record {
            skill: "implement",
            source: "committed",
            run_id: context.run_id.clone(),
            finding_id: fid.clone(),
            phase,
            outcome,
            is_oos_id: fid.starts_with("OOS"),
            severity: severity.to_owned(),
            body_severity,
            scope: ratings.scope,
            is_dynamic: is_dynamic(&rev_str),
            v_severities: ratings.severities,
            period: context.period,
            text,
            tags: Vec::new(),
        });
    }
    if records.is_empty() && !malformed_jsonl {
        return self_review_tally_records(run_dir, &context);
    }
    records
}

fn self_review_tally_records(run_dir: &Path, context: &RunContext) -> Vec<Record> {
    let Ok(bytes) = fs::read(run_dir.join("code-review-tally.json")) else {
        return Vec::new();
    };
    let jsonl = compose_self_review_findings_from_tally_json(&String::from_utf8_lossy(&bytes));
    let mut rows = Vec::new();
    for line in jsonl.lines() {
        let Ok(Value::Object(item)) = serde_json::from_str::<Value>(line) else {
            return Vec::new();
        };
        rows.push(Record {
            skill: "implement",
            source: "committed-self-review-tally",
            run_id: context.run_id.clone(),
            finding_id: item
                .get("id")
                .and_then(Value::as_str)
                .unwrap_or_default()
                .to_owned(),
            phase: "code-review".to_owned(),
            outcome: item
                .get("outcome")
                .and_then(Value::as_str)
                .unwrap_or_default()
                .to_owned(),
            is_oos_id: false,
            severity: "(none)".to_owned(),
            body_severity: String::new(),
            scope: String::new(),
            is_dynamic: false,
            v_severities: Vec::new(),
            period: context.period,
            text: String::new(),
            tags: Vec::new(),
        });
    }
    rows
}

fn extract_implement(
    implement_root: &Path,
    cutoff: Option<PyTimestamp>,
    since_version: Option<(u64, u64, u64)>,
) -> Vec<Record> {
    let corpus = RunLogCorpus::new(implement_root);
    let tsvs_by_run = implement_round_tsvs(&corpus);
    let mut records = Vec::new();
    for run_dir in corpus.safe_child_run_directories() {
        let tsv_paths = canonical_run_key(&run_dir)
            .and_then(|key| tsvs_by_run.get(&key).cloned())
            .unwrap_or_default();
        records.extend(extract_one_implement_run(
            &run_dir,
            &tsv_paths,
            cutoff,
            since_version,
        ));
    }
    records
}

#[allow(clippy::too_many_lines)] // Parity extraction preserves the Python record shape verbatim.
fn extract_one_design_tsv(
    tsv: &Path,
    design_root: &Path,
    cutoff: Option<PyTimestamp>,
    since_version: Option<(u64, u64, u64)>,
) -> Vec<Record> {
    static DESIGN_RUN_RE: LazyLock<Regex> =
        LazyLock::new(|| Regex::new(r"/design/([^/]+)/").expect("static design-run regex"));
    let tsv_text = tsv
        .to_string_lossy()
        .replace(std::path::MAIN_SEPARATOR, "/");
    let run_id = DESIGN_RUN_RE
        .captures(&tsv_text)
        .map_or_else(String::new, |captures| captures[1].to_owned());
    let run_dir = design_root.join(&run_id);
    let started = manifest_started(&run_dir);
    let larch_version = manifest_only_larch_version(&run_dir);
    let period = run_period(cutoff, since_version, &started, &larch_version);
    let block_dir = tsv.parent().map_or_else(PathBuf::new, Path::to_path_buf);
    let tsv_recs = parse_design_tsv(&read_text(tsv));
    let content = parse_md_blocks(&read_text(&block_dir.join("findings.md")));
    let mut records = Vec::new();
    for (fid, trec) in tsv_recs.iter() {
        let crec = content.get(fid).cloned().unwrap_or_default();
        let field = |key: &str| crec.fields.get(key).cloned().unwrap_or_default();
        let reviewers = if trec.reviewers.is_empty() {
            field("reviewer(s)")
        } else {
            trec.reviewers.clone()
        };
        let title = [
            crec.title.clone(),
            cap_chars(&field("concern"), 120),
            fid.clone(),
        ]
        .into_iter()
        .find(|candidate| !candidate.is_empty())
        .unwrap_or_default();
        let severity = if trec.body_severity.is_empty() {
            let modal_severity = modal(&trec.severities);
            if modal_severity.is_empty() {
                normalize_design_severity(&field("severity")).to_owned()
            } else {
                modal_severity
            }
        } else {
            normalize_design_severity(&trec.body_severity).to_owned()
        };
        let severity = if severity.is_empty() {
            "(none)".to_owned()
        } else {
            severity
        };
        let fallback_text = if reviewers.is_empty() {
            fid.clone()
        } else {
            reviewers.clone()
        };
        let concern = {
            let value = field("concern");
            if value.is_empty() {
                fallback_text
            } else {
                value
            }
        };
        let text = cap_chars(
            &format!(
                "{title}\n{concern}\n{}\n{}",
                field("proposed resolution"),
                crec.raw
            ),
            2000,
        );
        records.push(Record {
            skill: "design",
            source: "committed",
            run_id: run_id.clone(),
            finding_id: fid.clone(),
            phase: "plan-review".to_owned(),
            outcome: trec.result.clone(),
            is_oos_id: fid.starts_with("OOS"),
            severity,
            body_severity: trec.body_severity.clone(),
            scope: trec.scope.clone(),
            is_dynamic: is_dynamic(&reviewers),
            v_severities: trec.severities.clone(),
            period,
            text,
            tags: Vec::new(),
        });
    }
    records
}

fn extract_design(
    design_root: &Path,
    cutoff: Option<PyTimestamp>,
    since_version: Option<(u64, u64, u64)>,
) -> Vec<Record> {
    RunLogCorpus::new(design_root)
        .classification_files_anywhere()
        .iter()
        .flat_map(|tsv| extract_one_design_tsv(tsv, design_root, cutoff, since_version))
        .collect()
}

fn session_design_dirs(sessions_dir: &Path) -> Vec<PathBuf> {
    let Ok(entries) = fs::read_dir(sessions_dir) else {
        return Vec::new();
    };
    let mut paths: Vec<PathBuf> = entries
        .filter_map(Result::ok)
        .map(|entry| entry.path())
        .filter(|path| {
            path.file_name()
                .and_then(|name| name.to_str())
                .is_some_and(|name| name.starts_with("claude-design-"))
        })
        .collect();
    paths.sort();
    paths
}

fn file_mtime_seconds(path: &Path) -> Option<f64> {
    let modified = fs::metadata(path).ok()?.modified().ok()?;
    let elapsed = modified.duration_since(std::time::UNIX_EPOCH).ok()?;
    #[allow(clippy::cast_precision_loss)] // Fractional mtimes match Python float precision.
    Some(elapsed.as_secs_f64())
}

const IN_PROGRESS_CONTENT_FILES: [&str; 6] = [
    "findings.md",
    "accepted-plan-findings.md",
    "accepted-plan-findings-all.md",
    "rejected-findings.md",
    "findings-oos.md",
    "findings-in-scope.md",
];

#[allow(clippy::too_many_lines)] // Parity extraction preserves the Python record shape verbatim.
fn extract_in_progress(
    sessions_dir: &Path,
    cutoff: Option<PyTimestamp>,
    inprogress_min: Option<f64>,
) -> Vec<Record> {
    let mut records = Vec::new();
    for session_dir in session_design_dirs(sessions_dir) {
        let tally_path = session_dir.join("voting-tally.md");
        if fs::metadata(&tally_path).is_err() {
            continue;
        }
        let Some(mtime) = file_mtime_seconds(&tally_path) else {
            continue;
        };
        if inprogress_min.is_some_and(|minimum| minimum != 0.0 && mtime < minimum) {
            continue;
        }
        let tally = parse_voting_tally(&read_text(&tally_path));
        if tally.is_empty() {
            continue;
        }
        let mut content: HashMap<String, MdBlock> = HashMap::new();
        for name in IN_PROGRESS_CONTENT_FILES {
            let path = session_dir.join(name);
            if fs::metadata(&path).is_err() {
                continue;
            }
            for (fid, block) in parse_md_blocks(&read_text(&path)) {
                let replace = content
                    .get(&fid)
                    .is_none_or(|existing| block.fields.len() > existing.fields.len());
                if replace {
                    let _ = content.insert(fid, block);
                }
            }
        }
        let run_id = session_dir
            .file_name()
            .map_or_else(String::new, |name| name.to_string_lossy().into_owned());
        let period = period_of(cutoff, "", Some(mtime));
        for (fid, result) in tally.iter() {
            let crec = content.get(fid).cloned().unwrap_or_default();
            let field = |key: &str| crec.fields.get(key).cloned().unwrap_or_default();
            let reviewers = field("reviewer(s)");
            let title = [
                crec.title.clone(),
                cap_chars(&field("concern"), 120),
                fid.clone(),
            ]
            .into_iter()
            .find(|candidate| !candidate.is_empty())
            .unwrap_or_default();
            let fallback_text = if reviewers.is_empty() {
                fid.clone()
            } else {
                reviewers.clone()
            };
            let concern = {
                let value = field("concern");
                if value.is_empty() {
                    fallback_text
                } else {
                    value
                }
            };
            let text = cap_chars(
                &format!(
                    "{title}\n{concern}\n{}\n{}",
                    field("proposed resolution"),
                    crec.raw
                ),
                2000,
            );
            records.push(Record {
                skill: "design",
                source: "in_progress",
                run_id: run_id.clone(),
                finding_id: fid.clone(),
                phase: "plan-review".to_owned(),
                outcome: result.clone(),
                is_oos_id: fid.starts_with("OOS"),
                severity: field("severity").to_lowercase(),
                body_severity: String::new(),
                scope: String::new(),
                is_dynamic: is_dynamic(&reviewers),
                v_severities: Vec::new(),
                period,
                text,
                tags: Vec::new(),
            });
        }
    }
    records
}

struct ExtractionInputs<'a> {
    log_root: &'a Path,
    sessions_dir: &'a Path,
    include_in_progress: bool,
    cutoff: Option<PyTimestamp>,
    inprogress_min: Option<f64>,
    since_version: Option<(u64, u64, u64)>,
    post_only_tags: bool,
}

fn extract(inputs: &ExtractionInputs<'_>) -> Vec<Record> {
    let mut records = extract_implement(
        &inputs.log_root.join("implement"),
        inputs.cutoff,
        inputs.since_version,
    );
    records.extend(extract_design(
        &inputs.log_root.join("design"),
        inputs.cutoff,
        inputs.since_version,
    ));
    if inputs.include_in_progress && inputs.sessions_dir.is_dir() {
        records.extend(extract_in_progress(
            inputs.sessions_dir,
            inputs.cutoff,
            inputs.inprogress_min,
        ));
    }
    for record in &mut records {
        if inputs.post_only_tags && record.period != "post" {
            record.tags = Vec::new();
        } else {
            record.tags = tags_of(&record.text);
        }
    }
    records
}

// --------------------------------------------------------------------------
// implement false-negative rows
// --------------------------------------------------------------------------

struct FnRow {
    run_id: String,
    voting_result: String,
    body_severity: String,
    period: &'static str,
}

fn impl_fn_rows_from_run(
    run_dir: &Path,
    tsv_paths: &[PathBuf],
    cutoff: Option<PyTimestamp>,
    since_version: Option<(u64, u64, u64)>,
) -> Vec<FnRow> {
    let context = run_context(run_dir, cutoff, since_version);
    let jsonl_records: Vec<Map<String, Value>> = impl_jsonl_records_by_round(run_dir)
        .into_iter()
        .flat_map(|(_round, records)| records)
        .collect();
    let by_token = records_by_round_and_token(&jsonl_records);
    let multi_round = run_has_multiple_rounds(run_dir);
    let allow_unscoped = !multi_round && round_local_jsonl_paths(run_dir).is_empty();
    let mut rows = Vec::new();
    for tsv in tsv_paths {
        let round_num = round_from_path(tsv);
        for (fid, trow) in parse_impl_tsv(&read_text(tsv)).iter() {
            let verdict = trow.voting_result.trim().to_lowercase();
            let keep_id = fid.starts_with("FINDING") || fid.starts_with("REJ");
            if !keep_id || scope_is_oos(&trow.scope, fid) {
                continue;
            }
            if !matches!(verdict.as_str(), "accepted" | "neutral" | "rejected") {
                continue;
            }
            let matched = lookup_jsonl_record(&by_token, &round_num, fid, allow_unscoped);
            let json_body_severity = match matched {
                JsonlLookup::Ambiguous => continue,
                JsonlLookup::Missing => String::new(),
                JsonlLookup::One(record) => record
                    .get("body_severity")
                    .filter(|value| py_truthy(value))
                    .map(|value| py_str(value).trim().to_owned())
                    .unwrap_or_default(),
            };
            let body_severity = if json_body_severity.is_empty() {
                trow.body_severity.clone()
            } else {
                json_body_severity
            };
            rows.push(FnRow {
                run_id: context.run_id.clone(),
                voting_result: verdict,
                body_severity,
                period: context.period,
            });
        }
    }
    rows
}

fn build_impl_fn_rows(
    log_root: &Path,
    cutoff: Option<PyTimestamp>,
    since_version: Option<(u64, u64, u64)>,
) -> Vec<FnRow> {
    let corpus = RunLogCorpus::new(log_root.join("implement"));
    let tsvs_by_run = implement_round_tsvs(&corpus);
    let mut rows = Vec::new();
    for run_dir in corpus.safe_child_run_directories() {
        let tsv_paths = canonical_run_key(&run_dir)
            .and_then(|key| tsvs_by_run.get(&key).cloned())
            .unwrap_or_default();
        rows.extend(impl_fn_rows_from_run(
            &run_dir,
            &tsv_paths,
            cutoff,
            since_version,
        ));
    }
    rows
}

// --------------------------------------------------------------------------
// assessment and ship-outcome coverage
// --------------------------------------------------------------------------

struct AssessmentRow {
    run_id: String,
    larch_version: String,
    started_at: String,
    has_artifact: bool,
    assessment_kind: String,
}

struct OutcomeRow {
    classification: &'static str,
    outcome: String,
    reason: String,
}

fn started_before_cutoff(cutoff: PyTimestamp, started_raw: &str) -> bool {
    let Some(mut started) = parse_cutoff_text(started_raw) else {
        return true;
    };
    if cutoff.is_aware() && !started.is_aware() {
        started = started.promoted_to_utc();
    }
    started.utc_key() < cutoff.utc_key()
}

fn enumerate_design_run_dirs(
    design_root: &Path,
    cutoff: Option<PyTimestamp>,
    since_version: Option<(u64, u64, u64)>,
) -> Vec<(PathBuf, String, String)> {
    let mut run_dirs = Vec::new();
    for run_dir in RunLogCorpus::new(design_root).safe_child_run_directories() {
        let started_at = manifest_started(&run_dir);
        let larch_version = manifest_only_larch_version(&run_dir);
        if let Some(since) = since_version {
            let keep =
                parse_larch_version_tuple(&larch_version).is_some_and(|parsed| parsed >= since);
            if !keep {
                continue;
            }
        } else if let Some(cutoff) = cutoff
            && (started_at.is_empty() || started_before_cutoff(cutoff, &started_at))
        {
            continue;
        }
        run_dirs.push((run_dir, started_at, larch_version));
    }
    run_dirs
}

fn collect_arch_assessment_coverage(
    design_root: &Path,
    cutoff: Option<PyTimestamp>,
    since_version: Option<(u64, u64, u64)>,
    kind: AssessmentKind,
) -> Vec<AssessmentRow> {
    let violation_kind = match kind {
        AssessmentKind::Guidelines => "deviation",
        AssessmentKind::Invariants => "violation",
    };
    let mut coverage = Vec::new();
    for (run_dir, started_at, larch_version) in
        enumerate_design_run_dirs(design_root, cutoff, since_version)
    {
        let path = run_dir.join(kind.design_assessment_filename());
        let mut has_artifact = false;
        let mut assessment_kind = "missing";
        if fs::symlink_metadata(&path).is_ok() {
            let is_symlink =
                fs::symlink_metadata(&path).is_ok_and(|metadata| metadata.file_type().is_symlink());
            let regular_file = !is_symlink && path.is_file();
            let body = if regular_file {
                read_text(&path)
            } else {
                String::new()
            };
            if regular_file && !body.trim().is_empty() {
                has_artifact = true;
                assessment_kind = if body.trim_end_matches('\n') == kind.clean_presentation_note() {
                    "clean"
                } else {
                    violation_kind
                };
            }
        }
        coverage.push(AssessmentRow {
            run_id: run_dir
                .file_name()
                .map_or_else(String::new, |name| name.to_string_lossy().into_owned()),
            larch_version,
            started_at,
            has_artifact,
            assessment_kind: assessment_kind.to_owned(),
        });
    }
    coverage
}

fn enumerate_implement_run_dirs(
    implement_root: &Path,
    cutoff: Option<PyTimestamp>,
    since_version: Option<(u64, u64, u64)>,
) -> Vec<(PathBuf, Map<String, Value>)> {
    let mut run_dirs = Vec::new();
    for run_dir in RunLogCorpus::new(implement_root).safe_child_run_directories() {
        let raw = {
            let text = read_text(&run_dir.join("manifest.json"));
            if text.is_empty() {
                "{}".to_owned()
            } else {
                text
            }
        };
        let Ok(parsed) = serde_json::from_str::<Value>(&raw) else {
            continue;
        };
        let Value::Object(manifest) = parsed else {
            continue;
        };
        let larch_version = manifest
            .get("larch_version")
            .and_then(Value::as_str)
            .unwrap_or_default();
        if let Some(since) = since_version {
            let keep =
                parse_larch_version_tuple(larch_version).is_some_and(|parsed| parsed >= since);
            if !keep {
                continue;
            }
        } else if let Some(cutoff) = cutoff {
            let started_raw = manifest.get("started_at").map(py_str).unwrap_or_default();
            if parse_cutoff_text(&started_raw).is_none()
                || started_before_cutoff(cutoff, &started_raw)
            {
                continue;
            }
        }
        run_dirs.push((run_dir, manifest));
    }
    run_dirs
}

fn implement_step8_reachable(run_dir: &Path, manifest: &Map<String, Value>) -> bool {
    let value = Value::Object(manifest.clone());
    let context = ReachabilityContext::new(run_dir, &value);
    condition_reached(&context, "step8").unwrap_or(false)
}

fn string_or_empty(value: Option<&Value>) -> String {
    match value {
        Some(Value::String(text)) => text.clone(),
        _ => String::new(),
    }
}

fn valid_guideline_outcome(data: &Value) -> bool {
    let Value::Object(record) = data else {
        return false;
    };
    let required = [
        "schema_version",
        "phase",
        "step",
        "outcome",
        "reason",
        "detail",
        "guidelines_status",
        "head_sha",
        "base_ref",
    ];
    if !required.iter().all(|key| record.contains_key(*key)) {
        return false;
    }
    let field = |key: &str| str_if_truthy(record, key);
    field("schema_version") == "1"
        && matches!(field("outcome").as_str(), "pinned" | "clean" | "dropped")
        && matches!(
            field("guidelines_status").as_str(),
            "present" | "absent" | "invalid"
        )
        && AssessmentKind::Guidelines
            .ship_reason_tokens()
            .contains(&field("reason").as_str())
        && !field("head_sha").trim().is_empty()
        && !field("base_ref").trim().is_empty()
}

fn valid_invariant_outcome(data: &Value) -> bool {
    validate_ship_outcome_record(data, AssessmentKind::Invariants).is_none()
}

fn collect_implement_outcome_coverage(
    implement_root: &Path,
    cutoff: Option<PyTimestamp>,
    since_version: Option<(u64, u64, u64)>,
    kind: AssessmentKind,
) -> Vec<OutcomeRow> {
    let mut coverage = Vec::new();
    for (run_dir, manifest) in enumerate_implement_run_dirs(implement_root, cutoff, since_version) {
        let version = string_or_empty(manifest.get("larch_version"));
        let version_tuple = parse_larch_version_tuple(&version);
        let step8 = implement_step8_reachable(&run_dir, &manifest);
        let at_cutover =
            version_tuple.is_some_and(|version| version >= SHIP_OUTCOME_CUTOVER_VERSION);
        let mut classification = if step8 && at_cutover {
            "missing-current"
        } else {
            "missing-legacy"
        };
        let mut outcome = String::new();
        let mut reason = String::new();
        let artifact = run_dir.join(kind.ship_outcome_sidecar_filename());
        if fs::symlink_metadata(&artifact).is_ok() {
            let raw = {
                let text = read_text(&artifact);
                if text.is_empty() {
                    "{}".to_owned()
                } else {
                    text
                }
            };
            if let Ok(data) = serde_json::from_str::<Value>(&raw) {
                let valid = match kind {
                    AssessmentKind::Guidelines => valid_guideline_outcome(&data),
                    AssessmentKind::Invariants => valid_invariant_outcome(&data),
                };
                if valid {
                    classification = "valid";
                    if let Value::Object(record) = &data {
                        outcome = str_if_truthy(record, "outcome");
                        reason = str_if_truthy(record, "reason");
                    }
                }
            }
        }
        coverage.push(OutcomeRow {
            classification,
            outcome,
            reason,
        });
    }
    coverage
}

// --------------------------------------------------------------------------
// aggregation helpers
// --------------------------------------------------------------------------

fn threeway(rows: &[&Record]) -> (usize, usize, usize, usize) {
    let total = rows.len();
    let accepted = rows.iter().filter(|row| row.outcome == "accepted").count();
    let oos = rows
        .iter()
        .filter(|row| row.outcome == "out_of_scope")
        .count();
    let rejected = rows
        .iter()
        .filter(|row| matches!(row.outcome.as_str(), "rejected" | "exonerated" | "neutral"))
        .count();
    (total, accepted, oos, rejected)
}

fn acc_rate(rows: &[&Record]) -> (usize, usize, f64) {
    let total = rows.len();
    let accepted = rows.iter().filter(|row| row.outcome == "accepted").count();
    (accepted, total, pct(accepted, total))
}

fn fmt1(value: f64) -> String {
    format!("{value:.1}")
}

fn fmt0(value: f64) -> String {
    format!("{value:.0}")
}

// --------------------------------------------------------------------------
// report rendering
// --------------------------------------------------------------------------

/// Inputs for one fluff-analysis report over a prepared log root.
pub struct FluffOptions {
    /// The already-selected corpus root (explicit or synchronized).
    pub log_root: PathBuf,
    /// Session cache directory for `--include-in-progress`.
    pub sessions_dir: PathBuf,
    /// Whether to scan in-progress design session directories.
    pub include_in_progress: bool,
    /// Parsed `--cutoff` timestamp, when supplied and parseable.
    pub cutoff: Option<PyTimestamp>,
    /// Parsed `--inprogress-since` lower bound in epoch seconds.
    pub inprogress_min: Option<f64>,
    /// Parsed `--since-version` tuple.
    pub since_version: Option<(u64, u64, u64)>,
    /// Minimum findings for a semantic group to appear (already clamped >= 1).
    pub min_group: u64,
    /// Compute semantic tags only for post-period records.
    pub post_only_tags: bool,
}

/// Render the complete `/fluff-analysis` markdown report.
#[must_use]
pub fn fluff_analysis_report(options: &FluffOptions) -> String {
    let records = extract(&ExtractionInputs {
        log_root: &options.log_root,
        sessions_dir: &options.sessions_dir,
        include_in_progress: options.include_in_progress,
        cutoff: options.cutoff,
        inprogress_min: options.inprogress_min,
        since_version: options.since_version,
        post_only_tags: options.post_only_tags,
    });
    let design_root = options.log_root.join("design");
    let implement_root = options.log_root.join("implement");
    let i_fn_rows = build_impl_fn_rows(&options.log_root, options.cutoff, options.since_version);
    let assessment_coverage = collect_arch_assessment_coverage(
        &design_root,
        options.cutoff,
        options.since_version,
        AssessmentKind::Guidelines,
    );
    let invariant_assessment_coverage = collect_arch_assessment_coverage(
        &design_root,
        options.cutoff,
        options.since_version,
        AssessmentKind::Invariants,
    );
    let guideline_outcome_coverage = collect_implement_outcome_coverage(
        &implement_root,
        options.cutoff,
        options.since_version,
        AssessmentKind::Guidelines,
    );
    let invariant_outcome_coverage = collect_implement_outcome_coverage(
        &implement_root,
        options.cutoff,
        options.since_version,
        AssessmentKind::Invariants,
    );
    render(&RenderInputs {
        records: &records,
        cutoff: options.cutoff,
        min_group: options.min_group,
        since_version: options.since_version,
        assessment_coverage: &assessment_coverage,
        guideline_outcome_coverage: &guideline_outcome_coverage,
        invariant_assessment_coverage: &invariant_assessment_coverage,
        invariant_outcome_coverage: &invariant_outcome_coverage,
        i_fn_rows: &i_fn_rows,
    })
}

struct RenderInputs<'a> {
    records: &'a [Record],
    cutoff: Option<PyTimestamp>,
    min_group: u64,
    since_version: Option<(u64, u64, u64)>,
    assessment_coverage: &'a [AssessmentRow],
    guideline_outcome_coverage: &'a [OutcomeRow],
    invariant_assessment_coverage: &'a [AssessmentRow],
    invariant_outcome_coverage: &'a [OutcomeRow],
    i_fn_rows: &'a [FnRow],
}

#[allow(clippy::too_many_lines)] // Exact section order stays contiguous for parity review.
fn render(inputs: &RenderInputs<'_>) -> String {
    let design: Vec<&Record> = inputs
        .records
        .iter()
        .filter(|record| record.skill == "design")
        .collect();
    let impl_records: Vec<&Record> = inputs
        .records
        .iter()
        .filter(|record| record.skill == "implement")
        .collect();
    let d_inscope: Vec<&Record> = design
        .iter()
        .copied()
        .filter(|record| !record.is_oos_id)
        .collect();
    let d_fn_inscope: Vec<&Record> = d_inscope
        .iter()
        .copied()
        .filter(|record| {
            !scope_is_oos(&record.scope, &record.finding_id)
                && matches!(record.outcome.as_str(), "accepted" | "neutral" | "rejected")
        })
        .collect();
    let i_all: Vec<&Record> = impl_records
        .iter()
        .copied()
        .filter(|record| record.phase == "code-review")
        .collect();

    let mut out: Vec<String> = Vec::new();
    out.push("# Review Fluff Analysis".to_owned());
    out.push(String::new());
    out.push(
        "Characterizes review suggestions that are *not accepted* or *accepted-but-low-value*, \
from the synchronized larch run-log cache. Counts are directional (keyword tags are approximate; \
severity cuts are exact). See `skills/shared/review-acceptance-rubric.md` for the \
necessity gate this report is designed to inform."
            .to_owned(),
    );
    out.push(String::new());
    out.push(format!(
        "- Records: **{}** total (implement code-review **{}**, design in-scope **{}**)",
        inputs.records.len(),
        i_all.len(),
        d_inscope.len()
    ));
    let mut sources: BTreeMap<&str, usize> = BTreeMap::new();
    for record in inputs.records {
        *sources.entry(record.source).or_insert(0) += 1;
    }
    out.push(format!(
        "- Sources: {}",
        sources
            .iter()
            .map(|(source, count)| format!("{source}={count}"))
            .collect::<Vec<_>>()
            .join(", ")
    ));
    if i_all.is_empty() && d_inscope.is_empty() {
        out.extend(section_assessment_coverage(
            inputs.invariant_assessment_coverage,
            "Invariant assessment coverage",
        ));
        out.extend(section_assessment_coverage(
            inputs.assessment_coverage,
            "Guideline assessment coverage",
        ));
        out.extend(section_outcome_coverage(
            inputs.invariant_outcome_coverage,
            "Implement invariant outcome coverage",
        ));
        out.extend(section_outcome_coverage(
            inputs.guideline_outcome_coverage,
            "Implement guideline outcome coverage",
        ));
        out.extend(section_false_negatives(
            inputs.i_fn_rows,
            &d_fn_inscope,
            inputs.cutoff.is_some() || inputs.since_version.is_some(),
        ));
        out.push(String::new());
        out.push("> No review findings found under the log root. Nothing to analyze.".to_owned());
        return format!("{}\n", out.join("\n"));
    }

    out.extend(section_baselines(&i_all, &d_inscope, &design));
    out.extend(section_assessment_coverage(
        inputs.invariant_assessment_coverage,
        "Invariant assessment coverage",
    ));
    out.extend(section_assessment_coverage(
        inputs.assessment_coverage,
        "Guideline assessment coverage",
    ));
    out.extend(section_outcome_coverage(
        inputs.invariant_outcome_coverage,
        "Implement invariant outcome coverage",
    ));
    out.extend(section_outcome_coverage(
        inputs.guideline_outcome_coverage,
        "Implement guideline outcome coverage",
    ));
    out.extend(section_groups(&i_all, &d_inscope, inputs.min_group));
    out.extend(section_testing(&i_all));
    out.extend(section_severity(&i_all, &d_inscope));
    out.extend(section_lanes(&i_all, &d_inscope));
    out.extend(section_accepted_low_value(&i_all, &d_inscope));
    out.extend(section_false_negatives(
        inputs.i_fn_rows,
        &d_fn_inscope,
        inputs.cutoff.is_some() || inputs.since_version.is_some(),
    ));
    if inputs.cutoff.is_some() || inputs.since_version.is_some() {
        out.extend(section_prepost(
            &i_all,
            &d_inscope,
            inputs.since_version.is_some(),
        ));
    }
    out.extend(section_recommendations(&i_all, inputs.min_group));
    format!("{}\n", out.join("\n"))
}

fn section_baselines(i_all: &[&Record], d_inscope: &[&Record], design: &[&Record]) -> Vec<String> {
    let mut out = vec![String::new(), "## Baselines".to_owned(), String::new()];
    let (total, accepted, oos, rejected) = threeway(i_all);
    out.push("| corpus | n | accepted | OOS | rejected |".to_owned());
    out.push("|---|--:|--:|--:|--:|".to_owned());
    out.push(format!(
        "| implement code-review | {total} | {}% | {}% | {}% |",
        fmt1(pct(accepted, total)),
        fmt1(pct(oos, total)),
        fmt1(pct(rejected, total))
    ));
    let (_d_acc, d_total, d_rate) = acc_rate(d_inscope);
    out.push(format!(
        "| design in-scope | {d_total} | {}% | — | {}% |",
        fmt1(d_rate),
        fmt1(100.0 - d_rate)
    ));
    let d_oos: Vec<&Record> = design
        .iter()
        .copied()
        .filter(|record| record.is_oos_id)
        .collect();
    if !d_oos.is_empty() {
        let (_o_acc, o_total, o_rate) = acc_rate(&d_oos);
        out.push(format!(
            "| design OOS proposals | {o_total} | {}% file-worthy | | |",
            fmt1(o_rate)
        ));
    }
    out
}

fn section_assessment_coverage(coverage: &[AssessmentRow], title: &str) -> Vec<String> {
    if coverage.is_empty() {
        return Vec::new();
    }
    let total = coverage.len();
    let with_artifact = coverage.iter().filter(|row| row.has_artifact).count();
    let clean = coverage
        .iter()
        .filter(|row| row.assessment_kind == "clean")
        .count();
    let deviation = coverage
        .iter()
        .filter(|row| row.assessment_kind == "deviation")
        .count();
    let mut out = vec![String::new(), format!("## {title}"), String::new()];
    out.push(
        "| runs scanned | runs with assessment artifact | clean count | deviation count |"
            .to_owned(),
    );
    out.push("|--:|--:|--:|--:|".to_owned());
    out.push(format!(
        "| {total} | {with_artifact} | {clean} | {deviation} |"
    ));
    out.push(String::new());
    out.push("| run | started_at | larch_version | assessment_kind |".to_owned());
    out.push("|---|---|---|---|".to_owned());
    for row in coverage {
        out.push(format!(
            "| {} | {} | {} | {} |",
            row.run_id, row.started_at, row.larch_version, row.assessment_kind
        ));
    }
    out
}

fn section_outcome_coverage(coverage: &[OutcomeRow], title: &str) -> Vec<String> {
    if coverage.is_empty() {
        return Vec::new();
    }
    let total = coverage.len();
    let valid_rows: Vec<&OutcomeRow> = coverage
        .iter()
        .filter(|row| row.classification == "valid")
        .collect();
    let missing_current = coverage
        .iter()
        .filter(|row| row.classification == "missing-current")
        .count();
    let missing_legacy = coverage
        .iter()
        .filter(|row| row.classification == "missing-legacy")
        .count();
    let pinned = valid_rows
        .iter()
        .filter(|row| row.outcome == "pinned")
        .count();
    let clean = valid_rows
        .iter()
        .filter(|row| row.outcome == "clean")
        .count();
    let dropped = valid_rows
        .iter()
        .filter(|row| row.outcome == "dropped")
        .count();
    let mut reasons: BTreeMap<&str, usize> = BTreeMap::new();
    for row in valid_rows.iter().filter(|row| row.outcome == "dropped") {
        *reasons.entry(row.reason.as_str()).or_insert(0) += 1;
    }
    let mut out = vec![String::new(), format!("## {title}"), String::new()];
    out.push(
        "| runs scanned | valid | missing-current | missing-legacy | pinned | clean | dropped | drop rate |"
            .to_owned(),
    );
    out.push("|--:|--:|--:|--:|--:|--:|--:|--:|".to_owned());
    out.push(format!(
        "| {total} | {} | {missing_current} | {missing_legacy} | {pinned} | {clean} | {dropped} | {}% |",
        valid_rows.len(),
        fmt1(pct(dropped, valid_rows.len()))
    ));
    if !reasons.is_empty() {
        out.push(String::new());
        out.push("| dropped reason | count |".to_owned());
        out.push("|---|--:|".to_owned());
        for (reason, count) in &reasons {
            out.push(format!("| {reason} | {count} |"));
        }
    }
    out
}

type GroupRow = (&'static str, usize, f64, f64, f64);

fn group_rows(rows: &[&Record], min_group: u64, three_way: bool) -> Vec<GroupRow> {
    let mut table: Vec<GroupRow> = Vec::new();
    for (tag, _pattern) in TAGS.iter() {
        let sub: Vec<&Record> = rows
            .iter()
            .copied()
            .filter(|row| row.tags.contains(tag))
            .collect();
        if (sub.len() as u64) < min_group {
            continue;
        }
        if three_way {
            let (total, accepted, oos, rejected) = threeway(&sub);
            table.push((
                tag,
                total,
                pct(accepted, total),
                pct(oos, total),
                pct(rejected, total),
            ));
        } else {
            let (_accepted, total, rate) = acc_rate(&sub);
            table.push((tag, total, rate, 0.0, 0.0));
        }
    }
    table.sort_by(|left, right| left.2.total_cmp(&right.2));
    table
}

fn section_groups(i_all: &[&Record], d_inscope: &[&Record], min_group: u64) -> Vec<String> {
    let mut out = vec![
        String::new(),
        "## Q1 — Low-acceptance semantic groups".to_owned(),
        String::new(),
        "Multi-label tags (a finding may carry several). Groups below the corpus baseline are \
fluff-prone; distinguish **reject-heavy** (down-vote / suppress) from **OOS-heavy** \
(valid but defer)."
            .to_owned(),
        String::new(),
    ];
    let rows = group_rows(i_all, min_group, true);
    if !rows.is_empty() {
        out.push("### implement code-review (sorted by acceptance, ascending)".to_owned());
        out.push(String::new());
        out.push("| group | n | acc% | oos% | rej% |".to_owned());
        out.push("|---|--:|--:|--:|--:|".to_owned());
        for (tag, count, accepted, oos, rejected) in rows {
            out.push(format!(
                "| {tag} | {count} | {} | {} | {} |",
                fmt1(accepted),
                fmt1(oos),
                fmt1(rejected)
            ));
        }
    }
    let design_rows = group_rows(d_inscope, min_group, false);
    if !design_rows.is_empty() {
        out.push(String::new());
        out.push("### design in-scope (sorted by acceptance, ascending)".to_owned());
        out.push(String::new());
        out.push("| group | n | acc% |".to_owned());
        out.push("|---|--:|--:|".to_owned());
        for (tag, count, accepted, _oos, _rejected) in design_rows {
            out.push(format!("| {tag} | {count} | {} |", fmt1(accepted)));
        }
    }
    out
}

fn section_testing(i_all: &[&Record]) -> Vec<String> {
    let test: Vec<&Record> = i_all
        .iter()
        .copied()
        .filter(|row| row.tags.contains(&"theme:testing"))
        .collect();
    if test.is_empty() {
        return Vec::new();
    }
    let mut out = vec![
        String::new(),
        "## Q2 — Testing".to_owned(),
        String::new(),
        "Testing is typically the largest waste bucket by volume. The discriminator is \
necessity (severity), not size:"
            .to_owned(),
        String::new(),
    ];
    out.push(format!(
        "- testing findings: **{}** ({}% of implement code-review)",
        test.len(),
        fmt1(pct(test.len(), i_all.len()))
    ));
    out.push(String::new());
    out.push("| testing finding | n | acc% | oos% | rej% |".to_owned());
    out.push("|---|--:|--:|--:|--:|".to_owned());
    for severity in ["important", "latent", "nit", "(none)"] {
        let sub: Vec<&Record> = test
            .iter()
            .copied()
            .filter(|row| effective_severity(row) == severity)
            .collect();
        if sub.is_empty() {
            continue;
        }
        let (total, accepted, oos, rejected) = threeway(&sub);
        out.push(format!(
            "| testing+{severity} | {total} | {} | {} | {} |",
            fmt1(pct(accepted, total)),
            fmt1(pct(oos, total)),
            fmt1(pct(rejected, total))
        ));
    }
    out
}

const fn effective_severity(record: &Record) -> &str {
    if record.severity.is_empty() {
        "(none)"
    } else {
        record.severity.as_str()
    }
}

fn section_severity(i_all: &[&Record], d_inscope: &[&Record]) -> Vec<String> {
    let mut out = vec![
        String::new(),
        "## Q3 — Severity / quality / uncertain".to_owned(),
        String::new(),
    ];
    let has_impl_tiers = i_all
        .iter()
        .any(|row| matches!(effective_severity(row), "important" | "nit" | "latent"));
    if has_impl_tiers {
        out.push("**implement — reviewer-authored body severity → outcome**".to_owned());
        out.push(String::new());
        out.push("| severity | n | acc% | oos% | rej% |".to_owned());
        out.push("|---|--:|--:|--:|--:|".to_owned());
        for severity in SEV_BODY.iter().copied().chain(["(none)"]) {
            let sub: Vec<&Record> = i_all
                .iter()
                .copied()
                .filter(|row| effective_severity(row) == severity)
                .collect();
            if sub.is_empty() {
                continue;
            }
            let (total, accepted, oos, rejected) = threeway(&sub);
            out.push(format!(
                "| {severity} | {total} | {} | {} | {} |",
                fmt1(pct(accepted, total)),
                fmt1(pct(oos, total)),
                fmt1(pct(rejected, total))
            ));
        }
    }
    let modal_of = |record: &Record| {
        let value = modal(&record.v_severities);
        if value.is_empty() {
            "(none)".to_owned()
        } else {
            value
        }
    };
    let has_design_tiers = d_inscope
        .iter()
        .any(|row| matches!(modal_of(row).as_str(), "important" | "latent" | "nit"));
    if has_design_tiers {
        out.push(String::new());
        out.push("**design in-scope — modal voter severity → accept rate**".to_owned());
        out.push(String::new());
        out.push("| voter severity | n | acc% |".to_owned());
        out.push("|---|--:|--:|".to_owned());
        for severity in [
            "blocker",
            "critical",
            "important",
            "latent",
            "nit",
            "(none)",
        ] {
            let sub: Vec<&Record> = d_inscope
                .iter()
                .copied()
                .filter(|row| modal_of(row) == severity)
                .collect();
            if sub.is_empty() {
                continue;
            }
            let (_accepted, total, rate) = acc_rate(&sub);
            out.push(format!("| {severity} | {total} | {} |", fmt1(rate)));
        }
    }
    out
}

fn section_lanes(i_all: &[&Record], d_inscope: &[&Record]) -> Vec<String> {
    let mut out = vec![String::new(), "## Reviewer lane".to_owned(), String::new()];
    let mut wrote = false;
    for (label, rows) in [("implement", i_all), ("design in-scope", d_inscope)] {
        let mut lines = Vec::new();
        for dynamic in [true, false] {
            let sub: Vec<&Record> = rows
                .iter()
                .copied()
                .filter(|row| row.is_dynamic == dynamic)
                .collect();
            if sub.len() < 15 {
                continue;
            }
            let (total, accepted, oos, rejected) = threeway(&sub);
            let name = if dynamic { "dynamic" } else { "base" };
            lines.push(format!(
                "  - {label} {name}: n={total} acc={}% oos={}% rej={}%",
                fmt1(pct(accepted, total)),
                fmt1(pct(oos, total)),
                fmt1(pct(rejected, total))
            ));
        }
        if !lines.is_empty() {
            wrote = true;
            out.extend(lines);
        }
    }
    if !wrote {
        out.push("_(insufficient lane-tagged volume)_".to_owned());
    }
    out
}

fn section_accepted_low_value(i_all: &[&Record], d_inscope: &[&Record]) -> Vec<String> {
    let mut out = vec![
        String::new(),
        "## Accepted-but-low-value proxy".to_owned(),
        String::new(),
    ];
    let acc_impl: Vec<&Record> = i_all
        .iter()
        .copied()
        .filter(|row| row.outcome == "accepted")
        .collect();
    let low = acc_impl
        .iter()
        .filter(|row| matches!(row.severity.as_str(), "nit" | "latent"))
        .count();
    if !acc_impl.is_empty() {
        out.push(format!(
            "- implement: **{}%** of accepted findings were reviewer-severity nit/latent ({low}/{})",
            fmt1(pct(low, acc_impl.len())),
            acc_impl.len()
        ));
    }
    let acc_design: Vec<&Record> = d_inscope
        .iter()
        .copied()
        .filter(|row| row.outcome == "accepted")
        .collect();
    let low_design = acc_design
        .iter()
        .filter(|row| matches!(modal(&row.v_severities).as_str(), "nit" | "latent"))
        .count();
    if !acc_design.is_empty() {
        out.push(format!(
            "- design: **{}%** of accepted in-scope were modal-voter nit/latent ({low_design}/{})",
            fmt1(pct(low_design, acc_design.len())),
            acc_design.len()
        ));
    }
    out
}

#[allow(clippy::too_many_lines)] // Exact pre/post block order stays contiguous for parity review.
fn section_prepost(i_all: &[&Record], d_inscope: &[&Record], by_version: bool) -> Vec<String> {
    let header = if by_version {
        "## Pre/post comparison"
    } else {
        "## Pre/post cutoff"
    };
    let mut out = vec![String::new(), header.to_owned(), String::new()];
    let unknown = i_all
        .iter()
        .chain(d_inscope.iter())
        .filter(|row| row.period == "unknown")
        .count();
    if by_version && unknown > 0 {
        out.push(format!("- unknown-version skipped: {unknown}"));
        out.push(String::new());
    }
    for (label, rows, three) in [
        ("implement code-review", i_all, true),
        ("design in-scope", d_inscope, false),
    ] {
        out.push(format!("**{label}**"));
        for period in ["pre", "post"] {
            let sub: Vec<&Record> = rows
                .iter()
                .copied()
                .filter(|row| row.period == period)
                .collect();
            if sub.is_empty() {
                continue;
            }
            let runs = sub
                .iter()
                .map(|row| row.run_id.as_str())
                .collect::<BTreeSet<_>>()
                .len();
            if three {
                let (total, accepted, oos, rejected) = threeway(&sub);
                out.push(format!(
                    "- {period}: n={total} ({runs} runs, {}/run) acc={}% oos={}% rej={}%",
                    fmt1(ratio(total, runs)),
                    fmt1(pct(accepted, total)),
                    fmt1(pct(oos, total)),
                    fmt1(pct(rejected, total))
                ));
            } else {
                let (_accepted, total, rate) = acc_rate(&sub);
                out.push(format!(
                    "- {period}: n={total} ({runs} runs, {}/run) acc={}%",
                    fmt1(ratio(total, runs)),
                    fmt1(rate)
                ));
            }
        }
        out.push(String::new());
    }
    if !i_all.is_empty() {
        out.push("**implement code-review severity tiers**".to_owned());
        out.push(String::new());
        out.push("| period | severity | n | acc% | oos% | rej% |".to_owned());
        out.push("|---|---|--:|--:|--:|--:|".to_owned());
        for period in ["pre", "post"] {
            let per_rows: Vec<&Record> = i_all
                .iter()
                .copied()
                .filter(|row| row.period == period)
                .collect();
            if per_rows.is_empty() {
                continue;
            }
            for severity in ["important", "latent", "nit", "(none)"] {
                let sub: Vec<&Record> = per_rows
                    .iter()
                    .copied()
                    .filter(|row| normalize_severity(&row.severity) == severity)
                    .collect();
                let (total, accepted, oos, rejected) = threeway(&sub);
                out.push(format!(
                    "| {period} | {severity} | {total} | {} | {} | {} |",
                    fmt1(pct(accepted, total)),
                    fmt1(pct(oos, total)),
                    fmt1(pct(rejected, total))
                ));
            }
        }
        out.push(String::new());
        for period in ["pre", "post"] {
            let per_rows: Vec<&Record> = i_all
                .iter()
                .copied()
                .filter(|row| row.period == period)
                .collect();
            if per_rows.is_empty() {
                continue;
            }
            let accepted: Vec<&Record> = per_rows
                .iter()
                .copied()
                .filter(|row| row.outcome == "accepted")
                .collect();
            let low = accepted
                .iter()
                .filter(|row| matches!(normalize_severity(&row.severity), "nit" | "latent"))
                .count();
            out.push(format!(
                "- {period} accepted-low-value: {}% ({low}/{})",
                fmt1(pct(low, accepted.len())),
                accepted.len()
            ));
            let count_of = |tier: &str| {
                per_rows
                    .iter()
                    .filter(|row| normalize_severity(&row.severity) == tier)
                    .count()
            };
            out.push(format!(
                "- {period} tier-composition: important {}% latent {}% nit {}% (none) {}%",
                fmt1(pct(count_of("important"), per_rows.len())),
                fmt1(pct(count_of("latent"), per_rows.len())),
                fmt1(pct(count_of("nit"), per_rows.len())),
                fmt1(pct(count_of("(none)"), per_rows.len()))
            ));
        }
    }
    let d_prepost: Vec<&Record> = d_inscope
        .iter()
        .copied()
        .filter(|row| matches!(row.period, "pre" | "post"))
        .collect();
    if !d_prepost.is_empty() {
        out.push("**design in-scope voter severity tiers**".to_owned());
        out.push(String::new());
        out.push("| period | voter severity | n | acc% |".to_owned());
        out.push("|---|---|--:|--:|".to_owned());
        for period in ["pre", "post"] {
            let per_rows: Vec<&Record> = d_prepost
                .iter()
                .copied()
                .filter(|row| row.period == period)
                .collect();
            if per_rows.is_empty() {
                continue;
            }
            for severity in [
                "blocker",
                "critical",
                "important",
                "latent",
                "nit",
                "(none)",
            ] {
                let sub: Vec<&Record> = per_rows
                    .iter()
                    .copied()
                    .filter(|row| {
                        let value = modal(&row.v_severities);
                        let tier = if value.is_empty() {
                            "(none)"
                        } else {
                            value.as_str()
                        };
                        tier == severity
                    })
                    .collect();
                if sub.is_empty() {
                    continue;
                }
                let (_accepted, total, rate) = acc_rate(&sub);
                out.push(format!(
                    "| {period} | {severity} | {total} | {} |",
                    fmt1(rate)
                ));
            }
        }
        out.push(String::new());
    }
    out.push("_Small post samples are directional only._".to_owned());
    out
}

// --------------------------------------------------------------------------
// false-negative tables
// --------------------------------------------------------------------------

enum FnCorpusRow<'a> {
    Implement(&'a FnRow),
    Design(&'a Record),
}

impl FnCorpusRow<'_> {
    const fn period(&self) -> &str {
        match self {
            Self::Implement(row) => row.period,
            Self::Design(row) => row.period,
        }
    }

    fn body_severity(&self) -> &str {
        match self {
            Self::Implement(row) => &row.body_severity,
            Self::Design(row) => &row.body_severity,
        }
    }

    fn verdict(&self) -> &str {
        match self {
            Self::Implement(row) => {
                if row.voting_result.is_empty() {
                    ""
                } else {
                    &row.voting_result
                }
            }
            Self::Design(row) => &row.outcome,
        }
    }

    fn run_id(&self) -> &str {
        match self {
            Self::Implement(row) => &row.run_id,
            Self::Design(row) => &row.run_id,
        }
    }
}

type NeutralRow = (&'static str, &'static str, usize, usize, f64, usize);
type RejectRow = (&'static str, usize, usize, f64, usize);

fn fn_corpora<'a>(
    i_fn_rows: &'a [FnRow],
    d_fn_inscope: &'a [&'a Record],
) -> [(&'static str, Vec<FnCorpusRow<'a>>, &'static str); 2] {
    [
        (
            "implement false-negative",
            i_fn_rows.iter().map(FnCorpusRow::Implement).collect(),
            "implement",
        ),
        (
            "design in-scope",
            d_fn_inscope
                .iter()
                .map(|record| FnCorpusRow::Design(record))
                .collect(),
            "design",
        ),
    ]
}

fn distinct_runs(rows: &[&FnCorpusRow<'_>]) -> usize {
    rows.iter()
        .map(|row| row.run_id())
        .filter(|run_id| !run_id.is_empty())
        .collect::<BTreeSet<_>>()
        .len()
}

fn false_negative_neutral_rows(
    i_fn_rows: &[FnRow],
    d_fn_inscope: &[&Record],
    period: Option<&str>,
) -> Vec<NeutralRow> {
    let mut table = Vec::new();
    for (label, rows, corpus) in fn_corpora(i_fn_rows, d_fn_inscope) {
        let rows: Vec<&FnCorpusRow<'_>> = rows
            .iter()
            .filter(|row| period.is_none_or(|period| row.period() == period))
            .collect();
        for tier in ["important", "latent", "nit", "(none)"] {
            let sub: Vec<&FnCorpusRow<'_>> = rows
                .iter()
                .copied()
                .filter(|row| reviewer_claimed_tier(row.body_severity(), corpus) == tier)
                .collect();
            let total = sub.len();
            let neutral = sub.iter().filter(|row| row.verdict() == "neutral").count();
            let runs = distinct_runs(&sub);
            table.push((label, tier, neutral, total, pct(neutral, total), runs));
        }
    }
    table
}

fn false_negative_reject_rows(
    i_fn_rows: &[FnRow],
    d_fn_inscope: &[&Record],
    period: Option<&str>,
) -> Vec<RejectRow> {
    let mut table = Vec::new();
    for (label, rows, corpus) in fn_corpora(i_fn_rows, d_fn_inscope) {
        let important: Vec<&FnCorpusRow<'_>> = rows
            .iter()
            .filter(|row| period.is_none_or(|period| row.period() == period))
            .filter(|row| reviewer_claimed_tier(row.body_severity(), corpus) == "important")
            .collect();
        let rejected = important
            .iter()
            .filter(|row| row.verdict() == "rejected")
            .count();
        let runs = distinct_runs(&important);
        table.push((
            label,
            rejected,
            important.len(),
            pct(rejected, important.len()),
            runs,
        ));
    }
    table
}

fn append_neutral_table(out: &mut Vec<String>, rows: &[NeutralRow], period: Option<&str>) {
    if let Some(period) = period {
        out.push("| period | corpus | tier | neutral | total | rate | runs |".to_owned());
        out.push("|---|---|---|--:|--:|--:|--:|".to_owned());
        let mut wrote = false;
        for (label, tier, neutral, total, rate, runs) in rows {
            if *total == 0 {
                continue;
            }
            wrote = true;
            out.push(format!(
                "| {period} | {label} | {tier} | {neutral} | {total} | {}% | {runs} |",
                fmt1(*rate)
            ));
        }
        if !wrote {
            out.push(format!("| {period} | n/a | n/a | 0 | 0 | n/a | 0 |"));
        }
        return;
    }
    out.push("| corpus | tier | neutral | total | rate | runs |".to_owned());
    out.push("|---|---|--:|--:|--:|--:|".to_owned());
    let mut wrote = false;
    for (label, tier, neutral, total, rate, runs) in rows {
        if *total == 0 {
            continue;
        }
        wrote = true;
        out.push(format!(
            "| {label} | {tier} | {neutral} | {total} | {}% | {runs} |",
            fmt1(*rate)
        ));
    }
    if !wrote {
        out.push("| n/a | n/a | 0 | 0 | n/a | 0 |".to_owned());
    }
}

fn append_reject_table(out: &mut Vec<String>, rows: &[RejectRow], period: Option<&str>) {
    if let Some(period) = period {
        out.push(
            "| period | corpus | rejected | reviewer-claimed-important | rate | runs |".to_owned(),
        );
        out.push("|---|---|--:|--:|--:|--:|".to_owned());
        let mut wrote = false;
        for (label, rejected, total, rate, runs) in rows {
            if *total == 0 {
                continue;
            }
            wrote = true;
            out.push(format!(
                "| {period} | {label} | {rejected} | {total} | {}% | {runs} |",
                fmt1(*rate)
            ));
        }
        if !wrote {
            out.push(format!("| {period} | n/a | 0 | 0 | n/a | 0 |"));
        }
        return;
    }
    out.push("| corpus | rejected | reviewer-claimed-important | rate | runs |".to_owned());
    out.push("|---|--:|--:|--:|--:|".to_owned());
    let mut wrote = false;
    for (label, rejected, total, rate, runs) in rows {
        if *total == 0 {
            continue;
        }
        wrote = true;
        out.push(format!(
            "| {label} | {rejected} | {total} | {}% | {runs} |",
            fmt1(*rate)
        ));
    }
    if !wrote {
        out.push("| n/a | 0 | 0 | n/a | 0 |".to_owned());
    }
}

fn section_false_negatives(
    i_fn_rows: &[FnRow],
    d_fn_inscope: &[&Record],
    with_prepost: bool,
) -> Vec<String> {
    let mut out = vec![
        String::new(),
        "## False-negative / under-acceptance metrics".to_owned(),
        String::new(),
        "Diagnostic-only rates over TSV panel verdicts and reviewer-claimed `body_severity` tiers."
            .to_owned(),
        String::new(),
        "### Neutral-rate by severity tier".to_owned(),
        String::new(),
    ];
    append_neutral_table(
        &mut out,
        &false_negative_neutral_rows(i_fn_rows, d_fn_inscope, None),
        None,
    );
    out.push(String::new());
    out.push("### Important-reject-rate".to_owned());
    out.push(String::new());
    append_reject_table(
        &mut out,
        &false_negative_reject_rows(i_fn_rows, d_fn_inscope, None),
        None,
    );
    if with_prepost {
        out.push(String::new());
        out.push("### Pre/post false-negative neutral-rate".to_owned());
        out.push(String::new());
        for (index, period) in ["pre", "post"].into_iter().enumerate() {
            if index > 0 {
                out.push(String::new());
            }
            append_neutral_table(
                &mut out,
                &false_negative_neutral_rows(i_fn_rows, d_fn_inscope, Some(period)),
                Some(period),
            );
        }
        out.push(String::new());
        out.push("### Pre/post false-negative important-reject-rate".to_owned());
        out.push(String::new());
        for (index, period) in ["pre", "post"].into_iter().enumerate() {
            if index > 0 {
                out.push(String::new());
            }
            append_reject_table(
                &mut out,
                &false_negative_reject_rows(i_fn_rows, d_fn_inscope, Some(period)),
                Some(period),
            );
        }
    }
    out
}

fn section_recommendations(i_all: &[&Record], min_group: u64) -> Vec<String> {
    let mut out = vec![
        String::new(),
        "## Recommendations (data-driven)".to_owned(),
        String::new(),
    ];
    let (base_total, base_accepted, _oos, _rejected) = threeway(i_all);
    let baseline = pct(base_accepted, base_total);
    let mut fluff: Vec<GroupRow> = Vec::new();
    for (tag, _pattern) in TAGS.iter() {
        let sub: Vec<&Record> = i_all
            .iter()
            .copied()
            .filter(|row| row.tags.contains(tag))
            .collect();
        if (sub.len() as u64) < min_group {
            continue;
        }
        let (total, accepted, _oos, rejected) = threeway(&sub);
        if pct(accepted, total) < baseline && pct(rejected, total) >= baseline {
            fluff.push((tag, total, pct(accepted, total), 0.0, pct(rejected, total)));
        }
    }
    fluff.sort_by(|left, right| right.4.total_cmp(&left.4));
    if !fluff.is_empty() {
        out.push(format!(
            "1. **Add these reject-heavy groups to the rubric OOS-signal list / judge down-vote list** \
(below the {}% baseline acceptance, high reject rate):",
            fmt0(baseline)
        ));
        for (tag, count, accepted, _unused, rejected) in fluff.iter().take(8) {
            out.push(format!(
                "   - `{tag}` — n={count}, acc={}%, rej={}%",
                fmt0(*accepted),
                fmt0(*rejected)
            ));
        }
    }
    let acc_impl: Vec<&Record> = i_all
        .iter()
        .copied()
        .filter(|row| row.outcome == "accepted")
        .collect();
    let low = acc_impl
        .iter()
        .filter(|row| matches!(row.severity.as_str(), "nit" | "latent"))
        .count();
    let severity_floor = !acc_impl.is_empty() && pct(low, acc_impl.len()) >= 15.0;
    if severity_floor {
        out.push(format!(
            "2. **Judge severity floor:** {}% of accepted implement findings were nit/latent — \
instruct voters to vote NO on in-scope nit (and latent unless a real \
correctness/regression defect).",
            fmt0(pct(low, acc_impl.len()))
        ));
    }
    let test: Vec<&Record> = i_all
        .iter()
        .copied()
        .filter(|row| row.tags.contains(&"theme:testing"))
        .collect();
    if !test.is_empty() && pct(test.len(), i_all.len()) >= 15.0 {
        out.push(format!(
            "3. **Tests default-to-OOS:** testing is {}% of implement findings — a test is in-scope \
only if it covers a new, uncovered, risk-bearing path this feature introduces.",
            fmt0(pct(test.len(), i_all.len()))
        ));
    }
    out.push(String::new());
    out.push(
        "Apply changes at `skills/shared/review-acceptance-rubric.md` and propagate via its \
`## Update triggers` list; run `make test-render-voter-prompt`."
            .to_owned(),
    );
    if fluff.is_empty() && !severity_floor {
        out.push(String::new());
        out.push("_(No strong fluff signal at the current thresholds / sample size.)_".to_owned());
    }
    out
}
