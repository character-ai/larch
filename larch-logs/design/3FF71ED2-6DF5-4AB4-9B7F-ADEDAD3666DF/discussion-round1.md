## Decision 1: Which of the 5 bundled OOS findings are in scope
- **Question**: Issue #6089 bundles 5 OOS follow-ups from #5976/PR #6084. Finding #4 (heatmap TSV compat note) already appears resolved by an existing docs/run-logs.md note from the same PR. Which of the remaining 4 should this design address?
- **Resolution**: No response after two 60s waits (user away from keyboard); proceeded with the recommended defaults. In scope: Finding #1 (review Step 4 unconditional log-root + RUN_ID validation), Finding #2 (design publish warning-label mislabeling), Finding #5 (Step 18 + teardown duplicate flush-safety-net). Out of scope: Finding #3 (new review Step 4 regression harness — optional stretch, not recommended, deferred), Finding #4 (heatmap TSV compat note — already resolved, no action).
- **Source**: recommended default (no user response)

## Decision 2: Finding #1 must preserve scout-manifest branch behavior
- **Question**: N/A — surfaced via codebase inspection, not asked.
- **Resolution**: `review_log_root` is defined today only inside the `if [[ -n "${RUN_ID:-}" && "${SCOUT_STATUS:-na}" != "na" ]]` branch in skills/review/SKILL.md (line 82-84). The fix must make this value available unconditionally (including the `SCOUT_STATUS=na` standalone-review path) without changing the value already computed on the existing scout-manifest branch.
- **Source**: codebase

## Decision 3: Finding #5 must not regress bail/stall transcript coverage
- **Question**: N/A — surfaced via codebase inspection, not asked.
- **Resolution**: `finalize.py`'s `teardown()` → `_teardown_log_flush()` can run directly on bail/stall paths without `skills/implement/scripts/step-18.sh`'s own `execution-issues flush-safety-net` call ever having fired (per docs/run-logs.md: "Step 18 as a best-effort finalization safety net for bail and stall paths that reach teardown first"). The de-dup fix must not simply delete either call site outright; whichever site is removed or short-circuited must not lose coverage on paths where the other site never runs.
- **Source**: codebase

## Decision 4: Finding #2 scope — pause only, not clarify
- **Question**: Should the warning-label fix also wire up a distinct 'clarify' reason end-to-end, or just fix the confirmed pause-vs-5c mislabeling?
- **Resolution**: No response after a 60s wait; proceeded with the recommended default. Fix only the confirmed `reason=pause` mislabeling (thread `warning_step_label` so pause reports "pause" instead of "5c"). Leave `clarify.py`'s publish call as-is — it does not pass `--reason` today (defaults to "final"), and this design does not add a new "clarify" reason value.
- **Source**: recommended default (no user response)

Record 4 decisions resolved.
