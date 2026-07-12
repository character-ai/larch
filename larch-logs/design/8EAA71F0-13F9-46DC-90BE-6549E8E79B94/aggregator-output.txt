### FINDING_1: Regenerated baselines remain stranded
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Concern**: When only regenerated baseline files are dirty, the empty-intersection noop leaves them unowned and can reproduce the stranded-tree recovery failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Choose and implement one policy for run-generated baselines: commit them with the review fix or revert them, while preserving unrelated user changes

### FINDING_2: Status-path parsing is not robust
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: minor
- **Concern**: Non-NUL porcelain parsing can mismatch collected paths containing quoting or control characters, and may mishandle rename/copy records, causing an incorrect noop.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Use `git status --porcelain=v1 -z --untracked-files=all` with canonical parsing, including rename/copy records, and add a matching regression case
