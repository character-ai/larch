//! Side-effect-free parity contracts for plan-review rounds.
//!
//! Python remains the production owner until the later command-cutover leaf.
//! This module keeps the shared wire layout, finding normalization, and round
//! state transitions in one Rust owner for that future boundary.

use std::{
    collections::{BTreeMap, BTreeSet},
    fmt::Write as _,
    path::{Path, PathBuf},
    sync::LazyLock,
};

use regex::Regex;

use super::{BoundaryMode, ItemKind, parse_blocks, pipeline::normalize_output_base};

/// Default maximum number of plan-review rounds.
pub const ROUND_CAP: u64 = 2;
/// Maximum ordinary rounds before an explicitly authorized escalation.
pub const ROUND_THREE_AUTHORIZATION_CAP: u64 = 2;
/// Plan diff size at which continuation policy considers a change structural.
pub const STRUCTURAL_DIFF_LINE_THRESHOLD: u64 = 500;
/// Plan line count at which continuation policy considers a change structural.
pub const STRUCTURAL_PLAN_LINE_THRESHOLD: u64 = 120;
/// New non-nit findings required to continue a review round.
pub const NON_NIT_CONTINUE_THRESHOLD: usize = 5;
/// Minimum review rounds for a structural plan with material findings.
pub const STRUCTURAL_MIN_REVIEW_ROUNDS: u64 = 2;
/// Maximum OOS proposals retained for one reviewer slot.
pub const PER_REVIEWER_OOS_PROPOSAL_CAP: usize = 3;

/// Keys accepted while normalizing a Step 3 result environment.
pub const STEP3_NORMALIZE_ALLOW_KEYS: [&str; 23] = [
    "NEXT_ACTION",
    "BGJOB_RC",
    "LOOP_STATUS",
    "STEP3_REVIEW_LOOP_STATUS",
    "POSTPLAN_RC",
    "DEDUP_RC",
    "PLAN_REVIEW_CONTINUE_REASON",
    "FINAL_ROUND_NUM",
    "ACCEPTED_COUNT",
    "IMPORTANT_ACCEPTED_COUNT",
    "DEGRADED_PANEL",
    "DEGRADED_PANEL_WARNING",
    "INVALID_SLOT_PANEL_WARNING",
    "ROUNDS_COMPLETED",
    "TALLY_PLAN_REVIEW_STATUS",
    "AGGREGATOR_STATUS",
    "VOTING_TALLY_FILE",
    "SCOPE_ANCHOR_FILE",
    "STEP3_REVIEW_CAP_REACHED",
    "STEP3_REVIEW_ROUND_NUM",
    "ROUND_NUM",
    "REVIEW_ROUND_COUNT",
    "REASON",
];

/// Keys carried from an existing Step 3 result environment when not re-emitted.
pub const MERGE_KEYS: [&str; 10] = [
    "TALLY_PLAN_REVIEW_STATUS",
    "IMPORTANT_ACCEPTED_COUNT",
    "AGGREGATOR_STATUS",
    "VOTING_TALLY_FILE",
    "PANEL_PRUNED_EMPTY",
    "DEGRADED_PANEL_WARNING",
    "INVALID_SLOT_PANEL_WARNING",
    "ROUND_NUM",
    "PLAN_REVIEW_CONTINUE_REASON",
    "REASON",
];

/// Warning keys carried between Step 3 round envelopes.
pub const STEP3_ROUND_CARRY_KEYS: [&str; 2] =
    ["DEGRADED_PANEL_WARNING", "INVALID_SLOT_PANEL_WARNING"];

/// Remove carriage returns and newlines before emitting one `KEY=value` value.
#[must_use]
pub fn strip_crlf(value: &str) -> String {
    value.replace(['\r', '\n'], "")
}

/// Select Step 3 warnings to carry into a later result envelope.
#[must_use]
pub fn step3_round_carry_values(
    degraded_exit: bool,
    degraded_values: &BTreeMap<String, String>,
) -> BTreeMap<String, String> {
    if degraded_exit {
        return degraded_values.clone();
    }
    STEP3_ROUND_CARRY_KEYS
        .iter()
        .filter_map(|key| {
            degraded_values
                .get(*key)
                .filter(|value| !value.is_empty())
                .map(|value| ((*key).to_owned(), value.clone()))
        })
        .collect()
}

/// Merge carried Step 3 warnings only where a fresh envelope has no value.
#[must_use]
pub fn merge_step3_round_carry_warnings(
    values: &BTreeMap<String, String>,
    carry: &BTreeMap<String, String>,
) -> BTreeMap<String, String> {
    let mut merged = values.clone();
    for key in STEP3_ROUND_CARRY_KEYS {
        if merged.get(key).is_none_or(String::is_empty)
            && let Some(value) = carry.get(key).filter(|value| !value.is_empty())
        {
            merged.insert(key.to_owned(), value.clone());
        }
    }
    merged
}

/// Exact filesystem layout for one plan-review round.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct PlanReviewRoundArtifacts {
    root: PathBuf,
    round_num: u64,
}

impl PlanReviewRoundArtifacts {
    fn round_file(&self, name: &str) -> PathBuf {
        self.round_dir().join(name)
    }

    fn root_file(&self, name: &str) -> PathBuf {
        self.root.join(name)
    }

    /// Construct the layout rooted at one design temporary directory.
    #[must_use]
    pub fn new(root: impl Into<PathBuf>, round_num: u64) -> Self {
        Self {
            root: root.into(),
            round_num,
        }
    }

    /// Return the design temporary directory.
    #[must_use]
    pub fn root(&self) -> &Path {
        &self.root
    }

    /// Return the round number represented by this layout.
    #[must_use]
    pub const fn round_num(&self) -> u64 {
        self.round_num
    }

    /// Return `plan-review/round-N`.
    #[must_use]
    pub fn round_dir(&self) -> PathBuf {
        self.root
            .join("plan-review")
            .join(format!("round-{}", self.round_num))
    }

    /// Return the round-local reviewer status TSV path.
    #[must_use]
    pub fn reviewer_status_tsv(&self) -> PathBuf {
        self.round_file("reviewer-status.tsv")
    }

    /// Return the round-local rendered reviewer status table path.
    #[must_use]
    pub fn reviewer_status_table(&self) -> PathBuf {
        self.round_file("reviewer-status-table.txt")
    }

    /// Return the per-round `KEY=value` summary path.
    #[must_use]
    pub fn round_summary_env(&self) -> PathBuf {
        self.round_file("round-summary.env")
    }

    /// Return the round-local tally classification path.
    #[must_use]
    pub fn findings_classification_tsv(&self) -> PathBuf {
        self.round_file("findings-classification.tsv")
    }

    /// Return the OOS pre-vote pruning audit path.
    #[must_use]
    pub fn oos_dropped_before_vote(&self) -> PathBuf {
        self.round_file("oos-dropped-before-vote.md")
    }

    /// Return the round start-time artifact path.
    #[must_use]
    pub fn round_start_s(&self) -> PathBuf {
        self.round_file("round-start-s")
    }

    /// Return the shared slot manifest path.
    #[must_use]
    pub fn slots_manifest(&self) -> PathBuf {
        self.root_file("plan-review-slots.ndjson")
    }

    /// Return the shared collector result path.
    #[must_use]
    pub fn collector_results(&self) -> PathBuf {
        self.root_file("collector-results.env")
    }

    /// Return the latest reviewer-status compatibility copy.
    #[must_use]
    pub fn latest_reviewer_status_tsv(&self) -> PathBuf {
        self.root_file("latest-reviewer-status.tsv")
    }

    /// Return the stable chat-ready reviewer status table path.
    #[must_use]
    pub fn stable_reviewer_status_table(&self) -> PathBuf {
        self.root_file("reviewer-status-table.txt")
    }

    /// Return the persisted Step 3 result environment path.
    #[must_use]
    pub fn step3_result_env(&self) -> PathBuf {
        self.root_file(".step3-review-result.env")
    }

    /// Return the review round count path.
    #[must_use]
    pub fn review_round_count(&self) -> PathBuf {
        self.root_file("review-round-count.txt")
    }
}

/// One valid plan-review launcher-manifest row.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct PlanReviewManifestSlot {
    pub slot: String,
    pub tool: String,
    pub output: String,
    pub agent: String,
    pub prompt_file: String,
}

impl PlanReviewManifestSlot {
    /// Return whether this row satisfies Python's plan-review manifest predicate.
    #[must_use]
    pub fn is_valid(&self) -> bool {
        !self.slot.is_empty()
            && matches!(self.tool.as_str(), "codex" | "cursor")
            && !self.output.is_empty()
            && !self.output.contains(['\n', '\r'])
            && (self.agent.is_empty() != self.prompt_file.is_empty())
    }
}

/// One normalized structured finding produced by a reviewer sidecar.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct PlanReviewStructuredFinding {
    pub scope: String,
    pub severity: String,
    pub focus_area: String,
    pub location: String,
    pub what: String,
    pub scenario_or_breakage: String,
    pub suggested_fix: String,
}

/// One collector record enriched with any parsed structured sidecar rows.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct PlanReviewCollectorRecord {
    pub reviewer_file: String,
    pub tool: String,
    pub status: String,
    pub structured_findings: Vec<PlanReviewStructuredFinding>,
}

/// Normalized Markdown and accounting from collector records.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct PlanReviewFindingOutput {
    pub in_scope_markdown: String,
    pub out_of_scope_markdown: String,
    pub ok_count: usize,
    pub failure_count: usize,
}

/// One accepted in-scope finding shared with Gate B renderers.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct PlanReviewAcceptedFinding {
    pub finding_id: String,
    pub block: String,
    pub severity_raw: String,
    pub concern: String,
    pub reviewers: String,
}

/// Gate B severity counts and presentation order.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct PlanReviewGateBSeveritySummary {
    pub mode: String,
    pub critical_count: usize,
    pub high_count: usize,
    pub medium_count: usize,
    pub low_count: usize,
    pub display_labels: BTreeMap<String, String>,
    pub finding_ids: Vec<String>,
}

/// Fields for one Gate B prompt row.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct PlanReviewGateBDisplayRow {
    pub finding_id: String,
    pub display_severity_label: String,
    pub reviewer_text: String,
    pub excerpt: String,
}

