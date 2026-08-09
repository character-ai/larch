//! Integration coverage for the Rust-owned `timing` verbs.
//!
//! Every case pins report time with `--test-now` or a seeded ledger rather than
//! sleeping, so the suite stays deterministic under parallel execution.

use std::{fs, path::PathBuf, process::Output};

use assert_cmd::Command as AssertCommand;
use serde_json::Value;

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
        self.tmpdir.join("timing-ledger.tsv")
    }

    fn seed(&self, rows: &[&str]) {
        let mut text = rows.join("\n");
        text.push('\n');
        fs::write(self.ledger(), text).expect("ledger should seed");
    }

    fn rows(&self) -> Vec<Vec<String>> {
        fs::read_to_string(self.ledger())
            .unwrap_or_default()
            .lines()
            .map(|line| line.split('\t').map(str::to_owned).collect())
            .collect()
    }

    fn run(&self, arguments: &[&str]) -> Output {
        self.run_with_skill("implement", arguments)
    }

    fn run_with_skill(&self, skill: &str, arguments: &[&str]) -> Output {
        let mut command = AssertCommand::cargo_bin("larch").expect("larch binary should build");
        command
            .current_dir(&self.tmpdir)
            .env("TMPDIR", &self.tmpdir)
            .env("IMPLEMENT_TMPDIR", &self.tmpdir)
            .env("LARCH_TIMING_SKILL", skill)
            .env_remove("DESIGN_TMPDIR")
            .env_remove("REVIEW_TMPDIR")
            .env_remove("SESSION_ENV_PATH")
            .env_remove("LARCH_TIMING_LEDGER")
            .arg("timing")
            .args(arguments);
        command.output().expect("timing command should launch")
    }
}

fn stdout(output: &Output) -> String {
    String::from_utf8_lossy(&output.stdout).into_owned()
}

fn stderr(output: &Output) -> String {
    String::from_utf8_lossy(&output.stderr).into_owned()
}

const MARK_STEP_1: &str = "v1\tmark\t100\timplement\tStep 1\t-\t-\t-\t-\t-\t-\t-\t-";
const MARK_DESIGN_3: &str = "v1\tmark\t110\tdesign\tdesign Step 3\t-\t-\t-\t-\t-\t-\t-\t-";
const ROUND_DESIGN_3: &str = "v1\tround\t115\tdesign\tdesign Step 3\t1\t111\t118\t7\t2\t1\t3\t1";
const MARK_STEP_2: &str = "v1\tmark\t160\timplement\tStep 2\t-\t-\t-\t-\t-\t-\t-\t-";
const VENDOR_SHORT: &str =
    "v1\tvendor\t150\timplement\t-\tcodex\tcodex-review\t100\t130\t30\tout.txt\t0\tcomplete";
const VENDOR_LONG: &str =
    "v1\tvendor\t155\timplement\t-\tcodex\tcodex-review\t100\t150\t50\tout.txt\t0\tcomplete";

fn seeded(fixture: &Fixture) {
    fixture.seed(&[
        MARK_STEP_1,
        MARK_DESIGN_3,
        ROUND_DESIGN_3,
        VENDOR_SHORT,
        VENDOR_LONG,
        MARK_STEP_2,
    ]);
}

#[test]
fn mark_appends_one_canonical_row_and_task_kinds_lists_the_allow_list() {
    let fixture = Fixture::new();
    let output = fixture.run(&["mark", "Step 3 — checks"]);
    assert!(output.status.success(), "{}", stderr(&output));
    let rows = fixture.rows();
    assert_eq!(rows.len(), 1);
    assert_eq!(rows[0][0..2], ["v1".to_owned(), "mark".to_owned()]);
    assert_eq!(
        rows[0][3..5],
        ["implement".to_owned(), "Step 3 — checks".to_owned()]
    );
    assert_eq!(rows[0].len(), 13);

    let kinds = fixture.run(&["task-kinds"]);
    let kinds_text = stdout(&kinds);
    let listed: Vec<&str> = kinds_text.lines().collect();
    let mut sorted = listed.clone();
    sorted.sort_unstable();
    assert_eq!(listed, sorted, "task kinds must print sorted");
    assert!(listed.contains(&"codex-review"), "{listed:?}");
}

