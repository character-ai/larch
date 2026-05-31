### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: docs/skills.md:47
- **Concern**: Plan replaces the `/cleanup` retention blurb but does not require dropping the second sentence "Age is measured by each entry's top-level mtime.". Scenario: Implementer adds the nested-activity sentence and leaves the top-level-mtime sentence; the catalog still states the wrong deletion model after a doc-sync PR.
- **Proposed resolution**: In the `docs/skills.md` block, explicitly DELETE or reword that standalone "Age is measured…" sentence (merge into one nested-activity paragraph; keep only the reap / always-runnable sentences after).

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/cleanup/scripts/cleanup.md:21
- **Concern**: Edit-in-sync trigger is reworded but still omits `docs/skills.md`, `docs/linting.md`, and `skills/cleanup/scripts/test-cleanup.md` even though this PR edits all three.. Scenario: Future retention or maxdepth edits sync only the listed files; the six-file doc fix drifts again.
- **Proposed resolution**: Extend the `cleanup.md` (and matching `test-cleanup.md:26`) Edit-in-sync lists to include every doc the plan touches, or drop the "six docs stop drift" claim.

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: skills/cleanup/scripts/test-cleanup.md:10-12
- **Concern**: Case list still describes deletion as driven by "stale top-level mtime" while the PR corrects the model elsewhere in the same file.. Scenario: Readers of the harness doc infer top-level mtime still gates deletion, contradicting line 14 and the updated invariants.
- **Proposed resolution**: Reword those two case bullets to "no nested file within maxdepth 5 newer than cutoff" (same PR, no new tests).

### FINDING_4:
- **Reviewer(s)**: Cursor-dyn-doc-scope-completeness
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:24-25 / skills/cleanup/scripts/cleanup.md:12-13
- **Concern**: `cleanup.md` update adds fail-safe and fail-open bullets but does not retire the existing swallowed-enumeration invariant. Scenario: Implementer can leave bullet 12 ("Age-pass `find` enumeration errors are swallowed…") while adding nested-scan fail-safe (warn + skip delete) and enumeration fail-open bullets; contract doc then claims all age-pass `find` failures are silent, contradicting `should_remove_by_age` stderr warning on nested-scan failure (`skills/cleanup/scripts/cleanup.sh:23-25`)
- **Proposed resolution**: In the `cleanup.md` ### UPDATED block, explicitly remove or replace invariant bullet 12 so only top-level enumeration failures are fail-open (no warning) and nested-scan failures are fail-safe (warn + keep)
