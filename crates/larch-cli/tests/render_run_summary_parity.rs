//! Black-box parity coverage for the Rust `render run-summary` command (#8839).
//!
//! Each case drives the real binary and pins the rendered body, the `STATUS=ok`
//! / `OUTPUT_FILE=` stderr framing, the output-file wire, and the exit codes the
//! retired Python `render_run_summary_main` entrypoint produced. Dollar amounts
//! depend on the ambient rate table, so cost cases assert structural markers
//! rather than exact figures.

use std::fs;

use assert_cmd::Command as AssertCommand;
use predicates::prelude::PredicateBooleanExt as _;
use tempfile::TempDir;

fn larch() -> AssertCommand {
    AssertCommand::cargo_bin("larch").expect("larch binary")
}

#[test]
fn help_exits_zero() {
    larch()
        .args(["render", "run-summary", "--help"])
        .assert()
        .success();
}

#[test]
fn missing_required_arguments_is_a_usage_error() {
    larch()
        .args(["render", "run-summary"])
        .assert()
        .code(2)
        .stderr(predicates::str::contains("STATUS=ok").not());
}

#[test]
fn invalid_skill_choice_is_a_usage_error() {
    larch()
        .args([
            "render",
            "run-summary",
            "--skill",
            "bogus",
            "--outcome",
            "x",
            "--run-id",
            "r",
        ])
        .assert()
        .code(2)
        .stderr(predicates::str::contains("STATUS=ok").not());
}

#[test]
fn implement_cost_unavailable_writes_output_file() {
    let dir = TempDir::new().unwrap();
    let out = dir.path().join("summary.md");
    larch()
        .args([
            "render",
            "run-summary",
            "--skill",
            "implement",
            "--outcome",
            "completed",
            "--run-id",
            "run-1",
            "--output-file",
            &out.display().to_string(),
            "--cost-unavailable",
        ])
        .assert()
        .success()
        .stderr(predicates::str::contains("STATUS=ok"))
        .stderr(predicates::str::contains(format!(
            "OUTPUT_FILE={}",
            out.display()
        )));
    let body = fs::read_to_string(&out).unwrap();
    assert!(
        body.starts_with("## /implement run run-1: completed\n\n"),
        "{body}"
    );
    assert!(body.contains("- **Cost**: N/A\n"), "{body}");
    assert!(body.ends_with("<!-- larch:run-summary v=1 -->\n"), "{body}");
}

#[test]
fn design_summary_omits_pr_and_code_rows_on_stdout() {
    larch()
        .args([
            "render",
            "run-summary",
            "--skill",
            "design",
            "--outcome",
            "approved",
            "--run-id",
            "run-2",
            "--print-stdout",
            "--cost-unavailable",
        ])
        .assert()
        .success()
        .stdout(predicates::str::contains("## /design run run-2: approved"))
        .stdout(predicates::str::contains("- **Outcome**: \u{2705} DONE"))
        .stdout(predicates::str::contains("- **PR**:").not())
        .stdout(predicates::str::contains("- **Lines (PR diff)**:").not());
}

#[test]
fn cost_available_renders_the_total_line_and_codex_split() {
    let dir = TempDir::new().unwrap();
    let manifest = dir.path().join("manifest.json");
    fs::write(
        &manifest,
        "{\"model_roster\":{\"main\":\"claude-sonnet-4-6\"}}\n",
    )
    .unwrap();
    larch()
        .args([
            "render",
            "run-summary",
            "--skill",
            "implement",
            "--outcome",
            "merged",
            "--run-id",
            "run-3",
            "--manifest-path",
            &manifest.display().to_string(),
            "--claude-input-tokens",
            "1000000",
            "--codex-input-tokens",
            "1000000",
            "--codex-mini-input-tokens",
            "1000000",
            "--print-stdout",
        ])
        .assert()
        .success()
        .stdout(predicates::str::contains("\u{1f4b0} TOTAL"))
        .stdout(predicates::str::contains("Claude $"))
        .stdout(predicates::str::contains("Codex-5.6 $"))
        .stdout(predicates::str::contains("Codex-mini $"))
        .stdout(predicates::str::contains(
            "- **Main agent model**: claude-sonnet-4-6",
        ))
        .stdout(predicates::str::contains("Claude/GLM-5.2").not());
}

#[test]
fn glm_main_lane_renders_the_plan_estimate() {
    let dir = TempDir::new().unwrap();
    let manifest = dir.path().join("manifest.json");
    fs::write(&manifest, "{\"model_roster\":{\"main\":\"glm-5.2\"}}\n").unwrap();
    larch()
        .args([
            "render",
            "run-summary",
            "--skill",
            "implement",
            "--outcome",
            "merged",
            "--run-id",
            "run-glm",
            "--manifest-path",
            &manifest.display().to_string(),
            "--claude-input-tokens",
            "1000000",
            "--print-stdout",
        ])
        .assert()
        .success()
        .stdout(predicates::str::contains("Claude/GLM-5.2 token $"))
        .stdout(predicates::str::contains("**Cost note**:"))
        .stdout(predicates::str::contains("- **Main agent model**: glm-5.2"));
}

#[test]
fn partial_line_counts_degrade_to_not_available() {
    larch()
        .args([
            "render",
            "run-summary",
            "--skill",
            "implement",
            "--outcome",
            "merged",
            "--run-id",
            "run-lines",
            "--code-added",
            "10",
            "--print-stdout",
            "--cost-unavailable",
        ])
        .assert()
        .success()
        .stdout(predicates::str::contains("- **Lines (PR diff)**: N/A"));
}

#[test]
fn note_lines_file_appends_after_the_sentinel() {
    let dir = TempDir::new().unwrap();
    let note = dir.path().join("note.md");
    fs::write(&note, "extra note line\n").unwrap();
    let out = dir.path().join("summary.md");
    larch()
        .args([
            "render",
            "run-summary",
            "--skill",
            "design",
            "--outcome",
            "approved",
            "--run-id",
            "run-note",
            "--note-lines-file",
            &note.display().to_string(),
            "--output-file",
            &out.display().to_string(),
            "--cost-unavailable",
        ])
        .assert()
        .success();
    let body = fs::read_to_string(&out).unwrap();
    assert!(
        body.contains("<!-- larch:run-summary v=1 -->\n\nextra note line\n"),
        "{body}"
    );
}
