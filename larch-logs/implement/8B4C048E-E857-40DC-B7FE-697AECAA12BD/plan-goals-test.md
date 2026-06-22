## Goal
Implement issue #5041: [IMPLEMENTING] [OOS] Aggregated rollup of 2 capped OOS items.

## Implementation Plan
## Out-of-Scope Observation

**Surfaced by**: Combined: capped per-run rollup

**Phase**: implement

**Vote tally**: N/A — capped rollup of 2 entries


## Description

Cap 1 (OOS_ISSUES_PER_RUN_CAP) exceeded; the following 2 items were rolled up by skills/implement/scripts/oos-issue-cap.sh:
  - **[OUT_OF_SCOPE] No mechanical generator ties per-file grandfather entries to `complexity-baseline.json`**: OOS_1: [OUT_OF_SCOPE] No mechanical generator ties per-file grandfather entries to complexity-baseline.json - Description: [OUT_OF_SCOPE] No mechanical generator ties per-file grandfather entries to … [Files: python/ruff.toml python/lint_complexity_baseline.py]
  - **No generation/regen entrypoint for baseline or per-file-ignore emission**: OOS_3: No generation/regen entrypoint for baseline or per-file-ignore emission - Description: No generation/regen entrypoint for baseline or per-file-ignore emission. Scenario: Plan requires both art… [Files: generation/regen JSON/TOML python/lint_complexity_baseline.py:132-141]

---
*This issue was automatically created by the larch `/implement` workflow from an out-of-scope observation surfaced during the workflow.*

## Test plan
(no test plan section in plan-file)
