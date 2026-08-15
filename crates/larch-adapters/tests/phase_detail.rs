//! Public-contract coverage for review phase metadata and rendering.

use std::{fs, path::Path};

use larch_adapters::phase_detail::{
    PhaseSkill, RenderRequest, render_phase_detail, review_tally_summary_counts,
    write_design_round_meta, write_implement_round_meta, write_render_output,
};

fn write(path: &Path, text: &str) {
    fs::write(path, text).expect("write fixture artifact");
}

fn setup_implement_round(implement: &Path) {
    write(
        &implement.join("voting-tally.md"),
        concat!(
            "# Code Review Voting Tally\n\n",
            "## Findings\n\n",
            "| Item | YES | NO | JERR | Result |\n",
            "|---|---:|---:|---:|---|\n",
            "| FINDING_1 | 2 | 1 | 0 | accepted |\n",
            "| FINDING_2 | 0 | 3 | 0 | rejected |\n",
            "| FINDING_3 | 1 | 1 | 1 | neutral |\n",
            "| OOS_1 | 2 | 1 | 0 | accepted |\n",
            "| OOS_2 | 0 | 3 | 0 | rejected |\n\n",
            "## Voter Agreement Scoreboard\n",
        ),
    );
    write(
        &implement.join("findings-classification.tsv"),
        concat!(
            "finding_id\tfinding_reviewers\tvoting_result\tv1_vote\tv1_severity\tv2_vote\tv2_severity\tv3_vote\tv3_severity\tscope\n",
            "FINDING_1\tcursor-specialist-correctness-output.txt\taccepted\tYES\tmajor\tYES\tmajor\tNO\tminor\tin_scope\n",
            "FINDING_2\tcodex-generalist-output.txt\trejected\tNO\tminor\tNO\tminor\tNO\tminor\tin_scope\n",
            "FINDING_3\tcursor-specialist-testing-output.txt\tneutral\tYES\tminor\tNO\tminor\tJUDGE_ERROR\t\tin_scope\n",
            "OOS_1\tcursor-specialist-security-output.txt\taccepted\tYES\tmajor\tYES\tmajor\tNO\tminor\toos\n",
            "OOS_2\tcodex-generalist-output.txt\trejected\tNO\tminor\tNO\tminor\tNO\tminor\toos\n",
        ),
    );
    write(
        &implement.join("oos.md"),
        concat!(
            "### OOS_1: public follow-up\n- **Concern**: file it\n\n",
            "### OOS_2: [SECURITY] private follow-up\n- **Concern**: do not publish\n",
        ),
    );
    write(
        &implement.join("review-tally.env"),
        "OOS_ACCEPTED_COUNT=1\nACCEPTED_COUNT=1\nREJECTED_COUNT=1\n",
    );
    write(
        &implement.join("panel-manifest.ndjson"),
        concat!(
            "{\"slot\":\"correctness\",\"tool\":\"cursor\",\"output\":\"cursor-specialist-correctness-output.txt\"}\n",
            "{\"slot\":\"generalist\",\"tool\":\"codex\",\"output\":\"codex-generalist-output.txt\"}\n",
            "{\"slot\":\"testing\",\"tool\":\"cursor\",\"output\":\"cursor-specialist-testing-output.txt\"}\n",
        ),
    );
    write(
        &implement.join("collector-results.env"),
        concat!(
            "TOOL=cursor\nSTATUS=TIMEOUT\nREVIEWER_FILE=cursor-specialist-testing-output.txt\n\n",
            "TOOL=codex\nSTATUS=OK\nREVIEWER_FILE=codex-generalist-output.txt\n",
        ),
    );
    write(
        &implement.join("review.output-files.dropped-slots"),
        "dyn-risk\tcodex\tstraggler-dropped\n",
    );
    write(
        &implement.join("difficulty-rating.json"),
        "{\"applied_tier\":\"HARD\",\"panel_tier\":\"HARD\",\"round_cap\":3,\"escalations\":[\"panel\"]}\n",
    );
    write(
        &implement.join("scout-difficulty-rating.raw.json"),
        "{\"predicted_tier\":\"MODERATE\",\"confidence\":\"low\",\"rationale\":\"Concrete scope\"}\n",
    );
}

fn setup_design_round(design: &Path) {
    write(
        &design.join("voting-tally.md"),
        concat!(
            "## Findings\n",
            "| Item | YES | NO | JERR | Result |\n",
            "|---|---:|---:|---:|---|\n",
            "| FINDING_1 | 2 | 1 | 0 | accepted |\n",
            "| OOS_1 | 2 | 1 | 0 | accepted |\n",
        ),
    );
    write(
        &design.join("findings-oos.md"),
        "### OOS_1: [SECURITY] design follow-up\n- **Concern**: private\n",
    );
    write(
        &design.join("plan-review-slots.ndjson"),
        concat!(
            "{\"slot\":\"plan-fidelity\",\"tool\":\"codex\",\"output\":\"codex-plan-fidelity-output.txt\",\"focus_area\":\"architecture\"}\n",
            "{\"slot\":\"testing\",\"tool\":\"cursor\",\"output\":\"cursor-testing-output.txt\"}\n",
        ),
    );
    write(
        &design.join("round-summary.env"),
        "COLLECT_FAILURE_COUNT=1\n",
    );
    write(
        &design.join("collector-results.env"),
        "TOOL=cursor\nSTATUS=FAILED\nREVIEWER_FILE=cursor-testing-output.txt\n",
    );
    fs::create_dir_all(design.join("revise")).expect("create revision directory");
    write(
        &design.join("revise/revise.env"),
        "REVISE_STATUS=done\nREVISE_TIER=1\n",
    );
}

