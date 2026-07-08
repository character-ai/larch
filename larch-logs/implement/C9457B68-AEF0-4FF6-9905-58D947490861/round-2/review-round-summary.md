# Review Round 2

- Mode: `diff`
- 1 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Step 5 stall envelopes are skipped when `BGJOB_RC` is non-zero
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-bgjob-flow
- **Severity**: major
- **Concern**: Step 5 still treats any non-zero `BGJOB_RC` as a generic failure before checking a valid `STEP5_REVIEW_STATUS=stall` envelope, so intentional stalls can bypass the stall branch and lose stall-specific handling, `STALL_TRACKING`, and Step 18 seeding.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Parse result env first; route STEP5_REVIEW_STATUS=stall through step5-review-branches.md even when numeric BGJOB_RC is non-zero; keep generic gate for missing status, timeout, and orphaned.
  - From cursor-specialist-correctness: Retain envelope STALL_TRACKING in the stall carve-out before persisting or seeding Step 18 state.
  - From codex-specialist-correctness: When non-zero BGJOB_RC arrives with a valid STEP5_REVIEW_STATUS=stall envelope, route through the Step 5 stall branch. Use generic preflight/stall only for missing or malformed envelopes.
  - From cursor-specialist-edge-cases: Parse STEP5_REVIEW_STATUS first for valid stall envelopes, or exit 0 from review-and-fix on intentional stall
  - From cursor-specialist-testing: Add a Step 5 carve-out to branch on STEP5_REVIEW_STATUS=stall before the generic non-zero BGJOB_RC gate; pin ordering in structure tests and add a BGJOB_RC=2 stall-envelope regression test.
  - From dyn-dyn-bgjob-flow: After reading the final wait stdout and $IMPLEMENT_TMPDIR/bgjob/implement-step5-review.result.env, branch on a present STEP5_REVIEW_STATUS=stall envelope (and its required KVs) before the generic non-zero BGJOB_RC gate; reserve the unconditional BGJOB_RC != 0 fast-path for timeout, orphaned, DEAD, and envelopes missing STEP5_REVIEW_STATUS. Pin the ordering in scripts/test-implement-structure.sh.


