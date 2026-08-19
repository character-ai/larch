//! KEY=value contract-stream emitter shared by larch commands.

/// Write one `KEY=value` row to stdout for the machine-parsed contract stream.
///
/// This is the Rust emitter owner mirroring Python `logging_util.emit_kv`;
/// larch commands route scalar KV output through it instead of ad-hoc prints.
/// Rejects embedded newlines and carriage returns so a value cannot forge
/// extra contract-stream lines (G-IO-2).
///
/// # Panics
///
/// Panics when `key` or `value` contains a newline or carriage return.
pub fn emit_kv(key: &str, value: &str) {
    assert!(
        !key.contains(['\n', '\r']),
        "emit_kv key {key:?} contains newline or carriage-return"
    );
    assert!(
        !value.contains(['\n', '\r']),
        "emit_kv value for {key:?} contains newline or carriage-return"
    );
    println!("{key}={value}");
}

/// Strip C0 control bytes and DEL from one diagnostic line.
///
/// Mirrors Python `logging_util.sanitize_diagnostic_line`: a warning derived
/// from model output must not carry the control bytes that would let it forge
/// extra contract-stream rows or rewrite an operator's terminal.
#[must_use]
pub fn sanitize_diagnostic_line(text: &str) -> String {
    text.chars()
        .filter(|character| *character >= ' ' && *character != '\u{7f}')
        .collect()
}

#[cfg(test)]
mod tests {
    use super::{emit_kv, sanitize_diagnostic_line};

    #[test]
    fn sanitize_strips_control_bytes_and_del() {
        assert_eq!(sanitize_diagnostic_line("a\nb\u{7f}c\td"), "abcd");
        assert_eq!(sanitize_diagnostic_line("plain text"), "plain text");
    }

    #[test]
    #[should_panic(expected = "newline or carriage-return")]
    fn emit_kv_rejects_newline_in_value() {
        emit_kv("ERROR", "line1\nline2");
    }

    #[test]
    #[should_panic(expected = "newline or carriage-return")]
    fn emit_kv_rejects_cr_in_key() {
        emit_kv("ERR\rOR", "ok");
    }
}
