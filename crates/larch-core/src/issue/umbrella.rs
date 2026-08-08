//! The durable `/umbrella` proposal record and every comparison it decides.
//!
//! `/umbrella` turns one approved decomposition into a flat set of GitHub leaf
//! issues. The skill owns the decomposition; this module owns the record that
//! survives a crash between two leaf filings, so a resumed run cannot select an
//! unrelated issue, recreate a leaf that is already in flight, or accept a
//! partition the parent never approved.
//!
//! Three properties make that possible and all three live here:
//!
//! * A leaf's identity is a hash of the exact title and body it will carry, so
//!   the record binds to content rather than to a run-local path or timestamp.
//! * The record renders as the exact bytes Python's `json.dumps` produced for
//!   the same value, so a run that started under Python and resumes under Rust
//!   — or the reverse — reads the same file.
//! * Every refusal is one stable token. The caller publishes it verbatim, so a
//!   refusal is a contract rather than a message.
//!
//! Issue titles and bodies reaching this module are untrusted (G-Sec-2): they
//! are hashed, compared, and re-rendered, never interpreted.

use crate::{
    env_file::{
        CommentPolicy, CrStrip, DuplicateInputPolicy, EmptyKeyPolicy, KeyPolicy, KvDocument,
        MalformedLinePolicy, ParseOptions, WhitespacePolicy,
    },
    issue::{
        UMBRELLA_PREFIX,
        input::{InputMode, parse_issue_input},
    },
    text::{is_positive_decimal, is_python_whitespace, split_text_lines},
};
use serde_json::Value;
use sha2::{Digest as _, Sha256};
use std::{
    collections::{BTreeMap, BTreeSet},
    fmt::Write as _,
};

/// Marker that proves a body carries a durable umbrella proposal record.
pub const UMBRELLA_PROPOSAL_TOKEN: &str = "larch:umbrella-proposal";
/// Marker that proves a body carries an implementation plan block.
const PLAN_BLOCK_TOKEN: &str = "<!-- larch:plan";
/// Title prefix reserved for a pull request the umbrella flow cannot convert.
const PULL_REQUEST_PREFIX: &str = "[PR]";
/// The two managed lifecycle titles the prepared-partition carve-out accepts.
pub const MANAGED_PARTITION_PREFIXES: [&str; 2] = ["[DESIGNING] ", "[IMPLEMENTING] "];
/// Direct leaves one umbrella may carry.
pub const MAX_UMBRELLA_LEAVES: usize = 30;
/// Direct leaves a prepared parent partition must carry at minimum.
pub const MIN_PREPARED_LEAVES: usize = 2;
/// Bytes a prepared partition batch may occupy.
pub const MAX_PREPARED_INPUT_BYTES: usize = 262_144;
/// Bytes a prepared partition edge list may occupy.
pub const MAX_PREPARED_DEPS_BYTES: usize = 16_384;
/// Tab-separated fields one prepared dependency row carries.
const PREPARED_DEP_FIELD_COUNT: usize = 2;
/// Hexadecimal characters in a SHA-256 digest.
const SHA256_HEX_LENGTH: usize = 64;
/// Version row every completion sentinel carries.
pub const COMPLETION_SENTINEL_VERSION: &str = "2";
/// Value the sentinel's proof row carries once verification has succeeded.
const GRAPH_VERIFIED_VALUE: &str = "true";

/// One stable, safe reason token for a refused umbrella operation.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct UmbrellaRefusal(&'static str);

impl UmbrellaRefusal {
    /// Return the token the caller publishes as its `REASON=` row.
    #[must_use]
    pub const fn reason(self) -> &'static str {
        self.0
    }
}

/// The record could not be read as a bounded, self-consistent proposal.
pub const INVALID_PROPOSAL_RECORD: UmbrellaRefusal = UmbrellaRefusal("invalid-proposal-record");
/// A number that must identify an issue was absent, non-decimal, or zero.
pub const INVALID_UMBRELLA_NUMBER: UmbrellaRefusal = UmbrellaRefusal("invalid-umbrella");
/// A leaf number that must identify an issue was absent, non-decimal, or zero.
pub const INVALID_LEAF_NUMBER: UmbrellaRefusal = UmbrellaRefusal("invalid-leaf");
/// A resolved leaf carried no URL.
pub const INVALID_RESOLVED_LEAF: UmbrellaRefusal = UmbrellaRefusal("invalid-resolved-leaf");
/// The record has more leaves than one umbrella may carry.
pub const LEAF_CAP_EXCEEDED: UmbrellaRefusal = UmbrellaRefusal("leaf-cap-exceeded");
/// The named identity is not in the record.
pub const UNKNOWN_LEAF_IDENTITY: UmbrellaRefusal = UmbrellaRefusal("unknown-leaf-identity");
/// The named leaf is already resolved and cannot re-enter flight.
pub const LEAF_ALREADY_RESOLVED: UmbrellaRefusal = UmbrellaRefusal("leaf-already-resolved");
/// Recovery found no single remote issue carrying the exact leaf contract.
pub const AMBIGUOUS_IN_FLIGHT_RECOVERY: UmbrellaRefusal =
    UmbrellaRefusal("ambiguous-in-flight-recovery");
/// The parent partition is not one bounded, generic, well-formed batch.
pub const INVALID_PREPARED_PARTITION: UmbrellaRefusal =
    UmbrellaRefusal("invalid-prepared-partition");
/// The parent partition or its edge list is larger than the bound.
pub const PREPARED_PARTITION_TOO_LARGE: UmbrellaRefusal =
    UmbrellaRefusal("prepared-partition-too-large");
/// A prepared edge row is not two distinct in-range one-based indices.
pub const INVALID_PREPARED_DEPENDENCIES: UmbrellaRefusal =
    UmbrellaRefusal("invalid-prepared-dependencies");
/// The prepared edges describe a cycle.
pub const PREPARED_DEPENDENCY_CYCLE: UmbrellaRefusal = UmbrellaRefusal("prepared-dependency-cycle");
/// The source issue is closed.
pub const CLOSED_INPUT: UmbrellaRefusal = UmbrellaRefusal("closed-input");
/// The source issue is a pull request or already carries a plan block.
pub const INCOMPATIBLE_INPUT: UmbrellaRefusal = UmbrellaRefusal("incompatible-input");
/// The source is an `[UMBRELLA]` without a durable proposal record.
pub const INCOMPATIBLE_UMBRELLA: UmbrellaRefusal = UmbrellaRefusal("incompatible-umbrella");
/// The prepared-partition carve-out was requested for an ineligible source.
pub const INCOMPATIBLE_MANAGED_PARTITION: UmbrellaRefusal =
    UmbrellaRefusal("incompatible-managed-partition");
/// The final title or body does not carry the umbrella contract.
pub const INVALID_FINAL_UMBRELLA: UmbrellaRefusal = UmbrellaRefusal("invalid-final-umbrella");
/// A recorded leaf is unresolved, off-contract, or drifted from its issue.
pub const INCOMPLETE_GRAPH_STATE: UmbrellaRefusal = UmbrellaRefusal("incomplete-graph-state");
/// The live prepared artifacts no longer prove the persisted record.
pub const STALE_PREPARED_PARTITION: UmbrellaRefusal = UmbrellaRefusal("stale-prepared-partition");
/// The sentinel is not the exact seven `KEY=value` rows a proof carries.
pub const INVALID_COMPLETION_SENTINEL: UmbrellaRefusal =
    UmbrellaRefusal("invalid-completion-sentinel");
/// The sentinel's rows disagree with the live artifacts it claims to prove.
pub const STALE_COMPLETION_SENTINEL: UmbrellaRefusal = UmbrellaRefusal("stale-completion-sentinel");

/// The bounded fields one umbrella source issue contributes.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct UmbrellaSnapshot {
    pub repository: String,
    pub number: String,
    pub title: String,
    pub body: String,
    pub state: String,
    pub updated_at: String,
}

/// Where one recorded leaf stands between proposal and native graph wiring.
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub enum LeafState {
    /// Approved but not yet handed to `/issue`.
    #[default]
    Pending,
    /// Handed to `/issue`; the remote outcome is not yet recorded.
    InFlight,
    /// Bound to one exact remote issue.
    Resolved,
}

