//! Shared, confined filesystem and identifier helpers for bootstrap Step 0.

use larch_adapters::{PathIntent, TemporaryRoot, atomic_write_utf8_in, remove_optional_file};
use std::{fs, path::Path};

pub fn valid_run_id(value: &str) -> bool {
    !value.is_empty()
        && value
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'.' | b'_' | b'-'))
}

pub fn write_session_text(tmpdir: &str, name: &str, text: &str, mode: u32) -> Result<(), String> {
    let root =
        TemporaryRoot::resolve(Some(Path::new(tmpdir))).map_err(|error| error.to_string())?;
    let target = root.path().join(name);
    atomic_write_utf8_in(&root, &target, text, false, mode).map_err(|error| error.to_string())
}

pub fn remove_session_file(tmpdir: &str, name: &str) -> Result<(), String> {
    let root =
        TemporaryRoot::resolve(Some(Path::new(tmpdir))).map_err(|error| error.to_string())?;
    let target = root.path().join(name);
    if fs::symlink_metadata(&target)
        .is_err_and(|error| error.kind() == std::io::ErrorKind::NotFound)
    {
        return Ok(());
    }
    let confined = root
        .confine(&target, PathIntent::Cleanup)
        .map_err(|error| error.to_string())?;
    remove_optional_file(confined.path()).map_err(|error| error.to_string())
}
