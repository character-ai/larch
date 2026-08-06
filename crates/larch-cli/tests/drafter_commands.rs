//! End-to-end coverage for the drafter, negotiation, and Codex exec launchers.
//!
//! Vendor executables are shell fixtures placed ahead of the real ones on
//! `PATH`, so every case exercises the real launcher plumbing — argument
//! validation, private Codex home, artifact publication, and status files —
//! without contacting a vendor service.

#![cfg(unix)]

use std::{
    env, fs,
    os::unix::fs::PermissionsExt as _,
    path::{Path, PathBuf},
};

use assert_cmd::Command as AssertCommand;
use tempfile::TempDir;

const PLAN: &str = "LARCH_PLAN_BEGIN\n### NEW: a.rs\nwork\ndiff_lines: 12\nLARCH_PLAN_END\n";

fn larch() -> AssertCommand {
    AssertCommand::cargo_bin("larch").expect("larch binary should build")
}

fn write(path: &Path, contents: &str) {
    let parent = path.parent().expect("fixture path has parent");
    fs::create_dir_all(parent).expect("create fixture parent");
    fs::write(path, contents).expect("write fixture");
}

fn vendor_fixture(root: &Path, name: &str, body: &str) -> PathBuf {
    let bin = root.join("bin");
    fs::create_dir_all(&bin).expect("fixture bin");
    let executable = bin.join(name);
    write(&executable, body);
    fs::set_permissions(&executable, fs::Permissions::from_mode(0o755))
        .expect("fixture executable permissions");
    executable
}

/// Build a launcher invocation whose `PATH` resolves the fixture vendor first.
fn launcher(root: &Path) -> AssertCommand {
    let current = env::var_os("PATH").unwrap_or_default();
    let path = env::join_paths(std::iter::once(root.join("bin")).chain(env::split_paths(&current)))
        .expect("fixture PATH");
    let mut command = larch();
    command.env("PATH", path);
    command.env("HOME", root.join("home"));
    command.env_remove("OPENAI_API_KEY");
    command.env_remove("CLAUDE_PLUGIN_ROOT");
    command.current_dir(root);
    command
}

/// A design tmpdir with the prompt and repository the drafters require.
struct DraftFixture {
    _root: TempDir,
    path: PathBuf,
    design: PathBuf,
    repo: PathBuf,
    prompt: PathBuf,
    status: PathBuf,
}

impl DraftFixture {
    fn new() -> Self {
        let root = TempDir::new().expect("fixture");
        // Resolve `/var` style symlinks so containment checks see stable paths.
        let path = fs::canonicalize(root.path()).expect("canonical fixture root");
        let design = path.join("design");
        let repo = path.join("repo");
        fs::create_dir_all(&design).expect("design tmpdir");
        fs::create_dir_all(&repo).expect("repo root");
        fs::create_dir_all(path.join("home")).expect("private home");
        let prompt = design.join("step2b-drafter-prompt.txt");
        write(&prompt, "draft a plan\n");
        Self {
            _root: root,
            status: design.join("step2b-drafter-status.txt"),
            path,
            design,
            repo,
            prompt,
        }
    }

    fn codex_drafter(&self) -> AssertCommand {
        let mut command = launcher(&self.path);
        command.args(["agent", "launch-codex-drafter", "--prompt-file"]);
        command
            .arg(&self.prompt)
            .arg("--output-file")
            .arg(&self.status)
            .args(["--timeout", "60", "--design-tmpdir"])
            .arg(&self.design)
            .arg("--repo-root")
            .arg(&self.repo);
        command
    }

    fn status_text(&self) -> String {
        fs::read_to_string(&self.status).unwrap_or_default()
    }
}

/// A Codex fixture that writes `plan` to the launcher's `--output-last-message`.
fn codex_writing(plan: &str) -> String {
    format!(
        r#"#!/bin/sh
out=""
prev=""
for arg in "$@"; do
  if [ "$prev" = "--output-last-message" ]; then out="$arg"; fi
  prev="$arg"
done
printf '%s' '{plan}' > "$out"
printf '{{"type":"thread.started","thread_id":"123e4567-e89b-12d3-a456-426614174000"}}\n'
exit 0
"#
    )
}

