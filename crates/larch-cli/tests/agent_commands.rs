use std::{
    env, fs,
    path::{Path, PathBuf},
    process::Command,
};

#[cfg(unix)]
use std::os::unix::fs::{PermissionsExt as _, symlink};

use assert_cmd::Command as AssertCommand;
use predicates::prelude::*;
use tempfile::TempDir;

fn larch() -> AssertCommand {
    AssertCommand::cargo_bin("larch").expect("larch binary should build")
}

fn write(path: &Path, contents: &str) {
    let parent = path.parent().expect("fixture path has parent");
    fs::create_dir_all(parent).expect("create fixture parent");
    fs::write(path, contents).expect("write fixture");
}

#[cfg(unix)]
fn vendor_fixture(root: &Path, name: &str, body: &str) -> PathBuf {
    use std::os::unix::fs::PermissionsExt as _;

    let bin = root.join("bin");
    fs::create_dir_all(&bin).expect("fixture bin");
    let executable = bin.join(name);
    write(&executable, body);
    fs::set_permissions(&executable, fs::Permissions::from_mode(0o755))
        .expect("fixture executable permissions");
    executable
}

#[cfg(unix)]
fn larch_with_fixture_vendor(root: &Path) -> AssertCommand {
    let current_path = env::var_os("PATH").unwrap_or_default();
    let mut command = larch();
    let path =
        env::join_paths(std::iter::once(root.join("bin")).chain(env::split_paths(&current_path)))
            .expect("fixture PATH");
    command.env("PATH", path);
    command.current_dir(root);
    command
}

fn repository_root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .ancestors()
        .nth(2)
        .expect("workspace root")
        .to_path_buf()
}

fn classify(plugin: &Path, diff: &Path) -> AssertCommand {
    let mut command = larch();
    command
        .env("CLAUDE_PLUGIN_ROOT", plugin)
        .args(["agent", "classify-diff"])
        .arg(diff);
    command
}

#[test]
fn classify_diff_covers_modes_mixed_changes_and_bad_manifests() {
    let fixture = TempDir::new().expect("fixture");
    let plugin = fixture.path().join("plugin");
    write(
        &plugin.join("scripts/generators.tsv"),
        "generate code-reviewer-agent\tagents/generated.md\n",
    );
    let cases = [
        ("docs", "diff --git a/docs/a.md b/docs/a.md\n", "docs-only"),
        (
            "test",
            "diff --git a/scripts/test-a.sh b/scripts/test-a.sh\n",
            "test-only",
        ),
        (
            "generated",
            "diff --git a/agents/generated.md b/agents/generated.md\n",
            "generated-only",
        ),
        (
            "mixed",
            "diff --git a/docs/a.md b/docs/a.md\ndiff --git a/scripts/test-a.sh b/scripts/test-a.sh\n",
            "generic",
        ),
        (
            "unsafe",
            "diff --git a/docs/../a.md b/docs/../a.md\n",
            "generic",
        ),
    ];
    for (name, diff, mode) in cases {
        let diff_path = fixture.path().join(format!("{name}.diff"));
        write(&diff_path, diff);
        classify(&plugin, &diff_path)
            .assert()
            .success()
            .stdout(format!("DIFF_MODE={mode}\n"));
    }

    let missing_plugin = fixture.path().join("missing-plugin");
    let diff_path = fixture.path().join("missing.diff");
    write(&diff_path, "diff --git a/docs/a.md b/docs/a.md\n");
    classify(&missing_plugin, &diff_path)
        .assert()
        .code(1)
        .stderr(predicate::str::contains(
            "scripts/generators.tsv is missing or unsafe",
        ));
    write(&plugin.join("scripts/generators.tsv"), "generate\t \n");
    classify(&plugin, &diff_path)
        .assert()
        .code(1)
        .stderr(predicate::str::contains(
            "contains an empty required column",
        ));
}

#[test]
fn wait_reviewers_preserves_validation_and_completion_rows() {
    let fixture = TempDir::new().expect("fixture");
    let done = fixture.path().join("done.done");
    let empty = fixture.path().join("empty.done");
    let missing = fixture.path().join("missing.done");
    write(&done, "0\n");
    write(&empty, "\n");
    larch()
        .env("WAIT_FOR_REVIEWERS_POLL_INTERVAL", "0.01")
        .args(["agent", "wait-reviewers", "--timeout", "1"])
        .arg(&done)
        .arg(&empty)
        .arg(&missing)
        .assert()
        .success()
        .stdout("DONE 1 done: exit=0\nDONE 2 empty: exit=unknown\nTIMEOUT 3 missing\n");
    larch()
        .args(["agent", "wait-reviewers", "--timeout", "00"])
        .arg(&done)
        .assert()
        .code(1)
        .stderr(predicate::str::contains("must be a positive integer"));
    for invalid_timeout in ["0", "000", "abc"] {
        larch()
            .args(["agent", "wait-reviewers", "--timeout", invalid_timeout])
            .arg(&done)
            .assert()
            .code(1)
            .stderr(predicate::str::contains("must be a positive integer"));
    }
    larch()
        .env("WAIT_FOR_REVIEWERS_POLL_INTERVAL", "00")
        .args(["agent", "wait-reviewers"])
        .arg(&done)
        .assert()
        .code(1)
        .stderr(predicate::str::contains("WAIT_FOR_REVIEWERS_POLL_INTERVAL"));
}

