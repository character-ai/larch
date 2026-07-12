## Proposed Design Outline

### Goals
- Lock in #7095's `larch:plan` marker-grammar unification so cross-consumer drift cannot silently recur.
- Close #7047 as fixed by #7095 once the guard lands.

### Non-goals
- Re-do #7095's unification (decompose, design_router, learn_from_bugs already route through `issue_wire`).
- Extend to the heading-based plan-boundary regexes in `learn_from_bugs._BOUNDARY_PATTERNS` (`## Plan` / `## Approach` / `### NEW:`).
- Touch the unrelated `design-pause` marker literal at `design_router.py:87`.

### Approach sketch
- Add one class-wide regression guard: scan `python/` source (excluding tests, cache, fixtures) and assert no file outside `issue_wire.py` hardcodes the `<!-- larch:plan` block marker literal.
- Assert the three named consumers (`decompose`, `design_router`, `learn_from_bugs`) reference the `issue_wire` helper API, not a private copy of the grammar.
- Test-only change. No production code edits.
- Close #7047 with a `fixed by #7095` comment referencing the guard.

### Surfaces in scope
- New regression test under `python/tests/issue/` (marker-ownership guard, alongside `test_issue_wire.py`).

### Open questions
- None.
