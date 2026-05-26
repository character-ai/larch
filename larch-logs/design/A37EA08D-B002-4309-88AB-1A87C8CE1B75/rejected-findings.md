### [Plan Review] FINDING_30

### FINDING_30:
- **Reviewer(s)**: Codex-dyn-doc-surface-sync
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: docs/workflow-lifecycle.md:92,107-111
- **Concern**: 4. workflow-lifecycle.md is an omitted public docs surface for the new /design mode. Scenario: The plan conditionally updates README when it enumerates /design flags, but docs/workflow-lifecycle.md also documents standalone /design usage and the /design flag table; after the PR, readers there would not see the manual opt-out for the new default auto-apply behavior
- **Proposed resolution**: Add docs/workflow-lifecycle.md to reconciliation scope and document --manual/-m either in the standalone /design signature/prose or the Flags table as the Gate B manual-review opt-out


### [Plan Review] FINDING_35

### FINDING_35:
- **Reviewer(s)**: Cursor-dyn-apply-body-factoring, Cursor-dyn-apply-body-factoring, Cursor-dyn-apply-body-factoring
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:102
- **Concern**: skills/design/references/approval-gates.md:86. Scenario: Apply-all pipeline exists only as inline text inside the Apply all bullet; plan allows copy-paste OR optional factoring
- **Proposed resolution**: Implementer can paraphrase or truncate the auto-apply branch and omit dedup-sweep, dedup-sweep breadcrumb, ACTION=EMIT_PLAN, invoke-plan-validator-if-not-quick.sh, or Step 2b.5 without violating the written plan Mandate a named ### Apply-all body subsection with a stable anchor; require both manual option (a) and auto-apply to say Execute ### Apply-all body verbatim (no OR copy-paste path)


### [Plan Review] FINDING_41

### FINDING_41:
- **Reviewer(s)**: Cursor-dyn-apply-body-factoring
- **Severity**: nit
- **Focus area**: architecture
- **Location**: plan.txt:33-34
- **Concern**: plan.txt:153. Scenario: Failure mode #3 recommends shared subsection and agent-lint anchor but Hard constraints and approval-gates edit allow optional duplication
- **Proposed resolution**: Mitigation stays advisory while implementation path permits drift Add to Hard constraints: auto-apply and manual Apply all MUST reference a single named Apply-all body subsection; add agent-lint pin in Testing strategy (not optional)


