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
    path::{Path, PathBuf},
    sync::{Mutex, PoisonError},
    time::Duration,
};

use larch_core::{
    ChildEnvironment, ExternalProgram, LarchProgram, ProcessOutput, is_valid_plugin_root_value,
};

use crate::child_process::{bounded_request, bounded_request_in, run_bounded};

const PLUGIN_ROOT_ENV: &str = "CLAUDE_PLUGIN_ROOT";
const VERIFIED_LARCH_TIMEOUT: Duration = Duration::from_secs(600);
const VERIFIED_LARCH_SHUTDOWN_GRACE: Duration = Duration::from_secs(5);
const VERIFIED_LARCH_OUTPUT_LIMIT: usize = 256 * 1024;

/// Session-derived child environment used by later nested Rust commands.
static SESSION_ENVIRONMENT: Mutex<Vec<(ChildEnvironment, OsString)>> = Mutex::new(Vec::new());

/// Publish session-derived rows for later verified larch subprocesses.
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

/// Explicit context read by the current nested larch composition graph.
///
/// The shared runner clears every other ambient variable, while this allowlist
/// preserves session placement, operator-selected model/probe settings, and
/// vendor credentials that the previously inherited first-party call used.
const VERIFIED_LARCH_CONTEXT: &[ChildEnvironment] = &[
    ChildEnvironment::AnthropicApiKey,
    ChildEnvironment::ClaudePluginData,
    ChildEnvironment::ClaudePluginOptionCodexEffort,
    ChildEnvironment::ClaudePluginOptionCodexModel,
    ChildEnvironment::ClaudePluginOptionCursorModel,
    ChildEnvironment::ClaudeProjectDir,
    ChildEnvironment::ClaudeSubprocessHookExempt,
    ChildEnvironment::CodexHome,
    ChildEnvironment::CursorApiKey,
    ChildEnvironment::CursorConfigDir,
    ChildEnvironment::DesignTmpdir,
    ChildEnvironment::GhConfigDir,
    ChildEnvironment::ImplementTmpdir,
    ChildEnvironment::LarchBinary,
    ChildEnvironment::LarchClaudePid,
    ChildEnvironment::LarchClaudeSourceFile,
    ChildEnvironment::LarchCodexEffort,
    ChildEnvironment::LarchCodexFixModel,
    ChildEnvironment::LarchCodexModel,
    ChildEnvironment::LarchCodexReviewModel,
    ChildEnvironment::LarchCodexVoteModel,
    ChildEnvironment::LarchCursorModel,
    ChildEnvironment::LarchReviewerPrune,
    ChildEnvironment::LarchReviewerStragglerMultiple,
    ChildEnvironment::LarchReviewerStragglerFloorSeconds,
    ChildEnvironment::LarchReviewerStragglerMaxSeconds,
    ChildEnvironment::LarchUniqueFinderBonus,
    ChildEnvironment::LarchExternalAuthRetries,
    ChildEnvironment::LarchExternalHealthCheckTimeout,
    ChildEnvironment::LarchProbeNegativeTtlSeconds,
    ChildEnvironment::LarchProbeRetries,
    ChildEnvironment::LarchProbeTimeoutRetries,
    ChildEnvironment::LarchProbeTimeoutSeconds,
    ChildEnvironment::LarchProbeTtlSeconds,
    ChildEnvironment::LarchQuietDisable,
    ChildEnvironment::LarchRenderCacheDir,
    ChildEnvironment::LarchTimingLedger,
    ChildEnvironment::LarchTimingSkill,
    ChildEnvironment::LarchTokenLedger,
    ChildEnvironment::LarchTokenSessionId,
    ChildEnvironment::LarchStatuslineDisable,
    ChildEnvironment::NoOpenBrowser,
    ChildEnvironment::OpenAiApiKey,
    ChildEnvironment::RepoRoot,
    ChildEnvironment::ResearchTmpdir,
    ChildEnvironment::ReviewTmpdir,
    ChildEnvironment::SessionEnvPath,
    ChildEnvironment::SessionTmpdir,
    ChildEnvironment::XdgCacheHome,
    ChildEnvironment::XdgConfigHome,
];

/// Reduce a composed process result to `(exit_code, stdout)`.
///
/// Nested-composition callers that branch on a verified larch command's exit
/// code and captured stdout share this projection: a missing exit code and a
/// start failure both read as `1`.
#[must_use]
pub fn code_and_stdout(result: Result<ProcessOutput, String>) -> (i32, String) {
    match result {
        Ok(output) => (
            output.status().code().unwrap_or(1),
            String::from_utf8_lossy(output.stdout()).into_owned(),
        ),
        Err(_error) => (1, String::new()),
    }
}

/// Resolve and run the verified larch entrypoint with the supplied command.
///
/// # Errors
///
/// Returns a concise diagnostic when the active plugin root is unavailable or
/// the bootstrap process cannot be started. A non-zero child exit is returned
/// in [`ProcessOutput`] so the caller can preserve that command's own contract.
pub fn run_verified_larch(arguments: &[OsString]) -> Result<ProcessOutput, String> {
    run_verified_larch_with_environment(arguments, &[])
}

/// Run verified larch with a caller-owned deadline for a composed phase.
///
/// # Errors
/// Returns the same resolution and process errors as [`run_verified_larch`].
pub fn run_verified_larch_with_timeout(
    arguments: &[OsString],
    timeout: Duration,
) -> Result<ProcessOutput, String> {
    run_verified_larch_with_options(arguments, &[], timeout)
}

/// Run verified larch with explicitly scoped environment overrides.
///
/// # Errors
/// Returns the same resolution and process errors as [`run_verified_larch`].
pub fn run_verified_larch_with_environment(
    arguments: &[OsString],
    environment: &[(ChildEnvironment, OsString)],
) -> Result<ProcessOutput, String> {
    run_verified_larch_with_options(arguments, environment, VERIFIED_LARCH_TIMEOUT)
}

/// Run verified larch from a caller-selected plugin root with explicitly
/// scoped environment overrides.
///
/// # Errors
/// Returns a concise diagnostic when `plugin_root` is not an absolute,
/// resolvable directory or the bootstrap process cannot be started.
pub fn run_verified_larch_from_root_with_environment(
    plugin_root: &Path,
    arguments: &[OsString],
    environment: &[(ChildEnvironment, OsString)],
) -> Result<ProcessOutput, String> {
    let root = validate_verified_plugin_root(plugin_root)?;
    run_verified_larch_at_root(&root, arguments, environment, None, VERIFIED_LARCH_TIMEOUT)
}

pub fn run_verified_larch_with_options(
    arguments: &[OsString],
    environment: &[(ChildEnvironment, OsString)],
    timeout: Duration,
) -> Result<ProcessOutput, String> {
    run_verified_larch_at(arguments, environment, None, timeout)
}

/// Run verified larch from a caller-validated repository directory.
///
/// # Errors
/// Returns the same resolution and process errors as
/// [`run_verified_larch_with_options`].
pub fn run_verified_larch_with_options_in(
    arguments: &[OsString],
    environment: &[(ChildEnvironment, OsString)],
    working_directory: &Path,
    timeout: Duration,
) -> Result<ProcessOutput, String> {
    run_verified_larch_at(arguments, environment, Some(working_directory), timeout)
}

fn run_verified_larch_at(
    arguments: &[OsString],
    environment: &[(ChildEnvironment, OsString)],
    working_directory: Option<&Path>,
    timeout: Duration,
) -> Result<ProcessOutput, String> {
    let root = plugin_root()?;
    run_verified_larch_at_root(&root, arguments, environment, working_directory, timeout)
}

fn run_verified_larch_at_root(
    root: &Path,
    arguments: &[OsString],
    environment: &[(ChildEnvironment, OsString)],
    working_directory: Option<&Path>,
    timeout: Duration,
) -> Result<ProcessOutput, String> {
    let script = root.join("scripts").join("larch.sh");
    if !script.is_file() || script.is_symlink() {
        return Err("CLAUDE_PLUGIN_ROOT does not contain a safe scripts/larch.sh".to_owned());
    }
    let program = LarchProgram::bootstrap(root)
        .map_err(|error| format!("could not select verified larch entrypoint: {error}"))?;
    let mut request = match working_directory {
        Some(directory) => bounded_request_in(
            ExternalProgram::Larch(program),
            arguments.iter().cloned(),
            directory,
            timeout,
            VERIFIED_LARCH_SHUTDOWN_GRACE,
            VERIFIED_LARCH_OUTPUT_LIMIT,
        ),
        None => bounded_request(
            ExternalProgram::Larch(program),
            arguments.iter().cloned(),
            timeout,
            VERIFIED_LARCH_SHUTDOWN_GRACE,
            VERIFIED_LARCH_OUTPUT_LIMIT,
        ),
    }?;
    for key in VERIFIED_LARCH_CONTEXT {
        if let Some(value) = env::var_os(key.name()) {
            request = request.with_environment(*key, value);
        }
    }
    request = request.with_environment(
        ChildEnvironment::ClaudePluginRoot,
        root.as_os_str().to_owned(),
    );
    for (key, value) in session_environment() {
        request = request.with_environment(key, value);
    }
    for (key, value) in environment {
        request = request.with_environment(*key, value.clone());
    }
    run_bounded(request)
        .map_err(|error| format!("could not start verified larch entrypoint: {error}"))
}

/// Resolve the active plugin root without falling back to the ambient cwd.
///
/// A production command must use the installed plugin it was launched from,
/// not a checkout that happens to be the process working directory.
pub fn plugin_root() -> Result<PathBuf, String> {
    let root =
        plugin_root_directory().ok_or_else(|| "CLAUDE_PLUGIN_ROOT is required".to_owned())?;
    validate_plugin_root_directory(&root)
}

/// Resolve and validate an explicitly selected plugin root.
///
/// # Errors
/// Returns a concise diagnostic when `root` is relative, missing, or not a
/// directory.
pub fn validate_plugin_root_directory(root: &Path) -> Result<PathBuf, String> {
    if !root.is_absolute() {
        return Err("CLAUDE_PLUGIN_ROOT must be an absolute path".to_owned());
    }
    let root = fs::canonicalize(root)
        .map_err(|error| format!("could not resolve CLAUDE_PLUGIN_ROOT: {error}"))?;
    let metadata = fs::symlink_metadata(&root)
        .map_err(|error| format!("could not inspect CLAUDE_PLUGIN_ROOT: {error}"))?;
    if !metadata.is_dir() {
        return Err("CLAUDE_PLUGIN_ROOT must name a directory".to_owned());
    }
    Ok(root)
}

/// Resolve an explicitly selected plugin root and require its safe bootstrap
/// script.
///
/// # Errors
/// Returns the directory-validation diagnostic or reports that `scripts/larch.sh`
/// is missing, non-regular, or a symlink.
pub fn validate_verified_plugin_root(root: &Path) -> Result<PathBuf, String> {
    let root = validate_plugin_root_directory(root)?;
    let script = root.join("scripts").join("larch.sh");
    if !script.is_file() || script.is_symlink() {
        return Err("CLAUDE_PLUGIN_ROOT does not contain a safe scripts/larch.sh".to_owned());
    }
    Ok(root)
}

/// Resolve the active plugin root from the wrapper environment or executable.
///
/// Installed binaries live at `<root>/bin/larch`, so the executable fallback
/// stays within the verified runtime layout and never consults the ambient
/// working directory.
#[must_use]
pub fn plugin_root_directory() -> Option<PathBuf> {
    let declared = env::var(PLUGIN_ROOT_ENV).unwrap_or_default();
    if is_valid_plugin_root_value(&declared) {
        return Some(PathBuf::from(declared));
    }
    env::current_exe()
        .ok()?
        .parent()?
        .parent()
        .map(Path::to_path_buf)
}
