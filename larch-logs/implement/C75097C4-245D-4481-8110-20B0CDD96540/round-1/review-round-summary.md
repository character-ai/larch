# Review Round 1

- Mode: `diff`
- 1 accepted, 1 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Orchestrator omits EXIT_CODE (and full classify argv) causing checks-child-failed misclassification
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, codex-generalist, dyn-dyn-stall-recovery
- **Severity**: important
- **Concern**: Step 18a / `stall-recovery.md` item 3 documents `--in-memory-stall-tracking` but not the full `stall-recovery classify` argv template, especially `--exit-code`. On the Step 3/6 no-log checks path (`checks-repair-loop.md`), composite stdout from `checks-commit-route` emits `FAILURE_REASON=checks-child-failed` and `EXIT_CODE` (e.g. `-15` or `1`), but those values are not bound or passed to classify before Step 18. `_seed_durable_stall_state()` does not persist `EXIT_CODE`, so classify falls back to `st.get("EXIT_CODE", "unknown")` unless the orchestrator passes `--exit-code`. `_checks_child_sigterm_or_unresolved()` treats `unknown`/missing exit as retryable `checks-child-sigterm`. Genuine `checks-child-failed` with positive exit (e.g. `EXIT_CODE=1`) therefore misclassifies as `transient-infra` / `checks-commit-route-retry` instead of `contract-failure` / `RESUME_HINT=none`. Item 5 prose incorrectly implies genuine content failures always remain contract-failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Narrow unknown branch to negative signal evidence only or document and require --exit-code binding from composite stdout; update item 5 prose.
  - From cursor-specialist-correctness: Extend item 3 with explicit classify template for stall-step phase bail-reason exit-code; bind EXIT_CODE from composite stdout in checks-repair-loop section 4 before Step 18.
  - From cursor-specialist-edge-cases: Extend item 3 classify template with --exit-code "${EXIT_CODE:-unknown}" and bind EXIT_CODE from composite stdout before Step 18 in checks-repair-loop section 1.
  - From codex-generalist: Extend the Step 18a classify template to pass `--stall-step "${STALL_STEP}"`, `--phase "${PHASE:-checks}"`, `--bail-reason "${IMPLEMENT_BAIL_REASON:-${FINAL_BAIL_REASON:-}}"`, and `--exit-code "${EXIT_CODE:-unknown}"`, and update the checks failure macro/reference to bind those KVs from the composite stdout before the no-log skip to Step 18.
  - From dyn-dyn-stall-recovery: Extend Step 18a item 3 (and the checks-failure stall handoff in `skills/implement/references/checks-repair-loop.md`) to bind `EXIT_CODE` from captured composite stdout and pass `--exit-code "${EXIT_CODE:-unknown}"` to `stall-recovery classify`; add a regression test with `checks-child-failed`, no `--exit-code`, no disk `EXIT_CODE`, and in-memory stall tracking that asserts positive child exits stay `step-contract`.


