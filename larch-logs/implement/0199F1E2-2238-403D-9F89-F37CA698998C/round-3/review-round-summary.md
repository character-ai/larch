# Review Round 3

- Mode: `diff`
- 11 accepted, 4 rejected (1 neutral)

## Accepted Findings

### FINDING_10: Postplan return-code harness coverage is too narrow
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `test-review-design-step3-loop.sh` only covers postplan rc 12, leaving rc 10, 11, 13, 14, and failure routing unpinned.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_11: Orchestrator fence harness maps `postplan-failed` to complete
- **Reviewer(s)**: dyn-loop-integration-output.txt
- **Severity**: important
- **Concern**: `test-step3-orchestrator-fence.sh` diverges from SKILL routing by mapping `postplan-failed` to `LOOP_STATUS=complete`, so harness logic can normalize a hard postplan failure into a healthy completed round.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-loop-integration-output.txt: Address the concern above.


### FINDING_12: Loop envelope can persist contradictory terminal status
- **Reviewer(s)**: dyn-loop-integration-output.txt
- **Severity**: important
- **Concern**: `step3_loop_persist_envelope` can write `LOOP_STATUS=complete` alongside terminal or bail-out `STEP3_REVIEW_LOOP_STATUS` values, while continuation helpers read only `LOOP_STATUS`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-loop-integration-output.txt: Address the concern above.


### FINDING_16: Reviser phase marker can allow duplicate application after crash
- **Reviewer(s)**: dyn-phase-marker-consistency-output.txt
- **Severity**: important
- **Concern**: The phase file remains `awaiting-apply` until after `revise-plan-with-waterfall.sh` returns, so a crash after `plan.txt` changes but before phase promotion can resume by re-running the reviser on an already revised plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-phase-marker-consistency-output.txt: Address the concern above.


### FINDING_17: `postplan-operator-required` resume contract can re-run postplan
- **Reviewer(s)**: dyn-phase-marker-consistency-output.txt
- **Severity**: important
- **Concern**: `postplan-operator-required` leaves phase state prompt-managed and ambiguous; without an atomic phase transition and scoped resume contract, the loop or Gate B idempotency path can re-run `design-postplan-emit.sh` instead of advancing to continuation. The harness also does not pin the relevant phase/ready-marker state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-phase-marker-consistency-output.txt: Address the concern above.


### FINDING_2: Cap-hit envelope reports completed rounds as zero
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: On cap-hit after multiple review rounds, the result envelope can persist `ROUNDS_COMPLETED=0` while `FINAL_ROUND_NUM` reflects the actual final round, corrupting round accounting for logs and consumers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_3: `postplan-failed` is not mechanically fail-closed
- **Reviewer(s)**: codex-specialist-correctness-output.txt, dyn-loop-integration-output.txt
- **Severity**: important
- **Concern**: `postplan-failed` is described as a hard terminal, but the documented Step 3/3.5 flow can still continue into Gate B / Step 3b without a hard halt or fail-closed sentinel.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, dyn-loop-integration-output.txt: Address the concern above.


### FINDING_6: Retally env refresh can preserve stale loop status
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `_rewrite_env_file` in `persist-retally-step3-env.sh` can retain stale `STEP3_REVIEW_LOOP_STATUS`, causing pause/reentry to prioritize an old MAV or rollback envelope after retally.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_7: Per-round approval does not refresh canonical accepted/rejected artifacts
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The approval handoff records only `FINDINGS_FILE`; skipped findings can remain stale in canonical accepted artifacts and be reprocessed on continuation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_8: Mid-loop pause/resume coverage is missing for plan-required Step 3 paths
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `test-design-pause-resume.sh` lacks cases for pauses during `awaiting-post-apply` or postplan rc 11, leaving double-apply or re-review regressions untested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_9: Step 3 rc=2 path prints abort but may continue
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The Step 3 fence says `run-step3-review.sh` exit 2 aborts, but does not hard exit/return, so invalid phase evidence can continue toward Step 3b/Gate C.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Address the concern above.


