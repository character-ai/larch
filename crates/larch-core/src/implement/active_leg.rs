//! Stranded active-leg record cleanup for `implement kill-active-leg` (#8623).
//!
//! The record this reads is published by the Python commit-route leg runner
//! (`dispatch_leg_runner`), whose wire format predates the kernel process-birth
//! identity that [`crate::process_identity::validate_process_identity`] now
//! requires. Enforcing that field against a record that never carries it would
//! refuse every cleanup and silently strand the external coder's process group,
//! so validation here enforces birth identity only when the record supplies it
//! and otherwise falls back to the publisher's own contract: pid, pgid, start
//! time, and command signature. Every other check, signal order, and kill-log
//! event matches the shared owner, and the fallback disappears on its own once
//! the publisher moves to Rust in #8611.

use std::path::Path;

use serde_json::Value;

use crate::{
    implement::json_scalar_text,
    process_identity::{
        KillLogEvent, KillTargetSnapshot, ProcessIdentityHost, RecordedProcessIdentity,
        TerminateSignal, ValidationResult, collect_descendants, collect_process_group_members,
        log_signal, probe_process_identity, validate_process_identity_allowing_absent_birth,
    },
};

/// Basename of the active-leg identity sidecar inside an implement tmpdir.
pub const ACTIVE_LEG_IDENTITY_FILE: &str = ".active-leg.json";
/// Basename of the retired pgid-only active-leg sidecar, refused on sight.
pub const ACTIVE_LEG_LEGACY_PGID_FILE: &str = ".active-leg-pgid";
/// Basename of the active-leg kill log inside an implement tmpdir.
pub const ACTIVE_LEG_KILL_LOG_FILE: &str = "active-leg-kill.log.jsonl";
/// Environment variable naming the token that owns the current active leg.
pub const ENV_ACTIVE_LEG_OWNER_TOKEN: &str = "LARCH_ACTIVE_LEG_OWNER_TOKEN";

/// Caller recorded on every kill-log event this module writes.
pub const ACTIVE_LEG_CALLER: &str = "implement kill-active-leg";
/// Reason recorded when an owner-token match authorizes cleanup.
pub const ACTIVE_LEG_REASON: &str = "owner-token-cleanup";
/// Refusal reason for a record that cannot be parsed into an identity.
pub const REASON_MALFORMED: &str = "malformed-active-leg-record";
/// Refusal reason when the caller supplied no owner token.
pub const REASON_MISSING_TOKEN: &str = "missing-owner-token";
/// Refusal reason for the retired pgid-only sidecar.
pub const REASON_LEGACY_PGID: &str = "legacy-active-leg-pgid-refused";

/// Fields compared when deciding whether a record is still the one we read.
const IDENTITY_MATCH_KEYS: [&str; 6] = [
    "pid",
    "pgid",
    "start_time",
    "command_signature",
    "owner_token",
    "writer_pid",
];

/// Recover the signalable identity a published active-leg record describes.
///
/// Returns `None` for a payload missing or misshaping any required field, which
/// the caller treats as a malformed record.
#[must_use]
pub fn recorded_identity_from_payload(payload: &Value) -> Option<RecordedProcessIdentity> {
    let object = payload.as_object()?;
    Some(RecordedProcessIdentity {
        pid: json_int(object.get("pid"))?,
        pgid: json_int(object.get("pgid"))?,
        start_time: json_str(object.get("start_time"))?,
        birth_identity: object
            .get("birth_identity")
            .and_then(|value| serde_json::from_value(value.clone()).ok()),
        command_signature: json_str(object.get("command_signature"))?,
        expected_signature: object
            .get("expected_signature")
            .map_or_else(String::new, |value| {
                json_str(Some(value)).unwrap_or_default()
            }),
    })
}

/// Read an integer the way the Python publisher's `int(str(value))` did.
fn json_int(value: Option<&Value>) -> Option<i32> {
    match value? {
        Value::Number(number) => number.as_i64()?.try_into().ok(),
        Value::String(text) => text.trim().parse().ok(),
        _ => None,
    }
}

/// Read a string the way the Python publisher's `str(value)` did.
fn json_str(value: Option<&Value>) -> Option<String> {
    json_scalar_text(value?)
}

