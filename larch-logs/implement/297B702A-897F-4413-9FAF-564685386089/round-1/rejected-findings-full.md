### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: risk-integration: scripts/test-ship-pr.sh:5967-6107
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No end-to-end test that confirmed local harness failure yields documented exit 3/4 not raw harness exit 2. Unit tests pass while a future regression in evaluate-failure routing could still return exit 2 if only translation logic breaks. Add fix-loop-style subject asserting exit 3 with ci-local-unfixable (or stall 4) not exit 2 when harness fails under errexit.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: risk-integration: scripts/test-ship-pr.sh:6091-6107
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Harness capture test only covers failing command under set -e. Success path with errexit on is untested; a broken || pattern could wrongly leave _RCC_CMD_RC at 0 after failure or mishandle success. Add sub-case with exit-0 command asserting RCC_CMD_RC=0 and shell survival.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_17: architecture: scripts/test-ship-pr.sh:5967-6110
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Unit probes cover toggles and capture in isolation but not ship-pr.sh exiting with a documented code after a failing local harness in evaluate-failure. A regression in another errexit leak or unhardened helper invocation could restore raw exit 2 while errexit section tests still pass. Add a minimal subprocess test asserting exit 3/4 with BAIL_REASON not raw harness rc 2.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: code-quality: scripts/ship-pr.sh:1554-1572
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] run_pr_prep_phase duplicates save/restore around a helper that already manages errexit. Extra nesting and six lines per call site without added safety once the helper is fixed. Remove outer set +e wrappers and call the helper directly (plan allowed this simplification).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: code-quality: scripts/test-ship-pr.sh:6015-6033
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] prprep-first and prprep-recovery probes embed copy-pasted wrapper snippets instead of calling production entry points. Production wrapper edits may not update tests; probes could false-pass on stale patterns. Call run_pr_prep_phase with run_recovery_waterfall stubbed or share a small with_saved_errexit helper.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: code-quality: scripts/ship-pr.sh:1004,139
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] _had_errexit in OOS paths vs had_errexit in run_lint_fix_loop_capture for the same idiom. Minor inconsistency when searching or extending errexit patterns. Align variable naming with run_lint_fix_loop_capture.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

