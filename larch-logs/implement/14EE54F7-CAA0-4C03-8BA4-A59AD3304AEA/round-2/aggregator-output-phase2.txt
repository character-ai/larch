
### FINDING_1: Branch bundles unrelated #3217 / hook changes with #3210 ship-pr work
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The branch mixes #3210 ship-pr / ci-behind-count work with unrelated changes (#3217 hook anti-read-poll, AGENTS anti-polling, #3175 polling-hook surface). Reviewers cannot bisect failures; unrelated hook or matcher regressions can block or mask #3210 merge and release. Split unrelated work into its own PR/commit stack or clearly label non-#3210 commits; keep the #3210 diff focused on ship-pr, ci-behind-count, tests, and docs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Split #3217 into its own PR or commit stack; keep #3210 diff limited to ship-pr / ci-behind-count / tests / docs.
  - From cursor-specialist-testing-output.txt: Split commits or mandate explicit multi-harness CI checklist in PR test plan.
  - From cursor-specialist-plan-fidelity-output.txt: Split or clearly label non-#3210 commits in the PR.

### FINDING_2: ci-status ignores BEHIND_COUNT_RELIABLE
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `ci-status` parses `BEHIND_COUNT` but not `BEHIND_COUNT_RELIABLE`. After fetch/rev-list failure, `ci-behind-count` can emit `BEHIND_COUNT=0` with `RELIABLE=false`; `ci-wait` / `ci-decide` may proceed or skip rebase while `ship-pr` refuses push on the same repo state, causing poll/fix deadlock or inconsistent routing until refs heal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Parse BEHIND_COUNT_RELIABLE in ci-status (pending or fail-closed) or document and test intentional split.
  - From cursor-specialist-security-output.txt: Map BEHIND_COUNT_RELIABLE=false to pending / non-actionable behind state.
  - From cursor-specialist-edge-cases-output.txt: Parse BEHIND_COUNT_RELIABLE in ci-status.sh and align routing with ship-pr (pending/wait vs fail-closed push).

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

### FINDING_5: [OUT_OF_SCOPE] Duplicate BEHIND_COUNT KV parsing (awk vs kv_value)
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `ci-status.sh` and `ship-pr.sh` duplicate parsing of the `BEHIND_COUNT` contract (inline awk vs `kv_value`). Future helper output changes require two edits with drift risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract shared parse helper for both scripts.
  - From cursor-specialist-plan-fidelity-output.txt: Optionally route through kv_value for consistency with ship-pr.sh.

### FINDING_6: Plan fail-open behind-count vs ship-pr fail-closed push on unreliable count
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Documented plan/acceptance implies fail-open push when behind-count is unreliable (do not block push on count error), but `ship-pr` CI-fix staging can hard-block when `BEHIND_COUNT_RELIABLE=false` after a verified local fix (e.g., transient `git fetch` failure emits `BEHIND_COUNT=0` unreliable). Operators may expect push despite count errors; behavior is undocumented in tests and contradicts plan wording unless acceptance is updated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Warn and proceed with behind=0 plain push per acceptance; or update issue acceptance to match documented fail-closed policy.
  - From cursor-specialist-testing-output.txt: Reconcile docs/acceptance with implementation and add ship-pr unreliable-count test.
  - From cursor-specialist-plan-fidelity-output.txt: Restore fail-open push semantics per plan, or amend plan/acceptance to document the reliability gate and add a fetch-failure harness case.

### FINDING_7: Missing harness for BEHIND_COUNT_RELIABLE=false push refusal in CI-fix path
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: No end-to-end or fix-loop test asserts that CI-fix push is blocked when `BEHIND_COUNT_RELIABLE=false`. A regression could reintroduce push on fail-open count or remove the refusal branch without CI failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add fix-loop test with unreliable stub and no push-kind output.
  - From cursor-specialist-correctness-output.txt: Add harness cases for final-attempt pending stall and BEHIND_COUNT_RELIABLE=false.
  - From cursor-specialist-testing-output.txt: Add ci_fix_behind_count_unreliable fix-loop case stubbing unreliable KV and assert no push helpers run.
  - From cursor-specialist-edge-cases-output.txt: Add fix-loop stub asserting push helpers not called when unreliable.

### FINDING_8: CI_FIX_REBASE_PENDING can stall when set on the last fix iteration
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: When `CI_FIX_REBASE_PENDING` is set on the last `_fix_attempt` (e.g., vendor succeeds and deferred rebase on attempt 2, post-rebase verify fails, `_fix_attempt` becomes 3), the loop exits before the pending retry at line 2465, leaving a rebased unpushed branch. The `per_job` path `break` on the final attempt can skip the same pending retry when `per_job_rc=0` and stage sets pending on the last iteration.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Run push-only _stage_and_push_ci_fixes in the same iteration when pending is set; or exempt pending retries from _fix_attempt; or add a dedicated pending-retry budget.
  - From cursor-specialist-correctness-output.txt: Remove break or fall through to 2465 before leaving the loop.

### FINDING_9: Local verify failure does not continue waterfall tiers in the same attempt
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: After one vendor success, a local verify failure (e.g., Cursor exits 0 but jobs still fail) returns 1 without trying later waterfall tiers (codex/claude) until the next `_fix_attempt`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: On pre-stage verify failure continue waterfall or rotate start tier before returning 1.

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

### FINDING_12: Post-rebase verify rc=2 stall not covered end-to-end in ship-pr fix loop
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Post-rebase verify returning rc=2 → `exit_stall` is tested only on an isolated gate helper, not through full `run_evaluate_failure` / `_stage_and_push` wiring. Regression in mapping rc=2 to stall could ship without failing CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add fix-loop integration expecting STALL_STEP head-changed and no push when verify returns 2 after rebase.
  - From cursor-specialist-plan-fidelity-output.txt: Extend to full ship-pr integration stub asserting exit_stall 10-head-changed/12-head-changed tokens.

### FINDING_13: CI-fix push may ignore BEHIND_COUNT_RELIABLE and plain-push on unreliable zero count
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: CI-fix push path may ignore `BEHIND_COUNT_RELIABLE` and treat fail-open `BEHIND_COUNT=0` as authoritative. A network/git/rev-list glitch during `ci-behind-count` fetch could yield unreliable zero and allow plain-push of a fix still behind main without rebase or post-rebase re-verify.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Parse BEHIND_COUNT_RELIABLE; abort push (return 1 / stall) when false; only rebase/push on reliable counts.

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

### FINDING_17: test-ci-behind-count lacks fetch-failure / reliability harness
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: No test covers the default fetch path or fetch failure setting `BEHIND_COUNT_RELIABLE=false`. Fetch regression could break `--no-fetch` delegation assumptions in `ci-status` without harness signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add fetch-failure fixture without --no-fetch expecting BEHIND_COUNT_RELIABLE=false.

### FINDING_18: hook-anti-read-poll poll state follows TMPDIR
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Poll state directory follows `TMPDIR`. A malicious `TMPDIR` in the same user session could redirect poll-state writes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Pin under ~/.cache/larch/ or validate TMPDIR before use.

### FINDING_19: [OUT_OF_SCOPE] Vendor rotation test brittleness (launcher-order line)
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Vendor rotation assertion uses the third line of launcher-order rather than direct tier-0 on `_fix_attempt=1`. The test could pass or fail for retry side effects rather than rotation semantics; pre-existing brittleness not introduced solely by behind-count wiring.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Prefer asserting first launcher on second outer attempt equals codex when _fix_attempt=1.

### FINDING_20: [OUT_OF_SCOPE] CI_FIX_REBASE_PENDING push-only retry may skip job re-verify (pre-existing)
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Pre-existing retry shape: push-only `CI_FIX_REBASE_PENDING` retry with empty `failed_jobs_tsv` when `gh-run-logs` is unavailable may skip failed-job re-verification before force-push after rebase.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Consider threading last-known TSV on pending retry.
