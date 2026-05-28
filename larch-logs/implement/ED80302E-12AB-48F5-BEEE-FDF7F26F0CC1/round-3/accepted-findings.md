### FINDING_1: Missing `larch_quiet_bc_valid_category` regression coverage
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `scripts/test-lib-quiet.sh` no longer directly covers valid/invalid breadcrumb category handling, so helper regressions can pass the quiet library tests and later break breadcrumb monitor paths under `set -e`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_10: apply-bump docs still describe removed `emit_breadcrumb` routing
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `.claude/skills/bump-version/scripts/apply-bump.md` still documents `emit_breadcrumb`, stdout, quiet-log routing, or category/env guidance after `apply-bump.sh` migrated retry diagnostics to `larch_err` on stderr.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_12: Collect-agent transient retry tests do not assert visible retry diagnostics
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-collect-agent-results.sh` captures stderr for transient retry cases but does not assert expected `larch_err` retry lines, leaving C_T1/C_T4 diagnostic regressions uncovered.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_17: breadcrumb-monitor docs imply FD4/stderr tailing that code does not perform
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `scripts/breadcrumb-monitor.md` claims the monitor surfaces FD4/stderr breadcrumbs, but the script still tails `larch:bc` stream records only; Stage 2 Family-B runs can therefore block without showing live progress through the monitor.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_18: breadcrumb-monitor failure tail omits `larch_err` progress
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `scripts/breadcrumb-monitor.sh` tails only `QUIET_LOG` on failure, while `larch_err`/`larch_errf` write to FD4 and are excluded, making failures after migrated progress diagnostics appear silent or under-explained.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_2: Documentation still describes live NDJSON streams after quiet-log migration
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `SECURITY.md` and `docs/run-logs.md` still imply live NDJSON breadcrumb streams are produced, published, or available under session breadcrumb paths, while Stage 2 behavior is quiet-log-only with legacy NDJSON ignored or unpublished.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_3: SECURITY source-dir rejection docs no longer match publish behavior
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `SECURITY.md` still documents source-dir-level fail-closed rejection, but current publish code silently skips bad or symlinked source hints and relies on per-file staging guards.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt: Address the concern above.


### FINDING_4: Dispatch panel docs still gate launch breadcrumbs on inert env
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `skills/review/scripts/dispatch-panel.md` still describes `LARCH_QUIET_BREADCRUMBS=1` controlling launch breadcrumb surfacing, but the migrated script emits via `larch_err` unconditionally on operator stderr.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_5: Implement bootstrap harness docs describe removed quiet breadcrumb preconditions
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `skills/implement/scripts/test-implement-bootstrap.md` still documents `LARCH_QUIET_BREADCRUMBS`/FD breadcrumb surfacing instead of the current stderr capture contract, so local repro guidance diverges from CI behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_9: Refresh run-log harness still expects committed NDJSON
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `scripts/test-refresh-run-logs.sh` still requires committed `refresh.ndjson`, contradicting the quiet-log-only publish behavior and causing harness failures under the new implementation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


