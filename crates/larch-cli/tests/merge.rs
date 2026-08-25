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
    for (arguments, expected) in [
        (
            &["merge", "pr", "--help"][..],
            "usage: cli.py merge pr [-h] --pr PR --repo REPO [--no-admin-fallback]\n                       [--method {squash,merge}]\n\noptions:\n  -h, --help            show this help message and exit\n  --pr PR\n  --repo REPO\n  --no-admin-fallback\n  --method {squash,merge}\n",
        ),
        (
            &["merge", "wait", "--help"][..],
            "usage: cli.py merge wait [-h] --pr PR --repo REPO\n\noptions:\n  -h, --help   show this help message and exit\n  --pr PR\n  --repo REPO\n",
        ),
    ] {
        let output = run(arguments);
        assert_eq!(output.status.code(), Some(1));
        assert!(output.stderr.is_empty());
        assert_eq!(
            String::from_utf8(output.stdout).expect("UTF-8 help"),
            expected
        );
    }
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
    for (verb, expected) in [("pr", Some(0)), ("wait", Some(1))] {
        let output = Command::new(env!("CARGO_BIN_EXE_larch"))
            .args(["merge", verb, "--pr", "7", "--repo", "o/r"])
            .current_dir(directory.path())
            .output()
            .expect("run merge command");
        assert_eq!(output.status.code(), expected);
        let stdout = String::from_utf8(output.stdout).expect("UTF-8 stdout");
        assert!(stdout.starts_with("MERGE_RESULT=error\nERROR="));
        assert_eq!(stdout.lines().count(), 2);
        assert!(output.stderr.is_empty());
    }
}
