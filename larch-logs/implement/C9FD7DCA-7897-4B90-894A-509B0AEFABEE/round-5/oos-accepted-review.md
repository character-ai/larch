### OOS_13: [OUT_OF_SCOPE] Design review round count increments before terminal snapshot
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `run-step3-review.sh` increments `review-round-count.txt` before `plan-review-loop` completes, so a crash mid-round can skip retry on the next Step 3 invocation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### OOS_14: [OUT_OF_SCOPE] Prune-decision idempotency guard is inconsistent
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `plan-review-loop.sh` and `review-core.sh` use different guards for existing `prune-decision.env`, so zero-byte files block design default writes but not implement default writes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


