## Goal
Implement issue #5504: [IMPLEMENTING] [BUG] stall-recovery retry merges round timing windows, misplacing post-aggregation probes in Gantt chart.

## Implementation Plan
## Summary

When the Step 5 review-and-fix loop stalls with `aggregator-validation-exhausted` and the stall recovery retries the entire `step-5-review.sh` in the same session (same `IMPLEMENT_TMPDIR`, same timing ledger), both the stalled attempt and the successful retry write `v1 round` entries for the same round number (e.g., round 1) to the shared timing ledger. `progress_report._timing_round_windows` computes the Gantt window as `(min(all starts), max(all ends))` across ALL entries for that round number. This creates an artificially wide merged window spanning from the stalled attempt's start to the retry's end. Post-aggregation validation probes — the `tally-code-votes` voter agents that run on the `aggregator-validation-exhausted` path in `review_pipeline.py` — appear in the timing ledger with timestamps belonging to the stalled attempt's phase, but render within this merged window at unexpected positions (mid-chart gap or right edge) rather than adjacently after the aggregator that triggered them. For a terminal stall (no retry), the probes appear within the window correctly, but the round's Gantt layout may still be unexpected. A related symptom: when the retry's `dispatch-voters` step spawns agents labeled `codex/correctness` and `codex/edge-cases`, these appear far to the right of the chart (well past the second aggregator), looking disconnected from the review activity that produced them.

## Original report

post-aggregation validation probes don't appear on the Gantt chart: when the aggregator stalls and recovery probes run (e.g. the final codex/correctness and codex/edge-cases entries at the tail of the chart in run 77D53A96-5B8B-4F44-8754-25FB9AD3E744), those probes show up in the chart at all. But if aggregator validation fires on the FIRST attempt (the stalled round), those probes wouldn't show up at all in the Gantt because the stalled round's timing data is discarded. Post-aggregation validation probes that run during a stalled round should be included in the Gantt chart.

## Reproduction scenario

1. Run `/implement` on any issue where the review aggregator stalls with `aggregator-validation-exhausted` on round 1 (STEP5_REVIEW_STATUS=stall, STALL_REASON=aggregator-validation-exhausted).
2. The Step 18a stall recovery retries `step-5-review.sh` in the same session (RESUME_HINT=step5-review, same `$IMPLEMENT_TMPDIR`).
3. The retry runs round 1 again and succeeds.
4. Inspect the final `## Round 1 reviewer timing` Gantt section in the run summary.
5. The chart window spans from the stalled attempt's start to the retry's end (0:00–16:52 in run 77D53A96-5B8B-4F44-8754-25FB9AD3E744).
6. The exhaust-path `tally-code-votes` voter agents from the stalled attempt appear mid-chart (around minute 4), far from the second aggregator they have no relation to.
7. The retry's `dispatch-voters` agents (e.g. `codex/correctness`, `codex/edge-cases`) appear at the far right of the chart (~minute 13), looking disconnected from the review panel that preceded them.

Non-deterministic: requires the aggregator to stall on the first attempt and the stall recovery to retry in the same session.

## Expected behavior

Post-aggregation validation probes — the voter agents spawned by `tally-code-votes` on the `aggregator-validation-exhausted` path — should appear clearly adjacent to the aggregator row that triggered them in the Gantt chart. When a stall recovery reruns the same round number, the Gantt should either:

- Split the chart into two logical sub-rounds (stalled attempt vs. retry), keeping each probe set near its own aggregator; or
- At minimum, the merged window should not produce a misleading layout where probes appear far from their originating aggregator.

## Observed behavior

In run 77D53A96-5B8B-4F44-8754-25FB9AD3E744:

- First stalled attempt's exhaust-path voters (`codex/plan-fidelity-vote`, `codex/pragmatism-vote`, `cursor/validity-vote`) appear at ~4 minutes — correct relative to the first aggregator.
- Second retry's voter agents (`codex/correctness`, `codex/edge-cases`) appear at ~13 minutes — far to the right of the second aggregator (~10 minutes), making the chart misleading.
- Total chart window is 16:52 (1012s), much wider than either individual attempt.

