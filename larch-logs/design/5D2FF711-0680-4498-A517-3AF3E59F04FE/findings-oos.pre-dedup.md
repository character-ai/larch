### OOS_1: Plan-review scoreboard still labels vote-accepted OOS as `OOS-Accepted`
- **Description**: Plan-review scoreboard still labels vote-accepted OOS as `OOS-Accepted`. Scenario: After progress_report renames its column to `OOS fileable`, `voting-tally.md` scoreboard rows still increment `oos_accepted` for every vote-accepted OOS (including accepted-minor), so design operators comparing the scoreboard to the progress table can still read vote-accepted as fileable.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/larch/review/plan_review_tally.py:798-858
- **Phase**: design



