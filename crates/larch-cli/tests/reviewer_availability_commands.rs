//! Smoke coverage for reviewer-availability agent commands (#8108).

use assert_cmd::Command as AssertCommand;
use larch_adapters::{TemporaryRoot, vendor_auth::ProbeCache};
use larch_core::{
    CODEX_REVIEW_MODEL_DEFAULT, CodexEnvAuth, ProbeTtl, detect_codex_cli_gate,
    codex_probe_identity,
};
use predicates::prelude::*;
use std::{fs, os::unix::fs::PermissionsExt, path::Path};

fn larch() -> AssertCommand {
    AssertCommand::cargo_bin("larch").expect("larch binary should build")
}

fn make_executable(dir: &Path, name: &str) {
    fs::create_dir_all(dir).expect("bin dir");
    let path = dir.join(name);
    fs::write(&path, b"#!/bin/sh\nexit 0\n").expect("write binary");
    let mut permissions = fs::metadata(&path).expect("meta").permissions();
    permissions.set_mode(0o755);
    fs::set_permissions(&path, permissions).expect("chmod");
}

#[test]
fn check_reviewers_skip_probes_with_empty_path_reports_all_false() {
    larch()
        .env_clear()
        .env("PATH", "")
        .env("HOME", std::env::temp_dir())
        .env("TMPDIR", std::env::temp_dir())
        .env("USER", "larch-test")
        .args([
            "agent",
            "check-reviewers",
            "--skip-codex-probe",
            "--skip-cursor-probe",
        ])
        .assert()
        .success()
        .stdout(concat!(
            "CODEX_BINARY_FOUND=false\n",
            "CURSOR_BINARY_FOUND=false\n",
            "CODEX_PRESENT=false\n",
            "CURSOR_PRESENT=false\n",
            "CODEX_PROBE_TIMED_OUT=false\n",
            "CURSOR_PROBE_TIMED_OUT=false\n",
        ));
}

#[test]
fn check_reviewers_discovers_binaries_when_probes_are_skipped() {
    let bin = tempfile::tempdir().expect("bin");
    make_executable(bin.path(), "codex");
    make_executable(bin.path(), "cursor");

    larch()
        .env_clear()
        .env("PATH", bin.path())
        .env("HOME", std::env::temp_dir())
        .env("TMPDIR", std::env::temp_dir())
        .env("USER", "larch-test")
        .args([
            "agent",
            "check-reviewers",
            "--skip-codex-probe",
            "--skip-cursor-probe",
        ])
        .assert()
        .success()
        .stdout(concat!(
            "CODEX_BINARY_FOUND=true\n",
            "CURSOR_BINARY_FOUND=true\n",
            "CODEX_PRESENT=false\n",
            "CURSOR_PRESENT=false\n",
            "CODEX_PROBE_TIMED_OUT=false\n",
            "CURSOR_PROBE_TIMED_OUT=false\n",
        ));
}

#[test]
fn check_reviewers_skip_codex_only_leaves_cursor_unprobed_on_empty_path() {
    larch()
        .env_clear()
        .env("PATH", "")
        .env("HOME", std::env::temp_dir())
        .env("TMPDIR", std::env::temp_dir())
        .env("USER", "larch-test")
        .args(["agent", "check-reviewers", "--skip-codex-probe"])
        .assert()
        .success()
        .stdout(concat!(
            "CODEX_BINARY_FOUND=false\n",
            "CURSOR_BINARY_FOUND=false\n",
            "CODEX_PRESENT=false\n",
            "CURSOR_PRESENT=false\n",
            "CODEX_PROBE_TIMED_OUT=false\n",
            "CURSOR_PROBE_TIMED_OUT=false\n",
        ));
}

#[test]
fn check_reviewers_skip_cursor_only_leaves_codex_unprobed_on_empty_path() {
    larch()
        .env_clear()
        .env("PATH", "")
        .env("HOME", std::env::temp_dir())
        .env("TMPDIR", std::env::temp_dir())
        .env("USER", "larch-test")
        .args(["agent", "check-reviewers", "--skip-cursor-probe"])
        .assert()
        .success()
        .stdout(concat!(
            "CODEX_BINARY_FOUND=false\n",
            "CURSOR_BINARY_FOUND=false\n",
            "CODEX_PRESENT=false\n",
            "CURSOR_PRESENT=false\n",
            "CODEX_PROBE_TIMED_OUT=false\n",
            "CURSOR_PROBE_TIMED_OUT=false\n",
        ));
}

#[test]
fn degraded_tools_gate_both_down_emits_hard_fail_and_explanation() {
    larch()
        .args([
            "agent",
            "degraded-tools-gate",
            "--codex-binary-found",
            "false",
            "--codex-present",
            "false",
            "--cursor-binary-found",
            "false",
            "--cursor-present",
            "false",
            "--skill",
            "implement",
        ])
        .assert()
        .success()
        .stdout(predicate::str::contains("DEGRADED=true"))
        .stdout(predicate::str::contains("BOTH_DOWN=true"))
        .stdout(predicate::str::contains("DEGRADED_HARD_FAIL=true"))
        .stdout(predicate::str::contains("DEGRADED_EXPLANATION_BEGIN"))
        .stdout(predicate::str::contains("DEGRADED_EXPLANATION_END"));
}

#[test]
fn degraded_tools_gate_healthy_run_emits_not_degraded() {
    larch()
        .args([
            "agent",
            "degraded-tools-gate",
            "--codex-binary-found",
            "true",
            "--codex-present",
            "true",
            "--cursor-binary-found",
            "true",
            "--cursor-present",
            "true",
            "--skill",
            "design",
        ])
        .assert()
        .success()
        .stdout(predicate::str::contains("DEGRADED=false"))
        .stdout(predicate::str::contains("BOTH_DOWN=false"));
}

