//! Black-box parity fixtures for `gh remote-repo` and `gh resolve-repo`.

use std::{
    fs,
    path::{Path, PathBuf},
    process::Command as StdCommand,
};

use assert_cmd::Command;
use tempfile::TempDir;

fn larch() -> Command {
    Command::cargo_bin("larch").expect("larch binary should build")
}

fn git(cwd: &Path, args: &[&str]) {
    let status = StdCommand::new("git")
        .args(args)
        .current_dir(cwd)
        .status()
        .expect("git should run");
    assert!(status.success(), "git {args:?} failed");
}

fn init_repo(root: &Path) -> PathBuf {
    let repo = root.join("repo");
    fs::create_dir_all(&repo).expect("create repo");
    git(&repo, &["init", "-b", "main"]);
    git(&repo, &["config", "user.email", "test@example.com"]);
    git(&repo, &["config", "user.name", "Test"]);
    fs::write(repo.join("file.txt"), "base\n").expect("write file");
    git(&repo, &["add", "file.txt"]);
    git(&repo, &["commit", "-m", "init"]);
    repo
}

#[test]
fn remote_repo_parses_explicit_https_url() {
    larch()
        .args(["gh", "remote-repo", "https://github.com/acme/project.git"])
        .assert()
        .code(0)
        .stdout("acme/project\n")
        .stderr("");
}

#[test]
fn remote_repo_parses_explicit_ssh_scp_url() {
    larch()
        .args(["gh", "remote-repo", "git@github.com:acme/project.git"])
        .assert()
        .code(0)
        .stdout("acme/project\n")
        .stderr("");
}

#[test]
fn remote_repo_resolves_named_remote() {
    let temp = TempDir::new().expect("tempdir");
    let repo = init_repo(temp.path());
    git(
        &repo,
        &[
            "remote",
            "add",
            "origin",
            "https://github.com/acme/project.git",
        ],
    );

    larch()
        .args(["gh", "remote-repo", "origin"])
        .current_dir(&repo)
        .assert()
        .code(0)
        .stdout("acme/project\n")
        .stderr("");
}

#[test]
fn remote_repo_rejects_malformed_and_hostile_strings() {
    larch()
        .args(["gh", "remote-repo", "git@github.com:!!!/@@@"])
        .assert()
        .code(2)
        .stdout("")
        .stderr("github-remote-repo.sh: cannot parse remote\n");

    larch()
        .args(["gh", "remote-repo", "git@gitlab.com:acme/project.git"])
        .assert()
        .code(2)
        .stdout("")
        .stderr("github-remote-repo.sh: cannot parse remote\n");
}

#[test]
fn remote_repo_usage_without_argument() {
    larch()
        .args(["gh", "remote-repo"])
        .assert()
        .code(2)
        .stdout("")
        .stderr("Usage: github-remote-repo.sh <remote-name-or-url>\n");
}

#[test]
fn remote_repo_absent_named_remote_fails() {
    let temp = TempDir::new().expect("tempdir");
    let repo = init_repo(temp.path());

    larch()
        .args(["gh", "remote-repo", "origin"])
        .current_dir(&repo)
        .assert()
        .code(2)
        .stdout("")
        .stderr("github-remote-repo.sh: cannot parse remote\n");
}

#[test]
fn resolve_repo_uses_origin_when_service_credentials_are_absent() {
    let temp = TempDir::new().expect("tempdir");
    let repo = init_repo(temp.path());
    git(
        &repo,
        &["remote", "add", "origin", "git@github.com:acme/project.git"],
    );

    larch()
        .env_remove("LARCH_GH_TOKEN")
        .args(["gh", "resolve-repo"])
        .current_dir(&repo)
        .assert()
        .code(0)
        .stdout("acme/project\n")
        .stderr("");
}

#[test]
fn resolve_repo_works_in_linked_worktree() {
    let temp = TempDir::new().expect("tempdir");
    let repo = init_repo(temp.path());
    git(
        &repo,
        &[
            "remote",
            "add",
            "origin",
            "https://github.com/acme/project.git",
        ],
    );
    let worktree = temp.path().join("linked");
    git(
        &repo,
        &[
            "worktree",
            "add",
            worktree.to_str().expect("utf8"),
            "-b",
            "topic",
        ],
    );

    larch()
        .env_remove("LARCH_GH_TOKEN")
        .args(["gh", "resolve-repo"])
        .current_dir(&worktree)
        .assert()
        .code(0)
        .stdout("acme/project\n")
        .stderr("");
}

#[test]
fn resolve_repo_fails_without_repository() {
    let temp = TempDir::new().expect("tempdir");

    larch()
        .env_remove("LARCH_GH_TOKEN")
        .args(["gh", "resolve-repo"])
        .current_dir(temp.path())
        .assert()
        .code(1)
        .stdout("")
        .stderr("ERROR=could not resolve repo (gh repo view + git remote both failed)\n");
}

#[test]
fn resolve_repo_fails_when_origin_absent() {
    let temp = TempDir::new().expect("tempdir");
    let repo = init_repo(temp.path());

    larch()
        .env_remove("LARCH_GH_TOKEN")
        .args(["gh", "resolve-repo"])
        .current_dir(&repo)
        .assert()
        .code(1)
        .stdout("")
        .stderr("ERROR=could not resolve repo (gh repo view + git remote both failed)\n");
}

#[test]
fn resolve_repo_rejects_unknown_argument() {
    larch()
        .args(["gh", "resolve-repo", "--extra"])
        .assert()
        .code(1)
        .stdout("")
        .stderr("resolve-repo.sh: unknown argument: --extra\n");
}

#[test]
fn resolve_repo_rejects_malformed_origin() {
    let temp = TempDir::new().expect("tempdir");
    let repo = init_repo(temp.path());
    git(
        &repo,
        &["remote", "add", "origin", "git@github.com:!!!/@@@"],
    );

    larch()
        .env_remove("LARCH_GH_TOKEN")
        .args(["gh", "resolve-repo"])
        .current_dir(&repo)
        .assert()
        .code(1)
        .stdout("")
        .stderr("ERROR=could not resolve repo (gh repo view + git remote both failed)\n");
}
