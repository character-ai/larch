//! Black-box parity for the six architectural preparation commands (#8794).
//!
//! The cases pin the retired Python argv, stdout, exit, invalidation, frozen
//! diff, and metadata contracts through the released Rust binary.

#![cfg(unix)]

use std::{
    fs,
    path::{Path, PathBuf},
    process::Command as StdCommand,
};

use assert_cmd::Command as AssertCommand;
use sha2::{Digest as _, Sha256};
use tempfile::TempDir;

fn larch(root: &Path) -> AssertCommand {
    let mut command = AssertCommand::cargo_bin("larch").expect("larch binary should build");
    command.current_dir(root);
    command.env_remove("CLAUDE_PROJECT_DIR");
    command.env_remove("IMPLEMENT_TMPDIR");
    command
}

fn git(cwd: &Path, arguments: &[&str]) -> String {
    let completed = StdCommand::new("/usr/bin/git")
        .args(arguments)
        .current_dir(cwd)
        .output()
        .expect("git");
    assert!(
        completed.status.success(),
        "git {arguments:?} failed: {}",
        String::from_utf8_lossy(&completed.stderr)
    );
    String::from_utf8_lossy(&completed.stdout).trim().to_owned()
}

fn repository(tmp: &Path) -> PathBuf {
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
    git(&repo, &["update-ref", "refs/remotes/upstream/main", "HEAD"]);
    repo.canonicalize().expect("canonical repo")
}

fn commit(repo: &Path, paths: &[&str], message: &str) -> String {
    let mut add = vec!["add"];
    add.extend(paths);
    git(repo, &add);
    git(repo, &["commit", "-m", message]);
    git(repo, &["rev-parse", "HEAD"])
}

fn stdout(assertion: &assert_cmd::assert::Assert) -> String {
    String::from_utf8_lossy(&assertion.get_output().stdout).into_owned()
}

#[test]
fn help_matches_retired_argparse_for_each_domain_and_verb() {
    let root = TempDir::new().expect("temp");
    for domain in ["architectural-guidelines", "architectural-invariants"] {
        for verb in ["materialize-diff", "prepare", "prepare-compose"] {
            let assertion = larch(root.path())
                .args([domain, verb, "--help"])
                .assert()
                .success();
            let output = stdout(&assertion);
            let indent = " ".repeat(format!("usage: {domain} {verb} ").len());
            let expected = if verb == "prepare-compose" {
                format!(
                    "usage: {domain} {verb} [-h] [--repo-root REPO_ROOT]\n\
                     {indent}[--forked-target FORKED_TARGET]\n\
                     {indent}[--implement-tmpdir IMPLEMENT_TMPDIR]\n\
                     {indent}[--expected-head-sha EXPECTED_HEAD_SHA]\n\n\
                     options:\n  -h, --help            show this help message and exit\n  --repo-root REPO_ROOT\n  --forked-target FORKED_TARGET\n  --implement-tmpdir IMPLEMENT_TMPDIR\n  --expected-head-sha EXPECTED_HEAD_SHA\n"
                )
            } else {
                format!(
                    "usage: {domain} {verb} [-h] [--repo-root REPO_ROOT]\n\
                     {indent}[--forked-target FORKED_TARGET]\n\
                     {indent}[--output OUTPUT]\n\
                     {indent}[--implement-tmpdir IMPLEMENT_TMPDIR]\n\n\
                     options:\n  -h, --help            show this help message and exit\n  --repo-root REPO_ROOT\n  --forked-target FORKED_TARGET\n  --output OUTPUT\n  --implement-tmpdir IMPLEMENT_TMPDIR\n"
                )
            };
            assert_eq!(output, expected, "{domain} {verb}");
        }
    }
}

#[test]
fn gate_c_read_and_present_help_matches_retired_argparse() {
    let root = TempDir::new().expect("temp");
    for domain in ["architectural-guidelines", "architectural-invariants"] {
        for verb in ["read", "present-note"] {
            let assertion = larch(root.path())
                .args([domain, verb, "--help"])
                .assert()
                .success();
            let command = format!("{domain} {verb}");
            let indent = " ".repeat(format!("usage: {command} ").len());
            let expected = if verb == "read" {
                format!(
                    "usage: {command} [-h] [--repo-root REPO_ROOT]\n\n\
                     options:\n  -h, --help            show this help message and exit\n  --repo-root REPO_ROOT\n"
                )
            } else {
                format!(
                    "usage: {command} [-h] [--repo-root REPO_ROOT]\n\
                     {indent}[--assessment {{pending,clean}}]\n\n\
                     options:\n  -h, --help            show this help message and exit\n  --repo-root REPO_ROOT\n  --assessment {{pending,clean}}\n"
                )
            };
            assert_eq!(stdout(&assertion), expected, "{domain} {verb}");
        }
    }
}

