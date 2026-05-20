# test-dispatch-panel.sh Contract

Regression harness for `skills/review/scripts/dispatch-panel.sh`.

It uses stub Claude/external launchers and a scout-launch stub to verify:

- `--panel simple` with plan file launches 6 Cursor specialists. Plan file is required (absent → exit 2).
- `--panel hard` with plan file launches the same 6 Cursor specialists. Plan file is required (absent → exit 2).
- `--dynamic-archetypes 0` preserves the static manifest, while `--dynamic-archetypes 4` appends 4 Cursor-primary `prompt_file` slots and emits `STATIC_SLOT_COUNT=6`, `DYNAMIC_SLOTS=4`, `SLOT_COUNT=10`.
- `--dynamic-archetypes 8` appends 8 Cursor-primary `prompt_file` slots and emits `STATIC_SLOT_COUNT=6`, `DYNAMIC_SLOTS=8`, `SLOT_COUNT=14`.
- Empty scout output and scout failure keep the static panel and emit the relevant `SCOUT_STATUS`.
- Scout launches persist `scout-round<round>-status.env`, and reuse prefers that sidecar over deriving `SCOUT_STATUS` from an empty manifest.
- Three scout-parse-failed regression tests verify the test-harness path guard: (1) env-isolation asserts the parent `LARCH_EXECUTION_ISSUES_LOG` is not written when `REVIEW_TMPDIR` is under a `test-dispatch-panel.*` ancestor; (2) path-guard asserts the local diag sidecar is written while the parent issues-log is suppressed; (3) prod-shape asserts both the diag sidecar and the issues-log are written when `REVIEW_TMPDIR` is outside any harness ancestor.
- Invalid dynamic counts (`9`, `-1`, `abc`) exit 2.
- A set-but-empty `LARCH_DYNAMIC_ARCHETYPES_MAX` in the process environment is ignored (treated like unset): the run succeeds with the default cap `0` (`SCOUT_STATUS=na`, `DYNAMIC_SLOTS=0`), matching `review-and-fix.sh` / `test-review-and-fix.sh`.
- both-down external availability falls through to Claude phase-3 outputs.
- Both panels always include plan-fidelity; no conditional based on plan file presence.

Run with `bash skills/review/scripts/test-dispatch-panel.sh` or `make test-dispatch-panel`.
