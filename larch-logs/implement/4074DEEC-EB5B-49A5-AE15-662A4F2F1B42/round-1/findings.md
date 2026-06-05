### FINDING_1: [OUT_OF_SCOPE] correctness
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 1. **correctness** `skills/design/scripts/run-step3-review.sh:89-90` — Sessions that already have `.step3-entry-plan-printed` from the pre-fix warning-path touch are not healed by this patch; after `plan.txt` repair, `--preview-only` still hits the sentinel early-exit and skips the preview until the operator removes the sentinel file. **Suggested fix:** Document recovery (`rm "$DESIGN_TMPDIR/.step3-entry-plan-printed"`) in the issue/PR notes, or add a follow-up that invalidates the sentinel when `plan.txt` becomes non-empty and preview was never header-emitted (e.g., mtime/sidecar — explicitly deferred at design time).
- **Suggested revision**: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] correctness
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 2. **correctness** `skills/design/scripts/test-run-step3-review.sh:150-191` — The new missing→repair case uses stub renderers rather than `emit-design-plan-preview.sh` with a real empty/missing `plan.txt`; driver logic is well covered, but an integration-style call with the default renderer would catch drift between the exact warning string in the emitter and any future touch rules. **Suggested fix:** Optional harness case without `RUN_STEP3_EMIT_PREVIEW_SH` override when allowlist fixtures permit. --- **Plan verification (correctness lens):** | Requirement | Status | |-------------|--------| | No sentinel on exact missing-plan warning only | Met — branch removed at `run-step3-review.sh:108-110` | | Sentinel on header render | Met — unchanged header branch | | Missing → repair → preview re-renders + sentinel | Met — `test-run-step3-review.sh` `D_PV5B` scenario | | Harness inversion fails on unfixed code | Met — old code would fail `! -e` assertion | | Doc sync | Met — `run-step3-review.md` Responsibility 0 | Core logic is sound for new sessions and the #3493 repair path described in the plan. The only operational gap is pre-existing wrongly touched sentinels, which is outside what this diff changes.
- **Suggested revision**: Address the concern above.

### FINDING_3: risk-integration: skills/design/scripts/test-run-step3-review.sh:244-304
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No test for repeated missing-plan re-entry re-warn behavior documented in plan edge cases Operator triggers Step 3 twice while plan.txt remains missing; a partial regression could suppress output on the second entry while leaving sentinel absent, and current tests would still pass after a single missing-plan call Add a second consecutive --preview-only call with missing plan; assert warning text in stdout and sentinel still absent
- **Suggested revision**: Address the concern above.

### FINDING_4: risk-integration: skills/design/scripts/test-run-step3-review.sh:263-304
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Missing→repair regression uses header stub instead of default emit-design-plan-preview.sh on repair step Real emitter could change header formatting (extra whitespace, renamed heading) while stub tests stay green; driver substring gate would stop touching sentinel If feasible, repair step should call default renderer with restored plan.txt and assert header + sentinel
- **Suggested revision**: Address the concern above.

### FINDING_5: risk-integration: skills/design/scripts/run-step3-review.sh:89-90
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Fix does not invalidate sentinels created by pre-fix warning-path touch Sessions that already have .step3-entry-plan-printed from the old bug still skip preview after plan.txt repair even on fixed code Document manual sentinel deletion or add migration invalidation when plan.txt becomes non-empty
- **Suggested revision**: Address the concern above.

### FINDING_6: risk-integration: skills/design/scripts/test-run-step3-review.sh:255-275
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Missing-plan tests discard stdout; warning emission not asserted Renderer could stop emitting the warning while sentinel logic stays correct (or vice versa); operator loses the intended re-warn signal Capture stdout and assert_contains the exact missing-plan warning on first call
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] risk-integration: skills/design/scripts/test-emit-design-plan-preview.sh:1-138
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No harness case for missing/empty plan.txt on real step3 renderer Warning string in emit-design-plan-preview.sh could change without failing driver stub tests Add allowlisted tmpdir + rm plan.txt case to test-emit-design-plan-preview.sh
- **Suggested revision**: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] risk-integration: skills/design/scripts/test-run-step3-review.sh:143-376
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] All preview tests use RUN_STEP3_EMIT_PREVIEW_SH stubs; no default-path integration Default renderer regressions only surface in production / manual /design runs Add one preview-only case without renderer override using write_common_inputs + real plan.txt
- **Suggested revision**: Address the concern above.

