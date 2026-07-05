### OOS_1: [OUT_OF_SCOPE] Thread manifest `pr_number` into fluff-analysis `implement_step8_reachable` calls
- **Description**: [OUT_OF_SCOPE] Thread manifest `pr_number` into fluff-analysis `implement_step8_reachable` calls. Scenario: Issue scope Finding 2 names fluff-analysis as a consumer of `implement_step8_reachable`. The plan fixes audit scan and required-file paths only, so fluff-analysis coverage can still mark post-PR bail runs as step8-unreachable and undercount missing guideline outcomes.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/fluff-analysis/scripts/fluff-analysis.py:779
- **Phase**: design

Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted

