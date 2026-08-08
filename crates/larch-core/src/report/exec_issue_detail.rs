//! Shared exec-issue and warning detail parsing/rendering.
//!
//! Ports Python `larch.report.exec_issue_detail` except Claude assessment
//! subprocess launching. Callers inject an assessor into
//! [`render_issue_detail_block`] when live assessment is required.

use std::{
    collections::{BTreeMap, BTreeSet},
    error::Error,
    fmt, fs,
    path::Path,
};

use regex::Regex;
use serde_json::Value;
use sha2::{Digest, Sha256};

use crate::{SafeText, text::split_text_lines};

/// Categories whose rows count as executive issues.
pub const EXEC_CATEGORIES: &[&str] = &["Tool Failures", "External Reviewer Issues"];
/// Warning category heading.
pub const WARN_CATEGORY: &str = "Warnings";
/// Maximum display length for a collapsed issue row.
pub const MAX_DISPLAY_LEN: usize = 200;
/// Maximum dedupe-key length before truncation.
pub const MAX_DEDUPE_KEY_LEN: usize = 500;
/// Maximum rendered length of one returned materiality assessment.
pub const MAX_ASSESSMENT_LEN: usize = 260;
/// Seconds the exec-issue assessment subprocess may run.
pub const ASSESSMENT_TIMEOUT_SECONDS: u64 = 12;
/// Default model for the exec-issue materiality assessment.
pub const DEFAULT_ASSESSMENT_MODEL: &str = "claude-haiku-4-5";
/// Environment override for the exec-issue assessment model.
pub const ENV_EXEC_ISSUE_ASSESSMENT_MODEL: &str = "LARCH_EXEC_ISSUE_ASSESSMENT_MODEL";

static BOLD_BULLET_RE: std::sync::LazyLock<Regex> = std::sync::LazyLock::new(|| {
    Regex::new(r"^- \*\*([^*]+)\*\*:?(.*)$").expect("static bold bullet regex must compile")
});
static SECTION_HEADING_RE: std::sync::LazyLock<Regex> = std::sync::LazyLock::new(|| {
    Regex::new(r"(?m)^### (Tool Failures|External Reviewer Issues|Warnings)$")
        .expect("static section heading regex must compile")
});

/// One parsed bullet event before collapse.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct IssueEvent {
    /// Bold label when present.
    pub label: String,
    /// Description text after the label.
    pub description: String,
    /// Operator-facing display text.
    pub display_text: String,
    /// Stable dedupe key.
    pub dedupe_key: String,
}

/// A collapsed issue detail row with occurrence count.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct IssueDetail {
    /// Bold label when present.
    pub label: String,
    /// Description text after the label.
    pub description: String,
    /// Operator-facing display text.
    pub display_text: String,
    /// Occurrence count after collapse.
    pub count: usize,
}

/// Parsed executive and warning detail groups.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct IssueDetailGroups {
    /// Executive-issue rows.
    pub exec_issues: Vec<IssueDetail>,
    /// Warning rows.
    pub warnings: Vec<IssueDetail>,
}

/// Empty groups constant matching Python `EMPTY_GROUPS`.
pub static EMPTY_GROUPS: IssueDetailGroups = IssueDetailGroups {
    exec_issues: Vec::new(),
    warnings: Vec::new(),
};

/// Result of loading issue details from live markdown and/or ndjson.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct LoadResult {
    /// Parsed detail groups.
    pub groups: IssueDetailGroups,
    /// Whether listing degraded to category-string totals only.
    pub listing_degraded: bool,
    /// Degraded totals `(exec, warn)` when listing is degraded.
    pub degraded_totals: Option<(usize, usize)>,
}

/// Why [`LoadResult::new`] rejected an invariant.
#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub enum LoadResultErrorKind {
    /// `degraded_totals` set without `listing_degraded`.
    TotalsWithoutDegraded,
    /// Degraded listing with totals also carried detail rows.
    DegradedWithDetails,
}

/// Typed load-result invariant failure.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct LoadResultError {
    kind: LoadResultErrorKind,
}

impl LoadResultError {
    /// Return the failure kind.
    #[must_use]
    pub const fn kind(&self) -> LoadResultErrorKind {
        self.kind
    }

    /// Return the stable machine reason.
    #[must_use]
    pub const fn reason(&self) -> &'static str {
        match self.kind {
            LoadResultErrorKind::TotalsWithoutDegraded => "degraded-totals-without-flag",
            LoadResultErrorKind::DegradedWithDetails => "degraded-listing-with-details",
        }
    }
}

impl fmt::Display for LoadResultError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self.kind {
            LoadResultErrorKind::TotalsWithoutDegraded => {
                formatter.write_str("degraded_totals requires listing_degraded")
            }
            LoadResultErrorKind::DegradedWithDetails => {
                formatter.write_str("degraded listings with totals must not carry detail rows")
            }
        }
    }
}

impl Error for LoadResultError {}

impl LoadResult {
    /// Construct a load result, enforcing Python dataclass invariants.
    ///
    /// # Errors
    ///
    /// Returns [`LoadResultError`] when totals/details violate the degraded contract.
    pub fn new(
        groups: IssueDetailGroups,
        listing_degraded: bool,
        degraded_totals: Option<(usize, usize)>,
    ) -> Result<Self, LoadResultError> {
        if degraded_totals.is_some() && !listing_degraded {
            return Err(LoadResultError {
                kind: LoadResultErrorKind::TotalsWithoutDegraded,
            });
        }
        if listing_degraded
            && degraded_totals.is_some()
            && (!groups.exec_issues.is_empty() || !groups.warnings.is_empty())
        {
            return Err(LoadResultError {
                kind: LoadResultErrorKind::DegradedWithDetails,
            });
        }
        Ok(Self {
            groups,
            listing_degraded,
            degraded_totals,
        })
    }
}

/// Stable identity for an execution-issue ledger entry.
///
/// Matches Python `larch.report.run_log_batch.execution_issue_identity`.
#[must_use]
pub fn execution_issue_identity(category: &str, body: &str) -> String {
    let normalized = normalize_body_for_hash(body);
    let mut hasher = Sha256::new();
    hasher.update(category.as_bytes());
    hasher.update([0_u8]);
    hasher.update(normalized.as_bytes());
    hex_lower(&hasher.finalize())
}

/// Normalize one entry body before hashing it.
///
/// The ledger's identity ignores a leading `### ` heading and any blank
/// framing, so the same problem hashes alike whether it was recorded with its
/// section heading or without it.
#[must_use]
pub fn normalize_body_for_hash(body: &str) -> String {
    let mut lines: Vec<&str> = split_text_lines(body);
    if lines.first().is_some_and(|line| line.starts_with("### ")) {
        lines.remove(0);
    }
    while lines.first().is_some_and(|line| line.trim().is_empty()) {
        lines.remove(0);
    }
    while lines.last().is_some_and(|line| line.trim().is_empty()) {
        lines.pop();
    }
    lines.join("\n")
}

fn hex_lower(bytes: &[u8]) -> String {
    let mut out = String::with_capacity(bytes.len() * 2);
    for byte in bytes {
        let _ = fmt::Write::write_fmt(&mut out, format_args!("{byte:02x}"));
    }
    out
}

fn truncate(text: &str, limit: usize) -> String {
    let normalized = normalize_whitespace(text);
    if normalized.chars().count() <= limit {
        return normalized;
    }
    let keep = limit.saturating_sub(3);
    let mut out: String = normalized.chars().take(keep).collect();
    while out.ends_with(|ch: char| ch.is_whitespace()) {
        out.pop();
    }
    out.push_str("...");
    out
}

fn normalize_whitespace(text: &str) -> String {
    text.split_whitespace().collect::<Vec<_>>().join(" ")
}

fn redact_outbound(text: &str) -> String {
    if text.is_empty() {
        return String::new();
    }
    let ends_with_newline = text.ends_with('\n');
    // Python `redact` appends a trailing newline for non-empty text; outbound
    // then restores the caller's newline intent.
    let mut scrubbed = SafeText::from_untrusted(text).to_string();
    if !scrubbed.is_empty() && !scrubbed.ends_with('\n') {
        scrubbed.push('\n');
    }
    if ends_with_newline {
        scrubbed
    } else {
        scrubbed.trim_end_matches('\n').to_owned()
    }
}

/// Redact and bound one issue-detail string for an outbound assessment prompt.
#[must_use]
pub fn assessment_prompt_text(raw: &str) -> String {
    truncate(&redact_outbound(raw), MAX_DISPLAY_LEN)
}

/// Bound one returned assessment sentence to its rendered length.
#[must_use]
pub fn assessment_sentence(raw: &str) -> String {
    truncate(raw, MAX_ASSESSMENT_LEN)
}

fn display_from_raw(raw: &str) -> String {
    truncate(&redact_outbound(raw), MAX_DISPLAY_LEN)
}

fn dedupe_key_from_body(body: &str) -> String {
    let normalized = normalize_whitespace(body.trim());
    if normalized.chars().count() <= MAX_DEDUPE_KEY_LEN {
        return normalized;
    }
    let keep = MAX_DEDUPE_KEY_LEN.saturating_sub(3);
    let mut out: String = normalized.chars().take(keep).collect();
    while out.ends_with(|ch: char| ch.is_whitespace()) {
        out.pop();
    }
    out.push_str("...");
    out
}

fn dedupe_key_from_raw(raw: &str) -> String {
    dedupe_key_from_body(&redact_outbound(raw))
}

fn is_exec_category(heading: &str) -> bool {
    EXEC_CATEGORIES.contains(&heading)
}

fn split_issue_section_lines(text: &str) -> (Vec<String>, Vec<String>) {
    let mut exec_lines = Vec::new();
    let mut warn_lines = Vec::new();
    let mut section = Section::None;
    for line in split_text_lines(text) {
        if let Some(heading) = line.strip_prefix("### ") {
            let heading = heading.trim();
            if is_exec_category(heading) {
                section = Section::Exec;
            } else if heading == WARN_CATEGORY {
                section = Section::Warn;
            } else {
                section = Section::None;
            }
            continue;
        }
        // Python keeps fence lines inside the active section so the later
        // fence-aware bullet parser sees matching open/close markers.
        match section {
            Section::Exec => exec_lines.push(line.to_owned()),
            Section::Warn => warn_lines.push(line.to_owned()),
            Section::None => {}
        }
    }
    (exec_lines, warn_lines)
}

#[derive(Clone, Copy)]
enum Section {
    None,
    Exec,
    Warn,
}

fn parse_bullet_line(line: &str) -> Option<IssueEvent> {
    if !line.starts_with("- ") {
        return None;
    }
    if let Some(captures) = BOLD_BULLET_RE.captures(line) {
        let mut label = captures
            .get(1)
            .map(|m| m.as_str().trim().trim_end_matches(':').trim())
            .unwrap_or_default()
            .to_owned();
        let mut description = captures
            .get(2)
            .map(|m| m.as_str().trim())
            .unwrap_or_default()
            .to_owned();
        if description.starts_with(':') {
            description = description[1..].trim().to_owned();
        }
        if label.is_empty() && description.is_empty() {
            return None;
        }
        let raw_display = if !label.is_empty() && !description.is_empty() {
            format!("{label}: {description}")
        } else if label.is_empty() {
            description.clone()
        } else {
            label.clone()
        };
        let display_text = display_from_raw(&raw_display);
        let description = if description.is_empty() {
            String::new()
        } else {
            display_from_raw(&description)
        };
        return Some(IssueEvent {
            label: std::mem::take(&mut label),
            description,
            display_text,
            dedupe_key: dedupe_key_from_raw(&raw_display),
        });
    }
    let body = line[2..].trim();
    if body.is_empty() {
        return None;
    }
    let display_text = display_from_raw(body);
    Some(IssueEvent {
        label: String::new(),
        description: display_text.clone(),
        display_text,
        dedupe_key: dedupe_key_from_raw(body),
    })
}

fn parse_section_events(section_text: &str) -> Vec<IssueEvent> {
    let mut events = Vec::new();
    let mut in_fence = false;
    for line in split_text_lines(section_text) {
        if line.trim_start().starts_with("```") {
            in_fence = !in_fence;
            continue;
        }
        if in_fence {
            continue;
        }
        if let Some(event) = parse_bullet_line(line) {
            events.push(event);
        }
    }
    events
}

fn collapse_events(events: Vec<IssueEvent>) -> Vec<IssueDetail> {
    let mut order = Vec::new();
    let mut values: BTreeMap<String, IssueDetail> = BTreeMap::new();
    for event in events {
        if let Some(existing) = values.get_mut(&event.dedupe_key) {
            existing.count += 1;
        } else {
            order.push(event.dedupe_key.clone());
            values.insert(
                event.dedupe_key.clone(),
                IssueDetail {
                    label: event.label,
                    description: event.description,
                    display_text: event.display_text,
                    count: 1,
                },
            );
        }
    }
    order
        .into_iter()
        .filter_map(|key| values.remove(&key))
        .collect()
}

/// Parse markdown execution-issue sections into collapsed detail groups.
#[must_use]
pub fn parse_markdown_execution_issues(text: &str) -> IssueDetailGroups {
    let (exec_lines, warn_lines) = split_issue_section_lines(text);
    IssueDetailGroups {
        exec_issues: collapse_events(parse_section_events(&exec_lines.join("\n"))),
        warnings: collapse_events(parse_section_events(&warn_lines.join("\n"))),
    }
}

fn first_nonempty_line(text: &str) -> String {
    split_text_lines(text)
        .into_iter()
        .map(str::trim)
        .find(|line| !line.is_empty())
        .unwrap_or_default()
        .to_owned()
}

