## Proposed Design Outline

### Goals
- Prevent `set -e` from aborting the dispatcher when `reuse_slot_result` cannot copy a stale source file.
- Fall through to the existing relaunch path (phase-2 `launch_slot`) when reuse is not possible.
- Add regression coverage that locks the new behavior into the existing harness.

### Non-goals
- Do not audit or modify other `cp` calls in the dispatcher.
- Do not change PR #2962's ledger-truncation logic.
- Do not prune or rewrite the group ledger TSV on reuse failure.

### Approach sketch
- Modify `reuse_slot_result` in `scripts/dispatch-with-waterfall.sh` so any `cp` failure returns non-zero instead of aborting under `set -e`; clear partial sidecar / ledger state on the failed branch so a subsequent relaunch is clean.
- Update the single caller at line 499 to detect that non-zero return and fall through to `launch_slot` in phase 2 (the existing relaunch path) instead of `continue`.
- Add a regression case to `scripts/test-dispatch-with-waterfall.sh` that injects a group ledger row whose `output_path` points at a deleted file and asserts the second grouped slot relaunches successfully.
- Update sibling `scripts/dispatch-with-waterfall.md` to document the reuse-failure fallback behavior in the grouped-dedup section.

### Surfaces in scope
- `scripts/dispatch-with-waterfall.sh` — function `reuse_slot_result` and its single caller at the phase-2 grouped loop.
- `scripts/dispatch-with-waterfall.md` — grouped-dedup section.
- `scripts/test-dispatch-with-waterfall.sh` — append one new test scenario.

### Open questions
- None.
