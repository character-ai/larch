use crate::support;

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

#[test]
fn import_forms_and_every_owned_environment_access_are_reported() {
    let repository = TempRepo::new();
    repository.write(
        "crates/larch-lint/policy/env_constants.rs",
        b"pub const ENV_SESSION: &str = \"SESSION_ID\";\npub const ENV_TOKEN: &str = \"TOKEN\";\n",
    );
    repository.write(
        "src/demo.rs",
        b"use std::env;\nuse std::env::{remove_var as unset, set_var, var as read};\nuse std::env::*;\n\nfn demo() {\n    let _ = env::var(\"SESSION_ID\");\n    let _ = read(\"SESSION_ID\");\n    let _ = var_os(\"TOKEN\");\n    set_var(\"TOKEN\", \"value\");\n    unset(\"TOKEN\");\n}\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "env-via-config-constant"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "bare environment literal \"SESSION_ID\" for ENV_SESSION access var occurrence 1",
        ))
        .stdout(predicate::str::contains(
            "bare environment literal \"SESSION_ID\" for ENV_SESSION access var occurrence 2",
        ))
        .stdout(predicate::str::contains(
            "bare environment literal \"TOKEN\" for ENV_TOKEN access var_os occurrence 3",
        ))
        .stdout(predicate::str::contains(
            "bare environment literal \"TOKEN\" for ENV_TOKEN access set_var occurrence 4",
        ))
        .stdout(predicate::str::contains(
            "bare environment literal \"TOKEN\" for ENV_TOKEN access remove_var occurrence 5",
        ))
        .stderr(predicate::str::is_empty());
}

#[test]
fn malformed_owned_constants_and_exemptions_fail_closed() {
    let duplicate = TempRepo::new();
    duplicate.write(
        "crates/larch-lint/policy/env_constants.rs",
        b"pub const ENV_ONE: &str = \"SESSION_ID\";\npub const ENV_TWO: &str = \"SESSION_ID\";\n",
    );
    duplicate.commit_all();
    TempRepo::command_from(duplicate.path())
        .args(["rule", "env-via-config-constant"])
        .assert()
        .code(2)
        .stdout(predicate::str::is_empty())
        .stderr(predicate::str::contains(
            "duplicate ENV_* values: SESSION_ID",
        ));

    for (contents, error) in [
        (b"{}".as_slice(), "exemptions must be a JSON array"),
        (
            b"[{\"file\":\"src/demo.rs\",\"reason\":\"\",\"env_name\":\"SESSION_ID\"}]".as_slice(),
            "exemption 0 has invalid reason",
        ),
        (
            b"[{\"file\":\"src/demo.rs\",\"reason\":\"legacy\",\"constant\":\"NOT_ENV\"}]"
                .as_slice(),
            "exemption 0 has invalid constant",
        ),
        (
            b"[{\"file\":\"src/demo.rs\",\"reason\":\"legacy\",\"unknown\":\"value\"}]".as_slice(),
            "exemption 0 has unknown key unknown",
        ),
    ] {
        let repository = TempRepo::new();
        repository.write(
            "crates/larch-lint/policy/env_constants.rs",
            b"pub const ENV_SESSION: &str = \"SESSION_ID\";\n",
        );
        repository.write(
            "crates/larch-lint/policy/env-via-config-constant-exemptions.json",
            contents,
        );
        repository.commit_all();
        TempRepo::command_from(repository.path())
            .args(["rule", "env-via-config-constant"])
            .assert()
            .code(2)
            .stdout(predicate::str::is_empty())
            .stderr(predicate::str::contains(error));
    }
}

#[test]
fn file_and_constant_scoped_exemptions_match_only_their_declared_surface() {
    let repository = TempRepo::new();
    repository.write(
        "crates/larch-lint/policy/env_constants.rs",
        b"pub const ENV_SESSION: &str = \"SESSION_ID\";\npub const ENV_TOKEN: &str = \"TOKEN\";\n",
    );
    repository.write(
        "crates/larch-lint/policy/env-via-config-constant-exemptions.json",
        br#"[{"file":"src/demo.rs","reason":"token bridge","constant":"ENV_TOKEN"}]"#,
    );
    repository.write(
        "src/demo.rs",
        b"fn demo() {\n    let _ = std::env::var(\"SESSION_ID\");\n    let _ = std::env::var(\"TOKEN\");\n}\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "env-via-config-constant"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains("SESSION_ID"))
        .stdout(predicate::str::contains("TOKEN").not())
        .stderr(predicate::str::is_empty());
}
