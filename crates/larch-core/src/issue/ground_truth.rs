//! Ground-truth model binding panel findings to later issues and run evidence.
//!
//! Library parity for the in-scope half of Python `larch.issue._ground_truth`.
//! This leaf ports no command. Classification-TSV row construction stays with
//! the voting layer, the out-of-scope filed-issue join stays with the
//! out-of-scope core leaf, and the verdict-mode argument grammar stays with the
//! analysis command leaf. This module owns the evidence model, the
//! realized-outcome classification, the voter metrics, and the corpus scan that
//! feeds them.

use chrono::{DateTime, Utc};
use regex::Regex;
use std::{
    collections::{BTreeMap, BTreeSet},
    path::{Path, PathBuf},
    sync::LazyLock,
};

use super::report_core::{IssueCategory, IssueSummary, category_pattern, title_tokens};
use crate::{
    RunLogCorpus, RunLogCorpusEvent, RunLogCorpusWarning, RunLogRoundSort, RunLogRun,
    RunLogSelection, RunLogSlug, round_number_from_path,
};

/// Row count above which the accepted-finding evidence index is disabled.
pub const LARGE_CORPUS_ROW_LIMIT: usize = 5000;
/// Accepted-finding population below which every in-panel finding is a candidate.
const ACCEPTED_EVIDENCE_BROADCAST_LIMIT: usize = 50;
/// Skills whose classification artifacts carry ground-truth rows, in scan order.
const GROUND_TRUTH_SKILLS: [&str; 3] = ["design", "implement", "review"];

static REVERSAL_PATTERN: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(
        r"\b(?i-u:revert|reverted|undo|regress|regression|superseded|re-introduce|re-add|closed in favor of)\b",
    )
    .expect("reversal regex should compile")
});

static DIAGNOSTIC_LINE_SUFFIX: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r":\d+(?:-\d+)?$").expect("line-suffix regex should compile"));

const LONG_EXTS: &str = "cc|cfg|cjs|cpp|css|csv|cs|dart|gradle|groovy|go|html|htm|hpp|java|json|jsx|js|kt|lua|mjs|mk|mm|md|php|pl|proto|py|rb|rs|sass|scala|scss|sh|sql|swift|toml|tsx|tsv|ts|vue|xml|yaml|yml";
const SHORT_EXTS: &str = "lock|env|txt|c|h|m|r";

static DIAGNOSTIC_PATH_PATTERNS: LazyLock<[Regex; 2]> = LazyLock::new(|| {
    let long = format!(
        r"(^|[^A-Za-z0-9])\.?[A-Za-z_][A-Za-z0-9_./-]*\.((?i-u:{LONG_EXTS}))(:[0-9]+(-[0-9]+)?)?($|[^A-Za-z0-9_:/-])"
    );
    let short_path = format!(
        r"(^|[^A-Za-z0-9])\.?[A-Za-z_][A-Za-z0-9_./-]*[/_-][A-Za-z0-9_./-]*\.((?i-u:{SHORT_EXTS}))(:[0-9]+(-[0-9]+)?)?($|[^A-Za-z0-9_:/-])"
    );
    let short_line = format!(
        r"(^|[^A-Za-z0-9])\.?[A-Za-z_][A-Za-z0-9_./-]*\.((?i-u:{SHORT_EXTS})):[0-9]+(-[0-9]+)?($|[^A-Za-z0-9_:/-])"
    );
    [
        Regex::new(&format!("{long}|{short_path}|{short_line}"))
            .expect("file-line regex should compile"),
        Regex::new(
            r"(^|[^A-Za-z0-9_])((?i-u:Makefile|Dockerfile|GNUmakefile))(:[0-9]+(-[0-9]+)?)?",
        )
        .expect("extensionless file regex should compile"),
    ]
});

/// Which panel produced a ground-truth row.
#[derive(Clone, Copy, Debug, Eq, Hash, Ord, PartialEq, PartialOrd)]
pub enum PanelKind {
    /// The `/design` plan-review panel.
    Design,
    /// The `/implement` and standalone code-review panels.
    CodeReview,
}

impl PanelKind {
    /// Return the Python panel token.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Design => "design",
            Self::CodeReview => "code-review",
        }
    }

    /// Map a run-log skill directory name to its panel.
    #[must_use]
    pub fn for_skill(skill: &str) -> Self {
        if skill == "design" {
            Self::Design
        } else {
            Self::CodeReview
        }
    }
}

/// The authoritative panel verdict bound to a row.
#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub enum PanelVerdict {
    /// The panel accepted the finding.
    Accepted,
    /// The panel rejected the finding.
    Rejected,
    /// No authoritative verdict was bound.
    Missing,
}

impl PanelVerdict {
    /// Return whether this verdict can carry a realized outcome.
    #[must_use]
    pub const fn is_decisive_candidate(self) -> bool {
        matches!(self, Self::Accepted | Self::Rejected)
    }
}

/// One voter ballot on a row. Absent and unreadable ballots are `Missing`.
#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub enum VoterBallot {
    /// The voter voted to accept.
    Yes,
    /// The voter voted to reject.
    No,
    /// The ballot was absent or unreadable.
    Missing,
}

/// One voter's ballot and declared severity on a row.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct GroundTruthVoter {
    pub voter: String,
    pub ballot: VoterBallot,
    pub severity: String,
}

/// Where one piece of realized evidence came from.
#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub enum EvidenceSource {
    /// A later GitHub issue.
    Issue,
    /// A later accepted panel finding.
    AcceptedFinding,
}

impl EvidenceSource {
    /// Return the Python source token.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Issue => "issue",
            Self::AcceptedFinding => "accepted-finding",
        }
    }
}

