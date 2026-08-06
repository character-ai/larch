//! Integration coverage for the Rust-owned run-log entry-write commands.
//!
//! Each command is exercised for success, refusal, and recovery from an
//! interrupted or pre-existing destination, plus real cross-process concurrent
//! appends.

use std::{
    collections::BTreeMap,
    fs,
    path::{Path, PathBuf},
    process::Command,
};

use assert_cmd::Command as AssertCommand;
use larch_core::{KvDocument, ParseOptions};
use serde_json::Value;

fn larch() -> AssertCommand {
    AssertCommand::cargo_bin("larch").expect("larch binary should build")
}

fn larch_path() -> PathBuf {
    assert_cmd::cargo::cargo_bin("larch")
}

/// Parse a `KEY=value` stdout envelope into a map through the shared codec.
fn envelope(stdout: &[u8]) -> BTreeMap<String, String> {
    let stdout = String::from_utf8_lossy(stdout);
    KvDocument::parse(&stdout, ParseOptions::legacy())
        .expect("run-log envelope should be valid KEY=value output")
        .rows()
        .iter()
        .map(|row| (row.key().to_owned(), row.value().to_owned()))
        .collect()
}

struct Fixture {
    _directory: tempfile::TempDir,
    log_root: PathBuf,
}

impl Fixture {
    fn new() -> Self {
        let directory = tempfile::tempdir().expect("temporary root should create");
        // Real callers derive log roots from an already-resolved session tmpdir.
        // Canonicalize here so macOS's `/var` -> `/private/var` link does not trip
        // the writer's symlinked-ancestor refusal.
        let root = fs::canonicalize(directory.path()).expect("temporary root should canonicalize");
        let log_root = root.join("larch-logs");
        fs::create_dir_all(&log_root).expect("log root should create");
        Self {
            _directory: directory,
            log_root,
        }
    }

    fn identity(&self) -> Vec<String> {
        vec![
            "--log-root".to_owned(),
            self.log_root.display().to_string(),
            "--skill".to_owned(),
            "implement".to_owned(),
            "--run-id".to_owned(),
            "run-abc".to_owned(),
        ]
    }

    fn run_dir(&self) -> PathBuf {
        self.log_root.join("implement").join("run-abc")
    }

    fn write_source(&self, name: &str, body: &str) -> PathBuf {
        let path = self.log_root.parent().expect("parent").join(name);
        fs::write(&path, body).expect("source should write");
        path
    }

    /// Run one `run-log` verb with the shared identity flags and a clean env.
    fn run(&self, verb: &str, extra: &[String]) -> std::process::Output {
        let mut command = larch();
        command
            .arg("run-log")
            .arg(verb)
            .args(self.identity())
            .args(extra)
            .env_remove("IMPLEMENT_TMPDIR")
            .env_remove("LARCH_LOG_ROOT")
            .env_remove("LARCH_FLUSH_DEBUG");
        command.output().expect("command should launch")
    }
}

#[test]
fn init_writes_a_v2_manifest_then_reports_unchanged() {
    let fixture = Fixture::new();

    let first = fixture.run("init", &["--issue".to_owned(), "8073".to_owned()]);
    assert!(first.status.success(), "init should succeed");
    let first_envelope = envelope(&first.stdout);
    assert_eq!(first_envelope.get("LOG_WRITTEN"), Some(&"true".to_owned()));
    assert_eq!(first_envelope.get("UNCHANGED"), Some(&"false".to_owned()));

    let manifest_path = fixture.run_dir().join("manifest.json");
    let manifest: Value =
        serde_json::from_str(&fs::read_to_string(&manifest_path).expect("manifest should read"))
            .expect("manifest should decode");
    assert_eq!(manifest["schema_version"], Value::from(2));
    assert_eq!(manifest["skill"], Value::from("implement"));
    assert_eq!(manifest["run_id"], Value::from("run-abc"));
    assert_eq!(manifest["issue_number"], Value::from(8073));
    assert_eq!(manifest["parent_skill"], Value::Null);

    // A second init is idempotent and never rewrites the manifest.
    let before = fs::read(&manifest_path).expect("manifest should read");
    let second = fixture.run("init", &["--issue".to_owned(), "8073".to_owned()]);
    assert!(second.status.success(), "second init should succeed");
    let second_envelope = envelope(&second.stdout);
    assert_eq!(
        second_envelope.get("LOG_WRITTEN"),
        Some(&"false".to_owned())
    );
    assert_eq!(second_envelope.get("UNCHANGED"), Some(&"true".to_owned()));
    assert_eq!(
        fs::read(&manifest_path).expect("manifest should read"),
        before
    );
}

#[test]
fn init_refuses_a_half_specified_parent_and_a_non_numeric_issue() {
    let fixture = Fixture::new();

    let orphan = fixture.run("init", &["--parent-skill".to_owned(), "design".to_owned()]);
    assert_eq!(orphan.status.code(), Some(1));
    assert_eq!(
        envelope(&orphan.stdout).get("ERROR"),
        Some(&"parent-skill and parent-run-id must be provided together".to_owned())
    );

    let bad_issue = fixture.run("init", &["--issue".to_owned(), "80a73".to_owned()]);
    assert_eq!(bad_issue.status.code(), Some(1));
    assert_eq!(
        envelope(&bad_issue.stdout).get("ERROR"),
        Some(&"invalid issue: 80a73".to_owned())
    );
    assert!(!fixture.run_dir().join("manifest.json").exists());
}

#[test]
fn write_redacts_normalizes_and_reports_unchanged_on_a_repeat() {
    let fixture = Fixture::new();
    let source = fixture.write_source(
        "context.md",
        "context with token sk-ant-abcdefghijklmnopqrstuvwxyz0123\n\n\n",
    );

    let first = fixture.run(
        "write",
        &[
            "--batch".to_owned(),
            "review-context".to_owned(),
            "--input-file".to_owned(),
            source.display().to_string(),
        ],
    );
    assert!(first.status.success(), "write should succeed");
    assert_eq!(
        envelope(&first.stdout).get("LOG_WRITTEN"),
        Some(&"true".to_owned())
    );

    let written = fixture.run_dir().join("review-context.md");
    let body = fs::read_to_string(&written).expect("batch should read");
    assert!(!body.contains("sk-ant-"), "secret should be redacted");
    assert!(body.contains("<REDACTED-TOKEN>"));
    assert!(
        body.ends_with('\n') && !body.ends_with("\n\n"),
        "exactly one trailing newline"
    );

    let repeat = fixture.run(
        "write",
        &[
            "--batch".to_owned(),
            "review-context".to_owned(),
            "--input-file".to_owned(),
            source.display().to_string(),
        ],
    );
    let repeat_envelope = envelope(&repeat.stdout);
    assert_eq!(
        repeat_envelope.get("LOG_WRITTEN"),
        Some(&"false".to_owned())
    );
    assert_eq!(repeat_envelope.get("UNCHANGED"), Some(&"true".to_owned()));
}

#[test]
fn identity_flags_accept_the_inline_equals_spelling() {
    let fixture = Fixture::new();
    let source = fixture.write_source("stats.md", "stats\n");

    let output = larch()
        .args([
            "run-log",
            "write",
            &format!("--log-root={}", fixture.log_root.display()),
            "--skill=implement",
            "--run-id=run-abc",
            "--batch=run-statistics",
            &format!("--input-file={}", source.display()),
        ])
        .env_remove("IMPLEMENT_TMPDIR")
        .env_remove("LARCH_LOG_ROOT")
        .output()
        .expect("write should launch");

    assert!(
        output.status.success(),
        "inline spelling failed: {}",
        String::from_utf8_lossy(&output.stdout)
    );
    assert!(fixture.run_dir().join("run-statistics.md").is_file());
}

