//! The four `execution-issues` verbs `/implement` runs over its problem ledger.
//!
//! `$IMPLEMENT_TMPDIR/execution-issues.md` is the one mutable place a run
//! records what went wrong. These verbs are its whole lifecycle:
//!
//! * `append` adds one entry under its category heading, and adds it once.
//! * `flush` publishes the pending tail into the append-only `execution-issues`
//!   run-log batch, then clears the file so a later flush carries only what is
//!   new. A sentinel and a batch probe make a repeated flush a no-op.
//! * `flush-safety-net` publishes the same way at the terminal step but never
//!   clears the file, so the terminal snapshot still sees every entry.
//! * `refresh` projects the pending count onto the tracking issue's metadata
//!   comment.
//!
//! Recovery is the point of the split. A flush that composed records but died
//! before the batch append leaves the ledger untouched and no sentinel written,
//! so the retry recomposes and publishes. A flush that appended but died before
//! clearing the ledger finds its own rows in the batch on the retry and reports
//! `already-flushed` instead of publishing them twice. Deduplication is by
//! entry identity, never by file digest alone, so a partially flushed ledger
//! converges rather than duplicating.
//!
//! Every effect that leaves this process — the batch append and the tracking
//! comment — goes through the [`ExecutionIssueEffects`] seam, so each verb's
//! decisions are testable against a double rather than a live run log or a live
//! GitHub client.
//!
//! Ported from `larch.issue.execution_issues`.

use std::{
    env,
    ffi::OsString,
    fmt::Write as _,
    fs,
    path::{Path, PathBuf},
    process::ExitCode,
    time::Duration,
};

use larch_adapters::assert_no_symlink_path_or_ancestors;
use larch_core::{ChildEnvironment, ExternalProgram, LarchProgram};
use larch_core::{
    RecordLabels, RedactionRefusal, batch_contains_all_sections, emit_kv, execution_issue_records,
    split_text_lines,
};
use sha2::{Digest as _, Sha256};

use crate::{
    argparse_compat::{missing, parse_with_flags, usage_error as argparse_usage_error},
    child_process::{bounded_request, run_bounded},
    python_verb::plugin_root_directory,
    run_log_entry_commands::{
        ExecutionIssueAppendOutcome, append_execution_issue as append_execution_issue_atomic,
        append_execution_issue_filtered, clear_execution_issue_if_unchanged, plugin_version,
        read_optional_regular_lossy, read_regular_bytes, read_regular_lossy, write_run_log_file,
    },
};

/// Deadline for one re-entry into the verified larch executable.
const REENTRY_TIMEOUT: Duration = Duration::from_secs(120);
/// Grace period the runner allows a re-entered child to shut down.
const REENTRY_SHUTDOWN_GRACE: Duration = Duration::from_secs(5);
/// Cap on the bytes one re-entered child's captured output may carry.
const REENTRY_OUTPUT_LIMIT: usize = 1 << 20;

/// Exit code every verb reports for a rejected command line.
const VALIDATION_FAILED_RC: u8 = 2;
/// Only batch these verbs publish into.
const EXECUTION_ISSUES_BATCH: &str = "execution-issues";
/// Ledger basename every verb defaults to inside the session directory.
const LEDGER_BASENAME: &str = "execution-issues.md";
/// Sentinel recording the digest of the last successfully flushed ledger.
const FLUSHED_SENTINEL: &str = ".execution-issues-flushed.sha";
/// Sentinel recording that the Step 7a checkpoint ran at all.
const STEP7A_SENTINEL: &str = ".execution-issues-step7a-reached";
/// Longest transport diagnostic one refresh row carries.
const ERROR_LIMIT: usize = 500;

/// Publish one `argparse`-shaped usage refusal at this crate's usage code.
fn usage_error(usage: &str, program: &str, error: &str) -> ExitCode {
    argparse_usage_error(usage, program, error, VALIDATION_FAILED_RC)
}

const APPEND_USAGE: &str =
    "usage: cli.py execution-issues append [-h] --log LOG [--category CATEGORY] --entry ENTRY";

/// One captured child result: the exit status and both output streams.
pub struct EffectOutput {
    /// Exit status the child reported, or `None` when it could not be spawned.
    pub code: Option<i32>,
    /// Only what the child wrote to stdout.
    pub stdout: String,
    /// Only what the child wrote to stderr.
    pub stderr: String,
}

impl EffectOutput {
    /// Whether the effect completed with a success status.
    const fn succeeded(&self) -> bool {
        matches!(self.code, Some(0))
    }

    /// Render both streams the way the append log stores them.
    fn captured(&self) -> String {
        format!("{}{}", self.stdout, self.stderr)
    }

    /// Render the status the way the ledger's failure row spells it.
    fn status_text(&self) -> String {
        self.code.map_or_else(
            || "run-log could not run".to_owned(),
            |code| format!("run-log exited {code}"),
        )
    }
}

/// One tracking-issue summary publication request.
pub struct SummaryRequest<'a> {
    /// Issue number the summary comment belongs to.
    pub issue: &'a str,
    /// Marker that identifies this run's summary comment.
    pub marker: &'a str,
    /// File holding the rendered summary body.
    pub content_file: &'a Path,
    /// `owner/name` slug, when the session pinned one.
    pub repo: &'a str,
}

/// Every effect these verbs perform outside their own process.
pub trait ExecutionIssueEffects {
    /// Append one composed record file to the run-log `execution-issues` batch.
    fn append_records(&self, log_root: &Path, run_id: &str, record_file: &Path) -> EffectOutput;

    /// Publish one marker-keyed metadata summary comment on the tracking issue.
    fn upsert_summary(&self, request: &SummaryRequest<'_>) -> EffectOutput;
}

/// The live effects, each one re-entering through the verified bootstrap.
///
/// Python spawned the plugin entrypoint for the batch append and the Python CLI
/// for the summary comment. Both verbs now live in this binary, so the live
/// impl re-invokes `scripts/larch.sh` rather than resolving a second runtime, and each verb
/// still sees a captured child result instead of interleaved output on its own
/// contract stream.
pub struct LiveEffects;

impl LiveEffects {
    /// Run the verified larch bootstrap again with `arguments`.
    ///
    /// Both verbs it reaches for are Rust-owned and publish their own
    /// `KEY=value` envelope, so they run as bounded captured children rather
    /// than in process: the child's rows must land in the caller's diagnostic
    /// file, never interleaved into this verb's own contract stream.
    fn reenter(arguments: &[&str]) -> EffectOutput {
        let Some(root) = plugin_root_directory() else {
            return Self::unavailable("could not resolve the plugin root");
        };
        let Ok(program) = LarchProgram::bootstrap(&root) else {
            return Self::unavailable("could not resolve the larch executable");
        };
        let request = bounded_request(
            ExternalProgram::Larch(program),
            arguments.iter().map(OsString::from),
            REENTRY_TIMEOUT,
            REENTRY_SHUTDOWN_GRACE,
            REENTRY_OUTPUT_LIMIT,
        )
        .map(|request| {
            request.with_environment(ChildEnvironment::ClaudePluginRoot, root.into_os_string())
        });
        let outcome = match request {
            Ok(request) => run_bounded(request),
            Err(message) => Err(message),
        };
        match outcome {
            Ok(output) => {
                let stdout = String::from_utf8_lossy(output.stdout()).into_owned();
                let stderr = String::from_utf8_lossy(output.stderr()).into_owned();
                EffectOutput {
                    code: output.status().code(),
                    stdout,
                    stderr,
                }
            }
            Err(message) => Self::unavailable(&message),
        }
    }

    /// Report a child that never ran, keeping the reason on stderr.
    fn unavailable(message: &str) -> EffectOutput {
        EffectOutput {
            code: None,
            stdout: String::new(),
            stderr: message.to_owned(),
        }
    }
}

impl ExecutionIssueEffects for LiveEffects {
    fn append_records(&self, log_root: &Path, run_id: &str, record_file: &Path) -> EffectOutput {
        Self::reenter(&[
            "run-log",
            "append",
            "--log-root",
            &log_root.to_string_lossy(),
            "--skill",
            "implement",
            "--run-id",
            run_id,
            "--batch",
            EXECUTION_ISSUES_BATCH,
            "--record-file",
            &record_file.to_string_lossy(),
        ])
    }

    fn upsert_summary(&self, request: &SummaryRequest<'_>) -> EffectOutput {
        let content_file = request.content_file.to_string_lossy().into_owned();
        let mut arguments = vec![
            "tracking-issue",
            "upsert-summary",
            "--issue",
            request.issue,
            "--marker",
            request.marker,
            "--content-file",
            &content_file,
        ];
        if !request.repo.is_empty() {
            arguments.push("--repo");
            arguments.push(request.repo);
        }
        Self::reenter(&arguments)
    }
}

/// What one flush decided, in the shape its `KEY=value` contract publishes.
#[derive(Debug, Eq, PartialEq)]
pub struct FlushOutcome {
    /// Process exit code.
    pub rc: u8,
    /// `FLUSH_STATUS` row.
    pub status: &'static str,
    /// `RECORDS` row.
    pub records: usize,
    /// `APPEND_LOG_FILE` row, empty when no append was attempted.
    pub append_log: String,
}

/// One flush's inputs, shared by the clearing and safety-net variants.
pub struct FlushRequest<'a> {
    /// Absolute staging root the batch lives under.
    pub log_root: &'a Path,
    /// Run slug naming the staged run directory.
    pub run_id: &'a str,
    /// Ledger file the records are composed from.
    pub issue_log: &'a Path,
    /// Batch name; only `execution-issues` is accepted.
    pub batch: &'a str,
    /// Step label stamped on each composed record.
    pub step_label: &'a str,
    /// Source label stamped on each composed record.
    pub source_label: &'a str,
}

