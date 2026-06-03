### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: Structural SKILL grep for autonomous bail tokens
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `test-implement-step8-exit3-first-fixer.sh` only greps `ci-fix-exhausted`. Orchestrator prose could drop autonomous `When` grouping while grep still passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: Autonomous CI-fix path and hostile CI log trust boundary
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `ci-fix-exhausted` now triggers autonomous main-agent CI-fix before `AskUserQuestion`, using redacted CI logs as primary context. Hostile repo CI jobs can embed instruction-like text; more deterministic failures reach substantive fix then autonomous exit-3 instead of blind rerun churn, increasing unprompted edit/push attempts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: `needs_user_bail_reason` naming vs autonomous `ci-fix-exhausted`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `needs_user_bail_reason` includes autonomous tokens `ci-fix-exhausted` and `first-fixer-non-health`. The helper name may mislead orchestrators into assuming `BAIL_NEEDS_USER_INPUT=true` for `ci-fix-exhausted` despite the `is_autonomous` guard.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: Duplicated jittered-backoff blocks in `run_evaluate_failure`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Four duplicated jittered-backoff blocks in `run_evaluate_failure`. Future defer/backoff tweaks require four edits and risk asymmetric sleep behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: Python upfront log fetch when transient retry cap exhausted
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-bash-python-parity-output.txt
- **Severity**: latent
- **Concern**: Python always prefetches logs at `evaluate_failure` start; Bash skips the upfront `gh-run-logs.sh` block when `TRANSIENT_RETRIES >= 1`. Under exhausted transient budget, Python may perform an extra `gh` log fetch vs Bash on Phase 7 cutover. Stash/reuse behavior for blind rerun is otherwise aligned, but the extra upfront collect is a behavioral/API-call drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From dyn-bash-python-parity-output.txt: Optional parity: wrap the upfront `collect_failed_logs` call in the same `transient_retries < CI_MONITOR_TRANSIENT_RERUN_MAX` guard as the rerun branch, or document the extra fetch as an acceptable Python-only optimization.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

