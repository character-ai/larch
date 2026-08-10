//! End-to-end wire checks for Rust-owned run-audit compatibility verbs.

use std::{
    fs,
    path::{Path, PathBuf},
    process::Command,
};

use serde_json::Value;
use tempfile::TempDir;

fn larch() -> Command {
    Command::new(env!("CARGO_BIN_EXE_larch"))
}

fn prepare_scan_fixture(root: &Path) -> (PathBuf, PathBuf) {
    let run = root.join("larch-logs/implement/run-1");
    fs::create_dir_all(run.join("round-3")).expect("run tree");
    fs::write(
        run.join("manifest.json"),
        r#"{"schema_version":2,"pr_number":7,"ended_at":"done","larch_version":"56.2.2","steps_ran":{}}"#,
    )
    .expect("manifest");
    fs::write(
        run.join("review-findings-full.jsonl"),
        concat!(
            r#"{"id":"OOS_1","phase":"plan-review","outcome":"accepted","category":"wrong-category"}"#,
            "\n",
            "{\"id\":\"REJ_1\",\"phase\":\"code-review\",\"outcome\":\"rejected\",\"category\":false,\"prose_body\":\"### FINDING_X: correctness\"}",
        ),
    )
    .expect("findings");
    fs::write(
        run.join("round-3/voting-tally.md"),
        "| FINDING_A | 0 | 0 | 1 | text | rejected |\n",
    )
    .expect("tally");
    let scans = root.join("scans.tsv");
    fs::write(
        &scans,
        concat!(
            "name\ttype\n",
            "required-file-presence\tfiles\n",
            "exon-misclassification\tgrep\n",
            "oos-category-mangle\tjson\n",
            "rej-category-blank\tjson\n",
            "ns-retry-sidecars\tfiles\n",
            "cursor-ci-stall-causes\tjson\n",
            "codex-round1-adherence\tjson\n",
            "codex-generalist-waste\tjson\n",
            "execution-issues-categories\tjson\n",
            "cache-freshness\tjson\n",
            "changelog-rebase-conflicts\tjson\n",
            "coder-tool\tjson\n",
            "trailing-content-no-issues-found\tjson\n",
            "oos-silent-drop\tjson\n",
            "invariant-ship-outcome\tjson\n",
            "guideline-ship-outcome\tjson\n",
        ),
    )
    .expect("scan registry");
    (run, scans)
}

fn assert_scan_rows(rows: &[Value]) {
    for (scan_name, result) in [
        ("required-file-presence", "skip"),
        ("exon-misclassification", "fail"),
        ("oos-category-mangle", "fail"),
        ("rej-category-blank", "fail"),
        ("ns-retry-sidecars", "skip"),
        ("cursor-ci-stall-causes", "pass"),
        ("codex-round1-adherence", "pass"),
        ("codex-generalist-waste", "skip"),
        ("execution-issues-categories", "skip"),
        ("cache-freshness", "skip"),
        ("changelog-rebase-conflicts", "skip"),
        ("coder-tool", "pass"),
        ("trailing-content-no-issues-found", "skip"),
        ("oos-silent-drop", "skip"),
        ("invariant-ship-outcome", "informational"),
        ("guideline-ship-outcome", "informational"),
    ] {
        assert!(
            rows.iter()
                .any(|row| row["scan"] == scan_name && row["result"] == result),
            "missing {result} scan output for {scan_name}"
        );
    }
    assert!(rows.iter().any(|row| {
        row["scan"] == "exon-misclassification"
            && row["pr"] == 7
            && row["result"] == "fail"
            && row["count"] == 1
    }));
    assert!(rows.iter().any(|row| {
        row["scan"] == "oos-category-mangle"
            && row["pr"] == 7
            && row["result"] == "fail"
            && row["count"] == 1
    }));
    assert!(rows.iter().any(|row| {
        row["scan"] == "rej-category-blank" && row["result"] == "fail" && row["count"] == 1
    }));
    assert!(rows.iter().any(|row| {
        row["scan"] == "category-stats" && row["pr"] == 7 && row["partial_data"] == false
    }));
    assert!(rows.iter().any(|row| {
        row["scan"] == "cross-cutting"
            && row["ended_at_null"] == false
            && row["pr_number_null"] == false
            && row["self_deploying_gap"] == false
    }));
}

#[test]
fn scan_and_counter_wires_preserve_structured_artifacts() {
    let sandbox = TempDir::new().expect("sandbox");
    let root = sandbox.path();
    let (run, scans) = prepare_scan_fixture(root);

    let scan = larch()
        .args([
            "audit-runs",
            "scan-run",
            "--skill",
            "implement",
            "--run-dir",
        ])
        .arg(&run)
        .args(["--pr", "7", "--scans-tsv"])
        .arg(&scans)
        .output()
        .expect("scan command");
    assert!(scan.status.success());
    let output = String::from_utf8(scan.stdout).expect("UTF-8 scan output");
    let rows = output
        .lines()
        .map(|line| serde_json::from_str::<Value>(line).expect("scan JSON"))
        .collect::<Vec<_>>();
    assert_scan_rows(&rows);

    let scans_out = root.join("scan-results-7.ndjson");
    fs::write(&scans_out, output).expect("saved scan output");
    let counters = larch()
        .args(["audit-runs", "compute-counters", "--scan-results-dir"])
        .arg(root)
        .output()
        .expect("counter command");
    assert!(counters.status.success());
    let output = String::from_utf8(counters.stdout).expect("UTF-8 counter output");
    assert!(output.contains("SCAN_FILES_FOUND=1\n"));
    assert!(output.contains("EXON_DELTA=1\n"));
    assert!(output.contains("OOS_MANGLED_DELTA=1\n"));
}

#[test]
fn pacific_timestamp_refuses_extra_arguments() {
    let output = larch()
        .args(["audit-runs", "pacific-timestamp", "unexpected"])
        .output()
        .expect("Pacific command");
    assert!(!output.status.success());
    assert_eq!(
        String::from_utf8(output.stderr).expect("UTF-8 stderr"),
        "audit-pacific-timestamp.sh: unexpected argument(s)\n"
    );
}