#[test]
fn gate_c_read_and_present_note_preserve_status_and_empty_asymmetry() {
    let root = TempDir::new().expect("temp");
    let repo = repository(root.path());

    let absent = larch(root.path())
        .args([
            "architectural-guidelines",
            "read",
            "--repo-root",
            repo.to_str().expect("utf8"),
        ])
        .assert()
        .success();
    assert_eq!(stdout(&absent), "ARCHITECTURAL_GUIDELINES_STATUS=absent\n");

    fs::write(
        repo.join("ARCHITECTURAL_GUIDELINES.md"),
        "### G-Test-1: Escape <xml>\n- Why: parity\n- Deviate when: never\n",
    )
    .expect("guidelines");
    let read = larch(root.path())
        .args([
            "architectural-guidelines",
            "read",
            "--repo-root",
            repo.to_str().expect("utf8"),
        ])
        .assert()
        .success();
    let read_output = stdout(&read);
    assert!(
        read_output.starts_with(&format!(
            "ARCHITECTURAL_GUIDELINES_STATUS=present\nARCHITECTURAL_GUIDELINES_PATH={}\n",
            repo.join("ARCHITECTURAL_GUIDELINES.md").display()
        )),
        "{read_output}"
    );
    assert!(read_output.contains("### G-Test-1: Escape &lt;xml&gt;"));
    assert!(read_output.contains("- Why: parity\n- Deviate when: never"));

    let pending = larch(root.path())
        .args([
            "architectural-guidelines",
            "present-note",
            "--repo-root",
            repo.to_str().expect("utf8"),
        ])
        .assert()
        .success();
    let pending_output = stdout(&pending);
    assert!(pending_output.contains("GUIDELINES_DEVIATION_ASSESSMENT_REQUIRED=true\n"));
    assert!(pending_output.contains("<architectural_guidelines encoding=\"literal-redacted\">"));

    let clean = larch(root.path())
        .args([
            "architectural-guidelines",
            "present-note",
            "--repo-root",
            repo.to_str().expect("utf8"),
            "--assessment",
            "clean",
        ])
        .assert()
        .success();
    assert_eq!(
        stdout(&clean),
        "Consulted ARCHITECTURAL_GUIDELINES.md; no deviations identified.\n"
    );

    fs::write(
        repo.join("ARCHITECTURAL_INVARIANTS.md"),
        "# No parseable invariant entries\n",
    )
    .expect("invariants");
    let empty_pending = larch(root.path())
        .args([
            "architectural-invariants",
            "present-note",
            "--repo-root",
            repo.to_str().expect("utf8"),
        ])
        .assert()
        .success();
    assert_eq!(
        stdout(&empty_pending),
        format!(
            "ARCHITECTURAL_INVARIANTS_PATH={}\n",
            repo.join("ARCHITECTURAL_INVARIANTS.md").display()
        )
    );
    let empty_clean = larch(root.path())
        .args([
            "architectural-invariants",
            "present-note",
            "--repo-root",
            repo.to_str().expect("utf8"),
            "--assessment",
            "clean",
        ])
        .assert()
        .success();
    assert_eq!(stdout(&empty_clean), "");
}

