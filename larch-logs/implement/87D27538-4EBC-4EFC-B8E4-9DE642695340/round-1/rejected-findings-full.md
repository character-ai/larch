### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: risk-integration: scripts/test-lint-fix-loop.sh:239-262
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Coder-owned commit acceptance tested only at step3, not ship-pr-ci-per-job. Per-job site-specific regressions in forbidden-path or branch guards would not be caught by case 1. Add per-job case mirroring case 1 with --target-cmd-args-file.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: risk-integration: scripts/test-ship-pr.sh:3267-3354
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] ci_per_job_head_changed omits Phase B and relevant-checks assertions present in ci_per_job_happy. Push/CI replay could pass while local verification or step10 gate is skipped. Align assertions with ci_per_job_happy (env/make rerun counts, relevant-checks call log).
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_19: risk-integration: scripts/lint-fix-loop.sh:366-368
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Post-dispatch forbidden working-tree revert fails the run after a valid coder-owned commit is already on HEAD. Coder commits a passing fix then leaves a dirty forbidden path; revert succeeds but status is forbidden-path-violation, per-job returns dispatch-failed, and the good commit may never be pushed (variant of #2909). Keep fail-closed behavior but document it and/or add a harness case; consider whether revert-only violations should still emit applied when HEAD commit content is clean.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_22

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_22: correctness: scripts/lint-fix-loop.sh:347-372
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Accepted coder-commit path omits working-tree delta paths from LINT_FIX_DELTA_PATHS_FILE. Coder commits fix A and leaves allowlisted uncommitted untracked B; B may not be staged on push via delta allowlist (tracked dirt still handled in ship-pr). Union committed diff with delta_paths_after_dispatch if untracked carry-forward must be guaranteed.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_24

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_24: risk-integration: scripts/test-ship-pr.sh:3267-3353
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Per-job happy-path rewrite uses stub lint-fix only, not real git HEAD movement. Stub proves wiring; production coupling of applied + local commit + push is only covered in test-lint-fix-loop.sh. Optional end-to-end ship-pr fixture with real lint-fix-loop.sh copy.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: code-quality: scripts/test-lint-fix-loop.sh:83-219
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Five write_wrapper_* helpers duplicate identical external-agent argv parsing. Fixture churn copies the same parser block five times, increasing review burden and typo risk. Factor a write_stub_wrapper helper with a per-case body fragment.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: code-quality: scripts/test-ship-pr.sh:3059-3354
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] ci_per_job_head_changed duplicates ci_per_job_happy stubs and uses a misleading fixture name. Future CI recovery stub changes must be edited in two places; the name suggests stall behavior though the test now expects success. Share a write_per_job_ci_recovery_stubs helper and rename the repo/fixture.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: code-quality: scripts/lint-fix-loop.sh:349-356
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Three identical fail_status calls for head-changed guards. Logs do not distinguish branch vs ancestor vs dirty-baseline failures without reading source. Combine guards into one compound if or a small reject helper.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

