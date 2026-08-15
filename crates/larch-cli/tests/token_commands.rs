//! Integration coverage for the Rust-owned `token` verbs.

use std::{
    fs,
    path::{Path, PathBuf},
    process::{Command as ProcessCommand, Output},
};

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

struct MeasurementFixture {
    _directory: tempfile::TempDir,
    root: PathBuf,
    home: PathBuf,
    state: PathBuf,
}

impl MeasurementFixture {
    fn new() -> Self {
        let directory = tempfile::tempdir().expect("temporary root should create");
        let root = directory.path().join("repository");
        let home = directory.path().join("home");
        let state = directory.path().join("state");
        fs::create_dir_all(root.join("docs")).expect("fixture repository");
        fs::create_dir_all(&home).expect("fixture home");
        fs::create_dir_all(&state).expect("fixture state home");
        run_git(&root, &["init", "-b", "main"]);
        run_git(&root, &["config", "user.email", "test@example.com"]);
        run_git(&root, &["config", "user.name", "Larch Test"]);
        fs::write(root.join("README.md"), "").expect("fixture readme");
        fs::write(root.join("docs/guide.md"), "").expect("fixture guide");
        fs::write(
            root.join("tools-config.toml"),
            "[larch]\nstorage_base_uri = \"s3://fixture-bucket/larch-tests\"\n",
        )
        .expect("fixture storage configuration");
        run_git(&root, &["add", "."]);
        run_git(&root, &["commit", "-m", "fixture"]);
        run_git(
            &root,
            &[
                "remote",
                "add",
                "origin",
                "https://github.com/acme/widget.git",
            ],
        );
        Self {
            _directory: directory,
            root,
            home,
            state,
        }
    }

    fn run(&self, verb: &str) -> Output {
        let mut command = AssertCommand::cargo_bin("larch").expect("larch binary should build");
        command
            .current_dir(&self.root)
            .env("HOME", &self.home)
            .env("XDG_STATE_HOME", &self.state)
            .env("LARCH_MEASURE_DATE", "fixture")
            .env_remove("CLAUDE_PROJECT_DIR")
            .env_remove("LARCH_LOGS_URI")
            .env_remove("LARCH_STORAGE_BASE_URI")
            .args(["token", verb]);
        command.output().expect("measurement command should launch")
    }

    fn disable_storage(&self) {
        fs::remove_file(self.root.join("tools-config.toml")).expect("remove storage config");
    }
}

fn run_git(root: &Path, arguments: &[&str]) {
    let output = ProcessCommand::new("git")
        .current_dir(root)
        .args(arguments)
        .output()
        .expect("fixture git should launch");
    assert!(
        output.status.success(),
        "git {arguments:?} failed: {}",
        String::from_utf8_lossy(&output.stderr)
    );
}

