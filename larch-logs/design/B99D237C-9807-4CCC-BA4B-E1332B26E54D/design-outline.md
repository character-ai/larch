## Proposed Design Outline

### Goals
- Make the four `ship.py` CI-loop counters (`iteration`/`rebase_count`/`fix_attempts`/`transient_retries`) session-wide so the 50/20/10/1 caps survive exit-3/exit-6 handbacks.
- On re-entry, resume near the current phase from ground truth (gh PR state + git + run-log manifest) so checks/postbump/pr-prep are not redundantly re-run against an existing or already-merged PR.
- Add the Phase-7 driver acceptance matrix + `ci_monitor` routing coverage so the dormant Python ship path cannot silently regress.

### Non-goals
- No edits to live `scripts/ship-pr.sh`; no flip-to-python in `/implement` Step 8+ or `SKILL.md`.
- No change to `OUTCOME_EXIT_MAP` (0/1/3/4/6) or any stage-order invariant.
- No new counters or caps; reuse existing `config` constants.

### Approach sketch
- Restore counters from the persisted state file (`run_logs.read_state_kv`) at the top of the CI loop instead of seeding 0.
- Add a best-effort ground-truth resume reconciliation: gh PR open/merged + manifest OOS-filed decide skip-checks/postbump/pr-prep vs resume-CI-loop vs resume-postmerge.
- State file is the floor: a failed gh/git/manifest read degrades to the persisted PHASE/counters, never a hard error.
- Keep `run_ship` linear; gate the early phases rather than restructure into a bash-style phase-dispatch loop (minimum-change bias; full plan-review panel still vets it).

### Surfaces in scope
- `python/ship.py` (run_ship resume + counter restore), `python/run_logs.py` (small ground-truth / counter-read helper), `python/ci_monitor.py` (no behavior change; covered by tests).
- `python/test_ship.py`, `python/test_ci_monitor.py` (acceptance matrix + routing / transient-bail coverage).

### Open questions
- None. Scope resolved in Round 1 (Python-only; state-file floor, ground truth refines).
