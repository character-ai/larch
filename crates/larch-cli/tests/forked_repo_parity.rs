//! Black-box compatibility contracts for Rust-owned `forked-repo setup` (#8798).

use std::{path::Path, process::Command};

const USAGE: &str = "Usage: setup --upstream owner/repo --fork owner/repo [--mirror-confirmed] [--init-submodules]\n";

fn run(arguments: &[&str]) -> std::process::Output {
    run_in(
        arguments,
        &Path::new(env!("CARGO_MANIFEST_DIR")).join("../.."),
    )
}

fn run_in(arguments: &[&str], directory: &Path) -> std::process::Output {
    Command::new(env!("CARGO_BIN_EXE_larch"))
        .args(arguments)
        .current_dir(directory)
        .output()
        .expect("run larch")
}

#[test]
fn argument_streams_retain_the_frozen_python_contract() {
    for (arguments, code, expected) in [
        (&["forked-repo", "setup", "--help"][..], 0, USAGE.to_owned()),
        (
            &["forked-repo", "setup", "--unknown"][..],
            1,
            format!("{USAGE}ERROR: unknown argument: --unknown\n"),
        ),
        (
            &["forked-repo", "setup", "--fork", "me/project"][..],
            1,
            "ERROR: missing --upstream\n".to_owned(),
        ),
        (
            &[
                "forked-repo",
                "setup",
                "--upstream",
                "invalid",
                "--fork",
                "me/project",
            ][..],
            1,
            "ERROR: --upstream must have owner/repo shape\n".to_owned(),
        ),
    ] {
        let output = run(arguments);
        assert_eq!(output.status.code(), Some(code));
        assert!(output.stdout.is_empty());
        assert_eq!(String::from_utf8(output.stderr).unwrap(), expected);
    }
}

#[test]
fn repository_preflight_failure_is_stderr_only() {
    let directory = tempfile::tempdir().expect("temporary non-repository");
    let output = run_in(
        &[
            "forked-repo",
            "setup",
            "--upstream",
            "acme/project",
            "--fork",
            "me/project",
        ],
        directory.path(),
    );
    assert_eq!(output.status.code(), Some(1));
    assert!(output.stdout.is_empty());
    assert_eq!(
        String::from_utf8(output.stderr).unwrap(),
        "ERROR: not inside a Git working repository\n"
    );
}