#[test]
fn mark_if_latest_differs_suppresses_only_a_repeated_label_for_the_same_skill() {
    let fixture = Fixture::new();
    assert!(
        fixture
            .run(&["mark", "--if-latest-differs", "Step 5"])
            .status
            .success()
    );
    assert!(
        fixture
            .run(&["mark", "--if-latest-differs", "Step 5"])
            .status
            .success()
    );
    assert!(
        fixture
            .run_with_skill("design", &["mark", "--if-latest-differs", "Step 5"])
            .status
            .success()
    );
    let steps: Vec<String> = fixture.rows().iter().map(|row| row[4].clone()).collect();
    assert_eq!(steps, ["Step 5", "Step 5"]);
    let skills: Vec<String> = fixture.rows().iter().map(|row| row[3].clone()).collect();
    assert_eq!(skills, ["implement", "design"]);
}

#[test]
fn mark_without_a_resolvable_ledger_writes_nothing_and_succeeds() {
    let fixture = Fixture::new();
    let mut command = AssertCommand::cargo_bin("larch").expect("larch binary should build");
    command
        .current_dir(&fixture.tmpdir)
        .env_remove("IMPLEMENT_TMPDIR")
        .env_remove("DESIGN_TMPDIR")
        .env_remove("REVIEW_TMPDIR")
        .env_remove("SESSION_ENV_PATH")
        .env_remove("LARCH_TIMING_LEDGER")
        .args(["timing", "mark", "Step 1"]);
    let output = command.output().expect("timing mark should launch");
    assert!(output.status.success(), "{}", stderr(&output));
    assert!(!fixture.ledger().exists());
}

#[test]
fn record_vendor_task_normalizes_status_names_and_clamps_a_reversed_window() {
    let fixture = Fixture::new();
    let ok = fixture.run(&[
        "record-vendor-task",
        "--vendor",
        "codex",
        "--task-kind",
        "codex-review",
        "--start-s",
        "10.9",
        "--end-s",
        "25.4",
        "--output",
        "/nested/dir/codex.log",
        "--exit-code",
        "3",
        "--status",
        "ERROR",
    ]);
    assert!(ok.status.success(), "{}", stderr(&ok));
    let reversed = fixture.run(&[
        "record-vendor-task",
        "--vendor",
        "cursor",
        "--task-kind",
        "cursor-review",
        "--start-s",
        "50",
        "--end-s",
        "10",
        "--output",
        "cursor.log",
    ]);
    assert!(reversed.status.success());
    assert!(stderr(&reversed).contains("end_s precedes start_s"));
    let rows = fixture.rows();
    assert_eq!(
        rows[0][5..7],
        ["codex".to_owned(), "codex-review".to_owned()]
    );
    assert_eq!(
        rows[0][7..10],
        ["10".to_owned(), "25".to_owned(), "15".to_owned()]
    );
    assert_eq!(rows[0][10], "codex.log");
    assert_eq!(rows[0][11..13], ["3".to_owned(), "signal".to_owned()]);
    assert_eq!(rows[1][9], "0");
    assert_eq!(rows[1][12], "unknown");
}

#[test]
fn record_vendor_task_refuses_an_unknown_vendor_and_warns_on_an_unlisted_kind() {
    let fixture = Fixture::new();
    let refused = fixture.run(&[
        "record-vendor-task",
        "--vendor",
        "gemini",
        "--task-kind",
        "codex-review",
        "--start-s",
        "0",
        "--end-s",
        "1",
        "--output",
        "o",
    ]);
    assert_eq!(refused.status.code(), Some(1));
    assert!(stderr(&refused).contains("vendor must be codex, cursor, or claude"));
    let warned = fixture.run(&[
        "record-vendor-task",
        "--vendor",
        "codex",
        "--task-kind",
        "codex-unregistered",
        "--start-s",
        "0",
        "--end-s",
        "1",
        "--output",
        "o",
    ]);
    assert!(warned.status.success());
    assert!(stderr(&warned).contains("unknown task-kind: codex-unregistered"));
    assert_eq!(fixture.rows().len(), 1, "the warned row still records");
}

