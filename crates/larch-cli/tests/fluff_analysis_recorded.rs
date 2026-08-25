#[path = "support/recorded.rs"]
#[allow(dead_code)]
mod recorded_support;

use std::{
    env, fs,
    path::{Path, PathBuf},
};

use recorded_support::{NormalizationRule, RecordedCase, Program, SeedFile, assert_recorded_case};

const REPORT_HEADER: &str = "# Review Fluff Analysis";

const IMPL_HEADER_23: &str = "finding_id\treviewer_slots\tvoting_result\tv1_vote\tv1_correctness\tv1_severity\tv1_quality\tv1_uncertain\tv1_tool\tv2_vote\tv2_correctness\tv2_severity\tv2_quality\tv2_uncertain\tv2_tool\tv3_vote\tv3_correctness\tv3_severity\tv3_quality\tv3_uncertain\tv3_tool\tbody_severity\tscope";
const IMPL_HEADER_21: &str = "finding_id\treviewer_slots\tvoting_result\tv1_vote\tv1_correctness\tv1_severity\tv1_quality\tv1_uncertain\tv1_tool\tv2_vote\tv2_correctness\tv2_severity\tv2_quality\tv2_uncertain\tv2_tool\tv3_vote\tv3_correctness\tv3_severity\tv3_quality\tv3_uncertain\tv3_tool";
const COMPACT_HEADER_18: &str = "finding_id\treviewer_slots\tvoting_result\tv1_vote\tv1_correctness\tv1_severity\tv1_quality\tv1_uncertain\tv2_vote\tv2_correctness\tv2_severity\tv2_quality\tv2_uncertain\tv3_vote\tv3_correctness\tv3_severity\tv3_quality\tv3_uncertain";
const DESIGN_HEADER_22: &str = "finding_id\tfinding_reviewers\tvoting_result\tv1_vote\tv1_correctness\tv1_severity\tv1_quality\tv1_uncertain\tv1_tool\tv2_vote\tv2_correctness\tv2_severity\tv2_quality\tv2_uncertain\tv2_tool\tv3_vote\tv3_correctness\tv3_severity\tv3_quality\tv3_uncertain\tv3_tool\tbody_severity";

fn fixture_directory() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("tests/fixtures/recorded")
        .canonicalize()
        .expect("canonical recorded contract fixture directory")
}

/// The full synthetic corpus: accepted/rejected/OOS implement findings,
/// version segmentation rows, TSV-primary false-negative joins with the
/// `blocking` alias and scope exclusions, multi-round and round-local JSONL,
/// 21-column and compact 18-column TSVs, self-review tally fallback,
/// malformed-JSONL suppression, malformed `larch_version`, guideline and
/// invariant assessment coverage (clean/deviation/violation/empty/missing),
/// and valid/malformed/missing-current/missing-legacy ship outcomes.
#[allow(clippy::too_many_lines)] // One contiguous corpus keeps the fixture reviewable.
fn corpus_seeds() -> Vec<SeedFile> {
    let mut seeds = vec![
        SeedFile::text(
            "logs/implement/RUN-IMPL-1/manifest.json",
            r#"{"started_at":"2026-05-20T10:00:00Z","larch_version":"48.9.9","skill":"implement"}"#,
        ),
        SeedFile::text(
            "logs/implement/RUN-IMPL-1/review-findings-full.jsonl",
            concat!(
                r###"{"id":"FINDING_2","phase":"code-review","outcome":"accepted","reviewer_slots":["cursor-specialist-correctness-output.txt"],"round_num":"1","category":"Inverted guard skips required validation","prose_body":"## Inverted guard skips required validation\n- **Severity**: important\n- **Concern**: logic error: the check is inverted and the feature is broken."}"###,
                "\n",
                r###"{"id":"REJ_CR1_1","phase":"code-review","outcome":"rejected","reviewer_slots":["cursor-specialist-structure-output.txt"],"round_num":"1","category":"","body_severity":"nit","focus_area":"code-quality","prose_body":"## refactor: extract a helper for clarity\n- **Concern**: this would be cleaner as a refactor; more readable."}"###,
                "\n",
                r###"{"id":"OOS_CR1_1","phase":"code-review","outcome":"out_of_scope","reviewer_slots":["cursor-specialist-edge-cases-output.txt"],"round_num":"1","category":"","body_severity":"latent","prose_body":"## perf: avoid a redundant read\n- **Concern**: a micro-optimization could cache this."}"###,
                "\n",
                r#"{"id":"SKIP_1","phase":"retroactive-backfill","outcome":"accepted","round_num":"1","category":"Backfill row"}"#,
                "\n",
            ),
        ),
        SeedFile::text(
            "logs/implement/RUN-IMPL-BAD/manifest.json",
            r#"{"started_at":"2026-05-23T10:00:00Z","larch_version":"not-a-version","skill":"implement"}"#,
        ),
        SeedFile::text(
            "logs/implement/RUN-IMPL-BAD/review-findings-full.jsonl",
            concat!(
                r###"{"id":"FINDING_BAD","phase":"code-review","outcome":"accepted","reviewer_slots":["cursor-specialist-correctness-output.txt"],"round_num":"1","category":"Bad version run","body_severity":"important","prose_body":"## Bad version run"}"###,
                "\n",
            ),
        ),
        SeedFile::text(
            "logs/implement/RUN-IMPL-SELF/manifest.json",
            r#"{"started_at":"2026-05-26T10:00:00Z","larch_version":"49.0.0","skill":"implement"}"#,
        ),
        SeedFile::text(
            "logs/implement/RUN-IMPL-SELF/review-findings-full.jsonl",
            "",
        ),
        SeedFile::text(
            "logs/implement/RUN-IMPL-SELF/code-review-tally.json",
            r#"{"schema_version":2,"phase":"code-review","mode":"self-review","accepted_count":2,"rejected_count":1}"#,
        ),
        SeedFile::text(
            "logs/implement/RUN-IMPL-MALFORM/manifest.json",
            r#"{"started_at":"2026-05-27T10:00:00Z","larch_version":"49.0.0","skill":"implement"}"#,
        ),
        SeedFile::text(
            "logs/implement/RUN-IMPL-MALFORM/review-findings-full.jsonl",
            "{not json\n",
        ),
        SeedFile::text(
            "logs/implement/RUN-IMPL-MALFORM/code-review-tally.json",
            r#"{"schema_version":2,"phase":"code-review","mode":"self-review","accepted_count":5,"rejected_count":3}"#,
        ),
        SeedFile::text(
            "logs/implement/RUN-IMPL-FN/manifest.json",
            r#"{"started_at":"2026-05-28T10:00:00Z","larch_version":"49.0.0","skill":"implement"}"#,
        ),
        SeedFile::text(
            "logs/implement/RUN-IMPL-FN/round-1/review-findings-full.jsonl",
            concat!(
                r###"{"id":"REJ_CR1_4","phase":"code-review","outcome":"rejected","reviewer_slots":["cursor-validity"],"round_num":"1","category":"TSV neutral should win","body_severity":"important","prose_body":"## FINDING_4:\n- **Concern**: TSV links this mismatched JSONL id through the prose token."}"###,
                "\n",
                r###"{"id":"REJ_CR1_5","phase":"code-review","outcome":"rejected","reviewer_slots":["codex-pragmatism"],"round_num":"1","category":"Blocking reject","body_severity":"blocking","prose_body":"## FINDING_5:\n- **Concern**: This is truly blocking."}"###,
                "\n",
            ),
        ),
        SeedFile::text(
            "logs/implement/RUN-IMPL-FN/round-1/findings-classification.tsv",
            &format!(
                "{IMPL_HEADER_23}\n\
FINDING_4\tcursor-validity\tneutral\tYES\ttrue\tmajor\tgood\tfalse\tcursor-validity\tNO\ttrue\tnit\tweak\tfalse\tcodex-plan\tNO\ttrue\tnit\tweak\tfalse\tcodex-prag\t\t\n\
FINDING_5\tcodex-pragmatism\trejected\tYES\ttrue\tmajor\tgood\tfalse\tcursor-validity\tNO\ttrue\tnit\tweak\tfalse\tcodex-plan\tNO\ttrue\tnit\tweak\tfalse\tcodex-prag\tblocking\t\n\
OOS_CR1_6\tcursor-validity\tneutral\tYES\ttrue\tmajor\tgood\tfalse\tcursor-validity\tNO\ttrue\tnit\tweak\tfalse\tcodex-plan\tNO\ttrue\tnit\tweak\tfalse\tcodex-prag\timportant\t\n\
FINDING_7\tcursor-validity\tneutral\tYES\ttrue\tmajor\tgood\tfalse\tcursor-validity\tNO\ttrue\tnit\tweak\tfalse\tcodex-plan\tNO\ttrue\tnit\tweak\tfalse\tcodex-prag\timportant\toos\n\
FINDING_8\tcursor-validity\tout_of_scope\tYES\ttrue\tmajor\tgood\tfalse\tcursor-validity\tNO\ttrue\tnit\tweak\tfalse\tcodex-plan\tNO\ttrue\tnit\tweak\tfalse\tcodex-prag\timportant\t\n\
FINDING_10\tcursor-validity\texonerated\tYES\ttrue\tmajor\tgood\tfalse\tcursor-validity\tNO\ttrue\tnit\tweak\tfalse\tcodex-plan\tNO\ttrue\tnit\tweak\tfalse\tcodex-prag\timportant\t\n"
            ),
        ),
        SeedFile::text(
            "logs/implement/RUN-IMPL-TSV21/manifest.json",
            r#"{"started_at":"2026-05-25T10:00:00Z","larch_version":"49.0.0","skill":"implement"}"#,
        ),
        SeedFile::text(
            "logs/implement/RUN-IMPL-TSV21/review-findings-full.jsonl",
            concat!(
                r###"{"id":"FINDING_21","phase":"code-review","outcome":"accepted","reviewer_slots":["cursor-validity"],"round_num":"1","category":"Twenty-one column probe","prose_body":"## Twenty-one column probe"}"###,
                "\n",
            ),
        ),
        SeedFile::text(
            "logs/implement/RUN-IMPL-TSV21/round-1/findings-classification.tsv",
            &format!(
                "{IMPL_HEADER_21}\n\
FINDING_21\tcursor-validity\taccepted\tYES\ttrue\tmajor\tgood\tfalse\tcursor-validity\tNO\ttrue\tnit\tweak\tfalse\tcursor-plan-fidelity\tYES\ttrue\tminor\tadequate\tfalse\tcursor-pragmatism\n"
            ),
        ),
        SeedFile::text(
            "logs/implement/RUN-IMPL-MR/manifest.json",
            r#"{"started_at":"2026-05-29T10:00:00Z","larch_version":"49.1.0","skill":"implement"}"#,
        ),
        SeedFile::text(
            "logs/implement/RUN-IMPL-MR/review-findings-full.jsonl",
            concat!(
                r###"{"id":"FINDING_1","phase":"code-review","outcome":"accepted","reviewer_slots":["dyn-cursor-security"],"round_num":"1","category":"Round one accept","body_severity":"major","prose_body":"## Round one accept"}"###,
                "\n",
                r###"{"id":"FINDING_1","phase":"code-review","outcome":"rejected","reviewer_slots":["codex-generalist"],"round_num":"2","category":"Round two reject","body_severity":"trivial","prose_body":"## Round two reject"}"###,
                "\n",
            ),
        ),
        SeedFile::text(
            "logs/implement/RUN-IMPL-MR/round-1/findings-classification.tsv",
            &format!(
                "{COMPACT_HEADER_18}\n\
FINDING_1\tdyn-cursor-security\taccepted\tYES\ttrue\tmajor\tgood\tfalse\tYES\ttrue\timportant\tgood\tfalse\tNO\ttrue\tnit\tweak\tfalse\n"
            ),
        ),
        SeedFile::text(
            "logs/implement/RUN-IMPL-MR/round-2/findings-classification.tsv",
            &format!(
                "{COMPACT_HEADER_18}\n\
FINDING_1\tcodex-generalist\trejected\tNO\ttrue\tnit\tweak\tfalse\tNO\ttrue\tnit\tweak\tfalse\tNO\ttrue\tnit\tweak\tfalse\n"
            ),
        ),
        SeedFile::text(
            "logs/design/RUN-DSGN-1/manifest.json",
            r#"{"started_at":"2026-05-21T10:00:00Z","larch_version":"49.0.0"}"#,
        ),
        SeedFile::text(
            "logs/design/RUN-DSGN-1/architectural-guideline-assessment.md",
            "Deviation approved for the final plan.\n",
        ),
        SeedFile::text(
            "logs/design/RUN-DSGN-1/plan-review/round-1/findings.md",
            "### FINDING_1:\n\
- **Reviewer(s)**: Cursor-Arch\n\
- **Severity**: important\n\
- **Focus area**: correctness\n\
- **Concern**: Plan omits a required file; the feature is incomplete without it.\n\
\n\
### FINDING_2:\n\
- **Reviewer(s)**: Codex-Pragmatic\n\
- **Severity**: important\n\
- **Focus area**: code-quality\n\
- **Concern**: A rename would be cleaner here.\n",
        ),
        SeedFile::text(
            "logs/design/RUN-DSGN-1/plan-review/round-1/findings-classification.tsv",
            &format!(
                "{DESIGN_HEADER_22}\tscope\n\
FINDING_1\tCursor-Arch\taccepted\tYES\ttrue\tmajor\tgood\tfalse\tClaude\tYES\ttrue\tmajor\tgood\tfalse\tCodex\tYES\ttrue\tmajor\tgood\tfalse\tCursor\timportant\t\n\
FINDING_2\tCodex-Pragmatic\trejected\tNO\ttrue\tnit\tadequate\tfalse\tClaude\tNO\ttrue\tnit\tadequate\tfalse\tCodex\tNO\ttrue\tnit\tadequate\tfalse\tCursor\tnit\t\n\
FINDING_3\tCodex-FN\tneutral\tYES\ttrue\tmajor\tgood\tfalse\tClaude\tNO\ttrue\tnit\tadequate\tfalse\tCodex\tNO\ttrue\tnit\tadequate\tfalse\tCursor\timportant\t\n\
FINDING_4\tCodex-FN\trejected\tYES\ttrue\tmajor\tgood\tfalse\tClaude\tNO\ttrue\tnit\tadequate\tfalse\tCodex\tNO\ttrue\tnit\tadequate\tfalse\tCursor\tblocker\t\n\
FINDING_5\tCodex-FN\tneutral\tYES\ttrue\tmajor\tgood\tfalse\tClaude\tNO\ttrue\tnit\tadequate\tfalse\tCodex\tNO\ttrue\tnit\tadequate\tfalse\tCursor\timportant\toos\n\
FINDING_6\tCodex-FN\tout_of_scope\tYES\ttrue\tmajor\tgood\tfalse\tClaude\tNO\ttrue\tnit\tadequate\tfalse\tCodex\tNO\ttrue\tnit\tadequate\tfalse\tCursor\timportant\t\n"
            ),
        ),
        SeedFile::text(
            "logs/design/RUN-DSGN-2/manifest.json",
            r#"{"started_at":"2026-05-22T10:00:00Z","larch_version":"49.0.0"}"#,
        ),
        SeedFile::text(
            "logs/design/RUN-DSGN-2/plan-review/round-1/findings-classification.tsv",
            &format!(
                "{DESIGN_HEADER_22}\n\
FINDING_9\tCodex-Concise\taccepted\tYES\ttrue\tminor\tgood\tfalse\tClaude\tYES\ttrue\tminor\tgood\tfalse\tCodex\tYES\ttrue\tminor\tgood\tfalse\tCursor\tlatent\n"
            ),
        ),
        SeedFile::text(
            "logs/design/RUN-DSGN-EMPTY/manifest.json",
            r#"{"started_at":"2026-05-22T12:00:00Z","larch_version":"49.0.0"}"#,
        ),
        SeedFile::text(
            "logs/design/RUN-DSGN-EMPTY/architectural-guideline-assessment.md",
            " \n",
        ),
        SeedFile::text(
            "logs/design/RUN-DSGN-EMPTY/architectural-invariant-assessment.md",
            "Violation: something bad.\n",
        ),
        SeedFile::text(
            "logs/design/RUN-DSGN-ASSESS/manifest.json",
            r#"{"started_at":"2026-05-23T10:00:00Z","larch_version":"49.0.0"}"#,
        ),
        SeedFile::text(
            "logs/design/RUN-DSGN-ASSESS/architectural-guideline-assessment.md",
            "Consulted ARCHITECTURAL_GUIDELINES.md; no deviations identified.\n",
        ),
        SeedFile::text(
            "logs/design/RUN-DSGN-ASSESS/architectural-invariant-assessment.md",
            "Consulted ARCHITECTURAL_INVARIANTS.md; no violations identified.\n",
        ),
        // Non-canonical nested layout still reaches design discovery.
        SeedFile::text(
            "logs/design/RUN-NESTED/manifest.json",
            r#"{"started_at":"2026-05-21T00:00:00Z","larch_version":"49.0.0"}"#,
        ),
        SeedFile::text(
            "logs/design/RUN-NESTED/extra/round-1/findings-classification.tsv",
            "finding_id\tvoting_result\nFINDING_1\taccepted\n",
        ),
    ];
    seeds.extend(outcome_seeds());
    seeds
}

fn outcome_seeds() -> Vec<SeedFile> {
    let mut seeds = Vec::new();
    for (run, started, version) in [
        ("RUN-OUTCOME-PINNED", "2026-05-24T10:00:00Z", "52.4.16"),
        ("RUN-OUTCOME-CLEAN", "2026-05-24T11:00:00Z", "52.4.16"),
        ("RUN-OUTCOME-DROPPED", "2026-05-24T12:00:00Z", "52.4.16"),
        (
            "RUN-OUTCOME-MISSING_CURRENT",
            "2026-05-24T13:00:00Z",
            "52.4.16",
        ),
        (
            "RUN-OUTCOME-MISSING_LEGACY",
            "2026-05-24T14:00:00Z",
            "52.4.15",
        ),
        (
            "RUN-OUTCOME-MALFORMED_CURRENT",
            "2026-05-24T15:00:00Z",
            "52.4.16",
        ),
    ] {
        seeds.push(SeedFile::text(
            &format!("logs/implement/{run}/manifest.json"),
            &format!(
                r#"{{"started_at":"{started}","larch_version":"{version}","steps_ran":{{"step8":true}}}}"#
            ),
        ));
        seeds.push(SeedFile::text(
            &format!("logs/implement/{run}/final-summary.md"),
            "summary\n",
        ));
    }
    for (run, body) in [
        (
            "RUN-OUTCOME-PINNED",
            r#"{"schema_version":"1","phase":"implement","step":"8","outcome":"pinned","reason":"note-pinned","detail":"","guidelines_status":"present","head_sha":"abc123","base_ref":"origin/main","assessment_kind":"deviation"}"#,
        ),
        (
            "RUN-OUTCOME-CLEAN",
            r#"{"schema_version":"1","phase":"implement","step":"8","outcome":"clean","reason":"guidelines-absent","detail":"","guidelines_status":"absent","head_sha":"abc123","base_ref":"origin/main","assessment_kind":""}"#,
        ),
        (
            "RUN-OUTCOME-DROPPED",
            r#"{"schema_version":"1","phase":"implement","step":"8","outcome":"dropped","reason":"note-redaction-failed","detail":"","guidelines_status":"present","head_sha":"abc123","base_ref":"origin/main","assessment_kind":""}"#,
        ),
        (
            "RUN-OUTCOME-MALFORMED_CURRENT",
            r#"{"schema_version":"1","phase":"implement","step":"8","outcome":"pinned","reason":"bogus","detail":"","guidelines_status":"present","base_ref":"origin/main","assessment_kind":"deviation"}"#,
        ),
    ] {
        seeds.push(SeedFile::text(
            &format!("logs/implement/{run}/architectural-guideline-outcome.json"),
            body,
        ));
    }
    for (run, body) in [
        (
            "RUN-OUTCOME-PINNED",
            r#"{"schema_version":"1","phase":"implement","step":"8","outcome":"violation","reason":"violation-note","detail":"","invariants_status":"present","head_sha":"abc123","base_ref":"origin/main","assessment_kind":"violation"}"#,
        ),
        (
            "RUN-OUTCOME-CLEAN",
            r#"{"schema_version":"1","phase":"implement","step":"8","outcome":"clean","reason":"invariants-empty","detail":"","invariants_status":"present","head_sha":"abc123","base_ref":"origin/main","assessment_kind":"clean"}"#,
        ),
        (
            "RUN-OUTCOME-DROPPED",
            r#"{"schema_version":"1","phase":"implement","step":"8","outcome":"dropped","reason":"unavailable","detail":"","invariants_status":"present","head_sha":"abc123","base_ref":"origin/main","assessment_kind":""}"#,
        ),
    ] {
        seeds.push(SeedFile::text(
            &format!("logs/implement/{run}/architectural-invariant-outcome.json"),
            body,
        ));
    }
    seeds
}

