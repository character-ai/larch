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

#[test]
fn timing_task_kind_rule_covers_python_argv_and_supported_argparse_defaults() {
    let repository = TempRepo::new();
    write_allowlist(&repository);
    repository.write(
        "python/larch/launch.py",
        br#"import os

list_argv = ["--timing-task-kind", "missing-list"]
tuple_argv = ("--timing-task-kind", "missing-tuple")
parser.add_argument("--timing-task-kind", default="missing-default")
parser.add_argument("--timing-task-kind", default=os.environ.get("KIND", "missing-get"))
parser.add_argument("--timing-task-kind", default=os.getenv("KIND", "") or "missing-or")
parser.add_argument("--timing-task-kind", default="missing-yes" if enabled else "missing-no")
known = ["--timing-task-kind", "known-kind"]
dynamic = ["--timing-task-kind", dynamic_kind]
parser.add_argument("--timing-task-kind", default=dynamic_default)
"#,
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "timing-task-kind-allowlist"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "python/larch/launch.py:3: missing TIMING_TASK_KINDS_ALLOWED entry for missing-list",
        ))
        .stdout(predicate::str::contains(
            "python/larch/launch.py:4: missing TIMING_TASK_KINDS_ALLOWED entry for missing-tuple",
        ))
        .stdout(predicate::str::contains(
            "python/larch/launch.py:5: missing TIMING_TASK_KINDS_ALLOWED entry for missing-default",
        ))
        .stdout(predicate::str::contains(
            "python/larch/launch.py:6: missing TIMING_TASK_KINDS_ALLOWED entry for missing-get",
        ))
        .stdout(predicate::str::contains(
            "python/larch/launch.py:7: missing TIMING_TASK_KINDS_ALLOWED entry for missing-or",
        ))
        .stdout(predicate::str::contains(
            "python/larch/launch.py:8: missing TIMING_TASK_KINDS_ALLOWED entry for missing-yes",
        ))
        .stdout(predicate::str::contains(
            "python/larch/launch.py:8: missing TIMING_TASK_KINDS_ALLOWED entry for missing-no",
        ))
        .stdout(predicate::str::contains("known-kind").not())
        .stdout(predicate::str::contains(
            "python/larch/launch.py:10: timing task kind must resolve to a static allow-listed literal",
        ))
        .stdout(predicate::str::contains(
            "python/larch/launch.py:11: timing task kind must resolve to a static allow-listed literal",
        ));
}

#[test]
fn timing_task_kind_rule_accepts_each_supported_python_syntax_form() {
    let repository = TempRepo::new();
    write_allowlist(&repository);
    repository.write(
        "python/larch/launch.py",
        br#"import os

list_argv = ["--timing-task-kind", "known-kind"]
tuple_argv = ("--timing-task-kind", "known-kind")
parser.add_argument("--timing-task-kind", default="known-kind")
parser.add_argument("--timing-task-kind", default=os.environ.get("KIND", "known-kind"))
parser.add_argument("--timing-task-kind", default=os.getenv("KIND", "") or "known-kind")
parser.add_argument("--timing-task-kind", default="known-kind" if enabled else "known-kind")
"#,
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
fn timing_task_kind_rule_preserves_python_exclusions() {
    let repository = TempRepo::new();
    write_allowlist(&repository);
    for path in [
        "python/larch/test_launch.py",
        "python/larch/test-fixture.py",
        "python/larch/test_fixtures/launch.py",
        "python/larch/larch-logs/launch.py",
        "python/other/launch.py",
    ] {
        repository.write(path, b"argv = ['--timing-task-kind', 'ignored-kind']\n");
    }
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "timing-task-kind-allowlist"])
        .assert()
        .success()
        .stdout("")
        .stderr("");
}

#[test]
fn timing_task_kind_rule_rejects_malformed_python_source() {
    let repository = TempRepo::new();
    write_allowlist(&repository);
    repository.write(
        "python/larch/launch.py",
        b"argv = ['--timing-task-kind', 'missing-kind'\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "timing-task-kind-allowlist"])
        .assert()
        .code(2)
        .stdout("")
        .stderr(predicate::str::contains(
            "python/larch/launch.py: invalid Python syntax",
        ));
}
