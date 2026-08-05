//! Parallel-safe Cursor configuration isolation for vendor launches.
//!
//! Creates a private config directory and optionally copies the operator's
//! `cli-config.json`. It never mutates process environment; callers inject
//! [`ChildEnvironment::CursorConfigDir`] into the child request.

use crate::filesystem::{PathSafetyError, SecureTempDir, TemporaryRoot};
use larch_core::{ChildEnvironment, env};
use std::{ffi::OsString, fs, path::Path};

const CURSOR_CFG_PREFIX: &str = "larch-cursor-cfg-";

/// Owned Cursor configuration directory cleaned up on drop.
#[derive(Debug)]
pub struct CursorConfigContext {
    dir: SecureTempDir,
}

impl CursorConfigContext {
    /// Create an isolated config directory under `temp_root`.
    ///
    /// When `home/.cursor/cli-config.json` exists as a regular file, copy it
    /// best-effort into the isolated directory. Copy failures are suppressed so
    /// isolation still succeeds without a source config.
    ///
    /// # Errors
    /// Returns when the temporary root is unsafe or directory creation fails.
    pub fn create(temp_root: &TemporaryRoot, home: &Path) -> Result<Self, PathSafetyError> {
        let dir = SecureTempDir::create(temp_root, CURSOR_CFG_PREFIX)?;
        let source = home.join(".cursor").join("cli-config.json");
        if let Ok(metadata) = fs::symlink_metadata(&source)
            && metadata.is_file()
            && !metadata.file_type().is_symlink()
        {
            let destination = dir.path().join("cli-config.json");
            let _ = fs::copy(&source, &destination);
        }
        Ok(Self { dir })
    }

    /// Absolute path of the isolated configuration directory.
    #[must_use]
    pub fn path(&self) -> &Path {
        self.dir.path()
    }

    /// Typed child-environment override for [`ProcessRequest`](larch_core::ProcessRequest).
    #[must_use]
    pub fn child_environment(&self) -> (ChildEnvironment, OsString) {
        (
            ChildEnvironment::CursorConfigDir,
            self.path().as_os_str().to_owned(),
        )
    }

    /// Environment variable name injected into vendor children.
    #[must_use]
    pub const fn env_name() -> &'static str {
        env::CURSOR_CONFIG_DIR
    }

    /// Revalidate and remove the directory now.
    ///
    /// # Errors
    /// Returns when confinement revalidation or cleanup fails.
    pub fn close(self) -> Result<(), PathSafetyError> {
        self.dir.close()
    }
}

/// Test helper: create a temporary root and build a context beneath it.
///
/// # Errors
/// Propagates temporary-root resolution and context creation failures.
#[cfg(test)]
fn create_for_tests(
    home: &Path,
) -> Result<(tempfile::TempDir, CursorConfigContext), std::io::Error> {
    let temp = tempfile::tempdir()?;
    let root = TemporaryRoot::resolve(Some(temp.path()))
        .map_err(|error| std::io::Error::other(error.to_string()))?;
    let context = CursorConfigContext::create(&root, home)
        .map_err(|error| std::io::Error::other(error.to_string()))?;
    Ok((temp, context))
}

#[cfg(test)]
mod tests {
    use super::create_for_tests;
    use larch_core::{ChildEnvironment, env};
    use std::fs;

    #[test]
    fn copies_regular_config_and_exposes_child_env_without_process_mutation() {
        let home = tempfile::tempdir().expect("home");
        let cursor_dir = home.path().join(".cursor");
        fs::create_dir_all(&cursor_dir).expect("cursor dir");
        let source = cursor_dir.join("cli-config.json");
        fs::write(&source, "{\"approvalMode\":\"allow\"}\n").expect("write config");
        let before = std::env::var_os(env::CURSOR_CONFIG_DIR);

        let (_root, context) = create_for_tests(home.path()).expect("context");
        let copied = context.path().join("cli-config.json");
        assert!(copied.is_file());
        assert_eq!(
            fs::read_to_string(&copied).expect("read copy"),
            "{\"approvalMode\":\"allow\"}\n"
        );
        let (key, value) = context.child_environment();
        assert_eq!(key, ChildEnvironment::CursorConfigDir);
        assert_eq!(key.name(), env::CURSOR_CONFIG_DIR);
        assert_eq!(value, context.path().as_os_str());
        assert_eq!(std::env::var_os(env::CURSOR_CONFIG_DIR), before);
    }

    #[test]
    fn missing_source_config_still_isolates() {
        let home = tempfile::tempdir().expect("home");
        let (_root, context) = create_for_tests(home.path()).expect("context");
        assert!(!context.path().join("cli-config.json").exists());
        assert!(context.path().is_dir());
    }

    #[test]
    fn cleanup_removes_directory() {
        let home = tempfile::tempdir().expect("home");
        let (_root, context) = create_for_tests(home.path()).expect("context");
        let path = context.path().to_path_buf();
        assert!(path.is_dir());
        context.close().expect("close");
        assert!(!path.exists());
    }

    #[test]
    fn symlink_source_is_not_copied() {
        let home = tempfile::tempdir().expect("home");
        let cursor_dir = home.path().join(".cursor");
        fs::create_dir_all(&cursor_dir).expect("cursor dir");
        let outside = home.path().join("outside.json");
        fs::write(&outside, "{}\n").expect("outside");
        #[cfg(unix)]
        {
            std::os::unix::fs::symlink(&outside, cursor_dir.join("cli-config.json"))
                .expect("symlink");
        }
        #[cfg(not(unix))]
        {
            let _ = outside;
            return;
        }
        let (_root, context) = create_for_tests(home.path()).expect("context");
        assert!(!context.path().join("cli-config.json").exists());
    }
}
