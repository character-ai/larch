//! Rust owner for `implement kill-active-leg` (#8623).
//!
//! Cleans up an active-leg record whose owning process died without clearing
//! it. A leg the caller still holds a live handle for is cleaned up by that
//! caller, not here, so this command never reads a record it published itself.

use std::{ffi::OsString, path::Path, process::ExitCode};

use larch_adapters::SystemProcessIdentityHost;
use larch_core::{
    ProcessIdentityHost as _, append_kill_log,
    implement::{
        ACTIVE_LEG_CALLER, ACTIVE_LEG_IDENTITY_FILE, ACTIVE_LEG_KILL_LOG_FILE,
        ACTIVE_LEG_LEGACY_PGID_FILE, ACTIVE_LEG_REASON, REASON_LEGACY_PGID, REASON_MALFORMED,
        REASON_MISSING_TOKEN, record_matches, recorded_identity_from_payload, refusal_event,
        terminate_active_leg_group,
    },
};
use serde_json::{Value, json};

use crate::argparse_compat::parse_required_with_help;

const PROG: &str = "cli.py implement kill-active-leg";
const USAGE: &str = "usage: cli.py implement kill-active-leg [-h] --implement-tmpdir\n                                        IMPLEMENT_TMPDIR\n                                        [--owner-token OWNER_TOKEN]\n";
const HELP: &str = "usage: cli.py implement kill-active-leg [-h] --implement-tmpdir\n                                        IMPLEMENT_TMPDIR\n                                        [--owner-token OWNER_TOKEN]\n\noptions:\n  -h, --help            show this help message and exit\n  --implement-tmpdir IMPLEMENT_TMPDIR\n  --owner-token OWNER_TOKEN\n";

