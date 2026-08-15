//! Rust owners for code-review vote tallying, tally emission, and phase logging.
//!
//! These commands retain the line-oriented artifacts consumed by the remaining
//! Python review orchestrator.  The command boundary deliberately owns all
//! tally persistence so the Python side is only a verified-bootstrap consumer.

use std::{
    collections::{BTreeMap, BTreeSet, HashMap, HashSet},
    env,
    ffi::OsString,
    fmt::Write as _,
    fs,
    path::{Path, PathBuf},
    process::ExitCode,
    sync::LazyLock,
};

use indexmap::IndexMap;
use larch_adapters::phase_detail;
use larch_core::{
    BlockBoundary, DuplicatePolicy, EmptyKeyPolicy, KvDocument, ParseOptions,
    is_security_block_text, normalize_oos_block_header, parse_oos_blocks,
    review::{
        ItemContext, LedgerRow, VoteCell, alias_ballot_id, code_review_classification_header,
        ledger_root, normalize_output_base, parse_judge_vote_text, reviewer_for_block_text,
        run_items, write_round,
    },
    serialize_accepted_oos,
};
use regex::Regex;
use serde_json::{Map, Value, json};
use sha2::{Digest as _, Sha256};
use tempfile::Builder;

use crate::{
    argparse_compat::split_inline_option,
    claude_commands::parse_uint,
    launcher_support::{append_confined_checked, write_confined_checked},
    runtime_entrypoint::run_verified_larch,
};

const THREE_SLOT_COUNT: usize = 3;
const MIN_DEGRADABLE_PANEL: usize = 2;
const OOS_AGGREGATE_POOL: &str = "oos-aggregate-pool.md";
const TALLY_USAGE: &str = "usage: tally-code-votes [-h] --ballot-file BALLOT_FILE --review-tmpdir REVIEW_TMPDIR [--session-env-path SESSION_ENV_PATH] [--scope-files SCOPE_FILES] [--plan-file PLAN_FILE] [--manifest-file MANIFEST_FILE] [--collector-results-file COLLECTOR_RESULTS_FILE] [--not-substantive-count NOT_SUBSTANTIVE_COUNT] [--cursor-available CURSOR_AVAILABLE] [--codex-available CODEX_AVAILABLE] [--round-num ROUND_NUM] [--both-down BOTH_DOWN] [--proposer-map-file PROPOSER_MAP_FILE] [--voter-files [VOTER_FILES ...]] [--voter-tools [VOTER_TOOLS ...]]";
const EMIT_USAGE: &str = "usage: emit-tally [-h] --tally-file TALLY_FILE --accepted-findings-file ACCEPTED_FINDINGS_FILE --oos-file OOS_FILE --review-tmpdir REVIEW_TMPDIR [--session-env-path SESSION_ENV_PATH] [--round ROUND] --mode {diff,description} [--implement-tmpdir IMPLEMENT_TMPDIR] [--scout-status SCOUT_STATUS] [--dynamic-slots DYNAMIC_SLOTS] [--static-slot-count STATIC_SLOT_COUNT]";
const LOG_PHASE_USAGE: &str = "usage: log-phase [-h] --run-id RUN_ID --batch BATCH --action {write,append} --payload-file PAYLOAD_FILE [--log-root LOG_ROOT]";

static LEDGER_REASON_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?i)^[- ]*(Concern|Scenario|Reason|Suggested (revision|fix)):\s*")
        .expect("ledger reason regex")
});
static DEAD_ROW_LABEL_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"(?:-output)?\.txt$").expect("dead-row label regex"));
static SPECIALIST_OUTPUT_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^(cursor|codex)-specialist-.+-output\.txt$").expect("specialist regex")
});
static SCORE_LABEL_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"(?:-output)?\.txt$").expect("score label regex"));

#[derive(Clone, Debug)]
struct TallyRequest {
    ballot_file: PathBuf,
    review_tmpdir: PathBuf,
    voter_files: Vec<String>,
    voter_tools: Vec<String>,
    session_env_path: String,
    scope_files: String,
    plan_file: String,
    manifest_file: String,
    collector_results_file: String,
    not_substantive_count: String,
    cursor_available: String,
    codex_available: String,
    round_num: String,
    both_down: String,
    proposer_map_file: String,
}

#[derive(Clone, Debug)]
struct TallyResult {
    rc: u8,
    status: String,
    accepted_count: usize,
    rejected_count: usize,
    exonerated_count: usize,
    neutral_count: usize,
    oos_accepted_count: usize,
    oos_rejected_count: usize,
    out_of_scope_drift_count: usize,
    voting_tally_file: Option<PathBuf>,
    tally_file: Option<PathBuf>,
    accepted_findings_file: Option<PathBuf>,
    rejected_findings_file: Option<PathBuf>,
    oos_accepted_file: Option<PathBuf>,
    oos_file: Option<PathBuf>,
    eligible_voter_count: usize,
    voter_count: usize,
    parse_failed_count: usize,
    findings_classification_tsv_file: Option<PathBuf>,
    under_quorum_items: Vec<String>,
    voting_skipped_warning: String,
    yield_tsv_file: Option<PathBuf>,
    warnings: Vec<String>,
    error: String,
}

impl TallyResult {
    fn failure(message: impl Into<String>) -> Self {
        Self {
            rc: 2,
            status: String::new(),
            accepted_count: 0,
            rejected_count: 0,
            exonerated_count: 0,
            neutral_count: 0,
            oos_accepted_count: 0,
            oos_rejected_count: 0,
            out_of_scope_drift_count: 0,
            voting_tally_file: None,
            tally_file: None,
            accepted_findings_file: None,
            rejected_findings_file: None,
            oos_accepted_file: None,
            oos_file: None,
            eligible_voter_count: 0,
            voter_count: 0,
            parse_failed_count: 0,
            findings_classification_tsv_file: None,
            under_quorum_items: Vec::new(),
            voting_skipped_warning: String::new(),
            yield_tsv_file: None,
            warnings: Vec::new(),
            error: message.into(),
        }
    }

    fn emit(&self) {
        if !self.error.is_empty() {
            eprintln!("{}", self.error);
            return;
        }
        for warning in &self.warnings {
            println!("WARN={warning}");
        }
        for (key, value) in [
            ("TALLY_STATUS", self.status.clone()),
            ("ACCEPTED_COUNT", self.accepted_count.to_string()),
            ("REJECTED_COUNT", self.rejected_count.to_string()),
            ("EXONERATED_COUNT", self.exonerated_count.to_string()),
            ("NEUTRAL_COUNT", self.neutral_count.to_string()),
            ("OOS_ACCEPTED_COUNT", self.oos_accepted_count.to_string()),
            ("OOS_REJECTED_COUNT", self.oos_rejected_count.to_string()),
            (
                "OUT_OF_SCOPE_DRIFT_COUNT",
                self.out_of_scope_drift_count.to_string(),
            ),
        ] {
            println!("{key}={value}");
        }
        for (key, path) in [
            ("VOTING_TALLY_FILE", self.voting_tally_file.as_ref()),
            ("TALLY_FILE", self.tally_file.as_ref()),
            (
                "ACCEPTED_FINDINGS_FILE",
                self.accepted_findings_file.as_ref(),
            ),
            (
                "REJECTED_FINDINGS_FILE",
                self.rejected_findings_file.as_ref(),
            ),
            ("OOS_ACCEPTED_FILE", self.oos_accepted_file.as_ref()),
            ("OOS_FILE", self.oos_file.as_ref()),
        ] {
            if let Some(path) = path {
                println!("{key}={}", path.display());
            }
        }
        println!("TALLY_OK=true");
        println!("ELIGIBLE_VOTER_COUNT={}", self.eligible_voter_count);
        println!("VOTER_COUNT={}", self.voter_count);
        if self.status == "ok" {
            println!("UNDER_QUORUM_COUNT={}", self.under_quorum_items.len());
            println!("UNDER_QUORUM_ITEMS={}", self.under_quorum_items.join(", "));
        }
        println!("PARSE_FAILED_COUNT={}", self.parse_failed_count);
        if !self.voting_skipped_warning.is_empty() {
            println!("VOTING_SKIPPED_WARNING={}", self.voting_skipped_warning);
        }
        if let Some(path) = &self.findings_classification_tsv_file {
            println!("FINDINGS_CLASSIFICATION_TSV_FILE={}", path.display());
        }
        if let Some(path) = &self.yield_tsv_file {
            println!("YIELD_TSV_FILE={}", path.display());
        }
    }
}

#[derive(Default)]
struct ParsedOptions {
    values: HashMap<String, String>,
    lists: HashMap<String, Vec<String>>,
}

fn parse_options(
    arguments: &[OsString],
    program: &str,
    usage: &str,
    known: &[&str],
    list_options: &[&str],
) -> Result<ParsedOptions, ExitCode> {
    let values = arguments
        .iter()
        .map(|argument| argument.to_string_lossy().into_owned())
        .collect::<Vec<_>>();
    if values
        .iter()
        .any(|value| value == "-h" || value == "--help")
    {
        println!("{usage}\n\noptions:\n  -h, --help            show this help message and exit");
        return Err(ExitCode::SUCCESS);
    }
    let mut parsed = ParsedOptions::default();
    let mut index = 0;
    while index < values.len() {
        let raw = &values[index];
        let (option, inline) = split_inline_option(raw);
        if !known.contains(&option) && !list_options.contains(&option) {
            eprintln!("{usage}\n{program}: error: unrecognized arguments: {raw}");
            return Err(ExitCode::from(2));
        }
        if list_options.contains(&option) {
            let mut items = Vec::new();
            if let Some(value) = inline {
                if !value.is_empty() {
                    items.push(value.to_owned());
                }
                index += 1;
            } else {
                index += 1;
                while index < values.len() && !values[index].starts_with("--") {
                    items.push(values[index].clone());
                    index += 1;
                }
            }
            parsed
                .lists
                .entry(option.to_owned())
                .or_default()
                .extend(items);
            continue;
        }
        let value = if let Some(value) = inline {
            index += 1;
            value.to_owned()
        } else {
            let Some(value) = values.get(index + 1) else {
                eprintln!("{usage}\n{program}: error: argument {option}: expected one argument");
                return Err(ExitCode::from(2));
            };
            if value.starts_with("--") {
                eprintln!("{usage}\n{program}: error: argument {option}: expected one argument");
                return Err(ExitCode::from(2));
            }
            index += 2;
            value.clone()
        };
        parsed.values.insert(option.to_owned(), value);
    }
    Ok(parsed)
}

fn required(
    parsed: &ParsedOptions,
    option: &str,
    usage: &str,
    program: &str,
) -> Result<String, ExitCode> {
    parsed.values.get(option).cloned().ok_or_else(|| {
        eprintln!("{usage}\n{program}: error: the following arguments are required: {option}");
        ExitCode::from(2)
    })
}

fn require_all(
    parsed: &ParsedOptions,
    options: &[&str],
    usage: &str,
    program: &str,
) -> Result<(), ExitCode> {
    let missing = options
        .iter()
        .filter(|option| !parsed.values.contains_key(**option))
        .copied()
        .collect::<Vec<_>>();
    if missing.is_empty() {
        return Ok(());
    }
    eprintln!(
        "{usage}\n{program}: error: the following arguments are required: {}",
        missing.join(", ")
    );
    Err(ExitCode::from(2))
}

fn write_text(path: &Path, text: &str) -> Result<(), String> {
    write_confined_checked(path, text)
}

fn read_text(path: &Path) -> Result<String, String> {
    fs::read(path)
        .map_err(|error| error.to_string())
        .map(|bytes| String::from_utf8_lossy(&bytes).into_owned())
}

fn append_text(path: &Path, text: &str) -> Result<(), String> {
    append_confined_checked(path, text)
}

fn is_regular_nonempty(path: &Path) -> bool {
    path.metadata()
        .is_ok_and(|metadata| metadata.is_file() && metadata.len() > 0)
}

fn parse_kv(text: &str) -> BTreeMap<String, String> {
    KvDocument::parse(
        text,
        ParseOptions {
            empty_keys: EmptyKeyPolicy::Skip,
            ..ParseOptions::legacy()
        },
    )
    .map(|document| document.select(DuplicatePolicy::First))
    .unwrap_or_default()
}

fn parse_nonnegative(value: &str) -> usize {
    parse_ascii_decimal(value).unwrap_or(0)
}

fn parse_ascii_decimal(value: &str) -> Option<usize> {
    parse_uint(value).and_then(|parsed| parsed.try_into().ok())
}

fn parse_positive_round(value: &str) -> Option<u64> {
    parse_uint(value).filter(|round| *round > 0)
}

