### OOS_1:
- **Description**: Gantt vendor selection uses temporal overlap only, not reviewer task_kind. Scenario: Vendor rows from sketches, implement, or CI-fix with timestamps inside a review round window can appear under ### Round N reviewer timing with misleading labels
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: scripts/render-review-phase-detail.sh:31-43
- **Phase**: design

### OOS_2:
- **Description**: Implement caller doc still says renderer outputs nothing for self-review. Scenario: After renderer change, write-final-report.md contradicts behavior; implement callers are out of plan scope
- **Reviewer**: Cursor-Arch
- **Severity**: nit
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/write-final-report.md:110-112
- **Phase**: design

### OOS_1:
- **Description**: Live progress reports call the shared renderer during in-flight review when round dirs exist but round-meta.json does not. Scenario: Step 5 progress output can append No review rounds completed while a round is actively running misleading operators mid-run
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/progress_report.py:382-405
- **Phase**: design

### OOS_2:
- **Description**: Plan cites overlap selection for vendor rows but does not pin the interval predicate. Scenario: Mismatched inclusive or exclusive boundary rules can drop edge-touching vendor bars or include tasks from adjacent phases
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/render-review-phase-detail.sh
- **Phase**: design

### OOS_1:
- **Description**: Harness asserts Gantt substrings via grep but never runs mmdc --parseOnly or python/cli.py lint mermaid-fences on generated output. Scenario: A typo in label sanitization or task-line punctuation could pass all new grep assertions while still producing an unparsable fence; the failure would only show up when GitHub or lint-mermaid-fences renders the summary
- **Reviewer**: Cursor-dyn-mermaid-gantt-format
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: scripts/test-render-review-phase-detail.sh:121-140
- **Phase**: design

