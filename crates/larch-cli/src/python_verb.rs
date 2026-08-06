//! The single migration-era seam from a Rust-owned command to a Python verb.
//!
//! A Rust command frequently needs a sibling verb that Python still owns.
//! Routing every such call through this module keeps one owner for plugin-root
//! resolution and for the bounded process request, and gives the retirement
//! sweep one place to look when the last Python verb goes away.

use std::{
    env,
    ffi::OsString,
    num::NonZeroUsize,
    path::{Path, PathBuf},
    sync::Arc,
    time::Duration,
};

use larch_adapters::{
    NoopProcessObserver, TokioProcessRunner,
    runtime::{Cancellation, LarchRuntime},
};
use larch_core::{
    ExternalProcessRunner as _, ExternalProgram, ProcessOutput, ProcessRequest, PythonVerbProgram,
    is_valid_plugin_root_value,
};

/// Bounded capture for a delegated verb's standard streams.
const VERB_OUTPUT_LIMIT: usize = 256 * 1024;
/// Grace period before a delegated verb's process group is killed.
const VERB_SHUTDOWN_GRACE: Duration = Duration::from_secs(5);

/// Run one still-Python verb and return its bounded output.
///
/// # Errors
/// Returns a stable message when the plugin root, dispatcher, runtime, working
/// directory, request, or the verb itself fails.
pub fn run_python_verb(
    arguments: impl IntoIterator<Item = OsString>,
    timeout: Duration,
) -> Result<ProcessOutput, String> {
    let root =
        plugin_root_directory().ok_or_else(|| "cannot resolve the plugin root".to_owned())?;
    let program = PythonVerbProgram::new(&root).map_err(|error| error.to_string())?;
    let runtime = LarchRuntime::current_thread().map_err(|error| error.to_string())?;
    let working_directory = env::current_dir().map_err(|error| error.to_string())?;
    let request = ProcessRequest::new(
        ExternalProgram::PythonVerb(program),
        arguments,
        working_directory,
        timeout,
        VERB_SHUTDOWN_GRACE,
        NonZeroUsize::new(VERB_OUTPUT_LIMIT).unwrap_or(NonZeroUsize::MIN),
    )
    .map_err(|error| error.to_string())?;
    let runner = TokioProcessRunner::new(Arc::new(NoopProcessObserver));
    runtime
        .block_on(runner.run(request, &Cancellation::new()))
        .map_err(|error| error.message().to_owned())
}

/// Run one still-Python verb whose failure must not fail the caller.
///
/// Telemetry and accounting verbs use this: losing a usage record degrades a
/// report, while failing the launch would lose the vendor work it accounts for.
pub fn run_python_verb_best_effort(arguments: impl IntoIterator<Item = OsString>) {
    let _ignored = run_python_verb(arguments, Duration::from_secs(120));
}

/// Resolve the plugin root that owns the still-Python verb dispatcher.
pub fn plugin_root_directory() -> Option<PathBuf> {
    let declared = env::var("CLAUDE_PLUGIN_ROOT").unwrap_or_default();
    if is_valid_plugin_root_value(&declared) {
        return Some(PathBuf::from(declared));
    }
    // `<root>/bin/larch` is the only installed location, per I-Runtime-1.
    env::current_exe()
        .ok()?
        .parent()?
        .parent()
        .map(Path::to_path_buf)
}
