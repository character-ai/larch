//! Filtered session-transcript rendering for committed run logs.
//!
//! A raw Claude Code session JSONL is untrusted operator-adjacent input: it
//! carries whatever a tool printed, whatever a model wrote, and whatever a
//! remote page fed either of them. This module reduces that stream to the
//! committed schema-v3 chat view, keeping only slash commands, prose,
//! error-adjacent thinking, errored or warned tool results, and sanitized
//! reference reads.
//!
//! Three properties matter more than compactness:
//!
//! * **Structure is ours, not the content's.** Every rendered string is escaped
//!   so no code point in transcript content can terminate a document line. That
//!   includes the three line terminators JSON leaves bare — `U+0085`, `U+2028`,
//!   and `U+2029` — which Python's `str.splitlines` treats as record breaks.
//! * **Input is bounded.** An oversized file is refused and an oversized record
//!   is skipped and counted; neither is silently truncated.
//! * **Invalid UTF-8 is reported.** Bytes are replaced, as the Python owner did,
//!   but the count of affected records reaches the caller instead of vanishing.

use std::{
    fmt::{self, Write as _},
    fs,
    path::{Path, PathBuf},
};

use regex::Regex;
use serde_json::Value;
use std::collections::HashMap;
use std::sync::LazyLock;

/// Committed chat-view schema version.
pub const SCHEMA_VERSION: u64 = 3;

/// Redaction policy name recorded in the header line.
pub const TRANSCRIPT_POLICY: &str = "prose-errors-and-reference-reads";

/// Largest raw session file this renderer accepts.
///
/// Real sessions are far smaller. The bound exists so a corrupt or hostile
/// source cannot force an unbounded read, and it refuses loudly rather than
/// rendering a partial document that reads as complete.
pub const MAX_INPUT_BYTES: u64 = 512 * 1024 * 1024;

/// Largest single JSONL record this renderer parses.
///
/// A longer record is skipped and counted, the same disposition the Python
/// owner gave an unparseable line, and the count reaches the caller.
pub const MAX_RECORD_BYTES: usize = 8 * 1024 * 1024;

/// Placeholder a redacted operator repository path collapses to.
pub(super) const REDACTED_OPERATOR_REPO: &str = "<OPERATOR_REPO_PATH>";

/// Record `type` values the harness uses for housekeeping, never for content.
const HOUSEKEEPING_TYPES: [&str; 6] = [
    "permission-mode",
    "file-history-snapshot",
    "attachment",
    "last-prompt",
    "queue-operation",
    "system",
];

/// Leading characters of a Bash body that classification inspects.
const CLASSIFY_HEAD_CHARS: usize = 500;

/// Component count of an in-scope `skills/shared/<file>.md` reference.
const SHARED_REFERENCE_PARTS: usize = 3;

/// Component count of an in-scope `skills/<skill>/references/<file>.md` read.
const SKILL_REFERENCE_PARTS: usize = 4;

static SYSTEM_REMINDER: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?s)<system-reminder>.*?</system-reminder>")
        .expect("system-reminder expression is valid")
});
static COMMAND_NAME: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?s)<command-name>(.*?)</command-name>").expect("command-name expression is valid")
});
static COMMAND_ARGS: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?s)<command-args>(.*?)</command-args>").expect("command-args expression is valid")
});
static EXIT_CODE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?m)^Exit code ([1-9][0-9]*)").expect("exit-code expression is valid")
});
static ERROR_PREFIX: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"(?m)^Error:").expect("error-prefix expression is valid"));
// ASCII-only case folding: the workspace regex build excludes `unicode-case`,
// and the Python owner's heuristic only ever matched this ASCII literal.
static WARNING: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"(?i-u)warning:").expect("warning expression is valid"));

/// Why one raw session file could not become a rendered transcript.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum TranscriptError {
    /// The path is not a regular file the renderer can reach.
    Missing(PathBuf),
    /// The file exists but its bytes could not be read.
    Unreadable {
        /// Source path.
        path: PathBuf,
        /// One-line operating-system detail.
        detail: String,
    },
    /// The file is larger than [`MAX_INPUT_BYTES`].
    Oversized {
        /// Source path.
        path: PathBuf,
        /// Observed size in bytes.
        bytes: u64,
    },
    /// The file parsed but held no records.
    NoRecords(PathBuf),
}

