//! Black-box lifecycle tests for admission state that must survive later configuration drift.

use std::{
    fs,
    path::{Path, PathBuf},
    process::{Command, Output, Stdio},
};

use tempfile::TempDir;

fn git(repo: &Path, arguments: &[&str]) {
    let status = Command::new("git")
        .args(arguments)
        .current_dir(repo)
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .status()
        .expect("git should run");
    assert!(status.success(), "git {arguments:?} failed");
}

struct Harness {
    _temp: TempDir,
    root: PathBuf,
    repo: PathBuf,
}

impl Harness {
    fn new() -> Self {
        let temp = TempDir::new().expect("tempdir");
        let root = temp.path().canonicalize().expect("canonical tempdir");
        let repo = root.join("repo");
        fs::create_dir(&repo).expect("repo directory");
        git(&repo, &["init", "-b", "main"]);
        git(
            &repo,
            &[
                "remote",
                "add",
                "origin",
                "https://github.com/acme/client.git",
            ],
        );
        Self {
            _temp: temp,
            root,
            repo,
        }
    }

    fn command(&self, arguments: &[&str]) -> Command {
        let mut command = Command::new(env!("CARGO_BIN_EXE_larch"));
        command
            .args(arguments)
            .env("HOME", self.root.join("home"))
            .env("XDG_STATE_HOME", self.root.join("state"))
            .env("XDG_CACHE_HOME", self.root.join("cache"))
            .env_remove("LARCH_LOGS_URI")
            .env_remove("LARCH_STORAGE_BASE_URI")
            .current_dir(&self.repo);
        command
    }

    fn run(&self, arguments: &[&str]) -> Output {
        self.command(arguments).output().expect("larch should run")
    }
}

fn output_value(output: &Output, key: &str) -> String {
    String::from_utf8_lossy(&output.stdout)
        .lines()
        .find_map(|line| line.strip_prefix(&format!("{key}=")))
        .unwrap_or_else(|| panic!("missing {key} in stdout"))
        .to_owned()
}

#[test]
fn disabled_run_terminalizes_after_configuration_becomes_malformed() {
    let harness = Harness::new();
    let repo = harness.repo.to_str().expect("UTF-8 repo path");
    let started = harness.run(&[
        "run-log",
        "lifecycle-start",
        "--repo-root",
        repo,
        "--skill",
        "review",
        "--run-id",
        "disabled-before-malformed",
    ]);
    assert!(
        started.status.success(),
        "start failed: {}",
        String::from_utf8_lossy(&started.stderr)
    );
    let context_file = PathBuf::from(output_value(&started, "CONTEXT_FILE"));
    let run_dir = PathBuf::from(output_value(&started, "RUN_DIR"));
    assert!(context_file.is_file());
    assert!(run_dir.is_dir());
    let stdout = String::from_utf8_lossy(&started.stdout);
    assert!(stdout.contains("RUN_LOG_STORAGE=disabled\n"));
    assert!(stdout.contains("LIFECYCLE_STARTED=true\n"));

    fs::write(harness.repo.join("tools-config.toml"), "[larch\n").expect("malformed configuration");
    let finished = harness.run(&[
        "run-log",
        "lifecycle-finalize",
        "--repo-root",
        repo,
        "--skill",
        "review",
        "--run-id",
        "disabled-before-malformed",
    ]);
    assert!(
        finished.status.success(),
        "finalize failed: {}",
        String::from_utf8_lossy(&finished.stderr)
    );
    let stdout = String::from_utf8_lossy(&finished.stdout);
    assert!(stdout.contains("RUN_LOG_PUBLICATION=skipped-disabled\n"));
    assert!(stdout.contains("LIFECYCLE_FLUSHED=false\n"));
    assert!(stdout.contains("LIFECYCLE_TERMINALIZED=true\n"));
    assert!(!context_file.exists());
    assert!(!run_dir.exists());
}

