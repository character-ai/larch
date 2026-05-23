### OOS_1: [OUT_OF_SCOPE] New scripts/test-launch-claude-ci.sh harness wiring not in plan

- **Severity**: nit
- **Focus area**: risk-integration
- **Location**: Makefile:43-73,412-434
- **Description**: New scripts/test-launch-claude-ci.sh harness wiring not in plan
- **Scenario**: Merged code can pass local bash but miss CI make lint harness registration
- **Suggested fix**: Add Makefile target and attach to an existing test-harnesses-* shard like test-launch-cursor-ci
- **Reviewer**: Cursor-Edge


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_2: [OUT_OF_SCOPE] run_ci_fix_vendor remains cursor-or-codex with three launch attempts; no Claude

- **Severity**: latent
- **Focus area**: architecture
- **Location**: scripts/ship-pr.sh:1225-1361
- **Description**: run_ci_fix_vendor remains cursor-or-codex with three launch attempts; no Claude tier in evaluate-failure loop
- **Scenario**: Inconsistent recovery depth between CI-eval path and new stall waterfalls
- **Suggested fix**: Track follow-up to add third tier or document intentional asymmetry
- **Reviewer**: Cursor-Innovation

Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