#[test]
fn record_round_counts_prior_attempts_of_the_same_round() {
    let fixture = Fixture::new();
    for start in ["100", "300"] {
        let output = fixture.run(&[
            "record-round",
            "--skill",
            "implement",
            "--step",
            "Step 5 — code review",
            "--round",
            "1",
            "--start-s",
            start,
            "--end-s",
            "400",
            "--accepted",
            "1",
            "--rejected",
            "0",
        ]);
        assert!(output.status.success(), "{}", stderr(&output));
    }
    let second = fixture.run(&[
        "record-round",
        "--skill",
        "implement",
        "--step",
        "Step 5 — code review",
        "--round",
        "2",
        "--start-s",
        "500",
        "--end-s",
        "600",
        "--accepted",
        "0",
        "--rejected",
        "0",
    ]);
    assert!(second.status.success());
    let rows = fixture.rows();
    let rounds: Vec<String> = rows.iter().map(|row| row[5].clone()).collect();
    let attempts: Vec<String> = rows.iter().map(|row| row[12].clone()).collect();
    assert_eq!(rounds, ["1", "1", "2"]);
    assert_eq!(attempts, ["1", "2", "1"]);
    assert!(rows.iter().all(|row| row[11] == "-"));
    let refused = fixture.run(&[
        "record-round",
        "--skill",
        "review",
        "--step",
        "s",
        "--round",
        "1",
        "--start-s",
        "0",
        "--end-s",
        "1",
        "--accepted",
        "0",
        "--rejected",
        "0",
    ]);
    assert_eq!(refused.status.code(), Some(1));
    assert!(stderr(&refused).contains("--skill must be implement or design"));
}

#[test]
fn record_round_if_round_exists_preserves_idempotent_compatibility_calls() {
    let fixture = Fixture::new();
    let arguments = [
        "record-round",
        "--skill",
        "design",
        "--step",
        "design Step 3 — plan review",
        "--round",
        "1",
        "--start-s",
        "100",
        "--end-s",
        "120",
        "--accepted",
        "0",
        "--rejected",
        "0",
        "--if-round-exists",
    ];
    assert!(
        fixture
            .run_with_skill("design", &arguments)
            .status
            .success()
    );
    assert!(
        fixture
            .run_with_skill("design", &arguments)
            .status
            .success()
    );
    assert_eq!(fixture.rows().len(), 1);
    assert_eq!(fixture.rows()[0][12], "1");
}

#[test]
fn record_round_if_round_exists_keeps_a_legacy_short_round_row_unchanged() {
    let fixture = Fixture::new();
    fixture.seed(&["v1\tround\t100\tdesign\tdesign Step 3 — plan review\t1\t10\t20"]);
    let output = fixture.run_with_skill(
        "design",
        &[
            "record-round",
            "--skill",
            "design",
            "--step",
            "design Step 3 — plan review",
            "--round",
            "1",
            "--start-s",
            "10",
            "--end-s",
            "20",
            "--accepted",
            "0",
            "--rejected",
            "0",
            "--if-round-exists",
        ],
    );

    assert!(output.status.success(), "{}", stderr(&output));
    assert_eq!(fixture.rows().len(), 1);
    assert_eq!(fixture.rows()[0].len(), 8);
}

#[test]
fn concurrent_marks_from_separate_processes_keep_every_row_intact() {
    let fixture = Fixture::new();
    let mut children = Vec::new();
    for index in 0..8 {
        let mut command = std::process::Command::new(assert_cmd::cargo::cargo_bin("larch"));
        command
            .current_dir(&fixture.tmpdir)
            .env("TMPDIR", &fixture.tmpdir)
            .env("IMPLEMENT_TMPDIR", &fixture.tmpdir)
            .env_remove("DESIGN_TMPDIR")
            .env_remove("LARCH_TIMING_LEDGER")
            .args(["timing", "mark", &format!("Step {index}")]);
        children.push(command.spawn().expect("concurrent mark should launch"));
    }
    for mut child in children {
        assert!(
            child
                .wait()
                .expect("concurrent mark should finish")
                .success()
        );
    }
    let rows = fixture.rows();
    assert_eq!(rows.len(), 8);
    assert!(
        rows.iter()
            .all(|row| row.len() == 13 && row[0] == "v1" && row[1] == "mark")
    );
    let mut steps: Vec<String> = rows.iter().map(|row| row[4].clone()).collect();
    steps.sort();
    let mut expected: Vec<String> = (0..8).map(|index| format!("Step {index}")).collect();
    expected.sort();
    assert_eq!(steps, expected);
}

