### OOS_1: Aggregated rollup of 2 capped OOS items
- **Description**: Cap 1 (OOS_ISSUES_PER_RUN_CAP) exceeded; the following 2 items were rolled up by skills/implement/scripts/oos-issue-cap.sh:
  - **OOS_1:**: - **Description**: [OUT_OF_SCOPE] Shell-hardcoded CI kind lists will drift from `TIMING_TASK_KINDS_ALLOWED` and launcher defaults. Scenario: `timing.py` documents `*-ci-fix` while launchers record `co… [Files: python/timing.py:20-40 timing.py]
  - **OOS_1:**: - **Description**: Live Step 5 inflight Gantt uses a separate unfiltered vendor-row path. Scenario: _render_inflight_gantt calls _progress_vendor_rows without CI/probe filtering and uses a live now() … [Files: python/progress_report.py:520-593]
- **Reviewer**: Combined: capped per-run rollup
- **Vote tally**: N/A — capped rollup of 2 entries
- **Phase**: implement

