# Review Round 2

- Mode: `diff`
- 3 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_3: Malformed `current` pointers can abort cleanup
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases
- **Severity**: major
- **Concern**: `_read_active_run_id_from_dirfd` is not best-effort on bad `current` content: invalid UTF-8 can raise, and a FIFO `current` can block before `fstat`, causing `cleanup_old_progress_files` to abort instead of skipping the clone.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.


### FINDING_4: FIFO `breadcrumbs.log` can block append
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: major
- **Concern**: `_append_line_in_dir` can block on `os.open` before it reaches the non-regular-file `fstat` check, so a FIFO `breadcrumbs.log` with no reader can hang `progress note --run-id` instead of returning `False`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.


### FINDING_7: Path-based run-dir creation can race with a same-UID swap
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: major
- **Concern**: `activate_run()` and `append_breadcrumb_for_run()` still create child directories through path-based `mkdir`, so a same-UID swap in the pre-mkdir window can redirect creation outside `progress_root` before the later recheck.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Address the concern above.


