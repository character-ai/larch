//! End-to-end `final-report write` and `final-report step18b` composition.
//!
//! The fixtures below are the artifact set a recorded `/implement` run
//! leaves in its temporary root, reduced to the files the terminal report
//! reads. Assertions pin the rendered bytes the retired Python owner produced
//! for the same inputs.

use std::{
    collections::BTreeMap,
    fs,
    path::{Path, PathBuf},
    process::Command,
};

use larch_core::{DuplicatePolicy, KvDocument, ParseOptions};
use tempfile::TempDir;

const RUN_ID: &str = "20260808-120000-abcdef";

struct Run {
    _sandbox: TempDir,
    tmpdir: PathBuf,
}

impl Run {
    fn create() -> Self {
        let sandbox = TempDir::new().expect("sandbox");
        let root = sandbox.path().canonicalize().expect("canonical sandbox");
        let tmpdir = root.join("implement-tmpdir");
        let run_dir = tmpdir.join("larch-logs").join("implement").join(RUN_ID);
        fs::create_dir_all(&run_dir).expect("run directory");
        Self {
            _sandbox: sandbox,
            tmpdir,
        }
    }

    fn run_dir(&self) -> PathBuf {
        self.tmpdir
            .join("larch-logs")
            .join("implement")
            .join(RUN_ID)
    }

    fn write(&self, relative: &str, body: &str) {
        let path = self.tmpdir.join(relative);
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent).expect("parent directory");
        }
        fs::write(path, body).expect("fixture write");
    }

    fn command(&self, verb: &str) -> Command {
        let mut command = Command::new(env!("CARGO_BIN_EXE_larch"));
        command
            .arg("final-report")
            .arg(verb)
            .arg("--implement-tmpdir")
            .arg(&self.tmpdir)
            // Keep the delegated Python verbs unreachable so the assertions
            // cover the Rust composition and its documented degraded sections.
            .env_remove("CLAUDE_PLUGIN_ROOT")
            .env_remove("CLAUDE_CODE_EFFORT_LEVEL")
            .env_remove("CLAUDE_EFFORT")
            .env_remove("LARCH_TEST_PLUGIN_VERSION");
        command
    }
}

/// A shipped run with review tallies, timing, filed OOS issues, and a manifest.
fn shipped_run() -> Run {
    let run = Run::create();
    run.write(
        "parent-issue.md",
        &format!("ISSUE_NUMBER=4242\nRUN_ID={RUN_ID}\n"),
    );
    run.write(
        "session-env.sh",
        "REPO=character-ai/larch\nMODE=implement\nWORKFLOW_PATH=standard\nREPO_UNAVAILABLE=true\n",
    );
    run.write(
        "ship-pr-state.sh",
        "PR_NUMBER=8260\nPR_URL=https://github.com/character-ai/larch/pull/8260\n\
DURATION=00:41:07\nLINES_PR_NUMBER=8260\nLINES_STATUS=ok\nCODE_ADDED=1204\n\
CODE_DELETED=1470\nLOGS_ADDED=88\nLOGS_DELETED=0\n",
    );
    run.write("run-flags.sh", "FORCE_REQUESTED=false\n");
    let run_dir = format!("larch-logs/implement/{RUN_ID}");
    run.write(
        &format!("{run_dir}/manifest.json"),
        r#"{"schema_version": 2, "skill": "implement", "status": "done",
            "pr_number": 8260, "larch_version": "56.2.2",
            "model_roster": {"main": "claude-opus-4-8"}, "effort": "high",
            "steps_ran": {}, "run_id": "20260808-120000-abcdef",
            "issue_number": 4242, "started_at": "2026-08-08T12:00:00Z"}"#,
    );
    run.write(
        &format!("{run_dir}/plan-review-tally.json"),
        r#"{"phase": "plan-review", "accepted_count": 3, "rejected_count": 5}"#,
    );
    run.write(
        &format!("{run_dir}/code-review-tally.json"),
        r#"{"phase": "code-review", "accepted_count": 2, "rejected_count": 6}"#,
    );
    run.write(
        &format!("{run_dir}/timing-report.json"),
        r#"{"total_hms": "00:41:07", "total_seconds": 2467}"#,
    );
    run.write(
        &format!("{run_dir}/oos-issues.ndjson"),
        "{\"body\": \"- **Filed URL**: https://github.com/character-ai/larch/issues/8261\\n\"}\n",
    );
    run.write(
        &format!("{run_dir}/difficulty-rating.json"),
        r#"{"predicted_tier": "MODERATE", "applied_tier": "HARD",
            "floors_applied": ["plan-size"]}"#,
    );
    run.write(
        &format!("{run_dir}/token-report.json"),
        r#"{"claude": {"totals": {"total": 1200000}},
            "BUCKETS_claude": {"input": 100000, "cache_read": 900000,
                               "cache_create_5m": 150000, "cache_create_1h": 0,
                               "output": 50000}}"#,
    );
    run
}