fn wrote_path(output: &Output) -> PathBuf {
    stdout(output)
        .trim_end()
        .strip_prefix("WROTE\t")
        .map(PathBuf::from)
        .expect("WROTE path")
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

#[test]
fn record_vendor_appends_codex_row() {
    let fixture = Fixture::new();
    let output = fixture.run(&[
        "record-vendor",
        "codex",
        "input=4",
        "output=5",
        "cache_read=1",
        "cache_create=2",
        "total=12",
        "raw=codex_review",
        "model=gpt-5",
    ]);
    assert!(output.status.success(), "{}", stderr(&output));
    let text = fs::read_to_string(fixture.ledger()).expect("ledger");
    assert!(text.contains("\"vendor\":\"codex\""), "{text}");
    assert!(text.contains("\"total\":12"), "{text}");
    assert!(text.contains("\"model\":\"gpt-5\""), "{text}");
}

#[test]
fn record_vendor_sidecar_maps_claude_to_claude_sub() {
    let fixture = Fixture::new();
    let sidecar = fixture.tmpdir.join("claude.token-record");
    fs::write(
        &sidecar,
        "TOOL=claude\nINPUT=2\nOUTPUT=3\nCACHE_READ=0\nCACHE_CREATE=0\nTOTAL=5\nRAW=claude_review\nMODEL=claude-sonnet-4-6[1m]\n",
    )
    .expect("sidecar");
    let output = fixture.run(&[
        "record-vendor-sidecar",
        "--input",
        sidecar.to_str().expect("utf8"),
    ]);
    assert!(output.status.success(), "{}", stderr(&output));
    let text = fs::read_to_string(fixture.ledger()).expect("ledger");
    assert!(text.contains("\"vendor\":\"claude_sub\""), "{text}");
    assert!(text.contains("\"model\":\"claude-sonnet-4-6\""), "{text}");
}

#[test]
fn mark_accepts_explicit_ledger_flag() {
    let fixture = Fixture::new();
    let ledger = fixture.tmpdir.join("explicit.jsonl");
    let output = fixture.run(&[
        "mark",
        "--ledger",
        ledger.to_str().expect("utf8"),
        "Step 0 — preflight",
    ]);
    assert!(output.status.success(), "{}", stderr(&output));
    let text = fs::read_to_string(&ledger).expect("explicit ledger");
    assert!(text.contains("Step 0 \\u2014 preflight"), "{text}");
}

#[test]
fn mark_without_step_fails() {
    let fixture = Fixture::new();
    let output = fixture.run(&["mark"]);
    assert_eq!(output.status.code(), Some(1));
    assert!(stderr(&output).contains("requires"), "{}", stderr(&output));
}

#[test]
fn record_vendor_rejects_non_integer_field() {
    let fixture = Fixture::new();
    let output = fixture.run(&[
        "record-vendor",
        "codex",
        "input=abc",
        "output=0",
        "cache_read=0",
        "cache_create=0",
        "total=0",
        "raw=bad",
    ]);
    assert_eq!(output.status.code(), Some(1));
    assert!(
        stderr(&output).contains("non-negative integer"),
        "{}",
        stderr(&output)
    );
}

#[test]
fn lane_write_rejects_path_outside_tmp() {
    let fixture = Fixture::new();
    let output = fixture.run(&[
        "lane-write",
        "--dir",
        "/var/tmp/larch-token-lane-forbidden",
        "--phase",
        "research",
        "--lane",
        "edge",
        "--tool",
        "claude",
        "--total-tokens",
        "1",
    ]);
    assert_ne!(output.status.code(), Some(0));
    assert!(stderr(&output).contains("--dir"), "{}", stderr(&output));
}

#[test]
fn record_vendor_sidecar_skips_missing_input() {
    let fixture = Fixture::new();
    let missing = fixture.tmpdir.join("absent.token-record");
    let output = fixture.run(&[
        "record-vendor-sidecar",
        "--input",
        missing.to_str().expect("utf8"),
    ]);
    assert!(output.status.success(), "{}", stderr(&output));
    assert!(!fixture.ledger().exists());
}

#[test]
fn append_record_tolerates_absent_sidecar() {
    let fixture = Fixture::new();
    let missing = fixture.tmpdir.join("absent.token-record");
    let output = fixture.run(&[
        "append-record",
        "--input",
        missing.to_str().expect("utf8"),
        "--tmpdir",
        fixture.tmpdir.to_str().expect("utf8"),
    ]);
    assert!(output.status.success(), "{}", stderr(&output));
}

#[test]
fn measurement_source_commands_preserve_black_box_wires() {
    let fixture = MeasurementFixture::new();
    let markdown = fixture.run("measure-md-cost");
    assert_eq!(markdown.status.code(), Some(0));
    assert_eq!(stderr(&markdown), "");
    let markdown_path = wrote_path(&markdown);
    assert_eq!(
        stdout(&markdown),
        format!("WROTE\t{}\n", markdown_path.display())
    );
    assert_eq!(
        fs::read_to_string(markdown_path).expect("markdown report"),
        "path\ttier\tbytes\ttokens\tlines\th2_count\n\
docs/guide.md\ttier-3-doc\t0\t0\t0\t0\n\
README.md\ttier-3-other\t0\t0\t0\t0\n"
    );

    let ngram = fixture.run("measure-ngram-duplication");
    assert_eq!(ngram.status.code(), Some(0));
    assert_eq!(stderr(&ngram), "");
    let ngram_path = wrote_path(&ngram);
    assert_eq!(stdout(&ngram), format!("WROTE\t{}\n", ngram_path.display()));
    assert_eq!(
        fs::read_to_string(ngram_path).expect("ngram report"),
        "score\toccurrences\tfiles\tshingle\n"
    );
}

#[test]
fn corpus_measurements_preserve_disabled_storage_refusal() {
    let fixture = MeasurementFixture::new();
    fixture.disable_storage();
    let refusal = "run-log storage is disabled; configure [larch].storage_base_uri or set LARCH_STORAGE_BASE_URI\n";
    for verb in [
        "measure-cache-efficiency",
        "measure-checks-digest-savings",
        "measure-panel-cost",
        "measure-realized-cost",
        "measure-references-heatmap",
    ] {
        let output = fixture.run(verb);
        assert_eq!(output.status.code(), Some(4), "{verb}");
        assert_eq!(stdout(&output), "", "{verb}");
        let prefix = if verb == "measure-cache-efficiency" {
            ""
        } else {
            "ERROR: "
        };
        assert_eq!(stderr(&output), format!("{prefix}{refusal}"), "{verb}");
    }
}