/// `implement kill-active-leg` compatibility command.
///
/// Always exits `0` once the command line parses: the caller runs this from a
/// shell trap, where a refusal is a logged outcome and not a driver failure.
pub fn kill_active_leg(arguments: &[OsString]) -> ExitCode {
    let parsed = match parse_required_with_help(
        arguments,
        PROG,
        USAGE,
        HELP,
        &["--implement-tmpdir", "--owner-token"],
        &[],
        &["--implement-tmpdir"],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let tmpdir = Path::new(
        parsed
            .value("--implement-tmpdir")
            .expect("--implement-tmpdir is required"),
    )
    .to_path_buf();
    let owner_token = parsed
        .value("--owner-token")
        .map(|value| value.to_string_lossy().into_owned())
        .unwrap_or_default();
    let host = SystemProcessIdentityHost::new();
    cleanup_legacy_pgid_sidecar(&host, &tmpdir);
    if owner_token.is_empty() {
        log_refusal(&host, &tmpdir, REASON_MISSING_TOKEN, None);
        return ExitCode::SUCCESS;
    }
    kill_active_leg_record(&host, &tmpdir, &owner_token);
    ExitCode::SUCCESS
}

/// Terminate the process group named by a matching active-leg record.
fn kill_active_leg_record(host: &SystemProcessIdentityHost, tmpdir: &Path, owner_token: &str) {
    let path = tmpdir.join(ACTIVE_LEG_IDENTITY_FILE);
    if !host.is_regular_file(&path) {
        return;
    }
    let Some(payload) = host
        .read_identity_file(&path)
        .and_then(|text| serde_json::from_str::<Value>(&text).ok())
    else {
        log_refusal(host, tmpdir, REASON_MALFORMED, None);
        host.remove_file(&path);
        return;
    };
    let Some(object) = payload.as_object() else {
        log_refusal(host, tmpdir, REASON_MALFORMED, None);
        host.remove_file(&path);
        return;
    };
    if object
        .get("owner_token")
        .and_then(Value::as_str)
        .unwrap_or_default()
        != owner_token
    {
        // Another live owner published this record; leave it to its owner.
        return;
    }
    let Some(recorded) = recorded_identity_from_payload(&payload) else {
        log_refusal(host, tmpdir, REASON_MALFORMED, Some(&payload));
        host.remove_file(&path);
        return;
    };
    let log_path = tmpdir.join(ACTIVE_LEG_KILL_LOG_FILE);
    let validation = terminate_active_leg_group(
        host,
        &recorded,
        Some(&log_path),
        ACTIVE_LEG_CALLER,
        ACTIVE_LEG_REASON,
    );
    if !validation.ok {
        log_refusal(host, tmpdir, &validation.reason, Some(&payload));
        return;
    }
    // Re-read before unlinking: a peer may have republished this path while the
    // group was being signaled, and that peer's record is not ours to remove.
    let Some(current) = host
        .read_identity_file(&path)
        .and_then(|text| serde_json::from_str::<Value>(&text).ok())
    else {
        return;
    };
    if record_matches(&current, &payload) {
        host.remove_file(&path);
    }
}

/// Refuse and remove the retired pgid-only sidecar.
///
/// A bare pgid carries no identity, so it can never be proven to still name the
/// process group it was written for.
fn cleanup_legacy_pgid_sidecar(host: &SystemProcessIdentityHost, tmpdir: &Path) {
    let path = tmpdir.join(ACTIVE_LEG_LEGACY_PGID_FILE);
    if !host.is_regular_file(&path) {
        return;
    }
    let raw = host
        .read_text_lossy(&path)
        .unwrap_or_default()
        .trim()
        .to_owned();
    log_refusal(
        host,
        tmpdir,
        REASON_LEGACY_PGID,
        Some(&json!({"pid": raw, "pgid": raw, "command_signature": ""})),
    );
    host.remove_file(&path);
}

fn log_refusal(
    host: &SystemProcessIdentityHost,
    tmpdir: &Path,
    reason: &str,
    payload: Option<&Value>,
) {
    append_kill_log(
        host,
        Some(&tmpdir.join(ACTIVE_LEG_KILL_LOG_FILE)),
        &refusal_event(reason, payload),
    );
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;

    fn arguments(values: &[&str]) -> Vec<OsString> {
        values.iter().map(OsString::from).collect()
    }

    fn kill_log(tmpdir: &Path) -> String {
        fs::read_to_string(tmpdir.join(ACTIVE_LEG_KILL_LOG_FILE)).unwrap_or_default()
    }

    #[test]
    fn a_malformed_command_line_refuses_with_the_python_exit_codes() {
        assert_eq!(
            format!("{:?}", kill_active_leg(&arguments(&[]))),
            format!("{:?}", ExitCode::from(2))
        );
        assert_eq!(
            format!("{:?}", kill_active_leg(&arguments(&["--help"]))),
            format!("{:?}", ExitCode::SUCCESS)
        );
    }

    #[test]
    fn a_missing_owner_token_logs_a_refusal_and_succeeds() {
        let temporary = tempfile::tempdir().expect("temporary dir");
        let code = kill_active_leg(&arguments(&[
            "--implement-tmpdir",
            temporary.path().to_str().expect("utf8 path"),
        ]));
        assert_eq!(
            format!("{code:?}"),
            format!("{:?}", ExitCode::SUCCESS),
            "a trap-invoked cleanup never fails its caller"
        );
        let log = kill_log(temporary.path());
        assert!(log.contains(REASON_MISSING_TOKEN), "{log}");
        assert!(log.contains("\"event\":\"refusal\""), "{log}");
    }

    #[test]
    fn the_retired_pgid_sidecar_is_refused_and_removed() {
        let temporary = tempfile::tempdir().expect("temporary dir");
        let legacy = temporary.path().join(ACTIVE_LEG_LEGACY_PGID_FILE);
        fs::write(&legacy, "4242\n").expect("write legacy sidecar");
        let _code = kill_active_leg(&arguments(&[
            "--implement-tmpdir",
            temporary.path().to_str().expect("utf8 path"),
            "--owner-token",
            "owner-1",
        ]));
        assert!(!legacy.exists(), "the retired sidecar must not survive");
        let log = kill_log(temporary.path());
        assert!(log.contains(REASON_LEGACY_PGID), "{log}");
        assert!(log.contains("\"pid\":4242"), "{log}");
    }

    #[test]
    fn a_malformed_record_is_refused_and_discarded() {
        let temporary = tempfile::tempdir().expect("temporary dir");
        let record = temporary.path().join(ACTIVE_LEG_IDENTITY_FILE);
        fs::write(&record, "{not json").expect("write record");
        let _code = kill_active_leg(&arguments(&[
            "--implement-tmpdir",
            temporary.path().to_str().expect("utf8 path"),
            "--owner-token",
            "owner-1",
        ]));
        assert!(!record.exists());
        assert!(kill_log(temporary.path()).contains(REASON_MALFORMED));
    }

    #[test]
    fn a_record_owned_by_another_token_is_left_untouched_and_unlogged() {
        let temporary = tempfile::tempdir().expect("temporary dir");
        let record = temporary.path().join(ACTIVE_LEG_IDENTITY_FILE);
        fs::write(
            &record,
            serde_json::to_string(&json!({
                "pid": 4242,
                "pgid": 4242,
                "start_time": "now",
                "command_signature": "cmd",
                "owner_token": "someone-else",
                "writer_pid": 7,
            }))
            .expect("serialize record"),
        )
        .expect("write record");
        let _code = kill_active_leg(&arguments(&[
            "--implement-tmpdir",
            temporary.path().to_str().expect("utf8 path"),
            "--owner-token",
            "owner-1",
        ]));
        assert!(record.exists(), "a peer's record is not ours to remove");
        assert!(kill_log(temporary.path()).is_empty());
    }

    #[test]
    fn a_record_missing_required_fields_is_refused_with_its_pid_logged() {
        let temporary = tempfile::tempdir().expect("temporary dir");
        let record = temporary.path().join(ACTIVE_LEG_IDENTITY_FILE);
        fs::write(
            &record,
            serde_json::to_string(&json!({
                "pid": 4242,
                "command_signature": "cmd",
                "owner_token": "owner-1",
            }))
            .expect("serialize record"),
        )
        .expect("write record");
        let _code = kill_active_leg(&arguments(&[
            "--implement-tmpdir",
            temporary.path().to_str().expect("utf8 path"),
            "--owner-token",
            "owner-1",
        ]));
        assert!(!record.exists());
        let log = kill_log(temporary.path());
        assert!(log.contains(REASON_MALFORMED), "{log}");
        assert!(log.contains("\"pid\":4242"), "{log}");
    }

    #[test]
    fn a_stale_record_whose_group_is_gone_is_refused_and_left_in_place() {
        let temporary = tempfile::tempdir().expect("temporary dir");
        let record = temporary.path().join(ACTIVE_LEG_IDENTITY_FILE);
        // PID 2^31-1 cannot be live on any supported host, so validation reports
        // `missing-pid` with no surviving group member to signal. The retired
        // owner logs that refusal and keeps the sidecar rather than unlinking a
        // record it could not prove it had finished with.
        fs::write(
            &record,
            serde_json::to_string(&json!({
                "pid": 2_147_483_647_i64,
                "pgid": 2_147_483_647_i64,
                "start_time": "Fri Jul 3 17:01:02 2026",
                "command_signature": "python cli.py checks run-relevant",
                "expected_signature": "python cli.py checks run-relevant",
                "owner_token": "owner-1",
                "writer_pid": 7,
            }))
            .expect("serialize record"),
        )
        .expect("write record");
        let _code = kill_active_leg(&arguments(&[
            "--implement-tmpdir",
            temporary.path().to_str().expect("utf8 path"),
            "--owner-token",
            "owner-1",
        ]));
        assert!(record.exists(), "the sidecar outlives an unprovable kill");
        let log = kill_log(temporary.path());
        assert!(log.contains("missing-pid"), "{log}");
        assert!(log.contains("\"event\":\"refusal\""), "{log}");
    }
}
