//! Black-box argv and pre-write refusal coverage for `design publish` (#8591).
//!
//! The in-crate phase-machine tests script every sibling verb; these cases run
//! the real binary so the dispatch route, the argv contract, and the earliest
//! refusals are proven end to end without GitHub, git writes, or Python.

use std::{fs, process::Command};

use tempfile::TempDir;

/// Run `design publish` with `arguments` and no ambient publish attempt id.
fn publish(arguments: &[&str]) -> std::process::Output {
    Command::new(env!("CARGO_BIN_EXE_larch"))
        .args(["design", "publish"])
        .args(arguments)
        .env("LARCH_QUIET_DISABLE", "1")
        .env_remove("LARCH_DESIGN_PUBLISH_ATTEMPT_ID")
        .output()
        .expect("larch runs")
}

/// Exit code for `output`, treating a signal death as a test failure.
fn code(output: &std::process::Output) -> i32 {
    output.status.code().unwrap_or_else(|| {
        panic!(
            "design publish died without an exit code; stderr: {}",
            String::from_utf8_lossy(&output.stderr)
        )
    })
}

/// A design tmpdir plus the argv that addresses it.
fn design_tmpdir() -> TempDir {
    TempDir::new().expect("design tmpdir")
}

#[test]
fn help_exits_zero_before_touching_the_design_tmpdir() {
    for token in ["-h", "--help"] {
        let output = publish(&[token]);
        assert_eq!(code(&output), 0, "{token} should exit 0");
    }
}

#[test]
fn a_missing_or_malformed_argv_line_is_a_hard_failure() {
    let design = design_tmpdir();
    let tmpdir = design.path().to_string_lossy().into_owned();
    // Each case drops or corrupts exactly one required element of the contract:
    // the tmpdir, the issue, the `--session-id` flag itself, the pid, a value,
    // the repo slug shape, and the flag vocabulary.
    let cases: Vec<Vec<&str>> = vec![
        vec!["--issue", "42", "--session-id", "", "--claude-pid", "7"],
        vec![
            "--design-tmpdir",
            &tmpdir,
            "--session-id",
            "",
            "--claude-pid",
            "7",
        ],
        vec!["--design-tmpdir", &tmpdir, "--issue", "42", "--claude-pid", "7"],
        vec!["--design-tmpdir", &tmpdir, "--issue", "42", "--session-id", ""],
        vec![
            "--design-tmpdir",
            &tmpdir,
            "--issue",
            "0",
            "--session-id",
            "",
            "--claude-pid",
            "7",
        ],
        vec![
            "--design-tmpdir",
            &tmpdir,
            "--issue",
            "forty-two",
            "--session-id",
            "",
            "--claude-pid",
            "7",
        ],
        vec![
            "--design-tmpdir",
            &tmpdir,
            "--issue",
            "42",
            "--session-id",
            "",
            "--claude-pid",
            "7",
            "--repo",
            "not a slug",
        ],
        vec![
            "--design-tmpdir",
            &tmpdir,
            "--issue",
            "42",
            "--session-id",
            "",
            "--claude-pid",
            "7",
            "--unknown-flag",
            "x",
        ],
        vec!["--design-tmpdir"],
    ];
    for case in cases {
        let output = publish(&case);
        assert_eq!(code(&output), 5, "argv {case:?} should exit 5");
    }
}

#[test]
fn an_absent_step_5b_sentinel_is_a_hard_failure_that_writes_no_result_env() {
    let design = design_tmpdir();
    let output = publish(&[
        "--design-tmpdir",
        &design.path().to_string_lossy(),
        "--issue",
        "8591",
        "--session-id",
        "",
        "--claude-pid",
        "7",
        "--skip-validate",
    ]);
    assert_eq!(code(&output), 5);
    assert!(
        !design.path().join(".design-publish-result.env").exists(),
        "publish must not checkpoint before the Step 5b gate"
    );
}

#[test]
fn a_rejected_attempt_id_is_a_hard_failure_before_the_step_5b_gate() {
    let design = design_tmpdir();
    let completed = design.path().join(".completed");
    fs::create_dir_all(&completed).expect("completed dir");
    fs::write(completed.join("step-5b"), b"").expect("step-5b sentinel");
    let output = Command::new(env!("CARGO_BIN_EXE_larch"))
        .args([
            "design",
            "publish",
            "--design-tmpdir",
            &design.path().to_string_lossy(),
            "--issue",
            "8591",
            "--session-id",
            "",
            "--claude-pid",
            "7",
        ])
        .env("LARCH_QUIET_DISABLE", "1")
        .env("LARCH_DESIGN_PUBLISH_ATTEMPT_ID", "short")
        .output()
        .expect("larch runs");
    assert_eq!(code(&output), 5);
    assert!(!design.path().join(".design-publish-result.env").exists());
}
