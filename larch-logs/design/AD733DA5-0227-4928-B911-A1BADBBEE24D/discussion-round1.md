## Decision 1: Combined NEXT_ACTION token name
- **Question**: What token name for the combined reason?
- **Resolution**: `architectural-assessments` (as suggested in the issue "for example")
- **Source**: issue text + codebase pattern consistency

## Decision 2: DETAIL field format for kinds
- **Question**: How to communicate which kinds need authoring to the orchestrator?
- **Resolution**: Comma-separated list in `ShipResult.detail`, e.g. `"invariants"`, `"guidelines"`, `"invariants,guidelines"`. Written to DETAIL in `.ship-route-exit-handoff.env`.
- **Source**: codebase (DETAIL is a single-line string in the handoff env; comma-separated is the minimal overhead)

## Decision 3: Back-compat for paused runs
- **Question**: Keep old per-kind NEXT_ACTION tokens?
- **Resolution**: Yes — preserve `invariants-assessment` and `guidelines-assessment` dispatch entries and SKILL.md handlers for one release. No new routing for old tokens.
- **Source**: issue item 5

## Decision 4: `_refresh_guidelines_gate_after_rebase` scope
- **Question**: Does the post-rebase reassessment function also get combined?
- **Resolution**: Yes — it has the same two-exit pattern and is called in the CI monitoring loop after a rebase (HEAD-drift path). Must return combined exit.
- **Source**: codebase audit (lines 497, 1697, 1774 in ship.py)

## Decision 5: Phase string for state file
- **Question**: What phase string to use in `_write_ship_state` for the combined assessment?
- **Resolution**: `"assessments"` — one call replaces the two separate `_write_ship_state` calls
- **Source**: codebase pattern; ship_resume.py must add "assessments" to the set at line 401

## Decision 6: Reference file treatment
- **Question**: Merge two reference files into one or cross-link?
- **Resolution**: Cross-link — update Consumer/When-to-load in each to mention the combined action. The SKILL.md `assessments` handler reads both files.
- **Source**: issue ("merge or cross-link"), preference for smaller diff
