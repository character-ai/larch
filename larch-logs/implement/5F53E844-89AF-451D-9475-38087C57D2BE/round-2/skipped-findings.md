### OOS_5: C1b Python port ships as `run_legacy()` bash delegation, not importable Python implementations
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-generic-output.txt
- **Severity**: important
- **Concern**: The plan-required Python port is a thin `run_legacy` shell wrapper, not implemented pipeline logic. `review_pipeline`, `review_aggregate`, `review_tally`, and `compose_review` all invoke `bash python/legacy_review_shell/*.sh`. C1b acceptance ("absorbed bash deleted", importable Python functions) is unmet; behavior and security changes still require editing relocated shell. Operators and docs treat `python/cli.py review` as the owner, but the absorbed bash pipeline remains in the shipped runtime.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From codex-generic-output.txt: Replace the legacy-shell delegations with real Python implementations for the review pipeline verbs, and delete `python/legacy_review_shell` once parity tests pass.



### OOS_6: Deleted bash harness coverage replaced by minimal pytest; critical contracts untested
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-review-cli-parity-output.txt
- **Severity**: important
- **Concern**: The branch deletes multi-hundred-line bash harnesses (`test-aggregate-findings.sh`, `test-tally-code-votes.sh`, `test-compose-review-findings.sh`, `test-gather-context.sh`, `test-collect-findings.sh`, `test-review-core.sh`) but replaces them with only ~12 focused pytest cases. Makefile targets may run pytest, but coverage is a tiny fraction of deleted behavior. Missing pins include: diff-mode `gather-context` delegation plus trailing `SCOPE_FILES_COUNT=0`/`MODE=diff` KVs; collect-findings `.done` sentinel wait/timeout; post-threshold `panel-failed` gates; OOS snapshot/restore on zero-findings/prune-skipped; MAV emit-tally handoff; `aggregator-validation-exhausted` exhaust-side tally/emit; tally scope-fit/`OUT_OF_SCOPE_DRIFT_COUNT`; security-tagged compose holdback; aggregation merge, validation-exhausted, scope-reduction, plan-review mode, scope-anchor, and dispatch override cases. `test_review_pipeline.py` mostly exercises stubbed `REVIEW_CORE_*` overrides, so regressions in real legacy-shell paths can ship unnoticed. Regressions in scope-fit, security OOS, MAV paths, aggregation, tally scope-drift normalization, plan scope-reduction, compose redaction, and panel-failed gates may merge with green CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Port deleted harness scenarios into `python/test_review_{pipeline,aggregate,tally}.py` and `python/test_compose_review.py` before (or instead of) deleting bash harnesses.
  - From dyn-review-cli-parity-output.txt: Port the highest-risk harness scenarios from the deleted scripts into the four pytest modules, especially contracts called out in the C1b plan edge-case list and any path-resolution fallbacks not covered by `run_legacy` setdefault.



