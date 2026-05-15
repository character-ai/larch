# test-dispatch-panel.sh Contract

Regression harness for `skills/review/scripts/dispatch-panel.sh`.

It uses stub Claude and external-review launchers to verify:

- both-down branch emits `PANEL_MODE=both-down`, preserves `PANEL_SHAPE=hard`, launches one slot, and writes the expected sentinel.
- `--panel simple` launches Cursor `edge-cases`, Codex `structure`, and Claude generic.
- `--panel simple` adds `plan-fidelity` for each external tool only when `--plan-file` exists.
- `--panel hard` launches all six specialists for each available external tool (no Claude generic slot).

Includes a stdout size cap assertion (≤2 KB).

Run with `bash skills/review/scripts/test-dispatch-panel.sh` or `make test-dispatch-panel`.
