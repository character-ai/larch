### FINDING_1: Safe-compression can drop harness-exact waiter-ban literal
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan’s safe-compression guidance (merge adjacent sentences that repeat the same guard) conflicts with two intentionally distinct waiter-ban phrasings in `skills/shared/design-background-wait.md` (lines 29 and 31). `scripts/test-implement-anti-polling-rule.sh` pins the exact substring `NEVER launch a background recovery waiter` via a file-wide `check` (lines 225–226), while line 31 keeps the longer `Do not launch a background recovery waiter such as…` example. Merging or consolidating those sentences per safe-compression can preserve semantics but remove the harness-exact NEVER literal and fail CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add an explicit safe-compression carve-out: never merge the line-29 NEVER waiter ban with the line-31 `Do not launch…` example, and add `NEVER poll `.step3-review-result.env` with a sleep loop.` and `NEVER launch a background recovery waiter` to the protected-literal bullet list (harness also enforces the poll literal exactly once at lines 216-223).
  - From Cursor-Pragmatic: Add an explicit carve-out under safe compression: never merge or paraphrase away the standalone `NEVER launch a background recovery waiter` sentence; keep it as its own harness-exact line distinct from the longer `Do not launch…` example.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