#[allow(clippy::too_many_lines)] // Frozen argparse-compatible options remain adjacent for auditability.
fn tally_request(arguments: &[OsString]) -> Result<TallyRequest, ExitCode> {
    const KNOWN: &[&str] = &[
        "--ballot-file",
        "--review-tmpdir",
        "--session-env-path",
        "--scope-files",
        "--plan-file",
        "--manifest-file",
        "--collector-results-file",
        "--not-substantive-count",
        "--cursor-available",
        "--codex-available",
        "--round-num",
        "--both-down",
        "--proposer-map-file",
    ];
    let parsed = parse_options(
        arguments,
        "tally-code-votes",
        TALLY_USAGE,
        KNOWN,
        &["--voter-files", "--voter-tools"],
    )?;
    require_all(
        &parsed,
        &["--ballot-file", "--review-tmpdir"],
        TALLY_USAGE,
        "tally-code-votes",
    )?;
    Ok(TallyRequest {
        ballot_file: PathBuf::from(required(
            &parsed,
            "--ballot-file",
            TALLY_USAGE,
            "tally-code-votes",
        )?),
        review_tmpdir: PathBuf::from(required(
            &parsed,
            "--review-tmpdir",
            TALLY_USAGE,
            "tally-code-votes",
        )?),
        voter_files: parsed
            .lists
            .get("--voter-files")
            .cloned()
            .unwrap_or_default(),
        voter_tools: parsed
            .lists
            .get("--voter-tools")
            .cloned()
            .unwrap_or_default(),
        session_env_path: parsed
            .values
            .get("--session-env-path")
            .cloned()
            .unwrap_or_default(),
        scope_files: parsed
            .values
            .get("--scope-files")
            .cloned()
            .unwrap_or_default(),
        plan_file: parsed
            .values
            .get("--plan-file")
            .cloned()
            .unwrap_or_default(),
        manifest_file: parsed
            .values
            .get("--manifest-file")
            .cloned()
            .unwrap_or_default(),
        collector_results_file: parsed
            .values
            .get("--collector-results-file")
            .cloned()
            .unwrap_or_default(),
        not_substantive_count: parsed
            .values
            .get("--not-substantive-count")
            .cloned()
            .unwrap_or_else(|| "0".to_owned()),
        cursor_available: parsed
            .values
            .get("--cursor-available")
            .cloned()
            .unwrap_or_default(),
        codex_available: parsed
            .values
            .get("--codex-available")
            .cloned()
            .unwrap_or_default(),
        round_num: parsed
            .values
            .get("--round-num")
            .cloned()
            .unwrap_or_else(|| "1".to_owned()),
        both_down: parsed
            .values
            .get("--both-down")
            .cloned()
            .unwrap_or_else(|| "false".to_owned()),
        proposer_map_file: parsed
            .values
            .get("--proposer-map-file")
            .cloned()
            .unwrap_or_default(),
    })
}

#[derive(Clone, Debug, Default)]
struct ProposerMap {
    entries: BTreeMap<String, (String, String)>,
}

fn reviewer_pattern() -> Regex {
    Regex::new(
        r"^(?P<prefix>[\s-]*(?:\*\*Reviewer\(s\)\*\*|\*\*Reviewers?\*\*|Reviewer\(s\)|Reviewers?)\s*:\s*)(?P<value>.*?)(?P<trailing>[ \t]*)$",
    )
    .expect("reviewer attribution regex")
}

fn reviewer_is_neutral(reviewer: &str) -> bool {
    reviewer.trim().eq_ignore_ascii_case("anonymous")
}

fn ballot_is_neutralized(text: &str) -> bool {
    let pattern = reviewer_pattern();
    for block in parse_oos_blocks(text, BlockBoundary::ItemHeading) {
        for line in block.block.lines() {
            if let Some(captures) = pattern.captures(line) {
                return reviewer_is_neutral(
                    captures
                        .name("value")
                        .map_or("", |value| value.as_str())
                        .replace('*', "")
                        .trim(),
                );
            }
        }
    }
    false
}

fn read_proposer_map(path: &Path) -> ProposerMap {
    let Ok(text) = read_text(path) else {
        return ProposerMap::default();
    };
    let heading = Regex::new(r"^### (?:FINDING|OOS)_[0-9]+:").expect("proposer item regex");
    let mut entries = BTreeMap::new();
    for row in text.lines() {
        let values = row.split('\t').collect::<Vec<_>>();
        if values.len() != 3 {
            continue;
        }
        let item = values[0].trim();
        let reviewer = values[1].trim();
        let reviewer_line = values[2].trim();
        if heading.is_match(&format!("### {item}:"))
            && !reviewer.is_empty()
            && !reviewer_line.is_empty()
        {
            entries.insert(
                item.to_owned(),
                (reviewer.to_owned(), reviewer_line.to_owned()),
            );
        }
    }
    ProposerMap { entries }
}

fn sha256_hex(text: &str) -> String {
    format!("{:x}", Sha256::digest(text.as_bytes()))
}

fn validate_proposer_map_for_neutralized_ballot(
    ballot_path: &Path,
    ballot_text: &str,
    map_path: &Path,
) -> Result<ProposerMap, String> {
    if !map_path.is_file() {
        return Err(format!("proposer map file missing: {}", map_path.display()));
    }
    let rows = read_text(map_path)
        .map_err(|_| format!("proposer map unreadable: {}", map_path.display()))?;
    let neutral_stamp = rows
        .lines()
        .find_map(|line| line.strip_prefix("# neutral_ballot_sha256="))
        .map(str::trim)
        .unwrap_or_default();
    if neutral_stamp.is_empty() {
        return Err("proposer map missing neutral_ballot_sha256 stamp".to_owned());
    }
    if sha256_hex(ballot_text) != neutral_stamp {
        return Err("proposer map stale for current ballot".to_owned());
    }
    let proposer_map = read_proposer_map(map_path);
    let ballot_ids = parse_oos_blocks(ballot_text, BlockBoundary::ItemHeading)
        .into_iter()
        .map(|block| block.item_id)
        .collect::<BTreeSet<_>>();
    let map_ids = proposer_map
        .entries
        .keys()
        .cloned()
        .collect::<BTreeSet<_>>();
    if ballot_ids != map_ids {
        let missing = ballot_ids.difference(&map_ids).cloned().collect::<Vec<_>>();
        let extra = map_ids.difference(&ballot_ids).cloned().collect::<Vec<_>>();
        let mut details = Vec::new();
        if !missing.is_empty() {
            details.push(format!("missing item(s): {}", missing.join(", ")));
        }
        if !extra.is_empty() {
            details.push(format!("extra item(s): {}", extra.join(", ")));
        }
        return Err(format!(
            "proposer map item mismatch ({})",
            details.join("; ")
        ));
    }
    for (item, (reviewer, _line)) in &proposer_map.entries {
        if reviewer.trim().is_empty() || reviewer_is_neutral(reviewer) {
            return Err(format!(
                "proposer map has neutral or empty reviewer for {item}"
            ));
        }
    }
    let _ = ballot_path;
    Ok(proposer_map)
}

fn resolved_proposer_map(
    request: &TallyRequest,
    ballot_text: &str,
) -> Result<(ProposerMap, bool), String> {
    let neutralized = ballot_is_neutralized(ballot_text);
    let default_map = request.review_tmpdir.join("proposer-map.tsv");
    let map_path = if request.proposer_map_file.is_empty() {
        (default_map.is_file() && neutralized).then_some(default_map)
    } else {
        Some(PathBuf::from(&request.proposer_map_file))
    };
    let required = map_path.is_some() || neutralized;
    let map = if let Some(path) = map_path {
        if neutralized {
            validate_proposer_map_for_neutralized_ballot(&request.ballot_file, ballot_text, &path)?
        } else {
            read_proposer_map(&path)
        }
    } else {
        ProposerMap::default()
    };
    Ok((map, required))
}

fn proposer_for_item(
    item_id: &str,
    block_text: &str,
    proposer_map: &ProposerMap,
    sidecar_required: bool,
) -> Result<String, String> {
    let reviewer = reviewer_for_block_text(block_text);
    if !reviewer_is_neutral(&reviewer) {
        return Ok(reviewer);
    }
    if sidecar_required || !proposer_map.entries.is_empty() {
        if let Some((reviewer, _line)) = proposer_map.entries.get(item_id)
            && !reviewer.trim().is_empty()
            && !reviewer_is_neutral(reviewer)
        {
            return Ok(reviewer.clone());
        }
        return Err(format!(
            "missing proposer map entry for neutralized item {item_id}"
        ));
    }
    Ok(reviewer)
}

fn restore_reviewer_attribution(block_text: &str, reviewer_line: &str) -> String {
    if reviewer_line.is_empty() {
        return block_text.to_owned();
    }
    let pattern = reviewer_pattern();
    let mut output = String::new();
    let mut replaced = false;
    for segment in block_text.split_inclusive('\n') {
        let line = segment.strip_suffix('\n').unwrap_or(segment);
        if !replaced && let Some(captures) = pattern.captures(line) {
            let value = captures
                .name("value")
                .map_or("", |value| value.as_str())
                .replace('*', "");
            if reviewer_is_neutral(value.trim()) {
                output.push_str(reviewer_line);
                if segment.ends_with('\n') {
                    output.push('\n');
                }
                replaced = true;
                continue;
            }
            return block_text.to_owned();
        }
        output.push_str(segment);
    }
    if replaced {
        return output;
    }
    if let Some(index) = block_text.find('\n') {
        let mut output = String::with_capacity(block_text.len() + reviewer_line.len() + 2);
        output.push_str(&block_text[..=index]);
        output.push_str(reviewer_line);
        output.push('\n');
        output.push_str(&block_text[index + 1..]);
        return output;
    }
    format!("{block_text}\n{reviewer_line}\n")
}

fn ledger_entry(
    item_id: &str,
    block_text: &str,
    outcome: &str,
    vote_tally: &str,
    round: u64,
) -> LedgerRow {
    let first = block_text.lines().next().unwrap_or_default();
    let title_prefix = format!("### {item_id}:");
    let title = first
        .strip_prefix(&title_prefix)
        .map(str::trim)
        .filter(|title| !title.is_empty())
        .unwrap_or(item_id);
    let file_line = [
        "long-re",
        "short-path-re",
        "short-line-re",
        "extensionless-re",
        "any-re",
    ]
    .into_iter()
    .find_map(|name| {
        larch_core::file_line_regex(name)
            .and_then(|source| Regex::new(&source).ok())
            .and_then(|regex| {
                regex.find(block_text).map(|found| {
                    found
                        .as_str()
                        .trim_matches(|character: char| " \t\n\r`*()[],:;".contains(character))
                        .to_owned()
                })
            })
    })
    .unwrap_or_default();
    let reason = block_text
        .lines()
        .skip(1)
        .find_map(|line| {
            let normalized = line.replace('*', "");
            let trimmed = normalized.trim();
            LEDGER_REASON_RE
                .find(trimmed)
                .map(|matched| trimmed[matched.end()..].trim().to_owned())
        })
        .unwrap_or_default();
    LedgerRow::new(
        round, item_id, title, &file_line, outcome, vote_tally, &reason,
    )
}

fn sanitize_cell(value: &str) -> String {
    let pipe = Regex::new(r"\s*\|\s*").expect("classification pipe regex");
    let mut output = value.replace(['\t', '\r', '\n'], " ");
    output = pipe.replace_all(&output, "|").into_owned();
    if output.starts_with(['=', '+', '-', '@']) {
        output.insert(0, '\'');
    }
    output
}

fn sanitized_vote(value: &str) -> String {
    if ["YES", "NO", "JUDGE_ERROR"].contains(&value) {
        value.to_owned()
    } else {
        String::new()
    }
}

fn sanitized_one_of(value: &str, values: &[&str]) -> String {
    if values.contains(&value) {
        value.to_owned()
    } else {
        String::new()
    }
}

