# Review Round 1

- Mode: `diff`
- 12 accepted, 4 rejected (4 exonerated)

## Accepted Findings

### FINDING_1: Post-rebase retry with `CI_FIX_REBASE_PENDING` can skip re-verify and force-push an unverified tree
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Post-rebase `_verify_failed_jobs_locally` (or lint) can fail with `verify_rc` 4/1, setting `CI_FIX_REBASE_PENDING=true` and returning without push. On the next `_stage_and_push_ci_fixes` call, `ci-behind-count` may report `BEHIND_COUNT=0`, so the `behind > 0` block (deferred rebase + post-rebase re-verify) is skipped while `CI_FIX_REBASE_PENDING` still selects `git-force-push.sh`, publishing a rebased local tree that was not re-verified on retry. Related gap: `CI_FIX_REBASE_PENDING` / `did_rebase` may not survive a failed force-push across retries (plain `git-push` on retry → non-FF rejection).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_10: Behind>0 harness omits post-rebase job re-verify assertions
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Existing behind>0 fix-loop case may not supply a failed-jobs TSV or assert `_verify_failed_jobs_locally` before push on the rebased tree, so regressions in post-rebase job verification go undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_15: Behind>0 test omits `base-remote` / `base-ref` assertions
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Fix-loop harness may not assert `--base-remote` / `--base-ref` in `rebase-push-args.txt`, so fork/default base threading regressions could pass CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_16: `test-ci-status` still asserts raw `git rev-list` instead of `ci-behind-count` delegation
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Refactoring `ci-status` to delegate behind-count to `ci-behind-count.sh` could break the contract without failing ship-pr #3210 tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_2: Post-rebase verify failure re-dispatches full vendor waterfall instead of push-only retry
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: After a successful deferred rebase, post-rebase verify can return 4; the outer `_max_fix` loop may run `run_ci_fix_vendor` again (Cursor/Codex/Claude) on an already-rebased, unpushed tree instead of retrying `_stage_and_push_ci_fixes` (or a push-only helper) with `CI_FIX_REBASE_PENDING`. Vendor rotation should apply to pre-rebase verify failures, not post-rebase push/verify retries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_3: Fork CI-fix rebump/classify still keyed to `origin/main` while rebase uses `upstream/main`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: For `FORKED_TARGET`, deferred rebase/rebump threads `base_remote=upstream` / `base_ref=main`, but bump prep (`git-sync-local-main.sh`), `classify-bump` merge-base, and version-regression guards may still use `origin/main`. When upstream is ahead of fork `main`, rebump can mis-classify or apply wrong version correction vs the actual rebase base.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_4: Planned #3210 fix-loop regression coverage largely missing
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Acceptance/plan cases for `CI_FIX_REBASE_PENDING` retry, post-rebase verify `rc` 2/4, fork upstream base threading, HEAD refresh after rebase, and double-rebase noop are largely unguarded in `scripts/test-ship-pr.sh`; regressions on these edge paths may not fail CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_5: Fix-loop rotation test does not prove `start_attempt > 0` tier rotation
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Harness may pass when `tail -1` is `codex` on the first outer attempt (`_fix_attempt=0`), which matches the normal cursor→codex waterfall without exercising `_fix_attempt % 3` start-tier rotation; a broken rotation on the second outer attempt could ship undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_6: Fix-loop integration tests stub `ci-behind-count.sh`; real fetch/fail-open path under-tested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `#3210` ship-pr integration cases may stub `ci-behind-count.sh` while the real helper is only exercised in isolation (e.g. `--no-fetch`). `kv_value` parsing or fetch/fail-open behavior on the post-fix push path may not fail CI if regressed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_7: `ci-behind-count` fail-open `BEHIND_COUNT=0` vs `ci-status` pending on fetch failure
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: On fetch/rev-list errors, `ci-behind-count` can emit `BEHIND_COUNT=0` (fail-open) while `ci-status` treats fetch failure as pending. During CI-fix push, a transient count failure may skip pre-push rebase and plain-push a fix not validated against current main, diverging from `ci-wait` retry semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_8: `CI_FIX_REBASE_PENDING` is not persisted across `ship-pr` resume
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `CI_FIX_REBASE_PENDING` is a shell global (line ~60), not written to the state file. Resuming `ship-pr` after a failed post-rebase verify may lose the pending flag, leading to inconsistent plain-push vs force-push behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_9: Empty `failed_jobs_tsv` can skip post-rebase job re-verify when `behind > 0`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: When `behind > 0`, post-rebase `_verify_failed_jobs_locally` runs only if `failed_jobs_tsv` is non-empty; a vendor path with no TSV may rebase and push without re-running failed job make targets.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


