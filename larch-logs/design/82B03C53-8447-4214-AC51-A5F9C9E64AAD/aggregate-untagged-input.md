### FINDING_1:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:138
- **Concern**: Bash block prelude still names the structured-invocation pin as an always-loaded pre-bootstrap fence after the pin moves. Scenario: The plan deletes the registry `pr closes-issue` old-shape fence and moves that pin to `skills/implement/references/extracted-script-registry.md`, but it only promotes `### Bash block prelude` without revising its body. Line 138 will still say "The structured-invocation pin, Step 0 initial bootstrap, and dirty-tree recovery resume may keep the source guard…" even though that pin is no longer in always-loaded `SKILL.md`. That misstates a load-bearing orchestrator contract and can send `/implement` readers looking for a fence the fence-shape harness no longer expects in `SKILL.md`.
- **Proposed resolution**: When editing `skills/implement/SKILL.md`, update the promoted `## Bash block prelude` pre-bootstrap carve-out to list only fences that remain always-loaded (Preflight helper, Step 0 bootstrap, dirty-tree recovery resume). Remove the structured-invocation pin from that sentence or point it at `skills/implement/references/extracted-script-registry.md`.

### FINDING_2:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:138
- **Concern**: Bash block prelude still names structured-invocation pin as an always-loaded pre-bootstrap fence after registry fence relocation. Scenario: The plan moves the pr closes-issue old-shape Bash fence to skills/implement/references/extracted-script-registry.md and updates scripts/test-implement-fence-shape.md to two pre-bootstrap old-shape sites, but the promoted ## Bash block prelude paragraph still lists the structured-invocation pin alongside Step 0 initial bootstrap as SKILL.md pre-bootstrap fences that may keep the source-guard plus awk fallback. Orchestrators and maintainers can mis-count pre-bootstrap fence shape or edit the wrong surface.
- **Proposed resolution**: When promoting ## Bash block prelude, rewrite the pre-bootstrap sentence to cover only the Preflight helper and Step 0 initial bootstrap fences in SKILL.md; point pr closes-issue lookup to extracted-script-registry.md and dirty-tree resume lookup to bootstrap-recovery.md.