fn classification_row(
    item_id: &str,
    reviewer: &str,
    result: &str,
    cells: &[VoteCell],
    three_slot: bool,
    is_oos: bool,
) -> String {
    let mut values = vec![
        item_id.to_owned(),
        sanitize_cell(
            &reviewer
                .split(',')
                .map(str::trim)
                .filter(|part| !part.is_empty())
                .collect::<Vec<_>>()
                .join("|"),
        ),
        sanitized_one_of(result, &["accepted", "rejected", "neutral"]),
    ];
    for index in 0..THREE_SLOT_COUNT {
        let (vote, correctness, severity, quality, uncertain, tool) =
            cells.get(index).cloned().unwrap_or_default();
        let has_rating = !vote.is_empty()
            || !correctness.is_empty()
            || !severity.is_empty()
            || !quality.is_empty()
            || !uncertain.is_empty();
        if three_slot && !has_rating {
            values.extend([
                String::new(),
                String::new(),
                String::new(),
                String::new(),
                String::new(),
                sanitize_cell(tool.as_deref().unwrap_or_default()),
            ]);
            continue;
        }
        let vote = if has_rating {
            sanitized_vote(if vote.is_empty() {
                "JUDGE_ERROR"
            } else {
                &vote
            })
        } else {
            String::new()
        };
        let correctness = sanitized_one_of(
            &correctness,
            &["true", "partially-true", "false-positive", "uncertain"],
        );
        let severity = sanitized_one_of(&severity, &["major", "minor", "nit"]);
        let quality = sanitized_one_of(
            &quality,
            &[
                "excellent",
                "good",
                "adequate",
                "weak",
                "no-fix",
                "uncertain",
            ],
        );
        let uncertain = if has_rating
            && (correctness.is_empty() || severity.is_empty() || quality.is_empty())
        {
            "true".to_owned()
        } else if has_rating {
            sanitized_one_of(&uncertain, &["true", "false"])
        } else {
            String::new()
        };
        values.extend([vote, correctness, severity, quality, uncertain]);
        if three_slot {
            values.push(sanitize_cell(tool.as_deref().unwrap_or_default()));
        }
    }
    values.push(if is_oos { "oos" } else { "in_scope" }.to_owned());
    values.join("\t")
}

fn scope_drift(block_text: &str, scope_files: &str, plan_file: &str) -> bool {
    let scope_path = Path::new(scope_files);
    if scope_files.is_empty() || !is_regular_nonempty(scope_path) {
        return false;
    }
    let heading = block_text
        .lines()
        .next()
        .unwrap_or_default()
        .replace(['`', '*', '_'], "");
    let path_re = Regex::new(r"[a-zA-Z0-9_./-]+\.[a-zA-Z0-9]+:[0-9]+").expect("scope path regex");
    let line_re = Regex::new(r":[0-9]+$").expect("scope line regex");
    let paths = path_re
        .find_iter(&heading)
        .map(|found| line_re.replace(found.as_str(), "").into_owned())
        .collect::<Vec<_>>();
    if paths.is_empty() {
        return false;
    }
    let scope = read_text(scope_path).unwrap_or_default();
    let plan = if !plan_file.is_empty() && Path::new(plan_file).is_file() {
        read_text(Path::new(plan_file)).unwrap_or_default()
    } else {
        String::new()
    };
    paths
        .iter()
        .all(|path| !scope.lines().any(|line| line == path) && !plan.contains(path))
}

fn static_focus_area(slug: &str) -> &'static str {
    match slug {
        "correctness" | "edge-cases" => "correctness",
        "testing" => "risk-integration",
        "security" => "security",
        "plan-fidelity" | "plan-fidelity-forced" => "architecture",
        _ => "code-quality",
    }
}

#[derive(Clone, Debug)]
struct VoterObservation {
    panel: String,
    voter: String,
    vote: String,
    severity: String,
    agree: usize,
    disagree: usize,
    missing: usize,
}

fn normalized_vote(value: &str) -> String {
    match value.trim().to_ascii_uppercase().as_str() {
        "YES" => "YES".to_owned(),
        "NO" | "EXONERATE" => "NO".to_owned(),
        _ => String::new(),
    }
}

fn agreement_observations(
    result: &str,
    voter_votes: &[(String, String)],
    severities: &[String],
) -> Vec<VoterObservation> {
    if !["accepted", "rejected"].contains(&result.trim().to_ascii_lowercase().as_str()) {
        return Vec::new();
    }
    if voter_votes
        .iter()
        .filter(|(_, vote)| !normalized_vote(vote).is_empty())
        .count()
        < 2
    {
        return Vec::new();
    }
    voter_votes
        .iter()
        .enumerate()
        .filter(|(_, (label, _))| !label.trim().is_empty())
        .map(|(index, (label, raw_vote))| {
            let vote = normalized_vote(raw_vote);
            let agrees =
                (result == "accepted" && vote == "YES") || (result == "rejected" && vote == "NO");
            VoterObservation {
                panel: "code-review".to_owned(),
                voter: label.trim().to_owned(),
                severity: severities.get(index).cloned().unwrap_or_default(),
                agree: usize::from(!vote.is_empty() && agrees),
                disagree: usize::from(!vote.is_empty() && !agrees),
                missing: usize::from(vote.is_empty()),
                vote,
            }
        })
        .collect()
}

#[derive(Default)]
struct AgreementScore {
    eligible: usize,
    agree: usize,
    disagree: usize,
    missing: usize,
}

#[derive(Default)]
struct SeverityScore {
    yes_votes: usize,
    major: usize,
    minor: usize,
    nit: usize,
    missing_severity: usize,
}

fn format_rate(value: Option<f64>) -> String {
    value.map_or_else(|| "n/a".to_owned(), |value| format!("{value:.3}"))
}

#[allow(clippy::cast_precision_loss)] // A review panel has a bounded number of voter observations.
fn render_voter_scoreboards(rows: &[VoterObservation]) -> String {
    let mut agreement: BTreeMap<(String, String), AgreementScore> = BTreeMap::new();
    let mut severity: BTreeMap<(String, String), SeverityScore> = BTreeMap::new();
    for row in rows {
        let key = (row.panel.clone(), row.voter.clone());
        let entry = agreement.entry(key.clone()).or_default();
        entry.agree += row.agree;
        entry.disagree += row.disagree;
        entry.missing += row.missing;
        if row.agree != 0 || row.disagree != 0 {
            entry.eligible += 1;
        }
        let entry = severity.entry(key).or_default();
        if row.vote != "YES" {
            continue;
        }
        entry.yes_votes += 1;
        match row.severity.trim().to_ascii_lowercase().as_str() {
            "major" => entry.major += 1,
            "minor" => entry.minor += 1,
            "nit" => entry.nit += 1,
            _ => entry.missing_severity += 1,
        }
    }
    let mut output = String::from(
        "## Voter Agreement Scoreboard\n\n| Panel | Voter | Eligible | Agree | Disagree | Missing | Agreement | Outlier |\n|---|---|---:|---:|---:|---:|---:|---|\n",
    );
    if agreement.is_empty() {
        output.push_str("| undefined | n/a | 0 | 0 | 0 | 0 | n/a | false |\n\nAgreement is undefined when no accepted or rejected finding has at least two parseable YES/NO voter cells.\n");
    } else {
        for ((panel, voter), score) in &agreement {
            let denominator = score.agree + score.disagree;
            let agreement_rate =
                (denominator > 0).then_some(score.agree as f64 / denominator as f64);
            let outlier = score.eligible >= 20 && agreement_rate.is_some_and(|rate| rate < 0.5);
            writeln!(
                output,
                "| {panel} | {voter} | {} | {} | {} | {} | {} | {outlier} |",
                score.eligible,
                score.agree,
                score.disagree,
                score.missing,
                format_rate(agreement_rate),
            )
            .expect("string write");
        }
    }
    output.push_str("\n## Voter Severity Scoreboard\n\n| Panel | Voter | YES Votes | Major | Minor | Nit | Missing Severity | High Rate | Calibration Score | Uncalibrated |\n|---|---|---:|---:|---:|---:|---:|---:|---:|---|\n");
    if severity.is_empty() {
        output.push_str("| undefined | n/a | 0 | 0 | 0 | 0 | 0 | n/a | n/a | false |\n\nSeverity calibration is undefined when no accepted or rejected finding has at least two parseable YES/NO voter cells.\n");
    } else {
        for ((panel, voter), score) in severity {
            let valid = score.major + score.minor + score.nit;
            let high_rate = (valid > 0).then_some(score.major as f64 / valid as f64);
            let calibration = high_rate.map(|rate| {
                if rate <= 0.9 {
                    1.0
                } else {
                    (1.0 - ((rate - 0.9) / 0.1)).clamp(0.0, 1.0)
                }
            });
            writeln!(
                output,
                "| {panel} | {voter} | {} | {} | {} | {} | {} | {} | {} | {} |",
                score.yes_votes,
                score.major,
                score.minor,
                score.nit,
                score.missing_severity,
                format_rate(high_rate),
                format_rate(calibration),
                high_rate.is_some_and(|rate| rate > 0.9),
            )
            .expect("string write");
        }
    }
    output
}

fn unique_finder_bonus() -> f64 {
    env::var("LARCH_UNIQUE_FINDER_BONUS")
        .ok()
        .and_then(|value| value.trim().parse::<f64>().ok())
        .filter(|value| value.is_finite() && *value > 0.0)
        .unwrap_or(0.0)
}

fn trim_decimal(text: &str) -> &str {
    text.trim_end_matches('0').trim_end_matches('.')
}

fn format_score(value: f64) -> String {
    if value == 0.0 {
        return "0".to_owned();
    }
    if value.fract() == 0.0 {
        format!("{value:.0}")
    } else {
        // Python's `f"{value:g}"` uses six significant digits, switches to
        // scientific notation outside [-4, 6), and omits trailing zeroes.
        let scientific = format!("{value:.5e}");
        let (mantissa, exponent) = scientific
            .split_once('e')
            .expect("scientific float representation has an exponent");
        let exponent = exponent
            .parse::<i32>()
            .expect("scientific float exponent is numeric");
        if (-4..6).contains(&exponent) {
            let decimals =
                usize::try_from((5 - exponent).max(0)).expect("nonnegative display precision");
            return trim_decimal(&format!("{value:.decimals$}")).to_owned();
        }
        format!("{}e{exponent:+03}", trim_decimal(mantissa))
    }
}

fn is_fileable_artifact(text: &str) -> bool {
    Regex::new(r"(?mi)^Vote tally:.*(?:^|[ \t])Fileable=true(?:[ \t]|$)")
        .expect("fileable artifact regex")
        .is_match(text)
}

fn aggregate_block_identity(block: &str) -> String {
    let filed = Regex::new(r"(?m)^[ \t]*-[ \t]+\*\*Filed[ \t]*URL\*\*:[^\n]*(?:\n|$)")
        .expect("filed url regex");
    let tally = Regex::new(r"(?m)^Vote tally:.*(?:\n|$)").expect("vote tally regex");
    let heading = Regex::new(r"^###\s+(?:OOS|FINDING)_\d+:").expect("identity heading regex");
    let whitespace = Regex::new(r"\s+").expect("identity whitespace regex");
    let text = filed.replace_all(block, "");
    let text = tally.replace_all(&text, "");
    let text = heading.replace(&text, "### ITEM:");
    whitespace
        .replace_all(text.trim(), " ")
        .to_ascii_lowercase()
}

fn aggregate_blocks(text: &str) -> Vec<String> {
    parse_oos_blocks(
        &text.replace("\r\n", "\n").replace('\r', "\n"),
        BlockBoundary::ItemHeading,
    )
    .into_iter()
    .map(|block| format!("{}\n", block.block.trim_matches('\n')))
    .filter(|block| !block.trim().is_empty())
    .collect()
}

fn next_oos_number(text: &str) -> u64 {
    parse_oos_blocks(text, BlockBoundary::OosHeading)
        .into_iter()
        .filter(|block| block.kind.as_str() == "OOS")
        .filter_map(|block| {
            block
                .item_id
                .strip_prefix("OOS_")
                .and_then(|number| number.parse::<u64>().ok())
        })
        .max()
        .unwrap_or(0)
        .saturating_add(1)
}

fn seed_oos_seq(session_env_path: &str) -> u64 {
    if session_env_path.is_empty() {
        return 0;
    }
    let accumulated = Path::new(session_env_path)
        .parent()
        .map(|parent| parent.join("accumulated-oos.md"));
    let Some(path) = accumulated else {
        return 0;
    };
    if !is_regular_nonempty(&path) {
        return 0;
    }
    let mut count = 0;
    let mut in_block = false;
    for line in read_text(&path).unwrap_or_default().lines() {
        if larch_core::is_canonical_heading(line, None) {
            if in_block {
                count += 1;
            }
            in_block = true;
        }
    }
    count + u64::from(in_block)
}

fn collector_statuses(path: &str) -> BTreeMap<String, String> {
    if path.is_empty() || !Path::new(path).is_file() {
        return BTreeMap::new();
    }
    let mut statuses = BTreeMap::new();
    let mut file = String::new();
    let mut status = String::new();
    for line in read_text(Path::new(path))
        .unwrap_or_default()
        .lines()
        .chain(std::iter::once(""))
    {
        if line.is_empty() {
            if !file.is_empty() && !status.is_empty() {
                statuses.insert(normalize_output_base(&file), status.clone());
            }
            file.clear();
            status.clear();
        } else if let Some(value) = line.strip_prefix("REVIEWER_FILE=") {
            value.clone_into(&mut file);
        } else if let Some(value) = line.strip_prefix("STATUS=") {
            value.clone_into(&mut status);
        }
    }
    statuses
}

