### FINDING_1: Self-review synthetic rows need stable calibration IDs
- **Reviewer(s)**: Codex-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: Self-review synthetic JSONL rows are underspecified against the run-log record contract: they can satisfy the plan with phase/outcome-only rows, but that shape no longer satisfies the documented v2 review-findings-full schema. Because `difficulty_calibration` drops rows without a stable identity field, the self-review accepted-count fallback becomes unrecoverable even when the final-report tally fallback can still count the rows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: `Require each synthetic self-review row to be a minimal v2 review-findings-full record with a stable id plus schema_version, issue_number, reviewer_slots, round_num, category, and prose_body, while keeping one row per accepted or rejected outcome.`
  - From Cursor-Pragmatic: `In \`write_self_review_tally\`, emit one row per accepted/rejected finding with \`phase: code-review\`, the matching \`outcome\`, \`round_num: 1\`, and a unique \`id\` (for example \`SELF_REVIEW_A1\` / \`SELF_REVIEW_R1\`). Pin the shape in \`test_write_self_review_tally_nonzero_counts\` or a small calibration test.`


### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/review/review_and_fix.py:1076-1099
- **Concern**: [SCOPE-REDUCTION] Self-review synthetic JSONL rows omit the existing `SELF_REVIEW_*` id contract from `self_review_tally.py`. Scenario: The plan emits `phase: code-review` rows with only `outcome`, but `difficulty_calibration._parse_jsonl_source` drops rows without `finding_id`/`id` as malformed. A tolerated tally failure with nonzero self-review counts would still fix the summary ratio yet regress calibration from `accepted_count=0` (today's empty file) to `accepted_count=None`, and audit rows would not match the established `SELF_REVIEW_ACCEPTED_n` / `SELF_REVIEW_REJECTED_n` shape.
- **Proposed resolution**: Build the JSONL from `self_review_tally_items({"mode":"self-review","accepted_count":…,"rejected_count":…})`, emitting one row per item with those ids, `phase: code-review`, `outcome`, and `round_num: "1"` before the `run-log write` subprocess.


