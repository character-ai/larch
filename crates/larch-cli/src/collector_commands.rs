//! `agent collect-results`: collect, validate, and retry external reviewer output.
//!
//! One reviewer launch publishes an output file, a `.done` sentinel carrying the
//! launcher exit code, and optional `.meta`, `.diag`, and stderr sidecars. This
//! command waits for every sentinel, classifies each reviewer, retries the one
//! failure class the retired collector retried, optionally runs the substantive
//! and structured validators, and publishes one `KEY=value` block per reviewer.
//!
//! The command owns no vendor spawn: a retry re-enters `agent
//! run-external-agent`, `agent launch-review`, or `agent launch-codex-exec`
//! through the verified bootstrap, and those launchers own the vendor process.

use std::{
    collections::BTreeMap,
    env,
    ffi::OsString,
    fs,
    num::NonZeroUsize,
    path::{Path, PathBuf},
    process::ExitCode,
    sync::Arc,
    thread::{self, JoinHandle},
    time::Duration,
};

use larch_adapters::{
    NoopProcessObserver, TokioProcessRunner,
    runtime::{Cancellation, LarchRuntime},
};
use larch_core::{
    ChildEnvironment, CursorCredential, DuplicatePolicy, EXTERNAL_TOOL_NAMES,
    ExternalProcessRunner as _, ExternalProgram, FAILED_AGENT_STDERR_TAIL_BYTE_CAP,
    FAILED_AGENT_STDERR_TAIL_LINES, KvDocument, LarchProgram, LauncherArtifactKind, ParseOptions,
    ProcessRequest, ReviewerWaitConfig, ReviewerWaitRow, SafeText, cursor_child_environment,
    render_failed_agent_stderr_tail, wait_for_reviewers,
};
use regex::Regex;
use serde_json::Value;

use crate::agent_commands::{AgentRawArguments, SystemWaitHost, WaitBreadcrumbs};
use crate::git_commands::is_transient_net;
use crate::launcher_support::{is_non_empty_file, read_text};
use crate::python_verb::plugin_root_directory;
use crate::waterfall_commands::inherited_child_rows;

const PROG: &str = "collect-results";
const USAGE: &str = concat!(
    "Usage: larch agent collect-results --timeout <seconds> ",
    "[--substantive-validation [--validation-mode]] [--structured-reviewer-validation] ",
    "[--summary-only] [--paths-file <file>] <output-file>..."
);

/// Sentinel exit code the launchers publish for a vendor timeout.
const TIMEOUT_EXIT: &str = "124";
/// Slack added to a retry's own deadline before the runner terminates it.
const RETRY_WAIT_GRACE: u64 = 60;
/// Character budget for a published `FAILURE_REASON`.
const REASON_LIMIT: usize = 500;
/// Character budget for a validator-sourced `FAILURE_REASON`.
const VALIDATION_REASON_LIMIT: usize = 200;
const STATUS_CURSOR_EMPTY: &str = "CURSOR_EMPTY_RESPONSE";
const STATUS_CURSOR_DEGRADED: &str = "CURSOR_DEGRADED_RESPONSE";
const STATUS_OK: &str = "OK";
const STATUS_CAP_HIT: &str = "cap_hit";
const STATUS_EMPTY_OUTPUT: &str = "EMPTY_OUTPUT";
const STATUS_FAILED: &str = "FAILED";
const STATUS_TIMED_OUT: &str = "TIMED_OUT";
const STATUS_SENTINEL_TIMEOUT: &str = "SENTINEL_TIMEOUT";
const STATUS_NOT_SUBSTANTIVE: &str = "NOT_SUBSTANTIVE";
/// Largest exit code a sentinel may carry before it is coerced to 99.
const MAX_EXIT_CODE: u32 = 255;
/// Validator exit meaning the reviewer file held no usable output.
const EXIT_OUTPUT_EMPTY: i32 = 4;
/// Validator exit meaning a Cursor lane returned an empty or degraded response.
const EXIT_VALIDATION_CURSOR_EMPTY: i32 = 5;
/// Bounded capture for one retry child's discarded streams.
const RETRY_OUTPUT_LIMIT: usize = 256 * 1024;
/// Grace period before a retry child's process group is killed.
const RETRY_SHUTDOWN_GRACE: Duration = Duration::from_secs(5);
/// Poll interval for the collector's own sentinel waits.
const WAIT_POLL_INTERVAL: Duration = Duration::from_secs(1);

// ---------------------------------------------------------------------------
// Published record
// ---------------------------------------------------------------------------

/// One reviewer's published verdict.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct CollectorRecord {
    reviewer_file: String,
    tool: String,
    status: String,
    exit_code: String,
    structured_sidecar: String,
    failure_reason: String,
    ns_retry_mode: String,
    ns_retry_reason: String,
}

impl CollectorRecord {
    fn new(reviewer_file: &str, tool: &str, status: &str, exit_code: &str) -> Self {
        Self {
            reviewer_file: reviewer_file.to_owned(),
            tool: tool.to_owned(),
            status: status.to_owned(),
            exit_code: exit_code.to_owned(),
            ..Self::default()
        }
    }

    fn with_reason(mut self, reason: &str) -> Self {
        reason.clone_into(&mut self.failure_reason);
        self
    }

    fn with_ns_retry(mut self, kind: ValidationKind, validator_exit: i32) -> Self {
        kind.mode().clone_into(&mut self.ns_retry_mode);
        ns_retry_reason(validator_exit, kind).clone_into(&mut self.ns_retry_reason);
        self
    }

    /// Return the reviewer output path this record describes.
    #[must_use]
    pub fn reviewer_file(&self) -> &str {
        &self.reviewer_file
    }

    /// Return the published status label.
    #[must_use]
    pub fn status(&self) -> &str {
        &self.status
    }

    /// Return the published fields in wire order.
    fn fields(&self, publication: Publication) -> Vec<(&'static str, &str)> {
        let mut fields = vec![
            ("REVIEWER_FILE", self.reviewer_file.as_str()),
            ("TOOL", self.tool.as_str()),
            ("STATUS", self.status.as_str()),
            ("EXIT_CODE", self.exit_code.as_str()),
        ];
        if publication == Publication::SummaryOnly {
            return fields;
        }
        fields.push(("STRUCTURED_SIDECAR", self.structured_sidecar.as_str()));
        fields.push(("FAILURE_REASON", self.failure_reason.as_str()));
        if !self.ns_retry_mode.is_empty() {
            fields.push(("NS_RETRY_MODE", self.ns_retry_mode.as_str()));
        }
        if !self.ns_retry_reason.is_empty() {
            fields.push(("NS_RETRY_REASON", self.ns_retry_reason.as_str()));
        }
        fields
    }
}

/// Everything one collection published: the per-reviewer records and its notes.
pub struct CollectorOutcome {
    /// One record per requested output file, in request order.
    pub records: Vec<CollectorRecord>,
    /// Operator-facing diagnostic lines, already redacted.
    pub diagnostics: Vec<String>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct StructuredReviewerRow {
    pub scope: String,
    pub severity: String,
    pub focus_area: String,
    pub location: String,
    pub what: String,
    pub scenario: String,
    pub suggested_fix: String,
}

// ---------------------------------------------------------------------------
// Options
// ---------------------------------------------------------------------------

/// How the substantive-content validator treats each `OK` reviewer.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum SubstantiveValidation {
    /// Skip substantive-content validation.
    Off,
    /// Validate with the default prose thresholds.
    Default,
    /// Validate with the short reviewer-output preset (`--validation-mode`).
    ShortReviewer,
}

/// Whether the structured-reviewer validator writes per-reviewer sidecars.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum StructuredValidation {
    /// Skip structured-reviewer validation.
    Off,
    /// Validate and publish a `STRUCTURED_SIDECAR` per accepted reviewer.
    On,
}

/// How much of each record reaches the contract stream.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Publication {
    /// Publish every field and the failed-agent stderr excerpts.
    Full,
    /// Publish only the four summary fields and no excerpts.
    SummaryOnly,
}

/// One validated collection request.
pub struct CollectorOptions {
    /// Sentinel wait budget in whole seconds.
    pub timeout: u64,
    /// Reviewer output paths, in publication order.
    pub output_files: Vec<String>,
    /// Substantive-content validation policy.
    pub substantive: SubstantiveValidation,
    /// Structured-reviewer validation policy.
    pub structured: StructuredValidation,
    /// Publication policy for the emitted records.
    pub publication: Publication,
}

enum ParsedArguments {
    Help,
    Error(String),
    Parsed(Box<CollectorOptions>),
}

/// Run `agent collect-results` and return its process exit status.
pub fn collect_results(arguments: &AgentRawArguments) -> ExitCode {
    let options = match parse_arguments(&arguments.arguments) {
        ParsedArguments::Help => {
            eprintln!("{USAGE}");
            return ExitCode::SUCCESS;
        }
        ParsedArguments::Error(message) => {
            eprintln!("{}", SafeText::diagnostic(message).as_str());
            return ExitCode::from(1);
        }
        ParsedArguments::Parsed(options) => options,
    };
    let outcome = collect(&options);
    for line in &outcome.diagnostics {
        eprintln!("{line}");
    }
    emit_records(&outcome.records, options.publication);
    ExitCode::SUCCESS
}

fn parse_arguments(arguments: &[OsString]) -> ParsedArguments {
    let mut timeout_raw = String::new();
    let mut paths_file = String::new();
    let mut outputs: Vec<String> = Vec::new();
    let mut substantive = false;
    let mut validation_mode = false;
    let mut structured = false;
    let mut summary_only = false;
    let mut index = 0_usize;
    while index < arguments.len() {
        let argument = arguments[index].to_string_lossy().into_owned();
        match argument.as_str() {
            "--timeout" | "--paths-file" => {
                let Some(value) = arguments.get(index + 1) else {
                    return ParsedArguments::Error(format!("{argument} requires a value"));
                };
                let value = value.to_string_lossy().into_owned();
                if argument == "--timeout" {
                    timeout_raw = value;
                } else {
                    paths_file = value;
                }
                index += 2;
            }
            "--substantive-validation" => {
                substantive = true;
                index += 1;
            }
            "--validation-mode" => {
                validation_mode = true;
                index += 1;
            }
            "--structured-reviewer-validation" => {
                structured = true;
                index += 1;
            }
            "--summary-only" => {
                summary_only = true;
                index += 1;
            }
            "--help" => return ParsedArguments::Help,
            other if other.starts_with('-') => {
                return ParsedArguments::Error(format!("{PROG}: unknown option: {other}"));
            }
            other => {
                outputs.push(other.to_owned());
                index += 1;
            }
        }
    }
    if timeout_raw.is_empty() {
        return ParsedArguments::Error(format!("{PROG}: --timeout is required"));
    }
    let Some(timeout) = positive_seconds(&timeout_raw) else {
        return ParsedArguments::Error(format!(
            "Error: --timeout value must be a positive integer, got '{timeout_raw}'"
        ));
    };
    if !paths_file.is_empty() && !outputs.is_empty() {
        return ParsedArguments::Error(format!(
            "{PROG}: --paths-file is mutually exclusive with positional output-file arguments"
        ));
    }
    if !paths_file.is_empty() {
        match paths_from_file(&paths_file) {
            Ok(parsed) => outputs = parsed,
            Err(message) => return ParsedArguments::Error(message),
        }
    }
    if outputs.is_empty() {
        return ParsedArguments::Error(format!("{PROG}: at least one output file is required"));
    }
    ParsedArguments::Parsed(Box::new(CollectorOptions {
        timeout,
        output_files: outputs,
        substantive: match (substantive, validation_mode) {
            (false, _ignored) => SubstantiveValidation::Off,
            (true, false) => SubstantiveValidation::Default,
            (true, true) => SubstantiveValidation::ShortReviewer,
        },
        structured: if structured {
            StructuredValidation::On
        } else {
            StructuredValidation::Off
        },
        publication: if summary_only {
            Publication::SummaryOnly
        } else {
            Publication::Full
        },
    }))
}

fn positive_seconds(raw: &str) -> Option<u64> {
    if raw.is_empty() || !raw.bytes().all(|byte| byte.is_ascii_digit()) {
        return None;
    }
    raw.parse::<u64>().ok().filter(|value| *value >= 1)
}

fn paths_from_file(path: &str) -> Result<Vec<String>, String> {
    let candidate = Path::new(path);
    let Ok(metadata) = fs::metadata(candidate) else {
        return Err(format!("{PROG}: paths-file not readable: {path}"));
    };
    if !metadata.is_file() {
        return Err(format!("{PROG}: paths-file is not a regular file: {path}"));
    }
    let Ok(text) = fs::read(candidate) else {
        return Err(format!("{PROG}: paths-file not readable: {path}"));
    };
    let text = String::from_utf8_lossy(&text).into_owned();
    let outputs: Vec<String> = text
        .lines()
        .filter(|line| !line.trim().is_empty())
        .map(str::to_owned)
        .collect();
    if outputs.is_empty() {
        return Err(format!(
            "{PROG}: paths-file contains no entries (preserves anti-pattern #4)"
        ));
    }
    Ok(outputs)
}

fn emit_records(records: &[CollectorRecord], publication: Publication) {
    print!("{}", render_records(records, publication));
}

pub fn render_records(records: &[CollectorRecord], publication: Publication) -> String {
    let mut rendered = String::new();
    for (position, record) in records.iter().enumerate() {
        if position > 0 {
            rendered.push('\n');
        }
        for (key, value) in record.fields(publication) {
            rendered.push_str(key);
            rendered.push('=');
            rendered.push_str(value);
            rendered.push('\n');
        }
    }
    rendered
}

pub fn structured_reviewer_rows(path: &Path, review_tmpdir: &Path) -> Vec<StructuredReviewerRow> {
    if !is_non_empty_file(path) {
        return Vec::new();
    }
    let Ok(temporary) = tempfile::Builder::new()
        .prefix("collect-tsv.")
        .suffix(".tsv")
        .tempfile_in(review_tmpdir)
    else {
        return Vec::new();
    };
    let sidecar = temporary.into_temp_path();
    let result = run_validator(&[
        "--structured-reviewer-mode".to_owned(),
        "--write-structured".to_owned(),
        sidecar.display().to_string(),
        path.display().to_string(),
    ]);
    if result.exit_code != 0 {
        return Vec::new();
    }
    let Ok(text) = fs::read_to_string(&sidecar) else {
        return Vec::new();
    };
    text.lines()
        .filter_map(|line| {
            let columns = line.splitn(8, '\t').collect::<Vec<_>>();
            if columns.first() == Some(&"schema_version") || columns.len() < 8 {
                return None;
            }
            Some(StructuredReviewerRow {
                scope: columns[1].to_owned(),
                severity: columns[2].to_owned(),
                focus_area: columns[3].to_owned(),
                location: columns[4].to_owned(),
                what: columns[5].to_owned(),
                scenario: columns[6].to_owned(),
                suggested_fix: columns[7].to_owned(),
            })
        })
        .collect()
}

// ---------------------------------------------------------------------------
// Collection
// ---------------------------------------------------------------------------

/// Collect one batch of reviewer outputs and return its records and notes.
///
/// The caller decides where the diagnostics go: the command prints them to
/// standard error, and a dispatcher that asked for a summary drops them.
#[must_use]
pub fn collect(options: &CollectorOptions) -> CollectorOutcome {
    let mut notes: Vec<String> = Vec::new();
    let timed_out = initial_wait(options);
    let (mut records, mut plans) = build_initial_records(options, &timed_out, &mut notes);
    for plan in &mut plans {
        launch_retry_plan(plan, &mut records);
    }
    wait_retry_plans(&mut plans);
    apply_retry_results(&mut records, &plans, &mut notes);
    if options.substantive != SubstantiveValidation::Off {
        validate_substantive(&mut records, options.substantive);
    }
    if options.structured == StructuredValidation::On {
        validate_structured(&mut records, &mut notes);
    }
    if options.substantive != SubstantiveValidation::Off
        || options.structured == StructuredValidation::On
    {
        note_not_substantive(&records, &mut notes);
    }
    if options.publication == Publication::Full {
        note_failed_agent_stderr_tails(&records, &mut notes);
    }
    CollectorOutcome {
        records,
        diagnostics: notes,
    }
}

fn note(notes: &mut Vec<String>, message: &str) {
    notes.push(SafeText::diagnostic(message).as_str().to_owned());
}

fn initial_wait(options: &CollectorOptions) -> Vec<usize> {
    let sentinels: Vec<PathBuf> = options
        .output_files
        .iter()
        .map(|path| PathBuf::from(format!("{path}{}", LauncherArtifactKind::Done.suffix())))
        .collect();
    wait_for_sentinels(&sentinels, options.timeout)
}

/// Wait for every reviewer sentinel and return the one-based timed-out slots.
///
/// The retired collector ran `agent wait-reviewers` as a child and discarded
/// its captured streams on success, so the poll breadcrumbs never reached the
/// operator. Running the shared wait loop in process under the discarding
/// breadcrumb policy keeps that contract.
fn wait_for_sentinels(sentinels: &[PathBuf], timeout: u64) -> Vec<usize> {
    if sentinels.is_empty() {
        return Vec::new();
    }
    let mut host = SystemWaitHost::new(WaitBreadcrumbs::Discard);
    let result = wait_for_reviewers(
        &mut host,
        sentinels,
        ReviewerWaitConfig::new(timeout, WAIT_POLL_INTERVAL),
    );
    result
        .rows()
        .iter()
        .filter_map(|row| match row {
            ReviewerWaitRow::Timeout { index, .. } => Some(*index),
            ReviewerWaitRow::Done { .. } => None,
        })
        .collect()
}

// ---------------------------------------------------------------------------
// Classification
// ---------------------------------------------------------------------------

fn sanitize_failure_reason(text: &str, limit: usize) -> String {
    let flattened: String = text
        .chars()
        .map(|character| {
            if character == '|' || character == '\r' || character == '\n' {
                ' '
            } else {
                character
            }
        })
        .collect();
    let one_line = collapse_whitespace(&flattened);
    if one_line.chars().count() > limit {
        let keep = limit.saturating_sub(3);
        let head: String = one_line.chars().take(keep).collect();
        return format!("{head}...");
    }
    one_line
}

fn collapse_whitespace(text: &str) -> String {
    let mut out = String::with_capacity(text.len());
    let mut pending_space = false;
    for character in text.chars() {
        if character.is_whitespace() {
            pending_space = !out.is_empty();
            continue;
        }
        if pending_space {
            out.push(' ');
            pending_space = false;
        }
        out.push(character);
    }
    out
}

fn read_nonempty(path: &Path) -> String {
    if is_non_empty_file(path) {
        read_text(path)
    } else {
        String::new()
    }
}

fn sidecar(output: &str, kind: LauncherArtifactKind) -> PathBuf {
    PathBuf::from(format!("{output}{}", kind.suffix()))
}

/// Compose the published `FAILURE_REASON` for one failed reviewer.
fn build_failure_reason(output_file: &str, status: &str, exit_code: &str) -> String {
    let raw = read_nonempty(&sidecar(output_file, LauncherArtifactKind::Diag));
    let raw = if raw.is_empty() {
        match status {
            STATUS_SENTINEL_TIMEOUT => {
                "Process did not complete (sentinel file missing - possible crash or system kill)"
                    .to_owned()
            }
            STATUS_TIMED_OUT => "Process timed out (exit code 124)".to_owned(),
            STATUS_FAILED => format!("Process failed with exit code {exit_code}"),
            STATUS_EMPTY_OUTPUT => "Process exited successfully but produced no output".to_owned(),
            other => format!("Unknown failure (status={other}, exit_code={exit_code})"),
        }
    } else {
        raw
    };
    sanitize_failure_reason(&raw, REASON_LIMIT)
}

fn has_transient_diag(output_file: &str) -> bool {
    let raw = read_nonempty(&sidecar(output_file, LauncherArtifactKind::Diag));
    !raw.is_empty() && is_transient_net(&raw)
}

/// Normalize one sentinel exit code, coercing anything unusable to 99.
fn normalize_exit_code(raw: &str, context: &str, notes: &mut Vec<String>) -> (String, bool) {
    let value = raw.trim_end_matches('\n');
    let usable = !value.is_empty()
        && value.len() <= 3
        && value.bytes().all(|byte| byte.is_ascii_digit())
        && value
            .parse::<u32>()
            .is_ok_and(|parsed| parsed <= MAX_EXIT_CODE);
    if usable {
        return (value.to_owned(), false);
    }
    note(
        notes,
        &format!("{PROG}: invalid exit code from {context}; forcing EXIT_CODE=99"),
    );
    ("99".to_owned(), true)
}

fn read_sentinel_exit(path: &Path, context: &str, notes: &mut Vec<String>) -> (String, bool) {
    let raw = fs::read(path).map_or_else(
        |_error| "99".to_owned(),
        |bytes| String::from_utf8_lossy(&bytes).into_owned(),
    );
    normalize_exit_code(&raw, context, notes)
}

/// Report whether a Cursor lane published a narration-only or degraded reply.
fn is_cursor_degraded_response(path: &str) -> bool {
    let text = read_text(Path::new(path));
    text.lines()
        .map(str::trim)
        .find(|line| !line.is_empty())
        .is_some_and(|line| line == STATUS_CURSOR_EMPTY || line == STATUS_CURSOR_DEGRADED)
}

fn retry_output_path(output: &str) -> String {
    let base = output.strip_suffix(".txt").unwrap_or(output);
    format!("{base}-retry.txt")
}

/// Which validator produced a non-substantive verdict.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum ValidationKind {
    /// The substantive-content validator.
    Substantive,
    /// The structured-reviewer validator.
    Structured,
}

impl ValidationKind {
    const fn mode(self) -> &'static str {
        match self {
            Self::Substantive => "substantive",
            Self::Structured => "structured",
        }
    }
}

/// Map one validator exit code to the published non-substantive retry reason.
#[must_use]
const fn ns_retry_reason(validator_exit: i32, kind: ValidationKind) -> &'static str {
    match kind {
        ValidationKind::Structured => {
            if validator_exit == EXIT_VALIDATION_CURSOR_EMPTY {
                "JSON_PARSE_FAIL"
            } else {
                "UNKNOWN"
            }
        }
        ValidationKind::Substantive => match validator_exit {
            2 | 3 => "NO_ISSUES_FOUND_TOO_THIN",
            EXIT_OUTPUT_EMPTY => "OUTPUT_EMPTY",
            _other => "UNKNOWN",
        },
    }
}

// ---------------------------------------------------------------------------
// Launch metadata
// ---------------------------------------------------------------------------

/// One reviewer's `.meta` record, read with last-key-wins selection.
#[derive(Default)]
struct RetryMeta {
    rows: BTreeMap<String, String>,
}

impl RetryMeta {
    fn read(path: &Path) -> Self {
        let text = read_text(path);
        let rows = KvDocument::parse(&text, ParseOptions::legacy()).map_or_else(
            |_error| BTreeMap::new(),
            |document| document.select(DuplicatePolicy::Last),
        );
        Self { rows }
    }

    fn get(&self, key: &str) -> &str {
        self.rows.get(key).map_or("", String::as_str)
    }

    fn model_role(&self) -> &str {
        self.rows
            .get("OUTER_LAUNCHER_MODEL_ROLE")
            .map_or("default", String::as_str)
    }

    fn has_outer_launcher(&self) -> bool {
        !self.get("OUTER_LAUNCHER").is_empty()
            || !self.get("OUTER_LAUNCHER_PROMPT_FILE").is_empty()
            || !self.get("OUTER_LAUNCHER_WORKDIR").is_empty()
    }
}

fn registered_tool(name: &str) -> bool {
    EXTERNAL_TOOL_NAMES.contains(&name)
}

/// Attribute one output file to the vendor that produced it.
fn derive_tool(output_file: &str) -> String {
    let meta = RetryMeta::read(&sidecar(output_file, LauncherArtifactKind::Meta));
    let declared = meta.get("TOOL");
    if registered_tool(declared) {
        return declared.to_owned();
    }
    let base = Path::new(output_file)
        .file_name()
        .map_or_else(String::new, |name| name.to_string_lossy().into_owned());
    EXTERNAL_TOOL_NAMES
        .iter()
        .find(|tool| base.contains(**tool))
        .map_or_else(|| "unknown".to_owned(), |tool| (*tool).to_owned())
}

