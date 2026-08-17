//! Unit tests for the pure debate state-store codecs.

use super::{
    ActiveRound, DropRecord, InitializationContext, ParticipantSlot, RestoreMetadata, StateError,
    StateErrorClass, StoredState, canonical_json, decode_state, encode_state, fingerprint_payload,
    require_fingerprint, state_with_fingerprint,
};
use crate::debate::protocol::{self, Participant, PointId, SlotLedgerBinding};
use crate::vendor::VendorSessionHandle;
use serde_json::{Value, json};
use std::collections::BTreeMap;

const CURSOR_CHAT_ID: &str = "chat-0123456789abcdef";
const CODEX_SESSION_ID: &str = "6f1b2c3d-4e5f-4a6b-8c9d-0e1f2a3b4c5d";

fn sample_values() -> BTreeMap<String, String> {
    BTreeMap::from([("run".to_owned(), "local".to_owned())])
}

fn slots() -> Vec<ParticipantSlot> {
    vec![
        ParticipantSlot {
            slot: "cursor".to_owned(),
            tool: "cursor".to_owned(),
            transport: "subprocess".to_owned(),
            available: true,
            model: "cursor-model".to_owned(),
        },
        ParticipantSlot {
            slot: "codex".to_owned(),
            tool: "codex".to_owned(),
            transport: "subprocess".to_owned(),
            available: true,
            model: "codex-model".to_owned(),
        },
    ]
}

fn session_handles() -> BTreeMap<String, VendorSessionHandle> {
    BTreeMap::from([
        (
            "cursor".to_owned(),
            VendorSessionHandle::create("cursor", CURSOR_CHAT_ID).expect("cursor handle"),
        ),
        (
            "codex".to_owned(),
            VendorSessionHandle::create("codex", CODEX_SESSION_ID).expect("codex handle"),
        ),
    ])
}

fn cursor_binding(needles: &[&str]) -> SlotLedgerBinding {
    let reason = "adopt approach cursor";
    let fingerprint = protocol::fingerprint_reason(reason, needles).expect("fingerprint");
    let ledger = protocol::parse_slot_ledger(&format!("POINT POINT_1 HOLD {reason}"))
        .expect("ledger");
    SlotLedgerBinding::new(Participant::Cursor, ledger, vec![fingerprint], needles)
        .expect("binding")
}

fn mailbox_entry() -> super::MailboxEntry {
    json!({ "kind": "delta" })
        .as_object()
        .expect("object")
        .clone()
}

fn build_state() -> StoredState {
    let values = sample_values();
    let needles: Vec<&str> = values.values().map(String::as_str).collect();
    let proposal =
        protocol::new_proposal(&[PointId::new(1).expect("point")], &needles).expect("proposal");
    let active = ActiveRound {
        round_number: 1,
        prepared: true,
        mailboxes: BTreeMap::from([
            ("cursor".to_owned(), vec![mailbox_entry()]),
            ("codex".to_owned(), Vec::new()),
        ]),
        live_slots: vec!["cursor".to_owned(), "codex".to_owned()],
        pending_slots: vec!["claude".to_owned()],
        reserved_slot: None,
        bindings: BTreeMap::from([("cursor".to_owned(), cursor_binding(&needles))]),
    };
    let initialization = InitializationContext {
        point_universe: vec![1],
        run_local_values: values.clone(),
        repo_workdir: "/debate/repo".to_owned(),
        log_root: "/debate/logs".to_owned(),
        run_id: "test-run".to_owned(),
        slots: slots(),
        restore: RestoreMetadata {
            issue_number: "1".to_owned(),
            original_title: "old".to_owned(),
            restore_title: "new".to_owned(),
        },
        session_handles: session_handles(),
        warning: String::new(),
    };
    let state = StoredState {
        initialization,
        proposal,
        proposal_run_local_values: values,
        active_round: Some(active),
        drops: vec![DropRecord {
            slot: "claude".to_owned(),
            round_number: 1,
            reason: "runner_failure".to_owned(),
            event_id: "event-1".to_owned(),
        }],
        fingerprint: String::new(),
    };
    state_with_fingerprint(&state)
}

fn resign(mut value: Value) -> String {
    let fingerprint = fingerprint_payload(&value);
    value["fingerprint"] = Value::String(fingerprint);
    canonical_json(&value)
}

fn parse(text: &str) -> Value {
    serde_json::from_str(text).expect("value")
}