#[test]
fn write_refuses_unknown_batches_append_only_batches_and_bad_payloads() {
    let fixture = Fixture::new();
    let source = fixture.write_source("payload.json", "[]\n");

    let unknown = fixture.run(
        "write",
        &[
            "--batch".to_owned(),
            "no-such-batch".to_owned(),
            "--input-file".to_owned(),
            source.display().to_string(),
        ],
    );
    assert_eq!(unknown.status.code(), Some(1));
    assert_eq!(
        envelope(&unknown.stdout).get("ERROR"),
        Some(&"unknown batch: no-such-batch".to_owned())
    );

    let append_only = fixture.run(
        "write",
        &[
            "--batch".to_owned(),
            "execution-issues".to_owned(),
            "--input-file".to_owned(),
            source.display().to_string(),
        ],
    );
    assert_eq!(append_only.status.code(), Some(1));
    assert_eq!(
        envelope(&append_only.stdout).get("ERROR"),
        Some(&"batch execution-issues is append-only; use append".to_owned())
    );

    let bad_object = fixture.run(
        "write",
        &[
            "--batch".to_owned(),
            "code-review-tally".to_owned(),
            "--input-file".to_owned(),
            source.display().to_string(),
        ],
    );
    assert_eq!(bad_object.status.code(), Some(1));
    assert_eq!(
        envelope(&bad_object.stdout).get("ERROR"),
        Some(&"batch code-review-tally requires a JSON object".to_owned())
    );

    // A missing input file is an IO refusal, not a validation refusal.
    let missing = fixture.run(
        "write",
        &[
            "--batch".to_owned(),
            "review-context".to_owned(),
            "--input-file".to_owned(),
            "/nonexistent/input.md".to_owned(),
        ],
    );
    assert_eq!(missing.status.code(), Some(2));
    assert!(!fixture.run_dir().join("review-context.md").exists());
}

#[test]
fn write_leaves_the_previous_batch_intact_when_validation_refuses() {
    let fixture = Fixture::new();
    let good = fixture.write_source("good.json", "{\"round\": 1}\n");
    let bad = fixture.write_source("bad.json", "not json\n");
    let tally = fixture.run_dir().join("code-review-tally.json");

    assert!(
        fixture
            .run(
                "write",
                &[
                    "--batch".to_owned(),
                    "code-review-tally".to_owned(),
                    "--input-file".to_owned(),
                    good.display().to_string(),
                ],
            )
            .status
            .success()
    );
    let original = fs::read(&tally).expect("tally should read");

    let refused = fixture.run(
        "write",
        &[
            "--batch".to_owned(),
            "code-review-tally".to_owned(),
            "--input-file".to_owned(),
            bad.display().to_string(),
        ],
    );
    assert_eq!(refused.status.code(), Some(1));
    assert_eq!(
        fs::read(&tally).expect("tally should read"),
        original,
        "a refused payload never replaces the published artifact"
    );
    // No temp file is left behind for the next writer to trip over.
    let strays: Vec<_> = fs::read_dir(fixture.run_dir())
        .expect("run dir should list")
        .flatten()
        .map(|entry| entry.file_name().to_string_lossy().into_owned())
        .filter(|name| name.starts_with(".manifest-"))
        .collect();
    assert!(strays.is_empty(), "stray temp files: {strays:?}");
}

#[test]
fn append_accumulates_records_and_refuses_replace_only_batches() {
    let fixture = Fixture::new();
    let first = fixture.write_source("first.ndjson", "{\"a\":1}\n");
    let second = fixture.write_source("second.ndjson", "{\"b\":2}\n");

    for source in [&first, &second] {
        let output = fixture.run(
            "append",
            &[
                "--batch".to_owned(),
                "execution-issues".to_owned(),
                "--record-file".to_owned(),
                source.display().to_string(),
            ],
        );
        assert!(output.status.success(), "append should succeed");
        assert_eq!(
            envelope(&output.stdout).get("LOG_WRITTEN"),
            Some(&"true".to_owned())
        );
    }
    assert_eq!(
        fs::read_to_string(fixture.run_dir().join("execution-issues.ndjson"))
            .expect("ledger should read"),
        "{\"a\":1}\n{\"b\":2}\n"
    );

    let replace_only = fixture.run(
        "append",
        &[
            "--batch".to_owned(),
            "review-context".to_owned(),
            "--record-file".to_owned(),
            first.display().to_string(),
        ],
    );
    assert_eq!(replace_only.status.code(), Some(1));
    assert_eq!(
        envelope(&replace_only.stdout).get("ERROR"),
        Some(&"batch review-context is replace-only; use write".to_owned())
    );
}

