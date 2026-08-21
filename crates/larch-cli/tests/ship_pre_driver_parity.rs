//! Frozen black-box contracts for the four retired Python ship handlers.

use std::{
    fs,
    os::unix::fs::PermissionsExt as _,
    path::{Path, PathBuf},
    process::{Command as ProcessCommand, Output},
};

use assert_cmd::Command;
use tempfile::TempDir;

fn larch(tmpdir: &Path) -> Command {
    let mut command = Command::cargo_bin("larch").expect("larch binary");
    command.env("IMPLEMENT_TMPDIR", tmpdir).current_dir(tmpdir);
    command
}

fn write_result(tmpdir: &Path, rows: &str) {
    let bgjob = tmpdir.join("bgjob");
    fs::create_dir_all(&bgjob).expect("bgjob");
    fs::write(
        bgjob.join("implement-step8-ship.result.env"),
        format!("STEP=implement-step8-ship\n{rows}"),
    )
    .expect("result env");
}

fn output_text(output: &[u8]) -> String {
    String::from_utf8_lossy(output).into_owned()
}

fn ship(tmpdir: &Path, arguments: &[&str]) -> Output {
    larch(tmpdir)
        .args(arguments)
        .output()
        .expect("ship command")
}

fn install_larch_stub(root: &Path) -> std::path::PathBuf {
    let plugin = root.join("plugin");
    fs::create_dir_all(plugin.join("scripts")).expect("scripts");
    let script = plugin.join("scripts/larch.sh");
    let events = root.join("events.log");
    let mode_file = root.join("stub-mode");
    fs::write(
        &script,
        format!(
            r#"#!/bin/sh
printf '%s\n' "$*" >> '{0}'
mode=success
if [ -f '{1}' ]; then IFS= read -r mode < '{1}'; fi
if [ "$1 $2" = "gh resolve-repo" ]; then
  echo owner/repo
  if [ "$mode" = "self-delete" ]; then rm -f -- "$0"; fi
  exit 0
fi
if [ "$1 $2" = "implement step-8-seed-initial" ] && [ "$mode" = "seed-fail" ]; then
  echo seed-refused >&2
  exit 9
fi
if [ "$1 $2" = "oos file" ]; then
  case "$mode" in
    oos-security) echo '{{"status":"security_sidecar_present"}}'; exit 7 ;;
    oos-fail) echo '{{"status":"ordinary_failure"}}'; exit 8 ;;
  esac
fi
if [ "$1 $2 $3" = "push rebase --no-push" ]; then
  case "$mode" in
    first-conflict) echo 'CONFLICT_FILES=src/a.rs,src/b.rs'; exit 1 ;;
    first-fail) echo 'REBASE_ERROR=first rebase failed'; exit 2 ;;
    first-empty-conflict) exit 1 ;;
  esac
  git commit --allow-empty -qm rebased
  exit 0
fi
if [ "$1 $2" = "git sync-local-main" ] && [ "$mode" = "sync-refusal" ]; then
  echo "refusing to update local 'main'" >&2
  exit 1
fi
if [ "$1 $2" = "push rebase" ]; then
  case "$mode" in
    push-conflict) echo 'CONFLICT_FILES=src/pushed.rs'; exit 1 ;;
    push-fail) echo 'PUSH_ERROR=push rebase failed'; exit 2 ;;
  esac
fi
exit 0
"#,
            events.display(),
            mode_file.display()
        ),
    )
    .expect("stub");
    fs::set_permissions(&script, fs::Permissions::from_mode(0o755)).expect("chmod");
    plugin
}

fn set_stub_mode(plugin: &Path, mode: &str) {
    fs::write(
        plugin.parent().expect("plugin parent").join("stub-mode"),
        format!("{mode}\n"),
    )
    .expect("stub mode");
}

fn init_repo(root: &Path) {
    for args in [
        vec!["init", "-q", "-b", "feature/pre-fix"],
        vec!["config", "user.email", "test@example.com"],
        vec!["config", "user.name", "Test"],
        vec!["config", "commit.gpgsign", "false"],
    ] {
        git(root, &args);
    }
    fs::write(root.join("tracked.txt"), "tracked\n").expect("tracked");
    git(root, &["add", "tracked.txt"]);
    git(root, &["commit", "-qm", "initial"]);
}

fn git(root: &Path, arguments: &[&str]) {
    assert!(
        ProcessCommand::new("git")
            .args(arguments)
            .current_dir(root)
            .status()
            .expect("git")
            .success()
    );
}

fn pre_fix(root: &Path, tmpdir: &Path, plugin: &Path) -> Output {
    pre_fix_with_mode(root, tmpdir, plugin, "success")
}

fn pre_fix_with_mode(root: &Path, tmpdir: &Path, plugin: &Path, mode: &str) -> Output {
    set_stub_mode(plugin, mode);
    larch(tmpdir)
        .env("CLAUDE_PLUGIN_ROOT", plugin)
        .current_dir(root)
        .args([
            "ship",
            "pre-fix-rebase",
            "--implement-tmpdir",
            tmpdir.to_str().expect("utf8"),
            "--cwd",
            root.to_str().expect("utf8"),
        ])
        .output()
        .expect("pre-fix")
}

struct DriverFixture {
    root: TempDir,
    repo: PathBuf,
    tmpdir: PathBuf,
    plugin: PathBuf,
}

fn driver_fixture(plan: Option<&str>) -> DriverFixture {
    let root = TempDir::new().expect("root");
    let repo = root.path().join("repo");
    let tmpdir = root.path().join("tmp");
    fs::create_dir_all(&repo).expect("repo");
    fs::create_dir_all(&tmpdir).expect("tmpdir");
    init_repo(&repo);
    let head = ProcessCommand::new("git")
        .args(["rev-parse", "HEAD"])
        .current_dir(&repo)
        .output()
        .expect("head");
    assert!(head.status.success());
    fs::write(
        tmpdir.join("step2-baseline.txt"),
        output_text(&head.stdout).trim(),
    )
    .expect("baseline");
    fs::write(tmpdir.join("session-id"), "ship-pre-driver-parity\n").expect("session id");
    fs::write(
        tmpdir.join("session-env.sh"),
        format!("REPO_ROOT={}\n", repo.display()),
    )
    .expect("session");
    if let Some(plan) = plan {
        fs::write(tmpdir.join("plan.txt"), plan).expect("plan");
    }
    let plugin = install_larch_stub(root.path());
    DriverFixture {
        root,
        repo,
        tmpdir,
        plugin,
    }
}

fn pre_driver(fixture: &DriverFixture, mode: &str) -> Output {
    set_stub_mode(&fixture.plugin, mode);
    larch(&fixture.tmpdir)
        .env("CLAUDE_PLUGIN_ROOT", &fixture.plugin)
        .current_dir(&fixture.repo)
        .args(["ship", "pre-driver"])
        .output()
        .expect("pre-driver")
}

#[test]
fn help_matches_the_frozen_argparse_contracts() {
    let tmp = TempDir::new().expect("tmp");
    for (verb, expected) in [
        (
            "route-exit",
            "usage: cli.py ship route-exit [-h] [--implement-tmpdir IMPLEMENT_TMPDIR]\n\noptions:\n  -h, --help            show this help message and exit\n  --implement-tmpdir IMPLEMENT_TMPDIR\n",
        ),
        (
            "normalize-assessment-handoff",
            "usage: cli.py ship normalize-assessment-handoff [-h]\n                                                [--implement-tmpdir IMPLEMENT_TMPDIR]\n\noptions:\n  -h, --help            show this help message and exit\n  --implement-tmpdir IMPLEMENT_TMPDIR\n",
        ),
        (
            "pre-fix-rebase",
            "usage: cli.py ship pre-fix-rebase [-h] [--implement-tmpdir IMPLEMENT_TMPDIR]\n                                  [--cwd CWD]\n\noptions:\n  -h, --help            show this help message and exit\n  --implement-tmpdir IMPLEMENT_TMPDIR\n  --cwd CWD\n",
        ),
        (
            "pre-driver",
            "usage: cli.py ship pre-driver [-h]\n\noptions:\n  -h, --help  show this help message and exit\n",
        ),
    ] {
        let output = ship(tmp.path(), &["ship", verb, "--help"]);
        assert!(
            output.status.success(),
            "{verb}: {}",
            output_text(&output.stderr)
        );
        assert_eq!(output_text(&output.stdout), expected, "{verb}");
        assert_eq!(output_text(&output.stderr), "", "{verb}");
    }
}

#[test]
fn ship_commands_fail_closed_without_a_tmpdir() {
    for verb in [
        "route-exit",
        "normalize-assessment-handoff",
        "pre-driver",
        "pre-fix-rebase",
    ] {
        let output = Command::cargo_bin("larch")
            .expect("larch binary")
            .env_remove("IMPLEMENT_TMPDIR")
            .args(["ship", verb])
            .output()
            .expect("ship command");
        assert_eq!(output.status.code(), Some(2), "{verb}");
        assert!(!output_text(&output.stderr).is_empty(), "{verb}");
    }
}

#[test]
fn route_exit_classifies_success_and_writes_the_handoff() {
    let tmp = TempDir::new().expect("tmp");
    write_result(tmp.path(), "BGJOB_RC=0\noutcome=OK\n");
    let output = ship(tmp.path(), &["ship", "route-exit"]);
    assert!(output.status.success());
    assert_eq!(output_text(&output.stdout), "NEXT_ACTION=complete\n");
    assert_eq!(
        fs::read_to_string(tmp.path().join(".ship-route-exit-handoff.env")).expect("handoff"),
        "NEXT_ACTION=complete\n"
    );
}

#[test]
fn route_exit_preserves_ci_fix_evidence_and_scope() {
    let tmp = TempDir::new().expect("tmp");
    write_result(
        tmp.path(),
        "BGJOB_RC=3\noutcome=NEEDS_USER_INPUT\nNEEDS_USER_REASON=main-ci-fail\nFAILED_RUN_ID=77\nFAILED_JOBS_COUNT=2\nCI_ERRORS_FILE=/tmp/errors.md\n",
    );
    let output = ship(tmp.path(), &["ship", "route-exit"]);
    assert!(output.status.success());
    assert_eq!(output_text(&output.stdout), "NEXT_ACTION=ci-fix\n");
    let handoff =
        fs::read_to_string(tmp.path().join(".ship-route-exit-handoff.env")).expect("handoff");
    for row in [
        "FAILED_RUN_ID=77",
        "NEEDS_USER_REASON=main-ci-fail",
        "CI_FAILURE_SCOPE=main",
        "FAILED_JOBS_COUNT=2",
        "CI_ERRORS_FILE=/tmp/errors.md",
        "PRE_FIX_REBASE_REQUIRED=true",
        "NEXT_ACTION=ci-fix",
    ] {
        assert!(handoff.lines().any(|line| line == row), "{row}: {handoff}");
    }
}

