### FINDING_1: Duplicated CI-fix staging/commit logic in ship-pr.sh
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Duplicated `git add`/stage/commit logic in `_run_post_rebase_verify_gates` vs `_stage_and_push_ci_fixes`. Staging rule changes can fix one path and miss the other, violating the plan no-dup mandate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_11: Missing regression for post-rebase verify failure → vendor rotation
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Important interaction (post-rebase verify failure and vendor rotation) is not exercised by the harness. Add a fixture: post-rebase verify fails, then passes only after a rotated vendor.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_13: Missing integration tests for post-rebase verify rc=2/4 routing
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: No test that `_verify_failed_jobs_locally` failure after rebase routes through `run_evaluate_failure` / `_stage_and_push_ci_fixes` as specified (stall vs retry). Stub verify to return 2 and 4 after `did_rebase`; assert `exit_stall` vs exit 4 retry. Plan failure-mode coverage for rc=2 → stall is missing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_14: Missing regression for HEAD refresh after deferred rebase (#3134)
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Rebump-only HEAD advance after vendor fix could false-trigger `first-fixer-non-health`. No harness ensures deferred rebase + snapshot refresh prevents exit-3 mis-routing. Add fix-loop case with rebase stub advancing HEAD; assert no first-fixer bail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_15: Fetch fail-open path untested in ci-behind-count harness
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Network blip → `BEHIND_COUNT=0` → plain push while still behind main is untested. Add stubbed `git fetch` failure test expecting `BEHIND_COUNT=0` plus diagnostic.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_17: pending_retry may re-rebase after failed post-rebase verify
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `pending_retry` re-runs the behind check and may re-rebase after failed verify if main moved during backoff—second defer rebase on an already-rebased branch increases conflict/rebump risk. Skip rebase on `pending_retry` when HEAD already matches the post-deferred snapshot; rebase only if behind and the tree is not current.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_19: CI_FIX_REBASE_PENDING set on git-force-push failure, not only verify failure
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `CI_FIX_REBASE_PENDING` is set on `git-force-push.sh` failure, not only on `_run_post_rebase_verify_gates` failure. Transient push failure after successful verify forces pending-retry verify semantics and contradicts acceptance. Limit `CI_FIX_REBASE_PENDING` to post-rebase verify failures; handle push retry separately.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_2: defer-push rebase does not increment REBASE_COUNT
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The `defer_push=true` path increments `ITERATION` only; `REBASE_COUNT` is not incremented per plan. Post-fix / CI-fix deferred rebases do not count toward `_max_rebases=20` while `ci-wait` `ACTION=rebase` paths do, so the rebase storm cap can under-count many CI-fix rebases and diverge from actual rebase volume.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_20: Harness stubs do not exercise kv_value on noisy BEHIND_COUNT output
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: #3210 harness stubs do not exercise `kv_value` parsing on noisy `BEHIND_COUNT` contract output; a `kv_value` regression would not fail CI. Add a stub emitting extra contract lines before `BEHIND_COUNT=`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_3: Post-rebase verify TSV requirement vs pre-rebase policy
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Post-rebase verify requires a failed-jobs TSV while pre-rebase `_verify_failed_jobs_locally` treats missing TSV as success. With `gh_logs_rc` failure, a vendor fix, and `behind>0`, the flow can stall after rebase despite a valid fix, or defer-rebase with empty TSV when behind. Persist TSV before the vendor path, align post-rebase policy with pre-rebase (or use the same relevant-checks-only fallback), skip rebase when jobs are unknown, and add harness coverage for behind + empty TSV.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_4: Missing no-double-rebase regression test
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: No regression asserts that after the post-fix path leaves the branch current, a subsequent `ci-wait` poll does not invoke a second rebase (`run_rebase_rebump` / rebase-push). Plan acceptance is uncovered. Add a fix-loop / two-poll fixture: post-fix rebase then poll with `BEHIND_COUNT=0`; assert rebase-push call count does not increase again.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_5: hooks.json changes bundled with #3210 ship-pr work
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: The branch bundles anti-polling hook / related changes with #3210 `ship-pr` work. That raises review burden and conflict risk next to ship-pr modularization. Split the PR or clearly separate changelog/review sections.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_6: CI_FIX_REBASE_PENDING not persisted across resume/subprocess
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `CI_FIX_REBASE_PENDING` is process-global (in-memory), not written to ship-pr state. Resume or a new `ship-pr` process may plain-push after an unpushed deferred rebase, or lose coordination with deferred-rebase semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_8: test-ship-pr-3210-spot not on any harness shard
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `test-ship-pr-3210-spot` runs the full fix-loop subset but is not on any `test-harnesses-N` shard; `test-harness-shards-coverage` flags unsharded `test-*` recipes and `make lint` can fail on merge. Add to shard 14 (e.g. with `test-ship-pr-fix-loop`), remove the wrapper, or add a documented `CARVE_OUT` rationale.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_9: CI_FIX_REBASE_PENDING short-circuit blocks vendor rotation after post-rebase verify failure
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `CI_FIX_REBASE_PENDING` short-circuit blocks vendor re-dispatch after post-rebase verify failure: vendor fix passes pre-rebase verify; rebase breaks tests; post-rebase verify returns 1/4 and sets `PENDING`; the outer loop retries `_stage_and_push` only until max-retries without rotated fixer. Clear `PENDING` or skip the short-circuit on verify failure; route to `run_ci_fix_vendor` with `start_attempt` rotation; reserve `PENDING` for push-fail after successful verify.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


