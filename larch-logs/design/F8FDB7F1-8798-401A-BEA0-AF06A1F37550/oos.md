### OOS_1:
- **Description**: `test-render-cost-line-callsites.sh` Step 18 launcher awk block must be rewritten, not only grep strings. Scenario: The harness awk-scopes the old `python/cli.py final-report step18b` fence (`scripts/test-render-cost-line-callsites.sh:61-65`). Replacing grep pins without updating that block can leave stale launcher checks or miss wrapper `.step17-emitted` touches.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: architecture
- **Location**: plan.txt:254-263
- **Phase**: design

Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral

