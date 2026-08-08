//! Integration coverage for Rust-owned historical implement run-log cleanup.

use std::{
    fs,
    path::{Path, PathBuf},
    process::Output,
};

use assert_cmd::Command as AssertCommand;
use serde_json::Value;

#[cfg(unix)]
use std::os::unix::fs::symlink;

struct Fixture {
    _directory: tempfile::TempDir,
    root: PathBuf,
    implement_root: PathBuf,
}

impl Fixture {
    fn new() -> Self {
        let directory = tempfile::tempdir().expect("temporary root should create");
        let root = fs::canonicalize(directory.path()).expect("temporary root should canonicalize");
        let implement_root = root.join("larch-logs/implement");
        fs::create_dir_all(&implement_root).expect("implementation root should create");
        Self {
            _directory: directory,
            root,
            implement_root,
        }
    }

    fn completed_run(&self, run_id: &str) -> PathBuf {
        self.run_with_manifest(
            run_id,
            r#"{"issue_number":8082,"status":"done","publication_mode":"disabled"}"#,
        )
    }

    fn run_with_manifest(&self, run_id: &str, manifest: &str) -> PathBuf {
        let run = self.implement_root.join(run_id);
        fs::create_dir_all(&run).expect("run directory should create");
        write(&run.join("manifest.json"), manifest);
        run
    }

    fn command(&self, arguments: &[&str]) -> Output {
        let mut command = AssertCommand::cargo_bin("larch").expect("larch binary should build");
        command
            .current_dir(&self.root)
            .arg("run-log")
            .arg("cleanup-implement-logs")
            .args(arguments);
        command.output().expect("cleanup command should launch")
    }
}

