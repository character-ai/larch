### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:31-37
- **Concern**: Cursor CI normative epilogue table stops at stall guard and omits promote, failure append, and emit. Scenario: The per-family table is labeled normative; a hook list built only from lines 31-37 can skip `_promote_inner_done`, `_append_ci_failure`, and `_emit_ci_launcher_result`, breaking `.done` IPC and CI launcher-result stdout
- **Proposed resolution**: Add steps 6-8 to the Cursor CI table: `_promote_inner_done` → `_append_ci_failure` → `_emit_ci_launcher_result`, matching current `launch_cursor_ci_main` (~3713-3715) and the Codex CI table format



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:39-46
- **Concern**: Codex implement normative table jumps from step 5 (failure append) to step 7 (emit) and omits `_promote_inner_done`. Scenario: The numbered list is incomplete while later sections assume promote exists; a hook migration keyed only on this table can emit the implement envelope before `.inner.done` is promoted, so collectors wait on a missing public `.done`
- **Proposed resolution**: Insert step 6 `_promote_inner_done(output)` between failure append and `_emit_implement_launcher_envelope`; keep the adoption-scope 7-step list aligned with the numbered table



### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:48-54
- **Concern**: Cursor implement normative table omits `_record_implement_timing` and skips step numbering from 1 to 3. Scenario: Current `launch_cursor_implement_main` records timing at ~5223 between meta append and usage; hooks built from this table drop vendor timing entirely
- **Proposed resolution**: Add step 2 `_record_implement_timing("cursor", task_kind, start, output, result.exit_code)` and renumber the remaining steps to match `python/agents.py:5222-5228` and the test fixture at plan.txt:210



### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: plan.txt:31-37
- **Concern**: Cursor CI normative epilogue table truncates at stall; line 149 still claims eight hooks. Scenario: The table lists only meta → timing → usage → TOKEN_RECORD → stall. Current `launch_cursor_ci_main` also runs `_promote_inner_done`, `_append_ci_failure`, and `_emit_ci_launcher_result` after stall (~3713-3715). A hook list built from the five-step table can omit promote/failure/emit and break `.done` promotion plus CI failure IPC.
- **Proposed resolution**: Extend the Cursor CI table with explicit steps 6-8: `_promote_inner_done`, `_append_ci_failure`, `_emit_ci_launcher_result`, matching Codex CI steps 6-8 and current code order.



### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: plan.txt:39-46
- **Concern**: Codex implement normative table omits `_promote_inner_done` between failure append and emit. Scenario: The table jumps from step 5 (failure before promote) to step 7 (emit). `launch_codex_implement_main` calls `_promote_inner_done` at ~5120 between failure and emit. Hook lists derived from this table can skip promote, leaving `.inner.done` unpromoted and breaking `collect_results` wait-on-`.done`.
- **Proposed resolution**: Add step 6 `_promote_inner_done` explicitly; keep failure-before-promote and promote-before-emit ordering already stated at lines 151 and 285.



### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:48-54
- **Concern**: Cursor implement normative table omits `_record_implement_timing`. Scenario: The numbered list goes meta → usage → failure → promote → emit. `launch_cursor_implement_main` records timing at ~5223 between meta and usage. A hook list built from this table can drop timing and desync vendor-task records.
- **Proposed resolution**: Insert `_record_implement_timing` as step 2 between meta append and `_record_cursor_implement_usage`, matching ~5222-5224 and the acceptance bullet at line 285.



### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/agents.py:2391-2395
- **Concern**: `_promote_inner_done` keeps inline `.inner.done`/`.done` suffix literals while `LauncherPaths` becomes the declared single owner. Scenario: The plan routes every promote hook through `_promote_inner_done(paths.output)` but does not migrate that helper to `LauncherPaths` fields. A future suffix tweak in the dataclass can desync promotion from every other migrated sidecar path.
- **Proposed resolution**: Rewrite `_promote_inner_done` to use `LauncherPaths.from_output(output).inner_done` and `.done` (or accept `LauncherPaths` directly); treat this as part of the migration, not call-site-only.



### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: plan.txt:128-145
- **Concern**: [SCOPE-REDUCTION] Hooks-only `_finalize_launch` is a no-op coordinator that adds lambdas without deduplicating launcher tails. Scenario: The proposed helper only iterates caller hooks. Each CI/implement launcher still hand-builds 7-8 closures, so line count and ordering risk stay high while `LauncherPaths` plus `_record_launch_timing` already fix the typo-desync class the issue cites.
- **Proposed resolution**: Prefer minimum-change rollout: land `LauncherPaths`, migrate `run_external_agent` and failure-diag helpers, unify timing via `_record_launch_timing`, and keep sequential epilogue calls. Defer `_finalize_launch` unless a later PR extracts real shared steps beyond `for hook in hooks`.



