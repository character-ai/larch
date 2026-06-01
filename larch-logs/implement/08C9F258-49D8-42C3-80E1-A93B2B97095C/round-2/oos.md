### OOS_1: [OUT_OF_SCOPE] Branch bundles unrelated PRs with #3334
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Branch bundles unrelated PRs (#3314, #3297, #3338, larch-logs) with #3334. Harder review and wider CI failure attribution if harnesses break.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### OOS_2: [OUT_OF_SCOPE] Pre-existing per-job-before-vendor vs vendor-before-per-job ordering
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-bash-python-parity-output.txt
- **Severity**: latent
- **Concern**: Bash runs `run_per_job_local_fix_loop` before `run_ci_fix_vendor`; Python runs the vendor waterfall before the per-job loop inside `run_ci_fix`. Not introduced solely by #3334 diff but amplifies how the substantive flag must be defined. Track as migration parity work outside this bug fix unless scope explicitly includes reordering.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From dyn-bash-python-parity-output.txt: **Pre-existing ordering:** Bash runs `run_per_job_local_fix_loop` before `run_ci_fix_vendor`; Python runs the vendor waterfall before the per-job loop inside `run_ci_fix`. This branch does not introduce that difference, but it amplifies how the substantive flag must be defined.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_3: [OUT_OF_SCOPE] Verified exhaustion-surface parity for wired path
- **Reviewer(s)**: dyn-bash-python-parity-output.txt
- **Severity**: latent
- **Concern**: Verified parity for the wired path—Bash `state_set_many BAIL_REASON ci-fix-exhausted BAIL_NEEDS_USER_INPUT false` + `exit 3` matches Python `fix-exhausted` → `monitor` → `Outcome.NEEDS_USER_INPUT` with `detail=ci-fix-exhausted`. Python is not yet wired into live `ship-pr.sh`; cutover must map that outcome to the same bail tokens as Bash.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-python-parity-output.txt: **Exhaustion surface (scout item 4):** Verified parity for the wired path—Bash `state_set_many BAIL_REASON ci-fix-exhausted BAIL_NEEDS_USER_INPUT false` + `exit 3` (`scripts/ship-pr.sh:2705-2707`, `is_autonomous_exit3_bail_reason` at `1728-1731`) matches Python `fix-exhausted` → `monitor` → `Outcome.NEEDS_USER_INPUT` with `detail=ci-fix-exhausted` (`python/ci_monitor.py:1093-1094`, `1221-1228`). Python is not yet wired into live `ship-pr.sh`; cutover must map that outcome to the same bail tokens as Bash.


Vote tally: YES=2 NO=1 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_4: [OUT_OF_SCOPE] Jobs deferral broader in Python but aligned for errors
- **Reviewer(s)**: dyn-bash-python-parity-output.txt
- **Severity**: latent
- **Concern**: Python `jobs_state != "ready"` is broader than Bash's explicit `ci_failed_rc == 3` branch but aligns for `rc=1` errors (both defer without vendor dispatch). No regression identified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-python-parity-output.txt: **Jobs deferral (scout item 2):** Python `jobs_state != "ready"` (`1055-1058`) is broader than Bash's explicit `ci_failed_rc == 3` branch (`2601-2602`) but aligns for `rc=1` errors (both defer without vendor dispatch). No regression identified.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### OOS_5: [OUT_OF_SCOPE] Rerun-fail stash parity confirmed
- **Reviewer(s)**: dyn-bash-python-parity-output.txt
- **Severity**: latent
- **Concern**: Neither tree stashes upfront logs after a failed transient rerun; fix-loop iteration 1 re-fetches. Parity OK.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-python-parity-output.txt: **Rerun-fail stash (scout item 3):** Confirmed—neither tree stashes upfront logs after a failed transient rerun; fix-loop iteration 1 re-fetches. Parity OK.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_6: [OUT_OF_SCOPE] Flag never reset inside loop — satisfied in both trees
- **Reviewer(s)**: dyn-flag-predicate-correctness-output.txt
- **Severity**: latent
- **Concern**: Bash initializes `_code_fix_attempted_on_ready_log=false` once with no reassignment to `false` in the loop; Python initializes `code_fix_attempted_on_ready_log = False` and only ORs in. Satisfied in both trees.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-flag-predicate-correctness-output.txt: **FINDING_5 (flag never reset inside the loop):** Satisfied in both trees — Bash initializes `_code_fix_attempted_on_ready_log=false` once at `2533` with no reassignment to `false` in the loop; Python initializes `code_fix_attempted_on_ready_log = False` at `1034` and only ORs in via `1072-1073`.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_7: [OUT_OF_SCOPE] Vendor `vendor_rc==4` / verification-retry paths meet jobs-readiness predicate
- **Reviewer(s)**: dyn-flag-predicate-correctness-output.txt
- **Severity**: latent
- **Concern**: Bash sets the flag only under `ci_failed_rc == 0`; Python only calls `run_ci_fix` after `logs.state == "ready"` and `jobs_state == "ready"`, so those paths meet the jobs-readiness half of the predicate when reached.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-flag-predicate-correctness-output.txt: **Vendor `vendor_rc==4` / verification-retry paths:** Bash sets the flag only under `ci_failed_rc == 0` (`2650-2683`); Python only calls `run_ci_fix` after `logs.state == "ready"` and `jobs_state == "ready"` (`1045-1071`), so those paths meet the jobs-readiness half of the predicate when reached.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

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


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_9: [OUT_OF_SCOPE] Existing Bash/Python test stubs align with current semantics for covered paths
- **Reviewer(s)**: dyn-test-exhaustion-discrimination-output.txt
- **Severity**: latent
- **Concern**: `ci_fix_exhausted`, `test_evaluate_failure_push_failed_routes_fix_exhausted`, and `ci_fix_launcher_only_exhausted` (`FAILED_JOBS_COUNT=0`) stubs and assertions align with current Bash/Python semantics for their covered scenarios; they do not exercise the fixable-jobs launcher-only gap flagged in-scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-test-exhaustion-discrimination-output.txt: **`ci_fix_exhausted` (`scripts/test-ship-pr.sh:3418-3486`)** — Stubs line up with the intended path: ready `gh-run-logs` (exit 0), `ci-failed-jobs` with `FAILED_JOBS_COUNT=1` and fixable TSV, `lint-fix-loop.sh` → `LINT_FIX_STATUS=exhausted` (per-job returns non-zero → vendor), all launchers fail without `vendor_rc=4`; `_code_fix_attempted_on_ready_log` is set at `ship-pr.sh:2608` before vendor exhaustion, so exit 3 / `ci-fix-exhausted` is consistent with current Bash semantics (though the flag is set on block entry, not only after lint machinery succeeds).
  - From dyn-test-exhaustion-discrimination-output.txt: **`test_evaluate_failure_push_failed_routes_fix_exhausted` (`python/test_ci_monitor.py:844-899`)** — With a winning tier, `code_fix_attempted` becomes true at `ci_monitor.py:936`; push failure returns `code_fix_attempted_on_ready_log=True` at `975-979`, so `fix-exhausted` is expected and the sequential `git` responses are coherent.
  - From dyn-test-exhaustion-discrimination-output.txt: **`ci_fix_launcher_only_exhausted` (`scripts/test-ship-pr.sh:4188-4230`)** — `FAILED_JOBS_COUNT=0` skips the per-job block, so the substantive flag is never set and exit 4 is asserted correctly for launcher-only exhaustion in that scenario.

Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

