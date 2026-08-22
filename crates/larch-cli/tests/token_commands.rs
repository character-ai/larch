//! Integration coverage for the Rust-owned `token` verbs.

use std::{
    fs,
    path::{Path, PathBuf},
    process::{Command as ProcessCommand, Output},
};

use assert_cmd::Command as AssertCommand;

const TOKEN_REPORT_LEDGER: &str =
    include_str!("../../larch-core/tests/fixtures/token_scan/ledger.jsonl");
const TOKEN_REPORT_TRANSCRIPT: &str =
    include_str!("../../larch-core/tests/fixtures/token_scan/transcript.jsonl");
const TOKEN_REPORT_FULL: &str =
    include_str!("../../larch-core/tests/fixtures/token_scan/full-report.json");

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

    fn report_sources(&self) -> (PathBuf, PathBuf) {
        let ledger = self.tmpdir.join("report-ledger.jsonl");
        let transcript = self.tmpdir.join("report-transcript.jsonl");
        fs::write(&ledger, TOKEN_REPORT_LEDGER).expect("report ledger");
        fs::write(&transcript, TOKEN_REPORT_TRANSCRIPT).expect("report transcript");
        (ledger, transcript)
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
            .env_remove("LARCH_CLAUDE_SOURCE_FILE")
            .env_remove("LARCH_CLAUDE_SESSION_ID")
            .env_remove("CLAUDE_CODE_SESSION_ID")
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
fn check_budget_preserves_the_line_oriented_wire() {
    let fixture = Fixture::new();
    fs::write(
        fixture.ledger(),
        concat!(
            "{\"type\":\"vendor\",\"total\":100}\n",
            "{\"type\":\"mark\"}\n",
            "{\"type\":\"vendor\",\"total\":50}\n",
        ),
    )
    .expect("budget ledger");
    let under = fixture.run(&["check-budget", "--cap", "100", "--step", "Step 2"]);
    assert!(under.status.success(), "{}", stderr(&under));
    assert_eq!(
        stdout(&under),
        "STATUS=under_cap TOTAL=50 CAP=100 STEP=Step 2\n"
    );
    let hit = fixture.run(&["check-budget", "--cap", "40", "--step", "Step 2"]);
    assert!(hit.status.success(), "{}", stderr(&hit));
    assert_eq!(stdout(&hit), "STATUS=cap_hit TOTAL=50 CAP=40 STEP=Step 2\n");
}

#[test]
fn compute_pr_line_count_aliases_share_the_skipped_wire() {
    let fixture = Fixture::new();
    for verb in ["compute-pr-line-counts", "compute-pr-lines"] {
        let output = fixture.run(&[verb]);
        assert!(output.status.success(), "{}", stderr(&output));
        assert_eq!(stdout(&output), "LINES_STATUS=skipped\nREASON=no-pr\n");
    }
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
        "raw=codex=review",
        "model=gpt-5",
    ]);
    assert!(output.status.success(), "{}", stderr(&output));
    let text = fs::read_to_string(fixture.ledger()).expect("ledger");
    assert!(text.contains("\"vendor\":\"codex\""), "{text}");
    assert!(text.contains("\"total\":12"), "{text}");
    assert!(text.contains("\"raw\":\"codex=review\""), "{text}");
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
fn report_renders_recorded_json_markdown_and_compact_modes() {
    let fixture = Fixture::new();
    let (ledger, transcript) = fixture.report_sources();
    let ledger = ledger.to_str().expect("ledger utf8");
    let transcript = transcript.to_str().expect("transcript utf8");

    let full = fixture.run(&[
        "report",
        "--full",
        "--format",
        "json",
        "--ledger",
        ledger,
        "--transcript",
        transcript,
    ]);
    assert!(full.status.success(), "{}", stderr(&full));
    let expected: serde_json::Value =
        serde_json::from_str(TOKEN_REPORT_FULL).expect("recorded full report");
    let actual: serde_json::Value =
        serde_json::from_str(&stdout(&full)).expect("rendered full report");
    assert_eq!(actual, expected);
    assert!(stdout(&full).contains("\\u2014"), "{}", stdout(&full));

    let markdown = fixture.run(&[
        "report",
        "--full",
        "--markdown",
        "--ledger",
        ledger,
        "--transcript",
        transcript,
    ]);
    assert!(markdown.status.success(), "{}", stderr(&markdown));
    assert!(
        stdout(&markdown).contains("| **Grand total** |  | 1007 | 13 | 1521 |"),
        "{}",
        stdout(&markdown)
    );

    let summary = fixture.run(&[
        "report",
        "--summary",
        "--ledger",
        ledger,
        "--transcript",
        transcript,
    ]);
    assert_eq!(
        stdout(&summary),
        "Tokens: 2k, Claude: 0k | Codex: 2k | Cursor: 0k | Claude (subprocess): 0k\n"
    );
    let ignored_vendor = fixture.run(&[
        "report",
        "--summary",
        "--vendor",
        "unused",
        "--ledger",
        ledger,
        "--transcript",
        transcript,
    ]);
    assert!(
        ignored_vendor.status.success(),
        "{}",
        stderr(&ignored_vendor)
    );
    assert_eq!(stdout(&ignored_vendor), stdout(&summary));
    let terse = fixture.run(&[
        "report",
        "--terse",
        "--ledger",
        ledger,
        "--transcript",
        transcript,
    ]);
    assert_eq!(
        stdout(&terse),
        "Step 5 — code review: claude=0 tokens; vendor=145\n"
    );
    let buckets = fixture.run(&[
        "report",
        "--buckets",
        "--vendor",
        "codex",
        "--ledger",
        ledger,
        "--transcript",
        transcript,
    ]);
    assert_eq!(stdout(&buckets), "INPUT=1007 CACHED_INPUT=501 OUTPUT=13\n");
}

