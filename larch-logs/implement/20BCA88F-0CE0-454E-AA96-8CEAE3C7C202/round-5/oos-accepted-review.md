### FINDING_16: [OUT_OF_SCOPE] Merge-pr read calls remain unwrapped
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `scripts/merge-pr.sh` leaves `gh pr view` and `gh pr checks` calls without transient retry. Reviewers marked this as pre-existing or outside the current plan scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_17: [OUT_OF_SCOPE] Rebase no-push fetch remains unwrapped
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/rebase-push.sh --no-push` still hard-fails a bare `git fetch` without transient retry. Reviewer marked this as pre-existing and outside the current plan file list.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_18: [OUT_OF_SCOPE] Create-pr failure diagnostics are unredacted
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `scripts/create-pr.sh` logs raw PR create stderr/stdout-tail diagnostics without redaction on failure. Reviewer marked this as pre-existing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_19: [OUT_OF_SCOPE] Issue create failure emits unredacted output
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `.claude/skills/combine-issues/scripts/apply-combination.sh` emits unredacted `CREATE_OUT` on issue-create failure. Reviewer marked this as pre-existing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_20: [OUT_OF_SCOPE] Create-pr lost-success duplicate risk remains
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `scripts/create-pr.sh` wraps `gh pr create` and has recovery, but a lost-success duplicate-PR risk may remain if recovery misses; reviewer marked this as not introduced solely by this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted


