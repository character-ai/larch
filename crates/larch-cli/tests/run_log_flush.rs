//! End-to-end contracts for the Rust-owned mutable run-log flush.

#[cfg(unix)]
use std::os::unix::fs::PermissionsExt as _;
use std::{
    collections::BTreeMap,
    env, fs,
    path::{Path, PathBuf},
    process::Output,
};

use assert_cmd::Command as AssertCommand;
use larch_test_support::{
    ExecutionSnapshot, ReportingParityOracle, RunLogFixture, RunLogSnapshot, RunLogTree,
};
use sha2::{Digest as _, Sha256};

struct Fixture {
    _root: tempfile::TempDir,
    tmpdir: PathBuf,
    plugin_root: PathBuf,
    home: PathBuf,
    run_id: &'static str,
}

impl Fixture {
    fn new() -> Self {
        let root = tempfile::tempdir().expect("temporary root");
        let tmpdir = fs::canonicalize(root.path())
            .expect("canonical temporary root")
            .join("session");
        fs::create_dir(&tmpdir).expect("session directory");
        let plugin_root = Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("../..")
            .canonicalize()
            .expect("plugin root");
        let home = root.path().join("home");
        let project = home
            .join(".claude/projects")
            .join(plugin_root.to_string_lossy().replace('/', "-"));
        fs::create_dir_all(&project).expect("Claude project directory");
        fs::write(
            project.join("fallback.jsonl"),
            b"{\"type\":\"user\",\"message\":{\"role\":\"user\",\"content\":\"fallback\"}}\n",
        )
        .expect("fallback transcript");
        Self {
            _root: root,
            tmpdir,
            plugin_root,
            home,
            run_id: "run-abc",
        }
    }

    fn command(&self) -> AssertCommand {
        let process_tmp = self.tmpdir.parent().unwrap().join("process-tmp");
        fs::create_dir_all(&process_tmp).expect("process temporary directory");
        let mut command = AssertCommand::cargo_bin("larch").expect("larch binary");
        for (key, _value) in env::vars_os() {
            let name = key.to_string_lossy();
            if name.starts_with("LARCH_") || name.starts_with("CLAUDE_") {
                command.env_remove(key);
            }
        }
        command
            .env("CLAUDE_PLUGIN_ROOT", &self.plugin_root)
            .env("HOME", &self.home)
            .env_remove("IMPLEMENT_TMPDIR")
            .env_remove("DESIGN_TMPDIR")
            .env_remove("REVIEW_TMPDIR")
            // The live session root is cache-backed, not below TMPDIR. Keep the
            // fixture roots separate so delegated renderers exercise that path.
            .env("TMPDIR", process_tmp)
            .env("LARCH_TEST_TIMING_NOW", "20");
        command
    }

    fn run_dir(&self) -> PathBuf {
        self.tmpdir.join("larch-logs/implement").join(self.run_id)
    }

    fn manifest(&self) -> serde_json::Value {
        serde_json::from_slice(&fs::read(self.run_dir().join("manifest.json")).unwrap()).unwrap()
    }

    fn terminal(&self) -> Output {
        self.terminal_at(&self.tmpdir)
    }

    fn terminal_at(&self, tmpdir: &Path) -> Output {
        self.command()
            .args(["run-log", "prepare-terminal-snapshot", "--implement-tmpdir"])
            .arg(tmpdir)
            .args(["--run-id", self.run_id, "--repo-root"])
            .arg(&self.plugin_root)
            .args(["--no-logs-commit", "false"])
            .output()
            .expect("terminal command")
    }

    fn seed_terminal(&self) {
        fs::create_dir_all(self.run_dir()).expect("run directory");
        fs::write(self.tmpdir.join("session-id"), format!("{}\n", self.run_id))
            .expect("session id");
        fs::write(
            self.tmpdir.join("parent-issue.md"),
            format!(
                "RUN_ID={}\nISSUE_NUMBER=0\nREPO=o/r\nBRANCH=feature\n",
                self.run_id
            ),
        )
        .expect("parent issue");
        fs::write(
            self.tmpdir.join("finalize-state.sh"),
            format!(
                "RUN_ID={}\nNO_LOGS_COMMIT=false\nSTALL_TRACKING=false\n",
                self.run_id
            ),
        )
        .expect("finalize state");
        fs::write(self.tmpdir.join("run-flags.sh"), "FORCE_REQUESTED=false\n").expect("run flags");
        let transcript = self.tmpdir.join("raw.jsonl");
        fs::write(
            &transcript,
            b"{\"type\":\"user\",\"message\":{\"role\":\"user\",\"content\":\"hello\"}}\n",
        )
        .expect("transcript");
        let source = self.tmpdir.join("source.env");
        fs::write(
            &source,
            format!(
                "TRANSCRIPT_PATH={}\nSESSION_DIR={}\nSESSION_UUID=session-uuid\n",
                transcript.display(),
                self.tmpdir.display()
            ),
        )
        .expect("source");
        let ledger = self.tmpdir.join(format!(
            "larch-tokens-{:x}.jsonl",
            Sha256::digest(self.run_id.as_bytes())
        ));
        fs::write(
            ledger,
            b"{\"type\":\"mark\",\"step\":\"Step 1\",\"ts\":\"2026-05-06T00:00:00Z\"}\n",
        )
        .expect("token ledger");
        let timing = self.tmpdir.join("timing-ledger.tsv");
        fs::write(
            &timing,
            concat!(
                "v1\tmark\t10\timplement\tStep 1\t-\t-\t-\t-\t-\t-\t-\t-\n",
                "malformed timing row\n",
                "v1\tvendor\t9999999999\timplement\t-\tcodex\tcodex-review\t10\t20\t10\tout.txt\t0\tcomplete\n"
            ),
        )
        .expect("timing ledger");
        fs::write(
            self.tmpdir.join("session-env.sh"),
            format!(
                "LARCH_CLAUDE_SOURCE_FILE={}\nLARCH_TOKEN_SESSION_ID={}\nLARCH_TIMING_LEDGER={}\n",
                source.display(),
                self.run_id,
                timing.display()
            ),
        )
        .expect("session environment");
    }
}

#[cfg(unix)]
#[test]
fn capture_refuses_a_log_root_that_escapes_the_configured_session() {
    use std::os::unix::fs::symlink;

    let fixture = Fixture::new();
    let outside = fixture.tmpdir.parent().unwrap().join("outside-capture");
    fs::create_dir(&outside).expect("outside directory");
    let escape = fixture.tmpdir.join("escape");
    symlink(&outside, &escape).expect("escape link");
    let raw = fixture.tmpdir.join("raw.jsonl");
    fs::write(
        &raw,
        b"{\"type\":\"user\",\"message\":{\"role\":\"user\",\"content\":\"hello\"}}\n",
    )
    .expect("transcript");
    let source = fixture.tmpdir.join("source.env");
    fs::write(&source, format!("TRANSCRIPT_PATH={}\n", raw.display())).expect("source file");

    let output = fixture
        .command()
        .env("IMPLEMENT_TMPDIR", &fixture.tmpdir)
        .args(["run-log", "capture-transcript", "--source-file"])
        .arg(source)
        .args(["--log-root"])
        .arg(escape.join("larch-logs"))
        .args(["--skill", "review", "--run-id", fixture.run_id])
        .output()
        .expect("capture command");

    assert!(output.status.success());
    assert_eq!(output.stdout, b"SESSION_TRANSCRIPT_STATUS=write-failed\n");
    assert!(!outside.join("larch-logs").exists());
}

