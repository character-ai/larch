### OOS_1: Aggregated rollup of 3 capped OOS items
- **Description**: Cap 1 (OOS_ISSUES_PER_RUN_CAP) exceeded; the following 3 items were rolled up by skills/implement/scripts/oos-issue-cap.sh:
  - **OOS_1:**: - **Description**: Post-pack feasibility order not reflected in the dev SKILL prompt. Scenario: After Item 5, rebalance.md will describe pack-then-check, but SKILL.md step 3 still says to run feasibil… [Files: .claude/skills/rebalance-test-harnesses/SKILL.md:28-32 SKILL.md rebalance.md rebalance.py]
  - **OOS_2:**: - **Description**: No harness assertion pins the orchestrator-never premature-notification carve-out. Scenario: Plan lists test-implement-anti-polling-rule.sh in Testing strategy, but the harness only… [Files: orchestrator-never.md. scripts/test-implement-anti-polling-rule.sh:86-88 test-implement-anti-polling-rule.sh]
  - **OOS_3:**: - **Description**: [SCOPE-REDUCTION] Item 4 expands validator enum beyond prompt contract. Scenario: Prompt surfaces at reviewer-templates.md:204 and rendering.py:1136 still allow only important/nit/l… [Files: rendering.py:1136 reviewer-templates.md:204 skills/shared/reviewer-templates.md:204]
- **Reviewer**: Combined: capped per-run rollup
- **Vote tally**: N/A — capped rollup of 3 entries
- **Phase**: implement