fn manifest_rows(path: &Path) -> Vec<Map<String, Value>> {
    read_text(path)
        .unwrap_or_default()
        .lines()
        .filter(|line| !line.trim().is_empty())
        .filter_map(|line| serde_json::from_str::<Value>(line).ok())
        .filter_map(|value| value.as_object().cloned())
        .collect()
}

fn manifest_value(row: &Map<String, Value>, key: &str) -> String {
    row.get(key)
        .and_then(Value::as_str)
        .unwrap_or_default()
        .to_owned()
}

fn append_manifest_dead_rows(
    tally_lines: &mut String,
    manifest_file: &Path,
    collector_file: &str,
    score_rows: &[ScoreRow],
) {
    let statuses = collector_statuses(collector_file);
    let seen = score_rows
        .iter()
        .map(|(reviewer, _, _, _)| normalize_output_base(reviewer))
        .collect::<HashSet<_>>();
    for row in manifest_rows(manifest_file) {
        let output = manifest_value(&row, "output");
        let base = normalize_output_base(&output);
        if base.is_empty() || seen.contains(&base) {
            continue;
        }
        let status = statuses.get(&base).map_or("OK", String::as_str);
        let label = DEAD_ROW_LABEL_RE.replace(&base, "");
        writeln!(
            tally_lines,
            "| {label} | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS={status} |"
        )
        .expect("string write");
    }
}

fn archetype_map(path: &Path) -> IndexMap<String, (String, String, String)> {
    let mut map = IndexMap::new();
    for row in manifest_rows(path) {
        let output = manifest_value(&row, "output");
        let base = normalize_output_base(&output);
        let slot = manifest_value(&row, "slot");
        let mut focus = manifest_value(&row, "focus_area");
        let mut weight = manifest_value(&row, "weight");
        let archetype = if base == "codex-generalist-output.txt" {
            "code-quality".clone_into(&mut focus);
            "1".clone_into(&mut weight);
            "generic".to_owned()
        } else if base.starts_with("dyn-") && base.ends_with("-output.txt") {
            if focus.is_empty() {
                "code-quality".clone_into(&mut focus);
            }
            if slot.starts_with("dyn-") {
                slot
            } else {
                base.trim_end_matches("-output.txt").to_owned()
            }
        } else if SPECIALIST_OUTPUT_RE.is_match(&base) {
            let slug = base
                .strip_prefix("cursor-specialist-")
                .or_else(|| base.strip_prefix("codex-specialist-"))
                .unwrap_or(&base)
                .trim_end_matches("-output.txt");
            static_focus_area(slug).clone_into(&mut focus);
            "1".clone_into(&mut weight);
            slug.to_owned()
        } else {
            if focus.is_empty() {
                "code-quality".clone_into(&mut focus);
            }
            if weight.is_empty() {
                "1".clone_into(&mut weight);
            }
            if slot.is_empty() {
                base.trim_end_matches("-output.txt").to_owned()
            } else {
                slot
            }
        };
        if !weight.chars().all(|character| character.is_ascii_digit()) {
            "1".clone_into(&mut weight);
        }
        map.insert(base, (archetype, focus, weight));
    }
    map
}

#[allow(clippy::cast_precision_loss)] // Manifest rows are bounded by the review panel size.
fn write_yield_tsv(
    path: &Path,
    archetypes: &IndexMap<String, (String, String, String)>,
    score_rows: &[ScoreRow],
) -> Result<Vec<String>, String> {
    let mut totals: BTreeMap<String, (usize, usize, usize)> = BTreeMap::new();
    for (reviewer, kind, result, _) in score_rows {
        if kind != "finding" {
            continue;
        }
        let entry = totals.entry(normalize_output_base(reviewer)).or_default();
        entry.0 += 1;
        if result == "accepted" {
            entry.1 += 1;
        } else if result == "rejected" {
            entry.2 += 1;
        }
    }
    let mut text = String::from(
        "archetype_name\tfocus_area\tweight\tfindings_total\tfindings_accepted\tfindings_rejected\tyield_ratio\n",
    );
    for (base, (archetype, focus, weight)) in archetypes {
        let (total, accepted, rejected) = totals.get(base).copied().unwrap_or_default();
        let ratio = if total == 0 {
            "n/a".to_owned()
        } else {
            format!("{:.6}", accepted as f64 / total as f64)
        };
        writeln!(
            text,
            "{archetype}\t{focus}\t{weight}\t{total}\t{accepted}\t{rejected}\t{ratio}"
        )
        .expect("string write");
    }
    write_text(path, &text)?;
    let mut orphans = Vec::new();
    for (reviewer, _, _, _) in score_rows {
        let base = normalize_output_base(reviewer);
        if !archetypes.contains_key(&base) && !orphans.contains(&base) {
            orphans.push(base);
        }
    }
    Ok(orphans)
}

fn parse_rate_ok(
    voter_file: &str,
    ballot_file: &Path,
    review_tmpdir: &Path,
    tool: &str,
    slot: &str,
) -> Result<bool, String> {
    let path = Path::new(voter_file);
    if voter_file.is_empty() || !is_regular_nonempty(path) {
        return Ok(false);
    }
    let status = crate::voting_commands::tally_parse_rate_status(
        path,
        tool,
        ballot_file,
        review_tmpdir,
        slot,
    )
    .map_err(|_| format!("tally-code-votes: voter parse-rate check failed for {voter_file}"))?;
    Ok(status == "OK")
}

fn nested_implement_round(review_tmpdir: &Path, session_env_path: &str) -> bool {
    let Ok(real) = fs::canonicalize(review_tmpdir) else {
        return false;
    };
    let name = real
        .file_name()
        .and_then(|name| name.to_str())
        .unwrap_or_default();
    if !Regex::new(r"^round-[0-9]+$")
        .expect("round name regex")
        .is_match(name)
    {
        return false;
    }
    let Some(parent) = real.parent() else {
        return false;
    };
    if let Some(implement) = env::var_os("IMPLEMENT_TMPDIR")
        && fs::canonicalize(implement).is_ok_and(|path| path == parent)
    {
        return true;
    }
    !session_env_path.is_empty()
        && Path::new(session_env_path)
            .parent()
            .and_then(|path| fs::canonicalize(path).ok())
            .is_some_and(|path| path == parent)
}

fn is_initial_oos(item_id: &str, block_text: &str) -> bool {
    item_id.starts_with("OOS_")
        || Regex::new(r"\[(OUT_OF_SCOPE|OOS)\]")
            .expect("oos tag regex")
            .is_match(block_text.lines().next().unwrap_or_default())
}

fn not_substantive_warning(count: usize) -> String {
    format!(
        "**⚠ Degraded code-review panel: {count} reviewer slot(s) emitted narrative-only output (NOT_SUBSTANTIVE). Dead slots are shown in the scoreboard below.**"
    )
}

const fn panel_tier(eligible: usize) -> &'static str {
    match eligible {
        0 => "main-agent-required",
        1 => "single-judge",
        2 => "unanimous-2",
        _ => "full-3",
    }
}

fn item_number(item_id: &str) -> u64 {
    item_id
        .split_once('_')
        .and_then(|(_, number)| number.parse().ok())
        .unwrap_or(0)
}

type BallotBlock = (String, PathBuf, String);

fn block_paths(
    review_tmpdir: &Path,
    ballot_text: &str,
) -> Result<(tempfile::TempDir, Vec<BallotBlock>), String> {
    let mut blocks = larch_core::review::ballot_blocks(ballot_text)
        .map_err(|_| "duplicate or malformed FINDING/OOS headings in ballot".to_owned())?;
    blocks.sort_by_key(|(item_id, _)| {
        (
            usize::from(!item_id.starts_with("FINDING_")),
            item_number(item_id),
        )
    });
    let directory = Builder::new()
        .prefix("larch-tally-blocks-")
        .tempdir_in(review_tmpdir)
        .map_err(|error| error.to_string())?;
    let mut paths = Vec::new();
    for (item_id, text) in blocks {
        let path = directory.path().join(format!("{item_id}.md"));
        fs::write(&path, &text).map_err(|error| error.to_string())?;
        paths.push((item_id, path, text));
    }
    Ok((directory, paths))
}

type TallyPaths = (
    PathBuf,
    PathBuf,
    PathBuf,
    PathBuf,
    PathBuf,
    PathBuf,
    PathBuf,
    PathBuf,
    PathBuf,
);
type ScoreRow = (String, String, String, u8);

fn result_paths(request: &TallyRequest) -> TallyPaths {
    let accepted = request.review_tmpdir.join("accepted-findings.md");
    let rejected = request.review_tmpdir.join("rejected-findings.md");
    let oos_accepted = request.review_tmpdir.join("oos-accepted-review.md");
    let oos = request.review_tmpdir.join("oos.md");
    let voting_tally = request.review_tmpdir.join("voting-tally.md");
    let tally = request.review_tmpdir.join("review-tally.env");
    let yield_tsv = request.review_tmpdir.join("scout-archetype-yield.tsv");
    let class_tsv = if nested_implement_round(&request.review_tmpdir, &request.session_env_path) {
        request.review_tmpdir.join("findings-classification.tsv")
    } else {
        request.review_tmpdir.join(format!(
            "findings-classification-round-{}.tsv",
            request.round_num
        ))
    };
    let oos_out = if request.session_env_path.is_empty() {
        oos_accepted.clone()
    } else {
        Path::new(&request.session_env_path)
            .parent()
            .unwrap_or_else(|| Path::new(""))
            .join("oos-accepted-review.md")
    };
    (
        accepted,
        rejected,
        oos_accepted,
        oos,
        voting_tally,
        tally,
        yield_tsv,
        class_tsv,
        oos_out,
    )
}

fn initial_result(paths: &TallyPaths) -> TallyResult {
    TallyResult {
        rc: 0,
        status: String::new(),
        accepted_count: 0,
        rejected_count: 0,
        exonerated_count: 0,
        neutral_count: 0,
        oos_accepted_count: 0,
        oos_rejected_count: 0,
        out_of_scope_drift_count: 0,
        voting_tally_file: Some(paths.4.clone()),
        tally_file: Some(paths.5.clone()),
        accepted_findings_file: Some(paths.0.clone()),
        rejected_findings_file: Some(paths.1.clone()),
        oos_accepted_file: Some(paths.8.clone()),
        oos_file: Some(paths.3.clone()),
        eligible_voter_count: 0,
        voter_count: 0,
        parse_failed_count: 0,
        findings_classification_tsv_file: Some(paths.7.clone()),
        under_quorum_items: Vec::new(),
        voting_skipped_warning: String::new(),
        yield_tsv_file: None,
        warnings: Vec::new(),
        error: String::new(),
    }
}

#[allow(
    clippy::assigning_clones,
    clippy::cast_precision_loss,
    clippy::cognitive_complexity,
    clippy::format_push_string,
    clippy::suboptimal_flops,
    clippy::too_many_lines
)] // The ordered legacy tally artifacts are one compatibility transaction.
fn tally_code_votes_inner(request: &TallyRequest) -> TallyResult {
    if !request.ballot_file.is_file() {
        return TallyResult::failure("tally-code-votes: --ballot-file must name a file");
    }
    if !request.manifest_file.is_empty() && !Path::new(&request.manifest_file).is_file() {
        return TallyResult::failure("tally-code-votes: --manifest-file must name a file");
    }
    let Some(round) = parse_positive_round(&request.round_num) else {
        return TallyResult::failure("tally-code-votes: --round-num must be a positive integer");
    };
    let ballot_text = match read_text(&request.ballot_file) {
        Ok(text) => text,
        Err(error) => return TallyResult::failure(format!("tally-code-votes: {error}")),
    };
    if let Err(error) = fs::create_dir_all(&request.review_tmpdir) {
        return TallyResult::failure(format!("tally-code-votes: {error}"));
    }
    let (proposer_map, sidecar_required) = match resolved_proposer_map(request, &ballot_text) {
        Ok(value) => value,
        Err(error) => return TallyResult::failure(format!("tally-code-votes: {error}")),
    };
    let three_slot = !request.voter_tools.is_empty();
    if three_slot
        && (request.voter_files.len() != THREE_SLOT_COUNT
            || request.voter_tools.len() != THREE_SLOT_COUNT)
    {
        return TallyResult::failure(
            "tally-code-votes: --voter-tools requires exactly three --voter-files and three tool labels",
        );
    }
    let paths = result_paths(request);
    let mut output = initial_result(&paths);
    let (
        accepted_file,
        rejected_file,
        oos_accepted_file,
        oos_file,
        voting_tally_file,
        tally_env,
        yield_tsv,
        class_tsv,
        oos_accepted_out,
    ) = paths;
    for path in [
        &accepted_file,
        &rejected_file,
        &oos_accepted_file,
        &oos_file,
        &tally_env,
    ] {
        if let Err(error) = write_text(path, "") {
            return TallyResult::failure(format!("tally-code-votes: {error}"));
        }
    }
    if oos_accepted_out != oos_accepted_file
        && let Err(error) = write_text(&oos_accepted_out, "")
    {
        return TallyResult::failure(format!("tally-code-votes: {error}"));
    }
    let (_block_directory, blocks) = match block_paths(&request.review_tmpdir, &ballot_text) {
        Ok(value) => value,
        Err(error) => return TallyResult::failure(format!("tally-code-votes: {error}")),
    };
    let ballot_ids = blocks
        .iter()
        .map(|(item, _, _)| item.clone())
        .collect::<HashSet<_>>();
    let header = code_review_classification_header(three_slot, true);
    let mut classification = format!("{header}\n");
    let not_substantive = parse_nonnegative(&request.not_substantive_count);
    if blocks.is_empty() {
        let mut tally_text = String::from(
            "# Code Review Voting Tally\n\nRound skipped: no findings to adjudicate.\n\n",
        );
        if not_substantive > 0 {
            tally_text.push_str(&format!("{}\n\n", not_substantive_warning(not_substantive)));
        }
        tally_text.push_str(&render_voter_scoreboards(&[]));
        let counts = "ACCEPTED_COUNT=0\nREJECTED_COUNT=0\nEXONERATED_COUNT=0\nNEUTRAL_COUNT=0\nOOS_ACCEPTED_COUNT=0\nOOS_REJECTED_COUNT=0\n";
        let ledger_root = ledger_root(
            &request.review_tmpdir,
            (!request.session_env_path.is_empty()).then(|| Path::new(&request.session_env_path)),
            None,
        );
        if let Err(error) = write_round(&ledger_root, round, Vec::new()) {
            return TallyResult::failure(format!("tally-code-votes: {error}"));
        }
        for (path, text) in [
            (&class_tsv, classification.as_str()),
            (&voting_tally_file, tally_text.as_str()),
            (&tally_env, counts),
        ] {
            if let Err(error) = write_text(path, text) {
                return TallyResult::failure(format!("tally-code-votes: {error}"));
            }
        }
        "skipped-empty-findings".clone_into(&mut output.status);
        return output;
    }
    let mut eligible = 0_usize;
    let mut effective_files = Vec::new();
    let mut effective_slots = [false; THREE_SLOT_COUNT];
    let mut parse_failed = 0_usize;
    if three_slot {
        for (index, voter_file) in request.voter_files.iter().enumerate() {
            if is_regular_nonempty(Path::new(voter_file)) {
                eligible += 1;
                match parse_rate_ok(
                    voter_file,
                    &request.ballot_file,
                    &request.review_tmpdir,
                    &request.voter_tools[index],
                    &index.to_string(),
                ) {
                    Ok(true) => effective_slots[index] = true,
                    Ok(false) => parse_failed += 1,
                    Err(error) => return TallyResult::failure(error),
                }
            }
        }
    } else {
        eligible = if request.both_down == "true" {
            0
        } else {
            request.voter_files.len()
        };
        for voter_file in &request.voter_files {
            let tool = Path::new(voter_file)
                .file_name()
                .and_then(|name| name.to_str())
                .unwrap_or_default()
                .strip_suffix("-vote-output.txt")
                .unwrap_or("claude")
                .to_owned();
            match parse_rate_ok(
                voter_file,
                &request.ballot_file,
                &request.review_tmpdir,
                &tool,
                "",
            ) {
                Ok(true) => effective_files.push(voter_file.clone()),
                Ok(false) => parse_failed += 1,
                Err(error) => return TallyResult::failure(error),
            }
        }
    }
    let effective = eligible.saturating_sub(parse_failed);
    if effective == 0 {
        let mut contexts = Vec::new();
        for (item_id, block_path, block_text) in &blocks {
            let reviewer =
                match proposer_for_item(item_id, block_text, &proposer_map, sidecar_required) {
                    Ok(reviewer) => reviewer,
                    Err(error) => {
                        return TallyResult::failure(format!("tally-code-votes: {error}"));
                    }
                };
            let is_oos = is_initial_oos(item_id, block_text)
                || (!is_initial_oos(item_id, block_text)
                    && scope_drift(block_text, &request.scope_files, &request.plan_file));
            let cells = if three_slot {
                request
                    .voter_tools
                    .iter()
                    .map(|tool| {
                        (
                            String::new(),
                            String::new(),
                            String::new(),
                            String::new(),
                            String::new(),
                            Some(tool.clone()),
                        )
                    })
                    .collect()
            } else {
                Vec::new()
            };
            contexts.push(ItemContext {
                item_id: item_id.clone(),
                block_path: block_path.clone(),
                block_text: block_text.clone(),
                artifact_text: block_text.clone(),
                reviewer,
                cells,
                yes: 0,
                no: 0,
                judge_error: 0,
                is_oos,
                eligible_voters: 0,
                voter_votes: Vec::new(),
                voter_severities: Vec::new(),
            });
        }
        if let Err(error) = run_items(
            contexts,
            |result| {
                classification.push_str(&classification_row(
                    &result.context.item_id,
                    &result.context.reviewer,
                    &result.voting_result,
                    &result.context.cells,
                    three_slot,
                    result.context.is_oos,
                ));
                classification.push('\n');
                Ok::<(), String>(())
            },
            |_| Ok::<bool, String>(false),
            |_| Ok::<(), String>(()),
        ) {
            return TallyResult::failure(format!("tally-code-votes: {error}"));
        }
        let warning = "**⚠ Degraded code-review panel: 0 judges available. Panel tier: main-agent-required. Manual adjudication needed.**".to_owned();
        let mut tally_text = format!("# Code Review Voting Tally\n\n{warning}\n\n");
        if not_substantive > 0 {
            tally_text.push_str(&format!("{}\n\n", not_substantive_warning(not_substantive)));
        }
        if parse_failed > 0 && eligible > 0 {
            tally_text.push_str(&format!("**⚠ Degraded code-review panel: {parse_failed} voter slot(s) emitted narrative-only output (parse-rate ≥80% JUDGE_ERROR) and were removed from the effective quorum.**\n\n"));
        }
        tally_text.push_str(&render_voter_scoreboards(&[]));
        for (path, text) in [
            (&class_tsv, classification.as_str()),
            (&voting_tally_file, tally_text.as_str()),
        ] {
            if let Err(error) = write_text(path, text) {
                return TallyResult::failure(format!("tally-code-votes: {error}"));
            }
        }
        "main-agent-vote-required".clone_into(&mut output.status);
        output.eligible_voter_count = eligible;
        output.parse_failed_count = parse_failed;
        output.voting_skipped_warning = warning;
        return output;
    }

    let mut score_rows: Vec<ScoreRow> = Vec::new();
    let mut bonus_by_reviewer: BTreeMap<String, f64> = BTreeMap::new();
    let active_bonus = unique_finder_bonus();
    let mut sole_finder_reward_count = 0_usize;
    let mut agreement_rows = Vec::new();
    let mut ledger_entries = Vec::new();
    let mut tally_lines = String::from("# Code Review Voting Tally\n\n");
    let expected = if three_slot {
        if request.codex_available == "true" || request.cursor_available == "true" {
            THREE_SLOT_COUNT
        } else {
            1
        }
    } else {
        1 + usize::from(request.codex_available == "true")
            + usize::from(request.cursor_available == "true")
    };
    if effective < expected {
        tally_lines.push_str(&format!(
            "**⚠ Degraded code-review panel: {effective} judge(s) available. Panel tier: {}.**\n\n",
            panel_tier(effective),
        ));
    }
    if parse_failed > 0 {
        tally_lines.push_str(&format!(
            "**⚠ Degraded code-review panel: {parse_failed} voter slot(s) emitted narrative-only output (parse-rate ≥80% JUDGE_ERROR) and were removed from the effective quorum.**\n\n"
        ));
    }
    if not_substantive > 0 {
        tally_lines.push_str(&format!("{}\n\n", not_substantive_warning(not_substantive)));
    }
    tally_lines.push_str("## Per-finding vote breakdown\n\n| Item | YES | NO | JERR | Result |\n|---|---:|---:|---:|---|\n");
    let quorum = effective / 2 + 1;
    let mut under_quorum_items = Vec::new();
    let mut drift = 0_usize;
    let mut contexts = Vec::new();
    for (item_id, block_path, block_text) in &blocks {
        let alias = alias_ballot_id(item_id, &ballot_ids);
        let mut cells = Vec::new();
        let mut yes = 0_usize;
        let mut no = 0_usize;
        let mut judge_error = 0_usize;
        if three_slot {
            for (index, effective_slot) in effective_slots.iter().enumerate() {
                let tool = request.voter_tools[index].clone();
                if !effective_slot {
                    cells.push((
                        String::new(),
                        String::new(),
                        String::new(),
                        String::new(),
                        String::new(),
                        Some(tool),
                    ));
                    continue;
                }
                let parsed = parse_judge_vote_text(
                    item_id,
                    &read_text(Path::new(&request.voter_files[index])).unwrap_or_default(),
                    &alias,
                );
                let vote = if parsed.vote.is_empty() {
                    "JUDGE_ERROR".to_owned()
                } else {
                    parsed.vote
                };
                match vote.as_str() {
                    "YES" => yes += 1,
                    "NO" => no += 1,
                    _ => judge_error += 1,
                }
                cells.push((
                    vote,
                    parsed.correctness,
                    parsed.severity,
                    parsed.quality,
                    parsed.uncertain,
                    Some(tool),
                ));
            }
        } else {
            for voter_file in &effective_files {
                let parsed = parse_judge_vote_text(
                    item_id,
                    &read_text(Path::new(voter_file)).unwrap_or_default(),
                    &alias,
                );
                let vote = if parsed.vote.is_empty() {
                    "JUDGE_ERROR".to_owned()
                } else {
                    parsed.vote
                };
                match vote.as_str() {
                    "YES" => yes += 1,
                    "NO" => no += 1,
                    _ => judge_error += 1,
                }
                cells.push((
                    vote,
                    parsed.correctness,
                    parsed.severity,
                    parsed.quality,
                    parsed.uncertain,
                    None,
                ));
            }
        }
        let initial_oos = is_initial_oos(item_id, block_text);
        let is_oos =
            initial_oos || scope_drift(block_text, &request.scope_files, &request.plan_file);
        if is_oos && !initial_oos {
            drift += 1;
        }
        if effective >= MIN_DEGRADABLE_PANEL && yes + no < quorum {
            under_quorum_items.push(item_id.clone());
        }
        let voter_votes = if three_slot {
            (0..THREE_SLOT_COUNT)
                .map(|index| {
                    (
                        request.voter_tools[index].clone(),
                        cells
                            .get(index)
                            .map_or(String::new(), |cell| cell.0.clone()),
                    )
                })
                .collect()
        } else {
            (1..=THREE_SLOT_COUNT)
                .map(|index| {
                    (
                        format!("v{index}"),
                        cells
                            .get(index - 1)
                            .map_or(String::new(), |cell| cell.0.clone()),
                    )
                })
                .collect()
        };
        let voter_severities = (0..THREE_SLOT_COUNT)
            .map(|index| {
                cells
                    .get(index)
                    .map_or(String::new(), |cell| cell.2.clone())
            })
            .collect();
        let reviewer = match proposer_for_item(item_id, block_text, &proposer_map, sidecar_required)
        {
            Ok(value) => value,
            Err(error) => return TallyResult::failure(format!("tally-code-votes: {error}")),
        };
        let artifact_text = proposer_map.entries.get(item_id).map_or_else(
            || block_text.clone(),
            |(_, line)| restore_reviewer_attribution(block_text, line),
        );
        contexts.push(ItemContext {
            item_id: item_id.clone(),
            block_path: block_path.clone(),
            block_text: block_text.clone(),
            artifact_text,
            reviewer,
            cells,
            yes,
            no,
            judge_error,
            is_oos,
            eligible_voters: effective,
            voter_votes,
            voter_severities,
        });
    }
    let security_oos_file = if request.session_env_path.is_empty() {
        oos_accepted_file
            .parent()
            .unwrap_or(&request.review_tmpdir)
            .join("security-oos-observations.md")
    } else {
        Path::new(&request.session_env_path)
            .parent()
            .unwrap_or(&request.review_tmpdir)
            .join("security-oos-observations.md")
    };
    let pool_file = oos_accepted_out
        .parent()
        .unwrap_or(&request.review_tmpdir)
        .join(OOS_AGGREGATE_POOL);
    let mut accepted = 0_usize;
    let mut rejected = 0_usize;
    let exonerated = 0_usize;
    let mut neutral = 0_usize;
    let mut oos_accepted = 0_usize;
    let mut oos_rejected = 0_usize;
    let mut oos_seq = seed_oos_seq(&request.session_env_path);
    let execution = run_items(
        contexts,
        |result| {
            let context = &result.context;
            for observation in agreement_observations(
                &result.voting_result,
                &context.voter_votes,
                &context.voter_severities,
            ) {
                agreement_rows.push(observation);
            }
            tally_lines.push_str(&format!(
                "| {} | {} | {} | {} | {} |\n",
                context.item_id, context.yes, context.no, context.judge_error, result.voting_result,
            ));
            classification.push_str(&classification_row(
                &context.item_id,
                &context.reviewer,
                &result.voting_result,
                &context.cells,
                three_slot,
                result.classification_scope == "oos",
            ));
            classification.push('\n');
            ledger_entries.push(ledger_entry(
                &context.item_id,
                &context.block_text,
                &result.ledger_outcome,
                &format!("YES={}/{effective}", context.yes),
                round,
            ));
            let slots = context
                .reviewer
                .split(',')
                .map(str::trim)
                .filter(|slot| !slot.is_empty());
            for slot in slots {
                score_rows.push((
                    slot.to_owned(),
                    result.score_kind.clone(),
                    result.score_result.clone(),
                    result.accepted_weight,
                ));
            }
            let slot_count = context
                .reviewer
                .split(',')
                .filter(|slot| !slot.trim().is_empty())
                .count();
            if result.unique_finder_eligible && slot_count == 1 && active_bonus > 0.0 {
                let reviewer = context.reviewer.trim().to_owned();
                *bonus_by_reviewer.entry(reviewer).or_default() += active_bonus;
                sole_finder_reward_count += 1;
            }
            Ok::<(), String>(())
        },
        |context| Ok::<bool, String>(is_security_block_text(&context.block_text)),
        |result| {
            let context = &result.context;
            let security = result.security.unwrap_or(false);
            if result.artifact_bucket == "accepted" {
                append_text(&accepted_file, &format!("{}\n", context.artifact_text))?;
                accepted += 1;
                record_tally(&tally_env, &context.item_id, true, "accepted")?;
            } else if result.artifact_bucket == "rejected" {
                rejected += 1;
                if result.voting_result == "neutral" {
                    neutral += 1;
                }
                let subtype = if result.voting_result == "rejected" {
                    "dismissed (0 YES)"
                } else {
                    "neutral (YES below acceptance threshold)"
                };
                append_text(
                    &rejected_file,
                    &format!(
                        "### [rejected] {}\n\n**Rejected subtype:** {subtype}\n\n{}\nVote tally: YES={} NO={} JUDGE_ERROR={}\n\n",
                        context.item_id,
                        context.artifact_text,
                        context.yes,
                        context.no,
                        context.judge_error,
                    ),
                )?;
                record_tally(&tally_env, &context.item_id, false, &result.voting_result)?;
            } else if !context.is_oos {
                let artifact = format!(
                    "{}\nVote tally: YES={} NO={} JUDGE_ERROR={} Result={} ({})\n\n",
                    context.artifact_text,
                    context.yes,
                    context.no,
                    context.judge_error,
                    result.voting_result,
                    result.reroute_marker,
                );
                record_public_oos_artifact(
                    &oos_file,
                    &pool_file,
                    &security_oos_file,
                    &artifact,
                    security,
                    false,
                )?;
                oos_rejected += 1;
                record_tally(&tally_env, &context.item_id, false, "oos")?;
            } else {
                let marker = if result.fileable_oos { "true" } else { "false" };
                let artifact = format!(
                    "{}\nVote tally: YES={} NO={} JUDGE_ERROR={} Result={} Fileable={marker}\n\n",
                    context.artifact_text,
                    context.yes,
                    context.no,
                    context.judge_error,
                    result.voting_result,
                );
                record_public_oos_artifact(
                    &oos_file,
                    &pool_file,
                    &security_oos_file,
                    &artifact,
                    security,
                    result.fileable_oos,
                )?;
                if result.fileable_oos {
                    if !security {
                        oos_seq += 1;
                        let normalized =
                            normalize_oos_block_header(oos_seq, &context.artifact_text);
                        append_text(&oos_accepted_file, &format!("{normalized}\n"))?;
                        if oos_accepted_out != oos_accepted_file {
                            append_text(&oos_accepted_out, &format!("{normalized}\n"))?;
                        }
                        oos_accepted += 1;
                    }
                    record_tally(&tally_env, &context.item_id, true, "accepted")?;
                } else {
                    if result.voting_result != "accepted" {
                        oos_rejected += 1;
                    }
                    record_tally(
                        &tally_env,
                        &context.item_id,
                        result.voting_result == "accepted",
                        &result.voting_result,
                    )?;
                }
            }
            Ok::<(), String>(())
        },
    );
    if let Err(error) = execution {
        return TallyResult::failure(format!("tally-code-votes: {error}"));
    }
    if !under_quorum_items.is_empty() {
        let warning = format!(
            "**⚠ Degraded code-review panel: {} finding(s) decided below the {quorum}-of-{effective} panel quorum because per-item JUDGE_ERROR dropped valid votes below quorum ({}). These items were resolved by the remaining voter(s) and may warrant manual review.**\n\n",
            under_quorum_items.len(),
            under_quorum_items.join(", "),
        );
        tally_lines = format!(
            "# Code Review Voting Tally\n\n{warning}{}",
            tally_lines
                .strip_prefix("# Code Review Voting Tally\n\n")
                .unwrap_or(&tally_lines)
        );
    }
    tally_lines.push_str("\n## Reviewer Competition Scoreboard\n\n");
    tally_lines.push_str("| Reviewer | Proposed | Accepted | Neutral | Rejected | OOS-Proposed | OOS-Accepted | OOS-Neutral | OOS-Rejected | Score | Status |\n");
    tally_lines.push_str("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|\n");
    let mut stats: BTreeMap<String, BTreeMap<String, i64>> = BTreeMap::new();
    for (reviewer, kind, result, accepted_weight) in &score_rows {
        let row = stats.entry(reviewer.clone()).or_default();
        if kind == "finding" {
            *row.entry("proposed".to_owned()).or_default() += 1;
            *row.entry(result.clone()).or_default() += 1;
            if result == "accepted" {
                *row.entry("accepted_weight".to_owned()).or_default() +=
                    i64::from(*accepted_weight);
            }
        } else {
            *row.entry("oos_proposed".to_owned()).or_default() += 1;
            *row.entry(format!("oos_{result}")).or_default() += 1;
        }
    }
    for (reviewer, row) in &stats {
        let value = |name: &str| *row.get(name).unwrap_or(&0);
        let label = SCORE_LABEL_RE.replace(reviewer, "");
        let score = value("accepted_weight") as f64 - (value("neutral") as f64 * 0.25)
            + value("oos_accepted") as f64
            - value("rejected") as f64
            - value("oos_rejected") as f64
            + bonus_by_reviewer.get(reviewer).copied().unwrap_or_default();
        tally_lines.push_str(&format!(
            "| {label} | {} | {} | {} | {} | {} | {} | {} | {} | {} | STATUS=OK |\n",
            value("proposed"),
            value("accepted"),
            value("neutral"),
            value("rejected"),
            value("oos_proposed"),
            value("oos_accepted"),
            value("oos_neutral"),
            value("oos_rejected"),
            format_score(score),
        ));
    }
    if !request.manifest_file.is_empty() {
        append_manifest_dead_rows(
            &mut tally_lines,
            Path::new(&request.manifest_file),
            &request.collector_results_file,
            &score_rows,
        );
    }
    if active_bonus > 0.0 && sole_finder_reward_count > 0 {
        tally_lines.push_str(&format!(
            "\n**Unique finder bonus active:** {sole_finder_reward_count} accepted in-scope sole-finder finding(s) received +{} each.\n",
            format_score(active_bonus)
        ));
    }
    tally_lines.push('\n');
    tally_lines.push_str(&render_voter_scoreboards(&agreement_rows));
    if let Err(error) = write_text(&voting_tally_file, &tally_lines) {
        return TallyResult::failure(format!("tally-code-votes: {error}"));
    }
    if let Err(error) = write_text(&class_tsv, &classification) {
        return TallyResult::failure(format!("tally-code-votes: {error}"));
    }
    let mut warnings = Vec::new();
    let yield_file = if request.manifest_file.is_empty() {
        None
    } else {
        match write_yield_tsv(
            &yield_tsv,
            &archetype_map(Path::new(&request.manifest_file)),
            &score_rows,
        ) {
            Ok(orphans) => {
                warnings.extend(orphans.into_iter().map(|orphan| {
                    format!("yield TSV missing manifest entry for reviewer basename: {orphan}")
                }));
                Some(yield_tsv)
            }
            Err(error) => return TallyResult::failure(format!("tally-code-votes: {error}")),
        }
    };
    let ledger_root = ledger_root(
        &request.review_tmpdir,
        (!request.session_env_path.is_empty()).then(|| Path::new(&request.session_env_path)),
        None,
    );
    if let Err(error) = write_round(&ledger_root, round, ledger_entries) {
        return TallyResult::failure(format!("tally-code-votes: {error}"));
    }
    let counts = format!(
        "ACCEPTED_COUNT={accepted}\nREJECTED_COUNT={rejected}\nEXONERATED_COUNT={exonerated}\nNEUTRAL_COUNT={neutral}\nOOS_ACCEPTED_COUNT={oos_accepted}\nOOS_REJECTED_COUNT={oos_rejected}\n"
    );
    if let Err(error) = append_text(&tally_env, &counts) {
        return TallyResult::failure(format!("tally-code-votes: {error}"));
    }
    output.status = "ok".to_owned();
    output.accepted_count = accepted;
    output.rejected_count = rejected;
    output.exonerated_count = exonerated;
    output.neutral_count = neutral;
    output.oos_accepted_count = oos_accepted;
    output.oos_rejected_count = oos_rejected;
    output.out_of_scope_drift_count = drift;
    output.eligible_voter_count = eligible;
    output.voter_count = effective;
    output.parse_failed_count = parse_failed;
    output.under_quorum_items = under_quorum_items;
    output.yield_tsv_file = yield_file;
    output.warnings = warnings;
    output
}

