### FINDING_1: [OUT_OF_SCOPE] correctness
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 1. **correctness** `skills/design/scripts/run-step3-review.sh:89-90` — Sessions that already have `.step3-entry-plan-printed` from the pre-fix warning-path touch are not healed by this patch; after `plan.txt` repair, `--preview-only` still hits the sentinel early-exit and skips the preview until the operator removes the sentinel file. **Suggested fix:** Document recovery (`rm "$DESIGN_TMPDIR/.step3-entry-plan-printed"`) in the issue/PR notes, or add a follow-up that invalidates the sentinel when `plan.txt` becomes non-empty and preview was never header-emitted (e.g., mtime/sidecar — explicitly deferred at design time).
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_18: [OUT_OF_SCOPE] - **architecture** `skills/design/scripts/run-step3-review.sh:89-90` — Sessions that already have a poisoned `.step3-entry-plan-printed` from pre-fix code (warning path touched the sentinel without ever showing the plan header) still hit the early `exit 0` after upgrade, so repairing `plan.txt` alone will not restore the preview until the sentinel file is removed manually. **Suggested fix:** Document one-time recovery (`rm "$DESIGN_TMPDIR/.step3-entry-plan-printed"`) in the issue/PR notes, or add a future enhancement to clear the sentinel when `plan.txt` transitions from empty to non-empty (the plan explicitly deferred mtime-based invalidation).
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 1. - **architecture** `skills/design/scripts/run-step3-review.sh:89-90` — Sessions that already have a poisoned `.step3-entry-plan-printed` from pre-fix code (warning path touched the sentinel without ever showing the plan header) still hit the early `exit 0` after upgrade, so repairing `plan.txt` alone will not restore the preview until the sentinel file is removed manually. **Suggested fix:** Document one-time recovery (`rm "$DESIGN_TMPDIR/.step3-entry-plan-printed"`) in the issue/PR notes, or add a future enhancement to clear the sentinel when `plan.txt` transitions from empty to non-empty (the plan explicitly deferred mtime-based invalidation).
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_19: [OUT_OF_SCOPE] - **correctness** `skills/design/scripts/run-step3-review.sh:112` — `touch … || true` swallows touch failures; a failed touch leaves no sentinel, so every Step 3 re-entry re-emits the full preview (noisy but not silent). **Suggested fix:** Pre-existing pattern; only worth changing if you want a loud failure or a retry when sentinel creation fails.
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 2. - **correctness** `skills/design/scripts/run-step3-review.sh:112` — `touch … || true` swallows touch failures; a failed touch leaves no sentinel, so every Step 3 re-entry re-emits the full preview (noisy but not silent). **Suggested fix:** Pre-existing pattern; only worth changing if you want a loud failure or a retry when sentinel creation fails.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### FINDING_2: [OUT_OF_SCOPE] correctness
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 2. **correctness** `skills/design/scripts/test-run-step3-review.sh:150-191` — The new missing→repair case uses stub renderers rather than `emit-design-plan-preview.sh` with a real empty/missing `plan.txt`; driver logic is well covered, but an integration-style call with the default renderer would catch drift between the exact warning string in the emitter and any future touch rules. **Suggested fix:** Optional harness case without `RUN_STEP3_EMIT_PREVIEW_SH` override when allowlist fixtures permit. --- **Plan verification (correctness lens):** | Requirement | Status | |-------------|--------| | No sentinel on exact missing-plan warning only | Met — branch removed at `run-step3-review.sh:108-110` | | Sentinel on header render | Met — unchanged header branch | | Missing → repair → preview re-renders + sentinel | Met — `test-run-step3-review.sh` `D_PV5B` scenario | | Harness inversion fails on unfixed code | Met — old code would fail `! -e` assertion | | Doc sync | Met — `run-step3-review.md` Responsibility 0 | Core logic is sound for new sessions and the #3493 repair path described in the plan. The only operational gap is pre-existing wrongly touched sentinels, which is outside what this diff changes.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_20: [OUT_OF_SCOPE] - **code-quality** `skills/design/scripts/test-run-step3-review.sh:263-304` — The #3493 regression uses stub renderers for both calls, not `emit-design-plan-preview.sh` with a real `plan.txt` restore, so a renderer-only regression in the missing→repair path would not be caught here (driver contract is still well covered). **Suggested fix:** Optional follow-up: one harness case that `rm`s `plan.txt`, calls `--preview-only` with the default preview script, restores `plan.txt`, and asserts header output (complements `test-emit-design-plan-preview.sh`).
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 3. - **code-quality** `skills/design/scripts/test-run-step3-review.sh:263-304` — The #3493 regression uses stub renderers for both calls, not `emit-design-plan-preview.sh` with a real `plan.txt` restore, so a renderer-only regression in the missing→repair path would not be caught here (driver contract is still well covered). **Suggested fix:** Optional follow-up: one harness case that `rm`s `plan.txt`, calls `--preview-only` with the default preview script, restores `plan.txt`, and asserts header output (complements `test-emit-design-plan-preview.sh`).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### FINDING_21: [OUT_OF_SCOPE] - **code-quality** `skills/design/scripts/test-emit-design-plan-preview.sh` — No case asserts the step3 `plan.txt missing or empty` warning string; only allowlist/invalid-tmpdir warnings are tested. **Suggested fix:** Add a small allowlisted tmpdir test with no `plan.txt` and grep for the exact `**⚠ 3: plan.txt missing or empty…**` line.
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 4. - **code-quality** `skills/design/scripts/test-emit-design-plan-preview.sh` — No case asserts the step3 `plan.txt missing or empty` warning string; only allowlist/invalid-tmpdir warnings are tested. **Suggested fix:** Add a small allowlisted tmpdir test with no `plan.txt` and grep for the exact `**⚠ 3: plan.txt missing or empty…**` line. --- **Acceptance vs plan:** Met for the changed surfaces — warning-only output does not touch the sentinel; missing→repair re-renders the header and then touches the sentinel; docs match behavior; harness cases align with acceptance bullets (runtime lint not executed in this read-only review).
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_7: [OUT_OF_SCOPE] risk-integration: skills/design/scripts/test-emit-design-plan-preview.sh:1-138
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No harness case for missing/empty plan.txt on real step3 renderer Warning string in emit-design-plan-preview.sh could change without failing driver stub tests Add allowlisted tmpdir + rm plan.txt case to test-emit-design-plan-preview.sh
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_8: [OUT_OF_SCOPE] risk-integration: skills/design/scripts/test-run-step3-review.sh:143-376
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] All preview tests use RUN_STEP3_EMIT_PREVIEW_SH stubs; no default-path integration Default renderer regressions only surface in production / manual /design runs Add one preview-only case without renderer override using write_common_inputs + real plan.txt
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