impl FlushRequest<'_> {
    /// Directory holding the ledger and its sentinels.
    fn sentinel_dir(&self) -> &Path {
        self.issue_log.parent().unwrap_or_else(|| Path::new("."))
    }

    /// Staged batch path this run appends into.
    fn batch_path(&self) -> PathBuf {
        self.log_root
            .join("implement")
            .join(self.run_id)
            .join("execution-issues.ndjson")
    }

    /// Reject a command line no flush may act on.
    fn validate(&self) -> Option<(&'static str, String)> {
        if !self.log_root.is_absolute() {
            return Some(("failed", "--log-root must be absolute".to_owned()));
        }
        if !is_run_slug(self.run_id) {
            return Some((
                "failed",
                "--run-id must contain only letters, numbers, and hyphens".to_owned(),
            ));
        }
        if self.batch != EXECUTION_ISSUES_BATCH {
            return Some(("failed", "--batch must be execution-issues".to_owned()));
        }
        if let Err(message) = assert_no_symlink_path_or_ancestors(self.issue_log) {
            return Some(("failed", message));
        }
        if fs::symlink_metadata(self.issue_log).is_ok_and(|metadata| !metadata.is_file()) {
            return Some((
                "failed",
                format!(
                    "--issue-log must be a regular file: {}",
                    self.issue_log.display()
                ),
            ));
        }
        let batch_path = self.batch_path();
        if let Err(message) = assert_no_symlink_path_or_ancestors(&batch_path) {
            return Some(("failed", message));
        }
        if fs::symlink_metadata(&batch_path).is_ok_and(|metadata| !metadata.is_file()) {
            return Some((
                "failed",
                format!(
                    "execution-issues batch must be a regular file: {}",
                    batch_path.display()
                ),
            ));
        }
        None
    }

    /// Reject hostile state files only the clearing flush reads or writes.
    fn validate_sentinels(&self) -> Result<(), String> {
        for (path, label) in [
            (self.sentinel_dir().join(FLUSHED_SENTINEL), "flush sentinel"),
            (
                self.sentinel_dir().join(STEP7A_SENTINEL),
                "Step 7a sentinel",
            ),
        ] {
            assert_no_symlink_path_or_ancestors(&path)?;
            if fs::symlink_metadata(&path).is_ok_and(|metadata| !metadata.is_file()) {
                return Err(format!(
                    "{label} must be a regular file: {}",
                    path.display()
                ));
            }
        }
        Ok(())
    }
}

/// Whether one run slug carries only the characters the layout accepts.
fn is_run_slug(value: &str) -> bool {
    !value.is_empty()
        && value
            .chars()
            .all(|character| character.is_ascii_alphanumeric() || character == '-')
}

/// Read a file as UTF-8, replacing undecodable bytes.
pub fn read_lossy(path: &Path) -> String {
    fs::read(path).map_or_else(
        |_error| String::new(),
        |bytes| String::from_utf8_lossy(&bytes).into_owned(),
    )
}

/// Read required file bytes as UTF-8 with replacement, preserving IO errors.
fn read_lossy_required(path: &Path) -> Result<String, String> {
    read_regular_lossy(path)
}

/// Whether one path is a regular file carrying at least one byte.
///
/// Missing files are empty. Every other metadata failure and every hostile
/// file type is an error so a flush cannot silently publish an empty result for
/// a ledger it could not inspect.
fn non_empty_regular_file(path: &Path) -> Result<bool, String> {
    match fs::symlink_metadata(path) {
        Ok(metadata) if metadata.is_file() => Ok(metadata.len() > 0),
        Ok(_metadata) => Err(format!(
            "execution-issues ledger must be a regular file: {}",
            path.display()
        )),
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => Ok(false),
        Err(error) => Err(format!("{}: {error}", path.display())),
    }
}

/// Hex SHA-256 of one file's exact bytes.
#[cfg(test)]
fn sha256_file(path: &Path) -> Result<String, String> {
    let bytes = read_regular_bytes(path)?;
    Ok(sha256_bytes(&bytes))
}

/// Hex SHA-256 of one exact byte snapshot.
fn sha256_bytes(bytes: &[u8]) -> String {
    let mut out = String::with_capacity(64);
    for byte in Sha256::digest(bytes) {
        let _written = write!(&mut out, "{byte:02x}");
    }
    out
}

/// Compose the records one ledger still owes the staged batch, atomically.
///
/// Returns the number of records written. An empty ledger publishes an empty
/// record file, which is how the terminal checkpoint distinguishes "nothing
/// pending" from "composition failed".
///
/// # Errors
///
/// Returns the redaction refusal or the write failure, as a message.
pub fn write_execution_issue_records(
    issue_log: &Path,
    record_file: &Path,
    batch_path: Option<&Path>,
    labels: RecordLabels<'_>,
) -> Result<usize, String> {
    write_execution_issue_records_snapshot(issue_log, record_file, batch_path, labels)
        .map(|(records, _snapshot)| records)
}

/// Compose records from one exact live-ledger snapshot.
///
/// Returning the source bytes lets the clearing flush compare-and-clear under
/// the append lock after its external batch append. This closes the window in
/// which a later writer could otherwise be erased by the final clear.
fn write_execution_issue_records_snapshot(
    issue_log: &Path,
    record_file: &Path,
    batch_path: Option<&Path>,
    labels: RecordLabels<'_>,
) -> Result<(usize, Vec<u8>), String> {
    assert_no_symlink_path_or_ancestors(issue_log)?;
    let batch_text = match batch_path {
        Some(path) => {
            assert_no_symlink_path_or_ancestors(path)?;
            read_optional_regular_lossy(path, "execution-issues batch must be a regular file")?
        }
        None => String::new(),
    };
    let issue_bytes = match fs::symlink_metadata(issue_log) {
        Ok(metadata) if metadata.is_file() => read_regular_bytes(issue_log)?,
        Ok(_metadata) => {
            return Err(format!(
                "execution-issues ledger must be a regular file: {}",
                issue_log.display()
            ));
        }
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => Vec::new(),
        Err(error) => return Err(format!("{}: {error}", issue_log.display())),
    };
    let issue_text = String::from_utf8_lossy(&issue_bytes);
    let records = execution_issue_records(&issue_text, &batch_text, labels)
        .map_err(|RedactionRefusal| "redaction failed for run-log batch payload".to_owned())?;
    let payload = if records.is_empty() {
        String::new()
    } else {
        format!("{}\n", records.join("\n"))
    };
    write_run_log_file(record_file, &payload)?;
    Ok((records.len(), issue_bytes))
}

/// Record one wrapper failure back into the ledger it could not publish.
fn append_failure(issue_log: &Path, site: &str, message: &str) {
    let _recorded = append_execution_issue_atomic(
        issue_log,
        "Tool Failures",
        &format!("- **{site}**: {message}"),
    );
}

/// Preserve one flush failure in its source ledger and return the stable wire.
fn flush_failure(issue_log: &Path, site: &str, message: &str, append_log: String) -> FlushOutcome {
    append_failure(issue_log, site, message);
    FlushOutcome {
        rc: 1,
        status: "failed",
        records: 0,
        append_log,
    }
}

/// Record one published snapshot and clear it only if no writer raced it.
fn finalize_clearing_flush(
    issue_log: &Path,
    sentinel: &Path,
    digest: &str,
    snapshot: &[u8],
) -> Result<(), String> {
    write_run_log_file(sentinel, &format!("{digest}\n"))?;
    let _cleared = clear_execution_issue_if_unchanged(issue_log, snapshot)?;
    Ok(())
}

/// Persist the Step 7a checkpoint when this is the pre-bump flush.
fn mark_step7a_checkpoint(request: &FlushRequest<'_>) -> Result<(), String> {
    if request.step_label != "7a" {
        return Ok(());
    }
    let checkpoint = request.sentinel_dir().join(STEP7A_SENTINEL);
    if checkpoint.is_file() {
        return Ok(());
    }
    write_run_log_file(&checkpoint, "")
}

/// Publish the pending ledger tail and clear the ledger.
pub fn flush_with<E: ExecutionIssueEffects>(
    effects: &E,
    request: &FlushRequest<'_>,
) -> FlushOutcome {
    if let Some((status, reason)) = request.validate() {
        return FlushOutcome {
            rc: VALIDATION_FAILED_RC,
            status,
            records: 0,
            append_log: reason,
        };
    }
    if let Err(reason) = request.validate_sentinels() {
        return FlushOutcome {
            rc: VALIDATION_FAILED_RC,
            status: "failed",
            records: 0,
            append_log: reason,
        };
    }
    if let Err(message) = mark_step7a_checkpoint(request) {
        return flush_failure(
            request.issue_log,
            "flush-execution-issues",
            &message,
            String::new(),
        );
    }
    let non_empty = match non_empty_regular_file(request.issue_log) {
        Ok(non_empty) => non_empty,
        Err(message) => {
            return flush_failure(
                request.issue_log,
                "flush-execution-issues",
                &message,
                String::new(),
            );
        }
    };
    if !non_empty {
        return FlushOutcome {
            rc: 0,
            status: "skip",
            records: 0,
            append_log: String::new(),
        };
    }
    let sentinel = request.sentinel_dir().join(FLUSHED_SENTINEL);
    let batch_path = request.batch_path();
    let (snapshot, digest, already_published) =
        match flush_digest_state(request, &sentinel, &batch_path) {
            Ok(state) => state,
            Err(message) => {
                return flush_failure(
                    request.issue_log,
                    "flush-execution-issues",
                    &message,
                    String::new(),
                );
            }
        };
    if already_published {
        let finalized = finalize_clearing_flush(request.issue_log, &sentinel, &digest, &snapshot);
        if let Err(message) = finalized {
            return flush_failure(
                request.issue_log,
                "flush-execution-issues",
                &message,
                String::new(),
            );
        }
        return FlushOutcome {
            rc: 0,
            status: "already-flushed",
            records: 0,
            append_log: String::new(),
        };
    }
    let (outcome, published_snapshot) = publish(
        effects,
        request,
        &batch_path,
        &format!("flush-execution-issues-append.{}.log", std::process::id()),
        "flush-execution-issues",
    );
    if outcome.rc == 0 {
        let snapshot = published_snapshot.unwrap_or(snapshot);
        let published_digest = sha256_bytes(&snapshot);
        let finalized =
            finalize_clearing_flush(request.issue_log, &sentinel, &published_digest, &snapshot);
        if let Err(message) = finalized {
            return flush_failure(
                request.issue_log,
                "flush-execution-issues",
                &message,
                outcome.append_log,
            );
        }
    }
    outcome
}

/// Read the live digest and determine whether its records are already durable.
fn flush_digest_state(
    request: &FlushRequest<'_>,
    sentinel: &Path,
    batch_path: &Path,
) -> Result<(Vec<u8>, String, bool), String> {
    let snapshot = read_regular_bytes(request.issue_log)?;
    let digest = sha256_bytes(&snapshot);
    let issue_text = String::from_utf8_lossy(&snapshot);
    let already_published = already_flushed(sentinel, &digest, batch_path, &issue_text)?;
    Ok((snapshot, digest, already_published))
}

