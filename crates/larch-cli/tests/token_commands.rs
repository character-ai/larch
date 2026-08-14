//! Integration coverage for the Rust-owned `token` verbs.

use std::{fs, path::PathBuf, process::Output};

use assert_cmd::Command as AssertCommand;

struct Fixture {
    _directory: tempfile::TempDir,
    tmpdir: PathBuf,
}

impl Fixture {
    fn new() -> Self {
        let directory = tempfile::tempdir().expect("temporary root should create");
        let tmpdir =
            fs::canonicalize(directory.path()).expect("temporary root should canonicalize");
        Self {
            _directory: directory,
            tmpdir,
        }
    }

    fn ledger(&self) -> PathBuf {
        self.tmpdir.join("token-ledger.jsonl")
    }

    fn run(&self, arguments: &[&str]) -> Output {
        let mut command = AssertCommand::cargo_bin("larch").expect("larch binary should build");
        command
            .current_dir(&self.tmpdir)
            .env("TMPDIR", &self.tmpdir)
            .env("IMPLEMENT_TMPDIR", &self.tmpdir)
            .env("LARCH_TOKEN_LEDGER", self.ledger())
            .env_remove("DESIGN_TMPDIR")
            .env_remove("RESEARCH_TMPDIR")
            .env_remove("SESSION_ENV_PATH")
            .env_remove("LARCH_TOKEN_SESSION_ID")
            .arg("token")
            .args(arguments);
        command.output().expect("token command should launch")
    }
}

fn stdout(output: &Output) -> String {
    String::from_utf8_lossy(&output.stdout).into_owned()
}

fn stderr(output: &Output) -> String {
    String::from_utf8_lossy(&output.stderr).into_owned()
}

#[test]
fn mark_writes_one_jsonl_line() {
    let fixture = Fixture::new();
    let output = fixture.run(&["mark", "Step 3 — checks"]);
    assert!(output.status.success(), "{}", stderr(&output));
    let text = fs::read_to_string(fixture.ledger()).expect("ledger should exist");
    let lines: Vec<&str> = text.lines().collect();
    assert_eq!(lines.len(), 1);
    assert!(lines[0].contains("\"type\":\"mark\""), "{}", lines[0]);
    assert!(
        lines[0].contains("\"step\":\"Step 3 \\u2014 checks\""),
        "{}",
        lines[0]
    );
}

#[test]
fn record_vendor_rejects_reserved_claude() {
    let fixture = Fixture::new();
    let output = fixture.run(&[
        "record-vendor",
        "claude",
        "input=1",
        "output=0",
        "cache_read=0",
        "cache_create=0",
        "total=1",
        "raw=claude_main",
    ]);
    assert_eq!(output.status.code(), Some(1));
    assert!(stderr(&output).contains("reserved"), "{}", stderr(&output));
    assert!(!fixture.ledger().exists());
}

#[test]
fn dump_prints_path_and_contents() {
    let fixture = Fixture::new();
    assert!(fixture.run(&["mark", "Step 1"]).status.success());
    let output = fixture.run(&["dump"]);
    assert!(output.status.success(), "{}", stderr(&output));
    let text = stdout(&output);
    assert!(
        text.lines()
            .next()
            .is_some_and(|line| line.contains("token-ledger.jsonl")),
        "{text}"
    );
    assert!(text.contains("\"type\":\"mark\""), "{text}");
}

#[test]
fn lane_write_and_lane_report_roundtrip_under_tmp() {
    let fixture = Fixture::new();
    let dir = PathBuf::from("/tmp").join(format!(
        "larch-token-lane-{}",
        fixture
            .tmpdir
            .file_name()
            .and_then(|n| n.to_str())
            .unwrap_or("case")
    ));
    let _ = fs::remove_dir_all(&dir);
    fs::create_dir_all(&dir).expect("lane dir");
    let write = fixture.run(&[
        "lane-write",
        "--dir",
        dir.to_str().expect("utf8"),
        "--phase",
        "research",
        "--lane",
        "architecture",
        "--tool",
        "claude",
        "--total-tokens",
        "42",
    ]);
    assert!(write.status.success(), "{}", stderr(&write));
    let report = fixture.run(&["lane-report", "--dir", dir.to_str().expect("utf8")]);
    let _ = fs::remove_dir_all(&dir);
    assert!(report.status.success(), "{}", stderr(&report));
    let body = stdout(&report);
    assert!(body.contains("Token Spend"), "{body}");
    assert!(body.contains("total=42"), "{body}");
    assert!(body.contains("Research phase"), "{body}");
}

#[test]
fn append_record_writes_ndjson() {
    let fixture = Fixture::new();
    let sidecar = fixture.tmpdir.join("usage.token-record");
    fs::write(
        &sidecar,
        "TOOL=codex\nINPUT=1\nOUTPUT=2\nCACHE_READ=0\nCACHE_CREATE=0\nTOTAL=3\nRAW=codex_test\n",
    )
    .expect("sidecar");
    let output = fixture.run(&[
        "append-record",
        "--input",
        sidecar.to_str().expect("utf8"),
        "--tmpdir",
        fixture.tmpdir.to_str().expect("utf8"),
    ]);
    assert!(output.status.success(), "{}", stderr(&output));
    let ndjson = fixture.tmpdir.join("token-report.ndjson");
    let text = fs::read_to_string(ndjson).expect("ndjson");
    assert!(text.contains("codex"), "{text}");
    assert!(
        text.contains("\"total\":3") || text.contains("total"),
        "{text}"
    );
}

#[test]
fn dump_refuses_etc_passwd_style_ledger() {
    let fixture = Fixture::new();
    let output = fixture.run(&["dump", "--ledger", "/etc/passwd"]);
    assert_eq!(output.status.code(), Some(1));
    assert!(
        stderr(&output).contains("token dump:"),
        "{}",
        stderr(&output)
    );
}
