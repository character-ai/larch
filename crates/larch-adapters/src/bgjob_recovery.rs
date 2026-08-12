//! Shared durable background-job recovery.
//!
//! Every consumer that finds an abandoned background-job registry row uses this
//! module.  Keeping the claim, validated teardown, result-residue cleanup, and
//! unlink proof together prevents a secondary cleaner from discarding the last
//! durable identity while a process group may still be live.

use larch_core::{
    BgjobError, ProcessIdentityHost, RecoveryClaim, RegistryEntry, child_identity_policy,
    claim_recovery, confirm_process_group_absent, ensure_under, ordered_rows, phase_barrier,
    read_entry, recovery_claim_entry_path, release_recovery_claim, render_rows, startup_env_path,
    terminate_validated_process_group_and_confirm, unlink_entry,
};
use std::{
    fs::{self, File, OpenOptions},
    io::Write as _,
    path::Path,
};

#[cfg(unix)]
use std::os::unix::fs::OpenOptionsExt as _;

/// The result of one exclusive abandoned-row recovery attempt.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum BgjobRecoveryOutcome {
    /// Teardown was proven and the durable row was removed.
    Recovered,
    /// A healthy daemon or another recovery claimant still owns the row.
    Busy,
    /// The row disappeared before it could be recovered.
    Gone,
    /// A safe teardown or durable cleanup step could not be proven.
    Failed(String),
}

/// Claim and recover a registry row whose normal daemon may have died.
///
/// The caller must pass the row it observed only for an initial diagnostic.
/// After claiming, this function rereads the durable entry before it makes any
/// recovery decision.  That prevents a stale caller from tearing down a newer
/// launch for the same run and step.
#[must_use]
pub fn recover_abandoned_entry(
    host: &dyn ProcessIdentityHost,
    registry: &Path,
    observed: &RegistryEntry,
    caller: &str,
    context: &str,
) -> BgjobRecoveryOutcome {
    let claim = match claim_recovery(host, registry) {
        Ok(RecoveryClaim::Acquired(claim)) => claim,
        Ok(RecoveryClaim::Busy) => return BgjobRecoveryOutcome::Busy,
        Ok(RecoveryClaim::Gone) => return BgjobRecoveryOutcome::Gone,
        Err(error) => {
            let reason = format!("recovery-claim-{}", one_line(&error));
            return failed(observed, context, reason);
        }
    };
    let Some(entry) = read_entry(recovery_claim_entry_path(&claim)) else {
        release_recovery_claim(&claim);
        return BgjobRecoveryOutcome::Gone;
    };
    if larch_core::daemon_liveness(host, &entry).live {
        release_recovery_claim(&claim);
        return BgjobRecoveryOutcome::Busy;
    }
    if read_completed_result(&entry.result_env, &entry.step).is_some() {
        // A result from a dead daemon is terminal only after the group is
        // independently absent.  This also converges a crash between result
        // publication and registry unlink.
        let confirmation =
            confirm_process_group_absent(host, &entry.child, child_identity_policy(&entry));
        if confirmation.terminated {
            if let Err(reason) = remove_startup_marker(&entry) {
                release_recovery_claim(&claim);
                return failed(&entry, context, reason);
            }
            return unlink_claimed_entry(&claim, &entry, context, true);
        }
        // A valid result cannot authorize removal of either itself or the
        // registry row while a process group may still exist. Retain both for
        // a later claimant that can prove absence.
        release_recovery_claim(&claim);
        return failed(&entry, context, confirmation.reason);
    }
    if read_result(&entry.result_env).is_some()
        && let Err(reason) = remove_result_residue(&entry.result_env)
    {
        release_recovery_claim(&claim);
        return failed(&entry, context, format!("partial-result-remove-{reason}"));
    }
    let kill_log = entry.log_dir.join(format!("{}.kill.log.jsonl", entry.step));
    let termination = terminate_validated_process_group_and_confirm(
        host,
        &entry.child,
        child_identity_policy(&entry),
        Some(&kill_log),
        caller,
        context,
    );
    if !termination.terminated {
        release_recovery_claim(&claim);
        return failed(&entry, context, termination.reason);
    }
    // A dead daemon must not leave an incomplete result that could later be
    // mistaken for a completed one.
    if let Err(reason) = remove_result_residue(&entry.result_env) {
        release_recovery_claim(&claim);
        return failed(&entry, context, format!("partial-result-remove-{reason}"));
    }
    if let Err(reason) = remove_startup_marker(&entry) {
        release_recovery_claim(&claim);
        return failed(&entry, context, reason);
    }
    unlink_claimed_entry(&claim, &entry, context, false)
}

fn remove_startup_marker(entry: &RegistryEntry) -> Result<(), String> {
    let path = startup_env_path(&entry.tmpdir, &entry.step)
        .map_err(|error| format!("startup-marker-path-{}", one_line(&error)))?;
    remove_result_residue(&path).map_err(|reason| format!("startup-marker-remove-{reason}"))
}

