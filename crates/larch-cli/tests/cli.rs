use assert_cmd::Command;
use predicates::prelude::*;

#[test]
fn version_reports_the_workspace_version() {
    Command::cargo_bin("larch")
        .expect("larch binary should build")
        .arg("--version")
        .assert()
        .success()
        .stdout(predicate::eq(format!(
            "larch {}\n",
            env!("CARGO_PKG_VERSION")
        )));
}
