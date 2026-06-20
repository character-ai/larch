### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/plan_review.py:1453-1470
- **Concern**: [SCOPE-REDUCTION] Item 4 should pin in-memory warning carry at the continuation reset, not a new merge helper. Scenario: `awaiting-continuation` unlinks `.step3-review-result.env` then sets `degraded_values = {}` when `PLAN_REVIEW_CONTINUE=true`, so `MERGE_KEYS` replay cannot restore round-1 `DEGRADED_PANEL_WARNING` / `INVALID_SLOT_PANEL_WARNING`; final `complete_values` can omit them
- **Proposed resolution**: Replace `degraded_values = {}` with retaining only `_STEP3_ROUND_CARRY_KEYS` (or an equivalent snapshot) before advancing `round_num`; add the multi-round test against that branch; skip a separate merge helper if existing carry keys suffice



### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/plan_review.py:1469-1470
- **Concern**: Continuation advance clears all carried Step 3 warning state. Scenario: On PLAN_REVIEW_CONTINUE=true the loop sets degraded_values={} (and degraded_exit=false), dropping DEGRADED_PANEL_WARNING / INVALID_SLOT_PANEL_WARNING accumulated at python/plan_review.py:1367-1369; round-2+ apply/postplan envelopes and the final complete envelope can omit round-1 warnings even though MERGE_KEYS and _step3_round_carry_values already exist
- **Proposed resolution**: [SCOPE-REDUCTION] Reuse _STEP3_ROUND_CARRY_KEYS / _step3_round_carry_values at this boundary: retain only the two warning keys across continuation; reset other degraded state; do not add a parallel carry helper



### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/plan_review.py:1452-1471
- **Concern**: Item 4 omits that continuation unlinks `.step3-review-result.env` before clearing `degraded_values`. Scenario: Multi-round continue deletes the only persisted warning KV store; fixing the dict reset alone still loses warnings on resume/final emit
- **Proposed resolution**: Add a loop-scoped carried-warning map (or tmpdir sidecar) merged before the unlink and before building `complete_values` at ~1486-1487



### FINDING_4:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/plan_review.py:1469-1470
- **Concern**: Step 3 auto-continuation clears carry warnings because degraded_values is reset to {}. Scenario: When PLAN_REVIEW_CONTINUE=true advances to the next round, DEGRADED_PANEL_WARNING and INVALID_SLOT_PANEL_WARNING accumulated in degraded_values are dropped before later rounds and the final envelope
- **Proposed resolution**: Pin the fix at the continuation branch: stash _STEP3_ROUND_CARRY_KEYS before clearing state and restore them for the next round. Do not add another merge helper; _step3_round_carry_values already exists at python/plan_review.py:109-112



### FINDING_5:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/design_log_publish_flow.py:150-183
- **Concern**: Item 14 changes _copy_tree_redacted to return (success, scrub_violation_count) but omits the recursive child call at line 181. Scenario: A partial tree copy can return the wrong type, drop accumulated counts, or fail mid-publish without surfacing scrub totals
- **Proposed resolution**: Update the recursive call to aggregate child counts, return (False, partial_total) on failure, and adjust the run_dest copy loop at lines 292-293 to unpack the tuple



### FINDING_6:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: security
- **Location**: python/design_log_publish_flow.py:150-183
- **Concern**: Design pre-scrub path lacks the residual-secret fail-closed check before bypassing run-log re-scrub. Scenario: The plan writes redact.scrub_log_secrets() output in the design copy path, passes the count to run-log commit, then skips re-scrub when src and dest are the same tree. If a detected family remains after scrubbing, design publish can commit residual secret content while reporting a scrub count.
- **Proposed resolution**: Mirror python/run_logs.py:_scrub_run_tree: after scrub_log_secrets(), run scrub_log_secrets() on the scrubbed text and fail the copy/publish if residual findings remain.



