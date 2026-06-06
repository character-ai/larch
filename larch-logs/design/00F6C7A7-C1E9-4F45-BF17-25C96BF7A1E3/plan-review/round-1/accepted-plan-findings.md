### FINDING_1: Step-2 bail reason is not propagated to classifier
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Concern**: The plan renders `BAIL_REASON`, but the actual Step-2 hard-bail reason may never reach the classifier, so envelope or wrapper-validation failures can still render `none` instead of the intended sanitized bail reason.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Revise the plan to pass or persist the existing Step-2 REASON/FINAL_BAIL_REASON through the existing --bail-reason or BAIL_REASON path before Step 18a, and add a harness case for the actual Step-2 bailed flow rather than only a fixture that pre-seeds BAIL_REASON


### FINDING_2: Missing or empty EXIT_CODE still defaults to 0 before sanitization
- **Reviewer(s)**: Codex-Edge
- **Severity**: latent
- **Concern**: `compose_body_content` still defaults missing or empty `EXIT_CODE` to `0` before the sanitizer can map uncaptured values to `unknown`, leaving a path where malformed or older classification files render a misleading zero.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Load EXIT_CODE with an empty default, then pass it through safe_exit_code_value; keep real zero covered by explicit EXIT_CODE=0 tests


### FINDING_3: SECURITY.md is stale for new public stall-report fields
- **Reviewer(s)**: Codex-Edge, Codex-Innovation, Codex-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: The plan adds a public `bail_reason` stall-report field and changes exit-code rendering/BAIL_REASON sanitization behavior, but does not update `SECURITY.md`, leaving the documented public-boundary contract stale and misleading.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Update the stall recovery sanitization section to include the new bail_reason public field, integer-or-unknown exit rendering, and the current safe_bail_reason_value allowlist/redacted behavior
  - From Codex-Innovation: Make a minimal SECURITY.md update in the Stall recovery sanitization section to name the new public Bail reason field, the expanded closed enum, and exit_code integer-or-unknown behavior
  - From Codex-Pragmatic: Add a minimal SECURITY.md update alongside the planned docs: list rendered bail_reason as a sanitized closed-enum field with empty shown as none, update the full allowlist, and describe exit_code as integer-or-unknown
  - From Codex-Requirements: Add a minimal SECURITY.md update under Stall recovery sanitization to list bail_reason as an allowlisted public field, update the closed enum set, and note exit_code may render unknown for uncaptured values


### FINDING_4: Exit-code sanitizer tests miss non-zero and non-numeric cases
- **Reviewer(s)**: Codex-dyn-test-path-completeness
- **Severity**: important
- **Concern**: The proposed assertions cover empty `EXIT_CODE` and numeric zero, but omit explicit coverage for non-zero numeric pass-through and non-numeric non-empty input, so regressions for values like `4` or `abc` could pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-test-path-completeness: Add two minimal assertions in test-stall-recovery-report.sh: classify a fixture with EXIT_CODE=4 and assert EXIT_CODE=4; classify a fixture with EXIT_CODE=abc (or another non-empty string) and assert EXIT_CODE=unknown. Keep the existing uncaptured bug-body assertion as the compose_body_content idempotency check for classify-emitted unknown.

