//! End-to-end coverage for the three CI fix launchers.
//!
//! Vendor executables are shell fixtures placed ahead of the real ones on
//! `PATH`, so each case exercises the real launcher plumbing — argument
//! validation, prompt composition, artifact publication, and the launcher
//! result envelope — without contacting a vendor service.

#![cfg(unix)]

use std::{
    env, fs,
    os::unix::fs::PermissionsExt as _,
    path::{Path, PathBuf},
};

use assert_cmd::Command as AssertCommand;
use tempfile::TempDir;

fn write(path: &Path, contents: &str) {
    let parent = path.parent().expect("fixture path has parent");
    fs::create_dir_all(parent).expect("create fixture parent");
    fs::write(path, contents).expect("write fixture");
}

fn vendor_fixture(root: &Path, name: &str, body: &str) {
    let bin = root.join("bin");
    fs::create_dir_all(&bin).expect("fixture bin");
    let executable = bin.join(name);
    write(&executable, body);
    fs::set_permissions(&executable, fs::Permissions::from_mode(0o755))
        .expect("fixture executable permissions");
}

/// A launcher invocation whose `PATH` starts with this fixture's `bin`.
fn launcher(root: &Path) -> AssertCommand {
    // Only the fixture `bin` and the base system utilities are visible, so a
    // real vendor installed on the developer's machine cannot satisfy a case
    // that is about a missing binary.
    let path = env::join_paths([
        root.join("bin"),
        PathBuf::from("/usr/bin"),
        PathBuf::from("/bin"),
    ])
    .expect("fixture PATH");
    let mut command = AssertCommand::cargo_bin("larch").expect("larch binary should build");
    command.env("PATH", path);
    command.env("HOME", root.join("home"));
    command.env_remove("OPENAI_API_KEY");
    command.env_remove("CLAUDE_PLUGIN_ROOT");
    command.env_remove("IMPLEMENT_TMPDIR");
    command.env_remove("DESIGN_TMPDIR");
    command.env_remove("REVIEW_TMPDIR");
    command.env_remove("SESSION_ENV_PATH");
    command.env_remove("LARCH_EXECUTION_ISSUES_LOG");
    command.current_dir(root);
    command
}

struct CiFixture {
    _root: TempDir,
    path: PathBuf,
    output: PathBuf,
}

impl CiFixture {
    fn create() -> Self {
        let root = TempDir::new().expect("fixture root");
        let path = root.path().to_path_buf();
        fs::create_dir_all(path.join("home")).expect("fixture home");
        // An empty `bin` keeps every vendor missing until a case adds one.
        fs::create_dir_all(path.join("bin")).expect("fixture bin");
        let output = path.join("ci-fix.out");
        Self {
            _root: root,
            path,
            output,
        }
    }

    fn command(&self, verb: &str) -> AssertCommand {
        let mut command = launcher(&self.path);
        command.args([
            "agent",
            verb,
            "--role",
            "fix",
            "--output",
            &self.output.display().to_string(),
            "--run-id",
            "run-1",
            "--repo",
            "owner/repo",
            "--timeout",
            "30",
        ]);
        command
    }

    fn artifact(&self, suffix: &str) -> String {
        fs::read_to_string(format!("{}{suffix}", self.output.display())).unwrap_or_default()
    }
}

#[test]
fn a_missing_vendor_binary_publishes_the_documented_refusal_for_every_tool() {
    for (verb, tool) in [
        ("launch-codex-ci", "codex"),
        ("launch-cursor-ci", "cursor"),
        ("launch-claude-ci", "claude"),
    ] {
        let fixture = CiFixture::create();
        let assert = fixture.command(verb).assert().success();
        let stdout = String::from_utf8_lossy(&assert.get_output().stdout).into_owned();
        assert!(
            stdout.contains("LAUNCHER_EXIT=127"),
            "{verb} should report the missing-binary exit: {stdout}"
        );
        assert!(
            stdout.contains("LAUNCHER_FAILURE_CLASS="),
            "{verb} should classify the refusal: {stdout}"
        );
        assert_eq!(fixture.artifact(""), "");
        assert_eq!(
            fixture.artifact(".diag"),
            format!("STATUS=FAILED\nFAILURE_REASON={tool} binary missing\n")
        );
        assert!(
            fixture
                .artifact(".meta")
                .contains(&format!("TOOL={tool}\n"))
        );
        assert!(fixture.artifact(".meta").contains("CMD_JSON=[]\n"));
        assert_eq!(fixture.artifact(".done"), "127\n");
    }
}

