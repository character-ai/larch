//! Executable-boundary coverage for Rust-owned session closeout commands.

#![cfg(unix)]

use assert_cmd::Command as AssertCommand;
use predicates::prelude::*;
use std::{
    fs,
    path::{Path, PathBuf},
    process::Command,
};
use tempfile::TempDir;

fn larch() -> AssertCommand {
    AssertCommand::cargo_bin("larch").expect("larch binary should build")
}

fn workspace_root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .and_then(Path::parent)
        .expect("workspace root")
        .to_path_buf()
}

fn git(cwd: &Path, arguments: &[&str]) {
    let output = Command::new("git")
        .args(arguments)
        .current_dir(cwd)
        .output()
        .expect("git should launch");
    assert!(
        output.status.success(),
        "git {} failed: {}",
        arguments.join(" "),
        String::from_utf8_lossy(&output.stderr)
    );
}

fn git_stdout(cwd: &Path, arguments: &[&str]) -> String {
    let output = Command::new("git")
        .args(arguments)
        .current_dir(cwd)
        .output()
        .expect("git should launch");
    assert!(
        output.status.success(),
        "git {} failed",
        arguments.join(" ")
    );
    String::from_utf8_lossy(&output.stdout).trim().to_owned()
}

fn configure_identity(repository: &Path) {
    git(repository, &["config", "user.email", "ci@example.test"]);
    git(repository, &["config", "user.name", "Larch CI"]);
}

fn commit(repository: &Path, path: &str, contents: &str, subject: &str) {
    let target = repository.join(path);
    fs::create_dir_all(target.parent().expect("file parent")).expect("create file parent");
    fs::write(target, format!("{contents}\n")).expect("write fixture file");
    git(repository, &["add", "--", path]);
    git(repository, &["commit", "-q", "-m", subject]);
}

fn remote_repository(root: &Path, label: &str) -> PathBuf {
    let remote = root.join(format!("{label}-origin.git"));
    let seed = root.join(format!("{label}-seed"));
    let clone = root.join(format!("{label}-clone"));
    git(
        root,
        &[
            "init",
            "-q",
            "--bare",
            remote.to_str().expect("remote UTF-8"),
        ],
    );
    fs::create_dir(&seed).expect("create seed repository");
    git(&seed, &["init", "-q"]);
    git(&seed, &["checkout", "-q", "-b", "main"]);
    configure_identity(&seed);
    commit(&seed, "README.md", "initial", "init");
    git(
        &seed,
        &[
            "remote",
            "add",
            "origin",
            remote.to_str().expect("remote UTF-8"),
        ],
    );
    git(&seed, &["push", "-q", "-u", "origin", "main"]);
    git(&remote, &["symbolic-ref", "HEAD", "refs/heads/main"]);
    git(
        root,
        &[
            "clone",
            "-q",
            remote.to_str().expect("remote UTF-8"),
            clone.to_str().expect("clone UTF-8"),
        ],
    );
    configure_identity(&clone);
    git(&clone, &["branch", "feature"]);
    clone
}

#[test]
fn local_cleanup_rejects_main_without_mutating_a_repository() {
    larch()
        .args(["session", "local-cleanup", "--branch", "main"])
        .assert()
        .code(1)
        .stdout("")
        .stderr(predicate::str::contains("--branch must not be 'main'"));
}

#[test]
fn local_cleanup_fast_forwards_main_and_removes_the_feature_branch() {
    let temporary = TempDir::new().expect("temporary repository root");
    let repository = remote_repository(temporary.path(), "success");
    commit(
        &repository,
        "operator-note.txt",
        "keep me",
        "operator local note",
    );
    let ahead = git_stdout(&repository, &["rev-parse", "HEAD"]);

    larch()
        .current_dir(&repository)
        .args(["session", "local-cleanup", "--branch", "feature"])
        .assert()
        .success()
        .stdout(predicate::str::contains("CLEANUP_SUCCESS=true"))
        .stdout(predicate::str::contains("CURRENT_BRANCH=main"))
        .stdout(predicate::str::contains("BRANCH_DELETED=true"));

    assert_eq!(git_stdout(&repository, &["rev-parse", "HEAD"]), ahead);
    assert!(repository.join("operator-note.txt").is_file());
    assert!(git_stdout(&repository, &["branch", "--list", "feature"]).is_empty());
}

#[test]
fn local_cleanup_preserves_an_ahead_main_when_origin_has_diverged() {
    let temporary = TempDir::new().expect("temporary repository root");
    let repository = remote_repository(temporary.path(), "diverged");
    commit(&repository, "local-only.txt", "local", "local-only commit");
    let local_head = git_stdout(&repository, &["rev-parse", "HEAD"]);
    let remote_url = git_stdout(&repository, &["remote", "get-url", "origin"]);
    let pusher = temporary.path().join("diverged-pusher");
    git(
        temporary.path(),
        &[
            "clone",
            "-q",
            &remote_url,
            pusher.to_str().expect("pusher UTF-8"),
        ],
    );
    configure_identity(&pusher);
    commit(&pusher, "remote-only.txt", "remote", "remote-only commit");
    git(&pusher, &["push", "-q", "origin", "main"]);

    larch()
        .current_dir(&repository)
        .args(["session", "local-cleanup", "--branch", "feature"])
        .assert()
        .success()
        .stdout(predicate::str::contains("CLEANUP_SUCCESS=false"))
        .stdout(predicate::str::contains("BRANCH_DELETED=false"))
        .stderr(predicate::str::contains(
            "local main is ahead of origin/main by 1 commit(s)",
        ));

    assert_eq!(git_stdout(&repository, &["rev-parse", "HEAD"]), local_head);
    assert_eq!(
        git_stdout(&repository, &["branch", "--show-current"]),
        "main"
    );
    assert_eq!(
        git_stdout(&repository, &["branch", "--list", "feature"]),
        "feature"
    );
}

#[test]
fn local_cleanup_reports_a_branch_checked_out_in_another_worktree() {
    let temporary = TempDir::new().expect("temporary repository root");
    let repository = remote_repository(temporary.path(), "branch-delete-failure");
    let worktree = temporary.path().join("feature-worktree");
    git(
        &repository,
        &[
            "worktree",
            "add",
            "-q",
            worktree.to_str().expect("worktree UTF-8"),
            "feature",
        ],
    );

    larch()
        .current_dir(&repository)
        .args(["session", "local-cleanup", "--branch", "feature"])
        .assert()
        .success()
        .stdout(predicate::str::contains("CLEANUP_SUCCESS=false"))
        .stdout(predicate::str::contains("BRANCH_DELETED=false"))
        .stderr(predicate::str::contains(
            "Failed to delete local branch feature",
        ));

    assert_eq!(
        git_stdout(&worktree, &["branch", "--show-current"]),
        "feature"
    );
}

#[test]
fn stall_recovery_lint_uses_the_rust_owned_contract_check() {
    larch()
        .args(["stall-recovery", "lint"])
        .assert()
        .success()
        .stdout("LINT_OK=true\n")
        .stderr("");
}

#[test]
fn stall_recovery_lint_reads_the_contract_from_the_plugin_root() {
    let temporary = TempDir::new().expect("temporary caller directory");

    larch()
        .current_dir(temporary.path())
        .env("CLAUDE_PLUGIN_ROOT", workspace_root())
        .args(["stall-recovery", "lint"])
        .assert()
        .success()
        .stdout("LINT_OK=true\n")
        .stderr("");
}