fn session_seeds() -> Vec<SeedFile> {
    vec![
        SeedFile::text(
            "sessions/claude-design-abc123/voting-tally.md",
            "| finding | votes | result |\n\
| FINDING_1 | 3 | accepted |\n\
| FINDING_2 | 0 | rejected |\n\
| OOS_CR1_9 | 1 | out_of_scope |\n",
        ),
        SeedFile::text(
            "sessions/claude-design-abc123/findings.md",
            "### FINDING_1: In-progress concern\n\
- **Reviewer(s)**: dyn-cursor-arch\n\
- **Severity**: major\n\
- **Concern**: The plan is missing a required migration step.\n\
- **Proposed resolution**: add the step.\n\
\n\
### FINDING_2:\n\
- **Reviewer(s)**: codex-prag\n\
- **Severity**: nit\n\
- **Concern**: a rename would be cleaner.\n",
        ),
        SeedFile::text("sessions/claude-design-stale/voting-tally.md", ""),
    ]
}

fn recorded_case(
    name: &'static str,
    arguments: &[&str],
    seeds: Vec<SeedFile>,
    _fixture_directory: &Path,
) -> RecordedCase {
    RecordedCase {
        name,
        program: Program::new(env!("CARGO_BIN_EXE_larch"))
            .args(
                ["fluff-analysis", "analyze"]
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

/// Assert the recorded golden proves a real success-path report, so an
/// accidentally recorded failure cannot pass silently.
fn assert_success_report(golden_path: &Path, channel: &str) {
    let golden: serde_json::Value =
        serde_json::from_str(&fs::read_to_string(golden_path).expect("read fluff-analysis golden"))
            .expect("parse fluff-analysis golden");
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
        text.starts_with(REPORT_HEADER),
        "success case must render a report in {channel}: {}",
        golden_path.display()
    );
}

#[test]
#[allow(clippy::too_many_lines)] // The complete case matrix stays contiguous for recorded contract review.
fn fluff_analysis_analyze_preserves_recorded_black_box_contract() {
    let fixtures = fixture_directory();
    let corpus = corpus_seeds();
    let mut corpus_and_sessions = corpus.clone();
    corpus_and_sessions.extend(session_seeds());
    let success_cases: &[&str] = &[
        "fluff-analysis-corpus",
        "fluff-analysis-corpus-cutoff",
        "fluff-analysis-corpus-since-version",
        "fluff-analysis-corpus-post-only-tags",
        "fluff-analysis-corpus-default-min-group",
        "fluff-analysis-invalid-cutoff-warns",
        "fluff-analysis-empty",
        "fluff-analysis-in-progress",
        "fluff-analysis-in-progress-since",
    ];
    let cases = [
        recorded_case("fluff-analysis-help", &["--help"], Vec::new(), &fixtures),
        recorded_case(
            "fluff-analysis-unknown",
            &["--unknown"],
            Vec::new(),
            &fixtures,
        ),
        recorded_case(
            "fluff-analysis-missing-value",
            &["--out"],
            Vec::new(),
            &fixtures,
        ),
        recorded_case(
            "fluff-analysis-invalid-since-version",
            &["--since-version", "nope"],
            Vec::new(),
            &fixtures,
        ),
        recorded_case(
            "fluff-analysis-invalid-min-group",
            &["--min-group", "x"],
            Vec::new(),
            &fixtures,
        ),
        recorded_case(
            "fluff-analysis-missing-root",
            &["--log-root", "{sandbox}/missing"],
            Vec::new(),
            &fixtures,
        ),
        recorded_case("fluff-analysis-default-no-repo", &[], Vec::new(), &fixtures),
        recorded_case(
            "fluff-analysis-empty",
            &["--log-root", "{sandbox}/empty", "--min-group", "1"],
            vec![SeedFile::text("empty/.keep", "")],
            &fixtures,
        ),
        recorded_case(
            "fluff-analysis-corpus",
            &["--log-root", "{sandbox}/logs", "--min-group", "1"],
            corpus.clone(),
            &fixtures,
        ),
        recorded_case(
            "fluff-analysis-corpus-cutoff",
            &[
                "--log-root",
                "{sandbox}/logs",
                "--min-group",
                "1",
                "--cutoff",
                "2026-05-22T00:00:00Z",
            ],
            corpus.clone(),
            &fixtures,
        ),
        recorded_case(
            "fluff-analysis-corpus-since-version",
            &[
                "--log-root",
                "{sandbox}/logs",
                "--min-group",
                "1",
                "--since-version",
                "49.0.0",
            ],
            corpus.clone(),
            &fixtures,
        ),
        recorded_case(
            "fluff-analysis-corpus-post-only-tags",
            &[
                "--log-root",
                "{sandbox}/logs",
                "--min-group",
                "1",
                "--since-version",
                "49.0.0",
                "--post-only-tags",
            ],
            corpus.clone(),
            &fixtures,
        ),
        recorded_case(
            "fluff-analysis-corpus-default-min-group",
            &["--log-root", "{sandbox}/logs"],
            corpus.clone(),
            &fixtures,
        ),
        recorded_case(
            "fluff-analysis-invalid-cutoff-warns",
            &[
                "--log-root",
                "{sandbox}/logs",
                "--min-group",
                "1",
                "--cutoff",
                "not a time",
            ],
            corpus.clone(),
            &fixtures,
        ),
        recorded_case(
            "fluff-analysis-corpus-out",
            &[
                "--log-root",
                "{sandbox}/logs",
                "--min-group",
                "1",
                "--out",
                "{sandbox}/report.md",
            ],
            corpus,
            &fixtures,
        ),
        recorded_case(
            "fluff-analysis-in-progress",
            &[
                "--log-root",
                "{sandbox}/logs",
                "--min-group",
                "1",
                "--include-in-progress",
                "--sessions-dir",
                "{sandbox}/sessions",
                "--cutoff",
                "2026-05-22T00:00:00Z",
            ],
            corpus_and_sessions.clone(),
            &fixtures,
        ),
        recorded_case(
            "fluff-analysis-in-progress-since",
            &[
                "--log-root",
                "{sandbox}/logs",
                "--min-group",
                "1",
                "--include-in-progress",
                "--sessions-dir",
                "{sandbox}/sessions",
                "--inprogress-since",
                "2020-01-01T00:00:00Z",
            ],
            corpus_and_sessions,
            &fixtures,
        ),
    ];
    let goldens = fixtures.join("goldens");
    for case in cases {
        let golden = goldens.join(format!("{}.golden.json", case.name));
        assert_recorded_case(&case, &golden).unwrap_or_else(|error| panic!("{error}"));
        if success_cases.contains(&case.name) {
            assert_success_report(&golden, "stdout");
        }
        if case.name == "fluff-analysis-corpus-out" {
            assert_success_report(&golden, "report.md");
        }
    }
}
