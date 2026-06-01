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

### FINDING_10: Python sets `code_fix_attempted` before per-job machinery runs
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, dyn-exhaustion-predicate-output.txt
- **Severity**: nit
- **Concern**: `code_fix_attempted` is set from `bool(classified.fixable)` immediately after the waterfall wins, before the per-job loop body runs. This is mostly aligned with Bash’s per-job-entry gate (`ci_failed_count > 0`) but looser than “machinery ran”; borderline cases may reach `fix-exhausted` / autonomous exit 3 earlier than Bash.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From dyn-exhaustion-predicate-output.txt: Only set `code_fix_attempted` after at least one fixable job completes prep (or after the first `verify_job_locally` / RCC invocation), and mirror the same stricter gate in Bash if product intent requires “machinery ran” rather than “fixable jobs present.”

### FINDING_11: Step 8 harness only greps token presence
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-implement-step8-exit3-first-fixer.sh` greps for token presence, not Exit 3 When-clause grouping. A future edit could mention `ci-fix-exhausted` elsewhere while breaking autonomous trigger wiring.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_12: Deeply nested `run_evaluate_failure` fix-loop in ship-pr.sh
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The fix-loop has deeply nested readiness/defer/dispatch branches, making parity with Python harder to verify and increasing risk of missing a defer arm on future edits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_13: #3334 fix-loop helper does not prove dispatch ran
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-ship-pr-fix-loop-3334.inc.sh` does not prove the fix loop ran; implementation could skip rerun/fix and still pass with exit 4.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_14: No test for ready-only upfront log reuse on iteration 1
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: No test covers ready-only upfront log reuse on fix-loop iteration 1; broken stash wiring could double-fetch or mis-classify without failing existing tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_15: `ci_failed_rc` defer path lacks explicit defer log
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Non-0, non-3 `ci_failed_rc` defers correctly but lacks an explicit defer log; ops only see Warnings `record_failure`, making defer harder to distinguish from silent skip.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_16: Untrusted CI log text drives blind rerun before fix
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Blind rerun vs fix is decided by substring matching on GitHub Actions log text. On fork or otherwise untrusted CI, job output can include network-error phrases and trigger a blind rerun, wasting retry budget. Document CI logs as untrusted control input in SECURITY.md; consider fix-first default or extra corroboration for fork/untrusted CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_17: `ci-fix-exhausted` expands autonomous orchestrator CI-fix exposure
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `ci-fix-exhausted` routes to the same autonomous main-agent CI-fix sub-procedure as `first-fixer-non-health`. After substantive in-script exhaustion, redacted CI logs can drive up to three orchestrator write/commit/push cycles. Document `ci-fix-exhausted` in SECURITY.md with untrusted-log guidance; keep substantive-attempt and fork guards.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_18: Python performs extra upfront log fetch when transient budget exhausted
- **Reviewer(s)**: dyn-bash-python-parity-output.txt
- **Severity**: latent
- **Concern**: When `transient_retries >= 1`, Bash skips the entire upfront block (`scripts/ship-pr.sh:2504–2526`) while Python always calls `collect_failed_logs` (~1004) but only stashes when under the cap (~1006–1021), causing extra I/O without a logic fork on the gate itself.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-python-parity-output.txt: Wrap the upfront `collect_failed_logs` call in the same `transient_retries < CI_MONITOR_TRANSIENT_RERUN_MAX` guard as the rerun/stash logic, or document the intentional extra probe if you prefer simpler Python control flow.