/// One later signal a row's verdict can be judged against. Run fields are empty
/// for issue evidence; `created_at` is absent for finding evidence.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct GroundTruthEvidence {
    pub source: EvidenceSource,
    pub run_id: String,
    pub run_dir_key: String,
    pub round_num: u32,
    pub started_at: Option<DateTime<Utc>>,
    pub created_at: Option<DateTime<Utc>>,
    pub title: String,
    pub text: String,
    pub category: String,
    pub issue_number: Option<u64>,
    pub not_planned: bool,
}

/// One classified panel finding, bound to its run and its prose verdict.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct GroundTruthRow {
    pub panel_kind: PanelKind,
    pub run_id: String,
    /// Log-root-relative run directory, as [`run_dir_key`] returns it.
    pub run_dir_key: String,
    pub round_num: u32,
    pub started_at: Option<DateTime<Utc>>,
    pub run_ended_at: Option<DateTime<Utc>>,
    pub multi_round: bool,
    pub finding_id: String,
    pub title: String,
    pub prose_text: String,
    pub category: String,
    pub verdict: PanelVerdict,
    /// Why the bound verdict is not trustworthy, when it is not.
    pub weak_reason: Option<String>,
    /// One entry per voter slot. Like Python, the metric folds trust the
    /// producing layer to emit each voter at most once per row.
    pub voters: Vec<GroundTruthVoter>,
}

impl GroundTruthRow {
    /// Return the text a match is computed from.
    #[must_use]
    pub fn match_text(&self) -> String {
        format!("{}\n{}\n{}", self.title, self.prose_text, self.finding_id)
    }

    /// Return the leading panel-root segment of the run directory key.
    #[must_use]
    pub fn panel_root(&self) -> &str {
        panel_root(&self.run_dir_key)
    }
}

fn panel_root(run_dir_key: &str) -> &str {
    run_dir_key
        .split_once('/')
        .map_or(run_dir_key, |(head, _)| head)
}

/// Realized-outcome bucket for one row.
#[derive(Clone, Copy, Debug, Eq, Hash, Ord, PartialEq, PartialOrd)]
pub enum OutcomeBucket {
    /// The bound prose verdict was weak or self-contradictory.
    WeakProseVerdict,
    /// No authoritative panel verdict was bound.
    WeakPanelVerdict,
    /// An accepted finding was later reverted or regressed.
    AcceptedRevertedOrRegressed,
    /// A rejected finding later resurfaced.
    RejectedResurfaced,
    /// An accepted finding drew no later counter-evidence.
    AcceptedNoCounterevidence,
    /// A rejected finding was never observed again.
    RejectedNotObserved,
    /// An issue-backed reversal was suppressed by degraded enrichment.
    EnrichmentDegradedReversal,
    /// An issue-backed resurfacing was suppressed by degraded enrichment.
    EnrichmentDegradedResurfacing,
}

impl OutcomeBucket {
    /// Return the exact Python bucket token.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::WeakProseVerdict => "weak_prose_verdict",
            Self::WeakPanelVerdict => "weak_panel_verdict",
            Self::AcceptedRevertedOrRegressed => "accepted_reverted_or_regressed",
            Self::RejectedResurfaced => "rejected_resurfaced",
            Self::AcceptedNoCounterevidence => "accepted_no_counterevidence",
            Self::RejectedNotObserved => "rejected_not_observed",
            Self::EnrichmentDegradedReversal => "enrichment-degraded-reversal",
            Self::EnrichmentDegradedResurfacing => "enrichment-degraded-resurfacing",
        }
    }

    /// Return whether this bucket realizes a decisive outcome. Decisiveness and
    /// direction live on the bucket so no caller re-derives the terminal set.
    #[must_use]
    pub const fn is_decisive(self) -> bool {
        matches!(
            self,
            Self::AcceptedRevertedOrRegressed | Self::RejectedResurfaced
        )
    }

    /// Return the direction a decisive bucket points.
    #[must_use]
    pub const fn direction(self) -> OutcomeDirection {
        match self {
            Self::AcceptedRevertedOrRegressed => OutcomeDirection::ContradictsAcceptance,
            Self::RejectedResurfaced => OutcomeDirection::SupportsAcceptance,
            _ => OutcomeDirection::None,
        }
    }

    const fn reason(self) -> &'static str {
        match self {
            Self::AcceptedRevertedOrRegressed => "later matching reversal or regression signal",
            Self::RejectedResurfaced => "later matching issue or accepted finding",
            Self::EnrichmentDegradedReversal => {
                "issue-backed reversal suppressed by enrichment degradation"
            }
            Self::EnrichmentDegradedResurfacing => {
                "issue-backed resurfacing suppressed by enrichment degradation"
            }
            Self::AcceptedNoCounterevidence => "no later matching reversal signal",
            Self::RejectedNotObserved => "no later strong resurfacing match",
            Self::WeakPanelVerdict => "missing authoritative panel verdict",
            Self::WeakProseVerdict => "weak prose verdict",
        }
    }
}

/// Which way a decisive outcome points relative to acceptance.
#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub enum OutcomeDirection {
    /// The realized outcome supports accepting the finding.
    SupportsAcceptance,
    /// The realized outcome contradicts accepting the finding.
    ContradictsAcceptance,
    /// The outcome is not decisive.
    None,
}

impl OutcomeDirection {
    /// Return the Python direction token, empty when non-decisive.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::SupportsAcceptance => "supports_acceptance",
            Self::ContradictsAcceptance => "contradicts_acceptance",
            Self::None => "",
        }
    }
}

/// One row's realized outcome, plus the candidates it could not order in time.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct GroundTruthOutcome {
    pub bucket: OutcomeBucket,
    pub reason: String,
    pub timestamp_degraded_matches: usize,
}

impl GroundTruthOutcome {
    /// Return whether this outcome is decisive.
    #[must_use]
    pub const fn is_decisive(&self) -> bool {
        self.bucket.is_decisive()
    }

    /// Return the direction this outcome points.
    #[must_use]
    pub const fn direction(&self) -> OutcomeDirection {
        self.bucket.direction()
    }
}

/// Why one piece of evidence is not later than a row.
#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub enum NotLaterReason {
    /// Accepted-finding evidence came from a different panel root.
    PanelRootMismatch,
    /// The evidence shares the run and is not a later round.
    SameRunNotLater,
    /// The evidence may fall inside the run's own rounds.
    SameRunUnproved,
    /// Both timestamps were readable and the evidence was not later.
    NotLater,
    /// No timestamp pair could prove ordering.
    TimestampDegraded,
}

impl NotLaterReason {
    /// Return the exact Python reason token.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::PanelRootMismatch => "accepted-finding panel root mismatch",
            Self::SameRunNotLater => "same-run round ordering is not later",
            Self::SameRunUnproved => "same-run round ordering unproved",
            Self::NotLater => "not later",
            Self::TimestampDegraded => "timestamp-degraded",
        }
    }
}

/// Whether evidence provably follows a row.
#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub enum EvidenceOrdering {
    /// The evidence provably follows the row.
    Later,
    /// The evidence does not provably follow the row.
    NotLater(NotLaterReason),
}

/// Normalize a candidate diagnostic path reference.
///
/// Python strips punctuation only, so a reference that keeps its surrounding
/// separator keeps it here too, and a trailing separator un-anchors the line
/// hint. Both sides of a match run through this one rule, so the port preserves
/// the artifact instead of changing which rows match.
#[must_use]
pub fn normalize_diagnostic_path(raw: &str) -> String {
    let trimmed = raw.trim_matches(|character: char| "`*_#[](){}<>.,;:'\"".contains(character));
    let without_line = DIAGNOSTIC_LINE_SUFFIX.replace(trimmed, "");
    let value = without_line.trim_start_matches(['.', '/']).to_lowercase();
    if value.is_empty() || value.split('/').any(|part| part == "..") || value.starts_with('~') {
        return String::new();
    }
    value
}

/// Extract normalized file references from free-form finding or issue text.
#[must_use]
pub fn diagnostic_paths(text: &str) -> BTreeSet<String> {
    let mut paths = BTreeSet::new();
    for pattern in DIAGNOSTIC_PATH_PATTERNS.iter() {
        for captures in pattern.captures_iter(text) {
            let whole = captures.get(0).map_or("", |found| found.as_str());
            let first_group = captures
                .iter()
                .skip(1)
                .flatten()
                .map(|group| group.as_str())
                .find(|group| !group.is_empty());
            let candidate = match first_group {
                Some(group) if group.contains('/') || group.contains('.') => group,
                _ => whole,
            };
            let normalized = normalize_diagnostic_path(candidate);
            if !normalized.is_empty() {
                paths.insert(normalized);
            }
        }
    }
    paths
}

/// Extract the distinctive token set used for evidence matching.
#[must_use]
pub fn distinctive_tokens(text: &str) -> BTreeSet<String> {
    title_tokens(text).into_iter().collect()
}

/// The token and path sets one text contributes to evidence matching.
///
/// Python memoizes both extractions, so a profile is computed once per text and
/// reused instead of re-running the regex scans for every row-evidence pair.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct MatchProfile {
    tokens: BTreeSet<String>,
    paths: BTreeSet<String>,
}

impl MatchProfile {
    /// Extract the tokens and paths of one text.
    #[must_use]
    pub fn of_text(text: &str) -> Self {
        Self {
            tokens: distinctive_tokens(text),
            paths: diagnostic_paths(text),
        }
    }

    /// Extract the profile a row is matched by.
    #[must_use]
    pub fn of_row(row: &GroundTruthRow) -> Self {
        Self::of_text(&row.match_text())
    }

    /// Extract the profile a piece of evidence is matched by.
    #[must_use]
    pub fn of_evidence(evidence: &GroundTruthEvidence) -> Self {
        Self::of_text(&format!("{}\n{}", evidence.title, evidence.text))
    }

    /// Return the distinctive tokens.
    #[must_use]
    pub const fn tokens(&self) -> &BTreeSet<String> {
        &self.tokens
    }

    /// Return the normalized file references.
    #[must_use]
    pub const fn paths(&self) -> &BTreeSet<String> {
        &self.paths
    }

    /// Return whether two profiles agree strongly enough to bind a row to
    /// evidence. This is the single owner of the strong-match rule.
    #[must_use]
    pub fn matches(&self, other: &Self) -> bool {
        let overlap = self.tokens.intersection(&other.tokens).count();
        if self.paths.intersection(&other.paths).next().is_some() && overlap >= 2 {
            return true;
        }
        let smallest = self.tokens.len().min(other.tokens.len());
        if smallest <= 4 {
            return overlap >= smallest.max(2);
        }
        #[expect(
            clippy::cast_precision_loss,
            clippy::cast_possible_truncation,
            clippy::cast_sign_loss,
            reason = "token counts are small and the Python rule truncates the same product"
        )]
        let scaled = (smallest as f64 * 0.6) as usize;
        overlap >= scaled.max(3)
    }
}

/// Return whether evidence is a strong enough match for one row.
#[must_use]
pub fn strong_match(row: &GroundTruthRow, evidence: &GroundTruthEvidence) -> bool {
    MatchProfile::of_row(row).matches(&MatchProfile::of_evidence(evidence))
}

