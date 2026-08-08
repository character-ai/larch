//! Field derivation for the terminal `/implement` final report.
//!
//! Port of the derivation half of Python `larch.report.final_report`. Every
//! helper reads only files and returns values; process launches, GitHub calls,
//! and the still-Python helper verbs stay with the command layer.

use std::{fmt::Write as _, fs, path::Path};

use serde_json::{Map, Value};

use crate::{
    CLAUDE_FABLE_5_MODEL, CLAUDE_HAIKU_4_5_MODEL, CLAUDE_SONNET_4_6_MODEL, KvDocument,
    ParseOptions, read_kv_from_text,
    report::{ClaudeCounts, CodexCounts, token_scan::safe_int},
};

/// Spawned-Claude models that price through their own flag family.
const CLAUDE_SUB_MODEL_FLAG_PREFIXES: [(&str, &str); 3] = [
    (CLAUDE_SONNET_4_6_MODEL, "claude-sub-sonnet"),
    (CLAUDE_HAIKU_4_5_MODEL, "claude-sub-haiku"),
    (CLAUDE_FABLE_5_MODEL, "claude-sub-fable"),
];

/// Basename of the per-run difficulty record.
pub const DIFFICULTY_RECORD_BASENAME: &str = "difficulty-rating.json";
/// Manifest `status` for a completed run.
pub const MANIFEST_STATUS_DONE: &str = "done";
/// Manifest `status` for a run that shipped without merging.
pub const MANIFEST_STATUS_IN_PROGRESS: &str = "in-progress";
/// Ship-state keys the PR line-count cache owns.
pub const LINE_COUNT_STATE_KEYS: [&str; 6] = [
    "LINES_PR_NUMBER",
    "LINES_STATUS",
    "CODE_ADDED",
    "CODE_DELETED",
    "LOGS_ADDED",
    "LOGS_DELETED",
];
/// Outcomes `--normalized-outcome` accepts.
pub const NORMALIZED_OUTCOMES: [&str; 10] = [
    "bailed",
    "bailed-needs-user-input",
    "design-only",
    "force-merged-externally",
    "forked-dry-run",
    "merged",
    "pr-created",
    "pr-created-draft",
    "shipping",
    "stalled",
];
/// Outcomes where the merge completed, so a stale needs-user handoff is void.
pub const MERGE_COMPLETED_OUTCOMES: [&str; 2] = ["merged", "force-merged-externally"];

/// Read one `KEY=value` row from a state file, taking the first match.
#[must_use]
pub fn read_state_kv(path: &Path, key: &str) -> String {
    fs::read_to_string(path)
        .ok()
        .and_then(|text| read_kv_from_text(&text, key))
        .unwrap_or_default()
}

/// Read one JSON object file, degrading an unreadable or non-object file to empty.
#[must_use]
pub fn json_object(path: &Path) -> Map<String, Value> {
    fs::read(path)
        .ok()
        .and_then(|bytes| serde_json::from_slice::<Value>(&bytes).ok())
        .and_then(|value| value.as_object().cloned())
        .unwrap_or_default()
}

fn nested_object<'a>(map: &'a Map<String, Value>, key: &str) -> Option<&'a Map<String, Value>> {
    map.get(key).and_then(Value::as_object)
}

fn truthy_string(value: Option<&Value>) -> String {
    match value {
        Some(Value::String(text)) => text.clone(),
        Some(Value::Number(number)) => number.to_string(),
        _other => String::new(),
    }
}

/// Render the `- **Difficulty**:` line body from the run's difficulty record.
#[must_use]
pub fn difficulty_summary_line(run_dir: &Path) -> String {
    let record = run_dir.join(DIFFICULTY_RECORD_BASENAME);
    if !record.is_file() {
        return String::new();
    }
    let data = json_object(&record);
    if data.is_empty() {
        return String::new();
    }
    difficulty_line(&data)
}

/// Port of Python `larch.calibration.difficulty.difficulty_line`.
#[must_use]
pub fn difficulty_line(data: &Map<String, Value>) -> String {
    let predicted = {
        let value = truthy_string(data.get("predicted_tier"));
        if value.is_empty() {
            "unknown".to_owned()
        } else {
            value
        }
    };
    let applied = {
        let value = truthy_string(data.get("applied_tier"));
        if value.is_empty() {
            predicted.clone()
        } else {
            value
        }
    };
    let mut parts = vec![
        format!("predicted {predicted}"),
        format!("applied {applied}"),
    ];
    if data
        .get("floors_applied")
        .and_then(Value::as_array)
        .is_some_and(|items| !items.is_empty())
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
    let audit = truthy_string(data.get("audit_upgrade"));
    if !audit.is_empty() {
        parts.push(format!("audit {audit}"));
    }
    if truthy_string(data.get("override_source")) == "operator" {
        parts.push("override operator".to_owned());
    }
    if let Some(items) = data
        .get("escalations")
        .and_then(Value::as_array)
        .filter(|items| !items.is_empty())
    {
        let rendered: Vec<String> = items
            .iter()
            .map(|item| {
                let Some(row) = item.as_object() else {
                    return python_repr(item);
                };
                let field = |key: &str| row.get(key).map_or_else(|| "?".to_owned(), python_repr);
                let trigger = row.get("trigger").map(python_repr).unwrap_or_default();
                let suffix = if trigger.is_empty() {
                    String::new()
                } else {
                    format!(" {trigger}")
                };
                format!(
                    "r{} {}->{}{suffix}",
                    field("round"),
                    field("from_tier"),
                    field("to_tier")
                )
            })
            .collect();
        parts.push(format!("escalated {}", rendered.join(", ")));
    }
    let skipped = truthy_string(data.get("panel_skipped"));
    if !skipped.is_empty() {
        parts.push(format!("panel skipped: {skipped}"));
    }
    parts.join(", ")
}

