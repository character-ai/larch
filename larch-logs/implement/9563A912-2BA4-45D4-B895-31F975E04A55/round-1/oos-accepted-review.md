### OOS_1: [OUT_OF_SCOPE] Ship PR re-invocation docs bypass the Step 8 wrapper
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `ship-pr-exit-matrix.md` still directs re-invocation through `ship-pr.sh` or the Python CLI instead of the centralized `step-8-ship.sh` wrapper. Orchestrators following the reference can bypass the wrapper’s Python-version guard and driver-selection contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### OOS_2: [OUT_OF_SCOPE] Step 17 wrapper masks final-report write failures
- **Reviewer(s)**: codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `step-17.sh` logs `write-final-report.sh` failures but exits 0, while Step 17 prose expects non-zero failure behavior. The orchestrator may proceed with a stale `summary-final.md` after a failed GitHub final-summary update.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


