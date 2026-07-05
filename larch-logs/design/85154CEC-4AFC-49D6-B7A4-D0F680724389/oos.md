### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/issue/audit_runs.py:237-274
- **Concern**: [SCOPE-REDUCTION] Drop the optional `_manifest_bail_signal` rewrite from the plan. Scenario: Finding 2 is already fixed by adding `pr: int = 0` to `implement_step8_reachable`, passing `pr` into its `_manifest_bail_signal` calls, passing `pr` from `_guideline_ship_outcome_scan_obj` and `_scan_required` step8, and forwarding the same `pr` in `implement_step9a1_reachable(..., chain=True)`. The plan’s “if needed” bullet to treat a positive CLI `pr` as standalone PR evidence would change `manifest_pr_evidence_matches` semantics and can regress `test_scan_required_bail_and_step9a1_gating`, which expects `--pr 7` without manifest `pr_number` to keep bail skip.
- **Proposed resolution**: Delete the “If needed … make `_manifest_bail_signal` treat a positive CLI `pr` as PR evidence” bullet. Keep `_manifest_bail_signal` unchanged; only thread `pr` through `implement_step8_reachable` and its call sites.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### OOS_1: [OUT_OF_SCOPE] Thread manifest `pr_number` into fluff-analysis `implement_step8_reachable` calls
- **Description**: [OUT_OF_SCOPE] Thread manifest `pr_number` into fluff-analysis `implement_step8_reachable` calls. Scenario: Issue scope Finding 2 names fluff-analysis as a consumer of `implement_step8_reachable`. The plan fixes audit scan and required-file paths only, so fluff-analysis coverage can still mark post-PR bail runs as step8-unreachable and undercount missing guideline outcomes.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/fluff-analysis/scripts/fluff-analysis.py:779
- **Phase**: design

Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted

