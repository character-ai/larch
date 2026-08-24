use crate::support;

use std::fmt::Write as _;

use predicates::prelude::*;
use support::TempRepo;

const COMMANDS: [(&str, &str, u64, u64, &str, &str); 3] = [
    (
        "issue",
        "state",
        8167,
        7682,
        "larch.issue.issue_query",
        "issue_state_main",
    ),
    (
        "oos",
        "file",
        8179,
        7680,
        "larch.issue.oos_filer",
        "cmd_file",
    ),
    (
        "audit-runs",
        "title",
        8189,
        7682,
        "larch.issue.audit_runs",
        "title_main",
    ),
];

const HANDOFFS: [(&str, &str, u64); 2] = [
    ("issue", "migration-audit", 7685),
    ("oos", "serialize", 7680),
];

fn registry() -> String {
    let mut output = String::from("schema_version = 2\n");
    for (domain, verb, migration_issue, planning_issue, python_module, python_function) in COMMANDS
    {
        let _ = write!(
            output,
            r#"
[[commands]]
domain = "{domain}"
verb = "{verb}"
python_module = "{python_module}"
python_function = "{python_function}"
machine_stdout = false
owner = "rust"
implementation_parity = "complete"
consumer_cutover = "complete"
python_removal = "complete"
planning_issue = {planning_issue}
migration_issue = {migration_issue}
"#,
        );
    }
    for (domain, verb, planning_issue) in HANDOFFS {
        let _ = write!(
            output,
            r#"
[[commands]]
domain = "{domain}"
verb = "{verb}"
python_module = "larch.issue.handoff"
python_function = "main"
machine_stdout = false
owner = "python"
implementation_parity = "pending"
consumer_cutover = "pending"
python_removal = "pending"
planning_issue = {planning_issue}
"#,
        );
    }
    output
}

fn prepare(repository: &TempRepo) {
    repository.write(
        "crates/larch-lint/data/command-registry.toml",
        registry().as_bytes(),
    );
    repository.write(
        "python/larch/cli.py",
        b"_REGISTRY = {('other', 'run'): ('other', 'main', False)}\n",
    );
    repository.write(
        "skills/implement/scripts/refresh-execution-issues.sh",
        b"exec \"$PLUGIN_ROOT/scripts/larch.sh\" execution-issues refresh \"$@\"\n",
    );
}

/// A sample carries completed and hand-off rows, so only the unrepresented
/// final boundary rows should fail in this small fixture.
#[test]
fn accepts_sample_rows_and_reports_only_missing_boundary_rows() {
    let repository = TempRepo::new();
    prepare(&repository);
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "issue-python-free"])
        .assert()
        .failure()
        .stdout(
            predicate::str::contains("missing final issue-domain command row: issue context")
                .and(predicate::str::contains("non-final").not())
                .and(predicate::str::contains("drift").not())
                .and(predicate::str::contains("remains registered in Python").not())
                .and(predicate::str::contains("retired issue-domain").not()),
        )
        .stderr("");
}

#[test]
fn rejects_restored_python_registration_and_entrypoint() {
    let repository = TempRepo::new();
    prepare(&repository);
    repository.write(
        "python/larch/cli.py",
        b"_REGISTRY = {('issue', 'state'): ('larch.issue.issue_query', 'issue_state_main', False)}\n",
    );
    repository.write(
        "python/larch/issue/issue_query.py",
        b"def issue_state_main(argv: list[str]) -> int:\n    return 0\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "issue-python-free"])
        .assert()
        .failure()
        .stdout(predicate::str::contains(
            "issue-domain command remains registered in Python: issue state",
        ))
        .stdout(predicate::str::contains(
            "superseded issue-domain Python entrypoint remains: larch.issue.issue_query.issue_state_main",
        ));
}

#[test]
fn rejects_non_final_rows_handoff_owner_drift_and_unclosed_rows() {
    let repository = TempRepo::new();
    prepare(&repository);
    let drifted = format!(
        "{}\n[[commands]]\ndomain = \"unowned\"\nverb = \"issue-surface\"\nplanning_issue = 7682\n",
        registry()
    )
    .replacen("owner = \"rust\"", "owner = \"python\"", 1)
    .replacen("migration_issue = 8167", "migration_issue = 8168", 1)
    .replacen("planning_issue = 7680", "planning_issue = 7682", 1)
    .replacen("planning_issue = 7685", "planning_issue = 7682", 1);
    repository.write(
        "crates/larch-lint/data/command-registry.toml",
        drifted.as_bytes(),
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "issue-python-free"])
        .assert()
        .failure()
        .stdout(predicate::str::contains(
            "non-final issue-domain command row: issue state",
        ))
        .stdout(predicate::str::contains(
            "issue-domain migration leaf drift: issue state; expected #8167",
        ))
        .stdout(predicate::str::contains(
            "issue-domain planning owner drift: oos file; expected #7680",
        ))
        .stdout(predicate::str::contains(
            "issue-domain hand-off drift: issue migration-audit; expected #7685",
        ))
        .stdout(predicate::str::contains(
            "unclosed #7682 ledger row: unowned issue-surface",
        ));
}

