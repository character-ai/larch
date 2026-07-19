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

fn add_bare_origin(root: &Path, repo: &Path) -> PathBuf {
    let bare = root.join("origin.git");
    git(root, &["init", "--bare", bare.to_str().expect("bare path")]);
    git(
        repo,
        &["remote", "add", "origin", bare.to_str().expect("bare path")],
    );
    bare
}

#[test]
fn push_branch_uses_an_explicit_destination_and_sets_upstream() {
    let temp = TempDir::new().expect("tempdir");
    let repo = init_repo(temp.path());
    let bare = add_bare_origin(temp.path(), &repo);
    git(&repo, &["checkout", "-b", "feature/push"]);

    larch()
        .args(["push", "branch"])
        .current_dir(&repo)
        .assert()
        .code(0)
        .stdout("BRANCH=feature/push\n")
        .stderr("");

    let remote = StdCommand::new("git")
        .args([
            "--git-dir",
            bare.to_str().expect("bare path"),
            "rev-parse",
            "refs/heads/feature/push",
        ])
        .output()
        .expect("read remote ref");
    assert!(remote.status.success());
}

#[test]
fn push_branch_refuses_dirty_and_detached_worktrees() {
    let temp = TempDir::new().expect("tempdir");
    let repo = init_repo(temp.path());
    add_bare_origin(temp.path(), &repo);
    fs::write(repo.join("dirty.txt"), "dirty\n").expect("dirty write");
    larch()
        .args(["push", "branch"])
        .current_dir(&repo)
        .assert()
        .code(1)
        .stderr("uncommitted working-tree changes detected before push\n");
    fs::remove_file(repo.join("dirty.txt")).expect("remove dirty file");
    git(&repo, &["checkout", "--detach", "HEAD"]);
    larch()
        .args(["push", "branch"])
        .current_dir(&repo)
        .assert()
        .code(1)
        .stderr("git-push.sh: not on a named branch\n");
}

#[test]
fn push_commands_preserve_the_original_branch_guard_and_force_failure_envelopes() {
    let temp = TempDir::new().expect("tempdir");
    let repo = init_repo(temp.path());
    add_bare_origin(temp.path(), &repo);
    let state = temp.path().join("ship-pr-state.sh");
    fs::write(&state, "BRANCH_NAME=main\nORIGINAL_BRANCH_FORBIDDEN=true\n").expect("write state");

    larch()
        .args(["push", "branch"])
        .env("SHIP_PR_STATE_FILE", &state)
        .current_dir(&repo)
        .assert()
        .code(1)
        .stderr("refusing commit or push on forbidden original branch: main\n");
    larch()
        .args(["push", "force"])
        .env("SHIP_PR_STATE_FILE", &state)
        .current_dir(&repo)
        .assert()
        .code(2)
        .stdout("BRANCH=main\nPUSHED=false\nSTATUS=branch_mismatch\n")
        .stderr("");

    git(&repo, &["checkout", "--detach", "HEAD"]);
    larch()
        .args(["push", "force"])
        .current_dir(&repo)
        .assert()
        .code(2)
        .stdout("PUSHED=false\nSTATUS=detached_head\n")
        .stderr("git-force-push.sh: not on a named branch\n");
}

#[test]
fn force_push_reports_a_successful_leased_update() {
    let temp = TempDir::new().expect("tempdir");
    let repo = init_repo(temp.path());
    add_bare_origin(temp.path(), &repo);
    larch()
        .args(["push", "branch"])
        .current_dir(&repo)
        .assert()
        .success();
    fs::write(repo.join("file.txt"), "changed\n").expect("write change");
    git(&repo, &["add", "file.txt"]);
    git(&repo, &["commit", "-m", "changed"]);
    larch()
        .args(["push", "force"])
        .current_dir(&repo)
        .assert()
        .code(0)
        .stdout("BRANCH=main\nPUSHED=true\nSTATUS=pushed\n")
        .stderr("");
}

