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

fn larch(arguments: &[&str]) -> Output {
    Command::cargo_bin("larch")
        .expect("larch binary should build")
        .env("CLAUDE_PLUGIN_ROOT", plugin_root())
        .args(arguments)
        .output()
        .expect("run larch difficulty command")
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
fn extract_plan_metadata_errors_when_the_plan_is_missing() {
    let output = larch(&[
        "difficulty",
        "extract-plan-metadata",
        "--plan-file",
        "/no/such/plan.txt",
    ]);
    assert_eq!(code(&output), 2);
    assert!(stdout(&output).contains("STATUS=error"));
}

#[test]
fn write_record_applies_changed_path_floors_and_refresh() {
    let dir = TempDir::new().expect("tempdir");
    let record = dir.path().join("difficulty-rating.json");
    let paths = dir.path().join("changed.txt");
    fs::write(&paths, "hooks/pre-tool-use.sh\n").expect("paths");
    let output = larch(&[
        "difficulty",
        "write-record",
        "--output",
        record.to_str().expect("utf8"),
        "--rater",
        "implement",
        "--fallback-tier",
        "TRIVIAL",
        "--fallback-rationale",
        "tiny hook",
        "--changed-paths-file",
        paths.to_str().expect("utf8"),
    ]);
    assert_eq!(code(&output), 0, "{}", stdout(&output));
    let data: Value =
        serde_json::from_str(&fs::read_to_string(&record).expect("read")).expect("json");
    assert_eq!(data["applied_tier"], "MODERATE");
    assert_eq!(data["override_source"], "floor");

    let refreshed = larch(&[
        "difficulty",
        "write-record",
        "--output",
        record.to_str().expect("utf8"),
        "--refresh-existing",
        "--changed-paths-file",
        paths.to_str().expect("utf8"),
    ]);
    assert_eq!(code(&refreshed), 0, "{}", stdout(&refreshed));
}

#[test]
fn validate_rating_writes_an_output_file() {
    let dir = TempDir::new().expect("tempdir");
    let input = dir.path().join("rating.json");
    let output_file = dir.path().join("out.json");
    fs::write(
        &input,
        json!({
            "predicted_tier": "trivial",
            "confidence": "low",
            "rationale": "small"
        })
        .to_string(),
    )
    .expect("write rating");
    let output = larch(&[
        "difficulty",
        "validate-rating",
        "--input-file",
        input.to_str().expect("utf8"),
        "--output-file",
        output_file.to_str().expect("utf8"),
    ]);
    assert_eq!(code(&output), 0, "{}", stdout(&output));
    let data: Value =
        serde_json::from_str(&fs::read_to_string(&output_file).expect("read")).expect("json");
    assert_eq!(data["adjusted_tier"], "MODERATE");
}

#[test]
fn resolve_panel_rejects_an_invalid_override() {
    let dir = TempDir::new().expect("tempdir");
    let record = dir.path().join("difficulty-rating.json");
    fs::write(&record, "{}").expect("record");
    let output = larch(&[
        "difficulty",
        "resolve-panel",
        "--record-file",
        record.to_str().expect("utf8"),
        "--override",
        "EASY",
    ]);
    assert_eq!(code(&output), 2);
    assert!(stdout(&output).contains("ERROR=invalid-override"));
}

#[test]
fn write_record_honors_explicit_resolution_flags() {
    let dir = TempDir::new().expect("tempdir");
    let record = dir.path().join("difficulty-rating.json");
    let output = larch(&[
        "difficulty",
        "write-record",
        "--output",
        record.to_str().expect("utf8"),
        "--rater",
        "design",
        "--design-tier",
        "TRIVIAL",
        "--fallback-tier",
        "MODERATE",
        "--panel-skipped",
        "no-panel",
        "--audit-upgrade",
        "true",
        "--override-tier",
        "TRIVIAL",
        "--panel-tier",
        "HARD",
        "--round-cap",
        "1",
        "--codex-model-role",
        "review",
        "--audit-evaluated",
        "true",
        "--escalated-round",
        "false",
    ]);
    assert_eq!(code(&output), 0, "{}", stdout(&output));
    let data: Value =
        serde_json::from_str(&fs::read_to_string(&record).expect("read")).expect("json");
    assert_eq!(data["override_source"], "operator");
    assert_eq!(data["applied_tier"], "HARD");
    assert_eq!(data["panel_tier"], "HARD");
    assert_eq!(data["round_cap"], 1);
    assert_eq!(data["panel_skipped"], "no-panel");
}

#[test]
fn resolve_panel_audit_roll_upgrades_to_hard() {
    let dir = TempDir::new().expect("tempdir");
    let record = dir.path().join("difficulty-rating.json");
    let written = larch(&[
        "difficulty",
        "write-record",
        "--output",
        record.to_str().expect("utf8"),
        "--rater",
        "implement",
        "--fallback-tier",
        "TRIVIAL",
        "--fallback-rationale",
        "tiny",
    ]);
    assert_eq!(code(&written), 0, "{}", stdout(&written));
    let output = larch(&[
        "difficulty",
        "resolve-panel",
        "--record-file",
        record.to_str().expect("utf8"),
        "--audit-roll",
        "1",
    ]);
    assert_eq!(code(&output), 0, "{}", stdout(&output));
    assert!(stdout(&output).contains("PANEL_TIER=HARD"));
    assert!(stdout(&output).contains("AUDIT_UPGRADE=true"));
}

#[test]
fn write_record_refresh_reads_git_changed_paths() {
    let dir = TempDir::new().expect("tempdir");
    let root = dir.path();
    git(root, &["init", "--quiet"]);
    git(root, &["config", "user.email", "larch@example.com"]);
    git(root, &["config", "user.name", "Larch Test"]);
    fs::write(root.join("README"), "seed\n").expect("readme");
    git(root, &["add", "README"]);
    git(root, &["commit", "-q", "-m", "seed"]);
    fs::create_dir_all(root.join("hooks")).expect("hooks");
    fs::write(root.join("hooks/pre-tool-use.sh"), "echo\n").expect("hook");
    git(root, &["add", "hooks/pre-tool-use.sh"]);
    let record = root.join("difficulty-rating.json");
    let seed = larch(&[
        "difficulty",
        "write-record",
        "--output",
        record.to_str().expect("utf8"),
        "--rater",
        "implement",
        "--fallback-tier",
        "TRIVIAL",
        "--fallback-rationale",
        "tiny",
    ]);
    assert_eq!(code(&seed), 0, "{}", stdout(&seed));
    let refreshed = larch(&[
        "difficulty",
        "write-record",
        "--output",
        record.to_str().expect("utf8"),
        "--refresh-existing",
        "--refresh-repo-root",
        root.to_str().expect("utf8"),
    ]);
    assert_eq!(code(&refreshed), 0, "{}", stdout(&refreshed));
    let data: Value =
        serde_json::from_str(&fs::read_to_string(&record).expect("read")).expect("json");
    assert_eq!(data["applied_tier"], "MODERATE");
    assert_eq!(data["override_source"], "floor");
}

fn git(root: &Path, args: &[&str]) {
    let status = ProcessCommand::new("git") // lint-subprocess-via-runner: ok test-only Git fixture
        .args(args)
        .current_dir(root)
        .status()
        .expect("git");
    assert!(status.success(), "git {args:?} failed");
}
