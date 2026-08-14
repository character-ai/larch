//! Shared merge-sweep funnel used by `/validate-merged` and analyze-bugs report.
//!
//! Finder and refuter JSONL are untrusted agent output: every row is schema-
//! checked, bounded, and rejected on a foreign SHA before any durable write.

use std::{
    cmp::Reverse,
    collections::{BTreeMap, BTreeSet},
    env, fs,
    path::{Path, PathBuf},
    time::{SystemTime, UNIX_EPOCH},
};

use larch_adapters::{GixRepository, unified_blob_diff};
use larch_core::{ChangeKind, ObjectId, RepositoryRead, Revision};
use regex::Regex;
use serde_json::{Map, Value, json};
use std::sync::LazyLock;

use crate::admission_commands::fetch_origin_main;
use crate::analyze_bugs_commands::{
    exact_keys, full_sha, private_dir, private_write, repository_path_text,
};

pub const SWEEP_SCHEMA_VERSION: u64 = 1;
const SWEEP_INITIAL_WINDOW_SECONDS: u64 = 48 * 60 * 60;
const SWEEP_DIFF_CAP: usize = 60_000;
const SWEEP_SYMBOL_CAP: usize = 40;
const SWEEP_CONSUMER_CAP: usize = 40;
const SWEEP_FINDINGS_PER_MERGE_CAP: usize = 10;
const SWEEP_FINDING_FILE_CAP: usize = 512;
const SWEEP_FINDING_SYMBOL_CAP: usize = 200;
const SWEEP_FINDING_DESC_CAP: usize = 2000;
const MAX_WALK: usize = 20_000;
const MAX_CONSUMER_FILES: usize = 25_000;
const MAX_JSON_BYTES: u64 = 64 * 1024 * 1024;

pub const SWEEP_STATE_FILENAME: &str = "sweep-state.json";
pub const SWEEP_FINDER_RAW_NAME: &str = "sweep-finder.jsonl";
pub const SWEEP_REFUTER_RAW_NAME: &str = "sweep-refuter.jsonl";
pub const SWEEP_REFUTER_QUEUE_NAME: &str = "sweep-refuter-queue.jsonl";
pub const SWEEP_VALIDATED_NAME: &str = "sweep-validated.json";
pub const SWEEP_SELECTED_MANIFEST_NAME: &str = "sweep-selected-merges.json";
pub const SWEEP_BUNDLE_MANIFEST_NAME: &str = "sweep-bundle-paths.json";
pub const SWEEP_PREPARE_SUMMARY_NAME: &str = "sweep-prepare.json";

static PY_DEF: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^\+\s*(?:async\s+)?def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(").expect("def symbol regex")
});
static PY_CLASS: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^\+\s*class\s+([A-Za-z_][A-Za-z0-9_]*)\s*[:(]").expect("class symbol regex")
});
static PY_CONST: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^\+\s*([A-Z][A-Z0-9_]{2,})\s*=").expect("const symbol regex"));

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct SweepFinding {
    pub file: String,
    pub symbol: String,
    pub description: String,
    pub severity: String,
    pub confidence: String,
}

#[derive(Clone, Debug)]
struct SweepCommit {
    merge_sha: String,
    base_sha: String,
    subject: String,
    touched_paths: Vec<String>,
    diff_size: usize,
    capped_diff: String,
    diff_truncated: bool,
    changed_symbols: Vec<String>,
    symbols_truncated: bool,
    is_chronic: bool,
    history_order: usize,
}

#[derive(Clone, Debug)]
struct ConsumerHit {
    path: String,
    line: usize,
    text: String,
}

#[derive(Clone, Debug)]
pub struct SweepPrepareResult {
    pub rows: Vec<(String, String)>,
}

pub fn sweep_state_path(ledger_path: &Path) -> Result<PathBuf, String> {
    let ledger_path = absolute_path(ledger_path)?;
    let parent = ledger_path
        .parent()
        .ok_or_else(|| "ledger path has no parent for sweep state".to_owned())?;
    Ok(parent.join(SWEEP_STATE_FILENAME))
}

