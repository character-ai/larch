//! End-to-end coverage for the code-review voter panel dispatcher.
//!
//! Every case runs the real command against a fixture plugin root. The
//! waterfall owner is a stub reached through `scripts/larch.sh`, and the verbs
//! Python still owns are a stub `python/cli.py`. Both are steered by marker
//! files in the review tmpdir, because the dispatch publishes a typed child
//! environment rather than the ambient one.

#![cfg(unix)]

use std::{
    fs,
    os::unix::fs::PermissionsExt as _,
    path::{Path, PathBuf},
};

use assert_cmd::Command as AssertCommand;
use tempfile::TempDir;

/// Stub waterfall owner. It binds one result per manifest row, honouring the
/// marker files a case drops beside the manifest.
const WATERFALL_STUB: &str = r#"#!/usr/bin/env python3
import json
import os
import sys

args = sys.argv[1:]


def value(flag):
    return args[args.index(flag) + 1] if flag in args else ""


slots = value("--slots-file")
directory = os.path.dirname(slots)
with open(os.path.join(directory, "waterfall-argv.log"), "a") as handle:
    handle.write(" ".join(args) + "\n")
with open(os.path.join(directory, "waterfall-env.log"), "a") as handle:
    for key in (
        "CLAUDE_PLUGIN_ROOT",
        "LARCH_PANEL_ARTIFACT_DIR",
        "LARCH_PANEL_SITE",
        "LARCH_PANEL_ROUND_NUM",
        "LARCH_PANEL_ROUND_DIR",
        "LARCH_PANEL_SLOT",
        "REVIEW_TMPDIR",
    ):
        handle.write("%s=%s\n" % (key, os.environ.get(key, "")))


def marker(name):
    return os.path.exists(os.path.join(directory, name))


present = {"codex": value("--codex-present") == "true", "cursor": value("--cursor-present") == "true"}
outputs = []
tools = []
with open(slots) as handle:
    rows = [json.loads(line) for line in handle if line.strip()]
for row in rows:
    slot = row["slot"]
    output = row["output"]
    if marker("DROP-" + slot):
        continue
    primary = row["tool"]
    opposite = "cursor" if primary == "codex" else "codex"
    if present.get(primary):
        tool = primary
    elif present.get(opposite):
        tool = opposite
    else:
        tool = "claude"
    label = os.path.basename(output).removesuffix("-vote-output.txt")
    with open(output, "w") as handle:
        handle.write("" if marker("EMPTY-" + slot) else "narrative only\n" if marker("PARSE-BAD-" + label) else "FINDING_1: YES\n")
    if marker("STALE-DIAG-" + label): os.mkdir(output.removesuffix(".txt") + "-parse-rate-diag.txt")
    with open(output + ".done", "w") as handle:
        handle.write("1\n" if marker("RC1-" + slot) else "0\n")
    outputs.append(output)
    tools.append(tool)
if marker("PATHS-FILE"):
    # The live dispatcher publishes its result list as a file and leaves the
    # inline list for callers that cannot read it.
    published = os.path.join(directory, "slots.ndjson.output-files")
    with open(published, "w") as handle:
        handle.write("".join(path + "\n" for path in outputs))
    sys.stdout.write("ALL_OUTPUT_FILES_PATH=%s\n" % published)
    sys.stdout.write("ALL_OUTPUT_FILES=\n")
else:
    sys.stdout.write("ALL_OUTPUT_FILES=%s\n" % " ".join(outputs))
sys.stdout.write("ALL_OUTPUT_TOOLS=%s\n" % " ".join(tools))
sys.stdout.write("DISPATCH_OK=%s\n" % ("false" if marker("DISPATCH-FALSE") else "true"))
if marker("WATERFALL-WARN"):
    sys.stdout.write("WARN=stub warning\n")
sys.stderr.write("waterfall stub diagnostics\n")
sys.exit(3 if marker("WATERFALL-FAIL") else 0)
"#;

/// Stub Python dispatcher for the verbs this command still delegates.
const CLI_STUB: &str = r#"import os
import sys

args = sys.argv[1:]
verb = tuple(args[:2])
review = os.environ.get("REVIEW_TMPDIR", "")


def value(flag):
    return args[args.index(flag) + 1] if flag in args else ""


def marker(name):
    return os.path.exists(os.path.join(review, name))


with open(os.path.join(review, "cli-argv.log"), "a") as handle:
    handle.write(" ".join(args) + "\n")

if verb == ("render", "voter"):
    sidecar = value("--payload-bytes-output")
    if sidecar:
        with open(sidecar, "w") as handle:
            handle.write("128\n")
    sys.stdout.write("stub voter prompt for %s\n" % value("--voter-tool"))
    if not marker("RENDER-NO-POINTER"):
        sys.stdout.write("Read the ballot from this path: %s\n" % value("--ballot-file"))
    sys.exit(1 if marker("RENDER-FAIL") else 0)