The wide merged window results from `_timing_round_windows` taking `(min(starts), max(ends))` across all `v1 round` entries for round_num=1 in the shared timing ledger. Both attempts append entries for round 1 with different start/end timestamps.

## Root cause analysis

**Primary issue**: `_timing_round_windows` in `python/progress_report.py` aggregates all round timing ledger entries for a given round number with `(min(starts), max(ends))`. When a stall recovery reruns the same round in the same session and timing ledger, both the stalled attempt and the retry contribute `v1 round` entries for round 1. The merged window spans the entire session from first attempt start to retry end, producing a single wide chart where both attempts' vendor rows intermix without visual separation.

**Secondary issue**: The `dispatch-voters` voter agents in the retry (normal success path, `review_pipeline.py` line 2353) use timing task labels derived from the reviewer archetype names (e.g., `codex/correctness`, `codex/edge-cases`) rather than the voter slot labels (`codex/plan-fidelity-vote`, `codex/pragmatism-vote`). This causes them to be visually indistinguishable from specialist reviewer rows earlier in the chart, contributing to the confusing layout.

**Note on data availability**: The stalled round's timing data is NOT discarded. `record_round_timing` (called at `review_and_fix.py` line 2979) captures `end_s` after `_run_round` returns — which is after the exhaust-path `tally-code-votes` voter agents finish (run at `review_pipeline.py` line 2313, inside `_run_round`). The probes DO appear in the timing ledger and DO appear in the Gantt, but at the wrong position due to the merged window.

## Evidence

- `python/progress_report.py` line 515 (`_timing_round_windows`): returns `(min(starts), max(ends))` across ALL `v1 round` entries for the given round number — no differentiation between stalled and retry attempts.
- `python/review_and_fix.py` line 2979 (`record_round_timing`): always called after `_run_round` returns; `end_s` captures time after exhaust-path voters finish.
- `python/review_pipeline.py` lines 2297-2327 (`aggregator-validation-exhausted` path): runs `tally-code-votes` at line 2313 before `_flush_round_log` at line 2323 and return — all within `_run_round`.
- Run 77D53A96-5B8B-4F44-8754-25FB9AD3E744 Gantt: round 1 window = 0:00–16:52 (1012s); first-attempt voters appear at ~220s; retry voters appear at ~850s.
- `larch-logs/implement/77D53A96-5B8B-4F44-8754-25FB9AD3E744/round-1/round-meta.json` — present (stalled round DOES have a round-meta.json and appears in the Gantt).

## Affected files

- `python/progress_report.py` — `_timing_round_windows` merges all round entries without attempt separation; `_render_phase_gantt` renders a single merged window per round number.
- `python/review_and_fix.py` — round loop uses the same round number for both stalled attempt and retry; `record_round_timing` records separate `v1 round` entries for each.

## Suggested fix(es)

**Option A — attempt-keyed round windows**: annotate `v1 round` ledger rows with an attempt counter (e.g., a new column). `_timing_round_windows` uses the highest attempt's `(start, end)` for the canonical window, and `_render_phase_gantt` renders separate sub-charts per attempt when multiple exist. This is the most informative fix but requires a timing ledger schema change.

**Option B — review-round restarts use a synthetic round number**: when a stall recovery retries the same round, bump the internal round number (e.g., round 1 retry → round 1a) so both the timing ledger and `round-meta.json` use distinct identifiers. The progress report would then render them as separate named rounds. Requires changes to the retry dispatch, timing writers, and Gantt rendering.

**Option C — merge-window but split the chart visually**: detect when multiple `v1 round` entries exist for the same round number with non-overlapping `(start, end)` ranges (indicating multiple attempts), and render two separate Gantt sections labeled "Round 1 (attempt 1)" and "Round 1 (attempt 2)" using per-attempt windows. Least invasive schema change but still requires rendering logic changes.

## Open questions

- Should the timing ledger schema be versioned to support attempt-level keys, or is a higher-level approach (option B or C) preferred?
- Are there other stall-recovery paths that rerun a round in the same session and would benefit from the same fix?
- Should the final `## Round N reviewer timing` section always show ALL attempts, or only the last successful one?

## Test plan
(no test plan section in plan-file)
