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

#[test]
fn title_matching_nudge_and_prior_close_keep_their_command_wires() {
    let title = larch()
        .args([
            "audit-runs",
            "title",
            "--skill",
            "implement",
            "--pr-list",
            "3,1,2",
            "--timestamp",
            "T",
        ])
        .output()
        .expect("title command");
    assert!(title.status.success());
    assert_eq!(
        String::from_utf8(title.stdout).expect("UTF-8 title output"),
        "TITLE=[Implement Run Logs Audit T Report] PRs #1-#3\n"
    );

    let matching = larch()
        .args([
            "audit-runs",
            "title-match",
            "--skill",
            "design",
            "--title",
            "[Design Run Logs Audit T Report]",
        ])
        .output()
        .expect("title-match command");
    assert!(matching.status.success());
    assert!(matching.stdout.is_empty());

    let nudge = larch()
        .args([
            "audit-runs",
            "bugs-backlog-nudge",
            "--repo",
            "not-a-repository",
            "--root",
            ".",
        ])
        .output()
        .expect("nudge command");
    assert_eq!(nudge.status.code(), Some(2));
    assert_eq!(
        String::from_utf8(nudge.stderr).expect("UTF-8 nudge stderr"),
        "audit-runs bugs-backlog-nudge: --repo must be OWNER/REPO\n"
    );

    let refused = larch()
        .args([
            "audit-runs",
            "close-priors",
            "--skill",
            "implement",
            "--new-issue-number",
            "99",
        ])
        .output()
        .expect("close-priors command");
    assert_eq!(refused.status.code(), Some(5));
    assert_eq!(
        String::from_utf8(refused.stdout).expect("UTF-8 close-priors output"),
        "CLOSE_PRIORS_REFUSED=true\nREASON=unauthorized-mutation:unauthorized-mutation\n"
    );
}

#[test]
fn cutover_verbs_keep_usage_and_refusal_wires() {
    // issue-search: missing required option is a usage error.
    let missing = larch()
        .args(["audit-runs", "issue-search", "--repo", "o/r"])
        .output()
        .expect("issue-search command");
    assert_eq!(missing.status.code(), Some(2));
    assert!(
        String::from_utf8(missing.stderr)
            .expect("UTF-8 stderr")
            .contains("--keywords")
    );

    // fix-merge: a malformed --repo shape is rejected before any network.
    let bad_repo = larch()
        .args([
            "audit-runs",
            "fix-merge",
            "--repo",
            "not-a-repository",
            "--issue",
            "12",
        ])
        .output()
        .expect("fix-merge command");
    assert_eq!(bad_repo.status.code(), Some(2));
    assert!(
        String::from_utf8(bad_repo.stderr)
            .expect("UTF-8 stderr")
            .contains("--repo must be OWNER/REPO")
    );

    // label-check: both options are required.
    let no_label = larch()
        .args(["audit-runs", "label-check", "--repo", "o/r"])
        .output()
        .expect("label-check command");
    assert_eq!(no_label.status.code(), Some(2));

    // version-window: the instant must parse before any repository access.
    let bad_after = larch()
        .args([
            "audit-runs",
            "version-window",
            "--repo-root",
            ".",
            "--after",
            "not-an-instant",
        ])
        .output()
        .expect("version-window command");
    assert_eq!(bad_after.status.code(), Some(2));
    assert!(
        String::from_utf8(bad_after.stderr)
            .expect("UTF-8 stderr")
            .contains("--after must be an ISO-8601 instant")
    );

    // comment: omitting --operator-invoked refuses before body or network.
    let refused = larch()
        .args([
            "audit-runs",
            "comment",
            "--repo",
            "o/r",
            "--issue",
            "7",
            "--body-file",
            "missing-body.md",
        ])
        .output()
        .expect("comment command");
    assert_eq!(refused.status.code(), Some(5));
    assert_eq!(
        String::from_utf8(refused.stdout).expect("UTF-8 comment output"),
        "COMMENT_REFUSED=true\nREASON=unauthorized-mutation:unauthorized-mutation\n"
    );
}