impl LeafState {
    /// Render the token the record carries.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Pending => "pending",
            Self::InFlight => "in-flight",
            Self::Resolved => "resolved",
        }
    }

    fn parse(value: &str) -> Option<Self> {
        match value {
            "pending" => Some(Self::Pending),
            "in-flight" => Some(Self::InFlight),
            "resolved" => Some(Self::Resolved),
            _ => None,
        }
    }
}

/// One recorded leaf, bound to the exact title and body it will carry.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct ExpectedLeaf {
    pub identity: String,
    pub title: String,
    pub body: String,
    pub state: LeafState,
    pub number: String,
    pub url: String,
    pub issue_id: String,
}

/// One recorded edge, expressed between leaf identities.
#[derive(Clone, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub struct DependencyEdge {
    pub blocker: String,
    pub blocked: String,
}

/// The durable record one `/umbrella` run resumes from.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct ProposalRecord {
    pub umbrella: String,
    pub repository: String,
    pub expected_updated_at: String,
    pub common_context: String,
    pub leaves: Vec<ExpectedLeaf>,
    pub dependency_edges: Vec<DependencyEdge>,
    pub prepared_input_sha256: String,
    pub prepared_deps_sha256: String,
}

/// One leaf bound to the remote issue that now carries it.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ResolvedLeaf {
    pub identity: String,
    pub number: String,
    pub url: String,
    pub issue_id: String,
}

/// One remote issue offered as an in-flight recovery match.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct CandidateIssue {
    pub number: Option<u64>,
    pub url: String,
    pub title: String,
    pub body: String,
    pub issue_id: String,
}

/// One live GitHub issue the recorded graph is verified against.
///
/// A field the remote row could not supply as text arrives empty. Every
/// recorded leaf reaching verification already carries the fixed leaf title and
/// opening, so an empty field can only fail to match, never match by accident.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct RemoteLeaf {
    pub number: String,
    pub title: String,
    pub body: String,
}

/// The seven rows one completion sentinel publishes, in the order it writes.
///
/// The parent that approved a partition reads this file to prove the child
/// consumed exactly that partition and nothing else, so every row is compared
/// rather than inspected: an unexpected value is staleness, not a message.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct CompletionSentinel {
    pub version: String,
    pub repository: String,
    pub umbrella: String,
    pub prepared_input_sha256: String,
    pub prepared_deps_sha256: String,
    pub prepared_graph_sha256: String,
    pub graph_verified: String,
}

impl CompletionSentinel {
    /// The one decoding policy a completion proof is read under.
    const PARSE_OPTIONS: ParseOptions = ParseOptions {
        malformed_lines: MalformedLinePolicy::Reject,
        key_policy: Some(KeyPolicy::Wire),
        empty_keys: EmptyKeyPolicy::Keep,
        comments: CommentPolicy::Keep,
        key_whitespace: WhitespacePolicy::Preserve,
        value_whitespace: WhitespacePolicy::Preserve,
        cr_strip: CrStrip::None,
        duplicates: DuplicateInputPolicy::Reject,
    };

    /// Render the sentinel as the exact bytes an atomic publish writes.
    #[must_use]
    pub fn render(&self) -> String {
        let mut text = String::new();
        for (key, value) in self.rows() {
            let _ = writeln!(text, "{key}={value}");
        }
        text
    }

    /// Read one sentinel from its stored text.
    ///
    /// The proof is decoded through the shared `KEY=value` codec under the one
    /// policy this file allows: every record must be a well-formed pair, no key
    /// may repeat, and no carriage return or blank record may stand where a row
    /// belongs. Anything else is not a weaker proof, it is not a proof.
    ///
    /// # Errors
    /// Returns [`INVALID_COMPLETION_SENTINEL`] for a record that is not one
    /// `KEY=value` pair, a repeated key, or any key set but the exact seven.
    pub fn parse(text: &str) -> Result<Self, UmbrellaRefusal> {
        if text.contains('\r') || split_text_lines(text).iter().any(|line| line.is_empty()) {
            return Err(INVALID_COMPLETION_SENTINEL);
        }
        let document = KvDocument::parse(text, Self::PARSE_OPTIONS)
            .map_err(|_| INVALID_COMPLETION_SENTINEL)?;
        let mut rows: BTreeMap<&str, &str> = BTreeMap::new();
        for row in document.rows() {
            let _ = rows.insert(row.key(), row.value());
        }
        let mut parsed = Self {
            version: String::new(),
            repository: String::new(),
            umbrella: String::new(),
            prepared_input_sha256: String::new(),
            prepared_deps_sha256: String::new(),
            prepared_graph_sha256: String::new(),
            graph_verified: String::new(),
        };
        for (key, slot) in [
            ("UMBRELLA_SENTINEL_VERSION", &mut parsed.version),
            ("REPOSITORY", &mut parsed.repository),
            ("UMBRELLA_NUMBER", &mut parsed.umbrella),
            ("PREPARED_INPUT_SHA256", &mut parsed.prepared_input_sha256),
            ("PREPARED_DEPS_SHA256", &mut parsed.prepared_deps_sha256),
            ("PREPARED_GRAPH_SHA256", &mut parsed.prepared_graph_sha256),
            ("GRAPH_VERIFIED", &mut parsed.graph_verified),
        ] {
            let value = rows.remove(key).ok_or(INVALID_COMPLETION_SENTINEL)?;
            slot.push_str(value);
        }
        if rows.is_empty() {
            Ok(parsed)
        } else {
            Err(INVALID_COMPLETION_SENTINEL)
        }
    }

    /// Return the rows in publication order, keyed by their contract names.
    const fn rows(&self) -> [(&'static str, &str); 7] {
        [
            ("UMBRELLA_SENTINEL_VERSION", self.version.as_str()),
            ("REPOSITORY", self.repository.as_str()),
            ("UMBRELLA_NUMBER", self.umbrella.as_str()),
            ("PREPARED_INPUT_SHA256", self.prepared_input_sha256.as_str()),
            ("PREPARED_DEPS_SHA256", self.prepared_deps_sha256.as_str()),
            ("PREPARED_GRAPH_SHA256", self.prepared_graph_sha256.as_str()),
            ("GRAPH_VERIFIED", self.graph_verified.as_str()),
        ]
    }
}

/// Return the exact first body line every direct leaf of `umbrella` carries.
#[must_use]
pub fn umbrella_leaf_opening_text(umbrella: &str) -> String {
    format!("This is a leaf of umbrella #{umbrella}. Read the umbrella in full before acting.")
}

/// Return a stable identity that excludes run-local paths and timestamps.
#[must_use]
pub fn leaf_identity(title: &str, body: &str) -> String {
    let mut digest = Sha256::new();
    digest.update(title.trim_matches(is_python_whitespace).as_bytes());
    digest.update(b"\n");
    digest.update(body.as_bytes());
    hex(&digest.finalize())
}

fn text_sha256(text: &str) -> String {
    hex(&Sha256::digest(text.as_bytes()))
}

fn hex(bytes: &[u8]) -> String {
    let mut rendered = String::with_capacity(bytes.len() * 2);
    for byte in bytes {
        write!(rendered, "{byte:02x}").expect("writing to a String cannot fail");
    }
    rendered
}

fn is_sha256_hex(value: &str) -> bool {
    value.len() == SHA256_HEX_LENGTH
        && value
            .bytes()
            .all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte))
}

/// Report whether `title` names one of the two managed lifecycle partitions.
#[must_use]
pub fn is_managed_partition_title(title: &str) -> bool {
    MANAGED_PARTITION_PREFIXES
        .iter()
        .any(|prefix| title.starts_with(prefix))
}

