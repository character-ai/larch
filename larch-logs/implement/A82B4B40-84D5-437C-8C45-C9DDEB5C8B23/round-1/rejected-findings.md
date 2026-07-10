### [rejected] FINDING_2

**Rejected subtype:** dismissed (0 YES)

### FINDING_2: Synthetic Step 2 row is appended out of order
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases
- **Severity**: minor
- **Concern**: When no Step 2 mark exists, the synthesized Step 2 bucket is appended after later steps instead of being placed in step order, so per_step consumers see the wrong chronology.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Insert the synthetic Step 2 row at the right chronological index, or sort per_step after synthesis.
  - From codex-specialist-edge-cases: Insert the synthetic Step 2 row at the proper chronological position or sort per_step before returning.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** dismissed (0 YES)

### FINDING_5: Mixed-ledger tests miss the existing Step 2 merge path
- **Reviewer(s)**: cursor-specialist-testing, dyn-dyn-token-attribution
- **Severity**: minor
- **Concern**: The reroute coverage stops at the no-Step-2 shape, so the mixed ledger case with an existing Step 2 mark and both misplaced and in-span implementer rows is untested; duplicate synthetic Step 2 rows or double counting could regress undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add fixture with Step 0, misplaced codex_implement row, and existing Step 2 mark; assert no duplicate Step 2 row and stable totals
  - From dyn-dyn-token-attribution: Add a regression ledger with `Step 0`, `Step 2`, and `Step 3` marks, a misplaced implementer row under `Step 0`, and an in-span implementer row under `Step 2`; assert `Step 0` does not include implementer tokens, the single Step 2 bucket gets both implementer totals, vendor `totals` are unchanged, and per-step sums still match vendor totals for Codex and Cursor.
Vote tally: YES=0 NO=3 JUDGE_ERROR=0