if verb == ("voter-calibration", "snapshot"):
    if marker("SNAPSHOT-FAIL"):
        sys.exit(1)
    out = value("--out")
    if out and not marker("SNAPSHOT-EMPTY"):
        with open(out, "w") as handle:
            handle.write("tool\tyes_votes\n")
    sys.exit(0)

if verb == ("timing", "record-vendor-task"):
    with open(os.path.join(review, "timing.log"), "a") as handle:
        handle.write(" ".join(args) + "\n")
    sys.exit(0)

sys.stderr.write("unexpected verb: %s\n" % " ".join(args))
sys.exit(2)
"#;

fn write(path: &Path, contents: &str) {
    fs::create_dir_all(path.parent().expect("fixture parent")).expect("create fixture parent");
    fs::write(path, contents).expect("write fixture");
}

fn write_executable(path: &Path, contents: &str) {
    write(path, contents);
    fs::set_permissions(path, fs::Permissions::from_mode(0o755)).expect("fixture permissions");
}

/// One dispatch fixture: a plugin root, a review tmpdir, and a ballot.
struct Fixture {
    _root: TempDir,
    plugin: PathBuf,
    review: PathBuf,
    consumer: PathBuf,
}

impl Fixture {
    fn create() -> Self {
        // `/tmp` rather than the platform temp root: the plugin-root validator
        // rejects a path with characters the sandbox root can contain.
        let root = TempDir::new_in("/tmp").expect("fixture root");
        let plugin = root.path().join("plugin");
        let review = root.path().join("review");
        let consumer = root.path().join("consumer");
        write_executable(&plugin.join("scripts/larch.sh"), WATERFALL_STUB);
        write(&plugin.join("python/cli.py"), CLI_STUB);
        fs::create_dir_all(&review).expect("review tmpdir");
        fs::create_dir_all(&consumer).expect("consumer root");
        write(&review.join("findings.md"), "FINDING_1: something\n");
        Self {
            _root: root,
            plugin,
            review,
            consumer,
        }
    }

    fn path(&self, name: &str) -> PathBuf {
        self.review.join(name)
    }

    fn marker(&self, name: &str) {
        write(&self.path(name), "");
    }

    fn read(&self, name: &str) -> String {
        fs::read_to_string(self.path(name)).unwrap_or_default()
    }

    fn command(&self) -> AssertCommand {
        let mut command = AssertCommand::cargo_bin("larch").expect("larch binary should build");
        command.env("CLAUDE_PLUGIN_ROOT", &self.plugin);
        command.env("REVIEW_TMPDIR", &self.review);
        command.env("LARCH_CONSUMER_REPO", &self.consumer);
        for key in [
            "CLAUDE_PROJECT_DIR",
            "REPO_ROOT",
            "IMPLEMENT_TMPDIR",
            "DESIGN_TMPDIR",
            "SESSION_ENV_PATH",
            "LARCH_TIMING_LEDGER",
            "LARCH_TIMING_SKILL",
            "LARCH_PANEL_ARTIFACT_DIR",
            "LARCH_VOTER_CALIBRATION_FEEDBACK",
            "LARCH_VOTER_CALIBRATION_WINDOW",
            "LARCH_CODEX_MODEL",
            "LARCH_CODEX_VOTE_MODEL",
            "LARCH_VOTER_JUDGE_ERROR_PARSE_THRESHOLD",
        ] {
            command.env_remove(key);
        }
        if self.path("THRESHOLD-HALF").exists() {
            command.env("LARCH_VOTER_JUDGE_ERROR_PARSE_THRESHOLD", "0.5");
        }
        command.args(["agent", "dispatch-voters"]);
        command
    }

    /// Run one dispatch with the standard flags plus the caller's extras.
    fn dispatch(&self, codex: &str, cursor: &str, extra: &[&str]) -> std::process::Output {
        let mut command = self.command();
        command.args([
            "--ballot-file",
            &self.path("findings.md").display().to_string(),
            "--review-tmpdir",
            &self.review.display().to_string(),
            "--codex-available",
            codex,
            "--cursor-available",
            cursor,
        ]);
        command.args(extra);
        command.output().expect("dispatch runs")
    }
}

fn kv<'a>(stdout: &'a str, key: &str) -> &'a str {
    let prefix = format!("{key}=");
    stdout
        .lines()
        .filter_map(|line| line.strip_prefix(prefix.as_str()))
        .next_back()
        .unwrap_or_default()
}

fn stdout_of(output: &std::process::Output) -> String {
    String::from_utf8_lossy(&output.stdout).into_owned()
}

fn stderr_of(output: &std::process::Output) -> String {
    String::from_utf8_lossy(&output.stderr).into_owned()
}

#[test]
fn a_full_panel_publishes_three_launched_voters() {
    let fixture = Fixture::create();
    let output = fixture.dispatch("true", "true", &[]);
    assert_eq!(output.status.code(), Some(0), "{}", stderr_of(&output));
    let stdout = stdout_of(&output);
    assert_eq!(kv(&stdout, "DISPATCH_OK"), "true");
    for slot in 1..=3 {
        assert_eq!(kv(&stdout, &format!("VOTER_{slot}_STATUS")), "launched");
        assert_eq!(
            kv(&stdout, &format!("VOTER_{slot}_PARSE_RATE_STATUS")),
            "OK"
        );
    }
    assert_eq!(kv(&stdout, "VOTER_1_TOOL"), "codex-validity");
    assert_eq!(kv(&stdout, "VOTER_2_TOOL"), "codex-plan-fidelity");
    assert_eq!(kv(&stdout, "VOTER_3_TOOL"), "codex-pragmatism");
    assert!(
        kv(&stdout, "VOTER_1_PATH").ends_with("codex-validity-vote-output.txt"),
        "{stdout}"
    );
    assert_eq!(
        kv(&stdout, "VOTER_PATHS_FILE"),
        fixture.path("code-voter-paths.txt").display().to_string()
    );
    assert_eq!(fixture.read("code-voter-paths.txt").lines().count(), 3);
    let cli = fixture.read("cli-argv.log");
    assert!(!cli.contains("voting parse-rate-retry"));
    assert!(!stdout.contains("DEGRADED_PANEL_WARNING"), "{stdout}");
}

#[test]
fn the_wire_rows_stay_in_their_canonical_order() {
    let fixture = Fixture::create();
    let output = fixture.dispatch("true", "true", &[]);
    let stdout = stdout_of(&output);
    let expected = [
        "VOTER_1_PATH",
        "VOTER_1_TOOL",
        "VOTER_1_STATUS",
        "VOTER_1_PARSE_RATE_STATUS",
        "VOTER_2_PATH",
        "VOTER_2_TOOL",
        "VOTER_2_STATUS",
        "VOTER_2_PARSE_RATE_STATUS",
        "VOTER_3_PATH",
        "VOTER_3_TOOL",
        "VOTER_3_STATUS",
        "VOTER_3_PARSE_RATE_STATUS",
        "VOTER_PATHS_FILE",
        "DISPATCH_OK",
    ];
    let lines: Vec<&str> = stdout.lines().collect();
    assert_eq!(lines.len(), expected.len(), "{stdout}");
    for (line, key) in lines.iter().zip(expected) {
        assert!(line.starts_with(&format!("{key}=")), "{key} not at {line}");
    }
}

#[test]
fn the_manifest_carries_one_row_per_launched_slot() {
    let fixture = Fixture::create();
    let _output = fixture.dispatch("true", "true", &["--tier", "hard"]);
    let manifest = fixture.read("code-voter-slots.ndjson");
    let rows: Vec<serde_json::Value> = manifest
        .lines()
        .map(|line| serde_json::from_str(line).expect("manifest row is JSON"))
        .collect();
    assert_eq!(rows.len(), 3);
    assert_eq!(rows[0]["slot"], "voter-1");
    assert_eq!(rows[0]["tool"], "codex");
    assert_eq!(rows[0]["model_role"], "vote");
    assert_eq!(rows[0]["resolved_model"], "gpt-5.6-terra");
    assert_eq!(rows[0]["payload_files"]["codex"], 128);
    let prompts = rows[0]["prompt_files"]
        .as_object()
        .expect("prompt files object");
    assert_eq!(prompts.len(), 3, "{manifest}");
    assert!(
        prompts["claude"]
            .as_str()
            .unwrap_or_default()
            .ends_with("validity-vote-prompt-claude.txt"),
        "{manifest}"
    );
}

#[test]
fn a_trivial_tier_pins_the_review_model() {
    let fixture = Fixture::create();
    let _output = fixture.dispatch("true", "true", &["--tier", "TRIVIAL"]);
    let manifest = fixture.read("code-voter-slots.ndjson");
    let row: serde_json::Value =
        serde_json::from_str(manifest.lines().next().unwrap_or_default()).expect("row");
    assert_eq!(row["resolved_model"], "gpt-5.6-luna");
    assert!(
        fixture
            .read("waterfall-argv.log")
            .contains("--default-model gpt-5.6-luna"),
        "{}",
        fixture.read("waterfall-argv.log")
    );
}

