//! Timing-ledger rows, the timing dump, and the rendered timing report.
//!
//! Every rule here is a pure function over already-read ledger text and an
//! explicit `now` supplied by the caller's clock. The adapters and CLI layers
//! own path resolution, locking, and the append itself, so a test can exercise
//! the whole report contract with a fake clock and no filesystem.

use crate::ordered_json::OrderedJson;
use serde_json::Number;

/// Canonical allow-list for literal `--timing-task-kind` values.
///
/// Update this list with every new literal call site. `timing task-kinds`
/// prints it, and the allow-list lint compares call sites against that output.
pub const TIMING_TASK_KINDS_ALLOWED: [&str; 78] = [
    "claude-ci",
    "claude-ci-fix",
    "claude-code-voter",
    "claude-decomp-generic",
    "claude-lint-fix",
    "claude-phase3-aggregator",
    "claude-phase3-correctness",
    "claude-phase3-edge-cases",
    "claude-phase3-plan-fidelity",
    "claude-phase3-structure",
    "claude-phase3-testing",
    "claude-plan-draft",
    "claude-plan-generic",
    "claude-plan-voter",
    "claude-relevant-checks",
    "claude-review",
    "claude-review-fix",
    "claude-voter-1-parse-retry",
    "codex-brainstorm",
    "codex-ci",
    "codex-ci-fix",
    "codex-exec",
    "codex-implement",
    "codex-phase1-correctness",
    "codex-phase1-edge-cases",
    "codex-phase1-testing",
    "codex-phase2-correctness",
    "codex-phase2-edge-cases",
    "codex-phase2-testing",
    "codex-plan-arch",
    "codex-plan-autofix",
    "codex-plan-draft",
    "codex-plan-innovation",
    "codex-plan-pragmatic",
    "codex-plan-requirements",
    "codex-plan-voter",
    "codex-review",
    "codex-review-fix",
    "codex-review-generic",
    "codex-review-voter",
    "codex-specialist-correctness",
    "codex-specialist-edge-cases",
    "codex-specialist-plan-fidelity",
    "codex-specialist-structure",
    "codex-specialist-testing",
    "cursor-brainstorm",
    "cursor-ci",
    "cursor-ci-fix",
    "cursor-implement",
    "cursor-phase1-correctness",
    "cursor-phase1-edge-cases",
    "cursor-phase1-testing",
    "cursor-phase2-correctness",
    "cursor-phase2-edge-cases",
    "cursor-phase2-testing",
    "cursor-plan-arch",
    "cursor-plan-autofix",
    "cursor-plan-innovation",
    "cursor-plan-pragmatic",
    "cursor-plan-requirements",
    "cursor-plan-voter",
    "cursor-review",
    "cursor-review-fix",
    "cursor-review-generic",
    "cursor-review-voter",
    "cursor-specialist-correctness",
    "cursor-specialist-edge-cases",
    "cursor-specialist-plan-fidelity",
    "cursor-specialist-structure",
    "cursor-specialist-testing",
    "exec-issue-assessment",
    "gate-b-apply",
    "implement-code-flow",
    "rejected-analysis-verify",
    "reviewer-collect",
    "scout-dynamic-archetypes",
    "vendor-misc",
    "voter-dispatch-prep",
];

/// Vendors a `v1 vendor` row may name.
pub const TIMING_VENDORS_ALLOWED: [&str; 3] = ["codex", "cursor", "claude"];

/// Column count of every canonical `v1` ledger row.
pub const TIMING_ROW_COLUMNS: usize = 13;

/// Default outlier threshold in seconds when the environment names none.
pub const DEFAULT_OUTLIER_THRESHOLD_S: i64 = 14400;

/// Sentinel a rendered report emits when the ledger carries no step marks.
pub const REPORT_UNAVAILABLE: &str = "Timing report unavailable: no step marks in ledger";

/// One `v1 mark` row.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct TimingMark {
    /// Wall-clock second the mark was written.
    pub timestamp: i64,
    /// Skill that owns the mark.
    pub skill: String,
    /// Step label.
    pub step: String,
}

/// One `v1 vendor` row.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct VendorTask {
    /// Wall-clock second the row was written.
    pub timestamp: i64,
    /// Skill that owns the row.
    pub skill: String,
    /// Vendor that ran the task.
    pub vendor: String,
    /// Task-kind label.
    pub task_kind: String,
    /// Task start second.
    pub start: i64,
    /// Task end second.
    pub end: i64,
    /// Clamped task duration in seconds.
    pub duration: i64,
    /// Output artifact base name.
    pub output: String,
    /// Vendor exit code.
    pub exit_code: i64,
    /// Normalized completion status.
    pub status: String,
}

/// One `v1 round` row.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RoundRecord {
    /// Skill that owns the round.
    pub skill: String,
    /// Step label the round belongs to.
    pub step: String,
    /// Round number.
    pub round: i64,
    /// Round start second.
    pub start: i64,
    /// Round end second.
    pub end: i64,
    /// Clamped round duration in seconds.
    pub duration: i64,
    /// Accepted findings.
    pub accepted: i64,
    /// Rejected findings.
    pub rejected: i64,
    /// Out-of-scope findings, when the row recorded them.
    pub oos: Option<i64>,
}

/// Every row a ledger parse recovered, plus the operator warnings it raised.
#[derive(Clone, Debug, Default)]
pub struct LedgerRows {
    /// Step marks in ledger order.
    pub marks: Vec<TimingMark>,
    /// Vendor tasks in ledger order.
    pub vendors: Vec<VendorTask>,
    /// Review rounds in ledger order.
    pub rounds: Vec<RoundRecord>,
    /// Stderr warnings for rows that did not parse.
    pub warnings: Vec<String>,
}

/// One rendered per-step row of the timing report.
#[derive(Clone, Debug)]
pub struct StepRow {
    /// Skill that owns the step.
    pub skill: String,
    /// Step label.
    pub step: String,
    /// Step duration in seconds.
    pub duration_seconds: i64,
    /// Step duration rendered as `HH:MM:SS`.
    pub duration_hms: String,
    /// Whether the step exceeded the outlier threshold.
    pub outlier: bool,
    /// Review rounds that started inside the step window.
    pub rounds: Vec<RoundSummary>,
}

/// One review round attached to a rendered step row.
#[derive(Clone, Debug)]
pub struct RoundSummary {
    /// Round number.
    pub round: i64,
    /// Round duration in seconds.
    pub duration_seconds: i64,
    /// Accepted findings.
    pub accepted: i64,
    /// Rejected findings.
    pub rejected: i64,
    /// Out-of-scope findings, published only for `/design` rounds.
    pub oos: Option<i64>,
}

/// One vendor and task-kind average of the rendered report.
#[derive(Clone, Debug)]
pub struct VendorAverage {
    /// Vendor name.
    pub vendor: String,
    /// Task-kind label.
    pub task_kind: String,
    /// Completed sample count.
    pub samples: i64,
    /// Mean duration in seconds, rounded to three decimals.
    pub average_seconds: f64,
    /// Mean duration rendered as `HH:MM:SS`.
    pub average_hms: String,
    /// Shortest sample in seconds.
    pub min_seconds: i64,
    /// Longest sample in seconds.
    pub max_seconds: i64,
}

/// The whole machine payload a full timing report publishes.
#[derive(Clone, Debug, Default)]
pub struct TimingReportData {
    /// Per-step rows in report order.
    pub per_step: Vec<StepRow>,
    /// Total elapsed seconds across the driving skill.
    pub total_seconds: i64,
    /// Total elapsed time rendered as `HH:MM:SS`.
    pub total_hms: String,
    /// Vendor task averages in vendor then task-kind order.
    pub vendor_task_averages: Vec<VendorAverage>,
    /// Whether the ledger carried no step marks.
    pub empty: bool,
}

/// Replace the row separators a ledger field must never carry.
#[must_use]
pub fn sanitize(value: &str) -> String {
    value
        .replace('\t', "<NUL>")
        .replace('\n', "<NUL>")
        .replace('\r', "<NUL>")
}

/// Return whether `task_kind` matches the canonical `^[a-z][a-z0-9-]{0,63}$` shape.
#[must_use]
pub fn is_wellformed_task_kind(task_kind: &str) -> bool {
    let mut characters = task_kind.chars();
    let Some(first) = characters.next() else {
        return false;
    };
    if !first.is_ascii_lowercase() {
        return false;
    }
    task_kind.len() <= 64
        && characters.all(|character| character.is_ascii_lowercase() || character.is_ascii_digit() || character == '-')
}

/// Return whether `task_kind` is on the canonical allow-list.
#[must_use]
pub fn is_known_task_kind(task_kind: &str) -> bool {
    TIMING_TASK_KINDS_ALLOWED.contains(&task_kind)
}

/// Return whether `vendor` may appear in a `v1 vendor` row.
#[must_use]
pub fn is_known_vendor(vendor: &str) -> bool {
    TIMING_VENDORS_ALLOWED.contains(&vendor)
}

/// Normalize a caller-supplied vendor-task status, or return `None` when invalid.
#[must_use]
pub fn normalize_status(status: &str) -> Option<&'static str> {
    match status {
        "OK" | "complete" => Some("complete"),
        "ERROR" | "TIMEOUT" | "signal" => Some("signal"),
        "unknown" => Some("unknown"),
        _ => None,
    }
}