#[test]
fn capture_handles_non_utf8_and_retains_prior_bytes_on_retry() {
    let fixture = Fixture::new();
    let raw = fixture.tmpdir.join("raw transcript.jsonl");
    let mut raw_bytes = vec![0xff, b'\n'];
    raw_bytes
        .extend(b"{\"type\":\"user\",\"message\":{\"role\":\"user\",\"content\":\"hello\"}}\n");
    fs::write(&raw, raw_bytes).expect("non-UTF-8 transcript");
    let source = fixture.tmpdir.join("source.env");
    let mut source_bytes = vec![0xff, b'\n'];
    source_bytes.extend(format!("TRANSCRIPT_PATH={}\n", raw.display()).as_bytes());
    fs::write(&source, source_bytes).expect("non-UTF-8 source file");
    #[cfg(not(unix))]
    let log_root = fixture.tmpdir.join("larch-logs");
    #[cfg(unix)]
    let log_root = {
        use std::os::unix::fs::symlink;
        let parent = fixture.tmpdir.parent().unwrap();
        let alias = parent.join("capture-ancestor-alias");
        symlink(parent, &alias).expect("capture ancestor alias");
        alias.join("session/larch-logs")
    };
    let output = fixture
        .command()
        .args(["run-log", "capture-transcript", "--source-file"])
        .arg(&source)
        .args(["--log-root"])
        .arg(log_root)
        .args([
            "--skill",
            "review",
            "--run-id",
            fixture.run_id,
            "--refresh-mode",
            "true",
        ])
        .output()
        .expect("capture command");
    assert!(output.status.success());
    assert_eq!(output.stdout, b"SESSION_TRANSCRIPT_STATUS=captured\n");
    let staged = fixture
        .tmpdir
        .join("larch-logs/review/run-abc/session-transcript.jsonl");
    let expected = concat!(
        "{\"v\":3,\"source_basename\":\"raw transcript.jsonl\",\"turns\":1,\"policy\":\"prose-errors-and-reference-reads\"}\n",
        "{\"turn\":1,\"role\":\"user\",\"blocks\":[{\"type\":\"text\",\"value\":\"hello\"}]}\n"
    ).as_bytes();
    assert_eq!(fs::read(&staged).expect("staged transcript"), expected);
    fs::remove_file(&source).expect("remove source");
    #[cfg(unix)]
    {
        use std::os::unix::fs::symlink;
        let target = fixture.tmpdir.join("source-target.env");
        fs::write(&target, format!("TRANSCRIPT_PATH={}\n", raw.display())).expect("source target");
        symlink(target, &source).expect("symlinked source");
    }
    let retry = fixture
        .command()
        .args(["run-log", "capture-transcript", "--source-file"])
        .arg(&source)
        .args(["--log-root"])
        .arg(fixture.tmpdir.join("larch-logs"))
        .args([
            "--skill",
            "review",
            "--run-id",
            fixture.run_id,
            "--refresh-mode",
            "true",
        ])
        .output()
        .expect("retry capture");
    assert_eq!(
        retry.stdout,
        b"SESSION_TRANSCRIPT_STATUS=source-file-missing\n"
    );
    assert_eq!(fs::read(staged).expect("retained transcript"), expected);
}

#[test]
fn capture_uses_cache_scratch_for_an_ancestor_of_the_active_repo() {
    let fixture = Fixture::new();
    let fake_repo = fixture.tmpdir.join("checkout");
    fs::create_dir_all(fake_repo.join(".git")).expect("fake repository");
    let raw = fixture.tmpdir.join("raw.jsonl");
    fs::write(
        &raw,
        b"{\"type\":\"user\",\"message\":{\"role\":\"user\",\"content\":\"hello\"}}\n",
    )
    .expect("transcript");
    let source = fixture.tmpdir.join("source.env");
    fs::write(&source, format!("TRANSCRIPT_PATH={}\n", raw.display())).expect("source file");
    let home = fixture.tmpdir.join("home");

    let output = fixture
        .command()
        .current_dir(&fake_repo)
        .env("HOME", &home)
        .args(["run-log", "capture-transcript", "--source-file"])
        .arg(&source)
        .args(["--log-root"])
        .arg(fixture.tmpdir.join("larch-logs"))
        .args(["--skill", "review", "--run-id", fixture.run_id])
        .output()
        .expect("capture command");

    assert!(output.status.success());
    assert_eq!(output.stdout, b"SESSION_TRANSCRIPT_STATUS=captured\n");
    assert!(home.join(".cache/larch/sessions").is_dir());
}

