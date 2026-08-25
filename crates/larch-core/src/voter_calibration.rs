//! Pure math and rendering for the `/voter-calibration` analyzer.
//!
//! Byte-for-byte port of the retired Python analyzer
//! (`skills/voter-calibration/scripts/voter-calibration.py`) plus the
//! `larch.calibration.voting` helpers it consumed. In-crate tests pin the
//! calculation and rendering contract. Corpus discovery, era-boundary
//! resolution, and realized-outcome enrichment stay with the CLI owner in
//! `crates/larch-cli/src/voter_calibration_commands.rs`.

use std::collections::BTreeMap;
use std::fmt::Write as _;
use std::path::Path;

use crate::review::code_review_classification_required_fields;

const SEVERITY_BUCKETS: [&str; 3] = ["major", "minor", "nit"];
const DESIGN_REQUIRED: [&str; 6] = [
    "finding_id",
    "finding_reviewers",
    "voting_result",
    "v1_vote",
    "v2_vote",
    "v3_vote",
];
/// Positional voter fallbacks shared by design and code-review panels.
const VOTER_FALLBACKS: [&str; 3] = ["codex-validity", "codex-plan-fidelity", "codex-pragmatism"];
const FALSE_NEGATIVE_COUNTABLE: [&str; 3] = ["accepted", "neutral", "rejected"];
const FALSE_NEGATIVE_OOS_SCOPES: [&str; 3] = ["oos", "out_of_scope", "out-of-scope"];

/// One voter's ballot inside an eligible agreement row.
#[derive(Clone, Debug)]
pub struct AgreementVoter {
    pub voter: String,
    /// `"YES"`, `"NO"`, or `""` for a missing/unparseable cell.
    pub vote: String,
    pub agree: usize,
    pub disagree: usize,
    pub missing: usize,
    /// The raw severity cell; validated only during severity aggregation.
    pub severity: String,
}

/// One eligible accepted/rejected panel row.
#[derive(Clone, Debug)]
pub struct AgreementRow {
    pub panel: String,
    pub voters: Vec<AgreementVoter>,
}

/// Parsed agreement rows plus the malformed/ineligible row counters.
#[derive(Clone, Debug, Default)]
pub struct VoterAgreementTsvParse {
    pub rows: Vec<AgreementRow>,
    pub malformed_rows: usize,
    pub ineligible_rows: usize,
}

/// One parseable voter inside a false-negative-eligible row.
#[derive(Clone, Debug)]
pub struct FalseNegativeVoter {
    pub voter: String,
    pub vote: String,
}

/// One false-negative-eligible panel row (accepted, neutral, or rejected).
#[derive(Clone, Debug)]
pub struct FalseNegativeRow {
    pub panel: String,
    pub voting_result: String,
    pub voters: Vec<FalseNegativeVoter>,
}

/// Per-voter agreement aggregate.
#[derive(Clone, Debug)]
pub struct VoterAgreementRecord {
    pub panel: String,
    pub voter: String,
    pub eligible: usize,
    pub agree: usize,
    pub disagree: usize,
    pub missing: usize,
    pub agreement_rate: Option<f64>,
    pub outlier: bool,
}

/// Per-voter YES-severity aggregate.
#[derive(Clone, Debug)]
pub struct VoterSeverityRecord {
    pub panel: String,
    pub voter: String,
    pub yes_votes: usize,
    pub major: usize,
    pub minor: usize,
    pub nit: usize,
    pub missing_severity: usize,
    pub valid_yes_severity_count: usize,
    pub high_rate: Option<f64>,
    pub calibration_score: Option<f64>,
    pub uncalibrated: bool,
}

/// Per-voter false-negative YES aggregate.
#[derive(Clone, Debug)]
pub struct FalseNegativeRecord {
    pub panel: String,
    pub voter: String,
    pub yes_votes: usize,
    pub neutral_yes: usize,
    pub rejected_yes: usize,
    pub false_negative_yes: usize,
    pub false_negative_yes_rate: Option<f64>,
}

/// Accumulated per-corpus (or per-era-slice) parse state.
#[derive(Clone, Debug, Default)]
pub struct VoterCalibrationCorpus {
    pub files_seen: usize,
    pub skipped_files: usize,
    pub malformed_rows: usize,
    pub ineligible_rows: usize,
    pub rows: Vec<AgreementRow>,
    pub false_negative_rows: Vec<FalseNegativeRow>,
}

impl VoterCalibrationCorpus {
    /// Fold one classification TSV into this corpus, mirroring the Python
    /// `_parse_file_into_stats` skip/malformed/ineligible accounting.
    pub fn add_file(&mut self, panel_kind: &str, text: &str) {
        self.files_seen += 1;
        let parsed = voter_agreement_rows_from_tsv(text, panel_kind);
        let first_line = text.lines().next().unwrap_or_default();
        if parsed.rows.is_empty()
            && (!first_line.contains("voting_result")
                || !classification_tsv_schema_supported(text, panel_kind))
        {
            self.skipped_files += 1;
        }
        self.malformed_rows += parsed.malformed_rows;
        self.ineligible_rows += parsed.ineligible_rows;
        self.rows.extend(parsed.rows);
        self.false_negative_rows
            .extend(false_negative_rows_from_tsv(text, panel_kind));
    }
}

/// Rendering inputs describing the resolved era boundary.
#[derive(Clone, Debug)]
pub struct EraBoundaryDisplay {
    pub source: String,
    /// Boundary timestamp text, or `"n/a"` when unavailable.
    pub timestamp: String,
    /// Resolved repository slug, or `"n/a"` when unresolved.
    pub repo: String,
}