/// Decide whether one source issue may become or resume an umbrella.
///
/// The prepared-partition path is the sole protected-title carve-out: an exact
/// `[DESIGNING]` or `[IMPLEMENTING]` source is accepted only with
/// `managed_partition`, and only that path may carry an existing plan block.
///
/// # Errors
/// Returns the refusal token for a closed, pull-request, plan-bearing, or
/// record-less umbrella source.
pub fn classify_umbrella_source(
    title: &str,
    body: &str,
    state: &str,
    managed_partition: bool,
) -> Result<(), UmbrellaRefusal> {
    if !state.eq_ignore_ascii_case("open") {
        return Err(CLOSED_INPUT);
    }
    let umbrella_tag = UMBRELLA_PREFIX.trim_end();
    let compatible_umbrella =
        title.starts_with(umbrella_tag) && body.contains(UMBRELLA_PROPOSAL_TOKEN);
    if managed_partition && !is_managed_partition_title(title) && !compatible_umbrella {
        return Err(INCOMPATIBLE_MANAGED_PARTITION);
    }
    if title.starts_with(PULL_REQUEST_PREFIX)
        || (body.contains(PLAN_BLOCK_TOKEN) && !managed_partition && !compatible_umbrella)
    {
        return Err(INCOMPATIBLE_INPUT);
    }
    if title.starts_with(umbrella_tag) && !body.contains(UMBRELLA_PROPOSAL_TOKEN) {
        return Err(INCOMPATIBLE_UMBRELLA);
    }
    Ok(())
}

/// Report whether one recorded leaf still carries the fixed umbrella contract.
fn leaf_keeps_contract(leaf: &ExpectedLeaf, umbrella: &str) -> bool {
    leaf.title.starts_with(&format!("[LEAF OF {umbrella}]"))
        && leaf.body.starts_with(&umbrella_leaf_opening_text(umbrella))
}

fn string_field(
    row: &serde_json::Map<String, Value>,
    key: &str,
) -> Result<String, UmbrellaRefusal> {
    match row.get(key) {
        Some(Value::String(value)) => Ok(value.clone()),
        _ => Err(INVALID_PROPOSAL_RECORD),
    }
}

fn optional_string_field(
    row: &serde_json::Map<String, Value>,
    key: &str,
    default: &str,
) -> Result<String, UmbrellaRefusal> {
    match row.get(key) {
        None => Ok(default.to_owned()),
        Some(Value::String(value)) => Ok(value.clone()),
        Some(_) => Err(INVALID_PROPOSAL_RECORD),
    }
}

fn expected_leaf(value: &Value) -> Result<ExpectedLeaf, UmbrellaRefusal> {
    let row = value.as_object().ok_or(INVALID_PROPOSAL_RECORD)?;
    let identity = string_field(row, "identity")?;
    let title = string_field(row, "title")?;
    let body = string_field(row, "body")?;
    let state = optional_string_field(row, "state", "pending")?;
    let number = optional_string_field(row, "number", "")?;
    let url = optional_string_field(row, "url", "")?;
    let issue_id = optional_string_field(row, "issue_id", "")?;
    let state = LeafState::parse(&state).ok_or(INVALID_PROPOSAL_RECORD)?;
    if leaf_identity(&title, &body) != identity {
        return Err(INVALID_PROPOSAL_RECORD);
    }
    if state == LeafState::Resolved
        && (number.is_empty()
            || !number.bytes().all(|byte| byte.is_ascii_digit())
            || url.is_empty())
    {
        return Err(INVALID_PROPOSAL_RECORD);
    }
    Ok(ExpectedLeaf {
        identity,
        title,
        body,
        state,
        number,
        url,
        issue_id,
    })
}

/// Read one durable proposal record from its JSON text.
///
/// The record is self-proving: every leaf identity is recomputed from the exact
/// title and body it names, duplicate identities are refused, and the edge set
/// must reference only recorded leaves and describe no cycle. The repository
/// slug is validated by the caller, which owns the slug grammar.
///
/// # Errors
/// Returns [`INVALID_PROPOSAL_RECORD`] for any malformed or self-inconsistent
/// record and [`INVALID_UMBRELLA_NUMBER`] for a non-positive umbrella number.
pub fn parse_proposal(text: &str) -> Result<ProposalRecord, UmbrellaRefusal> {
    let value: Value = serde_json::from_str(text).map_err(|_| INVALID_PROPOSAL_RECORD)?;
    let row = value.as_object().ok_or(INVALID_PROPOSAL_RECORD)?;
    let umbrella = string_field(row, "umbrella")?;
    let repository = string_field(row, "repository")?;
    let expected_updated_at = string_field(row, "expected_updated_at")?;
    let common_context = string_field(row, "common_context")?;
    let leaves_value = row.get("leaves").ok_or(INVALID_PROPOSAL_RECORD)?;
    let rows = leaves_value.as_array().ok_or(INVALID_PROPOSAL_RECORD)?;
    if rows.is_empty() || rows.len() > MAX_UMBRELLA_LEAVES {
        return Err(INVALID_PROPOSAL_RECORD);
    }
    let leaves = rows
        .iter()
        .map(expected_leaf)
        .collect::<Result<Vec<ExpectedLeaf>, UmbrellaRefusal>>()?;
    let identities: BTreeSet<&str> = leaves.iter().map(|leaf| leaf.identity.as_str()).collect();
    if identities.len() != leaves.len() {
        return Err(INVALID_PROPOSAL_RECORD);
    }
    let mut edges = Vec::new();
    let edge_rows: &[Value] = match row.get("dependency_edges") {
        None => &[],
        Some(Value::Array(items)) => items,
        Some(_) => return Err(INVALID_PROPOSAL_RECORD),
    };
    for item in edge_rows {
        let edge = item.as_object().ok_or(INVALID_PROPOSAL_RECORD)?;
        let upstream = string_field(edge, "blocker")?;
        let downstream = string_field(edge, "blocked")?;
        if upstream == downstream
            || !identities.contains(upstream.as_str())
            || !identities.contains(downstream.as_str())
        {
            return Err(INVALID_PROPOSAL_RECORD);
        }
        edges.push(DependencyEdge {
            blocker: upstream,
            blocked: downstream,
        });
    }
    validate_dependency_graph(&leaves, &edges, INVALID_PROPOSAL_RECORD)?;
    let prepared_input_sha256 = optional_string_field(row, "prepared_input_sha256", "")?;
    let prepared_deps_sha256 = optional_string_field(row, "prepared_deps_sha256", "")?;
    if prepared_input_sha256.is_empty() != prepared_deps_sha256.is_empty()
        || (!prepared_input_sha256.is_empty()
            && (!is_sha256_hex(&prepared_input_sha256) || !is_sha256_hex(&prepared_deps_sha256)))
    {
        return Err(INVALID_PROPOSAL_RECORD);
    }
    if !is_positive_decimal(&umbrella) {
        return Err(INVALID_UMBRELLA_NUMBER);
    }
    Ok(ProposalRecord {
        umbrella,
        repository,
        expected_updated_at,
        common_context,
        leaves,
        dependency_edges: edges,
        prepared_input_sha256,
        prepared_deps_sha256,
    })
}

/// Refuse a duplicated, self-referential, dangling, or cyclic edge set.
fn validate_dependency_graph(
    leaves: &[ExpectedLeaf],
    edges: &[DependencyEdge],
    reason: UmbrellaRefusal,
) -> Result<(), UmbrellaRefusal> {
    let identities: BTreeSet<&str> = leaves.iter().map(|leaf| leaf.identity.as_str()).collect();
    let unique: BTreeSet<&DependencyEdge> = edges.iter().collect();
    if unique.len() != edges.len()
        || edges.iter().any(|edge| {
            edge.blocker == edge.blocked
                || !identities.contains(edge.blocker.as_str())
                || !identities.contains(edge.blocked.as_str())
        })
    {
        return Err(reason);
    }
    let mut blocked_by: BTreeMap<&str, usize> =
        identities.iter().map(|identity| (*identity, 0)).collect();
    let mut unblocks: BTreeMap<&str, Vec<&str>> = BTreeMap::new();
    for edge in edges {
        *blocked_by.get_mut(edge.blocked.as_str()).ok_or(reason)? += 1;
        unblocks
            .entry(edge.blocker.as_str())
            .or_default()
            .push(edge.blocked.as_str());
    }
    let mut ready: Vec<&str> = blocked_by
        .iter()
        .filter(|(_, count)| **count == 0)
        .map(|(identity, _)| *identity)
        .collect();
    let mut ordered = 0_usize;
    while let Some(identity) = ready.pop() {
        ordered += 1;
        for next in unblocks
            .get(identity)
            .map(Vec::as_slice)
            .unwrap_or_default()
        {
            let count = blocked_by.get_mut(*next).ok_or(reason)?;
            *count -= 1;
            if *count == 0 {
                ready.push(next);
            }
        }
    }
    if ordered == identities.len() {
        Ok(())
    } else {
        Err(reason)
    }
}

