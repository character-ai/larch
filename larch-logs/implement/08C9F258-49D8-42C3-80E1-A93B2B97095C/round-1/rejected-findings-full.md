### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: Python sets `code_fix_attempted` before per-job machinery runs
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, dyn-exhaustion-predicate-output.txt
- **Severity**: nit
- **Concern**: `code_fix_attempted` is set from `bool(classified.fixable)` immediately after the waterfall wins, before the per-job loop body runs. This is mostly aligned with Bash’s per-job-entry gate (`ci_failed_count > 0`) but looser than “machinery ran”; borderline cases may reach `fix-exhausted` / autonomous exit 3 earlier than Bash.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From dyn-exhaustion-predicate-output.txt: Only set `code_fix_attempted` after at least one fixable job completes prep (or after the first `verify_job_locally` / RCC invocation), and mirror the same stricter gate in Bash if product intent requires “machinery ran” rather than “fixable jobs present.”


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: Step 8 harness only greps token presence
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-implement-step8-exit3-first-fixer.sh` greps for token presence, not Exit 3 When-clause grouping. A future edit could mention `ci-fix-exhausted` elsewhere while breaking autonomous trigger wiring.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: Deeply nested `run_evaluate_failure` fix-loop in ship-pr.sh
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The fix-loop has deeply nested readiness/defer/dispatch branches, making parity with Python harder to verify and increasing risk of missing a defer arm on future edits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: #3334 fix-loop helper does not prove dispatch ran
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-ship-pr-fix-loop-3334.inc.sh` does not prove the fix loop ran; implementation could skip rerun/fix and still pass with exit 4.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: No test for ready-only upfront log reuse on iteration 1
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: No test covers ready-only upfront log reuse on fix-loop iteration 1; broken stash wiring could double-fetch or mis-classify without failing existing tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: `ci_failed_rc` defer path lacks explicit defer log
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Non-0, non-3 `ci_failed_rc` defers correctly but lacks an explicit defer log; ops only see Warnings `record_failure`, making defer harder to distinguish from silent skip.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: Untrusted CI log text drives blind rerun before fix
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Blind rerun vs fix is decided by substring matching on GitHub Actions log text. On fork or otherwise untrusted CI, job output can include network-error phrases and trigger a blind rerun, wasting retry budget. Document CI logs as untrusted control input in SECURITY.md; consider fix-first default or extra corroboration for fork/untrusted CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_17: `ci-fix-exhausted` expands autonomous orchestrator CI-fix exposure
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `ci-fix-exhausted` routes to the same autonomous main-agent CI-fix sub-procedure as `first-fixer-non-health`. After substantive in-script exhaustion, redacted CI logs can drive up to three orchestrator write/commit/push cycles. Document `ci-fix-exhausted` in SECURITY.md with untrusted-log guidance; keep substantive-attempt and fork guards.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_18: Python performs extra upfront log fetch when transient budget exhausted
- **Reviewer(s)**: dyn-bash-python-parity-output.txt
- **Severity**: latent
- **Concern**: When `transient_retries >= 1`, Bash skips the entire upfront block (`scripts/ship-pr.sh:2504–2526`) while Python always calls `collect_failed_logs` (~1004) but only stashes when under the cap (~1006–1021), causing extra I/O without a logic fork on the gate itself.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-python-parity-output.txt: Wrap the upfront `collect_failed_logs` call in the same `transient_retries < CI_MONITOR_TRANSIENT_RERUN_MAX` guard as the rerun/stash logic, or document the intentional extra probe if you prefer simpler Python control flow.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

