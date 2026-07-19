//! KEY=value contract-stream emitter shared by larch commands.

/// Write one `KEY=value` row to stdout for the machine-parsed contract stream.
///
/// This is the Rust emitter owner mirroring Python `logging_util.emit_kv`;
/// larch commands route scalar KV output through it instead of ad-hoc prints.
pub fn emit_kv(key: &str, value: &str) {
    println!("{key}={value}");
}