/// Render one JSON scalar the way Python's `str()` would.
fn python_repr(value: &Value) -> String {
    match value {
        Value::String(text) => text.clone(),
        Value::Bool(flag) => if *flag { "True" } else { "False" }.to_owned(),
        Value::Null => "None".to_owned(),
        other => other.to_string(),
    }
}

/// Return the count of `archetypes` entries in one scout manifest.
fn archetype_count(path: &Path) -> Option<usize> {
    let bytes = fs::read(path).ok()?;
    let value: Value = serde_json::from_slice(&bytes).ok()?;
    let object = value.as_object()?;
    object
        .get("archetypes")
        .and_then(Value::as_array)
        .map(Vec::len)
}

/// Return the sorted round-scoped paths matching `<round-*>/<prefix>*<suffix>`.
fn round_artifacts(tmpdir: &Path, prefix: &str, suffix: &str) -> Vec<std::path::PathBuf> {
    let mut rounds: Vec<std::path::PathBuf> = fs::read_dir(tmpdir)
        .into_iter()
        .flatten()
        .flatten()
        .map(|entry| entry.path())
        .filter(|path| {
            path.is_dir()
                && path
                    .file_name()
                    .and_then(|name| name.to_str())
                    .is_some_and(|name| name.starts_with("round-"))
        })
        .collect();
    rounds.sort();
    let mut found: Vec<std::path::PathBuf> = Vec::new();
    for round in rounds {
        let mut matches: Vec<std::path::PathBuf> = fs::read_dir(&round)
            .into_iter()
            .flatten()
            .flatten()
            .map(|entry| entry.path())
            .filter(|path| {
                path.file_name()
                    .and_then(|name| name.to_str())
                    .is_some_and(|name| name.starts_with(prefix) && name.ends_with(suffix))
            })
            .collect();
        matches.sort();
        found.extend(matches);
    }
    found
}

/// Render the `- **Dynamic archetypes**:` line body.
#[must_use]
pub fn dynamic_archetypes_line(tmpdir: &Path) -> String {
    let round_status = round_artifacts(tmpdir, "scout-round", "-status.env")
        .into_iter()
        .find_map(|path| {
            let status = read_state_kv(&path, "SCOUT_STATUS");
            (!status.is_empty()).then_some(status)
        })
        .unwrap_or_default();
    if round_status.starts_with("skipped-") {
        return round_status;
    }
    match round_status.as_str() {
        "producer-missing" | "producer-invalid" => {
            return "static-only, producer missing-or-invalid".to_owned();
        }
        "pre-scouted-empty" => return "static-only, pre-scouted-empty".to_owned(),
        "pre-scouted" => {
            let manifest = round_artifacts(tmpdir, "scout-round", "-manifest.json")
                .into_iter()
                .find(|path| path.is_file());
            return manifest
                .and_then(|path| archetype_count(&path))
                .map_or_else(|| "unknown".to_owned(), |count| format!("ok ({count})"));
        }
        "" => {}
        _unrecognized => return "unknown".to_owned(),
    }
    if read_state_kv(&tmpdir.join("run-flags.sh"), "SELF_REVIEW_REQUESTED") == "true" {
        return "N/A".to_owned();
    }
    let status_file = tmpdir.join("step2-scout-coder-status.env");
    if !status_file.is_file() {
        return "unknown".to_owned();
    }
    match read_state_kv(&status_file, "SCOUT_CODER_STATUS").as_str() {
        "" => return "unknown".to_owned(),
        "ok" => {}
        _other => return "static-only, producer missing-or-invalid".to_owned(),
    }
    let count = archetype_count(&tmpdir.join("scout-coder-manifest.json"));
    let eligible = tmpdir.join("step2-external-scout-eligible.txt").is_file();
    match count {
        None => "static-only, producer missing-or-invalid".to_owned(),
        Some(_any) if !eligible => "static-only, producer missing-or-invalid".to_owned(),
        Some(0) => "static-only, producer empty".to_owned(),
        Some(count) => format!("ok ({count})"),
    }
}

