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

    fn run(&self, arguments: &[&str]) -> Output {
        Command::new(env!("CARGO_BIN_EXE_larch"))
            .args(arguments)
            .env("HOME", self.root.join("home"))
            .env("XDG_STATE_HOME", self.root.join("state"))
            .env("XDG_CACHE_HOME", self.root.join("cache"))
            .env_remove("LARCH_LOGS_URI")
            .env_remove("LARCH_STORAGE_BASE_URI")
            .current_dir(&self.repo)
            .output()
            .expect("larch should run")
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
