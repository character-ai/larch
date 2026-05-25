# Review Round 2

- Mode: `diff`
- 8 accepted, 7 rejected (7 exonerated)

## Accepted Findings

### FINDING_1: Relevant-checks fix loop not refactored onto shared helper
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-refactor-completeness-output.txt, dyn-per-job-loop-states-output.txt
- **Severity**: important
- **Concern**: `run_checks_with_lint_fix_loop` remains separate from `run_captured_cmd_then_fix_loop` despite the plan and acceptance criteria. The two loops already differ around `LINT_FIX_STATUS=no-changes`, empty output, and exhaustion handling, so future fixes can drift between relevant-checks and per-job CI recovery without test signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-refactor-completeness-output.txt, dyn-per-job-loop-states-output.txt: Address the concern above.


### FINDING_10: Shared captured-command loop ignores `_RCC_MAX_ITER`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `run_captured_cmd_then_fix_loop` hardcodes iterations `1 2 3` despite having `_RCC_MAX_ITER`, so future cap tuning would not affect the actual attempt count.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_13: New agent-sync helper lacks dedicated offline harness
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `scripts/check-focus-area-enum.sh` has no small dedicated harness, so regressions in focus-area grep logic are only caught by full `make agent-sync` or the CI job.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_2: Per-job cap exhaustion falls through to vendor instead of unfixable bail
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-refactor-completeness-output.txt, dyn-per-job-loop-states-output.txt
- **Severity**: important
- **Concern**: When a per-job local fix loop exhausts, dispatch fails, or a multi-job pass has partial success plus one exhausted job, `run_per_job_local_fix_loop` returns `1`; `run_evaluate_failure` does not handle that code explicitly, so execution falls through to the broad vendor waterfall. This conflicts with the planned `exit 3` / `BAIL_REASON=ci-local-unfixable:<job>` handoff and can expose broader logs or invite unrelated vendor edits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-refactor-completeness-output.txt, dyn-per-job-loop-states-output.txt: Address the concern above.


### FINDING_3: Verification failures stall outer attempts instead of targeted per-job recovery
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-refactor-completeness-output.txt, dyn-per-job-loop-states-output.txt
- **Severity**: important
- **Concern**: Phase B verification returns `4` on the first failing job, triggering whole outer retries and eventual stall semantics rather than re-entering the per-job fix loop for the regressed job and bailing as locally unfixable after budget exhaustion. This also hides additional verification failures in the same sweep.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-refactor-completeness-output.txt, dyn-per-job-loop-states-output.txt: Address the concern above.


### FINDING_4: ship-pr docs disagree with implemented per-job bail behavior
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `scripts/ship-pr.md` says exhausted per-job repairs and verification failures exit `3` with `ci-local-unfixable`, while implementation and tests route some cases to vendor fallback or outer retry/stall. Operators and `/implement` Step 8 may mis-handle the actual behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_5: Plan-required ship-pr harness cases are missing
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-refactor-completeness-output.txt, dyn-per-job-loop-states-output.txt
- **Severity**: important
- **Concern**: `scripts/test-ship-pr.sh` lacks several plan-listed cases, including cap-exhausted bail, `gh` failure graceful degrade, per-job no-changes-after-fail, malformed or shard pins, and the refactored-loop byte-identical pin. Regressions in exhaustion, empty-log handling, degraded CI parsing, or relevant-checks/per-job divergence can ship without harness failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-refactor-completeness-output.txt, dyn-per-job-loop-states-output.txt: Address the concern above.


### FINDING_8: Cancelled and timed-out CI jobs are ignored
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `ci-failed-jobs.sh` only parses jobs with conclusion `failure`; cancelled or timed-out jobs can yield `FAILED_JOBS_COUNT=0`, causing the per-job loop to be skipped and narrower gates to run despite remote CI still not being green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


