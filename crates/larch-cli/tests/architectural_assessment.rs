//! Black-box contract coverage for the four `architectural-assessment` verbs.
//!
//! Exercises materialize usage and failure, submit gates, sanitize-detail
//! redaction, and final-report-sections fail-soft empty output.

#![cfg(unix)]

use std::{
    fs,
    path::{Path, PathBuf},
    process::Command as StdCommand,
};

use assert_cmd::Command as AssertCommand;
use tempfile::TempDir;

fn larch(root: &Path) -> AssertCommand {
    let mut command = AssertCommand::cargo_bin("larch").expect("larch binary should build");
    command.current_dir(root);
    command.env_remove("REPO");
    command.env_remove("IMPLEMENT_TMPDIR");
    command
}

fn git(cwd: &Path, args: &[&str]) {
    let completed = StdCommand::new("/usr/bin/git")
        .args(args)
        .current_dir(cwd)
        .output()
        .expect("git");
    assert!(
        completed.status.success(),
        "git {:?} failed: {}",
        args,
        String::from_utf8_lossy(&completed.stderr)
    );
}

fn real_repo_with_origin_main(tmp: &Path) -> (PathBuf, String) {
    let repo = tmp.join("repo");
    fs::create_dir_all(&repo).expect("repo");
    git(&repo, &["init"]);
    git(&repo, &["config", "user.name", "Larch Test"]);
    git(&repo, &["config", "user.email", "larch@example.invalid"]);
    fs::write(repo.join("README.md"), "base\n").expect("readme");
    git(&repo, &["add", "README.md"]);
    git(&repo, &["commit", "-m", "base"]);
    git(&repo, &["branch", "-M", "main"]);
    git(&repo, &["update-ref", "refs/remotes/origin/main", "HEAD"]);
    let head = StdCommand::new("/usr/bin/git")
        .args(["rev-parse", "HEAD"])
        .current_dir(&repo)
        .output()
        .expect("rev-parse");
    assert!(head.status.success());
    let sha = String::from_utf8_lossy(&head.stdout).trim().to_owned();
    (repo, sha)
}

fn stdout_of(assert: &assert_cmd::assert::Assert) -> String {
    String::from_utf8_lossy(&assert.get_output().stdout).into_owned()
}

#[test]
fn materialize_usage_error_without_kind() {
    let root = TempDir::new().expect("temp");
    let assertion = larch(root.path())
        .args([
            "architectural-assessment",
            "materialize",
            "--repo-root",
            root.path().to_str().expect("utf8"),
            "--implement-tmpdir",
            root.path().to_str().expect("utf8"),
        ])
        .assert()
        .code(2);
    let out = stdout_of(&assertion);
    assert!(
        out.lines()
            .next()
            .is_some_and(|line| line == "ASSESSMENT_MATERIALIZE_STATUS=usage-error"),
        "{out}"
    );
}

#[test]
fn materialize_usage_error_without_paths() {
    let root = TempDir::new().expect("temp");
    let assertion = larch(root.path())
        .args([
            "architectural-assessment",
            "materialize",
            "--kind",
            "guidelines",
        ])
        .assert()
        .code(2);
    let out = stdout_of(&assertion);
    assert!(
        out.contains("ASSESSMENT_MATERIALIZE_STATUS=usage-error"),
        "{out}"
    );
    assert!(out.contains("ASSESSMENT_DETAIL="), "{out}");
}

#[test]
fn materialize_fails_or_usage_on_fake_dirs() {
    let root = TempDir::new().expect("temp");
    let missing = root.path().join("missing-repo");
    let tmpdir = root.path().join("implement");
    fs::create_dir_all(&tmpdir).expect("tmpdir");
    let assertion = larch(root.path())
        .args([
            "architectural-assessment",
            "materialize",
            "--kind",
            "guidelines",
            "--repo-root",
            missing.to_str().expect("utf8"),
            "--implement-tmpdir",
            tmpdir.to_str().expect("utf8"),
        ])
        .assert();
    let code = assertion.get_output().status.code().unwrap_or(255);
    assert!(
        code == 1 || code == 2,
        "expected failed(1) or usage(2), got {code}"
    );
    let out = stdout_of(&assertion);
    assert!(
        out.contains("ASSESSMENT_MATERIALIZE_STATUS=failed")
            || out.contains("ASSESSMENT_MATERIALIZE_STATUS=usage-error"),
        "{out}"
    );
}

