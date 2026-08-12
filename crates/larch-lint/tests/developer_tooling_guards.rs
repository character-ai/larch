mod support;

use predicates::prelude::*;
use support::TempRepo;

fn write_rust_owned_registry(repository: &TempRepo, domain: &str, verb: &str) {
    repository.write(
        "crates/larch-lint/data/command-registry.toml",
        format!(
            r#"schema_version = 2

[[commands]]
domain = "fixture"
verb = "run"
python_module = "fixture"
python_function = "main"
machine_stdout = false
owner = "python"
implementation_parity = "pending"
consumer_cutover = "pending"
python_removal = "pending"
planning_issue = 7661
migration_issue = 7661

[[commands]]
domain = "{domain}"
verb = "{verb}"
python_module = "larch.example"
python_function = "main"
machine_stdout = false
owner = "rust"
implementation_parity = "complete"
consumer_cutover = "complete"
python_removal = "complete"
planning_issue = 8094
migration_issue = 8094
"#
        )
        .as_bytes(),
    );
}

#[test]
fn rust_owned_python_passes_without_python_callers() {
    let repository = TempRepo::new();
    write_rust_owned_registry(&repository, "plugin", "read-version");
    repository.write(
        "Makefile",
        b"lint:\n\tpython3 python/cli.py lint keyword-only\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "developer-tooling-rust-owned-python"])
        .assert()
        .success()
        .stdout(predicate::str::is_empty())
        .stderr(predicate::str::is_empty());
}

#[test]
fn rust_owned_python_fails_on_makefile_caller() {
    let repository = TempRepo::new();
    write_rust_owned_registry(&repository, "plugin", "read-version");
    repository.write(
        "Makefile",
        b"version:\n\tpython3 python/cli.py plugin read-version\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "developer-tooling-rust-owned-python"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "Makefile:2: developer tooling invokes python/cli.py plugin read-version; command registry marks it Rust-owned",
        ))
        .stderr(predicate::str::is_empty());
}

#[test]
fn crate_process_passes_with_vendor_and_documented_exceptions() {
    let repository = TempRepo::new();
    repository.write(
        "scripts/residual-bash-paths.txt",
        b"scripts/larch.sh\nscripts/file-failure-report-cross-repo.sh\nskills/combine-issues/scripts/search-implementing-issue.sh\nskills/implement/scripts/step-architectural-guidelines-write-staged.sh\n",
    );
    repository.write(
        "scripts/larch.sh",
        b"#!/usr/bin/env bash\ngh release verify v1\n",
    );
    repository.write(
        "scripts/file-failure-report-cross-repo.sh",
        b"#!/usr/bin/env bash\ngh issue create --title report\n",
    );
    repository.write(
        "skills/combine-issues/scripts/search-implementing-issue.sh",
        b"#!/usr/bin/env bash\ngh issue list --state open\n",
    );
    repository.write(
        "skills/implement/scripts/step-architectural-guidelines-write-staged.sh",
        b"#!/usr/bin/env bash\ngit rev-parse HEAD\n",
    );
    repository.write(
        ".github/actions/github-auth-config/action.yaml",
        b"runs:\n  using: composite\n  steps:\n    - run: gh auth status --hostname github.com\n",
    );
    repository.write(
        "scripts/vendor.sh",
        b"#!/usr/bin/env bash\nclaude -p hello\ncodex exec\ncursor agent\n",
    );
    repository.write(
        ".github/workflows/rust-release-assets.yaml",
        b"jobs:\n  upload:\n    steps:\n      - run: gh release upload tag asset\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "developer-tooling-crate-process"])
        .assert()
        .success()
        .stdout(predicate::str::is_empty())
        .stderr(predicate::str::is_empty());
}

#[test]
fn crate_process_does_not_treat_the_residual_manifest_as_a_blanket_waiver() {
    let repository = TempRepo::new();
    repository.write(
        "scripts/residual-bash-paths.txt",
        b"scripts/unreviewed-gh.sh\n",
    );
    repository.write(
        "scripts/unreviewed-gh.sh",
        b"#!/usr/bin/env bash\ngh api /user\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "developer-tooling-crate-process"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "scripts/unreviewed-gh.sh:2: developer tooling spawns gh; a Rust crate already provides this capability",
        ))
        .stderr(predicate::str::is_empty());
}

