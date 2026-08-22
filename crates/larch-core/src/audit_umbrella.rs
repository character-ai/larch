//! Durable data contracts for `/audit-umbrella`.
//!
//! The audit judgment stays in the public skill, but its inputs and outputs
//! cross a trust boundary.  This module owns the bounded JSON shapes that make
//! a later mutation prove it is acting on the exact repository snapshot,
//! requirement ledger, and corrective batch the audit produced.

use crate::{OrderedJson, bounded_ascii_identifier, issue::umbrella_leaf_opening_text};
use chrono::DateTime;
use serde::{Deserialize, Serialize};
use sha2::{Digest as _, Sha256};
use std::collections::{BTreeMap, BTreeSet};

/// Current JSON version for an immutable audit snapshot.
pub const AUDIT_SNAPSHOT_VERSION: u8 = 1;
/// Current JSON version for a requirements ledger.
pub const AUDIT_LEDGER_VERSION: u8 = 1;
/// Current JSON version for a persisted corrective proposal.
pub const AUDIT_PROPOSAL_VERSION: u8 = 1;
/// The largest complete issue/source snapshot the audit will accept.
pub const MAX_AUDIT_SOURCES: usize = 128;
/// The largest number of direct leaves the public umbrella convention admits.
pub const MAX_AUDIT_LEAVES: usize = 30;
/// Bound model-authored ledger rows before they reach a durable file.
pub const MAX_AUDIT_REQUIREMENTS: usize = 20_000;
/// Bound one model-authored issue body before a public mutation.
pub const MAX_AUDIT_LEAF_BODY_BYTES: usize = 64 * 1024;
/// Bound one public audit leaf title.
pub const MAX_AUDIT_LEAF_TITLE_BYTES: usize = 160;
/// Bound every persisted audit artifact to the command's confined read limit.
pub const MAX_AUDIT_ARTIFACT_BYTES: usize = 4 * 1024 * 1024;

/// One stable, non-user-facing refusal token from an audit data contract.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct AuditUmbrellaRefusal(&'static str);

impl AuditUmbrellaRefusal {
    /// Return the stable refusal token.
    #[must_use]
    pub const fn reason(self) -> &'static str {
        self.0
    }
}

/// Snapshot JSON did not have the exact bounded shape required by the audit.
pub const INVALID_AUDIT_SNAPSHOT: AuditUmbrellaRefusal =
    AuditUmbrellaRefusal("invalid-audit-snapshot");
/// Ledger JSON did not cover every immutable source item or was malformed.
pub const INVALID_AUDIT_LEDGER: AuditUmbrellaRefusal = AuditUmbrellaRefusal("invalid-audit-ledger");
/// A proposal draft did not form a complete, acyclic corrective batch.
pub const INVALID_AUDIT_PROPOSAL: AuditUmbrellaRefusal =
    AuditUmbrellaRefusal("invalid-audit-proposal");
/// A persisted proposal no longer binds the snapshot or ledger supplied to it.
pub const STALE_AUDIT_PROPOSAL: AuditUmbrellaRefusal = AuditUmbrellaRefusal("stale-audit-proposal");
/// The bounded immutable fields one GitHub issue contributes to an audit.
#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct AuditIssue {
    pub number: u64,
    pub id: u64,
    pub title: String,
    pub body: String,
    pub state: String,
    pub updated_at: String,
    pub url: String,
}

/// One issue that the audit must read, together with why it was selected.
#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct AuditSource {
    pub id: String,
    pub roles: Vec<String>,
    pub issue: AuditIssue,
}

/// The immutable GitHub and repository evidence available to one audit.
#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct AuditSnapshot {
    pub version: u8,
    pub repository: String,
    pub default_branch: String,
    pub audited_sha: String,
    pub umbrella: AuditIssue,
    pub sources: Vec<AuditSource>,
    pub historical_leaf_numbers: Vec<u64>,
}

/// A line-level immutable source item which a ledger must account for.
#[derive(Clone, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub struct AuditSourceItem {
    pub id: String,
    pub digest: String,
}

/// One final classification of a normative source item.
#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum RequirementStatus {
    Satisfied,
    Gap,
    NotApplicable,
    Blocked,
}

/// One requirement and its code/test evidence.
#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct AuditLedgerEntry {
    pub id: String,
    pub source_id: String,
    pub requirement: String,
    pub status: RequirementStatus,
    #[serde(default)]
    pub code_evidence: Vec<String>,
    #[serde(default)]
    pub test_evidence: Vec<String>,
    #[serde(default)]
    pub reason: String,
}

/// The model-authored but mechanically checked requirements ledger.
#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct AuditLedger {
    pub version: u8,
    pub snapshot_sha256: String,
    pub entries: Vec<AuditLedgerEntry>,
}

/// Resolved counts from one valid ledger.
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub struct AuditLedgerSummary {
    pub total: usize,
    pub satisfied: usize,
    pub gaps: usize,
    pub not_applicable: usize,
    pub blocked: usize,
}

/// The first constraint a ledger violated, named for a diagnostic surface.
///
/// This is the diagnostic granularity behind [`validate_audit_ledger`]'s stable
/// [`AuditUmbrellaRefusal`]. Each variant maps back to exactly one refusal token
/// through [`AuditLedgerViolation::refusal`], so the accept/reject outcome and
/// exit contract stay unchanged while the failure is now nameable.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum AuditLedgerViolation {
    /// The immutable snapshot itself failed its bounded contract.
    Snapshot,
    /// The ledger `version` did not match [`AUDIT_LEDGER_VERSION`].
    Version,
    /// The ledger `snapshot_sha256` did not bind the supplied snapshot.
    SnapshotBinding,
    /// The ledger carried no entries.
    EmptyEntries,
    /// The ledger carried more than [`MAX_AUDIT_REQUIREMENTS`] entries.
    TooManyEntries,
    /// One entry `id` was not a bounded ASCII identifier.
    MalformedEntryId { id: String },
    /// One entry `id` repeated an earlier entry `id`.
    DuplicateEntryId { id: String },
    /// One entry `requirement` was not a single trimmed line.
    RequirementLine { id: String },
    /// One entry `code_evidence` array had a malformed line.
    CodeEvidence { id: String },
    /// One entry `test_evidence` array had a malformed line.
    TestEvidence { id: String },
    /// One entry `reason` was too long or contained a carriage return.
    ReasonShape { id: String },
    /// A `satisfied` entry lacked required evidence or carried a reason.
    SatisfiedEvidence { id: String },
    /// A `gap` entry carried no code or test evidence.
    GapEvidence { id: String },
    /// A `not_applicable` entry had evidence or lacked a reason.
    NotApplicableShape { id: String },
    /// A `blocked` entry had evidence or lacked a reason.
    BlockedShape { id: String },
    /// The ledger left source items uncovered or referenced unknown source ids.
    Coverage { uncovered: usize, unknown: usize },
}

impl AuditLedgerViolation {
    /// Return the stable kebab-case constraint name for this violation.
    #[must_use]
    pub const fn constraint(&self) -> &'static str {
        match self {
            Self::Snapshot => "snapshot",
            Self::Version => "version",
            Self::SnapshotBinding => "snapshot-binding",
            Self::EmptyEntries => "empty-entries",
            Self::TooManyEntries => "too-many-entries",
            Self::MalformedEntryId { .. } => "malformed-entry-id",
            Self::DuplicateEntryId { .. } => "duplicate-entry-id",
            Self::RequirementLine { .. } => "requirement-line",
            Self::CodeEvidence { .. } => "code-evidence",
            Self::TestEvidence { .. } => "test-evidence",
            Self::ReasonShape { .. } => "reason-shape",
            Self::SatisfiedEvidence { .. } => "satisfied-evidence",
            Self::GapEvidence { .. } => "gap-evidence",
            Self::NotApplicableShape { .. } => "not-applicable-shape",
            Self::BlockedShape { .. } => "blocked-shape",
            Self::Coverage { .. } => "coverage",
        }
    }

    /// Return the offending entry id when the violation is scoped to one entry.
    #[must_use]
    pub const fn entry_id(&self) -> Option<&str> {
        match self {
            Self::MalformedEntryId { id }
            | Self::DuplicateEntryId { id }
            | Self::RequirementLine { id }
            | Self::CodeEvidence { id }
            | Self::TestEvidence { id }
            | Self::ReasonShape { id }
            | Self::SatisfiedEvidence { id }
            | Self::GapEvidence { id }
            | Self::NotApplicableShape { id }
            | Self::BlockedShape { id } => Some(id.as_str()),
            Self::Snapshot
            | Self::Version
            | Self::SnapshotBinding
            | Self::EmptyEntries
            | Self::TooManyEntries
            | Self::Coverage { .. } => None,
        }
    }

    /// Map this violation to the stable refusal token that owns the exit contract.
    #[must_use]
    pub const fn refusal(&self) -> AuditUmbrellaRefusal {
        match self {
            Self::Snapshot => INVALID_AUDIT_SNAPSHOT,
            _ => INVALID_AUDIT_LEDGER,
        }
    }
}

/// The first constraint a proposal draft violated, named for a diagnostic surface.
///
/// This is the diagnostic granularity behind [`build_audit_proposal`]'s stable
/// [`AuditUmbrellaRefusal`]. Leaf-scoped variants retain a one-based draft index
/// and the bounded title supplied by the draft. Gap-scoped variants also retain
/// the exact offending ledger entry id.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum AuditProposalViolation {
    /// The immutable snapshot itself failed its bounded contract.
    Snapshot,
    /// The supplied ledger failed its own validation contract.
    Ledger { violation: AuditLedgerViolation },
    /// At least one ledger entry was still blocked.
    BlockedLedger,
    /// The draft `version` did not match [`AUDIT_PROPOSAL_VERSION`].
    Version,
    /// A draft supplied leaves even though the ledger had no gaps.
    UnexpectedLeaves,
    /// A gap ledger supplied no corrective leaves.
    MissingLeaves { gap_id: String },
    /// The draft carried more than [`MAX_AUDIT_LEAVES`] leaves.
    TooManyLeaves,
    /// Historical and proposed leaves exceeded [`MAX_AUDIT_LEAVES`] together.
    LeafCapacity,
    /// One leaf title did not start with the exact umbrella prefix.
    LeafTitlePrefix { leaf: usize, title: String },
    /// One leaf title was empty, multiline, untrimmed, or oversized.
    LeafTitleShape { leaf: usize, title: String },
    /// One leaf body was empty, malformed, or oversized.
    LeafBodyShape { leaf: usize, title: String },
    /// One leaf body did not start with the exact umbrella opening sentence.
    LeafOpening { leaf: usize, title: String },
    /// One leaf body contained a protected `larch:plan` marker.
    LeafPlanMarker { leaf: usize, title: String },
    /// One required leaf section was missing or empty.
    LeafSection {
        leaf: usize,
        title: String,
        section: &'static str,
    },
    /// One `## Scope` section had no numbered `1. ` item.
    LeafNumberedScope { leaf: usize, title: String },
    /// One leaf carried no ledger entry ids in `gap_ids`.
    LeafGapIdsEmpty { leaf: usize, title: String },
    /// One leaf carried more than [`MAX_AUDIT_REQUIREMENTS`] gap ids.
    LeafGapIdsTooMany { leaf: usize, title: String },
    /// One `gap_id` was not a bounded ASCII ledger entry id.
    LeafGapIdMalformed {
        leaf: usize,
        title: String,
        gap_id: String,
    },
    /// One leaf's `gap_ids` were not sorted and unique.
    LeafGapIdsOrder { leaf: usize, title: String },
    /// One leaf body did not cite the audited commit SHA.
    LeafAuditedSha { leaf: usize, title: String },
    /// One leaf repeated an earlier leaf's exact title/body identity.
    DuplicateLeaf { leaf: usize, title: String },
    /// One `gap_id` was not a gap ledger entry id.
    UnknownGapId {
        leaf: usize,
        title: String,
        gap_id: String,
    },
    /// One `gap_id` was already owned by an earlier leaf.
    DuplicateGapId {
        leaf: usize,
        title: String,
        gap_id: String,
    },
    /// One gap ledger entry was not owned by any leaf.
    UncoveredGapId { gap_id: String },
    /// One dependency endpoint was invalid or unbound.
    DependencyNode { dependency: usize, removal: bool },
    /// One dependency used the same node at both endpoints.
    DependencySelf { dependency: usize, removal: bool },
    /// One dependency repeated an earlier edge in the same list.
    DependencyDuplicate { dependency: usize, removal: bool },
    /// One removal also appeared in the dependency-addition list.
    DependencyConflict { dependency: usize },
    /// The proposed dependency additions contained a cycle.
    DependencyCycle,
    /// The assembled durable proposal failed an internal consistency check.
    ProposalShape,
}

