//! Shared durable background-job recovery for abandoned registry rows.

use larch_core::{
    BgjobError, ParseOptions, ProcessIdentityHost, RecoveryClaim, RegistryEntry,
    child_identity_policy, claim_recovery, clear_completion_residue, completion_result_is_visible,
    confirm_process_group_absent, ensure_under, epoch_now, finish_completion_transaction,
    merge_rows, ordered_rows, parse_single_kv_row, phase_barrier, prepare_completion_transaction,
    read_completion_transaction, read_confined_regular_tail, read_confined_result_env, read_entry,
    read_merge_result_env, recovery_claim_entry_path, release_recovery_claim, render_rows,
    result_rows, startup_env_path, terminate_validated_process_group_and_confirm, unlink_entry,
    worker_status_path,
};
use std::{
    fs::{self, File, OpenOptions},
    io::Write as _,
    path::Path,
};

#[cfg(unix)]
use std::os::unix::fs::OpenOptionsExt as _;

const TERMINAL_STDOUT_RECOVERY_BYTES: u64 = 64 * 1024;

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

/// Claim and recover a row, rereading it after the claim before any teardown.
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
    if read_completed_result(&entry.tmpdir, &entry.result_env, &entry.step).is_some() {
        // A result is terminal only after group absence is independently proven.
        let confirmation =
            confirm_process_group_absent(host, &entry.child, child_identity_policy(&entry));
        if confirmation.terminated {
            if let Err(reason) = remove_startup_marker(&entry) {
                release_recovery_claim(&claim);
                return failed(&entry, context, reason);
            }
            return unlink_claimed_entry(&claim, &entry, context, true);
        }
        // Retain result and row until a later claimant can prove absence.
        release_recovery_claim(&claim);
        return failed(&entry, context, confirmation.reason);
    }
    match read_completion_transaction(&entry.tmpdir, &entry.step) {
        Ok(Some(transaction)) => {
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
            if let Err(error) = finish_completion_transaction(&transaction) {
                release_recovery_claim(&claim);
                return failed(
                    &entry,
                    context,
                    format!("completion-transaction-{}", one_line(&error)),
                );
            }
            if read_completed_result(&entry.tmpdir, &entry.result_env, &entry.step).is_none() {
                release_recovery_claim(&claim);
                return failed(
                    &entry,
                    context,
                    "completion-transaction-not-visible".to_owned(),
                );
            }
            if let Err(reason) = remove_startup_marker(&entry) {
                release_recovery_claim(&claim);
                return failed(&entry, context, reason);
            }
            return unlink_claimed_entry(&claim, &entry, context, true);
        }
        Ok(None) => {}
        Err(error) => {
            release_recovery_claim(&claim);
            return failed(
                &entry,
                context,
                format!("completion-descriptor-{}", one_line(&error)),
            );
        }
    }
    match recover_completed_worker(host, &claim, &entry, caller, context) {
        Ok(Some(outcome)) => return outcome,
        Ok(None) => {}
        Err(reason) => {
            release_recovery_claim(&claim);
            return failed(&entry, context, reason);
        }
    }
    recover_without_completion_transaction(host, &claim, &entry, caller, context)
}

/// Rebuild a terminal transaction when the worker finished but its daemon
/// died before preparing the normal completion descriptor.
///
/// The worker witness proves the requested child exited and drained its owned
/// group. Recovery independently confirms group absence before publishing any
/// result, then reconstructs the daemon-owned envelope from the persisted
/// launch inputs. A configured stdout marker is an explicit opt-in to recover
/// the final contiguous child envelope from the owned stdout log.
fn recover_completed_worker(
    host: &dyn ProcessIdentityHost,
    claim: &larch_core::RecoveryLease,
    entry: &RegistryEntry,
    caller: &str,
    context: &str,
) -> Result<Option<BgjobRecoveryOutcome>, String> {
    if !entry.recovery_inputs_recorded {
        return Ok(None);
    }
    let Some(worker_rc) = read_worker_completion(entry)? else {
        return Ok(None);
    };
    let kill_log = entry.log_dir.join(format!("{}.kill.log.jsonl", entry.step));
    let termination = terminate_validated_process_group_and_confirm(
        host,
        &entry.child,
        child_identity_policy(entry),
        Some(&kill_log),
        caller,
        context,
    );
    if !termination.terminated {
        return Err(termination.reason);
    }
    let merged = recovered_merge_rows(entry)?;
    let elapsed_s = epoch_now().saturating_sub(entry.start_epoch).max(0);
    let rows = result_rows(&entry.step, &worker_rc, elapsed_s, &merged)
        .map_err(|error| format!("completion-result-{}", one_line(&error)))?;
    let transaction = prepare_completion_transaction(
        &entry.tmpdir,
        &entry.step,
        &entry.sentinel_paths,
        &render_rows(&rows),
    )
    .map_err(|error| format!("completion-prepare-{}", one_line(&error)))?;
    finish_completion_transaction(&transaction)
        .map_err(|error| format!("completion-transaction-{}", one_line(&error)))?;
    if read_completed_result(&entry.tmpdir, &entry.result_env, &entry.step).is_none() {
        return Err("completion-transaction-not-visible".to_owned());
    }
    if let Ok(path) = worker_status_path(&entry.tmpdir, &entry.step) {
        let _ = remove_result_residue(&path);
    }
    remove_startup_marker(entry)?;
    Ok(Some(unlink_claimed_entry(claim, entry, context, true)))
}

