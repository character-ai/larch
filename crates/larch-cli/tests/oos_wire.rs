//! End-to-end wire contracts for the Rust-owned `oos serialize` and
//! `oos normalize-header` verbs.
//!
//! The findings and serialized goldens stay in lockstep with the core fixtures
//! in `crates/larch-core/tests/issue_oos.rs`.

use std::{
    io::Write as _,
    process::{Command, Stdio},
};

use tempfile::tempdir;

fn larch() -> Command {
    Command::new(env!("CARGO_BIN_EXE_larch"))
}

/// A recorded review artifact: one accepted item, one security hold, one
/// rejected finding, and one tagged out-of-scope finding.
const RECORDED_FINDINGS: &str = concat!(
    "### OOS_3: Retry budget is shared across unrelated calls\n",
    "- **Description**: `crates/larch-core/src/retry.rs:41-88` shares one budget.\n",
    "- **Reviewer**: reviewer-correctness\n",
    "- **Phase**: implement\n",
    "- **focus-area**: correctness\n",
    "Vote tally: 3/3 YES Result=accepted Fileable=true\n",
    "\n",
    "### OOS_4: [security] Token echoed into the run log\n",
    "- **Description**: The vendor tail keeps the bearer token.\n",
    "- **Phase**: implement\n",
    "Vote tally: 3/3 YES Result=accepted Fileable=true\n",
    "\n",
    "### FINDING_5: Fence example quotes a security heading\n",
    "- **Concern**: The doc shows\n",
    "```\n",
    "### OOS_9: [security] example\n",
    "- focus-area: security\n",
    "```\n",
    "  which must stay a finding.\n",
    "Vote tally: 2/3 YES Result=rejected Fileable=false\n",
    "\n",
    "### FINDING_6: [OUT_OF_SCOPE] Widen the flush window\n",
    "- **Description**: `python/larch/report/run_log_flush.py:120-140` and Makefile.\n",
    "- **Phase**: implement\n",
    "Vote tally: 3/3 YES Result=accepted Fileable=true\n",
);

/// The exact bytes `cli.py oos serialize` wrote for `RECORDED_FINDINGS`.
const RECORDED_SERIALIZED: &str = concat!(
    "### OOS_1: Retry budget is shared across unrelated calls\n",
    "- **Description**: `crates/larch-core/src/retry.rs:41-88` shares one budget.\n",
    "- **Reviewer**: reviewer-correctness\n",
    "- **Phase**: implement\n",
    "- **focus-area**: correctness\n",
    "Vote tally: 3/3 YES Result=accepted Fileable=true\n",
    "\n",
    "\n",
    "### OOS_2: [OUT_OF_SCOPE] Widen the flush window\n",
    "- **Description**: `python/larch/report/run_log_flush.py:120-140` and Makefile.\n",
    "- **Phase**: implement\n",
    "Vote tally: 3/3 YES Result=accepted Fileable=true\n",
    "\n",
);

const BLOCK: &str =
    "### FINDING_9: Widen the flush window\n- **Description**: body worth keeping.\n";
const NORMALIZED_BLOCK: &str =
    "### OOS_5: Widen the flush window\n- **Description**: body worth keeping.\n";

#[test]
fn serialize_writes_the_recorded_batch_and_reports_the_recorded_counts() {
    let dir = tempdir().expect("tempdir");
    let findings = dir.path().join("oos-accepted-review.md");
    std::fs::write(&findings, RECORDED_FINDINGS).expect("findings");
    let output = dir.path().join("nested/oos-serialized.md");

    let result = larch()
        .args([
            "oos",
            "serialize",
            "--findings-file",
            findings.to_str().expect("findings path"),
            "--output-file",
            output.to_str().expect("output path"),
            "--session-env-path",
            "/ignored/session.sh",
        ])
        .output()
        .expect("run serialize");

    assert!(result.status.success());
    assert_eq!(
        String::from_utf8(result.stdout).expect("UTF-8 stdout"),
        "OOS_ACCEPTED=2\nOOS_HELD_SECURITY=1\n"
    );
    assert_eq!(
        std::fs::read_to_string(&output).expect("read output"),
        RECORDED_SERIALIZED
    );
}

