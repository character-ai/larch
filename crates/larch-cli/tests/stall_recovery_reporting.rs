//! End-to-end security and contract coverage for Rust-owned stall reporting.

use std::{
    fs,
    path::{Path, PathBuf},
    process::{Command, Output},
};

use larch_adapters::stall_recovery::STALL_RECOVERY_EVIDENCE_NAMES;
use tempfile::TempDir;

const SECRET: &str = "ghp_abcdefghijklmnopqrstuvwxyz0123456789AB";

struct Fixture {
    _temporary: TempDir,
    tmpdir: PathBuf,
    project: PathBuf,
}

impl Fixture {
    fn new() -> Self {
        let temporary = tempfile::tempdir().expect("temporary root");
        let tmpdir = temporary.path().join("session");
        let project = temporary.path().join("project");
        fs::create_dir_all(project.join("skills/implement")).expect("project fixture");
        fs::write(project.join("skills/implement/SKILL.md"), "fixture\n").expect("project marker");
        fs::create_dir_all(&tmpdir).expect("session fixture");
        Self {
            _temporary: temporary,
            tmpdir: fs::canonicalize(tmpdir).expect("canonical session"),
            project: fs::canonicalize(project).expect("canonical project"),
        }
    }

    fn path(&self, name: &str) -> PathBuf {
        self.tmpdir.join(name)
    }

    fn write(&self, name: &str, text: &str) {
        fs::write(self.path(name), text).expect("write fixture input");
    }

    fn run(&self, verb: &str, arguments: &[String]) -> Output {
        Command::new(env!("CARGO_BIN_EXE_larch"))
            .args(["stall-recovery", verb])
            .args(arguments)
            .env("CLAUDE_PROJECT_DIR", &self.project)
            .env("LARCH_STALL_RECOVERY_DRY_RUN", "1")
            .env("LARCH_STALL_RECOVERY_TEST_LEGACY_SURFACES", "true")
            .output()
            .expect("run stall-recovery command")
    }

    fn run_live(&self, verb: &str, arguments: &[String]) -> Output {
        Command::new(env!("CARGO_BIN_EXE_larch"))
            .args(["stall-recovery", verb])
            .args(arguments)
            .env("CLAUDE_PROJECT_DIR", &self.project)
            .env("CLAUDE_PLUGIN_ROOT", &self.project)
            .env_remove("LARCH_STALL_RECOVERY_DRY_RUN")
            .env_remove("DRY_RUN_DECISION")
            .env_remove("LARCH_STALL_RECOVERY_TEST_LEGACY_SURFACES")
            .env_remove("LARCH_STALL_RECOVERY_ENABLE_TEST_FILING")
            .env_remove("LARCH_ISSUE_MUTATION_DENY")
            .output()
            .expect("run live stall-recovery command")
    }

    fn base_report_inputs(&self) {
        self.write(
            "stall-recovery-classification.env",
            "FAILURE_CLASS=test-failure\nSTALL_STEP=8a\nPHASE=ship-pr\nBAIL_REASON=review-required\nRESUME_HINT=none\nEXIT_CODE=1\nDISPATCHER=lint-fix-loop\nMATCHED_CLASSIFIER_PATTERN=test-output\n",
        );
        self.write(
            "stall-recovery-attempts.env",
            "version=1\nattempt_count=1\nattempt.1.class=test-failure\nattempt.1.resume_hint=none\nattempt.1.outcome=failed\nattempt.1.utc=unknown\n",
        );
        self.write(
            "stall-recovery-root-cause.md",
            "verdict=larch-defect\nconfidence=high\nsummary=Safe report title\n\nValidated evidence.\n",
        );
    }

    fn compose_arguments(&self, surface: &str) -> Vec<String> {
        vec![
            "--implement-tmpdir".to_owned(),
            self.tmpdir.to_string_lossy().into_owned(),
            "--surface".to_owned(),
            surface.to_owned(),
        ]
    }
}

fn text(path: &Path) -> String {
    fs::read_to_string(path).unwrap_or_else(|error| panic!("read {}: {error}", path.display()))
}

#[test]
fn tier_a_redacts_a_planted_secret_before_every_public_payload_write() {
    let fixture = Fixture::new();
    fixture.base_report_inputs();
    fixture.write(
        "stall-recovery-classification.env",
        &format!(
            "FAILURE_CLASS=test-failure\nSTALL_STEP=8a\nPHASE=ship-pr\nBAIL_REASON=review-required\nBAIL_REASON_RAW={SECRET}\nPR_URL={SECRET}\nFAILURE_DETAIL_LOG={}\n",
            fixture.path("detail.log").display(),
        ),
    );
    fixture.write(
        "stall-recovery-attempts.env",
        &format!(
            "version=1\nattempt_count=1\nattempt.1.class=test-failure\nattempt.1.resume_hint=none\nattempt.1.outcome=failed\nattempt.1.utc={SECRET}\n",
        ),
    );
    fixture.write(
        "stall-recovery-escalation-ledger.tsv",
        &format!("utc=unknown\tsite=step5\ttrigger=main-agent-required\tnote={SECRET}\n"),
    );
    fixture.write(
        "stall-recovery-escalation-fallback.tsv",
        &format!("utc=unknown\tsite=step8\ttrigger=escalate\tnote={SECRET}\n"),
    );
    fixture.write(
        "stall-recovery-escalation-record-failure.env",
        &format!("NOTE={SECRET}\n"),
    );
    fixture.write(
        "stall-recovery-root-cause.md",
        &format!(
            "verdict=larch-defect\nconfidence=high\nsummary=Report {SECRET}\n\nRoot-cause evidence {SECRET}.\n"
        ),
    );
    fixture.write("stall-recovery-title.txt", &format!("Title {SECRET}\n"));
    fixture.write("detail.log", &format!("detail {SECRET}\n"));
    fixture.write("run-log-pointer.txt", &format!("pointer {SECRET}\n"));
    fixture.write(
        "session-env.sh",
        &format!("LARCH_RUN_ID={SECRET}\nBRANCH_NAME=topic\n"),
    );
    fixture.write("ship-pr-state.sh", &format!("PR_URL={SECRET}\n"));
    fixture.write("finalize-state.sh", &format!("PR_URL={SECRET}\n"));
    fixture.write(
        "execution-issues.md",
        &format!("## Tool Failure: record-escalation\n\n{SECRET}\n"),
    );
    for name in STALL_RECOVERY_EVIDENCE_NAMES {
        if !fixture.path(name).exists() {
            fixture.write(name, &format!("evidence {name} {SECRET}\n"));
        }
    }

    let populated = fixture.run(
        "populate-sensitive-corpus",
        &[
            "--implement-tmpdir".to_owned(),
            fixture.tmpdir.to_string_lossy().into_owned(),
        ],
    );
    assert!(
        populated.status.success(),
        "{}",
        String::from_utf8_lossy(&populated.stderr)
    );
    assert!(text(&fixture.path("stall-recovery-sensitive-corpus.env")).contains(SECRET));

    let output = fixture.run("compose-report", &fixture.compose_arguments("issue-input"));
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(
        String::from_utf8_lossy(&output.stdout).contains("STALL_RECOVERY_REPORT_STATUS=dry-run")
    );

    for name in [
        "stall-recovery-issue-input.md",
        "stall-recovery-tier-a-attempts.md",
        "stall-recovery-tier-a-escalation.md",
        "stall-recovery-tier-a-root-cause.md",
    ] {
        let payload = text(&fixture.path(name));
        assert!(!payload.contains(SECRET), "secret leaked to {name}");
    }
    assert!(text(&fixture.path("stall-recovery-issue-input.md")).contains("<REDACTED-TOKEN>"));
}