#[test]
fn arguments_are_refused_in_the_legacy_order() {
    let fixture = CiFixture::create();
    let cases: [(&[&str], &str); 4] = [
        (
            &["--role", "bogus"],
            "agent launch-ci: --role must be fix or resolve-conflict",
        ),
        (
            &["--timeout", "0"],
            "agent launch-ci: --timeout must be a positive integer",
        ),
        (
            &["--model", "two tokens"],
            "agent launch-ci: --model must be a single non-empty token",
        ),
        (
            &["--conflict-files", "../escape"],
            "agent launch-ci: conflict files must be safe repo-relative paths",
        ),
    ];
    for (extra, message) in cases {
        let mut command = fixture.command("launch-codex-ci");
        command.args(extra);
        let assert = command.assert().code(2);
        let stderr = String::from_utf8_lossy(&assert.get_output().stderr).into_owned();
        assert!(
            stderr.contains(message),
            "expected {message:?} in stderr, got {stderr:?}"
        );
    }
}

#[test]
fn a_relative_output_is_refused_without_a_diagnostic() {
    let fixture = CiFixture::create();
    let mut command = launcher(&fixture.path);
    command.args([
        "agent",
        "launch-claude-ci",
        "--role",
        "fix",
        "--output",
        "relative.out",
        "--run-id",
        "run-1",
        "--repo",
        "owner/repo",
    ]);
    command.assert().code(2);
}

#[test]
fn a_failure_log_outside_the_implement_tmpdir_is_refused() {
    let fixture = CiFixture::create();
    let outside = fixture.path.join("outside.log");
    write(&outside, "boom\n");
    let tmpdir = fixture.path.join("implement");
    fs::create_dir_all(&tmpdir).expect("implement tmpdir");
    let mut command = fixture.command("launch-codex-ci");
    command.env("IMPLEMENT_TMPDIR", &tmpdir);
    command.args(["--failure-log", &outside.display().to_string()]);
    let assert = command.assert().code(2);
    let stderr = String::from_utf8_lossy(&assert.get_output().stderr).into_owned();
    assert!(
        stderr.contains("--failure-log must resolve under IMPLEMENT_TMPDIR"),
        "unexpected stderr: {stderr}"
    );
}

#[test]
fn the_claude_launcher_publishes_the_envelope_result_and_token_record() {
    let fixture = CiFixture::create();
    vendor_fixture(
        &fixture.path,
        "claude",
        "#!/bin/sh\ncat > /dev/null\nprintf '%s' '{\"result\":\"patched\",\"usage\":{\"input_tokens\":4,\"output_tokens\":3,\"cache_read_input_tokens\":2,\"cache_creation_input_tokens\":1}}'\n",
    );
    let assert = fixture.command("launch-claude-ci").assert().success();
    let stdout = String::from_utf8_lossy(&assert.get_output().stdout).into_owned();
    assert!(stdout.contains("LAUNCHER_EXIT=0"), "stdout: {stdout}");
    assert_eq!(fixture.artifact(""), "patched");
    assert_eq!(fixture.artifact(".done"), "0\n");
    let token_record = fixture.artifact(".token-record");
    assert!(
        token_record.contains("TOOL=claude\nMODEL=claude-sonnet-4-6\n"),
        "token record: {token_record}"
    );
    assert!(token_record.contains("TOTAL=10\nRAW=claude_ci_fix\n"));
    assert!(fixture.artifact(".prompt").contains("You are using Claude"));
}

#[test]
fn a_claude_envelope_without_a_result_publishes_the_empty_result_marker() {
    let fixture = CiFixture::create();
    vendor_fixture(
        &fixture.path,
        "claude",
        "#!/bin/sh\ncat > /dev/null\nprintf '%s' '{\"other\":1}'\n",
    );
    let assert = fixture.command("launch-claude-ci").assert().success();
    let stdout = String::from_utf8_lossy(&assert.get_output().stdout).into_owned();
    assert!(stdout.contains("LAUNCHER_EXIT=1"), "stdout: {stdout}");
    assert_eq!(fixture.artifact(""), "CLAUDE_CI_EMPTY_RESULT\n");
    assert_eq!(fixture.artifact(".done"), "1\n");
}