#[test]
fn prepare_guidelines_emits_redacted_knowledge_and_persists_diff() {
    let root = TempDir::new().expect("temp");
    let repo = repository(root.path());
    let token = format!("sk-{}", "A".repeat(24));
    fs::write(
        repo.join("ARCHITECTURAL_GUIDELINES.md"),
        format!("### G-Test-1: Escape <xml>\n- Why: protect {token}\n- Deviate when: never\n"),
    )
    .expect("guidelines");
    fs::write(repo.join("README.md"), "base\nchange\n").expect("change");
    let _head = commit(
        &repo,
        &["ARCHITECTURAL_GUIDELINES.md", "README.md"],
        "change",
    );
    let implement = root.path().join("implement");
    fs::create_dir_all(&implement).expect("implement");
    for stale in [
        "architectural-guideline-staged-assessment.md",
        "architectural-guideline-staged-assessment.env",
        "architectural-guideline-note.md",
        "architectural-guideline-note.meta.env",
    ] {
        fs::write(implement.join(stale), "stale\n").expect("stale");
    }

    let assertion = larch(root.path())
        .args([
            "architectural-guidelines",
            "prepare",
            "--repo-root",
            repo.to_str().expect("utf8"),
            "--implement-tmpdir",
            implement.to_str().expect("utf8"),
        ])
        .assert()
        .success();
    let output = stdout(&assertion);
    assert!(
        output.contains("ARCHITECTURAL_GUIDELINES_STATUS=present\n"),
        "{output}"
    );
    assert!(
        output.contains(&format!(
            "ARCHITECTURAL_GUIDELINES_PATH={}",
            repo.join("ARCHITECTURAL_GUIDELINES.md").display()
        )),
        "{output}"
    );
    assert!(output.contains("&lt;xml&gt;"), "{output}");
    assert!(output.contains("&lt;REDACTED-TOKEN&gt;"), "{output}");
    assert!(!output.contains(&token), "{output}");
    assert!(
        output.contains("ARCHITECTURAL_GUIDELINES_DIFF_STATUS=ok\n"),
        "{output}"
    );
    assert!(
        output.contains("ARCHITECTURAL_GUIDELINES_BASE_REF=origin/main\n"),
        "{output}"
    );
    assert!(output.contains("+change"), "{output}");

    let diff_path = implement.join("architectural-guideline-materialized-diff.txt");
    let diff = fs::read_to_string(&diff_path).expect("diff");
    let fingerprint = format!("{:x}", Sha256::digest(diff.as_bytes()));
    let metadata = fs::read_to_string(implement.join("architectural-guideline-materialize.env"))
        .expect("metadata");
    assert_eq!(
        metadata,
        format!("BASE_REF=origin/main\nDIFF_FINGERPRINT={fingerprint}\n")
    );
    assert!(output.contains(&format!(
        "ARCHITECTURAL_GUIDELINES_DIFF_FINGERPRINT={fingerprint}\n"
    )));
    for stale in [
        "architectural-guideline-staged-assessment.md",
        "architectural-guideline-staged-assessment.env",
        "architectural-guideline-note.md",
        "architectural-guideline-note.meta.env",
    ] {
        assert!(!implement.join(stale).exists(), "{stale} survived");
    }
}

#[test]
fn invariant_prepare_present_empty_skips_diff() {
    let root = TempDir::new().expect("temp");
    let repo = repository(root.path());
    fs::write(
        repo.join("ARCHITECTURAL_INVARIANTS.md"),
        "No parseable invariant entries.\n",
    )
    .expect("invariants");

    let assertion = larch(root.path())
        .args([
            "architectural-invariants",
            "prepare",
            "--repo-root",
            repo.to_str().expect("utf8"),
        ])
        .assert()
        .success();
    let output = stdout(&assertion);
    assert!(
        output.contains("ARCHITECTURAL_INVARIANTS_STATUS=present\n"),
        "{output}"
    );
    assert!(
        !output.contains("ARCHITECTURAL_INVARIANTS_DIFF_STATUS"),
        "{output}"
    );
}

#[test]
fn prepare_preserves_absent_invalid_and_diff_failure_envelopes() {
    let root = TempDir::new().expect("temp");
    let repo = repository(root.path());

    let absent = larch(root.path())
        .args([
            "architectural-guidelines",
            "prepare",
            "--repo-root",
            repo.to_str().expect("utf8"),
        ])
        .assert()
        .success();
    assert_eq!(stdout(&absent), "ARCHITECTURAL_GUIDELINES_STATUS=absent\n");

    let outside = root.path().join("outside-guidelines.md");
    fs::write(&outside, "### G-Test-1: Outside\n").expect("outside");
    let knowledge = repo.join("ARCHITECTURAL_GUIDELINES.md");
    std::os::unix::fs::symlink(&outside, &knowledge).expect("symlink");
    let invalid = larch(root.path())
        .args([
            "architectural-guidelines",
            "prepare",
            "--repo-root",
            repo.to_str().expect("utf8"),
        ])
        .assert()
        .success();
    let output = stdout(&invalid);
    assert!(output.starts_with("ARCHITECTURAL_GUIDELINES_STATUS=invalid\n"));
    assert!(output.contains("symlinks are not read"), "{output}");
    assert!(!output.contains("ARCHITECTURAL_GUIDELINES_DIFF_STATUS"));

    fs::remove_file(&knowledge).expect("remove symlink");
    fs::write(
        &knowledge,
        "### G-Test-1: Keep failures visible\n- Why: parity\n",
    )
    .expect("guidelines");
    git(&repo, &["update-ref", "-d", "refs/remotes/origin/main"]);
    let failed = larch(root.path())
        .args([
            "architectural-guidelines",
            "prepare",
            "--repo-root",
            repo.to_str().expect("utf8"),
        ])
        .assert()
        .code(1);
    let output = stdout(&failed);
    assert!(output.starts_with("ARCHITECTURAL_GUIDELINES_STATUS=present\n"));
    assert!(
        output.contains("ARCHITECTURAL_GUIDELINES_DIFF_STATUS=failed\n"),
        "{output}"
    );
    assert!(
        output.contains("ARCHITECTURAL_GUIDELINES_WARNING="),
        "{output}"
    );
}

