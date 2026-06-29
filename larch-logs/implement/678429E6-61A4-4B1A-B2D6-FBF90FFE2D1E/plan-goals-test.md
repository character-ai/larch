## Goal
Implement issue #5836: [IMPLEMENTING] [BUG] round-meta.json not written after round_runner split — Gantt charts always missing from final report.

## Implementation Plan
## Summary

When an `/implement` run completes, the final report's `## Review Phase Detail` section always shows "No review rounds completed." and no Gantt charts are generated. The root cause is that `write_implement_round_meta` — which writes `round-meta.json` into each round dir — was dropped when `_run_round` was moved from `review_and_fix.py` to the new `round_runner.py` module in the #5770 split refactor. Without `round-meta.json`, `_completed_round_dirs()` returns empty for every run, suppressing all Gantt output.

## Original report

User observed: Gantt charts not shown in final report

## Reproduction scenario

Run any `/implement --merge` issue. The final run report (committed to `larch-logs/implement/<RUN_ID>/final-summary.md` and emitted between `---LARCH-SUMMARY-FINAL-BEGIN---` / `---LARCH-SUMMARY-FINAL-END---` markers at Step 17) will contain:

```
## Review Phase Detail

No review rounds completed.
```

...regardless of how many review rounds actually ran. No `### Round N reviewer timing` Gantt blocks appear.

## Expected behavior

When one or more review rounds complete, the final report should include a populated `## Review Phase Detail` section with:
- A per-round tally table showing accepted/rejected counts.
- `### Round N reviewer timing` ASCII bar charts (Gantt charts) for each completed round.

## Observed behavior

`## Review Phase Detail` always reads "No review rounds completed." after any `/implement` run. The Gantt charts never appear, even when `ROUNDS_COMPLETED=1` is emitted by the review loop.

## Root cause analysis

The call chain for Gantt generation is:

```
write_final_report()
  → render_implement_review_detail()   # python/larch/report/review_phase_detail.py
    → _render_phase_detail_best_effort()
      → render_phase_detail()           # python/larch/report/progress_report.py
        → _completed_round_dirs()       # filters by round-meta.json presence
          → if empty → "No review rounds completed."
          → if non-empty → build table + call _render_phase_gantt()
```

`_completed_round_dirs()` (progress_report.py) identifies completed round dirs by checking that `round-meta.json` exists in each round dir inside `larch-logs/implement/<RUN_ID>/`:

```python
candidates = [p for p in rounds_root.iterdir() if p.is_dir() and (p / "round-meta.json").is_file()]
```

`round-meta.json` is copied from `implement_tmpdir/round-N/` to `larch-logs/implement/<RUN_ID>/round-N/` by `flush_round_log_after_coder` (via `run-log write-round`). But `round-meta.json` must already exist in `implement_tmpdir/round-N/` before that copy runs.

**The dropped call:** Before the #5770 split refactor (commit `7a9187e56`), `_run_round` in `review_and_fix.py` contained:

```python
with contextlib.suppress(Exception):
    _ = progress_report.write_implement_round_meta(round_dir)
run_id = getattr(args, "run_id", "")
if run_id:
    flush_round_log_after_coder(...)
```

When `_run_round` was moved to `round_runner.py`, the `write_implement_round_meta` call was not carried over. The new `round_runner.py` calls `flush_round_log_after_coder` directly without writing `round-meta.json` first. Since `round-meta.json` never exists in `implement_tmpdir/round-N/`, it is never copied to the run-log, and `_completed_round_dirs()` always returns empty.

The test `test_implement_round_meta_write_failure_does_not_block_flush` in `python/tests/review/test_review_and_fix.py` still patches `write_implement_round_meta` but the function is no longer called in production code, so the patch is a no-op and the test is not covering the real regression.

## Evidence

- **Commit `7a9187e56`** (PR #5810, "Fixes #5770"): diff of `python/larch/review/review_and_fix.py` shows the `-` lines removing the `write_implement_round_meta` call that was present before the split, without corresponding `+` lines adding it to `round_runner.py`.
- **`python/larch/review/round_runner.py` lines 624-626** (current): `_run_round` ends with `_write_summary`, `flush_scout_manifest`, `flush_round_log_after_coder` — no `write_implement_round_meta` call.
- **`python/larch/report/progress_report.py` line 696**: `_completed_round_dirs` requires `round-meta.json`.
- **`python/larch/report/run_log_batch.py` line 427**: `round-meta.json` is in `_ROUND_ARTIFACT_ALLOW` (would be copied if it existed).
- **`python/tests/review/test_review_and_fix.py` line 1959**: `write_implement_round_meta` is patched but not reachable in `_run_round`, meaning the test gives false confidence.
- **Observed run (RUN_ID `64055B7F-8A79-4C63-8957-BF9D2E76EC72`)**: `ROUNDS_COMPLETED=1` in Step 5 envelope, but final report body contains "No review rounds completed." — consistent with a missing `round-meta.json`.
- **`python/larch/report/progress_report.py:write_implement_round_meta`**: The function exists and is correct; it is simply never called from `round_runner._run_round`.

## Affected files

- `python/larch/review/round_runner.py` — `_run_round` is missing the `write_implement_round_meta` call before `flush_round_log_after_coder`.
- `python/tests/review/test_review_and_fix.py` — the `test_implement_round_meta_write_failure_does_not_block_flush` test needs its monkeypatch target corrected from `review_and_fix.progress_report` to `round_runner` (which now owns `_run_round`) and the test body updated to confirm the write is actually reached in production code.

## Suggested fix(es)

**Fix A (primary):** Restore the `write_implement_round_meta` call in `round_runner._run_round`, just before the `flush_round_log_after_coder` call:

```python
# In python/larch/review/round_runner.py, inside _run_round(), before flush_round_log_after_coder:
from larch.report import progress_report  # add import at top of file

# ...existing _write_summary and flush_scout_manifest calls...
with contextlib.suppress(Exception):
    progress_report.write_implement_round_meta(round_dir)
flush_round_log_after_coder(impl_tmpdir=implement_tmpdir, run_id=..., round_num=round_num, round_dir=round_dir)
```

**Fix B (test):** Update `test_implement_round_meta_write_failure_does_not_block_flush` to:
1. Patch `round_runner.progress_report.write_implement_round_meta` (not `review_and_fix.progress_report`).
2. Assert the patched function is actually invoked (add a call-tracker to `failing_meta`).
3. Assert that `flush_round_log_after_coder` is still called despite the failure.

Both fixes belong in the same PR.

## Open questions

- Should the `contextlib.suppress(Exception)` be preserved, or should the writer log a warning on failure? The original pre-split code used `suppress` silently; a warning to `_err()` or an execution-issue entry would improve observability. This is a design call for the implementer.
- Does this regression affect `/design` review rounds? `/design` uses `_write_design_round_meta` (in `plan_review.py`), which is separate and unaffected.

## Test plan
(no test plan section in plan-file)
