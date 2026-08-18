//! Pure compatibility rules for the external vendor-agent launcher.

use std::{error::Error, fmt, sync::LazyLock};

use regex::Regex;
use serde_json::Value;

use crate::{OrderedJson, VendorSessionHandle, redact, truncate_utf8_bytes};

/// Maximum retained event-stream tail inspected for a Codex policy rejection.
pub const CODEX_POLICY_REJECTION_TAIL_BYTES: usize = 32 * 1024;
/// Maximum redacted policy-rejection excerpt published to a diagnostic sidecar.
pub const CODEX_POLICY_REJECTION_EXCERPT_BYTES: usize = 2 * 1024;

static CODEX_EXEC_COMMAND_FAILED_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?i-u)\bexec_command\s+failed\b").expect("static policy regex must compile")
});
static CODEX_POLICY_BLOCKED_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?i-u)blocked by policy|Rejected\(").expect("static policy regex must compile")
});
static CURSOR_AUTH_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(concat!(
        r"(?i-u)Password not found|cursor-user|cursor-access-token|",
        r"keychain[ -~]*(not found|failed)|",
        r"auth[-_ ]?error|authentication (failed|required)|",
        r"Security (process exited with code|command failed)",
    ))
    .expect("static auth regex must compile")
});
static CODEX_AUTH_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?i-u)auth[-_ ]?error|not logged in|login required|authentication (failed|required)|unauthorized|invalid api key")
        .expect("static auth regex must compile")
});
static CLAUDE_AUTH_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?i-u)auth[-_ ]?error|not logged in|login required|authentication (failed|required)|unauthorized|invalid api key|api key not found|apiKeyHelper failed|did not return a value")
        .expect("static auth regex must compile")
});
static CODEX_PROVIDER_TABLE_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^\[\[?\s*model_providers\.openai-larch-env\s*\]?\]")
        .expect("static Codex provider table regex must compile")
});
static CODEX_MODEL_PROVIDER_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r#"^model_provider\s*=\s*['\"]?openai-larch-env"#)
        .expect("static Codex model provider regex must compile")
});
static CODEX_ENV_KEY_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r#"^env_key\s*=\s*['\"]?OPENAI_API_KEY"#)
        .expect("static Codex env key regex must compile")
});
static CODEX_API_KEY_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^([A-Za-z0-9_-]+\.)*(api_key|openai_api_key)\s*=")
        .expect("static Codex API key regex must compile")
});
static CODEX_INSTRUCTIONS_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^instructions\s*=").expect("static Codex instructions regex must compile")
});

/// Classify readable launch diagnostics for an authentication retry decision.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ExternalAuthVerdict {
    /// A vendor-specific authentication signature was present.
    Auth,
    /// At least one non-empty diagnostic was readable but none matched auth.
    NonAuth,
    /// No usable diagnostic was available, or the vendor has no classifier.
    Unclassified,
}

impl ExternalAuthVerdict {
    /// Stable wire spelling shared with the legacy retry loop.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Auth => "auth",
            Self::NonAuth => "non-auth",
            Self::Unclassified => "unclassified",
        }
    }
}

/// Classify one vendor's readable diagnostic texts for authentication retry.
#[must_use]
pub fn external_auth_verdict<'a>(
    tool: &str,
    sidecars: impl IntoIterator<Item = &'a str>,
) -> ExternalAuthVerdict {
    let pattern = match tool {
        "cursor" => &*CURSOR_AUTH_RE,
        "codex" => &*CODEX_AUTH_RE,
        "claude" => &*CLAUDE_AUTH_RE,
        _ => return ExternalAuthVerdict::Unclassified,
    };
    let mut readable = false;
    for text in sidecars {
        if text.is_empty() {
            continue;
        }
        readable = true;
        if pattern.is_match(text) {
            return ExternalAuthVerdict::Auth;
        }
    }
    if readable {
        ExternalAuthVerdict::NonAuth
    } else {
        ExternalAuthVerdict::Unclassified
    }
}

/// Replace a launcher tool label's unsupported characters without changing its shape.
#[must_use]
pub fn sanitize_tool_label(value: &str) -> String {
    let sanitized: String = value
        .chars()
        .map(|character| {
            if character.is_ascii_alphanumeric() || matches!(character, '.' | '_' | '-') {
                character
            } else {
                '_'
            }
        })
        .collect();
    if sanitized.is_empty() {
        "sanitized-empty".to_owned()
    } else {
        sanitized
    }
}

/// Remove inherited credentials, larch's environment provider, and optionally
/// prior instructions from a Codex TOML configuration.
///
/// This intentionally mirrors the legacy line-oriented stripping instead of
/// parsing and reserializing TOML: opaque operator settings keep their spelling
/// and order while only the credential-bearing fragments are omitted.
#[must_use]
pub fn strip_codex_config(text: &str, strip_instructions: bool) -> String {
    let mut retained = Vec::new();
    let mut skip_block_delimiter = None;
    let mut skip_provider = false;
    for line in text.lines() {
        let stripped = line.trim();
        if let Some(delimiter) = skip_block_delimiter {
            if line.contains(delimiter) {
                skip_block_delimiter = None;
            }
            continue;
        }
        if skip_provider {
            if stripped.starts_with('[') {
                skip_provider = false;
            } else {
                continue;
            }
        }
        if CODEX_PROVIDER_TABLE_RE.is_match(stripped) {
            skip_provider = true;
            continue;
        }
        let removes_value = CODEX_MODEL_PROVIDER_RE.is_match(stripped)
            || CODEX_ENV_KEY_RE.is_match(stripped)
            || CODEX_API_KEY_RE.is_match(stripped)
            || (strip_instructions && CODEX_INSTRUCTIONS_RE.is_match(stripped));
        if removes_value {
            skip_block_delimiter = unclosed_toml_delimiter(stripped);
            continue;
        }
        retained.push(line);
    }
    if retained.is_empty() {
        String::new()
    } else {
        format!("{}\n", retained.join("\n"))
    }
}

fn unclosed_toml_delimiter(line: &str) -> Option<&'static str> {
    ["'''", "\"\"\""]
        .into_iter()
        .find(|delimiter| line.contains(delimiter) && line.matches(delimiter).count() < 2)
}

/// Why a Codex session event stream cannot produce one unambiguous handle.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum CodexSessionParseError {
    /// One line was not a valid structured JSON record.
    MalformedEvent,
    /// A `thread.started` record had no string `thread_id` field.
    MissingThreadId,
    /// A `thread_id` was not a valid Codex UUID.
    InvalidThreadId,
    /// The stream contained two identical `thread.started` records.
    DuplicateThreadId,
    /// The stream contained two different `thread.started` thread IDs.
    ConflictingThreadId,
    /// No `thread.started` record was present.
    MissingThreadStarted,
}

impl fmt::Display for CodexSessionParseError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(match self {
            Self::MalformedEvent => "malformed codex session event",
            Self::MissingThreadId => "codex thread.started event missing string thread_id",
            Self::InvalidThreadId => "codex thread.started event has invalid thread_id",
            Self::DuplicateThreadId => "duplicate codex thread.started events",
            Self::ConflictingThreadId => "conflicting codex thread.started thread_id values",
            Self::MissingThreadStarted => "codex thread.started event missing",
        })
    }
}

impl Error for CodexSessionParseError {}

/// Parse exactly one structured Codex `thread.started` record from JSONL text.
///
/// The parser deliberately never scans aggregate prose for UUID-like substrings.
/// It validates the event's declared `thread_id` through the shared session-handle
/// owner before returning it.
///
/// # Errors
///
/// Returns a stable error for malformed records, missing fields, invalid handles,
/// duplicate records, conflicting records, or a missing event.
pub fn parse_codex_session_id(text: &str) -> Result<VendorSessionHandle, CodexSessionParseError> {
    let mut found: Option<VendorSessionHandle> = None;
    for line in text.lines() {
        let stripped = line.trim();
        if stripped.is_empty() {
            continue;
        }
        if !stripped.starts_with('{') {
            return Err(CodexSessionParseError::MalformedEvent);
        }
        let value: Value = serde_json::from_str(stripped)
            .map_err(|_error| CodexSessionParseError::MalformedEvent)?;
        let Value::Object(object) = value else {
            return Err(CodexSessionParseError::MalformedEvent);
        };
        if object.get("type").and_then(Value::as_str) != Some("thread.started") {
            continue;
        }
        let thread_id = object
            .get("thread_id")
            .and_then(Value::as_str)
            .ok_or(CodexSessionParseError::MissingThreadId)?;
        let handle = VendorSessionHandle::create("codex", thread_id)
            .map_err(|_error| CodexSessionParseError::InvalidThreadId)?;
        if let Some(existing) = &found {
            return if existing.session_id() == handle.session_id() {
                Err(CodexSessionParseError::DuplicateThreadId)
            } else {
                Err(CodexSessionParseError::ConflictingThreadId)
            };
        }
        found = Some(handle);
    }
    found.ok_or(CodexSessionParseError::MissingThreadStarted)
}

