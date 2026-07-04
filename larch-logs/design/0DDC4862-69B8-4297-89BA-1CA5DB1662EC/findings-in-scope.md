### FINDING_1: Self-review synthetic rows need stable calibration IDs
- **Reviewer(s)**: Codex-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: Self-review synthetic JSONL rows are underspecified against the run-log record contract: they can satisfy the plan with phase/outcome-only rows, but that shape no longer satisfies the documented v2 review-findings-full schema. Because `difficulty_calibration` drops rows without a stable identity field, the self-review accepted-count fallback becomes unrecoverable even when the final-report tally fallback can still count the rows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: `Require each synthetic self-review row to be a minimal v2 review-findings-full record with a stable id plus schema_version, issue_number, reviewer_slots, round_num, category, and prose_body, while keeping one row per accepted or rejected outcome.`
  - From Cursor-Pragmatic: `In \`write_self_review_tally\`, emit one row per accepted/rejected finding with \`phase: code-review\`, the matching \`outcome\`, \`round_num: 1\`, and a unique \`id\` (for example \`SELF_REVIEW_A1\` / \`SELF_REVIEW_R1\`). Pin the shape in \`test_write_self_review_tally_nonzero_counts\` or a small calibration test.`

### FINDING_2: Successful tally cleanup should fail open on unlink errors
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Concern**: The successful-tally cleanup path is not fail-open: after a later successful tally write, it removes stale `code-review-tally.flush.err` sidecars but suppresses only `FileNotFoundError`. If the stale sidecar hits a permissions or filesystem unlink error, cleanup can raise after `write-tally` already succeeded, turning observability cleanup into a Step 5 failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: `Suppress OSError for both tmpdir and run-root sidecar unlink attempts inside the helper, matching the fail-open sidecar write and Warnings append behavior.`

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/review/review_and_fix.py:1076-1099
- **Concern**: [SCOPE-REDUCTION] Self-review synthetic JSONL rows omit the existing `SELF_REVIEW_*` id contract from `self_review_tally.py`. Scenario: The plan emits `phase: code-review` rows with only `outcome`, but `difficulty_calibration._parse_jsonl_source` drops rows without `finding_id`/`id` as malformed. A tolerated tally failure with nonzero self-review counts would still fix the summary ratio yet regress calibration from `accepted_count=0` (today's empty file) to `accepted_count=None`, and audit rows would not match the established `SELF_REVIEW_ACCEPTED_n` / `SELF_REVIEW_REJECTED_n` shape.
- **Proposed resolution**: Build the JSONL from `self_review_tally_items({"mode":"self-review","accepted_count":…,"rejected_count":…})`, emitting one row per item with those ids, `phase: code-review`, `outcome`, and `round_num: "1"` before the `run-log write` subprocess.

### FINDING_4:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/review/batch_report.py:324-338
- **Concern**: [SCOPE-REDUCTION] Success cleanup can erase the required tally-failure trace. Scenario: A first Step 5 flush can fail and write code-review-tally.flush.err plus a Warnings entry, then a later flush in the same run can succeed and unlink the run-root sidecar. The committed warning then points at a missing file, losing the rc, stderr, and stdout the issue requires for root-cause capture.
- **Proposed resolution**: Do not unlink the run-root code-review-tally.flush.err on success. At most unlink the tmpdir-only sidecar, and adjust the stale-sidecar test to preserve committed failure evidence.
