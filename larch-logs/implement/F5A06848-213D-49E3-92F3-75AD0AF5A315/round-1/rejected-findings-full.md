### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: agg-zero test overmatches VOTER_ output
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `skills/review/scripts/test-review-core.sh` checks the full `review-core` output for any `VOTER_` text. Future unrelated KV lines or breadcrumbs containing `VOTER_` could fail `agg-zero` even when voter dispatch was correctly skipped.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_4: Correctness reviewer included commit listing instead of a behavioral finding
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: The reviewer output entries for commits `45186750`, `16e17510`, and `6d34e1e3` are commit inventory and plan-verification prose rather than actionable behavioral risks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_6: Missing regression for ok aggregate with nonzero MERGED_COUNT
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `skills/review/scripts/test-review-core.sh` lacks a stub case for `REASON=ok` with `MERGED_COUNT>0`. A broadened short-circuit could skip voting for aggregates that contain findings while existing disabled-aggregator tests remain green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: Empty-merge short-circuit trusts aggregate KV without findings guard
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `skills/review/scripts/review-core.sh` skips voter dispatch based only on aggregate env values `REASON=ok` and `MERGED_COUNT=0`. If the aggregate env is corrupt or substituted while `findings.md` still contains finding blocks, the review can finish as `zero-findings` incorrectly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

