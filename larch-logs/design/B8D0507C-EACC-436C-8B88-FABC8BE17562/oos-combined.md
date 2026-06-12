### OOS_1: Aggregated rollup of 6 capped OOS items
- **Description**: Cap 1 (OOS_ISSUES_PER_RUN_CAP) exceeded; the following 6 items were rolled up by skills/implement/scripts/oos-issue-cap.sh:
  - **OOS_4:**: - **Description**: Harness will assert substring presence only, not Mermaid parse validity. Scenario: Planned tests grep for gantt/dateFormat/axisFormat strings but never run python/cli.py lint mermai… [Files: python/cli.py scripts/test-render-review-phase-detail.sh:84-97]
  - **OOS_1:**: - **Description**: render-final-summary.md is in render-review-phase-detail.md edit-in-sync but absent from the plan Files list.. Scenario: Docs drift on empty vs in-flight vs Gantt behavior for desig… [Files: render-final-summary.md render-review-phase-detail.md skills/design/scripts/render-final-summary.md:58-60]
  - **OOS_2:**: - **Description**: The plan matches vendor rows to rounds by time overlap only and does not filter `$2=="vendor"` rows by `$4` skill or review-related `$7` task_kind.. Scenario: Non-reviewer vendor ta… [Files: scripts/render-review-phase-detail.sh:224-236]
  - **OOS_3:**: - **Description**: skills/implement/scripts/write-final-report.md is slated for doc sync, but the paired design caller doc `skills/design/scripts/render-final-summary.md` is not, even though `scripts/… [Files: plan.txt:149-153 scripts/render-review-phase-detail.md:86-91 skills/design/scripts/render-final-summary.md skills/implement/scripts/write-final-report.md]
  - **OOS_3:**: - **Description**: Live progress reports call the shared renderer during in-flight review when round dirs exist but round-meta.json does not. Scenario: Step 5 progress output can append No review roun… [Files: python/progress_report.py:382-405 round-meta.json]
  - **OOS_5:**: - **Description**: Harness asserts Gantt substrings via grep but never runs mmdc --parseOnly or python/cli.py lint mermaid-fences on generated output. Scenario: A typo in label sanitization or task-li… [Files: python/cli.py scripts/test-render-review-phase-detail.sh:121-140]
- **Reviewer**: Combined: capped per-run rollup
- **Vote tally**: N/A — capped rollup of 6 entries
- **Phase**: implement

