## Proposed Design Outline

### Goals
- Account `reuse_slot_result` fall-through phase-2 relaunches in `dispatch-with-waterfall.sh` cost metering.
- Trigger `WARN=cost-fallback-exceeded-threshold` when the combined fallback spend (phase-2 fall-through + phase-3 Claude) crosses `LARCH_FALLBACK_CLAUDE_WARN_THRESHOLD`.
- Surface the new phase-2 count as a distinct KV so operators can see the two cost sources separately.

### Non-goals
- Counting normal phase-2 ungrouped alt-tool swaps (line 471) — that path is documented waterfall behavior, not unexpected spend.
- Introducing a sibling `LARCH_PHASE2_RELAUNCH_WARN_THRESHOLD` knob.
- Refactoring the phase 2 grouped-fallback architecture or the `reuse_slot_result` helper itself.

### Approach sketch
- Add `phase2_relaunch_count=0` next to `fallback_count=0` in `scripts/dispatch-with-waterfall.sh`.
- Increment `phase2_relaunch_count` in the `reuse_slot_result` fall-through path, right before the `launch_slot "$idx" phase2 "$alt" "$out"` at ~line 508.
- Compute `combined_fallback=$((fallback_count + phase2_relaunch_count))`; use that combined total for the threshold check and for the `FALLBACK_COUNTER_FILE` persisted increment.
- Emit a new `PHASE2_RELAUNCH_COUNT` KV alongside existing `FALLBACK_COUNT`; `FALLBACK_COUNT` retains the phase-3 Claude count to preserve historic semantic, the warning consumes the combined sum.
- Add a `test-dispatch-with-waterfall.sh` scenario that forces a `reuse_slot_result` failure → fall-through relaunch and asserts both new behaviors (KV emit + threshold-triggered WARN).

### Surfaces in scope
- `scripts/dispatch-with-waterfall.sh`
- `scripts/test-dispatch-with-waterfall.sh`
- `scripts/dispatch-with-waterfall.md` (sibling-doc sync per `script-md-siblings.md`)

### Open questions
- None.
