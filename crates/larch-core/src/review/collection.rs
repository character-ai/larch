use std::{
    collections::{BTreeMap, BTreeSet},
    fmt::Write as _,
};

use serde_json::Value;

use super::{
    pipeline::{normalize_output_base, parse_legacy_collector_blocks},
    types::FOCUS_AREA_VALUES,
};
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct CollectedFinding {
    pub title: String,
    pub label: String,
    pub body: String,
}
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct CollectionRender {
    pub findings: String,
    pub oos: String,
    pub findings_count: usize,
    pub oos_count: usize,
}
#[must_use]
pub fn has_no_findings_sentinel(text: &str) -> bool {
    let lines = crate::split_text_lines(text);
    if lines.iter().any(|line| line.trim() == "NO_ISSUES_FOUND") {
        return true;
    }
    let trimmed = text.trim();
    if json_no_issues(trimmed) {
        return true;
    }
    lines.iter().any(|line| json_no_issues(line.trim()))
}

fn json_no_issues(text: &str) -> bool {
    serde_json::from_str::<Value>(text).is_ok_and(|value| {
        value
            .as_object()
            .and_then(|object| object.get("no_issues_found"))
            .is_some_and(Value::is_boolean)
            && value
                .as_object()
                .and_then(|object| object.get("no_issues_found"))
                == Some(&Value::Bool(true))
    })
}
#[must_use]
pub fn parse_markdown_findings(text: &str, label: &str) -> Vec<CollectedFinding> {
    if text.is_empty() || has_no_findings_sentinel(text) {
        return Vec::new();
    }
    let mut rows = Vec::new();
    let mut oos = false;
    let mut skip = false;
    let mut title = String::new();
    let mut body_lines = Vec::new();
    for line in crate::split_text_lines(text) {
        if line.starts_with("### Out-of-Scope Observations") {
            flush_markdown_finding(&mut rows, &mut title, &mut body_lines, label, oos);
            oos = true;
            skip = false;
            continue;
        }
        if line.starts_with("### In-Scope Findings") {
            flush_markdown_finding(&mut rows, &mut title, &mut body_lines, label, oos);
            oos = false;
            skip = false;
            continue;
        }
        if line.starts_with("## Commits since merge-base") {
            flush_markdown_finding(&mut rows, &mut title, &mut body_lines, label, oos);
            skip = true;
            continue;
        }
        if skip && (line.starts_with("### ") || line.starts_with("## ")) {
            skip = false;
            continue;
        }
        if skip {
            continue;
        }
        if let Some(next_title) = list_title(line) {
            flush_markdown_finding(&mut rows, &mut title, &mut body_lines, label, oos);
            next_title.clone_into(&mut title);
            body_lines.push(line.to_owned());
            continue;
        }
        if !line.trim().is_empty() {
            body_lines.push(line.to_owned());
        }
    }
    flush_markdown_finding(&mut rows, &mut title, &mut body_lines, label, oos);
    rows
}

fn list_title(line: &str) -> Option<&str> {
    if let Some(rest) = line.strip_prefix("- ").or_else(|| line.strip_prefix("* ")) {
        return Some(rest.trim_start());
    }
    let digits = line.bytes().take_while(u8::is_ascii_digit).count();
    let remainder = line.get(digits..)?;
    let after_dot = remainder.strip_prefix('.')?;
    let first = after_dot.chars().next()?;
    first.is_whitespace().then(|| after_dot.trim_start())
}

fn flush_markdown_finding(
    rows: &mut Vec<CollectedFinding>,
    title: &mut String,
    body_lines: &mut Vec<String>,
    label: &str,
    oos: bool,
) {
    if !title.is_empty() && !body_lines.is_empty() {
        let body = body_lines
            .iter()
            .map(|line| line.trim())
            .filter(|line| !line.is_empty())
            .collect::<Vec<_>>()
            .join(" ")
            .replace('\t', " ");
        let clean_title = title.trim().replace('\t', " ");
        rows.push(CollectedFinding {
            title: if oos {
                format!("[OUT_OF_SCOPE] {clean_title}")
            } else {
                clean_title
            },
            label: label.to_owned(),
            body,
        });
    }
    title.clear();
    body_lines.clear();
}
#[must_use]
pub fn render_collection(rows: impl IntoIterator<Item = CollectedFinding>) -> CollectionRender {
    const OOS_CAP_PER_REVIEWER: usize = 3;
    let mut findings = String::new();
    let mut oos = String::new();
    let mut findings_count = 0_usize;
    let mut oos_count = 0_usize;
    let mut oos_by_label = BTreeMap::<String, usize>::new();
    for row in rows {
        let label = normalize_reviewer_label(&row.label);
        if !label.ends_with("-output.txt") {
            continue;
        }
        let is_oos = row.title.starts_with("[OUT_OF_SCOPE]");
        if is_oos {
            let retained = oos_by_label.entry(label.clone()).or_default();
            if *retained >= OOS_CAP_PER_REVIEWER {
                continue;
            }
            *retained += 1;
        }
        findings_count += 1;
        let title = clean_oos_focus_title(&row.title);
        let _ignored = write!(
            findings,
            "### FINDING_{findings_count}: {title}\n- **Reviewer**: {label}\n- **Concern**: {}\n- **Suggested revision**: Address the concern above.\n\n",
            row.body
        );
        if is_oos {
            oos_count += 1;
            let _ignored = write!(
                oos,
                "### FINDING_{findings_count}: {title}\n{}\n\n",
                row.body
            );
        }
    }
    CollectionRender {
        findings,
        oos,
        findings_count,
        oos_count,
    }
}

fn normalize_reviewer_label(label: &str) -> String {
    let (mut stem, extension) = label.strip_suffix(".txt").map_or_else(
        || (label.to_owned(), ""),
        |value| (value.to_owned(), ".txt"),
    );
    loop {
        let Some(next) = ["-phase2", "-phase3", "-retry"]
            .iter()
            .find_map(|suffix| stem.strip_suffix(suffix))
        else {
            break;
        };
        stem = next.to_owned();
    }
    format!("{stem}{extension}")
}

fn clean_oos_focus_title(title: &str) -> String {
    let Some(rest) = title.strip_prefix("[OUT_OF_SCOPE] **") else {
        return title.to_owned();
    };
    let Some((category, _tail)) = rest.split_once("**") else {
        return title.to_owned();
    };
    if !FOCUS_AREA_VALUES.contains(&category) {
        return title.to_owned();
    }
    let location = title
        .find("[`")
        .and_then(|start| title[start + 2..].find("`]").map(|end| (start, end)))
        .map(|(start, end)| &title[start + 2..start + 2 + end]);
    location.map_or_else(
        || format!("[OUT_OF_SCOPE] {category}"),
        |location| format!("[OUT_OF_SCOPE] {category}: {location}"),
    )
}
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct CollectorResultRecord {
    pub reviewer_file: String,
    pub tool: String,
    pub status: String,
}
#[must_use]
pub fn parse_threshold_collector_records(text: &str) -> Vec<CollectorResultRecord> {
    parse_legacy_collector_blocks(text)
        .iter()
        .map(collector_record_from_fields)
        .collect()
}

