//! Smoke coverage for reviewer-availability agent commands (#8108).

use assert_cmd::Command as AssertCommand;
use predicates::prelude::*;

fn larch() -> AssertCommand {
    AssertCommand::cargo_bin("larch").expect("larch binary should build")
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
