# Review Round 1

- Mode: `diff`
- 10 accepted, 1 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Moved-base Step 8 end-to-end regression missing
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: important
- **Concern**: The planned run_ship regression that proves a postbump rebase onto moved origin/main still refreshes the PR body with a real assessment is missing, so CI cannot verify the original failure mode end to end.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Add a full run_ship integration test with moved origin/main, guidelines-assessment handoff, compose write, relaunch, and PR-body note assertion.
  - From cursor-specialist-testing: Add git-fixture run_ship test: main advances, rebase runs, compose gate fires, PR body gets real note.


### FINDING_3: Durable note reuse ignores diff fingerprint
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-compose-gate
- **Severity**: important
- **Concern**: Compose freshness is keyed only on HEAD_SHA, so a durable note can be reused even when the stored diff fingerprint no longer matches the live origin/main...HEAD materialization.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Also require fingerprint match (note_fingerprint_stale) before short-circuiting to current; rematerialize when stale.
  - From cursor-specialist-edge-cases: Require fingerprint match or force prepare_compose_assessment when the live diff fingerprint differs.
  - From dyn-dyn-compose-gate: Treat a durable note as consumable only when HEAD_SHA matches and the stored fingerprint matches a freshly materialized origin/main...HEAD diff (or force assessment-required when note_fingerprint_stale is true).


### FINDING_4: Compose helper unit coverage missing
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing
- **Severity**: important
- **Concern**: The planned unit-test matrix for the compose helpers is absent, leaving HEAD drift, invalid inputs, failed materialization, durable writes, and stale artifact clearing without direct regression coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Add the planned prepare_compose and write_compose_assessment test matrix from the implementation plan.
  - From cursor-specialist-testing: Add the seven scenarios from the plan against architectural_guidelines.py compose helpers.
  - From codex-specialist-testing: Add the compose-time helper tests required by the plan.


### FINDING_5: Transient compose prep failure fails open
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: latent
- **Concern**: Transient prepare_compose_assessment failures are downgraded to an empty note instead of forcing reassessment or rematerialization.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Map transient failed statuses to needs_assessment or rematerialize; do not proceed with an empty note.


### FINDING_6: Retired prepare wrapper still mentioned in SKILL.md
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness
- **Severity**: important
- **Concern**: SKILL.md still mentions the retired prepare wrapper in frontmatter/comment text, which the updated harness rejects even though it is no longer a live path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Remove the retired prepare wrapper from SKILL.md frontmatter, or narrow the harness if the comment is intentionally non-live.
  - From codex-specialist-correctness: Remove the retired wrapper from the comment or update the harness to ignore non-live frontmatter comments.


### FINDING_7: Redaction failure returns empty note
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: important
- **Concern**: If redaction fails for a present durable note, ship_guidelines returns an empty note instead of failing closed or stalling for reassessment.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Fail closed or route to reassessment/stall when redaction fails on a consumable durable note.


### FINDING_10: guidelines-assessment resume path lacks pre-PR test
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: important
- **Concern**: The ship_resume guidelines-assessment path is not covered to prove it resumes pre-PR compose without rerunning postbump work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Fixture test for PHASE=guidelines-assessment without PR_NUMBER asserting pre-pr-compose and no postbump.


### FINDING_11: Stale-note resume path not exercised
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: The open-PR resume test is too permissive because it always injects a note, so stale-note reuse after HEAD changes is not exercised.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Resume with stale durable note vs new HEAD; assert needs_assessment or NEEDS_USER_INPUT.


### FINDING_12: Fence-shape harness lacks ordering slice
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: The fence-shape harness does not cover the guidelines-assessment ordering slice, so prompt ordering regressions can slip through.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add SKILL.md slice checks mirroring ci-fix/reship ordering tests.


### FINDING_13: Legacy prepare invalidates compose artifacts
- **Reviewer(s)**: dyn-dyn-compose-gate
- **Severity**: important
- **Concern**: The legacy prepare verb still deletes compose-materialization artifacts, which can break an in-flight compose handoff after Step 8.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-compose-gate: Remove MATERIALIZE_ENV/MATERIALIZED_DIFF from legacy prepare invalidation, or make prepare/prepare-compose share one non-destructive preflight that never clears an in-flight compose handoff.


