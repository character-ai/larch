# test-dispatch-panel.sh Contract

Regression harness for `skills/review/scripts/dispatch-panel.sh`.

It uses stub Claude/external launchers and a scout-launch stub to verify:

- `--panel simple` with plan file launches 6 Cursor specialists + 1 Codex generalist = 7 slots. Plan file is required (absent → exit 2).
- `--panel hard` with plan file launches 6 Cursor specialists + 6 Codex specialists = 12 slots. Plan file is required (absent → exit 2).
- `--dynamic-archetypes 0` preserves the static manifest, while `--dynamic-archetypes 4` appends 4 Cursor-primary `prompt_file` slots and emits `STATIC_SLOT_COUNT=12`, `DYNAMIC_SLOTS=4`, `SLOT_COUNT=16`.
- Empty scout output and scout failure keep the static panel and emit the relevant `SCOUT_STATUS`.
- Invalid dynamic counts (`5`, `-1`, `abc`) exit 2.
- both-down external availability falls through to Claude phase-3 outputs.
- Both panels always include plan-fidelity; no conditional based on plan file presence.

Run with `bash skills/review/scripts/test-dispatch-panel.sh` or `make test-dispatch-panel`.
