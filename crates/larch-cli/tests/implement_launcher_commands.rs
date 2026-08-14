//! End-to-end coverage for the implement and Claude fix launchers.
//!
//! Vendor executables are shell fixtures placed ahead of the real ones on
//! `PATH`, so each case exercises the real launcher plumbing — argument
//! validation, path confinement, prompt composition, artifact publication, and
//! the launcher envelope — without contacting a vendor service.

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
    command.env_remove("CURSOR_API_KEY");
    command.env_remove("CLAUDE_PLUGIN_ROOT");
    command.env_remove("CLAUDE_PROJECT_DIR");
    command.env_remove("IMPLEMENT_TMPDIR");
    command.env_remove("DESIGN_TMPDIR");
    command.env_remove("REVIEW_TMPDIR");
    command.env_remove("SESSION_ENV_PATH");
    command.env_remove("LARCH_EXECUTION_ISSUES_LOG");
    command.env_remove("LARCH_TOKEN_BUDGET_CAP_IMPLEMENT");
    command.current_dir(root);
    command
}

/// One implement launch's session directory and required inputs.
struct ImplementFixture {
    _root: TempDir,
    path: PathBuf,
    session: PathBuf,
    transcript: PathBuf,
    sidecar: PathBuf,
}

impl ImplementFixture {
    fn create() -> Self {
        let root = TempDir::new().expect("fixture root");
        // macOS resolves the temporary root through a symlink and every
        // launcher publishes canonical paths, so the fixture uses them too.
        let path = fs::canonicalize(root.path()).expect("canonical fixture root");
        fs::create_dir_all(path.join("home")).expect("fixture home");
        fs::create_dir_all(path.join("bin")).expect("fixture bin");
        let session = path.join("session");
        fs::create_dir_all(&session).expect("session directory");
        write(&path.join("plan.txt"), "plan body\n");
        write(&path.join("feature.txt"), "feature body\n");
        write(
            &path.join("agent.md"),
            "---\ndescription: x\n---\nsystem prompt body\n",
        );
        Self {
            _root: root,
            transcript: session.join("transcript.txt"),
            sidecar: path.join("impl.log"),
            session,
            path,
        }
    }

    fn command(&self, verb: &str) -> AssertCommand {
        let mut command = launcher(&self.path);
        command.args([
            "agent",
            verb,
            "--transcript-path",
            &self.transcript.display().to_string(),
            "--sidecar-log",
            &self.sidecar.display().to_string(),
            "--manifest-path",
            &self.session.join("manifest.json").display().to_string(),
            "--qa-pending-path",
            &self.session.join("qa-pending.json").display().to_string(),
            "--scout-manifest-path",
            &self.session.join("scout.json").display().to_string(),
            "--plan-file",
            &self.path.join("plan.txt").display().to_string(),
            "--feature-file",
            &self.path.join("feature.txt").display().to_string(),
            "--agent-prompt",
            &self.path.join("agent.md").display().to_string(),
            "--timeout",
            "30",
        ]);
        command
    }

    fn artifact(&self, suffix: &str) -> String {
        fs::read_to_string(format!("{}{suffix}", self.transcript.display())).unwrap_or_default()
    }
}

#[test]
fn a_missing_coder_binary_publishes_the_documented_envelope() {
    for verb in ["launch-codex-implement", "launch-cursor-implement"] {
        let fixture = ImplementFixture::create();
        let assert = fixture.command(verb).assert().success();
        let stdout = String::from_utf8_lossy(&assert.get_output().stdout).into_owned();
        assert!(stdout.contains("LAUNCHER_EXIT=127"), "{verb}: {stdout}");
        assert!(
            stdout.contains("MANIFEST_WRITTEN=false"),
            "{verb}: {stdout}"
        );
        assert!(
            stdout.contains("QA_PENDING_WRITTEN=false"),
            "{verb}: {stdout}"
        );
        assert!(
            stdout.contains("SCOUT_MANIFEST_WRITTEN=false"),
            "{verb}: {stdout}"
        );
        assert!(stdout.contains("TRANSCRIPT="), "{verb}: {stdout}");
        assert!(stdout.contains("SIDECAR_LOG="), "{verb}: {stdout}");
        let sidecar = fs::read_to_string(&fixture.sidecar).unwrap_or_default();
        assert!(sidecar.contains("binary missing"), "{verb}: {sidecar}");
        assert!(!fixture.artifact(".stderr-tail").is_empty(), "{verb}");
    }
}

