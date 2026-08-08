//! The `/report-tokens` analysis report: sections, cache rows, and plot input.
//!
//! Rust parity for Python `larch.report.report_tokens_render`,
//! `larch.report.report_tokens_issue`, and the series half of
//! `larch.report.report_tokens_plot`. Everything here is pure: the caller owns
//! the corpus scan, the pricing pass, and every file the report advertises, so
//! one rendered report is reproducible from its records alone.
//!
//! Two contracts travel with the text. The NDJSON cache rows and the plot
//! input are machine-read, so they keep Python's key order, rounding, and
//! `json.dumps` spacing. The Markdown is user-facing, and the issue body drops
//! whole low-priority sections rather than cutting a table in half when GitHub's
//! size limit bites.

use std::{
    collections::{BTreeMap, HashSet},
    fmt,
};

use serde_json::Number;

use crate::{
    OrderedJson,
    redaction::redact,
    report::{
        token_cost::{RunCost, TokenRates, aggregate_vendor_tokens, python_round},
        token_scan::{TokenRunRecord, TokenVendor},
    },
    vendor::python_json_dumps,
};

/// How many leading characters of a timestamp form its date.
const DATE_LEN: usize = 10;
/// How many runs the top-runs table lists.
const TOP_RUNS: usize = 10;
/// How many rows the phase-breakdown table lists.
const PHASE_ROWS: usize = 20;
/// The one workflow group both skills render.
const ALL_RUNS: &str = "All runs";
/// Heading the report and the empty report both open with.
pub const REPORT_HEADING: &str = "## Report Tokens Analysis";
/// Body of the report emitted when no run carried a parseable token report.
pub const EMPTY_REPORT_BODY: &str = "No parseable token reports found.";
/// Basename of the durable NDJSON snapshot the report advertises.
pub const CACHE_BASENAME: &str = "report-cache.ndjson";
/// Banner prepended to an issue body that lost sections to the size limit.
const TRUNCATION_PREFIX: &str = "## \u{26a0} Report body trimmed to fit GitHub's size limit\n\n\
This report is incomplete because low-priority sections were omitted before posting. \
Run `/report-tokens --no-issue` locally for the full output.\n\n";

/// Order in which sections are dropped from an oversized issue body.
///
/// Lower values are retained longer. The values are the wire numbers Python's
/// `SectionPriority` `IntEnum` used, so a recorded section list still sorts the
/// same way.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
#[repr(u8)]
pub enum SectionPriority {
    /// Never dropped.
    Banner = 0,
    /// The headline totals.
    Summary = 10,
    /// Aggregate cost.
    Aggregate = 20,
    /// Vendor, top-run, and phase tables.
    Breakdown = 30,
    /// Per-day trends.
    Trends = 40,
    /// Cost-reduction suggestions.
    Suggestions = 50,
    /// The displayed rate card.
    Cache = 60,
}

/// One titled report section and the priority that decides its fate.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ReportSection {
    /// Stable machine key, not the rendered heading.
    pub title: String,
    /// Rendered Markdown.
    pub body: String,
    /// Retention priority.
    pub priority: SectionPriority,
}

/// One scanned run and the cost the pricing pass gave it.
#[derive(Clone, Debug)]
pub struct PricedRun {
    /// The scanned run.
    pub record: TokenRunRecord,
    /// Its priced cost.
    pub cost: RunCost,
}

/// A rendered report: the stdout body and the sections an issue may carry.
#[derive(Clone, Debug)]
pub struct RenderedReport {
    /// The full Markdown body, ending with the advertised cache pointer.
    pub body: String,
    /// The sections, in render order.
    pub sections: Vec<ReportSection>,
}

/// A refusal from issue-body assembly.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum IssueBodyError {
    /// Redaction reported that it could not prove a secret was gone.
    RedactionFailed,
}

impl fmt::Display for IssueBodyError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match *self {
            Self::RedactionFailed => {
                formatter.write_str("ERROR: report issue body redaction failed")
            }
        }
    }
}

impl std::error::Error for IssueBodyError {}

/// Render a dollar amount the way Python's `_money` did.
fn money(value: f64) -> String {
    format!("${value:.2}")
}

/// Render a float the way Python's `str()` did, keeping a bare integer's `.0`.
fn python_float(value: f64) -> String {
    let rendered = format!("{value}");
    if rendered.contains(['.', 'e', 'E', 'n', 'i']) {
        rendered
    } else {
        format!("{rendered}.0")
    }
}

/// Group an integer with thousands separators, matching Python's `{:,}`.
fn grouped(value: i64) -> String {
    let negative = value < 0;
    let digits = value.unsigned_abs().to_string();
    let mut rendered = String::with_capacity(digits.len() + digits.len() / 3 + 1);
    for (index, digit) in digits.chars().enumerate() {
        if index > 0 && (digits.len() - index).is_multiple_of(3) {
            rendered.push(',');
        }
        rendered.push(digit);
    }
    if negative {
        format!("-{rendered}")
    } else {
        rendered
    }
}

/// The date prefix of a timestamp, absent when the value is too short.
///
/// Python measured and sliced in characters, so this does too rather than
/// slicing bytes out from under a multibyte timestamp.
fn date_of(value: &str) -> Option<String> {
    (value.chars().count() >= DATE_LEN).then(|| value.chars().take(DATE_LEN).collect())
}

/// The date a record is attributed to, preferring `started_at`.
fn record_date(run: &PricedRun) -> Option<String> {
    let value = if run.record.started_at.is_empty() {
        run.record.closed_at.as_str()
    } else {
        run.record.started_at.as_str()
    };
    date_of(value)
}

/// Escape one Markdown table cell the way Python's `_md_cell` did.
fn md_cell(value: &str) -> String {
    let normalized = value.replace("\r\n", "\n").replace('\r', "\n");
    let escaped = normalized
        .replace('\\', "\\\\")
        .replace('|', "\\|")
        .replace('[', "\\[")
        .replace(']', "\\]");
    let mut parts: Vec<&str> = escaped.split('\n').collect();
    if escaped.ends_with('\n') {
        let _trailing = parts.pop();
    }
    let joined = parts.join(" ");
    if joined.is_empty() {
        "unknown".to_owned()
    } else {
        joined
    }
}

/// The Cursor lane split, present only when both component costs are priced.
const fn cursor_lanes(run: &PricedRun) -> Option<(f64, f64)> {
    match (run.cost.cursor_composer_cost, run.cost.cursor_grok_cost) {
        (Some(composer), Some(grok)) => Some((composer, grok)),
        _absent => None,
    }
}

/// The Cursor cell of the top-runs table.
fn cursor_cost_text(run: &PricedRun) -> String {
    cursor_lanes(run).map_or_else(
        || money(run.cost.cursor_cost),
        |(composer, grok)| {
            format!(
                "{} (Composer {}, Grok {})",
                money(run.cost.cursor_cost),
                money(composer),
                money(grok)
            )
        },
    )
}

/// Sum one lane's cost across every run.
fn total_of(runs: &[PricedRun], lane: impl Fn(&PricedRun) -> f64) -> f64 {
    runs.iter().map(lane).sum()
}

fn summary(runs: &[PricedRun], actual_spend: Option<f64>) -> String {
    let total = total_of(runs, |run| run.cost.total_cost);
    let mut lines = vec![
        REPORT_HEADING.to_owned(),
        String::new(),
        format!("Analyzed {} parseable runs.", runs.len()),
        format!("Tracked total estimated cost: {}.", money(total)),
    ];
    let fallback = runs
        .iter()
        .filter(|run| !run.cost.priced_by_token_cost)
        .count();
    if fallback != 0 {
        lines.push(format!(
            "Pricing fallback used for {fallback} runs; blended rates are marked with `fallback` in tables."
        ));
    }
    if let Some(actual) = actual_spend {
        let delta = actual - total;
        let percent = if total == 0.0 {
            0.0
        } else {
            delta / total * 100.0
        };
        lines.push(format!(
            "Actual-spend reconciliation: tracked={} actual={} delta={percent:.1}%",
            money(total),
            money(actual)
        ));
    }
    lines.join("\n")
}

/// Median of a cost list, matching Python's `statistics.median`.
fn median(costs: &[f64]) -> f64 {
    let mut sorted = costs.to_vec();
    sorted.sort_by(|left, right| left.partial_cmp(right).unwrap_or(std::cmp::Ordering::Equal));
    let middle = sorted.len() / 2;
    if sorted.len() % 2 == 1 {
        sorted[middle]
    } else {
        // Not `f64::midpoint`: Python averaged the two middle values with a
        // plain add-and-halve, and the more accurate midpoint can land on a
        // different last digit.
        #[expect(
            clippy::manual_midpoint,
            reason = "Python's arithmetic, digit for digit"
        )]
        {
            (sorted[middle - 1] + sorted[middle]) / 2.0
        }
    }
}

#[expect(
    clippy::cast_precision_loss,
    reason = "Python divided the same integer count as a float"
)]
fn mean(costs: &[f64]) -> f64 {
    costs.iter().sum::<f64>() / costs.len() as f64
}

fn aggregate(skill: &str, runs: &[PricedRun]) -> String {
    let costs: Vec<f64> = runs.iter().map(|run| run.cost.total_cost).collect();
    let implement = skill == "implement";
    let mut lines = vec!["## Aggregate cost".to_owned(), String::new()];
    if implement {
        lines.push("| Label | Runs | Total | Median | Mean | Max |".to_owned());
        lines.push("| --- | ---: | ---: | ---: | ---: | ---: |".to_owned());
    } else {
        lines.push("| Runs | Total | Median | Mean | Max |".to_owned());
        lines.push("| ---: | ---: | ---: | ---: | ---: |".to_owned());
    }
    if !costs.is_empty() {
        let maximum = costs.iter().copied().fold(f64::NEG_INFINITY, f64::max);
        let cells = format!(
            "{} | {} | {} | {} | {}",
            costs.len(),
            money(costs.iter().sum()),
            money(median(&costs)),
            money(mean(&costs)),
            money(maximum)
        );
        if implement {
            lines.push(format!("| {ALL_RUNS} | {cells} |"));
        } else {
            lines.push(format!("| {cells} |"));
        }
    }
    lines.join("\n")
}

fn vendor_breakdown(runs: &[PricedRun]) -> String {
    let lane = |vendor: TokenVendor| -> i64 {
        runs.iter()
            .map(|run| aggregate_vendor_tokens(&run.record, vendor))
            .sum()
    };
    let row = |label: &str, cost: f64, tokens: i64| {
        format!("| {label} | {} | {} |", money(cost), grouped(tokens))
    };
    let mut lines = vec![
        "## Vendor breakdown".to_owned(),
        String::new(),
        "| Vendor | Cost | Tokens |".to_owned(),
        "| --- | ---: | ---: |".to_owned(),
        row(
            "Claude",
            total_of(runs, |run| run.cost.claude_cost),
            lane(TokenVendor::Claude),
        ),
        row(
            "Codex",
            total_of(runs, |run| run.cost.codex_cost),
            lane(TokenVendor::Codex),
        ),
        row(
            "Cursor",
            total_of(runs, |run| run.cost.cursor_cost),
            lane(TokenVendor::Cursor),
        ),
        row(
            "Claude (subprocess)",
            total_of(runs, |run| run.cost.claude_sub_cost),
            lane(TokenVendor::ClaudeSub),
        ),
    ];
    if !runs.is_empty() && runs.iter().all(|run| cursor_lanes(run).is_some()) {
        let composer = total_of(runs, |run| run.cost.cursor_composer_cost.unwrap_or(0.0));
        let grok = total_of(runs, |run| run.cost.cursor_grok_cost.unwrap_or(0.0));
        lines.insert(6, format!("| Cursor Grok | {} | \u{2014} |", money(grok)));
        lines.insert(
            6,
            format!("| Cursor Composer | {} | \u{2014} |", money(composer)),
        );
    }
    lines.join("\n")
}

fn top_runs(runs: &[PricedRun]) -> String {
    let mut lines = vec![
        "## Top runs by estimated cost".to_owned(),
        String::new(),
        "| Issue | Started | Total | Claude | Codex | Cursor | Claude (sub) |".to_owned(),
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |".to_owned(),
    ];
    let mut ordered: Vec<&PricedRun> = runs.iter().collect();
    ordered.sort_by(|left, right| {
        right
            .cost
            .total_cost
            .partial_cmp(&left.cost.total_cost)
            .unwrap_or(std::cmp::Ordering::Equal)
    });
    for run in ordered.into_iter().take(TOP_RUNS) {
        let issue = if run.record.url.is_empty() {
            format!("#{}", run.record.number)
        } else {
            format!("[#{}]({})", run.record.number, run.record.url)
        };
        let pricing = if run.cost.priced_by_token_cost {
            "python-pricing"
        } else {
            "fallback"
        };
        let started = date_of(&run.record.started_at).unwrap_or_else(|| "unknown".to_owned());
        lines.push(format!(
            "| {issue} | {} | {} ({pricing}) | {} | {} | {} | {} |",
            md_cell(&started),
            money(run.cost.total_cost),
            money(run.cost.claude_cost),
            money(run.cost.codex_cost),
            cursor_cost_text(run),
            money(run.cost.claude_sub_cost),
        ));
    }
    lines.join("\n")
}

fn phase_breakdown(runs: &[PricedRun]) -> String {
    let mut order: Vec<(String, String)> = Vec::new();
    let mut tokens: BTreeMap<(String, String), i64> = BTreeMap::new();
    let mut seen: HashSet<(i64, String, String)> = HashSet::new();
    for run in runs {
        for row in &run.record.phase_rows {
            let key = (row.vendor.as_str().to_owned(), row.step.clone());
            if !tokens.contains_key(&key) {
                order.push(key.clone());
            }
            *tokens.entry(key.clone()).or_insert(0) += row.total;
            let _fresh = seen.insert((run.record.number, key.0, key.1));
        }
    }
    let mut counts: BTreeMap<(String, String), i64> = BTreeMap::new();
    for (_number, vendor, step) in seen {
        *counts.entry((vendor, step)).or_insert(0) += 1;
    }
    let mut rows: Vec<(usize, &(String, String))> = order.iter().enumerate().collect();
    rows.sort_by(|left, right| {
        tokens[right.1]
            .cmp(&tokens[left.1])
            .then_with(|| left.0.cmp(&right.0))
    });
    let mut lines = vec![
        "## Phase breakdown".to_owned(),
        String::new(),
        "| Vendor | Phase | Runs | Tokens |".to_owned(),
        "| --- | --- | ---: | ---: |".to_owned(),
    ];
    for (_index, key) in rows.into_iter().take(PHASE_ROWS) {
        lines.push(format!(
            "| {} | {} | {} | {} |",
            md_cell(&key.0),
            md_cell(&key.1),
            counts.get(key).copied().unwrap_or(0),
            grouped(tokens[key])
        ));
    }
    lines.join("\n")
}

/// One per-day trend series over a lane that may be absent for a run.
fn trend_table(
    title: &str,
    runs: &[PricedRun],
    lane: impl Fn(&PricedRun) -> Option<f64>,
) -> String {
    let mut by_day: BTreeMap<String, f64> = BTreeMap::new();
    let mut missing = 0_usize;
    for run in runs {
        let Some(day) = date_of(&run.record.started_at) else {
            missing += 1;
            continue;
        };
        if let Some(value) = lane(run) {
            *by_day.entry(day).or_insert(0.0) += value;
        }
    }
    let mut lines = vec![
        format!("### {title}"),
        String::new(),
        "| Date | Cost |".to_owned(),
        "| --- | ---: |".to_owned(),
    ];
    lines.extend(
        by_day
            .iter()
            .map(|(day, value)| format!("| {day} | {} |", money(*value))),
    );
    if missing != 0 {
        lines.push(format!(
            "\n_{missing} runs lacked a parseable started_at date._"
        ));
    }
    lines.join("\n")
}

