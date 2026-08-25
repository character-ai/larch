//! Black-box coverage for the deterministic CI monitor contracts.
//!
//! Live GitHub and Git history reads are covered at their typed adapter and
//! domain boundaries; this suite pins the public argv, stdout, stderr, and exit
//! envelopes without requiring credentials or a network.

use assert_cmd::Command;
use std::{fs, os::unix::fs::PermissionsExt};

fn larch() -> Command {
    Command::cargo_bin("larch").expect("larch binary")
}

#[rustfmt::skip]
fn authenticated_gh() -> tempfile::TempDir {
    let directory=tempfile::tempdir().expect("fake gh directory"); let executable=directory.path().join("gh");
    fs::write(&executable,"#!/bin/sh\nprintf '%s\\n' 'github_pat_000000000000000000000000000000000000'\n").expect("fake gh"); fs::set_permissions(&executable,fs::Permissions::from_mode(0o755)).expect("fake gh mode"); directory
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
fn decide_matrix_matches_the_frozen_python_owner() {
    let cases = [
        ("merged", "0", "false", "", "already_merged", ""),
        ("error", "0", "false", "", "bail", "ci-status-error"),
        ("pass", "0", "false", "", "merge", ""),
        ("pass", "2", "false", "", "merge", ""),
        ("pass", "2", "true", "", "rebase", ""),
        ("pending", "2", "false", "", "wait", ""),
        ("fail", "2", "false", "", "rebase_then_evaluate", ""),
        ("fail", "2", "false", "123", "evaluate_failure", ""),
    ];
    for (status, behind, conflicted, run_id, action, reason) in cases {
        larch().args(["ci", "decide", "--status", status, "--behind", behind, "--conflicted", conflicted, "--failed-run-id", run_id])
            .assert()
            .success()
            .stdout(format!("ACTION={action}\nBAIL_REASON={reason}\n"));
    }

    for (option, value, reason) in [("--rebase-count", "20", "ci-too-many-rebases"), ("--fix-attempts", "10", "fix-attempts-exhausted")] {
        larch().args(["ci", "decide", "--status", "pending", "--behind", "0", option, value])
            .assert().success().stdout(format!("ACTION=bail\nBAIL_REASON={reason}\n"));
    }
}

#[test]
#[rustfmt::skip]
fn decide_validation_matches_the_frozen_python_owner() {
    let cases: &[(&[&str], &str)] = &[
        (&["ci", "decide"], "the following arguments are required: --ci-status/--status, --behind-count/--behind"),
        (&["ci", "decide", "--status", "pass", "--behind", "nope"], "argument --behind-count/--behind: invalid int value: 'nope'"),
        (&["ci", "decide", "--status", "wat", "--behind", "0"], "ERROR: --status must be pass|fail|pending|merged|error, got: wat"),
        (&["ci", "decide", "--status", "pass", "--behind", "-1"], "ERROR: behind_count must be a non-negative integer, got: -1"),
        (&["ci", "decide", "--status", "NO_CHECKS", "--behind", "0"], "ERROR: --status must be pass|fail|pending|merged|error, got: NO_CHECKS"),
        (&["ci", "decide", "--status", "pass", "--behind", "0", "--iteration", "-1"], "ERROR: iteration must be a non-negative integer, got: -1"),
        (&["ci", "decide", "--status", "pass", "--behind", "0", "--rebase-count", "-1"], "ERROR: rebase_count must be a non-negative integer, got: -1"),
        (&["ci", "decide", "--status", "pass", "--behind", "0", "--fix-attempts", "-1"], "ERROR: fix_attempts must be a non-negative integer, got: -1"),
        (&["ci", "decide", "--status", "pass", "--behind", "0", "--conflicted", "maybe"], "ERROR: --conflicted must be true or false, got: maybe"),
    ];
    for (args, error) in cases {
        assert_fragments(args, 1, "", error);
    }
}

#[test]
fn status_usage_failure_keeps_its_fail_open_kv_envelope() {
    larch()
        .args(["ci", "status"])
        .assert()
        .success()
        .stdout("CI_STATUS=error\nBEHIND_COUNT=0\nFAILED_RUN_ID=\nCONFLICTED=false\n")
        .stderr(predicates::str::contains(
            "the following arguments are required: --pr, --repo",
        ));
}

#[test]
#[rustfmt::skip]
fn status_validation_failures_keep_the_fail_open_kv_envelope() {
    let cases: &[&[&str]]=&[&["ci","status","--pr","x","--repo","o/r"],&["ci","status","--pr","1","--repo","owner"],&["ci","status","--pr","1","--repo","o/r","--empty-checks-grace","-1"],&["ci","status","--pr","1","--repo","o/r","--base-ref","bad ref"],&["ci","status","--pr","1","--repo","o/r","--unknown"]];
    for args in cases { assert_fragments(args,0,"CI_STATUS=error",""); }
}

#[test]
#[rustfmt::skip]
fn live_wiring_fails_open_and_publishes_wait_results_without_network_access() {
    let gh=authenticated_gh();
    larch().env("PATH",gh.path()).args(["ci","status","--pr","-1","--repo","o/r"]).assert().success().stdout("CI_STATUS=error\nBEHIND_COUNT=0\nFAILED_RUN_ID=\nCONFLICTED=false\n");
    let output=tempfile::tempdir().expect("wait output directory"); let result=output.path().join("wait.env");
    larch().env("PATH",gh.path()).args(["ci","wait","--pr","-1","--repo","o/r","--iteration","50","--output-file",result.to_str().expect("UTF-8 path")]).assert().success();
    let envelope=fs::read_to_string(&result).expect("wait result"); assert!(envelope.contains("ACTION=bail\n")&&envelope.contains("BAIL_REASON=ci-timeout\n")); assert_eq!(fs::read_to_string(result.with_extension("env.done")).unwrap(),"0\n");
}

#[test]
#[rustfmt::skip]
fn wait_validation_keeps_its_exit_and_diagnostic_contract() {
    assert_fragments(&["ci", "wait", "--pr", "1", "--repo", "o/r", "--iteration", "-1"], 1, "", "ERROR: --iteration must be a non-negative integer, got: -1");
}

#[test]
#[rustfmt::skip]
fn wait_rejects_an_output_path_that_cannot_be_cleaned() {
    let directory=tempfile::tempdir().expect("temporary output directory");
    larch().args(["ci","wait","--pr","1","--repo","o/r","--output-file",directory.path().to_str().expect("UTF-8 path")]).assert().failure();
}

#[test]
fn help_keeps_the_frozen_python_exit_contract() {
    for (verb, code, output) in [
        ("decide", 1, "usage: cli.py ci decide"),
        ("wait", 1, "usage: cli.py ci wait"),
        ("status", 0, "CI_STATUS=error"),
    ] {
        assert_fragments(&["ci", verb, "--help"], code, output, "");
    }
}
