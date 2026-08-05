//! Filesystem-backed vendor failure diagnostics.
//!
//! Ordering, budgets, and redaction live in `larch_core::vendor_diagnostics`.
//! This module performs the reads and the confined writes those decisions need.

use std::{
    env, fmt,
    fmt::Write as _,
    path::{Path, PathBuf},
};

use larch_core::{
    FAILED_AGENT_STDERR_TAIL_BYTE_CAP, FAILED_AGENT_STDERR_TAIL_LINES, FailureDiagSource,
    FailureDiagWrite, LauncherArtifact, LauncherArtifactKind, LauncherArtifactPaths,
    LauncherExitArtifacts, StderrCaptureMode, UsageParseError, UsageTotals,
    VENDOR_FAILURE_DIAG_BYTE_CAP, VENDOR_FAILURE_DIAG_SECTION_LINES, compose_failure_diag,
    failed_agent_stderr_candidates, failure_diag_source_order, parse_codex_usage,
    plan_failure_diag_write, redact, render_failed_agent_stderr_tail, resolve_launcher_exit,
    stream_reset_history_entry,
};

use crate::{
    FileIoError, TemporaryRoot, atomic_write_utf8, atomic_write_utf8_in, read_optional_utf8_lossy,
    remove_optional_file,
};

/// Private mode for every diagnostic artifact this module publishes.
const DIAGNOSTIC_FILE_MODE: u32 = 0o600;
/// Sink path that is never read or truncated.
const NULL_DEVICE: &str = "/dev/null";

/// Why a Codex usage file could not be summarized.
#[derive(Debug)]
pub enum CodexUsageError {
    /// The events file could not be read.
    Io(FileIoError),
    /// The events stream could not produce totals.
    Parse(UsageParseError),
}

impl fmt::Display for CodexUsageError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Io(error) => write!(formatter, "{error}"),
            Self::Parse(error) => write!(formatter, "{error}"),
        }
    }
}

impl std::error::Error for CodexUsageError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match self {
            Self::Io(error) => Some(error),
            Self::Parse(error) => Some(error),
        }
    }
}

/// Read one launcher artifact, treating every non-regular path as absent.
///
/// # Errors
/// Returns [`FileIoError`] when an existing regular file cannot be read.
pub fn read_launcher_artifact(path: &Path) -> Result<LauncherArtifact, FileIoError> {
    Ok(read_optional_utf8_lossy(path)?
        .map_or_else(LauncherArtifact::missing, LauncherArtifact::present))
}

/// Sum the Codex usage events recorded in one events file.
///
/// # Errors
/// Returns [`CodexUsageError`] for an unreadable file, an absent or empty file,
/// or a stream that carries no usable totals.
pub fn parse_codex_usage_file(path: &Path) -> Result<UsageTotals, CodexUsageError> {
    let text = read_optional_utf8_lossy(path)
        .map_err(CodexUsageError::Io)?
        .ok_or(CodexUsageError::Parse(UsageParseError::EventsMissing))?;
    parse_codex_usage(&text).map_err(CodexUsageError::Parse)
}

/// Compose and atomically publish the collector's failure-log carrier.
///
/// Every source is read with the legacy replacement decoder. The final body is
/// redacted through the shared core owner before its private publication.
///
/// # Errors
/// Returns [`FileIoError`] when an input cannot be read or the confined output
/// cannot be published.
pub fn write_collector_failure_log(
    reviewer_file: Option<&Path>,
    structured_record: &str,
    output: &crate::ConfinedPath,
) -> Result<(), FileIoError> {
    let reviewer_label = reviewer_file
        .map(|path| path.display().to_string())
        .unwrap_or_default();
    let mut body = format!("## Structured collector record\n\n{structured_record}\n\n");
    body.push_str(&collector_section(
        &format!("Reviewer output ({reviewer_label})"),
        reviewer_file,
        false,
    )?);
    if let Some(reviewer_file) = reviewer_file {
        let reviewer_path = reviewer_file.display();
        let diagnostic = suffixed_path(reviewer_file, ".diag");
        let stderr_tail = suffixed_path(reviewer_file, ".stderr-tail");
        let launch_stderr = suffixed_path(reviewer_file, ".launch-stderr");
        body.push_str(&collector_section(
            &format!("Reviewer stderr ({reviewer_path}.diag)"),
            Some(&diagnostic),
            false,
        )?);
        body.push_str(&collector_section(
            &format!("Failed-agent stderr tail ({reviewer_path}.stderr-tail)"),
            Some(&stderr_tail),
            true,
        )?);
        body.push_str(&collector_section(
            &format!("Launcher stderr ({reviewer_path}.launch-stderr)"),
            Some(&launch_stderr),
            true,
        )?);
    }
    atomic_write_utf8(output, redact(&body).text(), DIAGNOSTIC_FILE_MODE)
}

