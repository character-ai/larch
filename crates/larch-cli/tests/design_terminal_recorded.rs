//! Golden-driven black-box contracts for the `/design` terminal verbs.
//!
//! Each case runs the Rust owner in an isolated sandbox and checks stdout,
//! stderr, exit status, and wire files against a reviewed snapshot.
//!
//! Scope note: the symlink-primary `read-result-env` warning and the deep
//! tier-A / gh-reconcile branches of `failure-report` are covered by
//! injected-seam unit tests in
//! `crates/larch-cli/src/design_terminal_commands.rs`, because the recorded contract
//! sandbox rejects tree symlinks and forbids live GitHub mutation. The goldens
//! here cover the deterministic read/stage/skip/fallback/emit branches.

#[path = "support/recorded.rs"]
#[allow(dead_code)]
mod recorded_support;

use std::{
    env, fs,
    path::{Path, PathBuf},
    process::{Command, Stdio},
};

use recorded_support::{NormalizationRule, RecordedCase, Program, SeedFile, assert_recorded_case};
use tempfile::TempDir;

fn repository_root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .canonicalize()
        .expect("canonical repository root")
}
fn fixture_directory() -> PathBuf {
    repository_root().join("crates/larch-cli/tests/fixtures/recorded")
}


fn recorded_case(
    name: &'static str,
    arguments: &[String],
    seeds: Vec<SeedFile>,
    env_rows: &[(&str, String)],
) -> RecordedCase {
    let root = repository_root();
    let plugin_root = root.to_string_lossy().into_owned();
    let path = env::var("PATH").expect("PATH");
    let binary = env!("CARGO_BIN_EXE_larch");

    let mut program = Program::new(binary)
        .args(arguments.iter().cloned())
        .env("CLAUDE_PLUGIN_ROOT", &plugin_root)
        .env("LARCH_BINARY", binary)
        .env("LARCH_QUIET_DISABLE", "1")
        .env("LARCH_TEST_TIMING_NOW", "1787000000")
        .env("COLUMNS", "1000")
        .env("PATH", &path);
    for (key, value) in env_rows {
        program = program.env(key, value);
    }
    RecordedCase {
        name,
        program,
        seed_files: seeds,
        side_effect_records: Vec::new(),
        normalization: vec![
            NormalizationRule::SandboxRoot,
            NormalizationRule::Rfc3339Utc,
            NormalizationRule::ProcessIdentity,
        ],
    }
}

fn args(values: &[&str]) -> Vec<String> {
    values.iter().map(|value| (*value).to_owned()).collect()
}

const DESIGN_RELATIVE: &str = "design";

fn design_dir_seed() -> Vec<SeedFile> {
    vec![SeedFile::text(&format!("{DESIGN_RELATIVE}/.keep"), "")]
}

fn design_tmpdir_env() -> Vec<(&'static str, String)> {
    vec![("DESIGN_TMPDIR", "{sandbox}/design".to_owned())]
}

// ------------------------------------------------------------- read-result-env

fn read_result_env_case(
    name: &'static str,
    tail: &[&str],
    extra_seeds: Vec<SeedFile>,
) -> RecordedCase {
    let mut seeds = design_dir_seed();
    seeds.extend(extra_seeds);
    let mut arguments = args(&["design", "read-result-env"]);
    arguments.extend(tail.iter().map(|value| (*value).to_owned()));
    recorded_case(name, &arguments, seeds, &[])
}

fn read_result_env_cases() -> Vec<RecordedCase> {
    vec![
        // Regular input: allowlisted rows are single-quoted into the output.
        read_result_env_case(
            "design-terminal-read-result-env-regular",
            &[
                "--input",
                "{sandbox}/design/in.env",
                "--allow",
                "FOO",
                "--allow",
                "BAZ",
                "--output",
                "{sandbox}/design/out.env",
            ],
            vec![SeedFile::text(
                &format!("{DESIGN_RELATIVE}/in.env"),
                "FOO=bar\nBAZ=qux quux\nDROP=hidden\n",
            )],
        ),
        // Missing primary with a regular fallback: read from the fallback, no warning.
        read_result_env_case(
            "design-terminal-read-result-env-fallback",
            &[
                "--input",
                "{sandbox}/design/missing.env",
                "--fallback-input",
                "{sandbox}/design/fallback.env",
                "--allow",
                "FOO",
                "--output",
                "{sandbox}/design/out.env",
            ],
            vec![SeedFile::text(
                &format!("{DESIGN_RELATIVE}/fallback.env"),
                "FOO=from-fallback\n",
            )],
        ),
        // bgjob-preferred source: the legacy status name resolves to its
        // regular bgjob sidecar.
        read_result_env_case(
            "design-terminal-read-result-env-bgjob",
            &[
                "--input",
                "{sandbox}/design/.design-step5c-status.env",
                "--allow",
                "PUBLISH_OK",
                "--output",
                "{sandbox}/design/out.env",
            ],
            vec![SeedFile::text(
                &format!("{DESIGN_RELATIVE}/bgjob/design-step5c.result.env"),
                "PUBLISH_OK=true\n",
            )],
        ),
        // Invalid `--allow` token: usage error, exit 1.
        read_result_env_case(
            "design-terminal-read-result-env-bad-allow",
            &[
                "--input",
                "{sandbox}/design/in.env",
                "--allow",
                "1BAD",
                "--output",
                "{sandbox}/design/out.env",
            ],
            vec![SeedFile::text(
                &format!("{DESIGN_RELATIVE}/in.env"),
                "FOO=bar\n",
            )],
        ),
    ]
}

