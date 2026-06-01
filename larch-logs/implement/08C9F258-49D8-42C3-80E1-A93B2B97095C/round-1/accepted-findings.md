### FINDING_1: ship-pr.md:96 — stale ci-wait / substantive exhaustion exit contract
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-exit-routing-output.txt
- **Severity**: important
- **Concern**: The `ci-wait.sh` helper-contract bullet at line 96 still documents substantive `run_evaluate_failure` exhaustion as exit 4 stall (`STALL_STEP=10-max-retries`). The branch routes substantive CI-fix exhaustion to autonomous exit 3 with `BAIL_REASON=ci-fix-exhausted` and `BAIL_NEEDS_USER_INPUT=false`. Operators and `/implement` agents reading Helper Contracts before Invariants can miss the Step 8+ autonomous path keyed on `ci-fix-exhausted`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-exit-routing-output.txt: Update the `ci-wait.sh` bullet at line 96 to match line 130 and `scripts/ci-decide.md:7` (exit **3**, `ci-fix-exhausted`, autonomous path; reserve exit **4** for non-substantive / launcher-only / defer-only exhaustion).


### FINDING_2: ship-pr.md:130 — stale ci-failed-jobs vendor fallback prose
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Invariants prose still claims `ci-failed-jobs` failure falls back to `run_ci_fix_vendor`. After the change, `ci_failed_rc` not in `{0,3}` records warnings and defers without vendor dispatch; the doc misleads operators debugging defer loops.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_3: Bash vs Python substantive-attempt predicate and fix-loop ordering
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-python-parity-output.txt
- **Severity**: important
- **Concern**: The unified substantive-attempt contract diverges across trees. Bash sets `_code_fix_attempted_on_ready_log` when `run_per_job_local_fix_loop` is entered (`ci_failed_count > 0`) before the vendor waterfall; exhaustion after all launcher tiers fail routes to `ci-fix-exhausted` (exit 3). Python sets `code_fix_attempted` only after `run_waterfall` returns a winning tier; if every tier fails, `run_ci_fix` returns `waterfall-failed` without setting `code_fix_attempted_on_ready_log`, so `evaluate_failure` ends at STALLED (exit 4) instead of `fix-exhausted` / autonomous exit 3 on `LARCH_SHIP_PR_IMPL=python` cutover. Same scenario is covered for Bash in `scripts/test-ship-pr.sh` (~3418–3471) but lacks a Python parity test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-bash-python-parity-output.txt: Mirror Bash by setting and propagating `code_fix_attempted_on_ready_log` when ready logs + ready jobs exist and the per-job phase is entered (before or independent of tier success), e.g. set the flag as soon as `classified.fixable` is non-empty and jobs are ready, or restructure `run_ci_fix` to run the per-job phase before/alongside the vendor waterfall like Bash; add a Python test with fixable jobs and all tiers failing to lock parity.


### FINDING_4: Missing `test_evaluate_failure_per_job_exhausted_routes_needs_user_input`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The plan-required `test_evaluate_failure_per_job_exhausted_routes_needs_user_input` was not implemented. Per-job-only outer exhaustion without `verify-failed` is untested in Python; Bash `ci_fix_exhausted` behavior and push-fail / ordering regressions on the Python path would not be caught. Existing `test_evaluate_failure_exhausted_routes_needs_user_input` assumes a winning vendor tier via `launcher_exit=0`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_5: Python `push failed` omits `code_fix_attempted_on_ready_log`
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt, dyn-exhaustion-predicate-output.txt, dyn-bash-python-parity-output.txt
- **Severity**: important
- **Concern**: After a winning vendor tier, per-job verify, and local fix work, `run_ci_fix` sets `code_fix_attempted` but the `push failed` return omits `code_fix_attempted_on_ready_log`. Outer `evaluate_failure` only promotes the flag from `fix.code_fix_attempted_on_ready_log`, so substantive work followed by push failure stalls (`waterfall-failed` / exit 4) instead of `fix-exhausted` / `ci-fix-exhausted`. Bash keeps `_code_fix_attempted_on_ready_log=true` from per-job entry through push failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-exhaustion-predicate-output.txt: On the `push failed` branch (and any other post–per-job `waterfall-failed` exits after line 930), pass `code_fix_attempted_on_ready_log=code_fix_attempted` on the `FixResult`; add a `test_evaluate_failure_*` case where `classified.fixable` is non-empty, verify passes, and `stage_and_push` returns `pushed=False`, asserting `fix-exhausted` / `ci-fix-exhausted`.
  - From dyn-bash-python-parity-output.txt: Include `code_fix_attempted_on_ready_log=code_fix_attempted` (or `True` when the per-job loop ran) on the `push failed` return, and add a unit test that stubs a successful verify with a failed push and expects `fix-exhausted`.


### FINDING_6: `CI_FIX_REBASE_PENDING` verify-retry never sets substantive flag
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: CI_FIX_REBASE_PENDING verify-retry (stage rc 4) never sets `_code_fix_attempted_on_ready_log`. Vendor fix plus push failure leads to pending rebase; three deferred verify rc=4 attempts can exhaust without the flag, producing exit 4 stall instead of `ci-fix-exhausted` exit 3.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_7: Vendor-only verification retry with empty `fixable` omits substantive flag
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Vendor-only verification retry does not set the substantive flag when `classified.fixable` is empty. Ready logs, zero failed local jobs, and vendor verify-retry exhaustion: Bash routes to autonomous exit 3; Python can exit 4 stall.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_8: ship-pr.md:72 — exit codes omit `ci-fix-exhausted`
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt, dyn-exit-routing-output.txt
- **Severity**: important
- **Concern**: The Exit Codes section documents autonomous exit 3 only for `first-fixer-non-health`, not `ci-fix-exhausted`, even though `skills/implement/SKILL.md` and `scripts/ship-pr.sh` treat both identically for orchestrator routing (`BAIL_NEEDS_USER_INPUT=false`, autonomous Step 8+ path).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-exit-routing-output.txt: Extend the line-72 prose to list **`ci-fix-exhausted`** alongside `first-fixer-non-health` as exit-3 bails that leave `BAIL_NEEDS_USER_INPUT=false` for the same autonomous Step 8+ path.


### FINDING_9: `ci_fix_exhausted` integration test may be flaky without stubs
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `scripts/test-ship-pr.sh` (~3418–3471) `ci_fix_exhausted` lacks make/per-job stubs. If local per-job repair succeeds, the test may expect rc 3 but get rc 0.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


