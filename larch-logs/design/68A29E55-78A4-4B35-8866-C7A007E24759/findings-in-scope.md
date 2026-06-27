### FINDING_1: Mandatory `DEGRADED_PANEL=1` when panel is degraded
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: `DEGRADED_PANEL=1` must be emitted whenever `effective < _PLAN_VOTER_PANEL_SIZE`. Optional plan language ("if implemented", "unless omission safer") leaves a gap: after `DISPATCH_OK` switches to `effective > 0`, a 2/3 panel (Claude failed, Codex+Cursor substantive) can tally and accept findings while `plan_review_round` sets `degraded=false` because `voter_kv` lacks `DEGRADED_PANEL=1`; `DEGRADED_PANEL_WARNING` alone does not drive degraded classification or continuation inputs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Require _emit DEGRADED_PANEL=1 whenever effective < _PLAN_VOTER_PANEL_SIZE before DISPATCH_OK; remove optional language from the plan and tests

### FINDING_2: Round regression must assert `DEGRADED_PANEL` propagation
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: important
- **Concern**: The proposed `execute_round` degraded-dispatch regression in `python/test_plan_review_round.py` does not assert that `DEGRADED_PANEL` propagates through round values. A regression that emits `DEGRADED_PANEL_WARNING` but omits `DEGRADED_PANEL=1` could still pass (tally called, `LOOP_STATUS != panel-failed`) while step3 envelopes and continuation logic read `DEGRADED_PANEL=0`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add values["DEGRADED_PANEL"] == "1" (and keep DEGRADED_PANEL_WARNING present) to the planned execute_round degraded-dispatch assertions
  - From Cursor-Innovation: Assert values["DEGRADED_PANEL"]=="1" (and optionally that DEGRADED_PANEL_WARNING propagates) in the new degraded-but-usable voter-dispatch round test

### FINDING_3: Update voter-dispatch stdout key-order regression for `DEGRADED_PANEL`
- **Reviewer(s)**: Cursor-Innovation, Codex-Requirements
- **Severity**: blocking
- **Concern**: The plan adds `DEGRADED_PANEL` as a new voter-dispatch KV but does not update `test_voter_dispatch_stdout_key_order` in `python/test_plan_review_panel.py` (lines 903-943), which pins exact voter-dispatch KV order ending at `DISPATCH_OK`. Once the new field is emitted, CI will fail even when dispatch logic is correct, and the wire contract will not be verified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add ### UPDATED test_plan_review_panel.py step to extend expected key list in test_voter_dispatch_stdout_key_order, or document fixed insertion point if DEGRADED_PANEL is dropped in favor of WARNING-based degraded inference
  - From Codex-Requirements: Add `DEGRADED_PANEL` to the expected key sequence in its emitted position, or relax the assertion if key order is not contractual.

### FINDING_4: Panel regression must require `DEGRADED_PANEL=1` on degraded-but-usable path
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Concern**: The new regression test in `python/test_plan_review_panel.py` treats `DEGRADED_PANEL=1` as optional instead of required for the degraded-but-usable voter path. The PR can land even if the panel stops emitting the degraded flag, and the round-path regression would not catch the loss of degraded-panel visibility.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/review/plan_review_round.py:1022-1023
- **Concern**: [SCOPE-REDUCTION] DISPATCH_OK-only panel change leaves round DEGRADED_PANEL false on degraded-but-usable dispatch. Scenario: After gating DISPATCH_OK on effective>0, voter_1 can fail while Codex+Cursor succeed: DISPATCH_OK=true, tally runs, but degraded uses only DISPATCH_OK and DEGRADED_PANEL KV; voter-dispatch never emits DEGRADED_PANEL today, so values["DEGRADED_PANEL"] stays 0 and downstream round classification/continuation treats the round as clean despite the plan's degraded visibility goal
- **Proposed resolution**: Either make DEGRADED_PANEL=1 emission mandatory in plan_review_panel.py when effective<_PLAN_VOTER_PANEL_SIZE (not optional in tests), or add a one-line ### UPDATED plan_review_round.py change: treat voter_kv DEGRADED_PANEL_WARNING as degraded in the line 1022 predicate