#[test]
fn both_externals_down_shrink_the_panel_rather_than_backfilling_it() {
    let fixture = Fixture::create();
    let output = fixture.dispatch("false", "false", &[]);
    let stdout = stdout_of(&output);
    assert_eq!(kv(&stdout, "VOTER_1_STATUS"), "launched");
    assert_eq!(kv(&stdout, "VOTER_1_TOOL"), "claude");
    assert_eq!(kv(&stdout, "VOTER_2_STATUS"), "skipped");
    assert_eq!(kv(&stdout, "VOTER_3_STATUS"), "skipped");
    assert_eq!(kv(&stdout, "VOTER_2_TOOL"), "codex-plan-fidelity");
    assert_eq!(kv(&stdout, "VOTER_2_PATH"), "");
    assert_eq!(kv(&stdout, "DISPATCH_OK"), "true");
    assert!(!stdout.contains("DEGRADED_PANEL_WARNING"), "{stdout}");
    assert_eq!(fixture.read("code-voter-paths.txt").lines().count(), 1);
    let manifest = fixture.read("code-voter-slots.ndjson");
    assert_eq!(manifest.lines().count(), 1);
    let row: serde_json::Value = serde_json::from_str(manifest.trim()).expect("row");
    let prompts = row["prompt_files"].as_object().expect("prompt files");
    assert_eq!(prompts.keys().collect::<Vec<_>>(), ["claude"]);
}

#[test]
fn one_external_down_still_launches_every_slot() {
    let fixture = Fixture::create();
    let output = fixture.dispatch("false", "true", &[]);
    let stdout = stdout_of(&output);
    assert_eq!(kv(&stdout, "VOTER_1_TOOL"), "cursor-validity");
    assert_eq!(kv(&stdout, "VOTER_3_STATUS"), "launched");
    let manifest = fixture.read("code-voter-slots.ndjson");
    let row: serde_json::Value =
        serde_json::from_str(manifest.lines().next().unwrap_or_default()).expect("row");
    let prompts = row["prompt_files"].as_object().expect("prompt files");
    assert_eq!(prompts.keys().collect::<Vec<_>>(), ["claude", "cursor"]);
}

#[test]
fn a_dropped_middle_slot_degrades_the_panel_without_backfill() {
    let fixture = Fixture::create();
    fixture.marker("DROP-voter-2");
    let output = fixture.dispatch("true", "true", &[]);
    let stdout = stdout_of(&output);
    assert_eq!(kv(&stdout, "VOTER_2_STATUS"), "failed");
    assert_eq!(kv(&stdout, "VOTER_2_TOOL"), "codex-plan-fidelity");
    assert_eq!(kv(&stdout, "VOTER_3_STATUS"), "launched");
    assert!(
        kv(&stdout, "VOTER_3_PATH").ends_with("codex-pragmatism-vote-output.txt"),
        "{stdout}"
    );
    assert_eq!(
        kv(&stdout, "DEGRADED_PANEL_WARNING"),
        "**⚠ Degraded code-review panel: 2/3 effective judges produced output.**"
    );
    assert_eq!(kv(&stdout, "DISPATCH_OK"), "true");
}

#[test]
fn a_nonzero_completion_sentinel_fails_its_slot() {
    let fixture = Fixture::create();
    fixture.marker("RC1-voter-3");
    let output = fixture.dispatch("true", "true", &[]);
    let stdout = stdout_of(&output);
    assert_eq!(kv(&stdout, "VOTER_3_STATUS"), "failed");
    assert_eq!(kv(&stdout, "VOTER_3_PARSE_RATE_STATUS"), "SKIPPED");
    assert!(stdout.contains("DEGRADED_PANEL_WARNING"), "{stdout}");
}

#[test]
fn an_empty_result_fails_its_slot() {
    let fixture = Fixture::create();
    fixture.marker("EMPTY-voter-1");
    let output = fixture.dispatch("true", "true", &[]);
    let stdout = stdout_of(&output);
    assert_eq!(kv(&stdout, "VOTER_1_STATUS"), "failed");
    assert_eq!(kv(&stdout, "DISPATCH_OK"), "false");
}

