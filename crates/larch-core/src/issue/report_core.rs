//! Deterministic issue categorization and coverage indexes.
//!
//! Library parity for the shared analysis half of Python `larch.issue._report`
//! and the `larch.issue._util` predicates it depends on. This leaf ports no
//! command: the backlog analysis commands stay Python-owned until their cutover
//! leaf moves them, chart and Markdown rendering stay with the reporting
//! umbrella, and the waste-signature and reviewer/persona sections ship with
//! the command leaves that render them.

use chrono::{DateTime, NaiveDate, Utc};
use regex::Regex;
use serde_json::Value;
use std::{collections::BTreeMap, sync::LazyLock};

/// Maximum issue-body characters any issue analysis reads.
pub const BODY_CAP: usize = 5 * 1024;

const STOP_WORDS: [&str; 19] = [
    "a", "an", "and", "are", "as", "be", "by", "for", "from", "in", "into", "is", "it", "of", "on",
    "or", "the", "to", "with",
];

/// Keywords whose Python rule matches inflections (`validate` -> `validat\w*`).
const STEM_KEYWORDS: [&str; 14] = [
    "determin",
    "validate",
    "sanitize",
    "simplify",
    "permission",
    "secret",
    "feature",
    "scaffold",
    "failure",
    "regression",
    "assert",
    "crash",
    "refactor",
    "rename",
];

/// Ordered keyword rules; the first matching category wins.
const CATEGORY_RULES: [(IssueCategory, &[&str]); 8] = [
    (
        IssueCategory::DocumentationContractDrift,
        &[
            "doc",
            "docs",
            "documentation",
            "documented",
            "documenting",
            "readme",
            "contract",
            "prompt",
            "instruction",
            "instructions",
            "schema",
            "schemas",
        ],
    ),
    (
        IssueCategory::BugFix,
        &[
            "bug",
            "bugs",
            "fix",
            "fixes",
            "fixed",
            "fixing",
            "broken",
            "failure",
            "error",
            "errors",
            "crash",
            "regression",
        ],
    ),
    (
        IssueCategory::TestCoverage,
        &[
            "test", "tests", "testing", "coverage", "harness", "fixture", "fixtures", "assert",
        ],
    ),
    (
        IssueCategory::HardeningValidationSecurity,
        &[
            "security",
            "secret",
            "validate",
            "guard",
            "permission",
            "sanitize",
            "safe",
        ],
    ),
    (
        IssueCategory::RefactorCodeClarity,
        &["refactor", "cleanup", "clarity", "simplify", "rename"],
    ),
    (
        IssueCategory::DeterminismHaltPrevention,
        &["determin", "halt", "timeout", "race", "idempotent", "retry"],
    ),
    (
        IssueCategory::NewFeatureNewSkill,
        &["feature", "skill", "scaffold", "add", "new"],
    ),
    (
        IssueCategory::PerformanceTokenCostReduction,
        &["performance", "token", "cost", "speed", "latency", "cache"],
    ),
];

/// One issue-analysis category, in Python rule order.
#[derive(Clone, Copy, Debug, Eq, Hash, Ord, PartialEq, PartialOrd)]
pub enum IssueCategory {
    /// Recognized by the tracking-issue body preamble.
    TrackingUmbrella,
    /// Recognized by an investigate or research title.
    ResearchInvestigation,
    /// Documentation, prompt, contract, and schema drift.
    DocumentationContractDrift,
    /// Defect repair.
    BugFix,
    /// Test, harness, and fixture coverage.
    TestCoverage,
    /// Hardening, validation, and security.
    HardeningValidationSecurity,
    /// Refactoring and code clarity.
    RefactorCodeClarity,
    /// Determinism and halt prevention.
    DeterminismHaltPrevention,
    /// New features and new skills.
    NewFeatureNewSkill,
    /// Performance and token-cost reduction.
    PerformanceTokenCostReduction,
    /// No rule matched.
    Other,
}