#[test]
fn full_report_json_publishes_every_machine_field() {
    let fixture = Fixture::new();
    seeded(&fixture);
    let output = fixture.run(&["report", "--full", "--format", "json", "--test-now", "200"]);
    assert!(output.status.success(), "{}", stderr(&output));
    let parsed: Value = serde_json::from_str(stdout(&output).trim()).expect("report json parses");
    assert_eq!(parsed["total_seconds"], 60);
    assert_eq!(parsed["total_hms"], "00:01:00");
    let steps = parsed["per_step"].as_array().expect("per_step array");
    assert_eq!(steps.len(), 3);
    assert_eq!(steps[1]["skill"], "design");
    assert_eq!(steps[1]["rounds"][0]["oos"], 3);
    assert_eq!(steps[1]["rounds"][0]["accepted"], 2);
    let averages = parsed["vendor_task_averages"]
        .as_array()
        .expect("averages array");
    assert_eq!(averages[0]["vendor"], "codex");
    assert_eq!(averages[0]["samples"], 2);
    assert_eq!(averages[0]["average_hms"], "00:00:40");
    assert_eq!(averages[0]["min_seconds"], 30);
    assert_eq!(averages[0]["max_seconds"], 50);
    // Python's `json.dumps(..., sort_keys=True)` spacing is part of the contract.
    assert!(
        stdout(&output).starts_with("{\"per_step\": [{\"duration_hms\""),
        "{}",
        stdout(&output)
    );
}

#[test]
fn markdown_report_keeps_the_readable_prose_contract() {
    let fixture = Fixture::new();
    seeded(&fixture);
    let output = fixture.run(&["report", "--full", "--test-now", "200"]);
    let rendered = stdout(&output);
    assert!(
        rendered.starts_with("## Per-Step Durations\n\n| Skill | Step | Duration |\n"),
        "{rendered}"
    );
    assert!(
        rendered.contains("| implement | Step 1 | 00:01:00 |"),
        "{rendered}"
    );
    assert!(
        rendered.contains("| **Total** | | 00:01:00 |"),
        "{rendered}"
    );
    assert!(
        rendered.contains("| codex | codex-review | 2 | 0.7 min | 0.5 min-0.8 min |"),
        "{rendered}"
    );
    let flagged = fixture.run(&[
        "report",
        "--full",
        "--outlier-threshold",
        "5",
        "--test-now",
        "200",
    ]);
    assert!(
        stdout(&flagged).contains("| implement | Step 1 | 00:01:00 [OUTLIER] |"),
        "{}",
        stdout(&flagged)
    );
}

#[test]
fn summary_and_terse_reports_count_vendor_tasks_by_end_time() {
    let fixture = Fixture::new();
    seeded(&fixture);
    let summary = fixture.run(&["report", "--summary", "--test-now", "200"]);
    assert_eq!(
        stdout(&summary).trim(),
        "Total: elapsed=00:01:40 vendor-tasks=2 (codex=2, cursor=0, claude=0)"
    );
    let terse = fixture.run(&["report", "--terse", "--test-now", "200"]);
    assert_eq!(
        stdout(&terse).trim(),
        "Step 2: elapsed=00:00:40 vendor-tasks=0 (codex=0, cursor=0, claude=0)"
    );
    let design = fixture.run_with_skill("design", &["report", "--terse", "--test-now", "200"]);
    assert!(
        stdout(&design).starts_with("design Step 3: elapsed=00:01:30"),
        "{}",
        stdout(&design)
    );
}

#[test]
fn report_flag_and_ledger_failures_stay_non_fatal() {
    let fixture = Fixture::new();
    seeded(&fixture);
    for arguments in [
        vec!["report"],
        vec!["report", "--nope"],
        vec!["report", "--full", "--format", "yaml"],
    ] {
        let output = fixture.run(&arguments);
        assert!(
            output.status.success(),
            "{arguments:?} should not fail the workflow"
        );
        assert!(
            stderr(&output).starts_with("Timing report unavailable:"),
            "{}",
            stderr(&output)
        );
    }
    let empty = Fixture::new();
    let output = empty.run(&["report", "--full", "--test-now", "200"]);
    assert_eq!(
        stdout(&output).trim(),
        "Timing report unavailable: no step marks in ledger"
    );
}

#[test]
fn report_writes_the_output_file_and_upserts_the_appended_section() {
    let fixture = Fixture::new();
    seeded(&fixture);
    let target = fixture.tmpdir.join("report.json");
    let written = fixture.run(&[
        "report",
        "--full",
        "--format",
        "json",
        "--test-now",
        "200",
        "--output",
        target.to_str().expect("utf-8 path"),
    ]);
    assert!(written.status.success(), "{}", stderr(&written));
    assert!(stdout(&written).is_empty(), "--output must not also print");
    assert!(
        fs::read_to_string(&target)
            .expect("report file")
            .contains("\"total_seconds\": 60")
    );

    let body = fixture.tmpdir.join("body.md");
    fs::write(&body, "intro\n").expect("body should seed");
    for _attempt in 0..2 {
        let appended = fixture.run(&[
            "report",
            "--test-now",
            "200",
            "--append-timing-section",
            body.to_str().expect("utf-8 path"),
        ]);
        assert!(appended.status.success(), "{}", stderr(&appended));
        assert!(
            stdout(&appended).is_empty(),
            "--append-timing-section must not also print"
        );
    }
    let rendered = fs::read_to_string(&body).expect("body should read");
    assert!(rendered.starts_with("intro\n"), "{rendered}");
    assert_eq!(
        rendered.matches("<!-- timing-report-begin -->").count(),
        1,
        "{rendered}"
    );
    assert!(rendered.contains("## Timing Report"), "{rendered}");
}

