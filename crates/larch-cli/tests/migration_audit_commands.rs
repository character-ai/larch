use assert_cmd::Command;
use predicates::prelude::*;

fn larch() -> Command {
    Command::cargo_bin("larch").expect("larch binary should build")
}

#[test]
fn migration_audit_keeps_its_argparse_help_and_validation_contract() {
    larch()
        .args(["issue", "migration-audit", "--h"])
        .assert()
        .success()
        .stdout(predicate::str::contains(
            "usage: larch issue migration-audit [-h] --repo REPO --chief CHIEF",
        ))
        .stdout(predicate::str::contains(
            "-h, --help            show this help message and exit",
        ))
        .stderr(predicate::str::is_empty());

    larch()
        .args(["issue", "migration-audit", "--help=unexpected"])
        .assert()
        .code(2)
        .stderr(predicate::str::contains(
            "larch issue migration-audit: error: argument -h/--help: ignored explicit argument 'unexpected'",
        ));

    larch()
        .args(["issue", "migration-audit", "-h=unexpected"])
        .assert()
        .code(2)
        .stderr(predicate::str::contains(
            "larch issue migration-audit: error: argument -h/--help: ignored explicit argument 'unexpected'",
        ));

    larch()
        .args([
            "issue",
            "migration-audit",
            "--repo",
            "owner/repo",
            "--chief",
            "bad",
        ])
        .assert()
        .code(2)
        .stderr(predicate::str::contains(
            "larch issue migration-audit: error: argument --chief: invalid int value: 'bad'",
        ));

    larch()
        .args([
            "issue",
            "migration-audit",
            "--repo",
            "not-a-repository",
            "--chief",
            " 1 ",
        ])
        .assert()
        .code(2)
        .stderr(predicate::str::contains(
            "ERROR: migration-audit: --repo must be exactly owner/name",
        ));

    larch()
        .args([
            "issue",
            "migration-audit",
            "--repo",
            "not-a-repository",
            "--chief",
            "1_000",
        ])
        .assert()
        .code(2)
        .stderr(predicate::str::contains(
            "ERROR: migration-audit: --repo must be exactly owner/name",
        ))
        .stderr(predicate::str::contains("invalid int value").not());

    larch()
        .args([
            "issue",
            "migration-audit",
            "--repo",
            "owner/repo",
            "--chief",
            "1",
            "--table-output",
            "stdout",
        ])
        .assert()
        .code(2)
        .stdout(predicate::str::is_empty())
        .stderr(predicate::str::contains(
            "ERROR: migration-audit: --table-output stdout requires --output so stdout stays machine-readable",
        ));
}