/// Render seconds as the report's `HH:MM:SS` clock text.
#[must_use]
pub fn hms(seconds: i64) -> String {
    let total = seconds.max(0);
    format!(
        "{:02}:{:02}:{:02}",
        total / 3600,
        (total % 3600) / 60,
        total % 60
    )
}

/// Render seconds as the report's one-decimal minute text.
#[must_use]
pub fn minutes(seconds: f64) -> String {
    format!("{:.1} min", seconds / 60.0)
}

/// Parse every canonical row of a timing ledger.
#[must_use]
pub fn parse_ledger(text: &str) -> LedgerRows {
    let mut rows = LedgerRows::default();
    for line in text.lines() {
        let columns: Vec<&str> = line.split('\t').collect();
        if columns.len() != TIMING_ROW_COLUMNS || columns[0] != "v1" {
            rows.warnings.push(format!(
                "timing report: WARNING: skipping malformed row with {} columns",
                columns.len()
            ));
            continue;
        }
        match columns[1] {
            "mark" => {
                let Some(timestamp) = parse_i64(columns[2]) else {
                    rows.warnings.push(malformed_warning());
                    continue;
                };
                rows.marks.push(TimingMark {
                    timestamp,
                    skill: columns[3].to_owned(),
                    step: columns[4].to_owned(),
                });
            }
            "vendor" => {
                let (
                    Some(timestamp),
                    Some(start),
                    Some(end),
                    Some(duration),
                    Some(exit_code),
                ) = (
                    parse_i64(columns[2]),
                    parse_i64(columns[7]),
                    parse_i64(columns[8]),
                    parse_i64(columns[9]),
                    parse_i64(columns[11]),
                )
                else {
                    rows.warnings.push(malformed_warning());
                    continue;
                };
                rows.vendors.push(VendorTask {
                    timestamp,
                    skill: columns[3].to_owned(),
                    vendor: columns[5].to_owned(),
                    task_kind: columns[6].to_owned(),
                    start,
                    end,
                    duration,
                    output: columns[10].to_owned(),
                    exit_code,
                    status: columns[12].to_owned(),
                });
            }
            "round" => {
                let (
                    Some(round),
                    Some(start),
                    Some(end),
                    Some(duration),
                    Some(accepted),
                    Some(rejected),
                ) = (
                    parse_i64(columns[5]),
                    parse_i64(columns[6]),
                    parse_i64(columns[7]),
                    parse_i64(columns[8]),
                    parse_i64(columns[9]),
                    parse_i64(columns[10]),
                )
                else {
                    rows.warnings.push(malformed_warning());
                    continue;
                };
                rows.rounds.push(RoundRecord {
                    skill: columns[3].to_owned(),
                    step: columns[4].to_owned(),
                    round,
                    start,
                    end,
                    duration,
                    accepted,
                    rejected,
                    oos: parse_unsigned(columns[11]),
                });
            }
            _ => {}
        }
    }
    rows
}

fn malformed_warning() -> String {
    format!("timing report: WARNING: skipping malformed row with {TIMING_ROW_COLUMNS} columns")
}

fn parse_i64(value: &str) -> Option<i64> {
    value.parse::<i64>().ok()
}

fn parse_unsigned(value: &str) -> Option<i64> {
    (!value.is_empty() && value.bytes().all(|byte| byte.is_ascii_digit()))
        .then(|| value.parse::<i64>().ok())
        .flatten()
}

/// Count prior attempts of one `(skill, round)` pair and return the next index.
#[must_use]
pub fn next_round_attempt(text: &str, skill: &str, round: i64) -> i64 {
    let sanitized = sanitize(skill);
    let wanted = round.to_string();
    let prior = text
        .lines()
        .filter(|line| {
            let columns: Vec<&str> = line.split('\t').collect();
            columns.len() == TIMING_ROW_COLUMNS
                && columns[0] == "v1"
                && columns[1] == "round"
                && columns[3] == sanitized
                && columns[5] == wanted
        })
        .count();
    i64::try_from(prior).unwrap_or(i64::MAX).saturating_add(1)
}

/// Build the tab-separated field list of a `v1 mark` row.
#[must_use]
pub fn mark_row(now: i64, skill: &str, step: &str) -> String {
    let mut fields = vec![
        "v1".to_owned(),
        "mark".to_owned(),
        now.to_string(),
        sanitize(skill),
        sanitize(step),
    ];
    fields.resize(TIMING_ROW_COLUMNS, "-".to_owned());
    fields.join("\t")
}

/// Build the tab-separated field list of a `v1 vendor` row.
#[must_use]
pub fn vendor_row(
    now: i64,
    skill: &str,
    vendor: &str,
    task_kind: &str,
    start: i64,
    end: i64,
    duration: i64,
    output_name: &str,
    exit_code: i64,
    status: &str,
) -> String {
    [
        "v1".to_owned(),
        "vendor".to_owned(),
        now.to_string(),
        sanitize(skill),
        "-".to_owned(),
        sanitize(vendor),
        sanitize(task_kind),
        start.to_string(),
        end.to_string(),
        duration.to_string(),
        sanitize(output_name),
        exit_code.to_string(),
        status.to_owned(),
    ]
    .join("\t")
}

/// Build the tab-separated field list of a `v1 round` row.
#[expect(
    clippy::too_many_arguments,
    reason = "one row writer per ledger schema keeps the column order in one place"
)]
#[must_use]
pub fn round_row(
    now: i64,
    skill: &str,
    step: &str,
    round: i64,
    start: i64,
    end: i64,
    duration: i64,
    accepted: i64,
    rejected: i64,
    oos: Option<i64>,
    attempt: i64,
) -> String {
    [
        "v1".to_owned(),
        "round".to_owned(),
        now.to_string(),
        sanitize(skill),
        sanitize(step),
        round.to_string(),
        start.to_string(),
        end.to_string(),
        duration.to_string(),
        accepted.to_string(),
        rejected.to_string(),
        oos.map_or_else(|| "-".to_owned(), |value| value.to_string()),
        attempt.to_string(),
    ]
    .join("\t")
}

/// Count completed vendor tasks per vendor at or after `start`.
#[must_use]
fn vendor_counts_since(rows: &LedgerRows, start: i64) -> [i64; 3] {
    let mut counts = [0_i64; 3];
    for row in &rows.vendors {
        if row.end < start {
            continue;
        }
        if let Some(index) = TIMING_VENDORS_ALLOWED
            .iter()
            .position(|vendor| *vendor == row.vendor)
        {
            counts[index] += 1;
        }
    }
    counts
}

/// Render the one-line `--summary` report.
#[must_use]
pub fn summary_line(rows: &LedgerRows, now: i64) -> String {
    let Some(first) = rows.marks.first() else {
        return REPORT_UNAVAILABLE.to_owned();
    };
    counted_line("Total", now - first.timestamp, vendor_counts_since(rows, first.timestamp))
}

/// Render the one-line `--terse` report for one skill.
#[must_use]
pub fn terse_line(rows: &LedgerRows, skill: &str, now: i64) -> String {
    let Some(last) = rows.marks.iter().rev().find(|mark| mark.skill == skill) else {
        return REPORT_UNAVAILABLE.to_owned();
    };
    counted_line(&last.step, now - last.timestamp, vendor_counts_since(rows, last.timestamp))
}

fn counted_line(label: &str, elapsed: i64, counts: [i64; 3]) -> String {
    format!(
        "{label}: elapsed={} vendor-tasks={} (codex={}, cursor={}, claude={})",
        hms(elapsed),
        counts[0] + counts[1] + counts[2],
        counts[0],
        counts[1],
        counts[2]
    )
}

/// Build the full timing report payload from parsed rows and an explicit `now`.
#[must_use]
pub fn build_report(rows: &LedgerRows, now: i64, threshold: i64) -> TimingReportData {
    if rows.marks.is_empty() {
        return TimingReportData {
            empty: true,
            ..TimingReportData::default()
        };
    }
    let implement: Vec<&TimingMark> = rows
        .marks
        .iter()
        .filter(|mark| mark.skill == "implement")
        .collect();
    let driving: Vec<&TimingMark> = if implement.is_empty() {
        rows.marks.iter().collect()
    } else {
        implement
    };
    let total = driving
        .last()
        .zip(driving.first())
        .map_or(0, |(last, first)| last.timestamp - first.timestamp);
    let last_event = rows
        .vendors
        .iter()
        .map(|vendor| vendor.timestamp)
        .fold(now, i64::max);
    let mut per_step: Vec<StepRow> = Vec::new();
    for (index, mark) in driving.iter().enumerate() {
        let end = driving
            .get(index + 1)
            .map_or(last_event, |next| next.timestamp);
        per_step.push(step_row(mark, end, threshold, rows));
        if mark.skill == "implement" {
            for child in ["design", "review"] {
                per_step.extend(child_steps(rows, child, mark.timestamp, end, now, threshold));
            }
        }
    }
    TimingReportData {
        per_step,
        total_seconds: total.max(0),
        total_hms: hms(total.max(0)),
        vendor_task_averages: vendor_averages(rows),
        empty: false,
    }
}

