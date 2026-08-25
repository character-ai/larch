//! Black-box contracts for the CI failure and repair-input commands.
//!
//! Live GitHub reads are covered at their typed adapter and domain boundaries;
//! this suite pins the public argv, stdout, stderr, and exit envelopes without
//! requiring credentials or a network.

use assert_cmd::Command;

fn larch() -> Command {
    Command::cargo_bin("larch").expect("larch binary")
}

#[rustfmt::skip]
fn assert_fragments(args: &[&str], code: i32, stdout: &str, stderr: &str) {
    let output = larch().args(args).output().expect("run larch");
    assert_eq!(output.status.code(), Some(code), "{args:?}");
    assert!(String::from_utf8_lossy(&output.stdout).contains(stdout), "{args:?}");
    assert!(String::from_utf8_lossy(&output.stderr).contains(stderr), "{args:?}");
}

#[test]
#[rustfmt::skip]
fn required_arguments_match_the_frozen_python_usage() {
    let cases: &[(&[&str], i32, &str)] = &[
        (&["ci", "failed-jobs"], 2, "usage: cli.py ci failed-jobs [-h] --run-id RUN_ID --repo REPO\n                             [--output-tsv OUTPUT_TSV]\ncli.py ci failed-jobs: error: the following arguments are required: --run-id, --repo"),
        (&["ci", "distill-log"], 2, "usage: cli.py ci distill-log [-h] --run-id RUN_ID --repo REPO --output OUTPUT\ncli.py ci distill-log: error: the following arguments are required: --run-id, --repo, --output"),
        (&["ci", "rerun-failed"], 1, "usage: cli.py ci rerun-failed [-h] --run-id RUN_ID --repo REPO\ncli.py ci rerun-failed: error: the following arguments are required: --run-id, --repo"),
        (&["ci", "main-health"], 2, "cli.py ci main-health: error: the following arguments are required: --repo"),
    ];
    for (args, code, stderr) in cases {
        assert_fragments(args, *code, "", stderr);
    }
}

#[test]
#[rustfmt::skip]
fn help_keeps_the_frozen_option_tables_and_exit_codes() {
    let cases: &[(&[&str], i32, &str)] = &[
        (&["ci", "failed-jobs", "--help"], 2, "  --output-tsv OUTPUT_TSV"),
        (&["ci", "distill-log", "--help"], 0, "usage: cli.py ci distill-log [-h] --run-id RUN_ID --repo REPO --output OUTPUT"),
        (&["ci", "rerun-failed", "--help"], 1, "  --run-id RUN_ID"),
        (&["ci", "behind-count", "--help"], 2, "  --base-remote BASE_REMOTE"),
        (&["ci", "main-health", "--help"], 2, "  --upstream-repo UPSTREAM_REPO"),
    ];
    for (args, code, stdout) in cases {
        assert_fragments(args, *code, stdout, "");
    }
}

/// `--skip-flap-check` is the one deliberate extension past the frozen surface.
///
/// The retired owner reached that behavior only through its Python library
/// query object. With the CLI as sole owner, the ship driver needs a public
/// spelling for it, so this case pins the added option rather than leaving it
/// undocumented.
#[test]
#[rustfmt::skip]
fn the_flap_check_override_is_a_documented_public_option() {
    assert_fragments(&["ci", "main-health", "--help"], 2, "                             [--skip-flap-check]", "");
    assert_fragments(&["ci", "main-health", "--help"], 2, "\n  --skip-flap-check", "");
}

#[test]
#[rustfmt::skip]
fn validation_refusals_precede_every_github_read() {
    let cases: &[(&[&str], i32, &str)] = &[
        (&["ci", "failed-jobs", "--run-id", "abc", "--repo", "o/r"], 1, "ERROR: --run-id must be numeric"),
        (&["ci", "failed-jobs", "--run-id", "12", "--repo", "nope"], 1, "ERROR: --repo must be owner/name"),
        (&["ci", "rerun-failed", "--run-id", "", "--repo", "o/r"], 1, "ERROR: --run-id must be numeric"),
        (&["ci", "distill-log", "--run-id", "abc", "--repo", "o/r", "--output", "/tmp/d.md"], 2, "ERROR: --run-id must be numeric"),
        (&["ci", "distill-log", "--run-id", "12", "--repo", "nope", "--output", "/tmp/d.md"], 2, "ERROR: --repo must be owner/name"),
        (&["ci", "main-health", "--repo", "o/r", "--limit", "-1"], 2, "ERROR: --limit must be a non-negative integer, got: -1"),
        (&["ci", "main-health", "--repo", "o/r", "--timeout", "nope"], 2, "argument --timeout: invalid int value: 'nope'"),
    ];
    for (args, code, stderr) in cases {
        assert_fragments(args, *code, "", stderr);
    }
}

#[test]
#[rustfmt::skip]
fn an_undeclared_session_root_refuses_the_digest_before_any_read() {
    let output = larch()
        .args(["ci", "distill-log", "--run-id", "12", "--repo", "o/r", "--output", "/tmp/larch-8620-digest.md"])
        .env_remove("IMPLEMENT_TMPDIR")
        .output()
        .expect("run larch");
    assert_eq!(output.status.code(), Some(2));
    assert!(String::from_utf8_lossy(&output.stderr).contains("ERROR: --output must resolve under IMPLEMENT_TMPDIR"));
}

#[test]
#[rustfmt::skip]
fn behind_count_fails_open_to_zero_outside_a_repository() {
    let directory = tempfile::tempdir().expect("empty directory");
    larch()
        .args(["ci", "behind-count", "--no-fetch"])
        .current_dir(directory.path())
        .assert()
        .success()
        .stdout("BEHIND_COUNT=0\n");
    larch()
        .args(["ci", "behind-count", "--base-remote", "bad remote", "--no-fetch"])
        .current_dir(directory.path())
        .assert()
        .success()
        .stdout("BEHIND_COUNT=0\n");
}

#[test]
#[rustfmt::skip]
fn a_malformed_repository_still_emits_the_full_rerun_envelope() {
    let output = larch().args(["ci", "rerun-failed", "--run-id", "12", "--repo", "nope"]).output().expect("run larch");
    assert_eq!(output.status.code(), Some(0));
    let stdout = String::from_utf8_lossy(&output.stdout).into_owned();
    assert!(stdout.starts_with("RERUN_SUBMITTED=false\nALREADY_RUNNING=false\nERROR="), "{stdout}");
}
