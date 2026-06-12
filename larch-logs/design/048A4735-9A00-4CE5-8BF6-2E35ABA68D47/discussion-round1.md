## Decision 1: #4062 blocking status
- **Question**: Are all 5 items now unblocked (requires #4062 merged)?
- **Resolution**: #4062 is closed with stateReason=COMPLETED (merged 2026-06-12). All 5 items are unblocked.
- **Source**: codebase (gh issue view 4062)

## Decision 2: Item 3 — timing ledger round-row column layout
- **Question**: Which column in the timing ledger holds the skill for `$2=="round"` rows?
- **Resolution**: Column 4 (`$4`) holds the skill string ("implement" or "design"), confirmed from `timing.py` record_round row layout.
- **Source**: codebase (python/timing.py)

## Decision 3: Item 3 — Gantt path excluded from filter
- **Question**: Should the skill filter also apply to the Gantt awk that reads `$2=="vendor"` rows?
- **Resolution**: No. The Gantt path uses `$2=="vendor"` rows for reviewer timing and uses overlap-only (no skill filter). Pre-design decision explicitly says: "do not change that". Only the `$2=="round"` window awk at line 243 gets the `$4==SKILL` filter.
- **Source**: user (pre-design decisions in issue body)

## Decision 4: Item 5 — when to skip detail renderer
- **Question**: Skip when current round lacks round-meta.json, or when ALL rounds lack it?
- **Resolution**: Skip when ALL discovered round dirs lack `round-meta.json` (pre-design decision: "check whether all discovered round dirs lack round-meta.json").
- **Source**: user (pre-design decisions in issue body)

## Decision 5: Item 5 — affect both _render_step5 and _render_design_plan_review
- **Question**: Does the fix apply only to the implement path or both implement and design?
- **Resolution**: Both. Pre-design decision explicitly names "_render_step5 and _render_design_plan_review".
- **Source**: user (pre-design decisions in issue body)

0 decisions deferred.
