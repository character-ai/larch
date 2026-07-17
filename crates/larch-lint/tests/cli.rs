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
fn rules_lists_registered_rules_in_name_order() {
    let repository = TempRepo::new();
    TempRepo::command_from(repository.path())
        .arg("rules")
        .assert()
        .success()
        .stdout(predicate::str::contains(
            "fixture\tValidate decentralized rule registration\n",
        ))
        .stdout(predicate::str::contains(
            "kv-codec\tReject ad-hoc KEY=value readers and emitters outside shared codec owners\n",
        ))
        .stdout(predicate::str::contains(
            "result-env-key-parity\tReject divergent key sets across sibling writers of the same result-env basename\n",
        ))
        .stderr(predicate::str::is_empty());
}

#[test]
fn fixture_rule_is_discovered_without_a_central_registry_edit() {
    let repository = TempRepo::new();
    repository.write("fixtures/demo.fixture", b"allowed\nforbidden\n");
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .arg("all")
        .assert()
        .code(1)
        .stdout("fixtures/demo.fixture:2: fixture violation\n")
        .stderr(predicate::str::is_empty());
}

#[test]
fn migration_ledger_rejects_missing_duplicate_and_stale_records() {
    let missing = TempRepo::new();
    fs::remove_file(
        missing
            .path()
            .join("crates/larch-lint/migration-ledger/fixture.toml"),
    )
    .expect("remove default ledger");
    missing.write("tracked.md", b"tracked\n");
    missing.commit_all();
    TempRepo::command_from(missing.path())
        .arg("all")
        .assert()
        .code(2)
        .stderr("larch-lint: error: missing migration-ledger record: crates/larch-lint/migration-ledger/fixture.toml\n");

    let duplicate = TempRepo::new();
    duplicate.write(
        "crates/larch-lint/migration-ledger/fixture-copy.toml",
        b"rule = \"fixture\"\n",
    );
    duplicate.commit_all();
    TempRepo::command_from(duplicate.path())
        .arg("all")
        .assert()
        .code(2)
        .stderr("larch-lint: error: duplicate migration-ledger rule record: fixture\n");

    let stale = TempRepo::new();
    stale.write(
        "crates/larch-lint/migration-ledger/obsolete.toml",
        b"rule = \"obsolete\"\n",
    );
    stale.commit_all();
    TempRepo::command_from(stale.path())
        .arg("all")
        .assert()
        .code(2)
        .stderr("larch-lint: error: stale migration-ledger rule record: obsolete\n");
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
fn kv_codec_and_result_env_rules_are_clean_on_empty_rust_corpus() {
    let repository = TempRepo::new();
    repository.write("crates/demo/src/lib.rs", b"pub fn ok() {}\n");
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "kv-codec"])
        .assert()
        .success()
        .stdout(predicate::str::is_empty());
    TempRepo::command_from(repository.path())
        .args(["rule", "result-env-key-parity"])
        .assert()
        .success()
        .stdout(predicate::str::is_empty());
}

#[test]
fn kv_codec_reports_ad_hoc_split() {
    let repository = TempRepo::new();
    repository.write(
        "crates/demo/src/lib.rs",
        b"fn parse(line: &str) {\n    let _ = line.split_once('=');\n}\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "kv-codec"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "crates/demo/src/lib.rs:2: ad-hoc KEY=value split",
        ));
}

#[test]
fn result_env_key_parity_reports_divergent_siblings() {
    let repository = TempRepo::new();
    repository.write(
        "crates/a/src/lib.rs",
        b"fn emit() {\n    write_result_env(\"slot.env\", [(\"A\", \"1\"), (\"B\", \"2\")]);\n}\n",
    );
    repository.write(
        "crates/b/src/lib.rs",
        b"fn emit() {\n    write_result_env(\"slot.env\", [(\"A\", \"1\")]);\n}\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "result-env-key-parity"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "slot.env writer missing key B present in sibling writers",
        ));
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
