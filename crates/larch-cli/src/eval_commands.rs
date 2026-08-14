//! Rust owner for the two `eval` research-evaluation commands.
//!
//! `validate-research-output` and `research` were Python
//! (`larch.research.research_eval`) until #8500 made Rust their single owner.
//! The commands preserve the retired stdout/stderr/exit-code and wire-file
//! contracts: the validator's exit-code matrix (0/1/2/3/4/5), the `_emit`
//! stdout lines, the `_diag` REJECT stderr lines, and the atomic normalized
//! structured wire file. `research` stays a live `claude`-invoking harness whose
//! offline success path is `--smoke-test`.
//!
//! JSONL records are re-serialized with sorted keys, compact separators, and the
//! Python `ensure_ascii=True` escaping so the normalized wire file stays
//! byte-for-byte identical to the retired Python output.

use std::{
    ffi::OsString,
    fs,
    io::Write as _,
    path::{Path, PathBuf},
    process::ExitCode,
    sync::LazyLock,
    time::{Duration, Instant, SystemTime},
};

use larch_core::review::{finding_scope_set, focus_area_set};
use larch_core::{
    ChildEnvironment, ExternalProgram, GitPath, ProcessErrorKind, RepositoryRead, Revision,
    VendorProgram, ensure_ascii_json, split_text_lines,
};
use regex::Regex;
use serde_json::Value;

use crate::argparse_compat::parse_with_flags;
use crate::child_process::{bounded_request_in, run_bounded_detailed};
use crate::research_commands::{FILELINE_RE, read_text_lossy, write_text_atomic};

const ANTHROPIC_EVAL_SOURCE: &str =
    "anthropic.com/engineering/built-multi-agent-research-system";
const EVAL_SET_REL: &str = "skills/research/references/eval-set.md";
const EVAL_BASELINE_REL: &str = "skills/research/references/eval-baseline.json";
const STRUCTURED_HEADER: &str = "schema_version\tscope\tseverity\tfocus_area\tlocation\twhat\tscenario_or_breakage\tsuggested_fix";
const ALLOWED_SEVERITIES: [&str; 3] = ["major", "minor", "nit"];

static WHITESPACE_RUN_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"\s+").expect("static whitespace-run regex"));
static MULTISPACE_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r" {2,}").expect("static multispace regex"));
static TSV_ROW_START_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^\d+\t").expect("static TSV row-start regex"));
static FINDING_LINE_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?m)^FINDING_[0-9]+:\s*(YES|NO|EXONERATE)").expect("static finding-line regex")
});
static URL_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"https?://[A-Za-z0-9._/?#&=%-]+").expect("static URL regex")
});
static PROV_FILE_LINE_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"[A-Za-z0-9_/.-]+:[0-9]+").expect("static file-line prov regex"));
static PROV_REPO_PATH_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?:scripts|skills|hooks|docs|tests|agents)/[A-Za-z0-9_/.-]+")
        .expect("static repo-path prov regex")
});
static EVAL_HEAD_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^### eval-[0-9]+:\s*(.+)$").expect("static eval-head regex"));
static EVAL_FIELD_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^- \*\*(question|category|expected_provenance_count|expected_keywords|notes)\*\*:\s*(.*)$")
        .expect("static eval-field regex")
});
static JUDGE_TOTAL_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^100$|^[1-9]?[0-9]$").expect("static judge-total regex"));
static JUDGE_AXIS_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^20$|^1?[0-9]$").expect("static judge-axis regex"));
static NEWLINE_RUN_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"[\r\n]+").expect("static newline-run regex"));
static ADVERSARIAL_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"(?i)adversarial").expect("static adversarial regex"));
static FICTITIOUS_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"(?i)fictitious|fabricat|invent").expect("static fictitious regex"));
static DATA_ABSENCE_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?i)data[- ]absen|no data|don.t have data").expect("static data-absence regex")
});

/// Collected stdout and stderr lines, flushed to the real streams by the CLI
/// entrypoints and captured directly by the in-process consumers.
#[derive(Default)]
struct Output {
    out: Vec<String>,
    err: Vec<String>,
}

impl Output {
    fn emit(&mut self, text: impl Into<String>) {
        self.out.push(text.into());
    }

    fn diag(&mut self, text: impl Into<String>) {
        self.err.push(text.into());
    }

    fn flush(&self) {
        let mut stdout = std::io::stdout().lock();
        for line in &self.out {
            let _ignored = writeln!(stdout, "{line}");
        }
        drop(stdout);
        let mut stderr = std::io::stderr().lock();
        for line in &self.err {
            let _ignored = writeln!(stderr, "{line}");
        }
    }

    fn stdout_text(&self) -> String {
        join_lines(&self.out)
    }

    fn stderr_text(&self) -> String {
        join_lines(&self.err)
    }
}

/// Join each captured line with a trailing newline into one stream text.
fn join_lines(lines: &[String]) -> String {
    let mut text = String::new();
    for line in lines {
        text.push_str(line);
        text.push('\n');
    }
    text
}

/// One captured validator run: exit code plus the standard streams as text.
pub struct ValidationRun {
    pub code: i32,
    pub stdout: String,
    pub stderr: String,
}

/// Write `text` to `path` atomically, matching Python `_write_structured`.
///
/// Reuses the shared `research_commands` atomic writer; the structured wire file
/// is optional, so a `None` path or a write failure is silently ignored, exactly
/// as the retired Python `_write_structured` behaved.
fn write_structured(path: Option<&Path>, text: &str) {
    if let Some(path) = path {
        let _ignored = write_text_atomic(path, text);
    }
}

/// Return trimmed, non-blank lines, matching Python `_trimmed_nonblank`.
fn trimmed_nonblank(text: &str) -> Vec<String> {
    split_text_lines(text)
        .into_iter()
        .map(|line| line.trim().to_owned())
        .filter(|line| !line.is_empty())
        .collect()
}

/// Map a known `focus_area` synonym onto the allowed enum, else return as-is.
fn canonical_focus(value: &str) -> String {
    if value == "completeness" {
        "code-quality".to_owned()
    } else {
        value.to_owned()
    }
}

/// Normalize a TSV column-1 value to the `schema_version` constant "1".
fn canonical_schema_version(value: &str) -> Option<&'static str> {
    if !value.is_empty() && value.chars().all(|character| character.is_ascii_digit()) {
        Some("1")
    } else {
        None
    }
}

// ---------------------------------------------------------------------------
// JSON helpers
// ---------------------------------------------------------------------------

/// Parse the first JSON value, allowing trailing text (Python `raw_decode`).
fn first_json_object(text: &str) -> Option<Value> {
    let stripped = text.trim_start();
    if !stripped.starts_with('{') {
        return None;
    }
    serde_json::Deserializer::from_str(stripped)
        .into_iter::<Value>()
        .next()
        .and_then(Result::ok)
}

/// Whether a dict's `no_issues_found` is boolean `true`.
fn object_no_issues(value: &Value) -> bool {
    value.get("no_issues_found") == Some(&Value::Bool(true))
}

fn json_no_issues(text: &str) -> bool {
    first_json_object(text).is_some_and(|value| value.is_object() && object_no_issues(&value))
}

fn line_json_no_issues(line: &str) -> bool {
    let stripped = line.trim();
    if !stripped.starts_with('{') {
        return false;
    }
    serde_json::from_str::<Value>(stripped)
        .ok()
        .is_some_and(|value| value.is_object() && object_no_issues(&value))
}

fn is_no_issues_sentinel_line(line: &str) -> bool {
    line.trim() == "NO_ISSUES_FOUND" || line_json_no_issues(line)
}

fn no_issues_sentinel_indexes(lines: &[String]) -> Vec<usize> {
    lines
        .iter()
        .enumerate()
        .filter(|(_index, line)| is_no_issues_sentinel_line(line))
        .map(|(index, _line)| index)
        .collect()
}

fn strict_whole_json_no_issues(text: &str) -> bool {
    let stripped = text.trim();
    if !stripped.starts_with('{') {
        return false;
    }
    serde_json::from_str::<Value>(stripped)
        .ok()
        .is_some_and(|value| value.is_object() && object_no_issues(&value))
}

fn line_json_has_schema_version(line: &str) -> bool {
    let stripped = line.trim();
    if !stripped.starts_with('{') {
        return false;
    }
    serde_json::from_str::<Value>(stripped)
        .ok()
        .is_some_and(|value| {
            value
                .as_object()
                .is_some_and(|object| object.contains_key("schema_version"))
        })
}

