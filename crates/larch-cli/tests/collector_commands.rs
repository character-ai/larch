//! End-to-end coverage for `agent collect-results`.
//!
//! Every case runs the real command against a fixture plugin root. A retry
//! re-enters the verified bootstrap, so `scripts/larch.sh` is a shell stub that
//! publishes the retry artifacts a launcher would; the content validators are a
//! stub `python/cli.py` reached through the delegated-verb seam.

#![cfg(unix)]

use std::{
    fs,
    os::unix::fs::PermissionsExt as _,
    path::{Path, PathBuf},
};

use assert_cmd::Command as AssertCommand;
use tempfile::TempDir;

/// The retry launcher stub: publishes whatever the marker files ask for.
const LAUNCHER_STUB: &str = r#"#!/usr/bin/env bash
set -uo pipefail
out=""
prev=""
for arg in "$@"; do
  if [[ "$prev" == "--output" ]]; then out="$arg"; fi
  prev="$arg"
done
dir="$(dirname "$out")"
printf '%s\n' "$*" >> "$dir/retry-argv.log"
if [[ -f "$dir/RETRY-SILENT" ]]; then exit 0; fi
if [[ -f "$dir/RETRY-FAIL" ]]; then
  printf 'retry launcher refused\n' > "$out.diag"
  printf '7\n' > "$out.done"
  exit 7
fi
if [[ -f "$dir/RETRY-EMPTY" ]]; then
  printf '0\n' > "$out.done"
  exit 0
fi
printf 'retry body\n' > "$out"
printf '0\n' > "$out.done"
"#;

/// The content-validator stub, reached through the delegated-verb seam.
const VALIDATOR_STUB: &str = r#"import os
import sys

arguments = sys.argv[1:]
target = arguments[-1]
directory = os.path.dirname(target)
if "--write-structured" in arguments:
    sidecar = arguments[arguments.index("--write-structured") + 1]
    if os.path.exists(os.path.join(directory, "STRUCTURED-FAIL")):
        sys.stdout.write("structured refusal\n")
        sys.exit(5)
    with open(sidecar, "w", encoding="utf-8") as handle:
        handle.write("scope\tseverity\n")
    if os.path.exists(os.path.join(directory, "STRUCTURED-RECOVERED")):
        sys.stdout.write("NO_ISSUES_SENTINEL_RECOVERED_AFTER_PREAMBLE\n")
    sys.exit(0)
if os.path.exists(os.path.join(directory, "SUBSTANTIVE-EMPTY")):
    sys.stdout.write("cursor produced nothing\n")
    sys.exit(5)
if os.path.exists(os.path.join(directory, "SUBSTANTIVE-THIN")):
    sys.stdout.write("too thin | for review\n")
    sys.exit(2)
sys.exit(0)
"#;

fn write(path: &Path, contents: &str) {
    fs::create_dir_all(path.parent().expect("fixture parent")).expect("create fixture parent");
    fs::write(path, contents).expect("write fixture");
}

fn write_executable(path: &Path, contents: &str) {
    write(path, contents);
    fs::set_permissions(path, fs::Permissions::from_mode(0o755)).expect("fixture permissions");
}

/// One collection fixture: a plugin root plus a reviewer working directory.
struct Fixture {
    _root: TempDir,
    plugin: PathBuf,
    work: PathBuf,
}

impl Fixture {
    fn create() -> Self {
        // `/tmp` rather than the platform temp root: the plugin-root validator
        // rejects a path with characters the sandbox root can contain.
        let root = TempDir::new_in("/tmp").expect("fixture root");
        let plugin = root.path().join("plugin");
        let work = root.path().join("work");
        write_executable(&plugin.join("scripts/larch.sh"), LAUNCHER_STUB);
        write(&plugin.join("python/cli.py"), VALIDATOR_STUB);
        fs::create_dir_all(&work).expect("work directory");
        Self {
            _root: root,
            plugin,
            work,
        }
    }

    fn path(&self, name: &str) -> PathBuf {
        self.work.join(name)
    }

    fn text(&self, name: &str) -> String {
        self.path(name).display().to_string()
    }

    fn marker(&self, name: &str) {
        write(&self.path(name), "");
    }

    fn write(&self, name: &str, contents: &str) {
        write(&self.path(name), contents);
    }

    fn read(&self, name: &str) -> String {
        fs::read_to_string(self.path(name)).unwrap_or_default()
    }

