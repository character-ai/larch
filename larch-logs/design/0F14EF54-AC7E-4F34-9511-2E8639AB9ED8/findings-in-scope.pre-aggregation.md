### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/plan_review.py:880-945
- **Concern**: Embedded plan-review-loop still invokes deleted aggregate-findings.sh; plan only retargets prune-nit. Scenario: G2 deletes python/legacy_review_shell/aggregate-findings.sh while C3a1 still runs gzip-embedded plan-review-loop.sh via _run_legacy; that loop calls optional aggregate-findings.sh (LARCH_AGGREGATOR_DISABLED) per live /design runs (AGGREGATOR_STATUS in round-summary.env). After deletion materialized python/legacy_review_shell lacks the script and aggregation fails or is skipped incorrectly.
- **Proposed resolution**: Extend _decode_legacy_asset / _rewrite_prune_asset (same argv-array + LARCH_PLAN_REVIEW_AGGREGATE_SH override pattern as prune-nit and #4417 collector) to default PLAN_REVIEW_AGGREGATE_CLI=(python3 "$PLUGIN_ROOT/python/cli.py" review aggregate-findings) and invoke "${PLAN_REVIEW_AGGREGATE_CLI[@]}" with --input-mode plan. Add test_embedded_plan_review_aggregate_uses_review_cli mirroring test_embedded_plan_review_loop_uses_migrated_collector.

### FINDING_2:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: blocking
- **Focus area**: risk-integration
- **Location**: python/plan_review.py:880-946
- **Concern**: The plan retargets embedded plan-review prune-nit via `_rewrite_prune_asset` but does not retarget embedded plan-review aggregate when `python/legacy_review_shell/aggregate-findings.sh` is deleted. Scenario: G2 deletes the aggregate shell while `run_plan_review_round` still executes gzip-embedded `plan-review-loop.sh` (`python/plan_review.py:1236-1237`). That loop still depends on the retired shell path (same class of consumer as collector migration fixed in `test_embedded_plan_review_loop_uses_migrated_collector`). Prune-only rewrite leaves plan-mode aggregation calling a missing script: rc 127, unmerged findings, wrong ballots/tally
- **Proposed resolution**: Extend `_decode_legacy_asset` with the same argv-array + override pattern used for prune and `DISPATCH_WATERFALL_CMD`: `PLAN_REVIEW_AGGREGATE_CLI=(python3 "$PLUGIN_ROOT/python/cli.py" review aggregate-findings)` with `LARCH_PLAN_REVIEW_AGGREGATE_SH` override; preserve `--input-mode plan` and `--allow-findings-outside-tmpdir true`. Add `test_embedded_plan_review_aggregate_uses_review_cli` mirroring the prune and collector embedded tests

