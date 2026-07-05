### OOS_1: pre-fix rebases bypass REBASE_COUNT
- **Reviewer(s)**: dyn-dyn-ship-rebase
- **Severity**: important
- **Concern**: Successful pre-fix rebases do not update `REBASE_COUNT`, so the CI monitor can allow more physical rebases than the configured cap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-ship-rebase: After a successful rebase_and_push with result.rebased true, increment and persist REBASE_COUNT (and mirror any other counter semantics _ship_rebase_phase relies on), or centralize counter updates inside rebase_and_push for all callers.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### OOS_2: Fence count expectation is stale
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: important
- **Concern**: The fence-shape test expects 22 launcher fences, but `skills/implement/SKILL.md` currently has 21, so CI will fail until the count is corrected or the missing fence is added.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Set EXPECTED_NEW to 21, or add the missing launcher fence if 22 was intended.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### OOS_3: In-progress conflict path omits PHASE=rebase state write
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: When `rebase_in_progress()` is true, the conflict handoff path can leave the state without a `PHASE=rebase` write, which weakens the conflict handoff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Reuse _ship_pre_fix_write_conflict_state or _write_ship_state(phase=rebase) on in-progress conflict path


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected (latent-rerouted)

### OOS_4: PrePushConflictHandoff write-failure path is untested
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: latent
- **Concern**: The write-failure exit path for pre-push conflict handoff still lacks regression coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Add monkeypatch test forcing _ship_pre_fix_write_conflict_state or _ship_pre_fix_patch_handoff to raise; assert rc != 0 and no NEXT_ACTION=


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected (latent-rerouted)

### OOS_5: Removed step-6 merge-ref rebase has no mechanical successor guard
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: latent
- **Concern**: The removed step-6 merge-ref rebase has no mechanical pre-fix successor guard, so generated-file ci-fix repairs can run without an explicit freshness sentinel.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Write tmpdir sentinel from ship_pre_fix_rebase_main and fail closed in ci-fix when PRE_FIX_REBASE_REQUIRED=true but sentinel absent


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected (latent-rerouted)

### OOS_6: Pre-fix conflict handoff can be skipped incorrectly after a conflict
- **Reviewer(s)**: dyn-dyn-ship-rebase
- **Severity**: important
- **Concern**: A second `ship pre-fix-rebase` call can take the phase14 skip branch before conflict checks and continue while the rebase is still paused on conflicts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-ship-rebase: Do not key the skip solely on flag presence. Run the in-progress/conflict-metadata checks before any skip; limit the skip to the no-checks-observed phase14 case (e.g. mirror `_ship_route_phase14_reship_pending` and/or distinguish flag content/reason), and unlink or use a separate marker for conflict handoffs from `_write_handoff_flag`.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### OOS_7: phase14 skip bypasses rebase and checkout guards
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-ship-rebase
- **Severity**: important
- **Concern**: The phase14 short-circuit can return `NEXT_ACTION=continue` before the in-progress rebase check and the branch/repo/protected-branch guards run. That lets a stale flag green-light `ci-fix` or `reship` on the wrong checkout, or skip conflict routing when a paused rebase should have gone to `conflict-fix` or stall.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From dyn-dyn-ship-rebase: Address the concern above.
  - From dyn-dyn-ship-rebase: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)
