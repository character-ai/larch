# Review Round 1

- Mode: `diff`
- 4 accepted, 3 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Delegate verify timeout budget per fixable job
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Delegate timeout budgets one verify subprocess per cycle but `_run_cycle` verifies each fixable job separately. Two fixable jobs each near `SUBPROCESS_DEFAULT_TIMEOUT_SEC` can cause the parent to kill the delegate during the second verify and return `pushed` from checkpoint instead of `ci-fix-exhausted`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Budget verify time per fixable job count or enforce a shared per-cycle verify deadline inside the delegate.


### FINDING_2: Missing test for untrusted passive-wait fail-closed branch
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The new untrusted passive-wait fail-closed branch in `python/ci_agentic_fix.py:413-423` lacks direct `_run_cycle` regression coverage. If the `FAILED_RUN_ID` guard regresses, `_run_cycle` could resume with a stale `run_id` when `_wait_for_ci` returns an unexpected `ACTION` without `FAILED_RUN_ID`. Only `wait_err` and `ACTION=bail` paths are tested today.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add stubbed `_run_cycle` test expecting `ci-fix-exhausted` and `next_run_id=None`.
  - From cursor-specialist-testing-output.txt: Add a monkeypatched `_run_cycle` test where `_wait_for_ci` returns e.g. `({ACTION: evaluate_failure, CI_STATUS: fail}, None)` and assert status `ci-fix-exhausted`, detail `ci-wait-untrusted-output`, and `next_run` is `None`.
  - From codex-specialist-testing-output.txt: Add a stubbed `_run_cycle` test with `ACTION=retry` and no `FAILED_RUN_ID`, asserting `ci-fix-exhausted` and `next_run` is `None`.


### FINDING_6: Forbidden-path stall leaves unrelated fixer edits dirty
- **Reviewer(s)**: codex-specialist-correctness-output.txt, dyn-conflict-guard-output.txt
- **Severity**: important
- **Concern**: On forbidden-path conflict stall in `python/rebase.py:270-276`, the branch resets conflict markers and raises `Stalled`, but does not roll back allowed-path deltas the fixer introduced. A fixer that touches a forbidden path and also edits allowed non-conflict files can leave partial allowed-path changes in the worktree (and potentially staged state), producing an inconsistent mid-rebase state for operator recovery or later resume. The failed-tier retry path at `python/rebase.py:295-296` and the guard rollback in `python/ci_agentic_fix.py:311-319` perform fuller baseline rollback.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Call `git.paths_delta_revert` with the pre-tier baseline before raising, then reset conflict paths.
  - From dyn-conflict-guard-output.txt: Before raising `Stalled`, call `git.paths_delta_revert` with the tier-loop baselines (and mirror the `ci_agentic_fix` staged/index rollback if needed), then reset conflict paths.


### FINDING_7: Forbidden-path guard can leave staged forbidden edits in index
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The new conflict-fixer forbidden-path guard can stall while leaving staged forbidden edits behind. If a fixer stages `.gitmodules` or `.claude-plugin/plugin.json`, `revert_forbidden_paths` returns positive and `_resolve_conflicts` raises `Stalled`, but the index-only protected edit can remain in the paused rebase and be committed later.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Clear both index and worktree for forbidden tracked paths, then add a staged-only forbidden-path regression test.


