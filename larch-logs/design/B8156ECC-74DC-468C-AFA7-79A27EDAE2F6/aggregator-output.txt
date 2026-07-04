### FINDING_1: Update continuation tests for the universal cap-2 branch
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: The continuation/escalation tests still assume a third review round after HARD is flattened to a cap of 2. At `review_count == 2`, the escalation branch no longer runs, so these cases should either expect `cap-reached` or seed `review_count=1` for the continue-true path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Rewrite `test_continuation_escalates_on_cumulative_hi<REDACTED-TOKEN>` and `test_continuation_continues_when_a_new_finding_appears` round-2 expectations to `PLAN_REVIEW_CONTINUE=false`, `PLAN_REVIEW_CONTINUE_REASON=cap-reached`, and `REVIEW_ROUND_CAP=2`; keep round-1 continue assertions unchanged.
  - From Cursor-Arch: Change the escalation continuation case to expect `PLAN_REVIEW_CONTINUE=false`, `PLAN_REVIEW_CONTINUE_REASON=cap-reached`, `REVIEW_ROUND_CAP=2`, and `append_escalation` writing `round_cap: 2`; update `test-step3-review-cap.md` to match.
  - From Cursor-Pragmatic: Rewrite this case explicitly: seed review_count=1, expect escalation to HARD with REVIEW_ROUND_CAP=2 and persisted round_cap=2, or expect cap-reached when count already equals 2. Name this subsection in the plan’s test-step3-review-cap.sh update bullet.
  - From Cursor-Requirements: Restructure those escalation cases: seed review_count=1 when the test still needs continue=true after escalation to HARD, assert REVIEW_ROUND_CAP=2, and keep a separate review_count=2 case that expects PLAN_REVIEW_CONTINUE=false with cap-reached; document that split in both test file rows

### FINDING_2: Separate persisted round_cap preservation from runtime clamping in difficulty tests
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: important
- **Concern**: The difficulty calibration tests mix two different contracts: on-disk merge preservation must keep stale `round_cap: 3`, while runtime resolution should clamp to 2. Rewriting every `round_cap: 3` expectation to `2` would erase regression coverage for stale persisted records.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: A split the test update: keep merge-on-disk assertions at `round_cap: 3` (or add a comment that disk may stay stale), and add a separate `resolve_panel_tier` / `_resolution_from_data` test proving a stored `round_cap: 3` resolves to `2` at runtime.
  - From Cursor-Innovation: Split the test work: keep merge preservation asserting on-disk `round_cap: 3` survives `write-record`; add or extend a resolution test that loads the same fixture and asserts `resolve_panel_tier(...).round_cap == 2` (and `tier_ceiling(HARD) == 2`). Update only assertions that truly track runtime cap emission, not disk preservation.

### FINDING_3: Refresh stale plan-review prose for the cap-2 world
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The tiered plan-review documentation still describes HARD as cap 3 and references round-3 pruning. That prose is stale once all tiers are capped at 2 and will mislead operators and readers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: When rewriting `plan-review.md`, change HARD to cap 2 and delete or reword the `round-3 pruning` sentence so pruning is described only for round 2 under a universal cap of 2.

### FINDING_4: Clamp stale persisted caps in report and flush paths too
- **Reviewer(s)**: Codex-Arch, Codex-Requirements
- **Severity**: important
- **Concern**: The report/flush merge path can still carry `round_cap: 3` into persisted report artifacts and refresh batches. That leaves stale caps alive outside the planned read-time clamp behavior, so the shared normalization path still needs to be updated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add firm updates for these paths. Clamp any stored int cap to min(stored, difficulty.tier_ceiling(panel_tier)) or reuse one central normalization helper, and update python/tests/report/test_progress_report.py and python/tests/report/test_run_log_flush.py to expect 2.
  - From Codex-Requirements: Add this report test to the firm test updates, expect cap 2, and clamp preserved round_cap values in the shared difficulty merge/write path.
