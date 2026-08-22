//! Frozen black-box compatibility cases for the retired Python command pair.

use std::process::{Command, Output};

fn larch(arguments: &[&str]) -> Output {
    Command::new(env!("CARGO_BIN_EXE_larch"))
        .args(arguments)
        .output()
        .expect("run larch command")
}

#[test]
fn governance_gate_help_matches_frozen_argparse_output() {
    let output = larch(&["issue", "governance-gate", "--help"]);
    assert_eq!(output.status.code(), Some(0));
    assert_eq!(
        String::from_utf8_lossy(&output.stdout),
        "usage: larch issue governance-gate [-h] --issue ISSUE --repo REPO --body-file\n                                   BODY_FILE --repo-root REPO_ROOT --head-sha\n                                   HEAD_SHA [--preflight-envelope]\n\noptions:\n  -h, --help            show this help message and exit\n  --issue ISSUE\n  --repo REPO\n  --body-file BODY_FILE\n  --repo-root REPO_ROOT\n  --head-sha HEAD_SHA\n  --preflight-envelope\n"
    );
    assert!(output.stderr.is_empty());
}

#[test]
fn plan_receipt_refresh_help_matches_frozen_argparse_output() {
    let output = larch(&["plan-receipt", "refresh", "--help"]);
    assert_eq!(output.status.code(), Some(0));
    assert_eq!(
        String::from_utf8_lossy(&output.stdout),
        "usage: larch plan-receipt refresh [-h] --issue ISSUE [--repo REPO] --repo-root\n                                  REPO_ROOT --preflight-tmpdir\n                                  PREFLIGHT_TMPDIR --base-ref BASE_REF\n                                  --previous-base-sha PREVIOUS_BASE_SHA\n                                  --base-sha BASE_SHA\n\noptions:\n  -h, --help            show this help message and exit\n  --issue ISSUE\n  --repo REPO\n  --repo-root REPO_ROOT\n  --preflight-tmpdir PREFLIGHT_TMPDIR\n  --base-ref BASE_REF\n  --previous-base-sha PREVIOUS_BASE_SHA\n  --base-sha BASE_SHA\n"
    );
    assert!(output.stderr.is_empty());
}

#[test]
fn governance_validation_uses_the_frozen_machine_failure_wire() {
    let output = larch(&[
        "issue",
        "governance-gate",
        "--issue",
        "zero",
        "--repo",
        "owner/repo",
        "--body-file",
        "/missing/body",
        "--repo-root",
        "/missing/repo",
        "--head-sha",
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "--preflight-envelope",
    ]);
    assert_eq!(output.status.code(), Some(2));
    assert_eq!(
        String::from_utf8_lossy(&output.stdout),
        "GOVERNANCE_OK=false\nENVELOPE_ERROR=--issue must be a positive issue number\n"
    );
    assert_eq!(
        String::from_utf8_lossy(&output.stderr),
        "ERROR: governance-gate: --issue must be a positive issue number\n"
    );
}

#[test]
fn refresh_validation_uses_the_frozen_machine_failure_wire() {
    let output = larch(&[
        "plan-receipt",
        "refresh",
        "--issue",
        "0",
        "--repo-root",
        "/missing/repo",
        "--preflight-tmpdir",
        "/missing/preflight",
        "--base-ref",
        "origin/main",
        "--previous-base-sha",
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "--base-sha",
        "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    ]);
    assert_eq!(output.status.code(), Some(2));
    assert_eq!(
        String::from_utf8_lossy(&output.stdout),
        "PLAN_RECEIPT_REFRESHED=false\n"
    );
    assert_eq!(
        String::from_utf8_lossy(&output.stderr),
        "ERROR: plan-receipt refresh: --issue must be a positive issue number\n"
    );
}