#[test]
fn materialize_diff_selects_upstream_and_honors_explicit_output() {
    let root = TempDir::new().expect("temp");
    let repo = repository(root.path());
    fs::write(repo.join("README.md"), "base\nfork change\n").expect("change");
    commit(&repo, &["README.md"], "fork change");
    let destination = root.path().join("snapshot.txt");

    let assertion = larch(root.path())
        .args([
            "architectural-guidelines",
            "materialize-diff",
            "--repo-root",
            repo.to_str().expect("utf8"),
            "--forked-target",
            "yes",
            "--output",
            destination.to_str().expect("utf8"),
        ])
        .assert()
        .success();
    let output = stdout(&assertion);
    assert!(
        output.contains("ARCHITECTURAL_GUIDELINES_BASE_REF=upstream/main\n"),
        "{output}"
    );
    assert!(
        fs::read_to_string(destination)
            .expect("snapshot")
            .contains("+fork change")
    );
}

#[test]
fn materialize_diff_trims_the_project_directory_environment_value() {
    let root = TempDir::new().expect("temp");
    let repo = repository(root.path());
    fs::write(repo.join("README.md"), "base\nenvironment root\n").expect("change");
    commit(&repo, &["README.md"], "environment root");

    let assertion = larch(root.path())
        .env(
            "CLAUDE_PROJECT_DIR",
            format!("  {}  ", repo.to_str().expect("utf8")),
        )
        .args(["architectural-guidelines", "materialize-diff"])
        .assert()
        .success();
    let output = stdout(&assertion);
    assert!(
        output.contains("ARCHITECTURAL_GUIDELINES_DIFF_STATUS=ok\n"),
        "{output}"
    );
    assert!(output.contains("+environment root"), "{output}");
}

