### FINDING_1: code-quality: phase-2 relaunch counter state can be simplified
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `reuse_fell_through` adds extra state around the phase-2 grouped reuse path; the counter could be incremented directly after `reuse_slot_result` fails for a non-empty `source_row`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] design degradation ignores phase-2 relaunches while WARN uses combined fallback
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-combined-fallback-consumers-output.txt
- **Severity**: latent
- **Concern**: `dispatch-with-waterfall.sh` now bases `WARN=cost-fallback-exceeded-threshold` on `FALLBACK_COUNT + PHASE2_RELAUNCH_COUNT`, but design dispatchers still compute `DEGRADED_ROUND` / `DEGRADED_PANEL` from phase-3-only `FALLBACK_COUNT`. A grouped phase-2 fall-through run can warn for cost fallback while leaving degradation false.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-combined-fallback-consumers-output.txt: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] missing tests for multi-fall-through and combined counter persistence
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The harness does not cover `PHASE2_RELAUNCH_COUNT=2` for multiple fall-throughs in one group, nor does it assert `--fallback-counter-file` persists the combined fallback total. Regressions that count once per group or persist only phase-3 fallbacks could pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_4: phase-3-only WARN test should assert zero phase-2 relaunches
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The phase-3-only WARN threshold test does not assert `PHASE2_RELAUNCH_COUNT=0`, so accidental inclusion of grouped phase-2 relaunches in unrelated runs may not fail that scenario.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_5: missing mixed phase-2 and phase-3 WARN threshold coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: No test combines one phase-2 fall-through and one phase-3 Claude fallback in the same threshold check, so `combined_fallback` could accidentally use only one counter while separate tests still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] fallback counter file semantics are undocumented and unused by callers
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-combined-fallback-consumers-output.txt
- **Severity**: nit
- **Concern**: `--fallback-counter-file` now stores combined phase-2 relaunch plus phase-3 fallback totals, but no in-repo production caller uses it and the combined semantics are not documented for future adopters.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-combined-fallback-consumers-output.txt: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] harness lacks agent_file production-shape coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-dispatch-with-waterfall.sh` uses `prompt_file`-only manifests, leaving `agent_file` launch regressions uncovered.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_8: design dispatcher docs do not describe combined WARN metering
- **Reviewer(s)**: dyn-combined-fallback-consumers-output.txt
- **Severity**: latent
- **Concern**: `dispatch-plan-review-panel.md` still documents degradation from phase-3-only `FALLBACK_COUNT` and does not describe `PHASE2_RELAUNCH_COUNT` or that `WARN=cost-fallback-exceeded-threshold` now uses the combined count.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-combined-fallback-consumers-output.txt: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] review dispatch path is not a fallback-metric consumer
- **Reviewer(s)**: dyn-combined-fallback-consumers-output.txt
- **Severity**: nit
- **Concern**: Review and implement Step 5 paths forward `WARN` but do not parse fallback counters; degradation there comes from voting tally banners, so no regression is identified for that surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-combined-fallback-consumers-output.txt: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] run telemetry files are not fallback KV consumers
- **Reviewer(s)**: dyn-combined-fallback-consumers-output.txt
- **Severity**: nit
- **Concern**: The added `larch-logs/implement/EBF09FB1-3025-4BF0-AA00-30D893666B9D/*` files are run telemetry, not runtime consumers of fallback KVs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-combined-fallback-consumers-output.txt: Address the concern above.
