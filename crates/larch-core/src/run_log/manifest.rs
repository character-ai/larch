//! Versioned run-log manifest reader.

use std::{collections::BTreeMap, error::Error, fmt, path::Path};

use serde_json::Value;

const MANIFEST_SCHEMA_VERSION: u64 = 2;

const V2_RESERVED_KEYS: &[&str] = &[
    "skill",
    "operator_cwd",
    "operator_repo_root",
    "parent_skill",
    "parent_run_id",
    "issue_number",
    "larch_version",
    "model_roster",
    "effort",
    "attempt",
    "superseded_by",
    "stalled_at_step",
    "flags",
    "pr_number",
];

const V2_CORE_KEYS: &[&str] = &[
    "status",
    "schema_version",
    "run_id",
    "steps_ran",
    "started_at",
    "updated_at",
];

const MANIFEST_IMMUTABLE_KEYS: &[&str] = &[
    "schema_version",
    "skill",
    "run_id",
    "started_at",
    "operator_cwd",
    "operator_repo_root",
    "parent_skill",
    "parent_run_id",
];

const V2_EXTRA_PROMOTABLE_RESERVED_KEYS: &[&str] =
    &["stalled_at_step", "pr_number", "issue_number"];

/// Input values for synthesizing a current v2 run-log manifest.
#[derive(Clone, Debug)]
pub struct ManifestV2Seed {
    /// Validated skill slug selected by the caller.
    pub skill: String,
    /// Validated run id selected by the caller.
    pub run_id: String,
    /// RFC3339 UTC timestamp used for both creation and update time.
    pub timestamp: String,
    /// Installed larch version recorded in the manifest.
    pub larch_version: String,
    /// Main orchestrator model recorded in the manifest.
    pub main_model: String,
    /// Requested effort level recorded in the manifest.
    pub effort: String,
    /// Initial step values.
    pub steps_ran: BTreeMap<String, Value>,
    /// Caller-supplied extension values, matching Python's final `data.update`.
    pub extra: BTreeMap<String, Value>,
}

/// A version-aware run-log manifest writer model.
///
/// This model accepts only v2 data for mutation. [`ManifestRecord`] remains
/// responsible for recognizing historical v1 manifests so readers retain their
/// compatibility contract without allowing an accidental writer downgrade.
#[derive(Clone, Debug)]
pub struct ManifestDocument {
    data: serde_json::Map<String, Value>,
}

/// A manifest update in the caller's original argument order.
pub type ManifestUpdate = (String, Value);

/// Why manifest construction or mutation could not proceed.
#[derive(Clone, Debug)]
pub enum ManifestWriteError {
    /// The shared versioned reader rejected the source bytes or shape.
    Read(ManifestReadError),
    /// The source was a recognized historical version that is read-only here.
    UnsupportedWriteVersion(ManifestFormatVersion),
    /// A caller tried to change a durable identity field.
    ImmutableField(Box<str>),
    /// Parsing unexpectedly failed after the shared reader accepted the bytes.
    ParseAfterValidation(Box<str>),
}

impl fmt::Display for ManifestWriteError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Read(error) => error.fmt(formatter),
            Self::UnsupportedWriteVersion(version) => {
                write!(
                    formatter,
                    "unsupported manifest write version: {}",
                    version.as_str()
                )
            }
            Self::ImmutableField(key) => write!(formatter, "immutable-field:{key}"),
            Self::ParseAfterValidation(detail) => {
                write!(formatter, "invalid-json-after-validation: {detail}")
            }
        }
    }
}

impl Error for ManifestWriteError {
    fn source(&self) -> Option<&(dyn Error + 'static)> {
        match self {
            Self::Read(error) => Some(error),
            Self::UnsupportedWriteVersion(_)
            | Self::ImmutableField(_)
            | Self::ParseAfterValidation(_) => None,
        }
    }
}

/// Detected historical manifest wire format.
#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub enum ManifestFormatVersion {
    /// Legacy `"version": "1"` manifests.
    V1,
    /// Current `"schema_version": 2` manifests.
    V2,
}

impl ManifestFormatVersion {
    /// Stable machine reason token for this version.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::V1 => "1",
            Self::V2 => "2",
        }
    }
}

/// Why a manifest read failed.
#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub enum ManifestReadErrorKind {
    /// The manifest path could not be read.
    Io,
    /// Bytes were not valid UTF-8 JSON.
    InvalidJson,
    /// JSON root was not an object.
    NotAnObject,
    /// Neither `schema_version` nor legacy `version` was present.
    MissingVersion,
    /// `schema_version` was present but not a supported value.
    UnknownSchemaVersion,
    /// Legacy `version` was present but not a supported value.
    UnknownVersion,
    /// Required structural fields were the wrong JSON type.
    InvalidShape,
}

/// A loud, stable-reason manifest read failure.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ManifestReadError {
    kind: ManifestReadErrorKind,
    detail: Box<str>,
}

impl ManifestReadError {
    fn new(kind: ManifestReadErrorKind, detail: impl Into<String>) -> Self {
        Self {
            kind,
            detail: detail.into().into_boxed_str(),
        }
    }

    /// Return the stable failure kind.
    #[must_use]
    pub const fn kind(&self) -> ManifestReadErrorKind {
        self.kind
    }

    /// Return a stable machine reason token.
    #[must_use]
    pub const fn reason(&self) -> &'static str {
        match self.kind {
            ManifestReadErrorKind::Io => "io-error",
            ManifestReadErrorKind::InvalidJson => "invalid-json",
            ManifestReadErrorKind::NotAnObject => "not-an-object",
            ManifestReadErrorKind::MissingVersion => "missing-version",
            ManifestReadErrorKind::UnknownSchemaVersion => "unknown-schema-version",
            ManifestReadErrorKind::UnknownVersion => "unknown-version",
            ManifestReadErrorKind::InvalidShape => "invalid-shape",
        }
    }

    /// Return the human-readable detail.
    #[must_use]
    pub fn detail(&self) -> &str {
        &self.detail
    }
}

impl fmt::Display for ManifestReadError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(formatter, "{}: {}", self.reason(), self.detail)
    }
}

impl Error for ManifestReadError {}

impl ManifestDocument {
    /// Synthesize a current v2 manifest using Python-compatible defaults.
    ///
    /// # Errors
    ///
    /// Returns [`ManifestWriteError`] when caller extensions replace the v2
    /// version marker with an unsupported shape.
    pub fn synthesize_v2(seed: ManifestV2Seed) -> Result<Self, ManifestWriteError> {
        let mut data = serde_json::Map::new();
        data.insert(
            "schema_version".to_owned(),
            Value::from(MANIFEST_SCHEMA_VERSION),
        );
        data.insert("skill".to_owned(), Value::String(seed.skill));
        data.insert("run_id".to_owned(), Value::String(seed.run_id));
        data.insert(
            "operator_cwd".to_owned(),
            Value::String("<OPERATOR_CWD>".to_owned()),
        );
        data.insert(
            "operator_repo_root".to_owned(),
            Value::String("<REPO_ROOT>".to_owned()),
        );
        data.insert("parent_skill".to_owned(), Value::Null);
        data.insert("parent_run_id".to_owned(), Value::Null);
        data.insert("issue_number".to_owned(), Value::Null);
        data.insert(
            "larch_version".to_owned(),
            Value::String(seed.larch_version),
        );
        let mut model_roster = serde_json::Map::new();
        model_roster.insert("main".to_owned(), Value::String(seed.main_model));
        data.insert("model_roster".to_owned(), Value::Object(model_roster));
        data.insert("effort".to_owned(), Value::String(seed.effort));
        data.insert(
            "started_at".to_owned(),
            Value::String(seed.timestamp.clone()),
        );
        data.insert("updated_at".to_owned(), Value::String(seed.timestamp));
        data.insert("attempt".to_owned(), Value::from(1));
        data.insert("superseded_by".to_owned(), Value::Null);
        data.insert("stalled_at_step".to_owned(), Value::Null);
        data.insert(
            "steps_ran".to_owned(),
            Value::Object(seed.steps_ran.into_iter().collect()),
        );
        data.insert("flags".to_owned(), Value::Object(serde_json::Map::new()));
        for (key, value) in seed.extra {
            data.insert(key, value);
        }
        Self::from_value(Value::Object(data))
    }

    /// Parse and validate source bytes before making them mutable.
    ///
    /// # Errors
    ///
    /// Returns [`ManifestWriteError`] when the shared reader rejects bytes or
    /// when the detected version is not v2.
    pub fn from_bytes(bytes: &[u8]) -> Result<Self, ManifestWriteError> {
        let record = ManifestRecord::parse_bytes(bytes).map_err(Self::read_error)?;
        let value = serde_json::from_slice(bytes).map_err(|error| {
            ManifestWriteError::ParseAfterValidation(error.to_string().into_boxed_str())
        })?;
        Self::from_record(&record, value)
    }

    /// Parse an already-decoded value through the shared versioned reader.
    ///
    /// # Errors
    ///
    /// Returns [`ManifestWriteError`] when the value is malformed, historical,
    /// or uses an unknown version marker.
    pub fn from_value(value: Value) -> Result<Self, ManifestWriteError> {
        let record = ManifestRecord::parse_value(value.clone()).map_err(Self::read_error)?;
        Self::from_record(&record, value)
    }

    /// Apply ordered updates and stamp a caller-provided UTC update timestamp.
    ///
    /// # Errors
    ///
    /// Returns [`ManifestWriteError::ImmutableField`] without changing this
    /// document when an immutable identity field appears in `updates`.
    pub fn apply_updates(
        &mut self,
        updates: &[ManifestUpdate],
        updated_at: impl Into<String>,
    ) -> Result<(), ManifestWriteError> {
        if let Some((key, _value)) = updates
            .iter()
            .find(|(key, _value)| MANIFEST_IMMUTABLE_KEYS.contains(&key.as_str()))
        {
            return Err(ManifestWriteError::ImmutableField(
                key.clone().into_boxed_str(),
            ));
        }

        let mut steps = self.steps_ran();
        let mut reserved = self.reserved();
        let mut extra = self.extra();
        let mut status = self
            .data
            .get("status")
            .map_or_else(|| "partial".to_owned(), python_string);

        for (key, value) in updates {
            if let Some(step) = key.strip_prefix("steps_ran.") {
                steps.insert(step.to_owned(), value.clone());
            } else if key == "steps_ran" {
                if let Value::Object(value_steps) = value {
                    for (step, step_value) in value_steps {
                        steps.insert(step.clone(), step_value.clone());
                    }
                } else {
                    extra.insert(key.clone(), value.clone());
                }
            } else if key == "status" {
                status = python_string(value);
            } else if V2_RESERVED_KEYS.contains(&key.as_str()) {
                reserved.insert(key.clone(), value.clone());
            } else {
                extra.insert(key.clone(), value.clone());
            }
        }

        let run_id = self
            .data
            .get("run_id")
            .map_or_else(String::new, python_string);
        let started_at = self
            .data
            .get("started_at")
            .map_or_else(String::new, python_string);
        let mut data = self.data.clone();
        data.remove("version");
        data.remove("created_at");
        data.insert(
            "schema_version".to_owned(),
            Value::from(MANIFEST_SCHEMA_VERSION),
        );
        data.insert("status".to_owned(), Value::String(status));
        data.insert("run_id".to_owned(), Value::String(run_id));
        data.insert(
            "steps_ran".to_owned(),
            Value::Object(steps.into_iter().collect()),
        );
        data.insert("started_at".to_owned(), Value::String(started_at));
        data.insert("updated_at".to_owned(), Value::String(updated_at.into()));
        for (key, value) in reserved {
            data.insert(key, value);
        }
        for (key, value) in extra {
            if v2_emit_extra_excluded(&key) {
                continue;
            }
            data.insert(key, value);
        }
        self.data = data;
        Ok(())
    }

    /// Render byte-compatible Python `json.dumps(..., indent=2, sort_keys=True)` output.
    #[must_use]
    pub fn canonical_json(&self) -> String {
        let mut output = String::new();
        write_canonical_json(&Value::Object(self.data.clone()), 0, &mut output);
        output.push('\n');
        output
    }

