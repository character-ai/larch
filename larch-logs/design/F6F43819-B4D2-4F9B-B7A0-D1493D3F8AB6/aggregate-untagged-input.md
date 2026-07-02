### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/lint/lint_skill_closure_growth.py:592-602
- **Concern**: Conditional closure becomes ratcheted but report output still says reported only. Scenario: Plan extends baseline and _growth_violations with conditional_* for skill targets, but Report labels and test_report_mode_prints_design_and_implement still assert the Conditional closure (reported only) header. Operators and CI will treat conditional metrics as informational while lint fails on conditional growth.
- **Proposed resolution**: Update _print_report to label conditional closure as ratcheted for skill targets (panel-tier may stay zero), and update the report-mode test expectations accordingly.

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/lint/lint_skill_closure_growth.py:592-593
- **Concern**: Report output still labels conditional closure as reported only. The plan renames the eager `skill` column to `target` but keeps the `Conditional closure (reported only)` header while `_growth_violations()` will ratchet conditional metrics for skill targets. Operators can see a passing report section label and still get a conditional growth lint failure, or misread review conditional as non-ratcheted.. Scenario: In the Report labels work, retitle the conditional section for skill targets (for example `Conditional closure (ratcheted)`) and note in docs that `panel-tier` prints zero conditional metrics.
- **Proposed resolution**:

### FINDING_9:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/lint/lint_skill_closure_growth.py:592-602
- **Concern**: Conditional metrics move into the baseline ratchet, but the report subtitle still says `Conditional closure (reported only)`. Scenario: The plan extends baseline keys and `_growth_violations()` to compare `conditional_*` for skill targets, so conditional growth will fail `lint skill-closure-growth`. `_print_report()` still labels that section reported-only, contradicting post-change behavior and docs operators will read.
- **Proposed resolution**: Rename the conditional section header to reflect ratcheted skill targets (for example `Conditional closure (ratcheted for skill targets)`), keep panel-tier zeros explicit, and mirror the wording in `docs/linting.md`.