#[cfg(unix)]
#[test]
fn run_external_agent_writes_legacy_artifacts_and_failure_diagnostics() {
    let fixture = TempDir::new().expect("fixture");
    let _vendor = vendor_fixture(
        fixture.path(),
        "claude",
        "#!/bin/sh\nprintf 'stdout line\\n'\nprintf 'stderr line\\n' >&2\nexit 3\n",
    );
    let output = fixture.path().join("agent.out");
    larch_with_fixture_vendor(fixture.path())
        .args([
            "agent",
            "run-external-agent",
            "--tool",
            "claude",
            "--output",
        ])
        .arg(&output)
        .args(["--timeout", "5", "--capture-stdout-only", "--stderr-sink"])
        .arg(fixture.path().join("sink.log"))
        .args(["--", "claude"])
        .assert()
        .code(3);
    assert_eq!(
        fs::read_to_string(&output).expect("stdout artifact"),
        "stdout line\n"
    );
    assert_eq!(
        fs::read_to_string(format!("{}.diag", output.display())).expect("diag artifact"),
        "stderr line\nFailed with exit code 3. Output size: 12 bytes.\n"
    );
    assert_eq!(
        fs::read_to_string(format!("{}.done", output.display())).expect("done artifact"),
        "3\n"
    );
    assert_eq!(
        fs::read_to_string(format!("{}.meta", output.display())).expect("meta artifact"),
        format!(
            "TOOL=claude\nTIMEOUT=5\nCAPTURE_STDOUT=false\nCAPTURE_STDOUT_ONLY=true\nOUTPUT_FILE={}\nSTDERR_SINK={}\nCMD_JSON=[\"claude\"]\n",
            output.display(),
            fixture.path().join("sink.log").display(),
        )
    );
    assert_eq!(
        fs::read_to_string(format!("{}.stderr-tail", output.display()))
            .expect("stderr tail artifact"),
        "stderr line\nFailed with exit code 3. Output size: 12 bytes.\n"
    );
    assert!(PathBuf::from(format!("{}.failure-diag", output.display())).is_file());
}

#[test]
fn run_external_agent_rejects_invalid_arguments_before_creating_sidecars() {
    let fixture = TempDir::new().expect("fixture");
    let unsafe_output = fixture.path().join("bad\nout.txt");
    larch()
        .args([
            "agent",
            "run-external-agent",
            "--tool",
            "claude",
            "--output",
        ])
        .arg(&unsafe_output)
        .args(["--timeout", "5", "--", "claude"])
        .assert()
        .code(1)
        .stderr(predicate::str::contains(
            "ERROR: --output contains unsupported characters",
        ));
    assert!(!unsafe_output.exists());
    assert!(!PathBuf::from(format!("{}.done", unsafe_output.display())).exists());
    assert!(!PathBuf::from(format!("{}.meta", unsafe_output.display())).exists());

    let output = fixture.path().join("out.txt");
    larch()
        .args([
            "agent",
            "run-external-agent",
            "--tool",
            "claude",
            "--output",
        ])
        .arg(&output)
        .args(["--timeout", "0", "--", "claude"])
        .assert()
        .code(1)
        .stderr(predicate::str::contains(
            "ERROR: --timeout must be a positive integer, got '0'",
        ));
    assert!(!PathBuf::from(format!("{}.done", output.display())).exists());
}

#[cfg(unix)]
#[test]
fn run_external_agent_inner_sentinel_replaces_stale_artifacts() {
    let fixture = TempDir::new().expect("fixture");
    let _vendor = vendor_fixture(
        fixture.path(),
        "claude",
        "#!/bin/sh\nprintf 'fresh output\\n'\n",
    );
    let output = fixture.path().join("agent.out");
    write(&output, "stale output\n");
    write(&PathBuf::from(format!("{}.done", output.display())), "99\n");
    write(
        &PathBuf::from(format!("{}.inner.done", output.display())),
        "98\n",
    );
    larch_with_fixture_vendor(fixture.path())
        .env("RUN_EXTERNAL_AGENT_INNER_SENTINEL_SUFFIX", ".inner.done")
        .args([
            "agent",
            "run-external-agent",
            "--tool",
            "claude",
            "--output",
        ])
        .arg(&output)
        .args(["--timeout", "5", "--capture-stdout", "--", "claude"])
        .assert()
        .success();
    assert_eq!(
        fs::read_to_string(&output).expect("fresh output"),
        "fresh output\n"
    );
    assert!(!PathBuf::from(format!("{}.done", output.display())).exists());
    assert_eq!(
        fs::read_to_string(format!("{}.inner.done", output.display()))
            .expect("inner completion sentinel"),
        "0\n"
    );
}

#[cfg(unix)]
#[test]
fn launch_review_codex_writes_review_artifacts_through_shared_runner() {
    let fixture = TempDir::new().expect("fixture");
    let _vendor = vendor_fixture(
        fixture.path(),
        "codex",
        "#!/bin/sh\nout=''\nprevious=''\nfor argument in \"$@\"; do\n  if [ \"$previous\" = '--output-last-message' ]; then out=\"$argument\"; fi\n  previous=\"$argument\"\ndone\nprintf '{\"type\":\"message\",\"usage\":{\"input_tokens\":4,\"cached_input_tokens\":1,\"output_tokens\":2}}\\n'\nprintf 'review result\\n' > \"$out\"\n",
    );
    let output = fixture.path().join("review.txt");
    larch_with_fixture_vendor(fixture.path())
        .env("OPENAI_API_KEY", "test-key")
        .env("LARCH_EXTERNAL_STARTUP_LOCK_DELAY", "0")
        .args(["agent", "launch-review", "--tool", "codex", "--output"])
        .arg(&output)
        .args(["--timeout", "5", "--prompt", "review this"])
        .assert()
        .success();
    assert_eq!(
        fs::read_to_string(&output).expect("review output"),
        "review result\n"
    );
    assert!(
        fs::read_to_string(format!("{}.events.jsonl", output.display()))
            .expect("events")
            .contains("input_tokens")
    );
    assert_eq!(
        fs::read_to_string(format!("{}.dirty-tree", output.display())).expect("dirty tree"),
        "STATUS=clean\nMODE=baseline\nREASON=codex-sandbox-read-only\n"
    );
    assert_eq!(
        fs::read_to_string(format!("{}.done", output.display())).expect("done"),
        "0\n"
    );
    let meta = fs::read_to_string(format!("{}.meta", output.display())).expect("meta");
    assert!(meta.contains("OUTER_LAUNCHER=agent launch-review"));
    assert!(meta.contains("OUTER_LAUNCHER_MODEL_ROLE=default"));
}

#[test]
fn launch_review_preserves_usage_and_early_error_exit_contracts() {
    let fixture = TempDir::new().expect("fixture");
    let output = fixture.path().join("review.txt");
    larch()
        .args(["agent", "launch-review", "--help"])
        .assert()
        .success()
        .stderr(predicate::str::contains(
            "usage: cli.py agent launch-review",
        ));
    larch()
        .args([
            "agent",
            "launch-review",
            "--output",
            "review.txt",
            "--timeout",
            "5",
            "--prompt",
            "review this",
        ])
        .assert()
        .code(2)
        .stderr(predicate::str::contains("arguments are required: --tool"));
    larch()
        .args(["agent", "launch-review", "--tool", "codex", "--output"])
        .arg(&output)
        .args(["--timeout", "bad", "--prompt", "review this"])
        .assert()
        .code(2)
        .stderr(predicate::str::contains("got 'bad'"));
    larch()
        .args(["agent", "launch-review", "--tool", "codex", "--output"])
        .arg(fixture.path().join("missing/review.txt"))
        .args(["--timeout", "5", "--prompt", "review this"])
        .assert()
        .code(2)
        .stderr(predicate::str::contains(
            "output parent directory does not exist",
        ));
    larch()
        .args(["agent", "launch-review", "--tool", "codex", "--output"])
        .arg(&output)
        .args(["--timeout", "5", "--prompt-file"])
        .arg(fixture.path().join("missing-prompt.txt"))
        .assert()
        .code(1)
        .stderr(predicate::str::contains("failed to read --prompt-file"));
}

#[cfg(unix)]
#[test]
fn launch_review_renders_a_specialist_agent_file_before_running_codex() {
    let fixture = TempDir::new().expect("fixture");
    let _vendor = vendor_fixture(
        fixture.path(),
        "codex",
        "#!/bin/sh\nout=''\nprevious=''\nfor argument in \"$@\"; do\n  if [ \"$previous\" = '--output-last-message' ]; then out=\"$argument\"; fi\n  previous=\"$argument\"\ndone\nprintf '{\"type\":\"message\",\"usage\":{\"input_tokens\":4,\"cached_input_tokens\":1,\"output_tokens\":2}}\\n'\nprintf 'review result\\n' > \"$out\"\n",
    );
    let output = fixture.path().join("review.txt");
    larch_with_fixture_vendor(fixture.path())
        .env("CLAUDE_PLUGIN_ROOT", repository_root())
        .env("OPENAI_API_KEY", "test-key")
        .env("LARCH_EXTERNAL_STARTUP_LOCK_DELAY", "0")
        .args(["agent", "launch-review", "--tool", "codex", "--output"])
        .arg(&output)
        .args(["--timeout", "5", "--agent-file"])
        .arg(repository_root().join("agents/reviewer-correctness.md"))
        .args([
            "--mode",
            "description",
            "--description-text",
            "Review the Rust launch-review migration.",
            "--scope-files",
            "crates/larch-cli/src/agent_review.rs",
        ])
        .assert()
        .success();
    let prompt =
        fs::read_to_string(format!("{}.prompt", output.display())).expect("prompt sidecar");
    assert!(prompt.contains("### In-Scope Findings"));
    assert_eq!(
        fs::read_to_string(&output).expect("review output"),
        "review result\n"
    );
}

#[cfg(unix)]
#[test]
fn launch_review_reconstructs_a_codex_prompt_sentinel_from_a_prompt_file() {
    let fixture = TempDir::new().expect("fixture");
    let _vendor = vendor_fixture(
        fixture.path(),
        "codex",
        "#!/bin/sh\nout=''\nprevious=''\nfor argument in \"$@\"; do\n  if [ \"$previous\" = '--output-last-message' ]; then out=\"$argument\"; fi\n  previous=\"$argument\"\ndone\nprintf 'review result\n' > \"$out\"\n",
    );
    let agent = repository_root().join("agents/reviewer-correctness.md");
    let first_output = fixture.path().join("first-review.txt");
    larch_with_fixture_vendor(fixture.path())
        .env("CLAUDE_PLUGIN_ROOT", repository_root())
        .env("OPENAI_API_KEY", "test-key")
        .env("LARCH_EXTERNAL_STARTUP_LOCK_DELAY", "0")
        .args(["agent", "launch-review", "--tool", "codex", "--output"])
        .arg(&first_output)
        .args(["--timeout", "5", "--agent-file"])
        .arg(&agent)
        .args(["--mode", "diff"])
        .assert()
        .success();
    let sentinel = PathBuf::from(format!("{}.prompt", first_output.display()));
    assert!(
        fs::read_to_string(&sentinel)
            .expect("sentinel prompt")
            .starts_with("LARCH_PROMPT_SENTINEL=1\n")
    );

    let second_output = fixture.path().join("second-review.txt");
    larch_with_fixture_vendor(fixture.path())
        .env("CLAUDE_PLUGIN_ROOT", repository_root())
        .env("OPENAI_API_KEY", "test-key")
        .env("LARCH_EXTERNAL_STARTUP_LOCK_DELAY", "0")
        .args(["agent", "launch-review", "--tool", "codex", "--output"])
        .arg(&second_output)
        .args(["--timeout", "5", "--prompt-file"])
        .arg(&sentinel)
        .assert()
        .success();
    let reconstructed =
        fs::read_to_string(format!("{}.prompt", second_output.display())).expect("prompt sidecar");
    assert!(reconstructed.contains("### In-Scope Findings"));
    assert!(!reconstructed.starts_with("LARCH_PROMPT_SENTINEL=1\n"));
}