#[test]
fn terminal_flush_is_complete_atomic_and_idempotent() {
    let fixture = Fixture::new();
    fixture.seed_terminal();
    let parts = fixture.tmpdir.join("vendor-failure-diagnostics.parts");
    fs::create_dir_all(parts.join("nested")).expect("parts directory");
    fs::write(parts.join("part.2"), "second\n").expect("second part");
    fs::write(parts.join("nested/part.1"), "first\n").expect("first part");
    #[cfg(unix)]
    {
        use std::os::unix::fs::symlink;
        let outside = fixture.tmpdir.join("outside-parts");
        fs::create_dir(&outside).expect("outside parts");
        fs::write(outside.join("part.0"), "must-not-publish\n").expect("outside part");
        symlink(outside, parts.join("linked")).expect("linked parts directory");
    }
    fs::write(
        fixture.run_dir().join("token-report.json"),
        "prior-complete-bytes\n",
    )
    .expect("prior report");
    fs::write(
        fixture
            .run_dir()
            .join(".manifest-token-report.interrupted.tmp"),
        "partial",
    )
    .expect("partial temp");

    let first = fixture.terminal();
    assert!(
        first.status.success(),
        "{}",
        String::from_utf8_lossy(&first.stderr)
    );
    assert!(String::from_utf8_lossy(&first.stdout).contains("TERMINAL_SNAPSHOT_STATUS=prepared"));
    assert_eq!(
        fs::read_to_string(fixture.run_dir().join("vendor-failure-diagnostics.txt")).unwrap(),
        "first\nsecond\n"
    );
    let names = [
        "execution-issues.ndjson",
        "final-summary.md",
        "session-transcript.jsonl",
        "timing-report.json",
        "token-report.json",
        "vendor-failure-diagnostics.txt",
    ];
    #[cfg(unix)]
    for name in names.into_iter().chain(["manifest.json"]) {
        let mode = fs::metadata(fixture.run_dir().join(name))
            .unwrap()
            .permissions()
            .mode();
        assert_eq!(mode & 0o777, 0o600, "unsafe mode for {name}");
    }
    let before: BTreeMap<_, _> = names
        .into_iter()
        .map(|name| {
            (
                name,
                fs::read(fixture.run_dir().join(name)).expect("terminal artifact"),
            )
        })
        .collect();
    let manifest_path = fixture.run_dir().join("manifest.json");
    let mut manifest: serde_json::Value =
        serde_json::from_slice(&fs::read(&manifest_path).unwrap()).unwrap();
    manifest["updated_at"] = serde_json::Value::String("fixed-for-idempotence".to_owned());
    fs::write(
        &manifest_path,
        serde_json::to_string_pretty(&manifest).unwrap() + "\n",
    )
    .unwrap();
    let manifest_before = fs::read(&manifest_path).unwrap();
    let mut golden = Sha256::new();
    for (name, bytes) in &before {
        golden.update(name.as_bytes());
        golden.update(bytes);
    }
    assert_eq!(
        format!("{:x}", golden.finalize()),
        "18fb26c1f237f8887839815f3fee0d650faf07ff2133bdd7291c10970a4b08d8",
        // Re-pinned for issue 8090: the terminal report is Rust-owned, so the
        // review-phase prefix renders in process instead of through a child
        // that this sandbox cannot launch, and the priced cost degrades to
        // `N/A` because the still-Python `token report` verb is unreachable
        // here. Every other byte is unchanged from the retired Python owner.
        "terminal snapshot bytes drifted from the Rust final-report owner",
    );
    let second = fixture.terminal();
    assert!(
        second.status.success(),
        "{}",
        String::from_utf8_lossy(&second.stderr)
    );
    let after: BTreeMap<_, _> = names
        .into_iter()
        .map(|name| {
            (
                name,
                fs::read(fixture.run_dir().join(name)).expect("repeated artifact"),
            )
        })
        .collect();
    assert_eq!(after, before);
    assert_eq!(fs::read(manifest_path).unwrap(), manifest_before);
}

#[cfg(unix)]
#[test]
fn terminal_accepts_a_symlinked_ancestor_spelling() {
    use std::os::unix::fs::symlink;

    let fixture = Fixture::new();
    fixture.seed_terminal();
    let parent = fixture.tmpdir.parent().unwrap();
    let alias = parent.join("ancestor-alias");
    symlink(parent, &alias).expect("symlinked ancestor");

    let output = fixture.terminal_at(&alias.join("session"));

    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(String::from_utf8_lossy(&output.stdout).contains("TERMINAL_SNAPSHOT_STATUS=prepared"));
}

#[test]
fn refresh_refuses_a_preterminal_terminal_outcome() {
    let fixture = Fixture::new();
    fixture.seed_terminal();
    fs::create_dir_all(fixture.run_dir()).expect("run directory");
    let summary = fixture.run_dir().join("final-summary.md");
    fs::write(&summary, "## /implement run run-abc: stalled\n").expect("terminal summary");

    let output = fixture
        .command()
        .args(["run-log", "refresh", "--implement-tmpdir"])
        .arg(&fixture.tmpdir)
        .args(["--run-id", fixture.run_id, "--no-logs-commit", "false"])
        .output()
        .expect("refresh command");

    assert!(output.status.success());
    assert!(
        String::from_utf8_lossy(&output.stdout)
            .contains("REFRESH_COMMITTED=false REASON=preterminal-outcome")
    );
    assert_eq!(
        fs::read_to_string(summary).unwrap(),
        "## /implement run run-abc: stalled\n"
    );
}

