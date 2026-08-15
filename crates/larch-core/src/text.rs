//! Text framing shared by the ported Python line readers.

use num_bigint::BigInt;
use serde_json::Value;
use std::{borrow::Cow, collections::BTreeSet, fmt::Write as _};
#[rustfmt::skip]
const PYTHON_DECIMAL_ZEROS: [u32; 66] = [
    0x30, 0x660, 0x6F0, 0x7C0, 0x966, 0x9E6, 0xA66, 0xAE6, 0xB66, 0xBE6,
    0xC66, 0xCE6, 0xD66, 0xDE6, 0xE50, 0xED0, 0xF20, 0x1040, 0x1090, 0x17E0,
    0x1810, 0x1946, 0x19D0, 0x1A80, 0x1A90, 0x1B50, 0x1BB0, 0x1C40, 0x1C50, 0xA620,
    0xA8D0, 0xA900, 0xA9D0, 0xA9F0, 0xAA50, 0xABF0, 0xFF10, 0x104A0, 0x10D30, 0x11066,
    0x110F0, 0x11136, 0x111D0, 0x112F0, 0x11450, 0x114D0, 0x11650, 0x116C0, 0x11730, 0x118E0,
    0x11950, 0x11C50, 0x11D50, 0x11DA0, 0x16A60, 0x16AC0, 0x16B50, 0x1D7CE, 0x1D7D8, 0x1D7E2,
    0x1D7EC, 0x1D7F6, 0x1E140, 0x1E2F0, 0x1E950, 0x1FBF0,
];
fn python_decimal_digit(character: char) -> Option<u32> {
    let code = character as u32;
    PYTHON_DECIMAL_ZEROS
        .iter()
        .find_map(|zero| (code >= *zero && code < *zero + 10).then(|| code - *zero))
}

/// Escape scalars Python's `ensure_ascii=True` encoder does in serialized JSON.
///
/// Python's JSON output uses ASCII `\\u` escapes, including UTF-16 surrogate
/// pairs for supplementary-plane characters. Keep that post-serialization
/// compatibility transform in one shared owner.
#[must_use]
pub fn ensure_ascii_json(text: &str) -> String {
    let mut output = String::with_capacity(text.len());
    for character in text.chars() {
        // Python's `ensure_ascii=True` also escapes DEL, even though it is an
        // ASCII scalar. `serde_json` leaves it literal, so preserve the Python
        // wire format for callers that start with a Rust-serialized document.
        if character.is_ascii() && character != '\u{007f}' {
            output.push(character);
            continue;
        }
        let mut units = [0; 2];
        for unit in character.encode_utf16(&mut units) {
            write!(output, "\\u{unit:04x}").expect("writing to a String cannot fail");
        }
    }
    output
}

/// Split text on every boundary Python's `str.splitlines` recognizes.
///
/// The ported readers all consumed `str.splitlines()`, which breaks on
/// vertical tab, form feed, the C1 information separators, NEL, and the two
/// Unicode line and paragraph separators in addition to LF and CRLF. Splitting
/// on LF alone would merge records that Python treated as separate, so the
/// migrated usage parser and diagnostic tails share this one owner.
///
/// Parse an unsigned decimal integer, rejecting every other spelling.
///
/// Only all-ASCII-digit input that fits a `u64` parses: no sign, no whitespace,
/// and no separators. Python's `str.isdigit()` also admitted non-ASCII digits
/// and unbounded magnitudes, both of which failed downstream; the migrated
/// readers narrow to this one owner instead.
#[must_use]
pub fn unsigned_integer(value: &str) -> Option<u64> {
    if value.is_empty() || !value.bytes().all(|byte| byte.is_ascii_digit()) {
        return None;
    }
    value.parse::<u64>().ok()
}

/// Parse a positive decimal integer, rejecting every other spelling.
///
/// [`unsigned_integer`] without zero. Shared by the issue-number and interval
/// readers.
#[must_use]
pub fn positive_integer(value: &str) -> Option<u64> {
    unsigned_integer(value).filter(|parsed| *parsed > 0)
}