/// Return the most recently modified `larch-tokens-*.jsonl` ledger in `tmpdir`.
#[must_use]
pub fn latest_token_ledger(tmpdir: &Path) -> Option<std::path::PathBuf> {
    let mut candidates: Vec<(std::time::SystemTime, std::path::PathBuf)> = fs::read_dir(tmpdir)
        .into_iter()
        .flatten()
        .flatten()
        .map(|entry| entry.path())
        .filter(|path| super::token_scan::is_ledger_name(path))
        .map(|path| {
            let modified = path
                .metadata()
                .and_then(|meta| meta.modified())
                .unwrap_or(std::time::UNIX_EPOCH);
            (modified, path)
        })
        .collect();
    candidates.sort();
    candidates.pop().map(|(_modified, path)| path)
}

/// Count accepted, rejected, and whether any code-review finding was seen.
#[must_use]
pub fn count_code_review_findings(findings_file: &Path) -> (i64, i64, bool) {
    if !findings_file.is_file() {
        return (0, 0, false);
    }
    let Ok(text) = fs::read_to_string(findings_file) else {
        return (0, 0, false);
    };
    let mut accepted = 0;
    let mut rejected = 0;
    let mut seen = false;
    for line in text.lines() {
        if line.trim().is_empty() {
            continue;
        }
        let Ok(Value::Object(record)) = serde_json::from_str::<Value>(line) else {
            continue;
        };
        if truthy_string(record.get("phase")) != "code-review" {
            continue;
        }
        seen = true;
        match truthy_string(record.get("outcome")).as_str() {
            "accepted" => accepted += 1,
            "rejected" => rejected += 1,
            _other => {}
        }
    }
    (accepted, rejected, seen)
}

fn review_line_from_findings(run_dir: &Path) -> String {
    let (accepted, rejected, seen) =
        count_code_review_findings(&run_dir.join("review-findings-full.jsonl"));
    let total = accepted + rejected;
    if total > 0 {
        return format!("{accepted}/{total} accepted");
    }
    if seen { "0 findings" } else { "N/A" }.to_owned()
}

/// Render one review tally line, degrading to `N/A` on every unusable input.
#[must_use]
pub fn derive_review_line(run_dir: &Path, filename: &str) -> String {
    let tally = run_dir.join(filename);
    if !tally.is_file() {
        if filename == "code-review-tally.json" {
            return review_line_from_findings(run_dir);
        }
        return "N/A".to_owned();
    }
    let data = json_object(&tally);
    if data.is_empty() {
        return "N/A".to_owned();
    }
    let count = |key: &str| -> Option<i64> {
        match data.get(key) {
            None | Some(Value::Null) => Some(0),
            Some(Value::Number(number)) => number.as_i64(),
            Some(Value::String(text)) if text.is_empty() => Some(0),
            Some(Value::String(text)) => text.parse::<i64>().ok(),
            Some(Value::Bool(flag)) => Some(i64::from(*flag)),
            Some(_other) => None,
        }
    };
    let (Some(accepted), Some(rejected)) = (count("accepted_count"), count("rejected_count"))
    else {
        return "N/A".to_owned();
    };
    if accepted < 0 || rejected < 0 {
        return "N/A".to_owned();
    }
    let total = accepted + rejected;
    if total > 0 {
        return format!("{accepted}/{total} accepted");
    }
    // A zero-count tally distinguishes "review ran clean" from "no review ran",
    // but only for code review; a plan-review zero total stays N/A.
    let is_code_review =
        filename == "code-review-tally.json" || truthy_string(data.get("phase")) == "code-review";
    if !is_code_review {
        return "N/A".to_owned();
    }
    if truthy_string(data.get("mode")) == "self-review" {
        return "self-review: 0 findings".to_owned();
    }
    "0 findings".to_owned()
}

/// Count filed out-of-scope issues and collect their sorted unique URLs.
#[must_use]
pub fn derive_oos_fields(run_dir: &Path) -> (String, String) {
    let ndjson = run_dir.join("oos-issues.ndjson");
    if !ndjson.is_file() {
        return ("0".to_owned(), String::new());
    }
    let Ok(text) = fs::read_to_string(&ndjson) else {
        return ("0".to_owned(), String::new());
    };
    let lines: Vec<&str> = text
        .lines()
        .filter(|line| !line.trim().is_empty())
        .collect();
    let mut urls: std::collections::BTreeSet<String> = std::collections::BTreeSet::new();
    for line in &lines {
        let Ok(Value::Object(record)) = serde_json::from_str::<Value>(line) else {
            continue;
        };
        let Some(Value::String(body)) = record.get("body") else {
            continue;
        };
        urls.extend(filed_url_lines(body));
    }
    (
        lines.len().to_string(),
        urls.into_iter().collect::<Vec<String>>().join(","),
    )
}

