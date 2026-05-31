### FINDING_1:
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/git.py:50-56
- **Concern**: Detached-HEAD guard assumes empty current_branch. Scenario: Plan step 1 maps detached HEAD to Stalled when current_branch is empty, but git.current_branch uses _ensure_success on symbolic-ref and raises ShipError instead of returning ""
- **Proposed resolution**: A detached-HEAD run crashes with ShipError before Stalled, breaking the stated escalation contract Add a non-raising helper (e.g. try_current_branch) or catch symbolic-ref failure in rebase_and_rebump and raise Stalled

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/rebase.py:26-28
- **Concern**: Already-fresh check calls merge-base --is-ancestor but git.py update list omits it. Scenario: Step 3 uses git.merge_base --is-ancestor; python/git.py has merge_base/try_merge_base only, so the short-circuit cannot be implemented as written without ad-hoc argv or a missing helper
- **Proposed resolution**: Add is_ancestor(runner, ancestor, descendant) to the python/git.py update list (and test_git.py)

### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/rebase.py:30-31
- **Concern**: Re-bump ends at apply_bump; no CHANGELOG commit. Scenario: Bash _run_rebase_rebump_from_step3 always runs ship_pr_commit_changelog_after_rebump after apply-bump; apply_bump only commits plugin.json
- **Proposed resolution**: Rebase+rebump leaves no matching Update CHANGELOG commit; same-version replay (#2952) and rebump parity tests miss the tail After apply_bump, call changelog.commit_changelog (and the bullets/write_changelog_entry path when a companion changelog commit was dropped)

### FINDING_4:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/rebase.py:22-25
- **Concern**: Companion CHANGELOG drop reimplements drop_changelog_commit without bullets or version. Scenario: Plan uses generic find_subject_commit_depth + drop_replay_commit; bash records OLD version, extracts bullets, then drop-changelog-commit.sh --version OLD
- **Proposed resolution**: Missing versioned drop and bullet staging recreates #2952 replay loops or loses section body; drop_replay_commit bypasses changelog.drop_changelog_commit guards Parse old version from the dropped bump subject, extract bullets if needed, call changelog.drop_changelog_commit(runner, old_version); Stall on non-"no match" failures per bash

### FINDING_5:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/config.py:65-66
- **Concern**: FIXER_CONFLICT_MAX_ROUNDS=2 tied to conflict-resolution reviewer rounds. Scenario: Plan caps the conflict loop at 2 citing conflict-resolution.md reviewer voting rounds; bash rebase conflict path has no equivalent 2-episode cap on multi-hop --continue
- **Proposed resolution**: Third+ conflict episode during one rebase may raise NeedsUserInput/Stalled while bash keeps resolving, or the constant is mis-documented Define the cap against bash behavior (per-episode waterfall vs multi-hop continue); drop or raise the limit; do not cite the Phase 3 reviewer 2-round rule

### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:30-31
- **Concern**: Re-bump step omits changelog commit after apply_bump. Scenario: Bash run_rebase_rebump fail-closes on commit-changelog.sh after apply-bump; apply_bump only commits plugin.json so force-push can land bump without matching Update CHANGELOG commit
- **Proposed resolution**: After successful apply_bump call changelog.commit_changelog with replaces_version from dropped bump version (and Stalled on failure), mirroring ship-pr.sh ship_pr_commit_changelog_after_rebump
