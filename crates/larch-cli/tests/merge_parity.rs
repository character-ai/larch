//! Black-box contracts for the Rust-owned `merge pr` and `merge wait` commands (#8788).

use std::{path::Path, process::Command};

use tempfile::TempDir;

fn run(arguments: &[&str]) -> std::process::Output {
    Command::new(env!("CARGO_BIN_EXE_larch"))
        .args(arguments)
        .current_dir(Path::new(env!("CARGO_MANIFEST_DIR")).join("../.."))
        .output()
        .expect("run larch")
}

#[test]
fn help_retains_the_frozen_python_wire_and_exit() {
    let pr = run(&["merge", "pr", "--help"]);
    assert_eq!(pr.status.code(), Some(1));
    assert!(pr.stderr.is_empty());
    assert_eq!(
        String::from_utf8(pr.stdout).expect("UTF-8 help"),
        "usage: cli.py merge pr [-h] --pr PR --repo REPO [--no-admin-fallback]\n                       [--method {squash,merge}]\n\noptions:\n  -h, --help            show this help message and exit\n  --pr PR\n  --repo REPO\n  --no-admin-fallback\n  --method {squash,merge}\n"
    );

    let wait = run(&["merge", "wait", "--help"]);
    assert_eq!(wait.status.code(), Some(1));
    assert!(wait.stderr.is_empty());
    assert_eq!(
        String::from_utf8(wait.stdout).expect("UTF-8 help"),
        "usage: cli.py merge wait [-h] --pr PR --repo REPO\n\noptions:\n  -h, --help   show this help message and exit\n  --pr PR\n  --repo REPO\n"
    );
}

#[test]
fn argparse_refusals_retain_exit_one_and_exact_diagnostics() {
    let missing = run(&["merge", "pr"]);
    assert_eq!(missing.status.code(), Some(1));
    assert!(missing.stdout.is_empty());
    assert_eq!(
        String::from_utf8(missing.stderr).expect("UTF-8 stderr"),
        "usage: cli.py merge pr [-h] --pr PR --repo REPO [--no-admin-fallback]\n                       [--method {squash,merge}]\ncli.py merge pr: error: the following arguments are required: --pr, --repo\n"
    );

    let invalid = run(&["merge", "pr", "--pr", "nope", "--repo", "o/r"]);
    assert_eq!(invalid.status.code(), Some(1));
    assert!(invalid.stdout.is_empty());
    assert!(
        String::from_utf8_lossy(&invalid.stderr)
            .ends_with("cli.py merge pr: error: argument --pr: invalid int value: 'nope'\n")
    );
}

#[test]
fn setup_failures_use_the_frozen_result_envelopes() {
    let directory = TempDir::new().expect("temporary non-repository");
    let pr = Command::new(env!("CARGO_BIN_EXE_larch"))
        .args(["merge", "pr", "--pr", "7", "--repo", "o/r"])
        .current_dir(directory.path())
        .output()
        .expect("run merge pr");
    assert!(pr.status.success());
    let stdout = String::from_utf8(pr.stdout).expect("UTF-8 stdout");
    assert!(stdout.starts_with("MERGE_RESULT=error\nERROR="));
    assert_eq!(stdout.lines().count(), 2);
    assert!(pr.stderr.is_empty());

    let wait = Command::new(env!("CARGO_BIN_EXE_larch"))
        .args(["merge", "wait", "--pr", "7", "--repo", "o/r"])
        .current_dir(directory.path())
        .output()
        .expect("run merge wait");
    assert_eq!(wait.status.code(), Some(1));
    assert!(String::from_utf8_lossy(&wait.stdout).starts_with("MERGE_RESULT=error\nERROR="));
    assert!(wait.stderr.is_empty());
}
