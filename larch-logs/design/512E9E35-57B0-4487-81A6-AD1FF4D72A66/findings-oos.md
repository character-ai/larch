### OOS_1:
- **Description**: Still documents --quick plan review via plan-review-quick.md. Scenario: Public doc contradicts two-tier full-panel model
- **Reviewer**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: docs/voting-process.md:7
- **Phase**: design

### OOS_2:
- **Description**: Harness still references plan-review-quick.md. Scenario: make lint fails after file delete
- **Reviewer**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-effort-prose.sh:15
- **Phase**: design

### OOS_3:
- **Description**: Doc still describes quick Claude-only plan review. Scenario: Contradicts full-panel SIMPLE/HARD model
- **Reviewer**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: docs/voting-process.md:7
- **Phase**: design

### OOS_4:
- **Description**: Topology rule still inputs deleted quick doc. Scenario: Regeneration or lint may reference missing file
- **Reviewer**: Cursor-Edge
- **Severity**: nit
- **Focus area**: architecture
- **Location**: .claude/rules/topology-generation.md:10
- **Phase**: design

### OOS_5:
- **Description**: Plan updates timing-ledger run-params reads not present in code. Scenario: No current reader; scope unclear unless new workflow-path record added from design
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: architecture
- **Location**: scripts/timing-ledger.sh:176-189
- **Phase**: design

### OOS_6:
- **Description**: [OUT_OF_SCOPE] The prompt-source grep list still includes skills/design/references/plan-review-quick.md, but the plan does not list this harness. Scenario: After the file is deleted, test-effort-prose can fail because grep is invoked on a missing prompt file during make lint
- **Reviewer**: Codex-dyn-deletion-completeness
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-effort-prose.sh:9-16
- **Phase**: design

