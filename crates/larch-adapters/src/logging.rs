//! JSONL sinks and explicit human, machine, and contract output channels.

use larch_core::{Breadcrumb, JournalRecord, SafeText};
use serde_json::{Map, Value};
use std::{error::Error, fmt, io::Write, time::SystemTime};

/// Stable failures from an observability adapter.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum LoggingErrorKind {
    /// The output sink rejected a write or flush.
    Io,
    /// JSON serialization failed before a write.
    Serialize,
    /// A timestamp predates the Unix epoch or exceeds the formatter's range.
    InvalidTimestamp,
    /// A contract key was empty or contained a line break or equals sign.
    InvalidContractKey,
    /// A contract value contained a line break.
    InvalidContractValue,
}

/// An output record could not be serialized or written.
#[derive(Debug)]
pub struct LoggingError {
    kind: LoggingErrorKind,
}

impl LoggingError {
    const fn new(kind: LoggingErrorKind) -> Self {
        Self { kind }
    }

    /// Return the stable failure class.
    #[must_use]
    pub const fn kind(&self) -> LoggingErrorKind {
        self.kind
    }
}

impl fmt::Display for LoggingError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(match self.kind {
            LoggingErrorKind::Io => "observability sink write failed",
            LoggingErrorKind::Serialize => "JSONL record serialization failed",
            LoggingErrorKind::InvalidTimestamp => "record timestamp is outside the supported range",
            LoggingErrorKind::InvalidContractKey => "contract key must be a single non-empty token",
            LoggingErrorKind::InvalidContractValue => "contract value must occupy one line",
        })
    }
}

impl Error for LoggingError {}

/// Three non-interchangeable process output channels.
pub struct OutputChannels<Machine, Human, Contract> {
    machine: Machine,
    human: Human,
    contract: Contract,
}

impl<Machine, Human, Contract> OutputChannels<Machine, Human, Contract>
where
    Machine: Write,
    Human: Write,
    Contract: Write,
{
    /// Bind machine stdout, human diagnostics, and the contract stream.
    #[must_use]
    pub const fn new(machine: Machine, human: Human, contract: Contract) -> Self {
        Self {
            machine,
            human,
            contract,
        }
    }

    /// Write redacted machine output to stdout's logical channel.
    ///
    /// # Errors
    ///
    /// Returns [`LoggingErrorKind::Io`] when the machine sink rejects the line.
    pub fn machine_line(&mut self, text: impl AsRef<str>) -> Result<(), LoggingError> {
        write_safe_line(&mut self.machine, &SafeText::from_untrusted(text))
    }

    /// Write a redacted operator-facing diagnostic to stderr's logical channel.
    ///
    /// # Errors
    ///
    /// Returns [`LoggingErrorKind::Io`] when the human sink rejects the line.
    pub fn diagnostic(&mut self, text: impl AsRef<str>) -> Result<(), LoggingError> {
        write_safe_line(&mut self.human, &SafeText::diagnostic(text))
    }

    /// Write one redacted `KEY=value` row to the contract channel.
    ///
    /// # Errors
    ///
    /// Rejects keys or values that could forge a second row, and returns an I/O
    /// error if the contract sink rejects the validated row.
    pub fn contract_kv(&mut self, key: &str, value: impl AsRef<str>) -> Result<(), LoggingError> {
        if key.is_empty()
            || !key
                .bytes()
                .all(|byte| byte.is_ascii_alphanumeric() || byte == b'_')
        {
            return Err(LoggingError::new(LoggingErrorKind::InvalidContractKey));
        }
        let value = SafeText::from_untrusted(value);
        if value.as_str().contains(['\n', '\r']) {
            return Err(LoggingError::new(LoggingErrorKind::InvalidContractValue));
        }
        self.contract
            .write_all(format!("{key}={}\n", value.as_str()).as_bytes())
            .and_then(|()| self.contract.flush())
            .map_err(|_error| LoggingError::new(LoggingErrorKind::Io))
    }

    /// Return the three bound sinks, primarily for composition and tests.
    #[must_use]
    pub fn into_inner(self) -> (Machine, Human, Contract) {
        (self.machine, self.human, self.contract)
    }
}

/// Append-only writer for structured progress breadcrumbs.
pub struct BreadcrumbWriter<Writer> {
    writer: Writer,
}

impl<Writer: Write> BreadcrumbWriter<Writer> {
    /// Bind a breadcrumb JSONL sink.
    #[must_use]
    pub const fn new(writer: Writer) -> Self {
        Self { writer }
    }

    /// Append one redacted breadcrumb as a newline-terminated JSON object.
    ///
    /// # Errors
    ///
    /// Returns a typed timestamp, serialization, or sink failure.
    pub fn append(&mut self, breadcrumb: &Breadcrumb) -> Result<(), LoggingError> {
        let mut object = Map::new();
        object.insert(
            String::from("ts"),
            Value::String(format_timestamp(breadcrumb.timestamp())?),
        );
        if let Some(run_id) = breadcrumb.run_id() {
            object.insert(String::from("run_id"), Value::String(run_id.to_string()));
        }
        object.insert(
            String::from("component"),
            Value::String(String::from(breadcrumb.component())),
        );
        object.insert(
            String::from("event"),
            Value::String(String::from(breadcrumb.event())),
        );
        object.insert(
            String::from("message"),
            Value::String(String::from(breadcrumb.message().as_str())),
        );
        append_json(&mut self.writer, &Value::Object(object))
    }

    /// Return the bound sink.
    #[must_use]
    pub fn into_inner(self) -> Writer {
        self.writer
    }
}

/// Append-only writer for journal JSONL records.
pub struct JsonlJournal<Writer> {
    writer: Writer,
}

impl<Writer: Write> JsonlJournal<Writer> {
    /// Bind a journal sink.
    #[must_use]
    pub const fn new(writer: Writer) -> Self {
        Self { writer }
    }

    /// Append one redacted, newline-terminated JSON object.
    ///
    /// # Errors
    ///
    /// Returns a typed timestamp, serialization, or sink failure.
    pub fn append(&mut self, record: &JournalRecord) -> Result<(), LoggingError> {
        let mut object = Map::new();
        object.insert(
            String::from("ts"),
            Value::String(format_timestamp(record.timestamp())?),
        );
        object.insert(
            String::from("run_id"),
            Value::String(record.run_id().to_string()),
        );
        object.insert(
            String::from("event"),
            Value::String(String::from(record.event())),
        );
        for (key, value) in record.fields() {
            object.insert(
                String::from(key),
                Value::String(String::from(value.as_str())),
            );
        }
        append_json(&mut self.writer, &Value::Object(object))
    }

    /// Return the bound sink.
    #[must_use]
    pub fn into_inner(self) -> Writer {
        self.writer
    }
}

fn write_safe_line(writer: &mut impl Write, text: &SafeText) -> Result<(), LoggingError> {
    writer
        .write_all(text.as_str().as_bytes())
        .and_then(|()| {
            if text.as_str().ends_with('\n') {
                Ok(())
            } else {
                writer.write_all(b"\n")
            }
        })
        .and_then(|()| writer.flush())
        .map_err(|_error| LoggingError::new(LoggingErrorKind::Io))
}

fn append_json(writer: &mut impl Write, value: &Value) -> Result<(), LoggingError> {
    let rendered = serde_json::to_vec(&value)
        .map_err(|_error| LoggingError::new(LoggingErrorKind::Serialize))?;
    writer
        .write_all(&rendered)
        .and_then(|()| writer.write_all(b"\n"))
        .and_then(|()| writer.flush())
        .map_err(|_error| LoggingError::new(LoggingErrorKind::Io))
}

fn format_timestamp(timestamp: SystemTime) -> Result<String, LoggingError> {
    let duration = timestamp
        .duration_since(SystemTime::UNIX_EPOCH)
        .map_err(|_error| LoggingError::new(LoggingErrorKind::InvalidTimestamp))?;
    let seconds = duration.as_secs();
    let days = i64::try_from(seconds / 86_400)
        .map_err(|_error| LoggingError::new(LoggingErrorKind::InvalidTimestamp))?;
    let seconds_in_day = seconds % 86_400;
    let hour = seconds_in_day / 3_600;
    let minute = seconds_in_day % 3_600 / 60;
    let second = seconds_in_day % 60;
    let (year, month, day) = civil_date(days);
    Ok(format!(
        "{year:04}-{month:02}-{day:02}T{hour:02}:{minute:02}:{second:02}.{nanos:09}Z",
        nanos = duration.subsec_nanos()
    ))
}

fn civil_date(days_since_epoch: i64) -> (i64, i64, i64) {
    let shifted = days_since_epoch + 719_468;
    let era = shifted / 146_097;
    let day_of_era = shifted - era * 146_097;
    let year_of_era =
        (day_of_era - day_of_era / 1_460 + day_of_era / 36_524 - day_of_era / 146_096) / 365;
    let mut year = year_of_era + era * 400;
    let day_of_year = day_of_era - (365 * year_of_era + year_of_era / 4 - year_of_era / 100);
    let month_prime = (5 * day_of_year + 2) / 153;
    let day = day_of_year - (153 * month_prime + 2) / 5 + 1;
    let month = month_prime + if month_prime < 10 { 3 } else { -9 };
    year += i64::from(month <= 2);
    (year, month, day)
}

