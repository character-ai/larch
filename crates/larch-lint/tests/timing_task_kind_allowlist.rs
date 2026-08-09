mod support;

use predicates::prelude::*;
use support::TempRepo;

fn write_allowlist(repository: &TempRepo) {
    repository.write(
        "crates/larch-core/src/report/timing.rs",
        b"pub const TIMING_TASK_KINDS_ALLOWED: [&str; 1] = [\"known-kind\"];\n",
    );
}

#[test]
fn timing_task_kind_rule_covers_skill_text_rust_commands_and_clap_defaults() {
    let repository = TempRepo::new();
    write_allowlist(&repository);
    repository.write(
        "skills/example/SKILL.md",
        b"scripts/larch.sh agent launch-review --timing-task-kind missing-markdown\n",
    );
    repository.write(
        "skills/example/scripts/launch.sh",
        b"scripts/larch.sh agent launch-review --timing-task-kind missing-shell\n",
    );
    repository.write(
        "skills/example/scripts/test-launch.sh",
        b"scripts/larch.sh agent launch-review --timing-task-kind ignored-test\n",
    );
    repository.write(
        "crates/example/src/timing.rs",
        b"use clap::Parser;\nuse std::process::Command;\nconst ARGS: [&str; 2] = [\"--timing-task-kind\", \"missing-array\"];\n#[derive(Parser)]\nstruct Cli {\n    #[arg(long = \"timing-task-kind\", default_value = \"missing-default\")]\n    timing_task_kind: String,\n}\nfn run() { Command::new(\"runner\").arg(\"--timing-task-kind\").arg(\"missing-builder\"); }\nfn typed() { TimingTaskKind::new(\"missing-constructor\"); TimingTaskKind::new(\"known-kind\"); }\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "timing-task-kind-allowlist"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains("skills/example/SKILL.md:1: missing TIMING_TASK_KINDS_ALLOWED entry for missing-markdown"))
        .stdout(predicate::str::contains("skills/example/scripts/launch.sh:1: missing TIMING_TASK_KINDS_ALLOWED entry for missing-shell"))
        .stdout(predicate::str::contains("crates/example/src/timing.rs:3: missing TIMING_TASK_KINDS_ALLOWED entry for missing-array"))
        .stdout(predicate::str::contains("crates/example/src/timing.rs:6: missing TIMING_TASK_KINDS_ALLOWED entry for missing-default"))
        .stdout(predicate::str::contains("crates/example/src/timing.rs:9: missing TIMING_TASK_KINDS_ALLOWED entry for missing-builder"))
        .stdout(predicate::str::contains("crates/example/src/timing.rs:10: missing TIMING_TASK_KINDS_ALLOWED entry for missing-constructor"))
        .stdout(predicate::str::contains("ignored-test").not());
}

#[test]
fn timing_task_kind_rule_accepts_known_constants_and_inferred_clap_long_names() {
    let repository = TempRepo::new();
    write_allowlist(&repository);
    repository.write(
        "crates/example/src/timing.rs",
        b"use clap::Parser;\nuse std::process::Command;\nconst KIND: &str = \"known-kind\";\n#[derive(Parser)]\nstruct Cli {\n    #[arg(long, default_value = \"known-kind\")]\n    timing_task_kind: String,\n}\nfn run() { Command::new(\"runner\").args([\"--timing-task-kind\", KIND]); TimingTaskKind::new(KIND); }\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "timing-task-kind-allowlist"])
        .assert()
        .success()
        .stdout("")
        .stderr("");
}

#[test]
fn timing_task_kind_rule_ignores_bare_long_defaults_on_unrelated_fields() {
    let repository = TempRepo::new();
    write_allowlist(&repository);
    repository.write(
        "crates/example/src/registry.rs",
        b"use clap::Parser;\n#[derive(Parser)]\nstruct Cli {\n    #[arg(long, default_value = \"kv\")]\n    kind: String,\n}\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "timing-task-kind-allowlist"])
        .assert()
        .success()
        .stdout("")
        .stderr("");
}