fn fixture_git(root: &Path, date: &str, args: &[&str]) {
    let status = Command::new("git")
        .args([
            "-c",
            "user.email=audit@test",
            "-c",
            "user.name=audit",
            "-c",
            "commit.gpgsign=false",
        ])
        .args(args)
        .env("GIT_AUTHOR_DATE", date)
        .env("GIT_COMMITTER_DATE", date)
        .current_dir(root)
        .status()
        .expect("git command");
    assert!(status.success(), "git {args:?} failed");
}

fn write_manifest(root: &Path, version: &str) {
    fs::create_dir_all(root.join(".claude-plugin")).expect("manifest directory");
    fs::write(
        root.join(".claude-plugin/plugin.json"),
        format!("{{\"name\":\"larch\",\"version\":\"{version}\"}}\n"),
    )
    .expect("manifest");
}

#[test]
fn version_window_resolves_the_first_bump_after_the_instant() {
    let sandbox = TempDir::new().expect("sandbox");
    let root = sandbox.path();
    fixture_git(root, "2026-08-01T00:00:00Z", &["init", "-q"]);
    write_manifest(root, "34.0.0");
    fixture_git(root, "2026-08-01T00:00:00Z", &["add", "."]);
    fixture_git(
        root,
        "2026-08-01T00:00:00Z",
        &["commit", "-qm", "Bump version to 34.0.0"],
    );
    write_manifest(root, "35.0.0");
    fixture_git(root, "2026-08-03T00:00:00Z", &["add", "."]);
    fixture_git(
        root,
        "2026-08-03T00:00:00Z",
        &["commit", "-qm", "Bump version to 35.0.0"],
    );
    fs::write(root.join("unrelated.txt"), "no manifest change\n").expect("unrelated file");
    fixture_git(root, "2026-08-04T00:00:00Z", &["add", "."]);
    fixture_git(
        root,
        "2026-08-04T00:00:00Z",
        &[
            "commit",
            "-qm",
            "Bump version prose without a manifest change",
        ],
    );
    write_manifest(root, "36.0.0");
    fixture_git(root, "2026-08-05T00:00:00Z", &["add", "."]);
    fixture_git(
        root,
        "2026-08-05T00:00:00Z",
        &["commit", "-qm", "Bump version to 36.0.0"],
    );

    // The earliest bump strictly after the instant wins, not the newest one.
    let output = larch()
        .args(["audit-runs", "version-window", "--repo-root"])
        .arg(root)
        .args([
            "--after",
            "2026-08-02T00:00:00Z",
            "--audited-versions",
            "34.0.0,34.0.1",
        ])
        .output()
        .expect("version-window command");
    assert!(output.status.success());
    let stdout = String::from_utf8(output.stdout).expect("UTF-8 output");
    assert!(stdout.contains("BUMP_SHA="), "missing BUMP_SHA: {stdout}");
    assert!(
        !stdout.contains("BUMP_SHA=none"),
        "unexpected none: {stdout}"
    );
    assert!(
        stdout.contains("FIX_SHIPPED_VERSION=35.0.0"),
        "wrong shipped version: {stdout}"
    );
    assert!(stdout.contains("IN_SCOPE=false\nDECISION=skip\n"));

    // Overlap with an audited version keeps the finding in scope.
    let output = larch()
        .args(["audit-runs", "version-window", "--repo-root"])
        .arg(root)
        .args([
            "--after",
            "2026-08-02T00:00:00Z",
            "--audited-versions",
            "34.0.0,35.0.0",
        ])
        .output()
        .expect("version-window command");
    assert!(output.status.success());
    let stdout = String::from_utf8(output.stdout).expect("UTF-8 output");
    assert!(stdout.contains("IN_SCOPE=true\nDECISION=propose\n"));

    // No bump after the instant reports unknown without a decision override.
    let output = larch()
        .args(["audit-runs", "version-window", "--repo-root"])
        .arg(root)
        .args([
            "--after",
            "2026-08-09T00:00:00Z",
            "--audited-versions",
            "34.0.0",
        ])
        .output()
        .expect("version-window command");
    assert!(output.status.success());
    let stdout = String::from_utf8(output.stdout).expect("UTF-8 output");
    assert!(stdout.contains("BUMP_SHA=none\nFIX_SHIPPED_VERSION=unknown\n"));
    assert!(stdout.contains("IN_SCOPE=true\nDECISION=propose\n"));
}

