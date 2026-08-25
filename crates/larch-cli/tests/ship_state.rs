//! Black-box coverage for the Rust-owned ship-state seed and wire contract.

use std::fs;

use assert_cmd::Command as AssertCommand;
use tempfile::TempDir;

fn command() -> AssertCommand {
    AssertCommand::cargo_bin("larch").expect("larch binary")
}

fn seed_args(root: &TempDir, manifest: &std::path::Path) -> Vec<String> {
    vec![
        "ship".to_owned(),
        "seed-initial-state".to_owned(),
        "--tmpdir".to_owned(),
        root.path().display().to_string(),
        "--state-file".to_owned(),
        root.path().join("ship-pr-state.sh").display().to_string(),
        "--branch".to_owned(),
        "feature/ship".to_owned(),
        "--issue".to_owned(),
        "42".to_owned(),
        "--repo".to_owned(),
        "owner/repo".to_owned(),
        "--run-id".to_owned(),
        "run-42".to_owned(),
        "--manifest-path".to_owned(),
        manifest.display().to_string(),
        "--tool-label".to_owned(),
        "Codex".to_owned(),
        "--merge".to_owned(),
        "true".to_owned(),
        "--draft".to_owned(),
        "true".to_owned(),
        "--forked".to_owned(),
        "true".to_owned(),
        "--repo-unavailable".to_owned(),
        "false".to_owned(),
        "--deferred".to_owned(),
        "true".to_owned(),
        "--no-admin-fallback".to_owned(),
        "true".to_owned(),
        "--no-logs-commit".to_owned(),
        "true".to_owned(),
        "--expected-session-id".to_owned(),
        "sid".to_owned(),
        "--expected-tmpdir-basename-prefix".to_owned(),
        "claude-implement-larch-".to_owned(),
    ]
}

#[test]
fn seed_writes_the_frozen_ordered_private_state() {
    let root = TempDir::new().expect("tmpdir");
    let manifest = root.path().join("manifest.json");
    fs::write(&manifest, "{\"summary_bullets\":[\"Ship\"]}\n").expect("manifest");

    let output = command()
        .args(seed_args(&root, &manifest))
        .output()
        .expect("seed command");
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(output.stdout.is_empty());
    assert!(output.stderr.is_empty());

    let expected = format!(
        concat!(
            "PHASE=checks\n",
            "BRANCH_NAME=feature/ship\n",
            "ISSUE_NUMBER=42\n",
            "RUN_ID=run-42\n",
            "REPO=owner/repo\n",
            "REPO_UNAVAILABLE=false\n",
            "FORKED_TARGET=true\n",
            "MERGE=true\n",
            "DRAFT=true\n",
            "DEFERRED=true\n",
            "PR_CLOSED=false\n",
            "DONE_RENAME_APPLIED=false\n",
            "STALL_TRACKING=false\n",
            "STALL_STEP=\n",
            "BAIL_NEEDS_USER_INPUT=false\n",
            "BAIL_REASON=\n",
            "BAIL_FAILURE_DETAIL_LOG=\n",
            "CI_PASSED=false\n",
            "PR_NUMBER=\n",
            "PR_URL=\n",
            "PR_TITLE=\n",
            "RESUME_PHASE=\n",
            "CALLER_KIND=\n",
            "REBASE_COUNT=0\n",
            "FIX_ATTEMPTS=0\n",
            "ITERATION=0\n",
            "TRANSIENT_RETRIES=0\n",
            "FAILED_RUN_ID=\n",
            "MANIFEST_PATH={}\n",
            "TOOL_LABEL=Codex\n",
            "DESIGN_ONLY_DONE=false\n",
            "EXPECTED_SESSION_ID=sid\n",
            "EXPECTED_TMPDIR_BASENAME_PREFIX=claude-implement-larch-\n",
            "NO_ADMIN_FALLBACK=true\n",
            "NO_LOGS_COMMIT=true\n",
            "IMPLEMENT_TMPDIR={}\n",
            "CI_FIX_REBASE_PENDING=false\n",
            "OOS_PENDING=false\n",
            "EMERGENCY_REPAIR_BRANCH=\n",
            "ORIGINAL_BRANCH_FORBIDDEN=false\n",
            "MAIN_REPAIR_RUN_ID=\n",
            "MAIN_REPAIR_HEAD=\n",
            "EMERGENCY_REPAIR_PR_NUMBER=\n",
            "MAIN_HEALTH_REPAIR_COMMITTED=false\n",
            "MAIN_HEALTH_REPAIR_FAILED_RUN_ID=\n",
            "MAIN_HEALTH_REPAIR_BASE_SHA=\n",
            "MAIN_HEALTH_REPAIR_HEAD=\n",
            "MAIN_HEALTH_HEAD_SHA=\n",
        ),
        manifest.display(),
        root.path().display(),
    );
    let state = root.path().join("ship-pr-state.sh");
    assert_eq!(fs::read_to_string(&state).expect("state"), expected);
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt as _;
        assert_eq!(
            fs::metadata(state).expect("metadata").permissions().mode() & 0o777,
            0o600
        );
    }
}

