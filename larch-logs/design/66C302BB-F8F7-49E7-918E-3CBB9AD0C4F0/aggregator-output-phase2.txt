### FINDING_1: `docs/skills.md` may keep obsolete top-level-mtime sentence
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: Plan replaces the `/cleanup` retention blurb but does not require dropping the second sentence "Age is measured by each entry's top-level mtime.". An implementer could add the nested-activity sentence and leave the top-level-mtime sentence, so the catalog would still describe the wrong deletion model after a doc-sync PR.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: In the `docs/skills.md` block, explicitly DELETE or reword that standalone "Age is measured…" sentence (merge into one nested-activity paragraph; keep only the reap / always-runnable sentences after).

### FINDING_2: Edit-in-sync lists omit docs this PR touches
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: latent
- **Concern**: The edit-in-sync trigger is reworded but still omits `docs/skills.md`, `docs/linting.md`, and `skills/cleanup/scripts/test-cleanup.md` even though this PR edits all three. Future retention or maxdepth edits may sync only the listed files and the six-file doc fix drifts again.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Extend the `cleanup.md` (and matching `test-cleanup.md:26`) Edit-in-sync lists to include every doc the plan touches, or drop the "six docs stop drift" claim.

### FINDING_3: Harness case bullets still describe top-level-mtime deletion
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: nit
- **Concern**: The case list in `test-cleanup.md` still describes deletion as driven by "stale top-level mtime" while the PR corrects the model elsewhere in the same file. Readers of the harness doc could infer top-level mtime still gates deletion, contradicting the updated invariants.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Reword those two case bullets to "no nested file within maxdepth 5 newer than cutoff" (same PR, no new tests).

### FINDING_4: Stale swallowed-enumeration invariant may coexist with new fail-safe/fail-open bullets
- **Reviewer(s)**: Cursor-dyn-doc-scope-completeness
- **Severity**: important
- **Concern**: The `cleanup.md` update adds fail-safe and fail-open bullets but does not retire the existing swallowed-enumeration invariant. An implementer could leave bullet 12 ("Age-pass `find` enumeration errors are swallowed…") while adding nested-scan fail-safe (warn + skip delete) and enumeration fail-open bullets, so the contract doc would claim all age-pass `find` failures are silent, contradicting `should_remove_by_age` stderr warning on nested-scan failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-doc-scope-completeness: In the `cleanup.md` ### UPDATED block, explicitly remove or replace invariant bullet 12 so only top-level enumeration failures are fail-open (no warning) and nested-scan failures are fail-safe (warn + keep)