#[cfg(unix)]
#[test]
fn launch_review_codex_auth_preflight_writes_terminal_artifacts() {
    let fixture = TempDir::new().expect("fixture");
    let home = fixture.path().join("home");
    let config = home.join(".codex/config.toml");
    write(&config, "model = \"test\"\n");
    fs::set_permissions(&config, fs::Permissions::from_mode(0o000))
        .expect("unreadable config permissions");
    let output = fixture.path().join("review.txt");
    let mut command = larch();
    command
        .current_dir(fixture.path())
        .env("HOME", home)
        .env_remove("OPENAI_API_KEY")
        .env("LARCH_EXTERNAL_STARTUP_LOCK_DELAY", "0")
        .args(["agent", "launch-review", "--tool", "codex", "--output"])
        .arg(&output)
        .args(["--timeout", "5", "--prompt", "review this"])
        .assert()
        .success();
    let diagnostic = fs::read_to_string(format!("{}.diag", output.display())).expect("diagnostic");
    assert!(diagnostic.contains("STATUS=FAILED"));
    assert!(PathBuf::from(format!("{}.meta", output.display())).is_file());
    assert!(PathBuf::from(format!("{}.dirty-tree", output.display())).is_file());
    assert_eq!(
        fs::read_to_string(format!("{}.done", output.display())).expect("done"),
        "1\n"
    );
}

#[cfg(unix)]
#[test]
fn launch_review_rejects_symlinked_session_bridge_files() {
    let fixture = TempDir::new().expect("fixture");
    let implementation = fixture.path().join("implementation");
    fs::create_dir_all(&implementation).expect("implementation directory");
    let target = fixture.path().join("outside-session-file");
    write(&target, "secret\n");
    symlink(&target, implementation.join("session-id")).expect("session-id symlink");
    symlink(&target, implementation.join("claude-source.env")).expect("source symlink");
    let _vendor = vendor_fixture(
        fixture.path(),
        "codex",
        "#!/bin/sh\nout=''\nprevious=''\nfor argument in \"$@\"; do\n  if [ \"$previous\" = '--output-last-message' ]; then out=\"$argument\"; fi\n  previous=\"$argument\"\ndone\nprintf '%s|%s' \"$LARCH_TOKEN_SESSION_ID\" \"$LARCH_CLAUDE_SOURCE_FILE\" > \"$out\"\n",
    );
    let output = fixture.path().join("review.txt");
    larch_with_fixture_vendor(fixture.path())
        .env("OPENAI_API_KEY", "test-key")
        .env("IMPLEMENT_TMPDIR", &implementation)
        .env("LARCH_EXTERNAL_STARTUP_LOCK_DELAY", "0")
        .args(["agent", "launch-review", "--tool", "codex", "--output"])
        .arg(&output)
        .args(["--timeout", "5", "--prompt", "review this"])
        .assert()
        .success();
    assert_eq!(fs::read_to_string(&output).expect("review output"), "|");
}

#[cfg(unix)]
#[test]
fn launch_review_passes_confined_session_bridge_files_to_codex() {
    let fixture = TempDir::new().expect("fixture");
    let implementation = fixture.path().join("implementation");
    let session_id = implementation.join("session-id");
    let claude_source = implementation.join("claude-source.env");
    write(&session_id, "session-123\n");
    write(&claude_source, "CLAUDE_SOURCE=trusted\n");
    let _vendor = vendor_fixture(
        fixture.path(),
        "codex",
        "#!/bin/sh\nout=''\nprevious=''\nfor argument in \"$@\"; do\n  if [ \"$previous\" = '--output-last-message' ]; then out=\"$argument\"; fi\n  previous=\"$argument\"\ndone\nprintf '%s|%s' \"$LARCH_TOKEN_SESSION_ID\" \"$LARCH_CLAUDE_SOURCE_FILE\" > \"$out\"\n",
    );
    let output = fixture.path().join("review.txt");
    larch_with_fixture_vendor(fixture.path())
        .env("OPENAI_API_KEY", "test-key")
        .env("IMPLEMENT_TMPDIR", &implementation)
        .env("LARCH_EXTERNAL_STARTUP_LOCK_DELAY", "0")
        .args(["agent", "launch-review", "--tool", "codex", "--output"])
        .arg(&output)
        .args(["--timeout", "5", "--prompt", "review this"])
        .assert()
        .success();
    assert_eq!(
        fs::read_to_string(&output).expect("review output"),
        format!(
            "session-123|{}",
            fs::canonicalize(&claude_source)
                .expect("canonical Claude source")
                .display()
        )
    );
}