impl AuditProposalViolation {
    /// Return the stable kebab-case constraint name for this violation.
    #[must_use]
    pub const fn constraint(&self) -> &'static str {
        match self {
            Self::Snapshot => "snapshot",
            Self::Ledger { .. } => "ledger",
            Self::BlockedLedger => "blocked-ledger",
            Self::Version => "version",
            Self::UnexpectedLeaves => "unexpected-leaves",
            Self::MissingLeaves { .. } => "missing-leaves",
            Self::TooManyLeaves => "too-many-leaves",
            Self::LeafCapacity => "leaf-capacity",
            Self::LeafTitlePrefix { .. } => "leaf-title-prefix",
            Self::LeafTitleShape { .. } => "leaf-title-shape",
            Self::LeafBodyShape { .. } => "leaf-body-shape",
            Self::LeafOpening { .. } => "leaf-opening",
            Self::LeafPlanMarker { .. } => "leaf-plan-marker",
            Self::LeafSection { .. } => "leaf-section",
            Self::LeafNumberedScope { .. } => "leaf-numbered-scope",
            Self::LeafGapIdsEmpty { .. } => "leaf-gap-ids-empty",
            Self::LeafGapIdsTooMany { .. } => "leaf-gap-ids-too-many",
            Self::LeafGapIdMalformed { .. } => "leaf-gap-id-malformed",
            Self::LeafGapIdsOrder { .. } => "leaf-gap-ids-order",
            Self::LeafAuditedSha { .. } => "leaf-audited-sha",
            Self::DuplicateLeaf { .. } => "duplicate-leaf",
            Self::UnknownGapId { .. } => "unknown-gap-id",
            Self::DuplicateGapId { .. } => "duplicate-gap-id",
            Self::UncoveredGapId { .. } => "uncovered-gap-id",
            Self::DependencyNode { .. } => "dependency-node",
            Self::DependencySelf { .. } => "dependency-self",
            Self::DependencyDuplicate { .. } => "dependency-duplicate",
            Self::DependencyConflict { .. } => "dependency-conflict",
            Self::DependencyCycle => "dependency-cycle",
            Self::ProposalShape => "proposal-shape",
        }
    }

    /// Return the one-based draft leaf index for a leaf-scoped violation.
    #[must_use]
    pub const fn leaf_index(&self) -> Option<usize> {
        match self {
            Self::LeafTitlePrefix { leaf, .. }
            | Self::LeafTitleShape { leaf, .. }
            | Self::LeafBodyShape { leaf, .. }
            | Self::LeafOpening { leaf, .. }
            | Self::LeafPlanMarker { leaf, .. }
            | Self::LeafSection { leaf, .. }
            | Self::LeafNumberedScope { leaf, .. }
            | Self::LeafGapIdsEmpty { leaf, .. }
            | Self::LeafGapIdsTooMany { leaf, .. }
            | Self::LeafGapIdMalformed { leaf, .. }
            | Self::LeafGapIdsOrder { leaf, .. }
            | Self::LeafAuditedSha { leaf, .. }
            | Self::DuplicateLeaf { leaf, .. }
            | Self::UnknownGapId { leaf, .. }
            | Self::DuplicateGapId { leaf, .. } => Some(*leaf),
            _ => None,
        }
    }

    /// Return the draft title for a leaf-scoped violation.
    #[must_use]
    pub const fn leaf_title(&self) -> Option<&str> {
        match self {
            Self::LeafTitlePrefix { title, .. }
            | Self::LeafTitleShape { title, .. }
            | Self::LeafBodyShape { title, .. }
            | Self::LeafOpening { title, .. }
            | Self::LeafPlanMarker { title, .. }
            | Self::LeafSection { title, .. }
            | Self::LeafNumberedScope { title, .. }
            | Self::LeafGapIdsEmpty { title, .. }
            | Self::LeafGapIdsTooMany { title, .. }
            | Self::LeafGapIdMalformed { title, .. }
            | Self::LeafGapIdsOrder { title, .. }
            | Self::LeafAuditedSha { title, .. }
            | Self::DuplicateLeaf { title, .. }
            | Self::UnknownGapId { title, .. }
            | Self::DuplicateGapId { title, .. } => Some(title.as_str()),
            _ => None,
        }
    }

    /// Return the offending ledger entry id for a gap-scoped violation.
    #[must_use]
    pub const fn gap_id(&self) -> Option<&str> {
        match self {
            Self::MissingLeaves { gap_id }
            | Self::LeafGapIdMalformed { gap_id, .. }
            | Self::UnknownGapId { gap_id, .. }
            | Self::DuplicateGapId { gap_id, .. }
            | Self::UncoveredGapId { gap_id } => Some(gap_id.as_str()),
            _ => None,
        }
    }

    /// Return the missing or empty section heading when applicable.
    #[must_use]
    pub const fn section(&self) -> Option<&'static str> {
        match self {
            Self::LeafSection { section, .. } => Some(section),
            _ => None,
        }
    }

    /// Return the one-based dependency index and whether it is a removal.
    #[must_use]
    pub const fn dependency(&self) -> Option<(usize, bool)> {
        match self {
            Self::DependencyNode {
                dependency,
                removal,
            }
            | Self::DependencySelf {
                dependency,
                removal,
            }
            | Self::DependencyDuplicate {
                dependency,
                removal,
            } => Some((*dependency, *removal)),
            Self::DependencyConflict { dependency } => Some((*dependency, true)),
            _ => None,
        }
    }

    /// Map this violation to the stable refusal token that owns the exit contract.
    #[must_use]
    pub const fn refusal(&self) -> AuditUmbrellaRefusal {
        match self {
            Self::Snapshot => INVALID_AUDIT_SNAPSHOT,
            Self::Ledger { violation } => violation.refusal(),
            _ => INVALID_AUDIT_PROPOSAL,
        }
    }
}

/// A node in a proposed native blocked-by edge.
#[derive(Clone, Debug, Eq, Ord, PartialEq, PartialOrd, Serialize, Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case")]
pub enum AuditDependencyNode {
    Existing { number: u64 },
    New { identity: String },
}

/// One native `dependent <- prerequisite` relation to add or remove.
#[derive(Clone, Debug, Eq, Ord, PartialEq, PartialOrd, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct AuditDependency {
    pub dependent: AuditDependencyNode,
    pub prerequisite: AuditDependencyNode,
}

/// One proposed public leaf before it has a GitHub identity.
#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct AuditLeafDraft {
    pub title: String,
    pub body: String,
    pub gap_ids: Vec<String>,
}

/// The exact corrective batch authored after an audit completes.
#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct AuditProposalDraft {
    pub version: u8,
    pub leaves: Vec<AuditLeafDraft>,
    #[serde(default)]
    pub dependencies: Vec<AuditDependency>,
    #[serde(default)]
    pub remove_dependencies: Vec<AuditDependency>,
}

/// Lifecycle state of one audit-created issue.
#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum AuditLeafState {
    Pending,
    InFlight,
    Resolved,
}

/// Durable progress state for the idempotent relationship reconciliation.
#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum AuditGraphState {
    /// No native sub-issue or blocked-by relation has been attempted.
    Pending,
    /// Relationship reconciliation may have partially reached GitHub and must
    /// resume through exact read-back and idempotent typed mutations.
    InFlight,
    /// Final read-back proved the persisted relationship batch.
    Verified,
}

/// One persisted audit-created leaf with its exact remote identity when known.
#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct AuditLeaf {
    pub identity: String,
    pub title: String,
    pub body: String,
    pub gap_ids: Vec<String>,
    pub state: AuditLeafState,
    pub number: u64,
    pub issue_id: u64,
    pub url: String,
}

/// A compare-and-swap fingerprint for an issue that may affect the mutation.
#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct AuditIssueFingerprint {
    pub number: u64,
    pub id: u64,
    pub updated_at: String,
    pub title_sha256: String,
    pub body_sha256: String,
}

/// The durable, resumable public mutation record.
#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct AuditProposal {
    pub version: u8,
    pub repository: String,
    pub umbrella: u64,
    pub audited_sha: String,
    pub snapshot_sha256: String,
    pub ledger_sha256: String,
    pub historical_leaf_numbers: Vec<u64>,
    /// Every historical leaf that must be a direct native child at final
    /// read-back. The snapshot admits this set only from an exact leaf
    /// discovery role, never from a generic referenced issue.
    pub direct_leaf_numbers: Vec<u64>,
    pub expected_issues: Vec<AuditIssueFingerprint>,
    pub leaves: Vec<AuditLeaf>,
    pub dependencies: Vec<AuditDependency>,
    pub remove_dependencies: Vec<AuditDependency>,
    pub graph_state: AuditGraphState,
    pub complete: bool,
}

/// Return one exact leaf title prefix for an audited umbrella.
#[must_use]
pub fn audit_leaf_prefix(umbrella: u64) -> String {
    format!("[LEAF OF {umbrella}] ")
}

/// Render a snapshot deterministically for a private session artifact.
///
/// # Errors
///
/// Returns [`INVALID_AUDIT_SNAPSHOT`] when the snapshot violates its bounded
/// contract or cannot be serialized.
pub fn render_audit_snapshot(snapshot: &AuditSnapshot) -> Result<String, AuditUmbrellaRefusal> {
    validate_snapshot(snapshot)?;
    render_artifact(snapshot, INVALID_AUDIT_SNAPSHOT)
}

/// Parse and validate one snapshot, rejecting duplicate JSON keys before decode.
///
/// # Errors
///
/// Returns [`INVALID_AUDIT_SNAPSHOT`] for malformed, duplicate-keyed, or
/// contract-invalid JSON.
pub fn parse_audit_snapshot(text: &str) -> Result<AuditSnapshot, AuditUmbrellaRefusal> {
    if text.len() > MAX_AUDIT_ARTIFACT_BYTES {
        return Err(INVALID_AUDIT_SNAPSHOT);
    }
    parse_unique(text, INVALID_AUDIT_SNAPSHOT)
        .and_then(|()| serde_json::from_str(text).map_err(|_error| INVALID_AUDIT_SNAPSHOT))
        .and_then(|snapshot| {
            validate_snapshot(&snapshot)?;
            Ok(snapshot)
        })
}

/// Return the SHA-256 binding for exact serialized snapshot bytes.
#[must_use]
pub fn audit_snapshot_sha256(snapshot: &AuditSnapshot) -> String {
    render_audit_snapshot(snapshot).map_or_else(|_error| String::new(), |text| sha256(&text))
}

/// Enumerate every non-empty issue title/body line that a ledger must resolve.
#[must_use]
pub fn audit_source_items(snapshot: &AuditSnapshot) -> Vec<AuditSourceItem> {
    let mut items = Vec::new();
    let mut source_rows = snapshot.sources.clone();
    source_rows.sort_by(|left, right| left.id.cmp(&right.id));
    for source in source_rows {
        if !source.issue.title.trim().is_empty() {
            items.push(AuditSourceItem {
                id: format!("{}:title", source.id),
                digest: sha256(&source.issue.title),
            });
        }
        for (index, line) in source.issue.body.lines().enumerate() {
            if !line.trim().is_empty() {
                items.push(AuditSourceItem {
                    id: format!("{}:body:{}", source.id, index + 1),
                    digest: sha256(line),
                });
            }
        }
    }
    items
}

/// Render one valid ledger as deterministic private JSON.
///
/// # Errors
///
/// Returns [`INVALID_AUDIT_LEDGER`] if serialization cannot produce the
/// durable artifact.
pub fn render_audit_ledger(ledger: &AuditLedger) -> Result<String, AuditUmbrellaRefusal> {
    render_artifact(ledger, INVALID_AUDIT_LEDGER)
}

/// Parse one ledger without asserting that it belongs to a particular snapshot.
///
/// # Errors
///
/// Returns [`INVALID_AUDIT_LEDGER`] for malformed or duplicate-keyed JSON.
pub fn parse_audit_ledger(text: &str) -> Result<AuditLedger, AuditUmbrellaRefusal> {
    if text.len() > MAX_AUDIT_ARTIFACT_BYTES {
        return Err(INVALID_AUDIT_LEDGER);
    }
    parse_unique(text, INVALID_AUDIT_LEDGER)
        .and_then(|()| serde_json::from_str(text).map_err(|_error| INVALID_AUDIT_LEDGER))
}

/// Validate full coverage and evidence of one ledger against an immutable snapshot.
///
/// This is the thin, refusal-typed wrapper over [`diagnose_audit_ledger`]. It
/// preserves the exact [`AuditUmbrellaRefusal`] contract every caller relies on;
/// use [`diagnose_audit_ledger`] directly when the named constraint is wanted.
///
/// # Errors
///
/// Returns [`INVALID_AUDIT_SNAPSHOT`] or [`INVALID_AUDIT_LEDGER`] when the
/// immutable source or ledger is invalid.
pub fn validate_audit_ledger(
    snapshot: &AuditSnapshot,
    ledger: &AuditLedger,
) -> Result<AuditLedgerSummary, AuditUmbrellaRefusal> {
    diagnose_audit_ledger(snapshot, ledger).map_err(|violation| violation.refusal())
}

/// Validate one ledger, naming the first violated constraint on failure.
///
/// The single validation authority for `/audit-umbrella`. Accept/reject outcome
/// and the refusal token surfaced by [`validate_audit_ledger`] are unchanged;
/// this variant additionally names the failing constraint, the offending entry
/// id, and the uncovered/unknown coverage counts.
///
/// # Errors
///
/// Returns the [`AuditLedgerViolation`] for the first constraint the immutable
/// source or ledger failed.
pub fn diagnose_audit_ledger(
    snapshot: &AuditSnapshot,
    ledger: &AuditLedger,
) -> Result<AuditLedgerSummary, AuditLedgerViolation> {
    validate_snapshot(snapshot).map_err(|_error| AuditLedgerViolation::Snapshot)?;
    if ledger.version != AUDIT_LEDGER_VERSION {
        return Err(AuditLedgerViolation::Version);
    }
    if ledger.snapshot_sha256 != audit_snapshot_sha256(snapshot) {
        return Err(AuditLedgerViolation::SnapshotBinding);
    }
    if ledger.entries.is_empty() {
        return Err(AuditLedgerViolation::EmptyEntries);
    }
    if ledger.entries.len() > MAX_AUDIT_REQUIREMENTS {
        return Err(AuditLedgerViolation::TooManyEntries);
    }
    let source_items = audit_source_items(snapshot);
    let expected_source_ids = source_items
        .iter()
        .map(|item| item.id.as_str())
        .collect::<BTreeSet<_>>();
    let mut entry_ids = BTreeSet::new();
    let mut covered = BTreeSet::new();
    let mut unknown = BTreeSet::new();
    let mut summary = AuditLedgerSummary::default();
    for entry in &ledger.entries {
        check_entry_shape(entry, &mut entry_ids)?;
        if expected_source_ids.contains(entry.source_id.as_str()) {
            let _ = covered.insert(entry.source_id.as_str());
        } else {
            let _ = unknown.insert(entry.source_id.as_str());
        }
        match check_entry_status(entry)? {
            RequirementStatus::Satisfied => summary.satisfied += 1,
            RequirementStatus::Gap => summary.gaps += 1,
            RequirementStatus::NotApplicable => summary.not_applicable += 1,
            RequirementStatus::Blocked => summary.blocked += 1,
        }
    }
    let uncovered = expected_source_ids.len() - covered.len();
    if uncovered != 0 || !unknown.is_empty() {
        return Err(AuditLedgerViolation::Coverage {
            uncovered,
            unknown: unknown.len(),
        });
    }
    summary.total = ledger.entries.len();
    Ok(summary)
}

