### FINDING_18: [OUT_OF_SCOPE] Case 29 omits legacy hard trigger with `diff_deleted` only
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Case 29 does not assert legacy hard trigger when `diff_deleted` is present but `diff_lines` exceeds 1500 without `diff_added` (harness gap; implementation may already be correct).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_4: [OUT_OF_SCOPE] Missing script-md stubs for design `lib-*.sh`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Skill-local `lib-*.sh` files lack script-md sibling stubs required elsewhere in the repo, making argv, callers, and edit-in-sync rules harder to discover (pre-existing gap also noted for `lib-findings-classification.sh`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_5: [OUT_OF_SCOPE] Redundant optional-trailer validation on file-replacement path
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `revise-plan-with-waterfall.sh` validates optional trailers on the candidate and again on `plan.txt` after apply, adding extra full-file awk passes on every tier-4 success; post-apply validation alone may suffice unless early reject is needed for clearer errors.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