#[cfg(unix)]
#[test]
fn launch_review_cursor_postprocesses_result_and_usage() {
    let fixture = TempDir::new().expect("fixture");
    let _vendor = vendor_fixture(
        fixture.path(),
        "cursor",
        "#!/bin/sh\nprintf '{\"result\":\"review result\",\"usage\":{\"inputTokens\":4,\"outputTokens\":2,\"cacheReadTokens\":1,\"cacheWriteTokens\":0}}\\n'\n",
    );
    let output = fixture.path().join("review.txt");
    larch_with_fixture_vendor(fixture.path())
        .env("CURSOR_API_KEY", "test-key")
        .env("LARCH_EXTERNAL_STARTUP_LOCK_DELAY", "0")
        .args(["agent", "launch-review", "--tool", "cursor", "--output"])
        .arg(&output)
        .args(["--timeout", "5", "--prompt", "review this"])
        .assert()
        .success();
    assert_eq!(
        fs::read_to_string(&output).expect("review output"),
        "review result"
    );
    assert!(
        fs::read_to_string(format!("{}.json", output.display()))
            .expect("raw cursor output")
            .contains("inputTokens")
    );
    let token_record =
        fs::read_to_string(format!("{}.token-record", output.display())).expect("token record");
    assert!(token_record.contains("TOOL=cursor"));
    assert!(token_record.contains("TOTAL=7"));
    assert!(
        fs::read_to_string(format!("{}.sidecar", output.display()))
            .expect("sidecar")
            .contains("cursor-status: ok")
    );
}

#[cfg(unix)]
#[test]
fn launch_review_writes_cap_artifacts_before_vendor_launch() {
    let fixture = TempDir::new().expect("fixture");
    let implementation = fixture.path().join("implement");
    fs::create_dir_all(&implementation).expect("implementation directory");
    let ledger = implementation.join("tokens.jsonl");
    write(&ledger, "{\"type\":\"vendor\",\"total\":5}\n");
    let _vendor = vendor_fixture(
        fixture.path(),
        "codex",
        "#!/bin/sh\nprintf 'vendor should not launch' >&2\nexit 9\n",
    );
    let output = fixture.path().join("review.txt");
    larch_with_fixture_vendor(fixture.path())
        .env("CLAUDE_PLUGIN_ROOT", repository_root())
        .env("IMPLEMENT_TMPDIR", &implementation)
        .env("LARCH_TOKEN_LEDGER", &ledger)
        .args(["agent", "launch-review", "--tool", "codex", "--output"])
        .arg(&output)
        .args([
            "--timeout",
            "5",
            "--prompt",
            "review this",
            "--token-budget-cap",
            "5",
        ])
        .assert()
        .success();
    assert_eq!(
        fs::read_to_string(&output).expect("cap output"),
        "STATUS=cap_hit\n"
    );
    assert!(
        fs::read_to_string(format!("{}.cap-hit", output.display()))
            .expect("cap hit artifact")
            .contains("TOTAL=5")
    );
    assert_eq!(
        fs::read_to_string(format!("{}.done", output.display())).expect("done"),
        "0\n"
    );
    assert!(implementation.join("step-budget-cap-hit.env").is_file());
}

#[cfg(unix)]
#[test]
fn launch_review_failure_writes_terminal_artifacts() {
    let fixture = TempDir::new().expect("fixture");
    let _vendor = vendor_fixture(
        fixture.path(),
        "codex",
        "#!/bin/sh\nprintf 'vendor failure\\n' >&2\nexit 2\n",
    );
    let output = fixture.path().join("review.txt");
    let sink = fixture.path().join("launcher-context.log");
    write(&sink, "captured launcher context\n");
    larch_with_fixture_vendor(fixture.path())
        .env("OPENAI_API_KEY", "test-key")
        .env("LARCH_EXTERNAL_STARTUP_LOCK_DELAY", "0")
        .args(["agent", "launch-review", "--tool", "codex", "--output"])
        .arg(&output)
        .args(["--timeout", "5", "--prompt", "review this", "--stderr-sink"])
        .arg(&sink)
        .assert()
        .code(2);
    assert_eq!(
        fs::read_to_string(format!("{}.done", output.display())).expect("done"),
        "2\n"
    );
    let failure_diag = fs::read_to_string(format!("{}.failure-diag", output.display()))
        .expect("failure diagnostic");
    assert!(failure_diag.contains("vendor failure"));
    assert!(
        failure_diag.contains("captured launcher context"),
        "failure diagnostic: {failure_diag}"
    );
    assert!(
        fs::read_to_string(format!("{}.sidecar", output.display()))
            .expect("sidecar")
            .contains("vendor failure")
    );
}

#[cfg(unix)]
#[test]
fn launch_review_does_not_read_a_symlinked_stderr_sink() {
    let fixture = TempDir::new().expect("fixture");
    let _vendor = vendor_fixture(
        fixture.path(),
        "codex",
        "#!/bin/sh\nprintf 'vendor failure\n' >&2\nexit 2\n",
    );
    let target = fixture.path().join("outside-sink.log");
    write(&target, "sensitive sink content\n");
    let sink = fixture.path().join("launcher-context.log");
    symlink(&target, &sink).expect("sink symlink");
    let output = fixture.path().join("review.txt");
    larch_with_fixture_vendor(fixture.path())
        .env("OPENAI_API_KEY", "test-key")
        .env("LARCH_EXTERNAL_STARTUP_LOCK_DELAY", "0")
        .args(["agent", "launch-review", "--tool", "codex", "--output"])
        .arg(&output)
        .args(["--timeout", "5", "--prompt", "review this", "--stderr-sink"])
        .arg(&sink)
        .assert()
        .code(2);
    let failure_diag = fs::read_to_string(format!("{}.failure-diag", output.display()))
        .expect("failure diagnostic");
    assert!(failure_diag.contains("vendor failure"));
    assert!(!failure_diag.contains("sensitive sink content"));
}

