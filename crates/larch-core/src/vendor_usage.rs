//! Codex JSONL usage-event parsing.

use serde_json::Value;
use std::fmt;

use crate::text::split_text_lines;

/// Per-run token totals summed from a Codex usage stream.
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
#[allow(
    clippy::struct_field_names,
    reason = "the shared `tokens` suffix is the vendor wire vocabulary"
)]
pub struct UsageTotals {
    input_tokens: i64,
    cached_input_tokens: i64,
    output_tokens: i64,
}

impl UsageTotals {
    /// Build one row of totals.
    #[must_use]
    pub const fn new(input_tokens: i64, cached_input_tokens: i64, output_tokens: i64) -> Self {
        Self {
            input_tokens,
            cached_input_tokens,
            output_tokens,
        }
    }

    /// Return the total input tokens, including the cached share.
    #[must_use]
    pub const fn input_tokens(self) -> i64 {
        self.input_tokens
    }

    /// Return the cached share of the input tokens.
    #[must_use]
    pub const fn cached_input_tokens(self) -> i64 {
        self.cached_input_tokens
    }

    /// Return the output tokens.
    #[must_use]
    pub const fn output_tokens(self) -> i64 {
        self.output_tokens
    }

    /// Return the input tokens that were not served from cache.
    #[must_use]
    pub const fn uncached_input_tokens(self) -> i64 {
        self.input_tokens.saturating_sub(self.cached_input_tokens)
    }

    /// Return the billed total across every bucket.
    #[must_use]
    pub const fn total_tokens(self) -> i64 {
        self.uncached_input_tokens()
            .saturating_add(self.cached_input_tokens)
            .saturating_add(self.output_tokens)
    }

    const fn plus(self, other: Self) -> Self {
        Self {
            input_tokens: self.input_tokens.saturating_add(other.input_tokens),
            cached_input_tokens: self
                .cached_input_tokens
                .saturating_add(other.cached_input_tokens),
            output_tokens: self.output_tokens.saturating_add(other.output_tokens),
        }
    }
}

/// Why a Codex usage stream could not produce totals.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum UsageParseError {
    /// The events file is absent or empty.
    EventsMissing,
    /// A candidate JSON record failed to parse.
    MalformedEvent,
    /// A row reported more cached tokens than input tokens.
    CachedExceedsInput,
    /// No selected row carried usable token counts.
    NoUsageEvents,
    /// A selected row carried a token value that is not an integer.
    ///
    /// Python raised an unlabeled `ValueError` here, and the command surfaced
    /// it through the same operator message as an empty usage stream. The
    /// distinct variant keeps the cause visible to library callers while
    /// [`UsageParseError::message`] preserves the exact command output.
    NonNumericToken,
}

impl UsageParseError {
    /// Return the exact operator-facing message for this failure.
    #[must_use]
    pub const fn message(self) -> &'static str {
        match self {
            Self::EventsMissing => "events file missing",
            Self::MalformedEvent => "malformed usage event; fail-closed",
            Self::CachedExceedsInput => "cached_tokens exceeds input_tokens; fail-closed",
            Self::NoUsageEvents | Self::NonNumericToken => "no usage events",
        }
    }
}

impl fmt::Display for UsageParseError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(self.message())
    }
}

impl std::error::Error for UsageParseError {}

/// Sum every usage-bearing record in one decoded Codex events stream.
///
/// # Errors
/// Returns [`UsageParseError`] for an empty stream, a malformed record, a
/// non-integer token value, or a row whose cached share exceeds its input.
pub fn parse_codex_usage(text: &str) -> Result<UsageTotals, UsageParseError> {
    if text.is_empty() {
        return Err(UsageParseError::EventsMissing);
    }
    let mut total = UsageTotals::default();
    let mut count = 0_usize;
    for line in split_text_lines(text) {
        let stripped = line.trim();
        if stripped.is_empty() || !(stripped.starts_with('{') || stripped.starts_with('[')) {
            // Wrapper banners and blank framing are not usage records.
            continue;
        }
        let record: Value =
            serde_json::from_str(line).map_err(|_error| UsageParseError::MalformedEvent)?;
        let Value::Object(_) = record else {
            continue;
        };
        if !is_selected(&record) {
            continue;
        }
        total = total.plus(usage_row(&record)?);
        count += 1;
    }
    if count == 0 || total.total_tokens() == 0 {
        return Err(UsageParseError::NoUsageEvents);
    }
    Ok(total)
}

fn is_selected(record: &Value) -> bool {
    has_tokenish(dig(record, &["msg", "usage"]))
        || has_tokenish(dig(record, &["usage"]))
        || (dig(record, &["type"]).and_then(Value::as_str) == Some("token_usage")
            && has_tokenish(Some(record)))
}

