### OOS_1: Symlinked `$DESIGN_TMPDIR/reviewer-status-table.txt` skips clear/write and Step 3 has no staleness guard
- **Description**: Symlinked `$DESIGN_TMPDIR/reviewer-status-table.txt` skips clear/write and Step 3 has no staleness guard. Scenario: The plan preserves symlink-safe no-op clears. If a prior-round pre-rendered line remains reachable through a symlink, Step 3 Read emits it verbatim and only warns when the path is missing, not when content is stale. Operators may see prior-round icons with no warning.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: correctness
- **Location**: plan.txt:177;python/plan_review_round.py:56-64
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

