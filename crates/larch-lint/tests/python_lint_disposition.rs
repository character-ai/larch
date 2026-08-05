mod support;

use std::fmt::Write as _;

use predicates::prelude::*;
use support::TempRepo;

const LEDGER: &str = "crates/larch-lint/data/python-lint-disposition.tsv";
const CLI: &str = "python/larch/cli.py";
const MAKEFILE: &str = "Makefile";

fn run(repository: &TempRepo) -> assert_cmd::assert::Assert {
    TempRepo::command_from(repository.path())
        .args(["rule", "python-lint-disposition"])
        .assert()
}

fn write_cli(repository: &TempRepo, verbs: &[&str]) {
    let mut body = String::from(
        "_REGISTRY: dict[tuple[str, str], tuple[str, str, bool]] = {\n    (\"fixture\", \"run\"): (\"fixture\", \"main\", False),\n",
    );
    for verb in verbs {
        let _ = writeln!(
            body,
            "    (\"lint\", \"{verb}\"): (\"larch.lint.lint_{}\", \"main\", False),",
            verb.replace('-', "_")
        );
    }
    body.push_str("}\n");
    repository.write(CLI, body.as_bytes());
}

fn write_ledger(repository: &TempRepo, rows: &[&str]) {
    let mut body = String::from("# verb\tdisposition\ttarget_surface\trationale\n");
    for row in rows {
        body.push_str(row);
        body.push('\n');
    }
    repository.write(LEDGER, body.as_bytes());
}

fn write_makefile(repository: &TempRepo, checks: &str) {
    repository.write(
        MAKEFILE,
        format!("PY_LINT_FAST_CHECKS := {checks}\nPY_LINT_FAST_CHECKS_SHARD_1 := {checks}\n")
            .as_bytes(),
    );
}

#[test]
fn clean_matching_ledger_passes() {
    let repository = TempRepo::new();
    write_cli(&repository, &["skill-run-lifecycle", "complexity-baseline"]);
    write_ledger(
        &repository,
        &[
            "complexity-baseline\tretire\tpython\tscans python only",
            "skill-run-lifecycle\tport\tskills\tscans skill Markdown",
        ],
    );
    write_makefile(&repository, "complexity-baseline skill-run-lifecycle");
    repository.write("python/keep.txt", b"present\n");
    repository.write("skills/keep.txt", b"present\n");
    repository.commit_all();

    run(&repository)
        .success()
        .stdout(predicate::str::is_empty())
        .stderr(predicate::str::is_empty());
}

#[test]
fn header_only_ledger_without_python_lint_targets_passes() {
    let repository = TempRepo::new();
    write_cli(&repository, &[]);
    write_ledger(&repository, &[]);
    repository.write(MAKEFILE, b"py-lint:\n\tcd python && ruff check .\n");
    repository.commit_all();

    run(&repository)
        .success()
        .stdout(predicate::str::is_empty())
        .stderr(predicate::str::is_empty());
}

#[test]
fn fails_when_registered_verb_has_no_row() {
    let repository = TempRepo::new();
    write_cli(&repository, &["complexity-baseline", "keyword-only"]);
    write_ledger(
        &repository,
        &["complexity-baseline\tretire\tpython\tscans python only"],
    );
    repository.write("python/keep.txt", b"present\n");
    repository.commit_all();

    run(&repository)
        .code(1)
        .stdout(predicate::str::contains(
            "missing disposition row for registered lint verb keyword-only",
        ))
        .stderr(predicate::str::is_empty());
}

#[test]
fn fails_when_row_names_unregistered_verb() {
    let repository = TempRepo::new();
    write_cli(&repository, &["complexity-baseline"]);
    write_ledger(
        &repository,
        &[
            "complexity-baseline\tretire\tpython\tscans python only",
            "obsolete-linter\tretire\tpython\tstale row",
        ],
    );
    repository.write("python/keep.txt", b"present\n");
    repository.commit_all();

    run(&repository)
        .code(1)
        .stdout(predicate::str::contains(
            "disposition row names unregistered lint verb obsolete-linter",
        ))
        .stderr(predicate::str::is_empty());
}

#[test]
fn fails_when_retire_row_stays_in_fast_checks_after_surface_gone() {
    let repository = TempRepo::new();
    write_cli(&repository, &["complexity-baseline"]);
    write_ledger(
        &repository,
        &["complexity-baseline\tretire\tgone-python-surface\tscans python only"],
    );
    write_makefile(&repository, "ruff complexity-baseline");
    repository.commit_all();

    run(&repository)
        .code(1)
        .stdout(predicate::str::contains(
            "retire disposition for complexity-baseline remains in PY_LINT_FAST_CHECKS after target surface",
        ))
        .stderr(predicate::str::is_empty());
}

#[test]
fn retire_row_with_present_surface_may_remain_in_fast_checks() {
    let repository = TempRepo::new();
    write_cli(&repository, &["complexity-baseline"]);
    write_ledger(
        &repository,
        &["complexity-baseline\tretire\tpython\tscans python only"],
    );
    write_makefile(&repository, "complexity-baseline");
    repository.write("python/keep.txt", b"present\n");
    repository.commit_all();

    run(&repository)
        .success()
        .stdout(predicate::str::is_empty())
        .stderr(predicate::str::is_empty());
}
