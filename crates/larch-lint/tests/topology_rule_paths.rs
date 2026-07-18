mod support;

use std::fs;
use std::path::Path;

use assert_cmd::Command as AssertCommand;
use predicates::prelude::*;
use support::TempRepo;

fn run(repository: &TempRepo) -> assert_cmd::assert::Assert {
    TempRepo::command_from(repository.path())
        .args(["rule", "topology-rule-paths"])
        .assert()
}

fn write_topology(repository: &TempRepo, row: &[u8]) {
    repository.write("skills/shared/topology.tsv", row);
}

#[test]
fn accepts_a_tracked_authority_that_contains_its_value() {
    let repository = TempRepo::new();
    write_topology(
        &repository,
        b"# comment\n\nkey\tneedle\tcomposition\tskills/authority.md\n",
    );
    repository.write("skills/authority.md", b"contains needle\n");
    repository.commit_all();

    run(&repository)
        .success()
        .stdout(predicate::str::is_empty())
        .stderr(predicate::str::is_empty());
}

#[test]
fn reports_missing_untracked_and_noncontaining_authorities() {
    let missing = TempRepo::new();
    write_topology(&missing, b"key\tneedle\tcomposition\tskills/missing.md\n");
    missing.commit_all();
    run(&missing).code(1).stdout(predicate::str::contains(
        "skills/shared/topology.tsv:1: runtime_authority file does not exist: skills/missing.md",
    ));

    let untracked = TempRepo::new();
    write_topology(
        &untracked,
        b"key\tneedle\tcomposition\tskills/authority.md\n",
    );
    untracked.commit_all();
    untracked.write("skills/authority.md", b"contains needle\n");
    run(&untracked).code(1).stdout(predicate::str::contains(
        "runtime_authority is not tracked by git: skills/authority.md",
    ));

    let wrong_value = TempRepo::new();
    write_topology(
        &wrong_value,
        b"key\tneedle\tcomposition\tskills/authority.md\n",
    );
    wrong_value.write("skills/authority.md", b"wrong value\n");
    wrong_value.commit_all();
    run(&wrong_value).code(1).stdout(predicate::str::contains(
        "runtime_authority skills/authority.md does not contain value 'needle'",
    ));
}

#[test]
fn reports_tsv_and_path_grammar_failures() {
    let repository = TempRepo::new();
    write_topology(
        &repository,
        b"key\tneedle\tcomposition\tskills/authority.md\r\nmalformed\trow\tthree\nkey\tneedle\tcomposition\tskills/../escape.md\n",
    );
    repository.commit_all();

    run(&repository)
        .code(1)
        .stdout(predicate::str::contains(
            "CRLF line endings not allowed (use LF)",
        ))
        .stdout(predicate::str::contains(
            "malformed row; expected exactly four",
        ))
        .stdout(predicate::str::contains(
            "runtime_authority must not contain parent traversal",
        ));
}

#[test]
fn rejects_an_authority_that_resolves_outside_the_repository() {
    let repository = TempRepo::new();
    let outside = tempfile::NamedTempFile::new().expect("outside authority");
    fs::write(outside.path(), b"needle\n").expect("write outside authority");
    let link = repository.path().join("skills/authority.md");
    fs::create_dir_all(link.parent().expect("link parent")).expect("create link parent");
    std::os::unix::fs::symlink(outside.path(), &link).expect("create authority symlink");
    write_topology(
        &repository,
        b"key\tneedle\tcomposition\tskills/authority.md\n",
    );
    repository.commit_all();

    run(&repository).code(2).stderr(predicate::str::contains(
        "tracked symlinks are not supported",
    ));
}

#[test]
fn resolves_a_live_repository_from_a_non_root_working_directory() {
    let repository = TempRepo::new();
    write_topology(
        &repository,
        b"key\tneedle\tcomposition\tskills/authority.md\n",
    );
    repository.write("skills/authority.md", b"needle\n");
    repository.commit_all();
    let nested = repository.path().join("nested/workdir");
    fs::create_dir_all(&nested).expect("create nested working directory");

    TempRepo::command_from(nested)
        .args(["rule", "topology-rule-paths"])
        .assert()
        .success()
        .stdout(predicate::str::is_empty())
        .stderr(predicate::str::is_empty());
}

#[test]
fn validates_the_live_repository_from_a_non_root_working_directory() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let nested = root.join("crates/larch-lint/src");

    let mut command = AssertCommand::cargo_bin("larch-lint").expect("larch-lint binary");
    command
        .current_dir(nested)
        .args(["rule", "topology-rule-paths"])
        .assert()
        .success()
        .stdout(predicate::str::is_empty())
        .stderr(predicate::str::is_empty());
}