/// Check one entry's identifier, single-line, and evidence shape.
fn check_entry_shape<'entry>(
    entry: &'entry AuditLedgerEntry,
    entry_ids: &mut BTreeSet<&'entry str>,
) -> Result<(), AuditLedgerViolation> {
    if !bounded_ascii_identifier(&entry.id, true) {
        return Err(AuditLedgerViolation::MalformedEntryId {
            id: entry.id.clone(),
        });
    }
    if !entry_ids.insert(entry.id.as_str()) {
        return Err(AuditLedgerViolation::DuplicateEntryId {
            id: entry.id.clone(),
        });
    }
    if !valid_single_line(&entry.requirement, 8 * 1024) {
        return Err(AuditLedgerViolation::RequirementLine {
            id: entry.id.clone(),
        });
    }
    if !evidence_valid(&entry.code_evidence) {
        return Err(AuditLedgerViolation::CodeEvidence {
            id: entry.id.clone(),
        });
    }
    if !evidence_valid(&entry.test_evidence) {
        return Err(AuditLedgerViolation::TestEvidence {
            id: entry.id.clone(),
        });
    }
    if entry.reason.len() > 8 * 1024 || entry.reason.contains('\r') {
        return Err(AuditLedgerViolation::ReasonShape {
            id: entry.id.clone(),
        });
    }
    Ok(())
}

/// Check one entry's per-status evidence and reason rules.
fn check_entry_status(entry: &AuditLedgerEntry) -> Result<RequirementStatus, AuditLedgerViolation> {
    match entry.status {
        RequirementStatus::Satisfied => {
            if entry.code_evidence.is_empty()
                || entry.test_evidence.is_empty()
                || !entry.reason.is_empty()
            {
                return Err(AuditLedgerViolation::SatisfiedEvidence {
                    id: entry.id.clone(),
                });
            }
        }
        RequirementStatus::Gap => {
            if entry.code_evidence.is_empty() && entry.test_evidence.is_empty() {
                return Err(AuditLedgerViolation::GapEvidence {
                    id: entry.id.clone(),
                });
            }
        }
        RequirementStatus::NotApplicable => {
            if !entry.code_evidence.is_empty()
                || !entry.test_evidence.is_empty()
                || !valid_text(&entry.reason, 8 * 1024)
            {
                return Err(AuditLedgerViolation::NotApplicableShape {
                    id: entry.id.clone(),
                });
            }
        }
        RequirementStatus::Blocked => {
            if !entry.code_evidence.is_empty()
                || !entry.test_evidence.is_empty()
                || !valid_text(&entry.reason, 8 * 1024)
            {
                return Err(AuditLedgerViolation::BlockedShape {
                    id: entry.id.clone(),
                });
            }
        }
    }
    Ok(entry.status)
}

/// Return the SHA-256 binding for exact serialized ledger bytes.
#[must_use]
pub fn audit_ledger_sha256(ledger: &AuditLedger) -> String {
    render_audit_ledger(ledger).map_or_else(|_error| String::new(), |text| sha256(&text))
}

/// Build the durable proposal after validating its draft against a complete ledger.
///
/// # Errors
///
/// Returns an audit refusal when the source, ledger, draft, or proposed graph
/// does not satisfy the closed batch contract.
pub fn build_audit_proposal(
    snapshot: &AuditSnapshot,
    ledger: &AuditLedger,
    draft: &AuditProposalDraft,
) -> Result<AuditProposal, AuditUmbrellaRefusal> {
    diagnose_audit_proposal(snapshot, ledger, draft).map_err(|violation| violation.refusal())
}

/// Build a durable proposal while naming the first violated draft constraint.
///
/// The single proposal-draft validation authority for `/audit-umbrella`.
/// Accept/reject outcomes and refusal tokens surfaced by
/// [`build_audit_proposal`] remain unchanged. This variant additionally names
/// the leaf, field, gap id, or dependency that caused the rejection.
///
/// # Errors
///
/// Returns the [`AuditProposalViolation`] for the first constraint the source,
/// ledger, draft, or proposed graph failed.
pub fn diagnose_audit_proposal(
    snapshot: &AuditSnapshot,
    ledger: &AuditLedger,
    draft: &AuditProposalDraft,
) -> Result<AuditProposal, AuditProposalViolation> {
    let summary = diagnose_audit_ledger(snapshot, ledger).map_err(|violation| match violation {
        AuditLedgerViolation::Snapshot => AuditProposalViolation::Snapshot,
        violation => AuditProposalViolation::Ledger { violation },
    })?;
    if summary.blocked != 0 {
        return Err(AuditProposalViolation::BlockedLedger);
    }
    if draft.version != AUDIT_PROPOSAL_VERSION {
        return Err(AuditProposalViolation::Version);
    }
    let gap_ids = ledger
        .entries
        .iter()
        .filter(|entry| entry.status == RequirementStatus::Gap)
        .map(|entry| entry.id.as_str())
        .collect::<BTreeSet<_>>();
    let leaves = diagnose_proposal_leaves(snapshot, draft, &gap_ids)?;
    let mut historical_leaf_numbers = snapshot.historical_leaf_numbers.clone();
    historical_leaf_numbers.sort_unstable();
    historical_leaf_numbers.dedup();
    let expected_issues =
        snapshot_issue_fingerprints(snapshot).map_err(|_error| AuditProposalViolation::Snapshot)?;
    let expected_numbers = expected_issues
        .iter()
        .map(|issue| issue.number)
        .collect::<BTreeSet<_>>();
    let known_new = leaves
        .iter()
        .map(|leaf| leaf.identity.as_str())
        .collect::<BTreeSet<_>>();
    diagnose_draft_dependencies(
        &draft.dependencies,
        &draft.remove_dependencies,
        &expected_numbers,
        &known_new,
    )?;
    let proposal = AuditProposal {
        version: AUDIT_PROPOSAL_VERSION,
        repository: snapshot.repository.clone(),
        umbrella: snapshot.umbrella.number,
        audited_sha: snapshot.audited_sha.clone(),
        snapshot_sha256: audit_snapshot_sha256(snapshot),
        ledger_sha256: audit_ledger_sha256(ledger),
        historical_leaf_numbers,
        direct_leaf_numbers: snapshot_direct_leaf_numbers(snapshot),
        expected_issues,
        leaves,
        dependencies: draft.dependencies.clone(),
        remove_dependencies: draft.remove_dependencies.clone(),
        graph_state: AuditGraphState::Pending,
        complete: false,
    };
    validate_audit_proposal(&proposal, Some(&gap_ids))
        .map_err(|_error| AuditProposalViolation::ProposalShape)?;
    Ok(proposal)
}

fn diagnose_proposal_leaves(
    snapshot: &AuditSnapshot,
    draft: &AuditProposalDraft,
    gap_ids: &BTreeSet<&str>,
) -> Result<Vec<AuditLeaf>, AuditProposalViolation> {
    if gap_ids.is_empty() && !draft.leaves.is_empty() {
        return Err(AuditProposalViolation::UnexpectedLeaves);
    }
    if draft.leaves.is_empty()
        && let Some(gap_id) = gap_ids.first()
    {
        return Err(AuditProposalViolation::MissingLeaves {
            gap_id: (*gap_id).to_owned(),
        });
    }
    if draft.leaves.len() > MAX_AUDIT_LEAVES {
        return Err(AuditProposalViolation::TooManyLeaves);
    }
    if snapshot_direct_leaf_numbers(snapshot)
        .len()
        .saturating_add(draft.leaves.len())
        > MAX_AUDIT_LEAVES
    {
        return Err(AuditProposalViolation::LeafCapacity);
    }
    let mut leaves = Vec::with_capacity(draft.leaves.len());
    let mut observed_gap_ids = BTreeSet::new();
    let mut identities = BTreeSet::new();
    for (index, leaf) in draft.leaves.iter().enumerate() {
        let leaf_index = index + 1;
        diagnose_leaf_draft(leaf, snapshot.umbrella.number, leaf_index)?;
        if !leaf.body.contains(&snapshot.audited_sha) {
            return Err(AuditProposalViolation::LeafAuditedSha {
                leaf: leaf_index,
                title: leaf.title.clone(),
            });
        }
        let identity = audit_leaf_identity(&leaf.title, &leaf.body);
        if !identities.insert(identity.clone()) {
            return Err(AuditProposalViolation::DuplicateLeaf {
                leaf: leaf_index,
                title: leaf.title.clone(),
            });
        }
        for gap_id in &leaf.gap_ids {
            if !gap_ids.contains(gap_id.as_str()) {
                return Err(AuditProposalViolation::UnknownGapId {
                    leaf: leaf_index,
                    title: leaf.title.clone(),
                    gap_id: gap_id.clone(),
                });
            }
            if !observed_gap_ids.insert(gap_id.as_str()) {
                return Err(AuditProposalViolation::DuplicateGapId {
                    leaf: leaf_index,
                    title: leaf.title.clone(),
                    gap_id: gap_id.clone(),
                });
            }
        }
        leaves.push(AuditLeaf {
            identity,
            title: leaf.title.clone(),
            body: leaf.body.clone(),
            gap_ids: leaf.gap_ids.clone(),
            state: AuditLeafState::Pending,
            number: 0,
            issue_id: 0,
            url: String::new(),
        });
    }
    if let Some(gap_id) = gap_ids.difference(&observed_gap_ids).next() {
        return Err(AuditProposalViolation::UncoveredGapId {
            gap_id: (**gap_id).to_owned(),
        });
    }
    Ok(leaves)
}

/// Parse one durable proposal and verify its self-consistent graph shape.
///
/// # Errors
///
/// Returns [`INVALID_AUDIT_PROPOSAL`] for malformed, duplicate-keyed, or
/// self-inconsistent JSON.
pub fn parse_audit_proposal(text: &str) -> Result<AuditProposal, AuditUmbrellaRefusal> {
    if text.len() > MAX_AUDIT_ARTIFACT_BYTES {
        return Err(INVALID_AUDIT_PROPOSAL);
    }
    parse_unique(text, INVALID_AUDIT_PROPOSAL)
        .and_then(|()| serde_json::from_str(text).map_err(|_error| INVALID_AUDIT_PROPOSAL))
        .and_then(|proposal| {
            validate_audit_proposal(&proposal, None)?;
            Ok(proposal)
        })
}

/// Render a durable proposal as deterministic private JSON.
///
/// # Errors
///
/// Returns [`INVALID_AUDIT_PROPOSAL`] when the proposal is invalid or cannot
/// be serialized.
pub fn render_audit_proposal(proposal: &AuditProposal) -> Result<String, AuditUmbrellaRefusal> {
    validate_audit_proposal(proposal, None)?;
    render_artifact(proposal, INVALID_AUDIT_PROPOSAL)
}

/// Verify a parsed proposal still binds exactly to this snapshot and ledger.
///
/// # Errors
///
/// Returns an audit refusal when any artifact is invalid or the proposal does
/// not bind exactly to the supplied snapshot and ledger.
pub fn validate_audit_proposal_binding(
    proposal: &AuditProposal,
    snapshot: &AuditSnapshot,
    ledger: &AuditLedger,
) -> Result<(), AuditUmbrellaRefusal> {
    let summary = validate_audit_ledger(snapshot, ledger)?;
    if summary.blocked != 0
        || proposal.repository != snapshot.repository
        || proposal.umbrella != snapshot.umbrella.number
        || proposal.audited_sha != snapshot.audited_sha
        || proposal.snapshot_sha256 != audit_snapshot_sha256(snapshot)
        || proposal.ledger_sha256 != audit_ledger_sha256(ledger)
        || proposal.historical_leaf_numbers != normalized_numbers(&snapshot.historical_leaf_numbers)
        || proposal.direct_leaf_numbers != snapshot_direct_leaf_numbers(snapshot)
    {
        return Err(STALE_AUDIT_PROPOSAL);
    }
    let gap_ids = ledger
        .entries
        .iter()
        .filter(|entry| entry.status == RequirementStatus::Gap)
        .map(|entry| entry.id.as_str())
        .collect::<BTreeSet<_>>();
    validate_audit_proposal(proposal, Some(&gap_ids))?;
    let snapshot_numbers = snapshot
        .sources
        .iter()
        .map(|source| source.issue.number)
        .collect::<BTreeSet<_>>();
    let expected_numbers = proposal
        .expected_issues
        .iter()
        .map(|issue| issue.number)
        .collect::<BTreeSet<_>>();
    let dependency_numbers = audit_proposal_existing_numbers(proposal);
    if !snapshot_numbers.is_subset(&expected_numbers)
        || !dependency_numbers.is_subset(&expected_numbers)
    {
        return Err(STALE_AUDIT_PROPOSAL);
    }
    Ok(())
}

/// Return every existing issue a proposal may read or mutate in its graph.
#[must_use]
pub fn audit_proposal_existing_numbers(proposal: &AuditProposal) -> BTreeSet<u64> {
    // The persisted fingerprint set is authoritative for every issue whose
    // source content or graph may make the batch stale.  Start there rather
    // than only with dependency endpoints: snapshot sources that are not
    // themselves dependencies must still be re-read before a public write.
    let mut numbers = proposal
        .expected_issues
        .iter()
        .map(|issue| issue.number)
        .collect::<BTreeSet<_>>();
    numbers.extend(
        proposal
            .dependencies
            .iter()
            .chain(proposal.remove_dependencies.iter())
            .flat_map(|edge| [&edge.dependent, &edge.prerequisite])
            .filter_map(|node| match node {
                AuditDependencyNode::Existing { number } => Some(*number),
                AuditDependencyNode::New { .. } => None,
            }),
    );
    let _ = numbers.insert(proposal.umbrella);
    for leaf in &proposal.leaves {
        if leaf.state == AuditLeafState::Resolved {
            let _ = numbers.insert(leaf.number);
        }
    }
    numbers
}

