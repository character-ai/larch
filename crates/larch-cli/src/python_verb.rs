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
    sync::{Arc, Mutex, PoisonError},
    time::Duration,
};

use larch_adapters::{
    NoopProcessObserver, TokioProcessRunner,
    runtime::{Cancellation, LarchRuntime},
};
use larch_core::{
    ChildEnvironment, ExternalProcessRunner as _, ExternalProgram, ProcessOutput, ProcessRequest,
    PythonVerbProgram, is_valid_plugin_root_value,
};

/// Bounded capture for a delegated verb's standard streams.
const VERB_OUTPUT_LIMIT: usize = 256 * 1024;

/// Session-derived child-environment rows every later delegated verb inherits.
///
/// A launcher can learn a session identity from files rather than from its own
/// environment. Publishing those rows here reaches the delegated verbs without
/// mutating this process's environment, which the workspace forbids.
static SESSION_ENVIRONMENT: Mutex<Vec<(ChildEnvironment, OsString)>> = Mutex::new(Vec::new());

/// Publish session-derived rows for every later delegated verb in this process.
///
/// Rows replace the same key from the ambient environment, matching the
/// hydration order the retired Python launchers used.
pub fn publish_session_environment(rows: Vec<(ChildEnvironment, OsString)>) {
    *SESSION_ENVIRONMENT
        .lock()
        .unwrap_or_else(PoisonError::into_inner) = rows;
}

fn session_environment() -> Vec<(ChildEnvironment, OsString)> {
    SESSION_ENVIRONMENT
        .lock()
        .unwrap_or_else(PoisonError::into_inner)
        .clone()
}

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
    let mut request = ProcessRequest::new(
        ExternalProgram::PythonVerb(program),
        arguments,
        working_directory,
        timeout,
        VERB_SHUTDOWN_GRACE,
        NonZeroUsize::new(VERB_OUTPUT_LIMIT).unwrap_or(NonZeroUsize::MIN),
    )
    .map_err(|error| error.to_string())?;
    // Legacy report verbs may invoke the operator-authenticated `gh` CLI.
    // Preserve only its non-secret configuration selectors; credential
    // environment variables remain excluded by the shared process policy.
    for key in [
        ChildEnvironment::ClaudePluginRoot,
        ChildEnvironment::ClaudePluginData,
        ChildEnvironment::DesignTmpdir,
        ChildEnvironment::GhConfigDir,
        ChildEnvironment::ImplementTmpdir,
        ChildEnvironment::LarchRenderCacheDir,
        ChildEnvironment::LarchTokenLedger,
        ChildEnvironment::LarchTokenSessionId,
        ChildEnvironment::LarchTimingLedger,
        ChildEnvironment::LarchTimingSkill,
        ChildEnvironment::ResearchTmpdir,
        ChildEnvironment::ReviewTmpdir,
        ChildEnvironment::SessionEnvPath,
        ChildEnvironment::XdgConfigHome,
    ] {
        if let Some(value) = env::var_os(key.name()) {
            request = request.with_environment(key, value);
        }
    }
    for (key, value) in session_environment() {
        request = request.with_environment(key, value);
    }
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

/// Record a vendor task's wall-clock through the still-Python timing writer.
pub fn record_vendor_timing(
    vendor: &str,
    task_kind: &str,
    start_s: impl std::fmt::Display,
    end_s: impl std::fmt::Display,
    output: &Path,
    exit_code: i32,
    status: &str,
) {
    run_python_verb_best_effort([
        OsString::from("timing"),
        OsString::from("record-vendor-task"),
        OsString::from("--vendor"),
        OsString::from(vendor),
        OsString::from("--task-kind"),
        OsString::from(task_kind),
        OsString::from("--start-s"),
        OsString::from(start_s.to_string()),
        OsString::from("--end-s"),
        OsString::from(end_s.to_string()),
        OsString::from("--output"),
        output.as_os_str().to_os_string(),
        OsString::from("--exit-code"),
        OsString::from(exit_code.to_string()),
        OsString::from("--status"),
        OsString::from(status),
    ]);
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