impl fmt::Display for TranscriptError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Missing(path) => write!(formatter, "input missing: {}", path.display()),
            Self::Unreadable { path, detail } => {
                write!(formatter, "input unreadable: {}: {detail}", path.display())
            }
            Self::Oversized { path, bytes } => write!(
                formatter,
                "input exceeds the {MAX_INPUT_BYTES}-byte bound: {} is {bytes} bytes",
                path.display()
            ),
            Self::NoRecords(path) => {
                write!(formatter, "no parseable records in {}", path.display())
            }
        }
    }
}

/// Bounded-input conditions the renderer survived but must not hide.
#[derive(Debug, Default, Clone, Copy, PartialEq, Eq)]
pub struct TranscriptWarnings {
    /// Records whose bytes were not valid UTF-8 and were replaced.
    pub replaced_records: usize,
    /// Records skipped for exceeding [`MAX_RECORD_BYTES`].
    pub oversized_records: usize,
}

impl TranscriptWarnings {
    /// Return whether any bounded-input condition fired.
    #[must_use]
    pub const fn is_empty(&self) -> bool {
        self.replaced_records == 0 && self.oversized_records == 0
    }

    /// Render one operator-facing line per condition that fired.
    #[must_use]
    pub fn lines(&self) -> Vec<String> {
        let mut lines = Vec::new();
        if self.replaced_records > 0 {
            lines.push(format!(
                "replaced invalid UTF-8 bytes in {} record(s)",
                self.replaced_records
            ));
        }
        if self.oversized_records > 0 {
            lines.push(format!(
                "skipped {} record(s) over the {MAX_RECORD_BYTES}-byte record bound",
                self.oversized_records
            ));
        }
        lines
    }
}

/// One rendered transcript plus what the renderer had to report about its input.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RenderedTranscript {
    /// Complete JSONL document, header line first, newline-terminated.
    pub text: String,
    /// Turn records the document carries.
    pub turns: usize,
    /// Bounded-input conditions the renderer survived.
    pub warnings: TranscriptWarnings,
}

/// Render one raw Claude Code session JSONL as the committed chat view.
///
/// `repo_root` is the clone whose absolute prefix a reference read may carry;
/// pass `None` when no root is resolvable, which leaves absolute reads
/// unmatched rather than stripping a bare leading separator.
///
/// # Errors
/// Returns [`TranscriptError`] when the input is missing, unreadable, larger
/// than [`MAX_INPUT_BYTES`], or holds no parseable record.
pub fn render_session_transcript(
    input: &Path,
    repo_root: Option<&Path>,
) -> Result<RenderedTranscript, TranscriptError> {
    let metadata =
        fs::metadata(input).map_err(|_error| TranscriptError::Missing(input.to_path_buf()))?;
    if !metadata.is_file() {
        return Err(TranscriptError::Missing(input.to_path_buf()));
    }
    if metadata.len() > MAX_INPUT_BYTES {
        return Err(TranscriptError::Oversized {
            path: input.to_path_buf(),
            bytes: metadata.len(),
        });
    }
    let bytes = fs::read(input).map_err(|error| TranscriptError::Unreadable {
        path: input.to_path_buf(),
        detail: one_line(&error.to_string()),
    })?;
    let mut warnings = TranscriptWarnings::default();
    let records = parse_jsonl(&bytes, &mut warnings);
    if records.is_empty() {
        return Err(TranscriptError::NoRecords(input.to_path_buf()));
    }
    Ok(render_records(
        &records,
        basename(input),
        repo_root,
        warnings,
    ))
}

