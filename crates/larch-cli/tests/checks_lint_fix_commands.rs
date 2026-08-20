//! Black-box parity coverage for the Rust `checks fixer-evidence` and
//! `checks lint-fix` commands (#8625). Each case drives the real binary and
//! pins the `KEY=value` stdout grammar, the argparse help/usage text, and the
//! exit codes the retired Python entrypoints produced. Vendor lanes are never
//! launched: every case terminates before a coder would be dispatched.

use std::fs;

use assert_cmd::Command as AssertCommand;
use tempfile::TempDir;

const LINT_FIX_HELP: &str = "usage: cli.py checks lint-fix [-h] --tmpdir TMPDIR --site SITE --checks-log\n                              CHECKS_LOG [--repo-root REPO_ROOT]\n                              [--run-parent RUN_PARENT]\n\noptions:\n  -h, --help            show this help message and exit\n  --tmpdir TMPDIR\n  --site SITE\n  --checks-log CHECKS_LOG\n  --repo-root REPO_ROOT\n  --run-parent RUN_PARENT\n";

const FIXER_EVIDENCE_HELP: &str = "usage: cli.py checks fixer-evidence [-h] --tmpdir TMPDIR --site SITE --round\n                                    ROUND --checks-log CHECKS_LOG\n\noptions:\n  -h, --help            show this help message and exit\n  --tmpdir TMPDIR\n  --site SITE\n  --round ROUND\n  --checks-log CHECKS_LOG\n";

fn larch() -> AssertCommand {
    AssertCommand::cargo_bin("larch").expect("larch binary")
}

/// Build a validated session tmpdir under a fake `XDG_CACHE_HOME` and return
/// both the cache root (for `XDG_CACHE_HOME`) and the session directory.
fn session_tmpdir() -> (TempDir, std::path::PathBuf) {
    let cache = TempDir::new().expect("cache tempdir");
    let sessions = cache.path().join("larch").join("sessions");
    fs::create_dir_all(&sessions).expect("sessions dir");
    let tmp = sessions.join("claude-implement-8625");
    fs::create_dir(&tmp).expect("session dir");
    (cache, tmp)
}

// ---- checks lint-fix ----

#[test]
fn lint_fix_help_matches_argparse() {
    larch()
        .args(["checks", "lint-fix", "--help"])
        .assert()
        .success()
        .stdout(LINT_FIX_HELP);
}

#[test]
fn lint_fix_missing_required_is_a_usage_error() {
    larch()
        .args(["checks", "lint-fix"])
        .assert()
        .code(2)
        .stderr(predicates::str::contains(
            "cli.py checks lint-fix: error: the following arguments are required: --tmpdir, --site, --checks-log",
        ));
}

#[test]
fn lint_fix_rejects_an_unvalidated_tmpdir() {
    larch()
        .args([
            "checks",
            "lint-fix",
            "--tmpdir",
            "/larch-clean-install-missing",
            "--site",
            "step5",
            "--checks-log",
            "/larch-clean-install-missing/checks.log",
        ])
        .assert()
        .code(2)
        .stdout("LINT_FIX_STATUS=failed\nFAILURE_REASON=tmpdir-validation\n");
}

#[test]
fn lint_fix_empty_checks_log_is_no_changes() {
    let (cache, tmp) = session_tmpdir();
    let checks_log = tmp.join("checks.log");
    fs::write(&checks_log, "").expect("empty checks log");
    larch()
        .env("XDG_CACHE_HOME", cache.path())
        .env("CLAUDE_BINARY_FOUND", "false")
        .env("CODEX_BINARY_FOUND", "false")
        .env("CURSOR_BINARY_FOUND", "false")
        .args([
            "checks",
            "lint-fix",
            "--tmpdir",
            &tmp.to_string_lossy(),
            "--site",
            "step5",
            "--checks-log",
            &checks_log.to_string_lossy(),
        ])
        .assert()
        .success()
        .stdout("LINT_FIX_STATUS=no-changes\n");
}

#[test]
fn lint_fix_no_selectable_tier_stalls_pre_ship() {
    let (cache, tmp) = session_tmpdir();
    let checks_log = tmp.join("checks.log");
    fs::write(&checks_log, "scripts/foo.sh:1:1 MD038 failure\n").expect("checks log");
    let assert = larch()
        .env("XDG_CACHE_HOME", cache.path())
        .env("CLAUDE_BINARY_FOUND", "false")
        .env("CODEX_BINARY_FOUND", "false")
        .env("CURSOR_BINARY_FOUND", "false")
        .args([
            "checks",
            "lint-fix",
            "--tmpdir",
            &tmp.to_string_lossy(),
            "--site",
            "step5",
            "--checks-log",
            &checks_log.to_string_lossy(),
        ])
        .assert()
        .code(1);
    let stdout = String::from_utf8(assert.get_output().stdout.clone()).expect("utf8");
    assert!(
        stdout.contains("LINT_FIX_STATUS=failed"),
        "unexpected stdout: {stdout}"
    );
    assert!(
        stdout.contains("FAILURE_REASON=lint-fix-no-selectable-tier"),
        "unexpected stdout: {stdout}"
    );
    assert!(
        stdout.contains("LINT_FIX_TIER_LEDGER_PATH="),
        "expected tier-ledger path: {stdout}"
    );
    // Pre-ship exhaustion does not emit the ledger block itself.
    assert!(
        !stdout.contains("LINT_FIX_LEDGER_READY=true"),
        "pre-ship stall should not be ledger-ready: {stdout}"
    );
}

