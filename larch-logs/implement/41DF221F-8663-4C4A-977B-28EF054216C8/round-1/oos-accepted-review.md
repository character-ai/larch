### OOS_1: [OUT_OF_SCOPE] `validate_manifest` accepts header-only manifest with zero data rows
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `validate_manifest` accepts a header-only manifest with zero data rows. An empty manifest yields `MANIFEST_STATUS=ok` and hides a missing cohort instead of failing closed on zero rows or below minimum cohort size.
- **Suggested revisions (informational for voters; coder decides)**:


