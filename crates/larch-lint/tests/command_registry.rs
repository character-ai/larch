mod support;

use std::fs;

use predicates::prelude::*;
use support::TempRepo;

const PYTHON_SOURCE: &[u8] = b"_REGISTRY: dict[tuple[str, str], tuple[str, str, bool]] = {\n    (\"fixture\", \"run\"): (\"fixture\", \"main\", False),\n}\n";

fn command_row(owner: &str, parity: &str, cutover: &str, removal: &str) -> String {
    command_row_for(
        "fixture", "run", "fixture", "main", owner, parity, cutover, removal,
    )
}

#[allow(clippy::too_many_arguments)] // Test rows expose each registry field explicitly.
fn command_row_for(
    domain: &str,
    verb: &str,
    module: &str,
    function: &str,
    owner: &str,
    parity: &str,
    cutover: &str,
    removal: &str,
) -> String {
    format!(
        "schema_version = 2\n\n[[commands]]\ndomain = \"{domain}\"\nverb = \"{verb}\"\npython_module = \"{module}\"\npython_function = \"{function}\"\nmachine_stdout = false\nowner = \"{owner}\"\nimplementation_parity = \"{parity}\"\nconsumer_cutover = \"{cutover}\"\npython_removal = \"{removal}\"\nplanning_issue = 7661\nmigration_issue = 7661\n"
    )
}

fn append_command(ledger: &mut String, row: &str) {
    let (_, command) = row.split_once("[[commands]]").expect("command row marker");
    ledger.push_str("\n[[commands]]");
    ledger.push_str(command);
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
        .stdout(predicate::str::contains(
            "| Exact migration-leaf assignments | 1 | 1 |",
        ))
        .stdout(predicate::str::contains("| #7661 | 1 | 0 | 0 |"))
        .stderr("");
}

#[test]
fn missing_and_duplicate_command_rows_fail_closed() {
    let missing = TempRepo::new();
    prepare(&missing, "schema_version = 2\n");
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
        .args(["command-registry", "sync", "--planning-issue", "7661"])
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
fn sync_assigns_only_planning_ownership_to_a_new_python_command() {
    let repository = TempRepo::new();
    prepare(&repository, "schema_version = 2\n");
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["command-registry", "sync", "--planning-issue", "7682"])
        .assert()
        .success()
        .stdout("COMMAND_REGISTRY_STATUS=synced\nCOMMANDS=1\nCALLERS=0\n");

    let ledger = fs::read_to_string(
        repository
            .path()
            .join("crates/larch-lint/data/command-registry.toml"),
    )
    .expect("read synced registry");
    assert!(ledger.contains("planning_issue = 7682"));
    assert!(!ledger.contains("migration_issue ="));
}

#[test]
fn chief_umbrella_migration_ownership_fails_closed() {
    let repository = TempRepo::new();
    let ledger = command_row("python", "pending", "pending", "pending")
        .replace("planning_issue = 7661", "planning_issue = 7687");
    prepare(&repository, &ledger);
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "command-registry"])
        .assert()
        .code(2)
        .stdout("")
        .stderr(predicate::str::contains(
            "fixture run delegates planning ownership to chief umbrella #7687",
        ));
}

#[test]
fn planning_umbrella_is_not_accepted_as_an_atomic_migration_leaf() {
    let repository = TempRepo::new();
    let ledger = command_row("python", "pending", "pending", "pending")
        .replace("migration_issue = 7661", "migration_issue = 7682");
    prepare(&repository, &ledger);
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "command-registry"])
        .assert()
        .code(2)
        .stderr(predicate::str::contains(
            "fixture run assigns atomic migration ownership to umbrella #7682",
        ));
}

#[test]
fn pending_python_command_may_leave_atomic_migration_unassigned() {
    let repository = TempRepo::new();
    let ledger = command_row("python", "pending", "pending", "pending")
        .replace("migration_issue = 7661\n", "");
    prepare(&repository, &ledger);
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "command-registry"])
        .assert()
        .success();
}

