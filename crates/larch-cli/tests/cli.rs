use std::{
    ffi::{OsStr, OsString},
    fs,
    path::{Path, PathBuf},
    process::{Command as ProcessCommand, Output},
};

use assert_cmd::Command;
use predicates::prelude::*;

const ROOT_HELP: &str = "\
Larch workflow automation

Usage: larch <COMMAND>

Commands:
  example        Non-production commands that exercise dispatcher wiring
  git            Local Git repository commands
  plugin         Plugin metadata commands
  release        Release-maintenance commands
  gh             GitHub workflow helper commands
  push           Push commands with typed Git network operations
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

const GIT_HELP: &str = "\
Local Git repository commands

Usage: larch git <COMMAND>

Commands:
  amend-add            Stage paths and amend them into the current commit
  branch-info          Emit `HEAD_SHA` and `CURRENT_BRANCH` for the cwd repository
  check-phantom-dirty  Classify repository changes against an untracked-path baseline
  check-remote-branch  Probe whether a remote branch exists via typed ls-remote
  check-main-sync      Classify or reset a flush-only local main branch ahead of origin/main
  checkout-ours        Check out the current side of conflicted paths
  clean-tree           Report whether the worktree is clean using machine-readable key/value rows
  commit               Stage optional paths and create a commit
  conflict-files       Print the files and index stages that are currently conflicted
  count-commits        Count commits on `HEAD` since `origin/main` or `main`
  current-branch       Emit `BRANCH` for the current symbolic `HEAD`
  phantom-probe        Classify phantom paths and append advisory warnings to the run ledger
  rebase-abort         Abort an in-progress rebase, succeeding when no rebase is active
  rebase-skip          Skip the current commit in an in-progress rebase
  show-stage           Print the blob at an index conflict stage
  sync-local-main      Update a non-checked-out local main branch from its remote-tracking ref
  snapshot-untracked   Atomically write the sorted untracked-path baseline to an output file
  stage                Stage one or more paths
  help                 Print this message or the help of the given subcommand(s)

Options:
  -h, --help  Print help
";

fn larch() -> Command {
    Command::cargo_bin("larch").expect("larch binary should build")
}

fn git_output<I, S>(root: &Path, arguments: I) -> Output
where
    I: IntoIterator<Item = S>,
    S: AsRef<OsStr>,
{
    ProcessCommand::new("git")
        .args(arguments)
        .current_dir(root)
        .env("GIT_CONFIG_NOSYSTEM", "1")
        .env("GIT_CONFIG_GLOBAL", "/dev/null")
        .env("GIT_EDITOR", "true")
        .env("GIT_SEQUENCE_EDITOR", "true")
        .output()
        .expect("Git should launch")
}

fn git<I, S>(root: &Path, arguments: I)
where
    I: IntoIterator<Item = S>,
    S: AsRef<OsStr>,
{
    let output = git_output(root, arguments);
    assert!(
        output.status.success(),
        "Git fixture command failed: {}",
        String::from_utf8_lossy(&output.stderr)
    );
}

fn repository() -> tempfile::TempDir {
    let directory = tempfile::tempdir().expect("temporary repository");
    git(
        directory.path(),
        ["init", "--quiet", "--initial-branch=main"],
    );
    git(directory.path(), ["config", "user.name", "Larch Test"]);
    git(
        directory.path(),
        ["config", "user.email", "larch-test@example.invalid"],
    );
    fs::write(directory.path().join("tracked.txt"), "base\n").expect("seed tracked file");
    git(directory.path(), ["add", "tracked.txt"]);
    git(directory.path(), ["commit", "--quiet", "-m", "base"]);
    directory
}

fn command_at(root: &Path, arguments: &[&str]) -> Command {
    let mut command = larch();
    command.current_dir(root).args(arguments);
    command
}