/// Publish the pending ledger tail without clearing the ledger.
pub fn flush_safety_net_with<E: ExecutionIssueEffects>(
    effects: &E,
    request: &FlushRequest<'_>,
) -> FlushOutcome {
    if let Some((status, reason)) = request.validate() {
        return FlushOutcome {
            rc: VALIDATION_FAILED_RC,
            status,
            records: 0,
            append_log: reason,
        };
    }
    let non_empty = match non_empty_regular_file(request.issue_log) {
        Ok(non_empty) => non_empty,
        Err(message) => {
            append_failure(
                request.issue_log,
                "flush-execution-issues-safety-net",
                &message,
            );
            return FlushOutcome {
                rc: 1,
                status: "failed",
                records: 0,
                append_log: String::new(),
            };
        }
    };
    if !non_empty {
        return FlushOutcome {
            rc: 0,
            status: "skip",
            records: 0,
            append_log: String::new(),
        };
    }
    let batch_path = request.batch_path();
    publish(
        effects,
        request,
        &batch_path,
        &format!(
            "flush-execution-issues-safety-net-append.{}.log",
            std::process::id()
        ),
        "flush-execution-issues-safety-net",
    )
    .0
}

/// Whether the staged batch already carries this exact ledger.
///
/// The sentinel answers the common case in one read. When it is missing — a
/// resumed run, a cleaned session — the batch itself is probed, first for the
/// whole-file digest an older writer stored and then for the per-entry hashes
/// the current writer stores.
fn already_flushed(
    sentinel: &Path,
    digest: &str,
    batch_path: &Path,
    issue_text: &str,
) -> Result<bool, String> {
    match fs::symlink_metadata(sentinel) {
        Ok(metadata) if metadata.is_file() => {
            if read_lossy_required(sentinel)?.trim() == digest {
                return Ok(true);
            }
        }
        Ok(_metadata) => {
            return Err(format!(
                "flush sentinel must be a regular file: {}",
                sentinel.display()
            ));
        }
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => {}
        Err(error) => return Err(format!("{}: {error}", sentinel.display())),
    }
    let batch_text =
        read_optional_regular_lossy(batch_path, "execution-issues batch must be a regular file")?;
    if batch_text.contains(&format!("\"source_sha256\":\"{digest}\"")) {
        return Ok(true);
    }
    batch_contains_all_sections(issue_text, &batch_text)
        .map_err(|RedactionRefusal| "redaction failed for run-log batch payload".to_owned())
}

/// Compose records, append them, and report what the append decided.
fn publish<E: ExecutionIssueEffects>(
    effects: &E,
    request: &FlushRequest<'_>,
    batch_path: &Path,
    append_log_name: &str,
    site: &str,
) -> (FlushOutcome, Option<Vec<u8>>) {
    let sentinel_dir = request.sentinel_dir();
    // The append-log name already carries this process's id, so the staging
    // file it derives is unique: two flushes in one session directory cannot
    // read each other's half-written composition.
    let record_path = sentinel_dir.join(format!(".{append_log_name}.records"));
    let append_log = sentinel_dir.join(append_log_name);
    let append_log_text = append_log.to_string_lossy().into_owned();
    let labels = RecordLabels {
        step: request.step_label,
        source: request.source_label,
    };
    let composed = write_execution_issue_records_snapshot(
        request.issue_log,
        &record_path,
        Some(batch_path),
        labels,
    );
    let mut snapshot = None;
    let (rc, status, records) = match composed {
        Err(message) => {
            append_failure(request.issue_log, site, &message);
            (1, "failed", 0)
        }
        Ok((0, source)) => {
            snapshot = Some(source);
            (0, "no-records", 0)
        }
        Ok((records, source)) => {
            snapshot = Some(source);
            let output = effects.append_records(request.log_root, request.run_id, &record_path);
            let captured = write_run_log_file(&append_log, &output.captured());
            if output.succeeded() && captured.is_ok() {
                (0, "ok", records)
            } else {
                append_failure(
                    request.issue_log,
                    site,
                    &captured.err().unwrap_or_else(|| output.status_text()),
                );
                (1, "failed", 0)
            }
        }
    };
    let _removed = fs::remove_file(&record_path);
    (
        FlushOutcome {
            rc,
            status,
            records,
            append_log: append_log_text,
        },
        snapshot,
    )
}

/// Read the first `KEY=value` row from one file, the way the wire reader does.
#[cfg(test)]
fn read_kv(path: &Path, key: &str) -> String {
    read_kv_checked(path, key).unwrap_or_default()
}

/// Read one optional KV file without collapsing an unsafe or unreadable file
/// into a missing value.
fn read_kv_checked(path: &Path, key: &str) -> Result<String, String> {
    let text = read_optional_regular_lossy(path, "session metadata must be a regular file")?;
    let prefix = format!("{key}=");
    Ok(text
        .split('\n')
        .find_map(|line| line.strip_prefix(&prefix))
        .map(|value| value.trim_matches('\r').to_owned())
        .unwrap_or_default())
}

/// What one refresh decided.
#[derive(Debug, Eq, PartialEq)]
pub struct RefreshOutcome {
    /// Process exit code.
    pub rc: u8,
    /// `REFRESHED` row.
    pub refreshed: bool,
    /// `REASON` row when refreshed, `ERROR` row when not.
    pub detail: String,
}

/// Return a failed refresh and preserve its diagnostic in the pending ledger.
fn refresh_failure(implement_tmpdir: &Path, best_effort: bool, detail: String) -> RefreshOutcome {
    append_failure(
        &implement_tmpdir.join(LEDGER_BASENAME),
        "refresh-execution-issues",
        &detail,
    );
    RefreshOutcome {
        rc: u8::from(!best_effort),
        refreshed: false,
        detail,
    }
}

/// Publish and capture one prepared metadata summary through the typed effect.
fn publish_refresh<E: ExecutionIssueEffects>(
    effects: &E,
    implement_tmpdir: &Path,
    best_effort: bool,
    request: &SummaryRequest<'_>,
) -> RefreshOutcome {
    let output = effects.upsert_summary(request);
    let stdout_capture = write_run_log_file(
        &implement_tmpdir.join("refresh-execution-issues.out"),
        &output.stdout,
    );
    let stderr_capture = write_run_log_file(
        &implement_tmpdir.join("refresh-execution-issues.err"),
        &output.stderr,
    );
    if let Err(error) = stdout_capture.and(stderr_capture) {
        return refresh_failure(implement_tmpdir, best_effort, error);
    }
    if output.succeeded() {
        return RefreshOutcome {
            rc: 0,
            refreshed: true,
            detail: String::new(),
        };
    }
    let detail = collapsed_diagnostic(&output.stderr);
    refresh_failure(
        implement_tmpdir,
        best_effort,
        if detail.is_empty() {
            output.status_text()
        } else {
            detail
        },
    )
}

/// Project the pending execution-issue count onto the tracking issue.
pub fn refresh_with<E: ExecutionIssueEffects>(
    effects: &E,
    implement_tmpdir: &Path,
    best_effort: bool,
    log_reference: &dyn Fn(Option<&Path>, &str, &Path) -> String,
) -> RefreshOutcome {
    if !implement_tmpdir.is_dir()
        || implement_tmpdir.is_symlink()
        || assert_no_symlink_path_or_ancestors(implement_tmpdir).is_err()
    {
        return RefreshOutcome {
            rc: if best_effort { 0 } else { VALIDATION_FAILED_RC },
            refreshed: false,
            detail: "--implement-tmpdir not found".to_owned(),
        };
    }
    let parent_issue = implement_tmpdir.join("parent-issue.md");
    let session_env = implement_tmpdir.join("session-env.sh");
    let session_id = implement_tmpdir.join("session-id");
    if [&parent_issue, &session_env, &session_id]
        .into_iter()
        .any(|path| path.is_symlink())
    {
        return refresh_failure(
            implement_tmpdir,
            best_effort,
            "session metadata must not be symlinked".to_owned(),
        );
    }
    let issue = match read_kv_checked(&parent_issue, "ISSUE_NUMBER") {
        Ok(issue) => issue,
        Err(message) => return refresh_failure(implement_tmpdir, best_effort, message),
    };
    let run_id = match resolve_run_id(&parent_issue, &session_id) {
        Ok(run_id) => run_id,
        Err(message) => return refresh_failure(implement_tmpdir, best_effort, message),
    };
    if issue.is_empty() || issue == "0" {
        return RefreshOutcome {
            rc: 0,
            refreshed: true,
            detail: "issue-not-set".to_owned(),
        };
    }
    if !issue.chars().all(|character| character.is_ascii_digit()) {
        return refresh_failure(
            implement_tmpdir,
            best_effort,
            "ISSUE_NUMBER must be numeric".to_owned(),
        );
    }
    let repo_root = match read_kv_checked(&session_env, "REPO_ROOT") {
        Ok(repo_root) => repo_root,
        Err(message) => return refresh_failure(implement_tmpdir, best_effort, message),
    };
    let reference = log_reference(
        (!repo_root.is_empty()).then(|| Path::new(&repo_root)),
        &run_id,
        &implement_tmpdir
            .join("larch-logs")
            .join("implement")
            .join(&run_id)
            .join("manifest.json"),
    );
    let summary = implement_tmpdir.join("summary-metadata.md");
    let version = plugin_version();
    let body = match compose_summary_metadata(
        implement_tmpdir,
        &summary,
        &issue,
        &run_id,
        &reference,
        &version,
    ) {
        Ok(body) => body,
        Err(message) => return refresh_failure(implement_tmpdir, best_effort, message),
    };
    if let Err(error) = write_run_log_file(&summary, &body) {
        return refresh_failure(implement_tmpdir, best_effort, error);
    }
    let repo = match read_kv_checked(&session_env, "REPO") {
        Ok(repo) => repo,
        Err(message) => return refresh_failure(implement_tmpdir, best_effort, message),
    };
    let marker = format!("<!-- larch:metadata v1 runid={run_id} -->");
    publish_refresh(
        effects,
        implement_tmpdir,
        best_effort,
        &SummaryRequest {
            issue: &issue,
            marker: &marker,
            content_file: &summary,
            repo: &repo,
        },
    )
}

/// Resolve the run slug from the parent-issue row, else the session sentinel.
fn resolve_run_id(parent_issue: &Path, session_id: &Path) -> Result<String, String> {
    let run_id = read_kv_checked(parent_issue, "RUN_ID")?;
    if !run_id.is_empty() {
        return Ok(run_id);
    }
    read_optional_regular_lossy(session_id, "session metadata must be a regular file")
        .map(|value| value.trim().to_owned())
}

