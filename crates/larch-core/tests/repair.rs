use std::collections::BTreeSet;

use larch_core::review::{
    RejectedFindingsRound, RepairBatchReport, RepairClassifier, RepairCleanupAction,
    RepairCoderAttempt, RepairCoderInput, RepairCoderResult, RepairCommitOutcome,
    RepairComposition, RepairConvergenceEvidence, RepairCounts, RepairRoundArtifacts,
    RepairRoundInput, RepairSnapshotError, RepairSnapshotLayout, RepairSnapshotMode,
    RepairTrackedPath, SnapshotArtifactIdentity, cleanup_plan, collect_repair_stage_paths,
    count_code_review_findings, render_rejected_findings_aggregate, render_repair_tally_body,
    render_scout_manifest_payload, resolve_coder_result, resolve_repair_round,
    snapshot_identity_matches, tally_flush_sidecar, tracked_delta_paths, untracked_delta_paths,
    validate_repair_snapshot,
};

const BATCH_GOLDEN: &str = include_str!("fixtures/review/repair_batch_report.golden.txt");

fn full_snapshot() -> RepairSnapshotLayout {
    RepairSnapshotLayout {
        root_exists: true,
        root_entries: BTreeSet::from([
            "pre-coder-head.txt".to_owned(),
            "pre-coder-tracked-paths.txt".to_owned(),
            "pre-coder-untracked-paths.txt".to_owned(),
            "pre-coder-path-diffs".to_owned(),
        ]),
        pre_head: Some("abc123\n".to_owned()),
        tracked_paths: Some(vec!["src/lib.rs".to_owned(), "notes\\draft.md".to_owned()]),
        untracked_paths: Some(vec!["already.tmp".to_owned()]),
        pre_coder_patch_names: BTreeSet::from([
            "src__lib.rs.patch".to_owned(),
            "src__lib.rs.cached.patch".to_owned(),
            "notes__draft.md.patch".to_owned(),
            "notes__draft.md.cached.patch".to_owned(),
        ]),
    }
}

#[test]
fn repair_artifacts_and_coder_wire_match_python_contract() {
    let artifacts = RepairRoundArtifacts::new("/tmp/implement", 2);
    assert_eq!(
        artifacts.round_dir().to_string_lossy(),
        "/tmp/implement/round-2"
    );
    assert_eq!(
        artifacts.accepted_in_scope_findings().to_string_lossy(),
        "/tmp/implement/round-2/accepted-in-scope-findings.md"
    );
    assert_eq!(
        artifacts.composed_findings().to_string_lossy(),
        "/tmp/implement/round-2/review-findings-full.composed.jsonl"
    );
    let result = larch_core::review::RepairCoderResult {
        rc: 0,
        tool: "codex".to_owned(),
        status: "applied".to_owned(),
        log_file: "coder-output.log\nignored".to_owned(),
        input_count: 2,
        scrub_count: 1,
        revert_count: 0,
        commit_sha: "deadbeef".to_owned(),
    };
    assert_eq!(
        result.render_env(),
        "CODER_TOOL=codex\nCODER_STATUS=applied\nCODER_LOG_FILE=coder-output.log ignored\nCODER_INPUT_COUNT=2\nSUBMODULE_SCRUB_COUNT=1\nSUBMODULE_REVERT_COUNT=0\nCODER_COMMIT_SHA=deadbeef\n"
    );
}

#[test]
fn repair_snapshot_transitions_and_cleanup_preserve_python_baselines() {
    let missing = RepairSnapshotLayout::default();
    assert_eq!(
        validate_repair_snapshot(&missing),
        Ok(RepairSnapshotMode::Missing)
    );
    assert_eq!(
        cleanup_plan(RepairSnapshotMode::Missing, false),
        vec![
            RepairCleanupAction::RestoreStaged,
            RepairCleanupAction::RestoreWorktree,
            RepairCleanupAction::Verify,
        ]
    );

    let full = full_snapshot();
    assert_eq!(
        validate_repair_snapshot(&full),
        Ok(RepairSnapshotMode::Full)
    );
    assert_eq!(
        cleanup_plan(RepairSnapshotMode::Full, true),
        vec![
            RepairCleanupAction::RestoreStaged,
            RepairCleanupAction::RestorePreCoderTracked,
            RepairCleanupAction::RemoveCoderUntracked,
            RepairCleanupAction::Verify,
        ]
    );
    let partial = RepairSnapshotLayout {
        root_entries: BTreeSet::new(),
        ..full.clone()
    };
    assert_eq!(
        validate_repair_snapshot(&partial),
        Err(RepairSnapshotError::PartialArtifacts)
    );
    let head_untracked = RepairSnapshotLayout {
        root_entries: BTreeSet::from([
            "pre-coder-head.txt".to_owned(),
            "pre-coder-untracked-paths.txt".to_owned(),
        ]),
        tracked_paths: None,
        pre_coder_patch_names: BTreeSet::new(),
        ..full
    };
    assert_eq!(
        validate_repair_snapshot(&head_untracked),
        Ok(RepairSnapshotMode::HeadUntracked)
    );
    let unsafe_head_untracked = RepairSnapshotLayout {
        root_entries: BTreeSet::from([
            "pre-coder-head.txt".to_owned(),
            "pre-coder-untracked-paths.txt".to_owned(),
            "pre-coder-path-diffs".to_owned(),
        ]),
        ..head_untracked
    };
    assert_eq!(
        validate_repair_snapshot(&unsafe_head_untracked),
        Err(RepairSnapshotError::UnexpectedPatches)
    );

    let baseline = BTreeSet::from(["dirty.py".to_owned()]);
    let tracked = tracked_delta_paths(
        &[
            RepairTrackedPath {
                path: "dirty.py".to_owned(),
                matches_baseline: true,
            },
            RepairTrackedPath {
                path: "fixed.py".to_owned(),
                matches_baseline: false,
            },
        ],
        &baseline,
    );
    assert_eq!(tracked, ["fixed.py"]);
    let untracked = untracked_delta_paths(
        &["already.tmp".to_owned(), "new.tmp".to_owned()],
        &BTreeSet::from(["already.tmp".to_owned()]),
    );
    assert_eq!(untracked, ["new.tmp"]);
    assert_eq!(
        collect_repair_stage_paths(RepairSnapshotMode::Full, "post-coder", &tracked, &untracked),
        ["fixed.py", "new.tmp"]
    );
    assert!(
        collect_repair_stage_paths(RepairSnapshotMode::Full, "", &tracked, &untracked).is_empty()
    );

    let identity = SnapshotArtifactIdentity {
        name: "pre-coder-head.txt".to_owned(),
        size: 7,
        checksum: 42,
    };
    assert!(snapshot_identity_matches(
        std::slice::from_ref(&identity),
        std::slice::from_ref(&identity),
    ));
}

#[test]
fn repair_coder_terminal_transitions_match_python() {
    let input = RepairCoderInput {
        input_count: 2,
        scrub_count: 1,
        scrub_ok: true,
        scrubbed_count: 2,
        snapshot_valid: true,
        snapshot_head_fresh: true,
        tool_log: "round-1/coder-output.log".to_owned(),
        attempts: vec![
            RepairCoderAttempt {
                tool: "cursor".to_owned(),
                dispatched: false,
                cleanup_ok: true,
                ..RepairCoderAttempt::default()
            },
            RepairCoderAttempt {
                tool: "codex".to_owned(),
                dispatched: true,
                cleanup_ok: true,
                stage_path_count: 1,
                commit: RepairCommitOutcome::Committed("deadbeef".to_owned()),
                ..RepairCoderAttempt::default()
            },
        ],
    };
    let coder = resolve_coder_result(&input);
    assert_eq!(coder.status, "applied");
    assert_eq!(coder.tool, "codex");
    assert_eq!(coder.commit_sha, "deadbeef");
    let failed_coder = resolve_coder_result(&RepairCoderInput {
        attempts: vec![RepairCoderAttempt {
            tool: "codex".to_owned(),
            dispatched: true,
            cleanup_ok: true,
            submodule_revert_count: 1,
            ..RepairCoderAttempt::default()
        }],
        ..input
    });
    assert_eq!(failed_coder.status, "submodule-violation");
    assert_eq!(failed_coder.rc, 3);
}

