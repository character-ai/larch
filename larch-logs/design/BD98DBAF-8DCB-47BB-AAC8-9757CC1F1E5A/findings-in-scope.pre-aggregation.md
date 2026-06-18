### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: Makefile:501-502
- **Concern**: Item 2 adds test_embedded_plan_review_loop_not_substantive_count_emitted but make test-plan-review-loop still runs pytest with -k 'loop_dedup or migrated_collector' only. Scenario: make lint shard 10 never executes the new NOT_SUBSTANTIVE count pins; a regression in the embedded plan-review-loop body can pass CI while Item 2 appears done
- **Proposed resolution**: Extend the Makefile test-plan-review-loop -k expression (or add a dedicated harness target) so the new test runs in the lint shard that owns plan-review-loop coverage

### FINDING_1:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: correctness
- **Location**: python/test_plan_review.py:28-36
- **Concern**: Item 2 requires an exact embedded-body substring COLLECT_FAILURE_COUNT=0 but no tracked source (only the gzipped legacy asset) contains that literal today; the loop likely initializes a lowercase bash counter and emits uppercase KVs only when writing round-summary.env. Scenario: Implementer adds test_embedded_plan_review_loop_not_substantive_count_emitted with assert "COLLECT_FAILURE_COUNT=0" in body; pytest fails even though NOT_SUBSTANTIVE counting works at runtime
- **Proposed resolution**: Decode plan-review-loop.sh via plan_review.legacy_asset_bytes before pinning; assert collect_failure_count=0 init and/or a round-summary writer emit line containing COLLECT_FAILURE_COUNT=, not the exact COLLECT_FAILURE_COUNT=0 assignment unless that literal is present

### FINDING_1:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-research-structure.sh:247-259
- **Concern**: Plan drops the Item 1 FINDING_3 pin. Scenario: The cleanup leaves one named issue-scope requirement unimplemented, so that contract remains unpinned after the PR
- **Proposed resolution**: Do not drop Check 15 outright. Add the minimal assertion for the intended FINDING_3 contract, or revise the scope before implementation if that sub-item is proven stale

### FINDING_2:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: code-quality
- **Location**: python/test_plan_review.py:31-47
- **Concern**: [SCOPE-REDUCTION] Proposed NOT_SUBSTANTIVE regional assertion is over-specific. Scenario: The embedded _count_collector_evidence helper counts wildcard non-OK statuses and does not contain NOT_SUBSTANTIVE, so the proposed test either fails or forces unrelated embedded-asset churn
- **Proposed resolution**: Keep the existing NOT_SUBSTANTIVE body pin. In the regional test, assert the non-OK increment path and the _write_round_summary COLLECT_FAILURE_COUNT emit only

