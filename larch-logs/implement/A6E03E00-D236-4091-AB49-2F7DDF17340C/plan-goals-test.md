## Goal
Implement issue #5194: [IMPLEMENTING] [BUG] zero-findings-degraded-panel loop exit omits ROUNDS_COMPLETED from .step3-review-result.env, causing Step 5c publish refusal.

## Implementation Plan
## Summary

When the Step 3 plan-review loop exits with `LOOP_STATUS=zero-findings-degraded-panel`, `ROUNDS_COMPLETED` is not written to `.step3-review-result.env`. `design_publish.py`'s `review_provenance()` then reads `rounds=0` and refuses to publish the plan with "publish refused — review provenance indicates rounds\_completed=0", even though the review completed normally.

## Original report

During `/design` Step 5c, the publish tail refused with `VALIDATE_STATUS=defects-found`, `VALIDATE_DEFECT_COUNT=1`, `VALIDATE_LOG_FILE=` (empty), `VALIDATE_MISSING_SCRIPT_COUNT=0`. The review had actually completed 2 rounds with `LOOP_STATUS=zero-findings-degraded-panel`. The workaround was to manually append `ROUNDS_COMPLETED=2` to `.step3-review-result.env` and re-run `design-step5c.sh`.

## Reproduction scenario

1. Run `/design` on any issue.
2. The Step 3 review loop exits with `LOOP_STATUS=zero-findings-degraded-panel` (all reviewers found zero findings; panel is treated as degraded due to zero-findings condition).
3. Proceed through Gate B (zero-findings short-circuit), Step 3b, Step 4, Gate C (Approve).
4. In Step 5c, `design-step5c.sh` exits with `PUBLISH_RC=4`, `PLAN_WRITE_OK=false`, `VALIDATE_STATUS=defects-found`, `VALIDATE_LOG_FILE=` empty.
5. Inspecting `.step3-review-result.env`: `ROUNDS_COMPLETED` is absent.

## Expected behavior

`design_publish.py` publishes the plan. The review ran N ≥ 1 rounds and completed cleanly. `ROUNDS_COMPLETED=N` should be present in `.step3-review-result.env` so `review_provenance()` can verify the review ran.

## Observed behavior

Step 5c exits with `PUBLISH_RC=4`, blocking plan publication. The `.step3-review-result.env` file lacks `ROUNDS_COMPLETED`. `review_provenance()` reads `rounds=0`, and `provenance_present=True` (due to `status="ok"` from `TALLY_PLAN_REVIEW_STATUS`), triggering the `provenance_present and rounds_completed == 0` guard in `design_publish.py`.

## Root cause analysis

In `python/plan_review.py`, the `zero-findings-degraded-panel` branch (lines ~1988–2001) calls `phase_driver_write_result_env` directly with a hardcoded key list:

```python
if loop_status == "zero-findings-degraded-panel":
    phase_driver_write_result_env(
        tmpdir / ".step3-review-result.env",
        [
            ("LOOP_STATUS", "zero-findings-degraded-panel"),
            ("PANEL_PRUNED_EMPTY", ...),
            ("TALLY_PLAN_REVIEW_STATUS", ...),
            ("ACCEPTED_COUNT", ...),
            ("DEGRADED_PANEL", ...),
            ("DEGRADED_PANEL_WARNING", ...),
            ("INVALID_SLOT_PANEL_WARNING", ...),
            ("REASON", ...),
        ],
    )
```

`ROUNDS_COMPLETED` is not in this list. `step3_loop_emit_envelope` (which does write `ROUNDS_COMPLETED`) is never called for this path. By contrast, the `complete` path calls `step3_loop_emit_envelope` which writes `("ROUNDS_COMPLETED", str(rounds_completed or 0))`.

`design_publish.py:review_provenance()` reads `ROUNDS_COMPLETED` (or `REVIEW_ROUND_COUNT`) from the env file. Neither key is present on the `zero-findings-degraded-panel` path, so `rounds = 0` and the `provenance_present and rounds_completed == 0` guard fires.

## Evidence

- `python/plan_review.py` lines ~1988–2001: hardcoded `phase_driver_write_result_env` call for `zero-findings-degraded-panel` omits `ROUNDS_COMPLETED`.
- `python/design_publish.py` lines ~102–108: `review_provenance()` looks for `ROUNDS_COMPLETED` or `REVIEW_ROUND_COUNT`; missing key → `rounds = 0`.
- `python/design_publish.py` lines ~231–233: `elif provenance_present and rounds_completed == 0: blocked_reason = "rounds_completed=0"`.
- Observed `.step3-review-result.env` content (no `ROUNDS_COMPLETED`): `LOOP_STATUS=zero-findings-degraded-panel`, `PANEL_PRUNED_EMPTY=false`, `TALLY_PLAN_REVIEW_STATUS=ok`, `ACCEPTED_COUNT=0`, `DEGRADED_PANEL=0`, `DEGRADED_PANEL_WARNING=`, `INVALID_SLOT_PANEL_WARNING=`, `REASON=zero-findings-degraded-panel`.
- `ROUNDS_COMPLETED=2` was present in task stdout (via `step3_loop_emit_envelope` earlier in the run) but not persisted to the env file.

## Affected files

- `python/plan_review.py` — hardcoded key list for `zero-findings-degraded-panel` path omits `ROUNDS_COMPLETED`.
- `python/design_publish.py` — `review_provenance()` gates on `rounds_completed == 0`.
- `python/test_plan_review.py` — may lack a test covering the zero-findings-degraded-panel → step5c publish path.

## Suggested fix(es)

**Option A (preferred):** Add `("ROUNDS_COMPLETED", str(round_num))` and `("REVIEW_ROUND_COUNT", str(round_num))` to the hardcoded list written by the `zero-findings-degraded-panel` branch in `plan_review.py`. The round number is `round_num` in the surrounding loop scope.

**Option B:** In `design_publish.py:review_provenance()`, treat `loop_status == "zero-findings-degraded-panel"` with `rounds_completed == 0` and `tally_status == "ok"` as a known-safe degraded path rather than a provenance refusal.

Option A is more surgical and keeps the env file self-consistent.

Add a regression test asserting that after a `zero-findings-degraded-panel` loop exit, `.step3-review-result.env` contains a numeric `ROUNDS_COMPLETED >= 1`.

## Open questions

- Is `FINAL_ROUND_NUM` also expected in the env file on the `zero-findings-degraded-panel` path? The `step3_loop_persist_envelope` function writes it, but the hardcoded list omits it too.
- Should `review_provenance()` be made more defensive against the `zero-findings-degraded-panel` case, as defense-in-depth even after Option A?

## Test plan
(no test plan section in plan-file)
