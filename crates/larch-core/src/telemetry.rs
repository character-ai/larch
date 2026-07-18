//! Structured, redaction-owning records for breadcrumbs and JSONL journals.

use crate::{RunId, SafeText};
use std::{collections::BTreeMap, error::Error, fmt, time::SystemTime};

const NAME_MAX_BYTES: usize = 128;

/// Stable validation failures for structured observability records.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum RecordErrorKind {
    /// An event, component, or field name was empty.
    EmptyName,
    /// A name exceeded the record schema's size bound.
    NameTooLong,
    /// A name contained a byte outside the stable ASCII allowlist.
    InvalidName,
    /// A journal attempted to define the same field twice.
    DuplicateField,
    /// A custom field attempted to replace a journal envelope key.
    ReservedField,
}

/// A record was rejected before it could reach a log sink.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct RecordError {
    kind: RecordErrorKind,
}

impl RecordError {
    /// Return the stable failure class.
    #[must_use]
    pub const fn kind(self) -> RecordErrorKind {
        self.kind
    }
}

impl fmt::Display for RecordError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(match self.kind {
            RecordErrorKind::EmptyName => "record name must be non-empty",
            RecordErrorKind::NameTooLong => "record name must be at most 128 bytes",
            RecordErrorKind::InvalidName => {
                "record name must contain only ASCII letters, digits, dot, underscore, or dash"
            }
            RecordErrorKind::DuplicateField => "journal field names must be unique",
            RecordErrorKind::ReservedField => {
                "journal custom field must not replace ts, run_id, or event"
            }
        })
    }
}

impl Error for RecordError {}

/// One structured progress breadcrumb.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Breadcrumb {
    timestamp: SystemTime,
    run_id: Option<RunId>,
    component: Box<str>,
    event: Box<str>,
    message: SafeText,
}

impl Breadcrumb {
    /// Build a breadcrumb and redact its untrusted message.
    ///
    /// # Errors
    ///
    /// Returns [`RecordError`] when `component` or `event` is not a valid name.
    pub fn new(
        timestamp: SystemTime,
        run_id: Option<RunId>,
        component: &str,
        event: &str,
        message: impl AsRef<str>,
    ) -> Result<Self, RecordError> {
        validate_name(component)?;
        validate_name(event)?;
        Ok(Self {
            timestamp,
            run_id,
            component: Box::from(component),
            event: Box::from(event),
            message: SafeText::from_untrusted(message),
        })
    }

    /// Return the record timestamp.
    #[must_use]
    pub const fn timestamp(&self) -> SystemTime {
        self.timestamp
    }

    /// Return the optional run identity.
    #[must_use]
    pub const fn run_id(&self) -> Option<&RunId> {
        self.run_id.as_ref()
    }

    /// Return the emitting component.
    #[must_use]
    pub fn component(&self) -> &str {
        &self.component
    }

    /// Return the stable event name.
    #[must_use]
    pub fn event(&self) -> &str {
        &self.event
    }

    /// Return the redacted human-readable detail.
    #[must_use]
    pub const fn message(&self) -> &SafeText {
        &self.message
    }
}

/// One append-only JSONL journal record keyed by run identity.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct JournalRecord {
    timestamp: SystemTime,
    run_id: RunId,
    event: Box<str>,
    fields: BTreeMap<Box<str>, SafeText>,
}

impl JournalRecord {
    /// Build a journal record and redact every untrusted field value.
    ///
    /// # Errors
    ///
    /// Returns [`RecordError`] for an invalid event or field name, or a duplicate field.
    pub fn new<I, K, V>(
        timestamp: SystemTime,
        run_id: RunId,
        event: &str,
        fields: I,
    ) -> Result<Self, RecordError>
    where
        I: IntoIterator<Item = (K, V)>,
        K: AsRef<str>,
        V: AsRef<str>,
    {
        validate_name(event)?;
        let mut safe_fields = BTreeMap::new();
        for (key, value) in fields {
            let key = key.as_ref();
            validate_name(key)?;
            if matches!(key, "ts" | "run_id" | "event") {
                return Err(RecordError {
                    kind: RecordErrorKind::ReservedField,
                });
            }
            if safe_fields
                .insert(Box::from(key), SafeText::from_untrusted(value))
                .is_some()
            {
                return Err(RecordError {
                    kind: RecordErrorKind::DuplicateField,
                });
            }
        }
        Ok(Self {
            timestamp,
            run_id,
            event: Box::from(event),
            fields: safe_fields,
        })
    }

    /// Return the record timestamp.
    #[must_use]
    pub const fn timestamp(&self) -> SystemTime {
        self.timestamp
    }

    /// Return the run identity.
    #[must_use]
    pub const fn run_id(&self) -> &RunId {
        &self.run_id
    }

    /// Return the stable event name.
    #[must_use]
    pub fn event(&self) -> &str {
        &self.event
    }

    /// Iterate over sorted, redacted custom fields.
    pub fn fields(&self) -> impl Iterator<Item = (&str, &SafeText)> {
        self.fields.iter().map(|(key, value)| (key.as_ref(), value))
    }
}

fn validate_name(name: &str) -> Result<(), RecordError> {
    let kind = if name.is_empty() {
        Some(RecordErrorKind::EmptyName)
    } else if name.len() > NAME_MAX_BYTES {
        Some(RecordErrorKind::NameTooLong)
    } else if !name
        .bytes()
        .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'.' | b'_' | b'-'))
    {
        Some(RecordErrorKind::InvalidName)
    } else {
        None
    };
    kind.map_or(Ok(()), |kind| Err(RecordError { kind }))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn records_redact_untrusted_values_at_construction() {
        let token = ["ghp_", "abcdefghijklmnopqrstuvwxyz0123456789AB"].concat();
        let record = JournalRecord::new(
            SystemTime::UNIX_EPOCH,
            RunId::parse("run-abc").expect("run ID should parse"),
            "phase",
            [("detail", token.as_str())],
        )
        .expect("record should build");

        assert_eq!(
            record
                .fields()
                .next()
                .expect("field should exist")
                .1
                .as_str(),
            "<REDACTED-TOKEN>"
        );
    }

    #[test]
    fn duplicate_fields_fail_closed() {
        let error = JournalRecord::new(
            SystemTime::UNIX_EPOCH,
            RunId::parse("run-abc").expect("run ID should parse"),
            "phase",
            [("step", "1"), ("step", "2")],
        )
        .expect_err("duplicate should fail");

        assert_eq!(error.kind(), RecordErrorKind::DuplicateField);
    }

    #[test]
    fn hostile_names_never_enter_the_record() {
        let error = Breadcrumb::new(
            SystemTime::UNIX_EPOCH,
            None,
            "ship\nforged",
            "start",
            "message",
        )
        .expect_err("newline should fail");

        assert_eq!(error.kind(), RecordErrorKind::InvalidName);
    }
}