/// Render the metadata comment body, preserving rows this refresh does not own.
///
/// A run that already published a summary keeps its own first row and every
/// line the refresh does not regenerate, so a re-run refreshes the run-log
/// pointer and the pending count without discarding what else the summary
/// carried.
fn compose_summary_metadata(
    implement_tmpdir: &Path,
    summary: &Path,
    issue: &str,
    run_id: &str,
    reference: &str,
    version: &str,
) -> Result<String, String> {
    let issue_log = implement_tmpdir.join(LEDGER_BASENAME);
    let count = if non_empty_regular_file(&issue_log)? {
        split_text_lines(&read_lossy_required(&issue_log)?)
            .into_iter()
            .filter(|line| line.starts_with("- "))
            .count()
    } else {
        0
    };
    let existing = match fs::symlink_metadata(summary) {
        Ok(metadata) if metadata.is_file() => read_lossy_required(summary)?,
        Ok(_metadata) => {
            return Err(format!(
                "summary metadata must be a regular file: {}",
                summary.display()
            ));
        }
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => String::new(),
        Err(error) => return Err(format!("{}: {error}", summary.display())),
    };
    let mut kept: Vec<String> = if existing.is_empty() {
        let session_env = implement_tmpdir.join("session-env.sh");
        let agent = read_kv_checked(&session_env, "AGENT")?;
        let coder = read_kv_checked(&session_env, "CODER")?;
        vec![
            format!("Run ID: `{run_id}`"),
            format!("Run log: {reference}"),
            format!("Tracking issue: #{issue}"),
            format!(
                "Agent: `{}`",
                if agent.is_empty() { "claude" } else { &agent }
            ),
            format!(
                "Coder: `{}`",
                if coder.is_empty() { "claude" } else { &coder }
            ),
            format!(
                "Larch version: `{}`",
                if version.is_empty() {
                    "unknown"
                } else {
                    version
                }
            ),
        ]
    } else {
        let mut rows: Vec<String> = split_text_lines(&existing)
            .into_iter()
            .filter(|line| !is_replaced_metadata_row(line))
            .map(str::to_owned)
            .collect();
        rows.insert(1.min(rows.len()), format!("Run log: {reference}"));
        rows
    };
    kept.push(format!("Execution issues pending flush: `{count}`"));
    Ok(format!("{}\n", kept.join("\n")))
}

/// Collapse one child's stderr into a single bounded diagnostic row.
fn collapsed_diagnostic(stderr: &str) -> String {
    let mut detail = stderr.split_whitespace().collect::<Vec<_>>().join(" ");
    detail.truncate(
        detail
            .char_indices()
            .nth(ERROR_LIMIT)
            .map_or(detail.len(), |(index, _character)| index),
    );
    detail
}

/// Whether one summary row is regenerated on every refresh.
fn is_replaced_metadata_row(line: &str) -> bool {
    ["Execution issues pending flush:", "Logs:", "Run log:"]
        .iter()
        .any(|prefix| line.starts_with(prefix))
}

/// Run the Rust-owned `execution-issues append` command.
#[must_use]
pub fn append(arguments: &[OsString]) -> ExitCode {
    let parsed = parse_with_flags(
        arguments,
        &["--log", "--category", "--entry", "--existing-batch"],
        &["--redact", "--report-status", "--spaced-section"],
        0,
    );
    if let Some(error) = parsed.error() {
        return usage_error(APPEND_USAGE, "cli.py execution-issues append", &error);
    }
    let (Some(log), Some(entry)) = (parsed.value("--log"), parsed.value("--entry")) else {
        return usage_error(
            APPEND_USAGE,
            "cli.py execution-issues append",
            &missing(&[
                ("--log", parsed.value("--log").is_some()),
                ("--entry", parsed.value("--entry").is_some()),
            ]),
        );
    };
    let category = parsed.value("--category").map_or_else(
        || "Tool Failures".to_owned(),
        |value| value.to_string_lossy().into_owned(),
    );
    let existing_batch = parsed
        .value("--existing-batch")
        .filter(|value| !value.is_empty())
        .map(Path::new);
    match append_execution_issue_filtered(
        Path::new(log),
        &category,
        &entry.to_string_lossy(),
        existing_batch,
        parsed.flag("--redact"),
        parsed.flag("--spaced-section"),
    ) {
        Ok(outcome) => {
            if parsed.flag("--report-status") {
                emit_kv(
                    "APPEND_STATUS",
                    match outcome {
                        ExecutionIssueAppendOutcome::Appended => "appended",
                        ExecutionIssueAppendOutcome::Duplicate => "duplicate",
                    },
                );
            }
            ExitCode::SUCCESS
        }
        Err(message) => {
            eprintln!("cli.py execution-issues append: error: {message}");
            ExitCode::FAILURE
        }
    }
}

/// Run the Rust-owned `execution-issues flush` command.
#[must_use]
pub fn flush(arguments: &[OsString]) -> ExitCode {
    let parsed = parse_with_flags(
        arguments,
        &[
            "--log-root",
            "--run-id",
            "--issue-log",
            "--batch",
            "--step-label",
            "--source-label",
        ],
        &[],
        0,
    );
    let Some(values) = flush_arguments(&parsed, "7a", "execution-issues.md pre-bump") else {
        return flush_usage_refusal();
    };
    let issue_log = values.issue_log.clone();
    let outcome = flush_with(
        &LiveEffects,
        &FlushRequest {
            log_root: Path::new(&values.log_root),
            run_id: &values.run_id,
            issue_log: &issue_log,
            batch: &values.batch,
            step_label: &values.step_label,
            source_label: &values.source_label,
        },
    );
    report_flush(&outcome)
}

/// Run the Rust-owned `execution-issues flush-safety-net` command.
#[must_use]
pub fn flush_safety_net(arguments: &[OsString]) -> ExitCode {
    let parsed = parse_with_flags(
        arguments,
        &[
            "--log-root",
            "--run-id",
            "--issue-log",
            "--batch",
            "--step-label",
            "--source-label",
            "--record-file",
        ],
        &[],
        0,
    );
    let Some(values) = flush_arguments(&parsed, "18", "execution-issues.md safety-net") else {
        return flush_usage_refusal();
    };
    let record_file = parsed
        .value("--record-file")
        .map(|value| PathBuf::from(value.to_owned()));
    if let Some(record_file) = record_file.filter(|path| !path.as_os_str().is_empty()) {
        return render_records(&values, &record_file);
    }
    let outcome = flush_safety_net_with(
        &LiveEffects,
        &FlushRequest {
            log_root: Path::new(&values.log_root),
            run_id: &values.run_id,
            issue_log: &values.issue_log,
            batch: &values.batch,
            step_label: &values.step_label,
            source_label: &values.source_label,
        },
    );
    report_flush(&outcome)
}

/// Compose records into a caller-named file without publishing them.
///
/// The caller is the Rust run-log checkpoint, which stages the composed rows
/// itself. The destination is confined to the staging tree's own parent so a
/// caller cannot redirect composition through a symlink or into an unrelated
/// directory.
fn render_records(values: &FlushArguments, record_file: &Path) -> ExitCode {
    let log_root = Path::new(&values.log_root);
    if !confined_record_destination(log_root, record_file, values) {
        emit_kv("FLUSH_STATUS", "failed");
        emit_kv("RECORDS", "0");
        emit_kv("ERROR", "validation failed");
        return ExitCode::from(VALIDATION_FAILED_RC);
    }
    let batch_path = log_root
        .join("implement")
        .join(&values.run_id)
        .join("execution-issues.ndjson");
    let composed = match non_empty_regular_file(&values.issue_log) {
        Ok(true) => write_execution_issue_records(
            &values.issue_log,
            record_file,
            Some(&batch_path),
            RecordLabels {
                step: &values.step_label,
                source: &values.source_label,
            },
        ),
        Ok(false) => write_run_log_file(record_file, "").map(|()| 0),
        Err(message) => Err(message),
    };
    match composed {
        Ok(records) => {
            emit_kv("FLUSH_STATUS", "rendered");
            emit_kv("RECORDS", &records.to_string());
            ExitCode::SUCCESS
        }
        Err(_message) => {
            emit_kv("FLUSH_STATUS", "failed");
            emit_kv("RECORDS", "0");
            emit_kv("ERROR", "validation failed");
            ExitCode::from(VALIDATION_FAILED_RC)
        }
    }
}

/// Whether one render destination may be written.
fn confined_record_destination(
    log_root: &Path,
    record_file: &Path,
    values: &FlushArguments,
) -> bool {
    if !log_root.is_absolute()
        || log_root.file_name().is_none_or(|name| name != "larch-logs")
        || !log_root.is_dir()
        || !record_file.is_absolute()
        || record_file.is_symlink()
        || !is_run_slug(&values.run_id)
        || values.issue_log.is_symlink()
    {
        return false;
    }
    if fs::symlink_metadata(record_file).is_ok_and(|data| !data.is_file()) {
        return false;
    }
    let batch_path = log_root
        .join("implement")
        .join(&values.run_id)
        .join("execution-issues.ndjson");
    if assert_no_symlink_path_or_ancestors(&values.issue_log).is_err()
        || assert_no_symlink_path_or_ancestors(record_file).is_err()
        || assert_no_symlink_path_or_ancestors(&batch_path).is_err()
    {
        return false;
    }
    let (Some(record_parent), Some(staging_parent)) = (record_file.parent(), log_root.parent())
    else {
        return false;
    };
    match (record_parent.canonicalize(), staging_parent.canonicalize()) {
        (Ok(record_parent), Ok(staging_parent)) => record_parent == staging_parent,
        _unresolved => false,
    }
}

/// Run the Rust-owned `execution-issues refresh` command.
#[must_use]
pub fn refresh(arguments: &[OsString]) -> ExitCode {
    let parsed = parse_with_flags(arguments, &["--implement-tmpdir"], &["--best-effort"], 0);
    if parsed.error().is_some() {
        emit_kv("REFRESHED", "false");
        emit_kv("ERROR", "usage");
        return ExitCode::from(VALIDATION_FAILED_RC);
    }
    let raw =
        crate::implement_commands::resolve_implement_tmpdir(parsed.value("--implement-tmpdir"));
    let Some(raw) = raw else {
        emit_kv("REFRESHED", "false");
        emit_kv(
            "ERROR",
            "--implement-tmpdir is required or IMPLEMENT_TMPDIR must be set",
        );
        return ExitCode::from(VALIDATION_FAILED_RC);
    };
    let outcome = refresh_with(
        &LiveEffects,
        Path::new(&raw),
        parsed.flag("--best-effort"),
        &|repo_root, run_id, manifest| {
            crate::run_log_commands::run_log_reference("implement", repo_root, run_id, manifest)
        },
    );
    emit_kv(
        "REFRESHED",
        if outcome.refreshed { "true" } else { "false" },
    );
    if !outcome.detail.is_empty() {
        emit_kv(
            if outcome.refreshed { "REASON" } else { "ERROR" },
            &outcome.detail,
        );
    }
    ExitCode::from(outcome.rc)
}

