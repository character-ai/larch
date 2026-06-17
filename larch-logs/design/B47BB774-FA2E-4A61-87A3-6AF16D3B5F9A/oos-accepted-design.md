### OOS_1:
- **Description**: Primary >50% NOT_SUBSTANTIVE/ERROR threshold is unchanged. Scenario: An all-OOS round where most static slots are NOT_SUBSTANTIVE in collector/output accounting can still set THRESHOLD_OK=false before the secondary gate; this plan would not unblock that path
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: correctness
- **Location**: python/legacy_review_shell/check-reviewer-failure-threshold.sh:245-252
- **Phase**: design
- **Filed URL**: https://github.com/character-ai/larch/issues/4652
### OOS_1:
- **Description**: Primary >50% NOT_SUBSTANTIVE threshold unchanged. Scenario: All-static-NOT_SUBSTANTIVE panels may still panel-fail despite parseable OOS output
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/legacy_review_shell/check-reviewer-failure-threshold.sh:245-251
- **Phase**: design

### OOS_1:
- **Description**: Bypass does not address external outputs skipped when collector marks slots non-OK. Scenario: When agent collect-results drops or marks every external slot NOT_SUBSTANTIVE/ERROR, collect-findings skips those files, findings.md can stay empty, collector_success_count stays 0, and the new bypass never fires even though reviewers completed
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/legacy_review_shell/collect-findings.sh:461-464
- **Phase**: design

### OOS_1:
- **Description**: The new regression inherits `LARCH_AGGREGATOR_DISABLED=1` from `build_review_core_env`, so it never exercises the production `aggregate_reason=ok && MERGED_COUNT=0` branch at `review-core.sh:1037-1040`.. Scenario: With aggregator enabled, an all-OOS round that legitimately merges to zero in-scope blocks could still route to `emit_zero_findings_branch` after bypass, reproducing a stall/mis-route the test would not catch.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: correctness
- **Location**: python/test_review_pipeline.py:406-421
- **Phase**: design

