### OOS_1: [OUT_OF_SCOPE] single-target consecutive retry sums instead of deduping
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: When a shard has one target retried consecutively (e.g. `test-a` 10s then `test-a` 12s), the implementation sums 22.0 instead of taking the latest 12.0. This path is undetected and untested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add test documenting intended behavior or extend split logic if consecutive same-target replay should count as retry


