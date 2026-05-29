### FINDING_13: [OUT_OF_SCOPE] git-push has a parallel retry mechanism
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/git-push.sh` retains a separate push-retry stack predating the `lib-net` lift, leaving dual retry mechanisms across call chains.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=1 Result=exonerated

### FINDING_14: [OUT_OF_SCOPE] merge-pr gh pr view/checks use local retry
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/merge-pr.sh` still uses local retry handling for `gh pr view/checks` rather than `with_transient_retry`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### FINDING_15: [OUT_OF_SCOPE] create-pr conflict recovery uses bare gh pr list
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `scripts/create-pr.sh` conflict recovery calls bare `gh pr list`, so a transient failure during recovery can miss an existing PR.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### FINDING_16: [OUT_OF_SCOPE] design-log publish removes worktree before merge failure handling
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `scripts/design-log-publish.sh` removes the worktree before checking merge failure outcome, which can prevent local inspection even though `RECOVERY_BRANCH` is emitted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=1 Result=exonerated

