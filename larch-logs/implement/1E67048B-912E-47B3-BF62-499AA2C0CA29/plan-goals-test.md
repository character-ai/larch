## Goal
Implement issue #5219: [IMPLEMENTING] [OOS] Aggregated rollup of 2 capped OOS items.

## Implementation Plan
## Out-of-Scope Observation

**Surfaced by**: Combined: capped per-run rollup

**Phase**: implement

**Vote tally**: N/A — capped rollup of 2 entries


## Description

Cap 1 (OOS_ISSUES_PER_RUN_CAP) exceeded; the following 2 items were rolled up by the per-run OOS issue cap. Each rolled-up item's full body is preserved verbatim below:
  - **correctness/risk-integration: python/implement_dispatch.py:1375-1650**: [Files: correctness/risk-integration python/implement_dispatch.py:1375-1650 1412/1584/1640 1646/1650.]
    ### OOS_1: correctness/risk-integration: python/implement_dispatch.py:1375-1650
    - **Reviewer**: cursor-specialist-correctness-output.txt; cursor-specialist-edge-cases-output.txt; codex-specialist-edge-cases-output.txt; codex-specialist-testing-output.txt
    - **Concern**: [important] `_append_warning` still allows plain non-bullet warning entries, while `exec_issue_detail` / final-summary detail parsing only renders bullet lines. The git-probe skip, plan-read failure, Codex nonzero-exit salvage, and working-tree touched-path probe warnings around 1412/1584/1640 can be written to `execution-issues.md` but omitted from `## Exec Issues and Warnings`, including the detailed Warnings block and header counts. This is the same class as the 614EEA92 path-only regression.
    - **Suggested revision**: Normalize warning entries in `_append_warning` or convert all implement_dispatch warning callers to the single-line `- **Step …**: description` shape used around 1646/1650. Add a final-summary parser regression for one of these warning paths.
  - **correctness: python/design_postplan.py:91**: [Files: python/design_postplan.py:91]
    ### OOS_2: correctness: python/design_postplan.py:91
    - **Reviewer**: cursor-specialist-correctness-output.txt
    - **Concern**: [important] `_self_log_check_size_failure` hardcodes site design Step 2b.5 but runs from `postplan_emit_main` in Step 2b. Check-size failures on the drafter postplan path appear in the final summary as Step 2b.5 warnings.
    - **Suggested revision**: Pass the actual site, such as design Step 2b, via parameter.

---
*This issue was automatically created by the larch `/implement` workflow from an out-of-scope observation surfaced during the workflow.*

## Test plan
(no test plan section in plan-file)