#[test]
fn rejects_restored_issue_module() {
    let repository = TempRepo::new();
    prepare(&repository);
    repository.write(
        "python/larch/issue/nested/new_owner.py",
        b"def helper() -> None:\n    return None\n",
    );
    repository.write(
        "python/larch/issue/nested/__init__.py",
        b"\"\"\"Nested issue package.\"\"\"\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "issue-python-free"])
        .assert()
        .failure()
        .stdout(predicate::str::contains(
            "python/larch/issue/nested/new_owner.py:1: retired issue-domain Python module returned",
        ))
        .stdout(predicate::str::contains(
            "python/larch/issue/nested/__init__.py:1: retired issue-domain Python module returned",
        ));
}

#[test]
fn rejects_restored_tracking_github_behavior_and_bypass_callers() {
    let repository = TempRepo::new();
    prepare(&repository);
    repository.write(
        "python/larch/issue/tracking_issue.py",
        b"from larch.git import gh\n\ndef mutate() -> None:\n    gh.issue_comment()\n",
    );
    repository.write(
        "python/larch/state/bootstrap.py",
        b"from larch.issue import tracking_issue\n\ndef activate() -> None:\n    tracking_issue.rename_with_details()\n\ndef resume() -> None:\n    _invoke_cli(\n        [\"tracking-issue\", \"read\"]\n    )\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "issue-python-free"])
        .assert()
        .failure()
        .stdout(predicate::str::contains(
            "python-command-equivalent-still-owned tracking-issue *: python/larch/issue/tracking_issue.py",
        ))
        .stdout(predicate::str::contains(
            "python-command-equivalent-still-owned tracking-issue *: python/larch/state/bootstrap.py",
        ))
        .stdout(predicate::str::contains(
            "production caller routes a retired tracking command through python/cli.py",
        ));
}

#[test]
fn rejects_restored_execution_issue_module_and_import_callers() {
    let repository = TempRepo::new();
    prepare(&repository);
    repository.write(
        "python/larch/issue/execution_issues.py",
        b"def append_execution_issue() -> None:\n    return None\n",
    );
    repository.write(
        "python/larch/implement/dispatch.py",
        b"from larch.issue import execution_issues\n\ndef run() -> None:\n    execution_issues.append_execution_issue()\n",
    );
    repository.write(
        "skills/implement/scripts/refresh-execution-issues.sh",
        b"\"$PLUGIN_ROOT/scripts/larch.sh\" tracking-issue upsert-summary\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "issue-python-free"])
        .assert()
        .failure()
        .stdout(predicate::str::contains(
            "superseded Python execution-issues behavior returned",
        ))
        .stdout(predicate::str::contains(
            "python-command-equivalent-still-owned execution-issues *: python/larch/implement/dispatch.py",
        ))
        .stdout(predicate::str::contains(
            "superseded Bash execution-issues refresh behavior returned",
        ));
}

#[test]
fn rejects_restored_tracking_module_but_ignores_non_issue_helpers() {
    let repository = TempRepo::new();
    prepare(&repository);
    repository.write(
        "python/larch/issue/tracking_issue.py",
        br#"from __future__ import annotations

def link_pr_closes(*, body: str, issue_number: int) -> str:
    return body + f"\n\nCloses #{issue_number}\n"

def renamed_mutation(*, issue_number: int) -> None:
    return None
"#,
    );
    repository.write(
        "python/larch/git/allowed_footer.py",
        b"from larch.issue.tracking_issue import link_pr_closes as closes\n\nBODY = closes(body=\"PR\", issue_number=7)\n",
    );
    repository.write(
        "python/larch/rendering/allowed_handoff.py",
        b"from larch.issue import issue_wire\n\nVALUE = issue_wire.helper()\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "issue-python-free"])
        .assert()
        .failure()
        .stdout(
            predicate::str::contains(
                "python/larch/issue/tracking_issue.py:1: retired issue-domain Python module returned",
            )
            .and(predicate::str::contains("python/larch/git/allowed_footer.py").not())
            .and(predicate::str::contains("python/larch/rendering/allowed_handoff.py").not()),
        );
}

#[test]
fn rejects_command_behavior_hidden_under_a_pure_tracking_name() {
    let repository = TempRepo::new();
    prepare(&repository);
    repository.write(
        "python/larch/issue/tracking_issue.py",
        br#"from __future__ import annotations

def link_pr_closes(*, body: str, issue_number: int) -> str:
    process = __import__("subprocess")
    return process.run(["gh", "issue", "edit", str(issue_number)]).stdout or body
"#,
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "issue-python-free"])
        .assert()
        .failure()
        .stdout(predicate::str::contains(
            "python-command-equivalent-still-owned tracking-issue *: python/larch/issue/tracking_issue.py",
        ));
}