#[cfg(unix)]
#[test]
fn launch_review_panel_telemetry_uses_the_canonical_schema() {
    let fixture = TempDir::new().expect("fixture");
    let _vendor = vendor_fixture(
        fixture.path(),
        "cursor",
        "#!/bin/sh\nprintf '{\"result\":\"review result\",\"usage\":{\"inputTokens\":4,\"outputTokens\":2,\"cacheReadTokens\":1,\"cacheWriteTokens\":0}}\\n'\n",
    );
    let artifacts = fixture.path().join("round-7");
    let output = fixture.path().join("review.txt");
    larch_with_fixture_vendor(fixture.path())
        .env("CURSOR_API_KEY", "test-key")
        .env("LARCH_EXTERNAL_STARTUP_LOCK_DELAY", "0")
        .env("LARCH_PANEL_ARTIFACT_DIR", &artifacts)
        .env("LARCH_PANEL_SLOT", "correctness")
        .env("LARCH_PANEL_PHASE", "review")
        .env("LARCH_PANEL_SITE", "review Step 2")
        .env("LARCH_PANEL_ROUND_NUM", "7")
        .env("LARCH_PANEL_PAYLOAD_BYTES", "5")
        .args(["agent", "launch-review", "--tool", "cursor", "--output"])
        .arg(&output)
        .args(["--timeout", "5", "--prompt", "review this"])
        .assert()
        .success();
    let telemetry =
        fs::read_to_string(artifacts.join("panel-prompt-sizes.tsv")).expect("panel telemetry");
    let rows = telemetry.lines().collect::<Vec<_>>();
    assert_eq!(rows.len(), 2);
    assert_eq!(
        rows[0].split('\t').collect::<Vec<_>>(),
        [
            "site",
            "phase",
            "round_num",
            "slot",
            "slot_kind",
            "tool",
            "output",
            "prompt_bytes",
            "prompt_tokens",
            "scaffold_bytes",
            "scaffold_tokens",
            "payload_bytes",
            "payload_tokens",
            "agent_file",
            "agent_bytes",
            "agent_tokens",
        ]
    );
    let values = rows[1].split('\t').collect::<Vec<_>>();
    assert_eq!(values.len(), 16);
    assert_eq!(values[4], "specialist");
    assert_eq!(values[5], "cursor");
}

#[cfg(unix)]
#[test]
fn launch_review_retries_without_leaving_stale_codex_events() {
    let fixture = TempDir::new().expect("fixture");
    let state = fixture.path().join("attempts");
    write(&state, "0\n");
    let _vendor = vendor_fixture(
        fixture.path(),
        "codex",
        "#!/bin/sh\ncount=$(cat attempts)\nprintf '%s' $((count + 1)) > attempts\nout=''\nprevious=''\nfor argument in \"$@\"; do\n  if [ \"$previous\" = '--output-last-message' ]; then out=\"$argument\"; fi\n  previous=\"$argument\"\ndone\nif [ \"$count\" = 0 ]; then\n  printf 'stale event\\n'\n  exit 7\nfi\nprintf '{\"type\":\"message\",\"usage\":{\"input_tokens\":1,\"cached_input_tokens\":0,\"output_tokens\":1}}\\n'\nprintf 'fresh result\\n' > \"$out\"\n",
    );
    let output = fixture.path().join("review.txt");
    larch_with_fixture_vendor(fixture.path())
        .env("OPENAI_API_KEY", "test-key")
        .env("PYTEST_CURRENT_TEST", "rust")
        .env("LARCH_EXTERNAL_STARTUP_LOCK_DELAY", "0")
        .args(["agent", "launch-review", "--tool", "codex", "--output"])
        .arg(&output)
        .args(["--timeout", "5", "--prompt", "review this"])
        .assert()
        .success();
    assert_eq!(fs::read_to_string(&state).expect("attempt count"), "2");
    assert_eq!(
        fs::read_to_string(&output).expect("fresh result"),
        "fresh result\n"
    );
    let events = fs::read_to_string(format!("{}.events.jsonl", output.display())).expect("events");
    assert!(!events.contains("stale event"));
    assert!(
        fs::read_to_string(format!("{}.sidecar.history", output.display()))
            .expect("history")
            .contains("stale event")
    );
}

#[cfg(unix)]
#[test]
fn run_external_agent_fast_fails_a_codex_policy_rejection() {
    let fixture = TempDir::new().expect("fixture");
    let _vendor = vendor_fixture(
        fixture.path(),
        "codex",
        "#!/bin/sh\nprintf 'error=exec_command failed for bash: CreateProcess {\"message\":\"Rejected(blocked by policy)\"}\\n'\nwhile :; do sleep 1; done\n",
    );
    let output = fixture.path().join("codex.out");
    larch_with_fixture_vendor(fixture.path())
        .env("RUN_EXTERNAL_AGENT_POLL_INTERVAL", "0.02")
        .args(["agent", "run-external-agent", "--tool", "codex", "--output"])
        .arg(&output)
        .args(["--timeout", "30", "--capture-stdout-only", "--", "codex"])
        .assert()
        .code(1);
    let diag = fs::read_to_string(format!("{}.diag", output.display())).expect("policy diag");
    assert!(diag.contains("FAILURE_CLASS=policy-rejection"));
    assert!(diag.contains("POLICY_REJECTION=true"));
    assert!(diag.contains("Rejected(blocked by policy)"));
    assert_eq!(
        fs::read_to_string(format!("{}.done", output.display())).expect("policy done"),
        "1\n"
    );
}

