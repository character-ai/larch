### FINDING_1: Misleading Option A backstop log on fail-closed follow-up
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: After round-mode follow-up, `review-and-fix.sh` logs that residue may be healed by ship-pr Option A, then returns `CODER_STATUS=failed` with exit 2 when tracked porcelain remains. Step 5 typically halts before ship-pr runs, so operators reading `coder-commit.log` may expect an automatic rebase-time fixup that will not occur in the same run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Reword or remove the Option A backstop reference when returning CODER_STATUS=failed
  - From cursor-specialist-testing-output.txt: Reword warning to match fail-closed behavior or mention Option A only when continuing applied
  - From cursor-specialist-edge-cases-output.txt: Reword the larch_err to say the round failed and manual cleanup or a later ship-pr run is required


### FINDING_12: Follow-up uses `git add -u` vs primary `git add -A`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Round-mode follow-up stages with `git add -u` while the primary round commit uses `git add -A`. Hook residue that is only new unstaged tracked files (not picked up by `-u`) can fail the second porcelain check with exit 2 and never reach ship-pr in the same run. Plan text specified `git add -A` for the follow-up block.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Use git add -A for the follow-up (after submodule revert) or document and test that hook residue must be modifications to existing tracked files.
  - From cursor-specialist-plan-fidelity-output.txt: Use git add -A per plan or document intentional git add -u in the plan.


### FINDING_2: Exit code 2 contract omits post-follow-up residue failure
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `review-and-fix.md` documents exit 2 causes but does not describe round-mode failure when tracked residue persists after the one-shot follow-up commit, so operators cannot distinguish that path from other exit-2 cases from the contract alone.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add exit 2 bullet for post-commit tracked residue / follow-up failure


### FINDING_6: Option B fail-closed on persistent residue vs plan warn-and-continue
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: When a non-idempotent pre-commit hook leaves tracked changes after the one-shot follow-up, Option B returns exit 2 and blocks Step 5 instead of warn-and-continuing so ship-pr Option A can fix up at rebase. That diverges from the plan’s warn-and-continue + Option A backstop failure mode and prevents Option A from running in the same `/implement` run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Restore warn-and-continue for that case or document and test fail-closed as intentional operator-blocking behavior
  - From cursor-specialist-plan-fidelity-output.txt: Restore warn-and-continue per plan, or formally amend the plan/acceptance to require fail-closed exit 2 and drop the warn-and-continue failure-mode text


### FINDING_7: Option A does not re-check tracked porcelain after fixup commit
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-git-semantics-output.txt
- **Severity**: important
- **Concern**: `run_rebase_rebump` step 0b commits tracked leftovers once via `git-commit.sh` but does not re-run `git status --porcelain --untracked-files=no` before `drop-bump-commit.sh`. A pre-commit hook that re-modifies tracked files during the fixup commit can leave the tree dirty again; Guard 1 still returns `DROPPED=false` and ship-pr stalls at step 10/12 despite step 0b having run (same residue class Option B handles in round-mode follow-up).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: After the fixup block, re-run git status --porcelain --untracked-files=no; if still dirty, stall with an explicit reason or allow one guarded second git add -u + git-commit.sh before invoking drop-bump-commit.sh.
  - From dyn-git-semantics-output.txt: After a successful fixup commit, re-check tracked porcelain once and, if still non-empty, attempt one guarded follow-up `git add -u` + `git-commit.sh` (or repeat the 0b block once), mirroring the round-mode residue re-check in `review-and-fix.sh`.


### FINDING_8: Option A fixup block not errexit-safe under mid-run `set -e`
- **Reviewer(s)**: dyn-shell-set-e-safety-output.txt
- **Severity**: important
- **Concern**: The new pre-rebase fixup uses bare `git add -u` and `git-commit.sh` followed by `rc=$?`, but `ship-pr.sh` enables `set -e` after `run_pr_prep_phase` (line ~1503) and does not disable it before `run_rebase_rebump`. A non-zero git command can abort the script before `rc=$?`, `record_failure`, and the intended best-effort fall-through to `drop-bump-commit.sh`. Offline tests do not catch this because each `ship-pr.sh` invocation starts without mid-run errexit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-set-e-safety-output.txt: Use the same errexit-safe capture pattern as `git add -A` at line 1106 (`rc=0; git add -u >"$fail_file" 2>&1 || rc=$?` and the same for `git-commit.sh`), or wrap only this block with `set +e` / restore errexit around both git calls.


### FINDING_9: Weak assertions on fixup-commit-failure stall path
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-test-edge-coverage-output.txt
- **Severity**: important
- **Concern**: `rebump_fixup_commit_fail_stalls` (and related coverage) only checks `ship-pr.sh` exit 4, which is shared by every `exit_stall` in `ci-initial`. The fixture does not pin `STALL_STEP=10`, stall tracking, or fail-log text distinguishing fixup failure → dirty tree → Guard 1 from other stall causes, so regressions could still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Assert STALL_STEP=10 no fixup commit and optional Warning in fail capture logs
  - From dyn-test-edge-coverage-output.txt: After the run, add `assert_state_line` for `STALL_STEP=10` and `EXIT_CODE=4`, and grep `$tmp/stdout-rebump-fixup-fail` or a captured fail file for `uncommitted tracked changes` / `drop-bump-commit.sh DROPPED=false` so the case uniquely pins fixup failure → dirty tree → Guard 1 stall, not an unrelated stall.


