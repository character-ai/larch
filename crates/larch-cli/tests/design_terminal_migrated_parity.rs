//! Golden-driven black-box parity for the migrated `/design` terminal verbs (#8580).
//!
//! The frozen Python reference at
//! `fixtures/rust-parity/design_terminal_migrated_reference.py` executes the
//! byte-frozen pre-cutover module; each case runs both it and the Rust owner in
//! isolated sandboxes and asserts stdout/stderr/exit/wire-file parity plus a
//! recorded golden, mirroring `design_step1_migrated_parity.rs`.
//!
//! Scope note: the symlink-primary `read-result-env` warning and the deep
//! tier-A / gh-reconcile branches of `failure-report` are covered by
//! injected-seam unit tests in
//! `crates/larch-cli/src/design_terminal_commands.rs`, because the parity
//! sandbox rejects tree symlinks and forbids live GitHub mutation. The goldens
//! here cover the deterministic read/stage/skip/fallback/emit branches.

#[path = "support/parity.rs"]
#[allow(dead_code)]
mod parity_support;

use std::{
    env,
    path::{Path, PathBuf},
};

use parity_support::{NormalizationRule, ParityCase, Program, SeedFile, assert_case};

fn repository_root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .canonicalize()
        .expect("canonical repository root")
}

fn fixture_directory() -> PathBuf {
    repository_root().join("fixtures/rust-parity")
}

fn python_executable() -> PathBuf {
    env::split_paths(&env::var_os("PATH").expect("PATH"))
        .map(|directory| directory.join("python3"))
        .find(|candidate| candidate.is_file())
        .and_then(|candidate| candidate.canonicalize().ok())
        .expect("python3 on PATH")
}

fn parity_case(
    name: &'static str,
    reference_tail: &[String],
    rust_tail: &[String],
    seeds: Vec<SeedFile>,
    env_rows: &[(&str, String)],
) -> ParityCase {
    let root = repository_root();
    let reference = fixture_directory().join("design_terminal_migrated_reference.py");
    let python_path = root.join("python");
    let plugin_root = root.to_string_lossy().into_owned();
    let path = env::var("PATH").expect("PATH");
    let binary = env!("CARGO_BIN_EXE_larch");

    let mut python = Program::new(python_executable())
        .args(
            std::iter::once(reference.to_string_lossy().into_owned())
                .chain(reference_tail.iter().cloned()),
        )
        .env("PYTHONPATH", &python_path.to_string_lossy())
        .env("CLAUDE_PLUGIN_ROOT", &plugin_root)
        // The frozen reference routes every larch child (stall-recovery,
        // run-log, progress) at the built binary.
        .env("LARCH_BINARY", binary)
        .env("LARCH_QUIET_DISABLE", "1")
        .env("LARCH_TEST_TIMING_NOW", "1787000000")
        .env("COLUMNS", "1000")
        .env("PATH", &path);
    let mut rust = Program::new(binary)
        .args(rust_tail.iter().cloned())
        .env("CLAUDE_PLUGIN_ROOT", &plugin_root)
        .env("LARCH_BINARY", binary)
        .env("LARCH_QUIET_DISABLE", "1")
        .env("LARCH_TEST_TIMING_NOW", "1787000000")
        .env("COLUMNS", "1000")
        .env("PATH", &path);
    for (key, value) in env_rows {
        python = python.env(key, value);
        rust = rust.env(key, value);
    }
    ParityCase {
        name,
        python,
        rust,
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
) -> ParityCase {
    let mut seeds = design_dir_seed();
    seeds.extend(extra_seeds);
    let reference_tail = {
        let mut v = args(&["read-result-env"]);
        v.extend(tail.iter().map(|value| (*value).to_owned()));
        v
    };
    let rust_tail = {
        let mut v = args(&["design", "read-result-env"]);
        v.extend(tail.iter().map(|value| (*value).to_owned()));
        v
    };
    parity_case(name, &reference_tail, &rust_tail, seeds, &[])
}

fn read_result_env_cases() -> Vec<ParityCase> {
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
            vec![SeedFile::text(&format!("{DESIGN_RELATIVE}/in.env"), "FOO=bar\n")],
        ),
    ]
}

// -------------------------------------------------------- stage-terminal-state

fn stage_tail(extra: &[&str]) -> (Vec<String>, Vec<String>) {
    let mut tail = args(&[
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
    tail.extend(extra.iter().map(|value| (*value).to_owned()));
    let mut rust_tail = args(&["design"]);
    rust_tail.extend(tail.iter().cloned());
    (tail, rust_tail)
}

fn stage_cases() -> Vec<ParityCase> {
    let mut cases = Vec::new();
    {
        // Fresh stage: STAGED=true and the terminal-state wire file.
        let (tail, rust_tail) = stage_tail(&[]);
        cases.push(parity_case(
            "design-terminal-stage-fresh",
            &tail,
            &rust_tail,
            design_dir_seed(),
            &[],
        ));
    }
    {
        // Existing state with a different SITE: preserve-on-mismatch.
        let (tail, rust_tail) = stage_tail(&[]);
        let mut seeds = design_dir_seed();
        seeds.push(SeedFile::text(
            &format!("{DESIGN_RELATIVE}/design-failure-terminal-state.env"),
            "DESIGN_FAILURE_VERSION=1\nDESIGN_FAILURE_KIND=terminal\nFAILURE_OUTCOME=failed-clarify\nSITE=other-site\nTRIGGER=failed\n",
        ));
        cases.push(parity_case(
            "design-terminal-stage-preserve-on-mismatch",
            &tail,
            &rust_tail,
            seeds,
            &[],
        ));
    }
    {
        // Unknown option: exit 2 with the sh-prefixed diagnostic.
        let (tail, rust_tail) = stage_tail(&["--nope"]);
        cases.push(parity_case(
            "design-terminal-stage-unknown-option",
            &tail,
            &rust_tail,
            design_dir_seed(),
            &[],
        ));
    }
    cases
}

// -------------------------------------------------------------- failure-report

fn failure_tail(outcome: &str) -> (Vec<String>, Vec<String>) {
    let tail = args(&[
        "failure-report",
        "--design-tmpdir",
        "{sandbox}/design",
        "--outcome",
        outcome,
    ]);
    let mut rust_tail = args(&["design"]);
    rust_tail.extend(tail.iter().cloned());
    (tail, rust_tail)
}

fn failure_cases() -> Vec<ParityCase> {
    let mut cases = Vec::new();
    {
        // A present terminal-report sentinel short-circuits to skip.
        let (tail, rust_tail) = failure_tail("approved");
        let mut seeds = design_dir_seed();
        seeds.push(SeedFile::text(
            &format!("{DESIGN_RELATIVE}/design-failure-terminal-report.env"),
            "STALL_RECOVERY_REPORT_STATUS=filed\n",
        ));
        cases.push(parity_case(
            "design-terminal-failure-report-skip-sentinel",
            &tail,
            &rust_tail,
            seeds,
            &[],
        ));
    }
    {
        // A terminal failed-* outcome with no terminal state falls back to chat.
        let (tail, rust_tail) = failure_tail("failed-clarify");
        cases.push(parity_case(
            "design-terminal-failure-report-missing-terminal-state",
            &tail,
            &rust_tail,
            design_dir_seed(),
            &[],
        ));
    }
    {
        // A non-allowlisted outcome skips with the outcome-not-success reason.
        let (tail, rust_tail) = failure_tail("in-progress");
        cases.push(parity_case(
            "design-terminal-failure-report-outcome-not-allowlisted",
            &tail,
            &rust_tail,
            design_dir_seed(),
            &[],
        ));
    }
    cases
}

// ---------------------------------------------------------- step-final-summary

fn step_final_summary_cases() -> Vec<ParityCase> {
    let tail = args(&[
        "step-final-summary",
        "--plugin-root",
        "{sandbox}",
        "--outcome",
        "failed-clarify",
    ]);
    let mut rust_tail = args(&["design"]);
    rust_tail.extend(tail.iter().cloned());
    let mut seeds = design_dir_seed();
    seeds.push(SeedFile::text(
        &format!("{DESIGN_RELATIVE}/final-summary.md"),
        "## Final summary\n\nDone.\n",
    ));
    vec![parity_case(
        "design-terminal-step-final-summary-failed-clarify-emit",
        &tail,
        &rust_tail,
        seeds,
        &design_tmpdir_env(),
    )]
}

fn all_cases() -> Vec<ParityCase> {
    let mut cases = Vec::new();
    cases.extend(read_result_env_cases());
    cases.extend(stage_cases());
    cases.extend(failure_cases());
    cases.extend(step_final_summary_cases());
    cases
}

#[test]
fn design_terminal_migrated_parity() {
    let goldens = fixture_directory().join("goldens");
    for case in all_cases() {
        let golden = goldens.join(format!("{}.golden.json", case.name));
        if let Err(error) = assert_case(&case, &golden) {
            panic!("{error}");
        }
    }
}
