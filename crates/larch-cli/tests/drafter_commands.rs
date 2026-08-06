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