/// Render one record as the exact bytes Python's `json.dumps` produced.
///
/// Keys are sorted, separators are compact, and every non-ASCII scalar and
/// every character Python escaped is escaped the same way, so a record written
/// by either runtime reads identically in the other.
#[must_use]
pub fn render_proposal(record: &ProposalRecord) -> String {
    let mut text = String::new();
    text.push('{');
    push_pair(&mut text, "common_context", &record.common_context, true);
    text.push_str(",\"dependency_edges\":[");
    for (index, edge) in record.dependency_edges.iter().enumerate() {
        if index > 0 {
            text.push(',');
        }
        text.push('{');
        push_pair(&mut text, "blocked", &edge.blocked, true);
        text.push(',');
        push_pair(&mut text, "blocker", &edge.blocker, true);
        text.push('}');
    }
    text.push_str("],");
    push_pair(
        &mut text,
        "expected_updated_at",
        &record.expected_updated_at,
        true,
    );
    text.push_str(",\"leaves\":[");
    for (index, leaf) in record.leaves.iter().enumerate() {
        if index > 0 {
            text.push(',');
        }
        text.push('{');
        push_pair(&mut text, "body", &leaf.body, true);
        text.push(',');
        push_pair(&mut text, "identity", &leaf.identity, true);
        text.push(',');
        push_pair(&mut text, "issue_id", &leaf.issue_id, true);
        text.push(',');
        push_pair(&mut text, "number", &leaf.number, true);
        text.push(',');
        push_pair(&mut text, "state", leaf.state.as_str(), true);
        text.push(',');
        push_pair(&mut text, "title", &leaf.title, true);
        text.push(',');
        push_pair(&mut text, "url", &leaf.url, true);
        text.push('}');
    }
    text.push_str("],");
    push_pair(
        &mut text,
        "prepared_deps_sha256",
        &record.prepared_deps_sha256,
        true,
    );
    text.push(',');
    push_pair(
        &mut text,
        "prepared_input_sha256",
        &record.prepared_input_sha256,
        true,
    );
    text.push(',');
    push_pair(&mut text, "repository", &record.repository, true);
    text.push(',');
    push_pair(&mut text, "umbrella", &record.umbrella, true);
    text.push_str(",\"version\":1}\n");
    text
}

/// Render one source snapshot the way `json.dumps(..., sort_keys=True)` did.
///
/// The snapshot handoff kept Python's default separators, so this renderer does
/// too; only the record above is compact.
#[must_use]
pub fn render_snapshot(snapshot: &UmbrellaSnapshot) -> String {
    let mut text = String::new();
    text.push('{');
    for (index, (key, value)) in [
        ("body", &snapshot.body),
        ("number", &snapshot.number),
        ("repository", &snapshot.repository),
        ("state", &snapshot.state),
        ("title", &snapshot.title),
        ("updated_at", &snapshot.updated_at),
    ]
    .into_iter()
    .enumerate()
    {
        if index > 0 {
            text.push_str(", ");
        }
        push_pair(&mut text, key, value, false);
    }
    text.push_str("}\n");
    text
}

fn push_pair(text: &mut String, key: &str, value: &str, compact: bool) {
    push_json_string(text, key);
    text.push(':');
    if !compact {
        text.push(' ');
    }
    push_json_string(text, value);
}

/// Escape one string the way Python's `json.dumps` with `ensure_ascii` did.
fn push_json_string(text: &mut String, value: &str) {
    text.push('"');
    for character in value.chars() {
        match character {
            '"' => text.push_str("\\\""),
            '\\' => text.push_str("\\\\"),
            '\n' => text.push_str("\\n"),
            '\r' => text.push_str("\\r"),
            '\t' => text.push_str("\\t"),
            '\u{8}' => text.push_str("\\b"),
            '\u{c}' => text.push_str("\\f"),
            ' '..='~' => text.push(character),
            other => {
                let mut units = [0; 2];
                for unit in other.encode_utf16(&mut units) {
                    write!(text, "\\u{unit:04x}").expect("writing to a String cannot fail");
                }
            }
        }
    }
    text.push('"');
}

/// Read the parent-approved edge list as identity edges over `leaves`.
fn prepared_edges(
    deps_text: &str,
    leaves: &[ExpectedLeaf],
) -> Result<Vec<DependencyEdge>, UmbrellaRefusal> {
    if deps_text.contains('\r') {
        return Err(INVALID_PREPARED_DEPENDENCIES);
    }
    let mut edges = Vec::new();
    let mut seen = BTreeSet::new();
    for line in split_text_lines(deps_text) {
        if line.is_empty() {
            return Err(INVALID_PREPARED_DEPENDENCIES);
        }
        let parts: Vec<&str> = line.split('\t').collect();
        if parts.len() != PREPARED_DEP_FIELD_COUNT {
            return Err(INVALID_PREPARED_DEPENDENCIES);
        }
        let mut indices = [0_usize; PREPARED_DEP_FIELD_COUNT];
        for (slot, part) in indices.iter_mut().zip(parts) {
            *slot = parse_dependency_index(part, leaves.len())?;
        }
        let [upstream, downstream] = indices;
        if upstream == downstream || !seen.insert((upstream, downstream)) {
            return Err(INVALID_PREPARED_DEPENDENCIES);
        }
        edges.push(DependencyEdge {
            blocker: leaves[upstream - 1].identity.clone(),
            blocked: leaves[downstream - 1].identity.clone(),
        });
    }
    validate_dependency_graph(leaves, &edges, PREPARED_DEPENDENCY_CYCLE)?;
    Ok(edges)
}

fn parse_dependency_index(part: &str, leaves: usize) -> Result<usize, UmbrellaRefusal> {
    if part.is_empty() || !part.bytes().all(|byte| byte.is_ascii_digit()) {
        return Err(INVALID_PREPARED_DEPENDENCIES);
    }
    let index: usize = part.parse().map_err(|_| INVALID_PREPARED_DEPENDENCIES)?;
    if index < 1 || index > leaves {
        return Err(INVALID_PREPARED_DEPENDENCIES);
    }
    Ok(index)
}

