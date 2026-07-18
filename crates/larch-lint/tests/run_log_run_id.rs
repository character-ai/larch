mod support;

use predicates::prelude::*;
use support::TempRepo;

fn run(repository: &TempRepo) -> assert_cmd::assert::Assert {
    TempRepo::command_from(repository.path())
        .args(["rule", "run-log-run-id"])
        .assert()
}

#[test]
fn rejects_committed_placeholder_run_log_paths() {
    let repository = TempRepo::new();
    repository.write("larch-logs/implement/run-1/report.md", b"report\n");
    repository.write("larch-logs/design/run-42/summary.md", b"summary\n");
    repository.commit_all();

    run(&repository)
        .code(1)
        .stdout(predicate::str::contains(
            "larch-logs/implement/run-1/report.md:1:",
        ))
        .stdout(predicate::str::contains(
            "larch-logs/design/run-42/summary.md:1:",
        ));
}

#[test]
fn accepts_unique_and_untracked_run_log_paths() {
    let repository = TempRepo::new();
    repository.write(
        "larch-logs/review/AA7794CE-3D50-48C5-8A12-6196F9912345/report.md",
        b"report\n",
    );
    repository.commit_all();
    repository.write("larch-logs/review/run-1/untracked.md", b"untracked\n");

    run(&repository)
        .success()
        .stdout(predicate::str::is_empty())
        .stderr(predicate::str::is_empty());
}