/// Why a Cursor `create-chat` output cannot produce one unambiguous chat id.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum CursorCreateChatParseError {
    /// One line was not a valid structured JSON object.
    MalformedRecord,
    /// A record declared a `chatId`/`chat_id` that was not one valid string.
    InvalidChatId,
    /// The stream declared two create-chat records.
    DuplicateRecord,
    /// No create-chat record was present.
    MissingRecord,
}

impl fmt::Display for CursorCreateChatParseError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(match self {
            Self::MalformedRecord => "malformed cursor create-chat record",
            Self::InvalidChatId => "cursor create-chat record has invalid chat id",
            Self::DuplicateRecord => "duplicate cursor create-chat records",
            Self::MissingRecord => "cursor create-chat record missing",
        })
    }
}

impl Error for CursorCreateChatParseError {}

/// Return one validated Cursor chat id declared by a create-chat record, if any.
fn cursor_create_chat_id_in(line: &str) -> Result<Option<String>, CursorCreateChatParseError> {
    let value: Value =
        serde_json::from_str(line).map_err(|_error| CursorCreateChatParseError::MalformedRecord)?;
    let Value::Object(object) = value else {
        return Err(CursorCreateChatParseError::MalformedRecord);
    };
    let present: Vec<&Value> = ["chatId", "chat_id"]
        .iter()
        .filter_map(|key| object.get(*key))
        .collect();
    if present.is_empty() {
        return Ok(None);
    }
    if present.len() != 1 {
        return Err(CursorCreateChatParseError::InvalidChatId);
    }
    let id = present[0]
        .as_str()
        .ok_or(CursorCreateChatParseError::InvalidChatId)?;
    let handle = VendorSessionHandle::create("cursor", id)
        .map_err(|_error| CursorCreateChatParseError::InvalidChatId)?;
    Ok(Some(handle.session_id().to_owned()))
}

/// Parse exactly one validated Cursor chat id from create-chat JSON output.
///
/// Cursor documents this command as a structured record, not prose. Accepts its
/// two field spellings (`chatId`/`chat_id`) used by released clients, but never
/// substring-scans stdout or accepts a duplicate record: both would make a
/// resumed debate session ambiguous.
///
/// # Errors
///
/// Returns a stable error for malformed records, an invalid chat id, duplicate
/// records, or a missing record.
pub fn parse_cursor_create_chat_id(text: &str) -> Result<String, CursorCreateChatParseError> {
    let mut found: Option<String> = None;
    for line in text.lines() {
        if line.trim().is_empty() {
            continue;
        }
        let Some(candidate) = cursor_create_chat_id_in(line)? else {
            continue;
        };
        if found.is_some() {
            return Err(CursorCreateChatParseError::DuplicateRecord);
        }
        found = Some(candidate);
    }
    found.ok_or(CursorCreateChatParseError::MissingRecord)
}

/// Return a bounded redacted excerpt only when a genuine Codex policy rejection is present.
///
/// Successful command output carried in `aggregated_output` is removed from the
/// scan before matching. That prevents a model's quoted successful output from
/// turning into a false policy rejection.
#[must_use]
pub fn codex_policy_rejection_excerpt(text: &str) -> String {
    let bounded = codex_policy_scan_tail(text);
    if bounded.is_empty() {
        return String::new();
    }
    let scanned = sanitize_codex_events_for_policy_scan(bounded);
    if !CODEX_EXEC_COMMAND_FAILED_RE.is_match(&scanned)
        || !CODEX_POLICY_BLOCKED_RE.is_match(&scanned)
    {
        return String::new();
    }
    let lines: Vec<&str> = scanned
        .lines()
        .filter(|line| {
            CODEX_EXEC_COMMAND_FAILED_RE.is_match(line)
                || CODEX_POLICY_BLOCKED_RE.is_match(line)
                || line.contains("CreateProcess")
        })
        .collect();
    let excerpt = if lines.is_empty() {
        tail_utf8(&scanned, CODEX_POLICY_REJECTION_EXCERPT_BYTES).to_owned()
    } else {
        lines[lines.len().saturating_sub(8)..].join("\n")
    };
    truncate_utf8_bytes(
        redact(&excerpt).text(),
        CODEX_POLICY_REJECTION_EXCERPT_BYTES,
    )
    .to_owned()
}

