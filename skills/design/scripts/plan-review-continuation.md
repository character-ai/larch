# plan-review-continuation.sh

Computes the `/design` Step 3.5 automatic plan-review continuation decision from disk artifacts.

Inputs:
- `--design-tmpdir DIR`
- `--approve-requested true|false`

Output KVs:
- `PLAN_REVIEW_CONTINUE=true|false`
- `PLAN_REVIEW_CONTINUE_REASON=<small-clean|explicit-approve|cap-reached|degraded-panel|high-accepted|non-nit-accepted|structural-or-large-change>`
- `REVIEW_ROUND_COUNT=<N>`
- `REVIEW_ROUND_CAP=5`
- `ACCEPTED_COUNT=<N>`
- `NIT_ACCEPTED_COUNT=<N>`
- `NON_NIT_ACCEPTED_COUNT=<N>`
- `HIGH_ACCEPTED_COUNT=<N>`
- `DEGRADED_PANEL=0|1`
- `STRUCTURAL_OR_LARGE_CHANGE=true|false`

The helper recomputes accepted-finding counts from `accepted-plan-findings.md` instead of trusting in-memory KVs. It resolves tier from canonical `design_classification` in `run-params.json`; missing or invalid values default to `HARD`, and stale `workflow_path` does not override `design_classification`. It stops under `--approve` so explicit Gate B operator choices do not silently trigger another automatic review round. It also stops at the shared review cap before the caller invokes `run-step3-review.sh`, preserving the current round artifacts for Gate C.
