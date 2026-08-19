//! Black-box parity for the migrated Step 18, Step 19, and checks identity
//! commands.
//!
//! Each case runs the real `larch` executable against a temporary plugin root
//! whose `scripts/larch.sh` is a stub that records its argv and answers with
//! canned rows, so the sibling-verb boundary, the wire files, and the exit
//! codes are exercised without a live session. The stub reads its configuration
//! from the implement tmpdir because the shared process policy publishes only
//! an allowlisted child environment.

#![cfg(unix)]

use std::{
    fs,
    os::unix::fs::PermissionsExt as _,
    path::{Path, PathBuf},
    process::{Command, Output},
};

use tempfile::TempDir;

const STUB_CLI: &str = r##"#!/usr/bin/env python3
import os
import sys
from pathlib import Path

TMP = Path(os.environ["IMPLEMENT_TMPDIR"])


def config(key: str, default: str) -> str:
    path = TMP / "stub-config.env"
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith(key + "="):
                return line.split("=", 1)[1]
    except OSError:
        pass
    return default


def log(message: str) -> None:
    with open(TMP / "stub-argv.log", "a", encoding="utf-8") as handle:
        handle.write(message + "\n")


def step18b(args):
    tmp = Path(args[args.index("--implement-tmpdir") + 1])
    sentinel = "true" if (tmp / ".step17-emitted").exists() else "false"
    log(f"step18b sentinel={sentinel} argv={' '.join(sys.argv[1:])}")
    summary = tmp / "summary-final.md"
    if config("WRITE_SUMMARY", "true") == "true":
        body = config("BODY", "# Final body").replace("\\n", "\n")
        summary.write_text(body, encoding="utf-8")
    if config("SUMMARY_UNREADABLE", "false") == "true" and summary.is_file():
        os.chmod(summary, 0o000)
    print("EMIT_BODY=" + config("EMIT_BODY", "true"))
    rc = int(config("WFR_RC", "0"))
    print(f"WFR_RC={rc}")
    print(f"STEP17_EMITTED_PRESENT={sentinel}")
    print("SNAPSHOT_OK=true")
    return rc


def prepare(args):
    log("prepare-terminal-snapshot " + " ".join(args))
    rc = int(config("SNAPSHOT_RC", "0"))
    if rc != 0:
        print("SESSION_TRANSCRIPT_STATUS=failed")
        print("TERMINAL_SNAPSHOT_STATUS=failed")
        return rc
    print("SESSION_TRANSCRIPT_STATUS=captured")
    print("TERMINAL_SNAPSHOT_STATUS=prepared")
    print("TERMINAL_SNAPSHOT_ERROR=")
    return 0


def lifecycle(verb, args):
    log("run-log " + verb + " " + " ".join(args))
    rc = int(config("PUBLISH_RC", "0"))
    if rc != 0:
        print("publication failed: stub upload failure", file=sys.stderr)
        return rc
    if config("STORAGE_DISABLED", "false") == "true":
        print("RUN_LOG_PUBLICATION=skipped-disabled")
        print("LIFECYCLE_FLUSHED=false")
        print("LIFECYCLE_TERMINALIZED=true")
        return 0
    cache = TMP / "published-cache"
    cache.mkdir(parents=True, exist_ok=True)
    print("REMOTE_KEY=run-logs/implement/RUN1.tar.gz")
    print(f"CACHE_DIR={cache}")
    print("RUN_LOG_PUBLICATION=published")
    print("LIFECYCLE_FLUSHED=true")
    print("LIFECYCLE_TERMINALIZED=true")
    return 0


def teardown(args):
    tmp = Path(args[args.index("--implement-tmpdir") + 1])
    state = args[args.index("--state-file") + 1]
    if Path(state) != (tmp / "finalize-state.sh"):
        print(f"bad state file {state}", file=sys.stderr)
        return 9
    marker = "before" if (tmp / ".step17-emitted").exists() else "missing"
    log(f"teardown sentinel={marker} argv={' '.join(sys.argv[1:])}")
    print("ISSUE_URL=https://example.test/issues/1")
    print("RENAME_BRANCH=skipped")
    print("RENAME_STATUS=ok")
    print("STASH_REF=refs/stash/test")
    print("SENTINEL_WRITTEN=true")
    print("FINALIZE_SUBCOMMAND=teardown")
    print("FINALIZE_WARNINGS=none")
    return 0


def normalize(args):
    log("normalize-outcome " + " ".join(args))
    print("IMPLEMENT_NORMALIZED_OUTCOME=" + config("OUTCOME", "shipped"))
    print("IMPLEMENT_PR_NUMBER=" + config("PR_NUMBER", "42"))
    return 0


def main() -> int:
    args = sys.argv[1:]
    head = args[:2]
    if head == ["final-report", "step18b"]:
        return step18b(args[2:])
    if head == ["run-log", "append-failure"]:
        log("append-failure " + " ".join(args[2:]))
        return 0
    if head == ["run-log", "prepare-terminal-snapshot"]:
        return prepare(args[2:])
    if len(args) >= 2 and args[0] == "run-log" and args[1].startswith("lifecycle-"):
        return lifecycle(args[1], args[2:])
    if head in (["token", "report"], ["timing", "report"]):
        log(" ".join(head))
        return 0
    if head in (["token", "mark"], ["timing", "mark"]):
        log(" ".join(head) + " " + " ".join(args[2:]))
        return 0
    if head == ["stall-recovery", "normalize-outcome"]:
        return normalize(args[2:])
    if head == ["session", "restore-finalize-state"]:
        log("restore-finalize-state " + " ".join(args[2:]))
        return int(config("RESTORE_RC", "0"))
    if head == ["session", "clear-implement-pointer"]:
        log("clear-implement-pointer " + " ".join(args[2:]))
        return 0
    if head == ["implement-finalize", "teardown"]:
        return teardown(args[2:])
    print("unexpected argv: " + " ".join(args), file=sys.stderr)
    return 8


