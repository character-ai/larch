### OOS_1: [OUT_OF_SCOPE] Stable drafter sidecar copy failures can hide usage
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `scripts/launch-codex-drafter.sh` uses `cp || true` for the stable sidecar copy. If the copy fails after billable usage, the stable sidecar can stay empty and Step 2b can miss `codex_plan_draft` usage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### OOS_2: [OUT_OF_SCOPE] Rebase conflict-fixer ingestion lacks seen-set deduplication
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-risk-integration-output.txt
- **Severity**: latent
- **Concern**: Rebase conflict-fixer sidecar ingestion does not pass a per-waterfall `seen` set like CI monitor does. Retrying or relaunching a tier with the same sidecar path can append duplicate token rows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-risk-integration-output.txt: Address the concern above.