// -------------------------------------------------------- stage-terminal-state

fn stage_arguments(extra: &[&str]) -> Vec<String> {
    let mut arguments = args(&["design",
        "stage-terminal-state",
        "--design-tmpdir",
        "{sandbox}/design",
        "--outcome",
        "failed-clarify",
        "--step",
        "clarify",
        "--phase",
        "clarify-loop",
        "--site",
        "clarify-loop",
        "--trigger",
        "failed",
        "--bail-reason",
        "clarify-hard-halt",
        "--exit-code",
        "1",
        "--source-script",
        "clarify-loop",
    ]);
    arguments.extend(extra.iter().map(|value| (*value).to_owned()));
    arguments
}

fn stage_cases() -> Vec<RecordedCase> {
    let mut cases = Vec::new();
    {
        // Fresh stage: STAGED=true and the terminal-state wire file.
        let arguments = stage_arguments(&[]);
        cases.push(recorded_case(
            "design-terminal-stage-fresh",
            &arguments,
            design_dir_seed(),
            &[],
        ));
    }
    {
        // Existing state with a different SITE: preserve-on-mismatch.
        let arguments = stage_arguments(&[]);
        let mut seeds = design_dir_seed();
        seeds.push(SeedFile::text(
            &format!("{DESIGN_RELATIVE}/design-failure-terminal-state.env"),
            "DESIGN_FAILURE_VERSION=1\nDESIGN_FAILURE_KIND=terminal\nFAILURE_OUTCOME=failed-clarify\nSITE=other-site\nTRIGGER=failed\n",
        ));
        cases.push(recorded_case(
            "design-terminal-stage-preserve-on-mismatch",
            &arguments,
            seeds,
            &[],
        ));
    }
    {
        // Unknown option: exit 2 with the sh-prefixed diagnostic.
        let arguments = stage_arguments(&["--nope"]);
        cases.push(recorded_case(
            "design-terminal-stage-unknown-option",
            &arguments,
            design_dir_seed(),
            &[],
        ));
    }
    cases
}

// -------------------------------------------------------------- failure-report

fn failure_arguments(outcome: &str) -> Vec<String> {
    args(&[
        "design",
        "failure-report",
        "--design-tmpdir",
        "{sandbox}/design",
        "--outcome",
        outcome,
    ])
}

fn failure_cases() -> Vec<RecordedCase> {
    let mut cases = Vec::new();
    {
        // A present terminal-report sentinel short-circuits to skip.
        let arguments = failure_arguments("approved");
        let mut seeds = design_dir_seed();
        seeds.push(SeedFile::text(
            &format!("{DESIGN_RELATIVE}/design-failure-terminal-report.env"),
            "STALL_RECOVERY_REPORT_STATUS=filed\n",
        ));
        cases.push(recorded_case(
            "design-terminal-failure-report-skip-sentinel",
            &arguments,
            seeds,
            &[],
        ));
    }
    {
        // A terminal failed-* outcome with no terminal state falls back to chat.
        let arguments = failure_arguments("failed-clarify");
        cases.push(recorded_case(
            "design-terminal-failure-report-missing-terminal-state",
            &arguments,
            design_dir_seed(),
            &[],
        ));
    }
    {
        // A non-allowlisted outcome skips with the outcome-not-success reason.
        let arguments = failure_arguments("in-progress");
        cases.push(recorded_case(
            "design-terminal-failure-report-outcome-not-allowlisted",
            &arguments,
            design_dir_seed(),
            &[],
        ));
    }
    cases
}

// ---------------------------------------------------------- step-final-summary