#[allow(clippy::too_many_lines)] // Shared first-parent selection writes every coupled sweep artifact.
pub fn sweep_prepare(
    run_dir: &Path,
    ledger_path: &Path,
    repo: &str,
    sweep_max: usize,
) -> Result<SweepPrepareResult, String> {
    if sweep_max == 0 {
        return Err("--max-merges must be a positive integer".to_owned());
    }
    let _ = repo;
    private_dir(run_dir)?;
    let cwd = env::current_dir().map_err(|error| format!("could not pin origin/main: {error}"))?;
    let _ = fetch_origin_main(&cwd);
    let repository =
        GixRepository::discover(&cwd).map_err(|_| "could not pin origin/main".to_owned())?;
    let tip_id = repository
        .resolve_revision(&Revision::new(b"origin/main"))
        .map_err(|_| "could not pin origin/main".to_owned())?;
    let pinned_tip = require_full_sha(&tip_id.to_hex(), "origin/main tip")?;
    let state_path = sweep_state_path(ledger_path)?;
    let state = load_sweep_state(&state_path)?;
    if let Some(state) = &state {
        require_reachable(
            &repository,
            &state.last_sweep_sha,
            &tip_id,
            "last_sweep_sha",
        )?;
        for pending in &state.pending_shas {
            require_reachable(&repository, pending, &tip_id, "pending SHA")?;
        }
    }
    let now = unix_now()?;
    let window = enumerate_first_parent_merges(&repository, &tip_id, state.as_ref(), now)?;
    let mut eligible = BTreeMap::new();
    let mut history_order = 0usize;
    for (sha, subject, commit_time) in window {
        if excluded_subject(&subject) {
            continue;
        }
        let Some(commit) = build_commit(
            &repository,
            &sha,
            &subject,
            commit_time,
            history_order,
            SWEEP_DIFF_CAP,
        )?
        else {
            continue;
        };
        if larch_logs_only(&commit.touched_paths) {
            continue;
        }
        eligible.insert(sha, commit);
        history_order += 1;
    }
    if let Some(state) = &state {
        for pending in &state.pending_shas {
            if eligible.contains_key(pending) {
                continue;
            }
            let (subject, commit_time) = subject_and_time(&repository, pending)?;
            if excluded_subject(&subject) {
                continue;
            }
            let Some(commit) = build_commit(
                &repository,
                pending,
                &subject,
                commit_time,
                history_order,
                SWEEP_DIFF_CAP,
            )?
            else {
                continue;
            };
            if larch_logs_only(&commit.touched_paths) {
                continue;
            }
            eligible.insert(pending.clone(), commit);
            history_order += 1;
        }
    }
    let mut ranked = eligible.into_values().collect::<Vec<_>>();
    ranked.sort_by_key(|commit| {
        (
            u8::from(!commit.is_chronic),
            Reverse(commit.diff_size),
            commit.history_order,
            commit.merge_sha.clone(),
        )
    });
    let selected = ranked.iter().take(sweep_max).cloned().collect::<Vec<_>>();
    let pending = ranked
        .iter()
        .skip(sweep_max)
        .map(|commit| commit.merge_sha.clone())
        .collect::<Vec<_>>();
    let skipped = pending.len();
    let coverage_incomplete = skipped > 0;
    let bundles = write_bundles(&repository, run_dir, &pinned_tip, &selected)?;
    if bundles.len() != selected.len() {
        return Err("partial sweep bundle coverage".to_owned());
    }
    let selected_path = run_dir.join(SWEEP_SELECTED_MANIFEST_NAME);
    let bundle_manifest_path = run_dir.join(SWEEP_BUNDLE_MANIFEST_NAME);
    let summary_path = run_dir.join(SWEEP_PREPARE_SUMMARY_NAME);
    let selected_payload = json!({
        "coverage_incomplete": coverage_incomplete,
        "pending_shas": pending,
        "pinned_tip": pinned_tip,
        "selected": selected.iter().map(|commit| {
            json!({
                "base_sha": commit.base_sha,
                "bundle_path": run_dir.join(format!("sweep-{}-bundle.md", commit.merge_sha)).display().to_string(),
                "chronic_zones": Value::Array(Vec::new()),
                "diff_size": commit.diff_size,
                "is_chronic": false,
                "merge_sha": commit.merge_sha,
                "subject": commit.subject,
                "touched_paths": commit.touched_paths,
            })
        }).collect::<Vec<_>>(),
        "selected_count": selected.len(),
        "skipped_count": skipped,
    });
    let bundle_payload = json!({
        "bundles": selected.iter().map(|commit| json!({
            "merge_sha": commit.merge_sha,
            "path": run_dir.join(format!("sweep-{}-bundle.md", commit.merge_sha)).display().to_string(),
        })).collect::<Vec<_>>(),
        "pinned_tip": pinned_tip,
    });
    let summary_payload = json!({
        "bundle_path_manifest": bundle_manifest_path.display().to_string(),
        "chronic_zone_names": Value::Array(Vec::new()),
        "coverage_incomplete": coverage_incomplete,
        "finder_raw_path": run_dir.join(SWEEP_FINDER_RAW_NAME).display().to_string(),
        "pending_shas": pending,
        "pinned_tip": pinned_tip,
        "refuter_raw_path": run_dir.join(SWEEP_REFUTER_RAW_NAME).display().to_string(),
        "selected_count": selected.len(),
        "selected_merge_manifest": selected_path.display().to_string(),
        "skipped_count": skipped,
        "state_path": state_path.display().to_string(),
    });
    write_sorted_json(&selected_path, &selected_payload)?;
    write_sorted_json(&bundle_manifest_path, &bundle_payload)?;
    write_sorted_json(&summary_path, &summary_payload)?;
    Ok(SweepPrepareResult {
        rows: vec![
            ("PINNED_TIP".to_owned(), pinned_tip),
            (
                "SELECTED_MERGE_MANIFEST".to_owned(),
                selected_path.display().to_string(),
            ),
            (
                "BUNDLE_PATH_MANIFEST".to_owned(),
                bundle_manifest_path.display().to_string(),
            ),
            ("SELECTED_COUNT".to_owned(), selected.len().to_string()),
            ("SKIPPED_COUNT".to_owned(), skipped.to_string()),
            (
                "PENDING_SHAS".to_owned(),
                compact_json(&Value::Array(
                    pending.into_iter().map(Value::String).collect(),
                ))?,
            ),
            (
                "COVERAGE_INCOMPLETE".to_owned(),
                if coverage_incomplete {
                    "true".to_owned()
                } else {
                    "false".to_owned()
                },
            ),
            ("STATE_PATH".to_owned(), state_path.display().to_string()),
            ("RUN_DIR".to_owned(), run_dir.display().to_string()),
            (
                "SWEEP_FINDER_RAW_PATH".to_owned(),
                run_dir.join(SWEEP_FINDER_RAW_NAME).display().to_string(),
            ),
            (
                "SWEEP_REFUTER_RAW_PATH".to_owned(),
                run_dir.join(SWEEP_REFUTER_RAW_NAME).display().to_string(),
            ),
            (
                "SWEEP_PREPARE_SUMMARY".to_owned(),
                summary_path.display().to_string(),
            ),
        ],
    })
}

pub fn write_sweep_state(
    path: &Path,
    last_sweep_sha: &str,
    last_sweep_at: &str,
    pending_shas: &[String],
) -> Result<(), String> {
    let last_sweep_sha = require_full_sha(last_sweep_sha, "last_sweep_sha")?;
    if !sweep_timestamp(last_sweep_at) {
        return Err("last_sweep_at must be an ISO-8601 UTC timestamp ending in Z".to_owned());
    }
    let mut seen = BTreeSet::new();
    let mut pending = Vec::new();
    for sha in pending_shas {
        let sha = require_full_sha(sha, "pending_shas entry")?;
        if !seen.insert(sha.clone()) {
            return Err(format!("duplicate pending SHA: {sha}"));
        }
        pending.push(sha);
    }
    write_sorted_json(
        path,
        &json!({
            "last_sweep_at": last_sweep_at,
            "last_sweep_sha": last_sweep_sha,
            "pending_shas": pending,
            "schema_version": SWEEP_SCHEMA_VERSION,
        }),
    )
}

pub fn sweep_ingest_finder(run_dir: &Path) -> Result<Vec<(String, String)>, String> {
    let (pinned_tip, selected_shas, summary) = load_selected_manifest(run_dir)?;
    let queue_path = run_dir.join(SWEEP_REFUTER_QUEUE_NAME);
    let finder_raw_path = run_dir.join(SWEEP_FINDER_RAW_NAME);
    if selected_shas.is_empty() {
        private_write(&queue_path, "")?;
        return Ok(finder_payload(
            &pinned_tip,
            &summary.manifest_path,
            0,
            &queue_path,
            0,
        ));
    }
    if !finder_raw_path.is_file() {
        return Err(format!(
            "finder raw capture missing: {}",
            finder_raw_path.display()
        ));
    }
    let raw_rows = read_strict_jsonl(&finder_raw_path, "finder raw")?;
    if raw_rows.is_empty() {
        return Err(format!(
            "finder raw capture is empty: {}",
            finder_raw_path.display()
        ));
    }
    let selected_set = selected_shas.iter().cloned().collect::<BTreeSet<_>>();
    let mut accepted = BTreeMap::new();
    for (index, raw) in raw_rows.iter().enumerate() {
        let lineno = index + 1;
        let parsed =
            parse_finder_row(raw).map_err(|error| format!("finder raw line {lineno}: {error}"))?;
        if accepted.contains_key(&parsed.0) {
            return Err(format!(
                "finder raw line {lineno}: duplicate merge_sha {}",
                parsed.0
            ));
        }
        if !selected_set.contains(&parsed.0) {
            return Err(format!(
                "finder raw line {lineno}: foreign merge_sha {}",
                parsed.0
            ));
        }
        accepted.insert(parsed.0, parsed.1);
    }
    let missing = selected_shas
        .iter()
        .filter(|sha| !accepted.contains_key(*sha))
        .cloned()
        .collect::<Vec<_>>();
    if !missing.is_empty() {
        return Err(format!(
            "finder raw missing selected merges: {}",
            missing.join(", ")
        ));
    }
    let mut queue_rows = Vec::new();
    for sha in &selected_shas {
        for (finding_index, finding) in accepted[sha].iter().enumerate() {
            queue_rows.push(json!({
                "confidence": finding.confidence,
                "description": finding.description,
                "file": finding.file,
                "finding_index": finding_index,
                "merge_sha": sha,
                "severity": finding.severity,
                "symbol": finding.symbol,
            }));
        }
    }
    write_jsonl(&queue_path, &queue_rows)?;
    Ok(finder_payload(
        &pinned_tip,
        &summary.manifest_path,
        accepted.len(),
        &queue_path,
        queue_rows.len(),
    ))
}

pub fn sweep_ingest_refuter(run_dir: &Path) -> Result<Vec<(String, String)>, String> {
    let (pinned_tip, _selected_shas, summary) = load_selected_manifest(run_dir)?;
    let queue_path = run_dir.join(SWEEP_REFUTER_QUEUE_NAME);
    let refuter_raw_path = run_dir.join(SWEEP_REFUTER_RAW_NAME);
    if !queue_path.is_file() {
        return Err(format!("refuter queue missing: {}", queue_path.display()));
    }
    let queue_raw = read_strict_jsonl(&queue_path, "refuter queue")?;
    let mut queue_order = Vec::new();
    let mut queue_by_key = BTreeMap::new();
    for (index, raw) in queue_raw.iter().enumerate() {
        let lineno = index + 1;
        let parsed = parse_queue_row(raw)
            .map_err(|error| format!("refuter queue line {lineno}: {error}"))?;
        let key = (parsed.merge_sha.clone(), parsed.finding_index);
        if queue_by_key.contains_key(&key) {
            return Err(format!("refuter queue line {lineno}: duplicate queue key"));
        }
        queue_order.push(key.clone());
        queue_by_key.insert(key, parsed);
    }
    let expected_keys = queue_by_key.keys().cloned().collect::<BTreeSet<_>>();
    let validated_path = run_dir.join(SWEEP_VALIDATED_NAME);
    if expected_keys.is_empty() {
        write_validated(&validated_path, &pinned_tip, &summary, &[])?;
        return Ok(refuter_payload(
            &pinned_tip,
            &summary.manifest_path,
            &validated_path,
            0,
            None,
            0,
        ));
    }
    if !refuter_raw_path.is_file() {
        return Err(format!(
            "refuter raw capture missing: {}",
            refuter_raw_path.display()
        ));
    }
    let result_rows = read_strict_jsonl(&refuter_raw_path, "refuter raw")?;
    if result_rows.is_empty() {
        return Err(format!(
            "refuter raw capture is empty: {}",
            refuter_raw_path.display()
        ));
    }
    let mut verdict_by_key = BTreeMap::new();
    let mut seen = BTreeSet::new();
    for (index, raw) in result_rows.iter().enumerate() {
        let lineno = index + 1;
        let parsed = parse_refuter_result(raw)
            .map_err(|error| format!("refuter raw line {lineno}: {error}"))?;
        let key = (parsed.0.clone(), parsed.1);
        if !seen.insert(key.clone()) {
            return Err(format!(
                "refuter raw line {lineno}: duplicate verdict for key"
            ));
        }
        if !expected_keys.contains(&key) {
            return Err(format!("refuter raw line {lineno}: foreign verdict key"));
        }
        verdict_by_key.insert(key, parsed.2);
    }
    let missing = expected_keys.len().saturating_sub(seen.len());
    if missing > 0 {
        return Err(format!("refuter raw missing {missing} queued verdict(s)"));
    }
    let mut candidates = Vec::new();
    for key in &queue_order {
        if verdict_by_key[key] != "survives" {
            continue;
        }
        let row = &queue_by_key[key];
        candidates.push(json!({
            "confidence": row.confidence,
            "description": row.description,
            "file": row.file,
            "merge_sha": row.merge_sha,
            "severity": row.severity,
            "symbol": row.symbol,
        }));
    }
    let candidate_count = candidates.len();
    let refuted = expected_keys.len() - candidate_count;
    write_validated(&validated_path, &pinned_tip, &summary, &candidates)?;
    Ok(refuter_payload(
        &pinned_tip,
        &summary.manifest_path,
        &validated_path,
        candidate_count,
        Some(refuted),
        expected_keys.len(),
    ))
}

struct SelectedSummary {
    manifest_path: String,
    selected_count: usize,
    skipped_count: usize,
    pending_shas: Vec<String>,
    coverage_incomplete: bool,
}

struct QueueRow {
    merge_sha: String,
    finding_index: u64,
    file: String,
    symbol: String,
    description: String,
    severity: String,
    confidence: String,
}

#[derive(Clone, Debug)]
struct SweepState {
    last_sweep_sha: String,
    #[allow(dead_code)] // Validated on load so a later watermark consumer can trust it.
    last_sweep_at: String,
    pending_shas: Vec<String>,
}

fn load_selected_manifest(
    run_dir: &Path,
) -> Result<(String, Vec<String>, SelectedSummary), String> {
    let manifest_path = run_dir.join(SWEEP_SELECTED_MANIFEST_NAME);
    if !manifest_path.is_file() {
        return Err(format!(
            "selected-merge manifest missing: {}",
            manifest_path.display()
        ));
    }
    let manifest = load_json_object(&manifest_path)?;
    let pinned_tip = require_full_sha(
        manifest
            .get("pinned_tip")
            .and_then(Value::as_str)
            .unwrap_or_default(),
        "selected manifest pinned_tip",
    )?;
    let selected_raw = manifest
        .get("selected")
        .and_then(Value::as_array)
        .ok_or_else(|| {
            format!(
                "selected manifest lacks selected array: {}",
                manifest_path.display()
            )
        })?;
    let mut selected_shas = Vec::new();
    for item in selected_raw {
        let object = item.as_object().ok_or_else(|| {
            format!(
                "selected manifest entry is not an object: {}",
                manifest_path.display()
            )
        })?;
        selected_shas.push(require_full_sha(
            object
                .get("merge_sha")
                .and_then(Value::as_str)
                .unwrap_or_default(),
            "selected merge_sha",
        )?);
    }
    let pending = manifest
        .get("pending_shas")
        .and_then(Value::as_array)
        .map(|items| {
            items
                .iter()
                .map(|item| {
                    require_full_sha(item.as_str().unwrap_or_default(), "pending_shas entry")
                })
                .collect::<Result<Vec<_>, _>>()
        })
        .transpose()?
        .unwrap_or_default();
    let skipped = manifest
        .get("skipped_count")
        .and_then(Value::as_u64)
        .and_then(|value| usize::try_from(value).ok())
        .unwrap_or(0);
    let selected_count = selected_shas.len();
    Ok((
        pinned_tip,
        selected_shas,
        SelectedSummary {
            manifest_path: manifest_path.display().to_string(),
            selected_count,
            skipped_count: skipped,
            pending_shas: pending,
            coverage_incomplete: manifest
                .get("coverage_incomplete")
                .and_then(Value::as_bool)
                .unwrap_or(false),
        },
    ))
}

