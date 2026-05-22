### [Plan Review] FINDING_14

### FINDING_14: Non-recursive depth-1 copy silently drops nested DESIGN_TMPDIR subdirs
- **Concern**: Plan says "non-recursive depth-1 for files; recurse one level into render-cache/". Other nested directories (e.g., future step artifacts) are silently dropped with no error. [1 reviewer, important, correctness]
- **Suggested revision**: Either document the explicit include list (and that unknown subdirs are intentionally dropped), or fail closed when unexpected directories exist, so log incompleteness is surfaced rather than silenced.

---

**OOS items:**


### [Plan Review] FINDING_6

### FINDING_6: Default-branch guard must use current_branch_is_default, not just "main"
- **Concern**: Plan says `design-log-publish.sh` refuses to run on main, "mirroring larch-log.sh commit". But `larch-log.sh commit` uses `current_branch_is_default` which matches `main`, `master`, and `origin/HEAD` default branch — not just `main`. A repo where the default branch is `develop` or `master` would bypass the guard if the script only checks for `main`. [5 of 10 reviewers, important, correctness]
- **Suggested revision**: Implement the guard using the same `current_branch_is_default` logic from `scripts/larch-log.sh:124-137` (or factor a shared helper), and align the edge-case prose.