/// Render already-parsed records, used by both the file path and the tests.
fn render_records(
    records: &[Value],
    source_basename: String,
    repo_root: Option<&Path>,
    warnings: TranscriptWarnings,
) -> RenderedTranscript {
    let (id_to_name, id_to_kept) = first_pass(records);
    let mut turns: Vec<Json> = Vec::new();
    for record in records {
        if record.get("isMeta").is_some_and(truthy) {
            continue;
        }
        if record
            .get("type")
            .and_then(Value::as_str)
            .is_some_and(|kind| HOUSEKEEPING_TYPES.contains(&kind))
        {
            continue;
        }
        let Some(message) = record.get("message").filter(|value| value.is_object()) else {
            continue;
        };
        let role = message.get("role").and_then(Value::as_str);
        let content = message.get("content");
        let blocks = match role {
            Some("user") => render_user_blocks(content, &id_to_name),
            Some("assistant") => render_assistant_blocks(content, &id_to_kept, repo_root),
            _other => continue,
        };
        if blocks.is_empty() {
            continue;
        }
        let turn = turns.len() + 1;
        turns.push(Json::Object(vec![
            ("turn", Json::number(turn)),
            ("role", Json::string(role.unwrap_or_default())),
            ("blocks", Json::Array(blocks)),
        ]));
    }
    let header = Json::Object(vec![
        ("v", Json::number(SCHEMA_VERSION)),
        ("source_basename", Json::String(source_basename)),
        ("turns", Json::number(turns.len())),
        ("policy", Json::string(TRANSCRIPT_POLICY)),
    ]);
    let mut text = String::new();
    header.write(&mut text);
    for turn in &turns {
        text.push('\n');
        turn.write(&mut text);
    }
    text.push('\n');
    RenderedTranscript {
        turns: turns.len(),
        text,
        warnings,
    }
}

/// Map every tool-use id to its tool name and to whether its result was kept.
fn first_pass(records: &[Value]) -> (HashMap<String, String>, HashMap<String, bool>) {
    let mut id_to_name: HashMap<String, String> = HashMap::new();
    let mut id_to_kept: HashMap<String, bool> = HashMap::new();
    for record in records {
        if record.get("isMeta").is_some_and(truthy) {
            continue;
        }
        if record
            .get("type")
            .and_then(Value::as_str)
            .is_some_and(|kind| HOUSEKEEPING_TYPES.contains(&kind))
        {
            continue;
        }
        let Some(content) = record
            .get("message")
            .filter(|value| value.is_object())
            .and_then(|message| message.get("content"))
            .and_then(Value::as_array)
        else {
            continue;
        };
        for block in content {
            if !block.is_object() {
                continue;
            }
            match block.get("type").and_then(Value::as_str) {
                Some("tool_use") => {
                    if let Some(id) = block.get("id").and_then(Value::as_str)
                        && !id.is_empty()
                    {
                        let name = block
                            .get("name")
                            .and_then(Value::as_str)
                            .unwrap_or("?")
                            .to_owned();
                        let _previous = id_to_name.insert(id.to_owned(), name);
                    }
                }
                Some("tool_result") => {
                    let Some(id) = block
                        .get("tool_use_id")
                        .and_then(Value::as_str)
                        .filter(|id| !id.is_empty())
                    else {
                        continue;
                    };
                    let name = id_to_name.get(id).map_or("?", String::as_str);
                    let outcome = classify_tool_result(block, name);
                    let _previous =
                        id_to_kept.insert(id.to_owned(), outcome.error || outcome.warning);
                }
                _other => {}
            }
        }
    }
    (id_to_name, id_to_kept)
}