fn parse_finder_row(raw: &Map<String, Value>) -> Result<(String, Vec<SweepFinding>), String> {
    if !exact_keys(raw, &["findings", "merge_sha"]) {
        return Err("finder row has unexpected or missing fields".to_owned());
    }
    let merge_sha = require_full_sha(
        raw.get("merge_sha")
            .and_then(Value::as_str)
            .unwrap_or_default(),
        "finder merge_sha",
    )
    .map_err(|_| "finder merge_sha must be a full 40-character SHA".to_owned())?;
    let findings_raw = raw
        .get("findings")
        .and_then(Value::as_array)
        .ok_or_else(|| "finder findings must be a list".to_owned())?;
    if findings_raw.len() > SWEEP_FINDINGS_PER_MERGE_CAP {
        return Err(format!(
            "finder findings exceed per-merge cap {SWEEP_FINDINGS_PER_MERGE_CAP}"
        ));
    }
    let mut findings = Vec::new();
    for item in findings_raw {
        let object = item
            .as_object()
            .ok_or_else(|| "finder finding must be an object".to_owned())?;
        findings.push(parse_finder_finding(object)?);
    }
    Ok((merge_sha, findings))
}

fn parse_finder_finding(raw: &Map<String, Value>) -> Result<SweepFinding, String> {
    if !exact_keys(
        raw,
        &["confidence", "description", "file", "severity", "symbol"],
    ) {
        return Err("finder finding has unexpected or missing fields".to_owned());
    }
    let file = raw
        .get("file")
        .and_then(Value::as_str)
        .ok_or_else(|| "finder finding file must be a repository-relative path".to_owned())?;
    if !valid_repo_relative_path(file) {
        return Err("finder finding file must be a repository-relative path".to_owned());
    }
    let symbol = raw
        .get("symbol")
        .and_then(Value::as_str)
        .ok_or_else(|| "finder finding symbol must be a bounded string".to_owned())?;
    if symbol.len() > SWEEP_FINDING_SYMBOL_CAP || symbol.contains('\0') {
        return Err("finder finding symbol must be a bounded string".to_owned());
    }
    let description = raw
        .get("description")
        .and_then(Value::as_str)
        .ok_or_else(|| "finder finding description must be a bounded string".to_owned())?;
    if description.len() > SWEEP_FINDING_DESC_CAP || description.contains('\0') {
        return Err("finder finding description must be a bounded string".to_owned());
    }
    let severity = raw
        .get("severity")
        .and_then(Value::as_str)
        .ok_or_else(|| "finder finding severity is unknown".to_owned())?;
    if !matches!(severity, "high" | "medium" | "low") {
        return Err("finder finding severity is unknown".to_owned());
    }
    let confidence = raw
        .get("confidence")
        .and_then(Value::as_str)
        .ok_or_else(|| "finder finding confidence is unknown".to_owned())?;
    if !matches!(confidence, "high" | "medium" | "low") {
        return Err("finder finding confidence is unknown".to_owned());
    }
    Ok(SweepFinding {
        file: file.to_owned(),
        symbol: normalize_agent_text(symbol),
        description: normalize_agent_text(description),
        severity: severity.to_owned(),
        confidence: confidence.to_owned(),
    })
}

fn parse_queue_row(raw: &Map<String, Value>) -> Result<QueueRow, String> {
    if !exact_keys(
        raw,
        &[
            "confidence",
            "description",
            "file",
            "finding_index",
            "merge_sha",
            "severity",
            "symbol",
        ],
    ) {
        return Err("refuter queue row has unexpected or missing fields".to_owned());
    }
    let merge_sha = require_full_sha(
        raw.get("merge_sha")
            .and_then(Value::as_str)
            .unwrap_or_default(),
        "queue merge_sha",
    )
    .map_err(|_| "queue merge_sha must be a full 40-character SHA".to_owned())?;
    let finding_index = raw
        .get("finding_index")
        .and_then(Value::as_u64)
        .ok_or_else(|| "queue finding_index must be a non-negative integer".to_owned())?;
    if raw.get("finding_index").and_then(Value::as_bool).is_some() {
        return Err("queue finding_index must be a non-negative integer".to_owned());
    }
    Ok(QueueRow {
        merge_sha,
        finding_index,
        file: string_field(raw, "file"),
        symbol: string_field(raw, "symbol"),
        description: string_field(raw, "description"),
        severity: string_field(raw, "severity"),
        confidence: string_field(raw, "confidence"),
    })
}

fn parse_refuter_result(raw: &Map<String, Value>) -> Result<(String, u64, String), String> {
    if !exact_keys(raw, &["finding_index", "merge_sha", "verdict"]) {
        return Err("refuter row has unexpected or missing fields".to_owned());
    }
    let merge_sha = require_full_sha(
        raw.get("merge_sha")
            .and_then(Value::as_str)
            .unwrap_or_default(),
        "refuter merge_sha",
    )
    .map_err(|_| "refuter merge_sha must be a full 40-character SHA".to_owned())?;
    if raw.get("finding_index").and_then(Value::as_bool).is_some() {
        return Err("refuter finding_index must be a non-negative integer".to_owned());
    }
    let finding_index = raw
        .get("finding_index")
        .and_then(Value::as_u64)
        .ok_or_else(|| "refuter finding_index must be a non-negative integer".to_owned())?;
    let verdict = raw
        .get("verdict")
        .and_then(Value::as_str)
        .ok_or_else(|| "refuter verdict is unknown".to_owned())?;
    if !matches!(verdict, "survives" | "refuted") {
        return Err("refuter verdict is unknown".to_owned());
    }
    Ok((merge_sha, finding_index, verdict.to_owned()))
}

fn load_sweep_state(path: &Path) -> Result<Option<SweepState>, String> {
    if !path.exists() {
        return Ok(None);
    }
    let raw = load_json_object(path)
        .map_err(|error| format!("malformed sweep state: {}: {error}", path.display()))?;
    if !exact_keys(
        &raw,
        &[
            "last_sweep_at",
            "last_sweep_sha",
            "pending_shas",
            "schema_version",
        ],
    ) {
        return Err(format!("malformed sweep state keys: {}", path.display()));
    }
    let schema_version = raw
        .get("schema_version")
        .and_then(Value::as_u64)
        .ok_or_else(|| format!("malformed sweep state schema_version: {}", path.display()))?;
    if schema_version != SWEEP_SCHEMA_VERSION {
        return Err(format!(
            "unsupported sweep state schema_version={schema_version}: {}",
            path.display()
        ));
    }
    let pending_raw = raw
        .get("pending_shas")
        .and_then(Value::as_array)
        .ok_or_else(|| format!("malformed sweep state pending_shas: {}", path.display()))?;
    let mut pending = Vec::new();
    let mut seen = BTreeSet::new();
    for item in pending_raw {
        let sha = require_full_sha(item.as_str().unwrap_or_default(), "pending_shas entry")?;
        if !seen.insert(sha.clone()) {
            return Err(format!("duplicate pending SHA in sweep state: {sha}"));
        }
        pending.push(sha);
    }
    let last_sweep_at = raw
        .get("last_sweep_at")
        .and_then(Value::as_str)
        .ok_or_else(|| "last_sweep_at must be an ISO-8601 UTC timestamp ending in Z".to_owned())?;
    if !sweep_timestamp(last_sweep_at) {
        return Err("last_sweep_at must be an ISO-8601 UTC timestamp ending in Z".to_owned());
    }
    Ok(Some(SweepState {
        last_sweep_sha: require_full_sha(
            raw.get("last_sweep_sha")
                .and_then(Value::as_str)
                .unwrap_or_default(),
            "last_sweep_sha",
        )?,
        last_sweep_at: last_sweep_at.to_owned(),
        pending_shas: pending,
    }))
}

