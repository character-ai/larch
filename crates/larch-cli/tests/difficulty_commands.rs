//! Contract coverage for the Rust-owned `difficulty` commands.

use std::{
    fs,
    path::{Path, PathBuf},
    process::{Command as ProcessCommand, Output},
};

use assert_cmd::Command;
use serde_json::{Value, json};
use tempfile::TempDir;

fn plugin_root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .canonicalize()
        .expect("plugin root")
}

fn python_root() -> PathBuf {
    plugin_root().join("python")
}

fn oracle_path() -> PathBuf {
    plugin_root().join("fixtures/rust-parity/difficulty_reference.py")
}

fn larch(arguments: &[&str]) -> Output {
    Command::cargo_bin("larch")
        .expect("larch binary should build")
        .env("CLAUDE_PLUGIN_ROOT", plugin_root())
        .args(arguments)
        .output()
        .expect("run larch difficulty command")
}

fn oracle(arguments: &[&str]) -> Output {
    ProcessCommand::new("python3") // lint-subprocess-via-runner: ok frozen test-only Python parity oracle
        .arg(oracle_path())
        .args(arguments)
        .env("PYTHONPATH", python_root())
        .env("CLAUDE_PLUGIN_ROOT", plugin_root())
        .output()
        .expect("run frozen Python difficulty oracle")
}

fn assert_same_output(left: &Output, right: &Output) {
    assert_eq!(
        code(left),
        code(right),
        "stderr rust={} python={}",
        stderr(left),
        stderr(right)
    );
    assert_eq!(stdout(left), stdout(right));
    assert_eq!(stderr(left), stderr(right));
}

fn stdout(output: &Output) -> String {
    String::from_utf8_lossy(&output.stdout).into_owned()
}

fn stderr(output: &Output) -> String {
    String::from_utf8_lossy(&output.stderr).into_owned()
}

fn code(output: &Output) -> i32 {
    output.status.code().unwrap_or(-1)
}

#[test]
fn render_rubric_prints_the_shared_anchor() {
    let output = larch(&["difficulty", "render-rubric"]);
    assert_eq!(code(&output), 0, "{}", stderr(&output));
    let text = stdout(&output);
    assert!(text.starts_with("Difficulty rating rubric"));
    assert!(text.contains("TRIVIAL:"));
    assert!(text.contains("Floors raise only."));
}

#[test]
fn render_rubric_help_matches_argparse() {
    let output = larch(&["difficulty", "render-rubric", "--help"]);
    assert_eq!(code(&output), 0, "{}", stderr(&output));
    assert_eq!(
        stdout(&output),
        "usage: cli.py difficulty render-rubric [-h]\n\noptions:\n  -h, --help  show this help message and exit\n"
    );
}

#[test]
fn validate_rating_accepts_a_low_confidence_bump() {
    let dir = TempDir::new().expect("tempdir");
    let input = dir.path().join("rating.json");
    fs::write(
        &input,
        json!({
            "predicted_tier": "trivial",
            "confidence": "low",
            "rationale": "line\nwith\tcontrols"
        })
        .to_string(),
    )
    .expect("write rating");
    let output = larch(&[
        "difficulty",
        "validate-rating",
        "--input-file",
        input.to_str().expect("utf8"),
    ]);
    assert_eq!(code(&output), 0, "{}", stdout(&output));
    let text = stdout(&output);
    assert!(text.contains("STATUS=ok"));
    assert!(text.contains("PREDICTED_TIER=TRIVIAL"));
    assert!(text.contains("ADJUSTED_TIER=MODERATE"));
}

#[test]
fn extract_plan_metadata_reads_the_trailing_trailer() {
    let dir = TempDir::new().expect("tempdir");
    let plan = dir.path().join("plan.txt");
    fs::write(&plan, "Goal\n\ndifficulty: HARD\ndiff_lines: 4\n").expect("write plan");
    let output = larch(&[
        "difficulty",
        "extract-plan-metadata",
        "--plan-file",
        plan.to_str().expect("utf8"),
    ]);
    assert_eq!(code(&output), 0, "{}", stdout(&output));
    assert!(stdout(&output).contains("DESIGN_DIFFICULTY=HARD"));
}

