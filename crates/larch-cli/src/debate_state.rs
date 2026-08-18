//! Effectful debate state store: confined load and atomic write plus the
//! per-debate state lock.
//!
//! Ports the filesystem half of the state layer in
//! `python/larch/debate/orchestrator.py` (leaf #8599). All serialization and
//! validation is delegated to `larch_core::debate::state`; this module owns
//! only the trusted-root confinement, the atomic write, and the flock.

use std::collections::BTreeMap;
use std::ffi::OsString;
use std::fs::{self, OpenOptions};
use std::path::Path;

#[cfg(unix)]
use std::os::unix::fs::OpenOptionsExt as _;

#[cfg(unix)]
use nix::fcntl::{Flock, FlockArg};

use larch_adapters::{
    PathIntent, TemporaryRoot, atomic_write_utf8_in, ensure_directory_chain, read_utf8,
};
use larch_core::debate::state::{
    STATE_FILENAME, STATE_LOCK_FILENAME, StateError, StoredState, decode_state, encode_state,
    state_with_fingerprint,
};

/// Resolve the debate root as a trusted, non-symlinked directory.
fn trusted_root(root: &Path) -> Result<TemporaryRoot, StateError> {
    TemporaryRoot::resolve(Some(root))
        .map_err(|_error| StateError::persistence("unsafe debate directory"))
}

/// Load and fully validate the persisted debate state below `root`.
///
/// # Errors
///
/// Returns a persistence-failure error for an unsafe root and a corrupt-state
/// error for a missing, unsafe, unreadable, or off-shape state file.
pub fn load_state(root: &Path) -> Result<StoredState, StateError> {
    let trusted = trusted_root(root)?;
    let target = trusted.path().join(STATE_FILENAME);
    let confined = trusted
        .confine(&target, PathIntent::Read)
        .map_err(|_error| StateError::corrupt("state file missing or unsafe"))?;
    let text =
        read_utf8(&confined).map_err(|_error| StateError::corrupt("unable to read state"))?;
    decode_state(&text)
}

/// Finalize the fingerprint and atomically write the state below `root`.
///
/// Always writes canonical bytes at the current schema version, matching the
/// Python writer. Returns the fingerprinted state.
///
/// # Errors
///
/// Returns a persistence-failure error when the root is unsafe or the atomic
/// write fails.
pub fn write_state(root: &Path, state: &StoredState) -> Result<StoredState, StateError> {
    ensure_directory_chain(root)
        .map_err(|_error| StateError::persistence("unsafe debate directory"))?;
    let trusted = trusted_root(root)?;
    let finalized = state_with_fingerprint(state);
    let canonical = encode_state(&finalized);
    let target = trusted.path().join(STATE_FILENAME);
    atomic_write_utf8_in(&trusted, &target, &canonical, false, 0o600)
        .map_err(|_error| StateError::persistence("unable to write state"))?;
    Ok(finalized)
}

/// Acquire the exclusive per-debate state lock below `root`.
///
/// Opens the lock file with `O_NOFOLLOW`, refuses a non-regular target, and
/// takes an exclusive `flock`. The lock releases when the returned guard drops.
///
/// # Errors
///
/// Returns a persistence-failure error when the lock path is a symlink or
/// non-regular file, or when the lock cannot be opened or acquired.
#[cfg(unix)]
pub fn lock_state(root: &Path) -> Result<Flock<fs::File>, StateError> {
    let lock = root.join(STATE_LOCK_FILENAME);
    let mut options = OpenOptions::new();
    options
        .read(true)
        .write(true)
        .create(true)
        .mode(0o600)
        .custom_flags(nix::libc::O_NOFOLLOW);
    let file = options
        .open(&lock)
        .map_err(|_error| StateError::persistence("unable to acquire debate state lock"))?;
    let metadata = file
        .metadata()
        .map_err(|_error| StateError::persistence("unable to acquire debate state lock"))?;
    if !metadata.file_type().is_file() {
        return Err(StateError::persistence(
            "refusing non-regular debate state lock",
        ));
    }
    Flock::lock(file, FlockArg::LockExclusive)
        .map_err(|(_file, _error)| StateError::persistence("unable to acquire debate state lock"))
}

/// Parse `--flag value` / `--flag=value` pairs for a closed known-flag set.
///
/// Unknown flags, non-flag tokens, missing values, and non-UTF-8 tokens fail.
/// Required-flag checks stay with the caller so init-style and publication-style
/// required sets can differ.
pub fn parse_known_flags(
    arguments: &[OsString],
    known: &[&str],
) -> Result<BTreeMap<String, String>, ()> {
    let mut parsed: BTreeMap<String, String> = BTreeMap::new();
    let mut index = 0;
    while index < arguments.len() {
        let token = arguments[index].to_str().ok_or(())?;
        if !token.starts_with("--") {
            return Err(());
        }
        let (flag, inline) = match token.split_once('=') {
            Some((flag, value)) => (flag, Some(value.to_owned())),
            None => (token, None),
        };
        if !known.contains(&flag) {
            return Err(());
        }
        let value = if let Some(value) = inline {
            value
        } else {
            index += 1;
            arguments
                .get(index)
                .ok_or(())?
                .to_str()
                .ok_or(())?
                .to_owned()
        };
        let _ = parsed.insert(flag.to_owned(), value);
        index += 1;
    }
    Ok(parsed)
}
