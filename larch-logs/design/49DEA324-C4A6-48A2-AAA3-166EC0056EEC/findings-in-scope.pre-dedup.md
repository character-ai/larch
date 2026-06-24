### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/agent_voters.py:432-433
- **Concern**: Plan mirrors plan_review_panel split dispatch but omits the parallel completion wait the reference implementation uses before status probes. Approach line 18 and agent_voters split-dispatch bullets specify async voter-1 plus a separate voters 2-3 waterfall yet never restate the post-waterfall wait that today’s unified path implements via `_wait_sentinels` over all three `.done` files. plan_review_panel.dispatch_voters waits the voter-1 process after the waterfall returns (python/plan_review_panel.py:714-718) before reading outputs.. Scenario: On Cursor-present runs, launching voter-1 concurrently with the voters 2-3 waterfall and then binding waterfall stdout immediately can probe voter-1 `.done`/output while validity is still running, mark voter-1 failed, or start parse-rate retry early. Codex-up/Cursor-down runs that Popen Claude voter-1 while launching the two-slot Codex waterfall have the same race. Pin the mirror contract explicitly: after the voters 2-3 waterfall returns, wait the voter-1 launch handle when started asynchronously, then call `_wait_sentinels` over every launched judge `.done` (voter-1 plus voters 2-3 resolved winning paths) before `.done`-rc probes, status assignment, and parse-rate retry; add regression tests for slow voter-1 finishing after the waterfall.
- **Proposed resolution**: 



### FINDING_2:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/agent_voters.py:200-222
- **Concern**: Split voters 2-3 still routed through `_dispatch_waterfall`, which hardcodes `--no-fallback`. Scenario: The plan requires voters 2-3 to launch via `agent dispatch-waterfall` without global `--no-fallback` so Codex-primary slots can fall back to Cursor. The live `_dispatch_waterfall` helper always appends `--no-fallback` (line 214). Reusing it for the new two-row manifest silently disables the required Codex-down/Cursor-up fallback and leaves pragmatism/plan-fidelity failed instead of on Cursor.
- **Proposed resolution**: Under `### UPDATED: python/agent_voters.py`, add an explicit step: parameterize `_dispatch_waterfall(..., no_fallback: bool)` or add `_dispatch_voter23_waterfall` that omits `--no-fallback`; route only voter-1 one-slot isolation through a `--no-fallback` launcher. State that the existing helper must not be reused verbatim for voters 2-3.



### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/agent_voters.py:432-449
- **Concern**: Split dispatch omits a combined `.done` wait across voter-1 and voters 2-3. Scenario: After split dispatch, the Cursor-present path must wait on voter-1 plus voters 2-3 before `.done` rc probes and parse-rate retry. The Codex-up/Cursor-down path currently waits only voter-1 (lines 448-449) while the plan adds a voters 2-3 waterfall there. Mirroring `plan_review_panel.dispatch_voters` Popen-plus-waterfall without restating `_wait_sentinels` can probe voter-1 or voters 2-3 before their `.done` files exist, causing false failures or premature parse-rate retry.
- **Proposed resolution**: In `### UPDATED: python/agent_voters.py`, require one `_wait_sentinels(review_tmpdir, [v1.done, v2.done, v3.done])` (or the launched subset on Claude-only shrink) after both voter-1 launch and the voters 2-3 waterfall return, on Cursor-present and Codex-up/Cursor-down paths, before `_read_done_exit_code` and parse-rate retry. Add a test that voter-1 `.done` is still pending when the waiter starts.



### FINDING_4:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/agents.py:483-548; plan.txt:47-54
- **Concern**: Default Codex role drops the existing `--default-model` fallback contract. Scenario: Current `resolve_model_args("codex", default_model=...)` and `agent model-args --default-model` use that value when env and plugin options are unset. The plan's default role falls straight to `gpt-5.5`, which breaks that CLI/Python surface outside the cheap-role change.
- **Proposed resolution**: Keep the default-role ladder as `LARCH_CODEX_MODEL`, plugin option, then `default_model or gpt-5.5`; add a focused assertion for `agent model-args --tool codex --default-model custom`.



