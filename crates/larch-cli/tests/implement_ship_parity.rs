//! Black-box compatibility coverage for the four Rust-owned Step 8 commands.

use std::{
    fs,
    os::unix::fs::{PermissionsExt as _, symlink},
};

use assert_cmd::Command as AssertCommand;
use tempfile::TempDir;

const PYTHON_STUB: &str = r#"#!/usr/bin/env python3
import os
import json
import pathlib
import sys

tmp = pathlib.Path(os.environ["IMPLEMENT_TMPDIR"])
with (tmp / "python-argv.txt").open("a", encoding="utf-8") as stream:
    stream.write(json.dumps(sys.argv[1:]) + "\n")
if sys.argv[1:3] == ["ship", "seed-initial-state"]:
    print("SEED_RELAY=ok")
elif sys.argv[1:3] == ["ship", "pr"]:
    print(json.dumps({"outcome": "OK", "pr_number": 12, "pr_url": "https://example.test/pr/12"}, sort_keys=True))
else:
    sys.exit(9)
"#;

struct Fixture {
    _root: TempDir,
    plugin: std::path::PathBuf,
    tmpdir: std::path::PathBuf,
}

fn fixture(checkpoint_rc: i32) -> Fixture {
    let root = TempDir::new().expect("temp root");
    let plugin = root.path().join("plugin");
    let tmpdir = root.path().join("tmp");
    fs::create_dir_all(plugin.join("scripts")).expect("scripts");
    fs::create_dir_all(plugin.join("python")).expect("python");
    fs::create_dir_all(&tmpdir).expect("tmpdir");
    let larch = plugin.join("scripts/larch.sh");
    fs::write(&larch, larch_stub(checkpoint_rc)).expect("larch stub");
    fs::write(plugin.join("python/cli.py"), PYTHON_STUB).expect("python stub");
    fs::set_permissions(&larch, fs::Permissions::from_mode(0o755)).expect("chmod larch");
    Fixture {
        _root: root,
        plugin: fs::canonicalize(plugin).expect("canonical plugin"),
        tmpdir: fs::canonicalize(tmpdir).expect("canonical tmpdir"),
    }
}

fn larch_stub(checkpoint_rc: i32) -> String {
    format!(
        r#"#!/usr/bin/env python3
import json
import os
import pathlib
import sys

args = sys.argv[1:]
tmp = pathlib.Path(os.environ.get("IMPLEMENT_TMPDIR", "."))
with (tmp / "larch-argv.txt").open("a", encoding="utf-8") as stream:
    stream.write(" ".join(args) + "\n")
if args[:2] == ["bgjob", "adapt"]:
    print("ADAPTER_RELAY=ok")
elif args[:2] == ["git", "phantom-probe"]:
    print("PHANTOM_STATUS=clean")
elif args[:2] == ["oos", "disposition-checkpoint"]:
    if {checkpoint_rc}:
        print("checkpoint failed", file=sys.stderr)
        sys.exit({checkpoint_rc})
elif args[:2] == ["run-log", "manifest"]:
    log_root = pathlib.Path(args[args.index("--log-root") + 1])
    run_id = args[args.index("--run-id") + 1]
    path = log_root / "implement" / run_id / "manifest.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc.setdefault("steps_ran", {{}})["step9a1"] = args[-1].endswith("=true")
    path.write_text(json.dumps(doc) + "\n", encoding="utf-8")
sys.exit(0)
"#
    )
}

fn command(fixture: &Fixture) -> AssertCommand {
    let mut command = AssertCommand::cargo_bin("larch").expect("larch binary");
    command
        .env("CLAUDE_PLUGIN_ROOT", &fixture.plugin)
        .env("IMPLEMENT_TMPDIR", &fixture.tmpdir)
        .env("PWD", &fixture.tmpdir)
        .current_dir(&fixture.tmpdir);
    command
}