/// True when the on-disk record still carries the fields we validated against.
///
/// Guards the final unlink so a peer that republished the sidecar between our
/// read and our cleanup keeps its own record.
#[must_use]
pub fn record_matches(current: &Value, expected: &Value) -> bool {
    let (Some(current), Some(expected)) = (current.as_object(), expected.as_object()) else {
        return false;
    };
    IDENTITY_MATCH_KEYS
        .iter()
        .all(|key| current.get(*key) == expected.get(*key))
}

/// Every group member whose own identity still names `recorded`'s group.
///
/// Used when the group leader is already gone: signaling a numeric pgid is only
/// safe once every surviving member is proven to belong to this record's group.
fn validated_missing_leader_members(
    host: &dyn ProcessIdentityHost,
    recorded: &RecordedProcessIdentity,
) -> Option<Vec<i32>> {
    let members = collect_process_group_members(host, recorded.pgid);
    if members.is_empty() {
        return None;
    }
    let mut validated = Vec::with_capacity(members.len());
    for member in members {
        let identity =
            probe_process_identity(host, member, &recorded.expected_signature).identity?;
        if identity.pgid != recorded.pgid {
            return None;
        }
        validated.push(member);
    }
    Some(validated)
}

/// Terminate the process group a stranded active-leg record names.
///
/// Escalates `SIGTERM` then `SIGKILL` across the group and its descendants,
/// recording every intended signal before it is sent. A record whose leader has
/// already exited and whose group is empty is reported as successfully cleaned.
#[must_use]
pub fn terminate_active_leg_group(
    host: &dyn ProcessIdentityHost,
    recorded: &RecordedProcessIdentity,
    log_path: Option<&Path>,
    caller: &str,
    reason: &str,
) -> ValidationResult {
    let validation = validate_process_identity_allowing_absent_birth(host, recorded);
    if !validation.ok && validation.reason != "missing-pid" {
        return validation;
    }
    let current = validation
        .current
        .clone()
        .unwrap_or_else(|| recorded.clone());
    let descendants = if validation.ok {
        collect_descendants(host, recorded.pid)
    } else {
        match validated_missing_leader_members(host, recorded) {
            Some(members) => members,
            None => return validation,
        }
    };
    signal_round(
        host,
        recorded,
        log_path,
        caller,
        reason,
        TerminateSignal::Term,
        &KillTargetSnapshot {
            pid: recorded.pid,
            pgid: recorded.pgid,
            descendants,
            command: current.command_signature.clone(),
        },
    );
    host.sleep(crate::process_identity::TERMINATE_ESCALATION_SLEEP);
    let validation = validate_process_identity_allowing_absent_birth(host, recorded);
    if !validation.ok && validation.reason != "missing-pid" {
        return validation;
    }
    let kill_descendants = if validation.ok {
        collect_descendants(host, recorded.pid)
    } else {
        collect_process_group_members(host, recorded.pgid)
    };
    if !validation.ok && kill_descendants.is_empty() {
        return cleaned(current);
    }
    let command = validation
        .current
        .as_ref()
        .unwrap_or(&current)
        .command_signature
        .clone();
    signal_round(
        host,
        recorded,
        log_path,
        caller,
        reason,
        TerminateSignal::Kill,
        &KillTargetSnapshot {
            pid: recorded.pid,
            pgid: recorded.pgid,
            descendants: kill_descendants,
            command,
        },
    );
    if !validation.ok && validation.reason == "missing-pid" {
        return cleaned(current);
    }
    validation
}

fn cleaned(current: RecordedProcessIdentity) -> ValidationResult {
    ValidationResult {
        ok: true,
        reason: "ok".to_owned(),
        current: Some(current),
    }
}

