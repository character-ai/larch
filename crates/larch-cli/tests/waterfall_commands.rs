//! End-to-end coverage for the three-phase review waterfall dispatcher.
//!
//! Every case runs the real command against a fixture plugin root: the child
//! launcher is a shell stub reached through `scripts/larch.sh`, and the
//! collector is the real in-process owner. The stub is keyed by marker files in
//! the round directory, because the dispatcher publishes a typed child
//! environment rather than the ambient one.

#![cfg(unix)]

use std::{
    env, fs,
    os::unix::fs::PermissionsExt as _,
    path::{Path, PathBuf},
    process::Command,
    time::Duration,
};

use assert_cmd::Command as AssertCommand;
use tempfile::TempDir;

/// The child launcher stub. Behavior is selected by marker files so a case can
/// steer one slot without an environment variable the process layer would drop.
const LAUNCHER_STUB: &str = r#"#!/usr/bin/env bash
set -uo pipefail
out=""
prev=""
for arg in "$@"; do
  if [[ "$prev" == "--output" ]]; then out="$arg"; fi
  prev="$arg"
done
dir="$(dirname "$out")"
name="$(basename "$out")"
printf '%s\n' "$*" >> "$dir/launch-argv.log"
printf 'slot=%s|phase=%s|tool=%s|payload=%s|round=%s|artifact=%s|root=%s|site=%s\n' \
  "${LARCH_PANEL_SLOT:-}" "${LARCH_PANEL_PHASE:-}" "${LARCH_PANEL_PRIMARY_TOOL:-}" \
  "${LARCH_PANEL_PAYLOAD_BYTES:-}" "${LARCH_PANEL_ROUND_NUM:-}" "${LARCH_PANEL_ARTIFACT_DIR:-}" \
  "${CLAUDE_PLUGIN_ROOT:-}" "${LARCH_PANEL_SITE:-}" >> "$dir/launch-env.log"
echo "CHILD_STDOUT=1"
echo "stub launcher notice $name" >&2
if [[ -f "$dir/SLOW-$name" ]]; then sleep 3; fi
if [[ -f "$dir/FAIL-$name" ]]; then
  echo "launcher stub refused $name" >&2
  exit 7
fi
if [[ -f "$dir/BODY-$name" ]]; then
  cat "$dir/BODY-$name" > "$out"
else
  printf '## Recommendation\nfine\n' > "$out"
fi
printf '0\n' > "$out.done"
"#;

fn write(path: &Path, contents: &str) {
    fs::create_dir_all(path.parent().expect("fixture parent")).expect("create fixture parent");
    fs::write(path, contents).expect("write fixture");
}

fn write_executable(path: &Path, contents: &str) {
    write(path, contents);
    fs::set_permissions(path, fs::Permissions::from_mode(0o755)).expect("fixture permissions");
}

fn repository_root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .ancestors()
        .nth(2)
        .expect("repository root")
        .to_path_buf()
}

/// One dispatch fixture: a plugin root, a round directory, and a slot manifest.
struct Fixture {
    _root: TempDir,
    plugin: PathBuf,
    round: PathBuf,
}

impl Fixture {
    fn create() -> Self {
        // `/tmp` rather than the platform temp root: the plugin-root validator
        // rejects a path with characters the sandbox root can contain.
        let root = TempDir::new_in("/tmp").expect("fixture root");
        let plugin = root.path().join("plugin");
        let round = root.path().join("round-1");
        write_executable(&plugin.join("scripts/larch.sh"), LAUNCHER_STUB);
        fs::create_dir_all(&round).expect("round directory");
        write(&round.join("prompt.txt"), "prompt body\n");
        Self {
            _root: root,
            plugin,
            round,
        }
    }

    fn path(&self, name: &str) -> PathBuf {
        self.round.join(name)
    }

    fn marker(&self, name: &str) {
        write(&self.path(name), "");
    }

    fn manifest(&self, rows: &[String]) -> PathBuf {
        let path = self.path("slots.ndjson");
        write(&path, &format!("{}\n", rows.join("\n")));
        path
    }

    fn read(&self, name: &str) -> String {
        fs::read_to_string(self.path(name)).unwrap_or_default()
    }

    fn command(&self) -> AssertCommand {
        let mut command = AssertCommand::cargo_bin("larch").expect("larch binary should build");
        command.env("CLAUDE_PLUGIN_ROOT", &self.plugin);
        command.env_remove("LARCH_PANEL_ARTIFACT_DIR");
        command.env_remove("LARCH_PANEL_SOURCE_AGENT_FILE");
        command.env_remove("LARCH_FALLBACK_CLAUDE_WARN_THRESHOLD");
        command.env_remove("LARCH_REVIEWER_STRAGGLER_MULTIPLE");
        command.env_remove("LARCH_REVIEWER_STRAGGLER_FLOOR_SECONDS");
        command.env_remove("LARCH_REVIEWER_STRAGGLER_MAX_SECONDS");
        command.current_dir(self.round.as_path());
        command.args(["agent", "dispatch-waterfall"]);
        command
    }

