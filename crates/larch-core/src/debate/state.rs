//! Pure debate state-store codecs: canonical JSON, strict parsing, payload
//! fingerprints, schema versioning, and the persisted-state encode/decode pair.
//!
//! Ports the serialization and validation half of the state layer in
//! `python/larch/debate/orchestrator.py` (leaf #8599). Side-effect free: no
//! filesystem, clock, or process access. The effectful `load_state`,
//! `write_state`, and state lock live in the CLI crate's `debate_state` module.
//!
//! Byte-identity contract: a schema-2 state file written by the live Python
//! `write_state` must decode here and re-encode byte for byte, so an in-flight
//! debate survives the later cutover. Schema-1 files decode to the same logical
//! proposal and re-serialize at the current schema, matching Python's
//! always-current writer.

use crate::debate::protocol::{
    self, AdjudicationDecision, AdjudicationRecord, Dispute, LedgerRow, NonterminalPhase,
    ParsedSlotLedger, Participant, PointId, ProposalState, ReasonFingerprint, RoundNumber,
    RoundState, SelectedAdjudication, SlotLedgerBinding, SplitAdjudication, TerminalOutcome,
    TransitionAction,
};
use crate::vendor::VendorSessionHandle;
use serde::de::{self, Deserialize, Deserializer, MapAccess, SeqAccess, Visitor};
use serde_json::{Map, Number, Value};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};
use std::fmt;

// ---------------------------------------------------------------------------
// Constants (mirror orchestrator.py and config.py)
// ---------------------------------------------------------------------------

/// Current persisted-state schema version; every write emits this version.
pub const STATE_SCHEMA_VERSION: i64 = 2;
/// Persisted-state schema versions accepted on load.
pub const SUPPORTED_STATE_SCHEMA_VERSIONS: [i64; 2] = [1, STATE_SCHEMA_VERSION];
/// Debate state filename below the debate root.
pub const STATE_FILENAME: &str = "debate-state.json";
/// Debate state lock filename below the debate root.
pub const STATE_LOCK_FILENAME: &str = ".debate-state.lock";
/// Sentinel expected-fingerprint value for a first, absent state.
pub const ABSENT_FINGERPRINT: &str = "ABSENT";
/// Exit code for a validation failure.
pub const EXIT_VALIDATION: i32 = 2;
/// Exit code for an expected-fingerprint mismatch.
pub const EXIT_STALE_FINGERPRINT: i32 = 3;
/// Exit code for corrupt or off-shape state.
pub const EXIT_CORRUPT_STATE: i32 = 4;
/// Exit code for a persistence failure.
pub const EXIT_PERSISTENCE_FAILURE: i32 = 5;

const STATE_KEYS: [&str; 6] = [
    "schema_version",
    "fingerprint",
    "initialization",
    "proposal",
    "active_round",
    "drops",
];
const PROPOSAL_LEGACY_KEYS: [&str; 5] =
    ["points", "phase", "terminal", "run_local_values", "rounds"];
const PROPOSAL_CURRENT_KEYS: [&str; 7] = [
    "points",
    "phase",
    "terminal",
    "run_local_values",
    "rounds",
    "disputes",
    "adjudications",
];

// ---------------------------------------------------------------------------
// Errors
// ---------------------------------------------------------------------------

/// Stable failure category for a state-store error, carrying its exit code.
#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub enum StateErrorClass {
    /// Input validation failure (exit 2).
    Validation,
    /// Expected-fingerprint mismatch (exit 3).
    StaleFingerprint,
    /// Corrupt or off-shape state (exit 4).
    CorruptState,
    /// Persistence failure (exit 5).
    PersistenceFailure,
}

impl StateErrorClass {
    /// The stable externally visible exit code.
    #[must_use]
    pub const fn exit_code(self) -> i32 {
        match self {
            Self::Validation => EXIT_VALIDATION,
            Self::StaleFingerprint => EXIT_STALE_FINGERPRINT,
            Self::CorruptState => EXIT_CORRUPT_STATE,
            Self::PersistenceFailure => EXIT_PERSISTENCE_FAILURE,
        }
    }

    /// The stable error-class wire token.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Validation => "validation",
            Self::StaleFingerprint => "stale_fingerprint",
            Self::CorruptState => "corrupt_state",
            Self::PersistenceFailure => "persistence_failure",
        }
    }
}

/// A stable, externally visible state-store failure.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct StateError {
    class: StateErrorClass,
    message: String,
}

impl StateError {
    /// Assemble an error of `class` with a human-readable `message`.
    #[must_use]
    pub fn new(class: StateErrorClass, message: impl Into<String>) -> Self {
        Self {
            class,
            message: message.into(),
        }
    }

    /// A [`StateErrorClass::CorruptState`] error.
    #[must_use]
    pub fn corrupt(message: impl Into<String>) -> Self {
        Self::new(StateErrorClass::CorruptState, message)
    }

    /// A [`StateErrorClass::StaleFingerprint`] error.
    #[must_use]
    pub fn stale(message: impl Into<String>) -> Self {
        Self::new(StateErrorClass::StaleFingerprint, message)
    }

    /// A [`StateErrorClass::PersistenceFailure`] error.
    #[must_use]
    pub fn persistence(message: impl Into<String>) -> Self {
        Self::new(StateErrorClass::PersistenceFailure, message)
    }

