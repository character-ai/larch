//! Pure repair-round contracts shared by the future review-and-fix command owner.
//!
//! The current Python owner performs process execution and filesystem mutation.
//! This module deliberately keeps those effects at its caller boundary while
//! preserving the state transitions and artifact bytes that the owner consumes.

use std::{
    collections::BTreeSet,
    fmt::Write as _,
    path::{Component, Path, PathBuf},
};

use serde_json::Value;

use super::types::{ItemKind, is_canonical_heading};

/// The stable filesystem layout for one code-review repair round.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RepairRoundArtifacts {
    root: PathBuf,
    round_num: u64,
}

impl RepairRoundArtifacts {
    /// Construct the artifact layout rooted at an implementation temporary directory.
    #[must_use]
    pub fn new(root: impl Into<PathBuf>, round_num: u64) -> Self {
        Self {
            root: root.into(),
            round_num,
        }
    }

    /// Return the implementation temporary directory.
    #[must_use]
    pub fn root(&self) -> &Path {
        &self.root
    }

    /// Return the represented round number.
    #[must_use]
    pub const fn round_num(&self) -> u64 {
        self.round_num
    }

    /// Return the round-local artifact directory.
    #[must_use]
    pub fn round_dir(&self) -> PathBuf {
        self.root.join(format!("round-{}", self.round_num))
    }

    /// Return the captured review-core environment path.
    #[must_use]
    pub fn review_core_env(&self) -> PathBuf {
        self.round_file("review-core.env")
    }

    /// Return the accepted findings path.
    #[must_use]
    pub fn accepted_findings(&self) -> PathBuf {
        self.round_file("accepted-findings.md")
    }

    /// Return the accepted, in-scope findings path passed to a coder.
    #[must_use]
    pub fn accepted_in_scope_findings(&self) -> PathBuf {
        self.round_file("accepted-in-scope-findings.md")
    }

    /// Return the compact rejected-findings path.
    #[must_use]
    pub fn rejected_findings(&self) -> PathBuf {
        self.round_file("rejected-findings.md")
    }

    /// Return the full rejected-findings path.
    #[must_use]
    pub fn rejected_findings_full(&self) -> PathBuf {
        self.round_file("rejected-findings-full.md")
    }

    /// Return the persisted coder result environment path.
    #[must_use]
    pub fn coder_env(&self) -> PathBuf {
        self.round_file("coder.env")
    }

    /// Return the coder output log path.
    #[must_use]
    pub fn coder_output(&self) -> PathBuf {
        self.round_file("coder-output.log")
    }

    /// Return the composed findings path for this round.
    #[must_use]
    pub fn composed_findings(&self) -> PathBuf {
        self.round_file("review-findings-full.composed.jsonl")
    }

    /// Return the round's terminal status environment path.
    #[must_use]
    pub fn result_env(&self) -> PathBuf {
        self.round_file("review-and-fix.env")
    }

    /// Return the cumulative review summary path.
    #[must_use]
    pub fn summary(&self) -> PathBuf {
        self.root.join("review-and-fix-summary.json")
    }

    /// Return the cumulative OOS JSONL path.
    #[must_use]
    pub fn accumulated_oos(&self) -> PathBuf {
        self.root.join("accumulated-oos.jsonl")
    }

    fn round_file(&self, name: &str) -> PathBuf {
        self.round_dir().join(name)
    }
}

/// A pre-coder snapshot's available safety level.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum RepairSnapshotMode {
    /// No snapshot exists; cleanup must restore a clean tree fail-closed.
    Missing,
    /// The snapshot preserves the commit and untracked baseline only.
    HeadUntracked,
    /// The snapshot preserves tracked patches as well as the untracked baseline.
    Full,
}

/// One persisted snapshot artifact identity, matching Python's size/checksum shape.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct SnapshotArtifactIdentity {
    pub name: String,
    pub size: u64,
    pub checksum: u32,
}

/// Pre-coder snapshot artifacts observed by the filesystem boundary.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct RepairSnapshotLayout {
    pub root_exists: bool,
    pub root_entries: BTreeSet<String>,
    pub pre_head: Option<String>,
    pub tracked_paths: Option<Vec<String>>,
    pub untracked_paths: Option<Vec<String>>,
    pub pre_coder_patch_names: BTreeSet<String>,
}

/// A malformed pre-coder snapshot reason.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum RepairSnapshotError {
    UnexpectedRootArtifact(String),
    PartialArtifacts,
    InvalidHead,
    InvalidInventory,
    PatchNameCollision,
    UnexpectedPatches,
}

/// Validate a snapshot artifact set and return its usable mode.
///
/// A caller owns symlink and filesystem containment checks. This function owns
/// the immutable artifact grammar used after those checks pass.
///
/// # Errors
///
/// Returns a reason when the observed artifact set is partial, unsafe, or does
/// not match the snapshot's expected tracked-patch grammar.
pub fn validate_repair_snapshot(
    layout: &RepairSnapshotLayout,
) -> Result<RepairSnapshotMode, RepairSnapshotError> {
    if !layout.root_exists {
        return Ok(RepairSnapshotMode::Missing);
    }
    validate_snapshot_root_entries(&layout.root_entries)?;
    if !layout.root_entries.contains("pre-coder-head.txt")
        || !layout
            .root_entries
            .contains("pre-coder-untracked-paths.txt")
    {
        return Err(RepairSnapshotError::PartialArtifacts);
    }
    let (Some(head), Some(untracked)) = (&layout.pre_head, &layout.untracked_paths) else {
        return Err(RepairSnapshotError::PartialArtifacts);
    };
    if !valid_snapshot_head(head) {
        return Err(RepairSnapshotError::InvalidHead);
    }
    validate_snapshot_inventory(untracked)?;
    let Some(tracked) = &layout.tracked_paths else {
        return if !layout.root_entries.contains("pre-coder-tracked-paths.txt")
            && layout.pre_coder_patch_names.is_empty()
            && !layout.root_entries.contains("pre-coder-path-diffs")
        {
            Ok(RepairSnapshotMode::HeadUntracked)
        } else {
            Err(RepairSnapshotError::UnexpectedPatches)
        };
    };
    if !layout.root_entries.contains("pre-coder-tracked-paths.txt") {
        return Err(RepairSnapshotError::PartialArtifacts);
    }
    if !layout.pre_coder_patch_names.is_empty()
        && !layout.root_entries.contains("pre-coder-path-diffs")
    {
        return Err(RepairSnapshotError::PartialArtifacts);
    }
    validate_snapshot_inventory(tracked)?;
    let expected = expected_patch_names(tracked)?;
    if expected == layout.pre_coder_patch_names {
        Ok(RepairSnapshotMode::Full)
    } else {
        Err(RepairSnapshotError::UnexpectedPatches)
    }
}

/// Return whether a re-read snapshot identity exactly matches its validation identity.
#[must_use]
pub fn snapshot_identity_matches(
    expected: &[SnapshotArtifactIdentity],
    actual: &[SnapshotArtifactIdentity],
) -> bool {
    let expected_len = expected.len();
    let actual_len = actual.len();
    let expected_set = identity_set(expected);
    let actual_set = identity_set(actual);
    expected_len == actual_len
        && expected_len == expected_set.len()
        && actual_len == actual_set.len()
        && expected_set == actual_set
}

/// Convert one tracked repository path into its stable patch-artifact basename.
#[must_use]
pub fn safe_patch_name(path: &str) -> String {
    path.replace(['/', '\\'], "__")
}

/// One current tracked path and whether it equals its preserved baseline patch.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RepairTrackedPath {
    pub path: String,
    pub matches_baseline: bool,
}

/// Return tracked paths changed by a coder, preserving Python's first-seen order.
#[must_use]
pub fn tracked_delta_paths(
    current: &[RepairTrackedPath],
    baseline_paths: &BTreeSet<String>,
) -> Vec<String> {
    let mut seen = BTreeSet::new();
    let mut deltas = Vec::new();
    for entry in current {
        if entry.path.is_empty() || !seen.insert(entry.path.clone()) {
            continue;
        }
        if !baseline_paths.contains(&entry.path) || !entry.matches_baseline {
            deltas.push(entry.path.clone());
        }
    }
    deltas
}