#[test]
fn implement_arguments_are_refused_in_the_legacy_order() {
    for (verb, tool) in [
        ("launch-codex-implement", "codex"),
        ("launch-cursor-implement", "cursor"),
    ] {
        let fixture = ImplementFixture::create();
        let cases: [(&[&str], String); 3] = [
            (
                &["--timeout", "0"],
                format!(
                    "agent launch-{tool}-implement: --timeout must be a positive integer (seconds), got '0'"
                ),
            ),
            (
                &["--token-budget-cap", "abc"],
                format!(
                    "agent launch-{tool}-implement: --token-budget-cap requires a positive integer"
                ),
            ),
            (
                &["--answers-file", "/nonexistent/answers.md"],
                format!(
                    "agent launch-{tool}-implement: --answers-file given but path does not exist"
                ),
            ),
        ];
        for (extra, message) in cases {
            let mut command = fixture.command(verb);
            command.args(extra);
            let assert = command.assert().code(2);
            let stderr = String::from_utf8_lossy(&assert.get_output().stderr).into_owned();
            assert!(
                stderr.contains(&message),
                "expected {message:?}: {stderr:?}"
            );
        }
        // The flag-like value is assembled at run time: the timing-allowlist
        // scanner reads an adjacent literal pair as a declared task kind.
        let flag_like = format!("--{}", "flagged");
        let mut command = fixture.command(verb);
        command.args(["--timing-task-kind".to_owned(), flag_like]);
        let assert = command.assert().code(2);
        let stderr = String::from_utf8_lossy(&assert.get_output().stderr).into_owned();
        assert!(
            stderr.contains(&format!(
                "agent launch-{tool}-implement: --timing-task-kind requires a non-empty, non-flag-like value"
            )),
            "stderr: {stderr}"
        );
    }
}

#[test]
fn a_missing_required_input_and_an_unknown_flag_are_rejected() {
    let fixture = ImplementFixture::create();
    let mut missing = launcher(&fixture.path);
    missing.args(["agent", "launch-codex-implement", "--timeout", "30"]);
    let assert = missing.assert().code(2);
    let stderr = String::from_utf8_lossy(&assert.get_output().stderr).into_owned();
    assert!(
        stderr.contains("the following arguments are required: --transcript-path"),
        "stderr: {stderr}"
    );

    let mut unknown = fixture.command("launch-cursor-implement");
    unknown.args(["--nope", "1"]);
    let assert = unknown.assert().code(2);
    let stderr = String::from_utf8_lossy(&assert.get_output().stderr).into_owned();
    assert!(
        stderr.contains("unrecognized arguments: --nope"),
        "stderr: {stderr}"
    );

    let mut choice = fixture.command("launch-codex-implement");
    choice.args(["--difficulty", "EASY"]);
    let assert = choice.assert().code(2);
    let stderr = String::from_utf8_lossy(&assert.get_output().stderr).into_owned();
    assert!(
        stderr.contains("argument --difficulty: invalid choice: 'EASY'"),
        "stderr: {stderr}"
    );
}

#[test]
fn a_missing_plan_file_names_the_flag_it_could_not_read() {
    let fixture = ImplementFixture::create();
    fs::remove_file(fixture.path.join("plan.txt")).expect("remove plan");
    let assert = fixture.command("launch-codex-implement").assert().code(2);
    let stderr = String::from_utf8_lossy(&assert.get_output().stderr).into_owned();
    assert!(
        stderr.contains("agent launch-codex-implement: plan-file not found:"),
        "stderr: {stderr}"
    );
}

#[test]
fn help_prints_the_usage_line_for_every_implement_launcher() {
    for verb in ["launch-codex-implement", "launch-cursor-implement"] {
        let fixture = ImplementFixture::create();
        let mut command = launcher(&fixture.path);
        command.args(["agent", verb, "--help"]);
        let assert = command.assert().success();
        let stderr = String::from_utf8_lossy(&assert.get_output().stderr).into_owned();
        assert!(
            stderr.contains(&format!("usage: cli.py agent {verb}")),
            "{verb}"
        );
    }
}

