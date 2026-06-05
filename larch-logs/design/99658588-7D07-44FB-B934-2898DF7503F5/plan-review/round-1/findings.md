### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: nit
- **Focus area**: architecture
- **Location**: skills/implement/scripts/test-write-final-report.sh:510-532
- **Concern**: Plan adds a new impl-lines-fb fixture and case though impl_fork_fb already runs stage2 compose_self_fallback with PR_NUMBER set and LINES_DATA_OK=true. Scenario: New fixture duplicates ~20 lines of ship-pr/session/finalize setup and increases stub save/restore surface without exercising a new code path; violates the plan's own smallest-change contract
- **Proposed resolution**: Extend the existing impl_fork_fb block: assert degraded banner, larch:final-summary-fallback v1, the bucketed Lines bullet, and PR bullet on $fork_fb; skip impl-lines-fb unless merged-outcome title coverage is explicitly required

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: architecture
- **Location**: skills/implement/scripts/test-write-final-report.sh:510-531
- **Concern**: Plan adds a new impl-lines-fb fixture though an existing stage2-fallback case already exercises LINES_DATA_OK=true. Scenario: ~30 lines of duplicated fixture setup (parent-issue session-env ship-pr-state finalize-state) when fork_fb (PR_NUMBER=18 renderer stub compose_self_fallback) or impl_lines (786) already reaches the untested printf branch
- **Proposed resolution**: Extend fork_fb assertions at 528-530 or bracket a renderer stub immediately after the impl_lines happy-path at 786; assert banner marker bucketed Lines bullet and PR bullet there instead of creating impl-lines-fb

### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: skills/implement/scripts/test-write-final-report.sh:510-531
- **Concern**: New impl-lines-fb fixture duplicates an existing stage2-fallback path. Scenario: The fork_fb case already stubs render-run-summary.sh to exit 1, sets a nonzero PR_NUMBER, runs compute-pr-line-counts via the shared gh shim, and reaches compose_self_fallback with LINES_DATA_OK=true; only the bucketed Lines bullet and PR bullet are unasserted
- **Proposed resolution**: Extend the existing fork_fb block with assert_contains for - **Lines (PR diff)**: code +17/-3, larch-logs +5/-1 and - **PR**: instead of adding a second fixture plus another stub save/restore bracket

### FINDING_4:
- **Reviewer(s)**: Cursor-dyn-harness-contract
- **Severity**: nit
- **Focus area**: architecture
- **Location**: skills/implement/scripts/test-write-final-report.sh:510-531
- **Concern**: New impl-lines-fb fixture duplicates an existing stage2 compose_self_fallback path that already has nonzero PR_NUMBER and the global gh shim. Scenario: The fork_fb block already stubs render-run-summary.sh with exit 1, runs write-final-report.sh with PR_NUMBER=18, hits compose_self_fallback with LINES_DATA_OK=true, and restores render-run-summary.real; only the bucketed Lines bullet and PR bullet are unasserted. A separate impl-lines-fb fixture (~clone of impl_lines) adds fixture churn without exercising a distinct code path because compose_self_fallback lines formatting is outcome-agnostic
- **Proposed resolution**: Add assert_contains for - **Lines (PR diff)**: code +17/-3, larch-logs +5/-1, - **PR**:, **⚠ Degraded fallback, and <!-- larch:final-summary-fallback v1 --> on the existing fork_fb stdout capture; skip a new fixture unless a distinct outcome-specific branch is required

### FINDING_5:
- **Reviewer(s)**: Cursor-dyn-metrics-contract
- **Severity**: nit
- **Focus area**: correctness
- **Location**: plan.txt:55
- **Concern**: Acceptance #1 lists partial-flags among test-write-final-report.sh harness cases. Scenario: Partial line-count flag handling is only asserted in scripts/test-render-run-summary.sh:257-280; skills/implement/scripts/test-write-final-report.sh has no partial-counter integration case
- **Proposed resolution**: Revise acceptance #1 to cite scripts/test-render-run-summary.sh for partial-flags (or drop partial-flags from the write-final-report parenthetical)

### FINDING_6:
- **Reviewer(s)**: Codex-dyn-metrics-contract
- **Severity**: latent
- **Focus area**: security
- **Location**: scripts/compute-pr-line-counts.sh:40-47; scripts/test-compute-pr-line-counts.sh:100-109; plan.txt:14,58
- **Concern**: Plan overstates REPO validation and pinning as exact owner/name. Scenario: The helper only enforces one slash with non-empty parts and no extra slash, while the harness pins only the extra-slash case; broader exact-slug or missing-part coverage is not test-pinned as claimed
- **Proposed resolution**: For SIMPLE scope, narrow the plan and acceptance wording to the actual single-slash/non-empty-parts guard and existing extra-slash pin; only add stricter code/tests if exact GitHub slug validation is intended

### FINDING_7:
- **Reviewer(s)**: Codex-dyn-metrics-contract
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/implement/scripts/write-final-report.sh:127-134,467-474; skills/implement/scripts/test-write-final-report.sh:758-850; scripts/test-render-run-summary.sh:257-280; plan.txt:55
- **Concern**: Plan says partial/non-numeric line data is pinned by existing write-final-report harness cases. Scenario: The integration harness covers happy path, no-PR, repo-unavailable, and gh-failed; partial flags are pinned only in the renderer harness, not through write-final-report parsing/line_args
- **Proposed resolution**: If no new coverage is desired, narrow the acceptance text to say partial/non-numeric data is renderer-pinned; otherwise add one minimal helper-stub integration case for ok plus missing/non-numeric counters