#[cfg(test)]
mod tests {
    use super::*;
    use larch_core::{RunId, SafeText};
    use std::time::Duration;

    #[test]
    fn output_channels_pin_stdout_stderr_and_contract_routing() {
        let mut channels = OutputChannels::new(Vec::new(), Vec::new(), Vec::new());
        channels
            .machine_line("RESULT=machine")
            .expect("machine should write");
        channels
            .diagnostic("human detail")
            .expect("diagnostic should write");
        channels
            .contract_kv("STATUS", "ok")
            .expect("contract should write");

        let (stdout, stderr, contract) = channels.into_inner();
        assert_eq!(stdout, b"RESULT=machine\n");
        assert_eq!(stderr, b"human detail\n");
        assert_eq!(contract, b"STATUS=ok\n");
    }

    #[test]
    fn every_channel_redacts_before_writing() {
        let token = ["ghp_", "abcdefghijklmnopqrstuvwxyz0123456789AB"].concat();
        let mut channels = OutputChannels::new(Vec::new(), Vec::new(), Vec::new());
        channels.machine_line(&token).expect("machine should write");
        channels
            .diagnostic(&token)
            .expect("diagnostic should write");
        channels
            .contract_kv("ERROR", &token)
            .expect("contract should write");

        for bytes in [channels.machine, channels.human, channels.contract] {
            let rendered = String::from_utf8(bytes).expect("output should be UTF-8");
            assert!(rendered.contains("<REDACTED-TOKEN>"));
            assert!(!rendered.contains(&token));
        }
    }

    #[test]
    fn contract_rows_reject_forged_lines_before_writing() {
        let mut channels = OutputChannels::new(Vec::new(), Vec::new(), Vec::new());

        let error = channels
            .contract_kv("STATUS", "ok\nFORGED=true")
            .expect_err("multiline value should fail");

        assert_eq!(error.kind(), LoggingErrorKind::InvalidContractValue);
        assert!(channels.contract.is_empty());
    }

    #[test]
    fn jsonl_journal_matches_the_existing_envelope_and_redacts_fields() {
        let token = ["crsr_", "1620abcdefghijklmnopqrstuvwxyz0123456789"].concat();
        let record = JournalRecord::new(
            SystemTime::UNIX_EPOCH,
            RunId::parse("run-abc").expect("run ID should parse"),
            "phase",
            [("detail", token.as_str()), ("step", "2")],
        )
        .expect("record should build");
        let mut journal = JsonlJournal::new(Vec::new());

        journal.append(&record).expect("record should append");

        let rendered = String::from_utf8(journal.into_inner()).expect("JSONL should be UTF-8");
        let parsed: Value = serde_json::from_str(rendered.trim()).expect("JSON should parse");
        assert_eq!(parsed["ts"], "1970-01-01T00:00:00.000000000Z");
        assert_eq!(parsed["run_id"], "run-abc");
        assert_eq!(parsed["event"], "phase");
        assert_eq!(parsed["step"], "2");
        assert_eq!(parsed["detail"], "<REDACTED-TOKEN>");
        assert!(!rendered.contains(&token));
        assert!(rendered.ends_with('\n'));
    }

    #[test]
    fn breadcrumb_is_structured_jsonl() {
        let breadcrumb = Breadcrumb::new(
            SystemTime::UNIX_EPOCH + Duration::from_secs(86_400),
            Some(RunId::parse("run-abc").expect("run ID should parse")),
            "ship",
            "checks",
            "running",
        )
        .expect("breadcrumb should build");
        let mut writer = BreadcrumbWriter::new(Vec::new());

        writer
            .append(&breadcrumb)
            .expect("breadcrumb should append");

        let rendered = String::from_utf8(writer.into_inner()).expect("JSONL should be UTF-8");
        let parsed: Value = serde_json::from_str(rendered.trim()).expect("JSON should parse");
        assert_eq!(parsed["ts"], "1970-01-02T00:00:00.000000000Z");
        assert_eq!(parsed["component"], "ship");
        assert_eq!(parsed["event"], "checks");
        assert_eq!(parsed["message"], "running");
    }

    #[test]
    fn safe_text_can_be_written_without_reintroducing_raw_access() {
        let safe = SafeText::from_untrusted("clean");
        let mut sink = Vec::new();

        write_safe_line(&mut sink, &safe).expect("line should write");

        assert_eq!(sink, b"clean\n");
    }
}