fn enumerate_first_parent_merges(
    repository: &GixRepository,
    tip: &ObjectId,
    state: Option<&SweepState>,
    now: u64,
) -> Result<Vec<(String, String, i64)>, String> {
    let mut rows = Vec::new();
    let mut current = tip.clone();
    let watermark = state
        .map(|state| object_id(&state.last_sweep_sha))
        .transpose()?;
    let since = state
        .is_none()
        .then(|| i64::try_from(now.saturating_sub(SWEEP_INITIAL_WINDOW_SECONDS)).unwrap_or(0));
    for _ in 0..MAX_WALK {
        if watermark.as_ref() == Some(&current) {
            break;
        }
        let commit = repository
            .walk_commits(&current, 1)
            .map_err(|_| "first-parent sweep enumeration failed".to_owned())?
            .into_iter()
            .next()
            .ok_or_else(|| "first-parent sweep enumeration failed".to_owned())?;
        let commit_time = committer_time(repository, &commit.id)?;
        if let Some(since) = since
            && commit_time < since
        {
            break;
        }
        if commit.parents.len() >= 2 {
            let subject = String::from_utf8_lossy(&commit.subject).into_owned();
            rows.push((commit.id.to_hex(), subject, commit_time));
        }
        let Some(parent) = commit.parents.first() else {
            break;
        };
        current = parent.clone();
    }
    rows.reverse();
    Ok(rows)
}

fn build_commit(
    repository: &GixRepository,
    merge_sha: &str,
    subject: &str,
    _commit_time: i64,
    history_order: usize,
    diff_cap: usize,
) -> Result<Option<SweepCommit>, String> {
    let merge_id = object_id(merge_sha)?;
    let commit = repository
        .walk_commits(&merge_id, 1)
        .map_err(|_| format!("first-parent base for {merge_sha} failed"))?
        .into_iter()
        .next()
        .ok_or_else(|| format!("first-parent base for {merge_sha} failed"))?;
    let Some(base_id) = commit.parents.first() else {
        return Ok(None);
    };
    let base_sha = require_full_sha(
        &base_id.to_hex(),
        &format!("first-parent base for {merge_sha}"),
    )?;
    let changes = repository
        .tree_changes(
            &repository
                .walk_commits(base_id, 1)
                .map_err(|_| format!("touched paths for {merge_sha} failed"))?
                .into_iter()
                .next()
                .ok_or_else(|| format!("touched paths for {merge_sha} failed"))?
                .tree,
            &commit.tree,
        )
        .map_err(|_| format!("touched paths for {merge_sha} failed"))?;
    let mut touched = Vec::new();
    let mut full_diff = String::new();
    for change in changes.entries() {
        let path = repository_path_text(&change.path)?;
        if !matches!(
            change.kind,
            ChangeKind::Added | ChangeKind::Deleted | ChangeKind::Modified | ChangeKind::Renamed
        ) {
            continue;
        }
        touched.push(path.clone());
        let before = change
            .old_id
            .as_ref()
            .and_then(|id| repository.object(id).ok().flatten())
            .map(|object| object.data)
            .unwrap_or_default();
        let after = change
            .new_id
            .as_ref()
            .and_then(|id| repository.object(id).ok().flatten())
            .map(|object| object.data)
            .unwrap_or_default();
        let header = format!("diff --git a/{path} b/{path}\n--- a/{path}\n+++ b/{path}\n");
        full_diff.push_str(&header);
        match unified_blob_diff(&before, &after) {
            Ok(unified) => full_diff.push_str(&unified),
            Err(_) => full_diff.push_str("Binary files differ\n"),
        }
    }
    let diff_size = full_diff.len();
    let truncated = diff_size > diff_cap;
    let capped = if truncated {
        format!(
            "{}{}",
            &full_diff[..diff_cap],
            format_args!("\n\n[content truncated to {diff_cap} characters]\n")
        )
    } else {
        full_diff.clone()
    };
    let (symbols, symbols_truncated) = extract_changed_symbols(&full_diff);
    Ok(Some(SweepCommit {
        merge_sha: merge_sha.to_owned(),
        base_sha,
        subject: subject.to_owned(),
        touched_paths: touched,
        diff_size,
        capped_diff: capped,
        diff_truncated: truncated,
        changed_symbols: symbols,
        symbols_truncated,
        is_chronic: false,
        history_order,
    }))
}

fn write_bundles(
    repository: &GixRepository,
    run_dir: &Path,
    pinned_tip: &str,
    selected: &[SweepCommit],
) -> Result<Vec<PathBuf>, String> {
    let mut paths = Vec::new();
    for commit in selected {
        let (consumers, consumers_truncated) = discover_consumers(
            repository,
            pinned_tip,
            &commit.changed_symbols,
            &commit.touched_paths,
        )?;
        let mut notices = Vec::new();
        if commit.diff_truncated {
            notices.push(format!("diff truncated to {SWEEP_DIFF_CAP} characters"));
        }
        if commit.symbols_truncated {
            notices.push(format!("changed symbols truncated to {SWEEP_SYMBOL_CAP}"));
        }
        if consumers_truncated {
            notices.push(format!("consumers truncated to {SWEEP_CONSUMER_CAP}"));
        }
        let path = run_dir.join(format!("sweep-{}-bundle.md", commit.merge_sha));
        private_write(
            &path,
            &render_bundle(pinned_tip, commit, &notices, &consumers),
        )?;
        paths.push(path);
    }
    Ok(paths)
}

fn discover_consumers(
    repository: &GixRepository,
    tip_hex: &str,
    symbols: &[String],
    defining_paths: &[String],
) -> Result<(Vec<ConsumerHit>, bool), String> {
    if symbols.is_empty() {
        return Ok((Vec::new(), false));
    }
    let tip = object_id(tip_hex)?;
    let files = repository
        .files_at_commit(&tip, MAX_CONSUMER_FILES)
        .map_err(|_| "consumer scan failed".to_owned())?;
    let defining = defining_paths.iter().cloned().collect::<BTreeSet<_>>();
    let mut hits = Vec::new();
    for path in files {
        let path_text = repository_path_text(&path)?;
        if defining.contains(&path_text) || excluded_consumer_path(&path_text) {
            continue;
        }
        let Some(blob) = repository.blob_at_commit(&tip, &path).map_err(|_| {
            format!(
                "consumer scan for {} failed",
                symbols.first().unwrap_or(&String::new())
            )
        })?
        else {
            continue;
        };
        let text = String::from_utf8_lossy(&blob);
        for (index, line) in text.lines().enumerate() {
            if symbols.iter().any(|symbol| line.contains(symbol.as_str())) {
                if hits.len() >= SWEEP_CONSUMER_CAP {
                    return Ok((hits, true));
                }
                hits.push(ConsumerHit {
                    path: path_text.clone(),
                    line: index + 1,
                    text: line.trim().to_owned(),
                });
            }
        }
    }
    Ok((hits, false))
}

