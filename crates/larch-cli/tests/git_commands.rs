//! Black-box parity fixtures for migrated Git branch/ref commands.

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
fn current_branch_emits_branch_on_named_head() {
    let temp = TempDir::new().expect("tempdir");
    let repo = init_repo(temp.path());
    git(&repo, &["checkout", "-b", "feature/x"]);

    larch()
        .args(["git", "current-branch"])
        .current_dir(&repo)
        .assert()
        .code(0)
        .stdout("BRANCH=feature/x\n")
        .stderr("");
}

#[test]
fn current_branch_fails_when_detached() {
    let temp = TempDir::new().expect("tempdir");
    let repo = init_repo(temp.path());
    git(&repo, &["checkout", "--detach", "HEAD"]);

    larch()
        .args(["git", "current-branch"])
        .current_dir(&repo)
        .assert()
        .code(1)
        .stdout("")
        .stderr("git-current-branch.sh: not on a named branch (detached HEAD or not a git repo)\n");
}

#[test]
fn branch_info_emits_head_and_branch() {
    let temp = TempDir::new().expect("tempdir");
    let repo = init_repo(temp.path());
    git(&repo, &["checkout", "-b", "topic"]);

    let output = larch()
        .args(["git", "branch-info"])
        .current_dir(&repo)
        .output()
        .expect("branch-info should run");
    assert!(output.status.success());
    assert!(output.stderr.is_empty());
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(stdout.contains("HEAD_SHA="));
    assert!(stdout.contains("CURRENT_BRANCH=topic\n"));
}

#[test]
fn branch_info_allows_detached_with_empty_branch() {
    let temp = TempDir::new().expect("tempdir");
    let repo = init_repo(temp.path());
    git(&repo, &["checkout", "--detach", "HEAD"]);

    let output = larch()
        .args(["git", "branch-info"])
        .current_dir(&repo)
        .output()
        .expect("branch-info should run");
    assert!(output.status.success());
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(stdout.contains("HEAD_SHA="));
    assert!(stdout.contains("CURRENT_BRANCH=\n"));
}

#[test]
fn count_commits_reports_zero_on_main_without_origin() {
    let temp = TempDir::new().expect("tempdir");
    let repo = init_repo(temp.path());

    larch()
        .args(["git", "count-commits"])
        .current_dir(&repo)
        .assert()
        .code(0)
        .stdout("0\n")
        .stderr("");
}

#[test]
fn count_commits_counts_commits_ahead_of_main() {
    let temp = TempDir::new().expect("tempdir");
    let repo = init_repo(temp.path());
    git(&repo, &["checkout", "-b", "feature"]);
    fs::write(repo.join("file.txt"), "change\n").expect("write");
    git(&repo, &["add", "file.txt"]);
    git(&repo, &["commit", "-m", "change"]);

    larch()
        .args(["git", "count-commits"])
        .current_dir(&repo)
        .assert()
        .code(0)
        .stdout("1\n")
        .stderr("");
}

#[test]
fn count_commits_writes_status_file_when_configured() {
    let temp = TempDir::new().expect("tempdir");
    let repo = init_repo(temp.path());
    let status = temp.path().join("status.txt");

    larch()
        .args(["git", "count-commits"])
        .current_dir(&repo)
        .env("COUNT_COMMITS_STATUS_FILE", &status)
        .assert()
        .code(0)
        .stdout("0\n");
    assert_eq!(fs::read_to_string(status).expect("status"), "ok\n");
}

#[test]
fn show_stage_reads_conflict_ours_blob() {
    let temp = TempDir::new().expect("tempdir");
    let repo = init_repo(temp.path());
    git(&repo, &["checkout", "-b", "feature"]);
    fs::write(repo.join("file.txt"), "feature\n").expect("write");
    git(&repo, &["add", "file.txt"]);
    git(&repo, &["commit", "-m", "feature"]);
    git(&repo, &["checkout", "main"]);
    fs::write(repo.join("file.txt"), "main\n").expect("write");
    git(&repo, &["add", "file.txt"]);
    git(&repo, &["commit", "-m", "main"]);
    let merge = StdCommand::new("git")
        .args(["merge", "feature"])
        .current_dir(&repo)
        .status()
        .expect("merge");
    assert!(!merge.success(), "merge should conflict");

    larch()
        .args(["git", "show-stage", "--stage", "2", "--file", "file.txt"])
        .current_dir(&repo)
        .assert()
        .code(0)
        .stdout("main\n")
        .stderr("");

    larch()
        .args(["git", "show-stage", "--stage", "3", "--file", "file.txt"])
        .current_dir(&repo)
        .assert()
        .code(0)
        .stdout("feature\n")
        .stderr("");
}

#[test]
fn show_stage_missing_stage_exits_nonzero() {
    let temp = TempDir::new().expect("tempdir");
    let repo = init_repo(temp.path());

    larch()
        .args(["git", "show-stage", "--stage", "2", "--file", "file.txt"])
        .current_dir(&repo)
        .assert()
        .code(128)
        .stdout("");
}

#[test]
fn check_remote_branch_reports_present_for_local_path_remote() {
    let temp = TempDir::new().expect("tempdir");
    let bare = temp.path().join("bare.git");
    let repo = init_repo(temp.path());
    git(
        temp.path(),
        &[
            "clone",
            "--bare",
            repo.to_str().unwrap(),
            bare.to_str().unwrap(),
        ],
    );
    git(&repo, &["remote", "add", "origin", bare.to_str().unwrap()]);
    git(&repo, &["push", "-u", "origin", "main"]);
    git(&repo, &["checkout", "-b", "feat"]);
    fs::write(repo.join("file.txt"), "feat\n").expect("write");
    git(&repo, &["add", "file.txt"]);
    git(&repo, &["commit", "-m", "feat"]);
    git(&repo, &["push", "-u", "origin", "feat"]);

    larch()
        .args(["git", "check-remote-branch", "--branch", "feat"])
        .current_dir(&repo)
        .assert()
        .code(0)
        .stdout("STATE=present\nRC=0\n")
        .stderr("");

    larch()
        .args(["git", "check-remote-branch", "--branch", "missing"])
        .current_dir(&repo)
        .assert()
        .code(0)
        .stdout("STATE=absent\nRC=2\n")
        .stderr("");
}
