### OOS_1: Aggregated rollup of 2 capped OOS items
- **Description**: Cap 1 (OOS_ISSUES_PER_RUN_CAP) exceeded; the following 2 items were rolled up by skills/implement/scripts/oos-issue-cap.sh:
  - **OOS_1:**: - **Description**: No fetch of origin default before merge-base check. Scenario: Stale origin/default ref can miss already-merged branch and skip idempotent short-circuit - **Reviewer**: Cursor-Arch -… [Files: scripts/design-log-publish.sh:21]
  - **OOS_2:**: - **Description**: Merged-branch harness may not match squash production semantics. Scenario: The planned test merges a log branch into main while keeping the remote ref. Unless the harness simulates … [Files: plan.txt:66-72 scripts/test-design-log-publish.sh:66-72]
- **Reviewer**: Combined: capped per-run rollup
- **Vote tally**: N/A — capped rollup of 2 entries
- **Phase**: implement

