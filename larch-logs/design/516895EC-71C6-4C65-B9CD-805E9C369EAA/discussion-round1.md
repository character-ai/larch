## Decision 1: Decomposition
- **Question**: Should D3 be split into multiple sub-issues or tackled as one PR?
- **Resolution**: One PR. The changes are mechanical and the acceptance check is behavioral (end-to-end parity + new lint).
- **Source**: user

## Decision 2: Step 0 merge scope
- **Question**: How far should the Step 0 merge go given that 0b-route has conditional output (ROUTE=proceed/clarify/already-planned)?
- **Resolution**: One `design-step0.sh` wrapper that handles everything through 0b-init, writes a `.design-step0-result.env`, and exits. Orchestrator reads ROUTE + ISSUE_NUMBER from that env. Clarify/already-planned paths exit with distinctive codes that the orchestrator handles.
- **Source**: user

## Decision 3: Prose → reference moves
- **Question**: Are the "move deferred-MAV paragraph to plan-review.md" and "compress Step 5b OOS narrative" in scope for D3?
- **Resolution**: Yes — explicitly listed in issue Scope section. Both included.
- **Source**: codebase (issue body)

## Decision 4: Anti-pattern #7 and prelude documentation
- **Question**: When every fence becomes a single script call, the 2-line prelude no longer appears in SKILL.md fences. Anti-pattern #7 ("NEVER omit pause-check line from Bash fences") and the "Bash block prelude" documentation section both change.
- **Resolution**: Anti-pattern #7 and the prelude documentation section both get updated to describe the new invariant (each fence is a single script call; the script internally sources env and handles pause). The canonical 2-line prelude example fence at L70-73 is removed or replaced.
- **Source**: codebase (acceptance criteria)
