mod support;

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
