//! Golden-driven black-box parity for `/implement` Steps 16 and 17 (#8791).
//!
//! Every case runs the frozen pre-cutover Python owner and the Rust command in
//! separate sandboxes. A deterministic verified-bootstrap stub records child
//! argv, supplies Step 16/17 outcomes, and persists failure-log requests, so
//! stdout, stderr, exit status, and every wire file are compared together.

#![cfg(unix)]

#[path = "support/parity.rs"]
#[allow(dead_code)]
mod parity_support;

use std::{env, fs, os::unix::fs::PermissionsExt as _, path::PathBuf, process::Command};

use parity_support::{NormalizationRule, ParityCase, Program, SeedFile, assert_case};

const STUB: &str = include_str!("../../../fixtures/rust-parity/implement_closeout_stub.sh");

fn repository_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .canonicalize()
        .expect("canonical repository root")
}

fn python_executable() -> PathBuf {
    let output = Command::new("python3")
        .args(["-c", "import sys; print(sys.executable)"])
        .output()
        .expect("launch python3 to resolve the interpreter");
    assert!(output.status.success(), "resolve the Python interpreter");
    PathBuf::from(
        String::from_utf8(output.stdout)
            .expect("Python interpreter path is UTF-8")
            .trim(),
    )
}

fn seeds(extra: &[(&str, &str)]) -> Vec<SeedFile> {
    let mut files = vec![
        SeedFile::executable_text("scripts/larch.sh", STUB),
        SeedFile::text("python/cli.py", "# parity root marker\n"),
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

fn parity_case(
    name: &'static str,
    verb: &str,
    tail: &[&str],
    extra_seeds: &[(&str, &str)],
    export_tmpdir: bool,
) -> ParityCase {
    parity_case_with_plugin_root(name, verb, tail, extra_seeds, export_tmpdir, true)
}

fn parity_case_with_plugin_root(
    name: &'static str,
    verb: &str,
    tail: &[&str],
    extra_seeds: &[(&str, &str)],
    export_tmpdir: bool,
    export_plugin_root: bool,
) -> ParityCase {
    let root = repository_root();
    let reference = root.join("fixtures/rust-parity/implement_closeout_reference.py");
    let python_path = root.join("python");
    let binary = PathBuf::from(env!("CARGO_BIN_EXE_larch"));
    let mut python_arguments = vec![reference.to_string_lossy().into_owned(), verb.to_owned()];
    python_arguments.extend(tail.iter().map(|value| (*value).to_owned()));
    let mut rust_arguments = vec!["implement".to_owned(), verb.to_owned()];
    rust_arguments.extend(tail.iter().map(|value| (*value).to_owned()));

    let mut python = Program::new(python_executable())
        .args(python_arguments)
        .env("PYTHONPATH", &python_path.to_string_lossy())
        .env("LARCH_CLAUDE_INPUT_RATE_PER_M", "1.25")
        .env("CLAUDE_CODE_EFFORT_LEVEL", "fixture-effort")
        .env("LARCH_EXEC_ISSUE_ASSESSMENT_MODEL", "fixture-model");
    let mut rust = Program::new(binary)
        .args(rust_arguments)
        .env("LARCH_CLAUDE_INPUT_RATE_PER_M", "1.25")
        .env("CLAUDE_CODE_EFFORT_LEVEL", "fixture-effort")
        .env("LARCH_EXEC_ISSUE_ASSESSMENT_MODEL", "fixture-model");
    if export_plugin_root {
        python = python.env("CLAUDE_PLUGIN_ROOT", "{sandbox}");
        rust = rust.env("CLAUDE_PLUGIN_ROOT", "{sandbox}");
    }
    if export_tmpdir {
        python = python.env("IMPLEMENT_TMPDIR", "{sandbox}/session");
        rust = rust.env("IMPLEMENT_TMPDIR", "{sandbox}/session");
    }
    ParityCase {
        name,
        python,
        rust,
        seed_files: seeds(extra_seeds),
        side_effect_records: Vec::new(),
        normalization: vec![NormalizationRule::SandboxRoot],
    }
}

fn with_environment(mut case: ParityCase, key: &str, value: &str) -> ParityCase {
    case.python = case.python.env(key, value);
    case.rust = case.rust.env(key, value);
    case
}

fn with_seed(mut case: ParityCase, seed: SeedFile) -> ParityCase {
    case.seed_files.push(seed);
    case
}

fn step16_cases() -> Vec<ParityCase> {
    vec![
        parity_case(
            "implement-closeout-step16-help",
            "step-16",
            &["--help"],
            &[],
            false,
        ),
        parity_case(
            "implement-closeout-step16-missing-tmpdir",
            "step-16",
            &[],
            &[],
            false,
        ),
        parity_case(
            "implement-closeout-step16-run-id",
            "step-16",
            &[],
            &[],
            true,
        ),
        parity_case(
            "implement-closeout-step16-ignores-child-exit",
            "step-16",
            &[],
            &[("session/step16-exit", "9\n")],
            true,
        ),
        parity_case(
            "implement-closeout-step16-16a-slack-warning",
            "step-16-16a",
            &[],
            &[("session/slack-status", "failed\n")],
            true,
        ),
        parity_case(
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
            parity_case(
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
            parity_case_with_plugin_root(
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

fn report_cases() -> Vec<ParityCase> {
    vec![
        parity_case(
            "implement-closeout-step17-print-success",
            "step-17",
            &[],
            &[],
            true,
        ),
        parity_case(
            "implement-closeout-step17-restores-stale-summary",
            "step-17",
            &["--no-print-stdout"],
            &[
                ("session/step17-mode", "fail-stale\n"),
                ("session/summary-final.md", "old body\n"),
            ],
            true,
        ),
        parity_case(
            "implement-closeout-step17-backup-refusal",
            "step-17",
            &["--no-print-stdout"],
            &[
                ("session/summary-final.md", "old body\n"),
                ("session/.summary-final.pre-step17.bak/keep", "occupied\n"),
            ],
            true,
        ),
        parity_case(
            "implement-closeout-composite-markers",
            "step-16-17",
            &[],
            &[("session/step17-mode", "success-no-newline\n")],
            true,
        ),
        parity_case(
            "implement-closeout-composite-upsert-failure-refresh",
            "step-16-17",
            &[],
            &[
                ("session/step17-mode", "fail-upsert\n"),
                ("session/summary-final.md", "old body\n"),
            ],
            true,
        ),
        parity_case(
            "implement-closeout-composite-empty-failure",
            "step-16-17",
            &[],
            &[("session/step17-mode", "fail-empty\n")],
            true,
        ),
    ]
}

fn cases() -> Vec<ParityCase> {
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
fn implement_closeout_matches_the_frozen_python_owner() {
    let goldens = repository_root().join("fixtures/rust-parity/goldens");
    for case in cases() {
        assert_case(&case, &goldens.join(format!("{}.golden.json", case.name)))
            .unwrap_or_else(|error| panic!("{error}"));
    }
}
