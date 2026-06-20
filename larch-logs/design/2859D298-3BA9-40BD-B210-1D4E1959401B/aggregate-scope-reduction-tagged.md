### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/plan_review.py:1453-1470
- **Concern**: [SCOPE-REDUCTION] Item 4 should pin in-memory warning carry at the continuation reset, not a new merge helper. Scenario: `awaiting-continuation` unlinks `.step3-review-result.env` then sets `degraded_values = {}` when `PLAN_REVIEW_CONTINUE=true`, so `MERGE_KEYS` replay cannot restore round-1 `DEGRADED_PANEL_WARNING` / `INVALID_SLOT_PANEL_WARNING`; final `complete_values` can omit them
- **Proposed resolution**: Replace `degraded_values = {}` with retaining only `_STEP3_ROUND_CARRY_KEYS` (or an equivalent snapshot) before advancing `round_num`; add the multi-round test against that branch; skip a separate merge helper if existing carry keys suffice