if __name__ == "__main__":
    raise SystemExit(main())
"##;

struct Fixture {
    _temp: TempDir,
    plugin: PathBuf,
    cache: PathBuf,
    tmpdir: PathBuf,
    repo: PathBuf,
}

fn write_executable(path: &Path, body: &str) {
    fs::create_dir_all(path.parent().expect("parent")).expect("create parent");
    fs::write(path, body).expect("write fixture");
    fs::set_permissions(path, fs::Permissions::from_mode(0o755)).expect("executable fixture");
}

fn fixture() -> Fixture {
    let temp = TempDir::new().expect("temp");
    // Canonicalize so the trusted-directory probes never see a `/var` symlink.
    let root = fs::canonicalize(temp.path()).expect("canonical temp root");
    let plugin = root.join("plugin");
    write_executable(&plugin.join("python").join("cli.py"), STUB_CLI);
    write_executable(
        &plugin.join("scripts").join("larch.sh"),
        &format!(
            "#!/usr/bin/env bash\nexec python3 \"{}\" \"$@\"\n",
            plugin.join("python").join("cli.py").display()
        ),
    );
    let repo = root.join("repo");
    fs::create_dir_all(&repo).expect("repo");
    // The self-edit-log verb only accepts a session directory under the larch
    // session cache, so the fixture publishes its own `XDG_CACHE_HOME`.
    let cache = root.join("cache");
    let tmpdir = cache
        .join("larch")
        .join("sessions")
        .join("claude-implement-parity");
    fs::create_dir_all(&tmpdir).expect("tmpdir");
    fs::write(
        tmpdir.join("session-env.sh"),
        format!("LARCH_RUN_ID=RUN1\nREPO_ROOT={}\nSTALL_TRACKING=false\n", repo.display()),
    )
    .expect("session env");
    fs::write(
        tmpdir.join("ship-pr-state.sh"),
        "STALL_TRACKING=false\nBAIL_NEEDS_USER_INPUT=false\nSTALL_STEP=\n",
    )
    .expect("ship state");
    fs::write(
        tmpdir.join("finalize-state.sh"),
        "STALL_TRACKING=false\nSTALL_STEP=\n",
    )
    .expect("finalize state");
    Fixture {
        _temp: temp,
        plugin,
        cache,
        tmpdir,
        repo,
    }
}

impl Fixture {
    fn configure(&self, rows: &[(&str, &str)]) {
        let mut text = String::new();
        for (key, value) in rows {
            text.push_str(key);
            text.push('=');
            text.push_str(value);
            text.push('\n');
        }
        fs::write(self.tmpdir.join("stub-config.env"), text).expect("stub config");
    }

    fn write_state(&self, name: &str, body: &str) {
        fs::write(self.tmpdir.join(name), body).expect("state file");
    }

    fn run(&self, arguments: &[&str]) -> Output {
        Command::new(env!("CARGO_BIN_EXE_larch"))
            .current_dir(&self.repo)
            .env("CLAUDE_PLUGIN_ROOT", &self.plugin)
            .env("IMPLEMENT_TMPDIR", &self.tmpdir)
            .env("XDG_CACHE_HOME", &self.cache)
            .env_remove("RUN_ID")
            .env_remove("STALL_TRACKING")
            .env_remove("LARCH_CLAUDE_PID")
            .args(arguments)
            .output()
            .expect("run larch")
    }

    fn log(&self) -> String {
        fs::read_to_string(self.tmpdir.join("stub-argv.log")).unwrap_or_default()
    }
}

fn stdout(output: &Output) -> String {
    String::from_utf8_lossy(&output.stdout).into_owned()
}

fn stderr(output: &Output) -> String {
    String::from_utf8_lossy(&output.stderr).into_owned()
}

fn code(output: &Output) -> i32 {
    output.status.code().expect("exit code")
}

fn count(needle: &str, text: &str) -> usize {
    text.lines().filter(|line| line.contains(needle)).count()
}

fn kv(key: &str, text: &str) -> String {
    let prefix = format!("{key}=");
    text.lines()
        .find_map(|line| line.strip_prefix(prefix.as_str()))
        .unwrap_or_default()
        .to_owned()
}

fn line_of(needle: &str, text: &str) -> Option<usize> {
    text.lines().position(|line| line.contains(needle))
}

// ---------------------------------------------------------------------------
// Step 18 gate
// ---------------------------------------------------------------------------

#[test]
fn step18_gate_clear_emits_every_layer_and_the_breadcrumb() {
    let fixture = fixture();
    let output = fixture.run(&[
        "implement",
        "step-18",
        "--phase",
        "gate",
        "--stall-tracking-memory",
        "false",
    ]);
    assert_eq!(code(&output), 0, "{}", stderr(&output));
    let text = stdout(&output);
    for key in [
        "STALL_TRACKING_MEMORY",
        "STALL_TRACKING_DISK",
        "STALL_TRACKING_FINALIZE",
        "STALL_TRACKING_SESSION",
    ] {
        assert_eq!(kv(key, &text), "false", "{key} in {text}");
    }
    assert_eq!(kv("STALL_RECOVERY_REQUIRED", &text), "false");
    assert!(text.contains("⏩ 18a: stall recovery; no stall detected"));
    assert!(
        !text.contains("STALL_TRACKING_ABANDONED_MARKER"),
        "only the composite emits the abandoned-marker layer"
    );
    assert!(fixture.log().is_empty(), "the gate runs no sibling verb");
}

#[test]
fn step18_gate_reports_a_disk_stall() {
    let fixture = fixture();
    fixture.write_state("ship-pr-state.sh", "STALL_TRACKING=maybe\n");
    let output = fixture.run(&["implement", "step-18", "--phase", "gate"]);
    assert_eq!(code(&output), 0);
    let text = stdout(&output);
    assert_eq!(kv("STALL_TRACKING_DISK", &text), "maybe");
    assert_eq!(kv("STALL_RECOVERY_REQUIRED", &text), "true");
    assert!(fixture.log().is_empty());
}

#[test]
fn step18_gate_predicate_matches_python_truthiness() {
    for (value, expected) in [
        ("", "false"),
        ("false", "false"),
        ("true", "true"),
        ("1", "true"),
        ("yes", "true"),
        ("arbitrary", "true"),
    ] {
        let fixture = fixture();
        let output = fixture.run(&[
            "implement",
            "step-18",
            "--phase",
            "gate",
            "--stall-tracking-memory",
            value,
        ]);
        assert_eq!(code(&output), 0);
        assert_eq!(
            kv("STALL_RECOVERY_REQUIRED", &stdout(&output)),
            expected,
            "predicate for {value:?}"
        );
    }
}

// ---------------------------------------------------------------------------
// Step 18 logs flush
// ---------------------------------------------------------------------------

#[test]
fn step18_logs_flush_publishes_and_emits_one_marker_pair() {
    let fixture = fixture();
    fixture.configure(&[("BODY", "## /implement run RUN1: shipped\\n\\n# Final body")]);
    let output = fixture.run(&[
        "implement",
        "step-18",
        "--phase",
        "logs-flush",
        "--step17-emitted",
        "false",
    ]);
    assert_eq!(code(&output), 0, "{}", stderr(&output));
    let text = stdout(&output);
    assert_eq!(kv("RUN_LOG_FINAL_FLUSH_OK", &text), "true");
    assert_eq!(kv("RUN_LOG_PUBLISH_OK", &text), "true");
    assert_eq!(kv("SESSION_TRANSCRIPT_STATUS", &text), "captured");
    assert_eq!(count("---LARCH-SUMMARY-FINAL-BEGIN---", &text), 1);
    assert_eq!(count("---LARCH-SUMMARY-FINAL-END---", &text), 1);
    assert_eq!(count("# Final body", &text), 1, "no duplicate raw body");
    assert!(!text.contains("STALL_RECOVERY_REQUIRED"));
    assert_eq!(
        fs::read_to_string(fixture.tmpdir.join(".run-log-terminalized")).expect("record"),
        "RUN_LOG_TERMINALIZED=true\nRUN_LOG_PUBLICATION=published\nLIFECYCLE_TERMINALIZED=true\n"
    );
    assert!(fixture.tmpdir.join(".step17-emitted").is_file());
    let log = fixture.log();
    assert!(log.contains("step18b sentinel=false argv=final-report step18b --implement-tmpdir"));
    assert!(log.contains("--step17-emitted false"));
    assert!(log.contains("--run-id RUN1 --no-logs-commit false"));
    assert!(log.contains("token mark Step 18 — logs flush"));
    assert!(!log.contains("teardown sentinel="));
    assert!(
        line_of("prepare-terminal-snapshot", &log) < line_of("run-log lifecycle-", &log),
        "{log}"
    );
    assert!(log.contains("run-log lifecycle-finalize"));
}

#[test]
fn step18_accepts_disabled_terminalization_without_remote_fields() {
    let fixture = fixture();
    fixture.configure(&[("STORAGE_DISABLED", "true")]);
    let output = fixture.run(&["implement", "step-18", "--phase", "logs-flush"]);
    assert_eq!(code(&output), 0, "{}", stderr(&output));
    let text = stdout(&output);
    assert_eq!(kv("RUN_LOG_PUBLICATION", &text), "skipped-disabled");
    assert_eq!(kv("LIFECYCLE_FLUSHED", &text), "false");
    assert_eq!(kv("LIFECYCLE_TERMINALIZED", &text), "true");
    assert_eq!(kv("RUN_LOG_PUBLISH_OK", &text), "true");
    assert!(!text.contains("REMOTE_KEY="));
    assert!(!text.contains("CACHE_DIR="));
    assert!(!stderr(&output).contains("durable pending state"));
}

