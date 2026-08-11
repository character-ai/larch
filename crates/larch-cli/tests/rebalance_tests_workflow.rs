use assert_cmd::Command;
use predicates::prelude::*;

#[test]
fn run_help_exposes_the_checked_orchestration_boundary() {
    Command::cargo_bin("larch")
        .expect("larch binary should build")
        .args(["rebalance-tests", "run", "--help"])
        .assert()
        .success()
        .stdout(predicate::str::contains(
            "checked repository, artifact, pull-request",
        ));
}
