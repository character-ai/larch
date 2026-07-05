### FINDING_6: Stall-recovery edits also need the pre-fix gate
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The stall-recovery path can still make inline CI edits without the new fetch+rebase step, so those edits can land on stale main before step-8-ship.sh resumes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Extend the autonomous pre-fix gate to step8-shippr code-edit repairs (run ship pre-fix-rebase after escalation, branch on NEXT_ACTION, then stale-handoff clear and relaunch), or document an explicit exclusion with a correctness rationale.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_8: Registry count must be updated for the new verb
- **Reviewer(s)**: Codex-Innovation
- **Severity**: blocking
- **Concern**: Adding `ship pre-fix-rebase` changes the registry size, but the test still hard-codes the old total, so the suite will fail even if the command is implemented correctly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Update the expected count to 40 or assert the new entry directly instead of a brittle total.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_9: Helper must fail closed on missing required state
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Concern**: The new helper must reject blank or missing `REPO`, `RUN_ID`, or tmpdir state before it calls into the rebase helper; otherwise it can emit a successful routing result against the wrong checkout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add an explicit required-state preflight that emits `PRE_FIX_REBASE_STATUS=stall` and `NEXT_ACTION=stall` before the rebase call when `REPO`, `RUN_ID`, or tmpdir is missing, and cover it with a regression test.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_11:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/SKILL.md
- **Concern**: [SCOPE-REDUCTION] reship is included in the pre-fix gate. Scenario: Acceptance targets autonomous main-agent fix handoffs; reship is a driver retry with no edits. Many reships already trigger _ship_phase14_rebase on relaunch when ship-pr-rrr-after-phase14.flag exists (dispatch_ship.py _ship_route_phase14_reship_pending). Unconditional pre-fix on every reship adds fetch/rebase work and can surface conflicts on transient-infra retries without fixing anything.
- **Proposed resolution**: Limit ship pre-fix-rebase to ci-fix (and any other path that performs repo edits before relaunch). Let reship keep stale-handoff clear then step-8-ship.sh only.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_12:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/SKILL.md
- **Concern**: [SCOPE-REDUCTION] Pre-fix on every route-exit reship exceeds the issue fix-handoff contract. Scenario: The binding scope requires fetch+rebase before the main agent applies a fix. route-exit reship (exit 0 non-OK, transient retry, no-ci-checks phase14) relaunches step-8-ship.sh without autonomous repo edits; stall-recovery already treats pure reship as non-escalation. Forcing pre-fix on all reship adds redundant fetch/rebase work and extra conflict surface on infra retries with no edit benefit.
- **Proposed resolution**: Limit PRE_FIX_REBASE_REQUIRED and the SKILL reship branch to reship only when the orchestrator will perform main-agent repo edits before the next ship launch (if any). Otherwise keep ci-fix as the sole mandatory pre-fix path, or split reship into fix-pending vs driver-only retry in route-exit and document the narrower token in ship-pr-exit-matrix.md.

Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_5: Live rebase with missing metadata can still stall instead of conflict-fix
- **Reviewer(s)**: Codex-Arch, Codex-Requirements
- **Severity**: important
- **Concern**: The in-progress rebase guard falls back to stall when persisted metadata is missing, even if the checkout already has unmerged paths that should route to conflict-fix.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Check git unmerged paths when rebase_in_progress is true; if any exist, write phase=rebase conflict handoff fields with CONFLICT_FILES and NEXT_ACTION=conflict-fix, and stall only when neither metadata nor unmerged paths exist
  - From Codex-Requirements: Check `git.unmerged_paths()` when `git.rebase_in_progress()` is true and `_ship_route_conflict_handoff_fields()` is empty. If paths exist, synthesize `RESUME_PHASE=ship-pr-rrr-phase14`, `CALLER_KIND=ship_pr_pre_push`, and `CONFLICT_FILES`, patch state and handoff, then emit `NEXT_ACTION=conflict-fix`


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_7: Pre-fix helper can mutate the wrong checkout before the ship guard
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Concern**: The new pre-fix helper can act on whatever checkout is currently active before the existing ship checkout guard aborts, so a branch mismatch can still edit the wrong tree.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add a non-mutating guard before `rebase_and_push()`: read `BRANCH_NAME` from `ship-pr-state.sh`, compare it to `git.try_current_branch()`, and route to a safe stall or documented operator-bail outcome without rebasing on mismatch


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### OOS_1: [SCOPE-REDUCTION] Unconditional pre-fix on every `reship` exceeds the autonomous fix-handoff contract
- **Description**: [SCOPE-REDUCTION] Unconditional pre-fix on every `reship` exceeds the autonomous fix-handoff contract. Scenario: The binding scope requires fetch+rebase before the main agent applies a fix (`ci-fix`). Many `reship` paths are driver retries with no repo edits (`exit 0` non-OK, transient infra, phase14 no-checks retry). Forcing pre-fix on all reships adds fetch/rebase work and conflict surface without edit benefit.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/implement/SKILL.md
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