#[test]
fn step18_terminal_log_failure_preserves_the_session() {
    for (key, rc, status, message, published) in [
        (
            "PUBLISH_RC",
            9,
            "RUN_LOG_PUBLISH_OK",
            "durable pending state",
            true,
        ),
        (
            "SNAPSHOT_RC",
            7,
            "RUN_LOG_FINAL_FLUSH_OK",
            "terminal snapshot preparation failed",
            false,
        ),
    ] {
        let fixture = fixture();
        fixture.configure(&[(key, &rc.to_string())]);
        let output = fixture.run(&["implement", "step-18", "--phase", "logs-flush"]);
        assert_eq!(code(&output), rc, "{key}: {}", stderr(&output));
        let text = stdout(&output);
        assert_eq!(kv(status, &text), "false");
        assert!(!text.contains("---LARCH-SUMMARY-FINAL-BEGIN---"));
        assert!(stderr(&output).contains(message), "{}", stderr(&output));
        let log = fixture.log();
        assert_eq!(log.contains("run-log lifecycle-"), published, "{log}");
        assert!(log.contains("prepare-terminal-snapshot"));
        assert!(!log.contains("teardown"));
        assert!(fixture.tmpdir.is_dir());
    }
}

#[test]
fn step18_no_logs_commit_skips_archive_publication() {
    let fixture = fixture();
    fixture.write_state("run-flags.sh", "NO_LOGS_COMMIT=true\n");
    fixture.configure(&[("EMIT_BODY", "false")]);
    let output = fixture.run(&["implement", "step-18", "--phase", "logs-flush"]);
    assert_eq!(code(&output), 0, "{}", stderr(&output));
    let text = stdout(&output);
    assert_eq!(kv("RUN_LOG_PUBLISH_SKIPPED", &text), "no-logs-commit");
    let log = fixture.log();
    assert!(log.contains("--run-id RUN1 --no-logs-commit true"));
    assert!(!log.contains("run-log lifecycle-"));
    assert_eq!(
        fs::read_to_string(fixture.tmpdir.join(".run-log-terminalized")).expect("record"),
        "RUN_LOG_TERMINALIZED=true\nRUN_LOG_PUBLICATION=skipped-suppressed\nLIFECYCLE_TERMINALIZED=true\n"
    );
}

#[test]
fn step18_step17_present_suppresses_the_body() {
    let fixture = fixture();
    fixture.configure(&[("EMIT_BODY", "false")]);
    let output = fixture.run(&[
        "implement",
        "step-18",
        "--phase",
        "logs-flush",
        "--step17-emitted",
        "true",
    ]);
    assert_eq!(code(&output), 0, "{}", stderr(&output));
    let text = stdout(&output);
    assert_eq!(kv("EMIT_BODY", &text), "false");
    assert_eq!(count("---LARCH-SUMMARY-FINAL-BEGIN---", &text), 0);
    let log = fixture.log();
    assert!(log.contains("step18b sentinel=true"));
    assert!(log.contains("--step17-emitted true"));
}

#[test]
fn step18_relays_a_failed_render_and_still_terminalizes() {
    let fixture = fixture();
    fixture.configure(&[("WFR_RC", "7"), ("EMIT_BODY", "true")]);
    let output = fixture.run(&["implement", "step-18", "--phase", "logs-flush"]);
    assert_eq!(code(&output), 0, "{}", stderr(&output));
    let text = stdout(&output);
    assert_eq!(kv("WFR_RC", &text), "7");
    assert_eq!(count("---LARCH-SUMMARY-FINAL-BEGIN---", &text), 0);
    assert!(stderr(&output).contains("final report render failed (WFR_RC=7)"));
    let log = fixture.log();
    assert!(log.contains("append-failure"));
    assert!(log.contains("run-log lifecycle-failure"), "{log}");
    assert!(!log.contains("teardown sentinel="));
}

#[test]
fn step18_unreadable_summary_leaves_an_unbalanced_marker_pair() {
    let fixture = fixture();
    fixture.configure(&[("SUMMARY_UNREADABLE", "true"), ("EMIT_BODY", "true")]);
    let output = fixture.run(&["implement", "step-18", "--phase", "logs-flush"]);
    assert_eq!(code(&output), 0, "{}", stderr(&output));
    let text = stdout(&output);
    assert_eq!(count("---LARCH-SUMMARY-FINAL-BEGIN---", &text), 1);
    assert_eq!(count("---LARCH-SUMMARY-FINAL-END---", &text), 0);
}

#[test]
fn step18_without_a_run_id_fails_before_the_safety_nets() {
    let fixture = fixture();
    fixture.write_state("session-env.sh", "STALL_TRACKING=false\n");
    fixture.configure(&[("EMIT_BODY", "false")]);
    let output = fixture.run(&["implement", "step-18", "--phase", "logs-flush"]);
    assert_eq!(code(&output), 1);
    assert_eq!(kv("RUN_LOG_PUBLISH_OK", &stdout(&output)), "false");
    assert!(stderr(&output).contains("LARCH_RUN_ID is unavailable"));
    let log = fixture.log();
    assert!(!log.contains("prepare-terminal-snapshot"));
    assert!(!log.contains("run-log lifecycle-"));
    assert!(!log.contains("teardown"));
    assert!(fixture.tmpdir.is_dir());
}

#[test]
fn step18_requires_the_session_tmpdir() {
    let fixture = fixture();
    let output = Command::new(env!("CARGO_BIN_EXE_larch"))
        .current_dir(&fixture.repo)
        .env("CLAUDE_PLUGIN_ROOT", &fixture.plugin)
        .env_remove("IMPLEMENT_TMPDIR")
        .args(["implement", "step-18", "--phase", "gate"])
        .output()
        .expect("run larch");
    assert_eq!(code(&output), 2);
    assert!(stderr(&output).contains("implement step-18: IMPLEMENT_TMPDIR is required"));
}