/// Normalize a JSON finding record, returning the validated value or `None`.
fn normalize_json_record(value: &Value) -> Option<Value> {
    let object = value.as_object()?;
    let mut record = object.clone();
    if let Some(Value::String(severity)) = record.get("severity") {
        record.insert("severity".to_owned(), Value::String(severity.to_lowercase()));
    }
    if let Some(Value::String(focus)) = record.get("focus_area") {
        record.insert("focus_area".to_owned(), Value::String(canonical_focus(focus)));
    }
    if record.get("schema_version").and_then(Value::as_f64) != Some(1.0) {
        return None;
    }
    let scope = record.get("scope").and_then(Value::as_str)?;
    if !finding_scope_set().contains(scope) {
        return None;
    }
    let severity = record.get("severity").and_then(Value::as_str)?;
    if !ALLOWED_SEVERITIES.contains(&severity) {
        return None;
    }
    let focus = record.get("focus_area").and_then(Value::as_str)?;
    if !focus_area_set().contains(focus) {
        return None;
    }
    for key in ["location", "what", "scenario_or_breakage", "suggested_fix"] {
        if !record.get(key).is_some_and(Value::is_string) {
            return None;
        }
    }
    Some(Value::Object(record))
}

/// Serialize a record with sorted keys, compact separators, and ASCII escapes.
fn dump_record(value: &Value) -> String {
    ensure_ascii_json(&serde_json::to_string(value).unwrap_or_default())
}

fn validate_structured_jsonl(text: &str) -> String {
    let mut lines: Vec<String> = Vec::new();
    for line in split_text_lines(text) {
        let stripped = line.trim();
        if stripped.is_empty() || stripped.starts_with("```") {
            continue;
        }
        let Ok(value) = serde_json::from_str::<Value>(stripped) else {
            continue;
        };
        if let Some(record) = normalize_json_record(&value) {
            lines.push(dump_record(&record));
        }
    }
    if lines.is_empty() {
        String::new()
    } else {
        format!("{}\n", lines.join("\n"))
    }
}

// ---------------------------------------------------------------------------
// TSV helpers
// ---------------------------------------------------------------------------

fn clean_tsv(value: &str) -> String {
    let flattened = value.replace(['\r', '\n'], " ");
    WHITESPACE_RUN_RE.replace_all(&flattened, " ").trim().to_owned()
}

/// Yield assembled TSV data rows after the header, joining continuations.
fn iter_tsv_logical_rows(text: &str, output: &mut Output) -> Vec<String> {
    let mut rows: Vec<String> = Vec::new();
    let mut seen_header = false;
    let mut buffer = String::new();
    for line in split_text_lines(text) {
        if line.trim().starts_with("```") {
            continue;
        }
        if !seen_header {
            if line == STRUCTURED_HEADER {
                seen_header = true;
            }
            continue;
        }
        if line.trim().is_empty() {
            continue;
        }
        if TSV_ROW_START_RE.is_match(line) {
            if !buffer.is_empty() {
                rows.push(std::mem::take(&mut buffer));
            }
            line.clone_into(&mut buffer);
        } else if !buffer.is_empty() {
            buffer = format!("{buffer} {}", line.trim());
        } else {
            output.diag("REJECT structured TSV row: continuation without row prefix");
        }
    }
    if !buffer.is_empty() {
        rows.push(buffer);
    }
    rows
}

fn location_field_valid(location: &str) -> bool {
    !clean_tsv(location).is_empty()
}

fn leading_typed_fields_valid(fields: &[String]) -> bool {
    if fields.len() < 6 {
        return false;
    }
    let schema = clean_tsv(&fields[0]);
    let scope = clean_tsv(&fields[1]);
    let severity = clean_tsv(&fields[2]);
    let focus = clean_tsv(&fields[3]);
    let location = clean_tsv(&fields[4]);
    canonical_schema_version(&schema).is_some()
        && finding_scope_set().contains(scope.as_str())
        && ALLOWED_SEVERITIES.contains(&severity.to_lowercase().as_str())
        && focus_area_set().contains(canonical_focus(&focus).as_str())
        && location_field_valid(&location)
}

fn multispace_run_count(field: &str) -> usize {
    MULTISPACE_RE.find_iter(field).count()
}

/// Gate trailing empty `suggested_fix` padding on high-confidence layout.
fn seven_field_pad_confident(fields: &[String]) -> bool {
    if fields[5..7]
        .iter()
        .any(|field| multispace_run_count(field) > 0)
    {
        return false;
    }
    !clean_tsv(&fields[5]).is_empty() || clean_tsv(&fields[6]).is_empty()
}

/// Reject space-to-tab repair that fabricates columns from in-field prose.
fn space_resplit_confident(original: &[String], candidate: &[String]) -> bool {
    if candidate.len() != 8 || original.len() >= 8 || original.len() < 6 {
        return false;
    }
    let deficit = 8 - original.len();
    let lead = original.len().min(5);
    if original[..lead]
        .iter()
        .any(|field| multispace_run_count(field) > 0)
    {
        return true;
    }
    if original.len() == 6 {
        return multispace_run_count(&original[5]) == deficit;
    }
    for field in &original[5..original.len() - 1] {
        let runs = multispace_run_count(field);
        if runs > 0 {
            return runs == deficit && deficit == 1;
        }
    }
    let tail_runs = multispace_run_count(&original[6]);
    tail_runs > 0 && tail_runs == deficit && deficit == 1
}

/// Recover an off-by-one-delimiter TSV row instead of dropping the whole slot.
fn salvage_structured_tsv_row(
    line: &str,
    fields: &[String],
    output: &mut Output,
) -> Option<Vec<String>> {
    if fields.len() < 8 {
        let joined = MULTISPACE_RE.replace_all(line, "\t");
        let candidate: Vec<String> = splitn_owned(&joined, 8, '\t');
        if candidate.len() == 8
            && leading_typed_fields_valid(&candidate)
            && space_resplit_confident(fields, &candidate)
        {
            return Some(candidate);
        }
    }
    if fields.len() == 7 && leading_typed_fields_valid(fields) {
        if seven_field_pad_confident(fields) {
            let mut padded = fields.to_vec();
            padded.push(String::new());
            return Some(padded);
        }
        output.diag("REJECT structured TSV row: ambiguous seven-field salvage layout");
    }
    None
}

/// Split one logical TSV row into eight fields or reject with a diagnostic.
fn split_structured_tsv_row(line: &str, output: &mut Output) -> Option<Vec<String>> {
    let flattened = NEWLINE_RUN_RE.replace_all(line, " ").into_owned();
    let fields = splitn_owned(&flattened, 8, '\t');
    if fields.len() >= 8 {
        return Some(fields);
    }
    if let Some(salvaged) = salvage_structured_tsv_row(&flattened, &fields, output) {
        return Some(salvaged);
    }
    output.diag(format!(
        "REJECT structured TSV row: expected 8 tab columns, got {}",
        fields.len()
    ));
    None
}

/// Split like Python `str.split(sep, maxsplit=count-1)`.
fn splitn_owned(text: &str, count: usize, separator: char) -> Vec<String> {
    text.splitn(count, separator).map(str::to_owned).collect()
}

fn validate_structured_tsv(text: &str, output: &mut Output) -> String {
    let mut out: Vec<String> = Vec::new();
    let mut seen_header = false;
    for line in split_text_lines(text) {
        if line == STRUCTURED_HEADER {
            seen_header = true;
            out.push(STRUCTURED_HEADER.to_owned());
            break;
        }
    }
    if !seen_header {
        return String::new();
    }
    let mut rows_seen = 0usize;
    for row in iter_tsv_logical_rows(text, output) {
        rows_seen += 1;
        let Some(fields) = split_structured_tsv_row(&row, output) else {
            continue;
        };
        let schema = clean_tsv(&fields[0]);
        let scope = clean_tsv(&fields[1]);
        let severity = clean_tsv(&fields[2]).to_lowercase();
        let focus = canonical_focus(&clean_tsv(&fields[3]));
        let location = clean_tsv(&fields[4]);
        let what = clean_tsv(&fields[5]);
        let scenario = clean_tsv(&fields[6]);
        let fix = clean_tsv(&fields[7]);
        let Some(canonical_schema) = canonical_schema_version(&schema) else {
            output.diag(format!(
                "REJECT structured TSV row: schema={} scope={} severity={} focus={}",
                python_repr(&schema),
                python_repr(&scope),
                python_repr(&severity),
                python_repr(&focus)
            ));
            continue;
        };
        if !finding_scope_set().contains(scope.as_str())
            || !ALLOWED_SEVERITIES.contains(&severity.as_str())
            || !focus_area_set().contains(focus.as_str())
        {
            output.diag(format!(
                "REJECT structured TSV row: schema={} scope={} severity={} focus={}",
                python_repr(&schema),
                python_repr(&scope),
                python_repr(&severity),
                python_repr(&focus)
            ));
            continue;
        }
        if !location_field_valid(&location) {
            output.diag(format!(
                "REJECT structured TSV row: invalid location={}",
                python_repr(&location)
            ));
            continue;
        }
        out.push(
            [
                canonical_schema.to_owned(),
                scope,
                severity,
                focus,
                location,
                what,
                scenario,
                fix,
            ]
            .join("\t"),
        );
    }
    if out.len() <= 1 {
        if rows_seen > 0 {
            output.diag(format!(
                "REJECT structured TSV: {rows_seen} data row(s) seen but none validated after salvage"
            ));
        }
        return String::new();
    }
    format!("{}\n", out.join("\n"))
}

/// Render a string with Python `repr` quoting, mirroring the `_diag` output.
fn python_repr(value: &str) -> String {
    crate::argparse_compat::python_repr(value)
}

fn validate_structured_reviewer_output(
    text: &str,
    write_target: Option<&Path>,
    output: &mut Output,
) -> i32 {
    let lines = trimmed_nonblank(text);
    let jsonl = validate_structured_jsonl(text);
    let normalized = if jsonl.is_empty() {
        validate_structured_tsv(text, output)
    } else {
        jsonl
    };
    if !normalized.is_empty() {
        write_structured(write_target, &normalized);
        return 0;
    }
    let sentinel_indexes = no_issues_sentinel_indexes(&lines);
    let joined = lines.join("\n");
    if sentinel_indexes.len() <= 1 && strict_whole_json_no_issues(&joined) {
        write_structured(write_target, "");
        return 0;
    }
    if !lines.iter().any(|line| line_json_has_schema_version(line))
        && sentinel_indexes.len() == 1
    {
        write_structured(write_target, "");
        if sentinel_indexes[0] > 0 {
            output.emit("WARNING=NO_ISSUES_SENTINEL_RECOVERED_AFTER_PREAMBLE");
        }
        return 0;
    }
    write_structured(write_target, "");
    output.emit("structured records not found after repair");
    5
}

// ---------------------------------------------------------------------------
// word count and provenance
// ---------------------------------------------------------------------------

fn is_fence_line(line: &str) -> bool {
    line.trim_start_matches([' ', '\t']).starts_with("```")
}

fn word_count_without_fences(text: &str) -> usize {
    let mut in_fence = false;
    let mut words = 0usize;
    for line in split_text_lines(text) {
        if is_fence_line(line) {
            in_fence = !in_fence;
            continue;
        }
        if !in_fence {
            words += line.split_whitespace().count();
        }
    }
    words
}

fn has_code_fence_content(text: &str) -> bool {
    let mut in_fence = false;
    for line in split_text_lines(text) {
        if is_fence_line(line) {
            in_fence = !in_fence;
            continue;
        }
        if in_fence && !line.trim().is_empty() {
            return true;
        }
    }
    false
}

fn validation_mode_reviewer_no_findings_prose(lines: &[String]) -> bool {
    if lines.len() != 2 && lines.len() != 4 {
        return false;
    }
    if lines[0] != "### In-Scope Findings" || lines[1] != "No in-scope issues found." {
        return false;
    }
    if lines.len() == 2 {
        return true;
    }
    if lines[2] != "### Out-of-Scope Observations" {
        return false;
    }
    lines[3] == "No out-of-scope observations."
}

fn has_provenance(text: &str) -> bool {
    FILELINE_RE.is_match(text)
        || has_code_fence_content(text)
        || text.contains("http://")
        || text.contains("https://")
}

fn validate_research_output(
    input_file: &Path,
    min_words: Option<i64>,
    require_citations: bool,
    validation_mode: bool,
    structured_reviewer_mode: bool,
    write_target: Option<&Path>,
    output: &mut Output,
) -> i32 {
    let min_words = min_words.unwrap_or(if validation_mode { 30 } else { 200 });
    if !input_file.is_file() {
        output.emit(format!(
            "file missing or not readable: {}",
            input_file.display()
        ));
        return 4;
    }
    let Ok(text) = read_text_lossy(input_file) else {
        output.emit(format!(
            "file missing or not readable: {}",
            input_file.display()
        ));
        return 4;
    };
    if structured_reviewer_mode {
        return validate_structured_reviewer_output(&text, write_target, output);
    }
    let lines = trimmed_nonblank(&text);
    let trimmed = lines.join("\n");
    if validation_mode {
        if trimmed == "CURSOR_EMPTY_RESPONSE" || trimmed == "CURSOR_DEGRADED_RESPONSE" {
            output.emit("STATUS=CURSOR_EMPTY_RESPONSE");
            output.emit("FAILURE_REASON=Cursor returned an empty or degraded JSON .result field: likely transient backend issue. Fallback engaged.");
            return 5;
        }
        let first = lines.first().map_or("", String::as_str);
        let last = lines.last().map_or("", String::as_str);
        if first == "NO_ISSUES_FOUND" || json_no_issues(&trimmed) {
            return 0;
        }
        if last != first && (last == "NO_ISSUES_FOUND" || json_no_issues(last)) {
            return 0;
        }
        if FINDING_LINE_RE.is_match(&text) {
            return 0;
        }
        if !validate_structured_tsv(&text, output).is_empty() {
            return 0;
        }
        if validation_mode_reviewer_no_findings_prose(&lines) {
            return 0;
        }
    }
    let words = i64::try_from(word_count_without_fences(&text)).unwrap_or(i64::MAX);
    if words < min_words {
        output.emit(format!(
            "body too thin: {words}/{min_words} words after stripping fenced code"
        ));
        return 2;
    }
    if require_citations && !has_provenance(&text) {
        output.emit("no provenance marker found");
        return 3;
    }
    0
}

// ---------------------------------------------------------------------------
// validate-research-output entrypoint
// ---------------------------------------------------------------------------

const VALIDATE_USAGE: &str = "Usage: validate-research-output [--min-words N] [--require-citations|--no-require-citations] [--validation-mode] [--structured-reviewer-mode] [--write-structured <path>] <file>";

fn is_help(arguments: &[OsString]) -> bool {
    arguments
        .iter()
        .any(|argument| matches!(argument.to_str(), Some("-h" | "--help")))
}

fn validate_research_output_main(arguments: &[OsString], output: &mut Output) -> i32 {
    if is_help(arguments) {
        output.emit(VALIDATE_USAGE);
        return 0;
    }
    let parsed = parse_with_flags(
        arguments,
        &["--min-words", "--write-structured"],
        &[
            "--require-citations",
            "--no-require-citations",
            "--validation-mode",
            "--structured-reviewer-mode",
        ],
        1,
    );
    if parsed.error().is_some() {
        output.diag("validate-research-output: file argument is required");
        return 1;
    }
    let Some(input) = parsed.positional(0) else {
        output.diag("validate-research-output: file argument is required");
        return 1;
    };
    let min_words = match parsed.value("--min-words") {
        Some(value) => match value.to_string_lossy().parse::<i64>() {
            Ok(parsed_value) => Some(parsed_value),
            Err(_error) => return 1,
        },
        None => None,
    };
    let require = !parsed.flag("--no-require-citations");
    let write_target = parsed.value("--write-structured").map(PathBuf::from);
    validate_research_output(
        Path::new(input),
        min_words,
        require,
        parsed.flag("--validation-mode"),
        parsed.flag("--structured-reviewer-mode"),
        write_target.as_deref(),
        output,
    )
}

/// Execute `eval validate-research-output`, printing to the real streams.
#[must_use]
pub fn validate_research_output_command(arguments: &[OsString]) -> ExitCode {
    let mut output = Output::default();
    let code = validate_research_output_main(arguments, &mut output);
    output.flush();
    ExitCode::from(u8::try_from(code).unwrap_or(1))
}

/// Run the validator in-process and capture its exit code and both streams.
#[must_use]
pub fn validate_captured(arguments: &[OsString]) -> ValidationRun {
    let mut output = Output::default();
    let code = validate_research_output_main(arguments, &mut output);
    ValidationRun {
        code,
        stdout: output.stdout_text(),
        stderr: output.stderr_text(),
    }
}

// ---------------------------------------------------------------------------
// eval research: eval-set and baseline validation
// ---------------------------------------------------------------------------

#[derive(Clone, Debug)]
struct EvalEntry {
    id: String,
    category: String,
    expected_provenance_count: i64,
    expected_keywords: String,
    question: String,
    notes: String,
}

