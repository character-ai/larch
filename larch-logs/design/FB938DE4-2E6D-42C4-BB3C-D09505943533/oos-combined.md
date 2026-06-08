### OOS_1:
- **Description**: docs/skills.md docs/workflow-lifecycle.md and docs/installation-and-setup.md still document public --approve after the planned hard cutover. Scenario: Operators following shipped consumer docs will use a retired flag and hit Step 0-pre VALIDATION_ERROR=--approve even though skip-approve and per-round-approval work
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: correctness
- **Location**: README.md:59-61
- **Phase**: design

### OOS_2:
- **Description**: plan-review.md Gate B prose still names --approve as the explicit Gate B opt-in. Scenario: The Step 3 finalize reference loaded during plan review will describe a nonexistent public flag after rename
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/design/references/plan-review.md:173-190
- **Phase**: design

### OOS_3:
- **Description**: SECURITY.md still names retired public flag --approve. Scenario: Operators reading security policy get a flag that now hard-errors at Step 0-pre
- **Reviewer**: Cursor-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: SECURITY.md:259
- **Phase**: design

### OOS_4:
- **Description**: --skip-approve auto-approves after summary-mode Gate C preview. Scenario: Plans above the summary threshold can publish without the operator ever viewing the full plan body
- **Reviewer**: Cursor-Edge
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/design/references/approval-gates.md:176-180
- **Phase**: design

### OOS_5: Aggregated rollup of 2 capped OOS items
- **Description**: Cap 5 (OOS_ISSUES_PER_RUN_CAP) exceeded; the following 2 items were rolled up by skills/implement/scripts/oos-issue-cap.sh:
  - **OOS_3:**: - **Description**: Resume OR-merge can set skip_approve_requested=true while a session is mid-loop after Gate C(b) discussion. Scenario: A second Gate C arrival after plan revision could auto-approve … [Files: skills/design/references/approval-gates.md:168-197]
  - **OOS_1:**: - **Description**: LARCH_DESIGN_PLAN_SUMMARY_THRESHOLD docs describe Gate C summary mode but the plan's consumer-doc sweep omits this file. Scenario: Operators tuning summary behavior will not see tha… [Files: docs/configuration-and-permissions.md:264-270]
- **Reviewer**: Combined: capped per-run rollup
- **Vote tally**: N/A — capped rollup of 2 entries
- **Phase**: implement

