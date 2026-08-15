//! Deterministic token-measurement reports over repository and run-log data.
#![allow(
    clippy::cast_precision_loss,
    reason = "measurement wire formats retain Python floating-point ratios"
)]

use super::{
    RunLogCorpus, RunLogCorpusEvent, RunLogCorpusWarning, RunLogCorpusWarningKind, RunLogSelection,
    TokenCorpusScan, TokenRunRecord, TokenScanEvent, TokenScanWarningKind, VendorTotals, safe_int,
};
use crate::RunLogSlug;
use csv::{ReaderBuilder, StringRecord};
use regex::Regex;
use serde_json::Value;
use std::{
    cmp::Ordering,
    collections::{BTreeMap, BTreeSet, HashMap},
    ffi::OsStr,
    fmt::Write as _,
    fs,
    path::{Path, PathBuf},
};
use tiktoken_rs::cl100k_base_singleton;

use super::run_log_corpus::{RunLogFileIter, is_contained_regular_file, safe_child_directories};
use super::session_transcript::{REDACTED_OPERATOR_REPO, strip_plugin_cache_read_suffix};

const CHECKS_DIGEST_FIELDS: [&str; 9] = [
    "site",
    "attempt",
    "redacted_bytes",
    "digest_bytes",
    "redacted_tokens",
    "digest_tokens",
    "saved_bytes",
    "saved_tokens",
    "digest_truncated",
];
const PANEL_SLOTS: [&str; 5] = [
    "specialist",
    "plan-review",
    "voter",
    "aggregator",
    "implementer",
];

fn has_markdown_extension(path: &str) -> bool {
    Path::new(path).extension() == Some(OsStr::new("md"))
}

fn token_count(text: &str) -> usize {
    cl100k_base_singleton().encode_ordinary(text).len()
}

fn tracked_text_paths(tracked: &[Vec<u8>]) -> Vec<String> {
    tracked
        .iter()
        .map(|path| String::from_utf8_lossy(path).into_owned())
        .collect()
}

fn read_lossy(path: &Path) -> Result<String, String> {
    let bytes =
        fs::read(path).map_err(|error| format!("could not read {}: {error}", path.display()))?;
    Ok(String::from_utf8_lossy(&bytes).into_owned())
}

fn claude_root_imports(repo: &Path) -> BTreeSet<String> {
    let Ok(text) = read_lossy(&repo.join("CLAUDE.md")) else {
        return BTreeSet::new();
    };
    text.lines()
        .filter_map(|line| {
            let line = line.trim();
            let target = line.strip_prefix('@')?.split_whitespace().next()?;
            (has_markdown_extension(target) && !target.starts_with('/')).then(|| target.to_owned())
        })
        .collect()
}

fn markdown_tier(path: &str, imports: &BTreeSet<String>) -> &'static str {
    if path == "CLAUDE.md" {
        "tier-1a-claude-root"
    } else if imports.contains(path) {
        "tier-1a-claude-import"
    } else if path.starts_with("skills/") && path.ends_with("/SKILL.md") {
        "tier-1b-runtime-skill"
    } else if path.starts_with(".claude/skills/") && path.ends_with("/SKILL.md") {
        "tier-1b-dev-skill"
    } else if path.starts_with("skills/shared/") {
        "tier-2-shared-reference"
    } else if path.contains("/references/") {
        "tier-2-skill-reference"
    } else if path.starts_with("scripts/") {
        "tier-2-script-doc"
    } else if path.starts_with("docs/") {
        "tier-3-doc"
    } else if path.starts_with("larch-logs/") {
        "tier-4-run-log"
    } else {
        "tier-3-other"
    }
}

#[derive(Debug)]
struct MarkdownRow {
    path: String,
    tier: &'static str,
    bytes: usize,
    lines: usize,
    h2_count: usize,
}

/// Render tracked Markdown size and `cl100k_base` token counts.
///
/// # Errors
/// Returns an error when a tracked Markdown file cannot be read.
pub fn markdown_cost(repo: &Path, tracked: &[Vec<u8>]) -> Result<String, String> {
    let imports = claude_root_imports(repo);
    let mut rows = Vec::new();
    let mut token_counts = Vec::new();
    for relative in tracked_text_paths(tracked)
        .into_iter()
        .filter(|path| has_markdown_extension(path))
    {
        let path = repo.join(&relative);
        if !path.is_file() {
            continue;
        }
        let bytes = fs::read(&path)
            .map_err(|error| format!("could not read {}: {error}", path.display()))?;
        let text = String::from_utf8_lossy(&bytes);
        let lines =
            text.matches('\n').count() + usize::from(!text.is_empty() && !text.ends_with('\n'));
        let h2_count = text.lines().filter(|line| line.starts_with("## ")).count();
        rows.push(MarkdownRow {
            tier: markdown_tier(&relative, &imports),
            path: relative,
            bytes: bytes.len(),
            lines,
            h2_count,
        });
        token_counts.push(token_count(&text));
    }
    rows.sort_by(|left, right| (left.tier, &left.path).cmp(&(right.tier, &right.path)));
    let mut output = String::from("path\ttier\tbytes\ttokens\tlines\th2_count\n");
    // Keep the historical Python pairing: counts are collected in index order,
    // while rows are sorted by tier before they are zipped.
    for (row, tokens) in rows.iter().zip(token_counts) {
        let _written = writeln!(
            &mut output,
            "{}\t{}\t{}\t{}\t{}\t{}",
            row.path, row.tier, row.bytes, tokens, row.lines, row.h2_count
        );
    }
    Ok(output)
}

fn is_skill_prompt(path: &str) -> bool {
    let parts: Vec<&str> = path.split('/').collect();
    (parts.len() == 3 && parts[0] == "skills" && parts[2] == "SKILL.md")
        || (parts.len() == 4
            && parts[0] == ".claude"
            && parts[1] == "skills"
            && parts[3] == "SKILL.md")
}

