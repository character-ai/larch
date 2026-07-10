### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/implement/checks_run_relevant.py:72-108
- **Concern**: Missing firm file for ledger-path propagation. Scenario: `FixOutcome` and `LoopResult` are defined here, so `LINT_FIX_TIER_LEDGER_PATH` cannot be carried through the planned result pipeline by changing only `checks_lint_fix.py`.
- **Proposed resolution**: Add `python/larch/implement/checks_run_relevant.py` as an updated file and add the bounded ledger-path fields to both result types.



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/checks_lint_fix.py:1329-1387
- **Concern**: Prior full-lane reservation fix remains incomplete. Scenario: `fixer_lane_budget_sec()` equals exactly one timeout per configured tier. Wall-clock setup and classification overhead can reduce remaining time below one full lane after earlier timeouts, preventing the final configured tier from dispatching despite the complete-waterfall requirement.
- **Proposed resolution**: Specify budget accounting that excludes orchestration overhead or caps each attempt's charged duration at `FIXER_LANE_TIMEOUT_SEC`, and test full-timeout attempts still leave the final configured tier eligible.



### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/implement/checks_run_relevant.py:73-113
- **Concern**: The required tier-ledger path is propagated through `FixOutcome` and `LoopResult`, but the plan does not include the module that defines either dataclass in its firm files. `checks_lint_fix.py` cannot carry `LINT_FIX_TIER_LEDGER_PATH` through the existing repair-loop result without adding fields or changing this contract.. Scenario: A pre-ship exhaustion can write the ledger but lose its path when `_handle_fix_outcome()` reduces `FixOutcome` into `LoopResult`; terminal repair-loop output then cannot expose the required authoritative evidence pointer.
- **Proposed resolution**: Add `python/larch/implement/checks_run_relevant.py` to the plan and specify the new bounded ledger-path fields on both result types, their propagation, and terminal emission.



### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/checks_lint_fix.py:1570-1605
- **Concern**: The plan remaps named pre-ship exhaustion via `_repair_loop_action()` but does not wire `FixOutcome.failure_reason` through `_handle_fix_outcome()` into durable loop state. Scenario: `_handle_fix_outcome()` collapses every `status="failed"` (except head-changed) to `loop.status="dispatch-failed"` and drops `failure_reason`; `_repair_loop_action()` only reads `loop.status`, so pre-ship exhaustion cannot be distinguished from other failures and may still route to `main-agent-edit` via stale `exhausted`/`no-changes-stale` ledger paths or mis-stall structural cases
- **Proposed resolution**: Add `last_failure_reason` (and tier-ledger path) to `LoopResult`, set them in `_handle_fix_outcome()`, and make `_repair_loop_action()` branch on an explicit pre-ship allowlist of named non-structural exhaustion reasons vs structural routes



### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/checks_run_relevant.py:73-108
- **Concern**: Plan-mandated tier-ledger and terminal-reason propagation require updating shared outcome dataclasses, but `checks_run_relevant.py` is not listed under Files to modify/create. Scenario: The plan says propagate the tier ledger through `FixOutcome` and repair-loop handling, yet `FixOutcome`/`LoopResult` live in `checks_run_relevant.py` with no `tier_ledger_path` or terminal `failure_reason` fields; implementers may add ad-hoc side channels or skip propagation
- **Proposed resolution**: Add `### UPDATED: python/larch/implement/checks_run_relevant.py` extending `FixOutcome`/`LoopResult` with bounded `tier_ledger_path` and terminal routing fields consumed by `checks_lint_fix.py` and tests



### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/checks_lint_fix.py:456-464
- **Concern**: Terminal pre-ship stall output must emit `LINT_FIX_TIER_LEDGER_PATH`, but the plan does not require updating `checks_repair_loop_main()` stdout emission. Scenario: Today `_print_loop_ledger()` runs only when `action == "main-agent-edit"`; pre-ship exhaustion will return `NEXT_ACTION=stall`, so tier-attempt evidence never reaches repair-loop stdout despite the documented `LINT_FIX_TIER_LEDGER_PATH` contract
- **Proposed resolution**: In `checks_repair_loop_main()`, emit `LINT_FIX_TIER_LEDGER_PATH` (and bounded tier-ledger metadata) on pre-ship `NEXT_ACTION=stall`; keep escalation `LINT_FIX_LEDGER_*` keys structural-only



### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: skills/implement/references/checks-repair-loop.md:90-101
- **Concern**: Rewriting stall routing risks dropping the Step 5 MAV/coder durable-bail exception. Scenario: The plan updates pre-ship stall semantics but only says to preserve pinned launcher contracts; it does not explicitly retain the existing rule that `step5-mav`/`coder-main-agent-required` terminal repair-loop stalls must not skip directly to Step 18 and must run the `--record-only` + Durable Bail path
- **Proposed resolution**: A explicit preserve directive: keep the Step 5 MAV/coder `NEXT_ACTION=stall` durable-bail paragraph unchanged when editing section 4; add a structure-test needle requiring it



### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/checks_lint_fix.py:258-282
- **Concern**: Named exhaustion tokens are unspecified, so `_repair_loop_action()` allowlists cannot be implemented consistently. Scenario: The plan uses prose like "named delegated-waterfall exhaustion reason" while Piece 1 already defines `config.FIXER_TIER_FAIL_REASON_UNAVAILABLE` / `FIXER_TIER_FAIL_REASON_EXHAUSTED` and current code uses ad-hoc strings such as `lint-fix-budget-exceeded`; ambiguous names invite wrong stall vs structural routing
- **Proposed resolution**: Pin the exact pre-ship non-structural terminal `failure_reason` set (at minimum the two `FIXER_TIER_FAIL_REASON_*` constants plus one budget-reservation token) and require `_repair_loop_action()` to match only that set for pre-ship stall



### FINDING_9:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/implement/checks_lint_fix.py:685-703
- **Concern**: [SCOPE-REDUCTION] Per-tier content baselines should reuse existing digest capture instead of new parallel machinery. Scenario: The plan requires content-aware dirty-path detection, but `_delta_paths_after_dispatch()` compares path membership only; adding a second bespoke digest scheme duplicates `dispatch_helpers._write_prelaunch_digests()` already used for pre-dispatch content snapshots
- **Proposed resolution**: Reuse or factor the existing SHA-256 digest helper for per-tier pre/post snapshots on already-dirty tracked and untracked paths; treat content hash change as useful delta



### FINDING_10:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/checks_run_relevant.py:73-108
- **Concern**: The plan does not include the result-model changes needed to propagate the new terminal reason and tier-ledger path. Scenario: `_run_lint_fix_impl` can return a named exhaustion `FixOutcome`, but `_handle_fix_outcome` currently collapses failed outcomes to `dispatch-failed` and `LoopResult` has no failure-reason or tier-ledger-path field; `_repair_loop_action` therefore cannot distinguish named non-structural exhaustion from structural failure, and terminal output cannot expose `LINT_FIX_TIER_LEDGER_PATH`
- **Proposed resolution**: Include the shared result-model file in the plan, or define an equivalent propagation mechanism. Add fields for the terminal failure reason and tier-ledger path to `FixOutcome` and `LoopResult`, copy them in `_handle_fix_outcome`, and use the reason in `_repair_loop_action` while emitting the path in the repair-loop envelope



