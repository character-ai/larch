### [rejected] FINDING_10

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_10: **Command execution:** `_preview_sh` still comes from `RUN_STEP3_EMIT_PREVIEW_SH` or the default emitter; this diff does not widen that seam.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Command execution:** `_preview_sh` still comes from `RUN_STEP3_EMIT_PREVIEW_SH` or the default emitter; this diff does not widen that seam.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_11: **Output handling:** Substring match on `_preview_out` for the header was already the primary touch rule; removing the warning branch does not weaken matching—it removes a false-positive touch path. A custom renderer could still spoof the header via env override; that was true before and is test/harness scope.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Output handling:** Substring match on `_preview_out` for the header was already the primary touch rule; removing the warning branch does not weaken matching—it removes a false-positive touch path. A custom renderer could still spoof the header via env override; that was true before and is test/harness scope.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_12: **Plan content:** `plan.txt` is still emitted through `emit-design-plan-preview.sh` when present; this change does not alter plan read/emit or redaction. Repeated missing-plan warnings are fixed strings with no file content—no new disclosure.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Plan content:** `plan.txt` is still emitted through `emit-design-plan-preview.sh` when present; this change does not alter plan read/emit or redaction. Repeated missing-plan warnings are fixed strings with no file content—no new disclosure.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_13: **Operational impact:** Fixing sentinel suppression on repair improves operator visibility (warnings and preview re-render), which is neutral-to-positive for session integrity, not a new attack vector.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Operational impact:** Fixing sentinel suppression on repair improves operator visibility (warnings and preview re-render), which is neutral-to-positive for session integrity, not a new attack vector. Acceptance criteria from the plan are met from a security lens; no injection, authz bypass, secret leakage, or path-traversal regression introduced.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_14: Early-exit on existing sentinel (lines 89–90) is unchanged and still correct once a real header has been shown.
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: - Early-exit on existing sentinel (lines 89–90) is unchanged and still correct once a real header has been shown.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_15: `emit-design-plan-preview.sh` still emits the exact missing-plan string only when `plan.txt` is missing/empty (lines 103–105); that path no longer satisfies touch — aligned with acceptance.
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: - `emit-design-plan-preview.sh` still emits the exact missing-plan string only when `plan.txt` is missing/empty (lines 103–105); that path no longer satisfies touch — aligned with acceptance.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_16: Harness inversion would fail on unfixed code (old behavior touched sentinel on warning).
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: - Harness inversion would fail on unfixed code (old behavior touched sentinel on warning).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_17: Missing→repair case (`D_PV5B`) exercises the regression path the issue describes.
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: - Missing→repair case (`D_PV5B`) exercises the regression path the issue describes. Intentional tradeoffs from the plan (not defects): repeated missing-plan warnings on every Step 3 re-entry until repair; existence-based sentinel (no mtime/content invalidation after a successful preview). ---
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_22

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_22: `run-step3-review.sh`: One `case` branch removed, comment updated — single-branch `case`/`esac` is syntactically valid Bash
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: - `run-step3-review.sh`: One `case` branch removed, comment updated — single-branch `case`/`esac` is syntactically valid Bash
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_23

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_23: `run-step3-review.md`: Responsibility 0 extended with the new sentinel-touch contract — accurate and inline with behavior
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: - `run-step3-review.md`: Responsibility 0 extended with the new sentinel-touch contract — accurate and inline with behavior
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_24

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_24: `test-run-step3-review.sh`: Existing test renamed+inverted; new `D_PV5B` regression block added with the two-phase missing→repair scenario
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: - `test-run-step3-review.sh`: Existing test renamed+inverted; new `D_PV5B` regression block added with the two-phase missing→repair scenario The new test's `assert_contains "$out" '## Plan Candidate for Review'` captures output via `2>&1` — the same pattern already used in the existing disallowed-tmpdir test block visible at the bottom of the diff, so it's a validated idiom in this harness. Plan fidelity is complete: all three plan-specified files are touched, the `--no-preview` path is untouched, no new flags or result-env keys are introduced.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: risk-integration: skills/design/scripts/test-run-step3-review.sh:244-304
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No test for repeated missing-plan re-entry re-warn behavior documented in plan edge cases Operator triggers Step 3 twice while plan.txt remains missing; a partial regression could suppress output on the second entry while leaving sentinel absent, and current tests would still pass after a single missing-plan call Add a second consecutive --preview-only call with missing plan; assert warning text in stdout and sentinel still absent
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: risk-integration: skills/design/scripts/test-run-step3-review.sh:263-304
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Missing→repair regression uses header stub instead of default emit-design-plan-preview.sh on repair step Real emitter could change header formatting (extra whitespace, renamed heading) while stub tests stay green; driver substring gate would stop touching sentinel If feasible, repair step should call default renderer with restored plan.txt and assert header + sentinel
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: risk-integration: skills/design/scripts/run-step3-review.sh:89-90
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Fix does not invalidate sentinels created by pre-fix warning-path touch Sessions that already have .step3-entry-plan-printed from the old bug still skip preview after plan.txt repair even on fixed code Document manual sentinel deletion or add migration invalidation when plan.txt becomes non-empty
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_9: **Path safety:** Sentinel `touch` still targets `"$_canonical_tmpdir/.step3-entry-plan-printed"` only after `larch_design_tmpdir_validate` and `cd … && pwd -P` (see ```86:112:skills/design/scripts/run-step3-review.sh```). Allowlist rejects `..`, newlines, and non-directory leaf symlinks (`scripts/lib-design-tmpdir.sh`).
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Path safety:** Sentinel `touch` still targets `"$_canonical_tmpdir/.step3-entry-plan-printed"` only after `larch_design_tmpdir_validate` and `cd … && pwd -P` (see ```86:112:skills/design/scripts/run-step3-review.sh```). Allowlist rejects `..`, newlines, and non-directory leaf symlinks (`scripts/lib-design-tmpdir.sh`).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

