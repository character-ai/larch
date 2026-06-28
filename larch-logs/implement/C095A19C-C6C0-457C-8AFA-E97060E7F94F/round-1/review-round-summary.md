# Review Round 1

- Mode: `diff`
- 2 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: correctness: timing-rehydration harness still expects two pre-bootstrap awk fallbacks
- **Reviewer(s)**: cursor-specialist-correctness, dyn-dyn-reachability
- **Severity**: blocking
- **Concern**: Moving the `pr closes-issue` old-shape Bash fence out of always-loaded `skills/implement/SKILL.md` into `skills/implement/references/extracted-script-registry.md` leaves one `LARCH_CLAUDE_PLUGIN_ROOT=` awk fallback in always-loaded SKILL.md (Step 0 initial bootstrap; Preflight is guard-only). Invariant C in `scripts/test-implement-timing-rehydration.sh` still requires `awk_count >= 2` (lines 87–88), so `make lint` fails with `expected at least two pre-bootstrap awk fallbacks to remain, found 1`. `scripts/test-implement-fence-shape.sh` was updated (`EXPECTED_OLD` 3→2), but the timing-rehydration harness and its doc were not, so plan acceptance “`make lint` passes” is not met.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness, dyn-dyn-reachability: Address the concern above.


### FINDING_2: correctness: always-loaded Step 8+ S030 reachability path list remains in SKILL.md
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: important
- **Concern**: The always-loaded Step 8+ S030 reachability path list at `skills/implement/SKILL.md:696` was not removed with the other machine-reachability inventories. Every `/implement` turn still loads nine script/doc path literals for lint anchoring; the feature goal of eliminating always-loaded G004/S030 inventories is only partially met.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


