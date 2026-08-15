//! Effect-free migration-governance admission decisions.

use std::{
    collections::{BTreeMap, BTreeSet},
    fmt,
    sync::LazyLock,
};

use chrono::{DateTime, NaiveDateTime, Utc};
use regex::Regex;
use sha2::{Digest, Sha256};

use crate::{
    DONE_PREFIX, IMPLEMENTING_PREFIX, ImplementationLease, NamedBlockDefect, PLAN_MARKER,
    STALLED_PREFIX, balanced_fence_line_indices, parse_implementation_lease, parse_named_block,
    split_lines_keep_ends, split_text_lines, trim_python_whitespace,
};

pub const REASON_MISSING_NATIVE: &str = "missing-native-blocker-edge";
pub const REASON_UNDOCUMENTED_NATIVE: &str = "undocumented-native-blocker-edge";
pub const REASON_CLOSED_RETAINED: &str = "closed-blocker-edge-retained";
pub const REASON_BLOCKER_READ_UNAVAILABLE: &str = "blocker-read-unavailable";
pub const REASON_STALE_PLAN_BODY: &str = "stale-plan-body";
pub const REASON_STALE_PLAN_BASE_SCOPE: &str = "stale-plan-base-scope";
pub const REASON_STALE_BLOCKER_SNAPSHOT: &str = "stale-blocker-snapshot";
pub const REASON_STALE_OWNER_SNAPSHOT: &str = "stale-owner-snapshot";
pub const REASON_MISSING_OWNER_BLOCK: &str = "missing-owner-block";
pub const REASON_OWNER_SCAN_UNAVAILABLE: &str = "owner-scan-unavailable";
pub const REASON_REUSE_SOURCE_UNAVAILABLE: &str = "reuse-source-unavailable";

const OWNERS_START: &str = "<!-- larch:owners:start -->";
const OWNERS_END: &str = "<!-- larch:owners:end -->";
const LEASE_STALE_HOURS: i64 = 12;

static NATIVE_BLOCKER_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^[ \t]*Native blockers?:[ \t]+(.+?)[ \t]*$")
        .expect("native blocker expression is valid")
});
static ISSUE_REF_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"#([1-9][0-9]*)").expect("issue expression is valid"));
static RECEIPT_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(
        r"^[ \t]*<!--[ \t]+larch:plan-receipt[ \t]+v1[ \t]+plan_sha256=([0-9a-f]{64})[ \t]+base_sha=([0-9a-f]{40})[ \t]+blockers_sha256=([0-9a-f]{64})[ \t]+owners_sha256=([0-9a-f]{64})[ \t]+-->[ \t]*$",
    )
    .expect("receipt expression is valid")
});
static RECEIPT_MARKER_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^[ \t]*<!--[ \t]+larch:plan-receipt(?:[ \t]|-->|$)")
        .expect("receipt marker expression is valid")
});
static OWNER_KEY_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^[a-z0-9]+(?:-[a-z0-9]+)*$").expect("owner key expression is valid")
});
static COMMAND_PART_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^[a-z0-9]+(?:-[a-z0-9]+)*$").expect("command expression is valid")
});
static SYMBOL_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^[A-Za-z_][A-Za-z0-9_.:-]*$").expect("symbol expression is valid")
});
static SHARED_OWNER_WORD_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(
        r"^(?:launchers?|adapters?|registr(?:y|ies)|resolvers?|clients?|state(?:-machines?)?)$",
    )
    .expect("shared owner expression is valid")
});
static CREATION_WORD_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^(?:add(?:s|ed|ing)?|build(?:s|ing)?|built|creat(?:e|es|ed|ing)|defin(?:e|es|ed|ing)|establish(?:es|ed|ing)?|introduc(?:e|es|ed|ing)|new)$")
        .expect("creation expression is valid")
});
static PLAN_HEADING_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(
        r"^(?:##|###)[ \t]+(?P<kind>NEW|UPDATED|REWRITTEN|MAY_UPDATE)(?:[ \t]*:[ \t]*(?P<colon>.+?)|[ \t]+\[(?P<bracket>[^]\r\n]+)\][ \t]*:?)[ \t]*$",
    )
    .expect("plan heading expression is valid")
});

#[derive(Clone, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub struct BlockerSnapshotRow {
    pub number: u64,
    pub state: String,
    pub updated_at: String,
}
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct PlanReceipt {
    pub plan_sha256: String,
    pub base_sha: String,
    pub blockers_sha256: String,
    pub owners_sha256: String,
}
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ParityVerdict {
    pub reasons: Vec<String>,
}
impl ParityVerdict {
    #[must_use]
    pub fn blocking(&self) -> bool {
        self.reasons
            .iter()
            .any(|reason| blocking_parity_reason(reason))
    }

