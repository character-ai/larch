### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: correctness
- **Location**: python/session_env.py:854-855
- **Concern**: [SCOPE-REDUCTION] sketch_budget=4 stays valid after HARD moves to 3. Scenario: Legacy or hand-edited run-params.json with sketch_budget=4 pass validation but SKILL launch/collect target only three HARD slots
- **Proposed resolution**: Prefer valid set {0,2,3} only (or map 4→3 on read) instead of maintaining dual budgets

### FINDING_1:
- **Reviewer(s)**: Cursor-dyn-residual-refs
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/scripts/review-core.sh:611-612
- **Concern**: [SCOPE-REDUCTION] Plan omits static_archetype_coverage_ok manifest-absent fallback still listing security archetype. Scenario: When panel_manifest is missing/empty, static_archetype_coverage_ok seeds expected slugs as security correctness edge-cases testing; after dispatch-panel drops security, degraded paths can false-fail with no successful static reviewer for archetype(s): security
- **Proposed resolution**: Add review-core.sh to plan: change fallback expected_file write to correctness edge-cases testing only (or derive expected slugs from manifest when present)
