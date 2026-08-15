//! Executable-boundary coverage for the `eval research` live harness.
//!
//! These tests drive the real `larch eval research` entrypoint against a fake
//! `claude` on `PATH`, so the orchestration path (launch, judge, scoring, and
//! baseline emission) runs end to end without contacting a real vendor.

use assert_cmd::Command;
use predicates::prelude::*;
use std::{env, fs, path::Path};
use tempfile::TempDir;

#[cfg(unix)]
use std::os::unix::fs::PermissionsExt as _;

fn valid_eval_set() -> String {
    let mut text = String::from(
        "# eval-set\nConsumer: research harness\nContract: scored eval entries\nWhen-to-load: on eval-research\nSource: anthropic.com/engineering/built-multi-agent-research-system\n\n",
    );
    let categories = [
        "lookup",
        "architecture",
        "external-comparison",
        "risk-assessment",
        "feasibility",
    ];
    for index in 0..20 {
        let category = categories[index % 5];
        let notes = match index {
            0 => "adversarial fictitious probe",
            1 => "adversarial no data expected",
            _ => "routine note",
        };
        let number = index + 1;
        text.push_str(&format!(
            "### eval-{number}: id-{number}\n- **category**: {category}\n- **expected_provenance_count**: 1\n- **expected_keywords**: alpha, beta\n- **question**: what is item {number}?\n- **notes**: {notes}\n\n"
        ));
    }
    text
}

fn valid_baseline_json() -> String {
    let entries: Vec<serde_json::Value> = (1..=2)
        .map(|number| {
            serde_json::json!({
                "id": format!("id-{number}"),
                "category": "lookup",
                "provenance": {"file_line": 0, "repo_path": 0, "url": 0},
                "keyword_coverage_pct": 0,
                "length_lines": 0,
                "judge_status": "ok",
                "judge_total": 50,
                "wall_clock_seconds": 1,
                "research_status": "ok",
            })
        })
        .collect();
    serde_json::json!({"version": 2, "entries": entries}).to_string()
}

fn plugin_root() -> TempDir {
    let root = TempDir::new().expect("fixture");
    let refs = root.path().join("skills/research/references");
    fs::create_dir_all(&refs).expect("refs dir");
    fs::write(refs.join("eval-set.md"), valid_eval_set()).expect("eval-set");
    fs::write(refs.join("eval-baseline.json"), valid_baseline_json()).expect("baseline");
    root
}

#[cfg(unix)]
fn write_claude(bin: &Path, body: &str) {
    fs::create_dir_all(bin).expect("bin directory");
    let claude = bin.join("claude");
    fs::write(&claude, body).expect("claude fixture");
    fs::set_permissions(&claude, fs::Permissions::from_mode(0o755)).expect("claude permissions");
}

fn command_with_path(root: &Path, bin: &Path) -> Command {
    let inherited = env::var_os("PATH").unwrap_or_default();
    let path =
        env::join_paths(std::iter::once(bin.to_path_buf()).chain(env::split_paths(&inherited)))
            .expect("fixture PATH");
    let mut command = Command::cargo_bin("larch").expect("larch binary should build");
    command
        .current_dir(root)
        .env("PATH", path)
        .env("CLAUDE_PLUGIN_ROOT", root);
    command
}

/// A fake `claude` that answers research prompts with provenance-bearing prose
/// and judge prompts with a well-formed score block.
const FAKE_CLAUDE: &str = "#!/bin/sh\nbody=$(cat)\ncase \"$body\" in\n  *JUDGE_SCORE_FACTUAL*)\n    printf 'JUDGE_SCORE_FACTUAL=18\\nJUDGE_SCORE_CITATION=15\\nJUDGE_SCORE_COMPLETENESS=16\\nJUDGE_SCORE_SOURCE_QUALITY=14\\nJUDGE_SCORE_TOOL_EFFICIENCY=12\\nJUDGE_SCORE_TOTAL=75\\nJUDGE_RATIONALE=ok\\n'\n    ;;\n  *)\n    printf 'Synthesis.\\nSee src/foo.rs:10 and skills/research/references/eval-set.md.\\nRefs https://anthropic.com/x https://medium.com/y https://random.example.net/z\\nKeywords alpha beta.\\n'\n    ;;\nesac\n";

#[test]
fn eval_research_smoke_test_validates_the_fixture_bundle() {
    let root = plugin_root();
    let bin = root.path().join("bin");
    fs::create_dir_all(&bin).expect("bin");
    command_with_path(root.path(), &bin)
        .args(["eval", "research", "--smoke-test"])
        .assert()
        .success()
        .stdout(predicate::str::contains("smoke test PASS"));
}

#[cfg(unix)]
#[test]
fn eval_research_writes_a_baseline_from_launched_entries() {
    let root = plugin_root();
    let bin = root.path().join("bin");
    write_claude(&bin, FAKE_CLAUDE);
    let work = root.path().join("work");
    let out = root.path().join("baseline-out.json");

    command_with_path(root.path(), &bin)
        .args([
            "eval",
            "research",
            "--work-dir",
            &work.display().to_string(),
            "--write-baseline",
            &out.display().to_string(),
        ])
        .assert()
        .success()
        .stdout(predicate::str::contains("baseline written to"));

    let written = fs::read_to_string(&out).expect("baseline output");
    let value: serde_json::Value = serde_json::from_str(&written).expect("valid json");
    assert_eq!(value["version"], serde_json::Value::from(2));
    let entries = value["entries"].as_array().expect("entries array");
    assert_eq!(entries.len(), 20);
    // The launched research and judge both succeed, so at least one row scores.
    assert!(entries.iter().any(|entry| entry["judge_status"] == "ok"));
    assert!(entries.iter().any(|entry| entry["research_status"] == "ok"));
}

#[cfg(unix)]
#[test]
fn eval_research_prints_a_results_table_for_a_single_id() {
    let root = plugin_root();
    let bin = root.path().join("bin");
    write_claude(&bin, FAKE_CLAUDE);

    command_with_path(root.path(), &bin)
        .args(["eval", "research", "--id", "id-1"])
        .assert()
        .success()
        .stdout(predicate::str::contains("| id | category |"))
        .stdout(predicate::str::contains("id-1"));
}

#[cfg(unix)]
#[test]
fn eval_research_requires_claude_on_path() {
    let root = plugin_root();
    // A bin directory that deliberately does not contain `claude`.
    let bin = root.path().join("empty-bin");
    fs::create_dir_all(&bin).expect("bin");
    let inherited_without_claude = bin.display().to_string();
    Command::cargo_bin("larch")
        .expect("larch binary should build")
        .current_dir(root.path())
        .env("PATH", inherited_without_claude)
        .env("CLAUDE_PLUGIN_ROOT", root.path())
        .args(["eval", "research", "--id", "id-1"])
        .assert()
        .failure()
        .code(3)
        .stderr(predicate::str::contains("required tool missing: claude"));
}