#[test]
fn materialize_docs_only_diff_is_deterministic_clean() {
    let root = TempDir::new().expect("temp");
    let (repo, _head) = real_repo_with_origin_main(root.path());
    fs::write(
        repo.join("ARCHITECTURAL_GUIDELINES.md"),
        "### G-Py-4: Fail loudly\n",
    )
    .expect("guidelines");
    git(&repo, &["add", "ARCHITECTURAL_GUIDELINES.md"]);
    git(&repo, &["commit", "-m", "guidelines knowledge"]);
    git(&repo, &["update-ref", "refs/remotes/origin/main", "HEAD"]);
    fs::create_dir_all(repo.join("docs")).expect("docs");
    fs::write(repo.join("docs/a.md"), "docs\n").expect("docs file");
    git(&repo, &["add", "docs/a.md"]);
    git(&repo, &["commit", "-m", "docs only"]);
    let tmpdir = root.path().join("implement");
    fs::create_dir_all(&tmpdir).expect("tmpdir");

    let assertion = larch(root.path())
        .args([
            "architectural-assessment",
            "materialize",
            "--kind",
            "guidelines",
            "--repo-root",
            repo.to_str().expect("utf8"),
            "--implement-tmpdir",
            tmpdir.to_str().expect("utf8"),
        ])
        .assert()
        .success();
    let out = stdout_of(&assertion);
    assert!(out.contains("ASSESSMENT_MATERIALIZE_STATUS=ok"), "{out}");
    assert!(
        out.contains("ASSESSMENT_DETERMINISTIC_KINDS=guidelines"),
        "{out}"
    );
    assert!(
        out.lines().any(|line| line == "ASSESSMENT_PENDING_KINDS="),
        "{out}"
    );
}

#[test]
fn materialize_code_diff_is_pending() {
    let root = TempDir::new().expect("temp");
    let (repo, _head) = real_repo_with_origin_main(root.path());
    fs::write(repo.join("app.py"), "print('hi')\n").expect("code");
    fs::write(
        repo.join("ARCHITECTURAL_GUIDELINES.md"),
        "### G-Py-4: Fail loudly\n",
    )
    .expect("guidelines");
    git(&repo, &["add", "app.py", "ARCHITECTURAL_GUIDELINES.md"]);
    git(&repo, &["commit", "-m", "code"]);
    let tmpdir = root.path().join("implement");
    fs::create_dir_all(&tmpdir).expect("tmpdir");

    let assertion = larch(root.path())
        .args([
            "architectural-assessment",
            "materialize",
            "--kind",
            "guidelines",
            "--repo-root",
            repo.to_str().expect("utf8"),
            "--implement-tmpdir",
            tmpdir.to_str().expect("utf8"),
        ])
        .assert()
        .success();
    let out = stdout_of(&assertion);
    assert!(out.contains("ASSESSMENT_MATERIALIZE_STATUS=ok"), "{out}");
    assert!(out.contains("ASSESSMENT_PENDING_KINDS=guidelines"), "{out}");
    assert!(
        out.contains("ASSESSMENT_KIND_GUIDELINES_DIFF_PATH="),
        "{out}"
    );
    assert!(
        out.contains("ASSESSMENT_KIND_GUIDELINES_KNOWLEDGE_PATH="),
        "{out}"
    );
    assert!(
        out.contains("ASSESSMENT_KIND_GUIDELINES_HEAD_SHA="),
        "{out}"
    );
    assert!(
        out.contains("ASSESSMENT_KIND_GUIDELINES_DIFF_FINGERPRINT="),
        "{out}"
    );
}