fn normalize_panel_kind(panel_kind: &str) -> String {
    let value = panel_kind.trim().to_lowercase();
    match value.as_str() {
        "design" | "plan-review" | "plan_review" => "design".to_owned(),
        "code-review" | "code_review" | "implement" | "review" => "code-review".to_owned(),
        "" => "unknown".to_owned(),
        _ => value,
    }
}

fn normalize_vote_cell(value: &str) -> &'static str {
    match value.trim().to_uppercase().as_str() {
        "YES" => "YES",
        "NO" | "EXONERATE" => "NO",
        _ => "",
    }
}

/// Validate one severity cell against the canonical buckets.
///
/// Legacy `blocker` maps to `major`; legacy `uncertain` maps to no bucket.
fn valid_panel_severity(token: &str) -> Option<&'static str> {
    let normalized = token.trim().to_lowercase();
    let normalized = match normalized.as_str() {
        "blocker" => "major",
        "uncertain" => "",
        other => other,
    };
    SEVERITY_BUCKETS
        .iter()
        .find(|bucket| **bucket == normalized)
        .copied()
}

/// Split non-blank lines into header names and per-row column maps.
///
/// Mirrors the Python `csv.DictReader` consumption of machine-written TSVs:
/// missing trailing cells read as empty, surplus cells are dropped, and a
/// duplicated header name keeps the rightmost column.
fn dict_rows_from_tsv(text: &str) -> (Vec<String>, Vec<BTreeMap<String, String>>) {
    let mut lines = text.lines().filter(|line| !line.trim().is_empty());
    let Some(header_line) = lines.next() else {
        return (Vec::new(), Vec::new());
    };
    let header: Vec<String> = header_line.split('\t').map(str::to_owned).collect();
    let rows = lines
        .map(|line| {
            let cells: Vec<&str> = line.split('\t').collect();
            let mut row = BTreeMap::new();
            for (index, name) in header.iter().enumerate() {
                row.insert(
                    name.clone(),
                    cells.get(index).copied().unwrap_or_default().to_owned(),
                );
            }
            row
        })
        .collect();
    (header, rows)
}

/// Return whether the classification header satisfies one supported schema.
#[must_use]
pub fn classification_tsv_schema_supported(text: &str, panel_kind: &str) -> bool {
    let panel = normalize_panel_kind(panel_kind);
    let (header, _rows) = dict_rows_from_tsv(text);
    if header.is_empty() {
        return false;
    }
    let header_set: std::collections::BTreeSet<&str> = header.iter().map(String::as_str).collect();
    match panel.as_str() {
        "design" => DESIGN_REQUIRED
            .iter()
            .all(|field| header_set.contains(field)),
        "code-review" => {
            let compact = code_review_classification_required_fields(false, false);
            let tool = code_review_classification_required_fields(true, true);
            compact
                .iter()
                .all(|field| header_set.contains(field.as_str()))
                || tool.iter().all(|field| header_set.contains(field.as_str()))
        }
        _ => false,
    }
}

struct RowPrep {
    row: BTreeMap<String, String>,
    panel: String,
    /// `(label, raw_vote)` per positional voter; labels are never empty.
    voter_votes: Vec<(String, String)>,
    voter_severities: Vec<String>,
}

fn voter_label(row: &BTreeMap<String, String>, pos: usize, panel: &str, compact: bool) -> String {
    if !compact {
        let tool = row
            .get(&format!("v{pos}_tool"))
            .map(|value| value.trim())
            .unwrap_or_default();
        if !tool.is_empty() {
            return tool.to_owned();
        }
    }
    if panel == "design" {
        return VOTER_FALLBACKS[pos - 1].to_owned();
    }
    if compact {
        return format!("v{pos}");
    }
    VOTER_FALLBACKS[pos - 1].to_owned()
}

fn classification_row_preps(text: &str, panel_kind: &str) -> Vec<RowPrep> {
    let panel = normalize_panel_kind(panel_kind);
    if !classification_tsv_schema_supported(text, &panel) {
        return Vec::new();
    }
    let (header, rows) = dict_rows_from_tsv(text);
    if header.is_empty() {
        return Vec::new();
    }
    let header_set: std::collections::BTreeSet<&str> = header.iter().map(String::as_str).collect();
    let label_compact = panel == "code-review"
        && !(1..=3).any(|pos| header_set.contains(format!("v{pos}_tool").as_str()));
    rows.into_iter()
        .map(|row| {
            let voter_votes = (1..=3)
                .map(|pos| {
                    (
                        voter_label(&row, pos, &panel, label_compact),
                        row.get(&format!("v{pos}_vote"))
                            .cloned()
                            .unwrap_or_default(),
                    )
                })
                .collect();
            let voter_severities = (1..=3)
                .map(|pos| {
                    row.get(&format!("v{pos}_severity"))
                        .cloned()
                        .unwrap_or_default()
                })
                .collect();
            RowPrep {
                row,
                panel: panel.clone(),
                voter_votes,
                voter_severities,
            }
        })
        .collect()
}

/// Build one agreement row from a panel verdict and its voter cells.
///
/// Returns `None` for neutral/other verdicts and for panels with fewer than
/// two parseable YES/NO cells, because agreement is undefined there.
#[must_use]
pub fn voter_agreement_row_from_panel(
    voting_result: &str,
    voter_votes: &[(String, String)],
    panel: &str,
    voter_severities: &[String],
) -> Option<AgreementRow> {
    let result = voting_result.trim().to_lowercase();
    if result != "accepted" && result != "rejected" {
        return None;
    }
    let parseable = voter_votes
        .iter()
        .filter(|(_label, vote)| !normalize_vote_cell(vote).is_empty())
        .count();
    if parseable < 2 {
        return None;
    }
    let mut voters = Vec::new();
    for (index, (raw_label, raw_vote)) in voter_votes.iter().enumerate() {
        let label = raw_label.trim();
        if label.is_empty() {
            continue;
        }
        let vote = normalize_vote_cell(raw_vote);
        let agrees =
            (result == "accepted" && vote == "YES") || (result == "rejected" && vote == "NO");
        voters.push(AgreementVoter {
            voter: label.to_owned(),
            vote: vote.to_owned(),
            agree: usize::from(!vote.is_empty() && agrees),
            disagree: usize::from(!vote.is_empty() && !agrees),
            missing: usize::from(vote.is_empty()),
            severity: voter_severities.get(index).cloned().unwrap_or_default(),
        });
    }
    if voters.is_empty() {
        return None;
    }
    Some(AgreementRow {
        panel: normalize_panel_kind(panel),
        voters,
    })
}

