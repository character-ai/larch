## Goal
Implement issue #5062: [IMPLEMENTING] [OOS] Aggregated rollup of 3 capped OOS items.

## Implementation Plan
## Out-of-Scope Observation

**Surfaced by**: Combined: capped per-run rollup
**Phase**: implement
**Vote tally**: N/A — capped rollup of 3 entries

## Description

Cap 1 (OOS_ISSUES_PER_RUN_CAP) exceeded; the following 3 items were rolled up by the per-run OOS issue cap:
  - **Issue evidence cites drafter launchers (launch_codex_drafter ~3036, launch_claude_drafter ~3190) but the plan never states they are deferred**: Issue evidence cites drafter launchers (launch_codex_drafter ~3036, launch_claude_drafter ~3190) but the plan never states they are deferred. Scenario: ~20+ canonical output.with_suffix(...) sites in… [Files: CI/implement/review]
  - **Drafter launchers still construct canonical output-rooted sidecars via inline with_suffix but are absent from the migration list**: Drafter launchers still construct canonical output-rooted sidecars via inline with_suffix but are absent from the migration list. Scenario: The issue cites drafter duplication as evidence (~3077, 311…
  - **[OUT_OF_SCOPE] Drafter stale-cleanup paths not in LauncherPaths migration scope**: [OUT_OF_SCOPE] Drafter stale-cleanup paths not in LauncherPaths migration scope. Scenario: Issue evidence cites drafter launcher duplication (:3035, :3189), but the plan never names launch_codex_draf…

---
*This issue was automatically created by the larch `/implement` workflow from an out-of-scope observation surfaced during the workflow.*

## Test plan
(no test plan section in plan-file)