#[test]
fn dump_prints_the_resolved_path_then_the_raw_rows() {
    let fixture = Fixture::new();
    fixture.seed(&[MARK_STEP_1]);
    let output = fixture.run(&["dump"]);
    assert!(output.status.success(), "{}", stderr(&output));
    let text = stdout(&output);
    let mut lines = text.lines();
    assert_eq!(
        lines.next(),
        Some(fixture.ledger().to_string_lossy().as_ref())
    );
    assert_eq!(lines.next(), Some(MARK_STEP_1));

    let refused = fixture.run(&["dump", "--ledger", "/etc/timing-ledger.tsv"]);
    assert_eq!(refused.status.code(), Some(1));
    assert!(stderr(&refused).contains("not under an allowed root"));
}

#[test]
fn harness_mark_publishes_the_sentinel_and_forwards_the_child_exit_code() {
    let fixture = Fixture::new();
    let ok = fixture.run(&["harness-mark", "--label", "unit", "--", "/bin/echo", "hi"]);
    assert!(ok.status.success());
    assert!(stdout(&ok).contains("hi\n"));
    assert!(
        stdout(&ok).contains("LARCH_HARNESS_TIMING\tunit\t"),
        "{}",
        stdout(&ok)
    );

    let failed = fixture.run(&["harness-mark", "unit-2", "--", "/bin/sh", "-c", "exit 7"]);
    assert_eq!(failed.status.code(), Some(7));
    assert!(stdout(&failed).contains("LARCH_HARNESS_TIMING\tunit-2\t"));

    let missing = fixture.run(&["harness-mark", "unit-3", "/larch/no/such/binary"]);
    assert_eq!(missing.status.code(), Some(127));

    let usage = fixture.run(&["harness-mark"]);
    assert_eq!(usage.status.code(), Some(2));
    assert!(stderr(&usage).contains("requires --label <label> -- <command>"));
}

#[test]
fn telemetry_mark_writes_the_implement_timing_row_and_ignores_a_bad_tmpdir() {
    let fixture = Fixture::new();
    fs::write(
        fixture.tmpdir.join("session-env.sh"),
        format!("LARCH_TIMING_LEDGER=\"{}\"\n", fixture.ledger().display()),
    )
    .expect("session env should seed");
    let output = fixture.run_with_skill(
        "design",
        &[
            "telemetry-mark",
            "--implement-tmpdir",
            fixture.tmpdir.to_str().expect("utf-8 path"),
            "--label",
            "Step 5 — code review",
        ],
    );
    assert!(output.status.success(), "{}", stderr(&output));
    let rows = fixture.rows();
    assert_eq!(rows.len(), 1);
    // The verb forces the implement skill even when the caller declares design.
    assert_eq!(rows[0][3], "implement");
    assert_eq!(rows[0][4], "Step 5 — code review");

    for arguments in [
        vec!["telemetry-mark"],
        vec![
            "telemetry-mark",
            "--implement-tmpdir",
            "relative/path",
            "--label",
            "x",
        ],
        vec![
            "telemetry-mark",
            "--implement-tmpdir",
            "/larch/missing",
            "--label",
            "x",
        ],
    ] {
        let skipped = fixture.run(&arguments);
        assert!(skipped.status.success(), "{arguments:?}");
    }
    assert_eq!(fixture.rows().len(), 1, "no skipped call may append a row");
}

#[test]
fn malformed_rows_are_skipped_with_a_warning_instead_of_failing_the_report() {
    let fixture = Fixture::new();
    fixture.seed(&[MARK_STEP_1, "garbage", MARK_STEP_2]);
    let output = fixture.run(&["report", "--full", "--test-now", "200"]);
    assert!(output.status.success(), "{}", stderr(&output));
    assert!(
        stderr(&output).contains("skipping malformed row with 1 columns"),
        "{}",
        stderr(&output)
    );
    assert!(
        stdout(&output).contains("| **Total** | | 00:01:00 |"),
        "{}",
        stdout(&output)
    );
}