### FINDING_11:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/implement/checks_run_relevant.py:72-108
- **Concern**: Plan requires propagating tier-ledger and terminal exhaustion evidence through FixOutcome/LoopResult but omits this firm file. Scenario: FixOutcome and LoopResult live in checks_run_relevant.py; the plan only lists checks_lint_fix.py. Without adding fields such as tier_ledger_path and a retained terminal failure_reason, checks_repair_loop_main cannot emit LINT_FIX_TIER_LEDGER_PATH or FAILURE_REASON on pre-ship stall as specified
- **Proposed resolution**: Add ### UPDATED: python/larch/implement/checks_run_relevant.py with tier_ledger_path on FixOutcome, terminal failure_reason on LoopResult, and _handle_fix_outcome/_repair_loop_action wiring that preserves them through repair-loop stdout



### FINDING_12:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/checks_lint_fix.py:1331-1406
- **Concern**: Recoverable no-useful-delta tiers need explicit pre-attempt repository restore before the next dispatch. Scenario: The plan captures per-attempt baselines and continues after timeout, launcher failure, and no-op tiers, but never requires restoring HEAD/index/worktree/untracked content to that attempt baseline when useful_delta is false. Leftover partial edits from a timed-out or failed tier pollute later tiers and can cause false useful-delta detection or wrong exhaustion/stall outcomes
- **Proposed resolution**: After classifying a recoverable tier as no useful delta, restore the captured pre-dispatch snapshot (tracked, index, untracked, HEAD) before calling next_untried_tier(); keep fail-closed behavior for structural/forbidden/integrity failures without silent acceptance



### FINDING_13:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/implement/checks_lint_fix.py:450-464
- **Concern**: Terminal pre-ship stall must surface the named exhaustion FAILURE_REASON in repair-loop stdout. Scenario: checks-repair-loop.md stall routing binds IMPLEMENT_BAIL_REASON from composite FAILURE_REASON, but checks_repair_loop_main today prints only NEXT_ACTION and LOOP_STATUS on stall and LoopResult stores no failure_reason. Remapping pre-ship exhaustion from main-agent-required to failed/stall drops the named reason unless explicitly propagated
- **Proposed resolution**: Extend LoopResult/checks_repair_loop_main to print FAILURE_REASON=<named non-structural token> on pre-ship stall alongside LINT_FIX_TIER_LEDGER_PATH; add regression tests that stall envelopes carry the exhaustion token for step3/step6 and step5-mav durable-bail paths



### FINDING_14:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: skills/implement/references/checks-repair-loop.md:90-101
- **Concern**: Site-routing rewrite must preserve the step5-mav/coder durable-bail exception when step5* exhaustion becomes stall. Scenario: The plan routes all pre-ship step5* non-structural exhaustion to NEXT_ACTION=stall. Current reference text exempts step5-mav and coder-main-agent-required terminal stalls from generic Step 18 routing. A generic step5* stall table can drop that override and send MAV/coder exhaustion to Step 18 instead of the existing durable-bail/resume path
- **Proposed resolution**: In the new site-routing table, list step5-mav and coder paths separately: stall remains the repair-loop action, but orchestrator handling stays the existing durable-bail paragraph; add a structure-harness assertion that this override survives the exhausted-to-stall remap



### FINDING_15:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/implement/checks_lint_fix.py:258-282
- **Concern**: Pin the non-structural exhaustion whitelist to Piece 1 config tokens in _repair_loop_action. Scenario: The plan uses unnamed delegated-waterfall exhaustion reasons. Piece 1 already defines config.FIXER_TIER_FAIL_REASON_UNAVAILABLE, config.FIXER_TIER_FAIL_REASON_EXHAUSTED, and the existing lint-fix-budget-exceeded token. Ad hoc strings can miss the stall branch and leak back to main-agent-edit or misclassify ship-pr handoffs
- **Proposed resolution**: Document and implement an explicit pre-ship non-structural set {unavailable, exhausted, lint-fix-budget-exceeded} mapped to stall; reserve main-agent-edit for structural fast-fail reasons and ship-pr-ci-* site-gated handoffs only