// ---------------------------------------------------------------------------
// step-18-gate-logs-flush composite
// ---------------------------------------------------------------------------

#[test]
fn composite_emits_all_five_layers_and_stops_on_a_stall() {
    let fixture = fixture();
    fixture.write_state("finalize-state.sh", "STALL_TRACKING=true\nSTALL_STEP=8\n");
    let output = fixture.run(&[
        "implement",
        "step-18-gate-logs-flush",
        "--implement-tmpdir",
        fixture.tmpdir.to_str().expect("utf8"),
    ]);
    assert_eq!(code(&output), 0, "{}", stderr(&output));
    let text = stdout(&output);
    assert_eq!(kv("STALL_TRACKING_ABANDONED_MARKER", &text), "false");
    assert_eq!(kv("STALL_TRACKING_FINALIZE", &text), "true");
    assert_eq!(kv("STALL_RECOVERY_REQUIRED", &text), "true");
    assert_eq!(kv("NEXT_ACTION", &text), "stall-recovery");
    assert!(fixture.log().is_empty());
}

#[test]
fn composite_runs_the_logs_flush_after_a_clear_gate() {
    let fixture = fixture();
    fixture.configure(&[("EMIT_BODY", "false"), ("OUTCOME", "shipped")]);
    let output = fixture.run(&["implement", "step-18-gate-logs-flush"]);
    assert_eq!(code(&output), 0, "{}", stderr(&output));
    let text = stdout(&output);
    assert_eq!(kv("STALL_RECOVERY_REQUIRED", &text), "false");
    assert_eq!(kv("NEXT_ACTION", &text), "logs-flush-done");
    assert_eq!(kv("IMPLEMENT_NORMALIZED_OUTCOME", &text), "shipped");
    assert!(fixture.log().contains("normalize-outcome"));
    assert!(fixture.tmpdir.join(".run-log-terminalized").is_file());
}

#[test]
fn composite_refuses_terminal_shipping_without_a_pr_number() {
    let fixture = fixture();
    fixture.configure(&[("OUTCOME", "shipping"), ("PR_NUMBER", "")]);
    let output = fixture.run(&["implement", "step-18-gate-logs-flush"]);
    assert_eq!(code(&output), 1, "{}", stderr(&output));
    let text = stdout(&output);
    assert_eq!(kv("STALL_RECOVERY_REQUIRED", &text), "true");
    assert_eq!(kv("TERMINAL_FINALIZE_REFUSED", &text), "true");
    assert_eq!(kv("STATUS", &text), "blocked");
    assert_eq!(kv("OUTCOME", &text), "stalled");
    assert_eq!(kv("NEXT_ACTION", &text), "tool-failure");
    let state = fs::read_to_string(fixture.tmpdir.join("finalize-state.sh")).expect("state");
    assert!(state.contains("BAIL_REASON=step18-terminal-shipping-without-pr\n"), "{state}");
    assert!(state.contains("STEP18_GATE_REFUSAL=step18-terminal-shipping-without-pr\n"));
    assert!(state.contains("EXIT_CODE=1\nPHASE=stalled\n"), "sorted keys: {state}");
    let issues = fs::read_to_string(fixture.tmpdir.join("execution-issues.md")).expect("issues");
    assert!(issues.contains("Step 18 terminal gate"));
    assert!(!fixture.log().contains("prepare-terminal-snapshot"));
}

#[test]
fn composite_reports_unknown_when_the_refusal_cannot_be_persisted() {
    let fixture = fixture();
    fixture.configure(&[("OUTCOME", "shipping"), ("PR_NUMBER", "")]);
    let state = fixture.tmpdir.join("finalize-state.sh");
    fs::remove_file(&state).expect("remove state");
    std::os::unix::fs::symlink(fixture.tmpdir.join("elsewhere.sh"), &state).expect("symlink");
    let output = fixture.run(&["implement", "step-18-gate-logs-flush"]);
    assert_eq!(code(&output), 1);
    assert_eq!(kv("STALL_RECOVERY_REQUIRED", &stdout(&output)), "unknown");
    assert!(stderr(&output).contains("cannot persist terminal shipping refusal"));
}

// ---------------------------------------------------------------------------
// Step 19
// ---------------------------------------------------------------------------

fn terminalize(fixture: &Fixture) {
    fs::write(
        fixture.tmpdir.join(".run-log-terminalized"),
        "RUN_LOG_TERMINALIZED=true\nRUN_LOG_PUBLICATION=published\nLIFECYCLE_TERMINALIZED=true\n",
    )
    .expect("terminalization record");
}

#[test]
fn step19_refuses_without_a_terminalization_record() {
    let fixture = fixture();
    let output = fixture.run(&["implement", "step-19"]);
    assert_eq!(code(&output), 1);
    assert_eq!(
        kv("CLEANUP_BLOCKED", &stdout(&output)),
        "run-log-not-terminalized"
    );
    assert!(stderr(&output).contains("Step 18 run-log terminalization is not recorded"));
    assert!(!fixture.log().contains("teardown"));
}

