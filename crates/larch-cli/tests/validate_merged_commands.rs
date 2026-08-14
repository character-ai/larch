//! Offline CLI coverage for the Rust-owned validate-merged commands.

use std::{
    fs,
    path::{Path, PathBuf},
    process::Command as ProcessCommand,
};

use assert_cmd::Command as AssertCommand;
use predicates::prelude::*;
use serde_json::{Value, json};
use tempfile::TempDir;

const SHA_A: &str = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
const SHA_B: &str = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb";
const TIP: &str = "cccccccccccccccccccccccccccccccccccccccc";

const PREPARE_USAGE: &str = "usage: python/cli.py validate-merged prepare [-h] [--root ROOT] --run-dir\n                                             RUN_DIR [--repo REPO]\n                                             [--max-merges MAX_MERGES]\n";
const FINDER_USAGE: &str =
    "usage: python/cli.py validate-merged ingest-finder [-h] --run-dir RUN_DIR\n";
const REPORT_USAGE: &str = "usage: python/cli.py validate-merged report [-h] [--root ROOT] --run-dir\n                                            RUN_DIR [--repo REPO]\n                                            --state-output STATE_OUTPUT\n";
const WRITE_USAGE: &str = "usage: python/cli.py validate-merged write-state [-h] [--root ROOT] --repo\n                                                 REPO --state-input\n                                                 STATE_INPUT\n                                                 [--expected-digest EXPECTED_DIGEST]\n";

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
        git(&root, ["update-ref", "refs/remotes/origin/main", "HEAD"]);
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
        .current_dir(root)
        .args(arguments)
        .output()
        .expect("git command");
    assert!(
        output.status.success(),
        "git {:?} failed: {}",
        arguments,
        String::from_utf8_lossy(&output.stderr)
    );
}

fn finding() -> Value {
    json!({
        "confidence": "medium",
        "description": "wrong dict key",
        "file": "python/larch/issue/mod.py",
        "severity": "high",
        "symbol": "helper",
    })
}

fn write_selected(run_dir: &Path, shas: &[&str]) {
    fs::create_dir_all(run_dir).expect("run dir");
    let selected = shas
        .iter()
        .map(|sha| json!({"merge_sha": sha}))
        .collect::<Vec<_>>();
    fs::write(
        run_dir.join("sweep-selected-merges.json"),
        serde_json::to_string_pretty(&json!({
            "coverage_incomplete": false,
            "pending_shas": [],
            "pinned_tip": TIP,
            "selected": selected,
            "selected_count": shas.len(),
            "skipped_count": 0,
        }))
        .expect("manifest"),
    )
    .expect("write manifest");
}

fn sample_state() -> Value {
    json!({
        "completed_at": "2026-07-16T12:00:00Z",
        "last_successful_tip": SHA_A,
        "merge_watermark": SHA_A,
        "pending_merge_shas": [SHA_B],
        "repo": "o/r",
        "schema_version": 1,
        "unresolved_candidates": [{
            "confidence": "high",
            "description": "bad default",
            "file": "python/larch/example.py",
            "merge_sha": SHA_A,
            "severity": "medium",
            "symbol": "example",
        }],
    })
}

#[test]
fn prepare_help_and_argument_failures_match_argparse() {
    let fixture = Fixture::create();
    fixture
        .command()
        .args(["validate-merged", "prepare", "--help"])
        .assert()
        .success()
        .stdout(predicate::str::starts_with(
            "usage: python/cli.py validate-merged prepare",
        ));
    fixture
        .command()
        .args(["validate-merged", "prepare"])
        .assert()
        .failure()
        .code(2)
        .stderr(format!(
            "{PREPARE_USAGE}python/cli.py validate-merged prepare: error: the following arguments are required: --run-dir\n"
        ));
    fixture
        .command()
        .args([
            "validate-merged",
            "prepare",
            "--run-dir",
            "/tmp",
            "--max-merges",
            "abc",
        ])
        .assert()
        .failure()
        .code(2)
        .stderr(format!(
            "{PREPARE_USAGE}python/cli.py validate-merged prepare: error: argument --max-merges: invalid int value: 'abc'\n"
        ));
    fixture
        .command()
        .args([
            "validate-merged",
            "prepare",
            "--run-dir",
            "/tmp",
            "--max-merges",
            "0",
            "--repo",
            "o/r",
        ])
        .assert()
        .failure()
        .code(2)
        .stderr("validate-merged: --max-merges must be a positive integer\n");
    fixture
        .command()
        .args(["validate-merged", "prepare", "--help=x"])
        .assert()
        .failure()
        .code(2)
        .stderr(format!(
            "{PREPARE_USAGE}python/cli.py validate-merged prepare: error: argument -h/--help: ignored explicit argument 'x'\n"
        ));
}