/// Return untracked paths created after a snapshot baseline, in current order.
#[must_use]
pub fn untracked_delta_paths(current: &[String], baseline_paths: &BTreeSet<String>) -> Vec<String> {
    current
        .iter()
        .filter(|path| !baseline_paths.contains(*path))
        .cloned()
        .collect()
}

/// Return paths eligible for the next repair commit.
///
/// A missing diff base deliberately produces no paths. That preserves the
/// fail-closed behavior used for absent post-coder commit markers.
#[must_use]
pub fn collect_repair_stage_paths(
    mode: RepairSnapshotMode,
    diff_base: &str,
    tracked: &[String],
    untracked: &[String],
) -> Vec<String> {
    if mode == RepairSnapshotMode::Missing || diff_base.is_empty() {
        return Vec::new();
    }
    let mut seen = BTreeSet::new();
    tracked
        .iter()
        .chain(untracked)
        .filter(|path| !path.is_empty() && seen.insert((*path).clone()))
        .cloned()
        .collect()
}

/// One ordered recovery operation for a failed coder attempt.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum RepairCleanupAction {
    RestoreStaged,
    RestorePreCoderTracked,
    RemoveCoderUntracked,
    RestoreAttemptTracked,
    RemoveAttemptUntracked,
    RestoreWorktree,
    Verify,
}

/// Build the fail-closed cleanup sequence for a failed coder attempt.
#[must_use]
pub fn cleanup_plan(mode: RepairSnapshotMode, has_coder_deltas: bool) -> Vec<RepairCleanupAction> {
    if has_coder_deltas {
        return match mode {
            RepairSnapshotMode::Full => vec![
                RepairCleanupAction::RestoreStaged,
                RepairCleanupAction::RestorePreCoderTracked,
                RepairCleanupAction::RemoveCoderUntracked,
                RepairCleanupAction::Verify,
            ],
            RepairSnapshotMode::HeadUntracked => vec![
                RepairCleanupAction::RestoreStaged,
                RepairCleanupAction::RemoveAttemptUntracked,
                RepairCleanupAction::RestoreAttemptTracked,
                RepairCleanupAction::Verify,
            ],
            RepairSnapshotMode::Missing => vec![
                RepairCleanupAction::RestoreStaged,
                RepairCleanupAction::RestoreWorktree,
                RepairCleanupAction::Verify,
            ],
        };
    }
    if mode == RepairSnapshotMode::Missing {
        return vec![
            RepairCleanupAction::RestoreStaged,
            RepairCleanupAction::RestoreWorktree,
            RepairCleanupAction::Verify,
        ];
    }
    Vec::new()
}

/// Result produced by an external repair coder.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RepairCoderResult {
    pub rc: i32,
    pub tool: String,
    pub status: String,
    pub log_file: String,
    pub input_count: usize,
    pub scrub_count: usize,
    pub revert_count: usize,
    pub commit_sha: String,
}

impl Default for RepairCoderResult {
    fn default() -> Self {
        Self {
            rc: 0,
            tool: "none".to_owned(),
            status: "skipped".to_owned(),
            log_file: String::new(),
            input_count: 0,
            scrub_count: 0,
            revert_count: 0,
            commit_sha: String::new(),
        }
    }
}

impl RepairCoderResult {
    /// Render the byte-stable Python `coder.env` wire grammar.
    #[must_use]
    pub fn render_env(&self) -> String {
        let rows = [
            ("CODER_TOOL", self.tool.as_str()),
            ("CODER_STATUS", self.status.as_str()),
            ("CODER_LOG_FILE", self.log_file.as_str()),
        ];
        let mut rendered = String::new();
        for (key, value) in rows {
            writeln!(rendered, "{key}={}", wire_value(value))
                .expect("writing to String cannot fail");
        }
        writeln!(rendered, "CODER_INPUT_COUNT={}", self.input_count)
            .expect("writing to String cannot fail");
        writeln!(rendered, "SUBMODULE_SCRUB_COUNT={}", self.scrub_count)
            .expect("writing to String cannot fail");
        writeln!(rendered, "SUBMODULE_REVERT_COUNT={}", self.revert_count)
            .expect("writing to String cannot fail");
        if !self.commit_sha.is_empty() {
            writeln!(
                rendered,
                "CODER_COMMIT_SHA={}",
                wire_value(&self.commit_sha)
            )
            .expect("writing to String cannot fail");
        }
        rendered
    }
}