fn unlink_claimed_entry(
    claim: &larch_core::RecoveryLease,
    entry: &RegistryEntry,
    context: &str,
    completed_result: bool,
) -> BgjobRecoveryOutcome {
    unlink_entry(recovery_claim_entry_path(claim));
    let removed = fs::symlink_metadata(recovery_claim_entry_path(claim))
        .is_err_and(|error| error.kind() == std::io::ErrorKind::NotFound);
    release_recovery_claim(claim);
    if removed {
        if completed_result {
            BgjobRecoveryOutcome::Gone
        } else {
            BgjobRecoveryOutcome::Recovered
        }
    } else {
        failed(entry, context, "registry-unlink-failed".to_owned())
    }
}

fn failed(entry: &RegistryEntry, context: &str, reason: String) -> BgjobRecoveryOutcome {
    append_teardown_diagnostic_at(&entry.log_dir, &entry.step, context, &reason);
    let _ = phase_barrier("after-recovery-failure");
    BgjobRecoveryOutcome::Failed(reason)
}

fn read_result(path: &Path) -> Option<Vec<(String, String)>> {
    let metadata = fs::symlink_metadata(path).ok()?;
    if metadata.file_type().is_symlink() || !metadata.is_file() {
        return None;
    }
    let bytes = fs::read(path).ok()?;
    let text = String::from_utf8_lossy(&bytes);
    if text.contains('\r') {
        return Some(Vec::new());
    }
    Some(ordered_rows(&text))
}

fn read_completed_result(path: &Path, step: &str) -> Option<Vec<(String, String)>> {
    let rows = read_result(path)?;
    let value = |key: &str| {
        rows.iter()
            .find(|(candidate, _)| candidate == key)
            .map(|(_, value)| value.as_str())
    };
    (value("BGJOB_RC").is_some_and(|value| !value.is_empty())
        && value("BGJOB_ELAPSED_S").is_some_and(|value| !value.is_empty())
        && value("STEP") == Some(step))
    .then_some(rows)
}

fn remove_result_residue(path: &Path) -> Result<(), String> {
    match fs::symlink_metadata(path) {
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => return Ok(()),
        Err(error) => return Err(one_line(&error)),
        Ok(metadata) if metadata.file_type().is_symlink() || !metadata.is_file() => {
            return Err("unsafe-result-path".to_owned());
        }
        Ok(_) => {}
    }
    fs::remove_file(path)
        .or_else(|error| {
            if error.kind() == std::io::ErrorKind::NotFound {
                Ok(())
            } else {
                Err(error)
            }
        })
        .map_err(|error| one_line(&error))
}

fn append_teardown_diagnostic_at(log_dir: &Path, step: &str, context: &str, reason: &str) {
    let stderr_log = log_dir.join(format!("{step}.stderr.log"));
    let text = render_rows(&[
        ("BGJOB_TEARDOWN_CONTEXT".to_owned(), context.to_owned()),
        ("BGJOB_TEARDOWN_REASON".to_owned(), reason.to_owned()),
    ]);
    if let Ok(mut handle) = open_verified_log(&stderr_log, log_dir) {
        let _ = handle.write_all(text.as_bytes());
    }
}

fn open_verified_log(path: &Path, root: &Path) -> Result<File, BgjobError> {
    let root_metadata =
        fs::symlink_metadata(root).map_err(|error| BgjobError::Io(error.to_string()))?;
    if root_metadata.file_type().is_symlink() || !root_metadata.is_dir() {
        return Err(BgjobError::Invalid(format!(
            "log root must be a regular directory: {}",
            root.display()
        )));
    }
    let verified_root =
        fs::canonicalize(root).map_err(|error| BgjobError::Io(error.to_string()))?;
    let verified_path = ensure_under(path, &verified_root, "log file")?;
    if fs::symlink_metadata(path).is_ok_and(|metadata| metadata.file_type().is_symlink()) {
        return Err(BgjobError::Invalid(format!(
            "log file must not be a symlink: {}",
            path.display()
        )));
    }
    let mut options = OpenOptions::new();
    options.append(true).create(true);
    #[cfg(unix)]
    {
        options.mode(0o600).custom_flags(nix::libc::O_NOFOLLOW);
    }
    let file = options
        .open(&verified_path)
        .map_err(|error| BgjobError::Io(error.to_string()))?;
    let opened = file
        .metadata()
        .map_err(|error| BgjobError::Io(error.to_string()))?;
    if opened.is_file() {
        Ok(file)
    } else {
        Err(BgjobError::Invalid(format!(
            "log file must be regular: {}",
            path.display()
        )))
    }
}

fn one_line(error: &impl std::fmt::Display) -> String {
    error
        .to_string()
        .replace(['\n', '\r'], " ")
        .chars()
        .take(240)
        .collect()
}