    /// The failure category.
    #[must_use]
    pub const fn class(&self) -> StateErrorClass {
        self.class
    }

    /// The externally visible exit code.
    #[must_use]
    pub const fn exit_code(&self) -> i32 {
        self.class.exit_code()
    }

    /// The human-readable message.
    #[must_use]
    pub fn message(&self) -> &str {
        &self.message
    }
}

impl fmt::Display for StateError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}: {}", self.class.as_str(), self.message)
    }
}

impl std::error::Error for StateError {}

/// Reclassify any protocol rejection at the state boundary as corrupt state.
fn corrupt_from(_reason: protocol::ParseRejectionReason) -> StateError {
    StateError::corrupt("invalid persisted protocol state")
}

// ---------------------------------------------------------------------------
// Persisted data types (mirror the orchestrator dataclasses)
// ---------------------------------------------------------------------------

/// A persisted panel position sourced from the canonical role registry.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ParticipantSlot {
    /// Slot name.
    pub slot: String,
    /// Vendor tool.
    pub tool: String,
    /// Launch transport.
    pub transport: String,
    /// Whether the vendor is available.
    pub available: bool,
    /// Model identifier.
    pub model: String,
}

/// Persisted restore metadata for the debate's tracking issue.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RestoreMetadata {
    /// Tracking issue number.
    pub issue_number: String,
    /// Original tracking-issue title.
    pub original_title: String,
    /// Restore tracking-issue title.
    pub restore_title: String,
}

/// Persisted initialization context established once per debate.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct InitializationContext {
    /// Fixed point universe as raw integers.
    pub point_universe: Vec<i64>,
    /// Run-local replacement mapping.
    pub run_local_values: BTreeMap<String, String>,
    /// Repository working directory.
    pub repo_workdir: String,
    /// Log root directory.
    pub log_root: String,
    /// Run identifier.
    pub run_id: String,
    /// Panel slots in seating order.
    pub slots: Vec<ParticipantSlot>,
    /// Restore metadata.
    pub restore: RestoreMetadata,
    /// Explicit vendor session handles keyed by slot.
    pub session_handles: BTreeMap<String, VendorSessionHandle>,
    /// Optional initialization warning.
    pub warning: String,
}

/// One persisted mailbox entry: an opaque JSON object round-tripped verbatim.
pub type MailboxEntry = Map<String, Value>;

/// Persisted in-progress round bookkeeping.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ActiveRound {
    /// Round number.
    pub round_number: i64,
    /// Whether prompts were prepared.
    pub prepared: bool,
    /// Per-slot mailbox deltas.
    pub mailboxes: BTreeMap<String, Vec<MailboxEntry>>,
    /// Live slots in canonical order.
    pub live_slots: Vec<String>,
    /// Pending slots.
    pub pending_slots: Vec<String>,
    /// Reserved slot, if any.
    pub reserved_slot: Option<String>,
    /// Recorded live-slot bindings keyed by slot.
    pub bindings: BTreeMap<String, SlotLedgerBinding>,
}

/// A persisted dropped-slot record.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct DropRecord {
    /// Dropped slot name.
    pub slot: String,
    /// Round number of the drop.
    pub round_number: i64,
    /// Drop reason class.
    pub reason: String,
    /// Event identifier.
    pub event_id: String,
}

/// The persisted wrapper around the pure protocol proposal state.
///
/// `proposal_run_local_values` carries the proposal's full run-local mapping
/// (keys and values), because `protocol::ProposalState` keeps only the
/// replacement values as needles. Both are required to re-encode byte for byte.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct StoredState {
    /// Initialization context.
    pub initialization: InitializationContext,
    /// Pure protocol proposal state.
    pub proposal: ProposalState,
    /// The proposal's persisted run-local mapping.
    pub proposal_run_local_values: BTreeMap<String, String>,
    /// In-progress round bookkeeping, if any.
    pub active_round: Option<ActiveRound>,
    /// Recorded slot drops.
    pub drops: Vec<DropRecord>,
    /// Canonical payload fingerprint.
    pub fingerprint: String,
}

// ---------------------------------------------------------------------------
// Canonical JSON, strict parsing, and fingerprint
// ---------------------------------------------------------------------------

/// Serialize `value` as canonical JSON plus a trailing newline.
///
/// The workspace pins `serde_json` without `preserve_order`, so
/// [`serde_json::Value`] uses a `BTreeMap` and emits keys sorted at every
/// level with compact `,`/`:` separators and non-ASCII passed through. This is
/// byte-identical to Python
/// `json.dumps(sort_keys=True, separators=(",",":"), ensure_ascii=False)`.
fn canonical_json(value: &Value) -> String {
    let mut text = serde_json::to_string(value).unwrap_or_default();
    text.push('\n');
    text
}

/// Deserialize `text` while rejecting duplicate object keys anywhere.
///
/// Plain `serde_json::from_str::<Value>` keeps the last duplicate; Python's
/// `object_pairs_hook` rejects them. This fails closed like Python.
fn strict_parse(text: &str) -> Result<Value, StateError> {
    let _dup_free = serde_json::from_str::<DuplicateKeyGuard>(text)
        .map_err(|_error| StateError::corrupt("invalid state JSON"))?;
    serde_json::from_str::<Value>(text).map_err(|_error| StateError::corrupt("invalid state JSON"))
}

/// A parse-only guard that recurses the document and rejects duplicate keys.
struct DuplicateKeyGuard;

impl<'de> Deserialize<'de> for DuplicateKeyGuard {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: Deserializer<'de>,
    {
        deserializer.deserialize_any(DuplicateKeyVisitor)?;
        Ok(Self)
    }
}

struct DuplicateKeyVisitor;

impl<'de> Visitor<'de> for DuplicateKeyVisitor {
    type Value = ();

    fn expecting(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str("any JSON value")
    }

    fn visit_bool<E>(self, _value: bool) -> Result<(), E> {
        Ok(())
    }

    fn visit_i64<E>(self, _value: i64) -> Result<(), E> {
        Ok(())
    }

    fn visit_u64<E>(self, _value: u64) -> Result<(), E> {
        Ok(())
    }

    fn visit_f64<E>(self, _value: f64) -> Result<(), E> {
        Ok(())
    }

    fn visit_str<E>(self, _value: &str) -> Result<(), E> {
        Ok(())
    }

    fn visit_none<E>(self) -> Result<(), E> {
        Ok(())
    }

    fn visit_unit<E>(self) -> Result<(), E> {
        Ok(())
    }

    fn visit_some<D>(self, deserializer: D) -> Result<(), D::Error>
    where
        D: Deserializer<'de>,
    {
        deserializer.deserialize_any(Self)
    }

    fn visit_seq<A>(self, mut seq: A) -> Result<(), A::Error>
    where
        A: SeqAccess<'de>,
    {
        while seq.next_element::<DuplicateKeyGuard>()?.is_some() {}
        Ok(())
    }

    fn visit_map<A>(self, mut map: A) -> Result<(), A::Error>
    where
        A: MapAccess<'de>,
    {
        let mut seen: BTreeSet<String> = BTreeSet::new();
        while let Some(key) = map.next_key::<String>()? {
            let _value: DuplicateKeyGuard = map.next_value()?;
            if !seen.insert(key) {
                return Err(de::Error::custom("duplicate JSON key"));
            }
        }
        Ok(())
    }
}

/// Return the SHA-256 hex of `payload` minus its `fingerprint` field.
fn fingerprint_payload(payload: &Value) -> String {
    let mut unsigned = payload.clone();
    if let Value::Object(map) = &mut unsigned {
        let _removed = map.remove("fingerprint");
    }
    let digest = Sha256::digest(canonical_json(&unsigned).as_bytes());
    let mut hex = String::with_capacity(digest.len() * 2);
    for byte in digest {
        use fmt::Write as _;
        let _ignored = write!(&mut hex, "{byte:02x}");
    }
    hex
}

// ---------------------------------------------------------------------------
// Typed accessors over untrusted JSON
// ---------------------------------------------------------------------------

fn as_object(value: &Value) -> Result<&Map<String, Value>, StateError> {
    value
        .as_object()
        .ok_or_else(|| StateError::corrupt("expected a JSON object"))
}

fn as_array(value: &Value) -> Result<&Vec<Value>, StateError> {
    value
        .as_array()
        .ok_or_else(|| StateError::corrupt("expected a JSON array"))
}

fn as_str(value: &Value) -> Result<&str, StateError> {
    value
        .as_str()
        .ok_or_else(|| StateError::corrupt("expected a JSON string"))
}

/// Accept only an exact JSON integer, rejecting booleans and floats.
fn as_json_int(value: &Value) -> Result<i64, StateError> {
    match value {
        Value::Number(number) => number
            .as_i64()
            .or_else(|| {
                number
                    .as_u64()
                    .and_then(|unsigned| i64::try_from(unsigned).ok())
            })
            .ok_or_else(|| StateError::corrupt("expected a JSON integer")),
        _ => Err(StateError::corrupt("expected a JSON integer")),
    }
}

/// Accept only an exact JSON boolean.
fn as_bool_exact(value: &Value) -> Result<bool, StateError> {
    value
        .as_bool()
        .ok_or_else(|| StateError::corrupt("expected a JSON boolean"))
}

/// Require `object` to carry exactly `expected` keys.
fn require_exact_keys(object: &Map<String, Value>, expected: &[&str]) -> Result<(), StateError> {
    let present: BTreeSet<&str> = object.keys().map(String::as_str).collect();
    let wanted: BTreeSet<&str> = expected.iter().copied().collect();
    if present == wanted {
        Ok(())
    } else {
        Err(StateError::corrupt("unexpected state fields"))
    }
}

fn field<'a>(object: &'a Map<String, Value>, key: &str) -> Result<&'a Value, StateError> {
    object
        .get(key)
        .ok_or_else(|| StateError::corrupt("missing state field"))
}

/// Decode a JSON object of string keys to string values.
fn decode_string_map(value: &Value) -> Result<BTreeMap<String, String>, StateError> {
    let object = as_object(value)?;
    let mut result: BTreeMap<String, String> = BTreeMap::new();
    for (key, item) in object {
        let _prior = result.insert(key.clone(), as_str(item)?.to_owned());
    }
    Ok(result)
}

/// Return the run-local replacement needles (values) of a mapping.
fn needles(values: &BTreeMap<String, String>) -> Vec<&str> {
    values.values().map(String::as_str).collect()
}

// ---------------------------------------------------------------------------
// Encoders
// ---------------------------------------------------------------------------

fn string_map_value(values: &BTreeMap<String, String>) -> Value {
    Value::Object(
        values
            .iter()
            .map(|(key, value)| (key.clone(), Value::String(value.clone())))
            .collect(),
    )
}

fn encode_row(row: &LedgerRow) -> Value {
    serde_json::json!({
        "point": row.point_id.number(),
        "action": row.action.as_str(),
        "reason": row.reason,
    })
}

fn encode_binding(binding: &SlotLedgerBinding) -> Value {
    let rows: Vec<Value> = binding.ledger().rows.iter().map(encode_row).collect();
    let fingerprints: Vec<Value> = binding
        .fingerprints()
        .iter()
        .map(|fingerprint| Value::String(fingerprint.value().to_owned()))
        .collect();
    serde_json::json!({
        "slot": binding.slot().as_str(),
        "rows": rows,
        "fingerprints": fingerprints,
    })
}

fn encode_dispute(dispute: &Dispute) -> Value {
    let holding: Vec<Value> = dispute
        .holding_slots()
        .iter()
        .map(|slot| Value::String(slot.as_str().to_owned()))
        .collect();
    serde_json::json!({ "point": dispute.point_id().number(), "holding_slots": holding })
}

fn encode_adjudication(record: &AdjudicationRecord) -> Value {
    match record {
        AdjudicationRecord::Selected(selected) => serde_json::json!({
            "point": selected.point_id().number(),
            "decision": AdjudicationDecision::Selected.as_str(),
            "selected_position": selected.selected_position(),
        }),
        AdjudicationRecord::Split(split) => serde_json::json!({
            "point": split.point_id().number(),
            "decision": AdjudicationDecision::Split.as_str(),
            "position_a": split.position_a(),
            "position_b": split.position_b(),
        }),
    }
}

fn encode_round(round: &RoundState) -> Value {
    let bindings: Vec<Value> = round.bindings().iter().map(encode_binding).collect();
    serde_json::json!({ "round": round.round_number() as i64, "bindings": bindings })
}

fn encode_proposal(proposal: &ProposalState, run_local_values: &BTreeMap<String, String>) -> Value {
    let points: Vec<Value> = proposal
        .point_universe()
        .iter()
        .map(|point| Value::Number(Number::from(point.number())))
        .collect();
    let rounds: Vec<Value> = proposal.rounds().iter().map(encode_round).collect();
    let disputes: Vec<Value> = proposal.disputes().iter().map(encode_dispute).collect();
    let adjudications: Vec<Value> = proposal
        .adjudications()
        .iter()
        .map(encode_adjudication)
        .collect();
    serde_json::json!({
        "points": points,
        "phase": proposal.phase().map(NonterminalPhase::as_str),
        "terminal": proposal.terminal_outcome().map(TerminalOutcome::as_str),
        "run_local_values": string_map_value(run_local_values),
        "rounds": rounds,
        "disputes": disputes,
        "adjudications": adjudications,
    })
}

fn encode_slot(slot: &ParticipantSlot) -> Value {
    serde_json::json!({
        "slot": slot.slot,
        "tool": slot.tool,
        "transport": slot.transport,
        "available": slot.available,
        "model": slot.model,
    })
}

fn encode_restore(restore: &RestoreMetadata) -> Value {
    serde_json::json!({
        "issue_number": restore.issue_number,
        "original_title": restore.original_title,
        "restore_title": restore.restore_title,
    })
}

fn encode_session_handles(handles: &BTreeMap<String, VendorSessionHandle>) -> Value {
    Value::Object(
        handles
            .iter()
            .map(|(slot, handle)| {
                (
                    slot.clone(),
                    serde_json::json!({
                        "vendor": handle.vendor().as_str(),
                        "session_id": handle.session_id(),
                    }),
                )
            })
            .collect(),
    )
}

fn encode_initialization(context: &InitializationContext) -> Value {
    let points: Vec<Value> = context
        .point_universe
        .iter()
        .map(|point| Value::Number(Number::from(*point)))
        .collect();
    let slots: Vec<Value> = context.slots.iter().map(encode_slot).collect();
    serde_json::json!({
        "point_universe": points,
        "run_local_values": string_map_value(&context.run_local_values),
        "repo_workdir": context.repo_workdir,
        "log_root": context.log_root,
        "run_id": context.run_id,
        "slots": slots,
        "warning": context.warning,
        "restore": encode_restore(&context.restore),
        "session_handles": encode_session_handles(&context.session_handles),
    })
}

fn encode_mailboxes(mailboxes: &BTreeMap<String, Vec<MailboxEntry>>) -> Value {
    Value::Object(
        mailboxes
            .iter()
            .map(|(slot, entries)| {
                let items: Vec<Value> = entries.iter().cloned().map(Value::Object).collect();
                (slot.clone(), Value::Array(items))
            })
            .collect(),
    )
}