fn ngram_sources(repo: &Path, tracked: &[Vec<u8>]) -> Vec<String> {
    let mut sources = Vec::new();
    let mut seen = BTreeSet::new();
    for relative in std::iter::once("CLAUDE.md".to_owned()).chain(claude_root_imports(repo)) {
        if repo.join(&relative).is_file() && seen.insert(relative.clone()) {
            sources.push(relative);
        }
    }
    for relative in tracked_text_paths(tracked) {
        if is_skill_prompt(&relative)
            && repo.join(&relative).is_file()
            && seen.insert(relative.clone())
        {
            sources.push(relative);
        }
    }
    sources
}

/// Render repeated word shingles across root and skill prompts.
///
/// # Errors
/// Returns an error when the tokenizer expression or a selected file cannot be read.
pub fn ngram_duplication(
    repo: &Path,
    tracked: &[Vec<u8>],
    size: usize,
    min_files: usize,
    limit: usize,
) -> Result<String, String> {
    let words = Regex::new(r"[A-Za-z0-9_./$:-]+")
        .map_err(|error| format!("could not compile ngram tokenizer: {error}"))?;
    let mut occurrences: HashMap<String, usize> = HashMap::new();
    let mut files: HashMap<String, BTreeSet<String>> = HashMap::new();
    for relative in ngram_sources(repo, tracked) {
        let text = read_lossy(&repo.join(&relative))?.to_lowercase();
        let tokens: Vec<&str> = words.find_iter(&text).map(|item| item.as_str()).collect();
        if size == 0 {
            for _ in 0..=tokens.len() {
                *occurrences.entry(String::new()).or_default() += 1;
                let _inserted = files
                    .entry(String::new())
                    .or_default()
                    .insert(relative.clone());
            }
        } else {
            for window in tokens.windows(size) {
                let shingle = window.join(" ");
                *occurrences.entry(shingle.clone()).or_default() += 1;
                let _inserted = files.entry(shingle).or_default().insert(relative.clone());
            }
        }
    }
    let mut ranked: Vec<(usize, usize, usize, String)> = occurrences
        .into_iter()
        .filter_map(|(shingle, count)| {
            let file_count = files.get(&shingle).map_or(0, BTreeSet::len);
            (file_count >= min_files).then_some((count * size, count, file_count, shingle))
        })
        .collect();
    ranked.sort_by(|left, right| {
        right
            .0
            .cmp(&left.0)
            .then_with(|| right.1.cmp(&left.1))
            .then_with(|| left.3.cmp(&right.3))
    });
    let mut output = String::from("score\toccurrences\tfiles\tshingle\n");
    for (score, count, file_count, shingle) in ranked.into_iter().take(limit) {
        let _written = writeln!(&mut output, "{score}\t{count}\t{file_count}\t{shingle}");
    }
    Ok(output)
}

#[derive(Clone, Debug)]
struct MeasurementRun {
    path: PathBuf,
    run_id: String,
    issue: Option<u64>,
}

fn transcript_path(run: &MeasurementRun) -> Option<PathBuf> {
    let path = run.path.join("session-transcript.jsonl");
    is_contained_regular_file(&run.path, &path).then_some(path)
}

fn skill_runs(corpus_root: &Path) -> BTreeMap<String, Vec<MeasurementRun>> {
    let mut grouped: BTreeMap<String, Vec<MeasurementRun>> = BTreeMap::new();
    for event in RunLogCorpus::new(corpus_root).select(RunLogSelection::all()) {
        let RunLogCorpusEvent::Run(run) = event else {
            continue;
        };
        grouped
            .entry(run.layout().skill().as_str().to_owned())
            .or_default()
            .push(MeasurementRun {
                path: run.directory().to_owned(),
                run_id: run.layout().run_id().as_str().to_owned(),
                issue: Some(run.manifest().issue_number()),
            });
    }
    let review_root = corpus_root.join("review");
    let seen: BTreeSet<PathBuf> = grouped
        .get("review")
        .into_iter()
        .flatten()
        .filter_map(|run| fs::canonicalize(&run.path).ok())
        .collect();
    for path in safe_child_directories(&review_root).directories {
        let Ok(resolved) = fs::canonicalize(&path) else {
            continue;
        };
        let run = MeasurementRun {
            run_id: path
                .file_name()
                .map_or_else(String::new, |name| name.to_string_lossy().into_owned()),
            path,
            issue: None,
        };
        if !seen.contains(&resolved) && transcript_path(&run).is_some() {
            grouped.entry("review".to_owned()).or_default().push(run);
        }
    }
    for runs in grouped.values_mut() {
        runs.sort_by(|left, right| left.run_id.cmp(&right.run_id));
    }
    grouped.retain(|_, runs| !runs.is_empty());
    grouped
}

fn normalize_read_path(raw: &Value, repo: &Path) -> Option<String> {
    let mut path = raw.as_str()?.to_owned();
    if !has_markdown_extension(&path) {
        return None;
    }
    let redacted_prefix = format!("{REDACTED_OPERATOR_REPO}/");
    if path.starts_with(&redacted_prefix) {
        path.replace_range(..redacted_prefix.len(), "");
    } else if path == REDACTED_OPERATOR_REPO || path.starts_with('<') {
        return None;
    }
    let prefix = format!("{}/", repo.display());
    if path.starts_with(&prefix) {
        path.replace_range(..prefix.len(), "");
    } else if let Some(relative) = strip_plugin_cache_read_suffix(&path) {
        path = relative;
    } else if path.starts_with('/') {
        return None;
    }
    if path.starts_with("../") || path == ".." || path.contains("/../") {
        return None;
    }
    let parts: Vec<&str> = path.split('/').collect();
    let in_scope = (parts.len() == 3 && parts[0] == "skills" && parts[1] == "shared")
        || (parts.len() == 4 && parts[0] == "skills" && parts[2] == "references");
    (in_scope && has_markdown_extension(&path)).then_some(path)
}

fn read_paths_from_blocks(value: Option<&Value>, types: &[&str], output: &mut Vec<Value>) {
    let Some(blocks) = value.and_then(Value::as_array) else {
        return;
    };
    for block in blocks {
        let Some(fields) = block.as_object() else {
            continue;
        };
        if fields
            .get("type")
            .and_then(Value::as_str)
            .is_some_and(|kind| types.contains(&kind))
            && fields.get("name").and_then(Value::as_str) == Some("Read")
            && let Some(path) = fields
                .get("input")
                .and_then(Value::as_object)
                .and_then(|input| input.get("file_path"))
        {
            output.push(path.clone());
        }
    }
}

fn reference_reads(repo: &Path, run: &MeasurementRun) -> Vec<String> {
    let Some(transcript) = transcript_path(run) else {
        return Vec::new();
    };
    let Ok(bytes) = fs::read(transcript) else {
        return Vec::new();
    };
    let mut reads = Vec::new();
    for line in bytes.split(|byte| *byte == b'\n') {
        let Ok(value) = serde_json::from_slice::<Value>(line) else {
            continue;
        };
        let Some(fields) = value.as_object() else {
            continue;
        };
        let mut paths = Vec::new();
        read_paths_from_blocks(fields.get("blocks"), &["tool_call", "tool_use"], &mut paths);
        read_paths_from_blocks(
            fields
                .get("message")
                .and_then(Value::as_object)
                .and_then(|message| message.get("content")),
            &["tool_use"],
            &mut paths,
        );
        reads.extend(
            paths
                .iter()
                .filter_map(|path| normalize_read_path(path, repo)),
        );
    }
    reads
}

fn repo_token_info(
    repo: &Path,
    paths: impl IntoIterator<Item = String>,
) -> BTreeMap<String, (usize, usize)> {
    let unique: BTreeSet<String> = paths.into_iter().collect();
    unique
        .into_iter()
        .map(|relative| {
            let path = repo.join(&relative);
            let counts = fs::symlink_metadata(&path)
                .ok()
                .filter(|metadata| metadata.is_file() && !metadata.file_type().is_symlink())
                .and_then(|_| fs::read(path).ok())
                .map_or((0, 0), |bytes| {
                    let text = String::from_utf8_lossy(&bytes);
                    (bytes.len(), token_count(&text))
                });
            (relative, counts)
        })
        .collect()
}

/// Render transcript coverage and observed reference loads.
#[must_use]
pub fn reference_heatmap(repo: &Path, corpus_root: &Path) -> String {
    let grouped = skill_runs(corpus_root);
    let mut observed = Vec::new();
    for (skill, runs) in &grouped {
        for run in runs {
            observed.extend(
                reference_reads(repo, run)
                    .into_iter()
                    .map(|path| (skill.clone(), path)),
            );
        }
    }
    let mut counts: BTreeMap<(String, String), usize> = BTreeMap::new();
    for read in &observed {
        *counts.entry(read.clone()).or_default() += 1;
    }
    let token_info = repo_token_info(repo, observed.into_iter().map(|(_, path)| path));
    let mut heatmap: Vec<(String, String, usize)> = counts
        .into_iter()
        .map(|((skill, path), count)| (skill, path, count))
        .collect();
    heatmap.sort_by(|left, right| {
        left.0
            .cmp(&right.0)
            .then_with(|| right.2.cmp(&left.2))
            .then_with(|| left.1.cmp(&right.1))
    });
    let mut output = String::from(
        "# transcript_coverage\nskill\truns_observed\ttranscript_runs_observed\tmissing_transcript_runs\ttranscript_coverage_ratio\treference_capture_status\n",
    );
    for (skill, runs) in &grouped {
        let captured = runs
            .iter()
            .filter(|run| transcript_path(run).is_some())
            .count();
        let ratio = captured as f64 / runs.len() as f64;
        let status = if captured == 0 {
            "not-yet-measured"
        } else {
            "measured"
        };
        let _written = writeln!(
            &mut output,
            "{skill}\t{}\t{captured}\t{}\t{ratio:.6}\t{status}",
            runs.len(),
            runs.len() - captured
        );
    }
    output.push_str("# reference_heatmap\nskill\treference_path\treads_observed\truns_observed\tloads_per_run\tbytes\ttokens\n");
    for (skill, path, count) in heatmap {
        let runs = grouped.get(&skill).map_or(0, Vec::len);
        let loads = count as f64 / runs as f64;
        let (bytes, tokens) = token_info.get(&path).copied().unwrap_or_default();
        let _written = writeln!(
            &mut output,
            "{skill}\t{path}\t{count}\t{runs}\t{loads:.6}\t{bytes}\t{tokens}"
        );
    }
    output
}

fn skill_prompt(repo: &Path, skill: &str) -> Option<PathBuf> {
    [
        repo.join("skills").join(skill).join("SKILL.md"),
        repo.join(".claude/skills").join(skill).join("SKILL.md"),
    ]
    .into_iter()
    .find(|path| path.is_file())
}

#[derive(Debug)]
struct RealizedRow {
    skill: String,
    invocations: usize,
    issues: usize,
    realized: usize,
    skill_tokens: usize,
    reference_tokens: usize,
    reference_reads: usize,
    measured: bool,
}

/// Render realized skill-prompt and observed reference token costs.
#[must_use]
pub fn realized_cost(repo: &Path, corpus_root: &Path) -> String {
    let grouped = skill_runs(corpus_root);
    let mut reads: BTreeMap<String, Vec<String>> = BTreeMap::new();
    for (skill, runs) in &grouped {
        reads.insert(
            skill.clone(),
            runs.iter()
                .flat_map(|run| reference_reads(repo, run))
                .collect(),
        );
    }
    let token_info = repo_token_info(repo, reads.values().flatten().cloned());
    let mut rows = Vec::new();
    for (skill, runs) in &grouped {
        let Some(prompt) = skill_prompt(repo, skill) else {
            continue;
        };
        let skill_tokens = read_lossy(&prompt).map_or(0, |text| token_count(&text));
        let skill_reads = reads.get(skill).map_or(&[][..], Vec::as_slice);
        let reference_tokens = skill_reads
            .iter()
            .map(|path| token_info.get(path).map_or(0, |counts| counts.1))
            .sum();
        let invocations = runs.len();
        rows.push(RealizedRow {
            skill: skill.clone(),
            invocations,
            issues: runs
                .iter()
                .filter_map(|run| run.issue)
                .collect::<BTreeSet<_>>()
                .len(),
            realized: invocations * skill_tokens + reference_tokens,
            skill_tokens,
            reference_tokens,
            reference_reads: skill_reads.len(),
            measured: runs.iter().any(|run| transcript_path(run).is_some()),
        });
    }
    rows.sort_by(|left, right| {
        right
            .realized
            .cmp(&left.realized)
            .then_with(|| left.skill.cmp(&right.skill))
    });
    let mut output = String::from(
        "skill\tinvocations\tissues_observed\ttokens_per_invocation\trealized_tokens\tskill_md_tokens\treference_tokens_per_invocation\treference_reads_observed\treference_capture_status\n",
    );
    for row in rows {
        let total_per_run = row.realized as f64 / row.invocations as f64;
        let refs_per_run = row.reference_tokens as f64 / row.invocations as f64;
        let status = if row.measured {
            "measured"
        } else {
            "not-yet-measured"
        };
        let _written = writeln!(
            &mut output,
            "{}\t{}\t{}\t{total_per_run:.2}\t{}\t{}\t{refs_per_run:.2}\t{}\t{status}",
            row.skill,
            row.invocations,
            row.issues,
            row.realized,
            row.skill_tokens,
            row.reference_reads
        );
    }
    output
}

#[derive(Clone, Copy, Debug, Default)]
struct CacheTotals {
    create: i128,
    create_5m: i128,
    create_1h: i128,
    read: i128,
    effective: i128,
}

impl CacheTotals {
    const fn effective_create(self) -> i128 {
        self.effective
    }

    const fn add(&mut self, other: Self) {
        self.create += other.create;
        self.create_5m += other.create_5m;
        self.create_1h += other.create_1h;
        self.read += other.read;
        self.effective += other.effective;
    }
}

#[derive(Debug)]
struct CacheRunRow {
    skill: String,
    issue: i64,
    started_at: String,
    lane: &'static str,
    title: String,
    totals: CacheTotals,
}

#[derive(Debug)]
struct CacheStepRow {
    skill: String,
    step: String,
    lane: &'static str,
    runs: usize,
    totals: CacheTotals,
}