static CONCERN_FIELD: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?mi)^-[\s\x{1c}-\x{1f}]+(?:\*\*)?Concern(?:\*\*)?:[\s\x{1c}-\x{1f}]*(.*)$")
        .expect("static concern regex")
});
static FIELD_BOUNDARY: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^(?:-[\s\x{1c}-\x{1f}]+|###[\s\x{1c}-\x{1f}]+)")
        .expect("static field boundary regex")
});
static REVIEWER_FIELD: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(
        r"(?mi)^-[\s\x{1c}-\x{1f}]+(?:\*\*)?Reviewer(?:\(s\))?(?:\*\*)?:[\s\x{1c}-\x{1f}]*(.*)$",
    )
    .expect("static reviewer regex")
});
static SEVERITY_FIELD: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?mi)^-[\s\x{1c}-\x{1f}]+\*\*Severity\*\*:[\s\x{1c}-\x{1f}]*([A-Za-z_-]+)[\s\x{1c}-\x{1f}]*$").expect("static severity regex")
});
static GATE_B_FALLBACK_PREDICATES: LazyLock<Vec<(&'static str, Regex)>> = LazyLock::new(|| {
    [
        ("Low", r"\b(style|naming|future[- ]proofing|no functional change)\b"),
        ("Medium", r"\b(robustness|clarity|secondary path|recoverable edge case)\b"),
        ("High", r"\b(functional incorrectness|primary code path|missing required documentation contract|missing required[^.]*doc|violates?[^.]*invariant|stated invariant)\b"),
        ("Critical", r"\b(data loss|security breach|build/ci breakage|build breakage|ci breakage|breaks (?:the )?build|breaks ci|downstream[^.]*regression|regression[^.]*downstream)\b"),
    ]
    .into_iter()
    .map(|(label, pattern)| (label, Regex::new(pattern).expect("static Gate B regex")))
    .collect()
});

/// Parse the byte-frozen accepted-finding document consumed by Gate B.
#[must_use]
pub fn parse_plan_review_accepted_findings(text: &str) -> Vec<PlanReviewAcceptedFinding> {
    let field = |block: &str| {
        let Some(found) = CONCERN_FIELD.captures(block) else {
            return String::new();
        };
        let Some(matched) = found.get(0) else {
            return String::new();
        };
        let mut lines = vec![crate::trim_python_whitespace(&found[1]).to_owned()];
        for line in crate::split_text_lines(&block[matched.end()..]) {
            if FIELD_BOUNDARY.is_match(line) {
                break;
            }
            if !crate::trim_python_whitespace(line).is_empty() {
                lines.push(crate::trim_python_whitespace(line).to_owned());
            }
        }
        crate::trim_python_whitespace(&lines.join("\n")).to_owned()
    };
    parse_blocks(text, BoundaryMode::LevelThreeHeading)
        .into_iter()
        .filter(|block| block.kind == ItemKind::Finding)
        .filter_map(|parsed| {
            let digits = parsed.item_id.strip_prefix("FINDING_")?;
            let finding_id = digits.trim_start_matches('0');
            let finding_id = if finding_id.is_empty() {
                "0"
            } else {
                finding_id
            };
            Some(PlanReviewAcceptedFinding {
                finding_id: finding_id.to_owned(),
                concern: field(&parsed.block),
                reviewers: REVIEWER_FIELD
                    .captures(&parsed.block)
                    .map_or_else(String::new, |found| {
                        crate::trim_python_whitespace(&found[1]).to_owned()
                    }),
                severity_raw: SEVERITY_FIELD
                    .captures(&parsed.block)
                    .map_or_else(String::new, |found| found[1].to_lowercase()),
                block: parsed.block,
            })
        })
        .collect()
}

/// Classify Gate B severity using the structured-all-or-fallback contract.
#[must_use]
pub fn classify_plan_review_gate_b(
    findings: &[PlanReviewAcceptedFinding],
) -> PlanReviewGateBSeveritySummary {
    let structured = findings
        .iter()
        .all(|finding| matches!(finding.severity_raw.as_str(), "major" | "minor" | "nit"));
    let mut summary = PlanReviewGateBSeveritySummary {
        mode: if structured { "structured" } else { "fallback" }.to_owned(),
        finding_ids: findings
            .iter()
            .map(|finding| finding.finding_id.clone())
            .collect(),
        ..Default::default()
    };
    for finding in findings {
        let label = if structured {
            match finding.severity_raw.as_str() {
                "major" => "High",
                "minor" => "Medium",
                _ => "Low",
            }
        } else {
            let concern = finding.concern.to_lowercase();
            GATE_B_FALLBACK_PREDICATES
                .iter()
                .find(|(_, pattern)| pattern.is_match(&concern))
                .map_or("Low", |(label, _)| *label)
        };
        *match label {
            "Critical" => &mut summary.critical_count,
            "High" => &mut summary.high_count,
            "Medium" => &mut summary.medium_count,
            _ => &mut summary.low_count,
        } += 1;
        summary
            .display_labels
            .insert(finding.finding_id.clone(), label.to_owned());
    }
    summary
}

