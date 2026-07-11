# Issue #6907 investigation notes

## Bug (verified)
Post-merge log flush emits `REASON=preterminal-outcome` (expected, NEVER #16 policy skip).
Stall classifier over-matches → `transient-infra / step8-shippr` → spurious reship →
`checkout-mismatch` (tree on main) → EXIT_CODE!=0 bail → normalize sees failure signals →
outcome "stalled" → terminal report → spurious [Bug] filed.

## Two-layer architecture (KEY)
- FAILURE_CLASS + RESUME_HINT (classifier, `_classify.py`) drive retry/reship.
  `RESUME_HINT=step8-shippr` is the ONLY reship branch (re-invokes step-8-ship.sh).
- root-cause VERDICT (`operator-action`|`larch-defect`|`environment`), written by Main Claude
  AFTER investigation, gates whether a public [Bug] is filed (stall-recovery.md sub-steps 8-9).
- ISSUE CONFLATES THESE: `operator-action` is NOT a FAILURE_CLASS returned by classifier normally;
  it IS a report verdict. BUT `_safe_class_value` (_tokens.py:380) DOES allow emitting
  FAILURE_CLASS=operator-action, and retry_policy caps.get(operator-action)->(0,"none") => no reship.

## Why RESUME_HINT=step8-shippr (two independent producers)
1. `_ship_refresh_preterminal_stall` matches `config.REFRESH_SKIP_PRETERMINAL_OUTCOME in lower`
   (_classify.py:148) -> returns transient-infra/step8-shippr/transient-output.
2. Even if #1 fixed -> fallback unrecoverable, BUT `_resume_hint_for` (_classify.py:97-119):
   `postmerge-flush` sanitizes to "unknown" step (_safe_step_value), so falls through to
   phase logic; phase=postmerge (non-empty, not review/impl) => returns "step8-shippr" for
   any non-terminal klass. `unrecoverable` klass short-circuits to "none" though (line 99).

## TRUE ORIGIN: ship_pr.py:331-338 `run_postmerge_phase`
- post.outcome OK (merge succeeded), terminal-OK finalize already written (line 330).
- optional `finalize_postmerge_logs` returns `skip.skipped=True` (reason=preterminal-outcome).
- Code then marks stall_tracking=True, stall_step="postmerge-flush", writes terminal finalize
  STALLED, returns ShipResult(STALLED). => A *skipped* best-effort log flush downgrades a
  SUCCESSFUL merge to STALLED. This seeds the entire cascade.

## Fix loci (design fork)
- A. Classifier short-circuit in classify() (issue primary): phase==postmerge && merge_result in
  _TERMINAL_MERGE_RESULTS -> return operator-action/none/postmerge-flush-expected. Matches issue
  scope; defense-in-depth. BUT filing suppression relies on downstream verdict (gap).
- B. ship_pr.py origin: skipped post-merge flush should NOT be STALLED (merge done). Deepest,
  stops cascade; higher blast radius on ship path.
- C. Narrow `_ship_refresh_preterminal_stall` (issue says less safe).

## Open questions (issue)
Q1: operator-action suppress ALL terminal reporting for postmerge-after-merge, or just skip reship?
    -> run is functionally complete (merged); want BOTH no-reship AND no-spurious-bug + outcome "merged".
Q2: other preterminal-outcome emission sites? -> only `_preterminal_outcome_refresh_skip`
    (run_log_flush.py:710), used by flush_logs_pre (pre-push, intended) and finalize_postmerge_logs
    (postmerge, the bug). No other emission sites of REFRESH_SKIP_PRETERMINAL_OUTCOME.

## Existing tests to respect
- test_classify_preterminal_ship_refresh_stall (test_stall_recovery.py:151) MUST still pass
  (pre-push STALL_STEP=pr-create-guideline-outcome-refresh -> transient-infra/step8-shippr).
- test_normalize_outcome_stale_finalize_terminal_fields_with_clean_merge (:881) postmerge+merged.
- test_ship.py:5839 asserts STALL_STEP==postmerge-flush (ship-side).
