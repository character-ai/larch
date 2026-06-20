### FINDING_2:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/git.py:46-54
- **Concern**: Planned `_has_live_git_process` scans for any system-wide git process instead of a repo-scoped or lock-holding check. Scenario: Operator runs `/design` or another git job in a different repo while a 0-byte stale `index.lock` blocks this repo; guarded removal is refused with `live git process detected` and Step 5 / `commit_fixes --stage-all` still stall until manual `rm`
- **Proposed resolution**: Scope the probe to the target repo (cwd / `rev-parse --absolute-git-dir`) or to processes holding `<git-dir>/index.lock`; treat unrelated git PIDs as non-blocking