/// One trend lane: its heading, whether it is skipped when never priced, and
/// the cost it reads.
type TrendLane = (&'static str, bool, fn(&PricedRun) -> Option<f64>);

/// The lanes the trend section renders, in order.
fn trend_lanes() -> Vec<TrendLane> {
    vec![
        ("Total cost", false, |run| Some(run.cost.total_cost)),
        ("Claude cost", false, |run| Some(run.cost.claude_cost)),
        ("Codex cost", false, |run| Some(run.cost.codex_cost)),
        ("Cursor cost", false, |run| Some(run.cost.cursor_cost)),
        ("Cursor Composer cost", true, |run| {
            run.cost.cursor_composer_cost
        }),
        ("Cursor Grok cost", true, |run| run.cost.cursor_grok_cost),
        ("Claude (subprocess) cost", false, |run| {
            Some(run.cost.claude_sub_cost)
        }),
    ]
}

fn trends(runs: &[PricedRun]) -> String {
    let mut lines = vec!["## Per-day cost trends".to_owned(), String::new()];
    if runs.is_empty() {
        return lines.join("\n").trim_end().to_owned();
    }
    for (title, optional, lane) in trend_lanes() {
        if optional && !runs.iter().any(|run| lane(run).is_some()) {
            continue;
        }
        lines.push(trend_table(title, runs, lane));
        lines.push(String::new());
    }
    lines.join("\n").trim_end().to_owned()
}

fn suggestions(runs: &[PricedRun]) -> String {
    let cache_read: i64 = runs
        .iter()
        .map(|run| run.record.claude.cache_read + run.record.cursor.cache_read)
        .sum();
    let pricing_line = if runs.iter().any(|run| !run.cost.priced_by_token_cost) {
        "- Treat dollar values as estimates; rows marked `fallback` used blended display rates because `python/larch/report/report_tokens_cost.py` used blended fallback pricing."
    } else {
        "- Treat dollar values as estimates; `python/larch/report/report_tokens_cost.py` remains the pricing authority used for headline totals."
    };
    [
        "## Cost-reduction suggestions",
        "",
        "- Review the highest-cost runs above before optimizing lower-cost phases.",
        &format!(
            "- Cache-read tokens observed: {}; preserve prompt stability where cache hits are useful.",
            grouped(cache_read)
        ),
        pricing_line,
    ]
    .join("\n")
}

fn rates_text(rates: &TokenRates) -> String {
    [
        "## Rates used for display/fallback".to_owned(),
        String::new(),
        format!(
            "Claude: input {}/M, cache read {}/M, output {}/M.",
            python_float(rates.claude_input),
            python_float(rates.claude_cache_read),
            python_float(rates.claude_output)
        ),
        format!(
            "Codex: input {}/M, cached input {}/M, output {}/M.",
            python_float(rates.codex_input),
            python_float(rates.codex_cached_input),
            python_float(rates.codex_output)
        ),
        format!(
            "Cursor Composer: input {}/M, cache read {}/M, output {}/M.",
            python_float(rates.cursor_input),
            python_float(rates.cursor_cache_read),
            python_float(rates.cursor_output)
        ),
        format!(
            "Cursor Grok: input {}/M, cache read {}/M, output {}/M.",
            python_float(rates.cursor_grok_input),
            python_float(rates.cursor_grok_cache_read),
            python_float(rates.cursor_grok_output)
        ),
    ]
    .join("\n")
}

/// Build every report section and the stdout body that carries them.
///
/// `cache_pointer` is the advertised NDJSON path; the caller writes that file
/// from [`cache_ndjson`]. Actual spend reaches the issue body only when
/// `include_actual_spend_in_issue` is set, so an operator's private
/// reconciliation never leaks into a filed issue by default.
#[must_use]
pub fn render_report(
    skill: &str,
    runs: &[PricedRun],
    rates: &TokenRates,
    actual_spend: Option<f64>,
    include_actual_spend_in_issue: bool,
    cache_pointer: &str,
) -> RenderedReport {
    let issue_spend = if include_actual_spend_in_issue {
        actual_spend
    } else {
        None
    };
    let sections = vec![
        ReportSection {
            title: "summary".to_owned(),
            body: summary(runs, issue_spend),
            priority: SectionPriority::Summary,
        },
        ReportSection {
            title: "aggregate".to_owned(),
            body: aggregate(skill, runs),
            priority: SectionPriority::Aggregate,
        },
        ReportSection {
            title: "vendor".to_owned(),
            body: vendor_breakdown(runs),
            priority: SectionPriority::Breakdown,
        },
        ReportSection {
            title: "top".to_owned(),
            body: top_runs(runs),
            priority: SectionPriority::Breakdown,
        },
        ReportSection {
            title: "phase".to_owned(),
            body: phase_breakdown(runs),
            priority: SectionPriority::Breakdown,
        },
        ReportSection {
            title: "trends".to_owned(),
            body: trends(runs),
            priority: SectionPriority::Trends,
        },
        ReportSection {
            title: "suggestions".to_owned(),
            body: suggestions(runs),
            priority: SectionPriority::Suggestions,
        },
        ReportSection {
            title: "rates".to_owned(),
            body: rates_text(rates),
            priority: SectionPriority::Cache,
        },
    ];
    let mut bodies: Vec<String> = sections
        .iter()
        .map(|section| section.body.clone())
        .collect();
    if actual_spend.is_some() && !include_actual_spend_in_issue {
        bodies[0] = summary(runs, actual_spend);
    }
    let body = format!("{}\n\nCache JSON: {cache_pointer}", bodies.join("\n\n"));
    RenderedReport { body, sections }
}

/// Render the durable NDJSON cache snapshot, one JSON object per run.
#[must_use]
pub fn cache_ndjson(runs: &[PricedRun]) -> String {
    let mut rendered = String::new();
    for run in runs {
        let optional = |value: Option<f64>| {
            value.map_or(OrderedJson::Null, |inner| {
                OrderedJson::Number(Number::from_f64(inner).unwrap_or_else(|| Number::from(0)))
            })
        };
        let number = |value: f64| {
            OrderedJson::Number(Number::from_f64(value).unwrap_or_else(|| Number::from(0)))
        };
        // Python emitted `json.dumps(..., sort_keys=True)`; these keys are sorted.
        let row = OrderedJson::Object(vec![
            ("claude_cost".to_owned(), number(run.cost.claude_cost)),
            (
                "claude_sub_cost".to_owned(),
                number(run.cost.claude_sub_cost),
            ),
            (
                "closed_at".to_owned(),
                OrderedJson::String(run.record.closed_at.clone()),
            ),
            ("codex_cost".to_owned(), number(run.cost.codex_cost)),
            (
                "cursor_composer_cost".to_owned(),
                optional(run.cost.cursor_composer_cost),
            ),
            ("cursor_cost".to_owned(), number(run.cost.cursor_cost)),
            (
                "cursor_grok_cost".to_owned(),
                optional(run.cost.cursor_grok_cost),
            ),
            (
                "number".to_owned(),
                OrderedJson::Number(Number::from(run.record.number)),
            ),
            (
                "pricing_source".to_owned(),
                OrderedJson::String(
                    if run.cost.priced_by_token_cost {
                        "python-pricing"
                    } else {
                        "python-blended-fallback"
                    }
                    .to_owned(),
                ),
            ),
            (
                "started_at".to_owned(),
                OrderedJson::String(run.record.started_at.clone()),
            ),
            (
                "title".to_owned(),
                OrderedJson::String(run.record.title.clone()),
            ),
            ("total_cost".to_owned(), number(run.cost.total_cost)),
            (
                "url".to_owned(),
                OrderedJson::String(run.record.url.clone()),
            ),
        ]);
        rendered.push_str(&python_json_dumps(&row).unwrap_or_default());
        rendered.push('\n');
    }
    rendered
}

/// Render the plot child's JSON input contract.
#[must_use]
pub fn plot_input_json(skill: &str, runs: &[PricedRun]) -> String {
    let mut by_day: BTreeMap<String, f64> = BTreeMap::new();
    for run in runs {
        if let Some(day) = record_date(run) {
            *by_day.entry(day).or_insert(0.0) += run.cost.total_cost;
        }
    }
    let points: Vec<OrderedJson> = by_day
        .into_iter()
        .map(|(day, cost)| {
            OrderedJson::Object(vec![
                (
                    "cost".to_owned(),
                    OrderedJson::Number(
                        Number::from_f64(python_round(cost, 2)).unwrap_or_else(|| Number::from(0)),
                    ),
                ),
                ("date".to_owned(), OrderedJson::String(day)),
            ])
        })
        .collect();
    let series = OrderedJson::Array(vec![OrderedJson::Object(vec![
        ("label".to_owned(), OrderedJson::String(ALL_RUNS.to_owned())),
        ("points".to_owned(), OrderedJson::Array(points)),
    ])]);
    // Python emitted `json.dumps(..., sort_keys=True)`; these keys are sorted.
    let document = OrderedJson::Object(vec![
        ("series".to_owned(), series),
        ("skill".to_owned(), OrderedJson::String(skill.to_owned())),
        ("version".to_owned(), OrderedJson::Number(Number::from(1))),
    ]);
    python_json_dumps(&document).unwrap_or_default()
}

/// Join the kept sections into one issue body.
fn assemble(sections: &[&ReportSection]) -> String {
    let joined = sections
        .iter()
        .map(|section| section.body.trim())
        .filter(|body| !body.is_empty())
        .collect::<Vec<_>>()
        .join("\n\n");
    format!("{joined}\n")
}

/// Redact one candidate body and refuse when redaction could not finish.
fn posting_body(text: &str) -> Result<String, IssueBodyError> {
    let redacted = redact(text).text().to_owned();
    if redacted.contains("[content truncated") {
        return Err(IssueBodyError::RedactionFailed);
    }
    Ok(redacted)
}

/// The heading a dropped section is named by in the truncation banner.
fn section_label(section: &ReportSection, skill: &str) -> String {
    if section.title == "aggregate" && skill == "implement" {
        return "Aggregate cost".to_owned();
    }
    match section.title.as_str() {
        "summary" => "Report Tokens Analysis",
        "aggregate" => "Aggregate cost by workflow",
        "vendor" => "Vendor breakdown",
        "top" => "Top runs by estimated cost",
        "phase" => "Phase breakdown",
        "trends" => "Per-day cost trends",
        "suggestions" => "Cost-reduction suggestions",
        "rates" => "Rates used for display/fallback",
        other => other,
    }
    .to_owned()
}

/// Assemble the issue body, dropping whole low-priority sections to fit `limit`.
///
/// Returns the redacted body and the labels of every dropped section. A body
/// that still exceeds `limit` after every droppable section is gone is returned
/// as-is; the caller decides whether to refuse the post.
///
/// # Errors
///
/// Returns [`IssueBodyError::RedactionFailed`] when redaction reports that it
/// could not prove a secret was removed.
pub fn assemble_issue_body(
    sections: &[ReportSection],
    limit: usize,
    skill: &str,
) -> Result<(String, Vec<String>), IssueBodyError> {
    let mut kept: Vec<&ReportSection> = sections.iter().collect();
    let mut omitted: Vec<String> = Vec::new();
    let redacted = posting_body(&assemble(&kept))?;
    if redacted.len() <= limit {
        return Ok((redacted, omitted));
    }
    let mut candidates: Vec<&ReportSection> = kept
        .iter()
        .copied()
        .filter(|section| section.priority != SectionPriority::Banner)
        .collect();
    candidates.sort_by(|left, right| right.priority.cmp(&left.priority));
    let mut body = redacted;
    for candidate in candidates {
        if let Some(index) = kept
            .iter()
            .position(|section| std::ptr::eq(*section, candidate))
        {
            let _dropped = kept.remove(index);
        }
        omitted.push(section_label(candidate, skill));
        let notice = format!(
            "{TRUNCATION_PREFIX}Omitted sections: {}.\n\n",
            omitted.join(", ")
        );
        body = posting_body(&format!("{notice}{}", assemble(&kept)))?;
        if body.len() <= limit {
            return Ok((body, omitted));
        }
    }
    Ok((body, omitted))
}

/// The issue title for one skill's report.
#[must_use]
pub fn title_for_skill(skill: &str, timestamp: &str) -> String {
    let label = if skill == "design" {
        "Design"
    } else {
        "Implement"
    };
    format!("[{label} Analysis Report] Token costs as of {timestamp}")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn groups_thousands_like_python() {
        assert_eq!(grouped(0), "0");
        assert_eq!(grouped(999), "999");
        assert_eq!(grouped(26_215), "26,215");
        assert_eq!(grouped(-1_234_567), "-1,234,567");
    }

    #[test]
    fn renders_floats_with_a_python_decimal_point() {
        assert_eq!(python_float(5.0), "5.0");
        assert_eq!(python_float(0.75), "0.75");
    }

    #[test]
    fn escapes_markdown_cells_and_defaults_to_unknown() {
        assert_eq!(md_cell("a|b"), "a\\|b");
        assert_eq!(md_cell("[x]"), "\\[x\\]");
        assert_eq!(md_cell(""), "unknown");
        assert_eq!(md_cell("a\r\nb"), "a b");
    }

    #[test]
    fn medians_even_and_odd_lengths() {
        assert!((median(&[1.0, 2.0, 3.0]) - 2.0).abs() < f64::EPSILON);
        assert!((median(&[1.0, 2.0, 3.0, 5.0]) - 2.5).abs() < f64::EPSILON);
    }
}