/// Extract every `- **Filed URL**: <issue url>` value from one issue body.
fn filed_url_lines(body: &str) -> Vec<String> {
    let mut found = Vec::new();
    for line in body.split('\n') {
        let trimmed = line.trim_start_matches([' ', '\t']);
        let Some(rest) = trimmed.strip_prefix('-') else {
            continue;
        };
        let rest = rest.trim_start_matches([' ', '\t']);
        let Some(rest) = rest.strip_prefix("**Filed") else {
            continue;
        };
        let rest = rest.trim_start_matches([' ', '\t']);
        let Some(rest) = rest.strip_prefix("URL**") else {
            continue;
        };
        let rest = rest.trim_start_matches([' ', '\t']);
        let Some(rest) = rest.strip_prefix(':') else {
            continue;
        };
        let rest = rest.trim_start_matches([' ', '\t']);
        if !rest.starts_with("https://") {
            continue;
        }
        let url: String = rest
            .chars()
            .take_while(|character| !character.is_whitespace())
            .collect();
        let Some((prefix, tail)) = url.rsplit_once("/issues/") else {
            continue;
        };
        if prefix.is_empty() || tail.is_empty() || !tail.bytes().all(|byte| byte.is_ascii_digit()) {
            continue;
        }
        found.push(url);
    }
    found
}

/// Resolve the reported run duration, preferring the timing report.
#[must_use]
pub fn final_report_duration(run_dir: &Path, ship: &Path) -> String {
    let timing = run_dir.join("timing-report.json");
    if timing.is_file() {
        let data = json_object(&timing);
        let total_hms = truthy_string(data.get("total_hms"));
        if !total_hms.is_empty() {
            return total_hms;
        }
        if let Some(total_seconds) = data.get("total_seconds").filter(|value| !value.is_null()) {
            return format!("{}s", python_repr(total_seconds));
        }
    }
    let duration = read_state_kv(ship, "DURATION");
    if duration.is_empty() {
        "N/A".to_owned()
    } else {
        duration
    }
}

/// Resolve a positive `pr_number` from a manifest, following `reserved`.
fn manifest_pr_number(data: &Map<String, Value>) -> i64 {
    for key in ["pr_number", "PR_NUMBER"] {
        match data.get(key) {
            Some(Value::Number(number)) => {
                if let Some(value) = number.as_i64().filter(|value| *value > 0) {
                    return value;
                }
            }
            Some(Value::String(text)) => {
                let trimmed = text.trim();
                if !trimmed.is_empty()
                    && trimmed.bytes().all(|byte| byte.is_ascii_digit())
                    && let Some(value) = trimmed.parse::<i64>().ok().filter(|value| *value > 0)
                {
                    return value;
                }
            }
            _other => {}
        }
    }
    nested_object(data, "reserved").map_or(0, manifest_pr_number)
}

/// Recover `merged` from a manifest-only run whose state files are empty.
#[must_use]
pub fn manifest_only_recovered_outcome(run_dir: &Path) -> String {
    let data = json_object(&run_dir.join("manifest.json"));
    if truthy_string(data.get("status")) == MANIFEST_STATUS_DONE && manifest_pr_number(&data) > 0 {
        return "merged".to_owned();
    }
    String::new()
}

/// Whether one state file holds at least one `KEY=value` row.
#[must_use]
pub fn state_file_has_rows(path: &Path) -> bool {
    fs::read_to_string(path).is_ok_and(|text| {
        text.lines()
            .any(|line| !line.trim().is_empty() && line.contains('='))
    })
}

/// Apply the manifest-only outcome backstop when both state files are empty.
#[must_use]
pub fn outcome_with_manifest_only_backstop(
    run_dir: &Path,
    outcome: &str,
    ship: &Path,
    finalize: &Path,
) -> String {
    if state_file_has_rows(ship) || state_file_has_rows(finalize) {
        return outcome.to_owned();
    }
    let recovered = manifest_only_recovered_outcome(run_dir);
    if recovered.is_empty() {
        outcome.to_owned()
    } else {
        recovered
    }
}

fn heading_line_is_stalled(line: &str) -> bool {
    let stripped = line.trim();
    stripped.starts_with("## /")
        && (stripped.ends_with(": stalled") || stripped.ends_with("\u{2014} stalled"))
}

/// Whether a rendered summary still carries a stalled run heading.
#[must_use]
pub fn summary_heading_is_stalled(text: &str) -> bool {
    text.split('\n').any(heading_line_is_stalled)
}

fn stalled_outcome_line(line: &str) -> bool {
    let trimmed = line.trim_end_matches(['\n', '\r']);
    let body = trimmed.trim_start_matches([' ', '\t']);
    let Some(rest) = body.strip_prefix('-') else {
        return false;
    };
    let rest = rest.trim_start_matches([' ', '\t']);
    let Some(rest) = rest.strip_prefix("**Outcome**:") else {
        return false;
    };
    let value = rest.trim_matches([' ', '\t']);
    let value = value
        .strip_prefix('\u{274c}')
        .map_or(value, |tail| tail.trim_start_matches([' ', '\t']));
    value.eq_ignore_ascii_case("stalled") || value == "DONE"
}

fn split_keep_ends(text: &str) -> Vec<String> {
    text.split_inclusive('\n').map(str::to_owned).collect()
}

