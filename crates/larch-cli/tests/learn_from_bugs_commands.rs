//! Offline CLI coverage for the Rust-owned learn-from-bugs preparation boundary.

use std::{
    fs,
    path::{Path, PathBuf},
    process::Command as ProcessCommand,
};

use assert_cmd::Command as AssertCommand;
use serde_json::Value;
use tempfile::TempDir;

struct Fixture {
    _temporary: TempDir,
    root: PathBuf,
    home: PathBuf,
    state_home: PathBuf,
}

impl Fixture {
    fn create() -> Self {
        let temporary = tempfile::tempdir().expect("fixture temporary directory");
        let root = temporary.path().join("repository");
        let home = temporary.path().join("home");
        let state_home = temporary.path().join("state");
        fs::create_dir_all(&root).expect("fixture repository");
        fs::create_dir_all(&home).expect("fixture home");
        fs::create_dir_all(&state_home).expect("fixture state home");
        git(&root, ["init", "-b", "main"]);
        git(&root, ["config", "user.email", "test@example.com"]);
        git(&root, ["config", "user.name", "Larch Test"]);
        fs::write(root.join("README.md"), "fixture\n").expect("fixture readme");
        git(&root, ["add", "README.md"]);
        git(&root, ["commit", "-m", "fixture"]);
        git(
            &root,
            [
                "remote",
                "add",
                "origin",
                "https://github.com/acme/widget.git",
            ],
        );
        fs::write(
            root.join("tools-config.toml"),
            "[larch]\nstorage_base_uri = \"s3://fixture-bucket/larch-tests\"\n",
        )
        .expect("fixture storage configuration");
        Self {
            _temporary: temporary,
            root,
            home,
            state_home,
        }
    }

    fn path(&self, relative: &str) -> PathBuf {
        self.root.join(relative)
    }

    fn write(&self, relative: &str, contents: &str) {
        let path = self.path(relative);
        fs::create_dir_all(path.parent().expect("fixture parent")).expect("fixture parent");
        fs::write(path, contents).expect("fixture file");
    }

    fn command(&self) -> AssertCommand {
        let mut command = AssertCommand::cargo_bin("larch").expect("larch binary should build");
        command
            .current_dir(&self.root)
            .env("HOME", &self.home)
            .env("XDG_STATE_HOME", &self.state_home)
            .env_remove("LARCH_LOGS_URI")
            .env_remove("LARCH_STORAGE_BASE_URI");
        command
    }
}

fn git<const N: usize>(root: &Path, arguments: [&str; N]) {
    let output = ProcessCommand::new("git")
        .args(arguments)
        .current_dir(root)
        .output()
        .expect("run fixture git command");
    assert!(
        output.status.success(),
        "fixture git failed: {}",
        String::from_utf8_lossy(&output.stderr)
    );
}

fn stdout(assertion: &assert_cmd::assert::Assert) -> String {
    String::from_utf8_lossy(&assertion.get_output().stdout).into_owned()
}

fn stderr(assertion: &assert_cmd::assert::Assert) -> String {
    String::from_utf8_lossy(&assertion.get_output().stderr).into_owned()
}

fn output_path(output: &str, key: &str) -> PathBuf {
    output
        .lines()
        .find_map(|line| line.strip_prefix(&format!("{key}=")))
        .map(PathBuf::from)
        .expect("command output path")
}

fn write_state(
    fixture: &Fixture,
    proposals_file: Option<&Path>,
    base_proposals_file: Option<&Path>,
) -> assert_cmd::assert::Assert {
    let root = fixture.root.to_str().expect("UTF-8 fixture root");
    let mut command = fixture.command();
    command.args([
        "learn-from-bugs",
        "write-state",
        "--root",
        root,
        "--repo",
        "acme/widget",
        "--search",
        "[BUG] in:title",
        "--state",
        "closed",
        "--selected-count",
        "4",
        "--highest-closed-issue-number-scanned",
        "91",
        "--run-date",
        "2026-08-09",
        "--scan-started-at",
        "2026-08-09T12:00:00Z",
    ]);
    if let Some(path) = proposals_file {
        command.args([
            "--proposals-file",
            path.to_str().expect("UTF-8 proposals path"),
        ]);
    }
    if let Some(path) = base_proposals_file {
        command.args([
            "--base-proposals-file",
            path.to_str().expect("UTF-8 base proposals path"),
        ]);
    }
    command.assert()
}

#[test]
fn preparation_and_coverage_index_run_without_github_when_limit_is_zero() {
    let fixture = Fixture::create();
    fixture.write(
        "ARCHITECTURAL_GUIDELINES.md",
        "### G-Example-1: First guideline\n\n```markdown\n### G-Fake-1: fenced\n```\n",
    );
    fixture.write(
        "ARCHITECTURAL_INVARIANTS.md",
        "### I-Example-1: First invariant\n\n```markdown\n### I-Fake-1: fenced\n```\n",
    );
    fixture.write("python/larch/lint/lint_alpha.py", "# fixture\n");
    fixture.write("python/larch/lint/lint_zeta.py", "# fixture\n");
    fixture.write("scripts/lint-zeta", "# fixture\n");
    fixture.write("scripts/lint-alpha", "# fixture\n");
    fs::create_dir_all(fixture.path("out")).expect("coverage output directory");
    let index_out = fixture.path("out/coverage.json");
    let root = fixture.root.to_str().expect("UTF-8 fixture root");

    let mut coverage = fixture.command();
    coverage.args([
        "learn-from-bugs",
        "coverage-index",
        "--root",
        root,
        "--out",
        index_out.to_str().expect("UTF-8 index path"),
    ]);
    let coverage = coverage.assert().success();
    let payload: Value = serde_json::from_str(&stdout(&coverage)).expect("coverage JSON");
    assert_eq!(
        payload["guidelines"],
        serde_json::json!([["G-Example-1", "First guideline"]])
    );
    assert_eq!(
        payload["invariants"],
        serde_json::json!([["I-Example-1", "First invariant"]])
    );
    assert_eq!(
        payload["python_lints"],
        serde_json::json!(["lint_alpha", "lint_zeta"])
    );
    assert_eq!(
        payload["script_lints"],
        serde_json::json!(["lint-alpha", "lint-zeta"])
    );
    assert_eq!(
        fs::read_to_string(&index_out).expect("written coverage index"),
        stdout(&coverage)
    );

    let out = fixture.path("out/prepared");
    let mut prepare = fixture.command();
    prepare.args([
        "learn-from-bugs",
        "prepare",
        "--root",
        root,
        "--repo",
        "acme/widget",
        "--out",
        out.to_str().expect("UTF-8 prepared path"),
        "--limit",
        "0",
    ]);
    let prepare = prepare.assert().success();
    let prepared = stdout(&prepare);
    assert!(prepared.contains("REPO=acme/widget\n"));
    assert!(prepared.contains("ISSUES_SELECTED=0\n"));
    assert!(prepared.contains("INCREMENTAL=false\n"));
    assert!(prepared.contains("GUIDELINES_INDEXED=1\n"));
    let digest_path = output_path(&prepared, "DIGEST_PATH");
    assert_eq!(fs::read_to_string(digest_path).expect("empty digest"), "");
    assert_eq!(
        fs::read_to_string(out.join("origin-headline.md")).expect("origin headline"),
        "#### Origin distribution (selected=0)\n- regression: 0 (0.0%)\n- new-code: 0 (0.0%)\n- spec-gap: 0 (0.0%)\n- unknown: 0 (0.0%)\n#### Referenced regression chains\n(none)\n#### Regression ratio\nn/a (0/0)\n"
    );
}

#[test]
fn state_round_trip_preserves_history_and_applies_residual_status() {
    let fixture = Fixture::create();
    fixture.write("python/larch/lint/lint_delta.py", "# fixture\n");
    let initial = fixture.path("initial.jsonl");
    fixture.write(
        "initial.jsonl",
        "{\"id\":\"lint-delta\",\"type\":\"lint\",\"target\":\"module:python/larch/lint/lint_delta.py\",\"run_date\":\"2026-08-09\",\"status\":\"proposed\",\"filed_issue\":null}\n",
    );
    let written = write_state(&fixture, Some(&initial), None).success();
    let written_stdout = stdout(&written);
    let state_path = output_path(&written_stdout, "STATE_PATH");
    assert!(state_path.starts_with(fs::canonicalize(&fixture.state_home).expect("state home")));
    assert!(
        fs::read_to_string(&state_path)
            .expect("state file")
            .contains("\"schema_version\": 2")
    );

    let root = fixture.root.to_str().expect("UTF-8 fixture root");
    let mut read = fixture.command();
    read.args(["learn-from-bugs", "read-state", "--root", root]);
    let read = read.assert().success();
    let read_stdout = stdout(&read);
    assert!(read_stdout.contains("LEARN_FROM_BUGS_STATE_FOUND=true\n"));
    assert!(read_stdout.contains("PROPOSAL_COUNT=1\n"));
    assert!(read_stdout.contains("HIGHEST_CLOSED_ISSUE_NUMBER_SCANNED=91\n"));

    let without_proposals = write_state(&fixture, None, None).code(1);
    assert!(
        stderr(&without_proposals)
            .contains("--proposals-file is required to preserve proposal history")
    );

    let residual = fixture.path("residual.jsonl");
    let base = fixture.path("base.jsonl");
    fixture.write(
        "residual.jsonl",
        "{\"id\":\"lint-delta\",\"type\":\"lint\",\"target\":\"module:python/larch/lint/lint_delta.py\",\"run_date\":\"2026-08-09\",\"status\":\"pending\",\"filed_issue\":42}\n",
    );
    fixture.write(
        "base.jsonl",
        "{\"id\":\"lint-delta\",\"type\":\"lint\",\"target\":\"module:python/larch/lint/lint_delta.py\",\"run_date\":\"2026-08-09\",\"status\":\"proposed\",\"filed_issue\":null}\n",
    );
    let updated = write_state(&fixture, Some(&residual), Some(&base)).success();
    assert!(stdout(&updated).contains("PROPOSAL_COUNT=1\n"));
    let state: Value = serde_json::from_str(&fs::read_to_string(&state_path).expect("state file"))
        .expect("state JSON");
    assert_eq!(state["proposals"][0]["status"], "pending");
    assert_eq!(state["proposals"][0]["filed_issue"], 42);
}