#[test]
fn debate_batches_refuse_session_tmpdir_pointers_including_inside_json() {
    let fixture = Fixture::new();
    let pointer = "/tmp/larch-implement-abc123/plan.txt";
    let plain = fixture.write_source("proposal.md", &format!("see {pointer}\n"));
    let nested = fixture.write_source(
        "ledger.ndjson",
        &format!("{{\"note\": \"{pointer}\"}}\n").replace('\\', ""),
    );

    let refused_plain = fixture.run(
        "write",
        &[
            "--batch".to_owned(),
            "debate-proposal".to_owned(),
            "--input-file".to_owned(),
            plain.display().to_string(),
        ],
    );
    assert_eq!(refused_plain.status.code(), Some(1));
    assert_eq!(
        envelope(&refused_plain.stdout).get("ERROR"),
        Some(
            &"batch debate-proposal rejects recognized session-tmpdir pointers before persistence"
                .to_owned()
        )
    );

    let refused_nested = fixture.run(
        "append",
        &[
            "--batch".to_owned(),
            "debate-round-ledger".to_owned(),
            "--record-file".to_owned(),
            nested.display().to_string(),
        ],
    );
    assert_eq!(refused_nested.status.code(), Some(1));
    assert!(
        !fixture
            .run_dir()
            .join("debate-round-ledger.ndjson")
            .exists()
    );
}

#[test]
fn exists_reports_presence_without_writing() {
    let fixture = Fixture::new();

    let absent = fixture.run(
        "exists",
        &["--batch".to_owned(), "run-statistics".to_owned()],
    );
    assert!(absent.status.success());
    let absent_envelope = envelope(&absent.stdout);
    assert_eq!(absent_envelope.get("UNCHANGED"), Some(&"false".to_owned()));
    assert_eq!(absent_envelope.get("BYTES"), Some(&"0".to_owned()));
    assert_eq!(absent_envelope.get("SHA256"), Some(&String::new()));
    assert!(
        !fixture.run_dir().exists(),
        "a probe never creates the run dir"
    );

    let source = fixture.write_source("stats.md", "stats\n");
    assert!(
        fixture
            .run(
                "write",
                &[
                    "--batch".to_owned(),
                    "run-statistics".to_owned(),
                    "--input-file".to_owned(),
                    source.display().to_string(),
                ],
            )
            .status
            .success()
    );
    let present = fixture.run(
        "exists",
        &["--batch".to_owned(), "run-statistics".to_owned()],
    );
    assert_eq!(
        envelope(&present.stdout).get("UNCHANGED"),
        Some(&"true".to_owned())
    );

    let unknown = fixture.run("exists", &["--batch".to_owned(), "nope".to_owned()]);
    assert_eq!(unknown.status.code(), Some(1));
}

#[test]
fn write_round_publishes_included_artifacts_and_annotates_the_panel_manifest() {
    let fixture = Fixture::new();
    let source = fixture.log_root.parent().expect("parent").join("round-src");
    fs::create_dir_all(&source).expect("round source should create");
    fs::write(source.join("coder-prompt.md"), "prompt\n").expect("allowed artifact");
    fs::write(source.join("findings.md"), "denied\n").expect("denied artifact");
    fs::write(source.join("coder.env"), "SIDECAR=1\n").expect("sidecar artifact");
    fs::write(
        source.join("panel-manifest.ndjson"),
        "{\"slot\":\"dyn-security\"}\n",
    )
    .expect("panel manifest");
    fs::write(source.join("reviewer-dyn-security.md"), "archetype\n").expect("archetype");

    let output = fixture.run(
        "write-round",
        &[
            "--round".to_owned(),
            "1".to_owned(),
            "--source-dir".to_owned(),
            source.display().to_string(),
        ],
    );
    assert!(
        output.status.success(),
        "write-round failed: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    let round_envelope = envelope(&output.stdout);
    assert_eq!(round_envelope.get("LOG_WRITTEN"), Some(&"true".to_owned()));
    // The destination is a directory, so the envelope reports no file digest.
    assert_eq!(round_envelope.get("BYTES"), Some(&"0".to_owned()));
    assert_eq!(round_envelope.get("SHA256"), Some(&String::new()));

    let dest = fixture.run_dir().join("round-1");
    assert!(dest.join("coder-prompt.md").is_file());
    assert!(!dest.join("findings.md").exists(), "deny globs win");
    assert!(!dest.join("coder.env").exists(), "sidecars never publish");
    assert!(!dest.join("reviewer-dyn-security.md").exists());

    let manifest =
        fs::read_to_string(dest.join("panel-manifest.ndjson")).expect("panel manifest should read");
    let row: Value = serde_json::from_str(manifest.trim()).expect("row should decode");
    let reference = row["archetype_ref"]
        .as_str()
        .expect("archetype_ref should be set");
    assert!(dest.join(reference).is_file(), "archetype pool file exists");
}

#[test]
fn write_round_refuses_a_bad_round_and_a_missing_source() {
    let fixture = Fixture::new();
    let source = fixture.log_root.parent().expect("parent").join("round-src");
    fs::create_dir_all(&source).expect("round source should create");

    let zero = fixture.run(
        "write-round",
        &[
            "--round".to_owned(),
            "0".to_owned(),
            "--source-dir".to_owned(),
            source.display().to_string(),
        ],
    );
    assert_eq!(zero.status.code(), Some(1));
    assert_eq!(
        envelope(&zero.stdout).get("ERROR"),
        Some(&"--round must be a positive integer".to_owned())
    );

    let missing = fixture.run(
        "write-round",
        &[
            "--round".to_owned(),
            "1".to_owned(),
            "--source-dir".to_owned(),
            "/nonexistent/round".to_owned(),
        ],
    );
    assert_eq!(missing.status.code(), Some(1));
    assert!(
        envelope(&missing.stdout)
            .get("ERROR")
            .is_some_and(|error| error.starts_with("source directory not found:"))
    );
}

#[test]
fn append_entry_creates_and_extends_category_sections() {
    let fixture = Fixture::new();
    let log = fixture.log_root.parent().expect("parent").join("issues.md");

    for (category, entry) in [
        ("Warnings", "- first"),
        ("CI Issues", "- ci"),
        ("Warnings", "- second"),
    ] {
        let output = larch()
            .args([
                "run-log",
                "append-entry",
                "--log",
                &log.display().to_string(),
                "--category",
                category,
                "--entry",
                entry,
            ])
            .output()
            .expect("append-entry should launch");
        assert!(output.status.success(), "append-entry should succeed");
        assert_eq!(
            envelope(&output.stdout).get("APPENDED"),
            Some(&"true".to_owned())
        );
    }
    let body = fs::read_to_string(&log).expect("ledger should read");
    assert!(body.contains("### Warnings"));
    assert!(body.contains("### CI Issues"));
    assert!(body.contains("- first"));
    assert!(body.contains("- second"));
    assert!(
        !log.with_file_name("issues.md.lock.d").exists(),
        "lock released"
    );

    let bad_category = larch()
        .args([
            "run-log",
            "append-entry",
            "--log",
            &log.display().to_string(),
            "--category",
            "Nonsense",
            "--entry",
            "- x",
        ])
        .output()
        .expect("append-entry should launch");
    assert_eq!(bad_category.status.code(), Some(1));
    assert_eq!(
        envelope(&bad_category.stdout).get("ERROR"),
        Some(&"unsupported category: Nonsense".to_owned())
    );

    // The mutually exclusive entry group is required.
    let neither = larch()
        .args([
            "run-log",
            "append-entry",
            "--log",
            &log.display().to_string(),
            "--category",
            "Warnings",
        ])
        .output()
        .expect("append-entry should launch");
    assert_eq!(neither.status.code(), Some(1));
    assert!(envelope(&neither.stdout).contains_key("USAGE"));
}

#[test]
fn append_failure_formats_diagnostics_and_refuses_bad_counts() {
    let fixture = Fixture::new();
    let log = fixture.log_root.parent().expect("parent").join("issues.md");
    let capture = fixture.write_source(
        "capture.txt",
        "boom\ntoken sk-ant-abcdefghijklmnopqrstuvwxyz0123\n",
    );

    let output = larch()
        .args([
            "run-log",
            "append-failure",
            "--log",
            &log.display().to_string(),
            "--site",
            "implement Step 2",
            "--tool",
            "codex-implement",
            "--exit-code",
            "9",
            "--category",
            "Tool Failures",
            "--output-file",
            &capture.display().to_string(),
            "--retry-count",
            "3",
            "--redact",
        ])
        .output()
        .expect("append-failure should launch");
    assert!(output.status.success(), "append-failure should succeed");
    let body = fs::read_to_string(&log).expect("ledger should read");
    assert!(body.contains("### Tool Failures"));
    assert!(
        body.contains("- **Step implement Step 2: codex-implement failed (exit 9, retries=3)**:")
    );
    assert!(body.contains("boom"));
    assert!(
        !body.contains("sk-ant-"),
        "--redact scrubs the captured body"
    );

    let bad_retry = larch()
        .args([
            "run-log",
            "append-failure",
            "--log",
            &log.display().to_string(),
            "--site",
            "implement Step 2",
            "--tool",
            "codex-implement",
            "--exit-code",
            "9",
            "--category",
            "Tool Failures",
            "--output-file",
            &capture.display().to_string(),
            "--retry-count",
            "many",
        ])
        .output()
        .expect("append-failure should launch");
    assert_eq!(bad_retry.status.code(), Some(1));
    assert_eq!(
        envelope(&bad_retry.stdout).get("ERROR"),
        Some(&"--retry-count must be a non-negative integer".to_owned())
    );
}

#[test]
fn append_failure_synthesizes_a_body_when_no_diagnostics_were_captured() {
    let fixture = Fixture::new();
    let log = fixture.log_root.parent().expect("parent").join("issues.md");

    let output = larch()
        .args([
            "run-log",
            "append-failure",
            "--log",
            &log.display().to_string(),
            "--site",
            "design Step 5b",
            "--tool",
            "file-oos-prepare",
            "--exit-code",
            "0",
            "--category",
            "Warnings",
            "--output-file",
            "/nonexistent/capture.log",
        ])
        .output()
        .expect("append-failure should launch");
    assert!(output.status.success());
    let body = fs::read_to_string(&log).expect("ledger should read");
    assert!(body.contains("no diagnostics captured (exit 0)"));
}

#[test]
fn append_failure_strips_diagram_bodies_from_warnings() {
    let fixture = Fixture::new();
    let log = fixture.log_root.parent().expect("parent").join("issues.md");
    let capture = fixture.write_source("diagram.log", "```mermaid\ngraph TD\nA-->B\n```\n");

    let output = larch()
        .args([
            "run-log",
            "append-failure",
            "--log",
            &log.display().to_string(),
            "--site",
            "design Step 5b.5 diagram",
            "--tool",
            "diagram-generator",
            "--exit-code",
            "2",
            "--category",
            "Warnings",
            "--output-file",
            &capture.display().to_string(),
        ])
        .output()
        .expect("append-failure should launch");
    assert!(output.status.success());
    let body = fs::read_to_string(&log).expect("ledger should read");
    assert!(body.contains("diagram-content-redacted"));
    assert!(!body.contains("graph TD"), "diagram bodies never persist");
}

#[test]
fn concurrent_appends_from_separate_processes_never_interleave_a_record() {
    let fixture = Fixture::new();
    let log = fixture.log_root.parent().expect("parent").join("issues.md");
    let binary = larch_path();

    let writers = 8;
    let children: Vec<_> = (0..writers)
        .map(|index| {
            Command::new(&binary)
                .args([
                    "run-log",
                    "append-entry",
                    "--log",
                    &log.display().to_string(),
                    "--category",
                    "Warnings",
                    "--entry",
                    &format!("- entry-{index}"),
                ])
                .spawn()
                .expect("child should spawn")
        })
        .collect();
    for mut child in children {
        assert!(
            child.wait().expect("child should finish").success(),
            "every concurrent append should succeed"
        );
    }

    let body = fs::read_to_string(&log).expect("ledger should read");
    for index in 0..writers {
        assert_eq!(
            body.matches(&format!("- entry-{index}")).count(),
            1,
            "entry-{index} should appear exactly once in:\n{body}"
        );
    }
    assert_eq!(
        body.matches("### Warnings").count(),
        1,
        "concurrent appends share one category heading"
    );
}

#[test]
fn verify_completeness_reports_ok_missing_and_manifest_defects() {
    let fixture = Fixture::new();
    let run_dir = fixture.run_dir();
    fs::create_dir_all(&run_dir).expect("run dir should create");
    let manifest_tsv = fixture
        .log_root
        .parent()
        .expect("parent")
        .join("required.tsv");

    // An unreadable run directory refuses before any manifest work.
    let missing_dir = verify(&run_dir.join("absent"), &manifest_tsv);
    assert_eq!(missing_dir.status.code(), Some(1));
    assert!(
        String::from_utf8_lossy(&missing_dir.stderr).contains("run dir not found"),
        "stderr names the missing run directory"
    );

    // A manifest-less run directory reports the manifest as missing.
    fs::write(
        &manifest_tsv,
        "relative_path\tcondition\nmanifest.json\talways\n",
    )
    .expect("required files manifest should write");
    let no_manifest = verify(&run_dir, &manifest_tsv);
    assert_eq!(no_manifest.status.code(), Some(1));
    assert_eq!(
        String::from_utf8_lossy(&no_manifest.stdout).trim(),
        "MISSING=manifest"
    );

    fs::write(
        run_dir.join("manifest.json"),
        "{\"schema_version\": 2, \"status\": \"merged\", \"steps_ran\": {\"step18\": true}}\n",
    )
    .expect("manifest should write");
    let complete = verify(&run_dir, &manifest_tsv);
    assert!(complete.status.success());
    assert_eq!(String::from_utf8_lossy(&complete.stdout).trim(), "OK");

    // A step18-conditioned row is reachable and absent.
    fs::write(
        &manifest_tsv,
        "relative_path\tcondition\nmanifest.json\talways\nfinal-summary.md\tstep18\n",
    )
    .expect("required files manifest should write");
    let missing = verify(&run_dir, &manifest_tsv);
    assert_eq!(missing.status.code(), Some(1));
    assert_eq!(
        String::from_utf8_lossy(&missing.stdout).trim(),
        "MISSING=final-summary.md"
    );

    // An unparsable manifest is reported as a missing manifest, never coerced.
    fs::write(run_dir.join("manifest.json"), "{not json\n").expect("manifest should write");
    let broken = verify(&run_dir, &manifest_tsv);
    assert_eq!(broken.status.code(), Some(1));
    assert_eq!(
        String::from_utf8_lossy(&broken.stdout).trim(),
        "MISSING=manifest"
    );
}

#[test]
fn verify_completeness_refuses_a_manifest_outside_the_plugin_root() {
    let fixture = Fixture::new();
    let run_dir = fixture.run_dir();
    fs::create_dir_all(&run_dir).expect("run dir should create");
    let outside = tempfile::tempdir().expect("outside root should create");
    let manifest_tsv = outside.path().join("required.tsv");
    // Distinct from the fixture root, so the containment check must refuse it.
    fs::write(&manifest_tsv, "manifest.json\talways\n").expect("manifest should write");

    let output = larch()
        .args([
            "run-log",
            "verify-completeness",
            &run_dir.display().to_string(),
        ])
        .env("LARCH_VERIFY_MANIFEST", &manifest_tsv)
        .env(
            "CLAUDE_PLUGIN_ROOT",
            fixture.log_root.parent().expect("parent"),
        )
        .output()
        .expect("verify-completeness should launch");

    assert_eq!(output.status.code(), Some(1));
    assert!(
        String::from_utf8_lossy(&output.stderr)
            .contains("LARCH_VERIFY_MANIFEST resolves outside repository root")
    );
}

/// Run `verify-completeness` with a caller-supplied required-files manifest.
fn verify(run_dir: &Path, manifest_tsv: &Path) -> std::process::Output {
    larch()
        .args([
            "run-log",
            "verify-completeness",
            &run_dir.display().to_string(),
        ])
        .env("LARCH_VERIFY_MANIFEST", manifest_tsv)
        .env(
            "CLAUDE_PLUGIN_ROOT",
            manifest_tsv.parent().expect("manifest parent"),
        )
        .output()
        .expect("verify-completeness should launch")
}
