# Review Round 2

- Mode: `diff`
- 1 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_4: Step 5 persistence is not transactional
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases, dyn-dyn-bgjob-kv
- **Severity**: major
- **Concern**: Step 5 emits terminal state and writes the result env in an order that can leave stdout, the sentinel, and `.step5-review-result.env` inconsistent; handoff rows can be omitted, and persistence failures can still leave a success-looking terminal marker behind.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From codex-specialist-edge-cases: Persist the result env before writing the sentinel; remove any marker and emit a stall/internal-error envelope on persistence failure
  - From dyn-dyn-bgjob-kv: Return ledger rows from _record_escalation_if_needed and persist them into .step5-review-result.env; test handoff statuses for STEP5_REVIEW_LEDGER_* persistence.
  - From dyn-dyn-bgjob-kv: Fail closed the same way plan-review does—refuse symlinked tmpdirs/result-env paths with a loud error and a stall envelope, or propagate the `atomic_write` `OSError`—instead of returning `None` and continuing as if persistence succeeded.
  - From dyn-dyn-bgjob-kv: Write the merge env first (or wrap stdout emission and persistence in one transactional helper) so a persistence failure cannot produce a second contradictory envelope on stdout.