/// Parse Python's signed decimal spelling with its default 4,300-digit guard.
#[must_use]
pub fn python_bigint(value: &str) -> Option<BigInt> {
    let trimmed = trim_python_whitespace(value);
    let (negative, digits) = trimmed.strip_prefix('-').map_or_else(
        || (false, trimmed.strip_prefix('+').unwrap_or(trimmed)),
        |rest| (true, rest),
    );
    if digits.is_empty() || digits.starts_with('_') || digits.ends_with('_') {
        return None;
    }
    let mut previous_underscore = false;
    let mut cleaned = String::with_capacity(digits.len());
    for character in digits.chars() {
        if character == '_' {
            if previous_underscore {
                return None;
            }
            previous_underscore = true;
            continue;
        }
        let digit = python_decimal_digit(character)?;
        previous_underscore = false;
        cleaned.push(char::from_digit(digit, 10)?);
    }
    if cleaned.len() > 4_300 {
        return None;
    }
    let magnitude = BigInt::parse_bytes(cleaned.as_bytes(), 10)?;
    Some(if negative { -magnitude } else { magnitude })
}

/// Parse Python's decimal float spelling, including Unicode digits and underscores.
#[must_use]
#[rustfmt::skip]
pub fn python_float(value: &str) -> Option<f64> {
    let mut characters = trim_python_whitespace(value).chars().peekable();
    let mut normalized = String::new();
    let mut previous_digit = false;
    while let Some(character) = characters.next() {
        if character == '_' {
            if !previous_digit || characters.peek().copied().and_then(python_decimal_digit).is_none() {
                return None;
            }
            previous_digit = false;
        } else if let Some(digit) = python_decimal_digit(character) {
            normalized.push(char::from_digit(digit, 10)?);
            previous_digit = true;
        } else {
            normalized.push(character);
            previous_digit = false;
        }
    }
    normalized.parse().ok()
}

/// Parse a signed decimal integer the way Python's `int(str)` does, within `i64`.
///
/// Python strips surrounding whitespace, accepts one leading sign, and allows
/// single underscores between digits. It has no magnitude bound; this owner
/// refuses non-ASCII or out-of-range values rather than silently broadening
/// existing callers' accepted input.
#[must_use]
pub fn python_int(value: &str) -> Option<i64> {
    let trimmed = trim_python_whitespace(value);
    let (negative, digits) = trimmed.strip_prefix('-').map_or_else(
        || (false, trimmed.strip_prefix('+').unwrap_or(trimmed)),
        |rest| (true, rest),
    );
    if digits.is_empty() || digits.starts_with('_') || digits.ends_with('_') {
        return None;
    }
    let mut previous_underscore = false;
    let mut cleaned = String::with_capacity(digits.len());
    for character in digits.chars() {
        if character == '_' {
            if previous_underscore {
                return None;
            }
            previous_underscore = true;
            continue;
        }
        if !character.is_ascii_digit() {
            return None;
        }
        previous_underscore = false;
        cleaned.push(character);
    }
    let magnitude = cleaned.parse::<i128>().ok()?;
    i64::try_from(if negative { -magnitude } else { magnitude }).ok()
}

/// Report whether `value` spells a positive decimal with no bound.
///
/// Python's `str.isdecimal()` guards accepted non-ASCII digits and magnitudes
/// no integer type holds. This owner narrows the digits to ASCII and keeps the
/// magnitude unbounded, so a value too large to parse is still refused for the
/// same reason Python refused it rather than for a different one.
#[must_use]
pub fn is_positive_decimal(value: &str) -> bool {
    !value.is_empty()
        && value.bytes().all(|byte| byte.is_ascii_digit())
        && value.bytes().any(|byte| byte != b'0')
}

/// A trailing boundary does not produce a final empty element.
#[must_use]
pub fn split_text_lines(text: &str) -> Vec<&str> {
    let mut lines = Vec::new();
    let mut start = 0;
    let mut index = 0;
    let bytes = text.as_bytes();
    while index < text.len() {
        let Some(character) = text[index..].chars().next() else {
            break;
        };
        let width = character.len_utf8();
        if !is_line_boundary(character) {
            index += width;
            continue;
        }
        lines.push(&text[start..index]);
        // A CRLF pair frames one record, so the LF never opens an empty line.
        index += if character == '\r' && bytes.get(index + 1) == Some(&b'\n') {
            2
        } else {
            width
        };
        start = index;
    }
    if start < text.len() {
        lines.push(&text[start..]);
    }
    lines
}

/// Split text into lines that keep their terminators.
///
/// Ports Python `str.splitlines(keepends=True)`: boundaries match
/// [`split_text_lines`], and each slice carries the terminator that closed it,
/// so concatenating the result reproduces `text` byte for byte. Both Markdown
/// block engines rebuild bodies by splicing these slices, so the round trip has
/// to be lossless.
#[must_use]
pub fn split_lines_keep_ends(text: &str) -> Vec<&str> {
    let mut lines = Vec::new();
    let mut start = 0;
    let mut index = 0;
    let bytes = text.as_bytes();
    while index < text.len() {
        let Some(character) = text[index..].chars().next() else {
            break;
        };
        let width = character.len_utf8();
        if !is_line_boundary(character) {
            index += width;
            continue;
        }
        // A CRLF pair terminates one line, so the LF never opens an empty line.
        index += if character == '\r' && bytes.get(index + 1) == Some(&b'\n') {
            2
        } else {
            width
        };
        lines.push(&text[start..index]);
        start = index;
    }
    if start < text.len() {
        lines.push(&text[start..]);
    }
    lines
}

/// Return the indices of lines strictly inside balanced Markdown code fences.
///
/// Ports Python `larch.design.plan_grammar.balanced_fence_line_indices` as the
/// one owner every fence-aware reader shares. An unmatched opener fences
/// nothing, so content after a truncated fence stays visible. A closer repeats
/// the opener's marker character, is at least as long, and carries only
/// whitespace after it.
#[must_use]
pub fn balanced_fence_line_indices<S: AsRef<str>>(lines: &[S]) -> BTreeSet<usize> {
    let mut fenced = BTreeSet::new();
    let mut stack: Vec<(usize, char, usize)> = Vec::new();
    for (index, line) in lines.iter().enumerate() {
        let Some((marker, length, suffix)) = fence_marker(trim_python_whitespace(line.as_ref()))
        else {
            continue;
        };
        let Some(&(open_index, open_marker, open_length)) = stack.last() else {
            stack.push((index, marker, length));
            continue;
        };
        if marker == open_marker
            && length >= open_length
            && trim_python_whitespace(suffix).is_empty()
        {
            let _ = stack.pop();
            fenced.extend((open_index + 1)..index);
        }
    }
    fenced
}

/// Match the Python fence-marker pattern against an already-stripped line: at
/// least three backticks or tildes, then an arbitrary suffix.
#[must_use]
pub fn fence_marker(line: &str) -> Option<(char, usize, &str)> {
    let marker = line.chars().next()?;
    if marker != '`' && marker != '~' {
        return None;
    }
    let length = line
        .chars()
        .take_while(|character| *character == marker)
        .count();
    if length < FENCE_MIN_LENGTH {
        return None;
    }
    Some((marker, length, &line[length..]))
}

const FENCE_MIN_LENGTH: usize = 3;

/// Return whether Python's `str.strip()` would remove this character.
///
/// Python treats the four information separators as whitespace; Rust's
/// `char::is_whitespace` does not, so they are added back here. The ported
/// readers that mirror a Python `strip` or `lstrip` share this one predicate.
#[must_use]
pub const fn is_python_whitespace(character: char) -> bool {
    character.is_whitespace() || matches!(character, '\u{1c}'..='\u{1f}')
}

/// Trim exactly the code points Python's `str.strip()` removes.
#[must_use]
pub fn trim_python_whitespace(text: &str) -> &str {
    text.trim_matches(is_python_whitespace)
}

/// Translate line endings the way Python's default text reader does.
///
/// `Path.read_text` opens in universal-newline mode, so every reader ported
/// from it sees `\n` even when the file holds `\r\n` or a bare `\r`. Readers
/// ported from `larch.io.read_text` do not, because that owner opens with
/// `newline=""`. Which translation applies is therefore a property of the
/// reader, not of the grammar, so the OOS text functions take whatever their
/// caller read and this owner spells out the choice.
#[must_use]
pub fn universal_newlines(text: &str) -> Cow<'_, str> {
    if text.contains('\r') {
        Cow::Owned(text.replace("\r\n", "\n").replace('\r', "\n"))
    } else {
        Cow::Borrowed(text)
    }
}