/// Commit result observed after an otherwise successful coder dispatch.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub enum RepairCommitOutcome {
    /// A direct apply command does not make a per-round commit.
    #[default]
    NotRequested,
    Committed(String),
    Failed,
    StaleIndexLock,
}

/// One attempted coder dispatch observed at the process boundary.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct RepairCoderAttempt {
    pub tool: String,
    pub dispatched: bool,
    pub cleanup_ok: bool,
    pub submodule_revert_count: usize,
    pub stage_path_count: usize,
    pub commit: RepairCommitOutcome,
}

/// Inputs already observed by the external coder runner.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct RepairCoderInput {
    pub input_count: usize,
    pub scrub_count: usize,
    pub scrub_ok: bool,
    pub scrubbed_count: usize,
    pub snapshot_valid: bool,
    pub snapshot_head_fresh: bool,
    pub tool_log: String,
    pub attempts: Vec<RepairCoderAttempt>,
}

/// Resolve Python-compatible coder terminal behavior from observed attempt outcomes.
#[must_use]
pub fn resolve_coder_result(input: &RepairCoderInput) -> RepairCoderResult {
    if let Some(result) = pre_attempt_coder_result(input) {
        return result;
    }
    for attempt in &input.attempts {
        if let Some(result) = resolve_coder_attempt(input, attempt) {
            return result;
        }
    }
    RepairCoderResult {
        rc: 4,
        tool: "none".to_owned(),
        status: "main-agent-required".to_owned(),
        log_file: String::new(),
        input_count: input.scrubbed_count,
        scrub_count: input.scrub_count,
        revert_count: 0,
        commit_sha: String::new(),
    }
}

/// Counts maintained by a repair round and its cumulative summary.
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub struct RepairCounts {
    pub accepted: usize,
    pub rejected: usize,
    pub exonerated: usize,
    pub neutral: usize,
}

/// Evidence used to decide whether a small repair round has converged.
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub enum RepairConvergenceEvidence {
    #[default]
    NotChecked,
    Findings {
        non_nit_count: usize,
        important_present: bool,
    },
    UnreadableFindings {
        non_nit_count: usize,
    },
}

/// Result of composing the cumulative review findings artifact.
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub enum RepairComposition {
    #[default]
    NotRun,
    Failed,
    Succeeded(RepairCounts),
}

/// Health of skipped-finding classification after a successful coder run.
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub enum RepairClassifier {
    #[default]
    Healthy,
    Failed,
}

/// Observed inputs to one repair round after side effects have completed.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct RepairRoundInput {
    pub core_exit_code: i32,
    pub core_status: String,
    pub zero_survivor_panel_failed: bool,
    pub round_counts: RepairCounts,
    pub prior_counts: RepairCounts,
    pub coder: RepairCoderResult,
    pub degraded_round: bool,
    pub convergence: RepairConvergenceEvidence,
    pub classifier: RepairClassifier,
    pub composition: RepairComposition,
}

/// Terminal state of one repair round.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RepairRoundState {
    pub exit_code: i32,
    pub status: String,
    pub core_status: String,
    pub round_num: u64,
    pub round_counts: RepairCounts,
    pub total_counts: RepairCounts,
    pub coder: RepairCoderResult,
    pub degraded_round: bool,
}

/// Resolve Python-compatible terminal state for a completed repair round.
#[must_use]
pub fn resolve_repair_round(round_num: u64, input: &RepairRoundInput) -> RepairRoundState {
    let (mut status, mut exit_code) = initial_round_state(input);
    if input.core_exit_code != 0 && exit_code == 0 && status != "self-review-required" {
        exit_code = input.core_exit_code;
    }
    apply_convergence(&mut status, &mut exit_code, input);
    let mut total_counts = add_counts(input.prior_counts, input.round_counts);
    apply_composition(
        &mut status,
        &mut exit_code,
        &mut total_counts,
        input.composition,
    );
    RepairRoundState {
        exit_code,
        status,
        core_status: input.core_status.clone(),
        round_num,
        round_counts: input.round_counts,
        total_counts,
        coder: input.coder.clone(),
        degraded_round: input.degraded_round,
    }
}

/// Count code-review findings from the composed JSONL artifact.
#[must_use]
pub fn count_code_review_findings(text: &str) -> (RepairCounts, bool) {
    let mut counts = RepairCounts::default();
    let mut saw_code_review = false;
    for line in text.lines() {
        let Ok(Value::Object(record)) = serde_json::from_str::<Value>(line) else {
            continue;
        };
        if record.get("phase").and_then(Value::as_str) != Some("code-review") {
            continue;
        }
        saw_code_review = true;
        match record.get("outcome").and_then(Value::as_str) {
            Some("accepted") => counts.accepted += 1,
            Some("rejected") => counts.rejected += 1,
            _ => {}
        }
    }
    (counts, saw_code_review)
}

/// One round's rejected-findings artifacts used for cumulative rendering.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct RejectedFindingsRound {
    pub round_num: u64,
    pub full: String,
    pub compact: String,
}

/// Render the cumulative rejected-findings artifact, or return `None` to remove it.
#[must_use]
pub fn render_rejected_findings_aggregate(
    rounds: &[RejectedFindingsRound],
    fallback: Option<&str>,
) -> Option<String> {
    if !rounds.iter().any(|round| !round.full.is_empty()) {
        return fallback.map(ToOwned::to_owned);
    }
    let mut ordered = rounds.to_vec();
    ordered.sort_by_key(|round| round.round_num);
    let mut output = String::new();
    let mut started = false;
    for round in ordered {
        let source = if round.full.is_empty() {
            &round.compact
        } else {
            &round.full
        };
        if source.is_empty() {
            continue;
        }
        if !started {
            output.push_str("# Rejected Findings\n\n");
            started = true;
        }
        writeln!(output, "# Review Round {}\n", round.round_num)
            .expect("writing to String cannot fail");
        for line in rejected_body_lines(source) {
            writeln!(output, "{line}").expect("writing to String cannot fail");
        }
        output.push('\n');
    }
    started.then_some(output)
}

/// Inputs to the persisted code-review tally body renderer.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct RepairBatchReport {
    pub rounds: u64,
    pub counts: RepairCounts,
    pub root_summary: String,
    pub round_summaries: Vec<(u64, String)>,
    pub rejected_findings: String,
    pub rejected_findings_full: String,
    pub voting_tally: String,
}

/// Render the byte-stable code-review tally body.
#[must_use]
pub fn render_repair_tally_body(report: &RepairBatchReport) -> String {
    let mut body = format!(
        "Rounds: {} | {} accepted, {} rejected\n",
        report.rounds, report.counts.accepted, report.counts.rejected
    );
    let summaries = selected_summaries(report);
    for summary in summaries {
        body.push('\n');
        for line in summary.lines() {
            if !is_summary_count_line(line) {
                writeln!(body, "{line}").expect("writing to String cannot fail");
            }
        }
        body.push('\n');
    }
    let rejected = first_nonempty(&report.rejected_findings, &report.rejected_findings_full);
    if let Some(rejected) = rejected {
        body.push_str("\n## Rejected Code Review Findings\n\n");
        body.push_str(&render_rejected_findings_for_tally(rejected));
        body.push('\n');
    }
    if report.rounds > 0 && !report.voting_tally.is_empty() {
        body.push_str("\n## Voting Tally\n\n");
        body.push_str(&report.voting_tally);
        body.push('\n');
    }
    body
}

/// Render the one-line JSON payload for a specialist scout manifest batch.
///
/// The dynamic slot value follows Python's non-negative digit grammar while
/// preserving the exact field order used by the recorded batch.
///
/// # Errors
///
/// Returns an error when `dynamic_slots` is not a non-negative decimal value.
pub fn render_scout_manifest_payload(
    status: &str,
    dynamic_slots: &str,
    manifest_path: &str,
    yield_tsv_path: &str,
) -> Result<String, &'static str> {
    let Some(dynamic_slots) = normalize_unsigned_decimal(dynamic_slots) else {
        return Err("invalid DYNAMIC_SLOTS for review-scout-manifest payload");
    };
    let status = json_string(status);
    let manifest = json_string(path_basename(manifest_path));
    let yield_tsv = json_string(path_basename(yield_tsv_path));
    Ok(format!(
        "{{\"status\":{status},\"dynamic_slots\":{dynamic_slots},\"manifest_basename\":{manifest},\"yield_tsv_basename\":{yield_tsv}}}\n"
    ))
}

/// Render the code-review tally-flush failure sidecar bytes.
#[must_use]
pub fn tally_flush_sidecar(returncode: i32, stderr: &str, stdout: &str) -> String {
    format!(
        "voting write-tally failed (returncode={returncode})\n--- stderr ---\n{stderr}\n--- stdout ---\n{stdout}\n"
    )
}

fn validate_snapshot_root_entries(entries: &BTreeSet<String>) -> Result<(), RepairSnapshotError> {
    let allowed = [
        "pre-coder-head.txt",
        "pre-coder-tracked-paths.txt",
        "pre-coder-untracked-paths.txt",
        "pre-coder-path-diffs",
        "attempt-pre-tracked-paths.txt",
        "attempt-pre-untracked-paths.txt",
        "attempt-pre-path-diffs",
    ];
    for entry in entries {
        if !allowed.contains(&entry.as_str()) {
            return Err(RepairSnapshotError::UnexpectedRootArtifact(entry.clone()));
        }
    }
    Ok(())
}

fn valid_snapshot_head(head: &str) -> bool {
    let head = head.trim();
    !head.is_empty() && !head.contains(['\n', '\r'])
}

fn validate_snapshot_inventory(entries: &[String]) -> Result<(), RepairSnapshotError> {
    let mut seen = BTreeSet::new();
    for entry in entries {
        let path = Path::new(entry);
        if entry.is_empty()
            || entry.contains('\0')
            || path.is_absolute()
            || path
                .components()
                .any(|component| component == Component::ParentDir)
            || !seen.insert(entry)
        {
            return Err(RepairSnapshotError::InvalidInventory);
        }
    }
    Ok(())
}

fn expected_patch_names(paths: &[String]) -> Result<BTreeSet<String>, RepairSnapshotError> {
    let names = paths
        .iter()
        .map(|path| safe_patch_name(path))
        .collect::<BTreeSet<_>>();
    if names.len() != paths.len() {
        return Err(RepairSnapshotError::PatchNameCollision);
    }
    Ok(names
        .iter()
        .flat_map(|name| [format!("{name}.patch"), format!("{name}.cached.patch")])
        .collect())
}

fn identity_set(identities: &[SnapshotArtifactIdentity]) -> BTreeSet<(String, u64, u32)> {
    identities
        .iter()
        .map(|identity| (identity.name.clone(), identity.size, identity.checksum))
        .collect()
}

fn wire_value(value: &str) -> String {
    value.replace(['\n', '\r'], " ")
}

fn coder_failure(
    tool: &str,
    log_file: &str,
    input_count: usize,
    scrub_count: usize,
    revert_count: usize,
) -> RepairCoderResult {
    RepairCoderResult {
        rc: 2,
        tool: tool.to_owned(),
        status: "failed".to_owned(),
        log_file: log_file.to_owned(),
        input_count,
        scrub_count,
        revert_count,
        commit_sha: String::new(),
    }
}

fn pre_attempt_coder_result(input: &RepairCoderInput) -> Option<RepairCoderResult> {
    if input.input_count == 0 {
        return Some(RepairCoderResult::default());
    }
    if !input.scrub_ok {
        return Some(coder_failure("none", "", 0, input.scrub_count, 0));
    }
    if input.scrubbed_count == 0 {
        return Some(RepairCoderResult {
            scrub_count: input.scrub_count,
            ..RepairCoderResult::default()
        });
    }
    if !input.snapshot_valid || !input.snapshot_head_fresh {
        return Some(coder_failure(
            "none",
            &input.tool_log,
            input.scrubbed_count,
            input.scrub_count,
            0,
        ));
    }
    None
}