#[test]
fn step19_relays_the_teardown_tail_and_exit_code() {
    let fixture = fixture();
    terminalize(&fixture);
    let output = fixture.run(&[
        "implement",
        "step-19",
        "--implement-tmpdir",
        fixture.tmpdir.to_str().expect("utf8"),
    ]);
    assert_eq!(code(&output), 0, "{}", stderr(&output));
    let text = stdout(&output);
    for row in [
        "ISSUE_URL=https://example.test/issues/1",
        "RENAME_BRANCH=skipped",
        "RENAME_STATUS=ok",
        "STASH_REF=refs/stash/test",
        "SENTINEL_WRITTEN=true",
        "FINALIZE_SUBCOMMAND=teardown",
        "FINALIZE_WARNINGS=none",
    ] {
        assert!(text.contains(row), "{row} missing from {text}");
    }
    let log = fixture.log();
    assert!(log.contains("clear-implement-pointer --claude-pid"));
    assert!(log.contains("teardown sentinel=missing argv=implement-finalize teardown --state-file"));
    assert!(
        !log.contains("restore-finalize-state"),
        "aligned state skips the restore"
    );
}

#[test]
fn step19_restores_for_each_documented_trigger() {
    for (name, ship, finalize) in [
        ("missing-finalize", "STALL_TRACKING=false\nSTALL_STEP=\n", None),
        (
            "ship-stall",
            "STALL_TRACKING=yes\nBAIL_NEEDS_USER_INPUT=false\nSTALL_STEP=\n",
            Some("STALL_TRACKING=false\nSTALL_STEP=\n"),
        ),
        (
            "ship-bail",
            "STALL_TRACKING=false\nBAIL_NEEDS_USER_INPUT=ON\nSTALL_STEP=\n",
            Some("STALL_TRACKING=false\nSTALL_STEP=\n"),
        ),
        (
            "stall-step-mismatch",
            "STALL_TRACKING=false\nBAIL_NEEDS_USER_INPUT=false\nSTALL_STEP=ship\n",
            Some("STALL_TRACKING=false\nSTALL_STEP=final\n"),
        ),
    ] {
        let fixture = fixture();
        terminalize(&fixture);
        fixture.write_state("ship-pr-state.sh", ship);
        match finalize {
            Some(body) => fixture.write_state("finalize-state.sh", body),
            None => fs::remove_file(fixture.tmpdir.join("finalize-state.sh")).expect("remove"),
        }
        let output = fixture.run(&["implement", "step-19"]);
        assert_eq!(code(&output), 0, "{name}: {}", stderr(&output));
        let log = fixture.log();
        assert!(
            log.contains("restore-finalize-state --implement-tmpdir"),
            "{name}: {log}"
        );
        assert!(
            line_of("restore-finalize-state", &log) < line_of("teardown sentinel=", &log),
            "{name}: restore must precede teardown"
        );
    }
}

#[test]
fn step19_tears_down_even_after_a_failed_restore() {
    let fixture = fixture();
    terminalize(&fixture);
    fixture.write_state(
        "ship-pr-state.sh",
        "STALL_TRACKING=yes\nBAIL_NEEDS_USER_INPUT=true\nSTALL_STEP=ship\n",
    );
    fixture.configure(&[("RESTORE_RC", "7")]);
    let output = fixture.run(&["implement", "step-19"]);
    assert_eq!(code(&output), 0, "{}", stderr(&output));
    assert!(stderr(&output).contains("restore-finalize-state failed"));
    let log = fixture.log();
    assert!(log.contains("restore-finalize-state --implement-tmpdir"));
    assert!(log.contains("teardown sentinel="));
}

// ---------------------------------------------------------------------------
// checks-result-identity and checks self-edit-log
// ---------------------------------------------------------------------------

fn git(repo: &Path, arguments: &[&str]) {
    let status = Command::new("git")
        .current_dir(repo)
        .args(arguments)
        .env("GIT_AUTHOR_NAME", "larch")
        .env("GIT_AUTHOR_EMAIL", "larch@example.invalid")
        .env("GIT_COMMITTER_NAME", "larch")
        .env("GIT_COMMITTER_EMAIL", "larch@example.invalid")
        .output()
        .expect("run git");
    assert!(
        status.status.success(),
        "git {arguments:?}: {}",
        String::from_utf8_lossy(&status.stderr)
    );
}

fn seeded_repository(fixture: &Fixture) -> PathBuf {
    let repo = fixture.repo.clone();
    git(&repo, &["init", "--quiet"]);
    fs::write(repo.join("tracked.txt"), "one\n").expect("tracked");
    git(&repo, &["add", "tracked.txt"]);
    git(&repo, &["commit", "--quiet", "-m", "seed"]);
    repo
}

fn identity_rows(fixture: &Fixture, repo: &Path) -> String {
    let output = fixture.run(&[
        "implement",
        "checks-result-identity",
        "compute",
        "--repo-root",
        repo.to_str().expect("utf8"),
    ]);
    assert_eq!(code(&output), 0, "{}", stderr(&output));
    stdout(&output)
}