/// Render one user turn's kept blocks.
fn render_user_blocks(content: Option<&Value>, id_to_name: &HashMap<String, String>) -> Vec<Json> {
    let mut blocks = Vec::new();
    match content {
        Some(Value::String(text)) => {
            let stripped = python_strip(&SYSTEM_REMINDER.replace_all(text, ""));
            if stripped.contains("<command-name>") {
                let name = capture(&COMMAND_NAME, &stripped);
                let args = capture(&COMMAND_ARGS, &stripped);
                if !name.is_empty() {
                    let mut command = vec![
                        ("type", Json::string("command")),
                        ("name", Json::String(name)),
                    ];
                    if !args.is_empty() {
                        command.push(("args", Json::String(args)));
                    }
                    blocks.push(Json::Object(command));
                }
            } else if !stripped.is_empty() {
                blocks.push(Json::Object(vec![
                    ("type", Json::string("text")),
                    ("value", Json::String(stripped)),
                ]));
            }
        }
        Some(Value::Array(items)) => {
            for block in items {
                if !block.is_object()
                    || block.get("type").and_then(Value::as_str) != Some("tool_result")
                {
                    continue;
                }
                let id = block
                    .get("tool_use_id")
                    .and_then(Value::as_str)
                    .unwrap_or_default();
                let name = id_to_name.get(id).map_or("?", String::as_str);
                let outcome = classify_tool_result(block, name);
                if !outcome.error && !outcome.warning {
                    // v3 policy: routine tool results are omitted entirely.
                    continue;
                }
                let mut rendered = vec![
                    ("type", Json::string("tool_result")),
                    ("tool_use_id", Json::string(id)),
                    ("name", Json::string(name)),
                    ("text", Json::String(tool_result_text(block))),
                ];
                if outcome.error {
                    rendered.push(("error", Json::Bool(true)));
                }
                if outcome.warning {
                    rendered.push(("warning", Json::Bool(true)));
                }
                if let Some(code) = outcome.exit_code {
                    rendered.push(("exit_code", Json::Number(code)));
                }
                blocks.push(Json::Object(rendered));
            }
        }
        _other => {}
    }
    blocks
}

/// Render one assistant turn's kept blocks.
fn render_assistant_blocks(
    content: Option<&Value>,
    id_to_kept: &HashMap<String, bool>,
    repo_root: Option<&Path>,
) -> Vec<Json> {
    let Some(items) = content.and_then(Value::as_array) else {
        return Vec::new();
    };
    let turn_has_kept = items.iter().any(|block| {
        block.is_object()
            && block.get("type").and_then(Value::as_str) == Some("tool_use")
            && block
                .get("id")
                .and_then(Value::as_str)
                .is_some_and(|id| id_to_kept.get(id).copied().unwrap_or(false))
    });
    let mut blocks = Vec::new();
    for block in items {
        if !block.is_object() {
            continue;
        }
        let rendered = match block.get("type").and_then(Value::as_str) {
            Some("text") => assistant_text_block(block),
            Some("thinking") if turn_has_kept => assistant_thinking_block(block),
            Some("tool_use") => reference_read_block(block, repo_root),
            // v3 policy: non-reference tool calls are omitted entirely.
            _other => None,
        };
        if let Some(rendered) = rendered {
            blocks.push(rendered);
        }
    }
    blocks
}

fn assistant_text_block(block: &Value) -> Option<Json> {
    let text = block
        .get("text")
        .and_then(Value::as_str)
        .unwrap_or_default();
    let stripped = python_rstrip(&SYSTEM_REMINDER.replace_all(text, ""));
    if stripped.is_empty() || stripped.starts_with("Base directory for this skill") {
        return None;
    }
    Some(Json::Object(vec![
        ("type", Json::string("text")),
        ("value", Json::String(stripped)),
    ]))
}

fn assistant_thinking_block(block: &Value) -> Option<Json> {
    let thinking = block
        .get("thinking")
        .and_then(Value::as_str)
        .unwrap_or_default();
    let stripped = python_strip(thinking);
    if stripped.is_empty() {
        return None;
    }
    Some(Json::Object(vec![
        ("type", Json::string("thinking")),
        ("value", Json::String(stripped)),
    ]))
}

fn reference_read_block(block: &Value, repo_root: Option<&Path>) -> Option<Json> {
    if block.get("name").and_then(Value::as_str) != Some("Read") {
        return None;
    }
    let input = block.get("input").filter(|value| value.is_object())?;
    let relative = normalize_reference_read_path(input.get("file_path"), repo_root)?;
    Some(Json::Object(vec![
        ("type", Json::string("tool_use")),
        ("name", Json::string("Read")),
        (
            "input",
            Json::Object(vec![("file_path", Json::String(relative))]),
        ),
    ]))
}