#[test]
fn codex_drafter_publishes_the_plan_status_and_dirty_tree_sidecar() {
    let fixture = DraftFixture::new();
    vendor_fixture(&fixture.path, "codex", &codex_writing(PLAN));

    fixture.codex_drafter().assert().success();

    let status = fixture.status_text();
    assert!(status.contains("STATUS=OK"), "{status}");
    assert!(status.contains("PLAN_WRITTEN=true"), "{status}");
    assert!(status.contains("PLAN_LINES=3"), "{status}");
    assert!(status.contains("DIFF_LINES=12"), "{status}");
    assert!(status.contains("DRAFTER_LAUNCHED=true"), "{status}");
    assert_eq!(
        fs::read_to_string(fixture.design.join("plan.txt")).expect("published plan"),
        "### NEW: a.rs\nwork\ndiff_lines: 12\n"
    );
    let sidecar = fs::read_to_string(fixture.design.join("step2b-drafter-status.txt.dirty-tree"))
        .expect("dirty-tree sidecar");
    assert!(sidecar.starts_with("STATUS="), "{sidecar}");
    assert_eq!(
        fs::read_to_string(fixture.design.join("step2b-drafter-status.txt.done"))
            .expect("completion sentinel"),
        "0\n"
    );
}

#[test]
fn codex_drafter_reports_a_delimiter_violation_without_publishing_a_plan() {
    let fixture = DraftFixture::new();
    vendor_fixture(
        &fixture.path,
        "codex",
        &codex_writing("LARCH_PLAN_BEGIN\nno trailer\nLARCH_PLAN_END\n"),
    );

    fixture.codex_drafter().assert().code(99);

    let status = fixture.status_text();
    assert!(
        status.contains("REASON=DELIMITER_EXTRACTION_INVALID"),
        "{status}"
    );
    assert!(!fixture.design.join("plan.txt").exists());
    let diag = fs::read_to_string(
        fixture
            .design
            .join("step2b-drafter-status.txt.failure-diag"),
    )
    .expect("failure diagnostic");
    assert!(diag.contains("missing final diff_lines trailer"), "{diag}");
}

#[test]
fn codex_drafter_reports_an_empty_vendor_response() {
    let fixture = DraftFixture::new();
    vendor_fixture(&fixture.path, "codex", "#!/bin/sh\nexit 0\n");

    fixture.codex_drafter().assert().code(1);

    let status = fixture.status_text();
    assert!(status.contains("REASON=CODEX_EMPTY_OUTPUT"), "{status}");
}

#[test]
fn codex_drafter_reports_a_failed_vendor_launch() {
    let fixture = DraftFixture::new();
    vendor_fixture(
        &fixture.path,
        "codex",
        "#!/bin/sh\necho 'codex exploded' >&2\nexit 7\n",
    );

    fixture.codex_drafter().assert().code(7);

    let status = fixture.status_text();
    assert!(status.contains("REASON=CODEX_EXEC_FAILED"), "{status}");
    assert!(status.contains("DRAFTER_LAUNCHED=true"), "{status}");
}

#[test]
fn drafter_arguments_are_rejected_before_any_write() {
    let fixture = DraftFixture::new();
    let escaping = fixture.design.join("..").join("escape.txt");
    let cases: Vec<(&str, Vec<String>)> = vec![
        (
            "launch-codex-drafter",
            vec!["--timeout".to_owned(), "0".to_owned()],
        ),
        (
            "launch-codex-drafter",
            vec!["--timeout".to_owned(), "1801".to_owned()],
        ),
        (
            "launch-codex-drafter",
            vec!["--timing-task-kind".to_owned(), "--not-a-kind".to_owned()],
        ),
        (
            "launch-claude-drafter",
            vec!["--design-tmpdir".to_owned(), escaping.display().to_string()],
        ),
        (
            "launch-claude-drafter",
            vec!["--model".to_owned(), "two tokens".to_owned()],
        ),
        (
            "launch-claude-drafter",
            vec!["--model".to_owned(), String::new()],
        ),
    ];
    for (verb, overrides) in cases {
        let mut command = launcher(&fixture.path);
        command.args(["agent", verb]);
        if verb == "launch-claude-drafter" {
            command.args(["--model", "claude-test"]);
        }
        command
            .arg("--prompt-file")
            .arg(&fixture.prompt)
            .arg("--output-file")
            .arg(&fixture.status)
            .args(["--timeout", "60", "--design-tmpdir"])
            .arg(&fixture.design)
            .arg("--repo-root")
            .arg(&fixture.repo)
            .args(overrides.iter().map(String::as_str));
        command.assert().code(2);
        assert!(
            !fixture.status.exists(),
            "{verb} wrote a status file for a rejected argument set"
        );
    }
}