#[test]
fn version_window_reports_unknown_for_malformed_manifest_versions() {
    let sandbox = TempDir::new().expect("sandbox");
    let root = sandbox.path();
    fixture_git(root, "2026-08-01T00:00:00Z", &["init", "-q"]);
    fs::create_dir_all(root.join(".claude-plugin")).expect("manifest directory");
    fs::write(
        root.join(".claude-plugin/plugin.json"),
        "{\"name\":\"larch\",\"version\":\"35.0.0-rc1\"}\n",
    )
    .expect("manifest");
    fixture_git(root, "2026-08-03T00:00:00Z", &["add", "."]);
    fixture_git(
        root,
        "2026-08-03T00:00:00Z",
        &["commit", "-qm", "Bump version to 35.0.0-rc1"],
    );

    // A pre-release suffix fails the strict parse: unknown, therefore propose.
    let output = larch()
        .args(["audit-runs", "version-window", "--repo-root"])
        .arg(root)
        .args([
            "--after",
            "2026-08-02T00:00:00Z",
            "--audited-versions",
            "34.0.0",
        ])
        .output()
        .expect("version-window command");
    assert!(output.status.success());
    let stdout = String::from_utf8(output.stdout).expect("UTF-8 output");
    assert!(
        !stdout.contains("BUMP_SHA=none"),
        "bump must resolve: {stdout}"
    );
    assert!(stdout.contains("FIX_SHIPPED_VERSION=unknown"));
    assert!(stdout.contains("IN_SCOPE=true\nDECISION=propose\n"));

    // A missing repository is a distinct failure wire. The plain directory
    // lives in its own sandbox so discovery cannot climb into the fixture repo.
    let plain = TempDir::new().expect("plain sandbox");
    let output = larch()
        .args(["audit-runs", "version-window", "--repo-root"])
        .arg(plain.path())
        .args(["--after", "2026-08-02T00:00:00Z"])
        .output()
        .expect("version-window command");
    assert!(!output.status.success());
    assert!(
        String::from_utf8(output.stdout)
            .expect("UTF-8 output")
            .contains("VERSION_WINDOW_FAILED=true")
    );
}

