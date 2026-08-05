use std::{fs, path::Path, process::Command};

#[cfg(unix)]
use std::os::unix::fs::PermissionsExt as _;

use assert_cmd::Command as AssertCommand;
use predicates::prelude::*;
use tempfile::TempDir;

fn larch() -> AssertCommand {
    AssertCommand::cargo_bin("larch").expect("larch binary should build")
}

fn write(path: &Path, contents: &str) {
    let parent = path.parent().expect("fixture path has parent");
    fs::create_dir_all(parent).expect("create fixture parent");
    fs::write(path, contents).expect("write fixture");
}

fn classify(plugin: &Path, diff: &Path) -> AssertCommand {
    let mut command = larch();
    command
        .env("CLAUDE_PLUGIN_ROOT", plugin)
        .args(["agent", "classify-diff"])
        .arg(diff);
    command
}

#[test]
fn classify_diff_covers_modes_mixed_changes_and_bad_manifests() {
    let fixture = TempDir::new().expect("fixture");
    let plugin = fixture.path().join("plugin");
    write(
        &plugin.join("scripts/generators.tsv"),
        "generate code-reviewer-agent\tagents/generated.md\n",
    );
    let cases = [
        ("docs", "diff --git a/docs/a.md b/docs/a.md\n", "docs-only"),
        (
            "test",
            "diff --git a/scripts/test-a.sh b/scripts/test-a.sh\n",
            "test-only",
        ),
        (
            "generated",
            "diff --git a/agents/generated.md b/agents/generated.md\n",
            "generated-only",
        ),
        (
            "mixed",
            "diff --git a/docs/a.md b/docs/a.md\ndiff --git a/scripts/test-a.sh b/scripts/test-a.sh\n",
            "generic",
        ),
        (
            "unsafe",
            "diff --git a/docs/../a.md b/docs/../a.md\n",
            "generic",
        ),
    ];
    for (name, diff, mode) in cases {
        let diff_path = fixture.path().join(format!("{name}.diff"));
        write(&diff_path, diff);
        classify(&plugin, &diff_path)
            .assert()
            .success()
            .stdout(format!("DIFF_MODE={mode}\n"));
    }

    let missing_plugin = fixture.path().join("missing-plugin");
    let diff_path = fixture.path().join("missing.diff");
    write(&diff_path, "diff --git a/docs/a.md b/docs/a.md\n");
    classify(&missing_plugin, &diff_path)
        .assert()
        .code(1)
        .stderr(predicate::str::contains(
            "scripts/generators.tsv is missing or unsafe",
        ));
    write(&plugin.join("scripts/generators.tsv"), "generate\t \n");
    classify(&plugin, &diff_path)
        .assert()
        .code(1)
        .stderr(predicate::str::contains(
            "contains an empty required column",
        ));
}

#[test]
fn wait_reviewers_preserves_validation_and_completion_rows() {
    let fixture = TempDir::new().expect("fixture");
    let done = fixture.path().join("done.done");
    let empty = fixture.path().join("empty.done");
    let missing = fixture.path().join("missing.done");
    write(&done, "0\n");
    write(&empty, "\n");
    larch()
        .env("WAIT_FOR_REVIEWERS_POLL_INTERVAL", "0.01")
        .args(["agent", "wait-reviewers", "--timeout", "1"])
        .arg(&done)
        .arg(&empty)
        .arg(&missing)
        .assert()
        .success()
        .stdout("DONE 1 done: exit=0\nDONE 2 empty: exit=unknown\nTIMEOUT 3 missing\n");
    larch()
        .args(["agent", "wait-reviewers", "--timeout", "00"])
        .arg(&done)
        .assert()
        .code(1)
        .stderr(predicate::str::contains("must be a positive integer"));
    for invalid_timeout in ["0", "000", "abc"] {
        larch()
            .args(["agent", "wait-reviewers", "--timeout", invalid_timeout])
            .arg(&done)
            .assert()
            .code(1)
            .stderr(predicate::str::contains("must be a positive integer"));
    }
    larch()
        .env("WAIT_FOR_REVIEWERS_POLL_INTERVAL", "00")
        .args(["agent", "wait-reviewers"])
        .arg(&done)
        .assert()
        .code(1)
        .stderr(predicate::str::contains("WAIT_FOR_REVIEWERS_POLL_INTERVAL"));
}

#[test]
fn compose_collector_failure_log_redacts_and_writes_sections() {
    let fixture = TempDir::new().expect("fixture");
    let reviewer = fixture.path().join("reviewer.txt");
    let secret = format!("sk-{}", "a".repeat(24));
    let session_path = fixture.path().join("larch-implement-redact123");
    write(&reviewer, "reviewer body\n");
    write(&fixture.path().join("reviewer.txt.diag"), "diag body\n");
    write(
        &fixture.path().join("reviewer.txt.launch-stderr"),
        &format!("line one {} {secret}\nline two\n", session_path.display()),
    );
    write(
        &fixture.path().join("reviewer.txt.stderr-tail"),
        &"é".repeat(6_000),
    );
    let output = fixture.path().join("failure.log");
    larch()
        .args(["agent", "compose-collector-failure-log", "--reviewer-file"])
        .arg(&reviewer)
        .args(["--structured-record", "STATUS=FAILED", "--output"])
        .arg(&output)
        .assert()
        .success();
    let body = fs::read_to_string(&output).expect("collector output");
    assert!(body.contains("## Structured collector record"));
    assert!(body.contains("reviewer body"));
    assert!(body.contains("diag body"));
    assert!(!body.contains(&secret));
    assert!(!body.contains(&session_path.display().to_string()));
    assert!(body.contains("<REDACTED-TOKEN>"));
    assert!(body.len() < 6_000, "stderr tails must remain bounded");
    #[cfg(unix)]
    assert_eq!(
        fs::metadata(&output)
            .expect("output metadata")
            .permissions()
            .mode()
            & 0o777,
        0o600
    );
    larch()
        .args([
            "agent",
            "compose-collector-failure-log",
            "--structured-record",
            "",
        ])
        .arg("--output")
        .arg(fixture.path().join("bad.log"))
        .assert()
        .code(2)
        .stderr(predicate::str::contains("required and non-empty"));
    larch()
        .args([
            "agent",
            "compose-collector-failure-log",
            "--structured-record",
            "STATUS=FAILED",
            "--output",
            "",
        ])
        .assert()
        .code(2)
        .stderr(predicate::str::contains("--output is required"));
}

fn git_output(repository: &Path, arguments: &[&str]) -> std::process::Output {
    let output = Command::new("git")
        .args(arguments)
        .current_dir(repository)
        .output()
        .expect("run fixture git");
    assert!(
        output.status.success(),
        "git {:?} failed: {}",
        arguments,
        String::from_utf8_lossy(&output.stderr)
    );
    output
}

fn git(repository: &Path, arguments: &[&str]) {
    let _ = git_output(repository, arguments);
}

fn git_stdout(repository: &Path, arguments: &[&str]) -> String {
    String::from_utf8(git_output(repository, arguments).stdout).expect("UTF-8 git stdout")
}

fn commit(repository: &Path, path: &str, contents: &str, message: &str) {
    write(&repository.join(path), contents);
    git(repository, &["add", path]);
    git(repository, &["commit", "-m", message]);
}

#[test]
fn gather_branch_context_excludes_larch_logs() {
    let fixture = TempDir::new().expect("fixture");
    let repository = fixture.path().join("repository");
    fs::create_dir(&repository).expect("repository dir");
    git(&repository, &["init", "-b", "main"]);
    git(&repository, &["config", "user.email", "test@example.com"]);
    git(&repository, &["config", "user.name", "Test User"]);
    commit(&repository, "src/feature.txt", "v1\n", "base code");
    git(&repository, &["checkout", "-b", "feature"]);
    commit(
        &repository,
        "larch-logs/run/session.txt",
        "run log\n",
        "add run log",
    );
    commit(&repository, "src/feature.txt", "v1\nv2\n", "feature change");
    let output = fixture.path().join("context");
    fs::create_dir(&output).expect("context dir");
    larch()
        .current_dir(&repository)
        .args(["agent", "gather-branch-context", "--output-dir"])
        .arg(&output)
        .assert()
        .success()
        .stdout(predicate::str::contains("COMMIT_COUNT=1"));
    let diff = fs::read_to_string(output.join("diff.txt")).expect("diff");
    let files = fs::read_to_string(output.join("file-list.txt")).expect("file list");
    let commits = fs::read_to_string(output.join("commit-log.txt")).expect("commit log");
    assert!(diff.contains("src/feature.txt"));
    assert!(files.contains("src/feature.txt"));
    assert!(commits.contains("feature change"));
    assert!(!diff.contains("larch-logs"));
    assert!(!files.contains("larch-logs"));
    assert!(!commits.contains("add run log"));
}

#[test]
fn gather_branch_context_prefers_origin_main_when_local_main_is_stale() {
    let fixture = TempDir::new().expect("fixture");
    let origin = fixture.path().join("origin.git");
    git(
        fixture.path(),
        &[
            "init",
            "--bare",
            "-b",
            "main",
            origin.to_str().expect("origin path"),
        ],
    );
    let repository = fixture.path().join("repository");
    fs::create_dir(&repository).expect("repository dir");
    git(&repository, &["init", "-b", "main"]);
    git(&repository, &["config", "user.email", "test@example.com"]);
    git(&repository, &["config", "user.name", "Test User"]);
    git(
        &repository,
        &[
            "remote",
            "add",
            "origin",
            origin.to_str().expect("origin path"),
        ],
    );
    commit(&repository, "feature.txt", "v1\n", "base A");
    git(&repository, &["push", "origin", "main"]);
    let base_a = git_stdout(&repository, &["rev-parse", "HEAD"])
        .trim()
        .to_owned();
    git(&repository, &["checkout", "-b", "feature"]);
    commit(
        &repository,
        "feature.txt",
        "v1\nfeature-edit\n",
        "feature change",
    );
    git(&repository, &["checkout", "main"]);
    commit(
        &repository,
        "unrelated.txt",
        "other-pr\n",
        "unrelated PR merged to main",
    );
    let base_b = git_stdout(&repository, &["rev-parse", "HEAD"])
        .trim()
        .to_owned();
    git(&repository, &["push", "origin", "main"]);
    git(&repository, &["reset", "--hard", &base_a]);
    git(&repository, &["checkout", "feature"]);
    git(&repository, &["rebase", &base_b]);
    git(&repository, &["fetch", "origin", "main"]);

    let output = fixture.path().join("context");
    fs::create_dir(&output).expect("context dir");
    larch()
        .current_dir(&repository)
        .args(["agent", "gather-branch-context", "--output-dir"])
        .arg(&output)
        .assert()
        .success()
        .stdout(predicate::str::contains("COMMIT_COUNT=1"));
    let diff = fs::read_to_string(output.join("diff.txt")).expect("diff");
    let files = fs::read_to_string(output.join("file-list.txt")).expect("file list");
    let commits = fs::read_to_string(output.join("commit-log.txt")).expect("commit log");
    assert!(files.contains("feature.txt"));
    assert!(commits.contains("feature change"));
    assert!(!files.contains("unrelated.txt"));
    assert!(!diff.contains("unrelated.txt"));
    assert!(!commits.contains("unrelated PR merged to main"));
}
