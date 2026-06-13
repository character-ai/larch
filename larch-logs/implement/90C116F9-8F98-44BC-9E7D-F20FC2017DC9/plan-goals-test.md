## Goal
Implement issue #4230: [IMPLEMENTING] [BUG] (URGENT) when /implement is running ship-pr and I ask for progress report, I get back step 0.

## Implementation Plan
## Plan

## Approach

- Keep the change small.
- Make ship-pr state-file presence drive ship-pr rendering.
- Stop filtering ship-pr reports through `SHIP_PR_PHASES`.
- Preserve the existing `phase = _kv_value(...)` read.
  - The Step 5 fallback still needs it for the `not phase` guard.
- Do not change `_render_ship_pr` output or ship-pr phase naming.

## Files to modify/create

### UPDATED: python/progress_report.py

- Remove the `SHIP_PR_PHASES` frozenset.
- In `_render_implement`, change:

  - From: render ship-pr only when `ship-pr-state.sh` exists and `PHASE` is in `SHIP_PR_PHASES`.
  - To: render ship-pr whenever `ship-pr-state.sh` exists.

- Leave `_render_ship_pr` unchanged.
- Leave the generic fallback unchanged.
- Leave Step 5 stale-mark inference unchanged.

### UPDATED: python/test_progress_report.py

- Add a regression test near existing ship-pr progress tests.
- Build a live implement run with:
  - an implement pointer,
  - a repo cwd,
  - an implement tmpdir,
  - `ship-pr-state.sh` containing an unlisted phase, for example `PHASE=bump`.
- Assert that `_report(str(cwd))` returns the ship-pr renderer output.
- Include at least:
  - `Ship-PR phase: bump`
- Optionally include `ITERATION` or `PR_NUMBER` only if useful.
- Do not depend on timing-ledger Step 0 output in this test, unless needed to prove the fallback no longer wins.

## Edge cases

- `ship-pr-state.sh` exists with an empty or missing `PHASE`.
  - Existing `_render_ship_pr` should display `Ship-PR phase: unknown`.
- `ship-pr-state.sh` exists while the latest timing mark is stale.
  - Ship-pr state should still win.
- `ship-pr-state.sh` is missing.
  - Existing Step 5 and generic behavior should remain unchanged.

## Failure modes

- If the file-existence check runs before Step 5 detection, an old stale `ship-pr-state.sh` can still win.
  - This matches the requested scope because the file indicates active ship-pr state.
- If a future ship-pr phase name changes, no progress-report code change should be needed.

## Testing strategy

- Run the targeted test file:

  `python3 -m pytest python/test_progress_report.py`

- If time permits, run the repository Python checks used by this area:

  `make py-test`

- Do not update docs or `SECURITY.md`.
  - This is a display bug fix with no security behavior change.

## Acceptance

- `python/progress_report.py`: `SHIP_PR_PHASES` constant removed; `_render_implement` condition uses only `is_file()` check for ship-pr detection.
- `python/test_progress_report.py`: regression test for unlisted phase (e.g., `PHASE=bump`) passes.
- `python3 -m pytest python/test_progress_report.py` passes.
- No other files changed.

diff_lines: 30

## Test plan
(no test plan section in plan-file)
