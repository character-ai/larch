### FINDING_1: Branch bundles unrelated #3217 / hook changes with #3210 ship-pr work
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The branch mixes #3210 ship-pr / ci-behind-count work with unrelated changes (#3217 hook anti-read-poll, AGENTS anti-polling, #3175 polling-hook surface). Reviewers cannot bisect failures; unrelated hook or matcher regressions can block or mask #3210 merge and release. Split unrelated work into its own PR/commit stack or clearly label non-#3210 commits; keep the #3210 diff focused on ship-pr, ci-behind-count, tests, and docs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Split #3217 into its own PR or commit stack; keep #3210 diff limited to ship-pr / ci-behind-count / tests / docs.
  - From cursor-specialist-testing-output.txt: Split commits or mandate explicit multi-harness CI checklist in PR test plan.
  - From cursor-specialist-plan-fidelity-output.txt: Split or clearly label non-#3210 commits in the PR.


### FINDING_10: Missing no-double-rebase regression across ci-wait polls
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: No multi-iteration harness asserts that after a successful post-fix rebase, a second poll with `BEHIND_COUNT=0` does not call `run_rebase_rebump` again. Regression could cause double rebase on `ACTION=rebase`, extra CI, and force-push churn.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add two-poll harness: after successful post-fix rebase BEHIND_COUNT=0 on second poll must not call rebase-push again.
  - From cursor-specialist-plan-fidelity-output.txt: Add fix-loop test: iteration 0 post-fix rebase+push succeeds; iteration 1 stubs BEHIND_COUNT=0 and asserts zero additional rebase-push calls.


### FINDING_11: Missing post-rebase HEAD refresh regression (false first-fixer-non-health)
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: No #3210 regression test ensures HEAD snapshot refresh after deferred rebase. Vendor noop with rebase-only HEAD advance could still classify as first-fixer-non-health and bail if snapshot refresh regresses.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add fixture combining BEHIND_COUNT=1 deferred rebase and unchanged vendor baseline vs moved HEAD expecting success not exit 3.
  - From cursor-specialist-plan-fidelity-output.txt: Add harness: vendor no-op commit + deferred rebase advances HEAD; assert success without BAIL_REASON=first-fixer-non-health.


### FINDING_14: CI_FIX_REBASE_PENDING retry with empty failed_jobs_tsv skips job re-verify before force-push
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: When `CI_FIX_REBASE_PENDING` is set but `failed_jobs_tsv` is empty (e.g., resume or `gh-run-logs` failure after job verify failed), the retry can run lint-only then `git-force-push.sh` without `_verify_failed_jobs_locally`, allowing force-push without passed failed-job verification.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Pass persisted ci_failed_tsv on all pending retries; block force-push until job verify passes.
  - From cursor-specialist-edge-cases-output.txt: Persist and pass last ci_failed_tsv on all CI_FIX_REBASE_PENDING retries.


### FINDING_15: Deferred rebase push failure does not persist force-push need
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: After defer-push rebase, if verify succeeds but `git-force-push.sh` fails, return 1 leaves `CI_FIX_REBASE_PENDING` false. The next evaluate/stage sees `behind=0` and may call `git-push.sh`, causing non-fast-forward loop or stall without auto-recovery.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Set CI_FIX_REBASE_PENDING (persisted) when push fails after did_rebase=true; retry path must keep using git-force-push.sh.


### FINDING_16: Post-rebase verify exit 3 leaves rebased unpushed tree without clear recovery
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: After unpushed deferred rebase, `_verify_failed_jobs_locally` can exit 3 on ci-local-unfixable without setting `CI_FIX_REBASE_PENDING`, leaving a rebased unpushed tree with unclear recovery versus acceptance to never push unverified fixes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Handle exit 3 explicitly after deferred rebase (documented stall) or avoid bare exit from post-rebase gate without state that blocks plain push on resume.


### FINDING_3: FORKED_TARGET paths do not consistently thread upstream base remote/ref
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Fork workflows mix `upstream/main` and `origin/main`: rebase-nonbump recovery can verify against the wrong base; deferred rebase/rebase-push uses `upstream/main` while `git-sync-local-main.sh` still syncs `origin/main`, skewing classify-bump merge-base and version/changelog when upstream is ahead of origin; behind-count on the fork path may not use the same base args as rebase-push, allowing rebase and behind-check to diverge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Pass upstream/main (from FORKED_TARGET) into _run_rebase_rebump_verify_plain_no_push.
  - From cursor-specialist-correctness-output.txt: Thread base_remote/base_ref into sync-before-classify or add upstream-aware sync; extend fork harness beyond rebase-push argv asserts.
  - From cursor-specialist-testing-output.txt: Assert ci-behind-count stub receives --base-remote upstream on forked FORKED_TARGET=true path.
  - From cursor-specialist-edge-cases-output.txt: Thread base_remote/base_ref into git-sync-local-main.sh (or fork-specific sync) matching rebase-push.sh.


### FINDING_4: run_rebase_rebump positional parser treats unknown tokens as base
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: The positional argument parser for `run_rebase_rebump` treats unknown tokens as `base_remote`/`base_ref`. A caller typo can silently rebase onto the wrong remote without validation before rebase-push.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Use explicit flags or validate base_remote/base_ref before rebase-push.


### FINDING_8: CI_FIX_REBASE_PENDING can stall when set on the last fix iteration
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: When `CI_FIX_REBASE_PENDING` is set on the last `_fix_attempt` (e.g., vendor succeeds and deferred rebase on attempt 2, post-rebase verify fails, `_fix_attempt` becomes 3), the loop exits before the pending retry at line 2465, leaving a rebased unpushed branch. The `per_job` path `break` on the final attempt can skip the same pending retry when `per_job_rc=0` and stage sets pending on the last iteration.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Run push-only _stage_and_push_ci_fixes in the same iteration when pending is set; or exempt pending retries from _fix_attempt; or add a dedicated pending-retry budget.
  - From cursor-specialist-correctness-output.txt: Remove break or fall through to 2465 before leaving the loop.