#[test]
fn route_exit_preserves_the_full_frozen_classification_table() {
    for (rc, outcome, reason, action) in [
        (0, "RETRY", "", "reship"),
        (1, "INTERNAL_ERROR", "", "tool-failure"),
        (
            3,
            "NEEDS_USER_INPUT",
            "postmerge-main-ci-fail",
            "postmerge-repair",
        ),
        (
            3,
            "NEEDS_USER_INPUT",
            "scope-disposition",
            "halt-scope-disposition",
        ),
        (3, "NEEDS_USER_INPUT", "oos-filing", "oos-pipeline"),
        (
            3,
            "NEEDS_USER_INPUT",
            "architectural-assessments",
            "assessments",
        ),
        (
            3,
            "NEEDS_USER_INPUT",
            "architectural-invariants-violation",
            "invariants-assessment",
        ),
        (
            3,
            "NEEDS_USER_INPUT",
            "architectural-guidelines-assessment",
            "guidelines-assessment",
        ),
        (3, "NEEDS_USER_INPUT", "first-fixer-non-health", "ci-fix"),
        (3, "NEEDS_USER_INPUT", "ci-local-unfixable:lint", "ci-fix"),
        (3, "NEEDS_USER_INPUT", "operator-decision", "operator-bail"),
        (4, "STALLED", "", "stall"),
    ] {
        let tmp = TempDir::new().expect("tmp");
        let reason_row = if reason.is_empty() {
            String::new()
        } else {
            format!("NEEDS_USER_REASON={reason}\n")
        };
        write_result(
            tmp.path(),
            &format!("BGJOB_RC={rc}\noutcome={outcome}\n{reason_row}"),
        );
        let output = ship(tmp.path(), &["ship", "route-exit"]);
        assert!(
            output.status.success(),
            "{rc}/{reason}: {}",
            output_text(&output.stderr)
        );
        assert_eq!(
            output_text(&output.stdout),
            format!("NEXT_ACTION={action}\n")
        );
    }
}

#[test]
fn route_exit_rejects_incomplete_or_inconsistent_results() {
    for body in [
        "STEP=wrong\nBGJOB_RC=0\noutcome=OK\n",
        "STEP=implement-step8-ship\nBGJOB_RC=timeout\noutcome=STALLED\n",
        "STEP=implement-step8-ship\nBGJOB_RC=orphaned\noutcome=STALLED\n",
        "STEP=implement-step8-ship\nBGJOB_RC=invalid\noutcome=OK\n",
        "STEP=implement-step8-ship\nBGJOB_RC=0\n",
        "STEP=implement-step8-ship\nBGJOB_RC=1\noutcome=OK\n",
        "STEP=implement-step8-ship\nBGJOB_RC=9\noutcome=UNKNOWN\n",
        "STEP=implement-step8-ship\r\nBGJOB_RC=0\r\noutcome=OK\r\n",
        "STEP=implement-step8-ship\n\nBGJOB_RC=0\noutcome=OK\n",
    ] {
        let tmp = TempDir::new().expect("tmp");
        let bgjob = tmp.path().join("bgjob");
        fs::create_dir(&bgjob).expect("bgjob");
        fs::write(bgjob.join("implement-step8-ship.result.env"), body).expect("result");
        let output = ship(tmp.path(), &["ship", "route-exit"]);
        assert_eq!(output.status.code(), Some(2), "{body:?}");
        assert!(!output_text(&output.stderr).is_empty(), "{body:?}");
        assert!(!tmp.path().join(".ship-route-exit-handoff.env").exists());
    }

    let tmp = TempDir::new().expect("tmp");
    let output = ship(tmp.path(), &["ship", "route-exit"]);
    assert_eq!(output.status.code(), Some(2));
    assert!(output_text(&output.stderr).contains("invalid bgjob result env"));
}

#[test]
fn route_exit_writes_long_detail_distill_ledger_and_health_evidence() {
    let tmp = TempDir::new().expect("tmp");
    let detail = "x".repeat(301);
    fs::write(tmp.path().join(".ship-pre-fix-rebase-ok"), "stale\n").expect("sentinel");
    write_result(
        tmp.path(),
        &format!(
            "BGJOB_RC=3\noutcome=NEEDS_USER_INPUT\nNEEDS_USER_REASON=ci-local-unfixable:lint\nFAILED_JOBS_COUNT=-2\nCI_ERRORS_FILE=\nCI_ERRORS_DISTILL_CLASS=artifact-missing\nDETAIL={detail}\nledger_ready=true\nMAIN_HEALTH_HEAD_SHA=abc123\n"
        ),
    );

    let output = ship(tmp.path(), &["ship", "route-exit"]);

    assert!(output.status.success(), "{}", output_text(&output.stderr));
    let handoff =
        fs::read_to_string(tmp.path().join(".ship-route-exit-handoff.env")).expect("handoff");
    for row in [
        "CI_FAILURE_SCOPE=pr",
        "FAILED_JOBS_COUNT=0",
        "CI_ERRORS_FILE=",
        "CI_ERRORS_DISTILL_CLASS=artifact-missing",
        "ledger_ready=true",
        "MAIN_HEALTH_HEAD_SHA=abc123",
        "PRE_FIX_REBASE_REQUIRED=true",
        "NEXT_ACTION=ci-fix",
    ] {
        assert!(handoff.lines().any(|line| line == row), "{row}: {handoff}");
    }
    let detail_path = tmp.path().join(".ship-route-exit-detail.txt");
    assert!(handoff.contains(&format!("DETAIL_FILE={}", detail_path.display())));
    assert_eq!(
        fs::read_to_string(detail_path).expect("detail"),
        format!("{detail}\n")
    );
    assert!(!tmp.path().join(".ship-pre-fix-rebase-ok").exists());
}

