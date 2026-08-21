//! Frozen black-box contracts for the four retired Python ship handlers.

use std::{
    fs,
    os::unix::fs::PermissionsExt as _,
    path::Path,
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
    fs::write(
        &script,
        format!(
            "#!/bin/sh\nprintf '%s\\n' \"$*\" >> '{}'\nif [ \"$1 $2\" = \"gh resolve-repo\" ]; then echo owner/repo; fi\nif [ \"$1 $2 $3\" = \"push rebase --no-push\" ]; then git commit --allow-empty -qm rebased; fi\nexit 0\n",
            events.display()
        ),
    )
    .expect("stub");
    fs::set_permissions(&script, fs::Permissions::from_mode(0o755)).expect("chmod");
    plugin
}

fn init_repo(root: &Path) {
    for args in [
        vec!["init", "-q", "-b", "feature/pre-fix"],
        vec!["config", "user.email", "test@example.com"],
        vec!["config", "user.name", "Test"],
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
