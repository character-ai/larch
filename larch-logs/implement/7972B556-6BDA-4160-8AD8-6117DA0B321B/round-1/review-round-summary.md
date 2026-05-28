# Review Round 1

- Mode: `diff`
- 3 accepted, 4 rejected (4 exonerated)

## Accepted Findings

### FINDING_2: Harness markdown is missing from agent-lint exclusions
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-step0b-router-flag-recovery.sh` is excluded as a Makefile-only harness, but the sibling `.md` is not listed like peer harness pairs, creating inconsistent lint policy.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_3: Harness documentation has stale line references
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-step0b-router-flag-recovery.md` points maintainers to old `scripts/test-design-structure.sh` line numbers for per-arm jq pins, so future edits may inspect unrelated checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_7: Missing run-params degraded path differs between harness and SKILL
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The harness hard-fails when `run-params.json` is missing, while SKILL.md says to warn and continue. That degraded missing-file path is untested and the harness contract can mislead future maintainers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


