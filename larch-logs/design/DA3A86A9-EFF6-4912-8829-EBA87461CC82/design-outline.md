## Proposed Design Outline

### Goals
- Remove two standalone orchestrator Bash turns: Step 4 `ACTION=FINALIZE` and the Step 2a SIMPLE-branch sentinel writes.
- Preserve behavior exactly: finalize artifacts guaranteed before Step 5; SIMPLE sentinels still written; FINALIZE validation failure still surfaced; pause/resume idempotency intact.

### Non-goals
- No change to `finalize-plan.sh` / `design-driver.sh` FINALIZE semantics — relocate the *caller* only.
- No change to HARD-tier sketches or any step other than the two fences.
- No new public flags, run-params fields, or driver scripts.

### Approach sketch
- Fold `ACTION=FINALIZE` into the Step 3b completion-boundary Bash block (runs on every path before Step 4); drop the dedicated Step 4 FINALIZE turn so Step 4 only reads `rejected-findings.md`.
- Fold the three SIMPLE sentinels (`NO_SKETCHES_CLASSIFIED_SIMPLE`->approach-synthesis.txt, `NO_CONTESTED_DECISIONS`->contested-decisions.md, empty dialectic-resolutions.md) into the Step 2a entry Bash block, guarded by `design_classification == SIMPLE`.
- Keep FINALIZE exit-code surfacing: a folded-call failure still aborts before Step 5 with the repair message.
- Review panel vets the final fold points (Step 3b boundary preferred for ordering safety over Gate C preview).

### Surfaces in scope
- `skills/design/SKILL.md` — Step 2a SIMPLE branch (~666-675, 704), Step 3b boundary (~1341), Step 4 (~1357-1367).
- `scripts/test-design-structure.sh` (+ `.md`) — update sentinel/finalize assertions that pin the standalone-turn structure.
- `skills/design/references/sketch-launch.md` — touch only if it pins the SIMPLE-sentinel fence location.

### Open questions
- None. Fold target deferred to plan + review panel per Step 1c.