impl IssueCategory {
    /// Return the exact Python category label.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::TrackingUmbrella => "Tracking/umbrella",
            Self::ResearchInvestigation => "Research/investigation",
            Self::DocumentationContractDrift => "Documentation/contract drift",
            Self::BugFix => "Bug fix",
            Self::TestCoverage => "Test coverage",
            Self::HardeningValidationSecurity => "Hardening/validation/security",
            Self::RefactorCodeClarity => "Refactor/code clarity",
            Self::DeterminismHaltPrevention => "Determinism/halt-prevention",
            Self::NewFeatureNewSkill => "New feature/new skill",
            Self::PerformanceTokenCostReduction => "Performance/token-cost reduction",
            Self::Other => "Other",
        }
    }
}

// WHY: the regex crate ships without `unicode-case`, so ASCII-only `(?i-u:...)`
// groups carry case insensitivity while `\b` and `\w` stay Unicode-aware, which
// is what Python's `re.I` gives these ASCII keywords.
fn keyword_pattern(keyword: &str) -> String {
    if STEM_KEYWORDS.contains(&keyword) {
        let stem = keyword.strip_suffix(['e', 'y']).unwrap_or(keyword);
        format!("(?i-u:{})\\w*", regex::escape(stem))
    } else {
        format!("(?i-u:{})\\b", regex::escape(keyword))
    }
}

static CATEGORY_PATTERNS: LazyLock<Vec<(IssueCategory, Regex)>> = LazyLock::new(|| {
    CATEGORY_RULES
        .iter()
        .map(|(category, keywords)| {
            let alternation = keywords
                .iter()
                .map(|keyword| keyword_pattern(keyword))
                .collect::<Vec<_>>()
                .join("|");
            let pattern = format!("\\b(?:{alternation})");
            (
                *category,
                Regex::new(&pattern).expect("category keyword regex should compile"),
            )
        })
        .collect()
});

/// Return the compiled keyword pattern for one rule-driven category, so the
/// ground-truth resurfacing test reuses this owner instead of its own copy.
#[must_use]
pub fn category_pattern(category: IssueCategory) -> Option<&'static Regex> {
    CATEGORY_PATTERNS
        .iter()
        .find_map(|(candidate, pattern)| (*candidate == category).then_some(pattern))
}

static PREFIX_PATTERN: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^\s*(?:\[(?i-u:DONE|OOS|IN PROGRESS|STALLED|URGENT)\]\s*)+")
        .expect("title prefix regex should compile")
});

static TOKEN_PATTERN: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"[a-z][a-z0-9-]{2,}").expect("title token regex should compile"));

static RESEARCH_TITLE_PATTERN: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^\s*(?:\[(?i-u:research)[^\]]*\]\s*)?(?i-u:investigate|research)\b")
        .expect("research title regex should compile")
});

static NOT_PLANNED_BODY_PATTERN: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"\b(?i-u:wontfix|won't fix|not[- ]planned|no plan to fix)\b")
        .expect("not-planned body regex should compile")
});

/// Strip the managed status prefixes a title lifecycle may accumulate.
#[must_use]
pub fn strip_prefixes(title: &str) -> String {
    PREFIX_PATTERN.replace(title, "").trim().to_owned()
}

/// Return the distinctive lowercase tokens of one title, in title order.
#[must_use]
pub fn title_tokens(title: &str) -> Vec<String> {
    let cleaned = strip_prefixes(title).to_lowercase();
    TOKEN_PATTERN
        .find_iter(&cleaned)
        .map(|token| token.as_str().to_owned())
        .filter(|token| !STOP_WORDS.contains(&token.as_str()))
        .collect()
}

/// Public lifecycle state of an analyzed issue. Unknown is never coerced.
#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub enum IssueLifecycle {
    /// `state` reported `OPEN`.
    Open,
    /// `state` reported `CLOSED`.
    Closed,
    /// `state` was absent or unrecognized; it counts toward totals only.
    Unknown,
}

impl IssueLifecycle {
    /// Parse the GitHub `state` field without coercing unknown values.
    ///
    /// Python compares the uppercased field for exact equality and never trims,
    /// so a padded value is `Unknown` here too.
    #[must_use]
    pub fn parse(raw: &str) -> Self {
        match raw.to_ascii_uppercase().as_str() {
            "OPEN" => Self::Open,
            "CLOSED" => Self::Closed,
            _ => Self::Unknown,
        }
    }

    /// Return the canonical uppercase token.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Open => "OPEN",
            Self::Closed => "CLOSED",
            Self::Unknown => "UNKNOWN",
        }
    }
}

/// One normalized issue record consumed by every issue analysis. `body` is
/// capped at [`BODY_CAP`] characters and `labels` are trimmed and lowercase.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct IssueSummary {
    pub number: u64,
    pub title: String,
    pub body: String,
    pub state: IssueLifecycle,
    pub state_reason: String,
    pub state_reason_degraded: bool,
    pub labels: Vec<String>,
    pub created_at: Option<DateTime<Utc>>,
    pub closed_at: Option<DateTime<Utc>>,
    pub closed_by_pull_requests: Vec<String>,
}

impl IssueSummary {
    /// Build a record from one element of a `gh issue list --json` dump.
    ///
    /// Returns `None` for the same elements the Python loader skips: anything
    /// that is not an object with a positive numeric `number`.
    #[must_use]
    pub fn from_json(value: &Value) -> Option<Self> {
        let object = value.as_object()?;
        let number = positive_number(object.get("number"))?;
        Some(Self {
            number,
            title: string_field(object.get("title")),
            body: body_field(object.get("body")),
            state: IssueLifecycle::parse(&string_field(object.get("state"))),
            state_reason: string_field(object.get("stateReason"))
                .trim()
                .to_ascii_uppercase(),
            state_reason_degraded: degraded_fields(object.get("_larch_degraded_fields"))
                .iter()
                .any(|field| field == "stateReason"),
            labels: label_names(object.get("labels")),
            created_at: parse_timestamp(&string_field(object.get("createdAt"))),
            closed_at: parse_timestamp(&string_field(object.get("closedAt"))),
            closed_by_pull_requests: pull_request_refs(
                object.get("closedByPullRequestsReferences"),
            ),
        })
    }

    /// Return the title-plus-capped-body haystack every classifier searches.
    #[must_use]
    pub fn text(&self) -> String {
        format!("{}\n{}", self.title, self.body)
    }

    /// Return whether this issue carries a not-planned signal.
    ///
    /// This is the single owner of the predicate; the out-of-scope fate
    /// classifier consumes it rather than re-deriving the signal.
    #[must_use]
    pub fn not_planned(&self) -> bool {
        if self.state_reason == "NOT_PLANNED" && !self.state_reason_degraded {
            return true;
        }
        if self.labels.iter().any(|label| {
            matches!(
                label.as_str(),
                "wontfix" | "won't fix" | "not planned" | "not-planned"
            )
        }) {
            return true;
        }
        NOT_PLANNED_BODY_PATTERN.is_match(&self.body.to_lowercase())
    }

    /// Return the rule-driven default category for this issue.
    #[must_use]
    pub fn default_category(&self) -> IssueCategory {
        let body_start = self.body.trim_start().to_lowercase();
        if body_start.starts_with("tracking issue for") && body_start.contains("original prompt") {
            return IssueCategory::TrackingUmbrella;
        }
        if RESEARCH_TITLE_PATTERN.is_match(&self.title) {
            return IssueCategory::ResearchInvestigation;
        }
        let haystack = self.text();
        CATEGORY_PATTERNS
            .iter()
            .find_map(|(category, pattern)| pattern.is_match(&haystack).then_some(*category))
            .unwrap_or(IssueCategory::Other)
    }
}

fn body_field(value: Option<&Value>) -> String {
    string_field(value).chars().take(BODY_CAP).collect()
}

fn string_field(value: Option<&Value>) -> String {
    match value {
        Some(Value::String(text)) => text.clone(),
        _ => String::new(),
    }
}

