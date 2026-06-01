### FINDING_1: Fix-loop test regressions still assume vendor dispatch on gh-run-logs failure
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Concern**: Two fix-loop regressions still require vendor dispatch on `gh-run-logs` failure. Scenario: FINDING_3 stops calling `run_ci_fix_vendor` when `gh_logs_rc` is not 0/3; `vendor_verify_empty_tsv` (4087-4142) expects exit 0 after gh-run-logs exit 1 and `vendor_verify_rc2_on_gh_logs_failed_branch` (4145-4175) expects `STALL_STEP=10-head-changed` via mocked `run_ci_fix_vendor` return 2 — both will fail under the proposed defer path (defer-only outer exhaustion → `STALL_STEP=10-max-retries`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Add these cases to the Testing strategy: rewrite `vendor_verify_empty_tsv` to assert no vendor dispatch and exit 4 on error-only exhaustion; replace `vendor_verify_rc2_on_gh_logs_failed_branch` with the planned error-log defer regression (or drop it if redundant with the NEW case at plan line 87)

---


### FINDING_2: Python substantive-attempt flag diverges from unified Bash+Python predicate
- **Reviewer(s)**: Cursor-Requirements, Cursor-dyn-bash-python-parity
- **Severity**: important
- **Concern**: The unified substantive-attempt contract sets the flag when Bash enters `run_per_job_local_fix_loop` with `ci_failed_count > 0` (`scripts/ship-pr.sh:2579-2581`), even if the loop returns non-zero and the vendor waterfall later exhausts without `vendor_rc==4`. The Python bullet in the plan narrows the flag to `run_ci_fix` results (`verify-failed` / verification-retry only). Because `run_ci_fix` runs the vendor waterfall before per-job work (`python/ci_monitor.py:909-948`), a ready-log/ready-jobs path can exhaust tiers with `waterfall-failed` and never set the flag while Bash would have set it on per-job entry — outer exhaustion becomes exit 4/`STALLED` in Python vs exit 3/`ci-fix-exhausted` in Bash for the same ready-log/ready-job churn.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Make the Python bullet defer to the unified predicate and spell a Python mapping (e.g. set after `run_ci_fix` when ready logs+jobs and fix machinery actually ran—tier launch or verify-failed—not on immediate `no launcher tiers`/`all tiers failed`/`push failed` alone); add/adjust a pytest that exhausts after per-job-style work without `verify-failed` if that path exists post-change
  - From Cursor-dyn-bash-python-parity: Replace plan.txt:60-63 tracking text with the unified predicate bullets verbatim; specify setting `code_fix_attempted_on_ready_log` inside `run_ci_fix` when `classified.fixable` is non-empty and the per-job phase runs (parity with Bash entry), plus on `verify-failed` and verification-retry equivalents; add/adjust a pytest that exhausts after per-job machinery without `verify-failed` and expects `fix-exhausted`, mirroring the rewritten `ci_fix_exhausted` Bash case

---


### FINDING_3: Step 8+ Exit 3 SKILL prose omits ci-fix-exhausted from autonomous trigger and fall-through
- **Reviewer(s)**: Cursor-dyn-exit-contract-sync
- **Severity**: important
- **Concern**: Step 8+ Exit 3 prose only says to extend the autonomous trigger; it does not require editing the existing When/fall-through sentences. Scenario: After exit 3 with `BAIL_REASON=ci-fix-exhausted`, the orchestrator still matches only `first-fixer-non-health` at line 1169 and treats other `needs_user_bail_reason` tokens (line 1182) as AskUserQuestion — skipping the autonomous sub-procedure and defeating `BAIL_NEEDS_USER_INPUT=false` for substantive fix exhaustion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-exit-contract-sync: Add explicit SKILL edits: group `ci-fix-exhausted` with `first-fixer-non-health` in the does-not-set-`BAIL_NEEDS_USER_INPUT=true` sentence; change the When clause to `BAIL_REASON=first-fixer-non-health` or `BAIL_REASON=ci-fix-exhausted`; add `ci-fix-exhausted` after-autonomous-fall-through beside `first-fixer-non-health` at line 1182