/// Convert one validated parent partition into exact umbrella leaf records.
///
/// The returned batch is the exact text `/issue` will read, and it is proven by
/// re-parsing it: a title or body that would not survive the round trip refuses
/// here rather than filing a leaf whose remote content differs from the record.
///
/// # Errors
/// Returns the bound, grammar, duplicate, edge, or cycle refusal token.
pub fn prepare_proposal_from_batch(
    snapshot: &UmbrellaSnapshot,
    input_text: &str,
    deps_text: &str,
) -> Result<(ProposalRecord, String), UmbrellaRefusal> {
    if input_text.len() > MAX_PREPARED_INPUT_BYTES || deps_text.len() > MAX_PREPARED_DEPS_BYTES {
        return Err(PREPARED_PARTITION_TOO_LARGE);
    }
    let parsed = parse_issue_input(input_text);
    if parsed.mode != InputMode::Generic
        || parsed.items.len() < MIN_PREPARED_LEAVES
        || parsed.items.len() > MAX_UMBRELLA_LEAVES
        || parsed.items.iter().any(|item| {
            item.malformed
                || item.title.trim_matches(is_python_whitespace).is_empty()
                || item.body.trim_matches(is_python_whitespace).is_empty()
                || item
                    .title
                    .trim_start_matches(is_python_whitespace)
                    .to_lowercase()
                    .starts_with("[leaf of ")
        })
    {
        return Err(INVALID_PREPARED_PARTITION);
    }
    let opening = umbrella_leaf_opening_text(&snapshot.number);
    let mut leaves = Vec::with_capacity(parsed.items.len());
    let mut batch_parts = Vec::with_capacity(parsed.items.len());
    for item in &parsed.items {
        let base_title = item.title.trim_matches(is_python_whitespace);
        let leaf_title = format!("[LEAF OF {}] {base_title}", snapshot.number);
        let leaf_body = format!(
            "{opening}\n\n{}",
            item.body.trim_matches(is_python_whitespace)
        );
        batch_parts.push(format!("### {base_title}\n\n{leaf_body}"));
        leaves.push(ExpectedLeaf {
            identity: leaf_identity(&leaf_title, &leaf_body),
            title: leaf_title,
            body: leaf_body,
            ..ExpectedLeaf::default()
        });
    }
    let identities: BTreeSet<&str> = leaves.iter().map(|leaf| leaf.identity.as_str()).collect();
    if identities.len() != leaves.len() {
        return Err(INVALID_PREPARED_PARTITION);
    }
    let record = ProposalRecord {
        umbrella: snapshot.number.clone(),
        repository: snapshot.repository.clone(),
        expected_updated_at: snapshot.updated_at.clone(),
        common_context: snapshot.body.clone(),
        dependency_edges: prepared_edges(deps_text, &leaves)?,
        prepared_input_sha256: text_sha256(input_text),
        prepared_deps_sha256: text_sha256(deps_text),
        leaves,
    };
    let issue_input = format!("{}\n", batch_parts.join("\n"));
    let round_trip = parse_issue_input(&issue_input);
    let prefix = format!("[LEAF OF {}] ", snapshot.number);
    if round_trip.mode != InputMode::Generic
        || round_trip.items.len() != record.leaves.len()
        || round_trip
            .items
            .iter()
            .zip(&record.leaves)
            .any(|(item, leaf)| {
                item.title.trim_matches(is_python_whitespace)
                    != leaf.title.strip_prefix(&prefix).unwrap_or(&leaf.title)
                    || item.body != leaf.body
            })
    {
        return Err(INVALID_PREPARED_PARTITION);
    }
    Ok((record, issue_input))
}

/// Return the record with one named leaf moved into flight.
///
/// # Errors
/// Returns [`UNKNOWN_LEAF_IDENTITY`] for an absent identity and
/// [`LEAF_ALREADY_RESOLVED`] for a leaf that is already bound to an issue.
pub fn mark_leaf_in_flight(
    record: &ProposalRecord,
    identity: &str,
) -> Result<ProposalRecord, UmbrellaRefusal> {
    let mut updated = record.clone();
    let leaf = updated
        .leaves
        .iter_mut()
        .find(|leaf| leaf.identity == identity)
        .ok_or(UNKNOWN_LEAF_IDENTITY)?;
    if leaf.state == LeafState::Resolved {
        return Err(LEAF_ALREADY_RESOLVED);
    }
    leaf.state = LeafState::InFlight;
    Ok(updated)
}

/// Return the record with one named leaf bound to its remote issue.
///
/// # Errors
/// Returns [`INVALID_LEAF_NUMBER`] or [`INVALID_RESOLVED_LEAF`] for an
/// unusable binding and [`UNKNOWN_LEAF_IDENTITY`] for an absent identity.
pub fn record_leaf_resolved(
    record: &ProposalRecord,
    resolved: &ResolvedLeaf,
) -> Result<ProposalRecord, UmbrellaRefusal> {
    if !is_positive_decimal(&resolved.number) {
        return Err(INVALID_LEAF_NUMBER);
    }
    if resolved.url.is_empty() {
        return Err(INVALID_RESOLVED_LEAF);
    }
    let mut updated = record.clone();
    let leaf = updated
        .leaves
        .iter_mut()
        .find(|leaf| leaf.identity == resolved.identity)
        .ok_or(UNKNOWN_LEAF_IDENTITY)?;
    leaf.state = LeafState::Resolved;
    leaf.number.clone_from(&resolved.number);
    leaf.url.clone_from(&resolved.url);
    leaf.issue_id.clone_from(&resolved.issue_id);
    Ok(updated)
}

/// Resolve exactly one remote issue matching the immutable in-flight contract.
///
/// Recovery is deliberately all-or-nothing: a leaf that is not in flight, has
/// lost its title or opening contract, or matches zero or several remote issues
/// refuses rather than binding the record to a plausible neighbour.
///
/// # Errors
/// Returns [`AMBIGUOUS_IN_FLIGHT_RECOVERY`] whenever the match is not unique.
pub fn reconcile_in_flight(
    record: &ProposalRecord,
    identity: &str,
    candidates: &[CandidateIssue],
) -> Result<ResolvedLeaf, UmbrellaRefusal> {
    let leaf = record
        .leaves
        .iter()
        .find(|leaf| leaf.identity == identity)
        .ok_or(AMBIGUOUS_IN_FLIGHT_RECOVERY)?;
    if leaf.state != LeafState::InFlight || !leaf_keeps_contract(leaf, &record.umbrella) {
        return Err(AMBIGUOUS_IN_FLIGHT_RECOVERY);
    }
    let mut matches = candidates.iter().filter(|candidate| {
        candidate.title == leaf.title
            && candidate.body == leaf.body
            && candidate.number.is_some()
            && !candidate.url.is_empty()
    });
    let (Some(candidate), None) = (matches.next(), matches.next()) else {
        return Err(AMBIGUOUS_IN_FLIGHT_RECOVERY);
    };
    Ok(ResolvedLeaf {
        identity: identity.to_owned(),
        number: candidate.number.unwrap_or_default().to_string(),
        url: candidate.url.clone(),
        issue_id: candidate.issue_id.clone(),
    })
}

/// Refuse a final umbrella that would lose its prefix or its durable record.
///
/// This is the last check standing between a live managed issue and a title or
/// body a resumed run could no longer recognize as an umbrella, so it runs
/// before the mutation rather than after it.
///
/// # Errors
/// Returns [`INVALID_FINAL_UMBRELLA`] for a title without the umbrella prefix
/// or a body without the embedded proposal marker.
pub fn validate_final_umbrella(title: &str, body: &str) -> Result<(), UmbrellaRefusal> {
    if title.starts_with(UMBRELLA_PREFIX.trim_end()) && body.contains(UMBRELLA_PROPOSAL_TOKEN) {
        Ok(())
    } else {
        Err(INVALID_FINAL_UMBRELLA)
    }
}

/// Prove every recorded leaf is resolved, on contract, and unchanged remotely.
///
/// Verification is all-or-nothing on purpose: the umbrella is only complete
/// when each recorded leaf names exactly one live issue whose title and body
/// are still the exact bytes the record bound the leaf to. One unresolved leaf,
/// one leaf that lost its `[LEAF OF N]` title or fixed opening, one number that
/// matches no issue or several, or one byte of drift refuses the whole graph.
///
/// # Errors
/// Returns [`INCOMPLETE_GRAPH_STATE`] for every one of those outcomes.
pub fn verify_graph_state(
    record: &ProposalRecord,
    remote: &[RemoteLeaf],
) -> Result<(), UmbrellaRefusal> {
    for leaf in &record.leaves {
        if leaf.state != LeafState::Resolved || !leaf_keeps_contract(leaf, &record.umbrella) {
            return Err(INCOMPLETE_GRAPH_STATE);
        }
        let mut matches = remote.iter().filter(|row| row.number == leaf.number);
        let (Some(row), None) = (matches.next(), matches.next()) else {
            return Err(INCOMPLETE_GRAPH_STATE);
        };
        if row.title != leaf.title || row.body != leaf.body {
            return Err(INCOMPLETE_GRAPH_STATE);
        }
    }
    Ok(())
}

