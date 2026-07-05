## Proposed Design Outline

### Goals
- Add a Python-enforced fetch+rebase before every autonomous fix handoff (`ci-fix` and `reship`).
- Remove the merge-ref-sensitive-only carve-out in `ship-pr-ci-fix.md` step 6.
- Cover the new rebase path with a regression test.

### Non-goals
- `operator-bail` is out of scope; the operator manages their own rebase.
- `conflict-fix` is already mid-rebase; no pre-fix rebase is added there.
- Changes to the ship driver's internal rebase phases (`_ship_rebase_phase`, `_ship_phase14_rebase`).

### Approach sketch
- Add `ship pre-fix-rebase` Python CLI verb in `dispatch_ship.py`, reusing `rebase.rebase_and_push()` with conflict-handoff support.
- Verb emits `PRE_FIX_REBASE_STATUS=ok|conflict|stall`; on conflict it writes handoff fields and routes to `conflict-fix`.
- Route-exit handoff env gains `PRE_FIX_REBASE_REQUIRED=true` for `ci-fix` and `reship` actions.
- SKILL.md and `ship-pr-ci-fix.md` call the new verb at the handoff boundary; Step 6 carve-out is removed.
- Regression test in `python/test_dispatch_ship.py` covers ok, conflict, and stall outcomes.

### Surfaces in scope
- `python/larch/implement/dispatch_ship.py`
- `python/cli.py` (register new verb)
- `skills/implement/SKILL.md` (reship pre-rebase step)
- `skills/implement/references/ship-pr-ci-fix.md` (remove carve-out, add Python step)
- `skills/implement/references/ship-pr-exit-matrix.md` (document new field)
- `python/test_dispatch_ship.py`

### Open questions
- None.
