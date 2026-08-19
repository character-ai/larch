//! Black-box parity coverage for the Rust `/implement` Step 5-7a review-routing
//! verbs. Each success path drives the real binary against a fixture whose
//! `scripts/larch.sh` and `python/cli.py` stubs stand in for the delegated
//! composites, so the assertions pin the relayed stdout grammar and exit codes
//! rather than only the argument-validation boundary.

use std::{fs, os::unix::fs::PermissionsExt as _, path::Path};

use assert_cmd::Command as AssertCommand;
use larch_test_support::{GitFixture, GitRepository};
use tempfile::TempDir;

const LARCH_STUB: &str = r#"#!/usr/bin/env bash
case "$1 $2" in
  "bgjob adapt") printf 'ADAPTER_RELAY=ok\nNEXT_ACTION=continue\n' ;;
  "bgjob start") printf 'BGJOB_STATUS=STARTED STEP=implement-step7a PGID=4242\n' ;;
  "checks run-relevant") printf 'RELEVANT_CHECKS_OK=true SITE=step5-review-fixes COVERAGE=full PHASE=post\n' ;;
  "implement step-5-resume") printf 'STEP5_REVIEW_STATUS=stall\nNEXT_ACTION=continue\n' ;;
  *) : ;;
esac
exit 0
"#;

// The checks-input identity verbs are Rust-owned and run in process, so the
// stub only has to stand in as a silent, successful delegated composite.
const PYTHON_STUB: &str = r"#!/usr/bin/env python3
import sys

sys.exit(0)
";

struct Fixture {
    _root: TempDir,
    plugin: std::path::PathBuf,
    tmpdir: std::path::PathBuf,
}

fn fixture() -> Fixture {
    let root = TempDir::new().expect("temp root");
    let plugin = root.path().join("plugin");
    let tmpdir = root.path().join("tmp");
    fs::create_dir_all(plugin.join("scripts")).expect("scripts dir");
    fs::create_dir_all(plugin.join("python")).expect("python dir");
    fs::create_dir_all(&tmpdir).expect("tmpdir");
    let larch = plugin.join("scripts").join("larch.sh");
    fs::write(&larch, LARCH_STUB).expect("write larch stub");
    fs::set_permissions(&larch, fs::Permissions::from_mode(0o755)).expect("chmod larch");
    fs::write(plugin.join("python").join("cli.py"), PYTHON_STUB).expect("write python stub");
    // Resolve `/var` -> `/private/var` and similar so the fixture tmpdir has no
    // symlinked ancestor, which the step-7a guard rejects by contract.
    let plugin = fs::canonicalize(&plugin).expect("canonical plugin");
    let tmpdir = fs::canonicalize(&tmpdir).expect("canonical tmpdir");
    Fixture {
        _root: root,
        plugin,
        tmpdir,
    }
}

fn larch(plugin: &Path, tmpdir: &Path) -> AssertCommand {
    let mut command = AssertCommand::cargo_bin("larch").expect("larch binary");
    command
        .env("CLAUDE_PLUGIN_ROOT", plugin)
        .env("IMPLEMENT_TMPDIR", tmpdir)
        .current_dir(tmpdir);
    command
}

fn stdout_of(output: &std::process::Output) -> String {
    String::from_utf8_lossy(&output.stdout).into_owned()
}

/// Seed a real repository and the session env the in-process identity verbs read.
///
/// `checks-step5-resume` resolves `REPO_ROOT` from `session-env.sh` and then
/// fingerprints that worktree in process, so the fixture needs a Git toplevel
/// with a resolvable `HEAD` rather than a stubbed child.
fn seed_session_repo(tmpdir: &Path) -> GitRepository {
    let repository = GitRepository::builder(GitFixture::Refs)
        .build()
        .expect("git fixture");
    fs::write(
        tmpdir.join("session-env.sh"),
        format!("REPO_ROOT={}\n", repository.root().display()),
    )
    .expect("write session env");
    repository
}

#[test]
fn step7a_bgjob_launch_relays_started_envelope() {
    let fixture = fixture();
    let output = larch(&fixture.plugin, &fixture.tmpdir)
        .args(["implement", "step-7a", "--bgjob-launch", "true"])
        .output()
        .expect("run step-7a");
    assert!(output.status.success(), "{}", stdout_of(&output));
    assert!(
        stdout_of(&output).contains("BGJOB_STATUS=STARTED STEP=implement-step7a"),
        "{}",
        stdout_of(&output)
    );
}

#[test]
fn step7a_unknown_flag_emits_argv_bail_envelope() {
    let fixture = fixture();
    let output = larch(&fixture.plugin, &fixture.tmpdir)
        .args(["implement", "step-7a", "--not-a-flag"])
        .output()
        .expect("run step-7a");
    assert_eq!(output.status.code(), Some(2));
    let text = stdout_of(&output);
    assert!(text.contains("DIAGRAM_STATUS=failed"), "{text}");
    assert!(text.contains("STEP_7A_BAIL_REASON=argv"), "{text}");
    assert!(text.contains("LOG_CHECKPOINT_STATUS=skip"), "{text}");
    assert!(text.contains("REBASE_OUTCOME=skipped"), "{text}");
}