fn usage_row(record: &Value) -> Result<UsageTotals, UsageParseError> {
    let message_usage = dig(record, &["msg", "usage"]);
    let usage = dig(record, &["usage"]);
    // A zero-valued msg.usage envelope alongside a populated sibling usage
    // block is a Codex rollup header, not a countable row.
    let ignore_message = has_tokenish(message_usage)
        && usage.is_some_and(serde_json::Value::is_object)
        && has_tokenish(usage)
        && number(first_present(&[dig_from(message_usage, &["input_tokens"])]))? == 0
        && number(first_present(&[
            dig_from(message_usage, &["cached_input_tokens"]),
            dig_from(message_usage, &["input_tokens_details", "cached_tokens"]),
        ]))? == 0
        && number(first_present(&[dig_from(
            message_usage,
            &["output_tokens"],
        )]))?
            == 0;
    let from_message = |path: &[&str]| {
        if ignore_message {
            None
        } else {
            dig_from(message_usage, path)
        }
    };
    let input = number(first_present(&[
        from_message(&["input_tokens"]),
        dig(record, &["msg", "input_tokens"]),
        dig_from(usage, &["input_tokens"]),
        dig(record, &["input_tokens"]),
    ]))?;
    let cached = number(first_present(&[
        from_message(&["cached_input_tokens"]),
        from_message(&["input_tokens_details", "cached_tokens"]),
        dig(record, &["msg", "cached_input_tokens"]),
        dig(record, &["msg", "input_tokens_details", "cached_tokens"]),
        dig_from(usage, &["cached_input_tokens"]),
        dig_from(usage, &["input_tokens_details", "cached_tokens"]),
        dig(record, &["cached_input_tokens"]),
        dig(record, &["input_tokens_details", "cached_tokens"]),
    ]))?;
    let output = number(first_present(&[
        from_message(&["output_tokens"]),
        dig(record, &["msg", "output_tokens"]),
        dig_from(usage, &["output_tokens"]),
        dig(record, &["output_tokens"]),
    ]))?;
    if cached > input {
        return Err(UsageParseError::CachedExceedsInput);
    }
    Ok(UsageTotals::new(input, cached, output))
}

const TOKEN_PATHS: [&[&str]; 8] = [
    &["input_tokens"],
    &["cached_input_tokens"],
    &["output_tokens"],
    &["input_tokens_details", "cached_tokens"],
    &["msg", "input_tokens"],
    &["msg", "cached_input_tokens"],
    &["msg", "output_tokens"],
    &["msg", "input_tokens_details", "cached_tokens"],
];

fn has_tokenish(value: Option<&Value>) -> bool {
    let Some(Value::Object(_)) = value else {
        return false;
    };
    TOKEN_PATHS
        .iter()
        .any(|path| dig_from(value, path).is_some())
}

fn dig<'a>(value: &'a Value, path: &[&str]) -> Option<&'a Value> {
    dig_from(Some(value), path)
}

fn dig_from<'a>(value: Option<&'a Value>, path: &[&str]) -> Option<&'a Value> {
    let mut current = value?;
    for key in path {
        current = current.as_object()?.get(*key)?;
    }
    // A JSON null is indistinguishable from an absent key for these readers.
    (!current.is_null()).then_some(current)
}

fn first_present<'a>(candidates: &[Option<&'a Value>]) -> Option<&'a Value> {
    candidates.iter().copied().flatten().next()
}

fn number(value: Option<&Value>) -> Result<i64, UsageParseError> {
    let Some(value) = value else {
        return Ok(0);
    };
    match value {
        Value::Null => Ok(0),
        Value::Bool(flag) => Ok(i64::from(*flag)),
        Value::Number(number) => number
            .as_i64()
            .or_else(|| number.as_f64().and_then(truncate_float))
            .ok_or(UsageParseError::NonNumericToken),
        Value::String(text) => {
            let trimmed = text.trim();
            trimmed
                .parse::<i64>()
                .map_err(|_error| UsageParseError::NonNumericToken)
        }
        Value::Array(_) | Value::Object(_) => Err(UsageParseError::NonNumericToken),
    }
}

/// Truncate a JSON float toward zero, mirroring Python's `int(float)`.
#[allow(
    clippy::cast_possible_truncation,
    reason = "the range check above proves the truncated value fits i64"
)]
fn truncate_float(value: f64) -> Option<i64> {
    let truncated = value.trunc();
    // 2^63 is exactly representable, so this bound excludes every value that
    // would saturate rather than convert.
    (-9_223_372_036_854_775_808.0..9_223_372_036_854_775_808.0)
        .contains(&truncated)
        .then_some(truncated as i64)
}

#[cfg(test)]
mod tests {
    use super::{UsageParseError, UsageTotals, parse_codex_usage};

    #[test]
    fn nested_usage_shapes_sum_across_records() {
        let events = concat!(
            "codex banner line\n",
            r#"{"type":"event","msg":{"usage":{"input_tokens":100,"cached_input_tokens":40,"output_tokens":7}}}"#,
            "\n",
            r#"{"usage":{"input_tokens":10,"input_tokens_details":{"cached_tokens":2},"output_tokens":3}}"#,
            "\n",
        );
        let totals = parse_codex_usage(events).expect("totals");
        assert_eq!(totals, UsageTotals::new(110, 42, 10));
        assert_eq!(totals.uncached_input_tokens(), 68);
        assert_eq!(totals.total_tokens(), 120);
    }

    #[test]
    fn a_zero_message_envelope_defers_to_the_sibling_usage_block() {
        let events = concat!(
            r#"{"msg":{"usage":{"input_tokens":0,"cached_input_tokens":0,"output_tokens":0}},"#,
            r#""usage":{"input_tokens":9,"cached_input_tokens":1,"output_tokens":4}}"#,
            "\n",
        );
        assert_eq!(
            parse_codex_usage(events).expect("totals"),
            UsageTotals::new(9, 1, 4)
        );
    }

    #[test]
    fn explicit_zero_rows_still_count_toward_a_populated_stream() {
        let events = concat!(
            r#"{"type":"token_usage","input_tokens":0,"cached_input_tokens":0,"output_tokens":0}"#,
            "\n",
            r#"{"type":"token_usage","input_tokens":5,"cached_input_tokens":0,"output_tokens":1}"#,
            "\n",
        );
        assert_eq!(
            parse_codex_usage(events).expect("totals"),
            UsageTotals::new(5, 0, 1)
        );
    }

    #[test]
    fn every_fail_closed_branch_reports_its_own_cause() {
        assert_eq!(parse_codex_usage(""), Err(UsageParseError::EventsMissing));
        assert_eq!(
            parse_codex_usage("{\"usage\":{\"input_tokens\":1,\n"),
            Err(UsageParseError::MalformedEvent)
        );
        assert_eq!(
            parse_codex_usage("banner only\n"),
            Err(UsageParseError::NoUsageEvents)
        );
        assert_eq!(
            parse_codex_usage(r#"{"usage":{"input_tokens":1,"cached_input_tokens":9}}"#),
            Err(UsageParseError::CachedExceedsInput)
        );
        assert_eq!(
            parse_codex_usage(r#"{"usage":{"input_tokens":"many","output_tokens":1}}"#),
            Err(UsageParseError::NonNumericToken)
        );
        assert_eq!(
            UsageParseError::NonNumericToken.message(),
            UsageParseError::NoUsageEvents.message()
        );
    }

    #[test]
    fn the_retired_shell_harness_fixtures_keep_their_recorded_totals() {
        // Preserved verbatim from scripts/test-token-vendor-scrapers.sh, whose
        // Codex rows now need a built binary and skip without one.
        let per_turn = concat!(
            "wrapper noise\n",
            r#"{"msg":{"usage":{"input_tokens":1000,"cached_input_tokens":900,"output_tokens":50}}}"#,
            "\n",
            r#"{"usage":{"input_tokens":20,"input_tokens_details":{"cached_tokens":5},"output_tokens":7}}"#,
            "\n",
        );
        let totals = parse_codex_usage(per_turn).expect("totals");
        assert_eq!(totals.uncached_input_tokens(), 115);
        assert_eq!(totals.cached_input_tokens(), 905);
        assert_eq!(totals.output_tokens(), 57);
        assert_eq!(totals.total_tokens(), 1077);

        assert_eq!(
            parse_codex_usage("{\"msg\":{\"kind\":\"started\"}}\n"),
            Err(UsageParseError::NoUsageEvents)
        );

        let rollup = concat!(
            r#"{"msg":{"usage":{"input_tokens":1000,"cached_input_tokens":900,"output_tokens":50}}}"#,
            "\n",
            r#"{"type":"token_usage","input_tokens":7777,"cached_input_tokens":7000,"output_tokens":222}"#,
            "\n",
            r#"{"type":"task.completed","input_tokens":999,"cached_input_tokens":500,"output_tokens":111}"#,
            "\n",
        );
        let totals = parse_codex_usage(rollup).expect("totals");
        assert_eq!(totals.uncached_input_tokens(), 877);
        assert_eq!(totals.cached_input_tokens(), 7900);
        assert_eq!(totals.output_tokens(), 272);
        assert_eq!(totals.total_tokens(), 9049);
    }

    #[test]
    fn non_object_records_and_null_values_are_skipped() {
        let events = concat!(
            "[1,2,3]\n",
            r#"{"usage":{"input_tokens":null,"output_tokens":6}}"#,
            "\n",
        );
        assert_eq!(
            parse_codex_usage(events).expect("totals"),
            UsageTotals::new(0, 0, 6)
        );
    }
}
