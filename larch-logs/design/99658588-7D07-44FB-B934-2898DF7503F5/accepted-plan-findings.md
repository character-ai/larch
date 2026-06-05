### FINDING_2: Acceptance text overstates write-final-report partial-flag coverage
- **Reviewer(s)**: Cursor-dyn-metrics-contract, Codex-dyn-metrics-contract
- **Severity**: latent
- **Concern**: The plan claims partial/non-numeric line-count flag handling is covered by `test-write-final-report.sh`, but current coverage appears to exist only in `scripts/test-render-run-summary.sh`, not the write-final-report integration harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-metrics-contract: Revise acceptance #1 to cite scripts/test-render-run-summary.sh for partial-flags (or drop partial-flags from the write-final-report parenthetical)
  - From Codex-dyn-metrics-contract: If no new coverage is desired, narrow the acceptance text to say partial/non-numeric data is renderer-pinned; otherwise add one minimal helper-stub integration case for ok plus missing/non-numeric counters


### FINDING_3: Plan overstates REPO validation guarantees
- **Reviewer(s)**: Codex-dyn-metrics-contract
- **Severity**: latent
- **Concern**: The plan claims exact owner/name validation and pinning, but the described helper only enforces a single slash with non-empty parts and no extra slash; broader exact-slug or missing-part coverage is not pinned as claimed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-metrics-contract: For SIMPLE scope, narrow the plan and acceptance wording to the actual single-slash/non-empty-parts guard and existing extra-slash pin; only add stricter code/tests if exact GitHub slug validation is intended