fn record_tally(path: &Path, item_id: &str, accepted: bool, outcome: &str) -> Result<(), String> {
    let (prefix, number) = item_id.split_once('_').unwrap_or((item_id, ""));
    let mut text = format!(
        "{prefix}_{number}_ACCEPTED={}\n",
        if accepted { "true" } else { "false" }
    );
    match outcome {
        "accepted" => writeln!(text, "{prefix}_{number}_OUTCOME=accepted").expect("string write"),
        "oos" => writeln!(text, "{prefix}_{number}_OUTCOME=oos").expect("string write"),
        _ => {
            writeln!(text, "{prefix}_{number}_OUTCOME=rejected").expect("string write");
            let subtype = if outcome == "rejected" {
                "true_rejected"
            } else {
                "neutral"
            };
            writeln!(text, "{prefix}_{number}_REJECTED_SUBTYPE={subtype}").expect("string write");
        }
    }
    append_text(path, &text)
}

fn record_public_oos_artifact(
    oos_file: &Path,
    pool_file: &Path,
    security_file: &Path,
    artifact: &str,
    security: bool,
    accepted: bool,
) -> Result<(), String> {
    if security {
        append_text(security_file, artifact)
    } else {
        append_text(oos_file, artifact)?;
        if accepted {
            append_oos_pool_candidate(pool_file, artifact)?;
        }
        Ok(())
    }
}

fn append_oos_pool_candidate(pool_file: &Path, artifact: &str) -> Result<(), String> {
    if !is_fileable_artifact(artifact) {
        return Ok(());
    }
    let identity = aggregate_block_identity(artifact);
    if identity.is_empty() {
        return Ok(());
    }
    let existing = read_text(pool_file).unwrap_or_default();
    if aggregate_blocks(&existing)
        .iter()
        .any(|block| aggregate_block_identity(block) == identity)
    {
        return Ok(());
    }
    let separator = if existing.is_empty() || existing.ends_with('\n') {
        ""
    } else {
        "\n"
    };
    append_text(
        pool_file,
        &format!("{separator}{}\n", artifact.trim_end_matches('\n')),
    )
}

