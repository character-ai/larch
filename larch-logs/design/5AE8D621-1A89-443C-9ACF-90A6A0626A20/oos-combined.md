### OOS_1: Aggregated rollup of 2 capped OOS items
- **Description**: Cap 1 (OOS_ISSUES_PER_RUN_CAP) exceeded; the following 2 items were rolled up by skills/implement/scripts/oos-issue-cap.sh:
  - **OOS_2:**: - **Description**: docs/python-migration.md:68-71. Scenario: docs/python-migration.md and docs/linting.md still say never bare basenames after behavior change - **Reviewer**: Cursor-dyn-lint-scope - *… [Files: docs/linting.md docs/python-migration.md docs/python-migration.md:68-71. plan.txt:38]
  - **OOS_1:**: - **Description**: [OUT_OF_SCOPE] lint-retired-scripts table row still claims full-path-only matching with no bare-basename branch. Scenario: After the scoped `.claude/skills/**/*.md` basename check l… [Files: AGENTS.md docs/linting.md docs/linting.md:174]
- **Reviewer**: Combined: capped per-run rollup
- **Vote tally**: N/A — capped rollup of 2 entries
- **Phase**: implement

