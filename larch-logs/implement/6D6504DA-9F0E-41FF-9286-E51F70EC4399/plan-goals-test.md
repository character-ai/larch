## Goal
Implement issue #5369: [IMPLEMENTING] [OOS] Aggregated rollup of 2 capped OOS items.

## Implementation Plan
## Out-of-Scope Observation

**Surfaced by**: Combined: capped per-run rollup

**Phase**: implement

**Vote tally**: N/A — capped rollup of 2 entries


## Description

Cap 1 (OOS_ISSUES_PER_RUN_CAP) exceeded; the following 2 items were rolled up by the per-run OOS issue cap. Each rolled-up item's full body is preserved verbatim below:
  - **[OUT_OF_SCOPE] Stale Gate C preview wrapper reference in configuration docs**: [Files: docs/configuration-and-permissions.md skills/design/scripts/design-step3b-tail.sh]
    ### OOS_1: [OUT_OF_SCOPE] Stale Gate C preview wrapper reference in configuration docs
    - **Reviewer(s)**: codex-specialist-testing-output.txt, cursor-specialist-testing, codex-generic
    - **Severity**: nit
    - **Concern**: `docs/configuration-and-permissions.md` still references the retired `design-step4b-preview.sh` Gate C preview wrapper even though the active flow uses `skills/design/scripts/design-step3b-tail.sh`. Operators auditing Gate C flow may follow the wrong wrapper.
    - **Suggested revisions (informational for voters; coder decides)**:
      - Update the stale docs reference to name `design-step3b-tail.sh` only and describe the active merged Step 4 tail fence.
  - **[OUT_OF_SCOPE] dialectic-protocol.md Overview still documents removed Step 2a.5 flow**: [Files: skills/shared/dialectic-protocol.md]
    ### OOS_2: [OUT_OF_SCOPE] dialectic-protocol.md Overview still documents removed Step 2a.5 flow
    - **Reviewer(s)**: dyn-dyn-dialectic-lifecycle-output.txt, cursor-specialist-edge-cases, dyn-dyn-dialectic-lifecycle
    - **Severity**: nit
    - **Concern**: Overview prose in `skills/shared/dialectic-protocol.md` still describes the removed Step 2a.5 external debater waterfall and binding `dialectic-resolutions.md` output. Maintainers may implement against obsolete choreography even though the Gate C clarifier profile subsection was added.
    - **Suggested revisions (informational for voters; coder decides)**:
      - Update the Overview section to reflect the active Gate C clarifier path.

---
*This issue was automatically created by the larch `/implement` workflow from an out-of-scope observation surfaced during the workflow.*

## Test plan
(no test plan section in plan-file)
