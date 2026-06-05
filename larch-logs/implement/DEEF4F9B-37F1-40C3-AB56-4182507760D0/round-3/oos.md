### FINDING_13: [OUT_OF_SCOPE] Approval-gates bypass prose omits completion boundary
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-harness-output.txt
- **Severity**: nit
- **Concern**: `approval-gates.md` says bypass paths go before Step 3b without naming the Step 3b completion boundary before Step 4, weakening documentation consistency.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, dyn-harness-output.txt: Address the concern above.


Vote tally: YES=2 NO=1 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_14: [OUT_OF_SCOPE] Pause step inference may drift from FINALIZE sentinel naming
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Pause step inference skips registry step 5 while FINALIZE uses `.completed/finalize`, which could desynchronize future step-5 sentinel changes from FINALIZE idempotency.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### FINDING_15: [OUT_OF_SCOPE] Legacy pause/resume paths appear sound
- **Reviewer(s)**: dyn-resume-output.txt, dyn-shell-fences-output.txt
- **Severity**: nit
- **Concern**: Reviewers observed that legacy SIMPLE and FINALIZE compatibility paths appear to repair or fail as intended.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-resume-output.txt, dyn-shell-fences-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_16: [OUT_OF_SCOPE] Pause-save/load ordering appears consistent with new boundary
- **Reviewer(s)**: dyn-resume-output.txt
- **Severity**: nit
- **Concern**: Reviewer observed that pause-save inference and HARD 3b-to-3.6 remapping remain consistent with the new completion boundary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-resume-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_20: [OUT_OF_SCOPE] Assessor references do not forward-declare completion boundary
- **Reviewer(s)**: dyn-routing-output.txt
- **Severity**: nit
- **Concern**: Assessor-related files still say to continue to Step 3b without explicitly declaring the Step 3b completion boundary before Step 4.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-routing-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_21: [OUT_OF_SCOPE] FINALIZE idempotency is now load-bearing for re-review routing
- **Reviewer(s)**: dyn-routing-output.txt
- **Severity**: latent
- **Concern**: `design-driver.sh` skips FINALIZE when `.completed/finalize` exists; this pre-existing behavior becomes risky if any re-review route fails to hit the Step 3b completion boundary and fresh Step 4 read.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-routing-output.txt: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### FINDING_25: [OUT_OF_SCOPE] Routing guard scanned surfaces appear aligned
- **Reviewer(s)**: dyn-shell-fences-output.txt
- **Severity**: nit
- **Concern**: Reviewer observed that the scanned routing surfaces currently align with the folded-boundary design and contain no bare Step 3b-to-Step 4 bypasses.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-fences-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_30: [OUT_OF_SCOPE] Step 4 anchor strings diverge in structure test
- **Reviewer(s)**: dyn-harness-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-design-structure.sh` uses two different Step 4 anchor strings, which both match today but could deslice regions after future edits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-output.txt: Address the concern above.

Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_6: [OUT_OF_SCOPE] Duplicate zero-findings routing prose in plan-review
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `plan-review.md` duplicates zero-findings routing prose, so future routing changes require editing repeated long text.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