/// Return whether evidence provably follows a row, and why not when it does not.
#[must_use]
pub fn evidence_ordering(row: &GroundTruthRow, evidence: &GroundTruthEvidence) -> EvidenceOrdering {
    if evidence.source == EvidenceSource::AcceptedFinding
        && !evidence.run_dir_key.is_empty()
        && panel_root(&evidence.run_dir_key) != row.panel_root()
    {
        return EvidenceOrdering::NotLater(NotLaterReason::PanelRootMismatch);
    }
    if !evidence.run_dir_key.is_empty() && evidence.run_dir_key == row.run_dir_key {
        return if evidence.round_num > row.round_num {
            EvidenceOrdering::Later
        } else {
            EvidenceOrdering::NotLater(NotLaterReason::SameRunNotLater)
        };
    }
    if evidence.source == EvidenceSource::Issue && evidence.run_id.is_empty() {
        return issue_evidence_ordering(row, evidence);
    }
    if let (Some(row_started), Some(evidence_started)) = (row.started_at, evidence.started_at) {
        return later_or_not(evidence_started > row_started);
    }
    if let (Some(row_started), Some(created_at)) = (row.started_at, evidence.created_at) {
        return later_or_not(created_at > row_started);
    }
    EvidenceOrdering::NotLater(NotLaterReason::TimestampDegraded)
}

fn issue_evidence_ordering(
    row: &GroundTruthRow,
    evidence: &GroundTruthEvidence,
) -> EvidenceOrdering {
    let (Some(row_started), Some(created_at)) = (row.started_at, evidence.created_at) else {
        return EvidenceOrdering::NotLater(NotLaterReason::TimestampDegraded);
    };
    if created_at <= row_started {
        return EvidenceOrdering::NotLater(NotLaterReason::NotLater);
    }
    if !row.multi_round {
        return EvidenceOrdering::Later;
    }
    match row.run_ended_at {
        Some(ended_at) if created_at > ended_at => EvidenceOrdering::Later,
        _ => EvidenceOrdering::NotLater(NotLaterReason::SameRunUnproved),
    }
}

const fn later_or_not(later: bool) -> EvidenceOrdering {
    if later {
        EvidenceOrdering::Later
    } else {
        EvidenceOrdering::NotLater(NotLaterReason::NotLater)
    }
}

/// Build issue-backed evidence in issue order.
#[must_use]
pub fn issue_evidence(issues: &[IssueSummary]) -> Vec<GroundTruthEvidence> {
    issues
        .iter()
        .map(|issue| GroundTruthEvidence {
            source: EvidenceSource::Issue,
            run_id: String::new(),
            run_dir_key: String::new(),
            round_num: 0,
            started_at: None,
            created_at: issue.created_at,
            title: issue.title.clone(),
            text: issue.text(),
            category: issue.default_category().as_str().to_owned(),
            issue_number: Some(issue.number),
            not_planned: issue.not_planned(),
        })
        .collect()
}

/// Build accepted-finding evidence from trustworthy accepted rows, in row order.
#[must_use]
pub fn accepted_finding_evidence(rows: &[GroundTruthRow]) -> Vec<GroundTruthEvidence> {
    rows.iter()
        .filter(|row| row.verdict == PanelVerdict::Accepted && row.weak_reason.is_none())
        .map(|row| GroundTruthEvidence {
            source: EvidenceSource::AcceptedFinding,
            run_id: row.run_id.clone(),
            run_dir_key: row.run_dir_key.clone(),
            round_num: row.round_num,
            started_at: row.started_at,
            created_at: None,
            title: if row.title.is_empty() {
                row.finding_id.clone()
            } else {
                row.title.clone()
            },
            text: row.prose_text.clone(),
            category: row.category.clone(),
            issue_number: None,
            not_planned: false,
        })
        .collect()
}

/// Owned evidence plus its per-item match profiles and token index.
///
/// Profiles are extracted once at build time, so candidate selection costs set
/// intersections rather than a regex scan per row-evidence pair.
#[derive(Clone, Debug, Default)]
pub struct EvidenceIndex {
    items: Vec<GroundTruthEvidence>,
    profiles: Vec<MatchProfile>,
    by_token: BTreeMap<String, Vec<usize>>,
}

impl EvidenceIndex {
    /// Take ownership of evidence and index it by its distinctive tokens.
    #[must_use]
    pub fn build(items: Vec<GroundTruthEvidence>) -> Self {
        let mut by_token: BTreeMap<String, Vec<usize>> = BTreeMap::new();
        let mut profiles = Vec::with_capacity(items.len());
        for (position, item) in items.iter().enumerate() {
            let profile = MatchProfile::of_evidence(item);
            for token in profile.tokens() {
                by_token.entry(token.clone()).or_default().push(position);
            }
            profiles.push(profile);
        }
        Self {
            items,
            profiles,
            by_token,
        }
    }

    /// Return the indexed evidence in build order.
    #[must_use]
    pub fn items(&self) -> &[GroundTruthEvidence] {
        &self.items
    }

    /// Return the number of indexed items.
    #[must_use]
    pub const fn len(&self) -> usize {
        self.items.len()
    }

    /// Return whether nothing was indexed.
    #[must_use]
    pub const fn is_empty(&self) -> bool {
        self.items.is_empty()
    }

    /// Return the evidence positions that carry one token.
    #[must_use]
    pub fn positions(&self, token: &str) -> &[usize] {
        self.by_token.get(token).map_or(&[], Vec::as_slice)
    }

    /// Return the indexed item at one position.
    #[must_use]
    pub fn get(&self, position: usize) -> Option<&GroundTruthEvidence> {
        self.items.get(position)
    }

    /// Return the match profile at one position.
    #[must_use]
    pub fn profile(&self, position: usize) -> Option<&MatchProfile> {
        self.profiles.get(position)
    }
}

