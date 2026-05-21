### FINDING_3: [OUT_OF_SCOPE] Dry-run contract omits some printed keys
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: The dry-run documentation does not list `RELEASE_REPO` and `RELEASE_PUBLISHED_AT` even though the script prints them before exit in dry-run mode, so enumerating keys from the doc alone is incomplete.
- **Suggested revision**: If tightening dry-run documentation is desired, extend the dry-run bullet to include those keys (or explicitly scope the dry-run key list); treat as optional follow-up.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated


