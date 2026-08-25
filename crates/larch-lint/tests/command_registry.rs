use crate::support;

use std::fs;

use predicates::prelude::*;
use support::TempRepo;

fn command_row(owner: &str, clean_install_test: Option<&str>) -> String {
    let clean_install = clean_install_test.map_or_else(String::new, |fixture| {
        format!("clean_install_test = \"{fixture}\"\n")
    });
    format!(
        "schema_version = 3\n\n[[commands]]\ndomain = \"fixture\"\nverb = \"run\"\nmachine_stdout = false\nowner = \"{owner}\"\nplanning_issue = 7661\nmigration_issue = 7661\n{clean_install}"
    )
}

fn prepare(repository: &TempRepo, registry: &str) {
    repository.write(
        "crates/larch-lint/data/command-registry.toml",
        registry.as_bytes(),
    );
    repository.write("hooks/hooks.json", b"{\"hooks\": {}}\n");
    repository.write(
        "crates/larch-cli/tests/clean_install.rs",
        b"const CLEAN_INSTALL_CASES: &[CleanInstallCase] = &[CleanInstallCase::new(\"clean-install-fixture-run\", \"fixture\", \"run\")];\n",
    );
}

#[test]
fn live_fixture_registry_is_clean_and_reports_rust_ownership() {
    let repository = TempRepo::new();
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "command-registry"])
        .assert()
        .success()
        .stdout("")
        .stderr("");

    TempRepo::command_from(repository.path())
        .args(["command-registry", "report"])
        .assert()
        .success()
        .stdout(predicate::str::contains("## Rust command registry"))
        .stdout(predicate::str::contains("| Registered commands | 1 |"))
        .stdout(predicate::str::contains("| Rust-owned commands | 1 |"))
        .stdout(predicate::str::contains("| Retired commands | 0 |"))
        .stdout(predicate::str::contains("| #7661 | 1 | 1 | 0 |"))
        .stderr("");
}

#[test]
fn old_schema_and_python_fields_fail_closed() {
    let old_schema = TempRepo::new();
    prepare(
        &old_schema,
        "schema_version = 2\n\n[[commands]]\ndomain = \"fixture\"\nverb = \"run\"\nmachine_stdout = false\nowner = \"rust\"\nplanning_issue = 7661\nmigration_issue = 7661\n",
    );
    old_schema.commit_all();
    TempRepo::command_from(old_schema.path())
        .args(["rule", "command-registry"])
        .assert()
        .code(2)
        .stderr(predicate::str::contains(
            "unsupported schema_version 2; expected 3",
        ));

    let python_field = TempRepo::new();
    let mut registry = command_row("rust", None);
    registry.push_str("python_module = \"fixture\"\n");
    prepare(&python_field, &registry);
    python_field.commit_all();
    TempRepo::command_from(python_field.path())
        .args(["rule", "command-registry"])
        .assert()
        .code(2)
        .stderr(predicate::str::contains("unknown field `python_module`"));
}

#[test]
fn duplicate_command_rows_fail_closed() {
    let repository = TempRepo::new();
    let mut registry = command_row("rust", None);
    let duplicate_row = command_row("rust", None);
    let (_, duplicate) = duplicate_row
        .split_once("[[commands]]")
        .expect("command marker");
    registry.push_str("\n[[commands]]");
    registry.push_str(duplicate);
    prepare(&repository, &registry);
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "command-registry"])
        .assert()
        .code(2)
        .stderr(predicate::str::contains(
            "duplicate ownership row for fixture run",
        ));
}

#[test]
fn sync_refreshes_only_the_rust_caller_inventory() {
    let repository = TempRepo::new();
    prepare(
        &repository,
        &command_row("rust", Some("clean-install-fixture-run")),
    );
    repository.write(
        "scripts/runtime.sh",
        b"\"${CLAUDE_PLUGIN_ROOT}/scripts/larch.sh\" fixture run\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["command-registry", "sync"])
        .assert()
        .success()
        .stdout(predicate::str::contains("COMMAND_REGISTRY_STATUS=synced"))
        .stdout(predicate::str::contains("CALLERS=1"))
        .stderr("");

    let registry = fs::read_to_string(
        repository
            .path()
            .join("crates/larch-lint/data/command-registry.toml"),
    )
    .expect("read synced registry");
    assert!(registry.contains("path = \"scripts/runtime.sh\""));
    assert!(registry.contains("rust = [\"fixture run\"]"));
    assert!(!registry.contains("python ="));
    assert!(!registry.contains("python_module"));

    repository.commit_all();
    TempRepo::command_from(repository.path())
        .args(["rule", "command-registry"])
        .assert()
        .success();
}

#[test]
fn caller_inventory_and_clean_install_coverage_are_enforced() {
    let repository = TempRepo::new();
    prepare(&repository, &command_row("rust", None));
    repository.write(
        "scripts/runtime.sh",
        b"\"${CLAUDE_PLUGIN_ROOT}/scripts/larch.sh\" fixture run\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "command-registry"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "production caller scripts/runtime.sh is missing from the ledger",
        ))
        .stdout(predicate::str::contains(
            "clean-install-coverage-missing fixture run",
        ));
}

#[test]
fn retired_commands_reject_live_callers() {
    let repository = TempRepo::new();
    let mut registry = command_row("retired", None);
    registry.push_str(
        "\n[[callers]]\npath = \"scripts/runtime.sh\"\nkind = \"script\"\nrust = [\"fixture run\"]\n",
    );
    prepare(&repository, &registry);
    repository.write(
        "scripts/runtime.sh",
        b"\"${CLAUDE_PLUGIN_ROOT}/scripts/larch.sh\" fixture run\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "command-registry"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "retired command fixture run has live callers: scripts/runtime.sh",
        ));
}

#[test]
fn migration_issue_audit_checks_registry_and_plan_evidence() {
    let repository = TempRepo::new();
    prepare(&repository, &command_row("rust", None));
    let audit_path = repository.path().join("audit.json");
    repository.write(
        "audit.json",
        br#"{"schema_version":1,"rollout_enabled":true,"issues":[{"number":7661,"state":"open","executable_leaf":true,"command":{"domain":"fixture","verb":"run"},"plan_commands":[]}]}"#,
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args([
            "command-registry",
            "audit",
            "--input",
            audit_path.to_str().expect("UTF-8 fixture path"),
        ])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "migration-issue-command-drift issue=#7661 command=fixture run",
        ));
}