#[test]
fn a_claude_launch_that_emits_invalid_json_publishes_the_malformed_marker() {
    let fixture = CiFixture::create();
    vendor_fixture(
        &fixture.path,
        "claude",
        "#!/bin/sh\ncat > /dev/null\nprintf '%s' 'not json'\n",
    );
    fixture.command("launch-claude-ci").assert().success();
    assert_eq!(fixture.artifact(""), "CLAUDE_CI_MALFORMED_JSON\n");
    assert!(
        fixture
            .artifact(".diag")
            .contains("Malformed Claude CI JSON")
    );
}

#[test]
fn the_prompt_carries_the_untrusted_plan_and_failure_context() {
    let fixture = CiFixture::create();
    let tmpdir = fixture.path.join("implement");
    fs::create_dir_all(&tmpdir).expect("implement tmpdir");
    let plan = tmpdir.join("plan.txt");
    write(&plan, "PLAN BODY\n");
    let failure = tmpdir.join("failure.log");
    write(&failure, "FAILURE BODY sk-AAAAAAAAAAAAAAAAAAAAAAAA\n");
    let mut command = fixture.command("launch-claude-ci");
    command.env("IMPLEMENT_TMPDIR", &tmpdir);
    command.args([
        "--plan-file",
        &plan.display().to_string(),
        "--failure-log",
        &failure.display().to_string(),
        "--conflict-files",
        "src/a.rs,src/b.rs",
    ]);
    command.assert().success();
    let prompt = fixture.artifact(".prompt");
    assert!(prompt.contains("<plan-context>\nPLAN BODY\n\n</plan-context>"));
    assert!(prompt.contains("FAILURE BODY"));
    assert!(
        !prompt.contains("sk-AAAAAAAAAAAAAAAAAAAAAAAA"),
        "the failure context must be redacted: {prompt}"
    );
    assert!(prompt.contains("Conflict files: src/a.rs,src/b.rs\n"));
}

/// A Codex fixture that publishes an events stream and a transcript.
const CODEX_FIXTURE: &str = concat!(
    "#!/bin/sh\n",
    "printf '%s\\n' '{\"usage\":{\"input_tokens\":10,\"cache_read_input_tokens\":4,\"output_tokens\":6}}'\n",
    "exit 0\n",
);

#[test]
fn the_codex_launcher_publishes_timing_usage_and_the_outer_meta_record() {
    let fixture = CiFixture::create();
    vendor_fixture(&fixture.path, "codex", CODEX_FIXTURE);
    let assert = fixture.command("launch-codex-ci").assert().success();
    let stdout = String::from_utf8_lossy(&assert.get_output().stdout).into_owned();
    assert!(stdout.contains("LAUNCHER_EXIT=0"), "stdout: {stdout}");
    assert!(stdout.contains("TOKEN_RECORD="), "stdout: {stdout}");
    let token_record = fixture.artifact(".token-record");
    assert!(
        token_record.contains("TOOL=codex\n") && token_record.contains("RAW=codex_ci_fix\n"),
        "token record: {token_record}"
    );
    let meta = fixture.artifact(".meta");
    assert!(
        meta.contains("OUTER_LAUNCHER=agent launch-codex-ci\n"),
        "meta: {meta}"
    );
    assert!(meta.contains("OUTER_LAUNCHER_PROMPT_FILE="));
    assert!(meta.contains("OUTER_LAUNCHER_WORKDIR="));
    assert_eq!(fixture.artifact(".done"), "0\n");
    assert!(fixture.artifact(".prompt").contains("You are using Codex"));
}

#[test]
fn a_failing_codex_launch_records_the_ci_failure_and_its_diagnostic_part() {
    let fixture = CiFixture::create();
    vendor_fixture(
        &fixture.path,
        "codex",
        "#!/bin/sh\necho 'codex blew up' >&2\nexit 3\n",
    );
    let tmpdir = fixture.path.join("implement");
    fs::create_dir_all(&tmpdir).expect("implement tmpdir");
    let mut command = fixture.command("launch-codex-ci");
    command.env("IMPLEMENT_TMPDIR", &tmpdir);
    let assert = command.assert().success();
    let stdout = String::from_utf8_lossy(&assert.get_output().stdout).into_owned();
    assert!(stdout.contains("LAUNCHER_EXIT=3"), "stdout: {stdout}");
    let parts = tmpdir.join("vendor-failure-diagnostics.parts");
    let entries: Vec<PathBuf> = fs::read_dir(&parts)
        .expect("diagnostics parts directory")
        .filter_map(|entry| entry.ok().map(|entry| entry.path()))
        .collect();
    assert_eq!(
        entries.len(),
        1,
        "expected one diagnostic part: {entries:?}"
    );
    let part = fs::read_to_string(&entries[0]).expect("read diagnostic part");
    assert!(
        part.contains("===== ci fixer codex-ci ====="),
        "part: {part}"
    );
    assert!(part.contains("exit-code: 3"), "part: {part}");
}

/// A Cursor fixture that publishes a result envelope with usage buckets.
const CURSOR_FIXTURE: &str = concat!(
    "#!/bin/sh\n",
    "printf '%s' '{\"result\":\"ok\",\"usage\":{\"inputTokens\":5,\"outputTokens\":4,\"cacheReadTokens\":3}}'\n",
    "exit 0\n",
);

fn cursor_command(fixture: &CiFixture, role: &str) -> AssertCommand {
    let mut command = fixture.command("launch-cursor-ci");
    command.env("CURSOR_API_KEY", "key_ci_launcher_fixture");
    command.args(["--role", role]);
    command
}

#[test]
fn the_cursor_launcher_publishes_usage_and_the_outer_meta_record() {
    let fixture = CiFixture::create();
    vendor_fixture(&fixture.path, "cursor", CURSOR_FIXTURE);
    let assert = cursor_command(&fixture, "fix").assert().success();
    let stdout = String::from_utf8_lossy(&assert.get_output().stdout).into_owned();
    assert!(stdout.contains("LAUNCHER_EXIT=0"), "stdout: {stdout}");
    assert!(stdout.contains("TOKEN_RECORD="), "stdout: {stdout}");
    let token_record = fixture.artifact(".token-record");
    assert!(
        token_record.contains(
            "TOOL=cursor\nINPUT=5\nOUTPUT=4\nCACHE_READ=3\nCACHE_CREATE=0\nTOTAL=12\nRAW=cursor_ci_fix\n"
        ),
        "token record: {token_record}"
    );
    assert!(
        fixture
            .artifact(".meta")
            .contains("OUTER_LAUNCHER=agent launch-cursor-ci\n")
    );
    assert!(
        fixture
            .artifact(".prompt")
            .starts_with(" /max-mode on. Prompt: You are using Cursor")
    );
    assert_eq!(fixture.artifact(".done"), "0\n");
}

#[test]
fn a_cursor_conflict_launch_wraps_the_conflict_role_prompt() {
    let fixture = CiFixture::create();
    vendor_fixture(&fixture.path, "cursor", CURSOR_FIXTURE);
    let mut command = cursor_command(&fixture, "resolve-conflict");
    command.args(["--conflict-files", "src/a.rs"]);
    command.assert().success();
    let prompt = fixture.artifact(".prompt");
    assert!(
        prompt.contains("resolve merge/rebase conflicts"),
        "{prompt}"
    );
    assert!(prompt.contains("Conflict files: src/a.rs\n"), "{prompt}");
}

#[test]
fn a_failing_cursor_launch_publishes_the_failure_envelope() {
    let fixture = CiFixture::create();
    vendor_fixture(
        &fixture.path,
        "cursor",
        "#!/bin/sh\necho 'cursor blew up' >&2\nexit 4\n",
    );
    let assert = cursor_command(&fixture, "fix").assert().success();
    let stdout = String::from_utf8_lossy(&assert.get_output().stdout).into_owned();
    assert!(stdout.contains("LAUNCHER_EXIT=4"), "stdout: {stdout}");
    assert!(
        stdout.contains("LAUNCHER_FAILURE_CLASS="),
        "stdout: {stdout}"
    );
    assert_eq!(fixture.artifact(".done"), "4\n");
}

