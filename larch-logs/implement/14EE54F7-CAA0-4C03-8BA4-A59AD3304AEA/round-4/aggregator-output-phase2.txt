Normalized aggregator output from the supplied reviewer slots. Merged items share one behavioral risk; distinct fixes or code paths stay separate. `[OUT_OF_SCOPE]` headings are preserved where any source used that tag.

### FINDING_1: Duplicated CI-fix staging/commit logic in ship-pr.sh
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Duplicated `git add`/stage/commit logic in `_run_post_rebase_verify_gates` vs `_stage_and_push_ci_fixes`. Staging rule changes can fix one path and miss the other, violating the plan no-dup mandate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

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

### FINDING_7: Duplicate BEHIND_COUNT parsing (awk vs kv_value)
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `ci-status.sh` uses `awk` for `BEHIND_COUNT` while `ship-pr.sh` uses `kv_value`—two parsers for the same contract stream. Unify on `kv_value` or a shared parse helper.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

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

### FINDING_10: Fail-open BEHIND_COUNT=0 on fetch/rev-list errors in post-fix push path
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `ci-behind-count.sh` / ship-pr behind-check fail-open to `BEHIND_COUNT=0` on fetch or `rev-list` errors. Transient git/network/auth failure or upstream outage makes the branch look current; post-fix CI-fix can plain-push on a stale base without rebasing onto latest main/upstream—the churn #3210 targets. Document fail-open, stall/retry when behind cannot be computed, emit unknown state, or make post-fix behind-check failures blocking; keep fail-open only where explicitly required (e.g. ci-status polling).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_11: Missing regression for post-rebase verify failure → vendor rotation
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Important interaction (post-rebase verify failure and vendor rotation) is not exercised by the harness. Add a fixture: post-rebase verify fails, then passes only after a rotated vendor.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_12: first-fixer-non-health may target wrong tier when Claude unavailable first
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: When Claude is skipped as the first tier, `waterfall_iter` shifts before Codex runs; `first-fixer-non-health` may target the wrong tier. Track the first actually-launched tier for `first-fixer-non-health`.
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

### FINDING_16: ci-behind-count harness never exercises default fetch path
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: All harness cases use `--no-fetch` only; default fetch behavior in `ci-behind-count.sh` is never exercised. Add one fetch-path fixture with a local origin remote.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_17: pending_retry may re-rebase after failed post-rebase verify
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `pending_retry` re-runs the behind check and may re-rebase after failed verify if main moved during backoff—second defer rebase on an already-rebased branch increases conflict/rebump risk. Skip rebase on `pending_retry` when HEAD already matches the post-deferred snapshot; rebase only if behind and the tree is not current.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_18: did_rebase set before run_rebase_rebump completes
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `did_rebase` is set before `run_rebase_rebump` completes; a future non-fatal rebase return could force-push without a completed rebase. Set `did_rebase` after successful rebase helper return.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_19: CI_FIX_REBASE_PENDING set on git-force-push failure, not only verify failure
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `CI_FIX_REBASE_PENDING` is set on `git-force-push.sh` failure, not only on `_run_post_rebase_verify_gates` failure. Transient push failure after successful verify forces pending-retry verify semantics and contradicts acceptance. Limit `CI_FIX_REBASE_PENDING` to post-rebase verify failures; handle push retry separately.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_20: Harness stubs do not exercise kv_value on noisy BEHIND_COUNT output
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: #3210 harness stubs do not exercise `kv_value` parsing on noisy `BEHIND_COUNT` contract output; a `kv_value` regression would not fail CI. Add a stub emitting extra contract lines before `BEHIND_COUNT=`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### OOS_1: [OUT_OF_SCOPE] _stage_and_push_ci_fixes modularization debt (#3132)
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `_stage_and_push_ci_fixes` grew into a multi-mode coordinator; pre-existing maintainability debt amplified by #3210. Track under #3132 modularization.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] Fail-open BEHIND_COUNT=0 (operational awareness)
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Fail-open `BEHIND_COUNT=0` on fetch/rev-list errors can skip rebase and plain-push on stale base when the probe fails. Operational awareness; optional stricter mode behind an env flag.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] Unrelated anti-polling / hook / AGENTS / CHANGELOG bundle on branch
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Large unrelated hook, `AGENTS.md`, `hook-anti-read-poll.sh`, and 47.0.4 anti-polling / changelog work rides on the #3210 branch—not in the #3210 plan—raising review noise, mixed concerns, and harder failure attribution. Split PRs, dedicated review, or explicit PR description; track anti-polling under #3217 where noted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### OOS_4: [OUT_OF_SCOPE] Duplicate BEHIND_COUNT parsing (maintainability)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Duplicate `BEHIND_COUNT` parsing styles between `ci-status.sh` and ship-pr (`awk` vs `kv_value`). Maintainability only—share `kv_value` or a tiny parse helper.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### OOS_5: [OUT_OF_SCOPE] test-ship-pr-3210-spot.sh redundant with fix-loop target
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Spot script duplicates `test-ship-pr-fix-loop`; redundant local entrypoint unless sharded. Remove or shard; prefer `make test-ship-pr-fix-loop` only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### OOS_6: [OUT_OF_SCOPE] Missing harness for behind>0 + missing TSV on gh-run-logs failure
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: No harness for behind>0 with missing TSV when `gh-run-logs` fails; regression risk for post-rebase TSV policy. Add fix-loop case stubbing `BEHIND_COUNT=1`, empty TSV, degraded `gh-run-logs`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### OOS_7: [OUT_OF_SCOPE] CHANGELOG 47.0.4 omits #3210 feature
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: 47.0.4 changelog omits #3210 feature documented in `workflow-lifecycle.md`; release readers miss CI-fix rebase-before-push behavior. Add #3210 bullet to the version changelog entry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

---

**Merge notes (for voters, not machine output):** 43 raw slots collapsed to **20 in-scope** findings and **7 OOS** blocks. Highest-impact clusters: **FINDING_2** (five slots), **FINDING_10** (three slots, elevated to important), **FINDING_4** / **FINDING_8** / **FINDING_13** (plan testing gaps). **FINDING_9** vs **FINDING_19** stay separate (vendor rotation vs push-failure `PENDING` semantics). In-scope **FINDING_10** vs **OOS_2** both mention fail-open; OOS_2 kept for the structure reviewer’s operational-only tag. **FINDING_7** vs **OOS_4**: same parser topic; in-scope nit vs OOS maintainability per source tagging.
