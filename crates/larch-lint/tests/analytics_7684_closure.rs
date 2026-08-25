use crate::support;

use std::fs;

use predicates::prelude::*;
use support::TempRepo;

const RULE: &str = "analytics-7684-closure";

fn git_inventory(rows: &str) -> String {
    format!(
        "# Git operation inventory\n\n<!-- git-ownership-matrix:start -->\n```text\nsurface\towner\tissue\toperations\n{rows}```\n<!-- git-ownership-matrix:end -->\n"
    )
}

fn service_inventory(rows: &str) -> String {
    format!(
        "<!-- github-service-ownership:start -->\n```text\noperation\tadapter_owner\tcurrent_owner\tplanning_issues\timplementation_parity\tconsumer_cutover\tpython_removal\tcommands\n{rows}```\n<!-- github-service-ownership:end -->\n"
    )
}

fn closure_registry(rows: &str) -> String {
    format!(
        "schema_version = 3\n\n[[commands]]\ndomain = \"fixture\"\nverb = \"run\"\nmachine_stdout = false\nowner = \"rust\"\nplanning_issue = 7681\nmigration_issue = 7681\n\n{rows}"
    )
}

fn closure_command(
    domain: &str,
    verb: &str,
    owner: &str,
    _parity: &str,
    _cutover: &str,
    _removal: &str,
    migration_issue: Option<u64>,
) -> String {
    let migration_issue = migration_issue.map_or_else(
        || "migration_issue = 7684\n".to_owned(),
        |issue| format!("migration_issue = {issue}\n"),
    );
    format!(
        "[[commands]]\ndomain = \"{domain}\"\nverb = \"{verb}\"\nmachine_stdout = false\nowner = \"{owner}\"\nplanning_issue = 7684\n{migration_issue}\n"
    )
}

fn analyzer_skill(domain: &str) -> String {
    format!(
        "# {domain}\n\n```bash\n\"${{CLAUDE_PLUGIN_ROOT}}/scripts/larch.sh\" {domain} analyze [flags]\n```\n"
    )
}

fn write_baseline(
    repository: &TempRepo,
    registry_rows: &str,
    service: Option<&str>,
    git: Option<&str>,
) {
    repository.write(
        "crates/larch-lint/data/command-registry.toml",
        closure_registry(registry_rows).as_bytes(),
    );
    repository.write("hooks/hooks.json", b"{}\n");
    if let Some(service) = service {
        repository.write("docs/github-service-inventory.md", service.as_bytes());
    }
    if let Some(git) = git {
        repository.write("docs/git-operation-inventory.md", git.as_bytes());
    }
    repository.write(
        "skills/fluff-analysis/SKILL.md",
        analyzer_skill("fluff-analysis").as_bytes(),
    );
    repository.write(
        "skills/voter-calibration/SKILL.md",
        analyzer_skill("voter-calibration").as_bytes(),
    );
}

fn complete_rows() -> String {
    closure_command(
        "fluff-analysis",
        "analyze",
        "rust",
        "complete",
        "complete",
        "complete",
        Some(8671),
    ) + &closure_command(
        "voter-calibration",
        "analyze",
        "rust",
        "complete",
        "complete",
        "complete",
        Some(8672),
    )
}

fn completed_service_inventory() -> String {
    service_inventory(
        "issues\tcrates/larch-adapters/src/github_rest.rs\trust\t#7684\tcomplete\tcomplete\tcomplete\tfluff-analysis analyze\n",
    )
}

#[test]
fn ignores_a_fixture_without_the_analytics_boundary() {
    let repository = TempRepo::new();
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", RULE])
        .assert()
        .success()
        .stdout(predicate::str::is_empty())
        .stderr(predicate::str::is_empty());
}

#[test]
fn accepts_closed_analytics_boundary() {
    let repository = TempRepo::new();
    write_baseline(
        &repository,
        &complete_rows(),
        Some(&completed_service_inventory()),
        Some(&git_inventory("")),
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", RULE])
        .assert()
        .success()
        .stdout(predicate::str::is_empty())
        .stderr(predicate::str::is_empty());
}

#[test]
fn rejects_non_rust_analytics_command_ownership() {
    let repository = TempRepo::new();
    write_baseline(
        &repository,
        &closure_command(
            "fluff-analysis",
            "analyze",
            "retired",
            "pending",
            "pending",
            "pending",
            Some(8671),
        ),
        Some(&completed_service_inventory()),
        Some(&git_inventory("")),
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", RULE])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "planning issue #7684 command fluff-analysis analyze is not Rust-owned",
        ))
        .stderr(predicate::str::is_empty());
}