/// Parse one classification TSV into eligible agreement rows and counters.
#[must_use]
pub fn voter_agreement_rows_from_tsv(text: &str, panel_kind: &str) -> VoterAgreementTsvParse {
    let mut parse = VoterAgreementTsvParse::default();
    for prep in classification_row_preps(text, panel_kind) {
        let voting_result = prep.row.get("voting_result").cloned().unwrap_or_default();
        if let Some(row) = voter_agreement_row_from_panel(
            &voting_result,
            &prep.voter_votes,
            &prep.panel,
            &prep.voter_severities,
        ) {
            parse.rows.push(row);
            continue;
        }
        let result = voting_result.trim().to_lowercase();
        let parseable = prep
            .voter_votes
            .iter()
            .filter(|(_label, vote)| !normalize_vote_cell(vote).is_empty())
            .count();
        if result == "neutral" || ((result == "accepted" || result == "rejected") && parseable < 2)
        {
            parse.ineligible_rows += 1;
        } else {
            parse.malformed_rows += 1;
        }
    }
    parse
}

fn false_negative_scope_is_oos(row: &BTreeMap<String, String>) -> bool {
    let scope = row
        .get("scope")
        .map(|value| value.trim().to_lowercase())
        .unwrap_or_default();
    let finding_id = row
        .get("finding_id")
        .map(|value| value.trim().to_uppercase())
        .unwrap_or_default();
    FALSE_NEGATIVE_OOS_SCOPES.contains(&scope.as_str()) || finding_id.starts_with("OOS_")
}

/// Parse false-negative-eligible rows (accepted, neutral, rejected; in-scope;
/// at least two parseable votes) from one classification TSV.
#[must_use]
pub fn false_negative_rows_from_tsv(text: &str, panel_kind: &str) -> Vec<FalseNegativeRow> {
    let mut rows = Vec::new();
    for prep in classification_row_preps(text, panel_kind) {
        let result = prep
            .row
            .get("voting_result")
            .map(|value| value.trim().to_lowercase())
            .unwrap_or_default();
        if !FALSE_NEGATIVE_COUNTABLE.contains(&result.as_str()) {
            continue;
        }
        if false_negative_scope_is_oos(&prep.row) {
            continue;
        }
        let parseable: Vec<FalseNegativeVoter> = prep
            .voter_votes
            .iter()
            .filter(|(label, _vote)| !label.is_empty())
            .filter_map(|(label, vote)| {
                let normalized = normalize_vote_cell(vote);
                (!normalized.is_empty()).then(|| FalseNegativeVoter {
                    voter: label.clone(),
                    vote: normalized.to_owned(),
                })
            })
            .collect();
        if parseable.len() < 2 {
            continue;
        }
        rows.push(FalseNegativeRow {
            panel: prep.panel,
            voting_result: result,
            voters: parseable,
        });
    }
    rows
}

/// Aggregate agreement rows into per-`(panel, voter)` records.
#[must_use]
pub fn compute_voter_agreement(
    rows: &[AgreementRow],
    min_votes: i64,
    outlier_threshold: f64,
) -> Vec<VoterAgreementRecord> {
    let mut aggregate: BTreeMap<(String, String), VoterAgreementRecord> = BTreeMap::new();
    for row in rows {
        for voter in &row.voters {
            let name = voter.voter.trim();
            if name.is_empty() {
                continue;
            }
            let record = aggregate
                .entry((row.panel.clone(), name.to_owned()))
                .or_insert_with(|| VoterAgreementRecord {
                    panel: row.panel.clone(),
                    voter: name.to_owned(),
                    eligible: 0,
                    agree: 0,
                    disagree: 0,
                    missing: 0,
                    agreement_rate: None,
                    outlier: false,
                });
            record.agree += voter.agree;
            record.disagree += voter.disagree;
            record.missing += voter.missing;
            if voter.agree > 0 || voter.disagree > 0 {
                record.eligible += 1;
            }
        }
    }
    let mut records: Vec<VoterAgreementRecord> = aggregate.into_values().collect();
    for record in &mut records {
        let denominator = record.agree + record.disagree;
        #[allow(clippy::cast_precision_loss)] // Vote counts stay far below 2^52.
        let rate = (denominator > 0).then(|| record.agree as f64 / denominator as f64);
        record.agreement_rate = rate;
        record.outlier = i64::try_from(record.eligible).unwrap_or(i64::MAX) >= min_votes
            && rate.is_some_and(|value| value < outlier_threshold);
    }
    records
}

/// Snapshot TSV header written by `voter-calibration snapshot` and read by
/// `render voter` feedback injection.
pub const CALIBRATION_SNAPSHOT_HEADER: &[&str] = &[
    "tool",
    "yes_votes",
    "valid_yes_severity_count",
    "major",
    "minor",
    "nit",
    "missing_severity",
    "high_rate",
    "calibration_score",
    "uncalibrated",
];

/// One row from a voter-calibration snapshot TSV, keyed by base tool.
#[derive(Clone, Debug, PartialEq)]
pub struct VoterCalibrationStat {
    pub tool: String,
    pub yes_votes: usize,
    pub valid_yes_severity_count: usize,
    pub major: usize,
    pub minor: usize,
    pub nit: usize,
    pub missing_severity: usize,
    pub high_rate: Option<f64>,
    pub calibration_score: Option<f64>,
    pub uncalibrated: bool,
}

/// Map a voter label from a snapshot row onto `claude` / `codex` / `cursor`.
#[must_use]
pub fn normalize_voter_label_to_base_tool(label: &str) -> Option<&'static str> {
    let normalized = label.trim().to_ascii_lowercase();
    if normalized == "claude" {
        return Some("claude");
    }
    if normalized.starts_with("codex") {
        return Some("codex");
    }
    if normalized.starts_with("cursor") || normalized == "v1" {
        return Some("cursor");
    }
    if normalized == "v2" || normalized == "v3" {
        return Some("codex");
    }
    None
}

/// Read a voter-calibration snapshot TSV into per-tool stats.
///
/// Fail-closed: missing, empty, symlink, wrong-header, or malformed rows yield
/// an empty map (or omit that row). Matches Python
/// `larch.calibration.voter_calibration.read_voter_calibration_stats`.
#[must_use]
pub fn read_voter_calibration_stats(path: &Path) -> BTreeMap<String, VoterCalibrationStat> {
    use std::fs;

    let Ok(metadata) = fs::symlink_metadata(path) else {
        return BTreeMap::new();
    };
    if !metadata.is_file() || metadata.file_type().is_symlink() || metadata.len() == 0 {
        return BTreeMap::new();
    }
    let Ok(text) = fs::read_to_string(path) else {
        return BTreeMap::new();
    };
    let mut reader = csv::ReaderBuilder::new()
        .delimiter(b'\t')
        .flexible(true)
        .from_reader(text.as_bytes());
    let Ok(headers) = reader.headers().cloned() else {
        return BTreeMap::new();
    };
    if headers.iter().collect::<Vec<_>>() != CALIBRATION_SNAPSHOT_HEADER {
        return BTreeMap::new();
    }
    let mut stats = BTreeMap::new();
    for row in reader.records().flatten() {
        let cell = |name: &str| -> String {
            headers
                .iter()
                .position(|header| header == name)
                .and_then(|index| row.get(index))
                .unwrap_or("")
                .trim()
                .to_owned()
        };
        let Some(tool) = normalize_voter_label_to_base_tool(&cell("tool")) else {
            continue;
        };
        let parse_usize = |name: &str| -> Option<usize> { cell(name).parse().ok() };
        let Some(yes_votes) = parse_usize("yes_votes") else {
            continue;
        };
        let Some(valid_yes_severity_count) = parse_usize("valid_yes_severity_count") else {
            continue;
        };
        let Some(major) = parse_usize("major") else {
            continue;
        };
        let Some(minor) = parse_usize("minor") else {
            continue;
        };
        let Some(nit) = parse_usize("nit") else {
            continue;
        };
        let Some(missing_severity) = parse_usize("missing_severity") else {
            continue;
        };
        if valid_yes_severity_count == 0 {
            continue;
        }
        let parse_f64 = |name: &str| -> Option<f64> {
            let value = cell(name);
            if value.is_empty() {
                None
            } else {
                value.parse().ok()
            }
        };
        stats.insert(
            tool.to_owned(),
            VoterCalibrationStat {
                tool: tool.to_owned(),
                yes_votes,
                valid_yes_severity_count,
                major,
                minor,
                nit,
                missing_severity,
                high_rate: parse_f64("high_rate"),
                calibration_score: parse_f64("calibration_score"),
                uncalibrated: cell("uncalibrated").eq_ignore_ascii_case("true"),
            },
        );
    }
    stats
}

/// Score threshold excess linearly: `1.0` at or below the threshold, falling
/// to `0.0` as the high rate approaches `1.0`. Thresholds at or above `1.0`
/// never penalize.
#[must_use]
pub fn severity_calibration_score(high_rate: f64, high_severity_threshold: f64) -> f64 {
    if high_severity_threshold >= 1.0 {
        return 1.0;
    }
    let threshold = high_severity_threshold.max(0.0);
    if high_rate <= threshold {
        return 1.0;
    }
    let score = 1.0 - ((high_rate - threshold) / (1.0 - threshold));
    score.clamp(0.0, 1.0)
}

/// Aggregate YES-vote severity spread into per-`(panel, voter)` records.
#[must_use]
pub fn compute_voter_severity_distribution(
    rows: &[AgreementRow],
    high_severity_threshold: f64,
) -> Vec<VoterSeverityRecord> {
    let mut aggregate: BTreeMap<(String, String), VoterSeverityRecord> = BTreeMap::new();
    for row in rows {
        for voter in &row.voters {
            let name = voter.voter.trim();
            if name.is_empty() {
                continue;
            }
            let record = aggregate
                .entry((row.panel.clone(), name.to_owned()))
                .or_insert_with(|| VoterSeverityRecord {
                    panel: row.panel.clone(),
                    voter: name.to_owned(),
                    yes_votes: 0,
                    major: 0,
                    minor: 0,
                    nit: 0,
                    missing_severity: 0,
                    valid_yes_severity_count: 0,
                    high_rate: None,
                    calibration_score: None,
                    uncalibrated: false,
                });
            if voter.vote.trim().to_uppercase() != "YES" {
                continue;
            }
            record.yes_votes += 1;
            match valid_panel_severity(&voter.severity) {
                Some("major") => {
                    record.major += 1;
                    record.valid_yes_severity_count += 1;
                }
                Some("minor") => {
                    record.minor += 1;
                    record.valid_yes_severity_count += 1;
                }
                Some("nit") => {
                    record.nit += 1;
                    record.valid_yes_severity_count += 1;
                }
                _ => record.missing_severity += 1,
            }
        }
    }
    let mut records: Vec<VoterSeverityRecord> = aggregate.into_values().collect();
    for record in &mut records {
        if record.valid_yes_severity_count > 0 {
            #[allow(clippy::cast_precision_loss)] // Vote counts stay far below 2^52.
            let high_rate = record.major as f64 / record.valid_yes_severity_count as f64;
            record.high_rate = Some(high_rate);
            record.calibration_score = Some(severity_calibration_score(
                high_rate,
                high_severity_threshold,
            ));
            record.uncalibrated = high_rate > high_severity_threshold;
        }
    }
    records
}

fn compute_false_negative_yes_rates(rows: &[FalseNegativeRow]) -> Vec<FalseNegativeRecord> {
    let mut aggregate: BTreeMap<(String, String), FalseNegativeRecord> = BTreeMap::new();
    for row in rows {
        for voter in &row.voters {
            let name = voter.voter.trim();
            if name.is_empty() {
                continue;
            }
            let record = aggregate
                .entry((row.panel.clone(), name.to_owned()))
                .or_insert_with(|| FalseNegativeRecord {
                    panel: row.panel.clone(),
                    voter: name.to_owned(),
                    yes_votes: 0,
                    neutral_yes: 0,
                    rejected_yes: 0,
                    false_negative_yes: 0,
                    false_negative_yes_rate: None,
                });
            if voter.vote.to_uppercase() != "YES" {
                continue;
            }
            record.yes_votes += 1;
            if row.voting_result == "neutral" {
                record.neutral_yes += 1;
            } else if row.voting_result == "rejected" {
                record.rejected_yes += 1;
            }
        }
    }
    let mut records: Vec<FalseNegativeRecord> = aggregate.into_values().collect();
    for record in &mut records {
        record.false_negative_yes = record.neutral_yes + record.rejected_yes;
        #[allow(clippy::cast_precision_loss)] // Vote counts stay far below 2^52.
        let rate = (record.yes_votes > 0)
            .then(|| record.false_negative_yes as f64 / record.yes_votes as f64);
        record.false_negative_yes_rate = rate;
    }
    records
}

/// Render a float the way Python `f"{value:.3f}"` does, or `n/a` for `None`.
fn format_rate(value: Option<f64>) -> String {
    value.map_or_else(|| "n/a".to_owned(), |value| py_float(value, 3))
}

/// Format with a fixed precision, matching Python's lowercase specials.
fn py_float(value: f64, precision: usize) -> String {
    if value.is_nan() {
        return "nan".to_owned();
    }
    if value.is_infinite() {
        return if value < 0.0 { "-inf" } else { "inf" }.to_owned();
    }
    format!("{value:.precision$}")
}

fn agreement_table(records: &[&VoterAgreementRecord]) -> String {
    let mut lines = vec![
        "| Panel | Voter | Eligible | Agree | Disagree | Missing | Agreement | Outlier |"
            .to_owned(),
        "|---|---|---:|---:|---:|---:|---:|---|".to_owned(),
    ];
    if records.is_empty() {
        lines.push("| n/a | n/a | 0 | 0 | 0 | 0 | n/a | false |".to_owned());
        return lines.join("\n");
    }
    for record in records {
        lines.push(format!(
            "| {} | {} | {} | {} | {} | {} | {} | {} |",
            record.panel,
            record.voter,
            record.eligible,
            record.agree,
            record.disagree,
            record.missing,
            format_rate(record.agreement_rate),
            record.outlier,
        ));
    }
    lines.join("\n")
}

/// Render the `## Voter Severity Scoreboard` section (with trailing newline).
#[must_use]
pub fn render_voter_severity_scoreboard(records: &[VoterSeverityRecord]) -> String {
    let mut buf = String::from("## Voter Severity Scoreboard\n\n");
    buf.push_str(
        "| Panel | Voter | YES Votes | Major | Minor | Nit | Missing Severity | High Rate | Calibration Score | Uncalibrated |\n",
    );
    buf.push_str("|---|---|---:|---:|---:|---:|---:|---:|---:|---|\n");
    if records.is_empty() {
        buf.push_str("| undefined | n/a | 0 | 0 | 0 | 0 | 0 | n/a | n/a | false |\n");
        buf.push_str(
            "\nSeverity calibration is undefined when no accepted or rejected finding has at least two parseable YES/NO voter cells.\n",
        );
        return buf;
    }
    for record in records {
        let _ = writeln!(
            buf,
            "| {} | {} | {} | {} | {} | {} | {} | {} | {} | {} |",
            record.panel,
            record.voter,
            record.yes_votes,
            record.major,
            record.minor,
            record.nit,
            record.missing_severity,
            format_rate(record.high_rate),
            format_rate(record.calibration_score),
            record.uncalibrated,
        );
    }
    buf
}

fn false_negative_yes_table(rows: &[FalseNegativeRow]) -> String {
    let mut lines = vec![
        "| Panel | Voter | YES Votes | Neutral YES | Rejected YES | False-negative YES | False-negative YES Rate |"
            .to_owned(),
        "|---|---|---:|---:|---:|---:|---:|".to_owned(),
    ];
    let records = compute_false_negative_yes_rates(rows);
    if records.is_empty() {
        lines.push("| n/a | n/a | 0 | 0 | 0 | 0 | n/a |".to_owned());
        return lines.join("\n");
    }
    for record in records {
        lines.push(format!(
            "| {} | {} | {} | {} | {} | {} | {} |",
            record.panel,
            record.voter,
            record.yes_votes,
            record.neutral_yes,
            record.rejected_yes,
            record.false_negative_yes,
            format_rate(record.false_negative_yes_rate),
        ));
    }
    lines.join("\n")
}

fn global_agreement_rows(rows: &[AgreementRow]) -> Vec<AgreementRow> {
    rows.iter()
        .map(|row| AgreementRow {
            panel: "global".to_owned(),
            voters: row.voters.clone(),
        })
        .collect()
}

fn global_false_negative_rows(rows: &[FalseNegativeRow]) -> Vec<FalseNegativeRow> {
    rows.iter()
        .map(|row| FalseNegativeRow {
            panel: "global".to_owned(),
            voting_result: row.voting_result.clone(),
            voters: row.voters.clone(),
        })
        .collect()
}

/// Render the boundary-unavailable era report (with trailing newline).
#[must_use]
pub fn render_era_boundary_unavailable(
    log_root: &str,
    source: &str,
    repo: &str,
    reason: &str,
) -> String {
    let reason = if reason.is_empty() { "unknown" } else { reason };
    let lines = [
        "# Voter Calibration Report".to_owned(),
        String::new(),
        "## Era Boundary Unavailable".to_owned(),
        String::new(),
        "- Era segmentation needs an incentive boundary timestamp.".to_owned(),
        format!("- Log root: `{log_root}`"),
        format!("- Boundary source attempted: `{source}`"),
        format!("- Resolved repo: `{repo}`"),
        format!("- Reason: `{reason}`"),
        "- Pass `--era-since-date YYYY-MM-DD` to choose a manual UTC midnight cutoff.".to_owned(),
        "- This report is diagnostic only.".to_owned(),
    ];
    let mut text = lines.join("\n");
    text.push('\n');
    text
}

fn render_era_slice(
    title: &str,
    corpus: &VoterCalibrationCorpus,
    min_votes: i64,
    outlier_threshold: f64,
    high_severity_threshold: f64,
) -> String {
    let records = compute_voter_agreement(&corpus.rows, min_votes, outlier_threshold);
    let severity_records =
        compute_voter_severity_distribution(&corpus.rows, high_severity_threshold);
    let mut false_negative_rows = corpus.false_negative_rows.clone();
    false_negative_rows.extend(global_false_negative_rows(&corpus.false_negative_rows));
    let record_refs: Vec<&VoterAgreementRecord> = records.iter().collect();
    let lines = [
        format!("## {title}"),
        String::new(),
        format!("- Classification TSV files scanned: {}", corpus.files_seen),
        format!(
            "- Malformed or unsupported TSV files skipped: {}",
            corpus.skipped_files
        ),
        format!("- Malformed data rows dropped: {}", corpus.malformed_rows),
        format!("- Ineligible panels excluded: {}", corpus.ineligible_rows),
        format!(
            "- Qualifying accepted/rejected panels: {}",
            corpus.rows.len()
        ),
        String::new(),
        "## Agreement Table".to_owned(),
        String::new(),
        agreement_table(&record_refs),
        String::new(),
        render_voter_severity_scoreboard(&severity_records),
        String::new(),
        "## Per-voter False-negative YES Rate".to_owned(),
        String::new(),
        false_negative_yes_table(&false_negative_rows),
    ];
    lines.join("\n")
}

/// Render the era-segmented report (with trailing newline).
#[expect(
    clippy::too_many_arguments,
    reason = "the argument list mirrors the frozen Python renderer signature"
)]
#[must_use]
pub fn render_voter_calibration_era_report(
    log_root: &str,
    era: &str,
    boundary: &EraBoundaryDisplay,
    pre: &VoterCalibrationCorpus,
    post: &VoterCalibrationCorpus,
    discovered_count: usize,
    excluded_missing_started_at_runs: usize,
    min_votes: i64,
    outlier_threshold: f64,
    high_severity_threshold: f64,
    realized_outcomes_markdown: &str,
) -> String {
    let mut lines = vec![
        "# Voter Calibration Report".to_owned(),
        String::new(),
        "## Era Boundary".to_owned(),
        String::new(),
        format!("- Log root: `{log_root}`"),
        format!("- Boundary source: `{}`", boundary.source),
        format!("- Boundary timestamp: `{}`", boundary.timestamp),
        format!("- Resolved repo: `{}`", boundary.repo),
        format!("- Classification TSV files discovered: {discovered_count}"),
        format!(
            "- Runs excluded for missing or invalid `started_at`: {excluded_missing_started_at_runs}"
        ),
        "- Runs before the boundary are pre-incentive. Runs at or after it are post-incentive."
            .to_owned(),
        String::new(),
    ];
    if era == "all" || era == "pre" {
        lines.push(render_era_slice(
            "Pre-incentive era",
            pre,
            min_votes,
            outlier_threshold,
            high_severity_threshold,
        ));
    }
    if era == "all" || era == "post" {
        if era == "all" {
            lines.push(String::new());
        }
        lines.push(render_era_slice(
            "Post-incentive era",
            post,
            min_votes,
            outlier_threshold,
            high_severity_threshold,
        ));
    }
    if !realized_outcomes_markdown.is_empty() {
        lines.push(String::new());
        lines.push(realized_outcomes_markdown.trim_end().to_owned());
    }
    lines.extend([
        String::new(),
        "## Notes".to_owned(),
        String::new(),
        "- Era segmentation is diagnostic only.".to_owned(),
        "- Empty, missing, and `JUDGE_ERROR` voter cells count as missing, not disagreement."
            .to_owned(),
        "- Severity calibration counts only YES votes with valid severity buckets.".to_owned(),
    ]);
    let mut text = lines.join("\n");
    text.push('\n');
    text
}

