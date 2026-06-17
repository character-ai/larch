### OOS_1: [OUT_OF_SCOPE] correctness: scripts/test-research-structure.sh:247-259
[nit] Planned research-phase pins for terminal NOT_SUBSTANTIVE and synthesis gating were not added. Doc regressions in research-phase synthesis gating may go unnoticed by lint. Add the missing contains pins from the plan.


### OOS_2: [OUT_OF_SCOPE] architecture: python/test_plan_review.py
[nit] Plan regression test for round-summary.env NOT_SUBSTANTIVE counts not implemented. Embedded loop counting could regress without runtime harness detection. Add stubbed collector stdout test asserting COLLECT_FAILURE_COUNT and paths-file omission.


### OOS_3: [OUT_OF_SCOPE] architecture: scripts/test-research-structure.sh
[nit] Missing FINDING_3 synthesis gating pins for research-phase.md. SYNTHESIS_PROMPT doc drift will not fail lint. Add contains pins for STATUS-gated synthesis inputs and dropped-lane markers.


### OOS_4: [OUT_OF_SCOPE] code-quality: python/collect_results.py:621-623
[nit] resolve_collector_stderr_tail_file still references ns-retry stderr tail paths. Dead code only; no functional regression expected. Remove ns-retry tail candidate after confirming no historical artifacts needed.


### OOS_5: [OUT_OF_SCOPE] **Pre-existing dual path:** `python/legacy_review_shell/tally-code-votes.sh:428-436` excludes voters via `voting parse-rate-diag-matches`, not `VOTER_N_PARSE_RATE_STATUS` KVs from dispatch. That still works when diag is written, but diag write is `suppress(OSError)` in `check_voter_parse_rate()` (`python/voting.py:525-526`); a failed diag write could let tally over-count while dispatch reports `NOT_SUBSTANTIVE`.
- **Pre-existing dual path:** `python/legacy_review_shell/tally-code-votes.sh:428-436` excludes voters via `voting parse-rate-diag-matches`, not `VOTER_N_PARSE_RATE_STATUS` KVs from dispatch. That still works when diag is written, but diag write is `suppress(OSError)` in `check_voter_parse_rate()` (`python/voting.py:525-526`); a failed diag write could let tally over-count while dispatch reports `NOT_SUBSTANTIVE`.


### OOS_6: [OUT_OF_SCOPE] **Harness naming drift:** Makefile targets like `test-dispatch-code-voters-retry-claude` (`Makefile:865-866`) still use “retry” labels while asserting classify-only `NOT_SUBSTANTIVE` behavior in `python/test_agent_voters.py`.
- **Harness naming drift:** Makefile targets like `test-dispatch-code-voters-retry-claude` (`Makefile:865-866`) still use “retry” labels while asserting classify-only `NOT_SUBSTANTIVE` behavior in `python/test_agent_voters.py`.


### OOS_7: [OUT_OF_SCOPE] **Test stub dead branch:** `scripts/test-prompt-template-invariants.sh:59-63` still simulates `*parse-retry*` codex output even though classify-only dispatch no longer creates those paths. Harmless for production; stub-only drift.
- **Test stub dead branch:** `scripts/test-prompt-template-invariants.sh:59-63` still simulates `*parse-retry*` codex output even though classify-only dispatch no longer creates those paths. Harmless for production; stub-only drift.