#[test]
fn crate_process_rejects_manifest_named_skill_runtime_surface() {
    let repository = TempRepo::new();
    repository.write(
        "scripts/residual-bash-paths.txt",
        b"skills/design/scripts/runtime-helper.sh\n",
    );
    repository.write(
        "skills/design/scripts/runtime-helper.sh",
        b"#!/usr/bin/env bash\ngit status --short\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "developer-tooling-crate-process"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "skills/design/scripts/runtime-helper.sh:2: developer tooling spawns git; a Rust crate already provides this capability",
        ))
        .stderr(predicate::str::is_empty());
}

#[test]
fn crate_process_fails_on_gcloud_in_makefile() {
    let repository = TempRepo::new();
    repository.write("Makefile", b"auth:\n\tgcloud auth print-access-token\n");
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "developer-tooling-crate-process"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "Makefile:2: developer tooling spawns gcloud; a Rust crate already provides this capability",
        ))
        .stderr(predicate::str::is_empty());
}

#[test]
fn crate_process_rejects_retained_skill_prompt_and_workflow_git() {
    let repository = TempRepo::new();
    repository.write(
        ".claude/skills/larch-size/SKILL.md",
        b"Run:\n\n```bash\ngit status --short\n```\n",
    );
    repository.write(
        ".github/workflows/ci.yaml",
        b"jobs:\n  check:\n    steps:\n      - run: git rev-parse HEAD\n      - run: |\n          gh api /user\n",
    );
    repository.write(
        ".github/actions/unreviewed/action.yaml",
        b"runs:\n  using: composite\n  steps:\n      - run: gcloud auth print-access-token\n",
    );
    repository.write(
        ".pre-commit-config.yaml",
        b"repos:\n  - entry: gcloud auth print-access-token\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "developer-tooling-crate-process"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            ".claude/skills/larch-size/SKILL.md:4: developer tooling spawns git; a Rust crate already provides this capability",
        ))
        .stdout(predicate::str::contains(
            ".github/workflows/ci.yaml:4: developer tooling spawns git; a Rust crate already provides this capability",
        ))
        .stdout(predicate::str::contains(
            ".github/workflows/ci.yaml:6: developer tooling spawns gh; a Rust crate already provides this capability",
        ))
        .stdout(predicate::str::contains(
            ".pre-commit-config.yaml:2: developer tooling spawns gcloud; a Rust crate already provides this capability",
        ))
        .stdout(predicate::str::contains(
            ".github/actions/unreviewed/action.yaml:4: developer tooling spawns gcloud; a Rust crate already provides this capability",
        ))
        .stderr(predicate::str::is_empty());
}

#[test]
fn crate_process_rejects_python_subprocess_argv() {
    let repository = TempRepo::new();
    repository.write(
        "scripts/developer_tool.py",
        br#"import subprocess as process

github_argv = ["gh", "api", "/user"]
git_argv = ["git", "status", "--short"]
git_command = "git status --short"
process.run(args=github_argv, check=True)
process.check_call(git_argv)
process.run(git_command, shell=True)
"#,
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "developer-tooling-crate-process"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "scripts/developer_tool.py:6: developer tooling spawns gh; a Rust crate already provides this capability",
        ))
        .stdout(predicate::str::contains(
            "scripts/developer_tool.py:7: developer tooling spawns git; a Rust crate already provides this capability",
        ))
        .stdout(predicate::str::contains(
            "scripts/developer_tool.py:8: developer tooling spawns git; a Rust crate already provides this capability",
        ))
        .stderr(predicate::str::is_empty());
}

#[test]
fn rust_owned_python_rejects_retained_developer_prompt() {
    let repository = TempRepo::new();
    write_rust_owned_registry(&repository, "plugin", "read-version");
    repository.write(
        ".claude/skills/larch-size/SKILL.md",
        b"Run `python3 python/cli.py plugin read-version`.\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "developer-tooling-rust-owned-python"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            ".claude/skills/larch-size/SKILL.md:1: developer tooling invokes python/cli.py plugin read-version; command registry marks it Rust-owned",
        ))
        .stderr(predicate::str::is_empty());
}

fn inventory(extra: &str) -> String {
    format!(
        "# Git operation inventory\n\n<!-- git-ownership-matrix:start -->\n```text\nsurface\towner\tissue\toperations\n{extra}```\n<!-- git-ownership-matrix:end -->\n"
    )
}

fn service_inventory(rows: &str) -> String {
    format!(
        "<!-- github-service-ownership:start -->\n```text\noperation\tadapter_owner\tcurrent_owner\tplanning_issues\timplementation_parity\tconsumer_cutover\tpython_removal\tcommands\n{rows}```\n<!-- github-service-ownership:end -->\n"
    )
}

