## Decision 1: Counter scope
- **Question**: Should the new counter cover ONLY the `reuse_slot_result` fall-through path, or ALSO the normal phase-2 ungrouped alt-tool swap?
- **Resolution**: Only the `reuse_slot_result` fall-through (line 501→505 in `scripts/dispatch-with-waterfall.sh`). Normal phase-2 swap is the documented waterfall behavior and stays unmeasured.
- **Source**: user

## Decision 2: Threshold wiring
- **Question**: How should the new counter feed `LARCH_FALLBACK_CLAUDE_WARN_THRESHOLD`?
- **Resolution**: Sum into `FALLBACK_COUNT` (combined total triggers the threshold warning) AND emit a separate `PHASE2_RELAUNCH_COUNT` KV for operator visibility.
- **Source**: user
