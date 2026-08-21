//! Golden-driven black-box parity for the migrated settlement and Step 5b verbs
//! (#8585). The frozen Python reference runs from
//! `fixtures/rust-parity/design_settle_migrated_reference.py`; each case
//! compares streams, exit code, and captured wire files against the Rust owner.

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

fn args(values: &[&str]) -> Vec<String> {
    values.iter().map(|value| (*value).to_owned()).collect()
}

fn parity_case(
    name: &'static str,
    reference_tail: &[String],
    rust_tail: &[String],
    seeds: Vec<SeedFile>,
    env_rows: &[(&str, String)],
) -> ParityCase {
    let root = repository_root();
    let reference = fixture_directory().join("design_settle_migrated_reference.py");
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

const DESIGN: &str = "design";
const OOS: &str = "### OOS_1: one\n- **Severity**: major\n- **Concern**: one.\nVote tally: YES=1 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=true\n";

fn design_seed() -> Vec<SeedFile> {
    vec![SeedFile::text(&format!("{DESIGN}/.keep"), "")]
}

fn design_env() -> Vec<(&'static str, String)> {
    vec![
        ("DESIGN_TMPDIR", "{sandbox}/design".to_owned()),
        ("REPO_ROOT", "{sandbox}/consumer".to_owned()),
    ]
}

fn migrated_case(
    name: &'static str,
    domain: &str,
    tail: &[&str],
    seeds: Vec<SeedFile>,
    env_rows: &[(&str, String)],
) -> ParityCase {
    let reference_tail = args(tail);
    let mut rust_tail = vec![domain.to_owned()];
    rust_tail.extend(reference_tail.iter().cloned());
    parity_case(name, &reference_tail, &rust_tail, seeds, env_rows)
}

fn prepare_missing_assessment_case() -> ParityCase {
    migrated_case(
        "design-step5b-prepare-missing-gatec-assessments",
        "design",
        &["step5b-prepare"],
        design_seed(),
        &[("DESIGN_TMPDIR", "{sandbox}/design".to_owned())],
    )
}

fn prepare_session_repo_root_case() -> ParityCase {
    let mut seeds = design_seed();
    seeds.extend([
        SeedFile::text("source-env.sh", "REPO_ROOT=consumer\n"),
        SeedFile::text(
            "consumer/ARCHITECTURAL_INVARIANTS.md",
            "## I-Core-1: Keep one owner\n",
        ),
    ]);
    migrated_case(
        "design-step5b-prepare-session-repo-root",
        "design",
        &[
            "step5b-prepare",
            "--session-env-path",
            "{sandbox}/source-env.sh",
        ],
        seeds,
        &[("DESIGN_TMPDIR", "{sandbox}/design".to_owned())],
    )
}

fn prepare_skip_case() -> ParityCase {
    migrated_case(
        "design-step5b-prepare-skip-no-items",
        "design",
        &["step5b-prepare"],
        design_seed(),
        &design_env(),
    )
}

fn prepare_ready_case() -> ParityCase {
    let mut seeds = design_seed();
    seeds.push(SeedFile::text("design/oos-accepted-design.md", OOS));
    migrated_case(
        "design-step5b-prepare-ready",
        "design",
        &["step5b-prepare"],
        seeds,
        &design_env(),
    )
}

fn annotate_empty_stdout_case() -> ParityCase {
    migrated_case(
        "design-step5b-annotate-empty-stdout-retry",
        "design",
        &["step5b-annotate"],
        design_seed(),
        &design_env(),
    )
}

fn annotate_success_case() -> ParityCase {
    let mut seeds = design_seed();
    for (path, contents) in [
        ("design/oos-accepted-design.md", OOS),
        ("design/oos-combined.md", OOS),
        ("design/oos-design-filing-order.txt", "1\n"),
        (
            "design/oos-filing-prepare.env",
            "FILE_DESIGN_OOS_STATUS=ready\nNEXT_ACTION=file-issues\n",
        ),
        (
            "design/oos-issue.stdout.txt",
            "ISSUE_1_URL=https://github.com/acme/repo/issues/101\nISSUES_FAILED=0\n",
        ),
    ] {
        seeds.push(SeedFile::text(path, contents));
    }
    migrated_case(
        "design-step5b-annotate-success",
        "design",
        &["step5b-annotate"],
        seeds,
        &design_env(),
    )
}

#[test]
fn migrated_settle_and_step5b_match_frozen_python() {
    let goldens = fixture_directory().join("goldens");
    let cases = [
        migrated_case(
            "design-step35-settle-gate-b-missing-round",
            "design",
            &["step35-settle", "--site", "gate-b"],
            design_seed(),
            &design_env(),
        ),
        migrated_case(
            "plan-review-step35-settle-gate-b-missing-round",
            "plan-review",
            &["step35-settle", "--site", "gate-b"],
            design_seed(),
            &design_env(),
        ),
        prepare_missing_assessment_case(),
        prepare_session_repo_root_case(),
        prepare_skip_case(),
        prepare_ready_case(),
        annotate_empty_stdout_case(),
        annotate_success_case(),
    ];
    for case in cases {
        assert_case(&case, &goldens.join(format!("{}.golden.json", case.name)))
            .unwrap_or_else(|error| panic!("{error}"));
    }
}