/// Mark one leaf in flight before its GitHub create is attempted.
///
/// # Errors
///
/// Returns [`INVALID_AUDIT_PROPOSAL`] unless the named leaf is pending in a
/// valid incomplete proposal.
pub fn mark_audit_leaf_in_flight(
    proposal: &mut AuditProposal,
    identity: &str,
) -> Result<(), AuditUmbrellaRefusal> {
    let leaf = proposal
        .leaves
        .iter_mut()
        .find(|leaf| leaf.identity == identity)
        .ok_or(INVALID_AUDIT_PROPOSAL)?;
    if leaf.state != AuditLeafState::Pending {
        return Err(INVALID_AUDIT_PROPOSAL);
    }
    leaf.state = AuditLeafState::InFlight;
    validate_audit_proposal(proposal, None)
}

/// Bind one in-flight leaf to the exact issue creation read-back.
///
/// # Errors
///
/// Returns [`INVALID_AUDIT_PROPOSAL`] unless the supplied remote identity can
/// resolve exactly one in-flight leaf while preserving proposal validity.
pub fn record_audit_leaf_resolved(
    proposal: &mut AuditProposal,
    identity: &str,
    number: u64,
    issue_id: u64,
    url: &str,
) -> Result<(), AuditUmbrellaRefusal> {
    if number == 0 || issue_id == 0 || !valid_text(url, 4 * 1024) {
        return Err(INVALID_AUDIT_PROPOSAL);
    }
    let leaf = proposal
        .leaves
        .iter_mut()
        .find(|leaf| leaf.identity == identity)
        .ok_or(INVALID_AUDIT_PROPOSAL)?;
    if leaf.state != AuditLeafState::InFlight {
        return Err(INVALID_AUDIT_PROPOSAL);
    }
    leaf.state = AuditLeafState::Resolved;
    leaf.number = number;
    leaf.issue_id = issue_id;
    url.clone_into(&mut leaf.url);
    validate_audit_proposal(proposal, None)
}

/// Return a stable content identity for one leaf title/body pair.
#[must_use]
pub fn audit_leaf_identity(title: &str, body: &str) -> String {
    sha256(&format!("{title}\n{body}"))
}

/// Build a freshness fingerprint from an immutable snapshot issue.
#[must_use]
pub fn audit_issue_fingerprint(issue: &AuditIssue) -> AuditIssueFingerprint {
    AuditIssueFingerprint {
        number: issue.number,
        id: issue.id,
        updated_at: issue.updated_at.clone(),
        title_sha256: sha256(&issue.title),
        body_sha256: sha256(&issue.body),
    }
}

/// Mark an already-validated proposal complete only after live read-back succeeds.
///
/// # Errors
///
/// Returns [`INVALID_AUDIT_PROPOSAL`] unless every leaf is resolved and the
/// graph has already entered its durable in-flight state.
pub fn mark_audit_proposal_complete(
    proposal: &mut AuditProposal,
) -> Result<(), AuditUmbrellaRefusal> {
    if proposal
        .leaves
        .iter()
        .any(|leaf| leaf.state != AuditLeafState::Resolved)
    {
        return Err(INVALID_AUDIT_PROPOSAL);
    }
    if proposal.graph_state != AuditGraphState::InFlight {
        return Err(INVALID_AUDIT_PROPOSAL);
    }
    proposal.graph_state = AuditGraphState::Verified;
    proposal.complete = true;
    validate_audit_proposal(proposal, None)
}

/// Persist the transition that makes graph reconciliation safely resumable.
///
/// # Errors
///
/// Returns [`INVALID_AUDIT_PROPOSAL`] unless every leaf is resolved and no
/// graph mutation has yet been attempted.
pub fn mark_audit_graph_in_flight(
    proposal: &mut AuditProposal,
) -> Result<(), AuditUmbrellaRefusal> {
    if proposal
        .leaves
        .iter()
        .any(|leaf| leaf.state != AuditLeafState::Resolved)
        || proposal.complete
        || proposal.graph_state != AuditGraphState::Pending
    {
        return Err(INVALID_AUDIT_PROPOSAL);
    }
    proposal.graph_state = AuditGraphState::InFlight;
    validate_audit_proposal(proposal, None)
}

/// Replace all live issue fingerprints after a verified mutation read-back.
///
/// # Errors
///
/// Returns [`INVALID_AUDIT_PROPOSAL`] when the replacement fingerprints would
/// make the durable proposal invalid.
pub fn replace_audit_issue_fingerprints(
    proposal: &mut AuditProposal,
    fingerprints: Vec<AuditIssueFingerprint>,
) -> Result<(), AuditUmbrellaRefusal> {
    proposal.expected_issues = fingerprints;
    validate_audit_proposal(proposal, None)
}

fn validate_snapshot(snapshot: &AuditSnapshot) -> Result<(), AuditUmbrellaRefusal> {
    if snapshot.version != AUDIT_SNAPSHOT_VERSION
        || !valid_repository(&snapshot.repository)
        || !valid_branch(&snapshot.default_branch)
        || !valid_object_id(&snapshot.audited_sha)
        || snapshot.umbrella.number == 0
        || snapshot.umbrella.id == 0
        || snapshot.sources.is_empty()
        || snapshot.sources.len() > MAX_AUDIT_SOURCES
        || snapshot.historical_leaf_numbers.len() > MAX_AUDIT_SOURCES
        || normalized_numbers(&snapshot.historical_leaf_numbers) != snapshot.historical_leaf_numbers
    {
        return Err(INVALID_AUDIT_SNAPSHOT);
    }
    validate_issue(&snapshot.umbrella)?;
    let mut source_ids = BTreeSet::new();
    let mut source_numbers = BTreeSet::new();
    let mut historical_source_numbers = BTreeSet::new();
    let mut umbrella_seen = false;
    for source in &snapshot.sources {
        if !valid_source_id(&source.id)
            || !source_ids.insert(source.id.as_str())
            || !source_numbers.insert(source.issue.number)
            || source.roles.is_empty()
            || source.roles.len() > 8
            || source.roles.iter().any(|role| !valid_role(role))
            || normalized_strings(&source.roles) != source.roles
        {
            return Err(INVALID_AUDIT_SNAPSHOT);
        }
        validate_issue(&source.issue)?;
        if source
            .roles
            .iter()
            .any(|role| matches!(role.as_str(), "native" | "explicit" | "title" | "backlink"))
        {
            let _ = historical_source_numbers.insert(source.issue.number);
        }
        if source.issue.number == snapshot.umbrella.number {
            umbrella_seen = true;
            if source.issue != snapshot.umbrella
                || !source.roles.iter().any(|role| role == "umbrella")
            {
                return Err(INVALID_AUDIT_SNAPSHOT);
            }
        }
    }
    if !umbrella_seen
        || snapshot.historical_leaf_numbers.iter().any(|number| {
            *number == snapshot.umbrella.number
                || !source_numbers.contains(number)
                || !historical_source_numbers.contains(number)
        })
    {
        return Err(INVALID_AUDIT_SNAPSHOT);
    }
    Ok(())
}

fn validate_issue(issue: &AuditIssue) -> Result<(), AuditUmbrellaRefusal> {
    if issue.number == 0
        || issue.id == 0
        || !valid_text(&issue.title, MAX_AUDIT_LEAF_BODY_BYTES)
        // A historical issue may intentionally have no body.  It is still a
        // source that the audit must account for through its title and
        // metadata, so do not reject a complete snapshot merely for that.
        || !valid_optional_text(&issue.body, MAX_AUDIT_LEAF_BODY_BYTES)
        || !matches!(issue.state.as_str(), "open" | "closed")
        || !valid_timestamp(&issue.updated_at)
        || !valid_text(&issue.url, 4 * 1024)
    {
        return Err(INVALID_AUDIT_SNAPSHOT);
    }
    Ok(())
}

fn validate_leaf_draft(leaf: &AuditLeafDraft, umbrella: u64) -> Result<(), AuditUmbrellaRefusal> {
    diagnose_leaf_draft(leaf, umbrella, 1).map_err(|violation| violation.refusal())
}

fn diagnose_leaf_draft(
    leaf: &AuditLeafDraft,
    umbrella: u64,
    leaf_index: usize,
) -> Result<(), AuditProposalViolation> {
    let prefix = audit_leaf_prefix(umbrella);
    if !leaf.title.starts_with(&prefix) {
        return Err(AuditProposalViolation::LeafTitlePrefix {
            leaf: leaf_index,
            title: leaf.title.clone(),
        });
    }
    if leaf.title.len() > MAX_AUDIT_LEAF_TITLE_BYTES
        || !valid_single_line(&leaf.title, MAX_AUDIT_LEAF_TITLE_BYTES)
        || leaf.title[prefix.len()..].trim().is_empty()
    {
        return Err(AuditProposalViolation::LeafTitleShape {
            leaf: leaf_index,
            title: leaf.title.clone(),
        });
    }
    if !valid_text(&leaf.body, MAX_AUDIT_LEAF_BODY_BYTES) {
        return Err(AuditProposalViolation::LeafBodyShape {
            leaf: leaf_index,
            title: leaf.title.clone(),
        });
    }
    if leaf.body.lines().next() != Some(umbrella_leaf_opening_text(&umbrella.to_string()).as_str())
    {
        return Err(AuditProposalViolation::LeafOpening {
            leaf: leaf_index,
            title: leaf.title.clone(),
        });
    }
    if leaf.body.contains("<!-- larch:plan") {
        return Err(AuditProposalViolation::LeafPlanMarker {
            leaf: leaf_index,
            title: leaf.title.clone(),
        });
    }
    for heading in [
        "## Program context",
        "## Problem",
        "## Scope",
        "## Acceptance",
    ] {
        if !has_nonempty_section(&leaf.body, heading) {
            return Err(AuditProposalViolation::LeafSection {
                leaf: leaf_index,
                title: leaf.title.clone(),
                section: heading,
            });
        }
    }
    if !has_numbered_scope(&leaf.body) {
        return Err(AuditProposalViolation::LeafNumberedScope {
            leaf: leaf_index,
            title: leaf.title.clone(),
        });
    }
    if leaf.gap_ids.is_empty() {
        return Err(AuditProposalViolation::LeafGapIdsEmpty {
            leaf: leaf_index,
            title: leaf.title.clone(),
        });
    }
    if leaf.gap_ids.len() > MAX_AUDIT_REQUIREMENTS {
        return Err(AuditProposalViolation::LeafGapIdsTooMany {
            leaf: leaf_index,
            title: leaf.title.clone(),
        });
    }
    if let Some(gap_id) = leaf
        .gap_ids
        .iter()
        .find(|id| !bounded_ascii_identifier(id, true))
    {
        return Err(AuditProposalViolation::LeafGapIdMalformed {
            leaf: leaf_index,
            title: leaf.title.clone(),
            gap_id: gap_id.clone(),
        });
    }
    if normalized_strings(&leaf.gap_ids) != leaf.gap_ids {
        return Err(AuditProposalViolation::LeafGapIdsOrder {
            leaf: leaf_index,
            title: leaf.title.clone(),
        });
    }
    Ok(())
}

fn has_nonempty_section(body: &str, heading: &str) -> bool {
    let Some(index) = body.lines().position(|line| line == heading) else {
        return false;
    };
    body.lines()
        .skip(index + 1)
        .take_while(|line| !line.starts_with("## "))
        .any(|line| !line.trim().is_empty())
}

fn has_numbered_scope(body: &str) -> bool {
    let Some(index) = body.lines().position(|line| line == "## Scope") else {
        return false;
    };
    body.lines()
        .skip(index + 1)
        .take_while(|line| !line.starts_with("## "))
        .any(|line| line.trim_start().starts_with("1. "))
}

fn validate_audit_proposal(
    proposal: &AuditProposal,
    expected_gap_ids: Option<&BTreeSet<&str>>,
) -> Result<(), AuditUmbrellaRefusal> {
    if proposal.version != AUDIT_PROPOSAL_VERSION
        || !valid_repository(&proposal.repository)
        || proposal.umbrella == 0
        || !valid_object_id(&proposal.audited_sha)
        || !is_sha256(&proposal.snapshot_sha256)
        || !is_sha256(&proposal.ledger_sha256)
        || proposal.historical_leaf_numbers.len() > MAX_AUDIT_SOURCES
        || normalized_numbers(&proposal.historical_leaf_numbers) != proposal.historical_leaf_numbers
        || proposal
            .historical_leaf_numbers
            .contains(&proposal.umbrella)
        || proposal.leaves.len() > MAX_AUDIT_LEAVES
        || normalized_numbers(&proposal.direct_leaf_numbers) != proposal.direct_leaf_numbers
        || proposal.direct_leaf_numbers != proposal.historical_leaf_numbers
        || proposal
            .direct_leaf_numbers
            .len()
            .saturating_add(proposal.leaves.len())
            > MAX_AUDIT_LEAVES
    {
        return Err(INVALID_AUDIT_PROPOSAL);
    }
    let observed_gaps = validate_proposal_leaves(proposal)?;
    if (proposal.complete && proposal.graph_state != AuditGraphState::Verified)
        || (!proposal.complete && proposal.graph_state == AuditGraphState::Verified)
        || (proposal.graph_state != AuditGraphState::Pending
            && proposal
                .leaves
                .iter()
                .any(|leaf| leaf.state != AuditLeafState::Resolved))
    {
        return Err(INVALID_AUDIT_PROPOSAL);
    }
    if let Some(expected) = expected_gap_ids
        && observed_gaps
            .iter()
            .map(String::as_str)
            .collect::<BTreeSet<_>>()
            != *expected
    {
        return Err(INVALID_AUDIT_PROPOSAL);
    }
    let expected_numbers = proposal
        .expected_issues
        .iter()
        .map(|issue| issue.number)
        .collect::<BTreeSet<_>>();
    if expected_numbers.len() != proposal.expected_issues.len()
        || !expected_numbers.contains(&proposal.umbrella)
        || proposal
            .expected_issues
            .iter()
            .any(|issue| !valid_fingerprint(issue))
    {
        return Err(INVALID_AUDIT_PROPOSAL);
    }
    let known_new = proposal
        .leaves
        .iter()
        .map(|leaf| leaf.identity.as_str())
        .collect::<BTreeSet<_>>();
    validate_dependencies(
        &proposal.dependencies,
        &proposal.remove_dependencies,
        &expected_numbers,
        &known_new,
    )
}

fn validate_proposal_leaves(
    proposal: &AuditProposal,
) -> Result<BTreeSet<String>, AuditUmbrellaRefusal> {
    let mut leaf_identities = BTreeSet::new();
    let mut leaf_numbers = BTreeSet::new();
    let mut observed_gaps = BTreeSet::new();
    for leaf in &proposal.leaves {
        validate_leaf_draft(
            &AuditLeafDraft {
                title: leaf.title.clone(),
                body: leaf.body.clone(),
                gap_ids: leaf.gap_ids.clone(),
            },
            proposal.umbrella,
        )?;
        if leaf.identity != audit_leaf_identity(&leaf.title, &leaf.body)
            || !leaf.body.contains(&proposal.audited_sha)
            || !leaf_identities.insert(leaf.identity.clone())
            || leaf
                .gap_ids
                .iter()
                .any(|id| !observed_gaps.insert(id.clone()))
        {
            return Err(INVALID_AUDIT_PROPOSAL);
        }
        match leaf.state {
            AuditLeafState::Pending | AuditLeafState::InFlight
                if leaf.number != 0 || leaf.issue_id != 0 || !leaf.url.is_empty() =>
            {
                return Err(INVALID_AUDIT_PROPOSAL);
            }
            AuditLeafState::Resolved
                if leaf.number == 0
                    || leaf.issue_id == 0
                    || !valid_text(&leaf.url, 4 * 1024)
                    || !leaf_numbers.insert(leaf.number) =>
            {
                return Err(INVALID_AUDIT_PROPOSAL);
            }
            AuditLeafState::Pending | AuditLeafState::InFlight | AuditLeafState::Resolved => {}
        }
    }
    Ok(observed_gaps)
}

fn validate_dependencies(
    dependencies: &[AuditDependency],
    removals: &[AuditDependency],
    expected_numbers: &BTreeSet<u64>,
    known_new: &BTreeSet<&str>,
) -> Result<(), AuditUmbrellaRefusal> {
    diagnose_draft_dependencies(dependencies, removals, expected_numbers, known_new)
        .map_err(|violation| violation.refusal())
}

fn diagnose_draft_dependencies(
    dependencies: &[AuditDependency],
    removals: &[AuditDependency],
    expected_numbers: &BTreeSet<u64>,
    known_new: &BTreeSet<&str>,
) -> Result<(), AuditProposalViolation> {
    let mut additions = BTreeSet::new();
    for (index, edge) in dependencies.iter().enumerate() {
        let dependency = index + 1;
        if !valid_dependency_node(&edge.dependent, expected_numbers, known_new)
            || !valid_dependency_node(&edge.prerequisite, expected_numbers, known_new)
        {
            return Err(AuditProposalViolation::DependencyNode {
                dependency,
                removal: false,
            });
        }
        if edge.dependent == edge.prerequisite {
            return Err(AuditProposalViolation::DependencySelf {
                dependency,
                removal: false,
            });
        }
        if !additions.insert(edge) {
            return Err(AuditProposalViolation::DependencyDuplicate {
                dependency,
                removal: false,
            });
        }
    }
    let mut removed = BTreeSet::new();
    for (index, edge) in removals.iter().enumerate() {
        let dependency = index + 1;
        if !matches!(edge.dependent, AuditDependencyNode::Existing { .. })
            || !matches!(edge.prerequisite, AuditDependencyNode::Existing { .. })
            || !valid_dependency_node(&edge.dependent, expected_numbers, known_new)
            || !valid_dependency_node(&edge.prerequisite, expected_numbers, known_new)
        {
            return Err(AuditProposalViolation::DependencyNode {
                dependency,
                removal: true,
            });
        }
        if edge.dependent == edge.prerequisite {
            return Err(AuditProposalViolation::DependencySelf {
                dependency,
                removal: true,
            });
        }
        if additions.contains(edge) {
            return Err(AuditProposalViolation::DependencyConflict { dependency });
        }
        if !removed.insert(edge) {
            return Err(AuditProposalViolation::DependencyDuplicate {
                dependency,
                removal: true,
            });
        }
    }
    let mut graph: BTreeMap<String, BTreeSet<String>> = BTreeMap::new();
    for edge in dependencies {
        let prerequisite = node_key(&edge.prerequisite);
        let dependent = node_key(&edge.dependent);
        let _ = graph.entry(prerequisite.clone()).or_default();
        let _ = graph.entry(dependent.clone()).or_default();
        let _ = graph.entry(prerequisite).or_default().insert(dependent);
    }
    if graph_has_cycle(&graph) {
        Err(AuditProposalViolation::DependencyCycle)
    } else {
        Ok(())
    }
}

fn valid_dependency_node(
    node: &AuditDependencyNode,
    expected_numbers: &BTreeSet<u64>,
    known_new: &BTreeSet<&str>,
) -> bool {
    match node {
        AuditDependencyNode::Existing { number } => {
            let _ = expected_numbers;
            *number != 0
        }
        AuditDependencyNode::New { identity } => {
            is_sha256(identity) && known_new.contains(identity.as_str())
        }
    }
}

fn graph_has_cycle(graph: &BTreeMap<String, BTreeSet<String>>) -> bool {
    let mut visiting = BTreeSet::new();
    let mut visited = BTreeSet::new();
    graph
        .keys()
        .any(|node| graph_cycle_at(node, graph, &mut visiting, &mut visited))
}

fn graph_cycle_at(
    node: &str,
    graph: &BTreeMap<String, BTreeSet<String>>,
    visiting: &mut BTreeSet<String>,
    visited: &mut BTreeSet<String>,
) -> bool {
    if visited.contains(node) {
        return false;
    }
    if !visiting.insert(node.to_owned()) {
        return true;
    }
    let cycle = graph.get(node).is_some_and(|children| {
        children
            .iter()
            .any(|child| graph_cycle_at(child, graph, visiting, visited))
    });
    let _ = visiting.remove(node);
    let _ = visited.insert(node.to_owned());
    cycle
}

fn snapshot_issue_fingerprints(
    snapshot: &AuditSnapshot,
) -> Result<Vec<AuditIssueFingerprint>, AuditUmbrellaRefusal> {
    let mut values = snapshot
        .sources
        .iter()
        .map(|source| audit_issue_fingerprint(&source.issue))
        .collect::<Vec<_>>();
    values.sort_by_key(|issue| issue.number);
    values.dedup_by_key(|issue| issue.number);
    if values.len() != snapshot.sources.len()
        || values.first().is_none_or(|issue| issue.number == 0)
    {
        return Err(INVALID_AUDIT_SNAPSHOT);
    }
    Ok(values)
}

fn snapshot_direct_leaf_numbers(snapshot: &AuditSnapshot) -> Vec<u64> {
    let mut values = snapshot.historical_leaf_numbers.clone();
    values.sort_unstable();
    values.dedup();
    values
}

fn valid_fingerprint(value: &AuditIssueFingerprint) -> bool {
    value.number != 0
        && value.id != 0
        && valid_timestamp(&value.updated_at)
        && is_sha256(&value.title_sha256)
        && is_sha256(&value.body_sha256)
}

fn node_key(node: &AuditDependencyNode) -> String {
    match node {
        AuditDependencyNode::Existing { number } => format!("existing:{number}"),
        AuditDependencyNode::New { identity } => format!("new:{identity}"),
    }
}

fn parse_unique(text: &str, refusal: AuditUmbrellaRefusal) -> Result<(), AuditUmbrellaRefusal> {
    OrderedJson::parse_unique(text)
        .map(|_value| ())
        .map_err(|_error| refusal)
}

fn render_artifact<T: Serialize>(
    artifact: &T,
    refusal: AuditUmbrellaRefusal,
) -> Result<String, AuditUmbrellaRefusal> {
    let text = serde_json::to_string_pretty(artifact)
        .map(|text| format!("{text}\n"))
        .map_err(|_error| refusal)?;
    if text.len() > MAX_AUDIT_ARTIFACT_BYTES {
        Err(refusal)
    } else {
        Ok(text)
    }
}

fn sha256(text: &str) -> String {
    format!("{:x}", Sha256::digest(text.as_bytes()))
}

fn is_sha256(value: &str) -> bool {
    value.len() == 64
        && value
            .bytes()
            .all(|byte| matches!(byte, b'0'..=b'9' | b'a'..=b'f'))
}

fn valid_object_id(value: &str) -> bool {
    matches!(value.len(), 40 | 64)
        && value
            .bytes()
            .all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte))
}

fn valid_repository(value: &str) -> bool {
    let mut pieces = value.split('/');
    let Some(owner) = pieces.next() else {
        return false;
    };
    let Some(name) = pieces.next() else {
        return false;
    };
    pieces.next().is_none()
        && [owner, name].iter().all(|piece| {
            !piece.is_empty()
                && piece.len() <= 100
                && piece
                    .bytes()
                    .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'.' | b'-' | b'_'))
        })
}

fn valid_branch(value: &str) -> bool {
    !value.is_empty()
        && value.len() <= 255
        && !value.starts_with('-')
        && !value.contains(['\r', '\n', ' ', '\t', '\\'])
        && !value.contains("..")
        && !value.contains("//")
}

fn valid_timestamp(value: &str) -> bool {
    !value.contains(['\r', '\n'])
        && DateTime::parse_from_rfc3339(value)
            .is_ok_and(|timestamp| timestamp.offset().local_minus_utc() == 0)
}

fn valid_source_id(value: &str) -> bool {
    let Some((kind, number)) = value.split_once(':') else {
        return false;
    };
    matches!(kind, "umbrella" | "leaf" | "control")
        && number.parse::<u64>().is_ok_and(|number| number != 0)
}

fn valid_role(value: &str) -> bool {
    matches!(
        value,
        "umbrella" | "native" | "explicit" | "title" | "backlink" | "control"
    )
}

fn valid_single_line(value: &str, limit: usize) -> bool {
    valid_text(value, limit) && !value.contains(['\r', '\n']) && value.trim() == value
}

fn valid_text(value: &str, limit: usize) -> bool {
    !value.is_empty()
        && value.len() <= limit
        && !value.contains('\r')
        && !value
            .chars()
            .any(|character| character.is_control() && character != '\n' && character != '\t')
}

fn valid_optional_text(value: &str, limit: usize) -> bool {
    value.is_empty() || valid_text(value, limit)
}

fn evidence_valid(values: &[String]) -> bool {
    values.len() <= 256
        && values
            .iter()
            .all(|value| valid_single_line(value, 4 * 1024))
}

fn normalized_numbers(values: &[u64]) -> Vec<u64> {
    let mut sorted = values.to_vec();
    sorted.sort_unstable();
    sorted.dedup();
    sorted
}

fn normalized_strings(values: &[String]) -> Vec<String> {
    let mut sorted = values.to_vec();
    sorted.sort();
    sorted.dedup();
    sorted
}

#[cfg(test)]
mod tests {
    use super::*;

    fn issue(number: u64, title: &str, body: &str) -> AuditIssue {
        AuditIssue {
            number,
            id: number + 100,
            title: title.to_owned(),
            body: body.to_owned(),
            state: "open".to_owned(),
            updated_at: "2026-08-11T12:00:00Z".to_owned(),
            url: format!("https://github.com/o/r/issues/{number}"),
        }
    }

    fn snapshot() -> AuditSnapshot {
        let umbrella = issue(
            40,
            "[UMBRELLA] Fixture",
            "## Requirement\n- cover the success path\n",
        );
        AuditSnapshot {
            version: AUDIT_SNAPSHOT_VERSION,
            repository: "o/r".to_owned(),
            default_branch: "main".to_owned(),
            audited_sha: "a".repeat(40),
            umbrella: umbrella.clone(),
            sources: vec![
                AuditSource {
                    id: "umbrella:40".to_owned(),
                    roles: vec!["umbrella".to_owned()],
                    issue: umbrella,
                },
                AuditSource {
                    id: "leaf:41".to_owned(),
                    roles: vec!["native".to_owned()],
                    issue: issue(
                        41,
                        "[LEAF OF 40] Existing leaf",
                        "This is a leaf of umbrella #40. Read the umbrella in full before acting.\n- preserve compatibility\n",
                    ),
                },
                AuditSource {
                    id: "control:42".to_owned(),
                    roles: vec!["control".to_owned()],
                    issue: issue(
                        42,
                        "[CHIEF UMBRELLA] Fixture program",
                        "## Program principle\n- preserve the wire contract\n",
                    ),
                },
            ],
            historical_leaf_numbers: vec![41],
        }
    }

    fn ledger(snapshot: &AuditSnapshot) -> AuditLedger {
        let entries = audit_source_items(snapshot)
            .into_iter()
            .enumerate()
            .map(|(index, item)| AuditLedgerEntry {
                id: format!("R-{}", index + 1),
                source_id: item.id,
                requirement: "Account for the source item".to_owned(),
                status: RequirementStatus::Gap,
                code_evidence: vec!["src/lib.rs: symbol is absent".to_owned()],
                test_evidence: vec!["tests/fixture.rs: missing assertion".to_owned()],
                reason: String::new(),
            })
            .collect();
        AuditLedger {
            version: AUDIT_LEDGER_VERSION,
            snapshot_sha256: audit_snapshot_sha256(snapshot),
            entries,
        }
    }