fn step_row(mark: &TimingMark, end: i64, threshold: i64, rows: &LedgerRows) -> StepRow {
    let duration = (end - mark.timestamp).max(0);
    StepRow {
        skill: mark.skill.clone(),
        step: mark.step.clone(),
        duration_seconds: duration,
        duration_hms: hms(duration),
        outlier: duration > threshold,
        rounds: rounds_for(rows, &mark.skill, &mark.step, mark.timestamp, end),
    }
}

fn child_steps(
    rows: &LedgerRows,
    skill: &str,
    start: i64,
    end: i64,
    now: i64,
    threshold: i64,
) -> Vec<StepRow> {
    let marks: Vec<&TimingMark> = rows
        .marks
        .iter()
        .filter(|mark| mark.skill == skill)
        .collect();
    let mut out = Vec::new();
    for (index, mark) in marks.iter().enumerate() {
        if !(start <= mark.timestamp && mark.timestamp < end) {
            continue;
        }
        let child_end = marks
            .get(index + 1)
            .map_or(now, |next| next.timestamp)
            .min(end);
        out.push(step_row(mark, child_end, threshold, rows));
    }
    out
}

fn rounds_for(
    rows: &LedgerRows,
    skill: &str,
    step: &str,
    start: i64,
    end: i64,
) -> Vec<RoundSummary> {
    let mut matched: Vec<(i64, &RoundRecord)> = Vec::new();
    for row in &rows.rounds {
        if row.skill != skill || row.step != step || !(start <= row.start && row.start < end) {
            continue;
        }
        match matched.iter_mut().find(|(key, _)| *key == row.round) {
            Some(entry) => entry.1 = row,
            None => matched.push((row.round, row)),
        }
    }
    matched.sort_by_key(|(key, _)| *key);
    matched
        .into_iter()
        .map(|(_, row)| RoundSummary {
            round: row.round,
            duration_seconds: row.duration,
            accepted: row.accepted,
            rejected: row.rejected,
            oos: if skill == "design" { row.oos } else { None },
        })
        .collect()
}

fn vendor_averages(rows: &LedgerRows) -> Vec<VendorAverage> {
    let mut buckets: Vec<((String, String), Vec<i64>)> = Vec::new();
    for row in &rows.vendors {
        if row.status != "complete" || row.exit_code != 0 {
            continue;
        }
        let key = (row.vendor.clone(), row.task_kind.clone());
        match buckets.iter_mut().find(|(existing, _)| *existing == key) {
            Some(entry) => entry.1.push(row.duration),
            None => buckets.push((key, vec![row.duration])),
        }
    }
    buckets.sort_by(|left, right| {
        vendor_order(&left.0.0)
            .cmp(&vendor_order(&right.0.0))
            .then_with(|| left.0.1.cmp(&right.0.1))
    });
    buckets
        .into_iter()
        .map(|((vendor, task_kind), values)| {
            let samples = i64::try_from(values.len()).unwrap_or(i64::MAX);
            let total: i64 = values.iter().sum();
            #[expect(
                clippy::cast_precision_loss,
                reason = "ledger seconds stay far below the f64 exact-integer bound"
            )]
            let average = total as f64 / values.len() as f64;
            VendorAverage {
                vendor,
                task_kind,
                samples,
                average_seconds: round_three(average),
                average_hms: hms(truncate_half_up(average)),
                min_seconds: values.iter().copied().min().unwrap_or(0),
                max_seconds: values.iter().copied().max().unwrap_or(0),
            }
        })
        .collect()
}

fn vendor_order(vendor: &str) -> usize {
    match vendor {
        "codex" => 1,
        "cursor" => 2,
        "claude" => 3,
        _ => 4,
    }
}

/// Round to three decimals with the ties-to-even rule Python's `round` uses.
fn round_three(value: f64) -> f64 {
    (value * 1000.0).round_ties_even() / 1000.0
}

#[expect(
    clippy::cast_possible_truncation,
    reason = "ledger averages stay far below the i64 bound"
)]
fn truncate_half_up(value: f64) -> i64 {
    (value + 0.5) as i64
}

/// Render the report payload as Python-compatible sorted-key JSON text.
#[must_use]
pub fn report_json(data: &TimingReportData) -> OrderedJson {
    if data.empty {
        return OrderedJson::Object(Vec::new());
    }
    OrderedJson::Object(vec![
        (
            "per_step".to_owned(),
            OrderedJson::Array(data.per_step.iter().map(step_json).collect()),
        ),
        ("total_hms".to_owned(), string_json(&data.total_hms)),
        ("total_seconds".to_owned(), integer_json(data.total_seconds)),
        (
            "vendor_task_averages".to_owned(),
            OrderedJson::Array(data.vendor_task_averages.iter().map(average_json).collect()),
        ),
    ])
}

