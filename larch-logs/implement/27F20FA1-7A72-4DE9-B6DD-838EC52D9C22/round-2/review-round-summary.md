# Review Round 2

- Mode: `diff`
- 2 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Bookkeeping RUN_ID resolution lacks session-id fallback
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-generic-output.txt, dyn-dyn-route-exit-output.txt, dyn-dyn-oos-checkpoint-output.txt
- **Severity**: important
- **Concern**: `_step8_oos_checkpoint_bookkeeping` calls `file_oos.resolve_implement_run_id()`, which resolves only `ship-pr-state.sh` `RUN_ID` or a single `larch-logs/implement/*/oos-issues.ndjson` match. Disposition uses `resolve_implement_run_id_for_disposition`, which falls back to `$IMPLEMENT_TMPDIR/session-id`. On an empty OOS batch with no state `RUN_ID`, no ndjson, and a valid `session-id`, disposition can return rc `0` while bookkeeping fails to resolve a run id, emits `OOS_CHECKPOINT_RC=2` / `NEXT_ACTION=stall`, and leaves `OOS_PENDING=true`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Use resolve_implement_run_id_for_disposition in bookkeeping or add session-id fallback per plan; add regression test
  - From cursor-specialist-edge-cases-output.txt: Use the same run-id resolver as disposition (including session-id fallback) in _step8_oos_checkpoint_bookkeeping and add a regression test for that empty-batch path.
  - From cursor-specialist-testing-output.txt: Use resolve_implement_run_id_for_disposition (or shared helper) in bookkeeping and add a session-id-only success test.
  - From codex-generic-output.txt: Use a single checkpoint resolver with explicit precedence: `ship-pr-state.sh` `RUN_ID`, then `session-id`, then the single-ndjson fallback only when both are absent.
  - From dyn-dyn-route-exit-output.txt: Resolve run id in bookkeeping with `file_oos.resolve_implement_run_id_for_disposition(implement_tmpdir)` (or share one helper used by both disposition and bookkeeping), and add a test where state lacks `RUN_ID`, ndjson is absent, `session-id` is present, disposition rc is `0`, and bookkeeping succeeds.
  - From dyn-dyn-oos-checkpoint-output.txt: Have `_step8_oos_checkpoint_bookkeeping` use `file_oos.resolve_implement_run_id_for_disposition` (or share one helper) so bookkeeping targets the same canonical run id as disposition, and add a test where state has no `RUN_ID`, there is no ndjson, `session-id` is present, and disposition rc `0` still completes bookkeeping.


### FINDING_7: Pre-driver prose keys continuation on reship instead of ship
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Pre-driver prose at `skills/implement/SKILL.md:854` keys continuation on `NEXT_ACTION=reship` instead of `ship`. The orchestrator follows the pre-driver paragraph after a successful OOS file, but `reship` never fires from pre-driver, so `step-8-ship.sh` is skipped.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Replace reship with ship in the pre-driver continuation sentence and pin it in test-implement-structure.sh.