/// Concatenate a tool result's textual body, whatever shape the harness used.
fn tool_result_text(block: &Value) -> String {
    match block.get("content") {
        Some(Value::String(text)) => text.clone(),
        Some(Value::Array(items)) => items
            .iter()
            .filter(|item| item.is_object())
            .filter(|item| item.get("type").and_then(Value::as_str) == Some("text"))
            .map(|item| item.get("text").and_then(Value::as_str).unwrap_or_default())
            .collect(),
        _other => String::new(),
    }
}

/// How one tool result classifies under the v3 keep policy.
#[derive(Debug, Default, Clone, PartialEq, Eq)]
struct ToolResultOutcome {
    /// The harness flagged the result, or a Bash body reported a failure.
    error: bool,
    /// A Bash body carried a warning and was not already an error.
    warning: bool,
    /// Exit code parsed from a leading `Exit code N` line, when present.
    exit_code: Option<String>,
}

/// Classify one tool-result block for the named tool.
fn classify_tool_result(block: &Value, tool_name: &str) -> ToolResultOutcome {
    let flagged = block.get("is_error") == Some(&Value::Bool(true));
    if tool_name != "Bash" {
        return ToolResultOutcome {
            error: flagged,
            warning: false,
            exit_code: None,
        };
    }
    let text = tool_result_text(block);
    let head: String = text.chars().take(CLASSIFY_HEAD_CHARS).collect();
    let exit_code = EXIT_CODE
        .captures(&head)
        .and_then(|captures| captures.get(1))
        .map(|code| code.as_str().to_owned());
    let error = flagged || exit_code.is_some() || ERROR_PREFIX.is_match(&head);
    let warning = !error && WARNING.is_match(&head);
    ToolResultOutcome {
        error,
        warning,
        exit_code,
    }
}

/// Reduce one `Read` tool input to its in-scope repository-relative reference.
///
/// Returns `None` for every path outside `skills/shared/<file>.md` and
/// `skills/<skill>/references/<file>.md`, which is the only file identity the
/// committed transcript may carry.
fn normalize_reference_read_path(raw: Option<&Value>, repo_root: Option<&Path>) -> Option<String> {
    let raw = raw.and_then(Value::as_str)?;
    // Byte comparison, not a path-extension check: the Python owner tested the
    // literal suffix, so a bare `.md` name qualifies here too.
    if !raw.as_bytes().ends_with(b".md") {
        return None;
    }
    let mut path = raw;
    let redacted_prefix = format!("{REDACTED_OPERATOR_REPO}/");
    if let Some(rest) = path.strip_prefix(&redacted_prefix) {
        path = rest;
    } else if path == REDACTED_OPERATOR_REPO {
        return None;
    }
    if path.starts_with('<') {
        return None;
    }
    let mut owned = path.to_owned();
    let repo_prefix = repo_root.map(|root| format!("{}/", root.display()));
    if let Some(rest) = repo_prefix
        .as_deref()
        .and_then(|prefix| path.strip_prefix(prefix))
    {
        rest.clone_into(&mut owned);
    } else if let Some(stripped) = strip_plugin_cache_read_suffix(path) {
        owned = stripped;
    } else if path.starts_with('/') {
        return None;
    }
    if owned.starts_with('/') || owned.starts_with("../") || owned.contains("/../") || owned == ".."
    {
        return None;
    }
    in_scope_reference(&owned).then_some(owned)
}

/// Return the repository-relative suffix after a known Claude plugin-cache root.
///
/// The installed layout is `<...>/plugins/cache/larch-local/larch/<version>/`,
/// so the version component is consumed with the root.
fn strip_plugin_cache_read_suffix(path: &str) -> Option<String> {
    let parts: Vec<&str> = path.split('/').collect();
    for (index, part) in parts.iter().enumerate() {
        if *part != "plugins"
            || index + 4 >= parts.len()
            || parts[index + 1..index + 4] != ["cache", "larch-local", "larch"]
            || parts[index + 4].is_empty()
        {
            continue;
        }
        if index == 0 || parts[index - 1] == ".claude" {
            let suffix = &parts[index + 5..];
            if !suffix.is_empty() {
                return Some(suffix.join("/"));
            }
        }
        return None;
    }
    None
}