    /// Run one dispatch with the common flags every case needs.
    fn dispatch(&self, manifest: &Path, extra: &[&str]) -> assert_cmd::assert::Assert {
        let mut command = self.command();
        command.args([
            "--slots-file",
            manifest.to_str().expect("manifest path"),
            "--codex-present",
            "true",
            "--cursor-present",
            "true",
            "--mode",
            "description",
            "--timeout",
            "60",
        ]);
        command.args(extra);
        command.assert()
    }
}

fn row(slot: &str, tool: &str, output: &Path, prompt: &Path) -> String {
    format!(
        r#"{{"slot":"{slot}","tool":"{tool}","output":"{}","prompt_file":"{}"}}"#,
        output.display(),
        prompt.display()
    )
}

fn stdout_of(assert: &assert_cmd::assert::Assert) -> String {
    String::from_utf8_lossy(&assert.get_output().stdout).into_owned()
}

fn stderr_of(assert: &assert_cmd::assert::Assert) -> String {
    String::from_utf8_lossy(&assert.get_output().stderr).into_owned()
}

fn kv<'a>(stdout: &'a str, key: &str) -> &'a str {
    stdout
        .lines()
        .find_map(|line| line.strip_prefix(&format!("{key}=")))
        .unwrap_or_default()
}

// ---------------------------------------------------------------------------
// Argument grammar
// ---------------------------------------------------------------------------

#[test]
fn help_prints_usage_and_succeeds() {
    let fixture = Fixture::create();
    let assert = fixture.command().arg("--help").assert().success();
    assert!(stderr_of(&assert).contains("Usage: dispatch-with-waterfall.sh"));
}

#[test]
fn unknown_option_reports_usage_and_exits_two() {
    let fixture = Fixture::create();
    let assert = fixture.command().arg("--nope").assert().code(2);
    let stderr = stderr_of(&assert);
    assert!(stderr.contains("unknown option: --nope"), "{stderr}");
    assert!(
        stderr.contains("Usage: dispatch-with-waterfall.sh"),
        "{stderr}"
    );
}

/// The mandatory flag quartet every grammar case starts from.
fn base_flags<'a>(manifest: &'a str, mode: &'a str) -> Vec<&'a str> {
    vec![
        "--slots-file",
        manifest,
        "--codex-present",
        "true",
        "--cursor-present",
        "true",
        "--mode",
        mode,
    ]
}

#[test]
fn dangling_value_and_invalid_flags_exit_two() {
    let fixture = Fixture::create();
    let output = fixture.path("out.txt");
    let manifest = fixture.manifest(&[row("s1", "codex", &output, &fixture.path("prompt.txt"))]);
    let path = manifest.to_str().expect("manifest path").to_owned();
    let mut cases: Vec<(Vec<&str>, &str)> = vec![
        (vec!["--slots-file"], "--slots-file requires a value"),
        (vec!["--codex-present"], "--codex-present requires a value"),
        (
            vec!["--cursor-available"],
            "--cursor-present requires a value",
        ),
        (
            vec![
                "--slots-file",
                "/nonexistent/slots.ndjson",
                "--codex-present",
                "true",
                "--cursor-present",
                "true",
                "--mode",
                "description",
            ],
            "--slots-file must name a file",
        ),
        (
            vec![
                "--slots-file",
                &path,
                "--codex-present",
                "maybe",
                "--cursor-present",
                "true",
                "--mode",
                "description",
            ],
            "--codex-present must be true or false",
        ),
        (
            base_flags(&path, "plan-review"),
            "--mode must be diff or description",
        ),
    ];
    for (tail, expected) in [
        (
            vec!["--timeout", "0"],
            "--timeout must be a positive integer",
        ),
        (
            vec!["--site", "--sneaky"],
            "--site requires a non-empty, non-flag-like value",
        ),
        (
            vec!["--site", "bad\u{7}site"],
            "--site must not contain control characters",
        ),
        (
            vec!["--model-role", "bogus"],
            "--model-role must be default, review, vote, or fix",
        ),
        (
            vec!["--require-result-pattern", "("],
            "--require-result-pattern is not a valid ERE: (",
        ),
    ] {
        let mut arguments = base_flags(&path, "diff");
        arguments.extend(tail);
        cases.push((arguments, expected));
    }
    for (arguments, expected) in cases {
        let assert = fixture.command().args(&arguments).assert().code(2);
        let stderr = stderr_of(&assert);
        assert!(
            stderr.contains(expected),
            "expected {expected:?} in {stderr:?}"
        );
    }
    assert!(
        !fixture.path("launch-argv.log").exists(),
        "refusals must not launch"
    );
}

// ---------------------------------------------------------------------------
// Slot-row schema
// ---------------------------------------------------------------------------

