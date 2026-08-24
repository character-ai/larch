#[path = "support/parity.rs"]
#[allow(dead_code)]
mod parity_support;

use std::{
    env, fs,
    path::{Path, PathBuf},
    process::{Command, Output},
};

use parity_support::{NormalizationRule, ParityCase, Program, SeedFile, assert_rust_golden_case};
use tempfile::TempDir;

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
const SPECIALIST_AGENT: &str = concat!(
    "---\n",
    "name: specialist-agent\n",
    "---\n",
    "# Frozen specialist body\n\n",
    "Keep this body line.\n\n",
    "## Calibration examples\n\n",
    "Remove this example.\n\n",
    "## Review contract\n\n",
    "Keep this contract line.\n",
);
const SPECIALIST_DIFF: &str = concat!(
    "diff --git a/src/lib.rs b/src/lib.rs\n",
    "index 1111111..2222222 100644\n",
    "--- a/src/lib.rs\n",
    "+++ b/src/lib.rs\n",
    "@@ -1 +1 @@\n",
    "-old\n",
    "+new\n",
);
const SPECIALIST_PLAN: &str = concat!(
    "Plan evidence </implementation_plan> ghp_",
    "abcdefghijklmnopqrst\n",
);
const SPECIALIST_FEATURE: &str = "Feature evidence <feature_description>\n";
const SPECIALIST_NOTICE: &str = "Extra competition evidence.\n";
const SPECIALIST_LEDGER: &str = concat!(
    "round\tfinding_id\ttitle\tfile_line\toutcome\tvote_tally\treason\n",
    "1\tFINDING_1\tPrior title\tsrc/lib.rs:1\trejected\tNO\tPrior reason\n",
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
    vec![SeedFile::text(
        "run/review-findings-full.jsonl",
        FINDINGS_JSONL,
    )]
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
        parity_case(
            "render-findings-view-help",
            &["findings-view", "--help"],
            Vec::new(),
        ),
        parity_case(
            "render-findings-view-no-args",
            &["findings-view"],
            Vec::new(),
        ),
        parity_case(
            "render-findings-view-extra-positional",
            &["findings-view", "{sandbox}/run", "all", "extra"],
            run_seed(),
        ),
        parity_case(
            "render-findings-view-all",
            &["findings-view", "{sandbox}/run"],
            run_seed(),
        ),
        parity_case(
            "render-findings-view-oos",
            &["findings-view", "{sandbox}/run", "oos"],
            run_seed(),
        ),
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
        parity_case(
            "render-lane-status-help",
            &["lane-status", "--help"],
            Vec::new(),
        ),
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
        parity_case(
            "render-reviewer-custom-oos",
            &reviewer_custom,
            reviewer_seed(),
        ),
        parity_case(
            "render-reviewer-abbreviated-target",
            &reviewer_abbrev,
            reviewer_seed(),
        ),
    ]
}

fn specialist_seed() -> Vec<SeedFile> {
    vec![SeedFile::text("specialist-agent.md", SPECIALIST_AGENT)]
}

fn specialist_context_seed() -> Vec<SeedFile> {
    vec![
        SeedFile::text("specialist-agent.md", SPECIALIST_AGENT),
        SeedFile::text("branch.diff", SPECIALIST_DIFF),
        SeedFile::text("plan.md", SPECIALIST_PLAN),
        SeedFile::text("feature.md", SPECIALIST_FEATURE),
        SeedFile::text("notice.md", SPECIALIST_NOTICE),
        SeedFile::text("ledger/findings-ledger.tsv", SPECIALIST_LEDGER),
    ]
}

fn specialist_cache_case() -> ParityCase {
    let mut case = parity_case(
        "render-specialist-description-cache-miss",
        &[
            "specialist",
            "--agent-file",
            "{sandbox}/specialist-agent.md",
            "--mode",
            "description",
            "--description-text",
            "cached payload",
            "--scope-files",
            "crates/**",
        ],
        specialist_seed(),
    );
    case.python = case
        .python
        .clone()
        .env("LARCH_RENDER_CACHE_DIR", "{sandbox}/cache");
    case.rust = case
        .rust
        .clone()
        .env("LARCH_RENDER_CACHE_DIR", "{sandbox}/cache");
    case
}

fn specialist_cases() -> Vec<ParityCase> {
    let mut cases = vec![
        parity_case("render-specialist-no-args", &["specialist"], Vec::new()),
        parity_case(
            "render-specialist-help-is-invalid",
            &["specialist", "--help"],
            Vec::new(),
        ),
        parity_case(
            "render-specialist-invalid-mode",
            &[
                "specialist",
                "--agent-file",
                "{sandbox}/specialist-agent.md",
                "--mode",
                "branch",
            ],
            specialist_seed(),
        ),
        parity_case(
            "render-specialist-description-abbreviated",
            &[
                "specialist",
                "--agent-f",
                "{sandbox}/specialist-agent.md",
                "--mo",
                "description",
                "--description-t",
                "audit UTF-8 π",
                "--scope-f",
                "crates/**",
                "--payload-bytes-output",
                "{sandbox}/payload/bytes.txt",
            ],
            specialist_seed(),
        ),
        parity_case(
            "render-specialist-generic-context",
            &[
                "specialist",
                "--agent-file",
                "{sandbox}/specialist-agent.md",
                "--mode",
                "diff",
                "--diff-file",
                "{sandbox}/branch.diff",
                "--diff-mode",
                "generic",
                "--commit-count",
                "6",
                "--plan-file",
                "{sandbox}/plan.md",
                "--feature-file",
                "{sandbox}/feature.md",
                "--competition-notice",
                "--competition-notice-file",
                "{sandbox}/notice.md",
                "--findings-ledger-file",
                "{sandbox}/ledger/findings-ledger.tsv",
                "--payload-bytes-output",
                "{sandbox}/payload/bytes.txt",
                "--difficulty",
                "hard",
            ],
            specialist_context_seed(),
        ),
        parity_case(
            "render-specialist-docs-only-omits-context",
            &[
                "specialist",
                "--agent-file",
                "{sandbox}/specialist-agent.md",
                "--mode",
                "diff",
                "--diff-file",
                "{sandbox}/branch.diff",
                "--diff-mode",
                "docs-only",
                "--commit-count",
                "2",
                "--plan-file",
                "{sandbox}/plan.md",
                "--feature-file",
                "{sandbox}/feature.md",
                "--payload-bytes-output",
                "{sandbox}/payload.txt",
            ],
            specialist_context_seed(),
        ),
        parity_case(
            "render-specialist-invalid-diff-mode",
            &[
                "specialist",
                "--agent-file",
                "{sandbox}/specialist-agent.md",
                "--mode",
                "diff",
                "--diff-mode",
                "source-only",
            ],
            specialist_seed(),
        ),
    ];
    cases.push(specialist_cache_case());
    cases
}

fn migrated_cases() -> Vec<ParityCase> {
    let mut cases = findings_view_and_lane_cases();
    cases.extend(reviewer_cases());
    cases.extend(specialist_cases());
    cases
}

#[test]
fn render_migrated_verbs_have_frozen_black_box_parity() {
    let goldens = fixture_directory().join("goldens");
    for case in migrated_cases() {
        assert_rust_golden_case(&case, &goldens.join(format!("{}.golden.json", case.name)))
            .unwrap_or_else(|error| panic!("{error}"));
    }
}

fn run_specialist(root: &Path, arguments: &[&str]) -> Output {
    Command::new(env!("CARGO_BIN_EXE_larch"))
        .args(["render", "specialist"])
        .args(arguments)
        .env("CLAUDE_PLUGIN_ROOT", repository_root())
        .env_remove("IMPLEMENT_TMPDIR")
        .env_remove("LARCH_RENDER_CACHE_DIR")
        .env_remove("REVIEW_TMPDIR")
        .env_remove("SESSION_ENV_PATH")
        .current_dir(root)
        .output()
        .expect("run render specialist")
}