#[test]
#[rustfmt::skip]
fn a_narrative_only_voter_leaves_the_tally() {
    let fixture = Fixture::create();
    fixture.marker("PARSE-BAD-codex-pragmatism");
    fixture.marker("STALE-DIAG-codex-validity");
    let output = fixture.dispatch("true", "true", &[]);
    let stdout = stdout_of(&output);
    assert_eq!(kv(&stdout, "VOTER_3_PARSE_RATE_STATUS"), "NOT_SUBSTANTIVE");
    assert_eq!(kv(&stdout, "VOTER_1_PARSE_RATE_STATUS"), "NOT_SUBSTANTIVE");
    assert_eq!(kv(&stdout, "VOTER_3_STATUS"), "launched");
    let stderr = stderr_of(&output);
    assert!(!stderr.contains("ballot items returned JUDGE_ERROR") && !stderr.contains("os error"), "{stderr}");
    assert!(stdout.contains("DEGRADED_PANEL_WARNING"), "{stdout}");
    // The path still reaches the tally so the retry sidecars remain readable.
    assert_eq!(fixture.read("code-voter-paths.txt").lines().count(), 3);
}

#[test]
#[rustfmt::skip]
fn nested_parse_rate_keeps_the_retired_child_threshold_boundary() {
    let fixture = Fixture::create();
    fixture.marker("THRESHOLD-HALF");
    write(&fixture.path("findings.md"), "FINDING_1: one\nFINDING_2: two\n");
    let output = fixture.dispatch("true", "true", &[]);
    assert_eq!(kv(&stdout_of(&output), "VOTER_1_PARSE_RATE_STATUS"), "OK");
    assert!(output.stderr.is_empty(), "{}", stderr_of(&output));
}

#[test]
fn a_failed_waterfall_reports_a_degraded_dispatch() {
    let fixture = Fixture::create();
    fixture.marker("DISPATCH-FALSE");
    fixture.marker("WATERFALL-FAIL");
    fixture.marker("WATERFALL-WARN");
    let output = fixture.dispatch("true", "true", &[]);
    assert_eq!(output.status.code(), Some(0));
    let stdout = stdout_of(&output);
    assert_eq!(kv(&stdout, "WARN"), "stub warning");
    assert_eq!(kv(&stdout, "DISPATCH_OK"), "false");
    assert!(
        stderr_of(&output).contains("agent dispatch-waterfall exited 3"),
        "{}",
        stderr_of(&output)
    );
}

#[test]
fn a_render_failure_aborts_before_any_launch() {
    let fixture = Fixture::create();
    fixture.marker("RENDER-FAIL");
    let output = fixture.dispatch("true", "true", &[]);
    assert_eq!(output.status.code(), Some(2));
    assert!(
        stderr_of(&output).contains("render voter failed for validity voter"),
        "{}",
        stderr_of(&output)
    );
    assert!(!fixture.path("code-voter-slots.ndjson").exists());
    assert!(!fixture.path("waterfall-argv.log").exists());
}

#[test]
fn a_prompt_without_its_ballot_pointer_aborts_before_any_launch() {
    let fixture = Fixture::create();
    fixture.marker("RENDER-NO-POINTER");
    let output = fixture.dispatch("true", "true", &[]);
    assert_eq!(output.status.code(), Some(2));
    assert!(
        stderr_of(&output).contains("missing ballot pointer"),
        "{}",
        stderr_of(&output)
    );
    assert!(!fixture.path("waterfall-argv.log").exists());
}

#[test]
fn the_waterfall_receives_the_retired_dispatch_grammar() {
    let fixture = Fixture::create();
    let diff = fixture.path("branch.diff");
    write(&diff, &"d".repeat(250_000));
    let plan = fixture.path("plan.txt");
    write(&plan, &"p".repeat(70_000));
    let _output = fixture.dispatch(
        "true",
        "false",
        &[
            "--diff-file",
            &diff.display().to_string(),
            "--plan-file",
            &plan.display().to_string(),
            "--round-num",
            "2",
            "--site",
            "implement Step 5",
        ],
    );
    let argv = fixture.read("waterfall-argv.log");
    for expected in [
        "--codex-present true",
        "--cursor-present false",
        "--mode description",
        "--timeout 1200",
        "--model-role vote",
        "--site implement Step 5",
    ] {
        assert!(argv.contains(expected), "missing {expected} in {argv}");
    }
    assert!(
        argv.contains(&format!(
            "--claude-read-tools-add-dir {}",
            fixture.review.display()
        )),
        "{argv}"
    );
    assert_eq!(fixture.read("diff-context.txt").len(), 200_000);
    assert_eq!(fixture.read("plan-context.txt").len(), 60_000);
    assert!(
        argv.contains(&format!(
            "--diff-file {} --plan-file {}",
            fixture.path("diff-context.txt").display(),
            fixture.path("plan-context.txt").display()
        )),
        "{argv}"
    );
}

#[test]
fn panel_rows_reach_the_waterfall_child() {
    let fixture = Fixture::create();
    fs::create_dir_all(fixture.path("round-3")).expect("round directory");
    let _output = fixture.dispatch("true", "true", &["--round-num", "3", "--site", "review r3"]);
    let environment = fixture.read("waterfall-env.log");
    assert!(
        environment.contains(&format!(
            "LARCH_PANEL_ARTIFACT_DIR={}",
            fixture.path("round-3").display()
        )),
        "{environment}"
    );
    assert!(
        environment.contains(&format!(
            "LARCH_PANEL_ROUND_DIR={}",
            fixture.path("round-3").display()
        )),
        "{environment}"
    );
    assert!(
        environment.contains("LARCH_PANEL_ROUND_NUM=3"),
        "{environment}"
    );
    assert!(
        environment.contains("LARCH_PANEL_SITE=review r3"),
        "{environment}"
    );
    assert!(environment.contains("LARCH_PANEL_SLOT=\n"), "{environment}");
    assert!(
        environment.contains(&format!("CLAUDE_PLUGIN_ROOT={}", fixture.plugin.display())),
        "{environment}"
    );
}

#[test]
fn a_review_tmpdir_that_is_its_own_round_owns_the_panel_artifacts() {
    let fixture = Fixture::create();
    let round = fixture.review.join("round-1");
    fs::create_dir_all(&round).expect("round directory");
    write(&round.join("findings.md"), "FINDING_1: something\n");
    let mut command = fixture.command();
    command.args([
        "--ballot-file",
        &round.join("findings.md").display().to_string(),
        "--review-tmpdir",
        &round.display().to_string(),
        "--codex-available",
        "true",
        "--cursor-available",
        "true",
    ]);
    let output = command.output().expect("dispatch runs");
    assert_eq!(output.status.code(), Some(0), "{}", stderr_of(&output));
    let environment = fs::read_to_string(round.join("waterfall-env.log")).expect("env log");
    assert!(
        environment.contains(&format!("LARCH_PANEL_ARTIFACT_DIR={}", round.display())),
        "{environment}"
    );
    assert!(
        environment.contains("LARCH_PANEL_ROUND_NUM=1"),
        "{environment}"
    );
}

#[test]
fn the_calibration_snapshot_reaches_every_prompt_render() {
    let fixture = Fixture::create();
    let _output = fixture.dispatch("true", "true", &[]);
    let cli = fixture.read("cli-argv.log");
    assert!(
        cli.contains("voter-calibration snapshot --log-root"),
        "{cli}"
    );
    assert!(
        cli.contains(&format!(
            "--calibration-stats-file {}",
            fixture.path("voter-calibration-stats.tsv").display()
        )),
        "{cli}"
    );
    assert_eq!(
        cli.matches("voter-calibration snapshot").count(),
        1,
        "{cli}"
    );
    // The consumer anchor resolves through the filesystem, so `/tmp` reads back
    // as `/private/tmp` on macOS.
    let consumer = fs::canonicalize(&fixture.consumer).expect("consumer root resolves");
    assert!(
        cli.contains(&format!(
            "--log-root {}",
            consumer.join("larch-logs").display()
        )),
        "{cli}"
    );
}

#[test]
fn a_disabled_feedback_flag_skips_the_snapshot() {
    let fixture = Fixture::create();
    let mut command = fixture.command();
    command.env("LARCH_VOTER_CALIBRATION_FEEDBACK", "0");
    command.args([
        "--ballot-file",
        &fixture.path("findings.md").display().to_string(),
        "--review-tmpdir",
        &fixture.review.display().to_string(),
        "--codex-available",
        "true",
        "--cursor-available",
        "true",
    ]);
    let output = command.output().expect("dispatch runs");
    assert_eq!(output.status.code(), Some(0), "{}", stderr_of(&output));
    let cli = fixture.read("cli-argv.log");
    assert!(!cli.contains("voter-calibration"), "{cli}");
    assert!(!cli.contains("--calibration-stats-file"), "{cli}");
}

#[test]
fn a_failed_snapshot_leaves_no_stale_calibration_file() {
    let fixture = Fixture::create();
    write(&fixture.path("voter-calibration-stats.tsv"), "stale\n");
    fixture.marker("SNAPSHOT-FAIL");
    let output = fixture.dispatch("true", "true", &[]);
    assert_eq!(output.status.code(), Some(0), "{}", stderr_of(&output));
    assert!(!fixture.path("voter-calibration-stats.tsv").exists());
    assert!(
        !fixture
            .read("cli-argv.log")
            .contains("--calibration-stats-file"),
        "{}",
        fixture.read("cli-argv.log")
    );
}

