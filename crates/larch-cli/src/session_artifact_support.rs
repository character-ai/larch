//! Confinement helpers for private, session-scoped command artifacts.
//!
//! Commands accept model-authored artifact paths, but each path must remain
//! below the caller's approved session root. Keeping that policy here ensures
//! every command gets the same symlink, containment, size, and file-mode
//! protections.

use larch_adapters::{
    ConfinedPath, PathIntent, TemporaryRoot, atomic_write_utf8, is_allowed_session_tmpdir,
    normalize_path, open_confined_read,
};
use larch_core::allowed_session_roots;
use std::{
    env, fs,
    io::Read as _,
    path::{Path, PathBuf},
};

/// Canonicalize one existing, non-symlink directory argument.
///
/// # Errors
///
/// Returns an error when `path` does not exist, is a symlink, or is not a
/// directory.
pub fn canonical_directory(path: &Path, option: &str) -> Result<PathBuf, String> {
    let canonical = fs::canonicalize(path).map_err(|_| format!("{option} must exist"))?;
    let metadata = fs::symlink_metadata(path).map_err(|error| error.to_string())?;
    if metadata.file_type().is_symlink() || !canonical.is_dir() {
        return Err(format!("{option} must be a non-symlink directory"));
    }
    Ok(canonical)
}

/// Resolve and authorize one absolute session root.
///
/// # Errors
///
/// Returns an error when the path is relative, cannot become a temporary root,
/// or lies outside Larch's configured session roots.
pub fn temporary_root(path: &Path, option: &str) -> Result<TemporaryRoot, String> {
    if !path.is_absolute() {
        return Err(format!("{option} must be absolute"));
    }
    let root = TemporaryRoot::resolve(Some(path)).map_err(|error| format!("{option}: {error}"))?;
    let allowed = allowed_session_roots(
        env::var_os("XDG_CACHE_HOME").as_deref(),
        env::var_os("HOME").as_deref(),
    );
    if !is_allowed_session_tmpdir(root.path(), &allowed) {
        return Err(format!("{option} must be below an allowed session root"));
    }
    Ok(root)
}

/// Confine an absolute artifact path below an already-authorized session root.
///
/// # Errors
///
/// Returns an error when either path is relative, the artifact escapes its
/// supplied root, names that root directly, or violates adapter confinement.
pub fn confine_session_path(
    path: &Path,
    supplied_root: &Path,
    root: &TemporaryRoot,
    intent: PathIntent,
    option: &str,
) -> Result<ConfinedPath, String> {
    if !path.is_absolute() || !supplied_root.is_absolute() {
        return Err(format!("{option} must be absolute"));
    }
    let supplied_root = normalize_path(supplied_root).map_err(|error| error.to_string())?;
    let path = normalize_path(path).map_err(|error| error.to_string())?;
    let relative = path
        .strip_prefix(&supplied_root)
        .map_err(|_| format!("{option} escapes its trusted root"))?;
    if relative.as_os_str().is_empty() {
        return Err(format!("{option} must name a path below its trusted root"));
    }
    root.confine(relative, intent)
        .map_err(|error| format!("{option}: {error}"))
}

/// Read a bounded UTF-8 artifact through a confined descriptor.
///
/// # Errors
///
/// Returns an error when the artifact is outside the authorized root, cannot
/// be opened safely, exceeds `limit`, or contains non-UTF-8 bytes.
pub fn read_expected_file(
    path: &Path,
    supplied_root: &Path,
    root: &TemporaryRoot,
    option: &str,
    limit: u64,
) -> Result<String, String> {
    let confined = confine_session_path(path, supplied_root, root, PathIntent::Read, option)?;
    let file = open_confined_read(&confined).map_err(|error| error.to_string())?;
    let mut bytes = Vec::new();
    file.take(limit.saturating_add(1))
        .read_to_end(&mut bytes)
        .map_err(|error| error.to_string())?;
    if u64::try_from(bytes.len()).unwrap_or(u64::MAX) > limit {
        return Err(format!("{option} exceeds its byte limit"));
    }
    String::from_utf8(bytes).map_err(|_| format!("{option} must be valid UTF-8"))
}

/// Atomically write a private UTF-8 artifact through a confined descriptor.
///
/// # Errors
///
/// Returns an error when the output is outside the authorized root or cannot
/// be written with owner-only permissions.
pub fn write_private_file(
    path: &Path,
    text: &str,
    supplied_root: &Path,
    root: &TemporaryRoot,
) -> Result<(), String> {
    let confined = confine_session_path(path, supplied_root, root, PathIntent::Write, "output")?;
    atomic_write_utf8(&confined, text, 0o600).map_err(|error| error.to_string())
}