    /// Publish one reviewer launch: its output body and its `.done` sentinel.
    fn launch(&self, name: &str, exit_code: &str, body: Option<&str>) {
        if let Some(body) = body {
            self.write(name, body);
        }
        self.write(&format!("{name}.done"), &format!("{exit_code}\n"));
    }

    fn command(&self) -> AssertCommand {
        let mut command = AssertCommand::cargo_bin("larch").expect("larch binary should build");
        command
            .current_dir(&self.work)
            .env("CLAUDE_PLUGIN_ROOT", &self.plugin)
            .env("WAIT_FOR_REVIEWERS_POLL_INTERVAL", "1")
            .args(["agent", "collect-results"]);
        command
    }

    fn collect(&self, arguments: &[&str]) -> assert_cmd::assert::Assert {
        let mut command = self.command();
        command.args(arguments);
        command.assert()
    }
}

fn stdout_of(assert: &assert_cmd::assert::Assert) -> String {
    String::from_utf8_lossy(&assert.get_output().stdout).into_owned()
}

fn stderr_of(assert: &assert_cmd::assert::Assert) -> String {
    String::from_utf8_lossy(&assert.get_output().stderr).into_owned()
}

/// Read one field from the record whose `REVIEWER_FILE` block contains it.
fn field(stdout: &str, block: usize, key: &str) -> String {
    let blocks: Vec<&str> = stdout
        .split("\n\n")
        .filter(|part| !part.is_empty())
        .collect();
    let Some(text) = blocks.get(block) else {
        return String::new();
    };
    text.lines()
        .find_map(|line| line.strip_prefix(&format!("{key}=")))
        .unwrap_or_default()
        .to_owned()
}

// ---------------------------------------------------------------------------
// Argument grammar
// ---------------------------------------------------------------------------

#[test]
fn help_prints_usage_and_succeeds() {
    let fixture = Fixture::create();
    let assert = fixture.collect(&["--help"]).success();
    assert!(stderr_of(&assert).contains("Usage: larch agent collect-results"));
}

#[test]
fn argument_errors_exit_one() {
    let fixture = Fixture::create();
    let output = fixture.text("a.txt");
    for (arguments, needle) in [
        (vec!["--timeout"], "--timeout requires a value"),
        (
            vec!["--timeout", "0", "a.txt"],
            "must be a positive integer",
        ),
        (
            vec!["--timeout", "abc", "a.txt"],
            "must be a positive integer",
        ),
        (
            vec!["--timeout", "1"],
            "at least one output file is required",
        ),
        (vec!["--timeout", "1", "--bogus"], "unknown option: --bogus"),
        (vec!["--paths-file"], "--paths-file requires a value"),
    ] {
        let assert = fixture.collect(&arguments).code(1);
        assert!(stderr_of(&assert).contains(needle), "{needle}");
    }
    let missing = fixture.text("absent-paths.txt");
    let assert = fixture
        .collect(&["--timeout", "1", "--paths-file", &missing])
        .code(1);
    assert!(stderr_of(&assert).contains("paths-file not readable"));

    let directory = fixture.text("dir-paths");
    fs::create_dir_all(&directory).expect("paths directory");
    let assert = fixture
        .collect(&["--timeout", "1", "--paths-file", &directory])
        .code(1);
    assert!(stderr_of(&assert).contains("is not a regular file"));

    fixture.write("blank-paths.txt", "\n   \n");
    let blank = fixture.text("blank-paths.txt");
    let assert = fixture
        .collect(&["--timeout", "1", "--paths-file", &blank])
        .code(1);
    assert!(stderr_of(&assert).contains("contains no entries"));

    fixture.write("paths.txt", &format!("{output}\n"));
    let paths = fixture.text("paths.txt");
    let assert = fixture
        .collect(&["--timeout", "1", "--paths-file", &paths, &output])
        .code(1);
    assert!(stderr_of(&assert).contains("mutually exclusive"));
}

#[test]
fn a_paths_file_supplies_the_output_list() {
    let fixture = Fixture::create();
    fixture.launch("codex-review.txt", "0", Some("findings\n"));
    fixture.write(
        "paths.txt",
        &format!("{}\n\n", fixture.text("codex-review.txt")),
    );
    let paths = fixture.text("paths.txt");
    let assert = fixture
        .collect(&["--timeout", "5", "--paths-file", &paths])
        .success();
    let stdout = stdout_of(&assert);
    assert_eq!(field(&stdout, 0, "STATUS"), "OK");
    assert_eq!(field(&stdout, 0, "TOOL"), "codex");
}