fn positive_number(value: Option<&Value>) -> Option<u64> {
    match value {
        Some(Value::Number(number)) => number.as_u64().filter(|parsed| *parsed > 0),
        Some(Value::String(text)) => text
            .chars()
            .all(|character| character.is_ascii_digit())
            .then(|| text.parse::<u64>().ok())
            .flatten()
            .filter(|parsed| *parsed > 0),
        _ => None,
    }
}

fn degraded_fields(value: Option<&Value>) -> Vec<String> {
    let Some(Value::Array(items)) = value else {
        return Vec::new();
    };
    items
        .iter()
        .filter_map(|item| item.as_str().map(str::to_owned))
        .collect()
}

/// Normalize label names, deduplicated like Python's label set but kept in
/// source order so the record stays comparable across runs.
fn label_names(value: Option<&Value>) -> Vec<String> {
    let Some(Value::Array(items)) = value else {
        return Vec::new();
    };
    let mut names: Vec<String> = Vec::new();
    for item in items {
        let scalar = match item {
            Value::Object(fields) => fields.get("name").and_then(label_scalar),
            other => label_scalar(other),
        };
        let Some(name) = scalar.map(|text| text.trim().to_lowercase()) else {
            continue;
        };
        if !name.is_empty() && !names.contains(&name) {
            names.push(name);
        }
    }
    names
}

/// Coerce a label scalar the way Python's `str(value)` does for truthy values.
///
/// Python skips falsy values (absent, empty, zero, false) and stringifies the
/// rest, so a numeric or boolean label still reaches the label set.
fn label_scalar(value: &Value) -> Option<String> {
    match value {
        Value::String(text) => (!text.is_empty()).then(|| text.clone()),
        Value::Number(number) => (number.as_f64() != Some(0.0)).then(|| number.to_string()),
        Value::Bool(true) => Some("True".to_owned()),
        _ => None,
    }
}

fn pull_request_refs(value: Option<&Value>) -> Vec<String> {
    let Some(Value::Array(items)) = value else {
        return Vec::new();
    };
    items.iter().map(pull_request_ref_id).collect()
}

fn pull_request_ref_id(reference: &Value) -> String {
    if let Some(fields) = reference.as_object() {
        for key in ["url", "number", "title"] {
            match fields.get(key) {
                Some(Value::String(text)) if !text.is_empty() => return text.clone(),
                Some(Value::Number(number)) => return number.to_string(),
                _ => {}
            }
        }
    }
    // WHY: a reference naming no url, number, or title is degenerate. The id
    // keeps one entry per reference so closed-by-PR counting matches Python;
    // its text is a Rust-side canonical form with no wire consumer yet.
    serde_json::to_string(reference).unwrap_or_default()
}

/// Parse an ISO-8601 timestamp into UTC, tolerating a trailing `Z`, a missing
/// offset, and a bare calendar date.
#[must_use]
pub fn parse_timestamp(value: &str) -> Option<DateTime<Utc>> {
    let trimmed = value.trim();
    if trimmed.is_empty() {
        return None;
    }
    if let Ok(parsed) = DateTime::parse_from_rfc3339(trimmed) {
        return Some(parsed.with_timezone(&Utc));
    }
    for format in ["%Y-%m-%dT%H:%M:%S%.f", "%Y-%m-%d %H:%M:%S%.f"] {
        if let Ok(naive) = chrono::NaiveDateTime::parse_from_str(trimmed, format) {
            return Some(naive.and_utc());
        }
    }
    NaiveDate::parse_from_str(trimmed, "%Y-%m-%d")
        .ok()
        .and_then(|date| date.and_hms_opt(0, 0, 0))
        .map(|naive| naive.and_utc())
}

/// Return the linearly interpolated percentile of `values`.
#[must_use]
pub fn percentile(values: &[f64], percent: f64) -> Option<f64> {
    if values.is_empty() {
        return None;
    }
    let mut ordered = values.to_vec();
    ordered.sort_by(f64::total_cmp);
    if ordered.len() == 1 {
        return ordered.first().copied();
    }
    #[expect(
        clippy::cast_precision_loss,
        reason = "issue counts stay far below the f64 integer range"
    )]
    let rank = (ordered.len() - 1) as f64 * (percent / 100.0);
    let lower = rank.floor();
    #[expect(
        clippy::cast_possible_truncation,
        clippy::cast_sign_loss,
        reason = "rank is a non-negative index bounded by the ordered length"
    )]
    let (lower_index, upper_index) = (lower as usize, rank.ceil() as usize);
    let low = *ordered.get(lower_index)?;
    if lower_index == upper_index {
        return Some(low);
    }
    let high = *ordered.get(upper_index)?;
    #[expect(
        clippy::suboptimal_flops,
        reason = "unfused arithmetic keeps the interpolated value bit-identical to Python"
    )]
    let interpolated = low + (high - low) * (rank - lower);
    Some(interpolated)
}

/// Deterministic coverage index over one issue population.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct CoverageStats {
    pub total: usize,
    pub open: usize,
    pub closed: usize,
    pub oldest: Option<NaiveDate>,
    pub newest: Option<NaiveDate>,
    pub p25_close_days: Option<f64>,
    pub median_close_days: Option<f64>,
    pub p75_close_days: Option<f64>,
    pub p90_close_days: Option<f64>,
    pub pr_closed_pct: f64,
}

/// Compute the coverage index. The result depends only on the issue records.
#[must_use]
pub fn coverage_stats(issues: &[IssueSummary]) -> CoverageStats {
    let created: Vec<NaiveDate> = issues
        .iter()
        .filter_map(|issue| issue.created_at.map(|value| value.date_naive()))
        .collect();
    let mut close_durations: Vec<f64> = Vec::new();
    let mut pr_closed = 0_usize;
    let mut closed = 0_usize;
    for issue in issues {
        if issue.state != IssueLifecycle::Closed {
            continue;
        }
        closed += 1;
        if !issue.closed_by_pull_requests.is_empty() {
            pr_closed += 1;
        }
        if let (Some(created_at), Some(closed_at)) = (issue.created_at, issue.closed_at)
            && closed_at >= created_at
        {
            close_durations.push(duration_days(closed_at - created_at));
        }
    }
    #[expect(
        clippy::cast_precision_loss,
        reason = "issue counts stay far below the f64 integer range"
    )]
    let pr_closed_pct = if closed == 0 {
        0.0
    } else {
        pr_closed as f64 / closed as f64 * 100.0
    };
    CoverageStats {
        total: issues.len(),
        open: issues
            .iter()
            .filter(|issue| issue.state == IssueLifecycle::Open)
            .count(),
        closed,
        oldest: created.iter().min().copied(),
        newest: created.iter().max().copied(),
        p25_close_days: percentile(&close_durations, 25.0),
        median_close_days: percentile(&close_durations, 50.0),
        p75_close_days: percentile(&close_durations, 75.0),
        p90_close_days: percentile(&close_durations, 90.0),
        pr_closed_pct,
    }
}

/// Convert an issue lifetime to fractional days.
///
/// Python divides `total_seconds()`, which carries sub-second precision, so the
/// microsecond component must survive the conversion.
#[expect(
    clippy::cast_precision_loss,
    reason = "issue lifetimes stay far below the f64 integer range"
)]
fn duration_days(delta: chrono::TimeDelta) -> f64 {
    let seconds = delta.num_microseconds().map_or_else(
        || delta.num_seconds() as f64,
        |micros| micros as f64 / 1_000_000.0,
    );
    seconds / 86_400.0
}

/// How [`categorize`] assigns labels.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum CategoryMode {
    /// Rule-driven categories.
    Default,
    /// Leading title tokens across the population.
    Auto,
}

/// One assigned category label.
#[derive(Clone, Debug, Eq, Hash, Ord, PartialEq, PartialOrd)]
pub enum CategoryLabel {
    /// A rule-driven category.
    Known(IssueCategory),
    /// An auto-mode token bucket, rendered as `Auto: <token>`.
    Auto(String),
}

impl CategoryLabel {
    /// Return the exact Python label text.
    #[must_use]
    pub fn label(&self) -> String {
        match self {
            Self::Known(category) => category.as_str().to_owned(),
            Self::Auto(token) => format!("Auto: {token}"),
        }
    }
}

