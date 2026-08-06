//! Filesystem effects for the session environment and run-flag writers.
//!
//! Confinement, atomic publication, and symlink handling all route through the
//! [`crate::filesystem`] and [`crate::file_io`] owners rather than re-deriving
//! path safety. Every entry point takes its roots and targets from the caller so
//! the composition root keeps ownership of ambient state.

use crate::{PathIntent, TemporaryRoot, atomic_write_utf8};
use larch_core::{WRITE_DESIGN_ENV_KEYS, parse_allowlisted_env_line};
use std::{
    fs,
    path::{Path, PathBuf},
};

/// Publish `text` to `output` atomically with private-by-default permissions.
///
/// Reproduces the legacy writer's guarantees: no symlink anywhere on the path,
/// a confined destination, and a temporary file replaced by rename so a crash
/// between write and rename leaves the prior file intact.
///
/// # Errors
///
/// Returns the operator diagnostic when any path component is a symlink, the
/// parent is unusable, or publication fails.
pub fn write_confined_file(
    output: &Path,
    text: &str,
    mode: u32,
    label: &str,
) -> Result<(), String> {
    let absolute = absolute_lexical(output);
    assert_no_symlink_path_or_ancestors(&absolute)?;
    let parent = parent_directory(&absolute);
    let root = TemporaryRoot::resolve(Some(&parent))
        .map_err(|error| format!("output parent is not a writable directory: {error}"))?;
    let confined = root
        .confine(&absolute, PathIntent::Write)
        .map_err(|error| format!("refusing unsafe {label} target: {error}"))?;
    atomic_write_utf8(&confined, text, mode).map_err(|error| format!("{error}"))
}

/// Create `path` and every missing ancestor.
///
/// # Errors
///
/// Returns the operator diagnostic when directory creation fails.
pub fn create_directories(path: &Path) -> Result<(), String> {
    fs::create_dir_all(path).map_err(|error| format!("{}: {error}", path.display()))
}

/// Refuse a path whose leaf or any ancestor is a symlink.
///
/// # Errors
///
/// Returns the operator diagnostic naming the first symlinked component.
pub fn assert_no_symlink_path_or_ancestors(path: &Path) -> Result<(), String> {
    let mut current = path;
    loop {
        if fs::symlink_metadata(current).is_ok_and(|data| data.file_type().is_symlink()) {
            return Err(format!(
                "refusing symlinked path or ancestor: {}",
                current.display()
            ));
        }
        match current.parent() {
            Some(parent) if parent != current => current = parent,
            _ => return Ok(()),
        }
    }
}

/// Refuse a design current-env link whose parent chain crosses a symlink.
///
/// The link itself is expected to be a symlink, so only its ancestors are
/// checked, matching the legacy `_validate_design_current_env_link` guard.
///
/// # Errors
///
/// Returns the operator diagnostic naming the first symlinked ancestor.
pub fn assert_no_symlink_ancestors(path: &Path) -> Result<(), String> {
    let mut ancestor = parent_directory(path);
    loop {
        if fs::symlink_metadata(&ancestor).is_ok_and(|data| data.file_type().is_symlink()) {
            return Err(format!(
                "refusing symlinked ancestor for design current-env link: {}",
                ancestor.display()
            ));
        }
        match ancestor.parent() {
            Some(parent) if parent != ancestor => ancestor = parent.to_path_buf(),
            _ => return Ok(()),
        }
    }
}

/// Atomically repoint `link` at `target` through a temporary sibling symlink.
///
/// # Errors
///
/// Returns the operator diagnostic when the temporary link cannot be created or
/// renamed into place.
pub fn publish_symlink(link: &Path, target: &Path, process_id: u32) -> Result<(), String> {
    let name = link
        .file_name()
        .map(|name| name.to_string_lossy().into_owned())
        .unwrap_or_default();
    let temporary = link.with_file_name(format!(".{name}.tmp.{process_id}"));
    match fs::remove_file(&temporary) {
        Ok(()) => {}
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => {}
        Err(error) => return Err(format!("{}: {error}", temporary.display())),
    }
    std::os::unix::fs::symlink(target, &temporary)
        .map_err(|error| format!("{}: {error}", temporary.display()))?;
    fs::rename(&temporary, link).map_err(|error| format!("{}: {error}", link.display()))
}