#[test]
fn write_record_merges_persisted_operator_resolution() {
    let dir = TempDir::new().expect("tempdir");
    let out = dir.path().join("difficulty-rating.json");
    fs::write(
        &out,
        json!({
            "schema_version": 1,
            "rater": "implement",
            "rater_tool": "bootstrap",
            "rater_model": "unknown",
            "predicted_tier": "TRIVIAL",
            "confidence": "medium",
            "rationale": "old",
            "design_tier": null,
            "implement_tier": null,
            "applied_tier": "HARD",
            "override_source": "operator",
            "floors_applied": [],
            "audit_upgrade": "true",
            "escalations": [{"round": 2, "from_tier": "MODERATE", "to_tier": "HARD", "trigger": "bulk-skip"}],
            "panel_skipped": null,
            "panel_tier": "HARD",
            "round_cap": 3,
            "codex_model_role": "default",
            "audit_evaluated": true,
            "escalated_round": true
        })
        .to_string(),
    )
    .expect("write existing");
    let output = larch(&[
        "difficulty",
        "write-record",
        "--output",
        out.to_str().expect("utf8"),
        "--rater",
        "implement",
        "--fallback-tier",
        "MODERATE",
        "--fallback-rationale",
        "new",
    ]);
    assert_eq!(code(&output), 0, "{}", stdout(&output));
    let data: Value =
        serde_json::from_str(&fs::read_to_string(&out).expect("read record")).expect("json");
    assert_eq!(data["override_source"], "operator");
    assert_eq!(data["audit_upgrade"], "true");
    assert_eq!(data["panel_tier"], "HARD");
    assert_eq!(data["round_cap"], 2);
}

#[test]
fn refresh_existing_does_not_write_when_git_fails() {
    let dir = TempDir::new().expect("tempdir");
    let out = dir.path().join("difficulty-rating.json");
    let body = json!({
        "schema_version": 1,
        "rater": "implement",
        "rater_tool": "unknown",
        "rater_model": "unknown",
        "predicted_tier": "MODERATE",
        "confidence": "medium",
        "rationale": "existing scope",
        "adjusted_tier": "MODERATE",
        "design_tier": null,
        "implement_tier": "MODERATE",
        "applied_tier": "MODERATE",
        "override_source": "none",
        "floors_applied": [],
        "audit_upgrade": null,
        "escalations": [],
        "panel_skipped": null,
        "panel_tier": "MODERATE",
        "round_cap": 2,
        "codex_model_role": "review",
        "audit_evaluated": null,
        "escalated_round": null
    })
    .to_string();
    fs::write(&out, &body).expect("write record");
    let before = fs::read(&out).expect("read before");
    let output = larch(&[
        "difficulty",
        "write-record",
        "--output",
        out.to_str().expect("utf8"),
        "--refresh-existing",
        "--refresh-repo-root",
        dir.path().to_str().expect("utf8"),
    ]);
    assert_eq!(code(&output), 1, "{}", stdout(&output));
    assert!(stdout(&output).contains("difficulty refresh could not read changed paths"));
    assert_eq!(fs::read(&out).expect("read after"), before);
}

#[test]
fn render_line_summarizes_a_record() {
    let dir = TempDir::new().expect("tempdir");
    let record = dir.path().join("record.json");
    fs::write(
        &record,
        json!({
            "predicted_tier": "MODERATE",
            "applied_tier": "HARD",
            "floors_applied": [{"path": "hooks/x.sh", "glob": "hooks/*", "floor": "MODERATE", "reason": "hooks"}],
            "override_source": "operator"
        })
        .to_string(),
    )
    .expect("write record");
    let output = larch(&[
        "difficulty",
        "render-line",
        "--record-file",
        record.to_str().expect("utf8"),
    ]);
    assert_eq!(code(&output), 0, "{}", stderr(&output));
    let line = stdout(&output);
    assert!(line.contains("predicted MODERATE"));
    assert!(line.contains("applied HARD"));
    assert!(line.contains("override operator"));
}