/// Select the evidence worth judging one row against, in evaluation order.
///
/// Token iteration is sorted, so the candidate order never depends on hash or
/// filesystem ordering.
#[must_use]
pub fn candidate_evidence(
    row: &GroundTruthRow,
    issues: &EvidenceIndex,
    accepted: &EvidenceIndex,
) -> Vec<GroundTruthEvidence> {
    let source_tokens = distinctive_tokens(&row.match_text());
    // The candidate filter reads paths from the title and prose only, while the
    // strong-match rule also reads the finding id.
    let source_paths = diagnostic_paths(&format!("{}\n{}", row.title, row.prose_text));
    let mut ranked_issues: Vec<(usize, usize)> = issues
        .profiles
        .iter()
        .enumerate()
        .filter_map(|(position, profile)| {
            let overlap = source_tokens.intersection(profile.tokens()).count();
            if overlap == 0 && source_paths.intersection(profile.paths()).next().is_none() {
                return None;
            }
            Some((overlap, position))
        })
        .collect();
    ranked_issues.sort_by(|left, right| right.0.cmp(&left.0));
    let issue_candidates = ranked_issues
        .into_iter()
        .filter_map(|(_, position)| issues.get(position).cloned());

    if row.verdict == PanelVerdict::Rejected {
        let mut seen: BTreeSet<(String, String, u32)> = BTreeSet::new();
        let mut accepted_candidates: Vec<GroundTruthEvidence> = Vec::new();
        for token in &source_tokens {
            for position in accepted.positions(token) {
                let Some(item) = accepted.get(*position) else {
                    continue;
                };
                if panel_root(&item.run_dir_key) != row.panel_root() {
                    continue;
                }
                let key = (item.run_dir_key.clone(), item.title.clone(), item.round_num);
                if seen.insert(key) {
                    accepted_candidates.push(item.clone());
                }
            }
        }
        accepted_candidates.extend(issue_candidates);
        return accepted_candidates;
    }
    let mut candidates: Vec<GroundTruthEvidence> = issue_candidates.collect();
    if accepted.len() < ACCEPTED_EVIDENCE_BROADCAST_LIMIT {
        candidates.extend(
            accepted
                .items()
                .iter()
                .filter(|item| panel_root(&item.run_dir_key) == row.panel_root())
                .cloned(),
        );
    }
    candidates
}

/// Classify one in-scope row against its candidate evidence.
#[must_use]
pub fn classify_in_scope(
    row: &GroundTruthRow,
    candidates: &[GroundTruthEvidence],
    enrichment_degraded: Option<&str>,
) -> GroundTruthOutcome {
    if let Some(reason) = &row.weak_reason {
        return GroundTruthOutcome {
            bucket: OutcomeBucket::WeakProseVerdict,
            reason: reason.clone(),
            timestamp_degraded_matches: 0,
        };
    }
    if !row.verdict.is_decisive_candidate() {
        return GroundTruthOutcome {
            bucket: OutcomeBucket::WeakPanelVerdict,
            reason: OutcomeBucket::WeakPanelVerdict.reason().to_owned(),
            timestamp_degraded_matches: 0,
        };
    }
    let mut timestamp_degraded_matches = 0_usize;
    let row_profile = MatchProfile::of_row(row);
    for item in candidates {
        match evidence_ordering(row, item) {
            EvidenceOrdering::Later => {}
            EvidenceOrdering::NotLater(NotLaterReason::TimestampDegraded) => {
                timestamp_degraded_matches += 1;
                continue;
            }
            EvidenceOrdering::NotLater(_) => continue,
        }
        if !row_profile.matches(&MatchProfile::of_evidence(item)) {
            continue;
        }
        if let Some(bucket) = decisive_bucket(row, item, enrichment_degraded) {
            return GroundTruthOutcome {
                bucket,
                reason: bucket.reason().to_owned(),
                timestamp_degraded_matches,
            };
        }
    }
    let bucket = if row.verdict == PanelVerdict::Accepted {
        OutcomeBucket::AcceptedNoCounterevidence
    } else {
        OutcomeBucket::RejectedNotObserved
    };
    GroundTruthOutcome {
        bucket,
        reason: bucket.reason().to_owned(),
        timestamp_degraded_matches,
    }
}

fn decisive_bucket(
    row: &GroundTruthRow,
    item: &GroundTruthEvidence,
    enrichment_degraded: Option<&str>,
) -> Option<OutcomeBucket> {
    let text = format!("{}\n{}\n{}", item.title, item.text, item.category);
    let reversal = REVERSAL_PATTERN.is_match(&text);
    let issue_backed = item.source == EvidenceSource::Issue;
    if row.verdict == PanelVerdict::Accepted {
        if !reversal {
            return None;
        }
        if enrichment_degraded.is_some() && issue_backed {
            return Some(OutcomeBucket::EnrichmentDegradedReversal);
        }
        return Some(OutcomeBucket::AcceptedRevertedOrRegressed);
    }
    if !resurfacing_signal(item, &text) {
        return None;
    }
    if enrichment_degraded.is_some() && issue_backed {
        return Some(OutcomeBucket::EnrichmentDegradedResurfacing);
    }
    if issue_backed && item.not_planned && !reversal {
        return None;
    }
    Some(OutcomeBucket::RejectedResurfaced)
}

fn resurfacing_signal(item: &GroundTruthEvidence, text: &str) -> bool {
    if item.source == EvidenceSource::AcceptedFinding {
        return true;
    }
    let categories = [
        IssueCategory::BugFix,
        IssueCategory::TestCoverage,
        IssueCategory::HardeningValidationSecurity,
    ];
    if categories
        .iter()
        .any(|category| item.category == category.as_str())
    {
        return true;
    }
    category_pattern(IssueCategory::BugFix).is_some_and(|pattern| pattern.is_match(text))
}

/// Realized alignment metrics for one panel and voter.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct VoterMetric {
    pub panel: PanelKind,
    pub voter: String,
    pub decisive: usize,
    pub aligned: usize,
    pub misaligned: usize,
    pub missing: usize,
    pub false_positive_yes: usize,
    pub false_negative_no: usize,
}