#[cfg(unix)]
#[test]
fn run_external_agent_marks_a_completed_codex_policy_rejection() {
    let fixture = TempDir::new().expect("fixture");
    let _vendor = vendor_fixture(
        fixture.path(),
        "codex",
        "#!/bin/sh\nprintf 'error=exec_command failed for bash: CreateProcess {\"message\":\"Rejected(blocked by policy)\"}\\n'\n",
    );
    let output = fixture.path().join("codex.out");
    larch_with_fixture_vendor(fixture.path())
        .args(["agent", "run-external-agent", "--tool", "codex", "--output"])
        .arg(&output)
        .args(["--timeout", "5", "--capture-stdout-only", "--", "codex"])
        .assert()
        .code(1);
    let diag = fs::read_to_string(format!("{}.diag", output.display())).expect("policy diag");
    assert!(diag.contains("POLICY_REJECTION=true"));
}

#[cfg(unix)]
#[test]
fn run_external_agent_uses_typed_cursor_environment() {
    let fixture = TempDir::new().expect("fixture");
    let _vendor = vendor_fixture(
        fixture.path(),
        "cursor",
        concat!(
            "#!/bin/sh\nprintf '%s:%s\\n' \"$",
            "{NO_OPEN_BROWSER:-missing}\" \"$",
            "{CURSOR_API_KEY:-missing}\"\n",
        ),
    );
    let output = fixture.path().join("cursor.out");
    larch_with_fixture_vendor(fixture.path())
        .env("CURSOR_API_KEY", "  cursor-token  ")
        .args([
            "agent",
            "run-external-agent",
            "--tool",
            "cursor",
            "--output",
        ])
        .arg(&output)
        .args(["--timeout", "5", "--capture-stdout", "--", "cursor"])
        .assert()
        .success();
    assert_eq!(
        fs::read_to_string(output).expect("cursor output"),
        "1:cursor-token\n"
    );
}

#[cfg(unix)]
#[test]
fn run_external_agent_deadline_kills_the_whole_vendor_process_group() {
    use nix::{errno::Errno, sys::signal::kill, unistd::Pid};

    let fixture = TempDir::new().expect("fixture");
    let pid_file = fixture.path().join("pids");
    let _vendor = vendor_fixture(
        fixture.path(),
        "codex",
        "#!/bin/sh\necho \"$$\" >> pids\nsh -c 'echo \"$$\" >> pids; sh -c '\\''echo \"$$\" >> pids; while :; do sleep 1; done'\\'' & wait' &\nwhile :; do sleep 1; done\n",
    );
    let output = fixture.path().join("hung.out");
    let command_output = larch_with_fixture_vendor(fixture.path())
        .args(["agent", "run-external-agent", "--tool", "codex", "--output"])
        .arg(&output)
        .args(["--timeout", "2", "--capture-stdout", "--", "codex"])
        .output()
        .expect("run timeout fixture");
    assert_eq!(
        command_output.status.code(),
        Some(124),
        "stderr={} diag={}",
        String::from_utf8_lossy(&command_output.stderr),
        fs::read_to_string(format!("{}.diag", output.display())).unwrap_or_default(),
    );
    let pids: Vec<i32> = fs::read_to_string(&pid_file)
        .expect("vendor PID ledger")
        .lines()
        .map(|line| line.parse().expect("numeric PID"))
        .collect();
    assert_eq!(pids.len(), 3, "fixture should record a process tree");
    let mut distinct_pids = pids.clone();
    distinct_pids.sort_unstable();
    distinct_pids.dedup();
    assert_eq!(
        distinct_pids.len(),
        3,
        "fixture should record unique processes"
    );
    for _attempt in 0..50 {
        if pids
            .iter()
            .all(|pid| matches!(kill(Pid::from_raw(*pid), None), Err(Errno::ESRCH)))
        {
            return;
        }
        std::thread::sleep(std::time::Duration::from_millis(10));
    }
    let live: Vec<i32> = pids
        .into_iter()
        .filter(|pid| !matches!(kill(Pid::from_raw(*pid), None), Err(Errno::ESRCH)))
        .collect();
    assert!(live.is_empty(), "live vendor descendants: {live:?}");
}

#[test]
fn compose_collector_failure_log_redacts_and_writes_sections() {
    let fixture = TempDir::new().expect("fixture");
    let reviewer = fixture.path().join("reviewer.txt");
    let secret = format!("sk-{}", "a".repeat(24));
    let session_path = fixture.path().join("larch-implement-redact123");
    write(&reviewer, "reviewer body\n");
    write(&fixture.path().join("reviewer.txt.diag"), "diag body\n");
    write(
        &fixture.path().join("reviewer.txt.launch-stderr"),
        &format!("line one {} {secret}\nline two\n", session_path.display()),
    );
    write(
        &fixture.path().join("reviewer.txt.stderr-tail"),
        &"é".repeat(6_000),
    );
    let output = fixture.path().join("failure.log");
    larch()
        .args(["agent", "compose-collector-failure-log", "--reviewer-file"])
        .arg(&reviewer)
        .args(["--structured-record", "STATUS=FAILED", "--output"])
        .arg(&output)
        .assert()
        .success();
    let body = fs::read_to_string(&output).expect("collector output");
    assert!(body.contains("## Structured collector record"));
    assert!(body.contains("reviewer body"));
    assert!(body.contains("diag body"));
    assert!(!body.contains(&secret));
    assert!(!body.contains(&session_path.display().to_string()));
    assert!(body.contains("<REDACTED-TOKEN>"));
    assert!(body.len() < 6_000, "stderr tails must remain bounded");
    #[cfg(unix)]
    assert_eq!(
        fs::metadata(&output)
            .expect("output metadata")
            .permissions()
            .mode()
            & 0o777,
        0o600
    );
    larch()
        .args([
            "agent",
            "compose-collector-failure-log",
            "--structured-record",
            "",
        ])
        .arg("--output")
        .arg(fixture.path().join("bad.log"))
        .assert()
        .code(2)
        .stderr(predicate::str::contains("required and non-empty"));
    larch()
        .args([
            "agent",
            "compose-collector-failure-log",
            "--structured-record",
            "STATUS=FAILED",
            "--output",
            "",
        ])
        .assert()
        .code(2)
        .stderr(predicate::str::contains("--output is required"));
}

