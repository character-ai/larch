### FINDING_1: Cp-fail test couples to earlier dedup scenario
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The cp-failure regression test compares the cp-fail Codex launch counter against a counter from an earlier dedup scenario, so unrelated test reordering or happy-path launch-count changes can fail the harness without a production regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_2: Duplicate reuse cleanup blocks
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `reuse_slot_result` has repeated cleanup-and-return blocks after cp, sidecar, and ledger guard failures, increasing maintenance risk if more guarded steps are added.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: Missing sidecar and ledger failure regression coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The new regression only exercises cp failure, so future breakage of the sidecar or ledger guarded failure paths in `reuse_slot_result` could pass `make test-dispatch-with-waterfall`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_4: Unguarded reuse bookkeeping can report success with partial state
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Unguarded `emit_kv` and `REUSED_INDICES_FILE` append operations after guarded reuse I/O can fail under if-test errexit suppression, leaving reused ledger/dedup state while skipping both phase-2 relaunch and phase-3 queueing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] Phase-2 relaunches lack fallback cost metering
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Phase-2 Cursor/Codex relaunches caused by reuse fall-through are not counted in `FALLBACK_COUNT` or surfaced through the cost-fallback warning threshold, so external-tool spend can rise without operator warning.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-security-output.txt: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] Branch contains unrelated PR-scope changes
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: The branch diff includes unrelated merge-pr, ship-pr, lint-fix-loop, tests, or docs changes outside the dispatch waterfall feature, which may confuse PR review scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] Reused-index append failure can double-launch
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: If appending to `REUSED_INDICES_FILE` fails after successful copy and ledger writes, reuse is treated as failed and relaunches, which avoids aborting but can double-launch on full-disk edge cases.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] Second-invocation dedup test does not model same-run stale ledger reuse
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The second-invocation dedup test deletes outputs between runs while startup truncates the ledger, so it does not model same-run stale ledger reuse.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] Reuse cp path is not revalidated against session root
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Grouped dedup copies the absolute path stored in `waterfall-group-results.tsv` without revalidating that it remains under the session output root, leaving a pre-existing hardening gap if a concurrent local writer can alter the ledger.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] Unconditional reuse call could reintroduce errexit abort
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `reuse_slot_result` returning nonzero is safe only when called inside the current `if reuse_slot_result; then continue` pattern; a future unconditional call could restore `set -e` abort behavior on cp failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] Multiple grouped slots can repeatedly hit one stale donor row
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Before a fresh ok row exists, multiple slots in one group can each encounter the same stale ledger row, paying repeated failed cp attempts and phase-2 relaunches for one deleted donor path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
