//! Golden-driven black-box contracts for `/implement` Steps 16 and 17.
//!
//! Every case runs the Rust command in an isolated sandbox. A deterministic
//! verified-bootstrap stub
//! records child argv, supplies Step 16/17 outcomes, and persists failure-log
//! requests so stdout, stderr, exit status, and every wire file remain pinned.

#![cfg(unix)]

#[path = "support/recorded.rs"]
#[allow(dead_code)]
mod recorded_support;

use std::{env, fs, os::unix::fs::PermissionsExt as _, path::PathBuf, process::Command};

use recorded_support::{NormalizationRule, RecordedCase, Program, SeedFile, assert_recorded_case};

const STUB: &str = include_str!("fixtures/recorded/implement_closeout_stub.sh");

fn repository_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .canonicalize()
        .expect("canonical repository root")
}


fn seeds(extra: &[(&str, &str)]) -> Vec<SeedFile> {
    let mut files = vec![
        SeedFile::executable_text("scripts/larch.sh", STUB),
        SeedFile::text("session/.keep", ""),
        SeedFile::text(
            "session/session-env.sh",
            "LARCH_RUN_ID=session-run\nLARCH_TOKEN_SESSION_ID=token-session\nLARCH_CLAUDE_SOURCE_FILE=/fixture/source.jsonl\nLARCH_TIMING_LEDGER=/fixture/timing.tsv\n",
        ),
    ];
    files.extend(
        extra
            .iter()
            .map(|(path, contents)| SeedFile::text(path, contents)),
    );
    files
}

fn recorded_case(
    name: &'static str,
    verb: &str,
    tail: &[&str],
    extra_seeds: &[(&str, &str)],
    export_tmpdir: bool,
) -> RecordedCase {
    recorded_case_with_plugin_root(name, verb, tail, extra_seeds, export_tmpdir, true)
}

fn recorded_case_with_plugin_root(
    name: &'static str,
    verb: &str,
    tail: &[&str],
    extra_seeds: &[(&str, &str)],
    export_tmpdir: bool,
    export_plugin_root: bool,
) -> RecordedCase {
    let binary = PathBuf::from(env!("CARGO_BIN_EXE_larch"));
    let mut rust_arguments = vec!["implement".to_owned(), verb.to_owned()];
    rust_arguments.extend(tail.iter().map(|value| (*value).to_owned()));

    let mut program = Program::new(binary)
        .args(rust_arguments)
        .env("LARCH_CLAUDE_INPUT_RATE_PER_M", "1.25")
        .env("CLAUDE_CODE_EFFORT_LEVEL", "fixture-effort")
        .env("LARCH_EXEC_ISSUE_ASSESSMENT_MODEL", "fixture-model");
    if export_plugin_root {
        program = program.env("CLAUDE_PLUGIN_ROOT", "{sandbox}");
    }
    if export_tmpdir {
        program = program.env("IMPLEMENT_TMPDIR", "{sandbox}/session");
    }
    RecordedCase {
        name,
        program,
        seed_files: seeds(extra_seeds),
        side_effect_records: Vec::new(),
        normalization: vec![NormalizationRule::SandboxRoot],
    }
}

fn with_environment(mut case: RecordedCase, key: &str, value: &str) -> RecordedCase {
    case.program = case.program.env(key, value);
    case
}

fn with_seed(mut case: RecordedCase, seed: SeedFile) -> RecordedCase {
    case.seed_files.push(seed);
    case
}

fn step16_cases() -> Vec<RecordedCase> {
    vec![
        recorded_case(
            "implement-closeout-step16-help",
            "step-16",
            &["--help"],
            &[],
            false,
        ),
        recorded_case(
            "implement-closeout-step16-missing-tmpdir",
            "step-16",
            &[],
            &[],
            false,
        ),
        recorded_case(
            "implement-closeout-step16-run-id",
            "step-16",
            &[],
            &[],
            true,
        ),
        recorded_case(
            "implement-closeout-step16-ignores-child-exit",
            "step-16",
            &[],
            &[("session/step16-exit", "9\n")],
            true,
        ),
        recorded_case(
            "implement-closeout-step16-16a-slack-warning",
            "step-16-16a",
            &[],
            &[("session/slack-status", "failed\n")],
            true,
        ),
        recorded_case(
            "implement-closeout-step16-ship-run-id-fallback",
            "step-16",
            &[],
            &[
                ("session/session-env.sh", ""),
                ("session/ship-pr-state.sh", "RUN_ID=ship-run\n"),
                ("session/finalize-state.sh", "RUN_ID=finalize-run\n"),
            ],
            true,
        ),
        with_environment(
            recorded_case(
                "implement-closeout-step16-ambient-run-id-fallback",
                "step-16",
                &[],
                &[
                    ("session/session-env.sh", ""),
                    ("session/ship-pr-state.sh", ""),
                    ("session/finalize-state.sh", ""),
                ],
                true,
            ),
            "RUN_ID",
            "ambient-run",
        ),
        with_seed(
            recorded_case_with_plugin_root(
                "implement-closeout-step16-recorded-plugin-root",
                "step-16",
                &[],
                &[],
                true,
                false,
            ),
            SeedFile::expanded_text("session/plugin-root.env", "CLAUDE_PLUGIN_ROOT={sandbox}\n"),
        ),
    ]
}

