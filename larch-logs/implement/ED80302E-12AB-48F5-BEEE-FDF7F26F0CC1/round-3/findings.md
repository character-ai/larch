### FINDING_1: Missing `larch_quiet_bc_valid_category` regression coverage
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `scripts/test-lib-quiet.sh` no longer directly covers valid/invalid breadcrumb category handling, so helper regressions can pass the quiet library tests and later break breadcrumb monitor paths under `set -e`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt: Address the concern above.

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

### FINDING_6: Branch mixes Stage 2 breadcrumb work with unrelated Gate B/version/run-log changes
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The branch appears to combine Stage 2 breadcrumb migration with #2667 Gate B documentation, version/changelog updates, and run-log flushes, making PR review, traceability, and bisecting less clear.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_7: Rebase checkpoint probe exports dead quiet breadcrumb env
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-rebase-checkpoint-probe.sh` still exports inert `LARCH_QUIET_BREADCRUMBS=1`, which can mislead maintainers about how breadcrumb assertions are surfaced.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_8: Review-and-fix tests rely on inert quiet breadcrumb env plus outer stderr capture
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `skills/review-and-fix/scripts/test-review-and-fix.sh` sets inert `LARCH_QUIET_BREADCRUMBS=1`; the tests actually depend on outer `2>&1` capture before quiet init, making future failures confusing if capture changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_9: Refresh run-log harness still expects committed NDJSON
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `scripts/test-refresh-run-logs.sh` still requires committed `refresh.ndjson`, contradicting the quiet-log-only publish behavior and causing harness failures under the new implementation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_10: apply-bump docs still describe removed `emit_breadcrumb` routing
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `.claude/skills/bump-version/scripts/apply-bump.md` still documents `emit_breadcrumb`, stdout, quiet-log routing, or category/env guidance after `apply-bump.sh` migrated retry diagnostics to `larch_err` on stderr.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_11: Planned `emit_breadcrumb` grep acceptance is not enforced
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The plan’s acceptance check for zero `.sh` `emit_breadcrumb` callsites is not pinned in CI or Makefile lint, so a reintroduced callsite could ship until runtime.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_12: Collect-agent transient retry tests do not assert visible retry diagnostics
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-collect-agent-results.sh` captures stderr for transient retry cases but does not assert expected `larch_err` retry lines, leaving C_T1/C_T4 diagnostic regressions uncovered.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_13: Family-B live diagnostics bypass prior monitor redaction path
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Migrated Family-B progress now uses `larch_err`/FD4 while `breadcrumb-monitor` redaction only applied to `larch:bc` stream records, so live operator transcript diagnostics may no longer receive the same per-line filtering.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_14: Collect-agent retry diagnostics now expose artifact basenames live
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `scripts/collect-agent-results.sh` moved retry breadcrumbs to `larch_err`/FD4, making namespace retry artifact basenames visible in the operator transcript where they previously stayed in the quiet breadcrumb channel.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] ship-pr redactor failure relays raw tool output
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `scripts/ship-pr.sh` can relay raw tool output through `larch_err` when `redact-secrets.sh` fails, potentially exposing tokens or tmpdir paths; reviewer marked this pre-existing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] create-pr surfaces raw gh stderr
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `scripts/create-pr.sh` surfaces raw `gh` stderr through `larch_err`, potentially exposing auth or host details; reviewer marked this pre-existing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

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

### FINDING_19: Published quiet-log forensics omit migrated `larch_err` progress
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `scripts/lib-larch-log.sh` quiet-log-only publication cannot stage progress emitted via `larch_err`, so committed breadcrumb forensics may lack ship-pr/ci-wait progress that no longer enters quiet logs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
