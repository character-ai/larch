//! `session` temp-directory lifecycle verbs.
//!
//! Each verb keeps the exit codes, stream routing, and diagnostic text its shell
//! and hook callers depend on. Ambient state — environment, clock, process
//! identity — is read here, at the composition root, and passed into the
//! adapter layer explicitly.

use crate::argparse_compat::{ParsedCommandLine, parse, write_stdout};
use larch_adapters::{
    CLEANUP_AUDIT_LOG_NAME, ImplementTmpdirQuery, NoopProcessObserver, TokioProcessRunner,
    append_cleanup_audit, is_allowed_session_tmpdir, parent_process_id, probe_process_command_name,
    remove_session_tmpdir, resolve_implement_tmpdir,
    runtime::{Cancellation, LarchRuntime},
    validate_design_tmpdir, write_session_id,
};
use larch_core::{
    allowed_session_roots, cleanup_cache_sessions_root, implement_session_roots,
    implement_tmpdir_ttl, redact,
};
use std::{
    env,
    ffi::{OsStr, OsString},
    path::{Path, PathBuf},
    process::ExitCode,
    sync::Arc,
    time::{SystemTime, UNIX_EPOCH},
};

const PLUGIN_ROOT_TEMPLATE_LITERAL: &str = "${CLAUDE_PLUGIN_ROOT}";
const REQUIRE_PLUGIN_ROOT_USAGE: &str = "usage: session require-plugin-root";
const VALIDATE_DESIGN_TMPDIR_USAGE: &str = "usage: session validate-design-tmpdir [path]";
const WRITE_ID_USAGE: &str = "usage: session write-id [--output OUTPUT]";
const CLEANUP_TMPDIR_USAGE: &str = "usage: session cleanup-tmpdir [--dir DIR] [pos]";
const RESOLVE_IMPLEMENT_TMPDIR_USAGE: &str = "usage: session resolve-implement-tmpdir [--cwd CWD]";
const TMP_FALLBACK: &str = "/tmp";

/// Fail closed when `CLAUDE_PLUGIN_ROOT` is absent or left as its template literal.
pub fn require_plugin_root(arguments: &[OsString]) -> ExitCode {
    if !arguments.is_empty() {
        return usage_error(
            REQUIRE_PLUGIN_ROOT_USAGE,
            "session require-plugin-root",
            &format!(
                "unrecognized arguments: {}",
                crate::argparse_compat::join_arguments(arguments)
            ),
            2,
        );
    }
    check_plugin_root().map_or(ExitCode::SUCCESS, |message| {
        eprintln!("{message}");
        ExitCode::FAILURE
    })
}

/// Validate a `/design` temp directory against the resolved session allowlist.
pub fn validate_design_tmpdir_command(arguments: &[OsString]) -> ExitCode {
    let parsed = parse(arguments, &[], 1);
    if let Some(error) = parsed.error() {
        return usage_error(
            VALIDATE_DESIGN_TMPDIR_USAGE,
            "session validate-design-tmpdir",
            &error,
            2,
        );
    }
    if let Some(message) = check_plugin_root() {
        eprintln!("{message}");
        return ExitCode::FAILURE;
    }
    let candidate = parsed.positional(0).unwrap_or_else(|| OsStr::new(""));
    match validate_design_tmpdir(
        &candidate.to_string_lossy(),
        env::var_os("TMPDIR").as_deref(),
        &cache_sessions_root(),
    ) {
        Ok(()) => ExitCode::SUCCESS,
        Err(message) => {
            eprintln!("{message}");
            ExitCode::from(2)
        }
    }
}

/// Idempotently publish a session identity below an allowed session root.
pub fn write_id(arguments: &[OsString]) -> ExitCode {
    let parsed = parse(arguments, &["--output"], 0);
    if let Some(error) = parsed.error() {
        emit_usage_error(WRITE_ID_USAGE, "session write-id", &error);
        return write_id_failure("unknown flag");
    }
    let output = parsed.value("--output").unwrap_or_else(|| OsStr::new(""));
    if output.is_empty() {
        return write_id_failure("--output is required");
    }
    match write_session_id(Path::new(output), &allowed_roots()) {
        Ok(_outcome) => ExitCode::SUCCESS,
        Err(message) => write_id_failure(&message),
    }
}

/// Print the live `/implement` temp directory for one clone, or nothing.
pub fn resolve_implement_tmpdir_command(arguments: &[OsString]) -> ExitCode {
    let parsed = parse(arguments, &["--cwd"], 0);
    if let Some(error) = parsed.error() {
        emit_usage_error(
            RESOLVE_IMPLEMENT_TMPDIR_USAGE,
            "session resolve-implement-tmpdir",
            &error,
        );
        // The legacy verb caught argparse's SystemExit and reported its code.
        eprintln!("resolve-implement-tmpdir: 2");
        return ExitCode::FAILURE;
    }
    let hook_cwd = parsed
        .value("--cwd")
        .unwrap_or_else(|| OsStr::new(""))
        .to_string_lossy()
        .into_owned();
    let session_id = env::var("LARCH_TOKEN_SESSION_ID").unwrap_or_default();
    let resolved = resolve_implement_tmpdir(&ImplementTmpdirQuery {
        hook_cwd: &hook_cwd,
        roots: &implement_session_roots(
            env::var_os("XDG_CACHE_HOME").as_deref(),
            env::var_os("HOME").as_deref(),
        ),
        session_id: &session_id,
        ttl_seconds: implement_tmpdir_ttl(
            env::var("LARCH_IMPLEMENT_TMPDIR_TTL_SECONDS")
                .ok()
                .as_deref(),
        ),
        now: unix_seconds(),
    });
    if resolved.is_empty() {
        return ExitCode::SUCCESS;
    }
    write_stdout(&resolved)
}

/// Remove a session temp directory after recording the invocation.
pub fn cleanup_tmpdir(arguments: &[OsString]) -> ExitCode {
    let parsed = parse(arguments, &["--dir"], 1);
    if let Some(error) = parsed.error() {
        emit_usage_error(CLEANUP_TMPDIR_USAGE, "session cleanup-tmpdir", &error);
        return breadcrumb_failure("Usage: cleanup-tmpdir.sh --dir <path>");
    }
    let target = cleanup_target(&parsed);
    if target.is_empty() {
        return breadcrumb_failure("ERROR: --dir is required and must be non-empty");
    }
    if !is_allowed_session_tmpdir(&target, &allowed_roots()) {
        return breadcrumb_failure(&format!(
            "ERROR: --dir must be under /tmp/, /private/tmp/, /var/folders/, or {}/ (got: {target})",
            cache_sessions_root().display()
        ));
    }
    append_cleanup_audit(&cleanup_audit_log(), &invoking_command_name(), &target);
    match remove_session_tmpdir(Path::new(&target)) {
        Ok(()) => ExitCode::SUCCESS,
        Err(message) => breadcrumb_failure(&format!("ERROR: {message}")),
    }
}

fn cleanup_target(parsed: &ParsedCommandLine) -> String {
    let explicit = parsed.value("--dir").unwrap_or_else(|| OsStr::new(""));
    if explicit.is_empty() {
        return parsed
            .positional(0)
            .unwrap_or_else(|| OsStr::new(""))
            .to_string_lossy()
            .into_owned();
    }
    explicit.to_string_lossy().into_owned()
}

/// Name the process that invoked this cleanup, or the unknown marker.
///
/// The audit trail records who asked for a removal. No portable API exposes a
/// parent's command name, so this goes through the allowlisted host-utility
/// probe; any failure degrades to `?` rather than blocking cleanup.
fn invoking_command_name() -> String {
    const UNKNOWN: &str = "?";
    let Ok(runtime) = LarchRuntime::current_thread() else {
        return UNKNOWN.to_owned();
    };
    let Ok(working_directory) = env::current_dir() else {
        return UNKNOWN.to_owned();
    };
    let runner = TokioProcessRunner::new(Arc::new(NoopProcessObserver));
    runtime
        .block_on(probe_process_command_name(
            &runner,
            parent_process_id(),
            &working_directory,
            &Cancellation::new(),
        ))
        .unwrap_or_else(|| UNKNOWN.to_owned())
}

fn cleanup_audit_log() -> PathBuf {
    PathBuf::from(
        env::var_os("TMPDIR")
            .filter(|value| !value.is_empty())
            .unwrap_or_else(|| OsString::from(TMP_FALLBACK)),
    )
    .join(CLEANUP_AUDIT_LOG_NAME)
}

fn check_plugin_root() -> Option<String> {
    let value = env::var("CLAUDE_PLUGIN_ROOT").unwrap_or_default();
    if value.is_empty() {
        return Some("/design wrapper: CLAUDE_PLUGIN_ROOT is empty; abort".to_owned());
    }
    if value == PLUGIN_ROOT_TEMPLATE_LITERAL {
        return Some(format!(
            "/design wrapper: CLAUDE_PLUGIN_ROOT is the unexpanded template literal {PLUGIN_ROOT_TEMPLATE_LITERAL}; abort"
        ));
    }
    None
}

fn allowed_roots() -> [PathBuf; 5] {
    allowed_session_roots(
        env::var_os("XDG_CACHE_HOME").as_deref(),
        env::var_os("HOME").as_deref(),
    )
}

fn cache_sessions_root() -> PathBuf {
    cleanup_cache_sessions_root(
        env::var_os("XDG_CACHE_HOME").as_deref(),
        env::var_os("HOME").as_deref(),
    )
}

fn unix_seconds() -> i64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .ok()
        .and_then(|elapsed| i64::try_from(elapsed.as_secs()).ok())
        .unwrap_or_default()
}

/// Report a `write-id` failure on the machine-readable contract stream.
fn write_id_failure(reason: &str) -> ExitCode {
    let _ignored = write_stdout(&format!("FAILED=true\nERROR={reason}\n"));
    ExitCode::FAILURE
}

/// Report a breadcrumb-style diagnostic, redacted the way the writer redacts.
fn breadcrumb_failure(message: &str) -> ExitCode {
    eprintln!("{}", redact(message).text());
    ExitCode::FAILURE
}

/// Reproduce the two-line `argparse` usage-error block on stderr.
fn emit_usage_error(usage: &str, program: &str, error: &str) {
    eprintln!("{usage}\n{program}: error: {error}");
}

fn usage_error(usage: &str, program: &str, error: &str, code: u8) -> ExitCode {
    emit_usage_error(usage, program, error);
    ExitCode::from(code)
}