fn manifest_only_reconciliation_allowed(run_dir: &Path) -> bool {
    let Some(tmpdir) = run_dir
        .parent()
        .and_then(Path::parent)
        .and_then(Path::parent)
    else {
        return false;
    };
    !state_file_has_rows(&tmpdir.join("ship-pr-state.sh"))
        && !state_file_has_rows(&tmpdir.join("finalize-state.sh"))
}

/// Whether a manifest-only merged run still shows a stalled summary.
#[must_use]
pub fn stalled_summary_manifest_reconciliation_needed(run_dir: &Path) -> bool {
    let summary = run_dir.join("final-summary.md");
    if !manifest_only_reconciliation_allowed(run_dir)
        || manifest_only_recovered_outcome(run_dir) != "merged"
        || !summary.is_file()
    {
        return false;
    }
    let Ok(text) = fs::read_to_string(&summary) else {
        return false;
    };
    let lines = split_keep_ends(&text);
    lines.iter().any(|line| heading_line_is_stalled(line))
        && lines.iter().any(|line| stalled_outcome_line(line))
}

/// Rewrite a manifest-only shipped summary away from `stalled`.
///
/// Returns the rewritten body when the summary needed and received the change.
#[must_use]
pub fn reconciled_stalled_summary(run_dir: &Path) -> Option<String> {
    if !manifest_only_reconciliation_allowed(run_dir)
        || manifest_only_recovered_outcome(run_dir) != "merged"
    {
        return None;
    }
    let summary = run_dir.join("final-summary.md");
    if !summary.is_file() {
        return None;
    }
    let text = fs::read_to_string(&summary).ok()?;
    let mut lines = split_keep_ends(&text);
    let heading_index = lines
        .iter()
        .position(|line| heading_line_is_stalled(line))?;
    let outcome_index = lines.iter().position(|line| stalled_outcome_line(line))?;
    let line = lines[heading_index].clone();
    let newline = if line.ends_with('\n') { "\n" } else { "" };
    let heading = line.trim_end_matches('\n').trim_end();
    let rewritten_heading = rewrite_stalled_heading(heading);
    lines[heading_index] = format!("{rewritten_heading}{newline}");
    let outcome_line = lines[outcome_index].clone();
    let outcome_newline = if outcome_line.ends_with('\n') {
        "\n"
    } else {
        ""
    };
    lines[outcome_index] = format!(
        "- **Outcome**: {}{outcome_newline}",
        super::run_summary::map_outcome_display("merged")
    );
    let rewritten: String = lines.concat();
    if rewritten.split('\n').any(stalled_outcome_line) {
        return None;
    }
    Some(rewritten)
}

/// Replace a trailing ` — stalled` or `: stalled` heading suffix with `: merged`.
fn rewrite_stalled_heading(heading: &str) -> String {
    for marker in ["\u{2014}", ":"] {
        if let Some(index) = heading.rfind(marker) {
            let (head, tail) = heading.split_at(index);
            let value = tail[marker.len()..].trim_start_matches([' ', '\t']);
            if value == "stalled" {
                let head = if marker == "\u{2014}" {
                    head.trim_end_matches([' ', '\t'])
                } else {
                    head
                };
                return format!("{head}: merged");
            }
        }
    }
    heading.to_owned()
}

/// Compose the summary body from optional prefix sections.
#[must_use]
pub fn join_prefixed_summary(prefix_sections: &[&str], summary_body: &str) -> String {
    let sections: Vec<&str> = prefix_sections
        .iter()
        .filter(|section| !section.trim().is_empty())
        .map(|section| section.trim_matches('\n'))
        .collect();
    if sections.is_empty() {
        return summary_body.to_owned();
    }
    let mut joined: Vec<&str> = sections;
    let body = summary_body.trim_matches('\n');
    joined.push(body);
    format!("{}\n", joined.join("\n\n"))
}

/// Render one architectural knowledge section, or empty when there is nothing.
#[must_use]
pub fn architectural_section(heading: &str, text: &str) -> String {
    let stripped = text.trim();
    if stripped.is_empty() {
        return String::new();
    }
    format!("## {heading}\n\n{stripped}\n")
}

/// Compose the needs-user execution-issue entry.
#[must_use]
pub fn needs_user_execution_entry(reason: &str, next_action: &str) -> String {
    let pending = if next_action.is_empty() {
        String::new()
    } else {
        format!("; pending NEXT_ACTION={next_action}")
    };
    format!(
        "- ship route: merge and CI watch skipped \u{2014} needs user (reason: {reason}{pending})"
    )
}

/// Return the key one `KEY=value` state line declares, through the shared codec.
fn kv_line_key(line: &str) -> Option<String> {
    let document = KvDocument::parse(line, ParseOptions::legacy()).ok()?;
    let [row] = document.rows() else { return None };
    Some(row.key().to_owned())
}

