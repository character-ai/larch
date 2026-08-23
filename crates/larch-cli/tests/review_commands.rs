use std::{fs, path::Path, process::Command};

use assert_cmd::Command as AssertCommand;
use predicates::prelude::*;
use tempfile::TempDir;

const GATHER_CONTEXT_USAGE: &str = "Usage: review gather-context --mode diff|description --output-dir DIR [--description-text TEXT --scope-files FILE]";

fn larch() -> AssertCommand {
    AssertCommand::cargo_bin("larch").expect("larch binary should build")
}

fn write(path: &Path, contents: &str) {
    let parent = path.parent().expect("fixture path has parent");
    fs::create_dir_all(parent).expect("create fixture parent");
    fs::write(path, contents).expect("write fixture");
}

fn git(repository: &Path, arguments: &[&str]) {
    let output = Command::new("git")
        .args(arguments)
        .current_dir(repository)
        .output()
        .expect("run fixture git");
    assert!(
        output.status.success(),
        "git {arguments:?} failed: {}",
        String::from_utf8_lossy(&output.stderr)
    );
}

fn commit(repository: &Path, path: &str, contents: &str, message: &str) {
    write(&repository.join(path), contents);
    git(repository, &["add", path]);
    git(repository, &["commit", "-m", message]);
}

fn repository(fixture: &TempDir) -> std::path::PathBuf {
    let repository = fixture.path().join("repository");
    fs::create_dir(&repository).expect("repository dir");
    git(&repository, &["init", "-b", "main"]);
    git(&repository, &["config", "user.email", "test@example.com"]);
    git(&repository, &["config", "user.name", "Test User"]);
    repository
}

fn ripgrep_path(fixture: &TempDir) -> std::path::PathBuf {
    let directory = fixture.path().join("bin");
    let executable = if cfg!(windows) { "rg.exe" } else { "rg" };
    let path = directory.join(executable);
    write(&path, "");
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt as _;

        fs::set_permissions(&path, fs::Permissions::from_mode(0o755)).expect("make rg executable");
    }
    directory
}

fn plugin_root() -> std::path::PathBuf {
    std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .and_then(std::path::Path::parent)
        .expect("workspace root")
        .to_path_buf()
}

#[cfg(unix)]
fn executable_script(path: &Path, text: &str) {
    use std::os::unix::fs::PermissionsExt as _;

    write(path, text);
    fs::set_permissions(path, fs::Permissions::from_mode(0o755)).expect("make fixture executable");
}

#[test]
fn gather_context_preserves_description_rows_and_content_fallback() {
    let fixture = TempDir::new().expect("fixture");
    let repository = repository(&fixture);
    commit(
        &repository,
        "docs/notes.txt",
        "A UNIQUE FULL PHRASE appears only in this file.\n",
        "base",
    );
    write(
        &repository.join("untracked.txt"),
        "A UNIQUE FULL PHRASE appears only in this file.\n",
    );
    let output = fixture.path().join("context");
    let path = ripgrep_path(&fixture);

    larch()
        .current_dir(&repository)
        .env("PATH", path)
        .args([
            "review",
            "gather-context",
            "--mode",
            "description",
            "--description-text",
            "unique full phrase",
            "--output-dir",
        ])
        .arg(&output)
        .assert()
        .success()
        .stdout(format!(
            "DIFF_FILE=\nFILE_LIST_FILE={}\nCOMMIT_LOG_FILE=\nCOMMIT_COUNT=0\nSCOPE_FILES_COUNT=2\nMODE=description\n",
            output.join("scope-files.txt").display(),
        ));
    assert_eq!(
        fs::read_to_string(output.join("scope-files.txt")).expect("scope file"),
        "docs/notes.txt\nuntracked.txt\n"
    );
}

#[test]
fn gather_context_does_not_treat_untracked_names_as_git_ls_files_matches() {
    let fixture = TempDir::new().expect("fixture");
    let repository = repository(&fixture);
    commit(&repository, "README.md", "base\n", "base");
    write(
        &repository.join("untracked-matching-token.txt"),
        "This file does not contain the full phrase.\n",
    );
    let output = fixture.path().join("context");

    larch()
        .current_dir(&repository)
        .args([
            "review",
            "gather-context",
            "--mode",
            "description",
            "--description-text",
            "matching token",
            "--output-dir",
        ])
        .arg(&output)
        .assert()
        .success()
        .stdout(format!(
            "DIFF_FILE=\nFILE_LIST_FILE={}\nCOMMIT_LOG_FILE=\nCOMMIT_COUNT=0\nSCOPE_FILES_COUNT=0\nMODE=description\n",
            output.join("scope-files.txt").display(),
        ));
    assert_eq!(
        fs::read_to_string(output.join("scope-files.txt")).expect("scope file"),
        ""
    );
}

#[test]
fn gather_context_keeps_the_legacy_no_ripgrep_fallback() {
    let fixture = TempDir::new().expect("fixture");
    let repository = repository(&fixture);
    commit(
        &repository,
        "docs/notes.txt",
        "A UNIQUE FULL PHRASE appears only in this file.\n",
        "base",
    );
    let output = fixture.path().join("context");

    larch()
        .current_dir(&repository)
        .env("PATH", "")
        .args([
            "review",
            "gather-context",
            "--mode",
            "description",
            "--description-text",
            "unique full phrase",
            "--output-dir",
        ])
        .arg(&output)
        .assert()
        .success()
        .stdout(format!(
            "DIFF_FILE=\nFILE_LIST_FILE={}\nCOMMIT_LOG_FILE=\nCOMMIT_COUNT=0\nSCOPE_FILES_COUNT=0\nMODE=description\n",
            output.join("scope-files.txt").display(),
        ));
}

#[test]
fn gather_context_uses_the_current_subdirectory_as_the_legacy_search_root() {
    let fixture = TempDir::new().expect("fixture");
    let repository = repository(&fixture);
    commit(
        &repository,
        "nested/notes.txt",
        "A UNIQUE NESTED PHRASE appears only here.\n",
        "base",
    );
    let output = fixture.path().join("context");
    let path = ripgrep_path(&fixture);

    larch()
        .current_dir(repository.join("nested"))
        .env("PATH", path)
        .args([
            "review",
            "gather-context",
            "--mode",
            "description",
            "--description-text",
            "unique nested phrase",
            "--output-dir",
        ])
        .arg(&output)
        .assert()
        .success();
    assert_eq!(
        fs::read_to_string(output.join("scope-files.txt")).expect("scope file"),
        "notes.txt\n"
    );
}

#[test]
fn gather_context_reuses_branch_collector_and_writes_legacy_sidecar() {
    let fixture = TempDir::new().expect("fixture");
    let repository = repository(&fixture);
    commit(&repository, "src/main.rs", "baseline\n", "base");
    git(&repository, &["checkout", "-b", "feature"]);
    let marker = "REVIEW_GATHER_CONTEXT_MARKER";
    commit(
        &repository,
        "src/main.rs",
        &format!("baseline\n{marker}\n"),
        "feature change",
    );
    let output = fixture.path().join("context");

    larch()
        .current_dir(&repository)
        .args(["review", "gather-context", "--mode", "diff", "--output-dir"])
        .arg(&output)
        .assert()
        .success()
        .stdout(format!(
            "DIFF_FILE={}\nFILE_LIST_FILE={}\nCOMMIT_LOG_FILE={}\nCOMMIT_COUNT=1\nSCOPE_FILES_COUNT=0\nMODE=diff\n",
            output.join("diff.txt").display(),
            output.join("file-list.txt").display(),
            output.join("commit-log.txt").display(),
        ));
    assert!(
        fs::read_to_string(output.join("diff.txt"))
            .expect("diff")
            .contains(marker)
    );
    assert_eq!(
        fs::read_to_string(output.join("gather-branch-context.env")).expect("sidecar"),
        format!(
            "DIFF_FILE={}\nFILE_LIST_FILE={}\nCOMMIT_LOG_FILE={}\nCOMMIT_COUNT=1\n",
            output.join("diff.txt").display(),
            output.join("file-list.txt").display(),
            output.join("commit-log.txt").display(),
        )
    );
}

