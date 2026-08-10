//! Rust owner for `status check`, composed from the existing agent owners.

use crate::runtime_entrypoint::run_verified_larch;
use larch_core::{DuplicatePolicy, KvDocument, ParseOptions};
use std::{ffi::OsString, process::ExitCode};

/// Print the current plugin and external-tool health envelope.
pub fn check(arguments: &[OsString]) -> ExitCode {
    if arguments
        .iter()
        .any(|argument| argument == "-h" || argument == "--help")
    {
        // `quiet_init()` suppressed argparse's help renderer in the retired
        // Python entrypoint, so this compatibility verb must stay silent.
        return ExitCode::SUCCESS;
    }
    if !arguments.is_empty() {
        eprintln!("usage: cli.py status check");
        return ExitCode::from(2);
    }
    let reviewers =
        match run_verified_larch(&[OsString::from("agent"), OsString::from("check-reviewers")]) {
            Ok(output) if output.status().success() => {
                parse_kv(&String::from_utf8_lossy(output.stdout()))
            }
            _ => std::collections::BTreeMap::default(),
        };
    let codex_binary = value(&reviewers, "CODEX_BINARY_FOUND", "false");
    let cursor_binary = value(&reviewers, "CURSOR_BINARY_FOUND", "false");
    let codex_present = value(&reviewers, "CODEX_PRESENT", "false");
    let cursor_present = value(&reviewers, "CURSOR_PRESENT", "false");
    let gate = match run_verified_larch(&[
        OsString::from("agent"),
        OsString::from("degraded-tools-gate"),
        OsString::from("--codex-binary-found"),
        OsString::from(codex_binary.clone()),
        OsString::from("--codex-present"),
        OsString::from(codex_present.clone()),
        OsString::from("--cursor-binary-found"),
        OsString::from(cursor_binary.clone()),
        OsString::from("--cursor-present"),
        OsString::from(cursor_present.clone()),
        OsString::from("--skill"),
        OsString::from("status"),
    ]) {
        Ok(output) if output.status().success() => {
            parse_kv(&String::from_utf8_lossy(output.stdout()))
        }
        _ => std::collections::BTreeMap::default(),
    };
    let codex_state = value(&gate, "CODEX_STATE", "probe-failed");
    let cursor_state = value(&gate, "CURSOR_STATE", "probe-failed");
    let pins = match run_verified_larch(&[
        OsString::from("agent"),
        OsString::from("resolve-model-pins"),
        OsString::from("--codex-state"),
        OsString::from(codex_state.clone()),
        OsString::from("--cursor-state"),
        OsString::from(cursor_state.clone()),
    ]) {
        Ok(output) if output.status().success() => {
            parse_kv(&String::from_utf8_lossy(output.stdout()))
        }
        _ => std::collections::BTreeMap::default(),
    };

    emit("LARCH_PLUGIN_VERSION", &plugin_version());
    emit("CODEX_BINARY_FOUND", &codex_binary);
    emit("CURSOR_BINARY_FOUND", &cursor_binary);
    emit("CODEX_PRESENT", &codex_present);
    emit("CURSOR_PRESENT", &cursor_present);
    emit("CODEX_STATE", &codex_state);
    emit("CURSOR_STATE", &cursor_state);
    emit("DEGRADED", &value(&gate, "DEGRADED", "true"));
    if codex_state == "probe-failed"
        && let Some(detail) =
            crate::agent_commands::current_codex_probe_detail(&codex_binary, &codex_present)
                .or_else(|| reviewers.get("CODEX_PROBE_DETAIL").cloned())
    {
        emit("CODEX_PROBE_DETAIL", &detail);
    }
    emit(
        "CURSOR_MODEL_PINS",
        &value(&pins, "CURSOR_MODEL_PINS", "skipped"),
    );
    if let Some(detail) = pins.get("CURSOR_MODEL_PIN_DETAIL") {
        emit("CURSOR_MODEL_PIN_DETAIL", detail);
    }
    emit(
        "CODEX_MODEL_PINS",
        &value(&pins, "CODEX_MODEL_PINS", "skipped"),
    );
    if let Some(detail) = pins.get("CODEX_MODEL_PIN_DETAIL") {
        emit("CODEX_MODEL_PIN_DETAIL", detail);
    }
    ExitCode::SUCCESS
}

fn plugin_version() -> String {
    crate::runtime_entrypoint::plugin_root()
        .ok()
        .and_then(|root| std::fs::read_to_string(root.join(".claude-plugin/plugin.json")).ok())
        .and_then(|text| serde_json::from_str::<serde_json::Value>(&text).ok())
        .and_then(|json| {
            json.get("version")
                .and_then(serde_json::Value::as_str)
                .map(ToOwned::to_owned)
        })
        .filter(|value| !value.trim().is_empty() && value != "null")
        .unwrap_or_else(|| "unknown".to_owned())
}

fn parse_kv(text: &str) -> std::collections::BTreeMap<String, String> {
    KvDocument::parse(text, ParseOptions::legacy())
        .map(|document| document.select(DuplicatePolicy::Last))
        .unwrap_or_default()
}

fn value(values: &std::collections::BTreeMap<String, String>, key: &str, fallback: &str) -> String {
    values
        .get(key)
        .cloned()
        .unwrap_or_else(|| fallback.to_owned())
}

fn emit(key: &str, value: &str) {
    println!("{key}={}", value.replace(['\n', '\r'], " "));
}