fn render_bundle(
    pinned_tip: &str,
    commit: &SweepCommit,
    notices: &[String],
    consumers: &[ConsumerHit],
) -> String {
    let notices = if notices.is_empty() {
        "- none".to_owned()
    } else {
        notices
            .iter()
            .map(|item| format!("- {item}"))
            .collect::<Vec<_>>()
            .join("\n")
    };
    let consumers = if consumers.is_empty() {
        "- none".to_owned()
    } else {
        consumers
            .iter()
            .map(|hit| format!("- {}:{}: {}", hit.path, hit.line, hit.text))
            .collect::<Vec<_>>()
            .join("\n")
    };
    let symbols = if commit.changed_symbols.is_empty() {
        "none".to_owned()
    } else {
        commit.changed_symbols.join(", ")
    };
    let touched = if commit.touched_paths.is_empty() {
        "- none".to_owned()
    } else {
        commit
            .touched_paths
            .iter()
            .map(|path| format!("- {path}"))
            .collect::<Vec<_>>()
            .join("\n")
    };
    format!(
        "# Sweep evidence bundle\n\n\
pinned_tip: {pinned_tip}\n\
merge_sha: {}\n\
base_sha: {}\n\
subject: {}\n\
chronic_tags: none\n\
changed_symbols: {symbols}\n\n\
## Touched files\n\
{touched}\n\n\
## Truncation notices\n\
{notices}\n\n\
## Consumers\n\
{consumers}\n\n\
## First-parent diff\n\
```diff\n\
{}\n\
```\n",
        commit.merge_sha,
        commit.base_sha,
        commit.subject,
        commit.capped_diff.trim_end_matches('\n')
    )
}

fn extract_changed_symbols(diff_text: &str) -> (Vec<String>, bool) {
    let mut symbols = Vec::new();
    let mut seen = BTreeSet::new();
    let mut truncated = false;
    for line in diff_text.lines() {
        if !line.starts_with('+') || line.starts_with("+++") {
            continue;
        }
        let found = PY_DEF
            .captures(line)
            .or_else(|| PY_CLASS.captures(line))
            .or_else(|| PY_CONST.captures(line));
        let Some(found) = found else {
            continue;
        };
        let name = found
            .get(1)
            .map(|value| value.as_str().to_owned())
            .unwrap_or_default();
        if !seen.insert(name.clone()) {
            continue;
        }
        if symbols.len() >= SWEEP_SYMBOL_CAP {
            truncated = true;
            break;
        }
        symbols.push(name);
    }
    (symbols, truncated)
}

fn write_validated(
    path: &Path,
    pinned_tip: &str,
    summary: &SelectedSummary,
    candidates: &[Value],
) -> Result<(), String> {
    write_sorted_json(
        path,
        &json!({
            "candidates": candidates,
            "coverage_incomplete": summary.coverage_incomplete,
            "pending_shas": summary.pending_shas,
            "pinned_tip": pinned_tip,
            "selected_count": summary.selected_count,
            "selected_manifest_path": summary.manifest_path,
            "skipped_count": summary.skipped_count,
        }),
    )
}

fn finder_payload(
    pinned_tip: &str,
    manifest: &str,
    accepted: usize,
    queue_path: &Path,
    queue_count: usize,
) -> Vec<(String, String)> {
    vec![
        ("PINNED_TIP".to_owned(), pinned_tip.to_owned()),
        ("SELECTED_MERGE_MANIFEST".to_owned(), manifest.to_owned()),
        ("INGEST_ACCEPTED".to_owned(), accepted.to_string()),
        (
            "REFUTER_QUEUE_PATH".to_owned(),
            queue_path.display().to_string(),
        ),
        ("REFUTER_QUEUE_COUNT".to_owned(), queue_count.to_string()),
    ]
}

fn refuter_payload(
    pinned_tip: &str,
    manifest: &str,
    validated_path: &Path,
    candidate_count: usize,
    refuted: Option<usize>,
    queue_count: usize,
) -> Vec<(String, String)> {
    let mut rows = vec![
        ("PINNED_TIP".to_owned(), pinned_tip.to_owned()),
        ("SELECTED_MERGE_MANIFEST".to_owned(), manifest.to_owned()),
        (
            "SWEEP_VALIDATED_PATH".to_owned(),
            validated_path.display().to_string(),
        ),
        ("CANDIDATE_COUNT".to_owned(), candidate_count.to_string()),
    ];
    if let Some(refuted) = refuted {
        rows.push(("REFUTED_COUNT".to_owned(), refuted.to_string()));
    }
    rows.push(("REFUTER_QUEUE_COUNT".to_owned(), queue_count.to_string()));
    rows
}

fn require_reachable(
    repository: &GixRepository,
    sha: &str,
    tip: &ObjectId,
    label: &str,
) -> Result<(), String> {
    let ancestor = object_id(sha)?;
    if !repository.is_ancestor(&ancestor, tip).map_err(|_| {
        format!(
            "{label} {sha} is not reachable from pinned tip {}",
            tip.to_hex()
        )
    })? {
        return Err(format!(
            "{label} {sha} is not reachable from pinned tip {}",
            tip.to_hex()
        ));
    }
    Ok(())
}

fn subject_and_time(repository: &GixRepository, sha: &str) -> Result<(String, i64), String> {
    let id = object_id(sha)?;
    let commit = repository
        .walk_commits(&id, 1)
        .map_err(|_| format!("commit metadata for {sha} failed"))?
        .into_iter()
        .next()
        .ok_or_else(|| format!("commit metadata for {sha} failed"))?;
    Ok((
        String::from_utf8_lossy(&commit.subject).into_owned(),
        committer_time(repository, &commit.id)?,
    ))
}

fn committer_time(repository: &GixRepository, id: &ObjectId) -> Result<i64, String> {
    let object = repository
        .object(id)
        .map_err(|_| "malformed commit timestamp".to_owned())?
        .ok_or_else(|| "malformed commit timestamp".to_owned())?;
    let text = String::from_utf8_lossy(&object.data);
    for line in text.lines() {
        let Some(rest) = line.strip_prefix("committer ") else {
            continue;
        };
        let Some(stamp) = rest.rsplit(' ').nth(1) else {
            continue;
        };
        return stamp
            .parse()
            .map_err(|_| "malformed commit timestamp".to_owned());
    }
    Err("malformed commit timestamp".to_owned())
}

fn object_id(sha: &str) -> Result<ObjectId, String> {
    let bytes = (0..sha.len())
        .step_by(2)
        .map(|index| u8::from_str_radix(&sha[index..index + 2], 16))
        .collect::<Result<Vec<_>, _>>()
        .map_err(|_| format!("{sha} must be a full 40-character lowercase SHA"))?;
    ObjectId::new(larch_core::ObjectHash::Sha1, bytes)
        .map_err(|_| format!("{sha} must be a full 40-character lowercase SHA"))
}

pub fn require_full_sha(value: &str, label: &str) -> Result<String, String> {
    if !full_sha(value) {
        return Err(format!("{label} must be a full 40-character lowercase SHA"));
    }
    Ok(value.to_owned())
}