/// Rewrite one ship-state body with a refreshed PR line-count cache.
#[must_use]
pub fn merged_line_count_state(existing: &str, pr_number: &str, rows: &[(&str, String)]) -> String {
    let mut preserved = String::new();
    for line in existing.split('\n') {
        let Some(key) = kv_line_key(line) else {
            continue;
        };
        if LINE_COUNT_STATE_KEYS.contains(&key.as_str()) {
            continue;
        }
        preserved.push_str(line);
        preserved.push('\n');
    }
    let number = if pr_number.is_empty() { "0" } else { pr_number };
    let _ = writeln!(preserved, "LINES_PR_NUMBER={number}");
    for (key, value) in rows {
        if *key == "REASON" {
            continue;
        }
        let _ = writeln!(preserved, "{key}={value}");
    }
    preserved
}

/// Codex token flags split by model, folding mini-class rows into the mini bucket.
fn codex_token_argv(report: &Map<String, Value>, bucket: &Map<String, Value>) -> Vec<String> {
    let Some(by_model) =
        nested_object(report, "BUCKETS_codex_by_model").filter(|split| !split.is_empty())
    else {
        return codex_flag_argv("codex", &CodexCounts::from_bucket(bucket));
    };
    let empty = Map::new();
    let mut main = CodexCounts::default();
    let mut mini = CodexCounts::default();
    for (model, raw) in by_model {
        let counts = CodexCounts::from_bucket(raw.as_object().unwrap_or(&empty));
        if super::CODEX_MINI_MODELS.contains(&model.as_str()) {
            mini.add(counts);
        } else {
            main.add(counts);
        }
    }
    let mut argv = codex_flag_argv("codex", &main);
    argv.extend(codex_flag_argv("codex-mini", &mini));
    argv
}

/// Codex-shaped flags for one display bucket.
fn codex_flag_argv(prefix: &str, counts: &CodexCounts) -> Vec<String> {
    vec![
        format!("--{prefix}-input-tokens"),
        counts.input.to_string(),
        format!("--{prefix}-cached-input-tokens"),
        counts.cached_input.to_string(),
        format!("--{prefix}-output-tokens"),
        counts.output.to_string(),
    ]
}

/// Claude-shaped flags for one lane prefix and its accumulated counts.
fn claude_flag_argv(prefix: &str, counts: &ClaudeCounts) -> Vec<String> {
    vec![
        format!("--{prefix}-input-tokens"),
        counts.input.to_string(),
        format!("--{prefix}-cache-read-tokens"),
        counts.cache_read.to_string(),
        format!("--{prefix}-cache-write-5m-tokens"),
        counts.cache_create_5m.to_string(),
        format!("--{prefix}-cache-write-1h-tokens"),
        counts.cache_create_1h.to_string(),
        format!("--{prefix}-output-tokens"),
        counts.output.to_string(),
    ]
}

/// Claude-shaped bucket flags for one lane prefix.
fn claude_bucket_argv(prefix: &str, bucket: &Map<String, Value>) -> Vec<String> {
    claude_flag_argv(prefix, &ClaudeCounts::from_bucket(bucket))
}

/// Spawned-Claude flags, split into the separately priced model families.
fn claude_sub_token_argv(report: &Map<String, Value>, bucket: &Map<String, Value>) -> Vec<String> {
    let Some(by_model) =
        nested_object(report, "BUCKETS_claude_sub_by_model").filter(|split| !split.is_empty())
    else {
        return claude_bucket_argv("claude-sub", bucket);
    };
    let families = CLAUDE_SUB_MODEL_FLAG_PREFIXES;
    let empty = Map::new();
    let mut aggregate = ClaudeCounts::default();
    let mut per_family = [ClaudeCounts::default(); CLAUDE_SUB_MODEL_FLAG_PREFIXES.len()];
    for (model, raw) in by_model {
        let counts = ClaudeCounts::from_bucket(raw.as_object().unwrap_or(&empty));
        let index = families
            .iter()
            .position(|(family_model, _prefix)| *family_model == model.as_str());
        let target = index.map_or(&mut aggregate, |index| &mut per_family[index]);
        target.add(counts);
    }
    let mut argv = claude_flag_argv("claude-sub", &aggregate);
    for (index, (_model, prefix)) in families.iter().enumerate() {
        argv.extend(claude_flag_argv(prefix, &per_family[index]));
    }
    argv
}

/// Cursor flags, split by model when every per-model bucket is exact.
fn cursor_token_argv(report: &Map<String, Value>, bucket: &Map<String, Value>) -> Vec<String> {
    if !super::cursor_buckets_are_detailed(report.get("BUCKETS_cursor_by_model")) {
        let total: i64 = ["input", "cache_read", "output"]
            .iter()
            .map(|key| safe_int(bucket.get(*key), 0))
            .sum();
        return vec!["--cursor-tokens".to_owned(), total.to_string()];
    }
    let detailed = nested_object(report, "BUCKETS_cursor_by_model").unwrap_or(&EMPTY_MAP);
    let mut composer = [0_i64; 3];
    let mut grok = [0_i64; 3];
    for (model, raw) in detailed {
        let fields = raw.as_object();
        let read = |key: &str| fields.map_or(0, |fields| safe_int(fields.get(key), 0));
        let target = if super::CURSOR_GROK_MODELS.contains(&model.as_str()) {
            &mut grok
        } else {
            &mut composer
        };
        target[0] += read("input");
        target[1] += read("cache_read");
        target[2] += read("output");
    }
    vec![
        "--cursor-input-tokens".to_owned(),
        composer[0].to_string(),
        "--cursor-cache-read-tokens".to_owned(),
        composer[1].to_string(),
        "--cursor-output-tokens".to_owned(),
        composer[2].to_string(),
        "--cursor-grok-input-tokens".to_owned(),
        grok[0].to_string(),
        "--cursor-grok-cache-read-tokens".to_owned(),
        grok[1].to_string(),
        "--cursor-grok-output-tokens".to_owned(),
        grok[2].to_string(),
    ]
}

static EMPTY_MAP: std::sync::LazyLock<Map<String, Value>> = std::sync::LazyLock::new(Map::new);

/// Build the `token cost` pricing flags one rendered token report supports.
///
/// A lane with a nonzero report bucket prices per bucket; a lane with only a
/// nonzero aggregate total prices blended; a lane with neither contributes no
/// flags at all, which is what makes an empty result mean "cost unavailable".
#[must_use]
pub fn token_argv_from_report(report: &Map<String, Value>) -> Vec<String> {
    let mut argv: Vec<String> = Vec::new();
    for (vendor, bucket_key, flag_prefix) in [
        ("claude", "BUCKETS_claude", "claude"),
        ("codex", "BUCKETS_codex", "codex"),
        ("cursor", "BUCKETS_cursor", "cursor"),
        ("claude_sub", "BUCKETS_claude_sub", "claude-sub"),
    ] {
        let bucket = nested_object(report, bucket_key).unwrap_or(&EMPTY_MAP);
        let has_counts =
            !bucket.is_empty() && bucket.values().any(|value| safe_int(Some(value), 0) != 0);
        if has_counts {
            match vendor {
                "claude" => {
                    let legacy = safe_int(bucket.get("cache_create"), 0);
                    let mut cache_create_5m = safe_int(bucket.get("cache_create_5m"), 0);
                    if cache_create_5m == 0 {
                        cache_create_5m = legacy;
                    }
                    argv.extend([
                        format!("--{flag_prefix}-input-tokens"),
                        safe_int(bucket.get("input"), 0).to_string(),
                        format!("--{flag_prefix}-cache-read-tokens"),
                        safe_int(bucket.get("cache_read"), 0).to_string(),
                        format!("--{flag_prefix}-cache-write-5m-tokens"),
                        cache_create_5m.to_string(),
                        format!("--{flag_prefix}-cache-write-1h-tokens"),
                        safe_int(bucket.get("cache_create_1h"), 0).to_string(),
                        format!("--{flag_prefix}-output-tokens"),
                        safe_int(bucket.get("output"), 0).to_string(),
                    ]);
                }
                "claude_sub" => argv.extend(claude_sub_token_argv(report, bucket)),
                "codex" => argv.extend(codex_token_argv(report, bucket)),
                _cursor => argv.extend(cursor_token_argv(report, bucket)),
            }
            continue;
        }
        let total = nested_object(report, vendor)
            .and_then(|totals| nested_object(totals, "totals"))
            .map_or(0, |totals| safe_int(totals.get("total"), 0));
        if total != 0 {
            argv.extend([format!("--{flag_prefix}-tokens"), total.to_string()]);
        }
    }
    argv
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn filed_urls_are_extracted_and_deduplicated() {
        let body = "- **Filed URL**: https://github.com/o/r/issues/12\n\
             - **Filed URL** : https://github.com/o/r/issues/12\n\
             - **Filed URL**: https://github.com/o/r/issues/notanumber\n";
        assert_eq!(
            filed_url_lines(body),
            vec![
                "https://github.com/o/r/issues/12".to_owned(),
                "https://github.com/o/r/issues/12".to_owned(),
            ]
        );
    }

    #[test]
    fn difficulty_line_matches_the_python_shape() {
        let record: Map<String, Value> = serde_json::from_str(
            r#"{"predicted_tier":"MODERATE","applied_tier":"HARD","floors_applied":["x"],
                "audit_upgrade":"HARD","override_source":"operator",
                "escalations":[{"round":2,"from_tier":"MODERATE","to_tier":"HARD","trigger":"panel"}],
                "panel_skipped":"trivial"}"#,
        )
        .expect("fixture parses");
        assert_eq!(
            difficulty_line(&record),
            "predicted MODERATE, applied HARD, floor raised, audit HARD, override operator, \
escalated r2 MODERATE->HARD panel, panel skipped: trivial"
        );
    }

    #[test]
    fn stalled_heading_rewrites_to_merged() {
        assert_eq!(
            rewrite_stalled_heading("## /implement run r1 \u{2014} stalled"),
            "## /implement run r1: merged"
        );
        assert_eq!(
            rewrite_stalled_heading("## /implement run r1: stalled"),
            "## /implement run r1: merged"
        );
    }

    #[test]
    fn stalled_outcome_lines_match_both_spellings() {
        assert!(stalled_outcome_line("- **Outcome**: \u{274c} stalled"));
        assert!(stalled_outcome_line("- **Outcome**: stalled"));
        assert!(stalled_outcome_line("- **Outcome**: DONE"));
        assert!(!stalled_outcome_line("- **Outcome**: \u{2705} DONE"));
    }

    fn manifest_only_run(summary: &str) -> tempfile::TempDir {
        let sandbox = tempfile::tempdir().expect("sandbox");
        let run_dir = sandbox
            .path()
            .join("larch-logs")
            .join("implement")
            .join("run-abc");
        fs::create_dir_all(&run_dir).expect("run directory");
        fs::write(
            run_dir.join("manifest.json"),
            r#"{"schema_version":2,"skill":"implement","run_id":"run-abc",
                "steps_ran":{},"status":"done","pr_number":12}"#,
        )
        .expect("manifest");
        fs::write(run_dir.join("final-summary.md"), summary).expect("summary");
        sandbox
    }

    fn run_dir_of(sandbox: &tempfile::TempDir) -> std::path::PathBuf {
        sandbox
            .path()
            .join("larch-logs")
            .join("implement")
            .join("run-abc")
    }

    #[test]
    fn manifest_only_stalled_summary_reconciles_every_recorded_spelling() {
        for (separator, outcome) in [
            (": ", "stalled"),
            (" \u{2014} ", "stalled"),
            (": ", "\u{274c} stalled"),
            (": ", "DONE"),
        ] {
            let sandbox = manifest_only_run(&format!(
                "prelude line\n\n## /implement run run-abc{separator}stalled\n\n\
- **Outcome**: {outcome}\n- **PR**: #12\n"
            ));
            let run_dir = run_dir_of(&sandbox);
            assert!(stalled_summary_manifest_reconciliation_needed(&run_dir));
            let rewritten = reconciled_stalled_summary(&run_dir).expect("rewritten summary");
            assert!(rewritten.contains("## /implement run run-abc: merged\n"));
            assert!(rewritten.contains("- **Outcome**: \u{2705} DONE\n"));
        }
    }

    #[test]
    fn an_outcome_bullet_without_a_stalled_heading_does_not_reconcile() {
        let sandbox = manifest_only_run("- **Outcome**: stalled\n- **PR**: #12\n");
        let run_dir = run_dir_of(&sandbox);
        assert!(!stalled_summary_manifest_reconciliation_needed(&run_dir));
        assert!(reconciled_stalled_summary(&run_dir).is_none());
    }

    #[test]
    fn a_populated_state_file_blocks_manifest_only_reconciliation() {
        let sandbox =
            manifest_only_run("## /implement run run-abc: stalled\n\n- **Outcome**: stalled\n");
        fs::write(sandbox.path().join("ship-pr-state.sh"), "PR_NUMBER=12\n").expect("state");
        let run_dir = run_dir_of(&sandbox);
        assert!(!stalled_summary_manifest_reconciliation_needed(&run_dir));
        assert!(reconciled_stalled_summary(&run_dir).is_none());
    }

    #[test]
    fn line_count_state_replaces_only_the_cached_rows() {
        let merged = merged_line_count_state(
            "PR_NUMBER=7\nCODE_ADDED=1\nLINES_STATUS=stale\n",
            "7",
            &[
                ("LINES_STATUS", "ok".to_owned()),
                ("CODE_ADDED", "9".to_owned()),
            ],
        );
        assert_eq!(
            merged,
            "PR_NUMBER=7\nLINES_PR_NUMBER=7\nLINES_STATUS=ok\nCODE_ADDED=9\n"
        );
    }

    #[test]
    fn token_argv_prefers_buckets_then_aggregate_totals() {
        let report: Map<String, Value> = serde_json::from_str(
            r#"{"BUCKETS_claude":{"input":10,"cache_read":0,"cache_create":5,"output":2},
                "codex":{"totals":{"total":42}}}"#,
        )
        .expect("fixture parses");
        assert_eq!(
            token_argv_from_report(&report),
            vec![
                "--claude-input-tokens",
                "10",
                "--claude-cache-read-tokens",
                "0",
                "--claude-cache-write-5m-tokens",
                "5",
                "--claude-cache-write-1h-tokens",
                "0",
                "--claude-output-tokens",
                "2",
                "--codex-tokens",
                "42",
            ]
        );
    }

    #[test]
    fn empty_report_yields_no_pricing_flags() {
        assert!(token_argv_from_report(&Map::new()).is_empty());
    }

    #[test]
    fn join_prefixed_summary_keeps_only_populated_sections() {
        assert_eq!(join_prefixed_summary(&["", "  "], "body\n"), "body\n");
        assert_eq!(
            join_prefixed_summary(&["one\n", "", "two"], "\nbody\n"),
            "one\n\ntwo\n\nbody\n"
        );
    }
}
