### FINDING_10: [OUT_OF_SCOPE] Shared concurrency lock blocks design and implement independently
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: A shared five-minute concurrency lock can make one skill’s audit filing block the other unless `--allow-concurrent` is used; reviewer marked this as a documented follow-up.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_14: [OUT_OF_SCOPE] Main already included broad non-run-log PRs
- **Reviewer(s)**: dyn-skill-filter-leak-output.txt
- **Severity**: nit
- **Concern**: The reviewer notes that broad inclusion of unmapped feature PRs is pre-existing on `main`; the implement branch mainly narrows by excluding design-titled PRs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-skill-filter-leak-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_15: [OUT_OF_SCOPE] `--log-root` validation bypass is not used by production skill paths
- **Reviewer(s)**: dyn-skill-filter-leak-output.txt
- **Severity**: nit
- **Concern**: The reviewer marks arbitrary temp `--log-root` validation as non-production because hermetic tests intentionally use temp roots and production SKILL paths do not pass `--log-root`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-skill-filter-leak-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_16: [OUT_OF_SCOPE] `run-dir-invalid` guard catches skill-root paths
- **Reviewer(s)**: dyn-skill-filter-leak-output.txt
- **Severity**: nit
- **Concern**: The reviewer notes that `audit-scan-run.sh` already rejects skill-root paths such as `larch-logs/design` or `larch-logs/$SKILL/`; per-run UUID paths remain valid.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-skill-filter-leak-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_17: [OUT_OF_SCOPE] Mis-titled design PRs can leak into implement bulk lists
- **Reviewer(s)**: dyn-skill-filter-leak-output.txt
- **Severity**: latent
- **Concern**: A design PR using a flush-style title rather than the expected design publication title would not match the design regex and could be included in implement lists; reviewer frames this as an edge case if title generation diverges.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-skill-filter-leak-output.txt: Address the concern above.

Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

