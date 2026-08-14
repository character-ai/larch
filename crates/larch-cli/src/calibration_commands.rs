//! Rust owners for voter-calibration snapshots and calibration replay.

#[rustfmt::skip]
mod implementation {

use crate::{
    argparse_compat::{missing, parse_with_flags, python_repr, usage_error},
    launcher_support::confined_target,
    runtime_entrypoint::run_verified_larch_with_environment,
    voter_dispatch_commands::voter_output_name,
};
use larch_adapters::{PathIntent, RepositoryRoot, TemporaryRoot, absolute_lexical, atomic_write_utf8_in, ensure_directory_chain, read_utf8, resolve_allow_missing};
use larch_core::{
    ChildEnvironment, DuplicatePolicy, KvDocument, ParseOptions, RunLogCorpus, RunLogRoundSort, emit_kv, file_line_regex,
    review::{LedgerRow, parse_judge_vote_text, write_round},
    python_str, run_started_at_without_manifest,
};
use regex::Regex;
use serde_json::Value;
use std::{
    collections::{BTreeMap, BTreeSet},
    env,
    ffi::OsString,
    fmt::Write as _,
    fs,
    path::{Component, Path, PathBuf},
    process::ExitCode,
    sync::LazyLock,
};

const FIXTURE_ROOT: &str = "python/test_fixtures/plan-fidelity-calibration";
const DEFAULT_MANIFEST: &str = "python/test_fixtures/plan-fidelity-calibration/manifest.tsv";
const DEFAULT_COHORT: &str = "python/test_fixtures/plan-fidelity-calibration/cohort.tsv";
const DEFAULT_BALLOTS: &str = "python/test_fixtures/plan-fidelity-calibration/ballots";
const DEFAULT_PLANS: &str = "python/test_fixtures/plan-fidelity-calibration/plans";
const DEFAULT_DIFFS: &str = "python/test_fixtures/plan-fidelity-calibration/diffs";
const SNAPSHOT_HEADER: &str = "tool\tyes_votes\tvalid_yes_severity_count\tmajor\tminor\tnit\tmissing_severity\thigh_rate\tcalibration_score\tuncalibrated\n";
const SNAPSHOT_USAGE: &str = "usage: cli.py voter-calibration snapshot [-h] [--log-root LOG_ROOT] --out OUT\n                                         [--window WINDOW]";
const REBUILD_USAGE: &str = "usage: calibration-replay rebuild-ballot [-h] --finding-id FINDING_ID\n                                         --run-root RUN_ROOT --round-num\n                                         ROUND_NUM\n                                         [--fixture-ballot FIXTURE_BALLOT]\n                                         [--repo-root REPO_ROOT]\n                                         [--output OUTPUT]";
const VALIDATE_USAGE: &str = "usage: calibration-replay validate-manifest [-h] [--manifest MANIFEST]\n                                            [--cohort COHORT]";
const REPLAY_USAGE: &str = "usage: calibration-replay run-replay [-h] [--manifest MANIFEST]\n                                     [--cohort COHORT] --work-dir WORK_DIR\n                                     [--dry-run]";
type Row = BTreeMap<String, String>;

static RUN_ID: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"(?i)^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$").expect("static run-id regex"));
static HEADING: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"^###[ \t]+((?:FINDING|OOS)_[A-Za-z0-9_]+):").expect("static ballot-heading regex"));
static REVIEWER: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"^([ \t-]*(?:\*\*Reviewer\(s\)\*\*|\*\*Reviewers?\*\*|Reviewer\(s\)|Reviewers?)\s*:\s*)(.*?)([ \t]*)$").expect("static reviewer regex"));
static POINTER: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?i)^(?:see\s+plan(?:\.txt)?(?:\s+.*)?|see\s+attached(?:\s+.*)?|see\s+linked(?:\s+.*)?|tbd(?:\s*:.*)?|todo(?:\s*:.*)?)\.?\s*$").expect("static pointer regex")
});

fn option(parsed: &crate::argparse_compat::ParsedCommandLine, name: &str) -> String {
    parsed.value(name).map_or_else(String::new, |value| value.to_string_lossy().into_owned())
}

fn options(
    arguments: &[OsString],
    program: &str,
    usage: &str,
    values: &[&'static str],
    flags: &[&'static str],
    required: &[&str],
) -> Result<crate::argparse_compat::ParsedCommandLine, ExitCode> {
    let mut all_flags = flags.to_vec();
    all_flags.extend(["-h", "--help"]);
    let parsed = parse_with_flags(arguments, values, &all_flags, 0);
    if parsed.flag("-h") || parsed.flag("--help") {
        println!("{usage}");
        return Err(ExitCode::SUCCESS);
    }
    if let Some(error) = parsed.value_error() {
        return Err(usage_error(usage, program, error, 2));
    }
    let states: Vec<_> = required.iter().map(|name| (*name, parsed.value(name).is_some())).collect();
    if states.iter().any(|(_, present)| !present) {
        return Err(usage_error(usage, program, &missing(&states), 2));
    }
    if let Some(error) = parsed.error() {
        return Err(usage_error(usage, program, &error, 2));
    }
    Ok(parsed)
}

fn read_text(path: &Path) -> Result<String, String> {
    fs::read(path).map(|bytes| String::from_utf8_lossy(&bytes).into_owned()).map_err(|_| format!("unable to read {}", path.display()))
}

fn safe_text(root: &Path, path: &Path) -> Result<String, String> {
    let root = RepositoryRoot::resolve(Some(&absolute_lexical(root))).map_err(|error| error.to_string())?;
    let path = root.confine(path, PathIntent::Read).map_err(|error| format!("unsafe synchronized input {}: {error}", path.display()))?;
    read_utf8(&path).map_err(|_| format!("unable to read {}", path.path().display()))
}

fn tsv_rows(path: &Path) -> Result<Vec<Row>, String> {
    if !path.is_file() { return Err(format!("tsv not found: {}", path.display())); }
    tsv_text_rows(&read_text(path)?)
}

fn tsv_text_rows(text: &str) -> Result<Vec<Row>, String> {
    let mut reader = csv::ReaderBuilder::new().delimiter(b'\t').flexible(true).from_reader(text.as_bytes());
    let header = reader.headers().map_err(|error| error.to_string())?.clone();
    reader
        .records()
        .map(|record| {
            let record = record.map_err(|error| error.to_string())?;
            Ok(header.iter().enumerate().map(|(index, key)| (key.to_owned(), record.get(index).unwrap_or("").to_owned())).collect())
        })
        .collect()
}

fn cell<'a>(row: &'a Row, key: &str) -> &'a str {
    row.get(key).map_or("", |value| value.trim())
}

