### OOS_4: [OUT_OF_SCOPE] voter1_pid not tracked by waterfall EXIT trap
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `voter1_pid` is not tracked by the waterfall EXIT trap. Abrupt kill of `dispatch-plan-voters` can orphan a parallel Claude voter. Pre-existing; not introduced by this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Extend voter dispatch with its own EXIT trap or PID tracking.


### OOS_5: [OUT_OF_SCOPE] Undocumented TERM trap in dispatch-with-waterfall
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: An undocumented TERM trap was added beyond the plan's EXIT trap only. External TERM mid-dispatch exits 143; behavior is not in the contract or tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Document in dispatch-with-waterfall.md or remove if redundant with EXIT.


