### FINDING_1: Dedup helper changes do not trigger owning harness
- **Reviewer(s)**: Codex-Innovation
- **Severity**: latent
- **Concern**: New dedup helper is not mapped to `test-plan-review-loop`. Scenario: a future change touching only `skills/design/scripts/dedup-plan-lines.py` or its sibling doc can pass `relevant-checks` without running the harness that owns dedup behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add skills/design/scripts/dedup-plan-lines.py and skills/design/scripts/dedup-plan-lines.md to the existing plan-review-loop case that appends test-plan-review-loop