/// One parsed flush command line.
struct FlushArguments {
    log_root: String,
    run_id: String,
    issue_log: PathBuf,
    batch: String,
    step_label: String,
    source_label: String,
}

/// Read the shared flush option table, or `None` when a required one is absent.
fn flush_arguments(
    parsed: &crate::argparse_compat::ParsedCommandLine,
    default_step: &str,
    default_source: &str,
) -> Option<FlushArguments> {
    if parsed.error().is_some() {
        return None;
    }
    let text = |option: &str, fallback: &str| -> String {
        parsed.value(option).map_or_else(
            || fallback.to_owned(),
            |value| value.to_string_lossy().into_owned(),
        )
    };
    let log_root = parsed.value("--log-root")?.to_string_lossy().into_owned();
    let run_id = parsed.value("--run-id")?.to_string_lossy().into_owned();
    let issue_log = parsed
        .value("--issue-log")
        .filter(|value| !value.is_empty())
        .map_or_else(
            || {
                PathBuf::from(env::var("IMPLEMENT_TMPDIR").unwrap_or_else(|_error| ".".to_owned()))
                    .join(LEDGER_BASENAME)
            },
            |value| PathBuf::from(value.to_owned()),
        );
    Some(FlushArguments {
        log_root,
        run_id,
        issue_log,
        batch: text("--batch", EXECUTION_ISSUES_BATCH),
        step_label: text("--step-label", default_step),
        source_label: text("--source-label", default_source),
    })
}

/// Publish the usage refusal both flush verbs share.
fn flush_usage_refusal() -> ExitCode {
    emit_kv("FLUSH_STATUS", "failed");
    emit_kv("RECORDS", "0");
    emit_kv("ERROR", "usage");
    ExitCode::from(VALIDATION_FAILED_RC)
}

/// Publish one flush outcome on the stream its callers parse.
fn report_flush(outcome: &FlushOutcome) -> ExitCode {
    emit_kv("FLUSH_STATUS", outcome.status);
    emit_kv("RECORDS", &outcome.records.to_string());
    if !outcome.append_log.is_empty() {
        emit_kv("APPEND_LOG_FILE", &outcome.append_log);
    }
    if outcome.rc == VALIDATION_FAILED_RC {
        emit_kv(
            "ERROR",
            if outcome.append_log.is_empty() {
                "validation failed"
            } else {
                &outcome.append_log
            },
        );
    }
    ExitCode::from(outcome.rc)
}

#[cfg(test)]
mod tests {
    use super::{
        EffectOutput, ExecutionIssueEffects, FLUSHED_SENTINEL, FlushArguments, FlushRequest,
        LEDGER_BASENAME, STEP7A_SENTINEL, SummaryRequest, append, collapsed_diagnostic,
        compose_summary_metadata, confined_record_destination, flush, flush_arguments,
        flush_safety_net, flush_safety_net_with, flush_with, plugin_version, read_kv, refresh,
        refresh_with, sha256_file, write_execution_issue_records,
    };
    use crate::run_log_commands::{pins_disabled_publication, run_log_reference};
    use crate::{
        argparse_compat::parse_with_flags, run_log_entry_commands::append_execution_issue,
    };
    use larch_core::RecordLabels;
    use std::process::ExitCode;
    use std::{
        cell::RefCell,
        fs,
        path::{Path, PathBuf},
    };
    use tempfile::TempDir;

    /// A double that stages appends into the batch file the live verb writes.
    struct FakeEffects {
        batch: PathBuf,
        append_code: Option<i32>,
        summary_code: Option<i32>,
        summary_stderr: String,
        late_append: Option<(PathBuf, String)>,
        seen: RefCell<Vec<String>>,
    }

    impl FakeEffects {
        fn new(batch: &Path) -> Self {
            Self {
                batch: batch.to_path_buf(),
                append_code: Some(0),
                summary_code: Some(0),
                summary_stderr: String::new(),
                late_append: None,
                seen: RefCell::new(Vec::new()),
            }
        }

        fn failing(batch: &Path) -> Self {
            Self {
                append_code: Some(9),
                ..Self::new(batch)
            }
        }
    }

    impl ExecutionIssueEffects for FakeEffects {
        fn append_records(
            &self,
            _log_root: &Path,
            _run_id: &str,
            record_file: &Path,
        ) -> EffectOutput {
            let payload = fs::read_to_string(record_file).unwrap_or_default();
            self.seen.borrow_mut().push(payload.clone());
            if let Some((log, entry)) = &self.late_append {
                append_execution_issue(log, "Warnings", entry).expect("late append");
            }
            if self.append_code == Some(0) {
                if let Some(parent) = self.batch.parent() {
                    fs::create_dir_all(parent).expect("batch parent must be creatable");
                }
                let existing = fs::read_to_string(&self.batch).unwrap_or_default();
                fs::write(&self.batch, format!("{existing}{payload}"))
                    .expect("batch must be writable");
            }
            EffectOutput {
                code: self.append_code,
                stdout: "out\n".to_owned(),
                stderr: "err\n".to_owned(),
            }
        }

        fn upsert_summary(&self, request: &SummaryRequest<'_>) -> EffectOutput {
            self.seen.borrow_mut().push(format!(
                "{} {} {}",
                request.issue, request.marker, request.repo
            ));
            EffectOutput {
                code: self.summary_code,
                stdout: "summary-out\n".to_owned(),
                stderr: self.summary_stderr.clone(),
            }
        }
    }

    /// A PEM opener the redactor must refuse, assembled at runtime so no secret
    /// scanner reads a contiguous key header out of this source file.
    fn unterminated_pem_body() -> String {
        format!("-----BEGIN {} KEY-----\nAAAA\n", "PRIVATE")
    }

    struct Session {
        _root: TempDir,
        tmpdir: PathBuf,
        log_root: PathBuf,
        issue_log: PathBuf,
        batch: PathBuf,
    }

    fn session(ledger: &str) -> Session {
        let root = TempDir::new().expect("temporary root must be creatable");
        let tmpdir = root.path().join("session");
        fs::create_dir_all(&tmpdir).expect("session directory must be creatable");
        let log_root = tmpdir.join("larch-logs");
        let issue_log = tmpdir.join(LEDGER_BASENAME);
        fs::write(&issue_log, ledger).expect("ledger must be writable");
        let batch = log_root
            .join("implement")
            .join("run-1")
            .join("execution-issues.ndjson");
        Session {
            _root: root,
            tmpdir,
            log_root,
            issue_log,
            batch,
        }
    }

    fn request<'a>(session: &'a Session, step: &'a str) -> FlushRequest<'a> {
        FlushRequest {
            log_root: &session.log_root,
            run_id: "run-1",
            issue_log: &session.issue_log,
            batch: "execution-issues",
            step_label: step,
            source_label: "execution-issues.md pre-bump",
        }
    }

    #[test]
    fn flush_refuses_a_relative_root_a_bad_slug_and_a_foreign_batch() {
        let session = session("### Warnings\n- one\n");
        let effects = FakeEffects::new(&session.batch);

        let relative = flush_with(
            &effects,
            &FlushRequest {
                log_root: Path::new("larch-logs"),
                ..request(&session, "7a")
            },
        );
        let slug = flush_with(
            &effects,
            &FlushRequest {
                run_id: "run 1",
                ..request(&session, "7a")
            },
        );
        let batch = flush_with(
            &effects,
            &FlushRequest {
                batch: "review-findings",
                ..request(&session, "7a")
            },
        );

        assert_eq!(
            (relative.rc, relative.status, relative.append_log.as_str()),
            (2, "failed", "--log-root must be absolute")
        );
        assert_eq!(
            (slug.rc, slug.append_log.as_str()),
            (
                2,
                "--run-id must contain only letters, numbers, and hyphens"
            )
        );
        assert_eq!(
            (batch.rc, batch.append_log.as_str()),
            (2, "--batch must be execution-issues")
        );
    }

    #[test]
    fn flush_refuses_a_symlinked_live_ledger_before_publishing() {
        let session = session("### Warnings\n- one\n");
        let target = session.tmpdir.join("real-ledger.md");
        fs::rename(&session.issue_log, &target).expect("move ledger");
        std::os::unix::fs::symlink(&target, &session.issue_log).expect("ledger symlink");
        let effects = FakeEffects::new(&session.batch);

        let outcome = flush_with(&effects, &request(&session, "7a"));

        assert_eq!((outcome.rc, outcome.status), (2, "failed"));
        assert!(effects.seen.borrow().is_empty());
        assert!(!session.batch.exists());
        assert_eq!(
            fs::read_to_string(target).expect("target ledger"),
            "### Warnings\n- one\n"
        );
    }

    #[test]
    fn flush_refuses_symlinked_sentinels_before_clearing_the_ledger() {
        for sentinel_name in [FLUSHED_SENTINEL, STEP7A_SENTINEL] {
            let session = session("### Warnings\n- one\n");
            let target = session.tmpdir.join(format!("real-{sentinel_name}"));
            fs::write(&target, "hostile sentinel\n").expect("sentinel target");
            std::os::unix::fs::symlink(&target, session.tmpdir.join(sentinel_name))
                .expect("sentinel symlink");
            let effects = FakeEffects::new(&session.batch);

            let outcome = flush_with(&effects, &request(&session, "7a"));

            assert_eq!((outcome.rc, outcome.status), (2, "failed"));
            assert!(effects.seen.borrow().is_empty());
            assert!(!session.batch.exists());
            assert_eq!(
                fs::read_to_string(&session.issue_log).expect("retained ledger"),
                "### Warnings\n- one\n"
            );
            assert_eq!(
                fs::read_to_string(target).expect("unchanged target"),
                "hostile sentinel\n"
            );
        }
    }