fn fallback_event(body: &str, category: &str) -> IssueEvent {
    let raw_display = {
        let first = first_nonempty_line(body);
        if first.is_empty() {
            category.to_owned()
        } else {
            first
        }
    };
    let display_text = display_from_raw(&raw_display);
    IssueEvent {
        label: String::new(),
        description: display_text.clone(),
        display_text,
        dedupe_key: dedupe_key_from_body(body),
    }
}

fn events_from_structured_body(body: &str, category: &str) -> Vec<IssueEvent> {
    let events = parse_section_events(body);
    if events.is_empty() {
        vec![fallback_event(body, category)]
    } else {
        events
    }
}

/// Return dedupe keys for a structured issue body.
#[must_use]
pub fn structured_body_dedupe_keys(body: &str, category: &str) -> BTreeSet<String> {
    events_from_structured_body(body, category)
        .into_iter()
        .map(|event| event.dedupe_key)
        .collect()
}

fn legacy_category_string_totals(body_text: &str) -> (usize, usize) {
    let exec_n = body_text.matches("\"category\":\"Tool Failures\"").count()
        + body_text
            .matches("\"category\":\"External Reviewer Issues\"")
            .count();
    let warn_n = body_text.matches("\"category\":\"Warnings\"").count();
    (exec_n, warn_n)
}

fn parse_ndjson_structured_rows(rows: &[Value]) -> IssueDetailGroups {
    let mut active_rows: Vec<Value> = Vec::new();
    for source_row in rows {
        let Some(object) = source_row.as_object() else {
            continue;
        };
        if object.get("event").and_then(Value::as_str) == Some("resolved") {
            let resolved: BTreeSet<String> = object
                .get("issue_ids")
                .and_then(Value::as_array)
                .into_iter()
                .flatten()
                .filter_map(Value::as_str)
                .map(str::to_owned)
                .collect();
            active_rows.retain(|active| {
                active
                    .get("issue_id")
                    .and_then(Value::as_str)
                    .is_none_or(|issue_id| !resolved.contains(issue_id))
            });
            continue;
        }
        let mut active_row = source_row.clone();
        if let (Some(category), Some(body)) = (
            object.get("category").and_then(Value::as_str),
            object.get("body").and_then(Value::as_str),
        ) && !object.get("issue_id").is_some_and(Value::is_string)
            && let Some(map) = active_row.as_object_mut()
        {
            map.insert(
                "issue_id".to_owned(),
                Value::String(execution_issue_identity(category, body)),
            );
        }
        active_rows.push(active_row);
    }

    let mut exec_events = Vec::new();
    let mut warn_events = Vec::new();
    for row in &active_rows {
        let category = row
            .get("category")
            .and_then(Value::as_str)
            .unwrap_or_default();
        let body = row.get("body").and_then(Value::as_str).unwrap_or_default();
        if is_exec_category(category) {
            exec_events.extend(events_from_structured_body(body, category));
        } else if category == WARN_CATEGORY {
            warn_events.extend(events_from_structured_body(body, category));
        }
    }
    IssueDetailGroups {
        exec_issues: collapse_events(exec_events),
        warnings: collapse_events(warn_events),
    }
}

fn is_structured_row(row: &Value) -> bool {
    row.get("category").is_some_and(Value::is_string)
        || row.get("event").and_then(Value::as_str) == Some("resolved")
}

fn read_text_replace(path: &Path) -> String {
    fs::read(path).map_or_else(
        |_| String::new(),
        |bytes| String::from_utf8_lossy(&bytes).into_owned(),
    )
}