fn step_json(row: &StepRow) -> OrderedJson {
    let mut members = vec![
        ("duration_hms".to_owned(), string_json(&row.duration_hms)),
        (
            "duration_seconds".to_owned(),
            integer_json(row.duration_seconds),
        ),
        ("outlier".to_owned(), OrderedJson::Bool(row.outlier)),
    ];
    if !row.rounds.is_empty() {
        members.push((
            "rounds".to_owned(),
            OrderedJson::Array(row.rounds.iter().map(round_json).collect()),
        ));
    }
    members.push(("skill".to_owned(), string_json(&row.skill)));
    members.push(("step".to_owned(), string_json(&row.step)));
    OrderedJson::Object(members)
}

fn round_json(row: &RoundSummary) -> OrderedJson {
    let mut members = vec![
        ("accepted".to_owned(), integer_json(row.accepted)),
        (
            "duration_seconds".to_owned(),
            integer_json(row.duration_seconds),
        ),
    ];
    if let Some(oos) = row.oos {
        members.push(("oos".to_owned(), integer_json(oos)));
    }
    members.push(("rejected".to_owned(), integer_json(row.rejected)));
    members.push(("round".to_owned(), integer_json(row.round)));
    OrderedJson::Object(members)
}

fn average_json(row: &VendorAverage) -> OrderedJson {
    OrderedJson::Object(vec![
        ("average_hms".to_owned(), string_json(&row.average_hms)),
        (
            "average_seconds".to_owned(),
            Number::from_f64(row.average_seconds)
                .map_or_else(|| integer_json(0), OrderedJson::Number),
        ),
        ("max_seconds".to_owned(), integer_json(row.max_seconds)),
        ("min_seconds".to_owned(), integer_json(row.min_seconds)),
        ("samples".to_owned(), integer_json(row.samples)),
        ("task_kind".to_owned(), string_json(&row.task_kind)),
        ("vendor".to_owned(), string_json(&row.vendor)),
    ])
}

fn string_json(value: &str) -> OrderedJson {
    OrderedJson::String(value.to_owned())
}

fn integer_json(value: i64) -> OrderedJson {
    OrderedJson::Number(Number::from(value))
}

/// Render the report payload as the operator-readable Markdown tables.
#[must_use]
pub fn report_markdown(data: &TimingReportData) -> String {
    let mut lines = vec![
        "## Per-Step Durations".to_owned(),
        String::new(),
        "| Skill | Step | Duration |".to_owned(),
        "| --- | --- | ---: |".to_owned(),
    ];
    for row in &data.per_step {
        let suffix = if row.outlier { " [OUTLIER]" } else { "" };
        lines.push(format!(
            "| {} | {} | {}{suffix} |",
            row.skill,
            row.step.replace('|', "\\|"),
            row.duration_hms
        ));
    }
    let total = if data.empty {
        "00:00:00"
    } else {
        &data.total_hms
    };
    lines.push(format!("| **Total** | | {total} |"));
    lines.extend([
        String::new(),
        "## Vendor Task Averages".to_owned(),
        String::new(),
        "| Vendor | Task kind | Samples | Average | Range |".to_owned(),
        "| --- | --- | ---: | ---: | --- |".to_owned(),
    ]);
    for row in &data.vendor_task_averages {
        #[expect(
            clippy::cast_precision_loss,
            reason = "ledger seconds stay far below the f64 exact-integer bound"
        )]
        let range = if row.samples == 1 {
            "(1 sample)".to_owned()
        } else {
            format!(
                "{}-{}",
                minutes(row.min_seconds as f64),
                minutes(row.max_seconds as f64)
            )
        };
        lines.push(format!(
            "| {} | {} | {} | {} | {range} |",
            row.vendor,
            row.task_kind,
            row.samples,
            minutes(row.average_seconds)
        ));
    }
    lines.join("\n")
}

/// Extract the progress-breadcrumb step token from a timing mark label.
#[must_use]
pub fn progress_step_from_label(label: &str) -> String {
    step_after_keyword(label)
        .or_else(|| bare_step_token(label))
        .unwrap_or_else(|| "?".to_owned())
}

fn step_after_keyword(label: &str) -> Option<String> {
    let lowered = label.to_ascii_lowercase();
    let mut search = 0;
    while let Some(offset) = lowered[search..].find("step") {
        let start = search + offset;
        search = start + 4;
        if start > 0 && is_word_byte(lowered.as_bytes()[start - 1]) {
            continue;
        }
        let rest = &label[start + 4..];
        let trimmed = rest.trim_start_matches([' ', '\t', '\n', '\r', '\u{0b}', '\u{0c}']);
        if trimmed.len() == rest.len() {
            continue;
        }
        if let Some(token) = leading_step_token(trimmed) {
            return Some(token);
        }
    }
    None
}

