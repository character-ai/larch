## Goal
Implement issue #5349: [IMPLEMENTING] [OOS] Aggregated rollup of 2 capped OOS items.

## Implementation Plan
## Out-of-Scope Observation

**Surfaced by**: Combined: capped per-run rollup

**Phase**: implement

**Vote tally**: N/A — capped rollup of 2 entries


## Description

Cap 1 (OOS_ISSUES_PER_RUN_CAP) exceeded; the following 2 items were rolled up by the per-run OOS issue cap. Each rolled-up item's full body is preserved verbatim below:
  - **[OUT_OF_SCOPE] No mechanical enforcement or structure-test pin for NEVER #21**: [Files: scripts/test-implement-structure.sh Edit/Write.]
    ### OOS_1: [OUT_OF_SCOPE] No mechanical enforcement or structure-test pin for NEVER #21
    - **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
    - **Severity**: latent
    - **Concern**: NEVER #21 has no structural `require()` pin in `scripts/test-implement-structure.sh` unlike NEVER #8 and #14. No dirty-tree probe at item 6 exit or hook gating on Edit/Write. Prompt-only guard can still be ignored. Future work per issue open questions.
    - **Suggested revisions (informational for voters; coder decides)**:
      - Add a `require(skill, 'NEVER make Edit, Write, or repo-mutating Bash calls between Preflight item 6', ...)` pin alongside the existing NEVER pins.
  - **[OUT_OF_SCOPE] Bootstrap ordering: tracking rename before dirty-tree check**: [Files: python/bootstrap.py]
    ### OOS_2: [OUT_OF_SCOPE] Bootstrap ordering: tracking rename before dirty-tree check
    - **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
    - **Severity**: nit
    - **Concern**: In `python/bootstrap.py`, tracking rename runs before dirty-tree check and branch creation. Pre-Step-0 edits plus Step 0 can yield an `[IMPLEMENTING]` title with dirty `main` and no feature branch.
    - **Suggested revisions (informational for voters; coder decides)**:
      - Consider moving the dirty-tree check and branch creation before tracking issue rename in a follow-up.

---
*This issue was automatically created by the larch `/implement` workflow from an out-of-scope observation surfaced during the workflow.*

## Test plan
(no test plan section in plan-file)
