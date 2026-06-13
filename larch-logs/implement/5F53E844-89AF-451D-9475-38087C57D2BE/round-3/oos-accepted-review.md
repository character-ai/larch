### OOS_7: [OUT_OF_SCOPE] Plan targeted full Python port; branch delivers delegation
- **Reviewer(s)**: dyn-review-cli-parity-output.txt
- **Severity**: important
- **Concern**: The plan targets a full Python port of C1b surfaces; the branch instead adds thin `run_legacy` wrappers over relocated bash in `python/legacy_review_shell/`. Behavior parity is plausible, but it is delegation rather than the planned importable Python implementation.


