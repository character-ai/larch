Reviewer entries that explicitly reported no new issue are not emitted as findings.

### FINDING_1: Static lint-fix pin calls fail before definition
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-shell-contracts-output.txt, dyn-harness-integrity-output.txt, dyn-artifact-flow-output.txt
- **Severity**: important
- **Concern**: `scripts/test-lint-fix-loop.sh` calls `fail` from the static `--stderr-sink` grep pin before `fail()` is defined, so a missing pin exits with `command not found` instead of the intended harness failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-shell-contracts-output.txt, dyn-harness-integrity-output.txt, dyn-artifact-flow-output.txt: Address the concern above.

### FINDING_2: Static review-and-fix pin calls fail before definition
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-shell-contracts-output.txt, dyn-harness-integrity-output.txt, dyn-artifact-flow-output.txt
- **Severity**: important
- **Concern**: `skills/review-and-fix/scripts/test-review-and-fix.sh` has the same ordering bug for the codex `--stderr-sink` grep pin, causing opaque shell failure on regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-shell-contracts-output.txt, dyn-harness-integrity-output.txt, dyn-artifact-flow-output.txt: Address the concern above.

### FINDING_3: Rejection helper duplicates existing assertion structure
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `assert_rejected_stderr_sink` duplicates `assert_rejected_output` structure, increasing maintenance cost for validation changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: Custom stderr-sink contract can drift between redirect and flag
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-artifact-flow-output.txt
- **Severity**: latent
- **Concern**: Default-mode launchers must both redirect fd2 to the sink and pass the same path via `--stderr-sink`; a future mismatch can silently fall back to older stderr-tail sources.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, dyn-artifact-flow-output.txt: Address the concern above.

### FINDING_5: Missing explicit-sink fallback case is not tested
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `scripts/test-lib-failed-agent-stderr-tail.sh` covers an empty explicit sink but not a nonexistent explicit sink path, leaving the `[[ -s ]]` fallback behavior unpinned.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] Cursor implement lane omits stderr-sink
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-shell-contracts-output.txt, dyn-artifact-flow-output.txt
- **Severity**: latent
- **Concern**: `launch-cursor-implement.sh` intentionally remains on the capture-mode stderr contract and does not pass `--stderr-sink`; reviewers marked this as pre-existing or intentional asymmetry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, dyn-shell-contracts-output.txt, dyn-artifact-flow-output.txt: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] Collector retries do not replay stderr-sink
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-shell-contracts-output.txt, dyn-artifact-flow-output.txt
- **Severity**: latent
- **Concern**: `scripts/collect-agent-results.sh` retry paths rebuild wrapper argv without preserving `--stderr-sink`, so retried default-mode runs lose custom-sink stderr-tail fidelity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-shell-contracts-output.txt, dyn-artifact-flow-output.txt: Address the concern above.

### FINDING_8: Timeout path lacks stderr-sink integration coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-harness-integrity-output.txt
- **Severity**: latent
- **Concern**: Existing `--stderr-sink` integration coverage exercises non-zero exit, but not timeout in default mode, so dropping the sink argument on the timeout branch would not be caught.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, dyn-harness-integrity-output.txt: Address the concern above.

### FINDING_9: stderr-sink rejection matrix is thinner than output
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `--stderr-sink` rejection coverage tests fewer invalid path shapes than the existing `--output` matrix.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] Path validation allows parent-directory segments
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `validate_meta_scalar_path` still permits `..` path segments; reviewer marked this as pre-existing and only relevant if wrapper argv becomes untrusted input.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] Security review noted static-pin ordering bug
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Security reviewer also observed the `fail` before definition issue in both static grep pins, but classified it as unrelated to security scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_12: Header usage comment omits stderr-sink
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-artifact-flow-output.txt
- **Severity**: nit
- **Concern**: `scripts/run-external-agent.sh` header `# Usage:` omits `[--stderr-sink PATH]` even though `usage()`, options text, and docs include it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, dyn-artifact-flow-output.txt: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] Mismatched stderr-sink path falls back silently
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Passing a wrong `--stderr-sink` path relative to the actual fd2 redirect silently falls back to legacy stderr-tail sources; reviewer marked this as pre-existing contract risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] Missing explicit-sink fallback test also noted as low risk
- **Reviewer(s)**: dyn-harness-integrity-output.txt
- **Severity**: latent
- **Concern**: Reviewer separately marked the nonexistent explicit-sink fallback test gap as out of scope and low risk because behavior is implied by `[[ -s ]]`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-integrity-output.txt: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] Static grep pins can match comments
- **Reviewer(s)**: dyn-harness-integrity-output.txt
- **Severity**: nit
- **Concern**: Static `grep -Fq` pins can pass if the literal appears only in a comment; reviewer says this limitation is acknowledged and acceptable for lane forwarding guards.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-integrity-output.txt: Address the concern above.
