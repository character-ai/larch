### OOS_1: [OUT_OF_SCOPE] no-admin-fallback review-required bail still suggests `--admin`
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: The review-required bail text still tells the operator to merge manually with `--admin` even when `working.no_admin_fallback` is enabled, which can mislead users on the no-admin-fallback path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] no-admin-fallback diagnostic read lacks a ShipError regression
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: nit
- **Concern**: There is no regression that exercises `pr_merge_state` raising `ShipError` on the no-admin-fallback review-required bail path, so the operator-facing merge-state detail handling on diagnostic-read failure is not verified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] CI-not-ready stall/race tests still rely on `pr_review_decision`
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: The CI-not-ready stall/race tests still stub `pr_review_decision` to `APPROVED` even though the admin path no longer calls it, so they would not fail if that no-call invariant regressed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.

