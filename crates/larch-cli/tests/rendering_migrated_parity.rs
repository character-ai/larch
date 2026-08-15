#[path = "support/parity.rs"]
#[allow(dead_code)]
mod parity_support;

use std::{
    env,
    path::{Path, PathBuf},
};

use parity_support::{NormalizationRule, ParityCase, Program, SeedFile, assert_case};

const FINDINGS_JSONL: &str = concat!(
    "{\"outcome\":\"accepted\",\"round_num\":1,\"prose_body\":\"Alpha body\"}\n",
    "\n",
    "{\"outcome\":\"rejected\",\"round_num\":2,\"prose_body\":\"Beta body\"}\n",
    "{\"outcome\":\"out_of_scope\",\"round_num\":3,\"prose_body\":null}\n",
    "not-json\n",
    "{\"outcome\":\"accepted\",\"round_num\":null,\"prose_body\":\"No round\"}\n",
);

const LANE_STATUS: &str = concat!(
    "# comment line\n",
    "RESEARCH_ARCH_STATUS=ok\n",
    "RESEARCH_EDGE_STATUS=fallback_binary_missing\n",
    "RESEARCH_EXT_STATUS=fallback_probe_failed\n",
    "RESEARCH_EXT_REASON=probe timed | out = badly    with   spaces\n",
    "RESEARCH_SEC_STATUS=fallback_runtime_timeout\n",
    "VALIDATION_CODE_STATUS=fallback_runtime_failed\n",
    "VALIDATION_CODE_REASON=runtime boom\n",
    "VALIDATION_CURSOR_STATUS=weird_token\n",
    "VALIDATION_CODEX_STATUS=ok\n",
);

const RESEARCH_QUESTION: &str = "What is the research question here?\n";
const RESEARCH_CONTEXT: &str = "Some research findings.\nLine two.\n";
const INSCOPE: &str = "What the concern is\nSuggested revision to the plan\n";
const CUSTOM_OOS: &str = "Custom OOS instruction line\n";

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
    let reference = fixture_directory().join("rendering_migrated_reference.py");
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
            .env("PATH", &path),
        rust: Program::new(env!("CARGO_BIN_EXE_larch"))
            .args(
                std::iter::once("render".to_owned())
                    .chain(arguments.iter().map(|argument| (*argument).to_owned())),
            )
            .env("CLAUDE_PLUGIN_ROOT", &plugin_root)
            .env("PATH", &path),
        seed_files: seeds,
        side_effect_records: Vec::new(),
        normalization: vec![NormalizationRule::SandboxRoot],
    }
}

fn run_seed() -> Vec<SeedFile> {
    vec![SeedFile::text("run/review-findings-full.jsonl", FINDINGS_JSONL)]
}

fn reviewer_seed() -> Vec<SeedFile> {
    vec![
        SeedFile::text("rq.txt", RESEARCH_QUESTION),
        SeedFile::text("ctx.txt", RESEARCH_CONTEXT),
        SeedFile::text("inscope.txt", INSCOPE),
        SeedFile::text("oos.txt", CUSTOM_OOS),
    ]
}