#[test]
fn command_contracts_reject_ambiguous_or_invalid_arguments() {
    let fixture = Fixture::create();
    let root = fixture.root.to_str().expect("UTF-8 fixture root");

    let mut coverage_help = fixture.command();
    coverage_help.args(["learn-from-bugs", "coverage-index", "--hel"]);
    assert!(
        stdout(&coverage_help.assert().success())
            .starts_with("usage: learn-from-bugs coverage-index")
    );

    let mut coverage_help_value = fixture.command();
    coverage_help_value.args(["learn-from-bugs", "coverage-index", "--help=unexpected"]);
    let coverage_help_value = coverage_help_value.assert().code(2);
    assert!(stderr(&coverage_help_value).contains("argument -h/--help: ignored explicit argument"));

    let mut zones = fixture.command();
    zones.args([
        "learn-from-bugs",
        "resolve-zones",
        "--zones",
        "design,implement",
    ]);
    assert_eq!(
        stdout(&zones.assert().success()),
        "RESOLVED_SEARCH=[BUG] (design OR implement) in:title,body\n"
    );

    let mut zones_conflict = fixture.command();
    zones_conflict.args([
        "learn-from-bugs",
        "resolve-zones",
        "--zones",
        "design",
        "--has-explicit-search",
    ]);
    assert_eq!(
        stderr(&zones_conflict.assert().code(2)),
        "--zones cannot be combined with --search\n"
    );

    let mut zones_unknown = fixture.command();
    zones_unknown.args([
        "learn-from-bugs",
        "resolve-zones",
        "--zones",
        "design",
        "extra",
    ]);
    let zones_unknown = zones_unknown.assert().code(2);
    assert!(stderr(&zones_unknown).contains("unrecognized arguments: extra"));

    let mut prepare_limit = fixture.command();
    prepare_limit.args([
        "learn-from-bugs",
        "prepare",
        "--out",
        "out",
        "--limit",
        "not-an-int",
    ]);
    let prepare_limit = prepare_limit.assert().code(2);
    assert!(stderr(&prepare_limit).contains("argument --limit: invalid int value: 'not-an-int'"));

    let mut prepare_repo = fixture.command();
    prepare_repo.args([
        "learn-from-bugs",
        "prepare",
        "--root",
        root,
        "--out",
        "out",
        "--repo",
        "not a repository",
    ]);
    let prepare_repo = prepare_repo.assert().code(1);
    assert!(stderr(&prepare_repo).contains("invalid repository: not a repository"));

    let mut read_missing = fixture.command();
    read_missing.args(["learn-from-bugs", "read-state"]);
    let read_missing = read_missing.assert().code(2);
    assert!(stderr(&read_missing).contains("the following arguments are required: --root"));

    let mut write_integer = fixture.command();
    write_integer.args(["learn-from-bugs", "write-state", "--selected-count", "nan"]);
    let write_integer = write_integer.assert().code(2);
    assert!(stderr(&write_integer).contains("argument --selected-count: invalid int value: 'nan'"));
}

