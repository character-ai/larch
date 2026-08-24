//! Golden-driven black-box parity for the migrated design OOS verbs (#8590).

#[path = "support/parity.rs"]
#[allow(dead_code)]
mod parity_support;

use std::{
    env,
    path::{Path, PathBuf},
};

use parity_support::{NormalizationRule, ParityCase, Program, SeedFile, assert_rust_golden_case};

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

fn case(name: &'static str, verb: &str, tail: &[&str], mut seeds: Vec<SeedFile>) -> ParityCase {
    seeds.push(SeedFile::text("design/.keep", ""));
    let root = repository_root();
    let reference = fixture_directory().join("design_oos_migrated_reference.py");
    let binary = env!("CARGO_BIN_EXE_larch");
    let path = env::var("PATH").expect("PATH");
    let arguments = std::iter::once(verb.to_owned())
        .chain(tail.iter().map(|value| (*value).to_owned()))
        .collect::<Vec<_>>();
    let python = Program::new(python_executable())
        .args(std::iter::once(reference.to_string_lossy().into_owned()).chain(arguments.clone()))
        .env("PYTHONPATH", &root.join("python").to_string_lossy())
        .env("CLAUDE_PLUGIN_ROOT", &root.to_string_lossy())
        .env("LARCH_BINARY", binary)
        .env("LARCH_QUIET_DISABLE", "1")
        .env("OOS_ISSUES_PER_RUN_CAP", "1")
        .env("PATH", &path);
    let rust = Program::new(binary)
        .args(std::iter::once("design".to_owned()).chain(arguments))
        .env("CLAUDE_PLUGIN_ROOT", &root.to_string_lossy())
        .env("LARCH_QUIET_DISABLE", "1")
        .env("OOS_ISSUES_PER_RUN_CAP", "1")
        .env("PATH", &path);
    ParityCase {
        name,
        python,
        rust,
        seed_files: seeds,
        side_effect_records: Vec::new(),
        normalization: vec![NormalizationRule::SandboxRoot],
    }
}

fn all_cases() -> Vec<ParityCase> {
    let tmpdir = ["--design-tmpdir", "{sandbox}/design"];
    vec![
        case(
            "design-oos-prepare-ready",
            "file-oos-prepare",
            &[
                "--design-tmpdir",
                "{sandbox}/design",
                "--issue-number",
                "42",
            ],
            vec![
                SeedFile::text(
                    "design/oos-accepted-design.md",
                    concat!(
                        "### OOS_7: recovered\n- **Focus area**: architecture\n\n",
                        "### OOS_9: follow-up\n- **Description**: preserve this.\n",
                    ),
                ),
                SeedFile::text(
                    ".home/.cache/larch/design-oos-filed/42.accepted-design.md",
                    "### OOS_7: recovered\n- **Focus area**: architecture\n",
                ),
                SeedFile::text(
                    ".home/.cache/larch/design-oos-filed/42.md",
                    "OOS_FILE_MAP\t7\thttps://github.com/acme/repo/issues/7\n",
                ),
            ],
        ),
        case(
            "design-oos-prepare-all-security",
            "file-oos-prepare",
            &tmpdir,
            vec![SeedFile::text(
                "design/oos-accepted-design.md",
                "### OOS_4: private\n- **Focus area**: security-hardening\n",
            )],
        ),
        case(
            "design-oos-prepare-promotes-pool",
            "file-oos-prepare",
            &tmpdir,
            vec![SeedFile::text(
                "design/oos-aggregate-pool.md",
                "### FINDING_1: promoted\n- **Concern**: follow up.\nVote tally: YES=1 NO=0 Result=accepted Fileable=true\n",
            )],
        ),
        case(
            "design-oos-annotate-complete",
            "file-oos-annotate",
            &tmpdir,
            vec![
                SeedFile::text(
                    "design/oos-accepted-design.md",
                    "### OOS_7: follow-up\n- **Focus area**: architecture\n",
                ),
                SeedFile::text(
                    "design/oos-combined.md",
                    "### OOS_1: follow-up\n- **Focus area**: architecture\n",
                ),
                SeedFile::text("design/oos-design-filing-order.txt", "7\n"),
                SeedFile::text(
                    "design/oos-issue.stdout.txt",
                    "ISSUE_URL=https://github.com/acme/repo/issues/101\nISSUES_FAILED=0\n",
                ),
            ],
        ),
        case(
            "design-oos-annotate-partial",
            "file-oos-annotate",
            &tmpdir,
            vec![
                SeedFile::text(
                    "design/oos-accepted-design.md",
                    "### OOS_1: one\na\n\n### OOS_2: two\nb\n",
                ),
                SeedFile::text(
                    "design/oos-combined.md",
                    "### OOS_1: one\na\n\n### OOS_2: two\nb\n",
                ),
                SeedFile::text("design/oos-design-filing-order.txt", "1\n2\n"),
                SeedFile::text(
                    "design/oos-issue.stdout.txt",
                    "ISSUE_1_URL=https://github.com/acme/repo/issues/101\nISSUE_2_FAILED=true\nISSUES_FAILED=1\n",
                ),
            ],
        ),
        case(
            "design-oos-prepare-missing-tmpdir",
            "file-oos-prepare",
            &[],
            Vec::new(),
        ),
    ]
}

#[test]
fn design_oos_migrated_parity() {
    let goldens = fixture_directory().join("goldens");
    for case in all_cases() {
        let golden = goldens.join(format!("{}.golden.json", case.name));
        if let Err(error) = assert_rust_golden_case(&case, &golden) {
            panic!("{error}");
        }
    }
}
