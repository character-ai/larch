## Proposed Design Outline

### Goals
- Require `STEP5_REVIEW_STATUS=complete` (not just truthy) in the `step5_canonical_result_env_state` classifier when `BGJOB_RC=0`, so a stall envelope with `BGJOB_RC=0` is never classified as complete.
- Add a test case that seeds `BGJOB_RC=0` + `STEP5_REVIEW_STATUS=stall` (all required keys) and asserts a fresh bgjob start, not reuse.

### Non-goals
- Not touching the live-registry clearing path beyond what the classifier fix already covers.
- Not changing behavior for `BGJOB_RC != 0` stall envelopes (already handled correctly).
- Not modifying other bgjob state classifiers.

### Approach sketch
- One-line fix in `step5_canonical_result_env_state`: change `status and` to `status == "complete" and` on the `BGJOB_RC=0` predicate.
- Add a new stall-env fixture (or inline seed) in `test-step-5-review.sh` with `BGJOB_RC=0`.
- Assert `bgjob-start-argv.txt` exists and `implement-step5-review.result.env` is cleared after the wrapper runs.

### Surfaces in scope
- `skills/implement/scripts/step-5-review.sh`
- `skills/implement/scripts/test-step-5-review.sh`

### Open questions
- None.
