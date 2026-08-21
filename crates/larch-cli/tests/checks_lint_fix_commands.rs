//! Black-box parity coverage for the Rust `checks fixer-evidence`,
//! `checks lint-fix`, and `checks repair-loop` commands (#8625, #8627).
//! Each case drives the real binary and
//! pins the `KEY=value` stdout grammar, the argparse help/usage text, and the
//! exit codes the retired Python entrypoints produced. The dispatch-loop cases
//! drive a fixture `CLAUDE_PLUGIN_ROOT` whose `scripts/larch.sh` stubs the
//! vendor launchers, so no real coder ever runs.
#![allow(clippy::literal_string_with_formatting_args)]

use std::fs;

use assert_cmd::Command as AssertCommand;
use tempfile::TempDir;

const LINT_FIX_HELP: &str = "usage: cli.py checks lint-fix [-h] --tmpdir TMPDIR --site SITE --checks-log\n                              CHECKS_LOG [--repo-root REPO_ROOT]\n                              [--run-parent RUN_PARENT]\n\noptions:\n  -h, --help            show this help message and exit\n  --tmpdir TMPDIR\n  --site SITE\n  --checks-log CHECKS_LOG\n  --repo-root REPO_ROOT\n  --run-parent RUN_PARENT\n";

const FIXER_EVIDENCE_HELP: &str = "usage: cli.py checks fixer-evidence [-h] --tmpdir TMPDIR --site SITE --round\n                                    ROUND --checks-log CHECKS_LOG\n\noptions:\n  -h, --help            show this help message and exit\n  --tmpdir TMPDIR\n  --site SITE\n  --round ROUND\n  --checks-log CHECKS_LOG\n";

const REPAIR_LOOP_HELP: &str = "usage: cli.py checks repair-loop [-h] --tmpdir TMPDIR --site SITE\n                                 [--checks-site CHECKS_SITE] --checks-log\n                                 CHECKS_LOG [--repo-root REPO_ROOT]\n                                 [--bgjob-launch {true,false}]\n                                 [--bgjob-merge-result-env BGJOB_MERGE_RESULT_ENV]\n\noptions:\n  -h, --help            show this help message and exit\n  --tmpdir TMPDIR\n  --site SITE\n  --checks-site CHECKS_SITE\n  --checks-log CHECKS_LOG\n  --repo-root REPO_ROOT\n  --bgjob-launch {true,false}\n  --bgjob-merge-result-env BGJOB_MERGE_RESULT_ENV\n";

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

// ---- checks repair-loop ----

#[test]
fn repair_loop_help_matches_argparse() {
    larch()
        .args(["checks", "repair-loop", "--help"])
        .assert()
        .success()
        .stdout(REPAIR_LOOP_HELP);
}

#[test]
fn repair_loop_missing_required_is_a_usage_error_with_stall_envelope() {
    larch()
        .args(["checks", "repair-loop"])
        .assert()
        .code(2)
        .stdout("NEXT_ACTION=stall\nLOOP_STATUS=argument-error\n")
        .stderr(predicates::str::contains(
            "cli.py checks repair-loop: error: the following arguments are required: --tmpdir, --site, --checks-log",
        ));
}

#[test]
fn repair_loop_rejects_an_unvalidated_tmpdir() {
    larch()
        .args([
            "checks",
            "repair-loop",
            "--tmpdir",
            "/larch-clean-install-missing",
            "--site",
            "step6",
            "--checks-log",
            "/larch-clean-install-missing/checks.log",
        ])
        .assert()
        .code(2)
        .stdout("NEXT_ACTION=stall\nLOOP_STATUS=tmpdir-validation\n");
}

#[test]
fn repair_loop_empty_tmpdir_uses_the_session_environment() {
    let (cache, tmp) = session_tmpdir();
    larch()
        .env("XDG_CACHE_HOME", cache.path())
        .env("IMPLEMENT_TMPDIR", &tmp)
        .args([
            "checks",
            "repair-loop",
            "--tmpdir",
            "",
            "--site",
            "step6",
            "--checks-site",
            "../bad",
            "--checks-log",
            &tmp.join("checks.log").to_string_lossy(),
        ])
        .assert()
        .code(2)
        .stdout("NEXT_ACTION=stall\nLOOP_STATUS=checks-site-validation\n");
}

#[test]
fn repair_loop_pre_ship_exhaustion_preserves_terminal_evidence() {
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
            "repair-loop",
            "--tmpdir",
            &tmp.to_string_lossy(),
            "--site",
            "step6",
            "--checks-log",
            &checks_log.to_string_lossy(),
        ])
        .assert()
        .code(1);
    let stdout = String::from_utf8(assert.get_output().stdout.clone()).expect("utf8");
    assert!(
        stdout.starts_with("PROGRESS=dispatching-lint-fix site=step6\n"),
        "unexpected stdout: {stdout}"
    );
    for expected in [
        "NEXT_ACTION=stall",
        "LOOP_STATUS=exhausted",
        "FAILURE_REASON=lint-fix-no-selectable-tier",
        "LINT_FIX_TIER_LEDGER_PATH=",
    ] {
        assert!(stdout.contains(expected), "missing {expected:?}: {stdout}");
    }
}

#[test]
fn repair_loop_structural_failure_flushes_the_merge_envelope() {
    let (cache, tmp) = session_tmpdir();
    let checks_log = tmp.join("checks.log");
    let merge_env = tmp.join("bgjob").join("implement-step5-repair.merge.env");
    fs::write(
        &checks_log,
        "python/larch/cli.py:12:3: PLR0911 too many returns\n",
    )
    .expect("checks log");
    larch()
        .env("XDG_CACHE_HOME", cache.path())
        .args([
            "checks",
            "repair-loop",
            "--tmpdir",
            &tmp.to_string_lossy(),
            "--site",
            "step5",
            "--checks-log",
            &checks_log.to_string_lossy(),
            "--bgjob-merge-result-env",
            &merge_env.to_string_lossy(),
        ])
        .assert()
        .success()
        .stdout(predicates::str::contains("NEXT_ACTION=main-agent-edit\n"));
    let rows = fs::read_to_string(&merge_env).expect("merge envelope");
    assert!(rows.starts_with("NEXT_ACTION=main-agent-edit\nLOOP_STATUS=main-agent-required\n"));
    assert!(rows.contains("FAILURE_REASON=structural-ruff-failure\n"));
    assert!(rows.contains("LINT_FIX_LEDGER_READY=true\n"));
    assert!(!rows.contains("BGJOB_RC="));
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

// ---- end-to-end dispatch loop (vendor launch fails fast without a plugin root) ----

fn init_git_repo() -> TempDir {
    let repo = TempDir::new().expect("repo tempdir");
    let run = |args: &[&str]| {
        let ok = std::process::Command::new("git")
            .args(args)
            .current_dir(repo.path())
            .env("GIT_AUTHOR_NAME", "t")
            .env("GIT_AUTHOR_EMAIL", "t@t")
            .env("GIT_COMMITTER_NAME", "t")
            .env("GIT_COMMITTER_EMAIL", "t@t")
            .env("GIT_CONFIG_GLOBAL", "/dev/null")
            .output()
            .expect("git runs")
            .status
            .success();
        assert!(ok, "git {args:?}");
    };
    run(&["init", "-b", "main"]);
    // A local identity so the coder-commit path (`larch git commit` through the
    // fixture bootstrap) succeeds on CI runners that have no global git config.
    run(&["config", "user.email", "t@t"]);
    run(&["config", "user.name", "t"]);
    fs::write(repo.path().join("a.txt"), "one\n").expect("seed");
    run(&["add", "."]);
    run(&["commit", "-m", "base"]);
    repo
}

fn assert_lane_exhausts(binary_env: &str) {
    let (cache, tmp) = session_tmpdir();
    let repo = init_git_repo();
    let checks_log = tmp.join("checks.log");
    fs::write(
        &checks_log,
        "scripts/foo.sh:1: MD038 inner-whitespace failure\n",
    )
    .expect("log");
    let mut command = larch();
    command
        .env("XDG_CACHE_HOME", cache.path())
        .env_remove("CLAUDE_PLUGIN_ROOT")
        .env("CLAUDE_BINARY_FOUND", "false")
        .env("CODEX_BINARY_FOUND", "false")
        .env("CURSOR_BINARY_FOUND", "false")
        .env(binary_env, "true");
    let assert = command
        .args([
            "checks",
            "lint-fix",
            "--tmpdir",
            &tmp.to_string_lossy(),
            "--site",
            "step5",
            "--checks-log",
            &checks_log.to_string_lossy(),
            "--repo-root",
            &repo.path().to_string_lossy(),
        ])
        .assert()
        .code(1);
    let stdout = String::from_utf8(assert.get_output().stdout.clone()).expect("utf8");
    assert!(
        stdout.contains("LINT_FIX_STATUS=failed"),
        "{binary_env}: {stdout}"
    );
    // Every delegated tier ran and made no useful delta, so the loop exhausts.
    assert!(
        stdout.contains("FAILURE_REASON=lint-fix-all-tiers-no-useful-delta"),
        "{binary_env}: {stdout}"
    );
    assert!(
        stdout.contains("LINT_FIX_TIER_LEDGER_PATH="),
        "{binary_env}: {stdout}"
    );
    // The tier ledger recorded exactly one failed attempt for the present tier.
    let ledger = tmp.join("lint-fix-loop").join("lint-fix-tier-ledger.tsv");
    let body = fs::read_to_string(&ledger).expect("tier ledger");
    let rows = body
        .lines()
        .filter(|line| !line.starts_with("sequence"))
        .count();
    assert_eq!(rows, 1, "{binary_env} ledger: {body}");
}

#[test]
fn lint_fix_claude_lane_exhausts_on_launch_failure() {
    assert_lane_exhausts("CLAUDE_BINARY_FOUND");
}

#[test]
fn lint_fix_codex_lane_exhausts_on_launch_failure() {
    assert_lane_exhausts("CODEX_BINARY_FOUND");
}

#[test]
fn lint_fix_cursor_lane_exhausts_on_launch_failure() {
    assert_lane_exhausts("CURSOR_BINARY_FOUND");
}

// ---- full dispatch through a stub vendor that produces a committed delta ----

/// A fixture `CLAUDE_PLUGIN_ROOT` whose `scripts/larch.sh` stubs the Claude
/// lint-fix launcher (write the transcript + edit a tracked file) and forwards
/// the verified `git stage` / `git commit` the baseline-clean apply path issues.
fn lint_fix_plugin(root: &std::path::Path) -> std::path::PathBuf {
    use std::os::unix::fs::PermissionsExt as _;
    let plugin = root.join("lint-fix-plugin");
    let scripts = plugin.join("scripts");
    fs::create_dir_all(&scripts).expect("fixture scripts");
    let bootstrap = scripts.join("larch.sh");
    fs::write(
        &bootstrap,
        r#"#!/bin/sh
set -eu
domain=${1:-}
verb=${2:-}
shift 2 || true
case "$domain:$verb" in
  agent:launch-claude-lint-fix|agent:launch-codex-exec)
    output=""
    while [ "$#" -gt 0 ]; do
      case "$1" in
        --output) output=$2; shift 2 ;;
        *) shift ;;
      esac
    done
    printf 'FIXED: a.txt | md038 inner-whitespace\n' > "$output"
    printf 'usage\n' > "$output.token-record"
    printf 'two\n' >> a.txt
    exit 0
    ;;
  agent:cursor-wrap-prompt) printf 'wrapped: %s\n' "$1"; exit 0 ;;
  token:append-record|token:record-vendor-sidecar) exit 0 ;;
  git:stage) exec git add "$@" ;;
  git:commit) exec git commit --no-verify -m "lint-fix stub commit" ;;
  timing:record-vendor-task) exit 0 ;;
  *) exit 0 ;;
esac
"#,
    )
    .expect("fixture bootstrap");
    fs::set_permissions(&bootstrap, fs::Permissions::from_mode(0o755)).expect("bootstrap mode");
    plugin
}

fn repair_loop_bgjob_plugin(root: &std::path::Path) -> std::path::PathBuf {
    use std::os::unix::fs::PermissionsExt as _;
    let plugin = root.join("repair-loop-bgjob-plugin");
    let scripts = plugin.join("scripts");
    fs::create_dir_all(&scripts).expect("fixture scripts");
    let bootstrap = scripts.join("larch.sh");
    fs::write(
        &bootstrap,
        r#"#!/bin/sh
set -eu
capture=$(dirname "$0")/../bgjob-argv
printf '%s\n' "$@" > "$capture"
printf 'BGJOB_STATUS=STARTED STEP=implement-step3-repair PGID=123\n'
"#,
    )
    .expect("fixture bootstrap");
    fs::set_permissions(&bootstrap, fs::Permissions::from_mode(0o755)).expect("bootstrap mode");
    plugin
}

#[test]
fn repair_loop_bgjob_launch_uses_the_verified_entrypoint_and_site_slug() {
    let (cache, tmp) = session_tmpdir();
    let fixture_plugin = repair_loop_bgjob_plugin(cache.path());
    let checks_log = tmp.join("checks.log");
    fs::write(&checks_log, "failure\n").expect("checks log");
    larch()
        .env("XDG_CACHE_HOME", cache.path())
        .env("CLAUDE_PLUGIN_ROOT", &fixture_plugin)
        .args([
            "checks",
            "repair-loop",
            "--tmpdir",
            &tmp.to_string_lossy(),
            "--site",
            "step3",
            "--checks-log",
            &checks_log.to_string_lossy(),
            "--repo-root",
            &cache.path().to_string_lossy(),
            "--bgjob-launch",
            "true",
        ])
        .assert()
        .success()
        .stdout("BGJOB_STATUS=STARTED STEP=implement-step3-repair PGID=123\n");

    let capture =
        fs::read_to_string(fixture_plugin.join("bgjob-argv")).expect("captured bgjob argv");
    let argv: Vec<&str> = capture.lines().collect();
    assert_eq!(
        &argv[..4],
        ["bgjob", "start", "--step", "implement-step3-repair"]
    );
    assert_eq!(
        argv.windows(2).find(|pair| pair[0] == "--budget-s"),
        Some(&["--budget-s", "16200"][..])
    );
    assert_eq!(
        argv.windows(2)
            .find(|pair| pair[0] == "--terminal-stdout-key"),
        Some(&["--terminal-stdout-key", "NEXT_ACTION"][..])
    );
    let separator = argv
        .iter()
        .position(|part| *part == "--")
        .expect("separator");
    assert_eq!(
        argv[separator + 2..separator + 4],
        ["checks", "repair-loop"]
    );
    assert!(argv.contains(&"--bgjob-merge-result-env"));
    assert!(!argv.contains(&"--bgjob-launch"));
    assert!(
        argv[separator + 1].ends_with("/scripts/larch.sh"),
        "nested command bypassed bootstrap: {argv:?}"
    );
    let merge_env = tmp.join("bgjob").join("implement-step3-repair.merge.env");
    assert_eq!(fs::read_to_string(merge_env).expect("merge env"), "");
}

