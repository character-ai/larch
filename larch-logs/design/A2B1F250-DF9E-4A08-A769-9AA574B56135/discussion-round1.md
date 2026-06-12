## Decision 1: Bug 1 fix approach
- **Question**: Which fix approach for mechanical_churn integer bypass — awk stderr, plan-size exit 2, or both?
- **Resolution**: Both — awk emits stderr diagnostic when value is not boolean, AND check-plan-size.sh exits 2 with PLAN_SIZE_STATUS=invalid-mechanical-churn.
- **Source**: user

## Decision 2: Bug 2 scope — plan-review-continuation.sh
- **Question**: Should plan-review-continuation.sh be updated to add ballot-items-lost continuation branch (not listed in issue's Affected files)?
- **Resolution**: Yes — add DEGRADED_PANEL=1 + ACCEPTED_COUNT=0 → CONTINUE=true REASON=ballot-items-lost. Without this, setting DEGRADED_PANEL=1 in plan-review-loop.sh has no downstream effect on round scheduling.
- **Source**: user
