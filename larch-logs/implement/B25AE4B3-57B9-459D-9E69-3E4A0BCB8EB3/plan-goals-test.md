## Goal
Implement issue #5210: [IMPLEMENTING] [BUG] zero-findings-degraded-panel result env missing ROUNDS_COMPLETED causes Step 5c publish refusal.

## Implementation Plan
## Summary

When the plan-review loop exits via the `zero-findings-degraded-panel` path, `plan_review.py` writes `.step3-review-result.env` without `ROUNDS_COMPLETED` or `REVIEW_ROUND_COUNT`. Step 5c's `review_provenance()` reads that file, finds no round count, interprets the result as `rounds_completed=0`, and the `provenance_present and rounds_completed == 0` guard blocks the plan-block write. The issue is filed as `VALIDATE_STATUS=defects-found` with `VALIDATE_LOG_FILE=` (empty), which the SKILL.md heuristic currently misidentifies as a review-provenance refusal requiring a full `/design` re-run rather than a simple retry.

## Original report

After a `/design` run for issue #5154 completed 2 review rounds with all reviewer slots showing `done`, Step 5c returned `PUBLISH_RC=4`, `PLAN_WRITE_OK=false`, `VALIDATE_STATUS=defects-found`, `VALIDATE_DEFECT_COUNT=1`, `VALIDATE_LOG_FILE=` (empty), `DESIGNED_ADMISSION_READY=false`. The SKILL.md heuristic (empty `VALIDATE_LOG_FILE` + `VALIDATE_MISSING_SCRIPT_COUNT=0`) led to a "review-provenance refusal" interpretation and prompted a Fix-and-retry re-running the review panel.

## Reproduction scenario

1. Run `/design <issue>` against a repo where the plan is clean and reviewers return empty or very-low-content findings across 2 rounds.
2. Panel exits with `LOOP_STATUS=zero-findings-degraded-panel`, `TALLY_PLAN_REVIEW_STATUS=ok`, `ACCEPTED_COUNT=0`, `AGGREGATOR_STATUS=insufficient-input`.
3. Step 5c is invoked.
4. `review_provenance()` reads `.step3-review-result.env`, finds no `ROUNDS_COMPLETED` or `REVIEW_ROUND_COUNT` key, returns `rounds_completed=0`.
5. The `provenance_present and rounds_completed == 0` guard fires; publish is blocked.

## Expected behavior

Step 5c should accept the review result from a `zero-findings-degraded-panel` path where `TALLY_PLAN_REVIEW_STATUS=ok` and at least one round launched. `ROUNDS_COMPLETED` should reflect the actual round count (2 in the reproduction above), and the provenance guard should not block.

## Observed behavior

`.step3-review-result.env` for `zero-findings-degraded-panel` contains:

```
LOOP_STATUS=zero-findings-degraded-panel
PANEL_PRUNED_EMPTY=false
TALLY_PLAN_REVIEW_STATUS=ok
ACCEPTED_COUNT=0
DEGRADED_PANEL=0
DEGRADED_PANEL_WARNING=
INVALID_SLOT_PANEL_WARNING=
REASON=zero-findings-degraded-panel
```

`ROUNDS_COMPLETED` and `REVIEW_ROUND_COUNT` are absent. `review_provenance()` returns `rounds_completed=0`, triggering the provenance block and returning `PUBLISH_RC=4` with the misleading `VALIDATE_STATUS=defects-found` envelope.

## Root cause analysis

