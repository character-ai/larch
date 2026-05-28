## Decision 1: Concern 1 — code change scope
- **Question**: Should the design fix or audit the alleged duplicate tracking issue?
- **Resolution**: Audit only. Verify each unguarded helper in phase_plan_materialize (lines 750-911 of scripts/implement-bootstrap.sh) is already idempotent on `--resume-plan-tail` re-entry (marker-based upsert, branch idempotency, etc.). No behavioral code change.
- **Source**: user

## Decision 2: Concern 2 — test scope
- **Question**: How much test coverage to add for the dirty-tree recovery path?
- **Resolution**: Structural pin only. Add or extend assertions in scripts/test-implement-structure.sh that the SKILL.md Step 0 dirty-tree recovery section retains the sentinel/env/args contract. Skip new mechanical harness fixtures. Existing assertions at lines 421-444 already cover some surface — extend only where gaps remain.
- **Source**: user
