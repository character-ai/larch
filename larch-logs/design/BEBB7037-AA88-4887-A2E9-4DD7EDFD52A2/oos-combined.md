### OOS_1: Aggregated rollup of 2 capped OOS items
- **Description**: Cap 1 (OOS_ISSUES_PER_RUN_CAP) exceeded; the following 2 items were rolled up by skills/implement/scripts/oos-issue-cap.sh:
  - **OOS_1:**: - **Description**: Terminal outcome constants are duplicated into Python with only a manual “keep in sync” note. Scenario: No mechanical guard ties `RUN_LOG_TERMINAL_OUTCOME_SUFFIX_EGREP` to Python co…
  - **OOS_4:**: - **Description**: `capture-transcript` argv list omits `--warning-step-label`. Scenario: Bash accepts `--warning-step-label` (default `7a`) and forwards it into warning bullets (`scripts/capture-sess… [Files: plan.txt:135-136 scripts/capture-session-transcript.sh:24-25]
- **Reviewer**: Combined: capped per-run rollup
- **Vote tally**: N/A — capped rollup of 2 entries
- **Phase**: implement

