### FINDING_1: Static lint-fix pin calls fail before definition
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-shell-contracts-output.txt, dyn-harness-integrity-output.txt, dyn-artifact-flow-output.txt
- **Severity**: important
- **Concern**: `scripts/test-lint-fix-loop.sh` calls `fail` from the static `--stderr-sink` grep pin before `fail()` is defined, so a missing pin exits with `command not found` instead of the intended harness failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-shell-contracts-output.txt, dyn-harness-integrity-output.txt, dyn-artifact-flow-output.txt: Address the concern above.


### FINDING_12: Header usage comment omits stderr-sink
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-artifact-flow-output.txt
- **Severity**: nit
- **Concern**: `scripts/run-external-agent.sh` header `# Usage:` omits `[--stderr-sink PATH]` even though `usage()`, options text, and docs include it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, dyn-artifact-flow-output.txt: Address the concern above.


### FINDING_2: Static review-and-fix pin calls fail before definition
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-shell-contracts-output.txt, dyn-harness-integrity-output.txt, dyn-artifact-flow-output.txt
- **Severity**: important
- **Concern**: `skills/review-and-fix/scripts/test-review-and-fix.sh` has the same ordering bug for the codex `--stderr-sink` grep pin, causing opaque shell failure on regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-shell-contracts-output.txt, dyn-harness-integrity-output.txt, dyn-artifact-flow-output.txt: Address the concern above.


