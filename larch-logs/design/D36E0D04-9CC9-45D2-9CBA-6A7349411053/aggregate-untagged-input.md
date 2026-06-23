### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/plan_review_round.py:235-257
- **Concern**: /design OOS cap slot lookup omits retry-path normalization already used by write_reviewer_status_tsv. Scenario: The plan keys oos_counts_by_slot by manifest slot_name via slot_by_output.get(rf, Path(rf).stem.replace("-output", "")). Collector OK records for waterfall retries use paths like cursor-plan-arch-output-retry.txt (see test_write_reviewer_status_tsv_retry_path_maps_to_done) that are absent from slot_by_output, so the fallback stem becomes cursor-plan-arch-retry instead of manifest slot cursor-plan-arch. That reviewer gets an independent 3-OOS bucket; a retry sidecar with 4+ OOS rows can retain 3 while the logical slot could accept 3 more from another collector record, exceeding the per-reviewer cap the issue targets. Prior round FINDING_5 fix is still incomplete.
- **Proposed resolution**: In _compose_findings_from_collector build slot_by_norm_output from manifest rows with voting.normalize_reviewer_basename(output) -> slot; resolve each REVIEWER_FILE through voting.normalize_reviewer_basename(rf) before cap accounting (mirror write_reviewer_status_tsv #4848). Extend edge cases and failure modes to cover /design retry/phase collector paths, not only /implement label normalization.

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/test_plan_review_round.py
- **Concern**: Planned /design cap tests omit retry-path collector identity regression. Scenario: The new cap test covers overflow OOS plus a trailing in-scope row on canonical output paths only. It does not exercise collector REVIEWER_FILE paths with -retry/-phase2/-phase3 suffixes that _compose_findings_from_collector already receives in production (#4848). An implementation can pass the listed tests while leaving retry-path cap keys on the wrong bucket.
- **Proposed resolution**: Add a unit test modeled on test_write_reviewer_status_tsv_retry_path_maps_to_done: manifest output cursor-plan-arch-output.txt, collector OK on cursor-plan-arch-output-retry.txt with 4 distinct OOS TSV rows plus 1 in-scope row; assert only 3 OOS retained under slot cursor-plan-arch, overflow absent, and the in-scope row kept.

### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/plan_review_round.py:257-313
- **Concern**: /design OOS cap keys `oos_counts_by_slot` from `slot_by_output.get(rf, Path(rf).stem.replace("-output", ""))` without basename normalization. Scenario: Collector OK records often use `-retry`/`-phase2`/`-phase3` paths that are not manifest `output` keys (`test_write_reviewer_status_tsv_retry_path_maps_to_done`). Fallback resolves to stems like `cursor-plan-arch-retry` instead of manifest slot `cursor-plan-arch`. Two OK records for one logical slot can each retain 3 OOS rows (6 total), defeating the per-reviewer cap. `write_reviewer_status_tsv` already joins via `voting.normalize_reviewer_basename`.
- **Proposed resolution**: When building `slot_by_output`, also map `voting.normalize_reviewer_basename(output)` to manifest `slot`. Resolve cap identity with the same norm join before counting. Add a `_compose_findings_from_collector` test with a retry-path OK sidecar (4 OOS + 1 in-scope) asserting only 3 OOS retained for slot `cursor-plan-arch`.
