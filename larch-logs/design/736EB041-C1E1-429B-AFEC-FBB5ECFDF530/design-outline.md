## Proposed Design Outline

### Goals
- Extend the byte-identical repeat silent-yield rule to all Tier-1 probe prose (AGENTS.md, orchestrator-never.md, SKILL.md Step 5c inline text).
- Clarify the fingerprint contract to remove ambiguity ("prefix-identical, first 200 chars").
- Pin repeat-fingerprint contract literals in acceptance tests so CI catches regressions.
- Fix the anti-pattern #5 title to reflect both the empty-output and repeat-notification cases.

### Non-goals
- No runtime/code behavior changes; prose and test-assertion updates only.
- No changes to the fingerprint algorithm (first-200-chars prefix stays as-is).
- No changes outside the four identified surfaces.

### Approach sketch
- Add a single sentence to the AGENTS.md probe-rule paragraph that carves out byte-identical repeats as a silent-yield case.
- Add a matching carve-out clause to orchestrator-never.md NEVER #3 `/design` section.
- Add an inline carve-out sentence to SKILL.md Step 5c routing text (line ~622).
- Rename "byte-identical" to "prefix-identical (first 200 chars)" in design-background-wait.md Step 3 section.
- Update anti-pattern #5 title in SKILL.md to name both empty-output and prefix-identical-repeat cases.
- Add `contains "$SHARED_DESIGN_WAIT_MD"` and `contains "$ORCH_NEVER_MD"` assertions in test-design-structure.sh; introduce `AGENTS_MD` variable and pin the new AGENTS.md literal.

### Surfaces in scope
- `AGENTS.md`
- `skills/shared/orchestrator-never.md`
- `skills/shared/design-background-wait.md`
- `skills/design/SKILL.md`
- `scripts/test-design-structure.sh`
- `scripts/test-design-structure.md` (update-triggers section)

### Open questions
- None.