#[test]
fn gather_context_preserves_diff_failure_rows_and_sidecar() {
    let fixture = TempDir::new().expect("fixture");
    let output = fixture.path().join("context");

    larch()
        .current_dir(fixture.path())
        .args(["review", "gather-context", "--mode", "diff", "--output-dir"])
        .arg(&output)
        .assert()
        .failure()
        .stdout("SCOPE_FILES_COUNT=0\nMODE=diff\n")
        .stderr("gather-branch-context.sh: cannot open repository\n");
    assert_eq!(
        fs::read_to_string(output.join("gather-branch-context.env")).expect("sidecar"),
        ""
    );
}

#[test]
fn collect_findings_preserves_oos_cap_and_claude_collector_records() {
    let fixture = TempDir::new().expect("fixture");
    let review = fixture.path().join("review");
    fs::create_dir_all(&review).expect("review directory");
    let reviewer = review.join("claude-architecture-output.txt");
    write(
        &reviewer,
        "### Out-of-Scope Observations\n- First OOS\n- Second OOS\n- Third OOS\n- Fourth OOS\n### In-Scope Findings\n- Later in-scope finding\n",
    );
    write(&review.join("claude-architecture-output.txt.done"), "0\n");
    let findings = review.join("findings.md");
    let oos = review.join("oos.md");

    larch()
        .env("REVIEW_TMPDIR", &review)
        .env("WAIT_FOR_REVIEWERS_POLL_INTERVAL", "0.01")
        .args([
            "review",
            "collect-findings",
            "--mode",
            "description",
            "--timeout",
            "1",
            "--findings-file",
        ])
        .arg(&findings)
        .arg("--oos-file")
        .arg(&oos)
        .arg("--claude-output-files")
        .arg(&reviewer)
        .assert()
        .success()
        .stdout(format!(
            "FINDINGS_COUNT=4\nOOS_COUNT=3\nDIRTY_DETECTED=false\nCOLLECT_OK=true\nCOLLECTOR_OUTPUT_FILE={}\n",
            review.join("collector-results.env").display(),
        ));
    let finding_text = fs::read_to_string(&findings).expect("findings");
    assert!(finding_text.contains("First OOS"));
    assert!(!finding_text.contains("Fourth OOS"));
    assert!(finding_text.contains("Later in-scope finding"));
    let collector = fs::read_to_string(review.join("collector-results.env")).expect("collector");
    assert!(collector.contains(&format!(
        "REVIEWER_FILE={}\nTOOL=claude\nSTATUS=OK\nEXIT_CODE=0\n",
        reviewer.display()
    )));
    let wait = fs::read_to_string(review.join("wait-for-claude-reviewers.log")).expect("wait log");
    assert!(wait.contains("DONE 1 claude-architecture-output.txt: exit=0"));
}

#[test]
fn collect_findings_records_non_substantive_and_no_findings_claude_slots() {
    let fixture = TempDir::new().expect("fixture");
    let review = fixture.path().join("review");
    fs::create_dir_all(&review).expect("review directory");
    let ok = review.join("claude-ok-output.txt");
    let failed = review.join("claude-failed-output.txt");
    write(&ok, "NO_ISSUES_FOUND\n");
    write(&failed, "A narrative with no finding list.\n");
    write(&review.join("claude-ok-output.txt.done"), "0\n");
    write(&review.join("claude-failed-output.txt.done"), "0\n");
    let findings = review.join("findings.md");
    let oos = review.join("oos.md");

    larch()
        .env("REVIEW_TMPDIR", &review)
        .env("WAIT_FOR_REVIEWERS_POLL_INTERVAL", "0.01")
        .args([
            "review",
            "collect-findings",
            "--mode",
            "description",
            "--timeout",
            "1",
            "--findings-file",
        ])
        .arg(&findings)
        .arg("--oos-file")
        .arg(&oos)
        .arg("--claude-output-files")
        .arg(&ok)
        .arg(&failed)
        .assert()
        .success()
        .stderr(predicate::str::contains(
            "Reviewer claude-failed-output.txt",
        ));
    let collector = fs::read_to_string(review.join("collector-results.env")).expect("collector");
    assert!(collector.contains(&format!(
        "REVIEWER_FILE={}\nTOOL=claude\nSTATUS=OK",
        ok.display()
    )));
    assert!(collector.contains(&format!(
        "REVIEWER_FILE={}\nTOOL=claude\nSTATUS=NOT_SUBSTANTIVE",
        failed.display()
    )));
    assert_eq!(fs::read_to_string(findings).expect("findings"), "");
}

