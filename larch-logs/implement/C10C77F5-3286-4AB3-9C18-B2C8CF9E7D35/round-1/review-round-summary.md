# Review Round 1

- Mode: `diff`
- 2 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Symlink ancestry can escape the staged tally root
- **Reviewer(s)**: codex-specialist-testing, codex-specialist-correctness, cursor-specialist-testing
- **Severity**: important
- **Concern**: `_write_tally_stage_dir` only rejects an immediate symlink parent, so a staged log root under a symlinked ancestor can still escape `IMPLEMENT_TMPDIR`; `write-tally` can stage its temp record outside the implement tmpdir, and the current tests do not cover ancestry symlinks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-testing: Add parametrized rejection tests for symlink, nonexistent, and non-directory parents


### FINDING_2: Writer-parity lint still has a file-wide `CLONE_PATH=` fallback
- **Reviewer(s)**: codex-specialist-testing, codex-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-bg-wait
- **Severity**: important
- **Concern**: `_has_clone_path_emission` falls back to a file-wide `CLONE_PATH=` scan when no write-context anchor is found, so a writer can drop the nearby stamp and still pass if an unrelated `CLONE_PATH=` remains elsewhere; the lint can silently miss the regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Fail closed when writer evidence exists but no write-context anchors are found; do not fall back to file-wide `CLONE_PATH=`
  - From cursor-specialist-testing: Fail closed when writer evidence exists but no write-context anchors are found, instead of file-wide fallback
  - From dyn-dyn-bg-wait: When marker_write_indexes is empty, return False (or fail unless _has_writer_evidence is also false) instead of scanning the whole file; keep the cleanup-only regression test by asserting pass only when no write-context anchors exist and writer evidence is absent or the file is not an inventoried writer.


