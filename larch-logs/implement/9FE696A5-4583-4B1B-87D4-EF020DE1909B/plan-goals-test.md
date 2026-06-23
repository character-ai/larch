## Goal
Implement issue #5238: [IMPLEMENTING] [BUG] deferred-commit transcript capture emits spurious Warnings entry on every normal run.

## Implementation Plan
## Summary

Every `/implement` run that uses the normal deferred-commit transcript path emits a spurious `Warnings` entry — "session transcript was written; commit deferred to caller" — in the final run summary. This is normal, expected behavior: Step 7a always defers the transcript git commit to the ship driver's `flush_logs_pre`. Because the warning fires on the success path of every run, it adds noise to the `## Exec Issues and Warnings` section and causes operators to investigate something that requires no action.

## Original report

this should not be a warning, since this is normal, expected behavior

## Reproduction scenario

Run any `/implement` workflow to completion with default flags. Observe the final run summary includes a `Warnings (N)` entry: `Step 7a — session-transcript status=captured: session transcript was written; commit deferred to caller.`

## Expected behavior

On the deferred-commit success path, no `Warnings` entry is appended. The status `SESSION_TRANSCRIPT_STATUS=captured` is emitted to stdout (for relay) but the execution-issues.md `Warnings` section receives no entry, matching the behavior of the non-deferred successful commit path.

## Observed behavior

The final run summary contains a spurious warning: `Step 7a — session-transcript status=captured: session transcript was written; commit deferred to caller.` This fires on every normal run because Step 7a always passes `--defer-commit true` to `run-log capture-transcript`.

## Root cause analysis

In `python/run_logs.py`, `capture_transcript_main()` handles the `defer_commit == "true"` success path (after the transcript is successfully written to the batch) by calling `_capture_transcript_emit()`. That helper unconditionally calls `_capture_transcript_append_warning()`, which appends to the `Warnings` section of `execution-issues.md`.

The non-deferred success path (line 2578) bypasses `_capture_transcript_emit` entirely and just prints `SESSION_TRANSCRIPT_STATUS=captured` directly — no warning appended.

The asymmetry: the deferred-commit path is the normal Step 7a path (`step_7a.py` always passes `--defer-commit true`), but it was routed through `_capture_transcript_emit` which was designed for error/degraded/informational paths. The `captured` status on the deferred path is a clean success, not an informational state warranting a warning.

## Evidence

- `python/run_logs.py` lines 2562–2568: the `defer_commit == "true"` success branch calls `_capture_transcript_emit(issues_log, ..., "captured", "session transcript was written; commit deferred to caller.")`.
- `python/run_logs.py` lines 2431–2439: `_capture_transcript_emit` always calls `_capture_transcript_append_warning`, which appends to `execution-issues.md` under `Warnings`.
- `python/run_logs.py` line 2578: non-deferred success path prints `SESSION_TRANSCRIPT_STATUS=captured` directly, no warning appended.
- `python/step_7a.py` lines 152–153: Step 7a always passes `--defer-commit true` to `capture-transcript`.
- Observed in run `631169B0-914E-475E-903E-D9781CBAF39E`: final summary shows `Warnings (2)`, one of which is the spurious transcript-captured entry.

## Affected files

- `python/run_logs.py` — `capture_transcript_main()`, the `defer_commit == "true"` success branch (lines 2562–2568)

## Suggested fix(es)

Replace the `_capture_transcript_emit` call in the `defer_commit == "true"` success branch with a direct `print("SESSION_TRANSCRIPT_STATUS=captured")` + `return 0`, matching the non-deferred success path:

```python
if args.defer_commit == "true":
    print("SESSION_TRANSCRIPT_STATUS=captured")
    return 0
```

A unit test asserting that `capture_transcript_main` with `--defer-commit true` on a successful transcript write does **not** append any `Warnings` entry to `execution-issues.md` would prevent regression.

## Open questions

- Should the `captured` status be renamed to `captured-deferred` on the deferred path to distinguish it from `captured` on the immediate-commit path, or is `captured` the right status in both cases? Currently the non-deferred success path also prints `SESSION_TRANSCRIPT_STATUS=captured` (line 2578), so using the same status on the deferred path is consistent.

## Test plan
(no test plan section in plan-file)
