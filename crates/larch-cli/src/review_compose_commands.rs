//! Rust owner for composing review finding artifacts into the published JSONL.

use std::{
    collections::BTreeMap,
    ffi::OsString,
    fs,
    path::{Path, PathBuf},
    process::ExitCode,
};

use larch_core::{
    ensure_ascii_json, redact,
    review::{filter_plan_review_gate_b_skipped, is_security_block_text},
    split_text_lines,
};
use regex::Regex;
use serde_json::{Value, json};

const USAGE: &str = "usage: compose-findings [-h] [--design-artifacts-dir DESIGN_ARTIFACTS_DIR] [--implement-tmpdir IMPLEMENT_TMPDIR] --issue ISSUE --output OUTPUT [--archive-dir ARCHIVE_DIR] [--archive-threshold ARCHIVE_THRESHOLD]";
const ONE_BY_ONE_SKIP_MARKER: &str = "rejected by user during one-by-one review";
const FOCUS_AREAS: &[&str] = &[
    "code-quality",
    "risk-integration",
    "correctness",
    "architecture",
    "security",
];

#[derive(Default)]
struct ComposeArguments {
    design_dir: Option<PathBuf>,
    implement_dir: Option<PathBuf>,
    issue: String,
    output: Option<PathBuf>,
}

#[derive(Clone, Copy)]
enum ArtifactKind {
    PlanAccepted,
    PlanRejected,
    CodeAccepted,
    CodeRejected,
    CodeOos,
}

impl ArtifactKind {
    const fn phase(self) -> &'static str {
        match self {
            Self::PlanAccepted | Self::PlanRejected => "plan-review",
            Self::CodeAccepted | Self::CodeRejected | Self::CodeOos => "code-review",
        }
    }

    const fn outcome(self) -> &'static str {
        match self {
            Self::PlanAccepted | Self::CodeAccepted => "accepted",
            Self::PlanRejected | Self::CodeRejected => "rejected",
            Self::CodeOos => "out_of_scope",
        }
    }
}

/// Compose public review finding records from staged review artifacts.
#[allow(clippy::too_many_lines)] // Artifact precedence and final JSONL emission are one compatibility transaction.
pub fn compose_findings(arguments: &[OsString]) -> ExitCode {
    let args = match parse_arguments(arguments) {
        Ok(Some(args)) => args,
        Ok(None) => return ExitCode::SUCCESS,
        Err(message) => {
            eprintln!("{message}\n{USAGE}");
            return ExitCode::from(2);
        }
    };
    if !args.issue.bytes().all(|byte| byte.is_ascii_digit()) {
        return fail(&format!(
            "invalid value for --issue: '{}' (expected non-negative integer)",
            args.issue
        ));
    }
    let Some(output) = args.output else {
        return fail("the following arguments are required: --output");
    };
    let design_map = build_design_reviewer_map(args.design_dir.as_deref());
    let mut records = Vec::new();
    if let Some(design) = args.design_dir.as_deref() {
        let all = design.join("accepted-plan-findings-all.md");
        let accepted = if file_nonempty(&all) {
            all
        } else {
            design.join("accepted-plan-findings.md")
        };
        let accepted_text = if file_exists(&accepted)
            && read_text(&design.join("rejected-findings.md")).contains(ONE_BY_ONE_SKIP_MARKER)
        {
            filter_plan_review_gate_b_skipped(
                &read_text(&accepted),
                &read_text(&design.join("rejected-findings.md")),
            )
        } else {
            read_text(&accepted)
        };
        parse_artifact(
            &accepted_text,
            ArtifactKind::PlanAccepted,
            "",
            &args.issue,
            &design_map,
            &mut records,
        );
        parse_artifact(
            &read_text(&design.join("rejected-findings.md")),
            ArtifactKind::PlanRejected,
            "",
            &args.issue,
            &design_map,
            &mut records,
        );
    }
    if let Some(implement) = args.implement_dir.as_deref() {
        let mut round_dirs = fs::read_dir(implement)
            .ok()
            .into_iter()
            .flatten()
            .filter_map(Result::ok)
            .filter_map(|entry| {
                let path = entry.path();
                (path.is_dir() && entry.file_name().to_string_lossy().starts_with("round-"))
                    .then_some(path)
            })
            .collect::<Vec<_>>();
        round_dirs.sort();
        let mut rejected_found = false;
        for round in round_dirs {
            let round_num = round
                .file_name()
                .and_then(|value| value.to_str())
                .and_then(|value| value.strip_prefix("round-"))
                .unwrap_or("");
            parse_artifact(
                &read_text(&round.join("accepted-findings.md")),
                ArtifactKind::CodeAccepted,
                round_num,
                &args.issue,
                &design_map,
                &mut records,
            );
            parse_artifact(
                &read_text(&round.join("oos.md")),
                ArtifactKind::CodeOos,
                round_num,
                &args.issue,
                &design_map,
                &mut records,
            );
            let full = round.join("rejected-findings-full.md");
            let rejected = round.join("rejected-findings.md");
            if file_nonempty(&full) {
                rejected_found = true;
                parse_artifact(
                    &read_text(&full),
                    ArtifactKind::CodeRejected,
                    round_num,
                    &args.issue,
                    &design_map,
                    &mut records,
                );
            } else if file_nonempty(&rejected) {
                rejected_found = true;
                parse_artifact(
                    &read_text(&rejected),
                    ArtifactKind::CodeRejected,
                    round_num,
                    &args.issue,
                    &design_map,
                    &mut records,
                );
            }
        }
        if !rejected_found {
            let full = implement.join("rejected-findings-full.md");
            let rejected = if file_nonempty(&full) {
                full
            } else {
                implement.join("rejected-findings.md")
            };
            parse_artifact(
                &read_text(&rejected),
                ArtifactKind::CodeRejected,
                "",
                &args.issue,
                &design_map,
                &mut records,
            );
        }
    }
    let mut rendered = String::new();
    for record in records {
        let Ok(line) = serialize_ascii_json(&record) else {
            return fail("could not serialize composed finding record");
        };
        rendered.push_str(&line);
        rendered.push('\n');
    }
    if let Some(parent) = output.parent()
        && let Err(error) = fs::create_dir_all(parent)
    {
        return fail(&format!("cannot create output directory: {error}"));
    }
    if let Err(error) = fs::write(&output, &rendered) {
        return fail(&format!("cannot write output: {error}"));
    }
    emit("COMPOSED", "true");
    emit("OUTPUT", output.to_string_lossy().as_ref());
    emit("FINDINGS_TOTAL", &records_len(&rendered).to_string());
    emit("MODE", "jsonl");
    ExitCode::SUCCESS
}