/// Render the core (non-era) report (with trailing newline).
#[must_use]
pub fn render_voter_calibration_report(
    log_root: &str,
    corpus: &VoterCalibrationCorpus,
    min_votes: i64,
    outlier_threshold: f64,
    high_severity_threshold: f64,
    realized_outcomes_markdown: &str,
) -> String {
    let records = compute_voter_agreement(&corpus.rows, min_votes, outlier_threshold);
    let global_records = compute_voter_agreement(
        &global_agreement_rows(&corpus.rows),
        min_votes,
        outlier_threshold,
    );
    let severity_records =
        compute_voter_severity_distribution(&corpus.rows, high_severity_threshold);
    let global_severity_records = compute_voter_severity_distribution(
        &global_agreement_rows(&corpus.rows),
        high_severity_threshold,
    );
    let mut false_negative_records = corpus.false_negative_rows.clone();
    false_negative_records.extend(global_false_negative_rows(&corpus.false_negative_rows));
    let outliers: Vec<&VoterAgreementRecord> = records
        .iter()
        .chain(global_records.iter())
        .filter(|record| record.outlier)
        .collect();
    let mut missing: Vec<&VoterAgreementRecord> = records.iter().collect();
    missing.sort_by_key(|record| std::cmp::Reverse(record.missing));
    let record_refs: Vec<&VoterAgreementRecord> = records.iter().collect();
    let global_refs: Vec<&VoterAgreementRecord> = global_records.iter().collect();

    let mut lines = vec![
        "# Voter Calibration Report".to_owned(),
        String::new(),
        "## Corpus".to_owned(),
        String::new(),
        format!("- Log root: `{log_root}`"),
        format!("- Classification TSV files scanned: {}", corpus.files_seen),
        format!(
            "- Malformed or unsupported TSV files skipped: {}",
            corpus.skipped_files
        ),
        format!("- Malformed data rows dropped: {}", corpus.malformed_rows),
        format!("- Ineligible panels excluded: {}", corpus.ineligible_rows),
        format!(
            "- Qualifying accepted/rejected panels: {}",
            corpus.rows.len()
        ),
        String::new(),
        "## Agreement Table".to_owned(),
        String::new(),
        agreement_table(&record_refs),
        String::new(),
        render_voter_severity_scoreboard(&severity_records),
        String::new(),
        "## Global Voter Agreement".to_owned(),
        String::new(),
        agreement_table(&global_refs),
        String::new(),
        render_voter_severity_scoreboard(&global_severity_records),
        String::new(),
        format!(
            "## Chronic Outliers (threshold < {}, min votes {min_votes})",
            py_float(outlier_threshold, 2)
        ),
        String::new(),
        agreement_table(&outliers),
        String::new(),
        "## Missing Vote Table".to_owned(),
        String::new(),
        agreement_table(&missing),
        String::new(),
        "## Per-voter False-negative YES Rate".to_owned(),
        String::new(),
        false_negative_yes_table(&false_negative_records),
        String::new(),
    ];
    if !realized_outcomes_markdown.is_empty() {
        lines.push(realized_outcomes_markdown.trim_end().to_owned());
        lines.push(String::new());
    }
    lines.extend([
        "## Notes".to_owned(),
        String::new(),
        "- Neutral panel verdicts are excluded from agreement denominators.".to_owned(),
        "- Single-voter and zero-voter panels are excluded because agreement is undefined."
            .to_owned(),
        "- Empty, missing, and `JUDGE_ERROR` voter cells count as missing, not disagreement."
            .to_owned(),
        "- `agreement_rate` uses `agree / (agree + disagree)`; missing votes are excluded."
            .to_owned(),
        "- Severity calibration counts only YES votes with valid severity buckets; missing and invalid severities are reported separately."
            .to_owned(),
        "- The severity scoreboard emits a voter-side Calibration Score from the High Rate threshold excess."
            .to_owned(),
        "- False-negative YES totals include neutral and rejected eligible panels, while agreement denominators still exclude neutral panels."
            .to_owned(),
        "- This report is diagnostic only. Agreement, severity calibration, and false-negative diagnostics do not affect reviewer/proposer points, spawning, thresholds, tokens, or live panel verdicts."
            .to_owned(),
    ]);
    let mut text = lines.join("\n");
    text.push('\n');
    text
}

#[cfg(test)]
mod tests {
    use super::*;

    const DESIGN_HEADER: &str = "finding_id\tfinding_reviewers\tvoting_result\tv1_vote\tv1_correctness\tv1_severity\tv1_quality\tv1_uncertain\tv1_tool\tv2_vote\tv2_correctness\tv2_severity\tv2_quality\tv2_uncertain\tv2_tool\tv3_vote\tv3_correctness\tv3_severity\tv3_quality\tv3_uncertain\tv3_tool\tbody_severity";
    const COMPACT_HEADER: &str = "finding_id\treviewer_slots\tvoting_result\tv1_vote\tv1_correctness\tv1_severity\tv1_quality\tv1_uncertain\tv2_vote\tv2_correctness\tv2_severity\tv2_quality\tv2_uncertain\tv3_vote\tv3_correctness\tv3_severity\tv3_quality\tv3_uncertain";

    fn design_row(result: &str, votes: [&str; 3], severities: [&str; 3]) -> String {
        format!(
            "F1\tR\t{result}\t{}\t\t{}\t\t\tClaude\t{}\t\t{}\t\t\tCodex\t{}\t\t{}\t\t\tCursor\tmajor",
            votes[0], severities[0], votes[1], severities[1], votes[2], severities[2],
        )
    }

    #[test]
    fn exonerate_normalizes_to_no_and_unknown_votes_are_missing() {
        assert_eq!(normalize_vote_cell(" exonerate "), "NO");
        assert_eq!(normalize_vote_cell("yes"), "YES");
        assert_eq!(normalize_vote_cell("JUDGE_ERROR"), "");
        assert_eq!(normalize_vote_cell(""), "");
    }