#[derive(Default)]
struct Stat {
    yes: u64,
    valid: u64,
    major: u64,
    minor: u64,
    nit: u64,
    missing: u64,
}

fn base_tool(label: &str) -> Option<&'static str> {
    let label = label.trim().to_lowercase();
    if label == "claude" {
        Some("claude")
    } else if label.starts_with("codex") || matches!(label.as_str(), "v2" | "v3") {
        Some("codex")
    } else if label.starts_with("cursor") || label == "v1" {
        Some("cursor")
    } else {
        None
    }
}

fn collect_stats(inputs: impl IntoIterator<Item = (bool, String)>) -> Vec<(String, Stat)> {
    let mut totals: BTreeMap<String, Stat> = BTreeMap::new();
    for (design, text) in inputs {
        let mut reader = csv::ReaderBuilder::new().delimiter(b'\t').flexible(true).from_reader(text.as_bytes());
        let Ok(header) = reader.headers().cloned() else {
            continue;
        };
        let has = |name: &str| header.iter().any(|field| field == name);
        let supported = if design {
            ["finding_id", "finding_reviewers", "voting_result", "v1_vote", "v2_vote", "v3_vote"]
                .iter()
                .all(|field| has(field))
        } else {
            has("finding_id")
                && has("reviewer_slots")
                && has("voting_result")
                && (1..=3).all(|slot| {
                    ["vote", "correctness", "severity", "quality", "uncertain"]
                        .iter()
                        .all(|field| has(&format!("v{slot}_{field}")))
                })
        };
        if !supported {
            continue;
        }
        let labels_are_compact = !design && !(1..=3).any(|slot| has(&format!("v{slot}_tool")));
        for record in reader.records().flatten() {
            let row: Row = header
                .iter()
                .enumerate()
                .map(|(index, key)| (key.to_owned(), record.get(index).unwrap_or("").to_owned()))
                .collect();
            if !matches!(cell(&row, "voting_result").to_lowercase().as_str(), "accepted" | "rejected")
                || (1..=3)
                    .filter(|slot| matches!(cell(&row, &format!("v{slot}_vote")).to_uppercase().as_str(), "YES" | "NO" | "EXONERATE"))
                    .count()
                    < 2
            {
                continue;
            }
            for slot in 1..=3 {
                let fallback = match slot {
                    1 => "codex-validity",
                    2 => "codex-plan-fidelity",
                    _ => "codex-pragmatism",
                };
                let label = if labels_are_compact {
                    match slot {
                        1 => "v1",
                        2 => "v2",
                        _ => "v3",
                    }
                } else {
                    let value = cell(&row, &format!("v{slot}_tool"));
                    if value.is_empty() { fallback } else { value }
                };
                let Some(tool) = base_tool(label) else {
                    continue;
                };
                let stat = totals.entry(tool.to_owned()).or_default();
                if cell(&row, &format!("v{slot}_vote")).to_uppercase() != "YES" {
                    continue;
                }
                stat.yes += 1;
                match cell(&row, &format!("v{slot}_severity")).to_lowercase().as_str() {
                    "major" | "blocker" => {
                        stat.major += 1;
                        stat.valid += 1;
                    }
                    "minor" => {
                        stat.minor += 1;
                        stat.valid += 1;
                    }
                    "nit" => {
                        stat.nit += 1;
                        stat.valid += 1;
                    }
                    _ => stat.missing += 1,
                }
            }
        }
    }
    totals.into_iter().filter(|(_, stat)| stat.valid > 0).collect()
}

#[allow(clippy::cast_precision_loss)]
fn snapshot_text(log_root: &Path, window: usize) -> Option<String> {
    let mut by_run: BTreeMap<PathBuf, Vec<(bool, PathBuf)>> = BTreeMap::new();
    for (skill, design) in [("design", true), ("implement", false), ("review", false)] {
        for (run, path) in RunLogCorpus::new(log_root.join(skill)).classification_paths_without_manifest(skill, RunLogRoundSort::Lexical) {
            by_run.entry(run).or_default().push((design, path));
        }
    }
    let mut runs: Vec<_> = by_run.into_iter().collect();
    runs.sort_by(|(left, _), (right, _)| (run_started_at_without_manifest(right), right).cmp(&(run_started_at_without_manifest(left), left)));
    let inputs = runs.into_iter().take(window).flat_map(|(_, mut rows)| {
        rows.sort_by(|left, right| left.1.cmp(&right.1));
        rows.into_iter().filter_map(|(panel, path)| safe_text(log_root, &path).ok().map(|text| (panel, text)))
    });
    let stats = collect_stats(inputs);
    if stats.is_empty() {
        return None;
    }
    let mut output = SNAPSHOT_HEADER.to_owned();
    for (tool, stat) in stats {
        let rate = stat.major as f64 / stat.valid as f64;
        let score = if rate <= 0.9 { 1.0 } else { ((1.0 - rate) / 0.1).clamp(0.0, 1.0) };
        let _ = writeln!(
            output,
            "{tool}\t{}\t{}\t{}\t{}\t{}\t{}\t{rate:.3}\t{score:.3}\t{}",
            stat.yes,
            stat.valid,
            stat.major,
            stat.minor,
            stat.nit,
            stat.missing,
            rate > 0.9
        );
    }
    Some(output)
}

pub fn positive_window(value: &str) -> Option<usize> {
    value.trim().parse().ok().filter(|value| *value > 0)
}

pub fn write_calibration_snapshot(log_root: &Path, output: &Path, window: usize) -> Result<bool, String> {
    let Some(text) = snapshot_text(log_root, window) else {
        match fs::remove_file(output) {
            Ok(()) => {}
            Err(error) if error.kind() == std::io::ErrorKind::NotFound => {}
            Err(error) => return Err(error.to_string()),
        }
        return Ok(false);
    };
    let output = absolute_lexical(output);
    let (root, target) = confined_target(&output).ok_or_else(|| "unsafe calibration output path".to_owned())?;
    atomic_write_utf8_in(&root, &target, &text, true, 0o600).map_err(|error| error.to_string())?;
    Ok(true)
}

fn default_log_root() -> Result<PathBuf, String> {
    let worktree = |path: &Path| crate::launcher_support::git_workdir(path).map(|root| absolute_lexical(&root));
    let plugin = crate::python_verb::plugin_root_directory().map(|root| worktree(&root).unwrap_or_else(|| absolute_lexical(&root)));
    for name in ["LARCH_CONSUMER_REPO", "CLAUDE_PROJECT_DIR", "REPO_ROOT"] {
        if let Some(root) = env::var_os(name).filter(|value| !value.is_empty()) {
            let root = worktree(Path::new(&root)).unwrap_or_else(|| absolute_lexical(Path::new(&root)));
            if plugin.as_ref() != Some(&root) { return Ok(root.join("larch-logs")); }
        }
    }
    let cwd = env::current_dir().map_err(|error| error.to_string())?;
    let root = worktree(&cwd).filter(|root| plugin.as_ref() != Some(root)).ok_or_else(|| "voter calibration log root unresolved".to_owned())?;
    Ok(root.join("larch-logs"))
}

pub fn voter_calibration_snapshot(arguments: &[OsString]) -> ExitCode {
    let parsed = match options(
        arguments,
        "cli.py voter-calibration snapshot",
        SNAPSHOT_USAGE,
        &["--log-root", "--out", "--window"],
        &[],
        &["--out"],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let log_root = if option(&parsed, "--log-root").is_empty() {
        match default_log_root() {
            Ok(path) => path,
            Err(error) => {
                eprintln!("voter-calibration snapshot: {error}");
                return ExitCode::FAILURE;
            }
        }
    } else {
        absolute_lexical(Path::new(&option(&parsed, "--log-root")))
    };
    let window_raw = if option(&parsed, "--window").is_empty() {
        env::var("LARCH_VOTER_CALIBRATION_WINDOW").unwrap_or_default()
    } else {
        option(&parsed, "--window")
    };
    let window = positive_window(&window_raw).unwrap_or(100);
    let output = PathBuf::from(option(&parsed, "--out"));
    match write_calibration_snapshot(&log_root, &output, window) {
        Ok(true) => emit_kv("CALIBRATION_STATS_FILE", &output.display().to_string()),
        Ok(false) => {
            emit_kv("CALIBRATION_STATS_FILE", "");
            emit_kv("CALIBRATION_STATS_STATUS", "no-data");
        }
        Err(error) => {
            eprintln!("voter-calibration snapshot: {error}");
            return ExitCode::FAILURE;
        }
    }
    ExitCode::SUCCESS
}

fn relative_path(repo: &Path, raw: &str, field: &str, required: bool) -> Result<Option<PathBuf>, String> {
    let value = raw.trim();
    if value.is_empty() {
        return if required { Err(format!("{field} is required")) } else { Ok(None) };
    }
    let path = Path::new(value);
    if path.is_absolute() || path.components().any(|part| part == Component::ParentDir) {
        return Err(format!("{field} must be a repo-relative path"));
    }
    Ok(Some(repo.join(path)))
}

fn require_under(path: &Path, root: &Path, field: &str, label: &str) -> Result<(), String> {
    let path = fs::canonicalize(path).map_err(|_| format!("{field} is not readable: {}", path.display()))?;
    let root = fs::canonicalize(root).map_err(|_| format!("{field} must be under {label}: {}", path.display()))?;
    if path.starts_with(root) {
        Ok(())
    } else {
        Err(format!("{field} must be under {label}: {}", path.display()))
    }
}

fn round_value(raw: &str) -> Option<u64> {
    (!raw.is_empty() && raw.bytes().all(|byte| byte.is_ascii_digit()))
        .then(|| raw.parse().ok())
        .flatten()
        .filter(|value| *value > 0)
}

fn assert_run(repo: &Path, run_root: &Path, run_id: &str) -> Result<(), String> {
    if !RUN_ID.is_match(run_id) {
        return Err(format!("run_id must be a UUID-shaped implement run id: {}", python_repr(run_id)));
    }
    let expected = absolute_lexical(&repo.join("larch-logs/implement").join(run_id));
    let actual = absolute_lexical(run_root);
    if actual != expected {
        return Err(format!("run_root must be larch-logs/implement/{run_id}: {}", run_root.display()));
    }
    Ok(())
}

fn strip_tally(text: &str) -> String {
    let mut lines: Vec<_> = text.lines().collect();
    while lines.last().is_some_and(|line| line.trim().is_empty()) {
        lines.pop();
    }
    while lines.last().is_some_and(|line| line.trim().to_lowercase().starts_with("vote tally:")) {
        lines.pop();
        while lines.last().is_some_and(|line| line.trim().is_empty()) {
            lines.pop();
        }
    }
    if lines.is_empty() {
        String::new()
    } else {
        format!("{}\n", lines.join("\n").trim_matches('\n'))
    }
}

fn ballot_block(text: &str, finding: &str) -> String {
    let lines: Vec<_> = text.lines().collect();
    let Some(start) = lines.iter().position(|line| HEADING.captures(line).is_some_and(|captures| &captures[1] == finding)) else {
        return String::new();
    };
    let end = lines[start + 1..]
        .iter()
        .position(|line| HEADING.is_match(line))
        .map_or(lines.len(), |offset| start + 1 + offset);
    format!("{}\n", lines[start..end].join("\n").trim())
}

fn neutralize(text: &str) -> String {
    let mut replaced = false;
    let trailing_newline = text.ends_with('\n');
    let lines: Vec<_> = text
        .lines()
        .map(|line| {
            if !replaced && let Some(captures) = REVIEWER.captures(line) {
                replaced = true;
                return format!("{}anonymous{}", &captures[1], &captures[3]);
            }
            line.to_owned()
        })
        .collect();
    format!("{}{}", lines.join("\n"), if trailing_newline { "\n" } else { "" })
}

fn jsonl_ballot(repo: &Path, run_root: &Path, finding: &str, round: u64) -> Result<Option<String>, String> {
    let path = run_root.join("review-findings-full.jsonl");
    if !path.is_file() {
        return Ok(None);
    }
    for line in safe_text(repo, &path)?.lines().filter(|line| !line.trim().is_empty()) {
        let Ok(Value::Object(record)) = serde_json::from_str::<Value>(line) else {
            continue;
        };
        if python_str(record.get("id")) != finding || python_str(record.get("round_num")).trim() != round.to_string() {
            continue;
        }
        let body = python_str(record.get("prose_body"));
        if body.chars().count() == 2000 {
            return Err(format!(
                "{finding} jsonl prose_body is exactly 2000 characters; jsonl alone is not production-parity for truncated bodies, so commit a fixture_ballot"
            ));
        }
        let body = if body.lines().next().is_some_and(|line| line.trim().starts_with("**Rejected subtype:**")) {
            body.lines().skip_while(|line| !HEADING.is_match(line)).collect::<Vec<_>>().join("\n")
        } else {
            body
        };
        let body = strip_tally(&body);
        let block = ballot_block(&body, finding);
        if !block.is_empty() {
            return Ok(Some(block));
        }
        let title = python_str(record.get("category")).trim().to_owned();
        let title = if title.is_empty() {
            body.lines().find_map(|line| line.trim().strip_prefix("## ").map(str::trim)).unwrap_or(finding).to_owned()
        } else {
            title
        };
        let mut body = body.trim_matches('\n').to_owned();
        if body.lines().next().is_some_and(|line| {
            line.trim_start_matches('#')
                .trim()
                .trim_start_matches(finding)
                .trim_start_matches(':')
                .trim()
                .eq_ignore_ascii_case(&title)
        }) {
            body.lines().skip(1).collect::<Vec<_>>().join("\n").trim_matches('\n').clone_into(&mut body);
        }
        return Ok(Some(format!(
            "### {finding}: {title}{}\n",
            if body.trim().is_empty() { String::new() } else { format!("\n\n{}", body.trim()) }
        )));
    }
    Ok(None)
}

fn rebuild_ballot(repo: &Path, run_root: &Path, finding: &str, round: u64, fixture: Option<&Path>) -> Result<(String, &'static str), String> {
    if let Some(path) = fixture {
        return Ok((neutralize(&strip_tally(&safe_text(repo, path)?)), "fixture_ballot"));
    }
    let findings = run_root.join(format!("round-{round}/findings.md"));
    if findings.is_file() {
        let block = strip_tally(&ballot_block(&safe_text(repo, &findings)?, finding));
        if !block.trim().is_empty() {
            return Ok((neutralize(&block), "round_findings"));
        }
    }
    if let Some(block) = jsonl_ballot(repo, run_root, finding, round)? {
        return Ok((neutralize(&block), "review_findings_jsonl"));
    }
    Err(format!("no ballot source found for {finding} round {round} under {}", run_root.display()))
}

fn fixture_ballot(row: &Row, repo: &Path, finding: &str, field: &str) -> Result<Option<PathBuf>, String> {
    let Some(path) = relative_path(repo, cell(row, "fixture_ballot"), field, false)? else {
        return Ok(None);
    };
    if !path.is_file() {
        return Err(if field == "--fixture-ballot" { "--fixture-ballot is not readable".to_owned() } else { format!("fixture_ballot is not readable: {}", cell(row, "fixture_ballot")) });
    }
    require_under(&path, &repo.join(DEFAULT_BALLOTS), "fixture_ballot", DEFAULT_BALLOTS)?;
    let text = safe_text(repo, &path)?;
    if text.trim().is_empty() {
        return Err(format!("fixture_ballot is empty: {}", path.display()));
    }
    if text.lines().any(|line| line.trim().to_lowercase().starts_with("vote tally:")) {
        return Err(format!("fixture_ballot contains historical vote tally: {}", path.display()));
    }
    let ids: Vec<_> = text.lines().filter_map(|line| HEADING.captures(line).map(|captures| captures[1].to_owned())).collect();
    if ids.len() != 1 {
        return Err(format!("fixture_ballot must contain exactly one finding heading: {}", path.display()));
    }
    if ids[0] != finding {
        return Err(format!(
            "fixture_ballot heading {} does not match finding_id {}: {}",
            python_repr(&ids[0]),
            python_repr(finding),
            path.display()
        ));
    }
    Ok(Some(path))
}

fn classification_path(repo: &Path, run: &str, round: u64) -> PathBuf {
    repo.join(format!("larch-logs/implement/{run}/round-{round}/findings-classification.tsv"))
}

fn classification_row(repo: &Path, run: &str, round: u64, finding: &str) -> Result<Row, String> {
    let path = classification_path(repo, run, round);
    if !path.is_file() {
        return Err(format!("findings-classification.tsv not found for {finding}: {}", path.display()));
    }
    tsv_text_rows(&safe_text(repo, &path)?)?
        .into_iter()
        .find(|row| cell(row, "finding_id") == finding)
        .ok_or_else(|| format!("finding_id {finding} missing from {}", path.display()))
}

fn parse_vote(raw: &str, finding: &str, context: &Path) -> Result<String, String> {
    let vote = raw.trim().to_uppercase();
    if matches!(vote.as_str(), "YES" | "NO") {
        Ok(vote)
    } else {
        Err(format!("invalid v2_vote for {finding} in {}: {}", context.display(), python_repr(raw)))
    }
}

fn validate_row(row: &Row, repo: &Path) -> Result<(), String> {
    let finding = cell(row, "finding_id");
    if finding.is_empty() {
        return Err("finding_id is required".to_owned());
    }
    let run = cell(row, "run_id");
    let round_raw = cell(row, "round_num");
    let Some(round) = round_value(round_raw) else {
        return Err(format!("run_id and positive numeric round_num are required for {finding}"));
    };
    if run.is_empty() {
        return Err(format!("run_id and positive numeric round_num are required for {finding}"));
    }
    let run_root = repo.join(format!("larch-logs/implement/{run}"));
    assert_run(repo, &run_root, run)?;
    let plan = relative_path(repo, cell(row, "fixture_plan"), "fixture_plan", true)?.expect("required path");
    if !plan.is_file() {
        return Err(format!("fixture_plan is not readable: {}", plan.display()));
    }
    require_under(&plan, &repo.join(DEFAULT_PLANS), "fixture_plan", DEFAULT_PLANS)?;
    let plan_text = safe_text(repo, &plan)?;
    if plan_text.trim().is_empty() {
        return Err(format!("fixture_plan is empty: {}", plan.display()));
    }
    let first = plan_text.lines().find(|line| !line.trim().is_empty()).map_or("", str::trim);
    if POINTER.is_match(first) {
        return Err(format!("fixture_plan is pointer-only, not a replay fixture: {}", plan.display()));
    }
    if plan_text.lines().any(|line| matches!(line.trim(), "## Goal" | "## Implementation Plan" | "## Test plan")) {
        return Err(format!(
            "fixture_plan must be an extracted Implementation Plan body, not a full plan-goals document: {}",
            plan.display()
        ));
    }
    let diff_required = match cell(row, "diff_required").to_lowercase().as_str() {
        "true" => true,
        "false" => false,
        _ => return Err("diff_required must be true or false".to_owned()),
    };
    if !diff_required && !cell(row, "fixture_diff").is_empty() {
        return Err(format!("fixture_diff must be empty when diff_required=false for {finding}"));
    }
    let diff = relative_path(repo, cell(row, "fixture_diff"), "fixture_diff", diff_required)?;
    if diff_required {
        let Some(diff) = diff else {
            return Err(format!("fixture_diff is required and must be readable for {finding}"));
        };
        if !diff.is_file() {
            return Err(format!("fixture_diff is required and must be readable for {finding}"));
        }
        require_under(&diff, &repo.join(DEFAULT_DIFFS), "fixture_diff", DEFAULT_DIFFS)?;
        if safe_text(repo, &diff)?.trim().is_empty() {
            return Err(format!("fixture_diff is empty: {}", diff.display()));
        }
    }
    let fixture = fixture_ballot(row, repo, finding, "fixture_ballot")?;
    let classification = classification_row(repo, run, round, finding)?;
    parse_vote(classification.get("v2_vote").map_or("", String::as_str), finding, &classification_path(repo, run, round))?;
    rebuild_ballot(repo, &run_root, finding, round, fixture.as_deref())?;
    Ok(())
}

fn row_key(row: &Row) -> (String, String, String) {
    (cell(row, "finding_id").to_owned(), cell(row, "run_id").to_owned(), cell(row, "round_num").to_owned())
}

fn key_label(key: &(String, String, String)) -> String {
    format!("{}@{}/round-{}", key.0, key.1, key.2)
}

fn validate_binding(manifest: &[Row], cohort: &[Row]) -> Result<(), String> {
    if cohort.is_empty() {
        return Err("cohort denominator is empty".to_owned());
    }
    let counts = |rows: &[Row]| {
        rows.iter().fold(BTreeMap::new(), |mut out, row| {
            *out.entry(row_key(row)).or_insert(0_usize) += 1;
            out
        })
    };
    let manifest_counts = counts(manifest);
    let cohort_counts = counts(cohort);
    let duplicates: Vec<_> = manifest_counts
        .keys()
        .chain(cohort_counts.keys())
        .collect::<BTreeSet<_>>()
        .into_iter()
        .filter(|key| manifest_counts.get(*key).copied().unwrap_or(0) > 1 || cohort_counts.get(*key).copied().unwrap_or(0) > 1)
        .collect();
    if !duplicates.is_empty() {
        return Err(format!(
            "duplicate labeled cohort keys: {}",
            duplicates.into_iter().map(key_label).collect::<Vec<_>>().join(", ")
        ));
    }
    let manifest_keys: BTreeSet<_> = manifest_counts.keys().collect();
    let cohort_keys: BTreeSet<_> = cohort_counts.keys().collect();
    let missing: Vec<_> = cohort_keys.difference(&manifest_keys).copied().collect();
    if !missing.is_empty() {
        return Err(format!(
            "manifest is missing labeled cohort rows: {}",
            missing.into_iter().map(key_label).collect::<Vec<_>>().join(", ")
        ));
    }
    let extra: Vec<_> = manifest_keys.difference(&cohort_keys).copied().collect();
    if !extra.is_empty() {
        return Err(format!(
            "manifest has rows outside the labeled cohort: {}",
            extra.into_iter().map(key_label).collect::<Vec<_>>().join(", ")
        ));
    }
    for row in manifest {
        let key = row_key(row);
        let cohort_row = cohort.iter().find(|candidate| row_key(candidate) == key).expect("equal key sets");
        for field in ["v2_tool", "v1_tool"] {
            let expected = cell(cohort_row, field);
            let actual = cell(row, field);
            if !expected.is_empty() && actual != expected {
                return Err(format!(
                    "{} manifest {field}={} does not match cohort {field}={}",
                    key.0,
                    python_repr(actual),
                    python_repr(expected)
                ));
            }
        }
    }
    Ok(())
}

fn manifest_errors(manifest: &Path, cohort: &Path, repo: &Path) -> Result<(Vec<Row>, Vec<String>), String> {
    if !manifest.is_file() {
        return Ok((Vec::new(), vec![format!("manifest not found: {}", manifest.display())]));
    }
    let rows = tsv_rows(manifest)?;
    let mut errors = Vec::new();
    if rows.is_empty() {
        errors.push("manifest has no data rows".to_owned());
    }
    if let Err(error) = validate_binding(&rows, &tsv_rows(cohort)?) {
        errors.push(error);
    }
    for (index, row) in rows.iter().enumerate() {
        if let Err(error) = validate_row(row, repo) {
            errors.push(format!("row {}: {error}", index + 2));
        }
    }
    Ok((rows, errors))
}

fn forbidden_output(repo: &Path, path: &Path) -> bool {
    let resolved = |path: &Path| resolve_allow_missing(path).unwrap_or_else(|_| absolute_lexical(path));
    let path = resolved(path);
    [repo.join("larch-logs"), repo.join(FIXTURE_ROOT)].iter().any(|root| path.starts_with(resolved(root)))
}

fn write_replay_file(repo: &Path, path: &Path, text: &str) -> Result<(), String> {
    if forbidden_output(repo, path) {
        return Err("replay output must stay outside synchronized run logs and committed calibration fixtures".to_owned());
    }
    let path = absolute_lexical(path);
    let (root, target) = confined_target(&path).ok_or_else(|| "refusing unsafe replay output target".to_owned())?;
    if forbidden_output(repo, root.path()) { return Err("replay output must stay outside synchronized run logs and committed calibration fixtures".to_owned()); }
    atomic_write_utf8_in(&root, &target, text, true, 0o644).map_err(|error| error.to_string())
}

pub fn rebuild_ballot_command(arguments: &[OsString]) -> ExitCode {
    let parsed = match options(
        arguments,
        "calibration-replay rebuild-ballot",
        REBUILD_USAGE,
        &["--finding-id", "--run-root", "--round-num", "--fixture-ballot", "--repo-root", "--output"],
        &[],
        &["--finding-id", "--run-root", "--round-num"],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let Some(round) = round_value(&option(&parsed, "--round-num")) else {
        println!("REBUILD_STATUS=failed\nERROR=--round-num must be a positive integer");
        return ExitCode::from(2);
    };
    let repo = if option(&parsed, "--repo-root").is_empty() {
        env::current_dir().unwrap_or_else(|_| PathBuf::from("."))
    } else {
        PathBuf::from(option(&parsed, "--repo-root"))
    };
    let run_root = PathBuf::from(option(&parsed, "--run-root"));
    let finding = option(&parsed, "--finding-id");
    let result = (|| {
        let run = run_root.file_name().and_then(|name| name.to_str()).unwrap_or("");
        assert_run(&repo, &run_root, run)?;
        let fixture = if option(&parsed, "--fixture-ballot").is_empty() {
            None
        } else {
            let row = Row::from([("fixture_ballot".to_owned(), option(&parsed, "--fixture-ballot"))]);
            fixture_ballot(&row, &repo, &finding, "--fixture-ballot")?
        };
        let (ballot, source) = rebuild_ballot(&repo, &run_root, &finding, round, fixture.as_deref())?;
        let output = if option(&parsed, "--output").is_empty() {
            env::current_dir().unwrap_or_else(|_| PathBuf::from(".")).join("calibration-replay-ballot.txt")
        } else {
            PathBuf::from(option(&parsed, "--output"))
        };
        write_replay_file(&repo, &output, &ballot)?;
        Ok::<_, String>((source, output))
    })();
    match result {
        Ok((source, output)) => {
            println!("REBUILD_STATUS=ok\nBALLOT_SOURCE={source}\nBALLOT_PATH={}", output.display());
            ExitCode::SUCCESS
        }
        Err(error) => {
            println!("REBUILD_STATUS=failed\nERROR={error}");
            ExitCode::FAILURE
        }
    }
}

pub fn validate_manifest_command(arguments: &[OsString]) -> ExitCode {
    let parsed = match options(arguments, "calibration-replay validate-manifest", VALIDATE_USAGE, &["--manifest", "--cohort"], &[], &[]) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let manifest = PathBuf::from(if option(&parsed, "--manifest").is_empty() {
        DEFAULT_MANIFEST.to_owned()
    } else {
        option(&parsed, "--manifest")
    });
    let cohort = PathBuf::from(if option(&parsed, "--cohort").is_empty() {
        DEFAULT_COHORT.to_owned()
    } else {
        option(&parsed, "--cohort")
    });
    let repo = env::current_dir().unwrap_or_else(|_| PathBuf::from("."));
    let errors = manifest_errors(&manifest, &cohort, &repo).map_or_else(|error| vec![error], |(_, errors)| errors);
    if errors.is_empty() {
        println!("MANIFEST_STATUS=ok");
        ExitCode::SUCCESS
    } else {
        println!("MANIFEST_STATUS=failed");
        for error in errors {
            println!("ERROR={error}");
        }
        ExitCode::FAILURE
    }
}

fn ledger_row(finding: &str, block: &str, row: &Row, round: u64) -> LedgerRow {
    let first = block.lines().next().unwrap_or("").trim();
    let title = first
        .strip_prefix("###")
        .map(str::trim)
        .and_then(|line| line.strip_prefix(&format!("{finding}:")))
        .map(str::trim)
        .filter(|title| !title.is_empty())
        .unwrap_or(finding);
    let file_line = ["long-re", "short-path-re", "short-line-re", "extensionless-re", "any-re", "long-exts", "short-exts"]
        .into_iter()
        .filter_map(file_line_regex)
        .filter_map(|pattern| Regex::new(&pattern).ok())
        .find_map(|regex| {
            regex
                .find(block)
                .map(|value| value.as_str().trim_matches(|character: char| " \t\n\r`*()[],:;".contains(character)).to_owned())
        })
        .unwrap_or_default();
    let reason = block
        .lines()
        .skip(1)
        .find_map(|line| {
            let clean = line.replace('*', "");
            let (label, value) = clean.trim().split_once(':')?;
            ["concern", "scenario", "reason", "suggested revision", "suggested fix"]
                .contains(&label.trim_start_matches('-').trim().to_lowercase().as_str())
                .then(|| value.trim().to_owned())
        })
        .unwrap_or_default();
    let outcome = if cell(row, "scope").eq_ignore_ascii_case("oos") || finding.starts_with("OOS_") {
        "oos"
    } else {
        match cell(row, "voting_result").to_lowercase().as_str() {
            "accepted" => "accepted",
            "neutral" => "neutral",
            "oos" => "oos",
            _ => "rejected",
        }
    };
    let votes: Vec<_> = ["v1_vote", "v2_vote", "v3_vote"]
        .iter()
        .map(|key| cell(row, key).to_uppercase())
        .filter(|vote| matches!(vote.as_str(), "YES" | "NO"))
        .collect();
    let tally = if votes.is_empty() {
        String::new()
    } else {
        format!("YES={}/{}", votes.iter().filter(|vote| vote.as_str() == "YES").count(), votes.len())
    };
    LedgerRow::new(round, finding, title, &file_line, outcome, &tally, &reason)
}

fn seed_ledger(work: &Path, repo: &Path, run: &str, round: u64) -> Result<(), String> {
    for prior in 1..round {
        let path = classification_path(repo, run, prior);
        if !path.is_file() {
            return Err(format!("findings-classification.tsv not found for prior round {prior}: {}", path.display()));
        }
        let mut entries = Vec::new();
        for row in tsv_text_rows(&safe_text(repo, &path)?)? {
            let finding = cell(&row, "finding_id");
            if finding.is_empty() {
                continue;
            }
            let (block, _) = rebuild_ballot(repo, &repo.join(format!("larch-logs/implement/{run}")), finding, prior, None)?;
            entries.push(ledger_row(finding, &block, &row, prior));
        }
        write_round(work, prior, entries).map_err(|error| error.to_string())?;
    }
    Ok(())
}

fn resolve_voter_path(parent: &Path, raw: &str) -> Result<PathBuf, String> {
    if raw.trim().is_empty() {
        return Err("VOTER_2_PATH is empty".to_owned());
    }
    let path = Path::new(raw.trim());
    if path.is_absolute() || path.components().any(|part| part == Component::ParentDir) {
        return Err(format!("VOTER_2_PATH must stay under review tmpdir: {}", raw.trim()));
    }
    let resolved = fs::canonicalize(parent.join(path)).map_err(|_| format!("voter output missing: {}", parent.join(path).display()))?;
    let root = fs::canonicalize(parent).map_err(|error| error.to_string())?;
    if !resolved.starts_with(root) || !resolved.is_file() {
        return Err(format!("VOTER_2_PATH escapes review tmpdir: {}", raw.trim()));
    }
    Ok(resolved)
}

fn dispatch(row: &Row, ballot: &Path, plan: &Path, diff: Option<&Path>) -> Result<(String, String, String, String, String), String> {
    let finding = cell(row, "finding_id");
    let expected = cell(row, "v2_tool");
    let (codex, cursor) = match expected {
        "cursor-plan-fidelity" => ("false", "true"),
        "codex-plan-fidelity" => ("true", if cell(row, "v1_tool") == "claude" { "false" } else { "true" }),
        _ => return Err(format!("unsupported v2_tool for replay: {expected}")),
    };
    let mut arguments: Vec<OsString> = [
        "agent",
        "dispatch-voters",
        "--ballot-file",
        &ballot.display().to_string(),
        "--review-tmpdir",
        &ballot.parent().unwrap_or_else(|| Path::new(".")).display().to_string(),
        "--plan-file",
        &plan.display().to_string(),
        "--codex-available",
        codex,
        "--cursor-available",
        cursor,
        "--round-num",
        "1",
        "--site",
        "calibration-replay",
    ]
    .into_iter()
    .map(OsString::from)
    .collect();
    if let Some(diff) = diff {
        arguments.extend([OsString::from("--diff-file"), diff.as_os_str().to_owned()]);
    }
    let output = run_verified_larch_with_environment(&arguments, &[(ChildEnvironment::LarchVoterCalibrationFeedback, OsString::from("0"))])?;
    let combined = [String::from_utf8_lossy(output.stdout()), String::from_utf8_lossy(output.stderr())]
        .into_iter()
        .filter(|part| !part.is_empty())
        .collect::<Vec<_>>()
        .join("\n");
    if !output.status().success() {
        return Err(format!("dispatch-voters failed for {finding}: {}", combined.trim()));
    }
    let values = KvDocument::parse(&combined, ParseOptions::legacy())
        .map_err(|error| error.to_string())?
        .select(DuplicatePolicy::Last);
    let get = |key| values.get(key).map_or("", String::as_str).trim().to_owned();
    let status = get("VOTER_2_STATUS");
    let parse = get("VOTER_2_PARSE_RATE_STATUS");
    let tool = get("VOTER_2_TOOL");
    let path = get("VOTER_2_PATH");
    if status != "launched" {
        return Err(format!("dispatch-voters did not launch slot v2 for {finding}: VOTER_2_STATUS={status}"));
    }
    if parse != "OK" {
        return Err(format!("dispatch-voters parse guard failed for {finding}: VOTER_2_PARSE_RATE_STATUS={parse}"));
    }
    if tool.is_empty() {
        return Err(format!("missing VOTER_2_TOOL for {finding}"));
    }
    if tool != expected {
        return Err(format!("VOTER_2_TOOL mismatch for {finding}: expected {expected}, got {tool}"));
    }
    if path.is_empty() {
        return Err(format!("missing VOTER_2_PATH for {finding}"));
    }
    let expected_name = voter_output_name(expected).ok_or_else(|| format!("unsupported v2_tool for replay: {expected}"))?;
    if Path::new(&path).file_name().and_then(|name| name.to_str()) != Some(expected_name) {
        return Err(format!(
            "VOTER_2_PATH basename mismatch for {finding}: expected {expected_name}, got {}",
            Path::new(&path).file_name().unwrap_or_default().to_string_lossy()
        ));
    }
    let voter = resolve_voter_path(ballot.parent().unwrap_or_else(|| Path::new(".")), &path)?;
    let text = safe_text(ballot.parent().unwrap_or_else(|| Path::new(".")), &voter)?;
    if text.trim().is_empty() {
        return Err(format!("voter output empty: {}", voter.display()));
    }
    let vote = parse_judge_vote_text(finding, &text, "").vote.to_uppercase();
    if !matches!(vote.as_str(), "YES" | "NO") {
        return Err(format!("unparseable vote for {finding} in {}: {}", voter.display(), python_repr(&vote)));
    }
    Ok((vote, path, status, tool, parse))
}

#[derive(Default)]
struct ReplayResult {
    finding: String,
    run: String,
    round: u64,
    source: String,
    before: String,
    tool: String,
    plan: String,
    diff: String,
    after: String,
    voter_path: String,
    voter_status: String,
    voter_tool: String,
    parse_status: String,
}

fn yes_rate(rows: &[ReplayResult], after: bool) -> String {
    let votes: Vec<_> = rows
        .iter()
        .map(|row| if after { &row.after } else { &row.before })
        .filter(|vote| !vote.is_empty())
        .collect();
    format!("{}/{}", votes.iter().filter(|vote| vote.as_str() == "YES").count(), votes.len())
}

#[allow(clippy::too_many_lines)]
pub fn run_replay_command(arguments: &[OsString]) -> ExitCode {
    let parsed = match options(
        arguments,
        "calibration-replay run-replay",
        REPLAY_USAGE,
        &["--manifest", "--cohort", "--work-dir"],
        &["--dry-run"],
        &["--work-dir"],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let repo = env::current_dir().unwrap_or_else(|_| PathBuf::from("."));
    let manifest = PathBuf::from(if option(&parsed, "--manifest").is_empty() {
        DEFAULT_MANIFEST.to_owned()
    } else {
        option(&parsed, "--manifest")
    });
    let cohort = PathBuf::from(if option(&parsed, "--cohort").is_empty() {
        DEFAULT_COHORT.to_owned()
    } else {
        option(&parsed, "--cohort")
    });
    let work = absolute_lexical(Path::new(&option(&parsed, "--work-dir")));
    let dry = parsed.flag("--dry-run");
    let run = (|| {
        let (rows, errors) = manifest_errors(&manifest, &cohort, &repo)?;
        if !errors.is_empty() {
            return Err(errors.join("; "));
        }
        if forbidden_output(&repo, &work) {
            return Err("replay output must stay outside synchronized run logs and committed calibration fixtures".to_owned());
        }
        ensure_directory_chain(&work).map_err(|error| error.to_string())?;
        let work_root = TemporaryRoot::resolve(Some(&work)).map_err(|error| error.to_string())?;
        if forbidden_output(&repo, work_root.path()) { return Err("replay output must stay outside synchronized run logs and committed calibration fixtures".to_owned()); }
        let mut results = Vec::new();
        for row in rows {
            let finding = cell(&row, "finding_id").to_owned();
            let run = cell(&row, "run_id").to_owned();
            let round = round_value(cell(&row, "round_num")).expect("validated round");
            let fixture = fixture_ballot(&row, &repo, &finding, "fixture_ballot")?;
            let (ballot, source) = rebuild_ballot(&repo, &repo.join(format!("larch-logs/implement/{run}")), &finding, round, fixture.as_deref())?;
            let row_dir = work.join(format!("{run}_{finding}"));
            work_root.ensure_directory(&row_dir).map_err(|error| error.to_string())?;
            let ballot_path = row_dir.join("ballot.txt");
            atomic_write_utf8_in(&work_root, &ballot_path, &ballot, true, 0o644).map_err(|error| error.to_string())?;
            let plan = relative_path(&repo, cell(&row, "fixture_plan"), "fixture_plan", true)?.expect("validated plan");
            let diff = relative_path(&repo, cell(&row, "fixture_diff"), "fixture_diff", false)?;
            let classification = classification_row(&repo, &run, round, &finding)?;
            let before = parse_vote(classification.get("v2_vote").map_or("", String::as_str), &finding, &classification_path(&repo, &run, round))?;
            let mut result = ReplayResult {
                finding,
                run,
                round,
                source: source.to_owned(),
                before,
                tool: cell(&row, "v2_tool").to_owned(),
                plan: plan.strip_prefix(&repo).unwrap_or(&plan).display().to_string(),
                diff: diff
                    .as_ref()
                    .map_or_else(String::new, |path| path.strip_prefix(&repo).unwrap_or(path).display().to_string()),
                ..ReplayResult::default()
            };
            if !dry {
                seed_ledger(&row_dir, &repo, &result.run, round)?;
                (result.after, result.voter_path, result.voter_status, result.voter_tool, result.parse_status) = dispatch(&row, &ballot_path, &plan, diff.as_deref())?;
            }
            results.push(result);
        }
        Ok::<_, String>(results)
    })();
    let results = match run {
        Ok(results) => results,
        Err(error) => {
            println!("REPLAY_STATUS=failed\nERROR={error}");
            return ExitCode::FAILURE;
        }
    };
    println!("REPLAY_STATUS=ok\nROW_COUNT={}\nYES_RATE_BEFORE={}", results.len(), yes_rate(&results, false));
    if !dry {
        println!("YES_RATE_AFTER={}", yes_rate(&results, true));
    }
    for (index, row) in results.iter().enumerate() {
        let n = index + 1;
        println!(
            "ROW_{n}_FINDING_ID={}\nROW_{n}_RUN_ID={}\nROW_{n}_ROUND_NUM={}\nROW_{n}_BALLOT_SOURCE={}\nROW_{n}_BEFORE_VOTE={}",
            row.finding, row.run, row.round, row.source, row.before
        );
        if !row.after.is_empty() {
            println!("ROW_{n}_AFTER_VOTE={}", row.after);
        }
        println!("ROW_{n}_V2_TOOL={}\nROW_{n}_FIXTURE_PLAN={}", row.tool, row.plan);
        if !row.diff.is_empty() {
            println!("ROW_{n}_FIXTURE_DIFF={}", row.diff);
        }
        if !row.voter_path.is_empty() {
            println!(
                "ROW_{n}_VOTER_2_PATH={}\nROW_{n}_VOTER_2_STATUS={}\nROW_{n}_VOTER_2_TOOL={}\nROW_{n}_VOTER_2_PARSE_RATE_STATUS={}",
                row.voter_path, row.voter_status, row.voter_tool, row.parse_status
            );
        }
    }
    ExitCode::SUCCESS
}

}

pub use implementation::{
    positive_window, rebuild_ballot_command, run_replay_command, validate_manifest_command,
    voter_calibration_snapshot, write_calibration_snapshot,
};