/// Realized alignment metrics for one panel, voter, and declared severity.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct VoterSeverityMetric {
    pub panel: PanelKind,
    pub voter: String,
    /// The declared severity, or `(missing)`.
    pub severity: String,
    pub decisive_yes: usize,
    pub aligned: usize,
    pub misaligned: usize,
    pub missing_severity: usize,
}

/// Return the realized alignment rate, absent when no ballot was decisive.
#[must_use]
pub fn realized_alignment_rate(aligned: usize, misaligned: usize) -> Option<f64> {
    let denominator = aligned + misaligned;
    #[expect(
        clippy::cast_precision_loss,
        reason = "ballot counts stay far below the f64 integer range"
    )]
    let rate = (denominator > 0).then(|| aligned as f64 / denominator as f64);
    rate
}

/// Counters describing one ground-truth analysis pass.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct GroundTruthStats {
    pub decisive_rows: usize,
    pub weak_rows: usize,
    pub timestamp_degraded: usize,
    pub verdict_disagreement: usize,
    pub enrichment_degraded_rows: usize,
    /// Whether the accepted-finding index was disabled for corpus size.
    pub large_corpus_skip: bool,
    pub buckets: BTreeMap<OutcomeBucket, usize>,
}

/// One complete ground-truth analysis pass.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct GroundTruthAnalysis {
    /// One outcome per input row, in row order.
    pub outcomes: Vec<GroundTruthOutcome>,
    pub stats: GroundTruthStats,
    /// Per-voter metrics in panel then voter order.
    pub metrics: Vec<VoterMetric>,
    /// Per-severity metrics in panel, voter, then severity order.
    pub severity_metrics: Vec<VoterSeverityMetric>,
}

/// Classify every in-scope row against later issues and accepted findings.
#[must_use]
pub fn analyze_ground_truth(
    rows: &[GroundTruthRow],
    issues: &[IssueSummary],
    enrichment_degraded: Option<&str>,
) -> GroundTruthAnalysis {
    let issue_index = EvidenceIndex::build(issue_evidence(issues));
    let large_corpus = rows.len() > LARGE_CORPUS_ROW_LIMIT;
    let accepted_index = EvidenceIndex::build(if large_corpus {
        Vec::new()
    } else {
        accepted_finding_evidence(rows)
    });
    let mut stats = GroundTruthStats {
        large_corpus_skip: large_corpus,
        ..GroundTruthStats::default()
    };
    let mut outcomes = Vec::with_capacity(rows.len());
    let mut metrics: BTreeMap<(PanelKind, String), VoterMetric> = BTreeMap::new();
    let mut severity: BTreeMap<(PanelKind, String, String), VoterSeverityMetric> = BTreeMap::new();
    for row in rows {
        let candidates = if row.weak_reason.is_some() || !row.verdict.is_decisive_candidate() {
            Vec::new()
        } else {
            candidate_evidence(row, &issue_index, &accepted_index)
        };
        let outcome = classify_in_scope(row, &candidates, enrichment_degraded);
        record_stats(&mut stats, row, &outcome, enrichment_degraded);
        update_voter_metrics(&mut metrics, row, &outcome);
        update_severity_metrics(&mut severity, row, &outcome);
        outcomes.push(outcome);
    }
    GroundTruthAnalysis {
        outcomes,
        stats,
        metrics: metrics.into_values().collect(),
        severity_metrics: severity.into_values().collect(),
    }
}

fn record_stats(
    stats: &mut GroundTruthStats,
    row: &GroundTruthRow,
    outcome: &GroundTruthOutcome,
    enrichment_degraded: Option<&str>,
) {
    if row
        .weak_reason
        .as_deref()
        .is_some_and(|reason| reason.contains("disagreement"))
    {
        stats.verdict_disagreement += 1;
    }
    if enrichment_degraded.is_some()
        && row.weak_reason.is_none()
        && row.verdict.is_decisive_candidate()
    {
        stats.enrichment_degraded_rows += 1;
    }
    stats.timestamp_degraded += outcome.timestamp_degraded_matches;
    *stats.buckets.entry(outcome.bucket).or_insert(0) += 1;
    if outcome.is_decisive() {
        stats.decisive_rows += 1;
    } else {
        stats.weak_rows += 1;
    }
}

fn update_voter_metrics(
    metrics: &mut BTreeMap<(PanelKind, String), VoterMetric>,
    row: &GroundTruthRow,
    outcome: &GroundTruthOutcome,
) {
    if !outcome.is_decisive() {
        return;
    }
    let supports = outcome.direction() == OutcomeDirection::SupportsAcceptance;
    for voter in &row.voters {
        let metric = metrics
            .entry((row.panel_kind, voter.voter.clone()))
            .or_insert_with(|| VoterMetric {
                panel: row.panel_kind,
                voter: voter.voter.clone(),
                decisive: 0,
                aligned: 0,
                misaligned: 0,
                missing: 0,
                false_positive_yes: 0,
                false_negative_no: 0,
            });
        if voter.ballot == VoterBallot::Missing {
            metric.missing += 1;
            continue;
        }
        metric.decisive += 1;
        if (voter.ballot == VoterBallot::Yes) == supports {
            metric.aligned += 1;
            continue;
        }
        metric.misaligned += 1;
        if voter.ballot == VoterBallot::Yes {
            metric.false_positive_yes += 1;
        } else {
            metric.false_negative_no += 1;
        }
    }
}

fn update_severity_metrics(
    metrics: &mut BTreeMap<(PanelKind, String, String), VoterSeverityMetric>,
    row: &GroundTruthRow,
    outcome: &GroundTruthOutcome,
) {
    if !outcome.is_decisive() {
        return;
    }
    let supports = outcome.direction() == OutcomeDirection::SupportsAcceptance;
    for voter in &row.voters {
        if voter.ballot != VoterBallot::Yes {
            continue;
        }
        let declared = voter.severity.trim();
        let severity = if declared.is_empty() {
            "(missing)".to_owned()
        } else {
            declared.to_owned()
        };
        let metric = metrics
            .entry((row.panel_kind, voter.voter.clone(), severity.clone()))
            .or_insert_with(|| VoterSeverityMetric {
                panel: row.panel_kind,
                voter: voter.voter.clone(),
                severity,
                decisive_yes: 0,
                aligned: 0,
                misaligned: 0,
                missing_severity: 0,
            });
        metric.decisive_yes += 1;
        if declared.is_empty() {
            metric.missing_severity += 1;
        }
        if supports {
            metric.aligned += 1;
        } else {
            metric.misaligned += 1;
        }
    }
}

/// Which ground-truth corpus a scan selects.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum GroundTruthMode {
    /// Every discoverable run, used by the diagnostic calibration report.
    Calibration,
    /// Only runs that pass the capstone verdict minima.
    Verdict,
}

/// Corpus selection inputs for a verdict-mode ground-truth scan.
#[derive(Clone, Debug, Default)]
pub struct CorpusFilter {
    pub since_date: Option<DateTime<Utc>>,
    pub min_larch_version: Option<String>,
}

/// One discovered classification artifact and its run binding.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ClassificationSource {
    pub panel_kind: PanelKind,
    pub path: PathBuf,
    pub run_dir: PathBuf,
    pub run_dir_key: String,
    pub run_id: String,
    pub round_num: u32,
    pub started_at: Option<DateTime<Utc>>,
    pub run_ended_at: Option<DateTime<Utc>>,
    pub multi_round: bool,
}

/// Run-selection counters for one corpus scan.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct CorpusScanStats {
    /// Every discovered classification artifact. Python additionally drops
    /// review artifacts whose TSV schema is unsupported, which needs the file
    /// bytes; the voting layer that reads them owns that filter.
    pub files_seen: usize,
    pub gc_slimmed_runs: usize,
    pub qualifying_runs: usize,
    pub excluded_pre_since_runs: usize,
    pub excluded_missing_started_at_runs: usize,
    pub excluded_below_version_runs: usize,
    pub excluded_missing_version_runs: usize,
    pub excluded_gc_slimmed_runs: usize,
}

/// One corpus scan result.
#[derive(Clone, Debug)]
pub struct GroundTruthCorpusScan {
    /// Discovered classification artifacts, in deterministic scan order.
    pub sources: Vec<ClassificationSource>,
    pub stats: CorpusScanStats,
    /// Structured walker warnings for unreadable or unsafe artifacts.
    pub warnings: Vec<RunLogCorpusWarning>,
}

/// Discover ground-truth classification artifacts through the shared walker.
///
/// The scan visits skills in a fixed order and each run's artifacts in the
/// walker's deterministic order, so the result never depends on directory
/// enumeration order. Unreadable or unsafe artifacts surface as warnings rather
/// than being dropped.
#[must_use]
pub fn scan_ground_truth_corpus(
    log_root: &Path,
    mode: GroundTruthMode,
    filter: &CorpusFilter,
) -> GroundTruthCorpusScan {
    let skills: Vec<RunLogSlug> = GROUND_TRUTH_SKILLS
        .iter()
        .filter_map(|skill| RunLogSlug::parse(*skill).ok())
        .collect();
    let corpus = RunLogCorpus::new(log_root);
    let mut scan = GroundTruthCorpusScan {
        sources: Vec::new(),
        stats: CorpusScanStats::default(),
        warnings: Vec::new(),
    };
    for event in corpus.select(RunLogSelection::for_skills(skills)) {
        match event {
            RunLogCorpusEvent::Warning(warning) => scan.warnings.push(warning),
            RunLogCorpusEvent::Run(run) => collect_run(&mut scan, &run, log_root, mode, filter),
        }
    }
    scan
}

fn collect_run(
    scan: &mut GroundTruthCorpusScan,
    run: &RunLogRun,
    log_root: &Path,
    mode: GroundTruthMode,
    filter: &CorpusFilter,
) {
    let run_dir = run.directory().to_path_buf();
    let gc_slimmed = run_dir.join("gc-slimmed").exists();
    let paths = run.classification_paths(RunLogRoundSort::Numeric);
    if mode == GroundTruthMode::Verdict {
        // A run with no classification artifact never reaches the verdict
        // minima, so it neither qualifies nor counts as excluded.
        if paths.is_empty() {
            return;
        }
        if gc_slimmed {
            scan.stats.excluded_gc_slimmed_runs += 1;
            scan.stats.gc_slimmed_runs += 1;
            return;
        }
        if !verdict_run_qualifies(run, filter, &mut scan.stats) {
            return;
        }
        scan.stats.qualifying_runs += 1;
    }
    scan.stats.files_seen += paths.len();
    if gc_slimmed {
        scan.stats.gc_slimmed_runs += 1;
        return;
    }
    let Some(run_dir_key) = run_dir_key(&run_dir, log_root) else {
        return;
    };
    let panel_kind = PanelKind::for_skill(run.layout().skill().as_str());
    let started_at = match mode {
        GroundTruthMode::Verdict => run.started_at(false, true),
        GroundTruthMode::Calibration => run.started_at(true, false),
    };
    let multi_round = run_round_dirs(run).len() > 1;
    // The walker reads `ended_at`, `completed_at`, then `updated_at` with the
    // same precedence Python uses. It also consults `run-manifest.json` when the
    // primary manifest holds an invalid timestamp, which is a strictly more
    // tolerant read than Python's manifest-only candidate list.
    let run_ended_at = run.ended_at(false);
    for path in paths {
        scan.sources.push(ClassificationSource {
            panel_kind,
            round_num: round_number_from_path(&path).unwrap_or(0),
            path,
            run_dir: run_dir.clone(),
            run_dir_key: run_dir_key.clone(),
            run_id: run.layout().run_id().as_str().to_owned(),
            started_at,
            run_ended_at,
            multi_round,
        });
    }
}

