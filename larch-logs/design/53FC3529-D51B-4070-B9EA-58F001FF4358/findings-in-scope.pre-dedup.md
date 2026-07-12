### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/review/voting.py:1356-1375
- **Concern**: [SCOPE-REDUCTION] Plan binds the shared voter-status row builder to `voter_status_block_main` interleaved layout only, but code-review already emits per-voter sequential rows from `agent_voters._emit_final_kvs`.. Scenario: Unifying on the plan-review row list reorders code-review stdout (VOTER_2/3 tool/status/parse move after VOTER_3_PATH and optional VOTER_PATHS_FILE), breaking the acceptance "14 VOTER_* final KVs stay identical" contract and the failure-mode ban on silent KV-order changes; only plan-review order is pinned by `test_voter_dispatch_stdout_key_order`.
- **Proposed resolution**: Add an explicit `row_layout` (or equivalent) to `dispatch_shared` with `plan_review_interleaved` and `code_review_sequential`; have `voter_status_block_main` and the in-process emitter select the family layout independently of paths-file policy; extend `test_dispatch_shared.py` with a code-review sequential-order regression alongside the existing plan-review interleaved case.



### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/review/dispatch_shared.py:shared final-KV row builder; python/larch/review/voting.py:1338-1372
- **Concern**: The plan does not preserve each family's existing VOTER KV order. Scenario: A single shared ordering can break plan-review's unchanged exact-order test or change code-review's wire contract
- **Proposed resolution**: Define explicit code-review and plan-review emission-order policies and test both orders, including paths-file omission and DISPATCH_OK placement



### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/review/dispatch_shared.py
- **Concern**: Unifying code-review final emission through the voter_status_block row builder changes KV order. Scenario: agent_voters._emit_final_kvs emits VOTER_2/3 tool-status-parse keys immediately after each path; voter_status_block_main interleaves VOTER_2_PATH and VOTER_3_PATH before VOTER_2_TOOL. Routing agent_voters through the shared builder without an explicit order policy changes code-review stdout order while failure modes forbid silent order changes
- **Proposed resolution**: Add an emission-order policy to the shared final-KV emitter (for example interleaved vs sequential) and bind code-review to sequential order, or document intentional alignment to interleaved order and add a test_agent_voters stdout key-order regression



### FINDING_4:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/review/plan_review_panel.py
- **Concern**: Plan-review trailing KVs still use print after voter block moves to emit_kv. Scenario: _emit_final_kvs currently replays voter-status-block stdout with print; VOTER_1_RETRIED and DEGRADED_PANEL use _emit (print). Moving voter KVs to logging_util.emit_kv under quiet_init leaves trailing keys on redirected stdout, so contract-stream parsers can miss VOTER_1_RETRIED and DEGRADED_PANEL
- **Proposed resolution**: Route VOTER_1_RETRIED and DEGRADED_PANEL through logging_util.emit_kv, preserving the existing post-DISPATCH_OK order exercised by test_voter_dispatch_stdout_key_order



### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/larch/review/plan_review_panel.py:1268-1269
- **Concern**: [ALREADY_ADDRESSED] Plan-review voter dispatch lacks quiet_init parity with code-review. Scenario: agent_voters.dispatch_voters_main calls logging_util.quiet_init before emit_kv; plan_review_panel.dispatch_voters_main does not. emit_kv only reaches fd 3 when quiet_init ran; without it, plan-review voter KVs may land on the quiet log stream instead of the contract stream under production wrappers
- **Proposed resolution**: Add logging_util.quiet_init(argv0="plan-review voter-dispatch") to dispatch_voters_main in the same plan_review_panel.py update that routes final voter emission through the shared emitter Wait - I used [ALREADY_ADDRESSED] prefix on finding 3 but it's saying the plan doesn't fully address it - that's wrong. FINDING_3 was accepted with emit_kv fix but quiet_init for plan_review wasn't in plan. I should NOT use [ALREADY_ADDRESSED] - that's for when plan already covers it. Remove [ALREADY_ADDRESSED] from finding 3. Also reconsider finding 3 - is it duplicate of FINDING_3 accepted? FINDING_3 was about print vs emit_kv in shared emitter. quiet_init for plan_review entry is adjacent but distinct. Keep as separate minor finding without ALREADY_ADDRESSED. Revise finding 3 text without prefix. schema_version scope severity focus_area location what scenario_or_breakage suggested_fix



### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/review/dispatch_shared.py
- **Concern**: Unifying code-review final emission through the voter_status_block row builder changes KV order. Scenario: agent_voters._emit_final_kvs emits each voter's PATH/TOOL/STATUS/PARSE_RATE block sequentially; voter_status_block_main emits VOTER_2_PATH and VOTER_3_PATH before VOTER_2_TOOL. Routing agent_voters through the shared builder without an explicit order policy changes code-review stdout order while failure modes forbid silent order changes
- **Proposed resolution**: Add an emission-order policy to the shared final-KV emitter (for example interleaved vs sequential) and bind code-review to sequential order, or document intentional alignment to interleaved order and add a test_agent_voters stdout key-order regression



### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/review/plan_review_panel.py
- **Concern**: Plan-review trailing KVs still use print after voter block moves to emit_kv. Scenario: _emit_final_kvs replays voter-status-block stdout with print today; VOTER_1_RETRIED and DEGRADED_PANEL use _emit (print). Moving voter KVs to logging_util.emit_kv under quiet_init leaves trailing keys on redirected stdout, so contract-stream parsers can miss VOTER_1_RETRIED and DEGRADED_PANEL
- **Proposed resolution**: Route VOTER_1_RETRIED and DEGRADED_PANEL through logging_util.emit_kv, preserving the post-DISPATCH_OK order required by test_voter_dispatch_stdout_key_order



### FINDING_8:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/larch/review/plan_review_panel.py:1268-1269
- **Concern**: Plan-review voter dispatch lacks quiet_init parity with code-review. Scenario: agent_voters.dispatch_voters_main calls logging_util.quiet_init before emit_kv; plan_review_panel.dispatch_voters_main does not. Without matching quiet_init, emit_kv may fall back to redirected stdout instead of the fd 3 contract stream in production wrappers
- **Proposed resolution**: Add logging_util.quiet_init(argv0="plan-review voter-dispatch") to dispatch_voters_main in the same plan_review_panel.py update that routes final voter emission through the shared emitter --- **Summary** The plan covers most prior-round accepted items: absent paths as `None`, plan-review facades, in-process `emit_kv` (no subprocess), Codex role resolution, and paths-file `always` vs `nonempty` policies. Three gaps remain: 1. **KV order (major)** — Code-review and plan-review use different emission orders today. The shared builder comes from `voter_status_block_main` (interleaved). Code-review would change wire order unless the plan adds an explicit policy. 2. **Trailing plan KVs (major)** — `VOTER_1_RETRIED` and `DEGRADED_PANEL` still use `print` via `_emit`. After voter KVs move to `emit_kv`, those keys can miss the contract stream under quiet routing. 3. **quiet_init (minor)** — `plan_review_panel.dispatch_voters_main` does not call `quiet_init` like `agent_voters` does, which weakens the FINDING-3 fix on the plan-review path.



### FINDING_9:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/review/dispatch_shared.py (plan lines 20-28, 38)
- **Concern**: Shared row builder cannot preserve both existing KV orders. Scenario: The builder extracted from `voter_status_block_main` uses plan-review ordering, which differs from `agent_voters._emit_final_kvs`; routing code review through it breaks the promised wire order
- **Proposed resolution**: Parameterize the row layout by family and test both existing sequences exactly



### FINDING_10:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/review/dispatch_shared.py
- **Concern**: The shared row builder is sourced only from voter_status_block_main, but the two families emit the 14 final VOTER_* lines in different orders today.. Scenario: Code review emits per-slot blocks (VOTER_2_TOOL immediately after VOTER_2_PATH). Plan review uses the interleaved voter_status_block order (VOTER_2_PATH and VOTER_3_PATH before VOTER_2_TOOL). A single shared builder would change code-review stdout byte order. The plan also forbids silently changing final voter KV order, and test_dispatch_shared.py only locks one ordering.
- **Proposed resolution**: Add a family-specific kv_order policy to the shared row builder and final emitter (for example sequential for code review and plan_interleaved for plan review). Route agent_voters through sequential order and plan_review_panel through interleaved order. Extend test_dispatch_shared.py with regressions for both orderings.



