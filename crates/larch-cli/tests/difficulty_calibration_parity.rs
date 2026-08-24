#[path = "support/parity.rs"]
#[allow(dead_code)]
mod parity_support;

use std::{
    env,
    path::{Path, PathBuf},
};

use larch_core::review::code_review_classification_header;
use parity_support::{NormalizationRule, ParityCase, Program, SeedFile, assert_rust_golden_case};

const DESIGN_HEADER: &str =
    "finding_id\tfinding_reviewers\tvoting_result\tv1_vote\tv2_vote\tv3_vote\tscope";
const DEFAULT_NO_REPO: &str = "difficulty-calibration-default-no-repo";
const GIT_CONFIG: &str = "[core]\nrepositoryformatversion = 0\nbare = false\n";
const RATING_TRIVIAL: &str = r#"{"rater":["implement"],"rater_tool":{"name":"codex"},"rater_model":0,"predicted_tier":"TRIVIAL","design_tier":null,"implement_tier":null,"applied_tier":"TRIVIAL","floors_applied":[],"audit_upgrade":null,"escalations":[],"panel_skipped":["typed"]}"#;
const RATING_MODERATE: &str = r#"{"rater":"implement","rater_tool":"codex","rater_model":"gpt-test","predicted_tier":"MODERATE","design_tier":null,"implement_tier":null,"applied_tier":"MODERATE","floors_applied":[],"audit_upgrade":"true","escalations":[],"panel_skipped":null}"#;
const MANIFEST: &str = r#"{"started_at":"2026-06-15T10:00:00Z","issue_number":42}"#;
const TOKEN_REPORT: &str = r#"{"BUCKETS_claude":{"total":9223372036854775807},"BUCKETS_codex":{"total":9223372036854775807}}"#;
const TIMING_REPORT: &str = r#"{"total_seconds":0,"per_step":[{"duration_seconds":9223372036854775807},{"duration_seconds":9223372036854775807}]}"#;

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

fn corpus_seeds() -> Vec<SeedFile> {
    let code_header = code_review_classification_header(false, false);
    let code_rows = format!(
        "{code_header}\nFINDING_1\treviewer\taccepted\nFINDING_2\treviewer\taccepted\nFINDING_3\treviewer\taccepted\n"
    );
    vec![
        SeedFile::text("logs/design/DESIGN/manifest.json", MANIFEST),
        SeedFile::text("logs/design/DESIGN/difficulty-rating.json", RATING_TRIVIAL),
        SeedFile::text("logs/design/DESIGN/token-report-final.json", TOKEN_REPORT),
        SeedFile::text("logs/design/DESIGN/timing-report-final.json", TIMING_REPORT),
        SeedFile::text(
            "logs/design/DESIGN/plan-review/round-1/findings-classification.tsv",
            &format!("{DESIGN_HEADER}\nFINDING_1\treviewer\taccepted\tYES\tNO\tNO\t\n"),
        ),
        SeedFile::text("logs/implement/IMPL/manifest.json", MANIFEST),
        SeedFile::text(
            "logs/implement/IMPL/difficulty-rating.json",
            RATING_MODERATE,
        ),
        SeedFile::text("logs/implement/IMPL/token-report.json", TOKEN_REPORT),
        SeedFile::text("logs/implement/IMPL/timing-report.json", TIMING_REPORT),
        SeedFile::text(
            "logs/implement/IMPL/round-1/findings-classification.tsv",
            &code_rows,
        ),
        SeedFile::text("logs/review/BROKEN/manifest.json", "{"),
        SeedFile::text("logs/review/BROKEN/difficulty-rating.json", "{"),
        SeedFile::text(
            "logs/review/BROKEN/review-findings-full.jsonl",
            "{bad\n{\"id\":\"FINDING_X\",\"phase\":\"design\",\"outcome\":\"accepted\"}\n{\"id\":[\"TYPED\"],\"phase\":\"code-review\",\"outcome\":{\"unexpected\":1}}\n",
        ),
        SeedFile::text(
            "logs/review/NO-SOURCE/difficulty-rating.json",
            RATING_TRIVIAL,
        ),
        SeedFile::text(
            "logs/review/NO-RATING/review-findings.ndjson",
            "{\"id\":\"FINDING_1\",\"phase\":\"code-review\",\"outcome\":\"accepted\",\"round_num\":1}\n",
        ),
        SeedFile::text("logs/design/EMPTY/manifest.json", MANIFEST),
        SeedFile::text("logs/design/EMPTY/difficulty-rating.json", RATING_TRIVIAL),
        SeedFile::text(
            "logs/design/EMPTY/plan-review/round-1/findings-classification.tsv",
            &format!("{DESIGN_HEADER}\n"),
        ),
        SeedFile::text("logs/implement/BOUND/manifest.json/child", "not a file"),
        SeedFile::text(
            "logs/implement/BOUND/difficulty-rating.json",
            RATING_TRIVIAL,
        ),
        SeedFile::text("logs/implement/BOUND/token-report.json/child", "not a file"),
        SeedFile::text(
            "logs/implement/BOUND/timing-report.json/child",
            "not a file",
        ),
        SeedFile::text(
            "logs/implement/BOUND/round-1/findings-classification.tsv",
            &format!("{code_header}\nFINDING_1\treviewer\trejected\n"),
        ),
        SeedFile::text(
            "logs/rejected-analysis-verdicts.tsv",
            "schema_version\tfinding_hash\tsource_skill\trun_id\tround_num\tfinding_id\tdissenting_slots\tverdict\tcurrent_location\tevidence\ttriaged_at\n1\thash1\timplement\tIMPL\t1\tFINDING_1\tv1\tstale\tloc\tevidence\t2026-01-01T00:00:00Z\n1\thash1\timplement\tIMPL\t1\tFINDING_1\tv1\tconfirmed\tloc\tevidence\t2026-01-02T00:00:00Z\n",
        ),
    ]
}

fn parity_case(
    name: &'static str,
    arguments: &[&str],
    seeds: Vec<SeedFile>,
    fixture_directory: &Path,
) -> ParityCase {
    let reference = fixture_directory.join("difficulty_calibration_reference.py");
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
            .env("PYTHONPATH", &python_path.to_string_lossy())
            .env("PATH", &env::var("PATH").expect("PATH")),
        rust: Program::new(env!("CARGO_BIN_EXE_larch"))
            .args(
                ["difficulty-calibration", "analyze"]
                    .into_iter()
                    .map(str::to_owned)
                    .chain(arguments.iter().map(|argument| (*argument).to_owned())),
            )
            .env("PATH", &env::var("PATH").expect("PATH")),
        seed_files: seeds,
        side_effect_records: Vec::new(),
        normalization: vec![NormalizationRule::SandboxRoot],
    }
}

#[test]
fn difficulty_calibration_analyze_has_frozen_black_box_parity() {
    let fixtures = fixture_directory();
    let cases = [
        parity_case(
            "difficulty-calibration-help",
            &["--help"],
            Vec::new(),
            &fixtures,
        ),
        parity_case(
            "difficulty-calibration-unknown",
            &["--unknown"],
            Vec::new(),
            &fixtures,
        ),
        parity_case(
            "difficulty-calibration-missing-value",
            &["--out"],
            Vec::new(),
            &fixtures,
        ),
        parity_case(
            "difficulty-calibration-missing-root",
            &["--log-root", "{sandbox}/missing"],
            Vec::new(),
            &fixtures,
        ),
        parity_case(DEFAULT_NO_REPO, &[], Vec::new(), &fixtures),
        parity_case(
            "difficulty-calibration-default-missing-origin",
            &[],
            vec![
                SeedFile::text(".git/HEAD", "ref: refs/heads/main\n"),
                SeedFile::text(".git/config", GIT_CONFIG),
                SeedFile::text(".git/objects/info/.keep", ""),
                SeedFile::text(".git/refs/heads/.keep", ""),
            ],
            &fixtures,
        ),
        parity_case(
            "difficulty-calibration-empty",
            &["--log-root", "{sandbox}/empty"],
            vec![SeedFile::text("empty/.keep", "")],
            &fixtures,
        ),
        parity_case(
            "difficulty-calibration-corpus-out",
            &[
                "--log-root",
                "{sandbox}/logs",
                "--out",
                "{sandbox}/wire/report.md",
            ],
            corpus_seeds(),
            &fixtures,
        ),
    ];
    let goldens = fixtures.join("goldens");
    for case in cases {
        assert_rust_golden_case(&case, &goldens.join(format!("{}.golden.json", case.name)))
            .unwrap_or_else(|error| panic!("{error}"));
    }
}
