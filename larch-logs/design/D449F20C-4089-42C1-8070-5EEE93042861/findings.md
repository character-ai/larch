### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-design-structure.sh:86
- **Concern**: skills/design/references/approval-gates.md:17. Scenario: Plan revises per-tier cap prose to drop "short-circuits to Gate C" but does not say whether the pinned cap breadcrumb stays verbatim
- **Proposed resolution**: Pin requires `skipping panel and returning to Gate C.`; routing-only edits fail `test-design-structure.sh` or leave misleading "returning to Gate C" copy Keep the breadcrumb literal and fix routing only in non-pinned sentences (e.g. SKILL.md:1128), or update the pin in the same change

### FINDING_2:
- **Reviewer(s)**: Cursor-dyn-cross-doc-consistency, Codex-dyn-cross-doc-consistency
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:52-65,71-97; skills/design/SKILL.md:1107-1134; skills/design/references/approval-gates.md:90-99,167-168
- **Concern**: The proposed SKILL.md changes add exact Step 3.6 skip breadcrumbs for tally-error, degraded-empty-collector, panel-failed, cap-reached, plan-size-trigger, and plan-validator-defects, but the approval-gates.md section of the plan only updates bypass prose and does not require the same breadcrumb strings there.. Scenario: After implementation, SKILL.md and approval-gates.md can have aligned routing lists but non-identical breadcrumb coverage, violating the plan-review directive that both files carry strictly identical breadcrumb strings for every Step 3 bypass status.
- **Proposed resolution**: Add the same six Step 3.6 skip breadcrumb literals to approval-gates.md, byte-for-byte matching SKILL.md, alongside the Gate-B-bypass status list; keep this as a compact list/table to avoid broader prose churn.

### FINDING_3:
- **Reviewer(s)**: Cursor-dyn-status-enumeration, Codex-dyn-status-enumeration
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:99-109; scripts/test-design-structure.sh:21-24
- **Concern**: The proposed structure pins only require a passive-summary sentence and a Gate-B-bypass sentence, not an exact one-category status matrix for the named Step 3 exits.. Scenario: An implementation can satisfy those two contains-style pins while omitting or duplicating a status such as complete, revision-failed, emit-plan-failed, main-agent-vote-required, panel-failed, or cap-reached across route-through versus skip prose.
- **Proposed resolution**: Add one focused test-design-structure assertion with explicit expected route-through and skip sets, then fail on missing or repeated statuses across those two categories. Keep test-assess-plan-round.sh limited to the two-entry assessor harness as planned.