#[test]
fn sanitize_detail_redacts_tmpdir_flattens_and_truncates() {
    let root = TempDir::new().expect("temp");
    let tmpdir = root.path().join("implement");
    fs::create_dir_all(&tmpdir).expect("tmpdir");
    let token = format!("ghp_{}", "x".repeat(30));
    let input = format!("first\n{}\t{token}", tmpdir.display());

    let assertion = larch(root.path())
        .args([
            "architectural-assessment",
            "sanitize-detail",
            "--implement-tmpdir",
            tmpdir.to_str().expect("utf8"),
        ])
        .write_stdin(input)
        .assert()
        .success();
    let out = stdout_of(&assertion);
    assert_eq!(out.matches('\n').count(), 1, "{out:?}");
    assert!(!out.contains(tmpdir.to_str().expect("utf8")), "{out}");
    assert!(!out.contains(&token), "{out}");
    assert!(out.contains("<implement-tmpdir>"), "{out}");
    assert!(out.contains("<REDACTED-TOKEN>"), "{out}");
    assert!(out.starts_with("first <implement-tmpdir>"), "{out}");
}

#[test]
fn sanitize_detail_rejects_invalid_implement_tmpdir() {
    let root = TempDir::new().expect("temp");
    let missing = root.path().join("no-such-dir");
    larch(root.path())
        .args([
            "architectural-assessment",
            "sanitize-detail",
            "--implement-tmpdir",
            missing.to_str().expect("utf8"),
        ])
        .write_stdin("secret\n")
        .assert()
        .code(2);
}

#[test]
fn submit_usage_error_when_required_missing() {
    let root = TempDir::new().expect("temp");
    larch(root.path())
        .args(["architectural-assessment", "submit"])
        .assert()
        .code(2);
}

#[test]
fn submit_rejects_documented_exception_without_allow_flag() {
    let root = TempDir::new().expect("temp");
    let (repo, _head) = real_repo_with_origin_main(root.path());
    fs::write(repo.join("app.py"), "print('hi')\n").expect("code");
    fs::write(
        repo.join("ARCHITECTURAL_GUIDELINES.md"),
        "### G-Py-4: Fail loudly\n",
    )
    .expect("guidelines");
    git(&repo, &["add", "app.py", "ARCHITECTURAL_GUIDELINES.md"]);
    git(&repo, &["commit", "-m", "code"]);
    let tmpdir = root.path().join("implement");
    fs::create_dir_all(&tmpdir).expect("tmpdir");

    larch(root.path())
        .args([
            "architectural-assessment",
            "materialize",
            "--kind",
            "guidelines",
            "--repo-root",
            repo.to_str().expect("utf8"),
            "--implement-tmpdir",
            tmpdir.to_str().expect("utf8"),
        ])
        .assert()
        .success();

    let note = tmpdir.join("assessment-note-guidelines.md");
    fs::write(
        &note,
        "G-Py-4 applies.\nException: pragmatic (author: main-agent, date: 2026-07-13)\n",
    )
    .expect("note");

    let assertion = larch(root.path())
        .args([
            "architectural-assessment",
            "submit",
            "--kind",
            "guidelines",
            "--state",
            "deviation",
            "--note-file",
            note.to_str().expect("utf8"),
            "--repo-root",
            repo.to_str().expect("utf8"),
            "--implement-tmpdir",
            tmpdir.to_str().expect("utf8"),
        ])
        .assert()
        .code(1);
    let out = stdout_of(&assertion);
    assert!(out.contains("ASSESSMENT_STATUS=failed"), "{out}");
    assert!(
        out.contains("documented-exception") || out.contains("allow-exception"),
        "{out}"
    );
}