#[test]
fn claude_drafter_publishes_a_plan_and_records_its_launch_metadata() {
    let fixture = DraftFixture::new();
    let envelope = serde_json::json!({ "result": PLAN }).to_string();
    vendor_fixture(
        &fixture.path,
        "claude",
        &format!("#!/bin/sh\ncat > /dev/null\nprintf '%s' '{envelope}'\nexit 0\n"),
    );

    let mut command = launcher(&fixture.path);
    command
        .args(["agent", "launch-claude-drafter", "--model", "claude-test"])
        .arg("--prompt-file")
        .arg(&fixture.prompt)
        .arg("--output-file")
        .arg(&fixture.status)
        .args(["--timeout", "60", "--design-tmpdir"])
        .arg(&fixture.design)
        .arg("--repo-root")
        .arg(&fixture.repo);
    command.assert().success();

    let status = fixture.status_text();
    assert!(status.contains("STATUS=OK"), "{status}");
    assert_eq!(
        fs::read_to_string(fixture.design.join("plan.txt")).expect("published plan"),
        "### NEW: a.rs\nwork\ndiff_lines: 12\n"
    );
    let meta = fs::read_to_string(fixture.design.join("step2b-drafter-status.txt.meta"))
        .expect("launch metadata");
    assert!(meta.contains("OUTER_LAUNCHER=claude-drafter"), "{meta}");
    assert!(meta.contains("TOOL=claude"), "{meta}");
    assert!(meta.contains("\"--permission-mode\",\"plan\""), "{meta}");
}

#[test]
fn claude_drafter_reports_a_malformed_result_envelope() {
    let fixture = DraftFixture::new();
    vendor_fixture(
        &fixture.path,
        "claude",
        "#!/bin/sh\ncat > /dev/null\nprintf 'not json'\nexit 0\n",
    );

    let mut command = launcher(&fixture.path);
    command
        .args(["agent", "launch-claude-drafter", "--model", "claude-test"])
        .arg("--prompt-file")
        .arg(&fixture.prompt)
        .arg("--output-file")
        .arg(&fixture.status)
        .args(["--timeout", "60", "--design-tmpdir"])
        .arg(&fixture.design)
        .arg("--repo-root")
        .arg(&fixture.repo);
    command.assert().code(99);

    let status = fixture.status_text();
    assert!(
        status.contains("REASON=CLAUDE_JSON_RESULT_INVALID"),
        "{status}"
    );
}

#[test]
fn codex_exec_promotes_its_sentinel_and_records_outer_launcher_metadata() {
    let fixture = DraftFixture::new();
    vendor_fixture(&fixture.path, "codex", &codex_writing("done\n"));
    let output = fixture.path.join("codex-exec-output.txt");

    let mut command = launcher(&fixture.path);
    command
        .args(["agent", "launch-codex-exec", "--output"])
        .arg(&output)
        .args(["--timeout", "60", "--prompt", "do work", "--workdir"])
        .arg(&fixture.repo);
    command.assert().success();

    assert_eq!(
        fs::read_to_string(fixture.path.join("codex-exec-output.txt.prompt"))
            .expect("prompt sidecar"),
        "do work"
    );
    let meta = fs::read_to_string(fixture.path.join("codex-exec-output.txt.meta"))
        .expect("launch metadata");
    assert!(
        meta.contains("OUTER_LAUNCHER=agent launch-codex-exec"),
        "{meta}"
    );
    assert!(meta.contains("OUTER_LAUNCHER_KIND=codex-exec"), "{meta}");
    assert!(
        meta.contains("OUTER_LAUNCHER_SANDBOX=workspace-write"),
        "{meta}"
    );
    assert_eq!(
        fs::read_to_string(fixture.path.join("codex-exec-output.txt.done"))
            .expect("promoted sentinel"),
        "0\n"
    );
    assert!(
        !fixture
            .path
            .join("codex-exec-output.txt.inner.done")
            .exists()
    );
}

#[test]
fn codex_exec_rejects_a_non_positive_timeout_and_an_unsupported_output_path() {
    let fixture = DraftFixture::new();
    let output = fixture.path.join("codex-exec-output.txt");
    let mut bad_timeout = launcher(&fixture.path);
    bad_timeout
        .args(["agent", "launch-codex-exec", "--output"])
        .arg(&output)
        .args(["--timeout", "0", "--prompt", "do work"]);
    bad_timeout.assert().code(2);

    let mut bad_output = launcher(&fixture.path);
    bad_output
        .args(["agent", "launch-codex-exec", "--output"])
        .arg(fixture.path.join("has space.txt"))
        .args(["--timeout", "60", "--prompt", "do work"]);
    bad_output.assert().code(2);
    assert!(!output.exists());
}

