//! Golden-driven black-box parity for the token command cutover in #8797.
//!
//! Each case runs the frozen Python owner and the Rust binary in separate
//! sandboxes, comparing stdout, stderr, exit status, and filesystem effects.

#![cfg(unix)]

#[path = "support/parity.rs"]
#[allow(dead_code)]
mod parity_support;

use std::{env, path::PathBuf, process::Command};

use parity_support::{NormalizationRule, ParityCase, Program, SeedFile, assert_case};

const LEDGER: &str = concat!(
    "{\"type\":\"vendor\",\"total\":100}\n",
    "{\"type\":\"mark\",\"step\":\"Step 2\"}\n",
    "{\"type\":\"vendor\",\"total\":50}\n",
    "malformed\n",
);

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

fn parity_case(name: &'static str, verb: &str, tail: &[&str]) -> ParityCase {
    let root = repository_root();
    let python_path = root.join("python");
    let mut python_arguments = vec![
        root.join("fixtures/rust-parity/token_cutover_reference.py")
            .to_string_lossy()
            .into_owned(),
        verb.to_owned(),
    ];
    python_arguments.extend(tail.iter().map(|value| (*value).to_owned()));
    let mut rust_arguments = vec!["token".to_owned(), verb.to_owned()];
    rust_arguments.extend(tail.iter().map(|value| (*value).to_owned()));
    ParityCase {
        name,
        python: Program::new(python_executable())
            .args(python_arguments)
            .env("PYTHONPATH", &python_path.to_string_lossy())
            .env("IMPLEMENT_TMPDIR", "{sandbox}/session")
            .env("LARCH_TOKEN_LEDGER", "{sandbox}/session/token.jsonl"),
        rust: Program::new(PathBuf::from(env!("CARGO_BIN_EXE_larch")))
            .args(rust_arguments)
            .env("IMPLEMENT_TMPDIR", "{sandbox}/session")
            .env("LARCH_TOKEN_LEDGER", "{sandbox}/session/token.jsonl"),
        seed_files: vec![SeedFile::text("session/token.jsonl", LEDGER)],
        side_effect_records: Vec::new(),
        normalization: vec![NormalizationRule::SandboxRoot],
    }
}

fn cases() -> Vec<ParityCase> {
    vec![
        parity_case(
            "token-check-budget-under-cap",
            "check-budget",
            &["--cap", "100", "--step", "Step 2"],
        ),
        parity_case(
            "token-check-budget-cap-hit",
            "check-budget",
            &["--cap", "40", "--step", "Step 2"],
        ),
        parity_case("token-check-budget-missing-cap", "check-budget", &[]),
        parity_case(
            "token-check-budget-unknown-flag",
            "check-budget",
            &["--wat"],
        ),
        parity_case(
            "token-compute-pr-line-counts-no-pr",
            "compute-pr-line-counts",
            &[],
        ),
        parity_case(
            "token-compute-pr-line-counts-invalid-repo",
            "compute-pr-line-counts",
            &["--pr-number", "42", "--repo", "invalid"],
        ),
        parity_case("token-compute-pr-lines-no-pr", "compute-pr-lines", &[]),
    ]
}

#[test]
fn token_cutover_matches_the_frozen_python_owner() {
    let goldens = repository_root().join("fixtures/rust-parity/goldens");
    for case in cases() {
        assert_case(&case, &goldens.join(format!("{}.golden.json", case.name)))
            .unwrap_or_else(|error| panic!("{error}"));
    }
}