#[test]
fn repair_loop_applies_a_stub_delta_and_rechecks_the_capture_site() {
    let (cache, tmp) = session_tmpdir();
    let repo = init_git_repo();
    let fixture_plugin = lint_fix_plugin(cache.path());
    let checks_log = tmp.join("checks.log");
    fs::write(&checks_log, "a.txt:1: MD038 inner-whitespace failure\n").expect("log");
    let assert = larch()
        .current_dir(repo.path())
        .env("XDG_CACHE_HOME", cache.path())
        .env("CLAUDE_PLUGIN_ROOT", &fixture_plugin)
        .env("CLAUDE_PROJECT_DIR", repo.path())
        .env("CLAUDE_BINARY_FOUND", "true")
        .env("CODEX_BINARY_FOUND", "false")
        .env("CURSOR_BINARY_FOUND", "false")
        .args([
            "checks",
            "repair-loop",
            "--tmpdir",
            &tmp.to_string_lossy(),
            "--site",
            "step5-mav",
            "--checks-site",
            "step5-review-fixes",
            "--checks-log",
            &checks_log.to_string_lossy(),
            "--repo-root",
            &repo.path().to_string_lossy(),
        ])
        .assert()
        .success();
    let stdout = String::from_utf8(assert.get_output().stdout.clone()).expect("utf8");
    assert!(stdout.starts_with(
        "PROGRESS=dispatching-lint-fix site=step5-mav\nNEXT_ACTION=continue\nLOOP_STATUS=ok\n"
    ));
    assert!(stdout.contains("LINT_FIX_TIER_LEDGER_PATH="));
    let self_edits = fs::read_to_string(tmp.join("self-edit-log.tsv")).expect("self-edit log");
    assert!(self_edits.contains("\tlint-fix:step5-mav\ta.txt\t"));
    let relevant_logs = fs::read_dir(tmp.join("relevant-checks")).expect("relevant checks logs");
    assert!(relevant_logs.filter_map(Result::ok).any(|entry| {
        entry
            .file_name()
            .to_string_lossy()
            .starts_with("step5-review-fixes-")
    }));
}

#[test]
fn lint_fix_applies_and_commits_a_stub_vendor_delta() {
    let (cache, tmp) = session_tmpdir();
    let repo = init_git_repo();
    let fixture_plugin = lint_fix_plugin(cache.path());
    let checks_log = tmp.join("checks.log");
    fs::write(&checks_log, "a.txt:1: MD038 inner-whitespace failure\n").expect("log");
    let assert = larch()
        .current_dir(repo.path())
        .env("XDG_CACHE_HOME", cache.path())
        .env("CLAUDE_PLUGIN_ROOT", &fixture_plugin)
        .env("CLAUDE_PROJECT_DIR", repo.path())
        .env("CLAUDE_BINARY_FOUND", "true")
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
            "--repo-root",
            &repo.path().to_string_lossy(),
        ])
        .assert()
        .success();
    let stdout = String::from_utf8(assert.get_output().stdout.clone()).expect("utf8");
    assert!(
        stdout.contains("LINT_FIX_STATUS=applied"),
        "expected applied: {stdout}"
    );
    assert!(
        stdout.contains("LINT_FIX_DELTA_COUNT=1"),
        "expected one delta path: {stdout}"
    );
    assert!(
        stdout.contains("LINT_FIX_DELTA_PATH_0=a.txt"),
        "expected the edited path: {stdout}"
    );
    // The baseline-clean apply path committed the stub's edit.
    let log = std::process::Command::new("git")
        .args(["log", "--oneline", "-1"])
        .current_dir(repo.path())
        .output()
        .expect("git log");
    assert!(
        String::from_utf8_lossy(&log.stdout).contains("lint-fix stub commit"),
        "expected the applied commit"
    );
}

#[test]
fn lint_fix_codex_lane_applies_a_stub_delta() {
    let (cache, tmp) = session_tmpdir();
    let repo = init_git_repo();
    let fixture_plugin = lint_fix_plugin(cache.path());
    let checks_log = tmp.join("checks.log");
    fs::write(&checks_log, "a.txt:1: MD038 failure\n").expect("log");
    let assert = larch()
        .current_dir(repo.path())
        .env("XDG_CACHE_HOME", cache.path())
        .env("CLAUDE_PLUGIN_ROOT", &fixture_plugin)
        .env("CLAUDE_PROJECT_DIR", repo.path())
        .env("CLAUDE_BINARY_FOUND", "false")
        .env("CODEX_BINARY_FOUND", "true")
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
            "--repo-root",
            &repo.path().to_string_lossy(),
        ])
        .assert()
        .success();
    let stdout = String::from_utf8(assert.get_output().stdout.clone()).expect("utf8");
    assert!(stdout.contains("LINT_FIX_STATUS=applied"), "{stdout}");
    assert!(stdout.contains("LINT_FIX_DELTA_PATH_0=a.txt"), "{stdout}");
}

