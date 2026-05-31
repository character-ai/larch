### FINDING_1: run_waterfall ignores TierAttempt.failure; log KV short-circuit gap
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `run_waterfall` short-circuits only from `LAUNCHER_FAILURE_CLASS=` lines in `failure_log` (via `parse_launcher_failure_class`) and ignores `TierAttempt.failure`. `launch_fn` can set `failure_class` (e.g. `other` via `classify_launch_failure`) without emitting matching log KVs, so the waterfall does not perform first-fixer-non-health bail and may cascade through later tiers (e.g. defaulting to health). Related API drift: planned injectable `classify_fn` is not implemented; integrators may expect classification without capture logs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_11: Missing transient-retry tests for run_list, run_view, failed_jobs
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Idempotent `gh` retry behavior is only tested for `pr_view` and `pr_for_branch`, not `run_list` / `run_view` / `failed_jobs`. A transient failure on run list/view during a future Phase 2+ ship-pr port could fail to retry while PR reads do, diverging from bash retry semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add stub-runner transient retry and exhaustion tests for run_list, run_view, and failed_jobs matching the pr_view patterns.


### FINDING_13: test-relevant-checks lacks positive case with Python tools on PATH
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Harness lacks a positive case with all Python tools on PATH. Regression that never appends `py-lint` when tools exist would pass `test-relevant-checks` and only fail in manual/CI runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add Section 3n with stub ruff/pylint/pyright/pytest on PATH asserting both targets run.


### FINDING_14: Timeout test does not assert partial capture
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Timeout test does not assert partial capture. Partial `gh`/`git` output might be dropped on timeout without failing tests, violating the documented proc contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Assert non-empty stdout/stderr on a timeout result from a child that emits before blocking.


### FINDING_15: No unit test for `with_transient_retry` predicate branch
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: No unit test for `with_transient_retry` `predicate=` branch. Custom predicate retries (used by bash envelope paths) could regress silently in later phases.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add one predicate-driven retry test with a fake sleeper.


### FINDING_17: exit 0 classification lacks bash parity test
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: exit 0 classification lacks bash parity test present in `test-lib-external-launcher-common.sh`. Subtle drift on success classification might not be caught until cross-language CI parity runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add test_parity_classify_success mirroring the bash harness argv.


### FINDING_18: PR/issue titles passed to gh without redact
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `pr_create` and `issue_edit` pass title to `gh` without `redact.redact()`. After Phase 7 cutover, a PR or issue title containing a GitHub PAT or tmpdir path may be published to GitHub in cleartext.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### FINDING_2: gh read helpers raise ShipError; plan expects retriable last result
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Read helpers raise `ShipError` after transient retries via `_ensure_success`. Phase 7 orchestration cannot map exhausted transient `gh` reads to `Outcome.TRANSIENT` without catching `ShipError`. Plan text expects retried read exhaustion to return the last `CommandResult` / `StepResult` rather than raising.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_24: subprocess `text=True` lacks `errors=replace`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `text=True` subprocess capture in `proc.py` lacks `errors=replace`. Binary or invalid UTF-8 child output may crash `proc.run` instead of returning `CommandResult`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_3: Unused `json` import in git.py
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Unused `json` import; dead import may fail future unused-import lint.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_6: `run_list` silently skips malformed JSON rows
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `run_list` skips malformed / non-dict JSON array elements without error. Partial or changed `gh` JSON yields an incomplete run list; orchestrator may misread CI state, skip reruns, or target the wrong workflow.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_8: `pr_create` omits `--base` and `--assignee @me`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `pr_create` omits `--base` and `--assignee @me` present in `create-pr.sh`. Future cutover may open PRs against repo default instead of ship-pr-resolved `BASE_REF`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