fn records_len(rendered: &str) -> usize {
    split_text_lines(rendered)
        .into_iter()
        .filter(|line| !line.trim().is_empty())
        .count()
}

/// Match Python's `json.dumps(..., ensure_ascii=True)` wire representation.
///
/// `serde_json` emits non-ASCII scalars directly. The retired composer used
/// Python's default ASCII-only JSON encoder, so use the shared translator for
/// its escaped, UTF-16-surrogate-pair representation.
fn serialize_ascii_json(record: &Value) -> Result<String, serde_json::Error> {
    let rendered = serde_json::to_string(record)?;
    Ok(ensure_ascii_json(&rendered))
}

fn parse_arguments(arguments: &[OsString]) -> Result<Option<ComposeArguments>, String> {
    let raw = arguments
        .iter()
        .map(|value| value.to_string_lossy().into_owned())
        .collect::<Vec<_>>();
    if raw.iter().any(|value| value == "--help" || value == "-h") {
        println!("{USAGE}");
        return Ok(None);
    }
    let mut parsed = ComposeArguments::default();
    let mut index = 0;
    while index < raw.len() {
        let option = &raw[index];
        let Some(value) = raw.get(index + 1) else {
            return Err(format!("{option} requires a value"));
        };
        match option.as_str() {
            "--design-artifacts-dir" => {
                parsed.design_dir = (!value.is_empty()).then_some(PathBuf::from(value));
            }
            "--implement-tmpdir" => {
                parsed.implement_dir = (!value.is_empty()).then_some(PathBuf::from(value));
            }
            "--issue" => parsed.issue.clone_from(value),
            "--output" => parsed.output = Some(PathBuf::from(value)),
            "--archive-dir" | "--archive-threshold" => {}
            _ => return Err(format!("unrecognized arguments: {option}")),
        }
        index += 2;
    }
    if parsed.issue.is_empty() {
        return Err("the following arguments are required: --issue".to_owned());
    }
    if parsed.output.is_none() {
        return Err("the following arguments are required: --output".to_owned());
    }
    Ok(Some(parsed))
}

fn fail(message: &str) -> ExitCode {
    emit("FAILED", "true");
    emit("ERROR", message);
    ExitCode::from(2)
}

fn emit(key: &str, value: &str) {
    println!("{key}={value}");
}

#[allow(clippy::too_many_lines)] // The retired parser's ordered heading cases stay contiguous for parity review.
fn parse_artifact(
    text: &str,
    kind: ArtifactKind,
    round_num: &str,
    issue: &str,
    design_map: &BTreeMap<String, String>,
    records: &mut Vec<Value>,
) {
    if text.trim().is_empty() {
        return;
    }
    let canonical = Regex::new(r"^###\s+(FINDING_(?:[0-9]+|[A-Za-z_][0-9A-Za-z_]*)):\s*(.*)$")
        .expect("accepted heading regex");
    let plan_rejected =
        Regex::new(r"^###\s+\[Plan\s+Review\]\s+(.+)$").expect("plan rejected regex");
    let code_rejected =
        Regex::new(r"^###\s+\[(rejected|Code\s+Review)\]\s+(.+)$").expect("code rejected regex");
    let oos = Regex::new(r"^###\s+OOS_[0-9A-Za-z_]+:\s*(.*)$").expect("oos regex");
    let legacy_oos = Regex::new(r"^###\s+FINDING_[0-9A-Za-z_]+:\s*\[OUT_OF_SCOPE\]\s*(.*)$")
        .expect("legacy oos regex");
    let mut pending_id = String::new();
    let mut pending_title = String::new();
    let mut pending_reviewer = String::new();
    let mut pending_lines = Vec::new();
    let mut counter = 0_usize;
    let flush = |pending_id: &mut String,
                 pending_title: &mut String,
                 pending_reviewer: &mut String,
                 pending_lines: &mut Vec<String>,
                 records: &mut Vec<Value>| {
        if pending_id.is_empty() {
            return;
        }
        let mut body = pending_lines.join("\n");
        if !pending_title.is_empty() {
            body = format!("## {pending_title}\n\n{body}");
        }
        let reviewer = if pending_reviewer.is_empty() {
            extract_reviewer(&body).unwrap_or_else(|| "panel".to_owned())
        } else {
            pending_reviewer.clone()
        };
        if !(matches!(kind, ArtifactKind::CodeOos) && is_security_block_text(&body)) {
            records.push(record(
                pending_id, kind, round_num, issue, design_map, &reviewer, &body,
            ));
        }
        pending_id.clear();
        pending_title.clear();
        pending_reviewer.clear();
        pending_lines.clear();
    };
    for line in split_text_lines(text) {
        match kind {
            ArtifactKind::PlanAccepted | ArtifactKind::CodeAccepted => {
                if let Some(captures) = canonical.captures(line) {
                    flush(
                        &mut pending_id,
                        &mut pending_title,
                        &mut pending_reviewer,
                        &mut pending_lines,
                        records,
                    );
                    captures
                        .get(1)
                        .map_or("", |value| value.as_str())
                        .clone_into(&mut pending_id);
                    captures
                        .get(2)
                        .map_or("", |value| value.as_str())
                        .clone_into(&mut pending_title);
                    continue;
                }
            }
            ArtifactKind::PlanRejected => {
                if let Some(captures) = plan_rejected.captures(line) {
                    flush(
                        &mut pending_id,
                        &mut pending_title,
                        &mut pending_reviewer,
                        &mut pending_lines,
                        records,
                    );
                    counter += 1;
                    pending_id = synthetic_id("REJ_P", counter, round_num);
                    captures
                        .get(1)
                        .map_or("", |value| value.as_str())
                        .clone_into(&mut pending_reviewer);
                    continue;
                }
            }
            ArtifactKind::CodeRejected => {
                if let Some(captures) = code_rejected.captures(line) {
                    flush(
                        &mut pending_id,
                        &mut pending_title,
                        &mut pending_reviewer,
                        &mut pending_lines,
                        records,
                    );
                    counter += 1;
                    pending_id = synthetic_id("REJ_C", counter, round_num);
                    if captures.get(1).map_or("", |value| value.as_str()) == "Code Review" {
                        captures
                            .get(2)
                            .map_or("", |value| value.as_str())
                            .clone_into(&mut pending_reviewer);
                    }
                    continue;
                }
                if !pending_id.is_empty() && line.starts_with("### ") {
                    pending_lines.push(line.to_owned());
                    continue;
                }
            }
            ArtifactKind::CodeOos => {
                if let Some(captures) = oos.captures(line).or_else(|| legacy_oos.captures(line)) {
                    flush(
                        &mut pending_id,
                        &mut pending_title,
                        &mut pending_reviewer,
                        &mut pending_lines,
                        records,
                    );
                    counter += 1;
                    pending_id = synthetic_id("OOS_C", counter, round_num);
                    captures
                        .get(1)
                        .map_or("", |value| value.as_str())
                        .clone_into(&mut pending_title);
                    continue;
                }
                if !pending_id.is_empty() && line.starts_with("### ") {
                    pending_lines.push(line.to_owned());
                    continue;
                }
            }
        }
        if line.starts_with("### ") {
            flush(
                &mut pending_id,
                &mut pending_title,
                &mut pending_reviewer,
                &mut pending_lines,
                records,
            );
            continue;
        }
        if !pending_id.is_empty() {
            pending_lines.push(line.to_owned());
        }
    }
    flush(
        &mut pending_id,
        &mut pending_title,
        &mut pending_reviewer,
        &mut pending_lines,
        records,
    );
}