#[test]
fn an_unresolvable_cursor_model_refuses_before_the_vendor_runs() {
    let fixture = CiFixture::create();
    vendor_fixture(&fixture.path, "cursor", CURSOR_FIXTURE);
    let mut command = cursor_command(&fixture, "fix");
    command.env("LARCH_CURSOR_MODEL", "   ");
    let assert = command.assert().success();
    let stdout = String::from_utf8_lossy(&assert.get_output().stdout).into_owned();
    assert!(stdout.contains("LAUNCHER_EXIT=1"), "stdout: {stdout}");
    assert!(
        fixture.artifact(".diag").contains("model args failed"),
        "diag: {}",
        fixture.artifact(".diag")
    );
    assert_eq!(fixture.artifact(".done"), "1\n");
}

#[test]
fn an_explicit_model_overrides_the_resolved_cursor_model() {
    let fixture = CiFixture::create();
    vendor_fixture(
        &fixture.path,
        "cursor",
        "#!/bin/sh\nprintf '%s' \"$*\"\nexit 0\n",
    );
    let mut command = cursor_command(&fixture, "fix");
    command.args(["--model", "fixture-model"]);
    command.assert().success();
    assert!(
        fixture.artifact("").contains("--model fixture-model"),
        "argv: {}",
        fixture.artifact("")
    );
}

#[test]
fn a_timed_out_claude_launch_publishes_the_timeout_exit() {
    let fixture = CiFixture::create();
    vendor_fixture(&fixture.path, "claude", "#!/bin/sh\nsleep 30\n");
    let mut command = fixture.command("launch-claude-ci");
    command.args(["--timeout", "1"]);
    let assert = command.assert().success();
    let stdout = String::from_utf8_lossy(&assert.get_output().stdout).into_owned();
    assert!(stdout.contains("LAUNCHER_EXIT=124"), "stdout: {stdout}");
    assert_eq!(fixture.artifact(".done"), "124\n");
}

#[test]
fn a_timed_out_codex_launch_publishes_the_stall_record() {
    let fixture = CiFixture::create();
    vendor_fixture(&fixture.path, "codex", "#!/bin/sh\nsleep 30\n");
    let mut command = fixture.command("launch-codex-ci");
    command.args(["--timeout", "1"]);
    let assert = command.assert().success();
    let stdout = String::from_utf8_lossy(&assert.get_output().stdout).into_owned();
    assert!(stdout.contains("LAUNCHER_EXIT=124"), "stdout: {stdout}");
    assert_eq!(
        fixture.artifact(".stall.json"),
        "{\"tool\":\"codex\",\"exit_code\":124,\"timeout\":1}\n"
    );
}

#[test]
fn help_prints_the_usage_line_for_every_launcher() {
    let fixture = CiFixture::create();
    for verb in ["launch-codex-ci", "launch-cursor-ci", "launch-claude-ci"] {
        let mut command = launcher(&fixture.path);
        command.args(["agent", verb, "--help"]);
        let assert = command.assert().success();
        let stderr = String::from_utf8_lossy(&assert.get_output().stderr).into_owned();
        assert!(stderr.contains(verb), "usage for {verb}: {stderr}");
    }
}

#[test]
fn an_unknown_flag_and_a_missing_required_flag_are_rejected() {
    let fixture = CiFixture::create();
    let mut unknown = fixture.command("launch-codex-ci");
    unknown.args(["--nonsense"]);
    unknown.assert().code(2);

    let mut missing = launcher(&fixture.path);
    missing.args(["agent", "launch-codex-ci", "--role", "fix"]);
    let assert = missing.assert().code(2);
    let stderr = String::from_utf8_lossy(&assert.get_output().stderr).into_owned();
    assert!(
        stderr.contains("the following arguments are required"),
        "stderr: {stderr}"
    );

    let mut dangling = launcher(&fixture.path);
    dangling.args(["agent", "launch-codex-ci", "--role"]);
    dangling.assert().code(2);
}
