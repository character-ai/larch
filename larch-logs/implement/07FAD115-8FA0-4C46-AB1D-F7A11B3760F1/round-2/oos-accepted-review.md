### OOS_2: [OUT_OF_SCOPE] Partial OOS issue-batch failure can duplicate issues on retry (`python/oos_filer.py`)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: On partial issue-batch failure, the flow exits before persisting sentinel/ndjson for successful creates. A retry after mid-batch failure can duplicate GitHub issues for items already created in the first attempt.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Extend persisted-evidence reuse to partial batch failures, not only checkpoint failures.