#[test]
fn the_pre_dispatch_window_lands_in_the_timing_ledger() {
    let fixture = Fixture::create();
    let ledger = fixture.path("timing-ledger.tsv");
    write(&ledger, "");
    let mut command = fixture.command();
    command.env("LARCH_TIMING_LEDGER", &ledger);
    command.args([
        "--ballot-file",
        &fixture.path("findings.md").display().to_string(),
        "--review-tmpdir",
        &fixture.review.display().to_string(),
        "--codex-available",
        "true",
        "--cursor-available",
        "true",
        "--round-num",
        "4",
    ]);
    let output = command.output().expect("dispatch runs");
    assert_eq!(output.status.code(), Some(0), "{}", stderr_of(&output));
    // `timing record-vendor-task` is Rust-owned, so the row lands in the ledger
    // rather than in the Python-verb double's argv log.
    let recorded = fs::read_to_string(&ledger).expect("read timing ledger");
    let row: Vec<&str> = recorded
        .lines()
        .find(|line| line.contains("voter-dispatch-prep"))
        .unwrap_or_default()
        .split('\t')
        .collect();
    assert_eq!(row.len(), 13, "{recorded}");
    assert_eq!(row[5], "claude", "{recorded}");
    assert_eq!(row[6], "voter-dispatch-prep", "{recorded}");
    assert_eq!(row[10], "voter-dispatch-prep-round-4.out", "{recorded}");
}

#[test]
fn no_timing_ledger_records_no_prep_row() {
    let fixture = Fixture::create();
    let output = fixture.dispatch("true", "true", &[]);
    assert_eq!(output.status.code(), Some(0), "{}", stderr_of(&output));
    assert!(!fixture.path("timing.log").exists());
}

#[test]
fn every_grammar_refusal_reports_exit_two() {
    let fixture = Fixture::create();
    let ballot = fixture.path("findings.md").display().to_string();
    let review = fixture.review.display().to_string();
    let cases: [(&[&str], &str); 6] = [
        (
            &["--ballot-file", "/larch-missing-ballot"],
            "--ballot-file must name a file",
        ),
        (
            &["--codex-available", "yes"],
            "--codex-available must be true or false",
        ),
        (
            &["--cursor-available", "1"],
            "--cursor-available must be true or false",
        ),
        (
            &["--round-num", "0"],
            "--round-num must be a positive integer",
        ),
        (
            &["--site", "  "],
            "--site requires a non-empty, non-flag-like value",
        ),
        (
            &["--tier", "EPIC"],
            "--tier must be TRIVIAL, MODERATE, or HARD",
        ),
    ];
    for (extra, expected) in cases {
        let mut command = fixture.command();
        command.args([
            "--ballot-file",
            &ballot,
            "--review-tmpdir",
            &review,
            "--codex-available",
            "true",
            "--cursor-available",
            "true",
        ]);
        command.args(extra);
        let output = command.output().expect("dispatch runs");
        assert_eq!(output.status.code(), Some(2), "{expected}");
        assert!(
            stderr_of(&output).contains(expected),
            "{expected} missing from {}",
            stderr_of(&output)
        );
    }
}

#[test]
fn a_missing_required_flag_reports_the_argparse_refusal() {
    let fixture = Fixture::create();
    let mut command = fixture.command();
    command.args(["--review-tmpdir", &fixture.review.display().to_string()]);
    let output = command.output().expect("dispatch runs");
    assert_eq!(output.status.code(), Some(2));
    let stderr = stderr_of(&output);
    assert!(
        stderr.contains(
            "the following arguments are required: --ballot-file, --codex-available, --cursor-available"
        ),
        "{stderr}"
    );
    assert!(stderr.contains("usage: agent dispatch-voters"), "{stderr}");
}

#[test]
fn an_unknown_flag_reports_the_argparse_refusal() {
    let fixture = Fixture::create();
    let output = fixture.dispatch("true", "true", &["--nope"]);
    assert_eq!(output.status.code(), Some(2));
    assert!(
        stderr_of(&output).contains("unrecognized arguments: --nope"),
        "{}",
        stderr_of(&output)
    );
}

#[test]
fn the_help_action_succeeds_without_dispatching() {
    let fixture = Fixture::create();
    let mut command = fixture.command();
    command.arg("--help");
    let output = command.output().expect("help runs");
    assert_eq!(output.status.code(), Some(0));
    assert!(
        stdout_of(&output).starts_with("usage: agent dispatch-voters"),
        "{}",
        stdout_of(&output)
    );
}

/// Build one dispatch command with the standard flags already bound.
fn standard_dispatch(fixture: &Fixture) -> AssertCommand {
    let mut command = fixture.command();
    command.args([
        "--ballot-file",
        &fixture.path("findings.md").display().to_string(),
        "--review-tmpdir",
        &fixture.review.display().to_string(),
        "--codex-available",
        "true",
        "--cursor-available",
        "true",
    ]);
    command
}

