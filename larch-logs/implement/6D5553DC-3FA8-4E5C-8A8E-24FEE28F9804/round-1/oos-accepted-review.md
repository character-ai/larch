### OOS_1: correctness: python/review_pipeline.py:1829-1947
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] review_core ignores gather_result and collect_result return codes When gather-branch-context or collect-findings fails, the round continues with empty or partial artifacts instead of aborting like bash set -e Check returncode after gather and collect; fail closed with panel-failed or propagate the child exit code
- **Suggested revision**: Address the concern above.


### OOS_2: risk-integration: python/review_pipeline.py:1931-1943
- **Reviewer**: codex-specialist-edge-cases-output.txt
- **Concern**: [important] Dirty-tree recovery was dropped from review_core after reviewer output collection. A reviewer leaves tracked or untracked changes and a dirty sidecar; collect_findings emits DIRTY_DETECTED=true, but review_core ignores it and later apply or commit steps can include reviewer mutations. Port and call the old recover_dirty_tree flow after collection, including dirty or unknown sidecars and dropped static outputs.
- **Suggested revision**: Address the concern above.


### OOS_3: correctness: python/review_pipeline.py:1931-1934
- **Reviewer**: codex-specialist-edge-cases-output.txt
- **Concern**: [important] review_core ignores non-zero collect-findings results. agent collect-results fails or Claude waiting times out after partial stdout; the round continues with missing FINDINGS_COUNT and can report a misleading zero-findings or success-like status. Check collect_result.returncode immediately, persist sidecars and logs, then fail the round or propagate the non-zero result before threshold and tally work.
- **Suggested revision**: Address the concern above.


### OOS_4: correctness: python/review_pipeline.py:1692-1743
- **Reviewer**: codex-specialist-edge-cases-output.txt
- **Concern**: [important] Zero-findings rounds no longer record reviewer-prune ledger history. Rounds 1 and 2 both produce zero accepted findings, but no ledger rows are written, so round 3 pruning has no two-round zero history and relaunches reviewers that should be pruned. Pass prune_ledger into _zero_findings_branch and call _record_prune_round after _record_classification.
- **Suggested revision**: Address the concern above.


### OOS_5: security: python/review_pipeline.py:727-732
- **Reviewer**: codex-specialist-edge-cases-output.txt
- **Concern**: [important] Dynamic scout fields are embedded raw without the prior redaction and escaping. A scout manifest contains tag-like prompt injection text or secret-like content; the generated reviewer prompt stores it as active-looking markup instead of inert escaped data. Redact and escape untrusted scout fields before embedding them, including at least <, >, and &, while keeping delimiter validation.
- **Suggested revision**: Address the concern above.


### OOS_6: risk-integration: python/test_review_pipeline.py:471-509
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Deleted reviewer-prune shell harness scenarios not ported to pytest Label-map mode fail-open off-switch or PRUNED_COMBOS regressions pass make test-reviewer-prune and break rounds 3-4 pruning in /design and /review Port deleted scripts/test-reviewer-prune.sh cases into focused pytest and keep make test-reviewer-prune pinned to them
- **Suggested revision**: Address the concern above.


### OOS_7: correctness: python/review_pipeline.py:1741-1743
- **Reviewer**: codex-specialist-testing-output.txt
- **Concern**: [important] Zero-findings rounds are not recorded into the reviewer prune ledger. After rounds 1 and 2 both produce zero findings, round 3 lacks the two zero-count ledger rows needed to prune zero-yield reviewer combos. Pass prune_ledger into _zero_findings_branch and call _record_prune_round after _record_classification.
- **Suggested revision**: Address the concern above.


### OOS_8: correctness: python/review_pipeline.py:1329-1373
- **Reviewer**: codex-specialist-testing-output.txt
- **Concern**: [important] Dirty reviewer sidecars are detected but reviewer-created worktree changes are no longer recovered. A reviewer leaves tracked or untracked changes behind, review core continues, and later implementation steps see polluted state. Port and call the old recover_dirty_tree flow after collection and before thresholding.
- **Suggested revision**: Address the concern above.


### OOS_9: correctness: python/review_pipeline.py:1741-1742
- **Reviewer**: codex-specialist-correctness-output.txt
- **Concern**: [important] Zero-finding rounds do not record reviewer-prune ledger rows. Rounds 1 and 2 with zero accepted findings leave the ledger empty, so round 3 does not prune combos that should have two zero-count rounds. Call _record_prune_round in _zero_findings_branch after _record_classification.
- **Suggested revision**: Address the concern above.


### OOS_10: correctness: python/review_pipeline.py:1931-1934
- **Reviewer**: codex-specialist-testing-output.txt
- **Concern**: [important] review_core ignores a non-zero collect-findings result. A timed-out reviewer with parseable raw output can lead to REVIEW_CORE_STATUS=zero-findings instead of a failed review round. Check collect_result.returncode and stop with a failed review status before threshold, tally, or zero-findings handling.
- **Suggested revision**: Address the concern above.


### OOS_11: **correctness** `python/review_pipeline.py:1930-1943` — The ported `review_core` drops the post-collect dirty-tree recovery that lived in deleted `python/legacy_review_shell/review-core.sh`. After `collect-findings`, the old script called `collect_dropped_static_outputs`, then `recover_dirty_tree` on external, Claude, and dropped-static outputs. That path ran `dirty-tree checkpoint`, discarded reviewer-introduced paths from sidecars, and wrote `review-dirty-tree-summary.env` (see `skills/review/references/heavy-worker.md`). The Python `review_core` goes straight from collect to the failure-threshold gate with no equivalent, so reviewer dirt can remain in the worktree and the summary artifact is never produced. **Suggested fix:** Port `collect_dropped_static_outputs`, `recover_dirty_tree`, and `log_dropped_slots` into `review_pipeline.py` (or shared helpers), invoke them immediately after a successful `collect-findings` call in `review_core`, and add pytest coverage for dirty/unknown sidecars plus dropped-slot outputs.
- **Reviewer**: dyn-pipeline-contracts-output.txt
- **Concern**: - **correctness** `python/review_pipeline.py:1930-1943` — The ported `review_core` drops the post-collect dirty-tree recovery that lived in deleted `python/legacy_review_shell/review-core.sh`. After `collect-findings`, the old script called `collect_dropped_static_outputs`, then `recover_dirty_tree` on external, Claude, and dropped-static outputs. That path ran `dirty-tree checkpoint`, discarded reviewer-introduced paths from sidecars, and wrote `review-dirty-tree-summary.env` (see `skills/review/references/heavy-worker.md`). The Python `review_core` goes straight from collect to the failure-threshold gate with no equivalent, so reviewer dirt can remain in the worktree and the summary artifact is never produced. **Suggested fix:** Port `collect_dropped_static_outputs`, `recover_dirty_tree`, and `log_dropped_slots` into `review_pipeline.py` (or shared helpers), invoke them immediately after a successful `collect-findings` call in `review_core`, and add pytest coverage for dirty/unknown sidecars plus dropped-slot outputs.
- **Suggested revision**: Address the concern above.


### OOS_12: **correctness** `python/review_pipeline.py:1931-1949` — `review_core` ignores `collect_result.returncode`. Deleted `review-core.sh` ran under `set -euo pipefail`, so a non-zero exit from `collect-findings` (collector failure, wait timeout, etc.) aborted the round. The Python path always parses stdout and continues into threshold/coverage logic, which can misclassify a failed collect as a normal round and emit misleading `REVIEW_CORE_STATUS` values. **Suggested fix:** After `collect_result` returns, fail closed when `returncode != 0` (mirror bash: write `review-core-collect.env`, ensure prune sidecars, flush round log, emit `panel-failed` or propagate the collect exit code) before running `check_reviewer-failure-threshold`.
- **Reviewer**: dyn-pipeline-contracts-output.txt
- **Concern**: - **correctness** `python/review_pipeline.py:1931-1949` — `review_core` ignores `collect_result.returncode`. Deleted `review-core.sh` ran under `set -euo pipefail`, so a non-zero exit from `collect-findings` (collector failure, wait timeout, etc.) aborted the round. The Python path always parses stdout and continues into threshold/coverage logic, which can misclassify a failed collect as a normal round and emit misleading `REVIEW_CORE_STATUS` values. **Suggested fix:** After `collect_result` returns, fail closed when `returncode != 0` (mirror bash: write `review-core-collect.env`, ensure prune sidecars, flush round log, emit `panel-failed` or propagate the collect exit code) before running `check_reviewer-failure-threshold`.
- **Suggested revision**: Address the concern above.