#[test]
fn dry_run_lists_the_same_changes_as_execute_without_mutating_first() {
    let fixture = Fixture::new();
    let run = fixture.completed_run("run-complete");
    write(
        &run.join("round-1/dyn-reviewer-prompt.md"),
        "dynamic prompt\n",
    );
    write(
        &run.join("round-1/dyn-reviewer-prompt.md.meta"),
        "metadata\n",
    );
    write(&run.join("round-1/dyn-reviewer-prompt.md.json"), "{}\n");
    write(&run.join("round-1/findings.md"), "findings\n");
    write(&run.join("round-1/aggregator-output.txt"), "findings\n");
    write(
        &run.join("round-1/aggregator-output.txt.meta"),
        "metadata\n",
    );
    write(&run.join("round-2/aggregator-output.txt.json"), "orphan\n");
    write(&run.join("scout-round-two-manifest.json.raw"), "raw\n");
    write(&run.join("token-report-refresh.json"), "{}\n");
    write(&run.join("token-report-refresh.json.meta"), "metadata\n");
    write(&run.join("session-transcript-refresh.txt"), "refresh\n");
    write(
        &run.join("cursor-specialist-a-output-phase1.txt"),
        "obsolete\n",
    );
    write(
        &run.join("cursor-specialist-a-output-phase1.txt.meta"),
        "metadata\n",
    );
    write(
        &run.join("cursor-specialist-a-output-ns-retry.txt"),
        "keep\n",
    );
    let transcript = concat!(
        "{\"v\":1,\"run_id\":\"run-complete\"}\n",
        "{\"role\":\"assistant\",\"blocks\":[",
        "{\"type\":\"tool_call\",\"name\":\"Edit\",",
        "\"input\":{\"file_path\":\"src/lib.rs\",\"content\":\"x\"}},",
        "{\"type\":\"tool_call\",\"name\":\"Shell\",",
        "\"input\":{\"script\":\""
    )
    .to_owned()
        + &"x".repeat(1_100)
        + "\"}}]}\nnot valid JSON\n";
    write(&run.join("session-transcript.jsonl"), &transcript);
    write(&run.join("breadcrumbs/larch-quiet-b.log"), "second\n");
    write(&run.join("breadcrumbs/larch-quiet-a.log"), "first\n");
    write(
        &run.join("code-review-tally.json"),
        r#"[{"title":"one","body":"remove","keep":true},{"body":"remove too"}]"#,
    );

    let dry_run = fixture.command(&[]);
    assert!(dry_run.status.success(), "dry run should succeed");
    let planned = paths(&dry_run.stdout, "DRY_RUN_PATH");
    assert!(
        !planned.is_empty(),
        "dry run should list every planned change"
    );
    assert!(run.join("round-1/dyn-reviewer-prompt.md").exists());
    assert!(run.join("breadcrumbs/larch-quiet-a.log").exists());

    let executed = fixture.command(&["--execute"]);
    assert!(executed.status.success(), "execute should succeed");
    assert_eq!(planned, paths(&executed.stdout, "CHANGED_PATH"));
    assert!(!run.join("round-1/dyn-reviewer-prompt.md").exists());
    assert!(!run.join("round-1/aggregator-output.txt").exists());
    assert!(!run.join("round-2/aggregator-output.txt.json").exists());
    assert!(!run.join("scout-round-two-manifest.json.raw").exists());
    assert!(!run.join("token-report-refresh.json").exists());
    assert!(!run.join("cursor-specialist-a-output-phase1.txt").exists());
    assert!(run.join("cursor-specialist-a-output-ns-retry.txt").exists());

    let transcript =
        fs::read_to_string(run.join("session-transcript.jsonl")).expect("transcript should remain");
    let lines: Vec<_> = transcript.lines().collect();
    assert_eq!(value(lines[0])["v"], 2);
    let assistant = value(lines[1]);
    let blocks = assistant["blocks"]
        .as_array()
        .expect("assistant blocks should remain");
    assert_eq!(blocks[0]["input"]["file_path"], "src/lib.rs");
    assert!(blocks[0]["input"]["input_bytes"].as_u64().is_some());
    assert!(blocks[1].get("input").is_none());
    assert!(blocks[1]["elided_input_bytes"].as_u64().is_some());
    assert_eq!(lines[2], "not valid JSON");
    assert_eq!(
        fs::read_to_string(run.join("breadcrumbs/quiet.log")).expect("quiet log should write"),
        "=== larch-quiet-a.log ===\nfirst\n=== larch-quiet-b.log ===\nsecond\n"
    );
    assert!(!run.join("breadcrumbs/larch-quiet-a.log").exists());
    let tally = value(
        &fs::read_to_string(run.join("code-review-tally.json")).expect("tally should remain"),
    );
    assert!(tally[0].get("body").is_none());
    assert!(tally[1].get("body").is_none());
    assert_eq!(tally[0]["keep"], true);
}

#[test]
fn protects_active_partial_and_unpublished_runs() {
    let fixture = Fixture::new();
    let active = fixture.run_with_manifest(
        "run-active",
        r#"{"issue_number":8082,"status":"in-progress","publication_mode":"disabled"}"#,
    );
    let partial = fixture.run_with_manifest(
        "run-partial",
        r#"{"issue_number":8082,"status":"done","publication_mode":"enabled"}"#,
    );
    write(&partial.join(".durability"), "state=pending-publication\n");
    let unpublished = fixture.run_with_manifest(
        "run-unpublished",
        r#"{"issue_number":8082,"status":"done","publication_mode":"enabled"}"#,
    );
    let corrupt = fixture.run_with_manifest(
        "run-corrupt",
        r#"{"issue_number":8082,"status":"done","publication_mode":"disabled"}"#,
    );
    write(&corrupt.join(".durability"), "not a durability marker\n");
    let unrecognized = fixture.run_with_manifest(
        "run-unrecognized",
        r#"{"issue_number":8082,"status":"done","publication_mode":"future-mode"}"#,
    );
    let committed = fixture.run_with_manifest(
        "run-committed",
        r#"{"issue_number":8082,"status":"done","publication_mode":"enabled"}"#,
    );
    write(&committed.join(".durability"), "state=committed\n");
    for run in [
        &active,
        &partial,
        &unpublished,
        &corrupt,
        &unrecognized,
        &committed,
    ] {
        write(&run.join("dyn-reviewer-prompt.md"), "obsolete\n");
    }

    let output = fixture.command(&["--execute"]);

    assert!(
        output.status.success(),
        "protected runs are skipped, not errors"
    );
    let stdout = String::from_utf8_lossy(&output.stdout);
    for run in [&active, &partial, &unpublished, &corrupt, &unrecognized] {
        assert!(
            stdout.contains(&format!("PROTECTED_RUN={}", run.display())),
            "protected run should be reported: {}",
            run.display()
        );
        assert!(run.join("dyn-reviewer-prompt.md").exists());
    }
    assert!(!committed.join("dyn-reviewer-prompt.md").exists());
}

