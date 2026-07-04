### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/tests/review/test_plan_review.py:2940-3012
- **Concern**: Round-2 escalation continuation tests still expect a third review round after cap flattening. Scenario: With HARD ceiling 2, `plan_review_continuation` only enters the escalation branch when `review_count < plan_review_round_cap("HARD")`. At `review-round-count.txt == 2`, that predicate is false, so `PLAN_REVIEW_CONTINUE` becomes false with `PLAN_REVIEW_CONTINUE_REASON=cap-reached`, not true with `escalated-high-accepted`. Updating only `REVIEW_ROUND_CAP=3` to `2` leaves these tests red.
- **Proposed resolution**: Rewrite `test_continuation_escalates_on_cumulative_hi<REDACTED-TOKEN>` and `test_continuation_continues_when_a_new_finding_appears` round-2 expectations to `PLAN_REVIEW_CONTINUE=false`, `PLAN_REVIEW_CONTINUE_REASON=cap-reached`, and `REVIEW_ROUND_CAP=2`; keep round-1 continue assertions unchanged.

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-step3-review-cap.sh:336-374
- **Concern**: Continuation harness still treats escalation at round 2 as unlocking another review round. Scenario: The `continuation helper escalates two new high findings to HARD` block asserts `PLAN_REVIEW_CONTINUE=true`, `REVIEW_ROUND_CAP=3`, and `round_cap == 3` on disk. After universal cap 2, the same inputs at count 2 should stop with `cap-reached`, not continue. Plan covers inverting the driver round-3 case but not this continuation block.
- **Proposed resolution**: Change the escalation continuation case to expect `PLAN_REVIEW_CONTINUE=false`, `PLAN_REVIEW_CONTINUE_REASON=cap-reached`, `REVIEW_ROUND_CAP=2`, and `append_escalation` writing `round_cap: 2`; update `test-step3-review-cap.md` to match.

### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/tests/calibration/test_difficulty.py:208-247
- **Concern**: Blanket `round_cap: 3` → `2` test edits conflict with the read-only clamp contract. Scenario: `test_write_record_merge_preserves_resolution_fields` intentionally proves `_merge_existing_record_fields` preserves persisted resolution fields, including `round_cap: 3`, on disk. The plan edge case says stale caps are clamped on read without rewriting the record, but the testing strategy says to update all `round_cap: 3` fixtures to `2`.
- **Proposed resolution**: A split the test update: keep merge-on-disk assertions at `round_cap: 3` (or add a comment that disk may stay stale), and add a separate `resolve_panel_tier` / `_resolution_from_data` test proving a stored `round_cap: 3` resolves to `2` at runtime.

### FINDING_4:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/references/plan-review.md:215
- **Concern**: Stale round-3 pruning prose survives a cap-2 world. Scenario: The tiered panel section still says HARD uses cap 3 and that `round-3 pruning uses the prior rounds ledger`. With no third review round, that pruning rule and cap-3 wording mislead operators and Gate B/C readers even after runtime caps flatten.
- **Proposed resolution**: When rewriting `plan-review.md`, change HARD to cap 2 and delete or reword the `round-3 pruning` sentence so pruning is described only for round 2 under a universal cap of 2.

### FINDING_5:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/report/progress_report.py:1717-1727; python/larch/report/run_log_flush.py:508-523
- **Concern**: Stale persisted round_cap 3 still survives report and flush paths outside the planned _resolution_from_data clamp. Scenario: An old HARD difficulty-rating.json with round_cap 3 can still produce round-meta ceiling_in_effect=3/round_cap=3, and _refresh_difficulty_record can rewrite the stale cap into the committed difficulty-rating batch. That leaves the old cap alive for already-resolved run artifacts, contrary to the plan’s persisted-record requirement.
- **Proposed resolution**: Add firm updates for these paths. Clamp any stored int cap to min(stored, difficulty.tier_ceiling(panel_tier)) or reuse one central normalization helper, and update python/tests/report/test_progress_report.py and python/tests/report/test_run_log_flush.py to expect 2.

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/tests/calibration/test_difficulty.py
- **Concern**: The testing strategy conflates on-disk preservation with resolved round cap. `test_write_record_merge_preserves_resolution_fields` seeds `round_cap: 3` and asserts the merged file still has `round_cap: 3`, matching `_merge_existing_record_fields` preserving persisted resolution fields. The edge cases say clamp on read without rewriting stale records. A blanket update of every `round_cap: 3` assertion to `2` breaks that contract or forces an unplanned merge-time rewrite.. Scenario: An implementer following the plan literally rewrites the merge test to expect `data["round_cap"] == 2`, which either drops regression coverage for stale on-disk caps or pushes clamp logic into merge/write and contradicts the read-only clamp design.
- **Proposed resolution**: Split the test work: keep merge preservation asserting on-disk `round_cap: 3` survives `write-record`; add or extend a resolution test that loads the same fixture and asserts `resolve_panel_tier(...).round_cap == 2` (and `tier_ceiling(HARD) == 2`). Update only assertions that truly track runtime cap emission, not disk preservation.

### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-step3-review-cap.sh:336-374
- **Concern**: The continuation-escalates-high harness case still seeds review_count=2 and expects PLAN_REVIEW_CONTINUE=true with REVIEW_ROUND_CAP=3 and round_cap=3 on disk.. Scenario: After universal cap 2, plan_review_loop only enters the escalated-high-accepted branch when review_count < plan_review_round_cap(HARD); at count 2 that is false, so the helper returns cap-reached instead. make test-step3-review-cap stays red if only the HARD round-3-reachable block is inverted.
- **Proposed resolution**: Rewrite this case explicitly: seed review_count=1, expect escalation to HARD with REVIEW_ROUND_CAP=2 and persisted round_cap=2, or expect cap-reached when count already equals 2. Name this subsection in the plan’s test-step3-review-cap.sh update bullet.

### FINDING_8:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/tests/review/test_plan_review.py:2954-3010, skills/design/scripts/test-step3-review-cap.sh:336-374
- **Concern**: Escalation continuation fixtures still seed review_count=2 and expect continue=true with a raised cap. Scenario: After a universal cap of 2, plan_review continuation treats review_count=2 as cap-reached before the escalation branch runs (review_count < plan_review_round_cap("HARD") is false when both are 2). Updating only REVIEW_ROUND_CAP=3 to =2 leaves PLAN_REVIEW_CONTINUE=true assertions failing in test_plan_review.py and the step3 cap harness
- **Proposed resolution**: Restructure those escalation cases: seed review_count=1 when the test still needs continue=true after escalation to HARD, assert REVIEW_ROUND_CAP=2, and keep a separate review_count=2 case that expects PLAN_REVIEW_CONTINUE=false with cap-reached; document that split in both test file rows

### FINDING_9:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/tests/report/test_run_log_flush.py:33-57
- **Concern**: Run-log refresh merge harness still expects a preserved HARD cap of 3. Scenario: The plan requires persisted merge behavior to stop carrying old round_cap:3 records. Clamping the shared merge/write path will make this full pytest shard fail; not clamping it leaves the persisted-record requirement unmet.
- **Proposed resolution**: Add this report test to the firm test updates, expect cap 2, and clamp preserved round_cap values in the shared difficulty merge/write path.