pub fn sweep_timestamp(value: &str) -> bool {
    value.len() == 20
        && value.as_bytes().get(10) == Some(&b'T')
        && value.ends_with('Z')
        && value
            .as_bytes()
            .iter()
            .enumerate()
            .all(|(index, byte)| match index {
                4 | 7 => *byte == b'-',
                10 => *byte == b'T',
                13 | 16 => *byte == b':',
                19 => *byte == b'Z',
                _ => byte.is_ascii_digit(),
            })
}

fn excluded_subject(subject: &str) -> bool {
    subject.starts_with("chore(larch-logs)") || subject.starts_with("Release v")
}

fn larch_logs_only(paths: &[String]) -> bool {
    !paths.is_empty()
        && paths
            .iter()
            .all(|path| path == "larch-logs" || path.starts_with("larch-logs/"))
}

fn excluded_consumer_path(path: &str) -> bool {
    path == "larch-logs" || path.starts_with("larch-logs/")
}

fn valid_repo_relative_path(value: &str) -> bool {
    if value.is_empty() || value.len() > SWEEP_FINDING_FILE_CAP {
        return false;
    }
    if value.starts_with(['/', '~']) || value.contains('\0') || value.contains('\\') {
        return false;
    }
    let parts = value
        .split('/')
        .filter(|part| !part.is_empty())
        .collect::<Vec<_>>();
    if parts.is_empty() {
        return false;
    }
    parts
        .iter()
        .all(|part| *part != "." && *part != ".." && part.chars().all(|character| character >= ' '))
}

fn normalize_agent_text(value: &str) -> String {
    value
        .chars()
        .filter(|character| *character == '\t' || *character == '\n' || *character >= ' ')
        .collect::<String>()
        .trim()
        .to_owned()
}

fn string_field(object: &Map<String, Value>, field: &str) -> String {
    object
        .get(field)
        .and_then(Value::as_str)
        .unwrap_or_default()
        .to_owned()
}

fn read_strict_jsonl(path: &Path, desc: &str) -> Result<Vec<Map<String, Value>>, String> {
    let text =
        String::from_utf8_lossy(&fs::read(path).map_err(|error| format!("{desc}: {error}"))?)
            .into_owned();
    let mut rows = Vec::new();
    for (index, line) in text.lines().enumerate() {
        if line.trim().is_empty() {
            continue;
        }
        let value: Value = serde_json::from_str(line)
            .map_err(|error| format!("{desc} line {}: not JSON: {error}", index + 1))?;
        let object = value
            .as_object()
            .cloned()
            .ok_or_else(|| format!("{desc} line {}: row is not an object", index + 1))?;
        rows.push(object);
    }
    Ok(rows)
}

fn load_json_object(path: &Path) -> Result<Map<String, Value>, String> {
    let metadata = fs::metadata(path).map_err(|error| error.to_string())?;
    if metadata.len() > MAX_JSON_BYTES {
        return Err(format!(
            "input exceeds {MAX_JSON_BYTES} bytes: {}",
            path.display()
        ));
    }
    let value: Value = serde_json::from_slice(&fs::read(path).map_err(|error| error.to_string())?)
        .map_err(|error| error.to_string())?;
    value
        .as_object()
        .cloned()
        .ok_or_else(|| format!("expected JSON object in {}", path.display()))
}

fn write_sorted_json(path: &Path, value: &Value) -> Result<(), String> {
    let mut text =
        serde_json::to_string_pretty(&sort_json(value)).map_err(|error| error.to_string())?;
    text.push('\n');
    private_write(path, &text)
}

fn write_jsonl(path: &Path, rows: &[Value]) -> Result<(), String> {
    let mut text = String::new();
    for row in rows {
        text.push_str(&python_dumps(&sort_json(row))?);
        text.push('\n');
    }
    private_write(path, &text)
}

fn compact_json(value: &Value) -> Result<String, String> {
    serde_json::to_string(&sort_json(value)).map_err(|error| error.to_string())
}

fn python_dumps(value: &Value) -> Result<String, String> {
    match value {
        Value::Null => Ok("null".to_owned()),
        Value::Bool(true) => Ok("true".to_owned()),
        Value::Bool(false) => Ok("false".to_owned()),
        Value::Number(number) => Ok(number.to_string()),
        Value::String(_) => serde_json::to_string(value).map_err(|error| error.to_string()),
        Value::Array(items) if items.is_empty() => Ok("[]".to_owned()),
        Value::Array(items) => {
            let inner = items
                .iter()
                .map(python_dumps)
                .collect::<Result<Vec<_>, _>>()?;
            Ok(format!("[{}]", inner.join(", ")))
        }
        Value::Object(map) if map.is_empty() => Ok("{}".to_owned()),
        Value::Object(map) => {
            let mut keys = map.keys().cloned().collect::<Vec<_>>();
            keys.sort();
            let mut inner = Vec::new();
            for key in keys {
                let encoded_key = serde_json::to_string(&Value::String(key.clone()))
                    .map_err(|error| error.to_string())?;
                inner.push(format!(
                    "{encoded_key}: {}",
                    python_dumps(map.get(&key).expect("sorted object key exists"))?
                ));
            }
            Ok(format!("{{{}}}", inner.join(", ")))
        }
    }
}

fn sort_json(value: &Value) -> Value {
    match value {
        Value::Object(map) => {
            let mut sorted = Map::new();
            let mut keys = map.keys().cloned().collect::<Vec<_>>();
            keys.sort();
            for key in keys {
                if let Some(child) = map.get(&key) {
                    sorted.insert(key, sort_json(child));
                }
            }
            Value::Object(sorted)
        }
        Value::Array(items) => Value::Array(items.iter().map(sort_json).collect()),
        other => other.clone(),
    }
}

fn absolute_path(path: &Path) -> Result<PathBuf, String> {
    if path.is_absolute() {
        Ok(path.to_path_buf())
    } else {
        env::current_dir()
            .map(|current| current.join(path))
            .map_err(|error| format!("could not resolve sweep state path: {error}"))
    }
}

fn unix_now() -> Result<u64, String> {
    Ok(SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_err(|error| error.to_string())?
        .as_secs())
}

pub fn emit_rows(rows: &[(String, String)]) {
    for (key, value) in rows {
        larch_core::emit_kv(key, value);
    }
}

#[cfg(test)]
pub fn kv<'a>(rows: &'a [(String, String)], key: &str) -> Option<&'a str> {
    rows.iter()
        .find(|(name, _)| name == key)
        .map(|(_, value)| value.as_str())
}

#[cfg(test)]
mod tests {
    use super::{
        parse_finder_finding, parse_finder_row, parse_refuter_result, sweep_ingest_finder,
        sweep_ingest_refuter, valid_repo_relative_path,
    };
    use serde_json::{Map, Value, json};
    use std::fs;
    use tempfile::tempdir;

    const SHA_A: &str = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
    const SHA_B: &str = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb";
    const TIP: &str = "cccccccccccccccccccccccccccccccccccccccc";

    fn finding() -> Map<String, Value> {
        json!({
            "confidence": "medium",
            "description": "wrong dict key",
            "file": "python/larch/issue/mod.py",
            "severity": "high",
            "symbol": "helper",
        })
        .as_object()
        .cloned()
        .expect("finding object")
    }