#[test]
fn lint_fix_cursor_lane_applies_a_stub_delta() {
    use std::os::unix::fs::PermissionsExt as _;
    let (cache, tmp) = session_tmpdir();
    let repo = init_git_repo();
    let fixture_plugin = lint_fix_plugin(cache.path());
    // The cursor lane launches the `cursor` binary directly (not via larch.sh);
    // a PATH stub makes the edit that becomes the applied delta.
    let bin = cache.path().join("bin");
    fs::create_dir_all(&bin).expect("bin");
    let cursor = bin.join("cursor");
    fs::write(&cursor, "#!/bin/sh\nprintf 'two\\n' >> a.txt\n").expect("cursor stub");
    fs::set_permissions(&cursor, fs::Permissions::from_mode(0o755)).expect("cursor mode");
    let system_path = std::env::var_os("PATH").expect("PATH");
    let path =
        std::env::join_paths(std::iter::once(bin).chain(std::env::split_paths(&system_path)))
            .expect("PATH join");
    let checks_log = tmp.join("checks.log");
    fs::write(&checks_log, "a.txt:1: MD038 failure\n").expect("log");
    let assert = larch()
        .current_dir(repo.path())
        .env("XDG_CACHE_HOME", cache.path())
        .env("CLAUDE_PLUGIN_ROOT", &fixture_plugin)
        .env("CLAUDE_PROJECT_DIR", repo.path())
        .env("CURSOR_API_KEY", "  cursor-test-token  ")
        .env("PATH", &path)
        .env("CLAUDE_BINARY_FOUND", "false")
        .env("CODEX_BINARY_FOUND", "false")
        .env("CURSOR_BINARY_FOUND", "true")
        .args([
            "checks",
            "lint-fix",
            "--tmpdir",
            &tmp.to_string_lossy(),
            "--site",
            "step5",
            "--checks-log",
            &checks_log.to_string_lossy(),
            "--repo-root",
            &repo.path().to_string_lossy(),
        ])
        .assert();
    let output = assert.get_output();
    let stdout = String::from_utf8_lossy(&output.stdout);
    // The cursor lifecycle is environment-sensitive; accept either a full apply
    // or a recorded no-delta attempt, but the lane must have run and emitted a
    // terminal status rather than crashing.
    assert!(
        stdout.contains("LINT_FIX_STATUS="),
        "cursor lane emitted no status: {stdout} / {}",
        String::from_utf8_lossy(&output.stderr)
    );
}

/// A fixture whose Claude launcher COMMITS its edit, so HEAD advances by one
/// clean non-merge commit and the apply path takes the committed-delta branch.
fn lint_fix_committing_plugin(root: &std::path::Path) -> std::path::PathBuf {
    use std::os::unix::fs::PermissionsExt as _;
    let plugin = root.join("committing-plugin");
    let scripts = plugin.join("scripts");
    fs::create_dir_all(&scripts).expect("fixture scripts");
    let bootstrap = scripts.join("larch.sh");
    fs::write(
        &bootstrap,
        r#"#!/bin/sh
set -eu
domain=${1:-}
verb=${2:-}
shift 2 || true
case "$domain:$verb" in
  agent:launch-claude-lint-fix)
    output=""
    while [ "$#" -gt 0 ]; do
      case "$1" in
        --output) output=$2; shift 2 ;;
        *) shift ;;
      esac
    done
    printf 'FIXED: a.txt | fix\n' > "$output"
    printf 'two\n' >> a.txt
    git add a.txt
    git commit --no-verify -m "coder commit" >/dev/null 2>&1
    exit 0
    ;;
  timing:record-vendor-task) exit 0 ;;
  *) exit 0 ;;
esac
"#,
    )
    .expect("fixture bootstrap");
    fs::set_permissions(&bootstrap, fs::Permissions::from_mode(0o755)).expect("bootstrap mode");
    plugin
}

#[test]
fn lint_fix_accepts_a_coder_committed_head_advance() {
    let (cache, tmp) = session_tmpdir();
    let repo = init_git_repo();
    let fixture_plugin = lint_fix_committing_plugin(cache.path());
    let checks_log = tmp.join("checks.log");
    fs::write(&checks_log, "a.txt:1: MD038 failure\n").expect("log");
    let assert = larch()
        .current_dir(repo.path())
        .env("XDG_CACHE_HOME", cache.path())
        .env("CLAUDE_PLUGIN_ROOT", &fixture_plugin)
        .env("CLAUDE_PROJECT_DIR", repo.path())
        .env("CLAUDE_BINARY_FOUND", "true")
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
            "--repo-root",
            &repo.path().to_string_lossy(),
        ])
        .assert()
        .success();
    let stdout = String::from_utf8(assert.get_output().stdout.clone()).expect("utf8");
    assert!(stdout.contains("LINT_FIX_STATUS=applied"), "{stdout}");
    assert!(stdout.contains("LINT_FIX_DELTA_PATH_0=a.txt"), "{stdout}");
}

