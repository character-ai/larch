//! Shared resolver for a Rust command that must call another production
//! command through the verified plugin bootstrap.
//!
//! The migration intentionally has a small number of composition commands that
//! reuse an already-owned verb.  They must not guess at `bin/larch`: the shell
//! bootstrap owns first-use installation and version verification.

use std::{
    env,
    ffi::OsString,
    fs,
    path::PathBuf,
    process::{Command, Output},
};

const PLUGIN_ROOT_ENV: &str = "CLAUDE_PLUGIN_ROOT";

/// Resolve and run the verified larch entrypoint with the supplied command.
///
/// # Errors
///
/// Returns a concise diagnostic when the active plugin root is unavailable or
/// the bootstrap process cannot be started.  A non-zero child exit is returned
/// in [`Output`] so the caller can preserve that command's own contract.
pub fn run_verified_larch(arguments: &[OsString]) -> Result<Output, String> {
    let root = plugin_root()?;
    let script = root.join("scripts").join("larch.sh");
    if !script.is_file() || script.is_symlink() {
        return Err("CLAUDE_PLUGIN_ROOT does not contain a safe scripts/larch.sh".to_owned());
    }
    Command::new(&script)
        .args(arguments)
        .env(PLUGIN_ROOT_ENV, &root)
        .output()
        .map_err(|error| format!("could not start verified larch entrypoint: {error}"))
}

/// Resolve the active plugin root without falling back to the ambient cwd.
///
/// A production command must use the installed plugin it was launched from,
/// not a checkout that happens to be the process working directory.
pub fn plugin_root() -> Result<PathBuf, String> {
    let raw = env::var_os(PLUGIN_ROOT_ENV)
        .filter(|value| !value.is_empty())
        .ok_or_else(|| "CLAUDE_PLUGIN_ROOT is required".to_owned())?;
    let root = PathBuf::from(raw);
    if !root.is_absolute() {
        return Err("CLAUDE_PLUGIN_ROOT must be an absolute path".to_owned());
    }
    let root = fs::canonicalize(&root)
        .map_err(|error| format!("could not resolve CLAUDE_PLUGIN_ROOT: {error}"))?;
    let metadata = fs::symlink_metadata(&root)
        .map_err(|error| format!("could not inspect CLAUDE_PLUGIN_ROOT: {error}"))?;
    if !metadata.is_dir() {
        return Err("CLAUDE_PLUGIN_ROOT must name a directory".to_owned());
    }
    Ok(root)
}
