### OOS_1: [OUT_OF_SCOPE] correctness
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 1. **correctness** `scripts/ship-pr.sh` — Items 4–5 from the combined OOS issue (`LAUNCHER_EXIT` fail-open in bash, missing `run_checks_with_lint_fix_loop` wrapper test) are not addressed on this branch. The plan explicitly defers them to the Python port. The bash path may still exhibit the #4161/#4159 behavior when `LARCH_SHIP_PR_IMPL=bash`. Not introduced by this diff.
- **Suggested revision**: Address the concern above.


### OOS_2: [OUT_OF_SCOPE] code-quality
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 5. **code-quality** `scripts/ship-pr.sh` (unchanged) — Plan correctly notes Python `agents.resolve_launcher_exit` already fails closed; bash `${launcher_exit:-0}` default-on-missing-KV remains a pre-existing gap when `LARCH_SHIP_PR_IMPL=bash`. Not introduced by this branch.
- **Suggested revision**: Address the concern above.


### OOS_3: correctness: python/plan_scout.py:456-483
- **Reviewer**: codex-specialist-edge-cases-output.txt
- **Concern**: [important] Only the cap-hit sidecar is cleared, leaving stale raw JSON eligible for reuse. A previous run leaves valid manifest.json.raw plus manifest.json.raw.cap-hit; the next launcher exits 0 without rewriting raw; after unlinking cap-hit, _raw_is_scout_json accepts old archetypes for the new diff. Delete or truncate raw together with cap_hit before each tier launch, or use fresh tier-specific raw paths and promote only the current validated output.
- **Suggested revision**: Address the concern above.


### OOS_4: [OUT_OF_SCOPE] correctness: scripts/ship-pr.sh:1720-1721
- **Reviewer**: codex-specialist-edge-cases-output.txt
- **Concern**: [important] Missing LAUNCHER_EXIT still defaults to 0 in unchanged bash ship-pr paths. A launcher wrapper can exit nonzero without emitting LAUNCHER_EXIT, and the bash fallback can treat launcher_exit as success. Mirror agents.resolve_launcher_exit semantics: prefer sidecar, then stdout, then fail closed to at least 1 on nonzero wrapper exit.
- **Suggested revision**: Address the concern above.


### OOS_5: [OUT_OF_SCOPE] risk-integration: scripts/test-ship-pr-rebase.sh:183-187
- **Reviewer**: codex-specialist-edge-cases-output.txt
- **Concern**: [nit] The lint-handoff runtime test still bypasses run_checks_with_lint_fix_loop and duplicates its handoff behavior inline. A regression that removes or reorders the wrapper-level handoff can pass because the test manually emits the ledger path after run_captured_cmd_then_fix_loop. Add an end-to-end wrapper test that calls run_checks_with_lint_fix_loop with narrow stubs and asserts SHIP_PR_LEDGER_* output.
- **Suggested revision**: Address the concern above.


### OOS_6: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 1. **risk-integration** `feature_description:items-4-5` — Combined issue #4206–#4207 still lists ship-pr `LAUNCHER_EXIT` fail-open (item 4) and `run_checks_with_lint_fix_loop` harness coverage (item 5). The implementation plan defers both (“Python port already correct”). `scripts/ship-pr.sh` still uses `${launcher_exit:-0}` at ~1721, 2494, 2877. **Why OOS:** Plan non-goal; pre-existing bash behavior, not introduced or worsened by this diff.
- **Suggested revision**: Address the concern above.


