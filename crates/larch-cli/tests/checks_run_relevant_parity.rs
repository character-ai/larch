//! Black-box parity coverage for the Rust `checks run-relevant` and
//! `checks contains-pins` commands (#8616). Each case drives the real binary
//! and pins the `KEY=value` stdout grammar, the diagnostic stderr, and the
//! exit codes the retired Python entrypoints produced.

use std::{fs, os::unix::fs::PermissionsExt as _, path::Path};

use assert_cmd::Command as AssertCommand;
use tempfile::TempDir;

const RUN_RELEVANT_HELP: &str = "usage: cli.py checks run-relevant [-h] --site SITE [--tmpdir TMPDIR]\n                                  [--repo-root REPO_ROOT] [--allow-skip]\n\noptions:\n  -h, --help            show this help message and exit\n  --site SITE\n  --tmpdir TMPDIR\n  --repo-root REPO_ROOT\n  --allow-skip\n";

const CONTAINS_PINS_HELP: &str = "usage: cli.py checks contains-pins [-h] [--changed-files CHANGED_FILES]\n                                   [--repo-root REPO_ROOT]\n\noptions:\n  -h, --help            show this help message and exit\n  --changed-files CHANGED_FILES\n  --repo-root REPO_ROOT\n";

fn larch() -> AssertCommand {
    AssertCommand::cargo_bin("larch").expect("larch binary")
}

#[test]
fn run_relevant_help_matches_argparse() {
    larch()
        .args(["checks", "run-relevant", "--help"])
        .assert()
        .success()
        .stdout(RUN_RELEVANT_HELP);
}

#[test]
fn run_relevant_missing_site_is_a_usage_error() {
    larch()
        .args(["checks", "run-relevant"])
        .assert()
        .code(2)
        .stderr(predicates::str::contains(
            "cli.py checks run-relevant: error: the following arguments are required: --site",
        ));
}

#[test]
fn run_relevant_rejects_an_invalid_site() {
    larch()
        .args([
            "checks",
            "run-relevant",
            "--site",
            "../bad",
            "--tmpdir",
            "/larch-clean-install-missing",
        ])
        .assert()
        .code(2)
        .stdout("STATUS=fail FAILURE_REASON=site-validation\n");
}

#[test]
fn run_relevant_rejects_an_unvalidated_tmpdir() {
    larch()
        .args([
            "checks",
            "run-relevant",
            "--site",
            "step3",
            "--tmpdir",
            "/larch-clean-install-missing",
            "--repo-root",
            ".",
        ])
        .assert()
        .code(2)
        .stdout("STATUS=fail FAILURE_REASON=tmpdir-validation\n");
}

#[test]
fn contains_pins_help_matches_argparse() {
    larch()
        .args(["checks", "contains-pins", "--help"])
        .assert()
        .success()
        .stdout(CONTAINS_PINS_HELP);
}

#[test]
fn contains_pins_rejects_a_non_directory_repo_root() {
    larch()
        .args([
            "checks",
            "contains-pins",
            "--repo-root",
            "/larch-clean-install-not-a-dir",
        ])
        .assert()
        .code(2)
        .stderr(predicates::str::contains(
            "ERROR: --repo-root is not a directory:",
        ));
}

/// Build a repo whose `scripts/test-*.sh` pins one present and one absent
/// literal, exercising the DEFECT stdout line and the exit-1 contract.
fn pinned_repo() -> TempDir {
    let root = TempDir::new().expect("temp repo");
    let scripts = root.path().join("scripts");
    fs::create_dir_all(&scripts).expect("scripts dir");
    fs::write(root.path().join("target.txt"), "present literal\n").expect("target");
    fs::write(
        scripts.join("test-present.sh"),
        "TARGET=\"$REPO_ROOT/target.txt\"\ncontains \"$TARGET\" \"present literal\" \"ok\"\n",
    )
    .expect("present script");
    fs::write(
        scripts.join("test-absent.sh"),
        "TARGET=\"$REPO_ROOT/target.txt\"\ncontains \"$TARGET\" \"absent literal\" \"ok\"\n",
    )
    .expect("absent script");
    for entry in ["test-present.sh", "test-absent.sh"] {
        fs::set_permissions(scripts.join(entry), fs::Permissions::from_mode(0o755))
            .expect("chmod script");
    }
    root
}

#[test]
fn contains_pins_reports_present_and_absent_literals() {
    let repo = pinned_repo();
    let repo_root = fs::canonicalize(repo.path()).expect("canonical repo");
    larch()
        .args(["checks", "contains-pins", "--repo-root"])
        .arg(&repo_root)
        .assert()
        .code(1)
        .stdout(predicates::str::contains("DEFECTS=1"))
        .stdout(predicates::str::contains(
            "DEFECT: scripts/test-absent.sh:2: literal 'absent literal' not found in target.txt",
        ));
}

#[test]
fn contains_pins_all_present_reports_no_defects() {
    let repo = TempDir::new().expect("temp repo");
    let repo_root: &Path = repo.path();
    let scripts = repo_root.join("scripts");
    fs::create_dir_all(&scripts).expect("scripts dir");
    fs::write(repo_root.join("target.txt"), "present literal\n").expect("target");
    fs::write(
        scripts.join("test-present.sh"),
        "TARGET=\"$REPO_ROOT/target.txt\"\ncontains \"$TARGET\" \"present literal\" \"ok\"\n",
    )
    .expect("present script");
    let canonical = fs::canonicalize(repo_root).expect("canonical repo");
    larch()
        .args(["checks", "contains-pins", "--repo-root"])
        .arg(&canonical)
        .assert()
        .success()
        .stdout("DEFECTS=0\n");
}
