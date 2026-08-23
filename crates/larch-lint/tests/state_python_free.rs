//! Regression coverage for the completed #7677 Python ownership boundary.

use crate::support;

use predicates::prelude::*;
use support::TempRepo;

const REGISTRY: &str = include_str!("../data/command-registry.toml");

fn prepare(repository: &TempRepo) {
    repository.write(
        "crates/larch-lint/data/command-registry.toml",
        REGISTRY.as_bytes(),
    );
    repository.write(
        "crates/larch-cli/src/session_closeout_commands.rs",
        b"pub struct SessionCloseout;\n",
    );
    repository.write(
        "crates/larch-cli/src/stall_recovery_commands.rs",
        b"pub struct StallRecovery;\n",
    );
    repository.write(
        "python/larch/cli.py",
        b"_REGISTRY = {('other', 'run'): ('other', 'main', False)}\n",
    );
}

#[test]
fn accepts_the_complete_rust_owned_boundary() {
    let repository = TempRepo::new();
    prepare(&repository);
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "state-python-free"])
        .assert()
        .success()
        .stdout("")
        .stderr("");
}

#[test]
fn rejects_pending_or_non_leaf_command_ownership() {
    let repository = TempRepo::new();
    prepare(&repository);
    let stale = REGISTRY
        .replace("migration_issue = 8068", "migration_issue = 7677")
        .replacen("owner = \"rust\"", "owner = \"python\"", 1);
    repository.write(
        "crates/larch-lint/data/command-registry.toml",
        stale.as_bytes(),
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "state-python-free"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "#7677 command must name an executable migration leaf",
        ))
        .stdout(predicate::str::contains("non-final #7677 command row"))
        .stderr("");
}

#[test]
fn rejects_python_dispatch_implementations_and_retired_tests() {
    let repository = TempRepo::new();
    prepare(&repository);
    repository.write(
        "python/larch/cli.py",
        b"_REGISTRY = {(\"session\", \"local-cleanup\"): (\"larch.state.session_env\", \"local_cleanup_main\", False)}\n",
    );
    repository.write(
        "python/larch/state/session_env.py",
        b"def local_cleanup_main():\n    pass\n",
    );
    repository.write("python/larch/state/stall_recovery.py", b"pass\n");
    repository.write("python/larch/state/bootstrap.py", b"pass\n");
    repository.write("python/larch/bgjob/unapproved.py", b"pass\n");
    repository.write("python/tests/state/test_old.py", b"pass\n");
    repository.write("python/tests/bgjob/test_old.py", b"pass\n");
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "state-python-free"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "completed #7677 command remains registered in Python",
        ))
        .stdout(predicate::str::contains(
            "superseded #7677 Python implementation remains",
        ))
        .stdout(predicate::str::contains(
            "superseded #7677 Python module returned",
        ))
        .stdout(predicate::str::contains(
            "unapproved Python state or background-job implementation",
        ))
        .stdout(predicate::str::contains(
            "python/larch/state/bootstrap.py:1: unapproved Python state or background-job implementation",
        ))
        .stdout(predicate::str::contains(
            "retired #7677 Python test surface returned",
        ))
        .stderr("");
}
