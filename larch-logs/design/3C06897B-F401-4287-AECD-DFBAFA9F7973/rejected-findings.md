### [Plan Review] FINDING_32

### FINDING_32:
- **Reviewer(s)**: Cursor-dyn-sequence-absorb
- **Severity**: latent
- **Focus area**: correctness
- **Location**: plan.txt:219-221
- **Concern**: Failure modes cite full invoke-log order tests but plan only asserts post-bail skips. Scenario: Green-path reorder regressions (e.g. dirty-tree before persist) slip past B6/B7-only skip assertions
- **Proposed resolution**: Add green-path invoke-log ordering assert in B5-plan or dedicated case matching Failure modes section 1 sequence


### [Plan Review] FINDING_33

### FINDING_33:
- **Reviewer(s)**: Cursor-dyn-sequence-absorb
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: plan.txt:94-98
- **Concern**: Success breadcrumbs always emitted after best-effort upsert failure. Scenario: tracking-issue-summary failure still prints step0 larch:plan posted misleading operators
- **Proposed resolution**: Gate emit_breadcrumb larch:plan posted on summary upsert rc=0 or emit a degraded breadcrumb when append-tool-failure runs


### [Plan Review] FINDING_45

### FINDING_45:
- **Reviewer(s)**: Codex-dyn-test-gap
- **Severity**: latent
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:34-39,167-170
- **Concern**: The dirty-tree unknown branch is named but untested. Scenario: The plan treats STATUS=dirty and STATUS=unknown identically, but B7 only configures STATUS=dirty, so a parsing/default bug for unknown can ship without a regression failure
- **Proposed resolution**: Parameterize B7 over dirty and unknown or add B7-unknown with the same bail and no-subsequent-helper assertions


### [Plan Review] FINDING_47

### FINDING_47:
- **Reviewer(s)**: Codex-dyn-test-gap
- **Severity**: nit
- **Focus area**: architecture
- **Location**: <TMPDIR>/plan.txt:148-188,221
- **Concern**: The order-of-operations failure mode is not translated into concrete test assertions. Scenario: The failure mode says invoke-log order assertions are the warning signal, but B5-B10 only specify success/skip/no-subsequent checks and never require the full snapshot -> gh -> cp -> workflow-path -> persist -> dirty -> branch -> current-branch -> plan-log -> summary order
- **Proposed resolution**: Add an explicit ordered invoke-log assertion to B5 green-path so reordering the absorbed Step 0 calls fails the harness