fn read_worker_completion(entry: &RegistryEntry) -> Result<Option<String>, String> {
    let path = worker_status_path(&entry.tmpdir, &entry.step)
        .map_err(|error| format!("worker-status-path-{}", one_line(&error)))?;
    let Some(text) = read_confined_result_env(&path, &entry.tmpdir)
        .map_err(|error| format!("worker-status-read-{}", one_line(&error)))?
    else {
        return Ok(None);
    };
    if text.contains('\r') {
        return Err("worker-status-invalid".to_owned());
    }
    let rows = ordered_rows(&text);
    let value = |key: &str| {
        rows.iter()
            .find(|(candidate, _)| candidate == key)
            .map(|(_, value)| value.as_str())
    };
    let Some(rc) = value("WORKER_RC") else {
        return Err("worker-status-invalid".to_owned());
    };
    if rc.parse::<i64>().is_err() || value("STEP") != Some(entry.step.as_str()) {
        return Err("worker-status-invalid".to_owned());
    }
    let expected = render_rows(&[
        ("WORKER_RC".to_owned(), rc.to_owned()),
        ("STEP".to_owned(), entry.step.clone()),
    ]);
    if text != expected {
        return Err("worker-status-invalid".to_owned());
    }
    Ok(Some(rc.to_owned()))
}

fn recovered_merge_rows(entry: &RegistryEntry) -> Result<Vec<(String, String)>, String> {
    let mut merged = entry
        .merge_result_env
        .as_ref()
        .map(|path| {
            read_merge_result_env(path, &entry.tmpdir)
                .map(|text| merge_rows(&text))
                .map_err(|error| format!("merge-result-read-{}", one_line(&error)))
        })
        .transpose()?
        .unwrap_or_default();
    let Some(marker) = entry.terminal_stdout_key.as_deref() else {
        return Ok(merged);
    };
    for (key, value) in terminal_stdout_rows(&entry.stdout_log, &entry.log_dir, marker)? {
        if matches!(key.as_str(), "BGJOB_RC" | "BGJOB_ELAPSED_S" | "STEP") {
            continue;
        }
        if let Some((_, existing)) = merged.iter_mut().find(|(candidate, _)| candidate == &key) {
            *existing = value;
        } else {
            merged.push((key, value));
        }
    }
    Ok(merged)
}

fn terminal_stdout_rows(
    path: &Path,
    root: &Path,
    marker: &str,
) -> Result<Vec<(String, String)>, String> {
    let (bytes, truncated) = read_verified_log_tail(path, root)?;
    let text = String::from_utf8(bytes).map_err(|_| "terminal-stdout-invalid-utf8".to_owned())?;
    let text = if truncated {
        let Some(index) = text.find('\n') else {
            return Err("terminal-stdout-truncated".to_owned());
        };
        &text[index + 1..]
    } else {
        text.as_str()
    };
    let mut rows = Vec::new();
    let mut found_boundary = false;
    for line in text.split_terminator('\n').rev() {
        if line.is_empty() && rows.is_empty() {
            continue;
        }
        let Some((key, value)) = strict_terminal_row(line) else {
            found_boundary = true;
            break;
        };
        rows.push((key, value));
    }
    rows.reverse();
    if truncated && !found_boundary {
        return Err("terminal-stdout-truncated".to_owned());
    }
    if rows.iter().all(|(key, _)| key != marker) {
        return Err("terminal-stdout-marker-missing".to_owned());
    }
    Ok(rows)
}

fn strict_terminal_row(line: &str) -> Option<(String, String)> {
    let row = parse_single_kv_row(line, ParseOptions::environment())?;
    Some((row.key().to_owned(), row.value().to_owned()))
}

fn read_verified_log_tail(path: &Path, root: &Path) -> Result<(Vec<u8>, bool), String> {
    read_confined_regular_tail(
        path,
        root,
        TERMINAL_STDOUT_RECOVERY_BYTES,
        "stdout log is unsafe",
    )
    .map_err(|error| match error {
        BgjobError::Invalid(_) => "terminal-stdout-log-unsafe".to_owned(),
        BgjobError::Io(_) => one_line(&error),
    })
}

fn recover_without_completion_transaction(
    host: &dyn ProcessIdentityHost,
    claim: &larch_core::RecoveryLease,
    entry: &RegistryEntry,
    caller: &str,
    context: &str,
) -> BgjobRecoveryOutcome {
    // Preserve the legacy pre-teardown cleanup for a readable partial result,
    // but do not let an I/O obstacle at an otherwise uncommitted output path
    // prevent teardown of an unowned child group. The full residue sweep runs
    // after absence is proven.
    if read_result(&entry.result_env).is_some()
        && let Err(reason) = remove_result_residue(&entry.result_env)
    {
        release_recovery_claim(claim);
        return failed(entry, context, format!("partial-result-remove-{reason}"));
    }
    let kill_log = entry.log_dir.join(format!("{}.kill.log.jsonl", entry.step));
    let termination = terminate_validated_process_group_and_confirm(
        host,
        &entry.child,
        child_identity_policy(entry),
        Some(&kill_log),
        caller,
        context,
    );
    if !termination.terminated {
        release_recovery_claim(claim);
        return failed(entry, context, termination.reason);
    }
    if let Err(error) = clear_completion_residue(&entry.tmpdir, &entry.step) {
        release_recovery_claim(claim);
        return failed(
            entry,
            context,
            format!("partial-result-remove-{}", one_line(&error)),
        );
    }
    if let Err(reason) = remove_startup_marker(entry) {
        release_recovery_claim(claim);
        return failed(entry, context, reason);
    }
    unlink_claimed_entry(claim, entry, context, false)
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

/// Read a regular, non-symlink bgjob env file into ordered rows.
#[must_use]
pub fn read_result(path: &Path) -> Option<Vec<(String, String)>> {
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

/// Return rows only when `path` is a completed result for `step`.
#[must_use]
pub fn read_completed_result(
    tmpdir: &Path,
    path: &Path,
    step: &str,
) -> Option<Vec<(String, String)>> {
    let text = read_confined_result_env(path, tmpdir).ok()??;
    if text.contains('\r') || !completion_result_is_visible(tmpdir, step, &text).ok()? {
        return None;
    }
    let rows = ordered_rows(&text);
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

/// Remove a regular result residue without following a symlink.
///
/// # Errors
/// Returns an error if the path cannot be safely removed.
pub fn remove_result_residue(path: &Path) -> Result<(), String> {
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

/// Append a durable teardown diagnostic to one bgjob stderr log.
pub fn append_teardown_diagnostic_at(log_dir: &Path, step: &str, context: &str, reason: &str) {
    let stderr_log = log_dir.join(format!("{step}.stderr.log"));
    let _ = fs::create_dir_all(log_dir);
    let text = render_rows(&[
        ("BGJOB_TEARDOWN_CONTEXT".to_owned(), context.to_owned()),
        ("BGJOB_TEARDOWN_REASON".to_owned(), reason.to_owned()),
    ]);
    if let Ok(mut handle) = open_verified_log(&stderr_log, log_dir) {
        let _ = handle.write_all(text.as_bytes());
    }
}

/// Open a regular log beneath `root` without following a symlink.
///
/// # Errors
/// Returns an error when the path or root cannot be verified.
pub fn open_verified_log(path: &Path, root: &Path) -> Result<File, BgjobError> {
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

#[cfg(test)]
mod tests {
    use super::{TERMINAL_STDOUT_RECOVERY_BYTES, terminal_stdout_rows};
    use std::fs;

    #[test]
    fn truncated_terminal_stdout_without_a_proven_boundary_is_not_recovered() {
        let root = tempfile::tempdir().expect("log root");
        let log = root.path().join("worker.stdout.log");
        let prefix = "X".repeat(usize::try_from(TERMINAL_STDOUT_RECOVERY_BYTES + 1).expect("size"));
        fs::write(&log, format!("{prefix}\nNEXT_ACTION=main-agent-edit\n")).expect("stdout log");

        assert_eq!(
            terminal_stdout_rows(&log, root.path(), "NEXT_ACTION"),
            Err("terminal-stdout-truncated".to_owned())
        );
    }

    #[test]
    fn terminal_stdout_rejects_a_nonregular_log_before_opening_it() {
        let root = tempfile::tempdir().expect("log root");
        let log = root.path().join("worker.stdout.log");
        fs::create_dir(&log).expect("nonregular log");

        assert_eq!(
            terminal_stdout_rows(&log, root.path(), "NEXT_ACTION"),
            Err("terminal-stdout-log-unsafe".to_owned())
        );
    }
}
