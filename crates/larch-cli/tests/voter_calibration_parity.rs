#[path = "support/parity.rs"]
#[allow(dead_code)]
mod parity_support;

use std::{
    env, fs,
    path::{Path, PathBuf},
};

use parity_support::{NormalizationRule, ParityCase, Program, SeedFile, assert_rust_golden_case};

const REPORT_HEADER: &str = "# Voter Calibration Report";
const GROUND_TRUTH_HEADER: &str = "## Ground-truth Voter Calibration";

const DESIGN_HEADER_22: &str = "finding_id\tfinding_reviewers\tvoting_result\tv1_vote\tv1_correctness\tv1_severity\tv1_quality\tv1_uncertain\tv1_tool\tv2_vote\tv2_correctness\tv2_severity\tv2_quality\tv2_uncertain\tv2_tool\tv3_vote\tv3_correctness\tv3_severity\tv3_quality\tv3_uncertain\tv3_tool\tbody_severity";
const DESIGN_HEADER_21: &str = "finding_id\tfinding_reviewers\tvoting_result\tv1_vote\tv1_correctness\tv1_severity\tv1_quality\tv1_uncertain\tv1_tool\tv2_vote\tv2_correctness\tv2_severity\tv2_quality\tv2_uncertain\tv2_tool\tv3_vote\tv3_correctness\tv3_severity\tv3_quality\tv3_uncertain\tv3_tool";
const CODE_REVIEW_HEADER_21: &str = "finding_id\treviewer_slots\tvoting_result\tv1_vote\tv1_correctness\tv1_severity\tv1_quality\tv1_uncertain\tv1_tool\tv2_vote\tv2_correctness\tv2_severity\tv2_quality\tv2_uncertain\tv2_tool\tv3_vote\tv3_correctness\tv3_severity\tv3_quality\tv3_uncertain\tv3_tool";
const COMPACT_HEADER_18: &str = "finding_id\treviewer_slots\tvoting_result\tv1_vote\tv1_correctness\tv1_severity\tv1_quality\tv1_uncertain\tv2_vote\tv2_correctness\tv2_severity\tv2_quality\tv2_uncertain\tv3_vote\tv3_correctness\tv3_severity\tv3_quality\tv3_uncertain";
const DESIGN_MINIMAL_HEADER: &str =
    "finding_id\tfinding_reviewers\tvoting_result\tv1_vote\tv2_vote\tv3_vote\tscope";

fn fixture_directory() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../../fixtures/rust-parity")
        .canonicalize()
        .expect("canonical parity fixture directory")
}

fn python_executable() -> PathBuf {
    env::split_paths(&env::var_os("PATH").expect("PATH"))
        .map(|directory| directory.join("python3"))
        .find(|candidate| candidate.is_file())
        .and_then(|candidate| candidate.canonicalize().ok())
        .expect("python3 on PATH")
}

/// The core corpus from the retired bash harness: the five documented TSV
/// schema shapes across design (22/21 column), code-review (21 column tool),
/// compact review (18 column), plus a malformed verdict row, a neutral
/// `EXONERATE` row, and a single-YES-vote ineligible row.
fn core_corpus_seeds() -> Vec<SeedFile> {
    vec![
        SeedFile::text(
            "logs/design/run-a/manifest.json",
            "{\"started_at\": \"2026-06-25T12:00:00Z\"}\n",
        ),
        SeedFile::text(
            "logs/design/run-a/plan-review/round-1/findings-classification.tsv",
            &format!(
                "{DESIGN_HEADER_22}\n\
FINDING_1\tR\taccepted\tYES\t\tmajor\t\t\tClaude\tYES\t\tuncertain\t\t\tCodex\tNO\t\tnit\t\t\tCursor\tmajor\n\
FINDING_2\tR\tneutral\tYES\t\tmajor\t\t\tClaude\tNO\t\tnit\t\t\tCodex\t\t\t\t\t\tCursor\tminor\n"
            ),
        ),
        SeedFile::text(
            "logs/design/run-b/manifest.json",
            "{\"started_at\": \"2026-06-25T13:00:00Z\"}\n",
        ),
        SeedFile::text(
            "logs/design/run-b/plan-review/round-1/findings-classification.tsv",
            &format!(
                "{DESIGN_HEADER_21}\n\
FINDING_3\tR\trejected\tNO\t\tnit\t\t\tClaude\tYES\t\tmajor\t\t\tCodex\tNO\t\tminor\t\t\tCursor\n"
            ),
        ),
        SeedFile::text(
            "logs/design/run-corrupt/manifest.json",
            "{\"started_at\": \"2026-06-25T14:00:00Z\"}\n",
        ),
        SeedFile::text(
            "logs/design/run-corrupt/plan-review/round-1/findings-classification.tsv",
            &format!(
                "{DESIGN_HEADER_22}\n\
FINDING_BAD\tR\tbogus\tYES\t\t\t\t\tClaude\tYES\t\t\t\t\tCodex\tNO\t\t\t\t\tCursor\tmajor\n\
FINDING_NEUTRAL\tR\tneutral\tYES\t\t\t\t\tClaude\tEXONERATE\t\t\t\t\tCodex\tYES\t\t\t\t\tCursor\tminor\n"
            ),
        ),
        SeedFile::text(
            "logs/implement/run-c/manifest.json",
            "{\"started_at\": \"2026-06-26T00:00:00Z\"}\n",
        ),
        SeedFile::text(
            "logs/implement/run-c/round-1/findings-classification.tsv",
            &format!(
                "{CODE_REVIEW_HEADER_21}\n\
FINDING_1\tR\taccepted\tYES\t\tblocker\t\t\tcursor-validity\tNO\t\tmajor\t\t\tcursor-plan-fidelity\tYES\t\tuncertain\t\t\tcursor-pragmatism\n"
            ),
        ),
        SeedFile::text(
            "logs/review/run-d/manifest.json",
            "{\"started_at\": \"2026-06-26T01:00:00Z\"}\n",
        ),
        SeedFile::text(
            "logs/review/run-d/review-findings-classification-round-1.tsv",
            &format!(
                "{COMPACT_HEADER_18}\n\
FINDING_1\tR\taccepted\tNO\t\tblocker\t\t\tYES\t\tmajor\t\t\tYES\t\tmajor\t\t\n\
FINDING_2\tR\taccepted\tNO\t\tblocker\t\t\tYES\t\tmajor\t\t\tYES\t\tmajor\t\t\n\
FINDING_3\tR\taccepted\tNO\t\tblocker\t\t\tYES\t\tmajor\t\t\tYES\t\tmajor\t\t\n\
FINDING_4\tR\taccepted\tNO\t\tblocker\t\t\tYES\t\tmajor\t\t\tYES\t\tminor\t\t\n\
FINDING_9\tR\taccepted\tYES\t\tmajor\t\t\t\t\t\t\t\t\t\t\t\t\n"
            ),
        ),
    ]
}

fn era_seed(run: &str, voter_stem: &str, manifest: Option<&str>) -> Vec<SeedFile> {
    let mut seeds = Vec::new();
    if let Some(manifest) = manifest {
        seeds.push(SeedFile::text(
            &format!("logs-era/design/{run}/manifest.json"),
            &format!("{manifest}\n"),
        ));
    }
    seeds.push(SeedFile::text(
        &format!("logs-era/design/{run}/plan-review/round-1/findings-classification.tsv"),
        &format!(
            "{DESIGN_HEADER_22}\n\
FINDING\tR\taccepted\tYES\t\tmajor\t\t\t{voter_stem}-voter\tNO\t\tminor\t\t\t{voter_stem}-peer\tYES\t\tnit\t\t\t{voter_stem}-third\tmajor\n"
        ),
    ));
    seeds
}

