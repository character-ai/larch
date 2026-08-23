use crate::support;

use support::TempRepo;

fn prepare_repository(repository: &TempRepo) {
    repository.write(
        "crates/larch-lint/migration-ledger/subprocess-via-runner.toml",
        b"rule = \"subprocess-via-runner\"\n",
    );
    repository.write(
        "crates/larch-lint/migration-ledger/gh-argv-literal.toml",
        b"rule = \"gh-argv-literal\"\n",
    );
}

#[test]
fn process_rule_rejects_direct_standard_process_construction() {
    let repository = TempRepo::new();
    prepare_repository(&repository);
    repository.write(
        "crates/larch-lint/src/direct.rs",
        b"use std::process::Command;\nfn run() { Command::new(\"git\"); }\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "subprocess-via-runner"])
        .assert()
        .code(1)
        .stdout("crates/larch-lint/src/direct.rs:2: calls process Command::new; route through the shared runner\n")
        .stderr("");
}

#[test]
fn process_rule_allows_the_shared_runner_owner_and_reasoned_suppression() {
    let repository = TempRepo::new();
    prepare_repository(&repository);
    repository.write(
        "crates/larch-adapters/src/process.rs",
        b"use std::process::Command;\nfn run() { Command::new(\"git\"); }\n",
    );
    repository.write(
        "crates/larch-lint/src/suppressed.rs",
        b"use std::process::Command;\nfn run() { Command::new(\"git\"); } // lint-subprocess-via-runner: ok fixture exercises the documented escape hatch\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "subprocess-via-runner"])
        .assert()
        .success()
        .stdout("")
        .stderr("");
}

#[test]
fn process_rule_rejects_direct_tokio_process_construction() {
    let repository = TempRepo::new();
    prepare_repository(&repository);
    repository.write(
        "crates/larch-core/src/direct.rs",
        b"use tokio::process::Command;\nfn run() { Command::new(\"git\"); }\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "subprocess-via-runner"])
        .assert()
        .code(1)
        .stdout("crates/larch-core/src/direct.rs:2: calls process Command::new; route through the shared runner\n")
        .stderr("");
}

#[test]
fn missing_process_suppression_reason_is_a_tool_error() {
    let repository = TempRepo::new();
    prepare_repository(&repository);
    repository.write(
        "crates/larch-lint/src/direct.rs",
        b"use std::process::Command;\nfn run() { Command::new(\"git\"); } // lint-subprocess-via-runner: ok\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "subprocess-via-runner"])
        .assert()
        .code(2)
        .stdout("")
        .stderr("larch-lint: error: suppression lint-subprocess-via-runner lacks a reason\n");
}

#[test]
fn github_rule_rejects_raw_gh_but_allows_its_owner_and_reasoned_suppression() {
    let repository = TempRepo::new();
    prepare_repository(&repository);
    repository.write(
        "crates/larch-lint/src/direct.rs",
        b"use std::process::Command as ProcessCommand;\nfn run() { ProcessCommand::new(\"gh\").arg(\"issue\"); }\n",
    );
    repository.write(
        "crates/larch-lint/src/git/gh.rs",
        b"use std::process::Command;\nfn run() { Command::new(\"gh\"); }\n",
    );
    repository.write(
        "crates/larch-lint/tests/fixture.rs",
        b"use std::process::Command;\nfn run() { Command::new(\"gh\"); } // lint-gh-argv-literal: ok fixture asserts raw argv policy\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "gh-argv-literal"])
        .assert()
        .code(1)
        .stdout("crates/larch-lint/src/direct.rs:2: constructs a raw gh command; use the GitHub wrapper\n")
        .stderr("");
}

#[test]
fn missing_github_suppression_reason_is_a_tool_error() {
    let repository = TempRepo::new();
    prepare_repository(&repository);
    repository.write(
        "crates/larch-lint/src/direct.rs",
        b"use std::process::Command;\nfn run() { Command::new(\"gh\"); } // lint-gh-argv-literal: ok\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "gh-argv-literal"])
        .assert()
        .code(2)
        .stdout("")
        .stderr("larch-lint: error: suppression lint-gh-argv-literal lacks a reason\n");
}