#[test]
fn route_exit_retries_no_checks_after_phase14_and_fails_on_unsafe_outputs() {
    let tmp = TempDir::new().expect("tmp");
    write_result(
        tmp.path(),
        "BGJOB_RC=4\noutcome=STALLED\nDETAIL=no-ci-checks-observed\n",
    );
    fs::write(tmp.path().join("ship-pr-rrr-after-phase14.flag"), "").expect("flag");
    let output = ship(tmp.path(), &["ship", "route-exit"]);
    assert!(output.status.success(), "{}", output_text(&output.stderr));
    assert_eq!(output_text(&output.stdout), "NEXT_ACTION=reship\n");

    let retry_tmp = TempDir::new().expect("retry tmp");
    fs::create_dir(retry_tmp.path().join("ship-pr-net-retries-python.count")).expect("count dir");
    write_result(retry_tmp.path(), "BGJOB_RC=6\noutcome=TRANSIENT_NETWORK\n");
    let retry = ship(retry_tmp.path(), &["ship", "route-exit"]);
    assert_eq!(retry.status.code(), Some(2));
    assert!(output_text(&retry.stderr).contains("transient retry counter"));

    let handoff_tmp = TempDir::new().expect("handoff tmp");
    fs::create_dir(handoff_tmp.path().join(".ship-route-exit-handoff.env")).expect("handoff dir");
    write_result(handoff_tmp.path(), "BGJOB_RC=0\noutcome=OK\n");
    let handoff = ship(handoff_tmp.path(), &["ship", "route-exit"]);
    assert_eq!(handoff.status.code(), Some(2));
    assert!(output_text(&handoff.stderr).contains("cannot write route-exit handoff"));
}

#[test]
fn route_exit_prefers_the_persisted_conflict_handoff() {
    let tmp = TempDir::new().expect("tmp");
    write_result(tmp.path(), "BGJOB_RC=4\noutcome=STALLED\n");
    fs::write(
        tmp.path().join("ship-pr-state.sh"),
        "RESUME_PHASE=ship-pr-rrr-phase14\nCALLER_KIND=ship_pr_pre_push\nCONFLICT_FILES=a.rs,b.rs\n",
    )
    .expect("state");
    let output = ship(tmp.path(), &["ship", "route-exit"]);
    assert!(output.status.success());
    assert_eq!(output_text(&output.stdout), "NEXT_ACTION=conflict-fix\n");
    let handoff =
        fs::read_to_string(tmp.path().join(".ship-route-exit-handoff.env")).expect("handoff");
    assert_eq!(
        handoff,
        "RESUME_PHASE=ship-pr-rrr-phase14\nCALLER_KIND=ship_pr_pre_push\nCONFLICT_FILES=a.rs,b.rs\nNEXT_ACTION=conflict-fix\n"
    );
}

#[test]
fn route_exit_fails_closed_and_clears_a_stale_handoff() {
    let tmp = TempDir::new().expect("tmp");
    fs::write(tmp.path().join(".ship-route-exit-handoff.env"), "stale\n").expect("stale");
    write_result(tmp.path(), "BGJOB_RC=0\noutcome=OK\noutcome=forged\n");
    let output = ship(tmp.path(), &["ship", "route-exit"]);
    assert_eq!(output.status.code(), Some(2));
    assert_eq!(output_text(&output.stdout), "");
    assert!(output_text(&output.stderr).contains("malformed bgjob result env"));
    assert!(!tmp.path().join(".ship-route-exit-handoff.env").exists());
}

#[test]
fn fourth_transient_attempt_seeds_stall_without_sleeping() {
    let tmp = TempDir::new().expect("tmp");
    let plugin = install_larch_stub(tmp.path());
    fs::write(tmp.path().join("ship-pr-net-retries-python.count"), "3\n").expect("count");
    write_result(tmp.path(), "BGJOB_RC=6\noutcome=TRANSIENT_NETWORK\n");
    let output = larch(tmp.path())
        .env("CLAUDE_PLUGIN_ROOT", plugin)
        .args(["ship", "route-exit"])
        .output()
        .expect("route");
    assert!(output.status.success(), "{}", output_text(&output.stderr));
    assert_eq!(output_text(&output.stdout), "NEXT_ACTION=stall\n");
    assert_eq!(
        fs::read_to_string(tmp.path().join("ship-pr-net-retries-python.count")).expect("count"),
        "4\n"
    );
}

#[test]
fn assessment_normalization_canonicalizes_order_and_strips_terminal_reason() {
    let tmp = TempDir::new().expect("tmp");
    fs::write(
        tmp.path().join(".ship-route-exit-handoff.env"),
        "FAILED_RUN_ID=77\nNEEDS_USER_REASON=architectural-assessments\nNEXT_ACTION=assessments\nDETAIL=guidelines,invariants\n",
    )
    .expect("handoff");
    let output = ship(tmp.path(), &["ship", "normalize-assessment-handoff"]);
    assert!(output.status.success(), "{}", output_text(&output.stderr));
    assert_eq!(
        output_text(&output.stdout),
        "NEXT_ACTION=assessments\nASSESSMENT_REQUESTED_KINDS=invariants,guidelines\n"
    );
    assert_eq!(
        fs::read_to_string(tmp.path().join(".ship-route-exit-handoff.env")).expect("handoff"),
        "FAILED_RUN_ID=77\nNEXT_ACTION=assessments\nDETAIL=invariants,guidelines\n"
    );
}

#[test]
fn assessment_normalization_preserves_non_kv_lines_and_rejects_duplicates() {
    let tmp = TempDir::new().expect("tmp");
    let handoff = tmp.path().join(".ship-route-exit-handoff.env");
    fs::write(
        &handoff,
        "legacy note\n=legacy row\nNEXT_ACTION=guidelines-assessment\nFAILED_RUN_ID=77\n",
    )
    .expect("handoff");
    let output = ship(tmp.path(), &["ship", "normalize-assessment-handoff"]);
    assert!(output.status.success(), "{}", output_text(&output.stderr));
    assert_eq!(
        fs::read_to_string(&handoff).expect("handoff"),
        "legacy note\n=legacy row\nFAILED_RUN_ID=77\nNEXT_ACTION=assessments\nDETAIL=guidelines\n"
    );

    fs::write(
        &handoff,
        "NEXT_ACTION=invariants-assessment\nNEXT_ACTION=guidelines-assessment\n",
    )
    .expect("handoff");
    let duplicate = ship(tmp.path(), &["ship", "normalize-assessment-handoff"]);
    assert_eq!(duplicate.status.code(), Some(2));
    assert!(output_text(&duplicate.stderr).contains("duplicate handoff key: NEXT_ACTION"));
}

#[test]
fn assessment_normalization_rejects_unsafe_or_noncanonical_detail_files() {
    let tmp = TempDir::new().expect("tmp");
    let outside = TempDir::new().expect("outside");
    let outside_detail = outside.path().join("detail.txt");
    fs::write(&outside_detail, "invariants").expect("outside detail");
    fs::write(
        tmp.path().join(".ship-route-exit-handoff.env"),
        format!(
            "NEXT_ACTION=assessments\nDETAIL_FILE={}\n",
            outside_detail.display()
        ),
    )
    .expect("handoff");
    let unsafe_output = ship(tmp.path(), &["ship", "normalize-assessment-handoff"]);
    assert_eq!(unsafe_output.status.code(), Some(2));
    assert!(output_text(&unsafe_output.stderr).contains("unsafe DETAIL_FILE"));

    let detail = tmp.path().join(".ship-route-exit-detail.txt");
    fs::write(&detail, "invariants\n").expect("detail");
    fs::write(
        tmp.path().join(".ship-route-exit-handoff.env"),
        format!(
            "NEXT_ACTION=assessments\nDETAIL_FILE={}\n",
            detail.display()
        ),
    )
    .expect("handoff");
    let output = ship(tmp.path(), &["ship", "normalize-assessment-handoff"]);
    assert_eq!(output.status.code(), Some(2));
    assert!(output_text(&output.stderr).contains("canonical tokens"));
}

#[test]
fn assessment_normalization_rejects_every_ambiguous_kind_shape() {
    for (body, expected) in [
        ("NEXT_ACTION=complete\n", "not an assessment handoff"),
        (
            "NEXT_ACTION=assessments\nDETAIL=invariants\nDETAIL_FILE=/tmp/detail\n",
            "cannot both be set",
        ),
        ("NEXT_ACTION=assessments\n", "missing assessment detail"),
        (
            "NEXT_ACTION=assessments\nDETAIL=invariants,invariants\n",
            "empty or duplicate tokens",
        ),
        (
            "NEXT_ACTION=assessments\nDETAIL=performance\n",
            "unsupported assessment kind",
        ),
    ] {
        let tmp = TempDir::new().expect("tmp");
        fs::write(tmp.path().join(".ship-route-exit-handoff.env"), body).expect("handoff");
        let output = ship(tmp.path(), &["ship", "normalize-assessment-handoff"]);
        assert_eq!(output.status.code(), Some(2), "{body:?}");
        assert!(
            output_text(&output.stderr).contains(expected),
            "{body:?}: {}",
            output_text(&output.stderr)
        );
    }
}

#[test]
fn pre_fix_closed_pr_skips_every_git_mutation_but_writes_proof() {
    let root = TempDir::new().expect("root");
    let tmpdir = root.path().join("tmp");
    fs::create_dir(&tmpdir).expect("tmpdir");
    init_repo(root.path());
    let plugin = install_larch_stub(root.path());
    fs::write(
        tmpdir.join("ship-pr-state.sh"),
        "PHASE=checks\nBRANCH_NAME=feature/pre-fix\nRUN_ID=run-8\nREPO=owner/repo\nPR_CLOSED=true\n",
    )
    .expect("state");
    let output = pre_fix(root.path(), &tmpdir, &plugin);
    assert!(output.status.success(), "{}", output_text(&output.stderr));
    assert_eq!(
        output_text(&output.stdout),
        "PRE_FIX_REBASE_STATUS=skip\nNEXT_ACTION=continue\n"
    );
    assert_eq!(
        fs::read_to_string(tmpdir.join(".ship-pre-fix-rebase-ok")).expect("proof"),
        "PRE_FIX_REBASE_OK=true\n"
    );
}

#[test]
fn pre_fix_conflict_handoff_precedes_the_closed_pr_skip() {
    let root = TempDir::new().expect("root");
    let tmpdir = root.path().join("tmp");
    fs::create_dir(&tmpdir).expect("tmpdir");
    init_repo(root.path());
    let plugin = install_larch_stub(root.path());
    fs::write(
        tmpdir.join("ship-pr-state.sh"),
        "PHASE=checks\nBRANCH_NAME=feature/pre-fix\nRUN_ID=run-8\nREPO=owner/repo\nPR_CLOSED=true\nCI_FIX_REBASE_PENDING=true\nCI_FIX_REBASE_PENDING_HEAD=abc\nRESUME_PHASE=ship-pr-rrr-phase14\nCALLER_KIND=ship_pr_pre_push\nCONFLICT_FILES=src/lib.rs\nEXIT_CODE=4\nBAIL_REASON=stale\nBAIL_NEEDS_USER_INPUT=true\nFAILED_RUN_ID=77\nBAIL_FAILURE_DETAIL_LOG=/tmp/stale\n",
    )
    .expect("state");
    fs::write(
        tmpdir.join(".ship-route-exit-handoff.env"),
        "legacy note\nKEEP=first\nKEEP=second\nNEXT_ACTION=stale\n",
    )
    .expect("handoff");
    let output = pre_fix(root.path(), &tmpdir, &plugin);
    assert!(output.status.success(), "{}", output_text(&output.stderr));
    assert_eq!(
        output_text(&output.stdout),
        "PRE_FIX_REBASE_STATUS=conflict\nNEXT_ACTION=conflict-fix\n"
    );
    let state = fs::read_to_string(tmpdir.join("ship-pr-state.sh")).expect("state");
    assert!(state.contains("PHASE=rebase\n"));
    assert!(state.contains("CONFLICT_FILES=src/lib.rs\n"));
    assert!(state.contains("CI_FIX_REBASE_PENDING=false\n"));
    assert!(state.contains("CI_FIX_REBASE_PENDING_HEAD=\n"));
    let handoff = fs::read_to_string(tmpdir.join(".ship-route-exit-handoff.env")).expect("handoff");
    assert!(handoff.lines().any(|line| line == "KEEP=first"));
    assert!(!handoff.lines().any(|line| line == "KEEP=second"));
    assert!(
        handoff
            .lines()
            .any(|line| line == "NEXT_ACTION=conflict-fix")
    );
    for stale in [
        "EXIT_CODE=",
        "BAIL_REASON=",
        "BAIL_NEEDS_USER_INPUT=",
        "FAILED_RUN_ID=",
        "BAIL_FAILURE_DETAIL_LOG=",
    ] {
        assert!(
            !state.lines().any(|line| line.starts_with(stale)),
            "{state}"
        );
    }
}

