### FINDING_2: Add combined-path carve-outs to present refs
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: The present-reference failure prose still forces immediate Step 8 relaunch on writer failures, which conflicts with the combined `assessments` flow and can reintroduce split-round behavior after a partial failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add combined-path failure carve-outs to both present refs: on `NEXT_ACTION=assessments`, wrapper or deviation-append failure is Tool Failure; do not relaunch Step 8 from the per-reference contract. Extend `test-architectural-guidelines-step.sh` pins so combined-path refs explicitly defer failure relaunch to the parent branch while back-compat branches keep per-kind relaunch text


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_4: Define combined-assessment failure routing
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Concern**: The new combined `assessments` branch does not yet spell out fail-closed behavior for helper failures, so a writer or append-deviation failure can leave the turn in an undefined state or fall through to stale relaunch prose.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add explicit `assessments`-branch failure bullets mirroring plan Failure modes: on any listed writer or append-deviation-note non-success, skip remaining DETAIL writers, do not relaunch Step 8 in the same turn, and route to the existing post-driver `tool-failure` (or documented stall) path; note that present-reference failure relaunch lines apply only to back-compat per-kind branches.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_5: Defer terminal guideline flushes
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Concern**: The runtime still flushes non-pending terminal guideline outcomes too early in the combined assessment path, which can dirty `HEAD` before draft writers finish and cause self-inflicted relaunch failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: When any assessment kind is pending, defer run-log-flushing terminal outcome handling for non-pending gates until the next Step 8 pass after requested drafts are durable. Add focused coverage for the invariants-only plus terminal-guidelines case.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### OOS_1: Post-fix CI recovery prose still promises compose-time reassessment will request only `NEXT_ACTION=guidelines-assessment`.
- **Description**: Post-fix CI recovery prose still promises compose-time reassessment will request only `NEXT_ACTION=guidelines-assessment`.. Scenario: After the combined contract lands, operators following ci-fix recovery may expect a guidelines-only pause even when invariant reassessment is also required.
- **Reviewer**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: skills/implement/references/ship-pr-ci-fix.md:25
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### OOS_2: Conflict-resolution recovery prose still names only `NEXT_ACTION=guidelines-assessment` for post-rebase compose reassessment.
- **Description**: Conflict-resolution recovery prose still names only `NEXT_ACTION=guidelines-assessment` for post-rebase compose reassessment.. Scenario: Same stale expectation after conflict resolution when both architectural files need compose-time authoring.
- **Reviewer**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: skills/implement/references/conflict-resolution.md:85
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

