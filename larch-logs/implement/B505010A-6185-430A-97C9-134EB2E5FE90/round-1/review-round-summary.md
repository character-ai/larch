# Review Round 1

- Mode: `diff`
- 2 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_2: `progress note --run-id` still needs a test that proves `current` is preserved
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-testing
- **Severity**: minor
- **Concern**: `progress note --run-id` routes to explicit-run append without touching `current` or the flat log, but the new test does not seed an existing `current` pointer, so a regression that rewrites it could still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: "Address the concern above."
  - From codex-specialist-testing: "Seed current with activate_run, run progress note --run-id, and assert the pointer file content is unchanged."


### FINDING_3: Cleanup traversal still needs fd-pinned clone-dir enumeration
- **Reviewer(s)**: codex-specialist-edge-cases, codex-specialist-testing
- **Severity**: major
- **Concern**: `cleanup_old_progress_files` still path-walks a clone dir after a plain symlink check and then recurses with `shutil.rmtree`, so a clone-dir swap between the check and `iterdir()` can make cleanup traverse or delete outside `progress_root`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: "Anchor cleanup on a verified clone-dir fd, and enumerate or remove children through dir-relative operations only"
  - From codex-specialist-testing: "Pin the clone dir with a verified directory fd before listing children, or re-open and re-check the inode immediately before recursion, and add a swap-race test."