#[test]
fn pre_fix_rebases_with_the_fork_aware_remote_pushes_and_increments_state() {
    for (forked, remote) in [("false", "origin"), ("true", "upstream")] {
        let root = TempDir::new().expect("root");
        let tmpdir = root.path().join("tmp");
        fs::create_dir(&tmpdir).expect("tmpdir");
        init_repo(root.path());
        let plugin = install_larch_stub(root.path());
        let events = root.path().join("events.log");
        fs::write(
            tmpdir.join("ship-pr-state.sh"),
            format!(
                "PHASE=checks\nBRANCH_NAME=feature/pre-fix\nRUN_ID=run-8\nREPO=owner/repo\nFORKED_TARGET={forked}\nREBASE_COUNT=2\n"
            ),
        )
        .expect("state");
        let output = pre_fix(root.path(), &tmpdir, &plugin);
        assert!(output.status.success(), "{}", output_text(&output.stderr));
        assert_eq!(
            output_text(&output.stdout),
            "PRE_FIX_REBASE_STATUS=ok\nNEXT_ACTION=continue\n"
        );
        assert_eq!(
            fs::read_to_string(&events).expect("events"),
            format!(
                "gh resolve-repo\npush rebase --no-push --keep-on-conflict --base-remote {remote} --base-ref main\ngit sync-local-main --base-remote {remote} --base-ref main\npush rebase --base-remote {remote} --base-ref main\n"
            )
        );
        assert!(
            fs::read_to_string(tmpdir.join("ship-pr-state.sh"))
                .expect("state")
                .lines()
                .any(|line| line == "REBASE_COUNT=3")
        );
    }
}

#[test]
fn pre_fix_validates_tmpdir_state_branch_and_repository_before_rebasing() {
    let outer = TempDir::new().expect("outer");
    let missing = outer.path().join("missing");
    let missing_output = Command::cargo_bin("larch")
        .expect("larch binary")
        .args([
            "ship",
            "pre-fix-rebase",
            "--implement-tmpdir",
            missing.to_str().expect("utf8"),
        ])
        .current_dir(outer.path())
        .output()
        .expect("pre-fix");
    assert_eq!(missing_output.status.code(), Some(2));
    assert!(output_text(&missing_output.stderr).contains("existing directory"));

    let root = TempDir::new().expect("root");
    let tmpdir = root.path().join("tmp");
    fs::create_dir(&tmpdir).expect("tmpdir");
    init_repo(root.path());
    let plugin = install_larch_stub(root.path());
    let missing_state = pre_fix(root.path(), &tmpdir, &plugin);
    assert_eq!(missing_state.status.code(), Some(2));
    assert!(output_text(&missing_state.stderr).contains("ship-pr-state.sh is missing"));

    for (state, expected) in [
        (
            "BRANCH_NAME=feature/pre-fix\nRUN_ID=run-8\n",
            "REPO is missing",
        ),
        (
            "BRANCH_NAME=feature/pre-fix\nREPO=owner/repo\n",
            "RUN_ID is missing",
        ),
        (
            "BRANCH_NAME=another-branch\nRUN_ID=run-8\nREPO=owner/repo\n",
            "does not match ship-pr-state.sh BRANCH_NAME",
        ),
        (
            "BRANCH_NAME=feature/pre-fix\nRUN_ID=run-8\nREPO=other/repo\n",
            "does not match ship-pr-state.sh REPO",
        ),
    ] {
        fs::write(tmpdir.join("ship-pr-state.sh"), state).expect("state");
        let output = pre_fix(root.path(), &tmpdir, &plugin);
        assert_eq!(output.status.code(), Some(2), "{state:?}");
        assert!(
            output_text(&output.stderr).contains(expected),
            "{state:?}: {}",
            output_text(&output.stderr)
        );
    }

    git(root.path(), &["branch", "-m", "main"]);
    fs::write(
        tmpdir.join("ship-pr-state.sh"),
        "BRANCH_NAME=main\nRUN_ID=run-8\nREPO=owner/repo\nFORKED_TARGET=false\n",
    )
    .expect("state");
    let main = pre_fix(root.path(), &tmpdir, &plugin);
    assert_eq!(main.status.code(), Some(2));
    assert!(output_text(&main.stderr).contains("refusing pre-fix rebase"));
}

