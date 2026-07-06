### [rejected] FINDING_6

**Rejected subtype:** dismissed (0 YES)

### FINDING_6: tracked-by-git gate misidentifies nested worktrees
- **Reviewer(s)**: dyn-dyn-topology
- **Severity**: major
- **Concern**: The tracked-by-git gate is keyed off parent work-tree presence rather than the directory's own git root, so non-git fixtures or nested checkout paths can be checked incorrectly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-topology: Gate tracking only when repo_root.resolve() equals git rev-parse --show-toplevel for that root (or when repo_root has its own .git). When gated on, pass ls-files paths relative to that toplevel (prefix with repo_root.relative_to(toplevel) when they differ), and add a harness case that runs a non-git init fixture from a directory inside the live checkout to pin the skip behavior.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