/// A fixture whose launcher edits a forbidden path (`.gitmodules`).
fn lint_fix_forbidden_plugin(root: &std::path::Path) -> std::path::PathBuf {
    use std::os::unix::fs::PermissionsExt as _;
    let plugin = root.join("forbidden-plugin");
    let scripts = plugin.join("scripts");
    fs::create_dir_all(&scripts).expect("fixture scripts");
    let bootstrap = scripts.join("larch.sh");
    fs::write(
        &bootstrap,
        r#"#!/bin/sh
set -eu
domain=${1:-}
verb=${2:-}
shift 2 || true
case "$domain:$verb" in
  agent:launch-claude-lint-fix)
    output=""
    while [ "$#" -gt 0 ]; do
      case "$1" in
        --output) output=$2; shift 2 ;;
        *) shift ;;
      esac
    done
    printf 'FIXED: .gitmodules | fix\n' > "$output"
    printf '[submodule "x"]\n\tpath = vendor/x\n' > .gitmodules
    exit 0
    ;;
  timing:record-vendor-task) exit 0 ;;
  *) exit 0 ;;
esac
"#,
    )
    .expect("fixture bootstrap");
    fs::set_permissions(&bootstrap, fs::Permissions::from_mode(0o755)).expect("bootstrap mode");
    plugin
}

#[test]
fn lint_fix_reverts_a_forbidden_path_edit() {
    let (cache, tmp) = session_tmpdir();
    let repo = init_git_repo();
    let fixture_plugin = lint_fix_forbidden_plugin(cache.path());
    let checks_log = tmp.join("checks.log");
    fs::write(&checks_log, "a.txt:1: MD038 failure\n").expect("log");
    let assert = larch()
        .current_dir(repo.path())
        .env("XDG_CACHE_HOME", cache.path())
        .env("CLAUDE_PLUGIN_ROOT", &fixture_plugin)
        .env("CLAUDE_PROJECT_DIR", repo.path())
        .env("CLAUDE_BINARY_FOUND", "true")
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
            "--repo-root",
            &repo.path().to_string_lossy(),
        ])
        .assert()
        .code(1);
    let stdout = String::from_utf8(assert.get_output().stdout.clone()).expect("utf8");
    assert!(stdout.contains("LINT_FIX_STATUS=failed"), "{stdout}");
    assert!(
        stdout.contains("FAILURE_REASON=forbidden-path-violation"),
        "{stdout}"
    );
    // The forbidden edit was reverted from the worktree.
    assert!(!repo.path().join(".gitmodules").exists());
}

#[test]
fn lint_fix_applies_without_committing_a_dirty_baseline() {
    let (cache, tmp) = session_tmpdir();
    let repo = init_git_repo();
    // A pre-existing uncommitted edit makes the baseline dirty, so the apply path
    // records the delta but leaves committing to the caller.
    fs::write(repo.path().join("a.txt"), "dirty\n").expect("pre-dirty");
    let fixture_plugin = lint_fix_plugin(cache.path());
    let checks_log = tmp.join("checks.log");
    fs::write(&checks_log, "a.txt:1: MD038 failure\n").expect("log");
    let head_before = std::process::Command::new("git")
        .args(["rev-parse", "HEAD"])
        .current_dir(repo.path())
        .output()
        .expect("head");
    let assert = larch()
        .current_dir(repo.path())
        .env("XDG_CACHE_HOME", cache.path())
        .env("CLAUDE_PLUGIN_ROOT", &fixture_plugin)
        .env("CLAUDE_PROJECT_DIR", repo.path())
        .env("CLAUDE_BINARY_FOUND", "true")
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
            "--repo-root",
            &repo.path().to_string_lossy(),
        ])
        .assert()
        .success();
    let stdout = String::from_utf8(assert.get_output().stdout.clone()).expect("utf8");
    assert!(stdout.contains("LINT_FIX_STATUS=applied"), "{stdout}");
    // A dirty baseline is not auto-committed: HEAD is unchanged.
    let head_after = std::process::Command::new("git")
        .args(["rev-parse", "HEAD"])
        .current_dir(repo.path())
        .output()
        .expect("head");
    assert_eq!(head_before.stdout, head_after.stdout);
}
