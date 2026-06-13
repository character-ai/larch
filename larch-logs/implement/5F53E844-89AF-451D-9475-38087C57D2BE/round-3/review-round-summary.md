# Review Round 3

- Mode: `diff`
- 9 accepted, 3 rejected (2 neutral)

## Accepted Findings

### FINDING_1: test_review_pipeline.py missing critical legacy harness coverage
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-review-cli-parity-output.txt
- **Severity**: important
- **Concern**: Deleted review-pipeline bash harnesses (~3k lines) were replaced by a thin pytest slice that stubs most review-core stages. Regressions in post-threshold panel-failed gates (`collector_success_count==0`, `static_archetype_coverage_ok`), MAV emit-tally handoff, OOS snapshot/restore on zero-findings/prune-skipped, collect-findings `.done` wait/timeout, diff-mode gather-context KV relay (`SCOPE_FILES_COUNT`, `MODE=diff`), and `run_legacy` quiet-mode behavior can pass CI while breaking live `/review` or `/implement` Step 5.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Port deleted test-review-core.sh gate fixtures as pytest cases using real review core with controlled collector/threshold files.
  - From cursor-specialist-edge-cases-output.txt: Port critical cases from deleted bash harnesses for panel-failed collector timeout OOS snapshot/restore and diff-mode gather KV parity.
  - From cursor-specialist-testing-output.txt: Port deleted harness fixtures into test_review_pipeline.py with per-section -k markers matching Makefile targets.
  - From dyn-review-cli-parity-output.txt: Port the highest-risk harness scenarios from the deleted bash tests into the four pytest modules (at minimum panel-failed gates, MAV, OOS snapshot/restore, collect `.done` timeout, scope-fit drift, security compose holdback, and aggregate scope-reduction), matching the plan's testing strategy.
  - From dyn-review-cli-parity-output.txt: Add a focused diff-mode gather-context test (fixture repo or stubbed `gather-branch-context.sh`) that asserts delegated KVs are relayed unchanged and the two trailing KVs are present on the CLI stdout contract stream.


### FINDING_13: review-and-fix harness never exercises default REVIEW_CORE_CMD path
- **Reviewer(s)**: dyn-review-and-fix-handoff-output.txt
- **Severity**: important
- **Concern**: Every orchestrator-mode harness case in `skills/review-and-fix/scripts/test-review-and-fix.sh:328-338` forces `REVIEW_AND_FIX_REVIEW_CORE_SH="$TMP/review-core-stub.sh"`, so the production default `REVIEW_CORE_CMD=(python3 "$PY_CLI" review core)` is never exercised end-to-end. The tally-fidelity case hits real `COMPOSE_CMD` but not review-core CLI wiring, `IMPLEMENT_TMPDIR` prefix propagation through `run_legacy`, or KV relay into `round-N/review-core.env`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-review-and-fix-handoff-output.txt: Add at least one harness case that omits `REVIEW_AND_FIX_REVIEW_CORE_SH`, stubs only the heavy legacy stages via `REVIEW_CORE_*_SH`, and asserts `review core` is invoked with the expected argv and that `IMPLEMENT_TMPDIR` reaches emit-tally / parent-copy behavior.


### FINDING_2: test_review_tally.py missing tally and classification harness coverage
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-review-cli-parity-output.txt
- **Severity**: important
- **Concern**: Deleted tally-code-votes.sh (~951 lines) and findings-classification.sh (~253 lines) harnesses were not ported. Only emit-tally and log-phase smoke tests remain. Scope-fit / `OUT_OF_SCOPE_DRIFT_COUNT`, security-tagged OOS holdback, nested classification TSV paths, 0-judge/MAV behavior, and scope-normalization bugs can regress without CI failure until a live implement run mis-files findings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Restore highest-risk tally fixtures from deleted shell harness in test_review_tally.py.
  - From cursor-specialist-edge-cases-output.txt: Port security OOS holdback scope-fit and classifier-failure cases from deleted test-tally-code-votes.sh into test_review_tally.py.
  - From cursor-specialist-testing-output.txt: Port tally and classification fixtures from deleted bash harnesses.


### FINDING_3: test_compose_review.py missing compose harness coverage
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-review-cli-parity-output.txt
- **Severity**: important
- **Concern**: Deleted test-compose-review-findings.sh (~579 lines) covered security holdback, Gate B, accepted-all precedence, field extraction, and redaction order. Only an empty-input smoke test remains. Security-tagged OOS could leak into committed `review-findings-full.jsonl` with green CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Port security-holdback, Gate B, and accepted-all fixtures from deleted compose harness.
  - From cursor-specialist-edge-cases-output.txt: Add pytest mirroring old security OOS holdback case asserting security blocks are absent from JSONL output.
  - From cursor-specialist-testing-output.txt: Port security holdback, Gate B, precedence, and redaction-order fixtures.