fn parse_eval_set(path: &Path) -> Vec<EvalEntry> {
    let Ok(text) = read_text_lossy(path) else {
        return Vec::new();
    };
    let mut entries: Vec<Vec<(String, String)>> = Vec::new();
    let mut current: Option<Vec<(String, String)>> = None;
    for line in split_text_lines(&text) {
        if let Some(captures) = EVAL_HEAD_RE.captures(line) {
            if let Some(existing) = current.take() {
                entries.push(existing);
            }
            current = Some(vec![("id".to_owned(), captures[1].trim().to_owned())]);
            continue;
        }
        let Some(fields) = current.as_mut() else {
            continue;
        };
        if let Some(captures) = EVAL_FIELD_RE.captures(line) {
            fields.push((captures[1].to_owned(), captures[2].to_owned()));
        }
    }
    if let Some(existing) = current {
        entries.push(existing);
    }
    entries
        .into_iter()
        .map(|fields| {
            let get = |key: &str| -> String {
                fields
                    .iter()
                    .find(|(name, _value)| name == key)
                    .map(|(_name, value)| value.clone())
                    .unwrap_or_default()
            };
            let provenance_raw = get("expected_provenance_count");
            let expected_provenance_count = if !provenance_raw.is_empty()
                && provenance_raw.chars().all(|c| c.is_ascii_digit())
            {
                provenance_raw.parse::<i64>().unwrap_or(-1)
            } else {
                -1
            };
            EvalEntry {
                id: get("id"),
                category: get("category"),
                expected_provenance_count,
                expected_keywords: get("expected_keywords"),
                question: get("question"),
                notes: get("notes"),
            }
        })
        .collect()
}

const EVAL_CATEGORIES: [&str; 5] = [
    "lookup",
    "architecture",
    "external-comparison",
    "risk-assessment",
    "feasibility",
];

fn validate_eval_set(path: &Path, output: &mut Output) -> bool {
    if !path.is_file() {
        output.diag(format!(
            "eval-research: eval-set.md not found at {}",
            path.display()
        ));
        return false;
    }
    let Ok(raw_text) = read_text_lossy(path) else {
        output.diag(format!(
            "eval-research: eval-set.md not found at {}",
            path.display()
        ));
        return false;
    };
    let entries = parse_eval_set(path);
    let header_ok = validate_eval_set_header(&raw_text, &entries, output);
    let entries_ok = validate_eval_set_entries(&entries, output);
    header_ok && entries_ok
}

/// Validate the first-20-lines markers, Anthropic literal, and adversarial notes.
fn validate_eval_set_header(raw_text: &str, entries: &[EvalEntry], output: &mut Output) -> bool {
    let first20 = split_text_lines(raw_text)
        .into_iter()
        .take(20)
        .collect::<Vec<_>>()
        .join("\n");
    let mut ok = true;
    for marker in ["Consumer", "Contract"] {
        if !first20.contains(marker) {
            output.diag(format!(
                "eval-research: eval-set.md missing first-20-lines header marker: {marker}"
            ));
            ok = false;
        }
    }
    if !first20.contains("When-to-load") && !first20.contains("When to load") {
        output.diag(
            "eval-research: eval-set.md missing first-20-lines header marker: When-to-load",
        );
        ok = false;
    }
    if !raw_text.contains(ANTHROPIC_EVAL_SOURCE) {
        output.diag(format!(
            "eval-research: eval-set.md missing Anthropic source literal: {ANTHROPIC_EVAL_SOURCE}"
        ));
        ok = false;
    }
    let adv_notes: Vec<&str> = entries
        .iter()
        .filter(|entry| ADVERSARIAL_RE.is_match(&entry.notes))
        .map(|entry| entry.notes.as_str())
        .collect();
    if adv_notes.len() < 2 {
        output.diag("eval-research: eval-set.md missing required adversarial note shapes");
        ok = false;
    } else {
        let has_fictitious = adv_notes.iter().any(|note| FICTITIOUS_RE.is_match(note));
        let has_data_absence = adv_notes.iter().any(|note| DATA_ABSENCE_RE.is_match(note));
        if !has_fictitious || !has_data_absence {
            output.diag("eval-research: eval-set.md missing required adversarial note shapes");
            ok = false;
        }
    }
    ok
}

/// Validate the entry count, per-entry fields, and full category coverage.
fn validate_eval_set_entries(entries: &[EvalEntry], output: &mut Output) -> bool {
    let mut ok = entries.len() >= 20;
    if !ok {
        output.diag(format!(
            "eval-research: eval-set.md has {} entries; need at least 20",
            entries.len()
        ));
    }
    let mut seen: Vec<String> = Vec::new();
    let mut cats: Vec<String> = Vec::new();
    for entry in entries {
        if entry.id.is_empty()
            || !entry
                .id
                .chars()
                .all(|c| c.is_ascii_lowercase() || c.is_ascii_digit() || c == '-')
        {
            output.diag(format!("eval-research: entry has invalid id: {}", entry.id));
            ok = false;
        }
        if seen.contains(&entry.id) {
            output.diag(format!("eval-research: duplicate eval id: {}", entry.id));
            ok = false;
        }
        seen.push(entry.id.clone());
        if !EVAL_CATEGORIES.contains(&entry.category.as_str()) {
            output.diag(format!(
                "eval-research: entry {} has unknown category: {}",
                entry.id, entry.category
            ));
            ok = false;
        }
        if !cats.contains(&entry.category) {
            cats.push(entry.category.clone());
        }
        if entry.expected_provenance_count < 0
            || entry.question.is_empty()
            || entry.expected_keywords.is_empty()
            || entry.notes.is_empty()
        {
            output.diag(format!(
                "eval-research: entry has missing field(s): id={} cat={}",
                entry.id, entry.category
            ));
            ok = false;
        }
    }
    for category in EVAL_CATEGORIES {
        if !cats.iter().any(|seen_cat| seen_cat == category) {
            output.diag(format!(
                "eval-research: eval-set.md missing entries from category: {category}"
            ));
            ok = false;
        }
    }
    ok
}

fn validate_baseline_json(path: &Path, output: &mut Output) -> bool {
    let missing = format!(
        "eval-research: eval-baseline.json not found at {}",
        path.display()
    );
    if !path.is_file() {
        output.diag(missing);
        return false;
    }
    let bad_keys = "eval-research: eval-baseline.json missing required keys (version, entries) or not valid JSON";
    let Ok(bytes) = fs::read(path) else {
        output.diag(missing);
        return false;
    };
    let Ok(text) = String::from_utf8(bytes) else {
        output.diag(bad_keys);
        return false;
    };
    let Ok(data) = serde_json::from_str::<Value>(&text) else {
        output.diag(bad_keys);
        return false;
    };
    let Some(object) = data.as_object() else {
        output.diag(bad_keys);
        return false;
    };
    if object.get("version").and_then(Value::as_f64) != Some(2.0)
        || !object.get("entries").is_some_and(Value::is_array)
    {
        output.diag(bad_keys);
        return false;
    }
    let entries = object
        .get("entries")
        .and_then(Value::as_array)
        .cloned()
        .unwrap_or_default();
    for entry in &entries {
        let Some(entry_object) = entry.as_object() else {
            output.diag("eval-research: eval-baseline.json entry is not an object");
            return false;
        };
        let Some(provenance) = entry_object.get("provenance").and_then(Value::as_object) else {
            output.diag("eval-research: eval-baseline.json entry missing provenance object");
            return false;
        };
        for key in ["file_line", "repo_path", "url"] {
            if !provenance.contains_key(key) {
                output.diag(format!(
                    "eval-research: eval-baseline.json entry provenance missing {key}"
                ));
                return false;
            }
        }
        for key in [
            "id",
            "category",
            "keyword_coverage_pct",
            "length_lines",
            "judge_status",
            "wall_clock_seconds",
            "research_status",
        ] {
            if !entry_object.contains_key(key) {
                output.diag(format!(
                    "eval-research: eval-baseline.json entry missing {key}"
                ));
                return false;
            }
        }
    }
    true
}

fn positive(value: &str, flag: &str) -> Result<i64, String> {
    let valid = !value.is_empty() && value.chars().all(|c| c.is_ascii_digit());
    let parsed = value.parse::<i64>().ok().filter(|number| *number >= 1);
    match (valid, parsed) {
        (true, Some(number)) => Ok(number),
        _invalid => Err(format!(
            "eval-research: {flag} must be a positive integer (got: {value})"
        )),
    }
}

fn baseline_ref_valid(value: &str) -> bool {
    !value.is_empty()
        && value
            .chars()
            .all(|c| c.is_ascii_alphanumeric() || matches!(c, '_' | '.' | '/' | '-'))
}

