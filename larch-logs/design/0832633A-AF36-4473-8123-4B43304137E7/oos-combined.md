### OOS_1: Aggregated rollup of 3 capped OOS items
- **Description**: Cap 1 (OOS_ISSUES_PER_RUN_CAP) exceeded; the following 3 items were rolled up by skills/implement/scripts/oos-issue-cap.sh:
  - **OOS_1:**: - **Description**: Synthetic defects-found triggers command auto-fix for composition omission. Scenario: Empty composed-plan.md satisfies plan.is_file so auto-fix may dispatch vendors before the opera… [Files: composed-plan.md skills/design/SKILL.md:912-925]
  - **OOS_1:**: - **Description**: State invariant still says all Step 5c validator Fix-and-retry / Override / autofix-success paths re-enter via `design-step5c.sh --skip-validate`. Scenario: Future readers may reint… [Files: design-step5c.sh skills/design/references/approval-gates.md:225]
  - **OOS_1:**: - **Description**: flags.md still implies --skip-validate skips all Step 5c composed-plan validation. Scenario: After the change, proceed-anyway skips only ordinary command validation; the missing-or-… [Files: flags.md skills/design/references/flags.md:73]
- **Reviewer**: Combined: capped per-run rollup
- **Vote tally**: N/A — capped rollup of 3 entries
- **Phase**: implement

