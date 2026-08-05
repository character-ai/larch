//! Versioned run-log manifest reader.

use std::{
    collections::BTreeMap,
    error::Error,
    fmt,
    path::Path,
};

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
                    if V2_CORE_KEYS.contains(&key.as_str()) || V2_RESERVED_KEYS.contains(&key.as_str())
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
    use super::{ManifestFormatVersion, ManifestReadErrorKind, ManifestRecord};
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
}