fn stdout(output: &std::process::Output) -> String {
    String::from_utf8_lossy(&output.stdout).into_owned()
}

fn stderr(output: &std::process::Output) -> String {
    String::from_utf8_lossy(&output.stderr).into_owned()
}

fn python_argv(fixture: &Fixture) -> Vec<Vec<String>> {
    fs::read_to_string(fixture.tmpdir.join("python-argv.txt"))
        .expect("python argv")
        .lines()
        .map(|line| serde_json::from_str(line).expect("argv JSON"))
        .collect()
}

fn strings(values: &[&str]) -> Vec<String> {
    values.iter().map(|value| (*value).to_owned()).collect()
}

fn oos_checkpoint(fixture: &Fixture) -> std::process::Output {
    command(fixture)
        .args(["implement", "step-8-oos-checkpoint"])
        .output()
        .expect("checkpoint")
}

#[test]
fn python_guard_accepts_current_python_without_output() {
    let fixture = fixture(0);
    let output = command(&fixture)
        .args(["implement", "step-8-python-guard"])
        .output()
        .expect("guard");
    assert!(output.status.success());
    assert_eq!(stdout(&output), "");
    assert_eq!(stderr(&output), "");
}

#[test]
fn python_guard_failure_preserves_json_stall_contract() {
    let fixture = fixture(0);
    let fake_path = fixture.tmpdir.join("fake-bin");
    fs::create_dir_all(&fake_path).expect("fake bin");
    let python = fake_path.join("python3");
    fs::write(&python, "#!/bin/sh\nexit 1\n").expect("fake python");
    fs::set_permissions(&python, fs::Permissions::from_mode(0o755)).expect("chmod python");
    let output = command(&fixture)
        .env("PATH", &fake_path)
        .args(["implement", "step-8-python-guard"])
        .output()
        .expect("guard");
    assert_eq!(output.status.code(), Some(4));
    assert_eq!(
        stderr(&output),
        "ERROR: Python ship driver requires Python 3.11 or newer\n"
    );
    assert_eq!(
        stdout(&output),
        "{\"detail\":\"Python ship driver requires Python 3.11 or newer\",\"failed_run_id\":\"\",\"ledger_dispatcher\":\"\",\"ledger_exit_code\":null,\"ledger_failure_detail_log\":\"\",\"ledger_phase\":\"\",\"ledger_ready\":false,\"ledger_site\":\"\",\"ledger_step\":\"\",\"ledger_trigger\":\"\",\"merge_result\":\"\",\"needs_user_reason\":\"\",\"outcome\":\"STALLED\",\"pr_number\":null,\"pr_url\":\"\"}\n"
    );
}

#[test]
fn seed_initial_resolves_durable_inputs_and_writes_in_process() {
    let fixture = fixture(0);
    fs::write(
        fixture.tmpdir.join("bootstrap-routing.env"),
        "coder=codex\nBRANCH_NAME=feature/ship\nISSUE_NUMBER=8624\nRUN_ID=run-8\nREPO=owner/repo\n",
    )
    .expect("bootstrap");
    fs::write(
        fixture.tmpdir.join("ship-seed-input.env"),
        "MERGE=true\nDRAFT=false\n",
    )
    .expect("seed");
    fs::write(fixture.tmpdir.join("session-id"), "session-8\n").expect("session");
    let output = command(&fixture)
        .args(["implement", "step-8-seed-initial"])
        .output()
        .expect("seed");
    assert!(output.status.success(), "{}", stderr(&output));
    assert_eq!(stdout(&output), "");
    assert!(!fixture.tmpdir.join("python-argv.txt").exists());
    let state = fs::read_to_string(fixture.tmpdir.join("ship-pr-state.sh")).expect("state");
    assert!(state.starts_with("PHASE=checks\nBRANCH_NAME=feature/ship\nISSUE_NUMBER=8624\n"));
    assert!(state.contains("TOOL_LABEL=Codex\n"));
    assert!(state.contains("EXPECTED_SESSION_ID=session-8\n"));
    assert!(state.contains("EXPECTED_TMPDIR_BASENAME_PREFIX=claude-implement-tmp-\n"));
    assert!(state.ends_with("MAIN_HEALTH_HEAD_SHA=\n"));
}

