### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: `ci-status` parses `BEHIND_COUNT` with `awk` instead of `kv_value`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Parsing diverges from `ship-pr.sh` contract-stream handling; extra lines or format changes could desync poll vs push interpretations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: `_stage_and_push_ci_fixes` grew into a multi-phase god function
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The CI-fix push pipeline (stage, behind rebase, re-verify, push) is hard to review and extend safely under ongoing #3132 refactor pressure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: Vendor rotation only on outer `_fix_attempt`, not after in-call verify failure
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Waterfall rotation may not match acceptance wording for trying a different fixer before bail when inner post-rebase verify fails once; outer-retry semantics may need documentation or an in-call waterfall retry before return.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: `_verify_failed_jobs_locally` exit 3 in post-rebase path
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Exit 3 (`ci-local-unfixable`) may terminate `ship-pr` instead of mapping to stall/retry behavior expected on the post-rebase verify path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