#[test]
fn the_codex_launcher_refuses_artifacts_outside_one_session_directory() {
    let fixture = ImplementFixture::create();
    let other = fixture.path.join("other");
    fs::create_dir_all(&other).expect("other directory");
    let mut command = fixture.command("launch-codex-implement");
    command.args([
        "--qa-pending-path",
        &other.join("qa-pending.json").display().to_string(),
    ]);
    let assert = command.assert().code(2);
    let stderr = String::from_utf8_lossy(&assert.get_output().stderr).into_owned();
    assert!(
        stderr.contains("--qa-pending-path must share the parent directory with --manifest-path"),
        "stderr: {stderr}"
    );
}

#[test]
fn the_codex_launcher_refuses_the_implement_session_root_as_its_grant() {
    let fixture = ImplementFixture::create();
    let mut command = fixture.command("launch-codex-implement");
    command.env("IMPLEMENT_TMPDIR", &fixture.session);
    let assert = command.assert().code(2);
    let stderr = String::from_utf8_lossy(&assert.get_output().stderr).into_owned();
    assert!(
        stderr.contains("must not be the implement session tmpdir root"),
        "stderr: {stderr}"
    );
}

#[test]
fn the_codex_launcher_refuses_a_symlinked_artifact_parent() {
    let fixture = ImplementFixture::create();
    let real = fixture.path.join("real-session");
    fs::create_dir_all(&real).expect("real session");
    let linked = fixture.path.join("linked-session");
    std::os::unix::fs::symlink(&real, &linked).expect("symlink session");
    let mut command = launcher(&fixture.path);
    command.args([
        "agent",
        "launch-codex-implement",
        "--transcript-path",
        &linked.join("transcript.txt").display().to_string(),
        "--sidecar-log",
        &fixture.sidecar.display().to_string(),
        "--manifest-path",
        &linked.join("manifest.json").display().to_string(),
        "--qa-pending-path",
        &linked.join("qa-pending.json").display().to_string(),
        "--scout-manifest-path",
        &linked.join("scout.json").display().to_string(),
        "--plan-file",
        &fixture.path.join("plan.txt").display().to_string(),
        "--feature-file",
        &fixture.path.join("feature.txt").display().to_string(),
        "--agent-prompt",
        &fixture.path.join("agent.md").display().to_string(),
        "--timeout",
        "30",
    ]);
    let assert = command.assert().code(2);
    let stderr = String::from_utf8_lossy(&assert.get_output().stderr).into_owned();
    assert!(
        stderr.contains("parent is not a directory"),
        "stderr: {stderr}"
    );
}

#[test]
fn the_cursor_launcher_refuses_a_scout_manifest_in_another_directory() {
    let fixture = ImplementFixture::create();
    let other = fixture.path.join("other");
    fs::create_dir_all(&other).expect("other directory");
    let mut command = fixture.command("launch-cursor-implement");
    command.args([
        "--scout-manifest-path",
        &other.join("scout.json").display().to_string(),
    ]);
    let assert = command.assert().code(2);
    let stderr = String::from_utf8_lossy(&assert.get_output().stderr).into_owned();
    assert!(
        stderr
            .contains("--scout-manifest-path must share the parent directory with --manifest-path"),
        "stderr: {stderr}"
    );
}

#[test]
fn an_empty_agent_prompt_body_is_refused_before_the_codex_home_is_built() {
    let fixture = ImplementFixture::create();
    write(
        &fixture.path.join("agent.md"),
        "---\ndescription: x\n---\n\n",
    );
    let assert = fixture.command("launch-codex-implement").assert().code(2);
    let stderr = String::from_utf8_lossy(&assert.get_output().stderr).into_owned();
    assert!(
        stderr.contains("agent prompt body is empty after frontmatter stripping"),
        "stderr: {stderr}"
    );
}

#[test]
fn an_agent_prompt_body_with_a_toml_delimiter_is_refused() {
    let fixture = ImplementFixture::create();
    write(
        &fixture.path.join("agent.md"),
        "---\ndescription: x\n---\nbody with ''' inside\n",
    );
    let assert = fixture.command("launch-codex-implement").assert().code(2);
    let stderr = String::from_utf8_lossy(&assert.get_output().stderr).into_owned();
    assert!(
        stderr.contains("contains TOML triple-single-quote delimiter"),
        "stderr: {stderr}"
    );
}

