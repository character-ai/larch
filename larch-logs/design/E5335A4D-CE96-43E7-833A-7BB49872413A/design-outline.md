## Proposed Design Outline

### Goals
- Move Gate B severity-count computation and findings-table rendering to Python.
- Reduce `approval-gates.md` prose to Python-call directives on the `--per-round-approval` path.

### Non-goals
- Changing Gate B classification rules, severity thresholds, or rubric mappings.
- Touching the default auto-apply path (cold path; no user prompt fires there).
- Altering the `plan-review continuation` continuation-decision logic itself.

### Approach sketch
- Extend `plan_review_continuation` to also emit `MEDIUM_ACCEPTED_COUNT`, `LOW_ACCEPTED_COUNT`, `CRITICAL_ACCEPTED_COUNT`, and `GATE_B_SEVERITY_MODE` (`structured` or `fallback`).
- Add `gate-b` variant to `emit_design_plan_preview` (reads `accepted-plan-findings.md`, renders `FINDING_N | Severity | Reviewer(s) | excerpt` table).
- Register `plan-review gate-b-counts` CLI verb that delegates to a thin helper that calls the classification logic and emits the KV lines (allows Gate B to call it without invoking the full continuation decision).
- Update `approval-gates.md` §Presentation to replace inline classification prose with `plan-review gate-b-counts` and `plan-review preview --variant gate-b` calls.

### Surfaces in scope
- `python/plan_review.py`
- `python/test_plan_review.py`
- `python/cli.py`
- `skills/design/references/approval-gates.md`

### Open questions
- None.
