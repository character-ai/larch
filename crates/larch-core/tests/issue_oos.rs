//! Golden parity for the out-of-scope record, priority, and conflict model.
//!
//! Every expectation is the byte-for-byte output of the Python owners
//! (`larch.issue.oos`, `larch.issue.oos_priority`, `larch.issue.oos_disposition`,
//! and the conflict half of `larch.issue.file_oos`) for the same input.

use larch_core::{
    BlockBoundary, DispositionCounters, DispositionState, OosItemKind, analyze_run_dir,
    count_non_security_blocks, is_high_risk_oos_block, parse_issue_input, parse_oos_blocks,
    plan_file_conflict_deps, render_deps_tsv, serialize_accepted_oos, topological_create_order,
    universal_newlines,
};
use std::fs;

/// A recorded review artifact: one accepted item, one security hold, one
/// finding whose fenced example quotes a security heading, and one tagged
/// out-of-scope finding.
const RECORDED_FINDINGS: &str = concat!(
    "### OOS_3: Retry budget is shared across unrelated calls\n",
    "- **Description**: `crates/larch-core/src/retry.rs:41-88` shares one budget.\n",
    "- **Reviewer**: reviewer-correctness\n",
    "- **Phase**: implement\n",
    "- **focus-area**: correctness\n",
    "Vote tally: 3/3 YES Result=accepted Fileable=true\n",
    "\n",
    "### OOS_4: [security] Token echoed into the run log\n",
    "- **Description**: The vendor tail keeps the bearer token.\n",
    "- **Phase**: implement\n",
    "Vote tally: 3/3 YES Result=accepted Fileable=true\n",
    "\n",
    "### FINDING_5: Fence example quotes a security heading\n",
    "- **Concern**: The doc shows\n",
    "```\n",
    "### OOS_9: [security] example\n",
    "- focus-area: security\n",
    "```\n",
    "  which must stay a finding.\n",
    "Vote tally: 2/3 YES Result=rejected Fileable=false\n",
    "\n",
    "### FINDING_6: [OUT_OF_SCOPE] Widen the flush window\n",
    "- **Description**: `python/larch/report/run_log_flush.py:120-140` and Makefile.\n",
    "- **Phase**: implement\n",
    "Vote tally: 3/3 YES Result=accepted Fileable=true\n",
);

/// The exact bytes `cli.py oos serialize` wrote for `RECORDED_FINDINGS`.
const RECORDED_SERIALIZED: &str = concat!(
    "### OOS_1: Retry budget is shared across unrelated calls\n",
    "- **Description**: `crates/larch-core/src/retry.rs:41-88` shares one budget.\n",
    "- **Reviewer**: reviewer-correctness\n",
    "- **Phase**: implement\n",
    "- **focus-area**: correctness\n",
    "Vote tally: 3/3 YES Result=accepted Fileable=true\n",
    "\n",
    "\n",
    "### OOS_2: [OUT_OF_SCOPE] Widen the flush window\n",
    "- **Description**: `python/larch/report/run_log_flush.py:120-140` and Makefile.\n",
    "- **Phase**: implement\n",
    "Vote tally: 3/3 YES Result=accepted Fileable=true\n",
    "\n",
);

/// A recorded filing batch: two items collide on one file, two on another.
const RECORDED_BATCH: &str = concat!(
    "### OOS_1: Retry budget is shared\n",
    "- **Description**: `crates/larch-core/src/retry.rs:41-88` shares one budget.\n",
    "- **focus-area**: correctness\n",
    "\n",
    "### OOS_2: Retry budget logging\n",
    "- **Description**: crates/larch-core/src/retry.rs:80-95 logs the wrong id.\n",
    "- **focus-area**: quality\n",
    "\n",
    "### OOS_3: Unrelated flush window\n",
    "- **Description**: python/larch/report/run_log_flush.py:120-140 needs widening.\n",
    "- **focus-area**: regression\n",
    "\n",
    "### OOS_4: Flush window docs\n",
    "- **Description**: See python/larch/report/run_log_flush.py and Makefile.\n",
);