#[test]
fn refuses_outside_or_symlinked_run_directories_without_touching_them() {
    let fixture = Fixture::new();
    let outside = fixture.root.join("outside-run");
    write(&outside.join("dyn-reviewer-prompt.md"), "outside\n");

    let outside_result = fixture.command(&[
        "--execute",
        "--run-dir",
        outside.to_str().expect("temporary path should be UTF-8"),
    ]);
    assert_eq!(outside_result.status.code(), Some(1));
    assert!(outside.join("dyn-reviewer-prompt.md").exists());

    #[cfg(unix)]
    {
        let escaped = fixture.implement_root.join("run-escaped");
        symlink(&outside, &escaped).expect("symlink should create");
        let result = fixture.command(&["--execute"]);
        assert!(result.status.success(), "unsafe corpus child is skipped");
        assert!(outside.join("dyn-reviewer-prompt.md").exists());
    }
}

#[cfg(unix)]
#[test]
fn completed_run_does_not_follow_internal_symlinks() {
    let fixture = Fixture::new();
    let run = fixture.completed_run("run-symlinked");
    let external = fixture.root.join("external");
    write(
        &external.join("dyn-escape-prompt.md"),
        "prompt stays external\n",
    );
    write(&external.join("findings.md"), "same as aggregator\n");
    write(
        &external.join("code-review-tally.json"),
        r#"[{"body":"external body"}]"#,
    );
    write(
        &external.join("larch-quiet-external.log"),
        "external breadcrumb\n",
    );
    write(&run.join("aggregator-output.txt"), "same as aggregator\n");
    symlink(
        external.join("dyn-escape-prompt.md"),
        run.join("dyn-escape-prompt.md"),
    )
    .expect("prompt symlink should create");
    symlink(external.join("findings.md"), run.join("findings.md"))
        .expect("findings symlink should create");
    symlink(
        external.join("code-review-tally.json"),
        run.join("code-review-tally.json"),
    )
    .expect("tally symlink should create");
    symlink(&external, run.join("breadcrumbs")).expect("breadcrumbs symlink should create");

    let output = fixture.command(&["--execute"]);

    assert!(output.status.success(), "unsafe nested paths are skipped");
    assert_eq!(
        fs::read_to_string(external.join("dyn-escape-prompt.md")).expect("prompt should remain"),
        "prompt stays external\n"
    );
    assert_eq!(
        fs::read_to_string(external.join("code-review-tally.json")).expect("tally should remain"),
        r#"[{"body":"external body"}]"#
    );
    assert!(external.join("larch-quiet-external.log").exists());
    assert!(!external.join("quiet.log").exists());
    assert!(
        run.join("aggregator-output.txt").exists(),
        "escaping findings symlink must not make the aggregator deletable"
    );
}

fn write(path: &Path, contents: &str) {
    fs::create_dir_all(path.parent().expect("fixture file should have parent"))
        .expect("fixture parent should create");
    fs::write(path, contents).expect("fixture file should write");
}

fn paths(output: &[u8], key: &str) -> Vec<String> {
    String::from_utf8_lossy(output)
        .lines()
        .filter_map(|line| line.strip_prefix(&format!("{key}=")))
        .map(str::to_owned)
        .collect()
}

fn value(text: &str) -> Value {
    serde_json::from_str(text).expect("fixture JSON should parse")
}
