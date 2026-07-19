use std::{
    ffi::OsString,
    fs,
    path::{Path, PathBuf},
    process::Command as ProcessCommand,
};

use assert_cmd::Command;
use predicates::prelude::*;

const ROOT_HELP: &str = "\
Larch workflow automation

Usage: larch <COMMAND>

Commands:
  example        Non-production commands that exercise dispatcher wiring
  git            Local repository status and snapshot operations
  release        Release-maintenance commands
  gh             GitHub workflow helper commands
  upgrade-larch  Upgrade the installed larch plugin and executable
  help           Print this message or the help of the given subcommand(s)

Options:
  -h, --help     Print help
  -V, --version  Print version
";

const EXAMPLE_HELP: &str = "\
Non-production commands that exercise dispatcher wiring

Usage: larch example <COMMAND>

Commands:
  echo  Print a message through the core library
  help  Print this message or the help of the given subcommand(s)

Options:
  -h, --help  Print help
";

fn larch() -> Command {
    Command::cargo_bin("larch").expect("larch binary should build")
}

fn git(root: &Path, arguments: &[&str]) {
    let output = ProcessCommand::new("git")
        .args(arguments)
        .current_dir(root)
        .env("GIT_CONFIG_NOSYSTEM", "1")
        .env("GIT_CONFIG_GLOBAL", "/dev/null")
        .output()
        .expect("Git should launch");
    assert!(
        output.status.success(),
        "git {arguments:?} failed: {}",
        String::from_utf8_lossy(&output.stderr)
    );
}

fn repository() -> tempfile::TempDir {
    let directory = tempfile::tempdir().expect("temporary repository");
    git(
        directory.path(),
        &["init", "--quiet", "--initial-branch=main"],
    );
    git(directory.path(), &["config", "user.name", "Larch Test"]);
    git(
        directory.path(),
        &["config", "user.email", "larch-test@example.invalid"],
    );
    fs::write(directory.path().join("tracked.txt"), "base\n").expect("seed tracked file");
    git(directory.path(), &["add", "tracked.txt"]);
    git(directory.path(), &["commit", "--quiet", "-m", "base"]);
    directory
}

fn command_at(root: &Path, arguments: &[&str]) -> Command {
    let mut command = larch();
    command.current_dir(root).args(arguments);
    command
}

#[test]
fn help_has_pinned_output_and_success_exit() {
    larch()
        .arg("--help")
        .assert()
        .code(0)
        .stdout(ROOT_HELP)
        .stderr("");
}

#[test]
fn version_reports_the_workspace_version() {
    larch()
        .arg("--version")
        .assert()
        .success()
        .stderr("")
        .stdout(predicate::eq(format!(
            "larch {}\n",
            env!("CARGO_PKG_VERSION")
        )));
}

#[test]
fn bootstrap_self_check_reports_machine_readable_build_identity() {
    let output = larch()
        .args(["bootstrap", "self-check"])
        .output()
        .expect("self-check should run");

    assert!(output.status.success());
    assert!(output.stderr.is_empty());
    let payload: serde_json::Value =
        serde_json::from_slice(&output.stdout).expect("self-check should emit JSON");
    assert_eq!(payload["schema_version"], 1);
    assert_eq!(payload["version"], env!("CARGO_PKG_VERSION"));
    assert!(
        payload["target"]
            .as_str()
            .is_some_and(|target| !target.is_empty())
    );
}

#[test]
fn compiled_version_matches_the_plugin_release_version() {
    let plugin_manifest_path =
        Path::new(env!("CARGO_MANIFEST_DIR")).join("../../.claude-plugin/plugin.json");
    let plugin_manifest =
        fs::read_to_string(&plugin_manifest_path).expect("plugin manifest should be readable");
    let plugin_manifest: serde_json::Value =
        serde_json::from_str(&plugin_manifest).expect("plugin manifest should contain valid JSON");

    assert_eq!(
        plugin_manifest["version"].as_str(),
        Some(env!("CARGO_PKG_VERSION")),
        "workspace package version must match .claude-plugin/plugin.json"
    );
}

#[test]
fn example_echo_dispatches_through_the_core_library() {
    larch()
        .args(["example", "echo", "library wiring"])
        .assert()
        .success()
        .stdout("library wiring\n")
        .stderr("");
}

#[test]
fn workflow_path_preserves_its_legacy_stdout_contract() {
    larch()
        .args(["gh", "workflow-path"])
        .assert()
        .success()
        .stdout("unknown\n")
        .stderr("");
}

#[test]
fn run_logs_reports_missing_rust_credential_without_fallback() {
    larch()
        .env_remove("LARCH_GH_TOKEN")
        .args(["gh", "run-logs", "--run-id", "7", "--repo", "owner/repo"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "--- CI log (run 7, repo owner/repo): failed-job log shown.",
        ))
        .stdout(predicate::str::contains("LARCH_GH_TOKEN is required"))
        .stderr("");
}

#[test]
fn missing_domain_has_pinned_help_and_usage_exit() {
    larch().assert().code(2).stdout("").stderr(ROOT_HELP);
}

#[test]
fn unknown_domain_has_pinned_error_and_does_not_fallback() {
    larch()
        .arg("python-command")
        .assert()
        .code(2)
        .stdout("")
        .stderr("error: unrecognized subcommand\n");
}

#[test]
fn missing_verb_has_pinned_help_and_usage_exit() {
    larch()
        .arg("example")
        .assert()
        .code(2)
        .stdout("")
        .stderr(EXAMPLE_HELP);
}