#[test]
fn identity_is_deterministic_and_changes_with_every_input_class() {
    let fixture = fixture();
    let repo = seeded_repository(&fixture);
    let first = identity_rows(&fixture, &repo);
    assert_eq!(
        first,
        identity_rows(&fixture, &repo),
        "two reads of an unchanged tree must agree"
    );
    assert_eq!(kv("CHECKS_INPUT_FP_SCHEMA", &first), "v1");
    assert_eq!(kv("CHECKS_INPUT_TREE_FP", &first).len(), 64);

    fs::write(repo.join("tracked.txt"), "two\n").expect("unstaged edit");
    let unstaged = identity_rows(&fixture, &repo);
    assert_ne!(kv("CHECKS_INPUT_TREE_FP", &first), kv("CHECKS_INPUT_TREE_FP", &unstaged));

    git(&repo, &["add", "tracked.txt"]);
    let staged = identity_rows(&fixture, &repo);
    assert_ne!(
        kv("CHECKS_INPUT_TREE_FP", &unstaged),
        kv("CHECKS_INPUT_TREE_FP", &staged)
    );

    fs::write(repo.join("new.txt"), "untracked\n").expect("untracked file");
    let untracked = identity_rows(&fixture, &repo);
    assert_ne!(
        kv("CHECKS_INPUT_TREE_FP", &staged),
        kv("CHECKS_INPUT_TREE_FP", &untracked)
    );

    git(&repo, &["add", "."]);
    git(&repo, &["commit", "--quiet", "-m", "second"]);
    let committed = identity_rows(&fixture, &repo);
    assert_ne!(
        kv("CHECKS_INPUT_HEAD_SHA", &first),
        kv("CHECKS_INPUT_HEAD_SHA", &committed)
    );
    assert_ne!(
        kv("CHECKS_INPUT_TREE_FP", &untracked),
        kv("CHECKS_INPUT_TREE_FP", &committed)
    );
}

#[test]
fn identity_validates_children_and_rejects_unsafe_roots() {
    let fixture = fixture();
    let repo = seeded_repository(&fixture);
    let rows = identity_rows(&fixture, &repo);
    let output = fixture.run(&[
        "implement",
        "checks-result-identity",
        "validate-child",
        "--repo-root",
        repo.to_str().expect("utf8"),
        "--expected-head",
        &kv("CHECKS_INPUT_HEAD_SHA", &rows),
        "--expected-fp",
        &kv("CHECKS_INPUT_TREE_FP", &rows),
    ]);
    assert_eq!(code(&output), 0, "{}", stderr(&output));
    assert_eq!(kv("MATCH", &stdout(&output)), "true");

    fs::write(repo.join("drift.txt"), "drift\n").expect("drift");
    let drifted = fixture.run(&[
        "implement",
        "checks-result-identity",
        "validate-child",
        "--repo-root",
        repo.to_str().expect("utf8"),
        "--expected-head",
        &kv("CHECKS_INPUT_HEAD_SHA", &rows),
        "--expected-fp",
        &kv("CHECKS_INPUT_TREE_FP", &rows),
    ]);
    assert_eq!(code(&drifted), 2);
    assert!(stderr(&drifted).contains("ERROR=checks input identity drifted from launch seed"));

    let relative = fixture.run(&[
        "implement",
        "checks-result-identity",
        "compute",
        "--repo-root",
        "relative",
    ]);
    assert_eq!(code(&relative), 2);
    assert!(stderr(&relative).contains("ERROR=repo root must be an absolute path"));

    let non_repo = fixture.run(&[
        "implement",
        "checks-result-identity",
        "compute",
        "--repo-root",
        fixture.tmpdir.to_str().expect("utf8"),
    ]);
    assert_eq!(code(&non_repo), 2);
    assert!(stderr(&non_repo).contains("ERROR=repo root is not"));
}

#[test]
fn identity_classifies_every_documented_state() {
    let fixture = fixture();
    let repo = seeded_repository(&fixture);
    let rows = identity_rows(&fixture, &repo);
    let result_env = fixture.tmpdir.join("result.env");
    let classify = |body: Option<&str>| -> Output {
        match body {
            Some(text) => fs::write(&result_env, text).expect("result env"),
            None => {
                let _ = fs::remove_file(&result_env);
            }
        }
        fixture.run(&[
            "implement",
            "checks-result-identity",
            "classify",
            "--result-env",
            result_env.to_str().expect("utf8"),
            "--step",
            "s",
            "--repo-root",
            repo.to_str().expect("utf8"),
        ])
    };
    for (body, state, reason, expected_code) in [
        (None, "absent", "missing", 1),
        (Some("\n"), "incomplete", "empty", 1),
        (Some("BGJOB_RC=1\n"), "incomplete", "bgjob-rc", 1),
        (
            Some("BGJOB_RC=0\n"),
            "incomplete",
            "missing-next-action",
            1,
        ),
        (
            Some("BGJOB_RC=0\nNEXT_ACTION=nope\n"),
            "incomplete",
            "unsupported-next-action",
            1,
        ),
        (
            Some("BGJOB_RC=0\nNEXT_ACTION=continue\nSTEP=other\n"),
            "stale",
            "step-mismatch",
            1,
        ),
        (
            Some("BGJOB_RC=0\nNEXT_ACTION=continue\nSTEP=s\n"),
            "stale",
            "missing-identity",
            1,
        ),
    ] {
        let output = classify(body);
        let text = stdout(&output);
        assert_eq!(kv("STATE", &text), state, "{body:?}");
        assert_eq!(kv("REASON", &text), reason, "{body:?}");
        assert_eq!(code(&output), expected_code, "{body:?}");
        assert_eq!(kv("CHECKS_INPUT_FP_SCHEMA", &text), "v1");
    }
    let matching = classify(Some(&format!(
        "BGJOB_RC=0\nNEXT_ACTION=continue\nSTEP=s\n{rows}"
    )));
    assert_eq!(code(&matching), 0, "{}", stderr(&matching));
    assert_eq!(kv("STATE", &stdout(&matching)), "matching");

    std::os::unix::fs::symlink(fixture.tmpdir.join("elsewhere"), fixture.tmpdir.join("link.env"))
        .expect("symlink");
    let unsafe_env = fixture.run(&[
        "implement",
        "checks-result-identity",
        "classify",
        "--result-env",
        fixture.tmpdir.join("link.env").to_str().expect("utf8"),
        "--step",
        "s",
        "--repo-root",
        repo.to_str().expect("utf8"),
    ]);
    assert_eq!(code(&unsafe_env), 2);
    assert_eq!(kv("REASON", &stdout(&unsafe_env)), "non-regular-result-env");
}

#[test]
fn identity_live_seed_and_repo_root_resolution() {
    let fixture = fixture();
    let repo = seeded_repository(&fixture);
    let rows = identity_rows(&fixture, &repo);
    let merge_env = fixture.tmpdir.join("merge.env");
    fs::write(&merge_env, &rows).expect("merge env");
    let matching = fixture.run(&[
        "implement",
        "checks-result-identity",
        "classify",
        "--mode",
        "live-seed",
        "--merge-env",
        merge_env.to_str().expect("utf8"),
        "--result-env",
        merge_env.to_str().expect("utf8"),
        "--step",
        "s",
        "--repo-root",
        repo.to_str().expect("utf8"),
    ]);
    assert_eq!(code(&matching), 0, "{}", stderr(&matching));
    assert_eq!(kv("STATE", &stdout(&matching)), "matching");

    fs::write(
        &merge_env,
        rows.replace(&kv("CHECKS_INPUT_FP_SCHEMA", &rows), "v2"),
    )
    .expect("schema drift");
    let drifted = fixture.run(&[
        "implement",
        "checks-result-identity",
        "classify",
        "--mode",
        "live-seed",
        "--merge-env",
        merge_env.to_str().expect("utf8"),
        "--result-env",
        merge_env.to_str().expect("utf8"),
        "--step",
        "s",
        "--repo-root",
        repo.to_str().expect("utf8"),
    ]);
    assert_eq!(code(&drifted), 1);
    assert_eq!(kv("REASON", &stdout(&drifted)), "missing-identity");

    fs::write(
        fixture.tmpdir.join("session-env.sh"),
        format!("REPO_ROOT={}\n", repo.display()),
    )
    .expect("session env");
    let resolved = fixture.run(&[
        "implement",
        "checks-result-identity",
        "resolve-repo-root",
        "--implement-tmpdir",
        fixture.tmpdir.to_str().expect("utf8"),
    ]);
    assert_eq!(code(&resolved), 0, "{}", stderr(&resolved));
    assert_eq!(
        kv("REPO_ROOT", &stdout(&resolved)),
        repo.to_str().expect("utf8")
    );
}

#[test]
fn self_edit_log_reports_records_and_attribution() {
    let fixture = fixture();
    let repo = seeded_repository(&fixture);
    let digest = fixture.run(&[
        "implement",
        "checks-result-identity",
        "compute",
        "--repo-root",
        repo.to_str().expect("utf8"),
    ]);
    assert_eq!(code(&digest), 0);
    fs::write(
        fixture.tmpdir.join("self-edit-log.tsv"),
        "recorded_epoch_s\tsource\tpath\tpost_sha256\n17\tlint-fix\ttracked.txt\tdeadbeef\nmalformed\trow\n",
    )
    .expect("self-edit log");
    let listed = fixture.run(&[
        "checks",
        "self-edit-log",
        "--tmpdir",
        fixture.tmpdir.to_str().expect("utf8"),
    ]);
    assert_eq!(code(&listed), 0, "{}", stderr(&listed));
    let text = stdout(&listed);
    assert_eq!(kv("SELF_EDIT_COUNT", &text), "1");
    assert!(text.contains(
        "SELF_EDIT source=lint-fix recorded_epoch_s=17 post_sha256=deadbeef path=tracked.txt"
    ));
    assert_eq!(kv("SELF_EDIT_LOG_STATUS", &text), "ok");

    let queried = fixture.run(&[
        "checks",
        "self-edit-log",
        "--tmpdir",
        fixture.tmpdir.to_str().expect("utf8"),
        "--path",
        "tracked.txt",
        "--repo-root",
        repo.to_str().expect("utf8"),
    ]);
    assert_eq!(code(&queried), 0);
    let queried_text = stdout(&queried);
    assert_eq!(kv("SELF_EDIT_ATTRIBUTED", &queried_text), "true");
    assert_eq!(kv("SELF_EDIT_CONTENT_MATCHES", &queried_text), "false");

    let absent = fixture.run(&[
        "checks",
        "self-edit-log",
        "--tmpdir",
        fixture.tmpdir.to_str().expect("utf8"),
        "--path",
        "other.txt",
    ]);
    assert_eq!(kv("SELF_EDIT_ATTRIBUTED", &stdout(&absent)), "false");

    let refused = fixture.run(&[
        "checks",
        "self-edit-log",
        "--tmpdir",
        repo.to_str().expect("utf8"),
    ]);
    assert_eq!(code(&refused), 2);
    assert_eq!(
        kv("SELF_EDIT_LOG_STATUS", &stdout(&refused)),
        "tmpdir-validation"
    );
}