fn report_cases() -> Vec<RecordedCase> {
    vec![
        recorded_case(
            "implement-closeout-step17-print-success",
            "step-17",
            &[],
            &[],
            true,
        ),
        recorded_case(
            "implement-closeout-step17-restores-stale-summary",
            "step-17",
            &["--no-print-stdout"],
            &[
                ("session/step17-mode", "fail-stale\n"),
                ("session/summary-final.md", "old body\n"),
            ],
            true,
        ),
        recorded_case(
            "implement-closeout-step17-backup-refusal",
            "step-17",
            &["--no-print-stdout"],
            &[
                ("session/summary-final.md", "old body\n"),
                ("session/.summary-final.pre-step17.bak/keep", "occupied\n"),
            ],
            true,
        ),
        recorded_case(
            "implement-closeout-composite-markers",
            "step-16-17",
            &[],
            &[("session/step17-mode", "success-no-newline\n")],
            true,
        ),
        recorded_case(
            "implement-closeout-composite-upsert-failure-refresh",
            "step-16-17",
            &[],
            &[
                ("session/step17-mode", "fail-upsert\n"),
                ("session/summary-final.md", "old body\n"),
            ],
            true,
        ),
        recorded_case(
            "implement-closeout-composite-empty-failure",
            "step-16-17",
            &[],
            &[("session/step17-mode", "fail-empty\n")],
            true,
        ),
    ]
}

fn cases() -> Vec<RecordedCase> {
    let mut cases = step16_cases();
    cases.extend(report_cases());
    cases
}

#[test]
fn closeout_forwards_the_webhook_only_to_the_slack_child() {
    let fixture = tempfile::tempdir().expect("closeout webhook fixture");
    let root = fixture.path();
    let scripts = root.join("scripts");
    let session = root.join("session");
    fs::create_dir_all(&scripts).expect("scripts directory");
    fs::create_dir_all(&session).expect("session directory");
    let entrypoint = scripts.join("larch.sh");
    fs::write(&entrypoint, STUB).expect("write closeout stub");
    let mut permissions = fs::metadata(&entrypoint)
        .expect("inspect closeout stub")
        .permissions();
    permissions.set_mode(0o755);
    fs::set_permissions(&entrypoint, permissions).expect("make closeout stub executable");
    fs::write(
        session.join("session-env.sh"),
        "LARCH_RUN_ID=run\nLARCH_TOKEN_SESSION_ID=token\n",
    )
    .expect("write closeout session");

    let output = Command::new(env!("CARGO_BIN_EXE_larch"))
        .args([
            "implement",
            "step-16-16a",
            "--implement-tmpdir",
            session.to_str().expect("UTF-8 session path"),
        ])
        .current_dir(root)
        .env_clear()
        .env("CLAUDE_PLUGIN_ROOT", root)
        .env("HOME", root.join("home"))
        .env("IMPLEMENT_TMPDIR", &session)
        .env("LARCH_SLACK_WEBHOOK_URL", "fixture-webhook")
        .env("PATH", "/usr/bin:/bin")
        .output()
        .expect("run closeout webhook fixture");
    assert!(
        output.status.success(),
        "closeout webhook fixture failed: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    let events =
        fs::read_to_string(session.join("child-events.log")).expect("read closeout child events");
    assert_eq!(events.matches("SLACK_WEBHOOK_PRESENT=true").count(), 1);
    assert!(!events.contains("fixture-webhook"));
}

#[test]
fn recorded_implement_closeout_contract() {
    let goldens = repository_root().join("crates/larch-cli/tests/fixtures/recorded/goldens");
    for case in cases() {
        assert_recorded_case(&case, &goldens.join(format!("{}.golden.json", case.name)))
            .unwrap_or_else(|error| panic!("{error}"));
    }
}
