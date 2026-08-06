//! Text framing shared by the ported Python line readers.

use std::fmt::Write as _;

/// Escape non-ASCII scalars in already-serialized JSON text.
///
/// Python's JSON output uses ASCII `\\u` escapes, including UTF-16 surrogate
/// pairs for supplementary-plane characters. Keep that post-serialization
/// compatibility transform in one shared owner.
#[must_use]
pub fn ensure_ascii_json(text: &str) -> String {
    let mut output = String::with_capacity(text.len());
    for character in text.chars() {
        if character.is_ascii() {
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
/// Parse a positive decimal integer, rejecting every other spelling.
///
/// Only all-ASCII-digit input parses: no sign, no whitespace, no separators,
/// and zero is not positive. Shared by the issue-number and interval readers.
#[must_use]
pub fn positive_integer(value: &str) -> Option<u64> {
    if value.is_empty() || !value.bytes().all(|byte| byte.is_ascii_digit()) {
        return None;
    }
    value.parse::<u64>().ok().filter(|parsed| *parsed > 0)
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

#[cfg(test)]
mod tests {
    use super::{ensure_ascii_json, split_text_lines, tail_lines, truncate_utf8_bytes};

    #[test]
    fn json_ascii_uses_utf16_escapes() {
        assert_eq!(
            ensure_ascii_json("\"café🙂\""),
            "\"caf\\u00e9\\ud83d\\ude42\""
        );
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
