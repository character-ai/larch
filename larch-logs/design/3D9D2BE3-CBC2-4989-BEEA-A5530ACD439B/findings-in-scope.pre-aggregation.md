### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:1656-1683
- **Concern**: MAIN_ADVANCED split must early-continue and stay out of the shared increment-only tail. Scenario: Plan adds a rebase block for MAIN_ADVANCED but leaves today’s combined `if merged.result in {CI_NOT_READY, MAIN_ADVANCED}` tail at 1673-1683. If MAIN_ADVANCED still hits `iteration += 1; phase=ci-initial; continue` after the new rebase path, counters advance twice and the bug can persist (rebase once, then merge-retry loop without the forced rebase semantics the issue targets).
- **Proposed resolution**: Restructure the merge-result branch so `MERGE_RESULT_CI_NOT_READY` keeps the review-probe + increment-only path, `MERGE_RESULT_MAIN_ADVANCED` runs the mirrored `goto_rebase` sequence and `continue`s immediately, and MAIN_ADVANCED is removed from the shared increment-only condition.

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:1656-1683
- **Concern**: MAIN_ADVANCED split must not double-increment iteration. Scenario: The live branch unions MERGE_RESULT_CI_NOT_READY and MERGE_RESULT_MAIN_ADVANCED and always does iteration += 1 once. The plan adds rebase_count += 1 and iteration += 1 on the MAIN_ADVANCED path but never says to remove MAIN_ADVANCED from that shared tail or continue before it. A nested split can increment iteration twice per loop.
- **Proposed resolution**: Handle MAIN_ADVANCED in a dedicated elif with continue immediately after the rebase pass. Keep CI_NOT_READY-only logic in the remaining branch. Pin ITERATION delta in the new test.

