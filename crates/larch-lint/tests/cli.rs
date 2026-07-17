mod support;

use std::fs;

use predicates::prelude::*;
use support::TempRepo;

#[test]
fn all_resolves_root_from_a_nested_working_directory() {
    let repository = TempRepo::new();
    repository.write("tracked.md", b"tracked\n");
    repository.commit_all();
    let nested = repository.path().join("nested/workdir");
    fs::create_dir_all(&nested).expect("nested directory");

    TempRepo::command_from(nested)
        .arg("all")
        .assert()
        .success()
        .stdout(predicate::str::is_empty())
        .stderr(predicate::str::is_empty());
}

#[test]
fn rules_lists_the_empty_foundation_registry() {
    let repository = TempRepo::new();
    TempRepo::command_from(repository.path())
        .arg("rules")
        .assert()
        .success()
        .stdout(predicate::str::is_empty())
        .stderr(predicate::str::is_empty());
}

#[test]
fn unknown_rule_has_a_distinct_error_exit() {
    let repository = TempRepo::new();
    TempRepo::command_from(repository.path())
        .args(["rule", "missing"])
        .assert()
        .code(2)
        .stdout(predicate::str::is_empty())
        .stderr("larch-lint: error: unknown rule: missing\n");
}

#[test]
fn malformed_cli_input_has_the_error_exit() {
    let repository = TempRepo::new();
    TempRepo::command_from(repository.path())
        .arg("unknown-command")
        .assert()
        .code(2)
        .stderr("error: unrecognized subcommand\n");
}

#[test]
#[cfg(unix)]
fn tracked_symlink_fails_closed() {
    use std::os::unix::fs::symlink;

    let repository = TempRepo::new();
    repository.write("target.md", b"target\n");
    symlink("target.md", repository.path().join("link.md")).expect("fixture symlink");
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .arg("all")
        .assert()
        .code(2)
        .stderr("larch-lint: error: link.md: tracked symlinks are not supported\n");
}