#[test]
fn canonical_json_matches_python_bytes() {
    let value = json!({ "b": 1, "a": "é", "z": 9999 });
    assert_eq!(canonical_json(&value), "{\"a\":\"é\",\"b\":1,\"z\":9999}\n");
}

#[test]
fn integers_render_without_a_fractional_part() {
    let value = json!({ "n": 9999, "one": 1 });
    assert_eq!(canonical_json(&value), "{\"n\":9999,\"one\":1}\n");
}

#[test]
fn fingerprint_payload_matches_python_hex() {
    let value = json!({ "b": 1, "a": "é", "z": 9999 });
    assert_eq!(
        fingerprint_payload(&value),
        "64bb590501bc9657d8ba67fa8d7734de710fb59e14ae89635e7f0d342f21f66d"
    );
}

#[test]
fn fingerprint_payload_ignores_the_fingerprint_field() {
    let signed = json!({ "a": 1, "fingerprint": "ignored" });
    let bare = json!({ "a": 1 });
    assert_eq!(fingerprint_payload(&signed), fingerprint_payload(&bare));
}

#[test]
fn round_trips_a_rich_state_byte_for_byte() {
    let state = build_state();
    let text = encode_state(&state);
    let decoded = decode_state(&text).expect("decode");
    assert_eq!(decoded, state);
    assert_eq!(encode_state(&decoded), text);
}

#[test]
fn rejects_invalid_json() {
    assert_eq!(
        decode_state("{").expect_err("invalid").class(),
        StateErrorClass::CorruptState
    );
}

#[test]
fn rejects_a_non_object_document() {
    assert_eq!(decode_state("[]").expect_err("array").class(), StateErrorClass::CorruptState);
}

#[test]
fn rejects_duplicate_keys() {
    let err: StateError = decode_state(r#"{"a":1,"a":2}"#).expect_err("duplicate");
    assert_eq!(err.class(), StateErrorClass::CorruptState);
}

#[test]
fn rejects_an_unknown_top_level_key_set() {
    assert_eq!(
        decode_state(r#"{"a":1}"#).expect_err("unknown").class(),
        StateErrorClass::CorruptState
    );
}

#[test]
fn rejects_an_unsupported_schema_version() {
    let mut value = parse(&encode_state(&build_state()));
    value["schema_version"] = json!(3);
    let text = resign(value);
    assert_eq!(decode_state(&text).expect_err("schema").class(), StateErrorClass::CorruptState);
}

#[test]
fn rejects_a_stale_fingerprint_field() {
    let mut value = parse(&encode_state(&build_state()));
    value["fingerprint"] = Value::String("0".repeat(64));
    let text = canonical_json(&value);
    assert_eq!(
        decode_state(&text).expect_err("fingerprint").class(),
        StateErrorClass::CorruptState
    );
}

#[test]
fn rejects_noncanonical_bytes() {
    let text = format!(" {}", encode_state(&build_state()));
    assert_eq!(
        decode_state(&text).expect_err("noncanonical").class(),
        StateErrorClass::CorruptState
    );
}

#[test]
fn rejects_live_slots_out_of_canonical_order() {
    let mut value = parse(&encode_state(&build_state()));
    value["active_round"]["live_slots"] = json!(["codex", "cursor"]);
    let text = resign(value);
    assert_eq!(
        decode_state(&text).expect_err("slot order").class(),
        StateErrorClass::CorruptState
    );
}

#[test]
fn rejects_an_off_shape_proposal() {
    let mut value = parse(&encode_state(&build_state()));
    value["proposal"]
        .as_object_mut()
        .expect("proposal")
        .remove("terminal");
    let text = resign(value);
    assert_eq!(
        decode_state(&text).expect_err("proposal").class(),
        StateErrorClass::CorruptState
    );
}

#[test]
fn require_fingerprint_flags_a_mismatch() {
    let state = build_state();
    assert!(require_fingerprint(&state, &state.fingerprint).is_ok());
    let err = require_fingerprint(&state, "mismatch").expect_err("stale");
    assert_eq!(err.class(), StateErrorClass::StaleFingerprint);
    assert_eq!(err.exit_code(), 3);
}

#[test]
fn error_classes_carry_the_python_exit_codes() {
    assert_eq!(StateErrorClass::Validation.exit_code(), 2);
    assert_eq!(StateErrorClass::StaleFingerprint.exit_code(), 3);
    assert_eq!(StateErrorClass::CorruptState.exit_code(), 4);
    assert_eq!(StateErrorClass::PersistenceFailure.exit_code(), 5);
}