    fn from_record(record: &ManifestRecord, value: Value) -> Result<Self, ManifestWriteError> {
        if record.detected_version() != ManifestFormatVersion::V2 {
            return Err(ManifestWriteError::UnsupportedWriteVersion(
                record.detected_version(),
            ));
        }
        let Value::Object(data) = value else {
            return Err(ManifestWriteError::ParseAfterValidation(
                "shared reader accepted a non-object manifest".into(),
            ));
        };
        Ok(Self { data })
    }

    const fn read_error(error: ManifestReadError) -> ManifestWriteError {
        ManifestWriteError::Read(error)
    }

    fn steps_ran(&self) -> BTreeMap<String, Value> {
        self.data
            .get("steps_ran")
            .and_then(Value::as_object)
            .map_or_else(BTreeMap::new, |steps| {
                steps
                    .iter()
                    .map(|(key, value)| (key.clone(), value.clone()))
                    .collect()
            })
    }

    fn reserved(&self) -> BTreeMap<String, Value> {
        V2_RESERVED_KEYS
            .iter()
            .filter_map(|key| {
                self.data
                    .get(*key)
                    .map(|value| ((*key).to_owned(), value.clone()))
            })
            .collect()
    }

    fn extra(&self) -> BTreeMap<String, Value> {
        self.data
            .iter()
            .filter(|(key, _value)| {
                !V2_CORE_KEYS.contains(&key.as_str()) && !V2_RESERVED_KEYS.contains(&key.as_str())
            })
            .map(|(key, value)| (key.clone(), value.clone()))
            .collect()
    }
}

fn v2_emit_extra_excluded(key: &str) -> bool {
    V2_CORE_KEYS.contains(&key)
        || (V2_RESERVED_KEYS.contains(&key) && !V2_EXTRA_PROMOTABLE_RESERVED_KEYS.contains(&key))
}

fn python_string(value: &Value) -> String {
    match value {
        Value::String(text) => text.clone(),
        Value::Null => "None".to_owned(),
        Value::Bool(flag) => {
            if *flag {
                "True".to_owned()
            } else {
                "False".to_owned()
            }
        }
        Value::Number(number) => number.to_string(),
        Value::Array(_) | Value::Object(_) => python_repr(value),
    }
}

fn python_repr(value: &Value) -> String {
    match value {
        Value::String(text) => python_repr_string(text),
        Value::Null | Value::Bool(_) | Value::Number(_) => python_string(value),
        Value::Array(values) => format!(
            "[{}]",
            values
                .iter()
                .map(python_repr)
                .collect::<Vec<_>>()
                .join(", ")
        ),
        Value::Object(values) => format!(
            "{{{}}}",
            values
                .iter()
                .map(|(key, value)| format!("{}: {}", python_repr_string(key), python_repr(value)))
                .collect::<Vec<_>>()
                .join(", ")
        ),
    }
}

fn python_repr_string(value: &str) -> String {
    let mut output = String::from("'");
    for character in value.chars() {
        match character {
            '\\' => output.push_str("\\\\"),
            '\'' => output.push_str("\\'"),
            '\n' => output.push_str("\\n"),
            '\r' => output.push_str("\\r"),
            '\t' => output.push_str("\\t"),
            '\u{08}' => output.push_str("\\x08"),
            '\u{0C}' => output.push_str("\\x0c"),
            control if control.is_control() => {
                use std::fmt::Write as _;

                write!(output, "\\x{:02x}", control as u32)
                    .expect("writing to a String cannot fail");
            }
            other => output.push(other),
        }
    }
    output.push('\'');
    output
}

fn write_canonical_json(value: &Value, depth: usize, output: &mut String) {
    match value {
        Value::Null => output.push_str("null"),
        Value::Bool(flag) => output.push_str(if *flag { "true" } else { "false" }),
        Value::Number(number) => output.push_str(&number.to_string()),
        Value::String(text) => write_json_string(text, output),
        Value::Array(values) => write_json_array(values, depth, output),
        Value::Object(values) => write_json_object(values, depth, output),
    }
}

fn write_json_array(values: &[Value], depth: usize, output: &mut String) {
    if values.is_empty() {
        output.push_str("[]");
        return;
    }
    output.push_str("[\n");
    for (index, value) in values.iter().enumerate() {
        write_indent(depth + 1, output);
        write_canonical_json(value, depth + 1, output);
        if index + 1 != values.len() {
            output.push(',');
        }
        output.push('\n');
    }
    write_indent(depth, output);
    output.push(']');
}

fn write_json_object(values: &serde_json::Map<String, Value>, depth: usize, output: &mut String) {
    if values.is_empty() {
        output.push_str("{}");
        return;
    }
    let mut keys: Vec<&String> = values.keys().collect();
    keys.sort_unstable();
    output.push_str("{\n");
    for (index, key) in keys.iter().enumerate() {
        write_indent(depth + 1, output);
        write_json_string(key, output);
        output.push_str(": ");
        if let Some(value) = values.get(*key) {
            write_canonical_json(value, depth + 1, output);
        }
        if index + 1 != keys.len() {
            output.push(',');
        }
        output.push('\n');
    }
    write_indent(depth, output);
    output.push('}');
}

fn write_indent(depth: usize, output: &mut String) {
    output.push_str(&"  ".repeat(depth));
}

fn write_json_string(value: &str, output: &mut String) {
    output.push('"');
    for character in value.chars() {
        match character {
            '"' => output.push_str("\\\""),
            '\\' => output.push_str("\\\\"),
            '\u{08}' => output.push_str("\\b"),
            '\u{0C}' => output.push_str("\\f"),
            '\n' => output.push_str("\\n"),
            '\r' => output.push_str("\\r"),
            '\t' => output.push_str("\\t"),
            control if control.is_control() => write_json_u16_escape(
                u16::try_from(control as u32).expect("control character is within u16 range"),
                output,
            ),
            ascii if ascii.is_ascii() => output.push(ascii),
            unicode if (unicode as u32) <= 0xFFFF => {
                write_json_u16_escape(
                    u16::try_from(unicode as u32).expect("BMP character is within u16 range"),
                    output,
                );
            }
            unicode => {
                let offset = unicode as u32 - 0x1_0000;
                write_json_u16_escape(
                    u16::try_from(0xD800 + (offset >> 10))
                        .expect("Unicode high surrogate is within u16 range"),
                    output,
                );
                write_json_u16_escape(
                    u16::try_from(0xDC00 + (offset & 0x3FF))
                        .expect("Unicode low surrogate is within u16 range"),
                    output,
                );
            }
        }
    }
    output.push('"');
}

fn write_json_u16_escape(value: u16, output: &mut String) {
    const HEX: &[u8; 16] = b"0123456789abcdef";
    output.push_str("\\u");
    for shift in [12, 8, 4, 0] {
        output.push(HEX[((value >> shift) & 0xF) as usize] as char);
    }
}

/// Read-only run-log manifest record with an explicit detected version.
#[derive(Clone, Debug)]
pub struct ManifestRecord {
    detected_version: ManifestFormatVersion,
    status: String,
    run_id: String,
    steps_ran: BTreeMap<String, Value>,
    created_at: String,
    updated_at: String,
    reserved: BTreeMap<String, Value>,
    extra: BTreeMap<String, Value>,
}

impl ManifestRecord {
    /// Return the detected wire format version.
    #[must_use]
    pub const fn detected_version(&self) -> ManifestFormatVersion {
        self.detected_version
    }

    /// Return the run status.
    #[must_use]
    pub fn status(&self) -> &str {
        &self.status
    }

    /// Return the run id string from the manifest body.
    #[must_use]
    pub fn run_id(&self) -> &str {
        &self.run_id
    }

    /// Return `steps_ran`.
    #[must_use]
    pub const fn steps_ran(&self) -> &BTreeMap<String, Value> {
        &self.steps_ran
    }

    /// Return created/started timestamp.
    #[must_use]
    pub fn created_at(&self) -> &str {
        &self.created_at
    }

    /// Return updated timestamp.
    #[must_use]
    pub fn updated_at(&self) -> &str {
        &self.updated_at
    }

    /// Return reserved v2 metadata keys.
    #[must_use]
    pub const fn reserved(&self) -> &BTreeMap<String, Value> {
        &self.reserved
    }

