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

### FINDING_6: Global write_stubs default may silently change unrelated fix-loop tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `write_stubs` now defaults `gh-run-logs` and `ci-failed-jobs` for every `make_repo`, replacing copied real `ci-failed-jobs.sh`. Unrelated fix-loop cases may change behavior (empty jobs, deterministic logs) without local overrides, causing silent regressions in `make test-ship-pr-fix-loop`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_7: Quoted heredoc breaks defer-test sentinel assertions
- **Reviewer(s)**: dyn-test-exhaustion-discrimination-output.txt
- **Severity**: important
- **Concern**: `ci_fix_jobs_in_progress_defer` and `ci_fix_gh_logs_error_defer` build `launch-cursor-ci.sh` with a quoted heredoc (`<<'STUB'`), so `$call_dir` is not expanded into the stub. At runtime the launcher writes to `/sentinel-fix.txt` instead of `$call_dir/sentinel-fix.txt`, while assertions check `$call_dir/sentinel-fix.txt`. Vendor dispatch would not fail the test (false negative). `vendor_verify_empty_tsv` correctly uses unquoted `<<STUB`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-test-exhaustion-discrimination-output.txt: Use unquoted `<<STUB` (or embed the expanded path) for these launch stubs, matching `vendor_verify_empty_tsv`.

### FINDING_8: Autonomous CI-fix expands prompt-injection reach after exhaustion
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `ci-fix-exhausted` now triggers autonomous main-agent CI-fix without `AskUserQuestion`, expanding write/commit/push cycles informed by redacted but untrusted CI logs. A compromised or malicious CI job prints instruction-like text; after in-script fix exhaustion the orchestrator autonomously edits the repo up to three times before user bail, amplifying prompt-injection reach versus stall-only behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_9: Codex launcher `_codex_canonical_existing_dir` missing `..` and control-char guards
- **Reviewer(s)**: dyn-codex-sandbox-symlink-output.txt
- **Severity**: important
- **Concern**: `_codex_canonical_existing_dir` only rejects the parent path when it is itself a symlink and does not mirror `launch-review.sh`'s helper, which also rejects control characters and any `..` substring before `(cd "$p" && pwd -P)`. A caller can pass `--manifest-path "$TMP/codex-step2-out/../manifest.json"`; `pwd -P` canonicalizes `--add-dir` to `$TMP` (implement tmpdir root). The `SESSION_TMPDIR == IMPLEMENT_TMPDIR` guard runs only when `IMPLEMENT_TMPDIR` is non-empty, so invocations with `IMPLEMENT_TMPDIR` cleared skip that guard and can grant Codex write access over orchestrator-owned root artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-codex-sandbox-symlink-output.txt: Port the `..` and control-char predicates from `launch-review.sh` into `_codex_canonical_existing_dir`, and either require a non-empty `IMPLEMENT_TMPDIR` on the Codex implement path (exit 2 if unset) or always reject when canonical `SESSION_TMPDIR` equals canonical `dirname` of `--sidecar-log` / other trusted tmpdir anchor, not only when the env var is set.

### FINDING_10: Codex launcher does not scan symlinks inside session tmpdir
- **Reviewer(s)**: dyn-codex-sandbox-symlink-output.txt
- **Severity**: latent
- **Concern**: Symlink rejection applies only to the immediate parent directory argument, not to entries inside `codex-step2-out/`. If an attacker can create a symlink under that directory before Codex runs (writable session cache), `--add-dir "$SESSION_TMPDIR"` may still follow it depending on Codex sandbox semantics, potentially allowing writes outside the intended subdir while the parent passes `-L`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-codex-sandbox-symlink-output.txt: After `mkdir -p` in `step2-implement.sh`, optionally scan `codex-step2-out` for symlinks before launch, or document and enforce that only the dispatcher creates that tree and session tmpdirs are user-private with restrictive permissions.

### FINDING_11: `run_evaluate_failure` grew into deep single-function control flow
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `run_evaluate_failure` grew into a deep single-function control-flow block. Harder to verify defer vs dispatch invariants and risks copy-paste drift on the next CI fix change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_12: `code_fix_attempted_on_ready_log` duplicated across many return sites
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `code_fix_attempted_on_ready_log` duplicated across many `FixResult` return sites. Easy to set the flag on one new return path and miss another, breaking Bash/Python parity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_13: No-blind-rerun test does not assert fix machinery ran
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Deterministic no-blind-rerun test does not assert fix machinery ran before stall. Acceptance requires code fix before retry; test only proves no `ci-rerun-failed.sh` and exit 4.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_14: Step 8 harness greps token presence not autonomous When-clause pairing
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Step 8 harness only greps `ci-fix-exhausted` presence, not autonomous When clause pairing. SKILL prose could mention token outside the autonomous When sentence; harness still passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_15: Bash per-job-before-vendor vs Python vendor-before-per-job ordering
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Bash runs per-job local fixes before vendor; Python runs vendor waterfall before per-job inside `run_ci_fix`. Makes `bool(classified.fixable)` a poor parity stand-in for substantive attempts. Autonomous routing can diverge for the same CI failure shape across `LARCH_SHIP_PR_IMPL` modes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_16: Optional redundant `gh` call when transient retries at cap
- **Reviewer(s)**: dyn-bash-python-parity-output.txt
- **Severity**: nit
- **Concern**: When `transient_retries` is already at the cap, Bash skips the upfront `gh-run-logs.sh` call entirely; Python always calls `collect_failed_logs` before the gated rerun block. Does not change retry-vs-fix decisions—the rerun branch is skipped in both trees—but Python makes a redundant `gh` call.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-python-parity-output.txt: Wrap the Python upfront collect inside the same `transient_retries < max` guard to avoid a redundant `gh` call.

