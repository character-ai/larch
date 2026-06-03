# Review Round 2

- Mode: `diff`
- 7 accepted, 9 rejected (9 exonerated)

## Accepted Findings

### FINDING_1: Python sets substantive flag from fixable presence before tier launch
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-python-parity-output.txt, dyn-flag-predicate-correctness-output.txt, dyn-test-exhaustion-discrimination-output.txt
- **Severity**: important
- **Concern**: `run_ci_fix` initializes `code_fix_attempted` from `bool(classified.fixable)` before the launcher tier waterfall and propagates it on `all tiers failed` returns before the per-job loop runs. With ready logs and fixable jobs but every launcher tier failing (`winning_tier is None`), Python returns `fix-exhausted` / `ci-fix-exhausted` (autonomous exit 3) while Bash `ci_fix_launcher_only_exhausted` stalls (exit 4) because vendor/per-job machinery never ran. This violates the unified substantive-attempt predicate: set the flag only after per-job loop entry (post winning tier), on `verify-failed`, or on verification-retry—not from fixable presence alone.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-bash-python-parity-output.txt: In `run_ci_fix`, drop the upfront `bool(classified.fixable)` assignment; set `code_fix_attempted_on_ready_log` only when the per-job loop over `classified.fixable` is entered (after `winning_tier`), on `verify-failed`, or on verification-retry re-drive—mirroring Bash. Do not pass the flag on `all tiers failed` / `push failed` unless one of those paths ran. Add a Python regression with ready logs, empty/zero fixable job dispatch, winning tier + push failure → `waterfall-failed` / `STALLED`, not `ci-fix-exhausted`.
  - From dyn-flag-predicate-correctness-output.txt: Move `code_fix_attempted = True` to after a winning tier and entry into the `for job in classified.fixable` loop (or reorder to run per-job local fixes before the vendor waterfall, matching Bash); return `code_fix_attempted_on_ready_log=False` on `"all tiers failed"` when only launchers were attempted; update the per-job-exhausted test to require actual per-job execution (or launcher `verify-failed` / verification-retry) before expecting `fix-exhausted`.
  - From dyn-test-exhaustion-discrimination-output.txt: Set `code_fix_attempted` only after the per-job loop over `classified.fixable` runs (or on `verify-failed` / verification-retry / push-fail after a winning tier), mirroring Bash; do not pass `bool(classified.fixable)` on the early `all tiers failed` return. Add a Python test with fixable jobs and an all-fail `launch_fn` expecting `waterfall-failed`, not `fix-exhausted`.


### FINDING_2: Python exhaustion tests encode wrong substantive predicate
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-test-exhaustion-discrimination-output.txt
- **Severity**: important
- **Concern**: Multiple Python tests expect `fix-exhausted` when only launchers fail and per-job machinery never runs, locking in the wrong predicate from production code. `test_evaluate_failure_per_job_exhausted_routes_needs_user_input` (809–841) uses all-failing tiers (`winning_tier is None`) without entering the per-job loop. `test_evaluate_failure_exhausted_routes_needs_user_input` (728–760) similarly expects fix-exhausted on launcher-only failure. Tests pass while production Python mis-routes launcher-only fixable failures to autonomous CI-fix; parity with rewritten Bash is illusory.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-test-exhaustion-discrimination-output.txt: Use a `launch_fn` that wins on the first tier (`wrapper_rc=0`, `launcher_exit=0`), drive `make py-lint` failure / verification-retry or outer-cap exhaustion without `verify-failed`, and assert `fix-exhausted` only after per-job code paths execute; add a separate case with fixable jobs and all-fail launchers expecting `waterfall-failed`.


### FINDING_3: Missing regression for fixable jobs plus launcher-only exhaustion
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-test-exhaustion-discrimination-output.txt
- **Severity**: important
- **Concern**: No Python test covers fixable jobs (`python-lint` or other `CI_FIXABLE_JOBS` member) with all launcher tiers failing and no per-job/vendor verify path. `test_evaluate_failure_launcher_exhausted_stalls` uses empty `jobs: []`, so it cannot catch the production gap. Regression can reintroduce autonomous routing on launcher-only failures without a failing pytest. Bash `ci_fix_launcher_only_exhausted` only covers `FAILED_JOBS_COUNT=0`; fixable-job launcher-only stall is untested on both sides.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-test-exhaustion-discrimination-output.txt: Add a case with `python-lint` (or other `CI_FIXABLE_JOBS` member) in `jobs_json`, all-fail `launch_fn`, and assert `waterfall-failed` with `detail != "ci-fix-exhausted"`; keep the empty-jobs case as a secondary guard.


