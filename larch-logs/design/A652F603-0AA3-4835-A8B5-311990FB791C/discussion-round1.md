## Decision 1: Fix scope — primary gate plus accurate bail detail
- **Question**: Beyond gating the CI_NOT_READY→REVIEW_REQUIRED conversion on `no_admin_fallback`, how much of issue #6071's secondary considerations should the fix include?
- **Resolution**: Primary fix (gate the conversion on `working.no_admin_fallback`) PLUS correct the misleading hardcoded `mergeStateStatus=BLOCKED` bail detail (ship.py:758) so the operator message reports the real observed state instead of asserting BLOCKED. Do NOT change retry/cap constants (`MERGE_PR_INITIAL_UNKNOWN_RETRIES`) and do NOT add a new CI-wait cap.
- **Source**: user (recommended default applied on non-response, per terse-answer rule)

## Decision 2: No new CI-wait cap needed
- **Question**: Does the review-required + admin-fallback re-loop need a dedicated CI-wait cap to avoid waiting on genuinely stuck CI?
- **Resolution**: No. The existing `_CiNotReadyGuard` + `SHIP_MERGE_CI_NOT_READY_STALL_THRESHOLD` in `_handle_merge_ci_not_ready` (ship_merge.py:76-119) already bounds the wait; the guard resets when the CI-not-ready detail changes, so a progressing CI is never stalled and a genuinely-stuck one stalls after threshold. Re-looping through this helper inherits that bound.
- **Source**: codebase

## Decision 3: Preserve `--no-admin-fallback` behavior (hard constraint)
- **Question**: Should the early review-required bail be preserved for `--no-admin-fallback` runs?
- **Resolution**: Yes. When `no_admin_fallback` is set, the required review genuinely blocks merge (no admin bypass), so the instant review-required bail on CI_NOT_READY stays correct and must be preserved. The fix only changes the admin-fallback-enabled (default `--merge`) path.
- **Source**: codebase / issue

## Decision 4: Regression-safety constraints (hard constraint)
- **Question**: What prior behavior must not regress?
- **Resolution**: Must not regress #3956 (admin-retry intent on REVIEW_REQUIRED for `--merge` runs), #3891 (wait-and-check for in-progress CI), or #4256 (merge-conflict-signal carve-out in `_maybe_review_required`). Re-looping on CI_NOT_READY regardless of reviewDecision (admin path) must stay bounded by `ci_not_ready_guard` to avoid a spurious-retry stall.
- **Source**: codebase / issue
