# Review Round 1

- Mode: `diff`
- 4 accepted, 8 rejected (5 neutral)

## Accepted Findings

### FINDING_1: correctness: skills/design/scripts/plan-review-continuation.sh:178-184
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] ballot-items-lost continuation requires exact REASON=ballot-items-lost but snapshot failure can append ,snapshot-failed to LOOP_REASON. When INSCOPE_REMAINING>0 and tally is ok but round snapshot fails, REASON becomes ballot-items-lost,snapshot-failed; continuation stays false and the review loop stops instead of retrying the lost ballot. Use prefix matching or a dedicated immutable reason key for ballot-items-lost that snapshot logic cannot suffix.
- **Suggested revision**: Address the concern above.


### FINDING_11: risk-integration: skills/design/scripts/test-design-postplan-emit.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] No regression test exercises invalid mechanical_churn through design-postplan-emit.sh --with-plan-size. Bug 1 was observed when Codex emitted mechanical_churn: 35 during Step 2b postplan; only test-check-plan-size.sh covers check-plan-size.sh in isolation. A postplan regression could re-silence or mislabel the failure while leaf tests still pass. Add a merged postplan case with mechanical_churn: 35 and valid diff_lines: assert exit 1, PLAN_SIZE_STATUS=invalid-mechanical-churn, WARN mentions invalid-mechanical-churn, validation log contains awk stderr.
- **Suggested revision**: Address the concern above.


### FINDING_15: **risk-integration** `skills/design/scripts/plan-review-continuation.sh:171-184` — The new `ballot-items-lost` continuation branch sits behind `elif [[ "$APPROVE_REQUESTED" == true ]]` at line 171, which only sets `REASON=explicit-approve` and leaves `CONTINUE=false`. On `/design --per-round-approval`, a round that correctly detects `REASON=ballot-items-lost` with `LOOP_STATUS=zero-findings-degraded-panel` and `ACCEPTED_COUNT=0` still stops instead of launching another review round, recreating Bug 2 for that flag combination. There is nothing for Gate B to approve in this shape, so the explicit-approve gate does not add operator value here. **Suggested fix:** Carve out `ballot-items-lost` before the `APPROVE_REQUESTED` branch (or use a compound condition) so lost-ballot recovery always sets `CONTINUE=true` regardless of `--per-round-approval`; update `plan-review-continuation.md` and add a cap test with `--approve-requested true`.
- **Reviewer**: dyn-risk-integration-output.txt
- **Concern**: - **risk-integration** `skills/design/scripts/plan-review-continuation.sh:171-184` — The new `ballot-items-lost` continuation branch sits behind `elif [[ "$APPROVE_REQUESTED" == true ]]` at line 171, which only sets `REASON=explicit-approve` and leaves `CONTINUE=false`. On `/design --per-round-approval`, a round that correctly detects `REASON=ballot-items-lost` with `LOOP_STATUS=zero-findings-degraded-panel` and `ACCEPTED_COUNT=0` still stops instead of launching another review round, recreating Bug 2 for that flag combination. There is nothing for Gate B to approve in this shape, so the explicit-approve gate does not add operator value here. **Suggested fix:** Carve out `ballot-items-lost` before the `APPROVE_REQUESTED` branch (or use a compound condition) so lost-ballot recovery always sets `CONTINUE=true` regardless of `--per-round-approval`; update `plan-review-continuation.md` and add a cap test with `--approve-requested true`.
- **Suggested revision**: Address the concern above.


### FINDING_27: **architecture** `scripts/run-step5-review.sh:232-238` — Step 5 now disables dynamic code-review scouts unless an external-coder scout marker exists. That overrides the implement-mode default of 3 dynamic archetypes in `skills/review-and-fix/scripts/review-and-fix.sh:1367-1385`, and it drops dynamic review coverage for `coder=claude`, emergency, and Claude fallback paths because `skills/implement/scripts/step2-implement.sh:184-188` clears the marker. If the marker exists but the optional sidecar is empty or invalid, `skills/review/scripts/dispatch-panel.sh:474-488` records `parse-failed` and also skips the legacy live scout. **Suggested fix:** Do not force `--dynamic-archetypes 0` when the marker is absent. Forward `--pre-scouted-manifest` only when `SCOUT_CODER_STATUS=ok`, or let `dispatch-panel.sh` fall back to the live scout when the pre-scouted manifest is missing, empty, or fully filtered.
- **Reviewer**: dyn-architecture-codex-output.txt
- **Concern**: - **architecture** `scripts/run-step5-review.sh:232-238` — Step 5 now disables dynamic code-review scouts unless an external-coder scout marker exists. That overrides the implement-mode default of 3 dynamic archetypes in `skills/review-and-fix/scripts/review-and-fix.sh:1367-1385`, and it drops dynamic review coverage for `coder=claude`, emergency, and Claude fallback paths because `skills/implement/scripts/step2-implement.sh:184-188` clears the marker. If the marker exists but the optional sidecar is empty or invalid, `skills/review/scripts/dispatch-panel.sh:474-488` records `parse-failed` and also skips the legacy live scout. **Suggested fix:** Do not force `--dynamic-archetypes 0` when the marker is absent. Forward `--pre-scouted-manifest` only when `SCOUT_CODER_STATUS=ok`, or let `dispatch-panel.sh` fall back to the live scout when the pre-scouted manifest is missing, empty, or fully filtered.
- **Suggested revision**: Address the concern above.


