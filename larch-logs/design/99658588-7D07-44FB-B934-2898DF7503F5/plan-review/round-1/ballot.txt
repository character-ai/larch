### FINDING_1: New impl-lines-fb fixture duplicates existing fallback coverage
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-dyn-harness-contract
- **Severity**: nit
- **Concern**: The proposed `impl-lines-fb` fixture duplicates an existing `fork_fb`/stage2 `compose_self_fallback` path that already exercises fallback rendering with `PR_NUMBER` set and line-count data available; only additional assertions appear to be needed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Extend the existing impl_fork_fb block: assert degraded banner, larch:final-summary-fallback v1, the bucketed Lines bullet, and PR bullet on $fork_fb; skip impl-lines-fb unless merged-outcome title coverage is explicitly required
  - From Cursor-Innovation: Extend fork_fb assertions at 528-530 or bracket a renderer stub immediately after the impl_lines happy-path at 786; assert banner marker bucketed Lines bullet and PR bullet there instead of creating impl-lines-fb
  - From Cursor-Pragmatic: Extend the existing fork_fb block with assert_contains for - **Lines (PR diff)**: code +17/-3, larch-logs +5/-1 and - **PR**: instead of adding a second fixture plus another stub save/restore bracket
  - From Cursor-dyn-harness-contract: Add assert_contains for - **Lines (PR diff)**: code +17/-3, larch-logs +5/-1, - **PR**:, **⚠ Degraded fallback, and <!-- larch:final-summary-fallback v1 --> on the existing fork_fb stdout capture; skip a new fixture unless a distinct outcome-specific branch is required

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