fn claude_on_path() -> bool {
    let Some(path) = std::env::var_os("PATH") else {
        return false;
    };
    std::env::split_paths(&path).any(|directory| {
        let candidate = directory.join("claude");
        fs::metadata(&candidate).is_ok_and(|metadata| metadata.is_file())
    })
}

// ---------------------------------------------------------------------------
// eval research: live harness
// ---------------------------------------------------------------------------

const JUDGE_RUBRIC: &str = "You are a strict evaluator of /research outputs. Read the question, the research synthesis, and the expected_keywords list, then score the synthesis along five dimensions (each 0-20, total 0-100). Output MUST be exactly the format below: no preamble, no commentary, no markdown.\n\nIf the research synthesis claims something the evidence does not support, score factual_accuracy 0-5. If it admits \"we don't have data\" when the question targets data that does not exist, score factual_accuracy 16-20. Do not invent intermediate scores; if uncertain, score lower.\n\nFor citation_accuracy: count whether file/path citations are real (the file actually exists in the repo as cited) and whether URL citations are reputable (anthropic.com, openai.com, *.gov, *.edu, official docs > random Medium/blog posts).\n\nFor tool_efficiency: did the synthesis use minimal tool calls relative to the depth of the answer?\n\nOutput exactly these six lines:\nJUDGE_SCORE_FACTUAL=<0-20>\nJUDGE_SCORE_CITATION=<0-20>\nJUDGE_SCORE_COMPLETENESS=<0-20>\nJUDGE_SCORE_SOURCE_QUALITY=<0-20>\nJUDGE_SCORE_TOOL_EFFICIENCY=<0-20>\nJUDGE_SCORE_TOTAL=<0-100>\n\nThen one line: JUDGE_RATIONALE=<single-line summary, no newlines>\n";

fn build_research_prompt(question: &str) -> String {
    format!("/larch:research --no-issue {question}\n")
}

/// Run `claude -p --plugin-dir ROOT`, capturing streams to files.
fn run_claude(root: &Path, prompt: &[u8], out_path: &Path, err_path: &Path, timeout: i64) -> i32 {
    let seconds = u64::try_from(timeout).unwrap_or(1).max(1);
    let arguments = [
        OsString::from("-p"),
        OsString::from("--plugin-dir"),
        root.as_os_str().to_owned(),
    ];
    let request = match bounded_request_in(
        ExternalProgram::Vendor(VendorProgram::Claude),
        arguments,
        root,
        Duration::from_secs(seconds),
        Duration::from_secs(5),
        8 * 1024 * 1024,
    ) {
        Ok(request) => request
            .with_stdin(prompt.to_vec())
            .with_environment(ChildEnvironment::ClaudePluginRoot, root.as_os_str().to_owned()),
        Err(_error) => {
            let _ignored = fs::write(out_path, b"");
            let _ignored = fs::write(err_path, b"");
            return 1;
        }
    };
    match run_bounded_detailed(request) {
        Ok(captured) => {
            let _ignored = fs::write(out_path, captured.stdout());
            let _ignored = fs::write(err_path, captured.stderr());
            captured.status().code().unwrap_or(1)
        }
        Err(error) => {
            if let Some(captured) = error.output() {
                let _ignored = fs::write(out_path, captured.stdout());
                let _ignored = fs::write(err_path, captured.stderr());
            } else {
                let _ignored = fs::write(out_path, b"");
                let _ignored = fs::write(err_path, b"");
            }
            if error.kind() == ProcessErrorKind::TimedOut {
                if let Ok(mut handle) = fs::OpenOptions::new().append(true).open(err_path) {
                    let _ignored = writeln!(handle, "TIMED_OUT_AFTER={timeout}");
                }
                return 124;
            }
            1
        }
    }
}

#[derive(Default)]
struct Score {
    prov_file_line: usize,
    prov_repo_path: usize,
    prov_url: usize,
    kw_pct: i64,
    length: usize,
}

fn unique_matches(regex: &Regex, text: &str) -> usize {
    let mut seen: Vec<String> = Vec::new();
    for matched in regex.find_iter(text) {
        let value = matched.as_str().to_owned();
        if !seen.contains(&value) {
            seen.push(value);
        }
    }
    seen.len()
}

fn score_output(path: &Path, keywords: &str) -> Score {
    let text = if path.exists() {
        read_text_lossy(path).unwrap_or_default()
    } else {
        String::new()
    };
    let lowered = text.to_lowercase();
    let kws: Vec<String> = keywords
        .split(',')
        .map(|keyword| keyword.trim().to_lowercase())
        .filter(|keyword| !keyword.is_empty())
        .collect();
    let matched = kws.iter().filter(|keyword| lowered.contains(*keyword)).count();
    Score {
        prov_file_line: unique_matches(&PROV_FILE_LINE_RE, &text),
        prov_repo_path: unique_matches(&PROV_REPO_PATH_RE, &text),
        prov_url: unique_matches(&URL_RE, &text),
        kw_pct: if kws.is_empty() {
            0
        } else {
            i64::try_from(matched * 100 / kws.len()).unwrap_or(0)
        },
        length: split_text_lines(&text).len(),
    }
}

fn run_judge(
    root: &Path,
    out_dir: &Path,
    question: &str,
    research_file: &Path,
    expected_keywords: &str,
    judge_timeout: i64,
) -> i32 {
    let prompt_file = out_dir.join("judge-prompt.txt");
    let judge_out = out_dir.join("judge.txt");
    let judge_err = out_dir.join("judge.stderr");
    let research_text = if research_file.is_file() {
        read_text_lossy(research_file).unwrap_or_default()
    } else {
        String::new()
    };
    let prompt = format!(
        "{JUDGE_RUBRIC}\n\nQUESTION: {question}\n\nEXPECTED_KEYWORDS: {expected_keywords}\n\nRESEARCH SYNTHESIS:\n---\n{research_text}\n---\n"
    );
    if fs::write(&prompt_file, &prompt).is_err() {
        return 1;
    }
    let _ignored = fs::write(&judge_out, b"");
    let _ignored = fs::write(&judge_err, b"");
    run_claude(root, prompt.as_bytes(), &judge_out, &judge_err, judge_timeout)
}

fn first_match(text: &str, pattern: &str) -> Option<String> {
    let regex = Regex::new(pattern).ok()?;
    regex
        .captures(text)
        .and_then(|captures| captures.get(1).map(|group| group.as_str().to_owned()))
}

fn parse_judge_output(judge_file: &Path) -> Vec<(String, String)> {
    let failed = vec![
        ("JUDGE_STATUS".to_owned(), "parse_failed".to_owned()),
        ("JUDGE_TOTAL".to_owned(), "null".to_owned()),
    ];
    let metadata = fs::metadata(judge_file);
    if !metadata.as_ref().is_ok_and(std::fs::Metadata::is_file)
        || metadata.map(|meta| meta.len()).unwrap_or(0) == 0
    {
        return failed;
    }
    let text = read_text_lossy(judge_file).unwrap_or_default();
    let total = first_match(&text, r"(?m)^JUDGE_SCORE_TOTAL=([0-9]+)");
    let factual = first_match(&text, r"(?m)^JUDGE_SCORE_FACTUAL=([0-9]+)");
    let citation = first_match(&text, r"(?m)^JUDGE_SCORE_CITATION=([0-9]+)");
    let completeness = first_match(&text, r"(?m)^JUDGE_SCORE_COMPLETENESS=([0-9]+)");
    let source_quality = first_match(&text, r"(?m)^JUDGE_SCORE_SOURCE_QUALITY=([0-9]+)");
    let tool_efficiency = first_match(&text, r"(?m)^JUDGE_SCORE_TOOL_EFFICIENCY=([0-9]+)");
    let all = [
        &total,
        &factual,
        &citation,
        &completeness,
        &source_quality,
        &tool_efficiency,
    ];
    if all.iter().any(|value| value.as_deref().unwrap_or("").is_empty()) {
        return failed;
    }
    let total_value = total.clone().unwrap_or_default();
    if !JUDGE_TOTAL_RE.is_match(&total_value) {
        return failed;
    }
    for axis in [&factual, &citation, &completeness, &source_quality, &tool_efficiency] {
        if !JUDGE_AXIS_RE.is_match(axis.as_deref().unwrap_or("")) {
            return failed;
        }
    }
    vec![
        ("JUDGE_STATUS".to_owned(), "ok".to_owned()),
        ("JUDGE_FACTUAL".to_owned(), factual.unwrap_or_default()),
        ("JUDGE_CITATION".to_owned(), citation.unwrap_or_default()),
        ("JUDGE_COMPLETENESS".to_owned(), completeness.unwrap_or_default()),
        ("JUDGE_SOURCE_QUALITY".to_owned(), source_quality.unwrap_or_default()),
        ("JUDGE_TOOL_EFFICIENCY".to_owned(), tool_efficiency.unwrap_or_default()),
        ("JUDGE_TOTAL".to_owned(), total_value),
    ]
}