pub fn tally_code_votes(arguments: &[OsString]) -> ExitCode {
    let request = match tally_request(arguments) {
        Ok(request) => request,
        Err(code) => return code,
    };
    let result = tally_code_votes_inner(&request);
    result.emit();
    ExitCode::from(result.rc)
}

#[derive(Clone, Debug)]
struct EmitRequest {
    tally_file: PathBuf,
    accepted_findings_file: PathBuf,
    oos_file: PathBuf,
    review_tmpdir: PathBuf,
    session_env_path: String,
    round: String,
    mode: String,
    implement_tmpdir: String,
    scout_status: String,
    dynamic_slots: String,
    static_slot_count: String,
}

fn emit_request(arguments: &[OsString]) -> Result<EmitRequest, ExitCode> {
    const KNOWN: &[&str] = &[
        "--tally-file",
        "--accepted-findings-file",
        "--oos-file",
        "--review-tmpdir",
        "--session-env-path",
        "--round",
        "--mode",
        "--implement-tmpdir",
        "--scout-status",
        "--dynamic-slots",
        "--static-slot-count",
    ];
    let parsed = parse_options(arguments, "emit-tally", EMIT_USAGE, KNOWN, &[])?;
    require_all(
        &parsed,
        &[
            "--tally-file",
            "--accepted-findings-file",
            "--oos-file",
            "--review-tmpdir",
            "--mode",
        ],
        EMIT_USAGE,
        "emit-tally",
    )?;
    let mode = required(&parsed, "--mode", EMIT_USAGE, "emit-tally")?;
    if !["diff", "description"].contains(&mode.as_str()) {
        eprintln!(
            "{EMIT_USAGE}\nemit-tally: error: argument --mode: invalid choice: '{mode}' (choose from 'diff', 'description')"
        );
        return Err(ExitCode::from(2));
    }
    Ok(EmitRequest {
        tally_file: PathBuf::from(required(&parsed, "--tally-file", EMIT_USAGE, "emit-tally")?),
        accepted_findings_file: PathBuf::from(required(
            &parsed,
            "--accepted-findings-file",
            EMIT_USAGE,
            "emit-tally",
        )?),
        oos_file: PathBuf::from(required(&parsed, "--oos-file", EMIT_USAGE, "emit-tally")?),
        review_tmpdir: PathBuf::from(required(
            &parsed,
            "--review-tmpdir",
            EMIT_USAGE,
            "emit-tally",
        )?),
        session_env_path: parsed
            .values
            .get("--session-env-path")
            .cloned()
            .unwrap_or_default(),
        round: parsed
            .values
            .get("--round")
            .cloned()
            .unwrap_or_else(|| "1".to_owned()),
        mode,
        implement_tmpdir: parsed
            .values
            .get("--implement-tmpdir")
            .cloned()
            .unwrap_or_default(),
        scout_status: parsed
            .values
            .get("--scout-status")
            .cloned()
            .unwrap_or_else(|| "na".to_owned()),
        dynamic_slots: parsed
            .values
            .get("--dynamic-slots")
            .cloned()
            .unwrap_or_else(|| "0".to_owned()),
        static_slot_count: parsed
            .values
            .get("--static-slot-count")
            .cloned()
            .unwrap_or_else(|| "0".to_owned()),
    })
}

fn tally_count(tally: &BTreeMap<String, String>, key: &str) -> usize {
    tally
        .get(key)
        .and_then(|value| parse_ascii_decimal(value))
        .unwrap_or(0)
}

fn fallback_counts_from_tally_text(text: &str) -> (usize, usize, usize) {
    let tally = parse_kv(text);
    let mut accepted = tally_count(&tally, "ACCEPTED_COUNT");
    let mut rejected = tally_count(&tally, "REJECTED_COUNT");
    let neutral = tally_count(&tally, "NEUTRAL_COUNT");
    if accepted == 0 && text.contains("ACCEPTED=true") {
        accepted = Regex::new(r"(?m)^[A-Z_]+_[0-9]+_ACCEPTED=true$")
            .expect("accepted fallback regex")
            .find_iter(text)
            .count();
    }
    if rejected == 0 {
        let has_outcomes = Regex::new(r"(?m)^[A-Z_]+_[0-9]+_REJECTED_SUBTYPE=")
            .expect("rejected subtype regex")
            .is_match(text)
            || text.contains("_OUTCOME=");
        let expression = if has_outcomes {
            r"(?m)^[A-Z_]+_[0-9]+_OUTCOME=rejected$"
        } else {
            r"(?m)^[A-Z_]+_[0-9]+_ACCEPTED=false$"
        };
        rejected = Regex::new(expression)
            .expect("rejected fallback regex")
            .find_iter(text)
            .count();
    }
    (accepted, rejected, neutral)
}

fn metadata_summary_counts(review_tmpdir: &Path) -> Option<(usize, usize, usize)> {
    let text = read_text(&review_tmpdir.join("round-meta.json")).ok()?;
    let parsed = serde_json::from_str::<Value>(&text).ok()?;
    let tally = parsed.get("tally")?.as_object()?;
    let count = |key: &str| {
        tally
            .get(key)
            .and_then(Value::as_str)
            .and_then(parse_ascii_decimal)
            .or_else(|| {
                tally
                    .get(key)
                    .and_then(Value::as_u64)
                    .and_then(|value| value.try_into().ok())
            })
            .unwrap_or(0)
    };
    Some((
        count("ACCEPTED_COUNT"),
        count("REJECTED_COUNT"),
        count("NEUTRAL_COUNT"),
    ))
}

fn artifact_summary_counts(review_tmpdir: &Path) -> Option<(usize, usize, usize)> {
    let tally_path = review_tmpdir.join("voting-tally.md");
    let classification_path = review_tmpdir.join("findings-classification.tsv");
    let markdown = tally_path
        .is_file()
        .then(|| phase_detail::review_tally_summary_counts(&tally_path));
    let lines = read_text(&classification_path)
        .unwrap_or_default()
        .lines()
        .map(str::to_owned)
        .collect::<Vec<_>>();
    if !classification_path.is_file() || lines.len() < 2 {
        return markdown;
    }
    let headers = lines[0].split('\t').map(str::trim).collect::<Vec<_>>();
    let finding_index = headers
        .iter()
        .position(|header| *header == "finding_id")
        .unwrap_or(0);
    let result_index = headers
        .iter()
        .position(|header| *header == "voting_result")
        .unwrap_or(2);
    let scope_index = headers.iter().position(|header| *header == "scope");
    let mut classification = [0_usize; 3];
    let mut has_data = false;
    for line in &lines[1..] {
        let values = line.split('\t').map(str::trim).collect::<Vec<_>>();
        if values.len() < 3 {
            continue;
        }
        has_data |= !line.trim().is_empty();
        let item = values.get(finding_index).copied().unwrap_or(values[0]);
        let result = values.get(result_index).copied().unwrap_or(values[2]);
        let in_scope = scope_index.map_or_else(
            || !item.starts_with("OOS_"),
            |index| values.get(index).copied().unwrap_or_default() == "in_scope",
        );
        if in_scope
            && item.strip_prefix("FINDING_").is_some_and(|suffix| {
                !suffix.is_empty()
                    && suffix
                        .bytes()
                        .all(|byte| byte.is_ascii_alphanumeric() || byte == b'_')
            })
        {
            increment_result(&mut classification, result);
        }
    }
    if markdown.is_none() || (markdown == Some((0, 0, 0)) && has_data) {
        Some(classification.into())
    } else {
        markdown
    }
}

fn increment_result(counts: &mut [usize; 3], result: &str) {
    match result {
        "accepted" => counts[0] += 1,
        "rejected" => counts[1] += 1,
        "neutral" => counts[2] += 1,
        _ => {}
    }
}

fn review_round_summary_body(
    review_tmpdir: &Path,
    round: &str,
    mode: &str,
    counts: (usize, usize, usize),
    accepted_file: &Path,
) -> String {
    let summary = metadata_summary_counts(review_tmpdir)
        .or_else(|| artifact_summary_counts(review_tmpdir))
        .unwrap_or(counts);
    let mut body = format!(
        "# Review Round {round}\n\n- Mode: `{mode}`\n- {} accepted, {} rejected ({} neutral)\n\n",
        summary.0, summary.1, summary.2,
    );
    if is_regular_nonempty(accepted_file) {
        body.push_str("## Accepted Findings\n\n");
        body.push_str(&read_text(accepted_file).unwrap_or_default());
    }
    body
}

fn compact_rejected_findings_from_tally(tally_text: &str) -> String {
    let has_outcomes = tally_text.contains("_OUTCOME=");
    let mut compact = String::from("# Rejected Findings\n\n");
    for (index, line) in tally_text.lines().enumerate() {
        if line.ends_with("_OUTCOME=rejected")
            || (!has_outcomes && line.ends_with("_ACCEPTED=false"))
        {
            writeln!(compact, "{}:{line}", index + 1).expect("string write");
        }
    }
    compact
}

fn non_security_oos_count(path: &Path) -> usize {
    if !is_regular_nonempty(path) {
        return 0;
    }
    parse_oos_blocks(
        &read_text(path).unwrap_or_default(),
        BlockBoundary::OosHeading,
    )
    .into_iter()
    .filter(|block| block.item_id.starts_with("OOS_"))
    .filter(|block| !is_security_block_text(&block.block))
    .count()
}

fn aggregate_parent(
    review_tmpdir: &Path,
    session_env_path: &str,
    implement_tmpdir: &str,
) -> PathBuf {
    if !session_env_path.is_empty() {
        return Path::new(session_env_path)
            .parent()
            .unwrap_or(review_tmpdir)
            .to_path_buf();
    }
    if !implement_tmpdir.is_empty() && Path::new(implement_tmpdir).is_dir() {
        return PathBuf::from(implement_tmpdir);
    }
    review_tmpdir.to_path_buf()
}

fn promote_aggregate_oos_pool(
    sink: &Path,
    pool: &Path,
    main_agent: Option<&Path>,
) -> Result<(), String> {
    let sink_text = read_text(sink).unwrap_or_default();
    let mut seen = aggregate_blocks(&sink_text)
        .iter()
        .map(|block| aggregate_block_identity(block))
        .collect::<HashSet<_>>();
    let mut candidates = Vec::new();
    if let Some(main_agent) = main_agent.filter(|path| path.is_file()) {
        candidates.extend(
            aggregate_blocks(&read_text(main_agent).unwrap_or_default())
                .into_iter()
                .filter(|block| !is_security_block_text(block)),
        );
    }
    if pool.is_file() {
        let accepted =
            Regex::new(r"(?mi)^Vote tally:.*\bResult=accepted\b").expect("pool accepted regex");
        candidates.extend(
            aggregate_blocks(&read_text(pool).unwrap_or_default())
                .into_iter()
                .filter(|block| {
                    !is_security_block_text(block)
                        && accepted.is_match(block)
                        && is_fileable_artifact(block)
                }),
        );
    }
    let mut next = next_oos_number(&sink_text);
    let mut promoted = Vec::new();
    for block in candidates {
        let identity = aggregate_block_identity(&block);
        if identity.is_empty() || !seen.insert(identity) {
            continue;
        }
        promoted.push(format!(
            "{}\n",
            normalize_oos_block_header(next, block.trim_end_matches('\n'))
        ));
        next += 1;
    }
    if promoted.is_empty() {
        return Ok(());
    }
    let separator = if sink_text.is_empty() || sink_text.ends_with('\n') {
        ""
    } else {
        "\n"
    };
    append_text(sink, &format!("{separator}{}", promoted.join("\n")))
}

fn copy_emit_artifacts(destinations: &[PathBuf], artifacts: &[(&Path, &str)]) {
    for destination in destinations {
        for (source, name) in artifacts {
            let _ignored = fs::copy(source, destination.join(name));
        }
    }
}

fn reviewer_output_paths(review_tmpdir: &Path) -> Vec<String> {
    let Ok(entries) = fs::read_dir(review_tmpdir) else {
        return Vec::new();
    };
    let mut paths = Vec::new();
    for entry in entries.flatten() {
        let path = entry.path();
        if path
            .file_name()
            .and_then(|name| name.to_str())
            .is_some_and(|name| name.ends_with("-output.txt"))
        {
            paths.push(path.display().to_string());
        }
    }
    paths.sort();
    paths
}

#[allow(clippy::too_many_lines)] // The summary and copied artifacts must stay in legacy publication order.
pub fn emit_tally(arguments: &[OsString]) -> ExitCode {
    let request = match emit_request(arguments) {
        Ok(request) => request,
        Err(code) => return code,
    };
    if !request.tally_file.is_file() {
        eprintln!("emit-tally: --tally-file must name a file");
        return ExitCode::from(2);
    }
    if !request.accepted_findings_file.is_file() {
        eprintln!("emit-tally: --accepted-findings-file must name a file");
        return ExitCode::from(2);
    }
    let (Some(dynamic_slots), Some(static_slot_count)) = (
        parse_ascii_decimal(&request.dynamic_slots),
        parse_ascii_decimal(&request.static_slot_count),
    ) else {
        eprintln!(
            "emit-tally: --dynamic-slots and --static-slot-count must be non-negative integers"
        );
        return ExitCode::from(2);
    };
    if let Err(error) = fs::create_dir_all(&request.review_tmpdir) {
        eprintln!("emit-tally: {error}");
        return ExitCode::from(1);
    }
    let tally_text = match read_text(&request.tally_file) {
        Ok(text) => text,
        Err(error) => {
            eprintln!("emit-tally: {error}");
            return ExitCode::from(1);
        }
    };
    let tally = parse_kv(&tally_text);
    let mut accepted = tally_count(&tally, "ACCEPTED_COUNT");
    let mut rejected = tally_count(&tally, "REJECTED_COUNT");
    let mut neutral = tally_count(&tally, "NEUTRAL_COUNT");
    let missing_accepted = tally.get("ACCEPTED_COUNT").is_none_or(String::is_empty);
    let missing_rejected = tally.get("REJECTED_COUNT").is_none_or(String::is_empty);
    let missing_neutral = tally.get("NEUTRAL_COUNT").is_none_or(String::is_empty);
    if missing_accepted || missing_rejected {
        let fallback = fallback_counts_from_tally_text(&tally_text);
        if missing_accepted {
            accepted = fallback.0;
        }
        if missing_rejected {
            rejected = fallback.1;
        }
        if missing_neutral {
            neutral = fallback.2;
        }
    }
    let oos_accepted_count = tally_count(&tally, "OOS_ACCEPTED_COUNT");
    let round_summary = request.review_tmpdir.join("review-round-summary.md");
    let review_summary = request.review_tmpdir.join("review-summary.json");
    let rejected_file = request.review_tmpdir.join("rejected-findings.md");
    let rejected_full = request.review_tmpdir.join("rejected-findings-full.md");
    let oos_accepted_file = request.review_tmpdir.join("oos-accepted-review.md");
    if let Err(error) = write_text(
        &round_summary,
        &review_round_summary_body(
            &request.review_tmpdir,
            &request.round,
            &request.mode,
            (accepted, rejected, neutral),
            &request.accepted_findings_file,
        ),
    ) {
        eprintln!("emit-tally: {error}");
        return ExitCode::from(1);
    }
    if is_regular_nonempty(&rejected_file) {
        if let Err(error) = fs::copy(&rejected_file, &rejected_full) {
            eprintln!("emit-tally: {error}");
            return ExitCode::from(1);
        }
    } else {
        if let Err(error) = write_text(&rejected_full, "") {
            eprintln!("emit-tally: {error}");
            return ExitCode::from(1);
        }
        if let Err(error) = write_text(
            &rejected_file,
            &compact_rejected_findings_from_tally(&tally_text),
        ) {
            eprintln!("emit-tally: {error}");
            return ExitCode::from(1);
        }
    }
    let reviewer_paths = reviewer_output_paths(&request.review_tmpdir);
    let rounds_completed = parse_ascii_decimal(&request.round).unwrap_or(1);
    let summary = json!({
        "schema_version": 3,
        "rounds_completed": rounds_completed,
        "reviewer_output_paths": reviewer_paths,
        "panel": {
            "scout_status": request.scout_status,
            "static_slot_count": static_slot_count,
            "dynamic_slot_count": dynamic_slots,
            "total_slot_count": static_slot_count + dynamic_slots,
        },
        "finding_counts": {
            "total_accepted": accepted,
            "total_rejected": rejected,
            "total_neutral": neutral,
            "total_exonerated": 0,
        },
        "accepted_count": accepted,
        "rejected_count": rejected,
        "neutral_count": neutral,
        "exonerated_count": 0,
    });
    let summary_text = match serde_json::to_string(&summary) {
        Ok(value) => format!("{value}\n"),
        Err(error) => {
            eprintln!("emit-tally: {error}");
            return ExitCode::from(1);
        }
    };
    if let Err(error) = write_text(&review_summary, &summary_text) {
        eprintln!("emit-tally: {error}");
        return ExitCode::from(1);
    }
    let sink_has_content = is_regular_nonempty(&oos_accepted_file);
    let sink_count = non_security_oos_count(&oos_accepted_file);
    if sink_has_content && sink_count >= oos_accepted_count {
        // An already-complete sink is authoritative and must not be rebuilt.
    } else if sink_has_content {
        eprintln!(
            "emit-tally: OOS_ACCEPTED_COUNT={oos_accepted_count} but accepted sink has {sink_count} non-security block(s); refusing destructive rebuild"
        );
        return ExitCode::from(1);
    } else if request.oos_file.is_file() {
        if oos_accepted_count > 0 {
            let serialized =
                serialize_accepted_oos(&read_text(&request.oos_file).unwrap_or_default());
            if let Err(error) = write_text(&oos_accepted_file, &serialized.text) {
                eprintln!("emit-tally: {error}");
                return ExitCode::from(1);
            }
            let rebuilt = non_security_oos_count(&oos_accepted_file);
            if rebuilt != oos_accepted_count {
                eprintln!(
                    "emit-tally: OOS_ACCEPTED_COUNT={oos_accepted_count} but rebuild produced {rebuilt} non-security block(s)"
                );
                return ExitCode::from(1);
            }
        }
    } else if oos_accepted_count > 0 {
        eprintln!("emit-tally: OOS_ACCEPTED_COUNT but oos.md is absent");
        return ExitCode::from(1);
    } else if let Err(error) = write_text(&oos_accepted_file, "") {
        eprintln!("emit-tally: {error}");
        return ExitCode::from(1);
    }
    let aggregate_parent = aggregate_parent(
        &request.review_tmpdir,
        &request.session_env_path,
        &request.implement_tmpdir,
    );
    if let Err(error) = promote_aggregate_oos_pool(
        &oos_accepted_file,
        &aggregate_parent.join(OOS_AGGREGATE_POOL),
        Some(&aggregate_parent.join("oos-accepted-main-agent.md")),
    ) {
        eprintln!("emit-tally: {error}");
        return ExitCode::from(1);
    }
    let mut destinations = Vec::new();
    if !request.session_env_path.is_empty() {
        destinations.push(
            Path::new(&request.session_env_path)
                .parent()
                .unwrap_or(&request.review_tmpdir)
                .to_path_buf(),
        );
    }
    if !request.implement_tmpdir.is_empty() && Path::new(&request.implement_tmpdir).is_dir() {
        destinations.push(PathBuf::from(&request.implement_tmpdir));
    }
    copy_emit_artifacts(
        &destinations,
        &[
            (&round_summary, "review-round-summary.md"),
            (&review_summary, "review-summary.json"),
            (&rejected_full, "rejected-findings-full.md"),
            (&oos_accepted_file, "oos-accepted-review.md"),
        ],
    );
    println!("EMIT_OK=true");
    println!("ROUND_SUMMARY_FILE={}", round_summary.display());
    println!("REVIEW_SUMMARY_FILE={}", review_summary.display());
    println!(
        "OOS_FILING_COUNT={}",
        non_security_oos_count(&oos_accepted_file)
    );
    ExitCode::SUCCESS
}

#[derive(Clone, Debug)]
struct LogPhaseRequest {
    run_id: String,
    batch: String,
    action: String,
    payload_file: PathBuf,
    log_root: String,
}

fn log_phase_request(arguments: &[OsString]) -> Result<LogPhaseRequest, ExitCode> {
    const KNOWN: &[&str] = &[
        "--run-id",
        "--batch",
        "--action",
        "--payload-file",
        "--log-root",
    ];
    let parsed = parse_options(arguments, "log-phase", LOG_PHASE_USAGE, KNOWN, &[])?;
    require_all(
        &parsed,
        &["--run-id", "--batch", "--action", "--payload-file"],
        LOG_PHASE_USAGE,
        "log-phase",
    )?;
    let action = required(&parsed, "--action", LOG_PHASE_USAGE, "log-phase")?;
    if !["write", "append"].contains(&action.as_str()) {
        eprintln!(
            "{LOG_PHASE_USAGE}\nlog-phase: error: argument --action: invalid choice: '{action}' (choose from 'write', 'append')"
        );
        return Err(ExitCode::from(2));
    }
    Ok(LogPhaseRequest {
        run_id: required(&parsed, "--run-id", LOG_PHASE_USAGE, "log-phase")?,
        batch: required(&parsed, "--batch", LOG_PHASE_USAGE, "log-phase")?,
        action,
        payload_file: PathBuf::from(required(
            &parsed,
            "--payload-file",
            LOG_PHASE_USAGE,
            "log-phase",
        )?),
        log_root: parsed
            .values
            .get("--log-root")
            .cloned()
            .or_else(|| env::var("LARCH_LOG_ROOT").ok())
            .unwrap_or_default(),
    })
}

fn run_log_command(
    request: &LogPhaseRequest,
    batch: &str,
    payload: &Path,
) -> Result<larch_core::ProcessOutput, String> {
    let mut arguments = vec![OsString::from("run-log"), OsString::from(&request.action)];
    if !request.log_root.is_empty() {
        arguments.extend([
            OsString::from("--log-root"),
            OsString::from(&request.log_root),
        ]);
    }
    arguments.extend([
        OsString::from("--skill"),
        OsString::from("review"),
        OsString::from(format!("--run-id={}", request.run_id)),
        OsString::from("--batch"),
        OsString::from(batch),
        OsString::from(if request.action == "write" {
            "--input-file"
        } else {
            "--record-file"
        }),
        payload.as_os_str().to_owned(),
    ]);
    run_verified_larch(&arguments)
}

fn child_exit_code(output: &larch_core::ProcessOutput) -> ExitCode {
    let code = output.status().code().unwrap_or(1);
    ExitCode::from(u8::try_from(code).unwrap_or(1))
}

pub fn log_phase(arguments: &[OsString]) -> ExitCode {
    let request = match log_phase_request(arguments) {
        Ok(request) => request,
        Err(code) => return code,
    };
    if !request.payload_file.is_file() {
        eprintln!("log-phase: --payload-file must name a file");
        return ExitCode::from(2);
    }
    let registered = Regex::new(r"^(?:review-context|review-panel-manifest|review-findings|review-tally|review-scout-manifest|difficulty-rating|review-round-summary|panel-prompt-sizes|review-findings-classification-round-[1-5])$")
        .expect("registered review batch regex");
    if !registered.is_match(&request.batch) {
        eprintln!("log-phase: unregistered review batch: {}", request.batch);
        return ExitCode::from(2);
    }
    let primary = match run_log_command(&request, &request.batch, &request.payload_file) {
        Ok(output) => output,
        Err(error) => {
            eprintln!("log-phase: {error}");
            return ExitCode::from(1);
        }
    };
    if !primary.stderr().is_empty() {
        eprint!("{}", String::from_utf8_lossy(primary.stderr()));
    }
    if !primary.stdout().is_empty() {
        print!("{}", String::from_utf8_lossy(primary.stdout()));
    }
    if request.batch == "review-panel-manifest" && request.action == "write" {
        let sibling = request
            .payload_file
            .with_file_name("panel-prompt-sizes.tsv");
        if is_regular_nonempty(&sibling) {
            match run_log_command(&request, "panel-prompt-sizes", &sibling) {
                Ok(output) if output.status().success() => {}
                Ok(output) => {
                    eprintln!(
                        "log-phase: warning: failed to write sibling panel-prompt-sizes batch"
                    );
                    if !output.stderr().is_empty() {
                        eprint!("{}", String::from_utf8_lossy(output.stderr()));
                    }
                }
                Err(error) => {
                    eprintln!(
                        "log-phase: warning: failed to write sibling panel-prompt-sizes batch"
                    );
                    eprintln!("{error}");
                }
            }
        }
    }
    child_exit_code(&primary)
}

#[cfg(test)]
mod tests {
    use super::format_score;

    #[test]
    fn format_score_matches_python_general_number_formatting() {
        assert_eq!(format_score(0.0), "0");
        assert_eq!(format_score(1.234_567), "1.23457");
        assert_eq!(format_score(0.000_001), "1e-06");
        assert_eq!(format_score(999_999.9), "1e+06");
    }
}