#[test]
fn repair_round_terminal_transitions_match_python() {
    let coder = RepairCoderResult {
        rc: 0,
        tool: "codex".to_owned(),
        status: "applied".to_owned(),
        log_file: "round-2/coder-output.log".to_owned(),
        input_count: 1,
        scrub_count: 0,
        revert_count: 0,
        commit_sha: "deadbeef".to_owned(),
    };
    let state = resolve_repair_round(
        2,
        &RepairRoundInput {
            core_status: "fix-required".to_owned(),
            round_counts: RepairCounts {
                accepted: 1,
                rejected: 0,
                exonerated: 2,
                neutral: 3,
            },
            prior_counts: RepairCounts {
                accepted: 4,
                rejected: 5,
                exonerated: 6,
                neutral: 7,
            },
            coder,
            composition: RepairComposition::Succeeded(RepairCounts {
                accepted: 9,
                rejected: 8,
                ..RepairCounts::default()
            }),
            ..RepairRoundInput::default()
        },
    );
    assert_eq!(state.status, "fix-applied");
    assert_eq!(state.total_counts.accepted, 9);
    assert_eq!(state.total_counts.rejected, 8);
    assert_eq!(state.total_counts.exonerated, 8);
    assert_eq!(state.total_counts.neutral, 10);

    let self_review = resolve_repair_round(
        1,
        &RepairRoundInput {
            core_exit_code: 1,
            core_status: "panel-failed".to_owned(),
            zero_survivor_panel_failed: true,
            ..RepairRoundInput::default()
        },
    );
    assert_eq!(
        (self_review.status.as_str(), self_review.exit_code),
        ("self-review-required", 0)
    );

    let tally_failed = resolve_repair_round(
        1,
        &RepairRoundInput {
            core_status: "ok".to_owned(),
            round_counts: RepairCounts {
                accepted: 1,
                ..RepairCounts::default()
            },
            convergence: RepairConvergenceEvidence::Findings {
                non_nit_count: 1,
                important_present: false,
            },
            composition: RepairComposition::Failed,
            classifier: RepairClassifier::Healthy,
            ..RepairRoundInput::default()
        },
    );
    assert_eq!(
        (tally_failed.status.as_str(), tally_failed.exit_code),
        ("tally-flush-failed", 2)
    );
}

#[test]
fn repair_batch_reports_are_byte_stable_and_count_only_code_review_records() {
    let report = RepairBatchReport {
        rounds: 2,
        counts: RepairCounts {
            accepted: 2,
            rejected: 1,
            ..RepairCounts::default()
        },
        round_summaries: vec![
            (
                2,
                "# Review Round 2\n- 2 accepted, 1 rejected (\nround-two note\n".to_owned(),
            ),
            (
                1,
                "# Review Round 1\n- Rejected findings: 1\nround-one note\n".to_owned(),
            ),
        ],
        rejected_findings: "# Rejected Findings\n\n### [Code Review] rejected one\nDetails\n"
            .to_owned(),
        voting_tally: "# Code Review Voting Tally\n\nFinal tally\n".to_owned(),
        ..RepairBatchReport::default()
    };
    assert_eq!(
        render_repair_tally_body(&report),
        format!("{BATCH_GOLDEN}\n")
    );
    assert_eq!(
        render_rejected_findings_aggregate(
            &[
                RejectedFindingsRound {
                    round_num: 2,
                    compact: "# Rejected Findings\n\n### [Code Review] two\n".to_owned(),
                    ..RejectedFindingsRound::default()
                },
                RejectedFindingsRound {
                    round_num: 1,
                    full: "# Rejected Findings\n\n### [Code Review] one\n".to_owned(),
                    ..RejectedFindingsRound::default()
                },
            ],
            None,
        ),
        Some("# Rejected Findings\n\n# Review Round 1\n\n### [Code Review] one\n\n# Review Round 2\n\n### [Code Review] two\n\n".to_owned())
    );
    let (counts, saw_code_review) = count_code_review_findings(
        "{\"phase\":\"code-review\",\"outcome\":\"accepted\"}\ninvalid\n{\"phase\":\"plan-review\",\"outcome\":\"rejected\"}\n{\"phase\":\"code-review\",\"outcome\":\"rejected\"}\n",
    );
    assert!(saw_code_review);
    assert_eq!((counts.accepted, counts.rejected), (1, 1));
    assert_eq!(
        render_scout_manifest_payload("ok", "002", "/tmp/scout.json", "/tmp/yield.tsv"),
        Ok("{\"status\":\"ok\",\"dynamic_slots\":2,\"manifest_basename\":\"scout.json\",\"yield_tsv_basename\":\"yield.tsv\"}\n".to_owned())
    );
    assert_eq!(
        tally_flush_sidecar(1, "bad\n", "out\n"),
        "voting write-tally failed (returncode=1)\n--- stderr ---\nbad\n\n--- stdout ---\nout\n\n"
    );
}
