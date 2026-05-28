### FINDING_17: [OUT_OF_SCOPE] Finalize Duplicates KV Emission
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `finalize` duplicates KV emission to `revise.env` and stdout, including `REVISE_TIER` and `REVISE_WINNING_TIER`. The duplication existed before but is amplified by more keys.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral


### FINDING_18: [OUT_OF_SCOPE] Unrelated Redaction Test Path Move
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `secret_path` was relocated outside the design tmpdir in `scripts/test-design-log-publish.sh`, which appears unrelated to the revise waterfall feature.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected


### FINDING_19: [OUT_OF_SCOPE] Gate B Docs Omit `ok-fallback`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Gate B documentation does not mention `ok-fallback` in passive-summary mode, so operators reading gate prose may not distinguish fallback success from tier-1 unified-diff success.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_20: [OUT_OF_SCOPE] Branch Commit Inventory
- **Reviewer(s)**: dyn-extract-patch-python-output.txt
- **Severity**: nit
- **Concern**: The reviewer listed branch commits versus `main`; this is contextual inventory rather than an in-scope defect.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-extract-patch-python-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected


### FINDING_21: [OUT_OF_SCOPE] Unified-Diff Path Positive Assessment
- **Reviewer(s)**: dyn-extract-patch-python-output.txt
- **Severity**: nit
- **Concern**: The reviewer states the unified-diff fenced path correctly prefers the last diff block and that trailing prose causes `invalid-patch`, not silent wrong apply. This is a positive/diagnostic observation rather than an in-scope fix request.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-extract-patch-python-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected


### FINDING_22: [OUT_OF_SCOPE] Empty Extraction Exit 0 Is Intentional
- **Reviewer(s)**: dyn-extract-patch-python-output.txt
- **Severity**: nit
- **Concern**: The reviewer notes `write_lines([])` plus exit 0 intentionally drives `no-patch` handling, with Python failure covered separately.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-extract-patch-python-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected


