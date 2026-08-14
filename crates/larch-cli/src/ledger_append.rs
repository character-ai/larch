//! Shared flock append helper for timing and token ledgers.
//!
//! Both domains write append-only files under a short exclusive lock and then
//! restore owner-only permissions. Keeping one owner avoids duplicate
//! production blocks across the CLI modules.

use std::{
    fs,
    io::Write as _,
    path::Path,
    thread,
    time::{Duration, SystemTime},
};

#[cfg(unix)]
use std::os::unix::fs::OpenOptionsExt as _;

const LOCK_TIMEOUT: Duration = Duration::from_secs(5);
const LOCK_RETRY_PAUSE: Duration = Duration::from_millis(50);

/// Append `line` under an exclusive non-blocking flock with a short retry budget.
///
/// On lock timeout the call logs a domain-prefixed warning and returns success
/// so best-effort telemetry writers do not fail the parent command.
///
/// # Errors
/// Returns an I/O diagnostic when the open or write fails.
pub fn append_locked_line(path: &Path, line: &str, domain: &str) -> Result<(), String> {
    append_locked(path, line, domain)
}

/// Restore owner-read/write permissions after a successful append.
pub fn restore_owner_only_permissions(path: &Path) {
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt as _;
        let _ignored = fs::set_permissions(path, fs::Permissions::from_mode(0o600));
    }
    #[cfg(not(unix))]
    {
        let _ = path;
    }
}

#[cfg(unix)]
fn append_locked(path: &Path, line: &str, domain: &str) -> Result<(), String> {
    use nix::fcntl::{Flock, FlockArg};

    let mut handle = fs::OpenOptions::new()
        .append(true)
        .create(true)
        .mode(0o600)
        .custom_flags(nix::libc::O_NOFOLLOW)
        .open(path)
        .map_err(|error| error.to_string())?;
    let deadline = SystemTime::now() + LOCK_TIMEOUT;
    loop {
        match Flock::lock(handle, FlockArg::LockExclusiveNonblock) {
            Ok(mut locked) => {
                return locked
                    .write_all(line.as_bytes())
                    .map_err(|error| error.to_string());
            }
            Err((returned, _errno)) => handle = returned,
        }
        if SystemTime::now() >= deadline {
            eprintln!(
                "{domain}: WARNING: flock lock acquisition failed; skipping append for {}",
                path.display()
            );
            return Ok(());
        }
        thread::sleep(LOCK_RETRY_PAUSE);
    }
}

#[cfg(not(unix))]
fn append_locked(path: &Path, line: &str, _domain: &str) -> Result<(), String> {
    fs::OpenOptions::new()
        .append(true)
        .create(true)
        .open(path)
        .and_then(|mut handle| handle.write_all(line.as_bytes()))
        .map_err(|error| error.to_string())
}