fn record(
    item_id: &str,
    kind: ArtifactKind,
    round_num: &str,
    issue: &str,
    design_map: &BTreeMap<String, String>,
    reviewer: &str,
    body: &str,
) -> Value {
    let reviewer = if matches!(
        kind,
        ArtifactKind::PlanAccepted | ArtifactKind::PlanRejected
    ) {
        normalize_design_reviewer(reviewer, design_map)
    } else {
        reviewer.to_owned()
    };
    let reviewer = redact(&reviewer).text().to_owned();
    let body = redact(body).text().to_owned();
    let strict = matches!(kind, ArtifactKind::CodeOos)
        || (matches!(kind, ArtifactKind::PlanAccepted) && kind.outcome() == "accepted");
    let reviewer_slots = reviewer
        .split(',')
        .map(str::trim)
        .filter(|value| !value.is_empty())
        .map(str::to_owned)
        .collect::<Vec<_>>();
    let reviewer_slots = if reviewer_slots.is_empty() {
        vec!["panel".to_owned()]
    } else {
        reviewer_slots
    };
    json!({
        "id": item_id,
        "issue_number": issue,
        "phase": kind.phase(),
        "outcome": kind.outcome(),
        "schema_version": "2",
        "reviewer_slots": reviewer_slots,
        "round_num": round_num,
        "category": extract_category(&body, strict),
        "body_severity": extract_field(&body, "Severity", false),
        "focus_area": extract_field(&body, "Focus area", true),
        "prose_body": truncate_chars(&body, 2000),
    })
}

fn synthetic_id(prefix: &str, counter: usize, round: &str) -> String {
    if round.is_empty() {
        format!("{prefix}{counter}")
    } else {
        format!("{prefix}R{round}_{counter}")
    }
}
fn extract_field(body: &str, field: &str, insensitive: bool) -> String {
    let pattern = if insensitive {
        format!(r"(?i)^[\s-]*\*\*{}\*\*:\s*(.*?)\s*$", regex::escape(field))
    } else {
        format!(r"^[\s-]*\*\*{}\*\*:\s*(.*?)\s*$", regex::escape(field))
    };
    let regex = Regex::new(&pattern).expect("field regex");
    split_text_lines(body)
        .into_iter()
        .find_map(|line| {
            regex
                .captures(line)
                .and_then(|captures| captures.get(1).map(|value| value.as_str().to_owned()))
        })
        .unwrap_or_default()
}
fn extract_reviewer(body: &str) -> Option<String> {
    let patterns = [
        r"^[\s-]*\*\*Reviewer\(s\)\*\*:\s*(.+)$",
        r"^[\s-]*\*\*Reviewers?\*\*:\s*(.+)$",
        r"^[\s-]*Reviewer\(s\):\s*(.+)$",
        r"^[\s-]*Reviewers?:\s*(.+)$",
    ];
    for pattern in patterns {
        let regex = Regex::new(pattern).expect("reviewer regex");
        if let Some(value) = split_text_lines(body).into_iter().find_map(|line| {
            regex.captures(line).and_then(|captures| {
                captures
                    .get(1)
                    .map(|value| value.as_str().replace('*', "").trim().to_owned())
            })
        }) {
            return Some(value);
        }
    }
    None
}
fn extract_category(body: &str, strict: bool) -> String {
    for line in split_text_lines(body) {
        if let Some(rest) = line
            .strip_prefix("### FINDING_")
            .and_then(|value| value.split_once(':').map(|(_, rest)| rest.trim()))
        {
            let parts = rest.split(':').map(str::trim).collect::<Vec<_>>();
            let candidate = if parts.len() >= 3
                || parts
                    .first()
                    .is_some_and(|value| FOCUS_AREAS.contains(value))
            {
                parts.first().copied().unwrap_or("")
            } else {
                ""
            };
            if !candidate.is_empty() && (!strict || FOCUS_AREAS.contains(&candidate)) {
                return candidate.to_owned();
            }
        }
        if let Some(mut candidate) = line.strip_prefix("## ").map(str::trim) {
            if let Some(bold) = candidate
                .strip_prefix("**")
                .and_then(|value| value.split_once("**").map(|(value, _)| value))
            {
                candidate = bold;
            } else {
                candidate = candidate
                    .split_once(':')
                    .map_or(candidate, |(value, _)| value)
                    .trim();
            }
            if !candidate.is_empty() && (!strict || FOCUS_AREAS.contains(&candidate)) {
                return candidate.to_owned();
            }
        }
        if let Some(rest) = line.strip_prefix("## ") {
            let mut candidate = rest.trim();
            if candidate.starts_with("**") {
                candidate = candidate
                    .strip_prefix("**")
                    .and_then(|value| value.split("**").next())
                    .unwrap_or(candidate);
            } else {
                candidate = candidate.split(':').next().unwrap_or(candidate).trim();
            }
            if !candidate.is_empty() && (!strict || FOCUS_AREAS.contains(&candidate)) {
                return candidate.to_owned();
            }
        }
    }
    String::new()
}
fn truncate_chars(value: &str, max: usize) -> String {
    value.chars().take(max).collect()
}