#[test]
fn lint_fix_structural_ruff_requires_the_main_agent() {
    let (cache, tmp) = session_tmpdir();
    let checks_log = tmp.join("checks.log");
    fs::write(
        &checks_log,
        "python/larch/cli.py:12:3: PLR0911 too many returns\n",
    )
    .expect("checks log");
    let assert = larch()
        .env("XDG_CACHE_HOME", cache.path())
        .args([
            "checks",
            "lint-fix",
            "--tmpdir",
            &tmp.to_string_lossy(),
            "--site",
            "step5",
            "--checks-log",
            &checks_log.to_string_lossy(),
        ])
        .assert()
        .success();
    let stdout = String::from_utf8(assert.get_output().stdout.clone()).expect("utf8");
    assert!(
        stdout.contains("LINT_FIX_STATUS=main-agent-required"),
        "unexpected stdout: {stdout}"
    );
    assert!(
        stdout.contains("FAILURE_REASON=structural-ruff-failure"),
        "unexpected stdout: {stdout}"
    );
    assert!(
        stdout.contains("LINT_FIX_LEDGER_READY=true"),
        "structural fast-fail is ledger-ready: {stdout}"
    );
    assert!(
        stdout.contains("LINT_FIX_LEDGER_STEP=5"),
        "unexpected ledger step: {stdout}"
    );
}

// ---- checks fixer-evidence ----

#[test]
fn fixer_evidence_help_matches_argparse() {
    larch()
        .args(["checks", "fixer-evidence", "--help"])
        .assert()
        .success()
        .stdout(FIXER_EVIDENCE_HELP);
}

#[test]
fn fixer_evidence_missing_required_is_a_usage_error() {
    larch()
        .args(["checks", "fixer-evidence"])
        .assert()
        .code(2)
        .stderr(predicates::str::contains(
            "cli.py checks fixer-evidence: error: the following arguments are required: --tmpdir, --site, --round, --checks-log",
        ));
}

#[test]
fn fixer_evidence_rejects_an_out_of_range_round() {
    let (cache, tmp) = session_tmpdir();
    let checks_log = tmp.join("checks.log");
    fs::write(&checks_log, "boom\n").expect("checks log");
    larch()
        .env("XDG_CACHE_HOME", cache.path())
        .args([
            "checks",
            "fixer-evidence",
            "--tmpdir",
            &tmp.to_string_lossy(),
            "--site",
            "step5",
            "--round",
            "99",
            "--checks-log",
            &checks_log.to_string_lossy(),
        ])
        .assert()
        .code(2)
        .stdout("CHECKS_FIXER_EVIDENCE_STATUS=invalid-round\n");
}

#[test]
fn fixer_evidence_writes_a_redacted_digest() {
    let (cache, tmp) = session_tmpdir();
    let checks_log = tmp.join("checks.log");
    fs::write(
        &checks_log,
        "ERROR: something failed\nFAILED tests/test_x.py\n",
    )
    .expect("checks log");
    // The validated tmpdir is canonicalized, so the emitted path resolves symlinks.
    let expected = fs::canonicalize(&tmp)
        .expect("canonical tmp")
        .join("checks-errors-step5-2.md");
    let assert = larch()
        .env("XDG_CACHE_HOME", cache.path())
        .args([
            "checks",
            "fixer-evidence",
            "--tmpdir",
            &tmp.to_string_lossy(),
            "--site",
            "step5",
            "--round",
            "2",
            "--checks-log",
            &checks_log.to_string_lossy(),
        ])
        .assert()
        .success();
    let stdout = String::from_utf8(assert.get_output().stdout.clone()).expect("utf8");
    assert!(
        stdout.contains("CHECKS_FIXER_EVIDENCE_STATUS=ok"),
        "unexpected stdout: {stdout}"
    );
    assert!(
        stdout.contains(&format!(
            "CHECKS_FIXER_EVIDENCE_FILE={}",
            expected.display()
        )),
        "unexpected stdout: {stdout}"
    );
    assert!(expected.is_file(), "digest file should exist");
}
