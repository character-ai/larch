//! Golden-driven black-box contract for the settlement and finalization verbs.

#[path = "support/recorded.rs"]
#[allow(dead_code)]
mod recorded_support;

use std::{
    env,
    path::{Path, PathBuf},
};

use recorded_support::{NormalizationRule, RecordedCase, Program, SeedFile, assert_recorded_case};

fn repository_root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .canonicalize()
        .expect("canonical repository root")
}

fn fixture_directory() -> PathBuf {
    repository_root().join("crates/larch-cli/tests/fixtures/recorded")
}


fn args(values: &[&str]) -> Vec<String> {
    values.iter().map(|value| (*value).to_owned()).collect()
}

fn recorded_case(
    name: &'static str,
    arguments: &[String],
    seeds: Vec<SeedFile>,
    env_rows: &[(&str, String)],
) -> RecordedCase {
    let root = repository_root();
    let plugin_root = root.to_string_lossy().into_owned();
    let path = env::var("PATH").expect("PATH");
    let binary = env!("CARGO_BIN_EXE_larch");
    let mut program = Program::new(binary)
        .args(arguments.iter().cloned())
        .env("CLAUDE_PLUGIN_ROOT", &plugin_root)
        .env("LARCH_BINARY", binary)
        .env("LARCH_QUIET_DISABLE", "1")
        .env("LARCH_TEST_TIMING_NOW", "1787000000")
        .env("COLUMNS", "1000")
        .env("PATH", &path);
    for (key, value) in env_rows {
        program = program.env(key, value);
    }
    RecordedCase {
        name,
        program,
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
const CONTRACT_PLAN: &str = concat!(
    "## Plan\n\n",
    "### Closed decisions and ownership\n\n- Publish keeps one owner.\n\n",
    "### Ordered implementation\n\n1. Write the plan block.\n2. Rename the issue.\n\n",
    "## Files to modify/create\n\n### NEW: src/lib.rs\n\n",
    "## Acceptance\n\n- The publish rows stay allowlisted.\n\n",
    "## Breaking changes and migration\n\nNone.\n\n",
    "diff_lines: 12\n",
);

fn design_seed() -> Vec<SeedFile> {
    vec![SeedFile::text(&format!("{DESIGN}/.keep"), "")]
}

fn design_env() -> Vec<(&'static str, String)> {
    vec![
        ("DESIGN_TMPDIR", "{sandbox}/design".to_owned()),
        ("REPO_ROOT", "{sandbox}/consumer".to_owned()),
    ]
}

fn domain_case(
    name: &'static str,
    domain: &str,
    tail: &[&str],
    seeds: Vec<SeedFile>,
    env_rows: &[(&str, String)],
) -> RecordedCase {
    let mut arguments = vec![domain.to_owned()];
    arguments.extend(tail.iter().map(|value| (*value).to_owned()));
    recorded_case(name, &arguments, seeds, env_rows)
}

fn finalize_case(name: &'static str, values: &[&str], seeds: Vec<SeedFile>) -> RecordedCase {
    let mut arguments = vec!["design".to_owned()];
    arguments.extend(values.iter().map(|value| (*value).to_owned()));
    recorded_case(name, &arguments, seeds, &design_env())
}

fn gate_c_case() -> RecordedCase {
    let mut case = finalize_case(
        "design-step5c-gate-c-refusal",
        &["step5c", "--skip-validate"],
        vec![
            SeedFile::text("design/.completed/step-5b", ""),
            SeedFile::text("design/.completed/step-3", ""),
            SeedFile::text("design/.completed/step-5b.5", ""),
            SeedFile::text("design/architecture-diagram.skipped", ""),
            SeedFile::text(
                "design/.step3-review-result.env",
                "STEP3_REVIEW_LOOP_STATUS=complete\nROUNDS_COMPLETED=1\n",
            ),
            SeedFile::text("design/plan.txt", CONTRACT_PLAN),
        ],
    );
    let plugin = fixture_directory().join("design_finalize_fake_plugin");
    let plugin = plugin.to_string_lossy();
    for (key, value) in [
        ("CLAUDE_PLUGIN_ROOT", plugin.as_ref()),
        ("ISSUE_NUMBER", "8586"),
        ("CLAUDE_PID", "123"),
    ] {
        case.program = case.program.clone().env(key, value);
    }
    case
}

fn fake_publish_case(name: &'static str, mode: &str) -> RecordedCase {
    let mut case = finalize_case(
        name,
        &["step5c"],
        vec![
            SeedFile::text("design/.completed/step-5b", ""),
            SeedFile::text("design/composed-plan.md", "## Plan\n\nReady.\n"),
        ],
    );
    let plugin = fixture_directory()
        .join("design_finalize_fake_plugin")
        .to_string_lossy()
        .into_owned();
    for (key, value) in [
        ("CLAUDE_PLUGIN_ROOT", plugin.as_str()),
        ("LARCH_BINARY", ""),
        ("DESIGN_FINALIZE_FAKE_MODE", mode),
        ("ISSUE_NUMBER", "8586"),
        ("CLAUDE_PID", "123"),
    ] {
        case.program = case.program.clone().env(key, value);
    }
    case
}

fn step5c_missing_step5b_case() -> RecordedCase {
    finalize_case(
        "design-step5c-missing-step5b",
        &[
            "step5c",
            "--session-env-path",
            "{sandbox}/source-env.sh",
            "--claude-pid",
            "123",
        ],
        vec![
            SeedFile::text("design/.keep", ""),
            SeedFile::text("source-env.sh", "STANDALONE_HEAVY_FAILED=true\n"),
        ],
    )
}

fn step6_cleanup_success_case() -> RecordedCase {
    let arguments = args(&["design", "step6-cleanup", "--claude-pid", "123"]);
    recorded_case(
        "design-step6-cleanup-success",
        &arguments,
        vec![SeedFile::text(
            ".tmp/design/.design-step5c-status.env",
            "PLAN_WRITE_OK=true\nPUBLISH_OK=true\nSESSION_ID=\nCLEANUP_ELIGIBLE=true\n",
        )],
        &[("DESIGN_TMPDIR", "{sandbox}/.tmp/design".to_owned())],
    )
}

fn prepare_missing_assessment_case() -> RecordedCase {
    domain_case(
        "design-step5b-prepare-missing-gatec-assessments",
        "design",
        &["step5b-prepare"],
        design_seed(),
        &[("DESIGN_TMPDIR", "{sandbox}/design".to_owned())],
    )
}

fn prepare_session_repo_root_case() -> RecordedCase {
    let mut seeds = design_seed();
    seeds.extend([
        SeedFile::text("source-env.sh", "REPO_ROOT=consumer\n"),
        SeedFile::text(
            "consumer/ARCHITECTURAL_INVARIANTS.md",
            "## I-Core-1: Keep one owner\n",
        ),
    ]);
    domain_case(
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

fn prepare_skip_case() -> RecordedCase {
    domain_case(
        "design-step5b-prepare-skip-no-items",
        "design",
        &["step5b-prepare"],
        design_seed(),
        &design_env(),
    )
}

fn prepare_ready_case() -> RecordedCase {
    let mut seeds = design_seed();
    seeds.push(SeedFile::text("design/oos-accepted-design.md", OOS));
    domain_case(
        "design-step5b-prepare-ready",
        "design",
        &["step5b-prepare"],
        seeds,
        &design_env(),
    )
}

fn annotate_empty_stdout_case() -> RecordedCase {
    domain_case(
        "design-step5b-annotate-empty-stdout-retry",
        "design",
        &["step5b-annotate"],
        design_seed(),
        &design_env(),
    )
}

fn annotate_success_case() -> RecordedCase {
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
    domain_case(
        "design-step5b-annotate-success",
        "design",
        &["step5b-annotate"],
        seeds,
        &design_env(),
    )
}

fn assert_cases(cases: impl IntoIterator<Item = RecordedCase>) {
    let goldens = fixture_directory().join("goldens");
    for case in cases {
        assert_recorded_case(&case, &goldens.join(format!("{}.golden.json", case.name)))
            .unwrap_or_else(|error| panic!("{error}"));
    }
}

#[test]
fn recorded_design_settlement_contract() {
    assert_cases([
        domain_case(
            "design-step35-settle-gate-b-missing-round",
            "design",
            &["step35-settle", "--site", "gate-b"],
            design_seed(),
            &design_env(),
        ),
        domain_case(
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
    ]);
}

#[test]
fn recorded_design_step5c_contract() {
    assert_cases([
        finalize_case(
            "design-compose-plan-md-basic",
            &["compose-plan-md", "--design-tmpdir", "{sandbox}/design"],
            vec![
                SeedFile::text("design/plan.txt", "### NEW: src/lib.rs\n- Add it.\n"),
                SeedFile::text("design/plan-diff-stat.env", "DIFF_LINES=3\n"),
            ],
        ),
        finalize_case("design-step2b5-missing-plan", &["step2b5"], design_seed()),
        step5c_missing_step5b_case(),
        gate_c_case(),
        fake_publish_case("design-step5c-success", "success"),
        fake_publish_case("design-step5c-rc5-stdout-fallback", "rc5"),
    ]);
}

#[test]
fn recorded_design_step6_contract() {
    assert_cases([
        finalize_case("design-step6-missing-status", &["step6"], design_seed()),
        finalize_case(
            "design-step6-cleanup-preserved",
            &["step6-cleanup"],
            vec![SeedFile::text(
                "design/.design-step5c-status.env",
                "PLAN_WRITE_OK=false\nCLEANUP_ELIGIBLE=false\n",
            )],
        ),
        finalize_case(
            "design-step6-prelude-missing-status",
            &["step6-prelude"],
            design_seed(),
        ),
        step6_cleanup_success_case(),
    ]);
}
