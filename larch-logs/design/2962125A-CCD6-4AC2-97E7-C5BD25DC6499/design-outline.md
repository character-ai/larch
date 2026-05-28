## Proposed Design Outline

### Goals
- Make design-phase degradation reasoning see the same combined fall-through count that the dispatcher's WARN already uses, eliminating the invariant gap from issue #3097.
- Add the two `test-dispatch-with-waterfall.sh` scenarios called out in Item B (multi-fall-through `PHASE2_RELAUNCH_COUNT=2` and `--fallback-counter-file` combined-sum persistence).
- Extend one existing harness scenario with an `agent_file` slot fixture and stub-launcher argv assertion (Item C).

### Non-goals
- No changes under `skills/review/scripts/` — review-path code reasons from `DISPATCH_OK`, not `FALLBACK_COUNT`, so its docs and code stay byte-identical.
- No refactor of the `dispatch-with-waterfall.sh` waterfall phases beyond the new KV emit.
- No backward-incompatible change to existing stdout keys (`FALLBACK_COUNT`, `PHASE2_RELAUNCH_COUNT` retained as-is; `COMBINED_FALLBACK_COUNT` is purely additive).

### Approach sketch
- Add one `emit_kv COMBINED_FALLBACK_COUNT "$combined_fallback"` line in `scripts/dispatch-with-waterfall.sh` next to the existing `FALLBACK_COUNT` / `PHASE2_RELAUNCH_COUNT` emits, reusing the existing `combined_fallback` local.
- In each of `skills/design/scripts/dispatch-plan-review-panel.sh`, `skills/design/scripts/plan-review-loop.sh`, and `skills/design/scripts/decompose-panel-dispatch.sh`: add `COMBINED_FALLBACK_COUNT` to the parse `case` and swap the `(( 10#$FALLBACK_COUNT > floor_half ))` comparison to use the combined value (default to `FALLBACK_COUNT` when the new KV is absent for older waterfall callers — defensive but minimal).
- Append three new assertion blocks to `scripts/test-dispatch-with-waterfall.sh`: (i) two phase-2 CP-stub failures in one grouped batch → `PHASE2_RELAUNCH_COUNT=2` + `COMBINED_FALLBACK_COUNT=<expected>`; (ii) `--fallback-counter-file` with phase-2 + phase-3 fallback → persisted file equals combined sum; (iii) extend one existing scenario whose slot fixture has `prompt_file` only to also include `agent_file`, asserting the stub launcher argv contains both.

### Surfaces in scope
- `scripts/dispatch-with-waterfall.sh` and `scripts/dispatch-with-waterfall.md` (new KV + doc bullet).
- `skills/design/scripts/dispatch-plan-review-panel.sh` and `.md` (parse + degradation swap + doc bullet).
- `skills/design/scripts/plan-review-loop.sh` and `.md` (parse + degradation swap + doc bullet).
- `skills/design/scripts/decompose-panel-dispatch.sh` and `.md` (parse + degradation swap + doc bullet).
- `scripts/test-dispatch-with-waterfall.sh` (3 assertion blocks).

### Open questions
- None.
