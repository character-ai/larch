### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: Parallel Markdown retitle/replace paths in changelog
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Parallel Markdown retitle/replace implementations in `_write_md_entry` and `_retitle_version_heading_md` used only by `commit_changelog`. A commit-time retitle fix (e.g. when the target version heading already exists) can diverge from `write_changelog_entry` behavior; parity tests may still pass if they only exercise one path. Extract a shared retitle/replace helper or route `commit_changelog` retitle through the same function as `write_changelog_entry`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_17: Classify-bump parity lacks live MAJOR/MINOR diff scenarios
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `classify-bump.sh` parity lacks live MAJOR/MINOR diff scenarios beyond idempotency harness. Classifier logic for real skill diffs could drift from bash with only StubRunner coverage. Add minimal temp-repo subprocess parity for delete→MAJOR and add→MINOR.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add minimal temp-repo subprocess parity for delete→MAJOR and add→MINOR


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_18: Missing tests for token-set cancellation and `agents/**` classify scope
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Missing tests for token-set cancellation and `agents/**` classify scope. Reordered argument-hint wording or agent file changes might mis-classify with no regression signal. Add StubRunner/git fixtures for unchanged flag token sets and `agents/*.md` D/A/R/M.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add StubRunner/git fixtures for unchanged flag token sets and agents/*.md D/A/R/M


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_20

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_20: `bump_worktree` helpers lack direct unit tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `bump_worktree` helpers lack direct unit tests. `find_commit_depth` or rebase-abort error handling regressions only surface via integration drops. Add focused StubRunner tests for depth search and `drop_replay_commit` failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add focused StubRunner tests for depth search and drop_replay_commit failures


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_21: CI workflow does not document git/bash/gawk for parity tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `python-tests` job does not document git/bash/gawk dependency for parity tests. Future CI image without bash/git could skip most parity tests silently. Add comment or sanity which step in workflow.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add comment or sanity which step in workflow


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_24

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_24: `check_bump_version_pre` arms sentinel outside session root
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `check_bump_version_pre` touches `.bump-version-armed` in any existing `implement_tmpdir` without session-root containment. Phase 7 caller passes attacker-influenced tmpdir; sentinel arms Stop-hook resolution outside the real session directory. Validate `implement_tmpdir` under session root before touch (match ship-pr plan-file containment).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Validate implement_tmpdir under session root before touch (match ship-pr plan-file containment)


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_25

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_25: `write_changelog_entry` does not validate semver on version strings
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `write_changelog_entry` does not validate semver on version/categories before structural insert. Untrusted version string with embedded newlines injects extra `##` headings into CHANGELOG. Apply `SEMVER_RE` at public text-transform entry points or enforce trusted input only at driver.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Apply SEMVER_RE at public text-transform entry points or enforce trusted input only at driver


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: Duplicated `ProcRunner` / `StubRunner` test doubles
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Duplicated `ProcRunner` and `StubRunner` test doubles across Phase 2 test files. Future Runner API tweaks require multi-file edits; subtle `StubRunner` differences (porcelain alias) are easy to miss. Introduce a shared test helper module imported by both test files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: Large nested `apply_bump` routine
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `apply_bump` nests multiple inner functions in one large routine. Harder to unit-test rollback and retry branches in isolation without standing up full integration fixtures. Hoist backup, rollback, and retry-loop steps to module-level private helpers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: `sorted_changed_files` UTF-8 vs bash `LC_ALL=C` sort
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `sorted_changed_files` uses UTF-8 byte sort; bash drop scripts use `LC_ALL=C`. Custom `LARCH_BUMP_FILES` with non-ASCII path segments could fail guard-4 equality vs bash (drop refused or allowed incorrectly). Match `LC_ALL=C` sorting or restrict/document ASCII-only bump file paths with a fixture test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: Monolithic `changelog.py` module
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Single large module combines RST/MD text ops and git orchestration. Phase 7 wiring increases merge conflict risk and review burden when touching one concern affects unrelated code. Consider splitting pure text transforms from git wrappers if more callers arrive.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

