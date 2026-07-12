### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/review/voting.py:1356-1375
- **Concern**: [SCOPE-REDUCTION] Plan binds the shared voter-status row builder to `voter_status_block_main` interleaved layout only, but code-review already emits per-voter sequential rows from `agent_voters._emit_final_kvs`.. Scenario: Unifying on the plan-review row list reorders code-review stdout (VOTER_2/3 tool/status/parse move after VOTER_3_PATH and optional VOTER_PATHS_FILE), breaking the acceptance "14 VOTER_* final KVs stay identical" contract and the failure-mode ban on silent KV-order changes; only plan-review order is pinned by `test_voter_dispatch_stdout_key_order`.
- **Proposed resolution**: Add an explicit `row_layout` (or equivalent) to `dispatch_shared` with `plan_review_interleaved` and `code_review_sequential`; have `voter_status_block_main` and the in-process emitter select the family layout independently of paths-file policy; extend `test_dispatch_shared.py` with a code-review sequential-order regression alongside the existing plan-review interleaved case.
