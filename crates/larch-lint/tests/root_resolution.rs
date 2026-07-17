mod support;

use predicates::prelude::*;
use support::TempRepo;

#[test]
fn rejects_private_root_helpers_outside_the_owner() {
    let repository = TempRepo::new();
    repository.write(
        "src/demo.rs",
        b"fn _plugin_root() -> &'static str { \"/tmp\" }\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "root-resolution"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "src/demo.rs:1: private-plugin-root must use the repository-root owner (occurrence 1)",
        ))
        .stderr(predicate::str::is_empty());
}

#[test]
fn rejects_inline_git_toplevel_construction() {
    let repository = TempRepo::new();
    repository.write(
        "src/demo.rs",
        b"fn demo() {\n    let _ = [\"git\", \"rev-parse\", \"--show-toplevel\"];\n}\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "root-resolution"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "src/demo.rs:2: inline-git-toplevel must use the repository-root owner (occurrence 1)",
        ))
        .stderr(predicate::str::is_empty());
}

#[test]
fn exempts_the_repository_root_owner() {
    let repository = TempRepo::new();
    repository.write(
        "crates/larch-lint/src/repository.rs",
        b"fn probe() {\n    let _ = [\"rev-parse\", \"--show-toplevel\"];\n    fn _plugin_root() {}\n}\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "root-resolution"])
        .assert()
        .success()
        .stdout(predicate::str::is_empty())
        .stderr(predicate::str::is_empty());
}