/// Return the digest of the record's deterministic leaf and edge shape.
///
/// Only the fields a partition fixes are hashed. The run-local state a leaf
/// accumulates — its number, URL, node id, and lifecycle — is deliberately
/// excluded, so the same approved partition hashes identically before the
/// first leaf is filed and after the last one is bound.
fn prepared_graph_sha256(record: &ProposalRecord) -> String {
    let mut text = String::from("{\"dependency_edges\":[");
    for (index, edge) in record.dependency_edges.iter().enumerate() {
        if index > 0 {
            text.push(',');
        }
        text.push('{');
        push_pair(&mut text, "blocked", &edge.blocked, true);
        text.push(',');
        push_pair(&mut text, "blocker", &edge.blocker, true);
        text.push('}');
    }
    text.push_str("],\"leaves\":[");
    for (index, leaf) in record.leaves.iter().enumerate() {
        if index > 0 {
            text.push(',');
        }
        text.push('{');
        push_pair(&mut text, "body", &leaf.body, true);
        text.push(',');
        push_pair(&mut text, "identity", &leaf.identity, true);
        text.push(',');
        push_pair(&mut text, "title", &leaf.title, true);
        text.push('}');
    }
    text.push_str("]}");
    text_sha256(&text)
}

/// Report whether two records describe the same fixed leaves and edges.
fn same_immutable_shape(left: &ProposalRecord, right: &ProposalRecord) -> bool {
    left.dependency_edges == right.dependency_edges
        && left.leaves.len() == right.leaves.len()
        && left.leaves.iter().zip(&right.leaves).all(|(one, other)| {
            one.identity == other.identity && one.title == other.title && one.body == other.body
        })
}

/// Compose the sentinel one proven partition authorizes.
fn completion_sentinel(
    repository: &str,
    umbrella: &str,
    input_text: &str,
    deps_text: &str,
    graph: &ProposalRecord,
) -> CompletionSentinel {
    CompletionSentinel {
        version: COMPLETION_SENTINEL_VERSION.to_owned(),
        repository: repository.to_owned(),
        umbrella: umbrella.to_owned(),
        prepared_input_sha256: text_sha256(input_text),
        prepared_deps_sha256: text_sha256(deps_text),
        prepared_graph_sha256: prepared_graph_sha256(graph),
        graph_verified: GRAPH_VERIFIED_VALUE.to_owned(),
    }
}

/// Prove the live prepared artifacts still are the ones the record was built
/// from, and return the sentinel that proof authorizes.
///
/// A record with no prepared hashes never came from a parent partition, so it
/// can authorize no completion sentinel at all. Beyond the two hashes the shape
/// is recomputed from the live batch and compared, so an edit that happens to
/// preserve a hash still cannot pass.
///
/// # Errors
/// Returns [`STALE_PREPARED_PARTITION`] when the live artifacts disagree with
/// the record, or the batch refusal when they no longer parse as a partition.
pub fn completion_sentinel_for_record(
    record: &ProposalRecord,
    input_text: &str,
    deps_text: &str,
) -> Result<CompletionSentinel, UmbrellaRefusal> {
    let snapshot = UmbrellaSnapshot {
        repository: record.repository.clone(),
        number: record.umbrella.clone(),
        title: String::new(),
        body: record.common_context.clone(),
        state: String::from("OPEN"),
        updated_at: record.expected_updated_at.clone(),
    };
    let (expected, _issue_input) = prepare_proposal_from_batch(&snapshot, input_text, deps_text)?;
    if record.prepared_input_sha256.is_empty()
        || text_sha256(input_text) != record.prepared_input_sha256
        || text_sha256(deps_text) != record.prepared_deps_sha256
        || !same_immutable_shape(record, &expected)
    {
        return Err(STALE_PREPARED_PARTITION);
    }
    Ok(completion_sentinel(
        &record.repository,
        &record.umbrella,
        input_text,
        deps_text,
        &expected,
    ))
}

/// Return the sentinel one repository, umbrella, and live partition must carry.
///
/// The parent holds no proposal record — it holds the batch it approved — so
/// the expected shape is rebuilt from that batch alone and compared row by row
/// against the sentinel the child published.
///
/// # Errors
/// Returns the batch refusal when the live artifacts are not one partition.
pub fn expected_completion_sentinel(
    repository: &str,
    umbrella: &str,
    input_text: &str,
    deps_text: &str,
) -> Result<CompletionSentinel, UmbrellaRefusal> {
    let snapshot = UmbrellaSnapshot {
        repository: repository.to_owned(),
        number: umbrella.to_owned(),
        state: String::from("OPEN"),
        ..UmbrellaSnapshot::default()
    };
    let (record, _issue_input) = prepare_proposal_from_batch(&snapshot, input_text, deps_text)?;
    Ok(completion_sentinel(
        repository, umbrella, input_text, deps_text, &record,
    ))
}

/// Refuse a record that carries more leaves than one umbrella may wire.
///
/// # Errors
/// Returns [`LEAF_CAP_EXCEEDED`] above the bound.
pub const fn check_leaf_cap(record: &ProposalRecord) -> Result<(), UmbrellaRefusal> {
    if record.leaves.len() > MAX_UMBRELLA_LEAVES {
        return Err(LEAF_CAP_EXCEEDED);
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::{
        AMBIGUOUS_IN_FLIGHT_RECOVERY, CLOSED_INPUT, COMPLETION_SENTINEL_VERSION, CandidateIssue,
        CompletionSentinel, DependencyEdge, ExpectedLeaf, INCOMPATIBLE_INPUT,
        INCOMPATIBLE_MANAGED_PARTITION, INCOMPATIBLE_UMBRELLA, INCOMPLETE_GRAPH_STATE,
        INVALID_COMPLETION_SENTINEL, INVALID_FINAL_UMBRELLA, INVALID_PREPARED_DEPENDENCIES,
        INVALID_PREPARED_PARTITION, INVALID_PROPOSAL_RECORD, INVALID_UMBRELLA_NUMBER,
        LEAF_ALREADY_RESOLVED, LeafState, MANAGED_PARTITION_PREFIXES, PREPARED_DEPENDENCY_CYCLE,
        PREPARED_PARTITION_TOO_LARGE, ProposalRecord, RemoteLeaf, ResolvedLeaf,
        STALE_PREPARED_PARTITION, UNKNOWN_LEAF_IDENTITY, UmbrellaSnapshot,
        classify_umbrella_source, completion_sentinel_for_record, expected_completion_sentinel,
        leaf_identity, mark_leaf_in_flight, parse_proposal, prepare_proposal_from_batch,
        reconcile_in_flight, record_leaf_resolved, render_proposal, render_snapshot,
        umbrella_leaf_opening_text, validate_final_umbrella, verify_graph_state,
    };

    fn snapshot() -> UmbrellaSnapshot {
        UmbrellaSnapshot {
            repository: "owner/repo".to_owned(),
            number: "12".to_owned(),
            title: format!("{}Split this work", MANAGED_PARTITION_PREFIXES[0]),
            body: "Shared context.".to_owned(),
            state: "OPEN".to_owned(),
            updated_at: "2026-08-03T00:00:00Z".to_owned(),
        }
    }

    fn record() -> ProposalRecord {
        let body = format!(
            "{}\n\nImplement the leaf.",
            umbrella_leaf_opening_text("12")
        );
        let title = "[LEAF OF 12] One".to_owned();
        ProposalRecord {
            umbrella: "12".to_owned(),
            repository: "owner/repo".to_owned(),
            expected_updated_at: "2026-07-26T00:00:00Z".to_owned(),
            common_context: "context".to_owned(),
            leaves: vec![ExpectedLeaf {
                identity: leaf_identity(&title, &body),
                title,
                body,
                ..ExpectedLeaf::default()
            }],
            ..ProposalRecord::default()
        }
    }

    #[test]
    fn an_identity_hashes_the_trimmed_title_and_the_exact_body() {
        // Frozen against the Python `hashlib.sha256` of the same two strings.
        assert_eq!(
            leaf_identity("  [LEAF OF 12] One  ", "body"),
            leaf_identity("[LEAF OF 12] One", "body")
        );
        assert_eq!(
            leaf_identity("[LEAF OF 12] One", "body"),
            "33228dbe87493bf4af2a0100ad43621fb8b2305ab651a4475aea7699eae39e57"
        );
    }

    #[test]
    fn a_record_round_trips_through_its_rendered_bytes() {
        let rendered = render_proposal(&record());
        assert!(rendered.ends_with("\"version\":1}\n"));
        assert_eq!(parse_proposal(&rendered).expect("record parses"), record());
    }

    #[test]
    fn rendering_escapes_every_character_python_escaped() {
        let mut tampered = record();
        tampered.common_context = "caf\u{e9}\u{1f600}\t\u{7f}\"\\\u{8}".to_owned();
        assert!(
            render_proposal(&tampered).starts_with(
                "{\"common_context\":\"caf\\u00e9\\ud83d\\ude00\\t\\u007f\\\"\\\\\\b\","
            )
        );
        assert_eq!(
            render_snapshot(&snapshot()),
            format!(
                "{{\"body\": \"Shared context.\", \"number\": \"12\", \"repository\": \"owner/repo\", \"state\": \"OPEN\", \"title\": \"{}Split this work\", \"updated_at\": \"2026-08-03T00:00:00Z\"}}\n",
                MANAGED_PARTITION_PREFIXES[0]
            )
        );
    }

    #[test]
    fn a_tampered_identity_number_or_edge_set_refuses() {
        let rendered = render_proposal(&record());
        let identity = record().leaves[0].identity.clone();
        assert_eq!(
            parse_proposal(&rendered.replace(&identity, &"a".repeat(64))),
            Err(INVALID_PROPOSAL_RECORD)
        );
        assert_eq!(
            parse_proposal(&rendered.replace("\"umbrella\":\"12\"", "\"umbrella\":\"0\"")),
            Err(INVALID_UMBRELLA_NUMBER)
        );
        assert_eq!(
            parse_proposal(&rendered.replace(
                "\"dependency_edges\":[]",
                &format!(
                    "\"dependency_edges\":[{{\"blocked\":\"{identity}\",\"blocker\":\"{identity}\"}}]"
                )
            )),
            Err(INVALID_PROPOSAL_RECORD)
        );
        assert_eq!(parse_proposal("[]"), Err(INVALID_PROPOSAL_RECORD));
        assert_eq!(parse_proposal("{"), Err(INVALID_PROPOSAL_RECORD));
        assert_eq!(
            parse_proposal(&rendered.replace("\"leaves\":[", "\"leaves\":[]").replacen(
                "],\"prepared_deps_sha256\"",
                ",\"prepared_deps_sha256\"",
                1
            )),
            Err(INVALID_PROPOSAL_RECORD)
        );
    }

    #[test]
    fn a_resolved_leaf_must_carry_a_number_and_a_url() {
        let rendered = render_proposal(&record());
        assert_eq!(
            parse_proposal(&rendered.replace("\"state\":\"pending\"", "\"state\":\"resolved\"")),
            Err(INVALID_PROPOSAL_RECORD)
        );
        assert_eq!(
            parse_proposal(&rendered.replace("\"state\":\"pending\"", "\"state\":\"shipped\"")),
            Err(INVALID_PROPOSAL_RECORD)
        );
    }

    #[test]
    fn a_leaf_moves_from_pending_through_flight_to_one_issue() {
        let identity = record().leaves[0].identity.clone();
        let marked = mark_leaf_in_flight(&record(), &identity).expect("marks in flight");
        assert_eq!(marked.leaves[0].state, LeafState::InFlight);
        assert_eq!(
            mark_leaf_in_flight(&record(), "absent"),
            Err(UNKNOWN_LEAF_IDENTITY)
        );
        let resolved = record_leaf_resolved(
            &marked,
            &ResolvedLeaf {
                identity: identity.clone(),
                number: "34".to_owned(),
                url: "https://example.test/issues/34".to_owned(),
                issue_id: "99".to_owned(),
            },
        )
        .expect("records the resolution");
        assert_eq!(resolved.leaves[0].state, LeafState::Resolved);
        assert_eq!(resolved.leaves[0].number, "34");
        assert_eq!(
            mark_leaf_in_flight(&resolved, &identity),
            Err(LEAF_ALREADY_RESOLVED)
        );
    }

    #[test]
    fn recovery_binds_only_one_exact_title_and_body_match() {
        let identity = record().leaves[0].identity.clone();
        let marked = mark_leaf_in_flight(&record(), &identity).expect("marks in flight");
        let leaf = marked.leaves[0].clone();
        let candidate = CandidateIssue {
            number: Some(34),
            url: "https://example.test/issues/34".to_owned(),
            title: leaf.title.clone(),
            body: leaf.body,
            issue_id: "99".to_owned(),
        };
        assert_eq!(
            reconcile_in_flight(&marked, &identity, std::slice::from_ref(&candidate))
                .expect("recovers")
                .number,
            "34"
        );
        assert_eq!(
            reconcile_in_flight(&marked, &identity, &[candidate.clone(), candidate.clone()]),
            Err(AMBIGUOUS_IN_FLIGHT_RECOVERY)
        );
        assert_eq!(
            reconcile_in_flight(&marked, &identity, &[]),
            Err(AMBIGUOUS_IN_FLIGHT_RECOVERY)
        );
        assert_eq!(
            reconcile_in_flight(&record(), &identity, std::slice::from_ref(&candidate)),
            Err(AMBIGUOUS_IN_FLIGHT_RECOVERY)
        );
        let numberless = CandidateIssue {
            number: None,
            ..candidate
        };
        assert_eq!(
            reconcile_in_flight(&marked, &identity, &[numberless]),
            Err(AMBIGUOUS_IN_FLIGHT_RECOVERY)
        );
    }

    #[test]
    fn a_prepared_batch_becomes_the_exact_leaf_titles_and_bodies() {
        let (record, issue_input) = prepare_proposal_from_batch(
            &snapshot(),
            "### [BUG] split-12-1 First\n\nFirst body.\n\n### [BUG] split-12-2 Second\n\nSecond body.\n",
            "1\t2\n",
        )
        .expect("prepares the partition");
        assert_eq!(
            record
                .leaves
                .iter()
                .map(|leaf| leaf.title.as_str())
                .collect::<Vec<&str>>(),
            [
                "[LEAF OF 12] [BUG] split-12-1 First",
                "[LEAF OF 12] [BUG] split-12-2 Second"
            ]
        );
        assert!(
            record
                .leaves
                .iter()
                .all(|leaf| leaf.body.starts_with(&umbrella_leaf_opening_text("12")))
        );
        assert_eq!(
            record.dependency_edges,
            [DependencyEdge {
                blocker: record.leaves[0].identity.clone(),
                blocked: record.leaves[1].identity.clone(),
            }]
        );
        assert_eq!(record.common_context, "Shared context.");
        assert!(!record.prepared_input_sha256.is_empty());
        assert!(issue_input.starts_with("### [BUG] split-12-1 First\n"));
    }

    #[test]
    fn a_prepared_batch_refuses_every_unusable_shape() {
        let valid = "### One\n\nFirst.\n\n### Two\n\nSecond.\n";
        for (deps, reason) in [
            ("1\t3\n", INVALID_PREPARED_DEPENDENCIES),
            (" 1\t2\n", INVALID_PREPARED_DEPENDENCIES),
            ("1\t2\r\n", INVALID_PREPARED_DEPENDENCIES),
            ("1\t2\n\n2\t1\n", INVALID_PREPARED_DEPENDENCIES),
            ("\u{661}\t\u{662}\n", INVALID_PREPARED_DEPENDENCIES),
            ("1\t2\n1\t2\n", INVALID_PREPARED_DEPENDENCIES),
            ("1\t1\n", INVALID_PREPARED_DEPENDENCIES),
            ("1\t2\n2\t1\n", PREPARED_DEPENDENCY_CYCLE),
        ] {
            assert_eq!(
                prepare_proposal_from_batch(&snapshot(), valid, deps),
                Err(reason),
                "deps {deps:?}"
            );
        }
        for input in [
            "### Same\n\nBody.\n\n### Same\n\nBody.\n",
            "### One\n\nOnly one item.\n",
            "### One\n\nFirst.\n\n### [LEAF OF 9] Two\n\nSecond.\n",
            "### One\n\n\n\n### Two\n\nSecond.\n",
            "### OOS_1: One\n\nFirst.\n\n### OOS_2: Two\n\nSecond.\n",
        ] {
            assert_eq!(
                prepare_proposal_from_batch(&snapshot(), input, ""),
                Err(INVALID_PREPARED_PARTITION),
                "input {input:?}"
            );
        }
        assert_eq!(
            prepare_proposal_from_batch(&snapshot(), &"x".repeat(262_145), ""),
            Err(PREPARED_PARTITION_TOO_LARGE)
        );
        assert_eq!(
            prepare_proposal_from_batch(&snapshot(), valid, &"1\t2\n".repeat(4_100)),
            Err(PREPARED_PARTITION_TOO_LARGE)
        );
    }

    /// The exact parent-approved batch every completion case is built from.
    const PREPARED_BATCH: &str = "### One\n\nFirst.\n\n### Two\n\nSecond.\n";

    /// One prepared record whose two leaves are already bound to issues.
    fn prepared_record() -> ProposalRecord {
        let (mut record, _issue_input) =
            prepare_proposal_from_batch(&snapshot(), PREPARED_BATCH, "1\t2\n")
                .expect("prepares the partition");
        for (index, leaf) in record.leaves.iter_mut().enumerate() {
            let number = 21 + index;
            leaf.state = LeafState::Resolved;
            leaf.number = number.to_string();
            leaf.url = format!("https://example.test/issues/{number}");
        }
        record
    }

    /// The live issues that exactly carry one record's recorded leaves.
    fn remote_rows(record: &ProposalRecord) -> Vec<RemoteLeaf> {
        record
            .leaves
            .iter()
            .map(|leaf| RemoteLeaf {
                number: leaf.number.clone(),
                title: leaf.title.clone(),
                body: leaf.body.clone(),
            })
            .collect()
    }

    #[test]
    fn a_final_umbrella_must_keep_its_prefix_and_its_record() {
        let body = "context\n<!-- larch:umbrella-proposal -->\n";
        assert_eq!(validate_final_umbrella("[UMBRELLA] Work", body), Ok(()));
        assert_eq!(
            validate_final_umbrella(&format!("{}Work", MANAGED_PARTITION_PREFIXES[0]), body),
            Err(INVALID_FINAL_UMBRELLA)
        );
        assert_eq!(
            validate_final_umbrella("[UMBRELLA] Work", "context\n"),
            Err(INVALID_FINAL_UMBRELLA)
        );
    }

    #[test]
    fn a_complete_graph_is_proved_one_recorded_leaf_at_a_time() {
        let record = prepared_record();
        let rows = remote_rows(&record);
        assert_eq!(verify_graph_state(&record, &rows), Ok(()));

        let mut pending = record.clone();
        pending.leaves[1].state = LeafState::InFlight;
        assert_eq!(
            verify_graph_state(&pending, &rows),
            Err(INCOMPLETE_GRAPH_STATE)
        );

        let mut renamed = record.clone();
        renamed.leaves[0].title = String::from("Plain title");
        assert_eq!(
            verify_graph_state(&renamed, &rows),
            Err(INCOMPLETE_GRAPH_STATE)
        );

        let mut drifted = rows.clone();
        drifted[0].body.push_str(" edited remotely");
        assert_eq!(
            verify_graph_state(&record, &drifted),
            Err(INCOMPLETE_GRAPH_STATE)
        );
        assert_eq!(
            verify_graph_state(&record, &rows[1..]),
            Err(INCOMPLETE_GRAPH_STATE)
        );
        let duplicated = [rows[0].clone(), rows[0].clone(), rows[1].clone()];
        assert_eq!(
            verify_graph_state(&record, &duplicated),
            Err(INCOMPLETE_GRAPH_STATE)
        );
    }

    #[test]
    fn a_sentinel_round_trips_and_refuses_every_other_row_shape() {
        let sentinel = completion_sentinel_for_record(&prepared_record(), PREPARED_BATCH, "1\t2\n")
            .expect("the live partition proves the record");
        let rendered = sentinel.render();
        assert!(rendered.starts_with(&format!(
            "UMBRELLA_SENTINEL_VERSION={COMPLETION_SENTINEL_VERSION}\nREPOSITORY=owner/repo\nUMBRELLA_NUMBER=12\n"
        )));
        assert!(rendered.ends_with("GRAPH_VERIFIED=true\n"));
        assert_eq!(CompletionSentinel::parse(&rendered), Ok(sentinel.clone()));
        // Frozen against Python's `json.dumps(..., sort_keys=True,
        // separators=(",", ":"))` of the same leaf and edge shape.
        assert_eq!(
            sentinel.prepared_graph_sha256,
            "20b76514a5936553c5a18422112a87e07ac4f2aad78897bfa35b822488bc92a6"
        );

        for text in [
            rendered.replace("GRAPH_VERIFIED=true\n", ""),
            format!("{rendered}EXTRA=row\n"),
            format!("{rendered}REPOSITORY=owner/repo\n"),
            rendered.replace("REPOSITORY=owner/repo", "no-separator"),
            rendered.replace("REPOSITORY=owner/repo", "=owner/repo"),
            rendered.replace("REPOSITORY=owner/repo\n", "REPOSITORY=owner/repo\r\n"),
            format!("{rendered}\n"),
        ] {
            assert_eq!(
                CompletionSentinel::parse(&text),
                Err(INVALID_COMPLETION_SENTINEL),
                "text {text:?}"
            );
        }
    }

    #[test]
    fn only_the_exact_prepared_partition_authorizes_a_sentinel() {
        let record = prepared_record();
        let sentinel = completion_sentinel_for_record(&record, PREPARED_BATCH, "1\t2\n")
            .expect("the live partition proves the record");
        // The parent holds only the batch it approved, so its independently
        // rebuilt expectation must be the same seven rows byte for byte.
        assert_eq!(
            expected_completion_sentinel("owner/repo", "12", PREPARED_BATCH, "1\t2\n"),
            Ok(sentinel)
        );
        assert_eq!(
            completion_sentinel_for_record(
                &record,
                "### One\n\nEdited.\n\n### Two\n\nSecond.\n",
                "1\t2\n"
            ),
            Err(STALE_PREPARED_PARTITION)
        );
        assert_eq!(
            completion_sentinel_for_record(&record, PREPARED_BATCH, ""),
            Err(STALE_PREPARED_PARTITION)
        );
        let drafted = ProposalRecord {
            prepared_input_sha256: String::new(),
            prepared_deps_sha256: String::new(),
            ..record
        };
        assert_eq!(
            completion_sentinel_for_record(&drafted, PREPARED_BATCH, "1\t2\n"),
            Err(STALE_PREPARED_PARTITION)
        );
        assert_eq!(
            expected_completion_sentinel("owner/repo", "12", "### Only\n\nOne.\n", ""),
            Err(INVALID_PREPARED_PARTITION)
        );
    }

    #[test]
    fn a_source_issue_is_accepted_only_on_its_declared_path() {
        assert_eq!(
            classify_umbrella_source("Regular", "body", "OPEN", false),
            Ok(())
        );
        assert_eq!(
            classify_umbrella_source("Regular", "body", "CLOSED", false),
            Err(CLOSED_INPUT)
        );
        assert_eq!(
            classify_umbrella_source("[PR] Something", "body", "OPEN", false),
            Err(INCOMPATIBLE_INPUT)
        );
        let managed = format!("{}Work", MANAGED_PARTITION_PREFIXES[0]);
        assert_eq!(
            classify_umbrella_source(&managed, "<!-- larch:plan -->", "OPEN", false),
            Err(INCOMPATIBLE_INPUT)
        );
        assert_eq!(
            classify_umbrella_source(&managed, "<!-- larch:plan -->", "OPEN", true),
            Ok(())
        );
        assert_eq!(
            classify_umbrella_source("Regular", "body", "OPEN", true),
            Err(INCOMPATIBLE_MANAGED_PARTITION)
        );
        assert_eq!(
            classify_umbrella_source("[UMBRELLA] Work", "body", "OPEN", false),
            Err(INCOMPATIBLE_UMBRELLA)
        );
        assert_eq!(
            classify_umbrella_source(
                "[UMBRELLA] Work",
                "<!-- larch:umbrella-proposal -->",
                "open",
                true
            ),
            Ok(())
        );
    }
}
