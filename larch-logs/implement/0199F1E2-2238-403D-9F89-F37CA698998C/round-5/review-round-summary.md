# Review Round 5

- Mode: `diff`
- 5 accepted, 4 rejected (3 neutral)

## Accepted Findings

### FINDING_3: Postplan-operator resume contract omits required marker and phase handling
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: The documented postplan-operator resume contract omits the loop’s `awaiting-postplan-operator` phase and `.postplan-operator-continue-N` marker, so Gate B Override/Continue resume can re-bail forever instead of continuing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_4: Postplan continue marker can skip HARD snapshot and cursor work
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: In HARD designs, a postplan operator Continue can resume at continuation without required `plan-after-round-1.txt` and cursor advancement, allowing later rounds to reuse cursor 1 and overwrite round-1 artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_7: Resume infers apply success from plan diff instead of explicit success marker
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Resume can treat `plan.txt` differing from the pre-apply snapshot as successful apply even if the reviser died after a partial write but before validation/revert/status, allowing postprocessing of a corrupted plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_8: Final envelope can over-report or clobber review round counts
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The final envelope persists loop-local `round_num` into `STEP3_REVIEW_ROUND_NUM` and `REVIEW_ROUND_COUNT` even for paths that did not consume that round, causing cap-hit or failed-round paths to report incorrect count state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_9: Pause/resume harness misses loop re-entry after awaiting-post-apply restore
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The pause/resume harness restores `awaiting-post-apply` state but never re-invokes the loop, so it does not exercise the exactly-once apply invariant and may miss double-apply behavior on resume.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