/// Return whether a repository-relative path is a runtime reference document.
fn in_scope_reference(relative: &str) -> bool {
    let parts: Vec<&str> = relative
        .split('/')
        .filter(|part| !part.is_empty() && *part != ".")
        .collect();
    if parts.is_empty() || parts.contains(&"..") {
        return false;
    }
    let Some(name) = parts.last() else {
        return false;
    };
    if python_suffix(name) != ".md" {
        return false;
    }
    if parts.len() == SHARED_REFERENCE_PARTS && parts[0] == "skills" && parts[1] == "shared" {
        return true;
    }
    parts.len() == SKILL_REFERENCE_PARTS && parts[0] == "skills" && parts[2] == "references"
}

/// Split a raw session file into records, honouring both input bounds.
fn parse_jsonl(bytes: &[u8], warnings: &mut TranscriptWarnings) -> Vec<Value> {
    let mut records = Vec::new();
    for line in universal_lines(bytes) {
        if line.is_empty() {
            continue;
        }
        if line.len() > MAX_RECORD_BYTES {
            warnings.oversized_records += 1;
            continue;
        }
        let text = match std::str::from_utf8(line) {
            Ok(text) => std::borrow::Cow::Borrowed(text),
            Err(_error) => {
                warnings.replaced_records += 1;
                String::from_utf8_lossy(line)
            }
        };
        if let Ok(value) = serde_json::from_str::<Value>(&text)
            && value.is_object()
        {
            records.push(value);
        }
    }
    records
}

/// Split on `\n`, `\r\n`, and bare `\r`, matching Python universal newlines.
fn universal_lines(bytes: &[u8]) -> Vec<&[u8]> {
    let mut lines = Vec::new();
    let mut start = 0;
    let mut index = 0;
    while index < bytes.len() {
        match bytes[index] {
            b'\n' => {
                lines.push(&bytes[start..index]);
                index += 1;
                start = index;
            }
            b'\r' => {
                lines.push(&bytes[start..index]);
                index += if bytes.get(index + 1) == Some(&b'\n') {
                    2
                } else {
                    1
                };
                start = index;
            }
            _other => index += 1,
        }
    }
    if start < bytes.len() {
        lines.push(&bytes[start..]);
    }
    lines
}