#[test]
fn pre_fix_resolves_the_checkout_from_the_session_when_cwd_is_omitted() {
    let root = TempDir::new().expect("root");
    let tmpdir = root.path().join("tmp");
    fs::create_dir(&tmpdir).expect("tmpdir");
    init_repo(root.path());
    let plugin = install_larch_stub(root.path());
    fs::write(
        tmpdir.join("session-env.sh"),
        format!("REPO_ROOT={}\n", root.path().display()),
    )
    .expect("session");
    fs::write(
        tmpdir.join("ship-pr-state.sh"),
        "BRANCH_NAME=feature/pre-fix\nRUN_ID=run-8\nREPO=owner/repo\nPR_CLOSED=true\n",
    )
    .expect("state");

    let output = larch(&tmpdir)
        .env("CLAUDE_PLUGIN_ROOT", plugin)
        .current_dir(root.path())
        .args([
            "ship",
            "pre-fix-rebase",
            "--implement-tmpdir",
            tmpdir.to_str().expect("utf8"),
        ])
        .output()
        .expect("pre-fix");

    assert!(output.status.success(), "{}", output_text(&output.stderr));
    assert_eq!(
        output_text(&output.stdout),
        "PRE_FIX_REBASE_STATUS=skip\nNEXT_ACTION=continue\n"
    );
}

#[test]
fn pre_fix_handles_active_rebases_phase14_proof_and_unsafe_conflicts() {
    let active = TempDir::new().expect("active");
    let active_tmp = active.path().join("tmp");
    fs::create_dir(&active_tmp).expect("tmpdir");
    init_repo(active.path());
    let plugin = install_larch_stub(active.path());
    fs::write(
        active_tmp.join("ship-pr-state.sh"),
        "BRANCH_NAME=feature/pre-fix\nRUN_ID=run-8\nREPO=owner/repo\n",
    )
    .expect("state");
    fs::create_dir(active.path().join(".git/rebase-merge")).expect("rebase marker");
    let output = pre_fix(active.path(), &active_tmp, &plugin);
    assert!(output.status.success(), "{}", output_text(&output.stderr));
    assert_eq!(
        output_text(&output.stdout),
        "PRE_FIX_REBASE_STATUS=stall\nNEXT_ACTION=stall\n"
    );

    let phase = TempDir::new().expect("phase");
    let phase_tmp = phase.path().join("tmp");
    fs::create_dir(&phase_tmp).expect("tmpdir");
    init_repo(phase.path());
    let plugin = install_larch_stub(phase.path());
    fs::write(
        phase_tmp.join("ship-pr-state.sh"),
        "BRANCH_NAME=feature/pre-fix\nRUN_ID=run-8\nREPO=owner/repo\n",
    )
    .expect("state");
    fs::write(
        phase_tmp.join("ship-pr-rrr-after-phase14.flag"),
        "RESUME_PHASE=ship-pr-rrr-phase14\nREASON=mergeStateStatus=DIRTY\n",
    )
    .expect("flag");
    let output = pre_fix(phase.path(), &phase_tmp, &plugin);
    assert!(output.status.success(), "{}", output_text(&output.stderr));
    assert_eq!(
        output_text(&output.stdout),
        "PRE_FIX_REBASE_STATUS=skip\nNEXT_ACTION=continue\n"
    );

    fs::write(
        phase_tmp.join("ship-pr-state.sh"),
        "BRANCH_NAME=feature/pre-fix\nRUN_ID=run-8\nREPO=owner/repo\nRESUME_PHASE=ship-pr-rrr-phase14\nCALLER_KIND=ship_pr_pre_push\nCONFLICT_FILES=../secret\n",
    )
    .expect("state");
    fs::remove_file(phase_tmp.join("ship-pr-rrr-after-phase14.flag")).expect("remove flag");
    let output = pre_fix(phase.path(), &phase_tmp, &plugin);
    assert_eq!(output.status.code(), Some(2));
    assert!(output_text(&output.stderr).contains("invalid CONFLICT_FILES entry"));
}

#[test]
fn pre_fix_maps_rebase_failures_and_conflicts_without_losing_detail() {
    for (mode, expected_status, expected_action, expected_detail) in [
        ("first-conflict", "conflict", "conflict-fix", ""),
        ("first-fail", "stall", "stall", "first rebase failed"),
        ("first-empty-conflict", "stall", "stall", "rebase failed"),
        (
            "sync-refusal",
            "stall",
            "stall",
            "refusing to update local 'main' while checked out on main",
        ),
        ("push-conflict", "conflict", "conflict-fix", ""),
        ("push-fail", "stall", "stall", "push rebase failed"),
    ] {
        let root = TempDir::new().expect("root");
        let tmpdir = root.path().join("tmp");
        fs::create_dir(&tmpdir).expect("tmpdir");
        init_repo(root.path());
        let plugin = install_larch_stub(root.path());
        fs::write(
            tmpdir.join("ship-pr-state.sh"),
            "BRANCH_NAME=feature/pre-fix\nRUN_ID=run-8\nREPO=owner/repo\n",
        )
        .expect("state");

        let output = pre_fix_with_mode(root.path(), &tmpdir, &plugin, mode);

        assert!(
            output.status.success(),
            "{mode}: {}",
            output_text(&output.stderr)
        );
        let stdout = output_text(&output.stdout);
        assert!(
            stdout.contains(&format!("PRE_FIX_REBASE_STATUS={expected_status}\n")),
            "{mode}: {stdout}"
        );
        assert!(
            stdout.contains(&format!("NEXT_ACTION={expected_action}\n")),
            "{mode}: {stdout}"
        );
        if !expected_detail.is_empty() {
            assert!(stdout.contains(expected_detail), "{mode}: {stdout}");
        }
        if expected_action == "conflict-fix" {
            assert!(tmpdir.join("ship-pr-rrr-after-phase14.flag").is_file());
            assert!(tmpdir.join(".ship-pre-fix-rebase-ok").is_file());
        }
    }
}

#[test]
fn pre_fix_fails_closed_when_the_plugin_or_success_sentinel_disappears() {
    let root = TempDir::new().expect("root");
    let tmpdir = root.path().join("tmp");
    fs::create_dir(&tmpdir).expect("tmpdir");
    init_repo(root.path());
    let plugin = install_larch_stub(root.path());
    fs::write(
        tmpdir.join("ship-pr-state.sh"),
        "BRANCH_NAME=feature/pre-fix\nRUN_ID=run-8\nREPO=owner/repo\n",
    )
    .expect("state");
    let output = pre_fix_with_mode(root.path(), &tmpdir, &plugin, "self-delete");
    assert_eq!(output.status.code(), Some(2));
    assert!(output_text(&output.stderr).contains("handoff setup failed"));

    let root = TempDir::new().expect("root");
    let tmpdir = root.path().join("tmp");
    fs::create_dir(&tmpdir).expect("tmpdir");
    init_repo(root.path());
    let plugin = install_larch_stub(root.path());
    fs::write(
        tmpdir.join("ship-pr-state.sh"),
        "BRANCH_NAME=feature/pre-fix\nRUN_ID=run-8\nREPO=owner/repo\nPR_CLOSED=true\n",
    )
    .expect("state");
    fs::create_dir(tmpdir.join(".ship-pre-fix-rebase-ok")).expect("sentinel directory");
    let output = pre_fix(root.path(), &tmpdir, &plugin);
    assert_eq!(output.status.code(), Some(2));
    assert!(output_text(&output.stderr).contains("cannot write pre-fix rebase sentinel"));
}

#[test]
fn pre_driver_runs_the_guard_before_repo_root_resolution() {
    let tmp = TempDir::new().expect("tmp");
    let plugin = tmp.path().join("plugin");
    fs::create_dir_all(plugin.join("scripts")).expect("scripts");
    let script = plugin.join("scripts/larch.sh");
    fs::write(&script, "#!/bin/sh\necho guard-refused >&2\nexit 9\n").expect("stub");
    fs::set_permissions(&script, fs::Permissions::from_mode(0o755)).expect("chmod");
    let output = larch(tmp.path())
        .env("CLAUDE_PLUGIN_ROOT", plugin)
        .args(["ship", "pre-driver"])
        .output()
        .expect("pre-driver");
    assert_eq!(output.status.code(), Some(4));
    assert_eq!(output_text(&output.stdout), "NEXT_ACTION=stall\n");
    assert!(output_text(&output.stderr).contains("guard-refused"));
}

#[test]
fn pre_driver_runs_scope_seed_and_oos_before_shipping() {
    let fixture = driver_fixture(Some("## Files to modify\n\n"));

    let output = pre_driver(&fixture, "success");

    assert!(output.status.success(), "{}", output_text(&output.stderr));
    assert_eq!(output_text(&output.stdout), "NEXT_ACTION=ship\n");
    let events = fs::read_to_string(fixture.root.path().join("events.log")).expect("events");
    assert_eq!(
        events,
        format!(
            "implement step-8-python-guard\nimplement step-8-seed-initial\noos file --implement-tmpdir {}\n",
            fixture.tmpdir.display()
        )
    );
    assert!(fixture.tmpdir.join("plan-coverage.json").is_file());
    assert!(fixture.tmpdir.join("plan-coverage.env").is_file());
}

#[test]
fn pre_driver_maps_seed_and_oos_failures_to_their_frozen_actions() {
    let seed = driver_fixture(Some("## Files to modify\n\n"));
    let seed_output = pre_driver(&seed, "seed-fail");
    assert_eq!(seed_output.status.code(), Some(9));
    assert_eq!(output_text(&seed_output.stdout), "NEXT_ACTION=halt-seed\n");
    assert!(output_text(&seed_output.stderr).contains("seed-refused"));

    for (mode, code, action) in [
        ("oos-security", 7, "oos-pipeline"),
        ("oos-fail", 8, "halt-oos"),
    ] {
        let fixture = driver_fixture(Some("## Files to modify\n\n"));
        let output = pre_driver(&fixture, mode);
        assert_eq!(output.status.code(), Some(code), "{mode}");
        assert_eq!(
            output_text(&output.stdout),
            format!("NEXT_ACTION={action}\n"),
            "{mode}"
        );
    }
}

#[test]
fn pre_driver_fails_closed_for_missing_repo_and_invalid_scope_state() {
    let missing_root = TempDir::new().expect("tmp");
    let plugin = install_larch_stub(missing_root.path());
    let output = larch(missing_root.path())
        .env("CLAUDE_PLUGIN_ROOT", plugin)
        .args(["ship", "pre-driver"])
        .output()
        .expect("pre-driver");
    assert_eq!(output.status.code(), Some(2));
    assert_eq!(output_text(&output.stdout), "NEXT_ACTION=halt-seed\n");

    let missing_plan = driver_fixture(None);
    let output = pre_driver(&missing_plan, "success");
    assert_eq!(output.status.code(), Some(4));
    assert!(output_text(&output.stderr).contains("coverage-recompute-failed"));

    let scope = driver_fixture(Some(
        "## Files to modify\n\n### NEW: `a.txt`\n\n### NEW: `b.txt`\n",
    ));
    fs::write(scope.repo.join("a.txt"), "touched\n").expect("touched");
    let output = pre_driver(&scope, "success");
    assert_eq!(output.status.code(), Some(3));
    assert_eq!(
        output_text(&output.stdout),
        "needs_user_reason=scope-disposition\nNEXT_ACTION=halt-scope-disposition\n"
    );
}

#[test]
fn pre_driver_stalls_when_the_verified_plugin_cannot_be_resolved() {
    let tmp = TempDir::new().expect("tmp");
    let output = larch(tmp.path())
        .env("CLAUDE_PLUGIN_ROOT", tmp.path().join("missing-plugin"))
        .args(["ship", "pre-driver"])
        .output()
        .expect("pre-driver");
    assert_eq!(output.status.code(), Some(4));
    assert_eq!(output_text(&output.stdout), "NEXT_ACTION=stall\n");
    assert!(!output_text(&output.stderr).is_empty());
}
