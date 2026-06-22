## Goal
Implement issue #5018: [IMPLEMENTING] [OOS] [OUT_OF_SCOPE] Capped aggregate retry evidence can retain only the first source stable ID.

## Implementation Plan
## Out-of-Scope Observation

**Surfaced by**: Cursor-Pragmatic Phase2
**Phase**: design
**Vote tally**: accepted-OOS

## Description

[OUT_OF_SCOPE] Capped aggregate retry evidence can retain only the first source stable ID (`python/oos_filer.py:786-806`; severity: latent; focus: risk-integration).

Scenario: When `issue_cap` rewrites seven accepted blocks into one aggregate, `_stable_ids_by_combined_item` is computed from the pre-cap `combined_text`. A retry after filing can match persisted evidence to only the first original block and re-file the rolled-up remainder.

---
*This issue was automatically created by the larch `/design` workflow from an out-of-scope observation surfaced during the workflow.*

## Test plan
(no test plan section in plan-file)