#[test]
fn degraded_tools_gate_one_down_codex_probe_failed_requires_confirmation() {
    larch()
        .args([
            "agent",
            "degraded-tools-gate",
            "--codex-binary-found",
            "true",
            "--codex-present",
            "false",
            "--cursor-binary-found",
            "true",
            "--cursor-present",
            "true",
            "--skill",
            "implement",
        ])
        .assert()
        .success()
        .stdout(predicate::str::contains("DEGRADED=true"))
        .stdout(predicate::str::contains("BOTH_DOWN=false"))
        .stdout(predicate::str::contains("CODEX_STATE=probe-failed"))
        .stdout(predicate::str::contains("CURSOR_STATE=ok"))
        .stdout(predicate::str::contains(
            "Exactly one external vendor is unavailable",
        ));
}

#[test]
fn degraded_tools_gate_one_down_cursor_missing_requires_confirmation() {
    larch()
        .args([
            "agent",
            "degraded-tools-gate",
            "--codex-binary-found",
            "true",
            "--codex-present",
            "true",
            "--cursor-binary-found",
            "false",
            "--cursor-present",
            "false",
            "--skill",
            "review",
        ])
        .assert()
        .success()
        .stdout(predicate::str::contains("DEGRADED=true"))
        .stdout(predicate::str::contains("BOTH_DOWN=false"))
        .stdout(predicate::str::contains("CODEX_STATE=ok"))
        .stdout(predicate::str::contains("CURSOR_STATE=binary-missing"))
        .stdout(predicate::str::contains(
            "Exactly one external vendor is unavailable",
        ));
}

#[test]
fn degraded_tools_gate_empty_presence_is_fail_safe() {
    larch()
        .env_remove("CODEX_PRESENT")
        .env_remove("CURSOR_PRESENT")
        .args([
            "agent",
            "degraded-tools-gate",
            "--codex-binary-found",
            "true",
            "--cursor-binary-found",
            "true",
            "--skill",
            "implement",
        ])
        .assert()
        .success()
        .stdout(predicate::str::contains("DEGRADED=true"))
        .stdout(predicate::str::contains("PRESENCE_INPUT_EMPTY=true"))
        .stderr(predicate::str::contains(
            "agent degraded-tools-gate: ERROR: --codex-present resolved empty",
        ))
        .stderr(predicate::str::contains(
            "agent degraded-tools-gate: ERROR: --cursor-present resolved empty",
        ));
}

#[test]
fn degraded_tools_gate_surfaces_cached_codex_gate_detail_for_probe_failed() {
    let tmp = tempfile::tempdir().expect("tmp");
    let canonical = fs::canonicalize(tmp.path()).expect("canonical tmp");
    let user = "larch-test";
    let identity = codex_probe_identity(CodexEnvAuth::Omit, CODEX_REVIEW_MODEL_DEFAULT);
    let detail = detect_codex_cli_gate("requires a newer version of Codex", CODEX_REVIEW_MODEL_DEFAULT)
        .expect("gate detail");
    let root = TemporaryRoot::resolve(Some(&canonical)).expect("temporary root");
    let cache = ProbeCache::new(root, Some(user), ProbeTtl::from_seconds(60, 30));
    cache.write_verdict(&identity, false).expect("stamp");
    cache
        .write_gate_detail(&identity, &detail)
        .expect("gate detail");

    larch()
        .env_clear()
        .env("TMPDIR", canonical.to_str().expect("utf8"))
        .env("HOME", std::env::temp_dir())
        .env("USER", user)
        .args([
            "agent",
            "degraded-tools-gate",
            "--codex-binary-found",
            "true",
            "--codex-present",
            "false",
            "--cursor-binary-found",
            "true",
            "--cursor-present",
            "true",
            "--skill",
            "implement",
        ])
        .assert()
        .success()
        .stdout(predicate::str::contains("DEGRADED=true"))
        .stdout(predicate::str::contains(detail.message()));
}

#[test]
fn resolve_model_pins_skips_cursor_when_binary_missing() {
    larch()
        .args([
            "agent",
            "resolve-model-pins",
            "--codex-state",
            "ok",
            "--cursor-state",
            "binary-missing",
        ])
        .assert()
        .success()
        .stdout(predicate::str::contains("CODEX_MODEL_PINS=unverifiable"))
        .stdout(predicate::str::contains("CURSOR_MODEL_PINS=skipped"));
}

#[test]
fn resolve_model_pins_skips_both_when_vendor_probes_not_ok() {
    larch()
        .args([
            "agent",
            "resolve-model-pins",
            "--codex-state",
            "probe-failed",
            "--cursor-state",
            "unavailable",
        ])
        .assert()
        .success()
        .stdout(predicate::str::contains("CODEX_MODEL_PINS=skipped"))
        .stdout(predicate::str::contains("CURSOR_MODEL_PINS=skipped"))
        .stdout(predicate::str::contains("vendor probe not ok"));
}

#[test]
fn resolve_model_pins_codex_unverifiable_when_codex_ok() {
    larch()
        .args([
            "agent",
            "resolve-model-pins",
            "--codex-state",
            "ok",
            "--cursor-state",
            "binary-missing",
        ])
        .assert()
        .success()
        .stdout(predicate::str::contains("CODEX_MODEL_PINS=unverifiable"))
        .stdout(predicate::str::contains("codex has no model-list surface"));
}
