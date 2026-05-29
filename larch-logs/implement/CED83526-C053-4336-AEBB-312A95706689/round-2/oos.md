### FINDING_29: [OUT_OF_SCOPE] Claude assessor dispatch is synchronous
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Claude assessor runs synchronously before the waterfall instead of parallel with all three slots. This affects latency, not verdict correctness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_30: [OUT_OF_SCOPE] Dispatch failure behavior also observed by out-of-scope reviewers
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-tally-bash32-output.txt
- **Severity**: nit
- **Concern**: Out-of-scope review notes also observed that `assess-plan-round.sh` tallies after `DISPATCH_OK=false` and that tests currently expect partial outputs to be tallied, diverging from the written plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, dyn-tally-bash32-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### FINDING_31: [OUT_OF_SCOPE] Cursor/snapshot sequencing mostly verified OK
- **Reviewer(s)**: dyn-cursor-write-last-output.txt
- **Severity**: nit
- **Concern**: The split sequencing between cursor advancement, write-after, and atomic snapshot/cursor paths appears intentional and mostly sound when the feature file is present.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cursor-write-last-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_32: [OUT_OF_SCOPE] Short-circuit paths skip Step 3.6 by design
- **Reviewer(s)**: dyn-cursor-write-last-output.txt
- **Severity**: nit
- **Concern**: Some degraded or cap-reached paths omit `plan-after-round-N.txt`, but Step 3’s advance-only-if-snapshot-exists rule may prevent permanent cursor drift on re-entry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cursor-write-last-output.txt: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### FINDING_33: [OUT_OF_SCOPE] FD3 routing itself is probably not silently empty
- **Reviewer(s)**: dyn-breadcrumb-pair-contract-output.txt
- **Severity**: nit
- **Concern**: `dispatch-plan-assessors.sh` emits KVs through FD3, and under quiet init those lines should land in the quiet log. The main risks are noisy parsing and missing tests, not silent FD3 loss.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-breadcrumb-pair-contract-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_34: [OUT_OF_SCOPE] Branch commit list was reported
- **Reviewer(s)**: dyn-breadcrumb-pair-contract-output.txt
- **Severity**: nit
- **Concern**: Reviewer reported branch commits since merge-base with `main`; this is diagnostic context, not a code finding.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-breadcrumb-pair-contract-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_35: [OUT_OF_SCOPE] Bash 3.2 array usage appears acceptable
- **Reviewer(s)**: dyn-tally-bash32-output.txt
- **Severity**: nit
- **Concern**: Bash 3.2 portability for array constructs in `tally-plan-assessor.sh` appears consistent with repo practice; no defect was found there.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-tally-bash32-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_36: [OUT_OF_SCOPE] strip_md_bold removes all asterisks but behaves acceptably
- **Reviewer(s)**: dyn-tally-bash32-output.txt
- **Severity**: nit
- **Concern**: `strip_md_bold` removes all `*` characters on header lines rather than paired bold markers only, but this still handles the intended bold-header cases.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-tally-bash32-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_37: [OUT_OF_SCOPE] Pre-existing voter timing-kind drift
- **Reviewer(s)**: dyn-timing-kind-allowlist-output.txt
- **Severity**: nit
- **Concern**: The same phase-qualified timing-kind synthesis drift exists for plan voters and predates this assessor branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-timing-kind-allowlist-output.txt: Address the concern above.

Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

