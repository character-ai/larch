//! Property tests for dormant review parity invariants.

use std::collections::HashSet;

use larch_core::review::{
    LedgerRow, accepted_finding_points_from_severities, classify_oos_result, classify_result,
    finding_dedup_key, neutral_high_severity_rescue_to_oos, oos_fileable_from_votes, parse_ledger,
    render_ledger, replace_round,
};
use proptest::prelude::*;

proptest! {
    #[test]
    fn classify_result_invariants(yes in 0usize..8, eligible in 0usize..8) {
        let result = classify_result(yes, eligible);
        prop_assert!(matches!(result, "accepted" | "neutral" | "rejected"));
        if eligible == 0 {
            prop_assert_eq!(result, "rejected");
        }
    }

    #[test]
    fn classify_oos_result_invariants(yes in 0usize..8, eligible in 0usize..8) {
        let result = classify_oos_result(yes, eligible);
        prop_assert!(matches!(result, "accepted" | "neutral" | "rejected"));
        if eligible == 0 {
            prop_assert_eq!(result, "rejected");
        }
    }

    #[test]
    fn accepted_finding_points_are_one_or_two(
        votes in prop::collection::vec(any::<bool>(), 0..4),
        majors in prop::collection::vec(any::<bool>(), 0..4),
    ) {
        let vote_values = votes
            .iter()
            .map(|yes| if *yes { "YES" } else { "NO" }.to_owned())
            .collect::<Vec<_>>();
        let severities = majors
            .iter()
            .map(|major| if *major { "major" } else { "minor" }.to_owned())
            .collect::<Vec<_>>();
        let points = accepted_finding_points_from_severities(&vote_values, &severities);
        prop_assert!(points == 1 || points == 2);
    }

    #[test]
    fn oos_fileable_requires_accepted_strict_majority(
        votes in prop::collection::vec(any::<bool>(), 1..4),
        majors in prop::collection::vec(any::<bool>(), 1..4),
    ) {
        let vote_values = votes
            .iter()
            .map(|yes| if *yes { "YES" } else { "NO" }.to_owned())
            .collect::<Vec<_>>();
        let severities = majors
            .iter()
            .map(|major| if *major { "major" } else { "minor" }.to_owned())
            .collect::<Vec<_>>();
        let result = classify_oos_result(
            vote_values.iter().filter(|vote| vote.as_str() == "YES").count(),
            vote_values.len(),
        );
        let fileable = oos_fileable_from_votes(result, &vote_values, &severities);
        if result != "accepted" {
            prop_assert!(!fileable);
        }
    }

    #[test]
    fn neutral_rescue_only_on_neutral_with_major_yes_majority(
        votes in prop::collection::vec(any::<bool>(), 1..4),
        majors in prop::collection::vec(any::<bool>(), 1..4),
    ) {
        let vote_values = votes
            .iter()
            .map(|yes| if *yes { "YES" } else { "NO" }.to_owned())
            .collect::<Vec<_>>();
        let severities = majors
            .iter()
            .map(|major| if *major { "major" } else { "minor" }.to_owned())
            .collect::<Vec<_>>();
        let result = classify_result(
            vote_values.iter().filter(|vote| vote.as_str() == "YES").count(),
            vote_values.len(),
        );
        let rescued = neutral_high_severity_rescue_to_oos(result, &vote_values, &severities);
        if result != "neutral" {
            prop_assert!(!rescued);
        }
    }

    #[test]
    fn ledger_render_round_trip_preserves_rows(
        round in 1u64..20,
        finding_id in "[A-Z_0-9]{3,12}",
        title in "[a-z ]{1,20}",
    ) {
        let row = LedgerRow::new(round, &finding_id, &title, "", "accepted", "", "");
        let sanitized_title = row.title.clone();
        let rendered = render_ledger(&[row]).expect("render");
        let parsed = parse_ledger(&rendered).expect("parse");
        prop_assert_eq!(parsed.len(), 1);
        prop_assert_eq!(&parsed[0].finding_id, &finding_id);
        prop_assert_eq!(&parsed[0].title, &sanitized_title);
    }

    #[test]
    fn replace_round_sets_target_round(
        old_round in 1u64..5,
        new_round in 6u64..10,
        label in "[A-Z]{1,6}",
    ) {
        let existing = vec![LedgerRow::new(old_round, "KEEP", "keep", "", "accepted", "", "")];
        let replacement = LedgerRow::new(99, &label, "new", "", "neutral", "", "");
        let merged = replace_round(existing, new_round, vec![replacement]);
        prop_assert_eq!(merged.len(), 2);
        prop_assert_eq!(&merged[0].round, &old_round.to_string());
        prop_assert_eq!(&merged[1].round, &new_round.to_string());
        prop_assert_eq!(&merged[1].finding_id, &label);
    }

    #[test]
    fn finding_dedup_key_uses_first_empty_location(
        suffix in "[a-z]{1,8}",
    ) {
        let block = format!(
            "### FINDING_1: a\n- **Location**: \n- **Location**: loc-{suffix}\n- **Concern**: same\n"
        );
        let key = finding_dedup_key(&block);
        prop_assert_eq!(key, "same");
    }

    #[test]
    fn finding_deduplication_is_idempotent_and_preserves_first_occurrence_order(
        entries in prop::collection::vec(("[a-z]{1,8}", "[a-z]{1,12}"), 1..16),
    ) {
        let blocks = entries
            .iter()
            .enumerate()
            .flat_map(|(index, (location, concern))| {
                let block = |ordinal| format!(
                    "### FINDING_{ordinal}: candidate\n- **Location**: {location}\n- **Concern**: {concern}\n"
                );
                [block(index + 1), block(index + 101)]
            })
            .collect::<Vec<_>>();
        let deduplicate = |input: &[String]| {
            let mut seen = HashSet::new();
            input
                .iter()
                .filter(|block| seen.insert(finding_dedup_key(block)))
                .cloned()
                .collect::<Vec<_>>()
        };
        let once = deduplicate(&blocks);
        let twice = deduplicate(&once);
        prop_assert_eq!(&once, &twice);

        let mut expected_seen = HashSet::new();
        let expected = entries
            .iter()
            .enumerate()
            .filter_map(|(index, (location, concern))| {
                let block = format!(
                    "### FINDING_{}: candidate\n- **Location**: {location}\n- **Concern**: {concern}\n",
                    index + 1
                );
                let key = finding_dedup_key(&block);
                expected_seen.insert(key.clone()).then_some(key)
            })
            .collect::<Vec<_>>();
        let actual = once
            .iter()
            .map(|block| finding_dedup_key(block))
            .collect::<Vec<_>>();
        prop_assert_eq!(actual, expected);
    }
}