fn leading_step_token(text: &str) -> Option<String> {
    let bytes = text.as_bytes();
    let mut index = 0;
    while index < bytes.len() && bytes[index].is_ascii_digit() {
        index += 1;
    }
    if index == 0 {
        return None;
    }
    if index < bytes.len() && bytes[index] == b'.' {
        let mut cursor = index + 1;
        while cursor < bytes.len()
            && (bytes[cursor].is_ascii_digit() || bytes[cursor].is_ascii_lowercase())
        {
            cursor += 1;
        }
        if cursor > index + 1 {
            index = cursor;
        }
    }
    if index < bytes.len() && bytes[index].is_ascii_lowercase() {
        index += 1;
    }
    (index >= bytes.len() || !is_word_byte(bytes[index])).then(|| text[..index].to_owned())
}

fn bare_step_token(label: &str) -> Option<String> {
    let bytes = label.as_bytes();
    let mut start = 0;
    while start < bytes.len() {
        if (start > 0 && is_word_byte(bytes[start - 1])) || !bytes[start].is_ascii_digit() {
            start += 1;
            continue;
        }
        let mut index = start;
        while index < bytes.len() && bytes[index].is_ascii_digit() {
            index += 1;
        }
        if index >= bytes.len() || !bytes[index].is_ascii_lowercase() {
            start = index.max(start + 1);
            continue;
        }
        index += 1;
        if index < bytes.len() && bytes[index] == b'.' {
            let mut cursor = index + 1;
            while cursor < bytes.len()
                && (bytes[cursor].is_ascii_digit() || bytes[cursor].is_ascii_lowercase())
            {
                cursor += 1;
            }
            if cursor > index + 1 {
                index = cursor;
            }
        }
        if index >= bytes.len() || !is_word_byte(bytes[index]) {
            return Some(label[start..index].to_owned());
        }
        start = index;
    }
    None
}

const fn is_word_byte(byte: u8) -> bool {
    byte.is_ascii_alphanumeric() || byte == b'_'
}

#[cfg(test)]
mod tests {
    use super::{
        LedgerRows, TIMING_TASK_KINDS_ALLOWED, build_report, hms, is_wellformed_task_kind,
        mark_row, next_round_attempt, normalize_status, parse_ledger, progress_step_from_label,
        report_json, report_markdown, round_row, sanitize, summary_line, terse_line, vendor_row,
    };
    use crate::vendor::python_json_dumps;

    fn ledger(rows: &[String]) -> String {
        let mut text = rows.join("\n");
        text.push('\n');
        text
    }

    #[test]
    fn task_kind_allow_list_stays_sorted_and_unique() {
        let mut sorted = TIMING_TASK_KINDS_ALLOWED.to_vec();
        sorted.sort_unstable();
        sorted.dedup();
        assert_eq!(sorted.as_slice(), TIMING_TASK_KINDS_ALLOWED.as_slice());
    }

    #[test]
    fn row_writers_sanitize_separators_and_keep_the_column_count() {
        let row = mark_row(10, "implement", "Step 1\tnow");
        assert_eq!(row.split('\t').count(), 13);
        assert!(row.contains("Step 1<NUL>now"), "{row}");
        assert_eq!(sanitize("a\r\nb"), "a<NUL><NUL>b");
    }

    #[test]
    fn round_attempts_count_prior_rows_for_the_same_skill_and_round() {
        let text = ledger(&[
            round_row(1, "design", "step", 2, 0, 5, 5, 1, 0, Some(0), 1),
            round_row(2, "design", "step", 2, 6, 9, 3, 1, 0, Some(0), 2),
            round_row(3, "design", "step", 3, 6, 9, 3, 1, 0, Some(0), 1),
        ]);
        assert_eq!(next_round_attempt(&text, "design", 2), 3);
        assert_eq!(next_round_attempt(&text, "design", 3), 2);
        assert_eq!(next_round_attempt(&text, "implement", 2), 1);
    }

    #[test]
    fn malformed_rows_are_skipped_with_one_warning_each() {
        let rows = parse_ledger("v1\tmark\tnot-a-number\timplement\tstep\t-\t-\t-\t-\t-\t-\t-\t-\nshort\n");
        assert!(rows.marks.is_empty());
        assert_eq!(rows.warnings.len(), 2);
    }

