### FINDING_1: Cap breadcrumb pin must stay aligned with routing prose
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan changes per-tier cap routing prose but does not specify whether the existing pinned cap breadcrumb remains literal. This can either fail `test-design-structure.sh` or leave misleading “returning to Gate C” wording.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation, Cursor-Pragmatic: Pin requires `skipping panel and returning to Gate C.`; routing-only edits fail `test-design-structure.sh` or leave misleading "returning to Gate C" copy Keep the breadcrumb literal and fix routing only in non-pinned sentences (e.g. SKILL.md:1128), or update the pin in the same change

### FINDING_2: Approval-gates must carry identical Step 3.6 skip breadcrumbs
- **Reviewer(s)**: Cursor-dyn-cross-doc-consistency, Codex-dyn-cross-doc-consistency
- **Severity**: important
- **Concern**: The planned `SKILL.md` changes add exact Step 3.6 skip breadcrumbs for multiple bypass statuses, but the `approval-gates.md` plan only updates bypass prose. After implementation, the two files could have aligned routing lists but non-identical breadcrumb coverage, violating the directive that both files carry strictly identical breadcrumb strings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-cross-doc-consistency, Codex-dyn-cross-doc-consistency: Add the same six Step 3.6 skip breadcrumb literals to approval-gates.md, byte-for-byte matching SKILL.md, alongside the Gate-B-bypass status list; keep this as a compact list/table to avoid broader prose churn.

### FINDING_3: Structure test needs exact route-through versus skip status matrix
- **Reviewer(s)**: Cursor-dyn-status-enumeration, Codex-dyn-status-enumeration
- **Severity**: important
- **Concern**: The proposed structure pins only assert a passive-summary sentence and a Gate-B-bypass sentence. An implementation could satisfy those contains-style checks while omitting or duplicating Step 3 statuses across route-through and skip prose.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-status-enumeration, Codex-dyn-status-enumeration: Add one focused test-design-structure assertion with explicit expected route-through and skip sets, then fail on missing or repeated statuses across those two categories. Keep test-assess-plan-round.sh limited to the two-entry assessor harness as planned.