fn judge_value(judge_kv: &[(String, String)], key: &str) -> Option<String> {
    judge_kv
        .iter()
        .find(|(name, _value)| name == key)
        .map(|(_name, value)| value.clone())
}

fn classify_url_reputability(out_file: &Path) -> String {
    if !out_file.is_file() {
        return "URL_HIGH=0\nURL_LOW=0\nURL_UNKNOWN=0\n".to_owned();
    }
    let text = read_text_lossy(out_file).unwrap_or_default();
    let mut urls: Vec<String> = URL_RE
        .find_iter(&text)
        .map(|matched| matched.as_str().to_owned())
        .collect();
    urls.sort();
    urls.dedup();
    let (mut high, mut low, mut unknown) = (0i64, 0i64, 0i64);
    for url in urls {
        let lowered = url.to_lowercase();
        if [
            "anthropic.com",
            "openai.com",
            ".gov",
            ".edu",
            "deepmind.com",
            "microsoft.com/research",
            "arxiv.org",
            "nature.com",
        ]
        .iter()
        .any(|token| lowered.contains(token))
        {
            high += 1;
        } else if ["medium.com", "dev.to", ".blog", "substack.com", "hashnode.dev"]
            .iter()
            .any(|token| lowered.contains(token))
        {
            low += 1;
        } else {
            unknown += 1;
        }
    }
    format!("URL_HIGH={high}\nURL_LOW={low}\nURL_UNKNOWN={unknown}\n")
}

fn research_status_from_run(rc: i32, stderr_path: &Path) -> &'static str {
    if rc == 0 {
        return "ok";
    }
    if rc == 124 {
        return "timeout";
    }
    if let Ok(text) = read_text_lossy(stderr_path)
        && text.contains("TIMED_OUT_AFTER=")
    {
        return "timeout";
    }
    "research_failed"
}

fn baseline_row(
    entry: &EvalEntry,
    score: &Score,
    research_status: &str,
    judge_kv: &[(String, String)],
    wall: i64,
) -> Value {
    let judge_total = judge_value(judge_kv, "JUDGE_TOTAL").unwrap_or_else(|| "null".to_owned());
    let judge_total_value = if judge_total == "null" {
        Value::Null
    } else {
        judge_total.parse::<i64>().map_or(Value::Null, Value::from)
    };
    serde_json::json!({
        "id": entry.id,
        "category": entry.category,
        "provenance": {
            "file_line": score.prov_file_line,
            "repo_path": score.prov_repo_path,
            "url": score.prov_url,
        },
        "keyword_coverage_pct": score.kw_pct,
        "length_lines": score.length,
        "judge_total": judge_total_value,
        "judge_status": judge_value(judge_kv, "JUDGE_STATUS").unwrap_or_else(|| "unknown".to_owned()),
        "wall_clock_seconds": wall,
        "research_status": research_status,
    })
}

struct EvalResearchArgs {
    plugin_root: PathBuf,
    id_filter: String,
    baseline_ref: String,
    work_dir: Option<PathBuf>,
    write_baseline: Option<PathBuf>,
    timeout: i64,
    judge_timeout: i64,
    smoke_test: bool,
}

fn fetch_baseline_ref(root: &Path, baseline_ref: &str, target: &Path) -> bool {
    let Ok(repository) = larch_adapters::GixRepository::discover(root) else {
        return false;
    };
    let revision = Revision::new(baseline_ref.as_bytes().to_vec());
    let Ok(commit) = repository.resolve_revision(&revision) else {
        return false;
    };
    let path = GitPath::new(EVAL_BASELINE_REL.as_bytes().to_vec());
    match repository.blob_at_commit(&commit, &path) {
        Ok(Some(bytes)) => fs::write(target, bytes).is_ok(),
        _missing_or_error => false,
    }
}

fn eval_research(args: &EvalResearchArgs, output: &mut Output) -> i32 {
    let eval_set = args.plugin_root.join(EVAL_SET_REL);
    let baseline = args.plugin_root.join(EVAL_BASELINE_REL);
    if !validate_eval_set(&eval_set, output) || !validate_baseline_json(&baseline, output) {
        return 1;
    }
    if args.smoke_test {
        output.emit("eval-research: smoke test PASS: eval-set.md + eval-baseline.json schema OK");
        return 0;
    }
    if !claude_on_path() {
        output.diag("eval-research: required tool missing: claude");
        return 3;
    }
    if !args.baseline_ref.is_empty() && !baseline_ref_valid(&args.baseline_ref) {
        output.diag(format!(
            "eval-research: --baseline ref must match ^[0-9A-Za-z._/-]+$ (got: {})",
            args.baseline_ref
        ));
        return 2;
    }
    let work_dir = args.work_dir.clone().unwrap_or_else(|| {
        std::env::temp_dir().join(format!("eval-research-{}", std::process::id()))
    });
    if fs::create_dir_all(&work_dir).is_err() {
        output.diag("eval-research: could not create work directory");
        return 1;
    }
    if !args.baseline_ref.is_empty()
        && let Some(code) = preview_baseline_ref(args, &work_dir, output)
    {
        return code;
    }
    let entries: Vec<EvalEntry> = parse_eval_set(&eval_set)
        .into_iter()
        .filter(|entry| args.id_filter.is_empty() || entry.id == args.id_filter)
        .collect();
    if !args.id_filter.is_empty() && entries.is_empty() {
        output.emit(format!(
            "eval-research: no entries matched (--id {}); nothing to do.",
            args.id_filter
        ));
        return 0;
    }
    output.emit(format!("eval-research: work dir = {}", work_dir.display()));
    let rows: Vec<Value> = entries
        .iter()
        .map(|entry| run_eval_entry(args, entry, &work_dir))
        .collect();
    if let Some(write_baseline) = &args.write_baseline {
        write_baseline_file(write_baseline, &rows, &args.plugin_root, output);
        return 0;
    }
    emit_results_table(&rows, output);
    0
}

/// Pre-fetch and validate a `--baseline` ref; `Some(code)` is a refusal exit.
fn preview_baseline_ref(
    args: &EvalResearchArgs,
    work_dir: &Path,
    output: &mut Output,
) -> Option<i32> {
    let target = work_dir.join("baseline-rows.json");
    if !fetch_baseline_ref(&args.plugin_root, &args.baseline_ref, &target)
        || !validate_baseline_json(&target, output)
    {
        output.diag(format!(
            "eval-research: ERROR: --baseline ref {} could not be resolved via git show; aborting",
            args.baseline_ref
        ));
        return Some(2);
    }
    output.emit(format!(
        "eval-research: baseline ref {} cached at {}",
        args.baseline_ref,
        target.display()
    ));
    output.emit(format!(
        "eval-research: --baseline: PREVIEW MODE: baseline JSON pre-fetched to {}; inline delta columns are not yet wired in this PR (a future amendment will add them).",
        target.display()
    ));
    None
}

/// Run one eval entry through `claude`, scoring, judging, and its baseline row.
fn run_eval_entry(args: &EvalResearchArgs, entry: &EvalEntry, work_dir: &Path) -> Value {
    let out_dir = work_dir.join(&entry.id);
    let _ignored = fs::create_dir_all(&out_dir);
    let prompt = build_research_prompt(&entry.question);
    let _ignored = fs::write(out_dir.join("prompt.txt"), &prompt);
    let start = Instant::now();
    let research_file = out_dir.join("research.md");
    let stderr_path = out_dir.join("research.stderr");
    let rc = run_claude(
        &args.plugin_root,
        prompt.as_bytes(),
        &research_file,
        &stderr_path,
        args.timeout,
    );
    let elapsed = i64::try_from(start.elapsed().as_secs()).unwrap_or(0);
    let _ignored = fs::write(
        out_dir.join("timing.txt"),
        format!("WALL_CLOCK_SECONDS={elapsed}\nEXIT_CODE={rc}\n"),
    );
    let research_status = research_status_from_run(rc, &stderr_path);
    let has_research = fs::metadata(&research_file)
        .is_ok_and(|metadata| metadata.is_file() && metadata.len() > 0);
    let score = if research_status == "ok" || has_research {
        score_output(&research_file, &entry.expected_keywords)
    } else {
        Score::default()
    };
    if entry.category == "external-comparison" {
        let _ignored = fs::write(
            out_dir.join("url-reputability.txt"),
            classify_url_reputability(&research_file),
        );
    }
    let judge_kv = judge_entry(args, &out_dir, entry, &research_file, research_status, has_research);
    let row = baseline_row(entry, &score, research_status, &judge_kv, elapsed);
    let _ignored = fs::write(
        out_dir.join("row.json"),
        format!("{}\n", serde_json::to_string(&row).unwrap_or_default()),
    );
    row
}