#[test]
fn ship_parent_replaces_completed_bgjob_result() {
    let fixture = fixture(0);
    fs::write(fixture.tmpdir.join("session-id"), "run-8\n").expect("session");
    let output = command(&fixture)
        .args(["implement", "step-8-ship"])
        .output()
        .expect("ship parent");
    assert!(output.status.success(), "{}", stderr(&output));
    assert_eq!(stdout(&output), "ADAPTER_RELAY=ok\n");
    let argv = fs::read_to_string(fixture.tmpdir.join("larch-argv.txt")).expect("argv");
    assert!(
        argv.contains("bgjob adapt --step implement-step8-ship"),
        "{argv}"
    );
    assert!(argv.contains("--replace-completed-result --"), "{argv}");
    assert!(argv.contains("implement step-8-ship"), "{argv}");
}

#[test]
fn ship_child_runs_guard_probe_and_canonical_python_driver() {
    let fixture = fixture(0);
    fs::write(
        fixture.tmpdir.join("ship-pr-state.sh"),
        "BRANCH_NAME=feature/ship\nISSUE_NUMBER=8624\nRUN_ID=run-8\nREPO=owner/repo\nMERGE=true\nDRAFT=false\n",
    )
    .expect("state");
    let merge = fixture.tmpdir.join("bgjob/ship.merge.env");
    fs::create_dir_all(merge.parent().expect("parent")).expect("bgjob");
    let output = command(&fixture)
        .args([
            "implement",
            "step-8-ship",
            "--bgjob-child",
            "--merge-result-env",
            merge.to_str().expect("utf8"),
        ])
        .output()
        .expect("ship child");
    assert!(output.status.success(), "{}", stderr(&output));
    assert_eq!(
        stdout(&output),
        "{\"outcome\": \"OK\", \"pr_number\": 12, \"pr_url\": \"https://example.test/pr/12\"}\n"
    );
    assert!(stderr(&output).contains("→ phantom-probe: 8-pre-ship"));
    assert!(stderr(&output).contains("PHANTOM_STATUS="));
    assert!(!fixture.tmpdir.join("larch-argv.txt").exists());
    let tmpdir = fixture.tmpdir.display().to_string();
    let state = fixture
        .tmpdir
        .join("ship-pr-state.sh")
        .display()
        .to_string();
    #[rustfmt::skip]
    let expected = strings(&[
        "ship", "pr",
        "--branch", "feature/ship",
        "--issue", "8624",
        "--repo", "owner/repo",
        "--run-id", "run-8",
        "--tmpdir", &tmpdir,
        "--manifest-path", "",
        "--state-file", &state,
        "--tool-label", "claude",
        "--merge", "true",
        "--draft", "false",
        "--forked", "false",
        "--repo-unavailable", "false",
        "--no-admin-fallback", "false",
        "--no-logs-commit", "false",
        "--expected-session-id", "",
        "--expected-tmpdir-basename-prefix", "claude-implement-tmp-",
    ]);
    assert_eq!(python_argv(&fixture), vec![expected]);
    let result_env = fs::read_to_string(&merge).expect("Rust result env");
    assert!(
        result_env.starts_with("outcome=OK\nNEEDS_USER_REASON=\nFAILED_RUN_ID=\nPR_NUMBER=12\n")
    );
    assert!(result_env.contains("PR_URL=https://example.test/pr/12\n"));
    assert!(
        result_env.ends_with("CI_ERRORS_FILE=\nFAILED_JOBS_COUNT=0\nCI_ERRORS_DISTILL_CLASS=\n")
    );
}