type CacheStepGroups = BTreeMap<(String, String, &'static str), (usize, CacheTotals)>;

const fn cache_totals(totals: &VendorTotals) -> CacheTotals {
    let split = totals.cache_create_5m as i128 + totals.cache_create_1h as i128;
    CacheTotals {
        create: totals.cache_create as i128,
        create_5m: totals.cache_create_5m as i128,
        create_1h: totals.cache_create_1h as i128,
        read: totals.cache_read as i128,
        effective: if split > 0 {
            split
        } else {
            totals.cache_create as i128
        },
    }
}

fn raw_cache_totals(value: &Value) -> CacheTotals {
    let fields = value.as_object();
    let create = i128::from(safe_int(fields.and_then(|map| map.get("cache_create")), 0));
    let five_minute_create = i128::from(safe_int(
        fields.and_then(|map| map.get("cache_create_5m")),
        0,
    ));
    let one_hour_create = i128::from(safe_int(
        fields.and_then(|map| map.get("cache_create_1h")),
        0,
    ));
    let split = five_minute_create + one_hour_create;
    CacheTotals {
        create,
        create_5m: five_minute_create,
        create_1h: one_hour_create,
        read: i128::from(safe_int(fields.and_then(|map| map.get("cache_read")), 0)),
        effective: if split > 0 { split } else { create },
    }
}

fn add_cache_record(
    skill: &str,
    record: &TokenRunRecord,
    runs: &mut Vec<CacheRunRow>,
    steps: &mut CacheStepGroups,
) {
    for (lane, totals) in [
        ("claude", cache_totals(&record.claude)),
        ("claude_sub", cache_totals(&record.claude_sub)),
    ] {
        runs.push(CacheRunRow {
            skill: skill.to_owned(),
            issue: record.number,
            started_at: record.started_at.clone(),
            lane,
            title: record.title.clone(),
            totals,
        });
        let Some(per_step) = record
            .raw_report
            .get(lane)
            .and_then(Value::as_object)
            .and_then(|fields| fields.get("per_step"))
            .and_then(Value::as_array)
        else {
            continue;
        };
        for item in per_step {
            let step = item
                .get("step")
                .and_then(Value::as_str)
                .filter(|text| !text.is_empty())
                .unwrap_or("unknown");
            let totals = raw_cache_totals(item.get("totals").unwrap_or(&Value::Null));
            let group = steps
                .entry((skill.to_owned(), step.to_owned(), lane))
                .or_default();
            group.0 += 1;
            group.1.add(totals);
        }
    }
}

fn cache_ratio(totals: CacheTotals) -> f64 {
    if totals.effective_create() > 0 && totals.read == 0 {
        f64::INFINITY
    } else if totals.read > 0 {
        totals.effective_create() as f64 / totals.read as f64
    } else {
        0.0
    }
}

fn cache_order(left: CacheTotals, right: CacheTotals) -> Ordering {
    let left_outlier = left.effective_create() > 0 && left.read == 0;
    let right_outlier = right.effective_create() > 0 && right.read == 0;
    right_outlier
        .cmp(&left_outlier)
        .then_with(|| cache_ratio(right).total_cmp(&cache_ratio(left)))
        .then_with(|| right.effective_create().cmp(&left.effective_create()))
        .then_with(|| right.read.cmp(&left.read))
}

fn tsv_cell(text: &str) -> String {
    text.chars()
        .map(|character| match character {
            '\t' | '\r' | '\n' => ' ',
            other => other,
        })
        .collect()
}

fn ratio_text(totals: CacheTotals) -> String {
    let ratio = cache_ratio(totals);
    if ratio.is_infinite() {
        "inf".to_owned()
    } else {
        format!("{ratio:.6}")
    }
}

fn legacy_corpus_warning(warning: &RunLogCorpusWarning) -> String {
    if warning.kind() == RunLogCorpusWarningKind::ManifestMissing {
        let run = warning.path().parent().unwrap_or_else(|| warning.path());
        format!("manifest for {} is missing; skipping", run.display())
    } else {
        warning.message().to_owned()
    }
}

fn scan_cache_rows(
    corpus_root: &Path,
    diagnostic: &mut impl FnMut(&str),
) -> (Vec<CacheRunRow>, CacheStepGroups) {
    let mut runs = Vec::new();
    let mut step_groups = BTreeMap::new();
    for skill in ["design", "implement"] {
        diagnostic(&format!(
            "Scanning {} for larch run logs (--skill={skill})...",
            corpus_root.join(skill).display()
        ));
        let slug = RunLogSlug::parse(skill).expect("fixed cache-report skills are valid slugs");
        let selection = RunLogSelection::for_skill(slug);
        for event in RunLogCorpus::new(corpus_root).select(selection.clone()) {
            if let RunLogCorpusEvent::Warning(warning) = event {
                diagnostic(&format!("Warning: {}", legacy_corpus_warning(&warning)));
            }
        }
        for event in TokenCorpusScan::new(corpus_root, selection, None, None) {
            match event {
                TokenScanEvent::Record(record) => {
                    add_cache_record(skill, &record, &mut runs, &mut step_groups);
                }
                TokenScanEvent::Warning(warning) => {
                    if warning.kind() != TokenScanWarningKind::Corpus {
                        diagnostic(&format!("Warning: {}", warning.message()));
                    }
                }
                TokenScanEvent::Observation(_) => {}
            }
        }
    }
    (runs, step_groups)
}

/// Render ranked per-run and per-step Claude cache creation ratios.
#[must_use]
pub fn token_cache_efficiency(corpus_root: &Path) -> String {
    token_cache_efficiency_with_diagnostics(corpus_root, |_| {})
}

/// Render cache efficiency while surfacing the retired scanner's diagnostics.
#[must_use]
pub fn token_cache_efficiency_with_diagnostics(
    corpus_root: &Path,
    mut diagnostic: impl FnMut(&str),
) -> String {
    let (mut runs, step_groups) = scan_cache_rows(corpus_root, &mut diagnostic);
    runs.retain(|row| row.totals.effective_create() != 0 || row.totals.read != 0);
    runs.sort_by(|left, right| {
        cache_order(left.totals, right.totals).then_with(|| {
            (
                &left.skill,
                left.issue,
                &left.started_at,
                left.lane,
                &left.title,
            )
                .cmp(&(
                    &right.skill,
                    right.issue,
                    &right.started_at,
                    right.lane,
                    &right.title,
                ))
        })
    });
    let mut steps: Vec<CacheStepRow> = step_groups
        .into_iter()
        .map(|((skill, step, lane), (runs, totals))| CacheStepRow {
            skill,
            step,
            lane,
            runs,
            totals,
        })
        .filter(|row| row.totals.effective_create() != 0 || row.totals.read != 0)
        .collect();
    steps.sort_by(|left, right| {
        cache_order(left.totals, right.totals).then_with(|| {
            (&left.skill, &left.step, left.lane).cmp(&(&right.skill, &right.step, right.lane))
        })
    });
    let mut output = String::from(
        "# per_run\nrank\tskill\tissue\tstarted_at\tlane\tcache_create\tcache_create_5m\tcache_create_1h\tcache_read\tratio\ttitle\n",
    );
    for (index, row) in runs.iter().enumerate() {
        let _written = writeln!(
            &mut output,
            "{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}",
            index + 1,
            row.skill,
            row.issue,
            tsv_cell(&row.started_at),
            row.lane,
            row.totals.create,
            row.totals.create_5m,
            row.totals.create_1h,
            row.totals.read,
            ratio_text(row.totals),
            tsv_cell(&row.title)
        );
    }
    output.push_str("\n# per_step\nrank\tskill\tstep\tlane\truns\tcache_create\tcache_create_5m\tcache_create_1h\tcache_read\tratio\n");
    for (index, row) in steps.iter().enumerate() {
        let _written = writeln!(
            &mut output,
            "{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}",
            index + 1,
            row.skill,
            tsv_cell(&row.step),
            row.lane,
            row.runs,
            row.totals.create,
            row.totals.create_5m,
            row.totals.create_1h,
            row.totals.read,
            ratio_text(row.totals)
        );
    }
    output
}

fn safe_run_files(corpus_root: &Path, skills: &[&str], basename: &str) -> Vec<PathBuf> {
    let mut paths = Vec::new();
    for skill in skills {
        for run in safe_child_directories(&corpus_root.join(skill)).directories {
            paths.extend(
                RunLogFileIter::new(&run).filter(|path| {
                    path.file_name().and_then(|name| name.to_str()) == Some(basename)
                }),
            );
        }
    }
    paths.sort();
    paths
}

fn header_index(headers: &StringRecord, name: &str) -> Option<usize> {
    headers
        .iter()
        .enumerate()
        .filter_map(|(index, field)| (field == name).then_some(index))
        .last()
}

fn check_unsigned(record: &StringRecord, headers: &StringRecord, name: &str) -> Option<i128> {
    let value = record
        .get(header_index(headers, name)?)
        .unwrap_or("")
        .trim();
    (!value.is_empty() && value.bytes().all(|byte| byte.is_ascii_digit()))
        .then(|| value.parse().ok())
        .flatten()
}

fn check_signed(record: &StringRecord, headers: &StringRecord, name: &str) -> Option<i128> {
    let value = record
        .get(header_index(headers, name)?)
        .unwrap_or("")
        .trim();
    let digits = value.strip_prefix('-').unwrap_or(value);
    (!digits.is_empty() && digits.bytes().all(|byte| byte.is_ascii_digit()))
        .then(|| value.parse().ok())
        .flatten()
}

#[derive(Clone, Copy, Debug, Default)]
struct ChecksAggregate {
    valid_rows: usize,
    files_observed: usize,
    rows_seen: usize,
    rows_skipped: usize,
    redacted_bytes: i128,
    digest_bytes: i128,
    redacted_tokens: i128,
    digest_tokens: i128,
    saved_bytes: i128,
    saved_tokens: i128,
}

fn add_checks_file(path: &Path, aggregate: &mut ChecksAggregate) {
    let Ok(bytes) = fs::read(path) else {
        return;
    };
    let text = String::from_utf8_lossy(&bytes);
    let mut reader = ReaderBuilder::new()
        .delimiter(b'\t')
        .flexible(true)
        .from_reader(text.as_bytes());
    let Ok(headers) = reader.headers().cloned() else {
        return;
    };
    if CHECKS_DIGEST_FIELDS
        .iter()
        .any(|field| header_index(&headers, field).is_none())
    {
        return;
    }
    aggregate.files_observed += 1;
    for record in reader.records().flatten() {
        aggregate.rows_seen += 1;
        let values = [
            check_unsigned(&record, &headers, "redacted_bytes"),
            check_unsigned(&record, &headers, "digest_bytes"),
            check_unsigned(&record, &headers, "redacted_tokens"),
            check_unsigned(&record, &headers, "digest_tokens"),
            check_signed(&record, &headers, "saved_bytes"),
            check_signed(&record, &headers, "saved_tokens"),
        ];
        let [
            Some(redacted_bytes),
            Some(digest_bytes),
            Some(redacted_tokens),
            Some(digest_tokens),
            Some(saved_bytes),
            Some(saved_tokens),
        ] = values
        else {
            aggregate.rows_skipped += 1;
            continue;
        };
        aggregate.valid_rows += 1;
        aggregate.redacted_bytes += redacted_bytes;
        aggregate.digest_bytes += digest_bytes;
        aggregate.redacted_tokens += redacted_tokens;
        aggregate.digest_tokens += digest_tokens;
        aggregate.saved_bytes += saved_bytes;
        aggregate.saved_tokens += saved_tokens;
    }
}

/// Render aggregate checks-digest savings telemetry.
#[must_use]
pub fn checks_digest_savings(corpus_root: &Path) -> String {
    let mut aggregate = ChecksAggregate::default();
    for skill in ["implement", "review"] {
        for run in safe_child_directories(&corpus_root.join(skill)).directories {
            let path = run.join("checks-digest-sizes.tsv");
            if is_contained_regular_file(&run, &path) {
                add_checks_file(&path, &mut aggregate);
            }
        }
    }
    let sufficient = aggregate.valid_rows >= 5;
    let recommendation = if !sufficient {
        ""
    } else if aggregate.saved_tokens > 0 {
        "go-design-validator-extension"
    } else {
        "no-go-design-validator-extension"
    };
    format!(
        "status\trecommendation\tvalid_rows\tfiles_observed\trows_seen\trows_skipped\tredacted_bytes\tdigest_bytes\tredacted_tokens\tdigest_tokens\tsaved_bytes\tsaved_tokens\n{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\n",
        if sufficient {
            "sufficient-data"
        } else {
            "insufficient-data"
        },
        recommendation,
        aggregate.valid_rows,
        aggregate.files_observed,
        aggregate.rows_seen,
        aggregate.rows_skipped,
        aggregate.redacted_bytes,
        aggregate.digest_bytes,
        aggregate.redacted_tokens,
        aggregate.digest_tokens,
        aggregate.saved_bytes,
        aggregate.saved_tokens
    )
}

#[derive(Debug, Default)]
struct PanelAggregate {
    dispatches: usize,
    prompt_bytes: u128,
    prompt_tokens: u128,
    scaffold_bytes: u128,
    scaffold_tokens: u128,
    payload_bytes: u128,
    payload_tokens: u128,
    agent_bytes: u128,
    agent_tokens: u128,
    runs: BTreeSet<(String, String)>,
}

fn is_round(value: &str) -> bool {
    value.strip_prefix("round-").is_some_and(|digits| {
        !digits.is_empty() && digits.bytes().all(|byte| byte.is_ascii_digit())
    })
}

fn panel_context(corpus_root: &Path, path: &Path) -> Option<(String, String)> {
    let corpus_root = fs::canonicalize(corpus_root).ok()?;
    let parts: Vec<String> = path
        .strip_prefix(&corpus_root)
        .ok()?
        .components()
        .map(|part| part.as_os_str().to_string_lossy().into_owned())
        .collect();
    let [skill, run_id, rest @ ..] = parts.as_slice() else {
        return None;
    };
    let valid = match skill.as_str() {
        "design" => rest.len() == 3 && rest[0] == "plan-review" && is_round(&rest[1]),
        "implement" => rest.len() == 2 && is_round(&rest[0]),
        "review" => rest.len() == 1 || (rest.len() == 2 && is_round(&rest[0])),
        _ => false,
    };
    (valid
        && rest
            .last()
            .is_some_and(|name| name == "panel-prompt-sizes.tsv"))
    .then(|| (skill.clone(), run_id.clone()))
}

fn panel_uint(record: &StringRecord, headers: &StringRecord, name: &str) -> u128 {
    let value = header_index(headers, name)
        .and_then(|index| record.get(index))
        .unwrap_or("");
    if !value.is_empty() && value.bytes().all(|byte| byte.is_ascii_digit()) {
        value.parse().unwrap_or(0)
    } else {
        0
    }
}

fn add_panel_file(
    corpus_root: &Path,
    path: &Path,
    aggregates: &mut BTreeMap<(String, String, String), PanelAggregate>,
) {
    let Some((skill, run_id)) = panel_context(corpus_root, path) else {
        return;
    };
    let Ok(bytes) = fs::read(path) else {
        return;
    };
    let text = String::from_utf8_lossy(&bytes);
    let mut reader = ReaderBuilder::new()
        .delimiter(b'\t')
        .flexible(true)
        .from_reader(text.as_bytes());
    let Ok(headers) = reader.headers().cloned() else {
        return;
    };
    let Some(slot_index) = header_index(&headers, "slot_kind") else {
        return;
    };
    let agent_index = header_index(&headers, "agent_file");
    let split = header_index(&headers, "scaffold_bytes").is_some()
        && header_index(&headers, "payload_bytes").is_some();
    for record in reader.records().flatten() {
        let slot = record.get(slot_index).unwrap_or("").trim();
        if !PANEL_SLOTS.contains(&slot) {
            continue;
        }
        let agent = agent_index
            .and_then(|index| record.get(index))
            .unwrap_or("")
            .trim();
        let agent = if agent.is_empty() {
            format!("generated/no-agent:{slot}")
        } else {
            agent.to_owned()
        };
        let prompt_bytes = panel_uint(&record, &headers, "prompt_bytes");
        let prompt_tokens = panel_uint(&record, &headers, "prompt_tokens");
        let aggregate = aggregates
            .entry((skill.clone(), agent, slot.to_owned()))
            .or_default();
        aggregate.dispatches += 1;
        aggregate.prompt_bytes += prompt_bytes;
        aggregate.prompt_tokens += prompt_tokens;
        aggregate.scaffold_bytes += if split {
            panel_uint(&record, &headers, "scaffold_bytes")
        } else {
            prompt_bytes
        };
        aggregate.scaffold_tokens += if split {
            panel_uint(&record, &headers, "scaffold_tokens")
        } else {
            prompt_tokens
        };
        if split {
            aggregate.payload_bytes += panel_uint(&record, &headers, "payload_bytes");
            aggregate.payload_tokens += panel_uint(&record, &headers, "payload_tokens");
        }
        aggregate.agent_bytes += panel_uint(&record, &headers, "agent_bytes");
        aggregate.agent_tokens += panel_uint(&record, &headers, "agent_tokens");
        let _inserted = aggregate.runs.insert((skill.clone(), run_id.clone()));
    }
}

/// Render aggregate panel prompt and agent-file costs.
#[must_use]
pub fn panel_cost(corpus_root: &Path) -> String {
    let mut aggregates = BTreeMap::new();
    for path in safe_run_files(
        corpus_root,
        &["design", "implement", "review"],
        "panel-prompt-sizes.tsv",
    ) {
        add_panel_file(corpus_root, &path, &mut aggregates);
    }
    let mut rows: Vec<_> = aggregates.into_iter().collect();
    rows.sort_by(|left, right| {
        let ((left_skill, left_agent, left_slot), left_aggregate) = left;
        let ((right_skill, right_agent, right_slot), right_aggregate) = right;
        right_aggregate
            .scaffold_bytes
            .cmp(&left_aggregate.scaffold_bytes)
            .then_with(|| {
                (right_aggregate.prompt_bytes + right_aggregate.agent_bytes)
                    .cmp(&(left_aggregate.prompt_bytes + left_aggregate.agent_bytes))
            })
            .then_with(|| left_agent.cmp(right_agent))
            .then_with(|| left_slot.cmp(right_slot))
            .then_with(|| left_skill.cmp(right_skill))
    });
    let mut output = String::from(
        "skill\tagent_file\tslot_kind\tdispatch_count\truns_observed\tloads_per_run\tprompt_bytes\tprompt_tokens\tscaffold_bytes\tscaffold_tokens\tpayload_bytes\tpayload_tokens\tagent_bytes\tagent_tokens\trealized_bytes\trealized_tokens\n",
    );
    for ((skill, agent, slot), aggregate) in rows {
        let runs = aggregate.runs.len();
        let loads = aggregate.dispatches as f64 / runs as f64;
        let _written = writeln!(
            &mut output,
            "{skill}\t{agent}\t{slot}\t{}\t{runs}\t{loads:.6}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}",
            aggregate.dispatches,
            aggregate.prompt_bytes,
            aggregate.prompt_tokens,
            aggregate.scaffold_bytes,
            aggregate.scaffold_tokens,
            aggregate.payload_bytes,
            aggregate.payload_tokens,
            aggregate.agent_bytes,
            aggregate.agent_tokens,
            aggregate.prompt_bytes + aggregate.agent_bytes,
            aggregate.prompt_tokens + aggregate.agent_tokens
        );
    }
    output
}

#[cfg(test)]
mod tests {
    use super::{
        checks_digest_savings, markdown_cost, ngram_duplication, panel_cost, realized_cost,
        reference_heatmap, token_cache_efficiency_with_diagnostics, token_count,
    };
    use serde_json::{Value, json};
    use std::{fs, path::Path};
    use tempfile::tempdir;

    fn write(path: &Path, text: &str) {
        fs::create_dir_all(path.parent().unwrap()).unwrap();
        fs::write(path, text).unwrap();
    }

    fn run(root: &Path, skill: &str, id: &str, issue: u64) -> std::path::PathBuf {
        let path = root.join(skill).join(id);
        write(
            &path.join("manifest.json"),
            &json!({
                "issue_number": issue,
                "title": format!("Issue {issue}"),
                "started_at": "2026-06-01T00:00:00Z"
            })
            .to_string(),
        );
        path
    }

    fn token_report(path: &Path, value: &Value) {
        write(path, &value.to_string());
    }

    #[test]
    fn repository_measurements_keep_markdown_and_ngram_wires() {
        let temporary = tempdir().unwrap();
        let repo = temporary.path();
        write(
            &repo.join("CLAUDE.md"),
            "@AGENTS.md\none two three four five six\n",
        );
        write(&repo.join("AGENTS.md"), "one two three four five six\n");
        write(
            &repo.join("skills/design/SKILL.md"),
            "one two three four five six\n",
        );
        write(&repo.join("docs/sample.md"), "# Title\n\n## Part\nBody\n");
        let tracked = [
            b"AGENTS.md".to_vec(),
            b"CLAUDE.md".to_vec(),
            b"docs/sample.md".to_vec(),
            b"skills/design/SKILL.md".to_vec(),
        ];

        let markdown = markdown_cost(repo, &tracked).unwrap();
        assert!(markdown.starts_with("path\ttier\tbytes\ttokens\tlines\th2_count\n"));
        assert!(markdown.contains("CLAUDE.md\ttier-1a-claude-root"));
        assert!(markdown.contains("docs/sample.md\ttier-3-doc"));

        let ngrams = ngram_duplication(repo, &tracked, 6, 3, 50).unwrap();
        assert!(ngrams.starts_with("score\toccurrences\tfiles\tshingle\n"));
        assert!(ngrams.contains("18\t3\t3\tone two three four five six\n"));
    }

    #[test]
    fn reference_reports_include_coverage_reads_and_realized_tokens() {
        let temporary = tempdir().unwrap();
        let repo = temporary.path();
        let corpus = repo.join("corpus");
        write(&repo.join("skills/design/SKILL.md"), "design prompt\n");
        write(&repo.join("skills/shared/topology.md"), "shared topology\n");
        let first = run(&corpus, "design", "run-1", 1);
        let _second = run(&corpus, "design", "run-2", 2);
        write(
            &first.join("session-transcript.jsonl"),
            &format!(
                "{}\n{}\n",
                json!({"blocks": [
                    {"type": "tool_use", "name": "Read", "input": {"file_path": "skills/shared/topology.md"}},
                    {"type": "tool_call", "name": "Read", "input": {"file_path": "<OPERATOR_REPO_PATH>/skills/shared/topology.md"}}
                ]}),
                json!({"message": {"content": [{"type": "tool_use", "name": "Read", "input": {"file_path": format!("{}/skills/shared/topology.md", repo.display())}}]}})
            ),
        );

        let heatmap = reference_heatmap(repo, &corpus);
        assert!(heatmap.contains("design\t2\t1\t1\t0.500000\tmeasured\n"));
        assert!(heatmap.contains("design\tskills/shared/topology.md\t3\t2\t1.500000"));

        let realized = realized_cost(repo, &corpus);
        let skill_tokens = token_count("design prompt\n");
        let reference_tokens = token_count("shared topology\n") * 3;
        let total = skill_tokens * 2 + reference_tokens;
        assert!(realized.contains(&format!(
            "design\t2\t2\t{:.2}\t{total}\t{skill_tokens}\t{:.2}\t3\tmeasured\n",
            total as f64 / 2.0,
            reference_tokens as f64 / 2.0
        )));
    }

    #[test]
    fn cache_report_ranks_outlier_and_sums_legacy_and_split_steps() {
        let temporary = tempdir().unwrap();
        let corpus = temporary.path();
        fs::create_dir_all(corpus.join("design/missing-manifest")).unwrap();
        let first = run(corpus, "design", "run-1", 1);
        token_report(
            &first.join("token-report-final.json"),
            &json!({"claude": {
                "totals": {"cache_create_5m": 3, "cache_create_1h": 2, "cache_read": 5},
                "per_step": [{"step": "3", "totals": {"cache_create_5m": 3, "cache_create_1h": 2, "cache_read": 5}}]
            }}),
        );
        let second = run(corpus, "design", "run-2", 2);
        token_report(
            &second.join("token-report-final.json"),
            &json!({"claude": {
                "totals": {"cache_create": 7, "cache_read": 5},
                "per_step": [{"step": "3", "totals": {"cache_create": 7, "cache_read": 5}}]
            }}),
        );
        let outlier = run(corpus, "implement", "run-3", 3);
        token_report(
            &outlier.join("token-report.json"),
            &json!({"claude_sub": {
                "totals": {"cache_create": 9, "cache_read": 0},
                "per_step": [{"step": "5", "totals": {"cache_create": 9, "cache_read": 0}}]
            }}),
        );

        let mut diagnostics = Vec::new();
        let report = token_cache_efficiency_with_diagnostics(corpus, |line| {
            diagnostics.push(line.to_owned());
        });
        assert!(report.starts_with("# per_run\n"));
        assert!(report.contains(
            "1\timplement\t3\t2026-06-01T00:00:00Z\tclaude_sub\t9\t0\t0\t0\tinf\tIssue 3\n"
        ));
        assert!(report.contains("design\t3\tclaude\t2\t7\t3\t2\t10\t1.200000\n"));
        assert!(diagnostics[0].contains("for larch run logs (--skill=design)..."));
        assert!(
            diagnostics
                .iter()
                .any(|line| line.starts_with("Warning: manifest for "))
        );
    }

    #[test]
    fn checks_and_panel_reports_preserve_aggregate_wires() {
        let temporary = tempdir().unwrap();
        let corpus = temporary.path();
        let checks = corpus.join("implement/run-1/checks-digest-sizes.tsv");
        write(
            &checks,
            &format!(
                "site\tattempt\tredacted_bytes\tdigest_bytes\tredacted_tokens\tdigest_tokens\tsaved_bytes\tsaved_tokens\tdigest_truncated\n{}",
                "step6\t1\t100\t20\t25\t5\t80\t20\tfalse\n".repeat(5)
            ),
        );
        let digest = checks_digest_savings(corpus);
        assert!(digest.contains(
            "sufficient-data\tgo-design-validator-extension\t5\t1\t5\t0\t500\t100\t125\t25\t400\t100\n"
        ));

        let panel = corpus.join("review/run-2/panel-prompt-sizes.tsv");
        write(
            &panel,
            "site\tphase\tround_num\tslot\tslot_kind\ttool\toutput\tprompt_bytes\tprompt_tokens\tagent_file\tagent_bytes\tagent_tokens\nreview\t\t\taggregator\taggregator\tcodex\tagg.txt\t70\t18\tagents/aggregator.md\t30\t8\n",
        );
        let report = panel_cost(corpus);
        assert!(
            report.contains(
                "review\tagents/aggregator.md\taggregator\t1\t1\t1.000000\t70\t18\t70\t18\t0\t0\t30\t8\t100\t26\n"
            ),
            "{report}"
        );
    }
}