    #[test]
    fn a_ledger_must_cover_every_immutable_source_item() {
        let snapshot = snapshot();
        let mut ledger = ledger(&snapshot);
        let _ = ledger.entries.pop();
        assert_eq!(
            validate_audit_ledger(&snapshot, &ledger),
            Err(INVALID_AUDIT_LEDGER)
        );
    }

    #[test]
    fn diagnose_accepts_a_complete_ledger() {
        let snapshot = snapshot();
        let ledger = ledger(&snapshot);
        let summary = diagnose_audit_ledger(&snapshot, &ledger).expect("valid ledger");
        assert_eq!(summary.total, ledger.entries.len());
    }

    #[test]
    fn diagnose_reports_uncovered_source_count() {
        let snapshot = snapshot();
        let mut ledger = ledger(&snapshot);
        let _ = ledger.entries.pop();
        assert_eq!(
            diagnose_audit_ledger(&snapshot, &ledger),
            Err(AuditLedgerViolation::Coverage {
                uncovered: 1,
                unknown: 0,
            })
        );
    }

    #[test]
    fn diagnose_reports_unknown_source_count() {
        let snapshot = snapshot();
        let mut ledger = ledger(&snapshot);
        let next = ledger.entries.len() + 1;
        ledger.entries.push(AuditLedgerEntry {
            id: format!("R-{next}"),
            source_id: "unknown:source:1".to_owned(),
            requirement: "Account for the source item".to_owned(),
            status: RequirementStatus::Gap,
            code_evidence: vec!["src/lib.rs: symbol is absent".to_owned()],
            test_evidence: vec!["tests/fixture.rs: missing assertion".to_owned()],
            reason: String::new(),
        });
        assert_eq!(
            diagnose_audit_ledger(&snapshot, &ledger),
            Err(AuditLedgerViolation::Coverage {
                uncovered: 0,
                unknown: 1,
            })
        );
    }

    #[test]
    fn diagnose_reports_duplicate_entry_id() {
        let snapshot = snapshot();
        let mut ledger = ledger(&snapshot);
        let first = ledger.entries[0].id.clone();
        ledger.entries[1].id = first.clone();
        assert_eq!(
            diagnose_audit_ledger(&snapshot, &ledger),
            Err(AuditLedgerViolation::DuplicateEntryId { id: first })
        );
    }

    #[test]
    fn diagnose_reports_satisfied_evidence_and_maps_to_ledger_refusal() {
        let snapshot = snapshot();
        let mut ledger = ledger(&snapshot);
        ledger.entries[0].status = RequirementStatus::Satisfied;
        ledger.entries[0].reason = "an unexpected reason".to_owned();
        let violation = diagnose_audit_ledger(&snapshot, &ledger).expect_err("violation");
        assert_eq!(
            violation,
            AuditLedgerViolation::SatisfiedEvidence {
                id: "R-1".to_owned(),
            }
        );
        assert_eq!(violation.refusal(), INVALID_AUDIT_LEDGER);
    }

    #[test]
    fn diagnose_accepts_security_keywords_as_ordinary_audit_text() {
        let snapshot = snapshot();
        let mut ledger = ledger(&snapshot);
        ledger.entries[0].requirement = "Preserve the secret-scrub guarantees".to_owned();
        diagnose_audit_ledger(&snapshot, &ledger).expect("security terms are ordinary text");
    }

    #[test]
    fn violation_constraint_names_are_stable() {
        assert_eq!(
            AuditLedgerViolation::Coverage {
                uncovered: 0,
                unknown: 0,
            }
            .constraint(),
            "coverage"
        );
        assert_eq!(
            AuditLedgerViolation::DuplicateEntryId {
                id: "R-1".to_owned()
            }
            .constraint(),
            "duplicate-entry-id"
        );
        assert_eq!(AuditLedgerViolation::Snapshot.constraint(), "snapshot");
        assert_eq!(
            AuditLedgerViolation::SatisfiedEvidence {
                id: "R-1".to_owned()
            }
            .entry_id(),
            Some("R-1")
        );
        assert_eq!(
            AuditLedgerViolation::Coverage {
                uncovered: 1,
                unknown: 0,
            }
            .entry_id(),
            None
        );
    }

    #[test]
    fn proposal_violation_constraint_names_and_metadata_are_stable() {
        let title = || "[LEAF OF 40] Repair the gap".to_owned();
        let violations = vec![
            (AuditProposalViolation::Snapshot, "snapshot"),
            (
                AuditProposalViolation::Ledger {
                    violation: AuditLedgerViolation::Version,
                },
                "ledger",
            ),
            (AuditProposalViolation::BlockedLedger, "blocked-ledger"),
            (AuditProposalViolation::Version, "version"),
            (
                AuditProposalViolation::UnexpectedLeaves,
                "unexpected-leaves",
            ),
            (
                AuditProposalViolation::MissingLeaves {
                    gap_id: "R-1".to_owned(),
                },
                "missing-leaves",
            ),
            (AuditProposalViolation::TooManyLeaves, "too-many-leaves"),
            (AuditProposalViolation::LeafCapacity, "leaf-capacity"),
            (
                AuditProposalViolation::LeafTitlePrefix {
                    leaf: 1,
                    title: title(),
                },
                "leaf-title-prefix",
            ),
            (
                AuditProposalViolation::LeafTitleShape {
                    leaf: 1,
                    title: title(),
                },
                "leaf-title-shape",
            ),
            (
                AuditProposalViolation::LeafBodyShape {
                    leaf: 1,
                    title: title(),
                },
                "leaf-body-shape",
            ),
            (
                AuditProposalViolation::LeafOpening {
                    leaf: 1,
                    title: title(),
                },
                "leaf-opening",
            ),
            (
                AuditProposalViolation::LeafPlanMarker {
                    leaf: 1,
                    title: title(),
                },
                "leaf-plan-marker",
            ),
            (
                AuditProposalViolation::LeafSection {
                    leaf: 1,
                    title: title(),
                    section: "## Scope",
                },
                "leaf-section",
            ),
            (
                AuditProposalViolation::LeafNumberedScope {
                    leaf: 1,
                    title: title(),
                },
                "leaf-numbered-scope",
            ),
            (
                AuditProposalViolation::LeafGapIdsEmpty {
                    leaf: 1,
                    title: title(),
                },
                "leaf-gap-ids-empty",
            ),
            (
                AuditProposalViolation::LeafGapIdsTooMany {
                    leaf: 1,
                    title: title(),
                },
                "leaf-gap-ids-too-many",
            ),
            (
                AuditProposalViolation::LeafGapIdMalformed {
                    leaf: 1,
                    title: title(),
                    gap_id: "bad:id".to_owned(),
                },
                "leaf-gap-id-malformed",
            ),
            (
                AuditProposalViolation::LeafGapIdsOrder {
                    leaf: 1,
                    title: title(),
                },
                "leaf-gap-ids-order",
            ),
            (
                AuditProposalViolation::LeafAuditedSha {
                    leaf: 1,
                    title: title(),
                },
                "leaf-audited-sha",
            ),
            (
                AuditProposalViolation::DuplicateLeaf {
                    leaf: 1,
                    title: title(),
                },
                "duplicate-leaf",
            ),
            (
                AuditProposalViolation::UnknownGapId {
                    leaf: 1,
                    title: title(),
                    gap_id: "R-2".to_owned(),
                },
                "unknown-gap-id",
            ),
            (
                AuditProposalViolation::DuplicateGapId {
                    leaf: 1,
                    title: title(),
                    gap_id: "R-1".to_owned(),
                },
                "duplicate-gap-id",
            ),
            (
                AuditProposalViolation::UncoveredGapId {
                    gap_id: "R-3".to_owned(),
                },
                "uncovered-gap-id",
            ),
            (
                AuditProposalViolation::DependencyNode {
                    dependency: 1,
                    removal: false,
                },
                "dependency-node",
            ),
            (
                AuditProposalViolation::DependencySelf {
                    dependency: 1,
                    removal: false,
                },
                "dependency-self",
            ),
            (
                AuditProposalViolation::DependencyDuplicate {
                    dependency: 1,
                    removal: true,
                },
                "dependency-duplicate",
            ),
            (
                AuditProposalViolation::DependencyConflict { dependency: 1 },
                "dependency-conflict",
            ),
            (AuditProposalViolation::DependencyCycle, "dependency-cycle"),
            (AuditProposalViolation::ProposalShape, "proposal-shape"),
        ];

        for (violation, expected_constraint) in &violations {
            assert_eq!(violation.constraint(), *expected_constraint);
            let _ = violation.leaf_index();
            let _ = violation.leaf_title();
            let _ = violation.gap_id();
            let _ = violation.section();
            let _ = violation.dependency();
            let expected_refusal = match violation {
                AuditProposalViolation::Snapshot => INVALID_AUDIT_SNAPSHOT,
                AuditProposalViolation::Ledger { .. } => INVALID_AUDIT_LEDGER,
                _ => INVALID_AUDIT_PROPOSAL,
            };
            assert_eq!(violation.refusal(), expected_refusal);
        }

        let section = &violations[13].0;
        assert_eq!(section.leaf_index(), Some(1));
        assert_eq!(section.leaf_title(), Some(title().as_str()));
        assert_eq!(section.section(), Some("## Scope"));
        assert_eq!(violations[5].0.gap_id(), Some("R-1"));
        assert_eq!(violations[24].0.dependency(), Some((1, false)));
        assert_eq!(violations[26].0.dependency(), Some((1, true)));
        assert_eq!(violations[27].0.dependency(), Some((1, true)));
    }

    #[test]
    fn a_valid_batch_binds_every_gap_once_and_rejects_cycles() {
        let snapshot = snapshot();
        let ledger = ledger(&snapshot);
        let gap_ids = ledger
            .entries
            .iter()
            .map(|entry| entry.id.clone())
            .collect::<Vec<_>>();
        let body = format!(
            "{}\n\n## Program context\n\nCurrent audit evidence at {}.\n\n## Problem\n\nA gap remains.\n\n## Scope\n\n1. Fix it.\n\n## Acceptance\n\n- It is covered.\n",
            umbrella_leaf_opening_text("40"),
            snapshot.audited_sha,
        );
        let draft = AuditProposalDraft {
            version: AUDIT_PROPOSAL_VERSION,
            leaves: vec![AuditLeafDraft {
                title: "[LEAF OF 40] Close the audited gap".to_owned(),
                body,
                gap_ids,
            }],
            dependencies: Vec::new(),
            remove_dependencies: Vec::new(),
        };
        let mut cyclic = build_audit_proposal(&snapshot, &ledger, &draft).expect("proposal");
        validate_audit_proposal_binding(&cyclic, &snapshot, &ledger).expect("binding");

        let identity = cyclic.leaves[0].identity.clone();
        cyclic.dependencies = vec![
            AuditDependency {
                dependent: AuditDependencyNode::Existing { number: 41 },
                prerequisite: AuditDependencyNode::New {
                    identity: identity.clone(),
                },
            },
            AuditDependency {
                dependent: AuditDependencyNode::New { identity },
                prerequisite: AuditDependencyNode::Existing { number: 41 },
            },
        ];
        assert_eq!(render_audit_proposal(&cyclic), Err(INVALID_AUDIT_PROPOSAL));
    }

    #[test]
    fn proposal_records_the_create_state_before_remote_identity() {
        let snapshot = snapshot();
        let ledger = ledger(&snapshot);
        let body = format!(
            "{}\n\n## Program context\n\nEvidence at {}.\n\n## Problem\n\nGap.\n\n## Scope\n\n1. Fix it.\n\n## Acceptance\n\n- Covered.\n",
            umbrella_leaf_opening_text("40"),
            snapshot.audited_sha,
        );
        let draft = AuditProposalDraft {
            version: AUDIT_PROPOSAL_VERSION,
            leaves: vec![AuditLeafDraft {
                title: "[LEAF OF 40] Close every gap".to_owned(),
                body,
                gap_ids: ledger
                    .entries
                    .iter()
                    .map(|entry| entry.id.clone())
                    .collect(),
            }],
            dependencies: Vec::new(),
            remove_dependencies: Vec::new(),
        };
        let mut proposal = build_audit_proposal(&snapshot, &ledger, &draft).expect("proposal");
        let identity = proposal.leaves[0].identity.clone();
        mark_audit_leaf_in_flight(&mut proposal, &identity).expect("in flight");
        assert_eq!(proposal.leaves[0].state, AuditLeafState::InFlight);
        record_audit_leaf_resolved(
            &mut proposal,
            &identity,
            42,
            142,
            "https://github.com/o/r/issues/42",
        )
        .expect("resolved");
        mark_audit_graph_in_flight(&mut proposal).expect("graph in flight");
        mark_audit_proposal_complete(&mut proposal).expect("complete");
    }

    #[test]
    fn persisted_leaf_must_keep_the_audited_sha_in_its_body() {
        let snapshot = snapshot();
        let ledger = ledger(&snapshot);
        let body = format!(
            "{}\n\n## Program context\n\nEvidence at {}.\n\n## Problem\n\nGap.\n\n## Scope\n\n1. Fix it.\n\n## Acceptance\n\n- Covered.\n",
            umbrella_leaf_opening_text("40"),
            snapshot.audited_sha,
        );
        let draft = AuditProposalDraft {
            version: AUDIT_PROPOSAL_VERSION,
            leaves: vec![AuditLeafDraft {
                title: "[LEAF OF 40] Keep the audit binding".to_owned(),
                body,
                gap_ids: ledger
                    .entries
                    .iter()
                    .map(|entry| entry.id.clone())
                    .collect(),
            }],
            dependencies: Vec::new(),
            remove_dependencies: Vec::new(),
        };
        let mut proposal = build_audit_proposal(&snapshot, &ledger, &draft).expect("proposal");
        proposal.leaves[0].body = proposal.leaves[0]
            .body
            .replace(&snapshot.audited_sha, &"b".repeat(40));
        proposal.leaves[0].identity =
            audit_leaf_identity(&proposal.leaves[0].title, &proposal.leaves[0].body);
        assert_eq!(
            render_audit_proposal(&proposal),
            Err(INVALID_AUDIT_PROPOSAL)
        );
    }