/// Build frozen Gate B display fields in document order.
#[must_use]
pub fn plan_review_gate_b_display_rows(
    findings: &[PlanReviewAcceptedFinding],
) -> Vec<PlanReviewGateBDisplayRow> {
    let summary = classify_plan_review_gate_b(findings);
    findings
        .iter()
        .map(|finding| {
            let excerpt = crate::split_text_lines(&finding.concern)
                .into_iter()
                .map(crate::trim_python_whitespace)
                .filter(|line| !line.is_empty())
                .take(2)
                .collect::<Vec<_>>()
                .join(" ")
                .chars()
                .take(200)
                .collect();
            PlanReviewGateBDisplayRow {
                finding_id: finding.finding_id.clone(),
                display_severity_label: summary
                    .display_labels
                    .get(&finding.finding_id)
                    .cloned()
                    .unwrap_or_else(|| "Low".to_owned()),
                reviewer_text: finding.reviewers.clone(),
                excerpt,
            }
        })
        .collect()
}

/// Remove accepted blocks explicitly skipped during Gate B one-by-one review.
#[must_use]
pub fn filter_plan_review_gate_b_skipped(accepted: &str, rejected: &str) -> String {
    const MARKER: &str = "rejected by user during one-by-one review";
    if !rejected.contains(MARKER) {
        return accepted.to_owned();
    }
    let normalize = |block: &str| {
        let normalized = crate::split_text_lines(crate::trim_python_whitespace(block))
            .into_iter()
            .filter(|line| !line.contains(MARKER))
            .map(|line| line.trim_end_matches(crate::is_python_whitespace))
            .collect::<Vec<_>>()
            .join("\n");
        crate::trim_python_whitespace(&normalized).to_owned()
    };
    let skipped: BTreeSet<String> = parse_blocks(rejected, BoundaryMode::LevelThreeHeading)
        .into_iter()
        .filter(|block| block.kind == ItemKind::Finding && block.block.contains(MARKER))
        .map(|block| normalize(&block.block))
        .collect();
    let kept = parse_blocks(accepted, BoundaryMode::LevelThreeHeading)
        .into_iter()
        .filter(|block| {
            block.kind == ItemKind::Finding && !skipped.contains(&normalize(&block.block))
        })
        .map(|block| crate::trim_python_whitespace(&block.block).to_owned())
        .collect::<Vec<_>>();
    if kept.is_empty() {
        String::new()
    } else {
        format!("{}\n\n", kept.join("\n\n"))
    }
}

/// Render recorded structured collector findings with Python-compatible layout.
#[must_use]
pub fn normalize_collected_findings(
    records: &[PlanReviewCollectorRecord],
    manifest_slots: &[PlanReviewManifestSlot],
) -> PlanReviewFindingOutput {
    let slot_by_output = manifest_slots
        .iter()
        .filter(|row| row.is_valid())
        .map(|row| (row.output.clone(), row.slot.clone()))
        .collect::<BTreeMap<_, _>>();
    let mut output = PlanReviewFindingOutput::default();
    let mut raw = String::new();
    let mut finding_num = 1_usize;
    let mut oos_num = 1_usize;
    let mut oos_counts_by_slot = BTreeMap::<String, usize>::new();

    for record in records {
        let slot = slot_by_output
            .get(&record.reviewer_file)
            .cloned()
            .unwrap_or_else(|| fallback_slot_name(&record.reviewer_file));
        if record.status != "OK" {
            output.failure_count += 1;
            continue;
        }
        output.ok_count += 1;
        let label = slot_human_label(&slot);
        for finding in &record.structured_findings {
            if is_oos_scope(&finding.scope) {
                let retained = oos_counts_by_slot.entry(slot.clone()).or_default();
                if *retained >= PER_REVIEWER_OOS_PROPOSAL_CAP {
                    continue;
                }
                *retained += 1;
                raw.push_str(&compose_oos_finding(&label, finding, oos_num));
                oos_num += 1;
            } else {
                raw.push_str(&compose_in_scope_finding(&label, finding, finding_num));
                finding_num += 1;
            }
        }
    }

    let parsed = parse_blocks(&raw, BoundaryMode::LevelThreeHeading);
    let in_scope = parsed
        .iter()
        .filter(|block| block.kind == ItemKind::Finding)
        .map(|block| block.block.as_str())
        .collect::<Vec<_>>();
    let oos = parsed
        .iter()
        .filter(|block| block.kind == ItemKind::Oos)
        .map(|block| block.block.as_str())
        .collect::<Vec<_>>();
    output.in_scope_markdown = render_blocks(&in_scope);
    output.out_of_scope_markdown = render_blocks(&oos);
    output
}

fn fallback_slot_name(reviewer_file: &str) -> String {
    Path::new(reviewer_file)
        .file_stem()
        .map_or_else(String::new, |stem| {
            stem.to_string_lossy().replace("-output", "")
        })
}

fn is_oos_scope(scope: &str) -> bool {
    matches!(
        scope.trim().to_ascii_lowercase().as_str(),
        "out_of_scope" | "out-of-scope" | "oos"
    )
}

fn compose_oos_finding(
    label: &str,
    finding: &PlanReviewStructuredFinding,
    number: usize,
) -> String {
    let severity = normalized_severity(&finding.severity);
    format!(
        "### OOS_{number}: {what}\n- **Description**: {what}. Scenario: {scenario}\n- **Reviewer**: {label}\n- **Severity**: {severity}\n- **Focus area**: {focus}\n- **Location**: {location}\n- **Phase**: design\n\n",
        what = finding.what.trim(),
        scenario = finding.scenario_or_breakage.trim(),
        focus = finding.focus_area.trim(),
        location = finding.location.trim(),
    )
}

fn compose_in_scope_finding(
    label: &str,
    finding: &PlanReviewStructuredFinding,
    number: usize,
) -> String {
    let severity = normalized_severity(&finding.severity);
    format!(
        "### FINDING_{number}:\n- **Reviewer(s)**: {label}\n- **Severity**: {severity}\n- **Focus area**: {focus}\n- **Location**: {location}\n- **Concern**: {what}. Scenario: {scenario}\n- **Proposed resolution**: {fix}\n\n",
        focus = finding.focus_area.trim(),
        location = finding.location.trim(),
        what = finding.what.trim(),
        scenario = finding.scenario_or_breakage.trim(),
        fix = finding.suggested_fix.trim(),
    )
}

fn normalized_severity(value: &str) -> &str {
    let value = value.trim();
    if value.is_empty() { "minor" } else { value }
}

fn render_blocks(blocks: &[&str]) -> String {
    if blocks.is_empty() {
        String::new()
    } else {
        format!("{}\n\n", blocks.join("\n\n"))
    }
}

/// Render the human label for one plan-review slot.
#[must_use]
pub fn slot_human_label(slot: &str) -> String {
    for (prefix, label) in [
        ("dyn-cursor-plan-", "Cursor-dyn-"),
        ("dyn-codex-plan-", "Codex-dyn-"),
        ("cursor-plan-", "Cursor-"),
        ("codex-plan-", "Codex-"),
        ("codex-primary-plan-", "Codex-"),
    ] {
        if let Some(suffix) = slot.strip_prefix(prefix) {
            return format!("{label}{}", title_slot_suffix(suffix));
        }
    }
    slot.to_owned()
}

fn title_slot_suffix(suffix: &str) -> String {
    suffix
        .split('-')
        .map(|part| {
            let mut characters = part.chars();
            let Some(first) = characters.next() else {
                return String::new();
            };
            first
                .to_uppercase()
                .chain(characters.flat_map(char::to_lowercase))
                .collect::<String>()
        })
        .collect::<Vec<_>>()
        .join(" ")
}

fn nominal_vendor_from_slot(slot: &str) -> &str {
    for (prefix, vendor) in [
        ("dyn-cursor-plan-", "cursor"),
        ("dyn-codex-plan-", "codex"),
        ("cursor-plan-", "cursor"),
        ("codex-plan-", "codex"),
        ("codex-primary-plan-", "codex"),
    ] {
        if slot.starts_with(prefix) {
            return vendor;
        }
    }
    ""
}

/// Render a reviewer label, recording a recognized fallback tool when needed.
#[must_use]
pub fn reconciled_reviewer_label(slot: &str, executing_tool: &str) -> String {
    let label = slot_human_label(slot);
    let nominal = nominal_vendor_from_slot(slot);
    let tool = executing_tool.trim();
    if !nominal.is_empty() && !tool.is_empty() && tool != "unknown" && tool != nominal {
        format!("{label} (via {})", title_slot_suffix(tool))
    } else {
        label
    }
}

/// One rendered reviewer status row.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct PlanReviewReviewerStatus {
    pub slot: String,
    pub status: String,
    pub elapsed: String,
}

/// Resolve one reviewer-status row per valid launched slot.
#[must_use]
pub fn reviewer_status_rows(
    manifest_slots: &[PlanReviewManifestSlot],
    collector_records: &[PlanReviewCollectorRecord],
) -> Vec<PlanReviewReviewerStatus> {
    let mut status_by_output = BTreeMap::<String, String>::new();
    let mut status_by_normalized_output = BTreeMap::<String, String>::new();
    let mut tool_by_output = BTreeMap::<String, String>::new();
    let mut tool_by_normalized_output = BTreeMap::<String, String>::new();
    for record in collector_records {
        if record.reviewer_file.is_empty() {
            continue;
        }
        let normalized = normalize_output_base(&record.reviewer_file);
        status_by_output.insert(record.reviewer_file.clone(), record.status.clone());
        tool_by_output.insert(record.reviewer_file.clone(), record.tool.clone());
        if status_by_normalized_output
            .get(&normalized)
            .is_none_or(|existing| existing != "OK")
        {
            status_by_normalized_output.insert(normalized.clone(), record.status.clone());
            tool_by_normalized_output.insert(normalized, record.tool.clone());
        }
    }

    manifest_slots
        .iter()
        .filter(|row| row.is_valid())
        .map(|row| {
            let normalized = normalize_output_base(&row.output);
            let raw_status = status_by_normalized_output
                .get(&normalized)
                .or_else(|| status_by_output.get(&row.output));
            let status = match raw_status {
                Some(value) if value == "OK" => "done",
                Some(_) => "failed",
                None => "skipped",
            };
            let tool = tool_by_normalized_output
                .get(&normalized)
                .or_else(|| tool_by_output.get(&row.output))
                .map_or("", String::as_str);
            PlanReviewReviewerStatus {
                slot: reconciled_reviewer_label(&row.slot, tool),
                status: status.to_owned(),
                elapsed: String::new(),
            }
        })
        .collect()
}

