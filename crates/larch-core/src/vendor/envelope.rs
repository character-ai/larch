//! Claude JSON envelope parsing into seven distinct typed outcomes.

use super::VendorParsedResult;
use serde_json::{Map, Value};

/// Distinct Claude envelope parse outcomes.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ClaudeEnvelopeStatus {
    /// Envelope parsed with a non-empty string `result`.
    Ok,
    /// Input was not valid JSON.
    MalformedJson,
    /// JSON root was not an object.
    NonObject,
    /// Envelope declared `is_error` truthy.
    IsError,
    /// Object lacked a `result` key.
    MissingResult,
    /// `result` existed but was not a string.
    NonStringResult,
    /// `result` was an empty string.
    EmptyResult,
}

impl ClaudeEnvelopeStatus {
    /// Wire token matching the Python constants.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Ok => "ok",
            Self::MalformedJson => "malformed_json",
            Self::NonObject => "non_object",
            Self::IsError => "is_error",
            Self::MissingResult => "missing_result",
            Self::NonStringResult => "non_string_result",
            Self::EmptyResult => "empty_result",
        }
    }
}

/// Parse a Claude JSON envelope into a typed postprocess outcome.
#[must_use]
pub fn parse_claude_envelope(raw: &str) -> VendorParsedResult {
    let parsed: Result<Value, _> = serde_json::from_str(raw);
    let Ok(value) = parsed else {
        return VendorParsedResult {
            status: ClaudeEnvelopeStatus::MalformedJson,
            text: String::new(),
            raw: raw.to_owned(),
            is_error: false,
            terminal_reason: String::new(),
        };
    };
    let Some(object) = value.as_object() else {
        return VendorParsedResult {
            status: ClaudeEnvelopeStatus::NonObject,
            text: String::new(),
            raw: raw.to_owned(),
            is_error: false,
            terminal_reason: String::new(),
        };
    };
    let terminal_reason = string_field(object, "terminal_reason");
    if object.get("is_error").is_some_and(json_truthy) {
        return VendorParsedResult {
            status: ClaudeEnvelopeStatus::IsError,
            text: String::new(),
            raw: raw.to_owned(),
            is_error: true,
            terminal_reason,
        };
    }
    let Some(result) = object.get("result") else {
        return VendorParsedResult {
            status: ClaudeEnvelopeStatus::MissingResult,
            text: String::new(),
            raw: raw.to_owned(),
            is_error: false,
            terminal_reason,
        };
    };
    let Some(text) = result.as_str() else {
        return VendorParsedResult {
            status: ClaudeEnvelopeStatus::NonStringResult,
            text: String::new(),
            raw: raw.to_owned(),
            is_error: false,
            terminal_reason,
        };
    };
    if text.is_empty() {
        return VendorParsedResult {
            status: ClaudeEnvelopeStatus::EmptyResult,
            text: String::new(),
            raw: raw.to_owned(),
            is_error: false,
            terminal_reason,
        };
    }
    VendorParsedResult {
        status: ClaudeEnvelopeStatus::Ok,
        text: text.to_owned(),
        raw: raw.to_owned(),
        is_error: false,
        terminal_reason,
    }
}

/// Report whether a Claude envelope is a recoverable API / connectivity failure.
///
/// Matches `is_error` envelopes with `terminal_reason=api_error` or result /
/// raw text that names DNS / reachability failures such as `ENOTFOUND`.
#[must_use]
pub fn is_transient_claude_api_error(parsed: &VendorParsedResult) -> bool {
    if parsed.status != ClaudeEnvelopeStatus::IsError && !parsed.is_error {
        return false;
    }
    if parsed.terminal_reason == "api_error" {
        return true;
    }
    claude_api_connectivity_signature(&parsed.raw)
}

fn string_field(object: &Map<String, Value>, key: &str) -> String {
    object
        .get(key)
        .and_then(Value::as_str)
        .unwrap_or("")
        .to_owned()
}

fn claude_api_connectivity_signature(text: &str) -> bool {
    let lower = text.to_ascii_lowercase();
    lower.contains("enotfound")
        || lower.contains("can't reach the api server")
        || lower.contains("cant reach the api server")
        || lower.contains("check your internet or dns")
        || lower.contains("econnreset")
        || lower.contains("etimedout")
        || lower.contains("econnrefused")
}

fn json_truthy(value: &Value) -> bool {
    match value {
        Value::Bool(flag) => *flag,
        Value::Null => false,
        Value::Number(number) => number.as_f64().is_some_and(|n| n != 0.0),
        Value::String(text) => !text.is_empty(),
        Value::Array(items) => !items.is_empty(),
        Value::Object(map) => !map.is_empty(),
    }
}