fn resolve_coder_attempt(
    input: &RepairCoderInput,
    attempt: &RepairCoderAttempt,
) -> Option<RepairCoderResult> {
    if !attempt.dispatched {
        return failed_cleanup_result(input, attempt, 0);
    }
    if attempt.submodule_revert_count > 0 {
        return Some(if attempt.cleanup_ok {
            RepairCoderResult {
                rc: 3,
                tool: attempt.tool.clone(),
                status: "submodule-violation".to_owned(),
                log_file: input.tool_log.clone(),
                input_count: input.scrubbed_count,
                scrub_count: input.scrub_count,
                revert_count: attempt.submodule_revert_count,
                commit_sha: String::new(),
            }
        } else {
            failed_coder_attempt(input, attempt, attempt.submodule_revert_count)
        });
    }
    if attempt.stage_path_count == 0 || attempt.commit == RepairCommitOutcome::Failed {
        return failed_cleanup_result(input, attempt, 0);
    }
    match &attempt.commit {
        RepairCommitOutcome::StaleIndexLock => Some(RepairCoderResult {
            rc: 2,
            tool: attempt.tool.clone(),
            status: "stale-index-lock".to_owned(),
            log_file: input.tool_log.clone(),
            input_count: input.scrubbed_count,
            scrub_count: input.scrub_count,
            revert_count: 0,
            commit_sha: String::new(),
        }),
        RepairCommitOutcome::NotRequested => Some(coder_applied(input, attempt, "")),
        RepairCommitOutcome::Committed(sha) => Some(coder_applied(input, attempt, sha)),
        RepairCommitOutcome::Failed => None,
    }
}

fn failed_cleanup_result(
    input: &RepairCoderInput,
    attempt: &RepairCoderAttempt,
    revert_count: usize,
) -> Option<RepairCoderResult> {
    (!attempt.cleanup_ok).then(|| failed_coder_attempt(input, attempt, revert_count))
}

fn failed_coder_attempt(
    input: &RepairCoderInput,
    attempt: &RepairCoderAttempt,
    revert_count: usize,
) -> RepairCoderResult {
    coder_failure(
        &attempt.tool,
        &input.tool_log,
        input.scrubbed_count,
        input.scrub_count,
        revert_count,
    )
}

fn coder_applied(
    input: &RepairCoderInput,
    attempt: &RepairCoderAttempt,
    commit_sha: &str,
) -> RepairCoderResult {
    RepairCoderResult {
        rc: 0,
        tool: attempt.tool.clone(),
        status: "applied".to_owned(),
        log_file: input.tool_log.clone(),
        input_count: input.scrubbed_count,
        scrub_count: input.scrub_count,
        revert_count: 0,
        commit_sha: commit_sha.to_owned(),
    }
}

fn initial_round_state(input: &RepairRoundInput) -> (String, i32) {
    if input.zero_survivor_panel_failed {
        return ("self-review-required".to_owned(), 0);
    }
    match input.core_status.as_str() {
        "panel-failed" | "aggregator-validation-exhausted" => (input.core_status.clone(), 2),
        "main-agent-vote-required" => ("main-agent-vote-required".to_owned(), 0),
        "fix-required" | "cap-reached" => coder_round_state(&input.coder),
        "prune-skipped" => ("prune-skipped".to_owned(), 0),
        "zero-findings" | "ok" => ("complete".to_owned(), 0),
        _ => (input.core_status.clone(), 0),
    }
}

fn coder_round_state(coder: &RepairCoderResult) -> (String, i32) {
    if coder.rc == 4 || coder.status == "main-agent-required" {
        return ("coder-main-agent-required".to_owned(), 0);
    }
    if matches!(coder.rc, 2 | 3) || coder.status == "submodule-violation" {
        return ("coder-failed".to_owned(), 2);
    }
    match coder.status.as_str() {
        "applied" => ("fix-applied".to_owned(), 0),
        "no-changes" => ("no-changes".to_owned(), 0),
        _ => ("in-scope-filtered-out".to_owned(), 0),
    }
}

fn apply_convergence(status: &mut String, exit_code: &mut i32, input: &RepairRoundInput) {
    if input.classifier == RepairClassifier::Failed {
        "classifier-failed".clone_into(status);
        *exit_code = 2;
        return;
    }
    if !matches!(status.as_str(), "complete" | "no-changes")
        || input.round_counts.accepted == 0
        || input.degraded_round
    {
        return;
    }
    match input.convergence {
        RepairConvergenceEvidence::Findings {
            non_nit_count,
            important_present,
        } if non_nit_count <= 5 && !important_present => {
            "converged-small-changes".clone_into(status);
        }
        RepairConvergenceEvidence::UnreadableFindings { non_nit_count } if non_nit_count > 0 => {
            "classifier-failed".clone_into(status);
            *exit_code = 2;
        }
        _ => {}
    }
}

