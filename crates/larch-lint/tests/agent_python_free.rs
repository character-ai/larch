use crate::support;

use predicates::prelude::*;
use support::TempRepo;

const CLOSED_REGISTRY: &str = include_str!("../data/command-registry.toml");

fn write_closed_registry(repository: &TempRepo, registry: &str) {
    repository.write(
        "crates/larch-lint/data/command-registry.toml",
        registry.as_bytes(),
    );
    repository.write(
        "crates/larch-cli/src/agent_commands.rs",
        b"pub fn run() {}\n",
    );
}

fn without_command(registry: &str, domain: &str, verb: &str) -> String {
    let header = format!("[[commands]]\ndomain = \"{domain}\"\nverb = \"{verb}\"\n");
    let start = registry.find(&header).expect("fixture command row");
    let following = start + header.len();
    let end = registry[following..]
        .find("\n[[commands]]")
        .map_or(registry.len(), |offset| following + offset + 1);
    let mut edited = registry.to_owned();
    edited.replace_range(start..end, "");
    edited
}

#[test]
fn agent_python_free_accepts_the_closed_boundary() {
    let repository = TempRepo::new();
    write_closed_registry(&repository, CLOSED_REGISTRY);
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "agent-python-free"])
        .assert()
        .success()
        .stdout("")
        .stderr("");
}

#[test]
fn agent_python_free_rejects_command_ledger_count_drift() {
    let repository = TempRepo::new();
    let registry = without_command(CLOSED_REGISTRY, "agent", "check-reviewers");
    write_closed_registry(&repository, &registry);
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "agent-python-free"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "#7678 command ledger count drift: expected 35, found 34",
        ));
}

#[test]
fn agent_python_free_rejects_a_same_count_selector_substitution() {
    let repository = TempRepo::new();
    let registry = CLOSED_REGISTRY.replacen(
        "verb = \"check-reviewers\"",
        "verb = \"invented-reviewer-check\"",
        1,
    );
    write_closed_registry(&repository, &registry);
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "agent-python-free"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "unexpected #7678 command row: agent invented-reviewer-check",
        ))
        .stdout(predicate::str::contains(
            "missing #7678 command row: agent check-reviewers",
        ));
}

#[test]
fn agent_python_free_rejects_restored_python_surfaces_and_runtime_callers() {
    let repository = TempRepo::new();
    write_closed_registry(&repository, CLOSED_REGISTRY);
    repository.write(
        "python/larch/agents/agents.py",
        b"def check_reviewers_main():\n    return 0\n",
    );
    repository.write(
        "scripts/legacy.sh",
        b"#!/usr/bin/env bash\npython3 python/cli.py agent check-reviewers\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "agent-python-free"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "python/larch/agents/agents.py:1: retired Python vendor-agent surface returned",
        ))
        .stdout(predicate::str::contains(
            "scripts/legacy.sh:2: live runtime or tooling still references the retired Python vendor-agent surface",
        ));
}

#[test]
fn agent_python_free_rejects_restored_python_registration() {
    let repository = TempRepo::new();
    write_closed_registry(&repository, CLOSED_REGISTRY);
    repository.write(
        "python/larch/cli.py",
        br#"_REGISTRY: dict[tuple[str, str], tuple[str, str, bool]] = {
    ("agent", "check-reviewers"): ("larch.agents.agents", "check_reviewers_main", False),
}
"#,
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "agent-python-free"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "retired vendor-agent command remains registered in Python: agent check-reviewers",
        ));
}