fn closure_registry(rows: &str) -> String {
    format!(
        "schema_version = 2\n\n[[commands]]\ndomain = \"fixture\"\nverb = \"run\"\npython_module = \"fixture\"\npython_function = \"main\"\nmachine_stdout = false\nowner = \"python\"\nimplementation_parity = \"pending\"\nconsumer_cutover = \"pending\"\npython_removal = \"pending\"\nplanning_issue = 7681\n\n{rows}"
    )
}

fn closure_command(
    owner: &str,
    parity: &str,
    cutover: &str,
    removal: &str,
    migration_issue: Option<u64>,
) -> String {
    let migration_issue = migration_issue
        .map(|issue| format!("migration_issue = {issue}\n"))
        .unwrap_or_default();
    format!(
        "[[commands]]\ndomain = \"issue\"\nverb = \"migration-audit\"\npython_module = \"larch.issue.migration_governance\"\npython_function = \"migration_audit_main\"\nmachine_stdout = true\nowner = \"{owner}\"\nimplementation_parity = \"{parity}\"\nconsumer_cutover = \"{cutover}\"\npython_removal = \"{removal}\"\nplanning_issue = 7685\n{migration_issue}\n"
    )
}

fn write_closure_baseline(repository: &TempRepo, registry_rows: &str) {
    repository.write(
        "crates/larch-lint/data/command-registry.toml",
        closure_registry(registry_rows).as_bytes(),
    );
    repository.write(
        "python/larch/cli.py",
        b"_REGISTRY: dict[tuple[str, str], tuple[str, str, bool]] = {\n    (\"fixture\", \"run\"): (\"fixture\", \"main\", False),\n}\n",
    );
    repository.write("hooks/hooks.json", b"{}\n");
    repository.write(
        "docs/github-service-inventory.md",
        service_inventory(
            "issues\tcrates/larch-adapters/src/github_rest.rs\trust\t#7682\tcomplete\tcomplete\tcomplete\tfixture run\n",
        )
        .as_bytes(),
    );
}

#[test]
fn developer_tooling_closure_rejects_unresolved_7685_inventory_row() {
    let repository = TempRepo::new();
    write_closure_baseline(&repository, "");
    repository.write(
        "docs/git-operation-inventory.md",
        inventory("scripts/developer.sh\tlater-domain\t#7685\tstatus\n").as_bytes(),
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "developer-tooling-7685-closure"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "docs/git-operation-inventory.md:1: Git-operation inventory still has unresolved later-domain #7685 row: scripts/developer.sh",
        ))
        .stderr(predicate::str::is_empty());
}

#[test]
fn developer_tooling_closure_allows_other_later_domain_rows() {
    let repository = TempRepo::new();
    write_closure_baseline(&repository, "");
    repository.write(
        "docs/git-operation-inventory.md",
        inventory("python/larch/issue/tool.py\tlater-domain\t#7682\tls-tree\n").as_bytes(),
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "developer-tooling-7685-closure"])
        .assert()
        .success()
        .stdout(predicate::str::is_empty())
        .stderr(predicate::str::is_empty());
}

#[test]
fn developer_tooling_closure_rejects_pending_7685_command_phase() {
    let repository = TempRepo::new();
    write_closure_baseline(
        &repository,
        &closure_command("python", "pending", "pending", "pending", None),
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "developer-tooling-7685-closure"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "planning issue #7685 command issue migration-audit is not Rust-owned",
        ))
        .stdout(predicate::str::contains(
            "planning issue #7685 command issue migration-audit has incomplete implementation parity",
        ))
        .stderr(predicate::str::is_empty());
}

#[test]
fn developer_tooling_closure_rejects_missing_and_umbrella_migration_leaves() {
    let repository = TempRepo::new();
    let missing = closure_command("rust", "complete", "complete", "complete", None);
    let umbrella = closure_command("rust", "complete", "complete", "complete", Some(7685))
        .replace("verb = \"migration-audit\"", "verb = \"migration-report\"");
    write_closure_baseline(&repository, &(missing + &umbrella));
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "developer-tooling-7685-closure"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "planning issue #7685 command issue migration-audit lacks an exact non-umbrella migration leaf",
        ))
        .stdout(predicate::str::contains(
            "planning issue #7685 command issue migration-report lacks an exact non-umbrella migration leaf",
        ))
        .stderr(predicate::str::is_empty());
}

#[test]
fn developer_tooling_closure_rejects_retained_7685_python_module() {
    let repository = TempRepo::new();
    write_closure_baseline(
        &repository,
        &closure_command("rust", "complete", "complete", "complete", Some(8392)),
    );
    repository.write(
        "python/larch/issue/migration_governance.py",
        b"def migration_audit_main(argv: list[str]) -> int:\n    return 0\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "developer-tooling-7685-closure"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "python-entrypoint-still-present issue migration-audit: python/larch/issue/migration_governance.py",
        ))
        .stderr(predicate::str::is_empty());
}