// ---------------------------------------------------------------------------
// Classification
// ---------------------------------------------------------------------------

#[test]
fn every_terminal_status_is_classified_from_its_sentinel() {
    let fixture = Fixture::create();
    fixture.launch("cursor-ok.txt", "0", Some("findings\n"));
    fixture.launch("cursor-timeout.txt", "124", None);
    fixture.launch("codex-failed.txt", "3", None);
    fixture.write("codex-failed.txt.diag", "codex exploded\n");
    fixture.write("cursor-missing.txt", "unused\n");
    fixture.launch("cursor-cap.txt", "0", Some("STATUS=cap_hit\nrest\n"));
    fixture.launch(
        "cursor-degraded.txt",
        "0",
        Some("\nCURSOR_EMPTY_RESPONSE\n"),
    );
    let arguments = [
        "--timeout".to_owned(),
        "1".to_owned(),
        fixture.text("cursor-ok.txt"),
        fixture.text("cursor-timeout.txt"),
        fixture.text("codex-failed.txt"),
        fixture.text("cursor-missing.txt"),
        fixture.text("cursor-cap.txt"),
        fixture.text("cursor-degraded.txt"),
    ];
    let borrowed: Vec<&str> = arguments.iter().map(String::as_str).collect();
    let assert = fixture.collect(&borrowed).success();
    let stdout = stdout_of(&assert);
    assert_eq!(field(&stdout, 0, "STATUS"), "OK");
    assert_eq!(field(&stdout, 0, "EXIT_CODE"), "0");
    assert_eq!(field(&stdout, 1, "STATUS"), "TIMED_OUT");
    assert_eq!(
        field(&stdout, 1, "FAILURE_REASON"),
        "Process timed out (exit code 124)"
    );
    assert_eq!(field(&stdout, 2, "STATUS"), "FAILED");
    assert_eq!(field(&stdout, 2, "FAILURE_REASON"), "codex exploded");
    assert_eq!(field(&stdout, 3, "STATUS"), "SENTINEL_TIMEOUT");
    assert_eq!(field(&stdout, 3, "EXIT_CODE"), "124");
    assert!(field(&stdout, 3, "FAILURE_REASON").contains("sentinel file missing"));
    assert_eq!(field(&stdout, 4, "STATUS"), "cap_hit");
    assert_eq!(
        field(&stdout, 4, "FAILURE_REASON"),
        "Token budget cap hit; reviewer skipped"
    );
    assert_eq!(field(&stdout, 5, "STATUS"), "CURSOR_EMPTY_RESPONSE");
}

#[test]
fn an_unusable_sentinel_with_no_output_becomes_empty_output() {
    let fixture = Fixture::create();
    fixture.write("cursor-bad.txt.done", "not-a-number\n");
    let output = fixture.text("cursor-bad.txt");
    let assert = fixture.collect(&["--timeout", "1", &output]).success();
    let stdout = stdout_of(&assert);
    assert_eq!(field(&stdout, 0, "STATUS"), "EMPTY_OUTPUT");
    assert_eq!(field(&stdout, 0, "EXIT_CODE"), "99");
    assert!(stderr_of(&assert).contains("invalid exit code from initial sentinel"));
}

#[test]
fn an_unusable_sentinel_with_output_stays_failed() {
    let fixture = Fixture::create();
    fixture.launch("cursor-bad.txt", "999", Some("body\n"));
    let output = fixture.text("cursor-bad.txt");
    let assert = fixture.collect(&["--timeout", "1", &output]).success();
    let stdout = stdout_of(&assert);
    assert_eq!(field(&stdout, 0, "STATUS"), "FAILED");
    assert_eq!(field(&stdout, 0, "EXIT_CODE"), "99");
}

#[test]
fn the_meta_tool_outranks_the_basename() {
    let fixture = Fixture::create();
    fixture.launch("reviewer.txt", "0", Some("findings\n"));
    fixture.write("reviewer.txt.meta", "TOOL=bogus\nTOOL=cursor\n");
    let output = fixture.text("reviewer.txt");
    let assert = fixture.collect(&["--timeout", "5", &output]).success();
    assert_eq!(field(&stdout_of(&assert), 0, "TOOL"), "cursor");
}

#[test]
fn an_unattributable_output_reports_the_unknown_tool() {
    let fixture = Fixture::create();
    fixture.launch("reviewer.txt", "0", Some("findings\n"));
    let output = fixture.text("reviewer.txt");
    let assert = fixture.collect(&["--timeout", "5", &output]).success();
    assert_eq!(field(&stdout_of(&assert), 0, "TOOL"), "unknown");
}

#[test]
fn summary_only_publishes_four_fields_and_no_excerpt() {
    let fixture = Fixture::create();
    fixture.launch("cursor-review.txt", "3", None);
    fixture.write("cursor-review.txt.stderr-tail", "boom\n");
    let output = fixture.text("cursor-review.txt");
    let assert = fixture
        .collect(&["--timeout", "1", "--summary-only", &output])
        .success();
    let stdout = stdout_of(&assert);
    assert!(!stdout.contains("STRUCTURED_SIDECAR="), "{stdout}");
    assert!(!stdout.contains("FAILURE_REASON="), "{stdout}");
    assert!(!stderr_of(&assert).contains("failed agent stderr tail"));
}

// ---------------------------------------------------------------------------
// Retries
// ---------------------------------------------------------------------------

fn cmd_json_meta(output: &str) -> String {
    format!(
        "TOOL=cursor\nTIMEOUT=5\nOUTPUT_FILE={output}\nCMD_JSON=[\"/usr/bin/cursor\", \"agent\", \"--workspace\", \"/tmp\", \"{output}\"]\n"
    )
}

#[test]
fn an_empty_output_with_metadata_retries_and_publishes_the_retry() {
    let fixture = Fixture::create();
    fixture.launch("cursor-review.txt", "0", None);
    let output = fixture.text("cursor-review.txt");
    fixture.write("cursor-review.txt.meta", &cmd_json_meta(&output));
    fixture.write("cursor-review.txt.stderr-tail", "first attempt noise\n");
    let assert = fixture.collect(&["--timeout", "1", &output]).success();
    let stdout = stdout_of(&assert);
    assert_eq!(field(&stdout, 0, "STATUS"), "OK");
    assert_eq!(
        field(&stdout, 0, "REVIEWER_FILE"),
        fixture.text("cursor-review-retry.txt")
    );
    let argv = fixture.read("retry-argv.log");
    assert!(
        argv.contains("agent run-external-agent --tool cursor"),
        "{argv}"
    );
    assert!(
        argv.contains(&fixture.text("cursor-review-retry.txt")),
        "{argv}"
    );
    assert!(!fixture.path("cursor-review.txt.stderr-tail").exists());
}

#[test]
fn a_failed_retry_reports_the_second_failure() {
    let fixture = Fixture::create();
    fixture.marker("RETRY-FAIL");
    fixture.launch("cursor-review.txt", "0", None);
    let output = fixture.text("cursor-review.txt");
    fixture.write("cursor-review.txt.meta", &cmd_json_meta(&output));
    let assert = fixture.collect(&["--timeout", "1", &output]).success();
    let stdout = stdout_of(&assert);
    assert_eq!(field(&stdout, 0, "STATUS"), "EMPTY_OUTPUT");
    assert_eq!(field(&stdout, 0, "EXIT_CODE"), "7");
    assert!(
        field(&stdout, 0, "FAILURE_REASON")
            .starts_with("Retry also failed: retry launcher refused"),
        "{stdout}"
    );
}

#[test]
fn a_retry_that_never_completes_reports_a_missing_sentinel() {
    let fixture = Fixture::create();
    fixture.marker("RETRY-SILENT");
    fixture.launch("cursor-review.txt", "0", None);
    let output = fixture.text("cursor-review.txt");
    fixture.write("cursor-review.txt.meta", &cmd_json_meta(&output));
    let assert = fixture.collect(&["--timeout", "1", &output]).success();
    let stdout = stdout_of(&assert);
    assert_eq!(field(&stdout, 0, "STATUS"), "EMPTY_OUTPUT");
    assert_eq!(field(&stdout, 0, "EXIT_CODE"), "99");
    assert_eq!(
        field(&stdout, 0, "FAILURE_REASON"),
        "Retry process did not complete (sentinel file missing)"
    );
}

