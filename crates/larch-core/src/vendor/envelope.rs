//! Claude JSON envelope parsing into seven distinct typed outcomes.

use super::VendorParsedResult;
use serde_json::Value;

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
        };
    };
    let Some(object) = value.as_object() else {
        return VendorParsedResult {
            status: ClaudeEnvelopeStatus::NonObject,
            text: String::new(),
            raw: raw.to_owned(),
            is_error: false,
        };
    };
    if object
        .get("is_error")
        .is_some_and(json_truthy)
    {
        return VendorParsedResult {
            status: ClaudeEnvelopeStatus::IsError,
            text: String::new(),
            raw: raw.to_owned(),
            is_error: true,
        };
    }
    let Some(result) = object.get("result") else {
        return VendorParsedResult {
            status: ClaudeEnvelopeStatus::MissingResult,
            text: String::new(),
            raw: raw.to_owned(),
            is_error: false,
        };
    };
    let Some(text) = result.as_str() else {
        return VendorParsedResult {
            status: ClaudeEnvelopeStatus::NonStringResult,
            text: String::new(),
            raw: raw.to_owned(),
            is_error: false,
        };
    };
    if text.is_empty() {
        return VendorParsedResult {
            status: ClaudeEnvelopeStatus::EmptyResult,
            text: String::new(),
            raw: raw.to_owned(),
            is_error: false,
        };
    }
    VendorParsedResult {
        status: ClaudeEnvelopeStatus::Ok,
        text: text.to_owned(),
        raw: raw.to_owned(),
        is_error: false,
    }
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