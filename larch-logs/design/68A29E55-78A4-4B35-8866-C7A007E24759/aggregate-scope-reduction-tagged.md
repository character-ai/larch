### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/review/plan_review_round.py:1022-1023
- **Concern**: [SCOPE-REDUCTION] DISPATCH_OK-only panel change leaves round DEGRADED_PANEL false on degraded-but-usable dispatch. Scenario: After gating DISPATCH_OK on effective>0, voter_1 can fail while Codex+Cursor succeed: DISPATCH_OK=true, tally runs, but degraded uses only DISPATCH_OK and DEGRADED_PANEL KV; voter-dispatch never emits DEGRADED_PANEL today, so values["DEGRADED_PANEL"] stays 0 and downstream round classification/continuation treats the round as clean despite the plan's degraded visibility goal
- **Proposed resolution**: Either make DEGRADED_PANEL=1 emission mandatory in plan_review_panel.py when effective<_PLAN_VOTER_PANEL_SIZE (not optional in tests), or add a one-line ### UPDATED plan_review_round.py change: treat voter_kv DEGRADED_PANEL_WARNING as degraded in the line 1022 predicate
