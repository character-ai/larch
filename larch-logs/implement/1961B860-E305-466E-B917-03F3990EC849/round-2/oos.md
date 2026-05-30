### OOS_1: [OUT_OF_SCOPE] Global drop-bump max-depth 20 predates fixups
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Global max-depth 20 window predates fixups; long branches can miss bump even without fixups—broader depth policy separate from #3209.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_10: [OUT_OF_SCOPE] Stale rc after fixup not primary drop-bump failure mode
- **Reviewer(s)**: dyn-set-e-safety-output.txt
- **Severity**: nit
- **Concern**: After fixup, `drop-bump-commit.sh` immediately reassigns `rc=$?`; main failure mode is abort-before-`rc=$?` under errexit, not stale `rc` at drop time.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-set-e-safety-output.txt: Address the concern above.

Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### OOS_2: [OUT_OF_SCOPE] fix-loop harness shard size / CI runtime
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: fix-loop section already long; new rebump cases add CI time—consider dedicated Makefile target when rebalancing shards.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### OOS_3: [OUT_OF_SCOPE] larch-logs on branch unrelated to #3209 code plan
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Design/implement run-log trees on branch are unrelated to #3209 code plan scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### OOS_4: [OUT_OF_SCOPE] Fixup subject not mistaken for bump/changelog drop targets
- **Reviewer(s)**: dyn-git-add-scope-output.txt
- **Severity**: nit
- **Concern**: Subject `chore: pre-rebase working-tree fixup (#3209)` does not match bump or changelog drop subject guards; will not be mistaken for drop targets.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_5: [OUT_OF_SCOPE] Primary review-and-fix round `git add -A` predates follow-up block
- **Reviewer(s)**: dyn-git-add-scope-output.txt
- **Severity**: nit
- **Concern**: Primary round-mode staging at `review-and-fix.sh:438` already uses `git add -A` and is documented; scout asymmetry applies to the new follow-up block only.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_6: [OUT_OF_SCOPE] Working tree already contains fixes if committed
- **Reviewer(s)**: dyn-git-add-scope-output.txt
- **Severity**: nit
- **Concern**: Uncommitted working tree already switches follow-up to `git add -u`, adds `return 2` on persistent residue, second Option A pass, and `drop_max_depth=21` when fixup created—addresses in-scope items if committed.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### OOS_7: [OUT_OF_SCOPE] Committed elif add/commit coupling fixed only in uncommitted revision
- **Reviewer(s)**: dyn-git-add-scope-output.txt
- **Severity**: nit
- **Concern**: Committed `ship-pr.sh` `elif ! git diff --cached` after failed `git add -u` skips fixup commit when index already staged; uncommitted revision separates checks.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### OOS_8: [OUT_OF_SCOPE] pr-prep phase leaves errexit on for later ship-pr phases
- **Reviewer(s)**: dyn-set-e-safety-output.txt
- **Severity**: latent
- **Concern**: `run_pr_prep_phase` runs `set +e` for OOS gate then `set -e` without restoring `set +e` for the rest of the process—pre-existing, widens blast radius of errexit on fixup block.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-set-e-safety-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_9: [OUT_OF_SCOPE] _stage_and_push_ci_fixes bare git add/rc shape pre-existing
- **Reviewer(s)**: dyn-set-e-safety-output.txt
- **Severity**: latent
- **Concern**: `_stage_and_push_ci_fixes` uses same bare `git add` / `rc=$?` shape as new fixup block; not introduced by this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-set-e-safety-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

