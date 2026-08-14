//! Frozen Python review wire fixtures and Rust review-contract coverage.
//!
//! Vote-table renderer parity belongs to #8444 and #8448; this leaf pins only
//! the Python-owned table bytes and their structural examples.

use larch_core::review::{
    BoundaryMode, ItemContext, LedgerRow, ReviewCoreStatus, ReviewVote,
    accepted_finding_points_from_severities, adjudicate_item, classify_oos_result, classify_result,
    code_review_classification_required_fields, finding_dedup_key, is_oos_eligible_block,
    parse_blocks, parse_canonical_heading, parse_ledger, render_ledger, render_wire_values,
    replace_round, run_items, write_round,
};
use sha2::{Digest, Sha256};
use std::{
    cell::RefCell,
    collections::{BTreeMap, BTreeSet},
    fs,
    path::PathBuf,
};

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
fn review_wire_values_are_lossless_and_project_required_headers() {
    assert_eq!(
        ReviewCoreStatus::from_wire("cap-reached").as_str(),
        "cap-reached"
    );
    assert_eq!(
        ReviewCoreStatus::from_wire("future-status").as_str(),
        "future-status"
    );
    assert_eq!(ReviewVote::from_wire("future-vote").as_str(), "future-vote");
    let fields = code_review_classification_required_fields(true, true);
    assert!(fields.contains("v3_tool"));
    assert!(fields.contains("scope"));
    assert!(!code_review_classification_required_fields(false, false).contains("v1_tool"));
    assert_eq!(
        render_wire_values(&["one", "two"], "/", true),
        "`one` / `two`"
    );
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
fn ledger_persistence_normalizes_rows_and_creates_a_fresh_root() {
    let parent = tempfile::tempdir().expect("parent");
    let root = parent.path().join("new-ledger-root");
    let hostile = LedgerRow {
        round: "99".to_owned(),
        finding_id: "FINDING\t1".to_owned(),
        title: "```title sk-aaaaaaaaaaaaaaaaaaaaaaaaaa".to_owned(),
        file_line: "src/lib.rs\n12".to_owned(),
        outcome: "UNSAFE".to_owned(),
        vote_tally: "=1/1".to_owned(),
        reason: "secret sk-aaaaaaaaaaaaaaaaaaaaaaaaaa".to_owned(),
    };
    write_round(&root, 4, vec![hostile]).expect("first write creates root");
    let text = fs::read_to_string(root.join("findings-ledger.tsv")).expect("ledger");
    assert!(text.contains("4\tFINDING 1\ttitle <REDACTED-TOKEN>"));
    assert!(text.contains("\trejected\t'=1/1\tsecret <REDACTED-TOKEN>\n"));
    assert!(!text.contains("sk-"));
    assert!(!text.contains("```"));
}

#[test]
fn ledger_root_requires_a_nonempty_numeric_round_suffix() {
    let root = tempfile::tempdir().expect("root");
    let session = root.path().join("session");
    let invalid = session.join("round-");
    fs::create_dir_all(&invalid).expect("invalid round dir");
    assert_eq!(
        larch_core::review::ledger_root(&invalid, Some(&session.join("session.env")), None),
        invalid
    );
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
fn seeded_generated_review_invariants_hold() {
    let mut state = 0x5eed_u64;
    for _ in 0..512 {
        state = state
            .wrapping_mul(6_364_136_223_846_793_005)
            .wrapping_add(1);
        let eligible = (state % 6) as usize;
        let yes = ((state >> 16) % 7) as usize;
        let result = classify_result(yes, eligible);
        assert!(matches!(result, "accepted" | "neutral" | "rejected"));
        let malformed =
            format!("### FINDING_1: x\n- **lOcAtIoN**: loc-{yes}\n- **CONCERN**: c-{eligible}\n");
        assert_eq!(
            finding_dedup_key(&malformed),
            format!("loc-{yes}\u{1f}c-{eligible}")
        );
        let row = LedgerRow::new(1, "FINDING_1", "a\tb", "", "accepted", "", "");
        assert!(
            render_ledger(&[row])
                .expect("render")
                .contains("FINDING_1\ta b\t")
        );
    }
}

#[test]
fn finding_dedup_key_without_fields_strips_finding_headers() {
    assert_eq!(
        finding_dedup_key("### FINDING_1: Title text\nbody stays\n"),
        finding_dedup_key("### FINDING_2: Other title\nbody stays\n")
    );
    assert_eq!(
        finding_dedup_key("### FINDING_1: Title text\nbody stays\n"),
        "body stays"
    );
}

#[test]
fn finding_dedup_key_preserves_first_empty_location_match() {
    let key = finding_dedup_key(
        "### FINDING_1: a\n- **Location**: \n- **Location**: later.rs:1\n- **Concern**: same\n",
    );
    assert_eq!(key, "\u{1f}same");
}

#[test]
fn replace_round_sets_replacement_row_round() {
    let merged = replace_round(
        vec![LedgerRow::new(2, "KEEP", "keep", "", "accepted", "", "")],
        3,
        vec![LedgerRow::new(9, "NEW", "new", "", "neutral", "", "")],
    );
    assert_eq!(merged[1].round, "3");
    assert_eq!(merged[1].finding_id, "NEW");
}

#[test]
fn non_fileable_accepted_oos_scores_neutral_with_zero_weight() {
    let context = ItemContext {
        item_id: "OOS_1".to_owned(),
        block_path: PathBuf::from("oos.md"),
        block_text: String::new(),
        artifact_text: String::new(),
        reviewer: "reviewer".to_owned(),
        cells: Vec::new(),
        yes: 2,
        no: 0,
        judge_error: 0,
        is_oos: true,
        eligible_voters: 2,
        voter_votes: vec![
            ("v1".to_owned(), "YES".to_owned()),
            ("v2".to_owned(), "YES".to_owned()),
        ],
        voter_severities: vec!["minor".to_owned(), "minor".to_owned()],
    };
    let result = adjudicate_item(context);
    assert_eq!(result.voting_result, "accepted");
    assert!(!result.fileable_oos);
    assert_eq!(result.score_result, "neutral");
    assert_eq!(result.accepted_weight, 0);
}

#[test]
fn fileable_accepted_oos_strict_majority_scores_accepted() {
    let context = ItemContext {
        item_id: "OOS_1".to_owned(),
        block_path: PathBuf::from("oos.md"),
        block_text: String::new(),
        artifact_text: String::new(),
        reviewer: "reviewer".to_owned(),
        cells: Vec::new(),
        yes: 2,
        no: 0,
        judge_error: 0,
        is_oos: true,
        eligible_voters: 2,
        voter_votes: vec![
            ("v1".to_owned(), "YES".to_owned()),
            ("v2".to_owned(), "YES".to_owned()),
        ],
        voter_severities: vec!["major".to_owned(), "major".to_owned()],
    };
    let result = adjudicate_item(context);
    assert!(result.fileable_oos);
    assert_eq!(result.score_result, "accepted");
}

#[test]
fn review_taxonomy_exports_match_python_wire_projections() {
    use larch_core::review::{
        CompatibilityBoundary, FINDING_SCOPE_VALUES, FOCUS_AREA_VALUES, FindingScope, FocusArea,
        ItemKind, finding_scope_set, focus_area_set, is_canonical_heading, parse_findings_text,
    };
    assert_eq!(
        FocusArea::all()
            .iter()
            .map(|area| area.as_str())
            .collect::<Vec<_>>(),
        FOCUS_AREA_VALUES
    );
    assert_eq!(focus_area_set().len(), FOCUS_AREA_VALUES.len());
    assert_eq!(
        [
            FindingScope::InScope.as_str(),
            FindingScope::OutOfScope.as_str()
        ],
        FINDING_SCOPE_VALUES
    );
    assert_eq!(finding_scope_set().len(), FINDING_SCOPE_VALUES.len());
    assert!(is_canonical_heading(
        "### OOS_2: title",
        Some(ItemKind::Oos)
    ));
    let findings = parse_findings_text(
        "### FINDING_1: f\nbody\n### Notes\nnotes\n### FINDING_2: g\nbody2\n",
        CompatibilityBoundary::AnyHeading,
    );
    assert_eq!(
        findings
            .iter()
            .map(|row| row.finding_id.as_str())
            .collect::<Vec<_>>(),
        ["FINDING_1", "FINDING_2"]
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

fn context(item_id: &str) -> ItemContext {
    ItemContext {
        item_id: item_id.to_owned(),
        block_path: PathBuf::from("finding.md"),
        block_text: String::new(),
        artifact_text: String::new(),
        reviewer: "reviewer".to_owned(),
        cells: Vec::new(),
        yes: 1,
        no: 0,
        judge_error: 0,
        is_oos: false,
        eligible_voters: 1,
        voter_votes: vec![("v1".to_owned(), "YES".to_owned())],
        voter_severities: vec!["major".to_owned()],
    }
}

#[test]
fn run_items_orders_hooks_and_stops_on_each_failure() {
    let calls = RefCell::new(Vec::new());
    let completed = run_items(
        [context("FINDING_1")],
        |_| {
            calls.borrow_mut().push("serialize");
            Ok::<_, &'static str>(())
        },
        |_| {
            calls.borrow_mut().push("security");
            Ok(true)
        },
        |_| {
            calls.borrow_mut().push("publish");
            Ok(())
        },
    )
    .expect("success");
    assert_eq!(calls.into_inner(), ["serialize", "security", "publish"]);
    assert_eq!(completed[0].security, Some(true));
    for (failure, expected) in [
        ("serialize", vec!["serialize"]),
        ("security", vec!["serialize", "security"]),
        ("publish", vec!["serialize", "security", "publish"]),
    ] {
        let calls = RefCell::new(Vec::new());
        let result = run_items(
            [context("FINDING_1"), context("FINDING_2")],
            |_| {
                calls.borrow_mut().push("serialize");
                if failure == "serialize" {
                    Err("stop")
                } else {
                    Ok(())
                }
            },
            |_| {
                calls.borrow_mut().push("security");
                if failure == "security" {
                    Err("stop")
                } else {
                    Ok(true)
                }
            },
            |_| {
                calls.borrow_mut().push("publish");
                if failure == "publish" {
                    Err("stop")
                } else {
                    Ok(())
                }
            },
        );
        assert_eq!(result, Err("stop"));
        assert_eq!(calls.into_inner(), expected);
    }
}

#[test]
fn parser_boundary_modes_cover_crlf_and_fences() {
    let text = "### FINDING_1: first\r\nbody\r\n```md\r\n### OOS_9: fenced\r\n```\r\n### OOS_2: second\r\nbody\r\n### Heading\r\nend\r\n";
    assert_eq!(parse_blocks(text, BoundaryMode::FindingHeading).len(), 2);
    assert_eq!(parse_blocks(text, BoundaryMode::OosHeading).len(), 2);
    let items = parse_blocks(text, BoundaryMode::ItemHeading);
    assert_eq!(items.len(), 2);
    assert!(items[0].block.contains("OOS_9: fenced"));
    assert_eq!(
        parse_blocks(text, BoundaryMode::LevelThreeHeading)[1].block,
        "### OOS_2: second\r\nbody\r\n"
    );
}

#[test]
fn pipeline_helpers_preserve_legacy_argument_and_record_edges() {
    use larch_core::review::{
        GatherContextArgumentError, GatherContextMode, GatherContextParse,
        description_path_matches, description_tokens, normalize_output_base,
        parse_collector_records, parse_gather_context_arguments, positive_integer,
        valid_relative_review_path,
    };

    let arguments = vec![
        "--mode".to_owned(),
        "diff".to_owned(),
        "--output-dir".to_owned(),
        "first".to_owned(),
        "--output-dir".to_owned(),
        "last".to_owned(),
    ];
    assert_eq!(
        parse_gather_context_arguments(&arguments),
        Ok(GatherContextParse::Arguments(
            larch_core::review::GatherContextArguments {
                mode: GatherContextMode::Diff,
                output_dir: "last".to_owned(),
                description_text: String::new(),
                scope_files: String::new(),
            }
        ))
    );
    assert_eq!(
        parse_gather_context_arguments(&["--unknown".to_owned()]),
        Err(GatherContextArgumentError::UnknownOption(
            "--unknown".to_owned()
        ))
    );
    assert_eq!(
        parse_gather_context_arguments(&["--mode".to_owned()]),
        Err(GatherContextArgumentError::MissingValue(
            "--mode".to_owned()
        ))
    );
    assert_eq!(
        parse_gather_context_arguments(&["--unknown".to_owned(), "--help".to_owned()]),
        Ok(GatherContextParse::Help)
    );
    assert_eq!(
        description_tokens("Alpha, beta /review-file and x"),
        ["alpha", "beta", "/review-file", "and"]
    );
    assert_eq!(
        description_path_matches(
            &["review".to_owned()],
            ["src/review.rs", "docs/review.md", "skip/review.md"],
            |path| !path.starts_with("skip/"),
        ),
        BTreeSet::from(["docs/review.md".to_owned(), "src/review.rs".to_owned()])
    );
    assert!(valid_relative_review_path("src/review.rs"));
    assert!(!valid_relative_review_path("../escape"));
    assert_eq!(
        parse_collector_records(
            "DIAGNOSTIC=ignored\nREVIEWER_FILE=a.md\nSTATUS=old\nSTATUS=new\n=kept\n\nREVIEWER_FILE=b.md\nSTATUS=only\n",
        ),
        vec![
            BTreeMap::from([
                (String::new(), "kept".to_owned()),
                ("REVIEWER_FILE".to_owned(), "a.md".to_owned()),
                ("STATUS".to_owned(), "new".to_owned()),
            ]),
            BTreeMap::from([
                ("REVIEWER_FILE".to_owned(), "b.md".to_owned()),
                ("STATUS".to_owned(), "only".to_owned()),
            ]),
        ]
    );
    assert_eq!(
        normalize_output_base("dir/agent-phase2-retry.txt"),
        "agent.txt"
    );
    assert_eq!(positive_integer("3"), Some(3));
    assert_eq!(positive_integer("0"), None);
}

#[test]
fn dispatch_helpers_preserve_fixed_slot_and_wire_contracts() {
    use larch_core::review::{
        DispatchError, VoterOutputBinding, VoterPathsFilePolicy, VoterRowLayout, VoterSlotPolicy,
        voter_states_from_bindings, voter_status_rows,
    };

    let policies = ["one", "two", "three"].map(|slot_name| VoterSlotPolicy {
        slot_name: slot_name.to_owned(),
        primary_tool: "codex".to_owned(),
        default_label: format!("default-{slot_name}"),
        semantic_labels: BTreeMap::from([("codex".to_owned(), format!("codex-{slot_name}"))]),
    });
    let states = voter_states_from_bindings(
        &policies,
        &BTreeMap::from([(
            "one".to_owned(),
            VoterOutputBinding {
                path: "one.txt".to_owned(),
                tool: "codex".to_owned(),
                dropped: false,
            },
        )]),
        &BTreeSet::from(["one".to_owned(), "two".to_owned()]),
        &BTreeMap::from([
            ("two".to_owned(), "two.txt".to_owned()),
            ("three".to_owned(), "three.txt".to_owned()),
        ]),
    )
    .expect("fixed voter slots");
    assert_eq!(states[0].status, "launched");
    assert_eq!(states[0].tool, "codex-one");
    assert_eq!(states[1].status, "failed");
    assert_eq!(states[1].path, "two.txt");
    assert_eq!(states[2].status, "skipped");
    assert_eq!(
        voter_states_from_bindings(
            &[
                policies[0].clone(),
                policies[1].clone(),
                policies[2].clone(),
                policies[0].clone(),
            ],
            &BTreeMap::new(),
            &BTreeSet::new(),
            &BTreeMap::new(),
        )
        .expect("legacy helper takes its fixed first three slots")
        .len(),
        3
    );
    assert_eq!(
        voter_states_from_bindings(
            &policies[..2],
            &BTreeMap::new(),
            &BTreeSet::new(),
            &BTreeMap::new()
        ),
        Err(DispatchError::VoterCount)
    );
    let rows = voter_status_rows(
        &states,
        "paths.txt",
        VoterRowLayout::PlanReviewInterleaved,
        VoterPathsFilePolicy::Nonempty,
        true,
    )
    .expect("fixed voter rows");
    assert_eq!(
        voter_status_rows(
            &states[..2],
            "",
            VoterRowLayout::CodeReviewSequential,
            VoterPathsFilePolicy::Always,
            false,
        ),
        Err(DispatchError::VoterRecordCount)
    );
    assert_eq!(
        rows.iter().map(|(key, _)| key.as_str()).collect::<Vec<_>>(),
        [
            "VOTER_1_PATH",
            "VOTER_1_TOOL",
            "VOTER_1_STATUS",
            "VOTER_1_PARSE_RATE_STATUS",
            "VOTER_2_PATH",
            "VOTER_3_PATH",
            "VOTER_PATHS_FILE",
            "VOTER_2_TOOL",
            "VOTER_3_TOOL",
            "VOTER_2_STATUS",
            "VOTER_3_STATUS",
            "VOTER_2_PARSE_RATE_STATUS",
            "VOTER_3_PARSE_RATE_STATUS",
        ]
    );
}

#[test]
fn dispatch_helpers_preserve_parse_rate_and_manifest_attribution() {
    use larch_core::review::{
        optional_positive_float, parse_rate_status, with_manifest_attribution,
    };
    use serde_json::{Map, Value};

    assert_eq!(optional_positive_float("", "timeout"), Ok(None));
    assert!(optional_positive_float("0", "timeout").is_err());
    assert_eq!(parse_rate_status(0, "warning\nOK\n"), "OK");
    assert_eq!(parse_rate_status(1, "OK\n"), "NOT_SUBSTANTIVE");
    let row = with_manifest_attribution(
        Map::from_iter([("tool".to_owned(), Value::String("codex".to_owned()))]),
        Some("vote"),
        "tier-model",
        &BTreeMap::new(),
    );
    assert_eq!(row["vendor"], "codex");
    assert_eq!(row["model_role"], "vote");
    assert_eq!(row["resolved_model"], "tier-model");
}

#[test]
fn frozen_vote_tables_have_pinned_hashes_and_structural_examples() {
    for (table, heading, rows, digest) in [
        (
            CODE_TABLE,
            "## Per-finding vote breakdown",
            3_usize,
            "b7a6652c9a70fb10bac1bc1b4187e559fc07b18a210cd0156a6cdc1a2e5c6f09",
        ),
        (
            PLAN_TABLE,
            "## Findings",
            3_usize,
            "a212d86daf7656861073bc45fa681b319deea113b38771b8be164def84c8a8b8",
        ),
    ] {
        assert!(table.starts_with(heading));
        assert_eq!(
            table
                .lines()
                .filter(|line| line.starts_with("| FINDING_") || line.starts_with("| OOS_"))
                .count(),
            rows
        );
        assert_eq!(format!("{:x}", Sha256::digest(table.as_bytes())), digest);
    }
}
