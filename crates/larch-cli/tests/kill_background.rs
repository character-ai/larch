#![cfg(unix)]

use assert_cmd::Command;
use predicates::prelude::*;
use std::{
    ffi::OsString,
    fs,
    os::unix::{ffi::OsStringExt, fs::PermissionsExt as _},
    path::PathBuf,
};
use tempfile::TempDir;

fn larch() -> Command {
    Command::cargo_bin("larch").expect("larch binary")
}

fn design_tmpdir(root: &TempDir) -> PathBuf {
    let dir = root.path().join("claude-design-coverage");
    fs::create_dir_all(&dir).expect("design dir");
    fs::write(dir.join("source-env.sh"), "DESIGN_TMPDIR=x\n").expect("marker");
    dir
}

#[test]
fn help_prints_usage() {
    larch()
        .args(["session", "kill-background-processes", "--help"])
        .assert()
        .success()
        .stdout(predicate::str::contains(
            "Usage: session kill-background-processes",
        ));
}

#[test]
fn missing_tmpdir_is_a_usage_error() {
    larch()
        .args(["session", "kill-background-processes"])
        .assert()
        .code(2)
        .stderr(predicate::str::contains(
            "ERROR=--design-tmpdir is required",
        ));
}

#[test]
fn rejects_relative_and_traversal_paths() {
    larch()
        .args([
            "session",
            "kill-background-processes",
            "--design-tmpdir",
            "relative/path",
        ])
        .assert()
        .code(2)
        .stderr(predicate::str::contains("absolute path"));

    larch()
        .args([
            "session",
            "kill-background-processes",
            "--design-tmpdir",
            "/tmp/claude-design-bad/../other",
        ])
        .assert()
        .code(2)
        .stderr(predicate::str::contains("'..' segments"));
}

#[test]
fn rejects_newline_in_path() {
    larch()
        .args([
            "session",
            "kill-background-processes",
            "--design-tmpdir",
            "/tmp/claude-design-bad\npath",
        ])
        .assert()
        .code(2)
        .stderr(predicate::str::contains("newline"));
}

#[test]
fn rejects_both_flags_and_unknown_args() {
    larch()
        .args([
            "session",
            "kill-background-processes",
            "--design-tmpdir",
            "/tmp/a",
            "--implement-tmpdir",
            "/tmp/b",
        ])
        .assert()
        .code(2)
        .stderr(predicate::str::contains("pass only one"));

    larch()
        .args(["session", "kill-background-processes", "--nope"])
        .assert()
        .code(2)
        .stderr(predicate::str::contains("unknown argument"));
}

#[test]
fn rejects_missing_marker_and_bad_basename() {
    let root = TempDir::new().expect("tmpdir");
    let env_tmpdir = root.path().to_path_buf();
    let no_marker = env_tmpdir.join("claude-design-no-marker");
    fs::create_dir_all(&no_marker).expect("dir");
    larch()
        .env("TMPDIR", &env_tmpdir)
        .args([
            "session",
            "kill-background-processes",
            "--design-tmpdir",
            no_marker.to_str().expect("utf8"),
        ])
        .assert()
        .code(2)
        .stderr(predicate::str::contains("source-env.sh"));

    let wrong_name = env_tmpdir.join("not-design");
    fs::create_dir_all(&wrong_name).expect("dir");
    larch()
        .env("TMPDIR", &env_tmpdir)
        .args([
            "session",
            "kill-background-processes",
            "--design-tmpdir",
            wrong_name.to_str().expect("utf8"),
        ])
        .assert()
        .code(2)
        .stderr(predicate::str::contains(
            "basename must start with claude-design-",
        ));
}

#[test]
fn rejects_symlinked_design_tmpdir() {
    let root = TempDir::new().expect("tmpdir");
    let env_tmpdir = root.path().to_path_buf();
    let real = design_tmpdir(&root);
    let link = env_tmpdir.join("claude-design-link");
    std::os::unix::fs::symlink(&real, &link).expect("symlink");
    larch()
        .env("TMPDIR", &env_tmpdir)
        .args([
            "session",
            "kill-background-processes",
            "--design-tmpdir",
            link.to_str().expect("utf8"),
        ])
        .assert()
        .code(2)
        .stderr(predicate::str::contains("symlink"));
}

