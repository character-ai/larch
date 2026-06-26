## Goal
Implement issue #5530: [IMPLEMENTING] [BUG] Wrong progress report given by /implement when in re-entered review stage (first time bailed) in /larch:im 5464.

## Implementation Plan
## Plan

Approach

- Keep this as a narrow `progress_report.py` fix.
- In `_render_implement`, remove the early `ship-pr-state.sh` return.
- Try the existing Step 5 render paths first when the run is not done:
  - latest mark contains `Step 5`
  - no mark and no ship-pr phase
  - stale mark but fresh review round artifacts
- After those Step 5 checks fail or are skipped, render `ship-pr-state.sh` if it exists.
- Fall through to the generic implement report last.
- Do not change stall recovery or clear `ship-pr-state.sh`.

Files to modify/create

### UPDATED: python/progress_report.py

- In `_render_implement`, bind `ship_state = tmpdir / "ship-pr-state.sh"` for reuse.
- Keep reading `phase` from `ship_state` so the no-label/no-phase Step 5 fallback stays unchanged.
- Move the `if ship_state.is_file(): return _render_ship_pr(tmpdir)` branch to after the `if not done_marker.exists():` Step 5 inference block.
- Preserve the existing done-marker behavior:
  - if done and ship-pr state exists, show ship-pr
  - if done and no ship-pr state exists, show generic implement status
- Preserve the stale-mark fresh-round note.

### UPDATED: python/test_progress_report.py

- Add a regression test near the existing implement dispatch tests.
- Set up an implement pointer, a latest timing mark of `Step 5 — code review`, a live `round-1` directory, and a stale `ship-pr-state.sh` with `PHASE=checks`.
- Add minimal round files so `_render_step5` returns a report, for example:
  - `round-1/panel-manifest.ndjson`
  - `round-1/round-start-s`
- Assert the report contains `Step 5 code review — round 1 in progress`.
- Assert the report does not contain `Ship-PR phase: checks`.
- Keep existing ship-pr tests intact, including cases where no Step 5 evidence can render.

Edge cases

- A stale `ship-pr-state.sh` must not mask a live Step 5 round.
- A real ship-pr phase must still render when Step 5 has no renderable round evidence.
- A done implement run must not re-enter Step 5 rendering.
- Fresh review artifacts must still override stale non-Step-5 marks before ship-pr fallback.

Failure modes

- If the ship-pr branch stays above Step 5 checks, the reported bug remains.
- If ship-pr fallback is removed instead of moved, real ship-pr progress can regress.
- If the test only writes a Step 5 mark without round artifacts, it may not prove Step 5 rendering wins.

Testing strategy

- Run `python3 -m pytest python/test_progress_report.py -k "ship_pr or step5 or dispatch"`.
- Run `make py-lint`.
- Run `make py-test`.
- Run `make lint`.

## Acceptance

See Testing strategy in plan.

diff_added: 24
diff_deleted: 2
mechanical_churn: false
diff_lines: 30

## Test plan
(no test plan section in plan-file)