### FINDING_4: test_review_aggregate.py missing aggregate harness coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-review-cli-parity-output.txt
- **Severity**: important
- **Concern**: Deleted test-aggregate-findings.sh (~1937 lines) was not ported. Only the disabled-aggregator fast path is tested. Merge validation, scope-reduction withholding (`[SCOPE-REDUCTION]`), validation-exhausted tally side-effects, and plan-mode aggregation can break without pytest failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add merge, validation-exhausted, plan-mode, and scope-reduction tests from the deleted harness.


### FINDING_5: C1b review CLI verbs are run_legacy bash delegates, not a Python port
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-generic-output.txt, dyn-review-and-fix-handoff-output.txt
- **Severity**: important
- **Concern**: `python/review_pipeline.py`, `python/review_aggregate.py`, `python/review_tally.py`, and `python/compose_review.py` delegate into `python/legacy_review_shell/*.sh`. The migration goal called for importable Python functions; callers importing `review_pipeline.dispatch_panel()` or `review_tally.tally_code_votes()` still shell out. Step 5 now routes bash → Python CLI → bash on every round, adding process hops and obscuring where MAV emit-tally and parent artifact copies live, while docs describe Python verbs as runtime authority. Future sh-to-py cleanup may falsely treat surfaces as migrated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Complete Python port per plan or document CLI-façade status until follow-up absorbs bash bodies.
  - From codex-generic-output.txt: port the pipeline logic into the new Python modules, keep only explicitly retained Bash subprocess boundaries, and remove `python/legacy_review_shell` runtime dependencies from the new CLI verbs.
  - From dyn-review-and-fix-handoff-output.txt: Either finish the native port so `review core` is in-process, or document and test the shim explicitly (including a contract test that `review-and-fix.sh` + default `REVIEW_CORE_CMD` reaches the same artifacts as the legacy entrypoint).


### FINDING_7: Quiet-mode KV relay chain inadequately tested
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-review-cli-parity-output.txt
- **Severity**: important
- **Concern**: Production `/review` runs with quiet routing enabled. Legacy bash stages emit contract KVs to FD 3; `proc.run` must capture them and `run_legacy` must re-emit them. The only relay test uses a stdout `printf` stub that never sources `lib-quiet.sh` or calls `emit`/`emit_kv`, so a break in the quiet-mode FD 3 relay chain would not fail CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add integration test with lib-quiet emit_kv under quiet mode asserting KVs relay through run_legacy.
  - From dyn-review-cli-parity-output.txt: Add an integration test that runs `run_legacy` against a tiny legacy-style script calling `larch_quiet_init` plus `emit_kv`, without `LARCH_QUIET_DISABLE`, and assert the Python contract stream receives the KV lines.


### FINDING_8: SECURITY.md and operator docs misattribute review implementation authority
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-retired-reference-sweep-output.txt
- **Severity**: important
- **Concern**: SECURITY.md credits `python/review_pipeline.py` for `<scout_notes>` untrusted-input framing and `python/compose_review.py` for redaction boundaries, but those modules are thin `run_legacy()` shims. Real logic lives in `python/legacy_review_shell/dispatch-panel.sh` and `compose-review-findings.sh`. `docs/run-logs.md` also names `python/compose_review.py` as the JSONL producer contract while the deleted `scripts/compose-review-findings.md` was not relocated. Security reviewers and operators tracing producer/redaction behavior inspect wrong files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Retarget SECURITY.md to legacy_review_shell scripts or document wrapper-to-legacy delegation explicitly.
  - From dyn-retired-reference-sweep-output.txt: Retarget the sentence to `python/legacy_review_shell/dispatch-panel.sh` (or `python/cli.py review dispatch-panel` with an explicit note that behavior is implemented in the legacy shell copy), and drop the `review_pipeline.py` claim unless the logic is actually ported into Python.
  - From dyn-retired-reference-sweep-output.txt: Point contract prose at `python/legacy_review_shell/compose-review-findings.sh` (and restore or add a `.md` contract beside it), or complete the planned Python port so `compose_review.py` actually owns the documented behavior.


### FINDING_9: docs/linting.md overclaims test_review_tally.py forensic TSV coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `docs/linting.md` line 208 claims `make test-review-findings-classification` exercises comprehensive forensic TSV coverage via `python/test_review_tally.py` (nested `/implement` and standalone `/review` paths, 0-judge outputs, parser parity, enum sanitization, etc.). That coverage does not exist in the current pytest module. Operators and CI readers assume classification/parser regressions are gated; they are not.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Update doc after porting tests, or narrow the documented scope to match reality.


