//! Black-box parity for the four Rust-owned dialectic candidate commands (#8584).

#[path = "support/parity.rs"]
#[allow(dead_code)]
mod parity_support;

use std::{
    env,
    path::{Path, PathBuf},
};

use larch_core::design::dialectic_plan_fingerprint;
use parity_support::{NormalizationRule, ParityCase, Program, SeedFile, assert_case};
use serde_json::json;

const DESIGN: &str = "design";

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

fn strings(values: &[&str]) -> Vec<String> {
    values.iter().map(|value| (*value).to_owned()).collect()
}

fn parity_case(
    name: &'static str,
    verb: &str,
    arguments: &[String],
    seeds: Vec<SeedFile>,
    stdin: Option<&str>,
) -> ParityCase {
    let root = repository_root();
    let path = env::var("PATH").expect("PATH");
    let reference = fixture_directory().join("design_dialectic_migrated_reference.py");
    let mut reference_arguments = vec![reference.to_string_lossy().into_owned(), verb.to_owned()];
    reference_arguments.extend(arguments.iter().cloned());
    let mut rust_arguments = vec!["design".to_owned(), verb.to_owned()];
    rust_arguments.extend(arguments.iter().cloned());
    let mut python = Program::new(python_executable())
        .args(reference_arguments)
        .env("PYTHONPATH", &root.join("python").to_string_lossy())
        .env("CLAUDE_PLUGIN_ROOT", &root.to_string_lossy())
        .env("COLUMNS", "80")
        .env("PATH", &path);
    let mut rust = Program::new(env!("CARGO_BIN_EXE_larch"))
        .args(rust_arguments)
        .env("CLAUDE_PLUGIN_ROOT", &root.to_string_lossy())
        .env("COLUMNS", "80")
        .env("PATH", &path);
    if let Some(stdin) = stdin {
        python = python.stdin(stdin.as_bytes());
        rust = rust.stdin(stdin.as_bytes());
    }
    ParityCase {
        name,
        python,
        rust,
        seed_files: seeds,
        side_effect_records: Vec::new(),
        normalization: vec![NormalizationRule::SandboxRoot],
    }
}

fn design_seed(plan: &str) -> Vec<SeedFile> {
    vec![SeedFile::text(&format!("{DESIGN}/plan.txt"), plan)]
}

fn candidate_payload(fingerprint: Option<&str>, pick: &str) -> String {
    let mut payload = json!({
        "decisions": [{
            "id": "storage-choice",
            "title": "Storage choice",
            "option_a": "Use SQLite",
            "option_b": "Use JSON files",
            "tradeoff": "Query power versus operational simplicity",
            "drafter_pick": pick,
            "why_this_matters": "It changes runtime dependencies"
        }]
    });
    if let Some(fingerprint) = fingerprint {
        payload["plan_fingerprint"] = json!(fingerprint);
    }
    serde_json::to_string(&payload).expect("candidate JSON")
}

fn validation_cases() -> Vec<ParityCase> {
    let plan = "## Plan\n\nUse JSON files.\n\ndiff_lines: 1\n";
    let fingerprint = dialectic_plan_fingerprint(plan.as_bytes());
    let rich_payload = serde_json::to_string(&json!({
        "plan_fingerprint": "kept",
        "decisions": [
            {
                "id": "same",
                "title": {"label": " Café ", "summary": "storage"},
                "option_a": "SQLite",
                "option_b": "JSON",
                "tradeoff": {"description": "query power"},
                "drafter_pick": "option_a",
                "why_this_matters": "runtime"
            },
            {
                "id": "same",
                "title": "Second",
                "option_a": "A",
                "option_b": "B",
                "tradeoff": "tradeoff",
                "drafter_pick": "option_b",
                "why_this_matters": "scope"
            },
            false
        ]
    }))
    .expect("rich payload");
    vec![
        parity_case(
            "design-dialectic-validate-normalize",
            "dialectic-validate-candidates",
            &[],
            Vec::new(),
            Some(&rich_payload),
        ),
        parity_case(
            "design-dialectic-validate-invalid-json",
            "dialectic-validate-candidates",
            &[],
            Vec::new(),
            Some("{\"decisions\":"),
        ),
        parity_case(
            "design-dialectic-validate-required-fingerprint",
            "dialectic-validate-candidates",
            &strings(&[
                "--content-file",
                "{sandbox}/candidate.json",
                "--design-tmpdir",
                "{sandbox}/design",
                "--require-fingerprint",
            ]),
            {
                let mut seeds = design_seed(plan);
                seeds.push(SeedFile::text(
                    "candidate.json",
                    &candidate_payload(Some(&fingerprint), "option_b"),
                ));
                seeds
            },
            None,
        ),
        parity_case(
            "design-dialectic-validate-stale-fingerprint",
            "dialectic-validate-candidates",
            &strings(&[
                "--content-file",
                "{sandbox}/candidate.json",
                "--design-tmpdir",
                "{sandbox}/design",
                "--require-fingerprint",
            ]),
            {
                let mut seeds = design_seed(plan);
                seeds.push(SeedFile::text(
                    "candidate.json",
                    &candidate_payload(Some("stale"), "option_b"),
                ));
                seeds
            },
            None,
        ),
    ]
}

fn write_and_promote_cases() -> Vec<ParityCase> {
    let plan = "## Plan\n\nUse JSON files.\n\ndiff_lines: 1\n";
    let valid = candidate_payload(None, "option_b");
    let mismatch = candidate_payload(None, "option_a");
    vec![
        parity_case(
            "design-dialectic-write-success",
            "dialectic-write-candidates",
            &strings(&[
                "--design-tmpdir",
                "{sandbox}/design",
                "--content-file",
                "{sandbox}/candidate.json",
            ]),
            {
                let mut seeds = design_seed(plan);
                seeds.push(SeedFile::text("candidate.json", &valid));
                seeds
            },
            None,
        ),
        parity_case(
            "design-dialectic-write-missing-content",
            "dialectic-write-candidates",
            &strings(&[
                "--design-tmpdir",
                "{sandbox}/design",
                "--content-file",
                "{sandbox}/missing.json",
            ]),
            design_seed(plan),
            None,
        ),
        parity_case(
            "design-dialectic-write-pick-mismatch",
            "dialectic-write-candidates",
            &strings(&[
                "--design-tmpdir",
                "{sandbox}/design",
                "--content-file",
                "{sandbox}/candidate.json",
            ]),
            {
                let mut seeds = design_seed(plan);
                seeds.push(SeedFile::text("candidate.json", &mismatch));
                seeds
            },
            None,
        ),
        parity_case(
            "design-dialectic-promote-success",
            "dialectic-promote-candidates",
            &strings(&["--design-tmpdir", "{sandbox}/design"]),
            {
                let mut seeds = design_seed(plan);
                seeds.push(SeedFile::text("design/.dialectic-raw-pending.json", &valid));
                seeds
            },
            None,
        ),
        parity_case(
            "design-dialectic-promote-absent",
            "dialectic-promote-candidates",
            &strings(&["--design-tmpdir", "{sandbox}/design"]),
            design_seed(plan),
            None,
        ),
        parity_case(
            "design-dialectic-promote-malformed-fail-open",
            "dialectic-promote-candidates",
            &strings(&["--design-tmpdir", "{sandbox}/design"]),
            {
                let mut seeds = design_seed(plan);
                seeds.push(SeedFile::text("design/.dialectic-raw-pending.json", "{"));
                seeds
            },
            None,
        ),
    ]
}

fn clear_cases() -> Vec<ParityCase> {
    let plan = "## Plan\n\nUse JSON files.\n\ndiff_lines: 1\n";
    let fingerprint = dialectic_plan_fingerprint(plan.as_bytes());
    let clear_args = strings(&[
        "--design-tmpdir",
        "{sandbox}/design",
        "--reason",
        "plan-rewrite",
    ]);
    let candidate = candidate_payload(Some(&fingerprint), "option_b");
    vec![
        parity_case(
            "design-dialectic-clear-stale-retains-raw",
            "dialectic-clear-stale",
            &clear_args,
            {
                let mut seeds = design_seed(plan);
                for (name, content) in [
                    (".dialectic-raw-pending.json", "{\"decisions\":[]}"),
                    (
                        "dialectic-clarifier-candidates.json",
                        "{\"plan_fingerprint\":\"stale\",\"decisions\":[]}",
                    ),
                    ("dialectic-manual-candidates.json", "{}"),
                    ("dialectic-clarifier-status.json", "{}"),
                    ("dialectic-clarifier-digest.md", "stale\n"),
                    ("dialectic-manual-request.txt", "stale\n"),
                ] {
                    seeds.push(SeedFile::text(&format!("design/{name}"), content));
                }
                seeds
            },
            None,
        ),
        parity_case(
            "design-dialectic-clear-preserves-valid-auto",
            "dialectic-clear-stale",
            &clear_args,
            {
                let mut seeds = design_seed(plan);
                seeds.push(SeedFile::text(
                    "design/dialectic-clarifier-candidates.json",
                    &candidate,
                ));
                seeds.push(SeedFile::text(
                    "design/dialectic-clarifier-status.json",
                    &json!({"kind":"auto","plan_fingerprint":fingerprint,"ordered_candidate_ids":["storage-choice"],"generation":99,"state":"running"}).to_string(),
                ));
                seeds.push(SeedFile::text(
                    "design/dialectic-clarifier-digest.md",
                    "auto digest\n",
                ));
                seeds
            },
            None,
        ),
        parity_case(
            "design-dialectic-clear-preserves-valid-manual",
            "dialectic-clear-stale",
            &clear_args,
            {
                let mut seeds = design_seed(plan);
                seeds.push(SeedFile::text(
                    "design/dialectic-manual-candidates.json",
                    &candidate,
                ));
                seeds.push(SeedFile::text(
                    "design/dialectic-clarifier-status.json",
                    &json!({"kind":"manual","plan_fingerprint":fingerprint,"ordered_candidate_ids":["storage-choice"],"generation":"3","state":"complete"}).to_string(),
                ));
                seeds.push(SeedFile::text(
                    "design/dialectic-clarifier-generation.txt",
                    "3\n",
                ));
                seeds.push(SeedFile::text(
                    "design/dialectic-clarifier-digest.md",
                    "manual digest\n",
                ));
                seeds.push(SeedFile::text(
                    "design/dialectic-manual-request.txt",
                    "debate storage-choice\n",
                ));
                seeds
            },
            None,
        ),
    ]
}

fn argument_cases() -> Vec<ParityCase> {
    [
        (
            "dialectic-clear-stale",
            "design-dialectic-clear-stale-help",
            "design-dialectic-clear-stale-missing-required",
        ),
        (
            "dialectic-promote-candidates",
            "design-dialectic-promote-candidates-help",
            "design-dialectic-promote-candidates-missing-required",
        ),
        (
            "dialectic-validate-candidates",
            "design-dialectic-validate-candidates-help",
            "design-dialectic-validate-candidates-missing-required",
        ),
        (
            "dialectic-write-candidates",
            "design-dialectic-write-candidates-help",
            "design-dialectic-write-candidates-missing-required",
        ),
    ]
    .into_iter()
    .flat_map(|(verb, help_name, missing_name)| {
        [
            parity_case(help_name, verb, &strings(&["--help"]), Vec::new(), None),
            parity_case(missing_name, verb, &[], Vec::new(), None),
        ]
    })
    .collect()
}

#[test]
fn design_dialectic_migrated_commands_match_frozen_python_reference() {
    let goldens = fixture_directory().join("goldens");
    for case in validation_cases()
        .into_iter()
        .chain(write_and_promote_cases())
        .chain(clear_cases())
        .chain(argument_cases())
    {
        assert_case(&case, &goldens.join(format!("{}.golden.json", case.name)))
            .unwrap_or_else(|error| panic!("{error}"));
    }
}
