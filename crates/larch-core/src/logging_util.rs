//! KEY=value contract-stream emitter shared by larch commands.

/// Write one `KEY=value` row to stdout for the machine-parsed contract stream.
///
/// This is the Rust emitter owner mirroring Python `logging_util.emit_kv`;
/// larch commands route scalar KV output through it instead of ad-hoc prints.
/// Rejects embedded newlines and carriage returns so a value cannot forge
/// extra contract-stream lines (G-IO-2).
pub fn emit_kv(key: &str, value: &str) {
    if key.contains(['\n', '\r']) {
        panic!("emit_kv key {key:?} contains newline or carriage-return");
    }
    if value.contains(['\n', '\r']) {
        panic!("emit_kv value for {key:?} contains newline or carriage-return");
    }
    println!("{key}={value}");
}

#[cfg(test)]
mod tests {
    use super::emit_kv;

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