fn collector_record_from_fields(fields: &BTreeMap<String, String>) -> CollectorResultRecord {
    CollectorResultRecord {
        reviewer_file: fields.get("REVIEWER_FILE").cloned().unwrap_or_default(),
        tool: fields.get("TOOL").cloned().unwrap_or_default(),
        status: fields.get("STATUS").cloned().unwrap_or_default(),
    }
}
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ReviewerOutput {
    pub path: String,
    pub content: Option<String>,
}
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct PanelManifestSlot {
    pub slot: String,
    pub tool: String,
    pub output: String,
}
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ReviewerFailureThresholdInput {
    pub collector_results: String,
    pub reviewer_outputs: Vec<ReviewerOutput>,
    pub dropped_slots: Option<String>,
    pub panel_manifest: Vec<PanelManifestSlot>,
    pub intended_slots: usize,
    pub launched_slots: Option<usize>,
}
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ReviewerFailureThreshold {
    pub intended_slots: usize,
    pub succeeded_slots: usize,
    pub failed_slots: usize,
    pub counted_slots: usize,
    pub not_substantive_slots: usize,
    pub dropped_slots: usize,
    pub dropped_static_slots: usize,
    pub dynamic_failed_slots: usize,
    pub dynamic_dropped_slots: usize,
    pub threshold_ok: bool,
    pub threshold_reason: String,
}
#[derive(Default)]
struct ThresholdCounts {
    succeeded: usize,
    failed: usize,
    counted: usize,
    not_substantive: usize,
}
#[derive(Default)]
struct ThresholdState {
    statuses: BTreeMap<String, String>,
    dynamic_bases: BTreeSet<String>,
    counted_slot_tools: BTreeSet<(String, String)>,
    counts: ThresholdCounts,
}
#[must_use]
pub fn reviewer_failure_threshold(
    input: &ReviewerFailureThresholdInput,
) -> ReviewerFailureThreshold {
    let manifest_by_output = input
        .panel_manifest
        .iter()
        .map(|row| {
            (
                normalize_output_base(&row.output),
                (row.slot.clone(), row.tool.clone()),
            )
        })
        .collect::<BTreeMap<_, _>>();
    let manifest_by_slot_tool = input
        .panel_manifest
        .iter()
        .map(|row| {
            (
                (row.slot.clone(), row.tool.clone()),
                normalize_output_base(&row.output),
            )
        })
        .collect::<BTreeMap<_, _>>();
    let mut state = ThresholdState::default();

    for record in parse_threshold_collector_records(&input.collector_results) {
        let base = normalize_output_base(&record.reviewer_file);
        if record.status.is_empty() || !is_reviewer_output_basename(&base) {
            continue;
        }
        let slot_tool = manifest_by_output.get(&base);
        if let Some(slot_tool) = slot_tool {
            state.counted_slot_tools.insert(slot_tool.clone());
        } else if let Some(derived) = slot_tool_from_reviewer_basename(&base, &record.tool) {
            state.counted_slot_tools.insert(derived);
        }
        let dynamic = is_dynamic_reviewer_basename(&base)
            || slot_tool.is_some_and(|(slot, _tool)| slot.starts_with("dyn-"));
        let _inserted = count_once(&mut state, base, &record.status, dynamic);
    }
    for output in &input.reviewer_outputs {
        let base = normalize_output_base(&output.path);
        if !is_reviewer_output_basename(&base) || state.statuses.contains_key(&base) {
            continue;
        }
        let slot_tool = manifest_by_output.get(&base);
        if let Some(slot_tool) = slot_tool {
            state.counted_slot_tools.insert(slot_tool.clone());
        }
        let dynamic = is_dynamic_reviewer_basename(&base)
            || slot_tool.is_some_and(|(slot, _tool)| slot.starts_with("dyn-"));
        let status = if output.content.as_deref().is_some_and(output_file_success) {
            "OK"
        } else {
            "ERROR"
        };
        let _inserted = count_once(&mut state, base, status, dynamic);
    }
    let (dropped_slots, dropped_static, dynamic_dropped_slots) =
        input.dropped_slots.as_deref().map_or((0, 0, 0), |dropped| {
            apply_dropped_slots(dropped, &manifest_by_slot_tool, &mut state)
        });
    if let Some(launched) = input.launched_slots {
        let never_launched = input.intended_slots.saturating_sub(launched);
        state.counts.failed += never_launched.saturating_sub(dropped_slots);
    }
    let dynamic_failed_slots = state
        .statuses
        .iter()
        .filter(|(base, status)| state.dynamic_bases.contains(*base) && !successful_status(status))
        .count();
    let half_plus_one = input.intended_slots / 2 + 1;
    let threshold_ok = state.counts.failed < half_plus_one;
    let threshold_reason = if threshold_ok {
        String::new()
    } else {
        format!(
            "{} of {} panel slots failed (threshold: >50% = >{})",
            state.counts.failed,
            input.intended_slots,
            input.intended_slots / 2
        )
    };
    ReviewerFailureThreshold {
        intended_slots: input.intended_slots,
        succeeded_slots: state.counts.succeeded,
        failed_slots: state.counts.failed,
        counted_slots: state.counts.counted,
        not_substantive_slots: state.counts.not_substantive,
        dropped_slots,
        dropped_static_slots: dropped_static,
        dynamic_failed_slots,
        dynamic_dropped_slots,
        threshold_ok,
        threshold_reason,
    }
}

fn count_once(state: &mut ThresholdState, base: String, status: &str, dynamic: bool) -> bool {
    if dynamic {
        state.dynamic_bases.insert(base.clone());
    }
    if state.statuses.contains_key(&base) {
        return false;
    }
    state.statuses.insert(base, status.to_owned());
    state.counts.counted += 1;
    if successful_status(status) {
        state.counts.succeeded += 1;
    } else {
        state.counts.failed += 1;
        if status == "NOT_SUBSTANTIVE" {
            state.counts.not_substantive += 1;
        }
    }
    true
}

fn apply_dropped_slots(
    dropped: &str,
    manifest_by_slot_tool: &BTreeMap<(String, String), String>,
    state: &mut ThresholdState,
) -> (usize, usize, usize) {
    let mut dropped_slots = 0_usize;
    let mut dropped_static = 0_usize;
    let mut dynamic_dropped_slots = 0_usize;
    for line in crate::split_text_lines(dropped) {
        let Some((slot, tool, reason)) = dropped_slot_fields(line) else {
            continue;
        };
        let dynamic_slot = slot.starts_with("dyn-");
        let base = dropped_reviewer_output_base(&slot, &tool, &reason, manifest_by_slot_tool);
        if dynamic_slot {
            dynamic_dropped_slots += 1;
        }
        if let Some(base) = base {
            dropped_slots += 1;
            if !dynamic_slot && reason != "straggler-dropped" {
                dropped_static += 1;
            }
            if state.statuses.contains_key(&base) {
                continue;
            }
            let dynamic = dynamic_slot || is_dynamic_reviewer_basename(&base);
            if count_once(state, base, "ERROR", dynamic) {
                state.counted_slot_tools.insert((slot, tool));
            }
            continue;
        }
        if !dynamic_slot {
            continue;
        }
        let synthetic = format!("dyn-slot:{slot}:{tool}");
        let drop_base = dynamic_drop_output_base(&slot, &tool);
        if state
            .counted_slot_tools
            .contains(&(slot.clone(), tool.clone()))
            || state.statuses.contains_key(&synthetic)
            || drop_base.is_some_and(|base| state.statuses.contains_key(&base))
        {
            continue;
        }
        if count_once(state, synthetic, "ERROR", true) {
            state.counted_slot_tools.insert((slot, tool));
        }
    }
    (dropped_slots, dropped_static, dynamic_dropped_slots)
}

fn successful_status(status: &str) -> bool {
    matches!(status, "OK" | "cap_hit")
}

fn output_file_success(text: &str) -> bool {
    !text.is_empty() && !text.lines().any(|line| line == "STATUS=NOT_SUBSTANTIVE")
}

fn is_static_reviewer_basename(base: &str) -> bool {
    let base = normalize_output_base(base);
    base == "codex-generalist-output.txt"
        || ["cursor", "codex"].iter().any(|tool| {
            base.strip_prefix(&format!("{tool}-specialist-"))
                .and_then(|rest| rest.strip_suffix("-output.txt"))
                .is_some_and(|slot| !slot.is_empty())
        })
}

fn is_dynamic_reviewer_basename(base: &str) -> bool {
    let base = normalize_output_base(base);
    base.strip_prefix("dyn-")
        .and_then(|rest| rest.strip_suffix("-output.txt"))
        .is_some()
}

fn is_reviewer_output_basename(base: &str) -> bool {
    is_static_reviewer_basename(base) || is_dynamic_reviewer_basename(base)
}

fn slot_tool_from_reviewer_basename(base: &str, tool: &str) -> Option<(String, String)> {
    if !matches!(tool, "codex" | "cursor") {
        return None;
    }
    let normalized = normalize_output_base(base);
    if let Some(slot) = normalized
        .strip_prefix("dyn-")
        .and_then(|rest| rest.strip_suffix("-output.txt"))
        .filter(|slot| !slot.is_empty())
    {
        return Some((format!("dyn-{slot}"), tool.to_owned()));
    }
    for vendor in ["cursor", "codex"] {
        if let Some(slot) = normalized
            .strip_prefix(&format!("{vendor}-specialist-"))
            .and_then(|rest| rest.strip_suffix("-output.txt"))
            .filter(|slot| !slot.is_empty())
        {
            return Some((slot.to_owned(), vendor.to_owned()));
        }
    }
    None
}

fn dropped_slot_fields(line: &str) -> Option<(String, String, String)> {
    let mut fields = line.split('\t');
    let slot = fields.next()?.to_owned();
    let tool = fields.next().unwrap_or_default().to_owned();
    let reason = fields.next().unwrap_or_default().to_owned();
    (!slot.is_empty() && matches!(tool.as_str(), "codex" | "cursor"))
        .then_some((slot, tool, reason))
}

fn dropped_reviewer_output_base(
    slot: &str,
    tool: &str,
    reason: &str,
    manifest_by_slot_tool: &BTreeMap<(String, String), String>,
) -> Option<String> {
    let dynamic = slot.starts_with("dyn-");
    if reason == "straggler-dropped" && !dynamic {
        return None;
    }
    if let Some(output) = manifest_by_slot_tool.get(&(slot.to_owned(), tool.to_owned())) {
        return Some(output.clone());
    }
    if dynamic {
        return dynamic_drop_output_base(slot, tool);
    }
    if slot == "generalist" && tool == "codex" {
        return Some(normalize_output_base("codex-generalist-output.txt"));
    }
    Some(normalize_output_base(&format!(
        "{tool}-specialist-{slot}-output.txt"
    )))
}

fn dynamic_drop_output_base(slot: &str, tool: &str) -> Option<String> {
    let mut archetype = slot.strip_prefix("dyn-")?.to_owned();
    if tool == "codex" && archetype.ends_with("-codex") {
        archetype.truncate(archetype.len() - "-codex".len());
    }
    let suffix = if tool == "codex" {
        "-codex-output.txt"
    } else {
        "-output.txt"
    };
    Some(normalize_output_base(&format!("dyn-{archetype}{suffix}")))
}
