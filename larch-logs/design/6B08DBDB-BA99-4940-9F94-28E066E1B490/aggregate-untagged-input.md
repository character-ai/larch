### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/review_and_fix.py:2485-2500
- **Concern**: Item 1 does not require mutating RoundResult when flush_review_batches returns False. Scenario: flush_review_batches runs after status/exit_code are finalized; ignoring the bool leaves fix-applied/complete and the Step 5 loop emits complete (review_and_fix.py:2842-2880) despite a failed hard write-tally
- **Proposed resolution**: On tally write failure set result status to tally-flush-failed (non-zero exit_code) before return; add a Step 5 loop branch that maps it to stall with STALL_REASON=tally-flush-failed and STALL_TRACKING=true

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/review_and_fix.py:2466-2491
- **Concern**: Item 1 omits mutating RoundResult after tally flush failure. Scenario: _run_round writes review-and-fix.env and RoundResult with exit_code 0 before flush_review_batches; the flush return is ignored; step5 branches on result.status not flush rc, so write-tally failure still yields STEP5_REVIEW_STATUS=complete
- **Proposed resolution**: After flush_review_batches in the exit_code==0 branch, when write-tally returns False set result.status to a dedicated token (e.g. tally-flush-failed), set result.rc non-zero, and rewrite round review-and-fix.env; add an explicit step5 loop branch mapping that status to STALL_REASON=tally-flush-failed

### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/review_and_fix.py:2485-2500
- **Concern**: Item 1 does not require `_run_round` to override `RoundResult` when `flush_review_batches` returns False. Scenario: After a hard `write-tally` failure the round can still return `exit_code==0` with `status` in `complete`/`fix-applied`/etc.; Step 5 then emits `STEP5_REVIEW_STATUS=complete` and the run proceeds with a stale committed tally
- **Proposed resolution**: In the `exit_code == 0` branch, capture the `flush_review_batches` bool; on False set `exit_code=2` and `status=tally-flush-failed` (overriding any review success status) before building/returning `RoundResult`

### FINDING_4:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/review_and_fix.py:2443-2500
- **Concern**: Item 1 omits wiring flush_review_batches False to RoundResult before Step 5 loop. Scenario: _run_round builds a frozen RoundResult with status complete and writes review-and-fix.env before flush_review_batches; the return value is ignored today (~2487-2491). Item 1 requires a hard stop but only names stall reason tally-flush-failed. The Step 5 loop treats complete as terminal success (~2842-2843), so a failed tally flush would still finish Step 5 unless status is overridden.
- **Proposed resolution**: After flush_review_batches returns False on the exit_code==0 path, rebuild the result with dataclasses.replace (status tally-flush-failed, rc non-zero), rewrite round review-and-fix.env if needed, then emit round KVs and return so the loop hits the stall branch with STALL_REASON round-failed-tally-flush-failed (or an explicit tally-flush-failed mapping).

### FINDING_5:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/review_and_fix.py:1774-1786
- **Concern**: Item 12 plan does not move the lint snapshot early enough. Scenario: On the common clean-tree path after review fixes were already committed, line 1774 leaves pre_lint_head empty. If lint-fix then applies changes and later returns main-agent-required, the proposed commit-before-stall path cannot compute commit_paths, so Step 5 can still stall with dirty lint-fix work.
- **Proposed resolution**: Take the pre-lint snapshot before the lint-fix loop whenever a git HEAD exists, even when porcelain is initially clean, then reuse the existing delta filtering before the main-agent-required return.