#[test]
fn developer_tooling_closure_rejects_retained_7685_python_registration() {
    let repository = TempRepo::new();
    write_closure_baseline(
        &repository,
        &closure_command("rust", "complete", "complete", "complete", Some(8392)),
    );
    repository.write(
        "python/larch/cli.py",
        b"_REGISTRY: dict[tuple[str, str], tuple[str, str, bool]] = {\n    (\"fixture\", \"run\"): (\"fixture\", \"main\", False),\n    (\"issue\", \"migration-audit\"): (\"larch.issue.migration_governance\", \"migration_audit_main\", True),\n}\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "developer-tooling-7685-closure"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "python-entrypoint-still-present issue migration-audit: python/larch/cli.py",
        ))
        .stderr(predicate::str::is_empty());
}

#[test]
fn developer_tooling_closure_rejects_retained_7685_python_caller() {
    let repository = TempRepo::new();
    write_closure_baseline(
        &repository,
        &closure_command("rust", "complete", "complete", "complete", Some(8392)),
    );
    repository.write(
        "Makefile",
        b"audit:\n\tpython3 python/cli.py issue migration-audit\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "developer-tooling-7685-closure"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "planning issue #7685 command issue migration-audit retains a Python production caller: Makefile",
        ))
        .stderr(predicate::str::is_empty());
}

#[test]
fn developer_tooling_closure_rejects_pending_7685_service_inventory_row() {
    let repository = TempRepo::new();
    write_closure_baseline(&repository, "");
    repository.write(
        "docs/github-service-inventory.md",
        service_inventory(
            "issues\tcrates/larch-adapters/src/github_rest.rs\tpython\t#7685\tpending\tpending\tpending\tfixture run\n",
        )
        .as_bytes(),
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "developer-tooling-7685-closure"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "GitHub service inventory still has incomplete #7685 ownership for operation: issues",
        ))
        .stderr(predicate::str::is_empty());
}

#[test]
fn developer_tooling_closure_allows_a_completed_retired_7685_service_row() {
    let repository = TempRepo::new();
    write_closure_baseline(&repository, "");
    repository.write(
        "docs/github-service-inventory.md",
        service_inventory(
            "legacy-issues\tcrates/larch-adapters/src/github_rest.rs\tretired\t#7685\tnot-applicable\tcomplete\tcomplete\tfixture run\n",
        )
        .as_bytes(),
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "developer-tooling-7685-closure"])
        .assert()
        .success()
        .stdout(predicate::str::is_empty())
        .stderr(predicate::str::is_empty());
}

#[test]
fn retired_module_passes_while_verb_still_registered() {
    let repository = TempRepo::new();
    repository.write(
        "python/larch/cli.py",
        b"_REGISTRY: dict[tuple[str, str], tuple[str, str, bool]] = {\n    (\"fixture\", \"run\"): (\"fixture\", \"main\", False),\n    (\"lint\", \"flat-tests\"): (\"larch.lint.lint_flat_tests\", \"main\", False),\n}\n",
    );
    repository.write(
        "crates/larch-lint/data/python-lint-disposition.tsv",
        b"# verb\tdisposition\ttarget_surface\trationale\nflat-tests\tretire\tpython\tscans python only\n",
    );
    repository.write(
        "python/larch/lint/lint_flat_tests.py",
        b"def main() -> None:\n    return None\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "retired-disposition-module"])
        .assert()
        .success()
        .stdout(predicate::str::is_empty())
        .stderr(predicate::str::is_empty());
}

#[test]
fn retired_module_fails_when_unregistered_module_remains() {
    let repository = TempRepo::new();
    repository.write(
        "python/larch/cli.py",
        b"_REGISTRY: dict[tuple[str, str], tuple[str, str, bool]] = {\n    (\"fixture\", \"run\"): (\"fixture\", \"main\", False),\n}\n",
    );
    repository.write(
        "crates/larch-lint/data/python-lint-disposition.tsv",
        b"# verb\tdisposition\ttarget_surface\trationale\nobsolete-check\tretire\tpython/larch/lint/lint_obsolete_check.py\talready removed from registry\n",
    );
    repository.write(
        "python/larch/lint/lint_obsolete_check.py",
        b"def main() -> None:\n    return None\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "retired-disposition-module"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "retired disposition module still exists for unregistered lint verb obsolete-check: python/larch/lint/lint_obsolete_check.py",
        ))
        .stderr(predicate::str::is_empty());
}