### OOS_13: **correctness** `python/review_pipeline.py:1329-1333` — `collect_findings` narrows `DIRTY_DETECTED` versus deleted `python/legacy_review_shell/collect-findings.sh`. Bash set `DIRTY_DETECTED=true` when a sidecar was missing/empty or did not contain `STATUS=clean`. Python only sets it when `STATUS` is exactly `dirty`, so missing sidecars and `STATUS=unknown` now report `DIRTY_DETECTED=false`. That breaks KV parity with the retired contract and with the plan’s dirty-sidecar edge case. **Suggested fix:** Restore bash semantics: treat a missing/empty sidecar or any status other than `clean` as dirty (`unknown` included), and add pytest cases for missing, `unknown`, `clean`, and `dirty` sidecars.
- **Reviewer**: dyn-pipeline-contracts-output.txt
- **Concern**: - **correctness** `python/review_pipeline.py:1329-1333` — `collect_findings` narrows `DIRTY_DETECTED` versus deleted `python/legacy_review_shell/collect-findings.sh`. Bash set `DIRTY_DETECTED=true` when a sidecar was missing/empty or did not contain `STATUS=clean`. Python only sets it when `STATUS` is exactly `dirty`, so missing sidecars and `STATUS=unknown` now report `DIRTY_DETECTED=false`. That breaks KV parity with the retired contract and with the plan’s dirty-sidecar edge case. **Suggested fix:** Restore bash semantics: treat a missing/empty sidecar or any status other than `clean` as dirty (`unknown` included), and add pytest cases for missing, `unknown`, `clean`, and `dirty` sidecars.
- **Suggested revision**: Address the concern above.


### OOS_14: **risk-integration** `Makefile:68-70` — `test-lib-prune-decision` now runs `pytest -k prune`, but the deleted `scripts/test-lib-prune-decision.sh` covered the `derive_prune_status` matrix and `ensure_reviewer_prune_ledger` repair paths. The five collected prune tests exercise prune-nits and `reviewer-prune` record/filter only; none assert `derive_prune_status`, `normalize_prune_eligible`, `prune_window_evaluated`, `write_prune_decision_env`, or `ensure_reviewer_prune_ledger`. Embedded plan-review assets still depend on shell copies of the first three helpers in `python/plan_review.py:833-876`, so rounds 3–4 prune-status and ledger repair can regress without CI signal. **Suggested fix:** Add focused pytest for the Python helpers (mirroring the deleted harness cases) and either test the inlined shell copies or route embedded `derive_prune_status` / `normalize_prune_eligible` / `prune_window_evaluated` through the Python implementations so there is a single authority.
- **Reviewer**: dyn-embedded-plan-review-output.txt
- **Concern**: - **risk-integration** `Makefile:68-70` — `test-lib-prune-decision` now runs `pytest -k prune`, but the deleted `scripts/test-lib-prune-decision.sh` covered the `derive_prune_status` matrix and `ensure_reviewer_prune_ledger` repair paths. The five collected prune tests exercise prune-nits and `reviewer-prune` record/filter only; none assert `derive_prune_status`, `normalize_prune_eligible`, `prune_window_evaluated`, `write_prune_decision_env`, or `ensure_reviewer_prune_ledger`. Embedded plan-review assets still depend on shell copies of the first three helpers in `python/plan_review.py:833-876`, so rounds 3–4 prune-status and ledger repair can regress without CI signal. **Suggested fix:** Add focused pytest for the Python helpers (mirroring the deleted harness cases) and either test the inlined shell copies or route embedded `derive_prune_status` / `normalize_prune_eligible` / `prune_window_evaluated` through the Python implementations so there is a single authority.
- **Suggested revision**: Address the concern above.


### OOS_15: **risk-integration** `python/plan_review.py:858-876` — `ensure_reviewer_prune_ledger` and `write_prune_decision_env` in the materialized embedded helpers gate on `python3 "$PLUGIN_ROOT/python/cli.py" review reviewer-prune --help` and return `1` before any Python work. `plan-review-loop.sh` calls `ensure_reviewer_prune_ledger` at startup under `set -euo pipefail` (decoded asset line 151), so a missing verb, broken materialized root, or `--help` failure aborts all of Step 3 before panel dispatch. The deleted `scripts/lib-prune-decision.sh` had no CLI dependency for ledger repair or env writes. **Suggested fix:** Drop the `--help` probe and call `review_pipeline.ensure_reviewer_prune_ledger` / `write_prune_decision_env` directly (or treat failures as warn-and-continue for env writes), matching the old fail-open posture for design plan-review.
- **Reviewer**: dyn-embedded-plan-review-output.txt
- **Concern**: - **risk-integration** `python/plan_review.py:858-876` — `ensure_reviewer_prune_ledger` and `write_prune_decision_env` in the materialized embedded helpers gate on `python3 "$PLUGIN_ROOT/python/cli.py" review reviewer-prune --help` and return `1` before any Python work. `plan-review-loop.sh` calls `ensure_reviewer_prune_ledger` at startup under `set -euo pipefail` (decoded asset line 151), so a missing verb, broken materialized root, or `--help` failure aborts all of Step 3 before panel dispatch. The deleted `scripts/lib-prune-decision.sh` had no CLI dependency for ledger repair or env writes. **Suggested fix:** Drop the `--help` probe and call `review_pipeline.ensure_reviewer_prune_ledger` / `write_prune_decision_env` directly (or treat failures as warn-and-continue for env writes), matching the old fail-open posture for design plan-review.
- **Suggested revision**: Address the concern above.


### OOS_16: **risk-integration** `python/test_plan_review.py:51-68` — `test_embedded_plan_review_reviewer_prune_uses_review_cli` only checks that decoded `dispatch-plan-review-panel.sh` and `plan-review-loop.sh` omit retired script paths and contain `review reviewer-prune` plus KV symbol names. It does not assert `write_prune_decision_env` invocation, the `plan-review/round-${ROUND_NUM}/prune-decision.env` path, or the `PRUNE_ROUND_NUM` vs `ROUND_NUM` split used in the embedded panel filter block (`python/plan_review.py:880-906`). A partial `_rewrite_prune_asset` miss could still leave filter on the CLI while breaking prune-decision artifact semantics for rounds 3–4. **Suggested fix:** Extend the embedded regression to assert decoded bodies call `write_prune_decision_env` with the round-scoped dest path, use `"${REVIEWER_PRUNE_CLI[@]}" filter` with `--round "$PRUNE_ROUND_NUM"`, and add a small materialized-root harness that runs filter on rounds 3–4 and checks `prune-decision.env` fields (`PRUNE_STATUS`, `PANEL_PRUNED_EMPTY`, `PRUNED_COUNT`, `PRUNED_COMBOS`).
- **Reviewer**: dyn-embedded-plan-review-output.txt
- **Concern**: - **risk-integration** `python/test_plan_review.py:51-68` — `test_embedded_plan_review_reviewer_prune_uses_review_cli` only checks that decoded `dispatch-plan-review-panel.sh` and `plan-review-loop.sh` omit retired script paths and contain `review reviewer-prune` plus KV symbol names. It does not assert `write_prune_decision_env` invocation, the `plan-review/round-${ROUND_NUM}/prune-decision.env` path, or the `PRUNE_ROUND_NUM` vs `ROUND_NUM` split used in the embedded panel filter block (`python/plan_review.py:880-906`). A partial `_rewrite_prune_asset` miss could still leave filter on the CLI while breaking prune-decision artifact semantics for rounds 3–4. **Suggested fix:** Extend the embedded regression to assert decoded bodies call `write_prune_decision_env` with the round-scoped dest path, use `"${REVIEWER_PRUNE_CLI[@]}" filter` with `--round "$PRUNE_ROUND_NUM"`, and add a small materialized-root harness that runs filter on rounds 3–4 and checks `prune-decision.env` fields (`PRUNE_STATUS`, `PANEL_PRUNED_EMPTY`, `PRUNED_COUNT`, `PRUNED_COMBOS`).
- **Suggested revision**: Address the concern above.


### OOS_17: correctness: python/review_pipeline.py:1329-1370
- **Reviewer**: codex-specialist-correctness-output.txt
- **Concern**: [important] Dirty-tree recovery was omitted and missing or unknown sidecars are treated as clean. A reviewer can leave tracked or untracked changes behind, and later implement steps run on a polluted worktree. Port recover_dirty_tree into review_core and preserve the old missing or non-clean sidecar handling.
- **Suggested revision**: Address the concern above.


### OOS_18: correctness: python/review_pipeline.py:1971-2087
- **Reviewer**: codex-specialist-correctness-output.txt
- **Concern**: [important] _emit_tally calls omit session and implement destinations. A normal fix-required round writes review summaries only under review_tmpdir, leaving parent Step 5 artifacts stale or missing. Pass --session-env-path and --implement-tmpdir on every emit_tally branch.
- **Suggested revision**: Address the concern above.


### OOS_19: risk-integration: python/review_pipeline.py:1931-1977
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] review_core dropped recover_dirty_tree and related dropped-slot sidecar handling that the deleted review-core.sh ran after collect. When an external reviewer dirties the working tree, /implement Step 5 can finish with a polluted tree or wrong findings because only DIRTY_DETECTED is set and no checkpoint/discard runs. Port recover_dirty_tree, collect_dropped_static_outputs, and log_dropped_slots; call them after collect before threshold.
- **Suggested revision**: Address the concern above.


### OOS_20: correctness: python/review_pipeline.py:1829-1832
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] review_core ignores gather_result.returncode. Failed gather-context still dispatches a panel with empty diff/scope context, producing misleading zero-findings or panel-failed outcomes. Check gather_result.returncode and bail with panel-failed exit 2 on non-zero, like dispatch-panel does.
- **Suggested revision**: Address the concern above.


### OOS_21: correctness: python/review_pipeline.py:1931-1977
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] review_core ignores collect_result.returncode. Collector or Claude wait failures no longer hard-stop the round; threshold/tally may run on empty collector state and misclassify the round. Check collect_result.returncode after collect; emit panel-failed and return 2 before threshold when collect fails.
- **Suggested revision**: Address the concern above.


