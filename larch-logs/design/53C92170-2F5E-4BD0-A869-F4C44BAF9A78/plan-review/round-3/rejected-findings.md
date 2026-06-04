### [Plan Review] FINDING_2

### FINDING_2: Avoid publishing volatile-only deltas to the repo worktree
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The plan mutates the repository worktree with publish-then-restore/clean for deltas that could be classified as volatile-only before publishing, creating unnecessary cleanup risk and diverging from bash parity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Mirror bash parity by classifying volatile-only deltas in the tmpdir run tree before `_publish_run_tree_to_repo`; when every change is allowlisted refresh sidecars, return the existing no-op without publishing or mutating the repo