#[test]
fn progress_groups_by_planning_owner_not_exact_leaf() {
    let repository = TempRepo::new();
    let ledger = command_row("python", "pending", "pending", "pending")
        .replace("planning_issue = 7661", "planning_issue = 7675")
        .replace("migration_issue = 7661", "migration_issue = 7734");
    prepare(&repository, &ledger);
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["command-registry", "report"])
        .assert()
        .success()
        .stdout(predicate::str::contains("| #7675 | 1 | 0 | 0 |"))
        .stdout(predicate::str::contains("| #7734 |").not());
}

#[test]
fn completed_migration_requires_an_exact_leaf() {
    let repository = TempRepo::new();
    let ledger = command_row("rust", "complete", "complete", "complete")
        .replace("migration_issue = 7661\n", "");
    prepare(&repository, &ledger);
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "command-registry"])
        .assert()
        .code(2)
        .stderr(predicate::str::contains(
            "fixture run completed migration state without an exact migration leaf",
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
        .args(["command-registry", "sync", "--planning-issue", "7661"])
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
        .args(["command-registry", "sync", "--planning-issue", "9999"])
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
    assert!(ledger.contains("planning_issue = 7661"));
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

#[test]
fn sync_inventories_every_caller_kind_and_shared_python_entrypoint() {
    let repository = TempRepo::new();
    prepare(
        &repository,
        &command_row("python", "pending", "pending", "pending"),
    );
    repository.write(
        "skills/example/SKILL.md",
        b"python3 python/cli.py fixture run\n",
    );
    repository.write("scripts/runtime.sh", b"python3 python/cli.py fixture run\n");
    repository.write(
        "scripts/standalone.sh",
        b"python3 python/cli.py fixture run\n",
    );
    repository.write(
        ".github/workflows/ci.yaml",
        b"run: python3 python/cli.py fixture run\n",
    );
    repository.write("agents/example.md", b"python3 python/cli.py fixture run\n");
    repository.write(
        ".claude/agents/private.md",
        b"python3 python/cli.py fixture run\n",
    );
    repository.write(
        "hooks/hooks.json",
        b"{\"hooks\": {\"SessionStart\": [{\"hooks\": [{\"command\": \"${CLAUDE_PLUGIN_ROOT}/scripts/runtime.sh\"}]}]}}\n",
    );
    repository.write(
        "python/larch/runtime.py",
        br#"from larch.core import repo_roots as roots
from larch.core.repo_roots import larch_entrypoint as resolve_larch

ENTRY = resolve_larch()
COMMAND = [str(ENTRY), "fixture", "run"]
MODULE_ALIAS = [str(roots.larch_entrypoint()), "fixture", "run"]
VERB = "run"
DYNAMIC = [str(ENTRY), "fixture", VERB]
DIRECT = ["scripts/larch.sh", "fixture", "run"]
"#,
    );
    repository.write(
        "python/larch/false_positive.py",
        b"TEXT = \"scripts/larch.sh fixture run\"\n# [\"scripts/larch.sh\", \"fixture\", \"run\"]\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["command-registry", "sync", "--planning-issue", "7661"])
        .assert()
        .success()
        .stdout("COMMAND_REGISTRY_STATUS=synced\nCOMMANDS=1\nCALLERS=7\n")
        .stderr("");

    let ledger = fs::read_to_string(
        repository
            .path()
            .join("crates/larch-lint/data/command-registry.toml"),
    )
    .expect("read synced registry");
    for kind in ["skill", "hook", "script", "ci", "agent", "python-runtime"] {
        assert!(
            ledger.contains(&format!("kind = \"{kind}\"")),
            "missing {kind}"
        );
    }
    assert!(ledger.contains("path = \".claude/agents/private.md\""));
    assert!(ledger.contains("path = \"python/larch/runtime.py\""));
    assert!(ledger.contains("rust = [\"fixture *\", \"fixture run\"]"));
    assert!(!ledger.contains("path = \"python/larch/false_positive.py\""));
}

#[test]
fn sync_inventories_issue_equivalents_and_preserves_pure_tracking_helpers() {
    let repository = TempRepo::new();
    let mut ledger = command_row("python", "pending", "pending", "pending");
    append_command(
        &mut ledger,
        &command_row_for(
            "tracking-issue",
            "rename",
            "larch.issue.tracking_issue",
            "rename_main",
            "rust",
            "complete",
            "complete",
            "complete",
        ),
    );
    append_command(
        &mut ledger,
        &command_row_for(
            "execution-issues",
            "append",
            "larch.issue.execution_issues",
            "append_execution_issue_main",
            "rust",
            "complete",
            "complete",
            "complete",
        ),
    );
    prepare(&repository, &ledger);
    repository.write(
        "python/larch/legacy_tracking.py",
        b"from larch.issue import tracking_issue as tracker\n\nRESULT = tracker.renamed_mutation()\n",
    );
    repository.write(
        "python/larch/legacy_execution_alias.py",
        b"import larch.issue.execution_issues as legacy\n\nRESULT = legacy.renamed_append()\n",
    );
    repository.write(
        "python/larch/legacy_execution_dynamic.py",
        b"import importlib\n\nOWNER = importlib.import_module(\"larch.issue.execution_issues\")\n",
    );
    repository.write(
        "python/larch/legacy_execution_from.py",
        b"from larch.issue.execution_issues import renamed_append as append\n\nRESULT = append()\n",
    );
    repository.write(
        "scripts/legacy_execution_parent.py",
        b"import larch.issue as issue\n\nOWNER = issue.execution_issues\n",
    );
    repository.write(
        "python/larch/pure_tracking.py",
        b"from larch.issue.tracking_issue import link_pr_closes as closes\n\nBODY = closes(body=\"PR\", issue_number=7)\n",
    );
    repository.write(
        "python/larch/issue_boundary_prose.py",
        b"TEXT = \"from larch.issue.execution_issues import renamed_append\"\n# tracking_issue.renamed_mutation()\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["command-registry", "sync", "--planning-issue", "7661"])
        .assert()
        .success()
        .stdout("COMMAND_REGISTRY_STATUS=synced\nCOMMANDS=3\nCALLERS=5\n")
        .stderr("");

    let ledger = fs::read_to_string(
        repository
            .path()
            .join("crates/larch-lint/data/command-registry.toml"),
    )
    .expect("read synced registry");
    assert!(ledger.contains("path = \"python/larch/legacy_tracking.py\""));
    assert!(ledger.contains("python = [\"tracking-issue *\"]"));
    assert!(ledger.contains("path = \"python/larch/legacy_execution_alias.py\""));
    assert!(ledger.contains("path = \"python/larch/legacy_execution_dynamic.py\""));
    assert!(ledger.contains("path = \"python/larch/legacy_execution_from.py\""));
    assert!(ledger.contains("path = \"scripts/legacy_execution_parent.py\""));
    assert!(ledger.contains("kind = \"script\""));
    assert!(ledger.contains("python = [\"execution-issues *\"]"));
    assert!(!ledger.contains("path = \"python/larch/pure_tracking.py\""));
    assert!(!ledger.contains("path = \"python/larch/issue_boundary_prose.py\""));

    TempRepo::command_from(repository.path())
        .args(["rule", "command-registry"])
        .assert()
        .failure()
        .stdout(predicate::str::contains(
            "tracking-issue rename cannot cut over to Rust while legacy callers remain: python/larch/legacy_tracking.py",
        ))
        .stdout(predicate::str::contains(
            "execution-issues append cannot cut over to Rust while legacy callers remain: python/larch/legacy_execution_alias.py, python/larch/legacy_execution_dynamic.py, python/larch/legacy_execution_from.py, scripts/legacy_execution_parent.py",
        ))
        .stdout(predicate::str::contains("python/larch/pure_tracking.py").not());
}

#[test]
fn python_owned_parity_and_atomic_rust_ownership_are_distinct_states() {
    let python = TempRepo::new();
    prepare(
        &python,
        &command_row("python", "complete", "pending", "pending"),
    );
    python.commit_all();
    TempRepo::command_from(python.path())
        .args(["rule", "command-registry"])
        .assert()
        .success()
        .stdout("")
        .stderr("");

    let rust = TempRepo::new();
    prepare(
        &rust,
        &command_row("rust", "complete", "complete", "pending"),
    );
    rust.commit_all();
    TempRepo::command_from(rust.path())
        .args(["rule", "command-registry"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "non-atomic-rust-owner fixture run: python removal is not complete",
        ))
        .stderr("");
}

#[test]
fn completed_python_removal_rejects_registration_definition_imports_and_calls() {
    let repository = TempRepo::new();
    let mut ledger = command_row_for(
        "retired",
        "run",
        "larch.fixture",
        "retired_main",
        "rust",
        "complete",
        "complete",
        "complete",
    );
    append_command(
        &mut ledger,
        &command_row_for(
            "fixture",
            "run",
            "larch.live",
            "main",
            "python",
            "pending",
            "pending",
            "pending",
        ),
    );
    repository.write(
        "python/larch/cli.py",
        b"_REGISTRY: dict[tuple[str, str], tuple[str, str, bool]] = {\n    (\"fixture\", \"run\"): (\"larch.live\", \"main\", False),\n    (\"retired\", \"run\"): (\"larch.fixture\", \"retired_main\", False),\n}\n",
    );
    repository.write(
        "crates/larch-lint/data/command-registry.toml",
        ledger.as_bytes(),
    );
    repository.write("hooks/hooks.json", b"{\"hooks\": {}}\n");
    repository.write(
        "python/larch/fixture.py",
        b"@staticmethod\ndef retired_main() -> int:\n    return 0\n\nRESULT = retired_main()\n",
    );
    repository.write(
        "python/larch/import_only.py",
        b"from larch.fixture import retired_main as old_entrypoint\nREFERENCE = old_entrypoint\n",
    );
    repository.write(
        "python/larch/caller.py",
        b"import larch.fixture as fixture_alias\nRESULT = fixture_alias.retired_main()\n",
    );
    repository.write(
        "python/larch/deep_qualified.py",
        b"import larch as root\nRESULT = root.fixture.retired_main()\n",
    );
    repository.write(
        "python/larch/false_positive.py",
        b"TEXT = \"from larch.fixture import retired_main\"\n# retired_main()\n",
    );
    repository.write(
        "python/larch/package/__init__.py",
        b"from ..fixture import retired_main as package_entrypoint\nPACKAGE_ENTRY = package_entrypoint\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "command-registry"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "python-entrypoint-still-present retired run: python/larch/cli.py",
        ))
        .stdout(predicate::str::contains(
            "python-entrypoint-still-present retired run: python/larch/fixture.py",
        ))
        .stdout(predicate::str::contains(
            "python-entrypoint-still-called retired run: python/larch/fixture.py",
        ))
        .stdout(predicate::str::contains(
            "python-entrypoint-still-imported retired run: python/larch/import_only.py",
        ))
        .stdout(predicate::str::contains(
            "python-entrypoint-still-called retired run: python/larch/caller.py",
        ))
        .stdout(predicate::str::contains(
            "python-entrypoint-still-called retired run: python/larch/deep_qualified.py",
        ))
        .stdout(predicate::str::contains(
            "python-entrypoint-still-imported retired run: python/larch/package/__init__.py",
        ))
        .stdout(predicate::str::contains("false_positive.py").not())
        .stderr("");
}

#[test]
fn completed_python_removals_preserve_findings_when_a_document_matches_multiple_entries() {
    let repository = TempRepo::new();
    let mut ledger = command_row_for(
        "retired",
        "run",
        "larch.fixture",
        "retired_main",
        "rust",
        "complete",
        "complete",
        "complete",
    );
    append_command(
        &mut ledger,
        &command_row_for(
            "retired",
            "status",
            "larch.fixture",
            "status_main",
            "rust",
            "complete",
            "complete",
            "complete",
        ),
    );
    prepare(&repository, &ledger);
    repository.write(
        "python/larch/cli.py",
        b"_REGISTRY: dict[tuple[str, str], tuple[str, str, bool]] = {\n    (\"retired\", \"run\"): (\"larch.fixture\", \"retired_main\", False),\n    (\"retired\", \"status\"): (\"larch.fixture\", \"status_main\", False),\n}\n",
    );
    repository.write(
        "python/larch/fixture.py",
        b"def retired_main() -> int:\n    return 0\n\ndef status_main() -> int:\n    return 0\n\nRETIRED = retired_main()\nSTATUS = status_main()\n",
    );
    repository.write(
        "python/larch/consumer.py",
        b"from larch.fixture import retired_main as retired, status_main as status\n\nRETIRED = retired()\nSTATUS = status()\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "command-registry"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "python-entrypoint-still-present retired run: python/larch/fixture.py",
        ))
        .stdout(predicate::str::contains(
            "python-entrypoint-still-called retired run: python/larch/fixture.py",
        ))
        .stdout(predicate::str::contains(
            "python-entrypoint-still-imported retired run: python/larch/consumer.py",
        ))
        .stdout(predicate::str::contains(
            "python-entrypoint-still-called retired run: python/larch/consumer.py",
        ))
        .stdout(predicate::str::contains(
            "python-entrypoint-still-present retired status: python/larch/fixture.py",
        ))
        .stdout(predicate::str::contains(
            "python-entrypoint-still-called retired status: python/larch/fixture.py",
        ))
        .stdout(predicate::str::contains(
            "python-entrypoint-still-imported retired status: python/larch/consumer.py",
        ))
        .stdout(predicate::str::contains(
            "python-entrypoint-still-called retired status: python/larch/consumer.py",
        ))
        .stderr("");
}

#[test]
fn live_rust_command_requires_a_matching_clean_install_fixture() {
    let repository = TempRepo::new();
    prepare(
        &repository,
        &command_row("rust", "complete", "complete", "complete"),
    );
    repository.write(
        "skills/example/SKILL.md",
        b"\"${CLAUDE_PLUGIN_ROOT}/scripts/larch.sh\" fixture run\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "command-registry"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "clean-install-coverage-missing fixture run",
        ))
        .stderr("");
}

#[test]
fn clean_install_fixture_references_reject_unknown_duplicate_and_malformed_ids() {
    let unknown = TempRepo::new();
    prepare(
        &unknown,
        &format!(
            "{}clean_install_test = \"missing-fixture\"\n",
            command_row("python", "pending", "pending", "pending")
        ),
    );
    unknown.commit_all();
    TempRepo::command_from(unknown.path())
        .args(["rule", "command-registry"])
        .assert()
        .code(2)
        .stderr(predicate::str::contains(
            "references unknown clean_install_test \"missing-fixture\"",
        ));

    let malformed = TempRepo::new();
    prepare(
        &malformed,
        &format!(
            "{}clean_install_test = \"Bad Fixture\"\n",
            command_row("python", "pending", "pending", "pending")
        ),
    );
    malformed.commit_all();
    TempRepo::command_from(malformed.path())
        .args(["rule", "command-registry"])
        .assert()
        .code(2)
        .stderr(predicate::str::contains("invalid clean_install_test token"));

    let duplicate = TempRepo::new();
    let mut duplicate_ledger = format!(
        "{}clean_install_test = \"clean-install-fixture-run\"\n",
        command_row("python", "pending", "pending", "pending")
    );
    let second = format!(
        "{}clean_install_test = \"clean-install-fixture-run\"\n",
        command_row_for(
            "fixture", "other", "fixture", "other", "python", "pending", "pending", "pending",
        )
    );
    append_command(&mut duplicate_ledger, &second);
    prepare(&duplicate, &duplicate_ledger);
    duplicate.commit_all();
    TempRepo::command_from(duplicate.path())
        .args(["rule", "command-registry"])
        .assert()
        .code(2)
        .stderr(predicate::str::contains(
            "duplicate clean_install_test \"clean-install-fixture-run\"",
        ));
}

#[test]
fn clean_install_fixture_table_rejects_duplicate_selectors_and_malformed_rows() {
    let duplicate = TempRepo::new();
    duplicate.write(
        "crates/larch-cli/tests/parity.rs",
        b"const CLEAN_INSTALL_CASES: &[CleanInstallCase] = &[\nCleanInstallCase::new(\"first\", \"fixture\", \"run\"),\nCleanInstallCase::new(\"second\", \"fixture\", \"run\"),\n];\n",
    );
    duplicate.commit_all();
    TempRepo::command_from(duplicate.path())
        .args(["rule", "command-registry"])
        .assert()
        .code(2)
        .stderr(predicate::str::contains(
            "duplicate clean-install selector fixture run",
        ));

    let malformed = TempRepo::new();
    malformed.write(
        "crates/larch-cli/tests/parity.rs",
        b"const CLEAN_INSTALL_CASES: &[CleanInstallCase] = &[CleanInstallCase::new(\"Bad Fixture\", \"fixture\", \"run\")];\n",
    );
    malformed.commit_all();
    TempRepo::command_from(malformed.path())
        .args(["rule", "command-registry"])
        .assert()
        .code(2)
        .stderr(predicate::str::contains(
            "parsed 0 of 1 clean-install fixture rows",
        ));
}

#[test]
fn migration_issue_audit_checks_both_directions_and_plan_mentions() {
    let repository = TempRepo::new();
    repository.commit_all();
    let input = repository.path().join("audit.json");
    fs::write(
        &input,
        r#"{"schema_version":1,"rollout_enabled":true,"issues":[{"number":7661,"state":"open","executable_leaf":true,"command":{"domain":"fixture","verb":"run"},"plan_commands":[{"domain":"fixture","verb":"run"}]}]}"#,
    )
    .expect("write audit input");
    TempRepo::command_from(repository.path())
        .args([
            "command-registry",
            "audit",
            "--input",
            input.to_str().expect("UTF-8 input path"),
        ])
        .assert()
        .success()
        .stdout("")
        .stderr("");

    fs::write(
        &input,
        r#"{"schema_version":1,"rollout_enabled":true,"issues":[{"number":7661,"state":"open","executable_leaf":true,"command":{"domain":"fixture","verb":"run"},"plan_commands":[]}]}"#,
    )
    .expect("write missing-plan audit input");
    TempRepo::command_from(repository.path())
        .args([
            "command-registry",
            "audit",
            "--input",
            input.to_str().expect("UTF-8 input path"),
        ])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "migration-issue-command-drift issue=#7661 command=fixture run",
        ));

    fs::write(
        &input,
        r#"{"schema_version":1,"rollout_enabled":true,"issues":[{"number":7661,"state":"open","executable_leaf":true,"command":null,"plan_commands":[]}]}"#,
    )
    .expect("write stale-registry audit input");
    TempRepo::command_from(repository.path())
        .args([
            "command-registry",
            "audit",
            "--input",
            input.to_str().expect("UTF-8 input path"),
        ])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "migration-issue-command-drift issue=#7661 command=fixture run",
        ));

    fs::write(
        &input,
        r#"{"schema_version":1,"rollout_enabled":false,"issues":[{"number":7661,"state":"open","executable_leaf":true,"command":{"domain":"fixture","verb":"missing"},"plan_commands":[{"domain":"fixture","verb":"missing"}]}]}"#,
    )
    .expect("write missing-selector audit input");
    TempRepo::command_from(repository.path())
        .args([
            "command-registry",
            "audit",
            "--input",
            input.to_str().expect("UTF-8 input path"),
        ])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "migration-issue-command-drift issue=#7661 command=fixture missing",
        ));

    fs::write(
        &input,
        r#"{"schema_version":1,"rollout_enabled":false,"issues":[{"number":9999,"state":"open","executable_leaf":true,"command":{"domain":"fixture","verb":"run"},"plan_commands":[{"domain":"fixture","verb":"run"}]}]}"#,
    )
    .expect("write wrong-issue audit input");
    TempRepo::command_from(repository.path())
        .args([
            "command-registry",
            "audit",
            "--input",
            input.to_str().expect("UTF-8 input path"),
        ])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "migration-issue-command-drift issue=#9999 command=fixture run",
        ));
}