/// Render the byte-stable reviewer-status TSV for one plan-review round.
#[must_use]
pub fn render_reviewer_status_tsv(rows: &[PlanReviewReviewerStatus]) -> String {
    let mut output = "slot\tstatus\telapsed\n".to_owned();
    for row in rows {
        output.push_str(&row.slot);
        output.push('\t');
        output.push_str(&row.status);
        output.push('\t');
        output.push_str(&row.elapsed);
        output.push('\n');
    }
    output
}

/// Render the chat-ready reviewer-status table, if at least one slot exists.
#[must_use]
pub fn render_reviewer_status_table(rows: &[PlanReviewReviewerStatus]) -> Option<String> {
    let rendered = rows
        .iter()
        .filter(|row| !row.slot.trim().is_empty())
        .map(|row| {
            let status = row.status.trim().to_ascii_lowercase();
            let icon = match status.as_str() {
                "done" => "✅",
                "pending" | "in-progress" => "⏳",
                "skipped" => "⊘",
                _ => "❌",
            };
            let elapsed = row.elapsed.trim();
            let suffix = if elapsed.is_empty() || status == "skipped" {
                String::new()
            } else {
                format!(" {elapsed}")
            };
            format!("{}: {icon}{suffix}", row.slot.trim())
        })
        .collect::<Vec<_>>();
    (!rendered.is_empty()).then(|| format!("📊 Reviewers: | {} |", rendered.join(" | ")))
}

/// Summary fields persisted for one finished plan-review round.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct PlanReviewRoundSummary {
    pub loop_status: String,
    pub collect_ok_count: usize,
    pub collect_failure_count: usize,
    pub tally_status: String,
    pub aggregator_status: String,
    pub accepted_count: String,
    pub degraded_panel: String,
}

impl PlanReviewRoundSummary {
    /// Render Python-compatible round-summary environment bytes.
    #[must_use]
    pub fn render(&self) -> String {
        let rows = [
            ("LOOP_STATUS", self.loop_status.clone()),
            ("COLLECT_OK_COUNT", self.collect_ok_count.to_string()),
            (
                "COLLECT_FAILURE_COUNT",
                self.collect_failure_count.to_string(),
            ),
            ("TALLY_PLAN_REVIEW_STATUS", self.tally_status.clone()),
            ("AGGREGATOR_STATUS", self.aggregator_status.clone()),
            ("ACCEPTED_COUNT", self.accepted_count.clone()),
            ("DEGRADED_PANEL", self.degraded_panel.clone()),
        ];
        let mut rendered = String::new();
        for (key, value) in rows {
            if !value.is_empty() {
                writeln!(rendered, "{key}={value}").expect("writing to String cannot fail");
            }
        }
        rendered
    }
}

/// Result reported by panel dispatch before collection begins.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct PlanReviewPanelOutcome {
    pub exit_code: i32,
    pub panel_pruned_empty: bool,
}

/// Result reported after collection and normalized finding composition.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct PlanReviewCollectionOutcome {
    pub exit_code: i32,
    pub record_count: usize,
    pub ok_count: usize,
    pub failure_count: usize,
}

/// Result reported by finding aggregation.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct PlanReviewAggregationOutcome {
    pub exit_code: i32,
    pub reason: String,
    pub aggregated: bool,
}

/// Result of preparing the normalized ballot and proposer map.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct PlanReviewBallotOutcome {
    pub preparation_failed: bool,
    pub has_canonical_items: bool,
}

/// Result reported by voter dispatch.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct PlanReviewVoterOutcome {
    pub exit_code: i32,
    pub dispatch_ok: bool,
    pub degraded_panel: bool,
}

/// Result reported by plan-review tallying.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct PlanReviewTallyOutcome {
    pub exit_code: i32,
    pub status: String,
    pub accepted_count: usize,
}

/// Injected outcomes for the side-effect-free round runner.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct PlanReviewRoundInput {
    pub panel: PlanReviewPanelOutcome,
    pub collection: PlanReviewCollectionOutcome,
    pub aggregation: PlanReviewAggregationOutcome,
    pub ballot: PlanReviewBallotOutcome,
    pub voter: PlanReviewVoterOutcome,
    pub tally: PlanReviewTallyOutcome,
}

/// Terminal state returned by the side-effect-free plan-review round runner.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct PlanReviewRoundState {
    pub exit_code: i32,
    pub loop_status: String,
    pub tally_status: String,
    pub aggregator_status: String,
    pub accepted_count: usize,
    pub degraded_panel: bool,
    pub panel_pruned_empty: bool,
    pub rounds_completed: Option<u64>,
    pub collect_ok_count: usize,
    pub collect_failure_count: usize,
}

impl PlanReviewRoundState {
    fn new(input: &PlanReviewRoundInput) -> Self {
        Self {
            exit_code: 0,
            loop_status: "complete".to_owned(),
            tally_status: "ok".to_owned(),
            aggregator_status: "ok".to_owned(),
            accepted_count: 0,
            degraded_panel: false,
            panel_pruned_empty: input.panel.panel_pruned_empty,
            rounds_completed: None,
            collect_ok_count: input.collection.ok_count,
            collect_failure_count: input.collection.failure_count,
        }
    }

    fn set_loop_status(&mut self, value: &str) {
        value.clone_into(&mut self.loop_status);
    }

