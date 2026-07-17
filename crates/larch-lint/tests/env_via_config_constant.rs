mod support;

use predicates::prelude::*;
use support::TempRepo;

#[test]
fn rejects_bare_owned_environment_literals() {
    let repository = TempRepo::new();
    repository.write(
        "crates/larch-lint/policy/env_constants.rs",
        b"pub const ENV_SESSION: &str = \"SESSION_ID\";\n",
    );
    repository.write(
        "src/demo.rs",
        b"fn demo() {\n    let _ = std::env::var(\"SESSION_ID\");\n}\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "env-via-config-constant"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "src/demo.rs:2: bare environment literal \"SESSION_ID\" for ENV_SESSION access var occurrence 1",
        ))
        .stderr(predicate::str::is_empty());
}

#[test]
fn allows_owner_constant_uses_and_suppressions() {
    let repository = TempRepo::new();
    repository.write(
        "crates/larch-lint/policy/env_constants.rs",
        b"pub const ENV_SESSION: &str = \"SESSION_ID\";\n",
    );
    repository.write(
        "src/demo.rs",
        b"const ENV_SESSION: &str = \"SESSION_ID\";\nfn demo() {\n    let _ = std::env::var(ENV_SESSION);\n    let _ = std::env::var(\"SESSION_ID\"); // lint-env-via-config-constant: ok fixture\n}\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "env-via-config-constant"])
        .assert()
        .success()
        .stdout(predicate::str::is_empty())
        .stderr(predicate::str::is_empty());
}

#[test]
fn owner_file_is_exempt_from_bare_literal_checks() {
    let repository = TempRepo::new();
    repository.write(
        "crates/larch-lint/policy/env_constants.rs",
        b"pub const ENV_SESSION: &str = \"SESSION_ID\";\nfn owner() { let _ = std::env::var(\"SESSION_ID\"); }\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "env-via-config-constant"])
        .assert()
        .success()
        .stdout(predicate::str::is_empty())
        .stderr(predicate::str::is_empty());
}

#[test]
fn scoped_exemptions_suppress_matching_findings() {
    let repository = TempRepo::new();
    repository.write(
        "crates/larch-lint/policy/env_constants.rs",
        b"pub const ENV_SESSION: &str = \"SESSION_ID\";\n",
    );
    repository.write(
        "crates/larch-lint/policy/env-via-config-constant-exemptions.json",
        br#"[{"file":"src/demo.rs","reason":"legacy bridge","env_name":"SESSION_ID","constant":"ENV_SESSION"}]"#,
    );
    repository.write(
        "src/demo.rs",
        b"fn demo() { let _ = std::env::set_var(\"SESSION_ID\", \"x\"); }\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "env-via-config-constant"])
        .assert()
        .success()
        .stdout(predicate::str::is_empty())
        .stderr(predicate::str::is_empty());
}