#[test]
fn unknown_verb_has_pinned_error_and_does_not_fallback() {
    larch()
        .args(["example", "python-verb"])
        .assert()
        .code(2)
        .stdout("")
        .stderr("error: unrecognized subcommand\n");
}

#[test]
fn missing_argument_has_pinned_error_and_usage_exit() {
    larch()
        .args(["example", "echo"])
        .assert()
        .code(2)
        .stdout("")
        .stderr("error: one or more required arguments were not provided\n");
}

#[test]
fn clean_tree_reports_clean_and_tracked_or_untracked_dirty_state() {
    let repository = repository();
    command_at(repository.path(), &["git", "clean-tree", "--fail-closed"])
        .assert()
        .success()
        .stdout("CLEAN=true\n")
        .stderr("");

    fs::write(repository.path().join("tracked.txt"), "changed\n").expect("dirty tracked file");
    command_at(repository.path(), &["git", "clean-tree"])
        .assert()
        .success()
        .stdout(predicate::str::starts_with(
            "CLEAN=false\nDIRTY_OUT= M tracked.txt ",
        ))
        .stderr("");

    fs::remove_file(repository.path().join("tracked.txt")).expect("remove dirty fixture");
    git(repository.path(), &["checkout", "--", "tracked.txt"]);
    fs::write(repository.path().join("untracked.txt"), "new\n").expect("untracked file");
    command_at(repository.path(), &["git", "clean-tree"])
        .assert()
        .success()
        .stdout(predicate::str::contains("DIRTY_OUT=?? untracked.txt "))
        .stderr("");
}

#[test]
fn conflict_files_reports_each_present_index_stage() {
    let repository = repository();
    git(repository.path(), &["branch", "other"]);
    fs::write(repository.path().join("tracked.txt"), "main\n").expect("main change");
    git(repository.path(), &["commit", "--quiet", "-am", "main"]);
    git(repository.path(), &["checkout", "--quiet", "other"]);
    fs::write(repository.path().join("tracked.txt"), "other\n").expect("other change");
    git(repository.path(), &["commit", "--quiet", "-am", "other"]);
    git(repository.path(), &["checkout", "--quiet", "main"]);
    let merge = ProcessCommand::new("git")
        .args(["merge", "--no-edit", "other"])
        .current_dir(repository.path())
        .output()
        .expect("merge should launch");
    assert!(!merge.status.success(), "fixture must conflict");

    command_at(repository.path(), &["git", "conflict-files"])
        .assert()
        .success()
        .stdout("FILE=tracked.txt\nSTAGE_1=true\nSTAGE_2=true\nSTAGE_3=true\n\n")
        .stderr("");
}

#[test]
fn snapshot_untracked_sorts_raw_paths_and_cleans_up_output_failures() {
    let repository = repository();
    fs::write(repository.path().join("b.txt"), "b\n").expect("untracked b");
    fs::write(repository.path().join("a.txt"), "a\n").expect("untracked a");
    let output = repository.path().join("snapshot.z");
    command_at(
        repository.path(),
        &[
            "git",
            "snapshot-untracked",
            "--output",
            output.to_str().unwrap(),
            "--nul",
        ],
    )
    .assert()
    .success()
    .stdout("")
    .stderr("");
    assert_eq!(
        fs::read(&output).expect("snapshot output"),
        b"a.txt\0b.txt\0"
    );

    let failed_output = repository.path().join("missing-parent/output.z");
    command_at(
        repository.path(),
        &[
            "git",
            "snapshot-untracked",
            "--output",
            failed_output.to_str().unwrap(),
        ],
    )
    .assert()
    .success()
    .stdout("")
    .stderr("");
    assert!(!failed_output.exists());
    assert!(!PathBuf::from(format!("{}.tmp", failed_output.display())).exists());
}

#[test]
fn snapshot_untracked_missing_output_keeps_legacy_success_exit() {
    let repository = repository();
    command_at(repository.path(), &["git", "snapshot-untracked"])
        .assert()
        .success()
        .stdout("")
        .stderr("snapshot-untracked.sh: --output is required\n");
}

#[test]
fn malformed_repository_is_fail_open_by_default_and_fail_closed_on_request() {
    let directory = tempfile::tempdir().expect("non-repository directory");
    command_at(directory.path(), &["git", "clean-tree"])
        .assert()
        .success()
        .stdout("CLEAN=true\n")
        .stderr("");
    command_at(directory.path(), &["git", "clean-tree", "--fail-closed"])
        .assert()
        .code(1)
        .stdout(predicate::str::starts_with(
            "CLEAN=unknown\nPROBE_ERROR=git exited 1 (",
        ))
        .stderr("");
}

#[cfg(unix)]
#[test]
fn snapshot_untracked_preserves_non_utf8_path_bytes() {
    use std::os::unix::ffi::OsStringExt;

    let repository = repository();
    let path = PathBuf::from(OsString::from_vec(b"non-utf8-\xff".to_vec()));
    if let Err(error) = fs::write(repository.path().join(&path), b"raw\n") {
        eprintln!("fixture skipped: raw byte paths are unsupported: {error}");
        return;
    }
    let output = repository.path().join("snapshot.z");
    command_at(
        repository.path(),
        &[
            "git",
            "snapshot-untracked",
            "--output",
            output.to_str().unwrap(),
            "--nul",
        ],
    )
    .assert()
    .success();
    assert_eq!(
        fs::read(output).expect("snapshot output"),
        b"non-utf8-\xff\0"
    );
}