/// One compact JSON value the renderer emits, in author-declared member order.
#[derive(Debug)]
enum Json {
    Bool(bool),
    /// A number already rendered in its exact source spelling.
    Number(String),
    String(String),
    Array(Vec<Self>),
    Object(Vec<(&'static str, Self)>),
}

impl Json {
    fn string(value: &str) -> Self {
        Self::String(value.to_owned())
    }

    fn number(value: impl fmt::Display) -> Self {
        Self::Number(value.to_string())
    }

    fn write(&self, out: &mut String) {
        match self {
            Self::Bool(value) => out.push_str(if *value { "true" } else { "false" }),
            Self::Number(value) => out.push_str(value),
            Self::String(value) => write_json_string(value, out),
            Self::Array(values) => {
                out.push('[');
                for (index, value) in values.iter().enumerate() {
                    if index > 0 {
                        out.push(',');
                    }
                    value.write(out);
                }
                out.push(']');
            }
            Self::Object(members) => {
                out.push('{');
                for (index, (key, value)) in members.iter().enumerate() {
                    if index > 0 {
                        out.push(',');
                    }
                    write_json_string(key, out);
                    out.push(':');
                    value.write(out);
                }
                out.push('}');
            }
        }
    }
}

/// Escape one string so no content code point can end a document line.
///
/// This is `json.dumps(..., ensure_ascii=False)` plus explicit escapes for
/// `U+0085`, `U+2028`, and `U+2029`. Those three are line terminators to
/// Python's `str.splitlines` and to many text tools, yet JSON leaves them bare,
/// so unescaped transcript content could forge a header or turn record.
fn write_json_string(value: &str, out: &mut String) {
    out.push('"');
    for character in value.chars() {
        match character {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            '\u{8}' => out.push_str("\\b"),
            '\u{c}' => out.push_str("\\f"),
            '\u{85}' | '\u{2028}' | '\u{2029}' => {
                let _written = write!(out, "\\u{:04x}", character as u32);
            }
            other if (other as u32) < 0x20 => {
                let _written = write!(out, "\\u{:04x}", other as u32);
            }
            other => out.push(other),
        }
    }
    out.push('"');
}

/// Return whether a JSON value is truthy the way Python's `if value` is.
fn truthy(value: &Value) -> bool {
    match value {
        Value::Null => false,
        Value::Bool(value) => *value,
        Value::Number(number) => number.as_f64().is_none_or(|value| value != 0.0),
        Value::String(text) => !text.is_empty(),
        Value::Array(items) => !items.is_empty(),
        Value::Object(members) => !members.is_empty(),
    }
}

/// Return the first capture group of `pattern`, stripped, or an empty string.
fn capture(pattern: &Regex, text: &str) -> String {
    pattern
        .captures(text)
        .and_then(|captures| captures.get(1))
        .map_or_else(String::new, |group| python_strip(group.as_str()))
}

/// Return whether a character is whitespace to Python's `str.strip`.
///
/// Python treats the four ASCII information separators as space; Rust's
/// `char::is_whitespace` does not.
fn python_space(character: char) -> bool {
    character.is_whitespace() || ('\u{1c}'..='\u{1f}').contains(&character)
}

fn python_strip(text: &str) -> String {
    text.trim_matches(python_space).to_owned()
}

fn python_rstrip(text: &str) -> String {
    text.trim_end_matches(python_space).to_owned()
}

/// Return the final dotted extension the way `pathlib.PurePath.suffix` does.
fn python_suffix(name: &str) -> &str {
    match name.rfind('.') {
        Some(index) if index > 0 && index < name.len() - 1 => &name[index..],
        _other => "",
    }
}

/// Return the file name the way `pathlib.PurePath.name` does.
fn basename(path: &Path) -> String {
    path.file_name()
        .map(|name| name.to_string_lossy().into_owned())
        .unwrap_or_default()
}

fn one_line(text: &str) -> String {
    text.replace(['\n', '\r'], " ")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn plugin_cache_suffix_requires_a_version_component() {
        assert_eq!(
            strip_plugin_cache_read_suffix(
                ".claude/plugins/cache/larch-local/larch/56.2.2/skills/shared/topology.md"
            )
            .as_deref(),
            Some("skills/shared/topology.md")
        );
        assert_eq!(
            strip_plugin_cache_read_suffix("/home/a/plugins/cache/larch-local/larch/56.2.2/x.md"),
            None
        );
        assert_eq!(
            strip_plugin_cache_read_suffix("skills/shared/topology.md"),
            None
        );
    }

    #[test]
    fn in_scope_reference_pins_both_accepted_shapes() {
        assert!(in_scope_reference("skills/shared/topology.md"));
        assert!(in_scope_reference("skills/design/references/flags.md"));
        assert!(!in_scope_reference("skills/shared/nested/topology.md"));
        assert!(!in_scope_reference("skills/design/scripts/flags.md"));
        assert!(!in_scope_reference("skills/shared/.md"));
        assert!(!in_scope_reference(""));
    }

    #[test]
    fn python_suffix_matches_pathlib() {
        assert_eq!(python_suffix("a.md"), ".md");
        assert_eq!(python_suffix("..md"), ".md");
        assert_eq!(python_suffix(".md"), "");
        assert_eq!(python_suffix("md"), "");
        assert_eq!(python_suffix("a."), "");
    }

    #[test]
    fn universal_lines_split_every_python_terminator() {
        assert_eq!(
            universal_lines(b"a\nb\r\nc\rd"),
            vec![&b"a"[..], &b"b"[..], &b"c"[..], &b"d"[..]]
        );
        assert_eq!(universal_lines(b"a\n"), vec![&b"a"[..]]);
        assert!(universal_lines(b"").is_empty());
    }

    #[test]
    fn json_strings_escape_every_line_terminator() {
        let mut out = String::new();
        write_json_string("a\u{85}b\u{2028}c\u{2029}d\u{b}e", &mut out);
        assert_eq!(out, "\"a\\u0085b\\u2028c\\u2029d\\u000be\"");
    }
}
