### FINDING_1: Crash finalization mishandles provenance read failures
- **Reviewer(s)**: Codex-Arch
- **Severity**: minor
- **Concern**: Crash-finalization provenance read failures are not mapped to the required bail result. If git cannot read the commit body or ancestry, `_git_read` raises `LaneClosedError`; crash finalization emits `crash-finalization-failed` instead of `crashed-lane-head-unverified`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Make the shared validator convert provenance read failures to False, so crash finalization returns the prescribed operator-bail result while normal dispatch still raises LaneClosedError

### FINDING_2: Normal dispatch lacks subject-only provenance regression coverage
- **Reviewer(s)**: Codex-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: Normal direct-HEAD dispatch, and its related salvage path, lack a mandatory regression test proving that a subject-only commit without the `Larch-Salvage-Step` trailer fails closed. The primary `fixer-produced-change` reship bypass could therefore regress while crash-finalize coverage still passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add subject-only cases to the normal-dispatch matrix for both direct-HEAD and uncommitted-salvage paths; assert no reship and preserved offending commit
  - From Cursor-Pragmatic: Add a dispatch test (or extend the parametrized matrix with a `missing-trailer` case on the direct-HEAD-change path) where the launcher commits `Apply CI fixer working-tree edits ({tier})` with no `Larch-Salvage-Step` trailer; assert fail-closed with no `reship` and no rounds/lineage advance.
  - From Cursor-Requirements: Add an explicit `_dispatch` negative test where a committing launcher advances `HEAD` with the expected subject but no trailer; assert `LaneClosedError` (or `operator-bail` if exercised through `main()`), no `reship`, and no rounds/lineage advance.
