## Goal
Implement issue #5196: [IMPLEMENTING] [OOS] [OUT_OF_SCOPE] Merged postplan-emit --with-plan-size still returns on check-size failure without execution-issues self-log.

## Implementation Plan
## Out-of-Scope Observation

**Surfaced by**: Cursor-Innovation
**Phase**: design
**Vote tally**:

## Description

[OUT_OF_SCOPE] Merged postplan-emit --with-plan-size still returns on check-size failure without execution-issues self-log. Scenario: Initial Step 2b and Gate B merged re-emits call plan check-size inside design_postplan.py, not design step2b5; failures return rc=1 with no append-failure, so the new self-logging pattern does not cover the busiest path

---
*This issue was automatically created by the larch `/implement` workflow from an out-of-scope observation surfaced during the workflow.*

## Test plan
(no test plan section in plan-file)