#[test]
fn standalone_publication_and_sync_preserve_disabled_and_parser_contracts() {
    let harness = Harness::new();
    let repo = harness.repo.to_str().expect("UTF-8 repo path");
    let staging = harness.root.join("staging");
    fs::create_dir_all(&staging).expect("staging should create");
    fs::write(staging.join("private.txt"), "unchanged\n").expect("staging should write");
    let publish = harness.run(&[
        "run-log",
        "publish",
        "--repo-root",
        repo,
        "--skill",
        "review",
        "--run-id",
        "disabled-standalone",
        "--staging-root",
        staging.to_str().expect("UTF-8 staging path"),
    ]);
    assert!(publish.status.success());
    for (key, expected) in [
        ("RUN_LOG_STORAGE", "disabled"),
        ("STORAGE_PREFLIGHT", "skipped-disabled"),
        ("RUN_LOG_PUBLICATION", "skipped-disabled"),
        ("SECRET_SCRUB_VIOLATIONS", "0"),
        ("PUBLISH_OK", "true"),
    ] {
        assert_eq!(output_value(&publish, key), expected);
    }
    assert_eq!(
        fs::read_to_string(staging.join("private.txt")).unwrap(),
        "unchanged\n"
    );
    assert!(!harness.root.join("state/larch/run-log-pending").exists());
    assert!(!harness.root.join("cache/larch/run-logs").exists());
    let sync = harness.run(&["run-log", "sync", "--repo-root", repo]);
    assert!(sync.status.success());
    for (key, expected) in [
        ("RUN_LOG_STORAGE", "disabled"),
        ("CORPUS_ROOT", ""),
        ("LISTED_ARCHIVES", "0"),
        ("PRESENT_RUNS", "0"),
        ("DOWNLOADED_RUNS", "0"),
        ("REPAIRED_RUNS", "0"),
        ("SYNC_OK", "true"),
    ] {
        assert_eq!(output_value(&sync, key), expected);
    }
    assert!(!harness.root.join("cache/larch/run-logs").exists());
    for count in ["-1", "+1"] {
        let invalid = harness.run(&[
            "run-log",
            "publish",
            "--repo-root",
            repo,
            "--skill",
            "review",
            "--run-id",
            "invalid-count",
            "--pre-scrub-violations",
            count,
        ]);
        assert_eq!(invalid.status.code(), Some(2));
        assert!(
            String::from_utf8_lossy(&invalid.stderr)
                .contains("--pre-scrub-violations must be a non-negative integer")
        );
        assert!(invalid.stdout.is_empty());
    }
    let help = harness.run(&["run-log", "publish", "--help"]);
    assert!(help.status.success());
    let help = String::from_utf8_lossy(&help.stdout);
    assert!(help.contains("[--pre-scrub-violations PRE_SCRUB_VIOLATIONS]"));
    assert!(help.contains("options:\n  -h, --help            show this help message and exit"));
    let missing = harness.run(&["run-log", "publish", "--repo-root", repo]);
    assert_eq!(missing.status.code(), Some(2));
    assert!(
        String::from_utf8_lossy(&missing.stderr)
            .contains("the following arguments are required: --skill, --run-id")
    );
}
#[test]
fn disabled_standalone_commands_skip_relative_xdg_homes() {
    let harness = Harness::new();
    let repo = harness.repo.to_str().expect("UTF-8 repo path");
    for arguments in [
        vec![
            "run-log",
            "publish",
            "--repo-root",
            repo,
            "--skill",
            "review",
            "--run-id",
            "disabled-relative-home",
        ],
        vec!["run-log", "sync", "--repo-root", repo],
    ] {
        let output = harness
            .command(&arguments)
            .env("XDG_STATE_HOME", "relative-state")
            .env("XDG_CACHE_HOME", "relative-cache")
            .output()
            .expect("disabled command should run");
        assert!(output.status.success());
        assert_eq!(output_value(&output, "RUN_LOG_STORAGE"), "disabled");
    }
}
#[test]
fn standalone_commands_fail_closed_before_provider_or_repository_mutation() {
    let harness = Harness::new();
    let repo = harness.repo.to_str().expect("UTF-8 repo path");
    for arguments in [
        vec![
            "run-log",
            "publish",
            "--repo-root",
            repo,
            "--skill",
            "review",
            "--run-id",
            "configured-provider",
        ],
        vec!["run-log", "sync", "--repo-root", repo],
    ] {
        let output = harness
            .command(&arguments)
            .env("LARCH_STORAGE_BASE_URI", "r2://bucket/testing")
            .env("LARCH_R2_ACCOUNT_ID", "")
            .env("LARCH_R2_ENDPOINT", "")
            .output()
            .expect("configured command should run");
        assert_eq!(output.status.code(), Some(1));
        assert!(String::from_utf8_lossy(&output.stderr).contains("r2"));
    }
    let missing = harness.root.join("missing-repository");
    let missing = missing.to_str().expect("UTF-8 missing repository path");
    for arguments in [
        vec![
            "run-log",
            "publish",
            "--repo-root",
            missing,
            "--skill",
            "review",
            "--run-id",
            "missing-repository",
        ],
        vec!["run-log", "sync", "--repo-root", missing],
        vec!["run-log", "sync", "--unexpected"],
    ] {
        let output = harness.run(&arguments);
        assert_eq!(output.status.code(), Some(2));
    }
    assert!(harness.run(&["run-log", "sync", "--help"]).status.success());
    assert!(harness.run(&["run-log", "sync"]).status.success());
}
#[test]
fn persisted_context_rehydrates_in_a_later_process_without_shell_state() {
    let harness = Harness::new();
    let repo = harness.repo.to_str().expect("UTF-8 repo path");
    let started = harness.run(&[
        "run-log",
        "lifecycle-start",
        "--repo-root",
        repo,
        "--skill",
        "review",
        "--run-id",
        "rehydrated-process",
    ]);
    assert!(
        started.status.success(),
        "start failed: {}",
        String::from_utf8_lossy(&started.stderr)
    );
    let context_file = output_value(&started, "CONTEXT_FILE");
    let run_dir = output_value(&started, "RUN_DIR");

    let rehydrated = harness.run(&[
        "run-log",
        "lifecycle-start",
        "--repo-root",
        repo,
        "--skill",
        "review",
        "--run-id",
        "rehydrated-process",
        "--rehydrate",
    ]);
    assert!(
        rehydrated.status.success(),
        "rehydration failed: {}",
        String::from_utf8_lossy(&rehydrated.stderr)
    );
    assert_eq!(output_value(&rehydrated, "CONTEXT_FILE"), context_file);
    assert_eq!(output_value(&rehydrated, "RUN_DIR"), run_dir);
    assert_eq!(output_value(&rehydrated, "LIFECYCLE_STARTED"), "true");
    assert_eq!(
        output_value(&rehydrated, "STORAGE_PREFLIGHT"),
        "skipped-disabled"
    );
}

#[test]
fn lifecycle_start_rejects_invalid_arguments_and_missing_state() {
    let harness = Harness::new();
    let repo = harness.repo.to_str().expect("UTF-8 repo path");

    let invalid_rehydrate = harness.run(&[
        "run-log",
        "lifecycle-start",
        "--repo-root",
        repo,
        "--skill",
        "review",
        "--run-id",
        "invalid-rehydrate",
        "--issue",
        "8077",
        "--rehydrate",
    ]);
    assert!(!invalid_rehydrate.status.success());
    assert!(
        String::from_utf8_lossy(&invalid_rehydrate.stderr).contains("--rehydrate requires only")
    );

    let missing_rehydrate = harness.run(&[
        "run-log",
        "lifecycle-start",
        "--repo-root",
        repo,
        "--skill",
        "review",
        "--run-id",
        "missing-rehydrate",
        "--rehydrate",
    ]);
    assert!(!missing_rehydrate.status.success());
    assert!(
        String::from_utf8_lossy(&missing_rehydrate.stderr)
            .contains("lifecycle context is missing or unsafe")
    );

    let invalid_issue = harness.run(&[
        "run-log",
        "lifecycle-start",
        "--repo-root",
        repo,
        "--skill",
        "review",
        "--run-id",
        "invalid-issue",
        "--issue",
        "80x77",
    ]);
    assert!(!invalid_issue.status.success());
    assert!(String::from_utf8_lossy(&invalid_issue.stderr).contains("invalid issue"));

    let missing_repo = harness.root.join("missing-repository");
    let missing_repo = missing_repo.to_str().expect("UTF-8 missing path");
    let resolution_failure = harness.run(&[
        "run-log",
        "lifecycle-start",
        "--repo-root",
        missing_repo,
        "--skill",
        "review",
    ]);
    assert!(!resolution_failure.status.success());
}

#[test]
fn lifecycle_finalize_failures_preserve_closed_cli_envelopes() {
    let harness = Harness::new();
    let repo = harness.repo.to_str().expect("UTF-8 repo path");

    let missing_terminal = harness.run(&[
        "run-log",
        "lifecycle-finalize",
        "--repo-root",
        repo,
        "--skill",
        "review",
        "--run-id",
        "missing-terminal",
    ]);
    assert!(!missing_terminal.status.success());
    assert_eq!(
        String::from_utf8_lossy(&missing_terminal.stdout),
        "RUN_LOG_PUBLICATION=failed\nLIFECYCLE_FLUSHED=false\nLIFECYCLE_TERMINALIZED=false\n"
    );

    let started = harness.run(&[
        "run-log",
        "lifecycle-start",
        "--repo-root",
        repo,
        "--skill",
        "review",
        "--run-id",
        "terminal-drift",
    ]);
    assert!(started.status.success());
    let manifest_path = PathBuf::from(output_value(&started, "RUN_DIR")).join("manifest.json");
    let mut manifest: serde_json::Value =
        serde_json::from_slice(&fs::read(&manifest_path).expect("manifest bytes"))
            .expect("manifest");
    manifest["lifecycle_schema_version"] = serde_json::json!(999);
    fs::write(
        &manifest_path,
        serde_json::to_vec(&manifest).expect("manifest encoding"),
    )
    .expect("manifest drift");
    let terminal_failure = harness.run(&[
        "run-log",
        "lifecycle-finalize",
        "--repo-root",
        repo,
        "--skill",
        "review",
        "--run-id",
        "terminal-drift",
    ]);
    assert!(!terminal_failure.status.success());
    assert_eq!(
        String::from_utf8_lossy(&terminal_failure.stdout),
        "RUN_LOG_PUBLICATION=failed\nLIFECYCLE_FLUSHED=false\nLIFECYCLE_TERMINALIZED=false\n"
    );
}
