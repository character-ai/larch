### OOS_2: [OUT_OF_SCOPE] run_ci_fix_vendor remains cursor-or-codex with three launch attempts; no Claude

- **Severity**: latent
- **Focus area**: architecture
- **Location**: scripts/ship-pr.sh:1225-1361
- **Description**: run_ci_fix_vendor remains cursor-or-codex with three launch attempts; no Claude tier in evaluate-failure loop
- **Scenario**: Inconsistent recovery depth between CI-eval path and new stall waterfalls
- **Suggested fix**: Track follow-up to add third tier or document intentional asymmetry
- **Reviewer**: Cursor-Innovation

