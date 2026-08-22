//! Golden-driven black-box parity for the migrated review-loop identity verbs (#8792).

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

fn case(name: &'static str, verb: &str, tail: &[&str]) -> ParityCase {
    let root = repository_root();
    let path = env::var("PATH").expect("PATH");
    let arguments = std::iter::once(verb.to_owned())
        .chain(tail.iter().map(|value| (*value).to_owned()))
        .collect::<Vec<_>>();
    ParityCase {
        name,
        python: Program::new(python_executable())
            .args(
                std::iter::once(
                    fixture_directory()
                        .join("review_loop_identity_reference.py")
                        .to_string_lossy()
                        .into_owned(),
                )
                .chain(arguments.clone()),
            )
            .env("PYTHONPATH", &root.join("python").to_string_lossy())
            .env("PATH", &path),
        rust: Program::new(env!("CARGO_BIN_EXE_larch"))
            .args(std::iter::once("review-and-fix".to_owned()).chain(arguments))
            .env("PATH", &path),
        seed_files: vec![SeedFile::text("implement/.keep", "")],
        side_effect_records: Vec::new(),
        normalization: vec![NormalizationRule::SandboxRoot],
    }
}

fn all_cases() -> Vec<ParityCase> {
    vec![
        case("review-loop-write-help", "write-loop-identity", &["--help"]),
        case("review-loop-await-help", "await-loop-identity", &["--help"]),
        case(
            "review-loop-teardown-help",
            "teardown-loop-identity",
            &["--help"],
        ),
        case("review-loop-write-missing", "write-loop-identity", &[]),
        case("review-loop-await-missing", "await-loop-identity", &[]),
        case(
            "review-loop-teardown-missing",
            "teardown-loop-identity",
            &[],
        ),
        case(
            "review-loop-write-invalid-pid",
            "write-loop-identity",
            &["--implement-tmpdir", "{sandbox}/implement", "--pid", "nope"],
        ),
        case(
            "review-loop-await-invalid-pid",
            "await-loop-identity",
            &["--implement-tmpdir", "{sandbox}/implement", "--pid", "nope"],
        ),
        case(
            "review-loop-await-invalid-timeout",
            "await-loop-identity",
            &[
                "--implement-tmpdir",
                "{sandbox}/implement",
                "--pid",
                "123",
                "--timeout-s",
                "not-a-number",
            ],
        ),
        case(
            "review-loop-await-missing-sidecar",
            "await-loop-identity",
            &[
                "--implement-tmpdir",
                "{sandbox}/implement",
                "--pid",
                "123",
                "--reattach",
            ],
        ),
        case(
            "review-loop-teardown-missing-sidecar",
            "teardown-loop-identity",
            &["--implement-tmpdir", "{sandbox}/implement", "--pid", "123"],
        ),
        case(
            "review-loop-write-unknown-option",
            "write-loop-identity",
            &[
                "--implement-tmpdir",
                "{sandbox}/implement",
                "--pid",
                "123",
                "--unknown",
            ],
        ),
    ]
}

#[test]
fn review_loop_identity_migrated_parity() {
    let goldens = fixture_directory().join("goldens");
    for case in all_cases() {
        let golden = goldens.join(format!("{}.golden.json", case.name));
        if let Err(error) = assert_case(&case, &golden) {
            panic!("{error}");
        }
    }
}