    #[test]
    fn legacy_severity_spellings_map_into_canonical_buckets() {
        assert_eq!(valid_panel_severity(" Blocker "), Some("major"));
        assert_eq!(valid_panel_severity("uncertain"), None);
        assert_eq!(valid_panel_severity("nit"), Some("nit"));
        assert_eq!(valid_panel_severity("latent"), None);
    }

    #[test]
    fn schema_detection_accepts_each_documented_header_shape() {
        let design = format!("{DESIGN_HEADER}\n");
        assert!(classification_tsv_schema_supported(&design, "design"));
        let compact = format!("{COMPACT_HEADER}\n");
        assert!(classification_tsv_schema_supported(&compact, "code-review"));
        assert!(!classification_tsv_schema_supported(&compact, "design"));
        assert!(!classification_tsv_schema_supported(
            "finding_id\tvoting_result\n",
            "code-review"
        ));
    }

    #[test]
    fn compact_code_review_rows_fall_back_to_positional_voter_labels() {
        let text = format!(
            "{COMPACT_HEADER}\nF1\tR\taccepted\tYES\t\tmajor\t\t\tNO\t\tnit\t\t\tYES\t\tminor\t\t\n"
        );
        let parse = voter_agreement_rows_from_tsv(&text, "review");
        assert_eq!(parse.rows.len(), 1);
        let voters: Vec<&str> = parse.rows[0]
            .voters
            .iter()
            .map(|voter| voter.voter.as_str())
            .collect();
        assert_eq!(voters, ["v1", "v2", "v3"]);
        assert_eq!(parse.rows[0].panel, "code-review");
    }

    #[test]
    fn neutral_and_single_vote_rows_count_as_ineligible_and_bogus_as_malformed() {
        let text = format!(
            "{DESIGN_HEADER}\n{}\n{}\n{}\n",
            design_row("neutral", ["YES", "NO", "NO"], ["major", "nit", "nit"]),
            design_row("accepted", ["YES", "", ""], ["major", "", ""]),
            design_row("bogus", ["YES", "NO", "NO"], ["major", "nit", "nit"]),
        );
        let parse = voter_agreement_rows_from_tsv(&text, "design");
        assert!(parse.rows.is_empty());
        assert_eq!(parse.ineligible_rows, 2);
        assert_eq!(parse.malformed_rows, 1);
    }

    #[test]
    fn agreement_and_outlier_math_match_the_python_thresholds() {
        let text = format!(
            "{DESIGN_HEADER}\n{}\n",
            design_row("rejected", ["NO", "YES", "NO"], ["nit", "major", "minor"]),
        );
        let parse = voter_agreement_rows_from_tsv(&text, "design");
        let records = compute_voter_agreement(&parse.rows, 1, 0.5);
        let codex = records
            .iter()
            .find(|record| record.voter == "Codex")
            .expect("codex record");
        assert_eq!((codex.agree, codex.disagree, codex.eligible), (0, 1, 1));
        assert_eq!(codex.agreement_rate, Some(0.0));
        assert!(codex.outlier);
        let claude = records
            .iter()
            .find(|record| record.voter == "Claude")
            .expect("claude record");
        assert_eq!(claude.agreement_rate, Some(1.0));
        assert!(!claude.outlier);
    }

    #[test]
    fn calibration_score_declines_linearly_and_never_divides_by_zero() {
        assert!((severity_calibration_score(0.9, 0.9) - 1.0).abs() < 1e-9);
        assert!((severity_calibration_score(0.95, 0.9) - 0.5).abs() < 1e-9);
        assert!(severity_calibration_score(1.0, 0.9).abs() < 1e-9);
        assert!((severity_calibration_score(1.0, 1.0) - 1.0).abs() < 1e-9);
        assert!((severity_calibration_score(0.4, -1.0) - 0.6).abs() < 1e-9);
    }

    #[test]
    fn oos_scoped_rows_stay_out_of_false_negative_totals() {
        let header =
            "finding_id\tfinding_reviewers\tvoting_result\tv1_vote\tv2_vote\tv3_vote\tscope";
        let text = format!(
            "{header}\nF1\tR\tneutral\tYES\tNO\tNO\t\nF2\tR\tneutral\tYES\tNO\tNO\toos\nOOS_3\tR\tneutral\tYES\tNO\tNO\t\n"
        );
        let rows = false_negative_rows_from_tsv(&text, "design");
        assert_eq!(rows.len(), 1);
        assert_eq!(rows[0].voting_result, "neutral");
        assert_eq!(rows[0].voters.len(), 3);
    }

    #[test]
    fn empty_corpus_renders_the_undefined_placeholders() {
        let corpus = VoterCalibrationCorpus::default();
        let report = render_voter_calibration_report("/logs", &corpus, 20, 0.5, 0.9, "");
        assert!(report.contains("| n/a | n/a | 0 | 0 | 0 | 0 | n/a | false |"));
        assert!(report.contains("## Chronic Outliers (threshold < 0.50, min votes 20)"));
        assert!(report.ends_with("live panel verdicts.\n"));
    }

    #[test]
    fn skipped_file_counting_requires_missing_schema_or_header_token() {
        let mut corpus = VoterCalibrationCorpus::default();
        corpus.add_file("design", "finding_id\tother\nF1\tx\n");
        assert_eq!(corpus.skipped_files, 1);
        let neutral_only = format!(
            "{DESIGN_HEADER}\n{}\n",
            design_row("neutral", ["YES", "NO", "NO"], ["major", "nit", "nit"]),
        );
        corpus.add_file("design", &neutral_only);
        assert_eq!(corpus.skipped_files, 1);
        assert_eq!(corpus.files_seen, 2);
        assert_eq!(corpus.ineligible_rows, 1);
    }
}
