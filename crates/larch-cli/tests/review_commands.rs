use std::{fs, path::Path, process::Command};

use assert_cmd::Command as AssertCommand;
use predicates::prelude::*;
use tempfile::TempDir;

const GATHER_CONTEXT_USAGE: &str = "Usage: review gather-context --mode diff|description --output-dir DIR [--description-text TEXT --scope-files FILE]";

fn larch() -> AssertCommand {
    AssertCommand::cargo_bin("larch").expect("larch binary should build")
}

fn write(path: &Path, contents: &str) {
    let parent = path.parent().expect("fixture path has parent");
    fs::create_dir_all(parent).expect("create fixture parent");
    fs::write(path, contents).expect("write fixture");
}

fn git(repository: &Path, arguments: &[&str]) {
    let output = Command::new("git")
        .args(arguments)
        .current_dir(repository)
        .output()
        .expect("run fixture git");
    assert!(
        output.status.success(),
        "git {arguments:?} failed: {}",
        String::from_utf8_lossy(&output.stderr)
    );
}

fn commit(repository: &Path, path: &str, contents: &str, message: &str) {
    write(&repository.join(path), contents);
    git(repository, &["add", path]);
    git(repository, &["commit", "-m", message]);
}

fn repository(fixture: &TempDir) -> std::path::PathBuf {
    let repository = fixture.path().join("repository");
    fs::create_dir(&repository).expect("repository dir");
    git(&repository, &["init", "-b", "main"]);
    git(&repository, &["config", "user.email", "test@example.com"]);
    git(&repository, &["config", "user.name", "Test User"]);
    repository
}

fn ripgrep_path(fixture: &TempDir) -> std::path::PathBuf {
    let directory = fixture.path().join("bin");
    let executable = if cfg!(windows) { "rg.exe" } else { "rg" };
    let path = directory.join(executable);
    write(&path, "");
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt as _;

        fs::set_permissions(&path, fs::Permissions::from_mode(0o755)).expect("make rg executable");
    }
    directory
}

#[test]
fn gather_context_preserves_description_rows_and_content_fallback() {
    let fixture = TempDir::new().expect("fixture");
    let repository = repository(&fixture);
    commit(
        &repository,
        "docs/notes.txt",
        "A UNIQUE FULL PHRASE appears only in this file.\n",
        "base",
    );
    write(
        &repository.join("untracked.txt"),
        "A UNIQUE FULL PHRASE appears only in this file.\n",
    );
    let output = fixture.path().join("context");
    let path = ripgrep_path(&fixture);

    larch()
        .current_dir(&repository)
        .env("PATH", path)
        .args([
            "review",
            "gather-context",
            "--mode",
            "description",
            "--description-text",
            "unique full phrase",
            "--output-dir",
        ])
        .arg(&output)
        .assert()
        .success()
        .stdout(format!(
            "DIFF_FILE=\nFILE_LIST_FILE={}\nCOMMIT_LOG_FILE=\nCOMMIT_COUNT=0\nSCOPE_FILES_COUNT=2\nMODE=description\n",
            output.join("scope-files.txt").display(),
        ));
    assert_eq!(
        fs::read_to_string(output.join("scope-files.txt")).expect("scope file"),
        "docs/notes.txt\nuntracked.txt\n"
    );
}

#[test]
fn gather_context_does_not_treat_untracked_names_as_git_ls_files_matches() {
    let fixture = TempDir::new().expect("fixture");
    let repository = repository(&fixture);
    commit(&repository, "README.md", "base\n", "base");
    write(
        &repository.join("untracked-matching-token.txt"),
        "This file does not contain the full phrase.\n",
    );
    let output = fixture.path().join("context");

    larch()
        .current_dir(&repository)
        .args([
            "review",
            "gather-context",
            "--mode",
            "description",
            "--description-text",
            "matching token",
            "--output-dir",
        ])
        .arg(&output)
        .assert()
        .success()
        .stdout(format!(
            "DIFF_FILE=\nFILE_LIST_FILE={}\nCOMMIT_LOG_FILE=\nCOMMIT_COUNT=0\nSCOPE_FILES_COUNT=0\nMODE=description\n",
            output.join("scope-files.txt").display(),
        ));
    assert_eq!(
        fs::read_to_string(output.join("scope-files.txt")).expect("scope file"),
        ""
    );
}

#[test]
fn gather_context_keeps_the_legacy_no_ripgrep_fallback() {
    let fixture = TempDir::new().expect("fixture");
    let repository = repository(&fixture);
    commit(
        &repository,
        "docs/notes.txt",
        "A UNIQUE FULL PHRASE appears only in this file.\n",
        "base",
    );
    let output = fixture.path().join("context");

    larch()
        .current_dir(&repository)
        .env("PATH", "")
        .args([
            "review",
            "gather-context",
            "--mode",
            "description",
            "--description-text",
            "unique full phrase",
            "--output-dir",
        ])
        .arg(&output)
        .assert()
        .success()
        .stdout(format!(
            "DIFF_FILE=\nFILE_LIST_FILE={}\nCOMMIT_LOG_FILE=\nCOMMIT_COUNT=0\nSCOPE_FILES_COUNT=0\nMODE=description\n",
            output.join("scope-files.txt").display(),
        ));
}

#[test]
fn gather_context_uses_the_current_subdirectory_as_the_legacy_search_root() {
    let fixture = TempDir::new().expect("fixture");
    let repository = repository(&fixture);
    commit(
        &repository,
        "nested/notes.txt",
        "A UNIQUE NESTED PHRASE appears only here.\n",
        "base",
    );
    let output = fixture.path().join("context");
    let path = ripgrep_path(&fixture);

    larch()
        .current_dir(repository.join("nested"))
        .env("PATH", path)
        .args([
            "review",
            "gather-context",
            "--mode",
            "description",
            "--description-text",
            "unique nested phrase",
            "--output-dir",
        ])
        .arg(&output)
        .assert()
        .success();
    assert_eq!(
        fs::read_to_string(output.join("scope-files.txt")).expect("scope file"),
        "notes.txt\n"
    );
}

#[test]
fn gather_context_reuses_branch_collector_and_writes_legacy_sidecar() {
    let fixture = TempDir::new().expect("fixture");
    let repository = repository(&fixture);
    commit(&repository, "src/main.rs", "baseline\n", "base");
    git(&repository, &["checkout", "-b", "feature"]);
    let marker = "REVIEW_GATHER_CONTEXT_MARKER";
    commit(
        &repository,
        "src/main.rs",
        &format!("baseline\n{marker}\n"),
        "feature change",
    );
    let output = fixture.path().join("context");

    larch()
        .current_dir(&repository)
        .args(["review", "gather-context", "--mode", "diff", "--output-dir"])
        .arg(&output)
        .assert()
        .success()
        .stdout(format!(
            "DIFF_FILE={}\nFILE_LIST_FILE={}\nCOMMIT_LOG_FILE={}\nCOMMIT_COUNT=1\nSCOPE_FILES_COUNT=0\nMODE=diff\n",
            output.join("diff.txt").display(),
            output.join("file-list.txt").display(),
            output.join("commit-log.txt").display(),
        ));
    assert!(
        fs::read_to_string(output.join("diff.txt"))
            .expect("diff")
            .contains(marker)
    );
    assert_eq!(
        fs::read_to_string(output.join("gather-branch-context.env")).expect("sidecar"),
        format!(
            "DIFF_FILE={}\nFILE_LIST_FILE={}\nCOMMIT_LOG_FILE={}\nCOMMIT_COUNT=1\n",
            output.join("diff.txt").display(),
            output.join("file-list.txt").display(),
            output.join("commit-log.txt").display(),
        )
    );
}

#[test]
fn gather_context_preserves_diff_failure_rows_and_sidecar() {
    let fixture = TempDir::new().expect("fixture");
    let output = fixture.path().join("context");

    larch()
        .current_dir(fixture.path())
        .args(["review", "gather-context", "--mode", "diff", "--output-dir"])
        .arg(&output)
        .assert()
        .failure()
        .stdout("SCOPE_FILES_COUNT=0\nMODE=diff\n")
        .stderr("gather-branch-context.sh: cannot open repository\n");
    assert_eq!(
        fs::read_to_string(output.join("gather-branch-context.env")).expect("sidecar"),
        ""
    );
}

#[test]
fn gather_context_preserves_legacy_help_and_argument_failures() {
    larch()
        .args(["review", "gather-context", "--help"])
        .assert()
        .success()
        .stdout("")
        .stderr(format!("{GATHER_CONTEXT_USAGE}\n"));
    larch()
        .args(["review", "gather-context", "--unknown"])
        .assert()
        .code(2)
        .stderr(format!("unknown option: --unknown{GATHER_CONTEXT_USAGE}\n"));
    larch()
        .args(["review", "gather-context", "--mode"])
        .assert()
        .code(2)
        .stderr(format!("--mode requires a value{GATHER_CONTEXT_USAGE}\n"));
    larch()
        .args([
            "review",
            "gather-context",
            "--mode",
            "unsupported",
            "--output-dir",
            ".",
        ])
        .assert()
        .code(2)
        .stderr(predicate::eq(
            "review gather-context: --mode must be diff or description\n",
        ));
}
