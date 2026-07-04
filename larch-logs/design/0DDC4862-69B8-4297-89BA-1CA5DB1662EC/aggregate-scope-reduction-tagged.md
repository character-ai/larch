### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/review/review_and_fix.py:1076-1099
- **Concern**: [SCOPE-REDUCTION] Self-review synthetic JSONL rows omit the existing `SELF_REVIEW_*` id contract from `self_review_tally.py`. Scenario: The plan emits `phase: code-review` rows with only `outcome`, but `difficulty_calibration._parse_jsonl_source` drops rows without `finding_id`/`id` as malformed. A tolerated tally failure with nonzero self-review counts would still fix the summary ratio yet regress calibration from `accepted_count=0` (today's empty file) to `accepted_count=None`, and audit rows would not match the established `SELF_REVIEW_ACCEPTED_n` / `SELF_REVIEW_REJECTED_n` shape.
- **Proposed resolution**: Build the JSONL from `self_review_tally_items({"mode":"self-review","accepted_count":…,"rejected_count":…})`, emitting one row per item with those ids, `phase: code-review`, `outcome`, and `round_num: "1"` before the `run-log write` subprocess.

### FINDING_5:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/review/batch_report.py:324-338
- **Concern**: [SCOPE-REDUCTION] Success cleanup can erase the required tally-failure trace. Scenario: A first Step 5 flush can fail and write code-review-tally.flush.err plus a Warnings entry, then a later flush in the same run can succeed and unlink the run-root sidecar. The committed warning then points at a missing file, losing the rc, stderr, and stdout the issue requires for root-cause capture.
- **Proposed resolution**: Do not unlink the run-root code-review-tally.flush.err on success. At most unlink the tmpdir-only sidecar, and adjust the stale-sidecar test to preserve committed failure evidence.