#[test]
fn push_network_failures_preserve_the_command_contracts() {
    let temp = TempDir::new().expect("tempdir");
    let repo = init_repo(temp.path());

    larch()
        .args(["push", "branch", "--unexpected"])
        .current_dir(&repo)
        .assert()
        .code(1)
        .stderr("git-push.sh: unknown argument: --unexpected\n");
    larch()
        .args(["push", "force", "--expected-remote-oid", "bad oid"])
        .current_dir(&repo)
        .assert()
        .code(2)
        .stdout("BRANCH=main\nPUSHED=false\nSTATUS=invalid_expected_remote_oid\n");

    fs::write(repo.join("dirty.txt"), "dirty\n").expect("dirty write");
    larch()
        .args(["push", "force"])
        .current_dir(&repo)
        .assert()
        .code(1)
        .stdout("BRANCH=main\nPUSHED=false\nSTATUS=dirty_worktree\n")
        .stderr("");
    fs::remove_file(repo.join("dirty.txt")).expect("remove dirty file");

    larch()
        .args(["push", "branch"])
        .current_dir(&repo)
        .assert()
        .code(128)
        .stdout("BRANCH=main\n");
    larch()
        .args(["push", "force"])
        .current_dir(&repo)
        .assert()
        .code(1)
        .stdout("BRANCH=main\nPUSHED=false\nSTATUS=diverged_retry_failed\n");
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
fn current_branch_emits_branch_when_unborn() {
    let temp = TempDir::new().expect("tempdir");
    let repo = temp.path().join("repo");
    fs::create_dir_all(&repo).expect("create repo");
    git(&repo, &["init", "-b", "unborn-topic"]);

    larch()
        .args(["git", "current-branch"])
        .current_dir(&repo)
        .assert()
        .code(0)
        .stdout("BRANCH=unborn-topic\n")
        .stderr("");
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
fn count_commits_missing_main_ref_warns_and_writes_status() {
    let temp = TempDir::new().expect("tempdir");
    let repo = temp.path().join("repo");
    fs::create_dir_all(&repo).expect("create repo");
    git(&repo, &["init", "-b", "topic"]);
    git(&repo, &["config", "user.email", "test@example.com"]);
    git(&repo, &["config", "user.name", "Test"]);
    fs::write(repo.join("file.txt"), "base\n").expect("write file");
    git(&repo, &["add", "file.txt"]);
    git(&repo, &["commit", "-m", "init"]);
    let status = temp.path().join("status.txt");

    larch()
        .args(["git", "count-commits"])
        .current_dir(&repo)
        .env("COUNT_COMMITS_STATUS_FILE", &status)
        .assert()
        .code(0)
        .stdout("0\n")
        .stderr(
            "WARN: lib-count-commits.sh: neither local 'main' nor 'origin/main' exists; cannot determine commit base. Returning 0.\n",
        );
    assert_eq!(
        fs::read_to_string(status).expect("status"),
        "missing_main_ref\n"
    );
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

fn attach_origin(repo: &Path, bare: &Path) {
    git(
        repo,
        &["remote", "add", "origin", bare.to_str().expect("bare path")],
    );
    git(repo, &["push", "-u", "origin", "main"]);
    git(bare, &["symbolic-ref", "HEAD", "refs/heads/main"]);
}

#[test]
fn check_main_sync_covers_in_sync_non_main_and_missing_remote_ref() {
    let temp = TempDir::new().expect("tempdir");
    let bare = temp.path().join("origin.git");
    let repo = init_repo(temp.path());
    git(
        temp.path(),
        &["init", "--bare", bare.to_str().expect("bare path")],
    );
    attach_origin(&repo, &bare);

    larch()
        .args(["git", "check-main-sync"])
        .current_dir(&repo)
        .assert()
        .code(0)
        .stdout("SYNC_STATUS=ok\nAHEAD_COUNT=0\n")
        .stderr("");

    larch()
        .args(["git", "sync-local-main"])
        .current_dir(&repo)
        .assert()
        .code(1)
        .stdout("")
        .stderr("cli.py git sync-local-main: refusing to update local 'main' while checked out on main\n");

    git(&repo, &["checkout", "-b", "feature"]);
    larch()
        .args(["git", "check-main-sync"])
        .current_dir(&repo)
        .assert()
        .code(0)
        .stdout("SYNC_STATUS=not-main\n")
        .stderr("");

    let linked = temp.path().join("linked");
    git(
        &repo,
        &[
            "worktree",
            "add",
            "-b",
            "linked-feature",
            linked.to_str().expect("linked path"),
        ],
    );
    larch()
        .args(["git", "check-main-sync"])
        .current_dir(&linked)
        .assert()
        .code(0)
        .stdout("SYNC_STATUS=not-main\n")
        .stderr("");

    let no_remote = init_repo(temp.path().join("no-remote").as_path());
    larch()
        .args(["git", "check-main-sync"])
        .current_dir(&no_remote)
        .assert()
        .code(2)
        .stdout("SYNC_STATUS=probe-error\nERROR=git rev-list failed or produced empty output (exit 128)\n")
        .stderr("");
}

#[test]
fn check_main_sync_blocks_non_log_commits_and_resets_flush_only_commits() {
    let temp = TempDir::new().expect("tempdir");
    let bare = temp.path().join("origin.git");
    let repo = init_repo(temp.path());
    git(
        temp.path(),
        &["init", "--bare", bare.to_str().expect("bare path")],
    );
    attach_origin(&repo, &bare);
    fs::write(repo.join("file.txt"), "real change\n").expect("write change");
    git(&repo, &["add", "file.txt"]);
    git(&repo, &["commit", "-m", "feat: real change"]);

    larch()
        .args(["git", "check-main-sync"])
        .current_dir(&repo)
        .assert()
        .code(1)
        .stdout(predicates::str::contains(
            "SYNC_STATUS=blocked\nAHEAD_COUNT=1\n",
        ))
        .stderr("");

    git(&repo, &["reset", "--hard", "origin/main"]);
    fs::create_dir_all(repo.join("larch-logs")).expect("logs directory");
    fs::write(repo.join("larch-logs/run.md"), "flush\n").expect("write flush log");
    git(&repo, &["add", "larch-logs/run.md"]);
    git(&repo, &["commit", "-m", "chore(larch-logs): flush run"]);

    larch()
        .args(["git", "check-main-sync"])
        .current_dir(&repo)
        .assert()
        .code(0)
        .stdout("SYNC_STATUS=reset\nAHEAD_COUNT=1\n")
        .stderr("");
    git(&repo, &["fsck", "--full", "--no-dangling"]);
    assert_eq!(
        StdCommand::new("git")
            .args(["rev-list", "--count", "origin/main..HEAD"])
            .current_dir(&repo)
            .output()
            .expect("count ahead")
            .stdout,
        b"0\n"
    );
}

#[test]
fn check_main_sync_refuses_a_dirty_flush_reset_and_sync_local_main_updates_a_feature_checkout() {
    let temp = TempDir::new().expect("tempdir");
    let bare = temp.path().join("origin.git");
    let repo = init_repo(temp.path());
    git(
        temp.path(),
        &["init", "--bare", bare.to_str().expect("bare path")],
    );
    attach_origin(&repo, &bare);
    fs::create_dir_all(repo.join("larch-logs")).expect("logs directory");
    fs::write(repo.join("larch-logs/run.md"), "flush\n").expect("write flush log");
    git(&repo, &["add", "larch-logs/run.md"]);
    git(&repo, &["commit", "-m", "chore(larch-logs): flush run"]);
    fs::write(repo.join("untracked.txt"), "dirty\n").expect("write untracked");

    larch()
        .args(["git", "check-main-sync"])
        .current_dir(&repo)
        .assert()
        .code(2)
        .stdout(predicates::str::contains("SYNC_STATUS=probe-error\nAHEAD_COUNT=1\nERROR=refusing reset: working tree is not clean"))
        .stderr("");
    fs::remove_file(repo.join("untracked.txt")).expect("remove untracked");
    git(&repo, &["reset", "--hard", "origin/main"]);

    let updater = temp.path().join("updater");
    git(
        temp.path(),
        &[
            "clone",
            bare.to_str().expect("bare path"),
            updater.to_str().expect("updater path"),
        ],
    );
    git(&updater, &["config", "user.email", "test@example.com"]);
    git(&updater, &["config", "user.name", "Test"]);
    fs::write(updater.join("file.txt"), "advanced\n").expect("advance main");
    git(&updater, &["add", "file.txt"]);
    git(&updater, &["commit", "-m", "advance main"]);
    git(&updater, &["push", "origin", "main"]);
    git(&repo, &["fetch", "origin", "main"]);
    git(&repo, &["checkout", "-b", "feature"]);

    larch()
        .args(["git", "sync-local-main"])
        .current_dir(&repo)
        .assert()
        .code(0)
        .stdout("RESULT=updated\n")
        .stderr("");
    assert_eq!(
        StdCommand::new("git")
            .args(["rev-parse", "main"])
            .current_dir(&repo)
            .output()
            .expect("local main")
            .stdout,
        StdCommand::new("git")
            .args(["rev-parse", "origin/main"])
            .current_dir(&repo)
            .output()
            .expect("remote main")
            .stdout
    );
    git(&repo, &["fsck", "--full", "--no-dangling"]);
}