### OOS_1: [OUT_OF_SCOPE] `needs_user_bail_reason` vs autonomous bail helper naming
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-exhaustion-predicate-output.txt
- **Severity**: nit
- **Concern**: `needs_user_bail_reason` includes autonomous tokens excluded by `is_autonomous_exit3_bail_reason` (e.g. `ci-fix-exhausted` listed at `scripts/ship-pr.sh:1720–1722` vs narrower handling at 1728–1731). Confusing for new readers; pre-existing, not introduced by this diff. Orchestrator behavior depends on the narrower helper plus `BAIL_NEEDS_USER_INPUT=false` at exit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From dyn-exhaustion-predicate-output.txt: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] Branch bundles unrelated commits beyond #3334
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Branch contains commits unrelated to #3334 (#3314, #3297, #3338, etc.). Unrelated harness failures could block merge while reviewing ship-pr changes only. Consider isolating the #3334 commit or running full relevant-checks / harness splits before merge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] Codex Step 2 grant narrowing (#3314)
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `scripts/launch-codex-implement.sh` grant narrowed with symlink and IMPLEMENT_TMPDIR-root rejection; reduces risk of Codex writing orchestrator-owned session artifacts; unrelated to #3334 but present on the branch. No action required for #3334.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### OOS_4: [OUT_OF_SCOPE] Missing per-job exhaustion test as regression gap for push-failed predicate
- **Reviewer(s)**: dyn-exhaustion-predicate-output.txt
- **Severity**: latent
- **Concern**: Plan-listed `test_evaluate_failure_per_job_exhausted_routes_needs_user_input` is absent; the push-failed `code_fix_attempted_on_ready_log` gap has no targeted regression in `python/test_ci_monitor.py`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-exhaustion-predicate-output.txt: Address the concern above.

### OOS_5: [OUT_OF_SCOPE] Planned test absence would have caught ordering drift
- **Reviewer(s)**: dyn-bash-python-parity-output.txt
- **Severity**: latent
- **Concern**: Plan-listed `test_evaluate_failure_per_job_exhausted_routes_needs_user_input` is not in `python/test_ci_monitor.py`; only `test_evaluate_failure_exhausted_routes_needs_user_input` (~774) with winning tier via `launcher_exit=0`. That gap would have caught per-job-before-vendor ordering drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-python-parity-output.txt: Address the concern above.

### OOS_6: [OUT_OF_SCOPE] Pre-existing Bash per-job-before-vendor vs Python vendor-first structure
- **Reviewer(s)**: dyn-bash-python-parity-output.txt
- **Severity**: latent
- **Concern**: Bash runs `run_per_job_local_fix_loop` before `run_ci_fix_vendor`; Python runs vendor waterfall inside `run_ci_fix` before the per-job loop. Predicate text claims a single contract but entry points differ structurally across trees.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-python-parity-output.txt: Address the concern above.

### OOS_7: [OUT_OF_SCOPE] Verified — Python `fix-exhausted` does not fall through to stall in `monitor()`
- **Reviewer(s)**: dyn-exit-routing-output.txt
- **Severity**: nit
- **Concern**: `python/ci_monitor.py:1083-1084` returns `fix-exhausted` / `ci-fix-exhausted`; `monitor()` handles it at 1211-1218 with `Outcome.NEEDS_USER_INPUT` before generic STALLED at 1225-1228. No routing defect.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_8: [OUT_OF_SCOPE] Verified — Bash autonomous exit 3 wiring for `ci-fix-exhausted`
- **Reviewer(s)**: dyn-exit-routing-output.txt
- **Severity**: nit
- **Concern**: `is_autonomous_exit3_bail_reason` includes `ci-fix-exhausted`; terminal exhaustion sets `BAIL_NEEDS_USER_INPUT=false`; `bail` handler skips needs-user when autonomous reason matches. No routing defect.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_9: [OUT_OF_SCOPE] Verified — implement SKILL groups both autonomous exit-3 tokens
- **Reviewer(s)**: dyn-exit-routing-output.txt
- **Severity**: nit
- **Concern**: `skills/implement/SKILL.md:1169,1182` groups `first-fixer-non-health` and `ci-fix-exhausted` in the autonomous When clause; `scripts/test-implement-step8-exit3-first-fixer.sh:19-20` greps both strings.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_10: [OUT_OF_SCOPE] Pre-existing stall-recovery / structure test gaps for `ci-fix-exhausted`
- **Reviewer(s)**: dyn-exit-routing-output.txt
- **Severity**: nit
- **Concern**: `skills/implement/scripts/stall-recovery-report.sh:251` allowlists `first-fixer-non-health` but not `ci-fix-exhausted`; `scripts/test-implement-structure.sh:233-247` structural awk still only requires `first-fixer-non-health` in the Exit 3 block (weaker than dedicated step8 test).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-exit-routing-output.txt: Address the concern above.