#[test]
fn prepare_errors_reject_bad_roots_and_artifact_destinations() {
    let fixture = Fixture::create();
    let root = fixture.root.to_str().expect("UTF-8 fixture root");

    let mut prepare_help_value = fixture.command();
    prepare_help_value.args(["learn-from-bugs", "prepare", "--help=unexpected"]);
    assert!(stderr(&prepare_help_value.assert().code(2)).contains("ignored explicit argument"));

    let mut prepare_missing_out = fixture.command();
    prepare_missing_out.args(["learn-from-bugs", "prepare", "--limit", "0"]);
    assert!(stderr(&prepare_missing_out.assert().code(2)).contains("required: --out"));

    let mut prepare_unknown = fixture.command();
    prepare_unknown.args([
        "learn-from-bugs",
        "prepare",
        "--out",
        "out",
        "--limit",
        "0",
        "extra",
    ]);
    assert!(stderr(&prepare_unknown.assert().code(2)).contains("unrecognized arguments: extra"));

    let mut prepare_missing_root = fixture.command();
    prepare_missing_root.args([
        "learn-from-bugs",
        "prepare",
        "--root",
        "missing-root",
        "--out",
        "out",
        "--limit",
        "0",
    ]);
    assert!(
        stderr(&prepare_missing_root.assert().code(1)).contains("cannot resolve analysis root")
    );

    let mut prepare_fetch = fixture.command();
    prepare_fetch.args([
        "learn-from-bugs",
        "prepare",
        "--root",
        root,
        "--repo",
        "acme/widget",
        "--out",
        "out",
        "--limit",
        "-1",
    ]);
    assert!(
        stderr(&prepare_fetch.assert().code(1))
            .contains("gh issue list failed: invalid issue limit")
    );

    let existing_file = fixture.path("not-a-directory");
    fs::write(&existing_file, "fixture\n").expect("output fixture file");
    let mut prepare_file = fixture.command();
    prepare_file.args([
        "learn-from-bugs",
        "prepare",
        "--root",
        root,
        "--repo",
        "acme/widget",
        "--out",
        existing_file.to_str().expect("UTF-8 output fixture"),
        "--limit",
        "0",
    ]);
    assert_eq!(prepare_file.assert().code(1).get_output().stdout, b"");
}

#[test]
fn prepare_rejects_mismatched_and_corrupt_state() {
    let fixture = Fixture::create();
    let root = fixture.root.to_str().expect("UTF-8 fixture root");
    let written = write_state(&fixture, None, None).success();
    let state_path = output_path(&stdout(&written), "STATE_PATH");
    let mut mismatch = fixture.command();
    mismatch.args([
        "learn-from-bugs",
        "prepare",
        "--root",
        root,
        "--repo",
        "other/widget",
        "--out",
        "out/mismatch",
        "--limit",
        "0",
    ]);
    assert!(stderr(&mismatch.assert().code(1)).contains("does not match the durable"));
    fs::write(&state_path, "invalid JSON\n").expect("corrupt durable state");
    let mut corrupt = fixture.command();
    corrupt.args([
        "learn-from-bugs",
        "prepare",
        "--root",
        root,
        "--repo",
        "acme/widget",
        "--out",
        "out/corrupt",
        "--limit",
        "0",
    ]);
    assert!(
        stderr(&corrupt.assert().code(1))
            .contains("existing state marker is invalid or unsupported")
    );
}

#[test]
fn state_and_coverage_errors_report_contracts() {
    let fresh = Fixture::create();
    let fresh_root = fresh.root.to_str().expect("UTF-8 fixture root");
    let mut read_missing = fresh.command();
    read_missing.args(["learn-from-bugs", "read-state", "--root", fresh_root]);
    assert!(stdout(&read_missing.assert().success()).contains("LEARN_FROM_BUGS_STATE_FOUND=false"));
    let mut read_bad_root = fresh.command();
    read_bad_root.args(["learn-from-bugs", "read-state", "--root", "missing-root"]);
    assert!(stderr(&read_bad_root.assert().code(1)).contains("cannot resolve analysis root"));

    let mut coverage_default = fresh.command();
    coverage_default.args(["learn-from-bugs", "coverage-index"]);
    assert!(stdout(&coverage_default.assert().success()).contains("\"guidelines\""));
    let mut coverage_bad_out = fresh.command();
    coverage_bad_out.args([
        "learn-from-bugs",
        "coverage-index",
        "--out",
        "missing/coverage.json",
    ]);
    assert_eq!(coverage_bad_out.assert().code(1).get_output().stdout, b"");

    let mut zones_help_value = fresh.command();
    zones_help_value.args(["learn-from-bugs", "resolve-zones", "--help=unexpected"]);
    assert!(stderr(&zones_help_value.assert().code(2)).contains("ignored explicit argument"));
    let mut zones_missing = fresh.command();
    zones_missing.args(["learn-from-bugs", "resolve-zones"]);
    assert!(stderr(&zones_missing.assert().code(2)).contains("required: --zones"));
}