fn parse_ndjson_legacy(path: &Path) -> LoadResult {
    let text = read_text_replace(path);
    let mut parsed: Vec<Option<Value>> = Vec::new();
    for raw in split_text_lines(&text) {
        if raw.trim().is_empty() {
            continue;
        }
        match serde_json::from_str::<Value>(raw) {
            Ok(value) => parsed.push(Some(value)),
            Err(_) => parsed.push(None),
        }
    }
    let dict_rows: Vec<Value> = parsed
        .iter()
        .filter_map(|row| row.as_ref())
        .filter(|row| row.is_object())
        .cloned()
        .collect();
    let all_dicts = !parsed.is_empty() && dict_rows.len() == parsed.len();
    let all_structured = !dict_rows.is_empty() && dict_rows.iter().all(is_structured_row);
    let structured_rows: Vec<Value> = dict_rows
        .iter()
        .filter(|row| is_structured_row(row))
        .cloned()
        .collect();
    if all_dicts && all_structured {
        return LoadResult {
            groups: parse_ndjson_structured_rows(&dict_rows),
            listing_degraded: false,
            degraded_totals: None,
        };
    }
    let body_parts: Vec<String> = parsed
        .iter()
        .filter_map(|row| row.as_ref())
        .filter_map(|row| row.as_object())
        .map(|row| {
            row.get("body")
                .map(|body| match body {
                    Value::String(text) => text.clone(),
                    other => other.to_string(),
                })
                .unwrap_or_default()
        })
        .collect();
    let body_text = body_parts.join("\n");
    if SECTION_HEADING_RE.is_match(&body_text) {
        return LoadResult {
            groups: parse_markdown_execution_issues(&body_text),
            listing_degraded: false,
            degraded_totals: None,
        };
    }
    if !structured_rows.is_empty() {
        return LoadResult {
            groups: parse_ndjson_structured_rows(&structured_rows),
            listing_degraded: false,
            degraded_totals: None,
        };
    }
    LoadResult {
        groups: IssueDetailGroups::default(),
        listing_degraded: true,
        degraded_totals: Some(legacy_category_string_totals(&body_text)),
    }
}

fn merge_details(first: &[IssueDetail], second: &[IssueDetail]) -> Vec<IssueDetail> {
    let mut order = Vec::new();
    let mut values: BTreeMap<String, IssueDetail> = BTreeMap::new();
    for detail in first.iter().chain(second.iter()) {
        if let Some(existing) = values.get_mut(&detail.display_text) {
            if existing.label.is_empty() {
                existing.label.clone_from(&detail.label);
            }
            if existing.description.is_empty() {
                existing.description.clone_from(&detail.description);
            }
            existing.count = existing.count.max(detail.count);
        } else {
            order.push(detail.display_text.clone());
            values.insert(detail.display_text.clone(), detail.clone());
        }
    }
    order
        .into_iter()
        .filter_map(|key| values.remove(&key))
        .collect()
}

fn merge_load_results(first: LoadResult, second: LoadResult) -> LoadResult {
    if first.listing_degraded && second.listing_degraded {
        let (first_exec, first_warn) = first.degraded_totals.unwrap_or((0, 0));
        let (second_exec, second_warn) = second.degraded_totals.unwrap_or((0, 0));
        return LoadResult {
            groups: IssueDetailGroups::default(),
            listing_degraded: true,
            degraded_totals: Some((first_exec + second_exec, first_warn + second_warn)),
        };
    }
    if first.listing_degraded {
        return second;
    }
    if second.listing_degraded {
        return first;
    }
    LoadResult {
        groups: IssueDetailGroups {
            exec_issues: merge_details(&first.groups.exec_issues, &second.groups.exec_issues),
            warnings: merge_details(&first.groups.warnings, &second.groups.warnings),
        },
        listing_degraded: false,
        degraded_totals: None,
    }
}

fn read_live_markdown(tmpdir: &Path) -> Option<LoadResult> {
    let issue_log = tmpdir.join("execution-issues.md");
    let metadata = fs::metadata(&issue_log).ok()?;
    if !metadata.is_file() || metadata.len() == 0 {
        return None;
    }
    let text = read_text_replace(&issue_log);
    Some(LoadResult {
        groups: parse_markdown_execution_issues(&text),
        listing_degraded: false,
        degraded_totals: None,
    })
}

/// Load issue-detail groups from live markdown and optional run-dir ndjson.
#[must_use]
pub fn load_issue_detail_groups(
    tmpdir: &Path,
    run_dir: Option<&Path>,
    prefer_run_dir: bool,
) -> LoadResult {
    let live_result = read_live_markdown(tmpdir);
    if prefer_run_dir && let Some(run_dir) = run_dir {
        let ndjson = run_dir.join("execution-issues.ndjson");
        if ndjson.is_file() {
            let run_result = parse_ndjson_legacy(&ndjson);
            return match live_result {
                Some(live) => merge_load_results(run_result, live),
                None => run_result,
            };
        }
    }
    if let Some(live) = live_result {
        return live;
    }
    if let Some(run_dir) = run_dir {
        let ndjson = run_dir.join("execution-issues.ndjson");
        if ndjson.is_file() {
            return parse_ndjson_legacy(&ndjson);
        }
    }
    LoadResult {
        groups: IssueDetailGroups::default(),
        listing_degraded: false,
        degraded_totals: None,
    }
}

/// Count executive and warning occurrences in detail groups.
#[must_use]
pub fn count_issue_groups(groups: &IssueDetailGroups) -> (usize, usize) {
    (
        groups.exec_issues.iter().map(|detail| detail.count).sum(),
        groups.warnings.iter().map(|detail| detail.count).sum(),
    )
}

/// Count executive and warning occurrences from a load result.
#[must_use]
pub fn count_load_result(load_result: &LoadResult) -> (usize, usize) {
    if load_result.listing_degraded
        && let Some(totals) = load_result.degraded_totals
    {
        return totals;
    }
    count_issue_groups(&load_result.groups)
}

fn render_category(
    title: &str,
    total: usize,
    details: &[IssueDetail],
    assessments: &BTreeMap<String, String>,
) -> Vec<String> {
    let mut lines = vec![format!("{title} ({total}):")];
    for (index, detail) in details.iter().enumerate() {
        let suffix = if detail.count > 1 {
            format!(" ×{}", detail.count)
        } else {
            String::new()
        };
        lines.push(format!("  {}. {}{suffix}", index + 1, detail.display_text));
        if let Some(assessment) = assessments.get(&index.to_string()) {
            let cleaned = assessment.trim();
            if !cleaned.is_empty() {
                lines.push(format!("    {cleaned}"));
            }
        }
    }
    lines
}

/// Render the executive issue-detail Markdown block.
///
/// When `assessor` is `Some`, it is invoked once per non-empty category with
/// the category title and detail rows. When `None`, assessment lines are
/// omitted (Python `assess=False`).
#[must_use]
pub fn render_issue_detail_block<F>(load_result: &LoadResult, mut assessor: Option<F>) -> String
where
    F: FnMut(&str, &[IssueDetail]) -> BTreeMap<String, String>,
{
    let (exec_total, warning_total) = count_load_result(load_result);
    let groups = &load_result.groups;
    if exec_total == 0
        && warning_total == 0
        && groups.exec_issues.is_empty()
        && groups.warnings.is_empty()
    {
        return String::new();
    }
    let mut lines = vec!["## Exec Issues and Warnings".to_owned()];
    if load_result.listing_degraded && groups.exec_issues.is_empty() && groups.warnings.is_empty() {
        lines.push(format!("Exec Issues ({exec_total}):"));
        lines.push(format!("Warnings ({warning_total}):"));
        let joined = format!("{}\n", lines.join("\n").trim_end());
        return redact_outbound(&joined);
    }
    let exec_assessments = match (&mut assessor, groups.exec_issues.is_empty()) {
        (Some(assess), false) => assess("Exec Issues", &groups.exec_issues),
        _ => BTreeMap::new(),
    };
    let warn_assessments = match (&mut assessor, groups.warnings.is_empty()) {
        (Some(assess), false) => assess("Warnings", &groups.warnings),
        _ => BTreeMap::new(),
    };
    lines.extend(render_category(
        "Exec Issues",
        exec_total,
        &groups.exec_issues,
        &exec_assessments,
    ));
    lines.extend(render_category(
        "Warnings",
        warning_total,
        &groups.warnings,
        &warn_assessments,
    ));
    let joined = format!("{}\n", lines.join("\n").trim_end());
    redact_outbound(&joined)
}

/// Build the issue-detail section with an injected assessor.
///
/// Library callers without Claude assessment pass a no-op assessor or use
/// [`render_issue_detail_block`] with `None`.
#[must_use]
pub fn build_issue_detail_section<F>(load_result: &LoadResult, assessor: F) -> String
where
    F: FnMut(&str, &[IssueDetail]) -> BTreeMap<String, String>,
{
    render_issue_detail_block(load_result, Some(assessor))
}

#[cfg(test)]
mod tests {
    use super::{
        IssueDetail, IssueDetailGroups, LoadResult, MAX_DISPLAY_LEN, count_issue_groups,
        count_load_result, execution_issue_identity, load_issue_detail_groups,
        parse_markdown_execution_issues, render_issue_detail_block, structured_body_dedupe_keys,
    };
    use serde_json::json;
    use std::{collections::BTreeMap, fs};
    use tempfile::tempdir;

    #[test]
    fn parses_markdown_sections_fence_aware() {
        let groups = parse_markdown_execution_issues(
            "### Tool Failures\n\
             - **lint**: drift\n\
             ```text\n\
             - hidden\n\
             ```\n\
             ### Notes\n\
             - ignored\n\
             ### Warnings\n\
             - plain warning\n",
        );
        assert_eq!(count_issue_groups(&groups), (1, 1));
        assert_eq!(groups.exec_issues[0].display_text, "lint: drift");
        assert_eq!(groups.warnings[0].display_text, "plain warning");
    }

    #[test]
    fn section_heading_inside_open_fence_is_still_boundary_like_python() {
        // Python section splitter treats `### Warnings` as a heading even inside
        // an open fence; bullets after that heading become warnings.
        let result = LoadResult {
            groups: parse_markdown_execution_issues(
                "### Tool Failures\n- exec1\n```\nlog line\n### Warnings\n- warn1\n",
            ),
            listing_degraded: false,
            degraded_totals: None,
        };
        assert_eq!(count_load_result(&result), (1, 1));
        let block = render_issue_detail_block(
            &result,
            None::<fn(&str, &[IssueDetail]) -> BTreeMap<String, String>>,
        );
        assert!(block.contains("1. exec1"));
        assert!(block.contains("1. warn1"));
    }

    #[test]
    fn untrusted_fenced_text_cannot_inject_bullets_while_fence_stays_open() {
        // Bullets inside an open fence are ignored by the event parser.
        let groups = parse_markdown_execution_issues(
            "### Tool Failures\n\
             - real failure\n\
             ```\n\
             - hostile fenced bullet\n\
             ## not a section heading\n\
             - still fenced\n\
             ```\n\
             - after fence still exec\n\
             ### Warnings\n\
             - real warning\n",
        );
        assert_eq!(count_issue_groups(&groups), (2, 1));
        assert!(
            !groups
                .exec_issues
                .iter()
                .chain(groups.warnings.iter())
                .any(|detail| detail.display_text.contains("hostile fenced bullet"))
        );
        let block = render_issue_detail_block(
            &LoadResult {
                groups,
                listing_degraded: false,
                degraded_totals: None,
            },
            None::<fn(&str, &[IssueDetail]) -> BTreeMap<String, String>>,
        );
        assert!(!block.contains("hostile fenced bullet"));
        assert!(block.contains("after fence still exec"));
        assert!(block.contains("real warning"));
    }

    #[test]
    fn bold_suffix_duplicate_collapse() {
        let result = LoadResult {
            groups: parse_markdown_execution_issues(
                "### Warnings\n\
                 - **lint**: drift\n\
                 - **lint**: drift\n\
                 - **lint**: timeout\n",
            ),
            listing_degraded: false,
            degraded_totals: None,
        };
        assert_eq!(count_load_result(&result), (0, 3));
        let block = render_issue_detail_block(
            &result,
            None::<fn(&str, &[IssueDetail]) -> BTreeMap<String, String>>,
        );
        assert!(block.contains("Warnings (3):"));
        assert!(block.contains("1. lint: drift ×2"));
        assert!(block.contains("2. lint: timeout"));
    }

    #[test]
    fn render_excludes_fenced_diagnostics_and_truncates() {
        let long_text = "x".repeat(MAX_DISPLAY_LEN + 30);
        let result = LoadResult {
            groups: parse_markdown_execution_issues(&format!(
                "### Tool Failures\n- {long_text}\n```\n- fenced secret diagnostic\n```\n"
            )),
            listing_degraded: false,
            degraded_totals: None,
        };
        assert!(result.groups.exec_issues[0].display_text.chars().count() <= MAX_DISPLAY_LEN);
        let block = render_issue_detail_block(
            &result,
            None::<fn(&str, &[IssueDetail]) -> BTreeMap<String, String>>,
        );
        assert!(!block.contains("fenced secret diagnostic"));
    }

    #[test]
    fn load_structured_ndjson_and_prefer_merge() {
        let dir = tempdir().unwrap();
        let run_dir = dir.path().join("run");
        fs::create_dir_all(&run_dir).unwrap();
        fs::write(
            dir.path().join("execution-issues.md"),
            "### Tool Failures\n- committed failure\n- post-flush failure\n### Warnings\n- live warning\n",
        )
        .unwrap();
        fs::write(
            run_dir.join("execution-issues.ndjson"),
            format!(
                "{}\n",
                json!({"category":"Tool Failures","body":"- committed failure\n"})
            ),
        )
        .unwrap();
        let result = load_issue_detail_groups(dir.path(), Some(&run_dir), true);
        assert_eq!(count_load_result(&result), (2, 1));
        assert_eq!(
            result
                .groups
                .exec_issues
                .iter()
                .map(|detail| detail.display_text.as_str())
                .collect::<Vec<_>>(),
            vec!["committed failure", "post-flush failure"]
        );
    }

    #[test]
    fn resolution_event_hides_earlier_ndjson_issue() {
        let dir = tempdir().unwrap();
        let run_dir = dir.path().join("run");
        fs::create_dir_all(&run_dir).unwrap();
        let body = "- transient blocker\n  with diagnostic context\n";
        let issue_id = execution_issue_identity("Tool Failures", body);
        let records = [
            json!({"category":"Tool Failures","body": body}),
            json!({"event":"resolved","issue_ids":[issue_id],"resolution":"recovered"}),
            json!({"category":"Tool Failures","body": body}),
        ];
        let text = records
            .iter()
            .map(std::string::ToString::to_string)
            .collect::<Vec<_>>()
            .join("\n")
            + "\n";
        fs::write(run_dir.join("execution-issues.ndjson"), text).unwrap();
        let result = load_issue_detail_groups(dir.path(), Some(&run_dir), false);
        assert_eq!(count_load_result(&result), (1, 0));
    }

    #[test]
    fn legacy_string_count_only_fallback() {
        let dir = tempdir().unwrap();
        let run_dir = dir.path().join("run");
        fs::create_dir_all(&run_dir).unwrap();
        let body = "{\"category\":\"Tool Failures\"}\n{\"category\":\"External Reviewer Issues\"}\n{\"category\":\"Warnings\"}";
        let rows = [json!("legacy"), json!({"body": body})];
        let text = rows
            .iter()
            .map(std::string::ToString::to_string)
            .collect::<Vec<_>>()
            .join("\n")
            + "\n";
        fs::write(run_dir.join("execution-issues.ndjson"), text).unwrap();
        let result = load_issue_detail_groups(dir.path(), Some(&run_dir), false);
        let block =
            render_issue_detail_block(&result, Some(|_: &str, _: &[IssueDetail]| BTreeMap::new()));
        assert!(result.listing_degraded);
        assert_eq!(result.degraded_totals, Some((2, 1)));
        assert!(block.contains("Exec Issues (2):"));
        assert!(block.contains("Warnings (1):"));
        assert!(!block.contains("  1."));
    }

    #[test]
    fn render_attaches_injected_assessments() {
        let groups = IssueDetailGroups {
            exec_issues: vec![IssueDetail {
                label: "step".into(),
                description: "failed".into(),
                display_text: "step: failed".into(),
                count: 1,
            }],
            warnings: Vec::new(),
        };
        let result = LoadResult {
            groups,
            listing_degraded: false,
            degraded_totals: None,
        };
        let block = render_issue_detail_block(
            &result,
            Some(|_: &str, _: &[IssueDetail]| {
                BTreeMap::from([(
                    "0".to_owned(),
                    "This may block operators until resolved.".to_owned(),
                )])
            }),
        );
        assert!(block.contains("    This may block operators until resolved."));
        let silent = render_issue_detail_block(
            &result,
            None::<fn(&str, &[IssueDetail]) -> BTreeMap<String, String>>,
        );
        assert!(!silent.contains("This may block operators"));
    }

    #[test]
    fn render_redacts_outbound_secret() {
        let raw_secret = format!("sk-{}", "b".repeat(32));
        let groups = IssueDetailGroups {
            exec_issues: Vec::new(),
            warnings: vec![IssueDetail {
                label: String::new(),
                description: raw_secret.clone(),
                display_text: raw_secret.clone(),
                count: 1,
            }],
        };
        let block = render_issue_detail_block(
            &LoadResult {
                groups,
                listing_degraded: false,
                degraded_totals: None,
            },
            None::<fn(&str, &[IssueDetail]) -> BTreeMap<String, String>>,
        );
        assert!(!block.contains(&raw_secret));
        assert!(block.contains("<REDACTED-TOKEN>"));
    }

    #[test]
    fn structured_body_dedupe_keys_cover_bullets() {
        let keys = structured_body_dedupe_keys("- a\n- **step**: b\n", "Tool Failures");
        assert_eq!(keys.len(), 2);
    }

    #[test]
    fn execution_issue_identity_matches_python_fixture() {
        let body = "- transient blocker\n  with diagnostic context\n";
        assert_eq!(
            execution_issue_identity("Tool Failures", body),
            "79bc13c31a8b4d84808d86972544c0f219da8343098669710d9a0216453c4cf3"
        );
    }

    #[test]
    fn render_matches_python_fixture_bytes() {
        let groups = parse_markdown_execution_issues(
            "### Tool Failures\n- **lint**: drift\n```text\n- hidden\n```\n### Warnings\n- plain warning\n",
        );
        let block = render_issue_detail_block(
            &LoadResult {
                groups,
                listing_degraded: false,
                degraded_totals: None,
            },
            None::<fn(&str, &[IssueDetail]) -> BTreeMap<String, String>>,
        );
        assert_eq!(
            block,
            "## Exec Issues and Warnings\nExec Issues (1):\n  1. lint: drift\nWarnings (1):\n  1. plain warning\n"
        );
    }
}