/// Extensions the reviewer file-reference grammar accepts without a line hint.
const FILE_REFERENCE_LONG_EXTENSIONS: &str = "cc|cfg|cjs|cpp|css|csv|cs|dart|gradle|groovy|go|html|htm|hpp|java|json|jsx|js|kt|lua|mjs|mk|mm|md|php|pl|proto|py|rb|rs|sass|scala|scss|sh|sql|swift|toml|tsx|tsv|ts|vue|xml|yaml|yml";
/// Extensions ambiguous enough to need a path separator or a line hint.
const FILE_REFERENCE_SHORT_EXTENSIONS: &str = "lock|env|txt|c|h|m|r";

/// Return one byte-frozen reviewer file-reference regex by its public name.
///
/// The command boundary exposes these source strings to shell callers, so this
/// projection deliberately uses the historical case-sensitive spellings.
#[must_use]
pub fn file_line_regex(name: &str) -> Option<String> {
    let [long, short_path, short_line, extensionless] = file_reference_alternatives(false);
    match name {
        "long-re" => Some(long),
        "short-path-re" => Some(short_path),
        "short-line-re" => Some(short_line),
        "extensionless-re" => Some(extensionless),
        "any-re" => Some(format!("{long}|{short_path}|{short_line}")),
        "long-exts" => Some(FILE_REFERENCE_LONG_EXTENSIONS.to_owned()),
        "short-exts" => Some(FILE_REFERENCE_SHORT_EXTENSIONS.to_owned()),
        _ => None,
    }
}

/// The four alternatives of the shared reviewer file-reference grammar.
///
/// Ports Python `larch.calibration.voting.FILE_LINE_REGEXES` as one owner, so the
/// evidence reader and the OOS conflict model cannot drift apart on which
/// prose counts as a file reference. The alternatives are returned as source
/// strings because the two readers compose them differently: evidence matching
/// wants them as separate expressions, and conflict detection wants one.
///
/// `fold_extension_case` is the only difference between the two callers. The
/// evidence reader accepts `.PY` because it is scoring similarity, while the
/// conflict model keeps Python's case-sensitive spelling because a spurious
/// match there would invent a dependency edge between unrelated items. Every
/// alternative keeps its capture-group count in both spellings.
#[must_use]
pub fn file_reference_alternatives(fold_extension_case: bool) -> [String; 4] {
    let group = |values: &str| {
        if fold_extension_case {
            format!("((?i-u:{values}))")
        } else {
            format!("({values})")
        }
    };
    let long = group(FILE_REFERENCE_LONG_EXTENSIONS);
    let short = group(FILE_REFERENCE_SHORT_EXTENSIONS);
    [
        format!(
            r"(^|[^A-Za-z0-9])\.?[A-Za-z_][A-Za-z0-9_./-]*\.{long}(:[0-9]+(-[0-9]+)?)?($|[^A-Za-z0-9_:/-])"
        ),
        format!(
            r"(^|[^A-Za-z0-9])\.?[A-Za-z_][A-Za-z0-9_./-]*[/_-][A-Za-z0-9_./-]*\.{short}(:[0-9]+(-[0-9]+)?)?($|[^A-Za-z0-9_:/-])"
        ),
        format!(
            r"(^|[^A-Za-z0-9])\.?[A-Za-z_][A-Za-z0-9_./-]*\.{short}:[0-9]+(-[0-9]+)?($|[^A-Za-z0-9_:/-])"
        ),
        format!(
            r"(^|[^A-Za-z0-9_]){}(:[0-9]+(-[0-9]+)?)?",
            group("Makefile|Dockerfile|GNUmakefile")
        ),
    ]
}

const fn is_line_boundary(character: char) -> bool {
    matches!(
        character,
        '\n' | '\r'
            | '\u{0b}'
            | '\u{0c}'
            | '\u{1c}'
            | '\u{1d}'
            | '\u{1e}'
            | '\u{85}'
            | '\u{2028}'
            | '\u{2029}'
    )
}

/// Truncate text to at most `cap` bytes without splitting a UTF-8 sequence.
#[must_use]
pub fn truncate_utf8_bytes(text: &str, cap: usize) -> &str {
    if text.len() <= cap {
        return text;
    }
    let mut end = cap;
    while end > 0 && !text.is_char_boundary(end) {
        end -= 1;
    }
    &text[..end]
}