    /// Return extension keys outside the core/reserved set.
    #[must_use]
    pub const fn extra(&self) -> &BTreeMap<String, Value> {
        &self.extra
    }

    /// Parse manifest JSON bytes, reporting the detected version.
    ///
    /// # Errors
    ///
    /// Returns [`ManifestReadError`] for truncated JSON, unknown versions, or
    /// non-object roots. Unknown shapes are never coerced silently.
    pub fn parse_bytes(bytes: &[u8]) -> Result<Self, ManifestReadError> {
        let value: Value = serde_json::from_slice(bytes).map_err(|error| {
            ManifestReadError::new(ManifestReadErrorKind::InvalidJson, error.to_string())
        })?;
        Self::parse_value(value)
    }

    /// Parse a JSON value already loaded into memory.
    ///
    /// # Errors
    ///
    /// Returns [`ManifestReadError`] for unknown or missing version markers.
    pub fn parse_value(value: Value) -> Result<Self, ManifestReadError> {
        let Value::Object(map) = value else {
            return Err(ManifestReadError::new(
                ManifestReadErrorKind::NotAnObject,
                "manifest root must be a JSON object",
            ));
        };
        let detected_version = detect_version(&map)?;
        let steps_ran = match map.get("steps_ran") {
            None => BTreeMap::new(),
            Some(Value::Object(steps)) => steps
                .iter()
                .map(|(key, value)| (key.clone(), value.clone()))
                .collect(),
            Some(_) => {
                return Err(ManifestReadError::new(
                    ManifestReadErrorKind::InvalidShape,
                    "steps_ran must be a JSON object when present",
                ));
            }
        };
        let status = string_field(&map, "status").unwrap_or_else(|| "partial".to_owned());
        let run_id = string_field(&map, "run_id").unwrap_or_default();
        match detected_version {
            ManifestFormatVersion::V2 => {
                let mut reserved = BTreeMap::new();
                for key in V2_RESERVED_KEYS {
                    if let Some(value) = map.get(*key) {
                        reserved.insert((*key).to_owned(), value.clone());
                    }
                }
                let mut extra = BTreeMap::new();
                for (key, value) in &map {
                    if V2_CORE_KEYS.contains(&key.as_str())
                        || V2_RESERVED_KEYS.contains(&key.as_str())
                    {
                        continue;
                    }
                    extra.insert(key.clone(), value.clone());
                }
                Ok(Self {
                    detected_version,
                    status,
                    run_id,
                    steps_ran,
                    created_at: string_field(&map, "started_at").unwrap_or_default(),
                    updated_at: string_field(&map, "updated_at").unwrap_or_default(),
                    reserved,
                    extra,
                })
            }
            ManifestFormatVersion::V1 => {
                let mut extra = BTreeMap::new();
                for (key, value) in &map {
                    if matches!(
                        key.as_str(),
                        "status" | "version" | "run_id" | "steps_ran" | "created_at" | "updated_at"
                    ) {
                        continue;
                    }
                    extra.insert(key.clone(), value.clone());
                }
                Ok(Self {
                    detected_version,
                    status,
                    run_id,
                    steps_ran,
                    created_at: string_field(&map, "created_at").unwrap_or_default(),
                    updated_at: string_field(&map, "updated_at").unwrap_or_default(),
                    reserved: BTreeMap::new(),
                    extra,
                })
            }
        }
    }

    /// Read and parse a manifest file.
    ///
    /// # Errors
    ///
    /// Returns [`ManifestReadErrorKind::Io`] when the path cannot be read, or
    /// parse failures from [`Self::parse_bytes`].
    pub fn read_path(path: &Path) -> Result<Self, ManifestReadError> {
        let bytes = std::fs::read(path).map_err(|error| {
            ManifestReadError::new(
                ManifestReadErrorKind::Io,
                format!("unable to read {}: {error}", path.display()),
            )
        })?;
        Self::parse_bytes(&bytes)
    }
}