### FINDING_4: Push failure after winning vendor tier diverges Python vs Bash
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-bash-python-parity-output.txt
- **Severity**: important
- **Concern**: After a winning vendor tier, push failure sets the substantive flag in Python (`code_fix_attempted or bool(waterfall.winning_tier)`) but not on equivalent Bash vendor-only exhaustion (`FAILED_JOBS_COUNT=0` / no per-job path). Vendor applies fixes, git push fails: Python outer exhaustion → `ci-fix-exhausted` exit 3; Bash likely exit 4 stall without autonomous CI-fix. Violates launcher/push carve-out relative to `ci_fix_launcher_only_exhausted`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-bash-python-parity-output.txt: In `run_ci_fix`, drop the upfront `bool(classified.fixable)` assignment; set `code_fix_attempted_on_ready_log` only when the per-job loop over `classified.fixable` is entered (after `winning_tier`), on `verify-failed`, or on verification-retry re-drive—mirroring Bash. Do not pass the flag on `all tiers failed` / `push failed` unless one of those paths ran. Add a Python regression with ready logs, empty/zero fixable job dispatch, winning tier + push failure → `waterfall-failed` / `STALLED`, not `ci-fix-exhausted`.


### FINDING_5: CI_FIX_REBASE_PENDING sets substantive flag without ready-log/job gate
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, dyn-flag-predicate-correctness-output.txt
- **Severity**: important
- **Concern**: `CI_FIX_REBASE_PENDING` sets `_code_fix_attempted_on_ready_log=true` at the top of each fix-loop iteration without re-checking `gh_logs_rc` / `ci_failed_rc` on that iteration. `CI_FIX_REBASE_PENDING` is only cleared on successful push, not on terminal `exit_stall` or `ci-fix-exhausted` exit. If persisted state still has `CI_FIX_REBASE_PENDING=true` when `run_evaluate_failure` runs again, the next call can route to autonomous `ci-fix-exhausted` without ready logs/jobs or fix machinery in the current evaluation—violating the same-attempt predicate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-flag-predicate-correctness-output.txt: Clear `CI_FIX_REBASE_PENDING` at the start of `run_evaluate_failure` (or on all terminal exhaustion paths), and only set `_code_fix_attempted_on_ready_log` in the pending branch if it was already true earlier in the same invocation or after a fresh ready-log/ready-job fetch confirms readiness.


### FINDING_7: Quoted heredoc breaks defer-test sentinel assertions
- **Reviewer(s)**: dyn-test-exhaustion-discrimination-output.txt
- **Severity**: important
- **Concern**: `ci_fix_jobs_in_progress_defer` and `ci_fix_gh_logs_error_defer` build `launch-cursor-ci.sh` with a quoted heredoc (`<<'STUB'`), so `$call_dir` is not expanded into the stub. At runtime the launcher writes to `/sentinel-fix.txt` instead of `$call_dir/sentinel-fix.txt`, while assertions check `$call_dir/sentinel-fix.txt`. Vendor dispatch would not fail the test (false negative). `vendor_verify_empty_tsv` correctly uses unquoted `<<STUB`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-test-exhaustion-discrimination-output.txt: Use unquoted `<<STUB` (or embed the expanded path) for these launch stubs, matching `vendor_verify_empty_tsv`.


### FINDING_9: Codex launcher `_codex_canonical_existing_dir` missing `..` and control-char guards
- **Reviewer(s)**: dyn-codex-sandbox-symlink-output.txt
- **Severity**: important
- **Concern**: `_codex_canonical_existing_dir` only rejects the parent path when it is itself a symlink and does not mirror `launch-review.sh`'s helper, which also rejects control characters and any `..` substring before `(cd "$p" && pwd -P)`. A caller can pass `--manifest-path "$TMP/codex-step2-out/../manifest.json"`; `pwd -P` canonicalizes `--add-dir` to `$TMP` (implement tmpdir root). The `SESSION_TMPDIR == IMPLEMENT_TMPDIR` guard runs only when `IMPLEMENT_TMPDIR` is non-empty, so invocations with `IMPLEMENT_TMPDIR` cleared skip that guard and can grant Codex write access over orchestrator-owned root artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-codex-sandbox-symlink-output.txt: Port the `..` and control-char predicates from `launch-review.sh` into `_codex_canonical_existing_dir`, and either require a non-empty `IMPLEMENT_TMPDIR` on the Codex implement path (exit 2 if unset) or always reject when canonical `SESSION_TMPDIR` equals canonical `dirname` of `--sidecar-log` / other trusted tmpdir anchor, not only when the env var is set.


