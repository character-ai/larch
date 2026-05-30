### OOS_1: [OUT_OF_SCOPE] fixup depth vs drop walk on deep histories (local uncommitted change noted)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Fixup commits without a matching `--max-depth` bump can leave the bump outside the drop walk on deep histories; continue path may force-push a stale bump. Source flags this as tied to local uncommitted depth-bump work rather than the committed diff under review.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Increase --max-depth with fixup count (local uncommitted change)


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_2: [OUT_OF_SCOPE] fixup subject does not collide with drop-bump / changelog matchers
- **Reviewer(s)**: dyn-git-add-scope-output.txt
- **Severity**: nit
- **Concern**: `chore: pre-rebase working-tree fixup (#3209)` does not match `drop-bump-commit.sh` Guard 2 bump regex or `drop-changelog-commit.sh` exact changelog subject; no collision found for those matchers.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_3: [OUT_OF_SCOPE] Option A `git add -u` semantics are intentional for staged tracked dirt
- **Reviewer(s)**: dyn-git-add-scope-output.txt
- **Severity**: nit
- **Concern**: For modified/deleted tracked files and index-only staged tracked changes, `git add -u` plus cached diff behaves as the plan describes; sweeping pre-existing staged tracked changes into the fixup commit is intentional, not index loss.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_4: [OUT_OF_SCOPE] working tree already contains fixes not on reviewed HEAD
- **Reviewer(s)**: dyn-git-add-scope-output.txt
- **Severity**: nit
- **Concern**: Uncommitted edits in `scripts/ship-pr.sh` and `skills/review-and-fix/scripts/review-and-fix.sh` reportedly already address submodule revert, decoupled add/commit, `git add -u` follow-up, fail-closed `return 2`, two-pass fixup, and `--max-depth` bump—but those fixes are not on `HEAD` (`65fa13777`); review targeted the committed diff.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_5: [OUT_OF_SCOPE] fixup subject is not a transparent bump-pipeline commit for classify-bump
- **Reviewer(s)**: dyn-git-add-scope-output.txt
- **Severity**: nit
- **Concern**: The fixup subject is not classified as a transparent bump-pipeline commit per `classify-bump.sh`; a fixup above the bump is handled by `drop-bump-commit.sh` replay walk, not mis-identified as the bump commit.
- **Suggested revisions (informational for voters; coder decides)**:

Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

