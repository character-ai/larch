### OOS_1: [OUT_OF_SCOPE] pre-commit hook misses Python writer paths
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing
- **Severity**: important
- **Concern**: The bg-wait writer parity pre-commit hook only matches skills paths, so edits confined to inventoried Python writer files can skip the new drift guard during local pre-commit and /implement relevant checks; the regression is then caught only in broader CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] CLONE_PATH check is too broad
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: latent
- **Concern**: The lint accepts any file-level CLONE_PATH substring, so a decoy line elsewhere in the file could satisfy the check while the actual marker emission omits CLONE_PATH.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] Step 3 shell harness is legacy-only
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: latent
- **Concern**: The Step 3 shell harness is legacy parity only; the live marker path is handled by dispatch_commit_route, so the shell script change does not affect production behavior and lacks a runtime guard.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.

### OOS_4: [OUT_OF_SCOPE] inventory tuple cannot discover new writers
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: The fixed WRITERS tuple cannot discover new writer files outside the inventory, so a new .bg-wait-active writer added off-list could miss CLONE_PATH until the tuple is updated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.