fn validate_retry_timeout(meta: &RetryMeta) -> Result<u64, String> {
    let raw = meta.get("TIMEOUT");
    if raw.is_empty() {
        return Err("Retry metadata invalid: TIMEOUT missing".to_owned());
    }
    positive_seconds(raw)
        .ok_or_else(|| "Retry metadata invalid: TIMEOUT not a positive integer".to_owned())
}

fn safe_meta_path_value(value: &str) -> bool {
    !value.contains("..")
}

// ---------------------------------------------------------------------------
// Retry plans
// ---------------------------------------------------------------------------

/// One scheduled retry of a reviewer whose first launch published nothing.
struct RetryPlan {
    index: usize,
    orig_output: String,
    retry_output: String,
    timeout: u64,
    launched: bool,
    sentinel: String,
    worker: Option<JoinHandle<()>>,
}

impl RetryPlan {
    fn new(index: usize, orig_output: &str, timeout: u64) -> Self {
        Self {
            index,
            orig_output: orig_output.to_owned(),
            retry_output: retry_output_path(orig_output),
            timeout,
            launched: false,
            sentinel: String::new(),
            worker: None,
        }
    }
}

fn mark_retry_metadata_invalid(records: &mut [CollectorRecord], plan: &RetryPlan, reason: &str) {
    records[plan.index] = CollectorRecord::new(
        &plan.orig_output,
        &derive_tool(&plan.orig_output),
        STATUS_EMPTY_OUTPUT,
        "99",
    )
    .with_reason(reason);
}

/// Start one retry, or refuse it and record why.
fn launch_retry_plan(plan: &mut RetryPlan, records: &mut [CollectorRecord]) {
    let meta = RetryMeta::read(&sidecar(&plan.orig_output, LauncherArtifactKind::Meta));
    match validate_retry_timeout(&meta) {
        Ok(timeout) => plan.timeout = timeout,
        Err(reason) => {
            mark_retry_metadata_invalid(records, plan, &reason);
            return;
        }
    }
    let request = if meta.has_outer_launcher() {
        outer_retry_request(plan, &meta)
    } else {
        cmd_json_retry_request(plan, &meta)
    };
    match request {
        Ok(request) => {
            plan.sentinel = format!(
                "{}{}",
                plan.retry_output,
                LauncherArtifactKind::Done.suffix()
            );
            plan.worker = Some(spawn_retry_worker(request));
            plan.launched = true;
        }
        Err(reason) => mark_retry_metadata_invalid(records, plan, &reason),
    }
}

fn invalid(reason: &str) -> String {
    format!("Retry metadata invalid: {reason}")
}

/// Build the retry child request from a recorded vendor argv.
fn cmd_json_retry_request(plan: &RetryPlan, meta: &RetryMeta) -> Result<ProcessRequest, String> {
    let cmd_json = meta.get("CMD_JSON");
    let tool = meta.get("TOOL");
    if cmd_json.is_empty() && tool.is_empty() {
        return Err(invalid("missing CMD_JSON and TOOL"));
    }
    if cmd_json.is_empty() {
        return Err(invalid("missing CMD_JSON"));
    }
    if tool.is_empty() {
        return Err(invalid("missing TOOL"));
    }
    let mut command = parse_json_string_array(cmd_json).map_err(|reason| invalid(&reason))?;
    let recorded_output = meta.get("OUTPUT_FILE");
    if !recorded_output.is_empty() {
        for item in &mut command {
            if item == recorded_output {
                item.clone_from(&plan.retry_output);
            }
        }
    }
    validate_cmd_json_shape(tool, &command)?;
    if cmd_json_requires_outer_launcher(&plan.orig_output, tool, &command) {
        return Err(invalid(
            "review-shaped CMD_JSON requires outer launcher metadata",
        ));
    }
    let stderr_sink = meta.get("STDERR_SINK");
    if !stderr_sink.is_empty() && !safe_meta_path_value(stderr_sink) {
        return Err(invalid("STDERR_SINK contains .."));
    }
    let mut argv = vec![
        "agent".to_owned(),
        "run-external-agent".to_owned(),
        "--tool".to_owned(),
        tool.to_owned(),
        "--output".to_owned(),
        plan.retry_output.clone(),
        "--timeout".to_owned(),
        plan.timeout.to_string(),
    ];
    if meta.get("CAPTURE_STDOUT") == "true" {
        argv.push("--capture-stdout".to_owned());
    } else if meta.get("CAPTURE_STDOUT_ONLY") == "true" {
        argv.push("--capture-stdout-only".to_owned());
    }
    if !stderr_sink.is_empty() {
        argv.push("--stderr-sink".to_owned());
        argv.push(stderr_sink.to_owned());
    }
    argv.push("--".to_owned());
    argv.extend(command);
    build_retry_request(plan, &argv, None, tool)
}

fn parse_json_string_array(raw: &str) -> Result<Vec<String>, String> {
    let parsed: Value =
        serde_json::from_str(raw).map_err(|_error| "malformed CMD_JSON".to_owned())?;
    let Value::Array(items) = parsed else {
        return Err("malformed CMD_JSON".to_owned());
    };
    if items.is_empty() {
        return Err("malformed CMD_JSON".to_owned());
    }
    items
        .into_iter()
        .map(|item| match item {
            Value::String(text) => Ok(text),
            _other => Err("malformed CMD_JSON".to_owned()),
        })
        .collect()
}

/// Refuse a recorded argv that no longer matches its tool's launch shape.
fn validate_cmd_json_shape(tool: &str, command: &[String]) -> Result<(), String> {
    let rejected = || Err(invalid(&format!("CMD_JSON argv shape rejected for {tool}")));
    let Some(first) = command.first() else {
        return rejected();
    };
    let argv0 = Path::new(first)
        .file_name()
        .map_or_else(String::new, |name| name.to_string_lossy().into_owned());
    let second = command.get(1).map_or("", String::as_str);
    match tool {
        "cursor" => {
            if argv0 != "cursor" || second != "agent" {
                return rejected();
            }
            if !command.iter().any(|token| token == "--workspace")
                || command.iter().any(|token| token == "--add-dir")
            {
                return rejected();
            }
            Ok(())
        }
        "codex" => {
            if argv0 != "codex" || second != "exec" {
                return rejected();
            }
            for needle in ["-C", "--add-dir", "--output-last-message"] {
                if !command.iter().any(|token| token == needle) {
                    return rejected();
                }
            }
            Ok(())
        }
        _other => Err(invalid("unknown TOOL for CMD_JSON")),
    }
}

/// Report whether a recorded argv is review-shaped and needs launcher metadata.
fn cmd_json_requires_outer_launcher(orig_output: &str, tool: &str, command: &[String]) -> bool {
    if sidecar(orig_output, LauncherArtifactKind::Prompt).is_file() {
        return true;
    }
    let Some(first) = command.first() else {
        return false;
    };
    let argv0 = Path::new(first)
        .file_name()
        .map_or_else(String::new, |name| name.to_string_lossy().into_owned());
    let second = command.get(1).map_or("", String::as_str);
    // The retired collector kept the last occurrence of a repeated flag.
    let last_value = |flag: &str| -> String {
        let mut found = String::new();
        for (position, token) in command.iter().enumerate() {
            if token == flag && position + 1 < command.len() {
                found.clone_from(&command[position + 1]);
            }
        }
        found
    };
    match tool {
        "cursor" if argv0 == "cursor" && second == "agent" => last_value("--mode") == "ask",
        "codex" if argv0 == "codex" && second == "exec" => last_value("--sandbox") == "read-only",
        _other => false,
    }
}