#[test]
fn tier_b_rejects_a_sensitive_bounded_root_cause_without_writing_payloads() {
    let fixture = Fixture::new();
    fixture.base_report_inputs();
    fixture.write(
        "stall-recovery-sensitive-corpus.env",
        "client-secret-value\n",
    );
    fixture.write(
        "stall-recovery-bounded-root-cause.md",
        "verdict=larch-defect\nconfidence=high\nsummary=Safe summary\n\nclient-secret-value\n",
    );

    let output = fixture.run("chat-print", &fixture.compose_arguments("chat-print"));
    assert_eq!(output.status.code(), Some(1));
    assert!(
        String::from_utf8_lossy(&output.stderr)
            .contains("bounded root-cause contains sensitive token")
    );
    for name in [
        "stall-recovery-chat-print.md",
        "stall-recovery-bounded-attempts.md",
        "stall-recovery-bounded-escalation-summary.md",
        "stall-recovery-bounded-root-cause-public.md",
    ] {
        assert!(
            !fixture.path(name).exists(),
            "unexpected public payload {name}"
        );
    }
}

#[test]
fn chat_print_keeps_the_tier_b_public_report_contract() {
    let fixture = Fixture::new();
    fixture.base_report_inputs();
    fixture.write("stall-recovery-sensitive-corpus.env", "");
    fixture.write(
        "stall-recovery-bounded-root-cause.md",
        "verdict=larch-defect\nconfidence=high\nsummary=Safe report title\n\nBounded evidence.\n",
    );

    let output = fixture.run("chat-print", &fixture.compose_arguments("chat-print"));
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    let stdout = String::from_utf8_lossy(&output.stdout);
    let signature = stdout
        .lines()
        .find_map(|line| line.strip_prefix("REPORT_DEDUP_SIGNATURE="))
        .expect("report signature");
    let report = text(&fixture.path("stall-recovery-chat-print.md"));
    assert!(
        report.starts_with(
            "### [BUG] /implement terminal: Safe report title (test-failure at 8a)\n\n"
        )
    );
    assert!(report.contains(&format!("<!-- larch-stall:signature={signature} -->")));
    assert!(report.contains(&format!(
        "| Larch version | `{}` |",
        env!("CARGO_PKG_VERSION")
    )));
    assert!(report.contains("| Run ID | `unknown` |"));
    for name in [
        "stall-recovery-bounded-attempts.md",
        "stall-recovery-bounded-escalation-summary.md",
        "stall-recovery-bounded-root-cause-public.md",
    ] {
        assert!(
            fixture.path(name).is_file(),
            "missing public payload {name}"
        );
    }
}

#[test]
fn filing_commands_refuse_mutation_before_their_helpers_run() {
    let fixture = Fixture::new();
    fixture.base_report_inputs();
    fixture.write("stall-recovery-sensitive-corpus.env", "");
    fixture.write(
        "stall-recovery-bounded-root-cause.md",
        "verdict=larch-defect\nconfidence=high\nsummary=Safe summary\n\nBounded evidence.\n",
    );

    let chat = fixture.run_live("chat-print", &fixture.compose_arguments("chat-print"));
    assert!(
        chat.status.success(),
        "{}",
        String::from_utf8_lossy(&chat.stderr)
    );
    let chat_stdout = String::from_utf8_lossy(&chat.stdout);
    assert!(
        chat_stdout.contains("STALL_RECOVERY_REPORT_STATUS=fallback-print-required"),
        "{chat_stdout}"
    );
    assert!(
        chat_stdout.contains(
            "STALL_RECOVERY_REPORT_FALLBACK_REASON=unauthorized-mutation:reporter-unauthorized"
        ),
        "{chat_stdout}"
    );

    fixture.write("stall-recovery-issue-input.md", "### [BUG] Tier A\n");
    let dedup = fixture.run_live(
        "dedup-tier-a-report",
        &[
            "--implement-tmpdir".to_owned(),
            fixture.tmpdir.to_string_lossy().into_owned(),
        ],
    );
    assert!(
        dedup.status.success(),
        "{}",
        String::from_utf8_lossy(&dedup.stderr)
    );
    let dedup_stdout = String::from_utf8_lossy(&dedup.stdout);
    assert!(dedup_stdout.contains("STALL_RECOVERY_REPORT_STATUS=mutation-refused"));
    assert!(dedup_stdout.contains(
        "STALL_RECOVERY_REPORT_FALLBACK_REASON=unauthorized-mutation:unauthorized-mutation"
    ));
}
