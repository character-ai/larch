# Review Round 3

- Mode: `diff`
- 3 accepted, 12 rejected (10 exonerated)

## Accepted Findings

### FINDING_1: Separate empty-result retry budget allows up to six cursor calls per auth pass
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, cursor-specialist-structure-output.txt, dyn-retry-budget-integrity-output.txt
- **Severity**: important
- **Concern**: Empty-result retries use `EMPTY_RESULT_ATTEMPT` bounded independently of `TRANSIENT_ATTEMPT` (both gated by `MAX_TRANSIENT_RETRIES=2`), diverging from the binding plan to reuse `TRANSIENT_ATTEMPT` and cap total cursor backend calls at three per slot per auth pass. Under mixed exit-code transients and exit-0 empty `.result`, a slot can issue up to six sequential `cursor agent` invocations (three exit-code + three empty-result), amplifying backend and rate-limit pressure during outages—especially across parallel panels (~8 slots).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Reuse TRANSIENT_ATTEMPT for empty-result retries, or update plan/acceptance to document separate budgets explicitly.
  - From cursor-specialist-testing-output.txt: Align counters with the plan (single shared budget) or document and accept the six-call ceiling explicitly in acceptance/docs.
  - From cursor-specialist-edge-cases-output.txt: Unify retry counting under one MAX_CURSOR_BACKEND_ATTEMPTS or cap total backend calls at three across both branches.
  - From cursor-specialist-plan-fidelity-output.txt: Reuse TRANSIENT_ATTEMPT for empty-result retries per the binding plan, or update the plan/acceptance criteria and keep docs aligned if separate budgets are intentional.
  - From cursor-specialist-structure-output.txt: No code change required if intentional; ensure issue/PR description calls out the deliberate plan deviation so future readers do not “simplify” back to a shared counter and break the mixed-retry tests.
  - From dyn-retry-budget-integrity-output.txt: Drop `EMPTY_RESULT_ATTEMPT` and drive empty-result retries through the existing `TRANSIENT_ATTEMPT` counter (increment before `continue` in either branch, single `_cursor_transient_backoff` using that counter), so the combined transient budget stays at `MAX_TRANSIENT_RETRIES + 1 = 3` total calls; update `SL-cursor-transient8-then-empty` and the docs in `scripts/launch-review.md` / `docs/configuration-and-permissions.md` to match the shared-budget semantics.

---


### FINDING_2: Operator docs understate separate-counter worst-case load
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Env-var documentation describes retry limits as sharing `MAX_TRANSIENT_RETRIES=2` with exit-code transients but does not clearly state that empty-result retries use a separate `EMPTY_RESULT_ATTEMPT` counter, so operators tuning parallel panels may not expect up to six backend calls per auth pass under mixed failure modes (as spelled out in `scripts/launch-review.md`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add one sentence under `LARCH_CURSOR_RETRY_EMPTY_RESULT` mirroring `launch-review.md` (separate counter, worst-case 3+3 calls per auth pass) so operators tuning parallel panels are not surprised by load.

---


### FINDING_7: Case B2 does not guard empty-result retry or diagnostic regressions
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `scripts/test-launch-review.sh` case B2 does not assert `.diag` content or stub invocation count. Removing `LARCH_CURSOR_RETRY_EMPTY_RESULT=0` from B2 could still pass marker assertions while invoking the stub three times and missing `.diag` regressions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add .diag grep and stub count==1 assertions to case B2, matching SL-cursor-empty-retry-disabled.
  - From cursor-specialist-edge-cases-output.txt: Set LARCH_CURSOR_RETRY_EMPTY_RESULT=0 for B2 or assert exactly one stub invocation.

---