/// Build the retry child request from recorded outer-launcher metadata.
fn outer_retry_request(plan: &RetryPlan, meta: &RetryMeta) -> Result<ProcessRequest, String> {
    let launcher = meta.get("OUTER_LAUNCHER");
    let prompt_file = meta.get("OUTER_LAUNCHER_PROMPT_FILE");
    let workdir = meta.get("OUTER_LAUNCHER_WORKDIR");
    if launcher.is_empty() {
        return Err(invalid("missing OUTER_LAUNCHER"));
    }
    if prompt_file.is_empty() {
        return Err(invalid("missing OUTER_LAUNCHER_PROMPT_FILE"));
    }
    if workdir.is_empty() {
        return Err(invalid("missing OUTER_LAUNCHER_WORKDIR"));
    }
    if !safe_meta_path_value(launcher) {
        return Err(invalid("OUTER_LAUNCHER contains .."));
    }
    let review = match launcher {
        "agent launch-review" => true,
        "agent launch-codex-exec" => false,
        other if other == "launch-review.sh" || other.ends_with("/launch-review.sh") => {
            return Err(invalid(
                "retired review OUTER_LAUNCHER metadata is no longer accepted",
            ));
        }
        _other => {
            return Err(invalid(
                "OUTER_LAUNCHER not canonical agent launch-review or agent launch-codex-exec",
            ));
        }
    };
    if !safe_meta_path_value(prompt_file) {
        return Err(invalid("OUTER_LAUNCHER_PROMPT_FILE contains .."));
    }
    let expected_prompt = format!(
        "{}{}",
        plan.orig_output,
        LauncherArtifactKind::Prompt.suffix()
    );
    if prompt_file != expected_prompt {
        return Err(invalid(
            "OUTER_LAUNCHER_PROMPT_FILE not the expected sidecar",
        ));
    }
    let prompt_path = Path::new(prompt_file);
    let regular_prompt = fs::symlink_metadata(prompt_path)
        .is_ok_and(|metadata| metadata.is_file() && !metadata.file_type().is_symlink());
    if !regular_prompt {
        return Err(invalid(
            "OUTER_LAUNCHER_PROMPT_FILE not a readable regular non-symlink file",
        ));
    }
    if !safe_meta_path_value(workdir) {
        return Err(invalid("OUTER_LAUNCHER_WORKDIR contains .."));
    }
    if !Path::new(workdir).is_dir() {
        return Err(invalid("OUTER_LAUNCHER_WORKDIR not a directory"));
    }
    let argv = if review {
        review_retry_arguments(plan, meta, prompt_file)?
    } else {
        codex_exec_retry_arguments(plan, meta, prompt_file)?
    };
    build_retry_request(plan, &argv, Some(Path::new(workdir)), meta.get("TOOL"))
}

fn review_retry_arguments(
    plan: &RetryPlan,
    meta: &RetryMeta,
    prompt_file: &str,
) -> Result<Vec<String>, String> {
    let stderr_sink = meta.get("STDERR_SINK");
    let recorded_risk = meta.get("OUTER_LAUNCHER_RISK");
    let risk = if recorded_risk == "high" || recorded_risk == "low" {
        recorded_risk
    } else {
        "high"
    };
    if !stderr_sink.is_empty() && !safe_meta_path_value(stderr_sink) {
        return Err(invalid("STDERR_SINK contains .."));
    }
    let tool = meta.get("TOOL");
    let mut timing_kind = meta.get("OUTER_LAUNCHER_TIMING_KIND").to_owned();
    if timing_kind.is_empty() {
        let fallback = match tool {
            "codex" => Some("codex-review"),
            "cursor" => Some("cursor-review"),
            _other => None,
        };
        if let Some(default) = fallback {
            timing_kind =
                env::var("LARCH_TIMING_TASK_KIND").unwrap_or_else(|_error| default.to_owned());
        }
    }
    let mut argv = vec![
        "agent".to_owned(),
        "launch-review".to_owned(),
        "--tool".to_owned(),
        tool.to_owned(),
        "--output".to_owned(),
        plan.retry_output.clone(),
        "--timeout".to_owned(),
        plan.timeout.to_string(),
        "--risk".to_owned(),
        risk.to_owned(),
        "--timing-task-kind".to_owned(),
        timing_kind,
        "--prompt-file".to_owned(),
        prompt_file.to_owned(),
    ];
    let model_role = meta.get("OUTER_LAUNCHER_MODEL_ROLE");
    if tool == "codex" && !model_role.is_empty() {
        if !matches!(model_role, "default" | "review" | "vote" | "fix") {
            return Err(invalid("OUTER_LAUNCHER_MODEL_ROLE invalid"));
        }
        argv.push("--model-role".to_owned());
        argv.push(model_role.to_owned());
    }
    let cursor_model = meta.get("OUTER_LAUNCHER_CURSOR_MODEL");
    if !cursor_model.is_empty() {
        if tool != "cursor" || !valid_cursor_model(cursor_model) {
            return Err(invalid("OUTER_LAUNCHER_CURSOR_MODEL invalid"));
        }
        argv.push("--cursor-model".to_owned());
        argv.push(cursor_model.to_owned());
    }
    let site = meta.get("OUTER_LAUNCHER_SITE");
    if !site.is_empty() {
        argv.push("--site".to_owned());
        argv.push(site.to_owned());
    }
    if !stderr_sink.is_empty() {
        argv.push("--stderr-sink".to_owned());
        argv.push(stderr_sink.to_owned());
    }
    Ok(argv)
}

fn valid_cursor_model(value: &str) -> bool {
    !value.trim().is_empty()
        && !value
            .chars()
            .any(|character| character < ' ' || character == '\u{7f}')
}

fn codex_exec_retry_arguments(
    plan: &RetryPlan,
    meta: &RetryMeta,
    prompt_file: &str,
) -> Result<Vec<String>, String> {
    if meta.get("OUTER_LAUNCHER_KIND") != "codex-exec" {
        return Err(invalid("OUTER_LAUNCHER_KIND must be codex-exec"));
    }
    let sandbox = meta.get("OUTER_LAUNCHER_SANDBOX");
    if !matches!(sandbox, "workspace-write" | "read-only") {
        return Err(invalid("OUTER_LAUNCHER_SANDBOX invalid"));
    }
    let with_effort = meta.get("OUTER_LAUNCHER_WITH_EFFORT");
    if !matches!(with_effort, "true" | "false") {
        return Err(invalid("OUTER_LAUNCHER_WITH_EFFORT invalid"));
    }
    let model_role = meta.model_role();
    if !matches!(model_role, "" | "default" | "fix") {
        return Err(invalid("OUTER_LAUNCHER_MODEL_ROLE invalid"));
    }
    let usage_label = meta.get("OUTER_LAUNCHER_USAGE_LABEL");
    if usage_label.is_empty() {
        return Err(invalid("missing OUTER_LAUNCHER_USAGE_LABEL"));
    }
    let timing_kind = meta.get("OUTER_LAUNCHER_TIMING_KIND");
    if timing_kind.is_empty() {
        return Err(invalid("missing OUTER_LAUNCHER_TIMING_KIND"));
    }
    let raw_dirs = meta.get("OUTER_LAUNCHER_ADD_DIRS_JSON");
    let add_dirs = parse_add_dirs(raw_dirs)?;
    let mut argv = vec![
        "agent".to_owned(),
        "launch-codex-exec".to_owned(),
        "--output".to_owned(),
        plan.retry_output.clone(),
        "--timeout".to_owned(),
        plan.timeout.to_string(),
        "--workdir".to_owned(),
        meta.get("OUTER_LAUNCHER_WORKDIR").to_owned(),
        "--prompt-file".to_owned(),
        prompt_file.to_owned(),
        "--sandbox".to_owned(),
        sandbox.to_owned(),
        "--usage-label".to_owned(),
        usage_label.to_owned(),
        "--model-role".to_owned(),
        if model_role.is_empty() {
            "default".to_owned()
        } else {
            model_role.to_owned()
        },
        "--timing-task-kind".to_owned(),
        timing_kind.to_owned(),
    ];
    if with_effort == "true" {
        argv.push("--with-effort".to_owned());
    }
    for directory in add_dirs.into_iter().filter(|value| !value.is_empty()) {
        argv.push("--add-dir".to_owned());
        argv.push(directory);
    }
    Ok(argv)
}