#[test]
fn succeeds_for_valid_design_tmpdir() {
    let root = TempDir::new().expect("tmpdir");
    let env_tmpdir = root.path().to_path_buf();
    let design = design_tmpdir(&root);
    larch()
        .env("TMPDIR", &env_tmpdir)
        .args([
            "session",
            "kill-background-processes",
            "--design-tmpdir",
            design.to_str().expect("utf8"),
        ])
        .assert()
        .success()
        .stdout(predicate::str::contains("KILLED="));
}

#[test]
fn implement_tmpdir_path_is_accepted() {
    let root = TempDir::new().expect("tmpdir");
    let env_tmpdir = root.path().to_path_buf();
    let implement = env_tmpdir.join("claude-implement-repo-coverage");
    fs::create_dir_all(&implement).expect("dir");
    let mut perms = fs::metadata(&implement).expect("meta").permissions();
    perms.set_mode(0o700);
    fs::set_permissions(&implement, perms).expect("mode");
    larch()
        .env("TMPDIR", &env_tmpdir)
        .args([
            "session",
            "kill-background-processes",
            "--implement-tmpdir",
            implement.to_str().expect("utf8"),
        ])
        .assert()
        .success()
        .stdout(predicate::str::contains("KILLED="));
}

#[test]
fn rejects_missing_flag_values_and_non_directories() {
    larch()
        .args(["session", "kill-background-processes", "--design-tmpdir"])
        .assert()
        .code(2)
        .stderr(predicate::str::contains("requires a value"));

    larch()
        .args(["session", "kill-background-processes", "--implement-tmpdir"])
        .assert()
        .code(2)
        .stderr(predicate::str::contains("requires a value"));

    let root = TempDir::new().expect("tmpdir");
    let env_tmpdir = root.path().to_path_buf();
    let file = env_tmpdir.join("claude-design-file");
    fs::write(&file, "not a dir\n").expect("file");
    larch()
        .env("TMPDIR", &env_tmpdir)
        .args([
            "session",
            "kill-background-processes",
            "--design-tmpdir",
            file.to_str().expect("utf8"),
        ])
        .assert()
        .code(2)
        .stderr(predicate::str::contains("must name a directory"));
}

#[test]
fn short_help_flag_works() {
    larch()
        .args(["session", "kill-background-processes", "-h"])
        .assert()
        .success()
        .stdout(predicate::str::contains("Usage:"));
}

#[test]
fn rejects_non_utf8_argument() {
    larch()
        .args([
            OsString::from("session"),
            OsString::from("kill-background-processes"),
            OsString::from_vec(b"bad-\xff-arg".to_vec()),
        ])
        .assert()
        .code(2)
        .stderr(predicate::str::contains("unknown argument"));
}

#[test]
fn rejects_missing_directory_and_outside_allowlist() {
    let root = TempDir::new().expect("tmpdir");
    let env_tmpdir = root.path().to_path_buf();
    let missing = env_tmpdir.join("claude-design-missing-dir");
    larch()
        .env("TMPDIR", &env_tmpdir)
        .args([
            "session",
            "kill-background-processes",
            "--design-tmpdir",
            missing.to_str().expect("utf8"),
        ])
        .assert()
        .code(2)
        .stderr(predicate::str::contains("must exist and be a directory"));

    let outside = PathBuf::from("/var/empty/larch-kill-background-outside-8061");
    larch()
        .env("TMPDIR", &env_tmpdir)
        .env_remove("XDG_CACHE_HOME")
        .args([
            "session",
            "kill-background-processes",
            "--design-tmpdir",
            outside.to_str().expect("utf8"),
        ])
        .assert()
        .code(2)
        .stderr(predicate::str::contains("allowlist").or(predicate::str::contains("directory")));
}

#[test]
fn rejects_dot_segment_in_path() {
    larch()
        .args([
            "session",
            "kill-background-processes",
            "--design-tmpdir",
            "/tmp/./claude-design-dot",
        ])
        .assert()
        .code(2)
        .stderr(
            predicate::str::contains("'.'")
                .or(predicate::str::contains("must exist"))
                .or(predicate::str::contains("allowlist"))
                .or(predicate::str::contains("directory")),
        );
}
