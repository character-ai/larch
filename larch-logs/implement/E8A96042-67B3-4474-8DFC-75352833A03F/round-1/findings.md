### FINDING_1: [OUT_OF_SCOPE] Duplicated routing parsing/key lists can drift
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-routing-contract-output.txt, dyn-dirty-resume-output.txt
- **Severity**: important
- **Concern**: Step 0 routing-envelope parsing and/or key whitelists are duplicated across initial bootstrap, dirty-tree resume, and the wrapper. Future edits can update one copy but leave another stale, causing divergent routing behavior or silently dropped keys.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-routing-contract-output.txt, dyn-dirty-resume-output.txt: Address the concern above.

### FINDING_2: Exit-2 STEP_FAILED harness coverage is incomplete
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-exit2-streams-output.txt
- **Severity**: important
- **Concern**: `test-implement-bootstrap-invoke.sh` covers only a subset of handled `STEP_FAILED` exit-2 cases and incompletely checks stderr/stdout/redaction behavior. Regressions in operator messages, empty stdout discipline, or secret redaction could ship without CI failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-exit2-streams-output.txt: Address the concern above.

### FINDING_3: Wrapper still uses confusing `_ib_*` internal names
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/implement-bootstrap-invoke.sh` retains `_ib_*` local names even though the SKILL-side `_ib_*` harness symbols were removed, creating confusing grep/review signals.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: Usage-error harness cases are missing
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: The wrapper harness does not cover absent `--mode`, invalid/missing mode usage exits, and resume without `IMPLEMENT_TMPDIR`, so usage-contract regressions can slip through CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] Unknown `STEP_FAILED` values exit silently
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-exit2-streams-output.txt
- **Severity**: latent
- **Concern**: The wrapper has no default or explicit arms for some possible `STEP_FAILED` values, so new or pre-existing bootstrap failures can exit 2 without a formatted operator stderr message.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-exit2-streams-output.txt: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] Stale routing state can be reapplied after failed or partial bootstrap invocations
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-routing-contract-output.txt, dyn-dirty-resume-output.txt
- **Severity**: important
- **Concern**: Step 0 can parse stale `bootstrap-routing.env` or preserve old shell routing values when the wrapper exits nonzero, the env file is incomplete/skipped, or stdout contains fresher routing data. This can resurrect dirty-tree bail state or stale branch/plan/coder values during recovery.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-routing-contract-output.txt, dyn-dirty-resume-output.txt: Address the concern above.

### FINDING_7: Structural pins do not enforce `set +e`/`set -e` adjacency
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Structure tests count `set +e`/`set -e` occurrences globally rather than pinning them immediately around each `implement-bootstrap-invoke.sh` command and `_inv_rc=$?` capture. A future edit could break the fence while tests still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_8: Initial-mode unset coder behavior is untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The harness lacks a case proving initial mode omits `--coder` when coder is unset, so the wrapper could regress to passing an empty `--coder` and disrupt coder selection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] Unquoted envelope values may mishandle spaces or equals
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Routing envelope values are unquoted, so values containing spaces or embedded equals could truncate or mis-route pre-rehydration consumers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] Deleted `_ib_*` symbol absence pins are not explicit
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Structure tests do not explicitly invert-pin removed `_ib_handle_bootstrap_exit2` / `_ib_kv_scan` names, leaving acceptance text slightly ahead of the pins.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] Dirty-tree resume can leave `coder` empty
- **Reviewer(s)**: dyn-routing-contract-output.txt, dyn-dirty-resume-output.txt
- **Severity**: important
- **Concern**: Dirty-tree recovery uses plan-only resume, which does not rerun coder selection. The emitted routing envelope can therefore carry an empty `coder`, while the continue path expects a non-empty coder.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-routing-contract-output.txt, dyn-dirty-resume-output.txt: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] Dirty-tree recovery routing semantics lack focused harness coverage
- **Reviewer(s)**: dyn-routing-contract-output.txt, dyn-dirty-resume-output.txt
- **Severity**: latent
- **Concern**: The invoke harness does not cover file-vs-stdout precedence, stale `bootstrap-routing.env`, failed resume with stale routing files, full post-recovery routing refresh, or plan-resume coder emptiness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-routing-contract-output.txt, dyn-dirty-resume-output.txt: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] Exit-2 stream ownership is an improvement, not a regression
- **Reviewer(s)**: dyn-exit2-streams-output.txt
- **Severity**: nit
- **Concern**: Reviewer observed that the new wrapper correctly routes formatted exit-2 text to stderr and that Step 0 does not re-print `_inv_out`; this is informational rather than a behavioral risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-exit2-streams-output.txt: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] Exit-2 no-print rule lives in docs rather than the Step 0 fence
- **Reviewer(s)**: dyn-exit2-streams-output.txt
- **Severity**: nit
- **Concern**: The rule not to print `_inv_out` on exit 2 is documented in `scripts/implement-bootstrap-invoke.md` rather than pinned directly in the Step 0 fenced bash, though behavior is currently enforced by the wrapper.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-exit2-streams-output.txt: Address the concern above.
