### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/review/review_and_fix.py:1076-1099
- **Concern**: [SCOPE-REDUCTION] Self-review synthetic JSONL rows omit the existing `SELF_REVIEW_*` id contract from `self_review_tally.py`. Scenario: The plan emits `phase: code-review` rows with only `outcome`, but `difficulty_calibration._parse_jsonl_source` drops rows without `finding_id`/`id` as malformed. A tolerated tally failure with nonzero self-review counts would still fix the summary ratio yet regress calibration from `accepted_count=0` (today's empty file) to `accepted_count=None`, and audit rows would not match the established `SELF_REVIEW_ACCEPTED_n` / `SELF_REVIEW_REJECTED_n` shape.
- **Proposed resolution**: Build the JSONL from `self_review_tally_items({"mode":"self-review","accepted_count":…,"rejected_count":…})`, emitting one row per item with those ids, `phase: code-review`, `outcome`, and `round_num: "1"` before the `run-log write` subprocess.



### FINDING_2:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/review/review_and_fix.py:1076-1100; docs/run-logs.md:417-423; python/larch/calibration/difficulty_calibration.py:391-416
- **Concern**: Self-review synthetic JSONL rows are underspecified against the run-log record contract. Scenario: An implementation can satisfy the plan with phase/outcome-only rows. Final-report fallback counts them, but committed review-findings-full.jsonl records no longer satisfy the documented v2 shape, and difficulty_calibration drops rows without an id, so self-review accepted counts stay unrecoverable for that fallback.
- **Proposed resolution**: Require each synthetic self-review row to be a minimal v2 review-findings-full record with a stable id plus schema_version, issue_number, reviewer_slots, round_num, category, and prose_body, while keeping one row per accepted or rejected outcome.



### FINDING_3:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/review/batch_report.py:324-373
- **Concern**: Successful tally cleanup is not fail-open. Scenario: The plan removes stale code-review-tally.flush.err files on a later successful tally write but suppresses only FileNotFoundError. A stale sidecar with a permissions or filesystem unlink error can raise after write-tally succeeds, turning observability cleanup into a Step 5 failure.
- **Proposed resolution**: Suppress OSError for both tmpdir and run-root sidecar unlink attempts inside the helper, matching the fail-open sidecar write and Warnings append behavior.



### FINDING_4:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/review/review_and_fix.py
- **Concern**: Self-review synthetic JSONL rows omit required identity fields for calibration. Scenario: When `code-review-tally.json` is missing, self-review runs rely on `review-findings-full.jsonl` as the classification source because they usually have no `round-*/findings-classification.tsv`. The plan emits only `phase` and `outcome`, but `difficulty_calibration._parse_jsonl_source` skips rows without `finding_id`/`id`/`finding_hash` as malformed. Final-report fallback can show real counts while #5993 calibration still records `accepted_count=None` for the same run.
- **Proposed resolution**: In `write_self_review_tally`, emit one row per accepted/rejected finding with `phase: code-review`, the matching `outcome`, `round_num: 1`, and a unique `id` (for example `SELF_REVIEW_A1` / `SELF_REVIEW_R1`). Pin the shape in `test_write_self_review_tally_nonzero_counts` or a small calibration test. ## Findings ### 1. [correctness] Self-review synthetic JSONL rows omit calibration identity fields **Location:** `python/larch/review/review_and_fix.py` (planned self-review emission) The plan correctly adds `phase: code-review` rows so `_derive_code_review_tally` and the final-report fallback can recover accepted/rejected ratios when the tally file is absent. That fixes the visible `Code review: N/A` regression. The issue scope also requires restoring the calibration accepted-count fallback (#5992 / #5993). Self-review runs normally have no `round-*/findings-classification.tsv`, so calibration falls through to run-root `review-findings-full.jsonl`. `_parse_jsonl_source` in `python/larch/calibration/difficulty_calibration.py` requires a non-empty `id` (or `finding_id` / `finding_hash`) on each row; rows with only `phase` and `outcome` are counted as malformed and dropped. **Suggested revision:** Extend the self-review emission spec so each synthetic row includes at least `id`, `phase`, `outcome`, and `round_num: 1`, mirroring the minimal shape used in `python/tests/calibration/test_difficulty_calibration.py` (`test_gc_slimmed_implement_recovers_root_jsonl_and_review_recovers_ndjson`). --- Prior-round items on duplicate warnings, fail-open append, run-root sidecar creation, shared counting core, preserved `_derive_code_review_tally` 2-tuple, self-review row counts, and test updates appear addressed in the current plan. No additional in-scope gaps found beyond finding 1.



### FINDING_5:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/review/batch_report.py:324-338
- **Concern**: [SCOPE-REDUCTION] Success cleanup can erase the required tally-failure trace. Scenario: A first Step 5 flush can fail and write code-review-tally.flush.err plus a Warnings entry, then a later flush in the same run can succeed and unlink the run-root sidecar. The committed warning then points at a missing file, losing the rc, stderr, and stdout the issue requires for root-cause capture.
- **Proposed resolution**: Do not unlink the run-root code-review-tally.flush.err on success. At most unlink the tmpdir-only sidecar, and adjust the stale-sidecar test to preserve committed failure evidence.



