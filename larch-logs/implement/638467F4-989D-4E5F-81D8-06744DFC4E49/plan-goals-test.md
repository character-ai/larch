## Goal
Implement issue #5047: [IMPLEMENTING] [BUG] panel-failed stall: _write_drops skipped when waterfall runs without --no-fallback, straggler-dropped static reviewer not excused by coverage gate.

## Implementation Plan
## Summary

When a static reviewer (e.g. `cursor-specialist-correctness`) is straggler-dropped in a waterfall dispatch that runs without `--no-fallback`, `agent_waterfall.py` silently skips writing the dropped-slots file (line 926 gates `_write_drops` on `opts.no_fallback`). `review_core` never receives a `DROPPED_SLOTS_FILE` path, so `_straggler_excused_static_slugs` returns an empty set, and the coverage gate fails with `COVERAGE_GATE_OK=false` for the missing required archetype — producing a spurious `panel-failed` stall even though the straggler drop was a normal transient event.

## Original report

In a Step 5 code review run (round 3 of 3), `cursor-specialist-correctness` was killed by the adaptive straggler deadline (exit code -9, 0-byte output). The coverage gate detected no successful reviewer for the required `correctness` archetype and emitted `REVIEW_CORE_STATUS=panel-failed`, stalling the `/implement` run. The two prior rounds completed successfully with 14/23 accepted findings total, and round-3's three surviving reviewers found 0 new in-scope findings (consistent with a complete review). Only the missing dropped-slots file caused the stall.

## Reproduction scenario

1. Run `/implement` on a large diff that triggers a 3-round review.
2. In a later round, the waterfall is dispatched in fallback mode (without `--no-fallback`).
3. A required static reviewer (e.g. `correctness`) runs past the adaptive straggler deadline and is killed.
4. `_write_drops` is skipped because `opts.no_fallback=False`.
5. `review_core` gets `DROPPED_SLOTS_FILE=""`.
6. Coverage gate fails → `panel-failed` stall.

The round-1 waterfall dispatch in the same run used `--no-fallback` (confirmed: dropped-slots file exists and lists `correctness`, `edge-cases`, `testing` as straggler-dropped; coverage gate correctly excused them). Round-3's dispatch did not use `--no-fallback`.

## Expected behavior

When a static reviewer is straggler-dropped, the dropped-slots file is written regardless of whether `--no-fallback` is active. The coverage gate excuses the straggler-dropped archetype, and the review round proceeds with the surviving reviewers (or degrades cleanly). A complete review that produced 0 new findings in the final round should converge to `complete` or `cap-hit`, not `panel-failed`.

## Observed behavior

- `agent_waterfall.py` line 926: `if opts.no_fallback and any(drop.reason for drop in drops): dropped_slots_file = _write_drops(...)` — the `opts.no_fallback` guard prevents the file from being written in non-no-fallback mode.
- `review-core-dispatch.env` has no `DROPPED_SLOTS_FILE` key.
- `review_pipeline.py` line 2148: `dropped = dispatch.get("DROPPED_SLOTS_FILE", "")` → empty string.
- `_straggler_excused_static_slugs(Path(""))` returns `set()` immediately (file doesn't exist).
- `_static_coverage_reason` finds `correctness` in `expected` but not in `success` and not in `excused`.
- `COVERAGE_GATE_OK=false`, `COVERAGE_GATE_REASON=no successful static reviewer for archetype(s): correctness`.
- `REVIEW_CORE_STATUS=panel-failed` → stall.

## Root cause analysis

**Location**: `python/agent_waterfall.py` line 926.

```python
if opts.no_fallback and any(drop.reason for drop in drops):
    dropped_slots_file = _write_drops(resolved_paths_file, slots, final_outputs, drops)
```

The `opts.no_fallback` guard is the root cause. Its original intent was likely to write drops only for the waterfall variant that doesn't have fallbacks (making drops more meaningful). But this means that when the same waterfall function is invoked in fallback mode (e.g. for Cursor-primary dispatch with Claude fallbacks), straggler drops are tracked internally in the `drops` list but never persisted to disk. The downstream coverage gate (`_static_coverage_reason` in `review_pipeline.py` lines 1785-1820) depends entirely on the dropped-slots file to excuse straggler-dropped required archetypes.

The result: a straggler-dropped required-archetype reviewer causes `panel-failed` specifically in rounds where the waterfall runs in non-no-fallback mode, while the identical scenario in no-fallback mode (round-1 in the same run) succeeds silently.

## Evidence

- `round-3/cursor-specialist-correctness-output.txt`: 0 bytes (straggler killed before writing output).
- `round-3/cursor-specialist-correctness-output.txt.done`: `-9` (SIGKILL from `_terminate_launch`; consistent with `_finish_launch` writing `rc if rc is not None else -signal.SIGTERM`).
- `round-3/cursor-specialist-correctness-output.txt.launch-stderr`: shows "still running" at 7m elapsed; round ended at 7m52s.
- `round-3/review-core-threshold.env`: `THRESHOLD_OK=true` (threshold passed), `COVERAGE_GATE_OK=false`, `COVERAGE_GATE_REASON=no successful static reviewer for archetype(s): correctness`.
- `round-3/collector-results.env`: only 3 entries (correctness absent entirely).
- `round-3/review-core-dispatch.env`: no `DROPPED_SLOTS_FILE` key.
- `round-1/panel-manifest.ndjson.output-files.dropped-slots` EXISTS and contains `correctness	cursor	straggler-dropped	cut at adaptive straggler deadline` — confirming round-1's no-fallback dispatch wrote the file and the coverage gate excused correctness there.
- `agent_waterfall.py` line 926: confirms the `opts.no_fallback` guard.
- `agent_waterfall.py` line 954: `if dropped_slots_file: logging_util.emit_kv("DROPPED_SLOTS_FILE", dropped_slots_file)` — only emits when file was written.

## Affected files

- `python/agent_waterfall.py` — line 926: the `opts.no_fallback` guard on `_write_drops`; the fix belongs here.
- `python/review_pipeline.py` — lines 1769-1782 (`_straggler_excused_static_slugs`), 1785-1820 (`_static_coverage_reason`): consumers of the dropped-slots file; no change needed if the file is always written.
- `python/test_review_pipeline.py` — contains `test_review_core_static_coverage_excuses_straggler_dropped_archetype` (line ~1277 based on slowest-durations output); may need a new test for non-no-fallback dispatch.

## Suggested fix(es)

**Primary fix (minimal change)**: Remove the `opts.no_fallback` guard from `_write_drops` in `agent_waterfall.py`:

```python
# Before (line 926):
if opts.no_fallback and any(drop.reason for drop in drops):
    dropped_slots_file = _write_drops(resolved_paths_file, slots, final_outputs, drops)

# After:
if any(drop.reason for drop in drops):
    dropped_slots_file = _write_drops(resolved_paths_file, slots, final_outputs, drops)
```

This ensures the dropped-slots file is always written when there are drops, regardless of fallback mode. The downstream `DROPPED_SLOTS_FILE` emission (line 954) is already gated on `if dropped_slots_file:` so it won't emit an empty path on no-drop runs.

**Test coverage**: Add a test to `test_review_pipeline.py` that covers the case where a static reviewer is straggler-dropped in a non-no-fallback waterfall dispatch — confirming the coverage gate excuses it when the dropped-slots file is present.

**Alternative (secondary fix, if no-fallback guard must stay)**: If the `opts.no_fallback` guard is intentional for non-straggler drops, narrow it to always write when there are straggler drops specifically:

```python
straggler_drops = any(d.reason == "straggler-dropped" for d in drops)
if (opts.no_fallback and any(drop.reason for drop in drops)) or straggler_drops:
    dropped_slots_file = _write_drops(resolved_paths_file, slots, final_outputs, drops)
```

The primary fix is preferred for simplicity.

## Open questions

- Why does the review-core dispatch use `--no-fallback` in some rounds (round-1) but not others (round-3)? Understanding this may reveal additional panel-dispatch configurations that are silently not writing drops. Is the switch tied to the static-slot count, the prune status (`active-dropped`), or a waterfall configuration in `_dispatch_panel`?
- Should `_write_drops` be renamed or its behavior documented more explicitly to reflect that it only runs in certain modes? The current conditional is easy to misread as "only write if there are drops."

## Test plan
(no test plan section in plan-file)