#[test]
fn a_transient_diagnostic_retries_a_failed_reviewer() {
    let fixture = Fixture::create();
    fixture.launch("cursor-review.txt", "3", None);
    let output = fixture.text("cursor-review.txt");
    fixture.write(
        "cursor-review.txt.diag",
        "fatal: Could not resolve host: api\n",
    );
    fixture.write("cursor-review.txt.meta", &cmd_json_meta(&output));
    let assert = fixture.collect(&["--timeout", "1", &output]).success();
    assert_eq!(field(&stdout_of(&assert), 0, "STATUS"), "OK");
    assert!(
        stderr_of(&assert).contains("transient diagnostic for cursor-review.txt; retrying once")
    );
}

#[test]
fn invalid_retry_metadata_fails_closed() {
    let fixture = Fixture::create();
    let cases: Vec<(&str, String, &str)> = vec![
        ("no-timeout", "TOOL=cursor\n".to_owned(), "TIMEOUT missing"),
        (
            "bad-timeout",
            "TOOL=cursor\nTIMEOUT=zero\n".to_owned(),
            "TIMEOUT not a positive integer",
        ),
        (
            "no-cmd",
            "TOOL=cursor\nTIMEOUT=5\n".to_owned(),
            "missing CMD_JSON",
        ),
        (
            "no-tool",
            "TIMEOUT=5\nCMD_JSON=[\"cursor\"]\n".to_owned(),
            "missing TOOL",
        ),
        (
            "no-both",
            "TIMEOUT=5\n".to_owned(),
            "missing CMD_JSON and TOOL",
        ),
        (
            "bad-json",
            "TOOL=cursor\nTIMEOUT=5\nCMD_JSON=[1]\n".to_owned(),
            "malformed CMD_JSON",
        ),
        (
            "bad-shape",
            "TOOL=cursor\nTIMEOUT=5\nCMD_JSON=[\"cursor\",\"agent\"]\n".to_owned(),
            "CMD_JSON argv shape rejected for cursor",
        ),
        (
            "unknown-tool",
            "TOOL=claude\nTIMEOUT=5\nCMD_JSON=[\"claude\"]\n".to_owned(),
            "unknown TOOL for CMD_JSON",
        ),
        (
            "escape",
            "TOOL=cursor\nTIMEOUT=5\nSTDERR_SINK=../escape\nCMD_JSON=[\"cursor\",\"agent\",\"--workspace\",\"/tmp\",\"go\"]\n"
                .to_owned(),
            "STDERR_SINK contains ..",
        ),
    ];
    for (name, meta, needle) in cases {
        let output_name = format!("cursor-{name}.txt");
        fixture.launch(&output_name, "0", None);
        fixture.write(&format!("{output_name}.meta"), &meta);
        let output = fixture.text(&output_name);
        let assert = fixture.collect(&["--timeout", "1", &output]).success();
        let stdout = stdout_of(&assert);
        assert_eq!(field(&stdout, 0, "STATUS"), "EMPTY_OUTPUT", "{name}");
        assert_eq!(field(&stdout, 0, "EXIT_CODE"), "99", "{name}");
        assert!(
            field(&stdout, 0, "FAILURE_REASON").contains(needle),
            "{name}: {stdout}"
        );
    }
}

#[test]
fn a_review_shaped_argv_without_launcher_metadata_is_refused() {
    let fixture = Fixture::create();
    fixture.launch("cursor-review.txt", "0", None);
    let output = fixture.text("cursor-review.txt");
    fixture.write(
        "cursor-review.txt.meta",
        &format!(
            "TOOL=cursor\nTIMEOUT=5\nCMD_JSON=[\"cursor\",\"agent\",\"--mode\",\"agent\",\"--mode\",\"ask\",\"--workspace\",\"/tmp\",\"go\"]\nOUTPUT_FILE={output}\n"
        ),
    );
    let assert = fixture.collect(&["--timeout", "1", &output]).success();
    assert!(
        field(&stdout_of(&assert), 0, "FAILURE_REASON")
            .contains("review-shaped CMD_JSON requires outer launcher metadata"),
        "{}",
        stdout_of(&assert)
    );
}