fn build_design_reviewer_map(design: Option<&Path>) -> BTreeMap<String, String> {
    let mut mapping = BTreeMap::new();
    let Some(design) = design else {
        return mapping;
    };
    let rounds = design.join("plan-review");
    let mut manifests = Vec::new();
    if rounds.is_dir() {
        let mut round_paths = fs::read_dir(&rounds)
            .ok()
            .into_iter()
            .flatten()
            .filter_map(Result::ok)
            .filter_map(|entry| {
                let path = entry.path();
                let name = entry.file_name().to_string_lossy().into_owned();
                (path.is_dir()
                    && Regex::new(r"^round-[0-9]+$")
                        .expect("round regex")
                        .is_match(&name))
                .then_some(path.join("plan-review-slots.ndjson"))
            })
            .collect::<Vec<_>>();
        round_paths.sort_by_key(|path| {
            numeric_round(
                path.parent()
                    .and_then(Path::file_name)
                    .and_then(|value| value.to_str())
                    .unwrap_or(""),
            )
        });
        manifests.extend(round_paths);
    }
    manifests.push(design.join("plan-review-slots.ndjson"));
    for manifest in manifests {
        for line in split_text_lines(&read_text(&manifest)) {
            let Ok(Value::Object(row)) = serde_json::from_str::<Value>(line) else {
                continue;
            };
            let output = row.get("output").and_then(Value::as_str).unwrap_or("");
            let base = Path::new(output)
                .file_name()
                .and_then(|value| value.to_str())
                .unwrap_or("");
            let slot = row.get("slot").and_then(Value::as_str).unwrap_or("");
            if !base.is_empty() {
                if !slot.is_empty() {
                    mapping
                        .entry(slot.to_owned())
                        .or_insert_with(|| base.to_owned());
                }
                let human = human_label(slot);
                if !human.is_empty() {
                    mapping.entry(human).or_insert_with(|| base.to_owned());
                }
            }
        }
    }
    let mut labels = vec![design.join("plan-review-prune-label-map.tsv")];
    if rounds.is_dir() {
        let mut paths = fs::read_dir(&rounds)
            .ok()
            .into_iter()
            .flatten()
            .filter_map(Result::ok)
            .map(|entry| entry.path())
            .filter(|path| path.is_dir())
            .collect::<Vec<_>>();
        paths.sort();
        labels.extend(
            paths
                .into_iter()
                .map(|path| path.join("plan-review-prune-label-map.tsv")),
        );
    }
    for label in labels {
        for line in split_text_lines(&read_text(&label)) {
            let fields = line.split('\t').collect::<Vec<_>>();
            if fields.len() >= 2 {
                let slot = fields[0].trim();
                let label = fields[1].trim();
                if let Some(output) = mapping.get(slot).cloned()
                    && !label.is_empty()
                {
                    mapping.entry(label.to_owned()).or_insert(output);
                }
            }
        }
    }
    mapping
}

fn numeric_round(name: &str) -> u64 {
    name.strip_prefix("round-")
        .and_then(|value| value.parse().ok())
        .unwrap_or(0)
}
fn human_label(slot: &str) -> String {
    for (prefix, label, dynamic) in [
        ("dyn-cursor-plan-", "Cursor-dyn-", true),
        ("dyn-codex-plan-", "Codex-dyn-", true),
        ("cursor-plan-", "Cursor-", false),
        ("codex-plan-", "Codex-", false),
        ("claude-plan-", "Claude-", false),
    ] {
        if let Some(rest) = slot.strip_prefix(prefix) {
            return if dynamic {
                format!("{label}{rest}")
            } else {
                format!(
                    "{label}{}",
                    rest.split(['_', ' '])
                        .filter(|part| !part.is_empty())
                        .map(|part| {
                            let mut chars = part.chars();
                            chars
                                .next()
                                .map(|first| {
                                    first.to_ascii_uppercase().to_string() + chars.as_str()
                                })
                                .unwrap_or_default()
                        })
                        .collect::<String>()
                )
            };
        }
    }
    slot.to_owned()
}
fn normalize_design_reviewer(value: &str, mapping: &BTreeMap<String, String>) -> String {
    if mapping.is_empty() {
        return value.to_owned();
    }
    let values = value
        .split(',')
        .map(str::trim)
        .filter(|part| !part.is_empty())
        .map(|part| {
            mapping
                .get(part)
                .cloned()
                .unwrap_or_else(|| part.to_owned())
        })
        .collect::<Vec<_>>();
    if values.is_empty() {
        value.to_owned()
    } else {
        values.join(",")
    }
}

fn read_text(path: &Path) -> String {
    fs::read(path)
        .map(|bytes| String::from_utf8_lossy(&bytes).into_owned())
        .unwrap_or_default()
}
fn file_exists(path: &Path) -> bool {
    path.is_file()
}
fn file_nonempty(path: &Path) -> bool {
    file_exists(path)
        && fs::metadata(path)
            .map(|metadata| metadata.len() > 0)
            .unwrap_or(false)
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    #[test]
    fn gate_b_filter_preserves_only_unskipped_accepted_blocks() {
        let accepted =
            "### FINDING_1: keep\n- **Concern**: x\n\n### FINDING_2: skip\n- **Concern**: y\n";
        let rejected = "### FINDING_2: skip\n- **Concern**: y\n- Reason: rejected by user during one-by-one review\n";
        let filtered = filter_plan_review_gate_b_skipped(accepted, rejected);
        assert!(filtered.contains("FINDING_1"));
        assert!(!filtered.contains("FINDING_2"));
    }

    #[test]
    fn composition_applies_the_shared_gate_b_skip_filter() {
        let sandbox = TempDir::new().expect("sandbox");
        let design = sandbox.path().join("design");
        fs::create_dir_all(&design).expect("design");
        fs::write(
            design.join("accepted-plan-findings-all.md"),
            "### FINDING_1: retain\n- **Concern**: keep\n\n### FINDING_2: skip\n- **Concern**: remove\n",
        )
        .expect("accepted findings");
        fs::write(
            design.join("rejected-findings.md"),
            "### FINDING_2: skip\n- **Concern**: remove\n- Reason: rejected by user during one-by-one review\n",
        )
        .expect("rejected findings");
        let output = sandbox.path().join("out.jsonl");
        let args = [
            "--design-artifacts-dir",
            design.to_str().expect("utf8"),
            "--issue",
            "1",
            "--output",
            output.to_str().expect("utf8"),
        ]
        .into_iter()
        .map(OsString::from)
        .collect::<Vec<_>>();

        assert_eq!(compose_findings(&args), ExitCode::SUCCESS);
        let rendered = read_text(&output);
        assert!(rendered.contains("FINDING_1"));
        assert!(!rendered.contains("FINDING_2"));
    }

    #[test]
    fn composition_redacts_body_before_publication() {
        let sandbox = TempDir::new().expect("sandbox");
        let input = sandbox.path().join("impl/round-1");
        fs::create_dir_all(&input).expect("round");
        fs::write(input.join("accepted-findings.md"), "### FINDING_1: title\n- **Reviewer**: panel\n- **Concern**: sk-ant-abcdefghijklmnopqrstuvwxyz0123456789ABCD\n").expect("finding");
        let output = sandbox.path().join("out.jsonl");
        let args = [
            "--implement-tmpdir",
            sandbox.path().join("impl").to_str().expect("utf8"),
            "--issue",
            "1",
            "--output",
            output.to_str().expect("utf8"),
        ]
        .into_iter()
        .map(OsString::from)
        .collect::<Vec<_>>();
        assert_eq!(compose_findings(&args), ExitCode::SUCCESS);
        let rendered = read_text(&output);
        assert!(!rendered.contains("sk-ant-abcdefghijklmnopqrstuvwxyz0123456789ABCD"));
        assert!(rendered.contains("<REDACTED-TOKEN>"));
    }

    #[test]
    fn composition_keeps_python_ascii_json_wire_encoding() {
        let record = json!({"title": "Important \u{007f} — supplementary 😀"});
        assert_eq!(
            serialize_ascii_json(&record).expect("json"),
            r#"{"title":"Important \u007f \u2014 supplementary \ud83d\ude00"}"#
        );
    }

    #[test]
    fn composition_uses_python_unicode_line_boundaries() {
        let sandbox = TempDir::new().expect("sandbox");
        let input = sandbox.path().join("impl/round-1");
        fs::create_dir_all(&input).expect("round");
        fs::write(
            input.join("accepted-findings.md"),
            "### FINDING_1: title\u{007f}\u{0080}\u{2028}😀\n- **Reviewer**: panel\n",
        )
        .expect("finding");
        let output = sandbox.path().join("out.jsonl");
        let args = [
            "--implement-tmpdir",
            sandbox.path().join("impl").to_str().expect("utf8"),
            "--issue",
            "1",
            "--output",
            output.to_str().expect("utf8"),
        ]
        .into_iter()
        .map(OsString::from)
        .collect::<Vec<_>>();
        assert_eq!(compose_findings(&args), ExitCode::SUCCESS);
        let record = serde_json::from_str::<Value>(read_text(&output).trim()).expect("record");
        assert_eq!(record["category"], "title\u{007f}\u{0080}");
        assert_eq!(
            record["prose_body"],
            "## title\u{007f}\u{0080}\n\n😀\n- **Reviewer**: panel"
        );
    }

    #[test]
    #[allow(clippy::too_many_lines)] // One parity fixture needs all artifact precedence cases visible together.
    fn composition_preserves_artifact_precedence_reviewer_aliases_and_all_outcomes() {
        let sandbox = TempDir::new().expect("sandbox");
        let design = sandbox.path().join("design");
        let round_two = design.join("plan-review/round-2");
        fs::create_dir_all(&round_two).expect("design rounds");
        fs::write(
            design.join("plan-review-slots.ndjson"),
            r#"{"slot":"codex-plan-security_scan","output":"/artifacts/slot-security.txt"}
not-json
"#,
        )
        .expect("root slots");
        fs::write(
            design.join("plan-review-prune-label-map.tsv"),
            "codex-plan-security_scan\tSecurity Experts\n",
        )
        .expect("root labels");
        fs::write(
            round_two.join("plan-review-slots.ndjson"),
            r#"{"slot":"dyn-cursor-plan-risk","output":"/artifacts/slot-risk.txt"}
"#,
        )
        .expect("round slots");
        fs::write(
            round_two.join("plan-review-prune-label-map.tsv"),
            "dyn-cursor-plan-risk\tRisk Panel\n",
        )
        .expect("round labels");
        fs::write(
            design.join("accepted-plan-findings.md"),
            "### FINDING_1: architecture: source: plan detail\n- **Reviewer(s)**: Security Experts\n- **Severity**: high\n- **Focus area**: ARCHITECTURE\n",
        )
        .expect("accepted plan findings");
        fs::write(
            design.join("rejected-findings.md"),
            "### [Plan Review] Risk Panel\n- **Concern**: rejected plan detail\n",
        )
        .expect("rejected plan findings");

        let implementation = sandbox.path().join("implementation");
        let round_two = implementation.join("round-2");
        let round_ten = implementation.join("round-10");
        fs::create_dir_all(&round_two).expect("round two");
        fs::create_dir_all(&round_ten).expect("round ten");
        fs::write(
            round_two.join("accepted-findings.md"),
            "### FINDING_2: correctness: source: code detail\n- **Reviewer**: code-reviewer\n- **Severity**: medium\n- **Focus area**: TESTING\n",
        )
        .expect("accepted code findings");
        fs::write(
            round_two.join("oos.md"),
            "### OOS_1: risk-integration: scope detail\n- **Reviewer**: scope-reviewer\n",
        )
        .expect("oos findings");
        fs::write(
            round_two.join("rejected-findings-full.md"),
            "### [Code Review] code-rejector\n- **Concern**: rejected code detail\n",
        )
        .expect("full rejected findings");
        fs::write(
            round_ten.join("rejected-findings.md"),
            "### [rejected] ignored title\n- **Reviewer**: fallback-rejector\n- **Concern**: fallback rejection\n",
        )
        .expect("rejected findings");

        let mapping = build_design_reviewer_map(Some(&design));
        assert_eq!(
            mapping.get("Security Experts").map(String::as_str),
            Some("slot-security.txt")
        );
        assert_eq!(
            mapping.get("Risk Panel").map(String::as_str),
            Some("slot-risk.txt")
        );
        assert_eq!(
            mapping.get("Cursor-dyn-risk").map(String::as_str),
            Some("slot-risk.txt")
        );

        let output = sandbox.path().join("public/reports/findings.jsonl");
        let args = [
            "--design-artifacts-dir",
            design.to_str().expect("utf8"),
            "--implement-tmpdir",
            implementation.to_str().expect("utf8"),
            "--issue",
            "8455",
            "--archive-dir",
            "unused",
            "--archive-threshold",
            "99",
            "--output",
            output.to_str().expect("utf8"),
        ]
        .into_iter()
        .map(OsString::from)
        .collect::<Vec<_>>();

        assert_eq!(compose_findings(&args), ExitCode::SUCCESS);
        let records = split_text_lines(&read_text(&output))
            .into_iter()
            .map(|line| serde_json::from_str::<Value>(line).expect("json record"))
            .collect::<Vec<_>>();
        assert_eq!(records.len(), 6);
        assert!(records.iter().any(|record| {
            record["id"] == "FINDING_1"
                && record["phase"] == "plan-review"
                && record["outcome"] == "accepted"
                && record["reviewer_slots"] == json!(["slot-security.txt"])
                && record["category"] == "architecture"
        }));
        assert!(records.iter().any(|record| {
            record["id"] == "REJ_P1"
                && record["outcome"] == "rejected"
                && record["reviewer_slots"] == json!(["slot-risk.txt"])
        }));
        assert!(records.iter().any(|record| {
            record["id"] == "FINDING_2"
                && record["round_num"] == "2"
                && record["category"] == "correctness"
        }));
        assert!(records.iter().any(|record| {
            record["id"] == "OOS_CR2_1"
                && record["outcome"] == "out_of_scope"
                && record["category"] == "risk-integration"
        }));
        assert!(records.iter().any(|record| {
            record["id"] == "REJ_CR2_1" && record["reviewer_slots"] == json!(["code-rejector"])
        }));
        assert!(records.iter().any(|record| {
            record["id"] == "REJ_CR10_1" && record["reviewer_slots"] == json!(["fallback-rejector"])
        }));
    }

    #[test]
    fn composition_accepts_legacy_oos_and_root_rejected_fallbacks() {
        let sandbox = TempDir::new().expect("sandbox");
        let implementation = sandbox.path().join("implementation");
        let round = implementation.join("round-3");
        fs::create_dir_all(&round).expect("round");
        fs::write(
            round.join("oos.md"),
            "### FINDING_8: [OUT_OF_SCOPE] security: deferred scope detail\n- **Reviewer**: scope-reviewer\n",
        )
        .expect("legacy oos");
        fs::write(
            implementation.join("rejected-findings-full.md"),
            "### [rejected] root fallback\n- **Reviewer**: root-rejector\n- **Concern**: fallback detail\n",
        )
        .expect("root rejected findings");
        let output = sandbox.path().join("out.jsonl");
        let args = [
            "--implement-tmpdir",
            implementation.to_str().expect("utf8"),
            "--issue",
            "0",
            "--output",
            output.to_str().expect("utf8"),
        ]
        .into_iter()
        .map(OsString::from)
        .collect::<Vec<_>>();

        assert_eq!(compose_findings(&args), ExitCode::SUCCESS);
        let rendered = read_text(&output);
        assert!(rendered.contains("OOS_CR3_1"));
        assert!(rendered.contains("REJ_C1"));
        assert!(rendered.contains("root-rejector"));

        let invalid = ["--issue", "invalid", "--output", "out.jsonl"]
            .into_iter()
            .map(OsString::from)
            .collect::<Vec<_>>();
        assert_eq!(compose_findings(&invalid), ExitCode::from(2));
        assert!(matches!(
            parse_arguments(&[OsString::from("--issue")]),
            Err(message) if message == "--issue requires a value"
        ));
        assert!(matches!(
            parse_arguments(&[
                OsString::from("--issue"),
                OsString::from("1"),
                OsString::from("--output"),
                OsString::from("out.jsonl"),
                OsString::from("--unexpected"),
                OsString::from("value"),
            ]),
            Err(message) if message == "unrecognized arguments: --unexpected"
        ));
    }
}
