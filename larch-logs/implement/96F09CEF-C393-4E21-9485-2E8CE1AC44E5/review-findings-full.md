### FINDING_2: panel [code-review/accepted]

## code-quality: scripts/test-implement-structure.sh:212-214

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] test uses global substring grep while fail message asserts STALL_STEP=12d exit 4 path A future edit could add DO NOT improvise elsewhere and delete the 12d printf; test still passes but stall capture logs no longer get the intended directive Anchor on ORCHESTRATOR DIRECTIVE (STALL_STEP=12d) near STALL_STEP 12d and exit 4 or use a bounded multiline pattern
- **Suggested revision**: Address the concern above.

### FINDING_3: panel [code-review/accepted]

## correctness: scripts/test-implement-structure.sh:213-214

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Whole-file grep for DO NOT improvise does not pin the STALL_STEP=12d exit-4 path The diagnostic could be removed from the 12d branch while the phrase remains elsewhere in ship-pr.sh, so the test would not catch the regression Anchor the assertion to the 12d exit path (e.g. multi-line pattern including STALL_STEP=12d and the directive banner)
- **Suggested revision**: Address the concern above.

### FINDING_4: panel [code-review/accepted]

## risk-integration: scripts/test-implement-structure.sh:153-155

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] test uses file-wide grep -q DO NOT improvise on ship-pr.sh while claiming to pin the STALL_STEP=12d exit 4 path the diagnostic line on the real stall branch can be deleted and replaced by an unrelated DO NOT improvise string elsewhere; CI still passes but operators lose the intended 12d-scoped guidance anchor the assertion to the policy_denied admin_failed error arm e.g. require ORCHESTRATOR DIRECTIVE STALL_STEP=12d near DO NOT improvise or use awk to require both within the case branch block
- **Suggested revision**: Address the concern above.

### FINDING_5: panel [code-review/accepted]

## risk-integration: scripts/test-implement-structure.sh:212-214

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Whole-file grep for 'DO NOT improvise' does not tie the string to the STALL_STEP=12d exit 4 path. A later change can delete the stall printf yet keep any other occurrence of the phrase in ship-pr.sh; CI stays green but operators lose the fail_file directive on the real 12d stall. Use a anchored pattern (e.g. STALL_STEP 12d nearby, or match the printf line) so removal from the exit path breaks the test.
- **Suggested revision**: Address the concern above.

### FINDING_6: panel [code-review/accepted]

## risk-integration: scripts/test-implement-structure.sh:212-214

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Substring-only pin on DO NOT improvise can survive refactors that move text off the 12d exit-4 path. Diagnostic removed from policy_denied|admin_failed|error branch but phrase remains elsewhere (e.g. helper); harness still passes and regression slips. Use a multi-line or contextual awk/grep pin (e.g. STALL_STEP 12d adjacent to the printf or a unique sentinel string only emitted on that branch).
- **Suggested revision**: Address the concern above.

