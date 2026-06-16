### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/pr_body.py:694-735
- **Concern**: Proposed raw ^- bullet counting does not exclude fenced diagnostics. Scenario: Existing run-log append-failure entries include fenced tool output; if that output contains a line like "- failed check", the final report counts it as a second issue instead of one logged failure
- **Proposed resolution**: Use one small shared bullet-count helper that tracks Markdown fences and counts ^- only outside fenced blocks; apply it to execution-issues.md, structured NDJSON bodies, and body_text fallback.

### FINDING_2:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_pr_body.py (planned plan.txt:54-66); python/pr_body.py:724-748
- **Concern**: Missing body_text fallback regression despite accepted all-path bullet counting. Scenario: The plan changes _refresh_issue_counts body_text fallback from bold-only to top-level bullets, but planned tests cover only execution-issues.md and structured dict rows. An implementation can leave the fallback at the old regex and still satisfy the planned tests.
- **Proposed resolution**: Add one focused _refresh_issue_counts test that forces the body_text fallback, for example an NDJSON file with a dict body containing ### Tool Failures and plain - bullets plus a non-dict JSON row so all(dict) is false.

### FINDING_3:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_bootstrap.py (planned plan.txt:116-127); docs/issue-anchored-plan.md:75-78
- **Concern**: Materialization test omits optional size trailers from the real provenance region. Scenario: The wire format inserts review_status and rounds_completed before the final size-trailer block so diff_lines stays last, but the planned fixture includes only provenance lines directly near diff_lines. A helper that strips only adjacent lines before diff_lines can pass while leaving provenance in real plans with diff_added, diff_deleted, or mechanical_churn trailers.
- **Proposed resolution**: Add optional size trailers to the materialization fixture and assert the provenance immediately above them is stripped while those trailers and diff_lines remain.