fn step_final_summary_cases() -> Vec<RecordedCase> {
    let arguments = args(&[
        "design",
        "step-final-summary",
        "--plugin-root",
        "{sandbox}",
        "--outcome",
        "failed-clarify",
    ]);
    let mut seeds = design_dir_seed();
    seeds.push(SeedFile::text(
        &format!("{DESIGN_RELATIVE}/final-summary.md"),
        "## Final summary\n\nDone.\n",
    ));
    vec![recorded_case(
        "design-terminal-step-final-summary-failed-clarify-emit",
        &arguments,
        seeds,
        &design_tmpdir_env(),
    )]
}

fn all_cases() -> Vec<RecordedCase> {
    let mut cases = Vec::new();
    cases.extend(read_result_env_cases());
    cases.extend(stage_cases());
    cases.extend(failure_cases());
    cases.extend(step_final_summary_cases());
    cases
}

#[test]
fn recorded_design_terminal_contract() {
    let goldens = fixture_directory().join("goldens");
    for case in all_cases() {
        let golden = goldens.join(format!("{}.golden.json", case.name));
        if let Err(error) = assert_recorded_case(&case, &golden) {
            panic!("{error}");
        }
    }
}

fn git(repo: &Path, arguments: &[&str]) {
    let status = Command::new("git")
        .args(arguments)
        .current_dir(repo)
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .status()
        .expect("git should run");
    assert!(status.success(), "git {arguments:?} failed");
}

#[test]
fn terminal_log_publish_uses_real_dispatcher_and_reads_publish_ok() {
    let temp = TempDir::new().expect("tempdir");
    let consumer = temp.path().join("consumer");
    let design = temp.path().join("design");
    fs::create_dir(&consumer).expect("consumer repo");
    fs::create_dir(&design).expect("design tmpdir");
    fs::create_dir(design.join("final-summary.md")).expect("non-file summary blocks remote upsert");
    git(&consumer, &["init", "-b", "main"]);
    git(
        &consumer,
        &[
            "remote",
            "add",
            "origin",
            "https://github.com/acme/client.git",
        ],
    );
    let root = repository_root();
    let run_id = "ABCDEF01-2345-6789-ABCD-EF0123456789";
    let started = Command::new(env!("CARGO_BIN_EXE_larch"))
        .args([
            "run-log",
            "lifecycle-start",
            "--repo-root",
            consumer.to_str().expect("consumer repo"),
            "--skill",
            "design",
            "--run-id",
            run_id,
        ])
        .current_dir(&consumer)
        .env("HOME", temp.path().join("home"))
        .env("XDG_CACHE_HOME", temp.path().join("cache"))
        .env_remove("XDG_STATE_HOME")
        .env_remove("LARCH_LOGS_URI")
        .env_remove("LARCH_STORAGE_BASE_URI")
        .output()
        .expect("lifecycle should start");
    assert!(
        started.status.success(),
        "{}",
        String::from_utf8_lossy(&started.stderr)
    );
    let output = Command::new(env!("CARGO_BIN_EXE_larch"))
        .args([
            "design",
            "step-final-summary",
            "--plugin-root",
            root.to_str().expect("plugin root"),
            "--outcome",
            "cancelled-operator",
        ])
        .current_dir(&consumer)
        .env("CLAUDE_PLUGIN_ROOT", &root)
        .env("LARCH_BINARY", env!("CARGO_BIN_EXE_larch"))
        .env("LARCH_QUIET_DISABLE", "1")
        .env("CLAUDE_PROJECT_DIR", &consumer)
        .env("REPO_ROOT", &consumer)
        .env("DESIGN_TMPDIR", &design)
        .env("SESSION_ID", run_id)
        .env("ISSUE_NUMBER", "42")
        .env("HOME", temp.path().join("home"))
        .env("XDG_CACHE_HOME", temp.path().join("cache"))
        .env_remove("XDG_STATE_HOME")
        .env_remove("LARCH_LOGS_URI")
        .env_remove("LARCH_STORAGE_BASE_URI")
        .output()
        .expect("step-final-summary should run");
    assert_eq!(output.status.code(), Some(1));
    let publish_stdout = fs::read_to_string(design.join("design-log-publish.terminal.stdout.log"))
        .expect("terminal publish stdout");
    let publish_stderr = fs::read_to_string(design.join("design-log-publish.terminal.stderr.log"))
        .expect("terminal publish stderr");
    assert!(
        publish_stdout.contains("PUBLISH_OK=true\n"),
        "stdout:\n{publish_stdout}\nstderr:\n{publish_stderr}\nouter stderr:\n{}",
        String::from_utf8_lossy(&output.stderr)
    );
    let issues = fs::read_to_string(design.join("execution-issues.md")).expect("issues");
    assert!(
        issues.contains("tracking-issue upsert-summary failed"),
        "{issues}"
    );
    assert!(!issues.contains("design log publish failed"), "{issues}");
}
