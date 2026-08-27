use crate::support;

use predicates::prelude::*;
use support::TempRepo;

const MESSAGE: &str = "production runtime must use scripts/larch.sh; cargo and target-directory execution are development-only";

#[test]
fn production_cargo_run_rejects_every_runtime_surface() {
    let repository = TempRepo::new();
    repository.write(
        "skills/example/SKILL.md",
        b"```bash\n\"cargo\" \\\n  install larch-cli\n```\n",
    );
    repository.write(
        "agents/direct.md",
        b"Run `target\\debug\\larch.exe git clean-tree`.\n",
    );
    repository.write(
        "hooks/hooks.json",
        br#"{"hooks":{"PreToolUse":[{"hooks":[{"type":"command","command":"cargo run --locked --package larch-cli"}]}]}}
"#,
    );
    repository.write(
        "scripts/direct.sh",
        b"#!/usr/bin/env bash\nenv LARCH_MODE=prod ./target/release/larch git clean-tree\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "production-cargo-run"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(format!(
            "skills/example/SKILL.md:2: {MESSAGE}"
        )))
        .stdout(predicate::str::contains(format!(
            "agents/direct.md:1: {MESSAGE}"
        )))
        .stdout(predicate::str::contains(format!(
            "hooks/hooks.json:1: {MESSAGE}"
        )))
        .stdout(predicate::str::contains(format!(
            "scripts/direct.sh:2: {MESSAGE}"
        )))
        .stderr("");
}

#[test]
fn production_cargo_run_rejects_multiline_markdown_commands() {
    let repository = TempRepo::new();
    repository.write(
        "agents/multiline.md",
        b"```console\n$ cargo \\\n  run --locked\n```\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "production-cargo-run"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(format!(
            "agents/multiline.md:2: {MESSAGE}"
        )))
        .stderr("");
}

#[test]
fn production_cargo_run_rejects_case_insensitive_markdown_and_nonrelease_commands() {
    let repository = TempRepo::new();
    repository.write("agents/direct.MD", b"Use `cargo install larch-cli`.\n");
    repository.write(
        ".claude/skills/release/SKILL.md",
        b"```bash\ncargo install larch-cli\n```\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "production-cargo-run"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(format!(
            "agents/direct.MD:1: {MESSAGE}"
        )))
        .stdout(predicate::str::contains(format!(
            ".claude/skills/release/SKILL.md:2: {MESSAGE}"
        )))
        .stderr("");
}

#[test]
fn production_cargo_run_allows_prose_comments_and_nonruntime_surfaces() {
    let repository = TempRepo::new();
    repository.write(
        "skills/example/SKILL.md",
        b"`cargo run` is forbidden in production.\nDo not run `target/debug/larch`.\n```text\ncargo install larch-cli\n```\n",
    );
    repository.write(
        "scripts/prose.sh",
        b"#!/usr/bin/env bash\n# cargo run is forbidden\nprintf '%s\\n' 'target/release/larch is development-only'\n",
    );
    repository.write(
        "docs/development.md",
        b"```bash\ncargo run --package larch-cli\n```\n",
    );
    repository.write(
        ".github/workflows/ci.yaml",
        b"run: cargo run --locked --package larch-cli -- release plugin-runtime\n",
    );
    repository.write("Makefile", b"install:\n\tcargo install cargo-deny\n");
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "production-cargo-run"])
        .assert()
        .success()
        .stdout("")
        .stderr("");
}

#[test]
fn production_cargo_run_rejects_release_step7_cargo_execution() {
    let repository = TempRepo::new();
    repository.write(
        ".claude/skills/release/SKILL.md",
        b"```bash\ncargo run --quiet --locked --package larch-cli -- upgrade-larch release-step7-root\n```\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "production-cargo-run"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(format!(
            ".claude/skills/release/SKILL.md:2: {MESSAGE}"
        )))
        .stderr("");
}

#[test]
fn production_cargo_run_allows_only_recognized_fixture_paths() {
    let repository = TempRepo::new();
    repository.write(
        "skills/example/scripts/test-runtime.md",
        b"```bash\ncargo run --package larch-cli\n```\n",
    );
    repository.write(
        "skills/example/scripts/fixtures/runtime.md",
        b"Run `target/debug/larch fixture`.\n",
    );
    repository.write(
        "scripts/test-runtime.sh",
        b"#!/usr/bin/env bash\ncargo install larch-cli\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "production-cargo-run"])
        .assert()
        .success()
        .stdout("")
        .stderr("");
}
