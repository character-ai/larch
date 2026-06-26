## Goal
Implement issue #5486: [IMPLEMENTING] [BUG] NOT_SUBSTANTIVE panel retry re-runs all reviewer slots instead of only failed ones.

## Implementation Plan
## Summary

When the round-1 code-review panel has NOT_SUBSTANTIVE slots (reviewer output that fails structured validation), `review_and_fix.py` detects the "⚠ Degraded code-review panel" banner in `voting-tally.md` and re-runs `review_core_capture` with **identical arguments**. This causes every slot in the panel — including the 9 that already produced valid, substantive output — to launch and run again. The wasted double-execution shows up as two identical groups of reviewer bars in the timing Gantt, and the extra serial work after the retry is the root cause of the gap between the reviewer bars and `cursor/apply`.

## Original report

During an `/implement` run for issue #5407, the Step 5 Gantt showed the same reviewer names appearing twice within a single round:

```
Round 1 reviewer timing  ·  window 0:00-17:38 (1058s)
codex/dyn-dyn-reference-shape-codex │█████                                                   │  94s
... [10 reviewers at t=0]
cursor/review                       │                   █                                    │   4s
aggregator                          │                     ███                                │  48s
cursor/validity-vote                │                        █████                           │  86s
codex/dyn-dyn-reference-shape-codex │                             ████████                   │ 144s
... [9 reviewers again at t=~670s]
cursor/apply                        │                                                      █ │  18s
```

The step-5 output contained: `⏳ /implement Step 5: round 1 panel was degraded (banner triggered); retrying with fresh panel.`

## Reproduction scenario

1. Run `/implement` on any issue large enough that 2+ reviewer slots produce narrative-only output (NOT_SUBSTANTIVE) in round 1.
2. Observe the `⏳ round N panel was degraded (banner triggered)` message in step-5 output.
3. The Gantt will show the same reviewer labels twice within the same round.
4. `INTENDED_SLOTS` will be 7, `SUCCEEDED_SLOTS` will be less than 7 (e.g. 5), confirming NOT_SUBSTANTIVE slots triggered the retry.

Likely trigger condition: reviewers produce preamble or meta-commentary without the required `### In-Scope Findings` / `### FINDING_N:` structure.

## Expected behavior

Only the NOT_SUBSTANTIVE slots re-run. The 9 slots that already produced valid structured output are not re-launched and their results are carried forward into the retry's aggregation.

## Observed behavior

All 11 slots re-run. `review_core_capture` is called a second time with identical `core_args` (including the same `--output-dir`). Inside `review_core`, `collector-results.env` is cleared at line 1562 and `dispatch-panel` launches a completely fresh panel. All timing and token costs for the first-pass successes are paid twice.

## Root cause analysis

**Confirmed.** The bug is in `python/review_and_fix.py`, function `_run_round`, around lines 2464–2489.

1. `_core_args_for_round` builds `core_args` once (line 2444). These args include `--output-dir str(round_dir)` and the full panel specification.
2. After the first `review_core_capture` (line 2450), if `voting-tally.md` contains the degraded-panel banner, the code calls `review_core_capture(core_args=core_args, ...)` again at line 2474 with the **identical** `core_args`.
3. Inside `review_pipeline.review_core`, `collector-results.env` is unconditionally cleared at the start (line 1562), erasing all first-pass slot results.
4. `dispatch-panel` is then called with no information about which slots already succeeded, so it launches all slots from scratch.

The NOT_SUBSTANTIVE detection itself is correct (`collect_results.py` marks slots `STATUS=NOT_SUBSTANTIVE` when structured validation fails). The problem is the retry strategy: re-running the full pipeline instead of only the failed slots.

## Evidence

- `python/review_and_fix.py:2444` — `core_args` built once, before the degraded check
- `python/review_and_fix.py:2474` — retry call passes same `core_args` verbatim
- `python/review_pipeline.py:1562` — `collector_results.write_text("", ...)` clears first-pass results unconditionally at review_core entry
- `larch-logs/implement/A520A3A7-78D6-4CB9-9337-68F3F3D34387/round-1/review-core-threshold.env`: `INTENDED_SLOTS=7 SUCCEEDED_SLOTS=5` — confirms 2 static slots were NOT_SUBSTANTIVE in the first pass
- `larch-logs/implement/A520A3A7-78D6-4CB9-9337-68F3F3D34387/round-1/collector-results.env`: 9 OK entries; `codex-specialist-correctness` and `cursor-specialist-testing` absent — the 2 NOT_SUBSTANTIVE slots from the first pass
- `larch-logs/implement/A520A3A7-78D6-4CB9-9337-68F3F3D34387/round-1/voting-tally.md`: scoreboard shows the same reviewer names twice — first pass (with real data) and retry pass (all zeros, because findings were deduped away)
- Step-5 output: `ROUNDS_COMPLETED=1` yet `window 0:00-17:38 (1058s)` — single round took 17+ minutes because it ran the full panel twice

## Affected files

- `python/review_and_fix.py` — `_run_round` contains the retry call at line 2474; this is where the fix belongs
- `python/review_pipeline.py` — `review_core`/`_collect_external_results` area (line 1562 clears collector; may need a skip-slots mechanism propagated from dispatch-panel)
- `python/collect_results.py` — NOT_SUBSTANTIVE detection (`_validate_substantive`, `_validate_structured`); no bug here but a slot-skip API may need to surface the already-OK file paths

## Suggested fix(es)

**Option A — targeted retry (preferred):** Before calling the retry `review_core_capture`, extract the list of already-successful slot output files from the first-pass `collector-results.env`. Pass those as a `--already-succeeded-files` argument (or equivalent) to `core_args` on the retry invocation. Inside `dispatch-panel`, skip re-launching any slot whose output file is already in that list and carry the file through to the collector. The retry then only spends tokens on the NOT_SUBSTANTIVE slots.

**Option B — pass NOT_SUBSTANTIVE slot names:** Alternatively, extract the NOT_SUBSTANTIVE slot basenames from the first-pass collector and pass `--skip-slots <names>` to `dispatch-panel` so only those are re-run.

Either option requires:
1. A way to pass the already-OK file list from `_run_round` into `core_args` for the retry call.
2. `dispatch-panel` (or `review_core`) to short-circuit those slots and copy their files into the new collector output.

A minimal guard with no API change: read the first-pass `collector-results.env` inside `review_and_fix.py` before the retry call and inject the OK file paths as `--external-output-files` into a modified `core_args` copy, skipping those slots in the dispatch.

## Open questions

1. Should the retry re-run dynamic archetype slots that were NOT_SUBSTANTIVE, or only static slots? (Dynamic slots are not counted by `check-reviewer-failure-threshold` today.)
2. Should `degraded-retry.flag` / `degraded-retry.done` sentinel filenames also be versioned (e.g. per-slot) to support partial retries, or is a single round-level flag sufficient?
3. If the first-pass voter results are reused, do the voter invocations also need to be re-run? (Voters run after aggregation, so likely yes on the NOT_SUBSTANTIVE slots only.)

## Test plan
(no test plan section in plan-file)