    #[test]
    fn proposal_binds_every_source_and_rejects_control_as_a_leaf() {
        let snapshot = snapshot();
        let ledger = ledger(&snapshot);
        let draft = AuditProposalDraft {
            version: AUDIT_PROPOSAL_VERSION,
            leaves: Vec::new(),
            dependencies: Vec::new(),
            remove_dependencies: Vec::new(),
        };
        let no_gap_ledger = AuditLedger {
            entries: ledger
                .entries
                .into_iter()
                .map(|mut entry| {
                    entry.status = RequirementStatus::Satisfied;
                    entry.reason.clear();
                    entry
                })
                .collect(),
            ..ledger
        };
        let proposal = build_audit_proposal(&snapshot, &no_gap_ledger, &draft).expect("proposal");
        assert_eq!(
            audit_proposal_existing_numbers(&proposal),
            BTreeSet::from([40, 41, 42])
        );

        let mut control_as_leaf = snapshot;
        control_as_leaf.historical_leaf_numbers = vec![42];
        assert_eq!(
            render_audit_snapshot(&control_as_leaf),
            Err(INVALID_AUDIT_SNAPSHOT)
        );
    }

    fn leaf_body(snapshot: &AuditSnapshot) -> String {
        format!(
            "{}\n\n## Program context\n\nEvidence at {}.\n\n## Problem\n\nA durable audit gap remains.\n\n## Scope\n\n1. Repair the audited behavior.\n\n## Acceptance\n\n- The audit gap is covered.\n",
            umbrella_leaf_opening_text(&snapshot.umbrella.number.to_string()),
            snapshot.audited_sha,
        )
    }

    fn gap_draft(snapshot: &AuditSnapshot, ledger: &AuditLedger) -> AuditProposalDraft {
        AuditProposalDraft {
            version: AUDIT_PROPOSAL_VERSION,
            leaves: vec![AuditLeafDraft {
                title: format!(
                    "[LEAF OF {}] Repair the exhaustive audit gap",
                    snapshot.umbrella.number
                ),
                body: leaf_body(snapshot),
                gap_ids: ledger
                    .entries
                    .iter()
                    .filter(|entry| entry.status == RequirementStatus::Gap)
                    .map(|entry| entry.id.clone())
                    .collect(),
            }],
            dependencies: Vec::new(),
            remove_dependencies: Vec::new(),
        }
    }