#[test]
fn an_outer_launcher_retry_re_enters_launch_review() {
    let fixture = Fixture::create();
    fixture.launch("codex-review.txt", "0", None);
    let output = fixture.text("codex-review.txt");
    fixture.write("codex-review.txt.prompt", "prompt body\n");
    fixture.write(
        "codex-review.txt.meta",
        &format!(
            "TOOL=codex\nTIMEOUT=5\nOUTER_LAUNCHER=agent launch-review\nOUTER_LAUNCHER_PROMPT_FILE={output}.prompt\nOUTER_LAUNCHER_WORKDIR={}\nOUTER_LAUNCHER_RISK=low\nOUTER_LAUNCHER_MODEL_ROLE=review\nOUTER_LAUNCHER_SITE=design Step 3\nOUTER_LAUNCHER_TIMING_KIND=codex-review\n",
            fixture.work.display()
        ),
    );
    let assert = fixture.collect(&["--timeout", "1", &output]).success();
    assert_eq!(field(&stdout_of(&assert), 0, "STATUS"), "OK");
    let argv = fixture.read("retry-argv.log");
    assert!(argv.contains("agent launch-review --tool codex"), "{argv}");
    assert!(argv.contains("--risk low"), "{argv}");
    assert!(argv.contains("--model-role review"), "{argv}");
    assert!(argv.contains("--site design Step 3"), "{argv}");
    assert!(argv.contains("--timing-task-kind codex-review"), "{argv}");
}

#[test]
fn an_outer_launcher_retry_re_enters_launch_codex_exec() {
    let fixture = Fixture::create();
    fixture.launch("codex-exec.txt", "0", None);
    let output = fixture.text("codex-exec.txt");
    fixture.write("codex-exec.txt.prompt", "prompt body\n");
    fixture.write(
        "codex-exec.txt.meta",
        &format!(
            "TOOL=codex\nTIMEOUT=5\nOUTER_LAUNCHER=agent launch-codex-exec\nOUTER_LAUNCHER_KIND=codex-exec\nOUTER_LAUNCHER_PROMPT_FILE={output}.prompt\nOUTER_LAUNCHER_WORKDIR={work}\nOUTER_LAUNCHER_SANDBOX=read-only\nOUTER_LAUNCHER_WITH_EFFORT=true\nOUTER_LAUNCHER_USAGE_LABEL=design-scout\nOUTER_LAUNCHER_TIMING_KIND=codex-scout\nOUTER_LAUNCHER_ADD_DIRS_JSON=[\"{work}\"]\n",
            work = fixture.work.display()
        ),
    );
    let assert = fixture.collect(&["--timeout", "1", &output]).success();
    assert_eq!(field(&stdout_of(&assert), 0, "STATUS"), "OK");
    let argv = fixture.read("retry-argv.log");
    assert!(argv.contains("agent launch-codex-exec"), "{argv}");
    assert!(argv.contains("--sandbox read-only"), "{argv}");
    assert!(argv.contains("--with-effort"), "{argv}");
    assert!(argv.contains("--usage-label design-scout"), "{argv}");
    assert!(argv.contains("--model-role default"), "{argv}");
    assert!(
        argv.contains(&format!("--add-dir {}", fixture.work.display())),
        "{argv}"
    );
}

#[test]
fn invalid_outer_launcher_metadata_fails_closed() {
    let fixture = Fixture::create();
    let work = fixture.work.display().to_string();
    let cases: Vec<(&str, String, &str)> = vec![
        (
            "retired",
            "OUTER_LAUNCHER=/opt/larch/launch-review.sh\nOUTER_LAUNCHER_PROMPT_FILE=P.prompt\nOUTER_LAUNCHER_WORKDIR=W\n"
                .to_owned(),
            "retired review OUTER_LAUNCHER metadata is no longer accepted",
        ),
        (
            "unknown",
            "OUTER_LAUNCHER=agent launch-nothing\nOUTER_LAUNCHER_PROMPT_FILE=P.prompt\nOUTER_LAUNCHER_WORKDIR=W\n"
                .to_owned(),
            "OUTER_LAUNCHER not canonical",
        ),
        (
            "escape",
            "OUTER_LAUNCHER=../agent launch-review\nOUTER_LAUNCHER_PROMPT_FILE=P.prompt\nOUTER_LAUNCHER_WORKDIR=W\n"
                .to_owned(),
            "OUTER_LAUNCHER contains ..",
        ),
        (
            "no-prompt",
            "OUTER_LAUNCHER=agent launch-review\nOUTER_LAUNCHER_WORKDIR=W\n".to_owned(),
            "missing OUTER_LAUNCHER_PROMPT_FILE",
        ),
        (
            "no-workdir",
            "OUTER_LAUNCHER=agent launch-review\nOUTER_LAUNCHER_PROMPT_FILE=P.prompt\n".to_owned(),
            "missing OUTER_LAUNCHER_WORKDIR",
        ),
        (
            "wrong-prompt",
            format!(
                "OUTER_LAUNCHER=agent launch-review\nOUTER_LAUNCHER_PROMPT_FILE={work}/other.prompt\nOUTER_LAUNCHER_WORKDIR={work}\n"
            ),
            "OUTER_LAUNCHER_PROMPT_FILE not the expected sidecar",
        ),
        (
            "no-launcher",
            format!(
                "OUTER_LAUNCHER_PROMPT_FILE={work}/x.prompt\nOUTER_LAUNCHER_WORKDIR={work}\n"
            ),
            "missing OUTER_LAUNCHER",
        ),
    ];
    for (name, extra, needle) in cases {
        let output_name = format!("codex-{name}.txt");
        fixture.launch(&output_name, "0", None);
        let output = fixture.text(&output_name);
        fixture.write(
            &format!("{output_name}.meta"),
            &format!("TOOL=codex\nTIMEOUT=5\n{extra}"),
        );
        let assert = fixture.collect(&["--timeout", "1", &output]).success();
        let stdout = stdout_of(&assert);
        assert!(
            field(&stdout, 0, "FAILURE_REASON").contains(needle),
            "{name}: {stdout}"
        );
    }
}

