### OOS_11: [OUT_OF_SCOPE] Hybrid signal-and-sidecar dedup is only a coverage gap
- **Reviewer(s)**: dyn-ns-retry-orphan-dedup-output.txt
- **Severity**: nit
- **Concern**: Tests do not cover the hybrid `reviewer_signals` plus matching sidecar case, but manual execution dedupes it correctly to count 1.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ns-retry-orphan-dedup-output.txt: Address the concern above.


### OOS_12: [OUT_OF_SCOPE] In-progress extraction ignores since-version binning
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `--include-in-progress` rows are omitted from version-only `--since-version` pre/post binning without an explicit warning.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