/// Return the last `count` lines, or every line when `count` is zero.
///
/// Zero keeps every line because the ported Python used a `lines[-count:]`
/// slice, and `lines[-0:]` selects the whole list. Callers that must return
/// nothing for a zero budget check that before calling.
#[must_use]
pub fn tail_lines<'a>(lines: &[&'a str], count: usize) -> Vec<&'a str> {
    if count == 0 {
        return lines.to_vec();
    }
    lines[lines.len().saturating_sub(count)..].to_vec()
}

/// Render one JSON field the way Python's `str(value) if value else ""` did.
///
/// The ported readers wrote through `str()` rather than requiring a JSON
/// string, so a numeric or boolean field still normalizes instead of vanishing,
/// and every falsy spelling collapses to `""`.
#[must_use]
pub fn python_str(value: Option<&Value>) -> String {
    match value {
        Some(Value::String(text)) => text.clone(),
        Some(Value::Bool(true)) => "True".to_owned(),
        Some(Value::Number(number)) if number.as_f64() != Some(0.0) => number.to_string(),
        _other => String::new(),
    }
}

/// Return whether `value` is a bounded ASCII identifier for a persisted contract.
///
/// The base alphabet is ASCII alphanumeric characters plus `_` and `-`.
/// Callers whose contract permits periods must opt into them explicitly.
#[must_use]
pub fn bounded_ascii_identifier(value: &str, allow_dot: bool) -> bool {
    !value.is_empty()
        && value.len() <= 128
        && value.bytes().all(|byte| {
            byte.is_ascii_alphanumeric()
                || matches!(byte, b'_' | b'-')
                || (allow_dot && byte == b'.')
        })
}

#[cfg(test)]
mod tests {
    #[rustfmt::skip]
    use super::{bounded_ascii_identifier, ensure_ascii_json, python_bigint, python_float, split_text_lines, tail_lines, truncate_utf8_bytes};

    #[test]
    fn bounded_ascii_identifier_requires_an_explicit_period_contract() {
        assert!(bounded_ascii_identifier("session-1_2", false));
        assert!(bounded_ascii_identifier("R-1.part_2", true));
        assert!(!bounded_ascii_identifier("R-1.part_2", false));
        assert!(!bounded_ascii_identifier("invalid value", true));
    }

    #[test]
    fn python_number_spellings_keep_unicode_and_default_integer_limit() {
        assert_eq!(python_float(" ٠.٥_٠ "), Some(0.5));
        assert!(python_bigint(&"1".repeat(4_300)).is_some());
        assert!(python_bigint(&"1".repeat(4_301)).is_none());
    }

    #[test]
    fn json_ascii_uses_utf16_escapes() {
        assert_eq!(
            ensure_ascii_json("\"café🙂\""),
            "\"caf\\u00e9\\ud83d\\ude42\""
        );
        assert_eq!(ensure_ascii_json("\"\u{007f}\""), "\"\\u007f\"");
    }

    #[test]
    fn splitting_matches_the_python_boundary_set() {
        assert_eq!(split_text_lines("a\nb\n"), vec!["a", "b"]);
        assert_eq!(split_text_lines("a\r\nb"), vec!["a", "b"]);
        assert_eq!(split_text_lines("a\rb"), vec!["a", "b"]);
        assert_eq!(split_text_lines("a\u{0b}b\u{2028}c"), vec!["a", "b", "c"]);
        assert_eq!(split_text_lines(""), Vec::<&str>::new());
        assert_eq!(split_text_lines("\n"), vec![""]);
    }

    #[test]
    fn truncation_never_splits_a_multibyte_sequence() {
        assert_eq!(truncate_utf8_bytes("héllo", 2), "h");
        assert_eq!(truncate_utf8_bytes("héllo", 3), "hé");
        assert_eq!(truncate_utf8_bytes("héllo", 0), "");
        assert_eq!(truncate_utf8_bytes("abc", 99), "abc");
        assert_eq!(truncate_utf8_bytes("🙂", 3), "");
    }

    #[test]
    fn a_zero_tail_budget_keeps_every_line() {
        let lines = ["a", "b", "c"];
        assert_eq!(tail_lines(&lines, 2), vec!["b", "c"]);
        assert_eq!(tail_lines(&lines, 9), vec!["a", "b", "c"]);
        assert_eq!(tail_lines(&lines, 0), vec!["a", "b", "c"]);
    }
}