fn detect_version(
    map: &serde_json::Map<String, Value>,
) -> Result<ManifestFormatVersion, ManifestReadError> {
    if let Some(schema) = map.get("schema_version") {
        return match schema {
            Value::Number(number) if number.as_u64() == Some(MANIFEST_SCHEMA_VERSION) => {
                Ok(ManifestFormatVersion::V2)
            }
            other => Err(ManifestReadError::new(
                ManifestReadErrorKind::UnknownSchemaVersion,
                format!("unsupported schema_version: {other}"),
            )),
        };
    }
    match map.get("version") {
        Some(Value::String(text)) if text == "1" => Ok(ManifestFormatVersion::V1),
        Some(Value::Number(number)) if number.as_u64() == Some(1) => Ok(ManifestFormatVersion::V1),
        Some(other) => Err(ManifestReadError::new(
            ManifestReadErrorKind::UnknownVersion,
            format!("unsupported version: {other}"),
        )),
        None => Err(ManifestReadError::new(
            ManifestReadErrorKind::MissingVersion,
            "manifest requires schema_version or version",
        )),
    }
}

fn string_field(map: &serde_json::Map<String, Value>, key: &str) -> Option<String> {
    match map.get(key)? {
        Value::String(text) => Some(text.clone()),
        Value::Number(number) => Some(number.to_string()),
        Value::Bool(flag) => Some(flag.to_string()),
        Value::Null => Some(String::new()),
        _ => None,
    }
}

#[cfg(test)]
mod tests {
    use super::{
        ManifestDocument, ManifestFormatVersion, ManifestReadErrorKind, ManifestRecord,
        ManifestUpdate, ManifestV2Seed, ManifestWriteError,
    };
    use serde_json::json;

    #[test]
    fn parses_historical_v1_and_current_v2() {
        let v1 = ManifestRecord::parse_value(json!({
            "status": "done",
            "version": "1",
            "run_id": "run-1",
            "steps_ran": {"0": "ok"},
            "created_at": "t0",
            "updated_at": "t1",
            "skill": "implement"
        }))
        .unwrap();
        assert_eq!(v1.detected_version(), ManifestFormatVersion::V1);
        assert_eq!(v1.status(), "done");
        assert_eq!(v1.extra().get("skill").unwrap(), &json!("implement"));

        let v2 = ManifestRecord::parse_value(json!({
            "schema_version": 2,
            "status": "partial",
            "run_id": "abc",
            "skill": "design",
            "started_at": "t0",
            "updated_at": "t1",
            "steps_ran": {},
            "lifecycle_schema_version": 1
        }))
        .unwrap();
        assert_eq!(v2.detected_version(), ManifestFormatVersion::V2);
        assert_eq!(v2.reserved().get("skill").unwrap(), &json!("design"));
        assert_eq!(
            v2.extra().get("lifecycle_schema_version").unwrap(),
            &json!(1)
        );
    }

    #[test]
    fn refuses_unknown_and_truncated_shapes() {
        let truncated = ManifestRecord::parse_bytes(br#"{"schema_version":2,"status":"#);
        assert_eq!(
            truncated.unwrap_err().kind(),
            ManifestReadErrorKind::InvalidJson
        );
        assert_eq!(
            ManifestRecord::parse_value(json!({"status": "partial"}))
                .unwrap_err()
                .reason(),
            "missing-version"
        );
        assert_eq!(
            ManifestRecord::parse_value(json!({"schema_version": 99, "run_id": "x"}))
                .unwrap_err()
                .reason(),
            "unknown-schema-version"
        );
        assert_eq!(
            ManifestRecord::parse_value(json!({"version": "9", "run_id": "x"}))
                .unwrap_err()
                .reason(),
            "unknown-version"
        );
    }

    #[test]
    fn synthesizes_byte_compatible_v2_json() {
        let document = ManifestDocument::synthesize_v2(ManifestV2Seed {
            skill: "implement".to_owned(),
            run_id: "run-1".to_owned(),
            timestamp: "2026-08-05T00:00:00Z".to_owned(),
            larch_version: "56.2.2".to_owned(),
            main_model: "gpt-5.6".to_owned(),
            effort: "high".to_owned(),
            steps_ran: [("step8".to_owned(), json!(true))].into_iter().collect(),
            extra: [
                ("issue_number".to_owned(), json!(8072)),
                ("z_extension".to_owned(), json!("snowman ☃")),
            ]
            .into_iter()
            .collect(),
        })
        .expect("v2 seed should synthesize");

        assert_eq!(
            document.canonical_json(),
            concat!(
                "{\n",
                "  \"attempt\": 1,\n",
                "  \"effort\": \"high\",\n",
                "  \"flags\": {},\n",
                "  \"issue_number\": 8072,\n",
                "  \"larch_version\": \"56.2.2\",\n",
                "  \"model_roster\": {\n",
                "    \"main\": \"gpt-5.6\"\n",
                "  },\n",
                "  \"operator_cwd\": \"<OPERATOR_CWD>\",\n",
                "  \"operator_repo_root\": \"<REPO_ROOT>\",\n",
                "  \"parent_run_id\": null,\n",
                "  \"parent_skill\": null,\n",
                "  \"run_id\": \"run-1\",\n",
                "  \"schema_version\": 2,\n",
                "  \"skill\": \"implement\",\n",
                "  \"stalled_at_step\": null,\n",
                "  \"started_at\": \"2026-08-05T00:00:00Z\",\n",
                "  \"steps_ran\": {\n",
                "    \"step8\": true\n",
                "  },\n",
                "  \"superseded_by\": null,\n",
                "  \"updated_at\": \"2026-08-05T00:00:00Z\",\n",
                "  \"z_extension\": \"snowman \\u2603\"\n",
                "}\n"
            )
        );
    }

    #[test]
    fn updates_v2_fields_with_python_scalar_and_extra_rules() {
        let mut document = ManifestDocument::from_value(json!({
            "schema_version": 2,
            "skill": "implement",
            "run_id": "run-1",
            "started_at": "t0",
            "status": "partial",
            "steps_ran": {"existing": false},
            "updated_at": "old",
            "operator_cwd": "cwd"
        }))
        .expect("v2 source should parse");
        let updates: Vec<ManifestUpdate> = vec![
            ("status".to_owned(), json!(true)),
            ("steps_ran.step8".to_owned(), json!(null)),
            ("pr_number".to_owned(), json!(17)),
            ("updated_at".to_owned(), json!("ignored")),
            ("z_extension".to_owned(), json!("🦀")),
        ];

        document
            .apply_updates(&updates, "t1")
            .expect("updates should apply");

        assert_eq!(
            document.canonical_json(),
            concat!(
                "{\n",
                "  \"operator_cwd\": \"cwd\",\n",
                "  \"pr_number\": 17,\n",
                "  \"run_id\": \"run-1\",\n",
                "  \"schema_version\": 2,\n",
                "  \"skill\": \"implement\",\n",
                "  \"started_at\": \"t0\",\n",
                "  \"status\": \"True\",\n",
                "  \"steps_ran\": {\n",
                "    \"existing\": false,\n",
                "    \"step8\": null\n",
                "  },\n",
                "  \"updated_at\": \"t1\",\n",
                "  \"z_extension\": \"\\ud83e\\udd80\"\n",
                "}\n"
            )
        );
    }

    #[test]
    fn refuses_immutable_historical_and_unknown_writes_without_mutation() {
        let mut document = ManifestDocument::from_value(json!({
            "schema_version": 2,
            "run_id": "run-1",
            "steps_ran": {}
        }))
        .expect("v2 source should parse");
        let before = document.canonical_json();
        let immutable = [("run_id".to_owned(), json!("other"))];

        assert!(matches!(
            document.apply_updates(&immutable, "t1"),
            Err(ManifestWriteError::ImmutableField(key)) if key.as_ref() == "run_id"
        ));
        assert_eq!(document.canonical_json(), before);
        assert!(matches!(
            ManifestDocument::from_value(json!({"version": "1", "steps_ran": {}})),
            Err(ManifestWriteError::UnsupportedWriteVersion(
                ManifestFormatVersion::V1
            ))
        ));
        assert!(matches!(
            ManifestDocument::from_value(json!({"schema_version": 99, "steps_ran": {}})),
            Err(ManifestWriteError::Read(error)) if error.reason() == "unknown-schema-version"
        ));
    }
}