In `python/plan_review.py`, the `zero-findings-degraded-panel` branch writes the result env at line 1989-2001 (the `phase_driver_write_result_env` call inside `run_step3_review`'s `while True:` loop). That call only includes:

```python
("LOOP_STATUS", "zero-findings-degraded-panel"),
("PANEL_PRUNED_EMPTY", ...),
("TALLY_PLAN_REVIEW_STATUS", ...),
("ACCEPTED_COUNT", ...),
("DEGRADED_PANEL", ...),
("DEGRADED_PANEL_WARNING", ...),
("INVALID_SLOT_PANEL_WARNING", ...),
("REASON", ...),
```

`ROUNDS_COMPLETED` and `REVIEW_ROUND_COUNT` are absent from this list. Every other terminal path that exits via `step3_loop_persist_envelope` / `step3_loop_emit_envelope` includes them (lines 812, 817). The `zero-findings-degraded-panel` terminal exit at lines 2090-2103 also omits them from its stdout emission.

`review_provenance()` in `design_publish.py` (line 102) reads `rounds_raw` only from `ROUNDS_COMPLETED` and `REVIEW_ROUND_COUNT`. When both are absent, `rounds = 0`. The check at line 232 (`provenance_present and rounds_completed == 0`) fires and blocks the publish.

Additionally, the `normalize_step3_status_main` function (via `_step3_overlay_stdout_env`) does eventually reconstruct `ROUNDS_COMPLETED=2` into the envelope it emits to the task output — but it uses the overlay from the pre-written result env and the stdout file. Since the stdout file from the inner loop also omits `ROUNDS_COMPLETED` on this path, the overlay relies on `_read_count(tmpdir)` or `review-round-count.txt` indirectly. The durable `.step3-review-result.env` is never updated to include the round count.

## Evidence

- `python/plan_review.py` line 1989-2001: `phase_driver_write_result_env` for `zero-findings-degraded-panel` does not include `ROUNDS_COMPLETED` or `REVIEW_ROUND_COUNT`.
- `python/plan_review.py` lines 806-817: `step3_loop_persist_envelope` always writes both keys — but is never called on the `zero-findings-degraded-panel` terminal path.
- `python/plan_review.py` lines 2090-2103: terminal `degraded_exit` branch emits KV to stdout without `ROUNDS_COMPLETED`.
- `python/design_publish.py` line 102: `rounds_raw = kv.get("ROUNDS_COMPLETED", "") or kv.get("REVIEW_ROUND_COUNT", "")` — both absent → `rounds_raw = ""` → `rounds = 0`.
- `python/design_publish.py` line 232: `elif provenance_present and rounds_completed == 0:` blocks the publish.
- Observed `.step3-review-result.env` for the session: confirms `ROUNDS_COMPLETED` absent.
- `review-round-count.txt` in the session: value `3` (updated by the retry), confirming rounds did execute.

## Affected files

- `python/plan_review.py` — the `phase_driver_write_result_env` call at line 1989-2001 and the terminal `degraded_exit` stdout path at lines 2090-2103 need `ROUNDS_COMPLETED` / `REVIEW_ROUND_COUNT`.
- `python/design_publish.py` — `review_provenance()` could also be made more resilient by falling back to `review-round-count.txt` when both keys are absent, as a defense-in-depth layer.

## Suggested fix(es)

**Primary (plan_review.py):** Add `ROUNDS_COMPLETED` and `REVIEW_ROUND_COUNT` to the `phase_driver_write_result_env` call at lines 1989-2001. At that call site, `round_num` holds the last-completed round number and is an appropriate value. Also add both keys to the terminal stdout emission at lines 2092-2102 (emit them from `degraded_values` or derive from `round_num`).

**Defense-in-depth (design_publish.py):** In `review_provenance()`, when both `ROUNDS_COMPLETED` and `REVIEW_ROUND_COUNT` are absent from the result env, fall back to reading `review-round-count.txt` (via `_read_count(design_tmpdir)` pattern). This prevents a repeat failure if another path forgets to include the round count.

**SKILL.md heuristic:** The current "empty `VALIDATE_LOG_FILE` = review-provenance refusal" heuristic is correct for the provenance block path but incorrectly routes this case to "re-run `/design` from Step 3" rather than "investigate". The heuristic itself may not need changing, but the confusing side-effect of treating a round-count gap as a validator defect warrants a note in the SKILL.md Step 5c section.

## Open questions

- Should `review_provenance()` also read `review-round-count.txt` as a fallback for all paths, or only when the result env status is "ok" (from `TALLY_PLAN_REVIEW_STATUS`)?
- Should the `zero-findings-degraded-panel` inline write use `round_num` or the value from `_read_count(tmpdir)` for `ROUNDS_COMPLETED`? They may differ by 1 depending on when `review-round-count.txt` was last written.

## Test plan
(no test plan section in plan-file)
