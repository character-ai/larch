### OOS_1: [OUT_OF_SCOPE] step5 result-env classifier mislabels stall as complete
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-plan-fidelity-auto, dyn-dyn-step5-recovery
- **Severity**: major
- **Concern**: `step5_canonical_result_env_state` can treat a `BGJOB_RC=0` envelope as complete even when the recorded Step 5 status is stalled, so cached stall envelopes may be reused instead of being cleared for a fresh relaunch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-plan-fidelity-auto: Address the concern above.
  - From dyn-dyn-step5-recovery: `step5_canonical_result_env_state` labels a result env `complete` whenever `BGJOB_RC=0` and all required Step 5 keys are present, without requiring `STEP5_REVIEW_STATUS=complete` or rejecting `STEP5_REVIEW_STATUS=stall`. A canonical env with `BGJOB_RC=0` plus a stall envelope would take the reuse branch at `step-5-review.sh:212-214` instead of the stall-clearing path, reproducing the cached-stall replay this change is meant to eliminate. Today’s panel-failed child usually exits non-zero, so this is latent rather than observed, but the classifier is fail-open on an integrity-sensitive boundary. **Suggested fix:** Tighten the `complete` predicate to require `STEP5_REVIEW_STATUS=complete` (or explicitly `!= stall`), and add a harness case that seeds `BGJOB_RC=0` with `STEP5_REVIEW_STATUS=stall` and asserts a fresh start, not `bgjob wait` reuse.