#[test]
fn checkpoint_flushes_pending_execution_issues_once() {
    let fixture = Fixture::new();
    fixture.seed_terminal();
    fs::write(fixture.tmpdir.join(".execution-issues-step7a-reached"), "")
        .expect("step 7a sentinel");
    fs::write(
        fixture.tmpdir.join("execution-issues.md"),
        "### Warnings\n- architectural-guidelines warning\n",
    )
    .expect("pending warning");

    let checkpoint = || {
        fixture
            .command()
            .env("IMPLEMENT_TMPDIR", &fixture.tmpdir)
            .args(["run-log", "checkpoint"])
            .output()
            .expect("checkpoint command")
    };
    let first = checkpoint();

    assert!(first.status.success());
    let batch = fixture.run_dir().join("execution-issues.ndjson");
    let before = fs::read(&batch).expect("execution issues batch");
    assert!(String::from_utf8_lossy(&before).contains("architectural-guidelines warning"));
    assert!(
        fixture
            .tmpdir
            .join(".execution-issues-flushed.sha")
            .is_file()
    );

    let second = checkpoint();
    assert!(second.status.success());
    assert_eq!(fs::read(batch).unwrap(), before);
}

#[test]
fn refresh_skips_every_terminal_merge_result() {
    let fixture = Fixture::new();
    fixture.seed_terminal();
    for merge_result in ["merged", "admin_merged", "already_merged"] {
        let output = fixture
            .command()
            .args(["run-log", "refresh", "--implement-tmpdir"])
            .arg(&fixture.tmpdir)
            .args([
                "--run-id",
                fixture.run_id,
                "--no-logs-commit",
                "false",
                "--merge-result",
                merge_result,
            ])
            .output()
            .expect("refresh command");
        assert!(output.status.success());
        assert_eq!(output.stdout, b"REFRESH_SKIPPED=true REASON=post-merge\n");
    }
}

#[test]
fn refresh_persisted_state_outranks_context_defaults() {
    let fixture = Fixture::new();
    fixture.seed_terminal();
    let state = fixture.tmpdir.join("persisted-state.env");
    fs::write(&state, "RUN_ID=run-abc\nNO_LOGS_COMMIT=true\n").expect("persisted state");
    let output = fixture
        .command()
        .args(["run-log", "refresh", "--state-file"])
        .arg(state)
        .args(["--implement-tmpdir"])
        .arg(&fixture.tmpdir)
        .args(["--run-id", fixture.run_id, "--no-logs-commit", "false"])
        .output()
        .expect("refresh command");
    assert!(output.status.success());
    assert_eq!(
        output.stdout,
        b"REFRESH_SKIPPED=true REASON=no-logs-commit\n"
    );

    fs::write(
        fixture.tmpdir.join("finalize-state.sh"),
        "RUN_ID=stale-run\nNO_LOGS_COMMIT=true\n",
    )
    .expect("stale default state");
    let explicit = fixture
        .command()
        .args(["run-log", "refresh", "--implement-tmpdir"])
        .arg(&fixture.tmpdir)
        .args(["--run-id", fixture.run_id, "--no-logs-commit", "false"])
        .output()
        .expect("context-only refresh command");
    assert_eq!(
        explicit.stdout,
        b"SESSION_TRANSCRIPT_STATUS=captured\nREFRESH_COMMITTED=true\n"
    );
}

#[test]
fn terminal_capture_failure_is_durable() {
    let fixture = Fixture::new();
    fixture.seed_terminal();
    fs::remove_file(fixture.tmpdir.join("raw.jsonl")).expect("remove transcript source");

    let failed = fixture.terminal();
    assert!(!failed.status.success());
    assert!(String::from_utf8_lossy(&failed.stdout).contains("TERMINAL_SNAPSHOT_STATUS=failed"));
    let issues = fs::read_to_string(fixture.run_dir().join("execution-issues.ndjson"))
        .expect("durable execution issues");
    assert!(issues.contains("session-transcript"), "{issues}");
    assert!(issues.contains("Step 18 terminal snapshot"));
}

#[test]
fn terminal_unconfigured_transcript_is_durably_waived() {
    let fixture = Fixture::new();
    fixture.seed_terminal();
    let session = fs::read_to_string(fixture.tmpdir.join("session-env.sh")).unwrap();
    fs::write(
        fixture.tmpdir.join("session-env.sh"),
        session
            .lines()
            .filter(|line| !line.starts_with("LARCH_CLAUDE_SOURCE_FILE="))
            .collect::<Vec<_>>()
            .join("\n")
            + "\n",
    )
    .unwrap();

    let output = fixture.terminal();

    assert!(
        output.status.success(),
        "stdout={} stderr={}",
        String::from_utf8_lossy(&output.stdout),
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(!fixture.run_dir().join("session-transcript.jsonl").exists());
    let issues = fs::read_to_string(fixture.run_dir().join("execution-issues.ndjson")).unwrap();
    assert!(issues.contains("session-transcript status=source-not-configured"));
}

#[test]
fn terminal_preserves_the_merge_downgrade_warning() {
    let fixture = Fixture::new();
    fixture.seed_terminal();
    fs::write(
        fixture.tmpdir.join("ship-pr-state.sh"),
        "PR_NUMBER=17\nMERGE=false\n",
    )
    .expect("ship state");
    fs::write(fixture.tmpdir.join("ship-seed-input.env"), "MERGE=true\n").expect("ship seed");
    fs::write(
        fixture.tmpdir.join("stall-recovery-classification.env"),
        "STALL_STEP=5\nRESUME_HINT=step8-shippr\n",
    )
    .expect("classification");
    fs::write(
        fixture.tmpdir.join("execution-issues.md"),
        "### Warnings\n- panel-failed recovery retained the PR for manual merge.\n",
    )
    .expect("panel failure evidence");

    let output = fixture.terminal();

    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    let summary = fs::read_to_string(fixture.run_dir().join("final-summary.md")).unwrap();
    assert!(summary.contains("**⚠ Merge downgraded**"), "{summary}");
}

#[cfg(unix)]
#[test]
fn postmerge_marks_done_only_after_report_success() {
    use std::os::unix::fs::symlink;

    let fixture = Fixture::new();
    fixture.seed_terminal();
    assert!(fixture.terminal().status.success());
    let summary = fixture.tmpdir.join("summary-final.md");
    fs::remove_file(&summary).unwrap();
    symlink(fixture.tmpdir.join("raw.jsonl"), &summary).unwrap();

    let failed = fixture
        .command()
        .args(["run-log", "refresh", "--implement-tmpdir"])
        .arg(&fixture.tmpdir)
        .args([
            "--run-id",
            fixture.run_id,
            "--postmerge",
            "true",
            "--merge-result",
            "merged",
            "--pr-number",
            "17",
        ])
        .output()
        .unwrap();
    assert!(String::from_utf8_lossy(&failed.stdout).contains("REASON=post-merge-refresh-failed"));
    assert_eq!(fixture.manifest()["status"], "in-progress");

    fs::remove_file(summary).unwrap();
    let completed = fixture
        .command()
        .args(["run-log", "refresh", "--implement-tmpdir"])
        .arg(&fixture.tmpdir)
        .args([
            "--run-id",
            fixture.run_id,
            "--postmerge",
            "true",
            "--render-reports",
            "false",
            "--merge-result",
            "merged",
            "--pr-number",
            "17",
        ])
        .output()
        .unwrap();
    assert_eq!(completed.stdout, b"REFRESH_COMMITTED=true\n");
    assert_eq!(fixture.manifest()["status"], "done");
    assert_eq!(fixture.manifest()["pr_number"], 17);
}

#[test]
fn failed_capture_preserves_the_shared_terminal_fixture() {
    let tree = RunLogTree::builder(RunLogFixture::TranscriptCredentials)
        .build()
        .expect("shared run-log fixture");
    let before = RunLogSnapshot::capture(&tree, ExecutionSnapshot::success())
        .expect("snapshot before capture");
    let missing = tree.root().join("missing-source.env");

    let output = AssertCommand::cargo_bin("larch")
        .expect("larch binary")
        .args(["run-log", "capture-transcript", "--source-file"])
        .arg(missing)
        .args(["--log-root"])
        .arg(tree.staging_root())
        .args(["--skill", tree.skill(), "--run-id", tree.run_id()])
        .output()
        .expect("capture command");

    assert!(output.status.success());
    assert_eq!(
        output.stdout,
        b"SESSION_TRANSCRIPT_STATUS=source-file-missing\n"
    );
    let after = RunLogSnapshot::capture(&tree, ExecutionSnapshot::success())
        .expect("snapshot after capture");
    assert!(
        ReportingParityOracle::new()
            .compare_run_logs(&before, &after)
            .is_empty()
    );
}