/// Assert the snapshot resolved the fixture's consumer repository.
fn assert_consumer_log_root(fixture: &Fixture) {
    let consumer = fs::canonicalize(&fixture.consumer).expect("consumer root resolves");
    let cli = fixture.read("cli-argv.log");
    assert!(
        cli.contains(&format!(
            "--log-root {}",
            consumer.join("larch-logs").display()
        )),
        "{cli}"
    );
}

#[test]
fn the_implement_session_record_resolves_the_calibration_corpus() {
    let fixture = Fixture::create();
    // The review tmpdir sits directly below the implement session root, which
    // is where the session record names the consumer repository.
    let session = fixture.review.parent().expect("session root").to_path_buf();
    write(
        &session.join("session-env.sh"),
        &format!(
            "REPO_CWD=/larch-missing-clone\nCLAUDE_PROJECT_DIR={}\n",
            fixture.consumer.display()
        ),
    );
    let mut command = standard_dispatch(&fixture);
    command.env_remove("LARCH_CONSUMER_REPO");
    let output = command.output().expect("dispatch runs");
    assert_eq!(output.status.code(), Some(0), "{}", stderr_of(&output));
    assert_consumer_log_root(&fixture);
}

#[test]
fn a_session_clone_record_resolves_the_calibration_corpus() {
    let fixture = Fixture::create();
    let session = fixture.review.parent().expect("session root").to_path_buf();
    write(
        &session.join(".larch-keepalive"),
        &format!("CLONE_PATH={}\n", fixture.consumer.display()),
    );
    let mut command = standard_dispatch(&fixture);
    command.env_remove("LARCH_CONSUMER_REPO");
    let output = command.output().expect("dispatch runs");
    assert_eq!(output.status.code(), Some(0), "{}", stderr_of(&output));
    assert_consumer_log_root(&fixture);
}

#[test]
fn an_unresolvable_calibration_corpus_skips_the_snapshot() {
    let fixture = Fixture::create();
    let mut command = standard_dispatch(&fixture);
    command.env_remove("LARCH_CONSUMER_REPO");
    let output = command.output().expect("dispatch runs");
    assert_eq!(output.status.code(), Some(0), "{}", stderr_of(&output));
    let cli = fixture.read("cli-argv.log");
    assert!(!cli.contains("voter-calibration"), "{cli}");
    assert!(!cli.contains("--calibration-stats-file"), "{cli}");
}

#[test]
fn the_calibration_window_override_reaches_the_snapshot() {
    let fixture = Fixture::create();
    let mut command = standard_dispatch(&fixture);
    command.env("LARCH_VOTER_CALIBRATION_WINDOW", "25");
    let output = command.output().expect("dispatch runs");
    assert_eq!(output.status.code(), Some(0), "{}", stderr_of(&output));
    let cli = fixture.read("cli-argv.log");
    assert!(cli.contains("--window 25"), "{cli}");
}

#[test]
fn an_empty_review_tmpdir_is_refused() {
    let fixture = Fixture::create();
    let mut command = fixture.command();
    command.args([
        "--ballot-file",
        &fixture.path("findings.md").display().to_string(),
        "--review-tmpdir",
        "",
        "--codex-available",
        "true",
        "--cursor-available",
        "true",
    ]);
    let output = command.output().expect("dispatch runs");
    assert_eq!(output.status.code(), Some(2));
    assert!(
        stderr_of(&output).contains("--review-tmpdir is required"),
        "{}",
        stderr_of(&output)
    );
}

#[test]
fn the_published_result_list_binds_every_slot() {
    let fixture = Fixture::create();
    fixture.marker("PATHS-FILE");
    let output = fixture.dispatch("true", "true", &[]);
    assert_eq!(output.status.code(), Some(0), "{}", stderr_of(&output));
    let stdout = stdout_of(&output);
    for slot in 1..=3 {
        assert_eq!(
            kv(&stdout, &format!("VOTER_{slot}_STATUS")),
            "launched",
            "{stdout}"
        );
    }
    assert!(
        kv(&stdout, "VOTER_3_PATH").ends_with("codex-pragmatism-vote-output.txt"),
        "{stdout}"
    );
    assert_eq!(kv(&stdout, "DISPATCH_OK"), "true");
}

#[test]
fn a_missing_plugin_dispatcher_is_refused() {
    let fixture = Fixture::create();
    fs::remove_file(fixture.plugin.join("python/cli.py")).expect("remove dispatcher");
    let output = standard_dispatch(&fixture).output().expect("dispatch runs");
    assert_eq!(output.status.code(), Some(2));
    assert!(
        stderr_of(&output).contains("missing python/cli.py at"),
        "{}",
        stderr_of(&output)
    );
}