fn encode_active(active: Option<&ActiveRound>) -> Value {
    let Some(active) = active else {
        return Value::Null;
    };
    let live: Vec<Value> = active
        .live_slots
        .iter()
        .map(|slot| Value::String(slot.clone()))
        .collect();
    let pending: Vec<Value> = active
        .pending_slots
        .iter()
        .map(|slot| Value::String(slot.clone()))
        .collect();
    let bindings = Value::Object(
        active
            .bindings
            .iter()
            .map(|(slot, binding)| (slot.clone(), encode_binding(binding)))
            .collect(),
    );
    serde_json::json!({
        "round": active.round_number,
        "prepared": active.prepared,
        "mailboxes": encode_mailboxes(&active.mailboxes),
        "live_slots": live,
        "pending_slots": pending,
        "reserved_slot": active.reserved_slot,
        "bindings": bindings,
    })
}

fn encode_drop(drop: &DropRecord) -> Value {
    serde_json::json!({
        "slot": drop.slot,
        "round_number": drop.round_number,
        "reason": drop.reason,
        "event_id": drop.event_id,
    })
}

fn encode_state_value(state: &StoredState) -> Value {
    let drops: Vec<Value> = state.drops.iter().map(encode_drop).collect();
    serde_json::json!({
        "schema_version": STATE_SCHEMA_VERSION,
        "fingerprint": state.fingerprint,
        "initialization": encode_initialization(&state.initialization),
        "proposal": encode_proposal(&state.proposal, &state.proposal_run_local_values),
        "active_round": encode_active(state.active_round.as_ref()),
        "drops": drops,
    })
}

/// Encode a persisted state as canonical JSON at the current schema version.
#[must_use]
pub fn encode_state(state: &StoredState) -> String {
    canonical_json(&encode_state_value(state))
}

/// Return `state` with its canonical payload fingerprint recomputed.
#[must_use]
pub fn state_with_fingerprint(state: &StoredState) -> StoredState {
    let payload = encode_state_value(state);
    let fingerprint = fingerprint_payload(&payload);
    StoredState {
        fingerprint,
        ..state.clone()
    }
}

/// Verify a state's fingerprint against an operator-supplied expectation.
///
/// # Errors
///
/// Returns a [`StateErrorClass::StaleFingerprint`] error when `expected` does
/// not match `state.fingerprint`.
pub fn require_fingerprint(state: &StoredState, expected: &str) -> Result<(), StateError> {
    if expected == state.fingerprint {
        Ok(())
    } else {
        Err(StateError::stale(
            "expected fingerprint does not match state",
        ))
    }
}

// ---------------------------------------------------------------------------
// Decoders
// ---------------------------------------------------------------------------

fn decode_row_line(row: &Value) -> Result<String, StateError> {
    let object = as_object(row)?;
    require_exact_keys(object, &["point", "action", "reason"])?;
    let point = as_json_int(field(object, "point")?)?;
    let action = as_str(field(object, "action")?)?;
    let reason = as_str(field(object, "reason")?)?;
    Ok(format!("POINT POINT_{point} {action} {reason}"))
}

fn decode_binding(raw: &Value, run_local_values: &[&str]) -> Result<SlotLedgerBinding, StateError> {
    let object = as_object(raw)?;
    require_exact_keys(object, &["slot", "rows", "fingerprints"])?;
    let slot = as_str(field(object, "slot")?)?;
    let rows = as_array(field(object, "rows")?)?;
    let fingerprints_raw = as_array(field(object, "fingerprints")?)?;

    let lines: Vec<String> = rows.iter().map(decode_row_line).collect::<Result<_, _>>()?;
    let ledger: ParsedSlotLedger =
        protocol::parse_slot_ledger(&lines.join("\n")).map_err(corrupt_from)?;

    let fingerprints: Vec<ReasonFingerprint> = fingerprints_raw
        .iter()
        .map(|value| {
            let text = as_str(value)?;
            ReasonFingerprint::new(text.to_owned()).map_err(corrupt_from)
        })
        .collect::<Result<_, _>>()?;

    let participant = protocol::parse_slot(slot).map_err(corrupt_from)?;
    SlotLedgerBinding::new(participant, ledger, fingerprints, run_local_values)
        .map_err(corrupt_from)
}

fn decode_dispute(raw: &Value) -> Result<Dispute, StateError> {
    let object = as_object(raw)?;
    require_exact_keys(object, &["point", "holding_slots"])?;
    let point = as_json_int(field(object, "point")?)?;
    let slots_raw = as_array(field(object, "holding_slots")?)?;
    let point_id = decode_point_id(point)?;
    let holding: Vec<Participant> = slots_raw
        .iter()
        .map(|value| protocol::parse_slot(as_str(value)?).map_err(corrupt_from))
        .collect::<Result<_, _>>()?;
    Dispute::new(point_id, holding).map_err(corrupt_from)
}

fn decode_adjudication(raw: &Value) -> Result<AdjudicationRecord, StateError> {
    let object = as_object(raw)?;
    let point = as_json_int(field(object, "point")?)?;
    let decision = as_str(field(object, "decision")?)?;
    let point_id = decode_point_id(point)?;
    if decision == AdjudicationDecision::Selected.as_str() {
        require_exact_keys(object, &["point", "decision", "selected_position"])?;
        let position = as_str(field(object, "selected_position")?)?;
        let record =
            SelectedAdjudication::new(point_id, position.to_owned()).map_err(corrupt_from)?;
        return Ok(AdjudicationRecord::Selected(record));
    }
    if decision == AdjudicationDecision::Split.as_str() {
        require_exact_keys(object, &["point", "decision", "position_a", "position_b"])?;
        let position_a = as_str(field(object, "position_a")?)?;
        let position_b = as_str(field(object, "position_b")?)?;
        let record = SplitAdjudication::new(point_id, position_a.to_owned(), position_b.to_owned())
            .map_err(corrupt_from)?;
        return Ok(AdjudicationRecord::Split(record));
    }
    Err(StateError::corrupt("unknown adjudication decision"))
}