#[test]
fn resolve_panel_no_audit_keeps_moderate() {
    let dir = TempDir::new().expect("tempdir");
    let record = dir.path().join("difficulty-rating.json");
    fs::write(
        &record,
        json!({
            "schema_version": 1,
            "rater": "design",
            "predicted_tier": "MODERATE",
            "confidence": "medium",
            "rationale": "bootstrap",
            "applied_tier": "MODERATE"
        })
        .to_string(),
    )
    .expect("write record");
    let output = larch(&[
        "difficulty",
        "resolve-panel",
        "--record-file",
        record.to_str().expect("utf8"),
        "--no-audit",
    ]);
    assert_eq!(code(&output), 0, "{}", stdout(&output));
    let text = stdout(&output);
    assert!(text.contains("PANEL_TIER=MODERATE"));
    assert!(text.contains("AUDIT_EVALUATED=false"));
}

#[test]
fn sync_labels_refuses_an_invalid_tier() {
    let output = larch(&[
        "difficulty",
        "sync-labels",
        "--issue",
        "9",
        "--tier",
        "EASY",
        "--repo",
        "o/r",
    ]);
    assert_eq!(code(&output), 2);
    assert!(stdout(&output).contains("ERROR=invalid-tier"));
}

#[test]
fn write_record_missing_output_is_argparse_usage() {
    let output = larch(&["difficulty", "write-record"]);
    assert_eq!(code(&output), 2);
    assert!(stderr(&output).contains("the following arguments are required: --output"));
}

#[test]
fn write_record_rejects_an_invalid_rater_choice() {
    let output = larch(&[
        "difficulty",
        "write-record",
        "--output",
        "x.json",
        "--rater",
        "EASY",
    ]);
    assert_eq!(code(&output), 2);
    assert!(stderr(&output).contains("argument --rater: invalid choice: 'EASY'"));
}

#[test]
fn help_text_matches_the_frozen_python_oracle() {
    for verb in [
        "validate-rating",
        "extract-plan-metadata",
        "write-record",
        "render-rubric",
        "render-line",
        "resolve-panel",
        "sync-labels",
    ] {
        assert_same_output(
            &larch(&["difficulty", verb, "--help"]),
            &oracle(&[verb, "--help"]),
        );
    }
}

#[test]
fn validate_rating_stdout_matches_the_frozen_python_oracle() {
    let dir = TempDir::new().expect("tempdir");
    let input = dir.path().join("rating.json");
    fs::write(
        &input,
        json!({
            "predicted_tier": "trivial",
            "confidence": "low",
            "rationale": "line\nwith\tcontrols"
        })
        .to_string(),
    )
    .expect("write rating");
    let path = input.to_str().expect("utf8");
    assert_same_output(
        &larch(&["difficulty", "validate-rating", "--input-file", path]),
        &oracle(&["validate-rating", "--input-file", path]),
    );
}

#[test]
fn write_record_wire_file_matches_the_frozen_python_oracle() {
    let dir = TempDir::new().expect("tempdir");
    let rust_out = dir.path().join("rust.json");
    let python_out = dir.path().join("python.json");
    let rust = larch(&[
        "difficulty",
        "write-record",
        "--output",
        rust_out.to_str().expect("utf8"),
        "--rater",
        "implement",
        "--fallback-tier",
        "MODERATE",
        "--fallback-rationale",
        "new",
    ]);
    let python = oracle(&[
        "write-record",
        "--output",
        python_out.to_str().expect("utf8"),
        "--rater",
        "implement",
        "--fallback-tier",
        "MODERATE",
        "--fallback-rationale",
        "new",
    ]);
    assert_eq!(code(&rust), 0, "{}", stdout(&rust));
    assert_eq!(code(&python), 0, "{}", stdout(&python));
    assert_eq!(
        fs::read_to_string(&rust_out).expect("rust record"),
        fs::read_to_string(&python_out).expect("python record")
    );
}

#[test]
fn sync_labels_invalid_tier_matches_the_frozen_python_oracle() {
    assert_same_output(
        &larch(&[
            "difficulty",
            "sync-labels",
            "--issue",
            "9",
            "--tier",
            "EASY",
            "--repo",
            "o/r",
        ]),
        &oracle(&[
            "sync-labels",
            "--issue",
            "9",
            "--tier",
            "EASY",
            "--repo",
            "o/r",
        ]),
    );
}