#[test]
fn serialization_matches_the_recorded_artifact_byte_for_byte() {
    let serialized = serialize_accepted_oos(RECORDED_FINDINGS);
    assert_eq!(serialized.text, RECORDED_SERIALIZED);
    assert_eq!(serialized.accepted, 2);
    assert_eq!(serialized.held_security, 1);
    assert_eq!(count_non_security_blocks(RECORDED_FINDINGS), 2);
}

#[test]
fn a_carriage_return_artifact_serializes_to_the_same_bytes() {
    let crlf = RECORDED_FINDINGS.replace('\n', "\r\n");
    let serialized = serialize_accepted_oos(&universal_newlines(&crlf));
    assert_eq!(serialized.text, RECORDED_SERIALIZED);
}

#[test]
fn serialized_records_reparse_as_the_batch_the_filer_reads() {
    let serialized = serialize_accepted_oos(RECORDED_FINDINGS);
    let blocks = parse_oos_blocks(&serialized.text, BlockBoundary::ItemHeading);
    let ids: Vec<&str> = blocks.iter().map(|block| block.item_id.as_str()).collect();
    assert_eq!(ids, ["OOS_1", "OOS_2"]);
    assert!(blocks.iter().all(|block| block.kind == OosItemKind::Oos));
    let parsed = parse_issue_input(&serialized.text);
    assert_eq!(parsed.items.len(), 2);
    assert!(parsed.items.iter().all(|item| !item.malformed));
}

#[test]
fn the_recorded_findings_carry_four_blocks_with_the_recorded_boundaries() {
    let blocks = parse_oos_blocks(RECORDED_FINDINGS, BlockBoundary::ItemHeading);
    let ids: Vec<&str> = blocks.iter().map(|block| block.item_id.as_str()).collect();
    assert_eq!(ids, ["OOS_3", "OOS_4", "FINDING_5", "FINDING_6"]);
    assert_eq!(blocks[3].end, RECORDED_FINDINGS.len());
    assert_eq!(
        blocks[2].title, "Fence example quotes a security heading",
        "a fenced heading must not open a block"
    );
}

#[test]
fn the_recorded_batch_plans_the_recorded_dependency_rows_and_order() {
    let parsed = parse_issue_input(RECORDED_BATCH);
    assert_eq!(parsed.items.len(), 4);
    let plan = plan_file_conflict_deps(&parsed.items, 200, 500).expect("plan");
    assert_eq!(plan.deps, [(1, 2), (3, 4)]);
    assert!(plan.warnings.is_empty());
    assert_eq!(render_deps_tsv(&plan.deps), "1\t2\n3\t4\n");
    assert_eq!(
        topological_create_order(parsed.items.len(), &plan.deps),
        [1, 2, 3, 4]
    );
    let priorities: Vec<bool> = parsed
        .items
        .iter()
        .map(|item| is_high_risk_oos_block(&item.body))
        .collect();
    assert_eq!(priorities, [true, false, true, false]);
}

#[test]
fn a_recorded_run_directory_reports_the_counters_the_gate_consumes() {
    let dir = tempfile::tempdir().expect("tempdir");
    fs::write(dir.path().join("oos-accepted-review.md"), RECORDED_FINDINGS).expect("write");
    fs::write(
        dir.path().join("oos-issues.ndjson"),
        "{\"body\": \"## Rejected / Out-of-Scope\\n- OOS_1 deferred\\n## Accepted\\n- OOS_2\"}\n",
    )
    .expect("write");
    let counts = analyze_run_dir(dir.path(), "");
    assert_eq!(counts.non_security_oos_blocks, 2);
    assert_eq!(counts.rejected_oos_markers, 1);
    assert_eq!(counts.issue_urls, 0);
    assert_eq!(counts.inline_triage_hits, 0);
    assert!(!counts.ndjson_parse_error);

    let counters = DispositionCounters {
        non_security: counts.non_security_oos_blocks,
        filed_urls: counts.issue_urls,
        inline_triage: counts.inline_triage_hits,
        rejected_markers: counts.rejected_oos_markers,
    };
    assert_eq!(counters.state(false), DispositionState::Blocked);
    assert_eq!(
        counters.failure_line("origin/main..HEAD"),
        "oos-disposition-gate: FAIL non_security_oos=2 filed_urls=0 inline_triage_lines=0 rejected_oos_markers=1 (commit-range origin/main..HEAD)"
    );
}