    fn write_selected(run_dir: &std::path::Path, shas: &[&str]) {
        fs::create_dir_all(run_dir).expect("run dir");
        let selected = shas
            .iter()
            .map(|sha| json!({"merge_sha": sha}))
            .collect::<Vec<_>>();
        fs::write(
            run_dir.join(super::SWEEP_SELECTED_MANIFEST_NAME),
            serde_json::to_string_pretty(&json!({
                "coverage_incomplete": false,
                "pending_shas": [],
                "pinned_tip": TIP,
                "selected": selected,
                "selected_count": shas.len(),
                "skipped_count": 0,
            }))
            .expect("manifest"),
        )
        .expect("write manifest");
    }

    #[test]
    fn finder_parser_rejects_foreign_paths_and_unknown_severity() {
        let parsed = parse_finder_finding(&finding()).expect("valid finding");
        assert_eq!(parsed.file, "python/larch/issue/mod.py");
        let mut extra = finding();
        extra.insert("extra".to_owned(), Value::from(1));
        assert!(parse_finder_finding(&extra).is_err());
        let mut blocker = finding();
        blocker.insert("severity".to_owned(), Value::from("blocker"));
        assert!(parse_finder_finding(&blocker).is_err());
        assert!(!valid_repo_relative_path("/abs/x.py"));
        assert!(!valid_repo_relative_path("../escape.py"));
        let row = json!({"findings": [], "merge_sha": SHA_A})
            .as_object()
            .cloned()
            .expect("row");
        assert!(parse_finder_row(&row).is_ok());
        let bad_index = json!({"finding_index": true, "merge_sha": SHA_A, "verdict": "refuted"})
            .as_object()
            .cloned()
            .expect("row");
        assert!(parse_refuter_result(&bad_index).is_err());
    }

    #[test]
    fn ingest_finder_writes_deterministic_queue() {
        let directory = tempdir().expect("tempdir");
        let run_dir = directory.path().join("run");
        write_selected(&run_dir, &[SHA_A]);
        fs::write(
            run_dir.join(super::SWEEP_FINDER_RAW_NAME),
            format!(
                "{}\n",
                json!({"findings":[finding(), {
                    "confidence": "medium",
                    "description": "d2",
                    "file": "python/larch/issue/mod.py",
                    "severity": "high",
                    "symbol": "second",
                }], "merge_sha": SHA_A})
            ),
        )
        .expect("finder raw");
        let payload = sweep_ingest_finder(&run_dir).expect("ingest");
        assert_eq!(super::kv(&payload, "INGEST_ACCEPTED"), Some("1"));
        assert_eq!(super::kv(&payload, "REFUTER_QUEUE_COUNT"), Some("2"));
        let queue =
            fs::read_to_string(run_dir.join(super::SWEEP_REFUTER_QUEUE_NAME)).expect("queue");
        let rows = queue
            .lines()
            .map(|line| serde_json::from_str::<Value>(line).expect("row"))
            .collect::<Vec<_>>();
        assert_eq!(rows[0]["finding_index"], 0);
        assert_eq!(rows[1]["finding_index"], 1);
        assert_eq!(rows[0]["symbol"], "helper");
        assert_eq!(rows[1]["symbol"], "second");
    }

    #[test]
    fn ingest_finder_rejects_foreign_and_duplicate_rows() {
        let directory = tempdir().expect("tempdir");
        let run_dir = directory.path().join("run");
        write_selected(&run_dir, &[SHA_A]);
        fs::write(
            run_dir.join(super::SWEEP_FINDER_RAW_NAME),
            format!("{}\n", json!({"findings":[], "merge_sha": SHA_B})),
        )
        .expect("finder raw");
        let error = sweep_ingest_finder(&run_dir).expect_err("foreign");
        assert!(error.contains("foreign merge_sha"));
    }

    #[test]
    fn ingest_refuter_keeps_survivors() {
        let directory = tempdir().expect("tempdir");
        let run_dir = directory.path().join("run");
        write_selected(&run_dir, &[SHA_A]);
        fs::write(
            run_dir.join(super::SWEEP_FINDER_RAW_NAME),
            format!(
                "{}\n",
                json!({"findings":[finding(), {
                    "confidence": "medium",
                    "description": "d2",
                    "file": "python/larch/issue/mod.py",
                    "severity": "high",
                    "symbol": "second",
                }], "merge_sha": SHA_A})
            ),
        )
        .expect("finder raw");
        sweep_ingest_finder(&run_dir).expect("finder");
        fs::write(
            run_dir.join(super::SWEEP_REFUTER_RAW_NAME),
            format!(
                "{}\n{}\n",
                json!({"finding_index": 0, "merge_sha": SHA_A, "verdict": "survives"}),
                json!({"finding_index": 1, "merge_sha": SHA_A, "verdict": "refuted"})
            ),
        )
        .expect("refuter raw");
        let payload = sweep_ingest_refuter(&run_dir).expect("refuter");
        assert_eq!(super::kv(&payload, "CANDIDATE_COUNT"), Some("1"));
        assert_eq!(super::kv(&payload, "REFUTED_COUNT"), Some("1"));
        let validated: Value = serde_json::from_str(
            &fs::read_to_string(run_dir.join(super::SWEEP_VALIDATED_NAME)).expect("validated"),
        )
        .expect("json");
        assert_eq!(validated["candidates"][0]["symbol"], "helper");
        assert_eq!(validated["pinned_tip"], TIP);
    }

    #[test]
    fn zero_selected_merges_bypass_finder_file() {
        let directory = tempdir().expect("tempdir");
        let run_dir = directory.path().join("run");
        write_selected(&run_dir, &[]);
        let payload = sweep_ingest_finder(&run_dir).expect("empty finder");
        assert_eq!(super::kv(&payload, "INGEST_ACCEPTED"), Some("0"));
        let refuter = sweep_ingest_refuter(&run_dir).expect("empty refuter");
        assert_eq!(super::kv(&refuter, "CANDIDATE_COUNT"), Some("0"));
        assert_eq!(super::kv(&refuter, "REFUTED_COUNT"), None);
    }

    #[test]
    fn sweep_state_round_trip_and_rejects_malformed() {
        let directory = tempdir().expect("tempdir");
        let path = directory.path().join("sweep-state.json");
        assert!(super::load_sweep_state(&path).expect("absent").is_none());
        super::write_sweep_state(
            &path,
            SHA_A,
            "2026-07-13T12:00:00Z",
            &[SHA_B.to_owned(), TIP.to_owned()],
        )
        .expect("write");
        let loaded = super::load_sweep_state(&path)
            .expect("load")
            .expect("state");
        assert_eq!(loaded.last_sweep_sha, SHA_A);
        assert_eq!(loaded.pending_shas, vec![SHA_B.to_owned(), TIP.to_owned()]);

        fs::write(
            &path,
            serde_json::to_string_pretty(&json!({
                "last_sweep_at": "2026-07-13T12:00:00Z",
                "last_sweep_sha": SHA_A,
                "pending_shas": [],
                "schema_version": 99,
            }))
            .expect("json"),
        )
        .expect("write malformed");
        let error = super::load_sweep_state(&path).expect_err("schema");
        assert!(error.contains("unsupported sweep state schema"));
    }
}
