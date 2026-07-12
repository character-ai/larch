### FINDING_1: Preserve family-specific final-KV order
- **Reviewer(s)**: Codex-Arch, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: The two review families currently emit the 14 final `VOTER_*` KVs in different orders. A single shared builder without an explicit family-specific order policy would change code-review’s stdout wire order.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Define explicit code-review and plan-review emission-order policies and test both orders, including paths-file omission and DISPATCH_OK placement
  - From Cursor-Pragmatic: Add an emission-order policy to the shared final-KV emitter (for example interleaved vs sequential) and bind code-review to sequential order, or document intentional alignment to interleaved order and add a test_agent_voters stdout key-order regression
  - From Codex-Pragmatic: Parameterize the row layout by family and test both existing sequences exactly
  - From Cursor-Requirements: Add a family-specific kv_order policy to the shared row builder and final emitter (for example sequential for code review and plan_interleaved for plan review). Route agent_voters through sequential order and plan_review_panel through interleaved order. Extend test_dispatch_shared.py with regressions for both orderings.


### FINDING_2: Preserve trailing plan-review contract KVs
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Concern**: Moving voter KVs to `emit_kv` while leaving `VOTER_1_RETRIED` and `DEGRADED_PANEL` on `print` can send those trailing keys to the wrong stream, causing contract-stream parsers to miss them.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Route VOTER_1_RETRIED and DEGRADED_PANEL through logging_util.emit_kv, preserving the existing post-DISPATCH_OK order exercised by test_voter_dispatch_stdout_key_order
  - From Cursor-Pragmatic: Route VOTER_1_RETRIED and DEGRADED_PANEL through logging_util.emit_kv, preserving the post-DISPATCH_OK order required by test_voter_dispatch_stdout_key_order


### FINDING_3: Initialize quiet routing for plan-review voter dispatch
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Concern**: `plan_review_panel.dispatch_voters_main` lacks the `quiet_init` setup used by code review. Without it, `emit_kv` may write to the wrong stream under production wrappers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add logging_util.quiet_init(argv0="plan-review voter-dispatch") to dispatch_voters_main in the same plan_review_panel.py update that routes final voter emission through the shared emitter


### FINDING_4:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/review/voting.py:1356-1375
- **Concern**: [SCOPE-REDUCTION] Plan binds the shared voter-status row builder to `voter_status_block_main` interleaved layout only, but code-review already emits per-voter sequential rows from `agent_voters._emit_final_kvs`.. Scenario: Unifying on the plan-review row list reorders code-review stdout (VOTER_2/3 tool/status/parse move after VOTER_3_PATH and optional VOTER_PATHS_FILE), breaking the acceptance "14 VOTER_* final KVs stay identical" contract and the failure-mode ban on silent KV-order changes; only plan-review order is pinned by `test_voter_dispatch_stdout_key_order`.
- **Proposed resolution**: Add an explicit `row_layout` (or equivalent) to `dispatch_shared` with `plan_review_interleaved` and `code_review_sequential`; have `voter_status_block_main` and the in-process emitter select the family layout independently of paths-file policy; extend `test_dispatch_shared.py` with a code-review sequential-order regression alongside the existing plan-review interleaved case.