#[test]
fn implement_round_metadata_preserves_tally_panel_and_security_artifacts() {
    let temporary = tempfile::tempdir().expect("temporary directory");
    let implement = temporary.path().join("round-1");
    fs::create_dir_all(&implement).expect("implement round directory");
    setup_implement_round(&implement);

    assert_eq!(
        review_tally_summary_counts(&implement.join("voting-tally.md")),
        (1, 1, 1)
    );
    assert!(write_implement_round_meta(&implement).expect("write implement metadata"));
    let metadata =
        fs::read_to_string(implement.join("round-meta.json")).expect("read implement metadata");
    assert!(metadata.contains("\"ACCEPTED_COUNT\": \"1\""));
    assert!(metadata.contains("\"OOS_ACCEPTED_COUNT\": \"1\""));
    assert!(metadata.contains("\"tally_canonical\""));
    assert!(metadata.contains("\"total_slot_count\": 3"));
}

#[test]
fn design_round_metadata_excludes_uppercase_security_oos() {
    let temporary = tempfile::tempdir().expect("temporary directory");
    let design = temporary.path().join("round-1");
    fs::create_dir_all(&design).expect("design round directory");
    setup_design_round(&design);

    assert!(write_design_round_meta(&design).expect("write design metadata"));
    let metadata =
        fs::read_to_string(design.join("round-meta.json")).expect("read design metadata");
    assert!(metadata.contains("\"OOS_ACCEPTED_COUNT\": \"0\""));
    assert!(metadata.contains("cursor-testing-output.txt"));
    assert!(metadata.contains("\"revise\""));
    assert!(design.join("panel-manifest.ndjson").is_file());
}

#[test]
fn renderer_preserves_tally_timing_and_panel_artifacts() {
    let temporary = tempfile::tempdir().expect("temporary directory");
    let rounds = temporary.path().join("rounds");
    let implement = rounds.join("round-1");
    let design = rounds.join("round-2");
    fs::create_dir_all(&implement).expect("implement round directory");
    fs::create_dir_all(&design).expect("design round directory");
    setup_implement_round(&implement);
    setup_design_round(&design);
    assert!(write_implement_round_meta(&implement).expect("write implement metadata"));
    assert!(write_design_round_meta(&design).expect("write design metadata"));

    let timing = temporary.path().join("timing.tsv");
    write(
        &timing,
        concat!(
            "v1\tround\t-\timplement\t-\t1\t100\t220\t-\t-\t-\t-\t1\n",
            "v1\tround\t-\timplement\t-\t1\t230\t260\t-\t-\t-\t-\t2\n",
            "v1\tvendor\t-\t-\t-\tcursor\treview\t120\t180\t-\tcursor-specialist-correctness-output.txt\t-\tcomplete\n",
            "v1\tvendor\t-\t-\t-\tcodex\treview\t240\t250\t-\tcodex-generalist-output.txt\t-\tcomplete\n",
        ),
    );
    let tokens = temporary.path().join("tokens.jsonl");
    write(
        &tokens,
        concat!(
            "{\"type\":\"vendor\",\"ts\":\"1970-01-01T00:02:30Z\",\"vendor\":\"codex\",\"model\":\"gpt-5.4\",\"raw\":\"\",\"input\":1000,\"cache_read\":10,\"cache_create\":0,\"output\":20}\n",
            "{\"type\":\"vendor\",\"ts\":\"1970-01-01T00:04:05Z\",\"vendor\":\"cursor\",\"model\":\"\",\"raw\":\"\",\"input\":1000,\"cache_read\":0,\"cache_create\":0,\"output\":20}\n",
        ),
    );
    let report = render_phase_detail(&RenderRequest {
        rounds_root: &rounds,
        skill: PhaseSkill::Implement,
        timing_ledger: Some(&timing),
        token_ledger: Some(&tokens),
        findings_file: None,
        top_n: 2,
        gantt_enabled: true,
    });
    assert!(report.contains("| 1 | 3 | 1 | 1 | 1 | 2m 40s | $"));
    assert!(report.contains("**Top reviewers**"));
    assert!(report.contains("cursor-specialist-correctness-output.txt: 2"));
    assert!(report.contains("**Reviewer slot failures**: 3"));
    assert!(report.contains("### Round 1 reviewer timing (attempt 1)"));
    assert!(report.contains("### Round 1 reviewer timing (attempt 2)"));

    let output = temporary.path().join("phase-detail.md");
    write_render_output(&output, &report).expect("publish rendered report");
    assert_eq!(
        fs::read_to_string(output).expect("read published report"),
        report
    );
}
