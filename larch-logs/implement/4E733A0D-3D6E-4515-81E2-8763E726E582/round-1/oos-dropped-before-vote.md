### OOS_1: [OUT_OF_SCOPE] Stale “only retryable validation failure” comment (`python/review_aggregate.py:29-32`)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The block comment above `_OOS_ATTRIBUTION_RC` still claims OOS-attribution is the only semantically retryable validation failure. That was already wrong after `#5077`/`#5222` and is more misleading now that `_PREAMBLE_SLIP_RC` exists. Pre-existing doc drift; not introduced by this diff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Update the comment to describe the full retryable set or defer to per-constant docs.
  - From cursor-specialist-testing-output.txt: Update or remove the outdated block comment in a follow-up docs-only change.

### OOS_2: [OUT_OF_SCOPE] Generic retry prompt for `preamble_finding_substring` slips (`python/review_aggregate.py:679-706`)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Preamble slips use the generic `_validation_retry_prompt` (e.g. “Fix exactly the error reported above…”) with opaque `AGGREGATOR_VALIDATION_FAILED=preamble_finding_substring`. The model may not understand it must emit structured `### FINDING_N:` blocks; retries may exhaust and degrade to unmerged findings. The plan left tailored preamble guidance as an open question; tests show generic feedback can succeed once, but production retry rate is not measured here.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add preamble-tailored guidance in `_validation_retry_prompt` when that token is present.
  - From cursor-specialist-testing-output.txt: Consider preamble-specific retry text only if post-merge telemetry shows repeated exhaust under generic guidance.

### OOS_3: [OUT_OF_SCOPE] `LARCH_AGGREGATE_REVISION_TRACE_STRICT=1` still maps `validate_rc == 1` to non-retryable stall (`python/review_aggregate.py:584-585`)
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `LARCH_AGGREGATE_REVISION_TRACE_STRICT=1` still maps `validate_rc == 1` to the non-retryable stall path, the same class of recoverable LLM slip as the preamble bug. Pre-existing behavior outside this diff’s scope.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_4: [OUT_OF_SCOPE] No focused unit test for `_PREAMBLE_SLIP_RC` mapping (`python/test_review_aggregate.py`)
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: No focused `_validate_aggregate_output` unit test asserting `rc == _PREAMBLE_SLIP_RC` for preamble-only output (unlike `#5022`’s suffix-variant unit test). Integration tests cover behavior end-to-end; a small unit test would only guard the RC mapping.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Optional follow-up if you want parity with other validation classes.

