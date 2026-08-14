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