/// The era corpus: one pre-boundary run, one at-boundary (post) run, and four
/// runs excluded for a missing manifest, an empty manifest object, an empty
/// `started_at`, and an unparseable `started_at`.
fn era_corpus_seeds() -> Vec<SeedFile> {
    let mut seeds = Vec::new();
    seeds.extend(era_seed(
        "run-pre-era",
        "pre-era",
        Some("{\"started_at\": \"2026-06-25T12:00:00Z\"}"),
    ));
    seeds.extend(era_seed(
        "run-post-era",
        "post-era",
        Some("{\"started_at\": \"2026-06-26T00:00:00Z\"}"),
    ));
    seeds.extend(era_seed("run-missing-started-at", "missing-era", None));
    seeds.extend(era_seed(
        "run-invalid-started-at-empty-manifest",
        "invalid-empty-manifest",
        Some("{}"),
    ));
    seeds.extend(era_seed(
        "run-invalid-started-at-empty-string",
        "invalid-empty-string",
        Some("{\"started_at\": \"\"}"),
    ));
    seeds.extend(era_seed(
        "run-invalid-started-at-bad-date",
        "invalid-bad-date",
        Some("{\"started_at\": \"not-a-date\"}"),
    ));
    seeds
}

/// The false-negative corpus: neutral/rejected compact rows, a minimal design
/// header falling back to positional voter labels, and an `oos`-scoped row
/// excluded from the false-negative totals.
fn false_negative_corpus_seeds() -> Vec<SeedFile> {
    vec![
        SeedFile::text(
            "logs-fn/review/run-compact/manifest.json",
            "{\"started_at\": \"2026-06-27T00:00:00Z\", \"issue_number\": 4242}\n",
        ),
        SeedFile::text(
            "logs-fn/review/run-compact/review-findings-classification-round-1.tsv",
            &format!(
                "{COMPACT_HEADER_18}\n\
FINDING_N\tR\tneutral\tYES\t\tmajor\t\t\tNO\t\tnit\t\t\tYES\t\tmajor\t\t\n\
FINDING_R\tR\trejected\tYES\t\tmajor\t\t\tNO\t\tnit\t\t\tNO\t\tnit\t\t\n"
            ),
        ),
        SeedFile::text(
            "logs-fn/design/run-fallback/manifest.json",
            "{\"started_at\": \"2026-06-27T00:00:00Z\", \"issue_number\": 4242}\n",
        ),
        SeedFile::text(
            "logs-fn/design/run-fallback/plan-review/round-1/findings-classification.tsv",
            &format!("{DESIGN_MINIMAL_HEADER}\nFINDING_FB\tR\tneutral\tYES\tNO\tNO\t\n"),
        ),
        SeedFile::text(
            "logs-fn/design/run-scope/manifest.json",
            "{\"started_at\": \"2026-06-27T00:00:00Z\", \"issue_number\": 4242}\n",
        ),
        SeedFile::text(
            "logs-fn/design/run-scope/plan-review/round-1/findings-classification.tsv",
            &format!(
                "{DESIGN_HEADER_22}\tscope\n\
FINDING_SCOPE\tR\tneutral\tYES\t\tmajor\t\t\tscoped-out\tNO\t\tnit\t\t\tpeer\tNO\t\tnit\t\t\tthird\tmajor\toos\n"
            ),
        ),
    ]
}

/// A filed-OOS implement run whose `oos-issues.ndjson` provides one
/// repo-filtered realized-outcome candidate for issue #123.
fn filed_oos_corpus_seeds() -> Vec<SeedFile> {
    vec![
        SeedFile::text(
            "logs-oos/implement/run-oos/manifest.json",
            "{\"started_at\": \"2026-06-27T00:00:00Z\", \"issue_number\": 4242}\n",
        ),
        SeedFile::text(
            "logs-oos/implement/run-oos/oos-issues.ndjson",
            "{\"body\": \"- **Stable ID**: oos-accepted-review:OOS_1\\n- **Filed URL**: https://github.com/example/larch/issues/123\"}\n",
        ),
    ]
}

fn filed_details_seed() -> SeedFile {
    SeedFile::text(
        "filed-details.json",
        "{\"123\":{\"number\":123,\"title\":\"Offline issue\",\"body\":\"\",\"state\":\"CLOSED\",\"labels\":[]}}\n",
    )
}

/// Single run without a manifest: historical pre-manifest corpora still scan.
fn single_run_seeds() -> Vec<SeedFile> {
    vec![SeedFile::text(
        "run-b-only/design/run-b/plan-review/round-1/findings-classification.tsv",
        &format!(
            "{DESIGN_HEADER_21}\n\
FINDING_3\tR\trejected\tNO\t\tnit\t\t\tClaude\tYES\t\tmajor\t\t\tCodex\tNO\t\tminor\t\t\tCursor\n"
        ),
    )]
}

fn parity_case(
    name: &'static str,
    arguments: &[&str],
    seeds: Vec<SeedFile>,
    fixture_directory: &Path,
) -> ParityCase {
    let reference = fixture_directory.join("voter_calibration_reference.py");
    let python_path = Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../../python")
        .canonicalize()
        .expect("canonical Python package root");
    ParityCase {
        name,
        python: Program::new(python_executable())
            .args(
                std::iter::once(reference.to_string_lossy().into_owned())
                    .chain(arguments.iter().map(|argument| (*argument).to_owned())),
            )
            .env("PYTHONPATH", &python_path.to_string_lossy()),
        rust: Program::new(env!("CARGO_BIN_EXE_larch")).args(
            ["voter-calibration", "analyze"]
                .into_iter()
                .map(str::to_owned)
                .chain(arguments.iter().map(|argument| (*argument).to_owned())),
        ),
        seed_files: seeds,
        side_effect_records: Vec::new(),
        normalization: vec![NormalizationRule::SandboxRoot],
    }
}

/// Assert the recorded golden proves a real success-path report, so a
/// differential no-op (both sides failing identically) cannot pass silently.
fn assert_success_report(golden_path: &Path, channel: &str, required: &str) {
    let golden: serde_json::Value = serde_json::from_str(
        &fs::read_to_string(golden_path).expect("read voter-calibration golden"),
    )
    .expect("parse voter-calibration golden");
    assert_eq!(
        golden.get("exit_code").and_then(serde_json::Value::as_i64),
        Some(0),
        "success case must exit 0: {}",
        golden_path.display()
    );
    let text = match channel {
        "stdout" => golden
            .pointer("/stdout/text")
            .and_then(serde_json::Value::as_str)
            .unwrap_or_default()
            .to_owned(),
        file => golden
            .pointer(&format!("/files/{file}/text"))
            .and_then(serde_json::Value::as_str)
            .unwrap_or_default()
            .to_owned(),
    };
    assert!(
        text.contains(required),
        "success case must render {required:?} in {channel}: {}",
        golden_path.display()
    );
}

#[test]
#[allow(clippy::too_many_lines)] // The complete case matrix stays contiguous for parity review.
fn voter_calibration_analyze_has_frozen_black_box_parity() {
    let fixtures = fixture_directory();
    let core = core_corpus_seeds();
    let era = era_corpus_seeds();
    let fn_corpus = false_negative_corpus_seeds();
    let oos = filed_oos_corpus_seeds();
    let mut oos_with_details = oos.clone();
    oos_with_details.push(filed_details_seed());
    let mut era_realized = oos.clone();
    era_realized.push(filed_details_seed());
    let success_cases: &[&str] = &[
        "voter-calibration-core",
        "voter-calibration-thresholds",
        "voter-calibration-single-run",
        "voter-calibration-era-all",
        "voter-calibration-era-pre",
        "voter-calibration-era-post",
        "voter-calibration-era-auto-unavailable",
        "voter-calibration-false-negative",
        "voter-calibration-realized-offline",
        "voter-calibration-era-realized-offline",
        "voter-calibration-realized-bad-json",
        "voter-calibration-realized-missing-json",
        "voter-calibration-realized-list-json",
        "voter-calibration-realized-no-candidates",
        "voter-calibration-realized-gh-unavailable",
        "voter-calibration-realized-repo-unresolved",
    ];
    let cases = [
        parity_case("voter-calibration-help", &["--help"], Vec::new(), &fixtures),
        parity_case(
            "voter-calibration-unknown",
            &["--unknown"],
            Vec::new(),
            &fixtures,
        ),
        parity_case(
            "voter-calibration-missing-value",
            &["--out"],
            Vec::new(),
            &fixtures,
        ),
        parity_case(
            "voter-calibration-invalid-int",
            &["--min-votes", "x"],
            Vec::new(),
            &fixtures,
        ),
        parity_case(
            "voter-calibration-invalid-float",
            &["--outlier-threshold", "zz"],
            Vec::new(),
            &fixtures,
        ),
        parity_case(
            "voter-calibration-invalid-era",
            &["--era", "bogus"],
            Vec::new(),
            &fixtures,
        ),
        parity_case(
            "voter-calibration-since-date-requires-era",
            &["--era-since-date", "2026-06-26"],
            Vec::new(),
            &fixtures,
        ),
        parity_case(
            "voter-calibration-invalid-era-date-shape",
            &[
                "--log-root",
                "{sandbox}/logs",
                "--era",
                "all",
                "--era-since-date",
                "26-06-26",
            ],
            core.clone(),
            &fixtures,
        ),
        parity_case(
            "voter-calibration-invalid-era-date",
            &[
                "--log-root",
                "{sandbox}/logs",
                "--era",
                "all",
                "--era-since-date",
                "2026-13-01",
            ],
            core.clone(),
            &fixtures,
        ),
        parity_case(
            "voter-calibration-default-no-repo",
            &[],
            Vec::new(),
            &fixtures,
        ),
        parity_case(
            "voter-calibration-missing-root",
            &["--log-root", "{sandbox}/missing"],
            Vec::new(),
            &fixtures,
        ),
        parity_case(
            "voter-calibration-core",
            &[
                "--log-root",
                "{sandbox}/logs",
                "--min-votes",
                "3",
                "--outlier-threshold",
                "0.50",
            ],
            core.clone(),
            &fixtures,
        ),
        parity_case(
            "voter-calibration-thresholds",
            &[
                "--log-root",
                "{sandbox}/logs",
                "--min-votes",
                "3",
                "--outlier-threshold",
                "0.50",
                "--high-severity-threshold",
                "0.50",
            ],
            core.clone(),
            &fixtures,
        ),
        parity_case(
            "voter-calibration-single-run",
            &[
                "--log-root",
                "{sandbox}/run-b-only",
                "--min-votes",
                "2",
                "--outlier-threshold",
                "0.50",
            ],
            single_run_seeds(),
            &fixtures,
        ),
        parity_case(
            "voter-calibration-out",
            &[
                "--log-root",
                "{sandbox}/logs",
                "--out",
                "{sandbox}/report.md",
            ],
            core.clone(),
            &fixtures,
        ),
        parity_case(
            "voter-calibration-era-all",
            &[
                "--log-root",
                "{sandbox}/logs-era",
                "--min-votes",
                "1",
                "--era",
                "all",
                "--era-since-date",
                "2026-06-26",
            ],
            era.clone(),
            &fixtures,
        ),
        parity_case(
            "voter-calibration-era-pre",
            &[
                "--log-root",
                "{sandbox}/logs-era",
                "--min-votes",
                "1",
                "--era",
                "pre",
                "--era-since-date",
                "2026-06-26",
            ],
            era.clone(),
            &fixtures,
        ),
        parity_case(
            "voter-calibration-era-post",
            &[
                "--log-root",
                "{sandbox}/logs-era",
                "--min-votes",
                "1",
                "--era",
                "post",
                "--era-since-date",
                "2026-06-26",
            ],
            era,
            &fixtures,
        ),
        // The sandbox has no Git checkout, `git`, or `gh`, so the automatic
        // boundary degrades to `repo_unresolved` on both sides without any
        // network reach.
        parity_case(
            "voter-calibration-era-auto-unavailable",
            &["--log-root", "{sandbox}/logs", "--era", "all"],
            core.clone(),
            &fixtures,
        ),
        parity_case(
            "voter-calibration-false-negative",
            &["--log-root", "{sandbox}/logs-fn", "--min-votes", "1"],
            fn_corpus,
            &fixtures,
        ),
        parity_case(
            "voter-calibration-realized-offline",
            &[
                "--log-root",
                "{sandbox}/logs-oos",
                "--realized-outcomes",
                "--repo",
                "example/larch",
                "--filed-issue-details-json",
                "{sandbox}/filed-details.json",
            ],
            oos_with_details,
            &fixtures,
        ),
        parity_case(
            "voter-calibration-era-realized-offline",
            &[
                "--log-root",
                "{sandbox}/logs-oos",
                "--era",
                "all",
                "--era-since-date",
                "2026-06-26",
                "--realized-outcomes",
                "--repo",
                "example/larch",
                "--filed-issue-details-json",
                "{sandbox}/filed-details.json",
            ],
            era_realized,
            &fixtures,
        ),
        parity_case(
            "voter-calibration-realized-bad-json",
            &[
                "--log-root",
                "{sandbox}/logs-oos",
                "--realized-outcomes",
                "--repo",
                "example/larch",
                "--filed-issue-details-json",
                "{sandbox}/bad-details.json",
            ],
            {
                let mut seeds = oos.clone();
                seeds.push(SeedFile::text("bad-details.json", "not json"));
                seeds
            },
            &fixtures,
        ),
        parity_case(
            "voter-calibration-realized-missing-json",
            &[
                "--log-root",
                "{sandbox}/logs-oos",
                "--realized-outcomes",
                "--repo",
                "example/larch",
                "--filed-issue-details-json",
                "{sandbox}/missing-details.json",
            ],
            oos.clone(),
            &fixtures,
        ),
        parity_case(
            "voter-calibration-realized-list-json",
            &[
                "--log-root",
                "{sandbox}/logs-oos",
                "--realized-outcomes",
                "--repo",
                "example/larch",
                "--filed-issue-details-json",
                "{sandbox}/list-details.json",
            ],
            {
                let mut seeds = oos.clone();
                seeds.push(SeedFile::text("list-details.json", "[]"));
                seeds
            },
            &fixtures,
        ),
        parity_case(
            "voter-calibration-realized-no-candidates",
            &[
                "--log-root",
                "{sandbox}/logs",
                "--realized-outcomes",
                "--repo",
                "example/larch",
            ],
            core,
            &fixtures,
        ),
        // `gh` is absent from the sandbox `PATH`, so the online bulk-snapshot
        // path degrades to `gh_unavailable` before any fetch on both sides.
        parity_case(
            "voter-calibration-realized-gh-unavailable",
            &[
                "--log-root",
                "{sandbox}/logs-oos",
                "--realized-outcomes",
                "--repo",
                "example/larch",
            ],
            oos.clone(),
            &fixtures,
        ),
        parity_case(
            "voter-calibration-realized-repo-unresolved",
            &["--log-root", "{sandbox}/logs-oos", "--realized-outcomes"],
            oos,
            &fixtures,
        ),
    ];
    let goldens = fixtures.join("goldens");
    for case in cases {
        let golden = goldens.join(format!("{}.golden.json", case.name));
        assert_rust_golden_case(&case, &golden).unwrap_or_else(|error| panic!("{error}"));
        if success_cases.contains(&case.name) {
            assert_success_report(&golden, "stdout", REPORT_HEADER);
        }
        if case.name == "voter-calibration-out" {
            assert_success_report(&golden, "report.md", REPORT_HEADER);
        }
        if case.name == "voter-calibration-realized-offline"
            || case.name == "voter-calibration-era-realized-offline"
        {
            assert_success_report(&golden, "stdout", GROUND_TRUTH_HEADER);
        }
    }
}
