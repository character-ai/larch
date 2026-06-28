## Goal
Implement issue #5695: [IMPLEMENTING] [BUG] Step 6 missing step-5c status sidecar after premature task notification.

## Implementation Plan
## Summary

After a successful `/design` run (PUBLISH_OK=true, PLAN_WRITE_OK=true), Step 6 emits "missing Step 5c status sidecar" and preserves `$DESIGN_TMPDIR` instead of cleaning up. The root cause is a premature `<task-notification>` from `design-step5c.sh`: the harness fires a "completed" notification when the Python process flushes its contract-stream KVs, while `_step5c_render_final_summary` and the outer `finally` (which write `final-summary.md` and `.completed/step-5c-terminal`) are still executing. The orchestrator's one-probe recovery finds the sentinel absent, then proceeds to Step 6, which finds the sidecar absent because the process is still writing it. Both artifacts appear on disk after the process eventually exits.

## Original report

`⚠ Step 6: missing step-5c status sidecar`

Observed during a `/design 5667` run after Gate C approval. Step 6 prelude printed:
```
**ℹ Step 6 prelude: missing Step 5c status sidecar; skipping step-5d write.**
STEP6_PRELUDE_STATUS=skipped
**ℹ Step 6: missing Step 5c status sidecar; preserving $DESIGN_TMPDIR for recovery.**
CLEANUP_STATUS=preserved
```

The design publish had already succeeded (PUBLISH_OK=true was in the `<task-notification>` output). The `$DESIGN_TMPDIR` was left on disk instead of being cleaned up.

## Reproduction scenario

1. Run `/design <issue-number>` through Gate C approval.
2. The `design-step5c.sh` background task fires a "completed" `<task-notification>` while `_step5c_render_final_summary` is still running.
3. The orchestrator performs its one-probe recovery; `.completed/step-5c-terminal` is absent.
4. The orchestrator proceeds to Step 6 before the Python process exits.
5. Step 6 (`step6_cleanup_core`) checks for `.design-step5c-status.env`; the file may still be in the process of being written or may not be visible yet.
6. Step 6 emits "missing Step 5c status sidecar" and preserves `$DESIGN_TMPDIR`.

Observed post-hoc: both `.design-step5c-status.env` and `.completed/step-5c-terminal` exist with timestamps matching the moment the process eventually finished. A stale `<task-notification>` for the same `bhzgizb3f` background task arrived much later (during the next user interaction), confirming the process was still running when the orchestrator processed the first "completed" notification.

## Expected behavior

Step 6 should only run after `.completed/step-5c-terminal` is confirmed present. When a premature notification fires:
- The sentinel is absent → wait for a real "process exited" notification.
- OR: Step 6 should use `_step6_in_flight` logic (which checks for `.bg-wait-active`) to detect the in-flight state and refuse to proceed.

## Observed behavior

Step 6 runs while `design-step5c.sh` is still executing. `_read_step5c_status_sidecar` returns an empty dict (file absent or being written), `_step6_cleanup_core` emits the "missing sidecar" message, and `CLEANUP_STATUS=preserved`.

## Root cause analysis

Two related issues may be interacting:

1. **Premature notification**: The `run_in_background` harness fires a "completed" `<task-notification>` when the Python process flushes stdout (via `_emit_core_kvs` at `design_lifecycle.py:4613`), before the outer `finally` block at line 4629 writes `.completed/step-5c-terminal`. The `_bg_wait_marker_context` (STEP=design-step5c) removes `.bg-wait-active` only after the `with` block exits (after line 4622 `return 0, []`), so the in-flight guard is still active — but the orchestrator's recovery only probes the terminal sentinel, not `.bg-wait-active`.

2. **Recovery protocol gap**: After a premature notification + absent sentinel, the SKILL.md allows one foreground probe. If the sentinel is absent, it says "end the turn without probing." But the orchestrator may continue to Step 6 in the same turn before the process exits. Step 6 then races with the background process for the sidecar file.

The `.design-step5c-status.env` sidecar is written at `design_lifecycle.py:4589`, before `_emit_core_kvs` at line 4613. So it should be on disk before the notification fires. The gap is specifically with `.completed/step-5c-terminal` (outer `finally`, line 4631).

## Evidence

- `step6_cleanup_core` (`design_lifecycle.py:4770-4773`): checks `sidecar.is_file()` before `_step6_in_flight`; if sidecar is absent, emits "missing sidecar" message.
- `step6_prelude_core` (`design_lifecycle.py:4720-4723`): same absent-sidecar check with same message.
- `_bg_wait_marker_context` writes `.bg-wait-active` at entry and removes it at exit (`design_lifecycle.py:172-201`).
- Outer `finally` at line 4629 writes `.completed/step-5c-terminal` only when `write_terminal_sentinel=True`.
- `write_terminal_sentinel` is set to `True` after env rehydration (line 4506), before the `_bg_wait_marker_context` block.
- The stale second notification for the same task arrived after the next user message, confirming the process outlived the first "completed" signal.

## Affected files

- `python/larch/design/design_lifecycle.py` — `step5c_core`, `step6_prelude_core`, `step6_cleanup_core`, `_step6_in_flight`
- `skills/design/SKILL.md` — Step 5c notification-wait and one-probe recovery contract

## Suggested fix(es)

**Option A** (preferred, minimal): In `step6_prelude_core` and `step6_cleanup_core`, check `_step6_in_flight` BEFORE the sidecar check. If in-flight (`.bg-wait-active` present and sidecar absent), emit a wait-required diagnostic and return non-zero so the orchestrator does not proceed. Currently `_step6_in_flight` is not called in `step6_prelude_core` or `step6_cleanup_core` — the in-flight guard only emits when `.bg-wait-active` is present AND sidecar is absent, which is the exact condition at the time Step 6 runs.

Wait, looking at the code again: `step6_cleanup_core` at line 4767-4773 DOES check `_step6_in_flight` first, and if true, emits a warning and returns 1. But `_step6_in_flight` returns False when the sidecar IS present. If the sidecar is absent AND `.bg-wait-active` is absent (because the process exited but sidecar write failed), it also returns False. In the observed case, `.bg-wait-active` may have been removed before Step 6 ran (if the context manager exited before the outer finally ran and Step 6 started).

**Option B**: After the one-probe recovery shows sentinel absent, check `.bg-wait-active` in the same probe. If `.bg-wait-active` is present (STEP=design-step5c), do not proceed to Step 6 in the same turn.

**Option C**: Move `_step5c_write_status` to run AFTER `_step5c_render_final_summary` and before the outer `finally`. This way the notification fires AFTER the sidecar is durably on disk. The outer finally still writes the terminal sentinel last.

## Open questions

- Is the "completed" notification truly premature (fires on stdout flush, not on process exit), or is there a different explanation?
- Does the `_bg_wait_marker_context` context manager exit BEFORE the outer `finally` runs? If so, `.bg-wait-active` may be absent when Step 6 runs, making `_step6_in_flight` return False even though the process hasn't written the terminal sentinel yet.
- Is Option A's `_step6_in_flight` check already present but ineffective because `.bg-wait-active` is removed before Step 6 starts?

## Test plan
(no test plan section in plan-file)