#[test]
fn serialize_folds_carriage_returns_before_serializing() {
    let dir = tempdir().expect("tempdir");
    let findings = dir.path().join("crlf.md");
    std::fs::write(&findings, RECORDED_FINDINGS.replace('\n', "\r\n")).expect("findings");
    let output = dir.path().join("out.md");

    let result = larch()
        .args([
            "oos",
            "serialize",
            "--findings-file",
            findings.to_str().expect("findings path"),
            "--output-file",
            output.to_str().expect("output path"),
        ])
        .output()
        .expect("run serialize");

    assert!(result.status.success());
    assert_eq!(
        std::fs::read_to_string(&output).expect("read output"),
        RECORDED_SERIALIZED
    );
}

#[test]
fn serialize_refuses_an_absent_findings_file() {
    let dir = tempdir().expect("tempdir");
    let output = dir.path().join("out.md");

    let result = larch()
        .args([
            "oos",
            "serialize",
            "--findings-file",
            "/nonexistent/findings.md",
            "--output-file",
            output.to_str().expect("output path"),
        ])
        .output()
        .expect("run serialize");

    assert_eq!(result.status.code(), Some(2));
    assert_eq!(
        String::from_utf8(result.stderr).expect("UTF-8 stderr"),
        "oos serialize: --findings-file must name a file\n"
    );
    assert!(!output.exists());
}

#[test]
fn serialize_reports_a_missing_required_flag_at_the_argparse_exit_code() {
    let result = larch()
        .args(["oos", "serialize"])
        .output()
        .expect("run serialize");

    assert_eq!(result.status.code(), Some(2));
    assert!(
        String::from_utf8(result.stderr)
            .expect("UTF-8 stderr")
            .contains("the following arguments are required")
    );
}

#[test]
fn normalize_header_rewrites_the_first_line_from_a_block_file() {
    let dir = tempdir().expect("tempdir");
    let block = dir.path().join("block.md");
    std::fs::write(&block, BLOCK).expect("block");

    let result = larch()
        .args([
            "oos",
            "normalize-header",
            "--seq",
            "5",
            "--block-file",
            block.to_str().expect("block path"),
        ])
        .output()
        .expect("run normalize-header");

    assert!(result.status.success());
    assert_eq!(
        String::from_utf8(result.stdout).expect("UTF-8 stdout"),
        NORMALIZED_BLOCK
    );
}

#[test]
fn normalize_header_rewrites_the_first_line_from_stdin() {
    let mut child = larch()
        .args(["oos", "normalize-header", "--seq", "5"])
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("spawn normalize-header");
    child
        .stdin
        .take()
        .expect("stdin")
        .write_all(BLOCK.as_bytes())
        .expect("write stdin");
    let result = child.wait_with_output().expect("wait normalize-header");

    assert!(result.status.success());
    assert_eq!(
        String::from_utf8(result.stdout).expect("UTF-8 stdout"),
        NORMALIZED_BLOCK
    );
}

#[test]
fn normalize_header_refuses_a_malformed_seq() {
    let result = larch()
        .args(["oos", "normalize-header", "--seq", "-1"])
        .output()
        .expect("run normalize-header");

    assert_eq!(result.status.code(), Some(2));
    assert_eq!(
        String::from_utf8(result.stderr).expect("UTF-8 stderr"),
        "oos normalize-header: --seq must be a non-negative integer\n"
    );
}

#[test]
fn normalize_header_refuses_a_block_file_that_is_not_a_file() {
    let result = larch()
        .args([
            "oos",
            "normalize-header",
            "--seq",
            "1",
            "--block-file",
            "/nonexistent/block.md",
        ])
        .output()
        .expect("run normalize-header");

    assert_eq!(result.status.code(), Some(2));
    assert_eq!(
        String::from_utf8(result.stderr).expect("UTF-8 stderr"),
        "oos normalize-header: --block-file must name a file\n"
    );
}