#[test]
fn oos_checkpoint_success_persists_all_post_pass_effects() {
    let fixture = fixture(0);
    fs::write(
        fixture.tmpdir.join("ship-pr-state.sh"),
        "PHASE=ci-initial\nRUN_ID=run-8\nPR_NUMBER=12\nOOS_PENDING=true\n",
    )
    .expect("state");
    fs::write(fixture.tmpdir.join("ship-pr-state.sh.tmp"), "stale\n").expect("stale temp");
    fs::write(fixture.tmpdir.join("session-id"), "session-run\n").expect("session");
    let run = fixture.tmpdir.join("larch-logs/implement/run-8");
    fs::create_dir_all(&run).expect("run");
    fs::write(run.join("manifest.json"), "{\"steps_ran\":{}}\n").expect("manifest");
    fs::write(
        run.join("oos-issues.ndjson"),
        "{\"body\":\"Filed URL: https://github.com/owner/repo/issues/1\"}\n",
    )
    .expect("ndjson");
    fs::create_dir_all(fixture.tmpdir.join("larch-logs/implement/session-run"))
        .expect("session run");
    let output = oos_checkpoint(&fixture);
    assert!(output.status.success(), "{}", stderr(&output));
    assert_eq!(stdout(&output), "OOS_CHECKPOINT_RC=0\nNEXT_ACTION=reship\n");
    assert_eq!(
        fs::read_to_string(run.join("run-statistics.md")).expect("statistics"),
        "Run run-8: 1 OOS issue(s) filed.\n"
    );
    assert!(
        !fixture
            .tmpdir
            .join("larch-logs/implement/session-run/run-statistics.md")
            .exists()
    );
    let state = fs::read_to_string(fixture.tmpdir.join("ship-pr-state.sh")).expect("state");
    assert!(state.contains("PR_NUMBER=12\n"));
    assert!(state.contains("OOS_PENDING=false\n"));
    assert_eq!(
        fs::read_to_string(fixture.tmpdir.join("ship-pr-state.sh.tmp")).expect("stale temp"),
        "stale\n"
    );
    let manifest = fs::read_to_string(run.join("manifest.json")).expect("manifest");
    assert!(manifest.contains("\"step9a1\": true"), "{manifest}");
    let calls = fs::read_to_string(fixture.tmpdir.join("larch-argv.txt")).expect("larch argv");
    assert_eq!(
        calls,
        format!(
            "oos disposition-checkpoint --implement-tmpdir {tmp}\nrun-log manifest --log-root {logs} --skill implement --run-id run-8 --field steps_ran.step9a1=true\nexecution-issues refresh --implement-tmpdir {tmp} --best-effort\n",
            tmp = fixture.tmpdir.display(),
            logs = fixture.tmpdir.join("larch-logs").display(),
        )
    );
}

#[test]
fn oos_checkpoint_nonzero_maps_to_stall_and_preserves_state() {
    let fixture = fixture(1);
    fs::write(
        fixture.tmpdir.join("ship-pr-state.sh"),
        "RUN_ID=run-8\nOOS_PENDING=true\n",
    )
    .expect("state");
    let output = oos_checkpoint(&fixture);
    assert!(output.status.success());
    assert_eq!(stdout(&output), "OOS_CHECKPOINT_RC=1\nNEXT_ACTION=stall\n");
    assert!(
        fs::read_to_string(fixture.tmpdir.join("ship-pr-state.sh"))
            .expect("state")
            .contains("OOS_PENDING=true")
    );
    assert_eq!(
        fs::read_to_string(fixture.tmpdir.join("oos-disposition-checkpoint.stderr.log"))
            .expect("stderr log"),
        "checkpoint failed\n"
    );
}

