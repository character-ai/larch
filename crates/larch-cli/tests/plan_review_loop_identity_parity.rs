//! Golden-driven black-box parity for the plan-review loop-identity verbs (#8835).

#[path = "support/parity.rs"]
#[allow(dead_code)]
mod parity_support;

use std::{
    env,
    path::{Path, PathBuf},
};

use parity_support::{NormalizationRule, ParityCase, Program, SeedFile, assert_rust_golden_case};

const MISMATCHED_IDENTITY: &str = concat!(
    "{\n",
    "  \"command_signature\": \"/usr/bin/python3 /repo/python/cli.py plan-review run\",\n",
    "  \"expected_signature\": \"plan-review run\",\n",
    "  \"pgid\": 321,\n",
    "  \"pid\": 321,\n",
    "  \"start_time\": \"Fri Jul 3 17:01:02 2026\"\n",
    "}\n",
);

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
                        .join("plan_review_loop_identity_reference.py")
                        .to_string_lossy()
                        .into_owned(),
                )
                .chain(arguments.clone()),
            )
            .env("PYTHONPATH", &root.join("python").to_string_lossy())
            .env("PATH", &path),
        rust: Program::new(env!("CARGO_BIN_EXE_larch"))
            .args(std::iter::once("plan-review".to_owned()).chain(arguments))
            .env("PATH", &path),
        seed_files: vec![SeedFile::text("design/.keep", "")],
        side_effect_records: Vec::new(),
        normalization: vec![NormalizationRule::SandboxRoot],
    }
}

fn identity_mismatch_case(name: &'static str, verb: &str, tail: &[&str]) -> ParityCase {
    let mut case = case(name, verb, tail);
    case.seed_files.push(SeedFile::text(
        "design/.step3-loop-identity.json",
        MISMATCHED_IDENTITY,
    ));
    case
}

fn all_cases() -> Vec<ParityCase> {
    vec![
        case("plan-loop-write-help", "write-loop-identity", &["--help"]),
        case("plan-loop-await-help", "await-loop-identity", &["--help"]),
        case(
            "plan-loop-teardown-help",
            "teardown-loop-identity",
            &["--help"],
        ),
        case("plan-loop-write-missing", "write-loop-identity", &[]),
        case("plan-loop-await-missing", "await-loop-identity", &[]),
        case("plan-loop-teardown-missing", "teardown-loop-identity", &[]),
        case(
            "plan-loop-write-tmpdir-refusal",
            "write-loop-identity",
            &["--design-tmpdir", "relative", "--pid", "123"],
        ),
        case(
            "plan-loop-await-tmpdir-refusal",
            "await-loop-identity",
            &["--design-tmpdir", "relative", "--pid", "123"],
        ),
        case(
            "plan-loop-teardown-tmpdir-refusal",
            "teardown-loop-identity",
            &["--design-tmpdir", "relative", "--pid", "123"],
        ),
        case(
            "plan-loop-write-invalid-pid",
            "write-loop-identity",
            &["--design-tmpdir", "{sandbox}/design", "--pid", "nope"],
        ),
        case(
            "plan-loop-await-invalid-pid",
            "await-loop-identity",
            &["--design-tmpdir", "{sandbox}/design", "--pid", "nope"],
        ),
        case(
            "plan-loop-await-invalid-timeout",
            "await-loop-identity",
            &[
                "--design-tmpdir",
                "{sandbox}/design",
                "--pid",
                "123",
                "--timeout-s",
                "not-a-number",
            ],
        ),
        case(
            "plan-loop-await-missing-sidecar",
            "await-loop-identity",
            &[
                "--design-tmpdir",
                "{sandbox}/design",
                "--pid",
                "123",
                "--reattach",
            ],
        ),
        identity_mismatch_case(
            "plan-loop-await-identity-mismatch",
            "await-loop-identity",
            &[
                "--design-tmpdir",
                "{sandbox}/design",
                "--pid",
                "123",
                "--reattach",
            ],
        ),
        case(
            "plan-loop-teardown-missing-sidecar",
            "teardown-loop-identity",
            &["--design-tmpdir", "{sandbox}/design", "--pid", "123"],
        ),
        identity_mismatch_case(
            "plan-loop-teardown-identity-mismatch",
            "teardown-loop-identity",
            &["--design-tmpdir", "{sandbox}/design", "--pid", "123"],
        ),
        case(
            "plan-loop-write-unknown-option",
            "write-loop-identity",
            &[
                "--design-tmpdir",
                "{sandbox}/design",
                "--pid",
                "123",
                "--unknown",
            ],
        ),
    ]
}

#[test]
fn plan_review_loop_identity_migrated_parity() {
    let goldens = fixture_directory().join("goldens");
    for case in all_cases() {
        let golden = goldens.join(format!("{}.golden.json", case.name));
        if let Err(error) = assert_rust_golden_case(&case, &golden) {
            panic!("{error}");
        }
    }
}
