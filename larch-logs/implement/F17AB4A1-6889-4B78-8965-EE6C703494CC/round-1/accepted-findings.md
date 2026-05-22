### FINDING_1: Git log/diff probes can fail silently and authorize a destructive reset
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: `git log` / `git diff` pipelines suppress errors (for example via `|| true` / empty reads), leaving “all flush” / “larch-logs-only” flags true by default; with `AHEAD>0`, transient or partial git failures can be misclassified as safe flush-only work and trigger `git reset --hard origin/main`, discarding real local commits that were never validated.
- **Suggested revision**: Stop masking probe failures on the destructive path; capture and check subprocess exit status; when `AHEAD>0` and probes fail or are ambiguous, emit `SYNC_STATUS=probe-error` and exit `2` before any reset (optionally tighten with parity checks such as subject/path line counts versus `AHEAD`).


### FINDING_2: Reset success is not verified; callers can continue in an inconsistent state
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Integration between `scripts/preflight.sh` and `scripts/check-main-sync.sh` can treat a reset as successful when it was not: `git reset --hard` may be silenced / unchecked while `SYNC_STATUS` still reflects success, so a failed reset (hooks, I/O, lock) or other unexpected git exit combined with permissive error handling can leave the repo on an ambiguous local state while the workflow proceeds (for example toward rebase).
- **Suggested revision**: Check `git reset --hard` exit status, surface stderr on failure, and map failure to `probe-error` / a non-success `SYNC_STATUS` (or an explicit blocked path) so preflight and downstream steps do not continue as if `origin/main` was restored.


### FINDING_3: Main-sync can be skipped when the helper is not executable, weakening the lock path
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: `skills/fix-issue/scripts/find-lock-issue.sh` gates running `check-main-sync` on the script being executable; broken packaging, sparse checkouts, or stripped execute bits can skip main-sync entirely while locking still proceeds, silently removing ahead-of-origin protection.
- **Suggested revision**: Fail closed (for example `ELIGIBLE=false` with an explicit error), invoke via `bash` on the script path, and/or enforce executable-bit guarantees in packaging/CI so the lock path cannot bypass sync checks.


### FINDING_5: Automated tests omit the planned probe-failure / exit-2 regression case
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: The implementation plan calls for a probe-failure scenario (`SYNC_STATUS=probe-error`, exit `2`), but `scripts/test-check-main-sync.sh` / related docs do not exercise it, so regressions in probe handling, `rev-list` edge cases, and caller mapping for exit `2` can ship without CI signal.
- **Suggested revision**: Add a controlled fixture (for example git wrapper, invalid `GIT_DIR`, or sterile repo) asserting stdout/`SYNC_STATUS` and exit code `2`, and align `scripts/test-check-main-sync.md` with the harness.


### FINDING_7: Documentation overclaims generic git probe failures vs what the code actually fail-closes
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: `scripts/check-main-sync.md` documents a generic git probe failure contract (exit `2`) that may not match narrower fail-closed behavior in code (called out as `rev-list`-only in the review), misleading maintainers about which probes are safety-critical.
- **Suggested revision**: Align the documented contract with the implemented checks, or extend the code to satisfy the documented contract.


### FINDING_8: Auto-reset combined with `--skip-clean-check` can destroy dirty tracked work before rebase
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: On a dirty tracked tree, using `--skip-clean-check` with flush-only ahead commits can still allow `check-main-sync`’s `git reset --hard`, wiping local tracked edits that preflight previously preserved when rebase would fail, changing lossiness of the workflow.
- **Suggested revision**: Gate destructive reset on a clean working tree (or on `SKIP_CLEAN_CHECK=false`), or refuse reset when `git status --porcelain` is non-empty.


