use assert_cmd::Command;
use std::{fs, path::Path};
use tempfile::TempDir;

fn larch() -> Command {
    Command::cargo_bin("larch").expect("larch binary should build")
}

#[test]
fn pack_command_emits_stable_lpt_json() {
    larch()
        .args(["test-shard", "pack", "--n-shards", "2"])
        .write_stdin(
            r#"[
  {"target":"test-a","seconds":10.0},
  {"target":"test-b","seconds":8.0},
  {"target":"test-c","seconds":6.0},
  {"target":"test-d","seconds":4.0}
]"#,
        )
        .assert()
        .success()
        .stdout("{\"1\":[\"test-a\",\"test-d\"],\"2\":[\"test-b\",\"test-c\"]}\n")
        .stderr("");
}

#[test]
fn pack_command_accepts_json_file_input() {
    let temporary = TempDir::new().expect("temporary directory");
    let input = temporary.path().join("timings.json");
    fs::write(
        &input,
        r#"[{"target":"test-a","seconds":3.5},{"target":"test-b","seconds":1.0}]"#,
    )
    .expect("write timings");

    larch()
        .args([
            "test-shard",
            "pack",
            "--n-shards",
            "2",
            "--input",
            input.to_str().expect("UTF-8 path"),
        ])
        .assert()
        .success()
        .stdout("{\"1\":[\"test-a\"],\"2\":[\"test-b\"]}\n")
        .stderr("");
}

#[test]
fn pack_command_keeps_affinity_groups_together() {
    larch()
        .args([
            "test-shard",
            "pack",
            "--n-shards",
            "2",
            "--fixed-startup-seconds",
            "7",
        ])
        .write_stdin(
            r#"[
  {"target":"test-compile-a","seconds":9.0,"affinity_group":"cargo","affinity_setup_seconds":12.0},
  {"target":"test-compile-b","seconds":1.0,"affinity_group":"cargo","affinity_setup_seconds":12.0},
  {"target":"test-independent","seconds":11.0}
]"#,
        )
        .assert()
        .success()
        .stdout("{\"1\":[\"test-compile-a\",\"test-compile-b\"],\"2\":[\"test-independent\"]}\n")
        .stderr("");
}

#[test]
fn makefile_commands_preserve_single_line_rules() {
    let temporary = TempDir::new().expect("temporary directory");
    let makefile = temporary.path().join("Makefile");
    fs::write(
        &makefile,
        concat!(
            ".PHONY: test-harnesses-1 test-harnesses-2\n",
            "test-harnesses-1: test-alpha test-beta\n",
            "test-harnesses-2: test-gamma\n",
            "test-alpha:\n\ttrue\n",
        ),
    )
    .expect("write Makefile");
    let path = makefile.to_str().expect("UTF-8 path");

    larch()
        .args(["test-shard", "read-makefile", "--path", path])
        .assert()
        .success()
        .stdout("{\"1\":[\"test-alpha\",\"test-beta\"],\"2\":[\"test-gamma\"]}\n")
        .stderr("");

    larch()
        .args(["test-shard", "write-makefile", "--path", path])
        .write_stdin(r#"{"1":["test-gamma"]}"#)
        .assert()
        .success()
        .stdout("")
        .stderr("");

    assert_eq!(
        fs::read_to_string(makefile).expect("read rewritten Makefile"),
        concat!(
            ".PHONY: test-harnesses-1 test-harnesses-2\n",
            "test-harnesses-1: test-gamma\n",
            "test-harnesses-2: test-gamma\n",
            "test-alpha:\n\ttrue\n",
        )
    );
}

#[test]
fn current_makefile_shard_lines_round_trip_byte_for_byte() {
    let repository_root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let source = repository_root.join("Makefile");
    let expected = fs::read(&source).expect("read repository Makefile");
    let temporary = TempDir::new().expect("temporary directory");
    let makefile = temporary.path().join("Makefile");
    fs::write(&makefile, &expected).expect("copy Makefile");
    let path = makefile.to_str().expect("UTF-8 path");

    let output = larch()
        .args(["test-shard", "read-makefile", "--path", path])
        .output()
        .expect("read shard lines");
    assert!(
        output.status.success(),
        "read-makefile failed: {}",
        String::from_utf8_lossy(&output.stderr)
    );

    larch()
        .args(["test-shard", "write-makefile", "--path", path])
        .write_stdin(output.stdout)
        .assert()
        .success()
        .stdout("")
        .stderr("");

    assert_eq!(
        fs::read(makefile).expect("read rewritten Makefile"),
        expected
    );
}
