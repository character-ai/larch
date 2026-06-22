## Goal
Implement issue #5038: [IMPLEMENTING] [OOS] Aggregated rollup of 3 capped OOS items.

## Implementation Plan
## Out-of-Scope Observation

**Surfaced by**: Combined: capped per-run rollup

**Phase**: implement

**Vote tally**: N/A — capped rollup of 3 entries


## Description

Cap 1 (OOS_ISSUES_PER_RUN_CAP) exceeded; the following 3 items were rolled up by skills/implement/scripts/oos-issue-cap.sh:
  - **[OUT_OF_SCOPE] Inner run-dir escape symlinks not guarded during `rglob`**: OOS_1: [OUT_OF_SCOPE] Inner run-dir escape symlinks not guarded during rglob - Reviewer(s): cursor-specialist-correctness, cursor-specialist-edge-cases - Severity: latent - Concern: Symlinks inside a… [Files: glob/rglob unlink/rmtree.]
  - **[OUT_OF_SCOPE] Contract doc omits bulk-mode containment guard**: OOS_2: [OUT_OF_SCOPE] Contract doc omits bulk-mode containment guard - Reviewer(s): cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing - Severity: nit - Concern: T… [Files: larch-logs/implement]
  - **[OUT_OF_SCOPE] `consolidate_breadcrumbs()` follows nested breadcrumbs symlink outside run dir**: OOS_3: [OUT_OF_SCOPE] consolidate_breadcrumbs() follows nested breadcrumbs symlink outside run dir - Reviewer(s): codex-specialist-testing, dyn-dyn-bulk-symlink-containment-codex - Severity: latent -… [Files: write/delete]

---
*This issue was automatically created by the larch `/implement` workflow from an out-of-scope observation surfaced during the workflow.*

## Test plan
(no test plan section in plan-file)
