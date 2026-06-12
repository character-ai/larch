# test-dispatch-panel.sh Contract

Regression harness for `skills/review/scripts/dispatch-panel.sh`.

It uses stub Claude/external launchers and a scout-launch stub to verify:

- `--panel simple` with plan file launches the static panel for each available vendor. Plan file is required (absent → exit 2).
- `--panel hard` with plan file launches the same per-available-vendor static layout. Plan file is required (absent → exit 2).
- `--dynamic-archetypes 0` preserves the static manifest, while `--dynamic-archetypes 3` appends Cursor + Codex dynamic `prompt_file` twins when both vendors are available and emits `STATIC_SLOT_COUNT=6`, `DYNAMIC_SLOTS=6`, `SLOT_COUNT=12`.
- `--dynamic-archetypes 3` (the max) appends 6 dynamic rows when both vendors are available and emits `STATIC_SLOT_COUNT=6`, `DYNAMIC_SLOTS=6`, `SLOT_COUNT=12`.
- Empty scout output and scout failure keep the static panel and emit the relevant `SCOUT_STATUS`.
- Scout launches persist `scout-round<round>-status.env`, and reuse prefers that sidecar over deriving `SCOUT_STATUS` from an empty manifest.
- Three scout-parse-failed regression tests verify the test-harness path guard: (1) env-isolation asserts the parent `LARCH_EXECUTION_ISSUES_LOG` is not written when `REVIEW_TMPDIR` is under a `test-dispatch-panel.*` ancestor; (2) path-guard asserts the local diag sidecar is written while the parent issues-log is suppressed; (3) prod-shape asserts both the diag sidecar and the issues-log are written when `REVIEW_TMPDIR` is outside any harness ancestor.
- Invalid dynamic counts (`4`, `9`, `-1`, `abc`) exit 2.
- A set-but-empty `LARCH_DYNAMIC_ARCHETYPES_MAX` in the process environment is ignored (treated like unset): the run succeeds with the default cap `0` (`SCOUT_STATUS=na`, `DYNAMIC_SLOTS=0`), matching `review-and-fix.sh` / `test-review-and-fix.sh`.
- both-down external availability emits Cursor-primary static rows that fall through to Claude phase-3 outputs; single-vendor runs omit global `--no-fallback`, while both-vendor runs in rounds 1–2 pass `--no-fallback` (round 3+ omits it so dropped Cursor slots can backfill — #4060) and forward any `DROPPED_SLOTS_FILE`.
- Round-3 Codex gating (#4060): with both vendors available, round 3 emits Cursor-only static rows (no Codex outputs, breadcrumb shows 0 Codex static) and suppresses dynamic Codex twins; with Cursor unavailable, round 3 emits the Codex replacement panel (Codex static rows plus Codex-only dynamic slots, breadcrumb shows 0 Cursor static).
- Both panels always include `reviewer-testing` with the folded plan-fidelity secondary scan; no conditional based on plan file presence.

Run with `bash skills/review/scripts/test-dispatch-panel.sh` or `make test-dispatch-panel`.
