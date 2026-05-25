### FINDING_1: Relevant-checks fix loop not refactored onto shared helper
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-refactor-completeness-output.txt, dyn-per-job-loop-states-output.txt
- **Severity**: important
- **Concern**: `run_checks_with_lint_fix_loop` remains separate from `run_captured_cmd_then_fix_loop` despite the plan and acceptance criteria. The two loops already differ around `LINT_FIX_STATUS=no-changes`, empty output, and exhaustion handling, so future fixes can drift between relevant-checks and per-job CI recovery without test signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-refactor-completeness-output.txt, dyn-per-job-loop-states-output.txt: Address the concern above.

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

### FINDING_6: Duplicate CI job mapping can drift
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: CI job-name mapping is duplicated between `ci-failed-jobs.sh` job classification and `ship-pr.sh` per-job argv dispatch, while drift tests only pin one side. A CI job rename or addition can pass the existing drift test but fail or misroute at runtime.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_7: Per-job TSV values are used in paths without revalidation
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `ship-pr.sh` builds `IMPLEMENT_TMPDIR` path prefixes from TSV `job_name` and `shard` fields without reapplying the validation used by `ci-failed-jobs.sh`. A tampered TSV row could use path traversal in generated args or log filenames before `lint-fix-loop` consumes them.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_8: Cancelled and timed-out CI jobs are ignored
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `ci-failed-jobs.sh` only parses jobs with conclusion `failure`; cancelled or timed-out jobs can yield `FAILED_JOBS_COUNT=0`, causing the per-job loop to be skipped and narrower gates to run despite remote CI still not being green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_9: Per-job push trusts gh failed-job listing completeness
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: The per-job-only push path assumes `gh run view` lists all failed jobs. If secret-scan jobs such as `gitleaks` or `trufflehog` are omitted, the path could skip vendor recovery and push while remote secret-scan jobs remain failed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_10: Shared captured-command loop ignores `_RCC_MAX_ITER`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `run_captured_cmd_then_fix_loop` hardcodes iterations `1 2 3` despite having `_RCC_MAX_ITER`, so future cap tuning would not affect the actual attempt count.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_11: Inconsistent job-token separators complicate triage
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `ci-failed-jobs` KV output and `ship-pr` temporary paths use inconsistent `job:shard` vs `job-shard` formatting, making incident correlation harder.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_12: Mixed unfixable test does not prove lint ran before bail
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The mixed gitleaks+lint unfixable test does not assert that the lint local command ran and was fixed before the gitleaks bail, so a miswire could still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_13: New agent-sync helper lacks dedicated offline harness
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `scripts/check-focus-area-enum.sh` has no small dedicated harness, so regressions in focus-area grep logic are only caught by full `make agent-sync` or the CI job.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_14: lint-fix prompt display does not escape command metacharacters
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `lint-fix-loop.sh` interpolates `target_cmd_display` inside inline markdown backticks without escaping. If argv-file inputs are ever widened beyond the fixed dispatcher, backticks or newlines could alter prompt structure for the external coder.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_15: `_stage_and_push_ci_fixes` behavior is under-documented for per-job path
- **Reviewer(s)**: dyn-refactor-completeness-output.txt
- **Severity**: latent
- **Concern**: `_stage_and_push_ci_fixes` is not just a push primitive; when `checks_site` is non-empty it also runs the full relevant-checks gate. The per-job success path calls it that way after Phase B verification, which may be intended defense-in-depth but should be documented or split if mapped-job verification is meant to be sufficient.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-refactor-completeness-output.txt: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] ship-pr file size concentrates CI recovery logic
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `ship-pr.sh` has accumulated substantial CI recovery logic, increasing long-term maintenance cost as more CI jobs or recovery modes are added.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] Per-job path still runs relevant-checks before push
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The per-job path still runs relevant-checks before pushing, so remote-only job failures can remain possible even after local per-job verification succeeds.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] Outer retry clears bail metadata between attempts
- **Reviewer(s)**: dyn-per-job-loop-states-output.txt
- **Severity**: nit
- **Concern**: Each outer `_fix_attempt` clears `BAIL_REASON` and `BAIL_FAILURE_DETAIL_LOG` before re-running `ci-failed-jobs.sh` against the same run. This matches current verification-retry tests, but partial local fixes persist across attempts and may matter if vendor and per-job paths interact.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-per-job-loop-states-output.txt: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] Graceful degrade for ci-failed-jobs failures is wired correctly
- **Reviewer(s)**: dyn-per-job-loop-states-output.txt
- **Severity**: nit
- **Concern**: `run_evaluate_failure` graceful degrade when `ci-failed-jobs.sh` returns `1` or `3` records a warning and runs vendor recovery as expected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-per-job-loop-states-output.txt: Address the concern above.

### FINDING_20: [OUT_OF_SCOPE] Branch commit list is informational
- **Reviewer(s)**: dyn-per-job-loop-states-output.txt
- **Severity**: nit
- **Concern**: The reviewer reported the branch commits since `main`: `84c246ae`, `7bbd2199`, and `671dc47f`. This is contextual metadata, not a code finding.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-per-job-loop-states-output.txt: Address the concern above.