### FINDING_16:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/implement/checks_run_relevant.py:73-105
- **Concern**: The plan requires propagating `LINT_FIX_TIER_LEDGER_PATH` through `FixOutcome` and `LoopResult`, but omits the file that defines both data contracts.. Scenario: Implementation either cannot pass the new field through the frozen `FixOutcome`, loses the pointer before terminal repair-loop output, or adds an unplanned workaround in `checks_lint_fix.py`.
- **Proposed resolution**: Add `### UPDATED: python/larch/implement/checks_run_relevant.py` with the minimal ledger-path fields on `FixOutcome` and `LoopResult`; copy the value in existing outcome reduction without changing other callers.



### FINDING_17:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/implement/checks_run_relevant.py:72-108
- **Concern**: The plan adds tier-ledger propagation through FixOutcome and repair-loop output but omits checks_run_relevant.py from firm file headings even though FixOutcome and LoopResult live there. Without new fields (for example tier_ledger_path) and _handle_fix_outcome copying them onto LoopResult, checks_repair_loop_main cannot emit LINT_FIX_TIER_LEDGER_PATH on pre-ship stall and per-tier evidence is dropped at the repair-loop boundary.. Scenario: Add tier_ledger_path (or equivalent) to FixOutcome and LoopResult in checks_run_relevant.py; update _handle_fix_outcome and checks_repair_loop_main to print LINT_FIX_TIER_LEDGER_PATH on terminal pre-ship stall, not only on main-agent-edit.
- **Proposed resolution**: 



### FINDING_18:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/checks_lint_fix.py:1298-1300
- **Concern**: The waterfall refactor dispatches multiple tiers inside one run_lint_fix call but the plan never requires per-attempt run/log isolation. Today a single mkdtemp run_dir holds claude-lint-fix.txt, codex.log, and cursor.log for the whole invocation; a second tier overwrites the first tier's artifacts and stderr tails.. Scenario: Multi-tier pre-ship runs can record the wrong tier in lint-fix-tier-ledger.tsv, attach the wrong redacted log to execution-issue rows, and misclassify recoverable failures after timeout or auth/preflight failure.
- **Proposed resolution**: Create a fresh per-attempt run_dir (or sequence-suffixed log paths) for every dispatched tier; bind ledger rows and execution-issue pointers to that attempt's artifacts.



### FINDING_19:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/implement/checks_lint_fix.py:1388-1390
- **Concern**: The plan uses placeholder named exhaustion reasons but does not pin them to the Piece 1 selectors already in config (FIXER_TIER_FAIL_REASON_UNAVAILABLE, FIXER_TIER_FAIL_REASON_EXHAUSTED) plus an explicit budget-exhausted token such as lint-fix-budget-exceeded. _repair_loop_action site routing and the replacement tests need a closed vocabulary.. Scenario: Divergent failure_reason strings between next_untried_tier(), FixOutcome, _repair_loop_action, and tests can leave some pre-ship exhaustion paths still mapping to dispatch-failed or main-agent-required, or fail the new regression assertions.
- **Proposed resolution**: Document the exact terminal failure_reason set in the plan and use only those constants in run_lint_fix returns and _repair_loop_action pre-ship stall routing.



### FINDING_20:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/checks_lint_fix.py:planned budget loop
- **Concern**: Accepted FINDING_7 remains incomplete: the exact `tier_count * FIXER_LANE_TIMEOUT_SEC` budget cannot reserve a full timeout for every tier when validation, state capture, ledger writes, and dispatch overhead count against elapsed wall time. Scenario: The first two tiers can each consume their 1800-second allowance plus small orchestration overhead. Less than 1800 seconds then remains, so the final configured tier is never dispatched even though acceptance requires a complete waterfall with a full timeout per tier
- **Proposed resolution**: Define budget accounting that excludes between-tier orchestration overhead from lane consumption, or provide bounded overhead headroom while preserving the full-lane pre-dispatch reservation. Add the planned final-tier test with prior tiers consuming their full timeout plus realistic overhead



