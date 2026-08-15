//! Shared resolver for a Rust command that must call another production
//! command through the verified plugin bootstrap.
//!
//! The migration intentionally has a small number of composition commands that
//! reuse an already-owned verb.  They must not guess at `bin/larch`: the shell
//! bootstrap owns first-use installation and version verification.

use std::{env, ffi::OsString, fs, path::PathBuf, time::Duration};

use larch_core::{ChildEnvironment, ExternalProgram, LarchProgram, ProcessOutput};

use crate::child_process::{bounded_request, run_bounded};

const PLUGIN_ROOT_ENV: &str = "CLAUDE_PLUGIN_ROOT";
const VERIFIED_LARCH_TIMEOUT: Duration = Duration::from_secs(600);
const VERIFIED_LARCH_SHUTDOWN_GRACE: Duration = Duration::from_secs(5);
const VERIFIED_LARCH_OUTPUT_LIMIT: usize = 256 * 1024;

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

fn run_verified_larch_with_options(
    arguments: &[OsString],
    environment: &[(ChildEnvironment, OsString)],
    timeout: Duration,
) -> Result<ProcessOutput, String> {
    let root = plugin_root()?;
    let script = root.join("scripts").join("larch.sh");
    if !script.is_file() || script.is_symlink() {
        return Err("CLAUDE_PLUGIN_ROOT does not contain a safe scripts/larch.sh".to_owned());
    }
    let program = LarchProgram::bootstrap(&root)
        .map_err(|error| format!("could not select verified larch entrypoint: {error}"))?;
    let mut request = bounded_request(
        ExternalProgram::Larch(program),
        arguments.iter().cloned(),
        timeout,
        VERIFIED_LARCH_SHUTDOWN_GRACE,
        VERIFIED_LARCH_OUTPUT_LIMIT,
    )?;
    for key in VERIFIED_LARCH_CONTEXT {
        if let Some(value) = env::var_os(key.name()) {
            request = request.with_environment(*key, value);
        }
    }
    request = request.with_environment(
        ChildEnvironment::ClaudePluginRoot,
        root.as_os_str().to_owned(),
    );
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