### FINDING_9:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/agents.py:5118-5121
- **Concern**: Codex implement normative epilogue table omits explicit _promote_inner_done step. Scenario: The per-family table jumps from step 5 (failure append) to step 7 (emit) while current launch_codex_implement_main promotes between them; hook assembly from the incomplete table can skip promote and leave .inner.done unpromoted so collect_results wait-on-.done IPC breaks
- **Proposed resolution**: Add step 6 _promote_inner_done between failure append and _emit_implement_launcher_envelope in the Codex implement normative table and mirror it in the launch_codex_implement_main hook list



### FINDING_10:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/agents.py:5222-5224
- **Concern**: Cursor implement normative epilogue table omits _record_implement_timing. Scenario: The table lists meta then usage (steps 1 and 3) but current launch_cursor_implement_main records timing between meta and usage; acceptance and fixtures say meta → timing → usage and failure modes warn about dropped timing
- **Proposed resolution**: Insert step 2 _record_implement_timing between Append .meta and _record_cursor_implement_usage in the Cursor implement normative table and hook list



### FINDING_11:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: blocking
- **Focus area**: risk-integration
- **Location**: python/agents.py:1747-1750
- **Concern**: run_external_agent stale cleanup contract drops optional stdout_path and stderr_path. Scenario: Plan migrates stale cleanup to LauncherPaths fields plus output only; current run_external_agent also unlinks caller-supplied stdout_path and stderr_path (events.jsonl and sidecar for Codex CI) on retry; omitting them leaves stale partial artifacts across auth retries
- **Proposed resolution**: State explicitly that stale cleanup still adds Path(stdout_path) and Path(stderr_path) when those kwargs are set in addition to LauncherPaths fields; extend the run_external_agent migration test to cover both kwargs



### FINDING_12:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/test_agents.py:2843-2908
- **Concern**: Per-family epilogue order tests lack a no-duplicate-hooks contract. Scenario: Parameterized hook-list tests can pass while launch_*_main wires a different order; the refactor goal is preserving launcher tails not just _finalize_launch iteration
- **Proposed resolution**: Require order fixtures to spy on _promote_inner_done _append_ci_failure _emit_ci_launcher_result _record_implement_timing etc during launch_codex_ci_main launch_cursor_ci_main and implement mains rather than maintaining parallel hook lists only in tests **1. [correctness / blocking]** Codex implement normative table (`plan.txt` lines 39–46) omits `_promote_inner_done`. Current code promotes at ```5118:5121:python/agents.py``` between failure append and emit. Revise the table and hook list to include promote as step 6. **2. [correctness / important]** Cursor implement normative table (`plan.txt` lines 48–54) omits `_record_implement_timing`. Current code records timing at ```5222:5224:python/agents.py``` between meta append and usage. Revise the table to insert timing as step 2. **3. [risk-integration / blocking]** `run_external_agent` stale cleanup at ```1747:1750:python/agents.py``` also removes optional `stdout_path` and `stderr_path`. The plan’s migration test scope (lines 188–192) covers only `LauncherPaths` fields plus `output`. Document and test preservation of conditional `stdout_path`/`stderr_path` cleanup. **4. [risk-integration / important]** Per-family order fixtures (lines 205–210) should verify callee order inside real `launch_*_main` paths (existing CI tests already monkeypatch launchers at ```2843:2908:python/test_agents.py```), not duplicate hook sequences that can drift from production wiring.



### FINDING_13:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:48-54
- **Concern**: Cursor implement normative epilogue table omits `_record_implement_timing`. Scenario: The numbered Cursor implement table jumps from step 1 (meta) to step 3 (usage) with no timing step, while `launch_cursor_implement_main` runs `_record_implement_timing` between meta and usage (`python/agents.py:5222-5224`) and failure modes warn that dropping timing breaks IPC
- **Proposed resolution**: Add step 2 `_record_implement_timing` to the Cursor implement normative table; keep the documented order meta → timing → usage → failure → promote → emit



### FINDING_14:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:39-46
- **Concern**: Codex implement normative epilogue table omits `_promote_inner_done`. Scenario: The Codex implement table numbers steps 1-5 then jumps to step 7 (emit) with no promote step, while code promotes before emit (`python/agents.py:5120-5121`) and acceptance/failure modes require an explicit promote hook between failure append and emit
- **Proposed resolution**: Add step 6 `_promote_inner_done` to the Codex implement normative table between conditional failure append and emit



### FINDING_15:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:31-37
- **Concern**: Cursor CI normative epilogue table stops after stall guard. Scenario: The Cursor CI table lists only steps 1-5 (through stall idempotency) but omits promote, failure append, and emit even though `launch_cursor_ci_main` runs them after stall (`python/agents.py:3713-3715`) and the Codex CI table documents the full 8-step tail
- **Proposed resolution**: Add steps 6-8 to the Cursor CI normative table: `_promote_inner_done`, `_append_ci_failure`, `_emit_ci_launcher_result`, matching the Codex CI tail pattern