#[test]
fn reviewer_failure_threshold_preserves_frozen_stdout_and_dynamic_drop_behavior() {
    let fixture = TempDir::new().expect("fixture");
    let reviewer = fixture.path().join("dyn-dyn-lint-escalation-output.txt");
    write(&reviewer, "STATUS=NOT_SUBSTANTIVE\n");
    let collector = fixture.path().join("collector-results.env");
    write(
        &collector,
        &format!(
            "REVIEWER_FILE={}\nTOOL=cursor\nSTATUS=OK\nEXIT_CODE=0\n\n",
            reviewer.display()
        ),
    );
    let dropped = fixture.path().join("dropped.tsv");
    write(
        &dropped,
        "dyn-dyn-lint-escalation\tcursor\tstraggler-dropped\tcut\n",
    );
    let manifest = fixture.path().join("panel.ndjson");
    write(
        &manifest,
        &format!(
            "{{\"slot\":\"dyn-dyn-lint-escalation\",\"tool\":\"cursor\",\"output\":\"{}\"}}\n",
            reviewer.display()
        ),
    );
    larch()
        .args([
            "review",
            "check-reviewer-failure-threshold",
            "--collector-results-file",
        ])
        .arg(&collector)
        .args([
            "--panel",
            "hard",
            "--intended-slots",
            "1",
            "--launched-slots",
            "1",
            "--dropped-slots-file",
        ])
        .arg(&dropped)
        .arg("--panel-manifest")
        .arg(&manifest)
        .arg("--reviewer-output-files")
        .arg(&reviewer)
        .assert()
        .success()
        .stdout(
            "INTENDED_SLOTS=1\nSUCCEEDED_SLOTS=1\nFAILED_SLOTS=0\nCOUNTED_SLOTS=1\nNOT_SUBSTANTIVE_SLOTS=0\nDROPPED_SLOTS=1\nDROPPED_STATIC_SLOTS=0\nDYNAMIC_FAILED_SLOTS=0\nDYNAMIC_DROPPED_SLOTS=1\nTHRESHOLD_OK=true\nTHRESHOLD_REASON=\n",
        );
}

#[test]
fn reviewer_failure_threshold_refuses_when_more_than_half_the_panel_failed() {
    let fixture = TempDir::new().expect("fixture");
    let collector = fixture.path().join("collector-results.env");
    write(
        &collector,
        "REVIEWER_FILE=codex-specialist-correctness-output.txt\nSTATUS=OK\n\nREVIEWER_FILE=cursor-specialist-edge-cases-output.txt\nSTATUS=ERROR\n\nREVIEWER_FILE=codex-specialist-testing-output.txt\nSTATUS=NOT_SUBSTANTIVE\n",
    );
    larch()
        .args([
            "review",
            "check-reviewer-failure-threshold",
            "--collector-results-file",
        ])
        .arg(&collector)
        .args([
            "--panel",
            "hard",
            "--intended-slots",
            "3",
            "--launched-slots",
            "3",
        ])
        .assert()
        .success()
        .stdout(
            "INTENDED_SLOTS=3\nSUCCEEDED_SLOTS=1\nFAILED_SLOTS=2\nCOUNTED_SLOTS=3\nNOT_SUBSTANTIVE_SLOTS=1\nDROPPED_SLOTS=0\nDROPPED_STATIC_SLOTS=0\nDYNAMIC_FAILED_SLOTS=0\nDYNAMIC_DROPPED_SLOTS=0\nTHRESHOLD_OK=false\nTHRESHOLD_REASON=2 of 3 panel slots failed (threshold: >50% = >1)\n",
        );
    let fully_failed = larch_core::review::reviewer_failure_threshold(
        &larch_core::review::ReviewerFailureThresholdInput {
            collector_results: "MALFORMED=record\n\nREVIEWER_FILE=codex-specialist-correctness-output.txt\nSTATUS=ERROR\n\nREVIEWER_FILE=cursor-specialist-edge-cases-output.txt\nSTATUS=ERROR\n\nREVIEWER_FILE=codex-specialist-testing-output.txt\nSTATUS=ERROR\n".to_owned(),
            reviewer_outputs: Vec::new(),
            dropped_slots: None,
            panel_manifest: Vec::new(),
            intended_slots: 3,
            launched_slots: None,
        },
    );
    assert_eq!(
        (
            fully_failed.succeeded_slots,
            fully_failed.failed_slots,
            fully_failed.threshold_ok
        ),
        (0, 3, false)
    );
}