fn parse_add_dirs(raw: &str) -> Result<Vec<String>, String> {
    let source = if raw.is_empty() { "[]" } else { raw };
    let malformed = || invalid("OUTER_LAUNCHER_ADD_DIRS_JSON malformed");
    let parsed: Value = serde_json::from_str(source).map_err(|_error| malformed())?;
    let Value::Array(items) = parsed else {
        return Err(malformed());
    };
    items
        .into_iter()
        .map(|item| match item {
            Value::String(text) => Ok(text),
            _other => Err(malformed()),
        })
        .collect()
}

/// Compose one retry child request against the verified bootstrap.
fn build_retry_request(
    plan: &RetryPlan,
    argv: &[String],
    workdir: Option<&Path>,
    tool: &str,
) -> Result<ProcessRequest, String> {
    let root = plugin_root_directory().ok_or_else(|| invalid("cannot resolve the plugin root"))?;
    let program = LarchProgram::bootstrap(&root).map_err(|error| invalid(&error.to_string()))?;
    let working_directory = match workdir {
        Some(path) => path.to_path_buf(),
        None => env::current_dir().map_err(|error| invalid(&error.to_string()))?,
    };
    let mut request = ProcessRequest::new(
        ExternalProgram::Larch(program),
        argv.iter().map(OsString::from),
        working_directory,
        Duration::from_secs(plan.timeout.saturating_add(RETRY_WAIT_GRACE)),
        RETRY_SHUTDOWN_GRACE,
        NonZeroUsize::new(RETRY_OUTPUT_LIMIT).unwrap_or(NonZeroUsize::MIN),
    )
    .map_err(|error| invalid(&error.to_string()))?;
    request = request.with_environment(
        ChildEnvironment::ClaudePluginRoot,
        root.as_os_str().to_owned(),
    );
    for (key, value) in inherited_child_rows() {
        request = request.with_environment(key, value);
    }
    if tool == "cursor" {
        let credential = env::var(larch_core::env::CURSOR_API_KEY)
            .ok()
            .and_then(|raw| CursorCredential::parse(raw.trim()));
        for (key, value) in cursor_child_environment(credential.as_ref()) {
            request = request.with_environment(key, value);
        }
    }
    Ok(request)
}

/// Run one retry child on its own thread; its streams are captured and dropped.
fn spawn_retry_worker(request: ProcessRequest) -> JoinHandle<()> {
    thread::spawn(move || {
        let Ok(runtime) = LarchRuntime::current_thread() else {
            return;
        };
        let runner = TokioProcessRunner::new(Arc::new(NoopProcessObserver));
        let _ignored = runtime.block_on(runner.run(request, &Cancellation::new()));
    })
}

/// Wait for every launched retry child to exit.
///
/// The retired collector polled each retry's `.done` sentinel on a floor of
/// thirty seconds and then reaped the child without blocking. Every accepted
/// retry launcher publishes that sentinel before it exits, so joining the
/// workers reaches the same terminal state under the same deadline: the child
/// request already carries `--timeout` plus one minute.
fn wait_retry_plans(plans: &mut [RetryPlan]) {
    for plan in plans {
        if let Some(worker) = plan.worker.take() {
            let _joined = worker.join();
        }
    }
}

fn retry_failure_result(
    records: &mut [CollectorRecord],
    plan: &RetryPlan,
    notes: &mut Vec<String>,
) {
    let tool = derive_tool(&plan.orig_output);
    let sentinel = PathBuf::from(&plan.sentinel);
    if sentinel.is_file() {
        let (retry_exit, _coerced) = read_sentinel_exit(&sentinel, "retry sentinel", notes);
        let retry_status = if retry_exit == TIMEOUT_EXIT {
            STATUS_TIMED_OUT
        } else if retry_exit == "0" {
            STATUS_EMPTY_OUTPUT
        } else {
            STATUS_FAILED
        };
        let reason = build_failure_reason(&plan.retry_output, retry_status, &retry_exit);
        records[plan.index] =
            CollectorRecord::new(&plan.orig_output, &tool, STATUS_EMPTY_OUTPUT, &retry_exit)
                .with_reason(&format!("Retry also failed: {reason}"));
    } else {
        records[plan.index] =
            CollectorRecord::new(&plan.orig_output, &tool, STATUS_EMPTY_OUTPUT, "99")
                .with_reason("Retry process did not complete (sentinel file missing)");
    }
}

fn apply_retry_results(
    records: &mut [CollectorRecord],
    plans: &[RetryPlan],
    notes: &mut Vec<String>,
) {
    for plan in plans {
        if !plan.launched {
            continue;
        }
        let sentinel = PathBuf::from(&plan.sentinel);
        if !sentinel.is_file() {
            retry_failure_result(records, plan, notes);
            continue;
        }
        let (retry_exit, _coerced) = read_sentinel_exit(&sentinel, "retry sentinel", notes);
        if retry_exit != "0" || !is_non_empty_file(Path::new(&plan.retry_output)) {
            retry_failure_result(records, plan, notes);
            continue;
        }
        let tool = derive_tool(&plan.orig_output);
        records[plan.index] = if is_cursor_degraded_response(&plan.retry_output) {
            CollectorRecord::new(&plan.retry_output, &tool, STATUS_CURSOR_EMPTY, "0")
                .with_reason("cursor narration-only / degraded backend response (retry)")
        } else {
            CollectorRecord::new(&plan.retry_output, &tool, STATUS_OK, "0")
        };
        for base in [&plan.orig_output, &plan.retry_output] {
            let _removed = fs::remove_file(sidecar(base, LauncherArtifactKind::StderrTail));
        }
    }
}

// ---------------------------------------------------------------------------
// Content validation
// ---------------------------------------------------------------------------

/// One validator run's exit code and combined output.
struct ValidatorResult {
    exit_code: i32,
    text: String,
}

fn run_validator(arguments: &[String]) -> ValidatorResult {
    let argv: Vec<OsString> = arguments.iter().map(OsString::from).collect();
    let run = crate::eval_commands::validate_captured(&argv);
    let mut text = run.stdout;
    text.push_str(&run.stderr);
    ValidatorResult {
        exit_code: run.code,
        text,
    }
}

fn validate_substantive(records: &mut [CollectorRecord], policy: SubstantiveValidation) {
    for record in records.iter_mut() {
        if record.status != STATUS_OK {
            continue;
        }
        let mut arguments: Vec<String> = Vec::new();
        if policy == SubstantiveValidation::ShortReviewer {
            arguments.push("--validation-mode".to_owned());
        }
        arguments.push(record.reviewer_file.clone());
        let result = run_validator(&arguments);
        if result.exit_code == 0 {
            continue;
        }
        let reason = sanitize_failure_reason(&result.text, VALIDATION_REASON_LIMIT);
        *record = if result.exit_code == EXIT_VALIDATION_CURSOR_EMPTY {
            CollectorRecord::new(
                &record.reviewer_file,
                &record.tool,
                STATUS_CURSOR_EMPTY,
                "0",
            )
            .with_reason(&reason)
        } else {
            CollectorRecord::new(
                &record.reviewer_file,
                &record.tool,
                STATUS_NOT_SUBSTANTIVE,
                "0",
            )
            .with_reason(&reason)
            .with_ns_retry(ValidationKind::Substantive, result.exit_code)
        };
    }
}

fn structured_sidecar_path(record: &CollectorRecord) -> String {
    let suffix = if record.tool == "cursor" || record.tool == "codex" {
        ".tsv"
    } else {
        ".jsonl"
    };
    format!("{}{suffix}", record.reviewer_file)
}

fn validate_structured(records: &mut [CollectorRecord], notes: &mut Vec<String>) {
    for record in records.iter_mut() {
        if record.status != STATUS_OK {
            continue;
        }
        let sidecar_path = structured_sidecar_path(record);
        let result = run_validator(&[
            "--structured-reviewer-mode".to_owned(),
            "--write-structured".to_owned(),
            sidecar_path.clone(),
            record.reviewer_file.clone(),
        ]);
        if result.exit_code == 0 {
            record.structured_sidecar = sidecar_path;
            if result
                .text
                .contains("NO_ISSUES_SENTINEL_RECOVERED_AFTER_PREAMBLE")
            {
                let base = Path::new(&record.reviewer_file)
                    .file_name()
                    .map_or_else(String::new, |name| name.to_string_lossy().into_owned());
                let tool = tool_label(&record.tool);
                note(
                    notes,
                    &format!(
                        "{PROG}: structured reviewer output recovered a no-issues sentinel after preamble basename={base} tool={tool}"
                    ),
                );
            }
            continue;
        }
        let reason = sanitize_failure_reason(&result.text, VALIDATION_REASON_LIMIT);
        *record = CollectorRecord::new(
            &record.reviewer_file,
            &record.tool,
            STATUS_NOT_SUBSTANTIVE,
            "0",
        )
        .with_reason(&reason)
        .with_ns_retry(ValidationKind::Structured, result.exit_code);
    }
}

const fn tool_label(tool: &str) -> &str {
    if tool.is_empty() { "unknown" } else { tool }
}

fn note_not_substantive(records: &[CollectorRecord], notes: &mut Vec<String>) {
    for record in records {
        if record.status != STATUS_NOT_SUBSTANTIVE {
            continue;
        }
        let base = Path::new(&record.reviewer_file)
            .file_name()
            .map_or_else(String::new, |name| name.to_string_lossy().into_owned());
        let mode = if record.ns_retry_mode.is_empty() {
            "none"
        } else {
            record.ns_retry_mode.as_str()
        };
        let reason = if record.ns_retry_reason.is_empty() {
            "UNKNOWN"
        } else {
            record.ns_retry_reason.as_str()
        };
        note(
            notes,
            &format!(
                "{PROG}: warning: dropping NOT_SUBSTANTIVE reviewer basename={base} tool={} NS_RETRY_MODE={mode} NS_RETRY_REASON={reason} FAILURE_REASON={}",
                tool_label(&record.tool),
                sanitize_failure_reason(&record.failure_reason, REASON_LIMIT)
            ),
        );
    }
}

// ---------------------------------------------------------------------------
// Failure excerpts
// ---------------------------------------------------------------------------

/// Fall-back reviewer paths one phase's excerpt may live under.
fn stderr_tail_candidates(reviewer_file: &str) -> Vec<String> {
    let mut candidates = vec![reviewer_file.to_owned()];
    if let Some(stem) = reviewer_file.strip_suffix("-phase3.txt") {
        candidates.push(format!("{stem}-phase2.txt"));
        candidates.push(format!("{stem}.txt"));
    } else if let Some(stem) = reviewer_file
        .strip_suffix("-phase2.txt")
        .or_else(|| reviewer_file.strip_suffix("-phase1.txt"))
    {
        candidates.push(format!("{stem}.txt"));
    }
    candidates
}

/// Where one failed reviewer's stderr excerpt came from.
enum TailSource {
    /// An excerpt already published on disk.
    Published(PathBuf),
    /// An excerpt rendered here from a raw launch-stderr capture.
    Rendered(String),
}

impl TailSource {
    fn text(&self) -> String {
        match self {
            Self::Published(path) => read_nonempty(path),
            Self::Rendered(text) => text.clone(),
        }
    }
}

fn published_tail(path: String) -> Option<TailSource> {
    is_non_empty_file(Path::new(&path)).then(|| TailSource::Published(PathBuf::from(path)))
}

fn rendered_launch_tail(launch_stderr: &str) -> Option<TailSource> {
    let path = Path::new(launch_stderr);
    if !is_non_empty_file(path) {
        return None;
    }
    let rendered = render_failed_agent_stderr_tail(
        &read_text(path),
        FAILED_AGENT_STDERR_TAIL_LINES,
        FAILED_AGENT_STDERR_TAIL_BYTE_CAP,
    );
    (!rendered.is_empty()).then_some(TailSource::Rendered(rendered))
}

/// Resolve the most specific stderr excerpt for one failed reviewer.
fn resolve_stderr_tail(reviewer_file: &str) -> Option<TailSource> {
    let base = reviewer_file.strip_suffix(".txt").unwrap_or(reviewer_file);
    for suffix in ["-retry.txt.stderr-tail", "-ns-retry.txt.stderr-tail"] {
        if let Some(found) = published_tail(format!("{base}{suffix}")) {
            return Some(found);
        }
    }
    for candidate in stderr_tail_candidates(reviewer_file) {
        let candidate_base = candidate.strip_suffix(".txt").unwrap_or(&candidate);
        for suffix in ["-retry.txt.stderr-tail", "-ns-retry.txt.stderr-tail"] {
            if let Some(found) = published_tail(format!("{candidate_base}{suffix}")) {
                return Some(found);
            }
        }
        for launch_stderr in [
            format!("{candidate_base}-retry.txt.launch-stderr"),
            format!("{candidate_base}-ns-retry.txt.launch-stderr"),
            format!("{candidate}{}", LauncherArtifactKind::LaunchStderr.suffix()),
        ] {
            if let Some(found) = rendered_launch_tail(&launch_stderr) {
                return Some(found);
            }
        }
        if let Some(found) = published_tail(format!(
            "{candidate}{}",
            LauncherArtifactKind::StderrTail.suffix()
        )) {
            return Some(found);
        }
    }
    None
}

/// Collapse volatile detail so identical root causes share one signature.
fn failure_signature(text: &str) -> String {
    if text.is_empty() {
        return String::new();
    }
    let hex = Regex::new(r"0x[0-9a-fA-F]+").expect("hex pattern");
    let digits = Regex::new(r"[0-9]+").expect("digit pattern");
    let outputs =
        Regex::new(r"\S+\.(?:txt|stderr-tail|sidecar|diag|done)( |\n|$)").expect("output pattern");
    let mut normalized = hex.replace_all(text, "0x#").into_owned();
    normalized = digits.replace_all(&normalized, "#").into_owned();
    for prefix in session_path_prefixes() {
        let pattern =
            Regex::new(&format!("{}\\S*", regex::escape(&prefix))).expect("session path pattern");
        normalized = pattern.replace_all(&normalized, "<path>").into_owned();
    }
    normalized = outputs.replace_all(&normalized, "<out>$1").into_owned();
    posix_cksum(normalized.as_bytes()).to_string()
}

fn session_path_prefixes() -> Vec<String> {
    let mut prefixes = vec!["/tmp".to_owned(), "/var/folders".to_owned()];
    if let Ok(home) = env::var(larch_core::env::HOME)
        && !home.is_empty()
    {
        prefixes.push(format!("{home}/.cache/larch/sessions"));
    }
    prefixes
}

/// Compute the POSIX `cksum` CRC of one buffer.
///
/// The retired collector shelled out to `cksum`. That is not an approved
/// external product, so the algorithm lives here: the same CRC-32 polynomial,
/// the same trailing length bytes, and the same final complement.
fn posix_cksum(data: &[u8]) -> u32 {
    let mut table = [0_u32; 256];
    for (index, slot) in table.iter_mut().enumerate() {
        let mut value = (u32::try_from(index).unwrap_or(0)) << 24;
        for _round in 0..8 {
            value = if value & 0x8000_0000 == 0 {
                value << 1
            } else {
                (value << 1) ^ 0x04C1_1DB7
            };
        }
        *slot = value;
    }
    let mut crc = 0_u32;
    for byte in data {
        let index = usize::from(u8::try_from(crc >> 24).unwrap_or(0) ^ *byte);
        crc = (crc << 8) ^ table[index];
    }
    let mut length = data.len();
    while length > 0 {
        let index = usize::from(
            u8::try_from(crc >> 24).unwrap_or(0) ^ u8::try_from(length & 0xff).unwrap_or(0),
        );
        crc = (crc << 8) ^ table[index];
        length >>= 8;
    }
    !crc
}

/// Publish one bounded excerpt per distinct root cause across failed reviewers.
fn note_failed_agent_stderr_tails(records: &[CollectorRecord], notes: &mut Vec<String>) {
    let mut seen: BTreeMap<String, String> = BTreeMap::new();
    for record in records {
        if matches!(record.status.as_str(), STATUS_OK | STATUS_CAP_HIT | "") {
            continue;
        }
        let Some(source) = resolve_stderr_tail(&record.reviewer_file) else {
            continue;
        };
        let signature = failure_signature(&source.text());
        let base = Path::new(&record.reviewer_file)
            .file_name()
            .map_or_else(String::new, |name| name.to_string_lossy().into_owned());
        if !signature.is_empty()
            && let Some(first) = seen.get(&signature)
        {
            note(
                notes,
                &format!(
                    "↩ {} {base}: identical failure to {first} (root-cause sig {signature}); stderr tail suppressed",
                    tool_label(&record.tool)
                ),
            );
            continue;
        }
        if !signature.is_empty() {
            let _replaced = seen.insert(signature, base);
        }
        let rendered = render_failed_agent_stderr_tail(
            &source.text(),
            FAILED_AGENT_STDERR_TAIL_LINES,
            FAILED_AGENT_STDERR_TAIL_BYTE_CAP,
        );
        if rendered.is_empty() {
            continue;
        }
        note(notes, "--- failed agent stderr tail ---");
        for line in rendered.lines().filter(|line| !line.is_empty()) {
            note(notes, line);
        }
        note(notes, "--- end failed agent stderr tail ---");
    }
}

// ---------------------------------------------------------------------------
// Initial classification
// ---------------------------------------------------------------------------

/// Classify every reviewer once its sentinel wait has finished.
fn build_initial_records(
    options: &CollectorOptions,
    timed_out: &[usize],
    notes: &mut Vec<String>,
) -> (Vec<CollectorRecord>, Vec<RetryPlan>) {
    let mut records = Vec::with_capacity(options.output_files.len());
    let mut plans = Vec::new();
    for (index, output) in options.output_files.iter().enumerate() {
        let tool = derive_tool(output);
        let sentinel = sidecar(output, LauncherArtifactKind::Done);
        let meta_path = sidecar(output, LauncherArtifactKind::Meta);
        let mut record = CollectorRecord::new(output, &tool, STATUS_OK, "0");
        if timed_out.contains(&(index + 1)) || !sentinel.is_file() {
            STATUS_SENTINEL_TIMEOUT.clone_into(&mut record.status);
            TIMEOUT_EXIT.clone_into(&mut record.exit_code);
            record.failure_reason = build_failure_reason(output, &record.status, &record.exit_code);
        } else {
            let (exit_code, coerced) = read_sentinel_exit(&sentinel, "initial sentinel", notes);
            record.exit_code = exit_code;
            let output_nonempty = is_non_empty_file(Path::new(output));
            if record.exit_code == TIMEOUT_EXIT {
                STATUS_TIMED_OUT.clone_into(&mut record.status);
                record.failure_reason =
                    build_failure_reason(output, &record.status, &record.exit_code);
            } else if (output_nonempty || !coerced) && record.exit_code != "0" {
                STATUS_FAILED.clone_into(&mut record.status);
                record.failure_reason =
                    build_failure_reason(output, &record.status, &record.exit_code);
            } else if output_nonempty && first_line(output) == "STATUS=cap_hit" {
                STATUS_CAP_HIT.clone_into(&mut record.status);
                "Token budget cap hit; reviewer skipped".clone_into(&mut record.failure_reason);
            } else if !output_nonempty {
                STATUS_EMPTY_OUTPUT.clone_into(&mut record.status);
                record.failure_reason =
                    build_failure_reason(output, &record.status, &record.exit_code);
                if meta_path.is_file() {
                    match validate_retry_timeout(&RetryMeta::read(&meta_path)) {
                        Ok(timeout) => plans.push(RetryPlan::new(index, output, timeout)),
                        Err(reason) => {
                            record = CollectorRecord::new(output, &tool, STATUS_EMPTY_OUTPUT, "99")
                                .with_reason(&reason);
                        }
                    }
                }
            }
        }
        if matches!(
            record.status.as_str(),
            STATUS_FAILED | STATUS_TIMED_OUT | STATUS_SENTINEL_TIMEOUT
        ) && has_transient_diag(output)
            && meta_path.is_file()
        {
            match validate_retry_timeout(&RetryMeta::read(&meta_path)) {
                Ok(timeout) => {
                    STATUS_EMPTY_OUTPUT.clone_into(&mut record.status);
                    let base = Path::new(output)
                        .file_name()
                        .map_or_else(String::new, |name| name.to_string_lossy().into_owned());
                    note(
                        notes,
                        &format!("{PROG}: transient diagnostic for {base}; retrying once"),
                    );
                    plans.push(RetryPlan::new(index, output, timeout));
                }
                Err(reason) => {
                    record = CollectorRecord::new(output, &tool, STATUS_EMPTY_OUTPUT, "99")
                        .with_reason(&reason);
                }
            }
        }
        if record.status == STATUS_OK && is_cursor_degraded_response(output) {
            STATUS_CURSOR_EMPTY.clone_into(&mut record.status);
            "cursor narration-only / degraded backend response"
                .clone_into(&mut record.failure_reason);
        }
        records.push(record);
    }
    (records, plans)
}

fn first_line(path: &str) -> String {
    read_text(Path::new(path))
        .lines()
        .next()
        .unwrap_or_default()
        .to_owned()
}

#[cfg(test)]
mod tests {
    use super::{
        ValidationKind, collapse_whitespace, failure_signature, ns_retry_reason, posix_cksum,
        retry_output_path, sanitize_failure_reason, stderr_tail_candidates,
    };

    #[test]
    fn posix_cksum_matches_the_reference_vectors() {
        // Reference values from POSIX `cksum` for the empty, one-line, and
        // multi-byte cases.
        assert_eq!(posix_cksum(b""), 4_294_967_295);
        assert_eq!(posix_cksum(b"a\n"), 2_418_082_923);
        assert_eq!(posix_cksum(b"hello world\n"), 3_733_384_285);
    }

    #[test]
    fn failure_reason_flattens_and_truncates() {
        assert_eq!(sanitize_failure_reason("a|b\nc  d\r\n", 500), "a b c d");
        assert_eq!(sanitize_failure_reason("abcdefgh", 6), "abc...");
        assert_eq!(collapse_whitespace("  a \t b  "), "a b");
    }

    #[test]
    fn retry_paths_and_candidates_follow_the_phase_ladder() {
        assert_eq!(retry_output_path("/tmp/foo.out"), "/tmp/foo.out-retry.txt");
        assert_eq!(retry_output_path("/tmp/foo.txt"), "/tmp/foo-retry.txt");
        assert_eq!(
            stderr_tail_candidates("/tmp/a-phase3.txt"),
            vec![
                "/tmp/a-phase3.txt".to_owned(),
                "/tmp/a-phase2.txt".to_owned(),
                "/tmp/a.txt".to_owned(),
            ]
        );
        assert_eq!(
            stderr_tail_candidates("/tmp/a-phase1.txt"),
            vec!["/tmp/a-phase1.txt".to_owned(), "/tmp/a.txt".to_owned()]
        );
        assert_eq!(
            stderr_tail_candidates("/tmp/plain.txt"),
            vec!["/tmp/plain.txt".to_owned()]
        );
    }

    #[test]
    fn ns_retry_reasons_split_by_mode() {
        assert_eq!(
            ns_retry_reason(5, ValidationKind::Structured),
            "JSON_PARSE_FAIL"
        );
        assert_eq!(ns_retry_reason(2, ValidationKind::Structured), "UNKNOWN");
        assert_eq!(
            ns_retry_reason(2, ValidationKind::Substantive),
            "NO_ISSUES_FOUND_TOO_THIN"
        );
        assert_eq!(
            ns_retry_reason(3, ValidationKind::Substantive),
            "NO_ISSUES_FOUND_TOO_THIN"
        );
        assert_eq!(
            ns_retry_reason(4, ValidationKind::Substantive),
            "OUTPUT_EMPTY"
        );
        assert_eq!(ns_retry_reason(9, ValidationKind::Substantive), "UNKNOWN");
    }

    #[test]
    fn signatures_collapse_volatile_detail() {
        let first = failure_signature("boom at 0xdeadbeef in /tmp/session-1/out.txt\n");
        let second = failure_signature("boom at 0xfeedface in /tmp/session-2/out.txt\n");
        assert_eq!(first, second);
        assert!(!first.is_empty());
        assert_eq!(failure_signature(""), "");
    }
}
