## Goal
Implement issue #4216: [IMPLEMENTING] [OOS] Runtime bug + test-coverage gaps: scout, Step 2 dispatch, ship-pr — 5 items.

## Implementation Plan
## Plan

See `plan.txt` for the full implementation plan. Summary:

- **Bug fix**: `python/plan_scout.py` — unlink `Path(str(raw) + ".cap-hit")` before each tier launch in `scout_dynamic_archetypes` so a stale Cursor cap-hit marker does not silently block a subsequent Claude write.
- **Tests**: `python/test_plan_scout.py` — 4 new tests (cap-hit regression, diff-mode `--read-tools` args, fenced JSON salvage, over-cap truncation).
- **Tests**: `python/test_rendering.py` — 4 scope-anchor boundary tests (symlink, zero-byte, oversize, CR/LF path).
- **Tests**: `skills/implement/scripts/test-step2-dispatch.sh` — Test 13a-scout-cursor: Cursor same-path variant asserting same-path normalization, scout eligibility, and correct archetype filtering.
- **Items 4-5**: Python port already correct (`agents.resolve_launcher_exit` fails closed; `run_checks_phase` is tested). No bash edits.

## Acceptance

- `python3 -m pytest python/test_plan_scout.py python/test_rendering.py -v` passes with all new tests green.
- `bash skills/implement/scripts/test-step2-dispatch.sh` passes including Test 13a-scout-cursor.
- `bash scripts/relevant-checks.sh` passes (no regressions).
- No changes to `scripts/ship-pr.sh` or `scripts/test-ship-pr-rebase.sh`.

diff_lines: 205

## Test plan
(no test plan section in plan-file)