fn git_output(repository: &Path, arguments: &[&str]) -> std::process::Output {
    let output = Command::new("git")
        .args(arguments)
        .current_dir(repository)
        .output()
        .expect("run fixture git");
    assert!(
        output.status.success(),
        "git {:?} failed: {}",
        arguments,
        String::from_utf8_lossy(&output.stderr)
    );
    output
}

fn git(repository: &Path, arguments: &[&str]) {
    let _ = git_output(repository, arguments);
}

fn git_stdout(repository: &Path, arguments: &[&str]) -> String {
    String::from_utf8(git_output(repository, arguments).stdout).expect("UTF-8 git stdout")
}

fn commit(repository: &Path, path: &str, contents: &str, message: &str) {
    write(&repository.join(path), contents);
    git(repository, &["add", path]);
    git(repository, &["commit", "-m", message]);
}

#[test]
fn gather_branch_context_excludes_larch_logs() {
    let fixture = TempDir::new().expect("fixture");
    let repository = fixture.path().join("repository");
    fs::create_dir(&repository).expect("repository dir");
    git(&repository, &["init", "-b", "main"]);
    git(&repository, &["config", "user.email", "test@example.com"]);
    git(&repository, &["config", "user.name", "Test User"]);
    commit(&repository, "src/feature.txt", "v1\n", "base code");
    git(&repository, &["checkout", "-b", "feature"]);
    commit(
        &repository,
        "larch-logs/run/session.txt",
        "run log\n",
        "add run log",
    );
    commit(&repository, "src/feature.txt", "v1\nv2\n", "feature change");
    let output = fixture.path().join("context");
    fs::create_dir(&output).expect("context dir");
    larch()
        .current_dir(&repository)
        .args(["agent", "gather-branch-context", "--output-dir"])
        .arg(&output)
        .assert()
        .success()
        .stdout(predicate::str::contains("COMMIT_COUNT=1"));
    let diff = fs::read_to_string(output.join("diff.txt")).expect("diff");
    let files = fs::read_to_string(output.join("file-list.txt")).expect("file list");
    let commits = fs::read_to_string(output.join("commit-log.txt")).expect("commit log");
    assert!(diff.contains("src/feature.txt"));
    assert!(files.contains("src/feature.txt"));
    assert!(commits.contains("feature change"));
    assert!(!diff.contains("larch-logs"));
    assert!(!files.contains("larch-logs"));
    assert!(!commits.contains("add run log"));
}

#[test]
fn gather_branch_context_prefers_origin_main_when_local_main_is_stale() {
    let fixture = TempDir::new().expect("fixture");
    let origin = fixture.path().join("origin.git");
    git(
        fixture.path(),
        &[
            "init",
            "--bare",
            "-b",
            "main",
            origin.to_str().expect("origin path"),
        ],
    );
    let repository = fixture.path().join("repository");
    fs::create_dir(&repository).expect("repository dir");
    git(&repository, &["init", "-b", "main"]);
    git(&repository, &["config", "user.email", "test@example.com"]);
    git(&repository, &["config", "user.name", "Test User"]);
    git(
        &repository,
        &[
            "remote",
            "add",
            "origin",
            origin.to_str().expect("origin path"),
        ],
    );
    commit(&repository, "feature.txt", "v1\n", "base A");
    git(&repository, &["push", "origin", "main"]);
    let base_a = git_stdout(&repository, &["rev-parse", "HEAD"])
        .trim()
        .to_owned();
    git(&repository, &["checkout", "-b", "feature"]);
    commit(
        &repository,
        "feature.txt",
        "v1\nfeature-edit\n",
        "feature change",
    );
    git(&repository, &["checkout", "main"]);
    commit(
        &repository,
        "unrelated.txt",
        "other-pr\n",
        "unrelated PR merged to main",
    );
    let base_b = git_stdout(&repository, &["rev-parse", "HEAD"])
        .trim()
        .to_owned();
    git(&repository, &["push", "origin", "main"]);
    git(&repository, &["reset", "--hard", &base_a]);
    git(&repository, &["checkout", "feature"]);
    git(&repository, &["rebase", &base_b]);
    git(&repository, &["fetch", "origin", "main"]);

    let output = fixture.path().join("context");
    fs::create_dir(&output).expect("context dir");
    larch()
        .current_dir(&repository)
        .args(["agent", "gather-branch-context", "--output-dir"])
        .arg(&output)
        .assert()
        .success()
        .stdout(predicate::str::contains("COMMIT_COUNT=1"));
    let diff = fs::read_to_string(output.join("diff.txt")).expect("diff");
    let files = fs::read_to_string(output.join("file-list.txt")).expect("file list");
    let commits = fs::read_to_string(output.join("commit-log.txt")).expect("commit log");
    assert!(files.contains("feature.txt"));
    assert!(commits.contains("feature change"));
    assert!(!files.contains("unrelated.txt"));
    assert!(!diff.contains("unrelated.txt"));
    assert!(!commits.contains("unrelated PR merged to main"));
}