#[test]
fn gather_context_preserves_legacy_help_and_argument_failures() {
    larch()
        .args(["review", "gather-context", "--help"])
        .assert()
        .success()
        .stdout("")
        .stderr(format!("{GATHER_CONTEXT_USAGE}\n"));
    larch()
        .args(["review", "gather-context", "--unknown"])
        .assert()
        .code(2)
        .stderr(format!("unknown option: --unknown{GATHER_CONTEXT_USAGE}\n"));
    larch()
        .args(["review", "gather-context", "--mode"])
        .assert()
        .code(2)
        .stderr(format!("--mode requires a value{GATHER_CONTEXT_USAGE}\n"));
    larch()
        .args([
            "review",
            "gather-context",
            "--mode",
            "unsupported",
            "--output-dir",
            ".",
        ])
        .assert()
        .code(2)
        .stderr(predicate::eq(
            "review gather-context: --mode must be diff or description\n",
        ));
}

#[cfg(unix)]
#[test]
fn aggregate_findings_preserves_the_merged_finding_wire() {
    let fixture = TempDir::new().expect("fixture");
    let review = fixture.path().join("review");
    fs::create_dir(&review).expect("review directory");
    let round = review.join("round-3");
    fs::create_dir(&round).expect("round directory");
    let findings = review.join("findings.md");
    let scope_anchor = review.join("scope-anchor.md");
    write(
        &scope_anchor,
        "Scope evidence preserved through the Rust-owned in-process validation seam.\n",
    );
    write(
        &findings,
        "### FINDING_7: Parse frames before decoding\n- **Reviewer(s)**: codex-specialist-parser\n- **Severity**: major\n- **Concern**: The decoder accepts a malformed frame.\n- **Suggested revision**: Validate frames before decoding.\n\n### FINDING_8: Decoder error path\n- **Reviewer(s)**: cursor-specialist-errors\n- **Severity**: major\n- **Concern**: The malformed frame path is not rejected.\n- **Suggested revision**: Reject malformed frames before decoding.\n\n### FINDING_9: Regression coverage\n- **Reviewer(s)**: claude-specialist-tests\n- **Severity**: minor\n- **Concern**: Malformed frames have no regression coverage.\n- **Suggested revision**: Add malformed frame regression coverage.\n",
    );
    let merged = review.join("aggregator-output.txt");
    let merged_text = "### FINDING_1: Validate malformed frames before decoding\n- **Reviewer(s)**: codex-specialist-parser, cursor-specialist-errors, claude-specialist-tests\n- **Concern**: A malformed frame reaches the decoder instead of being rejected.\n- **Suggested revisions**:\n  - From codex-specialist-parser: Validate frames before decoding.\n  - From cursor-specialist-errors: Reject malformed frames before decoding.\n  - From claude-specialist-tests: Add malformed frame regression coverage.\n".replace('\n', "\r\n");
    write(&merged, &merged_text);
    let paths = review.join("aggregator-output-files.txt");
    write(&paths, &format!("{}\n", merged.display()));
    let panel_context = fixture.path().join("panel-context.txt");
    let slot_record = fixture.path().join("slot-record.ndjson");
    let dispatch = fixture.path().join("dispatch.sh");
    executable_script(
        &dispatch,
        &format!(
            "#!/bin/sh\nslots=''\nwhile [ \"$#\" -gt 0 ]; do\n  case \"$1\" in\n    --slots-file) slots=\"$2\"; shift 2 ;;\n    *) shift ;;\n  esac\ndone\ncat \"$slots\" > '{}'\nprintf '%s\\n%s\\n%s\\n%s\\n' \"$LARCH_PANEL_SOURCE_AGENT_FILE\" \"$LARCH_PANEL_PHASE\" \"$LARCH_PANEL_PAYLOAD_BYTES\" \"$LARCH_PANEL_ARTIFACT_DIR\" > '{}'\nprintf 'DISPATCH_OK=true\\nALL_OUTPUT_FILES={}\\nALL_OUTPUT_FILES_PATH={}\\n'\n",
            slot_record.display(),
            panel_context.display(),
            merged.display(),
            paths.display(),
        ),
    );

    larch()
        .env("CLAUDE_PLUGIN_ROOT", plugin_root())
        .env("LARCH_BINARY", env!("CARGO_BIN_EXE_larch"))
        .env("AGGREGATE_DISPATCH_SH", dispatch)
        .args(["review", "aggregate-findings", "--findings-file"])
        .arg(&findings)
        .args(["--review-tmpdir"])
        .arg(&review)
        .args([
            "--round-num",
            "3",
            "--codex-present",
            "true",
            "--cursor-present",
            "false",
            "--mode",
            "diff",
            "--input-mode",
            "plan",
            "--scope-anchor-file",
        ])
        .arg(&scope_anchor)
        .assert()
        .success()
        .stdout("AGGREGATED=true\nINPUT_COUNT=3\nMERGED_COUNT=1\nREASON=ok\n");
    assert_eq!(
        fs::read_to_string(&findings).expect("merged findings"),
        format!("{}\n", merged_text.trim_end())
    );
    assert!(
        fs::read_to_string(review.join("aggregator-prompt.md"))
            .expect("aggregation prompt")
            .contains(
                "Scope evidence preserved through the Rust-owned in-process validation seam."
            )
    );
    assert_eq!(
        fs::read_to_string(review.join("aggregator-dispatch.env")).expect("dispatch envelope"),
        format!(
            "DISPATCH_OK=true\nALL_OUTPUT_FILES={}\nALL_OUTPUT_FILES_PATH={}\n",
            merged.display(),
            paths.display(),
        )
    );
    let panel_context = fs::read_to_string(panel_context).expect("panel context");
    let panel_context: Vec<&str> = panel_context.lines().collect();
    assert_eq!(panel_context[0], "agents/orchestrator-aggregator.md");
    assert_eq!(panel_context[1], "aggregate-findings");
    assert!(panel_context[2].parse::<usize>().expect("payload size") > 0);
    assert_eq!(
        panel_context[3],
        fs::canonicalize(&round)
            .expect("canonical round path")
            .to_str()
            .expect("UTF-8 round path")
    );
    let canonical_review = fs::canonicalize(&review).expect("canonical review path");
    assert_eq!(
        fs::read_to_string(slot_record).expect("slot record"),
        format!(
            "{{\"slot\":\"aggregator\",\"tool\":\"codex\",\"output\":\"{}\",\"prompt_file\":\"{}\",\"model_role\":\"review\",\"payload_bytes\":{}}}\n",
            canonical_review.join("aggregator-output.txt").display(),
            canonical_review.join("aggregator-prompt.md").display(),
            panel_context[2],
        )
    );
}

