# Review Round 1

- Mode: `diff`
- 3 accepted, 4 rejected (1 neutral)

## Accepted Findings

### FINDING_1: review-core branch matrix and golden stdout-order tests missing
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan-required direct `_review_core_body` tests and golden full-line `_emit_review_core_result` stdout-order coverage are largely absent across review-core branches (e.g. description-empty, dispatch failure, prune-skipped, proposer-map-failed, validation-exhausted, main-agent-vote-required, cap-reached, pre/post-voter tally-fail, aggregate-zero second zero-findings path). Row-order or segment-drop regressions can pass substring/key-presence integration tests while breaking `review_core_capture`, shell parsers, and Step 5 KV consumers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Add parametrized tests that emit ReviewCoreResult per branch recipe and assert the complete stdout line sequence
  - From cursor-specialist-testing-output.txt: Add _review_core_body test with TEST_FINDINGS=1 and REVIEW_CORE_AGGREGATE_FINDINGS_SH pointing at aggregate_zero; assert result.rows ordering
  - From cursor-specialist-testing-output.txt: Stub aggregate-exhausted plus failing tally for pre-voter path and voter dispatch plus failing tally for post-voter path; assert result.rows directly
  - From cursor-specialist-testing-output.txt: Add direct _review_core_body tests and golden emit tests for both branches per the plan row-order table
  - From codex-specialist-testing-output.txt: Add the required _review_core_body row assertions and _emit_review_core_result or wrapper golden stdout-order tests for each listed branch.


### FINDING_2: postplan decide and executor test coverage incomplete
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-dyn-postplan-purity-output.txt
- **Severity**: important
- **Concern**: `python/test_design_lifecycle.py` adds partial `_postplan_decide` coverage (chiefly rc `0`/`10`) but omits plan-required decide tests for rc `11`, `12`, `13`, and fatal rc, plus executor golden `stdout_lines` parity (`captured + "".join(decision.rows)`), pre-emit pause without emit, non-`step2b` preamble scout-clear, and post-emit rc `11` boundaries. Join-semantics, pause-order, or fatal duplicate-print regressions can pass decide-only or substring end-to-end tests while breaking `/design` Gate B and drafter wrapper parsers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Add executor tests stubbing postplan_emit_main that compare PostplanResult.stdout_lines byte-for-byte and assert _clear_scout_manifests behavior per site
  - From dyn-dyn-postplan-purity-output.txt: Add decide unit tests for rc `11`/`12`/`13`/fatal metadata, executor tests that fail if `postplan_emit_main` runs on pre-emit `.pause-requested`, a non-`step2b` scout-clear assertion, and golden full-string comparisons for rc `0`/`10` inline-retry/`12`/`13`/post-emit `11`.


### FINDING_5: ship helper boundary tests missing for phase14, postmerge, and caller paths
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, dyn-dyn-ship-state-output.txt
- **Severity**: important
- **Concern**: Ship helper extraction adds durable-state paths in `_ship_rebase_phase`, `_ship_phase14_rebase`, and `_ship_postmerge_phase`, but focused helper-boundary tests are missing for phase14 success `phase=ci-initial` writes, postmerge done-only-on-`Outcome.OK`, resume `merged` caller-owned `phase=postmerge` pre-write, and `main_advanced` follow-up `ci-initial` writes omitting monitor-head fields. Regressions inside helpers can change stall ordering, iteration ownership, or handoff-field clearing while broad `run_ship` tests still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From dyn-dyn-ship-state-output.txt: Add the plan-specified helper-level tests that call `_ship_phase14_rebase` and `_ship_postmerge_phase` directly (with stubbed runner/deps), assert the exact `ship-pr-state.sh` key set after each helper returns, and add a small `run_ship` `MERGE_RESULT_MAIN_ADVANCED` test that verifies the post-helper `ci-initial` write does not pass monitor-head fields.


