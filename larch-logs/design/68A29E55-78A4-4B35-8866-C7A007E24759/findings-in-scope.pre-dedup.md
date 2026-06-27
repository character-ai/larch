### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/review/plan_review_round.py:1022-1023
- **Concern**: DEGRADED_PANEL=1 must be mandatory when effective < _PLAN_VOTER_PANEL_SIZE; plan hedges with "if implemented" and "unless omission safer". Scenario: After DISPATCH_OK switches to effective > 0, a 2/3 panel (Claude failed, Codex+Cursor substantive) can tally and accept findings while plan_review_round sets degraded=false because voter_kv lacks DEGRADED_PANEL=1; DEGRADED_PANEL_WARNING alone does not drive degraded classification or continuation inputs
- **Proposed resolution**: Require _emit DEGRADED_PANEL=1 whenever effective < _PLAN_VOTER_PANEL_SIZE before DISPATCH_OK; remove optional language from the plan and tests



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/test_plan_review_round.py:proposed-degraded-dispatch-test
- **Concern**: Proposed execute_round regression test does not assert DEGRADED_PANEL propagates through round values. Scenario: A regression that emits DEGRADED_PANEL_WARNING but omits DEGRADED_PANEL=1 would still pass the planned round test (tally called, LOOP_STATUS != panel-failed) while step3 envelopes and continuation logic read DEGRADED_PANEL=0
- **Proposed resolution**: Add values["DEGRADED_PANEL"] == "1" (and keep DEGRADED_PANEL_WARNING present) to the planned execute_round degraded-dispatch assertions



### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/review/plan_review_round.py:1022-1023
- **Concern**: [SCOPE-REDUCTION] DISPATCH_OK-only panel change leaves round DEGRADED_PANEL false on degraded-but-usable dispatch. Scenario: After gating DISPATCH_OK on effective>0, voter_1 can fail while Codex+Cursor succeed: DISPATCH_OK=true, tally runs, but degraded uses only DISPATCH_OK and DEGRADED_PANEL KV; voter-dispatch never emits DEGRADED_PANEL today, so values["DEGRADED_PANEL"] stays 0 and downstream round classification/continuation treats the round as clean despite the plan's degraded visibility goal
- **Proposed resolution**: Either make DEGRADED_PANEL=1 emission mandatory in plan_review_panel.py when effective<_PLAN_VOTER_PANEL_SIZE (not optional in tests), or add a one-line ### UPDATED plan_review_round.py change: treat voter_kv DEGRADED_PANEL_WARNING as degraded in the line 1022 predicate



### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/test_plan_review_panel.py:903-943
- **Concern**: Plan omits stdout key-order test update when adding DEGRADED_PANEL. Scenario: test_voter_dispatch_stdout_key_order pins exact voter-dispatch KV order; inserting DEGRADED_PANEL (likely after DEGRADED_PANEL_WARNING or before DISPATCH_OK) will fail CI even when dispatch logic is correct
- **Proposed resolution**: Add ### UPDATED test_plan_review_panel.py step to extend expected key list in test_voter_dispatch_stdout_key_order, or document fixed insertion point if DEGRADED_PANEL is dropped in favor of WARNING-based degraded inference



### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_plan_review_round.py
- **Concern**: Proposed round regression omits DEGRADED_PANEL assertion on success path. Scenario: Plan failure modes warn that DISPATCH_OK-only checks miss degraded-metadata regressions; the new execute_round test asserts tally argv and LOOP_STATUS but not values["DEGRADED_PANEL"]=="1", so a future change could restore tally while clearing degraded flags again
- **Proposed resolution**: Assert values["DEGRADED_PANEL"]=="1" (and optionally that DEGRADED_PANEL_WARNING propagates) in the new degraded-but-usable voter-dispatch round test



### FINDING_6:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/test_plan_review_panel.py new regression test treats `DEGRADED_PANEL=1` as optional instead of required for the degraded-but-usable voter path
- **Concern**: The PR can still land even if the panel stops emitting the degraded flag, and the round-path regression would not catch the loss of degraded-panel visibility. Scenario: Make the new panel test assert `DEGRADED_PANEL=1` unconditionally, and add the round regression assertion `values["DEGRADED_PANEL"] == "1"` after `execute_round`
- **Proposed resolution**: 



### FINDING_7:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/test_plan_review_panel.py:903-943
- **Concern**: Plan adds `DEGRADED_PANEL` as a new voter-dispatch KV, but does not update the exact key-order regression test; the current expected list ends at `DISPATCH_OK`.. Scenario: Once the new field is emitted, this test will fail and the new wire contract will not be verified.
- **Proposed resolution**: Add `DEGRADED_PANEL` to the expected key sequence in its emitted position, or relax the assertion if key order is not contractual.