#[test]
fn rejects_missing_and_umbrella_analytics_migration_leaves() {
    let repository = TempRepo::new();
    let missing = closure_command(
        "fluff-analysis",
        "analyze",
        "rust",
        "complete",
        "complete",
        "complete",
        None,
    );
    let umbrella = closure_command(
        "voter-calibration",
        "analyze",
        "rust",
        "complete",
        "complete",
        "complete",
        Some(7684),
    );
    write_baseline(
        &repository,
        &(missing + &umbrella),
        Some(&completed_service_inventory()),
        Some(&git_inventory("")),
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", RULE])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "planning issue #7684 command fluff-analysis analyze lacks an exact non-umbrella migration leaf",
        ))
        .stdout(predicate::str::contains(
            "planning issue #7684 command voter-calibration analyze lacks an exact non-umbrella migration leaf",
        ))
        .stderr(predicate::str::is_empty());
}

#[test]
fn rejects_direct_python_analyzer_entrypoint_and_retired_script() {
    let repository = TempRepo::new();
    write_baseline(
        &repository,
        &complete_rows(),
        Some(&completed_service_inventory()),
        Some(&git_inventory("")),
    );
    repository.write(
        "skills/fluff-analysis/SKILL.md",
        b"# fluff-analysis\n\n```bash\npython3 \"${CLAUDE_PLUGIN_ROOT}/skills/fluff-analysis/scripts/fluff-analysis.py\"\n```\n",
    );
    repository.write(
        "skills/fluff-analysis/scripts/fluff-analysis.py",
        b"#!/usr/bin/env python3\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", RULE])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "shipped analytics entrypoint does not invoke its Rust owner: fluff-analysis analyze",
        ))
        .stdout(predicate::str::contains(
            "shipped analytics entrypoint directly invokes retired Python analyzer: skills/fluff-analysis/scripts/fluff-analysis.py",
        ))
        .stdout(predicate::str::contains(
            "skills/fluff-analysis/scripts/fluff-analysis.py:1: superseded shipped Python analyzer remains",
        ))
        .stderr(predicate::str::is_empty());
}

#[test]
fn rejects_unresolved_analytics_service_and_git_inventory_rows() {
    let repository = TempRepo::new();
    write_baseline(
        &repository,
        &complete_rows(),
        Some(&service_inventory(
            "issues\tcrates/larch-adapters/src/github_rest.rs\tpython\t#7684\tpending\tpending\tpending\tfluff-analysis analyze\n",
        )),
        Some(&git_inventory(
            "skills/fluff-analysis/scripts/fluff-analysis.py\tlater-domain\t#7684\tstatus\n",
        )),
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", RULE])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "GitHub service inventory still has incomplete #7684 ownership for operation: issues",
        ))
        .stdout(predicate::str::contains(
            "Git-operation inventory still has unresolved later-domain #7684 row: skills/fluff-analysis/scripts/fluff-analysis.py",
        ))
        .stderr(predicate::str::is_empty());
}

#[test]
fn fails_closed_on_malformed_or_unavailable_analytics_evidence() {
    for (service, git, message) in [
        (
            Some(
                "<!-- github-service-ownership:start -->\nissues\n<!-- github-service-ownership:end -->\n"
                    .to_owned(),
            ),
            Some(git_inventory("")),
            "docs/github-service-inventory.md: invalid GitHub service ownership header",
        ),
        (
            None,
            Some(git_inventory("")),
            "docs/github-service-inventory.md: required GitHub service ownership matrix is missing",
        ),
        (
            Some(completed_service_inventory()),
            None,
            "docs/git-operation-inventory.md: required Git operation ownership matrix is missing",
        ),
        (
            Some(completed_service_inventory()),
            Some("not an inventory\n".to_owned()),
            "docs/git-operation-inventory.md: missing <!-- git-ownership-matrix:start -->",
        ),
    ] {
        let repository = TempRepo::new();
        write_baseline(
            &repository,
            &complete_rows(),
            service.as_deref(),
            git.as_deref(),
        );
        if service.is_none() {
            fs::remove_file(repository.path().join("docs/github-service-inventory.md"))
                .expect("remove seeded GitHub-service inventory");
        }
        repository.commit_all();

        TempRepo::command_from(repository.path())
            .args(["rule", RULE])
            .assert()
            .code(2)
            .stdout(predicate::str::is_empty())
            .stderr(predicate::str::contains(message));
    }
}
