### FINDING_1: Redundant Case 2 rc assertion
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Case 2 asserts `rc == 0`, but `render-final-summary.sh` exits 0 even when `invoke_render` fails and falls back, so this assertion does not catch the Bash 3.2 nounset regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] Missing stderr log can skip nounset witness
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Case 2 only greps `render-final-summary.stderr.log` for `unbound variable` when that log exists. If stderr redirection regresses or the log is missing, the primary nounset witness can be skipped while fallback output and rc 0 still let the test pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_3: Duplicated minimal DESIGN_TMPDIR fixture
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The Bash 3.2 harness duplicates a minimal `DESIGN_TMPDIR` fixture from `test-render-final-summary.sh`, creating a maintenance risk if artifact requirements change in one harness only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: Static grep is sensitive to invocation formatting
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Case 1 requires the `render-run-summary` invocation to remain on a single line, so harmless wrapping could fail CI without reintroducing the Bash 3.2 bug.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] Other empty-array nounset risks may remain
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Other scripts may still have unguarded empty-array expansions under `set -u`; this was outside the scoped `render-final-summary.sh` call-site fix.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_6: Security review reported no command injection concern
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Security review notes no new interpolation of untrusted input into shell; relevant arrays and arguments remain quoted or fixed, and `OUTCOME` remains enum-validated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_7: Security review reported no word splitting or globbing concern
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Security review notes the outer unquoted `${…[@]+…}` form is intentional for empty arrays under `set -u`, while non-empty elements still expand through quoted inner array expansion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_8: Security review reported no secrets concern
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Security review notes no new credential logging or network use; failure paths still redact, and the harness avoids the GitHub boundary with an empty issue number.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] Fallback masks render failures with rc 0
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `compose_self_fallback` can produce a plausible `final-summary.md` with exit 0 when `invoke_render` fails, creating pre-existing degraded-output or audit-integrity risk outside this diff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] Prompt-only guard for interactive subprocesses
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: The hard guard for interactive subprocesses is prompt-only rather than enforced by launcher/runtime code, so a non-compliant external agent could still attempt `write_stdin`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_11: Case 2 does not exercise empty render_cost_args
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Dynamic Case 2 only empties `note_args`; it does not run the `render_cost_args` empty-array copy path under Bash 3.x, so regressions limited to cost-available design runs could pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_12: Case 2 success message overstates array coverage
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: The Case 2 success message claims empty arrays generally, but the fixture only empties `note_args`, which can mislead debugging.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] Design publish helper failure can skip rigid block
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `skills/design/SKILL.md` gates post-publish emit on helper exit 0 only, so Step 5c can skip the rigid block after helper failure; this is pre-existing and separate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] Bash 3.2 lint lacks empty-array nounset scan
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `lint-bash32` does not scan for unsafe empty-array expansion under nounset, leaving a pre-existing repo-wide coverage gap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