#[test]
fn oos_checkpoint_refuses_symlinked_diagnostic_log() {
    let fixture = fixture(1);
    let outside = fixture.tmpdir.parent().expect("parent").join("outside.log");
    fs::write(&outside, "existing\n").expect("outside");
    symlink(
        &outside,
        fixture.tmpdir.join("oos-disposition-checkpoint.stderr.log"),
    )
    .expect("diagnostic symlink");
    let output = oos_checkpoint(&fixture);
    assert!(output.status.success());
    assert_eq!(stdout(&output), "OOS_CHECKPOINT_RC=1\nNEXT_ACTION=stall\n");
    assert!(stderr(&output).contains("refusing unsafe stderr log"));
    assert_eq!(fs::read_to_string(outside).expect("outside"), "existing\n");
    let calls = fs::read_to_string(fixture.tmpdir.join("larch-argv.txt")).expect("calls");
    assert!(!calls.contains("run-log append-failure"), "{calls}");
}

#[test]
fn oos_checkpoint_launch_failure_emits_no_routing_contract() {
    let fixture = fixture(0);
    fs::remove_file(fixture.plugin.join("scripts/larch.sh")).expect("remove larch stub");
    let output = oos_checkpoint(&fixture);
    assert_eq!(output.status.code(), Some(1));
    assert_eq!(stdout(&output), "");
    assert!(!stderr(&output).is_empty());
}

#[test]
fn oos_checkpoint_patch_failure_rolls_back_manifest_and_statistics() {
    let fixture = fixture(0);
    fs::write(
        fixture.tmpdir.join("ship-pr-state.sh"),
        "RUN_ID=run-8\nPR_URL=https://\nOOS_PENDING=true\n",
    )
    .expect("state");
    let run = fixture.tmpdir.join("larch-logs/implement/run-8");
    fs::create_dir_all(&run).expect("run");
    fs::write(run.join("manifest.json"), "{\"steps_ran\":{}}\n").expect("manifest");
    let output = oos_checkpoint(&fixture);
    assert!(output.status.success());
    assert_eq!(stdout(&output), "OOS_CHECKPOINT_RC=2\nNEXT_ACTION=stall\n");
    assert!(stderr(&output).contains("invalid ship state PR_URL"));
    assert!(!run.join("run-statistics.md").exists());
    assert!(
        fs::read_to_string(fixture.tmpdir.join("ship-pr-state.sh"))
            .expect("state")
            .contains("OOS_PENDING=true")
    );
    let manifest = fs::read_to_string(run.join("manifest.json")).expect("manifest");
    assert!(manifest.contains("\"step9a1\": false"), "{manifest}");
}

#[test]
fn oos_checkpoint_stats_failure_preserves_unmodified_manifest() {
    let fixture = fixture(0);
    fs::write(
        fixture.tmpdir.join("ship-pr-state.sh"),
        "RUN_ID=run-8\nOOS_PENDING=true\n",
    )
    .expect("state");
    let run = fixture.tmpdir.join("larch-logs/implement/run-8");
    fs::create_dir_all(run.join("run-statistics.md")).expect("blocking statistics directory");
    fs::write(
        run.join("manifest.json"),
        "{\"steps_ran\":{\"step9a1\":true}}\n",
    )
    .expect("manifest");
    let output = oos_checkpoint(&fixture);
    assert!(output.status.success());
    assert_eq!(stdout(&output), "OOS_CHECKPOINT_RC=2\nNEXT_ACTION=stall\n");
    let manifest = fs::read_to_string(run.join("manifest.json")).expect("manifest");
    assert!(manifest.contains("\"step9a1\":true"), "{manifest}");
    let calls = fs::read_to_string(fixture.tmpdir.join("larch-argv.txt")).expect("calls");
    assert!(!calls.contains("run-log manifest"), "{calls}");
}