#[test]
fn step7a_missing_tmpdir_bails_before_work() {
    let fixture = fixture();
    let mut command = AssertCommand::cargo_bin("larch").expect("larch binary");
    command
        .env("CLAUDE_PLUGIN_ROOT", &fixture.plugin)
        .env_remove("IMPLEMENT_TMPDIR")
        .current_dir(&fixture.tmpdir);
    let output = command
        .args(["implement", "step-7a"])
        .output()
        .expect("run step-7a");
    assert_eq!(output.status.code(), Some(2));
    assert!(
        stdout_of(&output).contains("STEP_7A_BAIL_REASON=missing-implement-tmpdir"),
        "{}",
        stdout_of(&output)
    );
}

#[test]
fn step5_review_parent_relays_bgjob_adapter_stdout() {
    let fixture = fixture();
    let output = larch(&fixture.plugin, &fixture.tmpdir)
        .args(["implement", "step-5-review"])
        .output()
        .expect("run step-5-review");
    assert!(output.status.success(), "{}", stdout_of(&output));
    assert!(
        stdout_of(&output).contains("ADAPTER_RELAY=ok"),
        "{}",
        stdout_of(&output)
    );
}

#[test]
fn step5_resume_parent_relays_bgjob_adapter_stdout() {
    let fixture = fixture();
    let output = larch(&fixture.plugin, &fixture.tmpdir)
        .args(["implement", "step-5-resume", "--final-round-num", "2"])
        .output()
        .expect("run step-5-resume");
    assert!(output.status.success(), "{}", stdout_of(&output));
    assert!(
        stdout_of(&output).contains("ADAPTER_RELAY=ok"),
        "{}",
        stdout_of(&output)
    );
}

#[test]
fn step5_resume_non_numeric_round_is_rejected() {
    let fixture = fixture();
    let output = larch(&fixture.plugin, &fixture.tmpdir)
        .args(["implement", "step-5-resume", "--final-round-num", "abc"])
        .output()
        .expect("run step-5-resume");
    assert_eq!(output.status.code(), Some(2));
    assert!(
        String::from_utf8_lossy(&output.stderr).contains("must be numeric"),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
}

#[test]
fn checks_step5_resume_relays_checks_line_then_resume_leg() {
    let fixture = fixture();
    let _repository = seed_session_repo(&fixture.tmpdir);
    let output = larch(&fixture.plugin, &fixture.tmpdir)
        .args([
            "implement",
            "checks-step5-resume",
            "--checks-site",
            "step5-review-fixes",
            "--final-round-num",
            "2",
        ])
        .output()
        .expect("run checks-step5-resume");
    assert!(output.status.success(), "{}", stdout_of(&output));
    let text = stdout_of(&output);
    assert!(
        text.contains("RELEVANT_CHECKS_OK=true SITE=step5-review-fixes"),
        "{text}"
    );
    assert!(text.contains("STEP5_REVIEW_STATUS=stall"), "{text}");
    // The pass path must not fabricate a checks-failed routing action.
    assert!(!text.contains("NEXT_ACTION=checks-failed"), "{text}");
}

#[test]
fn checks_step5_resume_non_numeric_round_is_rejected() {
    let fixture = fixture();
    let output = larch(&fixture.plugin, &fixture.tmpdir)
        .args([
            "implement",
            "checks-step5-resume",
            "--checks-site",
            "step5-review-fixes",
            "--final-round-num",
            "x",
        ])
        .output()
        .expect("run checks-step5-resume");
    assert_eq!(output.status.code(), Some(2));
}

#[test]
fn step6_entry_parent_relays_bgjob_adapter_stdout() {
    let fixture = fixture();
    let _repository = seed_session_repo(&fixture.tmpdir);
    let output = larch(&fixture.plugin, &fixture.tmpdir)
        .args(["implement", "step-6-entry", "--forked-target", "false"])
        .output()
        .expect("run step-6-entry");
    assert!(output.status.success(), "{}", stdout_of(&output));
    assert!(
        stdout_of(&output).contains("ADAPTER_RELAY=ok"),
        "{}",
        stdout_of(&output)
    );
}

#[test]
fn review_verbs_help_actions_exit_zero() {
    let fixture = fixture();
    for verb in [
        "step-5-review",
        "step-5-resume",
        "step-6-entry",
        "checks-step5-resume",
    ] {
        let output = larch(&fixture.plugin, &fixture.tmpdir)
            .args(["implement", verb, "--help"])
            .output()
            .expect("run help");
        assert!(output.status.success(), "{verb} --help exited nonzero");
    }
}
