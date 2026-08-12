//! Durable data contracts for `/audit-umbrella`.
//!
//! The audit judgment stays in the public skill, but its inputs and outputs
//! cross a trust boundary.  This module owns the bounded JSON shapes that make
//! a later mutation prove it is acting on the exact repository snapshot,
//! requirement ledger, and corrective batch the audit produced.

use crate::{
    OrderedJson,
    issue::{triage_text_is_security_sensitive, umbrella_leaf_opening_text},
};
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
/// Audit content looks security-sensitive and must not reach a public mutation.
pub const SECURITY_SENSITIVE_AUDIT: AuditUmbrellaRefusal =
    AuditUmbrellaRefusal("security-sensitive-audit");

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
/// # Errors
///
/// Returns [`INVALID_AUDIT_SNAPSHOT`], [`INVALID_AUDIT_LEDGER`], or
/// [`SECURITY_SENSITIVE_AUDIT`] when the immutable source or ledger is unsafe.
pub fn validate_audit_ledger(
    snapshot: &AuditSnapshot,
    ledger: &AuditLedger,
) -> Result<AuditLedgerSummary, AuditUmbrellaRefusal> {
    validate_snapshot(snapshot)?;
    if ledger.version != AUDIT_LEDGER_VERSION
        || ledger.snapshot_sha256 != audit_snapshot_sha256(snapshot)
        || ledger.entries.is_empty()
        || ledger.entries.len() > MAX_AUDIT_REQUIREMENTS
    {
        return Err(INVALID_AUDIT_LEDGER);
    }
    let source_items = audit_source_items(snapshot);
    let expected_source_ids = source_items
        .iter()
        .map(|item| item.id.as_str())
        .collect::<BTreeSet<_>>();
    let mut entry_ids = BTreeSet::new();
    let mut covered = BTreeSet::new();
    let mut summary = AuditLedgerSummary::default();
    for entry in &ledger.entries {
        if !valid_identifier(&entry.id)
            || !entry_ids.insert(entry.id.as_str())
            || !expected_source_ids.contains(entry.source_id.as_str())
            || !valid_single_line(&entry.requirement, 8 * 1024)
            || !evidence_valid(&entry.code_evidence)
            || !evidence_valid(&entry.test_evidence)
            || entry.reason.len() > 8 * 1024
            || entry.reason.contains('\r')
        {
            return Err(INVALID_AUDIT_LEDGER);
        }
        if triage_text_is_security_sensitive(&format!(
            "{}\n{}\n{}\n{}",
            entry.requirement,
            entry.code_evidence.join("\n"),
            entry.test_evidence.join("\n"),
            entry.reason
        )) {
            return Err(SECURITY_SENSITIVE_AUDIT);
        }
        let _ = covered.insert(entry.source_id.as_str());
        match entry.status {
            RequirementStatus::Satisfied => {
                if entry.code_evidence.is_empty()
                    || entry.test_evidence.is_empty()
                    || !entry.reason.is_empty()
                {
                    return Err(INVALID_AUDIT_LEDGER);
                }
                summary.satisfied += 1;
            }
            RequirementStatus::Gap => {
                if entry.code_evidence.is_empty() && entry.test_evidence.is_empty() {
                    return Err(INVALID_AUDIT_LEDGER);
                }
                summary.gaps += 1;
            }
            RequirementStatus::NotApplicable => {
                if !entry.code_evidence.is_empty()
                    || !entry.test_evidence.is_empty()
                    || !valid_text(&entry.reason, 8 * 1024)
                {
                    return Err(INVALID_AUDIT_LEDGER);
                }
                summary.not_applicable += 1;
            }
            RequirementStatus::Blocked => {
                if !entry.code_evidence.is_empty()
                    || !entry.test_evidence.is_empty()
                    || !valid_text(&entry.reason, 8 * 1024)
                {
                    return Err(INVALID_AUDIT_LEDGER);
                }
                summary.blocked += 1;
            }
        }
    }
    if covered.len() != expected_source_ids.len()
        || !expected_source_ids.iter().all(|id| covered.contains(id))
    {
        return Err(INVALID_AUDIT_LEDGER);
    }
    summary.total = ledger.entries.len();
    Ok(summary)
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
    let summary = validate_audit_ledger(snapshot, ledger)?;
    if summary.blocked != 0 || draft.version != AUDIT_PROPOSAL_VERSION {
        return Err(INVALID_AUDIT_PROPOSAL);
    }
    let gap_ids = ledger
        .entries
        .iter()
        .filter(|entry| entry.status == RequirementStatus::Gap)
        .map(|entry| entry.id.as_str())
        .collect::<BTreeSet<_>>();
    if (gap_ids.is_empty() && !draft.leaves.is_empty())
        || (!gap_ids.is_empty() && draft.leaves.is_empty())
        || draft.leaves.len() > MAX_AUDIT_LEAVES
        || snapshot_direct_leaf_numbers(snapshot)
            .len()
            .saturating_add(draft.leaves.len())
            > MAX_AUDIT_LEAVES
    {
        return Err(INVALID_AUDIT_PROPOSAL);
    }
    let mut leaves = Vec::with_capacity(draft.leaves.len());
    let mut observed_gap_ids = BTreeSet::new();
    let mut identities = BTreeSet::new();
    for leaf in &draft.leaves {
        validate_leaf_draft(leaf, snapshot.umbrella.number)?;
        if !leaf.body.contains(&snapshot.audited_sha) {
            return Err(INVALID_AUDIT_PROPOSAL);
        }
        let identity = audit_leaf_identity(&leaf.title, &leaf.body);
        if !identities.insert(identity.clone()) {
            return Err(INVALID_AUDIT_PROPOSAL);
        }
        for gap_id in &leaf.gap_ids {
            if !gap_ids.contains(gap_id.as_str()) || !observed_gap_ids.insert(gap_id.as_str()) {
                return Err(INVALID_AUDIT_PROPOSAL);
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
    if observed_gap_ids.len() != gap_ids.len() {
        return Err(INVALID_AUDIT_PROPOSAL);
    }
    let mut historical_leaf_numbers = snapshot.historical_leaf_numbers.clone();
    historical_leaf_numbers.sort_unstable();
    historical_leaf_numbers.dedup();
    let expected_issues = snapshot_issue_fingerprints(snapshot)?;
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
    validate_audit_proposal(&proposal, Some(&gap_ids))?;
    Ok(proposal)
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
    let prefix = audit_leaf_prefix(umbrella);
    let security_sensitive =
        triage_text_is_security_sensitive(&format!("{}\n{}", leaf.title, leaf.body));
    if !leaf.title.starts_with(&prefix)
        || leaf.title.len() > MAX_AUDIT_LEAF_TITLE_BYTES
        || !valid_single_line(&leaf.title, MAX_AUDIT_LEAF_TITLE_BYTES)
        || leaf.title[prefix.len()..].trim().is_empty()
        || !valid_text(&leaf.body, MAX_AUDIT_LEAF_BODY_BYTES)
        || leaf.body.lines().next()
            != Some(umbrella_leaf_opening_text(&umbrella.to_string()).as_str())
        || leaf.body.contains("<!-- larch:plan")
        || ![
            "## Program context",
            "## Problem",
            "## Scope",
            "## Acceptance",
        ]
        .iter()
        .all(|heading| has_nonempty_section(&leaf.body, heading))
        || !has_numbered_scope(&leaf.body)
        || leaf.gap_ids.is_empty()
        || leaf.gap_ids.len() > MAX_AUDIT_REQUIREMENTS
        || leaf.gap_ids.iter().any(|id| !valid_identifier(id))
        || normalized_strings(&leaf.gap_ids) != leaf.gap_ids
        || security_sensitive
    {
        return Err(if security_sensitive {
            SECURITY_SENSITIVE_AUDIT
        } else {
            INVALID_AUDIT_PROPOSAL
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
    let mut additions = BTreeSet::new();
    for edge in dependencies {
        if !valid_dependency_node(&edge.dependent, expected_numbers, known_new)
            || !valid_dependency_node(&edge.prerequisite, expected_numbers, known_new)
            || edge.dependent == edge.prerequisite
            || !additions.insert(edge)
        {
            return Err(INVALID_AUDIT_PROPOSAL);
        }
    }
    let mut removed = BTreeSet::new();
    for edge in removals {
        if !matches!(edge.dependent, AuditDependencyNode::Existing { .. })
            || !matches!(edge.prerequisite, AuditDependencyNode::Existing { .. })
            || !valid_dependency_node(&edge.dependent, expected_numbers, known_new)
            || !valid_dependency_node(&edge.prerequisite, expected_numbers, known_new)
            || edge.dependent == edge.prerequisite
            || additions.contains(edge)
            || !removed.insert(edge)
        {
            return Err(INVALID_AUDIT_PROPOSAL);
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
        Err(INVALID_AUDIT_PROPOSAL)
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

fn valid_identifier(value: &str) -> bool {
    !value.is_empty()
        && value.len() <= 128
        && value
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'.' | b'_' | b'-'))
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

        let mut sensitive = classified;
        sensitive.entries[0].requirement = "An RCE is present in the parser".to_owned();
        assert_eq!(
            validate_audit_ledger(&snapshot, &sensitive),
            Err(SECURITY_SENSITIVE_AUDIT)
        );
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

        let mut sensitive = valid;
        sensitive
            .body
            .push_str("\nRCE details must remain private.\n");
        assert_eq!(
            validate_leaf_draft(&sensitive, snapshot.umbrella.number),
            Err(SECURITY_SENSITIVE_AUDIT)
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
        proposal.remove_dependencies = vec![remove.clone()];
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
        assert!(valid_identifier("R-1.part_2"));
        assert!(!valid_identifier("R 1"));
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