    #[must_use]
    pub fn report_only(&self) -> Vec<String> {
        self.reasons
            .iter()
            .filter(|reason| reason.starts_with(&format!("{REASON_CLOSED_RETAINED} ")))
            .cloned()
            .collect()
    }
}
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct FreshnessVerdict {
    pub reasons: Vec<String>,
}
impl FreshnessVerdict {
    #[must_use]
    pub const fn ok(&self) -> bool {
        self.reasons.is_empty()
    }
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum OwnerKind {
    Create,
    Reuse,
}
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct OwnerRow {
    pub kind: OwnerKind,
    pub owner_key: String,
    pub target: String,
    pub source_issue: Option<u64>,
}
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct OwnerBlock {
    pub domain: String,
    pub verb: String,
    pub owners: Vec<OwnerRow>,
}
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct OwnerBlockParse {
    pub block: Option<OwnerBlock>,
    pub defects: Vec<String>,
    pub raw_rows: Vec<String>,
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ReceiptDefect {
    InvalidFields,
    PlanBlockMalformed(NamedBlockDefect),
    PlanBlockMissing,
}
impl ReceiptDefect {
    #[must_use]
    pub const fn reason(self) -> &'static str {
        match self {
            Self::InvalidFields => "invalid-plan-receipt-fields",
            Self::PlanBlockMalformed(_) => "plan-block-malformed",
            Self::PlanBlockMissing => "plan-block-missing",
        }
    }
}
impl fmt::Display for ReceiptDefect {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(self.reason())
    }
}
impl std::error::Error for ReceiptDefect {}
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ScopeFile {
    pub path: String,
    pub object_id: String,
}
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub enum PlanScopeKind {
    New,
    Updated,
    Rewritten,
    MayUpdate,
}
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct PlanScopeDeclaration {
    pub kind: PlanScopeKind,
    pub path: String,
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ScopeFingerprintDefect {
    InvalidSha,
    ContradictoryFileIdentity,
}
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ScopeSnapshot {
    pub sha: String,
    pub files: Vec<ScopeFile>,
}
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ReceiptFreshnessRequest {
    pub body: String,
    pub blocker_rows: Vec<BlockerSnapshotRow>,
    pub base_scope: Option<ScopeSnapshot>,
    pub head_scope: Option<ScopeSnapshot>,
}
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct GovernanceIssueSnapshot {
    pub number: u64,
    pub title: String,
    pub state: String,
    pub body: String,
}
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RepositoryName(String);
impl RepositoryName {
    /// # Errors
    ///
    /// Returns [`RepositoryNameDefect`] for an invalid `owner/repository` token.
    pub fn parse(value: impl Into<String>) -> Result<Self, RepositoryNameDefect> {
        let value = value.into();
        let mut parts = value.split('/');
        let Some(owner) = parts.next() else {
            return Err(RepositoryNameDefect);
        };
        let Some(repository) = parts.next() else {
            return Err(RepositoryNameDefect);
        };
        if parts.next().is_some()
            || !valid_repository_part(owner)
            || !valid_repository_part(repository)
        {
            return Err(RepositoryNameDefect);
        }
        Ok(Self(value))
    }

    #[must_use]
    pub fn as_str(&self) -> &str {
        &self.0
    }
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct RepositoryNameDefect;
impl fmt::Display for RepositoryNameDefect {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str("invalid-repository-name")
    }
}
impl std::error::Error for RepositoryNameDefect {}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct OwnerAdmissionRequest {
    pub issue: u64,
    pub body: String,
    pub reuse_sources: Vec<GovernanceIssueSnapshot>,
    pub active_issues: Option<Vec<GovernanceIssueSnapshot>>,
    pub open_pr_branches: Option<Vec<String>>,
    pub now: DateTime<Utc>,
    pub repository: RepositoryName,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct LeaseAuditFinding {
    pub token: String,
    pub cleanup_command: String,
}

#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct OwnerAdmissionVerdict {
    pub reasons: Vec<String>,
    pub report_only: Vec<String>,
    pub cleanup_commands: Vec<String>,
}

impl OwnerAdmissionVerdict {
    #[must_use]
    pub const fn ok(&self) -> bool {
        self.reasons.is_empty()
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct GovernanceGateVerdict {
    pub parity: ParityVerdict,
    pub freshness: FreshnessVerdict,
    pub owners: OwnerAdmissionVerdict,
}

impl GovernanceGateVerdict {
    #[must_use]
    pub fn ok(&self) -> bool {
        !self.parity.blocking() && self.freshness.ok() && self.owners.ok()
    }

    #[must_use]
    pub fn blocking_reasons(&self) -> Vec<String> {
        let mut reasons: Vec<String> = self
            .parity
            .reasons
            .iter()
            .filter(|reason| blocking_parity_reason(reason))
            .cloned()
            .collect();
        reasons.extend(self.freshness.reasons.iter().cloned());
        reasons.extend(self.owners.reasons.iter().cloned());
        reasons
    }
}
#[must_use]
pub fn normalize_state(raw: &str) -> String {
    trim_python_whitespace(raw).to_ascii_lowercase()
}
#[must_use]
pub fn parse_native_blocker_refs(body: &str) -> Vec<u64> {
    let lines = split_text_lines(body);
    let fenced = balanced_fence_line_indices(&lines);
    let mut references = BTreeSet::new();
    for (index, line) in lines.iter().enumerate() {
        if fenced.contains(&index) {
            continue;
        }
        let Some(captures) = NATIVE_BLOCKER_RE.captures(line) else {
            continue;
        };
        let Some(value) = captures.get(1) else {
            continue;
        };
        for reference in ISSUE_REF_RE.captures_iter(value.as_str()) {
            if let Some(number) = reference.get(1).and_then(|item| item.as_str().parse().ok()) {
                references.insert(number);
            }
        }
    }
    references.into_iter().collect()
}
#[must_use]
pub fn hash_plan_block(plan_inner: &str) -> String {
    sha256_text(plan_inner)
}
#[must_use]
pub fn hash_blocker_rows(rows: &[BlockerSnapshotRow]) -> String {
    let mut sorted = rows.to_vec();
    sorted.sort_by_key(|row| row.number);
    let canonical = sorted
        .iter()
        .map(|row| format!("{}\t{}\t{}", row.number, row.state, row.updated_at))
        .collect::<Vec<_>>()
        .join("\n");
    sha256_text(&canonical)
}
#[must_use]
pub fn hash_owner_rows(rows: &[String]) -> String {
    let canonical =
        rows.iter()
            .collect::<BTreeSet<_>>()
            .into_iter()
            .fold(String::new(), |mut text, row| {
                if !text.is_empty() {
                    text.push('\n');
                }
                text.push_str(row);
                text
            });
    sha256_text(&canonical)
}
/// # Errors
///
/// Returns [`ReceiptDefect::InvalidFields`] for invalid receipt fields.
pub fn render_receipt(receipt: &PlanReceipt) -> Result<String, ReceiptDefect> {
    let rendered = format!(
        "<!-- larch:plan-receipt v1 plan_sha256={} base_sha={} blockers_sha256={} owners_sha256={} -->",
        receipt.plan_sha256, receipt.base_sha, receipt.blockers_sha256, receipt.owners_sha256
    );
    RECEIPT_RE
        .is_match(&rendered)
        .then_some(rendered)
        .ok_or(ReceiptDefect::InvalidFields)
}
#[must_use]
pub fn parse_receipt(body: &str) -> Option<PlanReceipt> {
    let lines = split_text_lines(body);
    let fenced = balanced_fence_line_indices(&lines);
    let mut receipts = Vec::new();
    for (index, line) in lines.iter().enumerate() {
        if fenced.contains(&index) || !RECEIPT_MARKER_RE.is_match(line) {
            continue;
        }
        receipts.push(receipt_from_line(line)?);
    }
    (receipts.len() == 1).then(|| receipts.pop()).flatten()
}
#[must_use]
pub fn receipt_marker_present(body: &str) -> bool {
    let lines = split_text_lines(body);
    let fenced = balanced_fence_line_indices(&lines);
    lines
        .iter()
        .enumerate()
        .any(|(index, line)| !fenced.contains(&index) && RECEIPT_MARKER_RE.is_match(line))
}
/// # Errors
///
/// Returns a stable [`ReceiptDefect`] when the body cannot accept the receipt.
pub fn upsert_receipt(body: &str, receipt: &PlanReceipt) -> Result<String, ReceiptDefect> {
    let rendered = render_receipt(receipt)?;
    let lines = split_lines_keep_ends(body);
    let span = crate::classify_named_block(body, PLAN_MARKER)
        .map_err(ReceiptDefect::PlanBlockMalformed)?
        .ok_or(ReceiptDefect::PlanBlockMissing)?;
    let mut output = lines[..=span.end()].concat();
    output.push_str(&rendered);
    output.push('\n');
    let mut index = span.end() + 1;
    while let Some(line) = lines.get(index) {
        let bare = line.trim_end_matches(['\r', '\n']);
        if trim_python_whitespace(bare).is_empty() {
            let mut probe = index + 1;
            while lines.get(probe).is_some_and(|candidate| {
                trim_python_whitespace(candidate.trim_end_matches(['\r', '\n'])).is_empty()
            }) {
                probe += 1;
            }
            if lines.get(probe).is_some_and(|candidate| {
                receipt_from_line(candidate.trim_end_matches(['\r', '\n'])).is_some()
            }) {
                index = probe + 1;
                continue;
            }
            break;
        }
        if receipt_from_line(bare).is_some() {
            index += 1;
            continue;
        }
        break;
    }
    output.push_str(&lines[index..].concat());
    Ok(output)
}
#[must_use]
pub fn compare_blocker_parity(
    body_rows: &[BlockerSnapshotRow],
    native_rows: &[BlockerSnapshotRow],
) -> ParityVerdict {
    let body_numbers: BTreeSet<u64> = body_rows.iter().map(|row| row.number).collect();
    let open_body: BTreeSet<u64> = body_rows
        .iter()
        .filter(|row| row.state == "open")
        .map(|row| row.number)
        .collect();
    let open_native: BTreeSet<u64> = native_rows
        .iter()
        .filter(|row| row.state == "open")
        .map(|row| row.number)
        .collect();
    let mut reasons = open_body
        .difference(&open_native)
        .map(|number| format!("{REASON_MISSING_NATIVE} issue=#{number}"))
        .collect::<Vec<_>>();
    reasons.extend(
        open_native
            .difference(&body_numbers)
            .map(|number| format!("{REASON_UNDOCUMENTED_NATIVE} issue=#{number}")),
    );
    let mut closed = native_rows
        .iter()
        .filter(|row| row.state != "open")
        .collect::<Vec<_>>();
    closed.sort_by_key(|row| row.number);
    reasons.extend(
        closed
            .into_iter()
            .map(|row| format!("{REASON_CLOSED_RETAINED} issue=#{}", row.number)),
    );
    ParityVerdict { reasons }
}
#[must_use]
pub fn parse_owner_block(body: &str) -> OwnerBlockParse {
    let lines = split_text_lines(body);
    let fenced = balanced_fence_line_indices(&lines);
    let starts = visible_exact_lines(&lines, &fenced, OWNERS_START);
    let ends = visible_exact_lines(&lines, &fenced, OWNERS_END);
    if starts.is_empty() && ends.is_empty() {
        return OwnerBlockParse {
            block: None,
            defects: Vec::new(),
            raw_rows: Vec::new(),
        };
    }
    if starts.len() != 1 || ends.len() != 1 || ends[0] <= starts[0] {
        return OwnerBlockParse {
            block: None,
            defects: vec!["malformed-owner-block".to_owned()],
            raw_rows: Vec::new(),
        };
    }
    let raw_rows: Vec<String> = lines[starts[0] + 1..ends[0]]
        .iter()
        .map(|row| (*row).to_owned())
        .collect();
    let mut defects = Vec::new();
    if raw_rows.is_empty() || raw_rows.iter().any(String::is_empty) {
        defects.push("invalid-owner-row".to_owned());
    }
    if raw_rows.iter().collect::<BTreeSet<_>>().len() != raw_rows.len() {
        defects.push("duplicate-owner-row".to_owned());
    }
    let mut sorted = raw_rows.clone();
    sorted.sort_unstable();
    if sorted != raw_rows {
        defects.push("unsorted-owner-rows".to_owned());
    }
    let (domain, verb) = parse_owner_command(&raw_rows, &mut defects);
    let owners = parse_owner_rows(&raw_rows, &mut defects);
    deduplicate(&mut defects);
    let block = defects.is_empty().then_some(OwnerBlock {
        domain,
        verb,
        owners,
    });
    OwnerBlockParse {
        block,
        defects,
        raw_rows,
    }
}
#[must_use]
pub fn owner_keys_from_rows(rows: &[String]) -> Vec<String> {
    rows.iter()
        .filter_map(|row| {
            let mut parts = row.split('\t');
            let kind = parts.next()?;
            let key = parts.next()?;
            ((kind == "CREATE" || kind == "REUSE") && OWNER_KEY_RE.is_match(key))
                .then_some(key.to_owned())
        })
        .collect::<BTreeSet<_>>()
        .into_iter()
        .collect()
}
/// Parse the fence-aware file declarations from an issue plan.
///
/// This intentionally retains unsafe paths so the effect boundary can reject
/// symlink and filesystem escapes with the same diagnostic contract.
#[must_use]
pub fn plan_scope_declarations(plan_inner: &str) -> Vec<PlanScopeDeclaration> {
    let lines = split_text_lines(plan_inner);
    let fenced = balanced_fence_line_indices(&lines);
    lines
        .iter()
        .enumerate()
        .filter(|(index, _)| !fenced.contains(index))
        .filter_map(|(_, line)| {
            let captures = PLAN_HEADING_RE.captures(line)?;
            let kind = match captures.name("kind")?.as_str() {
                "NEW" => PlanScopeKind::New,
                "UPDATED" => PlanScopeKind::Updated,
                "REWRITTEN" => PlanScopeKind::Rewritten,
                "MAY_UPDATE" => PlanScopeKind::MayUpdate,
                _ => return None,
            };
            let raw_path = captures
                .name("colon")
                .or_else(|| captures.name("bracket"))
                .map_or("", |capture| capture.as_str());
            Some(PlanScopeDeclaration {
                kind,
                path: heading_path_token(raw_path),
            })
        })
        .collect()
}
#[must_use]
pub fn declared_scope_paths(plan_inner: &str, tracked_paths: &[String]) -> Vec<String> {
    let mut paths = BTreeSet::new();
    for declaration in plan_scope_declarations(plan_inner) {
        let token = declaration.path;
        if unsafe_path(&token) {
            continue;
        }
        if has_glob(&token) {
            paths.extend(
                tracked_paths
                    .iter()
                    .filter(|candidate| scope_glob_matches(candidate, &token))
                    .cloned(),
            );
        } else {
            paths.insert(token);
        }
    }
    paths.into_iter().collect()
}
/// # Errors
///
/// Returns [`ScopeFingerprintDefect`] for invalid snapshot evidence.
pub fn compute_scope_fingerprint(
    plan_inner: &str,
    owner_keys: &[String],
    snapshot: &ScopeSnapshot,
) -> Result<String, ScopeFingerprintDefect> {
    if !sha1_hex(&snapshot.sha) {
        return Err(ScopeFingerprintDefect::InvalidSha);
    }
    let files = scope_file_map(&snapshot.files)?;
    let tracked = files.keys().cloned().collect::<Vec<_>>();
    let paths = declared_scope_paths(plan_inner, &tracked);
    let mut lines = paths
        .iter()
        .map(|path| {
            format!(
                "{path}\t{}",
                files.get(path).map_or("MISSING", String::as_str)
            )
        })
        .collect::<Vec<_>>();
    lines.extend(
        owner_keys
            .iter()
            .collect::<BTreeSet<_>>()
            .into_iter()
            .map(|key| format!("owner\t{key}")),
    );
    Ok(sha256_text(&lines.join("\n")))
}
#[must_use]
pub fn validate_receipt_freshness(request: &ReceiptFreshnessRequest) -> FreshnessVerdict {
    let Ok(Some(plan_inner)) = parse_named_block(&request.body, PLAN_MARKER) else {
        return FreshnessVerdict {
            reasons: vec![REASON_STALE_PLAN_BODY.to_owned()],
        };
    };
    let Some(receipt) = parse_receipt(&request.body) else {
        if !receipt_marker_present(&request.body) {
            return FreshnessVerdict {
                reasons: Vec::new(),
            };
        }
        return FreshnessVerdict {
            reasons: vec![REASON_STALE_PLAN_BODY.to_owned()],
        };
    };
    let owner_rows = parse_owner_block(&request.body).raw_rows;
    let mut reasons = Vec::new();
    if hash_plan_block(&plan_inner) != receipt.plan_sha256 {
        reasons.push(REASON_STALE_PLAN_BODY.to_owned());
    }
    if hash_owner_rows(&owner_rows) != receipt.owners_sha256 {
        reasons.push(REASON_STALE_OWNER_SNAPSHOT.to_owned());
    }
    if hash_blocker_rows(&request.blocker_rows) != receipt.blockers_sha256 {
        reasons.push(REASON_STALE_BLOCKER_SNAPSHOT.to_owned());
    }
    let owner_keys = owner_keys_from_rows(&owner_rows);
    let scope_fresh = request
        .base_scope
        .as_ref()
        .zip(request.head_scope.as_ref())
        .filter(|(base, _)| base.sha == receipt.base_sha)
        .and_then(|(base, head)| {
            let base = compute_scope_fingerprint(&plan_inner, &owner_keys, base).ok()?;
            let head = compute_scope_fingerprint(&plan_inner, &owner_keys, head).ok()?;
            Some(base == head)
        })
        .unwrap_or(false);
    if !scope_fresh {
        reasons.push(REASON_STALE_PLAN_BASE_SCOPE.to_owned());
    }
    FreshnessVerdict { reasons }
}
#[must_use]
pub fn migration_requires_owner_block(plan_inner: &str) -> bool {
    migration_section(plan_inner)
        .split(['.', '!', '?', ';'])
        .any(clause_creates_shared_owner)
}
#[must_use]
pub fn evaluate_owner_admission(request: &OwnerAdmissionRequest) -> OwnerAdmissionVerdict {
    let Ok(Some(plan_inner)) = parse_named_block(&request.body, PLAN_MARKER) else {
        return OwnerAdmissionVerdict::default();
    };
    let parsed = parse_owner_block(&request.body);
    let mut reasons = parsed
        .defects
        .iter()
        .map(|defect| format!("owner-block-invalid defect={defect}"))
        .collect::<Vec<_>>();
    if migration_requires_owner_block(&plan_inner) && parsed.block.is_none() {
        reasons.push(REASON_MISSING_OWNER_BLOCK.to_owned());
    }
    let Some(block) = parsed.block else {
        return OwnerAdmissionVerdict {
            reasons,
            ..OwnerAdmissionVerdict::default()
        };
    };
    reasons.extend(validate_reuse_sources(
        &block,
        &request.body,
        &request.reuse_sources,
    ));
    let Some(active_issues) = &request.active_issues else {
        reasons.push(REASON_OWNER_SCAN_UNAVAILABLE.to_owned());
        deduplicate(&mut reasons);
        return OwnerAdmissionVerdict {
            reasons,
            ..OwnerAdmissionVerdict::default()
        };
    };
    reasons.extend(active_owner_conflicts(request.issue, &block, active_issues));
    deduplicate(&mut reasons);
    let findings = request
        .open_pr_branches
        .as_ref()
        .map_or_else(Vec::new, |branches| {
            audit_stale_implementation_leases(
                &request.repository,
                active_issues,
                branches,
                request.now,
            )
        });
    OwnerAdmissionVerdict {
        reasons,
        report_only: findings
            .iter()
            .map(|finding| finding.token.clone())
            .collect(),
        cleanup_commands: findings
            .iter()
            .map(|finding| finding.cleanup_command.clone())
            .collect(),
    }
}
#[must_use]
pub fn audit_stale_implementation_leases(
    repository: &RepositoryName,
    active_issues: &[GovernanceIssueSnapshot],
    open_pr_branches: &[String],
    now: DateTime<Utc>,
) -> Vec<LeaseAuditFinding> {
    let branches = open_pr_branches.iter().cloned().collect::<BTreeSet<_>>();
    let mut issues = active_issues
        .iter()
        .filter(|issue| issue.title.starts_with(IMPLEMENTING_PREFIX))
        .collect::<Vec<_>>();
    issues.sort_by_key(|issue| issue.number);
    issues
        .into_iter()
        .filter_map(|issue| stale_lease_finding(repository, issue, &branches, now))
        .collect()
}
#[must_use]
pub const fn evaluate_governance_gate(
    parity: ParityVerdict,
    freshness: FreshnessVerdict,
    owners: OwnerAdmissionVerdict,
) -> GovernanceGateVerdict {
    GovernanceGateVerdict {
        parity,
        freshness,
        owners,
    }
}
#[must_use]
pub fn format_gate_refusal(site: &str, verdict: &GovernanceGateVerdict) -> String {
    let tokens = verdict.blocking_reasons().join(",");
    let tokens = if tokens.is_empty() {
        "unknown".to_owned()
    } else {
        tokens
    };
    format!("**❌ {site}: migration governance blocked: `{tokens}`.**")
}
fn sha256_text(text: &str) -> String {
    format!("{:x}", Sha256::digest(text.as_bytes()))
}
fn sha1_hex(value: &str) -> bool {
    value.len() == 40
        && value
            .bytes()
            .all(|byte| byte.is_ascii_hexdigit() && !byte.is_ascii_uppercase())
}

fn blocking_parity_reason(reason: &str) -> bool {
    reason == REASON_BLOCKER_READ_UNAVAILABLE
        || reason.starts_with(&format!("{REASON_MISSING_NATIVE} "))
        || reason.starts_with(&format!("{REASON_UNDOCUMENTED_NATIVE} "))
}

fn receipt_from_line(line: &str) -> Option<PlanReceipt> {
    let captures = RECEIPT_RE.captures(line)?;
    Some(PlanReceipt {
        plan_sha256: captures.get(1)?.as_str().to_owned(),
        base_sha: captures.get(2)?.as_str().to_owned(),
        blockers_sha256: captures.get(3)?.as_str().to_owned(),
        owners_sha256: captures.get(4)?.as_str().to_owned(),
    })
}

fn visible_exact_lines(lines: &[&str], fenced: &BTreeSet<usize>, expected: &str) -> Vec<usize> {
    lines
        .iter()
        .enumerate()
        .filter_map(|(index, line)| {
            (!fenced.contains(&index) && *line == expected).then_some(index)
        })
        .collect()
}

fn parse_owner_command(rows: &[String], defects: &mut Vec<String>) -> (String, String) {
    let commands = rows
        .iter()
        .filter(|row| row.starts_with("COMMAND\t"))
        .collect::<Vec<_>>();
    if commands.len() != 1 || rows.first() != commands.first().copied() {
        defects.push("invalid-owner-command".to_owned());
        return (String::new(), String::new());
    }
    let parts = commands[0].split('\t').collect::<Vec<_>>();
    if parts.len() != 3
        || !COMMAND_PART_RE.is_match(parts[1])
        || !COMMAND_PART_RE.is_match(parts[2])
    {
        defects.push("invalid-owner-command".to_owned());
        return (String::new(), String::new());
    }
    (parts[1].to_owned(), parts[2].to_owned())
}

fn parse_owner_rows(rows: &[String], defects: &mut Vec<String>) -> Vec<OwnerRow> {
    let owners = rows
        .iter()
        .filter_map(|row| parse_owner_row(row, defects))
        .collect::<Vec<_>>();
    if owners.is_empty() {
        defects.push("missing-owner-row".to_owned());
    }
    if owners
        .iter()
        .map(|owner| &owner.owner_key)
        .collect::<BTreeSet<_>>()
        .len()
        != owners.len()
    {
        defects.push("duplicate-owner-key".to_owned());
    }
    owners
}

fn parse_owner_row(row: &str, defects: &mut Vec<String>) -> Option<OwnerRow> {
    let parts = row.split('\t').collect::<Vec<_>>();
    if parts.first() == Some(&"COMMAND") {
        return None;
    }
    let parsed = match parts.as_slice() {
        ["CREATE", key, target] => Some((OwnerKind::Create, *key, *target, None)),
        ["REUSE", key, source, target]
            if source.strip_prefix('#').is_some_and(valid_positive_issue) =>
        {
            let source_issue = source
                .strip_prefix('#')
                .and_then(|number| number.parse().ok());
            Some((OwnerKind::Reuse, *key, *target, source_issue))
        }
        _ => None,
    };
    let Some((kind, owner_key, target, source_issue)) = parsed else {
        defects.push("invalid-owner-row".to_owned());
        return None;
    };
    if !OWNER_KEY_RE.is_match(owner_key) {
        defects.push("invalid-owner-key".to_owned());
    }
    if !safe_owner_target(target) {
        defects.push("unsafe-owner-target".to_owned());
    }
    Some(OwnerRow {
        kind,
        owner_key: owner_key.to_owned(),
        target: target.to_owned(),
        source_issue,
    })
}

fn safe_owner_target(value: &str) -> bool {
    if value.matches("::").count() > 1 {
        return false;
    }
    let (path, symbol) = value
        .rsplit_once("::")
        .map_or((value, None), |(path, symbol)| (path, Some(symbol)));
    if path.is_empty()
        || trim_python_whitespace(path) != path
        || path.contains('\\')
        || path.starts_with(['/', '~'])
        || path.starts_with("./")
        || path.split('/').any(|part| part == "..")
        || path
            .chars()
            .any(|character| character.is_control() || character == '\u{7f}')
    {
        return false;
    }
    symbol.is_none_or(|candidate| SYMBOL_RE.is_match(candidate))
}

fn deduplicate(values: &mut Vec<String>) {
    let mut seen = BTreeSet::new();
    values.retain(|value| seen.insert(value.clone()));
}

fn heading_path_token(raw: &str) -> String {
    let stripped = trim_python_whitespace(raw);
    if let Some(open) = stripped.find('`')
        && let Some(close) = stripped[open + 1..].find('`')
    {
        return trim_python_whitespace(&stripped[open + 1..open + 1 + close]).to_owned();
    }
    let token = stripped
        .split_whitespace()
        .next()
        .unwrap_or_default()
        .split_once('(')
        .map_or_else(
            || stripped.split_whitespace().next().unwrap_or_default(),
            |(path, _)| path,
        );
    trim_python_whitespace(token).to_owned()
}

fn unsafe_path(path: &str) -> bool {
    path.is_empty()
        || trim_python_whitespace(path) != path
        || path.starts_with(['~', '/'])
        || path.split('/').any(|part| part == "..")
}

fn has_glob(path: &str) -> bool {
    path.contains(['*', '?', '['])
}

fn scope_glob_matches(name: &str, pattern: &str) -> bool {
    crate::glob_matches(name, pattern)
}

fn scope_file_map(files: &[ScopeFile]) -> Result<BTreeMap<String, String>, ScopeFingerprintDefect> {
    let mut output = BTreeMap::new();
    for file in files {
        if output
            .insert(file.path.clone(), file.object_id.clone())
            .is_some_and(|prior| prior != file.object_id)
        {
            return Err(ScopeFingerprintDefect::ContradictoryFileIdentity);
        }
    }
    Ok(output)
}

fn migration_section(plan_inner: &str) -> String {
    let lines = split_text_lines(plan_inner);
    let fenced = balanced_fence_line_indices(&lines);
    let mut in_migration = false;
    let mut content = Vec::new();
    for (index, line) in lines.iter().enumerate() {
        if fenced.contains(&index) || fence_line(line) {
            continue;
        }
        if generic_level_two(line) {
            in_migration = trim_python_whitespace(line)
                .eq_ignore_ascii_case("## Breaking changes and migration");
            continue;
        }
        if in_migration {
            let stripped = trim_python_whitespace(line);
            if [
                "review_status:",
                "rounds_completed:",
                "difficulty:",
                "diff_added:",
                "diff_deleted:",
                "mechanical_churn:",
                "oversize_override:",
                "diff_lines:",
            ]
            .iter()
            .any(|prefix| stripped.starts_with(prefix))
                || stripped.to_ascii_lowercase().starts_with("confidence:")
            {
                break;
            }
            content.push(*line);
        }
    }
    trim_python_whitespace(&content.join("\n")).to_owned()
}

fn generic_level_two(line: &str) -> bool {
    line.strip_prefix("##")
        .is_some_and(|remaining| remaining.is_empty() || remaining.starts_with([' ', '\t']))
        && !line.starts_with("###")
}

fn fence_line(line: &str) -> bool {
    let trimmed = trim_python_whitespace(line);
    let marker = trimmed.as_bytes().first().copied();
    marker.is_some_and(|byte| {
        matches!(byte, b'`' | b'~')
            && trimmed
                .bytes()
                .take_while(|candidate| *candidate == byte)
                .count()
                >= 3
    })
}

fn clause_creates_shared_owner(clause: &str) -> bool {
    let words = clause
        .split(|character: char| !character.is_ascii_alphanumeric() && character != '-')
        .filter(|word| !word.is_empty())
        .map(str::to_ascii_lowercase)
        .collect::<Vec<_>>();
    words
        .iter()
        .enumerate()
        .any(|(index, word)| shared_owner_word(word) && owner_declaration(&words, index))
}

fn owner_declaration(words: &[String], owner_index: usize) -> bool {
    let negated = words[..owner_index]
        .iter()
        .rev()
        .take(4)
        .any(|word| matches!(word.as_str(), "no" | "not" | "never" | "neither" | "without"))
        || words[..owner_index].windows(3).rev().take(4).any(|window| {
        matches!(window, [first, second, third] if first == "no" && second == "need" && (third == "for" || third == "to"))
    });
    if negated
        || (owner_index > 0 && words[owner_index - 1] == "existing")
        || words
            .get(owner_index + 1)
            .is_some_and(|word| word == "tests" || word == "compatibility")
    {
        return false;
    }
    let creation = words[..=owner_index]
        .iter()
        .any(|word| CREATION_WORD_RE.is_match(word));
    creation
        || words
            .get(owner_index + 1..)
            .is_some_and(|tail| tail.windows(3).any(|window| matches!(window, [first, second, third] if first == "will" && second == "be" && matches!(third.as_str(), "added" | "built" | "created" | "defined" | "established" | "introduced"))))
}

fn shared_owner_word(word: &str) -> bool {
    SHARED_OWNER_WORD_RE.is_match(word)
}

fn validate_reuse_sources(
    block: &OwnerBlock,
    body: &str,
    sources: &[GovernanceIssueSnapshot],
) -> Vec<String> {
    let sources = unique_sources(sources);
    let native_refs = parse_native_blocker_refs(body)
        .into_iter()
        .collect::<BTreeSet<_>>();
    let mut reasons = Vec::new();
    for owner in &block.owners {
        if owner.kind != OwnerKind::Reuse {
            continue;
        }
        let Some(source_issue) = owner.source_issue else {
            continue;
        };
        let Some(source) = sources.get(&source_issue) else {
            reasons.push(format!(
                "{REASON_REUSE_SOURCE_UNAVAILABLE} owner={} issue=#{source_issue}",
                owner.owner_key
            ));
            continue;
        };
        reasons.extend(reuse_source_reasons(owner, source, &native_refs));
    }
    reasons
}

fn unique_sources(sources: &[GovernanceIssueSnapshot]) -> BTreeMap<u64, &GovernanceIssueSnapshot> {
    let mut counts = BTreeMap::<u64, usize>::new();
    for source in sources {
        *counts.entry(source.number).or_default() += 1;
    }
    sources
        .iter()
        .filter(|source| counts.get(&source.number) == Some(&1))
        .map(|source| (source.number, source))
        .collect()
}

fn reuse_source_reasons(
    owner: &OwnerRow,
    source: &GovernanceIssueSnapshot,
    native_refs: &BTreeSet<u64>,
) -> Vec<String> {
    let parsed = parse_owner_block(&source.body);
    let creates = parsed.block.as_ref().map_or_else(BTreeSet::new, |block| {
        block
            .owners
            .iter()
            .filter(|row| row.kind == OwnerKind::Create)
            .map(|row| row.owner_key.as_str())
            .collect()
    });
    let receipt = parse_receipt(&source.body);
    let source_has_plan = parse_named_block(&source.body, PLAN_MARKER)
        .ok()
        .flatten()
        .is_some();
    let receipt_ok = receipt
        .as_ref()
        .is_some_and(|receipt| receipt.owners_sha256 == hash_owner_rows(&parsed.raw_rows))
        || (receipt.is_none() && !receipt_marker_present(&source.body) && source_has_plan);
    let snapshot_ok = receipt_ok && creates.contains(owner.owner_key.as_str());
    let mut reasons = Vec::new();
    if !snapshot_ok {
        reasons.push(format!(
            "reuse-owner-snapshot-invalid owner={} issue=#{}",
            owner.owner_key, source.number
        ));
    }
    if normalize_state(&source.state) == "open" && !native_refs.contains(&source.number) {
        reasons.push(format!(
            "reuse-missing-native-blocker owner={} issue=#{}",
            owner.owner_key, source.number
        ));
    }
    reasons
}

fn active_owner_conflicts(
    issue: u64,
    block: &OwnerBlock,
    active_issues: &[GovernanceIssueSnapshot],
) -> Vec<String> {
    let creates = block
        .owners
        .iter()
        .filter(|owner| owner.kind == OwnerKind::Create)
        .map(|owner| owner.owner_key.as_str())
        .collect::<BTreeSet<_>>();
    let mut conflicts = BTreeSet::new();
    for active in active_issues {
        if active.number == issue || !active_or_pending(active) {
            continue;
        }
        let parsed = parse_owner_block(&active.body);
        let active_keys: BTreeSet<String> = parsed.block.as_ref().map_or_else(
            || owner_keys_from_rows(&parsed.raw_rows).into_iter().collect(),
            |owner_block| {
                owner_block
                    .owners
                    .iter()
                    .map(|owner| owner.owner_key.clone())
                    .collect()
            },
        );
        for key in &creates {
            if active_keys.contains(*key) {
                conflicts.insert(((*key).to_owned(), active.number));
            }
        }
    }
    conflicts
        .into_iter()
        .map(|(key, number)| format!("active-owner-conflict owner={key} issue=#{number}"))
        .collect()
}

fn active_or_pending(issue: &GovernanceIssueSnapshot) -> bool {
    issue.title.starts_with(IMPLEMENTING_PREFIX)
        || (parse_implementation_lease(&issue.body).is_some()
            && !issue.title.starts_with(DONE_PREFIX)
            && !issue.title.starts_with(STALLED_PREFIX))
}

fn stale_lease_finding(
    repository: &RepositoryName,
    issue: &GovernanceIssueSnapshot,
    open_pr_branches: &BTreeSet<String>,
    now: DateTime<Utc>,
) -> Option<LeaseAuditFinding> {
    let lease = parse_implementation_lease(&issue.body)?;
    (!open_pr_branches.contains(&lease.branch)).then_some(lease).and_then(|lease| {
        lease_age_hours(&lease, now).filter(|age| *age >= LEASE_STALE_HOURS).map(|age| {
            LeaseAuditFinding {
                token: format!("stale-implementation-lease issue=#{} age_hours={age}", issue.number),
                cleanup_command: format!(
                    "scripts/larch.sh tracking-issue rename --issue {} --state stalled --repo {} --run-id {}",
                    issue.number,
                    repository.as_str(),
                    lease.run_id
                ),
            }
        })
    })
}

fn lease_age_hours(lease: &ImplementationLease, now: DateTime<Utc>) -> Option<i64> {
    let parsed = NaiveDateTime::parse_from_str(&lease.updated_at, "%Y-%m-%dT%H:%M:%SZ").ok()?;
    Some((now - parsed.and_utc()).num_seconds().div_euclid(3600))
}

fn valid_repository_part(value: &str) -> bool {
    !value.is_empty()
        && value
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'.' | b'_' | b'-'))
}

fn valid_positive_issue(value: &str) -> bool {
    !value.starts_with('0')
        && value.bytes().all(|byte| byte.is_ascii_digit())
        && value.parse::<u64>().is_ok_and(|number| number > 0)
}