fn findings_view_and_lane_cases() -> Vec<ParityCase> {
    // Flag-abbreviation parity: the retired argparse owners accepted any
    // unambiguous prefix (`--hel`, `--inp`), so the Rust owner must too.
    vec![
        parity_case("render-findings-view-help", &["findings-view", "--help"], Vec::new()),
        parity_case("render-findings-view-no-args", &["findings-view"], Vec::new()),
        parity_case(
            "render-findings-view-extra-positional",
            &["findings-view", "{sandbox}/run", "all", "extra"],
            run_seed(),
        ),
        parity_case("render-findings-view-all", &["findings-view", "{sandbox}/run"], run_seed()),
        parity_case("render-findings-view-oos", &["findings-view", "{sandbox}/run", "oos"], run_seed()),
        parity_case(
            "render-findings-view-unknown-view",
            &["findings-view", "{sandbox}/run", "bogus"],
            run_seed(),
        ),
        parity_case(
            "render-findings-view-missing-jsonl",
            &["findings-view", "{sandbox}/missing"],
            Vec::new(),
        ),
        parity_case(
            "render-findings-view-help-abbreviated",
            &["findings-view", "--hel"],
            Vec::new(),
        ),
        parity_case("render-lane-status-help", &["lane-status", "--help"], Vec::new()),
        parity_case("render-lane-status-no-input", &["lane-status"], Vec::new()),
        parity_case(
            "render-lane-status-missing-file",
            &["lane-status", "--input", "{sandbox}/nope.txt"],
            Vec::new(),
        ),
        parity_case(
            "render-lane-status-success",
            &["lane-status", "--input", "{sandbox}/lane-status.txt"],
            vec![SeedFile::text("lane-status.txt", LANE_STATUS)],
        ),
        parity_case(
            "render-lane-status-abbreviated-input",
            &["lane-status", "--inp", "{sandbox}/lane-status.txt"],
            vec![SeedFile::text("lane-status.txt", LANE_STATUS)],
        ),
    ]
}

fn reviewer_cases() -> Vec<ParityCase> {
    let reviewer_args = [
        "reviewer",
        "--target",
        "an implementation plan",
        "--research-question-file",
        "{sandbox}/rq.txt",
        "--context-file",
        "{sandbox}/ctx.txt",
        "--in-scope-instruction-file",
        "{sandbox}/inscope.txt",
    ];
    let reviewer_custom = [
        "reviewer",
        "--target",
        "code changes",
        "--research-question-file",
        "{sandbox}/rq.txt",
        "--context-file",
        "{sandbox}/ctx.txt",
        "--in-scope-instruction-file",
        "{sandbox}/inscope.txt",
        "--oos-instruction-file",
        "{sandbox}/oos.txt",
    ];
    let reviewer_abbrev = [
        "reviewer",
        "--tar",
        "an implementation plan",
        "--research-question-file",
        "{sandbox}/rq.txt",
        "--context-file",
        "{sandbox}/ctx.txt",
        "--in-scope-instruction-file",
        "{sandbox}/inscope.txt",
    ];
    vec![
        parity_case("render-reviewer-help", &["reviewer", "--help"], Vec::new()),
        parity_case(
            "render-reviewer-no-target",
            &[
                "reviewer",
                "--research-question-file",
                "{sandbox}/rq.txt",
                "--context-file",
                "{sandbox}/ctx.txt",
                "--in-scope-instruction-file",
                "{sandbox}/inscope.txt",
            ],
            reviewer_seed(),
        ),
        parity_case(
            "render-reviewer-missing-question",
            &[
                "reviewer",
                "--target",
                "x",
                "--research-question-file",
                "{sandbox}/nope.txt",
                "--context-file",
                "{sandbox}/ctx.txt",
                "--in-scope-instruction-file",
                "{sandbox}/inscope.txt",
            ],
            reviewer_seed(),
        ),
        parity_case("render-reviewer-success", &reviewer_args, reviewer_seed()),
        parity_case("render-reviewer-custom-oos", &reviewer_custom, reviewer_seed()),
        parity_case("render-reviewer-abbreviated-target", &reviewer_abbrev, reviewer_seed()),
    ]
}

fn migrated_cases() -> Vec<ParityCase> {
    let mut cases = findings_view_and_lane_cases();
    cases.extend(reviewer_cases());
    cases
}

#[test]
fn render_migrated_verbs_have_frozen_black_box_parity() {
    let goldens = fixture_directory().join("goldens");
    for case in migrated_cases() {
        assert_case(&case, &goldens.join(format!("{}.golden.json", case.name)))
            .unwrap_or_else(|error| panic!("{error}"));
    }
}
