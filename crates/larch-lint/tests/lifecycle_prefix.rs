mod support;

use predicates::prelude::*;
use support::TempRepo;

#[test]
fn flags_a_lifecycle_prefix_comparison_in_rust_source() {
    let repository = TempRepo::new();
    repository.write(
        "src/lib.rs",
        b"pub fn check(state: &str) -> bool {\n    state == \"[DONE]\"\n}\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "lifecycle-prefix-literal"])
        .assert()
        .code(1)
        .stdout(
            "src/lib.rs:2: lifecycle-prefix literal [DONE] in comparison; \
             reference a shared lifecycle-prefix constant instead\n",
        )
        .stderr(predicate::str::is_empty());
}

#[test]
fn accepts_owner_definitions_and_reasoned_suppressions() {
    let repository = TempRepo::new();
    repository.write(
        "src/lib.rs",
        b"pub const DONE: &str = concat!(\"[DONE] \", \"x\");\n\
          pub fn check(state: &str) -> bool {\n    \
          state == \"[DONE]\" // lint-lifecycle-prefix: ok legacy compare\n}\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "lifecycle-prefix-literal"])
        .assert()
        .success()
        .stdout(predicate::str::is_empty())
        .stderr(predicate::str::is_empty());
}