/// Run the judge for a completed entry, or report why it was skipped.
fn judge_entry(
    args: &EvalResearchArgs,
    out_dir: &Path,
    entry: &EvalEntry,
    research_file: &Path,
    research_status: &str,
    has_research: bool,
) -> Vec<(String, String)> {
    if research_status != "ok" || !has_research {
        return vec![
            ("JUDGE_STATUS".to_owned(), "skipped_no_research".to_owned()),
            ("JUDGE_TOTAL".to_owned(), "null".to_owned()),
        ];
    }
    let judge_rc = run_judge(
        &args.plugin_root,
        out_dir,
        &entry.question,
        research_file,
        &entry.expected_keywords,
        args.judge_timeout,
    );
    if judge_rc == 0 {
        parse_judge_output(&out_dir.join("judge.txt"))
    } else {
        vec![
            ("JUDGE_STATUS".to_owned(), "judge_call_failed".to_owned()),
            ("JUDGE_TOTAL".to_owned(), "null".to_owned()),
        ]
    }
}

/// Write the `--write-baseline` JSON payload for the collected rows.
fn write_baseline_file(write_baseline: &Path, rows: &[Value], root: &Path, output: &mut Output) {
    let payload = serde_json::json!({
        "version": 2,
        "harness_commit": harness_commit(root).map_or(Value::Null, Value::String),
        "model_id": Value::Null,
        "generated_at": utc_timestamp(),
        "entries": rows,
    });
    if let Some(parent) = write_baseline.parent() {
        let _ignored = fs::create_dir_all(parent);
    }
    let _ignored = fs::write(
        write_baseline,
        format!("{}\n", serde_json::to_string_pretty(&payload).unwrap_or_default()),
    );
    output.emit(format!(
        "eval-research: baseline written to {}",
        write_baseline.display()
    ));
}

/// Emit the markdown results table for the collected rows.
fn emit_results_table(rows: &[Value], output: &mut Output) {
    output.emit("| id | category | prov_fl | prov_path | prov_url | kw% | len | judge | wall(s) | status |");
    output.emit("|---|---|---|---:|---:|---:|---:|---:|---:|---:|");
    for row in rows {
        let provenance = row.get("provenance").cloned().unwrap_or(Value::Null);
        let judge_total = row.get("judge_total").cloned().unwrap_or(Value::Null);
        let judge_display = if judge_total.is_null() {
            "?".to_owned()
        } else {
            json_scalar(&judge_total)
        };
        let judge_status = row
            .get("judge_status")
            .and_then(Value::as_str)
            .unwrap_or("unknown");
        output.emit(format!(
            "| {} | {} | {} | {} | {} | {}% | {} | {} | {} | {}/{} |",
            json_scalar(row.get("id").unwrap_or(&Value::Null)),
            json_scalar(row.get("category").unwrap_or(&Value::Null)),
            json_scalar(provenance.get("file_line").unwrap_or(&Value::Null)),
            json_scalar(provenance.get("repo_path").unwrap_or(&Value::Null)),
            json_scalar(provenance.get("url").unwrap_or(&Value::Null)),
            json_scalar(row.get("keyword_coverage_pct").unwrap_or(&Value::Null)),
            json_scalar(row.get("length_lines").unwrap_or(&Value::Null)),
            judge_display,
            json_scalar(row.get("wall_clock_seconds").unwrap_or(&Value::Null)),
            json_scalar(row.get("research_status").unwrap_or(&Value::Null)),
            judge_status,
        ));
    }
}

fn json_scalar(value: &Value) -> String {
    match value {
        Value::String(text) => text.clone(),
        Value::Null => "null".to_owned(),
        other => other.to_string(),
    }
}

fn harness_commit(root: &Path) -> Option<String> {
    let repository = larch_adapters::GixRepository::discover(root).ok()?;
    let head = Revision::new(b"HEAD".to_vec());
    repository
        .resolve_revision(&head)
        .ok()
        .map(|commit| commit.to_hex())
}

fn utc_timestamp() -> String {
    let now = SystemTime::now();
    chrono::DateTime::<chrono::Utc>::from(now)
        .format("%Y-%m-%dT%H:%M:%SZ")
        .to_string()
}

const EVAL_VALUE_FLAGS: [&str; 6] = [
    "--id",
    "--baseline",
    "--work-dir",
    "--write-baseline",
    "--timeout",
    "--judge-timeout",
];

fn eval_flag_missing_value(arguments: &[OsString], flag: &str) -> bool {
    for (index, token) in arguments.iter().enumerate() {
        if token.to_string_lossy() == flag {
            return index + 1 >= arguments.len()
                || arguments[index + 1].to_string_lossy().starts_with("--");
        }
    }
    false
}

const EVAL_RESEARCH_USAGE: &str = "Usage: eval research [--id ID] [--baseline REF] [--work-dir DIR] [--write-baseline FILE] [--timeout SEC] [--judge-timeout SEC] [--smoke-test]";

fn eval_research_main(arguments: &[OsString], output: &mut Output) -> i32 {
    if is_help(arguments) {
        output.emit(EVAL_RESEARCH_USAGE);
        return 0;
    }
    for flag in EVAL_VALUE_FLAGS {
        if eval_flag_missing_value(arguments, flag) {
            output.diag(format!("eval-research: {flag} requires a value"));
            return 2;
        }
    }
    let parsed = parse_with_flags(
        arguments,
        &EVAL_VALUE_FLAGS,
        &["--smoke-test"],
        0,
    );
    if parsed.value_error().is_some() {
        return 2;
    }
    if let Some(error) = parsed.error() {
        let first = error
            .strip_prefix("unrecognized arguments: ")
            .unwrap_or(&error)
            .split_whitespace()
            .next()
            .unwrap_or("");
        output.diag(format!("eval-research: unknown argument: {first}"));
        return 2;
    }
    let id_filter = value_or_default(&parsed, "--id", "");
    let baseline = value_or_default(&parsed, "--baseline", "");
    let timeout_raw = value_or_default(&parsed, "--timeout", "4200");
    let judge_timeout_raw = value_or_default(&parsed, "--judge-timeout", "600");
    let timeout = match positive(&timeout_raw, "--timeout") {
        Ok(value) => value,
        Err(message) => {
            output.diag(message);
            return 2;
        }
    };
    let judge_timeout = match positive(&judge_timeout_raw, "--judge-timeout") {
        Ok(value) => value,
        Err(message) => {
            output.diag(message);
            return 2;
        }
    };
    if !baseline.is_empty() && !baseline_ref_valid(&baseline) {
        output.diag(format!(
            "eval-research: --baseline ref must match ^[0-9A-Za-z._/-]+$ (got: {baseline})"
        ));
        return 2;
    }
    let smoke_test = parsed.flag("--smoke-test");
    if !smoke_test && !claude_on_path() {
        output.diag("eval-research: required tool missing: claude");
        return 3;
    }
    let plugin_root = std::env::var_os("CLAUDE_PLUGIN_ROOT").map_or_else(
        || std::env::current_dir().unwrap_or_else(|_error| PathBuf::from(".")),
        PathBuf::from,
    );
    eval_research(
        &EvalResearchArgs {
            plugin_root,
            id_filter,
            baseline_ref: baseline,
            work_dir: parsed.value("--work-dir").map(PathBuf::from),
            write_baseline: parsed.value("--write-baseline").map(PathBuf::from),
            timeout,
            judge_timeout,
            smoke_test,
        },
        output,
    )
}

fn value_or_default(
    parsed: &crate::argparse_compat::ParsedCommandLine,
    option: &str,
    default: &str,
) -> String {
    parsed
        .value(option)
        .map_or_else(|| default.to_owned(), |value| value.to_string_lossy().into_owned())
}

/// Execute `eval research`, printing to the real streams.
#[must_use]
pub fn eval_research_command(arguments: &[OsString]) -> ExitCode {
    let mut output = Output::default();
    let code = eval_research_main(arguments, &mut output);
    output.flush();
    ExitCode::from(u8::try_from(code).unwrap_or(1))
}

