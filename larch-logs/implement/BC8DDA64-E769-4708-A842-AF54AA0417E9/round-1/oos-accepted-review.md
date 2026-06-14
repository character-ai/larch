### OOS_1: [OUT_OF_SCOPE] Pytest parity matrix incomplete vs plan
- **Reviewer(s)**: dyn-step5-contract-output.txt
- **Severity**: important
- **Concern**: `python/test_review_and_fix.py` covers only a happy-path loop, single-round KV emission, and a few helper contracts. The plan listed dozens of Step 5 parity cases (lint cap, bulk-skip, MAV relocated head, `mav-resume-past-cap`, escalation sidecar, degraded retry) not present in pytest, so deleted bash harness coverage was not fully replaced on this branch.


### OOS_2: [OUT_OF_SCOPE] `.gitleaks.toml` allowlist references deleted harness paths
- **Reviewer(s)**: dyn-step5-contract-output.txt, dyn-migration-surface-output.txt
- **Severity**: important
- **Concern**: `.gitleaks.toml` still allowlists deleted harness paths (`skills/review-and-fix/scripts/test-review-and-fix.sh`, `skills/implement/scripts/test-write-rejected-findings.sh`) even though those files were removed and listed in `python/migrated-scripts.tsv`. Description was partially updated but `paths` array was not fully reconciled.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-step5-contract-output.txt: harmless for runtime correctness but stale config.
  - From dyn-migration-surface-output.txt: Remove the retired shell paths from `paths`, add `^python/test_review_and_fix\.py$` if fixture tokens land there, and keep description/paths in sync.


