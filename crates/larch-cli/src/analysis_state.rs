//! Shared XDG analysis-state marker path, snapshot, and locked replacement.
//!
//! `/learn-from-bugs` and `/validate-merged` publish compact durable markers
//! through the same symlink-safe lock and digest compare.

use std::{
    env,
    fs::{self, OpenOptions},
    path::{Path, PathBuf},
};

#[cfg(unix)]
use std::os::unix::fs::{MetadataExt as _, OpenOptionsExt as _, PermissionsExt as _};

#[cfg(unix)]
use nix::fcntl::{Flock, FlockArg};

use larch_adapters::ensure_directory_chain;
use sha2::{Digest as _, Sha256};

/// Bytes and SHA-256 digest of one regular analysis-state file, or `missing`.
#[derive(Clone, Debug)]
pub struct StateSnapshot {
    pub data: Option<Vec<u8>>,
    pub digest: String,
}

/// Held exclusive lock plus the marker parent used for the atomic write.
pub struct LockedMarker {
    _lock: Flock<fs::File>,
    pub parent: PathBuf,
    pub snapshot: StateSnapshot,
}

/// Resolve `$XDG_STATE_HOME/larch/analysis-state/v2/<client>/<origin>`.
pub fn storage_root(client_repo: &str, storage_origin_id: &str) -> Result<PathBuf, String> {
    let home = env::var_os("XDG_STATE_HOME")
        .filter(|value| !value.is_empty())
        .map(PathBuf::from)
        .or_else(|| {
            env::var_os("HOME")
                .filter(|value| !value.is_empty())
                .map(|home| PathBuf::from(home).join(".local/state"))
        })
        .ok_or_else(|| "could not resolve analysis-state root".to_owned())?;
    if !home.is_absolute() {
        return Err("analysis state home must be an absolute path".to_owned());
    }
    let home = fs::canonicalize(&home).unwrap_or(home);
    Ok(home
        .join("larch/analysis-state/v2")
        .join(client_repo)
        .join(storage_origin_id))
}

/// Resolve `$XDG_STATE_HOME/larch/analysis-state/v2/<client>/<origin>/<relpath>`.
pub fn marker_path(root: &Path, relpath: &str) -> Result<PathBuf, String> {
    let storage =
        crate::run_log_commands::resolve_enabled_storage_path(Some(root)).map_err(|error| {
            match error {
                crate::run_log_commands::PreflightFailure::Configuration(error) => {
                    error.to_string()
                }
                crate::run_log_commands::PreflightFailure::Provider(error) => error.to_string(),
            }
        })?;
    storage_root(&storage.client_repo, &storage.storage_origin_id()).map(|root| root.join(relpath))
}

/// Read a regular marker file without following a swapped inode.
pub fn read_snapshot(path: &Path) -> Result<StateSnapshot, String> {
    if has_symlink_ancestor(path) {
        return Err(format!(
            "refusing symlinked analysis state: {}",
            path.display()
        ));
    }
    let before = match fs::symlink_metadata(path) {
        Ok(metadata) if metadata.file_type().is_symlink() || !metadata.is_file() => {
            return Err(format!(
                "analysis state is not a regular file: {}",
                path.display()
            ));
        }
        Ok(metadata) => metadata,
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => {
            return Ok(StateSnapshot {
                data: None,
                digest: "missing".to_owned(),
            });
        }
        Err(error) => return Err(format!("analysis state is unreadable: {error}")),
    };
    let data = fs::read(path).map_err(|error| format!("analysis state is unreadable: {error}"))?;
    let after = fs::symlink_metadata(path)
        .map_err(|error| format!("analysis state changed while reading: {error}"))?;
    if after.file_type().is_symlink() || !after.is_file() || !same_state_metadata(&before, &after) {
        return Err(format!(
            "analysis state changed while reading: {}",
            path.display()
        ));
    }
    Ok(StateSnapshot {
        digest: format!("{:x}", Sha256::digest(&data)),
        data: Some(data),
    })
}

/// Lock `path` and refuse to continue when the digest no longer matches.
pub fn lock_existing(path: &Path, expected_digest: &str) -> Result<LockedMarker, String> {
    let parent = path
        .parent()
        .ok_or_else(|| "state path has no parent".to_owned())?;
    ensure_directory_chain(parent).map_err(|error| error.to_string())?;
    #[cfg(unix)]
    fs::set_permissions(parent, fs::Permissions::from_mode(0o700))
        .map_err(|error| error.to_string())?;
    let lock = lock_state(path)?;
    let snapshot = read_snapshot(path)?;
    if snapshot.digest != expected_digest {
        return Err(format!(
            "analysis state changed concurrently: {}",
            path.display()
        ));
    }
    Ok(LockedMarker {
        _lock: lock,
        parent: parent.to_path_buf(),
        snapshot,
    })
}

pub fn lock_state(path: &Path) -> Result<Flock<fs::File>, String> {
    let lock = path.with_file_name(format!(
        ".{}.lock",
        path.file_name()
            .and_then(|name| name.to_str())
            .unwrap_or("state")
    ));
    if fs::symlink_metadata(&lock).is_ok_and(|metadata| metadata.file_type().is_symlink()) {
        return Err(format!("could not lock analysis state: {}", path.display()));
    }
    let mut options = OpenOptions::new();
    options.read(true).write(true).create(true);
    #[cfg(unix)]
    {
        options.mode(0o600).custom_flags(nix::libc::O_NOFOLLOW);
    }
    let file = options
        .open(&lock)
        .map_err(|error| format!("could not lock analysis state: {error}"))?;
    if !file
        .metadata()
        .map_err(|error| format!("could not lock analysis state: {error}"))?
        .is_file()
    {
        return Err(format!("could not lock analysis state: {}", path.display()));
    }
    #[cfg(unix)]
    fs::set_permissions(&lock, fs::Permissions::from_mode(0o600))
        .map_err(|error| format!("could not lock analysis state: {error}"))?;
    #[cfg(unix)]
    Flock::lock(file, FlockArg::LockExclusive)
        .map_err(|(_file, error)| format!("could not lock analysis state: {error}"))
}

pub fn same_state_metadata(before: &fs::Metadata, after: &fs::Metadata) -> bool {
    if before.len() != after.len() || before.modified().ok() != after.modified().ok() {
        return false;
    }
    #[cfg(unix)]
    {
        before.dev() == after.dev()
            && before.ino() == after.ino()
            && before.mtime() == after.mtime()
            && before.mtime_nsec() == after.mtime_nsec()
    }
    #[cfg(not(unix))]
    {
        true
    }
}

pub fn has_symlink_ancestor(path: &Path) -> bool {
    let mut current = path.parent();
    while let Some(candidate) = current {
        if fs::symlink_metadata(candidate).is_ok_and(|metadata| refused_symlink(&metadata)) {
            return true;
        }
        current = candidate.parent();
    }
    false
}

fn refused_symlink(metadata: &fs::Metadata) -> bool {
    if !metadata.file_type().is_symlink() {
        return false;
    }
    #[cfg(unix)]
    {
        metadata.uid() != 0
    }
    #[cfg(not(unix))]
    {
        true
    }
}