#[test]
fn final_report_sections_empty_when_notes_missing() {
    let root = TempDir::new().expect("temp");
    let tmpdir = root.path().join("implement");
    fs::create_dir_all(&tmpdir).expect("tmpdir");
    let assertion = larch(root.path())
        .args([
            "architectural-assessment",
            "final-report-sections",
            "--implement-tmpdir",
            tmpdir.to_str().expect("utf8"),
        ])
        .assert()
        .success();
    assert_eq!(stdout_of(&assertion), "");
}

#[test]
fn final_report_sections_renders_after_deterministic_clean_materialize() {
    let root = TempDir::new().expect("temp");
    let (repo, _initial_head) = real_repo_with_origin_main(root.path());
    fs::write(
        repo.join("ARCHITECTURAL_GUIDELINES.md"),
        "### G-Py-4: Fail loudly\n",
    )
    .expect("guidelines");
    git(&repo, &["add", "ARCHITECTURAL_GUIDELINES.md"]);
    git(&repo, &["commit", "-m", "guidelines knowledge"]);
    git(&repo, &["update-ref", "refs/remotes/origin/main", "HEAD"]);
    fs::create_dir_all(repo.join("docs")).expect("docs");
    fs::write(repo.join("docs/a.md"), "docs\n").expect("docs file");
    git(&repo, &["add", "docs/a.md"]);
    git(&repo, &["commit", "-m", "docs only"]);
    let tmpdir = root.path().join("implement");
    fs::create_dir_all(&tmpdir).expect("tmpdir");

    larch(&repo)
        .args([
            "architectural-assessment",
            "materialize",
            "--kind",
            "guidelines",
            "--repo-root",
            repo.to_str().expect("utf8"),
            "--implement-tmpdir",
            tmpdir.to_str().expect("utf8"),
        ])
        .assert()
        .success();

    // final-report-sections resolves HEAD from cwd via gix discover.
    let assertion = larch(&repo)
        .args([
            "architectural-assessment",
            "final-report-sections",
            "--implement-tmpdir",
            tmpdir.to_str().expect("utf8"),
        ])
        .assert()
        .success();
    let out = stdout_of(&assertion);
    assert!(out.contains("## Architectural guidelines"), "{out}");
    assert!(out.contains("no deviations identified"), "{out}");
}

#[test]
fn submit_rejects_empty_note_file() {
    let root = TempDir::new().expect("temp");
    let (repo, _head) = real_repo_with_origin_main(root.path());
    fs::write(repo.join("app.py"), "print('hi')\n").expect("code");
    fs::write(
        repo.join("ARCHITECTURAL_GUIDELINES.md"),
        "### G-Py-4: Fail loudly\n",
    )
    .expect("guidelines");
    git(&repo, &["add", "app.py", "ARCHITECTURAL_GUIDELINES.md"]);
    git(&repo, &["commit", "-m", "code"]);
    let tmpdir = root.path().join("implement");
    fs::create_dir_all(&tmpdir).expect("tmpdir");

    larch(root.path())
        .args([
            "architectural-assessment",
            "materialize",
            "--kind",
            "guidelines",
            "--repo-root",
            repo.to_str().expect("utf8"),
            "--implement-tmpdir",
            tmpdir.to_str().expect("utf8"),
        ])
        .assert()
        .success();

    let note = tmpdir.join("empty-note.md");
    fs::write(&note, "   \n").expect("empty note");
    let assertion = larch(root.path())
        .args([
            "architectural-assessment",
            "submit",
            "--kind",
            "guidelines",
            "--state",
            "deviation",
            "--note-file",
            note.to_str().expect("utf8"),
            "--repo-root",
            repo.to_str().expect("utf8"),
            "--implement-tmpdir",
            tmpdir.to_str().expect("utf8"),
        ])
        .assert()
        .code(1);
    let out = stdout_of(&assertion);
    assert!(out.contains("ASSESSMENT_STATUS=failed"), "{out}");
    assert!(
        out.contains("empty") || out.contains("oversized") || out.contains("ASSESSMENT_DETAIL="),
        "{out}"
    );
}
