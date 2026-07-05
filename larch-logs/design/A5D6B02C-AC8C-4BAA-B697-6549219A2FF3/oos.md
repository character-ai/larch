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

