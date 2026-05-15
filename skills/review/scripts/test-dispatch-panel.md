# test-dispatch-panel.sh Contract

Regression harness for `skills/review/scripts/dispatch-panel.sh`.

It uses stub Claude and external-review launchers to verify:

- both-down branch emits `PANEL_MODE=both-down`, preserves `PANEL_SHAPE=hard`, launches zero slots.
- `--panel simple` with plan file launches 6 Cursor specialists + 1 Codex generalist = 7 slots. Plan file is required (absent → exit 2).
- `--panel hard` with plan file launches 6 Cursor specialists + 6 Codex specialists = 12 slots. Plan file is required (absent → exit 2).
- Both panels always include plan-fidelity; no conditional based on plan file presence.

Includes a stdout size cap assertion (≤2 KB).

Run with `bash skills/review/scripts/test-dispatch-panel.sh` or `make test-dispatch-panel`.
