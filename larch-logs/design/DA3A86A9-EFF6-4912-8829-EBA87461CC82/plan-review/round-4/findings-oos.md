### OOS_1:
- **Description**: Plan conditionally adds a run-step3-review.sh routing assertion but does not list this script under Files to modify. Scenario: Cap breadcrumb emit still says continuing to Step 3b, Step 4, then Gate C without naming the completion boundary; a strict assertion would fail or force an out-of-scope script edit unrelated to orchestrator routing
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/run-step3-review.sh:167
- **Phase**: design

