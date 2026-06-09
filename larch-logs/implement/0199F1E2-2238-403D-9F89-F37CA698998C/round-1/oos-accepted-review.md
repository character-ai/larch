### OOS_1: [OUT_OF_SCOPE] Cap-hit envelope round count telemetry
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: The source marked the cap-hit `ROUNDS_COMPLETED=0` issue out of scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### OOS_2: [OUT_OF_SCOPE] Structural pins do not enforce loop contracts
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-state-machine-output.txt
- **Severity**: nit
- **Concern**: Structural tests still pin legacy `LOOP_STATUS` / Gate B prose and do not pin the new `STEP3_REVIEW_LOOP_STATUS` and `--mode loop` contracts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From dyn-state-machine-output.txt: Address the concern above.


### OOS_3: [OUT_OF_SCOPE] Multi-round integration harness still uses legacy flow
- **Reviewer(s)**: dyn-state-machine-output.txt
- **Severity**: latent
- **Concern**: The source marked the legacy two-call `--no-preview` integration harness issue out of scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-machine-output.txt: Address the concern above.


### OOS_4: [OUT_OF_SCOPE] Legacy Gate B continuation prose still says `--no-preview`
- **Reviewer(s)**: dyn-sole-writer-invariant-output.txt
- **Severity**: latent
- **Concern**: The source marked stale Gate B continuation prose as out of scope because the primary multi-round flow is already in-loop.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-sole-writer-invariant-output.txt: Address the concern above.

