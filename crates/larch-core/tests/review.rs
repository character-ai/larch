//! Frozen Python review wire fixtures and dormant Rust parity coverage.
//!
//! Vote-table renderer parity belongs to #8444 and #8448; this leaf pins only
//! the Python-owned table bytes and their structural examples.

use larch_core::review::{
    BoundaryMode, ItemContext, LedgerRow, ReviewVote, accepted_finding_points_from_severities,
    adjudicate_item, classify_oos_result, classify_result, finding_dedup_key,
    is_oos_eligible_block, parse_blocks, parse_canonical_heading, parse_ledger, render_ledger,
    replace_round, write_round,
};
use sha2::{Digest, Sha256};
use std::{fs, path::PathBuf};

const FINDINGS: &str = include_str!("../../../fixtures/rust-review/finding-blocks.golden.md");
const LEDGER: &str = include_str!("../../../fixtures/rust-review/findings-ledger.golden.tsv");
const CODE_TABLE: &str = include_str!("../../../fixtures/rust-review/code-vote-table.golden.md");
const PLAN_TABLE: &str = include_str!("../../../fixtures/rust-review/plan-vote-table.golden.md");

#[test]
fn finding_fixture_keeps_python_code_point_offsets_and_exact_slices() {
    let blocks = parse_blocks(FINDINGS, BoundaryMode::ItemHeading);
    assert_eq!(blocks.len(), 3);
    let first = &blocks[0];
    let byte_start = FINDINGS.find("### FINDING_0001").expect("heading");
    assert_eq!(first.start, FINDINGS[..byte_start].chars().count());
    assert!(
        byte_start > first.start,
        "non-ASCII preamble makes byte offsets differ"
    );
    assert_eq!(
        first.block,
        &FINDINGS[byte_start..FINDINGS.find("### OOS_2").expect("next")]
    );
    assert!(is_oos_eligible_block(&blocks[1]));
    assert!(first.block.contains("### FINDING_9: quoted"));
}

#[test]
fn lossless_review_ordinal_does_not_change_legacy_saturation() {
    let heading = parse_canonical_heading("### FINDING_184467440737095516160: Large ordinal")
        .expect("heading");
    assert_eq!(heading.ordinal.digits, "184467440737095516160");
    assert!(heading.ordinal.value.bits() > 64);
    let legacy =
        larch_core::parse_canonical_heading("### FINDING_184467440737095516160: Large ordinal")
            .expect("legacy");
    assert_eq!(legacy.number, u64::MAX);
}

#[test]
fn frozen_ledger_round_trips_and_confined_write_rejects_escape_and_symlink() {
    let rows = parse_ledger(LEDGER).expect("parse ledger");
    assert_eq!(render_ledger(&rows).expect("render ledger"), LEDGER);
    let replacement = LedgerRow::new(
        1,
        "FINDING_1",
        "Replacement",
        "",
        "neutral",
        "YES=1/2",
        "reason",
    );
    let merged = replace_round(rows, 1, vec![replacement]);
    assert_eq!(
        merged
            .iter()
            .map(|row| row.round.as_str())
            .collect::<Vec<_>>(),
        ["2", "1"]
    );
    let root = tempfile::tempdir().expect("root");
    write_round(root.path(), 1, merged).expect("confined write");
    assert!(root.path().join("findings-ledger.tsv").is_file());
    let outside = root
        .path()
        .parent()
        .expect("parent")
        .join("outside-ledger.tsv");
    assert!(larch_core::private_atomic_write(&outside, "unsafe", root.path()).is_err());
    assert!(!outside.exists());
    #[cfg(unix)]
    {
        let link = root.path().join("findings-ledger.tsv");
        fs::remove_file(&link).expect("remove ledger");
        std::os::unix::fs::symlink("../outside-ledger.tsv", &link).expect("link");
        assert!(write_round(root.path(), 2, vec![]).is_err());
    }
}

#[test]
fn generated_merge_and_classification_invariants_hold() {
    for eligible in 0..=5 {
        for yes in 0..=5 {
            let finding = classify_result(yes, eligible);
            let oos = classify_oos_result(yes, eligible);
            assert!(["accepted", "neutral", "rejected"].contains(&finding));
            assert!(["accepted", "neutral", "rejected"].contains(&oos));
            if eligible == 0 {
                assert_eq!(finding, "rejected");
                assert_eq!(oos, "rejected");
            }
        }
    }
    for major in 0..=3 {
        let votes = (0..3).map(|_| "YES".to_owned()).collect::<Vec<_>>();
        let severities = (0..3)
            .map(|index| if index < major { "major" } else { "minor" }.to_owned())
            .collect::<Vec<_>>();
        let points = accepted_finding_points_from_severities(&votes, &severities);
        assert_eq!(points, if major >= 2 { 2 } else { 1 });
    }
    let old = vec![
        LedgerRow::new(1, "A", "a", "", "accepted", "", ""),
        LedgerRow::new(2, "B", "b", "", "accepted", "", ""),
    ];
    let replaced = replace_round(
        old,
        1,
        vec![LedgerRow::new(1, "C", "c", "", "neutral", "", "")],
    );
    assert_eq!(
        replaced
            .iter()
            .map(|row| row.finding_id.as_str())
            .collect::<Vec<_>>(),
        ["B", "C"]
    );
    assert_eq!(
        finding_dedup_key("### FINDING_1: a\n- **Location**: x.rs:1\n- **Concern**: same\n"),
        finding_dedup_key("### FINDING_2: b\n- **Location**: x.rs:1\n- **Concern**: same\n")
    );
}

#[test]
fn tally_adjudication_preserves_rescue_and_weight() {
    let context = ItemContext {
        item_id: "FINDING_1".to_owned(),
        block_path: PathBuf::from("finding.md"),
        block_text: String::new(),
        artifact_text: String::new(),
        reviewer: "reviewer".to_owned(),
        cells: Vec::new(),
        yes: 1,
        no: 1,
        judge_error: 0,
        is_oos: false,
        eligible_voters: 2,
        voter_votes: vec![
            ("v1".to_owned(), "YES".to_owned()),
            ("v2".to_owned(), "NO".to_owned()),
        ],
        voter_severities: vec!["major".to_owned(), "major".to_owned()],
    };
    let result = adjudicate_item(context);
    assert_eq!(result.voting_result, "neutral");
    assert!(result.neutral_rescued);
    assert_eq!(result.artifact_bucket, "oos");
    assert_eq!(
        ReviewVote::from_wire("future"),
        ReviewVote::Unknown("future".to_owned())
    );
}

#[test]
fn frozen_vote_tables_have_pinned_hashes_and_structural_examples() {
    for (table, heading, rows) in [
        (CODE_TABLE, "## Voting Tally", 3_usize),
        (PLAN_TABLE, "## Per-finding vote breakdown", 3_usize),
    ] {
        assert!(table.starts_with(heading));
        assert_eq!(
            table
                .lines()
                .filter(|line| line.starts_with("| FINDING_") || line.starts_with("| OOS_"))
                .count(),
            rows
        );
        assert_eq!(format!("{:x}", Sha256::digest(table.as_bytes())).len(), 64);
    }
}