fn codex_policy_scan_tail(text: &str) -> &str {
    if text.len() <= CODEX_POLICY_REJECTION_TAIL_BYTES {
        return text;
    }
    let bounded = tail_utf8(text, CODEX_POLICY_REJECTION_TAIL_BYTES);
    let start = text.len() - bounded.len();
    if text.as_bytes().get(start.saturating_sub(1)) == Some(&b'\n') {
        return bounded;
    }
    bounded.split_once('\n').map_or("", |(_partial, rest)| rest)
}

fn tail_utf8(text: &str, byte_cap: usize) -> &str {
    if text.len() <= byte_cap {
        return text;
    }
    let mut start = text.len().saturating_sub(byte_cap);
    while start < text.len() && !text.is_char_boundary(start) {
        start += 1;
    }
    &text[start..]
}

fn sanitize_codex_events_for_policy_scan(text: &str) -> String {
    let mut sanitized = String::with_capacity(text.len());
    for line in text.split_inclusive('\n') {
        let content = line.trim_end_matches(['\r', '\n']);
        let terminator = &line[content.len()..];
        if content.trim().is_empty() {
            sanitized.push_str(line);
            continue;
        }
        let Ok(mut value) = serde_json::from_str::<OrderedJson>(content) else {
            sanitized.push_str(line);
            continue;
        };
        strip_gated_aggregated_output(&mut value);
        match python_json_dumps(&value) {
            Ok(rendered) => {
                sanitized.push_str(&rendered);
                sanitized.push_str(terminator);
            }
            Err(_error) => sanitized.push_str(line),
        }
    }
    sanitized
}

fn strip_gated_aggregated_output(node: &mut OrderedJson) {
    match node {
        OrderedJson::Object(object) => {
            let remove = object
                .iter()
                .find(|(key, _value)| key == "exit_code")
                .zip(
                    object
                        .iter()
                        .find(|(key, _value)| key == "aggregated_output"),
                )
                .is_some_and(|(exit_code, aggregate)| {
                    json_equals_zero(&exit_code.1)
                        || (matches!(exit_code.1, OrderedJson::Null)
                            && json_is_falsey(&aggregate.1))
                });
            if remove {
                object.retain(|(key, _value)| key != "aggregated_output");
            }
            for (_key, value) in object {
                strip_gated_aggregated_output(value);
            }
        }
        OrderedJson::Array(items) => {
            for item in items {
                strip_gated_aggregated_output(item);
            }
        }
        OrderedJson::Null
        | OrderedJson::Bool(_)
        | OrderedJson::Number(_)
        | OrderedJson::String(_) => {}
    }
}

fn json_equals_zero(value: &OrderedJson) -> bool {
    matches!(value, OrderedJson::Bool(false))
        || matches!(value, OrderedJson::Number(number) if number.as_f64() == Some(0.0))
}

fn json_is_falsey(value: &OrderedJson) -> bool {
    match value {
        OrderedJson::Null => true,
        OrderedJson::Bool(value) => !value,
        OrderedJson::Number(value) => value.as_f64() == Some(0.0),
        OrderedJson::String(value) => value.is_empty(),
        OrderedJson::Array(values) => values.is_empty(),
        OrderedJson::Object(values) => values.is_empty(),
    }
}

/// Render ordered JSON with the spacing used by Python's default `json.dumps`.
///
/// # Errors
///
/// Returns a serialization error when an embedded JSON string cannot render.
pub fn python_json_dumps(value: &OrderedJson) -> Result<String, serde_json::Error> {
    let mut rendered = String::new();
    write_python_json(value, &mut rendered)?;
    Ok(rendered)
}

