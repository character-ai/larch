//! Black-box parity fixtures for the migrated `push rebase` and
//! `push checkpoint-probe` commands. Each mutation case runs `git fsck`.

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

/// Initialize a repository with an initial `file.txt` commit on `main`.
fn init_repo(root: &Path) -> PathBuf {
    let repo = root.join("repo");
    fs::create_dir_all(&repo).expect("create repo");
    git(&repo, &["init", "-b", "main"]);
    git(&repo, &["config", "user.email", "test@example.com"]);
    git(&repo, &["config", "user.name", "Test"]);
    // Deliberately set a hostile interactive editor: the trivial-conflict test's
    // `git rebase --continue` must stay non-interactive via the command's own
    // GIT_EDITOR=true, not a fixture escape hatch. `false` fails if ever invoked.
    git(&repo, &["config", "core.editor", "false"]);
    fs::write(repo.join("file.txt"), "base\n").expect("write file");
    git(&repo, &["add", "file.txt"]);
    git(&repo, &["commit", "-m", "init"]);
    repo
}

/// Add a bare remote and publish `main` to it.
fn publish_main(root: &Path, repo: &Path, remote: &str) -> PathBuf {
    let bare = root.join(format!("{remote}.git"));
    git(root, &["init", "--bare", bare.to_str().expect("bare path")]);
    git(
        repo,
        &["remote", "add", remote, bare.to_str().expect("bare path")],
    );
    git(repo, &["push", remote, "main"]);
    bare
}

fn assert_fsck_clean(repo: &Path) {
    let output = StdCommand::new("git")
        .args(["fsck", "--no-dangling"])
        .current_dir(repo)
        .output()
        .expect("git fsck should run");
    assert!(
        output.status.success(),
        "git fsck failed: {}",
        String::from_utf8_lossy(&output.stderr)
    );
}

fn rebase_in_progress(repo: &Path) -> bool {
    repo.join(".git/rebase-merge").is_dir() || repo.join(".git/rebase-apply").is_dir()
}

#[test]
fn rebase_rejects_flag_combinations_and_detached_head() {
    let temp = TempDir::new().expect("tempdir");
    let repo = init_repo(temp.path());

    // Base-label validation runs before any flag or git work.
    larch()
        .args(["push", "rebase", "--base-remote", "bad remote"])
        .current_dir(&repo)
        .assert()
        .code(3)
        .stdout("REBASE_ERROR=base_remote contains unsupported characters\n");
    // Flag-combination precedence, exit 3 with the exact operator message.
    larch()
        .args(["push", "rebase", "--skip-if-pushed"])
        .current_dir(&repo)
        .assert()
        .code(3)
        .stdout("REBASE_ERROR=--skip-if-pushed is only valid with --no-push\n");
    larch()
        .args(["push", "rebase", "--keep-on-conflict"])
        .current_dir(&repo)
        .assert()
        .code(3)
        .stdout("REBASE_ERROR=--keep-on-conflict is only valid with --no-push\n");
    larch()
        .args(["push", "rebase", "--continue", "--no-push"])
        .current_dir(&repo)
        .assert()
        .code(3)
        .stdout(
            "REBASE_ERROR=--continue --no-push requires --keep-on-conflict to safely handle nested conflicts\n",
        );
    larch()
        .args([
            "push",
            "rebase",
            "--no-push",
            "--skip-if-pushed",
            "--continue",
        ])
        .current_dir(&repo)
        .assert()
        .code(3)
        .stdout("REBASE_ERROR=--skip-if-pushed cannot be used with --continue\n");
    // Unknown flag → argparse-style exit 3 with no KV output.
    larch()
        .args(["push", "rebase", "--bogus"])
        .current_dir(&repo)
        .assert()
        .code(3)
        .stdout("");

    // Detached HEAD is reported before any fetch.
    git(&repo, &["checkout", "--detach", "HEAD"]);
    larch()
        .args(["push", "rebase", "--no-push"])
        .current_dir(&repo)
        .assert()
        .code(3)
        .stdout("REBASE_ERROR=Not on a branch (detached HEAD)\n");
}

