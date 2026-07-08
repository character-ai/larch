### [rejected] FINDING_2

**Rejected subtype:** dismissed (0 YES)

### FINDING_2: Post-merge transient re-entry still forces pre-fix rebase
- **Reviewer(s)**: codex-specialist-correctness, dyn-dyn-postmerge-retry
- **Severity**: major
- **Concern**: After a merged-SHA rerun returns `Outcome.TRANSIENT`, route-exit still maps it to `NEXT_ACTION=reship` with `PRE_FIX_REBASE_REQUIRED=true`, so the resumed Step 8 can run `ship pre-fix-rebase` on a closed PR branch instead of just re-entering the post-merge wait.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Add a post-merge transient carve-out that re-enters `step-8-ship.sh` without pre-fix rebase, for example by making `ship pre-fix-rebase` return `skip/continue` when state has `PHASE=postmerge-push-watch` and `PR_CLOSED=true`, or by having route-exit omit `PRE_FIX_REBASE_REQUIRED` for this specific post-merge transient handoff. Keep the existing `NEXT_ACTION=reship` token if required by the plan.
  - From dyn-dyn-postmerge-retry: Add a post-merge carve-out so `PHASE=postmerge-push-watch` / `PR_CLOSED=true` transient re-entry skips pre-fix rebase (similar to the phase14 skip), or route post-merge retry through a dedicated re-entry that relaunches `step-8-ship.sh` without rebasing.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** dismissed (0 YES)

### FINDING_3: Emergency-repair green resume can bypass flap detection
- **Reviewer(s)**: cursor-specialist-correctness, dyn-dyn-postmerge-retry
- **Severity**: major
- **Concern**: Emergency-repair resume uses `skip_flap_check=True`, which bypasses the same-SHA repository-flap guard and can auto-finalize a merged run on a green recheck without confirming that the green result is a rerun of the repair run itself.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From dyn-dyn-postmerge-retry: On emergency-repair resume, require either a successful re-check of `MAIN_REPAIR_RUN_ID` itself or evidence that the green conclusion is from a rerun of that run, and keep `skip_flap_check` only for the post-driver wait after an explicit `rerun_failed()` submission.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_4: Global transient cap can stall post-merge recovery
- **Reviewer(s)**: dyn-dyn-postmerge-retry
- **Severity**: major
- **Concern**: Post-merge retry re-entry shares the session-global exit-6 transient counter with unrelated transient failures, so an already-consumed count can make the first post-merge `Outcome.TRANSIENT` emit `NEXT_ACTION=stall` even while a merged-SHA rerun is in flight.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-postmerge-retry: Use a phase-scoped counter for post-merge transient re-entry, or exempt `PHASE=postmerge-push-watch` from the global exit-6 cap so merged-SHA recovery is bounded only by `MAIN_HEALTH_MAX_TRANSIENT_RETRIES` / `TRANSIENT_RETRIES`.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** dismissed (0 YES)

### FINDING_5: Emergency-repair green-resume test skips real postmerge phase
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: The green-resume test for emergency-repair stubs out `run_postmerge_phase()`, so the boundary where a post-merge rerun turns green and finalization still has to succeed is not exercised end-to-end.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Exercise real run_postmerge_phase with boundary stubs; assert sentinel on success and Outcome.STALLED on finalize failure.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** dismissed (0 YES)

### FINDING_6: Missing explicit already-running post-merge rerun coverage
- **Reviewer(s)**: cursor-specialist-testing, codex-specialist-testing
- **Severity**: minor
- **Concern**: The new post-merge rerun path is covered for rerun submission success and failure, but not for `submitted=True, already_running=True`, so a valid in-flight rerun could regress into emergency repair without a test catching it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add focused _ship_postmerge_phase tests for already_running TRANSIENT and empty failed_run_id emergency-repair fallback.
  - From codex-specialist-testing: Add a unit test for `RerunResult(submitted=True, already_running=True, error=None)` and assert `Outcome.TRANSIENT` plus the transient retry state update.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

