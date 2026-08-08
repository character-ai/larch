//! `triage inspect` against a real repository, with no network.
//!
//! The parity sandbox has no repository at all, so it can only prove the
//! scanners and the refusal an unreadable origin takes. The success path is the
//! half that matters most: an immutable object is resolved, its presence is
//! proved, and one bounded blob is published. That path needs a repository with
//! a GitHub-shaped `origin`, which is exactly what this fixture builds — the
//! remote URL is never contacted, because the cited commit is already local.

use std::{fs, path::Path, process::Command};

use assert_cmd::Command as AssertCommand;
use tempfile::TempDir;

/// The `origin` a triage evidence read is required to recognize.
const ORIGIN_URL: &str = "https://github.com/character-ai/larch.git";
/// The slug that origin resolves to.
const ORIGIN_SLUG: &str = "character-ai/larch";
/// Bytes of the seeded evidence file, chosen to exceed a small `--max-bytes`.
const EVIDENCE: &str = "first line\nsecond line\nthird line\n";

fn git(repository: &Path, arguments: &[&str]) {
    let status = Command::new("git")
        .current_dir(repository)
        .args(arguments)
        .env("GIT_AUTHOR_NAME", "larch")
        .env("GIT_AUTHOR_EMAIL", "larch@example.invalid")
        .env("GIT_COMMITTER_NAME", "larch")
        .env("GIT_COMMITTER_EMAIL", "larch@example.invalid")
        .env("GIT_CONFIG_GLOBAL", "/dev/null")
        .env("GIT_CONFIG_SYSTEM", "/dev/null")
        .output()
        .unwrap_or_else(|error| panic!("run git {arguments:?}: {error}"));
    assert!(
        status.status.success(),
        "git {arguments:?}: {}",
        String::from_utf8_lossy(&status.stderr)
    );
}

/// Build a one-commit repository whose `origin` names a GitHub repository.
fn seeded_repository() -> (TempDir, String) {
    let directory = tempfile::tempdir().expect("temporary repository");
    let root = directory.path();
    git(root, &["init", "--initial-branch", "main", "--quiet"]);
    git(root, &["remote", "add", "origin", ORIGIN_URL]);
    fs::write(root.join("evidence.md"), EVIDENCE).expect("seed evidence");
    git(root, &["add", "evidence.md"]);
    git(root, &["commit", "--quiet", "--message", "seed"]);
    let head = Command::new("git")
        .current_dir(root)
        .args(["rev-parse", "HEAD"])
        .output()
        .expect("resolve HEAD");
    let sha = String::from_utf8_lossy(&head.stdout).trim().to_owned();
    assert_eq!(sha.len(), 40, "a full object hash");
    (directory, sha)
}

fn inspect(root: &Path, arguments: &[&str]) -> (i32, String) {
    let output = AssertCommand::cargo_bin("larch")
        .expect("larch binary should build")
        .args(["triage", "inspect", "--repo-root"])
        .arg(root)
        .args(arguments)
        .output()
        .expect("run triage inspect");
    (
        output.status.code().unwrap_or(-1),
        String::from_utf8_lossy(&output.stdout).into_owned(),
    )
}

#[test]
fn an_immutable_commit_publishes_its_repository_and_object() {
    let (repository, sha) = seeded_repository();
    let (code, stdout) = inspect(repository.path(), &["--ref", &sha]);

    assert_eq!(code, 0, "{stdout}");
    assert_eq!(
        stdout,
        format!(
            "EVIDENCE_STATUS=ok\nREPOSITORY={ORIGIN_SLUG}\nIMMUTABLE_SHA={sha}\n\
             SOURCE_REF={sha}\nEVIDENCE_TRUNCATED=false\n"
        )
    );
}

#[test]
fn an_uppercase_citation_resolves_to_the_same_lowercase_object() {
    let (repository, sha) = seeded_repository();
    let (code, stdout) = inspect(repository.path(), &["--ref", &sha.to_uppercase()]);

    assert_eq!(code, 0, "{stdout}");
    assert!(stdout.contains(&format!("IMMUTABLE_SHA={sha}")), "{stdout}");
}

#[test]
fn one_bounded_blob_is_published_from_the_commit_tree() {
    let (repository, sha) = seeded_repository();
    let (code, stdout) = inspect(
        repository.path(),
        &["--ref", &sha, "--path", "./evidence.md"],
    );

    assert_eq!(code, 0, "{stdout}");
    // The path is republished in its normalized form, and the content arrives
    // between the two fences with the file's own trailing newline.
    assert!(stdout.contains("EVIDENCE_PATH=evidence.md\n"), "{stdout}");
    assert!(stdout.contains("EVIDENCE_TRUNCATED=false\n"), "{stdout}");
    assert!(
        stdout.ends_with(&format!(
            "EVIDENCE_CONTENT_BEGIN\n{EVIDENCE}EVIDENCE_CONTENT_END\n"
        )),
        "{stdout}"
    );
}

#[test]
fn a_blob_past_the_cap_is_truncated_and_says_so() {
    let (repository, sha) = seeded_repository();
    let (code, stdout) = inspect(
        repository.path(),
        &["--ref", &sha, "--path", "evidence.md", "--max-bytes", "10"],
    );

    assert_eq!(code, 0, "{stdout}");
    assert!(stdout.contains("EVIDENCE_TRUNCATED=true\n"), "{stdout}");
    // Ten bytes, then the newline the writer adds because the cut content does
    // not end in one.
    assert!(
        stdout.ends_with("EVIDENCE_CONTENT_BEGIN\nfirst line\nEVIDENCE_CONTENT_END\n"),
        "{stdout}"
    );
}

#[test]
fn an_absent_path_and_an_absent_object_are_both_evidence_gaps() {
    let (repository, sha) = seeded_repository();
    let (code, stdout) = inspect(repository.path(), &["--ref", &sha, "--path", "missing.md"]);
    assert_eq!(code, 8, "{stdout}");
    assert!(
        stdout.ends_with(
            "EVIDENCE_STATUS=gap\nEVIDENCE_GAP=evidence path is missing from the immutable commit\n"
        ),
        "{stdout}"
    );

    // A well-formed hash naming no local object cannot be fetched without a
    // network, so the citation is reported as unavailable rather than read.
    let (code, stdout) = inspect(repository.path(), &["--ref", &"a".repeat(40)]);
    assert_eq!(code, 8, "{stdout}");
    assert_eq!(
        stdout,
        "EVIDENCE_STATUS=gap\nEVIDENCE_GAP=cited immutable commit is unavailable\n"
    );
}

#[test]
fn a_directory_is_not_a_readable_evidence_path() {
    let (repository, sha) = seeded_repository();
    fs::create_dir(repository.path().join("nested")).expect("nested directory");
    fs::write(repository.path().join("nested/inner.md"), EVIDENCE).expect("nested evidence");
    git(repository.path(), &["add", "nested/inner.md"]);
    git(
        repository.path(),
        &["commit", "--quiet", "--message", "nest"],
    );

    let (code, stdout) = inspect(repository.path(), &["--ref", &sha, "--path", "nested"]);
    assert_eq!(code, 8, "{stdout}");
    assert!(
        stdout.contains("EVIDENCE_GAP=evidence path is missing"),
        "{stdout}"
    );
}

#[test]
fn a_non_github_origin_is_not_a_validated_remote() {
    let (repository, sha) = seeded_repository();
    git(
        repository.path(),
        &[
            "remote",
            "set-url",
            "origin",
            "https://gitlab.com/owner/repo.git",
        ],
    );

    let (code, stdout) = inspect(repository.path(), &["--ref", &sha]);
    assert_eq!(code, 8, "{stdout}");
    assert_eq!(
        stdout,
        "EVIDENCE_STATUS=gap\nEVIDENCE_GAP=origin is not a validated GitHub repository remote\n"
    );
}