### OOS_1: [OUT_OF_SCOPE] Branch bundles unrelated PRs with #3334
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Branch bundles unrelated PRs (#3314, #3297, #3338, larch-logs) with #3334. Harder review and wider CI failure attribution if harnesses break.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] Pre-existing per-job-before-vendor vs vendor-before-per-job ordering
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-bash-python-parity-output.txt
- **Severity**: latent
- **Concern**: Bash runs `run_per_job_local_fix_loop` before `run_ci_fix_vendor`; Python runs the vendor waterfall before the per-job loop inside `run_ci_fix`. Not introduced solely by #3334 diff but amplifies how the substantive flag must be defined. Track as migration parity work outside this bug fix unless scope explicitly includes reordering.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From dyn-bash-python-parity-output.txt: **Pre-existing ordering:** Bash runs `run_per_job_local_fix_loop` before `run_ci_fix_vendor`; Python runs the vendor waterfall before the per-job loop inside `run_ci_fix`. This branch does not introduce that difference, but it amplifies how the substantive flag must be defined.

### OOS_3: [OUT_OF_SCOPE] Verified exhaustion-surface parity for wired path
- **Reviewer(s)**: dyn-bash-python-parity-output.txt
- **Severity**: latent
- **Concern**: Verified parity for the wired path—Bash `state_set_many BAIL_REASON ci-fix-exhausted BAIL_NEEDS_USER_INPUT false` + `exit 3` matches Python `fix-exhausted` → `monitor` → `Outcome.NEEDS_USER_INPUT` with `detail=ci-fix-exhausted`. Python is not yet wired into live `ship-pr.sh`; cutover must map that outcome to the same bail tokens as Bash.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-python-parity-output.txt: **Exhaustion surface (scout item 4):** Verified parity for the wired path—Bash `state_set_many BAIL_REASON ci-fix-exhausted BAIL_NEEDS_USER_INPUT false` + `exit 3` (`scripts/ship-pr.sh:2705-2707`, `is_autonomous_exit3_bail_reason` at `1728-1731`) matches Python `fix-exhausted` → `monitor` → `Outcome.NEEDS_USER_INPUT` with `detail=ci-fix-exhausted` (`python/ci_monitor.py:1093-1094`, `1221-1228`). Python is not yet wired into live `ship-pr.sh`; cutover must map that outcome to the same bail tokens as Bash.

### OOS_4: [OUT_OF_SCOPE] Jobs deferral broader in Python but aligned for errors
- **Reviewer(s)**: dyn-bash-python-parity-output.txt
- **Severity**: latent
- **Concern**: Python `jobs_state != "ready"` is broader than Bash's explicit `ci_failed_rc == 3` branch but aligns for `rc=1` errors (both defer without vendor dispatch). No regression identified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-python-parity-output.txt: **Jobs deferral (scout item 2):** Python `jobs_state != "ready"` (`1055-1058`) is broader than Bash's explicit `ci_failed_rc == 3` branch (`2601-2602`) but aligns for `rc=1` errors (both defer without vendor dispatch). No regression identified.

### OOS_5: [OUT_OF_SCOPE] Rerun-fail stash parity confirmed
- **Reviewer(s)**: dyn-bash-python-parity-output.txt
- **Severity**: latent
- **Concern**: Neither tree stashes upfront logs after a failed transient rerun; fix-loop iteration 1 re-fetches. Parity OK.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-python-parity-output.txt: **Rerun-fail stash (scout item 3):** Confirmed—neither tree stashes upfront logs after a failed transient rerun; fix-loop iteration 1 re-fetches. Parity OK.

### OOS_6: [OUT_OF_SCOPE] Flag never reset inside loop — satisfied in both trees
- **Reviewer(s)**: dyn-flag-predicate-correctness-output.txt
- **Severity**: latent
- **Concern**: Bash initializes `_code_fix_attempted_on_ready_log=false` once with no reassignment to `false` in the loop; Python initializes `code_fix_attempted_on_ready_log = False` and only ORs in. Satisfied in both trees.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-flag-predicate-correctness-output.txt: **FINDING_5 (flag never reset inside the loop):** Satisfied in both trees — Bash initializes `_code_fix_attempted_on_ready_log=false` once at `2533` with no reassignment to `false` in the loop; Python initializes `code_fix_attempted_on_ready_log = False` at `1034` and only ORs in via `1072-1073`.

### OOS_7: [OUT_OF_SCOPE] Vendor `vendor_rc==4` / verification-retry paths meet jobs-readiness predicate
- **Reviewer(s)**: dyn-flag-predicate-correctness-output.txt
- **Severity**: latent
- **Concern**: Bash sets the flag only under `ci_failed_rc == 0`; Python only calls `run_ci_fix` after `logs.state == "ready"` and `jobs_state == "ready"`, so those paths meet the jobs-readiness half of the predicate when reached.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-flag-predicate-correctness-output.txt: **Vendor `vendor_rc==4` / verification-retry paths:** Bash sets the flag only under `ci_failed_rc == 0` (`2650-2683`); Python only calls `run_ci_fix` after `logs.state == "ready"` and `jobs_state == "ready"` (`1045-1071`), so those paths meet the jobs-readiness half of the predicate when reached.

### OOS_8: [OUT_OF_SCOPE] Codex sandbox review — no additional #3334 surface; ancillary checks OK
- **Reviewer(s)**: dyn-codex-sandbox-symlink-output.txt
- **Severity**: latent
- **Concern**: Invalid `IMPLEMENT_TMPDIR` behavior is correct; `TRANSCRIPT_PARENT` vs `SESSION_TMPDIR` check is warranted; TOCTOU on `pwd -P` is low practical exploitability; `_codex_canonical_existing_dir` leak on exit 2 is harmless; no additional sandbox surface in #3334 CI retry/fix-loop work relative to Codex `--add-dir` review focus.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-codex-sandbox-symlink-output.txt: **(b) Invalid `IMPLEMENT_TMPDIR`:** When set but not a directory or when it is a symlink, `_codex_canonical_existing_dir` returns 1 and the block at `153-157` exits 2 with the intended error path — behavior is correct.
  - From dyn-codex-sandbox-symlink-output.txt: **(c) `TRANSCRIPT_PARENT` vs `SESSION_TMPDIR`:** The new check at `149-151` is warranted: without it, manifest/qa could share one canonical `--add-dir` while `--output-last-message` targets a different parent, splitting write targets and weakening the narrowed-grant invariant.
  - From dyn-codex-sandbox-symlink-output.txt: **(d) TOCTOU between `-L` and `pwd -P`:** Theoretically a racing symlink swap on a world-writable parent could invalidate the check; typical larch session tmpdirs live under user-owned cache paths, so practical exploitability is low and not introduced as a new class beyond existing `pwd -P` canonicalization patterns.
  - From dyn-codex-sandbox-symlink-output.txt: **(e) `unset -f _codex_canonical_existing_dir`:** All validation failures `exit 2` before the helper is needed again; leaking the function on those paths is harmless because the process terminates.
  - From dyn-codex-sandbox-symlink-output.txt: **#3334 `ship-pr` / `ci_monitor` changes:** No additional sandbox or path-grant surface identified in the CI retry/fix-loop work relative to this Codex `--add-dir` review focus.

### OOS_9: [OUT_OF_SCOPE] Existing Bash/Python test stubs align with current semantics for covered paths
- **Reviewer(s)**: dyn-test-exhaustion-discrimination-output.txt
- **Severity**: latent
- **Concern**: `ci_fix_exhausted`, `test_evaluate_failure_push_failed_routes_fix_exhausted`, and `ci_fix_launcher_only_exhausted` (`FAILED_JOBS_COUNT=0`) stubs and assertions align with current Bash/Python semantics for their covered scenarios; they do not exercise the fixable-jobs launcher-only gap flagged in-scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-test-exhaustion-discrimination-output.txt: **`ci_fix_exhausted` (`scripts/test-ship-pr.sh:3418-3486`)** — Stubs line up with the intended path: ready `gh-run-logs` (exit 0), `ci-failed-jobs` with `FAILED_JOBS_COUNT=1` and fixable TSV, `lint-fix-loop.sh` → `LINT_FIX_STATUS=exhausted` (per-job returns non-zero → vendor), all launchers fail without `vendor_rc=4`; `_code_fix_attempted_on_ready_log` is set at `ship-pr.sh:2608` before vendor exhaustion, so exit 3 / `ci-fix-exhausted` is consistent with current Bash semantics (though the flag is set on block entry, not only after lint machinery succeeds).
  - From dyn-test-exhaustion-discrimination-output.txt: **`test_evaluate_failure_push_failed_routes_fix_exhausted` (`python/test_ci_monitor.py:844-899`)** — With a winning tier, `code_fix_attempted` becomes true at `ci_monitor.py:936`; push failure returns `code_fix_attempted_on_ready_log=True` at `975-979`, so `fix-exhausted` is expected and the sequential `git` responses are coherent.
  - From dyn-test-exhaustion-discrimination-output.txt: **`ci_fix_launcher_only_exhausted` (`scripts/test-ship-pr.sh:4188-4230`)** — `FAILED_JOBS_COUNT=0` skips the per-job block, so the substantive flag is never set and exit 4 is asserted correctly for launcher-only exhaustion in that scenario.
