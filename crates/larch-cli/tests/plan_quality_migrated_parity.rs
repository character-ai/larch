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

fn parity_case(name: &'static str, arguments: &[&str], seeds: Vec<SeedFile>) -> ParityCase {
    let root = repository_root();
    let reference = fixture_directory().join("plan_quality_migrated_reference.py");
    let python_path = root.join("python");
    let plugin_root = root.to_string_lossy().into_owned();
    let path = env::var("PATH").expect("PATH");
    ParityCase {
        name,
        python: Program::new(python_executable())
            .args(
                std::iter::once(reference.to_string_lossy().into_owned())
                    .chain(arguments.iter().map(|argument| (*argument).to_owned())),
            )
            .env("PYTHONPATH", &python_path.to_string_lossy())
            .env("CLAUDE_PLUGIN_ROOT", &plugin_root)
            .env("LARCH_QUIET_DISABLE", "1")
            .env("COLUMNS", "1000")
            .env("PATH", &path),
        rust: Program::new(env!("CARGO_BIN_EXE_larch"))
            .args(
                std::iter::once("plan".to_owned())
                    .chain(arguments.iter().map(|argument| (*argument).to_owned())),
            )
            .env("CLAUDE_PLUGIN_ROOT", &plugin_root)
            .env("LARCH_QUIET_DISABLE", "1")
            .env("COLUMNS", "1000")
            .env("PATH", &path),
        seed_files: seeds,
        side_effect_records: Vec::new(),
        normalization: vec![NormalizationRule::SandboxRoot],
    }
}

fn mini_plan() -> &'static str {
    "### NEW: fixture\n\n1. Touch `scripts/noop.sh`.\n\ndiff_lines: 1\n"
}

fn session_seeds(plan: &str) -> Vec<SeedFile> {
    vec![SeedFile::text(
        ".home/.cache/larch/sessions/plan-quality-parity/plan.txt",
        plan,
    )]
}

fn design_tmpdir() -> &'static str {
    "{sandbox}/.home/.cache/larch/sessions/plan-quality-parity"
}

fn help_and_usage_cases() -> Vec<ParityCase> {
    vec![
        parity_case("plan-parse-commands-help", &["parse-commands", "--help"], Vec::new()),
        parity_case("plan-parse-commands-no-args", &["parse-commands"], Vec::new()),
        parity_case(
            "plan-validate-commands-help",
            &["validate-commands", "--help"],
            Vec::new(),
        ),
        parity_case("plan-validate-commands-no-args", &["validate-commands"], Vec::new()),
        parity_case("plan-validate-help", &["validate", "--help"], Vec::new()),
        parity_case("plan-validate-no-args", &["validate"], Vec::new()),
        parity_case("plan-check-size-help", &["check-size", "--help"], Vec::new()),
        parity_case("plan-check-size-no-args", &["check-size"], Vec::new()),
        parity_case(
            "plan-set-oversize-override-help",
            &["set-oversize-override", "--help"],
            Vec::new(),
        ),
        parity_case(
            "plan-set-oversize-override-no-args",
            &["set-oversize-override"],
            Vec::new(),
        ),
        parity_case(
            "plan-revise-waterfall-help",
            &["revise-waterfall", "--help"],
            Vec::new(),
        ),
        parity_case("plan-revise-waterfall-no-args", &["revise-waterfall"], Vec::new()),
        parity_case(
            "plan-auto-fix-commands-help",
            &["auto-fix-commands", "--help"],
            Vec::new(),
        ),
        parity_case("plan-auto-fix-commands-no-args", &["auto-fix-commands"], Vec::new()),
        parity_case(
            "plan-validator-autofix-help",
            &["validator-autofix", "--help"],
            Vec::new(),
        ),
        parity_case(
            "plan-optional-trailers-help",
            &["optional-trailers", "--help"],
            Vec::new(),
        ),
        parity_case("plan-optional-trailers-no-args", &["optional-trailers"], Vec::new()),
        parity_case(
            "plan-compose-goals-test-help",
            &["compose-goals-test", "--help"],
            Vec::new(),
        ),
        parity_case("plan-compose-goals-test-no-args", &["compose-goals-test"], Vec::new()),
    ]
}

fn behavior_cases() -> Vec<ParityCase> {
    let session = design_tmpdir();
    let plan_path = format!("{session}/plan.txt");
    let plan = mini_plan();
    vec![
        parity_case(
            "plan-parse-commands-success",
            &[
                "parse-commands",
                "--plan-file",
                &plan_path,
                "--output",
                "{sandbox}/commands.tsv",
            ],
            session_seeds(plan),
        ),
        parity_case(
            "plan-validate-success",
            &[
                "validate",
                "--plan-file",
                &plan_path,
                "--design-tmpdir",
                session,
                "--repo-root",
                "{sandbox}",
            ],
            session_seeds(plan),
        ),
        parity_case(
            "plan-check-size-success",
            &["check-size", "--design-tmpdir", session],
            session_seeds(plan),
        ),
        parity_case(
            "plan-optional-trailers-parse",
            &["optional-trailers", "parse", "--plan-file", &plan_path],
            session_seeds(plan),
        ),
        parity_case(
            "plan-compose-goals-test-success",
            &["compose-goals-test", "--plan-file", &plan_path],
            session_seeds(plan),
        ),
        parity_case(
            "plan-set-oversize-override-success",
            &["set-oversize-override", "--design-tmpdir", session],
            session_seeds(plan),
        ),
        // Vendor verbs: usage refusal only (no network / agent spawn).
        parity_case(
            "plan-revise-waterfall-missing-files",
            &[
                "revise-waterfall",
                "--design-tmpdir",
                session,
                "--plan-file",
                &plan_path,
                "--findings-file",
                "{sandbox}/missing-findings.md",
                "--feature-file",
                "{sandbox}/missing-feature.txt",
                "--round-num",
                "1",
            ],
            session_seeds(plan),
        ),
        parity_case(
            "plan-auto-fix-commands-missing-plan",
            &[
                "auto-fix-commands",
                "--design-tmpdir",
                session,
                "--plan-file",
                "{sandbox}/missing-plan.txt",
            ],
            session_seeds(plan),
        ),
        parity_case(
            "plan-validator-autofix-operator-cancel",
            &["validator-autofix", "--operator-cancel"],
            Vec::new(),
        ),
    ]
}

#[test]
fn plan_quality_migrated_verbs_match_frozen_python_reference() {
    let goldens = fixture_directory().join("goldens");
    for case in help_and_usage_cases()
        .into_iter()
        .chain(behavior_cases())
    {
        assert_case(&case, &goldens.join(format!("{}.golden.json", case.name)))
            .unwrap_or_else(|error| panic!("{error}"));
    }
}
