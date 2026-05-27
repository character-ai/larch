### FINDING_14: [OUT_OF_SCOPE] Legacy step-5 snapshots may resume at the wrong step
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The registry walker skips step id `5` in favor of `5b`/`5c`/`5d`, so old `.completed/step-5` snapshots may resume at `5b` and repeat plan-write behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated


### FINDING_6: [OUT_OF_SCOPE] Plan marker read logic is not consolidated
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `scripts/plan-block-read.sh` has plan marker read logic that is not consolidated with named-block write/read helpers, so future marker grammar changes may need parallel updates.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated


### FINDING_7: [OUT_OF_SCOPE] Pause prelude lines are duplicated across fences
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `skills/design/SKILL.md` contains many copies of identical pause prelude lines, leaving drift risk for fences outside the harness-checked range.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated


