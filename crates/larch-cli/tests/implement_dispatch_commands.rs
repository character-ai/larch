//! Black-box coverage for implement recovery-paths and run-step-checks.

use std::{
    fs,
    path::{Path, PathBuf},
    process::Output,
};

use assert_cmd::Command;
use tempfile::TempDir;

fn larch(args: &[&str]) -> Output {
    Command::cargo_bin("larch")
        .expect("larch binary")
        .args(args)
        .output()
        .expect("run larch")
}

fn larch_env(args: &[&str], env: &[(&str, &str)], cwd: Option<&Path>) -> Output {
    let mut cmd = Command::cargo_bin("larch").expect("larch binary");
    cmd.args(args);
    for (key, value) in env {
        cmd.env(key, value);
    }
    if let Some(cwd) = cwd {
        cmd.current_dir(cwd);
    }
    cmd.output().expect("run larch")
}

fn plugin_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..")
}

#[test]
fn recovery_paths_empty_exits_one() {
    let root = TempDir::new().expect("temp");
    let repo = root.path().join("repo");
    let tmp = root.path().join("tmp");
    fs::create_dir_all(&repo).expect("repo");
    fs::create_dir_all(&tmp).expect("tmp");
    for name in [
        "step2-prelaunch-porcelain.nul",
        "step2-postlaunch-porcelain.nul",
        "step2-prelaunch-content-digests.txt",
    ] {
        fs::write(tmp.join(name), b"").expect("fixture");
    }
    let output = larch(&[
        "implement",
        "recovery-paths",
        "--repo-root",
        repo.to_str().expect("utf8"),
        "--tmpdir",
        tmp.to_str().expect("utf8"),
    ]);
    assert_eq!(output.status.code(), Some(1));
}

#[test]
fn recovery_paths_nonempty_exits_zero() {
    let root = TempDir::new().expect("temp");
    let repo = root.path().join("repo");
    let tmp = root.path().join("tmp");
    fs::create_dir_all(&repo).expect("repo");
    fs::create_dir_all(&tmp).expect("tmp");
    fs::write(repo.join("new.txt"), b"body").expect("file");
    fs::write(tmp.join("step2-prelaunch-porcelain.nul"), b"").expect("pre");
    fs::write(tmp.join("step2-postlaunch-porcelain.nul"), b"?? new.txt\0").expect("post");
    fs::write(tmp.join("step2-prelaunch-content-digests.txt"), b"").expect("digests");
    let output = larch(&[
        "implement",
        "recovery-paths",
        "--repo-root",
        repo.to_str().expect("utf8"),
        "--tmpdir",
        tmp.to_str().expect("utf8"),
    ]);
    assert_eq!(output.status.code(), Some(0));
    let out = fs::read(tmp.join("step2-recovery-paths.nul")).expect("out");
    assert!(out.windows(8).any(|w| w == b"new.txt\0"));
}

#[test]
fn recovery_paths_requires_tmpdir() {
    let output = larch(&["implement", "recovery-paths", "--repo-root", "/tmp"]);
    assert_eq!(output.status.code(), Some(2));
}

#[test]
fn run_step_checks_requires_tmpdir() {
    let output = larch_env(
        &["implement", "run-step-checks", "--site", "step3"],
        &[("CLAUDE_PLUGIN_ROOT", plugin_root().to_str().expect("utf8"))],
        None,
    );
    assert_eq!(output.status.code(), Some(2));
    let err = String::from_utf8_lossy(&output.stderr);
    assert!(err.contains("IMPLEMENT_TMPDIR"));
}

#[test]
fn run_step_checks_help_exits_zero() {
    let output = larch(&["implement", "run-step-checks", "--help"]);
    assert_eq!(output.status.code(), Some(0));
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(stdout.contains("--site"));
}

#[test]
fn recovery_paths_help_exits_zero() {
    let output = larch(&["implement", "recovery-paths", "--help"]);
    assert_eq!(output.status.code(), Some(0));
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(stdout.contains("--repo-root"));
}

#[test]
fn recovery_paths_capture_postlaunch_writes_porcelain() {
    let root = TempDir::new().expect("temp");
    let repo = root.path().join("repo");
    let tmp = root.path().join("tmp");
    fs::create_dir_all(&repo).expect("repo");
    fs::create_dir_all(&tmp).expect("tmp");
    let init = std::process::Command::new("git")
        .args(["init", "-q"])
        .current_dir(&repo)
        .status()
        .expect("git init");
    assert!(init.success());
    fs::write(repo.join("tracked.txt"), b"body").expect("file");
    let add = std::process::Command::new("git")
        .args(["add", "tracked.txt"])
        .current_dir(&repo)
        .status()
        .expect("git add");
    assert!(add.success());
    let commit = std::process::Command::new("git")
        .args([
            "-c",
            "user.email=t@t",
            "-c",
            "user.name=t",
            "commit",
            "-qm",
            "init",
        ])
        .current_dir(&repo)
        .status()
        .expect("git commit");
    assert!(commit.success());
    fs::write(repo.join("new.txt"), b"new").expect("untracked");
    for name in [
        "step2-prelaunch-porcelain.nul",
        "step2-prelaunch-content-digests.txt",
    ] {
        fs::write(tmp.join(name), b"").expect("fixture");
    }
    let output = larch(&[
        "implement",
        "recovery-paths",
        "--repo-root",
        repo.to_str().expect("utf8"),
        "--tmpdir",
        tmp.to_str().expect("utf8"),
        "--capture-postlaunch",
    ]);
    assert_eq!(output.status.code(), Some(0));
    let porcelain = fs::read(tmp.join("step2-postlaunch-porcelain.nul")).expect("porcelain");
    assert!(porcelain.windows(7).any(|w| w == b"new.txt"));
}
