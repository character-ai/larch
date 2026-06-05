### FINDING_1: Shipped plugin manifest still advertises retired implement hard workflow/path contract
- **Reviewer(s)**: Codex-Edge, Codex-Requirements, Codex-dyn-stale-contracts
- **Severity**: important
- **Concern**: `.claude-plugin/plugin.json` remains a shipped runtime/operator surface that describes `/implement` using stale hard workflow/path wording after the plan removes implement workflow classification. Consumers could see metadata that contradicts the new no-workflow-path contract, and acceptance checks may miss this stale shipped contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Update the manifest description to remove hard workflow path wording and describe /implement without a workflow tier/path dimension
  - From Codex-Requirements: Add .claude-plugin/plugin.json to the plan and reword the description to remove implement hard workflow/path framing while preserving the current /design tier wording
  - From Codex-dyn-stale-contracts: Add .claude-plugin/plugin.json to the plan updates; reword the description to keep /design SIMPLE/HARD wording design-only and describe /implement as fixed-timeout/no-workflow-path, and include this file in the stale-term acceptance grep


### FINDING_3: Timing ledger marks can still inherit polluted design skill context
- **Reviewer(s)**: Codex-dyn-env-isolation
- **Severity**: important
- **Concern**: The plan pins `timing-report.sh` to implement but leaves adjacent `timing-ledger.sh` mark commands dependent on ambient `LARCH_TIMING_SKILL`. If the parent environment is polluted with `design`, fresh implement timing boundaries may be recorded as design and then ignored by the implement-scoped report.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-env-isolation: Pin LARCH_TIMING_SKILL=implement on the adjacent timing-ledger.sh mark commands, or wrap each mark-plus-report block in an implement-scoped environment while making the planned report changes


### FINDING_4: Implement cache JSON workflow omission lacks direct test coverage
- **Reviewer(s)**: Codex-dyn-report-schema-drift
- **Severity**: important
- **Concern**: The plan says implement cache JSON omits workflow, but planned tests only cover markdown/golden output. Cache rows could still serialize workflow from legacy records even if visible report columns are removed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-report-schema-drift: Add minimal render-test assertions that implement cache rows lack workflow and design cache rows still retain workflow


### FINDING_5: Implement scan tests do not prove workflow artifacts are not read
- **Reviewer(s)**: Codex-dyn-report-schema-drift
- **Severity**: important
- **Concern**: The planned valid timing-report fixture could pass even if the scanner still opens implement workflow artifacts and discards their values. That would preserve the unwanted implement scan-input boundary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-report-schema-drift: Add one implement scan fixture with malformed or symlinked workflow artifacts and assert workflow == "" with no auxiliary artifact warnings; keep design fallback tests unchanged### OOS_1:
- **Description**: Marketplace description still says post-plan implement steps use the conventional hard workflow path. Scenario: Operators and marketplace consumers infer implement still has a HARD/SIMPLE workflow knob after this PR removes it entirely
- **Reviewer**: Cursor-dyn-stale-contracts
- **Severity**: latent
- **Focus area**: architecture
- **Location**: .claude-plugin/plugin.json:4
- **Phase**: design