const fn add_counts(left: RepairCounts, right: RepairCounts) -> RepairCounts {
    RepairCounts {
        accepted: left.accepted + right.accepted,
        rejected: left.rejected + right.rejected,
        exonerated: left.exonerated + right.exonerated,
        neutral: left.neutral + right.neutral,
    }
}

fn apply_composition(
    status: &mut String,
    exit_code: &mut i32,
    total_counts: &mut RepairCounts,
    composition: RepairComposition,
) {
    if *exit_code != 0 {
        return;
    }
    match composition {
        RepairComposition::Succeeded(counts) => {
            total_counts.accepted = counts.accepted;
            total_counts.rejected = counts.rejected;
        }
        RepairComposition::Failed
            if matches!(
                status.as_str(),
                "complete" | "no-changes" | "converged-small-changes"
            ) =>
        {
            "tally-flush-failed".clone_into(status);
            *exit_code = 2;
        }
        RepairComposition::NotRun | RepairComposition::Failed => {}
    }
}

fn rejected_body_lines(text: &str) -> Vec<&str> {
    let lines = text.lines().collect::<Vec<_>>();
    let mut index = 0;
    while lines.get(index).is_some_and(|line| line.trim().is_empty()) {
        index += 1;
    }
    if lines
        .get(index)
        .is_none_or(|line| line.trim() != "# Rejected Findings")
    {
        return lines;
    }
    index += 1;
    while lines.get(index).is_some_and(|line| line.trim().is_empty()) {
        index += 1;
    }
    lines[index..].to_vec()
}

fn selected_summaries(report: &RepairBatchReport) -> Vec<&str> {
    if !report.root_summary.is_empty() {
        return vec![&report.root_summary];
    }
    let mut summaries = report.round_summaries.iter().collect::<Vec<_>>();
    summaries.sort_by_key(|(round, _)| *round);
    summaries
        .into_iter()
        .filter_map(|(_, summary)| (!summary.is_empty()).then_some(summary.as_str()))
        .collect()
}

fn is_summary_count_line(line: &str) -> bool {
    if [
        "- Accepted findings: ",
        "- Rejected findings: ",
        "- Exonerated findings: ",
        "- Neutral findings: ",
    ]
    .iter()
    .any(|prefix| line.starts_with(prefix))
    {
        return true;
    }
    let Some(rest) = line.strip_prefix("- ") else {
        return false;
    };
    let Some((accepted, rest)) = rest.split_once(" accepted, ") else {
        return false;
    };
    let Some((rejected, _tail)) = rest.split_once(" rejected (") else {
        return false;
    };
    !accepted.is_empty()
        && !rejected.is_empty()
        && accepted.bytes().all(|byte| byte.is_ascii_digit())
        && rejected.bytes().all(|byte| byte.is_ascii_digit())
}

fn first_nonempty<'value>(first: &'value str, second: &'value str) -> Option<&'value str> {
    (!first.is_empty())
        .then_some(first)
        .or_else(|| (!second.is_empty()).then_some(second))
}

fn render_rejected_findings_for_tally(text: &str) -> String {
    let mut output = Vec::new();
    for line in text.lines() {
        let starts_block =
            line.starts_with("### [") || is_canonical_heading(line, Some(ItemKind::Finding));
        if starts_block || !output.is_empty() {
            output.push(line);
        }
    }
    output.join("\n")
}

fn normalize_unsigned_decimal(value: &str) -> Option<&str> {
    if value.is_empty() || !value.bytes().all(|byte| byte.is_ascii_digit()) {
        return None;
    }
    let normalized = value.trim_start_matches('0');
    Some(if normalized.is_empty() {
        "0"
    } else {
        normalized
    })
}

fn path_basename(path: &str) -> &str {
    Path::new(path)
        .file_name()
        .and_then(|name| name.to_str())
        .unwrap_or_default()
}

fn json_string(value: &str) -> String {
    serde_json::to_string(value).expect("serializing a string cannot fail")
}
