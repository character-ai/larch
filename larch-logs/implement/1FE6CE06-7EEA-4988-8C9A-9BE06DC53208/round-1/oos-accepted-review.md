### FINDING_17: [OUT_OF_SCOPE] `design-publish.sh` may trust `PUBLISH_OK=true` despite non-zero publish exit
- **Reviewer(s)**: dyn-bash-contract-output.txt
- **Severity**: important
- **Concern**: If `design-log-publish.sh` exits non-zero while stdout contains `PUBLISH_OK=true`, failure branches may be skipped and rename may proceed; reviewer marked this as restored pre-existing envelope behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-contract-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted


