### FINDING_1: Preserve absent voter-path semantics
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Requirements, Codex-dyn-Dispatch Contract Auditor
- **Severity**: major
- **Concern**: Converting empty skipped or failed voter paths to `Path("")` produces `"."`, changing existing empty `VOTER_*_PATH` values and potentially corrupting paths-file and file-check behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Code-review skipped/unlaunched slots bind to "" and tests assert VOTER_2_PATH= empty; plan-review skipped slots bind to canonical output paths under the tmpdir. Blind Path(path) or Path("") becomes "." and emits VOTER_N_PATH=. or mis-fires _file_nonempty, breaking test_both_externals_down_shrink_not_backfill and downstream KV consumers Document in dispatch_shared.py that binding stays family-local; for code-review keep absent/skipped paths as None or "" until the KV/subprocess boundary; add a shared str-path-for-kv helper; forbid Path("") for skipped slots
  - From Codex-Arch: Use Path | None for absent paths, normalize None to an empty wire value, skip None in file checks and paths-file writing, and test the all-failed and skipped cases
  - From Cursor-Innovation: Keep _state_from_bindings family-local and add an explicit edge-case row: skipped or failed slots retain each family’s current placeholder-path contract after Path migration
  - From Codex-Innovation: Use Path | None for absent paths and serialize None as an empty string at CLI, paths-file, done-sidecar, and KV boundaries. Add a skipped-voter regression assertion.
  - From Cursor-Pragmatic: Keep absent/skipped slot paths as an explicit empty-string sentinel in shared state (or Optional[Path] with None); at subprocess/KV boundaries emit "" unchanged. Add a regression test in python/tests/review/test_dispatch_shared.py for skipped-slot empty paths.
  - From Codex-Requirements: Allow `Path | None` or an explicit blank sentinel, and serialize absent paths as empty strings at wire boundaries
  - From Codex-dyn-Dispatch Contract Auditor: Use Path | None for absent paths and serialize None as an empty wire value; test skipped and failed slots


### FINDING_2: Retain plan-review helper aliases
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Requirements, Cursor-dyn-Dispatch Contract Auditor, Codex-dyn-Dispatch Contract Auditor
- **Severity**: major
- **Concern**: Moving calibration and parse-rate helpers into `dispatch_shared` without module-level plan-review facades breaks unchanged tests and monkeypatch seams.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add to plan_review_panel UPDATED: keep thin module-level wrappers/re-exports for _parse_rate_retry and _fresh_calibration_stats_file (same pattern as agent_voters)
  - From Cursor-Innovation: In plan_review_panel.py UPDATED, require thin module-level facades that keep the current signatures (design= vs review_tmpdir=) and delegate to dispatch_shared; mirror the agent_voters alias rule for every helper those tests monkeypatch or call
  - From Cursor-Requirements: In `### UPDATED: python/larch/review/plan_review_panel.py`, keep thin `_fresh_calibration_stats_file` and `_parse_rate_retry` wrappers that build family-specific argv and delegate validation or snapshot work to `dispatch_shared`, mirroring the alias-retention rule already stated for `agent_voters.py`
  - From Cursor-dyn-Dispatch Contract Auditor: Match agent_voters.py: add plan_review_panel re-exports/aliases for _parse_rate_retry, _fresh_calibration_stats_file, and any other moved symbols tests patch
  - From Codex-dyn-Dispatch Contract Auditor: Retain module-level adapter aliases for calibration and parse-rate helpers, and route them through injected shared runners


### FINDING_3: Preserve quiet contract-stream emission
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: major
- **Concern**: A shared emitter that uses `print()` can bypass `quiet_init`’s fd 3 contract stream and lose `VOTER_*` output from production dispatch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Specify the shared emitter writes voter-status-block stdout plus DISPATCH_OK through logging_util.emit/emit_kv (contract stream safe); plan_review may keep print or adopt the same helper; add one dispatch_voters_main-path assertion or document that gap
  - From Cursor-Pragmatic: In dispatch_shared, forward each voter-status-block output line through logging_util.emit (splitlines, preserve order). Keep DISPATCH_OK as emit_kv. Add a quiet-routing regression test that asserts captured contract output contains VOTER_1_PATH=.


### FINDING_5: Update the voter-status-block test harness
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Concern**: Routing agent-voter output through `voting.voter_status_block` requires a corresponding `FakeHarness.run` branch; otherwise the unchanged agent-voter suite fails.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Either add ### MAY_UPDATE: python/tests/agents/test_agent_voters.py with a minimal FakeHarness branch for ("voting","voter-status-block") mirroring python/tests/review/test_voting.py, or relax acceptance to allow that stub-only change. test_dispatch_shared.py alone cannot satisfy the unchanged integration suite.


### FINDING_6: Preserve plan-review Codex role resolution
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-dyn-Dispatch Contract Auditor
- **Severity**: major
- **Concern**: Topology `slot_defaults.model_role` does not capture plan-review’s difficulty- and archetype-dependent Codex role overrides, so topology-only shared builders can resolve incorrect models.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Limit shared panel builders to attribution helpers, or require an injected model_role resolver (topology key + archetype + tier) for Codex rows. Keep difficulty.codex_review_model_role_for_archetype in plan_review_panel when building static/generic/dynamic rows.
  - From Cursor-dyn-Dispatch Contract Auditor: Keep static/generic/dynamic render orchestration in plan_review_panel.py; limit shared builders to attribution helpers and require an injected role resolver (tier + archetype) for design.plan_review_panel Codex rows


### FINDING_7: Preserve code-review paths-file emission
- **Reviewer(s)**: Cursor-dyn-Dispatch Contract Auditor
- **Severity**: major
- **Concern**: Unifying final emission through `voter_status_block_main` may suppress `VOTER_PATHS_FILE` when the paths file is missing or empty, changing code-review’s existing always-emit behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-Dispatch Contract Auditor: Document the code-review paths-file non-empty invariant in the shared emitter contract, or add an explicit family flag so code-review keeps always-emit behavior while plan-review keeps the path gate


### FINDING_10:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/review/dispatch_shared.py:new final-KV emitter
- **Concern**: [SCOPE-REDUCTION] The planned extra CLI subprocess can silently drop the required voter KVs. Scenario: The unchanged agent-voter harness returns rc=2 for `voter-status-block`; the emitter then prints only `DISPATCH_OK`. A production subprocess failure creates the same false-success wire break.
- **Proposed resolution**: Call `voting.voter_status_block_main` in-process, or directly serialize its exact gated rows, then emit `DISPATCH_OK`; remove the subprocess-specific test requirement.


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

