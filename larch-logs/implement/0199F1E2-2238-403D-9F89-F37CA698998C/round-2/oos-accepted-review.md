### OOS_5: [OUT_OF_SCOPE] Mid-loop pause/resume coverage is missing
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-state-protocol-output.txt, dyn-legacy-coexistence-output.txt
- **Severity**: important
- **Concern**: The test suite lacks plan-mandated coverage for in-loop pause, postplan rc 11 resume, default starting-round recovery, and skip-reapply invariants, leaving pause/resume regressions without CI signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, dyn-state-protocol-output.txt, dyn-legacy-coexistence-output.txt: Address the concern above.


### OOS_6: [OUT_OF_SCOPE] Continuation helper failures are mislabeled as postplan failures
- **Reviewer(s)**: dyn-state-protocol-output.txt
- **Severity**: latent
- **Concern**: Continuation helper failure is surfaced as STEP3_REVIEW_LOOP_STATUS=postplan-failed and inherits the same complete remap problem, confusing envelope semantics and operator diagnostics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-protocol-output.txt: Address the concern above.


### OOS_7: [OUT_OF_SCOPE] cap-hit envelope reports completed rounds incorrectly
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-state-protocol-output.txt
- **Severity**: important
- **Concern**: cap-hit uses terminal_rounds=0, so ROUNDS_COMPLETED is always 0 and FINAL_ROUND_NUM can point at the unrun cap round instead of the last consumed review round.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, dyn-state-protocol-output.txt: Address the concern above.


