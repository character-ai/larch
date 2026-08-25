use crate::support;

use predicates::prelude::*;
use support::TempRepo;

const fn final_command() -> &'static str {
    r#"[[commands]]
domain = "review"
verb = "core"
machine_stdout = true
owner = "rust"
planning_issue = 7679
migration_issue = 8445
"#
}

fn handoff_command(planning_issue: u64) -> String {
    format!(
        r#"[[commands]]
domain = "render"
verb = "voter"
machine_stdout = false
owner = "rust"
planning_issue = {planning_issue}
migration_issue = 8560
"#
    )
}

fn prepare(repository: &TempRepo, planning_issue: u64) {
    repository.write(
        "crates/larch-lint/data/command-registry.toml",
        format!(
            "schema_version = 3\n\n{}\n{}",
            final_command(),
            handoff_command(planning_issue)
        )
        .as_bytes(),
    );
}

#[test]
fn sampled_final_rows_report_only_the_unsampled_inventory() {
    let repository = TempRepo::new();
    prepare(&repository, 7686);
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "review-python-free"])
        .assert()
        .code(1)
        .stdout(
            predicate::str::contains("missing final review command row: review gather-context")
                .and(predicate::str::contains(
                    "missing review-command hand-off row: render specialist",
                ))
                .and(predicate::str::contains("non-final review command row: review core").not())
                .and(predicate::str::contains("review-command hand-off drift: render voter").not()),
        )
        .stderr(predicate::str::is_empty());
}

#[test]
fn rejects_handoff_drift_and_unclosed_review_rows() {
    let repository = TempRepo::new();
    prepare(&repository, 7679);
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "review-python-free"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "review-command hand-off drift: render voter; expected #7686",
        ))
        .stderr(predicate::str::is_empty());
}

#[test]
fn rejects_restored_review_package_and_live_runtime_reference() {
    let repository = TempRepo::new();
    prepare(&repository, 7686);
    repository.write(
        "python/larch/review/legacy.py",
        b"def legacy() -> None:\n    return None\n",
    );
    repository.write(
        "skills/review/runtime.md",
        b"Import larch.review.legacy for the old runtime.\n",
    );
    repository.write(
        "hooks/hooks.json",
        br#"{"hooks":{"Stop":[{"hooks":[{"type":"command","command":"python3 python/larch/review/legacy.py"}]}]}}
"#,
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "review-python-free"])
        .assert()
        .code(1)
        .stdout(
            predicate::str::contains(
                "python/larch/review/legacy.py:1: superseded Python review package source remains",
            )
            .and(predicate::str::contains(
                "skills/review/runtime.md:1: live runtime source references the retired Python review package",
            ))
            .and(predicate::str::contains(
                "hooks/hooks.json:1: live runtime source references the retired Python review package",
            )),
        )
        .stderr(predicate::str::is_empty());
}

#[test]
fn rejects_restored_python_registration_for_migrated_command() {
    let repository = TempRepo::new();
    prepare(&repository, 7686);
    repository.write(
        "python/larch/cli.py",
        b"_REGISTRY: dict[tuple[str, str], tuple[str, str, bool]] = {\n    (\"review\", \"core\"): (\"larch.review.review_core_body\", \"review_core_main\", True),\n    (\"render\", \"voter\"): (\"larch.rendering.rendering\", \"render_voter_main\", False),\n}\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "review-python-free"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "python-entrypoint-still-present review core: python/larch/cli.py",
        ))
        .stderr(predicate::str::is_empty());
}
