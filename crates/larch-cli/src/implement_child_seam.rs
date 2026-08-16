//! The shared child seam the implement command owners compose through.
//!
//! Production behavior is the unwrapped call. A test build may substitute one
//! thread-local answer per composed child so a unit test never starts a
//! process and never depends on an installed plugin root.

use std::{ffi::OsString, path::PathBuf, time::Duration};

use larch_core::{ChildEnvironment, ProcessOutput};

use crate::{
    python_verb::run_python_verb,
    runtime_entrypoint::{plugin_root, run_verified_larch_with_environment},
};

#[cfg(test)]
type PythonHook =
    std::sync::Arc<dyn Fn(&[OsString]) -> Result<ProcessOutput, String> + Send + Sync>;
#[cfg(test)]
type LarchHook = std::sync::Arc<
    dyn Fn(&[OsString], &[(ChildEnvironment, OsString)]) -> Result<ProcessOutput, String>
        + Send
        + Sync,
>;

#[cfg(test)]
std::thread_local! {
    static TEST_PYTHON: std::cell::RefCell<Option<PythonHook>> = const { std::cell::RefCell::new(None) };
    static TEST_LARCH: std::cell::RefCell<Option<LarchHook>> = const { std::cell::RefCell::new(None) };
    static TEST_PLUGIN_ROOT: std::cell::RefCell<Option<PathBuf>> = const { std::cell::RefCell::new(None) };
}

/// Run one still-Python sibling through the shared migration-era seam.
pub fn delegate_python(
    arguments: Vec<OsString>,
    timeout: Duration,
) -> Result<ProcessOutput, String> {
    #[cfg(test)]
    if let Some(hook) = TEST_PYTHON.with(|slot| slot.borrow().clone()) {
        return hook(&arguments);
    }
    run_python_verb(arguments, timeout)
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

/// Resolve the active plugin root that owns the still-Python siblings.
pub fn resolve_plugin_root() -> Result<PathBuf, String> {
    #[cfg(test)]
    if let Some(root) = TEST_PLUGIN_ROOT.with(|slot| slot.borrow().clone()) {
        return Ok(root);
    }
    plugin_root()
}

/// Answer every composed Python sibling from `hook` for this thread.
#[cfg(test)]
pub fn install_python(
    hook: impl Fn(&[OsString]) -> Result<ProcessOutput, String> + Send + Sync + 'static,
) {
    TEST_PYTHON.with(|slot| *slot.borrow_mut() = Some(std::sync::Arc::new(hook)));
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
    TEST_PYTHON.with(|slot| *slot.borrow_mut() = None);
    TEST_LARCH.with(|slot| *slot.borrow_mut() = None);
    TEST_PLUGIN_ROOT.with(|slot| *slot.borrow_mut() = None);
}