fn kv(stdout: &str) -> BTreeMap<String, String> {
    KvDocument::parse(stdout, ParseOptions::legacy())
        .expect("KEY=value envelope")
        .select(DuplicatePolicy::Last)
}

fn summary(path: &Path) -> String {
    fs::read_to_string(path).expect("rendered summary")
}

#[test]
fn write_composes_the_terminal_summary_for_a_shipped_run() {
    let run = shipped_run();
    let output = run
        .command("write")
        .arg("--skip-tracking-upsert")
        .output()
        .expect("final-report write");
    let stdout = String::from_utf8_lossy(&output.stdout).into_owned();
    let values = kv(&stdout);
    assert_eq!(values.get("STATUS").map(String::as_str), Some("ok"));
    assert_eq!(values.get("COMMENT_URL").map(String::as_str), Some(""));
    assert!(output.status.success(), "stdout: {stdout}");

    let body = summary(&run.tmpdir.join("summary-final.md"));
    assert_eq!(
        body,
        format!(
            "## Review Phase Detail\n\
\n\
No review rounds completed.\n\
\n\
## /implement run {RUN_ID}: pr-created\n\
\n\
- **Outcome**: \u{2705} DONE\n\
- **Path**: standard\n\
- **Duration**: 00:41:07\n\
- **Cost**: \u{1f4b0} TOTAL ~$3.14: Claude $3.14, Codex-5.6 $0.00, Codex-mini $0.00, \
Cursor $0.00, Claude (subprocess) $0.00  |  Tokens: 1200k\n\
- **Issue**: #4242: https://github.com/character-ai/larch/issues/4242\n\
- **PR**: #8260: https://github.com/character-ai/larch/pull/8260\n\
- **Plan review**: 3/8 accepted\n\
- **Difficulty**: predicted MODERATE, applied HARD, floor raised\n\
- **Dynamic archetypes**: unknown\n\
- **Code review**: 2/8 accepted\n\
- **Lines (PR diff)**: code +1204/-1470, larch-logs +88/-0\n\
- **OOS filed**: 1: https://github.com/character-ai/larch/issues/8261\n\
- **Exec issues**: 0\n\
- **Warnings**: 0\n\
- **Run log**: provider `unknown`, skill `implement`, run ID `{RUN_ID}`\n\
- **Main agent model**: claude-opus-4-8\n\
- **Effort**: high\n\
- **Larch version**: 56.2.2\n\
\n\
<!-- larch:run-summary v=1 -->\n"
        )
    );
    // The committed run-log copy is written whenever `--comment-only` is absent.
    assert_eq!(summary(&run.run_dir().join("final-summary.md")), body);
}

#[test]
fn write_never_embeds_the_temporary_root_or_a_credential() {
    let run = shipped_run();
    let _output = run
        .command("write")
        .arg("--skip-tracking-upsert")
        .output()
        .expect("final-report write");
    let body = summary(&run.tmpdir.join("summary-final.md"));
    assert!(!body.contains(&run.tmpdir.display().to_string()));
    assert!(!body.contains("ghp_"));
}

#[test]
fn write_degrades_missing_timing_token_and_findings_inputs() {
    let run = Run::create();
    run.write(
        "parent-issue.md",
        &format!("ISSUE_NUMBER=0\nRUN_ID={RUN_ID}\n"),
    );
    run.write("session-env.sh", "REPO_UNAVAILABLE=true\n");
    let output = run
        .command("write")
        .arg("--skip-tracking-upsert")
        .output()
        .expect("final-report write");
    assert!(output.status.success());
    let body = summary(&run.tmpdir.join("summary-final.md"));
    assert!(body.contains("- **Duration**: N/A\n"));
    assert!(body.contains("- **Cost**: N/A\n"));
    assert!(body.contains("- **Issue**: N/A\n"));
    assert!(body.contains("- **Plan review**: N/A\n"));
    assert!(body.contains("- **Code review**: N/A\n"));
    assert!(body.contains("- **Lines (PR diff)**: N/A\n"));
    assert!(body.contains("- **OOS filed**: 0\n"));
    assert!(!body.contains("- **Difficulty**:"));
    assert!(!body.contains("- **PR**:"));
}

#[test]
fn write_uses_the_fixed_test_version_without_a_manifest() {
    let run = Run::create();
    run.write(
        "parent-issue.md",
        &format!("ISSUE_NUMBER=0\nRUN_ID={RUN_ID}\n"),
    );
    run.write("session-env.sh", "REPO_UNAVAILABLE=true\n");
    let output = run
        .command("write")
        .env("LARCH_TEST_PLUGIN_VERSION", "test-version")
        .arg("--skip-tracking-upsert")
        .output()
        .expect("final-report write");
    assert!(output.status.success());
    assert!(
        summary(&run.tmpdir.join("summary-final.md"))
            .contains("- **Larch version**: test-version\n")
    );
}

#[test]
fn write_rejects_a_traversing_run_identifier() {
    let run = Run::create();
    run.write("parent-issue.md", "ISSUE_NUMBER=0\nRUN_ID=../escape\n");
    let output = run.command("write").output().expect("final-report write");
    let values = kv(&String::from_utf8_lossy(&output.stdout));
    assert_eq!(values.get("STATUS").map(String::as_str), Some("failed"));
    assert_eq!(
        values.get("ERROR").map(String::as_str),
        Some("invalid RUN_ID (path-traversal characters rejected)")
    );
    assert!(!output.status.success());
}

#[test]
fn write_rejects_an_unknown_cost_override_key() {
    let run = shipped_run();
    let output = run
        .command("write")
        .arg("--cost-overrides-json")
        .arg(r#"{"LARCH_NOT_A_RATE": "1"}"#)
        .output()
        .expect("final-report write");
    let values = kv(&String::from_utf8_lossy(&output.stdout));
    assert_eq!(values.get("STATUS").map(String::as_str), Some("failed"));
    assert_eq!(
        values.get("ERROR").map(String::as_str),
        Some("final report render failed: unknown cost override key: LARCH_NOT_A_RATE")
    );
}

#[test]
fn step18b_emits_the_contract_and_refreshes_the_summary() {
    let run = shipped_run();
    fs::write(run.tmpdir.join(".step16-16a-done"), "").expect("marker");
    let output = run
        .command("step18b")
        .arg("--step17-emitted")
        .arg("false")
        .output()
        .expect("final-report step18b");
    let values = kv(&String::from_utf8_lossy(&output.stdout));
    assert_eq!(values.get("EMIT_BODY").map(String::as_str), Some("true"));
    assert_eq!(values.get("WFR_RC").map(String::as_str), Some("0"));
    assert_eq!(
        values.get("STEP17_EMITTED_PRESENT").map(String::as_str),
        Some("false")
    );
    assert_eq!(
        values.get("SNAPSHOT_OK").map(String::as_str),
        Some("absent")
    );
    assert_eq!(values.get("ERROR").map(String::as_str), Some(""));
    assert!(output.status.success());
    assert!(run.tmpdir.join("summary-final.md").is_file());
}

#[test]
fn step18b_suppresses_the_body_when_step17_already_emitted_an_identical_one() {
    let run = shipped_run();
    fs::write(run.tmpdir.join(".step16-16a-done"), "").expect("marker");
    let first = run
        .command("step18b")
        .arg("--step17-emitted")
        .arg("false")
        .output()
        .expect("first step18b");
    assert!(first.status.success());
    let second = run
        .command("step18b")
        .arg("--step17-emitted")
        .arg("true")
        .output()
        .expect("second step18b");
    let values = kv(&String::from_utf8_lossy(&second.stdout));
    assert_eq!(values.get("EMIT_BODY").map(String::as_str), Some("false"));
    assert_eq!(
        values.get("STEP17_EMITTED_PRESENT").map(String::as_str),
        Some("true")
    );
    assert_eq!(values.get("SNAPSHOT_OK").map(String::as_str), Some("true"));
}