#[test]
fn report_writes_output_and_replaces_append_block() {
    let fixture = Fixture::new();
    let (ledger, transcript) = fixture.report_sources();
    let output = fixture.tmpdir.join("rendered.json");
    let body = fixture.tmpdir.join("body.md");
    fs::write(&body, "before\n").expect("body");
    let arguments = [
        "report".to_owned(),
        "--full".to_owned(),
        "--format".to_owned(),
        "json".to_owned(),
        "--ledger".to_owned(),
        ledger.to_string_lossy().into_owned(),
        "--transcript".to_owned(),
        transcript.to_string_lossy().into_owned(),
        "--output".to_owned(),
        output.to_string_lossy().into_owned(),
        "--append-token-report".to_owned(),
        body.to_string_lossy().into_owned(),
    ];
    let refs: Vec<&str> = arguments.iter().map(String::as_str).collect();
    let first = fixture.run(&refs);
    assert!(first.status.success(), "{}", stderr(&first));
    assert!(stdout(&first).is_empty(), "{}", stdout(&first));
    let rendered: serde_json::Value =
        serde_json::from_str(&fs::read_to_string(&output).expect("output")).expect("json output");
    assert!(rendered.get("BUCKETS_codex").is_some());
    let repeated = fixture.run(&refs);
    assert!(repeated.status.success(), "{}", stderr(&repeated));
    let body = fs::read_to_string(&body).expect("appended body");
    assert_eq!(
        body.matches("<!-- token-report-begin -->").count(),
        1,
        "{body}"
    );
    assert!(body.contains("## Token Report"), "{body}");
}

