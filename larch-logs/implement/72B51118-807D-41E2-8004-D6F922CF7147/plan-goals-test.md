## Goal
Implement issue #5095: [IMPLEMENTING] [OOS] Aggregated rollup of 2 capped OOS items.

## Implementation Plan
## Out-of-Scope Observation

**Surfaced by**: Combined: capped per-run rollup

**Phase**: implement

**Vote tally**: N/A — capped rollup of 2 entries


## Description

Cap 1 (OOS_ISSUES_PER_RUN_CAP) exceeded; the following 2 items were rolled up by the per-run OOS issue cap:
  - **[OUT_OF_SCOPE] Unclosed bash fence openers treated as closed at EOF**: (malformed item — body unavailable)
  - **[OUT_OF_SCOPE] Example-fence suppression is broader than documented and can hide real bash fences**: (malformed item — body unavailable)

---
*This issue was automatically created by the larch `/implement` workflow from an out-of-scope observation surfaced during the workflow.*

## Test plan
(no test plan section in plan-file)