#[test]
fn ingest_and_report_help_match_argparse() {
    let fixture = Fixture::create();
    fixture
        .command()
        .args(["validate-merged", "ingest-finder"])
        .assert()
        .failure()
        .code(2)
        .stderr(format!(
            "{FINDER_USAGE}python/cli.py validate-merged ingest-finder: error: the following arguments are required: --run-dir\n"
        ));
    fixture
        .command()
        .args(["validate-merged", "report"])
        .assert()
        .failure()
        .code(2)
        .stderr(format!(
            "{REPORT_USAGE}python/cli.py validate-merged report: error: the following arguments are required: --run-dir, --state-output\n"
        ));
    fixture
        .command()
        .args(["validate-merged", "write-state"])
        .assert()
        .failure()
        .code(2)
        .stderr(format!(
            "{WRITE_USAGE}python/cli.py validate-merged write-state: error: the following arguments are required: --repo, --state-input\n"
        ));
}

#[test]
fn ingest_finder_and_refuter_keep_survivors() {
    let fixture = Fixture::create();
    let run_dir = fixture.root.join("run");
    write_selected(&run_dir, &[SHA_A]);
    fs::write(
        run_dir.join("sweep-finder.jsonl"),
        format!(
            "{}\n",
            json!({"findings":[finding(), {
                "confidence": "medium",
                "description": "d2",
                "file": "python/larch/issue/mod.py",
                "severity": "high",
                "symbol": "second",
            }], "merge_sha": SHA_A})
        ),
    )
    .expect("finder raw");
    let finder = fixture
        .command()
        .args([
            "validate-merged",
            "ingest-finder",
            "--run-dir",
            run_dir.to_str().expect("utf8"),
        ])
        .assert()
        .success()
        .get_output()
        .stdout
        .clone();
    let finder_text = String::from_utf8_lossy(&finder);
    assert!(finder_text.contains("INGEST_ACCEPTED=1"));
    assert!(finder_text.contains("REFUTER_QUEUE_COUNT=2"));
    fs::write(
        run_dir.join("sweep-refuter.jsonl"),
        format!(
            "{}\n{}\n",
            json!({"finding_index": 0, "merge_sha": SHA_A, "verdict": "survives"}),
            json!({"finding_index": 1, "merge_sha": SHA_A, "verdict": "refuted"})
        ),
    )
    .expect("refuter raw");
    let refuter = fixture
        .command()
        .args([
            "validate-merged",
            "ingest-refuter",
            "--run-dir",
            run_dir.to_str().expect("utf8"),
        ])
        .assert()
        .success()
        .get_output()
        .stdout
        .clone();
    let refuter_text = String::from_utf8_lossy(&refuter);
    assert!(refuter_text.contains("CANDIDATE_COUNT=1"));
    assert!(refuter_text.contains("REFUTED_COUNT=1"));
    let validated: Value = serde_json::from_str(
        &fs::read_to_string(run_dir.join("sweep-validated.json")).expect("validated"),
    )
    .expect("json");
    assert_eq!(validated["candidates"][0]["symbol"], "helper");
}

#[test]
fn write_state_round_trip_and_rejects_foreign_repo() {
    let fixture = Fixture::create();
    let input = fixture.root.join("state-input.json");
    let payload = sample_state();
    fs::write(
        &input,
        serde_json::to_string_pretty(&payload).expect("state") + "\n",
    )
    .expect("write input");
    let output = fixture
        .command()
        .args([
            "validate-merged",
            "write-state",
            "--root",
            fixture.root.to_str().expect("utf8"),
            "--repo",
            "o/r",
            "--state-input",
            input.to_str().expect("utf8"),
        ])
        .assert()
        .success()
        .get_output()
        .stdout
        .clone();
    let text = String::from_utf8_lossy(&output);
    assert!(text.contains("STATE_RELPATH=validate-merged/state.json"));
    assert!(text.contains("STATE_DIGEST="));
    let path_line = text
        .lines()
        .find(|line| line.starts_with("STATE_PATH="))
        .expect("state path");
    let published = PathBuf::from(path_line.trim_start_matches("STATE_PATH="));
    let stored: Value =
        serde_json::from_str(&fs::read_to_string(&published).expect("published")).expect("json");
    assert_eq!(stored["repo"], "o/r");
    assert_eq!(stored["pending_merge_shas"][0], SHA_B);

    fixture
        .command()
        .args([
            "validate-merged",
            "write-state",
            "--root",
            fixture.root.to_str().expect("utf8"),
            "--repo",
            "other/repo",
            "--state-input",
            input.to_str().expect("utf8"),
        ])
        .assert()
        .failure()
        .code(2)
        .stderr("validate-merged: committed state marker has an unsupported schema or foreign repository\n");
}

#[test]
fn prepare_selects_first_parent_merges_and_excludes_flush_release_and_logs() {
    let fixture = Fixture::create();
    let root = &fixture.root;
    git(root, ["checkout", "-q", "-b", "real-one"]);
    fs::create_dir_all(root.join("python/larch/issue")).expect("dir");
    fs::write(root.join("python/larch/issue/a.py"), "A = 3\n").expect("write");
    git(root, ["add", "--", "python/larch/issue/a.py"]);
    git(root, ["commit", "-q", "-m", "fix: real one"]);
    git(root, ["checkout", "-q", "main"]);
    git(
        root,
        ["merge", "--no-ff", "-q", "-m", "Merge real one", "real-one"],
    );
    let real_one = git_stdout(root, ["rev-parse", "HEAD"]);

    git(root, ["checkout", "-q", "-b", "real-two"]);
    fs::create_dir_all(root.join("python/larch/core")).expect("dir");
    fs::write(root.join("python/larch/core/b.py"), "B = 1\n").expect("write");
    git(root, ["add", "--", "python/larch/core/b.py"]);
    git(root, ["commit", "-q", "-m", "fix: real two"]);
    git(root, ["checkout", "-q", "main"]);
    git(
        root,
        ["merge", "--no-ff", "-q", "-m", "Merge real two", "real-two"],
    );
    let real_two = git_stdout(root, ["rev-parse", "HEAD"]);

    fs::create_dir_all(root.join("larch-logs/run")).expect("logs");
    fs::write(root.join("larch-logs/run/x.md"), "log\n").expect("flush");
    git(root, ["add", "--", "larch-logs/run/x.md"]);
    git(root, ["commit", "-q", "-m", "chore(larch-logs): flush"]);
    fs::write(root.join("VERSION"), "1.0.0\n").expect("version");
    git(root, ["add", "--", "VERSION"]);
    git(root, ["commit", "-q", "-m", "Release v1.0.0"]);
    git(root, ["update-ref", "refs/remotes/origin/main", "HEAD"]);

    let run_dir = root.join("run");
    let output = fixture
        .command()
        .args([
            "validate-merged",
            "prepare",
            "--root",
            root.to_str().expect("utf8"),
            "--run-dir",
            run_dir.to_str().expect("utf8"),
            "--repo",
            "o/r",
            "--max-merges",
            "20",
        ])
        .assert()
        .success()
        .get_output()
        .stdout
        .clone();
    let text = String::from_utf8_lossy(&output);
    assert!(text.contains("SELECTED_COUNT=2"), "{text}");
    let selected: Value = serde_json::from_str(
        &fs::read_to_string(run_dir.join("sweep-selected-merges.json")).expect("selected"),
    )
    .expect("json");
    let shas = selected["selected"]
        .as_array()
        .expect("selected")
        .iter()
        .map(|row| row["merge_sha"].as_str().expect("sha").to_owned())
        .collect::<std::collections::BTreeSet<_>>();
    assert_eq!(
        shas,
        [real_one, real_two]
            .into_iter()
            .collect::<std::collections::BTreeSet<_>>()
    );
}

fn git_stdout<const N: usize>(root: &Path, arguments: [&str; N]) -> String {
    let output = ProcessCommand::new("git")
        .current_dir(root)
        .args(arguments)
        .output()
        .expect("git");
    assert!(output.status.success(), "git {arguments:?} failed");
    String::from_utf8(output.stdout)
        .expect("utf8")
        .trim()
        .to_owned()
}