#[test]
fn prepare_compose_writes_full_metadata_and_detects_head_drift() {
    let root = TempDir::new().expect("temp");
    let repo = repository(root.path());
    fs::write(
        repo.join("ARCHITECTURAL_GUIDELINES.md"),
        "### G-Test-1: Keep evidence\n- Why: parity\n- Deviate when: never\n",
    )
    .expect("guidelines");
    fs::write(repo.join("README.md"), "base\ncompose\n").expect("change");
    let head = commit(
        &repo,
        &["ARCHITECTURAL_GUIDELINES.md", "README.md"],
        "compose",
    );
    let implement = root.path().join("implement");

    let assertion = larch(root.path())
        .args([
            "architectural-guidelines",
            "prepare-compose",
            "--repo-root",
            repo.to_str().expect("utf8"),
            "--implement-tmpdir",
            implement.to_str().expect("utf8"),
            "--expected-head-sha",
            &head,
        ])
        .assert()
        .success();
    let output = stdout(&assertion);
    assert!(
        output.contains("ARCHITECTURAL_GUIDELINES_COMPOSE_STATUS=assessment-required\n"),
        "{output}"
    );
    assert!(
        output.contains(&format!("ARCHITECTURAL_GUIDELINES_HEAD_SHA={head}\n")),
        "{output}"
    );
    assert!(
        output.contains("ARCHITECTURAL_GUIDELINES_BASE_REF=origin/main\n"),
        "{output}"
    );
    assert!(
        output.contains("<architectural_guidelines_diff encoding=\"literal-redacted\">"),
        "{output}"
    );

    let diff_path = implement.join("architectural-guideline-materialized-diff.txt");
    let diff = fs::read_to_string(&diff_path).expect("diff");
    let fingerprint = format!("{:x}", Sha256::digest(diff.as_bytes()));
    let metadata = fs::read_to_string(implement.join("architectural-guideline-materialize.env"))
        .expect("metadata");
    for row in [
        "STATUS=present".to_owned(),
        format!("HEAD_SHA={head}"),
        format!("ASSESSED_HEAD_SHA={head}"),
        "BASE_REF=origin/main".to_owned(),
        "NOTE_STATE=authored".to_owned(),
        format!("DIFF_FINGERPRINT={fingerprint}"),
        format!("AUTHORED_DIFF_FINGERPRINT={fingerprint}"),
        format!("COVERED_DIFF_FINGERPRINT={fingerprint}"),
        format!("DIFF_SNAPSHOT={}", diff_path.display()),
        "GUIDELINES_STATUS=present".to_owned(),
        format!(
            "GUIDELINES_PATH={}",
            repo.join("ARCHITECTURAL_GUIDELINES.md").display()
        ),
        "ASSESSMENT_KIND=".to_owned(),
    ] {
        assert!(
            metadata.lines().any(|line| line == row),
            "missing {row:?}: {metadata}"
        );
    }
    assert!(
        metadata
            .lines()
            .any(|line| line.starts_with("WRITTEN_AT=") && line.ends_with('Z'))
    );

    let drift = larch(root.path())
        .args([
            "architectural-guidelines",
            "prepare-compose",
            "--repo-root",
            repo.to_str().expect("utf8"),
            "--implement-tmpdir",
            implement.to_str().expect("utf8"),
            "--expected-head-sha",
            "0000000000000000000000000000000000000000",
        ])
        .assert()
        .code(1);
    let drift_output = stdout(&drift);
    assert!(drift_output.contains("ARCHITECTURAL_GUIDELINES_COMPOSE_STATUS=failed\n"));
    assert!(
        drift_output
            .contains("HEAD changed before architectural-guidelines compose materialization")
    );
}

#[test]
fn prepare_compose_requires_tmpdir_and_rejects_symlinked_knowledge() {
    let root = TempDir::new().expect("temp");
    let repo = repository(root.path());
    let outside = root.path().join("outside.md");
    fs::write(&outside, "### I-Test-1: Outside\n").expect("outside");
    std::os::unix::fs::symlink(&outside, repo.join("ARCHITECTURAL_INVARIANTS.md"))
        .expect("symlink");

    let missing = larch(root.path())
        .args(["architectural-invariants", "prepare-compose"])
        .assert()
        .code(2);
    assert_eq!(
        stdout(&missing),
        "ARCHITECTURAL_INVARIANTS_COMPOSE_STATUS=failed\nARCHITECTURAL_INVARIANTS_WARNING=missing implement tmpdir\n"
    );

    let implement = root.path().join("implement");
    let invalid = larch(root.path())
        .args([
            "architectural-invariants",
            "prepare-compose",
            "--repo-root",
            repo.to_str().expect("utf8"),
            "--implement-tmpdir",
            implement.to_str().expect("utf8"),
        ])
        .assert()
        .success();
    let output = stdout(&invalid);
    assert!(
        output.contains("ARCHITECTURAL_INVARIANTS_COMPOSE_STATUS=invalid\n"),
        "{output}"
    );
    assert!(
        output.contains("ARCHITECTURAL_INVARIANTS_STATUS=invalid\n"),
        "{output}"
    );
    assert!(output.contains("symlinks are not read"), "{output}");
}

#[test]
fn prepare_reports_invalidation_failure_before_reading_knowledge() {
    let root = TempDir::new().expect("temp");
    let repo = repository(root.path());
    let implement = root.path().join("implement-is-a-file");
    fs::write(&implement, "not a directory\n").expect("implement file");

    let assertion = larch(root.path())
        .args([
            "architectural-guidelines",
            "prepare",
            "--repo-root",
            repo.to_str().expect("utf8"),
            "--implement-tmpdir",
            implement.to_str().expect("utf8"),
        ])
        .assert()
        .code(2);
    let output = stdout(&assertion);
    assert!(
        output.starts_with("ARCHITECTURAL_GUIDELINES_INVALIDATE_STATUS=failed\n"),
        "{output}"
    );
    assert!(
        output.contains("ARCHITECTURAL_GUIDELINES_WARNING="),
        "{output}"
    );
    assert!(
        !output.contains("ARCHITECTURAL_GUIDELINES_STATUS="),
        "{output}"
    );
}
