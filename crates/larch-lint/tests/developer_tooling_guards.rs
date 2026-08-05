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
fn crate_process_passes_with_vendor_and_residual_exceptions() {
    let repository = TempRepo::new();
    repository.write(
        "scripts/residual-bash-paths.txt",
        b"scripts/allowed-gh.sh\n",
    );
    repository.write(
        "scripts/allowed-gh.sh",
        b"#!/usr/bin/env bash\ngh api user\n",
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