#[test]
fn negotiation_round_writes_only_its_response_and_codex_sidecars() {
    let fixture = DraftFixture::new();
    vendor_fixture(
        &fixture.path,
        "codex",
        "#!/bin/sh\ncat > /dev/null\nprintf 'events\\n'\nexit 0\n",
    );
    let prompt = fixture.path.join("negotiation-prompt.txt");
    write(&prompt, "please reconsider\n");
    let output = fixture.path.join("codex-negotiation-output.txt");

    let mut command = launcher(&fixture.path);
    command
        .args([
            "agent",
            "run-negotiation-round",
            "--tool",
            "codex",
            "--prompt-file",
        ])
        .arg(&prompt)
        .arg("--output")
        .arg(&output)
        .arg("--workspace")
        .arg(&fixture.repo);
    command
        .assert()
        .success()
        .stdout(predicates::str::contains("RESPONSE_FILE="));

    // The retired Python round published no launcher artifact family; only the
    // Codex event and diagnostic sidecars sit beside the response.
    let base = fixture.path.join("codex-negotiation-output");
    assert!(base.with_extension("events.jsonl").exists());
    for suffix in [".meta", ".done", ".diag", ".failure-diag"] {
        let stray = PathBuf::from(format!("{}{suffix}", output.display()));
        assert!(!stray.exists(), "negotiation wrote {}", stray.display());
    }
}

#[test]
fn negotiation_round_rejects_a_missing_prompt_and_an_unknown_tool() {
    let fixture = DraftFixture::new();
    let output = fixture.path.join("negotiation-output.txt");

    let mut missing = launcher(&fixture.path);
    missing
        .args([
            "agent",
            "run-negotiation-round",
            "--tool",
            "codex",
            "--prompt-file",
        ])
        .arg(fixture.path.join("absent.txt"))
        .arg("--output")
        .arg(&output)
        .arg("--workspace")
        .arg(&fixture.repo);
    missing.assert().code(1);

    let mut unknown = launcher(&fixture.path);
    unknown
        .args([
            "agent",
            "run-negotiation-round",
            "--tool",
            "claude",
            "--prompt-file",
        ])
        .arg(&fixture.prompt)
        .arg("--output")
        .arg(&output)
        .arg("--workspace")
        .arg(&fixture.repo);
    unknown.assert().code(1).stderr(predicates::str::contains(
        "--tool must be 'codex' or 'cursor'",
    ));
}

/// The repository root, used when a case needs the real still-Python helpers.
fn repository_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .and_then(Path::parent)
        .expect("workspace root")
        .to_path_buf()
}

#[test]
fn codex_drafter_filters_a_scout_manifest_through_the_plan_scout_owner() {
    let fixture = DraftFixture::new();
    let manifest = concat!(
        r#"{"archetypes":[{"name":"alpha","focus_area":"security","weight":1,"#,
        r#""rationale":"why","prompt_body":"body"},"#,
        r#"{"name":"beta","focus_area":"correctness","weight":1,"#,
        r#""rationale":"why","prompt_body":"body"}]}"#,
    );
    vendor_fixture(
        &fixture.path,
        "codex",
        &codex_writing(&format!(
            "{PLAN}LARCH_SCOUT_BEGIN\n{manifest}\nLARCH_SCOUT_END\n"
        )),
    );

    let mut command = fixture.codex_drafter();
    command.env("CLAUDE_PLUGIN_ROOT", repository_root());
    command.assert().success();

    let status = fixture.status_text();
    assert!(status.contains("SCOUT_WRITTEN=true"), "{status}");
    assert!(!status.contains("SCOUT_FAIL_REASON"), "{status}");
    let filtered = fs::read_to_string(fixture.design.join("scout-plan-manifest.json"))
        .expect("filtered scout manifest");
    let parsed: serde_json::Value =
        serde_json::from_str(&filtered).expect("filtered manifest is JSON");
    let archetypes = parsed["archetypes"]
        .as_array()
        .expect("filtered manifest keeps its archetypes array");
    // Plan review caps the panel at one dynamic specialist.
    assert_eq!(archetypes.len(), 1, "{filtered}");
    assert!(archetypes[0]["name"].is_string(), "{filtered}");
    assert!(archetypes[0]["focus_area"].is_string(), "{filtered}");
    // The scratch candidate and filter files never survive the run.
    for stray in fs::read_dir(&fixture.design).expect("design tmpdir") {
        let name = stray.expect("entry").file_name();
        let name = name.to_string_lossy();
        assert!(
            !name.contains("candidate") && !name.contains("filtered"),
            "left scratch file {name}"
        );
    }
}

#[test]
fn codex_drafter_reports_a_scout_block_the_grammar_rejects() {
    let fixture = DraftFixture::new();
    vendor_fixture(
        &fixture.path,
        "codex",
        &codex_writing(&format!(
            "{PLAN}LARCH_SCOUT_BEGIN\n{{\"archetypes\":\"not-a-list\"}}\nLARCH_SCOUT_END\n"
        )),
    );

    let mut command = fixture.codex_drafter();
    command.env("CLAUDE_PLUGIN_ROOT", repository_root());
    command.assert().success();

    let status = fixture.status_text();
    assert!(status.contains("STATUS=OK"), "{status}");
    assert!(status.contains("SCOUT_WRITTEN=false"), "{status}");
    assert!(
        status.contains("SCOUT_FAIL_REASON=invalid_archetypes_shape"),
        "{status}"
    );
}

// ---------------------------------------------------------------------------
// Negotiation round: Cursor
// ---------------------------------------------------------------------------

/// Build a negotiation invocation with Cursor authentication already proved.
///
/// A present `CURSOR_API_KEY` short-circuits the keychain preflight, so the
/// case exercises the launcher rather than the host's credential store.
fn cursor_negotiation(fixture: &DraftFixture, prompt: &Path, output: &Path) -> AssertCommand {
    let mut command = launcher(&fixture.path);
    command.env("CURSOR_API_KEY", "key_fixture");
    command
        .args([
            "agent",
            "run-negotiation-round",
            "--tool",
            "cursor",
            "--prompt-file",
        ])
        .arg(prompt)
        .arg("--output")
        .arg(output)
        .arg("--workspace")
        .arg(&fixture.repo);
    command
}

#[test]
fn cursor_negotiation_round_captures_the_response_and_emits_its_path() {
    let fixture = DraftFixture::new();
    vendor_fixture(
        &fixture.path,
        "cursor",
        "#!/bin/sh\nprintf 'cursor reply\\n'\nprintf 'cursor noise\\n' >&2\nexit 0\n",
    );
    let prompt = fixture.path.join("cursor-negotiation-prompt.txt");
    write(&prompt, "please reconsider\n");
    let output = fixture.path.join("cursor-negotiation-output.txt");

    cursor_negotiation(&fixture, &prompt, &output)
        .assert()
        .success()
        .stdout(predicates::str::contains("RESPONSE_FILE="));

    // Cursor's stderr belongs in the response file the caller reads.
    let response = fs::read_to_string(&output).expect("negotiation response");
    assert!(response.contains("cursor reply"), "{response}");
    assert!(response.contains("cursor noise"), "{response}");
    for suffix in [".meta", ".done", ".diag"] {
        let stray = PathBuf::from(format!("{}{suffix}", output.display()));
        assert!(!stray.exists(), "negotiation wrote {}", stray.display());
    }
}

#[test]
fn cursor_negotiation_round_reports_a_failed_reviewer_as_exit_two() {
    let fixture = DraftFixture::new();
    vendor_fixture(
        &fixture.path,
        "cursor",
        "#!/bin/sh\nprintf 'cursor failed\\n' >&2\nexit 4\n",
    );
    let prompt = fixture.path.join("cursor-negotiation-prompt.txt");
    write(&prompt, "please reconsider\n");
    let output = fixture.path.join("cursor-negotiation-output.txt");

    cursor_negotiation(&fixture, &prompt, &output)
        .assert()
        .code(2);
    assert!(output.exists(), "the response file is always published");
}

#[test]
fn negotiation_round_reports_a_missing_vendor_executable() {
    let fixture = DraftFixture::new();
    let prompt = fixture.path.join("negotiation-prompt.txt");
    write(&prompt, "please reconsider\n");
    let output = fixture.path.join("cursor-negotiation-output.txt");

    let mut command = cursor_negotiation(&fixture, &prompt, &output);
    // Resolve executables only from the empty fixture directory, so a real
    // `cursor` on the developer's PATH cannot satisfy the spawn.
    command.env("PATH", fixture.path.join("bin"));
    command.assert().code(2);
    let response = fs::read_to_string(&output).expect("negotiation response");
    assert!(response.contains("Failed to launch child"), "{response}");
}

#[test]
fn codex_negotiation_round_records_a_failed_reviewer_in_its_sidecar() {
    let fixture = DraftFixture::new();
    vendor_fixture(
        &fixture.path,
        "codex",
        "#!/bin/sh\ncat > /dev/null\nprintf 'codex broke\\n' >&2\nexit 5\n",
    );
    let prompt = fixture.path.join("negotiation-prompt.txt");
    write(&prompt, "please reconsider\n");
    let output = fixture.path.join("codex-negotiation-output.txt");

    let mut command = launcher(&fixture.path);
    command
        .args([
            "agent",
            "run-negotiation-round",
            "--tool",
            "codex",
            "--prompt-file",
        ])
        .arg(&prompt)
        .arg("--output")
        .arg(&output)
        .arg("--workspace")
        .arg(&fixture.repo);
    command.assert().code(2);

    let sidecar = fs::read_to_string(fixture.path.join("codex-negotiation-output.sidecar"))
        .unwrap_or_default();
    assert!(sidecar.contains("codex broke"), "{sidecar}");
}

// ---------------------------------------------------------------------------
// Codex exec
// ---------------------------------------------------------------------------

#[test]
fn codex_exec_resolves_its_workdir_from_the_repository_when_none_is_given() {
    let fixture = DraftFixture::new();
    // A real work tree so the default-workdir resolution has something to find.
    let mut init = AssertCommand::new("git");
    init.current_dir(&fixture.repo).args(["init", "--quiet"]);
    if init.assert().try_success().is_err() {
        return;
    }
    vendor_fixture(&fixture.path, "codex", &codex_writing("done\n"));
    let output = fixture.path.join("codex-exec-output.txt");

    let mut command = launcher(&fixture.path);
    command
        .env("CLAUDE_PROJECT_DIR", &fixture.repo)
        .args(["agent", "launch-codex-exec", "--output"])
        .arg(&output)
        .args(["--timeout", "60", "--prompt", "do work"]);
    command
        .assert()
        .success()
        .stdout(predicates::str::contains("LAUNCHER_EXIT=0"));

    let meta = fs::read_to_string(fixture.path.join("codex-exec-output.txt.meta"))
        .expect("launch metadata");
    let repo = fs::canonicalize(&fixture.repo).expect("canonical repo");
    assert!(
        meta.contains(&format!("OUTER_LAUNCHER_WORKDIR={}", repo.display())),
        "{meta}"
    );
}

#[test]
fn codex_exec_publishes_a_refusal_bundle_when_model_arguments_cannot_resolve() {
    let fixture = DraftFixture::new();
    vendor_fixture(&fixture.path, "codex", &codex_writing("done\n"));
    let output = fixture.path.join("codex-exec-output.txt");

    let mut command = launcher(&fixture.path);
    command
        .env("LARCH_CODEX_MODEL", "   ")
        .args(["agent", "launch-codex-exec", "--output"])
        .arg(&output)
        .args(["--timeout", "60", "--prompt", "do work", "--workdir"])
        .arg(&fixture.repo);
    command
        .assert()
        .success()
        .stdout(predicates::str::contains("LAUNCHER_FAILURE_CLASS="));

    let diag = fs::read_to_string(fixture.path.join("codex-exec-output.txt.diag"))
        .expect("refusal diagnostic");
    assert!(diag.contains("STATUS=FAILED"), "{diag}");
    assert!(diag.contains("model args failed"), "{diag}");
    assert_eq!(
        fs::read_to_string(fixture.path.join("codex-exec-output.txt.done"))
            .expect("refusal sentinel"),
        "1\n"
    );
    // A refusal runs no vendor, so it publishes an empty output file.
    assert_eq!(fs::read_to_string(&output).expect("refusal output"), "");
}

#[test]
fn codex_exec_publishes_a_refusal_bundle_for_unusable_trusted_instructions() {
    let fixture = DraftFixture::new();
    vendor_fixture(&fixture.path, "codex", &codex_writing("done\n"));
    let output = fixture.path.join("codex-exec-output.txt");
    let trusted = fixture.path.join("trusted.txt");
    // A TOML triple-single-quote delimiter cannot be embedded in the config.
    write(&trusted, "instructions with ''' inside\n");

    let mut command = launcher(&fixture.path);
    command
        .args(["agent", "launch-codex-exec", "--output"])
        .arg(&output)
        .args(["--timeout", "60", "--prompt", "do work", "--workdir"])
        .arg(&fixture.repo)
        .arg("--trusted-instructions-file")
        .arg(&trusted);
    command
        .assert()
        .success()
        .stdout(predicates::str::contains("LAUNCHER_EXIT=2"));

    let diag = fs::read_to_string(fixture.path.join("codex-exec-output.txt.diag"))
        .expect("refusal diagnostic");
    assert!(diag.contains("STATUS=FAILED"), "{diag}");
}

#[test]
fn codex_exec_carries_its_prompt_file_sandbox_and_role_into_the_launch_record() {
    let fixture = DraftFixture::new();
    vendor_fixture(&fixture.path, "codex", &codex_writing("done\n"));
    let output = fixture.path.join("codex-exec-output.txt");
    let prompt = fixture.path.join("exec-prompt.md");
    write(&prompt, "prompt from a file\n");

    let mut command = launcher(&fixture.path);
    command
        .args(["agent", "launch-codex-exec", "--output"])
        .arg(&output)
        .args(["--timeout", "60", "--prompt-file"])
        .arg(&prompt)
        .arg("--workdir")
        .arg(&fixture.repo)
        .arg("--add-dir")
        .arg(&fixture.design)
        .args([
            "--sandbox",
            "read-only",
            "--with-effort",
            "--model-role",
            "fix",
            "--usage-label",
            "codex_lint_fix",
            "--timing-task-kind",
            "codex-plan-autofix",
        ]);
    command.assert().success();

    assert_eq!(
        fs::read_to_string(fixture.path.join("codex-exec-output.txt.prompt"))
            .expect("prompt sidecar"),
        "prompt from a file\n"
    );
    let meta = fs::read_to_string(fixture.path.join("codex-exec-output.txt.meta"))
        .expect("launch metadata");
    assert!(meta.contains("OUTER_LAUNCHER_SANDBOX=read-only"), "{meta}");
    assert!(meta.contains("OUTER_LAUNCHER_WITH_EFFORT=true"), "{meta}");
    assert!(meta.contains("OUTER_LAUNCHER_MODEL_ROLE=fix"), "{meta}");
    assert!(
        meta.contains("OUTER_LAUNCHER_USAGE_LABEL=codex_lint_fix"),
        "{meta}"
    );
    assert!(
        meta.contains("OUTER_LAUNCHER_TIMING_KIND=codex-plan-autofix"),
        "{meta}"
    );
    assert!(
        meta.contains(&fixture.design.display().to_string()),
        "add-dir missing from {meta}"
    );
}

// ---------------------------------------------------------------------------
// Drafter details
// ---------------------------------------------------------------------------

#[test]
fn claude_drafter_records_subprocess_usage_from_its_envelope() {
    let fixture = DraftFixture::new();
    let envelope = serde_json::json!({
        "result": PLAN,
        "usage": {
            "input_tokens": 11,
            "output_tokens": 7,
            "cache_read_input_tokens": 3,
            "cache_creation_input_tokens": 2,
        },
    })
    .to_string();
    vendor_fixture(
        &fixture.path,
        "claude",
        &format!("#!/bin/sh\ncat > /dev/null\nprintf '%s' '{envelope}'\nexit 0\n"),
    );

    let mut command = launcher(&fixture.path);
    command
        .env("CLAUDE_PLUGIN_ROOT", repository_root())
        // The `[1m]` alias prices as its base model in the shared ledger.
        .args([
            "agent",
            "launch-claude-drafter",
            "--model",
            "claude-sonnet-4-6[1m]",
        ])
        .arg("--prompt-file")
        .arg(&fixture.prompt)
        .arg("--output-file")
        .arg(&fixture.status)
        .args(["--timeout", "60", "--design-tmpdir"])
        .arg(&fixture.design)
        .arg("--repo-root")
        .arg(&fixture.repo);
    command
        .assert()
        .success()
        .stdout(predicates::str::contains("ELAPSED="));

    let status = fixture.status_text();
    assert!(status.contains("STATUS=OK"), "{status}");
}

