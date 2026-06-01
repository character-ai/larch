## Decision 1: Scope breadth — full 8-module Phase 5 bundle
- **Question**: Cover all 8 modules (run_logs, tokens, tracking_issue, pr_body, push, pr, oos, merge) or a reduced critical-path subset?
- **Resolution**: All 8 modules in one cohesive plan, matching the issue's "ships as one phase" boundary.
- **Source**: user

## Decision 2: Bash-parity test rigor — focused on high-risk ports
- **Question**: How rigorous should bash-parity testing be across the ~14 ported .sh scripts?
- **Resolution**: Exhaustive parity for high-risk logic (merge result-variant routing, redaction, idempotency detection, mermaid-sanitize, PR-body compose); lighter behavioral tests for mechanical push/wrapper code.
- **Source**: user

## Decision 3: Output format — new typed format acceptable
- **Question**: Must Python-emitted output (run-log records, token/timing reports, PR body, tracking-issue comments) be byte-compatible with current .sh output consumed by committed larch-logs and /report-tokens?
- **Resolution**: New typed format acceptable since modules are dev/CI-only until Phase 7; reconcile with consumers at the Phase 7 cutover. Parity tests therefore assert semantic/behavioral equivalence, not byte-identical serialization.
- **Source**: user

## Decision 4: Strangler-fig — no live /implement wiring in Phase 5
- **Question**: Should Phase 5 wire any module into the live /implement path?
- **Resolution**: No. Zero change to the live /implement path until Phase 7 (locked architecture decision #2). New modules are dev/CI-only; runtime imports stay stdlib-only (Python >= 3.12).
- **Source**: codebase (issue #3238, python/README.md, AGENTS.md)

## Decision 5: Idempotency model — gh/git ground truth, no state file
- **Question**: How is recovery/idempotency achieved?
- **Resolution**: Single idempotent process; recovery via gh/git ground truth (detect already-created PR / already-merged state). No ship-pr-state.sh, no --resume-phase, no persisted state file (locked decision #1).
- **Source**: codebase (issue #3238)

## Decision 6: Do not delete ported .sh scripts in Phase 5
- **Question**: Should the source .sh scripts be deleted as part of this port?
- **Resolution**: No. Quality bar: do not delete a shared .sh until a caller grep is zero; strangler-fig keeps the live path on .sh until Phase 7. Phase 5 only adds python/ modules + colocated tests.
- **Source**: codebase (issue #3238)

## Decision 7: gh/git side effects exercised only through the proc.run seam in tests
- **Question**: Must tests avoid live network / gh / git mutations?
- **Resolution**: Yes. All outbound gh/git/push/merge operations route through the injectable proc.run seam; unit + parity tests use fakes — no live PR creation or merge during tests. All gh bodies are file-backed and pass through redact.py.
- **Source**: codebase (python/ conventions, proc.py seam)