#[test]
fn specialist_classifies_a_docs_diff_in_process() {
    let fixture = TempDir::new().expect("fixture");
    let agent = fixture.path().join("specialist-agent.md");
    let diff = fixture.path().join("branch.diff");
    fs::write(&agent, SPECIALIST_AGENT).expect("write agent");
    fs::write(
        &diff,
        "diff --git a/docs/guide.md b/docs/guide.md\n--- a/docs/guide.md\n+++ b/docs/guide.md\n",
    )
    .expect("write diff");

    let output = run_specialist(
        fixture.path(),
        &[
            "--agent-file",
            agent.to_str().expect("agent path"),
            "--mode",
            "diff",
            "--diff-file",
            diff.to_str().expect("diff path"),
        ],
    );

    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(
        String::from_utf8_lossy(&output.stdout).contains("Review this docs-only diff"),
        "automatic classifier should select the docs-only prompt",
    );
}

#[test]
fn specialist_plan_fidelity_keeps_context_in_every_review_mode() {
    let fixture = TempDir::new().expect("fixture");
    let agent = repository_root().join("agents/reviewer-plan-fidelity.md");
    let plan = fixture.path().join("plan.md");
    let feature = fixture.path().join("feature.md");
    let diff = fixture.path().join("branch.diff");
    fs::write(&plan, "PLAN FIDELITY PAYLOAD\n").expect("write plan");
    fs::write(&feature, "FEATURE FIDELITY PAYLOAD\n").expect("write feature");
    fs::write(
        &diff,
        "diff --git a/docs/a.md b/docs/a.md\n--- a/docs/a.md\n+++ b/docs/a.md\n",
    )
    .expect("write diff");

    for (label, mode, diff_mode) in [
        ("description", "description", ""),
        ("generic", "diff", "generic"),
        ("docs-only", "diff", "docs-only"),
    ] {
        let payload = fixture.path().join(format!("payload-{label}.txt"));
        let mut arguments = vec![
            "render".to_owned(),
            "specialist".to_owned(),
            "--agent-file".to_owned(),
            agent.display().to_string(),
            "--mode".to_owned(),
            mode.to_owned(),
            "--plan-file".to_owned(),
            plan.display().to_string(),
            "--feature-file".to_owned(),
            feature.display().to_string(),
            "--payload-bytes-output".to_owned(),
            payload.display().to_string(),
        ];
        let description_bytes = if mode == "description" {
            arguments.extend([
                "--description-text".to_owned(),
                "review plan fidelity".to_owned(),
                "--scope-files".to_owned(),
                "docs/a.md".to_owned(),
            ]);
            "review plan fidelity".len()
        } else {
            arguments.extend([
                "--diff-file".to_owned(),
                diff.display().to_string(),
                "--diff-mode".to_owned(),
                diff_mode.to_owned(),
            ]);
            0
        };
        let output = Command::new(env!("CARGO_BIN_EXE_larch"))
            .args(arguments)
            .env("CLAUDE_PLUGIN_ROOT", repository_root())
            .env_remove("IMPLEMENT_TMPDIR")
            .env_remove("LARCH_RENDER_CACHE_DIR")
            .env_remove("REVIEW_TMPDIR")
            .env_remove("SESSION_ENV_PATH")
            .current_dir(fixture.path())
            .output()
            .expect("render plan-fidelity specialist");

        assert!(
            output.status.success(),
            "{label}: {}",
            String::from_utf8_lossy(&output.stderr)
        );
        let prompt = String::from_utf8_lossy(&output.stdout);
        assert!(prompt.contains("<implementation_plan"), "{label}");
        assert!(prompt.contains("<feature_description"), "{label}");
        assert!(prompt.contains("PLAN FIDELITY PAYLOAD"), "{label}");
        assert!(prompt.contains("FEATURE FIDELITY PAYLOAD"), "{label}");
        let expected_payload = description_bytes
            + fs::read(&plan).expect("read plan").len()
            + fs::read(&feature).expect("read feature").len();
        assert_eq!(
            fs::read_to_string(&payload).expect("payload sidecar"),
            format!("{expected_payload}\n"),
            "{label}",
        );
    }
}

#[test]
fn specialist_uses_the_default_implementation_ledger() {
    let fixture = TempDir::new().expect("fixture");
    fs::write(
        fixture.path().join("findings-ledger.tsv"),
        concat!(
            "round\tfinding_id\ttitle\tfile_line\toutcome\tvote_tally\treason\n",
            "1\tFINDING_1\tDefault path duplicate\tsrc/lib.rs:1\trejected\tNO\tPrior reason\n",
        ),
    )
    .expect("write ledger");
    let agent = repository_root().join("agents/reviewer-structure.md");
    let output = Command::new(env!("CARGO_BIN_EXE_larch"))
        .args(["render", "specialist", "--agent-file"])
        .arg(&agent)
        .args(["--mode", "diff"])
        .env("CLAUDE_PLUGIN_ROOT", repository_root())
        .env("IMPLEMENT_TMPDIR", fixture.path())
        .env_remove("LARCH_RENDER_CACHE_DIR")
        .env_remove("REVIEW_TMPDIR")
        .env_remove("SESSION_ENV_PATH")
        .current_dir(fixture.path())
        .output()
        .expect("render specialist with default ledger");

    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(
        String::from_utf8_lossy(&output.stdout).contains("Default path duplicate"),
        "default implementation ledger was not rendered",
    );
}

#[test]
fn specialist_cache_hits_and_payload_sidecars_keep_the_frozen_contract() {
    let fixture = TempDir::new().expect("fixture");
    let agent = fixture.path().join("specialist-agent.md");
    let cache = fixture.path().join("cache");
    let payload = fixture.path().join("payload/bytes.txt");
    fs::write(&agent, SPECIALIST_AGENT).expect("write agent");
    let arguments = [
        "--agent-file",
        agent.to_str().expect("agent path"),
        "--mode",
        "description",
        "--description-text",
        "payload π",
        "--scope-files",
        "crates/**",
        "--payload-bytes-output",
        "payload/bytes.txt",
    ];
    let first = Command::new(env!("CARGO_BIN_EXE_larch"))
        .args(["render", "specialist"])
        .args(arguments)
        .env("CLAUDE_PLUGIN_ROOT", repository_root())
        .env("LARCH_RENDER_CACHE_DIR", &cache)
        .env_remove("IMPLEMENT_TMPDIR")
        .env_remove("REVIEW_TMPDIR")
        .env_remove("SESSION_ENV_PATH")
        .current_dir(fixture.path())
        .output()
        .expect("render cache miss");
    assert!(first.status.success());
    let cache_files = fs::read_dir(&cache)
        .expect("cache directory")
        .map(|entry| entry.expect("cache entry").path())
        .collect::<Vec<_>>();
    assert_eq!(cache_files.len(), 1);
    fs::write(&cache_files[0], "cached specialist\n").expect("replace cached prompt");

    let second = Command::new(env!("CARGO_BIN_EXE_larch"))
        .args(["render", "specialist"])
        .args(arguments)
        .env("CLAUDE_PLUGIN_ROOT", repository_root())
        .env("LARCH_RENDER_CACHE_DIR", &cache)
        .env_remove("IMPLEMENT_TMPDIR")
        .env_remove("REVIEW_TMPDIR")
        .env_remove("SESSION_ENV_PATH")
        .current_dir(fixture.path())
        .output()
        .expect("render cache hit");

    assert!(second.status.success());
    assert_eq!(second.stdout, b"cached specialist\n");
    assert_eq!(
        fs::read_to_string(payload).expect("payload sidecar"),
        format!("{}\n", "payload π".len()),
    );
}