#[test]
fn claude_drafter_reports_a_failed_vendor_launch_with_a_stderr_tail() {
    let fixture = DraftFixture::new();
    vendor_fixture(
        &fixture.path,
        "claude",
        "#!/bin/sh\ncat > /dev/null\nprintf 'claude exploded\\n' >&2\nexit 3\n",
    );

    let mut command = launcher(&fixture.path);
    command
        .args(["agent", "launch-claude-drafter", "--model", "claude-test"])
        .arg("--prompt-file")
        .arg(&fixture.prompt)
        .arg("--output-file")
        .arg(&fixture.status)
        .args(["--timeout", "60", "--design-tmpdir"])
        .arg(&fixture.design)
        .arg("--repo-root")
        .arg(&fixture.repo);
    command.assert().code(3);

    let status = fixture.status_text();
    assert!(status.contains("REASON=CLAUDE_EXIT_NONZERO"), "{status}");
    let tail = fs::read_to_string(fixture.design.join("step2b-drafter-status.txt.stderr-tail"))
        .expect("stderr tail");
    assert!(tail.contains("claude exploded"), "{tail}");
}

#[test]
fn claude_drafter_reports_a_deadline_as_a_timeout_status() {
    let fixture = DraftFixture::new();
    vendor_fixture(
        &fixture.path,
        "claude",
        "#!/bin/sh\ncat > /dev/null\nsleep 30\n",
    );

    let mut command = launcher(&fixture.path);
    command
        .args(["agent", "launch-claude-drafter", "--model", "claude-test"])
        .arg("--prompt-file")
        .arg(&fixture.prompt)
        .arg("--output-file")
        .arg(&fixture.status)
        .args(["--timeout", "1", "--design-tmpdir"])
        .arg(&fixture.design)
        .arg("--repo-root")
        .arg(&fixture.repo);
    command.assert().code(124);

    let status = fixture.status_text();
    assert!(status.contains("STATUS=TIMEOUT"), "{status}");
    assert!(status.contains("REASON=TIMEOUT"), "{status}");
}

#[test]
fn codex_drafter_publishes_a_refusal_bundle_when_model_arguments_cannot_resolve() {
    let fixture = DraftFixture::new();
    vendor_fixture(&fixture.path, "codex", &codex_writing(PLAN));

    let mut command = fixture.codex_drafter();
    command.env("LARCH_CODEX_MODEL", "   ");
    command.assert().code(1);

    let status = fixture.status_text();
    assert!(status.contains("REASON=CODEX_EXEC_FAILED"), "{status}");
    assert!(status.contains("DRAFTER_LAUNCHED=true"), "{status}");
}

#[test]
fn drafter_summary_and_dialectic_blocks_reach_the_design_tmpdir() {
    let fixture = DraftFixture::new();
    let response = format!(
        "LARCH_SUMMARY_BEGIN\nplan summary\nLARCH_SUMMARY_END\n{PLAN}\
         LARCH_DIALECTIC_BEGIN\n{{\"decisions\":[]}}\nLARCH_DIALECTIC_END\n"
    );
    vendor_fixture(&fixture.path, "codex", &codex_writing(&response));

    let mut command = fixture.codex_drafter();
    command.env("CLAUDE_PLUGIN_ROOT", repository_root());
    command.assert().success();

    let status = fixture.status_text();
    assert!(status.contains("SUMMARY_WRITTEN=true"), "{status}");
    assert_eq!(
        fs::read_to_string(fixture.design.join("plan-summary.md")).expect("published summary"),
        "plan summary\n"
    );
    // An empty decision list is not a usable candidate set.
    assert!(
        status.contains("DIALECTIC_CANDIDATES_PARSED=false"),
        "{status}"
    );
    assert!(
        status.contains("DIALECTIC_CANDIDATES_FAIL_REASON=invalid_dialectic_json"),
        "{status}"
    );
}

#[test]
fn codex_drafter_compares_its_dirty_tree_against_a_supplied_baseline() {
    let fixture = DraftFixture::new();
    vendor_fixture(&fixture.path, "codex", &codex_writing(PLAN));
    let baseline = fixture.design.join("step2b-drafter-baseline.porcelain");
    write(&baseline, "");

    let mut command = fixture.codex_drafter();
    command.arg("--baseline-porcelain").arg(&baseline);
    command.assert().success();

    let sidecar = fs::read_to_string(fixture.design.join("step2b-drafter-status.txt.dirty-tree"))
        .expect("dirty-tree sidecar");
    assert!(sidecar.contains("MODE=baseline-delta"), "{sidecar}");
}