/// Remove `path` when it exists, tolerating an already-absent target.
///
/// A dangling symlink counts as present so a stale pointer is still cleared.
///
/// # Errors
///
/// Returns the operator diagnostic when removal fails.
pub fn remove_file_if_present(path: &Path) -> Result<(), String> {
    if fs::symlink_metadata(path).is_err() {
        return Ok(());
    }
    match fs::remove_file(path) {
        Ok(()) => Ok(()),
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => Ok(()),
        Err(error) => Err(format!("{}: {error}", path.display())),
    }
}

/// Recover the last `export KEY=true|false` row from a prior design env file.
///
/// Reading is best effort by design: an absent prior file recovers nothing.
///
/// # Errors
///
/// Returns the operator diagnostic when the file carries a carriage return.
pub fn recover_prior_bool(prior_file: &Path, key: &str) -> Result<String, String> {
    let Some(text) = read_prior_env_text(prior_file)? else {
        return Ok(String::new());
    };
    let mut found = String::new();
    for line in text.split('\n') {
        for candidate in ["true", "false"] {
            if line == format!("export {key}={candidate}") {
                candidate.clone_into(&mut found);
            }
        }
    }
    Ok(found)
}

/// Recover the last allowlisted value for `key` from a prior design env file.
///
/// # Errors
///
/// Returns the operator diagnostic when the file carries a carriage return.
pub fn recover_prior_design_value(prior_file: &Path, key: &str) -> Result<String, String> {
    let Some(text) = read_prior_env_text(prior_file)? else {
        return Ok(String::new());
    };
    let mut found = String::new();
    for line in text.split('\n') {
        if let Some((parsed_key, value)) = parse_allowlisted_env_line(
            line,
            &WRITE_DESIGN_ENV_KEYS,
            Some(larch_core::KeyPolicy::Environment),
            true,
        ) && parsed_key == key
        {
            found = value;
        }
    }
    Ok(found)
}

/// Resolve a PID-keyed design session-env symlink to a trusted regular file.
///
/// Returns `None` when the path is not a symlink, its ancestors are unsafe, or
/// the resolved target is not a regular file.
#[must_use]
pub fn resolve_trusted_design_env_source(path: &Path) -> Option<PathBuf> {
    if !fs::symlink_metadata(path).is_ok_and(|data| data.file_type().is_symlink()) {
        return None;
    }
    assert_no_symlink_ancestors(path).ok()?;
    let resolved = fs::canonicalize(path).ok()?;
    fs::metadata(&resolved)
        .is_ok_and(|data| data.is_file())
        .then_some(resolved)
}

/// Return whether `path` names an existing directory.
#[must_use]
pub fn is_directory(path: &Path) -> bool {
    fs::metadata(path).is_ok_and(|data| data.is_dir())
}

/// Return whether `path` names an existing regular file.
#[must_use]
pub fn is_regular_file(path: &Path) -> bool {
    fs::metadata(path).is_ok_and(|data| data.is_file())
}

/// Return the deepest existing directory that would contain `path`.
#[must_use]
pub fn parent_directory(path: &Path) -> PathBuf {
    path.parent()
        .filter(|parent| !parent.as_os_str().is_empty())
        .map_or_else(|| PathBuf::from("."), Path::to_path_buf)
}

/// Return `path` made absolute against the process working directory.
#[must_use]
pub fn absolute_lexical(path: &Path) -> PathBuf {
    if path.is_absolute() {
        return path.to_path_buf();
    }
    std::env::current_dir().map_or_else(|_error| path.to_path_buf(), |cwd| cwd.join(path))
}

fn read_prior_env_text(prior_file: &Path) -> Result<Option<String>, String> {
    if !is_regular_file(prior_file) {
        return Ok(None);
    }
    let bytes = fs::read(prior_file).map_err(|error| format!("{error}"))?;
    let text = String::from_utf8_lossy(&bytes).into_owned();
    if text.contains('\r') {
        return Err(format!(
            "session env file contains carriage return: {}",
            prior_file.display()
        ));
    }
    Ok(Some(text))
}

#[cfg(test)]
mod tests {
    use super::{
        publish_symlink, recover_prior_bool, recover_prior_design_value, remove_file_if_present,
        resolve_trusted_design_env_source, write_confined_file,
    };
    use std::fs;
    use tempfile::tempdir;

    #[test]
    fn confined_publication_is_private_and_replaces_atomically() {
        let directory = tempdir().expect("fixture tempdir");
        let root = directory.path().canonicalize().expect("canonical fixture");
        let target = root.join("session-env.sh");

        write_confined_file(&target, "REPO=a/b\n", 0o600, "session-env").expect("first write");
        write_confined_file(&target, "REPO=c/d\n", 0o600, "session-env").expect("second write");

        assert_eq!(
            fs::read_to_string(&target).expect("published file"),
            "REPO=c/d\n"
        );
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt as _;
            assert_eq!(
                fs::metadata(&target)
                    .expect("metadata")
                    .permissions()
                    .mode()
                    & 0o777,
                0o600
            );
        }
        // No temporary sibling survives a successful publication.
        let leftovers = fs::read_dir(&root)
            .expect("read fixture root")
            .filter_map(Result::ok)
            .filter(|entry| entry.file_name().to_string_lossy().contains(".tmp"))
            .count();
        assert_eq!(leftovers, 0);
    }

    #[cfg(unix)]
    #[test]
    fn confined_publication_refuses_a_symlinked_destination() {
        let directory = tempdir().expect("fixture tempdir");
        let root = directory.path().canonicalize().expect("canonical fixture");
        fs::write(root.join("real"), "keep\n").expect("real file");
        let link = root.join("link");
        std::os::unix::fs::symlink(root.join("real"), &link).expect("destination symlink");

        let error = write_confined_file(&link, "REPO=a/b\n", 0o600, "session-env")
            .expect_err("symlinked destination must fail");

        assert!(
            error.starts_with("refusing symlinked path or ancestor: "),
            "{error}"
        );
        assert_eq!(
            fs::read_to_string(root.join("real")).expect("target untouched"),
            "keep\n"
        );
    }

    #[test]
    fn prior_recovery_takes_the_last_row_and_rejects_carriage_returns() {
        let directory = tempdir().expect("fixture tempdir");
        let prior = directory.path().join("source-env.sh");
        fs::write(
            &prior,
            "export CODEX_BINARY_FOUND=false\nexport CODEX_BINARY_FOUND=true\nexport LARCH_RUN_ID='run-9'\n",
        )
        .expect("prior env");

        assert_eq!(
            recover_prior_bool(&prior, "CODEX_BINARY_FOUND"),
            Ok("true".to_owned())
        );
        assert_eq!(
            recover_prior_design_value(&prior, "LARCH_RUN_ID"),
            Ok("run-9".to_owned())
        );
        assert_eq!(
            recover_prior_design_value(&prior, "REPO_ROOT"),
            Ok(String::new())
        );

        fs::write(&prior, "export CODEX_BINARY_FOUND=true\r\n").expect("malformed prior env");
        assert!(recover_prior_bool(&prior, "CODEX_BINARY_FOUND").is_err());
    }

    #[cfg(unix)]
    #[test]
    fn symlink_publication_replaces_a_prior_pointer_and_resolves_to_the_target() {
        let directory = tempdir().expect("fixture tempdir");
        let root = directory.path().canonicalize().expect("canonical fixture");
        let first = root.join("first.sh");
        let second = root.join("second.sh");
        fs::write(&first, "one\n").expect("first target");
        fs::write(&second, "two\n").expect("second target");
        let link = root.join("current-design-env-42.sh");

        publish_symlink(&link, &first, 4242).expect("first publish");
        publish_symlink(&link, &second, 4242).expect("second publish");

        assert_eq!(
            resolve_trusted_design_env_source(&link).expect("trusted source"),
            second
        );
        assert_eq!(resolve_trusted_design_env_source(&second), None);

        remove_file_if_present(&link).expect("remove pointer");
        assert!(fs::symlink_metadata(&link).is_err());
        remove_file_if_present(&link).expect("removing an absent pointer is a no-op");
    }
}