/// Issue-number to category assignment.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct CategoryIndex {
    assignments: BTreeMap<u64, CategoryLabel>,
}

impl CategoryIndex {
    /// Return the assigned label, defaulting to `Other`.
    #[must_use]
    pub fn label_for(&self, number: u64) -> CategoryLabel {
        self.assignments
            .get(&number)
            .cloned()
            .unwrap_or(CategoryLabel::Known(IssueCategory::Other))
    }

    /// Return the number of assignments.
    #[must_use]
    pub fn len(&self) -> usize {
        self.assignments.len()
    }

    /// Return whether no issue was assigned.
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.assignments.is_empty()
    }
}

/// Assign each issue a category.
///
/// Auto mode ranks tokens by document frequency and breaks ties by first
/// appearance in issue order, so the index depends only on the issue records
/// and never on hash or filesystem ordering.
#[must_use]
pub fn categorize(issues: &[IssueSummary], mode: CategoryMode, top_k: usize) -> CategoryIndex {
    if mode == CategoryMode::Default {
        return CategoryIndex {
            assignments: issues
                .iter()
                .map(|issue| (issue.number, CategoryLabel::Known(issue.default_category())))
                .collect(),
        };
    }
    let mut order: Vec<String> = Vec::new();
    let mut frequency: BTreeMap<String, usize> = BTreeMap::new();
    let mut issue_tokens: BTreeMap<u64, Vec<String>> = BTreeMap::new();
    for issue in issues {
        let tokens = title_tokens(&issue.title);
        let mut seen: Vec<&String> = Vec::new();
        for token in &tokens {
            if seen.contains(&token) {
                continue;
            }
            seen.push(token);
            let count = frequency.entry(token.clone()).or_insert(0);
            if *count == 0 {
                order.push(token.clone());
            }
            *count += 1;
        }
        issue_tokens.insert(issue.number, tokens);
    }
    let mut ranked: Vec<&String> = order.iter().collect();
    ranked.sort_by_key(|token| std::cmp::Reverse(frequency.get(*token).copied().unwrap_or(0)));
    let leaders: Vec<&str> = ranked
        .into_iter()
        .take(top_k.max(1))
        .map(String::as_str)
        .collect();
    CategoryIndex {
        assignments: issues
            .iter()
            .map(|issue| {
                let label = issue_tokens
                    .get(&issue.number)
                    .and_then(|tokens| {
                        tokens
                            .iter()
                            .find(|token| leaders.contains(&token.as_str()))
                    })
                    .map_or(CategoryLabel::Known(IssueCategory::Other), |token| {
                        CategoryLabel::Auto(token.clone())
                    });
                (issue.number, label)
            })
            .collect(),
    }
}

/// One row of the category breakdown.
#[derive(Clone, Debug, PartialEq)]
pub struct CategoryCount {
    pub label: String,
    pub count: usize,
    pub share_pct: f64,
}

/// Count issues per category, most frequent first, ties in first-seen order.
#[must_use]
pub fn category_breakdown(
    issues: &[IssueSummary],
    categories: &CategoryIndex,
) -> Vec<CategoryCount> {
    let mut order: Vec<String> = Vec::new();
    let mut counts: BTreeMap<String, usize> = BTreeMap::new();
    for issue in issues {
        let label = categories.label_for(issue.number).label();
        let count = counts.entry(label.clone()).or_insert(0);
        if *count == 0 {
            order.push(label);
        }
        *count += 1;
    }
    let total = issues.len().max(1);
    let mut rows: Vec<CategoryCount> = order
        .into_iter()
        .map(|label| {
            let count = counts.get(&label).copied().unwrap_or(0);
            #[expect(
                clippy::cast_precision_loss,
                reason = "issue counts stay far below the f64 integer range"
            )]
            let share_pct = count as f64 / total as f64 * 100.0;
            CategoryCount {
                label,
                count,
                share_pct,
            }
        })
        .collect();
    rows.sort_by_key(|row| std::cmp::Reverse(row.count));
    rows
}