#[test]
fn slot_row_schema_pins_every_field_including_prompt_file() {
    let fixture = Fixture::create();
    let output = fixture.path("full.txt");
    let prompt = fixture.path("prompt.txt");
    // The full key set one manifest row may carry. `prompt_file` is pinned here
    // because a past regression dropped it and silently disabled the panel.
    let full = format!(
        r#"{{"slot":"correctness","tool":"cursor","output":"{}","prompt_file":"{}","model_role":"review","cursor_model":"sentinel-cursor-model","prompt_files":{{"cursor":"{}"}},"payload_bytes":41,"payload_files":{{"cursor":42}}}}"#,
        output.display(),
        prompt.display(),
        prompt.display()
    );
    let manifest = fixture.manifest(&[full]);
    let assert = fixture
        .dispatch(
            &manifest,
            &[
                "--panel-artifact-dir",
                fixture.round.to_str().expect("round"),
            ],
        )
        .success();
    assert_eq!(kv(&stdout_of(&assert), "ALL_OUTPUT_TOOLS"), "cursor");
    let argv = fixture.read("launch-argv.log");
    assert!(argv.contains("--tool cursor"), "{argv}");
    assert!(
        argv.contains(&format!("--prompt-file {}", prompt.display())),
        "{argv}"
    );
    assert!(
        argv.contains("--cursor-model sentinel-cursor-model"),
        "{argv}"
    );
    assert!(
        argv.contains("--timing-task-kind cursor-phase1-correctness"),
        "{argv}"
    );
    // `prompt_files` and `payload_files` win over the scalar fields per tool.
    let environment = fixture.read("launch-env.log");
    assert!(environment.contains("payload=42"), "{environment}");
    assert!(
        environment.contains("slot=correctness|phase=phase1|tool=cursor"),
        "{environment}"
    );
    assert!(environment.contains("round=1"), "{environment}");
}

#[test]
fn a_nested_panel_artifact_dir_still_publishes_the_round_number() {
    let fixture = Fixture::create();
    // A panel artifact directory is often a child of the round directory. The
    // round number still has to reach the prompt-size ledger.
    let nested = fixture.path("aggregate");
    fs::create_dir_all(&nested).expect("nested artifact dir");
    let output = fixture.path("slot.txt");
    let manifest = fixture.manifest(&[row(
        "aggregator",
        "codex",
        &output,
        &fixture.path("prompt.txt"),
    )]);
    fixture
        .dispatch(
            &manifest,
            &["--panel-artifact-dir", nested.to_str().expect("nested")],
        )
        .success();
    let environment = fixture.read("launch-env.log");
    assert!(environment.contains("round=1"), "{environment}");
    assert!(
        environment.contains(&format!("artifact={}", nested.display())),
        "{environment}"
    );
}

#[test]
fn malformed_slot_rows_are_refused_without_launching() {
    let fixture = Fixture::create();
    let output = fixture.path("out.txt");
    let prompt = fixture.path("prompt.txt");
    let base = format!(
        r#""slot":"s1","tool":"cursor","output":"{}","prompt_file":"{}""#,
        output.display(),
        prompt.display()
    );
    let cases = [
        ("not json".to_owned(), "invalid slot row"),
        (
            format!(r#"{{"tool":"codex","output":"{}"}}"#, output.display()),
            "invalid slot row",
        ),
        (
            format!(
                r#"{{"slot":"s1","tool":"claude","output":"{}","prompt_file":"{}"}}"#,
                output.display(),
                prompt.display()
            ),
            "invalid slot row",
        ),
        (
            format!(
                r#"{{"slot":"s1","tool":"codex","output":"{}"}}"#,
                output.display()
            ),
            "must set either agent or prompt_file",
        ),
        (
            format!(
                r#"{{"slot":"s1","tool":"codex","output":"{}","prompt_file":"{}","agent":"a.md"}}"#,
                output.display(),
                prompt.display()
            ),
            "must not set both agent and prompt_file",
        ),
        (
            format!("{{{base},\"cursor_model\":\"\"}}"),
            "cursor_model must be a non-empty string",
        ),
        (
            format!("{{{base},\"cursor_model\":\"bad\\nmodel\"}}"),
            "cursor_model must not contain control characters",
        ),
        (
            format!(
                r#"{{"slot":"s1","tool":"codex","output":"{}","prompt_file":"{}","cursor_model":"m"}}"#,
                output.display(),
                prompt.display()
            ),
            "cursor_model is only valid for cursor slots",
        ),
        (
            format!("{{{base},\"model_role\":\"bogus\"}}"),
            "model_role must be default, review, vote, or fix",
        ),
        (
            format!("{{{base},\"payload_bytes\":-1}}"),
            "payload_bytes must be a non-negative integer",
        ),
        (
            format!("{{{base},\"payload_files\":{{\"cursor\":\"x\"}}}}"),
            "payload_files.cursor must be a non-negative integer",
        ),
        (
            format!("{{{base},\"payload_files\":{{}}}}"),
            "payload_files must not be empty",
        ),
        (
            format!("{{{base},\"prompt_files\":{{\"other\":\"p\"}}}}"),
            "prompt_files keys must be claude, codex, or cursor",
        ),
        (
            format!("{{{base},\"prompt_files\":[]}}"),
            "prompt_files must be an object",
        ),
        (
            format!(
                r#"{{"slot":"s1","tool":"codex","output":"a\nb","prompt_file":"{}"}}"#,
                prompt.display()
            ),
            "output path contains a newline or carriage return",
        ),
    ];
    for (bad_row, expected) in cases {
        let manifest = fixture.manifest(&[bad_row]);
        let assert = fixture.dispatch(&manifest, &[]).code(2);
        let stderr = stderr_of(&assert);
        assert!(
            stderr.contains(expected),
            "expected {expected:?} in {stderr:?}"
        );
    }
    assert!(
        !fixture.path("launch-argv.log").exists(),
        "refusals must not launch"
    );
}

#[test]
fn skip_invalid_slots_publishes_a_sidecar_and_launches_the_rest() {
    let fixture = Fixture::create();
    let good = fixture.path("good.txt");
    let manifest = fixture.manifest(&[
        "{\"slot\":\"broken\",\"tool\":\"codex\"}".to_owned(),
        row("good", "codex", &good, &fixture.path("prompt.txt")),
    ]);
    let assert = fixture
        .dispatch(&manifest, &["--skip-invalid-slots"])
        .success();
    let stdout = stdout_of(&assert);
    assert_eq!(kv(&stdout, "INVALID_SLOT_DROP_COUNT"), "1");
    assert_eq!(kv(&stdout, "WARN"), "invalid-slots-dropped");
    let sidecar = fs::read_to_string(kv(&stdout, "INVALID_SLOT_DROPS_FILE")).expect("sidecar");
    assert!(sidecar.contains("\"line\":1"), "{sidecar}");
    assert!(sidecar.contains("\"slot\":\"broken\""), "{sidecar}");
    assert_eq!(
        kv(&stdout, "ALL_OUTPUT_FILES"),
        good.to_str().expect("path")
    );
}

#[test]
fn skip_invalid_slots_with_no_valid_row_refuses() {
    let fixture = Fixture::create();
    let manifest = fixture.manifest(&["{\"slot\":\"broken\",\"tool\":\"codex\"}".to_owned()]);
    let assert = fixture
        .dispatch(&manifest, &["--skip-invalid-slots"])
        .code(2);
    assert!(stderr_of(&assert).contains("slots file contains no valid slot rows"));
}

#[test]
fn empty_manifest_refuses() {
    let fixture = Fixture::create();
    let manifest = fixture.path("empty.ndjson");
    write(&manifest, "\n");
    let assert = fixture.dispatch(&manifest, &[]).code(2);
    assert!(stderr_of(&assert).contains("slots file contains no slot rows"));
}

// ---------------------------------------------------------------------------
// Phase ordering and fallback
// ---------------------------------------------------------------------------

#[test]
fn phase_one_launches_every_slot_and_publishes_the_paths_file() {
    let fixture = Fixture::create();
    let prompt = fixture.path("prompt.txt");
    let first = fixture.path("a b.txt");
    let second = fixture.path("second.txt");
    let manifest = fixture.manifest(&[
        row("correctness", "codex", &first, &prompt),
        row("edge-cases", "cursor", &second, &prompt),
    ]);
    let assert = fixture
        .dispatch(
            &manifest,
            &["--require-result-pattern", "^[[:space:]]*## Recommendation"],
        )
        .success();
    let stdout = stdout_of(&assert);
    assert_eq!(kv(&stdout, "ALL_OUTPUT_TOOLS"), "codex cursor");
    assert_eq!(kv(&stdout, "DISPATCH_OK"), "true");
    assert_eq!(kv(&stdout, "FALLBACK_COUNT"), "0");
    assert!(
        !stdout.contains("CHILD_STDOUT"),
        "child stdout must not leak: {stdout}"
    );
    let paths = fs::read_to_string(kv(&stdout, "ALL_OUTPUT_FILES_PATH")).expect("paths file");
    assert_eq!(
        paths,
        format!("{}\n{}\n", first.display(), second.display()),
        "embedded spaces stay one path per line"
    );
    assert!(fixture.path("a b.txt.launch-stderr").is_file());
    assert!(
        !fixture.path("a b.txt.launch-stdout").exists(),
        "discarded stdout is removed"
    );
}

#[test]
fn absent_primary_tool_falls_through_to_cursor_then_claude() {
    let fixture = Fixture::create();
    let prompt = fixture.path("prompt.txt");
    let output = fixture.path("slot.txt");
    let manifest = fixture.manifest(&[row("correctness", "codex", &output, &prompt)]);
    fixture.marker("FAIL-slot-phase2.txt");
    let mut command = fixture.command();
    command.args([
        "--slots-file",
        manifest.to_str().expect("manifest"),
        "--codex-present",
        "false",
        "--cursor-present",
        "true",
        "--mode",
        "description",
        "--timeout",
        "60",
    ]);
    let assert = command.assert().success();
    let stdout = stdout_of(&assert);
    assert_eq!(kv(&stdout, "PHASE1_SLOTS"), "");
    assert_eq!(
        kv(&stdout, "PHASE2_SLOTS"),
        fixture.path("slot-phase2.txt").to_str().expect("path")
    );
    assert_eq!(
        kv(&stdout, "PHASE3_SLOTS"),
        fixture.path("slot-phase3.txt").to_str().expect("path")
    );
    assert_eq!(kv(&stdout, "FALLBACK_COUNT"), "1");
    assert_eq!(kv(&stdout, "ALL_OUTPUT_TOOLS"), "claude");
    let argv = fixture.read("launch-argv.log");
    assert!(argv.contains("--tool cursor"), "{argv}");
    assert!(argv.contains("agent launch-claude-review"), "{argv}");
}

#[test]
fn no_fallback_drops_absent_tools_and_records_every_slot() {
    let fixture = Fixture::create();
    let prompt = fixture.path("prompt.txt");
    let output = fixture.path("dyn-slot.txt");
    let manifest = fixture.manifest(&[row("dyn-alpha", "codex", &output, &prompt)]);
    let mut command = fixture.command();
    command.args([
        "--slots-file",
        manifest.to_str().expect("manifest"),
        "--codex-present",
        "false",
        "--cursor-present",
        "false",
        "--mode",
        "description",
        "--timeout",
        "60",
        "--no-fallback",
    ]);
    let assert = command.assert().success();
    let stdout = stdout_of(&assert);
    assert_eq!(kv(&stdout, "ALL_SLOTS_DROPPED"), "true");
    assert_eq!(kv(&stdout, "DYNAMIC_DISPATCH_OK"), "false");
    assert_eq!(kv(&stdout, "STATIC_DISPATCH_OK"), "true");
    let dropped = fs::read_to_string(kv(&stdout, "DROPPED_SLOTS_FILE")).expect("dropped sidecar");
    assert_eq!(
        dropped,
        "dyn-alpha\tcodex\ttool-absent\tprimary tool codex not present\n"
    );
    assert!(
        !fixture.path("launch-argv.log").exists(),
        "no tool is present"
    );
}

#[test]
fn result_gate_miss_drops_the_slot_and_preserves_a_diagnostic() {
    let fixture = Fixture::create();
    let prompt = fixture.path("prompt.txt");
    let output = fixture.path("slot.txt");
    write(&fixture.path("BODY-slot.txt"), "no verdict here\n");
    let manifest = fixture.manifest(&[row("correctness", "codex", &output, &prompt)]);
    let assert = fixture
        .dispatch(
            &manifest,
            &[
                "--no-fallback",
                "--require-result-pattern",
                "^[[:space:]]*## Recommendation",
            ],
        )
        .success();
    let stdout = stdout_of(&assert);
    assert_eq!(kv(&stdout, "ALL_OUTPUT_FILES"), "");
    let dropped = fs::read_to_string(kv(&stdout, "DROPPED_SLOTS_FILE")).expect("dropped sidecar");
    assert!(
        dropped.starts_with("correctness\tcodex\tresult-gate-miss\t"),
        "{dropped}"
    );
    assert!(
        fixture
            .path("dropped-correctness-codex-result-gate-miss.txt")
            .is_file()
    );
}

#[test]
fn collector_failure_drops_the_slot_with_a_stderr_snippet() {
    let fixture = Fixture::create();
    let prompt = fixture.path("prompt.txt");
    let output = fixture.path("slot.txt");
    fixture.marker("FAIL-slot.txt");
    let manifest = fixture.manifest(&[row("correctness", "codex", &output, &prompt)]);
    let assert = fixture.dispatch(&manifest, &["--no-fallback"]).success();
    let dropped =
        fs::read_to_string(kv(&stdout_of(&assert), "DROPPED_SLOTS_FILE")).expect("sidecar");
    assert!(
        dropped.contains("collector-failure\tSTATUS=FAILED"),
        "{dropped}"
    );
    assert!(dropped.contains("launcher stub refused"), "{dropped}");
}

#[test]
fn cap_hit_bypasses_the_result_gate() {
    let fixture = Fixture::create();
    let prompt = fixture.path("prompt.txt");
    let output = fixture.path("slot.txt");
    write(
        &fixture.path("BODY-slot.txt"),
        "STATUS=cap_hit\ntruncated body\n",
    );
    let manifest = fixture.manifest(&[row("correctness", "codex", &output, &prompt)]);
    let assert = fixture
        .dispatch(
            &manifest,
            &["--require-result-pattern", "^## Recommendation"],
        )
        .success();
    assert_eq!(kv(&stdout_of(&assert), "ALL_OUTPUT_TOOLS"), "codex");
}

#[test]
fn first_line_gate_salvages_a_preamble_and_drops_an_empty_result() {
    let fixture = Fixture::create();
    let prompt = fixture.path("prompt.txt");
    let salvage = fixture.path("salvage.txt");
    let empty = fixture.path("empty.txt");
    write(
        &fixture.path("BODY-salvage.txt"),
        "chatty preamble\n### FINDING_1: real\nbody\n",
    );
    write(&fixture.path("BODY-empty.txt"), "\n\n");
    let manifest = fixture.manifest(&[
        row("salvage", "codex", &salvage, &prompt),
        row("empty", "cursor", &empty, &prompt),
    ]);
    let assert = fixture
        .dispatch(
            &manifest,
            &[
                "--no-fallback",
                "--require-first-line-pattern",
                "^### FINDING_[0-9]+:",
            ],
        )
        .success();
    let stdout = stdout_of(&assert);
    assert_eq!(
        kv(&stdout, "ALL_OUTPUT_FILES"),
        salvage.to_str().expect("path")
    );
    assert_eq!(
        fs::read_to_string(&salvage).expect("salvaged"),
        "### FINDING_1: real\nbody\n"
    );
    let dropped = fs::read_to_string(kv(&stdout, "DROPPED_SLOTS_FILE")).expect("sidecar");
    assert!(dropped.contains("empty\tcursor\tempty\t"), "{dropped}");
}

// ---------------------------------------------------------------------------
// Forwarding, counters, and warnings
// ---------------------------------------------------------------------------

#[test]
fn codex_model_role_and_context_flags_reach_the_launcher() {
    let fixture = Fixture::create();
    let prompt = fixture.path("prompt.txt");
    let plan = fixture.path("plan.txt");
    write(&plan, "plan\n");
    let global = fixture.path("global.txt");
    let overridden = fixture.path("override.txt");
    let manifest = fixture.manifest(&[
        row("global-role", "codex", &global, &prompt),
        format!(
            r#"{{"slot":"slot-role","tool":"codex","output":"{}","prompt_file":"{}","model_role":"fix"}}"#,
            overridden.display(),
            prompt.display()
        ),
    ]);
    fixture
        .dispatch(
            &manifest,
            &[
                "--model-role",
                "vote",
                "--default-model",
                "sentinel-default",
                "--plan-file",
                plan.to_str().expect("plan"),
                "--difficulty",
                "hard",
                "--competition-notice",
                "--site",
                "review Step 9",
            ],
        )
        .success();
    let argv = fixture.read("launch-argv.log");
    let global_line = argv
        .lines()
        .find(|line| line.contains("global.txt"))
        .expect("global row launched");
    assert!(global_line.contains("--model-role vote"), "{global_line}");
    assert!(
        global_line.contains("--default-model sentinel-default"),
        "{global_line}"
    );
    assert!(global_line.contains("--difficulty hard"), "{global_line}");
    assert!(
        global_line.contains("--competition-notice"),
        "{global_line}"
    );
    assert!(
        global_line.contains("--site review Step 9"),
        "{global_line}"
    );
    let slot_line = argv
        .lines()
        .find(|line| line.contains("override.txt"))
        .expect("slot row launched");
    assert!(slot_line.contains("--model-role fix"), "{slot_line}");
}

#[test]
fn fallback_counter_accumulates_and_warns_above_the_threshold() {
    let fixture = Fixture::create();
    let prompt = fixture.path("prompt.txt");
    let counter = fixture.path("counter.txt");
    write(&counter, "2\n");
    let output = fixture.path("slot.txt");
    let manifest = fixture.manifest(&[row("correctness", "codex", &output, &prompt)]);
    let mut command = fixture.command();
    command.env("LARCH_FALLBACK_CLAUDE_WARN_THRESHOLD", "0");
    command.args([
        "--slots-file",
        manifest.to_str().expect("manifest"),
        "--codex-present",
        "false",
        "--cursor-present",
        "false",
        "--mode",
        "description",
        "--timeout",
        "60",
        "--fallback-counter-file",
        counter.to_str().expect("counter"),
        "--paths-file",
        fixture.path("explicit-paths.txt").to_str().expect("paths"),
    ]);
    let assert = command.assert().success();
    let stdout = stdout_of(&assert);
    assert_eq!(kv(&stdout, "COMBINED_FALLBACK_COUNT"), "1");
    assert_eq!(kv(&stdout, "WARN"), "cost-fallback-exceeded-threshold");
    assert_eq!(fixture.read("counter.txt"), "3\n");
    assert_eq!(
        kv(&stdout, "ALL_OUTPUT_FILES_PATH"),
        fixture.path("explicit-paths.txt").to_str().expect("paths")
    );
}

#[test]
fn a_missing_paths_file_directory_refuses_before_launching() {
    let fixture = Fixture::create();
    let prompt = fixture.path("prompt.txt");
    let output = fixture.path("slot.txt");
    let manifest = fixture.manifest(&[row("correctness", "codex", &output, &prompt)]);
    let assert = fixture
        .dispatch(&manifest, &["--paths-file", "/nonexistent-dir/paths.txt"])
        .code(2);
    assert!(stderr_of(&assert).contains("paths-file parent directory does not exist"));
    assert!(!fixture.path("launch-argv.log").exists());
}

#[test]
fn per_tool_prompt_files_select_the_phase_two_prompt() {
    let fixture = Fixture::create();
    let codex_prompt = fixture.path("codex.prompt");
    let cursor_prompt = fixture.path("cursor.prompt");
    write(&codex_prompt, "codex\n");
    write(&cursor_prompt, "cursor\n");
    let output = fixture.path("slot.txt");
    fixture.marker("FAIL-slot.txt");
    let manifest = fixture.manifest(&[format!(
        r#"{{"slot":"correctness","tool":"codex","output":"{}","prompt_files":{{"codex":"{}","cursor":"{}"}}}}"#,
        output.display(),
        codex_prompt.display(),
        cursor_prompt.display()
    )]);
    fixture.dispatch(&manifest, &[]).success();
    let argv = fixture.read("launch-argv.log");
    assert!(
        argv.contains(&format!(
            "--tool cursor --output {}",
            fixture.path("slot-phase2.txt").display()
        )),
        "{argv}"
    );
    assert!(
        argv.contains(&format!("--prompt-file {}", cursor_prompt.display())),
        "{argv}"
    );
}

#[test]
fn a_slot_without_a_claude_prompt_records_a_prompt_missing_drop() {
    let fixture = Fixture::create();
    let codex_prompt = fixture.path("codex.prompt");
    write(&codex_prompt, "codex\n");
    let output = fixture.path("slot.txt");
    fixture.marker("FAIL-slot.txt");
    let manifest = fixture.manifest(&[format!(
        r#"{{"slot":"correctness","tool":"codex","output":"{}","prompt_files":{{"codex":"{}"}}}}"#,
        output.display(),
        codex_prompt.display()
    )]);
    let mut command = fixture.command();
    command.args([
        "--slots-file",
        manifest.to_str().expect("manifest"),
        "--codex-present",
        "true",
        "--cursor-present",
        "false",
        "--mode",
        "description",
        "--timeout",
        "60",
    ]);
    let assert = command.assert().success();
    let stdout = stdout_of(&assert);
    assert_eq!(kv(&stdout, "DISPATCH_OK"), "false");
    let dropped = fs::read_to_string(kv(&stdout, "DROPPED_SLOTS_FILE")).expect("sidecar");
    assert!(
        dropped
            .contains("prompt-missing\tslot correctness has no prompt file for launch tool claude"),
        "{dropped}"
    );
}

// ---------------------------------------------------------------------------
// Straggler cutoff and interruption
// ---------------------------------------------------------------------------

#[test]
fn straggler_cutoff_drops_the_slow_slot_once_the_half_mark_lands() {
    let fixture = Fixture::create();
    let prompt = fixture.path("prompt.txt");
    let fast = fixture.path("fast.txt");
    let slow = fixture.path("slow.txt");
    fixture.marker("SLOW-slow.txt");
    let manifest = fixture.manifest(&[
        row("fast", "codex", &fast, &prompt),
        row("slow", "cursor", &slow, &prompt),
    ]);
    let mut command = fixture.command();
    command.env("LARCH_REVIEWER_STRAGGLER_FLOOR_SECONDS", "0");
    command.env("LARCH_REVIEWER_STRAGGLER_MULTIPLE", "0.1");
    command.args([
        "--slots-file",
        manifest.to_str().expect("manifest"),
        "--codex-present",
        "true",
        "--cursor-present",
        "true",
        "--mode",
        "description",
        "--timeout",
        "60",
        "--no-fallback",
        "--straggler-cutoff",
    ]);
    let assert = command.assert().success();
    let stdout = stdout_of(&assert);
    assert_eq!(kv(&stdout, "STRAGGLER_DROPPED_COUNT"), "1");
    assert_eq!(kv(&stdout, "WARN"), "reviewer-straggler-dropped");
    assert_eq!(
        kv(&stdout, "ALL_OUTPUT_FILES"),
        fast.to_str().expect("path")
    );
    let dropped = fs::read_to_string(kv(&stdout, "DROPPED_SLOTS_FILE")).expect("sidecar");
    assert!(
        dropped.contains("slow\tcursor\tstraggler-dropped\tcut at adaptive straggler deadline"),
        "{dropped}"
    );
}

#[test]
fn a_single_slot_phase_never_arms_the_straggler_cutoff() {
    let fixture = Fixture::create();
    let prompt = fixture.path("prompt.txt");
    let slow = fixture.path("slow.txt");
    fixture.marker("SLOW-slow.txt");
    let manifest = fixture.manifest(&[row("slow", "codex", &slow, &prompt)]);
    let mut command = fixture.command();
    command.env("LARCH_REVIEWER_STRAGGLER_FLOOR_SECONDS", "0");
    command.env("LARCH_REVIEWER_STRAGGLER_MULTIPLE", "0.1");
    command.args([
        "--slots-file",
        manifest.to_str().expect("manifest"),
        "--codex-present",
        "true",
        "--cursor-present",
        "true",
        "--mode",
        "description",
        "--timeout",
        "60",
        "--straggler-cutoff",
    ]);
    let assert = command.assert().success();
    let stdout = stdout_of(&assert);
    assert_eq!(kv(&stdout, "STRAGGLER_DROPPED_COUNT"), "0");
    assert_eq!(
        kv(&stdout, "ALL_OUTPUT_FILES"),
        slow.to_str().expect("path")
    );
}

#[test]
fn termination_leaves_no_orphan_slot_child() {
    let fixture = Fixture::create();
    let prompt = fixture.path("prompt.txt");
    let slow = fixture.path("slow.txt");
    // A stub that records its own pid and then sleeps well past the test.
    write_executable(
        &fixture.plugin.join("scripts/larch.sh"),
        r#"#!/usr/bin/env bash
set -uo pipefail
out=""
prev=""
for arg in "$@"; do
  if [[ "$prev" == "--output" ]]; then out="$arg"; fi
  prev="$arg"
done
pid_path="$(dirname "$out")/child.pid"
pid_tmp="${pid_path}.$$"
printf '%s\n' "$$" > "$pid_tmp"
mv "$pid_tmp" "$pid_path"
sleep 120
"#,
    );
    let manifest = fixture.manifest(&[row("slow", "codex", &slow, &prompt)]);
    let mut child = Command::new(assert_cmd::cargo::cargo_bin("larch"))
        .args([
            "agent",
            "dispatch-waterfall",
            "--slots-file",
            manifest.to_str().expect("manifest"),
            "--codex-present",
            "true",
            "--cursor-present",
            "true",
            "--mode",
            "description",
            "--timeout",
            "600",
        ])
        .env("CLAUDE_PLUGIN_ROOT", &fixture.plugin)
        .current_dir(&fixture.round)
        .spawn()
        .expect("spawn dispatcher");
    let pid_path = fixture.path("child.pid");
    let mut waited = Duration::ZERO;
    while !pid_path.is_file() && waited < Duration::from_secs(30) {
        std::thread::sleep(Duration::from_millis(50));
        waited += Duration::from_millis(50);
    }
    let pid: i32 = fs::read_to_string(&pid_path)
        .expect("child pid")
        .trim()
        .parse()
        .expect("numeric pid");
    let _terminated = Command::new("kill")
        .args(["-TERM", &child.id().to_string()])
        .status()
        .expect("signal dispatcher");
    let status = child.wait().expect("dispatcher exit");
    assert_eq!(status.code(), Some(143), "terminated dispatch reports 143");
    let mut alive = Duration::ZERO;
    while alive < Duration::from_secs(10) && process_alive(pid) {
        std::thread::sleep(Duration::from_millis(50));
        alive += Duration::from_millis(50);
    }
    assert!(
        !process_alive(pid),
        "slot child {pid} outlived the dispatcher"
    );
}

fn process_alive(pid: i32) -> bool {
    Command::new("kill")
        .args(["-0", &pid.to_string()])
        .status()
        .is_ok_and(|status| status.success())
}

// ---------------------------------------------------------------------------
// Retired-behavior guard
// ---------------------------------------------------------------------------

/// The grouped-reuse experiment was removed; nothing may reintroduce it.
#[test]
fn dispatcher_carries_no_grouped_reuse_machinery() {
    let root = repository_root();
    let dispatcher = fs::read_to_string(root.join("crates/larch-cli/src/waterfall_commands.rs"))
        .expect("dispatcher source");
    for symbol in [
        "reuse_slot_result",
        "find_group_ok_for_tool",
        "append_group_ledger_ok",
        "GROUP_LEDGER",
        "REUSED_INDICES",
        "idx_was_reused",
        "has_fallback_groups",
        "DEDUPE_REUSED",
        "phase2_grouped",
        concat!("fallback_", "group"),
        concat!("waterfall-", "group-results"),
    ] {
        assert!(
            !dispatcher.contains(symbol),
            "retired grouped-reuse symbol {symbol}"
        );
    }
    let token = concat!("fallback_", "group");
    let mut hits = Vec::new();
    for directory in ["skills", "scripts"] {
        collect_token_hits(&root.join(directory), token, &mut hits);
    }
    assert!(hits.is_empty(), "grouped-reuse token survives in {hits:?}");
}

fn collect_token_hits(directory: &Path, token: &str, hits: &mut Vec<String>) {
    let Ok(entries) = fs::read_dir(directory) else {
        return;
    };
    for entry in entries.flatten() {
        let path = entry.path();
        if path.is_dir() {
            collect_token_hits(&path, token, hits);
            continue;
        }
        let name = path
            .file_name()
            .unwrap_or_default()
            .to_string_lossy()
            .into_owned();
        if path.extension().is_some_and(|suffix| suffix == "md")
            || (name.starts_with("test-") && path.extension().is_some_and(|suffix| suffix == "sh"))
        {
            continue;
        }
        if fs::read_to_string(&path).is_ok_and(|text| text.contains(token)) {
            hits.push(path.display().to_string());
        }
    }
}