fn merge_conflict_repository(path: &Path) -> tempfile::TempDir {
    let directory = repository();
    fs::write(directory.path().join(path), b"base\n").expect("seed conflict path");
    git(
        directory.path(),
        [OsStr::new("add"), OsStr::new("--"), path.as_os_str()],
    );
    git(
        directory.path(),
        ["commit", "--quiet", "-m", "seed conflict path"],
    );
    git(directory.path(), ["branch", "other"]);
    fs::write(directory.path().join(path), b"main\n").expect("main conflict change");
    git(
        directory.path(),
        ["commit", "--quiet", "-am", "main change"],
    );
    git(directory.path(), ["checkout", "--quiet", "other"]);
    fs::write(directory.path().join(path), b"other\n").expect("other conflict change");
    git(
        directory.path(),
        ["commit", "--quiet", "-am", "other change"],
    );
    git(directory.path(), ["checkout", "--quiet", "main"]);
    let merge = git_output(directory.path(), ["merge", "--no-edit", "other"]);
    assert!(!merge.status.success(), "fixture must conflict");
    directory
}

fn rebase_conflict_repository() -> tempfile::TempDir {
    let directory = repository();
    git(directory.path(), ["branch", "topic"]);
    fs::write(directory.path().join("tracked.txt"), b"main\n").expect("main change");
    git(
        directory.path(),
        ["commit", "--quiet", "-am", "main change"],
    );
    git(directory.path(), ["checkout", "--quiet", "topic"]);
    fs::write(directory.path().join("tracked.txt"), b"topic\n").expect("topic change");
    git(
        directory.path(),
        ["commit", "--quiet", "-am", "topic change"],
    );
    let rebase = git_output(directory.path(), ["rebase", "main"]);
    assert!(!rebase.status.success(), "fixture rebase must conflict");
    directory
}

fn delete_modify_conflict_repository() -> tempfile::TempDir {
    let directory = repository();
    git(directory.path(), ["branch", "other"]);
    git(directory.path(), ["rm", "--quiet", "--", "tracked.txt"]);
    git(
        directory.path(),
        ["commit", "--quiet", "-m", "delete on main"],
    );
    git(directory.path(), ["checkout", "--quiet", "other"]);
    fs::write(directory.path().join("tracked.txt"), b"other\n").expect("other change");
    git(
        directory.path(),
        ["commit", "--quiet", "-am", "modify on other"],
    );
    git(directory.path(), ["checkout", "--quiet", "main"]);
    let merge = git_output(directory.path(), ["merge", "--no-edit", "other"]);
    assert!(!merge.status.success(), "fixture must have a missing stage");
    directory
}

fn configure_failing_smudge_filter(root: &Path, path: &OsStr) {
    let mut attributes = path.as_encoded_bytes().to_vec();
    attributes.extend_from_slice(b" filter=larch-test\n");
    fs::write(root.join(".gitattributes"), attributes).expect("write filter attributes");
    git(root, ["config", "filter.larch-test.clean", "cat"]);
    git(root, ["config", "filter.larch-test.smudge", "false"]);
    git(root, ["config", "filter.larch-test.required", "true"]);
}

fn assert_fsck(root: &Path) {
    git(root, ["fsck", "--full", "--no-dangling"]);
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
    git(repository.path(), ["checkout", "--", "tracked.txt"]);
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
    git(repository.path(), ["branch", "other"]);
    fs::write(repository.path().join("tracked.txt"), "main\n").expect("main change");
    git(repository.path(), ["commit", "--quiet", "-am", "main"]);
    git(repository.path(), ["checkout", "--quiet", "other"]);
    fs::write(repository.path().join("tracked.txt"), "other\n").expect("other change");
    git(repository.path(), ["commit", "--quiet", "-am", "other"]);
    git(repository.path(), ["checkout", "--quiet", "main"]);
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
fn checkout_ours_preserves_conflict_stages_and_accepts_spaced_paths() {
    let path = Path::new("path with spaces.txt");
    let repository = merge_conflict_repository(path);
    let before = git_output(repository.path(), ["ls-files", "--stage"]);

    command_at(
        repository.path(),
        &["git", "checkout-ours", path.to_str().unwrap()],
    )
    .assert()
    .success()
    .stdout("")
    .stderr("");

    assert_eq!(
        fs::read(repository.path().join(path)).expect("checked out conflict path"),
        b"main\n"
    );
    let after = git_output(repository.path(), ["ls-files", "--stage"]);
    assert_eq!(
        before.stdout, after.stdout,
        "checkout must retain index stages"
    );
    assert_fsck(repository.path());
}

#[test]
fn checkout_ours_preserves_missing_stages_on_failure() {
    let repository = delete_modify_conflict_repository();
    let before = git_output(repository.path(), ["ls-files", "--stage"]);
    assert!(!String::from_utf8_lossy(&before.stdout).contains(" 2\ttracked.txt"));

    command_at(repository.path(), &["git", "checkout-ours", "tracked.txt"])
        .assert()
        .code(1)
        .stdout("")
        .stderr(predicate::str::contains(
            "path 'tracked.txt' does not have our version",
        ));

    let after = git_output(repository.path(), ["ls-files", "--stage"]);
    assert_eq!(
        before.stdout, after.stdout,
        "failure must retain index stages"
    );
    assert_fsck(repository.path());
}

#[test]
fn checkout_ours_preserves_state_when_a_required_filter_fails() {
    let repository = merge_conflict_repository(Path::new("filtered.txt"));
    configure_failing_smudge_filter(repository.path(), OsStr::new("filtered.txt"));
    let before = git_output(repository.path(), ["ls-files", "--stage"]);

    command_at(repository.path(), &["git", "checkout-ours", "filtered.txt"])
        .assert()
        .code(128)
        .stdout("")
        .stderr(predicate::str::contains("smudge filter larch-test failed"));

    let after = git_output(repository.path(), ["ls-files", "--stage"]);
    assert_eq!(
        before.stdout, after.stdout,
        "filter failure must retain stages"
    );
    assert_fsck(repository.path());
}

#[test]
fn checkout_ours_rejects_missing_arguments_and_leaves_non_conflicted_paths_unchanged() {
    let repository = repository();
    command_at(repository.path(), &["git", "checkout-ours"])
        .assert()
        .code(1)
        .stdout("")
        .stderr(
            "git-checkout-ours.sh: at least one file argument is required\n\
             usage: git-checkout-ours.sh <file> [<file> ...]\n",
        );

    let original = fs::read(repository.path().join("tracked.txt")).expect("tracked contents");
    command_at(repository.path(), &["git", "checkout-ours", "tracked.txt"])
        .assert()
        .success()
        .stdout("")
        .stderr("");
    assert_eq!(
        fs::read(repository.path().join("tracked.txt")).expect("tracked contents"),
        original
    );
    assert_fsck(repository.path());
}

#[test]
fn rebase_abort_is_idempotent_and_restores_pre_rebase_state() {
    let clean = repository();
    command_at(clean.path(), &["git", "rebase-abort"])
        .assert()
        .success()
        .stdout("")
        .stderr("");
    assert_fsck(clean.path());

    let repository = rebase_conflict_repository();
    assert!(repository.path().join(".git/rebase-merge").is_dir());
    command_at(repository.path(), &["git", "rebase-abort"])
        .assert()
        .success()
        .stdout("")
        .stderr("");
    assert!(!repository.path().join(".git/rebase-merge").exists());
    assert_eq!(
        fs::read(repository.path().join("tracked.txt")).expect("restored topic contents"),
        b"topic\n"
    );
    let branch = git_output(repository.path(), ["branch", "--show-current"]);
    assert_eq!(branch.stdout, b"topic\n");
    assert_fsck(repository.path());
}

#[test]
fn rebase_controls_preserve_legacy_unknown_argument_contracts() {
    let repository = repository();
    command_at(repository.path(), &["git", "rebase-abort", "--unexpected"])
        .assert()
        .success()
        .stdout("")
        .stderr("git-rebase-abort.sh: unknown argument: --unexpected\n");
    command_at(repository.path(), &["git", "rebase-skip", "--unexpected"])
        .assert()
        .code(1)
        .stdout("")
        .stderr("git-rebase-skip.sh: unknown argument: --unexpected\n");
}

#[test]
fn rebase_skip_preserves_git_diagnostics_and_completes_the_rebase() {
    let clean = repository();
    command_at(clean.path(), &["git", "rebase-skip"])
        .assert()
        .failure()
        .stdout("")
        .stderr(
            predicate::str::contains("no rebase in progress")
                .or(predicate::str::contains("No rebase in progress")),
        );
    assert_fsck(clean.path());

    let repository = rebase_conflict_repository();
    command_at(repository.path(), &["git", "rebase-skip"])
        .assert()
        .success();
    assert!(!repository.path().join(".git/rebase-merge").exists());
    assert_eq!(
        fs::read(repository.path().join("tracked.txt")).expect("rebased worktree contents"),
        b"main\n"
    );
    let head = git_output(repository.path(), ["rev-parse", "HEAD"]);
    let main = git_output(repository.path(), ["rev-parse", "main"]);
    assert_eq!(
        head.stdout, main.stdout,
        "skip must omit the conflicting commit"
    );
    assert_fsck(repository.path());
}

#[test]
fn interrupted_rebase_controls_retain_state_and_allow_recovery() {
    for verb in ["rebase-abort", "rebase-skip"] {
        let repository = rebase_conflict_repository();
        configure_failing_smudge_filter(repository.path(), OsStr::new("tracked.txt"));
        let before = git_output(repository.path(), ["ls-files", "--stage"]);

        let mut command = command_at(repository.path(), &["git", verb]);
        if verb == "rebase-abort" {
            command.assert().success().stdout("").stderr("");
        } else {
            command
                .assert()
                .code(128)
                .stderr(predicate::str::contains("smudge filter larch-test failed"));
        }
        assert!(repository.path().join(".git/rebase-merge").is_dir());
        let after = git_output(repository.path(), ["ls-files", "--stage"]);
        assert_eq!(
            before.stdout, after.stdout,
            "interruption must retain stages"
        );
        assert_fsck(repository.path());

        git(
            repository.path(),
            ["config", "filter.larch-test.smudge", "cat"],
        );
        command_at(repository.path(), &["git", "rebase-abort"])
            .assert()
            .success()
            .stdout("")
            .stderr("");
        assert!(!repository.path().join(".git/rebase-merge").exists());
        assert_fsck(repository.path());
    }
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

#[test]
fn check_phantom_dirty_classifies_clean_tracked_phantom_and_mixed_states() {
    let repository = repository();
    let artifacts = tempfile::tempdir().expect("phantom artifacts directory");
    let baseline = artifacts.path().join("baseline.z");
    let paths = artifacts.path().join("phantom");
    fs::write(&baseline, []).expect("empty baseline");
    let arguments = || {
        vec![
            "git".to_owned(),
            "check-phantom-dirty".to_owned(),
            "--baseline".to_owned(),
            baseline.to_string_lossy().into_owned(),
            "--step".to_owned(),
            "step-1".to_owned(),
            "--phantom-paths-dir".to_owned(),
            paths.to_string_lossy().into_owned(),
        ]
    };

    command_at_owned(repository.path(), &arguments())
        .assert()
        .success()
        .stdout("STATUS=clean\n")
        .stderr("");

    fs::write(repository.path().join("tracked.txt"), "changed\n").expect("tracked change");
    command_at_owned(repository.path(), &arguments())
        .assert()
        .success()
        .stdout("STATUS=tracked-only\n")
        .stderr("");

    git(repository.path(), ["checkout", "--", "tracked.txt"]);
    fs::write(repository.path().join("new path.txt"), "new\n").expect("new untracked path");
    command_at_owned(repository.path(), &arguments())
        .assert()
        .success()
        .stdout(format!(
            "STATUS=phantom\nPHANTOM_COUNT=1\nPHANTOM_PATHS_FILE={}\n",
            paths.join("phantom-paths-step-1.z").display()
        ))
        .stderr("");
    assert_eq!(
        fs::read(paths.join("phantom-paths-step-1.z")).expect("phantom path artifact"),
        b"new path.txt\0"
    );

    fs::write(repository.path().join("tracked.txt"), "mixed\n").expect("mixed tracked change");
    command_at_owned(repository.path(), &arguments())
        .assert()
        .success()
        .stdout(format!(
            "STATUS=phantom\nPHANTOM_COUNT=1\nPHANTOM_PATHS_FILE={}\n",
            paths.join("phantom-paths-step-1.z").display()
        ))
        .stderr("");
}

#[test]
fn check_phantom_dirty_preserves_advisory_parse_and_baseline_failures() {
    let repository = repository();
    let paths = repository.path().join("phantom");
    fs::write(repository.path().join("new.txt"), "new\n").expect("new untracked path");
    let missing = repository.path().join("missing.z");
    let common = [
        "--step".to_owned(),
        "s1".to_owned(),
        "--phantom-paths-dir".to_owned(),
        paths.to_string_lossy().into_owned(),
    ];
    let mut missing_arguments = vec![
        "git".to_owned(),
        "check-phantom-dirty".to_owned(),
        "--baseline".to_owned(),
        missing.to_string_lossy().into_owned(),
    ];
    missing_arguments.extend(common.clone());
    command_at_owned(repository.path(), &missing_arguments)
        .assert()
        .success()
        .stdout("STATUS=unknown\nREASON=baseline-missing-untracked-ambiguous\n")
        .stderr("");

    let malformed = repository.path().join("bad baseline.z");
    fs::write(&malformed, b"new.txt").expect("malformed baseline fixture");
    let mut malformed_arguments = vec![
        "git".to_owned(),
        "check-phantom-dirty".to_owned(),
        "--baseline".to_owned(),
        malformed.to_string_lossy().into_owned(),
    ];
    malformed_arguments.extend(common);
    command_at_owned(repository.path(), &malformed_arguments)
        .assert()
        .success()
        .stdout("STATUS=unknown\nREASON=bad-baseline-path\n")
        .stderr("");

    command_at(
        repository.path(),
        &["git", "check-phantom-dirty", "--unknown"],
    )
    .assert()
    .success()
    .stdout("STATUS=unknown\nREASON=unknown-flag\n")
    .stderr("");
    command_at(repository.path(), &["git", "check-phantom-dirty", "--help"])
        .assert()
        .success()
        .stdout("STATUS=unknown\nREASON=unknown-flag\n")
        .stderr("");

    let valid = repository.path().join("valid.z");
    let blocked_paths = repository.path().join("blocked-paths");
    fs::write(&valid, b"valid.z\0").expect("valid baseline");
    fs::write(&blocked_paths, b"not a directory").expect("blocked output fixture");
    let output_failure_arguments = [
        "git".to_owned(),
        "check-phantom-dirty".to_owned(),
        "--baseline".to_owned(),
        valid.to_string_lossy().into_owned(),
        "--step".to_owned(),
        "output".to_owned(),
        "--phantom-paths-dir".to_owned(),
        blocked_paths.to_string_lossy().into_owned(),
    ];
    command_at_owned(repository.path(), &output_failure_arguments)
        .assert()
        .success()
        .stdout("STATUS=unknown\nREASON=phantom-paths-dir-create-failed\n")
        .stderr("");

    fs::remove_file(repository.path().join(".git/index")).expect("remove repository index");
    fs::create_dir(repository.path().join(".git/index")).expect("unreadable repository index");
    command_at_owned(repository.path(), &output_failure_arguments)
        .assert()
        .success()
        .stdout("STATUS=unknown\nREASON=git-status-failed\n")
        .stderr("");
}

#[test]
fn phantom_probe_appends_warning_and_keeps_append_failure_advisory() {
    let repository = repository();
    let artifacts = tempfile::tempdir().expect("phantom artifacts directory");
    let implement_tmpdir = fs::canonicalize(artifacts.path())
        .expect("canonical phantom artifacts directory")
        .join("implement");
    fs::create_dir(&implement_tmpdir).expect("implement tmpdir");
    fs::write(implement_tmpdir.join("untracked-baseline.z"), []).expect("empty baseline");
    fs::write(repository.path().join("new.txt"), "new\n").expect("new untracked path");

    let mut command = command_at(
        repository.path(),
        &["git", "phantom-probe", "--step", "8-pre-ship"],
    );
    command.env("IMPLEMENT_TMPDIR", &implement_tmpdir);
    command
        .assert()
        .success()
        .stdout(format!(
            "PHANTOM_STATUS=phantom\nPHANTOM_COUNT=1\nPHANTOM_PATHS_FILE={}\n",
            implement_tmpdir
                .join("phantom-paths-8-pre-ship.z")
                .display()
        ))
        .stderr("→ phantom-probe: 8-pre-ship\n");
    assert_eq!(
        fs::read_to_string(implement_tmpdir.join("execution-issues.md")).expect("warning ledger"),
        format!(
            "### Warnings\n\n- **Step 8-pre-ship — phantom untracked files:** 1 file(s) appeared since session baseline (inspect {}/phantom-paths-8-pre-ship.z locally)\n",
            implement_tmpdir.display()
        )
    );
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt as _;

        assert_eq!(
            fs::metadata(implement_tmpdir.join("execution-issues.md"))
                .expect("warning ledger metadata")
                .permissions()
                .mode()
                & 0o777,
            0o600
        );
    }

    fs::remove_file(implement_tmpdir.join("execution-issues.md")).expect("remove warning ledger");
    fs::create_dir(implement_tmpdir.join("execution-issues.md")).expect("append failure fixture");
    let mut failed = command_at(
        repository.path(),
        &["git", "phantom-probe", "--step", "append-fail"],
    );
    failed.env("IMPLEMENT_TMPDIR", &implement_tmpdir);
    failed
        .assert()
        .success()
        .stdout(
            predicate::str::contains("PHANTOM_STATUS=phantom\n")
                .and(predicate::str::contains("PHANTOM_APPEND_WARN_ERROR=")),
        )
        .stderr("→ phantom-probe: append-fail\n");
}

#[cfg(unix)]
#[test]
fn phantom_probe_refuses_a_symlinked_warning_ledger() {
    use std::os::unix::fs::symlink;

    let repository = repository();
    let artifacts = tempfile::tempdir().expect("phantom artifacts directory");
    let artifacts_root =
        fs::canonicalize(artifacts.path()).expect("canonical phantom artifacts directory");
    let implement_tmpdir = artifacts_root.join("implement");
    fs::create_dir(&implement_tmpdir).expect("implement tmpdir");
    fs::write(implement_tmpdir.join("untracked-baseline.z"), []).expect("empty baseline");
    fs::write(repository.path().join("new.txt"), "new\n").expect("new untracked path");
    let target = artifacts_root.join("warning-target.md");
    fs::write(&target, "unchanged\n").expect("warning target");
    let ledger = implement_tmpdir.join("execution-issues.md");
    symlink(&target, &ledger).expect("symlinked warning ledger");

    let mut command = command_at(
        repository.path(),
        &["git", "phantom-probe", "--step", "symlink"],
    );
    command.env("IMPLEMENT_TMPDIR", &implement_tmpdir);
    command
        .assert()
        .success()
        .stdout(predicate::str::contains(format!(
            "PHANTOM_APPEND_WARN_ERROR=refusing symlinked path or ancestor: {}\n",
            ledger.display()
        )))
        .stderr("→ phantom-probe: symlink\n");
    assert_eq!(
        fs::read_to_string(target).expect("warning target remains readable"),
        "unchanged\n"
    );
}

#[test]
fn phantom_commands_fail_closed_for_invalid_step_and_missing_repository() {
    let directory = tempfile::tempdir().expect("non-repository directory");
    let canonical_directory =
        fs::canonicalize(directory.path()).expect("canonical non-repository directory");
    let baseline = directory.path().join("baseline.z");
    fs::write(&baseline, []).expect("baseline");
    let check_arguments = [
        "git".to_owned(),
        "check-phantom-dirty".to_owned(),
        "--baseline".to_owned(),
        baseline.to_string_lossy().into_owned(),
        "--step".to_owned(),
        "s1".to_owned(),
        "--phantom-paths-dir".to_owned(),
        directory.path().to_string_lossy().into_owned(),
    ];
    command_at_owned(directory.path(), &check_arguments)
        .assert()
        .success()
        .stdout("STATUS=unknown\nREASON=git-status-failed\n")
        .stderr("");

    let mut no_repository = command_at(
        directory.path(),
        &["git", "phantom-probe", "--step", "no-repository"],
    );
    no_repository.env("IMPLEMENT_TMPDIR", &canonical_directory);
    no_repository
        .assert()
        .success()
        .stdout("PHANTOM_STATUS=unknown\nPHANTOM_REASON=git-status-failed\n")
        .stderr("→ phantom-probe: no-repository\n");

    let mut probe = command_at(
        directory.path(),
        &["git", "phantom-probe", "--step", "bad!step"],
    );
    probe.env("IMPLEMENT_TMPDIR", &canonical_directory);
    probe
        .assert()
        .success()
        .stdout("PHANTOM_STATUS=unknown\nPHANTOM_REASON=bad-step\n")
        .stderr("→ phantom-probe: bad!step\n");
}

#[cfg(unix)]
#[test]
fn check_phantom_dirty_preserves_non_utf8_path_bytes() {
    use std::os::unix::ffi::OsStringExt;

    let repository = repository();
    let artifacts = tempfile::tempdir().expect("phantom artifacts directory");
    let baseline = artifacts.path().join("baseline.z");
    let paths = artifacts.path().join("phantom");
    fs::write(&baseline, []).expect("baseline");
    let raw_path = PathBuf::from(OsString::from_vec(b"phantom-\xff".to_vec()));
    if let Err(error) = fs::write(repository.path().join(&raw_path), b"raw\n") {
        eprintln!("fixture skipped: raw byte paths are unsupported: {error}");
        return;
    }
    let arguments = [
        "git".to_owned(),
        "check-phantom-dirty".to_owned(),
        "--baseline".to_owned(),
        baseline.to_string_lossy().into_owned(),
        "--step".to_owned(),
        "raw".to_owned(),
        "--phantom-paths-dir".to_owned(),
        paths.to_string_lossy().into_owned(),
    ];
    command_at_owned(repository.path(), &arguments)
        .assert()
        .success();
    assert_eq!(
        fs::read(paths.join("phantom-paths-raw.z")).expect("raw phantom artifact"),
        b"phantom-\xff\0"
    );
}

#[test]
fn git_help_has_pinned_output() {
    larch()
        .args(["git", "--help"])
        .assert()
        .code(0)
        .stdout(GIT_HELP)
        .stderr("");
}

#[test]
fn git_current_branch_rejects_unknown_arguments() {
    larch()
        .args(["git", "current-branch", "--bogus"])
        .assert()
        .code(1)
        .stdout("")
        .stderr("git-current-branch.sh: unknown argument: --bogus\n");
}

#[test]
fn git_show_stage_rejects_invalid_stage() {
    larch()
        .args(["git", "show-stage", "--stage", "4", "--file", "x"])
        .assert()
        .code(1)
        .stdout("")
        .stderr("git-show-stage.sh: --stage must be 1, 2, or 3 (got: 4)\n");
}

#[test]
fn git_check_remote_branch_requires_branch_flag() {
    larch()
        .args(["git", "check-remote-branch"])
        .assert()
        .code(0)
        .stdout("STATE=error\nRC=1\nERROR=--branch is required\n")
        .stderr("");
}

#[test]
fn release_stage_commands_enter_the_rust_service_boundary() {
    let repository = repository();
    let commands = [
        vec!["release", "ensure-policy", "--repo", "character-ai/larch"],
        vec![
            "release",
            "stage",
            "--version",
            "1.2.3",
            "--notes-file",
            "missing",
            "--repo",
            "character-ai/larch",
            "--pr",
            "7",
        ],
        vec![
            "release",
            "asset-run",
            "--repo",
            "character-ai/larch",
            "--tag",
            "v1.2.3",
            "--source-commit",
            "1111111111111111111111111111111111111111",
        ],
        vec![
            "release",
            "validate-draft",
            "--version",
            "1.2.3",
            "--repo",
            "character-ai/larch",
            "--pr",
            "7",
            "--source-commit",
            "1111111111111111111111111111111111111111",
        ],
    ];
    for arguments in commands {
        larch()
            .current_dir(repository.path())
            .env_remove("LARCH_GH_TOKEN")
            .args(arguments)
            .assert()
            .failure()
            .stderr(predicate::str::contains("LARCH_GH_TOKEN is required"));
    }
}

fn command_at_owned(root: &Path, arguments: &[String]) -> Command {
    let mut command = larch();
    command.current_dir(root).args(arguments);
    command
}

#[cfg(unix)]
#[test]
fn checkout_ours_preserves_non_utf8_path_bytes() {
    use std::os::unix::ffi::OsStringExt;

    let path = PathBuf::from(OsString::from_vec(b"conflict-\xff.txt".to_vec()));
    let capability_probe = repository();
    if let Err(error) = fs::write(capability_probe.path().join(&path), b"probe\n") {
        eprintln!("fixture skipped: raw byte paths are unsupported: {error}");
        return;
    }
    let repository = merge_conflict_repository(&path);
    let mut command = larch();
    command
        .current_dir(repository.path())
        .args([OsString::from("git"), OsString::from("checkout-ours")])
        .arg(path.as_os_str());
    command.assert().success().stdout("").stderr("");
    assert_eq!(
        fs::read(repository.path().join(&path)).expect("raw path contents"),
        b"main\n"
    );
    assert_fsck(repository.path());
}