    #[test]
    fn flush_retains_and_records_the_ledger_when_post_append_capture_fails() {
        let session = session("### Warnings\n- one\n");
        let append_log = session.tmpdir.join(format!(
            "flush-execution-issues-append.{}.log",
            std::process::id()
        ));
        fs::create_dir(&append_log).expect("hostile append-log directory");
        let effects = FakeEffects::new(&session.batch);

        let outcome = flush_with(&effects, &request(&session, "7a"));

        assert_eq!((outcome.rc, outcome.status), (1, "failed"));
        let ledger = fs::read_to_string(&session.issue_log).expect("retained ledger");
        assert!(ledger.contains("- one"));
        assert!(ledger.contains("flush-execution-issues"));
        assert!(session.batch.is_file(), "the first append remains durable");
        assert!(!session.tmpdir.join(FLUSHED_SENTINEL).exists());
    }

    #[test]
    fn flush_skips_an_empty_ledger_but_still_records_the_checkpoint() {
        let session = session("");
        let effects = FakeEffects::new(&session.batch);

        let outcome = flush_with(&effects, &request(&session, "7a"));

        assert_eq!(
            (outcome.rc, outcome.status, outcome.records),
            (0, "skip", 0)
        );
        assert!(
            session
                .tmpdir
                .join(".execution-issues-step7a-reached")
                .is_file()
        );
        assert!(effects.seen.borrow().is_empty());
    }

    #[test]
    fn flush_at_another_step_does_not_record_the_step_7a_checkpoint() {
        let session = session("");
        let effects = FakeEffects::new(&session.batch);

        let outcome = flush_with(&effects, &request(&session, "18"));

        assert_eq!(outcome.status, "skip");
        assert!(
            !session
                .tmpdir
                .join(".execution-issues-step7a-reached")
                .exists()
        );
    }

    #[test]
    fn flush_publishes_clears_the_ledger_and_writes_the_sentinel() {
        let session = session("### Tool Failures\n\n- tool failed once\n");
        let effects = FakeEffects::new(&session.batch);

        let outcome = flush_with(&effects, &request(&session, "7a"));

        assert_eq!((outcome.rc, outcome.status, outcome.records), (0, "ok", 1));
        assert_eq!(
            fs::read_to_string(&session.issue_log).unwrap_or_default(),
            ""
        );
        assert!(
            session
                .tmpdir
                .join(".execution-issues-flushed.sha")
                .is_file()
        );
        assert!(Path::new(&outcome.append_log).is_file());
        assert!(effects.seen.borrow()[0].contains("\"category\":\"Tool Failures\""));
    }

    #[test]
    fn flush_is_a_no_op_when_its_own_sentinel_matches() {
        let session = session("### Warnings\n- one\n");
        let effects = FakeEffects::new(&session.batch);
        let first = flush_with(&effects, &request(&session, "7a"));
        fs::write(&session.issue_log, "### Warnings\n- one\n").expect("ledger must be writable");

        let second = flush_with(&effects, &request(&session, "7a"));

        assert_eq!(first.status, "ok");
        assert_eq!(
            (second.rc, second.status, second.records),
            (0, "already-flushed", 0)
        );
        assert_eq!(
            fs::read_to_string(&session.issue_log).unwrap_or_default(),
            ""
        );
        assert_eq!(effects.seen.borrow().len(), 1);
    }

    #[test]
    fn a_partial_flush_retries_without_publishing_its_rows_twice() {
        let session = session("### Warnings\n- one\n\n### Tool Failures\n- two\n");
        let effects = FakeEffects::new(&session.batch);
        let first = flush_with(&effects, &request(&session, "7a"));
        // The append landed but the process died before the sentinel write and
        // the ledger clear: restore exactly that state and retry.
        fs::remove_file(session.tmpdir.join(".execution-issues-flushed.sha"))
            .expect("sentinel must exist after a successful flush");
        fs::write(
            &session.issue_log,
            "### Warnings\n- one\n\n### Tool Failures\n- two\n",
        )
        .expect("ledger must be writable");

        let retry = flush_with(&effects, &request(&session, "7a"));

        assert_eq!((first.status, first.records), ("ok", 2));
        assert_eq!(retry.status, "already-flushed");
        assert_eq!(
            fs::read_to_string(&session.batch)
                .unwrap_or_default()
                .lines()
                .count(),
            2
        );
        assert_eq!(
            fs::read_to_string(&session.issue_log).unwrap_or_default(),
            ""
        );
    }

    #[test]
    fn a_flush_that_gained_one_entry_publishes_only_the_new_row() {
        let session = session("### Warnings\n- one\n");
        let effects = FakeEffects::new(&session.batch);
        let _first = flush_with(&effects, &request(&session, "7a"));
        fs::write(&session.issue_log, "### Warnings\n- one\n- two\n")
            .expect("ledger must be writable");

        let second = flush_with(&effects, &request(&session, "7a"));

        assert_eq!((second.status, second.records), ("ok", 1));
        assert_eq!(
            fs::read_to_string(&session.batch)
                .unwrap_or_default()
                .lines()
                .count(),
            2
        );
    }

    #[test]
    fn a_writer_that_appends_during_publication_is_never_cleared() {
        let session = session("### Warnings\n- original\n");
        let effects = FakeEffects {
            late_append: Some((session.issue_log.clone(), "- later".to_owned())),
            ..FakeEffects::new(&session.batch)
        };

        let first = flush_with(&effects, &request(&session, "7a"));

        assert_eq!((first.rc, first.status, first.records), (0, "ok", 1));
        let pending = fs::read_to_string(&session.issue_log).expect("pending ledger");
        assert!(pending.contains("- original"));
        assert!(pending.contains("- later"));

        let retry_effects = FakeEffects::new(&session.batch);
        let retry = flush_with(&retry_effects, &request(&session, "7a"));
        assert_eq!((retry.rc, retry.status, retry.records), (0, "ok", 1));
        assert_eq!(
            fs::read_to_string(&session.issue_log).expect("cleared ledger"),
            ""
        );
        assert_eq!(
            fs::read_to_string(&session.batch)
                .expect("durable batch")
                .lines()
                .count(),
            2
        );
    }

    #[test]
    fn flush_recognizes_a_whole_file_digest_an_older_writer_stored() {
        let session = session("### Warnings\n- one\n");
        let digest = sha256_file(&session.issue_log).expect("ledger must hash");
        fs::create_dir_all(session.batch.parent().expect("batch has a parent"))
            .expect("batch parent must be creatable");
        fs::write(
            &session.batch,
            format!("{{\"source_sha256\":\"{digest}\"}}\n"),
        )
        .expect("batch must be writable");
        let effects = FakeEffects::new(&session.batch);

        let outcome = flush_with(&effects, &request(&session, "7a"));

        assert_eq!(outcome.status, "already-flushed");
        assert!(effects.seen.borrow().is_empty());
    }

    #[test]
    fn flush_recognizes_its_own_rows_when_the_ledger_was_respelled() {
        let session = session("### Warnings\n- one\n");
        let effects = FakeEffects::new(&session.batch);
        let _first = flush_with(&effects, &request(&session, "7a"));
        // Same entry, a different byte sequence, and no sentinel: neither
        // digest matches, so only the per-entry identity can answer.
        fs::remove_file(session.tmpdir.join(".execution-issues-flushed.sha"))
            .expect("sentinel must exist after a successful flush");
        fs::write(&session.issue_log, "### Warnings\n\n- one\n\n")
            .expect("ledger must be writable");

        let outcome = flush_with(&effects, &request(&session, "7a"));

        assert_eq!(
            (outcome.rc, outcome.status, outcome.records),
            (0, "already-flushed", 0)
        );
        assert_eq!(
            fs::read_to_string(&session.issue_log).unwrap_or_default(),
            ""
        );
        assert_eq!(effects.seen.borrow().len(), 1);
    }

    #[test]
    fn a_failed_append_keeps_the_ledger_and_records_the_wrapper_failure() {
        let session = session("### Tool Failures\n\n- original failure\n");
        let effects = FakeEffects::failing(&session.batch);

        let outcome = flush_with(&effects, &request(&session, "7a"));

        let ledger = fs::read_to_string(&session.issue_log).unwrap_or_default();
        assert_eq!(
            (outcome.rc, outcome.status, outcome.records),
            (1, "failed", 0)
        );
        assert!(ledger.contains("- original failure"));
        assert!(ledger.contains("**flush-execution-issues**: run-log exited 9"));
        assert_eq!(
            fs::read_to_string(&outcome.append_log).unwrap_or_default(),
            "out\nerr\n"
        );
        assert!(
            !session
                .tmpdir
                .join(".execution-issues-flushed.sha")
                .exists()
        );
    }

    #[test]
    fn an_unspawnable_append_reports_that_it_could_not_run() {
        let session = session("### Warnings\n- one\n");
        let effects = FakeEffects {
            append_code: None,
            ..FakeEffects::new(&session.batch)
        };

        let outcome = flush_with(&effects, &request(&session, "7a"));

        assert_eq!((outcome.rc, outcome.status), (1, "failed"));
        assert!(
            fs::read_to_string(&session.issue_log)
                .unwrap_or_default()
                .contains("run-log could not run")
        );
    }

    #[test]
    fn a_refused_redaction_fails_the_flush_closed() {
        let session = session(&format!("### Warnings\n{}", unterminated_pem_body()));
        let effects = FakeEffects::new(&session.batch);

        let outcome = flush_with(&effects, &request(&session, "7a"));

        assert_eq!((outcome.rc, outcome.status), (1, "failed"));
        assert!(effects.seen.borrow().is_empty());
        assert!(
            fs::read_to_string(&session.issue_log)
                .unwrap_or_default()
                .contains("redaction failed for run-log batch payload")
        );
    }

    #[test]
    fn the_safety_net_publishes_without_clearing_the_ledger() {
        let session = session("### Warnings\n- one\n");
        let effects = FakeEffects::new(&session.batch);

        let outcome = flush_safety_net_with(&effects, &request(&session, "18"));

        assert_eq!((outcome.rc, outcome.status, outcome.records), (0, "ok", 1));
        assert_eq!(
            fs::read_to_string(&session.issue_log).unwrap_or_default(),
            "### Warnings\n- one\n"
        );
        assert!(
            !session
                .tmpdir
                .join(".execution-issues-flushed.sha")
                .exists()
        );
    }