#[test]
fn an_absent_prompt_sidecar_refuses_the_outer_retry() {
    let fixture = Fixture::create();
    fixture.launch("codex-review.txt", "0", None);
    let output = fixture.text("codex-review.txt");
    fixture.write(
        "codex-review.txt.meta",
        &format!(
            "TOOL=codex\nTIMEOUT=5\nOUTER_LAUNCHER=agent launch-review\nOUTER_LAUNCHER_PROMPT_FILE={output}.prompt\nOUTER_LAUNCHER_WORKDIR={}\n",
            fixture.work.display()
        ),
    );
    let assert = fixture.collect(&["--timeout", "1", &output]).success();
    assert!(
        field(&stdout_of(&assert), 0, "FAILURE_REASON")
            .contains("not a readable regular non-symlink file"),
        "{}",
        stdout_of(&assert)
    );
}

#[test]
fn a_missing_workdir_refuses_the_outer_retry() {
    let fixture = Fixture::create();
    fixture.launch("codex-review.txt", "0", None);
    let output = fixture.text("codex-review.txt");
    fixture.write("codex-review.txt.prompt", "prompt\n");
    fixture.write(
        "codex-review.txt.meta",
        &format!(
            "TOOL=codex\nTIMEOUT=5\nOUTER_LAUNCHER=agent launch-review\nOUTER_LAUNCHER_PROMPT_FILE={output}.prompt\nOUTER_LAUNCHER_WORKDIR={}/absent\n",
            fixture.work.display()
        ),
    );
    let assert = fixture.collect(&["--timeout", "1", &output]).success();
    assert!(
        field(&stdout_of(&assert), 0, "FAILURE_REASON")
            .contains("OUTER_LAUNCHER_WORKDIR not a directory"),
        "{}",
        stdout_of(&assert)
    );
}

// ---------------------------------------------------------------------------
// Content validation
// ---------------------------------------------------------------------------

#[test]
fn structured_validation_publishes_a_sidecar_and_records_recovery() {
    let fixture = Fixture::create();
    // A preamble line before a single no-issues sentinel drives the real
    // validator's recovered-after-preamble warning and empty wire file.
    fixture.launch(
        "cursor-review.txt",
        "0",
        Some("some preamble line\nNO_ISSUES_FOUND\n"),
    );
    let output = fixture.text("cursor-review.txt");
    let assert = fixture
        .collect(&[
            "--timeout",
            "5",
            "--structured-reviewer-validation",
            &output,
        ])
        .success();
    let stdout = stdout_of(&assert);
    assert_eq!(
        field(&stdout, 0, "STRUCTURED_SIDECAR"),
        format!("{output}.tsv")
    );
    assert!(fixture.path("cursor-review.txt.tsv").is_file());
    assert!(stderr_of(&assert).contains("recovered a no-issues sentinel after preamble"));
}

#[test]
fn a_refused_structured_validation_drops_the_reviewer() {
    let fixture = Fixture::create();
    // Free-text reviewer output normalizes to nothing and is not a sentinel, so
    // the real structured validator refuses with exit 5.
    fixture.launch("cursor-review.txt", "0", Some("findings\n"));
    let output = fixture.text("cursor-review.txt");
    let assert = fixture
        .collect(&[
            "--timeout",
            "5",
            "--structured-reviewer-validation",
            &output,
        ])
        .success();
    let stdout = stdout_of(&assert);
    assert_eq!(field(&stdout, 0, "STATUS"), "NOT_SUBSTANTIVE");
    assert_eq!(field(&stdout, 0, "NS_RETRY_MODE"), "structured");
    assert_eq!(field(&stdout, 0, "NS_RETRY_REASON"), "JSON_PARSE_FAIL");
    assert_eq!(
        field(&stdout, 0, "FAILURE_REASON"),
        "structured records not found after repair"
    );
    assert!(stderr_of(&assert).contains("dropping NOT_SUBSTANTIVE reviewer"));
}

#[test]
fn substantive_validation_classifies_thin_and_empty_reviewers() {
    let thin = Fixture::create();
    // One word in short-reviewer mode is below the 30-word floor.
    thin.launch("cursor-review.txt", "0", Some("findings\n"));
    let output = thin.text("cursor-review.txt");
    let assert = thin
        .collect(&[
            "--timeout",
            "5",
            "--substantive-validation",
            "--validation-mode",
            &output,
        ])
        .success();
    let stdout = stdout_of(&assert);
    assert_eq!(field(&stdout, 0, "STATUS"), "NOT_SUBSTANTIVE");
    assert_eq!(field(&stdout, 0, "NS_RETRY_MODE"), "substantive");
    assert_eq!(
        field(&stdout, 0, "NS_RETRY_REASON"),
        "NO_ISSUES_FOUND_TOO_THIN"
    );
    assert_eq!(
        field(&stdout, 0, "FAILURE_REASON"),
        "body too thin: 1/30 words after stripping fenced code"
    );

    let empty = Fixture::create();
    // The Cursor empty sentinel drives the validator's exit-5 empty response.
    empty.launch("cursor-review.txt", "0", Some("CURSOR_EMPTY_RESPONSE\n"));
    let output = empty.text("cursor-review.txt");
    let assert = empty
        .collect(&[
            "--timeout",
            "5",
            "--substantive-validation",
            "--validation-mode",
            &output,
        ])
        .success();
    let stdout = stdout_of(&assert);
    assert_eq!(field(&stdout, 0, "STATUS"), "CURSOR_EMPTY_RESPONSE");
    assert_eq!(field(&stdout, 0, "NS_RETRY_MODE"), "");
}

// ---------------------------------------------------------------------------
// Failure excerpts
// ---------------------------------------------------------------------------

#[test]
fn identical_root_causes_publish_one_excerpt() {
    let fixture = Fixture::create();
    fixture.launch("cursor-a.txt", "3", None);
    fixture.launch("cursor-b.txt", "3", None);
    fixture.write(
        "cursor-a.txt.stderr-tail",
        "boom at 0xdead in /tmp/s1/a.txt\n",
    );
    fixture.write(
        "cursor-b.txt.stderr-tail",
        "boom at 0xbeef in /tmp/s2/b.txt\n",
    );
    let first = fixture.text("cursor-a.txt");
    let second = fixture.text("cursor-b.txt");
    let assert = fixture
        .collect(&["--timeout", "1", &first, &second])
        .success();
    let stderr = stderr_of(&assert);
    assert_eq!(
        stderr.matches("--- failed agent stderr tail ---").count(),
        1
    );
    assert!(
        stderr.contains("identical failure to cursor-a.txt"),
        "{stderr}"
    );
    assert!(stderr.contains("stderr tail suppressed"), "{stderr}");
}

#[test]
fn a_phase_output_falls_back_to_its_base_launch_stderr() {
    let fixture = Fixture::create();
    fixture.launch("cursor-review-phase2.txt", "3", None);
    fixture.write(
        "cursor-review.txt.launch-stderr",
        "base launcher exploded\n",
    );
    let output = fixture.text("cursor-review-phase2.txt");
    let assert = fixture.collect(&["--timeout", "1", &output]).success();
    let stderr = stderr_of(&assert);
    assert!(stderr.contains("base launcher exploded"), "{stderr}");
}