fn verdict_run_qualifies(
    run: &RunLogRun,
    filter: &CorpusFilter,
    stats: &mut CorpusScanStats,
) -> bool {
    if let Some(since_date) = filter.since_date {
        let Some(started_at) = run.started_at(false, true) else {
            stats.excluded_missing_started_at_runs += 1;
            return false;
        };
        if started_at < since_date {
            stats.excluded_pre_since_runs += 1;
            return false;
        }
    }
    if let Some(floor) = filter.min_larch_version.as_deref() {
        let Some(version) = run
            .larch_version(true)
            .filter(|value| version_components(value).is_some())
        else {
            stats.excluded_missing_version_runs += 1;
            return false;
        };
        if !version_meets_floor(&version, floor) {
            stats.excluded_below_version_runs += 1;
            return false;
        }
    }
    true
}

/// Return the `round-*` directory names that hold at least one run artifact.
///
/// Python counts round directories, not round-numbered filenames, so a
/// standalone review run whose classification files carry `-round-N` suffixes at
/// the run root is single-round. An empty round directory holds no analyzable
/// artifact and does not count here.
fn run_round_dirs(run: &RunLogRun) -> BTreeSet<String> {
    run.files()
        .filter_map(|path| {
            let name = path.parent()?.file_name()?.to_str()?.to_owned();
            name.starts_with("round-").then_some(name)
        })
        .collect()
}

/// Return the log-root-relative run directory key, or `None` when the run
/// directory does not lie under the log root.
#[must_use]
pub fn run_dir_key(run_dir: &Path, log_root: &Path) -> Option<String> {
    let relative = run_dir.strip_prefix(log_root).ok()?;
    let parts: Vec<String> = relative
        .components()
        .map(|component| component.as_os_str().to_string_lossy().into_owned())
        .collect();
    Some(parts.join("/"))
}

/// Parse a dotted version into comparable numeric components.
#[must_use]
pub fn version_components(version: &str) -> Option<Vec<u32>> {
    let trimmed = version.trim().trim_start_matches(['v', 'V']);
    if trimmed.is_empty() {
        return None;
    }
    let mut parts: Vec<u32> = Vec::new();
    for raw in trimmed.split('.') {
        let digits: String = raw.chars().take_while(char::is_ascii_digit).collect();
        if digits.is_empty() {
            return None;
        }
        parts.push(digits.parse::<u32>().ok()?);
    }
    while parts.len() < 3 {
        parts.push(0);
    }
    Some(parts)
}

/// Return whether `version` is at or above `floor`.
#[must_use]
pub fn version_meets_floor(version: &str, floor: &str) -> bool {
    match (version_components(version), version_components(floor)) {
        (Some(parsed), Some(parsed_floor)) => parsed >= parsed_floor,
        _ => false,
    }
}

/// Whether the calibration incentive era had shipped when the corpus was read.
///
/// The two failing states carry distinct reason tokens because Python reports
/// an unreachable incentive issue differently from one that has not shipped.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum IncentiveEra {
    /// The incentive change had shipped.
    Shipped,
    /// The incentive change had not shipped.
    NotShipped,
    /// The incentive issue could not be read, so shipping is unproved.
    CheckUnavailable,
}

/// Why the capstone verdict gate failed.
#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub enum GateFailure {
    /// The calibration incentive era had not shipped.
    CalibrationIncentiveNotShipped,
    /// The calibration incentive issue could not be read.
    CalibrationIncentiveCheckUnavailable,
    /// Both GitHub enrichment and targeted fetch were degraded.
    EnrichmentAndTargetedFetchDegraded,
    /// GitHub issue enrichment was degraded.
    EnrichmentDegraded,
    /// Targeted issue fetch was degraded.
    TargetedFetchDegraded,
    /// Fewer runs qualified than the corpus minimum requires.
    CorpusBelowMinRuns,
}

impl GateFailure {
    /// Return the exact Python gate reason token.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::CalibrationIncentiveNotShipped => "calibration_incentive_not_shipped",
            Self::CalibrationIncentiveCheckUnavailable => "calibration_incentive_check_unavailable",
            Self::EnrichmentAndTargetedFetchDegraded => {
                "enrichment_degraded,targeted_fetch_degraded"
            }
            Self::EnrichmentDegraded => "enrichment_degraded",
            Self::TargetedFetchDegraded => "targeted_fetch_degraded",
            Self::CorpusBelowMinRuns => "corpus_below_min_runs",
        }
    }
}

/// Degradation inputs the capstone verdict gate reads.
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub struct VerdictGateInputs {
    pub enrichment_degraded: bool,
    pub targeted_fetch_degraded: bool,
    pub qualifying_runs: usize,
    pub min_runs: usize,
}

/// Apply the capstone verdict gate, returning the first failing reason.
#[must_use]
pub fn apply_verdict_gate(
    incentive: IncentiveEra,
    inputs: VerdictGateInputs,
) -> Option<GateFailure> {
    match incentive {
        IncentiveEra::NotShipped => return Some(GateFailure::CalibrationIncentiveNotShipped),
        IncentiveEra::CheckUnavailable => {
            return Some(GateFailure::CalibrationIncentiveCheckUnavailable);
        }
        IncentiveEra::Shipped => {}
    }
    match (inputs.enrichment_degraded, inputs.targeted_fetch_degraded) {
        (true, true) => return Some(GateFailure::EnrichmentAndTargetedFetchDegraded),
        (true, false) => return Some(GateFailure::EnrichmentDegraded),
        (false, true) => return Some(GateFailure::TargetedFetchDegraded),
        (false, false) => {}
    }
    (inputs.qualifying_runs < inputs.min_runs).then_some(GateFailure::CorpusBelowMinRuns)
}