/// Log and deliver one signal to the group, then to each recorded descendant.
fn signal_round(
    host: &dyn ProcessIdentityHost,
    recorded: &RecordedProcessIdentity,
    log_path: Option<&Path>,
    caller: &str,
    reason: &str,
    signal: TerminateSignal,
    snapshot: &KillTargetSnapshot,
) {
    log_signal(host, log_path, signal, snapshot, caller, reason);
    let _delivered = host.signal_group(recorded.pgid, signal);
    for child in &snapshot.descendants {
        // The publisher signals each recorded descendant individually, so a
        // child that left the group before this cleanup still receives it.
        log_signal(
            host,
            log_path,
            signal,
            &KillTargetSnapshot {
                pid: *child,
                pgid: recorded.pgid,
                descendants: Vec::new(),
                command: String::new(),
            },
            caller,
            reason,
        );
        let _delivered = host.signal_process(*child, signal);
    }
}

/// Compose the refusal event recorded when cleanup is declined.
#[must_use]
pub fn refusal_event(reason: &str, payload: Option<&Value>) -> KillLogEvent {
    let object = payload.and_then(Value::as_object);
    let numeric = |key: &str| {
        object
            .and_then(|map| map.get(key))
            .and_then(|value| json_str(Some(value)))
            .filter(|text| !text.is_empty() && text.bytes().all(|byte| byte.is_ascii_digit()))
            .and_then(|text| text.parse().ok())
            .unwrap_or(0)
    };
    KillLogEvent {
        event: "refusal".to_owned(),
        signal: String::new(),
        pid: numeric("pid"),
        pgid: numeric("pgid"),
        command: object
            .and_then(|map| map.get("command_signature"))
            .and_then(|value| json_str(Some(value)))
            .unwrap_or_default(),
        caller: ACTIVE_LEG_CALLER.to_owned(),
        reason: reason.to_owned(),
        descendants: Vec::new(),
        tmpdir_needle: String::new(),
        physical_needle: String::new(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn payload() -> Value {
        json!({
            "pid": 123,
            "pgid": 123,
            "start_time": "Fri Jul 3 17:01:02 2026",
            "command_signature": "python cli.py checks run-relevant",
            "expected_signature": "python cli.py checks run-relevant",
            "owner_token": "owner-1",
            "writer_pid": 7,
        })
    }

    #[test]
    fn payload_without_birth_identity_still_yields_a_signalable_record() {
        let recorded = recorded_identity_from_payload(&payload()).expect("record");
        assert_eq!(recorded.pid, 123);
        assert_eq!(recorded.pgid, 123);
        assert!(recorded.birth_identity.is_none());
        assert_eq!(
            recorded.expected_signature,
            "python cli.py checks run-relevant"
        );
    }

    #[test]
    fn string_numbers_parse_and_missing_fields_refuse() {
        let recorded = recorded_identity_from_payload(
            &json!({"pid": "5", "pgid": "5", "start_time": "t", "command_signature": "c"}),
        )
        .expect("record");
        assert_eq!(recorded.pid, 5);
        assert!(recorded.expected_signature.is_empty());
        assert!(recorded_identity_from_payload(&json!({"pid": 1})).is_none());
        assert!(recorded_identity_from_payload(&json!(["not", "object"])).is_none());
        assert!(
            recorded_identity_from_payload(
                &json!({"pid": "x", "pgid": 1, "start_time": "t", "command_signature": "c"})
            )
            .is_none()
        );
    }

    #[test]
    fn record_match_compares_only_the_publisher_identity_keys() {
        let expected = payload();
        let mut other = payload();
        other["expected_signature"] = json!("changed");
        assert!(record_matches(&other, &expected));
        other["writer_pid"] = json!(8);
        assert!(!record_matches(&other, &expected));
        assert!(!record_matches(&json!("scalar"), &expected));
    }

    #[test]
    fn refusal_event_keeps_digit_only_ids_and_drops_the_rest() {
        let event = refusal_event(REASON_MALFORMED, Some(&payload()));
        assert_eq!(event.pid, 123);
        assert_eq!(event.caller, ACTIVE_LEG_CALLER);
        assert!(event.signal.is_empty());
        let legacy = refusal_event(
            REASON_LEGACY_PGID,
            Some(&json!({"pid": "not-a-pid", "pgid": "", "command_signature": ""})),
        );
        assert_eq!(legacy.pid, 0);
        assert_eq!(legacy.pgid, 0);
        let bare = refusal_event(REASON_MISSING_TOKEN, None);
        assert_eq!(bare.pid, 0);
        assert!(bare.command.is_empty());
    }
}