#[test]
fn report_preserves_fail_open_unavailable_envelope() {
    let fixture = Fixture::new();
    let missing = fixture.tmpdir.join("missing-ledger.jsonl");
    let output = fixture.run(&[
        "report",
        "--ledger",
        missing.to_str().expect("missing utf8"),
    ]);
    assert!(output.status.success(), "{}", stderr(&output));
    assert!(
        stderr(&output).starts_with("Token report unavailable: "),
        "{}",
        stderr(&output)
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

#[test]
fn report_replays_a_validated_source_snapshot() {
    let fixture = Fixture::new();
    let (ledger, transcript) = fixture.report_sources();
    let source = fixture.tmpdir.join("claude-source.env");
    fs::write(
        &source,
        format!(
            "TRANSCRIPT_PATH={}\nSESSION_DIR={}\nSESSION_UUID=fixture-session\n",
            transcript.display(),
            fixture.tmpdir.display()
        ),
    )
    .expect("source snapshot");
    let output = fixture.run(&[
        "report",
        "--summary",
        "--ledger",
        ledger.to_str().expect("ledger utf8"),
        "--source-file",
        source.to_str().expect("source utf8"),
    ]);
    assert!(output.status.success(), "{}", stderr(&output));
    assert_eq!(
        stdout(&output),
        "Tokens: 2k, Claude: 0k | Codex: 2k | Cursor: 0k | Claude (subprocess): 0k\n"
    );
}

#[test]
fn claude_source_replays_a_validated_source_snapshot() {
    let fixture = Fixture::new();
    let transcript = fixture.tmpdir.join("claude-session.jsonl");
    fs::write(&transcript, "{\"type\":\"user\"}\n").expect("transcript");
    let source = fixture.tmpdir.join("claude-source.env");
    fs::write(
        &source,
        format!(
            "TRANSCRIPT_PATH={}\nSESSION_DIR={}\nSESSION_UUID=fixture-session\n",
            transcript.display(),
            fixture.tmpdir.display()
        ),
    )
    .expect("source snapshot");
    let output = fixture.run(&["claude-source", source.to_str().expect("source utf8")]);
    assert!(output.status.success(), "{}", stderr(&output));
    assert_eq!(
        stdout(&output),
        format!(
            "TRANSCRIPT_PATH={}\nSESSION_DIR={}\nSESSION_UUID=fixture-session\n",
            transcript.display(),
            fixture.tmpdir.display()
        )
    );
}

#[test]
fn claude_source_replays_a_snapshot_whose_session_dir_is_not_on_disk() {
    // A bootstrap snapshot names SESSION_DIR = <project>/<uuid>, a directory that
    // is never created. The replay must still honor the pinned transcript rather
    // than fall back to the newest project scan (which would pick `zzz.jsonl`).
    let directory = tempfile::tempdir().expect("temporary root");
    let base = fs::canonicalize(directory.path()).expect("canonical root");
    let repo = base.join("repo");
    fs::create_dir_all(&repo).expect("repo dir");
    run_git(&repo, &["init", "-b", "main"]);
    let repo_canonical = fs::canonicalize(&repo).expect("canonical repo");
    let dashed = repo_canonical.to_string_lossy().replace('/', "-");
    let home = base.join("home");
    let project = home.join(".claude").join("projects").join(dashed);
    fs::create_dir_all(&project).expect("project dir");
    let pinned = project.join("aaa.jsonl");
    fs::write(&pinned, "{\"type\":\"user\"}\n").expect("pinned transcript");
    fs::write(project.join("zzz.jsonl"), "{\"type\":\"user\"}\n").expect("competing transcript");
    let source = base.join("source.env");
    fs::write(
        &source,
        format!(
            "TRANSCRIPT_PATH={}\nSESSION_DIR={}\nSESSION_UUID=aaa\n",
            pinned.display(),
            project.join("aaa").display()
        ),
    )
    .expect("source snapshot");

    let mut command = AssertCommand::cargo_bin("larch").expect("larch binary should build");
    command
        .current_dir(&repo)
        .env("HOME", &home)
        .env_remove("LARCH_CLAUDE_SOURCE_FILE")
        .env_remove("LARCH_CLAUDE_SESSION_ID")
        .env_remove("CLAUDE_CODE_SESSION_ID")
        .args([
            "token",
            "claude-source",
            source.to_str().expect("source utf8"),
        ]);
    let output = command.output().expect("token claude-source should launch");

    assert!(output.status.success(), "{}", stderr(&output));
    let rendered = stdout(&output);
    assert!(
        rendered.contains(&format!("TRANSCRIPT_PATH={}\n", pinned.display())),
        "expected pinned transcript, got: {rendered}"
    );
    assert!(rendered.contains("SESSION_UUID=aaa\n"), "{rendered}");
    assert!(!rendered.contains("zzz.jsonl"), "{rendered}");
}

#[test]
fn claude_source_reports_unavailable_without_a_project() {
    let fixture = Fixture::new();
    let output = fixture.run(&["claude-source"]);
    assert_eq!(output.status.code(), Some(1));
    assert_eq!(
        stdout(&output),
        "STATUS=unavailable\nREASON=not inside a git repository\n"
    );
    assert_eq!(stderr(&output), "");
}

#[test]
fn report_scrape_normalizes_confined_token_and_timing_sidecars() {
    let fixture = Fixture::new();
    let sidecar = fixture.tmpdir.join("side=car.json");
    let timing = fixture.tmpdir.join("timing.json");
    let token_output = fixture.tmpdir.join("token.ndjson");
    let timing_output = fixture.tmpdir.join("timing.ndjson");
    fs::write(
        &sidecar,
        r#"{"input_tokens":1,"output_tokens":2,"cache_read_tokens":3,"cache_create_tokens":4,"model":"gpt"}"#,
    )
    .expect("token sidecar");
    fs::write(&timing, r#"{"duration_ms":20}"#).expect("timing sidecar");
    let arguments = [
        "report".to_owned(),
        "--scrape-run-output".to_owned(),
        token_output.to_string_lossy().into_owned(),
        "--scrape-timing-output".to_owned(),
        timing_output.to_string_lossy().into_owned(),
        "--implement-tmpdir".to_owned(),
        fixture.tmpdir.to_string_lossy().into_owned(),
        "--scrape-sidecar".to_owned(),
        format!("codex={}", sidecar.display()),
        "--scrape-timing-sidecar".to_owned(),
        format!("codex={}", timing.display()),
    ];
    let refs: Vec<&str> = arguments.iter().map(String::as_str).collect();
    let output = fixture.run(&refs);
    assert!(output.status.success(), "{}", stderr(&output));
    assert_eq!(
        fs::read_to_string(token_output).expect("normalized token sidecar"),
        "{\"cache_create_tokens\": 4, \"cache_read_tokens\": 3, \"input_tokens\": 1, \"model\": \"gpt\", \"output_tokens\": 2, \"tool\": \"codex\", \"total_tokens\": 10}\n"
    );
    assert_eq!(
        fs::read_to_string(timing_output).expect("normalized timing sidecar"),
        "{\"duration_ms\": 20, \"tool\": \"codex\"}\n"
    );

    let malformed_integer = fixture.tmpdir.join("malformed-integer.json");
    let malformed_output = fixture.tmpdir.join("malformed-integer.ndjson");
    fs::write(
        &malformed_integer,
        r#"{"input_tokens":"1.5","output_tokens":"2","cache_read_tokens":"1,000","model":false}"#,
    )
    .expect("malformed integer sidecar");
    let arguments = [
        "report".to_owned(),
        "--scrape-run-output".to_owned(),
        malformed_output.to_string_lossy().into_owned(),
        "--implement-tmpdir".to_owned(),
        fixture.tmpdir.to_string_lossy().into_owned(),
        "--scrape-sidecar".to_owned(),
        format!("cursor={}", malformed_integer.display()),
    ];
    let refs: Vec<&str> = arguments.iter().map(String::as_str).collect();
    let output = fixture.run(&refs);
    assert!(output.status.success(), "{}", stderr(&output));
    assert_eq!(
        fs::read_to_string(malformed_output).expect("normalized malformed integer sidecar"),
        "{\"cache_create_tokens\": 0, \"cache_read_tokens\": 0, \"input_tokens\": 0, \"output_tokens\": 2, \"tool\": \"cursor\", \"total_tokens\": 2}\n"
    );

    let outside = fixture
        .tmpdir
        .parent()
        .expect("temporary root parent")
        .join(format!(
            "outside-token-{}.ndjson",
            fixture
                .tmpdir
                .file_name()
                .and_then(|name| name.to_str())
                .expect("temporary root name")
        ));
    let arguments = [
        "report".to_owned(),
        "--scrape-run-output".to_owned(),
        outside.to_string_lossy().into_owned(),
        "--implement-tmpdir".to_owned(),
        fixture.tmpdir.to_string_lossy().into_owned(),
    ];
    let refs: Vec<&str> = arguments.iter().map(String::as_str).collect();
    let refused = fixture.run(&refs);
    assert!(refused.status.success(), "{}", stderr(&refused));
    assert!(!outside.exists());
    assert!(
        stderr(&refused).contains("scrape output must stay under --implement-tmpdir"),
        "{}",
        stderr(&refused)
    );
}

#[test]
fn report_scrape_ignores_timing_sidecars_without_a_timing_output() {
    let fixture = Fixture::new();
    let ignored_timing = fixture.tmpdir.join("ignored-timing.json");
    fs::write(&ignored_timing, [0xff_u8]).expect("invalid UTF-8 timing sidecar");
    let ignored_token_output = fixture.tmpdir.join("ignored-timing-token.ndjson");
    let arguments = [
        "report".to_owned(),
        "--scrape-run-output".to_owned(),
        ignored_token_output.to_string_lossy().into_owned(),
        "--implement-tmpdir".to_owned(),
        fixture.tmpdir.to_string_lossy().into_owned(),
        "--scrape-timing-sidecar".to_owned(),
        format!("cursor={}", ignored_timing.display()),
    ];
    let refs: Vec<&str> = arguments.iter().map(String::as_str).collect();
    let ignored = fixture.run(&refs);
    assert!(ignored.status.success(), "{}", stderr(&ignored));
    assert!(stderr(&ignored).is_empty(), "{}", stderr(&ignored));
    assert!(!ignored_token_output.exists());
}

#[test]
fn cost_and_render_cost_line_preserve_cli_contracts() {
    let fixture = Fixture::new();
    let cost = fixture.run(&[
        "cost",
        "--codex-input-tokens",
        "1000",
        "--codex-cached-input-tokens",
        "500",
        "--codex-output-tokens",
        "250",
    ]);
    assert!(cost.status.success(), "{}", stderr(&cost));
    assert!(
        stdout(&cost).starts_with("CLAUDE_COST="),
        "{}",
        stdout(&cost)
    );
    assert!(
        stdout(&cost).contains("TOTAL_TOKENS=1750\n"),
        "{}",
        stdout(&cost)
    );
    assert!(!stderr(&cost).contains("blended rate"), "{}", stderr(&cost));

    let line = fixture.run(&[
        "render-cost-line",
        "--codex-input-tokens",
        "1000",
        "--codex-output-tokens",
        "500",
    ]);
    assert!(line.status.success(), "{}", stderr(&line));
    assert!(
        stdout(&line).starts_with("💰 Cost: TOTAL ~$"),
        "{}",
        stdout(&line)
    );
    let quiet = fixture.run(&["render-cost-line", "--quiet-on-empty"]);
    assert!(quiet.status.success(), "{}", stderr(&quiet));
    assert!(stdout(&quiet).is_empty(), "{}", stdout(&quiet));
    let invalid = fixture.run(&["cost", "--unknown-tokens", "1"]);
    assert_eq!(invalid.status.code(), Some(2));
    assert!(
        stderr(&invalid).contains("token cost: unknown or incomplete flag"),
        "{}",
        stderr(&invalid)
    );
}
