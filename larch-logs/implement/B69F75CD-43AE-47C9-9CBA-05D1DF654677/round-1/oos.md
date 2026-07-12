### FINDING_4: [OUT_OF_SCOPE] PR head and base branches are not validated
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: PR identity validation checks only that the PR is open, not that its head and base branches are the expected ones.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_8: [OUT_OF_SCOPE] Strict-mode structural assertion is not fence-scoped
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: A file-global structural assertion could be satisfied by an unrelated Bash block rather than the publication fence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_9: [OUT_OF_SCOPE] Repository and checkout origin can diverge
- **Reviewer(s)**: cursor-specialist-edge-cases, codex-specialist-edge-cases, dyn-dyn-state-publish
- **Severity**: major
- **Concern**: The workflow pushes to `ANALYSIS_ROOT`’s `origin` while creating and merging a PR for `$REPO`, without verifying that both identify the same repository.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-state-publish: Address the concern above.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=true

### FINDING_10: PR state literals are unquoted
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: major
- **Concern**: Unquoted `OPEN` and `MERGED` values are interpreted as shell variables rather than string literals, breaking PR state checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_12: [OUT_OF_SCOPE] Filing terminology still references scan-marker commits
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: Filing prose uses terminology from the former scan-marker commit flow instead of the PR-based state publication flow.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### FINDING_13: [OUT_OF_SCOPE] No executable worktree-to-merge harness exists
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: The new live `pr create` path lacks an offline worktree-to-merge integration harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_16: [OUT_OF_SCOPE] State PRs inherit an unintended assignee
- **Reviewer(s)**: dyn-dyn-state-publish
- **Severity**: minor
- **Concern**: `gh.pr_create` defaults to assigning every state PR to `@me`, which may add operator noise.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-state-publish: Address the concern above.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_17: [OUT_OF_SCOPE] Structural tests remain grep-based
- **Reviewer(s)**: dyn-dyn-state-publish
- **Severity**: minor
- **Concern**: The structural suite continues to inspect prose rather than execute the publication fence, so runtime failures can pass CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-state-publish: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_18: [OUT_OF_SCOPE] Default-mode adoption checks remain stale during handoff
- **Reviewer(s)**: dyn-dyn-state-publish
- **Severity**: minor
- **Concern**: During manual-merge handoff, adoption checks against `ANALYSIS_ROOT` remain unchanged until the state PR merges.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-state-publish: Address the concern above.
Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false