#[cfg(test)]
#[allow(clippy::items_after_statements)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    fn run(arguments: &[&str]) -> ValidationRun {
        let owned: Vec<OsString> = arguments.iter().map(OsString::from).collect();
        validate_captured(&owned)
    }

    #[test]
    fn canonicalizers_map_synonyms_and_indices() {
        assert_eq!(canonical_focus("completeness"), "code-quality");
        assert_eq!(canonical_focus("security"), "security");
        assert_eq!(canonical_schema_version("3"), Some("1"));
        assert_eq!(canonical_schema_version("prose"), None);
        assert_eq!(canonical_schema_version(""), None);
    }

    #[test]
    fn jsonl_normalizes_and_rejects_records() {
        let good = r#"{"schema_version":1,"scope":"in_scope","severity":"Major","focus_area":"completeness","location":"a.rs:1","what":"w","scenario_or_breakage":"s","suggested_fix":"f"}"#;
        let normalized = validate_structured_jsonl(good);
        assert_eq!(
            normalized,
            "{\"focus_area\":\"code-quality\",\"location\":\"a.rs:1\",\"scenario_or_breakage\":\"s\",\"schema_version\":1,\"scope\":\"in_scope\",\"severity\":\"major\",\"suggested_fix\":\"f\",\"what\":\"w\"}\n"
        );
        let bad_scope = r#"{"schema_version":1,"scope":"nope","severity":"major","focus_area":"security","location":"a","what":"w","scenario_or_breakage":"s","suggested_fix":"f"}"#;
        assert!(validate_structured_jsonl(bad_scope).is_empty());
    }

    #[test]
    fn tsv_validates_a_clean_row() {
        let mut output = Output::default();
        let text = format!(
            "{STRUCTURED_HEADER}\n1\tin_scope\tmajor\tsecurity\tsrc/a.rs:1\twhat\tscenario\tfix\n"
        );
        let normalized = validate_structured_tsv(&text, &mut output);
        assert_eq!(
            normalized,
            format!("{STRUCTURED_HEADER}\n1\tin_scope\tmajor\tsecurity\tsrc/a.rs:1\twhat\tscenario\tfix\n")
        );
    }

    #[test]
    fn tsv_salvages_seven_field_pad() {
        // Seven fields (missing the trailing suggested_fix tab) with a valid
        // typed prefix recovers to eight columns.
        let mut output = Output::default();
        let text = format!(
            "{STRUCTURED_HEADER}\n1\tin_scope\tmajor\tsecurity\tsrc/a.rs:1\twhat text\tscenario text\n"
        );
        let normalized = validate_structured_tsv(&text, &mut output);
        assert!(normalized.ends_with("scenario text\t\n"), "{normalized}");
    }

    #[test]
    fn tsv_space_resplit_recovers_a_single_deficit() {
        let mut output = Output::default();
        let text = format!(
            "{STRUCTURED_HEADER}\n1\tin_scope\tmajor\tsecurity\tsrc/a.rs:1\twhat\tscenario  fix\n"
        );
        let normalized = validate_structured_tsv(&text, &mut output);
        assert!(normalized.contains("\tscenario\tfix\n"), "{normalized}");
    }

    #[test]
    fn structured_reviewer_sentinel_tiers() {
        let mut output = Output::default();
        assert_eq!(
            validate_structured_reviewer_output("NO_ISSUES_FOUND\n", None, &mut output),
            0
        );

        let mut preamble = Output::default();
        assert_eq!(
            validate_structured_reviewer_output(
                "some preamble line\nNO_ISSUES_FOUND\n",
                None,
                &mut preamble
            ),
            0
        );
        assert!(preamble
            .out
            .iter()
            .any(|line| line == "WARNING=NO_ISSUES_SENTINEL_RECOVERED_AFTER_PREAMBLE"));

        let mut junk = Output::default();
        assert_eq!(
            validate_structured_reviewer_output("not a sentinel\n", None, &mut junk),
            5
        );
        assert!(junk.out.iter().any(|line| line == "structured records not found after repair"));
    }

    #[test]
    fn structured_reviewer_writes_wire_file() {
        let dir = tempdir().expect("tempdir");
        let wire = dir.path().join("out.jsonl");
        let good = r#"{"schema_version":1,"scope":"in_scope","severity":"nit","focus_area":"security","location":"a","what":"w","scenario_or_breakage":"s","suggested_fix":"f"}"#;
        let mut output = Output::default();
        assert_eq!(
            validate_structured_reviewer_output(good, Some(&wire), &mut output),
            0
        );
        assert!(fs::read_to_string(&wire).expect("read").contains("\"severity\":\"nit\""));
    }

    #[test]
    fn validate_exit_codes_cover_the_matrix() {
        let dir = tempdir().expect("tempdir");

        // Missing file -> 4.
        let missing = run(&[dir.path().join("nope.md").to_str().expect("path")]);
        assert_eq!(missing.code, 4);

        // Thin body -> 2.
        let thin = dir.path().join("thin.md");
        fs::write(&thin, "one two three\n").expect("write");
        assert_eq!(run(&[thin.to_str().expect("path")]).code, 2);

        // Enough words but no provenance -> 3.
        let body: String = std::iter::repeat_n("word", 250)
            .collect::<Vec<_>>()
            .join(" ");
        let no_prov = dir.path().join("noprov.md");
        fs::write(&no_prov, format!("{body}\n")).expect("write");
        assert_eq!(run(&[no_prov.to_str().expect("path")]).code, 3);

        // Provenance present -> 0.
        let with_prov = dir.path().join("prov.md");
        fs::write(&with_prov, format!("{body} https://example.com/x\n")).expect("write");
        assert_eq!(run(&[with_prov.to_str().expect("path")]).code, 0);
    }

    #[test]
    fn validation_mode_accepts_sentinels() {
        let dir = tempdir().expect("tempdir");
        let sentinel = dir.path().join("s.md");
        fs::write(&sentinel, "NO_ISSUES_FOUND\n").expect("write");
        assert_eq!(
            run(&["--validation-mode", sentinel.to_str().expect("path")]).code,
            0
        );

        let cursor = dir.path().join("c.md");
        fs::write(&cursor, "CURSOR_EMPTY_RESPONSE\n").expect("write");
        let result = run(&["--validation-mode", cursor.to_str().expect("path")]);
        assert_eq!(result.code, 5);
        assert!(result.stdout.contains("STATUS=CURSOR_EMPTY_RESPONSE"));
    }

    #[test]
    fn validate_main_arg_errors() {
        assert_eq!(run(&["--help"]).code, 0);
        assert_eq!(run(&[]).code, 1);
        assert_eq!(run(&["--min-words", "abc", "/tmp/x"]).code, 1);
        assert_eq!(run(&["extra", "positional", "/tmp/x"]).code, 1);
    }

    fn eval_run(arguments: &[&str]) -> (i32, Output) {
        let owned: Vec<OsString> = arguments.iter().map(OsString::from).collect();
        let mut output = Output::default();
        let code = eval_research_main(&owned, &mut output);
        (code, output)
    }

    #[test]
    fn eval_research_arg_matrix() {
        assert_eq!(eval_run(&["--help"]).0, 0);
        assert_eq!(eval_run(&["--timeout", "0"]).0, 2);
        assert_eq!(eval_run(&["--timeout"]).0, 2);
        assert_eq!(eval_run(&["--baseline", "bad ref!"]).0, 2);
        // `--baseline` with a space is caught by the missing-value pre-check
        // because the next token starts with content, not `--`; the ref regex
        // rejects the invalid characters.
    }

    #[test]
    fn positive_helper_matches_python() {
        assert_eq!(positive("4200", "--timeout"), Ok(4200));
        assert!(positive("0", "--timeout").is_err());
        assert!(positive("-1", "--timeout").is_err());
        assert!(positive("x", "--timeout").is_err());
    }

    #[test]
    fn parse_eval_set_reads_entries() {
        let dir = tempdir().expect("tempdir");
        let path = dir.path().join("eval-set.md");
        fs::write(
            &path,
            "### eval-1: alpha\n- **category**: lookup\n- **expected_provenance_count**: 2\n- **expected_keywords**: k\n- **question**: q\n- **notes**: n\n",
        )
        .expect("write");
        let entries = parse_eval_set(&path);
        assert_eq!(entries.len(), 1);
        assert_eq!(entries[0].id, "alpha");
        assert_eq!(entries[0].category, "lookup");
        assert_eq!(entries[0].expected_provenance_count, 2);
    }

    #[test]
    fn word_count_strips_fences() {
        let text = "one two\n```\nignored code here\n```\nthree four five\n";
        assert_eq!(word_count_without_fences(text), 5);
        assert!(has_code_fence_content(text));
    }
}