#[test]
fn prune_nit_findings_keeps_order_and_separates_security_audit() {
    let fixture = TempDir::new().expect("fixture");
    let findings = fixture.path().join("findings.md");
    write(
        &findings,
        "### FINDING_8: Keep\n- **Severity**: minor\n\n### FINDING_9: Drop\n- **Severity**: nit\n\n### OOS_4: Security drop\n- **focus-area**: security-review\n- **Severity**: nit\n",
    );
    let audit = fixture.path().join("audit.md");
    let security = fixture.path().join("security.md");

    larch()
        .args(["review", "prune-nit-findings", "--findings-file"])
        .arg(&findings)
        .args(["--audit-file"])
        .arg(&audit)
        .args(["--security-audit-file"])
        .arg(&security)
        .assert()
        .success()
        .stdout("PRUNED_COUNT=2\nINSCOPE_REMAINING=1\nSTATUS=ok\n");
    assert_eq!(
        fs::read_to_string(&findings).expect("remaining findings"),
        "### FINDING_1: Keep\n- **Severity**: minor\n\n"
    );
    assert!(
        fs::read_to_string(&audit)
            .expect("audit")
            .contains("### FINDING_9: Drop")
    );
    assert!(
        fs::read_to_string(&security)
            .expect("security audit")
            .contains("### OOS_4: Security drop")
    );
}

#[test]
fn reviewer_prune_records_weighted_history_then_filters_in_manifest_order() {
    let fixture = TempDir::new().expect("fixture");
    let ledger = fixture.path().join("ledger.tsv");
    let manifest = fixture.path().join("manifest.ndjson");
    write(
        &manifest,
        "{\"tool\":\"codex\",\"slot\":\"keep\",\"output\":\"keep-output.txt\"}\n{\"tool\":\"cursor\",\"slot\":\"drop\",\"output\":\"drop-output.txt\"}\n",
    );
    let classification = fixture.path().join("classification.tsv");
    write(
        &classification,
        "finding_id\treviewer_slots\tvoting_result\tv1_vote\tv1_severity\tv2_vote\tv2_severity\tv3_vote\tv3_severity\tscope\nFINDING_1\tkeep-output.txt\taccepted\tYES\tmajor\tYES\tmajor\tNO\tminor\tin_scope\n",
    );
    larch()
        .args(["review", "reviewer-prune", "record", "--ledger"])
        .arg(&ledger)
        .args(["--round", "1", "--manifest"])
        .arg(&manifest)
        .args(["--classification"])
        .arg(&classification)
        .assert()
        .success()
        .stdout("");
    let out = fixture.path().join("filtered.ndjson");
    larch()
        .args(["review", "reviewer-prune", "filter", "--ledger"])
        .arg(&ledger)
        .args(["--round", "2", "--manifest"])
        .arg(&manifest)
        .args(["--out"])
        .arg(&out)
        .assert()
        .success()
        .stdout("PRUNE_ACTIVE=true\nELIGIBLE_COUNT=1\nPRUNED_COUNT=1\nPRUNED_COMBOS=cursor:drop\nPANEL_PRUNED_EMPTY=false\n");
    assert_eq!(
        fs::read_to_string(out).expect("filtered manifest"),
        "{\"tool\":\"codex\",\"slot\":\"keep\",\"output\":\"keep-output.txt\"}\n"
    );
}

#[test]
fn reviewer_prune_keeps_the_legacy_manual_option_grammar() {
    let usage = "Usage: review reviewer-prune record --ledger FILE --round N --manifest FILE --classification FILE [--label-map FILE] [--reviewer-status FILE] | review reviewer-prune filter --ledger FILE --round N --manifest FILE --out FILE";
    larch()
        .args(["review", "reviewer-prune", "record", "--ledger=ledger.tsv"])
        .assert()
        .code(2)
        .stdout("")
        .stderr(format!(
            "unknown option: --ledger=ledger.tsv\n{usage}\n{usage}\n"
        ));
}

#[test]
fn reviewer_failure_threshold_rejects_a_corrupt_manifest() {
    let fixture = TempDir::new().expect("fixture");
    let collector = fixture.path().join("collector.env");
    let manifest = fixture.path().join("manifest.ndjson");
    write(&collector, "REVIEWER_FILE=review.txt\nSTATUS=OK\n");
    write(&manifest, "{not-json}\n");
    larch()
        .args(["review", "check-reviewer-failure-threshold", "--collector-results-file"])
        .arg(collector)
        .args(["--panel", "hard", "--panel-manifest"])
        .arg(manifest)
        .assert()
        .code(1)
        .stdout("")
        .stderr("review check-reviewer-failure-threshold: --panel-manifest is unreadable or contains invalid JSON\n");
}
