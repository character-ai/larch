//! Frozen black-box parity for the deterministic CI monitor contracts (#8619).
//!
//! These cases were captured from the Python owner before its atomic removal.
//! Live GitHub and Git history reads are covered at their typed adapter and
//! domain boundaries; this suite pins the public argv, stdout, stderr, and exit
//! envelopes without requiring credentials or a network.

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
fn wait_validation_keeps_its_exit_and_diagnostic_contract() {
    assert_fragments(&["ci", "wait", "--pr", "1", "--repo", "o/r", "--iteration", "-1"], 1, "", "ERROR: --iteration must be a non-negative integer, got: -1");
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
