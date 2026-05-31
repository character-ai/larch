### FINDING_1: Detached-HEAD guard never reaches Stalled
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: important
- **Concern**: Plan step 1 treats detached HEAD as Stalled when `current_branch` is empty, but `git.current_branch` uses `_ensure_success` on `symbolic-ref` and raises `ShipError` instead of returning `""`. A detached-HEAD run can crash with `ShipError` before the Stalled escalation path, breaking the stated contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add a non-raising helper (e.g. try_current_branch) or catch symbolic-ref failure in rebase_and_rebump and raise Stalled
  - From Cursor-Innovation: Add a non-raising helper (e.g. try_current_branch) or catch symbolic-ref failure in rebase_and_rebump and raise Stalled


### FINDING_2: Already-fresh check needs `merge-base --is-ancestor` helper
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: Step 3 calls `git.merge_base --is-ancestor`, but `python/git.py` only documents `merge_base` / `try_merge_base`. The already-fresh short-circuit cannot be implemented as written without ad-hoc argv or a missing helper.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add is_ancestor(runner, ancestor, descendant) to the python/git.py update list (and test_git.py)


### FINDING_3: Re-bump omits post-`apply_bump` CHANGELOG commit
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: important
- **Concern**: Bash `_run_rebase_rebump_from_step3` / `run_rebase_rebump` always runs `ship_pr_commit_changelog_after_rebump` after `apply-bump`; `apply_bump` only commits `plugin.json`. The Python re-bump path (and plan step) stops at `apply_bump`, so force-push can land a version bump without a matching “Update CHANGELOG” commit—parity gaps for same-version replay (#2952) and rebump tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Rebase+rebump leaves no matching Update CHANGELOG commit; same-version replay (#2952) and rebump parity tests miss the tail After apply_bump, call changelog.commit_changelog (and the bullets/write_changelog_entry path when a companion changelog commit was dropped)
  - From Cursor-Pragmatic: After successful apply_bump call changelog.commit_changelog with replaces_version from dropped bump version (and Stalled on failure), mirroring ship-pr.sh ship_pr_commit_changelog_after_rebump


### FINDING_4: Companion CHANGELOG drop bypasses versioned `drop_changelog_commit`
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: Dropping a companion CHANGELOG commit reimplements generic `find_subject_commit_depth` + `drop_replay_commit` instead of bash’s version-aware path (record OLD version, extract bullets, `drop-changelog-commit.sh --version OLD`). Missing versioned drop and bullet staging risks #2952 replay loops or lost section body; `drop_replay_commit` skips `changelog.drop_changelog_commit` guards.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Missing versioned drop and bullet staging recreates #2952 replay loops or loses section body; drop_replay_commit bypasses changelog.drop_changelog_commit guards Parse old version from the dropped bump subject, extract bullets if needed, call changelog.drop_changelog_commit(runner, old_version); Stall on non-"no match" failures per bash


### FINDING_5: `FIXER_CONFLICT_MAX_ROUNDS=2` misaligned with bash rebase behavior
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: `FIXER_CONFLICT_MAX_ROUNDS=2` is tied to conflict-resolution reviewer voting rounds, but the bash rebase conflict path has no equivalent two-episode cap on multi-hop `--continue`. A third+ conflict episode in one rebase may raise `NeedsUserInput`/`Stalled` while bash keeps resolving—or the constant is mis-documented.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Third+ conflict episode during one rebase may raise NeedsUserInput/Stalled while bash keeps resolving, or the constant is mis-documented Define the cap against bash behavior (per-episode waterfall vs multi-hop continue); drop or raise the limit; do not cite the Phase 3 reviewer 2-round rule

---

**Merge note**: Original input `FINDING_3` (python/rebase.py) and `FINDING_6` (plan.txt) describe the same behavioral gap (no `commit_changelog` after `apply_bump`); they are merged above. All other input findings remain distinct (different code paths or fixes). Five `### FINDING_N:` blocks; no `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` line.