    #[test]
    fn status_normalization_accepts_only_the_documented_vocabulary() {
        assert_eq!(normalize_status("OK"), Some("complete"));
        assert_eq!(normalize_status("TIMEOUT"), Some("signal"));
        assert_eq!(normalize_status("unknown"), Some("unknown"));
        assert_eq!(normalize_status("weird"), None);
        assert!(is_wellformed_task_kind("codex-review"));
        assert!(!is_wellformed_task_kind("Codex"));
        assert!(!is_wellformed_task_kind(""));
    }

    #[test]
    fn full_report_nests_child_steps_rounds_and_vendor_averages() {
        let text = ledger(&[
            mark_row(100, "implement", "Step 1"),
            mark_row(110, "design", "design Step 3"),
            round_row(115, "design", "design Step 3", 1, 111, 118, 7, 2, 1, Some(3), 1),
            mark_row(160, "implement", "Step 2"),
            vendor_row(150, "implement", "codex", "codex-review", 100, 130, 30, "out.txt", 0, "complete"),
            vendor_row(155, "implement", "codex", "codex-review", 100, 150, 50, "out.txt", 0, "complete"),
        ]);
        let rows = parse_ledger(&text);
        let data = build_report(&rows, 200, 14400);
        assert_eq!(data.total_seconds, 60);
        assert_eq!(data.per_step.len(), 3);
        assert_eq!(data.per_step[1].skill, "design");
        assert_eq!(data.per_step[1].rounds.len(), 1);
        assert_eq!(data.per_step[1].rounds[0].oos, Some(3));
        assert_eq!(data.vendor_task_averages.len(), 1);
        assert!((data.vendor_task_averages[0].average_seconds - 40.0).abs() < f64::EPSILON);
        let rendered = python_json_dumps(&report_json(&data)).expect("render report json");
        assert!(rendered.starts_with("{\"per_step\": ["), "{rendered}");
        assert!(rendered.contains("\"average_seconds\": 40.0"), "{rendered}");
        let markdown = report_markdown(&data);
        assert!(markdown.contains("| **Total** | | 00:01:00 |"), "{markdown}");
        assert!(markdown.contains("| codex | codex-review | 2 | 0.7 min | 0.5 min-0.8 min |"), "{markdown}");
    }

    #[test]
    fn outlier_flag_follows_the_supplied_threshold() {
        let text = ledger(&[
            mark_row(0, "implement", "Step 1"),
            mark_row(100, "implement", "Step 2"),
        ]);
        let rows = parse_ledger(&text);
        assert!(build_report(&rows, 120, 50).per_step[0].outlier);
        assert!(!build_report(&rows, 120, 500).per_step[0].outlier);
    }

    #[test]
    fn empty_ledger_reports_are_unavailable() {
        let rows = LedgerRows::default();
        assert!(build_report(&rows, 5, 10).empty);
        assert_eq!(summary_line(&rows, 5), super::REPORT_UNAVAILABLE);
        assert_eq!(terse_line(&rows, "implement", 5), super::REPORT_UNAVAILABLE);
        assert_eq!(
            python_json_dumps(&report_json(&build_report(&rows, 5, 10))).expect("render"),
            "{}"
        );
    }

    #[test]
    fn summary_and_terse_lines_count_vendor_tasks_by_end_time() {
        let text = ledger(&[
            mark_row(10, "implement", "Step 1"),
            vendor_row(30, "implement", "codex", "codex-review", 5, 9, 4, "a.txt", 0, "complete"),
            vendor_row(40, "implement", "cursor", "cursor-review", 12, 30, 18, "b.txt", 0, "complete"),
            mark_row(50, "design", "design Step 3"),
        ]);
        let rows = parse_ledger(&text);
        assert_eq!(
            summary_line(&rows, 70),
            "Total: elapsed=00:01:00 vendor-tasks=1 (codex=0, cursor=1, claude=0)"
        );
        assert_eq!(
            terse_line(&rows, "design", 70),
            "design Step 3: elapsed=00:00:20 vendor-tasks=0 (codex=0, cursor=0, claude=0)"
        );
    }

    #[test]
    fn hms_clamps_negative_elapsed_time() {
        assert_eq!(hms(-5), "00:00:00");
        assert_eq!(hms(3661), "01:01:01");
    }

    #[test]
    fn progress_step_tokens_match_the_python_label_patterns() {
        assert_eq!(progress_step_from_label("Step 5 — code review"), "5");
        assert_eq!(progress_step_from_label("design Step 3.5 — gate B"), "3.5");
        assert_eq!(progress_step_from_label("Step 7a — pre-ship"), "7a");
        assert_eq!(progress_step_from_label("2b entry"), "2b");
        assert_eq!(progress_step_from_label("no step here"), "?");
    }
}