#[test]
fn rebase_no_push_skips_when_branch_is_already_fresh() {
    let temp = TempDir::new().expect("tempdir");
    let repo = init_repo(temp.path());
    publish_main(temp.path(), &repo, "origin");
    git(&repo, &["checkout", "-b", "topic"]);
    fs::write(repo.join("topic.txt"), "topic\n").expect("write topic");
    git(&repo, &["add", "topic.txt"]);
    git(&repo, &["commit", "-m", "topic work"]);

    larch()
        .args(["push", "rebase", "--no-push"])
        .current_dir(&repo)
        .assert()
        .code(0)
        .stdout("SKIPPED_ALREADY_FRESH=true\n");
    assert_fsck_clean(&repo);
}

#[test]
fn rebase_no_push_skip_if_pushed_detects_published_branch() {
    let temp = TempDir::new().expect("tempdir");
    let repo = init_repo(temp.path());
    publish_main(temp.path(), &repo, "origin");
    git(&repo, &["checkout", "-b", "topic"]);
    fs::write(repo.join("topic.txt"), "topic\n").expect("write topic");
    git(&repo, &["add", "topic.txt"]);
    git(&repo, &["commit", "-m", "topic work"]);
    git(&repo, &["push", "origin", "topic"]);

    larch()
        .args(["push", "rebase", "--no-push", "--skip-if-pushed"])
        .current_dir(&repo)
        .assert()
        .code(0)
        .stdout("SKIPPED_ALREADY_PUSHED=true\n");
    assert_fsck_clean(&repo);
}

#[test]
fn rebase_no_push_reports_conflict_and_aborts_without_keep() {
    let temp = TempDir::new().expect("tempdir");
    let repo = init_repo(temp.path());
    publish_main(temp.path(), &repo, "origin");
    // topic diverges on file.txt; origin/main advances file.txt differently.
    git(&repo, &["checkout", "-b", "topic"]);
    fs::write(repo.join("file.txt"), "topic\n").expect("write topic");
    git(&repo, &["commit", "-am", "topic edit"]);
    git(&repo, &["checkout", "main"]);
    fs::write(repo.join("file.txt"), "upstream\n").expect("write upstream");
    git(&repo, &["commit", "-am", "upstream edit"]);
    git(&repo, &["push", "origin", "main"]);
    git(&repo, &["checkout", "topic"]);

    larch()
        .args(["push", "rebase", "--no-push"])
        .current_dir(&repo)
        .assert()
        .code(1)
        .stdout("CONFLICT_FILES=file.txt\n");
    // Without --keep-on-conflict the rebase is aborted, leaving a clean tree.
    assert!(!rebase_in_progress(&repo), "rebase should be aborted");
    assert_fsck_clean(&repo);
}

#[test]
fn checkpoint_probe_routes_nontrivial_conflict_and_keeps_rebase() {
    let temp = TempDir::new().expect("tempdir");
    let repo = init_repo(temp.path());
    publish_main(temp.path(), &repo, "origin");
    git(&repo, &["checkout", "-b", "topic"]);
    fs::write(repo.join("file.txt"), "topic\n").expect("write topic");
    git(&repo, &["commit", "-am", "topic edit"]);
    git(&repo, &["checkout", "main"]);
    fs::write(repo.join("file.txt"), "upstream\n").expect("write upstream");
    git(&repo, &["commit", "-am", "upstream edit"]);
    git(&repo, &["push", "origin", "main"]);
    git(&repo, &["checkout", "topic"]);

    larch()
        .args([
            "push",
            "checkpoint-probe",
            "4.r",
            "commit (impl)",
            "--base-remote",
            "origin",
            "--base-ref",
            "main",
        ])
        .current_dir(&repo)
        .assert()
        .code(1)
        .stdout(
            "REBASE_RC=1\nREBASE_OUTCOME=conflict\nROUTE=conflict\nCONFLICT_FILES=file.txt\nCHECKPOINT_NEXT=load-routing\n",
        )
        .stderr("→ rebase-probe: 4.r commit (impl)\n");
    // --keep-on-conflict leaves the rebase in progress for the conflict handoff.
    assert!(
        rebase_in_progress(&repo),
        "rebase should be kept in progress"
    );
    assert_fsck_clean(&repo);
}