    #[test]
    fn the_safety_net_ignores_sentinels_it_neither_reads_nor_writes() {
        for sentinel_name in [FLUSHED_SENTINEL, STEP7A_SENTINEL] {
            let session = session("### Warnings\n- one\n");
            let target = session.tmpdir.join(format!("real-{sentinel_name}"));
            fs::write(&target, "hostile sentinel\n").expect("sentinel target");
            std::os::unix::fs::symlink(&target, session.tmpdir.join(sentinel_name))
                .expect("sentinel symlink");
            let effects = FakeEffects::new(&session.batch);

            let outcome = flush_safety_net_with(&effects, &request(&session, "18"));

            assert_eq!((outcome.rc, outcome.status, outcome.records), (0, "ok", 1));
            assert_eq!(
                fs::read_to_string(&session.issue_log).expect("retained ledger"),
                "### Warnings\n- one\n"
            );
            assert_eq!(
                fs::read_to_string(target).expect("unchanged target"),
                "hostile sentinel\n"
            );
        }
    }

    #[test]
    fn the_safety_net_dedupes_rows_the_pre_push_flush_already_published() {
        let session = session("### Warnings\n\n- shared warning\n");
        let effects = FakeEffects::new(&session.batch);
        let _first = flush_safety_net_with(&effects, &request(&session, "18"));

        let second = flush_safety_net_with(&effects, &request(&session, "18"));

        assert_eq!(
            (second.rc, second.status, second.records),
            (0, "no-records", 0)
        );
        assert_eq!(
            fs::read_to_string(&session.batch)
                .unwrap_or_default()
                .lines()
                .count(),
            1
        );
    }

    #[test]
    fn the_safety_net_refuses_a_relative_root_and_skips_an_empty_ledger() {
        let session = session("");
        let effects = FakeEffects::new(&session.batch);

        let refused = flush_safety_net_with(
            &effects,
            &FlushRequest {
                log_root: Path::new("larch-logs"),
                ..request(&session, "18")
            },
        );
        let skipped = flush_safety_net_with(&effects, &request(&session, "18"));

        assert_eq!(refused.rc, 2);
        assert_eq!(skipped.status, "skip");
    }

    #[test]
    fn append_creates_a_section_inserts_into_one_and_stays_idempotent() {
        let root = TempDir::new().expect("temporary root must be creatable");
        let log = root.path().join("nested").join(LEDGER_BASENAME);

        append_execution_issue(&log, "Warnings", "- warning").expect("first append must succeed");
        append_execution_issue(&log, "Warnings", "- warning").expect("repeat append must succeed");
        append_execution_issue(&log, "Tool Failures", "- boom").expect("append must succeed");
        append_execution_issue(&log, "Warnings", "- second").expect("append must succeed");

        let text = fs::read_to_string(&log).unwrap_or_default();
        assert_eq!(text.matches("- warning").count(), 1);
        assert!(text.find("- second").is_some_and(|second| {
            text.find("### Tool Failures")
                .is_some_and(|failures| second < failures)
        }));
    }

    #[test]
    fn append_refuses_a_ledger_that_is_not_a_regular_file() {
        let root = TempDir::new().expect("temporary root must be creatable");
        let log = root.path().join("ledger-directory");
        fs::create_dir(&log).expect("directory must be creatable");

        let refused = append_execution_issue(&log, "Warnings", "- warning");

        assert!(refused.is_err_and(|message| message.contains("non-regular log file")));
    }

    #[test]
    fn the_key_value_reader_takes_the_first_row_and_strips_framing() {
        let root = TempDir::new().expect("temporary root must be creatable");
        let path = root.path().join("parent-issue.md");
        fs::write(&path, "RUN_ID=first\r\nRUN_ID=second\n").expect("file must be writable");

        assert_eq!(read_kv(&path, "RUN_ID"), "first");
        assert_eq!(read_kv(&path, "ABSENT"), "");
        assert_eq!(read_kv(&root.path().join("missing.md"), "RUN_ID"), "");
    }

    fn refresh_session(issue: &str) -> Session {
        let session = session("### Warnings\n- one\n- two\n");
        fs::write(
            session.tmpdir.join("parent-issue.md"),
            format!("ISSUE_NUMBER={issue}\nRUN_ID=run-1\n"),
        )
        .expect("parent issue must be writable");
        fs::write(
            session.tmpdir.join("session-env.sh"),
            "REPO=owner/name\nAGENT=claude\nCODER=codex\n",
        )
        .expect("session env must be writable");
        session
    }

    fn fixed_reference(_repo_root: Option<&Path>, run_id: &str, _manifest: &Path) -> String {
        format!("provider `s3`, skill `implement`, run ID `{run_id}`")
    }

    #[test]
    fn refresh_refuses_a_missing_session_directory_unless_best_effort() {
        let root = TempDir::new().expect("temporary root must be creatable");
        let missing = root.path().join("absent");
        let effects = FakeEffects::new(&missing);

        let strict = refresh_with(&effects, &missing, false, &fixed_reference);
        let lenient = refresh_with(&effects, &missing, true, &fixed_reference);

        assert_eq!((strict.rc, strict.refreshed), (2, false));
        assert_eq!(strict.detail, "--implement-tmpdir not found");
        assert_eq!(lenient.rc, 0);
    }

    #[test]
    fn refresh_reports_an_unset_issue_as_a_successful_skip() {
        let session = refresh_session("0");
        let effects = FakeEffects::new(&session.batch);

        let outcome = refresh_with(&effects, &session.tmpdir, false, &fixed_reference);

        assert_eq!((outcome.rc, outcome.refreshed), (0, true));
        assert_eq!(outcome.detail, "issue-not-set");
        assert!(effects.seen.borrow().is_empty());
    }

    #[test]
    fn refresh_refuses_a_non_numeric_issue_number() {
        let session = refresh_session("abc");
        let effects = FakeEffects::new(&session.batch);

        let strict = refresh_with(&effects, &session.tmpdir, false, &fixed_reference);
        let lenient = refresh_with(&effects, &session.tmpdir, true, &fixed_reference);

        assert_eq!((strict.rc, strict.refreshed), (1, false));
        assert_eq!(strict.detail, "ISSUE_NUMBER must be numeric");
        assert_eq!(lenient.rc, 0);
        assert!(
            fs::read_to_string(&session.issue_log)
                .expect("failure ledger")
                .contains("**refresh-execution-issues**: ISSUE_NUMBER must be numeric")
        );
    }

    #[test]
    fn refresh_refuses_symlinked_session_metadata_and_records_the_failure() {
        let session = refresh_session("42");
        let target = session.tmpdir.join("real-session-id");
        let link = session.tmpdir.join("session-id");
        fs::write(&target, "run-target\n").expect("session target");
        std::os::unix::fs::symlink(&target, &link).expect("session symlink");
        let effects = FakeEffects::new(&session.batch);

        let outcome = refresh_with(&effects, &session.tmpdir, false, &fixed_reference);

        assert_eq!((outcome.rc, outcome.refreshed), (1, false));
        assert_eq!(outcome.detail, "session metadata must not be symlinked");
        assert!(effects.seen.borrow().is_empty());
        assert!(
            fs::read_to_string(&session.issue_log)
                .expect("failure ledger")
                .contains("session metadata must not be symlinked")
        );
    }

    #[test]
    fn refresh_publishes_the_pending_count_and_captures_both_streams() {
        let session = refresh_session("42");
        let effects = FakeEffects::new(&session.batch);

        let outcome = refresh_with(&effects, &session.tmpdir, false, &fixed_reference);

        let summary =
            fs::read_to_string(session.tmpdir.join("summary-metadata.md")).unwrap_or_default();
        assert_eq!((outcome.rc, outcome.refreshed), (0, true));
        assert_eq!(
            summary,
            format!(
                "Run ID: `run-1`\nRun log: provider `s3`, skill `implement`, run ID `run-1`\nTracking issue: #42\nAgent: `claude`\nCoder: `codex`\nLarch version: `{}`\nExecution issues pending flush: `2`\n",
                plugin_version()
            )
        );
        assert_eq!(
            effects.seen.borrow()[0],
            "42 <!-- larch:metadata v1 runid=run-1 --> owner/name"
        );
        assert_eq!(
            fs::read_to_string(session.tmpdir.join("refresh-execution-issues.out"))
                .unwrap_or_default(),
            "summary-out\n"
        );
    }

    #[test]
    fn refresh_collapses_a_failed_publication_into_one_bounded_row() {
        let session = refresh_session("42");
        let effects = FakeEffects {
            summary_code: Some(2),
            summary_stderr: "FAILED=true\nERROR=no auth\n".to_owned(),
            ..FakeEffects::new(&session.batch)
        };

        let strict = refresh_with(&effects, &session.tmpdir, false, &fixed_reference);
        let lenient = refresh_with(&effects, &session.tmpdir, true, &fixed_reference);

        assert_eq!((strict.rc, strict.refreshed), (1, false));
        assert_eq!(strict.detail, "FAILED=true ERROR=no auth");
        assert_eq!(lenient.rc, 0);
        assert_eq!(
            fs::read_to_string(session.tmpdir.join("refresh-execution-issues.err"))
                .unwrap_or_default(),
            "FAILED=true\nERROR=no auth\n"
        );
        let ledger = fs::read_to_string(&session.issue_log).expect("failure ledger");
        assert_eq!(ledger.matches("**refresh-execution-issues**").count(), 1);
        assert!(ledger.contains("FAILED=true ERROR=no auth"));
    }

    #[test]
    fn refresh_falls_back_to_the_session_sentinel_for_its_run_slug() {
        let session = refresh_session("42");
        fs::write(session.tmpdir.join("parent-issue.md"), "ISSUE_NUMBER=42\n")
            .expect("parent issue must be writable");
        fs::write(session.tmpdir.join("session-id"), "run-sentinel\n")
            .expect("session id must be writable");
        let effects = FakeEffects::new(&session.batch);

        let outcome = refresh_with(&effects, &session.tmpdir, false, &fixed_reference);

        assert!(outcome.refreshed);
        assert!(effects.seen.borrow()[0].contains("runid=run-sentinel"));
    }

    #[test]
    fn a_re_run_refreshes_the_rows_it_owns_and_keeps_the_rest() {
        let session = refresh_session("42");
        let summary = session.tmpdir.join("summary-metadata.md");
        fs::write(
            &summary,
            "Run ID: `run-1`\nRun log: stale\nTracking issue: #42\nLogs: stale\nNote: keep me\nExecution issues pending flush: `9`\n",
        )
        .expect("summary must be writable");

        let body =
            compose_summary_metadata(&session.tmpdir, &summary, "42", "run-1", "fresh", "1.2.3")
                .expect("summary composition");

        assert_eq!(
            body,
            "Run ID: `run-1`\nRun log: fresh\nTracking issue: #42\nNote: keep me\nExecution issues pending flush: `2`\n"
        );
    }

    #[test]
    fn the_render_destination_must_sit_beside_the_staging_root() {
        let session = session("### Warnings\n- one\n");
        fs::create_dir_all(&session.log_root).expect("staging root must be creatable");
        let values = FlushArguments {
            log_root: session.log_root.to_string_lossy().into_owned(),
            run_id: "run-1".to_owned(),
            issue_log: session.issue_log.clone(),
            batch: "execution-issues".to_owned(),
            step_label: "18".to_owned(),
            source_label: "execution-issues.md safety-net".to_owned(),
        };
        let nested = session.tmpdir.join("nested");
        fs::create_dir_all(&nested).expect("nested directory must be creatable");

        assert!(confined_record_destination(
            &session.log_root,
            &session.tmpdir.join("records.ndjson"),
            &values
        ));
        assert!(!confined_record_destination(
            &session.log_root,
            &nested.join("records.ndjson"),
            &values
        ));
        assert!(!confined_record_destination(
            &session.log_root,
            Path::new("records.ndjson"),
            &values
        ));
        assert!(!confined_record_destination(
            &session.tmpdir,
            &session.tmpdir.join("records.ndjson"),
            &values
        ));
        let hostile_batch_root = session.tmpdir.join("hostile-batch-root");
        fs::create_dir(&hostile_batch_root).expect("hostile batch root");
        std::os::unix::fs::symlink(&hostile_batch_root, session.log_root.join("implement"))
            .expect("batch ancestor symlink");
        assert!(!confined_record_destination(
            &session.log_root,
            &session.tmpdir.join("records.ndjson"),
            &values
        ));
        assert!(!confined_record_destination(
            &session.log_root,
            &session.tmpdir.join("records.ndjson"),
            &FlushArguments {
                run_id: "run 1".to_owned(),
                ..values
            }
        ));
    }

    #[test]
    fn composing_records_publishes_an_empty_file_for_an_empty_ledger() {
        let session = session("");
        let destination = session.tmpdir.join("records.ndjson");

        let composed = write_execution_issue_records(
            &session.issue_log,
            &destination,
            None,
            RecordLabels {
                step: "18",
                source: "test",
            },
        );

        assert_eq!(composed, Ok(0));
        assert_eq!(fs::read_to_string(&destination).unwrap_or_default(), "");
    }

    #[test]
    fn a_manifest_pins_disabled_publication_only_when_every_field_agrees() {
        let root = TempDir::new().expect("temporary root must be creatable");
        let manifest = root.path().join("manifest.json");
        let namespace = "a".repeat(64);
        let pinned = format!(
            "{{\"lifecycle_schema_version\":3,\"publication_mode\":\"disabled\",\"storage_resolution_reason\":\"config-file-missing\",\"skill\":\"implement\",\"run_id\":\"run-1\",\"local_namespace_id\":\"{namespace}\"}}"
        );
        fs::write(&manifest, &pinned).expect("manifest must be writable");

        assert!(pins_disabled_publication("implement", &manifest, "run-1"));
        assert!(!pins_disabled_publication("implement", &manifest, "run-2"));
        assert!(!pins_disabled_publication(
            "implement",
            &root.path().join("absent.json"),
            "run-1"
        ));
        fs::write(
            &manifest,
            pinned.replace("config-file-missing", "provider-configured"),
        )
        .expect("manifest must be writable");
        assert!(!pins_disabled_publication("implement", &manifest, "run-1"));
        fs::write(&manifest, "not json").expect("manifest must be writable");
        assert!(!pins_disabled_publication("implement", &manifest, "run-1"));
    }

    #[test]
    fn a_pinned_manifest_names_the_disabled_archive_without_reading_a_clone() {
        let root = TempDir::new().expect("temporary root must be creatable");
        let manifest = root.path().join("manifest.json");
        let namespace = "b".repeat(64);
        fs::write(
            &manifest,
            format!(
                "{{\"lifecycle_schema_version\":3,\"publication_mode\":\"disabled\",\"storage_resolution_reason\":\"larch-table-missing\",\"skill\":\"implement\",\"run_id\":\"run-9\",\"local_namespace_id\":\"{namespace}\"}}"
            ),
        )
        .expect("manifest must be writable");

        assert_eq!(
            run_log_reference("implement", None, "run-9", &manifest),
            "no archive published because run-log storage was disabled, skill `implement`, run ID `run-9`"
        );
        assert_eq!(
            run_log_reference("implement", None, "run-9", &root.path().join("absent.json")),
            "provider `unknown`, skill `implement`, run ID `run-9`"
        );
    }

    #[test]
    fn a_diagnostic_collapses_whitespace_and_stays_bounded() {
        assert_eq!(collapsed_diagnostic("  a\n\n b  "), "a b");
        assert_eq!(collapsed_diagnostic(&"x".repeat(900)).len(), 500);
    }

    fn argv(values: &[&str]) -> Vec<std::ffi::OsString> {
        values.iter().map(std::ffi::OsString::from).collect()
    }

    fn code(actual: ExitCode) -> String {
        format!("{actual:?}")
    }

    #[test]
    fn the_append_entrypoint_writes_one_entry_and_refuses_a_bad_line() {
        let root = TempDir::new().expect("temporary root must be creatable");
        let log = root.path().join(LEDGER_BASENAME);
        let path = log.to_string_lossy().into_owned();

        let written = append(&argv(&["--log", &path, "--entry", "- boom"]));
        let missing_entry = append(&argv(&["--log", &path]));
        let unknown = append(&argv(&["--log", &path, "--entry", "- x", "--help"]));

        assert_eq!(code(written), code(ExitCode::SUCCESS));
        assert_eq!(
            fs::read_to_string(&log).unwrap_or_default(),
            "### Tool Failures\n- boom\n"
        );
        assert_eq!(code(missing_entry), code(ExitCode::from(2)));
        assert_eq!(code(unknown), code(ExitCode::from(2)));
    }

    #[test]
    fn the_append_entrypoint_reports_a_ledger_it_cannot_write() {
        let root = TempDir::new().expect("temporary root must be creatable");
        let directory = root.path().join("ledger-directory");
        fs::create_dir(&directory).expect("directory must be creatable");

        let refused = append(&argv(&[
            "--log",
            &directory.to_string_lossy(),
            "--entry",
            "- boom",
            "--category",
            "Warnings",
        ]));

        assert_eq!(code(refused), code(ExitCode::FAILURE));
    }

    #[test]
    fn both_flush_entrypoints_refuse_a_line_they_cannot_use() {
        let usage = flush(&argv(&[]));
        let relative = flush(&argv(&["--log-root", "larch-logs", "--run-id", "run-1"]));
        let net_usage = flush_safety_net(&argv(&["--log-root", "/tmp"]));

        assert_eq!(code(usage), code(ExitCode::from(2)));
        assert_eq!(code(relative), code(ExitCode::from(2)));
        assert_eq!(code(net_usage), code(ExitCode::from(2)));
    }

    #[test]
    fn the_record_mode_renders_beside_the_staging_root_and_refuses_elsewhere() {
        let session = session("### Warnings\n- one\n");
        fs::create_dir_all(&session.log_root).expect("staging root must be creatable");
        let destination = session.tmpdir.join("records.ndjson");
        let nested = session.tmpdir.join("nested");
        fs::create_dir_all(&nested).expect("nested directory must be creatable");
        let line = |record: &Path| {
            argv(&[
                "--log-root",
                &session.log_root.to_string_lossy(),
                "--run-id",
                "run-1",
                "--issue-log",
                &session.issue_log.to_string_lossy(),
                "--record-file",
                &record.to_string_lossy(),
            ])
        };

        let rendered = flush_safety_net(&line(&destination));
        let refused = flush_safety_net(&line(&nested.join("records.ndjson")));

        assert_eq!(code(rendered), code(ExitCode::SUCCESS));
        assert_eq!(
            fs::read_to_string(&destination)
                .unwrap_or_default()
                .lines()
                .count(),
            1
        );
        assert_eq!(code(refused), code(ExitCode::from(2)));
        assert!(!nested.join("records.ndjson").exists());
    }

    #[test]
    fn the_record_mode_publishes_an_empty_file_for_an_empty_ledger() {
        let session = session("");
        fs::create_dir_all(&session.log_root).expect("staging root must be creatable");
        let destination = session.tmpdir.join("records.ndjson");

        let rendered = flush_safety_net(&argv(&[
            "--log-root",
            &session.log_root.to_string_lossy(),
            "--run-id",
            "run-1",
            "--issue-log",
            &session.issue_log.to_string_lossy(),
            "--record-file",
            &destination.to_string_lossy(),
        ]));

        assert_eq!(code(rendered), code(ExitCode::SUCCESS));
        assert_eq!(fs::read_to_string(&destination).unwrap_or_default(), "");
    }

    #[test]
    fn the_refresh_entrypoint_refuses_an_unusable_line_and_tolerates_best_effort() {
        let root = TempDir::new().expect("temporary root must be creatable");
        let missing = root.path().join("absent");

        let unknown = refresh(&argv(&["--help"]));
        let lenient = refresh(&argv(&[
            "--implement-tmpdir",
            &missing.to_string_lossy(),
            "--best-effort",
        ]));
        let strict = refresh(&argv(&["--implement-tmpdir", &missing.to_string_lossy()]));

        assert_eq!(code(unknown), code(ExitCode::from(2)));
        assert_eq!(code(lenient), code(ExitCode::SUCCESS));
        assert_eq!(code(strict), code(ExitCode::from(2)));
    }

    #[test]
    fn the_flush_option_table_defaults_per_verb_and_needs_both_identity_options() {
        let full = parse_with_flags(
            &argv(&["--log-root", "/tmp/larch-logs", "--run-id", "run-1"]),
            &[
                "--log-root",
                "--run-id",
                "--issue-log",
                "--batch",
                "--step-label",
                "--source-label",
            ],
            &[],
            0,
        );
        let partial = parse_with_flags(&argv(&["--log-root", "/tmp"]), &["--log-root"], &[], 0);

        let values = flush_arguments(&full, "7a", "execution-issues.md pre-bump")
            .expect("both identity options are present");
        assert_eq!(values.batch, "execution-issues");
        assert_eq!(values.step_label, "7a");
        assert_eq!(values.source_label, "execution-issues.md pre-bump");
        assert!(values.issue_log.ends_with(LEDGER_BASENAME));
        assert!(flush_arguments(&partial, "18", "safety-net").is_none());
    }
}