fn write_python_json(value: &OrderedJson, rendered: &mut String) -> Result<(), serde_json::Error> {
    match value {
        OrderedJson::Null => rendered.push_str("null"),
        OrderedJson::Bool(value) => rendered.push_str(if *value { "true" } else { "false" }),
        OrderedJson::Number(value) => rendered.push_str(&value.to_string()),
        OrderedJson::String(value) => rendered.push_str(&serde_json::to_string(value)?),
        OrderedJson::Array(values) => {
            rendered.push('[');
            for (index, value) in values.iter().enumerate() {
                if index > 0 {
                    rendered.push_str(", ");
                }
                write_python_json(value, rendered)?;
            }
            rendered.push(']');
        }
        OrderedJson::Object(values) => {
            rendered.push('{');
            for (index, (key, value)) in values.iter().enumerate() {
                if index > 0 {
                    rendered.push_str(", ");
                }
                rendered.push_str(&serde_json::to_string(key)?);
                rendered.push_str(": ");
                write_python_json(value, rendered)?;
            }
            rendered.push('}');
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::{
        CODEX_POLICY_REJECTION_TAIL_BYTES, CodexSessionParseError, ExternalAuthVerdict,
        codex_policy_rejection_excerpt, external_auth_verdict, parse_codex_session_id,
        sanitize_codex_events_for_policy_scan, sanitize_tool_label, strip_codex_config,
    };

    #[test]
    fn policy_scan_ignores_successful_aggregated_output_and_keeps_real_failures() {
        let benign = r#"{"item":{"exit_code":0,"aggregated_output":"exec_command failed Rejected(blocked by policy)"}}"#;
        assert!(codex_policy_rejection_excerpt(benign).is_empty());
        let genuine =
            "error=exec_command failed for bash: CreateProcess Rejected(blocked by policy)";
        assert!(
            codex_policy_rejection_excerpt(&format!("{benign}\n{genuine}\n")).contains("Rejected")
        );
        let long = format!(
            "{}\n{genuine}\n",
            "x".repeat(CODEX_POLICY_REJECTION_TAIL_BYTES + 128)
        );
        assert!(codex_policy_rejection_excerpt(&long).contains("exec_command failed"));
    }

    #[test]
    fn policy_scan_uses_python_json_spacing_order_and_falsey_gates() {
        let source = r#"{"z":1,"item":{"exit_code":null,"aggregated_output":[],"value":2}}"#;
        assert_eq!(
            sanitize_codex_events_for_policy_scan(source),
            r#"{"z": 1, "item": {"exit_code": null, "value": 2}}"#
        );
        let float_zero = r#"{"item":{"exit_code":0.0,"aggregated_output":"quoted policy text"}}"#;
        assert_eq!(
            sanitize_codex_events_for_policy_scan(float_zero),
            r#"{"item": {"exit_code": 0.0}}"#
        );
        let duplicate_and_large = r#"{"z":1,"z":2,"large":123456789012345678901234567890,"item":{"exit_code":0,"aggregated_output":"quoted policy text"}}"#;
        assert_eq!(
            sanitize_codex_events_for_policy_scan(duplicate_and_large),
            r#"{"z": 2, "large": 123456789012345678901234567890, "item": {"exit_code": 0}}"#
        );
    }

    #[test]
    fn session_parser_requires_one_valid_declared_thread_id() {
        let id = "123e4567-e89b-12d3-a456-426614174000";
        let handle = parse_codex_session_id(&format!(
            r#"{{"type":"thread.started","thread_id":"{id}"}}"#
        ))
        .expect("valid session");
        assert_eq!(handle.session_id(), id);
        assert_eq!(
            parse_codex_session_id("").expect_err("missing event"),
            CodexSessionParseError::MissingThreadStarted
        );
        assert_eq!(
            parse_codex_session_id(r#"{"type":"thread.started","thread_id":"nope"}"#)
                .expect_err("invalid id"),
            CodexSessionParseError::InvalidThreadId
        );
    }

    #[test]
    fn auth_labels_match_the_legacy_contract() {
        assert_eq!(
            external_auth_verdict("codex", ["login required"]),
            ExternalAuthVerdict::Auth
        );
        assert_eq!(
            external_auth_verdict("codex", ["ordinary failure"]),
            ExternalAuthVerdict::NonAuth
        );
        assert_eq!(
            external_auth_verdict("codex", [""]),
            ExternalAuthVerdict::Unclassified
        );
        assert_eq!(sanitize_tool_label("codex/β"), "codex__");
    }

    #[test]
    fn strips_credentials_and_replaces_prior_instruction_blocks() {
        let source = "model = \"kept\"\napi_key = \"secret\"\ninstructions = '''\nold\n'''\n[model_providers.openai-larch-env]\nenv_key = \"OPENAI_API_KEY\"\n[other]\nvalue = 1\n";
        assert_eq!(
            strip_codex_config(source, true),
            "model = \"kept\"\n[other]\nvalue = 1\n"
        );
    }
}
