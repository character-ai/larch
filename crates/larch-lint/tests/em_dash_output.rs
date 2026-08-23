use crate::support;

use predicates::prelude::*;
use support::TempRepo;

#[test]
fn scans_markdown_templates_and_rust_output_sinks() {
    let repository = TempRepo::new();
    repository.write(
        "skills/example/SKILL.md",
        "Print: `bad — template`\n".as_bytes(),
    );
    repository.write(
        "src/lib.rs",
        "pub fn emit() {\n    println!(\"bad — output\");\n}\n".as_bytes(),
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "em-dash-output"])
        .assert()
        .code(1)
        .stdout(
            "skills/example/SKILL.md:1: em dash in markdown print literal\n\
             src/lib.rs:2: em dash in Rust output literal\n",
        )
        .stderr(predicate::str::is_empty());
}

#[test]
fn ignores_non_output_rust_strings_and_markdown_quotes_and_fences() {
    let repository = TempRepo::new();
    repository.write(
        "agents/example.md",
        "> Print: `quoted — template`\n```\n⏩ fenced — output\n```\n".as_bytes(),
    );
    repository.write(
        "src/lib.rs",
        "pub fn value() -> &'static str { \"allowed — value\" }\n".as_bytes(),
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "em-dash-output"])
        .assert()
        .success()
        .stdout(predicate::str::is_empty())
        .stderr(predicate::str::is_empty());
}

#[test]
fn scans_python_output_sinks_and_breadcrumb_aliases() {
    let repository = TempRepo::new();
    repository.write(
        "python/larch/example.py",
        "from larch.core import logging_util\n\
         writer = logging_util.BreadcrumbWriter()\n\
         print(f\"bad — {writer}\")\n\
         logging_util.emit(\"bad — logging\")\n\
         writer.emit(\"bad — breadcrumb\")\n\
         value = \"allowed — value\"\n"
            .as_bytes(),
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "em-dash-output"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "python/larch/example.py:3: em dash in Python output literal",
        ))
        .stdout(predicate::str::contains(
            "python/larch/example.py:4: em dash in Python output literal",
        ))
        .stdout(predicate::str::contains(
            "python/larch/example.py:5: em dash in Python output literal",
        ))
        .stdout(predicate::str::contains("python/larch/example.py:6:").not());
}

#[test]
fn malformed_python_suppressions_fail_closed_even_without_an_em_dash() {
    let repository = TempRepo::new();
    repository.write(
        "python/larch/example.py",
        b"value = \"allowed\"  # lint-em-dash-output: ok\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "em-dash-output"])
        .assert()
        .code(2)
        .stderr(predicate::str::contains("lacks a reason"));
}