### FINDING_9: **Path safety:** Sentinel `touch` still targets `"$_canonical_tmpdir/.step3-entry-plan-printed"` only after `larch_design_tmpdir_validate` and `cd … && pwd -P` (see ```86:112:skills/design/scripts/run-step3-review.sh```). Allowlist rejects `..`, newlines, and non-directory leaf symlinks (`scripts/lib-design-tmpdir.sh`).
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Path safety:** Sentinel `touch` still targets `"$_canonical_tmpdir/.step3-entry-plan-printed"` only after `larch_design_tmpdir_validate` and `cd … && pwd -P` (see ```86:112:skills/design/scripts/run-step3-review.sh```). Allowlist rejects `..`, newlines, and non-directory leaf symlinks (`scripts/lib-design-tmpdir.sh`).
- **Suggested revision**: Address the concern above.

### FINDING_10: **Command execution:** `_preview_sh` still comes from `RUN_STEP3_EMIT_PREVIEW_SH` or the default emitter; this diff does not widen that seam.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Command execution:** `_preview_sh` still comes from `RUN_STEP3_EMIT_PREVIEW_SH` or the default emitter; this diff does not widen that seam.
- **Suggested revision**: Address the concern above.

### FINDING_11: **Output handling:** Substring match on `_preview_out` for the header was already the primary touch rule; removing the warning branch does not weaken matching—it removes a false-positive touch path. A custom renderer could still spoof the header via env override; that was true before and is test/harness scope.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Output handling:** Substring match on `_preview_out` for the header was already the primary touch rule; removing the warning branch does not weaken matching—it removes a false-positive touch path. A custom renderer could still spoof the header via env override; that was true before and is test/harness scope.
- **Suggested revision**: Address the concern above.

### FINDING_12: **Plan content:** `plan.txt` is still emitted through `emit-design-plan-preview.sh` when present; this change does not alter plan read/emit or redaction. Repeated missing-plan warnings are fixed strings with no file content—no new disclosure.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Plan content:** `plan.txt` is still emitted through `emit-design-plan-preview.sh` when present; this change does not alter plan read/emit or redaction. Repeated missing-plan warnings are fixed strings with no file content—no new disclosure.
- **Suggested revision**: Address the concern above.

### FINDING_13: **Operational impact:** Fixing sentinel suppression on repair improves operator visibility (warnings and preview re-render), which is neutral-to-positive for session integrity, not a new attack vector.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Operational impact:** Fixing sentinel suppression on repair improves operator visibility (warnings and preview re-render), which is neutral-to-positive for session integrity, not a new attack vector. Acceptance criteria from the plan are met from a security lens; no injection, authz bypass, secret leakage, or path-traversal regression introduced.
- **Suggested revision**: Address the concern above.

### FINDING_14: Early-exit on existing sentinel (lines 89–90) is unchanged and still correct once a real header has been shown.
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: - Early-exit on existing sentinel (lines 89–90) is unchanged and still correct once a real header has been shown.
- **Suggested revision**: Address the concern above.

### FINDING_15: `emit-design-plan-preview.sh` still emits the exact missing-plan string only when `plan.txt` is missing/empty (lines 103–105); that path no longer satisfies touch — aligned with acceptance.
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: - `emit-design-plan-preview.sh` still emits the exact missing-plan string only when `plan.txt` is missing/empty (lines 103–105); that path no longer satisfies touch — aligned with acceptance.
- **Suggested revision**: Address the concern above.

### FINDING_16: Harness inversion would fail on unfixed code (old behavior touched sentinel on warning).
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: - Harness inversion would fail on unfixed code (old behavior touched sentinel on warning).
- **Suggested revision**: Address the concern above.

### FINDING_17: Missing→repair case (`D_PV5B`) exercises the regression path the issue describes.
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: - Missing→repair case (`D_PV5B`) exercises the regression path the issue describes. Intentional tradeoffs from the plan (not defects): repeated missing-plan warnings on every Step 3 re-entry until repair; existence-based sentinel (no mtime/content invalidation after a successful preview). ---
- **Suggested revision**: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] - **architecture** `skills/design/scripts/run-step3-review.sh:89-90` — Sessions that already have a poisoned `.step3-entry-plan-printed` from pre-fix code (warning path touched the sentinel without ever showing the plan header) still hit the early `exit 0` after upgrade, so repairing `plan.txt` alone will not restore the preview until the sentinel file is removed manually. **Suggested fix:** Document one-time recovery (`rm "$DESIGN_TMPDIR/.step3-entry-plan-printed"`) in the issue/PR notes, or add a future enhancement to clear the sentinel when `plan.txt` transitions from empty to non-empty (the plan explicitly deferred mtime-based invalidation).
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 1. - **architecture** `skills/design/scripts/run-step3-review.sh:89-90` — Sessions that already have a poisoned `.step3-entry-plan-printed` from pre-fix code (warning path touched the sentinel without ever showing the plan header) still hit the early `exit 0` after upgrade, so repairing `plan.txt` alone will not restore the preview until the sentinel file is removed manually. **Suggested fix:** Document one-time recovery (`rm "$DESIGN_TMPDIR/.step3-entry-plan-printed"`) in the issue/PR notes, or add a future enhancement to clear the sentinel when `plan.txt` transitions from empty to non-empty (the plan explicitly deferred mtime-based invalidation).
- **Suggested revision**: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] - **correctness** `skills/design/scripts/run-step3-review.sh:112` — `touch … || true` swallows touch failures; a failed touch leaves no sentinel, so every Step 3 re-entry re-emits the full preview (noisy but not silent). **Suggested fix:** Pre-existing pattern; only worth changing if you want a loud failure or a retry when sentinel creation fails.
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 2. - **correctness** `skills/design/scripts/run-step3-review.sh:112` — `touch … || true` swallows touch failures; a failed touch leaves no sentinel, so every Step 3 re-entry re-emits the full preview (noisy but not silent). **Suggested fix:** Pre-existing pattern; only worth changing if you want a loud failure or a retry when sentinel creation fails.
- **Suggested revision**: Address the concern above.