/// A Codex fixture that publishes a transcript and a usage event.
const CODEX_FIXTURE: &str = concat!(
    "#!/bin/sh\n",
    "output=\"\"\n",
    "last=\"\"\n",
    "for arg in \"$@\"; do\n",
    "  if [ \"$last\" = \"--output-last-message\" ]; then output=\"$arg\"; fi\n",
    "  last=\"$arg\"\n",
    "done\n",
    "[ -n \"$output\" ] || exit 9\n",
    "printf 'codex transcript\\n' > \"$output\"\n",
    "printf '%s\\n' '{\"usage\":{\"input_tokens\":10,\"cache_read_input_tokens\":4,\"output_tokens\":6}}'\n",
);

#[test]
fn the_codex_launcher_publishes_the_prompt_grants_and_outer_meta_record() {
    let fixture = ImplementFixture::create();
    vendor_fixture(&fixture.path, "codex", CODEX_FIXTURE);
    let implement = fixture.path.join("implement");
    fs::create_dir_all(&implement).expect("implement tmpdir");
    let mut command = fixture.command("launch-codex-implement");
    command.env("IMPLEMENT_TMPDIR", &implement);
    let assert = command.assert().success();
    let stdout = String::from_utf8_lossy(&assert.get_output().stdout).into_owned();
    assert!(stdout.contains("LAUNCHER_EXIT=0"), "stdout: {stdout}");
    let prompt = fixture.artifact(".prompt");
    // Codex reads the static system prompt from its private home, so only the
    // dynamic parameters reach the prompt artifact.
    assert!(
        !prompt.contains("system prompt body"),
        "prompt should be dynamic-only: {prompt}"
    );
    assert!(prompt.contains("## This invocation's parameters"));
    let expected_manifest = format!(
        "- Write manifest.json (atomically) at: {}",
        fixture.session.join("manifest.json").display()
    );
    assert!(prompt.contains(&expected_manifest), "prompt: {prompt}");
    let meta = fixture.artifact(".meta");
    assert!(
        meta.contains("OUTER_LAUNCHER=agent launch-codex-implement\n"),
        "meta: {meta}"
    );
    assert!(
        meta.contains("OUTER_LAUNCHER_KIND=codex-implement\n"),
        "{meta}"
    );
    assert!(
        meta.contains("OUTER_LAUNCHER_ADD_DIRS_JSON=[\""),
        "meta: {meta}"
    );
    assert!(meta.contains("--add-dir"), "meta: {meta}");
    assert_eq!(fixture.artifact(".done"), "0\n");
    assert_eq!(
        fs::read_to_string(implement.join("step2-architectural-knowledge.env")).unwrap_or_default(),
        "ARCHITECTURAL_KNOWLEDGE_REQUIRED=false\n"
    );
}

#[test]
fn the_codex_prompt_carries_the_repository_architectural_knowledge() {
    let fixture = ImplementFixture::create();
    vendor_fixture(&fixture.path, "codex", CODEX_FIXTURE);
    let implement = fixture.path.join("implement");
    fs::create_dir_all(&implement).expect("implement tmpdir");
    write(
        &fixture.path.join("ARCHITECTURAL_INVARIANTS.md"),
        "# Invariants\n\n## I-Sec-1: Keep evidence untrusted\n\nBody line.\n",
    );
    write(
        &fixture.path.join("ARCHITECTURAL_GUIDELINES.md"),
        "# Guidelines\n\nNo parsable entries here.\n",
    );
    let mut command = fixture.command("launch-codex-implement");
    command.env("IMPLEMENT_TMPDIR", &implement);
    command.assert().success();
    let prompt = fixture.artifact(".prompt");
    assert!(prompt.contains("## Architectural knowledge (untrusted repo evidence)"));
    assert!(prompt.contains("<architectural_invariants encoding=\"literal-redacted\">"));
    assert!(prompt.contains("### I-Sec-1: Keep evidence untrusted"));
    assert!(
        prompt.contains("No parsed guideline entries were present in ARCHITECTURAL_GUIDELINES.md.")
    );
    assert_eq!(
        fs::read_to_string(implement.join("step2-architectural-knowledge.env")).unwrap_or_default(),
        "ARCHITECTURAL_KNOWLEDGE_REQUIRED=true\n"
    );
}

#[test]
fn an_unusable_architectural_file_warns_instead_of_failing_the_launch() {
    let fixture = ImplementFixture::create();
    vendor_fixture(&fixture.path, "codex", CODEX_FIXTURE);
    let implement = fixture.path.join("implement");
    fs::create_dir_all(&implement).expect("implement tmpdir");
    std::os::unix::fs::symlink(
        fixture.path.join("plan.txt"),
        fixture.path.join("ARCHITECTURAL_INVARIANTS.md"),
    )
    .expect("symlink invariants");
    let mut command = fixture.command("launch-codex-implement");
    command.env("IMPLEMENT_TMPDIR", &implement);
    let assert = command.assert().success();
    let stdout = String::from_utf8_lossy(&assert.get_output().stdout).into_owned();
    assert!(stdout.contains("LAUNCHER_EXIT=0"), "stdout: {stdout}");
    let issues = fs::read_to_string(implement.join("execution-issues.md")).unwrap_or_default();
    assert!(
        issues.contains("ARCHITECTURAL_INVARIANTS.md is invalid: symlinks are not read"),
        "execution issues: {issues}"
    );
    assert!(
        !fixture
            .artifact(".prompt")
            .contains("<architectural_invariants")
    );
}

#[test]
fn a_failing_codex_launch_records_the_step_two_failure() {
    let fixture = ImplementFixture::create();
    vendor_fixture(
        &fixture.path,
        "codex",
        "#!/bin/sh\nprintf 'codex boom\\n' >&2\nexit 4\n",
    );
    let implement = fixture.path.join("implement");
    fs::create_dir_all(&implement).expect("implement tmpdir");
    let mut command = fixture.command("launch-codex-implement");
    command.env("IMPLEMENT_TMPDIR", &implement);
    command.env("LARCH_EXTERNAL_AUTH_RETRIES", "1");
    let assert = command.assert().success();
    let stdout = String::from_utf8_lossy(&assert.get_output().stdout).into_owned();
    assert!(stdout.contains("LAUNCHER_EXIT=4"), "stdout: {stdout}");
    let issues = fs::read_to_string(implement.join("execution-issues.md")).unwrap_or_default();
    assert!(issues.contains("codex-implement"), "issues: {issues}");
    assert!(issues.contains("implement Step 2"), "issues: {issues}");
    assert!(!fixture.artifact(".stderr-tail").is_empty());
    let parts = implement.join("vendor-failure-diagnostics.parts");
    let staged = fs::read_dir(&parts)
        .map(std::iter::Iterator::count)
        .unwrap_or(0);
    assert!(staged > 0, "expected a staged diagnostic part in {parts:?}");
}

#[test]
fn a_hit_token_budget_cap_skips_the_coder_and_publishes_the_cap_artifacts() {
    let fixture = ImplementFixture::create();
    vendor_fixture(&fixture.path, "codex", CODEX_FIXTURE);
    // A plugin root whose dispatcher reports a cap hit stands in for the still
    // Python-owned `token check-budget` verb.
    let plugin = fixture.path.join("plugin");
    write(
        &plugin.join("python/cli.py"),
        "import sys\nprint('STATUS=cap_hit TOTAL=1234')\n",
    );
    let implement = fixture.path.join("implement");
    fs::create_dir_all(&implement).expect("implement tmpdir");
    let mut command = fixture.command("launch-codex-implement");
    command.env("CLAUDE_PLUGIN_ROOT", &plugin);
    command.env("IMPLEMENT_TMPDIR", &implement);
    command.env("LARCH_TOKEN_BUDGET_CAP_IMPLEMENT", "10");
    let assert = command.assert().success();
    let stdout = String::from_utf8_lossy(&assert.get_output().stdout).into_owned();
    assert!(stdout.contains("STATUS=cap_hit"), "stdout: {stdout}");
    assert!(stdout.contains("LAUNCHER_EXIT=0"), "stdout: {stdout}");
    let stderr = String::from_utf8_lossy(&assert.get_output().stderr).into_owned();
    assert!(
        stderr
            .contains("step token budget cap of 10 tokens exceeded (1234 combined vendor tokens)"),
        "stderr: {stderr}"
    );
    assert_eq!(fixture.artifact(""), "STATUS=cap_hit\n");
    assert!(fixture.artifact(".cap-hit").contains("STATUS=cap_hit"));
    assert!(
        fs::read_to_string(implement.join("step-budget-cap-hit.env"))
            .unwrap_or_default()
            .contains("STATUS=cap_hit")
    );
}

/// A Cursor fixture that publishes a JSON result envelope with usage.
const CURSOR_FIXTURE: &str = concat!(
    "#!/bin/sh\n",
    "printf '%s\\n' '{\"result\":\"done\",\"usage\":{\"inputTokens\":1,\"outputTokens\":2,\"cacheReadTokens\":3,\"cacheWriteTokens\":4}}'\n",
);

#[test]
fn the_cursor_launcher_wraps_the_prompt_and_publishes_the_outer_meta_record() {
    let fixture = ImplementFixture::create();
    vendor_fixture(&fixture.path, "cursor", CURSOR_FIXTURE);
    let mut command = fixture.command("launch-cursor-implement");
    command.env("CURSOR_API_KEY", "test-cursor-api-key");
    let assert = command.assert().success();
    let stdout = String::from_utf8_lossy(&assert.get_output().stdout).into_owned();
    assert!(stdout.contains("LAUNCHER_EXIT=0"), "stdout: {stdout}");
    let prompt = fixture.artifact(".prompt");
    // Cursor gets the agent prompt file verbatim, and the artifact keeps the
    // unwrapped text while the vendor receives the max-mode wrapper.
    assert!(
        prompt.starts_with("---\ndescription: x\n---\nsystem prompt body\n"),
        "prompt: {prompt}"
    );
    assert!(!prompt.contains("/max-mode on."), "prompt: {prompt}");
    let meta = fixture.artifact(".meta");
    assert!(
        meta.contains("OUTER_LAUNCHER=agent launch-cursor-implement\n"),
        "meta: {meta}"
    );
    assert!(meta.contains("/max-mode on. Prompt: "), "meta: {meta}");
    assert!(meta.contains("--output-format"), "meta: {meta}");
    assert_eq!(fixture.artifact(".done"), "0\n");
}

#[test]
fn the_cursor_launcher_pins_the_model_for_a_difficulty_tier() {
    for (tier, model) in [
        ("TRIVIAL", "cursor-grok-4.6-high"),
        ("HARD", "composer-2.5"),
    ] {
        let fixture = ImplementFixture::create();
        vendor_fixture(&fixture.path, "cursor", CURSOR_FIXTURE);
        let mut command = fixture.command("launch-cursor-implement");
        command.env("CURSOR_API_KEY", "test-cursor-api-key");
        command.args(["--difficulty", tier]);
        command.assert().success();
        let meta = fixture.artifact(".meta");
        assert!(meta.contains(model), "{tier} meta: {meta}");
    }
}

#[test]
fn the_resume_and_completion_retry_blocks_reach_the_coder_prompt() {
    let fixture = ImplementFixture::create();
    vendor_fixture(&fixture.path, "cursor", CURSOR_FIXTURE);
    let answers = fixture.path.join("answers.md");
    write(&answers, "operator answers\n");
    let retry = fixture.path.join("completion-retry.md");
    write(&retry, "Required path: docs/expected.md\n");
    let mut command = fixture.command("launch-cursor-implement");
    command.env("CURSOR_API_KEY", "test-cursor-api-key");
    command.args([
        "--answers-file",
        &answers.display().to_string(),
        "--completion-retry-file",
        &retry.display().to_string(),
    ]);
    command.assert().success();
    let prompt = fixture.artifact(".prompt");
    assert!(prompt.contains("## Resume invocation"), "prompt: {prompt}");
    assert!(prompt.contains("skills/implement/prompts/cursor-implementer.md"));
    assert!(prompt.contains("## Completion retry"), "prompt: {prompt}");
    assert!(prompt.contains("<completion_retry encoding=\"literal-redacted\">"));
    assert!(prompt.contains("Required path: docs/expected.md"));
}

// ---------------------------------------------------------------------------
// Claude fix launchers
// ---------------------------------------------------------------------------

/// One Claude fix launch's output and prompt body.
struct ClaudeFixFixture {
    _root: TempDir,
    path: PathBuf,
    output: PathBuf,
    prompt_body: PathBuf,
}

impl ClaudeFixFixture {
    fn create() -> Self {
        let root = TempDir::new().expect("fixture root");
        // macOS resolves the temporary root through a symlink and every
        // launcher publishes canonical paths, so the fixture uses them too.
        let path = fs::canonicalize(root.path()).expect("canonical fixture root");
        fs::create_dir_all(path.join("home")).expect("fixture home");
        fs::create_dir_all(path.join("bin")).expect("fixture bin");
        let prompt_body = path.join("prompt-body.md");
        write(&prompt_body, "fix the lint failure\n");
        Self {
            _root: root,
            output: path.join("fix.out"),
            prompt_body,
            path,
        }
    }

    fn command(&self, verb: &str) -> AssertCommand {
        let mut command = launcher(&self.path);
        command.args([
            "agent",
            verb,
            "--prompt-body-file",
            &self.prompt_body.display().to_string(),
            "--output",
            &self.output.display().to_string(),
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
fn a_missing_claude_binary_publishes_the_fix_refusal_bundle() {
    for verb in ["launch-claude-lint-fix", "launch-claude-review-fix"] {
        let fixture = ClaudeFixFixture::create();
        let assert = fixture.command(verb).assert().success();
        let stdout = String::from_utf8_lossy(&assert.get_output().stdout).into_owned();
        assert!(stdout.contains("LAUNCHER_EXIT=127"), "{verb}: {stdout}");
        assert_eq!(
            fixture.artifact(".diag"),
            "STATUS=FAILED\nFAILURE_REASON=claude binary missing\n"
        );
        assert!(fixture.artifact(".meta").contains("TOOL=claude\n"));
        assert_eq!(fixture.artifact(".done"), "127\n");
    }
}

#[test]
fn the_fix_launchers_publish_the_envelope_result_and_their_ledger_labels() {
    for (verb, role, raw, model) in [
        (
            "launch-claude-lint-fix",
            "You are Claude fixing local larch lint or check failures.",
            "claude_lint_fix",
            "claude-opus-4-8",
        ),
        (
            "launch-claude-review-fix",
            "You are Claude applying accepted review findings to the working tree.",
            "claude_review_fix",
            "claude-sonnet-4-6",
        ),
    ] {
        let fixture = ClaudeFixFixture::create();
        vendor_fixture(
            &fixture.path,
            "claude",
            "#!/bin/sh\ncat > /dev/null\nprintf '%s' '{\"result\":\"patched\",\"usage\":{\"input_tokens\":4,\"output_tokens\":3,\"cache_read_input_tokens\":2,\"cache_creation_input_tokens\":1}}'\n",
        );
        let assert = fixture.command(verb).assert().success();
        let stdout = String::from_utf8_lossy(&assert.get_output().stdout).into_owned();
        assert!(stdout.contains("LAUNCHER_EXIT=0"), "{verb}: {stdout}");
        assert_eq!(fixture.artifact(""), "patched");
        assert_eq!(fixture.artifact(".done"), "0\n");
        let prompt = fixture.artifact(".prompt");
        assert!(prompt.starts_with(role), "{verb} prompt: {prompt}");
        assert!(prompt.contains("fix the lint failure"), "{verb}");
        let token_record = fixture.artifact(".token-record");
        assert!(
            token_record.contains(&format!("MODEL={model}\n")),
            "{verb} token record: {token_record}"
        );
        assert!(
            token_record.contains(&format!("RAW={raw}\n")),
            "{verb} token record: {token_record}"
        );
    }
}

#[test]
fn a_non_json_fix_response_is_refused_rather_than_published() {
    let fixture = ClaudeFixFixture::create();
    vendor_fixture(
        &fixture.path,
        "claude",
        "#!/bin/sh\ncat > /dev/null\nprintf '%s' 'not json'\n",
    );
    let assert = fixture.command("launch-claude-lint-fix").assert().success();
    let stdout = String::from_utf8_lossy(&assert.get_output().stdout).into_owned();
    assert!(stdout.contains("LAUNCHER_EXIT=1"), "stdout: {stdout}");
    assert_eq!(fixture.artifact(""), "CLAUDE_LINT_FIX_MALFORMED_JSON\n");
    assert!(
        fixture
            .artifact(".diag")
            .contains("Malformed Claude lint-fix JSON")
    );
}

#[test]
fn a_fix_envelope_error_and_empty_result_publish_their_markers() {
    for (body, marker) in [
        ("{\"is_error\":true,\"result\":\"boom\"}", "ERROR_RESPONSE"),
        ("{\"other\":1}", "EMPTY_RESULT"),
    ] {
        let fixture = ClaudeFixFixture::create();
        vendor_fixture(
            &fixture.path,
            "claude",
            &format!("#!/bin/sh\ncat > /dev/null\nprintf '%s' '{body}'\n"),
        );
        fixture
            .command("launch-claude-review-fix")
            .assert()
            .success();
        assert_eq!(
            fixture.artifact(""),
            format!("CLAUDE_REVIEW_FIX_{marker}\n")
        );
        assert_eq!(fixture.artifact(".done"), "1\n");
    }
}

#[test]
fn fix_arguments_are_refused_in_the_legacy_order() {
    let fixture = ClaudeFixFixture::create();
    let cases: [(&[&str], &str); 2] = [
        (
            &["--timeout", "0"],
            "agent launch-claude-lint-fix: --timeout must be a positive integer",
        ),
        (
            &["--model", "two tokens"],
            "agent launch-claude-lint-fix: --model must be a single non-empty token",
        ),
    ];
    for (extra, message) in cases {
        let mut command = fixture.command("launch-claude-lint-fix");
        command.args(extra);
        let assert = command.assert().code(2);
        let stderr = String::from_utf8_lossy(&assert.get_output().stderr).into_owned();
        assert!(stderr.contains(message), "expected {message:?}: {stderr:?}");
    }

    let mut relative = launcher(&fixture.path);
    relative.args([
        "agent",
        "launch-claude-review-fix",
        "--prompt-body-file",
        &fixture.prompt_body.display().to_string(),
        "--output",
        "relative.out",
    ]);
    let assert = relative.assert().code(2);
    let stderr = String::from_utf8_lossy(&assert.get_output().stderr).into_owned();
    assert!(
        stderr.contains("--output-file must be an absolute safe path"),
        "stderr: {stderr}"
    );
}

#[test]
fn a_prompt_body_outside_the_session_and_repository_roots_is_refused() {
    let fixture = ClaudeFixFixture::create();
    let outside = TempDir::new().expect("outside root");
    let body = outside.path().join("prompt.md");
    write(&body, "elsewhere\n");
    let mut command = launcher(&fixture.path);
    command.args([
        "agent",
        "launch-claude-lint-fix",
        "--prompt-body-file",
        &body.display().to_string(),
        "--output",
        &fixture.output.display().to_string(),
    ]);
    let assert = command.assert().code(2);
    let stderr = String::from_utf8_lossy(&assert.get_output().stderr).into_owned();
    assert!(
        stderr.contains("prompt file outside allowed roots"),
        "stderr: {stderr}"
    );
}

#[test]
fn help_prints_the_usage_line_for_every_fix_launcher() {
    for verb in ["launch-claude-lint-fix", "launch-claude-review-fix"] {
        let fixture = ClaudeFixFixture::create();
        let mut command = launcher(&fixture.path);
        command.args(["agent", verb, "--help"]);
        let assert = command.assert().success();
        let stderr = String::from_utf8_lossy(&assert.get_output().stderr).into_owned();
        assert!(
            stderr.contains(&format!("usage: cli.py agent {verb}")),
            "{verb}"
        );
    }
}

#[test]
fn only_the_review_fix_launcher_accepts_a_timing_task_kind() {
    let fixture = ClaudeFixFixture::create();
    let mut lint = fixture.command("launch-claude-lint-fix");
    lint.args(["--timing-task-kind", "claude-review-fix"]);
    let assert = lint.assert().code(2);
    let stderr = String::from_utf8_lossy(&assert.get_output().stderr).into_owned();
    assert!(
        stderr.contains("unrecognized arguments: --timing-task-kind"),
        "stderr: {stderr}"
    );

    let mut review = fixture.command("launch-claude-review-fix");
    review.args(["--timing-task-kind", "claude-review-fix"]);
    review.assert().success();
}