#[test]
#[allow(clippy::too_many_lines)] // One archived run covers each published scanner contract.
fn scan_and_counter_cover_present_artifacts_and_all_counter_outcomes() {
    let sandbox = TempDir::new().expect("sandbox");
    let root = sandbox.path();
    let run = root.join("larch-logs/implement/complete-run");
    fs::create_dir_all(run.join("round-1")).expect("round one");
    fs::create_dir_all(run.join("round-3")).expect("round three");
    fs::write(
        run.join("manifest.json"),
        r#"{"schema_version":2,"pr_number":8,"ended_at":"done","larch_version":"56.2.2","steps_ran":{"step8":true}}"#,
    )
    .expect("manifest");
    fs::write(run.join("final-summary.md"), "completed\n").expect("summary");
    fs::write(
        run.join("review-findings-full.jsonl"),
        concat!(
            r#"{"id":"OOS_1","phase":"plan-review","outcome":"accepted","category":"security"}"#,
            "\n",
            r#"{"id":"REJ_1","phase":"code-review","outcome":"rejected","category":"security"}"#,
            "\n"
        ),
    )
    .expect("findings");
    fs::write(
        run.join("round-1/round-meta.json"),
        r#"{
          "reviewer_signals":[
            {"ns_retry_reason":"OUTPUT_EMPTY","output_basename":"review.txt","first_pass_trailing_content":true},
            {"output_basename":"codex-generalist-output.txt","result_kind":"NO_ISSUES_FOUND"}
          ],
          "wrapper_logs":{"codex":"125s elapsed"},
          "coder":{"CODER_TOOL":"codex"}
        }"#,
    )
    .expect("round metadata");
    fs::write(run.join("round-1/review-ns-retry.txt"), "retry\n").expect("retry sidecar");
    fs::write(
        run.join("round-3/cursor-ci-stall-one.json"),
        r#"{"channel":"nightly"}"#,
    )
    .expect("stall artifact");
    fs::write(
        run.join("round-3/panel-manifest.ndjson"),
        r#"{"tool":"codex","slot":"generalist"}"#,
    )
    .expect("panel manifest");
    fs::write(run.join("round-3/coder.env"), "CODER_TOOL=cursor\n").expect("coder environment");
    fs::write(run.join("round-3/voting-tally.md"), "no rejected finding\n").expect("tally");
    fs::write(
        run.join("execution-issues.ndjson"),
        concat!(
            r#"{"category":"Warnings","body":"ordinary warning"}"#,
            "\n",
            r#"{"category":"Correctness","body":"changelog rebase conflict"}"#,
            "\n"
        ),
    )
    .expect("execution issues");
    fs::write(
        run.join("architectural-guideline-assessment.md"),
        "Consulted ARCHITECTURAL_GUIDELINES.md; no deviations identified.\n",
    )
    .expect("guideline assessment");
    fs::write(
        run.join("architectural-invariant-assessment.md"),
        "one invariant violation\n",
    )
    .expect("invariant assessment");
    fs::write(
        run.join("architectural-guideline-outcome.json"),
        r#"{"schema_version":"1","phase":"implement","step":"8","base_ref":"origin/main","head_sha":"abc123","outcome":"pinned","reason":"note-pinned","guidelines_status":"present","assessment_kind":"deviation"}"#,
    )
    .expect("guideline outcome");
    fs::write(
        run.join("architectural-invariant-outcome.json"),
        r#"{"schema_version":"1","phase":"implement","step":"8","base_ref":"origin/main","head_sha":"abc123","outcome":"violation","reason":"violation-note","invariants_status":"present","assessment_kind":"violation"}"#,
    )
    .expect("invariant outcome");

    let scans = root.join("complete-scans.tsv");
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
            "guideline-assessment\tjson\n",
            "invariant-assessment\tjson\n",
            "guideline-ship-outcome\tjson\n",
            "invariant-ship-outcome\tjson\n",
        ),
    )
    .expect("scan registry");
    let required = root.join("required-files.tsv");
    fs::write(
        &required,
        "relative_path\tcondition\nmanifest.json\talways\nround-*/voting-tally.md\talways\n",
    )
    .expect("required-files registry");

    let scan = larch()
        .args([
            "audit-runs",
            "scan-run",
            "--skill",
            "implement",
            "--run-dir",
        ])
        .arg(&run)
        .args(["--pr", "8", "--scans-tsv"])
        .arg(&scans)
        .args(["--required-files-tsv"])
        .arg(&required)
        .args(["--current-version", "56.3.0"])
        .output()
        .expect("scan command");
    assert!(scan.status.success());
    let rows = String::from_utf8(scan.stdout)
        .expect("UTF-8 scan output")
        .lines()
        .map(|line| serde_json::from_str::<Value>(line).expect("scan JSON"))
        .collect::<Vec<_>>();
    for (scan, expected) in [
        ("required-file-presence", "pass"),
        ("exon-misclassification", "pass"),
        ("oos-category-mangle", "pass"),
        ("rej-category-blank", "pass"),
        ("ns-retry-sidecars", "fail"),
        ("cursor-ci-stall-causes", "informational"),
        ("codex-round1-adherence", "fail"),
        ("codex-generalist-waste", "fail"),
        ("execution-issues-categories", "fail"),
        ("cache-freshness", "informational"),
        ("changelog-rebase-conflicts", "fail"),
        ("coder-tool", "pass"),
        ("trailing-content-no-issues-found", "fail"),
        ("oos-silent-drop", "skip"),
        ("guideline-assessment", "pass"),
        ("invariant-assessment", "pass"),
        ("guideline-ship-outcome", "pass"),
        ("invariant-ship-outcome", "pass"),
    ] {
        assert!(
            rows.iter()
                .any(|row| row["scan"] == scan && row["result"] == expected),
            "missing {scan}={expected}"
        );
    }
    assert!(
        rows.iter()
            .any(|row| row["scan"] == "category-stats" && row["partial_data"] == false)
    );
    assert!(
        rows.iter()
            .any(|row| row["scan"] == "cross-cutting" && row["self_deploying_gap"] == false)
    );

    let invalid = larch()
        .args([
            "audit-runs",
            "scan-run",
            "--skill",
            "implement",
            "--run-dir",
        ])
        .arg(&run)
        .args(["--pr", "not-a-number", "--scans-tsv"])
        .arg(&scans)
        .output()
        .expect("invalid scan command");
    assert!(!invalid.status.success());
    assert!(
        String::from_utf8(invalid.stdout)
            .expect("UTF-8 invalid output")
            .contains("audit-scan-run-args")
    );

    let counters_dir = root.join("counters");
    fs::create_dir_all(&counters_dir).expect("counters directory");
    fs::write(
        counters_dir.join("scan-results-complete.ndjson"),
        concat!(
            "{\"scan\":\"exon-misclassification\",\"count\":2}\n",
            "{\"scan\":\"oos-category-mangle\",\"count\":3}\n",
            "{\"scan\":\"category-stats\",\"partial_data\":false,\"canonical\":3,\"oos_blank\":2}\n",
            "{\"scan\":\"category-stats\",\"partial_data\":true,\"detail\":\"other partial data\",\"canonical\":4,\"oos_blank\":1}\n",
            "{\"scan\":\"category-stats\",\"partial_data\":true,\"detail\":\"review-findings-full.jsonl not found\",\"canonical\":50,\"oos_blank\":50}\n",
            "{\"scan\":\"ns-retry-sidecars\",\"result\":\"fail\",\"count\":2}\n",
            "{\"scan\":\"ns-retry-sidecars\",\"result\":\"skip\"}\n",
            "{\"scan\":\"changelog-rebase-conflicts\",\"count\":4}\n",
            "{\"scan\":\"guideline-ship-outcome\",\"result\":\"pass\",\"outcome\":\"pinned\"}\n",
            "{\"scan\":\"guideline-ship-outcome\",\"result\":\"pass\",\"outcome\":\"clean\"}\n",
            "{\"scan\":\"guideline-ship-outcome\",\"result\":\"pass\",\"outcome\":\"dropped\"}\n",
            "{\"scan\":\"invariant-ship-outcome\",\"result\":\"pass\",\"outcome\":\"violation\"}\n",
            "{\"scan\":\"invariant-ship-outcome\",\"result\":\"pass\",\"outcome\":\"clean\"}\n",
            "{\"scan\":\"invariant-ship-outcome\",\"result\":\"pass\",\"outcome\":\"dropped\"}\n"
        ),
    )
    .expect("counter rows");
    let prior = root.join("prior.md");
    fs::write(
        &prior,
        concat!(
            "---\n",
            "exon_misclassifications: 4\n",
            "oos_categories_mangled: 5\n",
            "oos_categories_clean: 6\n",
            "oos_categories_blank: 7\n",
            "ns_retries_cursor_specialist: 8\n",
            "ns_retries_cursor_specialist_launches: 9\n",
            "changelog_rebase_conflicts: 10\n",
            "---\n"
        ),
    )
    .expect("prior counters");
    let counters = larch()
        .args(["audit-runs", "compute-counters", "--scan-results-dir"])
        .arg(&counters_dir)
        .args(["--prior-frontmatter"])
        .arg(&prior)
        .output()
        .expect("counter command");
    assert!(counters.status.success());
    let counters = String::from_utf8(counters.stdout).expect("UTF-8 counter output");
    for line in [
        "SCAN_FILES_FOUND=1",
        "EXON_MISCLASSIFICATIONS=6",
        "OOS_CATEGORIES_MANGLED=8",
        "OOS_CATEGORIES_CLEAN=13",
        "OOS_CATEGORIES_BLANK=10",
        "NS_RETRIES_CURSOR_SPECIALIST=11",
        "NS_RETRIES_SKIPPED_RUNS=1",
        "CHANGELOG_REBASE_CONFLICTS=14",
        "GUIDELINE_OUTCOME_RUNS=3",
        "GUIDELINE_OUTCOME_PINNED=1",
        "GUIDELINE_OUTCOME_CLEAN=1",
        "GUIDELINE_OUTCOME_DROPPED=1",
        "GUIDELINE_DROP_RATE_BPS=3333",
        "INVARIANT_OUTCOME_RUNS=3",
        "INVARIANT_OUTCOME_VIOLATION=1",
        "INVARIANT_OUTCOME_CLEAN=1",
        "INVARIANT_OUTCOME_DROPPED=1",
        "CATEGORY_STATS_PARTIAL=true",
    ] {
        assert!(counters.contains(line), "missing {line}");
    }
}
