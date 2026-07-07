### FINDING_4: Registry identity and filename derivation are still underspecified
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements
- **Severity**: major
- **Concern**: The registry contract does not pin how run-id is derived or how registry paths are built, so the required `<run-id>-<step>.env` layout is not enforced and concurrent sessions can collide on the same step name.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In registry.py and cli.py pin registry filenames to <run-id>-<step>.env, derive run-id at start from session RUN_ID or an equivalent per-run id in tmpdir keepalive, and require wait/status/reap to match on both run-id and step. Add a collision test in python/tests/bgjob/test_registry.py.
  - From Cursor-Requirements: Pin run-id capture in bgjob start (required when registry row is written), include RUN_ID/LARCH_RUN_ID in registry model fields, and add pytest coverage for distinct run-id rows for the same step


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_8: The plan points at the wrong Step 8 ship path
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Concern**: The migration plan targets a non-existent Step 8 ship reference path, so the actual shipped wrapper doc will be skipped during review and migration.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Retarget the plan entry to ### UPDATED: skills/implement/scripts/step-8-ship.md and keep references/ship-pr-exit-matrix.md and ship-pr-ci-fix.md as separate items


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### OOS_1: External-reviewers doc still instructs launching reviewers with run_in_background
- **Description**: External-reviewers doc still instructs launching reviewers with run_in_background. Scenario: After skill migration the inverse lint allowlists only retained legacy docs. external-reviewers.md remains a loaded operator contract and still teaches notification-era background launches, so degraded-tool guidance can reintroduce the removed primitive outside the linted skills surface.
- **Reviewer**: Cursor-Arch
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: docs/external-reviewers.md
- **Phase**: design




Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false

### OOS_2: Issue machinery mentions bgjob status for debugging but the plan does not wire /larch:status
- **Description**: Issue machinery mentions bgjob status for debugging but the plan does not wire /larch:status. Scenario: The issue defines bgjob status for /larch:status and debugging. Acceptance does not require it, yet operators have no first-class visibility into live registry rows after abandoning notification waits.
- **Reviewer**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: skills/status/SKILL.md
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### OOS_3: Consecutive-bash lint still treats run_in_background as the async-fence escape hatch
- **Description**: Consecutive-bash lint still treats run_in_background as the async-fence escape hatch. Scenario: Once migrated skills stop using run_in_background outside the allowlist, lint_consecutive_bash.py line 208 still exempts any fence containing run_in_background from consecutive-bash rules. New skill prose could reintroduce chained background fences without hitting bg-wait inverse lint.
- **Reviewer**: Cursor-Arch
- **Severity**: minor
- **Focus area**: code-quality
- **Location**: python/larch/lint/lint_consecutive_bash.py:208
- **Phase**: design




Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### OOS_4: [OUT_OF_SCOPE] Maintainer sibling doc still documents .bg-wait-active detach/reattach after wrapper migrates to bgjob
- **Description**: [OUT_OF_SCOPE] Maintainer sibling doc still documents .bg-wait-active detach/reattach after wrapper migrates to bgjob. Scenario: Runtime SKILL.md is updated, but editors relying on step-5-review.md will reintroduce retired marker/detach semantics while changing Step 5 wrapper
- **Reviewer**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: code-quality
- **Location**: skills/implement/scripts/step-5-review.md
- **Phase**: design

Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false

