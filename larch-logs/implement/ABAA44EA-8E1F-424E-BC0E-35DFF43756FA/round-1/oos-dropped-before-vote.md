### OOS_1: [OUT_OF_SCOPE] Missing RUN_ID regression coverage
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: The RUN_ID-missing regression path is still untested, so a future validation regression could slip through.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Add test_ship_pre_fix_rebase_missing_run_id_fails_without_next_action mirroring the blank REPO case.

### OOS_2: [OUT_OF_SCOPE] Hardcoded origin remote in force-push path
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: latent
- **Concern**: `rebase_and_push` still force-pushes through `origin` even when fork/base remote selection could differ.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Document or centralize push-remote selection when fork policy evolves.

### OOS_3: [OUT_OF_SCOPE] Phase14 skip prose and launcher fence drift apart
- **Reviewer(s)**: cursor-specialist-correctness, dyn-dyn-ship-rebase
- **Severity**: latent
- **Concern**: The SKILL prose describes the phase14 reship skip as conditional, but the fenced launcher is unconditional, so correctness depends on the orchestrator not invoking the fence outside the carve-out.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Align SKILL prose with flag-file authority or document both mechanisms explicitly.
  - From dyn-dyn-ship-rebase: Address the concern above.

### OOS_4: [OUT_OF_SCOPE] Phase14 skip guard disagrees on symlinked flags
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-ship-rebase
- **Severity**: latent
- **Concern**: The new phase14 skip guard accepts any file, while `_ship_route_phase14_reship_pending()` excludes symlinks, so route-exit and pre-fix-rebase can disagree on whether phase14 continuation is pending.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Use same is_file() and not is_symlink() predicate as _ship_route_phase14_reship_pending
  - From dyn-dyn-ship-rebase: Address the concern above.

### OOS_5: [OUT_OF_SCOPE] Route-exit integration test misses PRE_FIX_REBASE_REQUIRED assertion
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: nit
- **Concern**: The route-exit integration test still does not assert the `PRE_FIX_REBASE_REQUIRED` handoff contract for ci-fix and reship.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Extend test_ship_route_exit_classifies_driver_sidecars to assert PRE_FIX_REBASE_REQUIRED=true for ci-fix and reship only

### OOS_6: [OUT_OF_SCOPE] RUN_ID and ship-pr-state missing-path failures are untested
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: nit
- **Concern**: Blank `RUN_ID` and missing `ship-pr-state.sh` setup failures still lack parametrized coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Add parametrized tests expecting non-zero exit and no NEXT_ACTION for those setup failures

### OOS_7: [OUT_OF_SCOPE] OOS checkpoint reship still skips pre-fix rebase
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: nit
- **Concern**: The OOS checkpoint reship path still skips the pre-fix rebase; that is only acceptable if that path is intentionally autonomous and does not need fresh main.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Extend only if OOS reship gains edit steps
  - From cursor-specialist-testing: No change unless product wants pre-fix on OOS reship too

### OOS_8: [OUT_OF_SCOPE] New pre-fix tests are not in the shard map
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: nit
- **Concern**: The new pre-fix tests are not represented in the shard map, so they fall back to round-robin distribution and may skew timing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Rebalance shards if timing skew appears

### OOS_9: [OUT_OF_SCOPE] No git integration test for defer_push=False pre-fix push
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: nit
- **Concern**: There is still no git integration test for the `defer_push=False` pre-fix push path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Accept unit-test strategy or add optional git fixture test later

### OOS_10: [OUT_OF_SCOPE] Phase14 handoff conflict regression case is untested
- **Reviewer(s)**: dyn-dyn-ship-rebase
- **Severity**: nit
- **Concern**: The interaction where `enable_pre_push_handoff` creates the flag and a later `ship_pre_fix_rebase_main` must not continue while conflicts remain is still uncovered.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-ship-rebase: Address the concern above.