#[test]
fn seed_is_create_only_and_manifest_validation_is_fail_closed() {
    let root = TempDir::new().expect("tmpdir");
    let state = root.path().join("ship-pr-state.sh");
    fs::write(&state, "PHASE=checks\nPR_NUMBER=7\n").expect("state");
    let before = fs::read_to_string(&state).expect("before");
    let missing = root.path().join("missing.json");

    let output = command()
        .args(seed_args(&root, &missing))
        .output()
        .expect("seed command");
    assert_eq!(output.status.code(), Some(2));
    assert!(String::from_utf8_lossy(&output.stderr).contains("create-if-absent only"));
    assert_eq!(fs::read_to_string(&state).expect("after"), before);

    fs::remove_file(&state).expect("remove state");
    let output = command()
        .args(seed_args(&root, &missing))
        .output()
        .expect("seed command");
    assert_eq!(output.status.code(), Some(2));
    assert!(
        String::from_utf8_lossy(&output.stderr)
            .contains("MANIFEST_PATH must point at a readable JSON manifest")
    );
    assert!(!state.exists());
}

#[test]
fn missing_required_arguments_keep_the_argparse_exit_contract() {
    let help = command()
        .args(["ship", "seed-initial-state", "--help"])
        .output()
        .expect("help");
    assert_eq!(help.status.code(), Some(1));
    assert!(String::from_utf8_lossy(&help.stdout).contains("Seed initial ship-pr state"));

    let output = command()
        .args(["ship", "seed-initial-state"])
        .output()
        .expect("seed command");
    assert_eq!(output.status.code(), Some(2));
    assert!(output.stdout.is_empty());
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(stderr.starts_with("usage: cli.py [-h] --tmpdir TMPDIR"));
    assert!(stderr.ends_with(
        "cli.py: error: the following arguments are required: --tmpdir, --branch, --issue, --repo, --run-id\n"
    ));
}

#[test]
fn result_env_command_publishes_the_typed_mixed_case_contract() {
    let root = TempDir::new().expect("tmpdir");
    let sink = root.path().join("ship.result.env");
    let output = command()
        .args([
            "ship",
            "write-result-env",
            "--tmpdir",
            &root.path().display().to_string(),
            "--path",
            &sink.display().to_string(),
        ])
        .write_stdin(concat!(
            r#"{"outcome":"NEEDS_USER_INPUT","needs_user_reason":"main-ci-fail","pr_number":7,"detail":"line one\nline two","ledger_ready":true,"ledger_exit_code":3,"ci_errors_distill_class":"github-log-failure"}"#,
            "\n",
        ))
        .output()
        .expect("result env command");
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(output.stdout.is_empty());
    let text = fs::read_to_string(&sink).expect("result env");
    assert!(text.starts_with(
        "outcome=NEEDS_USER_INPUT\nNEEDS_USER_REASON=main-ci-fail\nFAILED_RUN_ID=\nPR_NUMBER=7\n"
    ));
    assert!(text.contains("DETAIL=line one line two\nledger_ready=true\n"));
    assert!(text.ends_with(
        "CI_ERRORS_FILE=\nFAILED_JOBS_COUNT=0\nCI_ERRORS_DISTILL_CLASS=github-log-failure\n"
    ));
}