    #[test]
    fn audit_artifacts_round_trip_and_reject_ambiguous_or_oversized_json() {
        let snapshot = snapshot();
        let snapshot_text = render_audit_snapshot(&snapshot).expect("render snapshot");
        assert_eq!(parse_audit_snapshot(&snapshot_text), Ok(snapshot.clone()));
        assert_eq!(audit_snapshot_sha256(&snapshot).len(), 64);
        assert_eq!(
            parse_audit_snapshot(r#"{"version":1,"version":1}"#),
            Err(INVALID_AUDIT_SNAPSHOT)
        );

        let ledger = ledger(&snapshot);
        let ledger_text = render_audit_ledger(&ledger).expect("render ledger");
        assert_eq!(parse_audit_ledger(&ledger_text), Ok(ledger.clone()));
        assert_eq!(audit_ledger_sha256(&ledger).len(), 64);
        assert_eq!(
            parse_audit_ledger(r#"{"version":1,"version":1}"#),
            Err(INVALID_AUDIT_LEDGER)
        );

        let proposal = build_audit_proposal(&snapshot, &ledger, &gap_draft(&snapshot, &ledger))
            .expect("build proposal");
        let proposal_text = render_audit_proposal(&proposal).expect("render proposal");
        assert_eq!(parse_audit_proposal(&proposal_text), Ok(proposal));
        assert_eq!(
            parse_audit_proposal(r#"{"version":1,"version":1}"#),
            Err(INVALID_AUDIT_PROPOSAL)
        );

        let oversized = " ".repeat(MAX_AUDIT_ARTIFACT_BYTES + 1);
        assert_eq!(
            parse_audit_snapshot(&oversized),
            Err(INVALID_AUDIT_SNAPSHOT)
        );
        assert_eq!(parse_audit_ledger(&oversized), Err(INVALID_AUDIT_LEDGER));
        assert_eq!(
            parse_audit_proposal(&oversized),
            Err(INVALID_AUDIT_PROPOSAL)
        );
    }

    #[test]
    fn ledger_classification_requires_evidence_and_tracks_every_status() {
        let snapshot = snapshot();
        let mut classified = ledger(&snapshot);
        for (index, entry) in classified.entries.iter_mut().enumerate() {
            match index % 4 {
                0 => entry.status = RequirementStatus::Satisfied,
                1 => {
                    entry.status = RequirementStatus::Gap;
                    entry.test_evidence.clear();
                }
                2 => {
                    entry.status = RequirementStatus::NotApplicable;
                    entry.code_evidence.clear();
                    entry.test_evidence.clear();
                    entry.reason = "The source item does not define runtime behavior.".to_owned();
                }
                _ => {
                    entry.status = RequirementStatus::Blocked;
                    entry.code_evidence.clear();
                    entry.test_evidence.clear();
                    entry.reason = "The required upstream evidence is unavailable.".to_owned();
                }
            }
        }

        let summary = validate_audit_ledger(&snapshot, &classified).expect("valid ledger");
        assert_eq!(summary.total, classified.entries.len());
        assert_eq!(
            summary.satisfied + summary.gaps + summary.not_applicable + summary.blocked,
            summary.total
        );
        assert!(summary.satisfied > 0);
        assert!(summary.gaps > 0);
        assert!(summary.not_applicable > 0);
        assert!(summary.blocked > 0);

        let mut satisfied_with_reason = classified.clone();
        satisfied_with_reason.entries[0].reason = "must remain empty".to_owned();
        assert_eq!(
            validate_audit_ledger(&snapshot, &satisfied_with_reason),
            Err(INVALID_AUDIT_LEDGER)
        );

        let mut gap_without_evidence = classified.clone();
        gap_without_evidence.entries[1].code_evidence.clear();
        assert_eq!(
            validate_audit_ledger(&snapshot, &gap_without_evidence),
            Err(INVALID_AUDIT_LEDGER)
        );

        let mut not_applicable_with_evidence = classified.clone();
        not_applicable_with_evidence.entries[2]
            .code_evidence
            .push("src/lib.rs:1".to_owned());
        assert_eq!(
            validate_audit_ledger(&snapshot, &not_applicable_with_evidence),
            Err(INVALID_AUDIT_LEDGER)
        );

        let mut blocked_without_reason = classified.clone();
        blocked_without_reason.entries[3].reason.clear();
        assert_eq!(
            validate_audit_ledger(&snapshot, &blocked_without_reason),
            Err(INVALID_AUDIT_LEDGER)
        );

        let mut security_terms = classified;
        security_terms.entries[0].requirement =
            "Document the credential redaction behavior".to_owned();
        validate_audit_ledger(&snapshot, &security_terms)
            .expect("security terms do not invalidate the ledger");
    }

    #[test]
    fn snapshot_shape_rejects_invalid_metadata_and_leaf_provenance() {
        let valid = snapshot();
        assert!(render_audit_snapshot(&valid).is_ok());

        let mut invalid_version = valid.clone();
        invalid_version.version = 0;
        assert_eq!(
            render_audit_snapshot(&invalid_version),
            Err(INVALID_AUDIT_SNAPSHOT)
        );

        let mut invalid_repository = valid.clone();
        invalid_repository.repository = "owner/not a repository".to_owned();
        assert_eq!(
            render_audit_snapshot(&invalid_repository),
            Err(INVALID_AUDIT_SNAPSHOT)
        );

        let mut invalid_branch = valid.clone();
        invalid_branch.default_branch = "main..backup".to_owned();
        assert_eq!(
            render_audit_snapshot(&invalid_branch),
            Err(INVALID_AUDIT_SNAPSHOT)
        );

        let mut invalid_sha = valid.clone();
        invalid_sha.audited_sha = "A".repeat(40);
        assert_eq!(
            render_audit_snapshot(&invalid_sha),
            Err(INVALID_AUDIT_SNAPSHOT)
        );

        let mut missing_umbrella = valid.clone();
        missing_umbrella.sources.remove(0);
        assert_eq!(
            render_audit_snapshot(&missing_umbrella),
            Err(INVALID_AUDIT_SNAPSHOT)
        );

        let mut unsorted_roles = valid.clone();
        unsorted_roles.sources[1].roles = vec!["title".to_owned(), "native".to_owned()];
        assert_eq!(
            render_audit_snapshot(&unsorted_roles),
            Err(INVALID_AUDIT_SNAPSHOT)
        );

        let mut duplicate_source = valid.clone();
        duplicate_source.sources[2].id = "leaf:41".to_owned();
        assert_eq!(
            render_audit_snapshot(&duplicate_source),
            Err(INVALID_AUDIT_SNAPSHOT)
        );

        let mut duplicate_history = valid.clone();
        duplicate_history.historical_leaf_numbers = vec![41, 41];
        assert_eq!(
            render_audit_snapshot(&duplicate_history),
            Err(INVALID_AUDIT_SNAPSHOT)
        );

        let mut mismatched_umbrella = valid;
        mismatched_umbrella.sources[0].issue.title = "different".to_owned();
        assert_eq!(
            render_audit_snapshot(&mismatched_umbrella),
            Err(INVALID_AUDIT_SNAPSHOT)
        );
    }

    #[test]
    fn leaf_drafts_reject_unbound_or_unsafe_public_content() {
        let snapshot = snapshot();
        let ledger = ledger(&snapshot);
        let valid = gap_draft(&snapshot, &ledger).leaves.remove(0);
        assert_eq!(
            validate_leaf_draft(&valid, snapshot.umbrella.number),
            Ok(())
        );

        let mut wrong_title = valid.clone();
        wrong_title.title = "Repair the audit gap".to_owned();
        assert_eq!(
            validate_leaf_draft(&wrong_title, snapshot.umbrella.number),
            Err(INVALID_AUDIT_PROPOSAL)
        );

        let mut missing_opening = valid.clone();
        missing_opening.body =
            missing_opening
                .body
                .replacen("This is a leaf", "This audit concerns", 1);
        assert_eq!(
            validate_leaf_draft(&missing_opening, snapshot.umbrella.number),
            Err(INVALID_AUDIT_PROPOSAL)
        );

        let mut missing_scope_item = valid.clone();
        missing_scope_item.body = missing_scope_item.body.replace("1. Repair", "- Repair");
        assert_eq!(
            validate_leaf_draft(&missing_scope_item, snapshot.umbrella.number),
            Err(INVALID_AUDIT_PROPOSAL)
        );

        let mut protected_marker = valid.clone();
        protected_marker.body.push_str("\n<!-- larch:plan v1 -->\n");
        assert_eq!(
            validate_leaf_draft(&protected_marker, snapshot.umbrella.number),
            Err(INVALID_AUDIT_PROPOSAL)
        );

        let mut duplicate_gaps = valid.clone();
        duplicate_gaps
            .gap_ids
            .push(duplicate_gaps.gap_ids[0].clone());
        assert_eq!(
            validate_leaf_draft(&duplicate_gaps, snapshot.umbrella.number),
            Err(INVALID_AUDIT_PROPOSAL)
        );

        let mut security_terms = valid;
        security_terms.title = format!(
            "{}Preserve secret-scrub guarantees",
            audit_leaf_prefix(snapshot.umbrella.number)
        );
        security_terms
            .body
            .push_str("\nRCE details must remain private.\n");
        validate_leaf_draft(&security_terms, snapshot.umbrella.number)
            .expect("security terms do not invalidate a leaf proposal");
    }

    #[test]
    fn proposal_diagnostics_name_numbered_scope_and_ledger_entry_ids() {
        let snapshot = snapshot();
        let mut ledger = ledger(&snapshot);
        for entry in &mut ledger.entries[1..] {
            entry.status = RequirementStatus::Satisfied;
        }
        let valid = gap_draft(&snapshot, &ledger);

        let mut bullet_scope = valid.clone();
        bullet_scope.leaves[0].body = bullet_scope.leaves[0].body.replace("1. Repair", "- Repair");
        let numbered = diagnose_audit_proposal(&snapshot, &ledger, &bullet_scope)
            .expect_err("numbered scope is required");
        assert_eq!(numbered.constraint(), "leaf-numbered-scope");
        assert_eq!(numbered.leaf_index(), Some(1));
        assert_eq!(numbered.leaf_title(), Some(valid.leaves[0].title.as_str()));
        assert_eq!(numbered.refusal(), INVALID_AUDIT_PROPOSAL);

        let mut source_id_gap = valid;
        source_id_gap.leaves[0].gap_ids = vec![ledger.entries[0].source_id.clone()];
        let unknown = diagnose_audit_proposal(&snapshot, &ledger, &source_id_gap)
            .expect_err("source_id is not a gap id");
        assert_eq!(unknown.constraint(), "leaf-gap-id-malformed");
        assert_eq!(unknown.leaf_index(), Some(1));
        assert_eq!(unknown.gap_id(), Some(ledger.entries[0].source_id.as_str()));
        assert_eq!(unknown.refusal(), INVALID_AUDIT_PROPOSAL);
    }

    #[test]
    fn proposal_diagnostics_cover_batch_and_gap_ownership_rules() {
        let snapshot = snapshot();
        let ledger = ledger(&snapshot);
        let valid = gap_draft(&snapshot, &ledger);

        let mut invalid_snapshot = snapshot.clone();
        invalid_snapshot.version = 0;
        assert_eq!(
            diagnose_audit_proposal(&invalid_snapshot, &ledger, &valid)
                .expect_err("invalid snapshot")
                .constraint(),
            "snapshot"
        );

        let mut invalid_ledger = ledger.clone();
        invalid_ledger.version = 0;
        assert_eq!(
            diagnose_audit_proposal(&snapshot, &invalid_ledger, &valid)
                .expect_err("invalid ledger")
                .constraint(),
            "ledger"
        );

        let mut blocked = ledger.clone();
        blocked.entries[0].status = RequirementStatus::Blocked;
        blocked.entries[0].code_evidence.clear();
        blocked.entries[0].test_evidence.clear();
        blocked.entries[0].reason = "Source evidence is unavailable.".to_owned();
        assert_eq!(
            diagnose_audit_proposal(&snapshot, &blocked, &valid)
                .expect_err("blocked ledger")
                .constraint(),
            "blocked-ledger"
        );

        let mut wrong_version = valid.clone();
        wrong_version.version = 0;
        assert_eq!(
            diagnose_audit_proposal(&snapshot, &ledger, &wrong_version)
                .expect_err("wrong proposal version")
                .constraint(),
            "version"
        );

        let mut no_gaps = ledger.clone();
        for entry in &mut no_gaps.entries {
            entry.status = RequirementStatus::Satisfied;
            entry.reason.clear();
        }
        assert_eq!(
            diagnose_audit_proposal(&snapshot, &no_gaps, &valid)
                .expect_err("leaves without gaps")
                .constraint(),
            "unexpected-leaves"
        );

        let mut no_leaves = valid.clone();
        no_leaves.leaves.clear();
        assert_eq!(
            diagnose_audit_proposal(&snapshot, &ledger, &no_leaves)
                .expect_err("gaps without leaves")
                .constraint(),
            "missing-leaves"
        );

        let mut too_many = valid.clone();
        too_many.leaves = vec![valid.leaves[0].clone(); MAX_AUDIT_LEAVES + 1];
        assert_eq!(
            diagnose_audit_proposal(&snapshot, &ledger, &too_many)
                .expect_err("too many leaves")
                .constraint(),
            "too-many-leaves"
        );

        let mut at_capacity = valid.clone();
        at_capacity.leaves = vec![valid.leaves[0].clone(); MAX_AUDIT_LEAVES];
        assert_eq!(
            diagnose_audit_proposal(&snapshot, &ledger, &at_capacity)
                .expect_err("historical plus proposed leaf capacity")
                .constraint(),
            "leaf-capacity"
        );

        let mut stale_body = valid.clone();
        stale_body.leaves[0].body = stale_body.leaves[0]
            .body
            .replace(&snapshot.audited_sha, &"b".repeat(40));
        assert_eq!(
            diagnose_audit_proposal(&snapshot, &ledger, &stale_body)
                .expect_err("missing audited SHA")
                .constraint(),
            "leaf-audited-sha"
        );

        let mut duplicate_leaf = valid.clone();
        duplicate_leaf.leaves.push(valid.leaves[0].clone());
        assert_eq!(
            diagnose_audit_proposal(&snapshot, &ledger, &duplicate_leaf)
                .expect_err("duplicate leaf identity")
                .constraint(),
            "duplicate-leaf"
        );

        let mut unknown_gap = valid.clone();
        unknown_gap.leaves[0].gap_ids = vec!["R-999".to_owned()];
        assert_eq!(
            diagnose_audit_proposal(&snapshot, &ledger, &unknown_gap)
                .expect_err("unknown gap id")
                .constraint(),
            "unknown-gap-id"
        );

        let mut duplicate_gap = valid.clone();
        let mut second_leaf = valid.leaves[0].clone();
        second_leaf.title.push_str(" again");
        second_leaf.gap_ids = vec![valid.leaves[0].gap_ids[0].clone()];
        duplicate_gap.leaves[0].gap_ids = vec![valid.leaves[0].gap_ids[0].clone()];
        duplicate_gap.leaves.push(second_leaf);
        assert_eq!(
            diagnose_audit_proposal(&snapshot, &ledger, &duplicate_gap)
                .expect_err("duplicate gap ownership")
                .constraint(),
            "duplicate-gap-id"
        );

        let mut uncovered_gap = valid;
        let _ = uncovered_gap.leaves[0].gap_ids.pop();
        assert_eq!(
            diagnose_audit_proposal(&snapshot, &ledger, &uncovered_gap)
                .expect_err("uncovered gap")
                .constraint(),
            "uncovered-gap-id"
        );
    }

    #[test]
    fn proposal_diagnostics_cover_leaf_shape_and_dependency_rules() {
        let snapshot = snapshot();
        let ledger = ledger(&snapshot);
        let valid = gap_draft(&snapshot, &ledger);
        let valid_leaf = &valid.leaves[0];

        let mut title_shape = valid_leaf.clone();
        title_shape.title = audit_leaf_prefix(snapshot.umbrella.number);
        assert_eq!(
            diagnose_leaf_draft(&title_shape, snapshot.umbrella.number, 2)
                .expect_err("empty leaf title")
                .constraint(),
            "leaf-title-shape"
        );

        let mut body_shape = valid_leaf.clone();
        body_shape.body.clear();
        assert_eq!(
            diagnose_leaf_draft(&body_shape, snapshot.umbrella.number, 2)
                .expect_err("empty leaf body")
                .constraint(),
            "leaf-body-shape"
        );

        let mut missing_section = valid_leaf.clone();
        missing_section.body = missing_section.body.replace("## Acceptance", "## Outcome");
        assert_eq!(
            diagnose_leaf_draft(&missing_section, snapshot.umbrella.number, 2)
                .expect_err("missing required section")
                .constraint(),
            "leaf-section"
        );

        let mut empty_gaps = valid_leaf.clone();
        empty_gaps.gap_ids.clear();
        assert_eq!(
            diagnose_leaf_draft(&empty_gaps, snapshot.umbrella.number, 2)
                .expect_err("empty gap list")
                .constraint(),
            "leaf-gap-ids-empty"
        );

        let mut too_many_gaps = valid_leaf.clone();
        too_many_gaps.gap_ids = vec!["R-1".to_owned(); MAX_AUDIT_REQUIREMENTS + 1];
        assert_eq!(
            diagnose_leaf_draft(&too_many_gaps, snapshot.umbrella.number, 2)
                .expect_err("too many gap ids")
                .constraint(),
            "leaf-gap-ids-too-many"
        );

        let existing = |number| AuditDependencyNode::Existing { number };
        let valid_edge = AuditDependency {
            dependent: existing(41),
            prerequisite: existing(42),
        };
        let expected_numbers = BTreeSet::from([40, 41, 42]);
        let known_new = BTreeSet::new();

        let self_edge = AuditDependency {
            dependent: existing(41),
            prerequisite: existing(41),
        };
        assert_eq!(
            diagnose_draft_dependencies(&[self_edge], &[], &expected_numbers, &known_new)
                .expect_err("self dependency")
                .constraint(),
            "dependency-self"
        );
        assert_eq!(
            diagnose_draft_dependencies(
                &[valid_edge.clone(), valid_edge.clone()],
                &[],
                &expected_numbers,
                &known_new,
            )
            .expect_err("duplicate dependency")
            .constraint(),
            "dependency-duplicate"
        );
        assert_eq!(
            diagnose_draft_dependencies(
                std::slice::from_ref(&valid_edge),
                std::slice::from_ref(&valid_edge),
                &expected_numbers,
                &known_new,
            )
            .expect_err("conflicting removal")
            .constraint(),
            "dependency-conflict"
        );
        assert_eq!(
            diagnose_draft_dependencies(
                &[],
                &[AuditDependency {
                    dependent: existing(42),
                    prerequisite: existing(42),
                }],
                &expected_numbers,
                &known_new,
            )
            .expect_err("self removal")
            .constraint(),
            "dependency-self"
        );
        assert_eq!(
            diagnose_draft_dependencies(
                &[],
                &[valid_edge.clone(), valid_edge],
                &expected_numbers,
                &known_new,
            )
            .expect_err("duplicate removal")
            .constraint(),
            "dependency-duplicate"
        );
    }

    #[test]
    fn proposal_lifecycle_stays_resumable_and_bound_to_its_inputs() {
        let snapshot = snapshot();
        let ledger = ledger(&snapshot);
        let mut proposal = build_audit_proposal(&snapshot, &ledger, &gap_draft(&snapshot, &ledger))
            .expect("proposal");
        let identity = proposal.leaves[0].identity.clone();

        assert_eq!(
            mark_audit_leaf_in_flight(&mut proposal, "not-a-leaf"),
            Err(INVALID_AUDIT_PROPOSAL)
        );
        assert_eq!(
            record_audit_leaf_resolved(
                &mut proposal,
                &identity,
                43,
                143,
                "https://github.com/o/r/issues/43",
            ),
            Err(INVALID_AUDIT_PROPOSAL)
        );
        assert_eq!(
            mark_audit_graph_in_flight(&mut proposal),
            Err(INVALID_AUDIT_PROPOSAL)
        );

        mark_audit_leaf_in_flight(&mut proposal, &identity).expect("in flight");
        assert_eq!(
            mark_audit_leaf_in_flight(&mut proposal, &identity),
            Err(INVALID_AUDIT_PROPOSAL)
        );
        assert_eq!(
            record_audit_leaf_resolved(&mut proposal, &identity, 0, 143, "url"),
            Err(INVALID_AUDIT_PROPOSAL)
        );
        record_audit_leaf_resolved(
            &mut proposal,
            &identity,
            43,
            143,
            "https://github.com/o/r/issues/43",
        )
        .expect("resolved");
        assert_eq!(
            audit_proposal_existing_numbers(&proposal),
            BTreeSet::from([40, 41, 42, 43])
        );

        mark_audit_graph_in_flight(&mut proposal).expect("graph in flight");
        mark_audit_proposal_complete(&mut proposal).expect("complete");
        assert!(proposal.complete);
        assert_eq!(proposal.graph_state, AuditGraphState::Verified);
        assert_eq!(
            mark_audit_proposal_complete(&mut proposal),
            Err(INVALID_AUDIT_PROPOSAL)
        );

        let mut stale = proposal.clone();
        stale.repository = "different/repository".to_owned();
        assert_eq!(
            validate_audit_proposal_binding(&stale, &snapshot, &ledger),
            Err(STALE_AUDIT_PROPOSAL)
        );

        let mut invalid_fingerprints = proposal.clone();
        assert_eq!(
            replace_audit_issue_fingerprints(&mut invalid_fingerprints, Vec::new()),
            Err(INVALID_AUDIT_PROPOSAL)
        );
    }

    #[test]
    fn dependency_batches_accept_bound_nodes_and_reject_conflicts() {
        let snapshot = snapshot();
        let ledger = ledger(&snapshot);
        let mut proposal = build_audit_proposal(&snapshot, &ledger, &gap_draft(&snapshot, &ledger))
            .expect("proposal");
        let identity = proposal.leaves[0].identity.clone();
        let add = AuditDependency {
            dependent: AuditDependencyNode::Existing { number: 41 },
            prerequisite: AuditDependencyNode::New {
                identity: identity.clone(),
            },
        };
        let remove = AuditDependency {
            dependent: AuditDependencyNode::Existing { number: 42 },
            prerequisite: AuditDependencyNode::Existing { number: 41 },
        };
        proposal.dependencies = vec![add.clone()];
        proposal.remove_dependencies = vec![remove];
        assert!(render_audit_proposal(&proposal).is_ok());

        let mut duplicate_add = proposal.clone();
        duplicate_add.dependencies.push(add);
        assert_eq!(
            render_audit_proposal(&duplicate_add),
            Err(INVALID_AUDIT_PROPOSAL)
        );

        let mut conflicting_remove = proposal.clone();
        conflicting_remove.remove_dependencies = vec![AuditDependency {
            dependent: AuditDependencyNode::Existing { number: 41 },
            prerequisite: AuditDependencyNode::New { identity },
        }];
        assert_eq!(
            render_audit_proposal(&conflicting_remove),
            Err(INVALID_AUDIT_PROPOSAL)
        );

        let mut unknown_node = proposal;
        unknown_node.dependencies = vec![AuditDependency {
            dependent: AuditDependencyNode::Existing { number: 41 },
            prerequisite: AuditDependencyNode::New {
                identity: "0".repeat(64),
            },
        }];
        assert_eq!(
            render_audit_proposal(&unknown_node),
            Err(INVALID_AUDIT_PROPOSAL)
        );
    }

    #[test]
    fn bounded_identifier_helpers_only_admit_the_persisted_contract() {
        assert!(valid_repository("owner/repository-name_1"));
        assert!(!valid_repository("owner/repo/extra"));
        assert!(valid_branch("release/2026.08"));
        assert!(!valid_branch("-main"));
        assert!(valid_timestamp("2026-08-11T12:00:00.000Z"));
        assert!(valid_timestamp("2026-08-11T12:00:00+00:00"));
        assert!(!valid_timestamp("2026-08-11T12:00:00+01:00"));
        assert!(!valid_timestamp("2026-99-11T12:00:00Z"));
        assert!(!valid_timestamp("not-a-timestamp"));
        assert!(valid_source_id("leaf:41"));
        assert!(!valid_source_id("leaf:0"));
        assert!(bounded_ascii_identifier("R-1.part_2", true));
        assert!(!bounded_ascii_identifier("R 1", true));
        assert!(valid_text("one\nline", 32));
        assert!(!valid_text("", 32));
        assert!(valid_optional_text("", 32));
        assert!(valid_single_line("one line", 32));
        assert!(!valid_single_line("one\nline", 32));
        assert!(evidence_valid(&["src/lib.rs:1".to_owned()]));
        assert!(!evidence_valid(&["bad\nvalue".to_owned()]));
        assert_eq!(normalized_numbers(&[3, 1, 3, 2]), vec![1, 2, 3]);
        assert_eq!(
            normalized_strings(&["b".to_owned(), "a".to_owned(), "b".to_owned()]),
            vec!["a", "b"]
        );
    }
}
