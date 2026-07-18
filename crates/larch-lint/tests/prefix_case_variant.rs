mod support;

use predicates::prelude::*;
use support::TempRepo;

#[test]
fn scans_markdown_and_declared_residual_bash_for_case_variants() {
    let repository = TempRepo::new();
    repository.write("skills/example/SKILL.md", b"Use `[Bug]`.\n");
    repository.write("scripts/example.sh", b"printf '%s\\n' '[bug]'\n");
    repository.write("scripts/residual-bash-paths.txt", b"scripts/example.sh\n");
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "prefix-case-variant"])
        .assert()
        .code(1)
        .stdout(
            "scripts/example.sh:1: matched [bug]; use exact-case [BUG]\n\
             skills/example/SKILL.md:1: matched [Bug]; use exact-case [BUG]\n",
        )
        .stderr(predicate::str::is_empty());
}

#[test]
fn accepts_exact_tokens_and_reasoned_surface_suppressions() {
    let repository = TempRepo::new();
    repository.write(
        "agents/example.md",
        b"Use `[DONE]`. `[Bug]` <!-- lint-prefix-case-variant: ok legacy fixture -->\n",
    );
    repository.write("skills/example.md", b"Keep `[BUG]` exact.\n");
    repository.write(
        ".claude/skills/example.md",
        b"Keep `[STALLED]` and `[IMPLEMENTING]` exact.\n",
    );
    repository.write(
        "scripts/example.sh",
        b"printf '%s\\n' '[bug]' # lint-prefix-case-variant: ok legacy fixture\n",
    );
    repository.write("scripts/residual-bash-paths.txt", b"scripts/example.sh\n");
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "prefix-case-variant"])
        .assert()
        .success()
        .stdout(predicate::str::is_empty())
        .stderr(predicate::str::is_empty());
}

#[test]
fn fails_closed_for_missing_residual_bash_entries() {
    let repository = TempRepo::new();
    repository.write("scripts/residual-bash-paths.txt", b"scripts/missing.sh\n");
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "prefix-case-variant"])
        .assert()
        .code(2)
        .stdout(predicate::str::is_empty())
        .stderr(predicate::str::contains(
            "missing residual bash path: scripts/missing.sh",
        ));
}