fn decode_point_id(number: i64) -> Result<PointId, StateError> {
    let narrowed =
        u16::try_from(number).map_err(|_error| StateError::corrupt("point out of range"))?;
    PointId::new(narrowed).map_err(corrupt_from)
}

fn decode_round_number(number: i64) -> Result<RoundNumber, StateError> {
    match number {
        1 => Ok(RoundNumber::Round1),
        2 => Ok(RoundNumber::Round2),
        _ => Err(StateError::corrupt("invalid round number")),
    }
}

fn replay_rounds(
    mut proposal: ProposalState,
    rounds: &[Value],
    values: &BTreeMap<String, String>,
) -> Result<ProposalState, StateError> {
    let borrowed = needles(values);
    for item in rounds {
        let object = as_object(item)?;
        require_exact_keys(object, &["round", "bindings"])?;
        let number = as_json_int(field(object, "round")?)?;
        let bindings_raw = as_array(field(object, "bindings")?)?;
        let bindings: Vec<SlotLedgerBinding> = bindings_raw
            .iter()
            .map(|binding| decode_binding(binding, &borrowed))
            .collect::<Result<_, _>>()?;
        let round =
            RoundState::new(decode_round_number(number)?, bindings).map_err(corrupt_from)?;
        proposal =
            protocol::transition(&proposal, TransitionAction::SubmitRound, Some(&round), None)
                .map_err(corrupt_from)?;
    }
    Ok(proposal)
}

/// Decode the persisted dispute and adjudication records (schema 2 only).
fn decode_proposal_records(
    object: &Map<String, Value>,
    schema_version: i64,
) -> Result<(Vec<Dispute>, Vec<AdjudicationRecord>), StateError> {
    if schema_version != STATE_SCHEMA_VERSION {
        return Ok((Vec::new(), Vec::new()));
    }
    let disputes_raw = as_array(field(object, "disputes")?)?;
    let adjudications_raw = as_array(field(object, "adjudications")?)?;
    let disputes: Vec<Dispute> = disputes_raw
        .iter()
        .map(decode_dispute)
        .collect::<Result<_, _>>()?;
    let adjudications: Vec<AdjudicationRecord> = adjudications_raw
        .iter()
        .map(decode_adjudication)
        .collect::<Result<_, _>>()?;
    Ok((disputes, adjudications))
}

/// Replay the persisted terminal transition, mirroring `_terminal_proposal`.
fn replay_terminal(
    proposal: ProposalState,
    terminal: Option<&str>,
    adjudications: &[AdjudicationRecord],
) -> Result<ProposalState, StateError> {
    match terminal {
        Some(token) if token == TerminalOutcome::Aborted.as_str() => {
            protocol::transition(&proposal, TransitionAction::Abort, None, None)
                .map_err(corrupt_from)
        }
        Some(token) if token == TerminalOutcome::Stalemate.as_str() => {
            protocol::transition(&proposal, TransitionAction::DeclareStalemate, None, None)
                .map_err(corrupt_from)
        }
        Some(token)
            if token == TerminalOutcome::Converged.as_str()
                || token == TerminalOutcome::BothViable.as_str() =>
        {
            if proposal.phase().is_none() {
                return Ok(proposal);
            }
            protocol::transition(
                &proposal,
                TransitionAction::Adjudicate,
                None,
                Some(adjudications),
            )
            .map_err(corrupt_from)
        }
        _ => Ok(proposal),
    }
}

/// Read the optional phase/terminal wire tokens, requiring null or string.
fn optional_token(value: &Value) -> Result<Option<String>, StateError> {
    match value {
        Value::Null => Ok(None),
        Value::String(text) => Ok(Some(text.clone())),
        _ => Err(StateError::corrupt("expected a phase or terminal token")),
    }
}

fn decode_point_universe(points: &[Value]) -> Result<Vec<PointId>, StateError> {
    points
        .iter()
        .map(|value| decode_point_id(as_json_int(value)?))
        .collect()
}

fn decode_proposal(
    raw: &Value,
    schema_version: i64,
) -> Result<(ProposalState, BTreeMap<String, String>), StateError> {
    let object = as_object(raw)?;
    let expected: &[&str] = if schema_version == STATE_SCHEMA_VERSION {
        &PROPOSAL_CURRENT_KEYS
    } else {
        &PROPOSAL_LEGACY_KEYS
    };
    require_exact_keys(object, expected)?;

    let points = as_array(field(object, "points")?)?;
    let values = decode_string_map(field(object, "run_local_values")?)?;
    let rounds = as_array(field(object, "rounds")?)?;
    let phase = optional_token(field(object, "phase")?)?;
    let terminal = optional_token(field(object, "terminal")?)?;

    let point_universe = decode_point_universe(points)?;
    let base = protocol::new_proposal(&point_universe, &needles(&values)).map_err(corrupt_from)?;
    let replayed = replay_rounds(base, rounds, &values)?;
    let (disputes, adjudications) = decode_proposal_records(object, schema_version)?;
    let proposal = replay_terminal(replayed, terminal.as_deref(), &adjudications)?;

    verify_replay(
        &proposal,
        phase.as_deref(),
        terminal.as_deref(),
        schema_version,
        &disputes,
        &adjudications,
    )?;
    Ok((proposal, values))
}

/// Assert the replayed proposal matches every persisted derived field.
fn verify_replay(
    proposal: &ProposalState,
    phase: Option<&str>,
    terminal: Option<&str>,
    schema_version: i64,
    disputes: &[Dispute],
    adjudications: &[AdjudicationRecord],
) -> Result<(), StateError> {
    let expected_phase = proposal.phase().map(NonterminalPhase::as_str);
    let expected_terminal = proposal.terminal_outcome().map(TerminalOutcome::as_str);
    if phase != expected_phase || terminal != expected_terminal {
        return Err(StateError::corrupt("persisted phase disagrees with replay"));
    }
    if schema_version == STATE_SCHEMA_VERSION
        && (proposal.disputes() != disputes || proposal.adjudications() != adjudications)
    {
        return Err(StateError::corrupt(
            "persisted records disagree with replay",
        ));
    }
    Ok(())
}

fn decode_slot(raw: &Value) -> Result<ParticipantSlot, StateError> {
    let object = as_object(raw)?;
    let present: BTreeSet<&str> = object.keys().map(String::as_str).collect();
    let allowed: BTreeSet<&str> = ["slot", "tool", "transport", "available", "model"].into();
    let required: BTreeSet<&str> = ["slot", "tool", "transport", "available"].into();
    if !present.is_subset(&allowed) || !required.is_subset(&present) {
        return Err(StateError::corrupt("invalid participant slot"));
    }
    let model = match object.get("model") {
        Some(value) => as_str(value)?.to_owned(),
        None => String::new(),
    };
    Ok(ParticipantSlot {
        slot: as_str(field(object, "slot")?)?.to_owned(),
        tool: as_str(field(object, "tool")?)?.to_owned(),
        transport: as_str(field(object, "transport")?)?.to_owned(),
        available: as_bool_exact(field(object, "available")?)?,
        model,
    })
}

fn decode_restore(raw: &Value) -> Result<RestoreMetadata, StateError> {
    let object = as_object(raw)?;
    require_exact_keys(object, &["issue_number", "original_title", "restore_title"])?;
    Ok(RestoreMetadata {
        issue_number: as_str(field(object, "issue_number")?)?.to_owned(),
        original_title: as_str(field(object, "original_title")?)?.to_owned(),
        restore_title: as_str(field(object, "restore_title")?)?.to_owned(),
    })
}

fn decode_session_handles(
    raw: &Value,
) -> Result<BTreeMap<String, VendorSessionHandle>, StateError> {
    let object = as_object(raw)?;
    let mut handles: BTreeMap<String, VendorSessionHandle> = BTreeMap::new();
    for (slot, item) in object {
        let handle_object = as_object(item)?;
        require_exact_keys(handle_object, &["vendor", "session_id"])?;
        let vendor = as_str(field(handle_object, "vendor")?)?;
        let session_id = as_str(field(handle_object, "session_id")?)?;
        let handle = VendorSessionHandle::create(vendor, session_id)
            .map_err(|_error| StateError::corrupt("invalid session handle"))?;
        let _prior = handles.insert(slot.clone(), handle);
    }
    Ok(handles)
}

fn decode_initialization(raw: &Value) -> Result<InitializationContext, StateError> {
    let object = as_object(raw)?;
    require_exact_keys(
        object,
        &[
            "point_universe",
            "run_local_values",
            "repo_workdir",
            "log_root",
            "run_id",
            "slots",
            "warning",
            "restore",
            "session_handles",
        ],
    )?;
    let point_universe: Vec<i64> = as_array(field(object, "point_universe")?)?
        .iter()
        .map(as_json_int)
        .collect::<Result<_, _>>()?;
    let slots: Vec<ParticipantSlot> = as_array(field(object, "slots")?)?
        .iter()
        .map(decode_slot)
        .collect::<Result<_, _>>()?;
    Ok(InitializationContext {
        point_universe,
        run_local_values: decode_string_map(field(object, "run_local_values")?)?,
        repo_workdir: as_str(field(object, "repo_workdir")?)?.to_owned(),
        log_root: as_str(field(object, "log_root")?)?.to_owned(),
        run_id: as_str(field(object, "run_id")?)?.to_owned(),
        slots,
        restore: decode_restore(field(object, "restore")?)?,
        session_handles: decode_session_handles(field(object, "session_handles")?)?,
        warning: as_str(field(object, "warning")?)?.to_owned(),
    })
}

fn decode_mailbox_entries(value: &Value) -> Result<Vec<MailboxEntry>, StateError> {
    as_array(value)?
        .iter()
        .map(|item| as_object(item).cloned())
        .collect()
}

fn decode_live_slots(value: &Value) -> Result<Vec<String>, StateError> {
    let live: Vec<String> = as_array(value)?
        .iter()
        .map(|slot| as_str(slot).map(str::to_owned))
        .collect::<Result<_, _>>()?;
    let canonical: Vec<String> = protocol::SLOT_ORDER
        .iter()
        .filter(|slot| live.iter().any(|entry| entry == *slot))
        .map(|slot| (*slot).to_owned())
        .collect();
    if live != canonical {
        return Err(StateError::corrupt("live slots violate canonical order"));
    }
    Ok(live)
}

fn decode_active(
    raw: &Value,
    values: &BTreeMap<String, String>,
) -> Result<Option<ActiveRound>, StateError> {
    if raw.is_null() {
        return Ok(None);
    }
    let object = as_object(raw)?;
    require_exact_keys(
        object,
        &[
            "round",
            "prepared",
            "mailboxes",
            "live_slots",
            "pending_slots",
            "reserved_slot",
            "bindings",
        ],
    )?;
    let round_number = as_json_int(field(object, "round")?)?;
    let prepared = as_bool_exact(field(object, "prepared")?)?;
    let live_slots = decode_live_slots(field(object, "live_slots")?)?;
    let pending_slots: Vec<String> = as_array(field(object, "pending_slots")?)?
        .iter()
        .map(|slot| as_str(slot).map(str::to_owned))
        .collect::<Result<_, _>>()?;
    let reserved_slot = match field(object, "reserved_slot")? {
        Value::Null => None,
        value => Some(as_str(value)?.to_owned()),
    };
    let mut mailboxes: BTreeMap<String, Vec<MailboxEntry>> = BTreeMap::new();
    for (slot, entries) in as_object(field(object, "mailboxes")?)? {
        let _prior = mailboxes.insert(slot.clone(), decode_mailbox_entries(entries)?);
    }
    let bindings = decode_active_bindings(field(object, "bindings")?, values, &live_slots)?;
    Ok(Some(ActiveRound {
        round_number,
        prepared,
        mailboxes,
        live_slots,
        pending_slots,
        reserved_slot,
        bindings,
    }))
}

fn decode_active_bindings(
    raw: &Value,
    values: &BTreeMap<String, String>,
    live_slots: &[String],
) -> Result<BTreeMap<String, SlotLedgerBinding>, StateError> {
    let borrowed = needles(values);
    let mut bindings: BTreeMap<String, SlotLedgerBinding> = BTreeMap::new();
    for (slot, item) in as_object(raw)? {
        if !live_slots.iter().any(|live| live == slot) {
            return Err(StateError::corrupt("binding slot is not live"));
        }
        let _prior = bindings.insert(slot.clone(), decode_binding(item, &borrowed)?);
    }
    Ok(bindings)
}

fn decode_drops(raw: &Value) -> Result<Vec<DropRecord>, StateError> {
    as_array(raw)?.iter().map(decode_drop).collect()
}

fn decode_drop(raw: &Value) -> Result<DropRecord, StateError> {
    let object = as_object(raw)?;
    require_exact_keys(object, &["slot", "round_number", "reason", "event_id"])?;
    Ok(DropRecord {
        slot: as_str(field(object, "slot")?)?.to_owned(),
        round_number: as_json_int(field(object, "round_number")?)?,
        reason: as_str(field(object, "reason")?)?.to_owned(),
        event_id: as_str(field(object, "event_id")?)?.to_owned(),
    })
}

/// Decode and fully validate a persisted debate-state document.
///
/// Reproduces the pure half of Python `load_state`: strict parse (rejecting
/// duplicate keys), exact top-level key set, schema and fingerprint field
/// checks, the recanonicalization-and-fingerprint gate, and per-section
/// decoding. Schema-1 documents decode with empty disputes and adjudications.
///
/// # Errors
///
/// Returns a [`StateErrorClass::CorruptState`] error for invalid JSON, an
/// unexpected key set, an unsupported schema, noncanonical bytes, a stale
/// fingerprint field, or any off-shape section.
pub fn decode_state(text: &str) -> Result<StoredState, StateError> {
    let raw = strict_parse(text)?;
    let object = as_object(&raw).map_err(|_error| StateError::corrupt("unknown state fields"))?;
    require_exact_keys(object, &STATE_KEYS)
        .map_err(|_error| StateError::corrupt("unknown state fields"))?;

    let schema_version = as_json_int(field(object, "schema_version")?)
        .map_err(|_error| StateError::corrupt("unsupported state schema"))?;
    if !SUPPORTED_STATE_SCHEMA_VERSIONS.contains(&schema_version) {
        return Err(StateError::corrupt("unsupported state schema"));
    }
    let fingerprint = as_str(field(object, "fingerprint")?)
        .map_err(|_error| StateError::corrupt("unsupported state schema"))?
        .to_owned();

    if canonical_json(&raw) != text || fingerprint_payload(&raw) != fingerprint {
        return Err(StateError::corrupt(
            "noncanonical or stale state fingerprint",
        ));
    }

    let initialization = decode_initialization(field(object, "initialization")?)?;
    let (proposal, proposal_run_local_values) =
        decode_proposal(field(object, "proposal")?, schema_version)?;
    let active_round = decode_active(field(object, "active_round")?, &proposal_run_local_values)?;
    let drops = decode_drops(field(object, "drops")?)?;

    Ok(StoredState {
        initialization,
        proposal,
        proposal_run_local_values,
        active_round,
        drops,
        fingerprint,
    })
}

#[cfg(test)]
mod tests;
