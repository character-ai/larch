### OOS_1: [OUT_OF_SCOPE] gate-failure stall envelope drops round metadata
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Gate exceptions from `_step5_post_round_gates` (`python/review_and_fix.py:3001-3005`) still reach the outer `except Exception` and emit `stall_reason=internal-error` with `rounds_completed=0` / `final_round=0`, even when a round completed and timing was recorded. Pre-existing; this diff does not change that handler. `test_step5_fix_applied_post_gate_exception_still_records_round_timing` checks timing and stall status only, not accurate round metadata on gate failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: On gate failure, emit the stall envelope with the current `round_num` and `rounds_completed` before re-raising or returning.
  - From cursor-specialist-testing-output.txt: If accurate round metadata on gate failures matters for run logs, assert `ROUNDS_COMPLETED` in that test and fix the handler separately.

### OOS_2: [OUT_OF_SCOPE] fix-applied timing ignores record_round_timing failures
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `_record_step5_round_timing` (`python/review_and_fix.py:2782-2797`) calls `record_round_timing(...)` and ignores its return code, so ledger write failures can leave Gantt gaps with no Step 5 stall. Pre-existing; not introduced by the inline refactor.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Log or propagate non-zero `record_round_timing` results on the `fix-applied` path.

### OOS_3: [OUT_OF_SCOPE] rc2 one-shot cleanup test lacks assertion
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `test_check_reviewers_cursor_preflight_rc2_one_shot_and_cleanup` (`python/test_agents.py:1200-1242`) patches `fake_cleanup` but never asserts cleanup ran, despite the name (same pattern as `transient_rc1_one_shot`). A regression that skipped cleanup would not fail CI. Pre-existing; the new seam does not worsen it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Track cleanup calls and assert exactly one invocation when the probe path runs.
  - From cursor-specialist-testing-output.txt: Track cleanup calls and assert `calls == 1`, mirroring `test_check_reviewers_cursor_private_config_cleanup`.

### OOS_4: [OUT_OF_SCOPE] stall-branch consolidation lacks targeted tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The diff includes stall-branch consolidation (`classifier-failed`/`tally-flush-failed` merge, `coder-failed` dict lookup) at `python/review_and_fix.py:2932-2946` beyond the plan's wrapper delete/inline. Behavior looks equivalent to the pre-change branches, but this PR adds no targeted tests for those paths, so a future typo there would rely on distant Step 5 coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Keep the planned timing change only, or add/extend a stall-status unit test if you want mechanical guardrails on those branches.