#[test]
fn oos_checkpoint_resolves_the_single_run_batch_without_persisted_identity() {
    let fixture = fixture(0);
    fs::write(
        fixture.tmpdir.join("ship-pr-state.sh"),
        "PR_NUMBER=12\nOOS_PENDING=true\n",
    )
    .expect("state");
    let run = fixture.tmpdir.join("larch-logs/implement/discovered-run");
    fs::create_dir_all(&run).expect("run");
    fs::write(run.join("manifest.json"), "{\"steps_ran\":{}}\n").expect("manifest");
    fs::write(
        run.join("oos-issues.ndjson"),
        "{\"body\":\"Filed URL: https://github.com/owner/repo/issues/9\"}\n",
    )
    .expect("ndjson");
    let output = oos_checkpoint(&fixture);
    assert!(output.status.success(), "{}", stderr(&output));
    assert_eq!(stdout(&output), "OOS_CHECKPOINT_RC=0\nNEXT_ACTION=reship\n");
    assert_eq!(
        fs::read_to_string(run.join("run-statistics.md")).expect("statistics"),
        "Run discovered-run: 1 OOS issue(s) filed.\n"
    );
}

#[test]
fn all_step8_help_actions_match_argparse() {
    let fixture = fixture(0);
    for (verb, expected) in [
        (
            "step-8-python-guard",
            "usage: cli.py implement step-8-python-guard [-h]\n\noptions:\n  -h, --help  show this help message and exit\n",
        ),
        (
            "step-8-seed-initial",
            "usage: cli.py implement step-8-seed-initial [-h] [--merge MERGE]\n                                            [--draft DRAFT]\n                                            [--no-admin-fallback NO_ADMIN_FALLBACK]\n                                            [--no-logs-commit NO_LOGS_COMMIT]\n                                            [--manifest-path MANIFEST_PATH]\n                                            [--tool-label TOOL_LABEL]\n                                            [--stall-tracking STALL_TRACKING]\n                                            [--stall-step STALL_STEP]\n                                            [--bail-reason BAIL_REASON]\n                                            [--bail-failure-detail-log BAIL_FAILURE_DETAIL_LOG]\n\noptions:\n  -h, --help            show this help message and exit\n  --merge MERGE\n  --draft DRAFT\n  --no-admin-fallback NO_ADMIN_FALLBACK\n  --no-logs-commit NO_LOGS_COMMIT\n  --manifest-path MANIFEST_PATH\n  --tool-label TOOL_LABEL\n  --stall-tracking STALL_TRACKING\n  --stall-step STALL_STEP\n  --bail-reason BAIL_REASON\n  --bail-failure-detail-log BAIL_FAILURE_DETAIL_LOG\n",
        ),
        (
            "step-8-ship",
            "usage: cli.py implement step-8-ship [-h] [--bgjob-child]\n                                    [--merge-result-env MERGE_RESULT_ENV]\n\noptions:\n  -h, --help            show this help message and exit\n  --bgjob-child\n  --merge-result-env MERGE_RESULT_ENV\n",
        ),
        (
            "step-8-oos-checkpoint",
            "usage: cli.py implement step-8-oos-checkpoint [-h]\n\noptions:\n  -h, --help  show this help message and exit\n",
        ),
    ] {
        let output = command(&fixture)
            .args(["implement", verb, "--help"])
            .output()
            .expect("help");
        assert!(output.status.success(), "{verb}: {}", stderr(&output));
        assert_eq!(stdout(&output), expected, "{verb}");
        assert_eq!(stderr(&output), "", "{verb}");
    }
}

#[test]
fn seed_refuses_to_overwrite_existing_shell_state() {
    let fixture = fixture(0);
    fs::write(fixture.tmpdir.join("ship-pr-state.sh"), "PHASE=checks\n").expect("state");
    let output = command(&fixture)
        .args(["implement", "step-8-seed-initial"])
        .output()
        .expect("seed");
    assert_eq!(output.status.code(), Some(2));
    assert!(stderr(&output).contains("create-if-absent only"));
    assert!(!fixture.tmpdir.join("python-argv.txt").exists());
}
