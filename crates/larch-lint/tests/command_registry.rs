mod support;

use std::fs;

use predicates::prelude::*;
use support::TempRepo;

const PYTHON_SOURCE: &[u8] = b"_REGISTRY: dict[tuple[str, str], tuple[str, str, bool]] = {\n    (\"fixture\", \"run\"): (\"fixture\", \"main\", False),\n}\n";

fn command_row(owner: &str, parity: &str, cutover: &str, removal: &str) -> String {
    format!(
        "schema_version = 1\n\n[[commands]]\ndomain = \"fixture\"\nverb = \"run\"\npython_module = \"fixture\"\npython_function = \"main\"\nmachine_stdout = false\nowner = \"{owner}\"\nimplementation_parity = \"{parity}\"\nconsumer_cutover = \"{cutover}\"\npython_removal = \"{removal}\"\nmigration_issue = 7661\n"
    )
}

fn prepare(repository: &TempRepo, ledger: &str) {
    repository.write("python/larch/cli.py", PYTHON_SOURCE);
    repository.write(
        "crates/larch-lint/data/command-registry.toml",
        ledger.as_bytes(),
    );
    repository.write("hooks/hooks.json", b"{\"hooks\": {}}\n");
}

#[test]
fn live_fixture_registry_is_clean_and_reports_separate_milestones() {
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
        .stdout(predicate::str::contains(
            "| Implementation parity | 0 | 1 |",
        ))
        .stdout(predicate::str::contains("| Consumer cutover | 0 | 1 |"))
        .stdout(predicate::str::contains("| Python removal | 0 | 1 |"))
        .stdout(predicate::str::contains("| #7661 | 1 | 0 | 0 |"))
        .stderr("");
}

#[test]
fn missing_and_duplicate_command_rows_fail_closed() {
    let missing = TempRepo::new();
    prepare(&missing, "schema_version = 1\n");
    missing.commit_all();
    TempRepo::command_from(missing.path())
        .args(["rule", "command-registry"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "Python registry command fixture run is missing from the ownership ledger",
        ))
        .stderr("");

    let duplicate = TempRepo::new();
    let row = command_row("python", "pending", "pending", "pending");
    let duplicate_row = row
        .split_once("[[commands]]")
        .expect("command row marker")
        .1;
    prepare(&duplicate, &format!("{row}\n[[commands]]{duplicate_row}"));
    duplicate.commit_all();
    TempRepo::command_from(duplicate.path())
        .args(["command-registry", "sync", "--migration-issue", "7661"])
        .assert()
        .code(2)
        .stdout("")
        .stderr(predicate::str::contains(
            "duplicate ownership row for fixture run",
        ));
    TempRepo::command_from(duplicate.path())
        .args(["rule", "command-registry"])
        .assert()
        .code(2)
        .stdout("")
        .stderr(predicate::str::contains(
            "duplicate ownership row for fixture run",
        ));
}

#[test]
fn rust_cutover_is_rejected_while_a_python_caller_remains() {
    let repository = TempRepo::new();
    let mut ledger = command_row("rust", "complete", "complete", "pending");
    ledger.push_str(
        "\n[[callers]]\npath = \"skills/example/SKILL.md\"\nkind = \"skill\"\npython = [\"fixture run\"]\nrust = []\n",
    );
    prepare(&repository, &ledger);
    repository.write(
        "skills/example/SKILL.md",
        b"python3 python/cli.py fixture run\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "command-registry"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "fixture run cannot cut over to Rust while legacy callers remain: skills/example/SKILL.md",
        ))
        .stderr("");

    TempRepo::command_from(repository.path())
        .args(["command-registry", "report"])
        .assert()
        .code(2)
        .stdout("")
        .stderr(predicate::str::contains(
            "cannot render progress from an invalid command registry",
        ));
}

#[test]
fn caller_inventory_drift_is_reported() {
    let repository = TempRepo::new();
    prepare(
        &repository,
        &command_row("python", "pending", "pending", "pending"),
    );
    repository.write("scripts/runtime.sh", b"python3 python/cli.py fixture run\n");
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "command-registry"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "production caller scripts/runtime.sh is missing from the ledger",
        ))
        .stderr("");
}

#[test]
fn caller_inventory_recognizes_the_verified_runtime_entrypoint() {
    let repository = TempRepo::new();
    prepare(
        &repository,
        &command_row("python", "pending", "pending", "pending"),
    );
    repository.write(
        "skills/example/SKILL.md",
        b"\"${CLAUDE_PLUGIN_ROOT}/scripts/larch.sh\" fixture run\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["command-registry", "sync", "--migration-issue", "7661"])
        .assert()
        .success()
        .stdout("COMMAND_REGISTRY_STATUS=synced\nCOMMANDS=1\nCALLERS=1\n")
        .stderr("");

    let ledger = fs::read_to_string(
        repository
            .path()
            .join("crates/larch-lint/data/command-registry.toml"),
    )
    .expect("read synced registry");
    assert!(ledger.contains("path = \"skills/example/SKILL.md\""));
    assert!(ledger.contains("python = []"));
    assert!(ledger.contains("rust = [\"fixture run\"]"));
}

#[test]
fn sync_refreshes_callers_and_preserves_human_migration_state() {
    let repository = TempRepo::new();
    prepare(
        &repository,
        &command_row("python", "complete", "pending", "pending"),
    );
    repository.write("scripts/runtime.sh", b"python3 python/cli.py fixture run\n");
    repository.write(
        ".github/workflows/ci.yaml",
        b"run: python3 python/cli.py fixture missing; python3 python/cli.py fixture run\n",
    );
    repository.write(
        "hooks/hooks.json",
        b"{\"hooks\": {\"SessionStart\": [{\"hooks\": [{\"command\": \"${CLAUDE_PLUGIN_ROOT}/scripts/runtime.sh\"}]}]}}\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["command-registry", "sync", "--migration-issue", "9999"])
        .assert()
        .success()
        .stdout("COMMAND_REGISTRY_STATUS=synced\nCOMMANDS=1\nCALLERS=2\n")
        .stderr("");

    let ledger = fs::read_to_string(
        repository
            .path()
            .join("crates/larch-lint/data/command-registry.toml"),
    )
    .expect("read synced registry");
    assert!(ledger.contains("implementation_parity = \"complete\""));
    assert!(ledger.contains("migration_issue = 7661"));
    assert!(ledger.contains("path = \"scripts/runtime.sh\""));
    assert!(ledger.contains("kind = \"hook\""));
    assert!(ledger.contains("path = \".github/workflows/ci.yaml\""));
    assert!(ledger.contains("kind = \"ci\""));

    TempRepo::command_from(repository.path())
        .args(["rule", "command-registry"])
        .assert()
        .success()
        .stdout("")
        .stderr("");
}