### FINDING_20: [OUT_OF_SCOPE] - **code-quality** `skills/design/scripts/test-run-step3-review.sh:263-304` — The #3493 regression uses stub renderers for both calls, not `emit-design-plan-preview.sh` with a real `plan.txt` restore, so a renderer-only regression in the missing→repair path would not be caught here (driver contract is still well covered). **Suggested fix:** Optional follow-up: one harness case that `rm`s `plan.txt`, calls `--preview-only` with the default preview script, restores `plan.txt`, and asserts header output (complements `test-emit-design-plan-preview.sh`).
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 3. - **code-quality** `skills/design/scripts/test-run-step3-review.sh:263-304` — The #3493 regression uses stub renderers for both calls, not `emit-design-plan-preview.sh` with a real `plan.txt` restore, so a renderer-only regression in the missing→repair path would not be caught here (driver contract is still well covered). **Suggested fix:** Optional follow-up: one harness case that `rm`s `plan.txt`, calls `--preview-only` with the default preview script, restores `plan.txt`, and asserts header output (complements `test-emit-design-plan-preview.sh`).
- **Suggested revision**: Address the concern above.

### FINDING_21: [OUT_OF_SCOPE] - **code-quality** `skills/design/scripts/test-emit-design-plan-preview.sh` — No case asserts the step3 `plan.txt missing or empty` warning string; only allowlist/invalid-tmpdir warnings are tested. **Suggested fix:** Add a small allowlisted tmpdir test with no `plan.txt` and grep for the exact `**⚠ 3: plan.txt missing or empty…**` line.
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 4. - **code-quality** `skills/design/scripts/test-emit-design-plan-preview.sh` — No case asserts the step3 `plan.txt missing or empty` warning string; only allowlist/invalid-tmpdir warnings are tested. **Suggested fix:** Add a small allowlisted tmpdir test with no `plan.txt` and grep for the exact `**⚠ 3: plan.txt missing or empty…**` line. --- **Acceptance vs plan:** Met for the changed surfaces — warning-only output does not touch the sentinel; missing→repair re-renders the header and then touches the sentinel; docs match behavior; harness cases align with acceptance bullets (runtime lint not executed in this read-only review).
- **Suggested revision**: Address the concern above.

### FINDING_22: `run-step3-review.sh`: One `case` branch removed, comment updated — single-branch `case`/`esac` is syntactically valid Bash
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: - `run-step3-review.sh`: One `case` branch removed, comment updated — single-branch `case`/`esac` is syntactically valid Bash
- **Suggested revision**: Address the concern above.

### FINDING_23: `run-step3-review.md`: Responsibility 0 extended with the new sentinel-touch contract — accurate and inline with behavior
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: - `run-step3-review.md`: Responsibility 0 extended with the new sentinel-touch contract — accurate and inline with behavior
- **Suggested revision**: Address the concern above.

### FINDING_24: `test-run-step3-review.sh`: Existing test renamed+inverted; new `D_PV5B` regression block added with the two-phase missing→repair scenario
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: - `test-run-step3-review.sh`: Existing test renamed+inverted; new `D_PV5B` regression block added with the two-phase missing→repair scenario The new test's `assert_contains "$out" '## Plan Candidate for Review'` captures output via `2>&1` — the same pattern already used in the existing disallowed-tmpdir test block visible at the bottom of the diff, so it's a validated idiom in this harness. Plan fidelity is complete: all three plan-specified files are touched, the `--no-preview` path is untouched, no new flags or result-env keys are introduced.
- **Suggested revision**: Address the concern above.

