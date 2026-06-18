# Review Round 2

- Mode: `diff`
- 4 accepted, 2 rejected (0 neutral)

## Accepted Findings

### FINDING_1: correctness: DISPATCH_OK!=true omits execution-issues warning
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-generic-output.txt
- **Severity**: important
- **Concern**: When `agent dispatch-waterfall` exits 0 with `DISPATCH_OK=false`, `python/review_aggregate.py:703-705` emits dispatch-failed KVs only and skips the execution-issues warning that the deleted `aggregate-findings.sh` appended. Aggregation is skipped correctly, but `/implement` Step 5 gets no **External Reviewer Issues** breadcrumb in `execution-issues.md`, making silent aggregation skips harder to diagnose.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Call _append_warning with DISPATCH_OK value and failure_see_phrase before emitting dispatch-failed KVs.
  - From codex-generic-output.txt: Mirror the deleted shell branch: call `_append_warning(...)` with `DISPATCH_OK=<value>` and `_failure_see_phrase(dispatch_err, ...)` before `_emit_aggregate_result(..., reason="dispatch-failed")`.


### FINDING_3: risk-integration: plan-mode OOS rollback test omits fail-open stdout KV assertions
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `test_prune_nit_plan_oos_replace_failure_restores_findings` in `python/test_review_aggregate.py:571-600` restores file bytes on simulated OOS move failure but never asserts `STATUS=skipped`, `PRUNED_COUNT=0`, and `INSCOPE_REMAINING=0` on stdout. Regressions in the contract stream consumed by `prune-nit.env` writers can slip through even though `review_aggregate.py:823-825` appears to emit those KVs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Run via run_review prune-nit-findings or capture CLI stdout and assert all three KVs on the rollback path


### FINDING_4: risk-integration: embedded plan-review prune lacks fail-open env synthesis
- **Reviewer(s)**: codex-generic-output.txt, dyn-plan-review-prune-output.txt
- **Severity**: important
- **Concern**: G2 retargets embedded plan-review prune-nit to `review prune-nit-findings` via `_rewrite_prune_asset` in `python/plan_review.py:906-923`, but does not add the fail-open env synthesis that `review_pipeline.py:2004-2006` now has. In the decoded `plan-review-loop.sh` body (~1761-1785), prune stdout is redirected to `plan-review-prune-nit.env`; on non-zero rc the loop only emits a WARN, then copies that file to `prune-nit.env` and defaults missing `INSCOPE_REMAINING` to `0`. If the Python CLI fails before emitting KVs (import error, bad override, missing `python3`), the env file stays empty or partial with no `STATUS=skipped`, while `review_pipeline` would write `PRUNED_COUNT=0\nINSCOPE_REMAINING=0\nSTATUS=skipped\n`. That can make `/design` Step 3 treat a failed prune like zero in-scope findings and skip or distort aggregation/tally.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Extend `_rewrite_prune_asset` so that after the prune invocation, non-zero rc or empty captured env rewrites the env file with the skipped KV fallback before the round-dir copy (mirror `review_pipeline.py:2006`); add a decoded-body contract test asserting that fallback block exists.
  - From dyn-plan-review-prune-output.txt: Extend `_rewrite_prune_asset` to mirror `review_pipeline.py:2006`: after the prune invocation, if rc is non-zero or the captured env file is empty, rewrite it with the skipped KV fallback before the round-dir copy; or invoke prune under `LARCH_QUIET_DISABLE=1` and add an explicit empty-stdout guard like reviewer-prune at `898-899`.


### FINDING_5: risk-integration: embedded plan-review prune fail-open persistence untested
- **Reviewer(s)**: dyn-plan-review-prune-output.txt
- **Severity**: important
- **Concern**: `test_embedded_plan_review_prune_nit_uses_review_cli` in `python/test_plan_review.py:73-85` checks CLI symbols in the decoded loop but not fail-open persistence. Plan acceptance requires `prune-nit.env` to stay parseable on success and fail-open paths; `review_pipeline.py:2006` and `_ensure_prune_sidecars` encode that contract for implement, but there is no pytest guard that the embedded loop writes skipped KVs when prune fails or returns empty stdout (~1769-1773).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-plan-review-prune-output.txt: Decode `plan-review-loop.sh`, locate the prune block, and assert it contains a fallback write of `PRUNED_COUNT=0` / `INSCOPE_REMAINING=0` / `STATUS=skipped` on failure or empty capture (mirror `test_embedded_plan_review_loop_uses_migrated_collector` style region assertions).