#[test]
fn checkpoint_probe_auto_resolves_trivial_larch_logs_conflict() {
    let temp = TempDir::new().expect("tempdir");
    let repo = init_repo(temp.path());
    fs::create_dir_all(repo.join("larch-logs")).expect("create larch-logs");
    fs::write(repo.join("larch-logs/run.md"), "base\n").expect("write log");
    git(&repo, &["add", "larch-logs/run.md"]);
    git(&repo, &["commit", "-m", "seed log"]);
    publish_main(temp.path(), &repo, "origin");
    // topic changes the log (trivial) plus a source file (preserved on continue).
    git(&repo, &["checkout", "-b", "topic"]);
    fs::write(repo.join("larch-logs/run.md"), "topic\n").expect("write log");
    fs::write(repo.join("src.txt"), "topic-src\n").expect("write src");
    git(&repo, &["add", "-A"]);
    git(&repo, &["commit", "-m", "topic work"]);
    git(&repo, &["checkout", "main"]);
    fs::write(repo.join("larch-logs/run.md"), "upstream\n").expect("write log");
    git(&repo, &["commit", "-am", "upstream log"]);
    git(&repo, &["push", "origin", "main"]);
    git(&repo, &["checkout", "topic"]);

    let assert = larch()
        .args([
            "push",
            "checkpoint-probe",
            "4.r",
            "commit (impl)",
            "--base-remote",
            "origin",
            "--base-ref",
            "main",
        ])
        .current_dir(&repo)
        .assert()
        .code(0)
        .stderr("→ rebase-probe: 4.r commit (impl)\n");
    let stdout = String::from_utf8_lossy(&assert.get_output().stdout).into_owned();
    assert!(
        stdout.starts_with(
            "REBASE_RC=0\nREBASE_OUTCOME=ok\nROUTE=continue\nCHECKPOINT_NEXT=continue\n"
        ),
        "unexpected routing rows: {stdout}"
    );
    // The phantom probe tail composes onto the success output.
    assert!(
        stdout.contains("PHANTOM_STATUS="),
        "missing phantom tail: {stdout}"
    );
    // checkout --ours during a rebase keeps origin/main's log; the source change survives.
    assert!(!rebase_in_progress(&repo), "rebase should complete");
    assert_eq!(
        fs::read_to_string(repo.join("larch-logs/run.md")).expect("read log"),
        "upstream\n"
    );
    assert_eq!(
        fs::read_to_string(repo.join("src.txt")).expect("read src"),
        "topic-src\n"
    );
    assert_fsck_clean(&repo);
}

#[test]
fn checkpoint_probe_forked_target_defaults_to_upstream() {
    let temp = TempDir::new().expect("tempdir");
    let repo = init_repo(temp.path());
    // Publish to an `upstream` remote only; `--forked-target true` selects it.
    publish_main(temp.path(), &repo, "upstream");
    git(&repo, &["checkout", "-b", "topic"]);
    fs::write(repo.join("topic.txt"), "topic\n").expect("write topic");
    git(&repo, &["add", "topic.txt"]);
    git(&repo, &["commit", "-m", "topic work"]);

    let assert = larch()
        .args([
            "push",
            "checkpoint-probe",
            "7.r",
            "commit (review)",
            "--forked-target",
            "true",
        ])
        .current_dir(&repo)
        .assert()
        .code(0)
        .stderr("→ rebase-probe: 7.r commit (review)\n");
    let stdout = String::from_utf8_lossy(&assert.get_output().stdout).into_owned();
    assert!(
        stdout.starts_with(
            "REBASE_RC=0\nSKIPPED_ALREADY_FRESH=true\nREBASE_OUTCOME=skipped\nROUTE=continue\nCHECKPOINT_NEXT=continue\n"
        ),
        "forked target should resolve upstream/main as already fresh: {stdout}"
    );
    assert_fsck_clean(&repo);
}

#[test]
fn checkpoint_probe_rejects_malformed_positionals() {
    let temp = TempDir::new().expect("tempdir");
    let repo = init_repo(temp.path());

    for args in [
        vec!["push", "checkpoint-probe", "only-one"],
        vec!["push", "checkpoint-probe", "a", "b", "c"],
        vec![
            "push",
            "checkpoint-probe",
            "a",
            "b",
            "--forked-target",
            "maybe",
        ],
    ] {
        larch()
            .args(&args)
            .current_dir(&repo)
            .assert()
            .code(2)
            .stdout("");
    }
}