    fn set_tally_status(&mut self, value: &str) {
        value.clone_into(&mut self.tally_status);
    }

    fn set_aggregator_status(&mut self, value: &str) {
        value.clone_into(&mut self.aggregator_status);
    }

    /// Return the byte-stable per-round summary for this state.
    #[must_use]
    pub fn summary(&self) -> PlanReviewRoundSummary {
        PlanReviewRoundSummary {
            loop_status: self.loop_status.clone(),
            collect_ok_count: self.collect_ok_count,
            collect_failure_count: self.collect_failure_count,
            tally_status: self.tally_status.clone(),
            aggregator_status: self.aggregator_status.clone(),
            accepted_count: self.accepted_count.to_string(),
            degraded_panel: if self.degraded_panel {
                "1".to_owned()
            } else {
                "0".to_owned()
            },
        }
    }
}

/// Run the pure plan-review state machine over already-observed stage outcomes.
#[must_use]
pub fn run_plan_review_round(round_num: u64, input: &PlanReviewRoundInput) -> PlanReviewRoundState {
    let mut state = PlanReviewRoundState::new(input);
    if input.panel.exit_code != 0 {
        state.exit_code = input.panel.exit_code;
        state.set_loop_status("panel-failed");
        state.set_tally_status("panel-failed");
        state.set_aggregator_status("skipped");
        state.degraded_panel = true;
        return state;
    }
    if input.panel.panel_pruned_empty {
        state.set_loop_status("zero-findings-degraded-panel");
        state.set_aggregator_status("skipped-pruned-empty");
        return state;
    }
    if input.collection.exit_code != 0 && input.collection.record_count == 0 {
        state.exit_code = 1;
        state.set_loop_status("panel-failed");
        state.set_tally_status("panel-failed");
        state.set_aggregator_status("skipped");
        state.degraded_panel = true;
        return state;
    }

    state.aggregator_status = aggregator_status(
        input.aggregation.exit_code,
        &input.aggregation.reason,
        input.aggregation.aggregated,
    );
    if !aggregation_ok_for_voting(
        input.aggregation.exit_code,
        &input.aggregation.reason,
        input.aggregation.aggregated,
    ) {
        state.exit_code = 1;
        state.set_loop_status("panel-failed");
        state.set_tally_status("panel-failed");
        state.degraded_panel = true;
        return state;
    }
    if input.ballot.preparation_failed {
        state.exit_code = 2;
        state.set_loop_status("tally-error");
        state.set_tally_status("tally-error");
        state.degraded_panel = true;
        return state;
    }
    if input.collection.ok_count > 0 && !input.ballot.has_canonical_items {
        state.set_loop_status("zero-findings-degraded-panel");
        state.rounds_completed = Some(round_num);
        return state;
    }
    if input.voter.exit_code != 0 || !input.voter.dispatch_ok {
        state.exit_code = 1;
        state.set_loop_status("panel-failed");
        state.set_tally_status("panel-failed");
        state.degraded_panel = true;
        return state;
    }

    state.tally_status = if input.tally.status.is_empty() {
        if input.tally.exit_code == 0 {
            "ok".to_owned()
        } else {
            "tally-error".to_owned()
        }
    } else {
        input.tally.status.clone()
    };
    if state.tally_status == "tally-error" || !matches!(input.tally.exit_code, 0 | 2) {
        state.exit_code = 2;
        state.set_loop_status("tally-error");
        state.set_tally_status("tally-error");
        return state;
    }
    if state.tally_status == "main-agent-vote-required" {
        state.set_loop_status("main-agent-vote-required");
        return state;
    }

    state.accepted_count = input.tally.accepted_count;
    state.degraded_panel = input.voter.degraded_panel;
    state.set_loop_status(classify_round_loop_status(
        state.accepted_count,
        input.collection.ok_count,
        state.degraded_panel,
        state.panel_pruned_empty,
        &state.tally_status,
    ));
    if state.loop_status == "degraded-empty-collector" {
        state.degraded_panel = true;
        return state;
    }
    state.rounds_completed = Some(round_num);
    state
}

/// Return whether aggregation can proceed to voter dispatch.
#[must_use]
pub fn aggregation_ok_for_voting(exit_code: i32, reason: &str, aggregated: bool) -> bool {
    exit_code == 0
        && (matches!(
            reason,
            "insufficient-input"
                | "disabled"
                | "dispatch-failed"
                | "validation-failed"
                | "validation-exhausted"
        ) || (reason == "ok" && aggregated))
}

/// Convert an aggregator process result to its stable status token.
#[must_use]
pub fn aggregator_status(exit_code: i32, reason: &str, aggregated: bool) -> String {
    if exit_code != 0 {
        return "aggregator-failed".to_owned();
    }
    if reason == "ok" && aggregated {
        return "ok".to_owned();
    }
    if matches!(reason, "insufficient-input" | "disabled") {
        return reason.to_owned();
    }
    if reason.is_empty() {
        "aggregator-failed".to_owned()
    } else {
        reason.to_owned()
    }
}

/// Classify a completed non-error plan-review round.
#[must_use]
pub fn classify_round_loop_status(
    accepted: usize,
    ok_count: usize,
    degraded: bool,
    panel_pruned_empty: bool,
    tally_status: &str,
) -> &'static str {
    if accepted == 0 && ok_count == 0 && !panel_pruned_empty {
        "degraded-empty-collector"
    } else if accepted == 0 && (degraded || tally_status == "skipped-empty-findings") {
        "zero-findings-degraded-panel"
    } else {
        "complete"
    }
}

/// Map a Step 3 terminal status to its loop status, preserving the fallback for unknown input.
#[must_use]
pub fn step3_loop_status_to_loop_status(status: &str, fallback: &str) -> String {
    match status {
        "complete" if fallback == "zero-findings-degraded-panel" => fallback.to_owned(),
        "cap-hit" => "cap-reached".to_owned(),
        "complete"
        | "main-agent-vote-required"
        | "postplan-failed"
        | "panel-failed"
        | "panel-init-failed"
        | "tally-error"
        | "degraded-empty-collector" => status.to_owned(),
        "main-agent-apply-required"
        | "per-round-approval-required"
        | "postplan-operator-required" => "complete".to_owned(),
        _ if fallback.is_empty() => "complete".to_owned(),
        _ => fallback.to_owned(),
    }
}

/// Recover a Step 3 terminal status from a persisted loop status.
#[must_use]
pub fn step3_status_from_loop_status(loop_status: &str) -> String {
    match loop_status {
        "complete" => "complete",
        "cap-reached" => "cap-hit",
        "main-agent-vote-required" => "main-agent-vote-required",
        "main-agent-apply-required" => "main-agent-apply-required",
        "per-round-approval-required" => "per-round-approval-required",
        "postplan-operator-required" => "postplan-operator-required",
        "postplan-failed" => "postplan-failed",
        "panel-failed" => "panel-failed",
        "panel-init-failed" => "panel-init-failed",
        "tally-error" => "tally-error",
        "degraded-empty-collector" => "degraded-empty-collector",
        _ => "",
    }
    .to_owned()
}

/// Resolve the Step 3 route from terminal, loop, and tally status values.
#[must_use]
pub fn step3_next_action(status: &str, loop_status: &str, tally_status: &str) -> String {
    if loop_status == "zero-findings-degraded-panel" {
        return "step3b".to_owned();
    }
    if tally_status == "tally-error" && (status == "complete" || loop_status == "complete") {
        return "step3b-bypass".to_owned();
    }
    match status {
        "complete" => "step3b",
        "cap-hit" | "panel-failed" | "tally-error" | "degraded-empty-collector" => "step3b-bypass",
        "main-agent-vote-required" => "mav",
        "main-agent-apply-required" | "per-round-approval-required" => "gate-b",
        "postplan-operator-required" => "postplan-operator",
        "postplan-failed" => "final-summary:failed-postplan",
        "panel-init-failed" => "final-summary:failed-judge-panel",
        _ => "",
    }
    .to_owned()
}

/// Read keys from an applied-finding ledger only from earlier rounds.
#[must_use]
pub fn applied_finding_keys_before(ledger: &str, before_round: u64) -> BTreeSet<String> {
    crate::split_text_lines(ledger)
        .into_iter()
        .filter_map(|line| {
            let (round, key) = line.split_once('\t')?;
            let round = round.parse::<u64>().ok()?;
            (!key.is_empty() && round < before_round).then(|| key.to_owned())
        })
        .collect()
}

/// Read every valid key from an applied-finding ledger.
#[must_use]
pub fn all_applied_finding_keys(ledger: &str) -> BTreeSet<String> {
    crate::split_text_lines(ledger)
        .into_iter()
        .filter_map(|line| {
            let (round, key) = line.split_once('\t')?;
            (!key.is_empty() && is_decimal(round)).then(|| key.to_owned())
        })
        .collect()
}

fn is_decimal(value: &str) -> bool {
    !value.is_empty() && value.bytes().all(|byte| byte.is_ascii_digit())
}

/// Replace one round's keys in an applied-finding ledger without duplicating input keys.
#[must_use]
pub fn replace_applied_finding_keys(ledger: &str, round_num: u64, keys: &[String]) -> String {
    let mut rows = crate::split_text_lines(ledger)
        .into_iter()
        .filter(|line| {
            line.split_once('\t').is_some_and(|(round, _)| {
                is_decimal(round) && (round.parse::<u64>() != Ok(round_num))
            })
        })
        .map(str::to_owned)
        .collect::<Vec<_>>();
    let mut seen = BTreeSet::new();
    for key in keys {
        if !key.is_empty() && seen.insert(key) {
            rows.push(format!("{round_num}\t{key}"));
        }
    }
    if rows.is_empty() {
        String::new()
    } else {
        format!("{}\n", rows.join("\n"))
    }
}

/// Merge already-addressed finding keys into a sorted, newline-terminated ledger.
#[must_use]
pub fn merge_already_addressed_finding_keys(ledger: &str, keys: &[String]) -> String {
    let mut merged = crate::split_text_lines(ledger)
        .into_iter()
        .map(crate::trim_python_whitespace)
        .filter(|key| !key.is_empty())
        .map(str::to_owned)
        .collect::<BTreeSet<_>>();
    merged.extend(keys.iter().filter(|key| !key.is_empty()).cloned());
    if merged.is_empty() {
        String::new()
    } else {
        format!("{}\n", merged.into_iter().collect::<Vec<_>>().join("\n"))
    }
}