#[test]
fn migration_issue_audit_rejects_malformed_schema_duplicate_and_unsorted_input() {
    let repository = TempRepo::new();
    repository.commit_all();
    let input = repository.path().join("audit.json");

    for (body, error) in [
        (
            r#"{"schema_version":2,"rollout_enabled":false,"issues":[]}"#,
            "unsupported schema_version 2; expected 1",
        ),
        (
            r#"{"schema_version":1,"rollout_enabled":false,"issues":[{"number":7661,"state":"open","executable_leaf":true,"command":null,"plan_commands":[]},{"number":7661,"state":"closed","executable_leaf":false,"command":null,"plan_commands":[]}]}"#,
            "issue numbers must be positive and unique",
        ),
        (
            r#"{"schema_version":1,"rollout_enabled":false,"issues":[{"number":0,"state":"open","executable_leaf":true,"command":null,"plan_commands":[]}]}"#,
            "issue numbers must be positive and unique",
        ),
        (
            r#"{"schema_version":1,"rollout_enabled":false,"issues":[{"number":7661,"state":"open","executable_leaf":true,"command":{"domain":"Fixture","verb":"run"},"plan_commands":[]}]}"#,
            "invalid audit command domain token",
        ),
        (
            r#"{"schema_version":1,"rollout_enabled":false,"issues":[{"number":7661,"state":"open","executable_leaf":true,"command":null,"plan_commands":[{"domain":"fixture","verb":"run"},{"domain":"fixture","verb":"run"}]}]}"#,
            "plan_commands must be sorted and unique",
        ),
    ] {
        fs::write(&input, body).expect("write audit input");
        TempRepo::command_from(repository.path())
            .args([
                "command-registry",
                "audit",
                "--input",
                input.to_str().expect("UTF-8 input path"),
            ])
            .assert()
            .code(2)
            .stdout("")
            .stderr(predicate::str::contains(error));
    }
}

#[test]
fn ledger_rejects_invalid_schema_command_and_caller_shapes() {
    let schema = TempRepo::new();
    prepare(&schema, "schema_version = 1\n");
    schema.commit_all();
    TempRepo::command_from(schema.path())
        .args(["rule", "command-registry"])
        .assert()
        .code(2)
        .stdout("")
        .stderr(predicate::str::contains("unsupported schema_version 1"));

    let invalid_command = TempRepo::new();
    prepare(
        &invalid_command,
        &command_row("python", "pending", "pending", "pending")
            .replace("domain = \"fixture\"", "domain = \"Fixture\""),
    );
    invalid_command.commit_all();
    TempRepo::command_from(invalid_command.path())
        .args(["rule", "command-registry"])
        .assert()
        .code(2)
        .stdout("")
        .stderr(predicate::str::contains("invalid domain token \"Fixture\""));

    let invalid_caller = TempRepo::new();
    let mut ledger = command_row("python", "pending", "pending", "pending");
    ledger.push_str(
        "\n[[callers]]\npath = \"../outside\"\nkind = \"skill\"\npython = []\nrust = []\n",
    );
    prepare(&invalid_caller, &ledger);
    invalid_caller.commit_all();
    TempRepo::command_from(invalid_caller.path())
        .args(["rule", "command-registry"])
        .assert()
        .code(2)
        .stdout("")
        .stderr(predicate::str::contains(
            "unsafe caller path \"../outside\"",
        ));

    let unsorted = TempRepo::new();
    let mut ledger = command_row("python", "pending", "pending", "pending");
    ledger.push_str(
        "\n[[callers]]\npath = \"skills/example/SKILL.md\"\nkind = \"skill\"\npython = [\"fixture run\", \"fixture run\"]\nrust = []\n",
    );
    prepare(&unsorted, &ledger);
    unsorted.commit_all();
    TempRepo::command_from(unsorted.path())
        .args(["rule", "command-registry"])
        .assert()
        .code(2)
        .stdout("")
        .stderr(predicate::str::contains(
            "skills/example/SKILL.md python selectors must be sorted and unique",
        ));
}