fn suffixed_path(path: &Path, suffix: &str) -> PathBuf {
    let mut rendered = path.as_os_str().to_owned();
    rendered.push(suffix);
    PathBuf::from(rendered)
}

fn collector_section(
    header: &str,
    path: Option<&Path>,
    bounded_tail: bool,
) -> Result<String, FileIoError> {
    let mut section = format!("## {header}\n\n");
    let Some(path) = path else {
        section.push_str("(no path provided)\n\n");
        return Ok(section);
    };
    let label = path.display();
    let Some(text) = read_optional_utf8_lossy(path)? else {
        let _ = write!(section, "(file missing: {label})\n\n");
        return Ok(section);
    };
    if text.is_empty() {
        let _ = write!(section, "(empty: {label})\n\n");
        return Ok(section);
    }
    if bounded_tail {
        let rendered = render_failed_agent_stderr_tail(
            &text,
            failed_agent_stderr_tail_lines(),
            FAILED_AGENT_STDERR_TAIL_BYTE_CAP,
        );
        if rendered.is_empty() {
            let _ = write!(
                section,
                "(launcher stderr redaction unavailable or empty: {label})"
            );
        } else {
            section.push_str(&rendered);
        }
        section.push_str("\n\n");
    } else {
        section.push_str(&text);
        section.push('\n');
    }
    Ok(section)
}

/// Read a launcher exit from the `.done` sidecar, then the output capture.
///
/// # Errors
/// Returns [`FileIoError`] when an existing artifact cannot be read.
pub fn read_launcher_exit(output: &Path, process_rc: i32) -> Result<i32, FileIoError> {
    resolve_launcher_exit_from_files("", Some(output), process_rc)
}

/// Resolve a launcher exit from captured text plus the on-disk artifacts.
///
/// # Errors
/// Returns [`FileIoError`] when an existing artifact cannot be read.
pub fn resolve_launcher_exit_from_files(
    captured_text: &str,
    output: Option<&Path>,
    process_rc: i32,
) -> Result<i32, FileIoError> {
    let artifacts = match output {
        Some(output) => {
            let paths = LauncherArtifactPaths::new(output);
            Some(LauncherExitArtifacts {
                done: read_optional_utf8_lossy(&paths.path(LauncherArtifactKind::Done))?,
                output: read_optional_utf8_lossy(output)?,
            })
        }
        None => None,
    };
    Ok(resolve_launcher_exit(
        captured_text,
        artifacts.as_ref(),
        process_rc,
    ))
}

/// Return the first stderr candidate that is a non-empty regular file.
///
/// # Errors
/// Returns [`FileIoError`] when an existing candidate cannot be read.
pub fn select_failed_agent_stderr_source(
    paths: &LauncherArtifactPaths,
    mode: StderrCaptureMode,
    stderr_sink: Option<&Path>,
) -> Result<Option<PathBuf>, FileIoError> {
    for candidate in failed_agent_stderr_candidates(paths, mode, stderr_sink) {
        if read_optional_utf8_lossy(&candidate)?.is_some_and(|text| !text.is_empty()) {
            return Ok(Some(candidate));
        }
    }
    Ok(None)
}

/// Publish a bounded, redacted stderr tail; remove a stale tail when empty.
///
/// Returns whether a tail artifact now exists.
///
/// # Errors
/// Returns [`FileIoError`] for read, write, or removal failures.
pub fn write_failed_agent_stderr_tail(
    root: &TemporaryRoot,
    source: &Path,
    paths: &LauncherArtifactPaths,
    lines: Option<usize>,
    byte_cap: Option<usize>,
) -> Result<bool, FileIoError> {
    let text = read_optional_utf8_lossy(source)?.unwrap_or_default();
    let rendered = render_failed_agent_stderr_tail(
        &text,
        lines.unwrap_or_else(failed_agent_stderr_tail_lines),
        byte_cap.unwrap_or(FAILED_AGENT_STDERR_TAIL_BYTE_CAP),
    );
    let tail = paths.path(LauncherArtifactKind::StderrTail);
    if rendered.is_empty() {
        remove_optional_file(&tail)?;
        return Ok(false);
    }
    atomic_write_utf8_in(root, &tail, &rendered, true, DIAGNOSTIC_FILE_MODE)?;
    Ok(true)
}

