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
        "usage: larch plan-receipt refresh [-h] --issue ISSUE [--repo REPO] --repo-root\n                                  REPO_ROOT --preflight-tmpdir\n                                  PREFLIGHT_TMPDIR --base-ref BASE_REF\n                                  --previous-base-sha PREVIOUS_BASE_SHA\n                                  --base-sha BASE_SHA [--run-id RUN_ID]\n                                  [--stage STAGE]\n\noptions:\n  -h, --help            show this help message and exit\n  --issue ISSUE\n  --repo REPO\n  --repo-root REPO_ROOT\n  --preflight-tmpdir PREFLIGHT_TMPDIR\n  --base-ref BASE_REF\n  --previous-base-sha PREVIOUS_BASE_SHA\n  --base-sha BASE_SHA\n  --run-id RUN_ID       implementation run lease; required after Step 0 when\n                        no RUN_ID/LARCH_RUN_ID/SESSION_ID env key names it\n  --stage STAGE         scope-drift record stage: preflight (default) or ship\n"
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

#[test]
fn refresh_rejects_an_invalid_run_id_lease_before_any_read() {
    let output = larch(&[
        "plan-receipt",
        "refresh",
        "--issue",
        "8993",
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
        "--run-id",
        "bad run id",
    ]);
    assert_eq!(output.status.code(), Some(2));
    assert_eq!(
        String::from_utf8_lossy(&output.stdout),
        "PLAN_RECEIPT_REFRESHED=false\n"
    );
    assert!(
        String::from_utf8_lossy(&output.stderr)
            .starts_with("ERROR: plan-receipt refresh: --run-id "),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
}

#[test]
fn refresh_rejects_an_unknown_scope_drift_stage_before_any_read() {
    for stage in ["postflight", ""] {
        let output = larch(&[
            "plan-receipt",
            "refresh",
            "--issue",
            "9006",
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
            "--stage",
            stage,
        ]);
        assert_eq!(output.status.code(), Some(2), "stage={stage:?}");
        assert_eq!(
            String::from_utf8_lossy(&output.stdout),
            "PLAN_RECEIPT_REFRESHED=false\n",
            "stage={stage:?}"
        );
        assert_eq!(
            String::from_utf8_lossy(&output.stderr),
            "ERROR: plan-receipt refresh: --stage must be preflight or ship\n",
            "stage={stage:?}"
        );
    }
}
