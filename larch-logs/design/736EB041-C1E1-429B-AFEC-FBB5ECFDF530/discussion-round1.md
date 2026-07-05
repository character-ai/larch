## Decision 1: Which files need the repeat carve-out (issue 1)
- **Question**: Which files carry "non-empty task output → probe" prose without a byte-identical repeat exception?
- **Resolution**: AGENTS.md (line 64 convention), skills/shared/orchestrator-never.md (NEVER #3 /design section), and skills/design/SKILL.md Step 5c inline routing text (line 622). The Step 3 section in design-background-wait.md already has line 33; SKILL.md Step 3 delegates there, so it is covered.
- **Source**: codebase

## Decision 2: Fingerprint contract clarification scope (issue 2)
- **Resolution**: Prose fix only. Replace/augment "byte-identical" with "prefix-identical (first 200 chars)" in design-background-wait.md line 33 and in SKILL.md anti-pattern #5 body. No code change.
- **Source**: codebase

## Decision 3: Contract test scope (issue 3)
- **Resolution**: Add `contains "$SHARED_DESIGN_WAIT_MD"` assertions for the repeat-fingerprint literal (#5418, "byte-identical" or "prefix-identical") to scripts/test-design-structure.sh. Also introduce `AGENTS_MD` variable and pin the AGENTS.md carve-out literal; add `contains "$ORCH_NEVER_MD"` for the new carve-out.
- **Source**: codebase

## Decision 4: Anti-pattern #5 title wording (issue 4)
- **Resolution**: Change title from "NEVER act on an empty-output `<task-notification>`" to cover both empty-output and repeat (prefix-identical) cases. Both cases end silently so they can share one rule title.
- **Source**: codebase
