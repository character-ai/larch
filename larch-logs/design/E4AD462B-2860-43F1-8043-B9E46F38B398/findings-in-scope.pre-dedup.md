### FINDING_1:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_review_pipeline.py:40-49
- **Concern**: All-security-only pre-vote drop test is optional though it guards the primary leak path. Scenario: When every dropped OOS block is security-tagged, a missed empty write to oos-dropped-before-vote.md leaves prior-round public audit bytes in review_tmpdir; _flush_round_log still allowlists and commits that stale public file, so security fixes can ship without catching the exact regression this issue describes
- **Proposed resolution**: Make the all-security dropped-OOS pytest mandatory (not "if needed"): assert dropped_count counts security blocks, oos-dropped-before-vote.md is empty, and oos-dropped-security-local.md holds the renumbered security block



### FINDING_2:
- **Reviewer(s)**: Codex-dyn-Security Oos Boundary
- **Severity**: blocking
- **Focus area**: security
- **Location**: <TMPDIR>/plan.txt:25-30,63-66
- **Concern**: [ALREADY_ADDRESSED] The plan splits the audit streams, but it does not make the two writes atomic or clean up the public file on any write failure. A failure after `oos-dropped-before-vote.md` is written can leave public security-adjacent content on disk.. Scenario: `python/review_pipeline.py:2262-2264` still routes gate failures through the panel-failed path, which flushes the round log, and `python/run_logs.py:2999-3009` still allowlists `oos-dropped-before-vote.md`. So a partial failure can still publish stale public content.
- **Proposed resolution**: Stage both audit writes to temp files and rename them only after both succeed, or truncate/delete `oos-dropped-before-vote.md` before re-raising so the fail-closed path cannot flush partial public content.



