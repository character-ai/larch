//! The shared child seam the implement command owners compose through.
//!
//! Production behavior is the unwrapped call. A test build may substitute one
//! thread-local answer per composed child so a unit test never starts a
//! process and never depends on an installed plugin root.

use std::{
    ffi::OsString,
    path::{Path, PathBuf},
    time::Duration,
};

use larch_core::{ChildEnvironment, DuplicatePolicy, KvDocument, ParseOptions, ProcessOutput};

use crate::runtime_entrypoint::{
    plugin_root, run_verified_larch_with_environment, run_verified_larch_with_options,
    run_verified_larch_with_options_in,
};

#[cfg(test)]
type LarchHook = std::sync::Arc<
    dyn Fn(&[OsString], &[(ChildEnvironment, OsString)]) -> Result<ProcessOutput, String>
        + Send
        + Sync,
>;

#[cfg(test)]
std::thread_local! {
    static TEST_LARCH: std::cell::RefCell<Option<LarchHook>> = const { std::cell::RefCell::new(None) };
    static TEST_PLUGIN_ROOT: std::cell::RefCell<Option<PathBuf>> = const { std::cell::RefCell::new(None) };
}

/// Decompose a delegated child's outcome into exit code, stdout, and stderr.
///
/// A seam failure reports exit 1 with the detail as newline-terminated stderr,
/// so a caller that persists these streams records why the child never ran
/// instead of an empty file.
#[must_use]
pub fn child_streams(result: &Result<ProcessOutput, String>) -> (i32, String, String) {
    match result {
        Ok(output) => (
            output.status().code().unwrap_or(1),
            String::from_utf8_lossy(output.stdout()).into_owned(),
            String::from_utf8_lossy(output.stderr()).into_owned(),
        ),
        Err(detail) => (1, String::new(), format!("{detail}\n")),
    }
}

/// Wait for one queued pull request through the Rust-owned merge driver.
pub fn delegate_merge_wait(
    number: u64,
    repository: &str,
    timeout: Duration,
) -> Result<ProcessOutput, String> {
    delegate_larch_with_options(
        &[
            "merge".into(),
            "wait".into(),
            "--pr".into(),
            number.to_string().into(),
            "--repo".into(),
            repository.into(),
        ],
        &[],
        timeout,
    )
}

/// Validate the Rust-owned merge wait command's terminal envelope.
pub fn verify_merge_wait(output: &ProcessOutput) -> Result<(), String> {
    if output.stdout_truncated() {
        return Err("merge queue wait output was truncated".to_owned());
    }
    let fields = KvDocument::parse(
        &String::from_utf8_lossy(output.stdout()),
        ParseOptions::legacy(),
    )
    .map(|document| document.select(DuplicatePolicy::Last))
    .map_err(|error| error.to_string())?;
    if output.status().success() && fields.get("MERGE_RESULT").map(String::as_str) == Some("merged")
    {
        return Ok(());
    }
    Err(fields
        .get("ERROR")
        .filter(|detail| !detail.is_empty())
        .cloned()
        .unwrap_or_else(|| "merge queue wait did not confirm the merge".to_owned()))
}

/// Run one already-owned larch command with explicit child-environment rows.
pub fn delegate_larch_with_environment(
    arguments: &[OsString],
    environment: &[(ChildEnvironment, OsString)],
) -> Result<ProcessOutput, String> {
    #[cfg(test)]
    if let Some(hook) = TEST_LARCH.with(|slot| slot.borrow().clone()) {
        return hook(arguments, environment);
    }
    run_verified_larch_with_environment(arguments, environment)
}

/// Run one already-owned larch command with scoped environment and deadline.
pub fn delegate_larch_with_options(
    arguments: &[OsString],
    environment: &[(ChildEnvironment, OsString)],
    timeout: Duration,
) -> Result<ProcessOutput, String> {
    #[cfg(test)]
    if let Some(hook) = TEST_LARCH.with(|slot| slot.borrow().clone()) {
        return hook(arguments, environment);
    }
    run_verified_larch_with_options(arguments, environment, timeout)
}

/// Run one already-owned larch command from a validated repository directory.
pub fn delegate_larch_with_options_in(
    arguments: &[OsString],
    environment: &[(ChildEnvironment, OsString)],
    working_directory: &Path,
    timeout: Duration,
) -> Result<ProcessOutput, String> {
    #[cfg(test)]
    if let Some(hook) = TEST_LARCH.with(|slot| slot.borrow().clone()) {
        return hook(arguments, environment);
    }
    run_verified_larch_with_options_in(arguments, environment, working_directory, timeout)
}

/// Resolve the active plugin root that owns the verified larch entrypoint.
pub fn resolve_plugin_root() -> Result<PathBuf, String> {
    #[cfg(test)]
    if let Some(root) = TEST_PLUGIN_ROOT.with(|slot| slot.borrow().clone()) {
        return Ok(root);
    }
    plugin_root()
}

/// Answer every composed larch command from `hook` for this thread.
#[cfg(test)]
pub fn install_larch(
    hook: impl Fn(&[OsString], &[(ChildEnvironment, OsString)]) -> Result<ProcessOutput, String>
    + Send
    + Sync
    + 'static,
) {
    TEST_LARCH.with(|slot| *slot.borrow_mut() = Some(std::sync::Arc::new(hook)));
}

/// Resolve the plugin root to `root` for this thread.
#[cfg(test)]
pub fn declare_plugin_root(root: &std::path::Path) {
    TEST_PLUGIN_ROOT.with(|slot| *slot.borrow_mut() = Some(root.to_path_buf()));
}

/// Restore every seam to its production answer for this thread.
#[cfg(test)]
pub fn clear_hooks() {
    TEST_LARCH.with(|slot| *slot.borrow_mut() = None);
    TEST_PLUGIN_ROOT.with(|slot| *slot.borrow_mut() = None);
}
