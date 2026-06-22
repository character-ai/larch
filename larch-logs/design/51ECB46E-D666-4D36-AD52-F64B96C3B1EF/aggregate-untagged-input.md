### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:1689-1699
- **Concern**: `_ship_phase14_rebase` success path omits today's `_write_ship_state(phase="ci-initial", ...)` contract. Scenario: On phase14 rebase success the inline loop writes `phase="ci-initial"` with incremented `rebase_count`, cleared `resume_phase`/`caller_kind`, and `last_monitored_head` before `continue`. The plan only lists flag unlink, local `rebase_count += 1`, handoff clears, and `continue`, so a helper-only extraction can drop the durable state write and regress `test_phase14_flag_rebase_success_clears_handoff_and_conflict_files` plus resume counters.
- **Proposed resolution**: Extend `_ship_phase14_rebase` to include the existing success `_write_ship_state(phase="ci-initial", iteration, rebase_count, fix_attempts, transient_retries, resume_phase="", caller_kind="", last_monitored_head=...)` before returning/`continue`; add a focused helper test mirroring that state contract.

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/review_pipeline.py:45-46
- **Concern**: `dispatch_scout_rows` definition names only three scout keys. Scenario: After successful dispatch, current code also emits conditional `SCOUT_FAIL_REASON`, `PRUNED_COMBOS`, and unconditional `PANEL_PRUNED_EMPTY` before branch split. A tuple built from only `SCOUT_STATUS`/`DYNAMIC_SLOTS`/`SCOUT_MANIFEST` will drop keys on prune-skipped, threshold-failure, zero-findings, and downstream paths, breaking `review_core_capture` consumers.
- **Proposed resolution**: Define `dispatch_scout_rows` as the full post-dispatch prefix through today's `python/review_pipeline.py:2078-2086` block (conditional fail reason/combos, always `PANEL_PRUNED_EMPTY`), and golden-test at least one branch where `PRUNED_COMBOS`/`PANEL_PRUNED_EMPTY` must appear.

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:1689-1699
- **Concern**: phase14 success state write contract is incomplete in `_ship_phase14_rebase`. Scenario: Today's phase14 path writes `phase=ci-initial` with `resume_phase=""`, `caller_kind=""`, and `last_monitored_head=last_monitored_head or ""` after a successful rebase. The plan only says to clear handoff fields and `continue`, so a helper or partial extraction can drop `last_monitored_head` and change empty-checks grace on the next monitor pass
- **Proposed resolution**: Add an explicit phase14 success contract: caller or helper must preserve today's `_write_ship_state(phase="ci-initial", ..., resume_phase="", caller_kind="", last_monitored_head=...)` field set; add a focused assertion in `test_phase14_flag_rebase_success_clears_handoff_and_conflict_files` or a new helper test

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:1951-2016
- **Concern**: `main_advanced` rebase variant omits explicit `phase="rebase"` pre-write. Scenario: Both `goto_rebase` and `MERGE_RESULT_MAIN_ADVANCED` currently write `phase="rebase"` before Flush+Push. The plan spells this out only for `goto_rebase`; `main_advanced` says "same Flush+Push contract" but does not list the pre-rebase state write, so the helper can skip it and stall/resume metadata diverges
- **Proposed resolution**: State explicitly that `ShipRebaseVariant.main_advanced` also writes `phase="rebase"` with the same counter snapshot before flush/rebase; cover in `_ship_rebase_phase` helper tests

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/design_lifecycle.py:3053-3109
- **Concern**: `_postplan_decide` row contract is detailed for rc `10` but underspecified for rc `0`/`12`/`13`. Scenario: Executor assembly is `captured + "".join(decision.rows)`. For rc `0`/`12`/`13`, today's body appends `POSTPLAN_RC`/`POSTPLAN_STATUS` (and only those KV rows) after captured emit output. If `_postplan_decide` omits them, decide-only tests can pass while `step2b_postplan_main` and drafter wrapper parsers lose required rows
- **Proposed resolution**: Document and test that rc `0` rows are `POSTPLAN_RC=0` + `POSTPLAN_STATUS=ok`; rc `12`/`13` rows are their `POSTPLAN_RC`/`POSTPLAN_STATUS` pairs; touches stay in apply metadata only

### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/review_pipeline.py:2015-2060
- **Concern**: Early-exit branches hardcode `panel_mode="normal"` and argv `panel`, not dispatch panel metadata. Scenario: The description-empty and dispatch-failure paths call `_emit_core_common(..., "normal", panel)` before any dispatch parse. The branch recipe table lists only scout/common segments and does not pin `PANEL_MODE`/`PANEL_SHAPE`, so a recipe copied from post-dispatch branches can emit `waterfall`/dispatch shape and break `review_core_capture` consumers
- **Proposed resolution**: Add recipe rows for description-empty and dispatch-failure that require `_core_common_rows(..., panel_mode="normal", panel_shape=<argv --panel>)`; cover in direct `_review_core_body` tests

### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/ship.py:1857-1876
- **Concern**: `_ship_rebase_phase` stall/return contract is unspecified. Scenario: When pre-rebase `flush_logs_pre` is skipped for a disallowed reason, today's code writes terminal stall state, publishes snapshot, and returns `ShipResult(Outcome.STALLED, ...)`. Without a pinned helper return/raise contract, the merge loop can continue after a stall
- **Proposed resolution**: Specify `_ship_rebase_phase` returns a small result (for example `Outcome.OK | STALLED` plus detail) or re-raises/returns `ShipResult`; caller must immediately return on stall and must not bump `iteration` or write ci-initial state

### FINDING_9:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/design_lifecycle.py:3034-3117
- **Concern**: Postplan ok/size/partition paths lack the same decide-metadata contract as rc 10. Scenario: The plan requires side-effect-free `_postplan_decide` plus an apply phase driven by `PostplanDecision.touches` (lines 111-123, 150-151), and decide tests must assert metadata without filesystem I/O (line 255). rc `10` enumerates touches/writes/unlinks/`clear_scout_manifests` (lines 127-131), but rc `0`/`12`/`13` completion touches appear only in preserve-rc prose (lines 160-165). The rc `0` decide test (line 248) names no expected `touches`. An implementer can keep rc `0`/`12`/`13` sentinel touches in `_shared_step2b_postplan_body`, leaving `_postplan_decide` untestable on the ok path and breaking the acceptance goal of a pure postplan decider.
- **Proposed resolution**: Spell out required `PostplanDecision` metadata for rc `0` (`.completed/step-2b.5`, optional `.completed/step-2b` when `site` is `step2b`), rc `12`, and rc `13` (`.completed/step-2b`) the same way rc `10` is specified; extend the rc `0`/`12`/`13` decide tests to assert those fields.

### FINDING_10:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/test_review_pipeline.py:234-243
- **Concern**: Golden stdout-order smoke tests lack a pre-refactor baseline capture step. Scenario: The plan requires full-line-order golden smoke tests for nine `review_core` branches (lines 234-243) and states batch emission must mirror per-branch order (lines 27-28, 305-306). It does not require recording current stdout from `review_core` (or `review_core_capture`) before the refactor. Row-level `_review_core_body` tests can pass while emit order regresses, breaking `review_and_fix.review_core_capture` and Step 5 parsers.
- **Proposed resolution**: Add an implementation-order step 0 (or phase 1 sub-step): capture pre-refactor golden stdout for each listed branch from current `python/review_pipeline.py`, commit fixtures under `python/test_review_pipeline.py` (or a sibling golden file), then refactor and lock parity against those fixtures.

### FINDING_12:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:1847-2005
- **Concern**: If ship extraction remains, _ship_rebase_phase lacks a required return contract for caller-owned state. Scenario: Both current rebase branches increment rebase_count before later state writes, and disallowed pre-rebase flush returns ShipResult(STALLED) immediately; a helper that only mutates a local counter or writes terminal state can persist stale REBASE_COUNT or continue after a stall
- **Proposed resolution**: Require the helper to return a small result carrying updated rebase_count plus an optional terminal ShipResult/action, and require callers to assign the count and return terminal results before iteration/state writes; otherwise keep the block inline