/// Compose and publish the bounded failure-diagnostic carrier.
///
/// # Errors
/// Returns [`FileIoError`] for read or write failures.
pub fn write_failure_diag(
    root: &TemporaryRoot,
    paths: &LauncherArtifactPaths,
    sink: Option<&Path>,
    history: Option<&Path>,
    events: Option<&Path>,
) -> Result<(), FileIoError> {
    let ordered = failure_diag_source_order(paths, sink, history, events);
    let mut bodies = Vec::with_capacity(ordered.len());
    for (label, path, filtered) in ordered {
        let text = read_optional_utf8_lossy(&path)?.unwrap_or_default();
        bodies.push((label, path, text, filtered));
    }
    let sources: Vec<FailureDiagSource<'_>> = bodies
        .iter()
        .map(|(label, path, text, filtered)| FailureDiagSource {
            label,
            path,
            text,
            filtered: *filtered,
        })
        .collect();
    let Some(composed) = compose_failure_diag(
        &sources,
        vendor_failure_diag_section_lines(),
        vendor_failure_diag_byte_cap(),
    ) else {
        return Ok(());
    };
    let carrier = paths.path(LauncherArtifactKind::FailureDiag);
    // Every byte this function republishes is a diagnostic write, including the
    // carrier's prior content. Scrub it once here so the dedup comparison, the
    // append base, and the deduplicated no-op path all see the same scrubbed
    // text. Redaction is idempotent, so this changes nothing for content this
    // owner wrote and closes the gap for a carrier an unmigrated writer left.
    let raw_existing = read_optional_utf8_lossy(&carrier)?.unwrap_or_default();
    let existing = redact(&raw_existing).text().to_owned();
    match plan_failure_diag_write(&existing, composed) {
        // The carrier already holds this body, but it may still hold it
        // unscrubbed; republish only when scrubbing actually changed something.
        // The carrier already holds this body, but it may still hold it
        // unscrubbed; republish only when scrubbing actually changed something.
        FailureDiagWrite::Skip if existing == raw_existing => Ok(()),
        FailureDiagWrite::Skip => {
            atomic_write_utf8_in(root, &carrier, &existing, true, DIAGNOSTIC_FILE_MODE)
        }
        FailureDiagWrite::Create(body) => {
            atomic_write_utf8_in(root, &carrier, &body, true, DIAGNOSTIC_FILE_MODE)
        }
        FailureDiagWrite::Append(body) => atomic_write_utf8_in(
            root,
            &carrier,
            &format!("{existing}{body}"),
            true,
            DIAGNOSTIC_FILE_MODE,
        ),
    }
}

/// Roll one attempt's stream into its history file and truncate the stream.
///
/// # Errors
/// Returns [`FileIoError`] for read or write failures.
pub fn external_stream_reset(
    root: &TemporaryRoot,
    target: &Path,
    history: Option<&Path>,
    label: &str,
) -> Result<(), FileIoError> {
    if target == Path::new(NULL_DEVICE) {
        return Ok(());
    }
    let text = read_optional_utf8_lossy(target)?.unwrap_or_default();
    if let Some(history) = history
        && let Some(entry) =
            stream_reset_history_entry(label, &text, vendor_failure_diag_section_lines())
    {
        // Republished prior bytes are a diagnostic write too; this path always
        // rewrites the history file, so scrubbing here is unconditional.
        let existing = redact(&read_optional_utf8_lossy(history)?.unwrap_or_default())
            .text()
            .to_owned();
        atomic_write_utf8_in(
            root,
            history,
            &format!("{existing}{entry}"),
            true,
            DIAGNOSTIC_FILE_MODE,
        )?;
    }
    atomic_write_utf8_in(root, target, "", true, DIAGNOSTIC_FILE_MODE)
}

/// Return the configured failed-agent stderr tail length.
#[must_use]
pub fn failed_agent_stderr_tail_lines() -> usize {
    env_usize(
        larch_core::env::LARCH_FAILED_AGENT_STDERR_TAIL_LINES,
        FAILED_AGENT_STDERR_TAIL_LINES,
    )
}

/// Return the configured per-section line budget for a failure diagnostic.
#[must_use]
pub fn vendor_failure_diag_section_lines() -> usize {
    env_usize(
        larch_core::env::LARCH_VENDOR_FAILURE_DIAG_SECTION_LINES,
        VENDOR_FAILURE_DIAG_SECTION_LINES,
    )
}

/// Return the configured byte ceiling for a composed failure diagnostic.
#[must_use]
pub fn vendor_failure_diag_byte_cap() -> usize {
    env_usize(
        larch_core::env::LARCH_VENDOR_FAILURE_DIAG_BYTES,
        VENDOR_FAILURE_DIAG_BYTE_CAP,
    )
}

/// Read one non-negative integer override, falling back on any other value.
fn env_usize(name: &str, default: usize) -> usize {
    let Ok(raw) = env::var(name) else {
        return default;
    };
    if raw.is_empty() || !raw.bytes().all(|byte| byte.is_ascii_digit()) {
        return default;
    }
    raw.parse::<usize>().unwrap_or(default)
}
